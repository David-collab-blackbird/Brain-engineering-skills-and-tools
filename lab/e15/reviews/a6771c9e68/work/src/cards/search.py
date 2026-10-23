"""Entity linking (R7) and BM25 ranking (R8, R10)."""
from __future__ import annotations

import math
from collections import Counter

from factstore.text import tokens

K1 = 1.2
B = 0.75


def link_entities(store, request_tokens: list[str], tenant: str) -> list[str]:
    """Entity ids linked from the request, ordered by first match position then id.

    Only entities of `tenant` take part. Matches are chosen longest first (equal length: lower entity id,
    then earlier position); a match that overlaps an already chosen one is not linked from that position.
    """
    matches = []
    for e in store.entities():
        if e["tenant"] != tenant:
            continue
        for name in (e["name"], *store.aliases(e["id"])):
            name_tokens = tokens(name)
            n = len(name_tokens)
            if n == 0:
                continue
            for start in range(len(request_tokens) - n + 1):
                if request_tokens[start:start + n] == name_tokens:
                    matches.append((n, e["id"], start))
    matches.sort(key=lambda m: (-m[0], m[1], m[2]))
    taken = [False] * len(request_tokens)
    first: dict[str, int] = {}
    for n, entity_id, start in matches:
        if any(taken[start:start + n]):
            continue
        for i in range(start, start + n):
            taken[i] = True
        first[entity_id] = min(start, first.get(entity_id, start))
    return sorted(first, key=lambda eid: (first[eid], eid))


def bm25_rank(docs: list[tuple[str, str]], query_tokens: list[str]) -> list[str]:
    """Note ids that match at least one query term, best first (ties: id ascending).

    `docs` must already be restricted to what the requester may see: the statistics (document count, document
    frequencies, average length) are computed over exactly these documents and nothing else.
    """
    terms = sorted(set(query_tokens))
    if not docs or not terms:
        return []
    tf = {nid: Counter(tokens(text)) for nid, text in docs}
    length = {nid: sum(c.values()) for nid, c in tf.items()}
    n_docs = len(docs)
    avgdl = sum(length.values()) / n_docs
    if avgdl == 0:
        return []
    df = {t: sum(1 for c in tf.values() if t in c) for t in terms}
    scored = []
    for nid, counts in tf.items():
        score = 0.0
        for t in terms:                     # fixed term order: identical documents get identical scores
            f = counts.get(t, 0)
            if f == 0:
                continue
            idf = math.log(1.0 + (n_docs - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * f * (K1 + 1.0) / (f + K1 * (1.0 - B + B * length[nid] / avgdl))
        if score > 0.0:
            scored.append((-score, nid))
    scored.sort()
    return [nid for _, nid in scored]
