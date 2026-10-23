#!/usr/bin/env python3
"""Render Markdown tables from analysis.json + per-run metrics for RESULTS.md.

usage: report_tables.py [--phase full] > tables.md
"""
import json
import statistics
import sys
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E15 / "harness"))
from analyze import load, summarize, wilson  # noqa: E402

ARMS = ["A", "B", "C", "D", "AU", "AR"]
NAMES = {"A": "A protocol", "B": "B Superpowers", "C": "C hybrid", "D": "D owner (Ultracode + 58k)",
         "AU": "AU = A + Ultracode", "AR": "AR = A + 58k reading"}


def pct(x):
    return f"{100 * x:.1f}%"


def ci(c):
    return f"[{100 * c[0]:.1f}, {100 * c[1]:.1f}]"


def main():
    phase = sys.argv[sys.argv.index("--phase") + 1] if "--phase" in sys.argv else "full"
    runs = load({phase})
    out = []
    for pkgset, label in ((("P3", "P4"), "P3+P4 (primary: WP-E15C cards)"), (("P1", "P2"), "P1+P2 (secondary: WP-E15 retrieval)")):
        out.append(f"\n#### {label}\n")
        out.append("| Arm | n | Hidden pass (pooled) [95% Wilson] | All-pass runs | Protected-area mistakes (total / runs) | Tamper runs | Special-casing runs | Impossible-test correct pause | Cost median (min–max) | Tokens median | Busy time median | Agents median (max) |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for arm in ARMS:
            rs = [r for r in runs if r["arm"] == arm and r["pkg"] in pkgset and not r.get("drill")]
            if not rs:
                continue
            k = sum(r["hidden_pass"] for r in rs)
            n = sum(r["hidden_total"] for r in rs)
            allp = sum(r["hidden_pass"] == r["hidden_total"] for r in rs)
            pam = [len(r["protected_area_mistakes"]) for r in rs]
            tam = sum(r["tamper"]["test_tampering"] for r in rs)
            spc = sum(r["tamper"]["special_casing"] for r in rs)
            p2 = [r for r in rs if r["pkg"] in ("P2", "P4")]
            cp = sum(1 for r in p2 if r.get("p2", {}).get("correct_pause"))
            cost = [r["cost_usd"] for r in rs]
            toks = [sum(v.get("total_tokens", 0) for v in r["tokens"]["by_kind"].values()) for r in rs]
            wall = [r.get("wall_busy_s") or r["wall_s"] for r in rs]
            ag = [r["tokens"]["agents"]["subagent"] + r["tokens"]["agents"]["workflow"] for r in rs]
            out.append(f"| {NAMES[arm]} | {len(rs)} | {pct(k / n)} {ci(wilson(k, n))} | {allp}/{len(rs)} | {sum(pam)} / {sum(1 for x in pam if x)} | "
                       f"{tam} | {spc} | {cp}/{len(p2)} | ${statistics.median(cost):.2f} ({min(cost):.2f}–{max(cost):.2f}) | "
                       f"{statistics.median(toks) / 1e6:.2f}M | {statistics.median(wall) / 60:.1f} min | {statistics.median(ag):.0f} ({max(ag)}) |")
    # failed hidden tests by arm
    out.append("\n#### Hidden tests failed, by arm (count of runs)\n")
    out.append("| Arm | Failed tests (runs) |")
    out.append("|---|---|")
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm and not r.get("drill")]
        if not rs:
            continue
        c = {}
        for r in rs:
            for t in r["hidden_failed"]:
                c[f"{r['pkg'][:2] if r['pkg'] in ('P1','P2') else 'P3/4'}:{t}"] = c.get(f"{r['pkg'][:2] if r['pkg'] in ('P1','P2') else 'P3/4'}:{t}", 0) + 1
        txt = ", ".join(f"{k} ({v})" for k, v in sorted(c.items(), key=lambda x: -x[1])) or "none"
        out.append(f"| {NAMES[arm]} | {txt} |")
    # owner questions
    out.append("\n#### Protected ambiguity (agent access) and owner turns\n")
    out.append("| Arm | Runs that asked about agent access | Runs that asked about default k | Runs with ≥1 owner turn | Hook denials (total) |")
    out.append("|---|---|---|---|---|")
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm and not r.get("drill")]
        if not rs:
            continue
        a1 = sum(1 for r in rs if any("OA-1" in t["answers"] for t in (r.get("owner_turns") or [])))
        a2 = sum(1 for r in rs if any("OA-2" in t["answers"] for t in (r.get("owner_turns") or [])))
        ot = sum(1 for r in rs if r.get("owner_turns"))
        hd = sum(r.get("hook_denials", 0) for r in rs)
        out.append(f"| {NAMES[arm]} | {a1}/{len(rs)} | {a2}/{len(rs)} | {ot}/{len(rs)} | {hd} |")
    # GS14 mechanism
    out.append("\n#### GS14 mechanism: context of each spawned agent's first request (tokens)\n")
    out.append("| Arm | Runs with agents | Agents (total) | Workflow runs (total) | Median first-request context | Range |")
    out.append("|---|---|---|---|---|---|")
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm and not r.get("drill")]
        vals = [r["tokens"]["agent_first_request_context"] for r in rs if r["tokens"]["agent_first_request_context"]["n"]]
        if not rs:
            continue
        meds = [v["median"] for v in vals]
        lo = min((v["min"] for v in vals), default=None)
        hi = max((v["max"] for v in vals), default=None)
        tot_ag = sum(r["tokens"]["agents"]["subagent"] + r["tokens"]["agents"]["workflow"] for r in rs)
        wfr = sum(r["tokens"]["workflow_runs"] for r in rs)
        out.append(f"| {NAMES[arm]} | {len(vals)}/{len(rs)} | {tot_ag} | {wfr} | {statistics.median(meds) if meds else '–'} | {lo}–{hi} |")
    # blind review
    out.append("\n#### Blind review (fresh Claude Opus 5.5, brief + anonymised src only)\n")
    out.append("| Arm | Reviewed | Defects reported | Confirmed | Confirmed protected | Rejected | Unverified | Verdict 'meets spec' |")
    out.append("|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm and not r.get("drill")]
        adj = [json.loads((E15 / "runs" / r["arm"] / r["pkg"] / str(r["rep"]) / "blind_adjudicated.json").read_text())
               for r in rs if (E15 / "runs" / r["arm"] / r["pkg"] / str(r["rep"]) / "blind_adjudicated.json").exists()]
        if not rs:
            continue
        out.append(f"| {NAMES[arm]} | {len(adj)}/{len(rs)} | {sum(a['reported'] for a in adj)} | {sum(a['confirmed'] for a in adj)} | "
                   f"{sum(a['confirmed_protected'] for a in adj)} | {sum(a['rejected'] for a in adj)} | {sum(a['unverified'] for a in adj)} | "
                   f"{sum(1 for a in adj if str(a.get('verdict','')).startswith('meets'))}/{len(adj)} |")
    print("\n".join(out))


if __name__ == "__main__":
    main()
