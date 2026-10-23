"""Brain: keyed-fact upsert, entity cards and context assembly over a FactStore.

Nothing about a requester is kept between calls: the visible set, the note
statistics and the entity links are all derived from the store on every call.
The only state that outlives a call is the compiled cards, which live in the
store's own connection (``cd_*`` tables) so that they commit and roll back
together with the facts they were compiled from.
"""
from __future__ import annotations

from factstore import tokens

from .access import can_see_group, is_id, is_text, resolve_visible_set
from .compiler import CardTable
from .linking import link_entities
from .model import Card, ContextItem, VisibleSet
from .ranking import bm25_rank

DEFAULT_K = 10       # the Interface's default (owner decision OA-2: the 8 in the done line was a mistake)
MAX_PINNED = 3       # R8: at most 3 pinned cards
_EXIT_ROUNDS = 5     # R11: how many times the exit check may rebuild the result before giving up


class Brain:
    def __init__(self, store):
        self.store = store
        self._cards = CardTable(store)
        self.rebuild()

    # ------------------------------------------------------------ access
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007
        return resolve_visible_set(self.store, principal_id)

    # ------------------------------------------------------------ cards
    def rebuild(self) -> None:
        """Recompile every card from the store."""
        # DECISION: ADR-010
        with self.store.transaction():
            self._cards.create()
            self._cards.rebuild()

    def _ensure_tables(self) -> None:
        """Recreate the derived tables if an outer rollback took them away (they are rebuilt from the store)."""
        if not self._cards.exists():
            self.rebuild()

    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        """The requester's visible cards of an entity, ordered by acl_group.

        Unknown entity, no visible card, unknown or revoked principal: ``()``.
        """
        # DECISION: ADR-007
        self._ensure_tables()
        visible = self.visible_set(principal_id)
        return tuple(c for c in self._acl_cards(entity_id, visible) if self._card_is_current(c, visible))

    def card(self, entity_id, principal_id) -> Card | None:
        found = self.cards(entity_id, principal_id)
        return found[0] if found else None

    def _acl_cards(self, entity_id, visible: VisibleSet) -> list[Card]:
        """Stored cards of the entity that pass the card ACL (R5). Nothing else is checked here."""
        # DECISION: ADR-007
        if visible.tenant is None or not is_id(entity_id):
            return []
        entity = self.store.entity(entity_id)
        if entity is None or entity["tenant"] != visible.tenant:
            return []
        return [c for c in self._cards.stored_cards(entity_id)
                if can_see_group(visible, c.acl_group, entity["tenant"])]

    def _card_is_current(self, card: Card, visible: VisibleSet) -> bool:
        """R11 for a card: the entity and every listed fact are still as compiled, still heads, still visible."""
        entity = self.store.entity(card.entity_id)
        if entity is None or not card.fact_ids or not can_see_group(visible, card.acl_group, entity["tenant"]):
            return False
        for fact_id in card.fact_ids:
            f = self.store.fact(fact_id)
            if (f is None or f["superseded_by"] is not None or f["entity_id"] != card.entity_id
                    or f["acl_group"] != card.acl_group):
                return False
        return True

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        """Keep one key current (path A). Returns the head version id after the call.

        Same value, valid_from, acl_group and entity as the head: no-op. Otherwise a
        new version is inserted, the old head points to it, and every affected card
        is recompiled, all in one transaction. A failure rolls everything back.
        """
        # DECISION: ADR-009
        args = dict(source_system=source_system, source_entity_id=source_entity_id, attribute=attribute,
                    entity_id=entity_id, value=value, valid_from=valid_from, source=source, acl_group=acl_group)
        for name, arg in args.items():
            if not isinstance(arg, str):
                raise TypeError(f"upsert: {name} must be text")
            if not is_text(arg):
                raise ValueError(f"upsert: {name} is not valid text")
        self._ensure_tables()
        with self.store.transaction():
            if self.store.entity(entity_id) is None:
                raise ValueError("upsert: unknown entity")
            old = self.store.head(source_system, source_entity_id, attribute)
            if old is not None and (old["value"], old["valid_from"], old["acl_group"], old["entity_id"]) == (
                    value, valid_from, acl_group, entity_id):
                return old["id"]

            new_id = self.store.insert_fact(**args)
            if old is not None:
                self.store.supersede(old["id"], new_id)
            head = self.store.head(source_system, source_entity_id, attribute)
            if head is None or head["id"] != new_id:
                raise RuntimeError("upsert: the new version did not become the head")

            # Every card that listed any version of this key, or lists the new one, is recompiled. The old head
            # is one of those versions; so is a version released earlier, whose card would otherwise keep it.
            touched = {(entity_id, acl_group)}
            for version_id, version_entity, version_group in self.store.conn.execute(
                    "SELECT id, entity_id, acl_group FROM facts "
                    "WHERE source_system = ? AND source_entity_id = ? AND attribute = ?",
                    (source_system, source_entity_id, attribute)).fetchall():
                touched.add((version_entity, version_group))
                touched |= self._cards.keys_listing(version_id)
            for key in sorted(touched):
                self._cards.recompile(*key)
            return new_id

    # ------------------------------------------------------------ assembly
    def assemble(self, request, principal_id, k: int = DEFAULT_K) -> list[ContextItem]:
        """Pinned cards of the entities the request names, then lexically found notes. At most ``k`` items."""
        # DECISION: ADR-010
        if k is None:
            k = DEFAULT_K
        if isinstance(k, bool) or not isinstance(k, int):
            raise TypeError("assemble: k must be an int")
        self._ensure_tables()
        visible = self.visible_set(principal_id)
        if visible.tenant is None or k <= 0 or not isinstance(request, str):
            return []
        query = tokens(request)
        if not query:
            return []

        # R8 step 1: link the entities the request names (R7)
        linked = self._linked_entities(query, visible.tenant)

        # R8 step 3: candidate notes. The visibility pre-filter runs before any statistic is computed (R10)
        docs = [(n["id"], tokens(n["text"])) for n in self.store.notes() if self._note_visible(n, visible)]
        note_candidates = [note_id for note_id, _ in bm25_rank(query, docs)]

        # R8 step 2 and R11. Each round picks against freshly resolved access (pinned cards are read again every
        # round, then notes), validates everything picked against the store, and only then reads access once
        # more: that read is the last one before returning. Any item that fails, or any change of access, sends
        # the pick round again, so dropped items are replaced by the next candidates. A change that lands inside
        # those last few reads cannot be seen by any re-read; that is inherent, not a gap in the check.
        for _ in range(_EXIT_ROUNDS):
            now = self.visible_set(principal_id)
            picked = self._pick(linked, note_candidates, now, k)
            # Notes are validated before the pinned cards (picked lists the cards first): a note costs many reads
            # (its annotations are recomputed), a card few, so this leaves the shortest stretch of reads between a
            # card's validation and the final access read.
            valid = all(self._still_valid(item, source, now) for item, source in reversed(picked))
            if valid and self.visible_set(principal_id) == now:
                return [item for item, _ in picked]
        return []       # the store kept changing under the call: fail closed

    def _pick(self, linked: list[str], note_candidates: list[str], visible: VisibleSet, k: int):
        """Up to k (item, source) pairs: valid pinned cards of the linked entities first, then valid notes."""
        picked = []
        pinned = (card for entity_id in linked for card in self._acl_cards(entity_id, visible))
        for card in pinned:
            if len(picked) >= min(MAX_PINNED, k):
                break
            if self._card_is_current(card, visible):
                picked.append((ContextItem(kind="card", ref=card.entity_id, text=card.text, reason="card"), card))
        returned: set[str] = set()
        for note_id in note_candidates:
            if len(picked) >= k:
                break
            note = self.store.note(note_id)
            if note_id in returned or not self._note_visible(note, visible):
                continue
            returned.add(note_id)
            picked.append((ContextItem(kind="note", ref=note_id, text=note["text"], reason="search",
                                       annotations=self._forward(note_id, visible)), note_id))
        return picked

    def _still_valid(self, item: ContextItem, source, visible: VisibleSet) -> bool:
        """The exit check for one picked item, from fresh store reads."""
        if item.kind == "card":
            return self._card_is_current(source, visible) and source in self._cards.stored_cards(source.entity_id)
        note = self.store.note(source)
        return (self._note_visible(note, visible) and note["text"] == item.text
                and self._forward(source, visible) == item.annotations)

    @staticmethod
    def _note_visible(note: dict | None, visible: VisibleSet) -> bool:
        """An active note of the requester's tenant in a group the requester may see (R8, R10, R11)."""
        return (note is not None and note["state"] == "active" and visible.tenant is not None
                and note["tenant"] == visible.tenant and note["acl_group"] in visible.groups)

    def _linked_entities(self, query: list[str], tenant: str) -> list[str]:
        entities = []
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            terms = [tokens(e["name"])] + [tokens(a) for a in self.store.aliases(e["id"])]
            entities.append((e["id"], [t for t in terms if t]))
        return link_entities(query, entities)

    def _forward(self, note_id: str, visible: VisibleSet) -> tuple[str, ...]:
        """Annotations for the quoted values of a note that have been superseded, in mention order."""
        # DECISION: ADR-009
        out = []
        for fact_id in self.store.mentions(note_id):
            quoted = self.store.fact(fact_id)
            if quoted is None or quoted["superseded_by"] is None:
                continue
            head = self.store.head_of(fact_id)
            if head is not None and head["superseded_by"] is None and self._head_visible(head, visible):
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _head_visible(self, head: dict, visible: VisibleSet) -> bool:
        entity = self.store.entity(head["entity_id"])
        return entity is not None and can_see_group(visible, head["acl_group"], entity["tenant"])
