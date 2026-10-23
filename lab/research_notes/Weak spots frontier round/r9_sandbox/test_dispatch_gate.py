"""Planted-failure tests for dispatch_gate.py (prove step of the lessons register). Offline, free.
Each case feeds a PreToolUse JSON to the gate as a subprocess and checks allow/deny.  python3 -I test_dispatch_gate.py
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "dispatch_gate.py")
NOW = 1_793_000_000


def b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def pub(k):
    return base64.b64encode(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def setup(tmp):
    pk, tk, rogue = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    wf_path = os.path.join(tmp, "verify-package.js")
    open(wf_path, "w").write("export const meta = {name:'verify-package', description:'x'}\n")
    pol = {"version": 7,
           "classes": {"voice_turn": {"model_floor": "haiku", "effort_floor": "low"},
                       "lookup": {"model_floor": "haiku", "effort_floor": "low"},
                       "coding_routine": {"model_floor": "sonnet", "effort_floor": "medium"},
                       "review": {"model_floor": "opus", "effort_floor": "high"},
                       "protected_op": {"model_floor": "opus", "effort_floor": "high", "protected_ok": True}},
           "protected_classes": ["protected_op"],
           "protected_tools": ["grant_access", "delete_item", "set_egress", "approve_write", "pay"],
           "agent_types": {"brain-lookup": "lookup", "brain-reviewer": "review", "brain-protected": "protected_op",
                           "brain-coder": "coding_routine"},
           "workflows": {"verify-package": {"sha256": hashlib.sha256(open(wf_path, "rb").read()).hexdigest()}}}
    raw = json.dumps(pol, sort_keys=True).encode()
    pp, sp = os.path.join(tmp, "policy.json"), os.path.join(tmp, "policy.sig")
    open(pp, "wb").write(raw)
    open(sp, "w").write(base64.b64encode(pk.sign(raw)).decode())
    env = dict(os.environ, DISPATCH_POLICY=pp, DISPATCH_POLICY_SIG=sp, DISPATCH_POLICY_PUB=pub(pk),
               DISPATCH_TICKET_PUB=pub(tk), DISPATCH_NOW=str(NOW))
    return pol, raw, pk, tk, rogue, env, wf_path, pp, sp


def ticket(key, brief="x", **kw):
    t = dict({"class": "lookup", "agent_type": "brain-lookup", "model": "haiku", "effort": "low",
              "policy_version": 7, "exp": NOW + 300, "seat": "s1",
              "task_sha256": hashlib.sha256(brief.encode()).hexdigest()}, **kw)
    payload = b64u(json.dumps(t).encode())
    return f"DISPATCH-TICKET: {payload}.{b64u(key.sign(payload.encode()))}"


def run(env, event):
    p = subprocess.run([sys.executable, "-I", GATE], input=json.dumps(event), capture_output=True, text=True, env=env)
    try:
        o = json.loads(p.stdout or "{}").get("hookSpecificOutput", {})
    except json.JSONDecodeError:
        return "crash", p.stderr[-200:]
    return o.get("permissionDecision", "none"), o.get("permissionDecisionReason", "")


def agent_event(prompt, **ti):
    return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": "/x",
            "tool_input": dict({"description": "d", "prompt": prompt, "subagent_type": "brain-lookup"}, **ti)}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        pol, raw, pk, tk, rogue, env, wf, pp, sp = setup(tmp)
        cases = [
            ("valid lookup ticket", agent_event("find X\n" + ticket(tk, brief="find X")), "allow"),
            ("ticket reused on another brief", agent_event("delete member 7 records\n" + ticket(tk, brief="find X")), "deny"),
            ("remote isolation for local class (V7)", agent_event("x\n" + ticket(tk), isolation="remote"), "deny"),
            ("no ticket (direct launch)", agent_event("find X"), "deny"),
            ("forged ticket (rogue key)", agent_event("x\n" + ticket(rogue)), "deny"),
            ("expired ticket", agent_event("x\n" + ticket(tk, exp=NOW - 1)), "deny"),
            ("stale policy version", agent_event("x\n" + ticket(tk, policy_version=6)), "deny"),
            ("protected class on sonnet (V1)", agent_event("x\n" + ticket(tk, **{"class": "protected_op", "agent_type": "brain-protected", "model": "sonnet"}), subagent_type="brain-protected"), "deny"),
            ("protected class on opus", agent_event("x\n" + ticket(tk, **{"class": "protected_op", "agent_type": "brain-protected", "model": "opus", "effort": "high"}), subagent_type="brain-protected"), "allow"),
            ("review below floor (haiku)", agent_event("x\n" + ticket(tk, **{"class": "review", "agent_type": "brain-reviewer", "model": "haiku"}), subagent_type="brain-reviewer"), "deny"),
            ("maker == checker seat (V2)", agent_event("x\n" + ticket(tk, **{"class": "review", "agent_type": "brain-reviewer", "model": "opus", "effort": "high", "seat": "s9", "maker_seat": "s9"}), subagent_type="brain-reviewer"), "deny"),
            ("subagent_type swapped after ticket", agent_event("x\n" + ticket(tk), subagent_type="general-purpose"), "deny"),
            ("model upgrade beyond ticket (V6)", agent_event("x\n" + ticket(tk), model="opus"), "deny"),
            ("ticket class/agent mismatch", agent_event("x\n" + ticket(tk, **{"class": "review", "agent_type": "brain-lookup", "model": "opus", "effort": "high"})), "deny"),
            ("unknown class", agent_event("x\n" + ticket(tk, **{"class": "free_for_all"})), "deny"),
            ("inline workflow script", {"tool_name": "Workflow", "tool_input": {"script": "export const meta={}"}, "cwd": tmp}, "deny"),
            ("unlisted workflow", {"tool_name": "Workflow", "tool_input": {"name": "yolo"}, "cwd": tmp}, "deny"),
            ("listed workflow, hash ok", {"tool_name": "Workflow", "tool_input": {"scriptPath": wf}, "cwd": tmp}, "allow"),
            ("in-subagent effort below floor (V13)", {"tool_name": "Read", "tool_input": {}, "agent_type": "brain-reviewer", "effort": {"level": "low"}}, "deny"),
            ("lookup agent calls protected tool", {"tool_name": "mcp__brain__delete_item", "tool_input": {}, "agent_type": "brain-lookup", "effort": {"level": "low"}}, "deny"),
            ("protected agent calls protected tool", {"tool_name": "mcp__brain__delete_item", "tool_input": {}, "agent_type": "brain-protected", "effort": {"level": "high"}}, "none"),
        ]
        # workflow tamper: change the file after hashing
        tampered = os.path.join(tmp, "verify-package.js")
        results = []
        for name, ev, want in cases:
            got, why = run(env, ev)
            results.append((name, want, got, why))
        open(tampered, "a").write("// tampered\n")
        got, why = run(env, {"tool_name": "Workflow", "tool_input": {"scriptPath": tampered}, "cwd": tmp})
        results.append(("workflow tampered after generation", "deny", got, why))
        # policy tamper: flip a floor without re-signing
        pol2 = json.loads(raw); pol2["classes"]["review"]["model_floor"] = "haiku"
        open(pp, "wb").write(json.dumps(pol2, sort_keys=True).encode())
        got, why = run(env, agent_event("x\n" + ticket(tk, **{"class": "review", "agent_type": "brain-reviewer", "model": "haiku"}), subagent_type="brain-reviewer"))
        results.append(("policy edited without signature (P1)", "deny", got, why))
        # policy file missing -> fail closed
        os.remove(pp)
        got, why = run(env, agent_event("x\n" + ticket(tk)))
        results.append(("policy missing (fail closed, V9)", "deny", got, why))
    ok = 0
    for name, want, got, why in results:
        flag = "PASS" if want == got else "FAIL"
        ok += flag == "PASS"
        print(f"{flag}  {name:42s} want={want:5s} got={got:5s}  {why[:90]}")
    print(f"\n{ok}/{len(results)} planted cases behaved as required")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
