"""WP-E15 visible-set retrieval: access pre-filter, visible-set statistics, exit check."""
from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass

from e15store.embedder import embed, tokens

__all__ = ["Retriever", "Hit", "VisibleSet"]

log = logging.getLogger("vretrieval")

K1, B = 1.2, 0.75
RRF_K = 60
CHANNEL_CAP = 200
COSINE_MIN = 0.2
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


def _person_groups(store, person: dict) -> frozenset[str]:
    out = set()
    for gid in store.membership_rows(person["id"]):
        g = store.group(gid)
        if g is not None and g["tenant"] == person["tenant"]:
            out.add(gid)
    return frozenset(out)


class Retriever:
    def __init__(self, store):
        self.store = store
        self.rebuild()

    # ------------------------------------------------------------ visible set
    # DECISION: ADR-007
    def visible_set(self, principal_id: str) -> VisibleSet:
        """Resolved from the store on every call; never cached."""
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            p = self.store.principal(principal_id)
        except Exception:
            return empty
        if p is None or p["status"] != "active":
            return empty
        if p["kind"] == "person":
            return VisibleSet(p["id"], p["tenant"], _person_groups(self.store, p))
        # Agent: delegated access, fail closed. The brief says an agent has the
        # person's access, yet its own membership rows exist to limit it; until
        # the owner answers (build/questions.json) use the intersection.
        owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
        if (owner is None or owner["kind"] != "person" or owner["status"] != "active"
                or owner["tenant"] != p["tenant"]):
            return VisibleSet(p["id"], p["tenant"], frozenset())
        groups = _person_groups(self.store, owner) & _person_groups(self.store, p)
        return VisibleSet(p["id"], p["tenant"], groups)

    @staticmethod
    def _visible(vs: VisibleSet, rec: dict | None) -> bool:
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    def get(self, record_id, principal_id) -> dict | None:
        try:
            vs = self.visible_set(principal_id)
            rec = self.store.current(record_id)
        except Exception:
            return None
        return rec if self._visible(vs, rec) else None

    # ------------------------------------------------------------------ index
    def rebuild(self) -> None:
        c = self.store.conn
        c.execute("DROP TABLE IF EXISTS vr_docs")
        c.execute("CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,"
                  " acl_group TEXT NOT NULL, len INTEGER NOT NULL, tf TEXT NOT NULL, vec TEXT NOT NULL)")
        for rec in self.store.current_records():
            self._index_safe(rec)
        c.commit()

    def refresh(self, record_id: str) -> None:
        self.store.conn.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        self._index_safe(self.store.current(record_id))
        self.store.conn.commit()

    def _index_safe(self, rec: dict | None) -> None:
        try:
            self._index(rec)
        except Exception:
            log.warning("could not index a record")  # skipped, never indexed

    def _index(self, rec: dict | None) -> None:
        if rec is None or rec["state"] != "active":
            return
        toks = tokens(rec["title"] + " " + rec["body"])
        self.store.conn.execute(
            "INSERT OR REPLACE INTO vr_docs VALUES (?,?,?,?,?,?,?)",
            (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks),
             json.dumps(Counter(toks)), json.dumps(embed(rec["title"] + "\n" + rec["body"]))))

    # ----------------------------------------------------------------- search
    def search(self, query, principal_id, k=5) -> list[Hit]:
        hits = self._search(query, principal_id, k)
        log.info("search principal=%r hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query, principal_id, k) -> list[Hit]:
        try:
            qtoks = tokens(query) if isinstance(query, str) else []
            if not qtoks or not isinstance(k, int) or k <= 0:
                return []
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return []
            # Pre-filter: only docs visible now (live ACL/state, indexed version is current).
            live = {r["id"]: r for r in self.store.current_records()}
            docs = []
            stale = []
            for id_, ver, tf, ln, vec in self.store.conn.execute(
                    "SELECT id, version, tf, len, vec FROM vr_docs WHERE tenant = ?", (vs.tenant,)):
                rec = live.get(id_)
                if self._visible(vs, rec) and rec["version"] == ver:
                    docs.append((id_, json.loads(tf), ln, json.loads(vec)))
                elif rec is None or rec["state"] != "active":
                    stale.append(id_)
            if stale:  # purge derived copies of erased/quarantined records
                self.store.conn.executemany("DELETE FROM vr_docs WHERE id = ?", [(i,) for i in stale])
                self.store.conn.commit()
            if not docs:
                return []

            # DECISION: ADR-006  statistics over the requester's visible docs only
            n = len(docs)
            avgdl = sum(d[2] for d in docs) / n
            uq = sorted(set(qtoks))
            df = {t: sum(1 for d in docs if t in d[1]) for t in uq}
            lex = []
            for id_, tf, ln, _ in docs:
                s = 0.0
                for t in uq:
                    f = tf.get(t, 0)
                    if f:
                        idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                        s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * ln / avgdl))
                if s > 0:
                    lex.append((-s, id_))
            qv = embed(query)
            dense = []
            for id_, _, _, vec in docs:
                cos = sum(a * b for a, b in zip(qv, vec))
                if cos >= COSINE_MIN:
                    dense.append((-cos, id_))

            # DECISION: ADR-005  reciprocal rank fusion, ties by id ascending
            fused: dict[str, float] = {}
            for chan in (lex, dense):
                for rank, (_, id_) in enumerate(sorted(chan)[:CHANNEL_CAP], start=1):
                    fused[id_] = fused.get(id_, 0.0) + 1.0 / (RRF_K + rank)
            ordered = sorted(fused.items(), key=lambda x: (-x[1], x[0]))

            # DECISION: ADR-007  exit check against the store, using this request's visible set
            indexed = {d[0] for d in docs}
            out = []
            for id_, score in ordered:
                rec = self.store.current(id_)
                if id_ not in indexed or not self._visible(vs, rec):
                    continue
                out.append(Hit(rec["id"], rec["version"], rec["title"],
                               rec["body"][:SNIPPET_LEN], float(score)))
                if len(out) == k:
                    break
            return out
        except Exception:
            log.exception("search failed")  # no query text, no content
            return []
