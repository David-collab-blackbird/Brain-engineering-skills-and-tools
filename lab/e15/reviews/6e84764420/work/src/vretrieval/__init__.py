"""WP-E15 visible-set retrieval: access pre-filter, visible-set statistics, exit check."""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass

from e15store.embedder import embed, tokens

log = logging.getLogger("vretrieval")

K1 = 1.2
B = 0.75
RRF_C = 60
CHANNEL_CAP = 200
DENSE_MIN = 0.2
SNIPPET_LEN = 120

__all__ = ["Retriever", "Hit", "VisibleSet"]


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


def _snippet(body: str) -> str:
    return body[:SNIPPET_LEN]


class Retriever:
    def __init__(self, store):
        self.store = store
        self.rebuild()

    # ---------------------------------------------------------------- index
    def rebuild(self) -> None:
        c = self.store.conn
        c.execute("DROP TABLE IF EXISTS vr_docs")
        c.execute(
            "CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,"
            " acl_group TEXT NOT NULL, tokens TEXT NOT NULL, vec TEXT NOT NULL)")
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def _index(self, rec: dict) -> None:
        if rec["state"] != "active":
            return
        text = rec["title"] + " " + rec["body"]
        self.store.conn.execute(
            "INSERT OR REPLACE INTO vr_docs VALUES (?,?,?,?,?,?)",
            (rec["id"], rec["version"], rec["tenant"], rec["acl_group"],
             json.dumps(tokens(text)), json.dumps(embed(rec["title"] + "\n" + rec["body"]))))

    def refresh(self, record_id: str) -> None:
        c = self.store.conn
        c.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None:
            self._index(rec)
        c.commit()

    # ---------------------------------------------------------- visible set
    # DECISION: ADR-007
    def visible_set(self, principal_id: str) -> VisibleSet:
        """Resolved from the store on every call; never cached."""
        empty = VisibleSet(principal_id, None, frozenset())
        p = self.store.principal(principal_id)
        if p is None or p["status"] != "active":
            return empty
        if p["kind"] == "agent":
            # Delegated access, fail closed: the agent's own valid rows limit what
            # it may use, and it can never exceed the person it acts for.
            owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
            if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                    or owner["tenant"] != p["tenant"]):
                return empty
            groups = self._groups(p) & self._groups(owner)
            return VisibleSet(principal_id, p["tenant"], frozenset(groups))
        return VisibleSet(principal_id, p["tenant"], frozenset(self._groups(p)))

    def _groups(self, p: dict) -> set[str]:
        # Only membership rows naming an existing group of the principal's own tenant
        # count. No role/ownership grants (R2a).
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    @staticmethod
    def _visible(vs: VisibleSet, rec: dict | None) -> bool:
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    # ------------------------------------------------------------------ get
    def get(self, record_id, principal_id) -> dict | None:
        try:
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return None
            rec = self.store.current(record_id)
            return rec if self._visible(vs, rec) else None
        except Exception:
            return None

    # --------------------------------------------------------------- search
    def search(self, query, principal_id, k=10) -> list[Hit]:
        hits = self._search(query, principal_id, k)
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query, principal_id, k) -> list[Hit]:
        try:
            if not isinstance(k, int) or k <= 0 or not isinstance(query, str):
                return []
            qtoks = tokens(query)
            if not qtoks:
                return []
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return []
            # Pre-filter: only indexed rows in the visible set and tenant are read.
            marks = ",".join("?" * len(vs.groups))
            rows = self.store.conn.execute(
                f"SELECT id, version, tokens, vec FROM vr_docs WHERE tenant = ? AND acl_group IN ({marks})"
                " ORDER BY id", (vs.tenant, *sorted(vs.groups))).fetchall()
            # Drop stale rows before computing statistics so that nothing the
            # requester cannot see (reclassified, erased, replaced) shapes scores.
            docs = {}
            for rid, ver, tk, vec in rows:
                cur = self.store.current(rid)
                if self._visible(vs, cur) and cur["version"] == ver:
                    docs[rid] = (json.loads(tk), json.loads(vec))
            if not docs:
                return []
            lexical = self._bm25(qtoks, docs)
            qv = embed(query)
            dense = []
            for rid, (_, vec) in docs.items():
                cos = sum(a * b for a, b in zip(qv, vec))
                if cos >= DENSE_MIN:
                    dense.append((-cos, rid))
            dense = [rid for _, rid in sorted(dense)[:CHANNEL_CAP]]
            # DECISION: ADR-005
            fused: dict[str, float] = {}
            for ranking in (lexical, dense):
                for rank, rid in enumerate(ranking, 1):
                    fused[rid] = fused.get(rid, 0.0) + 1.0 / (RRF_C + rank)
            order = sorted(fused, key=lambda r: (-fused[r], r))
            out = []
            for rid in order:
                # Exit check against the store, with this request's visible set.
                # DECISION: ADR-007
                cur = self.store.current(rid)
                if not self._visible(vs, cur) or cur["version"] != self._version(rid, docs, rows):
                    continue
                out.append(Hit(cur["id"], cur["version"], cur["title"],
                               _snippet(cur["body"]), float(fused[rid])))
                if len(out) == k:
                    break
            return out
        except Exception:
            log.exception("search failed")
            return []

    @staticmethod
    def _version(rid, docs, rows):
        for r in rows:
            if r[0] == rid:
                return r[1]
        return None

    @staticmethod
    def _bm25(qtoks, docs) -> list[str]:
        # DECISION: ADR-006
        # N, document frequencies and average length come from visible docs only.
        n = len(docs)
        avgdl = sum(len(t) for t, _ in docs.values()) / n
        qterms = set(qtoks)
        df = {t: 0 for t in qterms}
        for toks, _ in docs.values():
            for t in qterms & set(toks):
                df[t] += 1
        scored = []
        for rid, (toks, _) in docs.items():
            tf: dict[str, int] = {}
            for t in toks:
                if t in qterms:
                    tf[t] = tf.get(t, 0) + 1
            s = 0.0
            for t, f in tf.items():
                idf = math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * len(toks) / avgdl))
            if s > 0:
                scored.append((-s, rid))
        return [rid for _, rid in sorted(scored)[:CHANNEL_CAP]]
