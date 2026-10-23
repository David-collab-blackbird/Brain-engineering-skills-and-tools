"""Reference implementation of WP-E15C."""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass

from factstore import tokens

K1, B = 1.2, 0.75
MAX_CARDS = 3


@dataclass(frozen=True)
class VisibleSet:
    principal_id: str
    tenant: str | None
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
    annotations: tuple


class Brain:
    def __init__(self, store):
        self.store = store
        self.conn = store.conn
        with store.transaction():
            self.conn.execute("CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
                              "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
                              "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visible set
    def _own(self, p):
        out = set()
        for gid in self.store.membership_rows(p["id"]):
            g = self.store.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return out

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007 per-call, fail closed, agent = intersection (OA-1)
        p = self.store.principal(principal_id) if isinstance(principal_id, str) else None
        if p is None:
            return VisibleSet(str(principal_id), None if p is None else p["tenant"], frozenset())
        groups = self._own(p)
        if p["kind"] == "agent":
            person = self.store.principal(p["acts_for"]) if p["acts_for"] else None
            if person is None or person["status"] != "active" or person["kind"] != "person" \
                    or person["tenant"] != p["tenant"]:
                groups = set()
            else:
                groups &= self._own(person)
        return VisibleSet(p["id"], p["tenant"], frozenset(groups))

    # ------------------------------------------------------------ cards
    def _compile(self, entity_id, group):
        # DECISION: ADR-010 compiled in code from head rows of one group
        e = self.store.entity(entity_id)
        heads = sorted((f for f in self.store.head_facts(entity_id) if f["acl_group"] == group),
                       key=lambda f: (f["attribute"], f["id"]))
        if e is None or not heads:
            return None
        lines = [f"# {e['name']}"]
        al = sorted(self.store.aliases(entity_id))
        if al:
            lines.append("aliases: " + ", ".join(al))
        for f in heads:
            lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
        text = "\n".join(lines)
        ids = tuple(sorted(f["id"] for f in heads))
        return text, ids, hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _write_card(self, entity_id, group):
        c = self._compile(entity_id, group)
        self.conn.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (entity_id, group))
        if c is not None:
            self.conn.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                              (entity_id, group, c[0], ",".join(map(str, c[1])), c[2]))

    def rebuild(self):
        with self.store.transaction():
            self.conn.execute("DELETE FROM cd_cards")
            pairs = sorted({(f["entity_id"], f["acl_group"]) for f in self.store.head_facts()})
            for e, g in pairs:
                self._write_card(e, g)

    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source, acl_group):
        # DECISION: ADR-009 path A keyed upsert
        with self.store.transaction():
            old = self.store.head(source_system, source_entity_id, attribute)
            if old is not None and old["value"] == value and old["valid_from"] == valid_from \
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id:
                return old["id"]
            new = self.store.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                         attribute=attribute, entity_id=entity_id, value=value, valid_from=valid_from,
                                         source=source, acl_group=acl_group)
            touched = {(entity_id, acl_group)}
            if old is not None:
                self.store.supersede(old["id"], new)
                touched.add((old["entity_id"], old["acl_group"]))
            for e, g in sorted(touched):
                self._write_card(e, g)
            return new

    def _cards_for(self, entity_id, vs):
        e = self.store.entity(entity_id)
        if e is None or e["tenant"] != vs.tenant:
            return []
        rows = self.conn.execute("SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards "
                                 "WHERE entity_id = ? ORDER BY acl_group", (entity_id,)).fetchall()
        out = []
        for eid, g, text, fids, dig in rows:
            if g not in vs.groups:                # DECISION: ADR-007 card ACL
                continue
            ids = tuple(int(x) for x in fids.split(",") if x)
            # exit check: every listed fact still a head in this group
            ok = all((f := self.store.fact(i)) is not None and f["superseded_by"] is None and f["acl_group"] == g
                     for i in ids)
            if ok and ids:
                out.append(Card(eid, g, text, ids, dig))
        return out

    def cards(self, entity_id, principal_id):
        vs = self.visible_set(principal_id)
        if not vs.groups or not isinstance(entity_id, str):
            return ()
        return tuple(self._cards_for(entity_id, vs))

    def card(self, entity_id, principal_id):
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ assembly
    def _link(self, req_toks, tenant):
        cands = []
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                if not nt:
                    continue
                for i in range(len(req_toks) - len(nt) + 1):
                    if req_toks[i:i + len(nt)] == nt:
                        cands.append((i, i + len(nt), e["id"]))
        # longer match wins on overlap; equal length: lower entity id; process greedily
        cands.sort(key=lambda c: (-(c[1] - c[0]), c[2], c[0]))
        taken = []
        firstpos = {}
        for s, t, eid in cands:
            if any(not (t <= a or s >= b) and eid != oe for a, b, oe in taken):
                continue
            taken.append((s, t, eid))
            firstpos[eid] = min(firstpos.get(eid, s), s)
        return sorted(firstpos, key=lambda e: (firstpos[e], e))

    def assemble(self, request, principal_id, k=10):
        vs = self.visible_set(principal_id)
        if not vs.groups or not isinstance(request, str) or k <= 0:
            return []
        rt = tokens(request)
        items = []
        # DECISION: ADR-010 pin up to 3 visible cards of linked entities
        for eid in self._link(rt, vs.tenant):
            for c in self._cards_for(eid, vs):
                if len(items) < min(MAX_CARDS, k):
                    items.append(ContextItem("card", eid, c.text, "card", ()))
        if not rt:
            return items
        notes = [n for n in self.store.notes()
                 if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]
        if not notes:
            return items
        toks = {n["id"]: tokens(n["text"]) for n in notes}
        N = len(notes)
        avg = sum(len(t) for t in toks.values()) / N or 1.0
        scores = {}
        for term in set(rt):
            df = sum(1 for t in toks.values() if term in t)
            if not df:
                continue
            idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
            for nid, t in toks.items():
                tf = t.count(term)
                if tf:
                    scores[nid] = scores.get(nid, 0) + idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * len(t) / avg))
        ranked = sorted((nid for nid, s in scores.items() if s > 0), key=lambda nid: (-scores[nid], nid))
        for nid in ranked:
            if len(items) >= k:
                break
            n = self.store.note(nid)
            if n is None or n["state"] != "active" or n["acl_group"] not in vs.groups or n["tenant"] != vs.tenant:
                continue
            items.append(ContextItem("note", nid, n["text"], "search", self._forward(nid, vs)))
        return items

    def _forward(self, nid, vs):
        # DECISION: ADR-009 forward to head; never reveal a hidden head
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
