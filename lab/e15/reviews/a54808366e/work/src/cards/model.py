"""Plain value types returned by the cards package."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisibleSet:
    """What one requester may see, resolved from the store for one call.

    ``tenant`` is None and ``groups`` is empty for an unknown or revoked
    principal, and for an agent whose delegated access cannot be established.
    """

    principal_id: str
    tenant: str | None
    groups: frozenset[str]


@dataclass(frozen=True)
class Card:
    """One entity card: the head facts of one entity in one ACL group."""

    entity_id: str
    acl_group: str
    text: str
    fact_ids: tuple[int, ...]   # head fact version ids listed on the card, ascending
    digest: str                 # sha256 hex of ``text``


@dataclass(frozen=True)
class ContextItem:
    """One entry of an assembled context."""

    kind: str                   # "card" or "note"
    ref: str                    # entity id for a card, note id for a note
    text: str
    reason: str                 # "card" (pinned) or "search" (lexical)
    annotations: tuple[str, ...] = ()
