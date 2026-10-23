"""Visible set: which ACL groups a requester may read (resolved per call, never cached)."""
from __future__ import annotations

from .model import VisibleSet


def _member_groups(store, principal: dict) -> set[str]:
    """Groups named in the principal's membership rows that exist and belong to the principal's tenant."""
    groups = set()
    for gid in store.membership_rows(principal["id"]):
        g = store.group(gid)
        if g is not None and g["tenant"] == principal["tenant"]:
            groups.add(g["id"])
    return groups


def resolve_visible_set(store, principal_id) -> VisibleSet:
    # DECISION: ADR-007
    """Resolve the requester's visible set from the store, fail closed.

    Unknown or revoked principal: empty. A person sees exactly the groups in their own membership rows
    (existing, same tenant); no role, title or ownership adds anything (R2). An agent acts with the access of the
    person it acts for, narrowed by the agent's own membership rows (the owner's admin tool maintains them to
    limit what the agent may use): owner decision OA-1, a group is visible to an agent only if it is in the agent's
    own valid rows AND visible to that person.
    An agent whose person is missing, revoked, not a person, or in another tenant has nothing.
    """
    empty = VisibleSet(principal_id, None, frozenset())
    if not isinstance(principal_id, str):
        return empty
    p = store.principal(principal_id)
    if p is None or p["status"] != "active":
        return empty
    if p["kind"] == "person":
        groups = _member_groups(store, p)
    elif p["kind"] == "agent":
        acts_for = p["acts_for"]
        person = store.principal(acts_for) if isinstance(acts_for, str) else None
        if (person is None or person["status"] != "active" or person["kind"] != "person"
                or person["tenant"] != p["tenant"]):
            return empty
        groups = _member_groups(store, p) & _member_groups(store, person)
    else:
        return empty
    return VisibleSet(principal_id, p["tenant"], frozenset(groups))


def card_visible(vs: VisibleSet, entity_tenant: str, acl_group: str) -> bool:
    # DECISION: ADR-007
    """A card is visible only if its group is in the requester's set and the entity is in the requester's tenant."""
    return vs.tenant is not None and entity_tenant == vs.tenant and acl_group in vs.groups
