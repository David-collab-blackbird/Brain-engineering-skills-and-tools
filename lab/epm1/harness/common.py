"""Shared helpers for the E-PM1 harness: paths, list prices, spend ledger, plain (non-agent) claude calls."""
import csv
import fcntl
import json
import os
import subprocess
import time
from pathlib import Path

EPM1 = Path("/home/claude/epm1")
MAT = EPM1 / "materials"
H = EPM1 / "harness"
SPEND = EPM1 / "spend.csv"
CAP_USD = 480.0

# USD per million tokens, list prices (same table E15 uses: platform pricing page read 2026-10-24)
PRICES = {
    "opus": {"in": 4, "cw5": 5, "cw1h": 8, "cr": 0.2, "out": 20},
    "sonnet": {"in": 2, "cw5": 2.5, "cw1h": 4, "cr": 0.1, "out": 10},
    "haiku": {"in": 0.1, "cw5": 0.125, "cw1h": 0.2, "cr": 0.01, "out": 0.5},
}
FIELDS = ["time", "phase", "run_id", "model", "cost_usd", "wall_s", "rc", "note", "cumulative_usd"]

BASE_FLAGS = ["--tools", "", "--strict-mcp-config", "--no-chrome", "--disable-slash-commands",
              "--no-session-persistence", "--setting-sources", ""]


def clean_env(home: str) -> dict:
    """Environment for a model-under-test process (amendment 3): no inherited session, account, project or memory
    context. Only proxy/CA variables and a fresh HOME (E15's isolation pattern). Verified: with this env the model
    reports no user or project context; with the inherited env it received the account email and the attached
    project's description and document list."""
    os.makedirs(home, exist_ok=True)
    keep = {k: os.environ[k] for k in ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy") if k in os.environ}
    return {"HOME": home, "PATH": "/opt/node22/bin:/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", **keep,
            "SSL_CERT_FILE": "/root/.ccr/ca-bundle.crt", "NODE_EXTRA_CA_CERTS": "/root/.ccr/ca-bundle.crt",
            "IS_SANDBOX": "1", "DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "MCP_TIMEOUT": "30000"}


def leak_markers() -> list:
    """Strings that must never appear in a model-under-test log (read from the parent env at run time; never
    written to disk)."""
    return [v for v in (os.environ.get("CLAUDE_CODE_USER_EMAIL"), os.environ.get("CLAUDE_PROJECT_UUID"),
                        os.environ.get("CLAUDE_CODE_SESSION_ID")) if v] + ["Enterprise 'brain'", "AI Memory Specialist"]


def spent() -> float:
    if not SPEND.exists():
        return 0.0
    with open(SPEND) as f:
        return sum(float(r["cost_usd"] or 0) for r in csv.DictReader(f))


def ledger_append(row: dict):
    with open(SPEND, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        rows = list(csv.DictReader(f)) if f.read(1) else []
        f.seek(0)
        cum = sum(float(r["cost_usd"] or 0) for r in rows) + float(row["cost_usd"])
        row["cumulative_usd"] = f"{cum:.4f}"
        f.seek(0, 2)
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not rows and f.tell() == 0:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
        fcntl.flock(f, fcntl.LOCK_UN)


def plain_call(prompt: str, system: str, model: str, phase: str, run_id: str, budget: float = 1.0, timeout: int = 600,
               effort: str | None = None):
    """One-shot claude -p call (no tools). Returns (result_text, cost). Logs to spend.csv."""
    if spent() >= CAP_USD:
        raise SystemExit("spend cap reached")
    args = ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--system-prompt", system,
            "--max-budget-usd", f"{budget:.2f}"] + BASE_FLAGS
    if effort:
        args += ["--effort", effort]
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                       env=clean_env(str(EPM1 / "clienthome_plain")), cwd=str(EPM1 / "clienthome_plain"))
    wall = time.time() - t0
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        d = {"result": "", "total_cost_usd": 0, "is_error": True}
    cost = float(d.get("total_cost_usd") or 0)
    ledger_append({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "phase": phase, "run_id": run_id, "model": model,
                   "cost_usd": f"{cost:.6f}", "wall_s": f"{wall:.1f}", "rc": p.returncode,
                   "note": "error" if d.get("is_error") else ""})
    return d.get("result", ""), cost, d
