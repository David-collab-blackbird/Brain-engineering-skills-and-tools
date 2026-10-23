"""Forward a note's quoted values to their current head, without leaking (R9)."""
from __future__ import annotations

from .access import can_see


# DECISION: ADR-009
# A note quotes fact versions. When a quoted version has been superseded, follow
# ``superseded_by`` to the key's head (``store.head_of``). The head's value and date go into the
# annotation only if the requester can see the head's group (and the head's entity is in their
# tenant); otherwise, and when the key was released and has no head, the annotation says only that
# the quoted value was superseded: no date, no value. One annotation per superseded mention, in
# mention order. A quoted version that is still a head, or no longer exists, gets none.
def forward_annotations(store, visible, note_id) -> tuple[str, ...]:
    notes = []
    for fact_id in store.mentions(note_id):
        quoted = store.fact(fact_id)
        if quoted is None or quoted["superseded_by"] is None:
            continue
        head = store.head_of(fact_id)
        if head is not None and head["superseded_by"] is None and _head_visible(store, visible, head):
            notes.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
        else:
            notes.append("quoted value superseded")
    return tuple(notes)


def _head_visible(store, visible, head) -> bool:
    entity = store.entity(head["entity_id"])
    return entity is not None and can_see(visible, head["acl_group"], entity["tenant"])
