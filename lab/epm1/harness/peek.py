#!/usr/bin/env python3
"""Print a one-line summary per run of a phase (or a glob). usage: peek.py PHASE [CELL_SUBSTR]"""
import glob
import json
import sys
from pathlib import Path

phase = sys.argv[1]
sub = sys.argv[2] if len(sys.argv) > 2 else ""
keys = ["correct_use", "declared", "compliance", "outcome_pass", "error_class", "tokens_total", "completed", "harmful_completed",
        "gate_integrity_failure", "n_refused", "all_checks_executed_before_action"]
for d in sorted(glob.glob(f"/home/claude/epm1/runs/{phase}/*/*/*")):
    if sub and sub not in d:
        continue
    r = Path(d)
    try:
        res = json.load(open(r / "result.json"))
        sc = json.load(open(r / "score.json"))
    except Exception:
        print(r.relative_to(f"/home/claude/epm1/runs/{phase}"), "not done")
        continue
    print(r.relative_to(f"/home/claude/epm1/runs/{phase}"), f"${res['cost_usd']:.4f} {res['wall_s']}s t{res['num_turns']}",
          {k: sc.get(k) for k in keys if k in sc})
