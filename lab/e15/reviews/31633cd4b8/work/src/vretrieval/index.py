"""The index: two tables named vr_* inside the store's own connection (R8).

    vr_docs      one row per indexed record: id, the version that was indexed,
                 the document length in tokens, and the dense vector
    vr_postings  one row per (token, record): the term frequency

The index holds no title or body text and no access information, only each record's
distinct tokens with their counts, its length and its vector. Who may see a record is
always read from the store at query time, so a reclassification or erasure
takes effect on the next call even if the index is stale. What can be stale is
only the content: a record whose current version is newer than the indexed one
is left out of results until `refresh` or `rebuild` re-indexes it.

Only active records are indexed (erased and quarantined are never indexed).
The store's own tables are only ever read.
"""
from __future__ import annotations

import struct
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, Iterator

import e15store

_VECTOR = struct.Struct(f"<{e15store.DIM}d")

# Bound parameters per statement. SQLite allows at least 999 (32766 since 3.32).
_BATCH = 500

_SCHEMA = (
    "CREATE TABLE vr_docs ("
    " id TEXT PRIMARY KEY, version INTEGER NOT NULL, dl INTEGER NOT NULL, vec BLOB NOT NULL"
    ") WITHOUT ROWID",
    "CREATE TABLE vr_postings ("
    " token TEXT NOT NULL, id TEXT NOT NULL, tf INTEGER NOT NULL, PRIMARY KEY (token, id)"
    ") WITHOUT ROWID",
    "CREATE INDEX vr_postings_by_id ON vr_postings (id)",
)


@dataclass(frozen=True)
class IndexedDoc:
    """What the index knows about one record: enough to score it, nothing to show."""

    version: int
    length: int
    vector: tuple[float, ...]


def _batches(items: list) -> Iterator[list]:
    for start in range(0, len(items), _BATCH):
        yield items[start:start + _BATCH]


@contextmanager
def _atomic(conn):
    """All or nothing, so a failed re-index never leaves half an index behind.

    Inside a transaction the caller already holds, a savepoint is used instead, so a
    failure is undone without touching the caller's own work (or committing it).
    """
    if conn.in_transaction:
        conn.execute("SAVEPOINT vr_atomic")
        try:
            yield
        except BaseException:
            conn.execute("ROLLBACK TO vr_atomic")
            conn.execute("RELEASE vr_atomic")
            raise
        conn.execute("RELEASE vr_atomic")
        return
    conn.execute("BEGIN")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


class Index:
    """The vr_* tables of one store: build, re-index one record, and read back the visible part."""

    def __init__(self, store):
        self._store = store
        self._conn = store.conn

    # ---------------------------------------------------------------- writing
    def rebuild(self) -> None:
        """Drop the index and build it again from the store's current versions."""
        records = [r for r in self._store.current_records() if r["state"] == "active"]
        with _atomic(self._conn):
            self._conn.execute("DROP TABLE IF EXISTS vr_postings")
            self._conn.execute("DROP TABLE IF EXISTS vr_docs")
            for statement in _SCHEMA:
                self._conn.execute(statement)
            for record in records:
                self._insert(record)

    def refresh(self, record_id: str) -> None:
        """Re-index one record from the store, or remove it if it is not active."""
        record = self._store.current(record_id)
        with _atomic(self._conn):
            self._conn.execute("DELETE FROM vr_postings WHERE id = ?", (record_id,))
            self._conn.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
            if record is not None and record["state"] == "active":
                self._insert(record)

    def _insert(self, record: dict) -> None:
        title, body = record["title"], record["body"]
        doc_tokens = e15store.tokens(title + " " + body)  # R1: documents are title + " " + body
        vector = e15store.embed(title + "\n" + body)  # R5: computed here, once, not per query
        self._conn.execute(
            "INSERT INTO vr_docs (id, version, dl, vec) VALUES (?, ?, ?, ?)",
            (record["id"], record["version"], len(doc_tokens), _VECTOR.pack(*vector)))
        self._conn.executemany(
            "INSERT INTO vr_postings (token, id, tf) VALUES (?, ?, ?)",
            [(token, record["id"], tf) for token, tf in Counter(doc_tokens).items()])

    # ---------------------------------------------------------------- reading
    # DECISION: ADR-007
    # DECISION: ADR-006
    def visible_docs(self, tenant: str, groups: Iterable[str]) -> dict[str, IndexedDoc]:
        """The indexed records that are visible right now, by id.

        Visibility is read from the store, not from the index: a record is
        included only if its current version is active, is the version that was
        indexed, belongs to `tenant` and sits in one of `groups`. Nothing else
        is ever loaded, so every later statistic is over these records only.
        """
        docs: dict[str, IndexedDoc] = {}
        for chunk in _batches(sorted(groups)):
            marks = ",".join("?" * len(chunk))
            rows = self._conn.execute(
                "SELECT d.id, d.version, d.dl, d.vec"
                " FROM records AS r JOIN vr_docs AS d ON d.id = r.id AND d.version = r.version"
                " WHERE r.is_current = 1 AND r.state = 'active' AND r.tenant = ?"
                f" AND r.acl_group IN ({marks})",
                [tenant, *chunk])
            for record_id, version, length, blob in rows:
                docs[record_id] = IndexedDoc(version, length, _VECTOR.unpack(blob))
        return docs

    # DECISION: ADR-006
    def postings(self, terms: list[str], visible_ids) -> dict[str, dict[str, int]]:
        """term -> {record id: term frequency}, restricted to the visible records.

        The rows of every record that holds a query term are read, and those of records
        outside `visible_ids` are dropped before anything is counted: document frequencies
        are therefore over the visible records only.
        """
        found: dict[str, dict[str, int]] = {}
        for chunk in _batches(terms):
            marks = ",".join("?" * len(chunk))
            rows = self._conn.execute(
                f"SELECT token, id, tf FROM vr_postings WHERE token IN ({marks})", chunk)
            for token, record_id, tf in rows:
                if record_id in visible_ids:  # rows of records nobody asked for are dropped here
                    found.setdefault(token, {})[record_id] = tf
        return found
