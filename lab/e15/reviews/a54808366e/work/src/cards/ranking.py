"""BM25 over a caller-supplied document set (R8, R10).

The statistics (document count, document frequencies, average length) are
computed from the documents handed in and from nothing else. The caller hands in
only what the requester may see, so rows the requester cannot see never touch a
score. SQLite FTS5's bm25() is deliberately not used: it computes its statistics
over every row of the table.
"""
from __future__ import annotations

import math
from collections import Counter

K1 = 1.2
B = 0.75


def bm25_rank(query_tokens: list[str], docs) -> list[tuple[str, float]]:
    """Rank ``docs`` (an iterable of ``(doc_id, tokens)``) against the query.

    Returns ``(doc_id, score)`` for documents that match at least one query
    term, best first, ties by doc id ascending. IDF is the Lucene form
    ``ln(1 + (N - n + 0.5) / (n + 0.5))``, so it is always positive. A query
    word repeated m times counts m times. The work is linear in the size of the
    documents plus the length of the query, however long the query is.
    """
    wanted = Counter(query_tokens)                        # query term -> how many times it is asked
    docs = [(doc_id, len(toks), Counter(toks)) for doc_id, toks in docs]
    total = len(docs)
    if total == 0 or not wanted:
        return []
    avg_len = sum(length for _, length, _ in docs) / total
    if avg_len == 0:
        return []

    doc_freq = Counter()
    for _, _, tf in docs:
        doc_freq.update(term for term in tf if term in wanted)
    idf = {term: math.log(1.0 + (total - n + 0.5) / (n + 0.5)) for term, n in doc_freq.items()}

    scored = []
    for doc_id, length, tf in docs:
        norm = K1 * (1.0 - B + B * length / avg_len)
        parts = []
        for term, f in tf.items():
            times = wanted.get(term)
            if times:
                part = idf[term] * f * (K1 + 1.0) / (f + norm)
                parts.append(part * times if times > 1 else part)
        # fsum is exact and does not depend on the order of the parts, so two notes whose scores are equal
        # as numbers get the very same float and fall back to the note id (R8: ties by note id ascending).
        score = math.fsum(parts)
        if score > 0.0:
            scored.append((doc_id, score))
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored
