#!/usr/bin/env python3
"""Blind-review every finished run of a phase that has no review yet (sequential, low priority).

usage: review_all.py [--phase full] [--wait]   (--wait: keep polling until the schedule is done)
"""
import json
import subprocess
import sys
import time
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]


def pending(phase):
    out = []
    for m in sorted(E15.glob("runs/*/*/*/metrics.json")):
        d = json.loads(m.read_text())
        if d.get("phase") == phase and not (m.parent / "blind_review.json").exists() and not (m.parent / "INVALID").exists():
            out.append(m.parent)
    return out


def main():
    phase = sys.argv[sys.argv.index("--phase") + 1] if "--phase" in sys.argv else "full"
    wait = "--wait" in sys.argv
    while True:
        todo = pending(phase)
        for run in todo:
            subprocess.run([sys.executable, str(E15 / "harness/blind_review.py"), str(run)], check=False)
            if (run / "blind_review.json").exists():
                subprocess.run([sys.executable, str(E15 / "harness/verify_defects.py"), str(run)], check=False)
                subprocess.run([sys.executable, str(E15 / "harness/adjudicate.py"), str(run)], check=False)
        log = (E15 / "logs/schedule-full.log").read_text() if (E15 / "logs/schedule-full.log").exists() else ""
        if not wait or ("SCHEDULE DONE" in log and not pending(phase)):
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
