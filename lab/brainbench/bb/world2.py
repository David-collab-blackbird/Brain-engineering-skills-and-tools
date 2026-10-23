"""BrainBench v0.2 — larger, seed-varied synthetic world (batch-2 validity fixes).

Differences from v0 (bb/world.py, which is left untouched):
  * entity names, values and document wording are drawn from pools per seed, so different seeds are
    genuinely different worlds (v0 had fixed names);
  * many more entities (14 properties, 14 holdings, 10 projects, 8 tenders, 42 gym members, 7 coaches,
    7 cafe supply categories, 6 gym equipment categories, 5 trips, 6 capital commitments, ...), so every
    task class has >=120 DISTINCT required sets;
  * several wording variants for every special document and fact rendering.

Run:  python -m bb.world2 --seed 1     (writes data_v02/s1/*.jsonl)
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict

from .common import NOW_DAY, ROOT, day_to_date, month_start_day, quarter_label, write_jsonl
from .world import MENTION, SCOPES, Gen, fuzz_value, make_books, money_c

N_MONTHS = 18
DATA2 = os.path.join(ROOT, "data_v02")

N_PROP, N_HOLD, N_PROJ, N_TENDER, N_MEM = 14, 14, 10, 8, 42
MEMBER_IDS2 = [f"m{i:02d}" for i in range(1, N_MEM + 1)]
PARTITIONS2 = ["owner", "household", "biz/gym", "biz/construction", "biz/cafe", "public/gym"] + [f"member/{m}" for m in MEMBER_IDS2]


def identities2():
    ids = {
        "owner": {"name": "Dane Halloran", "tier": "owner", "partitions": list(PARTITIONS2)},
        "household": {"name": "Priya Halloran", "tier": "household", "partitions": ["household", "member/m03", "public/gym"]},
        "partner_gym": {"name": "Lachlan Moore", "tier": "partner", "partitions": ["biz/gym", "public/gym"] + [f"member/{m}" for m in MEMBER_IDS2]},
        "partner_construction": {"name": "Rhea Castell", "tier": "partner", "partitions": ["biz/construction", "public/gym"]},
        "partner_cafe": {"name": "Tomas Abiodun", "tier": "partner", "partitions": ["biz/cafe", "public/gym"]},
    }
    for m in MEMBER_IDS2:
        ids[f"member_{m}"] = {"name": None, "tier": "member", "partitions": [f"member/{m}", "public/gym"]}
    return ids


# ---------------------------------------------------------------- pools
STREETS = ["Wren", "Tamar", "Bellbird", "Ostler", "Quarry", "Halyard", "Juniper", "Marram", "Cobalt", "Ferrier", "Larkspur",
           "Pelican", "Banksia", "Corella", "Wattle", "Heron", "Lorikeet", "Tern", "Gannet", "Mallee", "Sextant", "Anchor",
           "Bracken", "Drover", "Foxglove", "Harrier", "Ibis", "Jetty", "Kurrajong", "Moraine", "Nettle", "Paddock", "Quoll",
           "Reedy", "Spinifex", "Tallow", "Umber", "Vireo", "Whistler", "Yarrow"]
STYPES = [("Street", "St"), ("Parade", "Pde"), ("Court", "Ct"), ("Road", "Rd"), ("Lane", "Ln"), ("Way", "Way"), ("Avenue", "Ave"),
          ("Crescent", "Cres"), ("Terrace", "Tce"), ("Close", "Cl"), ("Drive", "Dr"), ("Place", "Pl")]
SUBURBS = ["Granite Falls", "Easthaven", "Coralie", "Marlow Creek", "Kestrel Bay", "Tindal Point", "Ashgrove Rise", "Bramley",
           "Cutters Ridge", "Dunmore", "Elderslie", "Fairhaven", "Glenrock", "Hollins Bay", "Ingleby", "Jarrah Hill", "Kinross",
           "Larkhill", "Merrow", "Northam Flats", "Oakhurst", "Pebble Beach", "Quinns Rock", "Redcliff", "Seacombe", "Thornbury",
           "Upwey", "Valebrook", "Westmere", "Yallingup Heights"]
PKINDS = ["house", "unit", "duplex", "townhouse", "cottage", "villa", "terrace"]
HOLDINGS = [("Meridian Global Equity ETF", "MGE"), ("Halcyon Resources", "HLR"), ("Northgate Bank", "NGB"), ("Aurora Clean Energy", "ACE"),
            ("Pinecrest Infrastructure Fund", "PIF"), ("Solano Health", "SLH"), ("Corvid Logistics", "CVL"), ("Tasman Water", "TWR"),
            ("Brightline Telecom", "BLT"), ("Kestrel Gold", "KGD"), ("Orchard Agri", "ORA"), ("Vantage Software", "VSW"),
            ("Ridgeway REIT", "RRT"), ("Lumen Biotech", "LBX"), ("Harbour Ports Group", "HPG"), ("Saffron Consumer", "SFC"),
            ("Granite Insurance", "GIN"), ("Polaris Semiconductors", "PSC"), ("Eucalypt Timber", "EUT"), ("Coastal Rail", "CRL")]
FIRST = ["Hugo", "Lena", "Marco", "Siobhan", "Arjun", "Clara", "Felix", "Nina", "Owen", "Zara", "Leo", "Maya", "Rohan", "Freya", "Tariq",
         "Elise", "Gideon", "Hana", "Isaac", "Juno", "Kai", "Lucia", "Mateo", "Oscar", "Pia", "Quentin", "Rosa", "Sami", "Talia",
         "Uma", "Victor", "Willa", "Xavier", "Yara", "Zeke", "Amara", "Bodhi", "Cleo", "Dmitri", "Esme", "Finn", "Greta", "Hamish",
         "Ines", "Jasper", "Kiri", "Lars", "Mina", "Niko", "Odette", "Pascal", "Reuben", "Saskia"]
LAST = ["Brennan", "Voss", "Ruiz", "Kerr", "Mehta", "Dunn", "Ward", "Petrova", "Tate", "Quinn", "Hartmann", "Okoro", "Lindqvist",
        "Castillo", "Byrne", "Nakamura", "Sorensen", "Fitzgerald", "Adeyemi", "Moreau", "Kowalski", "Haddad", "Ferreira", "Olsen",
        "Takahashi", "Mbeki", "Duarte", "Lindgren", "Abara", "Costa", "Ivanova", "Mahoney", "Reyes", "Strand", "Yilmaz",
        "Zhou", "Bianchi", "Delacroix", "Eriksen"]
PROJ_PLACES = ["Harlow Park", "Elsbury", "Corran Heights", "Ballina Rise", "Moss Vale", "Pitt Lane", "Rookwood", "Saltwater Flats",
               "Tarrant", "Upfield", "Varley", "Whitlam Grove", "Yarra Bend", "Zetland", "Arden Vale", "Birchgrove"]
PROJ_TYPES = ["extension", "townhouses", "renovation", "duplex build", "granny flat", "new home", "second-storey addition"]
TENDERS = [("Ashgrove childcare centre fit-out", "commercial"), ("Bramley medical suites refurbishment", "commercial"),
           ("Dunmore four-townhouse development", "residential"), ("Kinross heritage cottage restoration", "residential"),
           ("Merrow school canteen upgrade", "commercial"), ("Oakhurst warehouse office fit-out", "commercial"),
           ("Redcliff dual-occupancy build", "residential"), ("Seacombe surf club extension", "commercial"),
           ("Thornbury aged-care refurbishment", "commercial"), ("Valebrook three-storey apartments", "residential"),
           ("Glenrock family home rebuild", "residential"), ("Fairhaven dental clinic fit-out", "commercial")]
CAFE_CATS = {
    "beans": ("coffee bean supplier", ["Ridgeback Roasters", "Ember & Oak Coffee", "Saltbush Coffee Roasters", "Northside Roastery", "Kettle Hill Coffee"],
              ["Beans didn't turn up this morning — bought retail bags to get through.", "{s} delivery came at 11 instead of 6, nearly ran out of house blend.",
               "Roaster missed the Tuesday drop again.", "Short-shipped on decaf, invoice still charged the full order.", "No coffee delivery today, {s} not answering."]),
    "milk": ("milk supplier", ["Valley Fresh Dairy", "Greenhill Dairy Co-op", "Riverbend Milk", "Paddock Lane Dairy"],
             ["Milk was off again — two crates binned.", "{s} late for the third week; customers waiting on flat whites.",
              "Half the oat milk cartons were dented and leaking.", "Dairy driver left the crates in the sun, all warm by 7."]),
    "bread": ("bread supplier", ["Crumb & Co Bakery", "Stonemill Breads", "Hearth Street Bakehouse", "Rye & Rise"],
              ["Sourdough came in stale, had to 86 the toasties.", "{s} forgot the gluten-free loaves again.", "Bread drop was an hour late, breakfast rush started without it."]),
    "produce": ("fruit and veg supplier", ["Market Lane Produce", "Greenleaf Grocers", "Harvest Run", "Orchard Gate Fresh"],
                ["Avocados were rock hard, smashed avo off the menu by 9.", "{s} subbed the spinach for rocket without asking.", "Half a box of tomatoes mouldy on arrival."]),
    "cleaning": ("cleaning contractor", ["Sparkline Cleaning", "Brightway Commercial Cleaning", "Shine Crew", "CleanSlate Services"],
                 ["Cleaners skipped the bathrooms last night.", "{s} left the floor wet and unsigned — slip hazard at open.", "Kitchen exhaust filters not done for a month."]),
    "packaging": ("takeaway packaging supplier", ["Ecopack Supplies", "CupCo", "GreenCup Packaging", "Boxwell"],
                  ["Ran out of 8oz lids, {s} backordered.", "Cups arrived with the wrong print run.", "Compostable bowls leaking at the seams."]),
    "linen": ("linen supplier", ["Talbot Linen Services", "Crisp Linen Co", "Fold & Press"],
              ["Linen delivery short two bags of tea towels.", "{s} sent aprons with someone else's logo.", "Tea towels came back still stained."]),
}
GYM_CATS = {"racks": ("squat racks", "three racks have worn J-hooks and one upright has a cracked weld"),
            "rowers": ("rowing machines", "two rowers have slipping chains and one monitor is dead"),
            "bikes": ("assault bikes", "fan bearings are grinding on four bikes"),
            "flooring": ("rubber flooring", "tiles in the lifting area have split and are lifting at the edges"),
            "dumbbells": ("dumbbell set", "several heads are loose and the 30s are missing"),
            "cables": ("cable machine", "the pulley cable is frayed and the weight stack sticks")}
GYM_SUPPLIERS = ["Forge Athletic Supply", "Apex Rig Co", "Titan Barbell Works", "Ironclad Fitness Supply", "Kinetic Gear", "Summit Strength Co"]
COACHES = ["Sasha Novak", "Ben Okafor", "Imogen Hartley", "Raf Silva", "Corey Lin", "Tess Wardle", "Jordan Pike"]
SPECIALTIES = [("strength", "barbell strength and powerlifting technique"), ("rehab", "return-from-injury and mobility work"),
               ("hiit", "conditioning and HIIT for busy people"), ("beginner", "nervous beginners and building confidence"),
               ("olympic", "Olympic lifting and athletic power"), ("weightloss", "body composition and nutrition habits"),
               ("endurance", "running and endurance blocks")]
MEMBER_PREFS = {"strength": ["Enjoys strength work, wants to learn to squat and deadlift properly.", "Loves lifting heavy; bored by cardio."],
                "rehab": ["Coming back from a shoulder injury; wants to move without pain.", "Bad knees — needs low-impact, careful progressions."],
                "hiit": ["Likes fast, sweaty sessions; can only spare 30 minutes.", "Wants high-energy group workouts after work."],
                "beginner": ["First time in a gym, a bit intimidated by the free-weights area.", "Never trained before; prefers small groups."],
                "olympic": ["Ex-sprinter, wants to learn the snatch and clean.", "Keen on explosive lifts and jumping."],
                "weightloss": ["Main goal is dropping body fat; wants accountability.", "Interested in habits and food as much as training."],
                "endurance": ["Training for a half marathon; wants strength to support running.", "Cyclist looking for off-season conditioning."]}
CAFE_STAFF_EXTRA = ["Ravi Sharma", "Bella Costa", "Finn Gallagher", "Lucy Park", "Sam Otieno"]
DUAL_ROLE = [("s_jordan_pike", "b_gym", "b_cafe", "part-time coach mornings at the gym, two cafe shifts a week"),
             ("s_tess_wardle", "b_gym", "b_cafe", "runs Saturday classes, and helps on the cafe register on Sundays"),
             ("s_gus_harland", "b_con", "b_gym", "labourer at Stonefield, does the gym's Sunday deep clean for extra cash"),
             ("s_kit_dawson", "b_cafe", "b_con", "weekend barista, also does Stonefield's invoicing two afternoons a week")]
PLACES = [("Saltmarsh Beach", "the kids love the rock pools", "p_ruby"), ("Ferngully Adventure Park", "Theo's favourite — high ropes course", "p_theo"),
          ("Lantern Hill Lookout", "easy walk, Ruby can manage it", "p_ruby"), ("Bramble Creek Farm", "pick-your-own berries, Ruby loved the goats", "p_ruby"),
          ("Tidewater Aquatic Centre", "wave pool; Mila trains here too", "p_mila"), ("Hoopla Courts", "indoor basketball open sessions, Theo would live there", "p_theo"),
          ("Clayworks Studio", "kids pottery class, Ruby made a bowl", "p_ruby"), ("Rip Curl Point", "surf lessons, Mila keen to try", "p_mila"),
          ("Skyline Trampoline Park", "Theo and friends, two hours flat out", "p_theo"), ("Westmere Wildlife Sanctuary", "koalas and the reptile show", "p_ruby"),
          ("Harbour Climbing Gym", "bouldering — Mila and Theo both loved it", "p_mila"), ("Old Mill Cinema", "cheap Tuesday movies, everyone happy", "p_theo")]
RESTAURANTS = ["Maple & Fig", "Koto Izakaya", "Little Saigon Kitchen", "The Olive Press", "Harbour Fish Co", "Nonna's Table", "Spice Route", "Copper Pot Bistro"]
OCCASIONS = [("birthday", "Priya's birthday: somewhere with share plates and a dessert worth it; Koto or Maple & Fig."),
             ("anniversary", "Anniversary: quiet, candlelit, no kids — The Olive Press was perfect last time."),
             ("date night", "Date night rule: walking distance or a cheap taxi, nothing fancy, Little Saigon is a winner."),
             ("grandparents", "When the grandparents visit: early dinner, easy parking, Nonna's Table (Grandpa's hearing — avoid loud places)."),
             ("team dinner", "End-of-season kids' team dinners: big tables, pizza, Copper Pot Bistro has a function room.")]
TRIPS = [("Coral Bay cabin", "5 nights in a beachfront cabin, $2,150, 3.5 hours' drive"), ("Snowy River lodge", "4 nights at a mountain lodge, $3,400, 6 hours' drive"),
         ("Kestrel Bay caravan park", "6 nights in a park cabin with a pool, $1,650, 2 hours' drive"),
         ("Gold Coast theme parks", "5 nights hotel plus park passes, $5,900, flights needed"), ("Lake Tamar houseboat", "3 nights on a houseboat, $2,700, 4 hours' drive")]
COMMITMENTS = [("gym_fitout", "biz/gym", "business/gym/finance", "Partners meeting: committed $45k for the recovery-room fit-out, install booked for August 2026; funded from gym reserve plus a $15k owner contribution each.", ["b_gym", "p_lachlan", "p_dane"]),
               ("cafe_kitchen", "biz/cafe", "business/cafe/finance", "Partners agreed the cafe kitchen upgrade: new combi oven and extraction, $28k total, $14k from each partner by September 2026.", ["b_cafe", "p_tomas", "p_dane"]),
               ("con_ute", "biz/construction", "business/construction/finance", "Office meeting: buying a second work ute for the new supervisor, $62k, 20% deposit from partners, balance on chattel mortgage.", ["b_con", "p_rhea", "p_dane"]),
               ("car_replace", "household", "family/leisure", "Priya's car is on its last legs — we said $35k for a replacement before the end of the year.", ["p_priya", "p_dane"]),
               ("school_fees", "household", "family/leisure", "School fees for next year confirmed: $14,800 for the three kids, first instalment due in January.", ["p_mila", "p_theo", "p_ruby"]),
               ("solar", "owner", "finance/personal", "Quote accepted in principle: 10kW solar plus battery for home, $18,900 after rebate, install in October.", ["p_dane"])]
COMMIT_DESC = {"gym_fitout": "the recovery room fit-out", "cafe_kitchen": "the cafe kitchen upgrade", "con_ute": "the new work ute",
               "car_replace": "Priya's new car", "school_fees": "next year's school fees", "solar": "the solar and battery install"}

pct = lambda v: f"{v:.2f}%"
wk = lambda v: f"${v:,.0f} per week"

FACT_RENDERS = [
    lambda e, label, vs, d: f"{e} — {label}: {vs} (as at {day_to_date(d)}).",
    lambda e, label, vs, d: f"Record for {e}: {label} is {vs}, effective {day_to_date(d)}.",
    lambda e, label, vs, d: f"{label.capitalize()} ({e}) updated to {vs} on {day_to_date(d)}.",
    lambda e, label, vs, d: f"{e} | {label} | {vs} | from {day_to_date(d)}",
]

MENTION2 = dict(MENTION)
MENTION2.update({
    "retention": ["{a}'s client retention is {v} this quarter.", "Retention check — {a}: {v}.", "{a} kept {v} of clients."],
    "cost": ["Cost to date on {a}: {v}.", "{a} has spent {v} so far.", "Running cost tally for {a} — {v}."],
    "valuation": MENTION["valuation"] + ["Neighbour sold for less, but our {a} still looks like {v}.", "Rough number for {a} from the bank portal: {v}."],
    "loan": MENTION["loan"] + ["{a} mortgage: {v} outstanding."],
    "supplier": MENTION["supplier"] + ["{v} is doing the {label} for {a} now."],
    "goal": MENTION["goal"] + ["New target: {v}.", "We said {v}. Holding ourselves to it."],
})


class Gen2(Gen):
    def fact2(self, key, entity, attr, label, versions, partition, scope, fmt, kind="state", family="generic", render=None):
        if render is None:
            rf = self.rng.choice(FACT_RENDERS)
            render = lambda e, vs, d, _rf=rf, _l=label: _rf(e, _l, vs, d)
        return self.fact(key, entity, attr, label, versions, partition, scope, fmt, kind, family, render)

    def mention2(self, key, vid, day, type_="note"):
        import re as _re
        k = self.keys[key]
        iid = self.mention(key, vid, day, type_=type_, templates=MENTION2.get(k["family"], MENTION2["generic"]))
        it = self.by_id[iid]
        t = _re.sub(r"\b(our|my|the|of) the ", r"\1 ", it["text"])
        it["text"] = t[0].upper() + t[1:]
        return iid


def _uniq_names(R, n, firsts, lasts, taken):
    out = []
    while len(out) < n:
        nm = f"{R.choice(firsts)} {R.choice(lasts)}"
        if nm not in taken:
            taken.add(nm)
            out.append(nm)
    return out


# ================================================================ build
def build2(seed: int) -> Gen2:
    g = Gen2(seed)
    R = g.rng
    g.meta = {}
    g.special = defaultdict(list)   # tag -> item ids (task builder reads these)
    S = g.add

    def sp(tag, iid):
        g.special[tag].append(iid)
        g.tag[tag].append(iid)
        return iid

    # ---- core people / businesses (stable across seeds; they are the household)
    g.ent("p_dane", "person", "Dane Halloran", ["Dane", "me"], ["owner", "household"])
    g.ent("p_priya", "person", "Priya Halloran", ["Priya", "P"], ["household", "member/m03"])
    for kid, al in (("p_mila", ["Mila Halloran", "our eldest"]), ("p_theo", ["Theo Halloran", "the middle one"]), ("p_ruby", ["Ruby Halloran", "the little one"])):
        g.ent(kid, "person", kid[2:].capitalize(), al, ["household"])
        g.edge("p_dane", kid, "family", "household")
    g.edge("p_dane", "p_priya", "family", "household")
    g.ent("p_lachlan", "person", "Lachlan Moore", ["Lachlan", "Lachie"], ["biz/gym"])
    g.ent("p_rhea", "person", "Rhea Castell", ["Rhea"], ["biz/construction"])
    g.ent("p_tomas", "person", "Tomas Abiodun", ["Tomas"], ["biz/cafe"])
    g.ent("p_nadia", "person", "Nadia Ferris", ["Nadia", "the broker"], ["owner"])
    g.ent("b_gym", "business", "IronBark Fitness", ["IronBark", "the gym", "Ironbark gym"], ["biz/gym", "public/gym"])
    g.ent("b_con", "business", "Stonefield Builders", ["Stonefield", "the building company", "the construction business"], ["biz/construction"])
    g.ent("b_cafe", "business", "Copperleaf Cafe", ["Copperleaf", "the cafe", "the café"], ["biz/cafe"])
    bpart = {"b_gym": "biz/gym", "b_cafe": "biz/cafe", "b_con": "biz/construction"}
    for b, p in (("b_gym", "p_lachlan"), ("b_con", "p_rhea"), ("b_cafe", "p_tomas")):
        g.edge("p_dane", b, "owns", bpart[b]); g.edge(p, b, "partner", bpart[b])

    taken = {"Dane Halloran", "Priya Halloran", "Lachlan Moore", "Rhea Castell", "Tomas Abiodun", "Nadia Ferris"} | set(COACHES)
    # ---- staff
    cafe_staff = ["Jordan Pike", "Mei Tran", "Olly Brandt", "Ana Ruiz", "Kit Dawson"] + R.sample(CAFE_STAFF_EXTRA, 3)
    con_staff = ["Ross Delaney", "Kira Matthews", "Dev Patel", "Sione Fifita", "Gus Harland", "Wade Kerr"]
    taken |= set(cafe_staff) | set(con_staff)
    for b, names in (("b_gym", COACHES), ("b_cafe", cafe_staff), ("b_con", con_staff)):
        for n in names:
            sid = "s_" + n.split()[0].lower() + "_" + n.split()[1].lower()
            if sid not in g.entities:
                g.ent(sid, "person", n, [n.split()[0]], [])
            if bpart[b] not in g.entities[sid]["partitions"]:
                g.entities[sid]["partitions"].append(bpart[b])
            g.edge(sid, b, "works_at", bpart[b])
    for sid, b1, b2, _ in DUAL_ROLE:
        for b in (b1, b2):
            if bpart[b] not in g.entities[sid]["partitions"]:
                g.entities[sid]["partitions"].append(bpart[b]); g.edge(sid, b, "works_at", bpart[b])
    g.entities["s_ben_okafor"]["partitions"].append("owner")

    # ---- shared / misc suppliers
    for sid, name, al, parts in (("sup_talbot", "Talbot Linen Services", ["Talbot", "Talbot Linen"], ["biz/gym", "biz/cafe"]),
                                 ("sup_brightwater", "Brightwater Plumbing", ["Brightwater", "the plumber"], ["biz/construction", "biz/cafe"]),
                                 ("sup_sparkline", "Sparkline Cleaning", ["Sparkline", "the cleaners"], ["biz/gym", "biz/cafe"]),
                                 ("sup_northcrest", "Northcrest Insurance", ["Northcrest"], ["biz/construction", "biz/gym"]),
                                 ("sup_harbourline", "Harbourline Property Management", ["Harbourline"], ["owner"]),
                                 ("sup_keystone", "Keystone Rentals", ["Keystone"], ["owner"]),
                                 ("sup_clearpath", "Clearpath Finance", ["Clearpath", "the broker's firm"], ["owner"]),
                                 ("sup_peopleworks", "PeopleWorks Hospitality Recruitment", ["PeopleWorks"], ["biz/cafe"]),
                                 ("sup_grayline", "Grayline Concrete", ["Grayline"], ["biz/construction"]),
                                 ("sup_monarch", "Monarch Readymix", ["Monarch"], ["biz/construction"])):
        g.ent(sid, "supplier", name, al, parts)

    FI = "finance/investments"
    # ================================================================ properties
    streets = R.sample(STREETS, N_PROP); subs = R.sample(SUBURBS, N_PROP)
    props = []
    for i in range(N_PROP):
        st, (stype, sab) = streets[i], R.choice(STYPES)
        kind = R.choice(PKINDS)
        num = f"{R.randint(1, 9)}/{R.randint(2, 60)}" if kind in ("unit", "villa") else str(R.randint(2, 88))
        pid = f"prop_{st.lower()}"
        name = f"{num} {st} {stype}, {subs[i]}"
        g.ent(pid, "property", name, [f"{st} {sab}", f"the {subs[i]} {kind}", f"the {st} {stype} {kind}", f"{num} {st}"], ["owner"], scope=FI, kind2=kind, suburb=subs[i])
        g.edge("p_dane", pid, "owns", "owner")
        props.append(pid)
    for pid in props:
        val = R.randint(42, 98) * 10_000
        vals = []
        for q in range(6):
            if q:
                val = round(val * (1 + R.gauss(0.018, 0.02)) / 1000) * 1000
            vals.append((month_start_day(q * 3) + R.randint(3, 25), val))
        g.fact2(f"{pid}.valuation", pid, "valuation", "current valuation", vals, "owner", FI, money_c, family="valuation")
        loan = round(vals[0][1] * R.uniform(0.5, 0.74) / 1000) * 1000
        loans = []
        for q in range(6):
            if q:
                loan = round(loan * (1 - R.uniform(0.006, 0.018)) / 100) * 100
            loans.append((month_start_day(q * 3) + R.randint(1, 20), loan))
        g.fact2(f"{pid}.loan", pid, "loan_balance", "loan balance", loans, "owner", FI, money_c, family="loan")
        r0 = R.choice([6.09, 6.19, 6.24, 6.34, 5.99, 6.44])
        g.fact2(f"{pid}.rate", pid, "interest_rate", "interest rate",
                [(month_start_day(0) + 2, r0), (month_start_day(7) + 3, r0 - 0.25), (month_start_day(13) + 3, r0 - 0.5 + R.choice([0, 0.05, -0.1]))], "owner", FI, pct, family="rate")
        rent, rm = R.randint(42, 78) * 10, R.randint(4, 14)
        g.fact2(f"{pid}.rent", pid, "weekly_rent", "weekly rent", [(month_start_day(0) + 5, rent), (month_start_day(rm) + 5, rent + R.choice([15, 20, 25, 30, 40]))], "owner", FI, wk, family="rent")
        pms = [(month_start_day(0) + 1, "Harbourline Property Management")]
        if R.random() < 0.35:
            pms.append((month_start_day(R.randint(7, 11)) + 4, "Keystone Rentals"))
        g.fact2(f"{pid}.pm", pid, "property_manager", "property manager", pms, "owner", FI, str, family="pm")
        g.fact2(f"{pid}.lease_end", pid, "lease_end", "lease end date",
                [(month_start_day(0) + 5, day_to_date(month_start_day(rm) + 4)), (month_start_day(rm) + 5, day_to_date(month_start_day(rm) + 369))], "owner", FI, str, family="lease_end")
        g.edge(pid, "sup_harbourline" if len(pms) == 1 else "sup_keystone", "managed_by", "owner")

    # ---- holdings
    holds = []
    for name, tick in R.sample(HOLDINGS, N_HOLD):
        hid = f"h_{tick.lower()}"
        short = name.split()[0]
        g.ent(hid, "holding", name, [tick, short, f"the {short} shares"], ["owner"], scope=FI)
        holds.append(hid)
        units = R.randint(8, 60) * 50
        uv = [(month_start_day(0) + 2, units)]
        for m in sorted(R.sample(range(3, 17), R.randint(1, 2))):
            units = max(100, units + R.choice([-1, 1, 1]) * R.randint(2, 12) * 50)
            uv.append((month_start_day(m) + R.randint(2, 20), units))
        g.fact2(f"{hid}.units", hid, "units", "units held", uv, "owner", FI, lambda v: f"{v:,} units", family="units")
        px, mv = R.uniform(8, 60), []
        for q in range(6):
            px *= 1 + R.gauss(0.02, 0.06)
            d = month_start_day(q * 3) + R.randint(25, 28)
            u = g.by_id[g.version_at(f"{hid}.units", d) or g.keys[f"{hid}.units"]["versions"][0]]["value"]
            mv.append((d, round(u * px / 100) * 100))
        g.fact2(f"{hid}.value", hid, "market_value", "market value", mv, "owner", FI, money_c, family="mvalue")

    # ---- personal finance
    g.ent("fin_portfolio", "account", "the property portfolio", ["portfolio", "our properties", "the investment portfolio"], ["owner"], scope=FI)
    g.ent("fin_offset", "account", "offset account", ["offset", "cash buffer", "the offset"], ["owner"], scope="finance/personal")
    g.ent("fin_household", "account", "household budget", ["family budget", "household spending"], ["household"], scope="finance/personal")
    g.ent("fin_edu", "account", "education fund", ["the kids' education fund", "school savings"], ["household"], scope="finance/personal")
    cash, cv = R.randint(70, 100) * 1000, []
    for m in range(N_MONTHS):
        if m:
            cash += R.randint(-6, 9) * 1000
        if m == 11:
            cash -= 38_000
        cv.append((month_start_day(m) + R.randint(26, 27), cash))
    g.fact2("offset.balance", "fin_offset", "balance", "offset balance", cv, "owner", "finance/personal", money_c, family="cash")
    bc0 = R.randint(85, 105) * 10_000
    g.fact2("portfolio.borrowing_capacity", "fin_portfolio", "borrowing_capacity", "borrowing capacity",
            [(month_start_day(0) + 14, bc0), (month_start_day(8) + 9, bc0 + 150_000), (month_start_day(14) + 6, bc0 + 290_000)], "owner", FI, money_c, family="borrowing")
    lv = R.choice([70, 72, 75])
    g.fact("portfolio.lvr_rule", "fin_portfolio", "lvr_rule", "maximum portfolio LVR rule",
           [(month_start_day(0) + 3, f"keep total portfolio loan-to-value at or below {lv}%"), (month_start_day(12) + 8, f"keep total portfolio loan-to-value at or below {lv-5}% after the rate scare")],
           "owner", FI, str, family="rule", render=lambda e, v, d: f"Rule for {e}: {v}. Agreed {day_to_date(d)}.")
    g.fact("portfolio.strategy", "fin_portfolio", "strategy", "investment strategy",
           [(month_start_day(0) + 6, "Buy and hold in our home region; prioritise rental yield; no flips."),
            (month_start_day(9) + 12, "Buy and hold, but the next purchases go interstate for diversification — target growth corridors with infrastructure spend; yield secondary.")],
           "owner", FI, str, family="strategy", render=lambda e, v, d: f"Strategy statement for {e} (set {day_to_date(d)}): {v}")
    g.fact2("offset.savings_goal", "fin_offset", "buffer_goal", "cash buffer goal", [(month_start_day(0) + 9, "$60,000 emergency buffer"), (month_start_day(10) + 2, "$80,000 emergency buffer")], "owner", "finance/personal", str, family="goal")
    g.fact2("household.budget", "fin_household", "monthly_budget", "monthly household budget", [(month_start_day(0) + 4, 9_500), (month_start_day(9) + 4, 10_200)], "household", "finance/personal", lambda v: f"${v:,} per month")
    g.fact2("edu.goal", "fin_edu", "goal", "education savings goal", [(month_start_day(0) + 4, "$40,000 in the education fund by the end of 2026")], "household", "finance/personal", str, family="goal")
    eb = R.randint(18, 26) * 1000
    g.fact2("edu.balance", "fin_edu", "balance", "education fund balance", [(month_start_day(q * 3) + 20, eb + q * R.randint(2, 4) * 1000) for q in range(6)], "household", "finance/personal", money_c, family="cash")

    # ================================================================ gym
    GO, GF = "business/gym/ops", "business/gym/finance"
    mem, mc = R.randint(290, 330), []
    for q in range(6):
        if q:
            mem += R.randint(10, 30)
        mc.append((month_start_day(q * 3) + R.randint(5, 15), mem))
    g.fact2("gym.members", "b_gym", "membership_count", "active memberships", mc, "biz/gym", GF, lambda v: f"{v} members", family="count")
    g.fact2("gym.member_target", "b_gym", "membership_target", "membership target", [(month_start_day(0) + 10, "400 active members by December 2025"), (month_start_day(12) + 5, "450 active members by December 2026")], "biz/gym", GF, str, family="goal")
    g.fact2("gym.head_coach", "b_gym", "head_coach", "head coach", [(month_start_day(0) + 1, "Sasha Novak"), (month_start_day(7) + 10, "Ben Okafor")], "biz/gym", GO, str, family="person_role")
    g.fact2("gym.equipment_supplier", "b_gym", "equipment_supplier", "equipment supplier", [(month_start_day(0) + 1, "Forge Athletic Supply"), (month_start_day(11) + 15, "Apex Rig Co")], "biz/gym", GO, str, family="supplier")
    g.fact2("gym.towel_supplier", "b_gym", "towel_supplier", "towel and laundry supplier", [(month_start_day(0) + 1, "Talbot Linen Services")], "biz/gym", GO, str, family="supplier")
    g.fact2("gym.cleaner", "b_gym", "cleaner", "cleaning contractor", [(month_start_day(0) + 1, "Sparkline Cleaning")], "biz/gym", GO, str, family="supplier")
    g.fact2("gym.insurer", "b_gym", "insurer", "insurer", [(month_start_day(0) + 1, "Northcrest Insurance")], "biz/gym", GF, str, family="supplier")
    g.fact2("gym.lease", "b_gym", "monthly_lease", "monthly lease cost", [(month_start_day(0) + 1, 8_400), (month_start_day(12) + 1, 8_900)], "biz/gym", GF, lambda v: f"${v:,} per month", family="price")
    g.fact2("gym.staff_count", "b_gym", "staff_count", "staff headcount", [(month_start_day(0) + 1, 9), (month_start_day(6) + 1, 11), (month_start_day(13) + 1, 12)], "biz/gym", GO, lambda v: f"{v} staff", family="count")
    g.fact2("gym.price", "b_gym", "membership_price", "standard membership price", [(month_start_day(0) + 1, 32), (month_start_day(6) + 14, 35)], "biz/gym", GF, lambda v: f"${v} per week", family="price")
    g.fact2("gym.timetable", "b_gym", "timetable", "class timetable",
            [(month_start_day(0) + 1, "6am strength Mon/Wed/Fri, 6pm HIIT Tue/Thu, Sat 8am team WOD"),
             (month_start_day(8) + 1, "5:30am and 6:30am strength Mon/Wed/Fri, 6pm HIIT Tue/Thu, Sat 8am team WOD, Sun 9am mobility, Wed 7pm beginners")], "public/gym", GO, str)
    g.fact2("gym.revenue_goal", "b_gym", "revenue_goal", "annual revenue target", [(month_start_day(12) + 3, "$980,000 for calendar 2026")], "biz/gym", GF, str, family="goal")
    # coaches: specialty notes + retention keys
    specs = list(SPECIALTIES)
    R.shuffle(specs)
    g.meta["coach_spec"] = {}
    for c, (sk, sdesc) in zip(COACHES, specs):
        sid = "s_" + c.split()[0].lower() + "_" + c.split()[1].lower()
        g.meta["coach_spec"][sk] = sid
        sp(f"coach_spec:{sid}", S("note", "biz/gym", GO, R.choice([f"{c.split()[0]} is our go-to for {sdesc}.", f"Coach profile — {c}: specialises in {sdesc}.", f"If a member needs {sdesc}, book them with {c.split()[0]}."]),
                                  month_start_day(R.randint(2, 10)) + 4, entities=[sid, "b_gym"], tags=("coach_spec",)))
        r0 = R.randint(60, 78)
        g.fact2(f"{sid}.retention", sid, "client_retention", "12-month client retention", [(month_start_day(q * 3) + 25, r0 + q * R.choice([-1, 0, 1, 2])) for q in range(6)], "biz/gym", GO, lambda v: f"{v}%", family="retention")
        g.fact2(f"{sid}.retention_target", sid, "retention_target", "retention target", [(month_start_day(6) + 3, f"keep 12-month client retention above {R.choice([75, 78, 80])}%")], "biz/gym", GO, str, family="goal")
        sp(f"coach_review:{sid}", S("note", "biz/gym", GO, R.choice([f"Quarterly review with {c.split()[0]}: clients love the sessions but follow-up messages slip when it's busy.",
                                                                    f"{c.split()[0]}'s review: great technical coaching; needs to book next sessions before clients leave.",
                                                                    f"Review notes ({c}): two long-term clients left after a timetable change; plan to re-engage them."]),
                                    month_start_day(R.randint(13, 16)) + 6, entities=[sid, "b_gym"], tags=("coach_review",)))
    # equipment categories
    for cat, (what, issue) in GYM_CATS.items():
        sp(f"gym_issue:{cat}", S("note", "biz/gym", GO, R.choice([f"Equipment audit: {issue}. {what.capitalize()} flagged as a safety risk.", f"Heads up on the {what}: {issue}.", f"Maintenance log — {what}: {issue}; partly out of service."]),
                                 month_start_day(R.randint(9, 15)) + 8, entities=["b_gym"], tags=("gym_issue",)))
        for s_ in R.sample(GYM_SUPPLIERS, 2):
            sp(f"gym_quote:{cat}", S("email", "biz/gym", GO, f"Quote from {s_}: replacement {what}, ${R.randint(8, 60) * 100:,} all up, {R.randint(2, 8)}-week lead time, {R.choice([3, 5, 10])}-year warranty.",
                                     month_start_day(R.randint(10, 16)) + 12, entities=["b_gym"], tags=("gym_quote",)))
    sp("gym_hire_decision", S("meeting", "biz/gym", GO, "Partners meeting (Lachlan, Dane): hiring freeze on new coaches until we're consistently above 400 active members; use casual cover for peaks.", month_start_day(8) + 9, entities=["b_gym", "p_lachlan"]))
    sp("gym_price_decision", S("meeting", "biz/gym", GF, "Partners meeting: price rise to $35/week approved from July; grandfather existing members for three months.", month_start_day(6) + 3, entities=["b_gym", "p_lachlan"]))
    sp("gym_capacity", S("note", "biz/gym", GO, "Peak-hour headcount: 6am strength classes at capacity four days out of five; waitlist averaging 7.", month_start_day(15) + 8, entities=["b_gym"]))

    # ---- gym members
    staff_first = {n.split()[0] for n in COACHES + cafe_staff + con_staff}
    mfirst = [f for f in FIRST if f not in staff_first]
    firsts = R.sample(mfirst, N_MEM)            # unique first names: tasks refer to members by first name
    mnames = [f"{f} {R.choice(LAST)}" for f in firsts]
    mnames[2] = "Priya Halloran"
    plans = ["Casual 10-pass", "Standard weekly", "Unlimited", "Off-peak", "Strength squad", "Family add-on"]
    progs = ["beginner strength 3x/week", "hypertrophy split 4x/week", "HIIT + mobility", "powerlifting peaking block", "general fitness 2x/week", "return-from-injury rehab", "half-marathon strength support"]
    g.meta["member_names"] = {}
    for m, nm in zip(MEMBER_IDS2, mnames):
        eid = "p_priya" if m == "m03" else f"mem_{m}"
        if m != "m03":
            g.ent(eid, "person", nm, [nm.split()[0]], [f"member/{m}"])
        g.entities[eid]["member_id"] = m
        g.meta["member_names"][m] = nm
        g.edge(eid, "b_gym", "member_of", f"member/{m}")
        mp = f"member/{m}"
        p1, p2 = R.sample(plans, 2)
        g.fact2(f"{m}.plan", eid, "plan", "membership plan", [(month_start_day(R.randint(0, 3)) + 3, p1), (month_start_day(R.randint(6, 15)) + 3, p2)], mp, "business/gym/members", str, family="plan")
        q1, q2 = R.sample(progs, 2)
        g.fact2(f"{m}.program", eid, "program", "training program", [(month_start_day(R.randint(0, 4)) + 3, q1), (month_start_day(R.randint(8, 16)) + 3, q2)], mp, "business/gym/members", str, family="member_program")
        c = R.choice(COACHES[:6])
        g.fact2(f"{m}.coach", eid, "coach", "assigned coach", [(month_start_day(0) + 3, c)], mp, "business/gym/members", str)
        kind = R.choice(["deadlift", "bodyfat", "attendance", "run5k", "pullups"])
        gs = R.randint(1, 6)
        if kind == "deadlift":
            tgt = [(month_start_day(gs) + 2, f"deadlift {R.randint(10, 14)*10} kg by end of 2025"), (month_start_day(R.randint(12, 14)) + 2, f"deadlift {R.randint(15, 18)*10} kg by end of 2026")]
            v0 = R.randint(8, 11) * 10
            prog = [(month_start_day(gs + 3 * i) + 9, v0 + i * R.choice([5, 10])) for i in range(4)]; fmtp, plab = (lambda v: f"{v} kg"), "deadlift best"
        elif kind == "bodyfat":
            tgt = [(month_start_day(gs) + 2, f"body fat under {R.randint(18, 24)}% by mid-2026")]
            v0 = R.randint(26, 32)
            prog = [(month_start_day(gs + 3 * i) + 9, v0 - i * R.choice([1, 2])) for i in range(4)]; fmtp, plab = (lambda v: f"{v}% body fat"), "body composition"
        elif kind == "attendance":
            tgt = [(month_start_day(gs) + 2, "train 3 times a week consistently")]
            prog = [(month_start_day(gs + 3 * i) + 9, R.choice([1, 2, 2, 3, 3, 4])) for i in range(4)]; fmtp, plab = (lambda v: f"{v} visits per week on average"), "attendance"
        elif kind == "pullups":
            tgt = [(month_start_day(gs) + 2, f"{R.randint(5, 12)} strict pull-ups by spring")]
            prog = [(month_start_day(gs + 3 * i) + 9, i + R.randint(0, 2)) for i in range(4)]; fmtp, plab = (lambda v: f"{v} strict pull-ups"), "pull-up count"
        else:
            tgt = [(month_start_day(gs) + 2, f"run 5k under {R.randint(24, 29)} minutes")]
            prog = [(month_start_day(gs + 3 * i) + 9, f"{R.randint(27, 33) - i}:{R.randint(10, 59)}") for i in range(4)]; fmtp, plab = str, "5k time"
        g.fact2(f"{m}.goal", eid, "goal", "member goal", tgt, mp, "business/gym/members", str, family="goal")
        g.fact2(f"{m}.progress", eid, "progress", plab, prog, mp, "business/gym/members", fmtp)
        sk = R.choice(list(MEMBER_PREFS))
        g.entities[eid]["pref_kind"] = sk
        sp(f"member_pref:{m}", S("preference", mp, "business/gym/members", R.choice(MEMBER_PREFS[sk]) + R.choice(["", " Prefers early mornings.", " Evenings only.", " Weekends suit best."]),
                                 month_start_day(R.randint(2, 14)) + 4, entities=[eid]))
        sp(f"member_checkin:{m}", S("log", mp, "business/gym/members", R.choice(["Coach check-in: technique improving; next step add a fourth weekly session.", "Check-in: missed two weeks with illness, ease back in.",
                                                                                "Check-in: progressing well, ready for a new block next month.", "Check-in: motivation dipping, wants more variety.",
                                                                                "Check-in: niggle in the lower back, regress the hinge for a fortnight."]), month_start_day(R.randint(14, 17)) + 4, entities=[eid]))

    # ================================================================ construction
    CO, CF = "business/construction/ops", "business/construction/finance"
    pipe, pv, ap = R.randint(18, 26) * 100_000, [], []
    for q in range(6):
        if q:
            pipe = round(pipe * (1 + R.gauss(0.03, 0.12)) / 10_000) * 10_000
        d = month_start_day(q * 3) + R.randint(5, 20)
        pv.append((d, pipe)); ap.append((d, R.randint(3, 7)))
    g.fact2("con.pipeline", "b_con", "pipeline_value", "contracted pipeline value", pv, "biz/construction", CF, money_c, family="count")
    g.fact2("con.active_projects", "b_con", "active_projects", "active projects", ap, "biz/construction", CO, lambda v: f"{v} active jobs", family="count")
    g.fact2("con.concrete_supplier", "b_con", "concrete_supplier", "concrete supplier", [(month_start_day(0) + 1, "Grayline Concrete"), (month_start_day(8) + 12, "Monarch Readymix")], "biz/construction", CO, str, family="supplier")
    g.fact2("con.supervisor", "b_con", "site_supervisor", "site supervisor", [(month_start_day(0) + 1, "Ross Delaney"), (month_start_day(10) + 3, "Kira Matthews")], "biz/construction", CO, str, family="person_role")
    g.fact2("con.insurance", "b_con", "insurance_premium", "public liability premium", [(month_start_day(0) + 20, 14_200), (month_start_day(9) + 20, 16_900)], "biz/construction", CF, lambda v: f"${v:,} per year with Northcrest Insurance", family="price")
    g.fact2("con.plumbing_sub", "b_con", "plumbing_sub", "plumbing subcontractor", [(month_start_day(0) + 1, "Brightwater Plumbing")], "biz/construction", CO, str, family="supplier")
    g.fact("con.strategy", "b_con", "strategy", "tender policy",
           [(month_start_day(0) + 3, "residential builds and renovations under $2m only; no commercial work"), (month_start_day(13) + 9, "residential under $2m plus light commercial fit-outs under $1m; no multi-storey")],
           "biz/construction", CF, str, family="rule", render=lambda e, v, d: f"{e} tender policy (agreed {day_to_date(d)}): {v}.")
    g.fact2("con.pipeline_target", "b_con", "pipeline_target", "pipeline target", [(month_start_day(0) + 4, "$2.5m contracted pipeline at all times"), (month_start_day(12) + 6, "$3.0m contracted pipeline by mid-2026")], "biz/construction", CF, str, family="goal")
    g.fact2("con.margin_target", "b_con", "margin_target", "gross margin target", [(month_start_day(12) + 6, "average gross margin of 14% across 2026 jobs")], "biz/construction", CF, str, family="goal")
    g.fact2("con.margin", "b_con", "gross_margin", "average gross margin", [(month_start_day(q * 3) + 22, R.choice([10.5, 11.2, 12.4, 13.1, 12.8, 11.9])) for q in range(6)], "biz/construction", CF, lambda v: f"{v}%")
    g.fact2("con.safety_target", "b_con", "safety_target", "safety target", [(month_start_day(6) + 2, "zero lost-time injuries for 2026")], "biz/construction", CO, str, family="goal")
    g.fact2("con.incidents", "b_con", "lti_count", "lost-time injuries this year", [(month_start_day(12) + 10, 0), (month_start_day(15) + 4, 1)], "biz/construction", CO, lambda v: f"{v} lost-time injuries")
    stages = ["site establishment", "slab poured", "frame up", "lock-up", "fit-off", "practical completion"]
    places = R.sample(PROJ_PLACES, N_PROJ - 1)
    projects = []
    halyard_prop = props[0]
    hp_name = g.entities[halyard_prop]["aliases"][0]
    for i in range(N_PROJ):
        if i == 0:
            prid, name, al = "proj_owner_reno", f"{hp_name} kitchen and bathroom renovation", [f"the {hp_name} reno", f"{hp_name} job"]
        else:
            pl = places[i - 1]
            prid = "proj_" + pl.lower().replace(" ", "_")
            name = f"{pl} {R.choice(PROJ_TYPES)}"
            al = [f"the {pl} job", pl]
        g.ent(prid, "project", name, al, ["biz/construction"], scope=CO)
        g.edge(prid, "b_con", "project_of", "biz/construction")
        projects.append(prid)
        start = R.randint(0, 8)
        ms = sorted(R.sample(range(start, 17), R.randint(3, 5)))
        g.fact2(f"{prid}.status", prid, "status", "project stage", [(month_start_day(m) + R.randint(2, 25), stages[min(j, 4) if i == 0 else j]) for j, m in enumerate(ms)], "biz/construction", CO, str, family="status")
        budget = R.randint(30, 140) * 10_000 if i else 46_800
        g.fact2(f"{prid}.budget", prid, "contract_value", "contract value", [(month_start_day(start) + 1, budget)], "biz/construction", CF, money_c, family="price")
        cost, cv2 = 0, []
        for j, m in enumerate(ms):
            cost += round(budget * R.uniform(0.12, 0.3) / 100) * 100
            cv2.append((month_start_day(m) + R.randint(2, 25), cost))
        g.fact2(f"{prid}.cost", prid, "cost_to_date", "cost to date", cv2, "biz/construction", CF, money_c, family="cost")
        sp(f"proj_variation:{prid}", S("email", "biz/construction", CF, R.choice([f"Variation on {al[0]}: client added {R.choice(['a skylight', 'upgraded tiles', 'extra power points', 'a butler’s pantry', 'ducted heating'])}, +${R.randint(4, 30)*1000:,}; not yet signed.",
                                                                                  f"Cost blowout warning for {al[0]}: {R.choice(['steel', 'timber', 'windows', 'tiles'])} came in ${R.randint(5, 25)*1000:,} over the allowance."]),
                                       month_start_day(R.randint(12, 16)) + 9, entities=["b_con", prid]))
        sp(f"proj_issue:{prid}", S("note", "biz/construction", CO, R.choice([f"{al[0]}: waiting on engineer sign-off for the retaining wall, crew idle two days.", f"{al[0]}: council inspection failed on stormwater, rework booked.",
                                                                             f"{al[0]}: client slow approving selections, cabinetry order on hold.", f"{al[0]}: roof trusses delayed three weeks by the supplier."]),
                                   month_start_day(R.randint(13, 17)) + 3, entities=["b_con", prid]))
    g.entities[halyard_prop]["partitions"].append("biz/construction")
    g.entities["proj_owner_reno"]["partitions"].append("owner")
    g.edge("proj_owner_reno", halyard_prop, "renovates", "biz/construction")
    g.meta["halyard_prop"] = halyard_prop
    for i, (tn, ttype) in enumerate(R.sample(TENDERS, N_TENDER)):
        tid = f"tender_{i}"
        g.ent(tid, "tender", tn, [tn.split()[0] + " tender"], ["biz/construction"], scope=CF)
        sp(f"tender:{tid}", S("email", "biz/construction", CF, f"Invitation to tender: {tn} ({ttype}). Estimated value ${R.randint(4, 30)*100_000:,}; start {R.choice(['August', 'September', 'October', 'November'])} 2026; "
                                                              f"liquidated damages ${R.choice([500, 800, 1200, 2000, 3500]):,}/day; {R.choice(['single storey', 'two storeys', 'three storeys'])}.",
                              month_start_day(R.randint(15, 17)) + R.randint(1, 20), entities=["b_con", tid]))
    sp("con_capacity", S("note", "biz/construction", CO, "Kira is running every site; can't take another job before September without a second supervisor.", month_start_day(15) + 4, entities=["b_con", "s_kira_matthews"]))
    sp("con_tender_decision", S("meeting", "biz/construction", CF, "Office meeting (Rhea, Dane): tender only where margin is at least 12% and we have supervisor capacity; decline anything with liquidated damages above $1k/day.", month_start_day(12) + 14, entities=["b_con", "p_rhea"]))
    sp("reno_quote_owner", S("email", "biz/construction", CF, f"Quote 24-117: kitchen and bathroom renovation at {g.entities[halyard_prop]['name']} — $46,800 inc GST, 7 weeks, Kira supervising. Client: D. Halloran (related party, arm's length rates applied).",
                             month_start_day(10) + 12, entities=[halyard_prop, "proj_owner_reno", "b_con"]))
    g.special[f"reno_quote:{halyard_prop}"].append(g.special["reno_quote_owner"][0])

    # ================================================================ cafe
    CaO, CaF = "business/cafe/ops", "business/cafe/finance"
    g.meta["cafe_cur"] = {}
    for cat, (label, sups, incs) in CAFE_CATS.items():
        sups = list(sups)
        R.shuffle(sups)
        if cat == "linen":
            sups.remove("Talbot Linen Services"); sups.insert(0, "Talbot Linen Services")
        if cat == "cleaning":
            sups.remove("Sparkline Cleaning"); sups.insert(0, "Sparkline Cleaning")
        if R.random() < 0.5 and cat not in ("linen", "cleaning"):
            vers = [(month_start_day(0) + 1, sups[1]), (month_start_day(R.randint(6, 11)) + 6, sups[0])]
        else:
            vers = [(month_start_day(0) + 1, sups[0])]
        cur = vers[-1][1]
        g.meta["cafe_cur"][cat] = cur
        g.fact2(f"cafe.{cat}_supplier", "b_cafe", f"{cat}_supplier", label, vers, "biz/cafe", CaO, str, family="supplier")
        sp(f"cafe_contract:{cat}", S("email", "biz/cafe", CaO, f"{cur} supply agreement ({label}): {R.choice([6, 12, 24])}-month term from {R.choice(['October 2025', 'January 2026', 'March 2026'])}, {R.choice([14, 30, 60])} days' written notice to terminate, {R.choice(['minimum order applies', 'no minimum order', 'price fixed for the term'])}.",
                                     month_start_day(R.randint(6, 12)) + 6, entities=["b_cafe"]))
        for txt in R.sample(incs, R.randint(1, 3)):
            sp(f"cafe_incident:{cat}", S("chat", "biz/cafe", CaO, txt.format(s=cur.split()[0]), month_start_day(R.randint(13, 17)) + R.randint(1, 25), entities=["b_cafe"]))
        for alt in [s for s in sups if s != cur][:2]:
            sp(f"cafe_quote:{cat}", S("email", "biz/cafe", CaO, f"{alt} quote ({label}): {R.choice(['10% under what we pay now', 'similar price, better delivery window', '3-month trial with no lock-in', 'daily delivery before 6am'])}; {R.choice(['free equipment service', 'credit for spoiled stock', 'local, family-owned', 'needs a 12-month commitment'])}.",
                                      month_start_day(R.randint(14, 17)) + R.randint(1, 20), entities=["b_cafe"]))
    g.fact2("cafe.hours", "b_cafe", "opening_hours", "opening hours", [(month_start_day(0) + 1, "7am–3pm Monday to Saturday, closed Sunday"), (month_start_day(11) + 1, "6:30am–3pm Monday to Saturday, 8am–1pm Sunday")], "biz/cafe", CaO, str)
    g.fact2("cafe.head_barista", "b_cafe", "head_barista", "head barista", [(month_start_day(0) + 1, "Jordan Pike"), (month_start_day(13) + 7, "Mei Tran")], "biz/cafe", CaO, str, family="person_role")
    cov, res, cvv, crr = R.randint(900, 1100), R.randint(30, 45) * 1000, [], []
    for q in range(6):
        if q:
            cov += R.randint(-40, 90); res += R.randint(-6, 10) * 1000
        d = month_start_day(q * 3) + R.randint(5, 20)
        cvv.append((d, cov)); crr.append((d + 3, res))
    g.fact2("cafe.covers", "b_cafe", "weekly_covers", "average weekly covers", cvv, "biz/cafe", CaO, lambda v: f"{v} covers a week", family="count")
    g.fact2("cafe.cash_reserve", "b_cafe", "cash_reserve", "cash reserve", crr, "biz/cafe", CaF, money_c, family="count")
    g.fact2("cafe.revenue_goal", "b_cafe", "revenue_goal", "annual revenue target", [(month_start_day(0) + 5, "$780,000 for calendar 2025"), (month_start_day(12) + 5, "$820,000 for calendar 2026")], "biz/cafe", CaF, str, family="goal")
    g.fact("cafe.distribution_rule", "b_cafe", "distribution_rule", "partner distribution rule",
           [(month_start_day(0) + 5, "any distribution or drawing above $20,000 needs both partners' written sign-off and must leave three months of operating costs in reserve")],
           "biz/cafe", CaF, str, family="rule", render=lambda e, v, d: f"{e} partnership agreement clause: {v}.")
    g.fact2("cafe.covers_target", "b_cafe", "covers_target", "weekly covers target", [(month_start_day(0) + 4, "1,100 covers a week"), (month_start_day(12) + 4, "1,250 covers a week by June 2026")], "biz/cafe", CaO, str, family="goal")
    g.fact2("cafe.waste_target", "b_cafe", "waste_target", "food waste target", [(month_start_day(10) + 4, "cut food waste below 4% of food cost")], "biz/cafe", CaO, str, family="goal")
    g.fact2("cafe.waste", "b_cafe", "food_waste", "food waste share", [(month_start_day(q * 3 + 1) + 12, R.choice([6.8, 6.1, 5.5, 5.2, 4.7, 4.4])) for q in range(6)], "biz/cafe", CaO, lambda v: f"{v}% of food cost")
    sp("cafe_sunday_decision", S("meeting", "biz/cafe", CaO, "Partners (Tomas, Dane): Sunday trading trial approved — 8am to 1pm, two staff, review after three months on covers and wage cost.", month_start_day(10) + 22, entities=["b_cafe", "p_tomas"]))
    sp("cafe_roster", S("note", "biz/cafe", CaO, f"Roster: weekday core is {', '.join(n.split()[0] for n in cafe_staff[1:4])}; {cafe_staff[4].split()[0]} covers weekends; Jordan only two shifts now he's coaching.", month_start_day(14) + 3, entities=["b_cafe", "s_mei_tran", "s_jordan_pike"]))
    sp("cafe_recruit_quote", S("email", "biz/cafe", CaO, "PeopleWorks Hospitality Recruitment: placement fee 12% of first-year salary for a senior barista, shortlist within 10 days.", month_start_day(13) + 1, entities=["b_cafe", "sup_peopleworks"]))
    g.meta["cafe_staff"] = []
    shift_prefs = ["prefers weekday mornings, can't do Sundays (uni)", "wants as many weekend shifts as possible", "only afternoons — school pick-up in the morning",
                   "happy to open at 6:30, hates closing", "max three shifts a week, studying", "keen on more hours, any day", "no Saturdays (plays sport)", "would like to train up on coffee"]
    R.shuffle(shift_prefs)
    for n, spf in zip(cafe_staff, shift_prefs):
        sid = "s_" + n.split()[0].lower() + "_" + n.split()[1].lower()
        g.meta["cafe_staff"].append(sid)
        sp(f"staff_pref:{sid}", S("preference", "biz/cafe", CaO, f"{n.split()[0]} {spf}.", month_start_day(R.randint(10, 16)) + 2, entities=[sid, "b_cafe"]))
        g.fact2(f"{sid}.training_goal", sid, "training_goal", "barista training goal", [(month_start_day(R.randint(9, 13)) + 2, f"{R.choice(['level 2 barista certification', 'latte art assessment', 'food safety supervisor certificate', 'shift supervisor sign-off'])} by {R.choice(['August', 'September', 'October'])} 2026")], "biz/cafe", CaO, str, family="goal")
        sp(f"staff_progress:{sid}", S("note", "biz/cafe", CaO, R.choice([f"{n.split()[0]} training check: passed milk texturing, still working on dial-in consistency.", f"{n.split()[0]} has done the online modules, practical assessment booked.",
                                                                          f"{n.split()[0]} progress: confident on the machine at quiet times, rattled in the rush."]), month_start_day(R.randint(15, 17)) + 5, entities=[sid, "b_cafe"]))
    # coach shift prefs (gym)
    for c in COACHES:
        sid = "s_" + c.split()[0].lower() + "_" + c.split()[1].lower()
        sp(f"coach_pref:{sid}", S("preference", "biz/gym", GO, f"{c.split()[0]} {R.choice(shift_prefs)}.", month_start_day(R.randint(10, 16)) + 2, entities=[sid, "b_gym"]))
    # ---- revenue series
    for b, part, sc, base in (("b_gym", "biz/gym", GF, 210_000), ("b_con", "biz/construction", CF, 820_000), ("b_cafe", "biz/cafe", CaF, 185_000)):
        short = {"b_gym": "gym", "b_con": "con", "b_cafe": "cafe"}[b]
        rev = base
        for q in range(6):
            rev = round(rev * (1 + R.gauss(0.025, 0.06)) / 100) * 100
            d = month_start_day(q * 3 + 3) + R.randint(5, 20) if q < 5 else NOW_DAY - R.randint(0, 3)
            ql = quarter_label(q * 3)
            vers = [(d, rev)]
            if R.random() < 0.35 and q < 5:
                vers.append((d + R.randint(20, 40), round(rev * R.uniform(0.95, 1.04) / 100) * 100))
            g.fact2(f"{short}.revenue.{ql}", b, f"revenue_{ql}", f"revenue for {ql}", vers, part, sc, money_c, kind="series", family="revenue")
    # ---- shared supplier feedback + dual-role notes + commitments
    for sup, notes in (("sup_talbot", [("biz/gym", GO, "b_gym", "Talbot Linen has been reliable all year at the gym — towel deliveries on time, one invoice error fixed same day."),
                                       ("biz/cafe", CaO, "b_cafe", "Talbot linen delivery was short two bags of tea towels; they credited it straight away.")]),
                       ("sup_brightwater", [("biz/construction", CO, "b_con", "Brightwater Plumbing: good work on site but invoices slow; their apprentice no-showed twice."),
                                            ("biz/cafe", CaO, "b_cafe", "Brightwater fixed the grease trap overflow same day — pricey but reliable for the cafe.")]),
                       ("sup_sparkline", [("biz/gym", GO, "b_gym", "Sparkline missed the change rooms twice this month; members complaining."),
                                          ("biz/cafe", CaO, "b_cafe", "Sparkline's night clean at the cafe is spotless, no complaints.")]),
                       ("sup_northcrest", [("biz/construction", CF, "b_con", "Northcrest premium up 19% at renewal; broker says the market is hard for builders."),
                                           ("biz/gym", GF, "b_gym", "Northcrest paid the gym's water-damage claim in ten days — easy process.")])):
        for part, sc, b, txt in notes:
            sp(f"supfb:{sup}:{b}", S("note", part, sc, txt, month_start_day(R.randint(11, 16)) + 2, entities=[sup, b]))
    for sid, b1, b2, desc in DUAL_ROLE:
        nm = g.entities[sid]["name"]
        sp(f"dual:{sid}", S("note", bpart[b1], "business/gym/ops" if b1 == "b_gym" else ("business/cafe/ops" if b1 == "b_cafe" else CO),
                            f"{nm} — {desc}. Watch the hours across both businesses.", month_start_day(R.randint(12, 15)) + 9, entities=[sid, b1, b2]))
    for cid, part, sc, txt, ents in COMMITMENTS:
        sp(f"commit:{cid}", S("meeting" if part.startswith("biz") else "note", part, sc, txt, month_start_day(R.randint(13, 16)) + 11, entities=ents))
    # ---- finance special docs
    for p in props:
        sp(f"refi_email:{p}", S("email", "owner", FI, R.choice([
            f"Hi Dane — Nadia from Clearpath. Ran the numbers on {g.alias(p)}: we could refix at {R.choice(['5.49%', '5.59%', '5.64%', '5.39%'])} for two years and release some equity for the next deal. Break costs look minimal.",
            f"Email from Nadia (Clearpath Finance): lender offering {R.choice(['5.49%', '5.59%', '5.64%'])} to keep {g.alias(p)}; a switch would save a bit monthly and free usable equity.",
            f"Clearpath refinance options for {g.alias(p)}: fixed {R.choice(['5.45%', '5.55%'])} or split loan; valuation would need to be ordered first."]),
            month_start_day(R.randint(13, 17)) + R.randint(1, 20), entities=[p, "p_nadia", "sup_clearpath"], title="Clearpath Finance — refinance option"))
        sp(f"pm_email:{p}", S("email", "owner", FI, R.choice([
            f"From the property manager: comparable rentals near {g.alias(p)} are leasing for $30–50 a week more. Recommend a rent review at renewal, or a light refresh (paint, blinds) to justify it.",
            f"PM update for {g.alias(p)}: two weeks of vacancy between tenants; market feedback says the kitchen is dated. Options: hold the rent, cut it slightly, or freshen up.",
            f"Property manager on {g.alias(p)}: tenant keen to renew if the rent stays put; market says +$25/week is achievable."]),
            month_start_day(R.randint(12, 17)) + R.randint(1, 20), entities=[p], title="Property manager update"))
        sp(f"tenant_issue:{p}", S("email", "owner", FI, R.choice([
            f"Tenant at {g.alias(p)} has asked to keep a small dog; PM suggests a pet bond and a clause.", f"Hot water system at {g.alias(p)} failed — PM has two replacement quotes, $1,900 and $2,600.",
            f"Rent at {g.alias(p)} was ten days late twice this quarter; PM recommends a breach notice.", f"Tenant at {g.alias(p)} wants to break the lease early for a job interstate."]),
            month_start_day(R.randint(14, 17)) + R.randint(1, 20), entities=[p], title="Tenant request"))
        if p != halyard_prop and R.random() < 0.6:
            sp(f"reno_quote:{p}", S("email", "owner", FI, f"Independent builder quote for refreshing {g.alias(p)}: repaint, new blinds and floor coverings — about ${R.randint(14, 26)},{R.randint(1, 9)}00, three weeks.",
                                    month_start_day(R.randint(13, 16)) + 5, entities=[p], title="Builder quote"))
    sp("related_party_policy", S("note", "owner", FI, "Policy if Stonefield works on our own rentals: get one independent quote, invoice at arm's length, and don't let partner time on family jobs eat into paid work. Rhea agreed.", month_start_day(10) + 4, entities=["b_con", "fin_portfolio", "p_rhea"]))
    sp("inv_decision", S("meeting", "owner", FI, "Sat-morning money meeting with Priya: decided no new purchase until the offset is back above the buffer goal; next property must be interstate and under $750k; revisit after the June valuations.", month_start_day(14) + 6, entities=["fin_portfolio", "fin_offset", "p_priya"]))
    sp("inv_decision_old", S("meeting", "owner", FI, "Earlier money meeting: happy to buy again locally this year if yield is above 5%; keep LVR under 70%.", month_start_day(3) + 6, entities=["fin_portfolio", "p_priya"]))
    for h in holds:
        e = g.entities[h]
        sp(f"thesis:{h}", S("note", "owner", FI, R.choice([f"Thesis for {e['name']}: long-term core position, only trim if it gets above 15% of the share portfolio.",
                                                          f"{e['aliases'][1]} — speculative; cap it at a small slice and don't average down.",
                                                          f"Why I own {e['aliases'][1]}: dividends and defensive; happy to hold through volatility.",
                                                          f"{e['aliases'][0]}: bought for the growth story; sell half if the thesis breaks (two bad quarters)."]),
                            month_start_day(R.randint(1, 8)) + 3, entities=[h]))

    # ================================================================ health / training
    HT = "health/training"
    g.ent("goal_squat", "goal", "squat goal", ["squat target", "the squat goal"], ["owner"], scope=HT)
    g.ent("goal_run", "goal", "10k running goal", ["the 10k goal", "running target"], ["owner"], scope=HT)
    g.ent("tr_me", "person_profile", "Dane's training", ["my training", "training"], ["owner"], scope=HT)
    for lift, base in (("squat", 152.5), ("bench", 112.5), ("deadlift", 185.0), ("press", 72.5)):
        v, ver = base, []
        for q in range(6):
            if q:
                v += R.choice([0, 2.5, 5, 5, 7.5])
            ver.append((month_start_day(q * 3) + R.randint(10, 25), v))
        g.fact2(f"train.{lift}_1rm", "tr_me", f"{lift}_1rm", f"{'overhead press' if lift == 'press' else lift} one-rep max", ver, "owner", HT, lambda v: f"{v:g} kg", family="lift")
    g.fact2("train.bodyweight", "tr_me", "bodyweight", "bodyweight", [(month_start_day(q * 3) + 3, round(94 - q * R.uniform(0.3, 0.9), 1)) for q in range(6)], "owner", HT, lambda v: f"{v} kg", family="bodyweight")
    g.fact2("train.program", "tr_me", "program", "training program", [(month_start_day(0) + 2, "5/3/1 Boring But Big"), (month_start_day(6) + 2, "Texas Method"), (month_start_day(12) + 2, "a 12-week conjugate block with Ben")], "owner", HT, str, family="program")
    g.fact2("train.sessions", "tr_me", "sessions_per_week", "sessions per week", [(month_start_day(0) + 2, 4), (month_start_day(5) + 2, 5), (month_start_day(11) + 20, 3), (month_start_day(15) + 2, 4)], "owner", HT, lambda v: f"{v}", family="sessions")
    g.fact2("train.run10k", "tr_me", "run_10k", "10k run time", [(month_start_day(m) + R.randint(5, 20), t) for m, t in ((1, "52:40"), (4, "51:15"), (8, "49:58"), (12, "49:20"), (16, "48:31"))], "owner", HT, str, family="runtime")
    g.fact2("train.coach", "tr_me", "coach", "strength coach", [(month_start_day(0) + 2, "Sasha Novak"), (month_start_day(7) + 12, "Ben Okafor")], "owner", HT, str, family="person_role")
    g.fact2("goal_squat.target", "goal_squat", "target", "squat target", [(month_start_day(0) + 4, "180 kg squat by 31 December 2025"), (month_start_day(12) + 4, "190 kg squat by 30 September 2026")], "owner", HT, str, family="goal")
    g.fact2("goal_run.target", "goal_run", "target", "10k target", [(month_start_day(0) + 4, "sub-50 minute 10k by October 2025"), (month_start_day(10) + 4, "sub-48 minute 10k by August 2026")], "owner", HT, str, family="goal")
    g.fact2("goal.deadlift", "tr_me", "deadlift_goal", "deadlift target", [(month_start_day(0) + 4, "220 kg deadlift by end of 2025"), (month_start_day(12) + 4, "230 kg deadlift by end of 2026")], "owner", HT, str, family="goal")
    g.fact2("goal.bench", "tr_me", "bench_goal", "bench target", [(month_start_day(3) + 4, "130 kg bench by June 2026")], "owner", HT, str, family="goal")
    g.fact2("goal.press", "tr_me", "press_goal", "overhead press target", [(month_start_day(6) + 4, "bodyweight overhead press (90 kg) by 2027")], "owner", HT, str, family="goal")
    g.fact2("goal.bodyweight", "tr_me", "bodyweight_goal", "bodyweight target", [(month_start_day(0) + 4, "get down to 90 kg while keeping strength")], "owner", HT, str, family="goal")
    g.edge("tr_me", "s_ben_okafor", "coached_by", "owner"); g.edge("tr_me", "b_gym", "trains_at", "owner")
    sp("coach_advice", S("note", "owner", HT, "Ben's advice on the stall: drop the top sets for three weeks, add paused squats and box squats, and fix the bracing — sleep is the limiter, not the program.", month_start_day(15) + 12, entities=["tr_me", "s_ben_okafor"]))
    sp("knee_note", S("note", "owner", HT, "Left knee niggle after the long run — physio says patellar tendon irritation; keep squat depth controlled and cut running volume for a fortnight.", month_start_day(13) + 20, entities=["tr_me"]))
    sp("training_clash", S("note", "owner", HT, "Since the cafe opened earlier and I'm doing the 6:30 opens twice a week, my 6am sessions are getting skipped. Need to move training to lunchtime or evenings.", month_start_day(12) + 15, entities=["tr_me", "b_cafe"]))
    sp("run_plan", S("note", "owner", HT, "Running plan: two easy runs and one interval session a week, long run Sunday, building to the 10k time trial.", month_start_day(10) + 6, entities=["tr_me", "goal_run"]))
    sp("shoulder_note", S("note", "owner", HT, "Right shoulder cranky on heavy pressing; Ben says swap to a slight incline and add face pulls.", month_start_day(14) + 2, entities=["tr_me", "s_ben_okafor"]))

    # ================================================================ reading
    RD = "reading"
    g.ent("rd_me", "person_profile", "Dane's reading", ["my reading", "reading list"], ["owner"], scope=RD)
    books = make_books(R) + make_books(R)[:20]
    seen, bl = set(), []
    for b in books:
        if b["title"] not in seen:
            seen.add(b["title"]); b["id"] = f"book_{len(bl):02d}"; bl.append(b)
    books = bl
    for b in books:
        g.ent(b["id"], "book", b["title"], [b["title"].replace("The ", ""), f"the {b['author'].split()[-1]} book"], ["owner"], scope=RD, author=b["author"], genre=b["genre"])
    g.fact2("reading.goal", "rd_me", "goal", "reading goal", [(month_start_day(0) + 1, "20 books in 2025"), (month_start_day(12) + 1, "24 books in 2026")], "owner", RD, str, family="goal")
    g.fact2("reading.finished", "rd_me", "books_finished_ytd", "books finished this year", [(month_start_day(q * 3) + 26, n) for q, n in enumerate([4, 9, 14, 19, 5, 11])], "owner", RD, lambda v: f"{v} books", family="reading_count")
    cur = R.sample(books, 6)
    g.fact2("reading.current", "rd_me", "currently_reading", "currently reading", [(month_start_day(q * 3) + 2, f"{b['title']} by {b['author']}") for q, b in enumerate(cur)], "owner", RD, str, family="reading_now")
    g._books = books
    genres = sorted({b["genre"] for b in books})
    likes = R.sample([x for x in genres if x not in ("fantasy", "business")], 4)
    g.meta["likes"] = likes
    for gname in likes:
        sp(f"genre_like:{gname}", S("preference", "owner", RD, R.choice([f"I really enjoy {gname} — more of that please.", f"Always happy with a good {gname} book.", f"Note: {gname} is a reliable win for me."]), month_start_day(R.randint(0, 10)) + 3, entities=["rd_me"]))
        g.special["reading_pref_current"].append(g.special[f"genre_like:{gname}"][0])
    g.special["reading_pref_stale"].append(S("preference", "owner", RD, "Love fantasy series, the longer the better.", month_start_day(1) + 3, entities=["rd_me"]))
    for txt, gn in (("Gone right off fantasy — couldn't finish the last two. Skip those.", "fantasy"), ("Business books feel like padded blog posts to me; avoid unless someone I trust insists.", "business")):
        iid = sp(f"genre_dislike:{gn}", S("preference", "owner", RD, txt, month_start_day(R.randint(6, 11)) + 3, entities=["rd_me"]))
        g.special["reading_pref_current"].append(iid)
    lovedb = [b for b in books if b["genre"] in likes][:10]
    for b in lovedb:
        iid = sp("book_loved", S("preference", "owner", RD, f"Finished {b['title']} by {b['author']} — loved it. Want more from {b['author'].split()[-1]}.", month_start_day(R.randint(2, 17)) + 9, entities=["rd_me", b["id"]]))
        g.special[f"book_loved_genre:{iid}"] = [b["genre"]]
    S("note", "owner", RD, "Wishlist from friends: " + ", ".join(f"{b['title']} ({b['author']})" for b in R.sample(books, 5)) + ".", month_start_day(16) + 2, entities=["rd_me"])

    # ================================================================ family
    FL = "family/leisure"
    g.fact2("mila.activity", "p_mila", "activities", "activities", [(month_start_day(0) + 20, "swim squad Tue/Thu 5:45am and Saturday 7am"), (month_start_day(9) + 6, "water polo Mon/Wed 4:30pm and swim squad Saturday 7am")], "household", FL, str, family="activity")
    g.fact2("theo.activity", "p_theo", "activities", "activities", [(month_start_day(0) + 20, "soccer training Wednesday 5pm, games Saturday morning"), (month_start_day(7) + 3, "soccer Wednesday 5pm and Saturday, basketball Friday 6pm")], "household", FL, str, family="activity")
    g.fact2("ruby.activity", "p_ruby", "activities", "activities", [(month_start_day(0) + 20, "piano lesson Thursday 4pm"), (month_start_day(10) + 3, "piano Thursday 4pm and gymnastics Saturday 9am")], "household", FL, str, family="activity")
    g.fact2("mila.swim_pb", "p_mila", "swim_pb", "100m freestyle personal best", [(month_start_day(m) + R.randint(5, 20), t) for m, t in ((1, "1:09.8"), (5, "1:08.1"), (10, "1:06.9"), (15, "1:05.6"))], "household", FL, str, family="pb")
    g.fact2("mila.swim_goal", "p_mila", "swim_goal", "regional qualifying goal", [(month_start_day(2) + 3, "100m freestyle under 1:05.0 to qualify for regionals in August 2026")], "household", FL, str, family="goal")
    g.fact2("theo.goal", "p_theo", "basketball_goal", "basketball goal", [(month_start_day(9) + 3, "make the under-14 rep team at the October trials")], "household", FL, str, family="goal")
    g.fact2("ruby.goal", "p_ruby", "piano_goal", "piano goal", [(month_start_day(8) + 3, "pass the grade 3 piano exam in November")], "household", FL, str, family="goal")
    g.fact2("family.holiday_budget", "fin_household", "holiday_budget", "holiday budget", [(month_start_day(0) + 9, "$6,000 for the year"), (month_start_day(12) + 9, "$8,500 for 2026 including the September trip")], "household", FL, str)
    g.fact2("family.holiday_fund", "fin_household", "holiday_fund", "holiday savings balance", [(month_start_day(q * 3 + 1) + 5, 1500 + q * R.randint(9, 13) * 100) for q in range(6)], "household", FL, money_c, family="cash")
    g.fact2("family.school_break", "p_dane", "school_break", "spring school holidays", [(month_start_day(12) + 15, "19 September to 5 October 2026")], "household", FL, str)
    sp("mila_coach_note", S("note", "household", FL, "Mila's coach: on current trend she should go under 1:05 by mid-year if she keeps the Saturday sessions and adds one dryland session.", month_start_day(15) + 12, entities=["p_mila"]))
    sp("theo_coach_note", S("note", "household", FL, "Theo's coach says his defence is rep standard; needs to work on his left hand and come to the Sunday skills clinic.", month_start_day(15) + 2, entities=["p_theo"]))
    sp("ruby_teacher_note", S("note", "household", FL, "Ruby's piano teacher: pieces are nearly there, scales need daily practice; mock exam in September.", month_start_day(15) + 9, entities=["p_ruby"]))
    for i, (name, why, kid) in enumerate(PLACES):
        pid = "pl_" + name.split()[0].lower()
        g.ent(pid, "place", name, [name.split()[0]], ["household"], scope=FL)
        sp(f"place:{kid}", S("preference", "household", FL, f"{name}: {why}.", month_start_day(R.randint(0, 16)) + 3, entities=[pid, kid]))
    for kid, txt in (("p_mila", "Mila wants weekends free for water polo friends now — swimming carnivals are a no."), ("p_theo", "Theo is obsessed with basketball; anything with a hoop wins."),
                     ("p_ruby", "Ruby loves animals and anything crafty; gets tired after about two hours out.")):
        sp(f"kid_pref:{kid}", S("preference", "household", FL, txt, month_start_day(R.randint(9, 16)) + 5, entities=[kid]))
    S("preference", "household", FL, "Mila used to love swim carnivals and early training.", month_start_day(2) + 5, entities=["p_mila"])
    sp("priya_food_pref", S("preference", "household", FL, "Priya: loves share plates and Japanese; not into steakhouses; prefers somewhere quiet enough to talk.", month_start_day(8) + 5, entities=["p_priya"]))
    for r_ in RESTAURANTS:
        g.ent("rest_" + r_.split()[0].lower(), "place", r_, [r_.split()[0]], ["household"], scope=FL)
    sp("restaurant_pref", S("preference", "household", FL, "Maple & Fig and Koto Izakaya are our two go-to places for special occasions.", month_start_day(12) + 5, entities=["rest_maple", "rest_koto"]))
    for occ, txt in OCCASIONS:
        sp(f"occasion:{occ}", S("preference", "household", FL, txt, month_start_day(R.randint(6, 16)) + 5, entities=["p_dane", "p_priya"]))
    sp("allergy", S("preference", "household", FL, "Ruby has a tree-nut allergy — always check menus.", month_start_day(0) + 25, entities=["p_ruby"]))
    sp("holiday_pref", S("preference", "household", FL, "Holiday lessons learned: beach + cabin beats cold lodges; max 4 hours driving with the kids; book somewhere with a pool.", month_start_day(11) + 10, entities=["p_dane", "p_priya"]))
    sp("holiday_pref", S("preference", "household", FL, "Coral Bay Holiday Park: best family holiday so far — cabins by the beach.", month_start_day(4) + 10, entities=["p_dane"]))
    for i, (tn, td) in enumerate(TRIPS):
        sp(f"trip:{i}", S("email", "household", FL, f"Trip option for the September break — {tn}: {td}.", month_start_day(R.randint(14, 17)) + 5, entities=["p_dane", "p_priya"]))
    sp("priya_gym_pause", S("note", "household", FL, "Priya's thinking of pausing her gym membership over winter — says she's not getting there.", month_start_day(15) + 22, entities=["p_priya", "b_gym"]))
    sp("priya_member_note", S("log", "member/m03", "business/gym/members", "Priya Halloran attendance: 3 visits in the last 8 weeks; asked about freezing the membership.", month_start_day(16) + 3, entities=["p_priya", "b_gym"]))

    # ================================================================ free text
    build_mentions2(g)
    build_filler2(g, props, holds, projects, cafe_staff)
    build_media2(g, props, projects)
    g.meta.update(props=props, holds=holds, projects=projects, cafe_staff_names=cafe_staff)
    return g


def build_mentions2(g: Gen2):
    R = g.rng
    chat_of = {"owner": "note", "household": "chat", "biz/gym": "chat", "biz/construction": "chat", "biz/cafe": "chat", "public/gym": "note"}
    for key, k in list(g.keys.items()):
        vers = k["versions"]
        for vid in vers:
            f = g.by_id[vid]
            lo = f["valid_from"]
            hi = f["valid_to"] if f["valid_to"] is not None else NOW_DAY
            if hi - lo < 2:
                continue
            n = R.choice([0, 1, 1, 2, 2]) if len(vers) > 1 else R.choice([0, 0, 1])
            for _ in range(n):
                d = R.randint(lo + 1, max(lo + 1, hi - 1))
                part = k["partition"]
                typ = "log" if part.startswith("member/") else chat_of.get(part, "note")
                g.mention2(key, vid, d, type_=typ)


def build_filler2(g: Gen2, props, holds, projects, cafe_staff):
    R = g.rng
    people_gym = [c.split()[0] for c in COACHES] + ["Lachlan"]
    people_cafe = [n.split()[0] for n in cafe_staff] + ["Tomas"]
    people_con = ["Ross", "Kira", "Dev", "Sione", "Gus", "Wade", "Rhea"]
    books = g._books

    def days(n):
        return sorted(R.randint(0, NOW_DAY) for _ in range(n))

    ex = ["squats", "bench", "deadlifts", "overhead press", "rows", "pull-ups", "lunges", "intervals", "easy run", "tempo run", "sled pushes", "kettlebell swings"]
    for d in days(560):
        a, b = R.sample(ex, 2)
        g.add("log", "owner", "health/training", R.choice([
            f"Session: {a} {R.randint(3,5)}x{R.randint(3,8)}, then {b}. RPE {R.randint(6,9)}.", f"Trained {a} and {b}. Felt {R.choice(['flat', 'strong', 'tired', 'good', 'sore'])}.",
            f"{a.capitalize()} day — top set moved well, {b} accessories after.", f"Short session, {a} only. {R.choice(['Slept badly.', 'Busy day.', 'Back felt tight.', 'Good energy.'])}",
            f"Garmin says recovery {R.randint(20, 95)}%; did {a} anyway.", f"Deload week: light {a}, mobility, {b}."]), d, entities=["tr_me"])
    items_c = ["oat milk", "takeaway cups", "lids", "banana bread", "sourdough", "eggs", "decaf", "chai", "napkins", "almond milk", "croissants", "spinach", "avocados"]
    for d in days(760):
        g.add("chat", "biz/cafe", R.choice(["business/cafe/ops", "business/cafe/ops", "business/cafe/finance"]), R.choice([
            f"{R.choice(people_cafe)}: can someone swap my {R.choice(['Tue', 'Wed', 'Thu', 'Sat', 'Sun'])} shift?", f"{R.choice(people_cafe)}: we're low on {R.choice(items_c)}, ordering more.",
            f"Busy morning, {R.randint(150, 320)} covers by 11.", f"Customer feedback: loved the {R.choice(['flat white', 'smashed avo', 'banana bread', 'chai', 'brekkie burrito'])}.",
            f"{R.choice(people_cafe)}: grinder needs a clean, coffee tasting bitter.", f"Delivery of {R.choice(items_c)} arrived and checked in.",
            f"Till was ${R.randint(-20, 20)} out at close, recounted.", f"Supplier invoice for {R.choice(items_c)} paid.", f"Wages this week came to about ${R.randint(5, 9)},{R.randint(100, 999)}.",
            f"Coffee machine service booked for {R.choice(['Monday', 'next week', 'Friday arvo'])}.", f"Google review: {R.randint(3, 5)} stars, '{R.choice(['friendly staff', 'slow at lunch', 'best coffee in town', 'a bit pricey'])}'."]), d, entities=["b_cafe"])
    for d in days(760):
        g.add(R.choice(["chat", "log"]), "biz/gym", R.choice(["business/gym/ops", "business/gym/ops", "business/gym/finance"]), R.choice([
            f"{R.choice(people_gym)}: 6am class had {R.randint(8, 22)} in it.", f"{R.choice(people_gym)}: rower {R.randint(1, 6)} making a noise, tagged out.",
            f"New member sign-ups this week: {R.randint(2, 11)}.", f"{R.choice(people_gym)}: covering {R.choice(['Tue', 'Thu', 'Sat'])} HIIT for {R.choice(people_gym)}.",
            f"Cleaning roster updated, {R.choice(people_gym)} on Sunday.", f"Cancellations this week: {R.randint(0, 6)}; reasons mostly {R.choice(['moving', 'cost', 'injury', 'not using it'])}.",
            f"Direct debits failed: {R.randint(1, 9)}, follow-up emails sent.", f"Towels delivered, {R.randint(4, 10)} bags.", f"{R.choice(people_gym)}: dumbbell rack needs reorganising.",
            f"Power bill for the gym came in at ${R.randint(1, 3)},{R.randint(100, 999)}.", f"Instagram post on the {R.choice(['deadlift challenge', 'new timetable', 'member of the month'])} got {R.randint(40, 400)} likes."]), d, entities=["b_gym"])
    for d in days(130):
        g.add("note", "public/gym", "business/gym/ops", R.choice(["Reminder: please re-rack your weights.", "Public holiday hours: 8am–12pm.", f"Challenge of the month: {R.choice(['1000 burpees', '50km row', 'plank ladder'])}.",
                                                                  "Lost property box is overflowing — collect by Friday.", "Mobility workshop this Sunday, free for members."]), d, entities=["b_gym"])
    for m in MEMBER_IDS2:
        eid = "p_priya" if m == "m03" else f"mem_{m}"
        for d in days(22):
            g.add("log", f"member/{m}", "business/gym/members", R.choice([f"Checked in at {R.choice(['5:58am', '6:31am', '12:10pm', '5:45pm', '6:02pm'])}.", f"Workout logged: {R.choice(ex)} and {R.choice(ex)}.",
                                                                        f"Booked {R.choice(['strength', 'HIIT', 'mobility', 'team WOD', 'beginners'])} class.", f"Body comp scan: {R.randint(14, 32)}% body fat."]), d, entities=[eid])
    pents = [g.entities[p] for p in projects]
    for d in days(860):
        p = R.choice(pents)
        g.add(R.choice(["log", "chat"]), "biz/construction", R.choice(["business/construction/ops"] * 3 + ["business/construction/finance"]), R.choice([
            f"Site diary {p['aliases'][0]}: {R.choice(people_con)} on site, {R.choice(['rain delay', 'framing progressing', 'waiting on inspection', 'plumber rough-in', 'electrician on site', 'skip bin swapped'])}.",
            f"{R.choice(people_con)}: concrete pour at {p['aliases'][0]} {R.choice(['booked', 'postponed', 'done'])}.", f"Variation request on {p['aliases'][0]}: client wants {R.choice(['extra power points', 'a bigger window', 'different tiles', 'a skylight'])}.",
            f"Invoice sent for {p['aliases'][0]} progress claim {R.randint(2, 6)}.", f"Safety walk at {p['aliases'][0]}: {R.choice(['all good', 'missing edge protection fixed', 'housekeeping needs work'])}.",
            f"Timber delivery for {p['aliases'][0]} {R.choice(['arrived', 'short by 20 lengths', 'delayed a day'])}.", f"{R.choice(people_con)}: need the {R.choice(['scissor lift', 'laser level', 'compactor'])} back by Friday."]), d, entities=["b_con", p["id"]])
    for d in days(950):
        kid = R.choice(["Mila", "Theo", "Ruby"])
        g.add("chat", "household", "family/leisure", R.choice([
            f"Can you grab {kid} from {R.choice(['school', 'training', 'a friend’s place'])} at {R.choice(['3:15', '4:30', '5:45'])}?", f"Groceries: {R.choice(['milk', 'bread', 'apples', 'pasta', 'yoghurt'])}, {R.choice(['eggs', 'rice', 'chicken', 'cheese'])}.",
            f"{kid} has a {R.choice(['school excursion', 'dentist appointment', 'birthday party', 'mufti day'])} on {R.choice(['Tuesday', 'Friday', 'Saturday'])}.", f"Dinner plan: {R.choice(['tacos', 'stir fry', 'pasta bake', 'roast chook', 'pizza night'])}.",
            f"{kid} needs new {R.choice(['shoes', 'goggles', 'a uniform', 'a library bag'])}.", f"Weekend? Maybe {R.choice(['the beach', 'the park', 'a movie', 'the markets', 'grandma’s'])}.",
            f"Reminder: {R.choice(['bins out tonight', 'car rego due', 'school fees', 'swim fees'])}."]), d, entities=["p_dane"])
    pe = [g.entities[p] for p in props]; he = [g.entities[h] for h in holds]
    for d in days(420):
        p = R.choice(pe); h = R.choice(he)
        g.add(R.choice(["note", "email"]), "owner", "finance/investments", R.choice([
            f"Rental statement for {p['aliases'][0]}: rent received, management fee deducted, {R.choice(['no maintenance', 'gutter clean', 'tap washer replaced', 'smoke alarm check'])}.",
            f"Council rates notice for {p['aliases'][0]} — due in 30 days.", f"Read an article on {R.choice(['interest rates', 'rental vacancy', 'regional growth', 'land tax'])}; worth watching.",
            f"{h['name']} announced {R.choice(['results', 'a dividend', 'a capital raise', 'a CEO change'])}.", f"Insurance renewal for {p['aliases'][0]} — premium {R.choice(['up a bit', 'flat', 'up 9%'])}.",
            f"Maintenance request at {p['aliases'][0]}: {R.choice(['dishwasher', 'hot water', 'fence', 'garage door'])}.", f"Broker newsletter: {R.choice(['rates on hold', 'APRA tweaks', 'fixed rates falling'])}."]), d, entities=[p["id"], h["id"]])
    for d in days(280):
        b = R.choice(books)
        g.add("note", "owner", "reading", R.choice([f"Highlight from {b['title']}: \"{R.choice(['what we notice becomes our world', 'every map is a lie of omission', 'patience is a strategy', 'the river does not hurry'])}\".",
                                                    f"Halfway through {b['title']}, {R.choice(['slow going', 'gripping', 'not sure yet'])}.", f"{b['author']} interview on a podcast — interesting on {R.choice(['craft', 'research', 'history'])}."]), d, entities=[b["id"], "rd_me"])
    for d in days(380):
        b, part, sc = R.choice([("b_gym", "biz/gym", "business/gym/finance"), ("b_cafe", "biz/cafe", "business/cafe/finance"), ("b_con", "biz/construction", "business/construction/finance")])
        g.add("email", part, sc, R.choice([f"BAS reminder for {g.entities[b]['name']} — lodge by the 28th.", f"Bank feed: {g.entities[b]['aliases'][0]} account reconciled for the month.",
                                           f"Accountant: please send {g.entities[b]['aliases'][0]} receipts for the quarter.", f"Software subscription renewal for {g.entities[b]['aliases'][0]}.",
                                           f"Supplier statement for {g.entities[b]['aliases'][0]} — {R.randint(2, 9)} invoices outstanding."]), d, entities=[b])


def build_media2(g: Gen2, props, projects):
    R = g.rng

    def media(kind, partition, scope, caption, day, origin, entities, tag, origin_only=False, ocr="", transcript=""):
        text = " ".join(x for x in (caption, ocr, transcript) if x).strip()
        iid = g.add(kind, partition, scope, text, day, entities=entities, tags=("mm_target", tag),
                    media=dict(caption=caption, ocr=ocr, transcript=transcript, origin=origin, origin_only=origin_only))
        g.special[tag].append(iid)
        return iid

    defects = ["hairline crack along the edge of the slab", "water pooling at the base of the wall", "gap between the window frame and the cladding",
               "chipped tile near the shower recess", "sagging gutter at the back corner", "rust stains under the balcony", "uneven skirting in the hallway"]
    stages_ph = ["frame inspection", "slab pour", "roof sheeting", "lock-up walkaround"]
    for p in projects:
        e = g.entities[p]
        for i, dfx in enumerate(R.sample(defects, 2)):
            oo = i == 0
            media("image", "biz/construction", "business/construction/ops", dfx if oo else f"{e['aliases'][0]}: {dfx}", month_start_day(R.randint(6, 17)) + 3,
                  dict(folder=f"Stonefield/Sites/{e['name']}/Defects", album="", chat="Stonefield office", shared_by=R.choice(["Kira Matthews", "Ross Delaney"])), ["b_con", p], f"mm_defect:{p}:{i}", oo)
        st = R.choice(stages_ph)
        media("image", "biz/construction", "business/construction/ops", f"{st} photo", month_start_day(R.randint(8, 17)) + 6,
              dict(folder=f"Stonefield/Sites/{e['name']}/Progress", album="", chat="", shared_by="Kira Matthews"), ["b_con", p], f"mm_progress:{p}", True)
        g.special[f"mm_progress_stage:{p}"] = [st]
    for i, topic in enumerate(["membership pricing tiers", "summer timetable", "recovery room layout", "member challenge leaderboard", "coach roster", "marketing plan"]):
        oo = i % 2 == 0
        ocr = {"membership pricing tiers": "Tier A 29/wk  Tier B 35/wk  Unlimited 42/wk  student -15%", "summer timetable": "5:30 STR  6:30 STR  12:10 EXPRESS  6PM HIIT",
               "recovery room layout": "sauna | cold plunge x2 | compression boots | stretch zone", "member challenge leaderboard": "1. KR 412  2. MJ 398  3. TP 377",
               "coach roster": "MON Sasha/Ben  TUE Imogen  WED Raf/Corey", "marketing plan": "Q3: referral promo, school holiday kids class, Insta reels x3/wk"}[topic]
        media("image", "biz/gym", "business/gym/ops", "whiteboard photo" if oo else f"whiteboard: {topic}", month_start_day(R.randint(6, 16)) + 9,
              dict(folder="", album="", chat="IronBark partners", shared_by="Lachlan Moore", adjacent_text=f"from today's partners meeting re {topic}" if oo else ""), ["b_gym"], f"mm_whiteboard:{i}", oo, ocr=ocr)
    for lift in ("squat", "bench", "deadlift", "press"):
        tr = {"squat": "hips below parallel, knees tracking out, good brace", "bench": "touch point a bit high, keep the arch",
              "deadlift": "bar drifting forward off the floor, lats tighter", "press": "ribs flaring, squeeze the glutes"}[lift]
        for i in range(2):
            oo = i == 0
            media("video_segment", "owner", "health/training", "form check" if oo else f"{lift} form check", month_start_day(R.randint(4, 17)) + 2,
                  dict(folder="", album=f"Training/Form checks/{lift.capitalize()}", chat="", shared_by="Ben Okafor"), ["tr_me", "s_ben_okafor"], f"mm_form:{lift}:{i}", oo, transcript=f"Coach: {tr}")
    for p in props:
        e = g.entities[p]
        oo = R.random() < 0.5
        vh = g.by_id[g.head(f"{p}.valuation")]
        media("page", "owner", "finance/investments", "page 1 of 6" if oo else f"Valuation report — {e['name']}", vh["valid_from"] + 2,
              dict(folder=f"Investments/{e['name']}/Valuations", album="", chat="", shared_by="Nadia Ferris"), [p], f"mm_valreport:{p}", oo,
              ocr="Market value assessment. Comparable sales. Valuer's certificate." if oo else f"Market value assessment {vh['value_str']}")
        rooms = R.sample(["kitchen", "living room", "back yard", "main bedroom", "bathroom", "front facade"], 2)
        for i, room in enumerate(rooms):
            oo = i == 0
            media("image", "owner", "finance/investments", room if oo else f"{e['aliases'][0]} {room}", month_start_day(R.randint(8, 16)) + 7,
                  dict(folder=f"Investments/{e['name']}/Listing photos", album="", chat="", shared_by="Harbourline Property Management"), [p], f"mm_listing:{p}:{i}", oo)
            g.special[f"mm_listing_room:{p}:{i}"] = [room]
    for kid, evs in (("p_ruby", [("piano recital", "on stage in the blue dress"), ("gymnastics display", "on the beam, arms out")]),
                     ("p_mila", [("regional swim meet", "diving off the blocks, lane 4"), ("water polo final", "team photo with medals")]),
                     ("p_theo", [("basketball grand final", "team holding the trophy"), ("soccer presentation night", "holding the best-and-fairest certificate")])):
        for j, (ev, desc) in enumerate(evs):
            for i in range(3):
                oo = i < 2
                media("image", "household", "family/leisure", desc if oo else f"{g.entities[kid]['name']} {ev}: {desc}", month_start_day(R.randint(12, 17)) + 6,
                      dict(folder="", album=f"{g.entities[kid]['name']} — {ev}", chat="Halloran family", shared_by="Priya Halloran"), [kid], f"mm_family:{kid}:{j}", oo)
            g.special[f"mm_family_ev:{kid}:{j}"] = [ev]
    receipts = [("biz/cafe", "business/cafe/ops", "b_cafe", "Copperleaf/Receipts/2026", "Grinder burr replacement $640 + labour", "grinder repair"),
                ("biz/gym", "business/gym/ops", "b_gym", "IronBark/Receipts/2026", "Cable machine pulley service $380", "cable machine service"),
                ("biz/construction", "business/construction/finance", "b_con", "Stonefield/Receipts/2026", "Laser level hire 3 days $210", "laser level hire")]
    for part, sc, b, folder, ocr, what in receipts:
        for i in range(2):
            oo = i == 0
            media("page", part, sc, "receipt" if oo else f"{g.entities[b]['name']} receipt", month_start_day(R.randint(12, 17)) + 4,
                  dict(folder=folder, album="", chat="", shared_by=R.choice(["Tomas Abiodun", "Lachlan Moore", "Rhea Castell"])), [b], f"mm_receipt:{b}:{i}", oo, ocr=ocr if i == 0 else ocr.split("$")[0])
    for i, board in enumerate(["breakfast menu", "lunch specials", "drinks and pricing", "kids menu"]):
        oo = i != 1
        ocr = {"breakfast menu": "smashed avo 19 | big breakfast 24 | granola 14", "lunch specials": "chicken burger 21 | soup of the day 15",
               "drinks and pricing": "flat white 5.2 | oat +0.8 | cold brew 6.5", "kids menu": "babycino 2 | toastie 8 | pancakes 10"}[board]
        media("image", "biz/cafe", "business/cafe/ops", "chalkboard" if oo else f"Copperleaf {board}", month_start_day(R.randint(10, 16)) + 3,
              dict(folder="Copperleaf/Menu/2026", album="", chat="Copperleaf team", shared_by="Tomas Abiodun", adjacent_text=f"new {board} board"), ["b_cafe"], f"mm_menu:{i}", oo, ocr=ocr)
    # distractor media
    gen_caps = ["photo", "IMG", "screenshot", "pic", "video clip", "scan", "photo of the whiteboard", "progress photo", "receipt", "form check", "page 2",
                "family photo", "selfie", "view from the site", "chalkboard", "kitchen", "back yard"]
    folders = {"owner": ["Investments/Misc", "Training/Progress", "Reading/Covers", "Camera Roll"], "household": ["Family/Camera Roll", "Family/School", "Family/Holidays"],
               "biz/gym": ["IronBark/Marketing", "IronBark/Equipment", "IronBark/Receipts/2025"],
               "biz/construction": [f"Stonefield/Sites/{g.entities[p]['name']}/Progress" for p in projects] + ["Stonefield/Receipts/2025"],
               "biz/cafe": ["Copperleaf/Menu", "Copperleaf/Receipts/2025", "Copperleaf/Social"]}
    scope_of = {"owner": ["finance/investments", "health/training", "reading"], "household": ["family/leisure"], "biz/gym": ["business/gym/ops"],
                "biz/construction": ["business/construction/ops"], "biz/cafe": ["business/cafe/ops"]}
    for _ in range(1800):
        part = R.choice(list(folders))
        kind = R.choice(["image", "image", "image", "video_segment", "page"])
        cap = R.choice(gen_caps)
        if R.random() < 0.4:
            cap += " " + R.choice(["morning", "after", "before", "v2", "close-up", "wide", "draft", "old"])
        ocr = R.choice(["", "", "Total $" + str(R.randint(12, 900)), "Invoice", "Tax invoice GST", "Page " + str(R.randint(1, 9))]) if kind == "page" else ""
        tr = R.choice(["", "talking through the set", "walk-through of the site", "kids laughing"]) if kind == "video_segment" else ""
        text = " ".join(x for x in (cap, ocr, tr) if x)
        g.add(kind, part, R.choice(scope_of[part]), text, R.randint(0, NOW_DAY), entities=[], tags=("mm_filler",),
              media=dict(caption=cap, ocr=ocr, transcript=tr, origin_only=False,
                         origin=dict(folder=R.choice(folders[part]), album="", chat=R.choice(["", "", "Halloran family", "Copperleaf team", "IronBark partners", "Stonefield office"]) if part != "owner" else "",
                                     shared_by=R.choice(["Dane Halloran", "Priya Halloran", "Lachlan Moore", "Kira Matthews", "Tomas Abiodun", ""]))))


# ================================================================ main
def main(seed: int = 1, out_root: str = DATA2):
    from . import tasks2
    g = build2(seed)
    ids = identities2()
    for m, nm in g.meta["member_names"].items():
        ids[f"member_{m}"]["name"] = nm
    g.identities = ids
    tasks2.build_tasks2(g, seed)
    out = os.path.join(out_root, f"s{seed}")
    os.makedirs(out, exist_ok=True)
    write_jsonl(os.path.join(out, "items.jsonl"), g.items)
    write_jsonl(os.path.join(out, "entities.jsonl"), g.entities.values())
    write_jsonl(os.path.join(out, "edges.jsonl"), g.edges)
    write_jsonl(os.path.join(out, "keys.jsonl"), g.keys.values())
    write_jsonl(os.path.join(out, "tasks.jsonl"), g.tasks)
    meta = dict(version="0.2", seed=seed, now_day=NOW_DAY, identities=ids, scopes=SCOPES, partitions=PARTITIONS2,
                coach_spec=g.meta["coach_spec"], halyard_prop=g.meta["halyard_prop"])
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    return g


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    g = main(a.seed)
    from collections import Counter
    print(len(g.items), "items;", len(g.entities), "entities;", len(g.keys), "keys;", len(g.tasks), "tasks")
    print(Counter(i["type"] for i in g.items))
