"""DT-U1a fabrication suite (DA2): does a required-field schema make the extractor invent values, and does span grounding
(model quote + code validator) stop it without losing recall?

200 items (seed 1): 100 where the asked (entity, attribute) value IS stated (extract-only key statements), 100 where it is NOT
(other items about the same entity kind; the asked attribute's value appears nowhere in the item). Three schemas
(required / nullable / nullable + span-required) x two writers (haiku, sonnet). Batches of 50 items.
"""
from __future__ import annotations

import json
import os
import random
from collections import Counter, defaultdict

from .common import ROOT
from . import gate3, llm3
from .pipe3 import World3

SCHEMAS = {"required": gate3.FAB_SYSTEM_REQUIRED, "nullable": gate3.FAB_SYSTEM_NULLABLE, "span": gate3.FAB_SYSTEM_SPAN}


def build_items(w, n_each=100, seed=11):
    R = random.Random(seed)
    schema = w.meta["schema"]
    present = []
    for iid, g in sorted(w.gold.items()):
        if g.get("extract_only"):
            for r in g["records"]:
                if r["t"] == "fact" and r.get("a"):
                    present.append(dict(id=iid, e=r["e"][0], a=r["a"], gold=r["v"], stated=True))
    R.shuffle(present)
    present = present[:n_each]
    # values of every version of every key: a "missing" item must contain none of the asked key's values
    vals = defaultdict(list)
    for k in w.keys_all.values():
        for v in k["versions"]:
            vals[(k["entity"], k["attr"])].append(w.gold[v].get("value_str") or "")
    missing, seen = [], set()
    cands = [iid for iid, g in sorted(w.gold.items()) if not w.by_id[iid].get("connector") and not w.by_id[iid].get("media") and g["entities"]
             and not any(r["t"] == "fact" and r.get("a") for r in g["records"])]
    R.shuffle(cands)
    for iid in cands:
        if len(missing) >= n_each:
            break
        g = w.gold[iid]
        e = g["entities"][0]
        if e not in w.entities:
            continue
        kind = w.entities[e]["kind"]
        attrs = sorted(a for (e2, a) in vals if e2 == e and a in schema.get(kind, {}))   # plausible: the entity really has this attribute
        if not attrs:
            continue
        a = R.choice(attrs)
        txt = gate3.nrm(w.by_id[iid]["text"])
        if any(v and gate3.nrm(v) in txt for v in vals.get((e, a), [])):
            continue
        if (e, a) in seen:
            continue
        seen.add((e, a))
        missing.append(dict(id=iid, e=e, a=a, gold=None, stated=False))
    items = present + missing
    R.shuffle(items)
    return items


def prompt_for(w, batch):
    sch = w.meta["schema"]
    lines = []
    for x in batch:
        e = w.entities[x["e"]]
        lines.append(json.dumps(dict(id=x["id"], text=w.by_id[x["id"]]["text"], entity=f"{x['e']} ({e['name']})", attribute=f"{x['a']} ({sch[e['kind']][x['a']]})"), ensure_ascii=False))
    return "Items:\n" + "\n".join(lines) + "\n"


def run(seed=1, models=("haiku", "sonnet"), log=print):
    w = World3(seed)
    items = build_items(w)
    out = {}
    for model in models:
        for sname, system in SCHEMAS.items():
            res = {}
            for bi in range(0, len(items), 50):
                batch = items[bi:bi + 50]
                try:
                    r = llm3.call(model, system, prompt_for(w, batch), stage=f"fab-{model}-{sname}", batch_id=f"s{seed}:{bi}")
                    arr = llm3.parse_json_array(r["text"])
                    for o in arr:
                        if isinstance(o, dict):
                            res[str(o.get("id"))] = o
                except (ValueError, RuntimeError) as ex:
                    log(f"[fab] {model} {sname} batch {bi}: {ex}")
                    if "spend cap" in str(ex):
                        raise
            out[(model, sname)] = res
            log(f"[fab] {model} {sname}: {len(res)} answers, spent ${llm3.spent():.2f}")
    return items, out, score(w, items, out)


def is_null(v):
    if v is None:
        return True
    x = str(v).strip().lower()
    return x in ("", "none", "null", "n/a", "unknown", "-") or x.startswith(("not stated", "not mentioned", "not specified", "no value", "not given", "not in the item", "unknown"))


def mislabeled(w, x):
    """A 'not stated' item whose gold holds a mention of the asked key (an older value rendered as e.g. '$461k'): the value IS stated.
    Found during analysis (generator-label error); excluded from both fabrication and recall."""
    g = w.gold[x["id"]]
    return (not x["stated"]) and any(r["t"] == "mention" and r.get("e") and r["e"][0] == x["e"] and r.get("a") == x["a"] for r in g["records"])


def score(w, items, out):
    rows = {}
    for (model, sname), res in out.items():
        c = Counter()
        for x in items:
            if mislabeled(w, x):
                c["excluded_mislabeled"] += 1
                continue
            o = res.get(x["id"], {})
            v = o.get("value")
            text = w.by_id[x["id"]]["text"]
            q = o.get("quote") or ""
            # code validator: value must be in the item; for the span schema also a verbatim quote containing the value
            valid = (not is_null(v)) and gate3.value_in(str(v), text) and (sname != "span" or (gate3.span_ok(q, text) and gate3.value_in(str(v), q)))
            if x["stated"]:
                c["stated_n"] += 1
                ok = (not is_null(v)) and (gate3.nrm(x["gold"]) in gate3.nrm(str(v)) or (gate3.nrm(str(v)) in gate3.nrm(x["gold"]) and len(gate3.nrm(str(v))) >= 0.6 * len(gate3.nrm(x["gold"]))))
                c["recall_raw"] += ok
                c["recall_validated"] += ok and valid
            else:
                c["missing_n"] += 1
                c["fab_raw"] += not is_null(v)
                c["fab_validated"] += valid
                c["fab_raw_not_in_item"] += (not is_null(v)) and not gate3.value_in(str(v), text)
            c["answered"] += x["id"] in res
        rows[f"{model}/{sname}"] = dict(stated_n=c["stated_n"], missing_n=c["missing_n"], answered=c["answered"], excluded=c["excluded_mislabeled"],
                                        recall_raw=c["recall_raw"] / max(1, c["stated_n"]), recall_validated=c["recall_validated"] / max(1, c["stated_n"]),
                                        fab_raw=c["fab_raw"] / max(1, c["missing_n"]), fab_validated=c["fab_validated"] / max(1, c["missing_n"]),
                                        fab_raw_k=c["fab_raw"], fab_validated_k=c["fab_validated"], recall_raw_k=c["recall_raw"], recall_validated_k=c["recall_validated"])
    return rows
