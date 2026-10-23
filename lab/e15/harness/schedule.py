#!/usr/bin/env python3
"""Run a randomised E15 schedule, at most N concurrent runs, with a spend stop.

usage: schedule.py PLAN.json [--concurrency 2] [--stop-usd 500]
PLAN.json: {"phase": "full", "seed": 1515, "runs": [["A","P3",2], ["D","P3",2], ...], "caps": {"D": 90, ...},
            "drill": {"A-P1-9": 0}}   (drill: run ids that get a kill-and-resume drill; value = kill-at seconds, 0 = auto)
Skips runs whose metrics.json already exists. Order is shuffled with the seed, then kept.
"""
import csv
import json
import random
import subprocess
import sys
import time
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
CAPS = {"A": 40, "B": 60, "C": 40, "D": 90, "AU": 90, "AR": 60}


def spent():
    p = E15 / "spend.csv"
    if not p.exists():
        return 0.0
    with open(p) as f:
        return sum(float(r["cost_usd"] or 0) for r in csv.DictReader(f))


def main():
    plan = json.loads(Path(sys.argv[1]).read_text())
    conc = int(sys.argv[sys.argv.index("--concurrency") + 1]) if "--concurrency" in sys.argv else 2
    stop = float(sys.argv[sys.argv.index("--stop-usd") + 1]) if "--stop-usd" in sys.argv else 500.0
    runs = [tuple(r) for r in plan["runs"]]
    random.Random(plan.get("seed", 1515)).shuffle(runs)
    caps = {**CAPS, **plan.get("caps", {})}
    drills = plan.get("drill", {})
    (E15 / "logs").mkdir(exist_ok=True)
    order_file = E15 / "logs" / f"schedule-{plan['phase']}.order.json"
    order_file.write_text(json.dumps(runs))
    active = []
    def in_progress(r):
        import subprocess as sp
        out = sp.run(["pgrep", "-f", f"[r]un_arm.py {r[0]} {r[1]} {r[2]} "], capture_output=True, text=True).stdout
        return bool(out.strip())
    queue = [r for r in runs if not (E15 / "runs" / r[0] / r[1] / str(r[2]) / "metrics.json").exists()
             and not in_progress(r)]
    adopted = len([r for r in runs if in_progress(r)])
    while queue or active or adopted:
        active = [(r, p) for r, p in active if p.poll() is None]
        adopted = len([r for r in runs if in_progress(r)]) - len(active)
        adopted = max(adopted, 0)
        if spent() >= stop:
            print(f"STOP: spend {spent():.2f} >= {stop}", flush=True)
            queue = []
        while queue and len(active) + adopted < conc:
            arm, pkg, rep = queue.pop(0)
            if in_progress((arm, pkg, rep)):
                continue
            rid = f"{arm}-{pkg}-{rep}"
            args = [sys.executable, str(E15 / "harness/run_arm.py"), arm, pkg, str(rep), "--phase", plan["phase"],
                    "--cap", str(caps[arm])]
            if arm in ("D", "AU"):
                args += ["--timeout", "9000"]
            if rid in drills:
                args += ["--drill", str(drills[rid] or 900)]
            log = open(E15 / "logs" / f"{plan['phase']}-{rid}.out", "w")
            print(f"{time.strftime('%H:%M:%S')} START {rid} (spent {spent():.2f})", flush=True)
            active.append(((arm, pkg, rep), subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)))
        time.sleep(15)
    print(f"{time.strftime('%H:%M:%S')} SCHEDULE DONE spent {spent():.2f}", flush=True)


if __name__ == "__main__":
    main()
