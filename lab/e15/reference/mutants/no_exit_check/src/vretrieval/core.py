"""Reference implementation of WP-E15 visible-set retrieval."""
from __future__ import annotations

import logging
import math
import re
from array import array
from collections import Counter
from dataclasses import dataclass

from e15store import embed, tokens

log = logging.getLogger("vretrieval")

K1, B = 1.2, 0.75
RRF_K = 60
DEPTH = 200
DENSE_MIN = 0.2
SNIPPET = 120


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: str | None
    groups: frozenset


@dataclass(frozen=True)
class Hit:
    id: str
    version: int
    title: str
    snippet: str
    score: float


class Retriever:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vr_docs(
                id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,
                acl_group TEXT NOT NULL, length INTEGER NOT NULL, vec BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS vr_postings(
                term TEXT NOT NULL, id TEXT NOT NULL, tf INTEGER NOT NULL, PRIMARY KEY (term, id));
            CREATE INDEX IF NOT EXISTS vr_postings_id ON vr_postings(id);
            """
        )
        self.rebuild()

    # ------------------------------------------------------------- index
    def rebuild(self) -> None:
        self.conn.execute("DELETE FROM vr_docs")
        self.conn.execute("DELETE FROM vr_postings")
        for rec in self.store.current_records():
            if rec["state"] == "active":
                self._index(rec)
        self.conn.commit()

    def refresh(self, record_id: str) -> None:
        self.conn.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        self.conn.execute("DELETE FROM vr_postings WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None and rec["state"] == "active":
            self._index(rec)
        self.conn.commit()

    def _index(self, rec: dict) -> None:
        toks = tokens(rec["title"] + " " + rec["body"])
        vec = array("d", embed(rec["title"] + "\n" + rec["body"])).tobytes()
        self.conn.execute(
            "INSERT INTO vr_docs(id, version, tenant, acl_group, length, vec) VALUES (?,?,?,?,?,?)",
            (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks), vec))
        self.conn.executemany(
            "INSERT INTO vr_postings(term, id, tf) VALUES (?,?,?)",
            [(t, rec["id"], n) for t, n in Counter(toks).items()])

    # ------------------------------------------------------- visible set
    def _own_groups(self, p: dict) -> set:
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 resolve per call, fail closed, agents get the intersection
        p = self.store.principal(principal_id) if isinstance(principal_id, str) else None
        if p is None or p["status"] != "active":
            return VisibleSet(str(principal_id), None if p is None else p["tenant"], frozenset())
        groups = self._own_groups(p)
        if p["kind"] == "agent":
            person = self.store.principal(p["acts_for"]) if p["acts_for"] else None
            if (person is None or person["status"] != "active" or person["kind"] != "person"
                    or person["tenant"] != p["tenant"]):
                groups = set()
            else:
                groups &= self._own_groups(person)
        return VisibleSet(p["id"], p["tenant"], frozenset(groups))

    def _visible(self, rec: dict | None, vs: VisibleSet) -> bool:
        # DECISION: ADR-007 visibility of the current version
        return (rec is not None and rec["state"] == "active" and rec["tenant"] == vs.tenant
                and rec["acl_group"] in vs.groups)

    # ------------------------------------------------------------ search
    def search(self, query, principal_id, k: int = 10) -> list[Hit]:
        vs = self.visible_set(principal_id)
        q = tokens(query) if isinstance(query, str) else []
        hits: list[Hit] = []
        if q and vs.groups and k > 0:
            hits = self._search(q, query, vs, k)
        log.info("search principal=%s hits=%d", vs.principal_id, len(hits))
        return hits

    def _search(self, q: list[str], query: str, vs: VisibleSet, k: int) -> list[Hit]:
        gl = sorted(vs.groups)
        ph = ",".join("?" * len(gl))
        docs = {r[0]: r[1:] for r in self.conn.execute(
            f"SELECT id, version, length, vec FROM vr_docs WHERE tenant = ? AND acl_group IN ({ph})",
            [vs.tenant, *gl])}
        if not docs:
            return []
        # DECISION: ADR-006 BM25 statistics over the visible set only
        n_docs = len(docs)
        avgdl = sum(d[1] for d in docs.values()) / n_docs or 1.0
        terms = sorted(set(q))
        tph = ",".join("?" * len(terms))
        tf: dict[str, dict[str, int]] = {}
        for term, rid, n in self.conn.execute(
                f"SELECT term, id, tf FROM vr_postings WHERE term IN ({tph})", terms):
            if rid in docs:
                tf.setdefault(term, {})[rid] = n
        bm25: dict[str, float] = {}
        for term, postings in tf.items():
            df = len(postings)
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            for rid, n in postings.items():
                dl = docs[rid][1]
                bm25[rid] = bm25.get(rid, 0.0) + idf * n * (K1 + 1) / (n + K1 * (1 - B + B * dl / avgdl))
        lex = sorted(((s, rid) for rid, s in bm25.items() if s > 0), key=lambda x: (-x[0], x[1]))[:DEPTH]
        qv = embed(query)
        dense = []
        for rid, (_, _, blob) in docs.items():
            dv = array("d")
            dv.frombytes(blob)
            c = sum(a * b for a, b in zip(qv, dv))
            if c >= DENSE_MIN:
                dense.append((c, rid))
        dense.sort(key=lambda x: (-x[0], x[1]))
        dense = dense[:DEPTH]
        # DECISION: ADR-005 reciprocal rank fusion, k = 60
        fused: dict[str, float] = {}
        for ranked in (lex, dense):
            for rank, (_, rid) in enumerate(ranked, start=1):
                fused[rid] = fused.get(rid, 0.0) + 1.0 / (RRF_K + rank)
        order = sorted(fused.items(), key=lambda x: (-x[1], x[0]))
        # DECISION: ADR-007 exit check against the record store
        out: list[Hit] = []
        for rid, score in order:
            rec = self.store.current(rid)
            if rec is None:
                continue
            out.append(Hit(rid, rec["version"], rec["title"], _snippet(rec["body"], q), score))
            if len(out) == k:
                break
        return out

    # --------------------------------------------------------------- get
    def get(self, record_id, principal_id):
        vs = self.visible_set(principal_id)
        rec = self.store.current(record_id) if isinstance(record_id, str) else None
        return dict(rec) if self._visible(rec, vs) else None


def _snippet(body: str, q: list[str]) -> str:
    best = None
    for t in q:
        m = re.search(re.escape(t), body, re.IGNORECASE)
        if m and (best is None or m.start() < best):
            best = m.start()
    if best is None or best < 40:
        return body[:SNIPPET]
    start = max(0, best - 40)
    return body[start:start + SNIPPET]
