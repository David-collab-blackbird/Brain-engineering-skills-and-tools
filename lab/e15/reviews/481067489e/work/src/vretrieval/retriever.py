from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass

from e15store import embed, tokens

log = logging.getLogger("vretrieval")

K1, B = 1.2, 0.75
RRF_K = 60
CHANNEL_CAP = 200
COS_MIN = 0.2
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


_EMPTY_GROUPS: frozenset[str] = frozenset()


class Retriever:
    def __init__(self, store):
        self.store = store
        self.rebuild()

    # ------------------------------------------------------------ visibility
    # DECISION: ADR-007
    def _person_groups(self, person: dict | None) -> frozenset[str]:
        """Groups named by membership rows that exist and belong to the person's tenant."""
        if person is None or person["status"] != "active" or person["kind"] != "person":
            return _EMPTY_GROUPS
        out = set()
        for gid in self.store.membership_rows(person["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == person["tenant"]:
                out.add(gid)
        return frozenset(out)

    # DECISION: ADR-007
    def visible_set(self, principal_id) -> VisibleSet:
        """Resolved from the store on every call; never cached. Fails closed."""
        empty = VisibleSet(str(principal_id), None, _EMPTY_GROUPS)
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            if p["kind"] == "person":
                groups = self._person_groups(p)
            else:
                # Agent: acts with the access of its person, limited to what its own
                # membership rows allow (intersection: fail closed). Owner question filed.
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if owner is None or owner["status"] != "active" or owner["kind"] != "person" \
                        or owner["tenant"] != p["tenant"]:
                    return empty
                own = set()
                for gid in self.store.membership_rows(p["id"]):
                    g = self.store.group(gid)
                    if g is not None and g["tenant"] == p["tenant"]:
                        own.add(gid)
                groups = self._person_groups(owner) & own
            if not groups:
                return empty
            return VisibleSet(p["id"], p["tenant"], groups)
        except Exception:
            return empty

    # DECISION: ADR-007
    def _is_visible(self, rec: dict | None, vs: VisibleSet) -> bool:
        return (rec is not None and rec["state"] == "active" and vs.tenant is not None
                and rec["tenant"] == vs.tenant and rec["acl_group"] in vs.groups)

    def get(self, record_id, principal_id) -> dict | None:
        try:
            vs = self.visible_set(principal_id)
            if not vs.groups:
                return None
            rec = self.store.current(record_id)
            return rec if self._is_visible(rec, vs) else None
        except Exception:
            return None

    # ----------------------------------------------------------------- index
    def rebuild(self) -> None:
        c = self.store.conn
        c.executescript(
            "DROP TABLE IF EXISTS vr_docs; DROP TABLE IF EXISTS vr_terms;"
            "CREATE TABLE vr_docs(id TEXT PRIMARY KEY, version INTEGER NOT NULL, dl INTEGER NOT NULL, vec TEXT NOT NULL);"
            "CREATE TABLE vr_terms(id TEXT NOT NULL, term TEXT NOT NULL, tf INTEGER NOT NULL, PRIMARY KEY(term, id));"
        )
        for rec in self.store.current_records():
            self._index(rec)
        c.commit()

    def refresh(self, record_id) -> None:
        c = self.store.conn
        c.execute("DELETE FROM vr_docs WHERE id = ?", (record_id,))
        c.execute("DELETE FROM vr_terms WHERE id = ?", (record_id,))
        rec = self.store.current(record_id)
        if rec is not None:
            self._index(rec)
        c.commit()

    def _index(self, rec: dict) -> None:
        if rec["state"] != "active":
            return
        c = self.store.conn
        toks = tokens(rec["title"] + " " + rec["body"])
        vec = embed(rec["title"] + "\n" + rec["body"])
        c.execute("INSERT INTO vr_docs(id, version, dl, vec) VALUES (?,?,?,?)",
                  (rec["id"], rec["version"], len(toks), json.dumps(vec)))
        c.executemany("INSERT INTO vr_terms(id, term, tf) VALUES (?,?,?)",
                      [(rec["id"], t, n) for t, n in Counter(toks).items()])

    # ---------------------------------------------------------------- search
    def _purge_inactive(self) -> None:
        """Drop index rows of records that are gone, erased or quarantined in the store."""
        c = self.store.conn
        gone = [r[0] for r in c.execute(
            "SELECT d.id FROM vr_docs d LEFT JOIN records r ON r.id = d.id AND r.is_current = 1 "
            "WHERE r.id IS NULL OR r.state != 'active'")]
        for i in gone:
            c.execute("DELETE FROM vr_docs WHERE id = ?", (i,))
            c.execute("DELETE FROM vr_terms WHERE id = ?", (i,))
        if gone:
            c.commit()

    def _visible_docs(self, vs: VisibleSet) -> dict[str, tuple[int, int]]:
        """id -> (indexed version, doc length) for visible, active, up-to-date indexed docs."""
        if not vs.groups:
            return {}
        groups = sorted(vs.groups)
        q = ",".join("?" * len(groups))
        cur = self.store.conn.execute(
            f"SELECT r.id, r.version, d.dl FROM records r JOIN vr_docs d ON d.id = r.id AND d.version = r.version "
            f"WHERE r.is_current = 1 AND r.state = 'active' AND r.tenant = ? AND r.acl_group IN ({q})",
            [vs.tenant, *groups])
        return {i: (v, dl) for i, v, dl in cur}

    # DECISION: ADR-006
    def _bm25(self, qtoks: list[str], docs: dict[str, tuple[int, int]]) -> list[tuple[str, float]]:
        """Statistics (N, avgdl, df) over the requester's visible docs only."""
        n = len(docs)
        if n == 0:
            return []
        avgdl = sum(dl for _, dl in docs.values()) / n
        scores: dict[str, float] = {}
        c = self.store.conn
        for term in qtoks:
            tf_rows = [(i, tf) for i, tf in c.execute("SELECT id, tf FROM vr_terms WHERE term = ?", (term,))
                       if i in docs]
            df = len(tf_rows)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, tf in tf_rows:
                dl = docs[i][1]
                s = idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl / avgdl))
                scores[i] = scores.get(i, 0.0) + s
        return [(i, s) for i, s in scores.items() if s > 0]

    def _dense(self, query: str, docs: dict[str, tuple[int, int]]) -> list[tuple[str, float]]:
        qv = embed(query)
        qn = math.sqrt(sum(x * x for x in qv))
        if qn == 0 or not docs:
            return []
        out = []
        for i, vec in self.store.conn.execute("SELECT id, vec FROM vr_docs"):
            if i not in docs:
                continue
            dv = json.loads(vec)
            dn = math.sqrt(sum(x * x for x in dv))
            if dn == 0:
                continue
            cos = sum(a * b for a, b in zip(qv, dv)) / (qn * dn)
            if cos >= COS_MIN:
                out.append((i, cos))
        return out

    @staticmethod
    def _rank(cands: list[tuple[str, float]]) -> list[str]:
        cands.sort(key=lambda x: (-x[1], x[0]))
        return [i for i, _ in cands[:CHANNEL_CAP]]

    def search(self, query, principal_id, k=10) -> list[Hit]:
        try:
            hits = self._search(query, principal_id, k)
        except Exception:
            hits = []
        log.info("search principal=%s hits=%d", principal_id, len(hits))
        return hits

    def _search(self, query, principal_id, k) -> list[Hit]:
        if not isinstance(query, str) or not isinstance(k, int) or k <= 0:
            return []
        qtoks = list(dict.fromkeys(tokens(query)))
        if not qtoks:
            return []
        self._purge_inactive()
        vs = self.visible_set(principal_id)
        docs = self._visible_docs(vs)
        if not docs:
            return []
        # DECISION: ADR-005
        fused: dict[str, float] = {}
        for ranked in (self._rank(self._bm25(qtoks, docs)), self._rank(self._dense(query, docs))):
            for r, i in enumerate(ranked, start=1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r)
        order = sorted(fused.items(), key=lambda x: (-x[1], x[0]))
        # DECISION: ADR-007
        out: list[Hit] = []
        for i, score in order:
            rec = self.store.current(i)
            if not self._is_visible(rec, vs) or rec["version"] != docs[i][0]:
                continue
            out.append(Hit(rec["id"], rec["version"], rec["title"], rec["body"][:SNIPPET_LEN], float(score)))
            if len(out) >= k:
                break
        return out
