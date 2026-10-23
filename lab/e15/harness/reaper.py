#!/usr/bin/env python3
"""Reap finished-but-lingering `claude -p` processes of E15 runs.

With CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 (needed so a running verification workflow is not killed),
print mode can wait forever after its last turn even when nothing is running. A process is reaped only if
ALL hold: its stdout log's last event is a `result`; the last `background_tasks_changed` event lists no
tasks; every `task_started` has a matching notification or terminal update; and the log has been silent
for >= IDLE seconds. Each reap is written to <rundir>/logs/<label>.reaped (and reaper.log).

usage: reaper.py [--idle 60] [--once]
"""
import json
import os
import signal
import sys
import time
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
IDLE = int(sys.argv[sys.argv.index("--idle") + 1]) if "--idle" in sys.argv else 60


def wakeup_delay(log: Path) -> int:
    """Largest ScheduleWakeup delay requested in this stream: a self-scheduled wake-up must be allowed to fire."""
    best = 0
    try:
        for line in log.read_text(errors="replace").splitlines():
            if '"ScheduleWakeup"' not in line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            for c in (d.get("message") or {}).get("content", []) or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "ScheduleWakeup":
                    try:
                        best = max(best, int((c.get("input") or {}).get("delaySeconds", 0)))
                    except (TypeError, ValueError):
                        pass
    except OSError:
        pass
    return best


def finished(log: Path) -> bool:
    last_type, bg, started, done = None, None, set(), set()
    try:
        lines = log.read_text(errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "system":
            st = d.get("subtype")
            if st == "task_started":
                started.add(d.get("task_id"))
            elif st == "task_notification":
                done.add(d.get("task_id"))
            elif st == "task_updated" and (d.get("patch") or {}).get("status") in ("completed", "failed", "killed", "stopped"):
                done.add(d.get("task_id"))
            elif st == "background_tasks_changed":
                bg = d.get("tasks", [])
            if st in ("thinking_tokens", "hook_started", "hook_response"):
                continue
        if t in ("assistant", "user", "result") or (t == "system" and d.get("subtype") in ("task_started", "init")):
            last_type = t
    return last_type == "result" and (bg is None or bg == []) and started <= done


def scan():
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
        if "/home/claude/e15/runs/" not in out and "/home/claude/e15/reviews/" not in out:
            continue
        if out.endswith(" (deleted)"):
            continue
        log = Path(out)
        try:
            if time.time() - log.stat().st_mtime < IDLE + wakeup_delay(log):
                continue
        except OSError:
            continue
        if finished(log):
            os.kill(int(pid), signal.SIGTERM)
            marker = log.with_suffix(".reaped")
            marker.write_text(json.dumps({"t": time.time(), "pid": int(pid), "idle_s": round(time.time() - log.stat().st_mtime)}))
            with open(E15 / "logs/reaper.log", "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} reaped pid {pid} {log}\n")


def main():
    while True:
        try:
            scan()
        except Exception as e:  # never die; log and continue
            with open(E15 / "logs/reaper.log", "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} scan error {e!r}\n")
        if "--once" in sys.argv:
            break
        time.sleep(15)


if __name__ == "__main__":
    main()
