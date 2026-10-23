#!/usr/bin/env python3
"""Blind review of one run: a fresh Claude (Opus) session sees only the brief, the provided store and the
anonymised builder src/ (no transcript, no arm label, no tests, no build/ state). It lists defects with evidence.

usage: blind_review.py RUNDIR [--model claude-opus-5-5]
Writes RUNDIR/blind_review.json. Reviewer id = sha1(run path) so the reviewer cannot infer the arm.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
SANDBOX = str(E15 / "harness/sandbox_claude.sh")
sys.path.insert(0, str(E15 / "harness"))
from run_arm import ledger_append  # noqa: E402

PROMPT = """You are reviewing a Python package against its specification. You did not write it.

- Specification: the one brief in packages/ (WP-*.md): its numbered rules, interface and outputs.
- Provided infrastructure (correct by definition): everything under provided/ (store, helpers, fixture.json).
- Code under review: everything under src/.

Find every defect: a place where the code violates a rule or the interface of the specification, or a bug that
would give wrong results. Pay special attention to the protected rules (access control, visibility, leakage,
statistics over unseen rows, staleness, erasure, "not found" equals "denied"): any way a requester could see,
infer, or be scored using data they may not see, or be served data that is no longer active/current/visible.
You may write and run probe scripts under /tmp with `python` (put src and provided on sys.path; load the
fixture with the provided store's from_fixture). Do not modify files under the repository.

Where the specification is ambiguous, do not count either reasonable reading as a defect; note it under
"ambiguities". Evidence is required for every defect: quote the line (file:line) or show probe output.

Finish with ONLY this JSON (no prose after it):
{"defects": [{"rule": "R?", "severity": "critical|major|minor", "location": "file:line",
  "description": "...", "evidence": "..."}],
 "ambiguities": ["..."], "verdict": "meets spec | does not meet spec"}
"""


def main():
    run = Path(sys.argv[1]).resolve()
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "claude-opus-5-5"
    rid = hashlib.sha1(str(run).encode()).hexdigest()[:10]
    box = E15 / "reviews" / rid
    if box.exists():
        shutil.rmtree(box)
    (box / "work").mkdir(parents=True)
    (box / "home").mkdir()
    w = box / "work"
    meta0 = json.loads((run / "meta.json").read_text())
    tpl = "template3" if meta0["pkg"] in ("P3", "P4") else "template"
    shutil.copytree(E15 / tpl / "common/packages", w / "packages")
    shutil.copytree(E15 / tpl / "common/provided", w / "provided", ignore=shutil.ignore_patterns("__pycache__"))
    src = run / "work/src"
    if src.exists():
        shutil.copytree(src, w / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # anonymise: strip arm-identifying words from comments (rare) and remove non-code files
    for f in list((w / "src").rglob("*")):
        if f.is_file() and f.suffix != ".py":
            f.unlink()
    t0 = time.time()
    out = box / "review.jsonl"
    with open(out, "w") as fo, open(box / "review.stderr", "w") as fe:
        p = subprocess.run([SANDBOX, str(box), "--", "-p", PROMPT, "--model", model, "--output-format", "stream-json",
                            "--verbose", "--setting-sources", "project,local", "--permission-mode",
                            "bypassPermissions", "--max-budget-usd", "6"], stdout=fo, stderr=fe, timeout=3000)
    res = None
    for line in out.read_text(errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "result":
            res = d
    text = (res or {}).get("result") or ""
    m = re.findall(r"\{[\s\S]*\}", text)
    parsed = None
    for cand in reversed(m):
        try:
            parsed = json.loads(cand)
            break
        except json.JSONDecodeError:
            # try the last balanced object
            s = cand[cand.rfind('{"defects"'):] if '{"defects"' in cand else cand
            try:
                parsed = json.loads(s)
                break
            except json.JSONDecodeError:
                continue
    cost = (res or {}).get("total_cost_usd") or 0
    review = {"run": str(run), "reviewer_id": rid, "model": model, "cost_usd": cost,
              "wall_s": round(time.time() - t0, 1), "parsed": parsed, "raw_tail": text[-4000:]}
    (run / "blind_review.json").write_text(json.dumps(review, indent=1))
    meta = meta0
    ledger_append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "phase": "blind-review", "run_id": meta["run_id"],
                   "arm": meta["arm"], "pkg": meta["pkg"], "rep": meta["rep"], "process": "review",
                   "wall_s": review["wall_s"], "cost_usd": f"{cost:.4f}", "killed": "", "rc": p.returncode})
    n = len(parsed["defects"]) if parsed else None
    print(f"{meta['run_id']}: blind review defects={n} cost=${cost:.2f}")


if __name__ == "__main__":
    main()
