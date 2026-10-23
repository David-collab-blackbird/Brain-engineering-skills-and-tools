from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass

from e15store.embedder import embed, tokens

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


def _person_groups(store, person: dict) -> frozenset[str]:
    """Groups named by the person's membership rows that exist in the person's tenant."""
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
    def visible_set(self, principal_id: str) -> VisibleSet:
        # DECISION: ADR-007 -- resolved from the store on every call, never cached; fail closed.
        empty = VisibleSet(principal_id, None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            if p["kind"] == "person":
                return VisibleSet(principal_id, p["tenant"], _person_groups(self.store, p))
            # Agent: acts with the access of the person it acts for. Fail closed: the
            # agent's own membership rows further limit it (intersection); see questions.json.
            owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
            if owner is None or owner["status"] != "active" or owner["kind"] != "person" \
                    or owner["tenant"] != p["tenant"]:
                return empty
            groups = _person_groups(self.store, owner) & _person_groups(self.store, p)
            return VisibleSet(principal_id, p["tenant"], groups)
        except Exception:
            return empty

    def _visible(self, vs: VisibleSet, rec: dict | None) -> bool:
        # DECISION: ADR-007 -- active, in a visible group, same tenant as requester.
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    # ------------------------------------------------------------------ get
    def get(self, record_id: str, principal_id: str) -> dict | None:
        try:
            vs = self.visible_set(principal_id)
            rec = self.store.current(record_id)
            return rec if self._visible(vs, rec) else None
        except Exception:
            return None

    # ---------------------------------------------------------------- index
    def rebuild(self) -> None:
        c = self.store.conn
        c.commit()
        c.execute("DROP TABLE IF EXISTS vr_docs")
        c.execute("CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL, "
                  "acl_group TEXT NOT NULL, dl INTEGER NOT NULL, tf TEXT NOT NULL, vec TEXT NOT NULL)")
        c.execute("CREATE INDEX vr_docs_group ON vr_docs(tenant, acl_group)")
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def _index(self, rec: dict) -> None:
        if rec["state"] != "active":
            return
        toks = tokens(rec["title"] + " " + rec["body"])
        self.store.conn.execute(
            "INSERT OR REPLACE INTO vr_docs(id, version, tenant, acl_group, dl, tf, vec) VALUES (?,?,?,?,?,?,?)",
            (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks),
             json.dumps(Counter(toks)), json.dumps(embed(rec["title"] + "\n" + rec["body"]))))

    def refresh(self, record_id: str) -> None:
        self.store.conn.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None:
            self._index(rec)
        self.store.conn.commit()

    # --------------------------------------------------------------- search
    def search(self, query: str, principal_id: str, k: int = 5) -> list[Hit]:
        try:
            hits = self._search(query, principal_id, k)
        except Exception:
            hits = []
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query: str, principal_id: str, k: int) -> list[Hit]:
        qtoks = tokens(query) if isinstance(query, str) else []
        if not qtoks or k <= 0:
            return []
        vs = self.visible_set(principal_id)
        if not vs.groups:
            return []

        # Pre-filter: only indexed rows in the visible groups, then the exit check against
        # the store (DECISION: ADR-007) so stale rows never enter results or statistics.
        # The indexed group may be stale (reclassify), so the store's current group decides.
        rows = self.store.conn.execute(
            "SELECT id, version, dl, tf, vec FROM vr_docs WHERE tenant = ?", (vs.tenant,)).fetchall()
        gone = []
        docs = {}
        current = {}
        for did, ver, dl, tf, vec in rows:
            rec = self.store.current(did)
            if rec is None or rec["state"] != "active":
                gone.append(did)  # erased/quarantined since indexing: drop its content from the index
                continue
            if rec["version"] != ver or not self._visible(vs, rec):
                continue
            current[did] = rec
            docs[did] = (dl, json.loads(tf), json.loads(vec))
        if gone:
            self.store.conn.executemany("DELETE FROM vr_docs WHERE id = ?", [(g,) for g in gone])
            self.store.conn.commit()
        if not docs:
            return []

        # DECISION: ADR-006 -- N, document frequencies and average length over visible docs only.
        n = len(docs)
        avgdl = sum(d[0] for d in docs.values()) / n
        qterms = sorted(set(qtoks))
        df = {t: sum(1 for d in docs.values() if t in d[1]) for t in qterms}
        bm25 = {}
        for did, (dl, tf, _) in docs.items():
            s = 0.0
            for t in qterms:
                f = tf.get(t, 0)
                if f:
                    idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                    s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / avgdl))
            if s > 0:
                bm25[did] = s
        qv = embed(query)
        dense = {}
        for did, (_, _, vec) in docs.items():
            cs = sum(a * b for a, b in zip(qv, vec))
            if cs >= COSINE_MIN:
                dense[did] = cs

        # DECISION: ADR-005 -- reciprocal rank fusion of the lexical and dense channels.
        fused: dict[str, float] = {}
        for chan in (bm25, dense):
            ranked = sorted(chan, key=lambda d: (-chan[d], d))[:CHANNEL_CAP]
            for rank, did in enumerate(ranked, 1):
                fused[did] = fused.get(did, 0.0) + 1.0 / (RRF_K + rank)
        order = sorted(fused, key=lambda d: (-fused[d], d))[:k]

        out = []
        for did in order:
            rec = current[did]
            out.append(Hit(did, rec["version"], rec["title"], rec["body"][:SNIPPET_LEN], float(fused[did])))
        return out
