#!/usr/bin/env python3
"""Reference PreToolUse dispatch gate (R9 / DISPATCH-POLICY-DRAFT §6). Deploy as a MANAGED command hook with
"onFailure": "block" on matcher "Agent|Task|Workflow|mcp__brain__.*" and on "*" for in-subagent effort checks.

Reads the hook JSON on stdin. Decides with the signed dispatch policy (never memory) and a short-lived signed ticket
issued by the brain's dispatch_profile tool. Fails closed: any error -> deny.

Env: DISPATCH_POLICY (policy.json), DISPATCH_POLICY_SIG (base64 Ed25519 sig over the policy bytes),
     DISPATCH_POLICY_PUB / DISPATCH_TICKET_PUB (raw 32-byte Ed25519 public keys, base64), DISPATCH_NOW (tests only).
"""
import base64
import hashlib
import json
import os
import re
import sys
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

TIER = {"haiku": 1, "sonnet": 2, "opus": 3, "fable": 4}
EFFORT = {"low": 1, "medium": 2, "high": 3, "xhigh": 4, "max": 5}
TICKET_RE = re.compile(r"^DISPATCH-TICKET: ([A-Za-z0-9_\-]+)\.([A-Za-z0-9_\-]+)\s*$", re.M)


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def out(decision, reason, updated=None):
    o = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                "permissionDecisionReason": reason}}
    if updated is not None:
        o["hookSpecificOutput"]["updatedInput"] = updated
    print(json.dumps(o))
    sys.exit(0)


def load_policy():
    raw = open(os.environ["DISPATCH_POLICY"], "rb").read()
    sig = base64.b64decode(open(os.environ["DISPATCH_POLICY_SIG"]).read().strip())
    Ed25519PublicKey.from_public_bytes(base64.b64decode(os.environ["DISPATCH_POLICY_PUB"])).verify(sig, raw)
    pol = json.loads(raw)
    floor_file = os.environ.get("DISPATCH_MIN_VERSION_FILE")  # anti-rollback: last version seen
    if floor_file and os.path.exists(floor_file) and pol["version"] < int(open(floor_file).read().strip()):
        raise ValueError("policy rollback")
    return pol


def verify_ticket(prompt, pol, now):
    m = TICKET_RE.search(prompt or "")
    if not m:
        return None, "no dispatch ticket in the prompt (call dispatch_profile first)"
    payload, sig = m.group(1), m.group(2)
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(os.environ["DISPATCH_TICKET_PUB"])).verify(
            b64d(sig), payload.encode())
    except Exception:
        return None, "ticket signature invalid"
    t = json.loads(b64d(payload))
    if t.get("exp", 0) < now:
        return None, "ticket expired"
    if t.get("policy_version") != pol["version"]:
        return None, "ticket issued under a different policy version"
    brief = TICKET_RE.sub("", prompt).strip()
    if t.get("task_sha256") != hashlib.sha256(brief.encode()).hexdigest():
        return None, "ticket was issued for a different task brief"
    return t, None


def main():
    now = int(os.environ.get("DISPATCH_NOW") or time.time())
    try:
        e = json.load(sys.stdin)
        pol = load_policy()
    except Exception as exc:  # fail closed (V9)
        out("deny", f"dispatch policy unavailable or unverified: {type(exc).__name__}")
    tool, ti = e.get("tool_name", ""), e.get("tool_input") or {}
    classes = pol["classes"]

    # (1) inside a dispatched subagent: effort floor and protected-tool scope (V13, V1)
    agent_type = e.get("agent_type")
    if agent_type and agent_type in pol["agent_types"]:
        cls = classes[pol["agent_types"][agent_type]]
        lvl = (e.get("effort") or {}).get("level")
        if lvl and EFFORT[lvl] < EFFORT[cls["effort_floor"]]:
            out("deny", f"effort {lvl} is below the policy floor {cls['effort_floor']} for {agent_type}")
        if tool.startswith("mcp__brain__") and tool.split("__")[-1] in pol["protected_tools"] and not cls.get("protected_ok"):
            out("deny", f"{agent_type} may not call protected tool {tool}")

    if tool in ("Agent", "Task"):
        t, why = verify_ticket(ti.get("prompt"), pol, now)
        if t is None:
            out("deny", why)
        cls_name = t["class"]
        cls = classes.get(cls_name)
        if cls is None:
            out("deny", f"unknown task class {cls_name}")
        # independent re-check of standing VETOs (do not trust the ticket alone)
        if TIER[t["model"]] < TIER[cls["model_floor"]]:
            out("deny", f"ticket model {t['model']} below the class floor {cls['model_floor']} (V1/V3)")
        if cls_name in pol["protected_classes"] and TIER[t["model"]] < TIER["opus"]:
            out("deny", "protected-area class below the strong tier (V1)")
        if pol["agent_types"].get(t["agent_type"]) != cls_name:
            out("deny", f"agent type {t['agent_type']} is not the policy's agent for class {cls_name}")
        if ti.get("subagent_type") and ti["subagent_type"] != t["agent_type"]:
            out("deny", f"subagent_type {ti['subagent_type']} does not match the ticket ({t['agent_type']})")
        if t.get("maker_seat") and t.get("maker_seat") == t.get("seat"):
            out("deny", "checker seat equals maker seat (V2)")
        if ti.get("isolation") == "remote" and not cls.get("remote_ok"):
            out("deny", "remote (cloud) isolation not allowed for this class / egress (V7)")
        req = ti.get("model")
        if req and TIER.get(req, 0) > TIER[t["model"]]:
            out("deny", f"requested model {req} above the ticket ({t['model']}); budget VETO (V6)")
        # The Agent tool's per-invocation `model` accepts aliases only and outranks the definition's pinned full
        # model ID, and per-invocation `effort` outranks the definition's effort: strip both so the policy-generated
        # agent definition (pinned ID + effort) governs. Escalation = a different agent type, never an override.
        updated = {k: v for k, v in ti.items() if k not in ("model", "effort")}
        updated["subagent_type"] = t["agent_type"]
        out("allow", f"dispatch ok: class {cls_name}, {t['model']}/{t['effort']}", updated)

    if tool == "Workflow":
        if ti.get("script"):
            out("deny", "inline workflow scripts are not allowed; use a policy-generated named workflow")
        name = ti.get("name") or os.path.splitext(os.path.basename(ti.get("scriptPath", "")))[0]
        wf = pol["workflows"].get(name)
        if not wf:
            out("deny", f"workflow {name!r} is not in the dispatch policy")
        path = ti.get("scriptPath") or os.path.join(e.get("cwd", "."), ".claude", "workflows", name + ".js")
        try:
            h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        except OSError:
            out("deny", f"workflow script {path} not readable")
        if h != wf["sha256"]:
            out("deny", f"workflow {name} differs from the policy-generated version")
        out("allow", f"workflow {name} matches policy hash")

    print(json.dumps({}))  # other tools: no opinion


if __name__ == "__main__":
    main()
