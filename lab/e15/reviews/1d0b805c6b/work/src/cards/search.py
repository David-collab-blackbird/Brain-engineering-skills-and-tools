"""Request linking (R7) and lexical search over the requester's visible notes (R8, R10)."""
from __future__ import annotations

import math
from collections import Counter

from factstore.text import tokens

K1 = 1.2
B = 0.75

_NOTE_COLS = ("id", "tenant", "acl_group", "text", "state")


def link_entities(store, tenant, request_tokens: list[str]) -> list[str]:
    """Entity ids linked from a request, in the order they are pinned (R7).

    An entity is linked when the tokens of its canonical name or of any alias occur as a
    contiguous run in the request's tokens. Only entities of ``tenant`` are looked at: other
    tenants' entity rows are never read. Overlapping matches are resolved greedily, longest
    first (equal length: lower entity id, then earlier position), and a match that overlaps
    one already kept is dropped, so with entities "north star" and "north star cafe" the request
    "north star cafe menu" links the longer one only. A run of no tokens never matches.
    Result order: first kept match position, then id.
    """
    if tenant is None or not request_tokens:
        return []
    n = len(request_tokens)
    found: list[tuple[int, str, int]] = []          # (-length, entity id, start)
    for entity_id, name in store.conn.execute(
            "SELECT id, name FROM entities WHERE tenant = ? ORDER BY id", (tenant,)).fetchall():
        for label in [name, *store.aliases(entity_id)]:
            run = tokens(label)
            if not run or len(run) > n:
                continue
            for start in range(n - len(run) + 1):
                if request_tokens[start:start + len(run)] == run:
                    found.append((-len(run), entity_id, start))
    found.sort()
    taken = bytearray(n)                            # taken[i] set: request token i belongs to a kept match
    first: dict[str, int] = {}
    for neg_length, entity_id, start in found:
        end = start - neg_length
        if any(taken[start:end]):
            continue
        taken[start:end] = b"\x01" * (end - start)
        first[entity_id] = min(start, first.get(entity_id, start))
    return [entity_id for entity_id, _ in sorted(first.items(), key=lambda kv: (kv[1], kv[0]))]


# DECISION: ADR-007
# Access is a pre-filter: a note is read only if it is active, in the requester's tenant and in
# one of the requester's visible groups. Hidden notes are never loaded, so nothing computed
# below can depend on them (R10).
def visible_active_notes(store, visible) -> list[dict]:
    if visible.tenant is None:
        return []
    notes = []
    for group in sorted(visible.groups):
        for row in store.conn.execute(
                "SELECT id, tenant, acl_group, text, state FROM notes "
                "WHERE tenant = ? AND acl_group = ? AND state = 'active' ORDER BY id", (visible.tenant, group)):
            notes.append(dict(zip(_NOTE_COLS, row)))
    notes.sort(key=lambda note: note["id"])
    return notes


def rank_notes(notes: list[dict], query_tokens: list[str]) -> list[str]:
    """Note ids that match the query, best first, by BM25 (k1 = 1.2, b = 0.75). Ties: note id ascending.

    R10 / ADR-006: every statistic (document count, document frequencies, average length) is
    computed over ``notes`` alone, and the caller passes only the requester's visible active
    notes, so a note the requester cannot see cannot move any score. A note that shares no term
    with the query is not "found" and is never returned.
    """
    terms = sorted(set(query_tokens))         # sorted: float sums must not depend on hash order
    if not notes or not terms:
        return []
    docs = []
    for note in notes:
        words = tokens(note["text"])
        docs.append((note["id"], Counter(words), len(words)))
    count = len(docs)
    avg_length = sum(length for _, _, length in docs) / count
    if avg_length == 0:
        return []
    df = {t: sum(1 for _, tf, _ in docs if t in tf) for t in terms}
    idf = {t: math.log(1 + (count - df[t] + 0.5) / (df[t] + 0.5)) for t in terms}
    scored = []
    for note_id, tf, length in docs:
        score = 0.0
        for t in terms:
            freq = tf.get(t, 0)
            if freq:
                score += idf[t] * freq * (K1 + 1) / (freq + K1 * (1 - B + B * length / avg_length))
        if score > 0:
            scored.append((-round(score, 12), note_id))     # rounding: mathematically equal scores tie
    scored.sort()
    return [note_id for _, note_id in scored]
