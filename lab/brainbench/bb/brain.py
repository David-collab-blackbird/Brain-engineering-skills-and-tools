"""Evaluation core: loads the world, builds the index, applies access/scope masks, write-path
variants, forward-to-head, and computes CR@k_all.

Default store used by E2/E3/E5/E7 (stated in RESULTS.md):
  keyed upsert — only the head version of each keyed fact is in the live index; superseded
  versions live in a history partition that is searched only when the temporal router fires.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

import numpy as np

from .common import DATA_DIR, NOW_DAY, read_jsonl, wilson
from .retrieval import Index, Retriever, topn
from .tasks import SCOPE_GROUPS, scope_group

TEMPORAL_RE = re.compile(
    r"\b(chang\w*|before|history|trend\w*|since|over time|used to|compar\w*|every|progression|quarter by quarter|"
    r"originally|original|earlier|last year|a year ago|previous\w*|moved|shifted|in order|through the|walk me through|"
    r"show all|all of mila|versus last|before and after|who used to|first logged|first set|first wrote|bump\w*|gone up|grown|improved|"
    r"paid down|over each|across every|across the whole|each quarter|every quarter|tracked since)\b", re.I)


def is_temporal_query(q: str) -> bool:
    return bool(TEMPORAL_RE.search(q))


class World:
    def __init__(self, data_dir: str = DATA_DIR):
        self.items = read_jsonl(os.path.join(data_dir, "items.jsonl"))
        self.entities = {e["id"]: e for e in read_jsonl(os.path.join(data_dir, "entities.jsonl"))}
        self.edges = read_jsonl(os.path.join(data_dir, "edges.jsonl"))
        self.keys = {k["key"]: k for k in read_jsonl(os.path.join(data_dir, "keys.jsonl"))}
        self.tasks = read_jsonl(os.path.join(data_dir, "tasks.jsonl"))
        with open(os.path.join(data_dir, "meta.json")) as f:
            self.meta = json.load(f)
        self.identities = self.meta["identities"]
        self.by_id = {it["id"]: it for it in self.items}
        self.head_of = {}
        for k in self.keys.values():
            for v in k["versions"]:
                self.head_of[v] = k["versions"][-1]


class Brain:
    def __init__(self, world: World, with_origin: bool = True, extra_docs: list[dict] | None = None,
                 lsa_dim: int = 256):
        self.w = world
        self.ix = Index(world.items, with_origin=with_origin, extra_docs=extra_docs, lsa_dim=lsa_dim)
        items = self.ix.items
        self.N = self.ix.N
        self.ids = self.ix.ids
        self.pos = self.ix.pos
        self.is_fact = np.array([it["type"] == "fact" for it in items])
        self.is_super = np.array([it["type"] == "fact" and it.get("superseded_by") is not None for it in items])
        self.is_extra = np.array([it.get("derived", False) for it in items])
        self.sgroup = np.array([scope_group(it.get("scope")) or "none" for it in items])
        self.part = self.ix.partition
        self._acc = {}
        self.head_idx = np.array([self.pos.get(world.head_of.get(it["id"], it["id"]), i) for i, it in enumerate(items)])

    def access(self, identity: str) -> np.ndarray:
        if identity not in self._acc:
            allowed = set(self.w.identities[identity]["partitions"])
            self._acc[identity] = np.array([p in allowed for p in self.part])
        return self._acc[identity]

    def live_mask(self, identity: str, write_mode: str = "keyed", temporal: bool = False,
                  include_extra: bool = True) -> np.ndarray:
        m = self.access(identity).copy()
        if write_mode == "keyed" and not temporal:
            m &= ~self.is_super
        if not include_extra:
            m &= ~self.is_extra
        return m

    def scope_mask(self, group: str | None) -> np.ndarray:
        if group is None:
            return np.ones(self.N, dtype=bool)
        return self.sgroup == group

    def forward(self, ranked: list[int], temporal: bool) -> list[int]:
        """I3: replace superseded fact versions by their head (dedupe, keep first position)."""
        if temporal:
            return ranked
        out, seen = [], set()
        for i in ranked:
            j = int(self.head_idx[i]) if self.is_super[i] else i
            if j not in seen:
                seen.add(j)
                out.append(j)
        return out


# --------------------------------------------------------------------------- metrics
def covered(final_ids: list[str], required: list[str], covers: dict | None = None) -> set:
    got = set(final_ids)
    if covers:
        for i in final_ids:
            got |= covers.get(i, set())
    return got & set(required)


def cr_at_k(final_ids: list[str], required: list[str], k: int, covers=None) -> tuple[bool, float]:
    c = covered(final_ids[:k], required, covers)
    return len(c) == len(set(required)), len(c) / len(set(required))


def summarise(rows: list[dict], key="ok", by="cls") -> dict:
    agg = defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        a = agg[r[by]]
        a[0] += int(r[key]); a[1] += 1; a[2] += r.get("recall", 0.0)
    out = {}
    for c, (k, n, rs) in sorted(agg.items()):
        p, lo, hi = wilson(k, n)
        out[c] = dict(k=k, n=n, p=p, lo=lo, hi=hi, item_recall=rs / n if n else float("nan"))
    tot_k = sum(v["k"] for v in out.values()); tot_n = sum(v["n"] for v in out.values())
    p, lo, hi = wilson(tot_k, tot_n)
    out["ALL"] = dict(k=tot_k, n=tot_n, p=p, lo=lo, hi=hi,
                      item_recall=sum(r.get("recall", 0) for r in rows) / max(1, len(rows)))
    return out


CLASSES = ["decision_support", "option_analysis", "current_state", "temporal_change", "goal_tracking",
           "preference_recommendation", "cross_domain", "multimodal"]
