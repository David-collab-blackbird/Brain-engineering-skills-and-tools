"""WP-E15C keyed facts, entity cards and context assembly."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

__all__ = ["Brain", "Card", "ContextItem", "VisibleSet"]

MAX_PINNED = 3
BM25_K1 = 1.2
BM25_B = 0.75


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: str | None
    groups: frozenset[str]


@dataclass(frozen=True)
class Card:
    entity_id: str
    acl_group: str
    text: str
    fact_ids: tuple[int, ...]
    digest: str


@dataclass(frozen=True)
class ContextItem:
    kind: str
    ref: str
    text: str
    reason: str
    annotations: tuple[str, ...] = ()


def _person_groups(store, person):
    """Groups named by the person's membership rows that exist in the person's own tenant."""
    out = set()
    for gid in store.membership_rows(person["id"]):
        g = store.group(gid)
        if g is not None and g["tenant"] == person["tenant"]:
            out.add(gid)
    return out


class Brain:
    def __init__(self, store):
        self.store = store
        with store.transaction():
            store.conn.execute(
                "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
                "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
                "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visibility
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 (resolved per call, fail closed, never crosses a tenant)
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            st = self.store
            p = st.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            if p["kind"] == "person":
                return VisibleSet(p["id"], p["tenant"], frozenset(_person_groups(st, p)))
            # Agent: access of the person it acts for, limited by the agent's own rows
            # (intersection; fail closed, see build/questions.json).
            owner = st.principal(p["acts_for"]) if p["acts_for"] else None
            if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                    or owner["tenant"] != p["tenant"]):
                return empty
            groups = _person_groups(st, owner) & _person_groups(st, p)
            return VisibleSet(p["id"], p["tenant"], frozenset(groups))
        except Exception:
            return empty

    # ------------------------------------------------------------ compilation
    def _compile_entity(self, entity_id):
        # DECISION: ADR-010 (cards compiled in code from rows, one per entity and ACL group)
        st = self.store
        st.conn.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        ent = st.entity(entity_id)
        if ent is None:
            return
        by_group: dict[str, list[dict]] = {}
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
            st.conn.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                            (entity_id, group, text, json.dumps(ids),
                             hashlib.sha256(text.encode("utf-8")).hexdigest()))

    def rebuild(self):
        st = self.store
        with st.transaction():
            st.conn.execute("DELETE FROM cd_cards")
            eids = {e["id"] for e in st.entities()}
            for eid in sorted(eids):
                self._compile_entity(eid)

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source, acl_group):
        # DECISION: ADR-009 (path A keyed upsert with supersession, same-transaction recompile)
        st = self.store
        with st.transaction():
            old = st.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            if st.entity(entity_id) is None:
                raise ValueError("unknown entity")
            new = st.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                 attribute=attribute, entity_id=entity_id, value=value,
                                 valid_from=valid_from, source=source, acl_group=acl_group)
            if old is not None:
                st.supersede(old["id"], new)
            affected = {entity_id}
            if old is not None:
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile_entity(eid)
            return new

    # ------------------------------------------------------------ cards
    def _row_card(self, r):
        return Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4])

    def _card_rows(self, entity_id):
        return self.store.conn.execute(
            "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
            "ORDER BY acl_group", (entity_id,)).fetchall()

    def _missing_group(self, entity_id, rows):
        have = {r[1] for r in rows}
        return any(f["acl_group"] not in have for f in self.store.head_facts(entity_id))

    def _visible_cards(self, entity_id, vs: VisibleSet):
        if vs.tenant is None:
            return ()
        ent = self.store.entity(entity_id)
        if ent is None or ent["tenant"] != vs.tenant:
            return ()
        rows = self._card_rows(entity_id)
        if not all(self._card_ok(self._row_card(r), None) for r in rows) or self._missing_group(entity_id, rows):
            # the store changed behind our back (e.g. a release): recompile this entity, never serve stale rows
            with self.store.transaction():
                self._compile_entity(entity_id)
            rows = self._card_rows(entity_id)
        # DECISION: ADR-007 (card visible only if its group is in the visible set)
        return tuple(self._row_card(r) for r in rows if r[1] in vs.groups)

    def cards(self, entity_id, principal_id):
        try:
            return self._visible_cards(entity_id, self.visible_set(principal_id))
        except Exception:
            return ()

    def card(self, entity_id, principal_id):
        c = self.cards(entity_id, principal_id)
        return c[0] if c else None

    # ------------------------------------------------------------ assembly
    def _link(self, request, tenant):
        # R7: longest contiguous token match wins; ties by lower entity id
        req = tokens(request)
        matches = []
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                t = tokens(name)
                n = len(t)
                if n == 0:
                    continue
                for i in range(len(req) - n + 1):
                    if req[i:i + n] == t:
                        matches.append((n, e["id"], i))
        matches.sort(key=lambda m: (-m[0], m[1], m[2]))
        taken: set[int] = set()
        first: dict[str, int] = {}
        for n, eid, i in matches:
            span = set(range(i, i + n))
            if span & taken:
                continue
            taken |= span
            first[eid] = min(first.get(eid, i), i)
        return [eid for eid, _ in sorted(first.items(), key=lambda kv: (kv[1], kv[0]))]

    def _rank_notes(self, req_tokens, vs: VisibleSet):
        # DECISION: ADR-010 (lexical search); statistics over visible active notes only (ADR-006)
        docs = []
        for n in self.store.notes():
            if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups:
                docs.append((n["id"], tokens(n["text"])))
        if not docs or not req_tokens:
            return []
        N = len(docs)
        avg = sum(len(t) for _, t in docs) / N or 1.0
        terms = sorted(set(req_tokens))
        df = {q: sum(1 for _, t in docs if q in t) for q in terms}
        scored = []
        for nid, toks in docs:
            tf: dict[str, int] = {}
            for w in toks:
                tf[w] = tf.get(w, 0) + 1
            s = 0.0
            for q in terms:
                f = tf.get(q, 0)
                if f == 0:
                    continue
                idf = math.log(1 + (N - df[q] + 0.5) / (df[q] + 0.5))
                s += idf * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * len(toks) / avg))
            if s > 0:
                scored.append((-s, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def _annotations(self, nid, vs: VisibleSet):
        # DECISION: ADR-009 (forward quoted stale values to the head, only if visible)
        st = self.store
        out = []
        for fid in st.mentions(nid):
            f = st.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            head = st.head_of(fid)
            if head is not None and head["acl_group"] in vs.groups:
                ent = st.entity(head["entity_id"])
                if ent is not None and ent["tenant"] == vs.tenant:
                    out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
                    continue
            out.append("quoted value superseded")
        return tuple(out)

    def _card_ok(self, card: Card, vs: VisibleSet):
        st = self.store
        if vs is not None:
            if card.acl_group not in vs.groups:
                return False
            ent = st.entity(card.entity_id)
            if ent is None or ent["tenant"] != vs.tenant:
                return False
        current = sorted(f["id"] for f in st.head_facts(card.entity_id) if f["acl_group"] == card.acl_group)
        return list(card.fact_ids) == current and bool(current)

    def _note_ok(self, nid, vs: VisibleSet):
        n = self.store.note(nid)
        return (n is not None and n["state"] == "active" and n["tenant"] == vs.tenant
                and n["acl_group"] in vs.groups)

    def assemble(self, request, principal_id, k=10):
        # DECISION: ADR-010 (pinned cards, then lexical notes, exit check)
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or not vs.groups or k <= 0:
                return []
            items: list[ContextItem] = []
            for eid in self._link(request, vs.tenant):
                for c in self._visible_cards(eid, vs):
                    if len(items) >= min(MAX_PINNED, k):
                        break
                    if self._card_ok(c, vs):
                        items.append(ContextItem("card", c.entity_id, c.text, "card", ()))
            seen = set()
            for nid in self._rank_notes(tokens(request), vs):
                if len(items) >= k:
                    break
                if nid in seen or not self._note_ok(nid, vs):
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, self.store.note(nid)["text"], "search",
                                         self._annotations(nid, vs)))
            return items
        except Exception:
            return []
