"""Gold tasks for BrainBench v0.2 (batch 2). Every class gets >=120 DISTINCT required sets; most sets get one
phrasing, ~30% get a second (different wording and, where possible, a different requester). Phrasings are drawn
from pools of 3-8 templates and then perturbed (greeting prefixes, sign-offs, capitalisation, dropped '?').

Each task carries `set_id` (hash of the sorted required IDs) so intervals and tests can be computed over distinct
sets (cluster-aware) instead of tasks.
"""
from __future__ import annotations

import hashlib
import random
import re
from collections import Counter, defaultdict

from .common import NOW_DAY
from .tasks import scope_group

CLASSES2 = ["decision_support", "option_analysis", "current_state", "temporal_change", "goal_tracking",
            "preference_recommendation", "cross_domain", "multimodal"]

PREFIX = ["", "", "", "", "hey, ", "quick one — ", "can you check: ", "need to know: ", "ok so ", "question: "]
SUFFIX = ["", "", "", "", " thanks", " cheers", " (for the meeting)", " — no rush", " pls", " asap"]


def set_id(req):
    return hashlib.md5("|".join(sorted(req)).encode()).hexdigest()[:12]


ATTRQ = {
    "valuation": ["what would {a} fetch if we sold it today?", "what's {a} worth these days?", "latest number on what {a} is worth?", "has anyone put a price on {a} recently?", "if we listed {a} tomorrow, what would it go for?"],
    "loan_balance": ["how much do we still owe on {a}?", "what's left on the mortgage for {a}?", "debt remaining against {a}?", "what's the outstanding debt on {a}?"],
    "interest_rate": ["what interest are we paying on {a} right now?", "what rate is the {a} mortgage on?", "what's the lender charging us on {a}?"],
    "weekly_rent": ["what's {a} bringing in each week?", "how much is the tenant at {a} paying?", "weekly income from {a}?"],
    "property_manager": ["who looks after {a} for us?", "which agency manages {a}?", "who's the agent handling {a}?"],
    "lease_end": ["when is the tenant at {a} up for renewal?", "when does the current lease at {a} finish?", "how long has the tenant at {a} got left?"],
    "units": ["how many {a} do I hold?", "what's my position size in {a}?", "how many shares of {a} have I got?"],
    "market_value": ["what's my {a} stake worth?", "how much is the {a} position worth now?", "dollar value of my {a} holding?"],
    "client_retention": ["how well does {a} keep clients?", "what share of {a}'s clients stick around?", "is {a} holding on to their clients?"],
    "retention_target": ["what retention number is {a} meant to hit?", "what client-keeping goal did we set {a}?"],
    "status": ["where's {a} up to?", "how far along is {a}?", "what stage is {a} at?"],
    "contract_value": ["how big is the {a} contract?", "what's {a} worth to us as a job?"],
    "cost_to_date": ["how much have we spent on {a} so far?", "what's {a} cost us to date?", "spend to date on {a}?"],
    "training_goal": ["what's {a} working towards on the training side?", "which certification is {a} going for?"],
}
CAFE_THING = {"beans": "coffee", "milk": "milk", "bread": "bread", "produce": "fruit and veg", "cleaning": "cleaning", "packaging": "takeaway cups and boxes", "linen": "tea towels and aprons"}
MEMBERQ = {"plan": ["what membership is {a} on?", "which plan is {a} paying for?"], "program": ["what's {a} doing in the gym these days?", "what training block is {a} on?"],
           "coach": ["who's looking after {a}?", "which coach is assigned to {a}?"], "goal": ["what's {a} working towards?", "what goal did {a} set?"],
           "progress": ["where's {a} at with their progress?", "latest progress numbers for {a}?"]}
SELFQ = {"plan": ["what plan am I on?", "which membership am I paying for?"], "program": ["what program have I been given?", "what should I be doing in my sessions?"],
         "coach": ["who's my coach?", "who do I talk to about my training?"], "goal": ["what did I say my goal was?", "remind me what I'm working towards"],
         "progress": ["how am I tracking?", "what were my latest numbers?"]}
KEYQ = {
    "offset.balance": ["how much cash have we got sitting in the offset?", "what's our buffer looking like at the moment?", "spare cash on hand right now?"],
    "portfolio.borrowing_capacity": ["how much could we borrow right now?", "what's the most the bank would lend us at the moment?"],
    "portfolio.lvr_rule": ["what's our gearing limit again?", "how far are we prepared to leverage the properties?"],
    "portfolio.strategy": ["what's our property game plan these days?", "remind me of the investing approach we settled on"],
    "offset.savings_goal": ["how big a rainy-day fund did we say we wanted?", "what's the emergency money target?"],
    "household.budget": ["what's our monthly spending allowance for the house?", "what did we set the family budget at?"],
    "edu.goal": ["how much did we want saved for the kids' schooling?", "what's the target for the education fund?"],
    "edu.balance": ["how much is in the kids' school savings?", "what's the education fund sitting at?"],
    "gym.members": ["how many people are signed up at {g}?", "what's our member count at {g}?"],
    "gym.member_target": ["what number of members are we aiming for at {g}?", "what's the growth goal for {g}?"],
    "gym.head_coach": ["who's in charge of the coaching team at {g}?", "who leads the coaches at {g} now?"],
    "gym.equipment_supplier": ["who do we buy gym gear from?", "which company supplies the weights and machines at {g}?"],
    "gym.towel_supplier": ["who does the towels at {g}?", "which laundry service does {g} use?"],
    "gym.cleaner": ["who cleans {g}?", "which cleaning company does {g} use?"],
    "gym.insurer": ["who insures {g}?", "which insurer covers the gym business?"],
    "gym.lease": ["what does the premises cost {g} each month?", "what's the rent on the {g} building?"],
    "gym.staff_count": ["how many people work at {g} now?", "how big is the {g} team?"],
    "gym.price": ["what do we charge for a standard membership at {g}?", "how much is a weekly membership?"],
    "gym.timetable": ["when are classes on at {g}?", "what's the class schedule at {g}?"],
    "gym.revenue_goal": ["what's the sales target for {g} this year?", "what turnover are we aiming for at {g}?"],
    "con.pipeline": ["how much work has {c} got signed up?", "what's the forward order book for {c}?"],
    "con.active_projects": ["how many jobs is {c} running?", "how many sites are live at the moment?"],
    "con.concrete_supplier": ["who pours our concrete?", "which readymix company does {c} use?"],
    "con.supervisor": ["who's running the sites for {c}?", "who supervises our building jobs?"],
    "con.insurance": ["what's {c} paying for liability cover?", "how much is the building business's insurance?"],
    "con.plumbing_sub": ["who does {c}'s plumbing?", "which plumber do we sub out to on builds?"],
    "con.strategy": ["what kind of jobs will {c} tender for?", "what's our policy on which builds we quote?"],
    "con.pipeline_target": ["how much forward work do we want {c} to carry?", "what's the order book goal for {c}?"],
    "con.margin_target": ["what margin are we aiming for on {c} jobs?", "what's {c}'s profitability goal?"],
    "con.margin": ["what margin is {c} making on jobs?", "how profitable are {c}'s jobs at the moment?"],
    "con.safety_target": ["what's {c}'s safety goal?", "what injury target did we set on site?"],
    "con.incidents": ["any lost-time injuries at {c} this year?", "how's {c}'s injury count?"],
    "cafe.hours": ["when is {f} open?", "what are {f}'s trading times?"],
    "cafe.head_barista": ["who's the lead on coffee at {f}?", "who runs the machine at {f}?"],
    "cafe.covers": ["how many customers is {f} serving a week?", "how busy is {f} week to week?"],
    "cafe.cash_reserve": ["how much money has {f} got in the bank?", "what's {f}'s reserve sitting at?"],
    "cafe.revenue_goal": ["what's the sales goal for {f} this year?", "what turnover are we targeting at {f}?"],
    "cafe.distribution_rule": ["what are the rules for taking money out of {f}?", "what does the partnership say about drawings from {f}?"],
    "cafe.covers_target": ["how many customers a week are we aiming for at {f}?", "what's the foot-traffic goal at {f}?"],
    "cafe.waste_target": ["what's our food waste goal at {f}?", "how low did we want waste at {f}?"],
    "cafe.waste": ["how much food are we throwing out at {f}?", "what's waste running at in {f}'s kitchen?"],
    "train.squat_1rm": ["what's my best squat at the moment?", "how much can I squat now?"],
    "train.bench_1rm": ["what's my current max bench?", "how much am I benching for a single?"],
    "train.deadlift_1rm": ["what's my deadlift max?", "how heavy can I pull right now?"],
    "train.press_1rm": ["what's my best strict press?", "how much can I press overhead?"],
    "train.bodyweight": ["what do I weigh at the moment?", "where's my weight sitting?"],
    "train.program": ["what program am I following?", "which training plan am I on?"],
    "train.sessions": ["how often am I training per week?", "how many times a week am I getting to the gym?"],
    "train.run10k": ["what's my latest 10k time?", "how fast am I running 10 kilometres now?"],
    "train.coach": ["who's coaching me?", "who writes my training?"],
    "goal_squat.target": ["what's the squat number I'm chasing?", "remind me of my squat goal"],
    "goal_run.target": ["what time am I aiming for over 10k?", "what's my running target?"],
    "goal.deadlift": ["what deadlift am I aiming for?", "remind me of the pulling goal"],
    "goal.bench": ["what bench am I chasing?", "what's the bench press goal?"],
    "goal.press": ["what overhead press am I working towards?", "what's my pressing goal?"],
    "goal.bodyweight": ["what weight am I trying to get to?", "what's my target bodyweight?"],
    "reading.goal": ["how many books did I want to get through this year?", "what's my reading target?"],
    "reading.finished": ["how many books have I knocked over this year?", "how's the book count going?"],
    "reading.current": ["what am I reading at the moment?", "which book is on the go?"],
    "mila.activity": ["what's Mila doing for sport these days?", "when is Mila training?"],
    "theo.activity": ["what's Theo signed up for this term?", "when is Theo's sport on?"],
    "ruby.activity": ["what does Ruby do after school?", "what lessons is Ruby doing?"],
    "mila.swim_pb": ["what's Mila's fastest 100 free?", "Mila's best swim time?"],
    "mila.swim_goal": ["what does Mila need to swim to make regionals?", "what's Mila's qualifying target?"],
    "theo.goal": ["what is Theo aiming for in basketball?", "what's Theo's big sport goal?"],
    "ruby.goal": ["what's Ruby working towards with piano?", "which exam is Ruby preparing for?"],
    "family.holiday_budget": ["how much did we set aside for holidays?", "what's the travel budget?"],
    "family.holiday_fund": ["how much have we saved for the trip so far?", "what's in the holiday kitty?"],
    "family.school_break": ["when are the spring school holidays?", "dates for the September school break?"],
}
REVQ = ["how much did {a} take in {q}?", "{q} turnover for {a}?", "what were {a}'s sales in {q}?"]
LABEL_PARA = {
    "training program": ["programming", "training block", "what they've been doing in sessions"], "membership plan": ["membership", "what they pay for at the gym", "plan at IronBark"],
    "current valuation": ["worth", "price tag", "what it would sell for"], "loan balance": ["mortgage", "debt", "what we owe"], "interest rate": ["rate", "borrowing cost"],
    "weekly rent": ["rent", "rental income"], "lease end date": ["lease expiry", "tenancy end"], "units held": ["share count", "position size"],
    "market value": ["dollar value", "stake value"], "attendance": ["visits per week", "how often they turn up"], "body composition": ["body fat", "body comp numbers"],
    "member goal": ["target", "what they're aiming for"], "deadlift best": ["deadlift", "best pull"], "project stage": ["progress on site", "build stage"],
    "cost to date": ["spend so far", "costs"], "property manager": ["managing agent", "agency"], "12-month client retention": ["client retention", "how many clients stay"],
    "pull-up count": ["pull-ups", "chin-up numbers"], "5k time": ["5k", "parkrun time"], "activities": ["sport and lessons", "after-school stuff"],
}


def para(label, rng):
    if label in LABEL_PARA:
        return rng.choice(LABEL_PARA[label])
    return label


TEMPQ = ["how has {thing} moved over the time we've tracked it?", "walk me through the changes to {thing}", "what was {thing} before, and what is it now?",
         "history of {thing}, please", "has {thing} changed? show me every step", "trend in {thing} since the start?", "how has {thing} shifted over the last year and a half?"]
TEMPQ2 = ["how does {thing} now compare with when we started tracking?", "what's {thing} done since we first logged it?", "{thing}: first record versus today?",
          "compare {thing} originally and now"]


class TB2:
    def __init__(self, g, seed):
        self.g = g
        self.rng = random.Random(1000 + seed)
        self.out = []
        self.ident = g.identities
        self.sets = defaultdict(set)

    def H(self, key):
        return self.g.keys[key]["versions"][-1]

    def V(self, key):
        return self.g.keys[key]["versions"]

    def sp(self, tag, i=0):
        lst = self.g.special.get(tag, [])
        return lst[i] if len(lst) > i else None

    def spall(self, tag):
        return list(self.g.special.get(tag, []))

    def alias(self, eid):
        e = self.g.entities[eid]
        return self.rng.choice(e["aliases"][1:] or e["aliases"])

    def style(self, q):
        R = self.rng
        q = re.sub(r"\b(my|the|our|of) the ", r"\1 ", q)
        q = R.choice(PREFIX) + q
        if R.random() < 0.15 and q.endswith("?"):
            q = q[:-1]
        q = q + R.choice(SUFFIX)
        if R.random() < 0.3:
            q = q[0].upper() + q[1:]
        return q

    def accessible(self, req, requester):
        parts = set(self.ident[requester]["partitions"])
        return all(self.g.by_id[r]["partition"] in parts for r in req)

    def add(self, cls, query, required, requester="owner", primary=None, extra_phrasings=(), alt_requesters=(), second_p=0.3, **kw):
        g = self.g
        req = list(dict.fromkeys(r for r in required if r))
        if not req:
            return
        if not self.accessible(req, requester):
            return
        groups = [scope_group(g.by_id[r]["scope"]) for r in req]
        if primary is None:
            primary = Counter(groups).most_common(1)[0][0]
        sid = set_id(req)
        if sid in self.sets[cls]:
            return  # one need-set per class enters once via this path (phrasings added below)
        self.sets[cls].add(sid)
        phr = [query]
        if extra_phrasings and self.rng.random() < second_p:
            phr.append(self.rng.choice(list(extra_phrasings)))
        for j, q in enumerate(phr):
            r = requester
            if j == 1 and alt_requesters:
                cand = [a for a in alt_requesters if self.accessible(req, a)]
                if cand:
                    r = self.rng.choice(cand)
            t = dict(id=f"t{len(self.out)+1:05d}", cls=cls, query=self.style(q), requester=r, declared_scope=primary, required=req,
                     required_scope_groups=sorted(set(groups)), size=len(req), set_id=sid)
            t.update(kw)
            self.out.append(t)

    def pick(self, phr, n=1, **fmt):
        ps = self.rng.sample(phr, min(len(phr), n + 1))
        ps = [p.format(**fmt) for p in ps]
        return ps[0], ps[1:]


def build_tasks2(g, seed):
    tb = TB2(g, seed)
    R = tb.rng
    H, V, sp, spall = tb.H, tb.V, tb.sp, tb.spall
    M = g.meta
    props, holds, projects = M["props"], M["holds"], M["projects"]
    members = sorted(M["member_names"])
    mem_eid = {m: ("p_priya" if m == "m03" else f"mem_{m}") for m in members}
    coach_ids = ["s_" + c.split()[0].lower() + "_" + c.split()[1].lower() for c in ("Sasha Novak", "Ben Okafor", "Imogen Hartley", "Raf Silva", "Corey Lin", "Tess Wardle", "Jordan Pike")]
    staff = M["cafe_staff"]
    cats = list(g.meta["cafe_cur"])
    gymcats = ["racks", "rowers", "bikes", "flooring", "dumbbells", "cables"]
    hal = M["halyard_prop"]
    fmt_g = lambda: dict(g=tb.alias("b_gym"), c=tb.alias("b_con"), f=tb.alias("b_cafe"))
    partner_of = {"biz/gym": "partner_gym", "biz/construction": "partner_construction", "biz/cafe": "partner_cafe", "household": "household"}
    first = lambda eid: g.entities[eid]["name"].split()[0]

    def biz_req(key):
        p = g.keys[key]["partition"]
        return partner_of.get(p)

    # ============================================================ current_state
    cs = []
    for key in sorted(g.keys):
        k = g.keys[key]
        attr, ent = k["attr"], k["entity"]
        fam = k["family"]
        if key.startswith("m") and key[1:3].isdigit():
            m, a2 = key.split(".")
            if R.random() < 0.5:
                cs.append((key, MEMBERQ[a2], dict(a=first(mem_eid[m])), "partner_gym", [f"member_{m}"], SELFQ[a2]))
            else:
                cs.append((key, SELFQ[a2], {}, f"member_{m}", ["partner_gym"], [q.format(a=first(mem_eid[m])) for q in MEMBERQ[a2]]))
        elif fam == "revenue":
            ql = key.split(".")[-1]
            cs.append((key, REVQ, dict(a=tb.alias(ent), q=f"Q{ql[-1]} {ql[:4]}"), "owner", [biz_req(key)] if biz_req(key) else [], None))
        elif key in KEYQ:
            alts = ["owner"] + ([biz_req(key)] if biz_req(key) else [])
            cs.append((key, KEYQ[key], fmt_g(), "owner", alts, None))
        elif attr in ATTRQ:
            alts = [biz_req(key)] if biz_req(key) else []
            cs.append((key, ATTRQ[attr], dict(a=tb.alias(ent)), "owner", alts, None))
        elif attr.endswith("_supplier") and attr[:-9] in CAFE_THING:
            th = CAFE_THING[attr[:-9]]
            cs.append((key, [f"who do we get {th} from at {{f}}?", f"which company does {{f}}'s {th} now?", f"{th} supplier for {{f}}?"], fmt_g(), "owner", ["partner_cafe"], None))
    R.shuffle(cs)
    for key, phr, fm, req_r, alts, alt_phr in cs:
        q, rest = tb.pick(phr, **fm)
        if alt_phr:
            rest = list(rest) + [p.format(**fm) if "{" in p else p for p in alt_phr]
        tb.add("current_state", q, [H(key)], req_r, extra_phrasings=rest, alt_requesters=alts, second_p=0.15)
    # composites (sizes 2-3)
    for p in props:
        a = tb.alias(p)
        tb.add("current_state", R.choice([f"what's our equity position in {a}?", f"how much of {a} do we actually own after the loan?"]), [H(f"{p}.valuation"), H(f"{p}.loan")])
        tb.add("current_state", R.choice([f"quick rundown on the tenancy at {a} — who manages it, what it rents for, when it's up", f"tenancy snapshot for {a}"]), [H(f"{p}.rent"), H(f"{p}.lease_end"), H(f"{p}.pm")])
        tb.add("current_state", R.choice([f"what are the borrowing terms on {a} — balance and rate?", f"loan details for {a}?"]), [H(f"{p}.loan"), H(f"{p}.rate")])
    for h in holds:
        tb.add("current_state", R.choice([f"how big is my {tb.alias(h)} holding — units and value?", f"{tb.alias(h)} position: how many and what's it worth?"]), [H(f"{h}.units"), H(f"{h}.value")])
    for m in members[:20]:
        tb.add("current_state", R.choice([f"give me the basics on {first(mem_eid[m])} — plan, program, who coaches them", f"member snapshot for {first(mem_eid[m])}"]), [H(f"{m}.plan"), H(f"{m}.program"), H(f"{m}.coach")], "partner_gym")
    for prid in projects:
        tb.add("current_state", R.choice([f"budget versus spend on {tb.alias(prid)}?", f"is {tb.alias(prid)} on budget so far?"]), [H(f"{prid}.budget"), H(f"{prid}.cost")], "owner", alt_requesters=["partner_construction"])

    # ============================================================ stale probes
    for key in sorted(g.keys):
        k = g.keys[key]
        if len(k["versions"]) < 2:
            continue
        cur = [t for t in tb.out if t["cls"] == "current_state" and t["required"] == [H(key)]]
        if not cur:
            continue
        stale = k["versions"][:-1]
        ss = set(stale)
        traps = [i["id"] for i in g.items if i.get("fact_refs") and set(i["fact_refs"]) & ss]
        t0 = cur[0]
        tb.out.append(dict(id=f"t{len(tb.out)+1:05d}", cls="stale_probe", query=t0["query"], requester=t0["requester"], declared_scope=t0["declared_scope"],
                           required=[H(key)], required_scope_groups=t0["required_scope_groups"], size=1, set_id=set_id([H(key)]), key=key, stale_ids=stale, trap_ids=traps))

    # ============================================================ temporal_change
    tkeys = [k for k in sorted(g.keys) if len(g.keys[k]["versions"]) >= 2]
    R.shuffle(tkeys)
    for key in tkeys:
        k = g.keys[key]
        ent = k["entity"]
        lab = para(k["label"], R)
        if key.startswith("m") and key[1:3].isdigit():
            m = key.split(".")[0]
            thing = f"{first(mem_eid[m])}'s {lab}"
            reqr, alts = "partner_gym", [f"member_{m}"]
        else:
            nm = tb.alias(ent) if g.entities[ent]["kind"] not in ("person_profile", "account") else ("my" if ent == "tr_me" else "our")
            thing = f"{nm} {lab}" if nm in ("my", "our") else f"{nm}'s {lab}"
            reqr, alts = "owner", ([partner_of[k["partition"]]] if k["partition"] in partner_of else [])
        vs = V(key)
        full = vs if len(vs) <= 6 else vs[-6:]
        q, rest = tb.pick(TEMPQ, thing=thing)
        tb.add("temporal_change", q, full, reqr, extra_phrasings=rest, alt_requesters=alts, temporal=True, second_p=0.2)
        if len(vs) >= 3 and R.random() < 0.5:
            q, rest = tb.pick(TEMPQ2, thing=thing)
            tb.add("temporal_change", q, [vs[0], vs[-1]], reqr, extra_phrasings=rest, alt_requesters=alts, temporal=True, second_p=0.1)
    for p in props:
        tb.add("temporal_change", R.choice([f"how has our equity in {tb.alias(p)} changed since we started tracking?", f"equity in {tb.alias(p)}: then versus now?"]),
               [V(f"{p}.valuation")[0], V(f"{p}.loan")[0], H(f"{p}.valuation"), H(f"{p}.loan")], "owner", temporal=True)

    # ============================================================ decision_support
    D = "decision_support"
    for p in props:
        a = tb.alias(p)
        q, rest = tb.pick([f"equity's up on {a}, thinking about the next purchase — what do I need to weigh up?", f"could we use the growth in {a} to fund another property?",
                           f"is now the time to pull equity out of {a} for the next deal?", f"{a} has gone up a fair bit — should we go again?", f"leverage {a} into property number {len(props)+1}?"])
        tb.add(D, q, [H(f"{p}.valuation"), H(f"{p}.loan"), H("portfolio.borrowing_capacity"), H("portfolio.strategy"), H("portfolio.lvr_rule"), H("offset.balance"), sp("inv_decision")], "owner", "finance", rest)
        q, rest = tb.pick([f"should I take the broker up on refinancing {a}?", f"is it worth switching lenders on {a}?", f"Nadia reckons we should refix {a} — does it stack up?", f"refi {a} or sit tight?"])
        tb.add(D, q, [H(f"{p}.loan"), H(f"{p}.rate"), sp(f"refi_email:{p}"), H(f"{p}.valuation"), H("portfolio.lvr_rule")], "owner", "finance", rest)
        q, rest = tb.pick([f"lease is coming up at {a} — push the rent or keep the tenant happy?", f"what should we do about the rent at {a} at renewal?", f"PM's asking how we want to handle {a} next — thoughts?"])
        tb.add(D, q, [H(f"{p}.rent"), H(f"{p}.lease_end"), sp(f"pm_email:{p}"), H(f"{p}.pm"), sp(f"reno_quote:{p}")], "owner", "finance", rest)
        q, rest = tb.pick([f"how should we respond to the tenant's request at {a}?", f"PM needs an answer on the tenant issue at {a} — what do we do?", f"the {a} tenant situation: approve, refuse or negotiate?"])
        tb.add(D, q, [sp(f"tenant_issue:{p}"), H(f"{p}.rent"), H(f"{p}.lease_end"), H(f"{p}.pm")], "owner", "finance", rest)
        if p != hal:
            q, rest = tb.pick([f"should we sell {a}?", f"is it time to offload {a}?", f"hold or sell {a} given everything?"])
            tb.add(D, q, [H(f"{p}.valuation"), H(f"{p}.loan"), H(f"{p}.rent"), H("portfolio.strategy"), sp("inv_decision")], "owner", "finance", rest)
    for h in holds:
        a = tb.alias(h)
        q, rest = tb.pick([f"should I trim {a}?", f"thinking of selling some {a} — sensible?", f"{a} has had a run, take profits or hold?", f"add to {a} or leave it?", f"rebalance: is {a} too big for me now?"])
        tb.add(D, q, [H(f"{h}.units"), H(f"{h}.value"), sp(f"thesis:{h}"), H("portfolio.strategy")], "owner", "finance", rest)
    for m in R.sample(members, 24):
        nm = first(mem_eid[m])
        q, rest = tb.pick([f"should we move {nm} onto a different membership?", f"is {nm} on the right plan for what they're doing?", f"upgrade or downgrade {nm}'s membership?"])
        tb.add(D, q, [H(f"{m}.plan"), H(f"{m}.progress"), H(f"{m}.goal"), sp(f"member_pref:{m}"), H("gym.price")], "partner_gym", "business/gym", rest)
    for i in range(8):
        tid = f"tender_{i}"
        a = g.entities[tid]["name"]
        q, rest = tb.pick([f"should {{c}} bid on the {a}?", f"do we tender for the {a}?", f"is the {a} one we should price?", f"go or no-go on the {a} tender?"], **fmt_g())
        tb.add(D, q, [sp(f"tender:{tid}"), sp("con_capacity"), sp("con_tender_decision"), H("con.strategy"), H("con.pipeline"), H("con.margin")], "owner", "business/construction", rest, ["partner_construction"])
    for prid in projects:
        a = tb.alias(prid)
        q, rest = tb.pick([f"do we wear the overrun on {a} or push it back to the client?", f"how should we handle the variation on {a}?", f"is {a} still going to make money?"])
        tb.add(D, q, [sp(f"proj_variation:{prid}"), H(f"{prid}.budget"), H(f"{prid}.cost"), H("con.margin_target")], "owner", "business/construction", rest, ["partner_construction"])
    for cat in cats:
        th = CAFE_THING[cat]
        q, rest = tb.pick([f"do we terminate the {th} contract?", f"is it time to give our {th} supplier notice?", f"should we walk away from the current {th} supplier now?", f"cut ties on {th} — yes or no?"])
        tb.add(D, q, [sp(f"cafe_contract:{cat}"), H(f"cafe.{cat}_supplier")] + spall(f"cafe_incident:{cat}"), "owner", "business/cafe", rest, ["partner_cafe"])
    for cat in gymcats:
        from .world2 import GYM_CATS
        what = GYM_CATS[cat][0]
        q, rest = tb.pick([f"replace the {what} now or patch them up?", f"should we buy new {what} for the gym?", f"{what} — fix, replace or wait?"])
        tb.add(D, q, [sp(f"gym_issue:{cat}")] + spall(f"gym_quote:{cat}") + [H("gym.revenue.2026Q2"), sp("commit:gym_fitout")], "owner", "business/gym", rest, ["partner_gym"])
    for sid in coach_ids:
        nm = first(sid)
        q, rest = tb.pick([f"is {nm} performing well enough to keep on full hours?", f"should we give {nm} more clients or fewer?", f"how do we handle {nm}'s performance review?"])
        tb.add(D, q, [H(f"{sid}.retention"), H(f"{sid}.retention_target"), sp(f"coach_review:{sid}"), sp(f"coach_spec:{sid}")], "owner", "business/gym", rest, ["partner_gym"])
    for sid in staff:
        nm = first(sid)
        q, rest = tb.pick([f"is {nm} ready to step up to head barista?", f"should we promote {nm}?", f"give {nm} more responsibility on the coffee side?"])
        tb.add(D, q, [g.keys[f"{sid}.training_goal"]["versions"][-1], sp(f"staff_progress:{sid}"), sp(f"staff_pref:{sid}"), H("cafe.head_barista")], "owner", "business/cafe", rest, ["partner_cafe"])
    for i in range(5):
        from .world2 import TRIPS
        tn = TRIPS[i][0]
        q, rest = tb.pick([f"should we book the {tn} for September?", f"is the {tn} trip a good call?", f"{tn} — yes or no for the school break?"])
        tb.add(D, q, [sp(f"trip:{i}"), H("family.holiday_budget"), H("family.holiday_fund"), sp("holiday_pref", 0), H("family.school_break")], "owner", "family", rest, ["household"])
    for q in ("should I enter a powerlifting meet in September?", "am I ready to compete this year?", "thinking of doing my first meet — good idea?"):
        pass
    tb.add(D, "should I enter a powerlifting meet in September?", [H("train.squat_1rm"), H("train.bench_1rm"), H("train.deadlift_1rm"), H("goal_squat.target"), H("train.program"), sp("knee_note"), sp("coach_advice")], "owner", "health",
           ["am I ready to compete this year?", "thinking of doing my first meet — good idea?"])
    tb.add(D, "can Tomas and I take a distribution from the cafe?", [H("cafe.cash_reserve"), H("cafe.distribution_rule"), H("cafe.revenue.2026Q2"), H("cafe.revenue_goal")], "owner", "business/cafe",
           ["is there room to pay ourselves out of Copperleaf?"], ["partner_cafe"])
    tb.add(D, "6am classes are packed — do we hire another coach?", [H("gym.members"), H("gym.member_target"), sp("gym_hire_decision"), H("gym.staff_count"), sp("gym_capacity"), H("gym.head_coach")], "owner", "business/gym",
           ["we keep turning people away at peak — time to hire?"], ["partner_gym"])
    tb.add(D, "should we put membership prices up again?", [H("gym.price"), sp("gym_price_decision"), H("gym.members"), H("gym.revenue.2026Q2"), H("gym.lease")], "owner", "business/gym", ["can IronBark handle another price rise?"], ["partner_gym"])

    # ============================================================ option_analysis
    O = "option_analysis"
    for p in props:
        a = tb.alias(p)
        q, rest = tb.pick([f"what can we do to get more out of {a}?", f"options for improving the return on {a}?", f"refresh, hold or cut the rent at {a} — lay out the options"])
        tb.add(O, q, [sp(f"pm_email:{p}"), H(f"{p}.rent"), H(f"{p}.valuation"), sp(f"reno_quote:{p}")], "owner", "finance", rest)
    for cat in cats:
        th = CAFE_THING[cat]
        q, rest = tb.pick([f"our {th} supplier keeps letting us down — what are the options?", f"who else could do our {th}, and can we get out of the current deal?", f"plan B for {th}?", f"lay out our choices on the {th} problem"])
        tb.add(O, q, [H(f"cafe.{cat}_supplier"), sp(f"cafe_contract:{cat}")] + spall(f"cafe_quote:{cat}"), "owner", "business/cafe", rest, ["partner_cafe"])
    for cat in gymcats:
        from .world2 import GYM_CATS
        what = GYM_CATS[cat][0]
        q, rest = tb.pick([f"what are our options for the {what}?", f"who could supply new {what} and at what price?", f"compare the quotes for the {what}"])
        tb.add(O, q, [sp(f"gym_issue:{cat}"), H("gym.equipment_supplier")] + spall(f"gym_quote:{cat}"), "owner", "business/gym", rest, ["partner_gym"])
    for m in members:
        nm = first(mem_eid[m])
        q, rest = tb.pick([f"{nm} has plateaued — what could we try?", f"options for changing up {nm}'s training?", f"what are the next-step options for {nm}?"])
        tb.add(O, q, [H(f"{m}.program"), H(f"{m}.progress"), H(f"{m}.goal"), sp(f"member_pref:{m}")], "partner_gym", "business/gym", rest, [f"member_{m}"])
    for prid in projects:
        a = tb.alias(prid)
        q, rest = tb.pick([f"options to get {a} moving faster?", f"what levers do we have on {a}'s timeline?", f"{a} is stuck — what can we do?"])
        tb.add(O, q, [H(f"{prid}.status"), sp(f"proj_issue:{prid}"), sp("con_capacity"), H("con.supervisor")], "partner_construction", "business/construction", rest, ["owner"])
    for p in props:
        a = tb.alias(p)
        q, rest = tb.pick([f"what are our options on the tenant issue at {a}?", f"lay out the choices for the tenant request at {a}", f"how could we handle the tenant at {a} — options?"])
        tb.add(O, q, [sp(f"tenant_issue:{p}"), H(f"{p}.lease_end"), H(f"{p}.pm")], "owner", "finance", rest)
    for h in holds:
        a = tb.alias(h)
        q, rest = tb.pick([f"what are my options with {a}?", f"{a}: hold, trim, or exit — what are the choices?"])
        tb.add(O, q, [H(f"{h}.units"), H(f"{h}.value"), sp(f"thesis:{h}")], "owner", "finance", rest)
    for kid, goal, note, act in (("p_theo", "theo.goal", "theo_coach_note", "theo.activity"), ("p_ruby", "ruby.goal", "ruby_teacher_note", "ruby.activity"), ("p_mila", "mila.swim_goal", "mila_coach_note", "mila.activity")):
        nm = g.entities[kid]["name"]
        q, rest = tb.pick([f"how can we help {nm} reach the goal — options?", f"what could {nm} change to get there?", f"options to support {nm} this term?"])
        tb.add(O, q, [H(goal), sp(note), H(act)], "owner", "family", rest, ["household"])
    for sid in coach_ids:
        nm = first(sid)
        q, rest = tb.pick([f"how could {nm} lift client retention — options?", f"ideas for {nm} to keep more clients?"])
        tb.add(O, q, [H(f"{sid}.retention"), sp(f"coach_review:{sid}"), sp(f"coach_spec:{sid}")], "owner", "business/gym", rest, ["partner_gym"])
    for q, req, pr in (("squat's stalled — what are my options?", [H("goal_squat.target"), H("train.squat_1rm"), sp("coach_advice"), sp("knee_note"), H("train.program"), sp("training_clash")], "health"),
                       ("running's plateaued, what are my options?", [H("goal_run.target"), H("train.run10k"), sp("run_plan"), sp("knee_note")], "health"),
                       ("pressing has stalled and the shoulder's cranky — options?", [H("goal.press"), H("train.press_1rm"), sp("shoulder_note"), H("train.program")], "health"),
                       ("what could we do with the cafe's reserve?", [H("cafe.cash_reserve"), H("cafe.distribution_rule"), H("cafe.revenue_goal")], "business/cafe"),
                       ("what are the options for growing membership at the gym?", [H("gym.members"), H("gym.member_target"), H("gym.price"), sp("gym_capacity"), H("gym.timetable")], "business/gym"),
                       ("options for adding supervision capacity at Stonefield?", [sp("con_capacity"), H("con.supervisor"), H("con.active_projects")], "business/construction"),
                       ("how do we rebuild the buffer faster?", [H("offset.balance"), H("offset.savings_goal"), sp("inv_decision"), sp("commit:gym_fitout")], "finance"),
                       ("options for getting cafe food waste down?", [H("cafe.waste"), H("cafe.waste_target")] + spall("cafe_incident:produce"), "business/cafe"),
                       ("options for covering the senior coffee role?", [H("cafe.head_barista"), sp("cafe_roster"), sp("cafe_recruit_quote")], "business/cafe"),
                       ("Brightwater or another plumber — what are the options?", [sp("supfb:sup_brightwater:b_cafe"), sp("supfb:sup_brightwater:b_con"), H("con.plumbing_sub")], None),
                       ("options for linen — stick with Talbot or shop around?", [sp("supfb:sup_talbot:b_gym"), sp("supfb:sup_talbot:b_cafe"), H("gym.towel_supplier"), H("cafe.linen_supplier")], None),
                       ("holiday options for the spring break?", [H("family.school_break"), H("family.holiday_budget"), sp("holiday_pref", 0), sp("holiday_pref", 1)] + [sp(f"trip:{i}") for i in range(5)], "family")):
        tb.add(O, q, req, "owner", pr)

    # ============================================================ goal_tracking
    G = "goal_tracking"
    for m in members:
        nm = first(mem_eid[m])
        base = [H(f"{m}.goal"), H(f"{m}.progress")]
        q, rest = tb.pick([f"is {nm} on track for their goal?", f"how is {nm} going against what they set out to do?", f"{nm}'s goal — are we getting them there?", f"progress report on {nm}'s goal please"])
        tb.add(G, q, base + [sp(f"member_checkin:{m}"), H(f"{m}.program")], "partner_gym", "business/gym", rest)
        q, rest = tb.pick(["am I on track for my goal?", "how close am I to what I set out to achieve?", "am I getting there with my goal?"])
        tb.add(G, q, base + [sp(f"member_checkin:{m}")], f"member_{m}", "business/gym", rest)
        if R.random() < 0.5:
            tb.add(G, R.choice([f"is {nm}'s coach getting results on their goal?", f"goal check for {nm}, and who's coaching them?"]), base + [H(f"{m}.coach")], "partner_gym", "business/gym")
    for sid in coach_ids:
        nm = first(sid)
        q, rest = tb.pick([f"is {nm} hitting the retention target?", f"{nm}'s client retention versus goal?", f"how's {nm} tracking on keeping clients?"])
        tb.add(G, q, [H(f"{sid}.retention_target"), H(f"{sid}.retention"), sp(f"coach_review:{sid}")], "owner", "business/gym", rest, ["partner_gym"])
    for sid in staff:
        nm = first(sid)
        q, rest = tb.pick([f"how's {nm} going with their training goal?", f"is {nm} on track for the certification?", f"{nm}'s training progress?"])
        tb.add(G, q, [g.keys[f"{sid}.training_goal"]["versions"][-1], sp(f"staff_progress:{sid}")], "owner", "business/cafe", rest, ["partner_cafe"])
    owner_goals = [
        (["am I on track for the squat target?", "squat's been stuck — will I make my goal in time?", "realistic chance of hitting the big squat number by September?"], [H("goal_squat.target"), H("train.squat_1rm"), H("train.program"), sp("coach_advice"), sp("knee_note"), H("train.sessions")], "health"),
        (["will I get under the running target in time?", "how's the 10k goal going?", "is the running goal on track given the knee?"], [H("goal_run.target"), H("train.run10k"), sp("run_plan"), sp("knee_note")], "health"),
        (["how's the deadlift goal looking?", "am I going to hit my pulling target this year?"], [H("goal.deadlift"), H("train.deadlift_1rm"), H("train.program")], "health"),
        (["bench goal — am I there yet?", "how far off the bench target am I?"], [H("goal.bench"), H("train.bench_1rm")], "health"),
        (["how's the overhead press goal going?", "am I closer to a bodyweight press?"], [H("goal.press"), H("train.press_1rm"), sp("shoulder_note")], "health"),
        (["am I getting closer to the weight I wanted?", "how much more weight to lose to hit my target?"], [H("goal.bodyweight"), H("train.bodyweight")], "health"),
        (["is the rainy-day fund where we wanted it?", "have we rebuilt the buffer to target?"], [H("offset.savings_goal"), H("offset.balance")], "finance"),
        (["are we on track with the kids' education savings?", "education fund versus target?"], [H("edu.goal"), H("edu.balance")], "finance"),
        (["am I on pace for my reading goal?", "will I hit the book target this year?"], [H("reading.goal"), H("reading.finished")], "reading"),
        (["are we going to make the gym's membership goal?", "can we lift the coach hiring freeze yet — are we past the member number?"], [H("gym.member_target"), H("gym.members"), sp("gym_hire_decision")], "business/gym"),
        (["is the gym on pace for its sales target?", "gym revenue versus this year's goal?"], [H("gym.revenue_goal"), H("gym.revenue.2026Q1"), H("gym.revenue.2026Q2")], "business/gym"),
        (["is the cafe hitting its customer goal?", "has Sunday trading helped us hit the covers goal?"], [H("cafe.covers_target"), H("cafe.covers"), sp("cafe_sunday_decision")], "business/cafe"),
        (["is the cafe on track for its sales target this year?", "half-year check: cafe sales versus target"], [H("cafe.revenue_goal"), H("cafe.revenue.2026Q1"), H("cafe.revenue.2026Q2")], "business/cafe"),
        (["are we winning on food waste at the cafe?", "waste versus target at Copperleaf?"], [H("cafe.waste_target"), H("cafe.waste")], "business/cafe"),
        (["is Stonefield carrying enough forward work?", "can Stonefield grow toward its pipeline target with current crew?"], [H("con.pipeline_target"), H("con.pipeline"), sp("con_capacity")], "business/construction"),
        (["is Stonefield making the margin we wanted?", "margin versus target on our builds?"], [H("con.margin_target"), H("con.margin")], "business/construction"),
        (["how are we going on the safety goal at Stonefield?", "are we still at zero injuries this year?"], [H("con.safety_target"), H("con.incidents")], "business/construction"),
        (["is Mila going to qualify for regionals?", "what does Mila still need to drop to qualify?"], [H("mila.swim_goal"), H("mila.swim_pb"), sp("mila_coach_note")], "family"),
        (["will Theo make the rep team?", "how's Theo tracking for the trials?"], [H("theo.goal"), sp("theo_coach_note"), H("theo.activity")], "family"),
        (["is Ruby ready for her piano exam?", "how's Ruby going towards grade 3?"], [H("ruby.goal"), sp("ruby_teacher_note")], "family"),
        (["are we saving fast enough for the holiday?", "holiday fund versus budget?"], [H("family.holiday_budget"), H("family.holiday_fund")], "family"),
        (["how am I going on all my training goals?", "full scorecard on my fitness targets"], [H("goal_squat.target"), H("train.squat_1rm"), H("goal.deadlift"), H("train.deadlift_1rm"), H("goal.bench"), H("train.bench_1rm"), H("goal_run.target"), H("train.run10k"), H("goal.bodyweight"), H("train.bodyweight")], "health"),
        (["scorecard: how are all three businesses tracking against their goals?", "are the businesses hitting their numbers this year?"], [H("gym.member_target"), H("gym.members"), H("cafe.covers_target"), H("cafe.covers"), H("cafe.revenue_goal"), H("cafe.revenue.2026Q2"), H("con.pipeline_target"), H("con.pipeline")], "business/cafe"),
        (["how are the kids tracking on their goals?", "kids' goals roundup — Mila, Theo and Ruby"], [H("mila.swim_goal"), H("mila.swim_pb"), H("theo.goal"), sp("theo_coach_note"), H("ruby.goal"), sp("ruby_teacher_note")], "family"),
        (["all the cafe targets — where are we?", "Copperleaf goals review"], [H("cafe.covers_target"), H("cafe.covers"), H("cafe.revenue_goal"), H("cafe.revenue.2026Q2"), H("cafe.waste_target"), H("cafe.waste")], "business/cafe"),
    ]
    for qs, req, pr in owner_goals:
        tb.add(G, qs[0], req, "owner", pr, qs[1:], [partner_of.get(g.by_id[req[0]]["partition"], "owner")])

    # ============================================================ preference_recommendation
    P = "preference_recommendation"
    spec_of = {v: k for k, v in g.meta["coach_spec"].items()}
    for m in members:
        nm = first(mem_eid[m])
        pk = g.entities[mem_eid[m]]["pref_kind"]
        csid = g.meta["coach_spec"][pk]
        q, rest = tb.pick([f"which coach would suit {nm} best?", f"who should we pair {nm} with for PT?", f"best coach match for {nm}?"])
        tb.add(P, q, [sp(f"member_pref:{m}"), sp(f"coach_spec:{csid}")], "partner_gym", "business/gym", rest)
        q, rest = tb.pick(["which classes would suit me?", "what should I book this week?", "any class you'd suggest I try?"])
        tb.add(P, q, [sp(f"member_pref:{m}"), H("gym.timetable"), H(f"{m}.program")], f"member_{m}", "business/gym", rest + [f"which classes would suit {nm}?"], ["partner_gym"])
    for sid in staff:
        nm = first(sid)
        q, rest = tb.pick([f"which shifts should we give {nm}?", f"how should we roster {nm} next month?", f"what hours would {nm} want?"])
        tb.add(P, q, [sp(f"staff_pref:{sid}"), H("cafe.hours")], "partner_cafe", "business/cafe", rest, ["owner"])
    for sid in coach_ids:
        nm = first(sid)
        q, rest = tb.pick([f"which classes should {nm} take on the new timetable?", f"what sessions suit {nm}'s availability?"])
        tb.add(P, q, [sp(f"coach_pref:{sid}"), H("gym.timetable")], "partner_gym", "business/gym", rest, ["owner"])
    for kid in ("p_mila", "p_theo", "p_ruby"):
        nm = g.entities[kid]["name"]
        places = spall(f"place:{kid}")
        q, rest = tb.pick([f"outing {nm} would enjoy?", f"take {nm} somewhere special — where?", f"one-on-one day with {nm}, ideas?"])
        tb.add(P, q, [sp(f"kid_pref:{kid}")] + places + (spall("allergy") if kid == "p_ruby" else []), "owner", "family", rest, ["household"])
        act = {"p_mila": "mila.activity", "p_theo": "theo.activity", "p_ruby": "ruby.activity"}[kid]
        q, rest = tb.pick([f"birthday present ideas for {nm}?", f"what would {nm} love as a gift?", f"what should we sign {nm} up for next term?"])
        tb.add(P, q, [sp(f"kid_pref:{kid}"), H(act)] + (spall("allergy") if kid == "p_ruby" else []), "owner", "family", rest, ["household"])
        for j, pl in enumerate(places):
            tb.add(P, R.choice([f"somewhere {nm} would enjoy this Saturday?", f"quick outing idea for {nm} — just the two of us?"]) + ("" if j == 0 else " (somewhere different this time)"), [sp(f"kid_pref:{kid}"), pl], "owner", "family")
    from .world2 import OCCASIONS
    for occ, _ in OCCASIONS:
        q, rest = tb.pick([f"where should we go for the {occ} dinner?", f"restaurant pick for the {occ}?", f"{occ} — where do we eat?"])
        tb.add(P, q, [sp(f"occasion:{occ}"), sp("priya_food_pref"), sp("allergy")], "owner", "family", rest, ["household"])
    loved = spall("book_loved")
    for bid in loved:
        b = g.by_id[bid]
        bk = g.entities[b["entities"][1]]
        gl = sp(f"genre_like:{bk['genre']}")
        q, rest = tb.pick([f"I want something like {bk['name']}", f"more in the vein of {bk['author']}?", f"what else would I enjoy if I liked {bk['name']}?"])
        tb.add(P, q, [bid, gl], "owner", "reading", rest)
    for gname in g.meta["likes"]:
        tb.add(P, R.choice([f"in the mood for some {gname} — suggestions?", f"recommend a {gname} book I'd like"]), [sp(f"genre_like:{gname}")], "owner", "reading")
    tb.add(P, "what should I read next?", spall("reading_pref_current"), "owner", "reading", ["recommend me a book for the holidays", "need something new to read — ideas?"])
    tb.add(P, "which books would I hate?", spall("genre_dislike:fantasy") + spall("genre_dislike:business"), "owner", "reading", ["genres to avoid for me?"])
    tb.add(P, "what kind of accommodation should we book for the trip?", spall("holiday_pref"), "owner", "family", ["where should we stay on holiday?"], ["household"])
    tb.add(P, "where should we go for date night?", [sp("priya_food_pref"), sp("restaurant_pref"), sp("allergy")], "owner", "family", ["somewhere nice to eat with the family?"], ["household"])

    # ============================================================ cross_domain
    C = "cross_domain"
    from .world2 import COMMIT_DESC
    cross_commits = ["gym_fitout", "cafe_kitchen", "con_ute", "car_replace", "school_fees"]
    for h in holds:
        for c in R.sample(cross_commits, 3):
            a, cd = tb.alias(h), COMMIT_DESC[c]
            q, rest = tb.pick([f"could I sell down {a} to cover {cd}?", f"fund {cd} from {a} rather than cash?", f"cash out {a} for {cd} — sensible given the property plan?", f"{a}, the next house, or {cd} — where should the money go?"])
            tb.add(C, q, [H(f"{h}.value"), sp(f"thesis:{h}"), sp(f"commit:{c}"), sp("inv_decision")], "owner", "finance", rest)
    for p in props:
        for c in R.sample(cross_commits, 2):
            a, cd = tb.alias(p), COMMIT_DESC[c]
            q, rest = tb.pick([f"could I release equity from {a} to cover {cd}?", f"refinance {a} to pay for {cd} — dumb idea?", f"use the growth in {a} for {cd}?"])
            tb.add(C, q, [H(f"{p}.valuation"), H(f"{p}.loan"), H("portfolio.lvr_rule"), sp(f"commit:{c}"), sp(f"refi_email:{p}")], "owner", "finance", rest)
        a = tb.alias(p)
        q, rest = tb.pick([f"PM wants a freshen-up at {a} — could Stonefield do it, and can we afford it?", f"should our building crew handle the work at {a}?", f"use Stonefield for {a}? think through crew, cash and the arm's-length thing"])
        tb.add(C, q, [sp(f"pm_email:{p}"), sp("related_party_policy"), sp("con_capacity"), H("offset.balance"), sp(f"reno_quote:{p}")], "owner", "finance", rest)
    for prid in projects[1:]:
        a = tb.alias(prid)
        q, rest = tb.pick([f"does our own renovation push back {a}?", f"family job versus paying client at {a} — who gets Kira first?", f"is the work on our rental going to hurt {a}?"])
        tb.add(C, q, [sp("con_capacity"), H("proj_owner_reno.status"), H(f"{prid}.status"), H("con.supervisor"), sp("related_party_policy")], "owner", "business/construction", rest)
    from .world2 import DUAL_ROLE
    for sid, b1, b2, _ in DUAL_ROLE:
        nm = first(sid)
        keyreq = {"b_gym": H("gym.staff_count"), "b_cafe": sp("cafe_roster"), "b_con": H("con.active_projects")}
        q, rest = tb.pick([f"{nm}'s splitting time across two businesses — is that working?", f"how stretched is {nm} across both jobs?", f"should {nm} go full-time at one of the businesses?"])
        tb.add(C, q, [sp(f"dual:{sid}"), keyreq[b1], keyreq[b2]] + ([sp(f"staff_pref:{sid}")] if sp(f"staff_pref:{sid}") else []) + ([sp(f"coach_pref:{sid}")] if sp(f"coach_pref:{sid}") else []), "owner", None, rest)
    for sup, ks in (("sup_talbot", [H("gym.towel_supplier"), H("cafe.linen_supplier")]), ("sup_brightwater", [H("con.plumbing_sub")]), ("sup_sparkline", [H("gym.cleaner"), H("cafe.cleaning_supplier")]), ("sup_northcrest", [H("gym.insurer"), H("con.insurance")])):
        nm = g.entities[sup]["aliases"][1]
        bs = [b for b in ("b_gym", "b_cafe", "b_con") if sp(f"supfb:{sup}:{b}")]
        q, rest = tb.pick([f"how's {nm} performing across the businesses?", f"{nm} — good or bad across all our jobs?", f"do we have a {nm} problem anywhere?"])
        tb.add(C, q, [sp(f"supfb:{sup}:{b}") for b in bs] + ks, "owner", None, rest)
    for kid, act in (("p_mila", "mila.activity"), ("p_theo", "theo.activity"), ("p_ruby", "ruby.activity")):
        nm = g.entities[kid]["name"]
        q, rest = tb.pick([f"can I do {nm}'s sport runs and still train enough?", f"juggle {nm}'s schedule with my sessions — how?", f"who covers {nm}'s activities if I move training to evenings?"])
        tb.add(C, q, [H(act), sp(f"kid_pref:{kid}"), sp("training_clash"), H("train.sessions")], "owner", "family", rest)
    for c in cross_commits:
        cd = COMMIT_DESC[c]
        q, rest = tb.pick([f"can we do both {cd} and the September holiday?", f"{cd} and the family trip — can we afford both?", f"holiday versus {cd}: which gives?"])
        tb.add(C, q, [sp(f"commit:{c}"), H("family.holiday_budget"), H("offset.balance"), H("family.school_break")], "owner", "finance", rest)
        q, rest = tb.pick([f"does {cd} delay the next property purchase?", f"{cd} versus buying again — which comes first?"])
        tb.add(C, q, [sp(f"commit:{c}"), sp("inv_decision"), H("offset.balance"), H("offset.savings_goal")], "owner", "finance", rest)
    for c1, c2 in [(a, b) for i, a in enumerate(cross_commits) for b in cross_commits[i + 1:]]:
        tb.add(C, R.choice([f"{COMMIT_DESC[c1]} and {COMMIT_DESC[c2]} in the same year — can we swing it?", f"cash plan for {COMMIT_DESC[c1]} plus {COMMIT_DESC[c2]}?"]),
               [sp(f"commit:{c1}"), sp(f"commit:{c2}"), H("offset.balance"), H("offset.savings_goal")], "owner", "finance")
    for qs, req, pr in (
        (["I keep missing morning sessions — how do I fit training around everything?", "how do I keep the program going with the new cafe hours?"], [sp("training_clash"), H("cafe.hours"), H("train.sessions"), H("gym.timetable"), H("train.program")], "health"),
        (["the townhouse reno — what does it mean for the tenant, the building crew and our cash?", "think through our rental reno end to end"], [H(f"{hal}.rent"), H(f"{hal}.lease_end"), sp("reno_quote_owner"), H("proj_owner_reno.status"), sp("related_party_policy"), sp("con_capacity")], "finance"),
        (["can we get away as a family in the September holidays given work?", "September — what's on across work and family before I book a holiday?"], [H("family.school_break"), H("family.holiday_budget"), sp("con_capacity"), sp("commit:gym_fitout"), H("mila.swim_goal")], "family"),
        (["Priya's talking about pausing the gym — what's the full picture?", "should Priya freeze her IronBark membership?"], [sp("priya_gym_pause"), sp("priya_member_note"), H("m03.plan"), H("household.budget")], "family"),
        (["is Ben doing too much — coaching me and running the coaching team?", "can Ben keep coaching me now he's head coach?"], [H("train.coach"), H("gym.head_coach"), sp("coach_advice"), sp("gym_hire_decision")], "health"),
        (["could I pull money out of the cafe toward the next deposit?", "is cafe cash an option for the property deposit?"], [H("cafe.cash_reserve"), H("cafe.distribution_rule"), H("offset.balance"), sp("inv_decision"), H("portfolio.borrowing_capacity")], "finance"),
        (["how do I fit training around the kids' sport?", "kids' activities versus my training — where's the gap in the week?"], [H("mila.activity"), H("theo.activity"), H("ruby.activity"), H("train.sessions"), sp("training_clash")], "family"),
        (["the cafe's earlier opening — how's it affecting staff, sales and me?", "review the cafe hours change against everything it touched"], [H("cafe.hours"), H("cafe.covers"), sp("cafe_roster"), sp("training_clash")], "business/cafe"),
        (["Stonefield's numbers this quarter — do they change my investing plans?", "if the building business slows, can we still buy again?"], [H("con.revenue.2026Q2"), H("con.pipeline"), sp("inv_decision"), H("portfolio.borrowing_capacity")], "finance"),
        (["can the household budget lean on cafe profits?", "cafe takings versus what the house needs each month?"], [H("cafe.revenue.2026Q2"), H("cafe.cash_reserve"), H("household.budget"), H("cafe.distribution_rule")], "business/cafe"),
        (["books to pack for the September holiday?", "holiday reading list for the spring break trip"], spall("reading_pref_current") + [H("family.school_break")], "reading"),
        (["should I train at the 6am class or will I take a paying member's spot?", "my training slot versus member capacity at the gym?"], [sp("gym_capacity"), H("gym.timetable"), sp("training_clash"), H("train.sessions")], "health"),
        (["will the September trip mess up Mila's qualifying prep and my own training block?", "holiday timing versus Mila's swim goal and my program?"], [H("mila.swim_goal"), H("family.school_break"), sp("mila_coach_note"), H("train.program")], "family"),
        (["is the gym making enough to justify my fit-out contribution?", "should the gym fund the fit-out itself rather than me topping it up?"], [H("gym.revenue.2026Q2"), sp("commit:gym_fitout"), H("offset.balance")], "business/gym"),
    ):
        tb.add(C, qs[0], req, "owner", pr, qs[1:])

    # ============================================================ multimodal
    MM = "multimodal"
    for prid in projects:
        nm = tb.alias(prid)
        pair = [sp(f"mm_defect:{prid}:0"), sp(f"mm_defect:{prid}:1")]
        q, rest = tb.pick([f"pull up the defect photos from {nm}", f"show me the pics of problems on {nm}", f"photos of what's wrong at {nm}?", f"defect pics for the {nm} handover"])
        tb.add(MM, q, pair, "owner", None, rest, ["partner_construction"])
        for j in (0, 1):
            it = g.by_id[pair[j]]
            tb.add(MM, R.choice([f"the photo of the {it['media']['caption'].split(': ')[-1]} at {nm}", f"find the {it['media']['caption'].split(': ')[-1]} photo — {nm}"]), [it["id"]], R.choice(["owner", "partner_construction"]))
        st = g.special[f"mm_progress_stage:{prid}"][0]
        tb.add(MM, R.choice([f"Kira's {st} photo from {nm}", f"pic from the {st} at {nm}", f"show me the {nm} {st} shot"]), [sp(f"mm_progress:{prid}")], R.choice(["owner", "partner_construction"]))
    for lift in ("squat", "bench", "deadlift", "press"):
        q, rest = tb.pick([f"Ben's videos of my {lift}", f"find the clips where my {lift} technique got checked", f"{lift} form videos?", f"technique footage of my {lift}"])
        tb.add(MM, q, [sp(f"mm_form:{lift}:0"), sp(f"mm_form:{lift}:1")], "owner", None, rest)
        tb.add(MM, R.choice([f"the most recent {lift} form check Ben sent", f"Ben's {lift} clip with the coaching notes"]), [sp(f"mm_form:{lift}:1")], "owner")
    for i, topic in enumerate(["membership pricing tiers", "summer timetable", "recovery room layout", "member challenge leaderboard", "coach roster", "marketing plan"]):
        q, rest = tb.pick([f"the whiteboard pic from the partners meeting about the {topic}", f"photo of what we drew up for the {topic}", f"find the {topic} whiteboard", f"image of the {topic} we sketched"])
        tb.add(MM, q, [sp(f"mm_whiteboard:{i}")], "owner", None, rest, ["partner_gym"])
    for p in props:
        nm = tb.alias(p)
        q, rest = tb.pick([f"valuation report for {nm}", f"the valuer's PDF on {nm}", f"the latest valuation document for {nm}"])
        tb.add(MM, q, [sp(f"mm_valreport:{p}")], "owner", None, rest)
        pair = [sp(f"mm_listing:{p}:0"), sp(f"mm_listing:{p}:1")]
        q, rest = tb.pick([f"listing photos of {nm}", f"pics the PM took of {nm}", f"all the advertising shots for {nm}"])
        tb.add(MM, q, pair, "owner", None, rest)
        for j in (0, 1):
            room = g.special[f"mm_listing_room:{p}:{j}"][0]
            tb.add(MM, R.choice([f"photo of the {room} at {tb.alias(p)}", f"the {room} shot from {tb.alias(p)}'s listing"]), [pair[j]], "owner")
    for kid in ("p_ruby", "p_mila", "p_theo"):
        nm = g.entities[kid]["name"]
        for j in (0, 1):
            ev = g.special[f"mm_family_ev:{kid}:{j}"][0]
            q, rest = tb.pick([f"photos from {nm}'s {ev}", f"pics of {nm} at the {ev}", f"{nm} {ev} photos for grandma", f"{nm}'s {ev} album"])
            tb.add(MM, q, spall(f"mm_family:{kid}:{j}"), "owner", None, rest, ["household"])
    for b, what in (("b_cafe", "grinder repair"), ("b_gym", "cable machine service"), ("b_con", "laser level hire")):
        nm = g.entities[b]["aliases"][1]
        pair = [sp(f"mm_receipt:{b}:0"), sp(f"mm_receipt:{b}:1")]
        tb.add(MM, R.choice([f"receipts for {nm} this year", f"scanned receipts from {nm}"]), pair, "owner", None, [f"show the {nm} receipt scans"], [partner_of[g.by_id[pair[0]]["partition"]]])
        tb.add(MM, f"find the {nm} receipt for the {what}", [pair[0]], "owner")
        tb.add(MM, R.choice([f"the other {nm} receipt, not the {what} one", f"{nm} receipt photo from this year (the second one)"]), [pair[1]], "owner")
    for i, board in enumerate(["breakfast menu", "lunch specials", "drinks and pricing", "kids menu"]):
        q, rest = tb.pick([f"photo of the cafe's {board} board", f"what did the {board} chalkboard say?", f"find the {board} pic Tomas posted", f"the {board} photo from the team chat"])
        tb.add(MM, q, [sp(f"mm_menu:{i}")], "owner", None, rest, ["partner_cafe"])

    # ============================================================ trails (I12 fields, as in v0)
    by_group_part = {}
    for it in g.items:
        sgp = scope_group(it["scope"])
        if sgp:
            by_group_part.setdefault((sgp, it["partition"]), []).append(it["id"])
    trng = random.Random(4242 + seed)
    for t in tb.out:
        parts = tb.ident[t["requester"]]["partitions"]
        groups_allowed = sorted({gg for (gg, pp) in by_group_part if pp in parts})
        tr = []
        for _ in range(6):
            grp = t["declared_scope"] if trng.random() < 0.7 else trng.choice(t["required_scope_groups"])
            pool = [i for pp in parts for i in by_group_part.get((grp, pp), [])]
            tr.append(trng.choice(pool) if pool else None)
        t["trail_on_task"] = [x for x in tr if x]
        t["trail_noise_draws"] = [trng.random() for _ in range(6)]
        t["trail_noise_items"] = []
        for _ in range(6):
            grp = trng.choice(groups_allowed)
            pool = [i for pp in parts for i in by_group_part.get((grp, pp), [])]
            t["trail_noise_items"].append(trng.choice(pool))
    # cross_domain must span >=2 scope groups
    tb.out = [t for t in tb.out if t["cls"] != "cross_domain" or len(t["required_scope_groups"]) >= 2]
    for i, t in enumerate(tb.out):
        t["id"] = f"t{i+1:05d}"
    g.tasks = tb.out
    return tb.out
