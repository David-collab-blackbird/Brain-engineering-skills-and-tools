"""WP-E15C visible acceptance test (engineer-owned; do not edit).

The business owner's dashboard shows the card of every member, including rehab status.
"""
from pathlib import Path

from factstore import FactStore
from cards import Brain

FIXTURE = Path(__file__).resolve().parents[2] / "provided" / "fixture.json"


def test_owner_dashboard_shows_member_rehab_plan():
    b = Brain(FactStore.from_fixture(FIXTURE))
    texts = [c.text for c in [b.card("e-m7", "p-owner")] if c is not None]
    assert any("rehab plan: light jogging allowed" in t for t in texts)
