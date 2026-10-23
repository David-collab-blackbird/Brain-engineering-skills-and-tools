"""WP-E15C: keyed facts, entity cards and context assembly."""
from __future__ import annotations

import hashlib
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


class Brain:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        with store.transaction():
            self.conn.execute("CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL,"
                              " text TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group))")
            self.conn.execute("CREATE TABLE IF NOT EXISTS cd_card_facts(entity_id TEXT NOT NULL,"
                              " acl_group TEXT NOT NULL, fact_id INTEGER NOT NULL,"
                              " PRIMARY KEY (entity_id, acl_group, fact_id))")
        self.rebuild()

    # ------------------------------------------------------------ visibility
    def _person_groups(self, person):
        """Groups a person may see: member rows naming existing groups of the person's own tenant."""
        out = set()
        for gid in self.store.membership_rows(person["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == person["tenant"]:
                out.add(gid)
        return out

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 (resolved per call from the store, fail closed)
        empty = VisibleSet(principal_id, None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            groups = self._person_groups(p)
            if p["kind"] == "agent":
                # Agents act with the access of the person they act for; their own rows may only narrow it.
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                groups &= self._person_groups(owner)
            elif p["kind"] != "person":
                return empty
            return VisibleSet(principal_id, p["tenant"], frozenset(groups))
        except Exception:
            return empty

    # ------------------------------------------------------------ cards
    def _compile(self, entity_id):
        """Recompile every card of one entity from its head facts. Caller holds the transaction."""
        # DECISION: ADR-010 (cards compiled in code from rows)
        c = self.conn
        c.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        c.execute("DELETE FROM cd_card_facts WHERE entity_id = ?", (entity_id,))
        ent = self.store.entity(entity_id)
        if ent is None:
            return
        by_group: dict[str, list[dict]] = {}
        for f in self.store.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(set(self.store.aliases(entity_id)))
        for group, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = ["# " + ent["name"]]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            c.execute("INSERT INTO cd_cards VALUES (?,?,?,?)",
                      (entity_id, group, text, hashlib.sha256(text.encode("utf-8")).hexdigest()))
            c.executemany("INSERT INTO cd_card_facts VALUES (?,?,?)", [(entity_id, group, f["id"]) for f in facts])

    def rebuild(self):
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            self.conn.execute("DELETE FROM cd_card_facts")
            ids = {f["entity_id"] for f in self.store.head_facts()}
            for eid in sorted(ids):
                self._compile(eid)

    def _card_fresh(self, entity_id):
        """True if every stored card of the entity matches the store's current head facts."""
        stored = {}
        for g, fid in self.conn.execute("SELECT acl_group, fact_id FROM cd_card_facts WHERE entity_id = ?",
                                        (entity_id,)):
            stored.setdefault(g, set()).add(fid)
        heads = {}
        for f in self.store.head_facts(entity_id):
            heads.setdefault(f["acl_group"], set()).add(f["id"])
        return stored == heads

    def _load_cards(self, entity_id, groups):
        if not self._card_fresh(entity_id):  # derived data went stale outside upsert: recompile
            with self.store.transaction():
                self._compile(entity_id)
        rows = self.conn.execute("SELECT acl_group, text, digest FROM cd_cards WHERE entity_id = ?"
                                 " ORDER BY acl_group", (entity_id,)).fetchall()
        out = []
        for g, text, digest in rows:
            if g not in groups:
                continue
            fids = tuple(r[0] for r in self.conn.execute(
                "SELECT fact_id FROM cd_card_facts WHERE entity_id = ? AND acl_group = ? ORDER BY fact_id",
                (entity_id, g)))
            out.append(Card(entity_id, g, text, fids, digest))
        return out

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        # DECISION: ADR-007 (card ACL: tenant and group must both be visible)
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if ent is None or vs.tenant is None or ent["tenant"] != vs.tenant:
                return ()
            return tuple(self._load_cards(entity_id, vs.groups))
        except Exception:
            return ()

    def card(self, entity_id, principal_id):
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009 (path A keyed upsert with supersession)
        with self.store.transaction():
            old = self.store.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new = self.store.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                         attribute=attribute, entity_id=entity_id, value=value,
                                         valid_from=valid_from, source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                self.store.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile(eid)
            return new

    # ------------------------------------------------------------ assembly
    def _link(self, request, tenant, linkable):
        """Only entities with a card visible to the requester are linkable (no existence oracle).
        Return [(first_position, entity_id)] for entities linked from the request."""
        rt = tokens(request)
        matches = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != tenant or e["id"] not in linkable:
                continue
            for name in {e["name"], *self.store.aliases(e["id"])}:
                nt = tokens(name)
                n = len(nt)
                if not n:
                    continue
                for s in range(len(rt) - n + 1):
                    if rt[s:s + n] == nt:
                        matches.append((n, e["id"], s))
        matches.sort(key=lambda m: (-m[0], m[1], m[2]))
        taken: set[int] = set()
        first: dict[str, int] = {}
        for n, eid, s in matches:
            span = range(s, s + n)
            if any(i in taken for i in span):
                continue
            taken.update(span)
            first[eid] = min(first.get(eid, s), s)
        return sorted((pos, eid) for eid, pos in first.items())

    def _note_ok(self, note, vs):
        return (note is not None and note["state"] == "active" and note["tenant"] == vs.tenant
                and note["acl_group"] in vs.groups)

    def _rank_notes(self, request, vs):
        # DECISION: ADR-010 (lexical search); statistics over visible active notes only (ADR-006)
        docs = []
        for n in self.store.notes():
            if self._note_ok(n, vs):
                docs.append((n["id"], tokens(n["text"])))
        q = sorted(set(tokens(request)))
        if not docs or not q:
            return []
        N = len(docs)
        avgdl = sum(len(t) for _, t in docs) / N
        df = {w: sum(1 for _, t in docs if w in t) for w in q}
        scored = []
        for nid, toks in docs:
            dl = len(toks)
            score = 0.0
            for w in q:
                f = toks.count(w)
                if not f:
                    continue
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl))
            if score > 0:
                scored.append((-score, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def _annotations(self, nid, vs):
        # DECISION: ADR-009 (forward stale quoted values to the head, only if the head is visible)
        out = []
        for fid in self.store.mentions(nid):
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            head = self.store.head_of(fid)
            if head is not None and head["acl_group"] in vs.groups and head["superseded_by"] is None:
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _card_ok(self, card, vs):
        ent = self.store.entity(card.entity_id)
        if ent is None or ent["tenant"] != vs.tenant or card.acl_group not in vs.groups:
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] not in vs.groups
                    or f["entity_id"] != card.entity_id):
                return False
        return True

    def assemble(self, request, principal_id, k=10) -> list[ContextItem]:
        # DECISION: ADR-010 (pinned cards, then search notes; exit check before returning)
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or k <= 0:
                return []
            items: list[ContextItem] = []
            cap = min(MAX_PINNED, k)
            for _, eid in self._link(request, vs.tenant, {e["id"] for e in self.store.entities()
                                                                     if e["tenant"] == vs.tenant and self._load_cards(e["id"], vs.groups)}):
                for card in self._load_cards(eid, vs.groups):
                    if len(items) >= cap:
                        break
                    if self._card_ok(card, vs):  # exit check (R11)
                        items.append(ContextItem("card", eid, card.text, "card", ()))
            seen = set()
            for nid in self._rank_notes(request, vs):
                if len(items) >= k:
                    break
                if nid in seen:
                    continue
                note = self.store.note(nid)
                if not self._note_ok(note, vs):  # exit check (R11)
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, note["text"], "search", self._annotations(nid, vs)))
            return items
        except Exception:
            return []
