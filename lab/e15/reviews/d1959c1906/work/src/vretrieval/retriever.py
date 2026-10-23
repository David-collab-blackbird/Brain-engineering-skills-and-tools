from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass

from e15store import embed, tokens

log = logging.getLogger("vretrieval")

K1 = 1.2
B = 0.75
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



class Retriever:
    def __init__(self, store):
        self.store = store
        self.rebuild()

    # ------------------------------------------------------------ visible set
    def _person_groups(self, person: dict) -> frozenset[str]:
        # Only rows naming an existing group of the person's own tenant count.
        # No role/ownership grants (R2a).
        out = set()
        for gid in self.store.membership_rows(person["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == person["tenant"]:
                out.add(gid)
        return frozenset(out)

    # DECISION: ADR-007
    def visible_set(self, principal_id) -> VisibleSet:
        """Resolved from the store on every call; fails closed."""
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            if p["kind"] == "agent":
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                # Delegated access, limited by the agent's own (valid) rows:
                # never more than the person it acts for, never more than its own grants.
                groups = self._person_groups(owner) & self._person_groups(p)
            else:
                groups = self._person_groups(p)
            if not groups:
                return empty
            return VisibleSet(p["id"], p["tenant"], groups)
        except Exception:
            return empty

    @staticmethod
    def _visible(vs: VisibleSet, rec: dict) -> bool:
        return (vs.tenant is not None and rec["tenant"] == vs.tenant
                and rec["acl_group"] in vs.groups)

    # -------------------------------------------------------------------- get
    def get(self, record_id, principal_id):
        try:
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return None
            rec = self.store.current(record_id)
            if rec is None or rec["state"] != "active" or not self._visible(vs, rec):
                return None
            return rec
        except Exception:
            return None

    # ------------------------------------------------------------------ index
    def rebuild(self):
        c = self.store.conn
        c.execute("DROP TABLE IF EXISTS vr_docs")
        c.execute("CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, "
                  "tenant TEXT NOT NULL, dlen INTEGER NOT NULL, tf TEXT NOT NULL, vec TEXT NOT NULL)")
        for rec in self.store.current_records():
            if rec["state"] == "active":
                self._index(rec)
        c.commit()

    def _index(self, rec):
        toks = tokens(rec["title"] + " " + rec["body"])
        self.store.conn.execute(
            "INSERT OR REPLACE INTO vr_docs(id, version, tenant, dlen, tf, vec) VALUES (?,?,?,?,?,?)",
            (rec["id"], rec["version"], rec["tenant"], len(toks), json.dumps(Counter(toks)),
             json.dumps(embed(rec["title"] + "\n" + rec["body"]))))

    def refresh(self, record_id):
        self.store.conn.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None and rec["state"] == "active":
            self._index(rec)
        self.store.conn.commit()

    # ----------------------------------------------------------------- search
    def search(self, query, principal_id, k=5):
        hits = []
        try:
            hits = self._search(query, principal_id, k)
        except Exception:
            hits = []
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query, principal_id, k):
        qtoks = tokens(query) if isinstance(query, str) else []
        if not qtoks or k <= 0:
            return []
        vs = self.visible_set(principal_id)
        if not vs.groups:
            return []

        # DECISION: ADR-007 (exit check, applied to the whole pool before any statistic)
        # Every indexed doc of the tenant is re-validated against the store: current,
        # active, same version as indexed, and visible now. Only then does it enter
        # the candidate pool or the statistics.
        pool = {}
        rows = self.store.conn.execute(
            "SELECT id, version, dlen, tf, vec FROM vr_docs WHERE tenant = ?", (vs.tenant,)).fetchall()
        for did, ver, dlen, tf, vec in rows:
            rec = self.store.current(did)
            if (rec is None or rec["state"] != "active" or rec["version"] != ver
                    or not self._visible(vs, rec)):
                continue
            pool[did] = (rec, dlen, json.loads(tf), json.loads(vec))
        if not pool:
            return []

        # DECISION: ADR-006 (all statistics over the visible pool only)
        n = len(pool)
        avgdl = sum(v[1] for v in pool.values()) / n
        qterms = set(qtoks)
        df = {t: sum(1 for v in pool.values() if t in v[2]) for t in qterms}
        idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in qterms}
        lex = {}
        for did, (_, dlen, tf, _) in pool.items():
            s = 0.0
            for t in qterms:
                f = tf.get(t, 0)
                if f:
                    s += idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * dlen / avgdl))
            if s > 0:
                lex[did] = s
        qv = embed(query)
        dense = {}
        for did, (_, _, _, vec) in pool.items():
            cos = sum(a * b for a, b in zip(qv, vec))
            if cos >= COSINE_MIN:
                dense[did] = cos

        # DECISION: ADR-005 (RRF fusion of exact BM25 and exact cosine ranks)
        fused: dict[str, float] = {}
        for chan in (lex, dense):
            ranked = sorted(chan, key=lambda d: (-chan[d], d))[:CHANNEL_CAP]
            for rank, did in enumerate(ranked, 1):
                fused[did] = fused.get(did, 0.0) + 1.0 / (RRF_K + rank)
        order = sorted(fused, key=lambda d: (-fused[d], d))[:k]
        out = []
        for did in order:
            rec = pool[did][0]
            out.append(Hit(did, rec["version"], rec["title"], _snippet(rec["body"], qterms),
                           float(fused[did])))
        return out


def _snippet(body: str, qterms: set) -> str:
    return body[:SNIPPET_LEN]
