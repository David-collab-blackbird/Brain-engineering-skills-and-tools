"""WP-E15C entity cards and context assembly: keyed facts, cards compiled in code, per-requester assembly."""
import hashlib
import math
from dataclasses import dataclass

from factstore.text import tokens

__all__ = ["Brain", "Card", "ContextItem", "VisibleSet"]

K1 = 1.2
B = 0.75
MAX_PINNED = 3


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: "str | None"
    groups: frozenset


@dataclass(frozen=True)
class Card:
    entity_id: str
    acl_group: str
    text: str
    fact_ids: tuple
    digest: str


@dataclass(frozen=True)
class ContextItem:
    kind: str
    ref: str
    text: str
    reason: str
    annotations: tuple = ()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL,
    digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group));
CREATE TABLE IF NOT EXISTS cd_card_facts(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, fact_id INTEGER NOT NULL,
    PRIMARY KEY (entity_id, acl_group, fact_id));
CREATE INDEX IF NOT EXISTS cd_card_facts_fact ON cd_card_facts(fact_id);
"""


class Brain:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                self.conn.execute(stmt)
        self.rebuild()

    # ------------------------------------------------------------ visible set
    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 (resolved per call, fail closed, never crosses a tenant)
        empty = VisibleSet(principal_id, None, frozenset())
        try:
            p = self.store.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            groups = self._own_groups(p)
            if p["kind"] == "agent":
                # An agent acts for a person; its own rows can only narrow that access (intersection).
                owner = self.store.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return empty
                groups &= self._own_groups(owner)
            elif p["kind"] != "person":
                return empty
            return VisibleSet(principal_id, p["tenant"], frozenset(groups))
        except Exception:
            return empty

    def _own_groups(self, p) -> set:
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    # ------------------------------------------------------------ cards
    def _compile(self, entity_id):
        """Recompile every card of one entity from head facts. # DECISION: ADR-010 (compiled in code from rows)"""
        c = self.conn
        c.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        c.execute("DELETE FROM cd_card_facts WHERE entity_id = ?", (entity_id,))
        ent = self.store.entity(entity_id)
        if ent is None:
            return
        by_group = {}
        for f in self.store.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(self.store.aliases(entity_id))
        for gid, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {ent['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            c.execute("INSERT INTO cd_cards VALUES (?,?,?,?)",
                      (entity_id, gid, text, hashlib.sha256(text.encode("utf-8")).hexdigest()))
            c.executemany("INSERT INTO cd_card_facts VALUES (?,?,?)", [(entity_id, gid, f["id"]) for f in facts])

    def rebuild(self):
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            self.conn.execute("DELETE FROM cd_card_facts")
            for eid in sorted({f["entity_id"] for f in self.store.head_facts()}):
                self._compile(eid)

    def _load_cards(self, entity_id):
        out = []
        for gid, text, digest in self.conn.execute(
                "SELECT acl_group, text, digest FROM cd_cards WHERE entity_id = ? ORDER BY acl_group", (entity_id,)):
            fids = tuple(r[0] for r in self.conn.execute(
                "SELECT fact_id FROM cd_card_facts WHERE entity_id = ? AND acl_group = ? ORDER BY fact_id",
                (entity_id, gid)))
            out.append(Card(entity_id, gid, text, fids, digest))
        return out

    def cards(self, entity_id, principal_id) -> tuple:
        # DECISION: ADR-007 (a card is visible only if its group is visible and the tenants match)
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if ent is None or vs.tenant is None or ent["tenant"] != vs.tenant:
                return ()
            return tuple(c for c in self._load_cards(entity_id) if c.acl_group in vs.groups)
        except Exception:
            return ()

    def card(self, entity_id, principal_id):
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009 (path A keyed upsert with supersession, cards recompiled in the same transaction)
        with self.store.transaction():
            old = self.store.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new = self.store.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                         attribute=attribute, entity_id=entity_id, value=value,
                                         valid_from=valid_from, source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                self.store.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile(eid)
            return new

    # ------------------------------------------------------------ assembly
    def _link(self, request, tenant):
        """Entities linked from the request, as (first_position, entity_id), overlaps resolved longest-first."""
        req = tokens(request)
        matches = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                n = len(nt)
                if not n:
                    continue
                for i in range(len(req) - n + 1):
                    if req[i:i + n] == nt:
                        matches.append((n, e["id"], i))
        matches.sort(key=lambda m: (-m[0], m[1], m[2]))
        used, first = set(), {}
        for n, eid, start in matches:
            span = range(start, start + n)
            if any(j in used for j in span):
                continue
            used.update(span)
            first[eid] = min(first.get(eid, start), start)
        return sorted((pos, eid) for eid, pos in first.items())

    def _note_visible(self, n, vs):
        return (n is not None and n["state"] == "active" and vs.tenant is not None
                and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups)

    def _bm25(self, request, vs):
        """Ranked note ids over the requester's visible active notes only. # DECISION: ADR-010 (assembly)"""
        docs = {n["id"]: tokens(n["text"]) for n in self.store.notes() if self._note_visible(n, vs)}
        q = sorted(set(tokens(request)))
        if not docs or not q:
            return []
        N = len(docs)
        avg = sum(len(d) for d in docs.values()) / N
        counts = {nid: {} for nid in docs}
        df = {}
        for nid, d in docs.items():
            for t in d:
                counts[nid][t] = counts[nid].get(t, 0) + 1
            for t in counts[nid]:
                df[t] = df.get(t, 0) + 1
        scored = []
        for nid, d in docs.items():
            s = 0.0
            for t in q:
                f = counts[nid].get(t)
                if not f:
                    continue
                idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * len(d) / avg)) if avg else 0.0
            if s > 0:
                scored.append((-s, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def _annotations(self, nid, vs):
        # DECISION: ADR-009 (forward quoted values to the head; hidden heads reveal nothing)
        out = []
        for fid in self.store.mentions(nid):
            f = self.store.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            h = self.store.head_of(fid)
            if h is not None and h["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {h['valid_from']}; current value {h['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)  # mention order (R9)

    def _card_valid(self, card, vs):
        ent = self.store.entity(card.entity_id)
        if ent is None or ent["tenant"] != vs.tenant or card.acl_group not in vs.groups:
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] != card.acl_group
                    or f["entity_id"] != card.entity_id):
                return False
        return True

    def assemble(self, request, principal_id, k=10) -> list:
        # DECISION: ADR-010 (pinned cards, then BM25 notes over visible rows)
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or not vs.groups or k <= 0:
                return []
            items = []
            for _, eid in self._link(request, vs.tenant):
                for card in self.cards(eid, principal_id):
                    if len(items) >= min(MAX_PINNED, k):
                        break
                    if self._card_valid(card, vs):  # exit check
                        items.append(ContextItem("card", eid, card.text, "card", ()))
            seen = set()
            for nid in self._bm25(request, vs):
                if len(items) >= k:
                    break
                n = self.store.note(nid)
                if nid in seen or not self._note_visible(n, vs):  # exit check
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, n["text"], "search", self._annotations(nid, vs)))
            return items
        except Exception:
            return []
