"""Free dry run for batch 3 (no LLM): every validator and scorer must PASS a gold reference and FAIL planted broken solutions.

    python -m bb.dryrun3 --seed 1      -> results_v03/dryrun_s1.json (exit 1 on any failed check)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter

from .common import ROOT
from . import gate3
from .pipe3 import Brain3, Gate, World3

OUT = os.path.join(ROOT, "results_v03")


def reference_raw(w):
    """What a perfect gate would return, in the LLM's output format."""
    raw = {}
    for iid, g in w.gold.items():
        it = w.by_id[iid]
        if it.get("connector") or it.get("media"):
            continue
        text = it["text"]
        rr, al = [], []
        for r in g["records"]:
            T = gate3.GOLD_T.get(r["t"])
            if r["t"] == "fact" and r.get("a"):
                rr.append(dict(t="fact", e=r["e"][0], a=r["a"], v=r["v"], q=text))
            elif r["t"] == "alias":
                al.append(dict(p=r["v"], e=r["e"][0]))
            elif T and T != "fact":
                rr.append(dict(t=T, e=r.get("e", []), q=text))
        raw[iid] = dict(id=iid, e=list(g["entities"]), r=rr, al=al, k=["topic words"])
    return raw


def broken_raw(w, ref, R):
    """Plant one error per chosen record. Every planted error must be rejected by the validators."""
    bad = json.loads(json.dumps(ref))
    planted = Counter()
    facts = [(iid, j) for iid, o in bad.items() for j, r in enumerate(o["r"]) if r["t"] == "fact"]
    R.shuffle(facts)
    other_space_ent = {}
    for e in w.entities.values():
        for sp in e.get("spaces", []):
            other_space_ent.setdefault(sp, set()).add(e["id"])
    for n, (iid, j) in enumerate(facts[:400]):
        r = bad[iid]["r"][j]
        it = w.by_id[iid]
        kind = n % 4
        if kind == 0:                                   # invented value (not in the item)
            if not re.search(r"\d", r["v"]):
                r["v"] = r["v"] + " plus 7 more"
            r["v"] = re.sub(r"\d", lambda m: str((int(m.group()) + 3) % 10), r["v"], count=1)
            if gate3.value_in(r["v"], it["text"]):
                continue
            planted["invented_value"] += 1; r["_planted"] = "invented_value"
        elif kind == 1:                                 # paraphrased (non-verbatim) quote
            words = r["q"].split()
            if len(words) < 4:
                continue
            r["q"] = " ".join(words[1:] + words[:1]) + " (paraphrased)"
            planted["paraphrased_quote"] += 1; r["_planted"] = "paraphrased_quote"
        elif kind == 2:                                 # entity from a space the item is not in
            cand = [e for e in w.entities if it["space"] not in w.entities[e].get("spaces", []) and not (it["space"].endswith("/account"))]
            r["e"] = R.choice(sorted(cand))
            planted["foreign_entity"] += 1; r["_planted"] = "foreign_entity"
        else:                                           # attribute not in the schema for the entity kind
            r["a"] = "made_up_attribute"
            planted["bad_attribute"] += 1; r["_planted"] = "bad_attribute"
    return bad, planted


def main(seed):
    w = World3(seed)
    R = random.Random(seed)
    checks, res = [], {}
    ref = reference_raw(w)
    L, Rr, A, E, st = gate3.validate(w, ref)
    n_fact_ref = sum(1 for o in ref.values() for r in o["r"] if r["t"] == "fact")
    kept = st.get("fact_kept", 0)
    res["reference"] = dict(stats=st, facts=n_fact_ref, kept=kept)
    checks.append(("validators keep >= 97% of reference facts", kept >= 0.97 * n_fact_ref, f"{kept}/{n_fact_ref}"))
    nrec = sum(1 for o in ref.values() for r in o["r"] if r["t"] != "fact")
    checks.append(("validators keep >= 99% of reference typed records", st.get("rec_kept", 0) >= 0.99 * nrec, f"{st.get('rec_kept', 0)}/{nrec}"))
    q = gate3.quality(w, L, Rr)
    res["reference_quality"] = q
    checks.append(("reference link precision/recall >= 0.99", q["link_precision"] >= 0.99 and q["link_recall"] >= 0.99, f"P {q['link_precision']:.3f} R {q['link_recall']:.3f}"))
    checks.append(("reference keyed-fact recall >= 0.97", q["keyed_fact_recall"] >= 0.97, f"{q['keyed_fact_recall']:.3f}"))
    bad, planted = broken_raw(w, ref, R)
    Lb, Rb, Ab, Eb, stb = gate3.validate(w, bad)
    survived = Counter()
    for iid, o in bad.items():
        for r in o["r"]:
            if r.get("_planted"):
                if any(x["t"] == "fact" and x.get("a") == r.get("a") and x["e"] == [r["e"]] and x["v"] == r["v"] for x in Rb.get(iid, [])):
                    survived[r["_planted"]] += 1
    res["broken"] = dict(planted=dict(planted), survived=dict(survived), stats=stb)
    checks.append(("every planted extraction error rejected", sum(survived.values()) == 0 and sum(planted.values()) >= 200, f"planted {dict(planted)} survived {dict(survived)}"))
    # scorer: gold context passes, context missing one vital item fails, wrong-value card does not credit
    b = Brain3(w, Gate.gold(w), embed=False)
    t = next(t for t in w.tasks if t["cls"] == "decision_support" and len(t["vital"]) >= 3)
    ctx = [b.ix.pos[i] for i in t["required"]]
    checks.append(("scorer passes the exact required set", b.score(t, ctx)["v@10"] and b.score(t, ctx)["a@10"], ""))
    ctx2 = [b.ix.pos[i] for i in t["required"] if i != t["vital"][0]]
    checks.append(("scorer fails a context missing one vital item", not b.score(t, ctx2)["v@10"], ""))
    ctx3 = [b.ix.pos[i] for i in t["vital"]]
    checks.append(("CR_vital passes without helpful items; CR_all fails if helpful exist", b.score(t, ctx3)["v@10"] and (not b.score(t, ctx3)["a@10"] or not t["helpful"]), ""))
    # card credit only when the value is correct
    store_bad = Gate("bad", {}, {iid: [dict(t="fact", e=[r["e"][0]], a=r["a"], v="999999 wrong", s="")] for iid, g in w.gold.items() if g.get("extract_only")
                                     for r in g["records"] if r["t"] == "fact" and r.get("a")})
    bb = Brain3(w, store_bad, embed=False)
    credited_wrong = sum(len(v) for k, v in bb.card_cover.items() if any(w.gold.get(s, {}).get("extract_only") for s in v))
    checks.append(("cards never credit an item whose value was extracted wrongly", credited_wrong == 0, f"{credited_wrong}"))
    # access: no-grant identity sees nothing; owner sees no member health space; expired coach share not visible
    vis_ng = w.visible("nogrant")
    checks.append(("no-grant credential sees nothing", len(vis_ng) == 0, ""))
    vd = w.visible("dane")
    checks.append(("owner has no standing access to member health spaces", not any(s.startswith("member/") and not s.endswith("/account") for s in vd), ""))
    exp = [g for g in w.grants if g["valid_to"] is not None]
    checks.append(("expired coach shares are not visible now", all(g["space"] not in w.visible(g["identity"]) or any(
        g2["identity"] == g["identity"] and g2["space"] == g["space"] and g2["valid_to"] is None for g2 in w.grants) for g in exp), f"{len(exp)} expired"))
    # tasks: every task's required items visible to its requester; held-out nicknames absent from corpus
    bad_acc = [t["id"] for t in w.tasks if not all(w.by_id[i]["space"] in w.visible(t["requester"]) for i in t["required"])]
    checks.append(("every task's required items are visible to its requester", not bad_acc, f"{len(bad_acc)} bad"))
    corpus = " ".join((it.get("title") or "") + " " + it["text"] + " " + json.dumps(it.get("media") or {}) for it in w.items).lower()
    leak = [v["nick"] for v in w.vocab.values() if v["nick"] and v["nick"].lower() in corpus]
    checks.append(("held-out nicknames never appear in the corpus", not leak, f"{leak[:3]}"))
    gold_leak = [k for it in w.items for k in ("entities", "fact_refs", "tags", "scope") if k in it]
    checks.append(("pipeline view carries no gold tags", not gold_leak, f"{len(gold_leak)}"))
    res["checks"] = [dict(name=n, ok=bool(o), detail=d) for n, o, d in checks]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"dryrun_s{seed}.json"), "w") as f:
        json.dump(res, f, indent=1)
    for n, o, d in checks:
        print(("PASS " if o else "FAIL ") + n + (f"  [{d}]" if d else ""))
    return all(o for _, o, _ in checks)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    sys.exit(0 if main(a.seed) else 1)
