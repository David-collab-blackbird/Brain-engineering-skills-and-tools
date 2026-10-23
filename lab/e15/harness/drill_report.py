#!/usr/bin/env python3
"""Kill-and-resume drill details per arm: what the fresh session did first, redone work, re-verification.

usage: drill_report.py  -> prints a Markdown table; writes drills.json
"""
import json
import re
import subprocess
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]


def git(work, *a):
    return subprocess.run(["git", "-c", "safe.directory=*", *a], cwd=work, capture_output=True, text=True).stdout


def first_actions(log: Path, n=6):
    acts = []
    for line in log.read_text(errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            for c in d["message"]["content"]:
                if c.get("type") == "tool_use":
                    i = c["input"]
                    acts.append(f"{c['name']}:{str(i.get('command') or i.get('file_path') or i.get('skill') or i.get('name') or '')[:400]}")
        if len(acts) >= n:
            break
    return acts


def main():
    rows = []
    for mf in sorted(E15.glob("runs/*/*/9/metrics.json")):
        m = json.loads(mf.read_text())
        run = mf.parent
        meta = json.loads((run / "meta.json").read_text())
        if not meta.get("drill"):
            continue
        work = run / "work"
        head = meta.get("drill_head_at_kill")
        msgs_before = git(work, "log", "--format=%s", f"{meta['base']}..{head}").splitlines() if head else []
        msgs_after = git(work, "log", "--format=%s", f"{head}..HEAD").splitlines() if head else []
        r0 = run / "logs/r0.jsonl"
        acts = first_actions(r0) if r0.exists() else []
        read_state = any("state.json" in a or "state" in a.lower() for a in acts[:3])
        ran_tests = any(re.search(r"make test|pytest", a) for a in acts)
        p0 = [p for p in meta["processes"] if p["label"] == "p0"][0]
        rest = [p for p in meta["processes"] if p["label"] != "p0"]
        rows.append({"run": m["run_id"], "arm": m["arm"], "killed_at_s": meta.get("drill_killed_at_s"),
                     "commits_before_kill": len(msgs_before), "commits_after": len(msgs_after),
                     "first_actions": acts, "read_state_first": read_state, "reverified_first": ran_tests,
                     "cost_before_kill": p0["cost"], "cost_after": round(sum(p["cost"] for p in rest), 4),
                     "hidden": f"{m['hidden_pass']}/{m['hidden_total']}", "visible": m["visible_pass"],
                     "completed": (m.get("drill") or {}).get("completed"), "msgs_after": msgs_after[:6]})
    (E15 / "drills.json").write_text(json.dumps(rows, indent=1))
    print("| Arm | Killed at | Commits before kill | Commits after resume | Read state first | Re-ran tests first | Cost before / after | Hidden | Completed |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['arm']} | {r['killed_at_s']:.0f} s | {r['commits_before_kill']} | {r['commits_after']} | {r['read_state_first']} | "
              f"{r['reverified_first']} | ${r['cost_before_kill']:.2f} / ${r['cost_after']:.2f} | {r['hidden']} | {r['completed']} |")


if __name__ == "__main__":
    main()
