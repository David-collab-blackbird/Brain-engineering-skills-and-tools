#!/usr/bin/env python3
"""Run one E15 arm on one package, isolated, with the scripted owner proxy.

usage: run_arm.py ARM PKG REP [--phase NAME] [--cap USD] [--drill KILL_AT_S] [--timeout S]

  ARM  A | B | C | D | AU (ablation: A + ultracode) | AR (ablation: A + D's reading list)
  PKG  P1 | P2

Layout: runs/<ARM>/<PKG>/<REP>/{work,home,logs,meta.json,metrics.json,grade.json,tamper.json}
Every claude process runs in harness/sandbox_claude.sh (hidden tests unreachable).
"""
import argparse
import csv
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
H = E15 / "harness"
MODEL = "claude-sonnet-5-5"          # the CLI default on this account (recorded in PREREGISTRATION.md)
SANDBOX = str(H / "sandbox_claude.sh")
OWNER = json.loads((H / "owner_answers.json").read_text())
MAX_OWNER_TURNS = 5
PROMPT = ("Build the work package specified in packages/{brief} (an approved design). The visible acceptance "
          "tests are in tests/acceptance/ (run them with `make test`). Work autonomously until the package's "
          "done line is met.")
PROMPT_D = PROMPT + " ultrathink: plan thoroughly before you build."
RESUME_PROMPT = ("Resume building the work package specified in packages/{brief} from the current repository "
                 "state (a previous session was interrupted). Work autonomously until the package's done line is met.")

ARMS = {
    "A": {"files": ["A"], "flags": [], "protect": True, "prompt": PROMPT},
    "B": {"files": ["B"], "flags": ["--plugin-dir", "/opt/e15/superpowers-7.0.1"], "protect": False, "prompt": PROMPT},
    "C": {"files": ["C"], "flags": [], "protect": True, "prompt": PROMPT},
    "D": {"files": ["D"], "flags": ["--effort", "ultracode"], "protect": False, "prompt": PROMPT_D},
    "AU": {"files": ["A"], "flags": ["--effort", "ultracode"], "protect": True, "prompt": PROMPT},
    "AR": {"files": ["A", "D-reading"], "flags": [], "protect": True, "prompt": PROMPT},
}
PROTECTED_PATHS = ["tests", "provided", "packages", "conftest.py", "Makefile", ".claude", "scripts", "CLAUDE.md",
                   "docs"]
ASK_PHRASES = re.compile(r"let me know|please confirm|awaiting|waiting (for|on) (your|the owner)|your call|"
                         r"would you like|do you want|shall i|should i|which (option|approach)|how would you like",
                         re.I)


def sh(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), check=check, capture_output=True,
                          text=True).stdout


def prepare(run: Path, arm: str, pkg: str):
    if run.exists():
        if (run / "meta.json").exists() and not (run / "metrics.json").exists():
            raise SystemExit(f"refusing to overwrite an unfinished run directory: {run}")
        if (run / "INVALID").exists():
            raise SystemExit(f"refusing to overwrite an invalidated run directory: {run}")
        logs = list((run / "logs").glob("*.jsonl")) if (run / "logs").exists() else []
        if logs and not (run / "metrics.json").exists() and \
                time.time() - max(f.stat().st_mtime for f in logs) < 7200:
            raise SystemExit(f"refusing to overwrite a run directory with recent activity: {run}")
        shutil.rmtree(run)
    work, home, logs = run / "work", run / "home", run / "logs"
    for d in (work, home, logs):
        d.mkdir(parents=True)
    tpl = E15 / ("template3" if pkg in ("P3", "P4") else "template")
    shutil.copytree(tpl / "common", work, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if pkg in ("P2", "P4"):
        shutil.copytree(tpl / "P2", work, dirs_exist_ok=True)
    for f in ARMS[arm]["files"]:
        if f == "D-reading":
            shutil.copytree(E15 / "arms/D/files/docs", work / "docs")
            claude_md = (work / "CLAUDE.md").read_text() + "\n" + (E15 / "arms/D/files/CLAUDE.md").read_text()
            (work / "CLAUDE.md").write_text(claude_md)
        else:
            shutil.copytree(E15 / "arms" / f / "files", work, dirs_exist_ok=True)
    if pkg in ("P3", "P4"):
        for f in list(work.rglob("*.md")) + list(work.rglob("*.js")) + list(work.rglob("*.json")) + \
                list(work.rglob("*.py")):
            if ".git" in f.parts or "provided" in f.parts or "packages" in f.parts or "tests" in f.parts:
                continue
            s = f.read_text(errors="replace")
            s2 = s.replace("WP-E15.md", "WP-E15C.md").replace("src/vretrieval/", "src/cards/").replace(
                "WP-E15:", "WP-E15C:").replace("(R2, R2a, R6, R7 here)", "(R1, R2, R5, R9, R10, R11 here)")
            if s2 != s:
                f.write_text(s2)
    (work / "tests/unit").mkdir(parents=True, exist_ok=True)
    env = {"GIT_AUTHOR_NAME": "engineer", "GIT_AUTHOR_EMAIL": "e@e15", "GIT_COMMITTER_NAME": "engineer",
           "GIT_COMMITTER_EMAIL": "e@e15", "PATH": "/usr/bin:/bin", "HOME": str(home)}
    subprocess.run("git init -q -b main && git add -A && git commit -qm 'WP-E15 template'", shell=True,
                   cwd=work, check=True, env=env)
    (home / ".gitconfig").write_text("[user]\n\tname = builder\n\temail = builder@e15\n[safe]\n\tdirectory = *\n")
    base = sh("git rev-parse HEAD", cwd=work).strip()
    if ARMS[arm]["protect"]:
        for p in PROTECTED_PATHS:
            if (work / p).exists():
                subprocess.run(["chown", "-R", "nobody:nogroup", str(work / p)], check=True)
                subprocess.run(f"find '{work / p}' -type d -exec chmod 555 {{}} + ; "
                               f"find '{work / p}' -type f -exec chmod 444 {{}} +", shell=True, check=True)
        # sticky, world-writable repo root owned by nobody: the builder (root without capabilities) can create
        # and delete its own files but cannot rename or delete the engineer-owned entries in it
        subprocess.run(["chown", "nobody:nogroup", str(work)], check=True)
        os.chmod(work, 0o1777)
        os.chmod(work / "tests", 0o1777)
        subprocess.run(["chown", "root:root", str(work / "tests/unit")], check=True)
        os.chmod(work / "tests/unit", 0o755)
    return base


def parse_stream(path: Path):
    out = {"session_id": None, "results": [], "tools": [], "init": None}
    if not path.exists():
        return out
    for line in path.read_text(errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            out["session_id"] = d.get("session_id")
            out["init"] = {k: d.get(k) for k in ("model", "permissionMode", "tools", "plugins", "claude_code_version")}
        elif t == "assistant":
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    out["tools"].append({"name": c.get("name"), "input": c.get("input")})
        elif t == "result":
            out["results"].append(d)
    return out


def questions(work: Path):
    p = work / "build/questions.json"
    try:
        q = json.loads(p.read_text())
    except Exception:
        return []
    if isinstance(q, dict):
        q = q.get("questions", [q])
    return [x for x in q if isinstance(x, (dict, str))]


def q_text(q):
    if isinstance(q, str):
        return q
    return " ".join(str(v) for v in q.values())


def owner_reply(new_qs, final_text, given, passed, pkg):
    asked = [q_text(q) for q in new_qs]
    asked += [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", final_text or "") if s.strip().endswith("?")]
    tail = (final_text or "")[-2500:]
    text_asks = bool(asked) or bool(ASK_PHRASES.search(tail))
    blob = "\n".join(asked) + ("\n" + tail if text_asks else "")
    lines, ids = [], []
    for a in OWNER["answers"]:
        if a["id"] in given or pkg not in a.get("packages", ["P1", "P2"]):
            continue
        if re.search(a["match"], blob, re.I):
            lines.append(a["text"])
            ids.append(a["id"])
    # Reply only to new question entries, or to a message that asks something a scripted answer covers,
    # or to a message that asks while the package is not marked passed.
    if not (new_qs or (text_asks and (ids or not passed))):
        return None, []
    lines.append(OWNER["generic"])
    return "Owner reply:\n" + "\n".join(lines) + "\n\nContinue.", ids


def run_claude(run: Path, arm: str, prompt: str, label: str, budget: float, timeout: int, resume=None,
               kill_check=None):
    args = [SANDBOX, str(run), "--", "-p", prompt, "--model", MODEL, "--output-format", "stream-json", "--verbose",
            "--setting-sources", "project,local", "--permission-mode", "bypassPermissions",
            "--max-budget-usd", f"{max(budget, 0.5):.2f}"] + ARMS[arm]["flags"]
    if resume:
        args += ["--resume", resume]
    log = run / "logs" / f"{label}.jsonl"
    err = run / "logs" / f"{label}.stderr"
    t0 = time.time()
    with open(log, "w") as fo, open(err, "w") as fe:
        p = subprocess.Popen(args, stdout=fo, stderr=fe, start_new_session=True)
        killed = None
        while p.poll() is None:
            time.sleep(5)
            el = time.time() - t0
            if el > timeout:
                killed = "timeout"
            elif kill_check and kill_check(el):
                killed = "drill"
            if killed:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(20)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                break
    wall = time.time() - t0
    st = parse_stream(log)
    # total_cost_usd is cumulative per session (also across --resume); the caller converts to increments
    cost = max([r.get("total_cost_usd") or 0 for r in st["results"]] or [0])
    cost_estimated = False
    if killed and st["session_id"]:
        # killed before (or after) a result: estimate the session's spend from its transcripts at list prices
        est = transcript_cost(run / "home", st["session_id"])
        if est > cost:
            cost, cost_estimated = est, True
    final = st["results"][-1].get("result", "") if st["results"] else ""
    return {"label": label, "rc": p.returncode, "killed": killed, "wall_s": round(wall, 1), "cost": cost,
            "cost_estimated": cost_estimated,
            "session_id": st["session_id"], "final_text": final, "n_results": len(st["results"]),
            "init": st["init"], "is_error": any(r.get("is_error") for r in st["results"]),
            "subtypes": [r.get("subtype") for r in st["results"]]}


def transcript_cost(home: Path, session_id: str) -> float:
    """List-price cost of one session (main transcript + its subagents/workflow agents), from transcripts."""
    sys.path.insert(0, str(H))
    from score_run import price
    total, seen = 0.0, set()
    files = list(home.glob(f".claude/projects/*/{session_id}.jsonl")) + \
        list(home.glob(f".claude/projects/*/{session_id}/**/*.jsonl"))
    for f in files:
        for line in f.read_text(errors="replace").splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "assistant":
                continue
            m = d.get("message", {})
            if m.get("id") in seen:
                continue
            seen.add(m.get("id"))
            total += price(m.get("model", ""), m.get("usage") or {})
    return round(total, 6)


def ledger_append(row: dict):
    path = E15 / "spend.csv"
    fields = ["time", "phase", "run_id", "arm", "pkg", "rep", "process", "wall_s", "cost_usd", "killed", "rc",
              "cumulative_usd"]
    with open(path, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        rows = list(csv.DictReader(f)) if f.read(1) else []
        f.seek(0)
        cum = sum(float(r["cost_usd"]) for r in rows) + float(row["cost_usd"])
        row["cumulative_usd"] = f"{cum:.4f}"
        f.seek(0, 2)
        w = csv.DictWriter(f, fieldnames=fields)
        if not rows and f.tell() == 0:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})
        fcntl.flock(f, fcntl.LOCK_UN)


def git_commits(work: Path, base: str):
    out = subprocess.run(["git", "-c", "safe.directory=*", "rev-list", "--count", f"{base}..HEAD"], cwd=work,
                         capture_output=True, text=True)
    try:
        return int(out.stdout.strip())
    except ValueError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("pkg")
    ap.add_argument("rep")
    ap.add_argument("--phase", default="full")
    ap.add_argument("--cap", type=float, default=40.0)
    ap.add_argument("--drill", type=float, default=0.0, help="kill after first checkpoint commit, or at this many s")
    ap.add_argument("--timeout", type=int, default=6000)
    a = ap.parse_args()
    run_id = f"{a.arm}-{a.pkg}-{a.rep}"
    run = E15 / "runs" / a.arm / a.pkg / str(a.rep)
    base = prepare(run, a.arm, a.pkg)
    meta = {"run_id": run_id, "arm": a.arm, "pkg": a.pkg, "rep": a.rep, "phase": a.phase, "model": MODEL,
            "flags": ARMS[a.arm]["flags"], "protect": ARMS[a.arm]["protect"], "base": base, "cap": a.cap,
            "start": time.time(), "processes": [], "owner_turns": [], "drill": bool(a.drill)}
    spent = 0.0
    seen_q = 0
    given = []
    session_cum = {}

    def record(res):
        nonlocal spent
        sid = res["session_id"]
        prev = session_cum.get(sid, 0.0)
        inc = max(res["cost"] - prev, 0.0)
        if sid:
            session_cum[sid] = max(res["cost"], prev)
        res["session_cumulative_cost"] = res["cost"]
        res["cost"] = round(inc, 6)
        spent += inc
        meta["processes"].append(res)
        ledger_append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "phase": a.phase, "run_id": run_id,
                       "arm": a.arm, "pkg": a.pkg, "rep": a.rep, "process": res["label"], "wall_s": res["wall_s"],
                       "cost_usd": f"{res['cost']:.4f}", "killed": res["killed"] or "", "rc": res["rc"]})
        (run / "meta.json").write_text(json.dumps(meta, indent=1))

    work = run / "work"
    kill_check = None
    if a.drill:
        def kill_check(el):
            return (git_commits(work, base) >= 1 and el >= 90) or el >= a.drill
    brief = "WP-E15C.md" if a.pkg in ("P3", "P4") else "WP-E15.md"
    res = run_claude(run, a.arm, ARMS[a.arm]["prompt"].format(brief=brief), "p0", a.cap, a.timeout,
                     kill_check=kill_check)
    record(res)
    session = res["session_id"]
    if a.drill:
        meta["drill_killed_at_s"] = res["wall_s"]
        meta["drill_commits_at_kill"] = git_commits(work, base)
        meta["drill_head_at_kill"] = sh("git -c safe.directory=* rev-parse HEAD", cwd=work).strip()
        res = run_claude(run, a.arm, RESUME_PROMPT.format(brief=brief), "r0", a.cap - spent, a.timeout)
        record(res)
        session = res["session_id"]
    turn = 0
    while turn < MAX_OWNER_TURNS and spent < a.cap and not res["killed"]:
        qs = questions(work)
        new_qs = qs[seen_q:]
        seen_q = len(qs)
        try:
            passed = json.loads((work / "build/state.json").read_text()).get("status") == "passed"
        except Exception:
            passed = False
        reply, ids = owner_reply(new_qs, res["final_text"], given, passed, a.pkg)
        if reply is None or not session:
            break
        given += ids
        turn += 1
        meta["owner_turns"].append({"turn": turn, "answers": ids, "new_questions": new_qs,
                                    "final_text_tail": (res["final_text"] or "")[-1500:]})
        res = run_claude(run, a.arm, reply, f"o{turn}", a.cap - spent + session_cum.get(session, 0.0), a.timeout,
                         resume=session)
        record(res)
        session = res["session_id"] or session
    meta["end"] = time.time()
    meta["wall_s"] = round(meta["end"] - meta["start"], 1)
    meta["cost_usd"] = round(spent, 4)
    meta["final_questions"] = questions(work)
    (run / "meta.json").write_text(json.dumps(meta, indent=1))
    subprocess.run([sys.executable, str(H / "score_run.py"), str(run)], check=False)
    print(json.dumps({"run": run_id, "cost": meta["cost_usd"], "wall_s": meta["wall_s"],
                      "owner_turns": len(meta["owner_turns"])}))


if __name__ == "__main__":
    main()
