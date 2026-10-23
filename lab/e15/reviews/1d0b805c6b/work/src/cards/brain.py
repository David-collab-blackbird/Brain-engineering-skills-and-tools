"""Brain: keyed facts, entity cards and context assembly over a FactStore."""
from __future__ import annotations

from factstore.text import tokens

from .access import can_see, is_lookup_id, resolve_visible_set
from .compiler import CardTable
from .forward import forward_annotations
from .model import Card, ContextItem, VisibleSet
from .search import link_entities, rank_notes, visible_active_notes

DEFAULT_K = 10     # items assemble() returns at most, unless the caller asks for another k (owner decision OA-2)
MAX_PINNED = 3     # cards pinned ahead of the searched notes (R8)


class Brain:
    """Keyed facts, entity cards and context assembly over one FactStore.

    Cards are compiled into ``cd_`` tables inside the store's own connection. Build a Brain outside
    any transaction you may roll back: a rollback would take its tables with it, and every call then
    fails until ``rebuild()`` recreates them. Nothing else is held in memory between calls.
    """

    def __init__(self, store):
        self._store = store
        self._table = CardTable(store)
        self.rebuild()

    # ------------------------------------------------------------------ access
    def visible_set(self, principal_id) -> VisibleSet:
        """What ``principal_id`` may see right now. Resolved from the store on every call (R1)."""
        return resolve_visible_set(self._store, principal_id)

    # ------------------------------------------------------------------ upsert
    # DECISION: ADR-009
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        """Path A: keep one key's head current. Returns the head version id after the call.

        One transaction:
          * the key's head has the same value, valid_from, acl_group and entity_id -> no-op,
            return the head's id (no row written, no card touched);
          * otherwise insert a new version, supersede the old head with it, and recompile
            every card that listed the old head (or any earlier version of the key) or lists
            the new version (R6).
        Rows are never deleted. Any failure rolls the facts AND the cards back, because the
        cards live in the same connection and are never held in memory.
        """
        given = dict(source_system=source_system, source_entity_id=source_entity_id, attribute=attribute,
                     entity_id=entity_id, value=value, valid_from=valid_from, source=source, acl_group=acl_group)
        for name, text in given.items():
            if not isinstance(text, str):
                raise TypeError(f"upsert: {name} must be text")
        s = self._store
        with s.transaction():
            head = s.head(source_system, source_entity_id, attribute)
            if (head is not None and head["value"] == value and head["valid_from"] == valid_from
                    and head["acl_group"] == acl_group and head["entity_id"] == entity_id):
                return head["id"]
            # Every version the key has had, read before the new one is added. Any card that lists
            # one of them must be recompiled (a released version is listed too), and every version
            # still without a successor is superseded, so the key ends with exactly one head.
            stale = {(entity_id, acl_group)}
            heads = []
            for version, version_entity, version_group, successor in s.conn.execute(
                    "SELECT id, entity_id, acl_group, superseded_by FROM facts "
                    "WHERE source_system = ? AND source_entity_id = ? AND attribute = ? ORDER BY id",
                    (source_system, source_entity_id, attribute)).fetchall():
                stale.update(self._table.listing(version))
                if successor is None:
                    heads.append(version)
                    stale.add((version_entity, version_group))
            new_id = s.insert_fact(**given)
            for old_head in heads:
                s.supersede(old_head, new_id)
            for stale_entity, stale_group in sorted(stale):
                self._table.recompile(stale_entity, stale_group)
            return new_id

    # ---------------------------------------------------------------- assembly
    # DECISION: ADR-010
    def assemble(self, request, principal_id, k=DEFAULT_K) -> list[ContextItem]:
        """Context for one requester, at most ``k`` items (R8):

        1. link the entities named in ``request`` (R7), own tenant only;
        2. pin up to 3 of their visible cards, in order of first mention;
        3. fill the rest with notes found by BM25 over the requester's visible active notes (R10);
        4. forward each note's quoted values to their current head (R9);
        5. exit check (R11): re-validate every item against the store and replace what dropped.
        Not found equals denied: an unknown or revoked principal gets ``[]``.
        """
        limit = _limit(k)
        visible = self.visible_set(principal_id)
        if limit == 0 or not isinstance(request, str) or not visible.groups:
            return []
        query = tokens(request)
        pin_candidates = [card for entity_id in link_entities(self._store, visible.tenant, query)
                          for card in self._stored_cards(entity_id, visible)]
        note_candidates = rank_notes(visible_active_notes(self._store, visible), query)

        # Exit check: nothing is returned on the strength of the lookups above. Each candidate is
        # re-validated against the store, with the visible set resolved again, and a dropped one is
        # replaced by the next candidate, so the caller still gets up to ``limit`` items.
        final = self.visible_set(principal_id)
        items: list[ContextItem] = []
        for card in pin_candidates:
            if len(items) >= min(MAX_PINNED, limit):
                break
            if self._card_is_current(card, final):
                items.append(ContextItem("card", card.entity_id, card.text, "card"))
        returned: set[str] = set()
        for note_id in note_candidates:
            if len(items) >= limit:
                break
            note = self._store.note(note_id)
            if (note is None or note_id in returned or note["state"] != "active"
                    or not can_see(final, note["acl_group"], note["tenant"])):
                continue
            returned.add(note_id)
            items.append(ContextItem("note", note_id, note["text"], "search",
                                     forward_annotations(self._store, final, note_id)))
        return items

    # ------------------------------------------------------------------- cards
    def rebuild(self) -> None:
        """Recompile every card from the store."""
        self._table.rebuild()

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        """The requester's visible cards of one entity, ordered by ACL group.

        "Not found" equals "denied" (R12): an unknown entity, an entity with no
        visible card and an unknown or revoked principal all give ``()``.
        """
        visible = self.visible_set(principal_id)
        return tuple(c for c in self._stored_cards(entity_id, visible) if self._card_is_current(c, visible))

    def card(self, entity_id, principal_id) -> Card | None:
        """The first of ``cards()``, or None."""
        found = self.cards(entity_id, principal_id)
        return found[0] if found else None

    # DECISION: ADR-007
    def _stored_cards(self, entity_id, visible: VisibleSet) -> tuple[Card, ...]:
        """Stored cards of one entity that pass the card ACL (R5): group in the visible set, same tenant.

        Only cards that pass are read from the table: a hidden card's text is never loaded.
        """
        if not is_lookup_id(entity_id) or visible.tenant is None:
            return ()
        entity = self._store.entity(entity_id)
        if entity is None:
            return ()
        found = []
        for group in self._table.groups_of(entity_id):
            if can_see(visible, group, entity["tenant"]):
                card = self._table.get(entity_id, group)
                if card is not None:
                    found.append(card)
        return tuple(found)

    def _card_is_current(self, card: Card, visible: VisibleSet) -> bool:
        """Re-validate a stored card against the store: every fact on it is still a head of
        the same entity and group, and the card is still visible to the requester (R11)."""
        entity = self._store.entity(card.entity_id)
        if entity is None or not card.fact_ids or not can_see(visible, card.acl_group, entity["tenant"]):
            return False
        for fact_id in card.fact_ids:
            fact = self._store.fact(fact_id)
            if (fact is None or fact["superseded_by"] is not None or fact["acl_group"] != card.acl_group
                    or fact["entity_id"] != card.entity_id):
                return False
        return True


def _limit(k) -> int:
    """The item cap for one assemble() call: ``None`` means the default, a negative number means none."""
    if k is None:
        return DEFAULT_K
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("assemble: k must be an integer")
    return max(0, k)
