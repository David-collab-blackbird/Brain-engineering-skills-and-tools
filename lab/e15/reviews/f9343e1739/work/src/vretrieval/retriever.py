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
RRF_C = 60
CHANNEL_CAP = 200
DENSE_MIN = 0.2
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


def _empty(pid) -> VisibleSet:
    return VisibleSet(str(pid), None, frozenset())


class Retriever:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        self.rebuild()

    # ------------------------------------------------------------ visibility
    def _own_groups(self, principal: dict) -> frozenset[str]:
        out = set()
        for gid in self.store.membership_rows(principal["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == principal["tenant"]:
                out.add(gid)
        return frozenset(out)

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 -- resolved from the store on every call, fail closed.
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return _empty(principal_id)
            groups = self._own_groups(p)
            if p["kind"] == "agent":
                # Delegated access, bounded by the agent's own membership rows
                # (the owner's admin tool uses them to limit the agent): the
                # intersection is the fail-closed reading. See build/questions.json.
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["kind"] != "person" or owner["status"] != "active"
                        or owner["tenant"] != p["tenant"]):
                    return _empty(principal_id)
                groups = groups & self._own_groups(owner)
            return VisibleSet(p["id"], p["tenant"], groups)
        except Exception:
            return _empty(principal_id)

    @staticmethod
    def _can_see(vs: VisibleSet, rec: dict | None) -> bool:
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    # ----------------------------------------------------------------- index
    def rebuild(self) -> None:
        c = self.conn
        c.executescript(
            "DROP TABLE IF EXISTS vr_docs; DROP TABLE IF EXISTS vr_tf;"
            "CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,"
            " acl_group TEXT NOT NULL, dl INTEGER NOT NULL, vec TEXT NOT NULL);"
            "CREATE TABLE vr_tf(id TEXT NOT NULL, term TEXT NOT NULL, tf INTEGER NOT NULL,"
            " PRIMARY KEY(term, id)) WITHOUT ROWID;")
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def _index(self, rec: dict) -> None:
        c = self.conn
        c.execute("DELETE FROM vr_docs WHERE id = ?", (rec["id"],))
        c.execute("DELETE FROM vr_tf WHERE id = ?", (rec["id"],))
        if rec["state"] != "active":
            return
        toks = tokens(rec["title"] + " " + rec["body"])
        c.execute("INSERT INTO vr_docs VALUES (?,?,?,?,?,?)",
                  (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks),
                   json.dumps(embed(rec["title"] + "\n" + rec["body"]))))
        c.executemany("INSERT INTO vr_tf VALUES (?,?,?)",
                      [(rec["id"], t, n) for t, n in Counter(toks).items()])

    def refresh(self, record_id) -> None:
        self._index(self.store.current(record_id) or {"id": record_id, "state": "gone"})
        self.conn.commit()

    # ------------------------------------------------------------------ get
    def get(self, record_id, principal_id):
        try:
            vs = self.visible_set(principal_id)
            rec = self.store.current(record_id)
            return rec if self._can_see(vs, rec) else None
        except Exception:
            return None

    # --------------------------------------------------------------- search
    def search(self, query, principal_id, k=10) -> list[Hit]:
        try:
            hits = self._search(query, principal_id, k)
        except Exception:
            hits = []
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _valid(self, vs: VisibleSet, doc_id: str, version: int) -> dict | None:
        # DECISION: ADR-007 -- exit check against the store, using this request's visible set.
        rec = self.store.current(doc_id)
        if not self._can_see(vs, rec) or rec["version"] != version:
            return None
        return rec

    def _search(self, query, principal_id, k) -> list[Hit]:
        q = tokens(query) if isinstance(query, str) else []
        if not q or k <= 0:
            return []
        vs = self.visible_set(principal_id)
        if not vs.groups:
            return []
        # Pre-filter: only documents in the requester's visible set enter any channel.
        docs = {r[0]: r[1:] for r in self.conn.execute(
            "SELECT id, version, acl_group, dl, vec FROM vr_docs WHERE tenant = ?", (vs.tenant,))
            if r[2] in vs.groups}
        if not docs:
            return []
        # Exit check first, so statistics never include stale, erased, quarantined or hidden rows.
        recs: dict[str, dict] = {}
        for doc_id in list(docs):
            rec = self._valid(vs, doc_id, docs[doc_id][0])
            if rec is None:
                del docs[doc_id]
            else:
                recs[doc_id] = rec
        if not docs:
            return []

        # DECISION: ADR-006 -- N, avgdl, df are computed over the visible documents only.
        n = len(docs)
        avgdl = sum(d[2] for d in docs.values()) / n
        bm: dict[str, float] = {}
        for term in dict.fromkeys(q):
            post = [(i, tf) for i, tf in self.conn.execute(
                "SELECT id, tf FROM vr_tf WHERE term = ?", (term,)) if i in docs]
            if not post:
                continue
            df = len(post)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, tf in post:
                dl = docs[i][2]
                bm[i] = bm.get(i, 0.0) + idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl / avgdl))
        qv = embed(query)
        dense = {}
        for i, d in docs.items():
            cos = sum(a * b for a, b in zip(qv, json.loads(d[3])))
            if cos >= DENSE_MIN:
                dense[i] = cos

        def ranked(scores):
            out = []
            for i in sorted((i for i, s in scores.items() if s > 0 or scores is dense),
                            key=lambda i: (-scores[i], i)):
                out.append(i)
                if len(out) == CHANNEL_CAP:
                    break
            return out

        # DECISION: ADR-005 -- reciprocal rank fusion of the lexical and dense channels.
        fused: dict[str, float] = {}
        for ch in (ranked(bm), ranked(dense)):
            for rank, i in enumerate(ch, 1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_C + rank)
        order = sorted(fused, key=lambda i: (-fused[i], i))[:k]
        return [Hit(i, recs[i]["version"], recs[i]["title"], recs[i]["body"][:SNIPPET_LEN],
                    float(fused[i])) for i in order]
