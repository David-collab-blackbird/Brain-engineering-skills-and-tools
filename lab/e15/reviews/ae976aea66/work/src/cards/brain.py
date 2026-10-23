"""Keyed facts, entity cards and context assembly (WP-E15C)."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

MAX_PINNED = 3
K1 = 1.2
B = 0.75


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


def _empty(pid):
    return VisibleSet(pid, None, frozenset())


class Brain:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        self.conn.execute("CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
                          "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
                          "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visible set
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 -- resolved per call from the store, fail closed.
        s = self.store
        p = s.principal(principal_id)
        if p is None or p["status"] != "active":
            return _empty(principal_id)
        rows = set(s.membership_rows(principal_id))
        if p["kind"] == "agent":
            # An agent acts with the access of the person it acts for, and its own rows
            # may only narrow that (never widen it).
            owner = s.principal(p["acts_for"]) if p["acts_for"] else None
            if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                    or owner["tenant"] != p["tenant"]):
                return _empty(principal_id)
            rows &= set(s.membership_rows(owner["id"]))
        groups = set()
        for gid in rows:
            g = s.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                groups.add(gid)
        return VisibleSet(principal_id, p["tenant"], frozenset(groups))

    # ------------------------------------------------------------ compiling
    def _compile_entity(self, eid):
        # DECISION: ADR-010 -- cards are compiled in code from rows, one per (entity, group).
        s = self.store
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ?", (eid,))
        ent = s.entity(eid)
        if ent is None:
            return
        by_group: dict[str, list[dict]] = {}
        for f in s.head_facts(eid):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(s.aliases(eid))
        for group, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            ids = sorted(f["id"] for f in facts)
            self.conn.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                              (eid, group, text, json.dumps(ids),
                               hashlib.sha256(text.encode("utf-8")).hexdigest()))

    def rebuild(self):
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            eids = {e["id"] for e in self.store.entities()}
            eids |= {f["entity_id"] for f in self.store.head_facts()}
            for eid in sorted(eids):
                self._compile_entity(eid)

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009 -- path A keyed upsert with supersession.
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
                self._compile_entity(eid)
            return new

    # ------------------------------------------------------------ card reads
    def _card_from_row(self, r):
        return Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4])

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        # DECISION: ADR-007 -- a card is visible only if its group is visible and tenants match.
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if ent is None or vs.tenant is None or ent["tenant"] != vs.tenant:
                return ()
            rows = self.conn.execute("SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards "
                                     "WHERE entity_id = ? ORDER BY acl_group", (entity_id,)).fetchall()
            return tuple(self._card_from_row(r) for r in rows if r[1] in vs.groups)
        except Exception:
            return ()

    def card(self, entity_id, principal_id):
        c = self.cards(entity_id, principal_id)
        return c[0] if c else None

    # ------------------------------------------------------------ assembly
    def _link(self, req_tokens, tenant):
        """R7: returns linked entity ids ordered by first match position, then id."""
        matches = []  # (length, entity_id, start)
        n = len(req_tokens)
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                t = tokens(name)
                m = len(t)
                if m == 0:
                    continue
                for i in range(n - m + 1):
                    if req_tokens[i:i + m] == t:
                        matches.append((m, e["id"], i))
        matches.sort(key=lambda x: (-x[0], x[1], x[2]))
        taken = [False] * n
        first: dict[str, int] = {}
        for m, eid, i in matches:
            if any(taken[i:i + m]):
                continue
            for j in range(i, i + m):
                taken[j] = True
            first[eid] = min(first.get(eid, i), i)
        return [e for e, _ in sorted(first.items(), key=lambda kv: (kv[1], kv[0]))]

    def _card_ok(self, card, vs):
        s = self.store
        if card.acl_group not in vs.groups:
            return False
        for fid in card.fact_ids:
            f = s.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] != card.acl_group
                    or f["acl_group"] not in vs.groups):
                return False
        return True

    def _note_ok(self, nid, vs):
        n = self.store.note(nid)
        return (n is not None and n["state"] == "active" and n["tenant"] == vs.tenant
                and n["acl_group"] in vs.groups)

    def _annotations(self, nid, vs):
        s = self.store
        out = []
        for fid in s.mentions(nid):
            f = s.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            # DECISION: ADR-009 -- forward a stale quoted value to its head.
            head = s.head_of(fid)
            if head is not None and head["superseded_by"] is None and head["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _ranked_notes(self, req_tokens, vs):
        # DECISION: ADR-006 -- statistics over the requester's visible active notes only.
        docs = []
        for n in self.store.notes():
            if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups:
                docs.append((n["id"], tokens(n["text"])))
        if not docs:
            return []
        N = len(docs)
        avg = sum(len(t) for _, t in docs) / N or 1.0
        terms = sorted(set(req_tokens))
        df = {q: sum(1 for _, t in docs if q in t) for q in terms}
        scored = []
        for nid, t in docs:
            dl = len(t)
            tf: dict[str, int] = {}
            for w in t:
                tf[w] = tf.get(w, 0) + 1
            score = 0.0
            for q in terms:
                f = tf.get(q, 0)
                if not f:
                    continue
                idf = math.log(1 + (N - df[q] + 0.5) / (df[q] + 0.5))
                score += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / avg))
            if score > 0:
                scored.append((-score, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def assemble(self, request, principal_id, k=10) -> list[ContextItem]:
        # DECISION: ADR-010 -- pinned cards first, then lexical notes; ADR-007 pre-filter.
        try:
            return self._assemble(request, principal_id, k)
        except Exception:
            return []

    def _assemble(self, request, principal_id, k):
        vs = self.visible_set(principal_id)
        if vs.tenant is None or k <= 0:
            return []
        req = tokens(request)
        items: list[ContextItem] = []
        for eid in self._link(req, vs.tenant):
            for c in self.cards(eid, principal_id):
                if len(items) >= min(MAX_PINNED, k):
                    break
                if self._card_ok(c, vs):  # exit check (R11)
                    items.append(ContextItem("card", eid, c.text, "card", ()))
        seen = set()
        for nid in self._ranked_notes(req, vs):
            if len(items) >= k:
                break
            if nid in seen or not self._note_ok(nid, vs):  # exit check (R11)
                continue
            seen.add(nid)
            items.append(ContextItem("note", nid, self.store.note(nid)["text"], "search",
                                     self._annotations(nid, vs)))
        return items
