"""Minimal mock of brain contract v0.1 reserved verbs procedures.start / procedures.check and receipt verification
by action tools (handover/BRAIN-CONTRACT-v0.md §5, CT-23..26), plus the ADR-021 signed gate table.

semantics="as-written": exactly the contract text. start(procedure, task_id, action_class, brief_hash); checks are
    computed by the brain from the evidence ids given at check time; the receipt carries {run_id, principal, task_id,
    action_class, procedure, step results, expires}; the action tool verifies same principal, same task, allowed
    version, not expired, signature valid, single use.
semantics="bound": proposed fix (E-PM1 finding): start also takes the action's parameters; every check evaluates those
    parameters (evidence cannot substitute other objects); the receipt carries params_hash and the action tool
    verifies it against its own call. CT-27 distinguishes the two.
Mutants (for proving the conformance tests catch broken gates) are switched on via `mutant=`.
"""
import base64
import hashlib
import json
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

RUN_TTL = 1800
RECEIPT_TTL = 900


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def money(s):
    try:
        return round(float(str(s).replace("$", "").replace(",", "").split()[0]), 2)
    except (ValueError, IndexError):
        return None


def norm_acct(d):
    if not isinstance(d, dict):
        return None
    return (str(d.get("bsb", "")).replace(" ", "").replace("-", ""), str(d.get("account", d.get("account_number", ""))).replace(" ", ""))


def params_hash(action_class, params):
    p = dict(params or {})
    if action_class == "deletion":
        p = {"record_ids": sorted(p.get("record_ids") or [])}
    elif action_class == "payment":
        p = {"bill_id": p.get("bill_id"), "bsb": str(p.get("bsb", "")).replace(" ", "").replace("-", ""),
             "account_number": str(p.get("account_number", "")).replace(" ", ""), "amount": money(p.get("amount"))}
    elif action_class == "external_send":
        p = {"to": str(p.get("to", "")).strip().lower()}
    return hashlib.sha256(canon(p).encode()).hexdigest()


class Gate:
    def __init__(self, library, world, principal, session_task_id, business, semantics="as-written", clock=None,
                 mutant=None, verify_procedure_signature=None):
        self.lib = {f"{p['slug']}@{p['version']}": p for p in library["gated_procedures"]}
        self.table = library["gate_table"]
        self.recs = {r["id"]: r for r in world["records"]}
        self.ledger = world["ledger"]
        self.today = world["today"]
        self.principal = principal
        self.session_task = session_task_id
        self.business = business
        self.semantics = semantics
        self.clock = clock or (lambda: 0.0)
        self.mutant = mutant or set()
        self.verify_sig = verify_procedure_signature or (lambda p: True)
        self._key = Ed25519PrivateKey.generate()
        self.pub = self._key.public_key()
        self.runs = {}
        self.taps = {}
        self.used_receipts = set()
        self.paid_bills = set()
        self.events = []

    # ------------------------------------------------------------------ start
    def start(self, procedure, task_id, action_class, brief_hash=None, params=None, principal=None):
        principal = principal or self.principal
        proc = self.lib.get(str(procedure))
        allowed = self.table.get(action_class, [])
        if proc is None or str(procedure) not in allowed and "skip_table" not in self.mutant:
            return self._ev("start", {"refused": True, "reason": "procedure version not allowed for this action class in the signed gate table"})
        if not self.verify_sig(proc) and "skip_sig" not in self.mutant:
            return self._ev("start", {"refused": True, "reason": "procedure signature or body digest invalid"})
        if self.semantics == "bound" and params is None:
            return self._ev("start", {"refused": True, "reason": "action parameters required"})
        run_id = "run-" + secrets.token_hex(6)
        enforced = [s for s in proc["steps"] if s["guard"] == "enforced"]
        steps = []
        for s in enforced:
            sid = s["text"].split()[0]  # c1, c2 ...
            steps.append({"step_id": sid, "text": s["text"], "check_type": "human" if s["door"] == "one-way" else "deterministic",
                          "one_way": s["door"] == "one-way"})
        self.runs[run_id] = {"principal": principal, "task_id": task_id, "action_class": action_class, "procedure": str(procedure),
                             "started": self.clock(), "expires": self.clock() + RUN_TTL, "steps": {s["step_id"]: None for s in steps},
                             "brief_hash": brief_hash, "params": params, "receipt_issued": False}
        return self._ev("start", {"run_id": run_id, "procedure": str(procedure), "action_class": action_class,
                                  "enforced_steps": steps, "expires_in_s": RUN_TTL})

    # ------------------------------------------------------------------ check
    def check(self, run_id, step_id, evidence=None, principal=None):
        principal = principal or self.principal
        run = self.runs.get(run_id)
        if run is None or run["principal"] != principal:
            return self._ev("check", {"error": "not_found"})
        if self.clock() > run["expires"]:
            return self._ev("check", {"run_id": run_id, "step_id": step_id, "result": "failed", "reason": "run expired"})
        if step_id not in run["steps"]:
            return self._ev("check", {"run_id": run_id, "step_id": step_id, "result": "failed", "reason": "unknown step"})
        ev = dict(evidence or {}) if isinstance(evidence, dict) else {"raw": evidence}
        ignored = [k for k in ("result", "passed", "status", "outcome") if k in ev]
        if "trust_caller" in self.mutant and str(ev.get("result", ev.get("status", ""))).lower() in ("passed", "pass", "true"):
            res, why = "passed", "caller result accepted (MUTANT)"
        else:
            if self.semantics == "bound":
                ev = {**ev, **self._bound_evidence(run)}
            res, why = self._compute(run_id, run, step_id, ev)
        run["steps"][step_id] = res
        out = {"run_id": run_id, "step_id": step_id, "result": res, "reason": why}
        if ignored:
            out["note"] = "caller-supplied result ignored; the brain computes every check"
        if all(v == "passed" for v in run["steps"].values()) and not run["receipt_issued"]:
            out["receipt"] = self._issue(run_id, run)
            run["receipt_issued"] = True
        return self._ev("check", out)

    def _bound_evidence(self, run):
        p = run["params"] or {}
        if run["action_class"] == "payment":
            return {"bill_id": p.get("bill_id"), "pay_to": {"bsb": p.get("bsb"), "account": p.get("account_number")}}
        if run["action_class"] == "external_send":
            return {"to": p.get("to")}
        if run["action_class"] == "deletion":
            return {"record_ids": p.get("record_ids")}
        return {}

    def _compute(self, run_id, run, step_id, ev):
        ac = run["action_class"]
        proc = self.lib[run["procedure"]]
        step = next(s for s in proc["steps"] if s["text"].split()[0] == step_id)
        if step["door"] == "one-way":
            tap = ev.get("tap_event_id")
            t = self.taps.get(tap) if isinstance(tap, str) else None
            if t is None:
                return "needs_human", "a fresh owner tap for this run is required; text such as 'ok', silence or bulk approval does not count"
            if "accept_any_tap" not in self.mutant and (t["run_id"] != run_id or t["used"]):
                return "needs_human", "tap not issued for this run or already used"
            t["used"] = True
            return "passed", "owner tapped approve"
        if ac == "payment":
            bill = self.recs.get(ev.get("bill_id") or "")
            if not bill or bill["kind"] != "bill":
                return "failed", "evidence must name the bill (bill_id)"
            f = bill["fields"]
            if step_id == "c1":
                po = self.recs.get(f.get("purchase_order") or "")
                ok = po is not None and money(po["fields"].get("total")) == money(f.get("total"))
                return ("passed", "bill total equals purchase order total") if ok else ("failed", "bill total does not equal the purchase order total")
            if step_id == "c2":
                sup = self.recs.get(f.get("supplier") or "")
                on_file = norm_acct(sup["fields"].get("bank_on_file")) if sup else None
                on_bill = norm_acct(f.get("bank_on_invoice"))
                ok = on_file is not None and on_file == on_bill
                if self.semantics == "bound":
                    ok = ok and norm_acct(ev.get("pay_to")) == on_file
                return ("passed", "bank details match the supplier's details on file") if ok else ("failed", "bank details differ from the supplier's details on file")
            if step_id == "c3":
                paid = bill["id"] in self.paid_bills or any(r.get("ref") == f.get("invoice_no") and r.get("status") == "paid"
                                                            for r in self.ledger.get(f.get("supplier"), []))
                return ("failed", "a payment for this bill already exists") if paid else ("passed", "no payment recorded for this bill")
        if ac == "external_send":
            to = str(ev.get("to") or "").strip().lower()
            if step_id == "c1":
                contact = self.recs.get(ev.get("contact_id") or "")
                on_file = {str(r["fields"].get("email", "")).lower() for r in self.recs.values()
                           if r["kind"] in ("customer", "supplier", "contact") and r["business"] == self.business}
                if self.semantics == "as-written" and contact is not None:
                    ok = to == str(contact["fields"].get("email", "")).lower()
                else:
                    ok = bool(to) and to in on_file
                return ("passed", "recipient is a contact email on file") if ok else ("failed", "recipient address is not the email on file")
        if ac == "deletion":
            ids = ev.get("record_ids")
            if not isinstance(ids, list) or not ids:
                return "failed", "evidence must list record_ids"
            recs = [self.recs.get(i) for i in ids]
            if any(r is None for r in recs):
                return "failed", "unknown record id"
            if step_id == "c1":
                ok = all(r["business"] == self.business for r in recs)
                return ("passed", "all records belong to this business") if ok else ("failed", "some records belong to another space")
            if step_id == "c2":
                held = [r["id"] for r in recs if r["fields"].get("legal_hold") or (r["fields"].get("retention_until") or "") > self.today]
                return ("failed", f"records under retention or legal hold: {held}") if held else ("passed", "no record under hold")
        return "failed", "unknown check"

    # ------------------------------------------------------------------ receipts
    def _issue(self, run_id, run):
        body = {"run_id": run_id, "principal": run["principal"], "task_id": run["task_id"], "action_class": run["action_class"],
                "procedure": run["procedure"], "step_results": dict(run["steps"]), "expires": self.clock() + RECEIPT_TTL,
                "nonce": secrets.token_hex(4)}
        if self.semantics == "bound":
            body["params_hash"] = params_hash(run["action_class"], run["params"])
        raw = canon(body).encode()
        sig = self._key.sign(raw)
        return "rcpt." + base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + sig.hex()

    def verify_receipt(self, receipt, action_class, params, principal=None, task_id=None):
        principal = principal or self.principal
        task_id = task_id or self.session_task
        if not isinstance(receipt, str) or not receipt.startswith("rcpt.") or receipt.count(".") != 2:
            return False, "a valid procedure receipt is required for this action"
        _, b64, sig = receipt.split(".")
        try:
            raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
            if "skip_receipt_sig" not in self.mutant:
                self.pub.verify(bytes.fromhex(sig), raw)
            body = json.loads(raw)
        except (InvalidSignature, ValueError, json.JSONDecodeError):
            return False, "receipt signature invalid"
        if body.get("principal") != principal:
            return False, "receipt issued to another principal"
        if body.get("task_id") != task_id and "skip_task" not in self.mutant:
            return False, "receipt issued for another task"
        if body.get("action_class") != action_class:
            return False, "receipt is for another action class"
        if body.get("procedure") not in self.table.get(action_class, []):
            return False, "procedure version not allowed by the gate table"
        if self.clock() > body.get("expires", 0) and "skip_expiry" not in self.mutant:
            return False, "receipt expired"
        if not all(v == "passed" for v in body.get("step_results", {}).values()):
            return False, "not every enforced step passed"
        key = body.get("run_id") + body.get("nonce", "")
        if key in self.used_receipts and "allow_reuse" not in self.mutant:
            return False, "receipt already used"
        if self.semantics == "bound" and body.get("params_hash") != params_hash(action_class, params):
            return False, "receipt does not match this action's parameters"
        self.used_receipts.add(key)
        return True, "receipt valid"

    def tap(self, run_id, summary=""):
        t = "tap-" + secrets.token_hex(5)
        self.taps[t] = {"run_id": run_id, "summary": summary, "used": False, "at": self.clock()}
        return t

    def _ev(self, kind, out):
        self.events.append({"kind": kind, "out": {k: v for k, v in out.items() if k != "receipt"}, "receipt": "receipt" in out})
        return out
