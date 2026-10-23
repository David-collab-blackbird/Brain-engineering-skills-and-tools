"""Who may see what: the visible set, record visibility and the exit check.

Access is decided from the record store on every call and is never cached
(R2). Everything here fails closed: anything unknown, revoked, missing or
mismatched means "nothing visible".
"""
from __future__ import annotations

from .models import VisibleSet


def is_storable_id(value) -> bool:
    """True for a string the store could hold as an id.

    Anything else (not a string, or text with a lone surrogate, which UTF-8 cannot
    encode) cannot be a principal or record id. Callers treat it as unknown instead
    of passing it on, because the database driver would raise on it (R7).
    """
    if not isinstance(value, str):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def id_text(value) -> str:
    """An id as text. A string is returned as it is; anything else as a short description.

    Never raises: a hostile object (a failing __repr__, a 5000-digit int, a list nested
    past the recursion limit) must not turn "unknown id" into an error (R7).
    """
    if isinstance(value, str):
        return value
    try:
        return repr(value)[:200]
    except Exception:
        return "<unprintable>"


def _nothing(principal_id) -> VisibleSet:
    return VisibleSet(principal_id=id_text(principal_id), tenant=None, groups=frozenset())


# DECISION: ADR-007
def resolve_visible_set(store, principal_id) -> VisibleSet:
    """The requester's visible set, resolved from the store right now (R2).

    - Unknown or revoked principal: empty.
    - A person sees the groups named in their membership rows that exist and
      belong to the person's own tenant. Every other row is ignored.
    - An agent acts with the access of the person it acts for: that person's
      groups are the most it can ever see. The agent's own membership rows
      only limit that (the owner's admin tool maintains them "to limit what
      each agent may use"): it sees the groups in both lists, so an own row
      can never widen it, and an agent with no usable rows sees nothing. It
      gets nothing unless the agent is active and the person exists, is an
      active person (not another agent) and is in the agent's tenant.
      Brief R2 and the data notes can be read the other way (own rows ignored);
      this is the reading that fails closed. See build/questions.json.
    - No role, title or ownership grants anything (R2a): there is no code
      path that looks at what a principal is called or what it owns.
    """
    if not is_storable_id(principal_id):
        return _nothing(principal_id)
    principal = store.principal(principal_id)
    if principal is None or principal["status"] != "active":
        return _nothing(principal_id)

    member = principal
    if principal["kind"] == "agent":
        acts_for = principal["acts_for"]
        member = store.principal(acts_for) if isinstance(acts_for, str) else None
        if (member is None
                or member["status"] != "active"
                or member["kind"] != "person"
                or member["tenant"] != principal["tenant"]):
            return _nothing(principal_id)

    tenant = principal["tenant"]
    groups = _member_groups(store, member["id"], tenant)
    if member is not principal:
        groups &= _member_groups(store, principal["id"], tenant)
    return VisibleSet(principal_id=principal_id, tenant=tenant, groups=frozenset(groups))


def _member_groups(store, principal_id: str, tenant: str) -> set[str]:
    """Groups named in the principal's membership rows that exist and belong to `tenant`."""
    groups = set()
    for group_id in store.membership_rows(principal_id):
        group = store.group(group_id)
        if group is not None and group["tenant"] == tenant:
            groups.add(group_id)
    return groups


def is_visible(record: dict, visible: VisibleSet) -> bool:
    """True if this record row's tenant and access group are in the visible set."""
    return (visible.tenant is not None
            and record["tenant"] == visible.tenant
            and record["acl_group"] in visible.groups)


# DECISION: ADR-007
def read_visible(store, visible: VisibleSet, record_id) -> dict | None:
    """The record's current version if it is active and visible, else None.

    Not found, hidden, erased and quarantined all give the same None (R7).
    """
    if not is_storable_id(record_id):
        return None
    record = store.current(record_id)
    if record is None or record["state"] != "active" or not is_visible(record, visible):
        return None
    return record


# DECISION: ADR-007
def exit_check(store, visible: VisibleSet, record_id: str, indexed_version: int) -> dict | None:
    """Re-validate one candidate against the store before it is returned (R6).

    Returns the current version's row only if the record still exists, its
    current version is active, that version is the one that was indexed, and it
    is visible to this request. Otherwise None, and the caller moves on to the
    next-best candidate.
    """
    record = read_visible(store, visible, record_id)
    if record is None or record["version"] != indexed_version:
        return None
    return record
