"""Per-seed context for batch 2: world, lexical index, dense embeddings, cards, searchers, metrics.

A `Ctx` holds two indexes (as in batch 1): the base index and the same index plus code-compiled entity cards.
Dense document matrices are aligned with each index's item order. All searchers expose the batch-1 Searcher
interface (raw / fused / rank) so arms can be written the same way.
"""
from __future__ import annotations

import math
import os
from collections import defaultdict

import numpy as np

from .brain import Brain, World, is_temporal_query
from .common import ROOT, wilson
from .experiments import Linker, build_cards
from .retrieval import item_text, minmax, rrf, topn

DATA2 = os.path.join(ROOT, "data_v02")
K = 10
DEPTH = 200
CLASSES2 = ["decision_support", "option_analysis", "current_state", "temporal_change", "goal_tracking",
            "preference_recommendation", "cross_domain", "multimodal"]
COMPLEX = ["decision_support", "option_analysis", "goal_tracking", "cross_domain"]


class Ctx:
    def __init__(self, seed: int, embedders=("bge-small", "qwen3-emb"), lsa=True):
        self.seed = seed
        self.w = World(os.path.join(DATA2, f"s{seed}"))
        self.tasks = [t for t in self.w.tasks if t["cls"] in CLASSES2]
        self.tasks_by_id = {t["id"]: t for t in self.w.tasks}
        self.b = Brain(self.w, lsa_dim=256 if lsa else 16)
        self.cards, self.covers, self.card_of = build_cards(self.w)
        self.bc = Brain(self.w, extra_docs=self.cards, lsa_dim=256 if lsa else 16)
        self.b_noorig = None
        self.L = Linker(self.w)
        self.E = {}
        self.emb = {}
        for e in embedders:
            self.add_embedder(e)

    def add_embedder(self, name):
        from .models import Embedder
        em = Embedder(name)
        self.emb[name] = em
        self.E[(name, "base")] = em.docs([item_text(it, True) for it in self.b.ix.items], f"s{self.seed}/base")
        self.E[(name, "cards")] = em.docs([item_text(it, True) for it in self.bc.ix.items], f"s{self.seed}/cards")

    def noorig(self, name):
        if self.b_noorig is None:
            self.b_noorig = Brain(self.w, with_origin=False)
        key = (name, "noorig")
        if key not in self.E:
            self.E[key] = self.emb[name].docs([item_text(it, False) for it in self.b_noorig.ix.items], f"s{self.seed}/noorig")
        return self.b_noorig, self.E[key]

    def searcher(self, method, emb=None, index="base", alpha=0.5):
        if index == "base":
            b, E = self.b, (self.E[(emb, "base")] if emb else None)
        elif index == "cards":
            b, E = self.bc, (self.E[(emb, "cards")] if emb else None)
        else:
            b, E = self.noorig(emb)
        return DSearcher(b, E, self.emb.get(emb), method, alpha)


class DSearcher:
    """method: bm25 | dense | rrf (BM25 + dense) | wsum (min-max weighted, alpha on BM25) | lsa | rrf-lsa (batch-1 default)."""

    def __init__(self, brain: Brain, E, embedder, method="rrf", alpha=0.5):
        self.b = brain
        self.E = E
        self.em = embedder
        self.method = method
        self.alpha = alpha
        self._cache = {}

    def raw(self, query, identity):
        key = (query, identity)
        if key in self._cache:
            self._cache[key] = self._cache.pop(key)       # LRU touch
            return self._cache[key]
        bc = self.b.__dict__.setdefault("_bm25_cache", {})
        if key not in bc:
            bc[key] = self.b.ix.bm25(query, stats_mask=self.b.access(identity)).astype(np.float32)
            if len(bc) > 6000:
                bc.pop(next(iter(bc)))
        bm = bc[key]
        if self.E is not None:
            dv = self.E @ self.em.queries([query])[0]
        else:
            dv = self.b.ix.lsa_cos(query)
        self._cache[key] = (bm, dv)
        if len(self._cache) > 400:
            self._cache.pop(next(iter(self._cache)))
        return self._cache[key]

    def prefetch(self, queries):
        if self.em is not None:
            self.em.queries(list(dict.fromkeys(queries)))

    def fused(self, query, identity, mask, extra_lists=None, extra_w=None):
        bm, dv = self.raw(query, identity)
        m = self.method
        if m == "bm25":
            if not extra_lists:
                return np.where(mask & (bm > 0), bm, -np.inf)
            lists, w = [topn(bm, mask & (bm > 0), DEPTH)], [1.0]
        elif m in ("dense", "lsa"):
            if not extra_lists:
                return np.where(mask, dv, -np.inf)
            lists, w = [topn(dv, mask, DEPTH)], [1.0]
        elif m in ("rrf", "rrf-lsa"):
            lists, w = [topn(bm, mask & (bm > 0), DEPTH), topn(dv, mask, DEPTH)], [1.0, 1.0]
        elif m == "wsum":
            s = self.alpha * minmax(bm, mask) + (1 - self.alpha) * minmax(dv, mask)
            if not extra_lists:
                return np.where(mask, s, -np.inf)
            lists, w = [topn(s, mask, DEPTH)], [1.0]
        else:
            raise ValueError(m)
        if extra_lists:
            lists = lists + list(extra_lists)
            w = w + list(extra_w)
        s = rrf(lists, self.b.N, weights=w)
        return np.where(mask & (s > 0), s, -np.inf)

    def rank(self, query, identity, mask, n=K, **kw):
        s = self.fused(query, identity, mask, **kw)
        return list(topn(s, np.isfinite(s), n))


# ============================================================================ pipeline helpers
def live(b: Brain, t):
    temporal = is_temporal_query(t["query"])
    return b.live_mask(t["requester"], "keyed", temporal), temporal


def query_ranked(b, s, t, n=100, mask=None, **kw):
    m, temporal = live(b, t)
    if mask is not None:
        m = m & mask
    return b.forward(s.rank(t["query"], t["requester"], m, n=n + 20, **kw), temporal)[:n]


def fill(prefix, ranked, total):
    out = list(prefix)
    for i in ranked:
        if len(out) >= total:
            break
        if i not in out:
            out.append(i)
    return out


def ids_of(b, idx):
    return [b.ids[i] for i in idx]


# ============================================================================ metrics (cluster-aware)
def row(t, final_ids, covers=None, ks=(10,)):
    req = set(t["required"])
    r = dict(id=t["id"], cls=t["cls"], set_id=t["set_id"], size=len(req))
    for k in ks:
        got = set(final_ids[:k])
        if covers:
            for i in final_ids[:k]:
                got |= covers.get(i, set())
        found = got & req
        r[f"ok@{k}"] = len(found) == len(req)
        r[f"rec@{k}"] = len(found) / len(req)
        if k == ks[0]:
            r["found"] = sorted(found)
    return r


def per_set(rows, key):
    """Collapse task rows to distinct required sets: per-set mean of `key`."""
    agg = defaultdict(list)
    for r in rows:
        agg[(r.get("seed", 0), r["set_id"])].append(float(r[key]))
    return {k: float(np.mean(v)) for k, v in agg.items()}


def wilson_sets(rows, key="ok@10"):
    """Rate = mean over distinct sets of the per-set success; Wilson interval with n = number of distinct sets."""
    ps = per_set(rows, key)
    n = len(ps)
    if n == 0:
        return dict(p=float("nan"), lo=float("nan"), hi=float("nan"), n=0, n_tasks=0)
    k = sum(ps.values())
    p, lo, hi = wilson_frac(k, n)
    return dict(p=p, lo=lo, hi=hi, n=n, n_tasks=len(rows))


def wilson_frac(k, n, z=1.959964):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(max(p * (1 - p), 0) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - hw), min(1.0, c + hw)


def sign_test_sets(rows_a, rows_b, key="ok@10"):
    """Paired, cluster-aware: per distinct set compare mean(B) vs mean(A); exact two-sided sign test on sets that differ.
    Returns (sets B better, sets A better, p, mean diff in pp, 95% cluster-bootstrap CI of the diff in pp)."""
    a, b = per_set(rows_a, key), per_set(rows_b, key)
    keys = sorted(set(a) & set(b))
    d = np.array([b[k] - a[k] for k in keys])
    wins, losses = int((d > 1e-9).sum()), int((d < -1e-9).sum())
    n = wins + losses
    if n == 0:
        p = 1.0
    else:
        kk = min(wins, losses)
        p = min(1.0, 2 * sum(math.comb(n, i) for i in range(kk + 1)) / 2 ** n)
    rng = np.random.default_rng(0)
    if len(d):
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
    else:
        lo = hi = float("nan")
    return dict(b_better=wins, a_better=losses, p=p, diff=100 * float(d.mean()) if len(d) else float("nan"), lo=100 * lo, hi=100 * hi, n_sets=len(keys))


def summarise_cls(rows, key="ok@10", classes=CLASSES2):
    out = {}
    for c in classes:
        rr = [r for r in rows if r["cls"] == c]
        out[c] = wilson_sets(rr, key)
        out[c]["item_recall"] = float(np.mean([r[key.replace("ok", "rec")] for r in rr])) if rr else float("nan")
    allr = [r for r in rows if r["cls"] in classes]
    out["ALL"] = wilson_sets(allr, key)
    out["ALL"]["item_recall"] = float(np.mean([r[key.replace("ok", "rec")] for r in allr])) if allr else float("nan")
    return out
