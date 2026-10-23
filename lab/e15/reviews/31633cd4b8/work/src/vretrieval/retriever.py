"""The Retriever (WP-E15): the public interface that ties the parts together."""
from __future__ import annotations

import logging
import operator

import e15store

from .access import exit_check, id_text, is_storable_id, read_visible, resolve_visible_set
from .index import Index
from .models import Hit, VisibleSet
from .ranking import dense_ranking, fuse, lexical_ranking, make_snippet

# The brief says both "top 5 by default" (Done line) and k=10 (Interface block).
# The Done line is the acceptance criterion, so 5 it is; see build/questions.json.
DEFAULT_K = 5

# R9: one INFO record per search, on this exact logger name.
audit = logging.getLogger("vretrieval")


# Characters that end a line (the ones str.splitlines splits on): an id containing one must not
# be able to start a second, forged line in a text log.
_LINE_BREAKS = {cp: "\\x%02x" % cp if cp < 0x100 else "\\u%04x" % cp
                for cp in (0x0A, 0x0B, 0x0C, 0x0D, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029)}


def _loggable(value) -> str:
    """The id as text for the log line: verbatim, except that line breaks and characters no encoding can write are escaped."""
    return id_text(value).translate(_LINE_BREAKS).encode("utf-8", "backslashreplace").decode("utf-8")


class Retriever:
    """Searches one RecordStore for one requester at a time.

    Constructing it (re)builds the vr_* index tables in the store's connection from the
    store's current active records, replacing any index a previous Retriever on the same
    store built. The store stays the truth: who may see what, and the text returned,
    are always read from it. Only content can be stale. A record added, replaced by a
    newer version or restored from quarantine after the index was built is not found until
    refresh(record_id) or rebuild(); a record erased, quarantined, reclassified or
    revoked since is never returned, with no refresh.
    """

    def __init__(self, store):
        self._store = store
        self._index = Index(store)
        self._index.rebuild()

    # ----------------------------------------------------------------- access
    # DECISION: ADR-007
    def visible_set(self, principal_id) -> VisibleSet:
        """What this requester may see, resolved from the store on every call."""
        return resolve_visible_set(self._store, principal_id)

    # DECISION: ADR-007
    def get(self, record_id, principal_id) -> dict | None:
        """The current version of a record if it is active and visible, else None (R7)."""
        return read_visible(self._store, self.visible_set(principal_id), record_id)

    # ----------------------------------------------------------------- search
    def search(self, query, principal_id, k: int = DEFAULT_K) -> list[Hit]:
        """The top k records this requester may see for the query, best first.

        Never raises for a query string, an unknown principal or an empty store.
        Logs one INFO record: the principal id and how many hits were returned.
        """
        k = operator.index(k)  # a programming error (not an integer) is the only way to raise
        hits = self._search(query, principal_id, k)
        audit.info("search principal=%s hits=%d", _loggable(principal_id), len(hits),
                   extra={"principal_id": principal_id, "hit_count": len(hits)})
        return hits

    def _search(self, query, principal_id, k: int) -> list[Hit]:
        if k <= 0 or not isinstance(query, str):
            return []
        terms = list(dict.fromkeys(e15store.tokens(query)))  # R1: distinct terms, query order
        if not terms:
            return []

        # DECISION: ADR-007
        visible = self.visible_set(principal_id)
        docs = self._index.visible_docs(visible.tenant, visible.groups) if visible.groups else {}
        if not docs:
            return []

        # DECISION: ADR-006
        # Both channels see the visible records only (R3), and the lexical statistics are
        # taken from them alone (R4): `docs` and the postings below hold nothing else.
        lexical = lexical_ranking(
            terms,
            {record_id: doc.length for record_id, doc in docs.items()},
            self._index.postings(terms, docs))
        dense = dense_ranking(
            e15store.embed(query),
            {record_id: doc.vector for record_id, doc in docs.items()})

        # DECISION: ADR-005
        fused = fuse([[record_id for record_id, _ in lexical], [record_id for record_id, _ in dense]])

        hits: list[Hit] = []
        for record_id, score in fused:
            # DECISION: ADR-007
            # Second line of defence (the first is the store read in visible_docs): re-read the
            # record from the store, which is also where the returned text comes from.
            current = exit_check(self._store, visible, record_id, docs[record_id].version)
            if current is None:
                continue  # dropped: the next-best candidate takes its place
            hits.append(Hit(
                id=current["id"],
                version=current["version"],
                title=current["title"],
                snippet=make_snippet(current["body"], terms),
                score=score))
            if len(hits) == k:
                break
        return hits

    # ------------------------------------------------------------------ index
    def refresh(self, record_id) -> None:
        """Re-index one record from the store, or drop it if it is no longer active."""
        if is_storable_id(record_id):
            self._index.refresh(record_id)

    def rebuild(self) -> None:
        """Drop the index and build it again from the store."""
        self._index.rebuild()
