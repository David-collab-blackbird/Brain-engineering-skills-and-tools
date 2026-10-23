#!/usr/bin/env python3
"""Readable trace of one run for the engineer hand-check: task request, gold procedure and its checklist text
(descriptions only), every server-side tool call with arguments, and the final summary. Deliberately does NOT
print the scorer's verdicts. usage: trace.py RUN_DIR [--maxarg 400]"""
import gzip
import json
import sys
from pathlib import Path

MAT = Path("/home/claude/epm1/materials")
run = Path(sys.argv[1])
mx = int(sys.argv[sys.argv.index("--maxarg") + 1]) if "--maxarg" in sys.argv else 400
res = json.load(open(run / "result.json"))
tasks = {t["id"]: t for f in ("tasks.json", "tasks_h.json") for t in json.load(open(MAT / f))}
t = tasks.get(res["task"])
print(f"RUN {run} arm={res['arm']} size={res['size']} model={res['model']} scope_declared={res['scope_declared']} routed={res.get('routed')}")
if t:
    print(f"REQUEST: {t['masked']}")
    print(f"GOLD: {t['gold']}")
    for s in t["steps"]:
        print(f"  checklist {s['id']}: {s['desc']}{' [distinctive]' if s['distinctive'] else ''}")
    for o in t["outcomes"]:
        print(f"  outcome: {o['desc']}")
for line in gzip.open(run / "brain.jsonl.gz", "rt"):
    d = json.loads(line)
    if "tool" in d:
        a = json.dumps(d["args"], ensure_ascii=False)
        print(f"{d['seq']:3d} {d['tool']}{' [ERROR]' if d['error'] else ''} {a[:mx]}")
print("FINAL TEXT:", (res.get("final_text") or "")[:800])
