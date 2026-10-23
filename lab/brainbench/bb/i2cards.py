"""I2 kill test (deferred from batch 1): do LLM-written entity cards carry stale values where code-compiled cards
(rendered from current keyed-fact heads) cannot?

For every (entity, partition) with free-text notes that quote keyed-fact values (`fact_refs`), the LLM writes a card
from those dated notes (the realistic situation for a model-written profile: it sees episodes, not the keyed store).
Two input orders: random (as retrieved by relevance) and newest-first. For every keyed fact of that entity with >=2
versions where the notes contain BOTH a current-version mention and a superseded-version mention, we check which
value(s) the card states.
"""
from __future__ import annotations

import random
import re
from collections import defaultdict

NUM = re.compile(r"\$?\s*(\d[\d,]*\.?\d*)\s*(k|m|grand|million)?\b", re.I)

CARD_PROMPT = """Below are dated notes about {name}. Write a short profile card listing the CURRENT facts about {name} (one "attribute: value" per line, at most 8 lines). Use only information in the notes.

Notes:
{notes}

Profile card for {name}:"""


def numbers(text):
    out = []
    for m in NUM.finditer(text):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        mult = (m.group(2) or "").lower()
        if mult in ("k", "grand"):
            v *= 1000
        elif mult in ("m", "million"):
            v *= 1_000_000
        out.append(v)
    return out


def states(card, value, value_str):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        tol = max(abs(value) * 0.006, 0.051)
        return any(abs(x - value) <= tol for x in numbers(card))
    return str(value_str).lower() in card.lower()


def run(w, llm, seed=0, max_notes=24, max_groups=None, max_new_tokens=160):
    R = random.Random(seed)
    head = {}
    for k in w.keys.values():
        for v in k["versions"]:
            head[v] = (k["key"], k["versions"][-1])
    groups = defaultdict(list)
    for it in w.items:
        if it.get("fact_refs") and it["type"] != "fact":
            groups[(w.keys[head[it["fact_refs"][0]][0]]["entity"], it["partition"])].append(it)
    jobs = []
    items_g = [(k, v) for k, v in sorted(groups.items()) if len(v) >= 3]
    if max_groups and len(items_g) > max_groups:
        items_g = sorted(R.sample(items_g, max_groups))
    for (eid, part), notes in items_g:
        notes = R.sample(notes, min(max_notes, len(notes)))
        name = w.entities[eid]["name"]
        for order in ("random", "newest-first"):
            ns = notes if order == "random" else sorted(notes, key=lambda x: -x["created_day"])
            prompt = CARD_PROMPT.format(name=name, notes="\n".join(f"- [{x['date']}] {x['text']}" for x in ns))
            jobs.append((eid, part, order, ns, prompt))
    outs = llm.generate([j[4] for j in jobs], max_new_tokens=max_new_tokens)
    res = []
    for (eid, part, order, ns, _), card in zip(jobs, outs):
        refs = defaultdict(set)
        for x in ns:
            for f in x["fact_refs"]:
                refs[head[f][0]].add(f)
        for key, vids in refs.items():
            k = w.keys[key]
            cur = k["versions"][-1]
            if len(k["versions"]) < 2 or cur not in vids or not (vids - {cur}):
                continue
            hv = w.by_id[cur]
            cur_s = states(card, hv["value"], hv["value_str"])
            old = [v for v in vids if v != cur and w.by_id[v]["value_str"] != hv["value_str"]]
            old_s = any(states(card, w.by_id[v]["value"], w.by_id[v]["value_str"]) for v in old)
            res.append(dict(entity=eid, key=key, order=order, current=cur_s, stale=old_s, family=k["family"]))
    return res, [dict(entity=j[0], order=j[2], card=c) for j, c in zip(jobs, outs)][:6]
