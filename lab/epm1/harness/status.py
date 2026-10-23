#!/usr/bin/env python3
"""Progress of the full plan: done/total per block, spend, failures so far, isolation failures."""
import json, glob, collections, sys
sys.path.insert(0, "/home/claude/epm1/harness")
from schedule import done
from common import spent
plan = json.load(open("/home/claude/epm1/logs/plan_full.json"))
for b in plan["blocks"]:
    d = sum(done(tuple(r)) for r in b["runs"])
    print(f"{b['name']:18s} {d:4d}/{len(b['runs'])}")
inc = iso = 0
for f in glob.glob("/home/claude/epm1/runs/full/*/*/*/result.json"):
    r = json.load(open(f))
    if not r.get("complete"):
        inc += 1
    if not (r.get("isolation") or {}).get("ok", False):
        iso += 1
print(f"spent ${spent():.2f}; incomplete runs {inc}; isolation failures {iso}")
