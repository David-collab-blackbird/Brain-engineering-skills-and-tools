"""Visible set: which ACL groups a requester may read (resolved from the store on every call)."""
from __future__ import annotations

from .model import VisibleSet


def _active_principal(store, pid):
    if not isinstance(pid, str):
        return None
    p = store.principal(pid)
    if p is None or p["status"] != "active":
        return None
    return p


def _membership_groups(store, principal) -> frozenset[str]:
    """Groups named in the principal's membership rows that exist and belong to the principal's tenant."""
    granted = set()
    for gid in store.membership_rows(principal["id"]):
        g = store.group(gid)
        if g is not None and g["tenant"] == principal["tenant"]:
            granted.add(g["id"])
    return frozenset(granted)


def resolve_visible_set(store, principal_id) -> VisibleSet:
    # DECISION: ADR-007
    # Fail closed: anything unclear resolves to the empty set. Access comes only from membership rows;
    # no role, title or ownership ever adds a group (R2).
    empty = VisibleSet(principal_id, None, frozenset())
    p = _active_principal(store, principal_id)
    if p is None:
        return empty
    if p["kind"] == "person":
        return VisibleSet(principal_id, p["tenant"], _membership_groups(store, p))
    if p["kind"] == "agent":
        # An agent acts for an active person of its own tenant. Its own membership rows only narrow what it may
        # use (owner decision OA-1): visible = person's groups ∩ agent's own groups.
        person = _active_principal(store, p["acts_for"])
        if person is None or person["kind"] != "person" or person["tenant"] != p["tenant"]:
            return empty
        groups = _membership_groups(store, person) & _membership_groups(store, p)
        return VisibleSet(principal_id, p["tenant"], groups)
    return empty
