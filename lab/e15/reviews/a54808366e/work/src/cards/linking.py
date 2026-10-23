"""Entity linking (R7): which entities does a request name?

Pure functions over token lists. The caller supplies only entities of the
requester's tenant, so nothing here can link across tenants.
"""
from __future__ import annotations


def link_entities(request_tokens: list[str], entities) -> list[str]:
    """Entity ids named in the request, ordered by first match position then id.

    ``entities`` is an iterable of ``(entity_id, terms)`` where each term is the
    token list of the canonical name or of one alias. A term matches where its
    tokens occur as a contiguous run in the request. When matches overlap the
    longer wins; at equal length the lower entity id wins; an entity that loses
    a position is not linked from that position (it can still be linked from a
    separate, non-overlapping match).
    """
    n = len(request_tokens)
    by_first_token: dict[str, list[tuple[str, list[str]]]] = {}
    for entity_id, terms in entities:
        for term in terms:
            if term:
                by_first_token.setdefault(term[0], []).append((entity_id, term))

    matches = []                                  # (length, entity id, start)
    for start, token in enumerate(request_tokens):
        for entity_id, term in by_first_token.get(token, ()):
            m = len(term)
            if start + m <= n and request_tokens[start:start + m] == term:
                matches.append((m, entity_id, start))

    matches.sort(key=lambda t: (-t[0], t[1], t[2]))
    taken = [False] * n
    first: dict[str, int] = {}
    for m, entity_id, start in matches:
        if any(taken[start:start + m]):
            continue
        for i in range(start, start + m):
            taken[i] = True
        if entity_id not in first or start < first[entity_id]:
            first[entity_id] = start
    return sorted(first, key=lambda e: (first[e], e))
