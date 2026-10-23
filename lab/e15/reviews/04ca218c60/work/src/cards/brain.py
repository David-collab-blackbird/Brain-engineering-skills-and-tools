from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from factstore.text import tokens

DEFAULT_K = 10
MAX_PINNED = 3
K1, B = 1.2, 0.75


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


_DDL = """
CREATE TABLE IF NOT EXISTS cd_cards(
    entity_id TEXT NOT NULL, acl_group TEXT NOT NULL, text TEXT NOT NULL,
    fact_ids TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY (entity_id, acl_group))
"""


class Brain:
    def __init__(self, store):
        self.store = store
        store.conn.execute(_DDL)
        self.rebuild()

    # ------------------------------------------------------------ visible set
    # DECISION: ADR-007
    def _person_groups(self, p) -> frozenset[str]:
        st = self.store
        out = set()
        for gid in st.membership_rows(p["id"]):
            g = st.group(gid)
            if g is not None and g["tenant"] == p["tenant"]:
                out.add(gid)
        return frozenset(out)

    def visible_set(self, principal_id) -> VisibleSet:
        # DECISION: ADR-007  (resolved per call, never cached)
        empty = VisibleSet(str(principal_id), None, frozenset())
        st = self.store
        p = st.principal(principal_id)
        if p is None or p["status"] != "active":
            return empty
        if p["kind"] == "person":
            return VisibleSet(p["id"], p["tenant"], self._person_groups(p))
        # Agent: delegated access of the person it acts for. Fail closed
        # (see build/questions.json): also limited to the agent's own rows.
        owner = st.principal(p["acts_for"]) if p["acts_for"] else None
        if (owner is None or owner["status"] != "active" or owner["kind"] != "person"
                or owner["tenant"] != p["tenant"]):
            return empty
        groups = self._person_groups(owner) & self._person_groups(p)
        return VisibleSet(p["id"], p["tenant"], groups)

    # ------------------------------------------------------------ compile
    # DECISION: ADR-010
    def _compile_entity(self, eid) -> dict[str, Card]:
        """Compile cards for one entity from head rows and sync cd_cards."""
        st = self.store
        ent = st.entity(eid)
        cards: dict[str, Card] = {}
        if ent is not None:
            by_group: dict[str, list[dict]] = {}
            for f in st.head_facts(eid):
                by_group.setdefault(f["acl_group"], []).append(f)
            aliases = sorted(st.aliases(eid))
            for gid, facts in by_group.items():
                facts.sort(key=lambda f: (f["attribute"], f["id"]))
                lines = [f"# {ent['name']}"]
                if aliases:
                    lines.append("aliases: " + ", ".join(aliases))
                for f in facts:
                    lines.append(f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, "
                                 f"source {f['source']})")
                text = "\n".join(lines)
                cards[gid] = Card(eid, gid, text, tuple(sorted(f["id"] for f in facts)),
                                  hashlib.sha256(text.encode("utf-8")).hexdigest())
        c = st.conn
        old = {r[0]: r[1:] for r in c.execute(
            "SELECT acl_group, text, fact_ids, digest FROM cd_cards WHERE entity_id = ?", (eid,))}
        new = {g: (k.text, json.dumps(list(k.fact_ids)), k.digest) for g, k in cards.items()}
        if old != new:
            with st.transaction():
                c.execute("DELETE FROM cd_cards WHERE entity_id = ?", (eid,))
                c.executemany("INSERT INTO cd_cards VALUES (?,?,?,?,?)",
                              [(eid, g, *v) for g, v in sorted(new.items())])
        return cards

    def rebuild(self) -> None:
        st = self.store
        with st.transaction():
            eids = {e["id"] for e in st.entities()}
            eids |= {r[0] for r in st.conn.execute("SELECT DISTINCT entity_id FROM cd_cards")}
            for eid in sorted(eids):
                self._compile_entity(eid)

    # ------------------------------------------------------------ upsert
    def upsert(self, source_system, source_entity_id, attribute, *, entity_id, value, valid_from, source,
               acl_group) -> int:
        # DECISION: ADR-009
        st = self.store
        with st.transaction():
            old = st.head(source_system, source_entity_id, attribute)
            if (old is not None and old["value"] == value and old["valid_from"] == valid_from
                    and old["acl_group"] == acl_group and old["entity_id"] == entity_id):
                return old["id"]
            ent, grp = st.entity(entity_id), st.group(acl_group)
            if ent is None or grp is None or grp["tenant"] != ent["tenant"]:
                return -1  # rejected, nothing written (R12: no raise on unknown ids)
            new = st.insert_fact(source_system=source_system, source_entity_id=source_entity_id,
                                 attribute=attribute, entity_id=entity_id, value=value,
                                 valid_from=valid_from, source=source, acl_group=acl_group)
            affected = {entity_id}
            if old is not None:
                st.supersede(old["id"], new)
                affected.add(old["entity_id"])
            for eid in sorted(affected):
                self._compile_entity(eid)
            return new

    # ------------------------------------------------------------ cards
    def cards(self, entity_id, principal_id) -> tuple[Card, ...]:
        # DECISION: ADR-007  (card ACL: group visible and same tenant; not found == denied)
        try:
            vs = self.visible_set(principal_id)
            ent = self.store.entity(entity_id)
            if vs.tenant is None or ent is None or ent["tenant"] != vs.tenant:
                return ()
            compiled = self._compile_entity(entity_id)
            return tuple(compiled[g] for g in sorted(compiled) if g in vs.groups)
        except Exception:
            return ()

    def card(self, entity_id, principal_id) -> Card | None:
        cs = self.cards(entity_id, principal_id)
        return cs[0] if cs else None

    # ------------------------------------------------------------ linking
    def _link(self, request, tenant) -> list[tuple[int, str]]:
        """(first position, entity id) of linked entities; longest match wins."""
        rt = tokens(request)
        matches = []
        for e in self.store.entities():
            if e["tenant"] != tenant:
                continue
            for name in [e["name"], *self.store.aliases(e["id"])]:
                nt = tokens(name)
                n = len(nt)
                if not n:
                    continue
                for i in range(len(rt) - n + 1):
                    if rt[i:i + n] == nt:
                        matches.append((i, i + n, e["id"]))
        matches.sort(key=lambda m: (-(m[1] - m[0]), m[2], m[0]))
        taken: list[tuple[int, int]] = []
        first: dict[str, int] = {}
        for s, e_, eid in matches:
            if any(s < te and ts < e_ for ts, te in taken):
                continue
            taken.append((s, e_))
            first[eid] = min(first.get(eid, s), s)
        return sorted((pos, eid) for eid, pos in first.items())

    # ------------------------------------------------------------ assembly
    def _visible_notes(self, vs) -> list[dict]:
        return [n for n in self.store.notes()
                if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]

    def _bm25(self, request, notes) -> list[dict]:
        q = set(tokens(request))
        docs = [(n, tokens(n["text"])) for n in notes]
        N = len(docs)
        if not N or not q:
            return []
        avg = sum(len(t) for _, t in docs) / N or 1.0
        df = {w: sum(1 for _, t in docs if w in t) for w in q}
        scored = []
        for n, t in docs:
            s = 0.0
            for w in q:
                f = t.count(w)
                if not f:
                    continue
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * len(t) / avg))
            if s > 0:
                scored.append((-s, n["id"], n))
        scored.sort(key=lambda x: (x[0], x[1]))
        return [n for _, _, n in scored]

    def _annotations(self, nid, vs) -> tuple[str, ...]:
        # DECISION: ADR-009  (forward superseded quotes to the head; hide unseen heads)
        st = self.store
        out = []
        for fid in st.mentions(nid):
            f = st.fact(fid)
            if f is None or f["superseded_by"] is None:
                continue
            h = st.head_of(fid)
            if h is not None and h["superseded_by"] is None and h["acl_group"] in vs.groups:
                out.append(f"quoted value superseded on {h['valid_from']}; current value {h['value']}")
            else:
                out.append("quoted value superseded")
        return tuple(out)

    def assemble(self, request, principal_id, k=DEFAULT_K) -> list[ContextItem]:
        # DECISION: ADR-010
        try:
            return self._assemble(request, principal_id, k)
        except Exception:
            return []

    def _assemble(self, request, principal_id, k):
        vs = self.visible_set(principal_id)
        if vs.tenant is None or k <= 0:
            return []
        out: list[ContextItem] = []
        # pinned cards
        cand_cards: list[Card] = []
        for _, eid in self._link(request, vs.tenant):
            cand_cards.extend(self.cards(eid, principal_id))
        for c in cand_cards:
            if len(out) >= MAX_PINNED:
                break
            # exit check: card facts still heads and visible
            if c.acl_group in vs.groups and all(
                    (f := self.store.fact(i)) and f["superseded_by"] is None and f["acl_group"] in vs.groups
                    for i in c.fact_ids):
                out.append(ContextItem("card", c.entity_id, c.text, "card", ()))
        out = out[:k]
        seen: set[str] = set()
        for n in self._bm25(request, self._visible_notes(vs)):
            if len(out) >= k:
                break
            if n["id"] in seen:
                continue
            # exit check: re-read the note
            cur = self.store.note(n["id"])
            if cur is None or cur["state"] != "active" or cur["acl_group"] not in vs.groups \
                    or cur["tenant"] != vs.tenant:
                continue
            seen.add(n["id"])
            out.append(ContextItem("note", cur["id"], cur["text"], "search",
                                   self._annotations(cur["id"], vs)))
        return out
