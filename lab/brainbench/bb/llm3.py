"""Headless `claude -p` caller for batch 3, run in its own worker process.

* One claude process at a time (fcntl lock on cache_v03/llm.lock), shared with every batch-3 stage.
* Every call is cached by sha256(model, system, prompt); a re-run never pays twice.
* Every paid call is appended to results_v03/spend_ledger.jsonl (model IDs from modelUsage, tokens, USD, wall time,
  stage, batch id). A hard cap (env BB3_CAP_USD, default 200) is checked before each call.
* Minimal CLI context: no tools, no MCP, no settings sources, no slash commands, no session persistence, neutral cwd.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import tempfile
import time

from .common import ROOT

CACHE = os.path.join(ROOT, "cache_v03", "llm")
LEDGER = os.path.join(ROOT, "results_v03", "spend_ledger.jsonl")
LOCK = os.path.join(ROOT, "cache_v03", "llm.lock")
CWD = os.path.join(ROOT, "cache_v03", "cwd")
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}


def spent():
    tot = 0.0
    if os.path.exists(LEDGER):
        with open(LEDGER) as f:
            for ln in f:
                try:
                    tot += json.loads(ln).get("usd", 0.0)
                except json.JSONDecodeError:
                    pass
    return tot


def spent_by(stage_prefix=""):
    out = {}
    if os.path.exists(LEDGER):
        with open(LEDGER) as f:
            for ln in f:
                r = json.loads(ln)
                if r.get("stage", "").startswith(stage_prefix):
                    k = (r.get("stage"), r.get("model"))
                    a = out.setdefault(k, dict(calls=0, usd=0.0, in_tok=0, out_tok=0, cache_read=0, cache_write=0, secs=0.0))
                    a["calls"] += 1; a["usd"] += r.get("usd", 0); a["in_tok"] += r.get("in_tok", 0); a["out_tok"] += r.get("out_tok", 0)
                    a["cache_read"] += r.get("cache_read", 0); a["cache_write"] += r.get("cache_write", 0); a["secs"] += r.get("secs", 0)
    return out


def key_of(model, system, prompt):
    return hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()


def cached(model, system, prompt):
    p = os.path.join(CACHE, key_of(MODELS.get(model, model), system, prompt) + ".json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def call(model, system, prompt, stage, batch_id="", timeout=900, cap=None, use_cache=True, effort=None):
    """Returns dict(text, usd, cached, raw_meta). Raises RuntimeError on CLI failure or cap breach."""
    mid = MODELS.get(model, model)
    os.makedirs(CACHE, exist_ok=True); os.makedirs(os.path.dirname(LEDGER), exist_ok=True); os.makedirs(CWD, exist_ok=True)
    k = key_of(mid, system, prompt)
    cp = os.path.join(CACHE, k + ".json")
    if use_cache and os.path.exists(cp):
        with open(cp) as f:
            d = json.load(f)
        d["cached"] = True
        return d
    cap = float(os.environ.get("BB3_CAP_USD", "200")) if cap is None else cap
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)          # one claude process at a time (all batch-3 stages)
        s = spent()
        if s >= cap:
            raise RuntimeError(f"spend cap reached: ${s:.2f} >= ${cap:.2f}")
        args = ["claude", "-p", "--output-format", "json", "--model", mid, "--system-prompt", system, "--tools", "",
                "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence", "--setting-sources", "",
                "--exclude-dynamic-system-prompt-sections"]
        if effort:
            args += ["--effort", effort]
        env = {k2: v for k2, v in os.environ.items() if k2 not in ("CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "CLAUDE_ADDITIONAL_DIRECTORIES")}
        t0 = time.time()
        p = subprocess.run(args, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=CWD, env=env)
        secs = time.time() - t0
        try:
            d = json.loads(p.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"claude CLI rc={p.returncode} non-JSON output: {p.stdout[:300]!r} err={p.stderr[:300]!r}")
        mu = d.get("modelUsage") or {}
        usd = float(d.get("total_cost_usd") or 0.0)
        main = mu.get(mid, {})
        rec = dict(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), stage=stage, batch=batch_id, model=mid, models_used=sorted(mu.keys()), usd=usd,
                   in_tok=main.get("inputTokens", 0), out_tok=main.get("outputTokens", 0), cache_read=main.get("cacheReadInputTokens", 0),
                   cache_write=main.get("cacheCreationInputTokens", 0), secs=round(secs, 1), is_error=bool(d.get("is_error")), stop=d.get("stop_reason"),
                   prompt_chars=len(prompt), system_chars=len(system))
        with open(LEDGER, "a") as f:
            f.write(json.dumps(rec) + "\n")
        if d.get("is_error") or d.get("subtype") != "success":
            raise RuntimeError(f"claude error: {str(d.get('result'))[:300]}")
        out = dict(text=d.get("result") or "", usd=usd, cached=False, meta=rec)
        fd, tmp = tempfile.mkstemp(dir=CACHE)
        with os.fdopen(fd, "w") as f:
            json.dump(out, f)
        os.replace(tmp, cp)
        return out


def parse_json_array(txt):
    """Parse a model's list of JSON objects: a top-level array, or JSONL (one object per line), tolerating code fences and prose.
    Returns a list of dicts (non-dict elements dropped)."""
    arr = []
    try:
        a0 = _parse_array(txt)
        if isinstance(a0, list):
            arr = [x for x in a0 if isinstance(x, dict)]
    except (ValueError, json.JSONDecodeError):
        pass
    out = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if ln.startswith("["):
            ln = ln[1:].strip()
        ln = ln.rstrip(",").strip()
        if ln.endswith("]") and not ln.endswith("}]}") or ln.endswith("}]"):
            ln = ln[:-1].rstrip().rstrip(",")
        if ln.startswith("{") and ln.endswith("}"):
            try:
                o = json.loads(ln)
                if isinstance(o, dict):
                    out.append(o)
            except json.JSONDecodeError:
                continue
    best = out if len(out) > len(arr) else arr          # mixed outputs: "[{...}]" then JSONL lines
    if not best:
        raise ValueError("no JSON objects found")
    return best


def _parse_array(txt):
    t = txt.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    s = t.find("[")
    if s < 0:
        raise ValueError("no JSON array")
    depth, instr, esc = 0, False, False
    for i in range(s, len(t)):
        c = t[i]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return json.loads(t[s:i + 1])
    raise ValueError("unterminated JSON array")
