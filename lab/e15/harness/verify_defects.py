#!/usr/bin/env python3
"""Verify blind-review defects: a second fresh Claude (Opus) session per run tries to REPRODUCE each claimed
defect with a probe script against the same sandboxed copy, and classifies it. Defaults to "rejected" when it
cannot reproduce. Writes RUNDIR/blind_manual.json (consumed by adjudicate.py) and RUNDIR/blind_verify.json.

usage: verify_defects.py RUNDIR [--model claude-opus-5-5]
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
SANDBOX = str(E15 / "harness/sandbox_claude.sh")
sys.path.insert(0, str(E15 / "harness"))
from run_arm import ledger_append  # noqa: E402

PROMPT = """You are a skeptical verifier. A reviewer claims the code under src/ violates the specification (the
brief in packages/). For EACH numbered claim below, try to REPRODUCE it yourself: read the cited code, and write
and run a minimal probe under /tmp with `python` (put src and provided on sys.path; provided/ is correct by
definition). Then classify each claim:
- "confirmed": you reproduced a behaviour that violates a numbered rule or the interface of the brief;
- "ambiguous": the brief genuinely supports more than one reading and the code follows one of them;
- "rejected": you could not reproduce it, the claim misreads the brief or the provided code, or the behaviour
  is allowed by the brief.
Default to "rejected" if you cannot reproduce. Do not modify files under the repository.

CLAIMS:
{claims}

Finish with ONLY this JSON (no prose after it):
{{"verdicts": [{{"i": 0, "verdict": "confirmed|ambiguous|rejected", "evidence": "..."}}]}}
"""


def main():
    run = Path(sys.argv[1]).resolve()
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "claude-opus-5-5"
    br = json.loads((run / "blind_review.json").read_text())
    defects = (br.get("parsed") or {}).get("defects") or []
    meta = json.loads((run / "meta.json").read_text())
    if not defects:
        (run / "blind_manual.json").write_text("{}")
        print(f"{meta['run_id']}: no defects to verify")
        return
    rid = hashlib.sha1(str(run).encode()).hexdigest()[:10]
    box = E15 / "reviews" / rid
    claims = "\n".join(f"[{i}] rule {d.get('rule')} ({d.get('severity')}) at {d.get('location')}: {d.get('description')} "
                       f"Reviewer's evidence: {str(d.get('evidence'))[:600]}" for i, d in enumerate(defects))
    t0 = time.time()
    out = box / "verify.jsonl"
    with open(out, "w") as fo, open(box / "verify.stderr", "w") as fe:
        p = subprocess.run([SANDBOX, str(box), "--", "-p", PROMPT.format(claims=claims), "--model", model,
                            "--output-format", "stream-json", "--verbose", "--setting-sources", "project,local",
                            "--permission-mode", "bypassPermissions", "--max-budget-usd", "6"],
                           stdout=fo, stderr=fe, timeout=3000)
    res = None
    for line in out.read_text(errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "result":
            res = d
    text = (res or {}).get("result") or ""
    parsed = None
    i = text.rfind('{"verdicts"')
    if i >= 0:
        try:
            parsed = json.loads(text[i:text.rfind("}") + 1])
        except json.JSONDecodeError:
            parsed = None
    manual = {}
    for v in (parsed or {}).get("verdicts", []):
        if str(v.get("verdict")) in ("confirmed", "ambiguous", "rejected"):
            manual[str(v.get("i"))] = v["verdict"]
    (run / "blind_manual.json").write_text(json.dumps(manual, indent=1))
    cost = (res or {}).get("total_cost_usd") or 0
    (run / "blind_verify.json").write_text(json.dumps({"model": model, "cost_usd": cost, "parsed": parsed,
                                                       "raw_tail": text[-3000:]}, indent=1))
    ledger_append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "phase": "blind-verify", "run_id": meta["run_id"],
                   "arm": meta["arm"], "pkg": meta["pkg"], "rep": meta["rep"], "process": "verify",
                   "wall_s": round(time.time() - t0, 1), "cost_usd": f"{cost:.4f}", "killed": "", "rc": p.returncode})
    print(f"{meta['run_id']}: verified {len(manual)}/{len(defects)} cost=${cost:.2f} "
          f"confirmed={sum(1 for v in manual.values() if v == 'confirmed')}")


if __name__ == "__main__":
    main()
