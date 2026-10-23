"""E11 / U2b: self-healing vocabulary over a simulated year (no LLM).

Stream per seed: 12 months x 50 requests. 70% use held-out reference forms (nicknames and descriptors that appear nowhere in
the corpus), drawn with replacement so phrases recur; 30% are control requests (registry form), used to count regressions.
After a miss on a held-out request the person corrects it with probability 0.5 ("no, I meant X"); 10% of corrections pick the
wrong entity. At month 6, 20% of the phrases change referent (drift). Assumption: the correction tells the system which
phrase was meant (a correction UI that asks "what do you call it?"); phrase extraction from free text is not tested.
Arms:
  none          no learning
  item-append   the phrase is appended to the searchable entry of the items the person picked (the task's vital items)
  entity-alias  (phrase -> entity, valid_from) added to the linker's alias table; a later correction of the same phrase
                supersedes the earlier one (time-scoped)
Metric: CR_vital@50 per month on held-out requests; regressions = control requests that pass under none but fail under the arm.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict

import numpy as np

from .pipe3 import EMB, Brain3, World3


def make_stream(w, R, months=12, per_month=50, p_held=0.7):
    held = [t for t in w.tasks if t.get("ref_form") in ("heldout_nick", "heldout_desc") and t.get("ref_used") and t["cls"] not in ("stale_probe",)]
    ctrl = [t for t in w.tasks if t.get("ref_form") == "registry" and t["cls"] not in ("stale_probe",)]
    # phrase -> tasks; drift: 20% of phrases switch at month 6 to tasks of another entity of the same kind, keeping the phrase
    by_phrase = defaultdict(list)
    for t in held:
        by_phrase[t["ref_used"][0][1]].append(t)
    phrases = sorted(by_phrase)
    drift = set(R.sample(phrases, max(1, int(0.2 * len(phrases)))))
    ent_tasks = defaultdict(list)
    for t in held:
        ent_tasks[t["ref_used"][0][0]].append(t)
    drift_to = {}
    for p in drift:
        e0 = by_phrase[p][0]["ref_used"][0][0]
        kind = w.entities[e0]["kind"]
        cands = [e for e in ent_tasks if e != e0 and w.entities[e]["kind"] == kind]
        if cands:
            drift_to[p] = R.choice(cands)
    stream = []
    for m in range(months):
        for _ in range(per_month):
            if R.random() < p_held:
                p = R.choice(phrases)
                if m >= 6 and p in drift_to:
                    t0 = R.choice(ent_tasks[drift_to[p]])
                    old = t0["ref_used"][0][1]
                    t = dict(t0, query=t0["query"].replace(old, p), ref_used=[(drift_to[p], p)])
                else:
                    t = R.choice(by_phrase[p])
                stream.append((m, "held", t))
            else:
                stream.append((m, "ctrl", R.choice(ctrl)))
    return stream, drift_to


class Learner:
    def __init__(self, b, mode):
        self.b, self.mode = b, mode
        self.alias = {}                    # phrase -> entity (latest correction wins: time scope)
        self.item_phr = defaultdict(set)   # item pos -> appended phrases
        self.corrections = 0

    def ctx(self, t):
        b = self.b
        b.alias_pats = self.base + [(p.lower(), e) for p, e in self.alias.items()]
        b.alias_pats.sort(key=lambda x: -len(x[0]))
        ctx = b.assemble(t, dict(prefix="router", nbhd=True, nbhd_router=True), maxk=60, maxt=0)
        if self.mode == "item-append" and self.item_phr:
            ql = t["query"].lower()
            vis = b.mask(t["requester"])
            pinned = [p for p, ph in self.item_phr.items() if vis[p] and any(x.lower() in ql for x in ph)]
            ctx = pinned + [p for p in ctx if p not in pinned]
        return ctx

    def correct(self, t, R, w):
        self.corrections += 1
        e, p = t["ref_used"][0]
        if R.random() < 0.10:      # wrong pick
            kind = w.entities[e]["kind"]
            e = R.choice([x for x in w.entities if w.entities[x]["kind"] == kind and x != e] or [e])
            items = [self.b.ix.pos[i] for i in self.b.ent_items_ids(e)[:3]] if hasattr(self.b, "ent_items_ids") else self.b.ent_items.get(e, [])[:3]
        else:
            items = [self.b.ix.pos[v] for v in t["vital"] if v in self.b.ix.pos]
        if self.mode == "entity-alias":
            self.alias[p] = e
        elif self.mode == "item-append":
            for it in items:
                self.item_phr[it].add(p)


def run(seeds, log=print, save=None, load=None, gate_name="gate_haiku"):
    from .exp3 import load_gate_obj, alias_table
    st = load("e11") or {}
    for s in seeds:
        if s in st:
            continue
        w = World3(s)
        g = load_gate_obj(w, gate_name) or load_gate_obj(w, "code")
        R0 = random.Random(1100 + s)
        stream, drift_to = make_stream(w, R0)
        EMB.prefetch_queries([t["query"] for _, _, t in stream])
        b = Brain3(w, g, alias_table=alias_table(g))
        base = list(b.alias_pats)
        res = {}
        for mode in ("none", "item-append", "entity-alias"):
            L = Learner(b, mode)
            L.base = base
            R = random.Random(2200 + s)
            rows = []
            for i, (m, kind, t) in enumerate(stream):
                ctx = L.ctx(t)
                r = b.score(t, ctx)
                ok = bool(r["v@50"])
                rows.append(dict(i=i, m=m, kind=kind, ok=ok, corrections=L.corrections, drifted=(m >= 6 and t["ref_used"] and t["ref_used"][0][1] in drift_to) if kind == "held" else False))
                if kind == "held" and not ok and R.random() < 0.5:
                    L.correct(t, R, w)
            res[mode] = rows
            log(f"[e11] s{s} {mode}: held CR {np.mean([r['ok'] for r in rows if r['kind']=='held']):.3f}, corrections {L.corrections}")
        b.alias_pats = base
        st[s] = dict(res=res, n_drift=len(drift_to))
        save("e11", st)
    return st
