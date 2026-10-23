#!/usr/bin/env python3
"""Build E-PM1 materials: signed procedure library (sizes 10/40/120), fixture world, tasks, gated tasks; lint.

usage: python3 -I build.py   (run from anywhere; writes into /home/claude/epm1/materials/)
Outputs: library.json, world.json, tasks.json, gated.json, lint.txt, keys/ (synthetic ed25519 key, generated once)
"""
import hashlib
import json
import os
import re as _re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from library_core import CORE
from library_extra import EXTRA
from gated import GATED_PROCS, PROMPT_PROCS, GATE_TABLE, ACTION_TOOL, GATED_RECORDS, PRESSURE, GATED_TASKS
from world_common import COMMON, TODAY
from tasks_a import TASKS_A
from tasks_b import TASKS_B, NONE_TASKS, LEDGER


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def key():
    os.makedirs(f"{HERE}/keys", exist_ok=True)
    p = f"{HERE}/keys/signing_key.pem"
    if not os.path.exists(p):
        k = Ed25519PrivateKey.generate()
        open(p, "wb").write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                            serialization.NoEncryption()))
    k = serialization.load_pem_private_key(open(p, "rb").read(), None)
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return k, pub


BACKGROUNDS = json.load(open(f"{HERE}/backgrounds.json")) if os.path.exists(f"{HERE}/backgrounds.json") else {}


def render_body(p):
    lines = [f"# {p['title']}", f"When to use: {p['when']}", ""]
    bg = BACKGROUNDS.get(p["slug"]) if p.get("status", "active") == "active" else None
    if bg:
        lines += [f"Background: {bg}", ""]
    if p.get("preface"):
        lines += [f"How to run it: {p['preface']}", ""]
    lines += ["Steps"]
    for i, (g, d, t) in enumerate(p["steps"], 1):
        lab = g + (", one-way: needs the owner" if d == "one-way" else "")
        lines.append(f"{i}. [{lab}] {t}")
    if p.get("done"):
        lines += ["", f"Done when: {p['done']}"]
    if p.get("never"):
        lines += ["", "Never:"] + [f"- {n}" for n in p["never"]]
    if p.get("notes"):
        lines += ["", "Notes:"] + [f"- {n}" for n in p["notes"]]
    return "\n".join(lines)


def sign_record(p, k, pub):
    body = render_body(p)
    digest = "sha256:" + hashlib.sha256(body.encode()).hexdigest()
    pid = "proc_" + hashlib.sha256(p["slug"].encode()).hexdigest()[:10]
    rec = {
        "procedure_id": pid, "slug": p["slug"], "version": p["version"], "status": p.get("status", "active"),
        "space_id": "template" if p["scope"] == "general" else "grp-tallisreed", "audience": p["audience"],
        "task_classes": [p["task_class"]], "scopes": [p["scope"]], "client_egress_min": "X2",
        "when_to_use": p["when"], "title": p["title"], "example_requests": p.get("examples", []),
        "triggers": p.get("triggers", []), "tag": p["tag"],
        "steps": [{"id": f"s{i}", "text": t, "guard": "enforced" if g == "enforced" else "advisory",
                   "door": d} for i, (g, d, t) in enumerate(p["steps"], 1)],
        "body": body, "body_digest": digest, "owner_principal": "user:owner", "approved_by": "user:owner",
        "approved_at": "2026-10-20T09:00:00+10:00", "review_by": "2027-04-20", "provenance": {"source": "synthetic E-PM1", "trust": "T0"},
        "gold": p.get("gold", False), "core10": p.get("core10", False), "gated_action": p.get("gated_action"),
        "attribution": "Generic method rewritten in our own words (patterns from R8 §5.1); no vendor text copied." if p["scope"] == "general" else None,
    }
    signed = {f: rec[f] for f in ("procedure_id", "slug", "version", "body_digest", "scopes", "task_classes", "audience", "approved_by", "status")}
    rec["signature"] = "ed25519:" + k.sign(canon(signed).encode()).hex()
    rec["signer_public_key"] = pub
    return rec


def toks(s):
    return _re.findall(r"[a-z0-9]+", s.lower())


STOP = set("the a an and or of to in for on with is are be this that it as by from at use when you your i my me we our "
           "us can get has have what do does need".split())


def stem(w):
    for suf in ("ments", "ment", "ings", "ing", "ions", "ion", "es", "s", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def lint_masked(task, proc):
    """Masked request must not contain a trigger phrase, the slug words in sequence, or >=2 title content words."""
    req = " ".join(stem(w) for w in toks(task["masked"]))
    issues = []
    for trig in proc.get("triggers", []):
        t = " ".join(stem(w) for w in toks(trig))
        if t and t in req:
            issues.append(f"trigger '{trig}'")
    slug = " ".join(stem(w) for w in proc["slug"].split("-"))
    if slug in req:
        issues.append("slug sequence")
    title_words = {stem(w) for w in toks(proc["title"]) if w not in STOP and len(w) > 2}
    hit = title_words & set(req.split())
    if len(hit) >= 2:
        issues.append(f"title words {sorted(hit)}")
    return issues, sorted(hit)


def main():
    k, pub = key()
    lib = [sign_record(p, k, pub) for p in CORE + EXTRA]
    slugs = [r["slug"] for r in lib]
    assert len(set(slugs)) == len(slugs), "duplicate slugs"
    tags = [r["tag"] for r in lib]
    assert len(set(tags)) == len(tags), "duplicate tags"
    gated = [sign_record(p, k, pub) for p in GATED_PROCS]
    prompt_variants = [sign_record(p, k, pub) for p in PROMPT_PROCS]
    core = {r["slug"] for r in lib[:40]}
    core10 = [r["slug"] for r in lib if r["core10"]]
    sizes = {"10": core10, "40": [r["slug"] for r in lib[:40]], "120": slugs}
    scopes = sorted({r["scopes"][0] for r in lib})
    # declared mappings (versioned data, ADR-012): each scope declares <=5 procedures
    declared = {}
    for size, members in sizes.items():
        declared[size] = {}
        for sc in scopes:
            decl = [s for s in members if s in core and next(r for r in lib if r["slug"] == s)["scopes"][0] == sc][:5]
            declared[size][sc] = decl
    library = {"version": "epm1-lib-1", "signer_public_key": pub, "procedures": lib, "gated_procedures": gated, "prompt_procedures": prompt_variants,
               "gate_table": GATE_TABLE, "action_tool": ACTION_TOOL, "sizes": sizes, "declared": declared}

    tasks = TASKS_A + TASKS_B + NONE_TASKS
    ids = [t["id"] for t in tasks]
    assert len(set(ids)) == len(ids)
    assert len(tasks) == 60, len(tasks)
    gold_counts = {}
    for t in tasks:
        if t["gold"]:
            assert t["gold"] in core, t["gold"]
            gold_counts[t["gold"]] = gold_counts.get(t["gold"], 0) + 1
            pr = next(r for r in lib if r["slug"] == t["gold"])
            assert pr["scopes"][0] == t["scope"], (t["id"], pr["scopes"], t["scope"])
            assert any(s["distinctive"] for s in t["steps"]), t["id"]
        t["ladder"] = (t["gold"] is None) or (t["gold"] in core10)
    assert all(v == 2 for v in gold_counts.values()) and len(gold_counts) == 25, gold_counts
    assert sum(t["ladder"] for t in tasks) == 30

    # world: common + task records + gated records; ids unique
    recs = list(COMMON)
    for t in tasks:
        recs += t["records"]
    recs += GATED_RECORDS
    rid = [r["id"] for r in recs]
    dup = {x for x in rid if rid.count(x) > 1}
    assert not dup, dup
    world = {"today": TODAY, "records": recs, "ledger": LEDGER}
    for t in tasks:
        t.pop("records")

    gtasks = []
    for g in GATED_TASKS:
        for pk, line in PRESSURE[g["action"]].items():
            gtasks.append({**g, "id": f"{g['id']}-{pk}", "pressure": pk, "request": g["base"] + " " + line})

    # lint
    out = []
    bad = 0
    for t in tasks:
        if not t["gold"]:
            continue
        pr = next(r for r in lib if r["slug"] == t["gold"])
        issues, hit = lint_masked(t, pr)
        vt = " ".join(stem(w) for w in toks(t["verbatim"]))
        vtrig = any(" ".join(stem(w) for w in toks(tr)) in vt for tr in pr["triggers"])
        out.append(f"{t['id']:5s} {t['gold']:34s} masked_issues={issues or '-'} title_overlap={hit or '-'} verbatim_has_trigger={vtrig}")
        bad += bool(issues)
    # example requests must not share a 4-gram with any task request (leak check)
    def grams(s, n=4):
        w = toks(s)
        return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}
    leak = []
    for r in lib:
        for ex in r["example_requests"]:
            for t in tasks:
                g = grams(ex) & grams(t["masked"])
                if g:
                    leak.append((r["slug"], t["id"], sorted(g)))
    out.append(f"\nmasked lint failures: {bad}")
    out.append(f"example-request 4-gram leaks into task requests: {len(leak)} {leak[:5]}")
    # sizes and token estimates (chars/4)
    def est(s):
        return round(len(s) / 4)
    for size, members in sizes.items():
        b = sum(est(next(r for r in lib if r["slug"] == s)["body"]) for s in members)
        out.append(f"library size {size}: {len(members)} procedures, ~{b} body tokens (chars/4)")
    for sc in scopes:
        out.append(f"declared[40][{sc}] = {declared['40'][sc]}")
    open(f"{HERE}/lint.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out[-14:]))

    json.dump(library, open(f"{HERE}/library.json", "w"), indent=1, ensure_ascii=False)
    json.dump(world, open(f"{HERE}/world.json", "w"), indent=1, ensure_ascii=False)
    json.dump(tasks, open(f"{HERE}/tasks.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"tasks": gtasks, "pressure": PRESSURE}, open(f"{HERE}/gated.json", "w"), indent=1, ensure_ascii=False)
    print(f"library {len(lib)} (+{len(gated)} gated), world {len(recs)} records, tasks {len(tasks)}, gated tasks {len(gtasks)}")
    if bad:
        sys.exit("masked-request lint failed")


if __name__ == "__main__":
    main()
