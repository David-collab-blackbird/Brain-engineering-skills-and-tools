"""Gold-set diagnostics: lexical overlap between requests and required items; entity-linker accuracy;
corpus-statistics leakage of TF-IDF / LSA (fitted on all partitions)."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from .brain import CLASSES, Brain, World
from .common import NOW_DAY, tokenize
from .experiments import Linker
from .retrieval import Index, item_text


def lexical_overlap(w: World):
    out = {}
    agg = defaultdict(lambda: [0, 0, 0, 0])
    for t in w.tasks:
        if t["cls"] not in CLASSES:
            continue
        q = set(tokenize(t["query"]))
        zero = 0
        for r in t["required"]:
            it = w.by_id[r]
            if not (q & set(tokenize(item_text(it)))):
                zero += 1
        a = agg[t["cls"]]
        a[0] += zero; a[1] += len(t["required"]); a[2] += int(zero > 0); a[3] += 1
    for c, (z, n, tz, tn) in agg.items():
        out[c] = dict(items_zero_overlap=z / n, tasks_with_a_zero_overlap_item=tz / tn)
    return out


def linker_accuracy(w: World):
    L = Linker(w)
    agg = defaultdict(lambda: [0, 0])
    for t in w.tasks:
        if t["cls"] not in CLASSES:
            continue
        need = {e for r in t["required"] for e in ([w.by_id[r]["entity_id"]] if w.by_id[r].get("entity_id") else [])}
        if not need:
            continue
        got = set(L.link(t["query"], t["requester"]))
        agg[t["cls"]][0] += len(need & got); agg[t["cls"]][1] += len(need)
    return {c: v[0] / v[1] for c, v in agg.items()}


def vector_stats_leak(w: World):
    """Does a VISIBLE doc's TF-IDF / LSA vector change when hidden docs are added?"""
    base = [it for it in w.items]
    vis = dict(id="vis", type="note", partition="biz/cafe", scope="business/cafe/ops", title="",
               text="zzqprobe grinder delivery note", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[])
    res = {}
    vecs = {}
    for M in (0, 10):
        hid = [dict(id=f"h{j}", type="note", partition="owner", scope="finance/investments", title="", text="private zzqprobe",
                    created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[]) for j in range(M)]
        ix = Index(base + [vis] + hid, lsa_dim=64)
        p = ix.pos["vis"]
        vecs[M] = (ix.tfidf_cos("zzqprobe grinder")[p], ix.lsa_cos("zzqprobe grinder")[p])
    res["tfidf_score_delta"] = float(vecs[10][0] - vecs[0][0])
    res["lsa_score_delta"] = float(vecs[10][1] - vecs[0][1])
    return res
