"""Turn results_v02/*.pkl into results_v02/tables.md and results_v02/summary.json (RESULTS_batch2.md is
hand-written from these tables). All rates are means over DISTINCT required sets (a set with two phrasings counts
once, with its mean); Wilson 95% intervals use n = number of distinct sets; seeds are pooled with sets keyed by
(seed, set_id). Paired tests are exact sign tests over distinct sets, with a cluster-bootstrap CI of the difference."""
from __future__ import annotations

import json
import os
import pickle
from collections import Counter, defaultdict

import numpy as np

from .ctx2 import CLASSES2, COMPLEX, DATA2, sign_test_sets, summarise_cls, wilson_sets
from .experiments2 import m1_analysis

SHORT = {"decision_support": "decision", "option_analysis": "option", "current_state": "current", "temporal_change": "temporal",
         "goal_tracking": "goal", "preference_recommendation": "pref", "cross_domain": "cross", "multimodal": "multimodal", "ALL": "ALL"}


def L(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def pool(by_seed: dict, arm: str):
    rows = []
    for s, d in by_seed.items():
        if arm in d:
            rows += d[arm]
    return rows


def cell(S, metric="p", ci=True):
    if S is None or S.get("n", 0) == 0:
        return "–"
    if metric == "p":
        return f"{100*S['p']:.1f} [{100*S['lo']:.0f}–{100*S['hi']:.0f}]" if ci else f"{100*S['p']:.1f}"
    return f"{100*S[metric]:.1f}"


def table(arm_rows: dict, key="ok@10", classes=CLASSES2, metric="p", ci=True, nrow=True):
    cols = list(classes) + ["ALL"]
    md = "| arm | " + " | ".join(SHORT.get(c, c) for c in cols) + " |\n|---|" + "---|" * len(cols) + "\n"
    first = None
    for name, rows in arm_rows.items():
        S = summarise_cls(rows, key, classes)
        first = first or S
        md += f"| {name} | " + " | ".join(cell(S.get(c), metric, ci) for c in cols) + " |\n"
    if nrow and first:
        md += "| *n sets (tasks)* | " + " | ".join(f"{first[c]['n']} ({first[c]['n_tasks']})" for c in cols) + " |\n"
    return md


def tests(arm_rows: dict, base: str, classes=("ALL",), key="ok@10"):
    md = "| arm vs " + base + " | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |\n|---|---|---|---|---|\n"
    out = {}
    for name, rows in arm_rows.items():
        if name == base:
            continue
        for c in classes:
            a = [r for r in arm_rows[base] if c == "ALL" or r["cls"] == c]
            b = [r for r in rows if c == "ALL" or r["cls"] == c]
            T = sign_test_sets(a, b, key)
            out[(name, c)] = T
            md += f"| {name} | {SHORT.get(c, c)} | +{T['b_better']} / −{T['a_better']} | {T['diff']:+.1f} [{T['lo']:+.1f}, {T['hi']:+.1f}] | {T['p']:.2g} |\n"
    return md, out


def per_seed_all(by_seed, arm, key="ok@10"):
    return " / ".join(f"{100*wilson_sets(d[arm], key)['p']:.1f}" for s, d in sorted(by_seed.items()) if arm in d)


def main(OUT, CONFIG):
    md, J = [], {}
    A = md.append
    A("# BrainBench v0.2 — batch 2 generated tables\n\nAll rates: mean over distinct required sets (cluster-aware), Wilson 95% over n = distinct sets, 3 seeds pooled unless stated. "
      "Paired tests: exact sign test over distinct sets; Δ with 95% cluster-bootstrap CI.\n")
    # ---------------------------------------------------------------- world stats
    A("\n## v0.2 world and tasks\n\n| seed | items | entities | keyed facts | tasks (8 classes) | stale probes |\n|---|---|---|---|---|---|\n")
    sets = defaultdict(lambda: defaultdict(set)); ntask = defaultdict(Counter); sizes = defaultdict(Counter)
    for s in (1, 2, 3):
        d = os.path.join(DATA2, f"s{s}")
        if not os.path.exists(d):
            continue
        n_items = sum(1 for _ in open(os.path.join(d, "items.jsonl")))
        n_ent = sum(1 for _ in open(os.path.join(d, "entities.jsonl")))
        n_keys = sum(1 for _ in open(os.path.join(d, "keys.jsonl")))
        ts = [json.loads(x) for x in open(os.path.join(d, "tasks.jsonl"))]
        for t in ts:
            sets[t["cls"]][s].add(t["set_id"]); ntask[t["cls"]][s] += 1
            if t["cls"] != "stale_probe":
                sizes[t["cls"]][min(t["size"], 8)] += 1
        A(f"| {s} | {n_items:,} | {n_ent} | {n_keys} | {sum(1 for t in ts if t['cls'] in CLASSES2):,} | {sum(1 for t in ts if t['cls'] == 'stale_probe')} |\n")
    A("\n| class | distinct sets per seed (s1/s2/s3) | tasks per seed | required-set sizes (pooled; 8 = 8+) |\n|---|---|---|---|\n")
    for c in CLASSES2:
        A(f"| {c} | {'/'.join(str(len(sets[c][s])) for s in (1, 2, 3))} | {'/'.join(str(ntask[c][s]) for s in (1, 2, 3))} | {', '.join(f'{k}:{v}' for k, v in sorted(sizes[c].items()))} |\n")

    # ---------------------------------------------------------------- E8a
    e8a = L(os.path.join(OUT, "e8a.pkl"))
    if e8a:
        R = e8a["rows"]; meta = e8a["meta"]
        arms = [k for k in R[1] if not k.endswith("#secs")]
        A(f"\n## E8a — first-stage retrievers, exact search (all tasks, 3 seeds)\n\nWeighted fusion alpha (on min-max BM25) tuned on seed 1 only: {meta['alpha']}. "
          f"Grid (seed 1, score = mean rec@10 + mean CR@10): {json.dumps({k: {str(a): round(v, 3) for a, v in g.items()} for k, g in meta.items() if k.startswith('alpha_grid')})}. "
          f"Best first stage chosen on seed 1: **{meta['best']}**.\n\n### CR@10 %\n\n")
        pooled = {a: pool(R, a) for a in arms}
        A(table(pooled))
        A("\n### Item recall@10 %\n\n" + table(pooled, metric="item_recall", ci=False, nrow=False))
        A("\n### Held-out seeds only (2 and 3), CR@10 % — the tuned fusion cannot have overfitted these\n\n")
        A(table({a: pool({s: R[s] for s in (2, 3)}, a) for a in arms}, ci=True))
        A("\n### Per-seed ALL CR@10 (s1 / s2 / s3)\n\n| arm | per seed |\n|---|---|\n" + "".join(f"| {a} | {per_seed_all(R, a)} |\n" for a in arms))
        A("\n### Depth diagnostic: item recall / CR at depth d (pooled)\n\n| arm | class | d=10 | d=20 | d=50 | d=100 | d=200 |\n|---|---|---|---|---|---|---|\n")
        for a in ("BM25", "RRF(BM25+LSA) (batch-1 default)", "Qwen3-Emb-0.6B", meta["best"]):
            for c in CLASSES2:
                rr = [r for r in pooled[a] if r["cls"] == c]
                A(f"| {a} | {SHORT[c]} | " + " | ".join(f"{100*np.mean([r[f'rec@{d}'] for r in rr]):.0f} / {100*wilson_sets(rr, f'ok@{d}')['p']:.0f}" for d in (10, 20, 50, 100, 200)) + " |\n")
        md_t, T = tests(pooled, "BM25", ("ALL",))
        A("\n### Paired tests vs BM25\n\n" + md_t)
        md_t, T2 = tests({k: pooled[k] for k in ("bge-small", "Qwen3-Emb-0.6B", "Qwen3-Emb-0.6B, task instruction")}, "bge-small", ("ALL",) + tuple(CLASSES2))
        A("\n### Qwen3 vs bge-small (paired, per class)\n\n" + md_t)
        md_t, _ = tests({k: pooled[k] for k in ("Qwen3-Emb-0.6B", "rrf(BM25+qwen3-emb)", "wsum(BM25+qwen3-emb)")}, "Qwen3-Emb-0.6B", ("ALL",) + tuple(CLASSES2))
        A("\n### Hybrid vs dense-only (Qwen3), paired\n\n" + md_t)
        md_t, _ = tests({k: pool({s: R[s] for s in (2, 3)}, k) for k in ("rrf(BM25+qwen3-emb)", "wsum(BM25+qwen3-emb)")}, "rrf(BM25+qwen3-emb)", ("ALL",))
        A("\n### Tuned weighted fusion vs RRF, held-out seeds 2–3\n\n" + md_t)
        A("\n### Query-time cost per task (exact search over ~11k items, includes BM25 + dense matmul; embeddings cached)\n\n| arm | ms/task |\n|---|---|\n" +
          "".join(f"| {a} | {1000*np.mean([R[s][a + '#secs'] for s in R]):.1f} |\n" for a in arms))
        J["e8a"] = {a: summarise_cls(pooled[a]) for a in arms}

    # ---------------------------------------------------------------- E8b
    e8b = L(os.path.join(OUT, "e8b.pkl"))
    if e8b:
        R = e8b["rows"]
        arms = [k for k in R[1] if not k.endswith("#wall")]
        A(f"\n## E8b — rerankers on the top-{CONFIG['rerank_depth']} of {e8b['first_stage']} (stratified distinct sets: {CONFIG['rerank_sets_per_class']} per class per seed)\n\n### CR@10 %\n\n")
        pooled = {a: pool(R, a) for a in arms}
        A(table(pooled))
        A("\n### Item recall@10 %\n\n" + table(pooled, metric="item_recall", ci=False, nrow=False))
        A(f"\nCeiling: CR@{CONFIG['rerank_depth']} of the candidate pool (no reranker can exceed it): " +
          ", ".join(f"{SHORT[c]} {100*wilson_sets([r for r in pooled['none'] if r['cls']==c], 'ok@' + str(CONFIG['rerank_depth']))['p']:.0f}" for c in CLASSES2) + "\n")
        md_t, T = tests(pooled, "none", ("ALL",) + tuple(CLASSES2))
        A("\n### Paired tests vs no reranker\n\n" + md_t)
        h12 = {k: pooled[k] for k in pooled if k.startswith("qwen3-reranker")}
        if len(h12) == 2:
            md_t, _ = tests(h12, "qwen3-reranker", ("ALL",) + tuple(CLASSES2))
            A("\n### H12: scope-templated vs generic instruction (Qwen3-Reranker)\n\n" + md_t)
        mx = {k: pool({1: R[1]}, k) for k in R[1] if k.startswith("mxbai") and not k.endswith("#wall")}
        if len(mx) == 2:
            md_t, _ = tests(mx, "mxbai-rerank-base-v2", ("ALL",))
            A("\n### Instruction check on mxbai (seed 1 only)\n\n" + md_t)
        A("\nReranker throughput (uncached pairs only) is in the component table at the end; wall-clock per variant including first-stage and cache hits: " +
          "; ".join(f"{k[:-5]} {sum(R[s_][k][0] for s_ in R if k in R[s_]):.0f} s" for k in R[1] if k.endswith("#wall")) + "\n")
        J["e8b"] = {a: summarise_cls(pooled[a]) for a in arms}

    # ---------------------------------------------------------------- E8c
    e8c = L(os.path.join(OUT, "e8c.pkl"))
    if e8c:
        R = e8c["rows"]
        arms = [k for k in R[1] if "@" not in k]
        pooled = {a: pool(R, a) for a in arms}
        A(f"\n## E8c — batch-1 arms re-run with the best real first stage ({e8c['first_stage']}), equal k=10, all tasks, 3 seeds\n\n### CR@10 %\n\n")
        A(table(pooled))
        A("\n### Item recall@10 %\n\n" + table(pooled, metric="item_recall", ci=False, nrow=False))
        md_t, T = tests(pooled, "query-only", ("ALL",) + tuple(CLASSES2))
        A("\n### Paired tests vs query-only\n\n" + md_t)
        J["e8c_tests"] = {f"{k[0]}|{k[1]}": v for k, v in T.items()}
        # prefix coverage
        A("\n### Mean share of required items covered by the pinned prefix alone\n\n| arm | " + " | ".join(SHORT[c] for c in CLASSES2) + " |\n|---|" + "---|" * len(CLASSES2) + "\n")
        for a in arms:
            if not any("prefix_cov" in r and r.get("prefix_cov") is not None for r in pooled[a]) or a.startswith(("query", "declared")):
                continue
            A(f"| {a} | " + " | ".join(f"{100*np.mean([r['prefix_cov'] for r in pooled[a] if r['cls']==c]):.0f}" for c in CLASSES2) + " |\n")
        lsa = e8c.get("lsa_rows")
        if lsa:
            pl = {a: pool(lsa, a) for a in lsa[1]}
            A("\n### Same arms with the batch-1 retriever (RRF BM25+LSA) on v0.2, CR@10 %\n\n" + table(pl, ci=False))
            A("\n### Real embedder vs LSA, per arm (ALL, paired over sets)\n\n| arm | LSA retriever | real retriever | Δ pp [CI] | p |\n|---|---|---|---|---|\n")
            for a in pl:
                if a in pooled:
                    T_ = sign_test_sets(pl[a], pooled[a])
                    A(f"| {a} | {100*wilson_sets(pl[a])['p']:.1f} | {100*wilson_sets(pooled[a])['p']:.1f} | {T_['diff']:+.1f} [{T_['lo']:+.1f}, {T_['hi']:+.1f}] | {T_['p']:.2g} |\n")
        # k sweep
        A("\n### H9 / k sweep: CR@k (query-only vs cards + static slots)\n\n| arm | " + " | ".join(SHORT[c] for c in CLASSES2) + " | ALL |\n|---|" + "---|" * (len(CLASSES2) + 1) + "\n")
        for a, key in (("query-only", "ok@10"), ("query-only@20", "ok@20"), ("query-only@30", "ok@30"), ("cards(<=3) + static slots + query", "ok@10"), ("cards+slots@20", "ok@20"), ("cards+slots@30", "ok@30")):
            S = summarise_cls(pool(R, a), key)
            A(f"| {a} | " + " | ".join(cell(S[c]) for c in CLASSES2 + ["ALL"]) + " |\n")
        # by size
        A("\n### CR@10 by required-set size (cards + static slots + query; pooled)\n\n| size | n sets | CR@10 | item recall | p^m prediction |\n|---|---|---|---|---|\n")
        rr = pool(R, "cards(<=3) + static slots + query")
        pall = np.mean([r["rec@10"] for r in rr])
        for m in sorted({min(r["size"], 8) for r in rr}):
            x = [r for r in rr if min(r["size"], 8) == m]
            S = wilson_sets(x)
            A(f"| {m}{'+' if m == 8 else ''} | {S['n']} | {cell(S)} | {100*np.mean([r['rec@10'] for r in x]):.0f} | {100*np.mean([pall**r['size'] for r in x]):.0f} |\n")
        # origin
        O = e8c["origin"]
        A("\n### I8 — origin context for media (multimodal, all tasks, 3 seeds), CR@10 %\n\n| index | retriever | all | caption sufficient | needs origin-only item |\n|---|---|---|---|---|\n")
        for a in O[1]:
            rows = pool(O, a)
            sub = lambda nm: wilson_sets([r for r in rows if r["sub"] == nm])
            A(f"| {a.split('/')[0]} | {a.split('/')[1]} | {cell(wilson_sets(rows))} (n={wilson_sets(rows)['n']}) | {cell(sub('caption sufficient'))} (n={sub('caption sufficient')['n']}) | {cell(sub('needs origin-only'))} (n={sub('needs origin-only')['n']}) |\n")
        for meth in ("bm25", "dense", "rrf", "wsum"):
            T_ = sign_test_sets(pool(O, f"noorig/{meth}"), pool(O, f"base/{meth}"))
            A(f"\nPaired ({meth}): with origin +{T_['b_better']} / −{T_['a_better']} sets, Δ {T_['diff']:+.1f} pp [{T_['lo']:+.1f}, {T_['hi']:+.1f}], p={T_['p']:.2g}.\n")
        J["e8c"] = {a: summarise_cls(pooled[a]) for a in arms}
        # M1
        m1 = m1_analysis({"query-only": pool(R, "query-only"), "cards + static slots": pool(R, "cards(<=3) + static slots + query"),
                          "query-only@30": [dict(r, **{"ok@10": r["ok@30"], "rec@10": r["rec@30"]}) for r in pool(R, "query-only@30")]})
        A("\n## M1 — measured CR@k vs independence prediction E[p^m]\n\n`p_item` = class item recall; `pred(class p)` = mean over tasks of p_item^m; `pred(size p)` uses the item recall of tasks with the same class and size; "
          "`rho` = intra-task correlation of item successes implied by the variance of the found count (beta-binomial; 0 = independent, >0 = items succeed/fail together).\n\n")
        for arm, res in m1.items():
            A(f"\n**{arm}**\n\n| class | n tasks | p_item | measured CR | pred (class p) | pred (size p) | measured − pred | rho |\n|---|---|---|---|---|---|---|---|\n")
            for c, v in res.items():
                A(f"| {SHORT[c]} | {v['n']} | {100*v['p_item']:.1f} | {100*v['measured']:.1f} | {100*v['pred_class_p']:.1f} | {100*v['pred_size_p']:.1f} | {100*(v['measured']-v['pred_class_p']):+.1f} | {v['rho']:.2f} |\n")
        J["m1"] = m1
        # item-level independence model (leave-one-task-out per-item success rates)
        from .experiments2 import m1_item_model
        req = {}
        for sd in (1, 2, 3):
            for x in open(os.path.join(DATA2, f"s{sd}", "tasks.jsonl")):
                t = json.loads(x)
                req[(sd, t["id"])] = t["required"]
        A("\n### M1 with item-specific p (product of each required item's leave-one-task-out hit rate in the same arm, class and seed)\n\n"
          "| arm | class | measured CR@10 | pred: Π p_item(i) | pred: p_class^m | share of items with own estimate |\n|---|---|---|---|---|---|\n")
        for arm, nm in (("query-only", "query-only"), ("cards(<=3) + static slots + query", "cards + static slots"), ("cards(<=3) + query", "cards")):
            rows = [dict(r, _req=req[(r["seed"], r["id"])]) for r in pool(R, arm)]
            mi = m1_item_model(rows)
            base = m1_analysis({nm: pool(R, arm)})[nm]
            for c, v in mi.items():
                A(f"| {nm} | {SHORT[c]} | {100*v['measured']:.1f} | {100*v['pred_item']:.1f} | {100*base[c]['pred_class_p']:.1f} | {100*v['share_items_with_loo']:.0f}% |\n")

    # ---------------------------------------------------------------- E8d router
    e8d = L(os.path.join(OUT, "e8d.pkl"))
    if e8d and e8c:
        Rd = e8d["rows"]
        arms_d = {"query-only": pool(e8c["rows"], "query-only"), "cards(<=3) + query": pool(e8c["rows"], "cards(<=3) + query"),
                  "cards(<=3) + static slots + query": pool(e8c["rows"], "cards(<=3) + static slots + query")}
        for a in Rd[1]:
            arms_d[a] = pool(Rd, a)
        A("\n## N5 — class-conditional prefix via a two-regex router (temporal regex from batch 1 + a media-word regex), CR@10 %\n\n" + table(arms_d))
        md_t, _ = tests(arms_d, "cards(<=3) + query", ("ALL",) + tuple(CLASSES2))
        A("\n### Paired vs cards(<=3) + query (best fixed arm)\n\n" + md_t)
        rt = Counter()
        for sd, d in e8d["routing"].items():
            for k, v in d.items():
                rt[k] += v
        A("\nRouting decisions (tasks, pooled): " + ", ".join(f"{k}: {v}" for k, v in sorted(rt.items())) + "\n")

    # ---------------------------------------------------------------- E8e oracle ceilings
    e8e = L(os.path.join(OUT, "e8e.pkl"))
    if e8e and e8c:
        sh = defaultdict(lambda: [0.0, 0.0, 0])
        for sd, d in e8e["share"].items():
            for c, v in d.items():
                sh[c][0] += v["fact"] * v["n"]; sh[c][1] += v["media"] * v["n"]; sh[c][2] += v["n"]
        A("\n## Structural ceilings (oracle analyses; no model calls)\n\nShare of required items that are keyed-fact versions (reachable by slots/cards) vs media vs other free text:\n\n| class | keyed facts | media | free text (notes, emails, chats, meetings, preferences) |\n|---|---|---|---|\n")
        for c in CLASSES2:
            f_, m_, n_ = sh[c]
            A(f"| {SHORT[c]} | {100*f_/n_:.0f}% | {100*m_/n_:.0f}% | {100*(n_-f_-m_)/n_:.0f}% |\n")
        arms_o = {"cards(<=3) + query (lexical linker)": pool(e8c["rows"], "cards(<=3) + query"), "cards(<=3) + static slots + query": pool(e8c["rows"], "cards(<=3) + static slots + query")}
        for a in e8e["rows"][1]:
            arms_o[a] = pool(e8e["rows"], a)
        A("\n### CR@10 % with oracle structure\n\n" + table(arms_o))
        A("\n### Item recall@10 %\n\n" + table(arms_o, metric="item_recall", ci=False, nrow=False))
        # residual: recall of the NON-fact required items (what search must find) under oracle slots
        itype = {}
        req = {}
        for sd in (1, 2, 3):
            for x in open(os.path.join(DATA2, f"s{sd}", "items.jsonl")):
                it = json.loads(x)
                itype[(sd, it["id"])] = "media" if it.get("media") else ("fact" if it["type"] == "fact" else "text")
            for x in open(os.path.join(DATA2, f"s{sd}", "tasks.jsonl")):
                t = json.loads(x)
                req[(sd, t["id"])] = t["required"]
        A("\n### Residual recall: share of required FREE-TEXT items in the top-10 (search's share of the job), and CR over tasks restricted to their free-text items\n\n"
          "| arm | " + " | ".join(SHORT[c] for c in ("decision_support", "option_analysis", "goal_tracking", "preference_recommendation", "cross_domain")) + " |\n|---|---|---|---|---|---|\n")
        for a in ("oracle slots: every required keyed fact pinned + query", "cards(<=3) + static slots + query"):
            rows = arms_o[a]
            cells = []
            for c in ("decision_support", "option_analysis", "goal_tracking", "preference_recommendation", "cross_domain"):
                hit = tot = ok = n = 0
                for r in rows:
                    if r["cls"] != c:
                        continue
                    ft = [i for i in req[(r["seed"], r["id"])] if itype[(r["seed"], i)] == "text"]
                    if not ft:
                        continue
                    f = set(r["found"])
                    hit += sum(i in f for i in ft); tot += len(ft); ok += all(i in f for i in ft); n += 1
                cells.append(f"{100*hit/max(tot,1):.0f}% items / {100*ok/max(n,1):.0f}% tasks (n={n})")
            A(f"| {a} | " + " | ".join(cells) + " |\n")

    # ---------------------------------------------------------------- E6
    e6 = L(os.path.join(OUT, "e6.pkl"))
    if e6 and e6.get("nonllm"):
        R = e6["nonllm"]
        pooled = {a: pool(R, a) for a in R[1]}
        A(f"\n## E6a — model-free arms on complex classes ({CONFIG['e6_sets_per_class']} distinct sets per class per seed, 3 seeds)\n\n### CR@10 %\n\n")
        A(table(pooled, classes=COMPLEX))
        A("\n### Item recall@10 %\n\n" + table(pooled, classes=COMPLEX, metric="item_recall", ci=False, nrow=False))
        A("\n### CR@20 %\n\n" + table(pooled, key="ok@20", classes=COMPLEX, ci=False, nrow=False))
        md_t, _ = tests(pooled, "one-shot", ("ALL",) + tuple(COMPLEX))
        A("\n### Paired vs one-shot (best hybrid)\n\n" + md_t)
        md_t, _ = tests({k: pooled[k] for k in pooled if k.startswith("cards+slots")}, "cards+slots + one-shot", ("ALL",) + tuple(COMPLEX))
        A("\n### With the structural prefix, paired vs cards+slots + one-shot\n\n" + md_t)
        J["e6a"] = {a: summarise_cls(pooled[a], classes=COMPLEX) for a in pooled}
    if e6 and e6.get("rows"):
        R = e6["rows"]
        seeds = sorted(R)
        pooled = {a: pool(R, a) for a in R[seeds[0]]}
        A(f"\n## E6b — LLM decomposition and gap-check (seeds {seeds}; {CONFIG.get('e6_llm_sets_per_class')} distinct sets per complex class; LLM = {CONFIG['llm']}, greedy, thinking off, few-shot prompts)\n\n### CR@10 %\n\n")
        A(table(pooled, classes=COMPLEX))
        A("\n### Item recall@10 %\n\n" + table(pooled, classes=COMPLEX, metric="item_recall", ci=False, nrow=False))
        A("\n### CR@20 %\n\n" + table(pooled, key="ok@20", classes=COMPLEX, ci=False, nrow=False))
        md_t, _ = tests(pooled, "one-shot", ("ALL",) + tuple(COMPLEX))
        A("\n### Paired vs one-shot\n\n" + md_t)
        md_t, _ = tests(pooled, "one-shot", ("ALL",), key="rec@10")
        A("\n### Paired vs one-shot, item recall@10\n\n" + md_t)
        md_t, _ = tests({k: pooled[k] for k in pooled if k.startswith("cards+slots")}, "cards+slots + one-shot", ("ALL",))
        A("\n### With the structural prefix, paired vs cards+slots + one-shot\n\n" + md_t)
        A("\n### Calls and latency (LLM on this CPU)\n\n| seed | decomposition calls | wall s | mean sub-queries | share at cap (4) | gap-check calls (all rounds) | gap wall s | gap calls/task | gap queries/task | round-2 continued |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for sd, st in e6["stats"].items():
            g = st["gap"]
            A(f"| {sd} | {st['decompose']['calls']} | {st['decompose']['wall']:.0f} | {st['decompose']['mean_subqueries']:.2f} | {100*st['decompose']['share_at_cap']:.0f}% | {sum(x['calls'] for x in g)} | {sum(x['wall'] for x in g):.0f} | {st['gap_calls_per_task']:.2f} | {st['gap_queries_per_task']:.2f} | {g[-1].get('continued', '–') if len(g) > 1 else '–'} |\n")
        A("\n### Examples\n\n")
        for e in e6["examples"].get(seeds[0], [])[:8]:
            A(f"- **{e['cls']}** — \"{e['q']}\"\n  - decomposition: {e['decomposition']}\n  - gap-check: {e['gap_queries']}\n  - facets: {e['facets']}\n")
        J["e6b"] = {a: summarise_cls(pooled[a], classes=COMPLEX) for a in pooled}

    # ---------------------------------------------------------------- N4
    n4 = L(os.path.join(OUT, "n4.pkl"))
    if n4:
        R = n4["res"]
        names = list(dict.fromkeys(nm for sd in sorted(R) for nm in R[sd]))
        A(f"\n## N4 — entity linkers ({CONFIG['n4_sets_per_class']} distinct sets per class per seed)\n\n### Linker recall of required fact entities (mean per task; share of tasks with ALL required entities linked)\n\n")
        A("| linker | " + " | ".join(SHORT[c] for c in CLASSES2) + " | ALL | all-linked (ALL) | precision | mean entities linked | seeds |\n|---|" + "---|" * (len(CLASSES2) + 5) + "\n")
        for nm in names:
            lk = [x for s in R if nm in R[s] for x in R[s][nm]["linker"]]
            A(f"| {nm} | " + " | ".join(f"{100*np.mean([x['rec'] for x in lk if x['cls']==c]):.0f}" if any(x['cls'] == c for x in lk) else "–" for c in CLASSES2) +
              f" | {100*np.mean([x['rec'] for x in lk]):.0f} | {100*np.mean([x['all'] for x in lk]):.0f} | {100*np.mean([R[s][nm]['precision'] for s in R if nm in R[s]]):.0f} | {np.mean([R[s][nm]['mean_linked'] for s in R if nm in R[s]]):.1f} | seeds {[s for s in R if nm in R[s]]} |\n")
        p3 = {nm: [r for s in R if nm in R[s] for r in R[s][nm]["rows_cards3_slots"]] for nm in names}
        p5 = {nm: [r for s in R if nm in R[s] for r in R[s][nm]["rows_cards5"]] for nm in names}
        A("\n### CR@10 with cards(<=3) + static slots + query, by linker\n\n" + table(p3))
        md_t, _ = tests(p3, "lexical", ("ALL",) + tuple(CLASSES2))
        A("\n(paired tests use only the seeds both linkers ran on)\n\n" + md_t)
        A("\n### CR@10 with cards(<=5) + query (no static slots), by linker\n\n" + table(p5, ci=False))
        md_t, _ = tests(p5, "lexical", ("ALL",))
        A("\n" + md_t)
        A("\nLLM linker cost: " + "; ".join(f"seed {s}: {st.get('llm_calls')} calls, {st.get('llm_wall', 0):.0f} s" for s, st in n4["stats"].items() if st) + "\n")

    # ---------------------------------------------------------------- H13
    h13 = L(os.path.join(OUT, "h13.pkl"))
    if h13:
        R = h13["rows"]
        pooled = {a: pool(R, a) for a in R[1]}
        A(f"\n## H13-lite — index-time origin enrichment vs query-side LLM expansion (multimodal, seed 1, {CONFIG.get("h13_sets")} distinct sets, best first stage)\n\n| arm | CR@10 | item recall@10 | n sets |\n|---|---|---|---|\n")
        for a, rows in pooled.items():
            S = summarise_cls(rows, classes=["multimodal"])["multimodal"]
            A(f"| {a} | {cell(S)} | {100*S['item_recall']:.1f} | {S['n']} |\n")
        ks = list(pooled)
        for a, b in ((ks[0], ks[1]), (ks[0], ks[2]), (ks[2], ks[3]), (ks[1], ks[2])):
            T_ = sign_test_sets(pooled[a], pooled[b])
            A(f"\n{b} vs {a}: +{T_['b_better']} / −{T_['a_better']}, Δ {T_['diff']:+.1f} pp [{T_['lo']:+.1f}, {T_['hi']:+.1f}], p={T_['p']:.2g}.\n")
        A("\nExpansion cost: " + "; ".join(f"seed {s}: {st['calls']} calls, {st['wall']:.0f} s" for s, st in h13["stats"].items()) + "\n")

    # ---------------------------------------------------------------- H11
    h11 = L(os.path.join(OUT, "h11.pkl"))
    if h11:
        R = h11["rows"]
        pooled = {a: pool(R, a) for a in R[1]}
        st = h11["stats"]
        A(f"\n## H11-lite — SigLIP2 image vectors vs text twins on synthetic TEXT-BEARING images (whiteboards, menu boards, receipts, report pages rendered from their OCR text); "
          f"within-media search; {sum(v['n_tasks'] for v in st.values())} tasks over 3 seeds, {st[1]['n_media']} rendered media items per seed\n\n| arm | CR@10 | item recall@10 | n sets |\n|---|---|---|---|\n")
        for a, rows in pooled.items():
            S = summarise_cls(rows, classes=["multimodal"])["multimodal"]
            A(f"| {a} | {cell(S)} | {100*S['item_recall']:.1f} | {S['n']} |\n")
        ks = list(pooled)
        for a, b_ in ((ks[2], ks[4]), (ks[1], ks[5]), (ks[2], ks[3])):
            T_ = sign_test_sets(pooled[a], pooled[b_])
            A(f"\n{b_} vs {a}: +{T_['b_better']} / −{T_['a_better']}, Δ {T_['diff']:+.1f} pp [{T_['lo']:+.1f}, {T_['hi']:+.1f}], p={T_['p']:.2g}.\n")
        A("\nSigLIP2-base image encoding on this CPU (fp32): " + ", ".join(f"{v['img_per_s']:.1f} img/s" for v in st.values()) + "\n")

    # ---------------------------------------------------------------- I2 kill test
    i2 = L(os.path.join(OUT, "i2.pkl"))
    if i2:
        rows = [dict(r, seed=s) for s, rr in i2["rows"].items() for r in rr]
        A("\n## I2 kill test — LLM-written cards (from dated notes) vs code-compiled cards (from keyed heads)\n\n"
          "Checks: keyed facts with >=2 versions where the notes given to the model quote BOTH the current and a superseded value. "
          "Code-compiled cards state only the current value by construction (0% stale).\n\n| input order | key checks | states current only | states stale only | states both | states neither | stale value present |\n|---|---|---|---|---|---|---|\n")
        from .ctx2 import wilson_frac
        for order in ("random", "newest-first"):
            rr = [r for r in rows if r["order"] == order]
            n = len(rr)
            if not n:
                continue
            co = sum(r["current"] and not r["stale"] for r in rr); so = sum(r["stale"] and not r["current"] for r in rr)
            bo = sum(r["stale"] and r["current"] for r in rr); ne = n - co - so - bo
            p, lo, hi = wilson_frac(so + bo, n)
            A(f"| {order} | {n} | {100*co/n:.1f}% | {100*so/n:.1f}% | {100*bo/n:.1f}% | {100*ne/n:.1f}% | **{100*p:.1f}% [{100*lo:.1f}–{100*hi:.1f}]** |\n")
        A("\nExample model-written cards (seed 1):\n\n")
        for e in i2["examples"].get(1, [])[:2]:
            A(f"```\n[{e['entity']} / {e['order']}]\n{e['card']}\n```\n")

    # ---------------------------------------------------------------- timing
    tp = os.path.join(os.path.dirname(OUT), "cache_v02", "timing.json")
    if os.path.exists(tp):
        T = json.load(open(tp))
        A("\n## Component throughput (pooled over both hosts: host A = Xeon 2.1 GHz with AMX/bf16; host B = Xeon 2.8 GHz without bf16, fp32 rerankers, emulated-bf16 LLM, shared CPU; see RESULTS_batch2.md for the per-host split)\n\n| component | items | seconds | items/s | ms/item |\n|---|---|---|---|---|\n")
        for k, v in sorted(T.items()):
            if k.startswith("llm-tokens-in"):
                continue
            n = sum(x[0] for x in v); s_ = sum(x[1] for x in v)
            if n:
                A(f"| {k} | {n:,} | {s_:.0f} | {n/max(s_,1e-9):.1f} | {1000*s_/n:.0f} |\n")
    with open(os.path.join(OUT, "tables.md"), "w") as f:
        f.write("".join(md))

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        return o
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(clean(J), f, indent=1, default=float)
    print("wrote", os.path.join(OUT, "tables.md"))
