"""Entity cards: compiled in code from store rows, kept in ``cd_*`` tables (R3, R4, R5, R6).

One card per (entity, ACL group) that holds at least one head fact of the entity
in that group. The text is built from rows only, never from free text, and the
same rows always give byte-identical text.
"""
from __future__ import annotations

import hashlib

from .model import Card

_DDL = (
    """CREATE TABLE IF NOT EXISTS cd_cards(
        entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL, digest TEXT NOT NULL,
        PRIMARY KEY (entity_id, acl_group)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS cd_card_facts(
        entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, fact_id INTEGER NOT NULL,
        PRIMARY KEY (entity_id, acl_group, fact_id)) WITHOUT ROWID""",
    "CREATE INDEX IF NOT EXISTS cd_card_facts_by_fact ON cd_card_facts(fact_id)",
)


def compile_text(name: str, aliases, facts) -> str:
    """The card text for one entity and one group.

    ``facts`` are head fact dicts of that entity in that group. Lines: the
    canonical name, the sorted aliases (omitted when there are none), then one
    line per fact sorted by attribute then fact id. Joined with newlines, no
    trailing newline.
    """
    # DECISION: ADR-010
    lines = [f"# {name}"]
    if aliases:
        lines.append("aliases: " + ", ".join(sorted(aliases)))
    for f in sorted(facts, key=lambda f: (f["attribute"], f["id"])):
        lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
    return "\n".join(lines)


def digest_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CardTable:
    """The derived card tables inside the store's own connection."""

    def __init__(self, store):
        self.store = store

    @property
    def conn(self):
        return self.store.conn

    def create(self) -> None:
        for ddl in _DDL:
            self.conn.execute(ddl)

    def exists(self) -> bool:
        """Whether both derived tables are present (an outer rollback can take them away)."""
        found = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('cd_cards', 'cd_card_facts')")}
        return len(found) == 2

    # ------------------------------------------------------------ compile
    def recompile(self, entity_id: str, acl_group: str) -> None:
        """Rebuild the one card for (entity, group) from the store, or remove it when it has no head fact."""
        # DECISION: ADR-010
        entity = self.store.entity(entity_id)
        facts = [f for f in self.store.head_facts(entity_id) if f["acl_group"] == acl_group]
        self._clear(entity_id, acl_group)
        if entity is not None and facts:
            self._write(entity, self.store.aliases(entity_id), acl_group, facts)

    def rebuild(self) -> None:
        """Recompile every card from the store, dropping cards that no longer have a head fact."""
        # DECISION: ADR-010
        self.conn.execute("DELETE FROM cd_card_facts")
        self.conn.execute("DELETE FROM cd_cards")
        by_key: dict[tuple[str, str], list[dict]] = {}
        for f in self.store.head_facts():
            by_key.setdefault((f["entity_id"], f["acl_group"]), []).append(f)
        for (entity_id, acl_group), facts in sorted(by_key.items()):
            entity = self.store.entity(entity_id)
            if entity is not None:
                self._write(entity, self.store.aliases(entity_id), acl_group, facts)

    def _clear(self, entity_id: str, acl_group: str) -> None:
        self.conn.execute("DELETE FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (entity_id, acl_group))
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (entity_id, acl_group))

    def _write(self, entity: dict, aliases, acl_group: str, facts: list[dict]) -> None:
        text = compile_text(entity["name"], aliases, facts)
        self.conn.execute("INSERT INTO cd_cards(entity_id, acl_group, text, digest) VALUES (?,?,?,?)",
                          (entity["id"], acl_group, text, digest_of(text)))
        self.conn.executemany("INSERT INTO cd_card_facts(entity_id, acl_group, fact_id) VALUES (?,?,?)",
                              [(entity["id"], acl_group, f["id"]) for f in facts])

    # ------------------------------------------------------------ read
    def keys_listing(self, fact_id: int) -> set[tuple[str, str]]:
        """The (entity, group) of every stored card that lists this fact version."""
        return {(r[0], r[1]) for r in self.conn.execute(
            "SELECT entity_id, acl_group FROM cd_card_facts WHERE fact_id = ?", (fact_id,))}

    def stored_cards(self, entity_id: str) -> list[Card]:
        """Every stored card of the entity, ordered by group. No access check: callers filter."""
        out = []
        for acl_group, text, digest in self.conn.execute(
                "SELECT acl_group, text, digest FROM cd_cards WHERE entity_id = ? ORDER BY acl_group", (entity_id,)):
            fact_ids = tuple(r[0] for r in self.conn.execute(
                "SELECT fact_id FROM cd_card_facts WHERE entity_id = ? AND acl_group = ? ORDER BY fact_id",
                (entity_id, acl_group)))
            out.append(Card(entity_id=entity_id, acl_group=acl_group, text=text, fact_ids=fact_ids, digest=digest))
        return out
