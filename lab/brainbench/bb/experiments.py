"""E1, E2, E3, E4, E5, E7 and the I8 check. Each function returns a dict of results (JSON-able)."""
from __future__ import annotations

import random
import re
from collections import Counter, defaultdict

import numpy as np
from sklearn.preprocessing import normalize

from .brain import CLASSES, Brain, World, cr_at_k, covered, is_temporal_query, summarise
from .common import NOW_DAY, day_to_date, month_start_day, tokenize, wilson
from .retrieval import Index, rrf, topn
from .tasks import SCOPE_GROUPS, scope_group

K = 10
DEPTH = 200


# =========================================================================== shared search
class Searcher:
    """Hybrid RRF(BM25, LSA) with BM25 statistics over the requester's visible set.
    Caches the raw score arrays per (query, identity)."""

    def __init__(self, brain: Brain, method: str = "rrf"):
        self.b = brain
        self.method = method
        self._cache = {}

    def raw(self, query, identity):
        key = (query, identity)
        if key not in self._cache:
            acc = self.b.access(identity)
            bm = self.b.ix.bm25(query, stats_mask=acc)
            ls = self.b.ix.lsa_cos(query)
            self._cache[key] = (bm, ls)
        return self._cache[key]

    def fused(self, query, identity, mask, extra_lists=None, extra_w=None):
        bm, ls = self.raw(query, identity)
        if self.method == "bm25":
            if not extra_lists:
                return np.where(mask & (bm > 0), bm, -np.inf)
            lists = [topn(bm, mask & (bm > 0), DEPTH)]
            s = rrf(lists + extra_lists, self.b.N, weights=[1.0] + list(extra_w))
            return np.where(mask & (s > 0), s, -np.inf)
        lists = [topn(bm, mask & (bm > 0), DEPTH), topn(ls, mask, DEPTH)]
        w = [1.0, 1.0]
        if extra_lists:
            lists += extra_lists
            w += extra_w
        s = rrf(lists, self.b.N, weights=w)
        s = np.where(mask & (s > 0), s, -np.inf)
        return s

    def rank(self, query, identity, mask, n=K, **kw):
        s = self.fused(query, identity, mask, **kw)
        return list(topn(s, np.isfinite(s), n))


def ids_of(b, idx):
    return [b.ids[i] for i in idx]


def leak_count(b, identity, idx):
    acc = b.access(identity)
    return sum(1 for i in idx if not acc[i])


def run_rows(tasks, fn):
    rows = []
    for t in tasks:
        final_ids, extra = fn(t)
        ok, rec = cr_at_k(final_ids, t["required"], K, extra.get("covers"))
        r = dict(id=t["id"], cls=t["cls"], ok=ok, recall=rec, size=t["size"])
        r.update({k: v for k, v in extra.items() if k != "covers"})
        rows.append(r)
    return rows


def eval_tasks(w):
    return [t for t in w.tasks if t["cls"] in CLASSES]


# =========================================================================== E0 baseline
def e0_baselines(w: World, brain: Brain):
    from .retrieval import Retriever
    out = {}
    tasks = eval_tasks(w)
    for method in ["bm25", "tfidf", "lsa", "rrf", "wsum"]:
        R = Retriever(brain.ix, method)
        rows = []
        for t in tasks:
            temporal = is_temporal_query(t["query"])
            m = brain.live_mask(t["requester"], "keyed", temporal)
            s = R.score(t["query"], m)
            top = topn(s, np.isfinite(s), K)
            ids = ids_of(brain, brain.forward(list(top), temporal))
            ok, rec = cr_at_k(ids, t["required"], K)
            rows.append(dict(cls=t["cls"], ok=ok, recall=rec))
        out[method] = summarise(rows)
    # temporal router accuracy
    tp = sum(is_temporal_query(t["query"]) for t in w.tasks if t["cls"] == "temporal_change")
    n_t = sum(t["cls"] == "temporal_change" for t in w.tasks)
    fp = sum(is_temporal_query(t["query"]) for t in w.tasks if t["cls"] != "temporal_change")
    n_nt = sum(t["cls"] != "temporal_change" for t in w.tasks)
    out["router"] = dict(tp=tp, n_temporal=n_t, fp=fp, n_non_temporal=n_nt)
    return out


# =========================================================================== E1 write paths
def build_summaries(w: World, gen_day: int | None):
    """Entity summaries compiled from keyed facts as at gen_day (None = current heads)."""
    docs = []
    per = defaultdict(list)
    for k in w.keys.values():
        if gen_day is None:
            vid = k["versions"][-1]
        else:
            vid = None
            for v in k["versions"]:
                if w.by_id[v]["valid_from"] <= gen_day:
                    vid = v
            if vid is None:
                continue
        per[(k["entity"], k["partition"])].append((k, vid))
    day = NOW_DAY if gen_day is None else gen_day
    for (eid, part), lst in sorted(per.items()):
        e = w.entities[eid]
        body = "; ".join(f"{k['label']}: {w.by_id[v]['value_str']}" for k, v in lst)
        sc = w.by_id[lst[0][1]]["scope"]
        docs.append(dict(id=f"sum_{eid}_{part.replace('/', '-')}", type="summary", partition=part, scope=sc,
                         title=f"Summary — {e['name']}", text=f"Profile of {e['name']} ({', '.join(e['aliases'][1:3])}), generated {day_to_date(day)}: {body}.",
                         created_day=day, recorded_day=day, entities=[eid], derived=True,
                         fact_versions={k["key"]: v for k, v in lst}))
    return docs


def e1_write_paths(w: World, brain: Brain, s: Searcher):
    probes = [t for t in w.tasks if t["cls"] == "stale_probe"]
    created = brain.ix.created

    def classify(t, ranked_idx, bb, summaries_stale=None):
        head = bb.pos[t["required"][0]]
        stale = {bb.pos[x] for x in t["stale_ids"]}
        traps = {bb.pos[x] for x in t["trap_ids"]}
        top = ranked_idx[:K]
        hpos = top.index(head) if head in top else None
        lim = hpos if hpos is not None else K

        def above(group):
            return any(i in group for i in top[:lim])
        st_fact = above(stale)
        st_trap = above(traps)
        st_sum = False
        cur_sum_hit = False
        if summaries_stale is not None:
            for i in top[:lim]:
                it = bb.ix.items[i]
                if it.get("type") == "summary":
                    fv = it["fact_versions"].get(t["key"])
                    if fv is None:
                        continue
                    if fv != t["required"][0]:
                        st_sum = True
                    else:
                        cur_sum_hit = True
        found = hpos is not None or cur_sum_hit
        # first value-bearing item in top-k (head, old version, stale trap, current trap, summary)
        cur_traps = {i for i in top if i not in traps and t["required"][0] in bb.ix.items[i].get("fact_refs", [])}
        first = None
        for i in top:
            it = bb.ix.items[i]
            if i == head or i in cur_traps:
                first = "current"; break
            if i in stale or i in traps:
                first = "stale"; break
            if it.get("type") == "summary" and t["key"] in it.get("fact_versions", {}):
                first = "current" if it["fact_versions"][t["key"]] == t["required"][0] else "stale"; break
        return dict(stale_fact=st_fact, stale_trap=st_trap, stale_sum=st_sum, head_found=found, first=first,
                    strict_ok=found and not st_fact and not st_sum,
                    strict_ok_traps=found and not st_fact and not st_sum and not st_trap)

    def arm(name, mode, bb=brain, ss=s, forward=False, recency_w=0.0, miss_p=None, mention_fwd=False, sums=None,
            suppress_mentions=None):
        rng = random.Random(99)
        missed = None
        if miss_p is not None:
            missed = np.array([bool(bb.is_super[i]) and rng.random() < miss_p for i in range(bb.N)])
        stale_mention = np.zeros(bb.N, dtype=bool)
        if suppress_mentions is not None:  # extraction recall r: share of stale mentions whose fact_ref was extracted
            rng2 = random.Random(7)
            for i, it in enumerate(bb.ix.items):
                refs = it.get("fact_refs", [])
                if refs and any(w.by_id[f].get("superseded_by") for f in refs if f in w.by_id) and rng2.random() < suppress_mentions:
                    stale_mention[i] = True
        rows = []
        for t in probes:
            acc = bb.access(t["requester"])
            if mode == "keyed":
                m = acc & ~bb.is_super
            elif mode == "invalidate":
                m = acc & (~bb.is_super | missed)
            else:
                m = acc.copy()
            m &= ~stale_mention
            extra_lists, extra_w = None, None
            if recency_w > 0:
                bm, ls = ss.raw(t["query"], t["requester"])
                cand = np.zeros(bb.N, dtype=bool)
                cand[topn(bm, m & (bm > 0), DEPTH)] = True
                cand[topn(ls, m, DEPTH)] = True
                rec_rank = topn(bb.ix.created.astype(float), cand, int(cand.sum()))
                extra_lists, extra_w = [rec_rank], [recency_w]
            ranked = ss.rank(t["query"], t["requester"], m, n=40, extra_lists=extra_lists, extra_w=extra_w)
            if forward:
                ranked = bb.forward(ranked, temporal=False)
            if mention_fwd:
                out, seen = [], set()
                for i in ranked:
                    for j in [i] + [bb.pos[w.head_of[f]] for f in bb.ix.items[i].get("fact_refs", []) if f in w.head_of]:
                        if j not in seen and acc[j]:
                            seen.add(j); out.append(j)
                ranked = out
            r = classify(t, ranked, bb, sums)
            r["leak"] = leak_count(bb, t["requester"], ranked[:K])
            rows.append(r)
        n = len(rows)
        res = dict(arm=name, n=n)
        for key in ("stale_fact", "stale_trap", "stale_sum"):
            k = sum(r[key] for r in rows)
            res[key] = dict(k=k, p=k / n, lo=wilson(k, n)[1], hi=wilson(k, n)[2])
        k = sum(not r["strict_ok"] for r in rows)
        res["strict_error"] = dict(k=k, p=k / n, lo=wilson(k, n)[1], hi=wilson(k, n)[2])
        k = sum(not r["strict_ok_traps"] for r in rows)
        res["strict_error_with_traps"] = dict(k=k, p=k / n, lo=wilson(k, n)[1], hi=wilson(k, n)[2])
        k = sum(not r["head_found"] for r in rows)
        res["head_miss"] = dict(k=k, p=k / n, lo=wilson(k, n)[1], hi=wilson(k, n)[2])
        res["leaks"] = sum(r["leak"] for r in rows)
        surf = [r for r in rows if r["first"] is not None]
        k = sum(r["first"] == "stale" for r in surf)
        p, lo, hi = wilson(k, len(surf))
        res["first_value_stale"] = dict(k=k, n=len(surf), p=p, lo=lo, hi=hi)
        res["rows"] = [bool(r["head_found"]) for r in rows]
        return res

    out = {"arms": []}
    A = out["arms"]
    A.append(arm("(c) add-only, no recency", "add"))
    A.append(arm("(b) add-only + recency prior (w=0.5)", "add", recency_w=0.5))
    A.append(arm("(b') add-only + recency prior (w=1.0)", "add", recency_w=1.0))
    A.append(arm("(b'') add-only + recency prior (w=2.0)", "add", recency_w=2.0))
    A.append(arm("I3 alone: add-only + forward-to-head", "add", forward=True))
    for p in (0.02, 0.05, 0.10, 0.20):
        A.append(arm(f"simulated imperfect invalidation, miss={int(p*100)}%", "invalidate", miss_p=p))
    A.append(arm("(a) keyed upsert (superseded out of live index)", "keyed"))
    A.append(arm("(a)+I3 keyed upsert + forward-to-head", "keyed", forward=True))
    A.append(arm("(a)+I3+mention-forwarding (traps pull in head)", "keyed", forward=True, mention_fwd=True))
    A.append(arm("(a)+I3 + recency prior (w=1.0)", "keyed", forward=True, recency_w=1.0))
    A.append(arm("add-only + I3 forward + mention-forwarding (all versions indexed)", "add", forward=True, mention_fwd=True))
    for r in (0.7, 0.9, 1.0):
        A.append(arm(f"(a)+I3 + stale-mention suppression (extraction recall {int(r*100)}%)", "keyed", forward=True, suppress_mentions=r))
    A.append(arm("(a)+I3 + suppression(90%) + mention-forwarding + recency(1.0)", "keyed", forward=True, suppress_mentions=0.9,
                 mention_fwd=True, recency_w=1.0))

    # ---- H5 derived artefacts: summaries generated at month 6, never regenerated
    for label, gday in (("stale summaries (generated month 6, not regenerated)", month_start_day(6) + 1),
                        ("summaries regenerated on dependency change (current)", None)):
        sums = build_summaries(w, gday)
        bb = Brain(w, extra_docs=sums)
        ss = Searcher(bb)
        A.append(arm(f"(a)+I3 + {label}", "keyed", bb=bb, ss=ss, forward=True, sums=True))
        if gday is not None:
            n_stale_docs = sum(1 for d in sums for kk, v in d["fact_versions"].items() if v != w.keys[kk]["versions"][-1])
            out["stale_summary_values"] = n_stale_docs
            out["summary_docs"] = len(sums)

    # ---- effect of write path on temporal_change CR@10 (keyed needs the router + history)
    ttasks = [t for t in w.tasks if t["cls"] == "temporal_change"]
    trows = {}
    for name, use_router, mode in (("keyed, history never searched", False, "keyed"), ("keyed + temporal router -> history", True, "keyed"),
                                   ("add-only (all versions live)", None, "add")):
        def fn(t, use_router=use_router, mode=mode):
            acc = brain.access(t["requester"])
            temporal = is_temporal_query(t["query"]) if use_router else (mode == "add")
            m = acc & ~brain.is_super if (mode == "keyed" and not temporal) else acc
            return ids_of(brain, s.rank(t["query"], t["requester"], m)), {}
        trows[name] = summarise(run_rows(ttasks, fn))["temporal_change"]
    out["temporal"] = trows
    return out


# =========================================================================== E2 scope modes
class ScopeInfer:
    def __init__(self, brain: Brain, tau=0.08, margin=0.01):
        ix = brain.ix
        self.groups = SCOPE_GROUPS
        cents = []
        for g in self.groups:
            m = brain.sgroup == g
            c = np.asarray(ix.tfidf[m].mean(axis=0)).ravel()
            cents.append(c / (np.linalg.norm(c) + 1e-12))
        self.C = np.vstack(cents)
        self.ix = ix
        self.b = brain
        self.tau, self.margin = tau, margin

    def query_sims(self, q):
        v = self.ix.tfidf_vec.transform([q]).toarray().ravel()
        return self.C @ v

    def from_query(self, q):
        s = self.query_sims(q)
        o = np.argsort(-s)
        if s[o[0]] < self.tau or s[o[0]] - s[o[1]] < self.margin:
            return None
        return self.groups[o[0]]

    def trail_votes(self, t, noise):
        items = [t["trail_noise_items"][i] if t["trail_noise_draws"][i] < noise else
                 (t["trail_on_task"][i] if i < len(t["trail_on_task"]) else t["trail_noise_items"][i]) for i in range(6)]
        c = Counter(scope_group(self.b.ix.items[self.b.pos[x]]["scope"]) for x in items)
        return c

    def from_trail(self, t, noise):
        c = self.trail_votes(t, noise)
        return c.most_common(1)[0][0]

    def from_both(self, t, noise):
        c = self.trail_votes(t, noise)
        s = self.query_sims(t["query"])
        sc = {g: c.get(g, 0) / 6 + 2.0 * s[i] for i, g in enumerate(self.groups)}
        return max(sc, key=sc.get)


def e2_scope(w: World, brain: Brain, s: Searcher):
    tasks = eval_tasks(w)
    si = ScopeInfer(brain)

    def live(t):
        temporal = is_temporal_query(t["query"])
        return brain.live_mask(t["requester"], "keyed", temporal), temporal

    def final(t, ranked, temporal):
        return ids_of(brain, brain.forward(ranked, temporal))

    def none(t):
        m, tp = live(t)
        return final(t, s.rank(t["query"], t["requester"], m), tp), {}

    def hard(group_fn):
        def f(t):
            m, tp = live(t)
            g = group_fn(t)
            mm = m & brain.scope_mask(g) if g else m
            return final(t, s.rank(t["query"], t["requester"], mm), tp), {}
        return f

    def boost(group_fn, wt=1.0):
        def f(t):
            m, tp = live(t)
            g = group_fn(t)
            if not g:
                return final(t, s.rank(t["query"], t["requester"], m), tp), {}
            fs = s.fused(t["query"], t["requester"], m & brain.scope_mask(g))
            lst = topn(fs, np.isfinite(fs), DEPTH)
            return final(t, s.rank(t["query"], t["requester"], m, extra_lists=[lst], extra_w=[wt]), tp), {}
        return f

    decl = lambda t: t["declared_scope"]
    q_inf = lambda t: si.from_query(t["query"])
    arms = {
        "none (access filter only)": none,
        "declared: hard filter": hard(decl),
        "declared: boost (RRF w=1)": boost(decl, 1.0),
        "declared: boost (RRF w=2)": boost(decl, 2.0),
        "inferred from query: boost": boost(q_inf),
        "inferred from query: hard filter": hard(q_inf),
        "trail (noise 0.3): boost": boost(lambda t: si.from_trail(t, 0.3)),
        "trail (noise 0.6): boost": boost(lambda t: si.from_trail(t, 0.6)),
        "trail+query (noise 0.3): boost": boost(lambda t: si.from_both(t, 0.3)),
    }
    out = {"arms": {}, "rows": {}}
    for name, fn in arms.items():
        rows = run_rows(tasks, fn)
        out["arms"][name] = summarise(rows)
        out["rows"][name] = [r["ok"] for r in rows]
    # hard-filter ceiling: share of tasks whose required items all live in the declared group
    ceil = defaultdict(lambda: [0, 0])
    for t in tasks:
        c = ceil[t["cls"]]
        c[0] += int(t["required_scope_groups"] == [t["declared_scope"]]); c[1] += 1
    out["hard_ceiling"] = {k: v[0] / v[1] for k, v in ceil.items()}
    # scope inference accuracy
    acc = {}
    for name, f in (("query", lambda t: si.from_query(t["query"])), ("trail noise 0.0", lambda t: si.from_trail(t, 0.0)),
                    ("trail noise 0.3", lambda t: si.from_trail(t, 0.3)), ("trail noise 0.6", lambda t: si.from_trail(t, 0.6)),
                    ("trail+query noise 0.3", lambda t: si.from_both(t, 0.3)), ("trail+query noise 0.6", lambda t: si.from_both(t, 0.6))):
        preds = [f(t) for t in tasks]
        right = sum(p == t["declared_scope"] for p, t in zip(preds, tasks))
        abst = sum(p is None for p in preds)
        in_req = sum(p in t["required_scope_groups"] for p, t in zip(preds, tasks))
        acc[name] = dict(n=len(tasks), correct=right, abstain=abst, in_required_groups=in_req)
    out["inference"] = acc
    out["order"] = [t["id"] for t in tasks]
    return out


# =========================================================================== E3 context assembly
HAND_SLOTS = {
    "finance": dict(static=["portfolio.strategy", "portfolio.lvr_rule", "offset.balance", "portfolio.borrowing_capacity", "offset.savings_goal"],
                    attrs={"property": ["valuation", "loan", "rent", "lease_end", "rate", "pm"], "holding": ["units", "value"], "account": []}),
    "business/gym": dict(static=["gym.members", "gym.member_target", "gym.price", "gym.staff_count", "gym.equipment_supplier"],
                         attrs={"person": ["plan", "program", "goal", "progress", "coach"]}),
    "business/cafe": dict(static=["cafe.cash_reserve", "cafe.covers", "cafe.revenue_goal", "cafe.bean_supplier", "cafe.head_barista"], attrs={}),
    "business/construction": dict(static=["con.pipeline", "con.strategy", "con.supervisor", "con.active_projects", "con.pipeline_target"],
                                  attrs={"project": ["status"]}),
    "health": dict(static=["train.program", "train.sessions", "goal_squat.target", "train.squat_1rm", "goal_run.target"], attrs={}),
    "family": dict(static=["family.school_break", "family.holiday_budget", "mila.activity", "theo.activity", "ruby.activity"],
                   attrs={"person": ["activities", "swim_pb", "swim_goal"]}),
    "reading": dict(static=["reading.goal", "reading.finished", "reading.current"], attrs={}),
}


class Linker:
    """Lexical entity linker over entity aliases + requester self-reference."""

    def __init__(self, w: World):
        self.w = w
        pats = []
        for e in w.entities.values():
            for a in e["aliases"]:
                if a.lower() in ("me", "p", "training", "portfolio", "offset", "reading list", "my training", "my reading") or len(a) < 3:
                    continue
                pats.append((a.lower(), e["id"]))
        pats.sort(key=lambda x: -len(x[0]))
        self.pats = pats
        self.member_ent = {}
        for e in w.entities.values():
            if e.get("member_id"):
                self.member_ent[f"member_{e['member_id']}"] = e["id"]
        self.keys_by_entity = defaultdict(list)
        for k in w.keys.values():
            self.keys_by_entity[k["entity"]].append(k)

    def link(self, q, requester):
        ql = q.lower()
        found = []
        for a, eid in self.pats:
            if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", ql) and eid not in found:
                found.append(eid)
        if requester in self.member_ent and re.search(r"\b(i|my|me|i'm|i've)\b", ql):
            found.insert(0, self.member_ent[requester])
        return found


def scope_packets(w: World, brain: Brain, P: int):
    """Standing packet per scope group (task-agnostic rule): current goal/strategy/rule keyed facts,
    then the most recent meeting decisions, newest first."""
    packets = {}
    for g in SCOPE_GROUPS:
        cand = []
        for k in w.keys.values():
            if scope_group(k["scope"]) == g and k["family"] in ("goal", "strategy", "rule"):
                h = w.by_id[k["versions"][-1]]
                cand.append((0, -h["created_day"], h["id"]))
        for it in w.items:
            if it["type"] == "meeting" and scope_group(it["scope"]) == g and it["created_day"] >= NOW_DAY - 240:
                cand.append((1, -it["created_day"], it["id"]))
        cand.sort()
        packets[g] = [c[2] for c in cand]
    return packets


def build_cards(w: World):
    docs, covers, card_of = [], {}, {}
    per = defaultdict(list)
    for k in w.keys.values():
        per[(k["entity"], k["partition"])].append(k)
    for (eid, part), ks in sorted(per.items()):
        e = w.entities[eid]
        heads = [k["versions"][-1] for k in ks]
        body = "; ".join(f"{k['label']}: {w.by_id[h]['value_str']}" for k, h in zip(ks, heads))
        cid = f"card_{eid}_{part.replace('/', '-')}"
        docs.append(dict(id=cid, type="entity_card", partition=part, scope=ks[0]["scope"], title=f"Entity card — {e['name']}",
                         text=f"{e['name']} ({', '.join(e['aliases'][1:])}). Current facts: {body}.", created_day=NOW_DAY,
                         recorded_day=NOW_DAY, entities=[eid], derived=True))
        covers[cid] = set(heads)
        card_of.setdefault(eid, []).append(cid)
    return docs, covers, card_of


def e3_assembly(w: World, brain: Brain, s: Searcher):
    tasks = eval_tasks(w)
    L = Linker(w)
    packets = scope_packets(w, brain, 5)

    def search_fill(t, prefix_idx, total=K, bb=brain, ss=s):
        temporal = is_temporal_query(t["query"])
        m = bb.live_mask(t["requester"], "keyed", temporal)
        ranked = bb.forward(ss.rank(t["query"], t["requester"], m, n=K + 30), temporal)
        out = list(prefix_idx)
        for i in ranked:
            if len(out) >= total:
                break
            if i not in out:
                out.append(i)
        return out

    def acc_ok(t, iid, bb=brain):
        return bb.access(t["requester"])[bb.pos[iid]]

    def q_only(t):
        return ids_of(brain, search_fill(t, [])), {}

    def q_mention_fwd(t):
        """Query top-k, but any retrieved note that references a keyed fact pulls that fact's head in
        directly after it (still k items total)."""
        temporal = is_temporal_query(t["query"])
        m = brain.live_mask(t["requester"], "keyed", temporal)
        acc = brain.access(t["requester"])
        ranked = brain.forward(s.rank(t["query"], t["requester"], m, n=K + 30), temporal)
        out = []
        for i in ranked:
            for j in [i] + [brain.pos[w.head_of[f]] for f in brain.ix.items[i].get("fact_refs", []) if f in w.head_of]:
                if j not in out and acc[j] and len(out) < K:
                    out.append(j)
            if len(out) >= K:
                break
        return ids_of(brain, out), {}

    def packet(P):
        def f(t):
            g = t["declared_scope"]
            pk = [brain.pos[i] for i in packets[g] if acc_ok(t, i)][:P]
            ids = ids_of(brain, search_fill(t, pk))
            return ids, dict(prefix_cov=len(set(ids_of(brain, pk)) & set(t["required"])) / len(set(t["required"])))
        return f

    def slot_ids(t, kind, cap):
        g = t["declared_scope"]
        ents = L.link(t["query"], t["requester"])
        out = []
        if kind == "hand":
            spec = HAND_SLOTS[g]
            for eid in ents:
                ek = w.entities[eid]["kind"]
                for attr in spec["attrs"].get(ek, []):
                    for k in L.keys_by_entity[eid]:
                        if k["key"].split(".")[-1] == attr or k["attr"] == attr:
                            out.append(k["versions"][-1])
            out += [w.keys[k]["versions"][-1] for k in spec["static"]]
        else:  # generic: all head facts of linked entities (ranked by query score), then goal/rule/strategy heads in scope
            bm, ls = s.raw(t["query"], t["requester"])
            ent_facts = []
            for eid in ents:
                for k in L.keys_by_entity[eid]:
                    h = k["versions"][-1]
                    ent_facts.append((-(bm[brain.pos[h]] + 5 * ls[brain.pos[h]]), h))
            out += [h for _, h in sorted(ent_facts)]
            out += packets[g]
        seen, res = set(), []
        for i in out:
            if i not in seen and acc_ok(t, i):
                seen.add(i); res.append(brain.pos[i])
        return res[:cap]

    def slots(kind, cap=5):
        def f(t):
            sl = slot_ids(t, kind, cap)
            ids = ids_of(brain, search_fill(t, sl))
            return ids, dict(prefix_cov=len(set(ids_of(brain, sl)) & set(t["required"])) / len(set(t["required"])))
        return f

    cards, covers, card_of = build_cards(w)
    bc = Brain(w, extra_docs=cards)
    sc = Searcher(bc, method=s.method)

    def cardsf(C=3, with_slots=False):
        def f(t):
            ents = L.link(t["query"], t["requester"])
            pre = []
            for eid in ents:
                for cid in card_of.get(eid, []):
                    if acc_ok(t, cid, bc) and len(pre) < C:
                        pre.append(bc.pos[cid])
            if with_slots:
                g = t["declared_scope"]
                for k in HAND_SLOTS[g]["static"]:
                    h = w.keys[k]["versions"][-1]
                    if acc_ok(t, h, bc) and len(pre) < 5 and bc.pos[h] not in pre:
                        # skip if a pinned card already covers it
                        if not any(h in covers.get(bc.ids[p], ()) for p in pre):
                            pre.append(bc.pos[h])
            ids = ids_of(bc, search_fill(t, pre, bb=bc, ss=sc))
            pc = covered(ids_of(bc, pre), t["required"], covers)
            return ids, dict(covers=covers, prefix_cov=len(pc) / len(set(t["required"])))
        return f

    # optimistic ceiling for ANY standing packet: the 5 items most often required by tasks declaring that scope
    # (computed on the test tasks themselves, so it is an upper bound, not a deployable packet)
    freq = defaultdict(Counter)
    for t in tasks:
        for r in t["required"]:
            freq[t["declared_scope"]][r] += 1
    oracle = {g: [i for i, _ in freq[g].most_common(40)] for g in freq}

    def oracle_packet(P):
        def f(t):
            pk = [brain.pos[i] for i in oracle[t["declared_scope"]] if acc_ok(t, i)][:P]
            ids = ids_of(brain, search_fill(t, pk))
            return ids, dict(prefix_cov=len(set(ids_of(brain, pk)) & set(t["required"])) / len(set(t["required"])))
        return f

    arms = {
        "query-only top-10": q_only,
        "query + mention->head forwarding (new)": q_mention_fwd,
        "ORACLE frequency packet(5) + query(5) [ceiling]": oracle_packet(5),
        "packet(3) + query(7)": packet(3),
        "packet(5) + query(5)": packet(5),
        "hand slot contract(<=5) + query": slots("hand"),
        "generic slots(<=5) + query": slots("generic"),
        "entity cards(<=3, pinned) + query (cards indexed)": cardsf(3),
        "cards(<=3) + hand static slots (<=5 total) + query": cardsf(3, with_slots=True),
    }
    out = {"arms": {}, "prefix_cov": {}, "rows": {}}
    for name, fn in arms.items():
        rows = run_rows(tasks, fn)
        out["arms"][name] = summarise(rows)
        out["rows"][name] = [r["ok"] for r in rows]
        if "prefix_cov" in rows[0]:
            pcs = defaultdict(list)
            for r in rows:
                pcs[r["cls"]].append(r["prefix_cov"])
            out["prefix_cov"][name] = {c: float(np.mean(v)) for c, v in pcs.items()}
            full = defaultdict(lambda: [0, 0])
            for r in rows:
                full[r["cls"]][0] += int(r["prefix_cov"] >= 0.999); full[r["cls"]][1] += 1
            out["prefix_cov"][name + " [all req. covered by prefix alone]"] = {c: v[0] / v[1] for c, v in full.items()}
    out["order"] = [t["id"] for t in tasks]
    return out


# =========================================================================== E4 BM25 side channel
def e4_bm25_side_channel(w: World):
    """Attacker = partner_cafe. Plants a probe note in their own partition containing a candidate term,
    queries it, and inverts the IDF to estimate how many documents ANYWHERE contain the term."""
    attacker = "partner_cafe"
    vis_parts = set(w.identities[attacker]["partitions"])
    base_items = list(w.items)
    candidates = ["halyard", "refix", "wren", "biopsy", "kestrel", "zzqprobe"]
    # one canary token from the owner partition (unique string) - can the attacker confirm it exists?
    owner_canary = next(it["canary_token"] for it in w.items if it.get("canary_token") and it["partition"] == "owner")
    candidates.append(owner_canary.split("-")[0].lower())
    probe_docs = [dict(id=f"probe_{i}", type="note", partition="biz/cafe", scope="business/cafe/ops", title="",
                       text=f"probe {c}", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[]) for i, c in enumerate(candidates)]

    def build(extra):
        ix = Index(base_items + probe_docs + extra, with_origin=True, lsa_dim=8)
        return ix

    def probe(ix, term, stats):
        pos = ix.pos[f"probe_{candidates.index(term)}"]
        acc = np.array([p in vis_parts for p in ix.partition])
        if stats == "global":
            sc = ix.bm25(term)
        elif stats == "visible":
            sc = ix.bm25(term, stats_mask=acc)
        else:
            sc = ix.bm25(term, per_partition=True)
        return sc[pos], acc

    def invert_df(ix, score, stats, acc, pos):
        # score = idf * tf*(k1+1)/(tf + k1*(1-b+b*dl/avgdl)); solve for df
        k1, b = 1.2, 0.75
        if stats == "global":
            mask = np.ones(ix.N, bool)
        elif stats == "visible":
            mask = acc
        else:
            mask = ix.partition == ix.partition[pos]
        n = mask.sum(); avgdl = ix.dl[mask].mean(); dl = ix.dl[pos]; tf = 1.0
        idf = score / (tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl)))
        # idf = ln(1 + (n-df+.5)/(df+.5)) -> df = (n+1)/(e^idf) - 0.5 ... solve exactly
        e = np.exp(idf) - 1
        return (n + 0.5 - 0.5 * e) / (1 + e)

    ix0 = build([])
    out = {"attacker": attacker, "candidates": []}
    for c in candidates:
        tid = ix0.vocab.get(tokenize(c)[0])
        true_total = 0 if tid is None else int((ix0.tf_csc.getcol(tid).toarray().ravel() > 0).sum())
        pos = ix0.pos[f"probe_{candidates.index(c)}"]
        acc = np.array([p in vis_parts for p in ix0.partition])
        visible_df = 0 if tid is None else int(((ix0.tf_csc.getcol(tid).toarray().ravel() > 0) & acc).sum())
        row = dict(term=c, true_df_all=true_total, true_df_visible=visible_df, true_df_hidden=true_total - visible_df)
        for stats in ("global", "visible", "partition"):
            sc, a = probe(ix0, c, stats)
            row[f"est_df_{stats}"] = round(float(invert_df(ix0, sc, stats, a, pos)), 2)
        out["candidates"].append(row)
    # controlled insertion: add M hidden docs containing a fresh rare term; watch the visible doc's score
    rare = "zzqprobe"
    deltas = []
    for M in (0, 1, 5, 20):
        hidden = [dict(id=f"hid_{j}", type="note", partition="owner", scope="finance/investments", title="",
                       text=f"private memo {rare} figures", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[]) for j in range(M)]
        ix = build(hidden)
        row = dict(hidden_docs=M)
        for stats in ("global", "visible", "partition"):
            sc, a = probe(ix, rare, stats)
            row[stats] = float(sc)
        # rank flip demo: two visible docs, A has rare term, B has "grinder"; query "zzqprobe grinder"
        deltas.append(row)
    base = deltas[0]
    for r in deltas:
        for stats in ("global", "visible", "partition"):
            r[f"delta_{stats}"] = r[stats] - base[stats]
    out["insertion"] = deltas
    # rank flip demonstration
    flip = []
    docA = dict(id="visA", type="note", partition="biz/cafe", scope="business/cafe/ops", title="", text=f"{rare} delivery note", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[])
    docB = dict(id="visB", type="note", partition="biz/cafe", scope="business/cafe/ops", title="", text="kombuchaqq delivery note", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[])
    for M in (0, 3, 10):
        hidden = [dict(id=f"hid_{j}", type="note", partition="owner", scope="finance/investments", title="",
                       text=f"private {rare}", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[]) for j in range(M)]
        hidden += [dict(id=f"vhB_{j}", type="note", partition="biz/cafe", scope="business/cafe/ops", title="", text="kombuchaqq", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[]) for j in range(2)]
        ix = Index(base_items + [docA, docB] + hidden, with_origin=True, lsa_dim=8)
        acc = np.array([p in vis_parts for p in ix.partition])
        row = dict(hidden_docs=M)
        for stats in ("global", "visible", "partition"):
            sc = ix.bm25(f"{rare} kombuchaqq") if stats == "global" else (ix.bm25(f"{rare} kombuchaqq", stats_mask=acc) if stats == "visible" else ix.bm25(f"{rare} kombuchaqq", per_partition=True))
            row[stats] = "A>B" if sc[ix.pos["visA"]] > sc[ix.pos["visB"]] else "B>A"
        flip.append(row)
    out["rank_flip"] = flip
    return out


# =========================================================================== E5 graph expansion
def e5_graph(w: World, brain: Brain, s: Searcher):
    tasks = eval_tasks(w)
    ent_items = defaultdict(list)
    for i, it in enumerate(brain.ix.items):
        for e in it.get("entities", []):
            ent_items[e].append(i)
    deg = {e: len(v) for e, v in ent_items.items()}
    nbr = defaultdict(list)
    for e in w.edges:
        nbr[e["src"]].append((e["dst"], e["partition"]))
        nbr[e["dst"]].append((e["src"], e["partition"]))
    HUB = 150  # do not expand through hub entities (e.g. a whole business); standard practice

    def expand(t, seeds, hops, acl, temporal=False):
        acc = brain.access(t["requester"])
        parts = set(w.identities[t["requester"]]["partitions"])
        frontier = set()
        for i in seeds:
            for e in brain.ix.items[i].get("entities", []):
                if deg.get(e, 0) <= HUB:
                    frontier.add(e)
        seen = set(frontier)
        for _ in range(hops):
            nxt = set()
            for e in frontier:
                for (d, p) in nbr[e]:
                    if acl and p not in parts:
                        continue
                    if acl and not (set(w.entities[d]["partitions"]) & parts):
                        continue
                    if d not in seen and deg.get(d, 0) <= HUB:
                        nxt.add(d)
            seen |= nxt
            frontier = nxt
        bm, ls = s.raw(t["query"], t["requester"])
        cand = set()
        for e in seen:
            for i in ent_items[e]:
                if brain.is_super[i] and not temporal:
                    continue
                if acl and not acc[i]:
                    continue
                cand.add(i)
        cand = list(cand)
        bmax = bm.max() if bm.size else 0.0
        cand.sort(key=lambda i: -(bm[i] / (bmax + 1e-9) + ls[i]))
        return cand[:DEPTH]

    def arm(hops, acl, mode="reserve"):
        """mode='reserve': top (K-R) from search + R best expansion items not already present (R=3).
        mode='rrf': RRF(search, expansion) with equal weights."""
        R = 3
        def f(t):
            temporal = is_temporal_query(t["query"])
            m = brain.live_mask(t["requester"], "keyed", temporal)
            first = s.rank(t["query"], t["requester"], m, n=DEPTH)
            if hops == 0:
                ranked = first
            else:
                ex = expand(t, first[:5], hops, acl, temporal)
                if mode == "rrf":
                    sc = rrf([np.array(first), np.array(ex, dtype=int)], brain.N, weights=[1.0, 1.0])
                    ranked = list(topn(sc, sc > 0, K + 10))
                else:
                    head = brain.forward(first, temporal)[:K - R]
                    extra = [i for i in brain.forward(ex, temporal) if i not in head][:R]
                    ranked = head + extra + [i for i in first if i not in head and i not in extra]
            ranked = brain.forward(ranked, temporal)[:K]
            leaks = [i for i in ranked if not brain.access(t["requester"])[i]]
            canary = [i for i in leaks if brain.ix.items[i]["type"] == "canary"]
            return ids_of(brain, ranked), dict(leak=len(leaks) > 0, nleak=len(leaks), canary=len(canary) > 0)
        return f

    out = {"arms": {}, "leak": {}}
    ARMS = (("no graph", 0, True, "reserve"),
            ("1-hop, per-hop ACL, 3 reserved slots", 1, True, "reserve"), ("2-hop, per-hop ACL, 3 reserved slots", 2, True, "reserve"),
            ("1-hop, per-hop ACL, RRF w=1", 1, True, "rrf"), ("2-hop, per-hop ACL, RRF w=1", 2, True, "rrf"),
            ("1-hop, NO per-hop ACL, 3 reserved slots", 1, False, "reserve"), ("2-hop, NO per-hop ACL, 3 reserved slots", 2, False, "reserve"),
            ("2-hop, NO per-hop ACL, RRF w=1", 2, False, "rrf"))
    for name, hops, acl, mode in ARMS:
        rows = run_rows(tasks, arm(hops, acl, mode))
        out["arms"][name] = summarise(rows)
        out.setdefault("rows", {})[name] = [r["ok"] for r in rows]
        nl = sum(r["leak"] for r in rows)
        out["leak"][name] = dict(tasks=len(rows), tasks_with_leak=nl, leaked_items=sum(r["nleak"] for r in rows),
                                 canary_tasks=sum(r["canary"] for r in rows),
                                 by_requester_tier=dict(Counter(w.identities[t["requester"]]["tier"] for t, r in zip(tasks, rows) if r["leak"])))
    # Canary monitor: every non-owner identity probes with every canary's anchor-entity names (realistic queries)
    mon = {}
    canaries = [it for it in brain.ix.items if it["type"] == "canary"]
    for name, hops, acl, mode in ARMS:
        alarms, probes = 0, 0
        planted_leaks = 0
        for ident in w.identities:
            if ident == "owner":
                continue
            for c in canaries:
                if brain.access(ident)[brain.pos[c["id"]]]:
                    continue
                for e in c["entities"]:
                    q = f"anything new about {w.entities[e]['name']}?"
                    t = dict(query=q, requester=ident, required=[c["id"]])
                    ids, ex = arm(hops, acl, mode)(t)
                    probes += 1
                    if c["id"] in ids or ex["canary"]:
                        alarms += 1
        mon[name] = dict(probes=probes, alarms=alarms)
    out["canary_monitor"] = mon
    out["order"] = [t["id"] for t in tasks]
    return out


# =========================================================================== E7 coverage packing
def e7_packing(w: World, brain: Brain, s: Searcher):
    tasks = eval_tasks(w)
    ent_df = Counter(e for it in brain.ix.items for e in it.get("entities", []))
    N = brain.N

    def facets(i):
        it = brain.ix.items[i]
        f = {}
        for e in it.get("entities", []):
            f["e:" + e] = float(np.log(N / (1 + ent_df[e])))
        if it.get("key"):
            f["k:" + it["key"].split(".")[-1]] = 1.0
        f["s:" + str(it.get("scope"))] = 0.5
        f["q:" + str(it["created_day"] // 91)] = 0.3
        f["t:" + it["type"]] = 0.3
        return f

    def pool(t, n=100):
        temporal = is_temporal_query(t["query"])
        m = brain.live_mask(t["requester"], "keyed", temporal)
        fs = s.fused(t["query"], t["requester"], m)
        idx = list(topn(fs, np.isfinite(fs), n))
        idx = brain.forward(idx, temporal)
        rel = np.array([fs[i] if np.isfinite(fs[i]) else 0 for i in idx])
        if rel.size and rel.max() > 0:
            rel = rel / rel.max()
        return idx, rel

    def topk(t, k):
        idx, _ = pool(t, max(100, k))
        return idx[:k]

    def mmr(t, k, lam=0.7):
        idx, rel = pool(t)
        V = brain.ix.lsa[idx]
        chosen = []
        rest = list(range(len(idx)))
        while rest and len(chosen) < k:
            if not chosen:
                j = rest[0]
            else:
                sim = V[rest] @ V[chosen].T
                sc = lam * rel[rest] - (1 - lam) * sim.max(axis=1)
                j = rest[int(np.argmax(sc))]
            chosen.append(j); rest.remove(j)
        return [idx[j] for j in chosen]

    def cover(t, k, lam=0.5):
        idx, rel = pool(t)
        F = [facets(i) for i in idx]
        got = set()
        chosen, rest = [], list(range(len(idx)))
        norm = max(1e-9, max((sum(f.values()) for f in F), default=1))
        while rest and len(chosen) < k:
            best, bj = -1e9, None
            for j in rest:
                gain = sum(v for fk, v in F[j].items() if fk not in got) / norm
                sc = rel[j] + lam * gain
                if sc > best:
                    best, bj = sc, j
            chosen.append(bj); rest.remove(bj); got |= set(F[bj])
        return [idx[j] for j in chosen]

    out = {"arms": {}, "by_size": {}, "rows": {}}
    for name, fn in (("top-k", lambda t: topk(t, K)), ("MMR (lambda=0.7, LSA sim)", lambda t: mmr(t, K)),
                     ("coverage packing (lambda=0.5)", lambda t: cover(t, K)),
                     ("coverage packing (lambda=0.25)", lambda t: cover(t, K, 0.25)),
                     ("coverage packing (lambda=1.0)", lambda t: cover(t, K, 1.0))):
        rows = run_rows(tasks, lambda t, fn=fn: (ids_of(brain, fn(t)), {}))
        out["arms"][name] = summarise(rows)
        out["rows"][name] = [r["ok"] for r in rows]
    # CR@k by required-set size for k in {10,20,30}
    for k in (10, 20, 30):
        for name, fn in (("top-k", lambda t, k=k: topk(t, k)), ("coverage(0.5)", lambda t, k=k: cover(t, k))):
            agg = defaultdict(lambda: [0, 0])
            for t in tasks:
                ids = ids_of(brain, fn(t))
                ok, _ = cr_at_k(ids, t["required"], k)
                b = t["size"] if t["size"] <= 7 else 8
                agg[b][0] += int(ok); agg[b][1] += 1
            out["by_size"][f"{name} @k={k}"] = {str(sz): v for sz, v in sorted(agg.items())}
    out["order"] = [t["id"] for t in tasks]
    return out


def e7_by_size_best(w: World, brain: Brain, s: Searcher):
    """H9 on the strongest E3 pipeline (cards + static slots + query) for k in {10,20,30}."""
    L = Linker(w)
    cards, covers, card_of = build_cards(w)
    bc = Brain(w, extra_docs=cards)
    sc = Searcher(bc)
    tasks = eval_tasks(w)
    out = {}
    for k in (10, 20, 30):
        agg = defaultdict(lambda: [0, 0])
        cls_agg = defaultdict(lambda: [0, 0])
        for t in tasks:
            ents = L.link(t["query"], t["requester"])
            pre = []
            for eid in ents:
                for cid in card_of.get(eid, []):
                    if bc.access(t["requester"])[bc.pos[cid]] and len(pre) < 3:
                        pre.append(bc.pos[cid])
            for kk in HAND_SLOTS[t["declared_scope"]]["static"]:
                h = w.keys[kk]["versions"][-1]
                if bc.access(t["requester"])[bc.pos[h]] and len(pre) < 5 and not any(h in covers.get(bc.ids[p], ()) for p in pre):
                    pre.append(bc.pos[h])
            temporal = is_temporal_query(t["query"])
            m = bc.live_mask(t["requester"], "keyed", temporal)
            ranked = bc.forward(sc.rank(t["query"], t["requester"], m, n=k + 30), temporal)
            fin = list(pre)
            for i in ranked:
                if len(fin) >= k:
                    break
                if i not in fin:
                    fin.append(i)
            ok, _ = cr_at_k(ids_of(bc, fin), t["required"], k, covers)
            b = t["size"] if t["size"] <= 7 else 8
            agg[b][0] += int(ok); agg[b][1] += 1
            cls_agg[t["cls"]][0] += int(ok); cls_agg[t["cls"]][1] += 1
        out[f"k={k}"] = dict(by_size={str(sz): v for sz, v in sorted(agg.items())}, by_class={c: v for c, v in sorted(cls_agg.items())})
    return out


# =========================================================================== I8 origin context
def i8_origin(w: World, brain_with: Brain, s_with: Searcher):
    tasks = [t for t in w.tasks if t["cls"] == "multimodal"]
    b0 = Brain(w, with_origin=False)
    s0 = Searcher(b0)
    oo = {t["id"]: any(w.by_id[r].get("media", {}).get("origin_only") for r in t["required"]) for t in tasks}
    out = {}
    for name, bb, ss in (("without origin context", b0, s0), ("with origin context (I8)", brain_with, s_with)):
        for meth in ("rrf", "bm25"):
            ss2 = Searcher(bb, method=meth)
            rows = run_rows(tasks, lambda t: (ids_of(bb, ss2.rank(t["query"], t["requester"], bb.live_mask(t["requester"]))), {}))
            for r in rows:
                r["sub"] = "needs origin-only item" if oo[r["id"]] else "caption sufficient"
            res = summarise(rows)
            res_sub = summarise(rows, by="sub")
            out[f"{name} [{meth}]"] = dict(all=res["multimodal"], **{k: v for k, v in res_sub.items() if k != "ALL"},
                                           rows=[r["ok"] for r in rows])
    return out


# =========================================================================== E0 diagnostic: where do required items rank?
def e0_depth(w: World, brain: Brain, s: Searcher):
    """Per class: share of required items found at depth d (item recall@d) and CR@d for d in 10..200.
    Tells us whether failures are ranking problems (items in the pool) or candidate-generation problems."""
    tasks = eval_tasks(w)
    depths = (10, 20, 50, 100, 200)
    agg = defaultdict(lambda: {d: [0, 0, 0, 0] for d in depths})
    for t in tasks:
        temporal = is_temporal_query(t["query"])
        m = brain.live_mask(t["requester"], "keyed", temporal)
        ranked = ids_of(brain, brain.forward(s.rank(t["query"], t["requester"], m, n=max(depths)), temporal))
        for d in depths:
            got = set(ranked[:d]) & set(t["required"])
            a = agg[t["cls"]][d]
            a[0] += len(got); a[1] += len(set(t["required"])); a[2] += int(len(got) == len(set(t["required"]))); a[3] += 1
    return {c: {str(d): dict(item_recall=v[0] / v[1], cr=v[2] / v[3], n=v[3]) for d, v in dd.items()} for c, dd in agg.items()}


# =========================================================================== robustness: BM25-only base
def robustness_bm25(w: World, brain: Brain):
    """Re-run the headline arms of E2, E3, E5, E7 with BM25 as the only first-stage retriever."""
    sb = Searcher(brain, method="bm25")
    out = {}
    e2 = e2_scope(w, brain, sb)
    out["E2"] = {k: e2["arms"][k] for k in ("none (access filter only)", "declared: hard filter", "declared: boost (RRF w=1)", "trail (noise 0.3): boost")}
    e3 = e3_assembly(w, brain, sb)
    out["E3"] = {k: e3["arms"][k] for k in ("query-only top-10", "query + mention->head forwarding (new)", "packet(5) + query(5)",
                                            "hand slot contract(<=5) + query", "entity cards(<=3, pinned) + query (cards indexed)",
                                            "cards(<=3) + hand static slots (<=5 total) + query")}
    e7 = e7_packing(w, brain, sb)
    out["E7"] = {k: e7["arms"][k] for k in ("top-k", "MMR (lambda=0.7, LSA sim)", "coverage packing (lambda=0.5)")}
    e5 = e5_graph(w, brain, sb)
    out["E5"] = {k: e5["arms"][k] for k in ("no graph", "1-hop, per-hop ACL, RRF w=1", "2-hop, per-hop ACL, RRF w=1")}
    out["E5_leak"] = {k: e5["leak"][k] for k in e5["leak"]}
    return out
