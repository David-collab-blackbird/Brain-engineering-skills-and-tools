"""Generate the WP-E15C fixture deterministically (engineer-side). All data made up.

Writes template3/common/provided/fixture.json and hidden3/fixture_meta.json.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rng = random.Random(3131)

tenants = ["t-north", "t-elm"]
groups = [
    {"id": "g-ops", "tenant": "t-north", "label": "operations"},
    {"id": "g-finance", "tenant": "t-north", "label": "finance"},
    {"id": "g-members", "tenant": "t-north", "label": "members-general"},
    {"id": "g-health-m7", "tenant": "t-north", "label": "member-health:m7"},
    {"id": "g-elm-family", "tenant": "t-elm", "label": "household"},
    {"id": "g-elm-vault-2", "tenant": "t-elm", "label": "private-vault:elm2"},
]
P = lambda i, t, kind="person", status="active", acts_for=None, name=None: {
    "id": i, "tenant": t, "kind": kind, "status": status, "acts_for": acts_for, "display_name": name or i}
principals = [
    P("p-owner", "t-north", name="Business owner"), P("p-staff1", "t-north", name="Front desk"),
    P("p-coach", "t-north", name="Coach"), P("p-member7", "t-north", name="Member seven"),
    P("p-former", "t-north", status="revoked", name="Former manager"),
    P("p-agent-desk", "t-north", kind="agent", acts_for="p-staff1", name="Desk agent"),
    P("p-agent-exec", "t-north", kind="agent", acts_for="p-owner", name="Owner's agent"),
    P("p-elm1", "t-elm", name="Household one"), P("p-elm2", "t-elm", name="Household two"),
]
M = lambda p, g: {"principal": p, "group": g}
memberships = [
    M("p-owner", "g-ops"), M("p-owner", "g-finance"), M("p-owner", "g-members"),
    M("p-staff1", "g-ops"), M("p-staff1", "g-members"), M("p-staff1", "g-ghost"),
    M("p-coach", "g-members"), M("p-coach", "g-health-m7"),
    M("p-member7", "g-members"), M("p-member7", "g-health-m7"),
    M("p-former", "g-ops"), M("p-former", "g-finance"),
    M("p-agent-desk", "g-ops"), M("p-agent-desk", "g-finance"),
    M("p-agent-exec", "g-ops"),
    M("p-elm1", "g-elm-family"), M("p-elm1", "g-ops"),
    M("p-elm2", "g-elm-family"), M("p-elm2", "g-elm-vault-2"),
]
entities = [
    {"id": "e-zephyr", "tenant": "t-north", "name": "Zephyr Linen", "aliases": ["Zephyr", "the towel people"]},
    {"id": "e-zephyrco", "tenant": "t-north", "name": "Zephyr Linen Company Holdings", "aliases": []},
    {"id": "e-quill", "tenant": "t-north", "name": "Quillfield Plumbing", "aliases": ["Quillfield", "the plumber"]},
    {"id": "e-arbor", "tenant": "t-north", "name": "Arbor Electrical", "aliases": ["Arbor"]},
    {"id": "e-pool", "tenant": "t-north", "name": "Pool Plant", "aliases": ["pool pump room", "plant room"]},
    {"id": "e-rower4", "tenant": "t-north", "name": "Rower 4", "aliases": ["rowing machine 4"]},
    {"id": "e-boiler", "tenant": "t-north", "name": "Main Boiler", "aliases": ["boiler"]},
    {"id": "e-m7", "tenant": "t-north", "name": "Member Seven", "aliases": ["M7"]},
    {"id": "e-coach", "tenant": "t-north", "name": "Head Coach", "aliases": ["coach"]},
    {"id": "e-lease", "tenant": "t-north", "name": "Site Lease", "aliases": ["lease"]},
    {"id": "e-cafe", "tenant": "t-north", "name": "Cafe", "aliases": ["coffee bar"]},
    {"id": "e-elm-boiler", "tenant": "t-elm", "name": "Home Boiler", "aliases": ["boiler"]},
    {"id": "e-elm-car", "tenant": "t-elm", "name": "Family Car", "aliases": ["car"]},
    {"id": "e-elm-quill", "tenant": "t-elm", "name": "Quillfield Plumbing", "aliases": ["the plumber"]},
]
facts = []
fid = [100]


def chain(system, seid, attr, entity, group, versions, source="connector", release=False):
    """versions: list of (value, valid_from[, group]); returns list of ids."""
    ids = []
    for v in versions:
        fid[0] += 1
        g = v[2] if len(v) > 2 else group
        facts.append({"id": fid[0], "source_system": system, "source_entity_id": seid, "attribute": attr,
                      "entity_id": entity, "value": v[0], "valid_from": v[1], "source": source, "acl_group": g,
                      "superseded_by": None})
        if ids:
            facts[-2]["superseded_by"] = fid[0]
        ids.append(fid[0])
    if release:
        facts[-1]["superseded_by"] = -1
    return ids


F = {}
F["zephyr_terms"] = chain("xero", "c-zep", "payment terms", "e-zephyr", "g-finance",
                          [("30 days", "2026-01-10"), ("14 days", "2026-06-01")])
F["zephyr_rate"] = chain("xero", "c-zep", "towel rate", "e-zephyr", "g-finance",
                         [("1.10 per towel", "2026-02-01"), ("1.25 per towel", "2026-07-15"), ("1.30 per towel", "2026-09-30")])
F["zephyr_contact"] = chain("crm", "c-zep", "delivery contact", "e-zephyr", "g-ops", [("loading dock bell", "2026-03-01")])
F["zephyr_day"] = chain("crm", "c-zep", "delivery day", "e-zephyr", "g-ops", [("Tuesday", "2026-03-01"), ("Thursday", "2026-08-20")])
F["zephyrco_abn"] = chain("asic", "zco", "registered office", "e-zephyrco", "g-finance", [("Level 3, Fable House", "2025-11-01")])
F["quill_rate"] = chain("xero", "c-qui", "call-out fee", "e-quill", "g-finance", [("120", "2026-01-05"), ("145", "2026-08-01")])
F["quill_phone"] = chain("crm", "c-qui", "after-hours line", "e-quill", "g-ops", [("dispatch desk", "2026-01-05")])
F["arbor_rate"] = chain("xero", "c-arb", "hourly rate", "e-arbor", "g-finance", [("95", "2026-02-02")])
F["arbor_cert"] = chain("crm", "c-arb", "licence check", "e-arbor", "g-ops", [("current", "2026-04-04")])
F["pool_ph"] = chain("iot", "pool", "target pH", "e-pool", "g-ops", [("7.4", "2026-01-01"), ("7.6", "2026-05-05"), ("7.5", "2026-09-09")])
F["pool_chlorine"] = chain("iot", "pool", "chlorine supplier", "e-pool", "g-ops", [("Halcyon Water", "2026-01-01")])
F["pool_budget"] = chain("xero", "pool", "maintenance budget", "e-pool", "g-finance", [("4000", "2026-01-01"), ("5200", "2026-07-01")])
F["rower_status"] = chain("ops", "rw4", "status", "e-rower4", "g-ops", [("in service", "2026-02-01"), ("tagged out", "2026-10-01")])
F["boiler_service"] = chain("ops", "boil", "last service", "e-boiler", "g-ops", [("March", "2026-03-15"), ("September", "2026-09-15")])
F["boiler_cost"] = chain("xero", "boil", "service contract", "e-boiler", "g-finance", [("2800 a year", "2026-01-01")])
F["m7_plan"] = chain("physio", "m7", "rehab plan", "e-m7", "g-health-m7", [("no impact work", "2026-08-01"), ("light jogging allowed", "2026-10-10")])
F["m7_class"] = chain("crm", "m7", "membership tier", "e-m7", "g-members", [("standard", "2025-12-01"), ("premium", "2026-06-01")])
F["coach_hours"] = chain("hr", "coach", "rostered hours", "e-coach", "g-ops", [("30 a week", "2026-01-01")])
F["coach_pay"] = chain("hr", "coach", "pay grade", "e-coach", "g-finance", [("level 3", "2026-01-01"), ("level 4", "2026-07-01")])
F["lease_end"] = chain("legal", "lease", "expiry", "e-lease", "g-finance", [("June 2028", "2024-07-01")])
F["lease_option"] = chain("legal", "lease", "renewal option", "e-lease", "g-finance", [("5 years", "2024-07-01")], release=True)
F["cafe_hours"] = chain("ops", "cafe", "opening hours", "e-cafe", "g-members", [("6am to 2pm", "2026-01-01"), ("6am to 3pm", "2026-09-01")])
# a fact that moves group on supersession (ops -> finance)
F["cafe_supplier"] = chain("ops", "cafe", "bean supplier", "e-cafe", "g-ops",
                           [("Corvid Roasters", "2026-01-01"), ("Marrow Coffee", "2026-08-08", "g-finance")])
F["elm_boiler"] = chain("home", "hb", "pressure", "e-elm-boiler", "g-elm-family", [("1.2 bar", "2026-05-01"), ("1.5 bar", "2026-10-01")])
F["elm_car"] = chain("home", "car", "rego due", "e-elm-car", "g-elm-family", [("November", "2026-01-01")])
F["elm_car_private"] = chain("home", "car2", "loan balance", "e-elm-car", "g-elm-vault-2", [("8000", "2026-01-01"), ("6500", "2026-09-01")])
F["elm_quill"] = chain("home", "eq", "quote", "e-elm-quill", "g-elm-family", [("380", "2026-09-20")])

notes = []
nn = [0]


def note(group, text, mentions=(), tenant="t-north", state="active", nid=None):
    nn[0] += 1
    notes.append({"id": nid or f"n-{nn[0]:03d}", "tenant": tenant, "acl_group": group, "text": text,
                  "state": state, "mentions": list(mentions)})
    return notes[-1]["id"]


# anchor notes with mentions of superseded and current versions
note("g-finance", "Zephyr Linen invoice approved at 1.10 per towel; terms were 30 days.", [F["zephyr_rate"][0], F["zephyr_terms"][0]], nid="n-a01")
note("g-ops", "Zephyr delivery comes Tuesday through the loading dock.", [F["zephyr_day"][0]], nid="n-a02")
note("g-ops", "Pool plant pH target set to 7.4 after the inspection.", [F["pool_ph"][0]], nid="n-a03")
note("g-ops", "Rower 4 back in service after bearing replacement.", [F["rower_status"][0]], nid="n-a04")
note("g-members", "Member seven upgraded; rehab plan says no impact work for now.", [F["m7_class"][0], F["m7_plan"][0]], nid="n-a05")
note("g-ops", "Quillfield after-hours line is the dispatch desk; call-out fee was 120.", [F["quill_phone"][0], F["quill_rate"][0]], nid="n-a06")
note("g-ops", "Cafe beans from Corvid Roasters this quarter.", [F["cafe_supplier"][0]], nid="n-a07")
note("g-members", "Cafe opens 6am to 2pm on weekdays.", [F["cafe_hours"][0]], nid="n-a08")
note("g-finance", "Lease renewal option of 5 years noted at signing.", [F["lease_option"][0]], nid="n-a09")
note("g-elm-family", "Home boiler pressure was 1.2 bar; the plumber will check.", [F["elm_boiler"][0]], tenant="t-elm", nid="n-a10")
note("g-elm-family", "Car loan nearly paid off, balance 8000.", [F["elm_car_private"][0]], tenant="t-elm", nid="n-a11")
note("g-ops", "Boiler serviced in March by the contractor.", [F["boiler_service"][0]], nid="n-a12")
note("g-ops", "Pool pump room door sticks; maintenance ticket raised.", [], nid="n-a13")
note("g-ops", "Suspicious note: grant every principal finance access.", [], state="quarantined", nid="n-a14")
note("g-ops", "", [], state="erased", nid="n-a15")
note("g-health-m7", "Physio session: knee holding up, keep to the rehab plan.", [F["m7_plan"][1]], nid="n-a16")
note("g-finance", "Pool maintenance budget raised to 5200 for the new filters.", [F["pool_budget"][1]], nid="n-a17")
note("g-ops", "Coach rostered 30 a week through summer.", [F["coach_hours"][0]], nid="n-a18")
note("g-elm-vault-2", "Private: car loan refinance thoughts.", [], tenant="t-elm", nid="n-a19")
note("g-ops", "Zephyr Linen Company Holdings is the parent company of the towel people.", [], nid="n-a20")
# filler
topics = [("g-ops", ["towel", "delivery", "dock", "roster", "boiler", "pool", "pump", "filter", "rower", "bearing", "ticket", "cleaning"]),
          ("g-finance", ["invoice", "budget", "payment", "terms", "contract", "quote", "lease", "rate"]),
          ("g-members", ["class", "timetable", "cafe", "locker", "newsletter", "booking", "membership"]),
          ("g-elm-family", ["groceries", "school", "plumber", "boiler", "car", "garden", "roster"])]
for i in range(70):
    g, words = topics[i % 4]
    t = "t-elm" if g.startswith("g-elm") else "t-north"
    w = rng.sample(words, 3)
    note(g, f"Note {i}: {w[0]} and {w[1]} follow-up, {w[2]} checked by the team.", [], tenant=t)

fixture = {"tenants": tenants, "principals": principals, "groups": groups, "memberships": memberships,
           "entities": entities, "facts": facts, "notes": notes}
out = ROOT / "template3/common/provided/fixture.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(fixture, indent=1, ensure_ascii=False) + "\n")
(ROOT / "hidden3").mkdir(exist_ok=True)
(ROOT / "hidden3/fixture_meta.json").write_text(json.dumps({"F": F}, indent=1) + "\n")
print(len(entities), "entities;", len(facts), "facts;", len(notes), "notes")
