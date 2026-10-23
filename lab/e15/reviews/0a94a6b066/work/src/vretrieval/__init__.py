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

K1 = 1.2
B = 0.75
RRF_K = 60
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


def _snippet(body: str) -> str:
    return body[:SNIPPET_LEN]


class Retriever:
    def __init__(self, store):
        self.store = store
        self.rebuild()

    # ------------------------------------------------------------ visibility
    # DECISION: ADR-007 (resolved from the store on every call, never cached; fail closed)
    def visible_set(self, principal_id: str) -> VisibleSet:
        empty = VisibleSet(principal_id, None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            owner = p
            if p["kind"] == "agent":
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return empty
            tenant = owner["tenant"]

            def groups_of(pid: str) -> set[str]:
                out = set()
                for gid in self.store.membership_rows(pid):
                    g = self.store.group(gid)
                    if g is not None and g["tenant"] == tenant:
                        out.add(gid)
                return out

            groups = groups_of(owner["id"])
            if p is not owner:
                # the agent's own rows only ever narrow the delegated access
                groups &= groups_of(p["id"])
            return VisibleSet(principal_id, tenant, frozenset(groups))
        except Exception:
            return empty

    # DECISION: ADR-007 (record visible only if current group is in the set and tenants match)
    @staticmethod
    def _can_see(vs: VisibleSet, rec: dict | None) -> bool:
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    def get(self, record_id: str, principal_id: str) -> dict | None:
        try:
            vs = self.visible_set(principal_id)
            rec = self.store.current(record_id)
            return rec if self._can_see(vs, rec) else None
        except Exception:
            return None

    # ----------------------------------------------------------------- index
    def rebuild(self) -> None:
        c = self.store.conn
        for t in ("vr_postings", "vr_docs"):
            c.execute(f"DROP TABLE IF EXISTS {t}")
        c.execute("CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, tenant TEXT NOT NULL,"
                  " acl_group TEXT NOT NULL, dlen INTEGER NOT NULL, vec TEXT NOT NULL)")
        c.execute("CREATE TABLE vr_postings(term TEXT NOT NULL, id TEXT NOT NULL, tf INTEGER NOT NULL,"
                  " PRIMARY KEY(term, id))")
        c.execute("CREATE INDEX vr_docs_scope ON vr_docs(tenant, acl_group)")
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def _index(self, rec: dict) -> None:
        c = self.store.conn
        toks = tokens(rec["title"] + " " + rec["body"])
        c.execute("INSERT INTO vr_docs VALUES (?,?,?,?,?,?)",
                  (rec["id"], rec["version"], rec["tenant"], rec["acl_group"], len(toks),
                   json.dumps(embed(rec["title"] + "\n" + rec["body"]))))
        c.executemany("INSERT INTO vr_postings VALUES (?,?,?)",
                      [(t, rec["id"], n) for t, n in Counter(toks).items()])

    def refresh(self, record_id: str) -> None:
        c = self.store.conn
        c.execute("DELETE FROM vr_postings WHERE id = ?", (record_id,))
        c.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None and rec["state"] == "active":
            self._index(rec)
        c.commit()

    # ---------------------------------------------------------------- search
    def search(self, query: str, principal_id: str, k: int = 10) -> list[Hit]:
        hits = self._search(query, principal_id, k)
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query: str, principal_id: str, k: int) -> list[Hit]:
        try:
            qtoks = tokens(query) if isinstance(query, str) else []
            if not qtoks or k <= 0:
                return []
            vs = self.visible_set(principal_id)
            if vs.tenant is None or not vs.groups:
                return []
            groups = sorted(vs.groups)
            marks = ",".join("?" * len(groups))
            scope = f"tenant = ? AND acl_group IN ({marks})"
            args = [vs.tenant, *groups]
            c = self.store.conn

            # DECISION: ADR-006 (N, df, avgdl over the requester's visible records only)
            docs = {i: (v, dl) for i, v, dl in c.execute(
                f"SELECT id, version, dlen FROM vr_docs WHERE {scope}", args)}
            if not docs:
                return []
            n_docs = len(docs)
            avgdl = sum(dl for _, dl in docs.values()) / n_docs

            qterms = sorted(set(qtoks))
            scores: dict[str, float] = {}
            for term in qterms:
                posts = [(i, tf) for i, tf in c.execute(
                    "SELECT id, tf FROM vr_postings WHERE term = ?", (term,)) if i in docs]
                if not posts:
                    continue
                df = len(posts)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                for i, tf in posts:
                    dl = docs[i][1]
                    scores[i] = scores.get(i, 0.0) + idf * tf * (K1 + 1) / (
                        tf + K1 * (1 - B + B * dl / avgdl))
            lexical = {i: s for i, s in scores.items() if s > 0}

            qvec = embed(query)
            dense: dict[str, float] = {}
            if any(qvec):
                for i, v, raw in c.execute(f"SELECT id, version, vec FROM vr_docs WHERE {scope}", args):
                    cos = sum(a * b for a, b in zip(qvec, json.loads(raw)))
                    if cos >= DENSE_MIN:
                        dense[i] = cos

            # DECISION: ADR-007 (exit check against the store before ranking, so drops are replaced)
            valid: dict[str, dict] = {}
            for i in set(lexical) | set(dense):
                rec = self.store.current(i)
                if rec is not None and rec["version"] == docs[i][0] and self._can_see(vs, rec):
                    valid[i] = rec

            # DECISION: ADR-005 (reciprocal rank fusion of lexical and dense, ties by id)
            fused: dict[str, float] = {}
            for chan in (lexical, dense):
                ranked = sorted((i for i in chan if i in valid), key=lambda i: (-chan[i], i))[:CHANNEL_CAP]
                for rank, i in enumerate(ranked, 1):
                    fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank)
            order = sorted(fused, key=lambda i: (-fused[i], i))[:k]
            return [Hit(i, valid[i]["version"], valid[i]["title"], _snippet(valid[i]["body"]),
                        float(fused[i])) for i in order]
        except Exception:
            return []
