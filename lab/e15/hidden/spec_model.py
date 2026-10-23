"""Independent model of the WP-E15 spec used by the hidden conformance tests.

Written separately from the reference solution: pure Python over the store's
current records. Includes the owner's scripted answer OA-1 (agents get the
intersection of their own valid groups and their person's visible groups).
"""
from __future__ import annotations

import math

from e15store import embed, tokens


def own_groups(store, p):
    out = set()
    for gid in store.membership_rows(p["id"]):
        g = store.group(gid)
        if g is not None and g["tenant"] == p["tenant"]:
            out.add(gid)
    return out


def visible(store, principal_id):
    p = store.principal(principal_id)
    if p is None or p["status"] != "active":
        return None, set()
    groups = own_groups(store, p)
    if p["kind"] == "agent":
        person = store.principal(p["acts_for"]) if p["acts_for"] else None
        if person is None or person["status"] != "active" or person["kind"] != "person" \
                or person["tenant"] != p["tenant"]:
            return p["tenant"], set()
        groups &= own_groups(store, person)
    return p["tenant"], groups


def search(store, query, principal_id, k=10, idf="lucene", unique_terms=True):
    tenant, groups = visible(store, principal_id)
    q = tokens(query)
    if not q or not groups:
        return []
    docs = [r for r in store.current_records()
            if r["state"] == "active" and r["tenant"] == tenant and r["acl_group"] in groups]
    if not docs:
        return []
    toks = {r["id"]: tokens(r["title"] + " " + r["body"]) for r in docs}
    n = len(docs)
    avgdl = sum(len(t) for t in toks.values()) / n
    terms = sorted(set(q)) if unique_terms else q
    lex = {}
    for term in terms:
        df = sum(1 for t in toks.values() if term in t)
        if df == 0:
            continue
        if idf == "lucene":
            w = math.log(1 + (n - df + 0.5) / (df + 0.5))
        else:
            w = math.log((n - df + 0.5) / (df + 0.5))
        for rid, t in toks.items():
            f = t.count(term)
            if f:
                lex[rid] = lex.get(rid, 0.0) + w * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(t) / avgdl))
    lex_rank = sorted([(s, rid) for rid, s in lex.items() if s > 0], key=lambda x: (-x[0], x[1]))[:200]
    qv = embed(query)
    dense = []
    for r in docs:
        c = sum(a * b for a, b in zip(qv, embed(r["title"] + "\n" + r["body"])))
        if c >= 0.2:
            dense.append((c, r["id"]))
    dense.sort(key=lambda x: (-x[0], x[1]))
    dense = dense[:200]
    fused = {}
    for ranked in (lex_rank, dense):
        for i, (_, rid) in enumerate(ranked, start=1):
            fused[rid] = fused.get(rid, 0.0) + 1.0 / (60 + i)
    return sorted(fused.items(), key=lambda x: (-x[1], x[0]))[:k]
