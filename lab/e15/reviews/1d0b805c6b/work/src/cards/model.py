"""Value types returned by the cards package (WP-E15C interface).

All three are frozen dataclasses: a caller can hold on to one without a later
upsert changing it under them.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisibleSet:
    """What one principal may see, resolved from the store for one call.

    ``tenant`` is ``None`` and ``groups`` is empty for an unknown or revoked
    principal (and for an agent whose delegation is not valid): "empty" is the
    one shape that means "sees nothing".
    """

    principal_id: str
    tenant: str | None
    groups: frozenset[str]


@dataclass(frozen=True)
class Card:
    """One compiled entity card: the head facts of one entity in one ACL group."""

    entity_id: str
    acl_group: str
    text: str
    fact_ids: tuple[int, ...]   # fact version ids listed on the card, ascending
    digest: str                 # sha256 hex of ``text`` (utf-8)


@dataclass(frozen=True)
class ContextItem:
    """One piece of assembled context: a pinned card or a found note."""

    kind: str                          # "card" or "note"
    ref: str                           # entity id for a card, note id for a note
    text: str
    reason: str                        # "card" (pinned) or "search" (found)
    annotations: tuple[str, ...] = ()  # forwarding notes, in mention order (notes only)
