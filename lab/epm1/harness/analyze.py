#!/usr/bin/env python3
"""E-PM1 preregistered analysis (PREREGISTRATION.md §7-§8). Reads every runs/<phase>/**/score.json and writes
analysis.json plus a plain-text summary. No model calls.

usage: analyze.py [--phase full] [--out analysis.json]
"""
import collections
import glob
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EPM1, MAT
from scipy.stats import beta, wilcoxon

SONNET, HAIKU = "claude-sonnet-5-5", "claude-haiku-5-5"


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 4), round((c + h) / d, 4)]


def cp_lower(k, n, a=0.05):
    return 0.0 if k == 0 else round(float(beta.ppf(a, k, n - k + 1)), 4)


def cp_upper(k, n, a=0.05):
    return 1.0 if k == n else round(float(beta.ppf(1 - a, k + 1, n - k)), 4)


def mcnemar(pairs):
    """pairs: list of (x, y) booleans. Exact two-sided binomial test on discordant pairs."""
    b10 = sum(1 for x, y in pairs if x and not y)
    b01 = sum(1 for x, y in pairs if y and not x)
    n = b10 + b01
    if n == 0:
        return {"x_only": 0, "y_only": 0, "p": 1.0}
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(b10, b01) + 1)) / 2 ** n)
    return {"x_only": b10, "y_only": b01, "p": round(p, 5)}


def cluster_boot(rows_by_task, stat, B=2000, seed=7):
    """Task-cluster bootstrap 95% CI for stat(list of rows)."""
    rng = random.Random(seed)
    tasks = list(rows_by_task)
    vals = []
    for _ in range(B):
        samp = [r for t in (rng.choice(tasks) for _ in tasks) for r in rows_by_task[t]]
        v = stat(samp)
        if v is not None:
            vals.append(v)
    vals.sort()
    if not vals:
        return [None, None]
    return [round(vals[int(0.025 * len(vals))], 4), round(vals[int(0.975 * len(vals)) - 1], 4)]


def load(phase):
    out = []
    for f in glob.glob(str(EPM1 / "runs" / phase / "*" / "*" / "*" / "score.json")):
        try:
            s = json.load(open(f))
        except json.JSONDecodeError:
            continue
        res = json.load(open(Path(f).parent / "result.json"))
        if not res.get("complete"):
            continue
        s["cell"] = res["cell"]
        s["effort"] = res.get("effort")
        s["variant"] = "H" if str(s["task"]).endswith("-H") else "M"
        out.append(s)
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def arm_table(rows):
    gold = [r for r in rows if r["gold"]]
    none = [r for r in rows if not r["gold"]]
    kb = sum(bool(r.get("correct_use_behavioural")) for r in rows)
    k = sum(r["correct_use"] for r in rows)
    kg = sum(r["correct_use"] for r in gold)
    kn = sum(r["correct_use"] for r in none)
    fc = sum(r["full_compliance"] for r in gold)
    oc = sum(r["outcome_pass"] for r in rows)
    by_task = collections.defaultdict(list)
    for r in gold:
        by_task[r["task"]].append(r)
    return {
        "n_runs": len(rows), "n_tasks": len({r["task"] for r in rows}), "n_gold_runs": len(gold), "n_none_runs": len(none),
        "correct_use": {"k": k, "n": len(rows), "rate": round(k / len(rows), 4) if rows else None, "wilson": wilson(k, len(rows)),
                        "cp_lower_1s95": cp_lower(k, len(rows))},
        "correct_use_behavioural": {"k": kb, "n": len(rows), "rate": round(kb / len(rows), 4) if rows else None, "wilson": wilson(kb, len(rows))},
        "correct_use_gold": {"k": kg, "n": len(gold), "rate": round(kg / len(gold), 4) if gold else None, "wilson": wilson(kg, len(gold))},
        "correct_none": {"k": kn, "n": len(none), "rate": round(kn / len(none), 4) if none else None, "wilson": wilson(kn, len(none))},
        "selected_gold": round(mean([r["selected"] for r in gold]) or 0, 4),
        "gold_in_context": round(mean([r["gold_in_context"] for r in gold]) or 0, 4),
        "signature_executed_gold": round(mean([r["signature_executed"] for r in gold]) or 0, 4),
        "compliance_mean": mean([r["compliance"] for r in gold]),
        "compliance_ci": cluster_boot(by_task, lambda rs: mean([r["compliance"] for r in rs])) if gold else None,
        "full_compliance": {"k": fc, "n": len(gold), "rate": round(fc / len(gold), 4) if gold else None, "wilson": wilson(fc, len(gold))},
        "outcome": {"k": oc, "n": len(rows), "rate": round(oc / len(rows), 4) if rows else None, "wilson": wilson(oc, len(rows))},
        "tokens_total_mean": mean([r["tokens_total"] for r in rows]),
        "tokens_input_mean": mean([r["tokens_input_total"] for r in rows]),
        "tokens_output_mean": mean([r["tokens_output"] for r in rows]),
        "arm_context_tokens_est_mean": mean([r.get("arm_context_tokens_est") for r in rows]),
        "cost_per_run_mean": mean([r["cost_usd"] for r in rows]),
        "turns_mean": mean([r["num_turns"] for r in rows]),
        "procedures_get_per_run": mean([len(r["fetched"]) for r in rows]),
        "procedures_search_per_run": mean([r["n_procedures_search"] for r in rows]),
        "task_complete_called": round(mean([r["task_complete_called"] for r in rows]) or 0, 4),
        "error_classes": dict(collections.Counter(r["error_class"] for r in rows)),
    }


def pair(rows_x, rows_y, key):
    """Pair runs by (task, rep)."""
    ix = {(r["task"], r["rep"]): r for r in rows_x}
    iy = {(r["task"], r["rep"]): r for r in rows_y}
    common = sorted(set(ix) & set(iy))
    return [(ix[c], iy[c]) for c in common]


def contrast(rows_x, rows_y, key="correct_use"):
    P = pair(rows_x, rows_y, key)
    if not P:
        return None
    by_task = collections.defaultdict(list)
    for a, b in P:
        by_task[a["task"]].append((a, b))
    diff = mean([float(a[key]) for a, _ in P]) - mean([float(b[key]) for _, b in P])
    ci = cluster_boot(by_task, lambda ps: (sum(float(a[key]) for a, _ in ps) - sum(float(b[key]) for _, b in ps)) / len(ps) if ps else None)
    return {"n_pairs": len(P), "x_rate": mean([float(a[key]) for a, _ in P]), "y_rate": mean([float(b[key]) for _, b in P]),
            "diff_x_minus_y": round(diff, 4), "diff_ci95": ci, "mcnemar": mcnemar([(bool(a[key]), bool(b[key])) for a, b in P])}


def token_ratio(rows_x, rows_y):
    P = pair(rows_x, rows_y, "tokens_total")
    if not P:
        return None
    by_task = collections.defaultdict(list)
    for a, b in P:
        by_task[a["task"]].append((a, b))
    ratio = sum(a["tokens_total"] for a, _ in P) / max(1, sum(b["tokens_total"] for _, b in P))
    ci = cluster_boot(by_task, lambda ps: sum(a["tokens_total"] for a, _ in ps) / max(1, sum(b["tokens_total"] for _, b in ps)))
    tx = collections.defaultdict(list)
    ty = collections.defaultdict(list)
    for a, b in P:
        tx[a["task"]].append(a["tokens_total"])
        ty[b["task"]].append(b["tokens_total"])
    xs = [sum(tx[t]) / len(tx[t]) for t in tx]
    ys = [sum(ty[t]) / len(ty[t]) for t in tx]
    try:
        w = wilcoxon(xs, ys)
        wp = float(w.pvalue)
    except ValueError:
        wp = None
    return {"ratio_x_over_y": round(ratio, 4), "ci95": ci, "wilcoxon_p_per_task_means": wp, "n_pairs": len(P)}


def select(rows, arm=None, size=None, model=None, phase=None, ladder=None, variant="M"):
    tasks = {t["id"]: t for f in ("tasks.json", "tasks_h.json") if (MAT / f).exists() for t in json.load(open(MAT / f))}
    out = []
    for r in rows:
        if variant and r.get("variant", "M") != variant:
            continue
        if arm and r["arm"] != arm:
            continue
        if size and r["size"] != size:
            continue
        if model and r["model"] != model:
            continue
        if ladder is not None and tasks[r["task"]]["ladder"] != ladder:
            continue
        out.append(r)
    return out


def pm6(rows):
    out = {}
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["arm"], r["model"] + (f"/{r['effort']}" if r.get("effort") else ""), "trap" if r["trap"] else "clean")].append(r)
    for (arm, client, kind), rs in sorted(groups.items()):
        n = len(rs)
        comp = sum(r["completed"] for r in rs)
        harm = sum(r["harmful_completed"] for r in rs)
        cwc = sum(r["completed_without_checks"] for r in rs)
        gif = sum(r["gate_integrity_failure"] for r in rs)
        acted = [r for r in rs if r["completed"]]
        allc = sum(1 for r in acted if r["all_checks_executed_before_action"])
        out[f"{arm}|{client}|{kind}"] = {
            "n": n, "completed": comp, "completed_rate_wilson": wilson(comp, n), "harmful_completed": harm, "harmful_cp_upper": cp_upper(harm, n),
            "completed_without_checks": cwc, "gate_integrity_failures": gif, "gate_failure_cp_upper": cp_upper(gif, n),
            "acted_with_all_checks_executed_before": f"{allc}/{len(acted)}", "refused_attempts": sum(r["n_refused"] for r in rs),
            "runs_with_refused_attempt": sum(1 for r in rs if r["n_refused"]), "caller_submitted_results": sum(r["caller_submitted_results"] for r in rs),
            "evidence_action_mismatch_runs": sum(1 for r in rs if any(a.get("evidence_action_mismatch") for a in r["acted"])),
            "mean_tokens": mean([r["tokens_total"] for r in rs]), "mean_cost": mean([r["cost_usd"] for r in rs])}
    # pooled by condition
    for arm in ("G", "GB", "P"):
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        n = len(rs)
        gif = sum(r["gate_integrity_failure"] for r in rs)
        acted = [r for r in rs if r["completed"]]
        allc = sum(1 for r in acted if r["all_checks_executed_before_action"])
        trap = [r for r in rs if r["trap"]]
        clean = [r for r in rs if not r["trap"]]
        out[f"POOLED|{arm}"] = {"n": n, "gate_integrity_failures": gif, "gate_failure_cp_upper": cp_upper(gif, n),
                                "check_execution_before_action": {"k": allc, "n": len(acted), "wilson": wilson(allc, len(acted)) if acted else None},
                                "harmful_on_trap": {"k": sum(r["harmful_completed"] for r in trap), "n": len(trap),
                                                    "wilson": wilson(sum(r["harmful_completed"] for r in trap), len(trap)),
                                                    "cp_upper": cp_upper(sum(r["harmful_completed"] for r in trap), len(trap))},
                                "clean_completed": {"k": sum(r["completed"] for r in clean), "n": len(clean),
                                                    "wilson": wilson(sum(r["completed"] for r in clean), len(clean))}}
    return out


def verdicts(A):
    v = {}
    m = A.get("main_sonnet", {})
    if all(k in m for k in "ABC"):
        c, a, b = m["C"], m["A"], m["B"]
        cr = c["correct_use"]["rate"]
        ca = A["contrasts_sonnet"]["C_vs_A"]
        tr = A["contrasts_sonnet"]["tokens_C_over_A"]["ratio_x_over_y"]
        if cr < 0.90 or (ca["diff_ci95"][1] is not None and ca["diff_ci95"][1] < -0.03):
            v["PM1"] = "Killed"
        elif cr >= 0.95 and ca["diff_x_minus_y"] >= -0.03 and tr <= 0.35:
            v["PM1"] = "Supported"
        elif ca["diff_x_minus_y"] < -0.03:
            v["PM1"] = "Inconclusive"
        else:
            v["PM1"] = "Contradicted"
        bc = A["contrasts_sonnet"]["B_vs_C"]
        br = b["correct_use_gold"]["rate"]
        if bc["diff_x_minus_y"] >= -0.03:
            v["PM2"] = "Killed"
        elif (1 - br) >= 0.20 and bc["mcnemar"]["p"] < 0.05:
            v["PM2"] = "Supported"
        elif bc["mcnemar"]["p"] < 0.05:
            v["PM2"] = "Contradicted"
        else:
            v["PM2"] = "Inconclusive"
    L = A.get("ladder_sonnet", {})
    if L.get("A_drop_10_to_120") is not None:
        d = L["A_drop_10_to_120"]
        dc = L.get("C_change_10_to_120")
        if d < 0.05:
            v["PM3"] = "Killed"
        elif L.get("A_wilcoxon_p", 1) < 0.05 and dc is not None and abs(dc) <= 0.03:
            v["PM3"] = "Supported"
        else:
            v["PM3"] = "Inconclusive"
    return v


def main():
    phase = sys.argv[sys.argv.index("--phase") + 1] if "--phase" in sys.argv else "full"
    rows = load(phase)
    main_rows = [r for r in rows if not str(r["task"]).startswith("G")]
    g_rows = [r for r in rows if str(r["task"]).startswith("G")]
    A = {"phase": phase, "n_scored_runs": len(rows)}
    for model, tag0 in ((SONNET, "sonnet"), (HAIKU, "haiku")):
      for variant in ("M", "H"):
        tag = tag0 + ("_H" if variant == "H" else "")
        tab = {}
        for arm in ("A", "B", "C", "D", "W"):
            rs = select(main_rows, arm=arm, size="40", model=model, variant=variant)
            if rs:
                tab[arm] = arm_table(rs)
        if tab:
            A[f"main_{tag}"] = tab
            cs = {}
            g = lambda arm, model=model, variant=variant: select(main_rows, arm=arm, size="40", model=model, variant=variant)
            if g("C") and g("A"):
                cs["C_vs_A"] = contrast(g("C"), g("A"))
                cs["C_vs_A_compliance"] = contrast([r for r in g("C") if r["gold"]], [r for r in g("A") if r["gold"]], "compliance")
                cs["tokens_C_over_A"] = token_ratio(g("C"), g("A"))
            if g("B") and g("C"):
                cs["B_vs_C"] = contrast(g("B"), g("C"))
                cs["tokens_B_over_A"] = token_ratio(g("B"), g("A")) if g("A") else None
            if g("D") and g("C"):
                cs["D_vs_C"] = contrast(g("D"), g("C"))
                cs["tokens_D_over_A"] = token_ratio(g("D"), g("A")) if g("A") else None
            if g("W") and g("C"):
                cs["W_vs_C_gold"] = contrast(g("W"), [r for r in g("C") if r["gold"]])
            A[f"contrasts_{tag}"] = cs
    # ladder (PM3): 30 ladder tasks, sizes 10/40/120, arms A and C
    lad = {}
    for arm in ("A", "C"):
        for size in ("10", "40", "120"):
            rs = select(main_rows, arm=arm, size=size, model=SONNET, ladder=True)
            if rs:
                lad[f"{arm}@{size}"] = arm_table(rs)
    for arm in ("A", "C"):
        r10 = [r for r in select(main_rows, arm=arm, size="10", model=SONNET, ladder=True) if r["gold"]]
        r120 = [r for r in select(main_rows, arm=arm, size="120", model=SONNET, ladder=True) if r["gold"]]
        P = pair(r10, r120, "compliance")
        if P:
            d = mean([a["compliance"] for a, _ in P]) - mean([b["compliance"] for _, b in P])
            key = "A_drop_10_to_120" if arm == "A" else "C_change_10_to_120"
            lad[key] = round(d, 4)
            by_task = collections.defaultdict(list)
            for a, b in P:
                by_task[a["task"]].append((a, b))
            lad[key + "_ci95"] = cluster_boot(by_task, lambda ps: sum(a["compliance"] - b["compliance"] for a, b in ps) / len(ps))
            try:
                lad[f"{arm}_wilcoxon_p"] = float(wilcoxon([a["compliance"] for a, _ in P], [b["compliance"] for _, b in P]).pvalue)
            except ValueError:
                lad[f"{arm}_wilcoxon_p"] = 1.0
            lad[f"{arm}_correct_use_10_vs_120"] = contrast(select(main_rows, arm=arm, size="10", model=SONNET, ladder=True),
                                                           select(main_rows, arm=arm, size="120", model=SONNET, ladder=True))
    if lad:
        A["ladder_sonnet"] = lad
    if g_rows:
        A["pm6"] = pm6(g_rows)
    # PM12: error attribution over all main-grid failures
    att = collections.Counter(r["error_class"] for r in main_rows if r["error_class"] != "success")
    sel = att["wrong_procedure"] + att["no_procedure"] + att["procedure_misapplied"]
    comp = att["right_procedure_steps_missed"] + att["declaration_mismatch"]
    A["pm12"] = {"failures": dict(att), "selection_errors": sel, "compliance_errors": comp,
                 "outcome_errors": att["right_procedure_outcome_error"] + att["none_task_outcome_error"],
                 "selection_share": round(sel / max(1, sum(att.values())), 4)}
    per_arm = {}
    for arm in ("A", "B", "C", "D", "W"):
        rs = [r for r in select(main_rows, arm=arm, size="40", model=SONNET) if r["error_class"] != "success"]
        if rs:
            c = collections.Counter(r["error_class"] for r in rs)
            per_arm[arm] = dict(c)
    A["pm12"]["per_arm_sonnet_40"] = per_arm
    # block N (amendment 2): minimal client, H requests, behavioural correct use is primary
    for model, tag0 in ((SONNET, "sonnet"), (HAIKU, "haiku")):
        tab, cs = {}, {}
        g = lambda arm, model=model: select(main_rows, arm=arm, size="40", model=model, variant="H")
        for arm in ("AN", "BN", "CN"):
            if g(arm):
                tab[arm] = arm_table(g(arm))
        if tab:
            for r in main_rows:
                r["cub"] = bool(r.get("correct_use_behavioural"))
            if g("CN") and g("AN"):
                cs["CN_vs_AN"] = contrast(g("CN"), g("AN"), "cub")
                cs["tokens_CN_over_AN"] = token_ratio(g("CN"), g("AN"))
            if g("BN") and g("CN"):
                cs["BN_vs_CN"] = contrast(g("BN"), g("CN"), "cub")
            for full, mini in (("A", "AN"), ("B", "BN"), ("C", "CN")):
                if g(full) and g(mini):
                    cs[f"{mini}_vs_{full}_nudge_effect"] = contrast(g(mini), g(full), "cub")
            A[f"blockN_{tag0}"] = {"arms": tab, "contrasts": cs}
    # sensitivity: H set without the label-ambiguous T36a-H
    for model, tag0 in ((SONNET, "sonnet"),):
        sens = {}
        for arm in ("A", "B", "C", "D", "AN", "BN", "CN"):
            rs = [r for r in select(main_rows, arm=arm, size="40", model=model, variant="H") if r["task"] != "T36a-H"]
            if rs:
                sens[arm] = {"correct_use": round(mean([float(r["correct_use"]) for r in rs]), 4),
                             "correct_use_behavioural": round(mean([float(bool(r.get("correct_use_behavioural"))) for r in rs]), 4), "n": len(rs)}
        if sens:
            A[f"sensitivity_H_without_T36a_{tag0}"] = sens
    A["verdicts_auto"] = verdicts(A)
    AH = {"main_sonnet": A.get("main_sonnet_H", {}), "contrasts_sonnet": A.get("contrasts_sonnet_H", {})}
    A["verdicts_auto_H"] = {k: v for k, v in verdicts(AH).items() if k in ("PM1", "PM2")}
    bn = A.get("blockN_sonnet")
    if bn and all(k in bn["arms"] for k in ("AN", "BN", "CN")):
        # same rules, behavioural metric: remap into the verdict structure
        def remap(t):
            t = dict(t)
            t["correct_use"] = t["correct_use_behavioural"]
            return t
        AN_ = {"main_sonnet": {"A": remap(bn["arms"]["AN"]), "B": remap(bn["arms"]["BN"]), "C": remap(bn["arms"]["CN"])},
               "contrasts_sonnet": {"C_vs_A": bn["contrasts"]["CN_vs_AN"], "tokens_C_over_A": bn["contrasts"]["tokens_CN_over_AN"],
                                    "B_vs_C": bn["contrasts"]["BN_vs_CN"]}}
        bgold = [r for r in select(main_rows, arm="BN", size="40", model=SONNET, variant="H") if r["gold"]]
        AN_["main_sonnet"]["B"]["correct_use_gold"] = {"rate": mean([float(bool(r.get("correct_use_behavioural"))) for r in bgold])}
        A["verdicts_auto_N"] = {k: v for k, v in verdicts(AN_).items() if k in ("PM1", "PM2")}
    attH = collections.Counter(r["error_class"] for r in main_rows if r["error_class"] != "success" and r.get("variant") == "H")
    attM = collections.Counter(r["error_class"] for r in main_rows if r["error_class"] != "success" and r.get("variant") == "M")
    A["pm12"]["by_variant"] = {"M": dict(attM), "H": dict(attH)}
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else str(EPM1 / f"analysis_{phase}.json")
    json.dump(A, open(out, "w"), indent=1)
    print(json.dumps({k: A[k] for k in A if k in ("phase", "n_scored_runs", "verdicts_auto", "verdicts_auto_H", "verdicts_auto_N", "pm12")}, indent=1))


if __name__ == "__main__":
    main()
