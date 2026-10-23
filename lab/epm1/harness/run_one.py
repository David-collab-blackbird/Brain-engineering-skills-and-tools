#!/usr/bin/env python3
"""Run one E-PM1 trial: one (arm, library size, model, task, rep) through `claude -p` against a fresh fixture brain.

usage: run_one.py --phase P --arm A|B|C|D|W|G|P --size 10|40|120 --model ID --task TID --rep N [--effort E] [--semantics as-written|bound]
  arm W = C with a wrong declared scope (fixed map below); G = PM6 gated; P = PM6 prompt-only.
Layout: runs/<phase>/<arm>-<size>-<modeltag>[-<effort>]/<task>/<rep>/{cfg.json, mcp.json, system.md, user.txt,
        stream.jsonl.gz, brain.jsonl.gz, result.json, score.json}
Checkpoint: a run with result.json {"complete": true} is never redone. Overload/rate-limit errors are retried with
exponential back-off (not counted as outcomes; their spend is still logged).
"""
import argparse
import gzip
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EPM1, MAT, BASE_FLAGS, CAP_USD, ledger_append, spent, clean_env, leak_markers
from prompts import system_prompt, user_turn, arm_context_tokens

WRONG_SCOPE = {"finance/payables": "finance/receivables", "finance/receivables": "finance/payables",
               "finance/compliance": "finance/payables", "people/members": "people/staff", "people/staff": "people/members",
               "ops/incidents": "people/staff", "sales/landscaping": "finance/receivables", "admin/owner": "finance/compliance"}
TRANSIENT = ("overloaded", "rate limit", "rate_limit", "429", "529", "503", "timed out", "ECONNRESET", "socket hang up", "Internal server error")


def modeltag(m):
    return m.replace("claude-", "").replace("-5-5", "55")


def load_task(tid):
    if tid.startswith("G"):
        g = json.load(open(MAT / "gated.json"))
        return next(t for t in g["tasks"] if t["id"] == tid)
    if tid.endswith("-H"):
        return next(t for t in json.load(open(MAT / "tasks_h.json")) if t["id"] == tid)
    return next(t for t in json.load(open(MAT / "tasks.json")) if t["id"] == tid)


def parse_stream(path):
    out = {"session_id": None, "init": None, "tool_uses": [], "texts": [], "results": [], "assistant_usage": []}
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            out["session_id"] = d.get("session_id")
            out["init"] = {k: d.get(k) for k in ("model", "tools", "claude_code_version", "mcp_servers")}
        elif t == "assistant":
            msg = d.get("message", {})
            out["assistant_usage"].append({"id": msg.get("id"), "model": msg.get("model"), "usage": msg.get("usage")})
            for c in msg.get("content", []):
                if c.get("type") == "tool_use":
                    out["tool_uses"].append({"name": c.get("name"), "input": c.get("input")})
                elif c.get("type") == "text":
                    out["texts"].append(c.get("text", ""))
        elif t == "result":
            out["results"].append(d)
    return out


def e15_live():
    """Count live `claude -p` processes belonging to E15 (stdout under /home/claude/e15/)."""
    n = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if not cmd or not cmd[0].endswith(b"claude") or b"-p" not in cmd:
                continue
            if "/home/claude/e15/" in os.readlink(f"/proc/{pid}/fd/1"):
                n += 1
        except OSError:
            continue
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--size", default="40")
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--effort", default=None)
    ap.add_argument("--semantics", default="as-written")
    ap.add_argument("--budget", type=float, default=1.0)
    ap.add_argument("--timeout", type=int, default=420)
    a = ap.parse_args()

    cell = f"{a.arm}-{a.size}-{modeltag(a.model)}" + (f"-{a.effort}" if a.effort else "")
    run = EPM1 / "runs" / a.phase / cell / a.task / str(a.rep)
    res_path = run / "result.json"
    if res_path.exists() and json.loads(res_path.read_text()).get("complete"):
        print(json.dumps({"skip": str(run)}))
        return
    if spent() >= CAP_USD:
        raise SystemExit("spend cap reached")
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)

    task = load_task(a.task)
    gated = a.arm in ("G", "P", "GB")
    if a.arm == "GB":
        a.semantics = "bound"
    scope = WRONG_SCOPE[task["scope"]] if a.arm == "W" else task["scope"]
    routed = None
    if a.arm in ("D", "DN"):
        routing = json.load(open(MAT / "routing.json"))
        routed = routing[a.size + ("H" if a.task.endswith("-H") else "")][a.task]["push"]
    gated_proc = None
    task_ref = None
    if gated:
        gated_proc = {"payment": "pay-supplier-bill", "external_send": "external-send", "deletion": "data-loss-gate"}[task["action"]]
        task_ref = f"tsk-{a.task}-{cell}-r{a.rep}".lower()
    client = "minimal" if a.arm in ("AN", "BN", "CN", "DN") else "full"
    arm_for_prompt = {"W": "C", "GB": "G", "AN": "A", "BN": "B", "CN": "C", "DN": "D"}.get(a.arm, a.arm)
    sysmd = system_prompt(arm_for_prompt, a.size, scope, routed=routed, gated_proc=gated_proc, client=client)
    user = user_turn(task, scope=scope, task_ref=task_ref)
    (run / "system.md").write_text(sysmd)
    (run / "user.txt").write_text(user)
    cfg = {"materials": str(MAT), "size": a.size, "mode": {"G": "gated", "GB": "gated", "P": "prompt"}.get(a.arm, "main"), "task_id": task_ref or a.task,
           "business": task["business"], "principal": "agent:ops-assistant (acting for the requester)", "log": str(run / "brain.jsonl"),
           "gate_semantics": a.semantics, "client": client}
    (run / "cfg.json").write_text(json.dumps(cfg, indent=1))
    (run / "mcp.json").write_text(json.dumps({"mcpServers": {"brain": {"type": "stdio", "command": "/usr/bin/python3",
                                                                      "args": ["-I", str(EPM1 / "harness/brain_mcp.py"), str(run / "cfg.json")]}}}))
    args = ["claude", "-p", user, "--model", a.model, "--output-format", "stream-json", "--verbose",
            "--system-prompt-file", str(run / "system.md"), "--mcp-config", str(run / "mcp.json"),
            "--permission-mode", "bypassPermissions", "--max-budget-usd", f"{a.budget:.2f}"] + BASE_FLAGS
    if a.effort:
        args += ["--effort", a.effort]
    env = clean_env(str(run / "home"))

    attempts = []
    delay = 30
    for attempt in range(5):
        while e15_live() > 2:
            time.sleep(20)
        stream = run / "stream.jsonl"
        if (run / "brain.jsonl").exists():
            (run / "brain.jsonl").unlink()
        t0 = time.time()
        killed = None
        with open(stream, "w") as fo, open(run / "stderr.txt", "w") as fe:
            p = subprocess.Popen(args, stdout=fo, stderr=fe, stdin=subprocess.DEVNULL, cwd=run, env=env, start_new_session=True)
            while p.poll() is None:
                time.sleep(1)
                if time.time() - t0 > a.timeout:
                    killed = "timeout"
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(15)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait()
        wall = time.time() - t0
        st = parse_stream(stream)
        res = st["results"][-1] if st["results"] else {}
        cost = float(res.get("total_cost_usd") or 0)
        if killed and not res:
            # estimate from per-message usage at list prices
            from common import PRICES
            seen, c = set(), 0.0
            for u in st["assistant_usage"]:
                if u["id"] in seen or not u["usage"]:
                    continue
                seen.add(u["id"])
                fam = "opus" if "opus" in (u["model"] or "") else "haiku" if "haiku" in (u["model"] or "") else "sonnet"
                pr, us = PRICES[fam], u["usage"]
                c += (us.get("input_tokens", 0) * pr["in"] + us.get("cache_creation_input_tokens", 0) * pr["cw1h"]
                      + us.get("cache_read_input_tokens", 0) * pr["cr"] + us.get("output_tokens", 0) * pr["out"]) / 1e6
            cost = round(c, 6)
        err_text = (res.get("result") or "") + " " + (run / "stderr.txt").read_text(errors="replace")[-2000:]
        transient = (res.get("is_error") or not res) and any(s.lower() in err_text.lower() for s in TRANSIENT)
        ledger_append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "phase": a.phase, "run_id": f"{cell}/{a.task}/{a.rep}",
                       "model": a.model, "cost_usd": f"{cost:.6f}", "wall_s": f"{wall:.1f}", "rc": p.returncode,
                       "note": ("transient-retry" if transient else (killed or ("error" if res.get("is_error") else "")))})
        attempts.append({"attempt": attempt, "wall_s": round(wall, 1), "cost": cost, "killed": killed, "rc": p.returncode,
                         "is_error": res.get("is_error"), "subtype": res.get("subtype"), "transient": transient})
        if transient and attempt < 4:
            time.sleep(delay)
            delay = min(delay * 2, 480)
            continue
        break

    # isolation guard (amendment 3): the run must not have seen the parent session's account or project context
    markers = leak_markers()
    blob = (run / "stream.jsonl").read_text(errors="replace") + ((run / "brain.jsonl").read_text(errors="replace") if (run / "brain.jsonl").exists() else "")
    init = st["init"] or {}
    raw_init = next((json.loads(l) for l in blob.splitlines() if '"subtype":"init"' in l.replace(" ", "")), {})
    iso = {"marker_found": any(m in blob for m in markers),
           "session_is_parent": raw_init.get("session_id") == os.environ.get("CLAUDE_CODE_SESSION_ID"),
           "user_context_builds": (raw_init.get("startup_timing") or {}).get("user_context_builds"),
           "entrypoint": (raw_init.get("startup_timing") or {}).get("entrypoint")}
    iso["ok"] = not iso["marker_found"] and not iso["session_is_parent"] and not iso["user_context_builds"]
    if iso["marker_found"]:
        for f in ("stream.jsonl", "brain.jsonl"):
            fp = run / f
            if fp.exists():
                t = fp.read_text(errors="replace")
                for m in markers:
                    t = t.replace(m, "<redacted>")
                fp.write_text(t)
        final_scrub = True
    usage = res.get("usage") or {}
    # gzip logs (kept for scoring and hand-checks)
    for f in ("stream.jsonl", "brain.jsonl"):
        fp = run / f
        if fp.exists():
            with open(fp, "rb") as fi, gzip.open(str(fp) + ".gz", "wb") as fo:
                shutil.copyfileobj(fi, fo)
            fp.unlink()
    final_text = res.get("result") or (st["texts"][-1] if st["texts"] else "")
    for m in markers:
        final_text = final_text.replace(m, "<redacted>")
    out = {"complete": bool(res) and not attempts[-1]["transient"] and iso["ok"], "isolation": iso, "phase": a.phase, "cell": cell, "arm": a.arm, "size": a.size,
           "model": a.model, "effort": a.effort, "task": a.task, "rep": a.rep, "scope_declared": scope, "routed": routed,
           "gated_proc": gated_proc, "task_ref": task_ref, "semantics": a.semantics,
           "cost_usd": round(sum(x["cost"] for x in attempts), 6), "cost_final_attempt": attempts[-1]["cost"],
           "wall_s": attempts[-1]["wall_s"], "attempts": attempts, "num_turns": res.get("num_turns"),
           "duration_ms": res.get("duration_ms"), "is_error": res.get("is_error"), "subtype": res.get("subtype"),
           "usage": {k: usage.get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")},
           "model_usage": res.get("modelUsage"), "arm_context_tokens_est": arm_context_tokens(arm_for_prompt, a.size, scope, routed, gated_proc, client),
           "client": client,
           "init": st["init"], "n_tool_uses": len(st["tool_uses"]), "final_text": final_text[-4000:],
           "cli_version": (st["init"] or {}).get("claude_code_version")}
    res_path.write_text(json.dumps(out, indent=1))
    subprocess.run([sys.executable, "-I", str(EPM1 / "harness/score.py"), str(run)], check=False)
    print(json.dumps({"run": str(run.relative_to(EPM1)), "cost": out["cost_usd"], "wall": out["wall_s"], "complete": out["complete"]}))


if __name__ == "__main__":
    main()
