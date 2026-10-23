"""Entity linking (R7) and BM25 over the requester's visible notes (R8, R10)."""
from __future__ import annotations

import math

from factstore.text import tokens

K1 = 1.2
B = 0.75


def link_entities(entities, aliases_of, request_tokens: list[str]) -> list[str]:
    # DECISION: ADR-010
    """Entity ids linked from a request, ordered by first match position then entity id.

    `entities` must already be restricted to the requester's tenant: an entity of another tenant must not take
    part in overlap resolution. A name or alias matches when its tokens occur as a contiguous run in the request.
    Overlaps are resolved globally, longest match first (equal length: lower entity id, then earlier position);
    a losing match does not link its entity from that position.
    """
    matches = []                                         # (-length, entity_id, start)
    for e in entities:
        names = {e["name"], *aliases_of(e["id"])}
        for name in names:
            nt = tokens(name)
            n = len(nt)
            if n == 0:
                continue
            for start in range(len(request_tokens) - n + 1):
                if request_tokens[start:start + n] == nt:
                    matches.append((-n, e["id"], start))
    matches.sort()
    taken = [False] * len(request_tokens)
    first: dict[str, int] = {}
    for neg_len, eid, start in matches:
        end = start - neg_len
        if any(taken[start:end]):
            continue
        for i in range(start, end):
            taken[i] = True
        if eid not in first or start < first[eid]:
            first[eid] = start
    return [eid for eid, _ in sorted(first.items(), key=lambda kv: (kv[1], kv[0]))]


def bm25_rank(docs: list[tuple[str, list[str]]], query_tokens: list[str]) -> list[str]:
    # DECISION: ADR-010
    """Note ids that match the query, best first (BM25, k1=1.2, b=0.75; ties by note id ascending).

    `docs` are (note_id, tokens) of the requester's visible active notes and nothing else: document count,
    document frequencies and average length are computed over exactly these (R10). IDF is the non-negative
    ln(1 + (N - n + 0.5) / (n + 0.5)); each distinct query term counts once. Notes matching no term are not returned.
    """
    terms = sorted(set(query_tokens))
    n_docs = len(docs)
    if not terms or n_docs == 0:
        return []
    avg_len = sum(len(t) for _, t in docs) / n_docs
    if avg_len == 0:
        return []
    counts = []
    df = dict.fromkeys(terms, 0)
    for nid, toks in docs:
        tf: dict[str, int] = {}
        for tok in toks:
            tf[tok] = tf.get(tok, 0) + 1
        counts.append((nid, len(toks), tf))
        for term in terms:
            if term in tf:
                df[term] += 1
    idf = {t: math.log(1.0 + (n_docs - df[t] + 0.5) / (df[t] + 0.5)) for t in terms}
    scored = []
    for nid, dl, tf in counts:
        score = 0.0
        for term in terms:
            f = tf.get(term)
            if f:
                score += idf[term] * f * (K1 + 1.0) / (f + K1 * (1.0 - B + B * dl / avg_len))
        if score > 0.0:
            scored.append((-score, nid))
    scored.sort()
    return [nid for _, nid in scored]
