"""Brain: keyed-fact upsert, entity cards, and context assembly for one requester."""
from __future__ import annotations

from factstore.text import tokens

from .access import resolve_visible_set
from .compiler import CardTable, digest_of
from .model import Card, ContextItem, VisibleSet
from .search import bm25_rank, link_entities

MAX_PINNED = 3
DEFAULT_K = 10


def _is_id(value) -> bool:
    return isinstance(value, str)


class Brain:
    def __init__(self, store):
        self.store = store
        self._table = CardTable(store)
        self.rebuild()

    # ------------------------------------------------------------ access
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007
        # Resolved from the store on every call; nothing about a requester is cached.
        return resolve_visible_set(self.store, principal_id)

    def _entity_in_tenant(self, entity_id, vs: VisibleSet) -> bool:
        if vs.tenant is None or not _is_id(entity_id):
            return False
        entity = self.store.entity(entity_id)
        return entity is not None and entity["tenant"] == vs.tenant

    def _fact_visible(self, fact: dict, vs: VisibleSet) -> bool:
        return fact["acl_group"] in vs.groups and self._entity_in_tenant(fact["entity_id"], vs)

    def _card_live(self, card: Card, vs: VisibleSet) -> bool:
        """Card ACL (R5) and exit check (R11): visible to `vs`, and every fact on it is still a head."""
        # DECISION: ADR-007
        if card.acl_group not in vs.groups or not self._entity_in_tenant(card.entity_id, vs):
            return False
        if not card.fact_ids or digest_of(card.text) != card.digest:
            return False
        for fid in card.fact_ids:
            fact = self.store.fact(fid)
            if (fact is None or fact["superseded_by"] is not None or fact["entity_id"] != card.entity_id
                    or fact["acl_group"] != card.acl_group):
                return False
        return True

    # ------------------------------------------------------------ cards
    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        vs = self.visible_set(principal_id)
        if not vs.groups or not self._entity_in_tenant(entity_id, vs):
            return ()
        return tuple(c for c in self._table.cards_of(entity_id) if self._card_live(c, vs))

    def card(self, entity_id, principal_id) -> Card | None:
        found = self.cards(entity_id, principal_id)
        return found[0] if found else None

    def rebuild(self) -> None:
        self._table.rebuild()

    # ------------------------------------------------------------ upsert
    def _as_stored(self, value):
        """`value` as the TEXT columns will hold it (SQLite turns 5 into '5'), so repeats compare equal."""
        if value is None or isinstance(value, (str, bytes)):
            return value
        return self.store.conn.execute("SELECT CAST(? AS TEXT)", (value,)).fetchone()[0]

    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009
        # Path A: keyed upsert with supersession, one transaction. A failure anywhere rolls back the store and
        # the derived card tables together (they share the store's connection).
        store = self.store
        with store.transaction():
            old = store.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == self._as_stored(value)
                    and old["valid_from"] == self._as_stored(valid_from)
                    and old["acl_group"] == self._as_stored(acl_group)
                    and old["entity_id"] == self._as_stored(entity_id)):
                return old["id"]
            new_id = store.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                       attribute=attribute, entity_id=entity_id, value=value,
                                       valid_from=valid_from, source=source, acl_group=acl_group)
            touched = {(entity_id, acl_group)}
            if old is not None:
                store.supersede(old["id"], new_id)
                touched.add((old["entity_id"], old["acl_group"]))
                touched.update(self._table.pairs_listing(old["id"]))
            self._table.recompile(touched)
            return new_id

    # ------------------------------------------------------------ assembly
    def assemble(self, request, principal_id, k: int = DEFAULT_K) -> list[ContextItem]:
        # DECISION: ADR-010
        # Pinned cards of linked entities first, then lexical-search notes. Candidates are drawn from what the
        # requester can see; the exit check below re-validates each item against the store before it is returned.
        if not _is_id(request) or isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            return []
        vs = self.visible_set(principal_id)
        if not vs.groups:
            return []
        request_tokens = tokens(request)

        card_candidates: list[Card] = []
        for entity_id in link_entities(self.store, request_tokens, vs.tenant):
            card_candidates.extend(c for c in self._table.cards_of(entity_id) if self._card_live(c, vs))

        note_candidates = bm25_rank(self._visible_active_notes(vs), request_tokens)

        # Exit check (R11): resolve the requester afresh and re-validate each candidate; dropped ones are
        # replaced by the next candidates.
        now = self.visible_set(principal_id)
        items: list[ContextItem] = []
        for card in card_candidates:
            if len(items) >= min(MAX_PINNED, k):
                break
            if self._card_live(card, now):
                items.append(ContextItem("card", card.entity_id, card.text, "card", ()))
        seen: set[str] = set()
        for note_id in note_candidates:
            if len(items) >= k:
                break
            if note_id in seen:
                continue
            seen.add(note_id)
            note = self._note_live(note_id, now)
            if note is not None:
                items.append(ContextItem("note", note["id"], note["text"], "search",
                                         self._annotations(note["id"], now)))
        return items

    def _visible_active_notes(self, vs: VisibleSet) -> list[tuple[str, str]]:
        """(id, text) of active notes in the requester's tenant and visible groups; hidden notes are never read."""
        if vs.tenant is None:
            return []
        rows = self.store.conn.execute(
            "SELECT id, acl_group, text FROM notes WHERE tenant = ? AND state = 'active' ORDER BY id", (vs.tenant,))
        return [(nid, text) for nid, group, text in rows if group in vs.groups]

    def _note_live(self, note_id: str, vs: VisibleSet) -> dict | None:
        note = self.store.note(note_id)
        if (note is None or note["state"] != "active" or vs.tenant is None or note["tenant"] != vs.tenant
                or note["acl_group"] not in vs.groups):
            return None
        return note

    def _annotations(self, note_id: str, vs: VisibleSet) -> tuple[str, ...]:
        # DECISION: ADR-009
        # Forward a stale quoted value to its head, in mention order. The head's date and value are disclosed
        # only if the requester can see the head; otherwise (or if the key was released) the bare notice.
        out = []
        for fact_id in self.store.mentions(note_id):
            quoted = self.store.fact(fact_id)
            if quoted is None or quoted["superseded_by"] is None:
                continue
            head = self.store.head_of(fact_id)
            if head is not None and head["superseded_by"] is None and self._fact_visible(head, vs):
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)
