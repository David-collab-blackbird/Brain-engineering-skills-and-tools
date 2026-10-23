"""E9 write gate (N8 / U1, DA2 I-3 contract) and its code validators.

Every text item passes one pipeline at ingest:
  1. batch by space and thread, in time order (so coreference inside a thread is resolvable);
  2. LLM (claude -p, model pinned per arm) links the item to registered entities (incl. implicit mentions), extracts typed
     records with verbatim source spans (decision, preference, constraint, plan, issue, offer, fact with entity+attribute+value),
     alias statements ("we call X 'the ...'"), and up to 6 search phrases (the U2 scribe entry, no values);
  3. code validators: schema (type, entity registered in the item's space, attribute valid for the entity kind),
     span check (verbatim substring after whitespace/quote normalisation), value-in-span (fact value present in the span
     and the item), "not stated" allowed; invalid records are dropped and counted. The write is never blocked.
Media items and connector facts do not go to the LLM: media are linked by code (registry aliases in caption + origin),
connector facts carry the connector's entity id.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

from .common import ROOT, tokenize
from . import llm3

GATE_DIR = os.path.join(ROOT, "results_v03", "gate")
RTYPES = ("decision", "preference", "constraint", "plan", "issue", "offer", "fact")
GOLD_T = {"decision": "decision", "preference": "preference", "rule": "constraint", "plan": "plan", "issue": "issue", "quote": "offer", "fact": "fact"}

SYSTEM = """You are the write gate of a private memory system for a family and its businesses. Every message, note, email, meeting minute and log entry passes through you once, at the moment it is stored. You turn each item into structured, linked records so it can be found later. You never answer questions and never add information that is not in the item.

For EACH input item output one JSON object:
{"id": <item id>,
 "e": [registered entity ids the item is about — include entities referred to only indirectly (pronouns, nicknames, "the cafe", "the site", the business whose chat or log this is, the member whose log this is); use ONLY ids from the registry below; [] if none],
 "r": [typed records, possibly empty:
   {"t": "decision"|"preference"|"constraint"|"plan"|"issue"|"offer", "e": [entity ids], "q": "<verbatim quote from the item>"}
   {"t": "fact", "e": "<one entity id>", "a": "<attribute name from the schema for that entity's kind>", "v": "<the value exactly as written in the item>", "q": "<verbatim quote containing the value>"}],
 "al": [{"p": "<nickname or descriptor the writer uses>", "e": "<entity id>"}] — only when the item itself shows a name being used for an entity that is not in the registry aliases; else omit,
 "k": [up to 6 short search phrases a person might later type to find this item: topics, people, places, kinds of thing; NO numbers, amounts, dates or values]}

Record types: decision = something agreed or decided; preference = a like, dislike or wish of a person; constraint = a rule, policy, limit, clause or precedence; plan = an intention, commitment, booking, obligation or due item; issue = a problem, fault, complaint, incident or risk; offer = a quote, offer, invoice, invitation or proposal; fact = a value for one schema attribute of one entity (a current state such as a supplier, goal, target, stage, role, program, schedule, budget, balance, price or count).
Rules:
- Quotes ("q") must be copied character for character from the item's text. Never paraphrase inside "q".
- A fact's "v" must appear in the item's text. If the item does not state a value for an attribute, do not output that fact ("not stated" is always acceptable; never guess, never fill from other items).
- Link to the registry only. If the item is about something not in the registry, leave it out of "e".
- Output ONLY the JSON array of objects, one per input item, in input order. No prose, no code fences. Write compact JSON: one object per line, no indentation.
"""

FAB_SYSTEM_REQUIRED = """Extract one record from each item. Output a JSON array of objects: {"id": <item id>, "entity": <entity id>, "attribute": <attribute>, "value": <the value>}. Every field is required: always give a value for the attribute named for that item. Output only the JSON array."""
FAB_SYSTEM_NULLABLE = """Extract one record from each item. Output a JSON array of objects: {"id": <item id>, "entity": <entity id>, "attribute": <attribute>, "value": <the value, or "not stated" if the item does not state it>}. Never guess. Output only the JSON array."""
FAB_SYSTEM_SPAN = """Extract one record from each item. Output a JSON array of objects: {"id": <item id>, "entity": <entity id>, "attribute": <attribute>, "value": <the value, or "not stated">, "quote": <verbatim words from the item that state the value, or "" if not stated>}. A value without a verbatim quote that contains it is invalid. Never guess. Output only the JSON array."""


# ============================================================================ text normalisation for validators
def nrm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    return " ".join(s.split()).lower()


def span_ok(q, text):
    q2, t2 = nrm(q), nrm(text)
    if not q2:
        return False
    if q2 in t2:
        return True
    q3 = re.sub(r"[^a-z0-9$%.]+", " ", q2).strip()
    t3 = re.sub(r"[^a-z0-9$%.]+", " ", t2)
    return bool(q3) and q3 in t3


VAL_STOP = {"the", "a", "an", "of", "and", "per", "for", "to", "at", "on", "in", "by", "with", "our", "is"}


def value_in(v, text):
    v2, t2 = nrm(v), nrm(text)
    if not v2:
        return False
    if v2 in t2:
        return True
    nums = re.findall(r"\d[\d,]*(?:\.\d+)?", v2)
    words = [w for w in re.findall(r"[a-z]+", v2) if w not in VAL_STOP and len(w) > 2]
    tt = re.sub(r"[,]", "", t2)
    if nums and not all(n.replace(",", "") in tt for n in nums):
        return False
    if words:
        hit = sum(1 for w in words if re.search(r"(?<![a-z])" + re.escape(w[:max(4, len(w) - 2)]), t2))
        return hit / len(words) >= 0.8
    return bool(nums)


# ============================================================================ batching and prompts
def registry_for(w, spaces):
    reg = []
    for e in w.entities.values():
        if set(e.get("spaces", [])) & spaces:
            reg.append(e)
    reg.sort(key=lambda e: (e["kind"], e["id"]))
    return reg


def schema_block(w, kinds):
    sch = w.meta["schema"]
    lines = []
    for k in sorted(kinds):
        if k in sch:
            lines.append(f"- {k}: " + "; ".join(f"{a} ({lab})" for a, lab in sorted(sch[k].items())))
    return "\n".join(lines)


def system_for(w, spaces):
    reg = registry_for(w, spaces)
    rl = "\n".join(f"{e['id']} | {e['kind']} | {e['name']}" + (f" | aka: {', '.join(e['aliases'][1:])}" if len(e["aliases"]) > 1 else "") for e in reg)
    sch = schema_block(w, {e["kind"] for e in reg})
    return SYSTEM + f"\nRegistry (entities in these spaces: {', '.join(sorted(spaces))}):\n{rl}\n\nAttribute schema by entity kind (attribute (meaning)):\n{sch}\n"


def item_line(it):
    d = dict(id=it["id"], date=it["date"], type=it["type"], space=it["space"], thread=it.get("thread") or "", text=it["text"])
    if it.get("title"):
        d["title"] = it["title"]
    if it.get("sender"):
        d["from"] = it["sender"]
    return json.dumps(d, ensure_ascii=False)


def space_group(sp):
    if sp.startswith("member/"):
        n = int(sp.split("/")[1][1:3])
        return f"members{(n - 1) // 7}"
    return sp


def batches(w, max_items=60, max_chars=9000):
    """Text items (not media, not connector) grouped by space group, then thread, then time."""
    todo = [it for it in w.items if not it.get("connector") and not it.get("media")]
    groups = defaultdict(list)
    for it in todo:
        groups[space_group(it["space"])].append(it)
    out = []
    for gname in sorted(groups):
        its = sorted(groups[gname], key=lambda it: (it.get("thread") or "", it["created_day"], it["id"]))
        cur, chars = [], 0
        for it in its:
            ln = len(item_line(it))
            if cur and (len(cur) >= max_items or chars + ln > max_chars):
                out.append((gname, cur)); cur, chars = [], 0
            cur.append(it); chars += ln
        if cur:
            out.append((gname, cur))
    return out


# ============================================================================ run the gate for one seed
def run_gate(w, model, stage, limit_batches=None, only_groups=None, max_items=60, log=print, max_new_calls=None):
    os.makedirs(GATE_DIR, exist_ok=True)
    bs = batches(w, max_items=max_items)
    if only_groups:
        bs = [b for b in bs if b[0] in only_groups]
    if limit_batches is not None:
        bs = bs[:limit_batches]
    raw = {}
    fails = 0
    new_calls = 0
    for bi, (gname, its) in enumerate(bs):
        if max_new_calls is not None and new_calls >= max_new_calls:
            return None, dict(batches=len(bs), stopped_at=bi)      # bounded chunk: resume later from the cache
        spaces = {it["space"] for it in its}
        if gname.startswith("members"):
            spaces |= {s + "/account" for s in spaces if s.count("/") == 1} | {"company/ironbark/public"}
        system = system_for(w, spaces)
        prompt = "Items:\n" + "\n".join(item_line(it) for it in its) + "\n"
        bid = f"s{w.seed}:{gname}:{bi}"
        got = None
        for attempt in range(2):
            try:
                r = llm3.call(model, system, prompt + ("" if attempt == 0 else "\n(Return valid JSON only.)"), stage=stage, batch_id=bid)
                new_calls += 0 if r.get("cached") else 1
                arr = llm3.parse_json_array(r["text"])
                got = {str(o.get("id")): o for o in arr if isinstance(o, dict)}
                break
            except (ValueError, json.JSONDecodeError) as ex:
                log(f"[gate] {bid} parse error attempt {attempt}: {ex}")
            except RuntimeError as ex:
                log(f"[gate] {bid} call error: {ex}")
                if "spend cap" in str(ex):
                    raise
        if got is None:
            fails += 1
            got = {}
        for it in its:
            raw[it["id"]] = got.get(it["id"], {"id": it["id"], "missing": True})
        if bi % 10 == 0:
            log(f"[gate] {stage} {bi+1}/{len(bs)} batches, spent so far ${llm3.spent():.2f}")
    return raw, dict(batches=len(bs), failed_batches=fails)


# ============================================================================ validators (code) and the gate's final output
def validate(w, raw):
    """Returns (links, records, aliases, entries, stats). Never blocks: every item keeps its place in the store."""
    st = Counter()
    links, records, aliases, entries = {}, {}, [], {}
    schema = w.meta["schema"]
    for iid, o in raw.items():
        it = w.by_id[iid]
        text = (it.get("title") or "") + " " + it["text"]
        sp = it["space"]
        ok_ent = lambda e: e in w.entities and (sp in w.entities[e].get("spaces", []) or (sp.endswith("/account") and sp.rsplit("/", 1)[0] in w.entities[e].get("spaces", [])))
        if o.get("missing"):
            st["items_missing"] += 1
        es = o.get("e") or []
        if isinstance(es, str):
            es = [es]
        good = []
        for e in es:
            if ok_ent(e):
                good.append(e)
            else:
                st["link_invalid_entity"] += 1
        links[iid] = list(dict.fromkeys(good))
        rr = []
        for r in o.get("r") or []:
            if not isinstance(r, dict):
                st["rec_bad_shape"] += 1; continue
            t = r.get("t")
            st["rec_raw"] += 1
            if t not in RTYPES:
                st["rec_bad_type"] += 1; continue
            q = r.get("q") or ""
            if t == "fact":
                e = r.get("e"); e = e[0] if isinstance(e, list) and e else e
                a, v = r.get("a"), r.get("v")
                st["fact_raw"] += 1
                if v in (None, "", "not stated"):
                    st["fact_not_stated"] += 1; continue
                if not value_in(str(v), text):
                    st["fact_value_not_in_item"] += 1; continue        # invented value
                if not isinstance(e, str) or not ok_ent(e):
                    st["fact_bad_entity"] += 1; continue
                if a not in schema.get(w.entities[e]["kind"], {}):
                    st["fact_bad_attr"] += 1; continue
                if q and not span_ok(q, text):
                    st["fact_span_not_verbatim"] += 1; continue
                if q and not value_in(str(v), q):
                    st["fact_value_not_in_span"] += 1; continue
                rr.append(dict(t="fact", e=[e], a=a, v=str(v), s=q))
                st["fact_kept"] += 1
            else:
                es2 = r.get("e") or []
                es2 = [es2] if isinstance(es2, str) else es2
                es2 = [e for e in es2 if ok_ent(e)]
                if not q or not span_ok(q, text):
                    st["rec_span_not_verbatim"] += 1; continue
                rr.append(dict(t=t, e=es2, s=q))
                st["rec_kept"] += 1
        records[iid] = rr
        for a in o.get("al") or []:
            if isinstance(a, dict) and a.get("p") and ok_ent(a.get("e")) and span_ok(a["p"], text):
                aliases.append((a["p"], a["e"], iid)); st["alias_kept"] += 1
            elif isinstance(a, dict):
                st["alias_rejected"] += 1
        ks = [k for k in (o.get("k") or []) if isinstance(k, str)][:6]
        entries[iid] = ks
    # media: code linker over caption + origin (no LLM)
    pats = []
    for e in w.entities.values():
        for a in e["aliases"]:
            if len(a) >= 4 and a.lower() not in ("training", "portfolio", "offset", "reading list"):
                pats.append((a.lower(), e["id"]))
    for it in w.items:
        if it.get("media"):
            m = it["media"]; o = m.get("origin") or {}
            txt = " ".join([it["text"], o.get("folder", "").replace("/", " "), o.get("album", ""), o.get("chat", ""), o.get("adjacent_text", "")]).lower()
            links[it["id"]] = [eid for a, eid in pats if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", txt) and it["space"] in w.entities[eid].get("spaces", [])]
            records.setdefault(it["id"], [])
        elif it.get("connector"):
            links[it["id"]] = [it["connector"]["entity_id"]]
            records.setdefault(it["id"], [])
    return links, records, aliases, entries, dict(st)


def code_gate(w):
    """Deterministic baseline gate (no LLM): registry-alias string match + the space's owner entity; no typed records,
    no implicit mentions. DA2 A10's 'string-match extractor'."""
    from .world3 import SPACE_DEFAULT_ENTITY
    pats = []
    for e in w.entities.values():
        for a in e["aliases"]:
            if len(a) >= 3 and a.lower() not in ("me", "training", "portfolio", "offset", "reading list", "my training", "my reading"):
                pats.append((a.lower(), e["id"]))
    pats.sort(key=lambda x: -len(x[0]))
    member_ent = {f"member/{e['member_id']}": e["id"] for e in w.entities.values() if e.get("member_id")}
    links, records = {}, {}
    for it in w.items:
        if it.get("connector"):
            links[it["id"]] = [it["connector"]["entity_id"]]; records[it["id"]] = []; continue
        txt = ((it.get("title") or "") + " " + it["text"] + " " + json.dumps(it.get("media") or {})).lower()
        es = [eid for a, eid in pats if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", txt) and it["space"] in w.entities[eid].get("spaces", [])]
        d = SPACE_DEFAULT_ENTITY.get(it["space"]) or member_ent.get(it["space"])
        if d and d not in es and not it.get("media"):
            es.append(d)
        links[it["id"]] = list(dict.fromkeys(es))
        records[it["id"]] = []
    return links, records


# ============================================================================ extraction quality vs gold
def quality(w, links, records, required_ids=None):
    """Linking P/R (all items with gold entities; required evidence items; implicit mentions), typed-record coverage by type,
    keyed-fact coverage for extract-only keys, value accuracy."""
    out = {}
    tp = fp = fn = 0
    imp_hit = imp_n = exp_hit = exp_n = 0
    req_tp = req_fp = req_fn = 0
    for iid, g in w.gold.items():
        it = w.by_id[iid]
        if it.get("connector") or it.get("media"):
            continue
        ge = set(g["entities"])
        pe = set(links.get(iid, []))
        tp += len(ge & pe); fp += len(pe - ge); fn += len(ge - pe)
        if required_ids is not None and iid in required_ids:
            req_tp += len(ge & pe); req_fp += len(pe - ge); req_fn += len(ge - pe)
        for e, imp in g.get("implicit", {}).items():
            if imp:
                imp_n += 1; imp_hit += e in pe
            else:
                exp_n += 1; exp_hit += e in pe
    out["link_precision"] = tp / max(1, tp + fp)
    # lenient precision: a predicted entity not in gold still counts as correct when the item names one of its registered aliases
    # (v0.2-derived gold tags on filler items are incomplete, e.g. staff first names)
    lfp = 0
    for iid, g in w.gold.items():
        it = w.by_id[iid]
        if it.get("connector") or it.get("media"):
            continue
        txt = ((it.get("title") or "") + " " + it["text"]).lower()
        for e in set(links.get(iid, [])) - set(g["entities"]):
            al = [a.lower() for a in w.entities[e]["aliases"] if len(a) >= 3]
            if not any(re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", txt) for a in al):
                lfp += 1
    out["link_precision_lenient"] = tp / max(1, tp + lfp) if (tp + lfp) else 0.0
    out["link_recall"] = tp / max(1, tp + fn)
    out["link_recall_implicit"] = imp_hit / max(1, imp_n)
    out["link_recall_explicit"] = exp_hit / max(1, exp_n)
    out["n_implicit"], out["n_explicit"] = imp_n, exp_n
    if required_ids is not None:
        out["req_link_precision"] = req_tp / max(1, req_tp + req_fp)
        out["req_link_recall"] = req_tp / max(1, req_tp + req_fn)
    # typed records: a gold record (type T, entities E) is covered if the gate has a record of type T on that item
    cov = Counter(); tot = Counter(); cov_imp = Counter(); tot_imp = Counter()
    for iid, g in w.gold.items():
        it = w.by_id[iid]
        if it.get("connector") or it.get("media"):
            continue
        pr = records.get(iid, [])
        imp_item = any(g.get("implicit", {}).values())
        for r in g["records"]:
            T = GOLD_T.get(r["t"]) if r["t"] != "mention" else "fact"
            if T is None:
                continue
            if r["t"] == "fact" and not g.get("extract_only"):
                continue
            tot[T] += 1
            hit = any(GOLD_T.get(p["t"], p["t"]) == T for p in pr) if T != "fact" else any(p["t"] == "fact" and (r.get("key") is None or p.get("a") == r.get("a")) for p in pr)
            cov[T] += hit
            if imp_item:
                tot_imp[T] += 1; cov_imp[T] += hit
    out["record_coverage"] = {T: cov[T] / tot[T] for T in tot}
    out["record_coverage_n"] = dict(tot)
    out["record_coverage_implicit_items"] = {T: cov_imp[T] / tot_imp[T] for T in tot_imp if tot_imp[T]}
    # keyed facts for extract-only keys: (entity, attr, value) correct
    n = hit = wrong = 0
    for iid, g in w.gold.items():
        if not g.get("extract_only"):
            continue
        gr = [r for r in g["records"] if r["t"] == "fact" and r.get("key")]
        for r in gr:
            n += 1
            ps = [p for p in records.get(iid, []) if p["t"] == "fact" and p["e"] and p["e"][0] == r["e"][0] and p["a"] == r["a"]]
            if any(nrm(r["v"]) in nrm(p["v"]) or (nrm(p["v"]) in nrm(r["v"]) and len(nrm(p["v"])) >= 0.6 * len(nrm(r["v"]))) for p in ps):
                hit += 1
            elif ps:
                wrong += 1
    out["keyed_fact_recall"] = hit / max(1, n)
    out["keyed_fact_wrong_value"] = wrong / max(1, n)
    out["keyed_fact_n"] = n
    return out


def save_gate(name, seed, links, records, aliases, entries, stats, meta=None):
    os.makedirs(GATE_DIR, exist_ok=True)
    with open(os.path.join(GATE_DIR, f"{name}_s{seed}.json"), "w") as f:
        json.dump(dict(links=links, records=records, aliases=aliases, entries=entries, stats=stats, meta=meta or {}), f)


def load_gate(name, seed):
    p = os.path.join(GATE_DIR, f"{name}_s{seed}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)
