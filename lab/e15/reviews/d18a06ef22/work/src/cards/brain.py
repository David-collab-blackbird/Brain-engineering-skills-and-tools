"""Keyed facts, entity cards and context assembly (WP-E15C)."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: str | None
    groups: frozenset[str]


@dataclass(frozen=True)
class Card:
    entity_id: str
    acl_group: str
    text: str
    fact_ids: tuple[int, ...]
    digest: str


@dataclass(frozen=True)
class ContextItem:
    kind: str
    ref: str
    text: str
    reason: str
    annotations: tuple[str, ...] = ()


_DDL = """CREATE TABLE IF NOT EXISTS cd_cards(
    entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL,
    fact_ids TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group))"""

PIN_LIMIT = 3


class Brain:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        self.conn.execute(_DDL)
        self.rebuild()

    # ------------------------------------------------------------ visibility
    # DECISION: ADR-007
    def _person_groups(self, p) -> frozenset[str]:
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return frozenset(out)

    # DECISION: ADR-007
    def visible_set(self, principal_id) -> VisibleSet:
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            groups = self._person_groups(p)
            if p["kind"] == "agent":
                # Agent: delegated access of the person it acts for, capped by
                # its own membership rows (fail closed; see build/questions.json).
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                groups = groups & self._person_groups(owner)
            return VisibleSet(p["id"], p["tenant"], frozenset(groups))
        except Exception:
            return empty

    # ------------------------------------------------------------ compile
    # DECISION: ADR-010
    def _compile_entity(self, entity_id):
        """Recompile all cards of one entity from head rows (caller holds the transaction)."""
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        ent = self.store.entity(entity_id)
        if ent is None:
            return
        by_group: dict[str, list[dict]] = {}
        for f in self.store.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(self.store.aliases(entity_id))
        for group, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            self.conn.execute(
                "INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                (entity_id, group, text, json.dumps(sorted(f["id"] for f in facts)),
                 hashlib.sha256(text.encode("utf-8")).hexdigest()))

    def rebuild(self):
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            ids = {e["id"] for e in self.store.entities()}
            ids |= {f["entity_id"] for f in self.store.head_facts()}
            for eid in sorted(ids):
                self._compile_entity(eid)

    # ------------------------------------------------------------ upsert
    # DECISION: ADR-009
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source, acl_group):
        s = self.store
        with s.transaction():
            old = s.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new = s.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                attribute=attribute, entity_id=entity_id, value=value, valid_from=valid_from,
                                source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                s.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile_entity(eid)
            return new

    # ------------------------------------------------------------ cards
    def _row_card(self, r) -> Card:
        return Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4])

    # DECISION: ADR-007
    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if vs.tenant is None or ent is None or ent["tenant"] != vs.tenant:
                return ()
            rows = self.conn.execute(
                "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
                "ORDER BY acl_group", (entity_id,)).fetchall()
            cs = (self._row_card(r) for r in rows if r[1] in vs.groups)
            return tuple(c for c in cs if self._card_valid(c, vs))
        except Exception:
            return ()

    def card(self, entity_id, principal_id) -> Card | None:
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ linking
    def _link(self, request_tokens, tenant):
        """Return [(first_pos, entity_id)] for accepted matches, longest first."""
        n = len(request_tokens)
        matches = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                t = tokens(name)
                m = len(t)
                if m == 0:
                    continue
                for i in range(n - m + 1):
                    if request_tokens[i:i + m] == t:
                        matches.append((m, e["id"], i))
        matches.sort(key=lambda x: (-x[0], x[1], x[2]))
        taken = [False] * n
        first: dict[str, int] = {}
        for m, eid, i in matches:
            if any(taken[i:i + m]):
                continue
            for j in range(i, i + m):
                taken[j] = True
            first[eid] = min(first.get(eid, i), i)
        return sorted((pos, eid) for eid, pos in first.items())

    # ------------------------------------------------------------ assembly
    def _valid_note(self, nid, vs):
        n = self.store.note(nid)
        if n is None or n["state"] != "active" or n["tenant"] != vs.tenant or n["acl_group"] not in vs.groups:
            return None
        return n

    # DECISION: ADR-009
    def _annotations(self, nid, vs) -> tuple[str, ...]:
        out = []
        for fid in self.store.mentions(nid):
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            head = self.store.head_of(fid)
            if head is not None and head["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {head['valid_from']}; current value {head['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _card_valid(self, card, vs) -> bool:
        if card.acl_group not in vs.groups:
            return False
        ent = self.store.entity(card.entity_id)
        if ent is None or ent["tenant"] != vs.tenant:
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] != card.acl_group
                    or f["entity_id"] != card.entity_id):
                return False
        return True

    # DECISION: ADR-010
    def assemble(self, request, principal_id, k=10) -> list[ContextItem]:
        try:
            return self._assemble(request, principal_id, k)
        except Exception:
            return []

    def _assemble(self, request, principal_id, k):
        vs = self.visible_set(principal_id)
        if vs.tenant is None or k <= 0:
            return []
        qt = tokens(request)
        items: list[ContextItem] = []
        # pinned cards
        pins = []
        for _, eid in self._link(qt, vs.tenant):
            pins.extend(self.cards(eid, principal_id))
        for c in pins:
            if len(items) >= min(PIN_LIMIT, k):
                break
            if self._card_valid(c, vs):
                items.append(ContextItem("card", c.entity_id, c.text, "card", ()))
        # BM25 over visible active notes only
        slots = k - len(items)
        if slots > 0:
            docs = []
            for n in self.store.notes():
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups:
                    docs.append((n["id"], tokens(n["text"])))
            ranked = self._bm25(docs, qt)
            seen = set()
            for nid in ranked:
                if slots <= 0:
                    break
                if nid in seen:
                    continue
                n = self._valid_note(nid, vs)  # exit check
                if n is None:
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, n["text"], "search", self._annotations(nid, vs)))
                slots -= 1
        return items

    @staticmethod
    def _bm25(docs, query, k1=1.2, b=0.75):
        N = len(docs)
        if N == 0:
            return []
        avg = sum(len(t) for _, t in docs) / N
        terms = sorted(set(query))
        df = {w: sum(1 for _, t in docs if w in t) for w in terms}
        scored = []
        for nid, t in docs:
            score = 0.0
            for w in terms:
                if not df[w]:
                    continue
                tf = t.count(w)
                if not tf:
                    continue
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(t) / avg if avg else 1))
            if score > 0:
                scored.append((-score, nid))
        scored.sort()
        return [nid for _, nid in scored]
