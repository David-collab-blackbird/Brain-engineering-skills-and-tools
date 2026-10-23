"""Score GBrain runs on BrainBench v0.2 with the batch-2 metric (CR@k over distinct required sets, Wilson 95%),
paired against batch-2 arms on the same tasks (seed 1). Also: leak count, stale-probe metrics (E1 definitions).

python3 -I score.py <seed> <arm_name>=<run.jsonl>[:transform] ...      transform: raw | fwd | cards
"""
from __future__ import annotations

import json
import math
import os
import pickle
import re
import sys
from collections import defaultdict

import numpy as np

BB = "/home/claude/brainbench"
CLASSES = ["decision_support", "option_analysis", "current_state", "temporal_change", "goal_tracking",
           "preference_recommendation", "cross_domain", "multimodal"]
SHORT = dict(decision_support="decision", option_analysis="option", current_state="current", temporal_change="temporal",
             goal_tracking="goal", preference_recommendation="pref", cross_domain="cross", multimodal="multimodal")
TEMPORAL_RE = re.compile(
    r"\b(chang\w*|before|history|trend\w*|since|over time|used to|compar\w*|every|progression|quarter by quarter|"
    r"originally|original|earlier|last year|a year ago|previous\w*|moved|shifted|in order|through the|walk me through|"
    r"show all|all of mila|versus last|before and after|who used to|first logged|first set|first wrote|bump\w*|gone up|grown|improved|"
    r"paid down|over each|across every|across the whole|each quarter|every quarter|tracked since)\b", re.I)  # copied from bb/brain.py


def rj(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def wilson(k, n, z=1.959964):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(max(p * (1 - p), 0) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - hw), min(1.0, c + hw)


def per_set(rows, key):
    agg = defaultdict(list)
    for r in rows:
        agg[r["set_id"]].append(float(r[key]))
    return {k: float(np.mean(v)) for k, v in agg.items()}


def rate(rows, key):
    ps = per_set(rows, key)
    n = len(ps)
    p, lo, hi = wilson(sum(ps.values()), n)
    return p, lo, hi, n


def sign(rows_a, rows_b, key):
    a, b = per_set(rows_a, key), per_set(rows_b, key)
    ks = sorted(set(a) & set(b))
    d = np.array([b[k] - a[k] for k in ks])
    w, l = int((d > 1e-9).sum()), int((d < -1e-9).sum())
    n = w + l
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)
    rng = np.random.default_rng(0)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)] if len(d) else [float("nan")]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return w, l, p, 100 * float(d.mean()) if len(d) else float("nan"), 100 * lo, 100 * hi


class World:
    def __init__(self, seed):
        d = f"{BB}/data_v02/s{seed}"
        self.items = {it["id"]: it for it in rj(f"{d}/items.jsonl")}
        self.tasks = rj(f"{d}/tasks.jsonl")
        self.keys = rj(f"{d}/keys.jsonl")
        self.meta = json.load(open(f"{d}/meta.json"))
        self.head_of = {}
        for k in self.keys:
            for v in k["versions"]:
                self.head_of[v] = k["versions"][-1]
        self.superseded = {i for i, it in self.items.items() if it["type"] == "fact" and it.get("superseded_by")}
        self.cards = {}
        for k in self.keys:
            cid = f"card_{k['entity']}_{k['partition'].replace('/', '-')}"
            self.cards.setdefault(cid, set()).add(k["versions"][-1])
        self.card_prefix = {}
        cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"card_prefix_s{seed}.json")
        if os.path.exists(cp):
            d = json.load(open(cp))
            self.card_prefix = d["prefix"]
            self.cards = {k: set(v) for k, v in d["covers"].items()}

    def allowed(self, requester):
        return set(p.replace("/", "-") for p in self.meta["identities"][requester]["partitions"])


def transform(w: World, t, ids, how):
    """raw = GBrain as shipped (every fact version is a live page).
    keyed = batch-2 store semantics applied to GBrain's ranking: for non-temporal queries superseded fact versions are
            not live (dropped from the list), temporal queries see history (= batch-2 live_mask + forward).
    fwd = our ADR-009 forward-to-head: a retrieved superseded version is replaced in place by its current head."""
    covers = {}
    if how == "keyed":
        if not TEMPORAL_RE.search(t["query"]):
            ids = [i for i in ids if i not in w.superseded]
    if how in ("fwd", "fwdcards"):
        if not TEMPORAL_RE.search(t["query"]):
            out, seen = [], set()
            for i in ids:
                j = w.head_of.get(i, i) if i in w.superseded else i
                if j not in seen:
                    seen.add(j); out.append(j)
            ids = out
    if how in ("cards", "fwdcards", "pincards", "pincardskeyed"):
        covers = w.cards
    if how in ("pincards", "pincardskeyed"):
        # batch-2 cards(<=3)+query assembly with GBrain as the ranker: pin the task's linked, ACL-checked cards first
        if how == "pincardskeyed" and not TEMPORAL_RE.search(t["query"]):
            ids = [i for i in ids if i not in w.superseded]
        pre = w.card_prefix.get(t["id"], [])
        ids = pre + [i for i in ids if i not in pre]
    return ids, covers


def row(t, ids, covers, ks=(10, 20, 50, 100)):
    req = set(t["required"])
    r = dict(id=t["id"], cls=t["cls"], set_id=t["set_id"], size=len(req))
    for k in ks:
        got = set(ids[:k])
        for i in ids[:k]:
            got |= covers.get(i, set())
        f = got & req
        r[f"ok@{k}"] = len(f) == len(req)
        r[f"rec@{k}"] = len(f) / len(req)
    return r


def stale_metrics(w: World, t, ids):
    head = t["required"][0]
    stale, traps = set(t["stale_ids"]), set(t["trap_ids"])
    top = ids[:10]
    lim = top.index(head) if head in top else 10
    first = None
    for i in top:
        it = w.items.get(i, {})
        if i == head or (i not in traps and head in it.get("fact_refs", [])):
            first = "current"; break
        if i in stale or i in traps:
            first = "stale"; break
    return dict(stale_fact=any(i in stale for i in top[:lim]), stale_trap=any(i in traps for i in top[:lim]),
                head_found=head in top, first=first)


def main():
    seed = int(sys.argv[1])
    w = World(seed)
    tasks = {t["id"]: t for t in w.tasks}
    arms = {}
    for spec in sys.argv[2:]:
        name, rest = spec.split("=", 1)
        path, _, how = rest.partition(":")
        arms[name] = (path, how or "raw")
    # batch-2 comparators (same seed, same tasks)
    e8a = pickle.load(open(f"{BB}/results_v02/e8a.pkl", "rb"))["rows"][seed]
    e8c = pickle.load(open(f"{BB}/results_v02/e8c.pkl", "rb"))["rows"][seed]
    comp = {"B2 BM25": e8a["BM25"], "B2 bge-small dense": e8a["bge-small"], "B2 rrf(BM25+bge-small)": e8a["rrf(BM25+bge-small)"],
            "B2 wsum(BM25+bge-small) = query-only": e8a["wsum(BM25+bge-small)"], "B2 cards(<=3)+query": e8c["cards(<=3) + query"],
            "B2 cards+slots+query": e8c["cards(<=3) + static slots + query"]}
    # restrict comparators to exactly the task ids the GBrain arms ran (paired on identical tasks)
    ran = set()
    for name, (path, how) in arms.items():
        ran |= {r["id"] for r in rj(path)}
    comp = {n: [x for x in rows if x["id"] in ran] for n, rows in comp.items()}
    res, leaks, stale_rows, lat, errs = {}, {}, {}, {}, {}
    for name, (path, how) in arms.items():
        runs = rj(path)
        rows, srows, nleak, nleak_tasks, ms, ne = [], [], 0, 0, [], 0
        for r in runs:
            t = tasks[r["id"]]
            ok_src = w.allowed(t["requester"])
            bad = [s for s in r["srcs"] if s not in ok_src]
            nleak += len(bad); nleak_tasks += bool(bad)
            ms.append(r["ms"]); ne += bool(r.get("err"))
            ids, cov = transform(w, t, r["ids"], how)
            if t["cls"] == "stale_probe":
                srows.append(stale_metrics(w, t, ids))
            elif t["cls"] in CLASSES:
                rows.append(row(t, ids, cov))
        res[name] = rows; stale_rows[name] = srows
        leaks[name] = (nleak, nleak_tasks, len(runs)); lat[name] = (np.percentile(ms, 50), np.percentile(ms, 95)); errs[name] = ne
    out = []
    P = out.append
    P(f"## GBrain on BrainBench v0.2 seed {seed}\n")
    P("Rates: mean over distinct required sets, Wilson 95% (n = distinct sets). Batch-2 comparators re-read from results_v02 pickles, same seed and tasks.\n")
    for k in (10, 20, 50, 100):
        P(f"### CR@{k} %\n")
        P("| arm | " + " | ".join(SHORT[c] for c in CLASSES) + " | ALL |")
        P("|---" * (len(CLASSES) + 2) + "|")
        allarms = list(res.items()) + ([(n, r) for n, r in comp.items()] if k == 10 else [(n, r) for n, r in comp.items() if f"ok@{k}" in r[0]])
        for name, rows in allarms:
            cells = []
            for c in CLASSES + ["ALL"]:
                rr = [x for x in rows if (c == "ALL" or x["cls"] == c)]
                if not rr or f"ok@{k}" not in rr[0]:
                    cells.append("–"); continue
                p, lo, hi, n = rate(rr, f"ok@{k}")
                cells.append(f"{100*p:.1f} [{100*lo:.0f}–{100*hi:.0f}]")
            P(f"| {name} | " + " | ".join(cells) + " |")
        P("")
    P("### Item recall@10 / @100 %\n")
    P("| arm | " + " | ".join(SHORT[c] for c in CLASSES) + " | ALL |")
    P("|---" * (len(CLASSES) + 2) + "|")
    for name, rows in list(res.items()):
        cells = []
        for c in CLASSES + ["ALL"]:
            rr = [x for x in rows if (c == "ALL" or x["cls"] == c)]
            cells.append(f"{100*np.mean([x['rec@10'] for x in rr]):.1f} / {100*np.mean([x['rec@100'] for x in rr]):.1f}")
        P(f"| {name} | " + " | ".join(cells) + " |")
    P("")
    P("### Paired tests (CR@10, distinct sets; exact sign test; Δ = arm − comparator, cluster-bootstrap 95% CI)\n")
    P("| arm | vs | class | better/worse | Δ pp [CI] | p |")
    P("|---|---|---|---|---|---|")
    for name, rows in res.items():
        for cname in ("B2 wsum(BM25+bge-small) = query-only", "B2 cards(<=3)+query", "B2 bge-small dense"):
            for c in ["ALL"] + CLASSES:
                a = [x for x in comp[cname] if c == "ALL" or x["cls"] == c]
                b = [x for x in rows if c == "ALL" or x["cls"] == c]
                wv, lv, p, d, lo, hi = sign(a, b, "ok@10")
                P(f"| {name} | {cname} | {SHORT.get(c, c)} | +{wv}/−{lv} | {d:+.1f} [{lo:+.1f}, {hi:+.1f}] | {p:.2g} |")
    P("")
    P("### Leakage, latency, errors\n")
    P("| arm | returned rows from ungranted sources | tasks with any | tasks | p50 / p95 ms per search | errors |")
    P("|---|---|---|---|---|---|")
    for name in res:
        nl, nt, n = leaks[name]
        P(f"| {name} | {nl} | {nt} | {n} | {lat[name][0]:.0f} / {lat[name][1]:.0f} | {errs[name]} |")
    P("")
    if any(stale_rows.values()):
        P("### Stale probes (E1 definitions; top-10)\n")
        P("| arm | n | stale version above current | stale-quoting note above current | current value missing from top-10 | first value-bearing item stale |")
        P("|---|---|---|---|---|---|")
        for name, srows in stale_rows.items():
            if not srows:
                continue
            n = len(srows)
            def f(key):
                k = sum(r[key] for r in srows); p, lo, hi = wilson(k, n); return f"{100*p:.1f}% [{100*lo:.1f}–{100*hi:.1f}] ({k})"
            km = sum(not r["head_found"] for r in srows); p, lo, hi = wilson(km, n)
            surf = [r for r in srows if r["first"] is not None]; kf = sum(r["first"] == "stale" for r in surf); pf, lof, hif = wilson(kf, len(surf))
            P(f"| {name} | {n} | {f('stale_fact')} | {f('stale_trap')} | {100*p:.1f}% [{100*lo:.1f}–{100*hi:.1f}] ({km}) | {100*pf:.1f}% [{100*lof:.1f}–{100*hif:.1f}] ({kf}/{len(surf)}) |")
        P("")
    txt = "\n".join(out)
    print(txt)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"tables_s{seed}.md"), "w") as fh:
        fh.write(txt)
    pickle.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"rows_s{seed}.pkl"), "wb"))


if __name__ == "__main__":
    main()
