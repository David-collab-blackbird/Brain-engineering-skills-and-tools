"""Fact store for WP-E15C (provided by the engineer; builders must not modify it).

SQLite store: tenants, principals, ACL groups, memberships, entities (+ aliases),
keyed fact versions and notes with value mentions. Plain dicts are returned.
``store.conn`` is the sqlite3 connection; derived tables (``cd_*``) may be added
to it. Write methods do NOT commit: the caller owns the transaction (use
``with store.transaction(): ...``). Methods marked [test] are for tests to change
the world after the Brain was built.
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE tenants(id TEXT PRIMARY KEY);
CREATE TABLE principals(id TEXT PRIMARY KEY, tenant TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('person','agent')),
    status TEXT NOT NULL CHECK (status IN ('active','revoked')),
    acts_for TEXT, display_name TEXT NOT NULL);
CREATE TABLE acl_groups(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, label TEXT NOT NULL);
CREATE TABLE memberships(principal_id TEXT NOT NULL, group_id TEXT NOT NULL, PRIMARY KEY (principal_id, group_id));
CREATE TABLE entities(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, name TEXT NOT NULL);
CREATE TABLE aliases(entity_id TEXT NOT NULL, alias TEXT NOT NULL, PRIMARY KEY (entity_id, alias));
CREATE TABLE facts(
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL, source_entity_id TEXT NOT NULL, attribute TEXT NOT NULL,
    entity_id TEXT NOT NULL, value TEXT NOT NULL, valid_from TEXT NOT NULL, source TEXT NOT NULL,
    acl_group TEXT NOT NULL, superseded_by INTEGER);
CREATE INDEX facts_key ON facts(source_system, source_entity_id, attribute);
CREATE INDEX facts_entity ON facts(entity_id);
CREATE TABLE notes(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('active','erased','quarantined')));
CREATE TABLE mentions(note_id TEXT NOT NULL, position INTEGER NOT NULL, fact_id INTEGER NOT NULL,
    PRIMARY KEY (note_id, position));
"""

FACT_COLS = ("id", "source_system", "source_entity_id", "attribute", "entity_id", "value", "valid_from",
             "source", "acl_group", "superseded_by")


def _fact(row):
    return None if row is None else dict(zip(FACT_COLS, row))


class FactStore:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.isolation_level = None          # explicit transactions only
        self._depth = 0

    # ------------------------------------------------------------ setup
    @classmethod
    def empty(cls, path: str = ":memory:") -> "FactStore":
        conn = sqlite3.connect(path)
        conn.executescript(SCHEMA)
        return cls(conn)

    @classmethod
    def from_fixture(cls, fixture, path: str = ":memory:") -> "FactStore":
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text(encoding="utf-8"))
        s = cls.empty(path)
        c = s.conn
        with s.transaction():
            c.executemany("INSERT INTO tenants VALUES (?)", [(t,) for t in fixture["tenants"]])
            c.executemany("INSERT INTO principals VALUES (?,?,?,?,?,?)",
                          [(p["id"], p["tenant"], p["kind"], p["status"], p.get("acts_for"), p["display_name"])
                           for p in fixture["principals"]])
            c.executemany("INSERT INTO acl_groups VALUES (?,?,?)",
                          [(g["id"], g["tenant"], g["label"]) for g in fixture["groups"]])
            c.executemany("INSERT INTO memberships VALUES (?,?)",
                          [(m["principal"], m["group"]) for m in fixture["memberships"]])
            for e in fixture["entities"]:
                c.execute("INSERT INTO entities VALUES (?,?,?)", (e["id"], e["tenant"], e["name"]))
                c.executemany("INSERT INTO aliases VALUES (?,?)", [(e["id"], a) for a in e.get("aliases", [])])
            for f in fixture["facts"]:
                c.execute("INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(f[k] for k in FACT_COLS))
            for n in fixture["notes"]:
                c.execute("INSERT INTO notes VALUES (?,?,?,?,?)", (n["id"], n["tenant"], n["acl_group"], n["text"],
                                                                  n["state"]))
                c.executemany("INSERT INTO mentions VALUES (?,?,?)",
                              [(n["id"], i, fid) for i, fid in enumerate(n.get("mentions", []))])
        return s

    @contextlib.contextmanager
    def transaction(self):
        """Nestable transaction (savepoints). Rolls back on exception."""
        name = f"sp{self._depth}"
        if self._depth == 0:
            self.conn.execute("BEGIN")
        else:
            self.conn.execute(f"SAVEPOINT {name}")
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("ROLLBACK")
            else:
                self.conn.execute(f"ROLLBACK TO {name}")
                self.conn.execute(f"RELEASE {name}")
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self.conn.execute("COMMIT")
            else:
                self.conn.execute(f"RELEASE {name}")

    # ------------------------------------------------------------ reads
    def principal(self, pid):
        r = self.conn.execute("SELECT id, tenant, kind, status, acts_for, display_name FROM principals WHERE id = ?",
                              (pid,)).fetchone()
        return None if r is None else dict(zip(("id", "tenant", "kind", "status", "acts_for", "display_name"), r))

    def membership_rows(self, pid) -> list[str]:
        """Raw group ids (sorted). Rows may name missing groups or groups in another tenant."""
        return [r[0] for r in self.conn.execute(
            "SELECT group_id FROM memberships WHERE principal_id = ? ORDER BY group_id", (pid,))]

    def group(self, gid):
        r = self.conn.execute("SELECT id, tenant, label FROM acl_groups WHERE id = ?", (gid,)).fetchone()
        return None if r is None else dict(zip(("id", "tenant", "label"), r))

    def entities(self) -> list[dict]:
        """All entities {id, tenant, name}, ordered by id."""
        return [dict(zip(("id", "tenant", "name"), r)) for r in
                self.conn.execute("SELECT id, tenant, name FROM entities ORDER BY id")]

    def entity(self, eid):
        r = self.conn.execute("SELECT id, tenant, name FROM entities WHERE id = ?", (eid,)).fetchone()
        return None if r is None else dict(zip(("id", "tenant", "name"), r))

    def aliases(self, eid) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT alias FROM aliases WHERE entity_id = ? ORDER BY alias",
                                                (eid,))]

    def fact(self, fid):
        return _fact(self.conn.execute(f"SELECT {', '.join(FACT_COLS)} FROM facts WHERE id = ?", (fid,)).fetchone())

    def head(self, source_system, source_entity_id, attribute):
        """The current head version of a key, or None (no versions, or released)."""
        return _fact(self.conn.execute(
            f"SELECT {', '.join(FACT_COLS)} FROM facts WHERE source_system = ? AND source_entity_id = ? "
            "AND attribute = ? AND superseded_by IS NULL ORDER BY id DESC LIMIT 1",
            (source_system, source_entity_id, attribute)).fetchone())

    def head_of(self, fid):
        """Follow superseded_by from a version to its head (None if the chain ends in a release)."""
        seen = set()
        f = self.fact(fid)
        while f is not None and f["superseded_by"] is not None and f["id"] not in seen:
            seen.add(f["id"])
            if f["superseded_by"] == -1:
                return None
            f = self.fact(f["superseded_by"])
        return f

    def head_facts(self, entity_id=None) -> list[dict]:
        """All head facts (superseded_by IS NULL), optionally for one entity, ordered by id."""
        q = f"SELECT {', '.join(FACT_COLS)} FROM facts WHERE superseded_by IS NULL"
        args = ()
        if entity_id is not None:
            q += " AND entity_id = ?"
            args = (entity_id,)
        return [_fact(r) for r in self.conn.execute(q + " ORDER BY id", args)]

    def notes(self) -> list[dict]:
        """All notes {id, tenant, acl_group, text, state}, ordered by id."""
        return [dict(zip(("id", "tenant", "acl_group", "text", "state"), r)) for r in
                self.conn.execute("SELECT id, tenant, acl_group, text, state FROM notes ORDER BY id")]

    def note(self, nid):
        r = self.conn.execute("SELECT id, tenant, acl_group, text, state FROM notes WHERE id = ?", (nid,)).fetchone()
        return None if r is None else dict(zip(("id", "tenant", "acl_group", "text", "state"), r))

    def mentions(self, nid) -> list[int]:
        """Fact version ids quoted by a note, in mention order."""
        return [r[0] for r in self.conn.execute("SELECT fact_id FROM mentions WHERE note_id = ? ORDER BY position",
                                                (nid,))]

    # ------------------------------------------------------- fact writes (no commit)
    def insert_fact(self, *, source_system, source_entity_id, attribute, entity_id, value, valid_from, source,
                    acl_group) -> int:
        cur = self.conn.execute(
            "INSERT INTO facts(source_system, source_entity_id, attribute, entity_id, value, valid_from, source, "
            "acl_group, superseded_by) VALUES (?,?,?,?,?,?,?,?,NULL)",
            (source_system, source_entity_id, attribute, entity_id, value, valid_from, source, acl_group))
        return cur.lastrowid

    def supersede(self, old_id: int, new_id: int) -> None:
        self.conn.execute("UPDATE facts SET superseded_by = ? WHERE id = ? AND superseded_by IS NULL",
                          (new_id, old_id))

    # ------------------------------------------------------- [test] world changes (commit)
    def revoke(self, pid):
        with self.transaction():
            self.conn.execute("UPDATE principals SET status = 'revoked' WHERE id = ?", (pid,))

    def add_membership(self, pid, gid):
        with self.transaction():
            self.conn.execute("INSERT OR IGNORE INTO memberships VALUES (?,?)", (pid, gid))

    def remove_membership(self, pid, gid):
        with self.transaction():
            self.conn.execute("DELETE FROM memberships WHERE principal_id = ? AND group_id = ?", (pid, gid))

    def add_note(self, nid, *, tenant, acl_group, text, mentions=()):
        with self.transaction():
            self.conn.execute("INSERT INTO notes VALUES (?,?,?,?, 'active')", (nid, tenant, acl_group, text))
            self.conn.executemany("INSERT INTO mentions VALUES (?,?,?)",
                                  [(nid, i, f) for i, f in enumerate(mentions)])

    def set_note_state(self, nid, state):
        with self.transaction():
            if state == "erased":
                self.conn.execute("UPDATE notes SET state = 'erased', text = '' WHERE id = ?", (nid,))
            else:
                self.conn.execute("UPDATE notes SET state = ? WHERE id = ?", (state, nid))

    def release(self, fid):
        """[test] Release a head fact with no successor (superseded_by = -1): the key has no head."""
        with self.transaction():
            self.conn.execute("UPDATE facts SET superseded_by = -1 WHERE id = ? AND superseded_by IS NULL", (fid,))
