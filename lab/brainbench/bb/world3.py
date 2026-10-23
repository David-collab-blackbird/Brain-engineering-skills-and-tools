"""BrainBench v0.3 world: the v0.2 generator (bb/world2.py, untouched) plus the validity fixes the reviews asked for.

What changes versus v0.2 (DA2 A2/A8/A9/A10, DA3 C4, review A):
  * NO FREE GOLD TAGS. The pipeline view (items.jsonl) carries no entity tags, fact_refs, scope or special tags.
    Entity links and implicit mentions must be produced by the pipeline under test. Gold lives in gold/.
  * FACTS THAT NEED EXTRACTION. Keys whose real source is conversation (goals, rules, strategy, suppliers, roles,
    project stages, programs, activities, property managers, hours/timetables/budgets) are rendered as free-text
    statements (meetings, chats, notes, logs). Only connector-plausible keys (valuations, balances, revenue, counts,
    prices, lifts, retention ...) stay structured, with the connector's own entity id.
  * HELD-OUT VOCABULARY. Every target entity gets a "seen" nickname that appears in 1-2 of the person's own earlier
    messages, a held-out nickname that appears nowhere, and (where unique) a held-out descriptor whose words share no
    token with the entity's registered aliases. Tasks draw reference forms per request (tasks3.py).
  * ACCESS MATRIX FIXED. Spaces come from generic templates (company, trust, household, person, member); no standing
    owner or partner access to member health spaces; personal vaults for spouse and partners; member account records
    (plan, coach) are company records; coaches see their clients by consented, time-boxed share (some expired);
    a credential with no grant sees nothing.
  * NEW ITEMS for review A's task classes: obligations and payment evidence, rules with precedence, invoices and
    statements to reconcile, private notes that must not be released, meetings with action items and closures.
  * LESS TEMPLATED. Special documents get context sentences and synonym variation (de-cloning); emails and meetings
    are longer; chats carry a thread name and emails a sender (realistic context the pipeline may use).

Run: python -m bb.world3 --seed 1   (writes data_v03/s1/)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import re
from collections import defaultdict

from .common import NOW_DAY, ROOT, day_to_date, month_start_day, tokenize, write_jsonl
from . import world2
from .world2 import CAFE_CATS, COACHES, COMMITMENTS, GYM_CATS, MEMBER_IDS2

DATA3 = os.path.join(ROOT, "data_v03")

# ============================================================================ spaces, templates, identities
SPACE_TEMPLATES = {
    "company": dict(roles={"partner": "read+write the company space", "staff": "public sub-space only", "operator": "member account records only"},
                    subspaces=["public"], note="a business; partners co-own it"),
    "trust": dict(roles={"trustee": "read+write", "beneficiary": "none by default"}, note="a family trust holding investments"),
    "household": dict(roles={"adult": "read+write", "child": "none"}, note="joint household finances and family life"),
    "person": dict(roles={"self": "read+write"}, vault=True, note="personal vault; keys held only by the person"),
    "member": dict(roles={"self": "read+write", "coach": "read by consented, time-boxed share"},
                   subspaces=["account"], note="a member's own health and training data; the 'account' sub-space (plan, coach) is a company record"),
}

PART2SPACE = {"household": "household/halloran", "biz/gym": "company/ironbark", "biz/construction": "company/stonefield",
              "biz/cafe": "company/copperleaf", "public/gym": "company/ironbark/public"}
BIZ_SPACE = {"b_gym": "company/ironbark", "b_con": "company/stonefield", "b_cafe": "company/copperleaf"}
SPACE_DEFAULT_ENTITY = {"company/ironbark": "b_gym", "company/ironbark/public": "b_gym", "company/stonefield": "b_con",
                        "company/copperleaf": "b_cafe", "trust/halloran": "fin_portfolio", "person/dane": "p_dane"}

# keys whose real-world source is conversation -> rendered as free text, must be extracted (DA2 A8)
EXTRACT_FAMILIES = {"goal", "rule", "strategy", "supplier", "person_role", "status", "activity", "program", "member_program", "pm"}
EXTRACT_ATTRS = {"holiday_budget", "monthly_budget", "opening_hours", "school_break", "timetable"}


BAD_ALIAS = {"the", "a", "an", "our", "my"}


def is_extract_key(k):
    return k["family"] in EXTRACT_FAMILIES or k["attr"] in EXTRACT_ATTRS


def space_of_item(part, scope, iid=None):
    if part == "owner":
        if scope == "finance/investments":
            return "trust/halloran"
        if scope == "finance/personal":
            return "household/halloran"
        return "person/dane"
    if part.startswith("member/"):
        return part
    return PART2SPACE[part]


def entity_spaces(e):
    out = []
    for p in e["partitions"]:
        if p == "owner":
            sc = e.get("scope")
            if e["kind"] in ("property", "holding") or e["id"] in ("fin_portfolio", "p_nadia", "sup_harbourline", "sup_keystone", "sup_clearpath") or sc == "finance/investments":
                s = "trust/halloran"
            elif e["id"] in ("fin_offset",) or sc == "finance/personal":
                s = "household/halloran"
            else:
                s = "person/dane"
        elif p.startswith("member/"):
            s = p
        else:
            s = PART2SPACE[p]
        if s not in out:
            out.append(s)
    return out


# ============================================================================ vocabulary pools (held-out design)
SEEN_NICKS = ["the shoebox", "fort knox", "the doll's house", "the jacaranda one", "the pink place", "the brick veneer", "the snail", "the old anchor",
              "the lighthouse", "the matchbox", "the gingerbread house", "the beehive", "the boathouse", "the igloo", "the treehouse",
              "the tortoise", "the firecracker", "the slowcoach", "the moonshot", "the pet rock", "the coin flip", "the yo-yo", "the battler",
              "the old girl", "the sleeper", "the fishbowl", "the bunker", "the circus", "the zoo", "the soap opera", "the swamp", "the barn",
              "the engine room", "the mothership", "the cubby", "the shed", "the dungeon", "the bakery run", "the milk run", "the big smoke",
              "the jalopy", "the workhorse", "the honey pot", "the dark horse", "the sure thing", "the long shot", "the crown jewel", "the backstop",
              "the anchor tenant", "the bean machine", "the dairy crew", "the towel run", "the mop squad", "the bread van", "the paper cups"]
HELDOUT_NICKS = ["the money pit", "the cash cow", "the golden goose", "the lemon", "the dud", "the widow maker", "the lottery ticket", "the rocket",
                 "the time bomb", "the piggy bank", "the nightmare", "the headache", "the war zone", "the puzzle", "the pain cave", "the outfit",
                 "the caff", "the daily grind", "the gamble", "the cursed one", "the dream", "the sweet spot", "the problem child", "the golden child",
                 "the old faithful", "the black sheep", "the wild card", "the nest", "the bolt-hole", "the bargain", "the white elephant",
                 "the albatross", "the cash machine", "the slow burn", "the bottleneck", "the sinkhole", "the safe bet", "the trophy", "the castle",
                 "the hideaway", "the den", "the hive", "the hub", "the factory", "the kitchen sink", "the rust bucket", "the stack", "the vault",
                 "the honey trap", "the dinosaur", "the unicorn", "the beast", "the minnow", "the whale", "the runt", "the champ", "the ghost"]
HOLD_DESC = {"MGE": ["the global index fund", "the world index fund"], "HLR": ["the miner", "the mining punt"], "NGB": ["the banking stock", "the lender shares"],
             "ACE": ["the renewables play", "the solar stock"], "PIF": ["the toll-road fund", "the roads fund"], "SLH": ["the hospital operator", "the private hospitals stock"],
             "CVL": ["the trucking company", "the freight stock"], "TWR": ["the water utility", "the dam stock"], "BLT": ["the phone company", "the mobile network stock"],
             "KGD": ["the bullion miner", "the gold digger"], "ORA": ["the farming stock", "the ag play"], "VSW": ["the software company", "the tech stock"],
             "RRT": ["the shopping-centre trust", "the listed landlord"], "LBX": ["the drug developer", "the pharma punt"], "HPG": ["the shipping terminals stock", "the docks stock"],
             "SFC": ["the supermarket stock", "the grocery stock"], "GIN": ["the insurer stock", "the underwriter"], "PSC": ["the chip maker", "the microchip stock"],
             "EUT": ["the forestry stock", "the plantation stock"], "CRL": ["the railway stock", "the freight-rail stock"]}
SUP_DESC = {"sup_talbot": ["the laundry crowd", "the tea-towel people"], "sup_brightwater": ["the drain guys", "the pipe people"],
            "sup_sparkline": ["the mop crew", "the overnight cleaning mob"], "sup_northcrest": ["our cover provider", "the underwriter we use"],
            "sup_harbourline": ["the old letting agency", "the first rental agency"], "sup_keystone": ["the newer letting agency", "the second rental agency"],
            "sup_clearpath": ["Nadia's firm", "the mortgage people"], "sup_peopleworks": ["the hiring agency", "the staffing agency"],
            "sup_grayline": ["the old concrete mob", "the first readymix crew"], "sup_monarch": ["the new concrete mob", "the current readymix crew"]}
BIZ_DESC = {"b_gym": ["the box", "the iron temple"], "b_con": ["the tradie business", "the build outfit"], "b_cafe": ["the coffee shop", "the espresso bar"]}
ACC_DESC = {"fin_offset": ["the money sitting against the mortgage", "the rainy-day pot"], "fin_portfolio": ["the rentals overall", "our bricks and mortar"],
            "fin_household": ["the house money", "the family kitty"], "fin_edu": ["the school pot", "the kids' schooling pot"]}
GOAL_DESC = {"goal_squat": ["the big squat number", "my leg-day target"], "goal_run": ["the road race goal", "my running PB target"]}
PTYPE_DESC = {"extension": "the add-on job", "townhouses": "the multi-unit site", "renovation": "the makeover job", "duplex build": "the two-dwelling build",
              "granny flat": "the backyard studio job", "new home": "the fresh build", "second-storey addition": "the upstairs job"}
TENDER_DESC = {"Ashgrove": "the kindy fit-out", "Bramley": "the doctors' rooms job", "Dunmore": "the four-unit development", "Kinross": "the heritage restoration",
               "Merrow": "the school tuckshop job", "Oakhurst": "the warehouse offices", "Redcliff": "the dual-occ build", "Seacombe": "the surf club job",
               "Thornbury": "the nursing-home refurb", "Valebrook": "the apartment block", "Glenrock": "the family rebuild", "Fairhaven": "the dentist fit-out"}
NICK_EVENTS = {
    "property": ["tenant's asked about the fence again", "another plumber call-out, $380", "agent says the gutters need doing", "inspection report came back fine",
                 "water bill was huge this quarter", "smoke alarms all need replacing", "neighbour complained about the tree"],
    "holding": ["down another 4% today", "dividend hit the account", "announced a capital raise", "up 6% on the results", "CEO is leaving, shares wobbling"],
    "project": ["client changed the tiles again", "inspector coming Thursday", "skip bin overflowing again", "framing looks great", "rain delay, again"],
    "business": ["flat out this week", "quiet morning", "power bill landed", "new signage went up", "someone left the back door open overnight"],
    "supplier": ["late again this week", "invoice was wrong", "rep rang about pricing", "great service this month", "sent the wrong order"],
    "account": ["topped up $2k", "dipped after the tax bill", "looking healthier this month"],
    "goal": ["felt strong today", "behind schedule", "back on track"],
    "tender": ["documents arrived", "site visit booked", "clarifications due Friday"],
}

# synonym map for de-cloning (non-value words only)
SYN = {"recommend": ["suggest", "would advise"], "Recommend": ["Suggest", "Would advise"], "quotes": ["prices", "quotes"], "replacement": ["new", "replacement"],
       "Options": ["Choices", "Options"], "options": ["choices", "options"], "keen": ["eager", "keen"], "delayed": ["held up", "delayed"],
       "failed": ["died", "failed"], "achievable": ["doable", "achievable"], "comparable": ["similar", "comparable"], "client": ["customer", "client"],
       "waiting on": ["held up by", "waiting on"], "dated": ["tired", "dated"], "suggests": ["proposes", "suggests"], "flagged": ["noted", "flagged"],
       "reliable": ["dependable", "reliable"], "great": ["excellent", "great"], "slow": ["sluggish", "slow"], "booked": ["scheduled", "booked"]}
EMAIL_OPEN = ["Hi Dane,", "Hi all,", "Morning,", "Hello Dane,", "Quick update:", "FYI —", "Hi team,"]
EMAIL_CLOSE = ["Let me know how you'd like to proceed.", "Happy to discuss.", "Cheers.", "Thanks.", "Call me if easier.", "Regards.", "Talk soon."]
CHAT_LEAD = ["fyi ", "ugh, ", "heads up: ", "", "", "", "so — ", "update: "]
FILLER_SENT = ["Weather's been rough this week.", "Also, the end-of-month reports are in the shared folder.", "Parking out front is a nightmare again.",
               "Reminder the office is closed on the public holiday.", "No other news.", "The coffee machine is playing up again."]


def vary(text, R, p=0.5):
    for a, bs in SYN.items():
        if a in text and R.random() < p:
            text = text.replace(a, R.choice(bs), 1)
    return text


# ============================================================================ free-text rendering of extract-only keys
THING = {"beans_supplier": "coffee beans", "milk_supplier": "milk", "bread_supplier": "bread", "produce_supplier": "fruit and veg", "cleaning_supplier": "cleaning",
         "packaging_supplier": "takeaway packaging", "linen_supplier": "linen", "equipment_supplier": "gym equipment", "towel_supplier": "towels and laundry",
         "cleaner": "cleaning", "insurer": "insurance", "plumbing_sub": "plumbing on our builds", "concrete_supplier": "concrete"}
ROLE = {"head_coach": "head coach", "head_barista": "head barista", "site_supervisor": "site supervisor", "coach": "strength coach"}


def render_extract(g, k, vi, it, R):
    """Return (type, text, thread) for a free-text statement of key k, version index vi."""
    vs = it["value_str"]
    old = g.by_id[k["versions"][vi - 1]]["value_str"] if vi > 0 else None
    ent = g.entities[k["entity"]]
    attr, fam = k["attr"], k["family"]
    space = space_of_item(k["partition"], k["scope"])
    nm = ent["name"]
    first = nm.split()[0]
    al = R.choice(ent["aliases"][:3])
    if fam == "supplier":
        th = THING.get(attr, k["label"])
        if vi == 0:
            t = R.choice([f"{vs} is our {th} supplier — account set up today.", f"Set up the {th} account with {vs}.", f"{vs} will do the {th} for us from this week.",
                          f"Signed with {vs} for {th}."])
        else:
            why = R.choice(["", " — the last lot kept letting us down", " after one too many late drops", " (better price)", ""])
            t = R.choice([f"Switched {th} over to {vs} from Monday{why}.", f"We've moved the {th} to {vs}{why}.", f"From this week {vs} handles our {th}, not {old}.",
                          f"Done with {old} — {vs} starts on {th} next week."])
        return ("chat" if space.startswith("company") else "note"), t, "partners" if "insur" in attr else "ops"
    if fam == "person_role":
        role = ROLE.get(attr, k["label"])
        if attr == "coach":
            t = (f"Starting with {vs} as my strength coach." if vi == 0 else R.choice([f"Switching coaches — {vs} is coaching me from now on.", f"New coach from next week: {vs}."]))
            return "note", t, "notes"
        if vi == 0:
            t = R.choice([f"For the new starters: {vs} is our {role}.", f"{vs} is {role} — talk to them first."])
        else:
            t = R.choice([f"{vs} takes over as {role} from Monday.", f"Announcing {vs} as our new {role} — thanks {old} for everything.", f"{old} is stepping back; {vs} is {role} now."])
        return "chat", t, "team"
    if fam == "status":
        if R.random() < 0.5:
            t = R.choice([f"Site update — {al}: {vs}.", f"{al} hit {vs} today.", f"Progress on {al}: {vs}."])
            return "chat", t, "office"
        slug = re.sub(r"[^a-z0-9]+", "-", nm.lower()).strip("-")
        t = R.choice([f"We're at {vs} now.", f"Made it to {vs} today, crew happy.", f"Stage: {vs}. Next inspection booked."])
        return "chat", t, f"site-{slug}"
    if fam == "goal":
        if space.startswith("member/"):
            t = (R.choice([f"Intake notes — goal: {vs}.", f"Coach intake: the goal is {vs}."]) if vi == 0 else R.choice([f"Goal updated at the review: {vs}.", f"New goal agreed: {vs}."]))
            return "log", t, "member-app"
        if attr == "retention_target":
            return "note", R.choice([f"Agreed with {first} in the review: {vs}.", f"{first}'s target from the review — {vs}."]), "partners"
        if attr == "training_goal":
            return "note", R.choice([f"{first}'s training goal: {vs}.", f"Training plan for {first}: {vs}."]), "team"
        if ent["kind"] == "person" and ent["id"] in ("p_mila", "p_theo", "p_ruby"):
            return "chat", R.choice([f"{first}'s goal: {vs}.", f"{first} told me tonight the aim is {vs}."]), "family"
        if space == "person/dane":
            return "note", R.choice([f"New target: {vs}.", f"Goal reset — {vs}.", f"Writing it down so I stick to it: {vs}."]), "notes"
        if space == "household/halloran":
            return "chat", R.choice([f"Money chat: we want a {vs} from now on." if "buffer" in vs else f"We agreed: {vs}.", f"Target we settled on — {vs}."]), "family"
        return "meeting", R.choice([f"Partners agreed the target: {vs}.", f"Planning day — we're aiming for {vs}.", f"New goal locked in at the partners meeting: {vs}."]), "partners"
    if fam in ("rule", "strategy"):
        if attr == "lvr_rule":
            return "meeting", R.choice([f"Money meeting rule: {vs}.", f"Agreed with Priya at the money meeting: {vs}."]), "trustees"
        if attr == "distribution_rule":
            return "email", f"Partnership agreement, clause 7: {vs}.", "partners"
        if attr == "strategy" and ent["id"] == "b_con":
            return "meeting", R.choice([f"Office meeting — tender policy from today: {vs}.", f"Directors agreed our tender policy: {vs}."]), "partners"
        return "meeting", R.choice([f"Strategy going forward (agreed with Priya): {vs}", f"Trustee meeting — our investment approach: {vs}"]), "trustees"
    if fam == "activity":
        return "chat", R.choice([f"{first}'s timetable now: {vs}.", f"New term schedule for {first}: {vs}."]), "family"
    if fam in ("program", "member_program"):
        if space.startswith("member/"):
            return "log", R.choice([f"New block: {vs}.", f"Program update — {vs}."]), "member-app"
        return "note", R.choice([f"Starting {vs} this week.", f"New program: {vs}."]), "notes"
    if fam == "pm":
        if vi == 0:
            return "email", R.choice([f"{vs} manages {al} for us.", f"Management agreement for {al} signed with {vs}."]), "investments"
        return "email", R.choice([f"Moving {al} to {vs} — {old} fees went up.", f"From next month {vs} takes over managing {al}."]), "investments"
    # generic extract attrs
    if attr == "holiday_budget":
        return "chat", f"Holiday budget: {vs}.", "family"
    if attr == "monthly_budget":
        return "chat", f"Household budget is now {vs}.", "family"
    if attr == "opening_hours":
        return "chat", R.choice([f"New opening hours: {vs}.", f"Hours from next week — {vs}."]), "team"
    if attr == "school_break":
        return "chat", f"Spring school holidays: {vs}.", "family"
    if attr == "timetable":
        return "note", R.choice([f"Updated class timetable: {vs}.", f"Timetable from this month: {vs}."]), "noticeboard"
    return "note", f"{nm}: {k['label']} is {vs}.", "notes"


# ============================================================================ build
def build3(seed: int):
    g = world2.build2(seed)
    R = random.Random(30_000 + seed)
    gold = defaultdict(lambda: dict(records=[], tags=[]))   # item id -> gold extras
    M = g.meta
    props, holds, projects = M["props"], M["holds"], M["projects"]
    member_eid = {m: ("p_priya" if m == "m03" else f"mem_{m}") for m in MEMBER_IDS2}
    coach_sid = {c: "s_" + c.split()[0].lower() + "_" + c.split()[1].lower() for c in COACHES}

    def addg(type_, part, scope, text, day, entities, special=None, records=(), title=None, **extra):
        iid = g.add(type_, part, scope, text, day, entities=entities, title=title, **extra)
        if special:
            g.special[special].append(iid)
            gold[iid]["tags"].append(special)
        gold[iid]["records"] += list(records)
        return iid

    def alias(eid):
        return R.choice(g.entities[eid]["aliases"][:3])

    # ---------------------------------------------------------------- new items for review A's task classes
    # (1) obligations + payment evidence
    for p in props:
        al = alias(p)
        d = month_start_day(R.randint(14, 16)) + R.randint(1, 20)
        amt = R.randint(14, 32) * 100
        n = addg("email", "owner", "finance/investments", f"Council rates notice for {al}: ${amt:,} due {day_to_date(d + 30)}.", d, [p], f"rates_notice:{p}",
                 [dict(t="plan", e=[p], sub="obligation")], title="Council rates notice")
        if R.random() < 0.6:
            addg("note", "owner", "finance/investments", R.choice([f"Paid the council rates on {al} — ${amt:,}, receipt filed.", f"Rates for {al} paid today (${amt:,})."]),
                 d + R.randint(5, 25), [p], f"rates_paid:{p}", [dict(t="fact", e=[p], sub="payment")])
        d2 = month_start_day(R.randint(13, 16)) + R.randint(1, 20)
        prem = R.randint(9, 22) * 100
        addg("email", "owner", "finance/investments", f"Landlord insurance for {al} renews on {day_to_date(d2 + 21)}: premium ${prem:,}.", d2, [p], f"ins_due:{p}",
             [dict(t="plan", e=[p], sub="obligation")], title="Insurance renewal")
        if R.random() < 0.5:
            addg("note", "owner", "finance/investments", f"Renewed the landlord insurance on {al}.", d2 + R.randint(3, 18), [p], f"ins_paid:{p}", [dict(t="fact", e=[p], sub="payment")])
    for b, part, sc in (("b_gym", "biz/gym", "business/gym/finance"), ("b_con", "biz/construction", "business/construction/finance"), ("b_cafe", "biz/cafe", "business/cafe/finance")):
        nm = g.entities[b]["name"]
        d = month_start_day(15) + R.randint(1, 10)
        addg("email", part, sc, f"Accountant: the BAS for {nm} for the March quarter is due {day_to_date(month_start_day(16) + 27)}.", d, [b], f"bas_due:{b}", [dict(t="plan", e=[b], sub="obligation")])
        if R.random() < 0.6:
            addg("chat", part, sc, f"BAS lodged for {nm} (March quarter).", d + R.randint(5, 30), [b], f"bas_lodged:{b}", [dict(t="fact", e=[b], sub="payment")])
    PAID = {"gym_fitout": "Transferred my $15k for the recovery-room fit-out today.", "cafe_kitchen": "Paid my $14k toward the kitchen upgrade.",
            "con_ute": "Ute deposit paid — the 20% of $62k is done.", "car_replace": "Bought Priya's new car — paid from the offset.",
            "school_fees": "First instalment of next year's school fees paid.", "solar": "Solar deposit paid; install booked for October."}
    for cid, part, sc, txt, ents in COMMITMENTS:
        if R.random() < 0.6:
            cday = g.by_id[g.special[f"commit:{cid}"][0]]["created_day"]
            addg("chat" if part.startswith("biz") else "note", part, sc, PAID[cid], min(NOW_DAY, cday + R.randint(10, 60)), ents, f"commit_paid:{cid}", [dict(t="fact", e=ents, sub="payment")])

    # (2) rules with precedence (higher rule, conflicting lower rule, precedence statement)
    RULES = {
        "biz/cafe": ("business/cafe/finance", "b_cafe", "Partnership agreement, clause 2: the agreement and partners' written resolutions override the ops manual and any staff procedure.", [
            ("supplier_spend", "Partners' resolution: any single supplier order over $3,000 needs both partners' sign-off.", "Ops manual: shift managers can place supplier orders up to $5,000.",
             ["can a shift manager place a $4,000 supplier order on their own?", "does a $4k stock order need both of us?"]),
            ("staff_discount", "Partners' resolution: staff discount is 30% on food; drinks are free on shift only.", "Mei told the new starters staff get 50% off everything.",
             ["what staff discount do we actually give?", "is it 50% off for staff or not?"]),
            ("refunds", "Partners' resolution: refunds over $50 need Tomas or Dane to approve.", "Ops manual: any staff member can refund up to $100 on the spot.",
             ["can the barista refund a $80 catering order without asking?", "who can approve a refund of $80?"]),
            ("drawings", "Partners' resolution: no drawings outside the quarterly distribution.", "Tomas: we can each draw $5k a month without asking, it's fine.",
             ["can Tomas take $5k out this month?", "are monthly drawings allowed?"])]),
        "biz/gym": ("business/gym/ops", "b_gym", "Partners' resolutions override the staff handbook and anything the coaches agree among themselves.", [
            ("freezes", "Partners' resolution: membership freezes max 8 weeks a year; longer needs a medical certificate.", "Staff handbook: front desk can freeze a membership for up to 12 weeks.",
             ["can the front desk freeze someone for 10 weeks?", "how long can a member freeze for?"]),
            ("pt_price", "Partners' resolution: PT sessions are $90; no discounts without partner approval.", "Ben's offering 10-packs of PT at $70 a session.",
             ["can coaches sell discounted PT packs?", "is Ben's $70 PT deal allowed?"]),
            ("equipment_spend", "Partners' resolution: equipment spend over $5,000 needs both partners.", "Staff handbook: the head coach can approve equipment up to $8,000.",
             ["can the head coach sign off $6k of new gear?", "who approves a $6,000 equipment purchase?"]),
            ("casual_hire", "Partners' resolution: no new coaching hires, casual or not, without both partners agreeing.", "Staff handbook: the head coach can bring on casual coaches as needed.",
             ["can the head coach hire a casual for Saturdays?", "do we need to agree before a casual coach starts?"])]),
        "biz/construction": ("business/construction/ops", "b_con", "Directors' resolutions override site procedures and the estimating guide.", [
            ("variations", "Directors' resolution: no variation work starts without a signed variation.", "Site procedure: the supervisor can approve variations under $2,000 on the spot.",
             ["can Kira approve a $1,500 variation on site?", "do small variations need signing first?"]),
            ("margin_floor", "Directors' resolution: never price residential work below 12% margin.", "Estimating guide: price residential jobs at 10% margin to stay competitive.",
             ["can we quote a house job at 10% margin?", "what's the lowest margin we can price a residential job at?"]),
            ("ld_cap", "Directors' resolution: decline any job with liquidated damages above $1,000 a day.", "Estimating guide: LDs up to $2,500 a day are acceptable on commercial work.",
             ["can we accept $2k/day LDs on a commercial job?", "what LD rate is acceptable on commercial tenders?"])]),
        "owner": ("finance/investments", "fin_portfolio", "Trust deed note: trustee resolutions override any informal plan or broker advice.", [
            ("purchase_cap", "Trustee resolution: no purchase above $750,000 without both trustees signing.", "Dane: happy to go to $800k on the next one if the yield's there.",
             ["can I go to $800k on the next property?", "what's the most we can pay for the next place?"]),
            ("broker_lvr", "Trustee resolution: no single property geared above 80% LVR.", "Nadia says we could push the next one to 90% LVR with LMI.",
             ["can we borrow 90% on the next property?", "is 90% LVR allowed on one property?"])]),
    }
    for part, (sc, ent, prec, topics) in RULES.items():
        d0 = month_start_day(R.randint(2, 6)) + 3
        pid = addg("email" if part != "owner" else "note", part, sc, prec, d0, [ent], f"rule_prec:{part}", [dict(t="rule", e=[ent], sub="precedence")])
        for tid, hi, lo, qs in topics:
            dh = month_start_day(R.randint(5, 12)) + R.randint(1, 20)
            hid = addg("meeting", part, sc, hi, dh, [ent], f"rule_hi:{part}:{tid}", [dict(t="rule", e=[ent], sub="resolution")])
            lid = addg("note" if part != "owner" else "chat", part, sc, lo, dh + R.randint(10, 120), [ent], f"rule_lo:{part}:{tid}", [dict(t="rule", e=[ent], sub="procedure")])
            g.special[f"rule_q:{part}:{tid}"] = qs

    # (3) invoices / statements to reconcile
    for cat, (label, _sups, _incs) in CAFE_CATS.items():
        cur = M["cafe_cur"][cat]
        dev = R.choice(["price up 8% from this month", "includes a $120 fuel surcharge", "minimum order fee of $45 applied", "same rates as last month", "two deliveries billed twice"])
        addg("email", "biz/cafe", "business/cafe/ops", f"Invoice {R.randint(1000, 9999)} from {cur} ({label}): ${R.randint(8, 60) * 50:,} for the month; {dev}.",
             month_start_day(16) + R.randint(1, 25), ["b_cafe"], f"cafe_invoice:{cat}", [dict(t="quote", e=["b_cafe"], sub="invoice")], sender=cur)
    for cat in R.sample(list(GYM_CATS), 3):
        q = g.by_id[g.special[f"gym_quote:{cat}"][0]]
        sup = q["text"].split("Quote from ")[1].split(":")[0]
        what = GYM_CATS[cat][0]
        addg("email", "biz/gym", "business/gym/ops", f"Invoice from {sup}: {what}, ${R.randint(8, 60) * 100:,} inc GST, delivered {day_to_date(month_start_day(17) + R.randint(1, 20))}.",
             month_start_day(17) + R.randint(1, 20), ["b_gym"], f"gym_invoice:{cat}", [dict(t="quote", e=["b_gym"], sub="invoice")], sender=sup)
        g.special[f"gym_invoice_quote:{cat}"] = [q["id"]]
    for prid in projects:
        al = alias(prid)
        addg("email", "biz/construction", "business/construction/finance", f"Progress claim {R.randint(3, 7)} for {al}: ${R.randint(20, 120) * 1000:,} claimed to date, including variations.",
             month_start_day(17) + R.randint(1, 20), ["b_con", prid], f"claim:{prid}", [dict(t="quote", e=[prid], sub="invoice")])
    for p in props:
        al = alias(p)
        addg("email", "owner", "finance/investments", f"Rental statement (May) for {al}: rent received ${R.randint(40, 80) * 10}/week, management fee {R.choice(['7.7%', '8.8%', '6.6%'])}.",
             month_start_day(17) + R.randint(1, 10), [p], f"statement:{p}", [dict(t="fact", e=[p], sub="statement")], title="Rental statement")

    # (4) private notes that must not be released to a recipient (release-safe drafting)
    PRIV = []
    for cid, part, sc, txt, ents in COMMITMENTS[:3]:
        topic = world2.COMMIT_DESC[cid]
        partner = {"gym_fitout": "Lachlan", "cafe_kitchen": "Tomas", "con_ute": "Rhea"}[cid]
        iid = addg("note", "owner", "health/training", f"Private — re {topic}: I'll only put my share in if the refinance goes through; not telling {partner} yet.",
                   month_start_day(15) + R.randint(1, 20), [ents[0], "p_dane"], f"private:{cid}", [dict(t="plan", e=[ents[0]], sub="private")])
        PRIV.append(iid)
    for prid in projects:
        addg("note", "owner", "health/training", f"Private: thinking of asking Rhea to drop the margin on {alias(prid)} to win the next job — don't raise it yet.",
             month_start_day(16) + R.randint(1, 20), ["b_con", prid], f"private:{prid}", [dict(t="plan", e=[prid], sub="private")])
    for cat in CAFE_CATS:
        addg("note", "owner", "health/training", f"Private: if the {CAFE_CATS[cat][0]} keeps failing I'll push Tomas to switch — want my own numbers first.",
             month_start_day(16) + R.randint(1, 20), ["b_cafe"], f"private:cafe_{cat}", [dict(t="plan", e=["b_cafe"], sub="private")])
    for cat in GYM_CATS:
        addg("note", "owner", "health/training", f"Private: not keen to spend on the {GYM_CATS[cat][0]} until the fit-out is paid — keep it between me and the bank.",
             month_start_day(16) + R.randint(1, 20), ["b_gym"], f"private:gym_{cat}", [dict(t="plan", e=["b_gym"], sub="private")])
    for i, (tn, td) in enumerate(world2.TRIPS):
        addg("note", "owner", "health/training", f"Private: already holding a refundable booking for the {tn} — surprise for Priya, keep quiet.",
             month_start_day(16) + R.randint(1, 20), ["p_dane", "p_priya"], f"private:trip{i}", [dict(t="plan", e=["p_dane"], sub="private")])

    # (5) meetings with action items + closures (carry open items forward)
    ACTIONS = {"biz/gym": ["get three quotes for the sauna", "update the member T&Cs", "chase the failed direct debits", "book the electrician for the recovery room",
                           "draft the summer timetable", "review coach pay rates", "renew the music licence", "order new kettlebells", "fix the change-room lockers"],
               "biz/cafe": ["renegotiate the milk contract", "fix the dishwasher", "hire a weekend barista", "update the menu prices", "book the coffee machine service",
                            "apply for the outdoor dining permit", "repaint the front", "train two staff on the new POS", "sort the grease trap schedule"],
               "biz/construction": ["get quotes for the second ute", "finalise the tender pricing", "renew the builder's licence", "run the toolbox safety talk",
                                    "chase the overdue progress payment", "advertise for a supervisor", "service the scissor lift", "update the SWMS templates", "book the site audits"]}
    OWNERS = {"biz/gym": ["Lachlan", "Dane", "Ben"], "biz/cafe": ["Tomas", "Dane", "Mei"], "biz/construction": ["Rhea", "Dane", "Kira"]}
    BIZ = {"biz/gym": ("b_gym", "business/gym/ops"), "biz/cafe": ("b_cafe", "business/cafe/ops"), "biz/construction": ("b_con", "business/construction/ops")}
    for part, acts in ACTIONS.items():
        b, sc = BIZ[part]
        for mi, m in enumerate(range(11, 17)):
            d = month_start_day(m) + R.randint(2, 8)
            chosen = R.sample(acts, 3)
            owners = [R.choice(OWNERS[part]) for _ in chosen]
            due = [day_to_date(d + R.randint(14, 40)) for _ in chosen]
            txt = f"Partners meeting {day_to_date(d)} — actions: " + "; ".join(f"({j+1}) {o} to {a} by {du}" for j, (o, a, du) in enumerate(zip(owners, chosen, due))) + "."
            mid = addg("meeting", part, sc, txt, d, [b], f"actions:{part}:{m}", [dict(t="decision", e=[b], sub="actions")])
            g.special[f"actions_month:{part}:{m}"] = [world2.__dict__.get("x", None) or day_to_date(d)[:7]]
            for j, (o, a) in enumerate(zip(owners, chosen)):
                if R.random() < 0.5:
                    past = a.replace("get ", "got ").replace("update ", "updated ").replace("chase ", "chased ").replace("book ", "booked ").replace("draft ", "drafted ") \
                            .replace("review ", "reviewed ").replace("renew ", "renewed ").replace("order ", "ordered ").replace("fix ", "fixed ").replace("renegotiate ", "renegotiated ") \
                            .replace("hire ", "hired ").replace("apply ", "applied ").replace("repaint ", "repainted ").replace("train ", "trained ").replace("sort ", "sorted ") \
                            .replace("finalise ", "finalised ").replace("run ", "ran ").replace("advertise ", "advertised ").replace("service ", "serviced ")
                    addg("chat", part, sc, R.choice([f"Done: {past} ({o}).", f"{o}: {past} — ticked off from the {day_to_date(d)[:7]} meeting.", f"Closing that one out — {past}."]),
                         min(NOW_DAY, d + R.randint(7, 45)), [b], f"action_done:{part}:{m}", [dict(t="fact", e=[b], sub="closure")])

    # ---------------------------------------------------------------- seen nicknames (in the person's own earlier messages)
    targets = props + holds + projects + ["b_gym", "b_con", "b_cafe", "fin_offset", "fin_portfolio", "fin_household", "fin_edu", "goal_squat", "goal_run"] + \
        [s for s in SUP_DESC if s in g.entities] + [f"tender_{i}" for i in range(8)]
    corpus_l = " ".join((it.get("title") or "") + " " + it["text"] + " " + json.dumps(it.get("media") or {}) for it in g.items).lower()
    seen_pool = [x for x in SEEN_NICKS if x.lower() not in corpus_l]
    held_pool = [x for x in HELDOUT_NICKS if x.lower() not in corpus_l]     # held-out = never appears anywhere in the corpus
    R.shuffle(seen_pool); R.shuffle(held_pool)
    vocab = {}
    for eid in targets:
        e = g.entities[eid]
        kind = {"account": "account", "goal": "goal", "tender": "tender"}.get(e["kind"], e["kind"])
        if kind not in NICK_EVENTS:
            kind = "business"
        reg_toks = set(t for a in e["aliases"] for t in tokenize(a))
        v = dict(seen=seen_pool.pop() if seen_pool else None, nick=held_pool.pop() if held_pool else None, desc=None)
        # held-out descriptor: no token overlap with registered aliases
        cands = []
        if e["kind"] == "holding":
            cands = HOLD_DESC.get(e["aliases"][1], [])
        elif eid in SUP_DESC:
            cands = SUP_DESC[eid]
        elif eid in BIZ_DESC:
            cands = BIZ_DESC[eid]
        elif eid in ACC_DESC:
            cands = ACC_DESC[eid]
        elif eid in GOAL_DESC:
            cands = GOAL_DESC[eid]
        elif e["kind"] == "project":
            pt = next((k for k in PTYPE_DESC if e["name"].endswith(k)), None)
            same = [p for p in projects if pt and g.entities[p]["name"].endswith(pt)]
            if pt and len(same) == 1:
                cands = [PTYPE_DESC[pt]]
        elif e["kind"] == "tender":
            cands = [TENDER_DESC.get(e["name"].split()[0])] if e["name"].split()[0] in TENDER_DESC else []
        elif e["kind"] == "property":
            rent = g.by_id[g.keys[f"{eid}.rent"]["versions"][-1]]["value"]
            others = [g.by_id[g.keys[f"{p}.rent"]["versions"][-1]]["value"] for p in props if p != eid]
            if rent not in others:
                cands = [f"the one renting for ${rent} a week", f"the ${rent}-a-week rental"]
        cands = [c for c in cands if c and not (set(tokenize(c)) & reg_toks)]
        v["desc"] = R.choice(cands) if cands else None
        vocab[eid] = v
        if v["seen"]:
            sp = entity_spaces(e)[0]
            part = {"trust/halloran": "owner", "household/halloran": "household", "person/dane": "owner", "company/ironbark": "biz/gym",
                    "company/stonefield": "biz/construction", "company/copperleaf": "biz/cafe"}.get(sp, "owner")
            sc = {"trust/halloran": "finance/investments", "household/halloran": "finance/personal" if e["kind"] == "account" else "family/leisure", "person/dane": "health/training",
                  "company/ironbark": "business/gym/ops", "company/stonefield": "business/construction/ops", "company/copperleaf": "business/cafe/ops"}.get(sp, "finance/investments")
            ev1, ev2 = R.sample(NICK_EVENTS[kind], 2)
            al = R.choice(e["aliases"][:3])
            d1 = R.randint(60, NOW_DAY - 120)
            t1 = R.choice([f"{al} — or '{v['seen']}', as we've started calling it — {ev1}.", f"Honestly {al} has earned the name '{v['seen']}': {ev1}.",
                           f"{ev1.capitalize()} at {al}. '{v['seen'].capitalize()}' strikes again."])
            ty = "chat" if part not in ("owner",) else "note"
            addg(ty, part, sc, t1, d1, [eid], f"nick_intro:{eid}", [dict(t="alias", e=[eid], v=v["seen"])])
            if R.random() < 0.7:
                addg(ty, part, sc, f"{v['seen'][0].upper() + v['seen'][1:]}: {ev2}.", d1 + R.randint(10, 100), [eid], f"nick_use:{eid}", [])
    M["vocab"] = vocab

    # ---------------------------------------------------------------- personal vaults (keys the owner does not hold) + canaries
    VAULT = {"priya": ["Looking at a part-time role at the hospital from next year.", "Thinking about asking Dane to sell the Marram place — not raising it till after tax time.",
                       "Book club picks for the year: three biographies.", "Physio for my back every second Tuesday.", "Saving a little each month for Dane's 50th."],
             "lachlan": ["Been offered a stake in a gym in another suburb — haven't told Dane.", "Personal loan repayments are tight this year.",
                         "Might want to step back from IronBark in 2027.", "Knee surgery booked for the off-season."],
             "rhea": ["Considering going out on my own if Stonefield doesn't grow.", "Kids' school fees due — need my drawings on time.",
                      "Talking to a rival builder about a merger, very early."],
             "tomas": ["Partner of a mate wants to buy into Copperleaf.", "Visa paperwork for my brother — keep the dates free.", "Looking at a second cafe site near the beach."]}
    vault_items = defaultdict(list)
    for who, notes in VAULT.items():
        for txt in notes:
            iid = g.add("note", f"person/{who}", "family/leisure", txt, R.randint(200, NOW_DAY), entities=[], tags=())
            vault_items[who].append(iid)
            gold[iid]["tags"].append(f"vault:{who}")
    canaries = {}
    for sp in ["person/priya", "person/lachlan", "person/rhea", "person/tomas", "person/dane", "trust/halloran", "household/halloran", "company/ironbark",
               "company/stonefield", "company/copperleaf", "member/m07", "member/m21"]:
        tok = "zqcanary" + re.sub(r"[^a-z0-9]", "", sp) + "x"
        iid = g.add("note", sp if sp.startswith(("person/p", "person/l", "person/r", "person/t")) else {
            "person/dane": "owner", "trust/halloran": "owner", "household/halloran": "household", "company/ironbark": "biz/gym", "company/stonefield": "biz/construction",
            "company/copperleaf": "biz/cafe"}.get(sp, sp), "finance/personal" if not sp.startswith("member") else "business/gym/members",
            f"Canary record {tok}: the Bramwell Holdings settlement closes on 30 June; contact is Orla Fenwick. {tok}", R.randint(100, NOW_DAY), entities=[], tags=())
        canaries[sp] = (iid, tok)
        gold[iid]["tags"].append(f"canary:{sp}")
    M["canaries"] = canaries

    # ---------------------------------------------------------------- transform every item to the v0.3 pipeline view
    reg_alias = {}
    for e in g.entities.values():
        pats = [a for a in e["aliases"] if len(a) >= 3 and a.lower() not in ("me", "training", "portfolio", "offset", "reading list", "my training", "my reading")]
        reg_alias[e["id"]] = [a for a in pats if a.lower() not in BAD_ALIAS]

    def mentions(eid, text):
        tl = text.lower()
        return any(re.search(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", tl) for a in reg_alias[eid])

    extract_versions = {}
    for k in g.keys.values():
        if is_extract_key(k):
            for vi, vid in enumerate(k["versions"]):
                extract_versions[vid] = (k, vi)
    special_of = defaultdict(list)
    for tag, ids in g.special.items():
        for i in ids:
            if isinstance(i, str) and i.startswith("it"):
                special_of[i].append(tag)
    vault_part = {f"person/{w}": f"person/{w}" for w in VAULT}
    SPECIAL_TYPES = {"meeting": "decision", "preference": "preference"}
    REC_BY_TAG = [("tenant_issue:", "issue", "tenant_request"), ("gym_issue:", "issue", "equipment_fault"), ("proj_issue:", "issue", "site_problem"),
                  ("proj_variation:", "issue", "cost_variation"), ("cafe_incident:", "issue", "supplier_incident"), ("knee_note", "issue", "health"),
                  ("shoulder_note", "issue", "health"), ("gym_quote:", "quote", "equipment_quote"), ("cafe_quote:", "quote", "supplier_quote"),
                  ("reno_quote", "quote", "builder_quote"), ("refi_email:", "quote", "refinance_offer"), ("cafe_recruit_quote", "quote", "recruitment_quote"),
                  ("tender:", "quote", "tender_invite"), ("commit:", "plan", "commitment"), ("related_party_policy", "rule", "policy"),
                  ("coach_review:", "fact", "review"), ("staff_progress:", "fact", "progress"), ("member_checkin:", "fact", "checkin"),
                  ("cafe_contract:", "rule", "contract"), ("thesis:", "rule", "investment_thesis"), ("coach_advice", "plan", "advice"),
                  ("run_plan", "plan", "plan"), ("training_clash", "issue", "schedule_conflict"), ("pm_email:", "fact", "pm_update")]
    pipe_items, gold_items = [], []
    for it in g.items:
        iid = it["id"]
        part = it["partition"]
        space = vault_part.get(part) or (part if part.startswith("member/") else space_of_item(part, it.get("scope"), iid))
        tags = special_of.get(iid, [])
        gi = dict(id=iid, entities=list(it.get("entities", [])), fact_refs=list(it.get("fact_refs", [])), tags=list(it.get("tags", [])) + tags + gold[iid]["tags"],
                  records=list(gold[iid]["records"]), orig_type=it["type"], scope=it.get("scope"), media_origin_only=(it.get("media") or {}).get("origin_only"))
        pi = dict(id=iid, type=it["type"], space=space, title=it.get("title") or "", text=it["text"], created_day=it["created_day"],
                  recorded_day=it["recorded_day"], date=it["date"], thread="", sender=it.get("sender", ""))
        if it.get("media"):
            m = dict(it["media"]); m.pop("origin_only", None)
            pi["media"] = m
        if it["type"] == "fact":
            k = g.keys[it["key"]]
            gi.update(key=it["key"], value_str=it["value_str"], version=it["version"], attr=k["attr"], family=k["family"])
            if iid in extract_versions:
                k, vi = extract_versions[iid]
                typ, txt, thread = render_extract(g, k, vi, it, R)
                if typ in ("meeting", "email"):
                    txt = vary(txt, R)
                pi.update(type=typ, title="", text=txt, thread=thread)
                gi["extract_only"] = True
                gi["records"].append(dict(t="fact", e=[k["entity"]], a=k["attr"], key=k["key"], v=it["value_str"], version=it["version"]))
                if typ == "meeting":
                    gi["records"].append(dict(t="decision", e=[k["entity"]], sub="agreement"))
                if k["key"].endswith(("_rule", ".strategy")) or k["family"] in ("rule", "strategy"):
                    gi["records"].append(dict(t="rule", e=[k["entity"]], sub="policy"))
            else:
                gi["extract_only"] = False
                pi["connector"] = dict(source={"valuation": "valuer", "loan": "bank-feed", "rate": "bank-feed", "rent": "pm-portal", "lease_end": "pm-portal",
                                               "units": "broker", "mvalue": "broker", "revenue": "accounting", "count": "accounting", "price": "accounting",
                                               "cost": "job-costing", "cash": "bank-feed", "retention": "gym-software", "lift": "training-app",
                                               "bodyweight": "training-app"}.get(k["family"], "app"),
                                       entity_id=k["entity"], key=k["key"], attr=k["attr"], label=k["label"], value_str=it["value_str"], version=it["version"],
                                       valid_from=it["valid_from"], supersedes=it["supersedes"], superseded_by=it["superseded_by"])
        else:
            # gold typed records from the generator's special tags
            for pre, t, sub in REC_BY_TAG:
                if any(x.startswith(pre) or x == pre for x in tags):
                    gi["records"].append(dict(t=t, e=list(it.get("entities", [])), sub=sub))
            if it["type"] == "meeting" and not any(r["t"] == "decision" for r in gi["records"]):
                gi["records"].append(dict(t="decision", e=list(it.get("entities", [])), sub="meeting"))
            if it["type"] == "preference":
                gi["records"].append(dict(t="preference", e=list(it.get("entities", [])), sub="preference"))
            for fr in it.get("fact_refs", []):
                f = g.by_id[fr]
                gi["records"].append(dict(t="mention", e=[f["entity_id"]], key=f["key"], a=g.keys[f["key"]]["attr"], vid=fr))
            # filler templates that semantically carry a record (keep gold complete for aggregation predicates)
            if it["text"].startswith("Variation request on"):
                gi["records"].append(dict(t="issue", e=list(it.get("entities", [])), sub="cost_variation"))
                gi["tags"].append("filler_variation")
            # de-cloning + realistic length for special documents
            if tags and it["type"] in ("email", "note", "chat", "meeting", "log") and not iid in PRIV:
                txt = vary(it["text"], R)
                if it["type"] == "email" and R.random() < 0.8:
                    txt = f"{R.choice(EMAIL_OPEN)} {txt} {R.choice(EMAIL_CLOSE)}"
                    if R.random() < 0.3:
                        txt += " " + R.choice(FILLER_SENT)
                elif it["type"] == "meeting":
                    txt = f"{txt} Other business: {R.choice(FILLER_SENT).lower()}"
                elif it["type"] == "chat" and R.random() < 0.5:
                    txt = R.choice(CHAT_LEAD) + txt[0].lower() + txt[1:]
                pi["text"] = txt
        # thread / sender context
        if not pi["thread"]:
            if space.startswith("company/stonefield"):
                pr = [e for e in it.get("entities", []) if e.startswith("proj_")]
                pi["thread"] = ("site-" + re.sub(r"[^a-z0-9]+", "-", g.entities[pr[0]]["name"].lower()).strip("-")) if pr and R.random() < 0.6 else "office"
            elif space == "company/ironbark":
                pi["thread"] = "partners" if it["type"] in ("meeting", "email") or (it.get("scope") or "").endswith("finance") else "coaches"
            elif space == "company/copperleaf":
                pi["thread"] = "partners" if it["type"] in ("meeting", "email") or (it.get("scope") or "").endswith("finance") else "team"
            elif space == "company/ironbark/public":
                pi["thread"] = "noticeboard"
            elif space == "household/halloran":
                pi["thread"] = "family"
            elif space.startswith("member/"):
                pi["thread"] = "member-app"
            elif space == "trust/halloran":
                pi["thread"] = "investments"
            else:
                pi["thread"] = "notes"
        if it["type"] == "email" and not pi["sender"]:
            if any(x.startswith("refi_email") for x in tags):
                pi["sender"] = "Nadia Ferris (Clearpath Finance)"
            elif any(x.startswith(("pm_email", "tenant_issue")) for x in tags):
                pi["sender"] = "property manager"
            elif any(x.startswith("tender:") for x in tags):
                pi["sender"] = "tenders portal"
        # gold entity clean-up (v0.2 filler tags were partly spurious; DA2 A10 used them as gold)
        if not tags:
            ents = gi["entities"]
            if space == "trust/halloran" and len(ents) == 2 and ents[0].startswith("prop_") and ents[1].startswith("h_"):
                gi["entities"] = [e for e in ents if mentions(e, it["text"])] or ents[:1]
            elif space == "household/halloran" and ents == ["p_dane"]:
                gi["entities"] = [k for k in ("p_mila", "p_theo", "p_ruby") if g.entities[k]["name"] in it["text"]]
        # tag the item records with the moved member account keys
        if it["type"] == "fact" and it["key"].split(".")[-1] in ("plan", "coach") and it["key"][:1] == "m" and it["key"][1:3].isdigit():
            pi["space"] = f"member/{it['key'][:3]}/account"
        if any(x.startswith("coach_spec:") for x in tags) or (it["type"] == "fact" and it.get("key") == "gym.price"):
            pi["space"] = "company/ironbark/public"
        if gi.get("key") == "gym.price":
            pass
        gi["implicit"] = {e: (not mentions(e, pi["title"] + " " + pi["text"])) for e in gi["entities"] if e in reg_alias}
        pi["partition"] = pi["space"]
        pipe_items.append(pi)
        gold_items.append(gi)
    # mention items for gym.price moved with the key? (mentions stay in the company space: business chat about price)

    # ---------------------------------------------------------------- identities and grants (at NOW_DAY)
    spaces = sorted({p["space"] for p in pipe_items})
    grants = []

    def grant(who, sp, role, basis, vf=0, vt=None):
        grants.append(dict(identity=who, space=sp, role=role, basis=basis, valid_from=vf, valid_to=vt))

    for sp in ("person/dane",):
        grant("dane", sp, "self", "owner of the vault")
    for who in ("dane", "priya"):
        grant(who, "trust/halloran", "trustee", "trust deed")
        grant(who, "household/halloran", "adult", "household")
    grant("priya", "person/priya", "self", "owner of the vault")
    for who, co in (("dane", "company/ironbark"), ("dane", "company/stonefield"), ("dane", "company/copperleaf"), ("lachlan", "company/ironbark"),
                    ("rhea", "company/stonefield"), ("tomas", "company/copperleaf")):
        grant(who, co, "partner", "partnership agreement")
    for who in ("lachlan", "rhea", "tomas"):
        grant(who, f"person/{who}", "self", "owner of the vault")
    for who in ("dane", "priya", "lachlan", "rhea", "tomas"):
        grant(who, "company/ironbark/public", "guest", "public noticeboard")
    for m in MEMBER_IDS2:
        grant(f"member_{m}", f"member/{m}", "self", "member")
        grant(f"member_{m}", f"member/{m}/account", "self", "member")
        grant(f"member_{m}", "company/ironbark/public", "member", "membership")
        for who in ("dane", "lachlan"):
            grant(who, f"member/{m}/account", "operator", "company record (billing, coach assignment)")
    grant("priya", "member/m03", "self", "Priya is member m03")
    grant("priya", "member/m03/account", "self", "Priya is member m03")
    coach_of = {}
    for m in MEMBER_IDS2:
        c = g.by_id[g.keys[f"{m}.coach"]["versions"][-1]]["value"]
        sid = coach_sid[c]
        coach_of[m] = sid
        d0 = g.by_id[g.keys[f"{m}.coach"]["versions"][-1]]["valid_from"]
        if R.random() < 0.2:   # an earlier coach whose consented share has expired (revocation tests)
            prev = R.choice([s for s in coach_sid.values() if s != sid and s != "s_jordan_pike"])
            grant(f"coach_{prev}", f"member/{m}", "coach", "member consent (expired)", 0, d0 + R.randint(30, 200))
            grant(f"coach_{sid}", f"member/{m}", "coach", "member consent", d0 + R.randint(201, 300))
        else:
            grant(f"coach_{sid}", f"member/{m}", "coach", "member consent", d0)
    for sid in sorted(set(coach_sid.values())):
        grant(f"coach_{sid}", "company/ironbark/public", "staff", "employment")
    idents = sorted({gr["identity"] for gr in grants}) + ["nogrant"]

    def visible(who, day=NOW_DAY):
        return sorted({gr["space"] for gr in grants if gr["identity"] == who and gr["valid_from"] <= day and (gr["valid_to"] is None or day < gr["valid_to"])})

    identities = {w: dict(name=w, partitions=visible(w)) for w in idents}

    # registry (entities) with v0.3 spaces; nicknames are NOT registered
    ents_out = []
    for e in g.entities.values():
        ee = {k: v for k, v in e.items() if k not in ("partitions", "pref_kind")}
        ee["aliases"] = [a for a in e["aliases"] if a.lower() not in BAD_ALIAS]   # v0.2 artefact: "The" (from "The Olive Press") matched every request
        ee["spaces"] = entity_spaces(e)
        if e["id"] == "s_ben_okafor" and "person/dane" not in ee["spaces"]:
            ee["spaces"].append("person/dane")
        if e["id"].startswith("mem_") or e["id"] == "p_priya":
            m = e.get("member_id")
            if m:
                ee["spaces"] = sorted(set(ee["spaces"]) | {f"member/{m}", f"member/{m}/account"})
        if e["id"] in coach_sid.values():
            ee["spaces"] = sorted(set(ee["spaces"]) | {"company/ironbark/public"})
        ents_out.append(ee)

    keys_all, keys_conn = [], []
    for k in g.keys.values():
        kk = dict(k)
        kk["space"] = space_of_item(k["partition"], k["scope"])
        if k["key"].split(".")[-1] in ("plan", "coach") and k["key"][:1] == "m" and k["key"][1:3].isdigit():
            kk["space"] = f"member/{k['key'][:3]}/account"
        if k["key"] == "gym.price":
            kk["space"] = "company/ironbark/public"
        kk["extract_only"] = is_extract_key(k)
        keys_all.append(kk)
        if not kk["extract_only"]:
            keys_conn.append({x: kk[x] for x in ("key", "entity", "attr", "label", "versions", "space", "family")})
    # attribute schema for extraction (schema design, not gold): attrs per entity kind
    schema = defaultdict(dict)
    for k in g.keys.values():
        kind = g.entities[k["entity"]]["kind"]
        schema[kind][k["attr"]] = k["label"]
    meta = dict(version="0.3", seed=seed, now_day=NOW_DAY, space_templates=SPACE_TEMPLATES, spaces=spaces, grants=grants, identities=identities,
                coach_of=coach_of, space_default_entity=SPACE_DEFAULT_ENTITY, schema=schema)
    return g, pipe_items, gold_items, ents_out, keys_all, keys_conn, meta, vocab


def main(seed: int = 1, out_root: str = DATA3):
    from . import tasks3
    g, items, gitems, ents, keys_all, keys_conn, meta, vocab = build3(seed)
    tasks = tasks3.build_tasks3(g, items, gitems, ents, keys_all, meta, vocab, seed)
    out = os.path.join(out_root, f"s{seed}")
    os.makedirs(os.path.join(out, "gold"), exist_ok=True)
    write_jsonl(os.path.join(out, "items.jsonl"), items)
    write_jsonl(os.path.join(out, "entities.jsonl"), ents)
    write_jsonl(os.path.join(out, "keys_connector.jsonl"), keys_conn)
    write_jsonl(os.path.join(out, "tasks.jsonl"), tasks)
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    write_jsonl(os.path.join(out, "gold", "items_gold.jsonl"), gitems)
    write_jsonl(os.path.join(out, "gold", "keys_all.jsonl"), keys_all)
    with open(os.path.join(out, "gold", "vocab.json"), "w") as f:
        json.dump(vocab, f, indent=1)
    with open(os.path.join(out, "gold", "specials.json"), "w") as f:
        json.dump({k: v for k, v in g.special.items()}, f)
    return g, items, tasks


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    main(a.seed)
