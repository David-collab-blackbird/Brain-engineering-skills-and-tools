"""Value types of the vretrieval interface (WP-E15, "Interface")."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisibleSet:
    """What one requester may see right now.

    ``groups`` is empty when nothing is visible; ``tenant`` is then usually
    None. A record is visible only if its tenant equals ``tenant`` and its
    ``acl_group`` is in ``groups``.
    """

    principal_id: str
    tenant: str | None = None
    groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Hit:
    """One search result. Text always comes from the record's current version."""

    id: str
    version: int
    title: str
    snippet: str
    score: float
