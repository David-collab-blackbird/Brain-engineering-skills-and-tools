"""BrainBench v0 — synthetic multi-domain world generator.

Everything is fictional and generated from a seed. Gold labels are exact by construction:
every task records the item IDs it needs, and every fact version records its validity window
and supersession pointers.

Run:  python -m bb.world  (writes data/*.jsonl and data/README.md)
"""
from __future__ import annotations

import json
import os
import random
from collections import defaultdict

from .common import (DATA_DIR, NOW_DAY, day_to_date, month_name, month_start_day,
                     quarter_label, write_jsonl)

N_MONTHS = 18

# ---------------------------------------------------------------- identities / ACL
MEMBER_IDS = [f"m{i:02d}" for i in range(1, 13)]
PARTITIONS = ["owner", "household", "biz/gym", "biz/construction", "biz/cafe", "public/gym"] + [
    f"member/{m}" for m in MEMBER_IDS]

IDENTITIES = {
    "owner": {"name": "Dane Halloran", "tier": "owner", "partitions": list(PARTITIONS)},
    "household": {"name": "Priya Halloran", "tier": "household",
                  "partitions": ["household", "member/m03", "public/gym"]},
    "partner_gym": {"name": "Lachlan Moore", "tier": "partner",
                    "partitions": ["biz/gym", "public/gym"] + [f"member/{m}" for m in MEMBER_IDS]},
    "partner_construction": {"name": "Rhea Castell", "tier": "partner",
                             "partitions": ["biz/construction", "public/gym"]},
    "partner_cafe": {"name": "Tomas Abiodun", "tier": "partner", "partitions": ["biz/cafe", "public/gym"]},
}
for _m in MEMBER_IDS:
    IDENTITIES[f"member_{_m}"] = {"name": None, "tier": "member",
                                  "partitions": [f"member/{_m}", "public/gym"]}

SCOPES = {
    "finance/investments": "investment properties portfolio holdings shares etf valuation loan mortgage refinance equity lvr strategy rent tenant property manager broker",
    "finance/personal": "cash offset buffer savings borrowing capacity household budget spending",
    "business/gym/ops": "ironbark gym coaches classes members equipment timetable staff towels",
    "business/gym/finance": "ironbark gym revenue membership numbers price lease rent target",
    "business/gym/members": "member program plan coach personal best check-in",
    "business/construction/ops": "stonefield builders site slab frame supervisor concrete subcontractor project crew",
    "business/construction/finance": "stonefield revenue pipeline tender insurance quote margin",
    "business/cafe/ops": "copperleaf cafe coffee beans milk barista roster hours supplier delivery covers",
    "business/cafe/finance": "copperleaf cafe revenue cash reserve target distribution",
    "health/training": "training squat bench deadlift program coach run 10k bodyweight lift session",
    "family/leisure": "kids mila theo ruby swim soccer piano holiday weekend restaurant priya school",
    "reading": "books reading novel author genre finished currently reading",
}


class Gen:
    def __init__(self, seed: int = 20261023):
        self.rng = random.Random(seed)
        self.items: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.entities: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.keys: dict[str, dict] = {}
        self.tag: dict[str, list[str]] = defaultdict(list)
        self.tasks: list[dict] = []
        self._n = 0

    # ------------------------------------------------------------ primitives
    def ent(self, eid, kind, name, aliases, partitions, scope=None, **extra):
        self.entities[eid] = dict(id=eid, kind=kind, name=name, aliases=[name] + list(aliases),
                                  partitions=list(partitions), scope=scope, **extra)
        return eid

    def edge(self, a, b, rel, partition):
        self.edges.append(dict(src=a, dst=b, rel=rel, partition=partition))

    def alias(self, eid):
        return self.rng.choice(self.entities[eid]["aliases"])

    def add(self, type_, partition, scope, text, day, entities=(), title=None, fact_refs=(),
            tags=(), **extra):
        self._n += 1
        iid = f"it{self._n:05d}"
        day = int(min(max(day, 0), NOW_DAY))
        it = dict(id=iid, type=type_, partition=partition, scope=scope, title=title or "",
                  text=text, created_day=day, recorded_day=day, date=day_to_date(day),
                  entities=list(dict.fromkeys(entities)), fact_refs=list(fact_refs), tags=list(tags))
        it.update(extra)
        self.items.append(it)
        self.by_id[iid] = it
        for t in tags:
            self.tag[t].append(iid)
        return iid

    def day_in_month(self, m, lo=1, hi=27):
        return month_start_day(m) + self.rng.randint(lo, hi)

    # ------------------------------------------------------------ keyed facts
    def fact(self, key, entity, attr, label, versions, partition, scope, fmt, kind="state",
             family="generic", render=None):
        """versions: list of (day, value). Creates one item per version with supersession."""
        versions = sorted(versions, key=lambda x: x[0])
        ids = []
        ename = self.entities[entity]["name"]
        for i, (d, v) in enumerate(versions):
            vs = fmt(v)
            if render:
                txt = render(ename, vs, d)
            else:
                txt = f"{ename} — {label}: {vs} (as at {day_to_date(d)})."
            lag = self.rng.choice([0, 0, 1, 2, 3, 5, 9])
            iid = self.add("fact", partition, scope, txt, d, entities=[entity],
                           title=f"{ename} · {label}", key=key, attribute=attr, entity_id=entity,
                           value=v, value_str=vs, version=i + 1, valid_from=d,
                           valid_to=None, supersedes=None, superseded_by=None, fact_family=family)
            self.by_id[iid]["recorded_day"] = min(NOW_DAY, d + lag)
            ids.append(iid)
        for i, iid in enumerate(ids):
            if i > 0:
                self.by_id[iid]["supersedes"] = ids[i - 1]
            if i + 1 < len(ids):
                self.by_id[iid]["superseded_by"] = ids[i + 1]
                self.by_id[iid]["valid_to"] = versions[i + 1][0]
        self.keys[key] = dict(key=key, entity=entity, attr=attr, label=label, versions=ids,
                              partition=partition, scope=scope, kind=kind, family=family)
        return ids

    def head(self, key):
        return self.keys[key]["versions"][-1]

    def version_at(self, key, day):
        vid = None
        for v in self.keys[key]["versions"]:
            if self.by_id[v]["valid_from"] <= day:
                vid = v
        return vid

    def mention(self, key, vid, day, partition=None, scope=None, type_="note", templates=None,
                extra_entities=(), tags=()):
        """A free-text item that mentions a specific fact version (becomes a stale trap later)."""
        f = self.by_id[vid]
        k = self.keys[key]
        tpls = templates or MENTION[k["family"]]
        a = self.alias(k["entity"])
        txt = self.rng.choice(tpls).format(a=a, v=fuzz_value(self.rng, f["value"], f["value_str"]),
                                           label=k["label"])
        return self.add(type_, partition or k["partition"], scope or k["scope"], txt, day,
                        entities=[k["entity"], *extra_entities], fact_refs=[vid],
                        tags=("mention", *tags))


# ---------------------------------------------------------------- value formatting
def money_c(v):
    return f"${v:,.0f}"


def fuzz_value(rng, v, vs):
    """Free-text rendering of a value: humans don't write canonical strings."""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) >= 1000 and vs.startswith("$"):
        r = rng.random()
        if abs(v) >= 1_000_000 and r < 0.5:
            return f"${v/1e6:.2f}m"
        if r < 0.35:
            return f"${v/1000:.0f}k"
        if r < 0.55:
            return f"{v/1000:.0f}k"
        if r < 0.7:
            return f"about {v/1000:.0f} grand"
        return vs
    return vs


MENTION = {
    "valuation": [
        "Valuer came through {a} today, reckons it's worth around {v} now.",
        "Agent's appraisal on {a}: {v}. Not bad given the market.",
        "{a} desktop valuation landed at {v} — screenshot saved.",
        "Bank's figure for {a} is {v}, a bit under what I hoped.",
        "Spoke to the agent, {a} would list at roughly {v} if we ever sold.",
    ],
    "loan": [
        "Statement for {a} shows we still owe {v} on it.",
        "Checked the mortgage on {a} — balance sitting at {v}.",
        "{a} loan is down to {v} after this month's repayment.",
        "Owing {v} on {a} per the latest bank statement.",
    ],
    "rate": [
        "Lender moved {a} to {v}. Should check if that's competitive.",
        "{a} is now on {v} variable.",
        "Rate notice: {a} at {v} from this month.",
    ],
    "rent": [
        "PM confirmed {a} rent is {v} from the new lease.",
        "Tenant at {a} paying {v} now.",
        "{a} rent review done — {v}.",
    ],
    "pm": [
        "{a} is now managed by {v}.",
        "Property manager for {a}: {v}. Their number is in contacts.",
    ],
    "lease_end": ["Lease on {a} runs to {v}.", "{a} tenant's lease ends {v}, PM will ask about renewal."],
    "cash": [
        "Offset balance is {v} as of today.",
        "Cash buffer check: {v} sitting in the offset.",
        "Money in the offset: {v}. Keep an eye on it before the next settlement.",
        "Looked at the accounts — {v} in the offset.",
    ],
    "borrowing": [
        "Broker says our borrowing capacity is about {v} at the moment.",
        "Pre-approval estimate came back: {v} max borrowing.",
        "Serviceability calc from the broker: {v}.",
    ],
    "rule": [
        "Reminder to self: {label} — {v}.",
        "Agreed with Priya: {v}. That's the line.",
    ],
    "strategy": [
        "Strategy note: {v}",
        "Keep coming back to this — {v}",
    ],
    "units": ["Holding {v} of {a} now.", "{a}: position is {v} after the last trade.",
              "Topped up / trimmed {a} — sitting at {v}."],
    "mvalue": ["{a} position worth {v} on today's close.", "Portfolio check: {a} at {v}.",
               "{a} marked at {v}."],
    "count": ["{a} is at {v} as of this week.", "Numbers update — {a}: {v}.", "{label} for {a}: {v}."],
    "person_role": ["{v} is now {label} at {a}.", "Heads up — {a} {label} is {v} going forward.",
                    "{v} stepping in as {label} ({a})."],
    "supplier": ["We're using {v} for {label} at {a}.", "{a} {label}: {v}. Contact in the shared drive.",
                 "Switched over — {label} for {a} is {v} now."],
    "price": ["{a} {label} set at {v}.", "New {label} at {a}: {v}."],
    "revenue": ["{label}: {v} for {a}. Accountant to confirm.", "{a} turned over {v} ({label}).",
                "Rough numbers — {a} {label} came in at {v}."],
    "lift": ["Tested {label} today: {v}. Felt solid.", "New {label} — {v}!", "{label} sitting at {v}."],
    "bodyweight": ["Weighed in at {v} this morning.", "Bodyweight {v}."],
    "program": ["Running {v} this block.", "Switched program to {v}.", "Coach has me on {v}."],
    "sessions": ["Managing {v} sessions a week at the moment.", "Training frequency: {v} per week."],
    "runtime": ["Ran 10k in {v} this morning.", "10k time trial: {v}."],
    "goal": ["Goal locked in: {v}.", "Target reset — {v}.", "Writing it down so it's real: {v}."],
    "reading_count": ["{v} books finished so far this year.", "Reading tally: {v} done."],
    "reading_now": ["Currently reading {v}.", "Started {v} last night.", "Picked up {v} — on the bedside table now."],
    "activity": ["{a}: {v}.", "Schedule for {a} this term — {v}.", "{a}'s activities now: {v}."],
    "pb": ["{a} swam a PB: {v}!", "New best time for {a}: {v}."],
    "plan": ["{a} membership plan: {v}.", "{a} moved to the {v} plan."],
    "member_program": ["{a} program: {v}.", "Programmed {a} on {v}."],
    "status": ["{a} update: {v}.", "Site status — {a}: {v}.", "{a} is at {v} stage."],
    "generic": ["{a}: {label} is {v}.", "Note — {label} for {a}: {v}."],
}


# ---------------------------------------------------------------- the world
def build(seed: int = 20261023) -> Gen:
    g = Gen(seed)
    R = g.rng

    # ---- people
    g.ent("p_dane", "person", "Dane Halloran", ["Dane", "me"], ["owner", "household"])
    g.ent("p_priya", "person", "Priya Halloran", ["Priya", "P"], ["household", "member/m03"])
    g.ent("p_mila", "person", "Mila", ["Mila Halloran", "our eldest"], ["household"])
    g.ent("p_theo", "person", "Theo", ["Theo Halloran", "the middle one"], ["household"])
    g.ent("p_ruby", "person", "Ruby", ["Ruby Halloran", "the little one"], ["household"])
    for p in ("p_priya", "p_mila", "p_theo", "p_ruby"):
        g.edge("p_dane", p, "family", "household")
    g.ent("p_lachlan", "person", "Lachlan Moore", ["Lachlan", "Lachie"], ["biz/gym"])
    g.ent("p_rhea", "person", "Rhea Castell", ["Rhea"], ["biz/construction"])
    g.ent("p_tomas", "person", "Tomas Abiodun", ["Tomas"], ["biz/cafe"])
    g.ent("p_nadia", "person", "Nadia Ferris", ["Nadia", "the broker", "Clearpath"], ["owner"])

    # ---- businesses
    g.ent("b_gym", "business", "IronBark Fitness", ["IronBark", "the gym", "Ironbark gym"], ["biz/gym", "public/gym"])
    g.ent("b_con", "business", "Stonefield Builders", ["Stonefield", "the building company", "the construction business"], ["biz/construction"])
    g.ent("b_cafe", "business", "Copperleaf Cafe", ["Copperleaf", "the cafe", "the café"], ["biz/cafe"])
    g.edge("p_dane", "b_gym", "owns", "biz/gym"); g.edge("p_lachlan", "b_gym", "partner", "biz/gym")
    g.edge("p_dane", "b_con", "owns", "biz/construction"); g.edge("p_rhea", "b_con", "partner", "biz/construction")
    g.edge("p_dane", "b_cafe", "owns", "biz/cafe"); g.edge("p_tomas", "b_cafe", "partner", "biz/cafe")

    # ---- staff
    staff = {
        "b_gym": ["Sasha Novak", "Ben Okafor", "Imogen Hartley", "Raf Silva", "Corey Lin", "Tess Wardle", "Jordan Pike"],
        "b_cafe": ["Jordan Pike", "Mei Tran", "Olly Brandt", "Ana Ruiz", "Kit Dawson"],
        "b_con": ["Ross Delaney", "Kira Matthews", "Dev Patel", "Sione Fifita", "Gus Harland", "Wade Kerr"],
    }
    bpart = {"b_gym": "biz/gym", "b_cafe": "biz/cafe", "b_con": "biz/construction"}
    for b, names in staff.items():
        for n in names:
            sid = "s_" + n.split()[0].lower() + "_" + n.split()[1].lower()
            if sid not in g.entities:
                g.ent(sid, "person", n, [n.split()[0]], [])
            g.entities[sid]["partitions"].append(bpart[b])
            g.edge(sid, b, "works_at", bpart[b])
    # Ben Okafor also coaches Dane (owner partition) -> shared person
    g.entities["s_ben_okafor"]["partitions"].append("owner")
    g.entities["s_sasha_novak"]["partitions"].append("owner")

    # ---- suppliers (some shared across businesses)
    sup = [
        ("sup_talbot", "Talbot Linen Services", ["Talbot", "Talbot Linen", "the linen people"], ["b_gym", "b_cafe"]),
        ("sup_brightwater", "Brightwater Plumbing", ["Brightwater", "the plumber"], ["b_con", "b_cafe"]),
        ("sup_ridgeback", "Ridgeback Roasters", ["Ridgeback"], ["b_cafe"]),
        ("sup_emberoak", "Ember & Oak Coffee", ["Ember and Oak", "Ember & Oak", "the roaster"], ["b_cafe"]),
        ("sup_saltbush", "Saltbush Coffee Roasters", ["Saltbush"], ["b_cafe"]),
        ("sup_northside", "Northside Roastery", ["Northside"], ["b_cafe"]),
        ("sup_valley", "Valley Fresh Dairy", ["Valley Fresh"], ["b_cafe"]),
        ("sup_greenhill", "Greenhill Dairy Co-op", ["Greenhill", "the dairy co-op"], ["b_cafe"]),
        ("sup_forge", "Forge Athletic Supply", ["Forge", "Forge Athletic"], ["b_gym"]),
        ("sup_apex", "Apex Rig Co", ["Apex", "Apex Rig"], ["b_gym"]),
        ("sup_titanbar", "Titan Barbell Works", ["Titan Barbell", "Titan"], ["b_gym"]),
        ("sup_grayline", "Grayline Concrete", ["Grayline"], ["b_con"]),
        ("sup_monarch", "Monarch Readymix", ["Monarch"], ["b_con"]),
        ("sup_northcrest", "Northcrest Insurance", ["Northcrest"], ["b_con"]),
        ("sup_harbourline", "Harbourline Property Management", ["Harbourline"], ["owner"]),
        ("sup_keystone", "Keystone Rentals", ["Keystone"], ["owner"]),
        ("sup_clearpath", "Clearpath Finance", ["Clearpath", "the broker's firm"], ["owner"]),
        ("sup_peopleworks", "PeopleWorks Hospitality Recruitment", ["PeopleWorks"], ["b_cafe"]),
    ]
    for sid, name, al, users in sup:
        parts = [bpart.get(u, u) for u in users]
        g.ent(sid, "supplier", name, al, parts)
        for u in users:
            if u in bpart:
                g.edge(sid, u, "supplies", bpart[u])
    g.edge("sup_brightwater", "b_con", "subcontractor", "biz/construction")

    # ---- investment properties
    props = [
        ("prop_wren", "14 Wren Street, Granite Falls", ["Wren St", "the Wren Street house", "the Granite Falls place"], "Northbrook"),
        ("prop_tamar", "3/22 Tamar Parade, Easthaven", ["Tamar Pde", "the Easthaven unit", "the Tamar unit"], "home"),
        ("prop_bellbird", "7 Bellbird Court, Coralie", ["Bellbird Ct", "the Coralie house", "Bellbird"], "Westmere"),
        ("prop_ostler", "41 Ostler Road, Marlow Creek", ["Ostler Rd", "the Marlow Creek duplex", "the duplex"], "home"),
        ("prop_quarry", "9 Quarry Lane, Kestrel Bay", ["Quarry Ln", "the Kestrel Bay cottage", "the beach cottage"], "Southport"),
        ("prop_halyard", "18 Halyard Way, Tindal Point", ["Halyard Way", "the Tindal Point townhouse", "the townhouse"], "Northbrook"),
    ]
    for pid, name, al, region in props:
        g.ent(pid, "property", name, al, ["owner"], scope="finance/investments", region=region)
        g.edge("p_dane", pid, "owns", "owner")
    # Halyard Way is being renovated by Stonefield: shared entity owner <-> construction
    g.entities["prop_halyard"]["partitions"].append("biz/construction")
    g.edge("prop_halyard", "b_con", "renovation_by", "biz/construction")

    pct = lambda v: f"{v:.2f}%"
    wk = lambda v: f"${v:,.0f} per week"
    FI = "finance/investments"
    for pid, name, al, region in props:
        val = R.randint(42, 88) * 10_000
        vals = []
        for q in range(6):
            d = month_start_day(q * 3) + R.randint(3, 25)
            if q:
                val = round(val * (1 + R.gauss(0.018, 0.018)) / 1000) * 1000
            vals.append((d, val))
        g.fact(f"{pid}.valuation", pid, "valuation", "current valuation", vals, "owner", FI, money_c,
               family="valuation")
        loan = round(vals[0][1] * R.uniform(0.52, 0.72) / 1000) * 1000
        loans = []
        for q in range(6):
            d = month_start_day(q * 3) + R.randint(1, 20)
            if q:
                loan = round(loan * (1 - R.uniform(0.006, 0.018)) / 100) * 100
            if pid == "prop_wren" and q == 4:  # equity release on refinance
                loan += 85_000
            loans.append((d, loan))
        g.fact(f"{pid}.loan", pid, "loan_balance", "loan balance", loans, "owner", FI, money_c, family="loan")
        r0 = R.choice([6.09, 6.19, 6.24, 6.34, 5.99])
        rates = [(month_start_day(0) + 2, r0), (month_start_day(7) + 3, r0 - 0.25),
                 (month_start_day(13) + 3, r0 - 0.5 + R.choice([0, 0.05, -0.1]))]
        g.fact(f"{pid}.rate", pid, "interest_rate", "interest rate", rates, "owner", FI, pct, family="rate")
        rent = R.randint(42, 68) * 10
        rm = R.randint(4, 14)
        g.fact(f"{pid}.rent", pid, "weekly_rent", "weekly rent",
               [(month_start_day(0) + 5, rent), (month_start_day(rm) + 5, rent + R.choice([15, 20, 25, 30, 40]))],
               "owner", FI, wk, family="rent")
        pms = [(month_start_day(0) + 1, "Harbourline Property Management")]
        if pid in ("prop_bellbird", "prop_quarry"):
            pms.append((month_start_day(R.randint(7, 11)) + 4, "Keystone Rentals"))
        g.fact(f"{pid}.pm", pid, "property_manager", "property manager", pms, "owner", FI, str, family="pm")
        le0 = day_to_date(month_start_day(rm) + 4)
        le1 = day_to_date(month_start_day(rm) + 4 + 365)
        g.fact(f"{pid}.lease_end", pid, "lease_end", "lease end date",
               [(month_start_day(0) + 5, le0), (month_start_day(rm) + 5, le1)], "owner", FI, str, family="lease_end")
        g.edge(pid, "sup_harbourline" if len(pms) == 1 else "sup_keystone", "managed_by", "owner")

    # ---- holdings
    holds = [("h_mge", "Meridian Global Equity ETF", ["MGE", "the global ETF"]),
             ("h_hlr", "Halcyon Resources", ["HLR", "Halcyon"]),
             ("h_ngb", "Northgate Bank", ["NGB", "Northgate"]),
             ("h_ace", "Aurora Clean Energy", ["ACE", "Aurora"]),
             ("h_pif", "Pinecrest Infrastructure Fund", ["PIF", "Pinecrest"]),
             ("h_slh", "Solano Health", ["SLH", "Solano"])]
    for hid, name, al in holds:
        g.ent(hid, "holding", name, al, ["owner"], scope=FI)
        units = R.randint(8, 60) * 50
        uv = [(month_start_day(0) + 2, units)]
        for m in sorted(R.sample(range(3, 17), R.randint(1, 2))):
            units = max(100, units + R.choice([-1, 1, 1]) * R.randint(2, 12) * 50)
            uv.append((month_start_day(m) + R.randint(2, 20), units))
        g.fact(f"{hid}.units", hid, "units", "units held", uv, "owner", FI, lambda v: f"{v:,} units", family="units")
        px = R.uniform(8, 60)
        mv = []
        for q in range(6):
            px *= 1 + R.gauss(0.02, 0.06)
            d = month_start_day(q * 3) + R.randint(25, 28)
            u = g.by_id[g.version_at(f"{hid}.units", d) or g.keys[f"{hid}.units"]["versions"][0]]["value"]
            mv.append((d, round(u * px / 100) * 100))
        g.fact(f"{hid}.value", hid, "market_value", "market value", mv, "owner", FI, money_c, family="mvalue")

    # ---- personal finance
    g.ent("fin_portfolio", "account", "the property portfolio", ["portfolio", "our properties", "the investment portfolio"], ["owner"], scope=FI)
    g.ent("fin_offset", "account", "offset account", ["offset", "cash buffer", "the offset"], ["owner"], scope="finance/personal")
    g.ent("fin_household", "account", "household budget", ["family budget", "household spending"], ["household"], scope="finance/personal")
    cash = 86_000
    cv = []
    for m in range(N_MONTHS):
        if m:
            cash += R.randint(-6, 9) * 1000
        if m == 11:
            cash -= 38_000
        cv.append((month_start_day(m) + R.randint(26, 27), cash))
    g.fact("offset.balance", "fin_offset", "balance", "offset balance", cv, "owner", "finance/personal", money_c, family="cash")
    g.fact("portfolio.borrowing_capacity", "fin_portfolio", "borrowing_capacity", "borrowing capacity",
           [(month_start_day(0) + 14, 950_000), (month_start_day(8) + 9, 1_100_000), (month_start_day(14) + 6, 1_240_000)],
           "owner", FI, money_c, family="borrowing")
    g.fact("portfolio.lvr_rule", "fin_portfolio", "lvr_rule", "maximum portfolio LVR rule",
           [(month_start_day(0) + 3, "keep total portfolio loan-to-value at or below 70%"),
            (month_start_day(12) + 8, "keep total portfolio loan-to-value at or below 65% after the rate scare")],
           "owner", FI, str, family="rule",
           render=lambda e, v, d: f"Rule for {e}: {v}. Agreed {day_to_date(d)}.")
    g.fact("portfolio.strategy", "fin_portfolio", "strategy", "investment strategy",
           [(month_start_day(0) + 6, "Buy and hold in our home region; prioritise rental yield; no flips."),
            (month_start_day(9) + 12, "Buy and hold, but the next purchases go interstate for diversification — target growth corridors with infrastructure spend; yield secondary.")],
           "owner", FI, str, family="strategy",
           render=lambda e, v, d: f"Strategy statement for {e} (set {day_to_date(d)}): {v}")
    g.fact("offset.savings_goal", "fin_offset", "buffer_goal", "cash buffer goal",
           [(month_start_day(0) + 9, "$60,000 emergency buffer"), (month_start_day(10) + 2, "$80,000 emergency buffer")],
           "owner", "finance/personal", str, family="goal")
    g.fact("household.budget", "fin_household", "monthly_budget", "monthly household budget",
           [(month_start_day(0) + 4, 9_500), (month_start_day(9) + 4, 10_200)], "household", "finance/personal",
           lambda v: f"${v:,} per month", family="generic")

    # ---- gym
    GO, GF = "business/gym/ops", "business/gym/finance"
    mem = 310
    mc = []
    for q in range(6):
        if q:
            mem += R.randint(10, 30)
        mc.append((month_start_day(q * 3) + R.randint(5, 15), mem))
    g.fact("gym.members", "b_gym", "membership_count", "active memberships", mc, "biz/gym", GF, lambda v: f"{v} members", family="count")
    g.fact("gym.member_target", "b_gym", "membership_target", "membership target",
           [(month_start_day(0) + 10, "400 active members by December 2025"), (month_start_day(12) + 5, "450 active members by December 2026")],
           "biz/gym", GF, str, family="goal")
    g.fact("gym.head_coach", "b_gym", "head_coach", "head coach",
           [(month_start_day(0) + 1, "Sasha Novak"), (month_start_day(7) + 10, "Ben Okafor")], "biz/gym", GO, str, family="person_role")
    g.fact("gym.equipment_supplier", "b_gym", "equipment_supplier", "equipment supplier",
           [(month_start_day(0) + 1, "Forge Athletic Supply"), (month_start_day(11) + 15, "Apex Rig Co")], "biz/gym", GO, str, family="supplier")
    g.fact("gym.towel_supplier", "b_gym", "towel_supplier", "towel and laundry supplier",
           [(month_start_day(0) + 1, "Talbot Linen Services")], "biz/gym", GO, str, family="supplier")
    g.fact("gym.lease", "b_gym", "monthly_lease", "monthly lease cost",
           [(month_start_day(0) + 1, 8_400), (month_start_day(12) + 1, 8_900)], "biz/gym", GF, lambda v: f"${v:,} per month", family="price")
    g.fact("gym.staff_count", "b_gym", "staff_count", "staff headcount",
           [(month_start_day(0) + 1, 9), (month_start_day(6) + 1, 11), (month_start_day(13) + 1, 12)], "biz/gym", GO, lambda v: f"{v} staff", family="count")
    g.fact("gym.price", "b_gym", "membership_price", "standard membership price",
           [(month_start_day(0) + 1, 32), (month_start_day(6) + 14, 35)], "biz/gym", GF, lambda v: f"${v} per week", family="price")
    g.fact("gym.timetable", "b_gym", "timetable", "class timetable",
           [(month_start_day(0) + 1, "6am strength Mon/Wed/Fri, 6pm HIIT Tue/Thu, Sat 8am team WOD"),
            (month_start_day(8) + 1, "5:30am and 6:30am strength Mon/Wed/Fri, 6pm HIIT Tue/Thu, Sat 8am team WOD, Sun 9am mobility")],
           "public/gym", GO, str, family="generic")
    # ---- construction
    CO, CF = "business/construction/ops", "business/construction/finance"
    pipe = R.randint(18, 26) * 100_000
    pv, ap = [], []
    for q in range(6):
        if q:
            pipe = round(pipe * (1 + R.gauss(0.03, 0.12)) / 10_000) * 10_000
        d = month_start_day(q * 3) + R.randint(5, 20)
        pv.append((d, pipe)); ap.append((d, R.randint(3, 6)))
    g.fact("con.pipeline", "b_con", "pipeline_value", "contracted pipeline value", pv, "biz/construction", CF, money_c, family="count")
    g.fact("con.active_projects", "b_con", "active_projects", "active projects", ap, "biz/construction", CO, lambda v: f"{v} active jobs", family="count")
    g.fact("con.concrete_supplier", "b_con", "concrete_supplier", "concrete supplier",
           [(month_start_day(0) + 1, "Grayline Concrete"), (month_start_day(8) + 12, "Monarch Readymix")], "biz/construction", CO, str, family="supplier")
    g.fact("con.supervisor", "b_con", "site_supervisor", "site supervisor",
           [(month_start_day(0) + 1, "Ross Delaney"), (month_start_day(10) + 3, "Kira Matthews")], "biz/construction", CO, str, family="person_role")
    g.fact("con.insurance", "b_con", "insurance_premium", "public liability premium",
           [(month_start_day(0) + 20, 14_200), (month_start_day(9) + 20, 16_900)], "biz/construction", CF, lambda v: f"${v:,} per year with Northcrest Insurance", family="price")
    g.fact("con.plumbing_sub", "b_con", "plumbing_sub", "plumbing subcontractor",
           [(month_start_day(0) + 1, "Brightwater Plumbing")], "biz/construction", CO, str, family="supplier")
    g.fact("con.strategy", "b_con", "strategy", "tender policy",
           [(month_start_day(0) + 3, "residential builds and renovations under $2m only; no commercial work"),
            (month_start_day(13) + 9, "residential under $2m plus light commercial fit-outs under $1m; no multi-storey")],
           "biz/construction", CF, str, family="rule",
           render=lambda e, v, d: f"{e} tender policy (agreed {day_to_date(d)}): {v}.")
    projects = [("proj_harlow", "Harlow Park extension", ["the Harlow Park job", "Harlow Park"]),
                ("proj_elsbury", "Elsbury townhouses", ["the Elsbury job", "Elsbury"]),
                ("proj_corran", "Corran Heights renovation", ["Corran Heights", "the Corran reno"]),
                ("proj_halyard", "Halyard Way kitchen and bathroom renovation", ["the Halyard reno", "Halyard Way job"])]
    stages = ["site establishment", "slab poured", "frame up", "lock-up", "fit-off", "practical completion"]
    for prid, name, al in projects:
        g.ent(prid, "project", name, al, ["biz/construction"], scope=CO)
        g.edge(prid, "b_con", "project_of", "biz/construction")
        start = R.randint(0, 8)
        ns = R.randint(3, 5)
        ms = sorted(R.sample(range(start, 17), ns))
        g.fact(f"{prid}.status", prid, "status", "project stage",
               [(month_start_day(m) + R.randint(2, 25), stages[i if prid != "proj_halyard" else min(i, 4)]) for i, m in enumerate(ms)],
               "biz/construction", CO, str, family="status")
    g.entities["proj_halyard"]["partitions"].append("owner")
    g.edge("proj_halyard", "prop_halyard", "renovates", "biz/construction")
    # ---- cafe
    CaO, CaF = "business/cafe/ops", "business/cafe/finance"
    g.fact("cafe.bean_supplier", "b_cafe", "bean_supplier", "coffee bean supplier",
           [(month_start_day(0) + 1, "Ridgeback Roasters"), (month_start_day(9) + 6, "Ember & Oak Coffee")], "biz/cafe", CaO, str, family="supplier")
    g.fact("cafe.milk_supplier", "b_cafe", "milk_supplier", "milk supplier",
           [(month_start_day(0) + 1, "Valley Fresh Dairy"), (month_start_day(5) + 3, "Greenhill Dairy Co-op")], "biz/cafe", CaO, str, family="supplier")
    g.fact("cafe.linen_supplier", "b_cafe", "linen_supplier", "linen supplier",
           [(month_start_day(0) + 1, "Talbot Linen Services")], "biz/cafe", CaO, str, family="supplier")
    g.fact("cafe.hours", "b_cafe", "opening_hours", "opening hours",
           [(month_start_day(0) + 1, "7am–3pm Monday to Saturday, closed Sunday"),
            (month_start_day(11) + 1, "6:30am–3pm Monday to Saturday, 8am–1pm Sunday")], "biz/cafe", CaO, str, family="generic")
    g.fact("cafe.head_barista", "b_cafe", "head_barista", "head barista",
           [(month_start_day(0) + 1, "Jordan Pike"), (month_start_day(13) + 7, "Mei Tran")], "biz/cafe", CaO, str, family="person_role")
    cov = R.randint(900, 1100)
    cvv, crr = [], []
    res = R.randint(30, 45) * 1000
    for q in range(6):
        if q:
            cov += R.randint(-40, 90); res += R.randint(-6, 10) * 1000
        d = month_start_day(q * 3) + R.randint(5, 20)
        cvv.append((d, cov)); crr.append((d + 3, res))
    g.fact("cafe.covers", "b_cafe", "weekly_covers", "average weekly covers", cvv, "biz/cafe", CaO, lambda v: f"{v} covers a week", family="count")
    g.fact("cafe.cash_reserve", "b_cafe", "cash_reserve", "cash reserve", crr, "biz/cafe", CaF, money_c, family="count")
    g.fact("cafe.revenue_goal", "b_cafe", "revenue_goal", "annual revenue target",
           [(month_start_day(0) + 5, "$780,000 for calendar 2025"), (month_start_day(12) + 5, "$820,000 for calendar 2026")], "biz/cafe", CaF, str, family="goal")
    g.fact("cafe.distribution_rule", "b_cafe", "distribution_rule", "partner distribution rule",
           [(month_start_day(0) + 5, "any distribution or drawing above $20,000 needs both partners' written sign-off and must leave three months of operating costs in reserve")],
           "biz/cafe", CaF, str, family="rule",
           render=lambda e, v, d: f"{e} partnership agreement clause: {v}.")
    # ---- revenue series (separate keys per quarter; some restated)
    for b, part, sc, base in (("b_gym", "biz/gym", GF, 210_000), ("b_con", "biz/construction", CF, 820_000),
                              ("b_cafe", "biz/cafe", CaF, 185_000)):
        short = {"b_gym": "gym", "b_con": "con", "b_cafe": "cafe"}[b]
        rev = base
        for q in range(6):
            rev = round(rev * (1 + R.gauss(0.025, 0.06)) / 100) * 100
            d = month_start_day(q * 3 + 3) + R.randint(5, 20) if q < 5 else NOW_DAY - R.randint(0, 3)
            ql = quarter_label(q * 3)
            vers = [(d, rev)]
            if R.random() < 0.35 and q < 5:
                vers.append((d + R.randint(20, 40), round(rev * R.uniform(0.95, 1.04) / 100) * 100))
            g.fact(f"{short}.revenue.{ql}", b, f"revenue_{ql}", f"revenue for {ql}", vers, part, sc, money_c,
                   kind="series", family="revenue")

    # ---- health / training (owner)
    g.ent("goal_squat", "goal", "squat goal", ["squat target", "the squat goal"], ["owner"], scope="health/training")
    g.ent("goal_run", "goal", "10k running goal", ["the 10k goal", "running target"], ["owner"], scope="health/training")
    g.ent("tr_me", "person_profile", "Dane's training", ["my training", "training"], ["owner"], scope="health/training")
    HT = "health/training"
    for lift, base in (("squat", 152.5), ("bench", 112.5), ("deadlift", 185.0)):
        v = base
        ver = []
        for q in range(6):
            if q:
                v += R.choice([0, 2.5, 5, 5, 7.5])
            ver.append((month_start_day(q * 3) + R.randint(10, 25), v))
        g.fact(f"train.{lift}_1rm", "tr_me", f"{lift}_1rm", f"{lift} one-rep max", ver, "owner", HT, lambda v: f"{v:g} kg", family="lift")
    g.fact("train.bodyweight", "tr_me", "bodyweight", "bodyweight",
           [(month_start_day(q * 3) + 3, round(94 - q * R.uniform(0.3, 0.9), 1)) for q in range(6)], "owner", HT, lambda v: f"{v} kg", family="bodyweight")
    g.fact("train.program", "tr_me", "program", "training program",
           [(month_start_day(0) + 2, "5/3/1 Boring But Big"), (month_start_day(6) + 2, "Texas Method"),
            (month_start_day(12) + 2, "a 12-week conjugate block with Ben")], "owner", HT, str, family="program")
    g.fact("train.sessions", "tr_me", "sessions_per_week", "sessions per week",
           [(month_start_day(0) + 2, 4), (month_start_day(5) + 2, 5), (month_start_day(11) + 20, 3), (month_start_day(15) + 2, 4)],
           "owner", HT, lambda v: f"{v}", family="sessions")
    g.fact("train.run10k", "tr_me", "run_10k", "10k run time",
           [(month_start_day(m) + R.randint(5, 20), t) for m, t in ((1, "52:40"), (4, "51:15"), (8, "49:58"), (12, "49:20"), (16, "48:31"))],
           "owner", HT, str, family="runtime")
    g.fact("train.coach", "tr_me", "coach", "strength coach",
           [(month_start_day(0) + 2, "Sasha Novak"), (month_start_day(7) + 12, "Ben Okafor")], "owner", HT, str, family="person_role")
    g.fact("goal_squat.target", "goal_squat", "target", "squat target",
           [(month_start_day(0) + 4, "180 kg squat by 31 December 2025"), (month_start_day(12) + 4, "190 kg squat by 30 September 2026")],
           "owner", HT, str, family="goal")
    g.fact("goal_run.target", "goal_run", "target", "10k target",
           [(month_start_day(0) + 4, "sub-50 minute 10k by October 2025"), (month_start_day(10) + 4, "sub-48 minute 10k by August 2026")],
           "owner", HT, str, family="goal")
    g.edge("tr_me", "s_ben_okafor", "coached_by", "owner")
    g.edge("tr_me", "b_gym", "trains_at", "owner")

    # ---- reading
    RD = "reading"
    g.ent("rd_me", "person_profile", "Dane's reading", ["my reading", "reading list"], ["owner"], scope=RD)
    books = make_books(R)
    for b in books:
        g.ent(b["id"], "book", b["title"], [b["title"].replace("The ", ""), f"the {b['author'].split()[-1]} book"], ["owner"], scope=RD, author=b["author"], genre=b["genre"])
    g.fact("reading.goal", "rd_me", "goal", "reading goal",
           [(month_start_day(0) + 1, "20 books in 2025"), (month_start_day(12) + 1, "24 books in 2026")], "owner", RD, str, family="goal")
    g.fact("reading.finished", "rd_me", "books_finished_ytd", "books finished this year",
           [(month_start_day(q * 3) + 26, n) for q, n in enumerate([4, 9, 14, 19, 5, 11])], "owner", RD, lambda v: f"{v} books", family="reading_count")
    cur = R.sample(books, 6)
    g.fact("reading.current", "rd_me", "currently_reading", "currently reading",
           [(month_start_day(q * 3) + 2, f"{b['title']} by {b['author']}") for q, b in enumerate(cur)], "owner", RD, str, family="reading_now")
    g._books = books

    # ---- family
    FL = "family/leisure"
    g.fact("mila.activity", "p_mila", "activities", "activities",
           [(month_start_day(0) + 20, "swim squad Tue/Thu 5:45am and Saturday 7am"), (month_start_day(9) + 6, "water polo Mon/Wed 4:30pm and swim squad Saturday 7am")],
           "household", FL, str, family="activity")
    g.fact("theo.activity", "p_theo", "activities", "activities",
           [(month_start_day(0) + 20, "soccer training Wednesday 5pm, games Saturday morning"), (month_start_day(7) + 3, "soccer Wednesday 5pm and Saturday, basketball Friday 6pm")],
           "household", FL, str, family="activity")
    g.fact("ruby.activity", "p_ruby", "activities", "activities",
           [(month_start_day(0) + 20, "piano lesson Thursday 4pm"), (month_start_day(10) + 3, "piano Thursday 4pm and gymnastics Saturday 9am")],
           "household", FL, str, family="activity")
    g.fact("mila.swim_pb", "p_mila", "swim_pb", "100m freestyle personal best",
           [(month_start_day(m) + R.randint(5, 20), t) for m, t in ((1, "1:09.8"), (5, "1:08.1"), (10, "1:06.9"), (15, "1:05.6"))],
           "household", FL, str, family="pb")
    g.fact("mila.swim_goal", "p_mila", "swim_goal", "regional qualifying goal",
           [(month_start_day(2) + 3, "100m freestyle under 1:05.0 to qualify for regionals in August 2026")], "household", FL, str, family="goal")
    g.fact("family.holiday_budget", "fin_household", "holiday_budget", "holiday budget",
           [(month_start_day(0) + 9, "$6,000 for the year"), (month_start_day(12) + 9, "$8,500 for 2026 including the September trip")],
           "household", FL, str, family="generic")
    g.fact("family.school_break", "p_dane", "school_break", "spring school holidays",
           [(month_start_day(12) + 15, "19 September to 5 October 2026")], "household", FL, str, family="generic")

    # ---- gym members (per-member partitions); m03 is Priya (shared entity)
    member_names = ["Hugo Brennan", "Lena Voss", "Priya Halloran", "Marco Ruiz", "Siobhan Kerr", "Arjun Mehta",
                    "Clara Dunn", "Felix Ward", "Nina Petrova", "Owen Tate", "Zara Quinn", "Leo Hartmann"]
    plans = ["Casual 10-pass", "Standard weekly", "Unlimited", "Off-peak", "Strength squad"]
    progs = ["beginner strength 3x/week", "hypertrophy split 4x/week", "HIIT + mobility", "powerlifting peaking block", "general fitness 2x/week", "return-from-injury rehab"]
    coaches = ["Sasha Novak", "Ben Okafor", "Imogen Hartley", "Raf Silva", "Jordan Pike"]
    for m, nm in zip(MEMBER_IDS, member_names):
        IDENTITIES[f"member_{m}"]["name"] = nm
        eid = "p_priya" if m == "m03" else f"mem_{m}"
        if m != "m03":
            g.ent(eid, "person", nm, [nm.split()[0]], [f"member/{m}"])
        g.entities[eid].setdefault("member_id", m)
        g.edge(eid, "b_gym", "member_of", f"member/{m}")
        p1, p2 = R.sample(plans, 2)
        g.fact(f"{m}.plan", eid, "plan", "membership plan",
               [(month_start_day(R.randint(0, 3)) + 3, p1), (month_start_day(R.randint(6, 15)) + 3, p2)], f"member/{m}", "business/gym/members", str, family="plan")
        q1, q2 = R.sample(progs, 2)
        g.fact(f"{m}.program", eid, "program", "training program",
               [(month_start_day(R.randint(0, 4)) + 3, q1), (month_start_day(R.randint(8, 16)) + 3, q2)], f"member/{m}", "business/gym/members", str, family="member_program")
        c = R.choice(coaches)
        g.fact(f"{m}.coach", eid, "coach", "assigned coach", [(month_start_day(0) + 3, c)], f"member/{m}", "business/gym/members", str, family="generic")
        sid = "s_" + c.split()[0].lower() + "_" + c.split()[1].lower()
        g.edge(eid, sid, "coached_by", f"member/{m}")
        # member goal + progress metric
        kind = R.choice(["deadlift", "bodyfat", "attendance", "run5k"])
        gstart = R.randint(1, 6)
        if kind == "deadlift":
            tgt = [(month_start_day(gstart) + 2, f"deadlift {R.randint(10, 14)*10} kg by end of 2025")]
            tgt.append((month_start_day(R.randint(12, 14)) + 2, f"deadlift {R.randint(15, 18)*10} kg by end of 2026"))
            v0 = R.randint(8, 11) * 10
            prog = [(month_start_day(gstart + 3 * i) + 9, v0 + i * R.choice([5, 10])) for i in range(4)]
            fmtp, plab = (lambda v: f"{v} kg"), "deadlift best"
        elif kind == "bodyfat":
            tgt = [(month_start_day(gstart) + 2, f"body fat under {R.randint(18, 24)}% by mid-2026")]
            v0 = R.randint(26, 32)
            prog = [(month_start_day(gstart + 3 * i) + 9, v0 - i * R.choice([1, 2])) for i in range(4)]
            fmtp, plab = (lambda v: f"{v}% body fat"), "body composition"
        elif kind == "attendance":
            tgt = [(month_start_day(gstart) + 2, "train 3 times a week consistently")]
            prog = [(month_start_day(gstart + 3 * i) + 9, R.choice([1, 2, 2, 3, 3, 4])) for i in range(4)]
            fmtp, plab = (lambda v: f"{v} visits per week on average"), "attendance"
        else:
            tgt = [(month_start_day(gstart) + 2, f"run 5k under {R.randint(24, 29)} minutes")]
            prog = [(month_start_day(gstart + 3 * i) + 9, f"{R.randint(27, 33) - i}:{R.randint(10, 59)}") for i in range(4)]
            fmtp, plab = str, "5k time"
        g.fact(f"{m}.goal", eid, "goal", "member goal", tgt, f"member/{m}", "business/gym/members", str, family="goal")
        g.fact(f"{m}.progress", eid, "progress", plab, prog, f"member/{m}", "business/gym/members", fmtp, family="generic")
        g.entities[eid]["goal_kind"] = kind

    # extra owner / business goals (goal + metric pairs for goal_tracking)
    g.fact("goal.deadlift", "tr_me", "deadlift_goal", "deadlift target",
           [(month_start_day(0) + 4, "220 kg deadlift by end of 2025"), (month_start_day(12) + 4, "230 kg deadlift by end of 2026")],
           "owner", "health/training", str, family="goal")
    g.fact("goal.bench", "tr_me", "bench_goal", "bench target",
           [(month_start_day(3) + 4, "130 kg bench by June 2026")], "owner", "health/training", str, family="goal")
    g.fact("goal.bodyweight", "tr_me", "bodyweight_goal", "bodyweight target",
           [(month_start_day(0) + 4, "get down to 90 kg while keeping strength")], "owner", "health/training", str, family="goal")
    g.fact("con.pipeline_target", "b_con", "pipeline_target", "pipeline target",
           [(month_start_day(0) + 4, "$2.5m contracted pipeline at all times"), (month_start_day(12) + 6, "$3.0m contracted pipeline by mid-2026")],
           "biz/construction", "business/construction/finance", str, family="goal")
    g.fact("cafe.covers_target", "b_cafe", "covers_target", "weekly covers target",
           [(month_start_day(0) + 4, "1,100 covers a week"), (month_start_day(12) + 4, "1,250 covers a week by June 2026")],
           "biz/cafe", "business/cafe/ops", str, family="goal")

    # ================================================================ free text
    build_mentions(g)
    build_special(g)
    build_filler(g)
    build_media(g)
    build_canaries(g)
    return g


def make_books(R):
    first = ["The Salt", "A Quiet", "The Long", "Iron", "The Glass", "Northern", "The Last", "Paper", "The Hollow", "Silver",
             "The Ninth", "Wild", "The Copper", "Small", "The Distant", "Bright", "The Lantern", "Cold", "The Orchard", "Burning"]
    second = ["Harbour", "Ledger", "Season", "Kingdom", "Compass", "Meridian", "Tide", "Republic", "Engine", "Garden",
              "Frontier", "Signal", "Archive", "River", "Machine", "Summer", "Atlas", "Covenant", "Quarry", "Weather"]
    authors = ["Maren Ostby", "Felix Arden", "Ida Valcourt", "Tobias Rennick", "Hana Morrow", "Callum Strand", "Ines Dorado",
               "Wim Castellan", "Rosa Ellery", "Ken Akaishi", "Lotte Brenner", "Amos Kettle"]
    genres = ["literary fiction", "history", "science fiction", "business", "biography", "fantasy", "crime", "popular science"]
    out = []
    used = set()
    while len(out) < 40:
        t = f"{R.choice(first)} {R.choice(second)}"
        if t in used:
            continue
        used.add(t)
        out.append(dict(id=f"book_{len(out):02d}", title=t, author=R.choice(authors), genre=R.choice(genres)))
    return out


# ---------------------------------------------------------------- mentions (stale traps)
def build_mentions(g: Gen):
    R = g.rng
    chat_of = {"owner": ("note", "Notes to self"), "household": ("chat", "Halloran family"),
               "biz/gym": ("chat", "IronBark partners"), "biz/construction": ("chat", "Stonefield office"),
               "biz/cafe": ("chat", "Copperleaf team"), "public/gym": ("note", "IronBark noticeboard")}
    for key, k in g.keys.items():
        vers = k["versions"]
        for i, vid in enumerate(vers):
            f = g.by_id[vid]
            lo = f["valid_from"]
            hi = f["valid_to"] if f["valid_to"] is not None else NOW_DAY
            if hi - lo < 2:
                continue
            n = R.choice([1, 1, 2, 2, 3]) if len(vers) > 1 else R.choice([0, 1])
            for _ in range(n):
                d = R.randint(lo + 1, max(lo + 1, hi - 1))
                part = k["partition"]
                typ = chat_of.get(part, ("note", ""))[0]
                if part.startswith("member/"):
                    typ = "log"
                g.mention(key, vid, d, type_=typ)


# ---------------------------------------------------------------- special (task-linked) documents
def build_special(g: Gen):
    R = g.rng
    S = g.add
    FI = "finance/investments"
    props = [e for e in g.entities.values() if e["kind"] == "property"]
    # Broker refinance emails (one per property, recent)
    for p in props:
        d = month_start_day(R.randint(13, 17)) + R.randint(1, 20)
        rate = R.choice(["5.49%", "5.59%", "5.64%", "5.39%"])
        txt = R.choice([
            f"Hi Dane — Nadia from Clearpath here. Ran the numbers on {g.alias(p['id'])}: we could refix at {rate} for two years and release some equity if you want it for the next deal. Break costs look minimal. Let me know.",
            f"Email from Nadia (Clearpath Finance): lender is offering {rate} to keep {g.alias(p['id'])}; she thinks a switch would save a bit each month and free up usable equity.",
        ])
        S("email", "owner", FI, txt, d, entities=[p["id"], "p_nadia", "sup_clearpath"], title="Clearpath Finance — refinance option",
          tags=("refi_email", f"refi_email:{p['id']}"))
    # PM emails on market rent / vacancy
    for p in props:
        d = month_start_day(R.randint(12, 17)) + R.randint(1, 20)
        txt = R.choice([
            f"From the property manager: comparable rentals near {g.alias(p['id'])} are leasing for $30–50 a week more. Recommend a rent review at renewal, or a light refresh (paint, blinds) to justify it.",
            f"PM update for {g.alias(p['id'])}: there were two weeks of vacancy between tenants; market feedback says the kitchen is dated. Options: hold the rent, cut it slightly, or freshen up.",
        ])
        S("email", "owner", FI, txt, d, entities=[p["id"]], title="Property manager update", tags=("pm_email", f"pm_email:{p['id']}"))
    # Related-party policy + Stonefield quotes on owner's properties
    S("note", "owner", FI, "Policy if Stonefield works on our own rentals: get one independent quote, invoice at arm's length, and don't let partner time on family jobs eat into paid work. Rhea agreed.",
      month_start_day(10) + 4, entities=["b_con", "fin_portfolio", "p_rhea"], tags=("related_party_policy",))
    S("email", "biz/construction", "business/construction/finance",
      "Quote 24-117: kitchen and bathroom renovation at 18 Halyard Way, Tindal Point — $46,800 inc GST, 7 weeks, Kira supervising. Client: D. Halloran (related party, arm's length rates applied).",
      month_start_day(10) + 12, entities=["prop_halyard", "proj_halyard", "b_con"], title="Quote 24-117", tags=("reno_quote", "reno_quote:prop_halyard"))
    for pid in ("prop_quarry", "prop_bellbird"):
        S("email", "owner", FI, f"Independent builder quote for refreshing {g.alias(pid)}: repaint, new blinds and floor coverings — about ${R.randint(14, 26)},{R.randint(1,9)}00, three weeks.",
          month_start_day(R.randint(13, 16)) + 5, entities=[pid], title="Builder quote", tags=("reno_quote", f"reno_quote:{pid}"))
    # Investment meeting / accountant notes
    S("meeting", "owner", FI, "Sat-morning money meeting with Priya: decided no new purchase until the offset is back above the buffer goal; next property must be interstate and under $750k; revisit after the June valuations.",
      month_start_day(14) + 6, entities=["fin_portfolio", "fin_offset", "p_priya"], tags=("inv_decision",))
    S("meeting", "owner", FI, "Earlier money meeting: happy to buy again locally this year if yield is above 5%; keep LVR under 70%.",
      month_start_day(3) + 6, entities=["fin_portfolio", "p_priya"], tags=("inv_decision_old",))
    # Holding notes
    for h in [e for e in g.entities.values() if e["kind"] == "holding"]:
        S("note", "owner", FI, R.choice([
            f"Thesis for {h['name']}: long-term core position, only trim if it gets above 15% of the share portfolio.",
            f"{h['aliases'][1]} — speculative; cap it at a small slice and don't average down.",
            f"Why I own {h['aliases'][1]}: dividends and defensive; happy to hold through volatility."]),
          month_start_day(R.randint(1, 8)) + 3, entities=[h["id"]], tags=("thesis", f"thesis:{h['id']}"))

    # ---- gym
    GO, GF = "business/gym/ops", "business/gym/finance"
    S("meeting", "biz/gym", GO, "Partners meeting (Lachlan, Dane): hiring freeze on new coaches until we're consistently above 400 active members; use casual cover for peaks.",
      month_start_day(8) + 9, entities=["b_gym", "p_lachlan"], title="Partners meeting minutes", tags=("gym_hire_decision",))
    S("meeting", "biz/gym", GF, "Partners meeting: price rise to $35/week approved from July; grandfather existing members for three months.",
      month_start_day(6) + 3, entities=["b_gym", "p_lachlan"], tags=("gym_price_decision",))
    S("meeting", "biz/gym", GF, "Partners meeting: committed $45k for the recovery-room fit-out, deposit paid, install booked for August 2026. Funds come from gym reserve plus a $15k owner contribution each.",
      month_start_day(14) + 11, entities=["b_gym", "p_lachlan", "p_dane"], tags=("gym_fitout",))
    S("note", "biz/gym", GO, "Rack audit: three of the Forge squat racks have worn J-hooks and one has a cracked weld on the upright — out of service until replaced.",
      month_start_day(10) + 8, entities=["b_gym", "sup_forge"], tags=("gym_equipment_issue",))
    S("note", "biz/gym", GO, "Peak-hour headcount: 6am strength classes at capacity four days out of five; waitlist averaging 7.",
      month_start_day(15) + 8, entities=["b_gym"], tags=("gym_capacity",))
    for sid, price in (("sup_titanbar", "$3,950"), ("sup_apex", "$4,400")):
        S("email", "biz/gym", GO, f"Quote from {g.entities[sid]['name']}: commercial power rack with safeties {price} each, 6-week lead time, 10-year frame warranty.",
          month_start_day(R.randint(10, 11)) + 12, entities=["b_gym", sid], tags=("gym_rack_quote",))
    S("email", "biz/gym", GO, "Talbot Linen has been reliable for us all year — every towel delivery on time, one invoice error fixed same day.",
      month_start_day(15) + 2, entities=["b_gym", "sup_talbot"], tags=("talbot_gym_feedback",))
    S("note", "biz/gym", GO, "Jordan Pike starting as a part-time coach — mornings at the gym, still doing two cafe shifts a week for now.",
      month_start_day(13) + 9, entities=["b_gym", "s_jordan_pike", "b_cafe"], tags=("jordan_gym",))
    # ---- construction
    CO, CF = "business/construction/ops", "business/construction/finance"
    S("note", "biz/construction", CO, "Kira is running all four sites; can't take another job before September without a second supervisor.",
      month_start_day(15) + 4, entities=["b_con", "s_kira_matthews"], tags=("con_capacity",))
    S("meeting", "biz/construction", CF, "Office meeting (Rhea, Dane): tender only where margin is at least 12% and we have supervisor capacity; decline anything with liquidated damages above $1k/day.",
      month_start_day(12) + 14, entities=["b_con", "p_rhea"], tags=("con_tender_decision",))
    S("note", "biz/construction", CO, "Brightwater Plumbing: good work on Corran Heights but invoices slow; their apprentice no-showed twice in March.",
      month_start_day(14) + 2, entities=["b_con", "sup_brightwater"], tags=("brightwater_con_feedback",))
    # ---- cafe
    CaO, CaF = "business/cafe/ops", "business/cafe/finance"
    for i in range(5):
        S("chat", "biz/cafe", CaO, R.choice([
            "Beans didn't turn up again this morning — had to buy retail bags from the supermarket to get through.",
            "Ember & Oak delivery came at 11 instead of 6, we nearly ran out of the house blend.",
            "Roaster missed the Tuesday drop again. Third time this month.",
            "No coffee delivery today, called the roaster and got voicemail.",
            "Short-shipped on decaf and the house blend; invoice still charged the full order."]),
          month_start_day(15 + i // 2) + R.randint(1, 25), entities=["b_cafe", "sup_emberoak"], tags=("bean_incident",))
    S("email", "biz/cafe", CaO, "Ember & Oak Coffee supply agreement: 12-month term from October 2025, 30 days' written notice to terminate, minimum order 40kg a week.",
      month_start_day(9) + 6, entities=["b_cafe", "sup_emberoak"], tags=("bean_contract",))
    for sid, txt in (("sup_saltbush", "Saltbush Coffee Roasters quote: house blend $34/kg, deliveries Mon/Wed/Fri before 6am, no minimum, free grinder service."),
                     ("sup_northside", "Northside Roastery quote: $31/kg at 50kg+ a week, deliveries twice a week, 3-month trial with no lock-in."),
                     ("sup_ridgeback", "Ridgeback Roasters would take us back at $33/kg; same delivery days as before.")):
        S("email", "biz/cafe", CaO, txt, month_start_day(16) + R.randint(1, 20), entities=["b_cafe", sid], tags=("bean_quote",))
    S("chat", "biz/cafe", CaO, "Milk was off again from Valley Fresh — two crates binned.",
      month_start_day(3) + 10, entities=["b_cafe", "sup_valley"], tags=("milk_incident",))
    S("chat", "biz/cafe", CaO, "Valley Fresh late for the third week; customers waiting on flat whites.",
      month_start_day(4) + 7, entities=["b_cafe", "sup_valley"], tags=("milk_incident",))
    S("email", "biz/cafe", CaO, "Greenhill Dairy Co-op quote: $1.62/L, daily 5am delivery, credit for spoiled stock.",
      month_start_day(4) + 18, entities=["b_cafe", "sup_greenhill"], tags=("milk_quote",))
    S("meeting", "biz/cafe", CaO, "Partners (Tomas, Dane): Sunday trading trial approved — 8am to 1pm, two staff, review after three months on covers and wage cost.",
      month_start_day(10) + 22, entities=["b_cafe", "p_tomas"], tags=("cafe_sunday_decision",))
    S("note", "biz/cafe", CaO, "Roster: weekday core is Mei, Olly, Ana; Kit covers weekends; Jordan only two shifts now he's coaching.",
      month_start_day(14) + 3, entities=["b_cafe", "s_mei_tran", "s_jordan_pike"], tags=("cafe_roster",))
    S("email", "biz/cafe", CaO, "PeopleWorks Hospitality Recruitment: placement fee 12% of first-year salary for a senior barista, shortlist within 10 days.",
      month_start_day(13) + 1, entities=["b_cafe", "sup_peopleworks"], tags=("cafe_recruit_quote",))
    S("chat", "biz/cafe", CaO, "Talbot linen delivery was short two bags of tea towels; they credited it straight away.",
      month_start_day(12) + 5, entities=["b_cafe", "sup_talbot"], tags=("talbot_cafe_feedback",))
    S("note", "biz/cafe", CaO, "Brightwater fixed the grease trap overflow same day — pricey but reliable for the cafe.",
      month_start_day(11) + 19, entities=["b_cafe", "sup_brightwater"], tags=("brightwater_cafe_feedback",))

    # ---- health
    HT = "health/training"
    S("note", "owner", HT, "Ben's advice on the stall: drop the top sets for three weeks, add paused squats and box squats, and fix the bracing — sleep is the limiter, not the program.",
      month_start_day(15) + 12, entities=["tr_me", "s_ben_okafor"], tags=("coach_advice",))
    S("note", "owner", HT, "Left knee niggle after the long run — physio says patellar tendon irritation; keep squat depth controlled and cut running volume for a fortnight.",
      month_start_day(13) + 20, entities=["tr_me"], tags=("knee_note",))
    S("note", "owner", HT, "Since the cafe opened earlier and I'm doing the 6:30 opens twice a week, my 6am sessions are getting skipped. Need to move training to lunchtime or evenings.",
      month_start_day(12) + 15, entities=["tr_me", "b_cafe"], tags=("training_clash",))
    S("note", "owner", HT, "Running plan: two easy runs and one interval session a week, long run Sunday, building to the 10k time trial.",
      month_start_day(10) + 6, entities=["tr_me", "goal_run"], tags=("run_plan",))
    # ---- reading preferences (with drift)
    books = g._books
    genres = sorted({b["genre"] for b in books})
    likes = ["history", "popular science", "literary fiction", "crime"]
    for gname in likes:
        S("preference", "owner", "reading", R.choice([f"I really enjoy {gname} — more of that please.", f"Always happy with a good {gname} book.", f"Note: {gname} is a reliable win for me."]),
          month_start_day(R.randint(0, 10)) + 3, entities=["rd_me"], tags=("reading_pref", "reading_pref_current", f"genre_like:{gname}"))
    S("preference", "owner", "reading", "Love fantasy series, the longer the better.", month_start_day(1) + 3, entities=["rd_me"],
      tags=("reading_pref", "reading_pref_stale", "genre_like:fantasy"))
    S("preference", "owner", "reading", "Gone right off fantasy — couldn't finish the last two. Skip those.", month_start_day(11) + 3,
      entities=["rd_me"], tags=("reading_pref", "reading_pref_current", "genre_dislike:fantasy"))
    S("preference", "owner", "reading", "Business books feel like padded blog posts to me; avoid unless someone I trust insists.", month_start_day(6) + 3,
      entities=["rd_me"], tags=("reading_pref", "reading_pref_current", "genre_dislike:business"))
    lovedb = [b for b in books if b["genre"] in likes][:6]
    for b in lovedb:
        S("preference", "owner", "reading", f"Finished {b['title']} by {b['author']} — loved it. Want more from {b['author'].split()[-1]}.",
          month_start_day(R.randint(2, 17)) + 9, entities=["rd_me", b["id"]], tags=("reading_pref", "book_loved", "reading_pref_current"))
    S("note", "owner", "reading", "Wishlist from friends: " + ", ".join(f"{b['title']} ({b['author']})" for b in R.sample(books, 5)) + ".",
      month_start_day(16) + 2, entities=["rd_me"], tags=("reading_wishlist",))
    # ---- family preferences
    FL = "family/leisure"
    places = [("pl_saltmarsh", "Saltmarsh Beach", "the kids love the rock pools"),
              ("pl_ferngully", "Ferngully Adventure Park", "Theo's favourite — high ropes course"),
              ("pl_lantern", "Lantern Hill Lookout", "easy walk, Ruby can manage it"),
              ("pl_bramble", "Bramble Creek Farm", "pick-your-own berries, Ruby loved it"),
              ("pl_tidewater", "Tidewater Aquatic Centre", "wave pool; Mila trains here too"),
              ("pl_maple", "Maple & Fig", "Priya's favourite restaurant — share plates"),
              ("pl_koto", "Koto Izakaya", "we all liked it, good for birthdays"),
              ("pl_greystone", "Greystone Lodge", "winter weekend away, fireplace, kids bored by day 2"),
              ("pl_coralbay", "Coral Bay Holiday Park", "best family holiday so far — cabins by the beach")]
    for pid, name, why in places:
        g.ent(pid, "place", name, [name.split()[0]], ["household"], scope=FL)
    for pid, name, why in places[:5]:
        S("preference", "household", FL, f"{name}: {why}.", month_start_day(R.randint(0, 16)) + 3, entities=[pid, "p_dane"],
          tags=("family_place_pref", f"place:{pid}"))
    for kid, txt in (("p_mila", "Mila wants weekends free for water polo friends now — swimming carnivals are a no."),
                     ("p_theo", "Theo is obsessed with basketball; anything with a hoop wins."),
                     ("p_ruby", "Ruby loves animals and anything crafty; gets tired after about two hours out.")):
        S("preference", "household", FL, txt, month_start_day(R.randint(9, 16)) + 5, entities=[kid], tags=("kid_pref", f"kid_pref:{kid}"))
    S("preference", "household", FL, "Mila used to love swim carnivals and early training.", month_start_day(2) + 5, entities=["p_mila"], tags=("kid_pref_stale",))
    S("preference", "household", FL, "Priya: loves share plates and Japanese; not into steakhouses; prefers somewhere quiet enough to talk.",
      month_start_day(8) + 5, entities=["p_priya"], tags=("priya_food_pref",))
    S("preference", "household", FL, "Maple & Fig and Koto Izakaya are our two go-to places for special occasions.", month_start_day(12) + 5,
      entities=["pl_maple", "pl_koto"], tags=("restaurant_pref",))
    S("preference", "household", FL, "Ruby has a tree-nut allergy — always check menus.", month_start_day(0) + 25, entities=["p_ruby"], tags=("allergy",))
    S("preference", "household", FL, "Holiday lessons learned: beach + cabin beats cold lodges; max 4 hours driving with the kids; book somewhere with a pool.",
      month_start_day(11) + 10, entities=["p_dane", "p_priya"], tags=("holiday_pref",))
    S("preference", "household", FL, "Coral Bay Holiday Park: best family holiday so far — cabins by the beach.", month_start_day(4) + 10,
      entities=["pl_coralbay"], tags=("holiday_pref",))
    S("note", "household", FL, "Mila's coach: on current trend she should go under 1:05 by mid-year if she keeps the Saturday sessions and adds one dryland session.",
      month_start_day(15) + 12, entities=["p_mila"], tags=("mila_coach_note",))
    S("note", "household", FL, "Priya's thinking of pausing her gym membership over winter — says she's not getting there.",
      month_start_day(15) + 22, entities=["p_priya", "b_gym"], tags=("priya_gym_pause",))
    # Priya's own member partition note (shared entity Priya)
    S("log", "member/m03", "business/gym/members", "Priya Halloran attendance: 3 visits in the last 8 weeks; asked about freezing the membership.",
      month_start_day(16) + 3, entities=["p_priya", "b_gym"], tags=("priya_member_note",))
    # member preference notes
    for m in MEMBER_IDS:
        eid = "p_priya" if m == "m03" else f"mem_{m}"
        S("preference", f"member/{m}", "business/gym/members", R.choice([
            "Prefers early morning classes; dislikes high-impact jumping because of ankles.",
            "Enjoys strength work, wants to learn the Olympic lifts eventually.",
            "Likes group classes for motivation; struggles with solo sessions.",
            "Goal is general fitness and mobility; finds HIIT too intense."]),
          month_start_day(R.randint(2, 14)) + 4, entities=[eid], tags=("member_pref", f"member_pref:{m}"))
        S("log", f"member/{m}", "business/gym/members", R.choice([
            "Coach check-in: technique improving; next step add a fourth weekly session.",
            "Check-in: missed two weeks with illness, ease back in.",
            "Check-in: progressing well, ready for a new block next month."]),
          month_start_day(R.randint(14, 17)) + 4, entities=[eid], tags=("member_checkin", f"member_checkin:{m}"))


# ---------------------------------------------------------------- filler (realistic distractors)
def build_filler(g: Gen):
    R = g.rng
    people_gym = ["Sasha", "Ben", "Imogen", "Raf", "Corey", "Tess", "Jordan", "Lachlan"]
    people_cafe = ["Mei", "Olly", "Ana", "Kit", "Jordan", "Tomas"]
    people_con = ["Ross", "Kira", "Dev", "Sione", "Gus", "Wade", "Rhea"]
    projs = [e for e in g.entities.values() if e["kind"] == "project"]
    props = [e for e in g.entities.values() if e["kind"] == "property"]
    holds = [e for e in g.entities.values() if e["kind"] == "holding"]
    books = g._books

    def days(n):
        return sorted(R.randint(0, NOW_DAY) for _ in range(n))

    # training logs (owner)
    ex = ["squats", "bench", "deadlifts", "overhead press", "rows", "pull-ups", "lunges", "intervals", "easy run", "tempo run"]
    for d in days(520):
        a, b = R.sample(ex, 2)
        g.add("log", "owner", "health/training", R.choice([
            f"Session: {a} {R.randint(3,5)}x{R.randint(3,8)}, then {b}. RPE {R.randint(6,9)}.",
            f"Trained {a} and {b}. Felt {R.choice(['flat', 'strong', 'tired', 'good', 'sore'])}.",
            f"{a.capitalize()} day — top set moved well, {b} accessories after.",
            f"Short session, {a} only. {R.choice(['Slept badly.', 'Busy day.', 'Back felt tight.', 'Good energy.'])}"]),
              d, entities=["tr_me"], tags=("training_log",))
    # cafe team chat
    items_c = ["oat milk", "takeaway cups", "lids", "banana bread", "sourdough", "eggs", "decaf", "chai", "napkins", "almond milk", "croissants"]
    for d in days(700):
        g.add("chat", "biz/cafe", R.choice(["business/cafe/ops", "business/cafe/ops", "business/cafe/finance"]), R.choice([
            f"{R.choice(people_cafe)}: can someone swap my {R.choice(['Tue', 'Wed', 'Thu', 'Sat'])} shift?",
            f"{R.choice(people_cafe)}: we're low on {R.choice(items_c)}, ordering more.",
            f"Busy morning, {R.randint(150, 320)} covers by 11.",
            f"Customer feedback: loved the {R.choice(['flat white', 'smashed avo', 'banana bread', 'chai'])}.",
            f"{R.choice(people_cafe)}: grinder needs a clean, coffee tasting bitter.",
            f"Delivery of {R.choice(items_c)} arrived and checked in.",
            f"Till was ${R.randint(-20, 20)} out at close, recounted.",
            f"Supplier invoice for {R.choice(items_c)} paid.",
            f"Wages this week came to about ${R.randint(5, 9)},{R.randint(100, 999)}.",
            f"Coffee machine service booked for {R.choice(['Monday', 'next week', 'Friday arvo'])}."]),
              d, entities=["b_cafe"], tags=("cafe_chat",))
    # gym ops
    for d in days(700):
        g.add(R.choice(["chat", "log"]), "biz/gym", R.choice(["business/gym/ops", "business/gym/ops", "business/gym/finance"]), R.choice([
            f"{R.choice(people_gym)}: 6am class had {R.randint(8, 22)} in it.",
            f"{R.choice(people_gym)}: rower {R.randint(1, 6)} making a noise, tagged out.",
            f"New member sign-ups this week: {R.randint(2, 11)}.",
            f"{R.choice(people_gym)}: covering {R.choice(['Tue', 'Thu', 'Sat'])} HIIT for {R.choice(people_gym)}.",
            f"Cleaning roster updated, {R.choice(people_gym)} on Sunday.",
            f"Cancellations this week: {R.randint(0, 6)}; reasons mostly {R.choice(['moving', 'cost', 'injury', 'not using it'])}.",
            f"Direct debits failed: {R.randint(1, 9)}, follow-up emails sent.",
            f"Towels delivered, {R.randint(4, 10)} bags.",
            f"{R.choice(people_gym)}: dumbbell rack needs reorganising.",
            f"Power bill for the gym came in at ${R.randint(1, 3)},{R.randint(100, 999)}."]),
              d, entities=["b_gym"], tags=("gym_chat",))
    # public gym noticeboard
    for d in days(120):
        g.add("note", "public/gym", "business/gym/ops", R.choice([
            "Reminder: please re-rack your weights.", "Public holiday hours: 8am–12pm.",
            f"Challenge of the month: {R.choice(['1000 burpees', '50km row', 'plank ladder'])}.",
            "Lost property box is overflowing — collect by Friday.", "Mobility workshop this Sunday, free for members."]),
              d, entities=["b_gym"], tags=("gym_notice",))
    # member logs
    for m in MEMBER_IDS:
        eid = "p_priya" if m == "m03" else f"mem_{m}"
        for d in days(28):
            g.add("log", f"member/{m}", "business/gym/members", R.choice([
                f"Checked in at {R.choice(['5:58am', '6:31am', '12:10pm', '5:45pm', '6:02pm'])}.",
                f"Workout logged: {R.choice(ex)} and {R.choice(ex)}.",
                f"Booked {R.choice(['strength', 'HIIT', 'mobility', 'team WOD'])} class.",
                f"Body comp scan: {R.randint(14, 32)}% body fat."]),
                  d, entities=[eid], tags=("member_log",))
    # construction site diaries
    for d in days(800):
        p = R.choice(projs)
        g.add(R.choice(["log", "chat"]), "biz/construction", R.choice(["business/construction/ops"] * 3 + ["business/construction/finance"]), R.choice([
            f"Site diary {p['aliases'][0]}: {R.choice(people_con)} on site, {R.choice(['rain delay', 'framing progressing', 'waiting on inspection', 'plumber rough-in', 'electrician on site', 'skip bin swapped'])}.",
            f"{R.choice(people_con)}: concrete pour at {p['aliases'][0]} {R.choice(['booked', 'postponed', 'done'])}.",
            f"Variation request on {p['aliases'][0]}: client wants {R.choice(['extra power points', 'a bigger window', 'different tiles', 'a skylight'])}.",
            f"Invoice sent for {p['aliases'][0]} progress claim {R.randint(2, 6)}.",
            f"Safety walk at {p['aliases'][0]}: {R.choice(['all good', 'missing edge protection fixed', 'housekeeping needs work'])}.",
            f"Timber delivery for {p['aliases'][0]} {R.choice(['arrived', 'short by 20 lengths', 'delayed a day'])}.",
            f"{R.choice(people_con)}: need the {R.choice(['scissor lift', 'laser level', 'compactor'])} back by Friday."]),
              d, entities=["b_con", p["id"]], tags=("con_diary",))
    # household chat
    for d in days(900):
        kid = R.choice(["Mila", "Theo", "Ruby"])
        g.add("chat", "household", "family/leisure", R.choice([
            f"Can you grab {kid} from {R.choice(['school', 'training', 'a friend’s place'])} at {R.choice(['3:15', '4:30', '5:45'])}?",
            f"Groceries: {R.choice(['milk', 'bread', 'apples', 'pasta', 'yoghurt'])}, {R.choice(['eggs', 'rice', 'chicken', 'cheese'])}.",
            f"{kid} has a {R.choice(['school excursion', 'dentist appointment', 'birthday party', 'mufti day'])} on {R.choice(['Tuesday', 'Friday', 'Saturday'])}.",
            f"Dinner plan: {R.choice(['tacos', 'stir fry', 'pasta bake', 'roast chook', 'pizza night'])}.",
            f"{kid} needs new {R.choice(['shoes', 'goggles', 'a uniform', 'a library bag'])}.",
            f"Weekend? Maybe {R.choice(['the beach', 'the park', 'a movie', 'the markets', 'grandma’s'])}.",
            f"Reminder: {R.choice(['bins out tonight', 'car rego due', 'school fees', 'swim fees'])}."]),
              d, entities=["p_dane"], tags=("family_chat",))
    # investment filler (owner)
    for d in days(320):
        p = R.choice(props); h = R.choice(holds)
        g.add(R.choice(["note", "email"]), "owner", "finance/investments", R.choice([
            f"Rental statement for {p['aliases'][0]}: rent received, management fee deducted, {R.choice(['no maintenance', 'gutter clean', 'tap washer replaced', 'smoke alarm check'])}.",
            f"Council rates notice for {p['aliases'][0]} — due in 30 days.",
            f"Read an article on {R.choice(['interest rates', 'rental vacancy', 'regional growth', 'land tax'])}; worth watching.",
            f"{h['name']} announced {R.choice(['results', 'a dividend', 'a capital raise', 'a CEO change'])}.",
            f"Insurance renewal for {p['aliases'][0]} — premium {R.choice(['up a bit', 'flat', 'up 9%'])}.",
            f"Maintenance request at {p['aliases'][0]}: {R.choice(['dishwasher', 'hot water', 'fence', 'garage door'])}."]),
              d, entities=[p["id"], h["id"]], tags=("inv_filler",))
    # reading notes
    for d in days(260):
        b = R.choice(books)
        g.add("note", "owner", "reading", R.choice([
            f"Highlight from {b['title']}: \"{R.choice(['what we notice becomes our world', 'every map is a lie of omission', 'patience is a strategy', 'the river does not hurry'])}\".",
            f"Halfway through {b['title']}, {R.choice(['slow going', 'gripping', 'not sure yet'])}.",
            f"{b['author']} interview on a podcast — interesting on {R.choice(['craft', 'research', 'history'])}."]),
              d, entities=[b["id"], "rd_me"], tags=("reading_note",))
    # business emails
    for d in days(350):
        b, part, sc = R.choice([("b_gym", "biz/gym", "business/gym/finance"), ("b_cafe", "biz/cafe", "business/cafe/finance"),
                                ("b_con", "biz/construction", "business/construction/finance")])
        g.add("email", part, sc, R.choice([
            f"BAS reminder for {g.entities[b]['name']} — lodge by the 28th.",
            f"Bank feed: {g.entities[b]['aliases'][0]} account reconciled for the month.",
            f"Accountant: please send {g.entities[b]['aliases'][0]} receipts for the quarter.",
            f"Software subscription renewal for {g.entities[b]['aliases'][0]}.",
            f"Supplier statement for {g.entities[b]['aliases'][0]} — {R.randint(2, 9)} invoices outstanding."]),
              d, entities=[b], tags=("biz_email",))


# ---------------------------------------------------------------- media stand-ins
def build_media(g: Gen):
    R = g.rng
    projs = [e for e in g.entities.values() if e["kind"] == "project"]
    props = [e for e in g.entities.values() if e["kind"] == "property"]

    def media(kind, partition, scope, caption, day, origin, entities, tags=(), origin_only=False, ocr="", transcript=""):
        text = caption
        if ocr:
            text += " " + ocr
        if transcript:
            text += " " + transcript
        return g.add(kind, partition, scope, text.strip(), day, entities=entities, tags=tags,
                     media=dict(caption=caption, ocr=ocr, transcript=transcript, origin=origin, origin_only=origin_only))

    # --- target media (task-linked). origin_only=True => identifying words only in origin context
    defects = ["hairline crack along the edge of the slab", "water pooling at the base of the wall", "gap between the window frame and the cladding",
               "chipped tile near the shower recess", "sagging gutter at the back corner"]
    for p in projs:
        for i, dfx in enumerate(R.sample(defects, 2)):
            oo = (i == 0)
            cap = f"{dfx}" if oo else f"{p['aliases'][0]}: {dfx}"
            media("image", "biz/construction", "business/construction/ops", cap, month_start_day(R.randint(6, 17)) + 3,
                  origin=dict(folder=f"Stonefield/Sites/{p['name']}/Defects", album="", chat="Stonefield office", shared_by=R.choice(["Kira Matthews", "Ross Delaney"])),
                  entities=["b_con", p["id"]], tags=("mm_target", f"mm_defect:{p['id']}:{i}"), origin_only=oo)
    for i, topic in enumerate(["membership pricing tiers", "summer timetable", "recovery room layout"]):
        oo = i % 2 == 0
        ocr = {"membership pricing tiers": "Tier A 29/wk  Tier B 35/wk  Unlimited 42/wk  student -15%",
               "summer timetable": "5:30 STR  6:30 STR  12:10 EXPRESS  6PM HIIT",
               "recovery room layout": "sauna | cold plunge x2 | compression boots | stretch zone"}[topic]
        cap = "whiteboard photo" if oo else f"whiteboard: {topic}"
        media("image", "biz/gym", "business/gym/ops", cap, month_start_day(R.randint(6, 16)) + 9,
              origin=dict(folder="", album="", chat="IronBark partners", shared_by="Lachlan Moore",
                          adjacent_text=f"from today's partners meeting re {topic}" if oo else ""),
              entities=["b_gym"], tags=("mm_target", f"mm_whiteboard:{i}"), origin_only=oo, ocr=ocr)
    for lift in ("squat", "bench", "deadlift"):
        for i in range(2):
            oo = i == 0
            tr = {"squat": "hips below parallel, knees tracking out, good brace", "bench": "touch point a bit high, keep the arch",
                  "deadlift": "bar drifting forward off the floor, lats tighter"}[lift]
            cap = "form check" if oo else f"{lift} form check"
            media("video_segment", "owner", "health/training", cap, month_start_day(R.randint(4, 17)) + 2,
                  origin=dict(folder="", album=f"Training/Form checks/{lift.capitalize()}", chat="", shared_by="Ben Okafor"),
                  entities=["tr_me", "s_ben_okafor"], tags=("mm_target", f"mm_form:{lift}:{i}"), origin_only=oo, transcript=f"Coach: {tr}")
    for p in props:
        oo = R.random() < 0.5
        cap = "page 1 of 6" if oo else f"Valuation report — {p['name']}"
        val_vid = g.head(f"{p['id']}.valuation")
        media("page", "owner", "finance/investments", cap, g.by_id[val_vid]["valid_from"] + 2,
              origin=dict(folder=f"Investments/{p['name']}/Valuations", album="", chat="", shared_by="Nadia Ferris"),
              entities=[p["id"]], tags=("mm_target", f"mm_valreport:{p['id']}"), origin_only=oo,
              ocr="Market value assessment. Comparable sales. Valuer's certificate." if oo else f"Market value assessment {g.by_id[val_vid]['value_str']}")
    for kid, ev, desc in (("p_ruby", "piano recital", "on stage in the blue dress"), ("p_mila", "regional swim meet", "diving off the blocks, lane 4"),
                          ("p_theo", "basketball grand final", "team holding the trophy")):
        for i in range(3):
            oo = i < 2
            cap = desc if oo else f"{g.entities[kid]['name']} {ev}: {desc}"
            media("image", "household", "family/leisure", cap, month_start_day(R.randint(12, 17)) + 6,
                  origin=dict(folder="", album=f"{g.entities[kid]['name']} — {ev}", chat="Halloran family", shared_by="Priya Halloran"),
                  entities=[kid], tags=("mm_target", f"mm_family:{kid}"), origin_only=oo)
    receipts = [("biz/cafe", "business/cafe/ops", "b_cafe", "Copperleaf/Receipts/2026", "Grinder burr replacement $640 + labour"),
                ("biz/gym", "business/gym/ops", "b_gym", "IronBark/Receipts/2026", "Cable machine pulley service $380"),
                ("biz/construction", "business/construction/finance", "b_con", "Stonefield/Receipts/2026", "Laser level hire 3 days $210")]
    for part, sc, b, folder, ocr in receipts:
        for i in range(2):
            oo = i == 0
            media("page", part, sc, "receipt" if oo else f"{g.entities[b]['name']} receipt", month_start_day(R.randint(12, 17)) + 4,
                  origin=dict(folder=folder, album="", chat="", shared_by=R.choice(["Tomas Abiodun", "Lachlan Moore", "Rhea Castell"])),
                  entities=[b], tags=("mm_target", f"mm_receipt:{b}:{i}"), origin_only=oo, ocr=ocr if i == 0 else ocr.split("$")[0])

    rooms = ["kitchen", "living room", "back yard", "main bedroom"]
    for p in props:
        for i, room in enumerate(R.sample(rooms, 2)):
            oo = i == 0
            media("image", "owner", "finance/investments", room if oo else f"{p['aliases'][0]} {room}", month_start_day(R.randint(8, 16)) + 7,
                  origin=dict(folder=f"Investments/{p['name']}/Listing photos", album="", chat="", shared_by="Harbourline Property Management"),
                  entities=[p["id"]], tags=("mm_target", f"mm_listing:{p['id']}:{i}"), origin_only=oo)
    for i, board in enumerate(["breakfast menu", "lunch specials", "drinks and pricing"]):
        oo = i != 1
        ocr = {"breakfast menu": "smashed avo 19 | big breakfast 24 | granola 14",
               "lunch specials": "chicken burger 21 | soup of the day 15",
               "drinks and pricing": "flat white 5.2 | oat +0.8 | cold brew 6.5"}[board]
        media("image", "biz/cafe", "business/cafe/ops", "chalkboard" if oo else f"Copperleaf {board}", month_start_day(R.randint(10, 16)) + 3,
              origin=dict(folder="Copperleaf/Menu/2026", album="", chat="Copperleaf team", shared_by="Tomas Abiodun", adjacent_text=f"new {board} board"),
              entities=["b_cafe"], tags=("mm_target", f"mm_menu:{i}"), origin_only=oo, ocr=ocr)

    # --- distractor media (bulk)
    gen_caps = ["photo", "IMG", "screenshot", "pic", "video clip", "scan", "photo of the whiteboard", "progress photo",
                "receipt", "form check", "page 2", "family photo", "selfie", "view from the site"]
    folders = {
        "owner": ["Investments/Misc", "Training/Progress", "Reading/Covers", "Camera Roll"],
        "household": ["Family/Camera Roll", "Family/School", "Family/Holidays"],
        "biz/gym": ["IronBark/Marketing", "IronBark/Equipment", "IronBark/Receipts/2025"],
        "biz/construction": [f"Stonefield/Sites/{p['name']}/Progress" for p in projs] + ["Stonefield/Receipts/2025"],
        "biz/cafe": ["Copperleaf/Menu", "Copperleaf/Receipts/2025", "Copperleaf/Social"],
    }
    scope_of = {"owner": ["finance/investments", "health/training", "reading"], "household": ["family/leisure"],
                "biz/gym": ["business/gym/ops"], "biz/construction": ["business/construction/ops"], "biz/cafe": ["business/cafe/ops"]}
    for _ in range(1500):
        part = R.choice(list(folders))
        kind = R.choice(["image", "image", "image", "video_segment", "page"])
        cap = R.choice(gen_caps)
        if R.random() < 0.4:
            cap += " " + R.choice(["morning", "after", "before", "v2", "close-up", "wide", "draft", "old"])
        ocr = R.choice(["", "", "Total $" + str(R.randint(12, 900)), "Invoice", "Tax invoice GST", "Page " + str(R.randint(1, 9))]) if kind == "page" else ""
        tr = R.choice(["", "talking through the set", "walk-through of the site", "kids laughing"]) if kind == "video_segment" else ""
        media(kind, part, R.choice(scope_of[part]), cap, R.randint(0, NOW_DAY),
              origin=dict(folder=R.choice(folders[part]), album="", chat=R.choice(["", "", "Halloran family", "Copperleaf team", "IronBark partners", "Stonefield office"]) if part != "owner" else "",
                          shared_by=R.choice(["Dane Halloran", "Priya Halloran", "Lachlan Moore", "Kira Matthews", "Tomas Abiodun", ""])),
              entities=[], tags=("mm_filler",), ocr=ocr, transcript=tr)


# ---------------------------------------------------------------- canaries
def build_canaries(g: Gen):
    R = g.rng
    words = ["ZEPHYR", "QUILL", "MARBLE", "OSPREY", "LUMEN", "CINDER", "FATHOM", "TALON", "VESPER", "NOMAD", "ARBOR", "GLYPH",
             "SABLE", "RIVET", "KESTRA", "PLINTH", "MORROW", "ONYX", "BRISK", "CAIRN"]
    anchor = {"owner": ["prop_halyard", "s_ben_okafor"], "household": ["p_priya"], "biz/gym": ["sup_talbot", "s_jordan_pike", "p_priya"],
              "biz/construction": ["sup_brightwater", "prop_halyard"], "biz/cafe": ["sup_talbot", "sup_brightwater", "s_jordan_pike"],
              "public/gym": ["b_gym"]}
    used = set()
    for part in PARTITIONS:
        while True:
            tok = f"{R.choice(words)}-{R.choice(words)}-{R.randint(1000, 9999)}"
            if tok not in used:
                used.add(tok)
                break
        ents = anchor.get(part)
        if ents is None:  # member partitions: anchor on member + coach
            m = part.split("/")[1]
            eid = "p_priya" if m == "m03" else f"mem_{m}"
            coach_edge = [e["dst"] for e in g.edges if e["src"] == eid and e["rel"] == "coached_by"]
            ents = [eid] + coach_edge
        names = ", ".join(g.entities[e]["name"] for e in ents)
        g.add("canary", part, None, f"Reference marker {tok} — internal note regarding {names}.", R.randint(100, NOW_DAY),
              entities=ents, tags=("canary", f"canary:{part}"), canary_token=tok)


# ================================================================ tasks
from . import tasks as _tasks  # noqa: E402


def main(seed: int = 20261023):
    g = build(seed)
    _tasks.build_tasks(g)
    os.makedirs(DATA_DIR, exist_ok=True)
    write_jsonl(os.path.join(DATA_DIR, "items.jsonl"), g.items)
    write_jsonl(os.path.join(DATA_DIR, "entities.jsonl"), g.entities.values())
    write_jsonl(os.path.join(DATA_DIR, "edges.jsonl"), g.edges)
    write_jsonl(os.path.join(DATA_DIR, "keys.jsonl"), g.keys.values())
    write_jsonl(os.path.join(DATA_DIR, "tasks.jsonl"), g.tasks)
    with open(os.path.join(DATA_DIR, "meta.json"), "w") as f:
        json.dump(dict(seed=seed, now_day=NOW_DAY, identities=IDENTITIES, scopes=SCOPES, partitions=PARTITIONS), f, indent=1)
    return g


if __name__ == "__main__":
    g = main()
    from collections import Counter
    print(len(g.items), "items;", len(g.entities), "entities;", len(g.keys), "keys;", len(g.tasks), "tasks")
    print(Counter(i["type"] for i in g.items))
    print(Counter(t["cls"] for t in g.tasks))
