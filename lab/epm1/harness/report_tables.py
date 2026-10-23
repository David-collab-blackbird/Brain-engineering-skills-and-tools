#!/usr/bin/env python3
"""Markdown tables for RESULTS.md from analysis_full.json (+ free analyses). usage: report_tables.py > logs/tables.md"""
import json

E = "/home/claude/epm1"
A = json.load(open(f"{E}/analysis_full.json"))


def pct(x):
    return "–" if x is None else f"{100 * x:.1f}"


def ci(w):
    return "–" if not w or w[0] is None else f"[{100 * w[0]:.1f}–{100 * w[1]:.1f}]"


def arm_rows(tab, arms, label=""):
    out = ["| Arm | runs (tasks) | correct use % [Wilson] | behavioural % | gold: correct use | no-gold: correct | step compliance % (mean) [task bootstrap] | full compliance % [Wilson] | outcome % [Wilson] | tokens / task (mean) | arm context tokens (est.) | $ / run |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in arms:
        if a not in tab:
            continue
        t = tab[a]
        out.append(f"| {label}{a} | {t['n_runs']} ({t['n_tasks']}) | {pct(t['correct_use']['rate'])} {ci(t['correct_use']['wilson'])} | "
                   f"{pct(t['correct_use_behavioural']['rate'])} | {t['correct_use_gold']['k']}/{t['correct_use_gold']['n']} | "
                   f"{t['correct_none']['k']}/{t['correct_none']['n']} | {pct(t['compliance_mean'])} {ci(t['compliance_ci'])} | "
                   f"{pct(t['full_compliance']['rate'])} {ci(t['full_compliance']['wilson'])} | {pct(t['outcome']['rate'])} {ci(t['outcome']['wilson'])} | "
                   f"{t['tokens_total_mean']:,.0f} | {t['arm_context_tokens_est_mean']:,.0f} | {t['cost_per_run_mean']:.4f} |")
    return "\n".join(out)


def contrast_rows(cs):
    out = ["| Contrast | paired runs | x % | y % | x − y (pp) [task bootstrap 95%] | McNemar x-only / y-only, p |", "|---|---|---|---|---|---|"]
    for k, c in cs.items():
        if not c or "mcnemar" not in c:
            continue
        out.append(f"| {k} | {c['n_pairs']} | {pct(c['x_rate'])} | {pct(c['y_rate'])} | {100 * c['diff_x_minus_y']:+.1f} "
                   f"[{100 * c['diff_ci95'][0]:+.1f}, {100 * c['diff_ci95'][1]:+.1f}] | {c['mcnemar']['x_only']} / {c['mcnemar']['y_only']}, p={c['mcnemar']['p']} |")
    tok = ["| Token ratio | ratio [task bootstrap 95%] | Wilcoxon p (per-task means) |", "|---|---|---|"]
    for k, c in cs.items():
        if c and "ratio_x_over_y" in c:
            tok.append(f"| {k} | {c['ratio_x_over_y']:.3f} [{c['ci95'][0]:.3f}, {c['ci95'][1]:.3f}] | {c['wilcoxon_p_per_task_means']:.2g} |")
    return "\n".join(out) + "\n\n" + "\n".join(tok)


def errors(tab, arms):
    keys = ["success", "no_procedure", "wrong_procedure", "declaration_mismatch", "right_procedure_steps_missed", "right_procedure_outcome_error",
            "procedure_misapplied", "none_task_outcome_error"]
    out = ["| Arm | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for a in arms:
        if a in tab:
            out.append(f"| {a} | " + " | ".join(str(tab[a]["error_classes"].get(k, 0)) for k in keys) + " |")
    return "\n".join(out)


def main():
    for key, title, arms in (("main_sonnet", "Masked requests, Sonnet 5.5, size 40", "ABCDW"), ("main_sonnet_H", "Hardened requests (H), Sonnet 5.5, size 40", "ABCD"),
                             ("main_haiku", "Masked requests, Haiku 5.5, size 40", "ABCD"), ("main_haiku_H", "Hardened requests (H), Haiku 5.5, size 40", "ABCD")):
        if key in A:
            print(f"\n### {title}\n")
            print(arm_rows(A[key], arms))
            tag = key.replace("main_", "contrasts_")
            if tag in A:
                print()
                print(contrast_rows(A[tag]))
            print()
            print(errors(A[key], arms))
    for tag in ("sonnet", "haiku"):
        b = A.get(f"blockN_{tag}")
        if b:
            print(f"\n### Block N (minimal client), {tag}, H requests\n")
            print(arm_rows(b["arms"], ["AN", "BN", "CN"]))
            print()
            print(contrast_rows(b["contrasts"]))
            print()
            print(errors(b["arms"], ["AN", "BN", "CN"]))
    L = A.get("ladder_sonnet")
    if L:
        print("\n### Ladder (PM3), Sonnet, 30 ladder tasks\n")
        print(arm_rows(L, [k for k in L if "@" in k]))
        for k in ("A_drop_10_to_120", "C_change_10_to_120"):
            if k in L:
                print(f"\n- {k}: {100 * L[k]:+.1f} pp [{100 * L[k + '_ci95'][0]:+.1f}, {100 * L[k + '_ci95'][1]:+.1f}], Wilcoxon p = {L[k[0] + '_wilcoxon_p']:.3g}")
    if "pm6" in A:
        print("\n### PM6\n")
        print("| Condition | client | kind | n | completed | harmful | completed without checks | gate integrity failures (CP upper 95%) | acted with all checks first | refused attempts (runs) | caller 'passed' | evidence≠action |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for k, v in A["pm6"].items():
            if k.startswith("POOLED"):
                continue
            arm, client, kind = k.split("|")
            print(f"| {arm} | {client} | {kind} | {v['n']} | {v['completed']} | {v['harmful_completed']} | {v['completed_without_checks']} | "
                  f"{v['gate_integrity_failures']} ({100 * v['gate_failure_cp_upper']:.1f}%) | {v['acted_with_all_checks_executed_before']} | "
                  f"{v['refused_attempts']} ({v['runs_with_refused_attempt']}) | {v['caller_submitted_results']} | {v['evidence_action_mismatch_runs']} |")
        print()
        for k, v in A["pm6"].items():
            if k.startswith("POOLED"):
                print(f"- {k}: {json.dumps(v)}")
    print("\n### Verdicts (automatic)\n")
    for k in ("verdicts_auto", "verdicts_auto_H", "verdicts_auto_N"):
        print(f"- {k}: {A.get(k)}")
    print("\n### PM12\n")
    print(json.dumps(A["pm12"], indent=1))
    for k in A:
        if k.startswith("sensitivity"):
            print(f"\n### {k}\n{json.dumps(A[k], indent=1)}")


if __name__ == "__main__":
    main()
