"""Record store for WP-E15 (provided by the engineer; builders must not modify it).

A small SQLite store holding tenants, principals, access-control groups,
memberships and versioned records. It is the source of truth: a retrieval
index built from it may go stale, and the store's write methods below are how
tests simulate the world changing after an index was built.

Every method returns plain dicts (or lists of dicts) so callers never depend
on sqlite3.Row.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE tenants(
    id TEXT PRIMARY KEY
);
CREATE TABLE principals(
    id TEXT PRIMARY KEY,
    tenant TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('person', 'agent')),
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
    acts_for TEXT,                -- agents only: the person the agent acts for
    display_name TEXT NOT NULL
);
CREATE TABLE acl_groups(
    id TEXT PRIMARY KEY,
    tenant TEXT NOT NULL,
    label TEXT NOT NULL
);
CREATE TABLE memberships(
    principal_id TEXT NOT NULL,
    group_id TEXT NOT NULL,       -- not a foreign key: rows may name missing groups
    PRIMARY KEY (principal_id, group_id)
);
CREATE TABLE records(
    id TEXT NOT NULL,
    version INTEGER NOT NULL,
    tenant TEXT NOT NULL,
    acl_group TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('active', 'erased', 'quarantined')),
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    PRIMARY KEY (id, version)
);
CREATE INDEX records_current ON records(is_current, id);
"""

_RECORD_COLS = "id, version, tenant, acl_group, title, body, state"


def _record(row: tuple | None) -> dict | None:
    if row is None:
        return None
    keys = ("id", "version", "tenant", "acl_group", "title", "body", "state")
    return dict(zip(keys, row))


class RecordStore:
    """SQLite-backed record store.

    ``store.conn`` is the sqlite3 connection. A retrieval index may add its own
    tables to this connection (WP-E15 requires tables named ``vr_*``); it must
    not alter the store's own tables.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ------------------------------------------------------------------ setup
    @classmethod
    def empty(cls, path: str = ":memory:") -> "RecordStore":
        conn = sqlite3.connect(path)
        conn.executescript(SCHEMA)
        conn.commit()
        return cls(conn)

    @classmethod
    def from_fixture(cls, fixture: dict | str | Path, path: str = ":memory:") -> "RecordStore":
        """Create a store from a fixture dict or a JSON file path."""
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text(encoding="utf-8"))
        store = cls.empty(path)
        c = store.conn
        c.executemany("INSERT INTO tenants(id) VALUES (?)", [(t,) for t in fixture["tenants"]])
        c.executemany(
            "INSERT INTO principals(id, tenant, kind, status, acts_for, display_name) VALUES (?,?,?,?,?,?)",
            [(p["id"], p["tenant"], p["kind"], p["status"], p.get("acts_for"), p["display_name"])
             for p in fixture["principals"]],
        )
        c.executemany(
            "INSERT INTO acl_groups(id, tenant, label) VALUES (?,?,?)",
            [(g["id"], g["tenant"], g["label"]) for g in fixture["groups"]],
        )
        c.executemany(
            "INSERT INTO memberships(principal_id, group_id) VALUES (?,?)",
            [(m["principal"], m["group"]) for m in fixture["memberships"]],
        )
        rows = []
        for r in fixture["records"]:
            for v in r["versions"]:
                rows.append((r["id"], v["version"], r["tenant"], v["acl_group"], v["title"], v["body"],
                             v["state"], 1 if v["version"] == r["current_version"] else 0))
        c.executemany(
            "INSERT INTO records(id, version, tenant, acl_group, title, body, state, is_current) "
            "VALUES (?,?,?,?,?,?,?,?)", rows)
        c.commit()
        return store

    # ------------------------------------------------------------------ reads
    def principal(self, principal_id: str) -> dict | None:
        """{id, tenant, kind, status, acts_for, display_name} or None if unknown."""
        row = self.conn.execute(
            "SELECT id, tenant, kind, status, acts_for, display_name FROM principals WHERE id = ?",
            (principal_id,)).fetchone()
        if row is None:
            return None
        return dict(zip(("id", "tenant", "kind", "status", "acts_for", "display_name"), row))

    def membership_rows(self, principal_id: str) -> list[str]:
        """Raw group ids from the memberships table, sorted.

        Rows are data, not a guarantee: a row may name a group that does not
        exist, or a group that belongs to another tenant.
        """
        return [r[0] for r in self.conn.execute(
            "SELECT group_id FROM memberships WHERE principal_id = ? ORDER BY group_id", (principal_id,))]

    def group(self, group_id: str) -> dict | None:
        """{id, tenant, label} or None if the group does not exist."""
        row = self.conn.execute("SELECT id, tenant, label FROM acl_groups WHERE id = ?", (group_id,)).fetchone()
        return None if row is None else dict(zip(("id", "tenant", "label"), row))

    def current(self, record_id: str) -> dict | None:
        """The current version of a record, in any state, or None if no such record.

        Keys: id, version, tenant, acl_group, title, body, state.
        """
        return _record(self.conn.execute(
            f"SELECT {_RECORD_COLS} FROM records WHERE id = ? AND is_current = 1", (record_id,)).fetchone())

    def version(self, record_id: str, version: int) -> dict | None:
        """A specific version of a record, or None."""
        return _record(self.conn.execute(
            f"SELECT {_RECORD_COLS} FROM records WHERE id = ? AND version = ?", (record_id, version)).fetchone())

    def current_records(self) -> list[dict]:
        """Every record's current version, in any state, ordered by id."""
        return [_record(r) for r in self.conn.execute(
            f"SELECT {_RECORD_COLS} FROM records WHERE is_current = 1 ORDER BY id")]

    # ----------------------------------------------------------------- writes
    # Tests use these to change the world after an index was built.
    def add_tenant(self, tenant_id: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO tenants(id) VALUES (?)", (tenant_id,))
        self.conn.commit()

    def add_principal(self, principal_id: str, *, tenant: str, kind: str = "person", status: str = "active",
                      acts_for: str | None = None, display_name: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO principals(id, tenant, kind, status, acts_for, display_name) VALUES (?,?,?,?,?,?)",
            (principal_id, tenant, kind, status, acts_for, display_name or principal_id))
        self.conn.commit()

    def revoke(self, principal_id: str) -> None:
        self.conn.execute("UPDATE principals SET status = 'revoked' WHERE id = ?", (principal_id,))
        self.conn.commit()

    def add_group(self, group_id: str, *, tenant: str, label: str | None = None) -> None:
        self.conn.execute("INSERT INTO acl_groups(id, tenant, label) VALUES (?,?,?)",
                          (group_id, tenant, label or group_id))
        self.conn.commit()

    def add_membership(self, principal_id: str, group_id: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO memberships(principal_id, group_id) VALUES (?,?)",
                          (principal_id, group_id))
        self.conn.commit()

    def remove_membership(self, principal_id: str, group_id: str) -> None:
        self.conn.execute("DELETE FROM memberships WHERE principal_id = ? AND group_id = ?",
                          (principal_id, group_id))
        self.conn.commit()

    def put(self, record_id: str, *, acl_group: str, title: str, body: str, tenant: str | None = None) -> int:
        """Write a new current version (version 1 for a new id). Returns the version number.

        The tenant defaults to the group's tenant. The previous version stays in
        the table with is_current = 0.
        """
        if tenant is None:
            g = self.group(acl_group)
            if g is None:
                raise ValueError(f"unknown group {acl_group!r}; pass tenant explicitly")
            tenant = g["tenant"]
        row = self.conn.execute("SELECT MAX(version) FROM records WHERE id = ?", (record_id,)).fetchone()
        version = (row[0] or 0) + 1
        self.conn.execute("UPDATE records SET is_current = 0 WHERE id = ?", (record_id,))
        self.conn.execute(
            "INSERT INTO records(id, version, tenant, acl_group, title, body, state, is_current) "
            "VALUES (?,?,?,?,?,?, 'active', 1)", (record_id, version, tenant, acl_group, title, body))
        self.conn.commit()
        return version

    def reclassify(self, record_id: str, acl_group: str) -> None:
        """Move the current version to another group in place (no new version)."""
        self.conn.execute("UPDATE records SET acl_group = ? WHERE id = ? AND is_current = 1", (acl_group, record_id))
        self.conn.commit()

    def erase(self, record_id: str) -> None:
        """Privacy erasure: every version becomes state 'erased' with empty title and body."""
        self.conn.execute("UPDATE records SET state = 'erased', title = '', body = '' WHERE id = ?", (record_id,))
        self.conn.commit()

    def quarantine(self, record_id: str) -> None:
        """Quarantine the current version (content kept, never served)."""
        self.conn.execute("UPDATE records SET state = 'quarantined' WHERE id = ? AND is_current = 1", (record_id,))
        self.conn.commit()

    def restore(self, record_id: str) -> None:
        """Lift a quarantine on the current version."""
        self.conn.execute(
            "UPDATE records SET state = 'active' WHERE id = ? AND is_current = 1 AND state = 'quarantined'",
            (record_id,))
        self.conn.commit()


def load_fixture(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ids(records: Iterable[dict]) -> list[str]:
    return [r["id"] for r in records]
