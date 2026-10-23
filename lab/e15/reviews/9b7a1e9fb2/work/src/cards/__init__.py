"""WP-E15C: keyed facts, entity cards and context assembly."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

__all__ = ["Brain", "Card", "ContextItem", "VisibleSet"]


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
    annotations: tuple = ()


_EMPTY = frozenset()


class Brain:
    def __init__(self, store):
        self.store = store
        with store.transaction():
            store.conn.execute(
                "CREATE TABLE IF NOT EXISTS cd_cards(entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, "
                "text TEXT NOT NULL, fact_ids TEXT NOT NULL, digest TEXT NOT NULL, "
                "PRIMARY KEY (entity_id, acl_group))")
        self.rebuild()

    # ------------------------------------------------------------ visibility
    def _groups_of(self, person):
        """Groups a person's membership rows name that exist in the person's tenant."""
        s = self.store
        out = set()
        for gid in s.membership_rows(person["id"]):
            g = s.group(gid)
            if g is not None and g["tenant"] == person["tenant"]:
                out.add(gid)
        return out

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007
        try:
            s = self.store
            p = s.principal(principal_id)
            if p is None or p["status"] != "active":
                return VisibleSet(str(principal_id), None, _EMPTY)
            groups = self._groups_of(p)
            if p["kind"] == "agent":
                # Delegated access, narrowed by the agent's own rows (fail closed; see build/questions.json).
                owner = s.principal(p["acts_for"]) if p["acts_for"] else None
                if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                        or owner["tenant"] != p["tenant"]):
                    return VisibleSet(p["id"], None, _EMPTY)
                groups &= self._groups_of(owner)
            return VisibleSet(p["id"], p["tenant"], frozenset(groups))
        except Exception:
            return VisibleSet(str(principal_id), None, _EMPTY)

    # ------------------------------------------------------------ cards
    def _compile(self, entity_id, group):
        # DECISION: ADR-010
        s = self.store
        ent = s.entity(entity_id)
        facts = [f for f in s.head_facts(entity_id) if f["acl_group"] == group]
        if ent is None or not facts:
            return None
        facts.sort(key=lambda f: (f["attribute"], f["id"]))
        lines = [f"# {ent['name']}"]
        al = sorted(s.aliases(entity_id))
        if al:
            lines.append("aliases: " + ", ".join(al))
        for f in facts:
            lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})")
        text = "\n".join(lines)
        return Card(entity_id, group, text, tuple(sorted(f["id"] for f in facts)),
                    hashlib.sha256(text.encode("utf-8")).hexdigest())

    def _refresh(self, entity_id, group):
        c = self.store.conn
        c.execute("DELETE FROM cd_cards WHERE entity_id = ? AND acl_group = ?", (entity_id, group))
        card = self._compile(entity_id, group)
        if card is not None:
            c.execute("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                      (entity_id, group, card.text, json.dumps(list(card.fact_ids)), card.digest))

    def rebuild(self):
        s = self.store
        with s.transaction():
            s.conn.execute("DELETE FROM cd_cards")
            pairs = {(f["entity_id"], f["acl_group"]) for f in s.head_facts()}
            for e, g in sorted(pairs):
                self._refresh(e, g)

    def _all_cards(self, entity_id):
        rows = self.store.conn.execute(
            "SELECT entity_id, acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ? "
            "ORDER BY acl_group", (entity_id,)).fetchall()
        return [Card(r[0], r[1], r[2], tuple(json.loads(r[3])), r[4]) for r in rows]

    def _card_ok(self, card, vs):
        """Exit check for a card: group visible, facts still heads in that group."""
        if card.acl_group not in vs.groups:
            return False
        for fid in card.fact_ids:
            f = self.store.fact(fid)
            if (f is None or f["superseded_by"] is not None or f["acl_group"] != card.acl_group
                    or f["entity_id"] != card.entity_id):
                return False
        return bool(card.fact_ids)

    def cards(self, entity_id, principal_id):
        # DECISION: ADR-007
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if vs.tenant is None or ent is None or ent["tenant"] != vs.tenant:
                return ()
            out = []
            for c in self._all_cards(entity_id):
                if c.acl_group not in vs.groups:
                    continue
                if not self._card_ok(c, vs):   # store changed outside upsert: recompile, don't drop
                    c = self._compile(entity_id, c.acl_group)
                if c is not None and self._card_ok(c, vs):
                    out.append(c)
            return tuple(out)
        except Exception:
            return ()

    def card(self, entity_id, principal_id):
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group):
        # DECISION: ADR-009
        s = self.store
        with s.transaction():
            if s.entity(entity_id) is None or s.group(acl_group) is None:
                raise ValueError("unknown entity or group")
            old = s.head(source_system, source_entity_id, attribute)
            if (old and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            new = s.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                attribute=attribute, entity_id=entity_id, value=value, valid_from=valid_from,
                                source=source, acl_group=acl_group)
            pairs = {(entity_id, acl_group)}
            if old:
                s.supersede(old["id"], new)
                pairs.add((old["entity_id"], old["acl_group"]))
            for e, g in sorted(pairs):
                self._refresh(e, g)
            return new

    # ------------------------------------------------------------ linking
    def _link(self, req_tokens, tenant):
        """Return [(first_position, entity_id)] for linked entities (longest match wins)."""
        s = self.store
        cands = []
        for e in s.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *s.aliases(e["id"])]:
                nt = tokens(name)
                n = len(nt)
                if n == 0:
                    continue
                for i in range(len(req_tokens) - n + 1):
                    if req_tokens[i:i + n] == nt:
                        cands.append((-n, e["id"], i))
        cands.sort()
        used = set()
        first = {}
        for negn, eid, i in cands:
            span = set(range(i, i - negn))
            if span & used:
                continue
            used |= span
            first[eid] = min(i, first.get(eid, i))
        return sorted((pos, eid) for eid, pos in first.items())

    # ------------------------------------------------------------ assembly
    def _note_ok(self, nid, vs):
        n = self.store.note(nid)
        return (n is not None and n["state"] == "active" and n["tenant"] == vs.tenant
                and n["acl_group"] in vs.groups)

    def _annotations(self, nid, vs):
        s = self.store
        out = []
        for fid in s.mentions(nid):
            f = s.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            h = s.head_of(fid)
            if h is not None and h["superseded_by"] is None and h["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {h['valid_from']}; current value {h['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def _rank(self, q_tokens, vs):
        s = self.store
        docs = [(n["id"], tokens(n["text"])) for n in s.notes()
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]
        if not docs or not q_tokens:
            return []
        N = len(docs)
        avg = sum(len(t) for _, t in docs) / N
        terms = sorted(set(q_tokens))
        df = {t: sum(1 for _, d in docs if t in d) for t in terms}
        k1, b = 1.2, 0.75
        scored = []
        for nid, d in docs:
            if not d:
                continue
            tf = {}
            for w in d:
                tf[w] = tf.get(w, 0) + 1
            sc = 0.0
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                    sc += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avg))
            if sc > 0:
                scored.append((-sc, nid))
        scored.sort()
        return [nid for _, nid in scored]

    def assemble(self, request, principal_id, k=10):
        # DECISION: ADR-010
        # DECISION: ADR-009
        try:
            vs = self.visible_set(principal_id)
            if vs.tenant is None or not vs.groups or k <= 0:
                return []
            q = tokens(request)
            items = []
            for _, eid in self._link(q, vs.tenant):
                for c in self.cards(eid, principal_id):   # exit check included
                    if len(items) >= min(3, k):
                        break
                    items.append(ContextItem("card", eid, c.text, "card", ()))
            seen = set()
            for nid in self._rank(q, vs):
                if len(items) >= k:
                    break
                if nid in seen or not self._note_ok(nid, vs):
                    continue
                seen.add(nid)
                items.append(ContextItem("note", nid, self.store.note(nid)["text"], "search",
                                         self._annotations(nid, vs)))
            return items
        except Exception:
            return []
