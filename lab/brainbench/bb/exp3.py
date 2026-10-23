"""Batch 3 analysis stages (free): E9, E10/E10b, H17 aggregation, I15, ADR checks, E11; paid small stages fab, escr.
Each stage checkpoints its rows to results_v03/<stage>.pkl (per seed) so an OOM kill or restart resumes."""
from __future__ import annotations

import gc
import json
import os
import random
import re
from collections import Counter, defaultdict

import numpy as np

from .common import NOW_DAY, ROOT
from . import gate3
from .pipe3 import (CLASSES_NEW, CLASSES_V2, EMB, KS, TARGET5, TS, Brain3, Gate, World3, rate, sign_test)

OUT = os.path.join(ROOT, "results_v03")
EVAL_CLASSES = CLASSES_V2 + CLASSES_NEW


def load_gate_obj(w, name):
    if name == "gold":
        return Gate.gold(w)
    if name == "code":
        L, R = gate3.code_gate(w)
        return Gate("code", L, R)
    d = gate3.load_gate(name, w.seed)
    if d is None:
        return None
    return Gate(name, d["links"], d["records"], [tuple(a) for a in d["aliases"]], d["entries"])


def alias_table(gate):
    return [(p, e) for p, e, *_ in (gate.aliases or [])]


def run_arm(b, tasks, arm, seed, name, maxk=100, maxt=8000):
    rows = []
    for t in tasks:
        ctx = b.assemble(t, arm, maxk=maxk, maxt=maxt)
        r = b.score(t, ctx)
        r.update(seed=seed, arm=name)
        rows.append(r)
    return rows


def reach(b, w, tasks):
    """Share of VITAL non-connector items reachable through structure for each task: linked by the gate to an entity the query
    linker finds, or stated correctly on a card of such an entity."""
    out = []
    for t in tasks:
        vis = w.visible(t["requester"])
        ents = set(b.link_query(t["query"], t["requester"], vis))
        cover = set()
        for e in ents:
            for cid in b.card_of.get(e, []):
                cover |= b.card_cover.get(cid, set())
        pents = ents | {p for e in ents for p in b.parents_of(e)}
        n = hit = hitp = 0
        for v in t["vital"]:
            if w.by_id[v].get("connector"):
                continue
            n += 1
            h = bool(set(b.links.get(v, [])) & ents) or v in cover
            hit += h
            hitp += h or bool(set(b.links.get(v, [])) & pents)
        if n:
            out.append(dict(cls=t["cls"], set_id=t["set_id"], seed=w.seed, n=n, hit=hit, hit_par=hitp, reach=hit / n, form=t.get("ref_form")))
    return out


E9_ARMS = {
    "A0 query-only": ("none", dict(prefix="none")),
    "A1 router (batch-2 best, no gate)": ("none", dict(prefix="router")),
    "A2 code gate + nbhd": ("code", dict(prefix="router", nbhd=True, nbhd_router=True)),
    "A3 haiku gate + nbhd (typed first)": ("gate_haiku", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True)),
    "A3c haiku gate, cards only": ("gate_haiku", dict(prefix="router")),
    "A3u haiku gate + nbhd (query order)": ("gate_haiku", dict(prefix="router", nbhd=True, nbhd_router=True)),
    "A4 sonnet gate + nbhd (typed first)": ("gate_sonnet", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True)),
    "A4c sonnet gate, cards only": ("gate_sonnet", dict(prefix="router")),
    "A5 gold gate + nbhd (typed first)": ("gold", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True)),
    "A5c gold gate, cards only": ("gold", dict(prefix="router")),
    # exploratory (not preregistered): PM13-style declared mapping — permission questions pin the space's constraint records
    "X3r haiku gate + nbhd + rule pin (exploratory)": ("gate_haiku", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True, rule_pin=True)),
    "X5r gold gate + nbhd + rule pin (exploratory)": ("gold", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True, rule_pin=True)),
    # exploratory: parent-entity neighbourhood (decisions and policies live on the portfolio / company, requests name the child)
    "X3p haiku gate + nbhd + parents (exploratory)": ("gate_haiku", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True, parents=True)),
    "X5p gold gate + nbhd + parents (exploratory)": ("gold", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True, parents=True)),
}


def stage_e9(seeds, log=print, save=None, load=None):
    st = load("e9") or dict(rows={}, quality={}, reach={}, store={})
    for s in seeds:
        w = World3(s)
        tasks = [t for t in w.tasks if t["cls"] in EVAL_CLASSES]
        EMB.prefetch_queries([t["query"] for t in tasks])
        gates = {}
        for gname in sorted({g for g, _ in E9_ARMS.values()}):
            if gname == "none":
                continue
            g = load_gate_obj(w, gname)
            if g is not None:
                gates[gname] = g
                req_ids = {v for t in tasks for v in t["required"]}
                q = gate3.quality(w, g.links, g.records, required_ids=req_ids)
                st["quality"][(s, gname)] = q
        brains = {}
        for name, (gname, arm) in E9_ARMS.items():
            if (s, name) in st["rows"]:
                continue
            if name.startswith("X") and s != 1 and not os.environ.get("BB3_X_ALL"):
                continue          # exploratory arms: seed 1 only (CPU budget); confirm in a later batch
            if gname != "none" and gname not in gates:
                continue
            if gname not in brains:
                gc.collect()
                g = gates.get(gname)
                brains = {gname: Brain3(w, g, alias_table=alias_table(g) if g else None)}
                b = brains[gname]
                st["store"][(s, gname)] = dict(n_fact=b.store["n_fact"], n_ok=b.store["n_ok"], keys=len(b.store["keys"]))
                if g is not None:
                    st["reach"][(s, gname)] = reach(b, w, [t for t in tasks if t["cls"] in TARGET5])
            st["rows"][(s, name)] = run_arm(brains[gname], tasks, arm, s, name)
            log(f"[e9] s{s} {name}: done")
            save("e9", st)
        brains = None
        gc.collect()
    save("e9", st)
    EMB.save()
    return st


# ============================================================================ E10 / E10b: double entry
def entries_for(w, gate, mode, filt_thr=None, learned=None):
    """mode: header | scribe | scribe_f | header+scribe_f | header+values"""
    out = {}
    learned = learned or defaultdict(list)
    for iid, es in gate.links.items():
        parts = []
        if "header" in mode:
            for e in es:
                ent = w.entities.get(e)
                if ent:
                    parts += ent["aliases"] + learned.get(e, [])
        if "scribe" in mode:
            ks = gate.entries.get(iid, []) if gate.entries else []
            if mode.endswith("scribe_f") and filt_thr is not None:
                ks = [k for k in ks if filt_thr.get((iid, k), 1.0) >= filt_thr["_thr"]]
            parts += ks
        if "values" in mode:
            parts += [r["v"] for r in gate.records.get(iid, []) if r.get("t") == "fact" and r.get("v")]
        if parts:
            out[iid] = " | ".join(dict.fromkeys(parts))
    return out


def scribe_filter_scores(w, gate):
    """Doc2Query-- style filter: cosine(item text, phrase) with bge-small; threshold = 30th percentile over the seed."""
    pairs = [(iid, k) for iid, ks in (gate.entries or {}).items() for k in ks]
    if not pairs:
        return {"_thr": 0.0}
    from .pipe3 import ctx_text
    items = sorted({p[0] for p in pairs})
    iv = dict(zip(items, EMB.docs([ctx_text(w.by_id[i]) for i in items])))
    phr = sorted({p[1] for p in pairs})
    pv = dict(zip(phr, EMB.docs(phr)))
    sc = {(i, k): float(iv[i] @ pv[k]) for i, k in pairs}
    thr = float(np.percentile(list(sc.values()), 30))
    sc["_thr"] = thr
    EMB.save()
    return sc


def stale_rows(b, w, seed, name, arm):
    rows = []
    for t in w.tasks:
        if t["cls"] != "stale_probe":
            continue
        ctx = b.assemble(t, arm, maxk=10, maxt=0)[:10]
        ids = [b.ix.ids[p] for p in ctx]
        got = set()
        cur_rank = None
        for n, p in enumerate(ctx):
            did = b.ix.ids[p]
            got.add(did); got |= b.card_cover.get(did, set())
            if cur_rank is None and t["vital"][0] in got:
                cur_rank = n
        bad = set(t.get("stale_ids", [])) | set(t.get("trap_ids", []))
        st_rank = next((n for n, i in enumerate(ids) if i in bad), None)
        exposed = st_rank is not None and (cur_rank is None or st_rank < cur_rank)
        rows.append(dict(seed=seed, arm=name, id=t["id"], set_id=t["set_id"], cls="stale_probe", pair_id=t.get("pair_id"), exposed=exposed,
                         current_found=cur_rank is not None, unresolved=st_rank is not None and cur_rank is None, ref_form=t.get("ref_form")))
    return rows


E10_MODES = ["raw", "header", "scribe", "scribe_f", "header+scribe_f", "header+values"]


def stage_e10(seeds, log=print, save=None, load=None, gate_name="gate_haiku"):
    st = load("e10") or dict(rows={}, stale={}, filt={})
    for s in seeds:
        w = World3(s)
        g = load_gate_obj(w, gate_name)
        if g is None:
            log(f"[e10] s{s}: no {gate_name}; skipped")
            continue
        tasks = [t for t in w.tasks if t["cls"] in EVAL_CLASSES]
        EMB.prefetch_queries([t["query"] for t in w.tasks])
        learned = defaultdict(list)
        for p, e, *_ in g.aliases:
            learned[e].append(p)
        filt = scribe_filter_scores(w, g)
        st["filt"][s] = dict(thr=filt["_thr"], n=len(filt) - 1)
        for mode in E10_MODES:
            if (s, mode, "A3") in st["rows"]:
                continue
            ent = None if mode == "raw" else entries_for(w, g, mode, filt, learned)
            gc.collect()
            b = Brain3(w, g, entries=ent, alias_table=alias_table(g))
            for qname, arm in (("A0", dict(prefix="none")), ("A3", dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True))):
                st["rows"][(s, mode, qname)] = run_arm(b, tasks, arm, s, f"{mode}/{qname}")
                st["stale"][(s, mode, qname)] = stale_rows(b, w, s, f"{mode}/{qname}", arm)
            log(f"[e10] s{s} {mode}: done")
            save("e10", st)
            b = None
        EMB.save()
    save("e10", st)
    return st


# ============================================================================ H17 aggregation: records vs top-k
AGG_CUES = [("issue", r"\b(problem|problems|issue|issues|incident|incidents|repair|repairs|maintenance|variation|variations|cost change)"),
            ("offer", r"\b(quote|quotes|invoice|invoices|price|prices|offer|offers|tender|tenders|invitation)"),
            ("constraint", r"\b(resolution|resolutions|rule|rules|policy|policies)"),
            ("decision", r"\b(decision|decisions|decided)"),
            ("plan", r"\b(commitment|commitments|action item|actions|receipt)"),
            ("fact", r"\b(check-in|check-ins|review|reviews|receipt|notes)")]
GOLD2T = {"issue": "issue", "quote": "offer", "rule": "constraint", "decision": "decision", "plan": "plan", "fact": "fact", "preference": "preference"}


def agg_parse(q):
    ql = q.lower()
    ts = [t for t, rx in AGG_CUES if re.search(rx, ql)]
    return ts or ["any"]


def agg_records(b, w, t, gate):
    """Deterministic spec: record types from cue words; entity from the query linker; else every visible space.
    Returns the set of item ids whose gate records match."""
    vis = w.visible(t["requester"])
    ents = b.link_query(t["query"], t["requester"], vis)
    types = agg_parse(t["query"])
    person = re.search(r"\b(?:item|items) ([A-Z][a-z]+) has been given|of ([A-Z][a-z]+)'s actions|action item ([A-Z][a-z]+)", t["query"])
    out = []
    for iid, rr in gate.records.items():
        it = w.by_id.get(iid)
        if it is None or it["space"] not in vis or it.get("connector") or it.get("media"):
            continue
        if ents and not (set(gate.links.get(iid, [])) & set(ents)):
            continue
        if types != ["any"] and not any(r.get("t") in types for r in rr):
            continue
        if types == ["any"] and not rr:
            continue
        out.append(iid)
    return out


def stage_agg(seeds, log=print, save=None, load=None):
    st = load("agg") or dict(rows={})
    for s in seeds:
        w = World3(s)
        tasks = [t for t in w.tasks if t["cls"] == "aggregation"]
        EMB.prefetch_queries([t["query"] for t in tasks])
        for gname in ("gold", "code", "gate_haiku", "gate_sonnet"):
            if (s, gname) in st["rows"]:
                continue
            g = load_gate_obj(w, gname)
            if g is None:
                continue
            gold_like = Gate("goldT", g.links, {iid: [dict(r, t=GOLD2T.get(r["t"], r["t"])) for r in rr] for iid, rr in g.records.items()}) if gname == "gold" else g
            b = Brain3(w, g, alias_table=alias_table(g), embed=True)
            rows = []
            for t in tasks:
                pred = set(agg_records(b, w, t, gold_like))
                vital = set(t["vital"])
                ctx = b.assemble(t, dict(prefix="none"), maxk=100, maxt=0)
                ids = [b.ix.ids[p] for p in ctx]
                r = dict(seed=s, set_id=t["set_id"], cls="aggregation", id=t["id"], absence=bool(t.get("absence")), n=len(vital), npred=len(pred),
                         rec_exact=(vital <= pred) if vital else (len(pred) == 0), recall=len(vital & pred) / len(vital) if vital else float(len(pred) == 0),
                         precision=len(vital & pred) / len(pred) if pred else float(not vital))
                for k in KS:
                    r[f"topk@{k}"] = vital <= set(ids[:k]) if vital else False
                rows.append(r)
            st["rows"][(s, gname)] = rows
            log(f"[agg] s{s} {gname}: done")
            save("agg", st)
    save("agg", st)
    return st


# ============================================================================ I15 certified recall (worst-vital-item conformal)
def stage_i15(seeds, log=print, save=None, load=None, gate_name="gate_haiku"):
    st = load("i15") or dict(rows={})
    for s in seeds:
        if (s, gate_name) in st["rows"]:
            continue
        w = World3(s)
        g = load_gate_obj(w, gate_name)
        if g is None:
            continue
        tasks = [t for t in w.tasks if t["cls"] in EVAL_CLASSES]
        EMB.prefetch_queries([t["query"] for t in tasks])
        b = Brain3(w, g, alias_table=alias_table(g))
        arm = dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True)
        st["rows"][(s, gate_name)] = run_arm(b, tasks, arm, s, "i15", maxk=400, maxt=10 ** 9)
        log(f"[i15] s{s}: done")
        save("i15", st)
        b = None; gc.collect()
    return st


def conformal(rows_cal, rows_test, key, alpha=0.10):
    """Split conformal on the worst-vital-item score (one task per distinct set in calibration). None = unreachable (inf)."""
    def first_per_set(rows):
        d = {}
        for r in rows:
            d.setdefault((r["seed"], r["set_id"]), r)
        return list(d.values())
    cal = [r[key] if r[key] is not None else float("inf") for r in first_per_set(rows_cal)]
    n = len(cal)
    if n == 0:
        return None
    kq = int(np.ceil((n + 1) * (1 - alpha)))
    thr = float("inf") if kq > n else sorted(cal)[kq - 1]
    test = first_per_set(rows_test)
    cov = [1.0 if (r[key] is not None and r[key] <= thr) else 0.0 for r in test]
    return dict(thr=thr, n_cal=n, n_test=len(test), coverage=float(np.mean(cov)) if cov else float("nan"), k=int(sum(cov)))


def clopper_lower(k, n, conf=0.95):
    from scipy.stats import beta
    if n == 0:
        return float("nan")
    return 0.0 if k == 0 else float(beta.ppf(1 - conf, k, n - k + 1))


# ============================================================================ paid small stages
def stage_fab(seeds, log=print, save=None, load=None):
    from . import fab3
    st = load("fab")
    if st is None or not st.get("scores"):
        items, out, scores = fab3.run(1, log=log)
        st = dict(items=items, out={f"{m}/{s}": v for (m, s), v in out.items()}, scores=scores)
        save("fab", st)
    for k, v in st["scores"].items():
        log(f"[fab] {k}: {v}")
    return st


def stage_escr(seeds, log=print, save=None, load=None):
    from . import escr3
    st = load("escr") or {}
    if "entries" not in st:
        sel, out = escr3.run_writers(1, log=log)
        st = dict(sel=sel, entries=out)
        save("escr", st)
    w = World3(1)
    st["analysis"], st["seeded"] = {}, {}
    for model, entries in st["entries"].items():
        st["analysis"][model] = escr3.analyse(w, st["sel"], entries, model, log=log)
        st["seeded"][model] = escr3.seeded_errors(w, entries, model, log=log)
        log(f"[escr] {model}: {st['analysis'][model]['metrics']}")
    st["spoof"] = escr3.spoof_probe(next(iter(st["entries"].values())))
    save("escr", st)
    return st


# ADR and E11 stages live in adr3.py / e11.py
def stage_adr(seeds, log=print, save=None, load=None):
    from . import adr3
    return adr3.run_all(seeds, log=log, save=save, load=load)


def stage_e11(seeds, log=print, save=None, load=None):
    from . import e11
    return e11.run(seeds, log=log, save=save, load=load)


def stage_report(seeds, log=print, save=None, load=None):
    from . import report3
    return report3.write(log=log, load=load)


# ============================================================================ release-safe drafting: recipient-intersection visibility
def stage_release(seeds, log=print, save=None, load=None, gate_name="gate_haiku"):
    """For release_safe tasks: context assembled under the requester's visibility vs under (requester ∩ recipient) visibility.
    Forbidden = the owner's private notes about the topic. Reports forbidden exposure and CR_vital."""
    st = load("release") or {}
    for s in seeds:
        w = World3(s)
        g = load_gate_obj(w, gate_name) or load_gate_obj(w, "code")
        tasks = [t for t in w.tasks if t["cls"] == "release_safe"]
        EMB.prefetch_queries([t["query"] for t in tasks])
        b = Brain3(w, g, alias_table=alias_table(g))
        arm = dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True)
        for mode in ("requester", "intersection"):
            if (s, mode) in st:
                continue
            rows = []
            for t in tasks:
                sp = None
                if mode == "intersection":
                    sp = frozenset(w.visible(t["requester"]) & w.visible(t["recipient"]))
                ctx = b.assemble(t, arm, spaces=sp)
                r = b.score(t, ctx)
                r.update(seed=s, arm=mode, gate=g.name)
                rows.append(r)
            st[(s, mode)] = rows
            log(f"[release] s{s} {mode}: forbidden@10 {np.mean([r['forbid@10'] for r in rows]):.2f} @50 {np.mean([r['forbid@50'] for r in rows]):.2f}")
        save("release", st)
    return st


def stage_reach(seeds, log=print, save=None, load=None):
    """Recompute structure reach (incl. parent entities) for every available gate; no embeddings needed."""
    st = load("e9")
    for s in seeds:
        w = World3(s)
        tasks = [t for t in w.tasks if t["cls"] in TARGET5]
        for gname in ("code", "gold", "gate_haiku", "gate_sonnet"):
            g = load_gate_obj(w, gname)
            if g is None:
                continue
            b = Brain3(w, g, alias_table=alias_table(g), embed=False)
            st["reach"][(s, gname)] = reach(b, w, tasks)
            log(f"[reach] s{s} {gname}: done")
    save("e9", st)
