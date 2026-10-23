"""Cards compiled in code from fact rows; context assembly for one requester."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

PIN_MAX = 3
BM25_K1 = 1.2
BM25_B = 0.75


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: str | None
    groups: frozenset


@dataclass(frozen=True)
class Card:
    entity_id: str
    acl_group: str
    text: str
    fact_ids: tuple
    digest: str


@dataclass(frozen=True)
class ContextItem:
    kind: str
    ref: str
    text: str
    reason: str
    annotations: tuple = ()


class Brain:
    def __init__(self, store):
        self.store = store
        with store.transaction():
            store.conn.execute(
                "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
                "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
                "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visible set
    # DECISION: ADR-007
    def _person_groups(self, p):
        """Groups named by the principal's own membership rows that exist in the principal's tenant."""
        st = self.store
        out = set()
        for gid in st.membership_rows(p["id"]):
            g = st.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007  (resolved per call; never cached; fail closed)
        empty = VisibleSet(principal_id, None, frozenset())
        try:
            st = self.store
            p = st.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            if p["kind"] == "person":
                return VisibleSet(principal_id, p["tenant"], frozenset(self._person_groups(p)))
            if p["kind"] == "agent":
                owner = st.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                # An agent never exceeds the person it acts for; its own rows can only narrow that.
                groups = self._person_groups(owner) & self._person_groups(p)
                return VisibleSet(principal_id, p["tenant"], frozenset(groups))
        except Exception:
            pass
        return empty

    # ------------------------------------------------------------ compilation
    # DECISION: ADR-010
    def _compile_entity(self, entity_id):
        """Recompile every card of one entity from head fact rows (caller holds the transaction)."""
        st = self.store
        conn = st.conn
        conn.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        ent = st.entity(entity_id)
        if ent is None:
            return
        by_group: dict[str, list] = {}
        for f in st.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(st.aliases(entity_id))
        for group, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            ids = sorted(f["id"] for f in facts)
            conn.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                         (entity_id, group, text, json.dumps(ids),
                          hashlib.sha256(text.encode("utf-8")).hexdigest()))

    def rebuild(self):
        # DECISION: ADR-010
        st = self.store
        with st.transaction():
            st.conn.execute("DELETE FROM cd_cards")
            ids = {e["id"] for e in st.entities()}
            for eid in sorted(ids):
                self._compile_entity(eid)

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group):
        # DECISION: ADR-009
        st = self.store
        with st.transaction():
            old = st.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new_id = st.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                    attribute=attribute, entity_id=entity_id, value=value,
                                    valid_from=valid_from, source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                st.supersede(old["id"], new_id)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile_entity(eid)
            return new_id

    # ------------------------------------------------------------ cards
    def _row_card(self, r):
        return Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4])

    def cards(self, entity_id, principal_id):
        # DECISION: ADR-007  (card ACL: group visible and same tenant; unknown == denied)
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if ent is None or vs.tenant is None or ent["tenant"] != vs.tenant:
                return ()
            cards = self._stored(entity_id)
            if any(not self._heads_ok(c) for c in cards):
                with self.store.transaction():  # a head changed outside upsert: recompile
                    self._compile_entity(entity_id)
                cards = self._stored(entity_id)
            return tuple(c for c in cards if c.acl_group in vs.groups)
        except Exception:
            return ()

    def _stored(self, entity_id):
        rows = self.store.conn.execute(
            "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
            "ORDER BY acl_group", (entity_id,)).fetchall()
        return [self._row_card(r) for r in rows]

    def _heads_ok(self, card):
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is not None:
                return False
        return True

    def card(self, entity_id, principal_id):
        c = self.cards(entity_id, principal_id)
        return c[0] if c else None

    # ------------------------------------------------------------ linking
    def _link(self, request, tenant, principal_id):
        """Return [(first_position, entity_id)] of linked entities (R7)."""
        req = tokens(request)
        cands = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != tenant or not self.cards(e["id"], principal_id):
                continue  # entities with no visible card cannot shape the result (R12)
            names = {tuple(tokens(n)) for n in [e["name"], *self.store.aliases(e["id"])]}
            for nt in names:
                n = len(nt)
                if n == 0:
                    continue
                for i in range(len(req) - n + 1):
                    if tuple(req[i:i + n]) == nt:
                        cands.append((n, e["id"], i))
        cands.sort(key=lambda c: (-c[0], c[1], c[2]))
        taken: set[int] = set()
        first: dict[str, int] = {}
        for n, eid, i in cands:
            span = range(i, i + n)
            if any(p in taken for p in span):
                continue
            taken.update(span)
            first[eid] = min(first.get(eid, i), i)
        return sorted((pos, eid) for eid, pos in first.items())

    # ------------------------------------------------------------ assembly
    def _card_valid(self, card, vs):
        st = self.store
        if card.acl_group not in vs.groups:
            return False
        for fid in card.fact_ids:
            f = st.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] != card.acl_group
                    or f["entity_id"] != card.entity_id):
                return False
        return True

    def _note_valid(self, nid, vs):
        n = self.store.note(nid)
        return (n is not None and n["state"] == "active" and n["tenant"] == vs.tenant
                and n["acl_group"] in vs.groups)

    def _annotations(self, nid, vs):
        # DECISION: ADR-009  (forward to head; never reveal a head the requester cannot see)
        st = self.store
        out = []
        for fid in st.mentions(nid):
            f = st.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            head = st.head_of(fid)
            if head is not None and head["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _bm25(self, request, vs):
        """Ranked note ids over the requester's visible active notes only (R10)."""
        docs = [(n["id"], tokens(n["text"])) for n in self.store.notes()
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]
        if not docs:
            return []
        N = len(docs)
        avg = sum(len(t) for _, t in docs) / N or 1.0
        q = sorted(set(tokens(request)))
        df = {w: sum(1 for _, t in docs if w in t) for w in q}
        scored = []
        for nid, t in docs:
            s = 0.0
            for w in q:
                if not df[w]:
                    continue
                tf = t.count(w)
                if not tf:
                    continue
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * len(t) / avg))
            if s > 0:
                scored.append((-s, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def assemble(self, request, principal_id, k=10):
        # DECISION: ADR-010
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or k <= 0:
                return []
            items: list[ContextItem] = []
            cap = min(PIN_MAX, k)
            for _, eid in self._link(request, vs.tenant, principal_id):
                for c in self.cards(eid, principal_id):
                    if len(items) >= cap:
                        break
                    # exit check (R11): facts still heads and visible
                    if self._card_valid(c, vs):
                        items.append(ContextItem("card", eid, c.text, "card", ()))
            seen = set()
            for nid in self._bm25(request, vs):
                if len(items) >= k:
                    break
                if nid in seen or not self._note_valid(nid, vs):
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, self.store.note(nid)["text"], "search",
                                         self._annotations(nid, vs)))
            return items
        except Exception:
            return []
