"""Entity card compiler and the derived `cd_*` tables.

Cards are compiled in code from store rows (never from free text): one card per (entity, ACL group) that holds at
least one head fact of that entity in that group.
"""
from __future__ import annotations

import hashlib

from .model import Card

_DDL = (
    "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL, "
    "digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group))",
    "CREATE TABLE IF NOT EXISTS cd_card_facts(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
    "fact_id INTEGER NOT NULL, PRIMARY KEY (entity_id, acl_group, fact_id))",
    "CREATE INDEX IF NOT EXISTS cd_card_facts_fact ON cd_card_facts(fact_id)",
)


def compile_text(name: str, aliases, heads) -> str:
    # DECISION: ADR-010
    """Deterministic card text: same rows, byte-identical text."""
    lines = [f"# {name}"]
    aliases = sorted(aliases)
    if aliases:
        lines.append("aliases: " + ", ".join(aliases))
    for f in sorted(heads, key=lambda f: (f["attribute"], f["id"])):
        lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
    return "\n".join(lines)


class CardTable:
    """Reads and writes the derived card tables inside the store's connection."""

    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        with store.transaction():
            for ddl in _DDL:
                self.conn.execute(ddl)

    # ------------------------------------------------------------ compile
    def _compile(self, entity: dict, group: str, heads: list[dict]) -> None:
        """Write (or remove) the card of one (entity, group) from the given head facts of the entity."""
        # DECISION: ADR-010
        eid = entity["id"]
        facts = [f for f in heads if f["entity_id"] == eid and f["acl_group"] == group]
        self.conn.execute("DELETE FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (eid, group))
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (eid, group))
        if not facts:
            return
        text = compile_text(entity["name"], self.store.aliases(eid), facts)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.conn.execute("INSERT INTO cd_cards(entity_id, acl_group, text, digest) VALUES (?,?,?,?)",
                          (eid, group, text, digest))
        self.conn.executemany("INSERT INTO cd_card_facts(entity_id, acl_group, fact_id) VALUES (?,?,?)",
                              [(eid, group, f["id"]) for f in sorted(facts, key=lambda f: f["id"])])

    def recompile(self, entity_id: str, group: str) -> None:
        """Recompile one card from the store's current head facts (drops it if it no longer holds any)."""
        entity = self.store.entity(entity_id)
        if entity is None:
            # no entity row: no name, no tenant, nothing to show; make sure no card lingers
            self.conn.execute("DELETE FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (entity_id, group))
            self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (entity_id, group))
            return
        self._compile(entity, group, self.store.head_facts(entity_id))

    def rebuild(self) -> None:
        """Recompile every card from the store."""
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_card_facts")
            self.conn.execute("DELETE FROM cd_cards")
            by_entity: dict[str, list[dict]] = {}
            for f in self.store.head_facts():
                by_entity.setdefault(f["entity_id"], []).append(f)
            for eid in sorted(by_entity):
                entity = self.store.entity(eid)
                if entity is None:
                    continue
                for group in sorted({f["acl_group"] for f in by_entity[eid]}):
                    self._compile(entity, group, by_entity[eid])

    # ------------------------------------------------------------ read
    def listing(self, fact_id: int) -> set[tuple[str, str]]:
        """(entity, group) of every stored card that lists the fact version."""
        return {(r[0], r[1]) for r in self.conn.execute(
            "SELECT entity_id, acl_group FROM cd_card_facts WHERE fact_id = ?", (fact_id,))}

    def for_entity(self, entity_id: str) -> list[Card]:
        """All stored cards of an entity, ordered by acl_group (no access filtering here)."""
        rows = self.conn.execute(
            "SELECT acl_group, text, digest FROM cd_cards WHERE entity_id = ? ORDER BY acl_group", (entity_id,)
        ).fetchall()
        out = []
        for group, text, digest in rows:
            fids = tuple(r[0] for r in self.conn.execute(
                "SELECT fact_id FROM cd_card_facts WHERE entity_id = ? AND acl_group = ? ORDER BY fact_id",
                (entity_id, group)))
            out.append(Card(entity_id, group, text, fids, digest))
        return out
