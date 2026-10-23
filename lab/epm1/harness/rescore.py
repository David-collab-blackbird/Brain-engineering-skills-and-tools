#!/usr/bin/env python3
"""Re-run the (deterministic) scorer over every completed run of a phase, so all runs are scored by the same
score.py version. usage: rescore.py PHASE"""
import glob
import json
import subprocess
import sys

phase = sys.argv[1]
n = 0
for res in glob.glob(f"/home/claude/epm1/runs/{phase}/*/*/*/result.json"):
    try:
        if not json.load(open(res)).get("complete"):
            continue
    except json.JSONDecodeError:
        continue
    subprocess.run([sys.executable, "-I", "/home/claude/epm1/harness/score.py", res.rsplit("/", 1)[0]], check=False)
    n += 1
print("rescored", n)
