"""Card compiler and the derived tables (cd_*) that hold compiled cards."""
from __future__ import annotations

import hashlib
import re

from .model import Card

_DDL = (
    "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL, "
    "digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group))",
    "CREATE TABLE IF NOT EXISTS cd_card_facts(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
    "fact_id INTEGER NOT NULL, PRIMARY KEY (entity_id, acl_group, fact_id))",
    "CREATE INDEX IF NOT EXISTS cd_card_facts_fact ON cd_card_facts(fact_id)",
)


def digest_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_LINE_BREAKS = re.compile("[\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]")   # everything str.splitlines() splits on


def _inline(value) -> str:
    """A row field as text that cannot start a new card line (a card has one line per fact)."""
    return _LINE_BREAKS.sub(" ", str(value))


def compile_text(name: str, aliases, facts) -> str:
    # DECISION: ADR-010
    # Cards are compiled in code from rows, never from free text. Same rows -> byte-identical text.
    lines = [f"# {_inline(name)}"]
    aliases = sorted(aliases)
    if aliases:
        lines.append("aliases: " + ", ".join(_inline(a) for a in aliases))
    for f in sorted(facts, key=lambda f: (f["attribute"], f["id"])):
        lines.append(f"{_inline(f['attribute'])}: {_inline(f['value'])} "
                     f"(valid_from {_inline(f['valid_from'])}, source {_inline(f['source'])})")
    return "\n".join(lines)


class CardTable:
    """Reads and writes compiled cards in the store's connection (so they share the store's transaction)."""

    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        with store.transaction():
            for stmt in _DDL:
                self.conn.execute(stmt)

    # ------------------------------------------------------------ compile
    def _write(self, entity_id: str, group: str, name: str, aliases, facts) -> None:
        text = compile_text(name, aliases, facts)
        self.conn.execute("INSERT OR REPLACE INTO cd_cards VALUES (?,?,?,?)",
                          (entity_id, group, text, digest_of(text)))
        self.conn.execute("DELETE FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (entity_id, group))
        self.conn.executemany("INSERT INTO cd_card_facts VALUES (?,?,?)",
                              [(entity_id, group, f["id"]) for f in sorted(facts, key=lambda f: f["id"])])

    def _drop(self, entity_id: str, group: str) -> None:
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (entity_id, group))
        self.conn.execute("DELETE FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (entity_id, group))

    def recompile(self, pairs) -> None:
        """Recompile the given (entity_id, acl_group) cards from the store's current head facts."""
        store = self.store
        with store.transaction():
            for entity_id, group in sorted(set(pairs)):
                entity = store.entity(entity_id)
                facts = [f for f in store.head_facts(entity_id) if f["acl_group"] == group] if entity else []
                if entity is None or not facts:
                    self._drop(entity_id, group)
                else:
                    self._write(entity_id, group, entity["name"], store.aliases(entity_id), facts)

    def rebuild(self) -> None:
        """Recompile every card from the store."""
        store = self.store
        with store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            self.conn.execute("DELETE FROM cd_card_facts")
            by_pair: dict[tuple[str, str], list[dict]] = {}
            for f in store.head_facts():
                by_pair.setdefault((f["entity_id"], f["acl_group"]), []).append(f)
            for (entity_id, group), facts in sorted(by_pair.items()):
                entity = store.entity(entity_id)
                if entity is not None:
                    self._write(entity_id, group, entity["name"], store.aliases(entity_id), facts)

    # ------------------------------------------------------------ read
    def pairs_listing(self, fact_id: int) -> list[tuple[str, str]]:
        return [(r[0], r[1]) for r in self.conn.execute(
            "SELECT entity_id, acl_group FROM cd_card_facts WHERE fact_id = ?", (fact_id,))]

    def cards_of(self, entity_id: str) -> list[Card]:
        """Every compiled card of an entity (all groups), ordered by acl_group. No access check here."""
        out = []
        for group, text, digest in self.conn.execute(
                "SELECT acl_group, text, digest FROM cd_cards WHERE entity_id = ?", (entity_id,)):
            ids = tuple(sorted(r[0] for r in self.conn.execute(
                "SELECT fact_id FROM cd_card_facts WHERE entity_id = ? AND acl_group = ?", (entity_id, group))))
            out.append(Card(entity_id, group, text, ids, digest))
        out.sort(key=lambda c: c.acl_group)
        return out
