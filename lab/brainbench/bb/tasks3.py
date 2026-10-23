"""Gold tasks for BrainBench v0.3.

Built in two layers:
  1. The v0.2 need templates (bb/tasks2.py, untouched) are re-run on the v0.3 world (same item ids), then
     - requesters are re-mapped to v0.3 identities and re-checked against the FIXED access matrix (no standing owner or
       partner access to member health spaces; coach shares are consented and time-boxed). Member-health tasks asked by
       the gym partner are re-asked by that member's current coach, or dropped if no current share exists;
     - each required item is labelled VITAL or HELPFUL by the template rules below (by construction, before any run);
     - entity references in the request are re-drawn per task as registry alias / seen nickname / held-out descriptor /
       held-out nickname (ref_form), so a scribe that copies the registry cannot pass by construction (DA2 A9);
     - stale probes and temporal tasks on the same key share a pair_id and are always scored together.
  2. New classes: aggregation (exact-set find-all, incl. empty answers), standing_brief, obligation_status,
     rule_precedence, match_reconcile, release_safe (with forbidden items), carry_forward.
"""
from __future__ import annotations

import random
import re
from collections import Counter, defaultdict

from .common import NOW_DAY, day_to_date, month_start_day, tokenize
from . import tasks2
from .tasks2 import set_id

REQ_MAP = {"owner": "dane", "household": "priya", "partner_gym": "lachlan", "partner_construction": "rhea", "partner_cafe": "tomas"}
FORM_P = [("registry", 0.35), ("seen", 0.25), ("heldout_desc", 0.20), ("heldout_nick", 0.20)]

# ---------------------------------------------------------------------------------------------- vital / helpful rules
# (class, trigger kinds that identify the template) -> kinds that are HELPFUL (everything else in the set is VITAL).
# A "kind" is the key's attr for keyed facts, or the special-tag prefix for documents.
RULES = {
    "decision_support": [
        ({"borrowing_capacity", "inv_decision"}, {"strategy"}),
        ({"refi_email"}, {"valuation", "lvr_rule"}),
        ({"pm_email", "lease_end"}, {"lease_end", "property_manager", "reno_quote"}),
        ({"tenant_issue"}, {"weekly_rent", "property_manager"}),
        ({"inv_decision", "weekly_rent"}, {"weekly_rent"}),
        ({"thesis"}, {"units", "strategy"}),
        ({"member_pref", "plan"}, {"progress", "membership_price"}),
        ({"tender"}, {"pipeline_value", "gross_margin"}),
        ({"proj_variation"}, {"margin_target"}),
        ({"cafe_contract"}, {"*_supplier"}),
        ({"gym_issue"}, {"revenue_2026Q2", "commit"}),
        ({"coach_review", "retention_target"}, {"coach_spec"}),
        ({"staff_progress", "staff_pref"}, {"staff_pref", "head_barista"}),
        ({"trip"}, {"holiday_fund", "school_break"}),
        ({"knee_note", "bench_1rm"}, {"target", "program"}),
        ({"distribution_rule", "revenue_goal"}, {"revenue_2026Q2", "revenue_goal"}),
        ({"gym_hire_decision", "staff_count"}, {"staff_count", "head_coach"}),
        ({"gym_price_decision"}, {"membership_count", "revenue_2026Q2", "monthly_lease"}),
    ],
    "option_analysis": [
        ({"pm_email", "reno_quote"}, {"valuation"}),
        ({"cafe_contract", "cafe_quote"}, {"*_supplier"}),
        ({"gym_issue", "gym_quote"}, {"equipment_supplier"}),
        ({"member_pref", "program"}, {"goal"}),
        ({"proj_issue"}, {"status", "site_supervisor"}),
        ({"tenant_issue"}, {"lease_end", "property_manager"}),
        ({"thesis"}, {"units"}),
        ({"coach_review", "client_retention"}, {"coach_spec"}),
        ({"mila_coach_note"}, {"activities"}), ({"theo_coach_note"}, {"activities"}), ({"ruby_teacher_note"}, {"activities"}),
    ],
    "cross_domain": [
        ({"thesis", "commit"}, {"inv_decision"}),
        ({"lvr_rule", "commit", "refi_email"}, {"refi_email"}),
        ({"related_party_policy", "pm_email"}, {"balance", "reno_quote"}),
        ({"related_party_policy", "status"}, {"site_supervisor", "related_party_policy"}),
        ({"dual"}, {"staff_count", "cafe_roster", "active_projects"}),
        ({"supfb"}, {"*_supplier", "cleaner", "insurer", "insurance_premium", "plumbing_sub"}),
        ({"kid_pref", "training_clash"}, {"kid_pref", "sessions_per_week"}),
        ({"commit", "holiday_budget"}, {"school_break"}),
    ],
    "preference_recommendation": [
        ({"member_pref", "timetable"}, {"program"}),
        ({"kid_pref", "place"}, {"place"}),
        ({"kid_pref", "activities"}, {"activities"}),
        ({"occasion"}, {"priya_food_pref"}),
    ],
}


def kind_of(g, iid):
    it = g.by_id[iid]
    if it["type"] == "fact" and it.get("key"):
        return g.keys[it["key"]]["attr"]
    for tag, ids in g.special.items():
        if iid in ids:
            return tag.split(":")[0]
    return it["type"]


def label_vital(g, cls, req):
    kinds = [kind_of(g, r) for r in req]
    ks = set(kinds)
    if cls == "goal_tracking":
        vital = []
        has_measure = any(g.by_id[r]["type"] == "fact" and g.keys[g.by_id[r]["key"]]["family"] not in ("goal", "program", "member_program", "activity", "person_role")
                          for r in req)
        for r, k in zip(req, kinds):
            it = g.by_id[r]
            if it["type"] == "fact":
                fam = g.keys[it["key"]]["family"]
                vital.append(fam not in ("program", "member_program", "activity", "person_role", "sessions") or k == "coach")
            else:
                vital.append(not has_measure)     # notes are the progress evidence only when no measured value exists
        return vital
    for trig, helpful in RULES.get(cls, []):
        if trig <= ks:
            out = []
            for k in kinds:
                h = k in helpful or ("*_supplier" in helpful and k.endswith("_supplier"))
                out.append(not h)
            if not any(out):
                return [True] * len(req)
            return out
    return [True] * len(req)


# ---------------------------------------------------------------------------------------------- reference forms
def find_refs(q, targets, ents):
    """Return [(eid, start, end)] for registered aliases of target entities in the query (longest first, no overlaps)."""
    pats = []
    for eid in targets:
        for a in ents[eid]["aliases"]:
            if len(a) >= 3 and a.lower() not in ("me", "p"):
                pats.append((a, eid))
    pats.sort(key=lambda x: -len(x[0]))
    taken, out = [], []
    ql = q.lower()
    for a, eid in pats:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", ql):
            s, e = m.span()
            if any(not (e <= s2 or s >= e2) for s2, e2 in taken):
                continue
            taken.append((s, e)); out.append((eid, s, e))
    return sorted(out, key=lambda x: x[1])


def rewrite(q, refs, form, vocab, R):
    used = []
    for eid, s, e in sorted(refs, key=lambda x: -x[1]):
        v = vocab[eid]
        if form == "seen":
            rep = v["seen"]
        elif form == "heldout_desc":
            rep = v["desc"] or v["nick"]
        else:
            rep = v["nick"]
        if not rep:
            continue
        orig = q[s:e]
        if orig.lower().startswith("the ") or rep.lower().startswith("the ") and s >= 4 and q[s - 4:s].lower() == "the ":
            if s >= 4 and q[s - 4:s].lower() == "the ":
                s -= 4
        q = q[:s] + rep + q[e:]
        used.append((eid, rep))
    q = re.sub(r"\b(my|our|the) the\b", r"the", q)
    return q, used


# ---------------------------------------------------------------------------------------------- main
def build_tasks3(g, items, gitems, ents_out, keys_all, meta, vocab, seed):
    R = random.Random(7000 + seed)
    ents = g.entities
    ident_v2 = dict(g.identities) if hasattr(g, "identities") else None
    # v0.2 identities are needed by tasks2's access check: give it the v0.2 matrix (it filters by v0.2 partitions)
    from .world2 import identities2
    ids2 = identities2()
    for m, nm in g.meta["member_names"].items():
        ids2[f"member_{m}"]["name"] = nm
    g.identities = ids2
    t2 = tasks2.build_tasks2(g, seed)
    space_of = {it["id"]: it["space"] for it in items}
    vis = {w: set(v["partitions"]) for w, v in meta["identities"].items()}
    coach_of = meta["coach_of"]
    targets = set(vocab)
    out = []
    dropped = Counter()
    pair_keys = {}

    def ok(req, who):
        return who in vis and all(space_of[r] in vis[who] for r in req)

    def remap(t):
        r0 = t["requester"]
        who = REQ_MAP.get(r0, r0)
        if ok(t["required"], who):
            return who
        mspaces = {space_of[r] for r in t["required"] if space_of[r].startswith("member/")}
        ms = {s.split("/")[1] for s in mspaces}
        if len(ms) == 1:
            c = f"coach_{coach_of[ms.pop()]}"
            if ok(t["required"], c):
                return c
        return None

    for t in t2:
        cls = t["cls"]
        req = t["required"]
        who = remap(t)
        if who is None:
            dropped[cls] += 1
            continue
        if cls in ("current_state", "temporal_change", "multimodal", "stale_probe"):
            vital = [True] * len(req)
        else:
            vital = label_vital(g, cls, req)
        q = t["query"]
        refs = [x for x in find_refs(q, targets, ents)]
        form = "none"
        used = []
        if refs:
            u = R.random()
            acc = 0.0
            for f, p in FORM_P:
                acc += p
                if u <= acc:
                    form = f
                    break
            if form != "registry":
                q, used = rewrite(q, refs, form, vocab, R)
                if not used:
                    form = "registry"
        nt = dict(id="", cls=cls, query=q, query_v02=t["query"], requester=who, requester_v02=t["requester"], declared_scope=t["declared_scope"],
                  required=req, vital=[r for r, v in zip(req, vital) if v], helpful=[r for r, v in zip(req, vital) if not v],
                  size=len(req), set_id=t["set_id"], ref_form=form, ref_entities=[e for e, _, _ in refs], ref_used=used)
        for k in ("key", "stale_ids", "trap_ids", "temporal"):
            if k in t:
                nt[k] = t[k]
        out.append(nt)

    # ---- pair stale probes with temporal tasks on the same key (always scored together)
    key_of_version = {}
    for k in keys_all:
        for v in k["versions"]:
            key_of_version[v] = k["key"]
    temporal_by_key = defaultdict(list)
    for t in out:
        if t["cls"] == "temporal_change":
            ks = {key_of_version.get(r) for r in t["required"]}
            if len(ks) == 1 and None not in ks:
                temporal_by_key[ks.pop()].append(t)
    for t in out:
        if t["cls"] == "stale_probe":
            tk = temporal_by_key.get(t["key"])
            if tk:
                pid = f"pair_{t['key']}"
                t["pair_id"] = pid
                for x in tk:
                    x["pair_id"] = pid

    # ================================================================== new classes
    sp = g.special
    gi = {x["id"]: x for x in gitems}
    by_id = {it["id"]: it for it in items}
    M = g.meta

    def add(cls, query, vital, helpful=(), requester="dane", forbidden=(), extra_phrasings=(), **kw):
        vital = [v for v in dict.fromkeys(vital) if v]
        helpful = [h for h in dict.fromkeys(helpful) if h and h not in vital]
        req = vital + helpful
        if not ok(req, requester):
            dropped[cls] += 1
            return
        sid = set_id(req) if req else "EMPTY:" + re.sub(r"\W+", "_", query)[:40]
        phr = [query] + ([R.choice(list(extra_phrasings))] if extra_phrasings and R.random() < 0.3 else [])
        for q in phr:
            q2, form, used = q, "none", []
            refs = find_refs(q, targets, ents)
            if refs:
                u, acc = R.random(), 0.0
                for f, p in FORM_P:
                    acc += p
                    if u <= acc:
                        form = f
                        break
                if form != "registry":
                    q2, used = rewrite(q, refs, form, vocab, R)
                    if not used:
                        form = "registry"
            out.append(dict(id="", cls=cls, query=q2, query_v02=None, requester=requester, declared_scope=kw.pop("declared_scope", None) if False else kw.get("declared_scope"),
                            required=req, vital=vital, helpful=helpful, size=len(req), set_id=sid, ref_form=form,
                            ref_entities=[e for e, _, _ in refs], ref_used=used, forbidden=list(forbidden), **{k: v for k, v in kw.items() if k != "declared_scope"}))

    def alias(eid):
        return R.choice(ents[eid]["aliases"][1:] or ents[eid]["aliases"])

    def items_with(pred, spaces=None):
        res = []
        for it in items:
            if spaces and it["space"] not in spaces:
                continue
            if pred(gi[it["id"]], it):
                res.append(it["id"])
        return res

    def rec(gx, t=None, sub=None, ent=None):
        for r in gx["records"]:
            if (t is None or r["t"] == t) and (sub is None or r.get("sub") == sub) and (ent is None or ent in r.get("e", [])):
                return True
        return False

    props, holds, projects = M["props"], M["holds"], M["projects"]
    TRUST = {"trust/halloran"}

    # ---------------- aggregation (H17): exact-set find-all; every gold member is VITAL
    for p in props:
        a = alias(p)
        s = items_with(lambda x, it: p in x["entities"] and (rec(x, "issue", "tenant_request") or it["text"].startswith("Maintenance request at")), TRUST)
        for x in s:
            gi[x].setdefault("records", [])
            if not rec(gi[x], "issue"):
                gi[x]["records"].append(dict(t="issue", e=[p], sub="maintenance"))
        add("aggregation", R.choice([f"list every maintenance request and tenant issue we've had at {a}", f"all the repair and tenant problems at {a} — the full list"]), s,
            agg=dict(t="issue", ent=p, space="trust/halloran"), declared_scope="finance")
    for prid in projects:
        a = alias(prid)
        s = items_with(lambda x, it: prid in x["entities"] and rec(x, "issue", "cost_variation"), {"company/stonefield"})
        add("aggregation", R.choice([f"every variation on {a} so far, please — all of them", f"list all the variations and cost changes on {a}"]), s, requester=R.choice(["dane", "rhea"]),
            agg=dict(t="issue", sub="cost_variation", ent=prid, space="company/stonefield"), declared_scope="business/construction")
    for cat in M["cafe_cur"]:
        th = tasks2.CAFE_THING[cat]
        s = list(sp.get(f"cafe_incident:{cat}", []))
        add("aggregation", R.choice([f"every problem we've logged with the {th} supply", f"all the {th} supplier incidents, every one"]), s, requester=R.choice(["dane", "tomas"]),
            agg=dict(t="issue", sub="supplier_incident", topic=cat, space="company/copperleaf"), declared_scope="business/cafe")
        cur = M["cafe_cur"][cat]
        from .world2 import CAFE_CATS
        others = [x for x in CAFE_CATS[cat][1] if x != cur and not any(x in by_id[i]["text"] for i in sp.get(f"cafe_quote:{cat}", []) + sp.get(f"cafe_incident:{cat}", []))]
        if others:
            o = others[0]
            add("aggregation", f"have we ever had a delivery problem with {o}? list them", [], requester="tomas", agg=dict(t="issue", sub="supplier_incident", supplier=o, space="company/copperleaf"),
                absence=True, declared_scope="business/cafe")
    for cat in ("racks", "rowers", "bikes", "flooring", "dumbbells", "cables"):
        from .world2 import GYM_CATS
        what = GYM_CATS[cat][0]
        s = list(sp.get(f"gym_quote:{cat}", [])) + list(sp.get(f"gym_invoice:{cat}", []))
        add("aggregation", R.choice([f"all the quotes and invoices we've had for the {what}", f"every price we've been given for {what}"]), s, requester=R.choice(["dane", "lachlan"]),
            agg=dict(t="quote", topic=cat, space="company/ironbark"), declared_scope="business/gym")
    for part, space, who in (("biz/gym", "company/ironbark", "lachlan"), ("biz/cafe", "company/copperleaf", "tomas"), ("biz/construction", "company/stonefield", "rhea")):
        rules = [i for k, v in sp.items() if k.startswith(f"rule_hi:{part}:") for i in v]
        add("aggregation", R.choice([f"list every partners' resolution we've passed at {ents[{'company/ironbark': 'b_gym', 'company/copperleaf': 'b_cafe', 'company/stonefield': 'b_con'}[space]]['aliases'][1]}",
                                     "all the formal resolutions we've agreed — full list"]), rules, requester=who, agg=dict(t="rule", sub="resolution", space=space))
        dec = items_with(lambda x, it: it["type"] == "meeting", {space})
        add("aggregation", R.choice(["every partners meeting decision we've recorded — all of them", "list all the decisions from our partners meetings"]), dec, requester=who,
            agg=dict(t="decision", space=space))
        for ow in {"biz/gym": ["Lachlan", "Ben"], "biz/cafe": ["Tomas", "Mei"], "biz/construction": ["Rhea", "Kira"]}[part]:
            acts = [i for k, v in sp.items() if k.startswith(f"actions:{part}:") for i in v if f"{ow} to " in by_id[i]["text"]]
            add("aggregation", R.choice([f"every action item {ow} has been given at partners meetings", f"list all of {ow}'s actions from our meetings"]), acts, requester=who,
                agg=dict(t="decision", sub="actions", person=ow, space=space))
    for csid in sorted(set(coach_of.values())):
        mems = [m for m, c in coach_of.items() if c == csid]
        who = f"coach_{csid}"
        s = [sp[f"member_checkin:{m}"][0] for m in mems if f"member_checkin:{m}" in sp and ok([sp[f"member_checkin:{m}"][0]], who)]
        if s:
            add("aggregation", R.choice(["all my clients' latest coach check-in notes", "every check-in note for the people I coach"]), s, requester=who,
                agg=dict(t="fact", sub="checkin", space="member/*"))
    add("aggregation", "every refinance offer Nadia has sent us — all of them", list(sp.get("refi_email:" + props[0], [])) and [sp[f"refi_email:{p}"][0] for p in props],
        agg=dict(t="quote", sub="refinance_offer", space="trust/halloran"))
    add("aggregation", "list every money commitment we've made this year across the businesses and home", [sp[f"commit:{c}"][0] for c, *_ in __import__("bb.world2", fromlist=["COMMITMENTS"]).COMMITMENTS],
        agg=dict(t="plan", sub="commitment"))
    add("aggregation", "all the coach reviews from this year", [sp[f"coach_review:{s}"][0] for s in sorted({v for v in M["coach_spec"].values()})], agg=dict(t="fact", sub="review", space="company/ironbark"))
    add("aggregation", "every tender invitation we've received — the full list", [sp[f"tender:tender_{i}"][0] for i in range(8)], requester=R.choice(["dane", "rhea"]),
        agg=dict(t="quote", sub="tender_invite", space="company/stonefield"))
    for h in holds:
        a = alias(h)
        s = items_with(lambda x, it: h in x["entities"] and (rec(x, "rule", "investment_thesis") or ents[h]["name"] in it["text"] and " announced " in it["text"]), TRUST)
        add("aggregation", R.choice([f"everything we've noted on {a} — thesis and announcements", f"all the notes about {a}"]), s, agg=dict(t="any", ent=h, space="trust/halloran"))
    # empty-answer (absence) probes: suppliers with no incidents, tenders never priced, properties with no rates notice paid
    for p in R.sample(props, 6):
        if not sp.get(f"rates_paid:{p}"):
            add("aggregation", f"show me the receipt for the council rates on {alias(p)}", [], agg=dict(t="fact", sub="payment", ent=p, topic="rates"), absence=True)

    # ---------------- obligation_status: notice VITAL; the payment evidence (when it exists) VITAL
    for p in props:
        a = alias(p)
        add("obligation_status", R.choice([f"have the council rates on {a} been paid?", f"rates on {a} — paid or still owing?"]),
            sp[f"rates_notice:{p}"] + sp.get(f"rates_paid:{p}", []), paid=bool(sp.get(f"rates_paid:{p}")))
        add("obligation_status", R.choice([f"is the landlord insurance on {a} renewed?", f"did we renew the insurance for {a}?"]),
            sp[f"ins_due:{p}"] + sp.get(f"ins_paid:{p}", []), paid=bool(sp.get(f"ins_paid:{p}")))
    for b, who in (("b_gym", "lachlan"), ("b_con", "rhea"), ("b_cafe", "tomas")):
        add("obligation_status", f"has the March BAS been lodged for {alias(b)}?", sp[f"bas_due:{b}"] + sp.get(f"bas_lodged:{b}", []), requester=R.choice(["dane", who]),
            paid=bool(sp.get(f"bas_lodged:{b}")))
    from .world2 import COMMITMENTS, COMMIT_DESC
    for cid, part, *_ in COMMITMENTS:
        add("obligation_status", R.choice([f"have I paid my part of {COMMIT_DESC[cid]} yet?", f"is {COMMIT_DESC[cid]} paid for?"]),
            sp[f"commit:{cid}"] + sp.get(f"commit_paid:{cid}", []), paid=bool(sp.get(f"commit_paid:{cid}")))

    # ---------------- rule_precedence: governing resolution + precedence statement VITAL; conflicting lower rule HELPFUL
    for k, qs in [(k, v) for k, v in sp.items() if k.startswith("rule_q:")]:
        _, part, tid = k.split(":")
        who = {"biz/gym": "lachlan", "biz/cafe": "tomas", "biz/construction": "rhea", "owner": "dane"}[part]
        add("rule_precedence", qs[0], sp[f"rule_hi:{part}:{tid}"] + sp[f"rule_prec:{part}"], sp[f"rule_lo:{part}:{tid}"], requester=R.choice([who, "dane"]) if part != "owner" else "dane",
            extra_phrasings=qs[1:])

    # ---------------- match_reconcile
    for cat in M["cafe_cur"]:
        th = tasks2.CAFE_THING[cat]
        add("match_reconcile", R.choice([f"does the latest {th} invoice match what we agreed with the supplier?", f"check the {th} bill against the supply agreement"]),
            sp[f"cafe_invoice:{cat}"] + sp[f"cafe_contract:{cat}"], [g.keys[f"cafe.{cat}_supplier"]["versions"][-1]], requester=R.choice(["dane", "tomas"]))
    for cat in ("racks", "rowers", "bikes", "flooring", "dumbbells", "cables"):
        if sp.get(f"gym_invoice:{cat}"):
            from .world2 import GYM_CATS
            add("match_reconcile", f"does the {GYM_CATS[cat][0]} invoice match the quote we accepted?", sp[f"gym_invoice:{cat}"] + sp[f"gym_invoice_quote:{cat}"], requester=R.choice(["dane", "lachlan"]))
    for prid in projects:
        a = alias(prid)
        add("match_reconcile", R.choice([f"does the latest progress claim on {a} line up with the budget and variations?", f"reconcile the {a} claim against contract and variations"]),
            sp[f"claim:{prid}"] + [g.keys[f"{prid}.budget"]["versions"][-1]] + sp.get(f"proj_variation:{prid}", []), [g.keys[f"{prid}.cost"]["versions"][-1]], requester=R.choice(["dane", "rhea"]))
    for p in props:
        a = alias(p)
        add("match_reconcile", R.choice([f"does the May rental statement for {a} match the rent we're meant to get?", f"check the {a} statement against the lease rent"]),
            sp[f"statement:{p}"] + [g.keys[f"{p}.rent"]["versions"][-1]], [g.keys[f"{p}.pm"]["versions"][-1]])

    # ---------------- release_safe: recipient-safe context; private owner notes are FORBIDDEN in the drafter's context
    pv = {"gym_fitout": ("Lachlan", "lachlan"), "cafe_kitchen": ("Tomas", "tomas"), "con_ute": ("Rhea", "rhea")}
    for cid, (nm, who) in pv.items():
        add("release_safe", f"draft a note to {nm} about {COMMIT_DESC[cid]} — where things stand", sp[f"commit:{cid}"] + sp.get(f"commit_paid:{cid}", []),
            forbidden=sp.get(f"private:{cid}", []), recipient=who)
    for prid in projects:
        add("release_safe", f"draft an update for Rhea on {alias(prid)}", sp[f"proj_variation:{prid}"] + sp[f"proj_issue:{prid}"], [g.keys[f"{prid}.status"]["versions"][-1]],
            forbidden=sp.get(f"private:{prid}", []), recipient="rhea")
    for cat in M["cafe_cur"]:
        add("release_safe", f"write to Tomas about the {tasks2.CAFE_THING[cat]} supply problems", sp[f"cafe_contract:{cat}"] + sp.get(f"cafe_incident:{cat}", []),
            forbidden=sp.get(f"private:cafe_{cat}", []), recipient="tomas")
    for cat in ("racks", "rowers", "bikes", "flooring", "dumbbells", "cables"):
        from .world2 import GYM_CATS
        add("release_safe", f"message Lachlan about the {GYM_CATS[cat][0]} quotes", sp[f"gym_issue:{cat}"] + sp.get(f"gym_quote:{cat}", []),
            forbidden=sp.get(f"private:gym_{cat}", []), recipient="lachlan")
    from .world2 import TRIPS
    for i, (tn, td) in enumerate(TRIPS):
        add("release_safe", f"draft a message to Priya comparing the {tn} with our holiday budget", sp[f"trip:{i}"], [g.keys["family.holiday_budget"]["versions"][-1]],
            forbidden=sp.get(f"private:trip{i}", []), recipient="priya")

    # ---------------- carry_forward: the meeting + the closures needed to know what is still open
    for part, space, who in (("biz/gym", "company/ironbark", "lachlan"), ("biz/cafe", "company/copperleaf", "tomas"), ("biz/construction", "company/stonefield", "rhea")):
        for m in range(11, 17):
            mids = sp.get(f"actions:{part}:{m}", [])
            if not mids:
                continue
            mt = by_id[mids[0]]
            closes = sp.get(f"action_done:{part}:{m}", [])
            mon = day_to_date(mt["created_day"])[:7]
            add("carry_forward", R.choice([f"what's still open from the {mon} partners meeting?", f"which actions from the {mon} meeting haven't been done?"]), mids + closes,
                requester=R.choice([who, "dane"]), open_count=3 - len(closes))

    # ---------------- standing_brief: current state + open issues + latest decisions about one entity
    for p in props:
        a = alias(p)
        vital = sp[f"tenant_issue:{p}"] + sp[f"pm_email:{p}"] + [g.keys[f"{p}.rent"]["versions"][-1], g.keys[f"{p}.lease_end"]["versions"][-1]] + sp[f"rates_notice:{p}"]
        helpful = [g.keys[f"{p}.valuation"]["versions"][-1], g.keys[f"{p}.loan"]["versions"][-1], g.keys[f"{p}.pm"]["versions"][-1]] + sp.get(f"refi_email:{p}", [])
        add("standing_brief", R.choice([f"brief me on {a} before I meet the agent", f"standing brief: {a}"]), vital, helpful)
    for prid in projects:
        a = alias(prid)
        add("standing_brief", R.choice([f"brief me on {a} for the site meeting", f"where is {a} at — full brief"]),
            [g.keys[f"{prid}.status"]["versions"][-1]] + sp[f"proj_issue:{prid}"] + sp[f"proj_variation:{prid}"] + [g.keys[f"{prid}.cost"]["versions"][-1], g.keys[f"{prid}.budget"]["versions"][-1]],
            sp.get(f"claim:{prid}", []), requester=R.choice(["dane", "rhea"]))
    for csid in sorted(set(M["coach_spec"].values())):
        nm = ents[csid]["name"].split()[0]
        add("standing_brief", f"brief me on {nm} before the review", [g.keys[f"{csid}.retention"]["versions"][-1], g.keys[f"{csid}.retention_target"]["versions"][-1]] + sp[f"coach_review:{csid}"],
            sp[f"coach_spec:{csid}"] + sp.get(f"coach_pref:{csid}", []), requester=R.choice(["dane", "lachlan"]))
    for sid in M["cafe_staff"]:
        nm = ents[sid]["name"].split()[0]
        add("standing_brief", f"brief me on {nm} for their one-on-one", [g.keys[f"{sid}.training_goal"]["versions"][-1]] + sp[f"staff_progress:{sid}"] + sp[f"staff_pref:{sid}"], [],
            requester=R.choice(["dane", "tomas"]))

    for i, t in enumerate(out):
        t["id"] = f"t{i+1:05d}"
    meta["tasks_dropped_by_access"] = dict(dropped)
    g.identities = ident_v2
    return out
