"""Value types returned by the cards package."""
from __future__ import annotations

from dataclasses import dataclass


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
