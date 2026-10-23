"""Run everything: generate BrainBench v0, run E0-E5, E7 and the I8 check, write results/*.json
and results/tables.md (RESULTS.md is hand-written from these tables).

    python run_all.py            # full run (~2-3 minutes on 2 CPUs)
    python run_all.py --no-gen   # reuse data/
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bb import world  # noqa: E402
from bb.brain import CLASSES, Brain, World  # noqa: E402
from bb.common import RESULTS_DIR, fmt_wilson, mcnemar_exact, wilson  # noqa: E402
from bb import experiments as X  # noqa: E402

COLS = CLASSES + ["ALL"]
SHORT = {"decision_support": "decision", "option_analysis": "option", "current_state": "current", "temporal_change": "temporal",
         "goal_tracking": "goal", "preference_recommendation": "pref", "cross_domain": "cross", "multimodal": "multimodal", "ALL": "ALL"}


def table(arms: dict, cols=COLS, metric="p", ci=True) -> str:
    head = "| arm | " + " | ".join(SHORT.get(c, c) for c in cols) + " |\n|---|" + "---|" * len(cols) + "\n"
    rows = []
    for name, S in arms.items():
        cells = []
        for c in cols:
            v = S.get(c)
            if v is None:
                cells.append("–")
            elif metric == "p" and ci:
                cells.append(f"{100*v['p']:.1f} [{100*v['lo']:.0f}–{100*v['hi']:.0f}]")
            elif metric == "p":
                cells.append(f"{100*v['p']:.1f}")
            else:
                cells.append(f"{100*v[metric]:.1f}")
        rows.append(f"| {name} | " + " | ".join(cells) + " |")
    ns = arms[next(iter(arms))]
    rows.append("| *n* | " + " | ".join(str(ns[c]["n"]) if c in ns else "–" for c in cols) + " |")
    return head + "\n".join(rows) + "\n"


def mcnemar_lines(rows: dict, base: str, order, tasks_by_id, classes=("ALL",)) -> str:
    out = []
    for name, r in rows.items():
        if name == base:
            continue
        for c in classes:
            idx = [i for i, tid in enumerate(order) if c == "ALL" or tasks_by_id[tid]["cls"] == c]
            a = [rows[base][i] for i in idx]
            b = [r[i] for i in idx]
            n01, n10, p = mcnemar_exact(a, b)
            out.append(f"| {name} | {c} | +{n01} / −{n10} | {p:.3g} |")
    return "| arm vs base | class | wins / losses | exact McNemar p |\n|---|---|---|---|\n" + "\n".join(out) + "\n"


def main():
    t_all = time.time()
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if "--no-gen" not in sys.argv:
        t = time.time(); world.main(); print(f"[E0] world generated in {time.time()-t:.1f}s")
    w = World()
    tasks_by_id = {t["id"]: t for t in w.tasks}
    b = Brain(w)
    s = X.Searcher(b)
    R = {}
    md = []

    def step(name, fn, *a):
        t = time.time()
        r = fn(*a)
        print(f"[{name}] {time.time()-t:.1f}s")
        R[name] = r
        return r

    # ---------------- E0
    from collections import Counter
    md.append("# BrainBench v0 — generated tables\n")
    md.append(f"Items: {len(w.items)} · entities: {len(w.entities)} · keyed facts: {len(w.keys)} · tasks: {len(w.tasks)}\n")
    md.append("Item types: " + ", ".join(f"{k} {v}" for k, v in Counter(i['type'] for i in w.items).most_common()) + "\n")
    md.append("Tasks per class: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(t['cls'] for t in w.tasks).items())) + "\n")
    md.append("Required-set sizes: " + ", ".join(f"{k}:{v}" for k, v in sorted(Counter(t['size'] for t in w.tasks if t['cls'] != 'stale_probe').items())) + "\n")
    e0 = step("E0", X.e0_baselines, w, b)
    md.append("\n## E0 — baseline retrievers (keyed store, access pre-filter, temporal router, no scope), CR@10 % [Wilson 95%]\n")
    md.append(table({k: v for k, v in e0.items() if k != "router"}))
    md.append("\nItem-level recall@10 (share of required items present):\n")
    md.append(table({k: v for k, v in e0.items() if k != "router"}, metric="item_recall"))
    r = e0["router"]
    md.append(f"\nTemporal router (regex): fires on {r['tp']}/{r['n_temporal']} temporal_change tasks; false-fires on {r['fp']}/{r['n_non_temporal']} others.\n")
    dep = step("E0-depth", X.e0_depth, w, b, s)
    md.append("\n### E0 — depth diagnostic (default hybrid): item recall / CR at depth d\n")
    md.append("| class | " + " | ".join(f"d={d}" for d in (10, 20, 50, 100, 200)) + " |\n|---|---|---|---|---|---|\n")
    for c in CLASSES:
        md.append(f"| {SHORT[c]} | " + " | ".join(f"{100*dep[c][str(d)]['item_recall']:.0f} / {100*dep[c][str(d)]['cr']:.0f}" for d in (10, 20, 50, 100, 200)) + " |\n")

    from bb import diagnostics as D
    lo = step("E0-overlap", D.lexical_overlap, w)
    la = step("E0-linker", D.linker_accuracy, w)
    vl = step("E4-vector", D.vector_stats_leak, w)
    md.append("\n### E0 — gold-set lexical difficulty and entity-linker recall\n\n| class | required items with ZERO token overlap with the request | tasks with ≥1 such item | linker recall of required fact entities |\n|---|---|---|---|\n")
    for c in CLASSES:
        md.append(f"| {SHORT[c]} | {100*lo[c]['items_zero_overlap']:.0f}% | {100*lo[c]['tasks_with_a_zero_overlap_item']:.0f}% | {('%.0f%%' % (100*la[c])) if c in la else '–'} |\n")

    # ---------------- E1
    e1 = step("E1", X.e1_write_paths, w, b, s)
    n = e1["arms"][0]["n"]
    md.append(f"\n## E1 — write paths on stale probes (n={n}), % [Wilson 95%]\n")
    md.append("Columns: **stale-fact** = a superseded version of the same key ranks above the head (or head absent and old version in top-10); "
              "**stale-trap** = a free-text note quoting an old value ranks above the head; **stale-summary** = a derived summary holding an old value ranks above the head; "
              "**head miss** = current version not in top-10; **first value stale** = the first value-bearing item in the top-10 carries an old value (n = probes where any value-bearing item surfaced).\n\n")
    md.append("| arm | stale-fact | stale-trap | stale-summary | head miss@10 | first value stale |\n|---|---|---|---|---|---|\n")
    for a in e1["arms"]:
        f = lambda key: f"{100*a[key]['p']:.1f} [{100*a[key]['lo']:.1f}–{100*a[key]['hi']:.1f}]"
        fv = a["first_value_stale"]
        md.append(f"| {a['arm']} | {f('stale_fact')} | {f('stale_trap')} | {f('stale_sum')} | {f('head_miss')} | {fv['k']}/{fv['n']} = {100*fv['p']:.1f} [{100*fv['lo']:.1f}–{100*fv['hi']:.1f}] |\n")
    hf = {a["arm"]: a["rows"] for a in e1["arms"]}
    md.append("\nPaired head-found@10 comparisons (exact McNemar):\n\n| A | B | B finds head, A not / A finds, B not | p |\n|---|---|---|---|\n")
    for A_, B_ in (("(a) keyed upsert (superseded out of live index)", "I3 alone: add-only + forward-to-head"),
                   ("(a)+I3+mention-forwarding (traps pull in head)", "add-only + I3 forward + mention-forwarding (all versions indexed)"),
                   ("(a) keyed upsert (superseded out of live index)", "(a)+I3+mention-forwarding (traps pull in head)"),
                   ("(a) keyed upsert (superseded out of live index)", "(a)+I3 + stale-mention suppression (extraction recall 90%)")):
        n01, n10, p = mcnemar_exact(hf[A_], hf[B_])
        md.append(f"| {A_} | {B_} | {n01} / {n10} | {p:.3g} |\n")
    md.append(f"\nStale summaries: {e1.get('summary_docs')} entity summaries generated at month 6 hold {e1.get('stale_summary_values')} values that were later superseded.\n")
    md.append("\nWrite path vs temporal_change CR@10:\n\n| store | CR@10 temporal_change |\n|---|---|\n")
    for k, v in e1["temporal"].items():
        md.append(f"| {k} | {fmt_wilson(v['k'], v['n'])} (n={v['n']}) |\n")

    # ---------------- E2
    e2 = step("E2", X.e2_scope, w, b, s)
    md.append("\n## E2 — scope modes, CR@10 % [Wilson 95%]\n")
    md.append(table(e2["arms"]))
    md.append("\nItem-level recall@10:\n")
    md.append(table(e2["arms"], metric="item_recall"))
    md.append("\nHard-filter ceiling (share of tasks whose required items all sit in the declared scope group): "
              + ", ".join(f"{SHORT[k]} {100*v:.0f}%" for k, v in sorted(e2["hard_ceiling"].items())) + "\n")
    md.append("\nScope inference accuracy (vs declared primary scope):\n\n| method | correct | abstain | prediction ∈ required groups |\n|---|---|---|---|\n")
    for k, v in e2["inference"].items():
        md.append(f"| {k} | {fmt_wilson(v['correct'], v['n'])} | {v['abstain']} | {fmt_wilson(v['in_required_groups'], v['n'])} |\n")
    md.append("\nPaired tests vs 'none':\n\n")
    md.append(mcnemar_lines(e2["rows"], "none (access filter only)", e2["order"], tasks_by_id, ("ALL", "cross_domain", "current_state", "temporal_change")))

    # ---------------- E3
    e3 = step("E3", X.e3_assembly, w, b, s)
    md.append("\n## E3 — context assembly at equal k=10, CR@10 % [Wilson 95%]\n")
    md.append(table(e3["arms"]))
    md.append("\nItem-level recall@10:\n")
    md.append(table(e3["arms"], metric="item_recall"))
    md.append("\nMean share of required items covered by the prefix (packet/slots/cards) alone:\n\n")
    md.append("| prefix | " + " | ".join(SHORT[c] for c in CLASSES) + " |\n|---|" + "---|" * len(CLASSES) + "\n")
    for k, v in e3["prefix_cov"].items():
        md.append(f"| {k} | " + " | ".join(f"{100*v.get(c, 0):.0f}" for c in CLASSES) + " |\n")
    md.append("\nPaired tests vs query-only:\n\n")
    md.append(mcnemar_lines(e3["rows"], "query-only top-10", e3["order"], tasks_by_id, ("ALL", "current_state", "decision_support", "goal_tracking")))

    # ---------------- E4
    e4 = step("E4", X.e4_bm25_side_channel, w)
    md.append(f"\n## E4 — BM25 statistics side channel (attacker identity: {e4['attacker']})\n")
    md.append("\nAttacker plants a one-word note in its own partition, queries the word, and inverts BM25 to estimate document frequency.\n\n")
    md.append("| term | true df (all) | true df (hidden from attacker) | estimated df — global stats | — visible-set stats | — per-partition stats |\n|---|---|---|---|---|---|\n")
    for c in e4["candidates"]:
        md.append(f"| {c['term']} | {c['true_df_all']} | {c['true_df_hidden']} | {c['est_df_global']} | {c['est_df_visible']} | {c['est_df_partition']} |\n")
    md.append("\nControlled insertion of M hidden documents (owner partition) containing a rare term; BM25 score of the attacker's visible document:\n\n")
    md.append("| hidden docs M | global | Δ global | visible-set | Δ visible | per-partition | Δ per-partition |\n|---|---|---|---|---|---|---|\n")
    for r in e4["insertion"]:
        md.append(f"| {r['hidden_docs']} | {r['global']:.3f} | {r['delta_global']:+.3f} | {r['visible']:.3f} | {r['delta_visible']:+.3f} | {r['partition']:.3f} | {r['delta_partition']:+.3f} |\n")
    md.append("\nRank flip between two visible docs as hidden docs are added:\n\n| hidden docs | global | visible-set | per-partition |\n|---|---|---|---|\n")
    for r in e4["rank_flip"]:
        md.append(f"| {r['hidden_docs']} | {r['global']} | {r['visible']} | {r['partition']} |\n")

    md.append(f"\nCorpus-fitted vector models leak too: adding 10 hidden docs changes a visible doc's TF-IDF cosine by {vl['tfidf_score_delta']:+.4f} and its LSA cosine by {vl['lsa_score_delta']:+.4f}.\n")

    # ---------------- E5
    e5 = step("E5", X.e5_graph, w, b, s)
    md.append("\n## E5 — entity-graph expansion, CR@10 % [Wilson 95%]\n")
    md.append(table(e5["arms"]))
    md.append("\nPaired tests vs no graph:\n\n")
    md.append(mcnemar_lines(e5["rows"], "no graph", e5["order"], tasks_by_id, ("ALL", "option_analysis", "cross_domain")))
    md.append("\nLeakage (any returned item outside requester's access) and canary monitor:\n\n")
    md.append("| arm | tasks with leak | leaked items | tasks leaking a canary | leaking tiers | canary monitor alarms / probes |\n|---|---|---|---|---|---|\n")
    for k, v in e5["leak"].items():
        mon = e5["canary_monitor"][k]
        md.append(f"| {k} | {fmt_wilson(v['tasks_with_leak'], v['tasks'])} | {v['leaked_items']} | {v['canary_tasks']} | {v['by_requester_tier']} | {mon['alarms']}/{mon['probes']} |\n")

    # ---------------- E7
    e7 = step("E7", X.e7_packing, w, b, s)
    md.append("\n## E7 — packing at equal k=10, CR@10 % [Wilson 95%]\n")
    md.append(table(e7["arms"]))
    md.append("\nPaired tests vs top-k:\n\n")
    md.append(mcnemar_lines(e7["rows"], "top-k", e7["order"], tasks_by_id, ("ALL",)))
    md.append("\nCR@k by required-set size (default hybrid, query-only):\n\n| arm | " + " | ".join(f"size {s_}" for s_ in ["1", "2", "3", "4", "5", "6", "7", "8"]) + " |\n|---|" + "---|" * 8 + "\n")
    for k, v in e7["by_size"].items():
        md.append(f"| {k} | " + " | ".join(f"{100*v[s_][0]/v[s_][1]:.0f} ({v[s_][1]})" if s_ in v else "–" for s_ in ["1", "2", "3", "4", "5", "6", "7", "8"]) + " |\n")
    e7b = step("E7-best", X.e7_by_size_best, w, b, s)
    md.append("\nCR@k by required-set size, best E3 pipeline (cards + static slots + query); size 8 = 9–10:\n\n| k | " + " | ".join(f"size {s_}" for s_ in ["1", "2", "3", "4", "5", "6", "7", "8"]) + " |\n|---|" + "---|" * 8 + "\n")
    for k, v in e7b.items():
        bs = v["by_size"]
        md.append(f"| {k} | " + " | ".join(f"{fmt_wilson(bs[s_][0], bs[s_][1])} (n={bs[s_][1]})" if s_ in bs else "–" for s_ in ["1", "2", "3", "4", "5", "6", "7", "8"]) + " |\n")
    md.append("\nSame pipeline, CR@k by class:\n\n| k | " + " | ".join(SHORT[c] for c in CLASSES) + " |\n|---|" + "---|" * len(CLASSES) + "\n")
    for k, v in e7b.items():
        bc = v["by_class"]
        md.append(f"| {k} | " + " | ".join(fmt_wilson(*bc[c]) for c in CLASSES) + " |\n")

    # ---------------- I8
    i8 = step("I8", X.i8_origin, w, b, s)
    md.append("\n## I8 — origin-context enrichment, multimodal CR@10 % [Wilson 95%]\n\n| index | retriever | all multimodal | caption sufficient | needs origin-only item |\n|---|---|---|---|---|\n")
    for k, v in i8.items():
        name, meth = k.rsplit(" [", 1)
        f = lambda x: f"{fmt_wilson(x['k'], x['n'])} (n={x['n']})"
        md.append(f"| {name} | {meth[:-1]} | {f(v['all'])} | {f(v['caption sufficient'])} | {f(v['needs origin-only item'])} |\n")
    for meth in ("rrf", "bm25"):
        a = i8[f"without origin context [{meth}]"]["rows"]; bb_ = i8[f"with origin context (I8) [{meth}]"]["rows"]
        n01, n10, p = mcnemar_exact(a, bb_)
        md.append(f"\nPaired ({meth}): with-origin wins {n01}, loses {n10}, exact McNemar p={p:.2g}.\n")

    rb = step("Robustness-BM25", X.robustness_bm25, w, b)
    md.append("\n## Robustness — headline arms re-run with BM25-only first stage (CR@10 % [Wilson 95%])\n")
    for k in ("E2", "E3", "E5", "E7"):
        md.append(f"\n**{k}**\n\n" + table(rb[k]))
    md.append("\nE5 leakage with BM25 base: " + "; ".join(f"{k}: {v['tasks_with_leak']} tasks / canary monitor n/a" for k, v in rb["E5_leak"].items()) + "\n")

    with open(os.path.join(RESULTS_DIR, "tables.md"), "w") as f:
        f.write("".join(md))

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in ("rows", "order")}
        return o
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump(strip(R), f, indent=1, default=float)
    print(f"done in {time.time()-t_all:.1f}s -> results/tables.md, results/results.json")


if __name__ == "__main__":
    main()
