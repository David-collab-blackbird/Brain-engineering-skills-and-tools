"""Who may see what (R1, R2, R5).

Access is resolved from the store on every call and is never cached: a revoked
principal, a removed membership or a deleted group takes effect on the next
call. Group access comes from membership rows and from nothing else. There is
no role, title or ownership shortcut, so no principal has standing access to any
group (R2).
"""
from __future__ import annotations

from .model import VisibleSet


MAX_ID_CHARS = 250_000     # far beyond any real id; longer strings are treated as unknown ids, never looked up


def is_text(value) -> bool:
    """True for a str that can be stored: UTF-8 encodable (no lone surrogates).

    Uses the unbound str methods so a str subclass cannot run code of its own here.
    """
    if not isinstance(value, str):
        return False
    try:
        str.encode(value, "utf-8")
    except Exception:
        return False
    return True


def is_id(value) -> bool:
    """True for a str the store can look up. Anything else (None, numbers, lone surrogates, absurd sizes) is
    just an unknown id: callers treat it as not found and never raise (R12)."""
    return is_text(value) and str.__len__(value) <= MAX_ID_CHARS


def _empty(principal_id) -> VisibleSet:
    return VisibleSet(principal_id=principal_id, tenant=None, groups=frozenset())


def _own_groups(store, principal: dict) -> frozenset[str]:
    """Groups named in the principal's membership rows that exist in the principal's tenant.

    Membership rows are raw data: a row may name a missing group or a group of
    another tenant, and both are ignored.
    """
    groups = set()
    for gid in store.membership_rows(principal["id"]):
        group = store.group(gid)
        if group is not None and group["tenant"] == principal["tenant"]:
            groups.add(gid)
    return frozenset(groups)


def resolve_visible_set(store, principal_id) -> VisibleSet:
    # DECISION: ADR-007
    # Access control is a pre-filter that fails closed: anything not positively
    # established below is an empty set.
    if not is_id(principal_id):
        return _empty(principal_id)
    principal = store.principal(principal_id)
    if principal is None or principal["status"] != "active":
        return _empty(principal_id)

    groups = _own_groups(store, principal)
    if principal["kind"] == "agent":
        # Owner decision OA-1: a group is visible to an agent only if it is in the agent's own valid
        # membership rows (existing, same tenant) AND visible to the person it acts for. If that person is
        # unknown, revoked, not a person or in another tenant, the agent sees nothing.
        delegator = store.principal(principal["acts_for"]) if is_id(principal["acts_for"]) else None
        if (delegator is None or delegator["kind"] != "person" or delegator["status"] != "active"
                or delegator["tenant"] != principal["tenant"]):
            return _empty(principal_id)
        groups = groups & _own_groups(store, delegator)

    return VisibleSet(principal_id=principal_id, tenant=principal["tenant"], groups=groups)


def can_see_group(visible: VisibleSet, acl_group: str, entity_tenant: str | None) -> bool:
    """The card ACL test (R5): the group is in the requester's set and the tenants match."""
    # DECISION: ADR-007
    return (visible.tenant is not None and entity_tenant == visible.tenant
            and acl_group in visible.groups)
