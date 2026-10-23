"""Entity cards: compiled in code from store rows, kept in derived ``cd_`` tables.

A card is a pure function of (entity name, aliases, head facts of one entity in
one ACL group). Nothing here reads free text, and nothing is held in memory
between calls: the compiled cards live in the store's own connection, so a
rolled-back transaction rolls the cards back with the facts (R3).
"""
from __future__ import annotations

import hashlib

from .model import Card

# WITHOUT ROWID: the primary key is the table itself, so SQLite adds no automatic
# "sqlite_autoindex_..." object and every object this package creates is named cd_...
_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS cd_cards("
    " entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL, digest TEXT NOT NULL,"
    " PRIMARY KEY (entity_id, acl_group)) WITHOUT ROWID",
    "CREATE TABLE IF NOT EXISTS cd_card_facts("
    " entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, fact_id INTEGER NOT NULL,"
    " PRIMARY KEY (entity_id, acl_group, fact_id)) WITHOUT ROWID",
    "CREATE INDEX IF NOT EXISTS cd_card_facts_by_fact ON cd_card_facts(fact_id)",
)


# DECISION: ADR-010
# Cards are compiled in code from rows, never from free text:
#   line 1  "# <canonical name>"
#   line 2  "aliases: <aliases sorted, comma-separated>"   (left out when there are none)
#   then one line per head fact, sorted by attribute then fact id:
#           "<attribute>: <value> (valid_from <date>, source <source>)"
# Lines are joined with "\n", no trailing newline. The same rows always give the
# same bytes, so the digest changes only when the card's content does.
def compile_card(name: str, aliases, facts) -> tuple[str, tuple[int, ...], str]:
    """Return ``(text, fact_ids, digest)`` for one entity's head facts in one ACL group."""
    lines = [f"# {name}"]
    names = sorted(aliases)
    if names:
        lines.append("aliases: " + ", ".join(names))
    for f in sorted(facts, key=lambda f: (f["attribute"], f["id"])):
        lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
    text = "\n".join(lines)
    fact_ids = tuple(sorted(f["id"] for f in facts))
    return text, fact_ids, hashlib.sha256(text.encode("utf-8")).hexdigest()


class CardTable:
    """The derived tables ``cd_cards`` and ``cd_card_facts`` for one store.

    Every write goes through the store's transaction (nestable), so callers get
    all-or-nothing behaviour by wrapping a call in ``store.transaction()``.
    """

    def __init__(self, store):
        self._store = store

    def create_schema(self) -> None:
        with self._store.transaction():
            for statement in _SCHEMA:
                self._store.conn.execute(statement)

    # ------------------------------------------------------------------ compile
    # DECISION: ADR-010
    def rebuild(self) -> None:
        """Recompile every card from the store: drop all rows, then one card per (entity, group) with a head fact."""
        s = self._store
        with s.transaction():
            self.create_schema()            # also puts the tables back if a caller's rollback took them away
            s.conn.execute("DELETE FROM cd_card_facts")
            s.conn.execute("DELETE FROM cd_cards")
            buckets: dict[tuple[str, str], list[dict]] = {}
            for fact in s.head_facts():
                buckets.setdefault((fact["entity_id"], fact["acl_group"]), []).append(fact)
            for entity_id, acl_group in sorted(buckets):
                self._write(entity_id, acl_group, buckets[(entity_id, acl_group)])

    # DECISION: ADR-010
    def recompile(self, entity_id: str, acl_group: str) -> None:
        """Recompile the one card for (entity, group); remove it when no head fact is left in that group (R6)."""
        s = self._store
        with s.transaction():
            facts = [f for f in s.head_facts(entity_id) if f["acl_group"] == acl_group]
            self._delete(entity_id, acl_group)
            if facts:
                self._write(entity_id, acl_group, facts)

    def _write(self, entity_id: str, acl_group: str, facts: list[dict]) -> None:
        s = self._store
        entity = s.entity(entity_id)
        if entity is None:      # a fact about an entity the store does not know has no name to compile
            return
        text, fact_ids, digest = compile_card(entity["name"], s.aliases(entity_id), facts)
        s.conn.execute("INSERT INTO cd_cards VALUES (?,?,?,?)", (entity_id, acl_group, text, digest))
        s.conn.executemany("INSERT INTO cd_card_facts VALUES (?,?,?)",
                           [(entity_id, acl_group, fid) for fid in fact_ids])

    def _delete(self, entity_id: str, acl_group: str) -> None:
        c = self._store.conn
        c.execute("DELETE FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (entity_id, acl_group))
        c.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (entity_id, acl_group))

    # --------------------------------------------------------------------- read
    def listing(self, fact_id: int) -> list[tuple[str, str]]:
        """The (entity, group) of every card that lists this fact version."""
        return [(r[0], r[1]) for r in self._store.conn.execute(
            "SELECT entity_id, acl_group FROM cd_card_facts WHERE fact_id = ? ORDER BY entity_id, acl_group",
            (fact_id,))]

    def groups_of(self, entity_id: str) -> list[str]:
        """The ACL groups an entity has a card in, sorted. Group names only: no card text is read."""
        return [r[0] for r in self._store.conn.execute(
            "SELECT acl_group FROM cd_cards WHERE entity_id = ? ORDER BY acl_group", (entity_id,))]

    def get(self, entity_id: str, acl_group: str) -> Card | None:
        c = self._store.conn
        row = c.execute("SELECT text, digest FROM cd_cards WHERE entity_id = ? AND acl_group = ?",
                        (entity_id, acl_group)).fetchone()
        if row is None:
            return None
        fact_ids = tuple(r[0] for r in c.execute(
            "SELECT fact_id FROM cd_card_facts WHERE entity_id = ? AND acl_group = ? ORDER BY fact_id",
            (entity_id, acl_group)))
        return Card(entity_id, acl_group, row[0], fact_ids, row[1])
