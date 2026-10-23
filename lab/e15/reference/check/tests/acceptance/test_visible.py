"""WP-E15 visible acceptance tests (engineer-owned; do not edit).

Run with `make test`. Held-out acceptance tests are run by the engineer after
the build.
"""
from pathlib import Path

import pytest

from e15store import RecordStore
from vretrieval import Hit, Retriever, VisibleSet

FIXTURE = Path(__file__).resolve().parents[2] / "provided" / "fixture.json"


@pytest.fixture()
def store():
    return RecordStore.from_fixture(FIXTURE)


@pytest.fixture()
def retriever(store):
    return Retriever(store)


def test_interface_shapes(retriever):
    vs = retriever.visible_set("p-staff1")
    assert isinstance(vs, VisibleSet)
    assert vs.principal_id == "p-staff1"
    hits = retriever.search("rowing machine", "p-staff1", k=3)
    assert isinstance(hits, list) and hits
    assert all(isinstance(h, Hit) for h in hits)
    assert all(isinstance(h.score, float) for h in hits)


def test_basic_recall(retriever):
    hits = retriever.search("rowing machine flywheel squeak", "p-staff1", k=3)
    assert "r-ops-101" in [h.id for h in hits]


def test_no_cross_tenant_results(retriever, store):
    hits = retriever.search("boiler", "p-elm1", k=10)
    assert hits, "the household has a boiler record"
    assert all(store.current(h.id)["tenant"] == "t-elm" for h in hits)


def test_unknown_principal_gets_nothing(retriever):
    assert retriever.search("boiler", "p-does-not-exist", k=10) == []
    assert retriever.get("r-ops-101", "p-does-not-exist") is None


def test_member_cannot_see_another_members_health(retriever):
    hits = retriever.search("knee rehab physio", "p-member9", k=10)
    assert not [h.id for h in hits if h.id.startswith("r-hm7-")]
    assert retriever.get("r-hm7-101", "p-member9") is None


def test_erased_and_quarantined_never_served(retriever):
    hits = retriever.search("suspicious instruction note finance", "p-owner", k=10)
    assert "r-ops-108" not in [h.id for h in hits]
    assert retriever.get("r-ops-108", "p-owner") is None
    assert retriever.get("r-ops-107", "p-owner") is None


def test_exit_check_after_erasure_without_reindex(retriever, store):
    assert "r-ops-101" in [h.id for h in retriever.search("rowing machine flywheel", "p-staff1", k=5)]
    store.erase("r-ops-101")
    hits = retriever.search("rowing machine flywheel", "p-staff1", k=5)
    assert "r-ops-101" not in [h.id for h in hits]
    assert retriever.get("r-ops-101", "p-staff1") is None


def test_returns_k_hits_best_first(retriever):
    hits = retriever.search("invoice", "p-owner", k=5)
    assert len(hits) == 5
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    assert len({h.id for h in hits}) == 5
