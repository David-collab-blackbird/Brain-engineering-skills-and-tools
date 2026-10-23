"""Build labelled closed-question sets J1-J3 from BrainBench v0.2.

Seed s1 = label pool (training / calibration labels, i.e. the "brain's own outcomes"); seed s2 = held-out test world
(different entities, same generator). Output: /home/claude/sysone/data/{job}_{split}.jsonl, one decision per line:
  {id, job, group, state, question, qtype, options:[(key, description)], label:int, meta:{...}}

J1 extraction checker  (noul): is an extracted record supported by its quoted source span? 50% true, 50% seeded errors
   (numeric drift, value swap, entity swap, attribute swap).
J2 relevance           (noul): is this candidate item vital for the request? required items vs TF-IDF hard negatives
   from the requester's own partitions (+1 random). Also a 3-way label (vital / related / irrelevant).
J3 router              (choice): request type (5 options) and area (7 options), given requester role + request.

Usage: python3 -I build_sets.py   (deterministic, seed 7)
"""
import collections
import json
import os
import random
import re
import sys

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

BB = "/home/claude/brainbench/data_v02"
OUT = "/home/claude/sysone/data"
os.makedirs(OUT, exist_ok=True)


def load(seed):
    d = f"{BB}/s{seed}"
    rd = lambda f: [json.loads(l) for l in open(f"{d}/{f}")]
    items = {x["id"]: x for x in rd("items.jsonl")}
    keys = {x["key"]: x for x in rd("keys.jsonl")}
    ents = {x["id"]: x for x in rd("entities.jsonl")}
    tasks = rd("tasks.jsonl")
    meta = json.load(open(f"{d}/meta.json"))
    return items, keys, ents, tasks, meta


def norm(s):
    return re.sub(r"[\s,]", "", s.lower())


SUFFIXES = [" per week", " units", " body fat", " strict pull-ups", " visits per week on average"]


def core_value(vs):
    for suf in SUFFIXES:
        vs = vs.replace(suf, "")
    return vs


def mentions(span, vs):
    return norm(core_value(vs)) in norm(span)


NUM = re.compile(r"(\d[\d,]*\.?\d*)")


def perturb_numeric(vs, rng):
    """Change the first number in a value string by 5-25% (or shift a date), keeping its format."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", vs)
    if m:
        y, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mo2 = (mo - 1 + rng.choice([-3, -2, -1, 1, 2, 3])) % 12 + 1
        return f"{y:04d}-{mo2:02d}-{dd:02d}"
    m = re.search(r"(\d+):(\d+)(\.\d)?", vs)  # times like 26:16 or 1:06.9
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        b2 = (b + rng.choice([-7, -5, -3, 3, 5, 7])) % 60
        return vs[:m.start()] + f"{a}:{b2:02d}{m.group(3) or ''}" + vs[m.end():]
    m = NUM.search(vs)
    if not m:
        return None
    raw = m.group(1)
    dec = len(raw.split(".")[1]) if "." in raw else 0
    x = float(raw.replace(",", ""))
    if x == 0:
        return None
    for _ in range(20):
        f = rng.choice([rng.uniform(0.75, 0.95), rng.uniform(1.05, 1.25)])
        y = x * f
        if dec:
            y = round(y, dec)
            s = f"{y:.{dec}f}"
        else:
            # keep trailing-zero granularity of the original (e.g. 588,000 -> 5xx,000)
            tz = len(str(int(x))) - len(str(int(x)).rstrip("0"))
            g = 10 ** min(tz, max(0, len(str(int(x))) - 2))
            y = int(round(y / g) * g)
            if y == int(x) or y <= 0:
                continue
            s = f"{y:,}" if "," in raw else str(y)
        if s != raw:
            return vs[:m.start()] + s + vs[m.end():]
    return None


def value_kind(vs):
    if vs.startswith("$"):
        return "money"
    if vs.endswith("%"):
        return "pct"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", vs):
        return "date"
    if re.search(r"\d", vs):
        return "num:" + re.sub(r"[\d,\.]+", "#", vs)
    return "text"


# --------------------------------------------------------------------------------------------- J1
def build_j1(seed, n_pos, rng):
    items, keys, ents, tasks, meta = load(seed)
    srcs = [i for i in items.values() if i.get("fact_refs")]
    rows = []
    by_attr_vals = collections.defaultdict(set)   # attribute -> value strings (any entity / version)
    by_kind_ents = collections.defaultdict(set)   # (entity kind, attribute) -> entity ids
    labels_by_kind = collections.defaultdict(set)  # (entity kind, value kind) -> key labels
    for it in items.values():
        if it["type"] == "fact" and it.get("key") in keys:
            by_attr_vals[it["attribute"]].add(it["value_str"])
            ek = ents[it["entity_id"]]["kind"]
            by_kind_ents[(ek, it["attribute"])].add(it["entity_id"])
            labels_by_kind[(ek, value_kind(it["value_str"]))].add(keys[it["key"]]["label"])
    cand = []
    for s in srcs:
        f = items[s["fact_refs"][0]]
        if f.get("key") not in keys or f["entity_id"] not in ents:
            continue
        if not mentions(s["text"], f["value_str"]):
            continue  # approximate mentions ("about 271 grand") are excluded: support would be ambiguous
        cand.append((s, f))
    rng.shuffle(cand)
    # one source per (entity, attribute, value) to avoid near-duplicates
    seen, uniq = set(), []
    for s, f in cand:
        k = (f["entity_id"], f["attribute"], f["value_str"])
        if k not in seen:
            seen.add(k)
            uniq.append((s, f))
    uniq = uniq[: 2 * n_pos]
    kinds = ["value_numeric", "value_swap", "entity_swap", "attribute_swap"]
    for j, (s, f) in enumerate(uniq):
        ent = ents[f["entity_id"]]
        label = keys[f["key"]]["label"]
        ename, value = ent["name"], f["value_str"]
        group = f"{seed}:{f['entity_id']}"
        base = dict(job="J1", group=group, qtype="noul", source_id=s["id"], fact_id=f["id"])
        if j % 2 == 0:  # supported
            rows.append(dict(base, claim=f"{ename} — {label}: {value}", span=s["text"], label=1,
                             meta=dict(kind="true", attribute=f["attribute"], scope=f["scope"], src_type=s["type"])))
            continue
        order = kinds[:]
        rng.shuffle(order)
        made = None
        for kind in order:
            if kind == "value_numeric":
                v2 = perturb_numeric(value, rng)
                if v2 and not mentions(s["text"], v2):
                    made = (kind, ename, label, v2)
            elif kind == "value_swap":
                pool = [v for v in by_attr_vals[f["attribute"]] if v != value and not mentions(s["text"], v)]
                if pool:
                    made = (kind, ename, label, rng.choice(sorted(pool)))
            elif kind == "entity_swap":
                pool = sorted(by_kind_ents[(ent["kind"], f["attribute"])] - {f["entity_id"]})
                pool = [e for e in pool if ents[e]["name"].split(",")[0].split()[-1].lower() not in s["text"].lower()]
                if pool:
                    made = (kind, ents[rng.choice(pool)]["name"], label, value)
            elif kind == "attribute_swap":
                pool = sorted(labels_by_kind[(ent["kind"], value_kind(value))] - {label})
                if pool:
                    made = (kind, ename, rng.choice(pool), value)
            if made:
                break
        if not made:
            continue
        kind, e2, l2, v2 = made
        rows.append(dict(base, claim=f"{e2} — {l2}: {v2}", span=s["text"], label=0,
                         meta=dict(kind=kind, attribute=f["attribute"], scope=f["scope"], src_type=s["type"])))
    out = []
    for r in rows:
        out.append(dict(
            id=f"J1-s{seed}-{len(out):05d}", job="J1", group=r["group"], qtype="noul",
            state=f"Quoted source: \"{r['span']}\"\nExtracted record: {r['claim']}",
            question="Is the extracted record fully supported by the quoted source (same entity, same attribute, same value)?",
            options=[["false", "no, the record is not supported by the source"], ["true", "yes, the source states exactly this record"]],
            label=r["label"], meta=r["meta"], parts=dict(span=r["span"], claim=r["claim"])))
    return out


# --------------------------------------------------------------------------------------------- J2 / J3 helpers
def origin_text(it):
    m = it.get("media")
    if not m:
        return ""
    o = m.get("origin", {})
    parts = [o.get("folder", "").replace("/", " "), o.get("album", ""), o.get("chat", ""),
             ("shared by " + o["shared_by"]) if o.get("shared_by") else ""]
    return " ".join(p for p in parts if p)


def item_text(it):
    t = it["text"]
    if it.get("type") in ("image", "video_segment", "page"):
        t = f"[{it['type']}] " + t + (" — " + origin_text(it) if origin_text(it) else "")
    else:
        t = f"[{it['type']}, {it['date']}] " + t
    return t


ROLE = {"owner": "the owner (Dane Halloran)", "partner": "a business partner", "member": "a gym member (app user)",
        "household": "a family member"}


def role_of(requester):
    p = requester.split("_")[0]
    if requester.startswith("partner_"):
        return f"a business partner ({requester.split('_', 1)[1]} business)"
    return ROLE.get(p, requester)


def build_j2(seed, per_class, rng):
    items, keys, ents, tasks, meta = load(seed)
    idents = meta["identities"]
    ids = sorted(items)
    texts = [item_text(items[i]) for i in ids]
    vec = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=1, stop_words="english")
    X = vec.fit_transform(texts)
    pos = {i: k for k, i in enumerate(ids)}
    part = np.array([items[i]["partition"] for i in ids])
    by_cls = collections.defaultdict(list)
    for t in tasks:
        by_cls[t["cls"]].append(t)
    out = []
    for cls in sorted(by_cls):
        ts = by_cls[cls][:]
        rng.shuffle(ts)
        seen_sets, chosen = set(), []
        for t in ts:
            if t["set_id"] in seen_sets:
                continue
            seen_sets.add(t["set_id"])
            chosen.append(t)
            if len(chosen) >= per_class:
                break
        for t in chosen:
            parts = set(idents[t["requester"]]["partitions"]) if t["requester"] in idents else None
            if parts is None:
                continue
            acc = np.isin(part, list(parts))
            q = vec.transform([t["query"]])
            sc = (X @ q.T).toarray().ravel()
            sc[~acc] = -1
            req = list(t["required"])
            req_ents = {e for r in req for e in items[r]["entities"]}
            top = [ids[k] for k in np.argsort(-sc)[:40] if ids[k] not in req]
            negs = top[:5]
            pool = [ids[k] for k in np.where(acc)[0] if ids[k] not in req and ids[k] not in negs]
            negs.append(rng.choice(pool))
            if len(req) > 4:
                req = rng.sample(req, 4)
            for iid in req + negs:
                it = items[iid]
                vital = iid in t["required"]
                rel = "vital" if vital else ("related" if set(it["entities"]) & req_ents else "irrelevant")
                out.append(dict(
                    id=f"J2-s{seed}-{len(out):05d}", job="J2", group=f"{seed}:{t['id']}", qtype="noul",
                    state=f"Request from {role_of(t['requester'])}: \"{t['query']}\"\nCandidate memory item: {item_text(it)}",
                    question="Is this memory item needed to answer the request correctly and completely?",
                    options=[["false", "no, the item is not needed for this request"], ["true", "yes, the item is needed for this request"]],
                    label=int(vital), meta=dict(cls=cls, rel3=rel, item_type=it["type"], superseded=bool(it.get("superseded_by")),
                                                hard=iid in top[:5]),
                    parts=dict(query=t["query"], item=item_text(it), role=role_of(t["requester"]))))
    return out


TYPE_MAP = {"current_state": "lookup", "stale_probe": "lookup", "temporal_change": "history",
            "decision_support": "advice", "option_analysis": "advice", "goal_tracking": "advice",
            "preference_recommendation": "advice", "cross_domain": "cross_area", "multimodal": "media"}
TYPE_OPTS = [["lookup", "look up one current fact or record"],
             ["history", "how something changed over time, or its past values"],
             ["advice", "reasoning, a recommendation, a decision or progress against a goal"],
             ["cross_area", "combine information from several different areas of life or business"],
             ["media", "find a photo, video, scan or document file"]]
AREA_OPTS = [["business/gym", "the gym business, its members, coaches and training"],
             ["business/construction", "the construction business, its jobs and sites"],
             ["business/cafe", "the cafe business"],
             ["finance", "investments, properties, loans, shares and personal finance"],
             ["family", "the family, household and leisure"],
             ["health", "the owner's own health and training"],
             ["reading", "books and reading"]]


def build_j3(seed, per_type, rng):
    items, keys, ents, tasks, meta = load(seed)
    by_type = collections.defaultdict(list)
    for t in tasks:
        by_type[TYPE_MAP[t["cls"]]].append(t)
    out = []
    for ty in sorted(by_type):
        ts = by_type[ty][:]
        rng.shuffle(ts)
        # dedupe identical query strings
        seen, chosen = set(), []
        for t in ts:
            if t["query"] in seen:
                continue
            seen.add(t["query"])
            chosen.append(t)
            if len(chosen) >= per_type:
                break
        for t in chosen:
            state = f"Requester: {role_of(t['requester'])}\nRequest: \"{t['query']}\""
            base = dict(job="J3", group=f"{seed}:{t['id']}", qtype="choice", state=state,
                        parts=dict(query=t["query"], role=role_of(t["requester"])))
            out.append(dict(base, id=f"J3t-s{seed}-{len(out):05d}", subjob="type",
                            question="What kind of request is this?", options=TYPE_OPTS,
                            label=[o[0] for o in TYPE_OPTS].index(ty), meta=dict(cls=t["cls"], type=ty)))
            area = t["declared_scope"]
            out.append(dict(base, id=f"J3a-s{seed}-{len(out):05d}", subjob="area",
                            question="Which area of the brain does this request belong to?", options=AREA_OPTS,
                            label=[o[0] for o in AREA_OPTS].index(area), meta=dict(cls=t["cls"], area=area)))
    return out


def write(rows, name):
    with open(f"{OUT}/{name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    lab = collections.Counter(r["label"] for r in rows)
    print(f"{name}: {len(rows)} rows, labels {dict(lab)}")


def group_shuffle(rows, rng, cap=None):
    """Shuffle at the group level (whole tasks / entities stay together) so any prefix of the pool is a clean
    'first N labels' sample; optionally cap the number of rows."""
    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    keys = list(groups)
    rng.shuffle(keys)
    out = [r for k in keys for r in groups[k]]
    return out[:cap] if cap else out


if __name__ == "__main__":
    rng = random.Random(7)
    # label pools come from worlds s1 (+ s3 for J1, which has fewer unique sources); the test set is world s2
    # (different people, properties, businesses' records; same generator).
    j1_pool = build_j1(1, 700, rng) + build_j1(3, 700, rng)
    write(group_shuffle(j1_pool, rng, 1200), "J1_pool")
    write(build_j1(2, 200, rng), "J1_test")
    write(group_shuffle(build_j2(1, 60, rng), rng, 1500), "J2_pool")
    write(group_shuffle(build_j2(2, 12, rng), rng), "J2_test")
    write(group_shuffle(build_j3(1, 400, rng), rng, 1200), "J3_pool")
    write(group_shuffle(build_j3(2, 40, rng), rng), "J3_test")
