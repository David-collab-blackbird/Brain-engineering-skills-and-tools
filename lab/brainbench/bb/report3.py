"""Tables for batch 3 -> results_v03/tables.md and results_v03/summary.json (RESULTS_batch3.md quotes these)."""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict

import numpy as np

from .common import ROOT
from .pipe3 import CLASSES_NEW, CLASSES_V2, KS, TARGET5, TS, rate, sign_test, wilson_frac

OUT = os.path.join(ROOT, "results_v03")
N8 = ["decision_support", "option_analysis", "cross_domain"]
DOG = ["decision_support", "option_analysis", "goal_tracking"]
SHORT = {"decision_support": "decision", "option_analysis": "option", "goal_tracking": "goal", "preference_recommendation": "pref", "cross_domain": "cross",
         "current_state": "current", "temporal_change": "temporal", "multimodal": "media", "aggregation": "aggreg", "standing_brief": "brief",
         "obligation_status": "oblig", "rule_precedence": "rule-prec", "match_reconcile": "reconcile", "release_safe": "release", "carry_forward": "carry"}


def fix(rows):
    out = []
    for r in rows:
        r = dict(r)
        r["set_id"] = f"{r['cls']}:{r['set_id']}"
        out.append(r)
    return out


def sub(rows, classes=None, forms=None):
    return [r for r in rows if (classes is None or r["cls"] in classes) and (forms is None or r.get("ref_form") in forms)]


def pct(x):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}"


def cell(rows, key):
    r = rate(rows, key)
    if not r["n"]:
        return "–"
    return f"{100 * r['p']:.1f} [{100 * r['lo']:.0f}–{100 * r['hi']:.0f}]"


def cellp(rows, key):
    r = rate(rows, key)
    return "–" if not r["n"] else f"{100 * r['p']:.1f}"


def ptest(a, b, key):
    t = sign_test(a, b, key)
    return f"{t['diff']:+.1f} pp [{t['lo']:+.1f}, {t['hi']:+.1f}], +{t['b_better']}/−{t['a_better']}, p={t['p']:.2g}" if t["n"] else "–"


def table_arms(lines, arms, title, keys=("v@10", "v@50", "v@100", "v@T1000", "v@T4000", "v@T8000"), pools=(("target5", TARGET5), ("N8 pool", N8))):
    lines.append(f"\n### {title}\n")
    hdr = "| arm | " + " | ".join(f"{p} {k}" for p, _ in pools for k in keys) + " |"
    lines.append(hdr)
    lines.append("|" + "---|" * (1 + len(pools) * len(keys)))
    for name, rows in arms.items():
        lines.append(f"| {name} | " + " | ".join(cellp(sub(rows, cl), k) for _, cl in pools for k in keys) + " |")
    n = {p: rate(sub(next(iter(arms.values())), cl), keys[0])["n"] for p, cl in pools}
    lines.append(f"\n(n distinct sets: {n}; CR_vital, % — Wilson intervals in the per-class table)")


def table_classes(lines, arms, key, title, classes):
    lines.append(f"\n### {title} ({key})\n")
    lines.append("| arm | " + " | ".join(SHORT.get(c, c) for c in classes) + " |")
    lines.append("|" + "---|" * (1 + len(classes)))
    for name, rows in arms.items():
        lines.append(f"| {name} | " + " | ".join(cell(sub(rows, [c]), key) for c in classes) + " |")
    first = next(iter(arms.values()))
    lines.append("| *n sets* | " + " | ".join(str(rate(sub(first, [c]), key)["n"]) for c in classes) + " |")


def write(log=print, load=None):
    L = ["# Batch 3 generated tables (BrainBench v0.3)\n", "Rates are means over distinct need-sets (seed × class × set), CR_vital unless marked; brackets are Wilson 95% intervals; paired tests are exact sign tests over distinct sets with a cluster-bootstrap 95% CI.\n"]
    S = {}
    e9 = load("e9")
    if e9:
        arms = defaultdict(list)
        for (s, name), rows in sorted(e9["rows"].items(), key=lambda x: (x[0][1], x[0][0])):
            arms[name] += fix(rows)
        seeds_by_arm = defaultdict(set)
        for (s, name) in e9["rows"]:
            seeds_by_arm[name].add(s)
        L.append("\n## E9 / N8 / U1 — structure at write\n")
        L.append("Seeds per arm: " + "; ".join(f"{a}: {sorted(v)}" for a, v in seeds_by_arm.items()))
        order = [a for a in ("A0 query-only", "A1 router (batch-2 best, no gate)", "A2 code gate + nbhd", "A3c haiku gate, cards only", "A3u haiku gate + nbhd (query order)",
                             "A3 haiku gate + nbhd (typed first)", "A4c sonnet gate, cards only", "A4 sonnet gate + nbhd (typed first)", "A5c gold gate, cards only", "A5 gold gate + nbhd (typed first)") if a in arms]
        table_arms(L, {a: arms[a] for a in order}, "Pools (CR_vital %)")
        for key in ("v@10", "v@50", "v@T4000", "a@50"):
            table_classes(L, {a: arms[a] for a in order}, key, "Per class", TARGET5 + ["current_state", "temporal_change", "multimodal"] + CLASSES_NEW)
        # paired tests on common seeds
        L.append("\n### Paired tests (common seeds only)\n")
        S["e9_tests"] = {}
        pairs = [("A1 router (batch-2 best, no gate)", "A3 haiku gate + nbhd (typed first)"), ("A0 query-only", "A1 router (batch-2 best, no gate)"),
                 ("A1 router (batch-2 best, no gate)", "A2 code gate + nbhd"), ("A2 code gate + nbhd", "A3 haiku gate + nbhd (typed first)"),
                 ("A3c haiku gate, cards only", "A3 haiku gate + nbhd (typed first)"), ("A3u haiku gate + nbhd (query order)", "A3 haiku gate + nbhd (typed first)"),
                 ("A3 haiku gate + nbhd (typed first)", "A4 sonnet gate + nbhd (typed first)"), ("A3 haiku gate + nbhd (typed first)", "A5 gold gate + nbhd (typed first)"),
                 ("A1 router (batch-2 best, no gate)", "A4 sonnet gate + nbhd (typed first)"), ("A1 router (batch-2 best, no gate)", "A5 gold gate + nbhd (typed first)")]
        for a, b in pairs:
            if a not in arms or b not in arms:
                continue
            common = seeds_by_arm[a] & seeds_by_arm[b]
            ra = [r for r in arms[a] if r["seed"] in common]
            rb = [r for r in arms[b] if r["seed"] in common]
            L.append(f"- **{b} vs {a}** (seeds {sorted(common)}):")
            for pname, cl in (("target5", TARGET5), ("N8", N8), ("dec+opt+goal", DOG)):
                for key in ("v@10", "v@50", "v@T4000"):
                    t = sign_test(sub(ra, cl), sub(rb, cl), key)
                    S["e9_tests"][f"{b} vs {a} | {pname} | {key}"] = t
                L.append(f"  - target5 @K50: {ptest(sub(ra, TARGET5), sub(rb, TARGET5), 'v@50')}; @K10: {ptest(sub(ra, TARGET5), sub(rb, TARGET5), 'v@10')}; @T4k: {ptest(sub(ra, TARGET5), sub(rb, TARGET5), 'v@T4000')}")
                L.append(f"  - N8 pool @K50: {ptest(sub(ra, N8), sub(rb, N8), 'v@50')}; @K10: {ptest(sub(ra, N8), sub(rb, N8), 'v@10')}; @T4k: {ptest(sub(ra, N8), sub(rb, N8), 'v@T4000')}")
                L.append(f"  - decision+option+goal @K50: {ptest(sub(ra, DOG), sub(rb, DOG), 'v@50')}")
                break
        # by reference form
        L.append("\n### CR_vital@50 by reference form (all classes with an entity reference)\n")
        forms = ["registry", "seen", "heldout_desc", "heldout_nick"]
        L.append("| arm | " + " | ".join(forms) + " |")
        L.append("|---|---|---|---|---|")
        for a in order:
            L.append(f"| {a} | " + " | ".join(cell(sub(arms[a], None, [f]), "v@50") for f in forms) + " |")
        # extraction quality
        L.append("\n### Write-gate extraction quality (vs gold; seed-level)\n")
        L.append("| gate | seed | link P | link P (lenient) | link R | implicit R | explicit R | req-evidence link R | keyed-fact recall | wrong value | decision | constraint | plan | issue | offer | preference |")
        L.append("|" + "---|" * 16)
        S["quality"] = {}
        for (s, g), q in sorted(e9["quality"].items(), key=lambda x: (x[0][1], x[0][0])):
            rc = q["record_coverage"]
            S["quality"][f"{g}/s{s}"] = q
            L.append(f"| {g} | {s} | {pct(q['link_precision'])} | {pct(q.get('link_precision_lenient'))} | {pct(q['link_recall'])} | {pct(q['link_recall_implicit'])} | {pct(q['link_recall_explicit'])} | {pct(q.get('req_link_recall'))} | {pct(q['keyed_fact_recall'])} | {pct(q['keyed_fact_wrong_value'])} | "
                     + " | ".join(pct(rc.get(T)) for T in ("decision", "constraint", "plan", "issue", "offer", "preference")) + " |")
        L.append("\n### Structure reach: share of VITAL free-text items reachable by structure (target classes)\n")
        L.append("| gate | seeds | reach (item-weighted) | tasks with every vital free-text item reachable | registry | seen | heldout_desc | heldout_nick |")
        L.append("|---|---|---|---|---|---|---|---|")
        rg = defaultdict(list)
        for (s, g), rr in e9["reach"].items():
            rg[g] += rr
        S["reach"] = {}
        for g, rr in sorted(rg.items()):
            n = sum(r["n"] for r in rr); h = sum(r["hit"] for r in rr)
            allr = np.mean([r["hit"] == r["n"] for r in rr])
            byf = {f: (sum(r["hit"] for r in rr if r["form"] == f) / max(1, sum(r["n"] for r in rr if r["form"] == f))) for f in forms}
            hp = sum(r.get("hit_par", r["hit"]) for r in rr)
            S["reach"][g] = dict(reach=h / max(1, n), reach_with_parents=hp / max(1, n), all=float(allr), **byf)
            L.append(f"| {g} | {sorted({k[0] for k in e9['reach'] if k[1] == g})} | {pct(h / max(1, n))} (with parent entities: {pct(hp / max(1, n))}) | {pct(allr)} | " + " | ".join(pct(byf[f]) for f in forms) + " |")
        S["e9_pools"] = {a: {p: {k: rate(sub(arms[a], cl), k) for k in ("v@10", "v@50", "v@100", "v@T1000", "v@T4000", "v@T8000", "a@50")} for p, cl in (("target5", TARGET5), ("N8", N8), ("DOG", DOG))} for a in order}
        S["e9_class"] = {a: {c: {k: rate(sub(arms[a], [c]), k) for k in ("v@10", "v@50", "v@T4000", "a@50")} for c in TARGET5 + ["current_state", "temporal_change", "multimodal"] + CLASSES_NEW} for a in order}
        S["e9_forms"] = {a: {f: rate(sub(arms[a], None, [f]), "v@50") for f in forms} for a in order}
        S["e9_store"] = {f"{g}/s{s}": v for (s, g), v in e9["store"].items()}
    rel = load("release")
    if rel:
        L.append("\n## Release-safe drafting: requester visibility vs requester ∩ recipient\n")
        L.append("| visibility | forbidden private note in context @10 | @50 | CR_vital@10 | CR_vital@50 | seeds |")
        L.append("|---|---|---|---|---|---|")
        by = defaultdict(list)
        for (s, mode), rows in rel.items():
            by[mode] += fix(rows)
        S["release"] = {}
        for mode, rows in by.items():
            S["release"][mode] = dict(forbid10=rate(rows, "forbid@10"), forbid50=rate(rows, "forbid@50"), v10=rate(rows, "v@10"), v50=rate(rows, "v@50"))
            L.append(f"| {mode} | {cell(rows, 'forbid@10')} | {cell(rows, 'forbid@50')} | {cell(rows, 'v@10')} | {cell(rows, 'v@50')} | {sorted({k[0] for k in rel if k[1] == mode})} |")
    e10 = load("e10")
    if e10:
        L.append("\n## E10 / E10b / U2 / U2a — double entry\n")
        forms = ["registry", "seen", "heldout_desc", "heldout_nick"]
        S["e10"] = {}
        for qn in ("A0", "A3"):
            L.append(f"\n### Query side {qn}: CR_vital@50 by reference form (all classes)\n")
            L.append("| entry | seeds | " + " | ".join(forms) + " | held-out pooled | all |")
            L.append("|---|---|---|---|---|---|---|---|")
            modes = defaultdict(list)
            for (s, mode, q), rows in e10["rows"].items():
                if q == qn:
                    modes[mode] += fix(rows)
            for mode in ("raw", "header", "scribe", "scribe_f", "header+scribe_f", "header+values"):
                if mode not in modes:
                    continue
                rr = modes[mode]
                L.append(f"| {mode} | {sorted({k[0] for k in e10['rows'] if k[1] == mode and k[2] == qn})} | " + " | ".join(cell(sub(rr, None, [f]), "v@50") for f in forms)
                         + f" | {cell(sub(rr, None, ['heldout_desc', 'heldout_nick']), 'v@50')} | {cell(rr, 'v@50')} |")
                S["e10"][f"{qn}/{mode}"] = {f: rate(sub(rr, None, [f]), "v@50") for f in forms + ["all"]} if False else {f: rate(sub(rr, None, [f]), "v@50") for f in forms}
            L.append("\nPaired (sign test over distinct sets):")
            for a, b, fl in (("raw", "header", ["seen"]), ("raw", "header", ["heldout_desc", "heldout_nick"]), ("header", "header+scribe_f", ["heldout_desc", "heldout_nick"]),
                             ("header", "header+scribe_f", ["seen"]), ("raw", "scribe", ["heldout_desc", "heldout_nick"]), ("scribe", "scribe_f", ["heldout_desc", "heldout_nick"]),
                             ("header", "header+values", None)):
                if a in modes and b in modes:
                    for key in ("v@10", "v@50"):
                        S["e10"][f"test {qn} {b} vs {a} {fl} {key}"] = sign_test(sub(modes[a], None, fl), sub(modes[b], None, fl), key)
                    L.append(f"- {qn}: **{b} vs {a}** on {fl or 'all'}: @K50 {ptest(sub(modes[a], None, fl), sub(modes[b], None, fl), 'v@50')}; @K10 {ptest(sub(modes[a], None, fl), sub(modes[b], None, fl), 'v@10')}")
            # precision@10 proxy: share of top-10 items that are required items
        L.append("\n### Stale exposure (stale probes) paired with temporal CR on the same keys\n")
        L.append("| entry / query side | stale exposure @10 | unresolved stale (no current value) | current value found @10 | temporal CR_vital@10 (paired keys) | n probes |")
        L.append("|---|---|---|---|---|---|")
        for (s, mode, qn), rows in sorted(e10["stale"].items(), key=lambda x: (x[0][2], x[0][1], x[0][0])):
            pass
        agg = defaultdict(list)
        for (s, mode, qn), rows in e10["stale"].items():
            agg[(mode, qn)] += rows
        tagg = defaultdict(list)
        for (s, mode, qn), rows in e10["rows"].items():
            tagg[(mode, qn)] += rows
        S["e10_stale"] = {}
        for (mode, qn), rows in sorted(agg.items(), key=lambda x: (x[0][1], x[0][0])):
            pairs = {r["pair_id"] for r in rows if r.get("pair_id")}
            trows = [r for r in tagg[(mode, qn)] if r["cls"] == "temporal_change"]
            ex = np.mean([r["exposed"] for r in rows]); un = np.mean([r["unresolved"] for r in rows]); cf = np.mean([r["current_found"] for r in rows])
            k = sum(r["exposed"] for r in rows); n = len(rows)
            p, lo, hi = wilson_frac(k, n)
            S["e10_stale"][f"{qn}/{mode}"] = dict(exposed=ex, lo=lo, hi=hi, unresolved=un, current_found=cf, n=n)
            L.append(f"| {mode} / {qn} | {100*ex:.1f} [{100*lo:.0f}–{100*hi:.0f}] | {100*un:.1f} | {100*cf:.1f} | {cellp(trows, 'v@10')} | {n} |")
        if ("header", "A3") in agg and ("header+values", "A3") in agg:
            a = {(r["seed"], r["id"]): r["exposed"] for r in agg[("header", "A3")]}
            b = {(r["seed"], r["id"]): r["exposed"] for r in agg[("header+values", "A3")]}
            ks = sorted(set(a) & set(b))
            d = np.array([b[k] - a[k] for k in ks], float)
            w_, l_ = int((d > 0).sum()), int((d < 0).sum())
            from math import comb
            nn = w_ + l_
            pv = 1.0 if nn == 0 else min(1.0, 2 * sum(comb(nn, i) for i in range(min(w_, l_) + 1)) / 2 ** nn)
            rng = np.random.default_rng(0)
            bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)] if len(d) else [0]
            S["e10_U2a"] = dict(diff=float(d.mean()) if len(d) else 0.0, lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), worse=w_, better=l_, p=pv, n=len(ks))
            L.append(f"\nU2a (values in the searchable entry vs not, A3): Δ stale exposure {100*S['e10_U2a']['diff']:+.2f} pp [{100*S['e10_U2a']['lo']:+.2f}, {100*S['e10_U2a']['hi']:+.2f}], +{w_}/−{l_} probes, p={pv:.2g}")
    agg = load("agg")
    if agg:
        L.append("\n## H17 — aggregation (exact-set)\n")
        L.append("| records from | seeds | exact-set recall (records) | recall (item) | precision | absence correct | top-K exact @10 / @50 / @100 |")
        L.append("|---|---|---|---|---|---|---|")
        by = defaultdict(list)
        for (s, g), rows in agg["rows"].items():
            by[g] += [dict(r, set_id=f"agg:{r['set_id']}") for r in rows]
        S["agg"] = {}
        for g, rows in by.items():
            nonabs = [r for r in rows if not r["absence"]]
            ab = [r for r in rows if r["absence"]]
            S["agg"][g] = dict(exact=rate(nonabs, "rec_exact"), recall=float(np.mean([r["recall"] for r in nonabs])), precision=float(np.mean([r["precision"] for r in nonabs])),
                               absence=float(np.mean([r["rec_exact"] for r in ab])) if ab else None, n_abs=len(ab),
                               topk={k: rate(nonabs, f"topk@{k}") for k in KS})
            L.append(f"| {g} | {sorted({k[0] for k in agg['rows'] if k[1] == g})} | {cell(nonabs, 'rec_exact')} | {pct(S['agg'][g]['recall'])} | {pct(S['agg'][g]['precision'])} | "
                     f"{pct(S['agg'][g]['absence'])} (n={len(ab)}) | " + " / ".join(cellp(nonabs, f'topk@{k}') for k in KS) + " |")
    i15 = load("i15")
    if i15 and i15.get("rows"):
        from .exp3 import conformal, clopper_lower
        L.append("\n## I15 — certified recall (worst-vital-item split conformal, α = 0.10)\n")
        rows = {k[0]: fix(v) for k, v in i15["rows"].items()}
        seeds = sorted(rows)
        S["i15"] = {}
        if len(seeds) >= 2:
            cal_seeds, test_seed = seeds[:-1], seeds[-1]
            L.append(f"Calibrate on seeds {cal_seeds} (one task per distinct set), test on held-out seed {test_seed}. K̂ = items, T̂ = tokens; inf = >10% of calibration sets have a vital item never reached within 400 items.\n")
            L.append("| class | n cal | n test | K̂ | coverage (items) | CP 95% lower | T̂ tokens | coverage (tokens) | T̂ ≤ 8k? | 200 within-seed splits: mean cov (K̂) |")
            L.append("|---|---|---|---|---|---|---|---|---|---|")
            import random as _r
            for c in TARGET5 + ["current_state", "temporal_change", "multimodal"] + CLASSES_NEW:
                cal = [r for s in cal_seeds for r in rows[s] if r["cls"] == c]
                te = [r for r in rows[test_seed] if r["cls"] == c]
                ck = conformal(cal, te, "r_vital"); ct = conformal(cal, te, "t_vital")
                if not ck:
                    continue
                lo = clopper_lower(ck["k"], ck["n_test"])
                # within-seed random splits (all seeds pooled by set)
                allr = [r for s in seeds for r in rows[s] if r["cls"] == c]
                sets = sorted({(r["seed"], r["set_id"]) for r in allr})
                R = _r.Random(0)
                covs, khat = [], []
                for _ in range(200):
                    R.shuffle(sets)
                    h = len(sets) // 2
                    cs, ts = set(sets[:h]), set(sets[h:])
                    res = conformal([r for r in allr if (r["seed"], r["set_id"]) in cs], [r for r in allr if (r["seed"], r["set_id"]) in ts], "r_vital")
                    if res:
                        covs.append(res["coverage"]); khat.append(res["thr"])
                kmed = float(np.median(khat)) if khat else float("nan")
                S["i15"][c] = dict(items=ck, tokens=ct, cp_lower=lo, split_cov=float(np.mean(covs)) if covs else None, split_khat_median=kmed)
                fmt = lambda x: "inf" if x == float("inf") else f"{x:.0f}"
                L.append(f"| {SHORT.get(c, c)} | {ck['n_cal']} | {ck['n_test']} | {fmt(ck['thr'])} | {100*ck['coverage']:.1f} | {100*lo:.1f} | {fmt(ct['thr'])} | {100*ct['coverage']:.1f} | "
                         f"{'yes' if ct['thr'] <= 8000 else 'no'} | {100*np.mean(covs):.1f} ({fmt(kmed)}) |")
    adr = load("adr")
    if adr:
        L.append("\n## ADR checks\n")
        d4 = adr.get("da1_4", {})
        if d4:
            L.append("\n### DA1-4 BM25 statistics policy (query-only)\n")
            L.append(f"Share of query terms unseen in WikiText-2: {pct(d4.get('oov_share'))}%\n")
            L.append("| statistics | retriever | ALL v@10 | ALL v@50 | target5 v@50 | current v@10 | temporal v@10 |")
            L.append("|---|---|---|---|---|---|---|")
            by = defaultdict(list)
            for k, v in d4.items():
                if isinstance(k, tuple):
                    by[(k[1], k[2])] += fix(v)
            S["da1_4"] = {}
            for (stt, ret), rr in sorted(by.items(), key=lambda x: (x[0][1], x[0][0])):
                S["da1_4"][f"{ret}/{stt}"] = {k: rate(rr, k) for k in ("v@10", "v@50")}
                L.append(f"| {stt} | {ret} | {cell(rr, 'v@10')} | {cellp(rr, 'v@50')} | {cellp(sub(rr, TARGET5), 'v@50')} | {cellp(sub(rr, ['current_state']), 'v@10')} | {cellp(sub(rr, ['temporal_change']), 'v@10')} |")
            for ret in ("bm25", "hybrid"):
                if (("visible", ret) in by) and (("frozen", ret) in by):
                    for alt in ("frozen", "partition", "global"):
                        if (alt, ret) in by:
                            t = sign_test(by[("visible", ret)], by[(alt, ret)], "v@10")
                            S["da1_4"][f"test {ret} {alt} vs visible v@10"] = t
                            L.append(f"- {ret}: **{alt} vs visible** @10: {ptest(by[('visible', ret)], by[(alt, ret)], 'v@10')}; @50: {ptest(by[('visible', ret)], by[(alt, ret)], 'v@50')}")
        s2 = adr.get("s2", {}).get("s2")
        if s2:
            L.append("\n### S2 / S3 twin-world noninterference vs canaries\n")
            L.append(f"Identities: {s2['idents']}. No-grant credential: {s2['nogrant']}\n")
            L.append("| engine | twin-world: identities with any observable change | ids changed | own-revocation equivalence failures | canary alarms / probes |")
            L.append("|---|---|---|---|---|")
            for bug, r in s2["res"].items():
                c = s2["canary"][bug]
                L.append(f"| {bug} | {r['detected_any']}/{r['n_ident']} | {r['detected_ids']}/{r['n_ident']} | {r.get('revocation_detected', 0)}/{r.get('revocation_checks', 0)} | {c['alarms']}/{c['probes']} |")
            S["s2"] = s2
        d6 = adr.get("da1_6", {})
        if d6:
            L.append("\n### DA1-6 history growth: version rows vs key timelines (temporal and current state, CR_vital@10)\n")
            L.append("| extra versions per key | arm | temporal v@10 | temporal v@50 | current v@10 | seeds |")
            L.append("|---|---|---|---|---|---|")
            by = defaultdict(list)
            for k, v in d6.items():
                by[(k[1], k[2])] += fix(v)
            S["da1_6"] = {}
            for (B, arm), rr in sorted(by.items()):
                S["da1_6"][f"B{B}/{arm}"] = dict(temporal=rate(sub(rr, ["temporal_change"]), "v@10"), current=rate(sub(rr, ["current_state"]), "v@10"))
                L.append(f"| {B} | {arm} | {cell(sub(rr, ['temporal_change']), 'v@10')} | {cellp(sub(rr, ['temporal_change']), 'v@50')} | {cellp(sub(rr, ['current_state']), 'v@10')} | {sorted({k[0] for k in d6 if k[1] == B})} |")
        d7 = adr.get("da1_7", {})
        if d7:
            L.append("\n### DA1-7 values-free stub cards (read-time values) vs stored cards (cards ≤3 + query)\n")
            by = defaultdict(list)
            for k, v in d7.items():
                by[(k[1], k[2])] += fix(v)
            S["da1_7"] = {}
            for g in sorted({k[0] for k in by}):
                if (g, "stored") in by and (g, "stub") in by:
                    t = sign_test(by[(g, "stored")], by[(g, "stub")], "v@10")
                    S["da1_7"][g] = dict(stored=rate(by[(g, "stored")], "v@10"), stub=rate(by[(g, "stub")], "v@10"), test=t)
                    L.append(f"- {g} gate: stored {cell(by[(g, 'stored')], 'v@10')} vs stub {cell(by[(g, 'stub')], 'v@10')} (ALL v@10); stub vs stored {ptest(by[(g, 'stored')], by[(g, 'stub')], 'v@10')}; @50 {ptest(by[(g, 'stored')], by[(g, 'stub')], 'v@50')}")
        ex = adr.get("exit", {})
        if ex:
            L.append("\n### Exit check vs a delayed index (revocation + erasure)\n")
            S["exit"] = {}
            for s, d in sorted(ex.items()):
                r0, r1 = fix(d["rows"]["no exit"]), fix(d["rows"]["exit check"])
                S["exit"][s] = dict(leaks=d["leaks"], probes=d["probes"], no_exit=rate(r0, "v@10"), exit=rate(r1, "v@10"))
                L.append(f"- seed {s}: leaks without exit check: {d['leaks'].get('no_exit_items', 0)} items in {d['leaks'].get('no_exit_tasks', 0)} task contexts (top 50) + "
                         f"{d['leaks'].get('probe_no_exit', 0)} items in revoked-coach probes; with exit check: {d['leaks'].get('exit_items', 0)}. "
                         f"CR_vital@10 on unaffected tasks: {cellp(r0, 'v@10')} → {cellp(r1, 'v@10')} ({ptest(r0, r1, 'v@10')}).")
    e11 = load("e11")
    if e11:
        L.append("\n## E11 — self-healing vocabulary (simulated year)\n")
        L.append("| seed | arm | held-out CR_vital@50 months 0–2 | months 9–11 | drifted phrases after drift | control regressions vs none | corrections |")
        L.append("|---|---|---|---|---|---|---|")
        S["e11"] = {}
        for s, d in sorted(e11.items()):
            base = {r["i"]: r["ok"] for r in d["res"]["none"]}
            for mode, rows in d["res"].items():
                early = [r["ok"] for r in rows if r["kind"] == "held" and r["m"] <= 2]
                late = [r["ok"] for r in rows if r["kind"] == "held" and r["m"] >= 9]
                dr = [r["ok"] for r in rows if r["kind"] == "held" and r.get("drifted")]
                reg = sum(1 for r in rows if r["kind"] == "ctrl" and base[r["i"]] and not r["ok"])
                corr = rows[-1]["corrections"]
                S["e11"][f"s{s}/{mode}"] = dict(early=float(np.mean(early)), late=float(np.mean(late)), drift=float(np.mean(dr)) if dr else None, regressions=reg, corrections=corr,
                                                 held_all=float(np.mean([r["ok"] for r in rows if r["kind"] == "held"])))
                L.append(f"| {s} | {mode} | {pct(np.mean(early))} | {pct(np.mean(late))} | {pct(np.mean(dr)) if dr else '–'} | {reg} | {corr} |")
    fab = load("fab")
    if fab and fab.get("scores"):
        L.append("\n## DT-U1a fabrication suite (seed 1; 100 stated + 100 not-stated fields)\n")
        L.append("| writer / schema | fabrication (raw) | fabrication after code validator | recall (raw) | recall after validator | answered |")
        L.append("|---|---|---|---|---|---|")
        for k, v in fab["scores"].items():
            pf, lf, hf = wilson_frac(v["fab_raw_k"], v["missing_n"])
            pv, lv, hv = wilson_frac(v["fab_validated_k"], v["missing_n"])
            L.append(f"| {k} | {100*pf:.1f} [{100*lf:.0f}–{100*hf:.0f}] | {100*pv:.1f} [{100*lv:.0f}–{100*hv:.0f}] | {pct(v['recall_raw'])} | {pct(v['recall_validated'])} | {v['answered']} |")
        S["fab"] = fab["scores"]
    escr = load("escr")
    if escr and escr.get("analysis"):
        L.append("\n## E-SCR — the owner's scribe (seed 1)\n")
        L.append("| writer | entries | unparsable | clean at first check (G0) | coverage keep-worthy | coverage implicit | filler recorded | spouse turns recorded | invented value tokens | link P | link R | G1 extra flags |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        S["escr"] = {}
        for m, a in escr["analysis"].items():
            x = a["metrics"]
            S["escr"][m] = dict(metrics=x, g0_rules=a["g0_rules"], g1=a["metrics"].get("g1_rule_counts"), seeded=escr["seeded"].get(m))
            L.append(f"| {m} | {x['entries']} | {x['unparsable']} | {x['clean_g0']}/{x['entries'] - x['unparsable']} | {pct(x['coverage_keep'])} | {pct(x['coverage_keep_implicit'])} | {pct(x['filler_recorded'])} | {x['spouse_recorded']}/{x['spouse_n']} | "
                     f"{x['invented_value_tokens']}/{x['value_tokens']} ({pct(x['invented_value_rate'])}) | {pct(x['link_precision'])} | {pct(x['link_recall'])} | {x['flagged_g1_extra']} {x.get('g1_rule_counts')} |")
            L.append(f"\n{m}: G0 rule counts {a['g0_rules']}; summary: {a['g0_summary']}")
            sd = escr["seeded"].get(m) or {}
            if sd:
                L.append(f"\nSeeded bad readings ({m}): " + "; ".join(f"{k}: n={v['n']}, G0 caught {v['g0']}, G1 {v['g1']}, G2 {v['g2']}, G1+C6 {v.get('g1_c6')}, G2+C6 {v.get('g2_c6')}" for k, v in sd["by_kind"].items()) + f" (G2 threshold {sd['g2_threshold']:.3f}, set at a 10% flag rate on {sd['n_clean_readings']} unseeded readings)")
        L.append(f"\nSpoof probe (home: self-confirmation): {escr.get('spoof')}")
        S["escr_spoof"] = escr.get("spoof")
    # cost ledger
    from . import llm3
    sb = llm3.spent_by("")
    L.append("\n## Spend ledger\n")
    L.append("| stage | model | calls | USD | output tokens | wall s |")
    L.append("|---|---|---|---|---|---|")
    tot = 0
    for (stg, mdl), a in sorted(sb.items()):
        tot += a["usd"]
        L.append(f"| {stg} | {mdl} | {a['calls']} | {a['usd']:.2f} | {a['out_tok']} | {a['secs']:.0f} |")
    L.append(f"| **total** | | | **{tot:.2f}** | | |")
    S["spend_total"] = tot
    S["spend"] = {f"{k[0]}|{k[1]}": v for k, v in sb.items()}
    with open(os.path.join(OUT, "tables.md"), "w") as f:
        f.write("\n".join(L) + "\n")

    def default(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, set):
            return sorted(o)
        return str(o)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(S, f, indent=1, default=default)
    log(f"[report] tables.md written; spend ${tot:.2f}")
    return S
