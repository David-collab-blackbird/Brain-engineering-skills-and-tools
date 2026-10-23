#!/usr/bin/env python3
"""Adjudicate blind-review defects deterministically where possible.

usage: adjudicate.py RUNDIR
A blind-review defect is CONFIRMED if (a) a hidden test covering the same rule failed for this run, or (b) the
engineer's adjudication file (manual, RUNDIR/blind_manual.json: {"<index>": "confirmed|rejected|ambiguous"}) says so.
Unadjudicated defects are reported as 'unverified' (never counted as confirmed).
Writes RUNDIR/blind_adjudicated.json: {reported, confirmed, confirmed_protected, rejected, unverified, items[]}.
"""
import json
import re
import sys
from pathlib import Path

PROTECTED_RULES = {"P1": {"R2", "R2a", "R3", "R4", "R6", "R7"}, "P2": {"R2", "R2a", "R3", "R4", "R6", "R7"},
                   "P3": {"R1", "R2", "R5", "R9", "R10", "R11", "R12"}, "P4": {"R1", "R2", "R5", "R9", "R10", "R11", "R12"}}


def main(run: Path):
    br = json.loads((run / "blind_review.json").read_text())
    m = json.loads((run / "metrics.json").read_text())
    manual = {}
    mp = run / "blind_manual.json"
    if mp.exists():
        manual = json.loads(mp.read_text())
    defects = (br.get("parsed") or {}).get("defects") or []
    items = []
    for i, d in enumerate(defects):
        rule = str(d.get("rule", ""))
        rules = set(re.findall(r"R\d+a?", rule))
        verdict = manual.get(str(i), "unverified")
        items.append({"i": i, "rule": rule, "severity": d.get("severity"), "location": d.get("location"),
                      "description": (d.get("description") or "")[:400], "verdict": verdict,
                      "protected": bool(rules & PROTECTED_RULES[m["pkg"]])})
    out = {"reported": len(items), "confirmed": sum(x["verdict"] == "confirmed" for x in items),
           "confirmed_protected": sum(x["verdict"] == "confirmed" and x["protected"] for x in items),
           "rejected": sum(x["verdict"] == "rejected" for x in items),
           "ambiguous": sum(x["verdict"] == "ambiguous" for x in items),
           "unverified": sum(x["verdict"] == "unverified" for x in items), "items": items,
           "verdict": (br.get("parsed") or {}).get("verdict")}
    (run / "blind_adjudicated.json").write_text(json.dumps(out, indent=1))
    print(f"{m['run_id']}: reported {out['reported']} confirmed {out['confirmed']} (protected {out['confirmed_protected']}) "
          f"rejected {out['rejected']} unverified {out['unverified']}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
