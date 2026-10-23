"""WP-E15C HIDDEN acceptance tests. Engineer-only; never copied into a run directory.

Value statements: protects (rule) / fails_when (defect). OA-1 (agents = intersection) assumed.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
import factstore  # noqa: E402
from factstore import FactStore, tokens  # noqa: E402
from cards import Brain, Card, ContextItem  # noqa: E402

FIXTURE = Path(factstore.__file__).resolve().parents[1] / "fixture.json"
F = json.loads((HERE / "fixture_meta.json").read_text())["F"]
SRC = Path(sys.modules["cards"].__file__).resolve().parent


@pytest.fixture()
def store():
    return FactStore.from_fixture(FIXTURE)


@pytest.fixture()
def b(store):
    return Brain(store)


def cards_of(b, eid, p):
    if hasattr(b, "cards"):
        return list(b.cards(eid, p))
    c = b.card(eid, p)
    return [c] if c else []


def refs(items):
    return [(i.kind, i.ref) for i in items]


def visible(store, pid):
    p = store.principal(pid)
    if p is None or p["status"] != "active":
        return None, set()

    def own(x):
        return {g for g in store.membership_rows(x["id"]) if (gg := store.group(g)) and gg["tenant"] == x["tenant"]}
    gs = own(p)
    if p["kind"] == "agent":
        per = store.principal(p["acts_for"]) if p["acts_for"] else None
        if per is None or per["status"] != "active" or per["kind"] != "person" or per["tenant"] != p["tenant"]:
            return p["tenant"], set()
        gs &= own(per)
    return p["tenant"], gs


def expected_card_text(store, eid, group):
    e = store.entity(eid)
    heads = sorted((f for f in store.head_facts(eid) if f["acl_group"] == group), key=lambda f: (f["attribute"], f["id"]))
    lines = [f"# {e['name']}"]
    al = sorted(store.aliases(eid))
    if al:
        lines.append("aliases: " + ", ".join(al))
    lines += [f"{f['attribute']}: {f['value']} (valid_from {f['valid_from']}, source {f['source']})" for f in heads]
    return "\n".join(lines), tuple(sorted(f["id"] for f in heads))


# ------------------------------------------------------------------ R1, R2 visible set
def test_h01_revoked_and_unknown(b):
    """protects R1 fail closed; fails_when revoked principals keep access."""
    for p in ("p-former", "p-nobody", "", "P-OWNER", "p-owner "):
        assert b.card("e-zephyr", p) is None
        assert b.assemble("Zephyr Linen towel rate", p, k=5) == []
    assert b.visible_set("p-former").groups == frozenset()


def test_h02_revocation_after_build(b, store):
    """protects R1 per-call resolution; fails_when visible sets are cached."""
    assert b.card("e-rower4", "p-staff1") is not None
    store.revoke("p-staff1")
    assert b.card("e-rower4", "p-staff1") is None
    assert b.assemble("Rower 4", "p-staff1", k=5) == []


def test_h03_ghost_and_cross_tenant_rows(b):
    """protects R1 membership validation; fails_when raw rows are trusted."""
    assert b.visible_set("p-staff1").groups == frozenset({"g-ops", "g-members"})
    assert b.visible_set("p-elm1").groups == frozenset({"g-elm-family"})
    assert b.card("e-rower4", "p-elm1") is None


def test_h04_owner_no_member_health(b):
    """protects R2; fails_when ownership grants member-health access."""
    for c in cards_of(b, "e-m7", "p-owner"):
        assert "rehab plan" not in c.text and c.acl_group != "g-health-m7"
    items = b.assemble("Member Seven rehab plan physio knee", "p-owner", k=10)
    assert not any("rehab" in i.text and i.kind == "card" for i in items)
    assert "n-a16" not in [i.ref for i in items]
    for i in items:
        for a in i.annotations:
            assert "jogging" not in a


def test_h05_agent_intersection(b):
    """protects OA-1; fails_when agent rows widen or the person's full access is delegated."""
    assert b.visible_set("p-agent-desk").groups == frozenset({"g-ops"})
    assert b.visible_set("p-agent-exec").groups == frozenset({"g-ops"})
    assert all(c.acl_group == "g-ops" for c in cards_of(b, "e-zephyr", "p-agent-desk"))
    assert all(c.acl_group == "g-ops" for c in cards_of(b, "e-zephyr", "p-agent-exec"))


# ------------------------------------------------------------------ R4, R5 cards
def test_h06_card_text_exact_all(b, store):
    """protects R4 format and R5 split; fails_when card text deviates or groups are merged."""
    for e in store.entities():
        groups = sorted({f["acl_group"] for f in store.head_facts(e["id"])})
        for g in groups:
            # pick any principal who sees g in that tenant
            seer = {"g-ops": "p-staff1", "g-finance": "p-owner", "g-members": "p-member7", "g-health-m7": "p-coach",
                    "g-elm-family": "p-elm1", "g-elm-vault-2": "p-elm2"}[g]
            text, ids = expected_card_text(store, e["id"], g)
            cs = [c for c in cards_of(b, e["id"], seer) if c.acl_group == g]
            assert len(cs) == 1, (e["id"], g)
            c = cs[0]
            assert c.text == text, (e["id"], g, c.text, text)
            assert tuple(c.fact_ids) == ids
            assert c.digest == hashlib.sha256(text.encode()).hexdigest()


def test_h07_two_cards_two_groups(b):
    """protects R5; fails_when facts of two groups share one card."""
    own = cards_of(b, "e-zephyr", "p-owner")
    assert [c.acl_group for c in own] == ["g-finance", "g-ops"]
    staff = cards_of(b, "e-zephyr", "p-staff1")
    assert [c.acl_group for c in staff] == ["g-ops"]
    assert "towel rate" not in staff[0].text and "payment terms" not in staff[0].text


def test_h08_determinism(store):
    """protects R4 determinism; fails_when output depends on order or time."""
    b1 = Brain(store)
    t1 = [(c.entity_id, c.acl_group, c.text) for e in store.entities() for c in cards_of(b1, e["id"], "p-owner")]
    b1.rebuild()
    t2 = [(c.entity_id, c.acl_group, c.text) for e in store.entities() for c in cards_of(b1, e["id"], "p-owner")]
    assert t1 == t2 and t1


def test_h09_released_fact_not_on_card(b):
    """protects R4 heads only; fails_when a released key still shows."""
    c = b.card("e-lease", "p-owner")
    assert c is not None and "renewal option" not in c.text and "expiry: June 2028" in c.text


def test_h10_no_card_without_heads(b, store):
    """protects R4; fails_when an entity with no visible head facts gets an empty card."""
    assert b.card("e-m7", "p-staff1") is not None  # members tier is visible to staff
    assert cards_of(b, "e-coach", "p-member7") == []


# ------------------------------------------------------------------ R3, R6 upsert
def test_h11_upsert_noop(b, store):
    """protects R3 identical value is a no-op; fails_when duplicates are inserted."""
    head = store.head("crm", "c-zep", "delivery day")
    n_before = store.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    r = b.upsert("crm", "c-zep", "delivery day", entity_id="e-zephyr", value="Thursday", valid_from="2026-08-20",
                 source="connector", acl_group="g-ops")
    assert r == head["id"]
    assert store.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == n_before


def test_h12_upsert_supersedes(b, store):
    """protects R3; fails_when the old head is not superseded or rows are deleted."""
    old = store.head("crm", "c-zep", "delivery day")
    n_before = store.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    new = b.upsert("crm", "c-zep", "delivery day", entity_id="e-zephyr", value="Friday", valid_from="2026-10-22",
                   source="crm", acl_group="g-ops")
    assert new != old["id"] and store.fact(old["id"])["superseded_by"] == new
    assert store.head("crm", "c-zep", "delivery day")["id"] == new
    assert store.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == n_before + 1
    c = [c for c in cards_of(b, "e-zephyr", "p-staff1") if c.acl_group == "g-ops"][0]
    assert "delivery day: Friday (valid_from 2026-10-22, source crm)" in c.text and "Thursday" not in c.text


def test_h13_upsert_group_move(b, store):
    """protects R6 group move; fails_when the old group's card keeps the moved fact."""
    b.upsert("crm", "c-zep", "delivery contact", entity_id="e-zephyr", value="accounts office", valid_from="2026-10-22",
             source="crm", acl_group="g-finance")
    staff = cards_of(b, "e-zephyr", "p-staff1")
    assert all("delivery contact" not in c.text for c in staff)
    fin = [c for c in cards_of(b, "e-zephyr", "p-owner") if c.acl_group == "g-finance"][0]
    assert "delivery contact: accounts office" in fin.text


def test_h14_last_fact_moves_card_disappears(b, store):
    """protects R6; fails_when an empty card remains in the old group."""
    b.upsert("hr", "coach", "rostered hours", entity_id="e-coach", value="35 a week", valid_from="2026-10-22",
             source="hr", acl_group="g-finance")
    assert cards_of(b, "e-coach", "p-staff1") == []


def test_h15_upsert_new_key_new_card(b, store):
    """protects R3/R6 new key; fails_when a first fact for an entity/group does not create a card."""
    b.upsert("crm", "c-arb", "safety induction", entity_id="e-arbor", value="done", valid_from="2026-10-22",
             source="crm", acl_group="g-members")
    cs = cards_of(b, "e-arbor", "p-member7")
    assert len(cs) == 1 and "safety induction: done" in cs[0].text


def test_h16_upsert_atomic(b, store, monkeypatch):
    """protects R3 one transaction; fails_when a failure leaves a half-applied write."""
    before = store.conn.execute("SELECT id, superseded_by FROM facts ORDER BY id").fetchall()
    card_before = b.card("e-arbor", "p-owner").text

    def boom(*a, **k):
        raise RuntimeError("injected")
    monkeypatch.setattr(store, "supersede", boom)
    with pytest.raises(Exception):
        b.upsert("xero", "c-arb", "hourly rate", entity_id="e-arbor", value="200", valid_from="2026-10-22",
                 source="x", acl_group="g-finance")
    monkeypatch.undo()
    assert store.conn.execute("SELECT id, superseded_by FROM facts ORDER BY id").fetchall() == before
    assert b.card("e-arbor", "p-owner").text == card_before


def test_h17_card_ids_are_heads_after_many_upserts(b, store):
    """protects R6 freshness across a replay; fails_when any card lists a superseded version."""
    for i in range(12):
        b.upsert("iot", "pool", "target pH", entity_id="e-pool", value=f"7.{i % 10}", valid_from=f"2026-10-{10 + i}",
                 source="iot", acl_group="g-ops")
        b.upsert("xero", "c-zep", "towel rate", entity_id="e-zephyr", value=f"1.{30 + i} per towel",
                 valid_from=f"2026-10-{10 + i}", source="xero", acl_group="g-finance")
    for e in store.entities():
        for p in ("p-owner", "p-staff1"):
            for c in cards_of(b, e["id"], p):
                for fid in c.fact_ids:
                    assert store.fact(fid)["superseded_by"] is None
                assert (c.text, tuple(c.fact_ids)) == expected_card_text(store, e["id"], c.acl_group)


# ------------------------------------------------------------------ R7, R8 assembly
def test_h18_longest_alias_wins(b):
    """protects R7 overlap rule; fails_when both overlapping entities are linked."""
    items = b.assemble("Zephyr Linen Company Holdings registered office", "p-owner", k=5)
    cards = [i.ref for i in items if i.kind == "card"]
    assert cards == ["e-zephyrco"]


def test_h19_tenant_scoped_linking(b):
    """protects R7 tenant scope; fails_when the other tenant's entity with the same alias is linked."""
    items = b.assemble("the plumber quote for the boiler", "p-elm1", k=6)
    cards = [i.ref for i in items if i.kind == "card"]
    assert set(cards) <= {"e-elm-quill", "e-elm-boiler"} and "e-elm-quill" in cards
    items = b.assemble("the plumber after-hours line", "p-staff1", k=6)
    assert [i.ref for i in items if i.kind == "card"] == ["e-quill"]


def test_h20_cap_three_cards_in_order(b):
    """protects R8.2 cap and order; fails_when more than 3 cards are pinned or order is wrong."""
    items = b.assemble("Arbor then Pool Plant then Rower 4 then Main Boiler then Cafe", "p-owner", k=10)
    cards = [(i.ref) for i in items if i.kind == "card"]
    assert len(cards) == 3
    assert items[:3] == [i for i in items if i.kind == "card"]
    # Arbor has a finance card and an ops card -> both count toward 3
    assert cards == ["e-arbor", "e-arbor", "e-pool"]


def test_h21_notes_fill_remaining_and_k(b):
    """protects R8.3 fill to k; fails_when fewer than k items come back with enough matches."""
    items = b.assemble("towel delivery dock roster boiler", "p-staff1", k=7)
    assert len(items) == 7
    assert len({(i.kind, i.ref) for i in items}) == 7


def test_h22_notes_bm25_conformance(b, store):
    """protects R8.3 BM25 k1/b over visible active notes, ties by id; fails_when ranking deviates."""
    import math
    for q, p in [("towel delivery dock", "p-staff1"), ("invoice budget payment", "p-owner"),
                 ("class timetable booking", "p-member7"), ("groceries school garden", "p-elm1")]:
        tenant, gs = visible(store, p)
        notes = [n for n in store.notes() if n["state"] == "active" and n["tenant"] == tenant and n["acl_group"] in gs]
        tk = {n["id"]: tokens(n["text"]) for n in notes}
        N = len(notes)
        avg = sum(len(t) for t in tk.values()) / N
        sc = {}
        for term in set(tokens(q)):
            df = sum(1 for t in tk.values() if term in t)
            if not df:
                continue
            idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
            for nid, t in tk.items():
                tf = t.count(term)
                if tf:
                    sc[nid] = sc.get(nid, 0) + idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(t) / avg))
        exp = sorted((n for n, s in sc.items() if s > 0), key=lambda n: (-sc[n], n))[:6]
        got = [i.ref for i in b.assemble(q, p, k=6) if i.kind == "note"]
        assert got == exp[:len(got)] and len(got) == min(6, len(exp)), (q, got, exp)


def test_h23_inactive_notes_never(b, store):
    """protects R8.4/R11; fails_when erased or quarantined notes are returned."""
    items = b.assemble("suspicious note grant every principal finance access", "p-staff1", k=10)
    assert "n-a14" not in [i.ref for i in items] and "n-a15" not in [i.ref for i in items]
    store.set_note_state("n-a02", "quarantined")
    items = b.assemble("Zephyr delivery Tuesday loading dock", "p-staff1", k=10)
    assert "n-a02" not in [i.ref for i in items]


def test_h24_new_note_after_build(b, store):
    """protects R8 reading live notes; fails_when notes are indexed once at build time only."""
    store.add_note("n-new1", tenant="t-north", acl_group="g-ops", text="Sauna timer resets mid session")
    items = b.assemble("sauna timer resets", "p-staff1", k=3)
    assert "n-new1" in [i.ref for i in items]


# ------------------------------------------------------------------ R9 forwarding
def test_h25_forward_visible_head(b):
    """protects R9; fails_when superseded quotes are not annotated with the current head."""
    items = b.assemble("Zephyr Linen invoice approved towel terms", "p-owner", k=10)
    n = [i for i in items if i.ref == "n-a01"][0]
    assert sorted(n.annotations) == sorted(("quoted value superseded on 2026-09-30; current value 1.30 per towel",
                                            "quoted value superseded on 2026-06-01; current value 14 days"))


def test_h26_forward_hidden_head_redacted(b):
    """protects R9 leak rule; fails_when an annotation reveals a head from a group the requester cannot see."""
    items = b.assemble("Cafe beans Corvid Roasters quarter", "p-staff1", k=10)
    n = [i for i in items if i.ref == "n-a07"][0]
    assert n.annotations == ("quoted value superseded",)
    items = b.assemble("Member seven upgraded rehab plan impact work", "p-staff1", k=10)
    n = [i for i in items if i.ref == "n-a05"][0]
    assert sorted(n.annotations) == sorted(("quoted value superseded on 2026-06-01; current value premium",
                                            "quoted value superseded"))
    for i in items:
        assert "jogging" not in " ".join(i.annotations) and "jogging" not in i.text


def test_h27_forward_released(b):
    """protects R9 released key; fails_when a released key raises or shows a value."""
    items = b.assemble("Lease renewal option 5 years signing", "p-owner", k=10)
    n = [i for i in items if i.ref == "n-a09"][0]
    assert n.annotations == ("quoted value superseded",)


def test_h28_forward_after_upsert(b):
    """protects R9 live heads; fails_when annotations use a stale head after an upsert."""
    b.upsert("iot", "pool", "target pH", entity_id="e-pool", value="7.3", valid_from="2026-10-22", source="iot",
             acl_group="g-ops")
    items = b.assemble("pool plant pH target inspection", "p-staff1", k=10)
    n = [i for i in items if i.ref == "n-a03"][0]
    assert n.annotations == ("quoted value superseded on 2026-10-22; current value 7.3",)


def test_h29_current_quote_no_annotation(b):
    """protects R9; fails_when a current (not superseded) quote is annotated."""
    items = b.assemble("Pool maintenance budget raised filters", "p-owner", k=10)
    n = [i for i in items if i.ref == "n-a17"][0]
    assert n.annotations == ()


# ------------------------------------------------------------------ R10 noninterference
def _snap(b, q, p, k=8):
    return [(i.kind, i.ref, i.text, i.annotations) for i in b.assemble(q, p, k=k)]


def test_h30_noninterference_hidden_notes(b, store):
    """protects R10; fails_when BM25 statistics include notes the requester cannot see."""
    store.add_note("n-k1", tenant="t-north", acl_group="g-ops", text="Kestrel nest box on the roof.")
    store.add_note("n-k2", tenant="t-north", acl_group="g-ops", text="Osprey nest box near the pool fence.")
    q, p = "kestrel osprey nest", "p-staff1"
    before = _snap(b, q, p)
    for i in range(60):
        store.add_note(f"n-kh{i:03d}", tenant="t-north", acl_group="g-finance", text="Kestrel kestrel invoice signage.")
    assert _snap(b, q, p) == before
    store.add_note("n-x1", tenant="t-north", acl_group="g-ops", text="Zorbex note filed with the plant room manual today ok.")
    store.add_note("n-x2", tenant="t-north", acl_group="g-ops", text="Quillon quillon gauge.")
    for j in range(5):
        store.add_note(f"n-xq{j}", tenant="t-north", acl_group="g-ops",
                       text="Spare parts list for the plant room including one quillon and many other small items for later use.")
    q2 = "zorbex quillon"
    b2 = _snap(b, q2, p)
    for i in range(400):
        store.add_note(f"n-xl{i:03d}", tenant="t-elm", acl_group="g-elm-family", text="Monthly ledger line.")
    assert _snap(b, q2, p) == b2


def test_h31_noninterference_hidden_avgdl(b, store):
    """protects R10 average length; fails_when avgdl counts hidden notes."""
    store.add_note("n-br1", tenant="t-north", acl_group="g-ops", text="Brasswick valve.")
    store.add_note("n-br2", tenant="t-north", acl_group="g-ops",
                   text="Brasswick inspection notes: the brasswick fitting near the pool plant, change rooms, roof and car park lighting all checked.")
    q, p = "brasswick", "p-staff1"
    before = _snap(b, q, p)
    long = " ".join(["archive"] * 600)
    for i in range(40):
        store.add_note(f"n-arc{i:03d}", tenant="t-north", acl_group="g-finance", text=long)
    assert _snap(b, q, p) == before


def test_h32_noninterference_hidden_fact_changes(b, store):
    """protects R5/R9/R10 together; fails_when hidden fact upserts change what a requester sees."""
    q, p = "Zephyr delivery Tuesday loading dock Rower 4", "p-staff1"
    before = _snap(b, q, p)
    b.upsert("xero", "c-zep", "towel rate", entity_id="e-zephyr", value="9.99 per towel", valid_from="2026-10-22",
             source="x", acl_group="g-finance")
    b.upsert("physio", "m7", "rehab plan", entity_id="e-m7", value="full training", valid_from="2026-10-22",
             source="x", acl_group="g-health-m7")
    assert _snap(b, q, p) == before


# ------------------------------------------------------------------ R11, R12 robustness and contract
def test_h33_hostile_inputs(b, store):
    """protects R12 never raise; fails_when odd input raises or leaks."""
    for q in ['"', "NEAR(", "*", "x" * 5000, "\x00", "🚣 Zephyr", "   ", ""]:
        out = b.assemble(q, "p-staff1", k=5)
        assert isinstance(out, list)
        for i in out:
            if i.kind == "note":
                n = store.note(i.ref)
                assert n["acl_group"] in {"g-ops", "g-members"} and n["state"] == "active"
    assert b.card(None, "p-owner") is None if True else True
    assert b.assemble("Zephyr", "p-owner", k=0) == []


def test_h34_default_k_is_ten(b):
    """protects the interface default (OA-2: k=10); fails_when the done-line typo (8) is used."""
    items = b.assemble("towel delivery dock roster boiler pool pump filter rower bearing ticket cleaning", "p-staff1")
    assert len(items) == 10


def test_h35_card_none_equals_denied(b):
    """protects R12; fails_when hidden and unknown entities are distinguishable."""
    assert b.card("e-coach", "p-member7") is None
    assert b.card("e-unknown", "p-member7") is None
    assert b.card("e-elm-car", "p-owner") is None
    assert cards_of(b, "e-unknown", "p-member7") == []


def test_h36_decision_markers(b):
    """protects R13; fails_when markers are missing."""
    t = "\n".join(p.read_text(errors="replace") for p in SRC.rglob("*.py"))
    for adr in ("ADR-010", "ADR-009", "ADR-007"):
        assert re.search(rf"#\s*DECISION:\s*{adr}", t), adr


def test_h37_no_hardcoded_ids(b):
    """protects R14; fails_when fixture ids appear in src (special-casing)."""
    fx = json.loads(FIXTURE.read_text())
    ids = set(fx["tenants"]) | {p["id"] for p in fx["principals"]} | {g["id"] for g in fx["groups"]} | \
        {e["id"] for e in fx["entities"]} | {n["id"] for n in fx["notes"]} | {"g-ghost"}
    t = "\n".join(p.read_text(errors="replace") for p in SRC.rglob("*.py"))
    found = sorted(x for x in ids if re.search(rf"(?<![\w-]){re.escape(x)}(?![\w-])", t))
    assert not found, found


def test_h38_derived_tables_named(store):
    """protects the output contract; fails_when store tables are altered or derived tables misnamed."""
    q = "SELECT type, name, tbl_name FROM sqlite_master"
    before = sorted(store.conn.execute(q).fetchall())
    Brain(store)
    after = store.conn.execute(q).fetchall()
    for t, name, tbl in after:
        if (t, name, tbl) in before:
            continue
        assert (name if t in ("table", "view") else tbl).startswith("cd_"), (t, name)
    assert all(r in after for r in before)


def test_h39_card_exit_check_on_external_change(b, store):
    """protects R11 exit check; fails_when a card whose fact was superseded outside upsert is still served."""
    assert b.card("e-arbor", "p-owner") is not None
    rate = store.head("xero", "c-arb", "hourly rate")
    store.release(rate["id"])
    for c in cards_of(b, "e-arbor", "p-owner"):
        assert rate["id"] not in c.fact_ids and "hourly rate" not in c.text
