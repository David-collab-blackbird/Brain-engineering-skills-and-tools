"""WP-E15C entity cards and context assembly."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

__all__ = ["Brain", "Card", "ContextItem", "VisibleSet"]


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
        self.conn = store.conn
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
            "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
            "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visibility
    def _groups_of(self, pid, tenant) -> set[str]:
        out = set()
        for gid in self.store.membership_rows(pid):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == tenant:
                out.add(gid)
        return out

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007
        # Resolved from the store on every call; never cached.
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            tenant = p["tenant"]
            groups = self._groups_of(p["id"], tenant)
            if p["kind"] == "agent":
                # An agent acts for a person; it never exceeds that person's access, and its own
                # membership rows (set by the admin tool) narrow what it may use (fail closed).
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if owner is None or owner["status"] != "active" or owner["kind"] != "person" \
                        or owner["tenant"] != tenant:
                    return empty
                groups &= self._groups_of(owner["id"], tenant)
            return VisibleSet(p["id"], tenant, frozenset(groups))
        except Exception:
            return empty

    # ------------------------------------------------------------ cards
    def _compile(self, entity_id) -> None:
        # DECISION: ADR-010
        # Cards are compiled in code from rows; one card per (entity, ACL group).
        c = self.conn
        c.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        ent = self.store.entity(entity_id)
        if ent is None:
            return
        by_group: dict[str, list[dict]] = {}
        for f in self.store.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(self.store.aliases(entity_id))
        for group, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            c.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                      (entity_id, group, text, json.dumps(sorted(f["id"] for f in facts)),
                       hashlib.sha256(text.encode("utf-8")).hexdigest()))

    def rebuild(self) -> None:
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            ids = {e["id"] for e in self.store.entities()}
            ids |= {f["entity_id"] for f in self.store.head_facts()}
            for eid in sorted(ids):
                self._compile(eid)

    def _all_cards(self, entity_id) -> list[Card]:
        rows = self.conn.execute(
            "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
            "ORDER BY acl_group", (entity_id,)).fetchall()
        return [Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4]) for r in rows]

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        # DECISION: ADR-007
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if vs.tenant is None or ent is None or ent["tenant"] != vs.tenant:
                return ()
            return tuple(c for c in self._all_cards(entity_id) if c.acl_group in vs.groups)
        except Exception:
            return ()

    def card(self, entity_id, principal_id) -> Card | None:
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009
        # Path A keyed upsert: supersede the head, recompile affected cards in the same transaction.
        with self.store.transaction():
            old = self.store.head(source_system, source_entity_id, attribute)
            if old is not None and (old["value"], old["valid_from"], old["acl_group"], old["entity_id"]) == \
                    (value, valid_from, acl_group, entity_id):
                return old["id"]
            new = self.store.insert_fact(
                source_system=source_system, source_entity_id=source_entity_id, attribute=attribute,
                entity_id=entity_id, value=value, valid_from=valid_from, source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                self.store.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile(eid)
            return new

    # ------------------------------------------------------------ assembly
    def _link(self, request, tenant) -> list[str]:
        """Linked entity ids ordered by first match position, then id (R7)."""
        rt = tokens(request)
        matches = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                n = len(nt)
                if n == 0:
                    continue
                for s in range(len(rt) - n + 1):
                    if rt[s:s + n] == nt:
                        matches.append((n, e["id"], s))
        matches.sort(key=lambda m: (-m[0], m[1], m[2]))
        taken: set[int] = set()
        first: dict[str, int] = {}
        for n, eid, s in matches:
            span = set(range(s, s + n))
            if span & taken:
                continue
            taken |= span
            first[eid] = min(first.get(eid, s), s)
        return sorted(first, key=lambda e: (first[e], e))

    def _visible_notes(self, vs) -> list[dict]:
        return [n for n in self.store.notes()
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]

    def _rank(self, request, notes) -> list[dict]:
        # Statistics are over the requester's visible active notes only (ADR-006).
        docs = [(n, tokens(n["text"])) for n in notes]
        N = len(docs)
        if N == 0:
            return []
        avgdl = sum(len(t) for _, t in docs) / N
        terms = sorted(set(tokens(request)))
        df = {t: sum(1 for _, toks in docs if t in toks) for t in terms}
        k1, b = 1.2, 0.75
        scored = []
        for n, toks in docs:
            score = 0.0
            dl = len(toks)
            for t in terms:
                if not df[t]:
                    continue
                tf = toks.count(t)
                if not tf:
                    continue
                idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
            if score > 0:
                scored.append((-score, n["id"], n))
        scored.sort(key=lambda x: (x[0], x[1]))
        return [n for _, _, n in scored]

    def _annotations(self, note_id, vs) -> tuple[str, ...]:
        # DECISION: ADR-009
        # Forward superseded quoted values to the head, only if the head is visible.
        out = []
        for fid in self.store.mentions(note_id):
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            h = self.store.head_of(fid)
            ent = self.store.entity(h["entity_id"]) if h else None
            if h and h["acl_group"] in vs.groups and ent is not None and ent["tenant"] == vs.tenant:
                out.append(f"quoted value superseded on {h['valid_from']}; current value {h['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _card_ok(self, card, principal_id) -> bool:
        cur = {c.acl_group: c for c in self.cards(card.entity_id, principal_id)}.get(card.acl_group)
        if cur is None or cur.fact_ids != card.fact_ids:
            return False
        return all((f := self.store.fact(i)) is not None and f["superseded_by"] is None for i in card.fact_ids)

    def _note_ok(self, note_id, principal_id) -> bool:
        vs = self.visible_set(principal_id)
        n = self.store.note(note_id)
        return n is not None and n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups

    def assemble(self, request, principal_id, k=10) -> list[ContextItem]:
        # DECISION: ADR-010
        # Pinned cards of linked entities first, then BM25 notes over the visible set.
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or k <= 0:
                return []
            cands: list[tuple[str, object]] = []
            pinned = 0
            for eid in self._link(request, vs.tenant):
                for c in self.cards(eid, principal_id):
                    if pinned < 3:
                        cands.append(("card", c))
                        pinned += 1
            for n in self._rank(request, self._visible_notes(vs)):
                cands.append(("note", n))
            items, seen = [], set()
            ncards = 0
            for kind, obj in cands:
                if len(items) >= k:
                    break
                if kind == "card":
                    if ncards >= 3 or not self._card_ok(obj, principal_id):
                        continue
                    ncards += 1
                    items.append(ContextItem("card", obj.entity_id, obj.text, "card", ()))
                else:
                    if obj["id"] in seen or not self._note_ok(obj["id"], principal_id):
                        continue
                    seen.add(obj["id"])
                    cur = self.store.note(obj["id"])
                    items.append(ContextItem("note", cur["id"], cur["text"], "search",
                                             self._annotations(cur["id"], self.visible_set(principal_id))))
            return items
        except Exception:
            return []
