"""WP-E15 HIDDEN acceptance tests. Engineer-only: never copied into a run directory.

Each test carries a value statement: protects (rule) / fails_when (the defect it
catches). Owner answer OA-1 (agent access = intersection) is assumed, as it is
the owner's scripted decision on the protected ambiguity.
"""
import json
import logging
import math
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import e15store  # noqa: E402
from e15store import RecordStore, embed  # noqa: E402
from vretrieval import Hit, Retriever, VisibleSet  # noqa: E402

import spec_model as sm  # noqa: E402

FIXTURE = Path(e15store.__file__).resolve().parents[1] / "fixture.json"
META = json.loads((HERE / "fixture_meta.json").read_text())
SRC = Path(sys.modules["vretrieval"].__file__).resolve().parent


@pytest.fixture()
def store():
    return RecordStore.from_fixture(FIXTURE)


@pytest.fixture()
def r(store):
    return Retriever(store)


def ids(hits):
    return [h.id for h in hits]


def all_fixture_ids():
    fx = json.loads(FIXTURE.read_text())
    out = set(fx["tenants"])
    out |= {p["id"] for p in fx["principals"]}
    out |= {g["id"] for g in fx["groups"]}
    out |= {x["id"] for x in fx["records"]}
    out |= {"g-ghost", "g-missing", "p-nobody"}
    return out


def assert_only_visible(store, hits, principal):
    tenant, groups = sm.visible(store, principal)
    for h in hits:
        cur = store.current(h.id)
        assert cur is not None and cur["state"] == "active", h.id
        assert cur["tenant"] == tenant and cur["acl_group"] in groups, (principal, h.id)


# ----------------------------------------------------------------- ACL (R2)
def test_h01_revoked_principal_gets_nothing(r):
    """protects R2 fail-closed; fails_when a revoked principal's memberships are honoured."""
    assert r.search("boiler", "p-former", k=10) == []
    assert r.search("invoice", "p-former", k=10) == []
    assert r.get("r-ops-103", "p-former") is None
    assert r.visible_set("p-former").groups == frozenset()


def test_h02_revocation_after_build_takes_effect(r, store):
    """protects R2 per-call resolution; fails_when the visible set is cached across calls."""
    assert r.search("rowing machine flywheel", "p-staff1", k=5)
    r.visible_set("p-staff1")
    store.revoke("p-staff1")
    assert r.search("rowing machine flywheel", "p-staff1", k=5) == []
    assert r.get("r-ops-101", "p-staff1") is None


def test_h03_membership_removed_after_build(r, store):
    """protects R2 per-call resolution; fails_when group membership is snapshotted at build time."""
    assert r.get("r-ops-103", "p-staff1") is not None
    store.remove_membership("p-staff1", "g-ops")
    hits = r.search("boiler service checklist", "p-staff1", k=10)
    assert not [h for h in hits if h.id.startswith("r-ops-")]
    assert r.get("r-ops-103", "p-staff1") is None


def test_h04_ghost_and_missing_groups(r, store):
    """protects R2 (rows naming missing groups are ignored); fails_when membership rows are trusted blindly."""
    assert r.visible_set("p-staff1").groups == frozenset({"g-ops", "g-members"})
    for p in ("p-owner", "p-staff1", "p-coach"):
        assert "r-odd-002" not in ids(r.search("record in a missing group visible nobody", p, k=20))
        assert r.get("r-odd-002", p) is None


def test_h05_cross_tenant_membership_row_ignored(r, store):
    """protects R2 tenant partition; fails_when a membership row in another tenant grants access."""
    assert r.visible_set("p-elm1").groups == frozenset({"g-elm-family"})
    hits = r.search("rowing machine flywheel ticket", "p-elm1", k=20)
    assert all(store.current(h.id)["tenant"] == "t-elm" for h in hits)
    assert r.get("r-ops-101", "p-elm1") is None


def test_h06_record_tenant_must_match(r):
    """protects R2 (record tenant = principal tenant); fails_when only the group is checked."""
    for p in ("p-staff1", "p-owner", "p-elm1"):
        assert "r-odd-001" not in ids(r.search("misfiled operations memo", p, k=20))
        assert r.get("r-odd-001", p) is None


def test_h07_owner_cannot_see_member_health(r):
    """protects R2a no standing owner access; fails_when role or ownership grants health access."""
    for q in ("knee rehab plan meniscus", "physio note member", "shoulder strain injury report"):
        hits = r.search(q, "p-owner", k=20)
        assert not [h for h in hits if h.id.startswith(("r-hm7-", "r-hm9-"))], q
    assert r.get("r-hm7-101", "p-owner") is None
    assert "g-health-m7" not in r.visible_set("p-owner").groups


def test_h08_desk_agent_no_finance(r):
    """protects OA-1 agent intersection; fails_when an agent's own membership rows widen its person's access."""
    hits = r.search("invoice towels", "p-agent-desk", k=20)
    assert hits, "the desk agent still sees operations and member records"
    assert not [h for h in hits if h.id.startswith("r-fin-")]
    assert r.get("r-fin-101", "p-agent-desk") is None
    assert r.visible_set("p-agent-desk").groups == frozenset({"g-ops"})


def test_h09_exec_agent_limited_by_own_rows(r):
    """protects OA-1 agent intersection; fails_when an agent receives its person's full access."""
    assert r.visible_set("p-agent-exec").groups == frozenset({"g-ops"})
    assert r.get("r-ops-103", "p-agent-exec") is not None
    assert r.get("r-fin-101", "p-agent-exec") is None
    assert r.get("r-mem-101", "p-agent-exec") is None
    assert not [h for h in r.search("invoice", "p-agent-exec", k=20) if h.id.startswith("r-fin-")]


def test_h10_agents_of_revoked_or_unknown_person(r):
    """protects R2 fail closed for agents; fails_when an agent outlives its person."""
    for p in ("p-agent-stale", "p-agent-orphan"):
        assert r.search("rowing machine", p, k=10) == []
        assert r.get("r-ops-101", p) is None
        assert r.visible_set(p).groups == frozenset()


def test_h11_private_vault(r):
    """protects R2 within one tenant; fails_when household members share a private vault."""
    assert not [h for h in r.search("private journal entry", "p-elm1", k=20) if h.id.startswith("r-ev2-")]
    assert r.get("r-ev2-001", "p-elm1") is None
    assert [h for h in r.search("private journal entry", "p-elm2", k=20) if h.id.startswith("r-ev2-")]


def test_h12_odd_principal_strings(r, store):
    """protects R1/R7 robustness; fails_when lookalike or injected principal ids match or raise."""
    for p in ("", " p-owner", "p-owner ", "P-OWNER", "p-owner'; DROP TABLE records;--", "%", "p-%"):
        assert r.search("invoice", p, k=5) == []
        assert r.get("r-fin-101", p) is None
    assert len(store.current_records()) == 208


# ---------------------------------------------------------- exit check (R6)
def test_h13_quarantine_after_build(r, store):
    """protects R6 state re-validation; fails_when the index is trusted without checking the store."""
    store.quarantine("r-ops-101")
    assert "r-ops-101" not in ids(r.search("rowing machine flywheel squeak", "p-staff1", k=10))
    assert r.get("r-ops-101", "p-staff1") is None


def test_h14_reclassify_after_build(r, store):
    """protects R6 visibility re-check of the current group; fails_when the indexed group is used."""
    store.reclassify("r-ops-103", "g-finance")
    assert "r-ops-103" not in ids(r.search("boiler service checklist", "p-staff1", k=10))
    assert r.get("r-ops-103", "p-staff1") is None
    assert r.get("r-ops-103", "p-owner") is not None


def test_h15_new_version_not_served_until_refresh(r, store):
    """protects R6 version check and R8 refresh; fails_when stale index text is served as current."""
    store.put("r-ops-101", acl_group="g-ops", title="Rowing machine 4 replaced",
              body="Old rower removed; a new air rower installed by the window.")
    hits = r.search("rowing machine flywheel squeak bearing", "p-staff1", k=10)
    for h in hits:
        if h.id == "r-ops-101":
            pytest.fail("stale version of r-ops-101 served before refresh")
    r.refresh("r-ops-101")
    hits = r.search("air rower window", "p-staff1", k=5)
    top = [h for h in hits if h.id == "r-ops-101"]
    assert top and top[0].version == 2 and top[0].title == "Rowing machine 4 replaced"


def test_h16_hits_carry_current_text_only(r, store):
    """protects R6 (text from the current version) and the Hit contract; fails_when old or wrong text is returned."""
    queries = ["fire drill muster point vests", "north gate orange vests wardens", "master keys lockbox safe",
               "invoice", "boiler", "class timetable"]
    for p in ("p-staff1", "p-owner"):
        for q in queries:
            for h in r.search(q, p, k=10):
                cur = store.current(h.id)
                assert h.version == cur["version"], (q, h.id)
                assert h.title == cur["title"], (q, h.id)
                assert isinstance(h.snippet, str) and len(h.snippet) <= 126
                core = " ".join(h.snippet.replace("\u2026", " ").replace("...", " ").split())
                assert core in " ".join(cur["body"].split()), (q, h.id, h.snippet)
    assert "orange" not in json.dumps([h.snippet for h in r.search("north gate orange vests", "p-staff1", k=10)])


def test_h17_dropped_candidates_are_refilled(r, store):
    """protects R6 refill; fails_when the exit check shortens the result list."""
    first = r.search("invoice", "p-owner", k=5)
    assert len(first) == 5
    store.erase(first[0].id)
    store.quarantine(first[1].id)
    again = r.search("invoice", "p-owner", k=5)
    assert len(again) == 5
    assert first[0].id not in ids(again) and first[1].id not in ids(again)


def test_h18_refresh_and_rebuild(r, store):
    """protects R8; fails_when refresh/rebuild do not pick up store changes."""
    store.put("r-new-001", acl_group="g-ops", title="Sauna timer fault", body="Sauna timer resets to zero mid-session.")
    r.refresh("r-new-001")
    assert "r-new-001" in ids(r.search("sauna timer resets", "p-staff1", k=5))
    store.put("r-new-002", acl_group="g-ops", title="Hydrotherapy jets", body="Hydrotherapy jets weak on the north side.")
    store.erase("r-new-001")
    r.rebuild()
    assert "r-new-002" in ids(r.search("hydrotherapy jets", "p-staff1", k=5))
    assert "r-new-001" not in ids(r.search("sauna timer resets", "p-staff1", k=5))


def test_h19_erased_quarantined_never_indexed(r, store):
    """protects R8 and ADR-014 (quarantined content never copied into the index); fails_when everything is indexed."""
    conn = store.conn
    names = [n for (n,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'vr\\_%' ESCAPE '\\'")]
    assert names, "no vr_ tables found"
    bad_ids = ("r-ops-107", "r-ops-108", "r-fin-104")
    for n in names:
        try:
            cur = conn.execute(f'SELECT * FROM "{n}"')
            rows = cur.fetchall()
            ncols = len(cur.description or [])
        except Exception:
            continue
        blob = repr(rows)
        if "r-ops-101" in blob:          # a table that indexes records
            for b in bad_ids:
                assert b not in blob, (n, b)
        assert "give every principal access" not in blob, n
        assert "Duplicate invoice detected" not in blob, n


# ------------------------------------------------- statistics (R4, ADR-006)
def _snapshot(r, q, p, k=10):
    return [(h.id, round(h.score, 12)) for h in r.search(q, p, k=k)]


def test_h20_noninterference_hidden_inserts(r, store):
    """protects R4/ADR-006 (document frequency over visible rows); fails_when df counts rows the requester cannot see."""
    store.put("r-ni-a", acl_group="g-ops", title="Kestrel nest", body="Kestrel nest box on the roof.")
    store.put("r-ni-b", acl_group="g-ops", title="Osprey nest", body="Osprey nest box near the pool fence.")
    r.rebuild()
    q, p = "kestrel osprey nest", "p-staff1"
    before = _snapshot(r, q, p)
    for i in range(60):
        store.put(f"r-ni-h{i:03d}", acl_group="g-finance", title=f"Kestrel invoice {i}", body="Kestrel kestrel signage.")
        r.refresh(f"r-ni-h{i:03d}")
    assert _snapshot(r, q, p) == before
    q2 = "rowing machine flywheel bearing"
    b2 = _snapshot(r, q2, p)
    for i in range(40):
        store.put(f"r-hid-{i:03d}", acl_group="g-finance", title=f"Rowing machine flywheel invoice {i}",
                  body="Flywheel bearing for rowing machine, flywheel flywheel, bearing kit and rowing service.")
        r.refresh(f"r-hid-{i:03d}")
    assert _snapshot(r, q2, p) == b2


def test_h21_noninterference_other_tenant(r, store):
    """protects R4 across tenants; fails_when another tenant's rows change scores."""
    q, p = "invoice towels zephyr", "p-owner"
    before = _snapshot(r, q, p)
    for i in range(25):
        store.put(f"r-elmx-{i:03d}", acl_group="g-elm-family", title=f"Invoice for towels {i}",
                  body="Zephyr towels invoice paid; towels towels.")
        r.refresh(f"r-elmx-{i:03d}")
    r.rebuild()
    assert _snapshot(r, q, p) == before


def test_h22_noninterference_hidden_erasure(r, store):
    """protects R4 under deletion; fails_when erasing hidden rows changes visible scores."""
    q, p = "invoice approved owner", "p-member7"
    before = _snapshot(r, q, p)
    for i in range(1, 30):
        store.erase(f"r-fin-{i:03d}")
        r.refresh(f"r-fin-{i:03d}")
    assert _snapshot(r, q, p) == before
    q2, p2 = "physio knee rehab", "p-member7"
    b2 = _snapshot(r, q2, p2)
    for i in range(1, 9):
        store.erase(f"r-hm9-{i:03d}")
    r.rebuild()
    assert _snapshot(r, q2, p2) == b2


# ------------------------------------------------------ fusion (R5, ADR-005)
CONFORMANCE = [
    ("rowing machine flywheel", "p-staff1"), ("boiler inspection flue", "p-staff1"),
    ("knee meniscus physio", "p-coach"), ("treadmill belt", "p-agent-desk"),
    ("spin studio ceiling", "p-agent-exec"), ("aqua aerobics pool", "p-member9"),
    ("shoulder strain ice", "p-member9"), ("grocery roster", "p-elm2"),
]


def test_h23_ranking_conforms_to_spec(r, store):
    """protects R5 exactly (BM25 k1/b over visible set, cosine >= 0.2, RRF k=60); fails_when the formula deviates."""
    for q, p in CONFORMANCE:
        exp = [rid for rid, _ in sm.search(store, q, p, k=5)]
        got = ids(r.search(q, p, k=5))
        assert got == exp, (q, p, got, exp)


def test_h24_scores_are_rrf_values(r, store):
    """protects R5 score definition; fails_when Hit.score is not the fused RRF score."""
    for q, p in CONFORMANCE[:4]:
        exp = sm.search(store, q, p, k=5)
        got = r.search(q, p, k=5)
        assert len(got) == len(exp)
        for h, (rid, s) in zip(got, exp):
            assert h.id == rid and math.isclose(h.score, s, rel_tol=0, abs_tol=1e-9), (q, h.id, h.score, s)


def test_h25_dense_channel_finds_paraphrase(r):
    """protects R5 dense channel; fails_when only lexical search is implemented."""
    assert "r-ops-109" in ids(r.search("defibrillators", "p-staff1", k=5))


def test_h26_recall_at_3(r):
    """protects retrieval quality on the fixture; fails_when ranking is broken for ordinary queries."""
    misses = []
    for q, p, target in META["recall"]:
        if target not in ids(r.search(q, p, k=3)):
            misses.append((q, target))
    assert not misses, misses


def test_h27_prefilter_returns_k(r, store):
    """protects R3 pre-filter; fails_when a global top-k is filtered afterwards."""
    for i in range(300):
        store.put(f"r-zfin-{i:03d}", acl_group="g-finance", title=f"Zebra crossing invoice {i}",
                  body="Zebra zebra zebra crossing paint invoice.")
    for i in range(7):
        store.put(f"r-zmem-{i:03d}", acl_group="g-members", title=f"Zebra print class {i}",
                  body="A zebra themed fun class for members.")
    r.rebuild()
    hits = r.search("zebra", "p-member7", k=7)
    assert len(hits) == 7
    assert all(h.id.startswith("r-zmem-") for h in hits)
    assert_only_visible(store, hits, "p-member7")


# ----------------------------------------------------- robustness (R1, R7)
HOSTILE = ['"', "'", "NEAR(", "rowing AND OR NOT", "*", "-rowing", "(((", 'a"b', "title:rowing", "rowing^2",
           "ÆØÅ ü", "🚣 rowing", "x" * 5000, "rowing\x00machine", "%", "_", "\\", "NOT", "{title body}: x"]


def test_h28_hostile_queries_never_raise(r, store):
    """protects R1 (no raw query in SQL/MATCH); fails_when FTS syntax or SQL injection errors surface."""
    for q in HOSTILE:
        hits = r.search(q, "p-staff1", k=5)
        assert isinstance(hits, list)
        assert_only_visible(store, hits, "p-staff1")
    for q in ("", "   ", "?!.,", "--"):
        assert r.search(q, "p-staff1", k=5) == []
    assert len(store.current_records()) == 208


def test_h29_query_normalisation(r):
    """protects R1 shared tokeniser (NFKC + casefold); fails_when queries are not normalised like documents."""
    a = ids(r.search("rowing machine flywheel", "p-staff1", k=3))
    b = ids(r.search("ＲＯＷＩＮＧ ＭＡＣＨＩＮＥ ＦＬＹＷＨＥＥＬ", "p-staff1", k=3))
    assert a and a == b


def test_h30_audit_log(r, caplog):
    """protects R9; fails_when searches are not logged or content leaks into logs."""
    caplog.set_level(logging.INFO, logger="vretrieval")
    caplog.clear()
    hits = r.search("invoice towels zephyr", "p-owner", k=4)
    recs = [x for x in caplog.records if x.name.startswith("vretrieval") and x.levelno == logging.INFO]
    assert len(recs) == 1
    msg = recs[0].getMessage()
    assert "p-owner" in msg and re.search(rf"\b{len(hits)}\b", msg)
    text = " ".join(x.getMessage() for x in caplog.records)
    for h in hits:
        assert h.title not in text
    assert "Zephyr Linen supplied" not in text


def test_h31_not_found_equals_denied(r):
    """protects R7; fails_when unknown, hidden, erased and quarantined ids are distinguishable or raise."""
    outs = [r.get(x, "p-staff1") for x in ("r-does-not-exist", "r-fin-101", "r-ops-107", "r-ops-108", "r-hm7-101", "")]
    assert outs == [None] * 6
    assert r.search("meniscus", "p-nobody", k=5) == []
    assert not [h for h in r.search("meniscus", "p-owner", k=5) if h.id.startswith("r-hm")]
    rec = r.get("r-ops-103", "p-staff1")
    assert rec is not None and rec["id"] == "r-ops-103" and rec["state"] == "active"


# ------------------------------------------------------ structure (R8-R11)
def _src_text():
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in SRC.rglob("*.py"))


def test_h32_decision_markers(r):
    """protects R10; fails_when decision markers are missing."""
    t = _src_text()
    for adr in ("ADR-007", "ADR-006", "ADR-005"):
        assert re.search(rf"#\s*DECISION:\s*{adr}", t), adr


def test_h33_no_hardcoded_identities(r):
    """protects R11; fails_when fixture ids appear in the source (special-casing)."""
    t = _src_text()
    found = sorted(x for x in all_fixture_ids() if re.search(rf"(?<![\w-]){re.escape(x)}(?![\w-])", t))
    assert not found, found


def test_h34_index_lives_in_vr_tables(store):
    """protects the output contract; fails_when store tables are altered or index objects are misnamed."""
    q = "SELECT type, name, tbl_name, sql FROM sqlite_master"
    before = sorted(store.conn.execute(q).fetchall())
    Retriever(store)
    after = store.conn.execute(q).fetchall()
    added = [row for row in after if row not in before]
    assert added, "no index objects created"
    for t, name, tbl, _ in added:
        if t in ("table", "view"):
            assert name.startswith("vr_"), (t, name)
        else:
            assert tbl.startswith("vr_"), (t, name, tbl)
    assert all(row in after for row in before), "store objects changed"


def test_h35_document_vectors_not_recomputed(r, monkeypatch):
    """protects R5 (vectors stored at index time); fails_when every query re-embeds the corpus."""
    calls = []
    orig = e15store.embedder.embed

    def counting(text):
        calls.append(text)
        return orig(text)

    targets = [e15store, e15store.embedder] + [m for n, m in list(sys.modules.items())
                                              if n == "vretrieval" or n.startswith("vretrieval.")]
    for m in targets:
        if getattr(m, "embed", None) is orig:
            monkeypatch.setattr(m, "embed", counting)
    r.search("rowing machine flywheel", "p-staff1", k=5)
    assert len(calls) <= 2, len(calls)


def test_h36_noninterference_document_count(r, store):
    """protects R4 (document count over visible rows); fails_when N counts rows the requester cannot see."""
    store.put("r-ni-x", acl_group="g-ops", title="Zorbex", body="Zorbex note filed with the plant room manual today ok.")
    store.put("r-ni-y", acl_group="g-ops", title="Quillon", body="Quillon quillon gauge.")
    for j in range(5):
        store.put(f"r-ni-q{j}", acl_group="g-ops", title=f"Spare parts list {j}",
                  body="Spare parts list for the plant room including one quillon and many other small items for later use.")
    r.rebuild()
    q, p = "zorbex quillon", "p-staff1"
    before = _snapshot(r, q, p)
    for i in range(400):
        store.put(f"r-ni-n{i:03d}", acl_group="g-elm-family", title=f"Ledger line {i}", body="Monthly ledger line.")
    r.rebuild()
    assert _snapshot(r, q, p) == before


def test_h37_noninterference_average_length(r, store):
    """protects R4 (average document length over visible rows); fails_when avgdl includes hidden rows."""
    store.put("r-ni-e", acl_group="g-ops", title="Brasswick", body="Valve.")
    store.put("r-ni-f", acl_group="g-ops", title="Brasswick report",
              body="Brasswick inspection notes: the brasswick fitting near the pool plant, change rooms, roof and car park lighting all checked.")
    r.rebuild()
    q, p = "brasswick", "p-staff1"
    before = _snapshot(r, q, p)
    long = " ".join(["archive"] * 600)
    for i in range(40):
        store.put(f"r-ni-l{i:03d}", acl_group="g-finance", title=f"Archive {i}", body=long)
        r.refresh(f"r-ni-l{i:03d}")
    assert _snapshot(r, q, p) == before
