"""Keyed facts, entity cards and context assembly (WP-E15C)."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass

from factstore.text import tokens

DEFAULT_K = 10
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
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 -- resolved per call from the store, fail closed, never crosses a tenant.
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            s = self.store
            p = s.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            groups = self._person_groups(p)
            if p["kind"] == "agent":
                # Delegated access, limited by the agent's own rows: the intersection, so an agent
                # never exceeds its owner and never exceeds what the admin tool granted it.
                owner = s.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["kind"] != "person" or owner["status"] != "active"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                groups = groups & self._person_groups(owner)
            return VisibleSet(p["id"], p["tenant"], frozenset(groups))
        except Exception:
            return empty

    def _person_groups(self, p) -> set[str]:
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    # ------------------------------------------------------------ cards
    def _compile(self, entity_id) -> list[Card]:
        # DECISION: ADR-010 -- cards are compiled in code from rows, one per (entity, ACL group).
        s = self.store
        ent = s.entity(entity_id)
        if ent is None:
            return []
        by_group: dict[str, list[dict]] = {}
        for f in s.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(s.aliases(entity_id))
        cards = []
        for group in sorted(by_group):
            facts = sorted(by_group[group], key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            cards.append(Card(entity_id, group, text, tuple(sorted(f["id"] for f in facts)),
                              hashlib.sha256(text.encode("utf-8")).hexdigest()))
        return cards

    def _store_cards(self, entity_id, cards):
        c = self.store.conn
        c.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        c.executemany("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                      [(k.entity_id, k.acl_group, k.text, json.dumps(list(k.fact_ids)), k.digest) for k in cards])

    def _stored(self, entity_id) -> list[Card]:
        return [Card(e, g, t, tuple(json.loads(f)), d) for e, g, t, f, d in self.store.conn.execute(
            "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
            "ORDER BY acl_group", (entity_id,))]

    def _refresh(self, entity_id) -> list[Card]:
        """Cards of one entity, recompiled if the stored ones no longer match the rows."""
        fresh = self._compile(entity_id)
        if fresh != self._stored(entity_id):
            with self.store.transaction():
                self._store_cards(entity_id, fresh)
        return fresh

    def rebuild(self):
        s = self.store
        ids = {e["id"] for e in s.entities()} | {r[0] for r in s.conn.execute("SELECT entity_id FROM facts")}
        with s.transaction():
            s.conn.execute("DELETE FROM cd_cards")
            for eid in sorted(ids):
                self._store_cards(eid, self._compile(eid))

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        # DECISION: ADR-007 -- a card is visible only for a visible group in the requester's tenant.
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if vs.tenant is None or ent is None or ent["tenant"] != vs.tenant:
                return ()
            return tuple(c for c in self._refresh(entity_id) if c.acl_group in vs.groups)
        except Exception:
            return ()

    def card(self, entity_id, principal_id) -> Card | None:
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009 -- path A keyed upsert with supersession, cards recompiled in the same transaction.
        s = self.store
        with s.transaction():
            old = s.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new = s.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                attribute=attribute, entity_id=entity_id, value=value, valid_from=valid_from,
                                source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                s.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._store_cards(eid, self._compile(eid))
            return new

    # ------------------------------------------------------------ assembly
    def _link(self, request, tenant) -> list[str]:
        """Entity ids linked from the request, ordered by first match position then id (R7)."""
        rt = tokens(request)
        matches = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                n = len(nt)
                if not n:
                    continue
                for i in range(len(rt) - n + 1):
                    if rt[i:i + n] == nt:
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
        return sorted(first, key=lambda e: (first[e], e))

    def _search(self, request, vs) -> list[dict]:
        """Visible active notes ranked by BM25 over the visible active notes only (R10)."""
        docs = [(n, tokens(n["text"])) for n in self.store.notes()
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]
        docs = [(n, t) for n, t in docs if t]
        if not docs:
            return []
        N = len(docs)
        avg = sum(len(t) for _, t in docs) / N
        q = sorted(set(tokens(request)))
        df = {w: sum(1 for _, t in docs if w in set(t)) for w in q}
        scored = []
        for n, t in docs:
            tf = Counter(t)
            score = 0.0
            for w in q:
                if df[w] == 0 or tf[w] == 0:
                    continue
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * tf[w] * (BM25_K1 + 1) / (tf[w] + BM25_K1 * (1 - BM25_B + BM25_B * len(t) / avg))
            if score > 0:
                scored.append((-score, n["id"], n))
        scored.sort(key=lambda x: (x[0], x[1]))
        return [n for _, _, n in scored]

    def _annotations(self, note_id, vs) -> tuple[str, ...]:
        # DECISION: ADR-009 -- forward quoted values to the head at read time, never leaking hidden groups.
        s = self.store
        out = []
        for fid in s.mentions(note_id):
            f = s.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            head = s.head_of(fid)
            if head is not None and head["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _card_ok(self, card, vs) -> bool:
        if card.acl_group not in vs.groups:
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is not None or f["acl_group"] not in vs.groups:
                return False
        return True

    def _note_ok(self, note, vs) -> bool:
        n = self.store.note(note["id"])
        return (n is not None and n["state"] == "active" and n["tenant"] == vs.tenant
                and n["acl_group"] in vs.groups)

    def assemble(self, request, principal_id, k=DEFAULT_K) -> list[ContextItem]:
        # DECISION: ADR-010 -- pinned cards for linked entities, then lexical notes, then an exit check.
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or not vs.groups or k <= 0:
                return []
            items: list[ContextItem] = []
            pinned = 0
            for eid in self._link(request, vs.tenant):
                for c in self.cards(eid, principal_id):
                    if pinned >= MAX_PINNED or len(items) >= k:
                        break
                    if self._card_ok(c, vs):  # exit check
                        items.append(ContextItem("card", eid, c.text, "card", ()))
                        pinned += 1
            seen = set()
            for n in self._search(request, vs):
                if len(items) >= k:
                    break
                if n["id"] in seen or not self._note_ok(n, vs):  # exit check
                    continue
                seen.add(n["id"])
                cur = self.store.note(n["id"])
                items.append(ContextItem("note", n["id"], cur["text"], "search", self._annotations(n["id"], vs)))
            return items
        except Exception:
            return []
