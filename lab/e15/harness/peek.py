#!/usr/bin/env python3
"""Print a compact trace of a run's stream-json logs. usage: peek.py RUNDIR [N]"""
import json, sys
from pathlib import Path
run = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
lines = []
for f in sorted((run / "logs").glob("*.jsonl"), key=lambda p: p.stat().st_mtime):
    for l in f.read_text(errors="replace").splitlines():
        try: d = json.loads(l)
        except Exception: continue
        t = d.get("type")
        if t == "assistant":
            for c in d["message"]["content"]:
                if c["type"] == "tool_use":
                    inp = c["input"]; s = inp.get("command") or inp.get("file_path") or inp.get("name") or inp.get("skill") or inp.get("description") or json.dumps(inp)[:100]
                    lines.append(f"{f.stem} TOOL {c['name']}: {str(s)[:150]}")
                elif c["type"] == "text" and c["text"].strip():
                    lines.append(f"{f.stem} TEXT {c['text'][:200]!r}")
        elif t == "result":
            lines.append(f"{f.stem} RESULT cost={d.get('total_cost_usd')} turns={d.get('num_turns')} sub={d.get('subtype')} {str(d.get('result'))[:300]!r}")
        elif t == "system" and d.get("subtype") in ("task_started", "task_notification"):
            lines.append(f"{f.stem} SYS {d.get('subtype')} {str(d.get('description') or d.get('summary'))[:120]} {d.get('status','')}")
print("\n".join(lines[-n:]))
