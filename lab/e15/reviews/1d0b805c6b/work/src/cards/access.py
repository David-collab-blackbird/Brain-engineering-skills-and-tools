"""Who may see what: the visible set and the card/fact ACL predicate.

Every function here reads the store afresh. Nothing is remembered between
calls, so a revoked principal or a changed membership takes effect on the very
next call (R1).
"""
from __future__ import annotations

from .model import VisibleSet


def is_lookup_id(value) -> bool:
    """True if ``value`` can be looked up in the store at all: text that encodes as UTF-8.

    Anything else (a non-string, or a string with a lone surrogate, which SQLite cannot bind) names
    nothing, so callers answer "unknown" for it exactly as for any other id that is not in the store.
    """
    if not isinstance(value, str):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


# DECISION: ADR-007
# Access control is a pre-filter that fails closed. The visible set is built
# only from the store's own rows: a principal's membership rows, narrowed to
# groups that exist and sit in the principal's own tenant. No role, title,
# display name, group label or ownership widens it (R2): the business owner is
# an ordinary person here and sees exactly the groups he is a member of.
def resolve_visible_set(store, principal_id) -> VisibleSet:
    """Resolve ``principal_id`` to a VisibleSet, or the empty set (R1, R12).

    * unknown, revoked or malformed principal -> empty;
    * person -> the groups in their membership rows that exist and belong to
      their own tenant;
    * agent -> delegated access: never more than the person it acts for.
      The agent's own membership rows are the admin tool's limit on that agent,
      so the agent gets the groups present in BOTH its own valid rows and the
      person's (owner decision OA-1). An agent whose person is missing, revoked, not a person, or in
      another tenant gets nothing (a delegation from nobody is no delegation).
    Nothing ever crosses a tenant.
    """
    empty = VisibleSet(principal_id, None, frozenset())
    if not is_lookup_id(principal_id):
        return empty
    principal = store.principal(principal_id)
    if principal is None or principal["status"] != "active":
        return empty
    own = _member_groups(store, principal)
    if principal["kind"] == "person":
        return VisibleSet(principal_id, principal["tenant"], own)
    if principal["kind"] == "agent":
        person = store.principal(principal["acts_for"]) if principal["acts_for"] else None
        if (person is None or person["kind"] != "person" or person["status"] != "active"
                or person["tenant"] != principal["tenant"]):
            return empty
        return VisibleSet(principal_id, principal["tenant"], own & _member_groups(store, person))
    return empty


def _member_groups(store, principal) -> frozenset[str]:
    """Groups named in the principal's membership rows that exist in the principal's own tenant."""
    groups = set()
    for group_id in store.membership_rows(principal["id"]):
        group = store.group(group_id)
        if group is not None and group["tenant"] == principal["tenant"]:
            groups.add(group_id)
    return frozenset(groups)


# DECISION: ADR-007
# A card (and any fact on it) is visible only when BOTH hold: its ACL group is in
# the requester's visible set, and its entity belongs to the requester's tenant.
# A visible set that is empty (tenant None) can never match, so this fails closed.
def can_see(visible: VisibleSet, acl_group, entity_tenant) -> bool:
    return (visible.tenant is not None and entity_tenant == visible.tenant
            and acl_group in visible.groups)
