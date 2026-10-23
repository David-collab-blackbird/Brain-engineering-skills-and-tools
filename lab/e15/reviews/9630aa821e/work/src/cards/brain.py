from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

PIN_LIMIT = 3
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
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
            "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visibility
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 -- resolved per call from the store, fail closed.
        empty = VisibleSet(str(principal_id), None, frozenset())
        p = self.store.principal(principal_id)
        if p is None or p["status"] != "active":
            return empty
        groups = self._person_groups(p)
        if p["kind"] == "agent":
            owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
            if owner is None or owner["status"] != "active" or owner["kind"] != "person" \
                    or owner["tenant"] != p["tenant"]:
                return empty
            # Delegated access, limited by the agent's own rows (fail closed: intersection).
            groups = groups & self._person_groups(owner)
        return VisibleSet(p["id"], p["tenant"], frozenset(groups))

    def _person_groups(self, p) -> set[str]:
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    # ------------------------------------------------------------ compile
    def _compile_entity(self, entity_id) -> list[Card]:
        # DECISION: ADR-010 -- cards are compiled in code from rows, one per (entity, group).
        ent = self.store.entity(entity_id)
        if ent is None:
            return []
        by_group: dict[str, list[dict]] = {}
        for f in self.store.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(self.store.aliases(entity_id))
        cards = []
        for group in sorted(by_group):
            facts = sorted(by_group[group], key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            lines += [f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})"
                      for f in facts]
            text = "\n".join(lines)
            cards.append(Card(entity_id, group, text, tuple(sorted(f["id"] for f in facts)),
                              hashlib.sha256(text.encode("utf-8")).hexdigest()))
        return cards

    def _store_entity(self, entity_id) -> None:
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        for c in self._compile_entity(entity_id):
            self.conn.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                              (c.entity_id, c.acl_group, c.text, json.dumps(list(c.fact_ids)), c.digest))

    def rebuild(self) -> None:
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            ids = {e["id"] for e in self.store.entities()} | {f["entity_id"] for f in self.store.head_facts()}
            for eid in sorted(ids):
                self._store_entity(eid)

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009 -- path A keyed upsert with supersession, cards recompiled in the same transaction.
        with self.store.transaction():
            old = self.store.head(source_system, source_entity_id, attribute)
            if old is not None and old["value"] == value and old["valid_from"] == valid_from \
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id:
                return old["id"]
            if self.store.entity(entity_id) is None:
                raise ValueError("unknown entity")
            new = self.store.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                         attribute=attribute, entity_id=entity_id, value=value,
                                         valid_from=valid_from, source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                self.store.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._store_entity(eid)
            return new

    # ------------------------------------------------------------ reads
    def _fresh(self, entity_id) -> bool:
        """Stored cards of an entity still list only current heads and match a fresh compile."""
        rows = self.conn.execute("SELECT acl_group, digest FROM cd_cards WHERE entity_id = ? ORDER BY acl_group",
                                 (entity_id,)).fetchall()
        return rows == [(c.acl_group, c.digest) for c in self._compile_entity(entity_id)]

    def _all_cards(self, entity_id) -> list[Card]:
        if not self._fresh(entity_id):
            with self.store.transaction():
                self._store_entity(entity_id)
        return [Card(entity_id, g, t, tuple(json.loads(ids)), d) for g, t, ids, d in self.conn.execute(
            "SELECT acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? ORDER BY acl_group",
            (entity_id,))]

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        # DECISION: ADR-007 -- a card is visible only in its group and inside the requester's tenant.
        vs = self.visible_set(principal_id)
        ent = self.store.entity(entity_id)
        if vs.tenant is None or ent is None or ent["tenant"] != vs.tenant:
            return ()
        return tuple(c for c in self._all_cards(entity_id) if c.acl_group in vs.groups)

    def card(self, entity_id, principal_id) -> Card | None:
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ linking
    def _link(self, request_tokens, tenant) -> list[str]:
        """Entity ids linked from the request, ordered by first match position then id. (R7)"""
        matches = []
        n = len(request_tokens)
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                m = len(nt)
                if m == 0:
                    continue
                for s in range(n - m + 1):
                    if request_tokens[s:s + m] == nt:
                        matches.append((s, s + m, e["id"]))
        matches.sort(key=lambda x: (-(x[1] - x[0]), x[2], x[0]))
        taken = [False] * n
        first: dict[str, int] = {}
        for s, e_, eid in matches:
            if any(taken[s:e_]):
                continue
            for i in range(s, e_):
                taken[i] = True
            first[eid] = min(first.get(eid, s), s)
        return sorted(first, key=lambda eid: (first[eid], eid))

    # ------------------------------------------------------------ assembly
    def _note_ok(self, note, vs) -> bool:
        return (note is not None and note["state"] == "active" and note["tenant"] == vs.tenant
                and note["acl_group"] in vs.groups)

    def _bm25(self, query, vs) -> list[str]:
        docs = {}
        for n in self.store.notes():
            if self._note_ok(n, vs):
                docs[n["id"]] = tokens(n["text"])
        if not docs or not query:
            return []
        N = len(docs)
        avg = sum(len(d) for d in docs.values()) / N
        terms = sorted(set(query))
        df = {t: sum(1 for d in docs.values() if t in d) for t in terms}
        scored = []
        for nid, d in docs.items():
            tf = {}
            for w in d:
                tf[w] = tf.get(w, 0) + 1
            score = 0.0
            for t in terms:
                if not df[t] or t not in tf:
                    continue
                idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                f = tf[t]
                score += idf * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * len(d) / avg))
            if score > 0:
                scored.append((-score, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def _annotations(self, nid, vs) -> tuple[str, ...]:
        # DECISION: ADR-009 -- forward quoted values to the head; only reveal heads the requester can see.
        out = []
        for fid in self.store.mentions(nid):
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            head = self.store.head_of(fid)
            if head is not None and head["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def assemble(self, request, principal_id, k=10) -> list[ContextItem]:
        # DECISION: ADR-010 -- pinned cards first, then lexical search over visible active notes.
        vs = self.visible_set(principal_id)
        if vs.tenant is None or k <= 0:
            return []
        qt = tokens(request)
        pinned: list[Card] = []
        for eid in self._link(qt, vs.tenant):
            pinned.extend(self.cards(eid, principal_id))
        items = []
        for c in pinned:
            if len(items) >= min(PIN_LIMIT, k):
                break
            if self._card_ok(c, vs):      # exit check; a dropped card is replaced by the next candidate
                items.append(ContextItem("card", c.entity_id, c.text, "card", ()))
        seen = set()
        for nid in self._bm25(qt, vs):
            if len(items) >= k:
                break
            if nid in seen:
                continue
            seen.add(nid)
            note = self.store.note(nid)
            if not self._note_ok(note, vs):      # exit check
                continue
            items.append(ContextItem("note", nid, note["text"], "search", self._annotations(nid, vs)))
        return items

    def _card_ok(self, c, vs) -> bool:
        if c.acl_group not in vs.groups:
            return False
        for fid in c.fact_ids:
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is not None or f["acl_group"] != c.acl_group \
                    or f["entity_id"] != c.entity_id:
                return False
        return True
