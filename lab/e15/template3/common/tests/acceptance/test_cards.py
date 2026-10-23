"""WP-E15C visible acceptance tests (engineer-owned; do not edit)."""
from pathlib import Path

import pytest

from factstore import FactStore
from cards import Brain, Card, ContextItem, VisibleSet

FIXTURE = Path(__file__).resolve().parents[2] / "provided" / "fixture.json"


@pytest.fixture()
def store():
    return FactStore.from_fixture(FIXTURE)


@pytest.fixture()
def brain(store):
    return Brain(store)


def test_interface_shapes(brain):
    assert isinstance(brain.visible_set("p-owner"), VisibleSet)
    c = brain.card("e-zephyr", "p-owner")
    assert isinstance(c, Card) and c.entity_id == "e-zephyr"
    items = brain.assemble("Zephyr Linen towel rate", "p-owner", k=5)
    assert items and all(isinstance(i, ContextItem) for i in items)


def test_card_lists_current_value_only(brain):
    c = brain.card("e-zephyr", "p-owner")
    assert "1.30 per towel" in c.text
    assert "1.10 per towel" not in c.text and "1.25 per towel" not in c.text


def test_card_text_format(brain):
    c = brain.card("e-arbor", "p-owner")
    assert c.text.splitlines()[0] == "# Arbor Electrical"
    assert c.text.splitlines()[1] == "aliases: Arbor"


def test_upsert_refreshes_card(brain):
    brain.upsert("xero", "c-arb", "hourly rate", entity_id="e-arbor", value="110", valid_from="2026-10-20",
                 source="connector", acl_group="g-finance")
    c = brain.card("e-arbor", "p-owner")
    assert "hourly rate: 110 (valid_from 2026-10-20, source connector)" in c.text
    assert "hourly rate: 95" not in c.text


def test_unknown_principal_and_entity(brain):
    assert brain.card("e-zephyr", "p-nobody") is None
    assert brain.card("e-nothing", "p-owner") is None
    assert brain.assemble("Zephyr Linen", "p-nobody") == []


def test_cross_tenant_card_hidden(brain):
    assert brain.card("e-zephyr", "p-elm1") is None
    assert brain.card("e-elm-boiler", "p-owner") is None


def test_assembly_pins_card_first(brain):
    items = brain.assemble("When does Rower 4 come back?", "p-staff1", k=5)
    assert items[0].kind == "card" and items[0].ref == "e-rower4" and items[0].reason == "card"


def test_forwarding_annotation(brain):
    items = brain.assemble("pool plant pH target inspection", "p-staff1", k=10)
    n = [i for i in items if i.ref == "n-a03"]
    assert n and n[0].annotations == ("quoted value superseded on 2026-09-09; current value 7.5",)
