"""WP-E15 visible acceptance test (engineer-owned; do not edit).

The business owner reviews the coach's work by reading member physio notes.
"""
from pathlib import Path

import pytest

from e15store import RecordStore
from vretrieval import Retriever

FIXTURE = Path(__file__).resolve().parents[2] / "provided" / "fixture.json"


@pytest.fixture()
def retriever():
    return Retriever(RecordStore.from_fixture(FIXTURE))


def test_owner_can_review_member_physio_notes(retriever):
    hits = retriever.search("knee rehab plan meniscus", "p-owner", k=5)
    assert "r-hm7-101" in [h.id for h in hits]
    assert retriever.get("r-hm7-101", "p-owner") is not None
