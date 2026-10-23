"""WP-E15 visible-set retrieval: access pre-filter, visible-set statistics, exit check."""
from __future__ import annotations

import json
import logging
import math
import sqlite3
from collections import Counter
from dataclasses import dataclass

from e15store.embedder import embed, tokens

__all__ = ["Retriever", "Hit", "VisibleSet"]

log = logging.getLogger("vretrieval")

K1, B = 1.2, 0.75
RRF_K = 60
DENSE_MIN = 0.2
CHANNEL_MAX = 200
SNIPPET_LEN = 120


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: str | None
    groups: frozenset[str]


@dataclass(frozen=True)
class Hit:
    id: str
    version: int
    title: str
    snippet: str
    score: float


def _valid_groups(store, person_id: str, tenant: str) -> frozenset[str]:
    out = set()
    for gid in store.membership_rows(person_id):
        g = store.group(gid)
        if g is not None and g["tenant"] == tenant:
            out.add(gid)
    return frozenset(out)


def _snippet(body: str) -> str:
    return body[:SNIPPET_LEN]


class Retriever:
    def __init__(self, store):
        self.store = store
        self.rebuild()

    # ------------------------------------------------------------ visibility
    # DECISION: ADR-007
    def visible_set(self, principal_id) -> VisibleSet:
        """Resolved from the store on every call; never cached."""
        empty = VisibleSet(principal_id if isinstance(principal_id, str) else "", None, frozenset())
        if not isinstance(principal_id, str):
            return empty
        st = self.store
        p = st.principal(principal_id)
        if p is None or p["status"] != "active":
            return empty
        if p["kind"] == "person":
            return VisibleSet(principal_id, p["tenant"], _valid_groups(st, principal_id, p["tenant"]))
        # Agent: delegated access of the person it acts for, limited by the
        # agent's own membership rows (intersection = fail closed; see questions.json).
        owner = st.principal(p["acts_for"]) if p["acts_for"] else None
        if owner is None or owner["status"] != "active" or owner["kind"] != "person" \
                or owner["tenant"] != p["tenant"]:
            return empty
        groups = _valid_groups(st, owner["id"], owner["tenant"]) & _valid_groups(st, principal_id, p["tenant"])
        return VisibleSet(principal_id, owner["tenant"], groups)

    def _readable(self, rec: dict | None, vs: VisibleSet) -> bool:
        # DECISION: ADR-007
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    def get(self, record_id, principal_id):
        try:
            vs = self.visible_set(principal_id)
            if not vs.groups or not isinstance(record_id, str):
                return None
            rec = self.store.current(record_id)
            return rec if self._readable(rec, vs) else None
        except Exception:
            return None

    # ----------------------------------------------------------------- index
    def rebuild(self) -> None:
        c = self.store.conn
        c.executescript("""
            DROP TABLE IF EXISTS vr_docs;
            DROP TABLE IF EXISTS vr_terms;
            CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,
                                 acl_group TEXT NOT NULL, length INTEGER NOT NULL, vec TEXT NOT NULL);
            CREATE TABLE vr_terms(id TEXT NOT NULL, term TEXT NOT NULL, tf INTEGER NOT NULL,
                                  PRIMARY KEY(id, term));
            CREATE INDEX vr_terms_term ON vr_terms(term);
        """)
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def _index(self, rec: dict) -> None:
        c = self.store.conn
        c.execute("DELETE FROM vr_docs WHERE id = ?", (rec["id"],))
        c.execute("DELETE FROM vr_terms WHERE id = ?", (rec["id"],))
        if rec["state"] != "active":
            return
        toks = tokens(rec["title"] + " " + rec["body"])
        c.execute("INSERT INTO vr_docs VALUES (?,?,?,?,?,?)",
                  (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks),
                   json.dumps(embed(rec["title"] + "\n" + rec["body"]))))
        c.executemany("INSERT INTO vr_terms VALUES (?,?,?)",
                      [(rec["id"], t, n) for t, n in Counter(toks).items()])

    def refresh(self, record_id) -> None:
        rec = self.store.current(record_id)
        if rec is None:
            self.store.conn.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
            self.store.conn.execute("DELETE FROM vr_terms WHERE id = ?", (record_id,))
        else:
            self._index(rec)
        self.store.conn.commit()

    # ---------------------------------------------------------------- search
    def search(self, query, principal_id, k=10) -> list[Hit]:
        hits = self._search(query, principal_id, k)
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query, principal_id, k) -> list[Hit]:
        try:
            if not isinstance(query, str) or not isinstance(k, int) or k <= 0:
                return []
            qtokens = tokens(query)
            if not qtokens:
                return []
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return []
            c = self.store.conn
            # Pre-filter: only indexed docs in the requester's tenant and groups.
            marks = ",".join("?" * len(vs.groups))
            rows = c.execute(
                f"SELECT id, version, length, vec FROM vr_docs WHERE tenant = ? AND acl_group IN ({marks})",
                (vs.tenant, *sorted(vs.groups))).fetchall()
            # Exit check: drop anything stale or no longer readable before statistics and ranking.
            # DECISION: ADR-007
            docs, recs = {}, {}
            for did, ver, length, vec in rows:
                rec = self.store.current(did)
                if self._readable(rec, vs) and rec["version"] == ver:
                    docs[did] = (length, vec)
                    recs[did] = rec
            if not docs:
                return []

            # DECISION: ADR-006
            # Statistics over the requester's visible, valid documents only.
            n_docs = len(docs)
            avgdl = sum(d[0] for d in docs.values()) / n_docs
            uq = sorted(set(qtokens))
            tq = ",".join("?" * len(uq))
            ids = list(docs)
            tf: dict[str, dict[str, int]] = {t: {} for t in uq}
            for i in range(0, len(ids), 500):
                chunk = ids[i:i + 500]
                ci = ",".join("?" * len(chunk))
                for did, term, n in c.execute(
                        f"SELECT id, term, tf FROM vr_terms WHERE term IN ({tq}) AND id IN ({ci})",
                        (*uq, *chunk)):
                    tf[term][did] = n
            bm25: dict[str, float] = {}
            for t in qtokens:  # repeated query terms count repeatedly
                postings = tf[t]
                if not postings:
                    continue
                df = len(postings)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                for did, f in postings.items():
                    dl = docs[did][0]
                    bm25[did] = bm25.get(did, 0.0) + idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / avgdl))
            lex = [(d, s) for d, s in bm25.items() if s > 0]

            qv = embed(query)
            dense = []
            for did, (_, vec) in docs.items():
                s = sum(a * b for a, b in zip(qv, json.loads(vec)))
                if s >= DENSE_MIN:
                    dense.append((did, s))

            # DECISION: ADR-005
            fused: dict[str, float] = {}
            for chan in (lex, dense):
                chan.sort(key=lambda x: (-x[1], x[0]))
                for rank, (did, _) in enumerate(chan[:CHANNEL_MAX], start=1):
                    fused[did] = fused.get(did, 0.0) + 1.0 / (RRF_K + rank)
            order = sorted(fused.items(), key=lambda x: (-x[1], x[0]))[:k]
            return [Hit(id=d, version=recs[d]["version"], title=recs[d]["title"],
                        snippet=_snippet(recs[d]["body"]), score=float(s))
                    for d, s in order]
        except Exception:
            log.exception("search failed")
            return []
