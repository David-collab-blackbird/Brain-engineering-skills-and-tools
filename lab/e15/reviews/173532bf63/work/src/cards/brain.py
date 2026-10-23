"""The Brain: keyed-fact upsert, entity cards and context assembly over a FactStore."""
from __future__ import annotations

import operator

from factstore.text import tokens

from .access import card_visible, resolve_visible_set
from .compiler import CardTable
from .model import Card, ContextItem, VisibleSet
from .search import bm25_rank, link_entities

PIN_LIMIT = 3          # most cards pinned ahead of the notes
DEFAULT_K = 10         # items returned by default (owner decision OA-2: the interface value; the done line's 8 was a mistake)


class Brain:
    def __init__(self, store):
        self.store = store
        self._cards = CardTable(store)
        self.rebuild()                                  # compiles all cards from the store

    # ------------------------------------------------------------ access
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007
        """Resolved from the store on every call; nothing is cached across calls."""
        return resolve_visible_set(self.store, principal_id)

    def _visible_cards(self, entity_id, vs: VisibleSet) -> tuple[Card, ...]:
        # DECISION: ADR-007
        if not isinstance(entity_id, str) or not vs.groups:
            return ()
        # a stored card is served only while it is visible and every fact it lists is still a head (R4, R11)
        return tuple(c for c in self._cards.for_entity(entity_id) if self._card_valid(c, vs))

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        """The requester's visible cards of an entity, ordered by acl_group.

        Unknown entity, no visible card, unknown or revoked principal: (). Never raises for unknown ids.
        """
        return self._visible_cards(entity_id, self.visible_set(principal_id))

    def card(self, entity_id, principal_id) -> Card | None:
        found = self.cards(entity_id, principal_id)
        return found[0] if found else None

    # ------------------------------------------------------------ assembly
    def assemble(self, request, principal_id, k=DEFAULT_K) -> list[ContextItem]:
        # DECISION: ADR-010
        """Context for one requester: pinned cards of the entities named in the request, then notes by BM25.

        Everything is filtered to the requester's visible set before it is ranked or counted; every item is
        re-validated against the store before it is returned (exit check) and replaced by the next candidate
        if it no longer holds. Unknown or revoked principal: [].
        """
        k = operator.index(k)
        vs = self.visible_set(principal_id)
        if k <= 0 or not vs.groups:
            return []
        req = tokens(request) if isinstance(request, str) else []

        # candidates, all drawn from what the requester can see
        entities = [e for e in self.store.entities() if e["tenant"] == vs.tenant]
        linked = link_entities(entities, self.store.aliases, req)
        card_candidates = [c for eid in linked for c in self._visible_cards(eid, vs)]
        docs = [(n["id"], tokens(n["text"])) for n in self.store.notes()
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]
        note_candidates = bm25_rank(docs, req)

        # exit check: re-resolve access and re-read the rows, then fill up to k from the candidates still valid
        now = self.visible_set(principal_id)
        items: list[ContextItem] = []
        for card in card_candidates:
            if len(items) >= min(PIN_LIMIT, k):
                break
            if self._card_valid(card, now):
                items.append(ContextItem("card", card.entity_id, card.text, "card", ()))
        seen: set[str] = set()
        for nid in note_candidates:
            if len(items) >= k:
                break
            if nid in seen:
                continue
            seen.add(nid)
            note = self.store.note(nid)
            if note is not None and self._note_valid(note, now):
                items.append(ContextItem("note", nid, note["text"], "search", self._forward(nid, now)))
        return items

    def _card_valid(self, card: Card, vs: VisibleSet) -> bool:
        """The card is visible and every fact it lists is still a head of the same entity and group."""
        entity = self.store.entity(card.entity_id)
        if entity is None or not card.fact_ids or not card_visible(vs, entity["tenant"], card.acl_group):
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["entity_id"] != card.entity_id
                    or f["acl_group"] != card.acl_group):
                return False
        return True

    @staticmethod
    def _note_valid(note: dict, vs: VisibleSet) -> bool:
        return note["state"] == "active" and note["tenant"] == vs.tenant and note["acl_group"] in vs.groups

    def _fact_visible(self, fact: dict, vs: VisibleSet) -> bool:
        entity = self.store.entity(fact["entity_id"])
        return entity is not None and card_visible(vs, entity["tenant"], fact["acl_group"])

    def _forward(self, note_id: str, vs: VisibleSet) -> tuple[str, ...]:
        # DECISION: ADR-009
        """Annotations for the superseded values a note quotes, in mention order (R9).

        The current value and its date are given only when the head exists and the requester can see its group;
        a released key or an unseen head yields the bare "quoted value superseded".
        """
        out = []
        for fid in self.store.mentions(note_id):
            quoted = self.store.fact(fid)
            if quoted is None or quoted["superseded_by"] is None:
                continue
            head = self.store.head_of(fid)
            if head is not None and head["superseded_by"] is None and self._fact_visible(head, vs):
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    # ------------------------------------------------------------ writes
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009
        """Path A keyed upsert; returns the head version id of the key after the call.

        One transaction: an identical head is a no-op; otherwise a new version is inserted, the old head (if any)
        is superseded by it, and every card that listed the old head or lists the new version is recompiled.
        Nothing is deleted. Any failure rolls back the store and the cards together.
        """
        args = dict(source_system=source_system, source_entity_id=source_entity_id, attribute=attribute,
                    entity_id=entity_id, value=value, valid_from=valid_from, source=source, acl_group=acl_group)
        for name, arg in args.items():
            if not isinstance(arg, str):
                raise TypeError(f"{name} must be str")
        with self.store.transaction():
            entity = self.store.entity(entity_id)
            if entity is None:
                raise ValueError("unknown entity")
            group = self.store.group(acl_group)
            if group is None or group["tenant"] != entity["tenant"]:
                raise ValueError("unknown ACL group for the entity's tenant")
            if not self._key_in_tenant(source_system, source_entity_id, attribute, entity["tenant"]):
                raise ValueError("key is not writable for this entity")        # nothing crosses a tenant
            old = self.store.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new_id = self.store.insert_fact(**args)
            touched = {(entity_id, acl_group)}
            if old is not None:
                self.store.supersede(old["id"], new_id)
                touched.add((old["entity_id"], old["acl_group"]))
                touched |= self._cards.listing(old["id"])
            head = self.store.head(source_system, source_entity_id, attribute)
            if head is None or head["id"] != new_id:
                raise RuntimeError("supersession did not make the new version the head")
            for eid, grp in sorted(touched):
                self._cards.recompile(eid, grp)
            return new_id

    def _key_in_tenant(self, source_system, source_entity_id, attribute, tenant) -> bool:
        """True if the key has no versions yet, or its latest version (head or released) lives in `tenant`."""
        r = self.store.conn.execute(
            "SELECT id FROM facts WHERE source_system = ? AND source_entity_id = ? AND attribute = ? "
            "ORDER BY id DESC LIMIT 1", (source_system, source_entity_id, attribute)).fetchone()
        if r is None:
            return True
        latest = self.store.fact(r[0])
        entity = self.store.entity(latest["entity_id"])
        group = self.store.group(latest["acl_group"])
        return entity is not None and group is not None and entity["tenant"] == tenant == group["tenant"]

    # ------------------------------------------------------------ maintenance
    def rebuild(self) -> None:
        """Recompile every card from the store."""
        self._cards.rebuild()
