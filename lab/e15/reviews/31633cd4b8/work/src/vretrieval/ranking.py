"""The two first-stage channels, fusion and snippets (R5, R6).

Every function here is handed only records the requester may see, and works
out its statistics from exactly what it is handed.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Collection, Mapping, Sequence

import e15store

# R5 constants.
BM25_K1 = 1.2
BM25_B = 0.75
DENSE_MIN_COSINE = 0.2
CHANNEL_CAP = 200
RRF_K = 60

SNIPPET_CHARS = 120
# Words of the raw body, for placing a snippet: the tokeniser's own pattern (\w+) plus the
# combining-mark blocks, so a decomposed "cafe" + U+0301 is one word, as it is after the
# tokeniser's NFKC step, and is found like its composed form.
_WORD = re.compile("(?:\\w|[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f])+")


# Two scores that are equal in exact arithmetic can differ in the last bit when they are
# reached by different routes (a different term frequency, a different order of additions),
# and that noise must not decide the order. Scores within this relative distance are ties.
_TIE_TOLERANCE = 1e-12


def _settle_ties(by_score: Sequence[tuple[str, float]]) -> list[tuple[str, float]]:
    """Order ties by record id ascending (R5), never by storage order or float noise.

    `by_score` is sorted by descending score. Each run of scores within
    _TIE_TOLERANCE of the run's first becomes one score (the run's highest, so
    the list stays exactly non-increasing) with its records in id order.
    """
    settled: list[tuple[str, float]] = []
    start = 0
    while start < len(by_score):
        top = by_score[start][1]
        end = start + 1
        while end < len(by_score) and top - by_score[end][1] <= _TIE_TOLERANCE * abs(top):
            end += 1
        settled.extend((record_id, top) for record_id, _ in sorted(by_score[start:end]))
        start = end
    return settled


def _best_first(scores: Mapping[str, float]) -> list[tuple[str, float]]:
    """Highest score first; ties by record id ascending, never by storage order (R5)."""
    return _settle_ties(sorted(scores.items(), key=lambda item: -item[1]))[:CHANNEL_CAP]


# DECISION: ADR-006
def lexical_ranking(
    terms: Sequence[str],
    lengths: Mapping[str, int],
    postings: Mapping[str, Mapping[str, int]],
) -> list[tuple[str, float]]:
    """BM25 over the visible records, best first, at most CHANNEL_CAP (R5).

    `lengths` holds the token count of every visible record, and `postings`
    maps each query term to {record id: term frequency} for visible records
    only. The document count, the average length and each term's document
    frequency are taken from those and from nothing else, so a record the
    requester cannot see has no way to move a score.

    The idf is ln(1 + (N - df + 0.5) / (df + 0.5)), which is positive for every
    term that occurs, so the candidates (BM25 > 0) are exactly the visible
    records that contain at least one query term. Each distinct query term
    counts once, however often `terms` repeats it.
    """
    # DECISION: ADR-006
    doc_count = len(lengths)
    if doc_count == 0:
        return []
    average_length = sum(lengths.values()) / doc_count

    scores: dict[str, float] = {}
    for term in dict.fromkeys(terms):
        frequencies = postings.get(term)
        if not frequencies:
            continue
        doc_frequency = len(frequencies)  # over the visible records only
        idf = math.log(1.0 + (doc_count - doc_frequency + 0.5) / (doc_frequency + 0.5))
        for record_id, tf in frequencies.items():
            norm = BM25_K1 * (1.0 - BM25_B + BM25_B * lengths[record_id] / average_length)
            scores[record_id] = scores.get(record_id, 0.0) + idf * tf * (BM25_K1 + 1.0) / (tf + norm)
    return _best_first(scores)


def _norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in vector))


def dense_ranking(
    query_vector: Sequence[float],
    vectors: Mapping[str, Sequence[float]],
) -> list[tuple[str, float]]:
    """Exact cosine against every visible record, best first (R5).

    Candidates are the records with cosine >= DENSE_MIN_COSINE, at most
    CHANNEL_CAP. Each cosine depends on the query and one record only.
    """
    # Norms are worked out here, not assumed to be 1: stored vectors are unit length only up to
    # rounding, and this keeps the result the exact cosine for any vector.
    query_norm = _norm(query_vector)
    if query_norm == 0.0:
        return []
    scores: dict[str, float] = {}
    for record_id, vector in vectors.items():
        vector_norm = _norm(vector)
        if vector_norm == 0.0:
            continue
        dot = sum(a * b for a, b in zip(query_vector, vector))
        cosine = dot / (query_norm * vector_norm)
        if cosine >= DENSE_MIN_COSINE:
            scores[record_id] = cosine
    return _best_first(scores)


# DECISION: ADR-005
def fuse(rankings: Sequence[Sequence[str]]) -> list[tuple[str, float]]:
    """Reciprocal rank fusion of the channels' rankings (R5).

    Each ranking lists record ids best first. A record scores the sum over the
    rankings it appears in of 1 / (60 + rank) (RRF_K = 60), with rank starting
    at 1, and gets nothing from a ranking it is missing from. Best first; ties
    by record id ascending. Nothing is cut here: the exit check may drop
    candidates and the next-best ones must be there to replace them.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, record_id in enumerate(ranking, start=1):
            scores[record_id] = scores.get(record_id, 0.0) + 1.0 / (RRF_K + rank)  # DECISION: ADR-005
    return _settle_ties(sorted(scores.items(), key=lambda item: -item[1]))


def make_snippet(body: str, terms: Collection[str]) -> str:
    """The SNIPPET_CHARS-character part of `body` that best matches the query.

    That is the first SNIPPET_CHARS characters, unless a later window of the
    same length contains strictly more distinct query terms; the earliest window
    with the most terms wins. So a record that matches only through its title or
    through words that all sit in the first window gets exactly the first
    SNIPPET_CHARS characters of the body, and a body that is short enough is
    returned whole. A window that would run past the end of the body is moved
    back so that it is always a full SNIPPET_CHARS long; a window may therefore
    begin in the middle of a word.
    """
    if len(body) <= SNIPPET_CHARS:
        return body
    wanted = set(terms)
    spans: list[tuple[int, int, list[str]]] = []  # (start, end, query terms in this word)
    for word in _WORD.finditer(body):
        matched = [t for t in e15store.tokens(word.group()) if t in wanted]
        if matched:
            spans.append((word.start(), word.end(), matched))
    if not spans:
        return body[:SNIPPET_CHARS]

    last_start = len(body) - SNIPPET_CHARS  # the latest start that still gives a full window
    best_start, best_cover = 0, -1
    inside: Counter[str] = Counter()  # query terms in spans[low:high], i.e. in the window
    low = high = 0
    for start in sorted({0, *(min(span[0], last_start) for span in spans)}):
        while low < len(spans) and spans[low][0] < start:  # words that begin before the window
            if low < high:
                for term in spans[low][2]:
                    inside[term] -= 1
                    if not inside[term]:
                        del inside[term]
            low += 1
        high = max(high, low)
        while high < len(spans) and spans[high][1] <= start + SNIPPET_CHARS:  # words that end inside it
            for term in spans[high][2]:
                inside[term] += 1
            high += 1
        if len(inside) > best_cover:
            best_start, best_cover = start, len(inside)
    return body[best_start:best_start + SNIPPET_CHARS]
