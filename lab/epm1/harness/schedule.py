#!/usr/bin/env python3
"""Run an E-PM1 plan: at most N concurrent run_one.py processes (default 2), hard spend stop read from spend.csv,
pause while E15 has more than 2 live `claude -p` processes, reap lingering finished `claude -p` processes of E-PM1,
skip runs already complete (checkpointed), seeded shuffle within each block, blocks in the given priority order.

usage: schedule.py PLAN.json [--concurrency 2] [--stop-usd 470]
PLAN.json: {"name": "full", "seed": 2024, "blocks": [{"name": "main", "runs": [[phase, arm, size, model, effort|null, task, rep], ...]}, ...]}
"""
import json
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EPM1, spent
from run_one import e15_live, modeltag

LOGD = EPM1 / "logs"


def done(r):
    phase, arm, size, model, effort, task, rep = r
    cell = f"{arm}-{size}-{modeltag(model)}" + (f"-{effort}" if effort else "")
    p = EPM1 / "runs" / phase / cell / task / str(rep) / "result.json"
    try:
        return json.loads(p.read_text()).get("complete", False)
    except (OSError, json.JSONDecodeError):
        return False


def reap():
    """Kill E-PM1 `claude -p` processes whose stream already ended with a result and has been idle >= 60 s."""
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if not cmd or not cmd[0].endswith(b"claude") or b"-p" not in cmd:
                continue
            out = os.readlink(f"/proc/{pid}/fd/1")
        except OSError:
            continue
        if "/home/claude/epm1/runs/" not in out or out.endswith(" (deleted)"):
            continue
        try:
            lp = Path(out)
            if time.time() - lp.stat().st_mtime < 60:
                continue
            last = lp.read_text(errors="replace").strip().splitlines()[-1]
            if json.loads(last).get("type") == "result":
                os.kill(int(pid), signal.SIGTERM)
                with open(LOGD / "reaper.log", "a") as f:
                    f.write(f"{time.strftime('%H:%M:%S')} reaped {pid} {out}\n")
        except (OSError, IndexError, json.JSONDecodeError):
            continue


def epm1_live():
    """Live `claude -p` processes of E-PM1 (any scheduler), so the global limit holds across restarts."""
    n = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if cmd and cmd[0].endswith(b"claude") and b"-p" in cmd and "/home/claude/epm1/runs/" in os.readlink(f"/proc/{pid}/fd/1"):
                n += 1
        except OSError:
            continue
    return n


def main():
    plan = json.loads(Path(sys.argv[1]).read_text())
    conc = int(sys.argv[sys.argv.index("--concurrency") + 1]) if "--concurrency" in sys.argv else 2
    stop = float(sys.argv[sys.argv.index("--stop-usd") + 1]) if "--stop-usd" in sys.argv else 470.0
    LOGD.mkdir(exist_ok=True)
    rng = random.Random(plan.get("seed", 2024))
    queue = []
    for b in plan["blocks"]:
        runs = [tuple(r) for r in b["runs"]]
        rng.shuffle(runs)
        queue += [(b["name"], r) for r in runs if not done(r)]
    (LOGD / f"schedule-{plan['name']}.order.json").write_text(json.dumps(queue))
    active = []
    print(f"{time.strftime('%H:%M:%S')} plan {plan['name']}: {len(queue)} runs to do, spent {spent():.2f}", flush=True)
    while queue or active:
        active = [(r, p) for r, p in active if p.poll() is None]
        reap()
        if spent() >= stop:
            if queue:
                print(f"{time.strftime('%H:%M:%S')} STOP: spend {spent():.2f} >= {stop}; {len(queue)} runs not started", flush=True)
            queue = []
        while queue and len(active) < conc and max(epm1_live(), len(active)) < conc and e15_live() <= 2:
            blk, r = queue.pop(0)
            phase, arm, size, model, effort, task, rep = r
            args = [sys.executable, "-I", str(EPM1 / "harness/run_one.py"), "--phase", phase, "--arm", arm, "--size", str(size),
                    "--model", model, "--task", task, "--rep", str(rep)]
            if effort:
                args += ["--effort", effort]
            log = open(LOGD / f"{plan['name']}.runs.log", "a")
            active.append((r, subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)))
            print(f"{time.strftime('%H:%M:%S')} START [{blk}] {arm}-{size}-{modeltag(model)}{'-' + effort if effort else ''} {task} r{rep} "
                  f"(spent {spent():.2f}, left {len(queue)})", flush=True)
        time.sleep(3)
    print(f"{time.strftime('%H:%M:%S')} PLAN DONE {plan['name']} spent {spent():.2f}", flush=True)


if __name__ == "__main__":
    main()
