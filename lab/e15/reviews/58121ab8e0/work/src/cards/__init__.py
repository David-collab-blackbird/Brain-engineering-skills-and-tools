"""WP-E15C entity cards and context assembly."""
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


MAX_PINNED = 3
K1, B = 1.2, 0.75


class Brain:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        with store.transaction():
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
                "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
                "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visible set
    def _valid_groups(self, p):
        groups = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                groups.add(gid)
        return groups

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007
        empty = VisibleSet(str(principal_id), None, frozenset())
        try:
            s = self.store
            p = s.principal(principal_id)
            if p is None or p["status"] != "active":
                return empty
            own = None
            if p["kind"] == "agent":
                # an agent gets the intersection of its own valid rows and its person's visible groups
                person = s.principal(p["acts_for"]) if p["acts_for"] else None
                if (person is None or person["status"] != "active" or person["kind"] != "person"
                        or person["tenant"] != p["tenant"]):
                    return empty
                own = self._valid_groups(p)
                p = person
            groups = self._valid_groups(p)
            if own is not None:
                groups &= own
            return VisibleSet(str(principal_id), p["tenant"], frozenset(groups))
        except Exception:
            return empty

    # ------------------------------------------------------------ compiling
    def _compile(self, entity_id):
        # DECISION: ADR-010
        s = self.store
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ?", (entity_id,))
        e = s.entity(entity_id)
        if e is None:
            return
        by_group: dict[str, list[dict]] = {}
        for f in s.head_facts(entity_id):
            by_group.setdefault(f["acl_group"], []).append(f)
        aliases = sorted(s.aliases(entity_id))
        for group, facts in by_group.items():
            facts.sort(key=lambda f: (f["attribute"], f["id"]))
            lines = [f"# {e['name']}"]
            if aliases:
                lines.append("aliases: " + ", ".join(aliases))
            for f in facts:
                lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
            text = "\n".join(lines)
            ids = sorted(f["id"] for f in facts)
            self.conn.execute(
                "INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                (entity_id, group, text, json.dumps(ids), hashlib.sha256(text.encode("utf-8")).hexdigest()))

    def rebuild(self):
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            eids = {e["id"] for e in self.store.entities()}
            for eid in sorted(eids):
                self._compile(eid)

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009
        s = self.store
        with s.transaction():
            ent = s.entity(entity_id)
            grp = s.group(acl_group)
            if ent is None or grp is None or grp["tenant"] != ent["tenant"]:
                raise ValueError("unknown entity or acl group")
            old = s.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new = s.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                attribute=attribute, entity_id=entity_id, value=value, valid_from=valid_from,
                                source=source, acl_group=acl_group)
            touched = {entity_id}
            if old is not None:
                s.supersede(old["id"], new)
                touched.add(old["entity_id"])
            for eid in sorted(touched):
                self._compile(eid)
            return new

    # ------------------------------------------------------------ cards
    def _row_card(self, r):
        return Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4])

    def _card_ok(self, card, vs):
        # exit check: group visible, entity in tenant, every fact still a visible head
        # DECISION: ADR-007
        if card.acl_group not in vs.groups:
            return False
        e = self.store.entity(card.entity_id)
        if e is None or e["tenant"] != vs.tenant:
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] != card.acl_group
                    or f["entity_id"] != card.entity_id):
                return False
        return True

    def _cards(self, entity_id, vs):
        if vs.tenant is None:
            return ()
        rows = self.conn.execute(
            "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
            "ORDER BY acl_group", (entity_id,)).fetchall()
        return tuple(c for c in map(self._row_card, rows) if self._card_ok(c, vs))

    def cards(self, entity_id, principal_id):
        try:
            return self._cards(entity_id, self.visible_set(principal_id))
        except Exception:
            return ()

    def card(self, entity_id, principal_id):
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ linking
    def _link(self, request, vs):
        """Return linked entity ids ordered by first match position, then id."""
        # DECISION: ADR-010
        toks = tokens(request)
        matches = []  # (length, entity_id, start)
        for e in self.store.entities():
            if e["tenant"] != vs.tenant:
                continue
            if not self._cards(e["id"], vs):
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                n = len(nt)
                if n == 0:
                    continue
                for i in range(len(toks) - n + 1):
                    if toks[i:i + n] == nt:
                        matches.append((n, e["id"], i))
        matches.sort(key=lambda m: (-m[0], m[1], m[2]))
        taken: set[int] = set()
        first: dict[str, int] = {}
        for n, eid, i in matches:
            span = range(i, i + n)
            if any(p in taken for p in span):
                continue
            taken.update(span)
            first[eid] = min(first.get(eid, i), i)
        return sorted(first, key=lambda eid: (first[eid], eid))

    # ------------------------------------------------------------ search
    def _ranked_notes(self, request, vs):
        docs = []
        for n in self.store.notes():
            if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups:
                docs.append((n["id"], tokens(n["text"])))
        if not docs:
            return []
        N = len(docs)
        avg = sum(len(t) for _, t in docs) / N
        q = sorted(set(tokens(request)))
        df = {w: sum(1 for _, t in docs if w in t) for w in q}
        scored = []
        for nid, t in docs:
            score = 0.0
            L = len(t)
            for w in q:
                if not df[w]:
                    continue
                tf = t.count(w)
                if not tf:
                    continue
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * L / avg if avg else 1))
            if score > 0:
                scored.append((-score, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def _annotations(self, nid, vs):
        # DECISION: ADR-009
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
        return tuple(out)

    # ------------------------------------------------------------ assembly
    def assemble(self, request, principal_id, k=10):
        # DECISION: ADR-010
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or k <= 0:
                return []
            items = []
            for eid in self._link(request, vs):
                for c in self._cards(eid, vs):
                    if len(items) >= min(MAX_PINNED, k):
                        break
                    items.append(ContextItem("card", c.entity_id, c.text, "card", ()))
            seen = set()
            for nid in self._ranked_notes(request, vs):
                if len(items) >= k:
                    break
                n = self.store.note(nid)  # exit check: still active and visible
                if (n is None or n["state"] != "active" or n["acl_group"] not in vs.groups
                        or n["tenant"] != vs.tenant or nid in seen):
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, n["text"], "search", self._annotations(nid, vs)))
            return items
        except Exception:
            return []
