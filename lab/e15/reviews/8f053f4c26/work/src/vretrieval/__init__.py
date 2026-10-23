"""WP-E15 visible-set retrieval: access pre-filter, visible-set statistics, exit check."""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass

from e15store import embed, tokens

__all__ = ["Retriever", "Hit", "VisibleSet"]

log = logging.getLogger("vretrieval")

K1 = 1.2
B = 0.75
RRF_C = 60
CHANNEL_CAP = 200
DENSE_MIN = 0.2
DEFAULT_K = 10


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


def _valid_groups(store, person: dict) -> frozenset[str]:
    """Membership rows naming existing groups of the person's own tenant."""
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
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 (resolved from the store on every call, never cached; fail closed)
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            if p["kind"] == "person":
                return VisibleSet(p["id"], p["tenant"], _valid_groups(self.store, p))
            if p["kind"] == "agent":
                # Delegation: the agent never exceeds the person it acts for; its own
                # membership rows narrow that further (see build/questions.json).
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["kind"] != "person" or owner["status"] != "active"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                groups = _valid_groups(self.store, owner) & _valid_groups(self.store, p)
                return VisibleSet(p["id"], p["tenant"], groups)
        except Exception:
            log.exception("visible_set failed; failing closed")
        return empty

    @staticmethod
    def _is_visible(vs: VisibleSet, rec: dict) -> bool:
        # DECISION: ADR-007
        return (bool(vs.groups) and vs.tenant is not None and rec["tenant"] == vs.tenant
                and rec["acl_group"] in vs.groups)

    def get(self, record_id, principal_id):
        try:
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return None
            rec = self.store.current(record_id)
            if rec is None or rec["state"] != "active" or not self._is_visible(vs, rec):
                return None
            return rec
        except Exception:
            return None

    # ------------------------------------------------------------------ index
    def rebuild(self):
        c = self.store.conn
        for t in ("vr_terms", "vr_docs"):
            c.execute(f"DROP TABLE IF EXISTS {t}")
        c.execute("CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,"
                  " acl_group TEXT NOT NULL, dl INTEGER NOT NULL, vec TEXT NOT NULL)")
        c.execute("CREATE TABLE vr_terms(doc_id TEXT NOT NULL, term TEXT NOT NULL, tf INTEGER NOT NULL,"
                  " PRIMARY KEY(doc_id, term))")
        c.execute("CREATE INDEX vr_terms_term ON vr_terms(term)")
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def _index(self, rec: dict):
        if rec["state"] != "active":
            return
        c = self.store.conn
        toks = tokens(rec["title"] + " " + rec["body"])
        c.execute("INSERT INTO vr_docs VALUES (?,?,?,?,?,?)",
                  (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks),
                   json.dumps(embed(rec["title"] + "\n" + rec["body"]))))
        tf: dict[str, int] = defaultdict(int)
        for t in toks:
            tf[t] += 1
        c.executemany("INSERT INTO vr_terms VALUES (?,?,?)", [(rec["id"], t, n) for t, n in tf.items()])

    def refresh(self, record_id):
        c = self.store.conn
        c.execute("DELETE FROM vr_terms WHERE doc_id = ?", (record_id,))
        c.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None:
            self._index(rec)
        c.commit()

    # ----------------------------------------------------------------- search
    def search(self, query, principal_id, k=DEFAULT_K) -> list[Hit]:
        try:
            hits = self._search(query, principal_id, k)
        except Exception:
            log.exception("search failed; failing closed")
            hits = []
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _eligible(self, vs: VisibleSet) -> dict[str, tuple[dict, str]]:
        """Pre-filter + exit check: indexed docs the requester may see in the store's current,
        active version. Returns id -> (current record, vec json)."""
        # DECISION: ADR-007
        if not vs.groups:
            return {}
        out = {}
        # the index's acl_group/tenant may be stale (in-place reclassify): the store decides
        rows = self.store.conn.execute("SELECT id, version, vec FROM vr_docs ORDER BY id").fetchall()
        for rid, ver, vec in rows:
            rec = self.store.current(rid)
            if (rec is not None and rec["state"] == "active" and rec["version"] == ver
                    and self._is_visible(vs, rec)):
                out[rid] = (rec, vec)
        return out

    def _search(self, query, principal_id, k) -> list[Hit]:
        if not isinstance(query, str) or not isinstance(k, int) or k <= 0:
            return []
        qtoks = list(dict.fromkeys(tokens(query)))
        if not qtoks:
            return []
        vs = self.visible_set(principal_id)
        elig = self._eligible(vs)
        if not elig:
            return []
        ids = list(elig)

        # DECISION: ADR-006 (N, df, avgdl over the requester's visible records only)
        c = self.store.conn
        dl = dict(c.execute("SELECT id, dl FROM vr_docs").fetchall())
        n = len(ids)
        avgdl = sum(dl[i] for i in ids) / n
        marks = ",".join("?" * len(qtoks))
        tfs: dict[str, dict[str, int]] = defaultdict(dict)
        for did, term, tf in c.execute(
                f"SELECT doc_id, term, tf FROM vr_terms WHERE term IN ({marks})", qtoks):
            if did in elig:
                tfs[term][did] = tf
        bm: dict[str, float] = defaultdict(float)
        for term, postings in tfs.items():
            df = len(postings)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for did, tf in postings.items():
                norm = tf + K1 * (1 - B + B * dl[did] / avgdl) if avgdl else tf + K1
                bm[did] += idf * tf * (K1 + 1) / norm
        lexical = [d for d, s in sorted(bm.items(), key=lambda x: (-x[1], x[0])) if s > 0][:CHANNEL_CAP]

        qv = embed(query)
        dense_scores = {}
        for did in ids:
            dv = json.loads(elig[did][1])
            s = sum(a * b for a, b in zip(qv, dv))
            if s >= DENSE_MIN:
                dense_scores[did] = s
        dense = [d for d, _ in sorted(dense_scores.items(), key=lambda x: (-x[1], x[0]))][:CHANNEL_CAP]

        # DECISION: ADR-005 (reciprocal rank fusion, constant 60, ties by id)
        fused: dict[str, float] = defaultdict(float)
        for ranking in (lexical, dense):
            for rank, did in enumerate(ranking, start=1):
                fused[did] += 1.0 / (RRF_C + rank)
        order = sorted(fused.items(), key=lambda x: (-x[1], x[0]))[:k]
        return [Hit(id=d, version=elig[d][0]["version"], title=elig[d][0]["title"],
                    snippet=elig[d][0]["body"][:120], score=float(s)) for d, s in order]
