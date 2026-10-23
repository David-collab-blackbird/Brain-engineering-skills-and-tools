"""Gold task construction for BrainBench v0.

Every task records: query, requester identity, declared scope group, the exact required item IDs,
and for stale probes the superseded versions and stale-trap documents to compare against.
Required items are verified to be accessible to the requester at build time.
"""
from __future__ import annotations

import random
from collections import Counter

from .common import NOW_DAY, month_start_day

SCOPE_GROUPS = ["finance", "business/gym", "business/construction", "business/cafe", "health", "family", "reading"]


def scope_group(scope: str | None) -> str | None:
    if scope is None:
        return None
    if scope.startswith("finance/"):
        return "finance"
    if scope.startswith("business/"):
        return "/".join(scope.split("/")[:2])
    return {"health/training": "health", "family/leisure": "family", "reading": "reading"}[scope]


# ---------------------------------------------------------------- current-state question templates
Q_FAMILY = {
    "valuation": ["what would {a} fetch if we sold it today?", "what's {a} worth these days?",
                  "latest number on what {a} is worth?", "has anyone put a price on {a} recently?"],
    "loan": ["how much do we still owe on {a}?", "what's left on the mortgage for {a}?", "debt remaining against {a}?"],
    "rate": ["what interest are we paying on {a} right now?", "what rate is the {a} mortgage on?"],
    "rent": ["what's {a} bringing in each week?", "how much is the tenant at {a} paying?"],
    "pm": ["who looks after {a} for us?", "which agency manages {a}?"],
    "lease_end": ["when is the tenant at {a} up for renewal?", "when does the current lease at {a} finish?"],
    "units": ["how many {a} do I hold?", "what's my position size in {a}?"],
    "mvalue": ["what's my {a} stake worth?", "how much is the {a} position worth now?"],
    "status": ["where's {a} up to?", "how far along is {a}?", "what stage is {a} at?"],
    "revenue": ["how much did {a} take in {q}?", "{q} turnover for {a}?", "what were {a}'s sales in {q}?"],
}
Q_KEY = {
    "offset.balance": ["how much cash have we got sitting in the offset?", "what's our buffer looking like at the moment?"],
    "portfolio.borrowing_capacity": ["how much could we borrow right now?", "what's the most the bank would lend us at the moment?"],
    "portfolio.lvr_rule": ["what's our gearing limit again?", "how far are we prepared to leverage the properties?"],
    "portfolio.strategy": ["what's our property game plan these days?", "remind me of the investing approach we settled on"],
    "offset.savings_goal": ["how big a rainy-day fund did we say we wanted?", "what's the emergency money target?"],
    "household.budget": ["what's our monthly spending allowance for the house?", "what did we set the family budget at?"],
    "gym.members": ["how many people are signed up at IronBark?", "what's our member count at the gym?"],
    "gym.member_target": ["what number of members are we aiming for at the gym?", "what's the growth goal for IronBark?"],
    "gym.head_coach": ["who's in charge of the coaching team at the gym?", "who leads the coaches at IronBark now?"],
    "gym.equipment_supplier": ["who do we buy gym gear from?", "which company supplies the racks and weights?"],
    "gym.towel_supplier": ["who does the gym's towels?", "which laundry service does IronBark use?"],
    "gym.lease": ["what does the gym premises cost us each month?", "what's the rent on the IronBark building?"],
    "gym.staff_count": ["how many people work at the gym now?", "how big is the IronBark team?"],
    "gym.price": ["what do we charge for a standard membership?", "how much is a weekly membership at IronBark?"],
    "gym.timetable": ["when are classes on at the gym?", "what's the class schedule at IronBark?"],
    "con.pipeline": ["how much work has Stonefield got signed up?", "what's the forward order book for the building business?"],
    "con.active_projects": ["how many jobs is Stonefield running?", "how many sites are live at the moment?"],
    "con.concrete_supplier": ["who pours our concrete?", "which readymix company does Stonefield use?"],
    "con.supervisor": ["who's running the sites for Stonefield?", "who supervises our building jobs?"],
    "con.insurance": ["what's Stonefield paying for liability cover?", "how much is the building business's insurance?"],
    "con.plumbing_sub": ["who does Stonefield's plumbing?", "which plumber do we sub out to on builds?"],
    "con.strategy": ["what kind of jobs will Stonefield tender for?", "what's our policy on which builds we quote?"],
    "con.pipeline_target": ["how much forward work do we want Stonefield to carry?", "what's the order book goal for the building business?"],
    "cafe.bean_supplier": ["where are we getting our coffee from at Copperleaf?", "who roasts for the cafe now?"],
    "cafe.milk_supplier": ["who delivers our milk at the cafe?", "which dairy supplies Copperleaf?"],
    "cafe.linen_supplier": ["who does the cafe's tea towels and aprons?", "which linen company does Copperleaf use?"],
    "cafe.hours": ["when is the cafe open?", "what are Copperleaf's trading times?"],
    "cafe.head_barista": ["who's the lead on coffee at Copperleaf?", "who runs the machine at the cafe?"],
    "cafe.covers": ["how many customers is the cafe serving a week?", "how busy is Copperleaf week to week?"],
    "cafe.cash_reserve": ["how much money has the cafe got in the bank?", "what's Copperleaf's reserve sitting at?"],
    "cafe.revenue_goal": ["what's the sales goal for the cafe this year?", "what turnover are we targeting at Copperleaf?"],
    "cafe.distribution_rule": ["what are the rules for taking money out of the cafe?", "what does the partnership say about drawings from Copperleaf?"],
    "cafe.covers_target": ["how many customers a week are we aiming for at the cafe?", "what's the foot-traffic goal at Copperleaf?"],
    "train.squat_1rm": ["what's my best squat at the moment?", "how much can I squat now?"],
    "train.bench_1rm": ["what's my current max bench?", "how much am I benching for a single?"],
    "train.deadlift_1rm": ["what's my deadlift max?", "how heavy can I pull right now?"],
    "train.bodyweight": ["what do I weigh at the moment?", "where's my weight sitting?"],
    "train.program": ["what program am I following?", "which training plan am I on?"],
    "train.sessions": ["how often am I training per week?", "how many times a week am I getting to the gym?"],
    "train.run10k": ["what's my latest 10k time?", "how fast am I running 10 kilometres now?"],
    "train.coach": ["who's coaching me?", "who writes my training?"],
    "goal_squat.target": ["what's the squat number I'm chasing?", "remind me of my squat goal"],
    "goal_run.target": ["what time am I aiming for over 10k?", "what's my running target?"],
    "goal.deadlift": ["what deadlift am I aiming for?", "remind me of the pulling goal"],
    "goal.bench": ["what bench am I chasing?", "what's the bench press goal?"],
    "goal.bodyweight": ["what weight am I trying to get to?", "what's my target bodyweight?"],
    "reading.goal": ["how many books did I want to get through this year?", "what's my reading target?"],
    "reading.finished": ["how many books have I knocked over this year?", "how's the book count going?"],
    "reading.current": ["what am I reading at the moment?", "which book is on the go?"],
    "mila.activity": ["what's Mila doing for sport these days?", "when is Mila training?"],
    "theo.activity": ["what's Theo signed up for this term?", "when is Theo's sport on?"],
    "ruby.activity": ["what does Ruby do after school?", "what lessons is Ruby doing?"],
    "mila.swim_pb": ["what's Mila's fastest 100 free?", "Mila's best swim time?"],
    "mila.swim_goal": ["what does Mila need to swim to make regionals?", "what's Mila's qualifying target?"],
    "family.holiday_budget": ["how much did we set aside for holidays?", "what's the travel budget?"],
    "family.school_break": ["when are the spring school holidays?", "dates for the September school break?"],
}
Q_MEMBER = {
    "plan": ["what membership is {a} on?", "which plan is {a} paying for?"],
    "program": ["what's {a} doing in the gym these days?", "what training block is {a} on?"],
    "coach": ["who's looking after {a}?", "which coach is assigned to {a}?"],
    "goal": ["what's {a} working towards?", "what goal did {a} set?"],
    "progress": ["where's {a} at with their progress?", "latest progress numbers for {a}?"],
}
Q_SELF = {
    "plan": ["what plan am I on?", "which membership am I paying for?"],
    "program": ["what program have I been given?", "what should I be doing in my sessions?"],
    "coach": ["who's my coach?", "who do I talk to about my training?"],
    "goal": ["what did I say my goal was?", "remind me what I'm working towards"],
    "progress": ["how am I tracking?", "what were my latest numbers?"],
}


class TB:
    def __init__(self, g):
        self.g = g
        self.rng = random.Random(77)
        self.out = []
        from .world import IDENTITIES
        self.ident = IDENTITIES

    def tg(self, tag):
        return list(self.g.tag.get(tag, []))

    def H(self, key):
        return self.g.head(key)

    def alias(self, eid, plain=False):
        e = self.g.entities[eid]
        if plain:
            return e["aliases"][1] if len(e["aliases"]) > 1 else e["name"]
        return self.rng.choice(e["aliases"][1:] or e["aliases"])

    def add(self, cls, query, required, requester="owner", primary=None, **kw):
        g = self.g
        req = list(dict.fromkeys(r for r in required if r))
        assert req, (cls, query)
        parts = set(self.ident[requester]["partitions"])
        for r in req:
            assert g.by_id[r]["partition"] in parts, (cls, query, requester, r, g.by_id[r]["partition"])
        groups = [scope_group(g.by_id[r]["scope"]) for r in req]
        if primary is None:
            primary = Counter(groups).most_common(1)[0][0]
        t = dict(id=f"t{len(self.out)+1:05d}", cls=cls, query=query, requester=requester,
                 declared_scope=primary, required=req, required_scope_groups=sorted(set(groups)),
                 size=len(req))
        t.update(kw)
        self.out.append(t)
        return t


def _qlabel(ql):  # "2025Q3" -> "Q3 2025"
    return f"Q{ql[-1]} {ql[:4]}"


def current_state_questions(tb: TB, key: str):
    """Return list of (question, requester) for a key's current value."""
    g = tb.g
    k = g.keys[key]
    fam = k["family"]
    ent = k["entity"]
    out = []
    if key in Q_KEY:
        for q in Q_KEY[key]:
            out.append((q, "owner"))
    elif key.startswith("m") and key[1:3].isdigit():
        m, attr = key.split(".")
        name = g.entities[ent]["name"].split()[0]
        for q in Q_MEMBER[attr]:
            out.append((q.format(a=name), "partner_gym"))
        for q in Q_SELF[attr]:
            out.append((q, f"member_{m}"))
    elif fam == "revenue":
        ql = key.split(".")[-1]
        for q in Q_FAMILY["revenue"]:
            out.append((q.format(a=tb.alias(ent), q=_qlabel(ql)), "owner"))
    elif fam in Q_FAMILY:
        for q in Q_FAMILY[fam]:
            out.append((q.format(a=tb.alias(ent)), "owner"))
    # partner variants for business keys
    p = k["partition"]
    partner = {"biz/gym": "partner_gym", "biz/construction": "partner_construction", "biz/cafe": "partner_cafe"}.get(p)
    if partner:
        out = [(q, partner if i % 2 else r) for i, (q, r) in enumerate(out)]
    if p == "household":
        out = [(q, "household" if i % 2 else r) for i, (q, r) in enumerate(out)]
    return out


def build_tasks(g):
    tb = TB(g)
    R = tb.rng
    H, tg = tb.H, tb.tg
    props = [e["id"] for e in g.entities.values() if e["kind"] == "property"]
    holds = [e["id"] for e in g.entities.values() if e["kind"] == "holding"]
    projects = [e["id"] for e in g.entities.values() if e["kind"] == "project"]
    from .world import MEMBER_IDS
    mem_eid = {m: ("p_priya" if m == "m03" else f"mem_{m}") for m in MEMBER_IDS}

    # ============================================================ current_state (sizes 1-3)
    keys_sorted = sorted(g.keys)
    cs = []
    for key in keys_sorted:
        qs = current_state_questions(tb, key)
        if qs:
            q, r = qs[0]
            cs.append((q, [H(key)], r))
    for p in props:
        a = tb.alias(p)
        cs.append((f"what's our equity position in {a}?", [H(f"{p}.valuation"), H(f"{p}.loan")], "owner"))
        cs.append((f"quick rundown on the tenancy at {tb.alias(p)} — who manages it, what it rents for, when it's up", [H(f"{p}.rent"), H(f"{p}.lease_end"), H(f"{p}.pm")], "owner"))
        cs.append((f"what are the borrowing terms on {tb.alias(p)} — balance and rate?", [H(f"{p}.loan"), H(f"{p}.rate")], "owner"))
    for h in holds:
        cs.append((f"how big is my {tb.alias(h)} holding — units and value?", [H(f"{h}.units"), H(f"{h}.value")], "owner"))
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        cs.append((f"give me the basics on {nm} — plan, program, who coaches them", [H(f"{m}.plan"), H(f"{m}.program"), H(f"{m}.coach")], "partner_gym"))
    for q, req, r in cs:
        tb.add("current_state", q, req, r)

    # ============================================================ stale probes (>=200)
    for key in keys_sorted:
        k = g.keys[key]
        if len(k["versions"]) < 2:
            continue
        qs = current_state_questions(tb, key)
        head = H(key)
        stale = k["versions"][:-1]
        stale_set = set(stale)
        traps = [i["id"] for i in g.items if i.get("fact_refs") and set(i["fact_refs"]) & stale_set]
        for q, r in qs[:2]:
            tb.add("stale_probe", q, [head], r, key=key, stale_ids=stale, trap_ids=traps)

    # ============================================================ temporal_change
    def versions(key):
        return g.keys[key]["versions"]

    def since_year(key):
        v_old = g.version_at(key, NOW_DAY - 365) or versions(key)[0]
        return [v_old, H(key)] if v_old != H(key) else None

    tc = []
    for p in props:
        tc.append((f"how has {tb.alias(p)}'s value moved over the time we've tracked it?", versions(f"{p}.valuation")))
        tc.append((f"how much have we paid down on {tb.alias(p)} since we started tracking?", [versions(f"{p}.loan")[0], H(f"{p}.loan")]))
        tc.append((f"what's happened to the rent at {tb.alias(p)} — before and after the last review?", versions(f"{p}.rent")))
        tc.append((f"walk me through the interest rate changes on {tb.alias(p)}", versions(f"{p}.rate")))
        if len(versions(f"{p}.pm")) > 1:
            tc.append((f"who used to manage {tb.alias(p)} and who's got it now?", versions(f"{p}.pm")))
    for h in holds:
        tc.append((f"how has my {tb.alias(h)} position changed over time — every trade?", versions(f"{h}.units")))
        tc.append((f"what's {tb.alias(h)} done since I first logged it?", [versions(f"{h}.value")[0], H(f"{h}.value")]))
    for key, q in (("offset.balance", "how does our cash buffer compare with this time last year?"),
                   ("portfolio.borrowing_capacity", "how has our borrowing power changed through the year and a half?"),
                   ("portfolio.strategy", "how has our investing approach shifted since we first wrote it down?"),
                   ("portfolio.lvr_rule", "did we change the gearing rule at some point? what was it before?"),
                   ("offset.savings_goal", "has the rainy-day target changed since we first set it?"),
                   ("gym.members", "how has membership grown quarter by quarter at IronBark?"),
                   ("gym.price", "what did a membership cost before the price rise versus now?"),
                   ("gym.head_coach", "who used to lead the coaching team and who does now?"),
                   ("gym.equipment_supplier", "who did we buy gym equipment from before the switch, and who now?"),
                   ("gym.staff_count", "how has the gym team grown since early last year?"),
                   ("gym.timetable", "how has the class schedule changed since we started?"),
                   ("gym.lease", "how much has the gym rent gone up?"),
                   ("cafe.bean_supplier", "when did we change roasters at Copperleaf, and from whom to whom?"),
                   ("cafe.milk_supplier", "which dairy did we drop and who replaced them?"),
                   ("cafe.hours", "how have the cafe's trading hours changed?"),
                   ("cafe.head_barista", "who was head barista before and who is now?"),
                   ("cafe.covers", "how have weekly customer numbers trended at the cafe across every quarter?"),
                   ("cafe.cash_reserve", "track the cafe's reserve over each quarter for me"),
                   ("con.pipeline", "how has Stonefield's order book trended over the last six quarters?"),
                   ("con.supervisor", "who ran Stonefield's sites before Kira took over?"),
                   ("con.concrete_supplier", "who supplied concrete before the change, and who now?"),
                   ("con.insurance", "how much has Stonefield's liability premium gone up?"),
                   ("con.strategy", "how has the tender policy changed over time?"),
                   ("train.squat_1rm", "chart my squat progress every quarter since we started"),
                   ("train.bench_1rm", "how has my bench improved over each testing block?"),
                   ("train.deadlift_1rm", "show my deadlift progression across the whole period"),
                   ("train.bodyweight", "how has my weight trended quarter to quarter?"),
                   ("train.program", "what programs have I run over the last year and a half, in order?"),
                   ("train.sessions", "how has my training frequency changed over time?"),
                   ("train.run10k", "show every 10k time I've logged — am I getting faster?"),
                   ("train.coach", "who coached me before Ben?"),
                   ("goal_squat.target", "how has my squat goal changed since I first set it?"),
                   ("goal_run.target", "did I move the running target? what was it originally?"),
                   ("goal.deadlift", "what was my original deadlift goal compared with now?"),
                   ("reading.current", "list what I've been reading over the past 18 months, in order"),
                   ("reading.goal", "has my reading target changed from last year?"),
                   ("mila.activity", "how has Mila's sport changed this year compared with before?"),
                   ("theo.activity", "what did Theo used to do and what's he doing now?"),
                   ("ruby.activity", "what's changed in Ruby's activities since last year?"),
                   ("mila.swim_pb", "show all of Mila's 100 free times — how much has she improved?"),
                   ("family.holiday_budget", "did we bump the holiday budget from last year?"),
                   ("household.budget", "how has the family spending allowance changed?"),
                   ("con.pipeline_target", "has the order book target moved since we first set it?"),
                   ("cafe.covers_target", "what was the customer target last year versus this year?"),
                   ("cafe.revenue_goal", "how does this year's cafe sales target compare with last year's?"),
                   ("gym.member_target", "what was the membership goal last year and what is it now?")):
        vs = versions(key)
        tc.append((q, vs if len(vs) <= 6 else vs[-6:]))
    for prid in projects:
        tc.append((f"give me the history of {tb.alias(prid)} — every stage and when", versions(f"{prid}.status")))
    for short, b in (("gym", "b_gym"), ("cafe", "b_cafe"), ("con", "b_con")):
        qs = ["2025Q3", "2025Q4", "2026Q1", "2026Q2"]
        tc.append((f"how has {tb.alias(b)} turnover trended over the last four quarters?", [H(f"{short}.revenue.{q}") for q in qs]))
        tc.append((f"compare {tb.alias(b)} sales this June quarter with the same quarter a year ago", [H(f"{short}.revenue.2025Q2"), H(f"{short}.revenue.2026Q2")]))
        tc.append((f"first half of 2025 versus first half of 2026 takings at {tb.alias(b)}?",
                   [H(f"{short}.revenue.{q}") for q in ("2025Q1", "2025Q2", "2026Q1", "2026Q2")]))
    temporal_tasks = [(q, req, "owner") for q, req in tc]
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        temporal_tasks.append((f"how has {nm}'s progress tracked since they started?", versions(f"{m}.progress"), "partner_gym"))
        temporal_tasks.append((f"what plan was {nm} on before, and what now?", versions(f"{m}.plan"), "partner_gym"))
        temporal_tasks.append((f"what programs has {nm} been through?", versions(f"{m}.program"), "partner_gym"))
        temporal_tasks.append(("show me how my numbers have changed since I joined", versions(f"{m}.progress"), f"member_{m}"))
    for q, req, r in temporal_tasks:
        if r == "owner" and g.by_id[req[0]]["partition"] == "household" and R.random() < 0.4:
            r = "household"
        tb.add("temporal_change", q, req, r, temporal=True)

    # ============================================================ goal_tracking
    gt = [
        (["am I on track for the squat target?", "squat's been stuck — will I make my goal in time?", "realistic chance of hitting the big squat number by September?",
          "how close am I to the squat I'm chasing?", "is the squat goal still achievable?", "check my squat goal progress"],
         [H("goal_squat.target"), H("train.squat_1rm"), H("train.program"), tg("coach_advice")[0], tg("knee_note")[0], H("train.sessions")], "health"),
        (["will I get under the running target in time?", "how's the 10k goal going?", "am I close to my run time goal?",
          "is the running goal on track given the knee?", "progress check on my 10k target", "how far off my running target am I?"],
         [H("goal_run.target"), H("train.run10k"), tg("run_plan")[0], tg("knee_note")[0]], "health"),
        (["how's the deadlift goal looking?", "am I going to hit my pulling target this year?", "deadlift target — on track?",
          "gap between my deadlift and the goal?", "deadlift goal check-in"],
         [H("goal.deadlift"), H("train.deadlift_1rm"), H("train.program")], "health"),
        (["bench goal — am I there yet?", "how far off the bench target am I?", "will I make the bench goal by June?", "bench progress versus target?"],
         [H("goal.bench"), H("train.bench_1rm")], "health"),
        (["am I getting closer to the weight I wanted?", "progress on my bodyweight goal?", "how much more weight to lose to hit my target?", "weight goal check"],
         [H("goal.bodyweight"), H("train.bodyweight")], "health"),
        (["is the rainy-day fund where we wanted it?", "have we rebuilt the buffer to target?", "how far off our emergency money goal are we?",
          "are we back above the buffer we agreed?", "cash buffer versus our goal?"],
         [H("offset.savings_goal"), H("offset.balance")], "finance"),
        (["am I on pace for my reading goal?", "will I hit the book target this year?", "reading challenge progress?", "how's my book count against the target?"],
         [H("reading.goal"), H("reading.finished")], "reading"),
        (["are we going to make the gym's membership goal?", "how far off the IronBark growth target are we?", "membership target progress?",
          "can we lift the coach hiring freeze yet — are we past the member number?", "is IronBark on track for this year's member number?", "gap to the gym's member goal?"],
         [H("gym.member_target"), H("gym.members"), tg("gym_hire_decision")[0]], "business/gym"),
        (["is the cafe hitting its customer goal?", "covers versus target at Copperleaf?", "are we getting the foot traffic we planned for at the cafe?",
          "has Sunday trading helped us hit the covers goal?", "customer numbers against plan at the cafe?"],
         [H("cafe.covers_target"), H("cafe.covers"), tg("cafe_sunday_decision")[0]], "business/cafe"),
        (["is the cafe on track for its sales target this year?", "how are we going against Copperleaf's turnover goal?", "will the cafe make its annual number?",
          "half-year check: cafe sales versus target", "cafe revenue pace versus the yearly goal?"],
         [H("cafe.revenue_goal"), H("cafe.revenue.2026Q1"), H("cafe.revenue.2026Q2")], "business/cafe"),
        (["is Stonefield carrying enough forward work?", "order book versus target at Stonefield?", "are we at the pipeline goal for the building business?",
          "can Stonefield grow toward its pipeline target with current crew?", "pipeline target check for Stonefield"],
         [H("con.pipeline_target"), H("con.pipeline"), tg("con_capacity")[0]], "business/construction"),
        (["is Mila going to qualify for regionals?", "how close is Mila to the qualifying time?", "will Mila make regionals at this rate?",
          "Mila's swim goal — on track?", "what does Mila still need to drop to qualify?"],
         [H("mila.swim_goal"), H("mila.swim_pb"), tg("mila_coach_note")[0]], "family"),
    ]
    for qs, req, prim in gt:
        req = [r for r in req if r]
        partner = {"business/gym": "partner_gym", "business/cafe": "partner_cafe", "business/construction": "partner_construction"}.get(prim)
        for i, q in enumerate(qs):
            r = partner if (partner and i % 2 == 1) else ("household" if prim == "family" and i % 2 else "owner")
            if r == "household":
                req2 = [x for x in req if g.by_id[x]["partition"] in tb.ident["household"]["partitions"]]
            else:
                req2 = req
            tb.add("goal_tracking", q, req2, r, primary=prim)
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        base = [H(f"{m}.goal"), H(f"{m}.progress")]
        chk = tg(f"member_checkin:{m}")[0]
        for q in (f"is {nm} on track for their goal?", f"how is {nm} going against what they set out to do?", f"{nm}'s goal — are we getting them there?"):
            tb.add("goal_tracking", q, base + [chk, H(f"{m}.program")], "partner_gym", primary="business/gym")
        for q in ("am I on track for my goal?", "how close am I to what I set out to achieve?"):
            tb.add("goal_tracking", q, base + [chk], f"member_{m}", primary="business/gym")

    # ============================================================ decision_support
    ds = []
    for p in props:
        a = tb.alias(p, plain=True)
        need = [H(f"{p}.valuation"), H(f"{p}.loan"), H("portfolio.borrowing_capacity"), H("portfolio.strategy"),
                H("portfolio.lvr_rule"), H("offset.balance"), tg("inv_decision")[0]]
        for q in (f"equity's up on {a}, thinking about the next purchase — what do I need to weigh up?",
                  f"could we use the growth in {a} to fund another property?",
                  f"is now the time to pull equity out of {a} for the next deal?",
                  f"{a} has gone up a fair bit — should we go again?"):
            ds.append((q, need, "owner", "finance"))
        need = [H(f"{p}.loan"), H(f"{p}.rate"), tg(f"refi_email:{p}")[0], H(f"{p}.valuation"), H("portfolio.lvr_rule")]
        for q in (f"should I take the broker up on refinancing {a}?", f"is it worth switching lenders on {a}?", f"Nadia reckons we should refix {a} — does it stack up?"):
            ds.append((q, need, "owner", "finance"))
        need = [H(f"{p}.rent"), H(f"{p}.lease_end"), tg(f"pm_email:{p}")[0], H(f"{p}.pm")] + tg(f"reno_quote:{p}")[:1]
        for q in (f"lease is coming up at {a} — push the rent or keep the tenant happy?", f"what should we do about the rent at {a} at renewal?",
                  f"PM's asking how we want to handle {a} next — thoughts?"):
            ds.append((q, need, "owner", "finance"))
    for h in holds:
        a = tb.alias(h, plain=True)
        need = [H(f"{h}.units"), H(f"{h}.value"), tg(f"thesis:{h}")[0], H("portfolio.strategy")]
        for q in (f"should I trim {a}?", f"thinking of selling some {a} — sensible?", f"{a} has had a run, take profits or hold?", f"add to {a} or leave it?"):
            ds.append((q, need, "owner", "finance"))
    need = [tg("reno_quote:prop_halyard")[0], tg("related_party_policy")[0], H("proj_halyard.status"), tg("con_capacity")[0], H("prop_halyard.valuation"), H("offset.balance")]
    for q in ("should we go ahead with Stonefield doing the Halyard Way reno?", "is the townhouse reno a good idea right now?",
              "green-light the Tindal Point renovation or wait?", "can we justify the kitchen and bathroom job at Halyard?"):
        ds.append((q, need, "owner", "finance"))
    gym_hire = [H("gym.members"), H("gym.member_target"), tg("gym_hire_decision")[0], H("gym.staff_count"), tg("gym_capacity")[0], H("gym.head_coach")]
    gym_rack = [tg("gym_equipment_issue")[0], H("gym.equipment_supplier")] + tg("gym_rack_quote") + [H("gym.revenue.2026Q2"), tg("gym_fitout")[0]]
    gym_price = [H("gym.price"), tg("gym_price_decision")[0], H("gym.members"), H("gym.revenue.2026Q2"), H("gym.lease")]
    for i, q in enumerate(("6am classes are packed — do we hire another coach?", "should IronBark bring on more coaching staff?",
                           "we keep turning people away at peak — time to hire?", "is it time to add a coach at the gym?",
                           "coaches are stretched, can we afford another hire?", "do we need more coaches at IronBark?")):
        ds.append((q, gym_hire, "partner_gym" if i % 2 else "owner", "business/gym"))
    for i, q in enumerate(("some of the racks are stuffed — replace them now or patch them?", "should we buy new squat racks for the gym?",
                           "what do we do about the broken racks?", "is it worth upgrading the gym's racks this year?",
                           "rack replacement — go or wait?", "the racks need sorting, what's the call?")):
        ds.append((q, gym_rack, "partner_gym" if i % 2 else "owner", "business/gym"))
    for i, q in enumerate(("should we put membership prices up again?", "can IronBark handle another price rise?",
                           "is it time to lift our weekly rate at the gym?", "another price increase at the gym — yes or no?")):
        ds.append((q, gym_price, "partner_gym" if i % 2 else "owner", "business/gym"))
    con_tender = [tg("con_capacity")[0], tg("con_tender_decision")[0], H("con.strategy"), H("con.pipeline"), H("con.active_projects"), H("con.supervisor"), H("con.insurance")]
    for i, q in enumerate(("we've been asked to quote a big job — should Stonefield go for it?", "new tender came in, do we bid?",
                           "can we take on another build right now?", "should the building business chase this commercial fit-out?",
                           "is it smart to price another job this quarter?", "worth tendering for the new project?")):
        ds.append((q, con_tender, "partner_construction" if i % 2 else "owner", "business/construction"))
    cafe_draw = [H("cafe.cash_reserve"), H("cafe.distribution_rule"), H("cafe.revenue.2026Q2"), H("cafe.revenue_goal")]
    for i, q in enumerate(("can Tomas and I take a distribution from the cafe?", "is there room to pay ourselves out of Copperleaf?",
                           "should we pull some profit out of the cafe this quarter?", "could the cafe afford a partner drawing?")):
        ds.append((q, cafe_draw, "partner_cafe" if i % 2 else "owner", "business/cafe"))
    cafe_hire = [H("cafe.head_barista"), tg("cafe_roster")[0], tg("cafe_recruit_quote")[0], H("cafe.covers"), H("cafe.revenue.2026Q2")]
    for i, q in enumerate(("do we need to recruit a senior barista?", "should we pay a recruiter for a coffee lead?",
                           "is it time to hire another experienced barista at Copperleaf?", "the roster's thin — hire or manage?")):
        ds.append((q, cafe_hire, "partner_cafe" if i % 2 else "owner", "business/cafe"))
    meet = [H("train.squat_1rm"), H("train.bench_1rm"), H("train.deadlift_1rm"), H("goal_squat.target"), H("train.program"), tg("knee_note")[0], tg("coach_advice")[0]]
    for q in ("should I enter a powerlifting meet in September?", "am I ready to compete this year?", "thinking of doing my first meet — good idea?",
              "should I sign up for the strength comp?", "worth competing or keep training?", "is a meet realistic for me before spring?"):
        ds.append((q, meet, "owner", "health"))
    for q, req, r, prim in ds:
        tb.add("decision_support", q, req, r, primary=prim)

    # ============================================================ option_analysis
    oa = []
    beans = [H("cafe.bean_supplier"), tg("bean_contract")[0]] + tg("bean_quote")
    for i, q in enumerate(("supplier's bottlenecking the cafe, what are our options?", "coffee deliveries keep failing — what can we do?",
                           "who else could roast for us, and can we get out of the current deal?", "options if we ditch our roaster?",
                           "the bean situation is killing us — alternatives?", "what are the alternatives to our current coffee supplier?",
                           "lay out our choices on the coffee supply problem", "plan B for beans?")):
        oa.append((q, beans, "partner_cafe" if i % 2 else "owner", "business/cafe"))
    racks = [tg("gym_equipment_issue")[0], H("gym.equipment_supplier")] + tg("gym_rack_quote")
    for i, q in enumerate(("what are our options for replacing the damaged racks?", "who could supply new racks and at what price?",
                           "compare the rack quotes we've got", "options for the broken equipment at IronBark?", "rack suppliers — what's on the table?")):
        oa.append((q, racks, "partner_gym" if i % 2 else "owner", "business/gym"))
    holiday = [H("family.school_break"), H("family.holiday_budget")] + tg("holiday_pref") + [tg("kid_pref:p_mila")[0], tg("kid_pref:p_theo")[0], tg("kid_pref:p_ruby")[0]]
    for i, q in enumerate(("what are our options for a trip in the spring holidays?", "where could we go in the September break?",
                           "give me a few holiday ideas for the school break that suit everyone", "holiday options for the family this spring?",
                           "shortlist of trips for September?", "what kind of getaway works for us in the next school holidays?")):
        oa.append((q, holiday, "household" if i % 2 else "owner", "family"))
    for p in props:
        need = [tg(f"pm_email:{p}")[0], H(f"{p}.rent"), H(f"{p}.valuation")] + tg(f"reno_quote:{p}")[:1]
        for q in (f"what can we do to get more out of {tb.alias(p, plain=True)}?", f"options for improving the return on {tb.alias(p)}?",
                  f"refresh, hold or cut the rent at {tb.alias(p)} — lay out the options"):
            oa.append((q, need, "owner", "finance"))
    sq = [H("goal_squat.target"), H("train.squat_1rm"), tg("coach_advice")[0], tg("knee_note")[0], H("train.program"), tg("training_clash")[0]]
    for q in ("squat's stalled — what are my options?", "how could I break through the squat plateau?", "ways to get the squat moving again?",
              "what can I change to start progressing my squat?", "options for fixing my stalled lower body strength?"):
        oa.append((q, sq, "owner", "health"))
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        need = [H(f"{m}.program"), H(f"{m}.progress"), H(f"{m}.goal"), tg(f"member_pref:{m}")[0]]
        for q in (f"{nm} has plateaued — what could we try?", f"options for changing up {nm}'s training?", f"what are the next-step options for {nm}?"):
            oa.append((q, need, "partner_gym", "business/gym"))
        oa.append(("I've plateaued — what could I change?", need, f"member_{m}", "business/gym"))
    barista = [H("cafe.head_barista"), tg("cafe_roster")[0], tg("cafe_recruit_quote")[0]]
    for i, q in enumerate(("options for covering the senior coffee role?", "promote from within or recruit for barista lead?",
                           "who could step up on the coffee machine, or do we hire?", "barista lead — what are the options?")):
        oa.append((q, barista, "partner_cafe" if i % 2 else "owner", "business/cafe"))
    for q, req, r in (("is Talbot still the right linen supplier for us?", [tg("talbot_gym_feedback")[0], tg("talbot_cafe_feedback")[0], H("gym.towel_supplier"), H("cafe.linen_supplier")], "owner"),
                      ("should we keep Talbot for towels?", [tg("talbot_gym_feedback")[0], H("gym.towel_supplier")], "partner_gym"),
                      ("should we keep Talbot for the tea towels?", [tg("talbot_cafe_feedback")[0], H("cafe.linen_supplier")], "partner_cafe"),
                      ("options for linen — stick with Talbot or shop around?", [tg("talbot_gym_feedback")[0], tg("talbot_cafe_feedback")[0], H("gym.towel_supplier"), H("cafe.linen_supplier")], "owner"),
                      ("Brightwater or another plumber — what are the options?", [tg("brightwater_cafe_feedback")[0], tg("brightwater_con_feedback")[0], H("con.plumbing_sub")], "owner"),
                      ("should we keep using Brightwater for the cafe?", [tg("brightwater_cafe_feedback")[0]], "partner_cafe"),
                      ("keep Brightwater as our plumbing sub or switch?", [tg("brightwater_con_feedback")[0], H("con.plumbing_sub")], "partner_construction"),
                      ("where should we take Priya for her birthday?", [tg("priya_food_pref")[0], tg("restaurant_pref")[0], tg("allergy")[0]], "owner"),
                      ("restaurant options for a family birthday dinner?", [tg("priya_food_pref")[0], tg("restaurant_pref")[0], tg("allergy")[0]], "household")):
        prim = None
        for _ in range(3):
            oa.append((q, req, r, prim))
    seen = set()
    for q, req, r, prim in oa:
        key = (q, r)
        if key in seen:
            q = q + (" " + R.choice(["Thoughts?", "What do you reckon?", "Lay it out.", "Pros and cons?"]))
        seen.add((q, r))
        tb.add("option_analysis", q, req, r, primary=prim)

    # ============================================================ preference_recommendation
    pr = []
    cur_prefs = [i for i in tg("reading_pref_current") if "book_loved" not in g.by_id[i]["tags"]]
    for q in ("what should I read next?", "recommend me a book for the holidays", "need something new to read — ideas?",
              "pick my next book", "what book should I grab at the airport?", "suggest a few books I'd actually finish",
              "I've run out of books, what next?", "give me reading suggestions"):
        pr.append((q, cur_prefs, "owner", "reading"))
    for bid in tg("book_loved"):
        b = g.by_id[bid]
        bk = g.entities[b["entities"][1]]
        gl = [i for i in tg(f"genre_like:{bk['genre']}") if "reading_pref_current" in g.by_id[i]["tags"]]
        for q in (f"I want something like {bk['name']}", f"more in the vein of {bk['author']}?", f"what else would I enjoy if I liked {bk['name']}?"):
            pr.append((q, [bid] + gl, "owner", "reading"))
    kids_wknd = [tg("kid_pref:p_mila")[0], tg("kid_pref:p_theo")[0], tg("kid_pref:p_ruby")[0]] + tg("family_place_pref")[:3]
    for i, q in enumerate(("what should we do with the kids this weekend?", "ideas for a Saturday outing everyone will like?",
                           "family day out suggestions?", "where can we take the kids on Sunday?", "something fun for all three this weekend?",
                           "weekend plans for the kids — ideas?")):
        pr.append((q, kids_wknd, "household" if i % 2 else "owner", "family"))
    rest = [tg("priya_food_pref")[0], tg("restaurant_pref")[0], tg("allergy")[0]]
    for i, q in enumerate(("where should we go for date night?", "pick a restaurant for Saturday", "dinner out — where would we enjoy?",
                           "anniversary dinner spot?", "somewhere nice to eat with the family?")):
        pr.append((q, rest, "household" if i % 2 else "owner", "family"))
    for kid, act, extra in (("p_theo", "theo.activity", []), ("p_mila", "mila.activity", []), ("p_ruby", "ruby.activity", tg("allergy"))):
        nm = g.entities[kid]["name"]
        need = [tg(f"kid_pref:{kid}")[0], H(act)] + extra
        for i, q in enumerate((f"birthday present ideas for {nm}?", f"what would {nm} love as a gift?", f"school holiday activity for {nm}?",
                               f"what should we sign {nm} up for next term?", f"treat for {nm} this weekend?")):
            pr.append((q, need, "household" if i % 2 else "owner", "family"))
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        need = [tg(f"member_pref:{m}")[0], H("gym.timetable"), H(f"{m}.program")]
        for q in (f"which classes would suit {nm}?", f"what sessions should we recommend to {nm}?"):
            pr.append((q, need, "partner_gym", "business/gym"))
        for q in ("which classes would suit me?", "what should I book this week?"):
            pr.append((q, need, f"member_{m}", "business/gym"))
    for i, q in enumerate(("recommend a podcast-style audiobook for my commute", "what non-fiction would I like?")):
        pr.append((q, cur_prefs, "owner", "reading"))
    for q, req, r, prim in pr:
        tb.add("preference_recommendation", q, req, r, primary=prim)

    # ============================================================ cross_domain
    cd = []
    def addcd(qs, req, prim, reqs=("owner",)):
        for i, q in enumerate(qs):
            cd.append((q, req, reqs[i % len(reqs)], prim))
    addcd(("I keep missing morning sessions — how do I fit training around everything?", "my training's falling apart with the early starts, what can I change?",
           "when can I realistically train each week now?", "training keeps getting bumped, help me rethink the week",
           "how do I keep the program going with the new cafe hours?", "find me a training slot that doesn't clash"),
          [tg("training_clash")[0], H("cafe.hours"), H("train.sessions"), H("gym.timetable"), H("train.program")], "health")
    addcd(("we've got some spare cash — gym fit-out, next property, or keep the buffer?", "where should spare money go this quarter?",
           "can we afford the recovery room contribution and still buy again?", "money priorities for the next six months?",
           "do I tip money into the gym or save for a deposit?", "balance the gym commitment against the property plans"),
          [H("offset.balance"), H("offset.savings_goal"), tg("gym_fitout")[0], tg("inv_decision")[0], H("portfolio.borrowing_capacity")], "finance")
    addcd(("the townhouse reno — what does it mean for the tenant, the building crew and our cash?", "if Stonefield does Halyard, what's the knock-on for everything else?",
           "think through the Halyard job end to end", "Halyard renovation: tenancy, crew capacity and the conflict-of-interest side?",
           "what do I need to juggle if we renovate Halyard Way?"),
          [H("prop_halyard.rent"), H("prop_halyard.lease_end"), tg("reno_quote:prop_halyard")[0], H("proj_halyard.status"), tg("related_party_policy")[0], tg("con_capacity")[0]], "finance")
    addcd(("can we get away as a family in the September holidays given work?", "is a September trip realistic with everything going on?",
           "September — what's on across work and family before I book a holiday?", "plan around the spring break: who's free and what's committed?",
           "any clashes if we travel in the school break?"),
          [H("family.school_break"), H("family.holiday_budget"), tg("con_capacity")[0], tg("gym_fitout")[0], H("mila.swim_goal")], "family")
    addcd(("Jordan's splitting time between the gym and cafe — is that working?", "how stretched is Jordan across both businesses?",
           "should Jordan go full-time at one of the businesses?", "Jordan staffing across IronBark and Copperleaf — any issues?"),
          [tg("jordan_gym")[0], tg("cafe_roster")[0], H("cafe.head_barista"), H("gym.staff_count")], "business/cafe")
    addcd(("Priya's talking about pausing the gym — what's the full picture?", "should Priya freeze her IronBark membership?",
           "what does Priya's gym usage look like and what would pausing save us?", "Priya and the gym membership — keep or pause?"),
          [tg("priya_gym_pause")[0], tg("priya_member_note")[0], H("m03.plan"), H("household.budget")], "family", reqs=("owner", "household"))
    addcd(("is Ben doing too much — coaching me and running the coaching team?", "Ben's workload across my program and the gym — sustainable?",
           "can Ben keep coaching me now he's head coach?", "should someone else take over my programming from Ben?"),
          [H("train.coach"), H("gym.head_coach"), tg("coach_advice")[0], tg("gym_hire_decision")[0]], "health")
    addcd(("how's Brightwater performing across the businesses?", "Brightwater — good or bad across all our jobs?", "do we have a Brightwater problem anywhere?"),
          [tg("brightwater_cafe_feedback")[0], tg("brightwater_con_feedback")[0], H("con.plumbing_sub")], "business/construction")
    addcd(("how is Talbot going for both businesses?", "Talbot linen across the gym and cafe — any issues?", "one linen supplier for both — still a good idea?"),
          [tg("talbot_gym_feedback")[0], tg("talbot_cafe_feedback")[0], H("gym.towel_supplier"), H("cafe.linen_supplier")], "business/gym")
    addcd(("could I pull money out of the cafe toward the next deposit?", "use cafe profits for the next property — possible?",
           "fund part of the next purchase from Copperleaf?", "is cafe cash an option for the property deposit?", "draw from the cafe for investing — allowed and sensible?"),
          [H("cafe.cash_reserve"), H("cafe.distribution_rule"), H("offset.balance"), tg("inv_decision")[0], H("portfolio.borrowing_capacity")], "finance")
    addcd(("how do I fit training around the kids' sport?", "find time to train given everyone's after-school stuff",
           "kids' activities versus my training — where's the gap in the week?", "work out a week where I train and still do the kids' runs",
           "family schedule and gym time — how do they fit?"),
          [H("mila.activity"), H("theo.activity"), H("ruby.activity"), H("train.sessions"), tg("training_clash")[0]], "family")
    for p in props:
        need = [tg(f"pm_email:{p}")[0], tg("related_party_policy")[0], tg("con_capacity")[0], H("offset.balance")] + tg(f"reno_quote:{p}")[:1]
        for q in (f"PM wants a freshen-up at {tb.alias(p, plain=True)} — could Stonefield do it, and can we afford it?",
                  f"should our building crew handle the work at {tb.alias(p)}?",
                  f"use Stonefield for {tb.alias(p)}? think through crew, cash and the arm's-length thing"):
            cd.append((q, need, "owner", "finance"))
    addcd(("the cafe's earlier opening — how's it affecting staff, sales and me?", "has the 6:30 open been worth it across the board?",
           "earlier cafe hours: covers, roster and my own week?", "review the cafe hours change against everything it touched"),
          [H("cafe.hours"), H("cafe.covers"), tg("cafe_roster")[0], tg("training_clash")[0]], "business/cafe")
    addcd(("does buying gym racks clash with the recovery room spend and my own cash?", "gym capex this year: racks, fit-out and what I'm putting in?",
           "can the gym fund both the racks and the recovery room?"),
          [tg("gym_fitout")[0], tg("gym_equipment_issue")[0], H("offset.balance")] + tg("gym_rack_quote"), "business/gym")
    for q, req, r, prim in cd:
        tb.add("cross_domain", q, req, r, primary=prim)

    # ============================================================ multimodal
    mm = []
    for prid in projects:
        pair = tg(f"mm_defect:{prid}:0") + tg(f"mm_defect:{prid}:1")
        nm = tb.alias(prid, plain=True)
        for i, q in enumerate((f"pull up the defect photos from {nm}", f"show me the pics of problems on {nm}", f"photos of what's wrong at {nm}?")):
            mm.append((q, pair, "partner_construction" if i % 2 else "owner"))
        for j in (0, 1):
            it = g.by_id[tg(f"mm_defect:{prid}:{j}")[0]]
            mm.append((f"the photo of the {it['media']['caption'].split(': ')[-1]} at {nm}", [it["id"]], "owner"))
    for lift in ("squat", "bench", "deadlift"):
        pair = tg(f"mm_form:{lift}:0") + tg(f"mm_form:{lift}:1")
        for q in (f"Ben's videos of my {lift}", f"find the clips where my {lift} technique got checked", f"{lift} form videos?"):
            mm.append((q, pair, "owner"))
    for i, topic in enumerate(["membership pricing tiers", "summer timetable", "recovery room layout"]):
        for j, q in enumerate((f"the whiteboard pic from the partners meeting about the {topic}", f"photo of what we drew up for the {topic}", f"find the {topic} whiteboard")):
            mm.append((q, tg(f"mm_whiteboard:{i}"), "partner_gym" if j % 2 else "owner"))
    for p in props:
        for q in (f"valuation report for {tb.alias(p, plain=True)}", f"the valuer's PDF on {tb.alias(p)}"):
            mm.append((q, tg(f"mm_valreport:{p}"), "owner"))
        pair = tg(f"mm_listing:{p}:0") + tg(f"mm_listing:{p}:1")
        for q in (f"listing photos of {tb.alias(p, plain=True)}", f"pics the PM took of {tb.alias(p)}"):
            mm.append((q, pair, "owner"))
        it = g.by_id[tg(f"mm_listing:{p}:0")[0]]
        mm.append((f"photo of the {it['media']['caption']} at {tb.alias(p)}", [it["id"]], "owner"))
    for kid, ev in (("p_ruby", "piano recital"), ("p_mila", "regional swim meet"), ("p_theo", "basketball grand final")):
        nm = g.entities[kid]["name"]
        for i, q in enumerate((f"photos from {nm}'s {ev}", f"pics of {nm} at the {ev}", f"{nm} {ev} photos for grandma")):
            mm.append((q, tg(f"mm_family:{kid}"), "household" if i % 2 else "owner"))
    for b, what, partner in (("b_cafe", "grinder repair", "partner_cafe"), ("b_gym", "cable machine service", "partner_gym"), ("b_con", "laser level hire", "partner_construction")):
        nm = g.entities[b]["aliases"][1]
        pair = tg(f"mm_receipt:{b}:0") + tg(f"mm_receipt:{b}:1")
        for i, q in enumerate((f"receipts for {nm} this year", f"find the {nm} receipt for the {what}", f"scanned receipts from {nm}")):
            req = pair if i != 1 else tg(f"mm_receipt:{b}:0")
            mm.append((q, req, partner if i % 2 else "owner"))
    for i, board in enumerate(["breakfast menu", "lunch specials", "drinks and pricing"]):
        for j, q in enumerate((f"photo of the cafe's {board} board", f"what did the {board} chalkboard say?", f"find the {board} pic Tomas posted")):
            mm.append((q, tg(f"mm_menu:{i}"), "partner_cafe" if j % 2 else "owner"))
    for q, req, r in mm:
        tb.add("multimodal", q, req, r)

    # ============================================================ extra need-sets (to reach >=150 per class)
    X = []  # (cls, q, req, requester, primary)
    # --- cross_domain
    for h in holds:
        need = [H(f"{h}.value"), tg(f"thesis:{h}")[0], tg("inv_decision")[0], tg("gym_fitout")[0], H("gym.revenue.2026Q2")]
        for q in (f"could I sell down {tb.alias(h, plain=True)} to cover my gym fit-out share instead of delaying the next deposit?", f"fund the recovery room from {tb.alias(h)} rather than the gym's own money?",
                  f"cash out {tb.alias(h)} for the gym commitment — sensible given the property plan?", f"{tb.alias(h)}, the next house, or my share of the gym upgrade — where should the money go?"):
            X.append(("cross_domain", q, need, "owner", "finance"))
    for p in props:
        need = [H(f"{p}.valuation"), H(f"{p}.loan"), H("portfolio.lvr_rule"), tg("gym_fitout")[0], tg(f"refi_email:{p}")[0]]
        for q in (f"could I release equity from {tb.alias(p, plain=True)} to cover my share of the gym fit-out?",
                  f"refinance {tb.alias(p)} to pay for the recovery room — dumb idea?"):
            X.append(("cross_domain", q, need, "owner", "finance"))
    for kid, act in (("p_mila", "mila.activity"), ("p_theo", "theo.activity"), ("p_ruby", "ruby.activity")):
        nm = g.entities[kid]["name"]
        need = [H(act), tg(f"kid_pref:{kid}")[0], tg("training_clash")[0], H("train.sessions")]
        for q in (f"can I do {nm}'s sport runs and still train enough?", f"juggle {nm}'s schedule with my sessions — how?", f"who covers {nm}'s activities if I move training to evenings?"):
            X.append(("cross_domain", q, need, "owner", "family"))
    for q in ("is the gym making enough to justify my fit-out contribution?", "gym earnings versus what I'm putting into the recovery room?", "should the gym fund the fit-out itself rather than me topping it up?"):
        X.append(("cross_domain", q, [H("gym.revenue.2026Q2"), tg("gym_fitout")[0], H("offset.balance")], "owner", "business/gym"))
    for q in ("Stonefield's numbers this quarter — do they change my investing plans?", "if the building business slows, can we still buy again?", "how exposed is the next purchase to Stonefield's pipeline?"):
        X.append(("cross_domain", q, [H("con.revenue.2026Q2"), H("con.pipeline"), tg("inv_decision")[0], H("portfolio.borrowing_capacity")], "owner", "finance"))
    for q in ("can the household budget lean on cafe profits?", "is cafe income enough to cover the bump in family spending?", "cafe takings versus what the house needs each month?"):
        X.append(("cross_domain", q, [H("cafe.revenue.2026Q2"), H("cafe.cash_reserve"), H("household.budget"), H("cafe.distribution_rule")], "owner", "business/cafe"))
    for q in ("books to pack for the September holiday?", "holiday reading list for the spring break trip", "what should I read on the September getaway?"):
        X.append(("cross_domain", q, cur_prefs + [H("family.school_break")], "owner", "reading"))
    for prid in [p for p in projects if p != "proj_halyard"]:
        need = [tg("con_capacity")[0], H("proj_halyard.status"), H(f"{prid}.status"), H("con.supervisor"), tg("related_party_policy")[0]]
        for q in (f"does our own Halyard reno push back {tb.alias(prid, plain=True)}?", f"family job versus paying client at {tb.alias(prid)} — who gets Kira first?",
                  f"is the Halyard work going to hurt {tb.alias(prid)}?"):
            X.append(("cross_domain", q, need, "owner", "business/construction"))
    for q in ("should I train at the 6am class or will I take a paying member's spot?", "is it fair for me to train at peak at IronBark?",
              "when can I train at the gym without crowding the classes?", "my training slot versus member capacity at the gym?"):
        X.append(("cross_domain", q, [tg("gym_capacity")[0], H("gym.timetable"), tg("training_clash")[0], H("train.sessions")], "owner", "health"))
    for q in ("will the September trip mess up Mila's qualifying prep and my own training block?", "holiday timing versus Mila's swim goal and my program?", "can Mila and I both keep training if we travel in the break?"):
        X.append(("cross_domain", q, [H("mila.swim_goal"), H("family.school_break"), tg("mila_coach_note")[0], H("train.program")], "owner", "family"))
    for q in ("can we do both the recovery room and the September holiday?", "fit-out contribution and the family trip — can we afford both?",
              "holiday versus gym spend: which gives?", "money for the trip after the gym commitment?"):
        X.append(("cross_domain", q, [tg("gym_fitout")[0], H("family.holiday_budget"), H("offset.balance"), H("family.school_break")], "owner", "finance"))

    # --- decision_support
    for h in holds:
        X.append(("decision_support", f"rebalance: is {tb.alias(h)} too big or too small for me now?",
                  [H(f"{h}.units"), H(f"{h}.value"), tg(f"thesis:{h}")[0], H("portfolio.strategy")], "owner", "finance"))
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        X.append(("decision_support", f"should we move {nm} onto a different membership?",
                  [H(f"{m}.plan"), H(f"{m}.progress"), H(f"{m}.goal"), tg(f"member_pref:{m}")[0], H("gym.price")], "partner_gym", "business/gym"))
    beans_need = [tg("bean_contract")[0], H("cafe.bean_supplier")] + tg("bean_incident")
    for i, q in enumerate(("do we terminate the coffee contract?", "is it time to give our roaster notice?", "should we walk away from the bean supplier now?", "cut ties with the roaster — yes or no?")):
        X.append(("decision_support", q, beans_need, "partner_cafe" if i % 2 else "owner", "business/cafe"))
    for i, q in enumerate(("keep trading Sundays at the cafe?", "is the Sunday trial worth continuing?", "should Copperleaf stay open Sundays?", "Sunday hours — keep or drop?")):
        X.append(("decision_support", q, [tg("cafe_sunday_decision")[0], H("cafe.covers"), H("cafe.hours"), H("cafe.revenue.2026Q2")], "partner_cafe" if i % 2 else "owner", "business/cafe"))
    for i, q in enumerate(("should we renew the gym lease on the current terms?", "can the gym carry the new rent?", "is the IronBark premises still affordable?")):
        X.append(("decision_support", q, [H("gym.lease"), H("gym.revenue.2026Q2"), H("gym.members")], "partner_gym" if i % 2 else "owner", "business/gym"))

    # --- option_analysis
    for prid in projects:
        for q in (f"options to get {tb.alias(prid, plain=True)} moving faster?", f"what levers do we have on {tb.alias(prid)}'s timeline?"):
            X.append(("option_analysis", q, [H(f"{prid}.status"), tg("con_capacity")[0], H("con.supervisor")], "partner_construction", "business/construction"))
    for q in ("running's plateaued, what are my options?", "how could I get faster over 10k?", "options to get the run time down without wrecking my knee?", "ways to improve my running?"):
        X.append(("option_analysis", q, [H("goal_run.target"), H("train.run10k"), tg("run_plan")[0], tg("knee_note")[0]], "owner", "health"))
    for i, q in enumerate(("what could we do with the cafe's reserve?", "options for the money sitting in Copperleaf?", "reinvest, distribute or hold the cafe cash?")):
        X.append(("option_analysis", q, [H("cafe.cash_reserve"), H("cafe.distribution_rule"), H("cafe.revenue_goal")], "partner_cafe" if i % 2 else "owner", "business/cafe"))
    for i, q in enumerate(("what are the options for growing membership at the gym?", "how could IronBark get more members?", "levers for gym growth?", "ways to lift sign-ups at the gym?")):
        X.append(("option_analysis", q, [H("gym.members"), H("gym.member_target"), H("gym.price"), tg("gym_capacity")[0], H("gym.timetable")], "partner_gym" if i % 2 else "owner", "business/gym"))
    for h in holds:
        X.append(("option_analysis", f"what are my options with {tb.alias(h)}?", [H(f"{h}.units"), H(f"{h}.value"), tg(f"thesis:{h}")[0]], "owner", "finance"))
    for i, q in enumerate(("options for adding supervision capacity at Stonefield?", "how could we free up Kira?", "second supervisor, subcontract, or slow down?")):
        X.append(("option_analysis", q, [tg("con_capacity")[0], H("con.supervisor"), H("con.active_projects")], "partner_construction" if i % 2 else "owner", "business/construction"))
    for q in ("how do we rebuild the buffer faster?", "options to top up the offset?", "what could we do to get cash back to target?"):
        X.append(("option_analysis", q, [H("offset.balance"), H("offset.savings_goal"), tg("inv_decision")[0], tg("gym_fitout")[0]], "owner", "finance"))

    # --- goal_tracking
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        X.append(("goal_tracking", f"progress report on {nm}'s goal please",
                  [H(f"{m}.goal"), H(f"{m}.progress"), tg(f"member_checkin:{m}")[0], H(f"{m}.program")], "partner_gym", "business/gym"))
    extra_goal_q = [
        ("squat target — honest assessment?", [H("goal_squat.target"), H("train.squat_1rm"), H("train.program"), tg("coach_advice")[0], tg("knee_note")[0], H("train.sessions")], "health"),
        ("10k goal — honest assessment?", [H("goal_run.target"), H("train.run10k"), tg("run_plan")[0], tg("knee_note")[0]], "health"),
        ("deadlift goal, how far to go?", [H("goal.deadlift"), H("train.deadlift_1rm"), H("train.program")], "health"),
        ("bench goal, how far to go?", [H("goal.bench"), H("train.bench_1rm")], "health"),
        ("bodyweight goal, how far to go?", [H("goal.bodyweight"), H("train.bodyweight")], "health"),
        ("buffer goal — where are we?", [H("offset.savings_goal"), H("offset.balance")], "finance"),
        ("books goal — where am I?", [H("reading.goal"), H("reading.finished")], "reading"),
        ("member goal at the gym — where are we?", [H("gym.member_target"), H("gym.members"), tg("gym_hire_decision")[0]], "business/gym"),
        ("cafe customer goal — where are we?", [H("cafe.covers_target"), H("cafe.covers"), tg("cafe_sunday_decision")[0]], "business/cafe"),
        ("cafe sales goal — where are we?", [H("cafe.revenue_goal"), H("cafe.revenue.2026Q1"), H("cafe.revenue.2026Q2")], "business/cafe"),
        ("Stonefield pipeline goal — where are we?", [H("con.pipeline_target"), H("con.pipeline"), tg("con_capacity")[0]], "business/construction"),
        ("Mila's regional goal — where is she?", [H("mila.swim_goal"), H("mila.swim_pb"), tg("mila_coach_note")[0]], "family"),
    ]
    for q, req, prim in extra_goal_q:
        X.append(("goal_tracking", q, req, "owner", prim))
    all_train = [H("goal_squat.target"), H("train.squat_1rm"), H("goal.deadlift"), H("train.deadlift_1rm"), H("goal.bench"), H("train.bench_1rm"),
                 H("goal_run.target"), H("train.run10k"), H("goal.bodyweight"), H("train.bodyweight")]
    for q in ("how am I going on all my training goals?", "full scorecard on my fitness targets", "where am I against every strength and running goal?", "training goals review — all of them"):
        X.append(("goal_tracking", q, all_train, "owner", "health"))
    biz_goals = [H("gym.member_target"), H("gym.members"), H("cafe.covers_target"), H("cafe.covers"), H("cafe.revenue_goal"),
                 H("cafe.revenue.2026Q1"), H("cafe.revenue.2026Q2"), H("con.pipeline_target"), H("con.pipeline")]
    for q in ("scorecard: how are all three businesses tracking against their goals?", "business targets review across the gym, cafe and Stonefield", "are the businesses hitting their numbers this year?"):
        X.append(("goal_tracking", q, biz_goals, "owner", "business/cafe"))

    # --- preference_recommendation
    for gname in ("history", "popular science", "literary fiction", "crime"):
        gl = [i for i in tg(f"genre_like:{gname}") if "reading_pref_current" in g.by_id[i]["tags"]]
        for q in (f"in the mood for some {gname} — suggestions?", f"recommend a {gname} book I'd like"):
            X.append(("preference_recommendation", q, gl, "owner", "reading"))
    for m in MEMBER_IDS:
        nm = g.entities[mem_eid[m]]["name"].split()[0]
        need = [tg(f"member_pref:{m}")[0], H("gym.timetable"), H(f"{m}.program")]
        X.append(("preference_recommendation", f"what class add-on would {nm} enjoy?", need, "partner_gym", "business/gym"))
        X.append(("preference_recommendation", "any class you'd suggest I try?", need, f"member_{m}", "business/gym"))
    kid_places = {"p_ruby": ["place:pl_bramble", "place:pl_lantern"], "p_theo": ["place:pl_ferngully"], "p_mila": ["place:pl_tidewater"]}
    for kid, pl in kid_places.items():
        nm = g.entities[kid]["name"]
        need = [tg(f"kid_pref:{kid}")[0]] + [tg(p)[0] for p in pl if tg(p)] + (tg("allergy") if kid == "p_ruby" else [])
        for i, q in enumerate((f"outing {nm} would enjoy?", f"take {nm} somewhere special — where?", f"one-on-one day with {nm}, ideas?")):
            X.append(("preference_recommendation", q, need, "household" if i % 2 else "owner", "family"))
    for i, q in enumerate(("what kind of accommodation should we book for the trip?", "cabin, hotel or lodge for the family?", "where should we stay on holiday?", "what worked last time we went away?")):
        X.append(("preference_recommendation", q, tg("holiday_pref"), "household" if i % 2 else "owner", "family"))
    for i, q in enumerate(("gift idea for Priya?", "how should I spoil Priya on Mother's Day?", "treat for Priya?")):
        X.append(("preference_recommendation", q, [tg("priya_food_pref")[0], tg("restaurant_pref")[0]], "owner", "family"))
    dislikes = tg("genre_dislike:fantasy") + tg("genre_dislike:business")
    for q in ("anything I should skip on the bestseller list?", "which books would I hate?", "don't recommend me what kind of books?", "genres to avoid for me?"):
        X.append(("preference_recommendation", q, dislikes, "owner", "reading"))

    # --- multimodal
    for lift in ("squat", "bench", "deadlift"):
        pair = tg(f"mm_form:{lift}:0") + tg(f"mm_form:{lift}:1")
        for q in (f"technique footage of my {lift}", f"where are the {lift} recordings Ben sent?"):
            X.append(("multimodal", q, pair, "owner", None))
    for b, partner in (("b_cafe", "partner_cafe"), ("b_gym", "partner_gym"), ("b_con", "partner_construction")):
        X.append(("multimodal", f"show the {g.entities[b]['aliases'][1]} receipt scans", tg(f"mm_receipt:{b}:0") + tg(f"mm_receipt:{b}:1"), partner, None))
    for p in props:
        X.append(("multimodal", f"the latest valuation document for {tb.alias(p)}", tg(f"mm_valreport:{p}"), "owner", None))
        it = g.by_id[tg(f"mm_listing:{p}:1")[0]]
        room = it["media"]["caption"].split(" ")[-2:]
        X.append(("multimodal", f"picture of the {' '.join(room)} at {tb.alias(p, plain=True)}", [it["id"]], "owner", None))
        it0 = g.by_id[tg(f"mm_listing:{p}:0")[0]]
        X.append(("multimodal", f"the {it0['media']['caption']} shot from {tb.alias(p)}'s listing", [it0["id"]], "owner", None))
    for kid, ev in (("p_ruby", "piano recital"), ("p_mila", "regional swim meet"), ("p_theo", "basketball grand final")):
        nm = g.entities[kid]["name"]
        for i, q in enumerate((f"all the {ev} pictures of {nm}", f"{nm}'s {ev} album")):
            X.append(("multimodal", q, tg(f"mm_family:{kid}"), "household" if i % 2 else "owner", None))
    for i, topic in enumerate(["membership pricing tiers", "summer timetable", "recovery room layout"]):
        X.append(("multimodal", f"image of the {topic} we sketched", tg(f"mm_whiteboard:{i}"), "partner_gym", None))
    for i, board in enumerate(["breakfast menu", "lunch specials", "drinks and pricing"]):
        X.append(("multimodal", f"the {board} photo from the team chat", tg(f"mm_menu:{i}"), "partner_cafe", None))
    for prid in projects:
        pair = tg(f"mm_defect:{prid}:0") + tg(f"mm_defect:{prid}:1")
        for q in (f"defect pics for the {tb.alias(prid, plain=True)} handover", f"images of the issues at {tb.alias(prid)}"):
            X.append(("multimodal", q, pair, "partner_construction", None))
        for j in (0, 1):
            it = g.by_id[tg(f"mm_defect:{prid}:{j}")[0]]
            X.append(("multimodal", f"find the {it['media']['caption'].split(': ')[-1]} photo — {tb.alias(prid)}", [it["id"]], "partner_construction", None))

    # --- temporal_change
    for p in props:
        X.append(("temporal_change", f"how has our equity in {tb.alias(p)} changed since we started tracking?",
                  [versions(f"{p}.valuation")[0], versions(f"{p}.loan")[0], H(f"{p}.valuation"), H(f"{p}.loan")], "owner", None))
    for h in holds:
        X.append(("temporal_change", f"every quarterly mark on {tb.alias(h)} please", versions(f"{h}.value"), "owner", None))

    for cls, q, req, r, prim in X:
        tb.add(cls, q, req, r, primary=prim, temporal=(cls == "temporal_change"))

    # ============================================================ activity trails (for I12)
    # A trail is the last 6 items the requester touched before asking. With prob (1-noise) each item comes from
    # one of the task's required scope groups (primary first), else from a random permitted group.
    by_group_part = {}
    for it in g.items:
        sgp = scope_group(it["scope"])
        if sgp:
            by_group_part.setdefault((sgp, it["partition"]), []).append(it["id"])
    trng = random.Random(4242)
    for t in tb.out:
        parts = tb.ident[t["requester"]]["partitions"]
        groups_allowed = sorted({gg for (gg, pp) in by_group_part if pp in parts})
        trail_true = []
        for _ in range(6):
            grp = t["declared_scope"] if trng.random() < 0.7 else trng.choice(t["required_scope_groups"])
            pool = [i for pp in parts for i in by_group_part.get((grp, pp), [])]
            trail_true.append(trng.choice(pool) if pool else None)
        t["trail_on_task"] = [x for x in trail_true if x]
        t["trail_noise_draws"] = [trng.random() for _ in range(6)]
        t["trail_noise_items"] = []
        for _ in range(6):
            grp = trng.choice(groups_allowed)
            pool = [i for pp in parts for i in by_group_part.get((grp, pp), [])]
            t["trail_noise_items"].append(trng.choice(pool))
    g.tasks = tb.out
    return tb.out
