"""ADR checks for batch 3 (no LLM):
  DA1-4  frozen external BM25 statistics (WikiText-2) vs visible-set vs per-partition (and global, leaky reference)
  S2/S3  twin-world noninterference on a reference engine + 10 injected leak classes; canary monitor sensitivity;
         no-grant credential (GBrain GB11 lesson)
  DA1-6  key timelines vs indexed version rows under history growth (+0/+10/+40 versions per connector key)
  DA1-7  values-free stub cards (values compiled at read time) vs stored cards
  EXIT   read-time exit check against a deliberately delayed index (revocation + erasure)
"""
from __future__ import annotations

import copy
import gc
import hashlib
import json
import random
import re
from collections import Counter, defaultdict

import numpy as np

from .common import NOW_DAY, tokenize
from .pipe3 import (EMB, KS, Brain3, Gate, World3, ctx_text, ext_idf_wikitext, minmax, rate, sign_test, topn)
from .brain import is_temporal_query

EVAL = ["decision_support", "option_analysis", "current_state", "temporal_change", "goal_tracking", "preference_recommendation", "cross_domain", "multimodal",
        "aggregation", "standing_brief", "obligation_status", "rule_precedence", "match_reconcile", "release_safe", "carry_forward"]


def _rows(b, tasks, arm, seed, name, maxk=100, maxt=8000):
    out = []
    for t in tasks:
        ctx = b.assemble(t, arm, maxk=maxk, maxt=maxt)
        r = b.score(t, ctx)
        r.update(seed=seed, arm=name)
        out.append(r)
    return out


# ============================================================================ DA1-4
def da1_4(seeds, log, st):
    ext = ext_idf_wikitext()
    for s in seeds:
        w = World3(s)
        tasks = [t for t in w.tasks if t["cls"] in EVAL]
        EMB.prefetch_queries([t["query"] for t in tasks])
        for stats in ("visible", "frozen", "partition", "global"):
            if (s, stats, "bm25") in st:
                continue
            b = Brain3(w, None, stats=stats, ext=ext, alpha=1.0)
            st[(s, stats, "bm25")] = _rows(b, tasks, dict(prefix="none"), s, f"bm25/{stats}")
            b.alpha = 0.2
            st[(s, stats, "hybrid")] = _rows(b, tasks, dict(prefix="none"), s, f"hybrid/{stats}")
            log(f"[da1-4] s{s} {stats}: done")
            b = None; gc.collect()
    oov = []
    w = World3(1)
    for t in w.tasks[:2000]:
        toks = tokenize(t["query"])
        if toks:
            oov.append(np.mean([ext["df"].get(x, 0) == 0 for x in toks]))
    st["oov_share"] = float(np.mean(oov))
    return st


# ============================================================================ S2 / S3: twin-world noninterference
BUGS = ["none", "seed_only_hop", "global_idf", "query_cache", "hidden_snippet", "count_before_filter", "global_tiebreak",
        "stale_revocation_cache", "card_widening", "shared_prefix_cache", "semantic_cache"]


class Engine:
    """A small serving engine over a Brain3 index with one injectable bug. serve() returns every observable a caller can see."""

    def __init__(self, b: Brain3, w, bug="none", grants=None):
        self.b, self.w, self.bug = b, w, bug
        self.grants = grants if grants is not None else w.grants
        self.qcache, self.semcache, self.prefix = {}, [], set()
        self.vis_cache = {}
        # card widening: cards compiled over ALL spaces of an entity, shown wherever the entity is visible
        if bug == "card_widening":
            self.wide = {}
            per = defaultdict(list)
            for k, d in b.store["keys"].items():
                if d["versions"]:
                    per[d["entity"]].append(d["versions"][-1])
            for e, hs in per.items():
                self.wide[e] = "; ".join(f"{h['label']}: {h['v']}" for h in hs)

    def visible(self, who):
        if self.bug == "stale_revocation_cache":
            if who not in self.vis_cache:
                self.vis_cache[who] = self._vis(who)
            return self.vis_cache[who]
        return self._vis(who)

    def _vis(self, who):
        return frozenset(g["space"] for g in self.grants if g["identity"] == who and g["valid_from"] <= NOW_DAY and (g["valid_to"] is None or NOW_DAY < g["valid_to"]))

    def serve(self, who, q):
        b = self.b
        vis = self.visible(who)
        if not vis:
            return dict(ids=(), scores=(), count=0, snippets=(), err="no_grant", latency="miss")
        m = np.array([d["space"] in vis for d in b.docs]) & ~b.is_super
        if self.bug in ("query_cache",) and q in self.qcache:
            ids, sc = self.qcache[q]
            ids2 = tuple(i for i in ids if b.docs[b.ix.pos[i]]["space"] in vis)[:10]
            return dict(ids=ids2, scores=tuple(sc.get(i) for i in ids2), count=len(ids2), snippets=tuple(b.disp[b.ix.pos[i]][:80] for i in ids2), err="", latency="hit")
        if self.bug == "semantic_cache":
            qv = EMB.queries([q])[0]
            for v, ids, sc in self.semcache:
                if float(v @ qv) >= 0.95:
                    ids2 = tuple(i for i in ids if b.docs[b.ix.pos[i]]["space"] in vis)[:10]
                    return dict(ids=ids2, scores=tuple(sc.get(i) for i in ids2), count=len(ids2), snippets=tuple(b.disp[b.ix.pos[i]][:80] for i in ids2), err="", latency="hit")
        stats = "global" if self.bug == "global_idf" else "visible"
        bm = b.ix.bm25(q, m, stats)
        dv = b.E @ EMB.queries([q])[0]
        s = 0.2 * minmax(bm, m) + 0.8 * minmax(dv, m)
        s = np.where(m, s, -np.inf)
        if self.bug == "global_tiebreak":
            # batch-1 style: non-stable argpartition over the FULL array (hidden rows included), quantised scores create ties
            sq = np.where(m, np.round(s, 2), -np.inf)
            n = 60
            idx = np.argpartition(-sq, n)[:n]
            idx = idx[np.argsort(-sq[idx], kind="quicksort")]
            ranked = [int(i) for i in idx if np.isfinite(sq[i])]
            s = sq
        else:
            ranked = topn(s, m, 60)
        ents = b.link_query(q, who, vis)
        out = []
        if ents:
            for e in ents:
                cand = b.ent_items.get(e, [])
                if self.bug == "seed_only_hop":
                    cand = [p for p in cand]                       # access checked on the seed entity only
                    sc2 = 0.2 * minmax(bm, np.ones_like(m)) + 0.8 * minmax(dv, np.ones_like(m))
                    cand = sorted(cand, key=lambda p: (-sc2[p], p))[:5]
                else:
                    cand = sorted([p for p in cand if m[p]], key=lambda p: (-s[p], p))[:5]
                out += [p for p in cand if p not in out]
        for p in ranked:
            if p not in out:
                out.append(p)
        out = out[:10]
        ids = tuple(b.ix.ids[p] for p in out)
        scores = tuple(round(float(s[p]), 6) if np.isfinite(s[p]) else None for p in out)
        snippets = []
        if self.bug == "hidden_snippet":
            allm = np.ones_like(m)
            s_all = 0.2 * minmax(b.ix.bm25(q, allm, "visible"), allm) + 0.8 * minmax(dv, allm)
            best2 = np.argsort(-s_all)[:12]
        for p in out:
            sn = b.disp[p][:80]
            if self.bug == "hidden_snippet":
                # "related:" enrichment picks the best match from ANY space
                j = int(next(x for x in best2 if x != p))
                sn += " | related: " + b.disp[j][:40]
            if self.bug == "card_widening" and b.docs[p]["kind"] == "card":
                sn = "card: " + self.wide.get(b.docs[p].get("entity"), "")[:120]
            snippets.append(sn)
        count = int(((bm > 0)).sum()) if self.bug == "count_before_filter" else int(((bm > 0) & m).sum())
        latency = "miss"
        if self.bug == "shared_prefix_cache":
            prompt = "SYS|" + q + "|" + "|".join(b.disp[p][:60] for p in out[:3])
            blocks = [prompt[:i] for i in range(16, len(prompt) + 1, 16)]
            hit = max((len(x) for x in blocks if x in self.prefix), default=0)
            latency = f"prefix{hit // 16}"
            self.prefix |= set(blocks)
        if self.bug == "query_cache":
            self.qcache[q] = (tuple(b.ix.ids[p] for p in ranked[:60]), {b.ix.ids[p]: round(float(s[p]), 6) for p in ranked[:60]})
        if self.bug == "semantic_cache":
            self.semcache.append((EMB.queries([q])[0], tuple(b.ix.ids[p] for p in ranked[:60]), {b.ix.ids[p]: round(float(s[p]), 6) for p in ranked[:60]}))
        return dict(ids=ids, scores=scores, count=count, snippets=tuple(snippets), err="", latency=latency)


def mutate(w, who, R, n_ins=25, n_edit=10, n_del=10, probe_words=()):
    """W' = W + changes confined to spaces `who` cannot see: inserts (vocabulary from who's queries, linked to entities who can
    also see), edits, deletes, a new hidden version of a connector key of a shared entity, and a revocation of ANOTHER identity's
    share. Returns (items', grants', extra_links, extra_facts)."""
    vis = w.visible(who)
    hidden_spaces = sorted({it["space"] for it in w.items} - set(vis))
    hidden = [it for it in w.items if it["space"] in hidden_spaces]
    shared = [e for e in w.entities.values() if set(e.get("spaces", [])) & set(vis) and set(e.get("spaces", [])) - set(vis)]
    items = list(w.items)
    new, links = [], {}
    words = list(probe_words) or ["update", "renewal", "plan"]
    for i in range(n_ins):
        sp = R.choice(hidden_spaces)
        e = R.choice(shared) if shared else None
        txt = " ".join(R.sample(words, min(4, len(words)))) + (f" — {e['name']}" if e else "") + f" note {R.randint(100, 999)}"
        iid = f"mut_{who}_{i}"
        new.append(dict(id=iid, type="note", space=sp, partition=sp, title="", text=txt, created_day=NOW_DAY, recorded_day=NOW_DAY, date="2026-06-30", thread="notes", sender=""))
        if e:
            links[iid] = [e["id"]]
    edit_ids = {it["id"] for it in R.sample(hidden, min(n_edit, len(hidden)))}
    del_ids = {it["id"] for it in R.sample([h for h in hidden if h["id"] not in edit_ids and not h.get("connector")], min(n_del, len(hidden)))}
    out = []
    for it in items:
        if it["id"] in del_ids:
            continue
        if it["id"] in edit_ids and not it.get("connector"):
            it = dict(it, text=it["text"] + " (edited: " + " ".join(R.sample(words, min(2, len(words)))) + ")")
        out.append(it)
    out += new
    grants = [dict(g) for g in w.grants]
    others = [g for g in grants if g["identity"] != who and g["identity"].startswith("coach_") and g["valid_to"] is None]
    if others:
        R.choice(others)["valid_to"] = NOW_DAY - 1
    keys_conn = copy.deepcopy(w.keys_conn)
    shared_ids = {e["id"] for e in shared}
    cand = [k for k in keys_conn.values() if k["entity"] in shared_ids and k["space"] in hidden_spaces]
    for j, k in enumerate(R.sample(cand, min(3, len(cand)))):
        h = w.by_id[k["versions"][-1]]
        c = dict(h["connector"], version=h["connector"]["version"] + 1, value_str=h["connector"]["value_str"] + " (revised)", supersedes=h["id"], superseded_by=None,
                 valid_from=NOW_DAY)
        iid = f"mutf_{who}_{j}"
        out = [dict(x, connector=dict(x["connector"], superseded_by=iid)) if x["id"] == h["id"] else x for x in out]
        out.append(dict(h, id=iid, text=h["text"] + " (revised)", created_day=NOW_DAY, recorded_day=NOW_DAY, connector=c))
        k["versions"] = k["versions"] + [iid]
    return out, grants, links, keys_conn


class WView:
    """A World3-like view with replaced items/grants (for twin worlds and history growth)."""

    def __init__(self, w, items=None, grants=None, keys_conn=None):
        self.__dict__.update({k: v for k, v in w.__dict__.items() if k not in ("_vis",)})
        if items is not None:
            self.items = items
            self.by_id = {it["id"]: it for it in items}
        if grants is not None:
            self.grants = grants
        if keys_conn is not None:
            self.keys_conn = keys_conn
        self._vis = {}
        self.gold = w.gold
        self.keys_all = w.keys_all

    visible = World3.visible


def observe(eng, who, qs, warm_qs):
    for q in warm_qs:
        eng.serve("dane", q)                  # privileged principal pre-warms shared state (GBrain harness method)
    return [eng.serve(who, q) for q in qs]


def s2(log, st, seed=1, n_ident=10):
    w = World3(seed)
    R = random.Random(77)
    L = {}
    from . import gate3
    links, recs = gate3.code_gate(w)
    # canaries linked to their space's owner entity so return-path bugs can surface them (DA3 anchored canaries the same way)
    from .world3 import SPACE_DEFAULT_ENTITY
    canary_tok = {}
    for it in w.items:
        m = re.search(r"(zqcanary\w+x)", it["text"])
        if m:
            canary_tok[it["id"]] = m.group(1)
            d = SPACE_DEFAULT_ENTITY.get(it["space"])
            if d:
                links[it["id"]] = [d]
    g = Gate("code", links, recs)
    idents = ["lachlan", "rhea", "tomas", "priya"] + sorted({x["identity"] for x in w.grants if x["identity"].startswith("coach_")})[:3] + ["member_m05", "member_m21", "member_m33"]
    idents = idents[:n_ident]
    tasks_by = defaultdict(list)
    for t in w.tasks:
        tasks_by[t["requester"]].append(t["query"])
    shared_names = [e["name"] for e in w.entities.values() if len(e.get("spaces", [])) > 1][:6]
    prev = st.get("s2_partial", {})
    res = prev.get("res") or {bug: dict(detected_ids=0, detected_any=0, n_ident=0, examples=[]) for bug in BUGS}
    done = set(prev.get("done", []))
    b_W = Brain3(w, g)
    for who in idents:
        if who in done:
            continue
        qs = (tasks_by.get(who, [])[:15] + [f"anything new about {n}?" for n in shared_names[:4]] + ["Bramwell Holdings settlement Orla Fenwick"])
        words = sorted({x for q in qs for x in re.findall(r"[a-z]{4,}", q.lower())})
        items2, grants2, extra_links, keys2 = mutate(w, who, random.Random(sum(map(ord, who))), probe_words=words)
        w2 = WView(w, items=items2, grants=grants2, keys_conn=keys2)
        g2 = Gate("code", {**{k: v for k, v in links.items() if k in w2.by_id}, **extra_links}, {k: v for k, v in recs.items() if k in w2.by_id})
        b_W2 = Brain3(w2, g2)
        for bug in BUGS:
            e1, e2 = Engine(b_W, w, bug), Engine(b_W2, w2, bug)
            o1, o2 = observe(e1, who, qs, qs), observe(e2, who, qs, qs)
            diff = [(q, a, c) for q, a, c in zip(qs, o1, o2) if a != c]
            idd = [(q, a, c) for q, a, c in zip(qs, o1, o2) if a["ids"] != c["ids"]]
            res[bug]["n_ident"] += 1
            res[bug]["detected_any"] += bool(diff)
            res[bug]["detected_ids"] += bool(idd)
            if diff and len(res[bug]["examples"]) < 2:
                q, a, c = diff[0]
                res[bug]["examples"].append(dict(who=who, q=q, field=[k for k in a if a[k] != c[k]]))
        # stale revocation cache: X's OWN share revoked; outputs must equal a fresh engine built on the revoked grants
        if who.startswith("coach_"):
            mine = [x for x in w.grants if x["identity"] == who and x["space"].startswith("member/") and x["valid_to"] is None]
            if mine:
                grants3 = [dict(x) for x in w.grants]
                for x in grants3:
                    if x["identity"] == who and x["space"] == mine[0]["space"]:
                        x["valid_to"] = NOW_DAY - 1
                for bug in BUGS:
                    eng = Engine(b_W, w, bug)
                    observe(eng, who, qs[:5], [])          # warm X's own state before the revocation
                    eng.grants = grants3                     # revocation reaches the system of record
                    fresh = Engine(b_W, w, "none", grants=grants3)
                    oa, ob = [eng.serve(who, q) for q in qs], [fresh.serve(who, q) for q in qs]
                    res[bug].setdefault("revocation_checks", 0)
                    res[bug]["revocation_checks"] += 1
                    res[bug].setdefault("revocation_detected", 0)
                    res[bug]["revocation_detected"] += any(a["ids"] != c["ids"] for a, c in zip(oa, ob))
        log(f"[s2] {who}: done")
        b_W2 = None; gc.collect()
        done.add(who)
        st["s2_partial"] = dict(res=res, done=sorted(done))
        CK[0]()
    # canary monitor on W for every bug: probes from every non-entitled identity
    canary = {}
    for bug in BUGS:
        eng = Engine(b_W, w, bug)
        alarms = probes = 0
        for who in idents + ["nogrant"]:
            vis = w.visible(who)
            for iid, tok in canary_tok.items():
                if w.by_id[iid]["space"] in vis:
                    continue
                hidden_toks = {t for i2, t in canary_tok.items() if w.by_id[i2]["space"] not in vis}
                for q in (f"{tok}", f"anything new about {w.entities.get((links.get(iid) or ['b_gym'])[0], {}).get('name', 'IronBark')}?", "Bramwell Holdings settlement"):
                    o = eng.serve(who, q)
                    probes += 1
                    if any(i in canary_tok and w.by_id[i]["space"] not in vis for i in o["ids"]) or any(t in sn for sn in o["snippets"] for t in hidden_toks):
                        alarms += 1
        canary[bug] = dict(alarms=alarms, probes=probes)
    # no-grant credential
    ng = Engine(b_W, w, "none").serve("nogrant", "anything new about IronBark Fitness?")
    st["s2"] = dict(res=res, canary=canary, nogrant=dict(rows=len(ng["ids"]), err=ng["err"]), idents=idents)
    return st


# ============================================================================ DA1-6 history growth + key timelines
def bloat_world(w, B, R):
    if B == 0:
        return w
    items = list(w.items)
    keys = copy.deepcopy(w.keys_conn)
    for k in keys.values():
        v1 = w.by_id[k["versions"][0]]
        c1 = v1["connector"]
        new_ids = []
        for j in range(B):
            iid = f"bl_{k['key']}_{j}"
            day = max(-1500, c1["valid_from"] - (B - j) * R.randint(20, 40))
            txt = v1["text"]
            for num in re.findall(r"\d[\d,]*", c1["value_str"])[:1]:
                try:
                    nv = int(num.replace(",", ""))
                    txt = txt.replace(num, f"{int(nv * R.uniform(0.8, 1.2)):,}" if "," in num else str(int(nv * R.uniform(0.8, 1.2))))
                except ValueError:
                    pass
            c = dict(c1, valid_from=day, version=0, value_str=c1["value_str"] if txt == v1["text"] else c1["value_str"] + "*", superseded_by="x", supersedes=None)
            items.append(dict(v1, id=iid, text=txt, created_day=max(0, day), recorded_day=max(0, day), connector=c))
            new_ids.append(iid)
        k["versions"] = new_ids + k["versions"]
    return WView(w, items=items, keys_conn=keys)


def da1_6(seeds, log, st):
    for s in seeds:
        w = World3(s)
        tasks = [t for t in w.tasks if t["cls"] in ("temporal_change", "current_state")]
        EMB.prefetch_queries([t["query"] for t in tasks])
        for B in (0, 10, 40):
            if (s, B, "timeline") in st:
                continue
            wb = bloat_world(w, B, random.Random(100 + s))
            b = Brain3(wb, None, timelines=True)
            # (a) version rows indexed (temporal router opens history); (b) key timelines pinned for linked entities
            st[(s, B, "rows")] = _rows(b, tasks, dict(prefix="none"), s, f"rows/B{B}")
            st[(s, B, "timeline")] = _rows(b, tasks, dict(prefix="none", timeline=True), s, f"timeline/B{B}")
            log(f"[da1-6] s{s} B={B}: done ({b.ix.N} docs)")
            b = None; gc.collect()
            EMB.save()
            CK[0]()
    return st


# ============================================================================ DA1-7 stub cards
CK = [lambda: None]


def da1_7(seeds, log, st, gate_names=("gold", "gate_haiku")):
    from .exp3 import load_gate_obj, alias_table
    for s in seeds:
        w = World3(s)
        tasks = [t for t in w.tasks if t["cls"] in EVAL]
        EMB.prefetch_queries([t["query"] for t in tasks])
        for gname in gate_names:
            g = load_gate_obj(w, gname)
            if g is None or (s, gname, "stub") in st:
                continue
            for mode in ("stored", "stub"):
                b = Brain3(w, g, alias_table=alias_table(g), stub_cards=(mode == "stub"))
                st[(s, gname, mode)] = _rows(b, tasks, dict(prefix="cards", C=3), s, f"cards/{mode}")
                b = None; gc.collect()
            log(f"[da1-7] s{s} {gname}: done")
            EMB.save()
            CK[0]()
    return st


# ============================================================================ EXIT check vs delayed index
def exit_check(seeds, log, st):
    for s in seeds:
        if s in st:
            continue
        w = World3(s)
        R = random.Random(500 + s)
        tasks = [t for t in w.tasks if t["cls"] in EVAL]
        EMB.prefetch_queries([t["query"] for t in tasks])
        b = Brain3(w, None)
        # system of record NOW: revoke every coach share of 3 members, erase member m07 entirely and 15 company items
        new_grants = [dict(g) for g in w.grants]
        revoked_spaces = [f"member/m{n:02d}" for n in R.sample(range(1, 43), 3)]
        for g in new_grants:
            if g["identity"].startswith("coach_") and g["space"] in revoked_spaces:
                g["valid_to"] = NOW_DAY - 1
        erased = {it["id"] for it in w.items if it["space"] == "member/m07"} | {it["id"] for it in R.sample([i for i in w.items if i["space"] == "company/ironbark"], 15)}
        sor = WView(w, grants=new_grants)

        def visible_now(who):
            return sor.visible(who)

        rows = defaultdict(list)
        leaks = Counter()
        for t in tasks:
            who = t["requester"]
            # delayed index: ACL snapshot from BEFORE the revocation, erased items still indexed
            ctx = b.assemble(t, dict(prefix="none"), maxk=200, maxt=0)
            ids = [b.ix.ids[p] for p in ctx]
            vis_now = visible_now(who)
            bad = [i for i in ids[:50] if i in erased or b.docs[b.ix.pos[i]]["space"] not in vis_now]
            leaks["no_exit_items"] += len(bad)
            leaks["no_exit_tasks"] += bool(bad)
            # exit check: one primary-key re-check of the final ids against the system of record, then backfill
            ok = [p for p in ctx if b.ix.ids[p] not in erased and b.docs[p]["space"] in vis_now]
            bad2 = [i for i in [b.ix.ids[p] for p in ok[:50]] if i in erased or b.docs[b.ix.pos[i]]["space"] not in vis_now]
            leaks["exit_items"] += len(bad2)
            # recall: tasks whose required items are all still visible and not erased
            if all(r not in erased and w.by_id[r]["space"] in vis_now for r in t["required"]):
                r0 = b.score(t, ctx); r1 = b.score(t, ok)
                r0.update(seed=s, arm="no exit"); r1.update(seed=s, arm="exit check")
                rows["no exit"].append(r0); rows["exit check"].append(r1)
        # targeted probes from revoked coaches and the erased member's own credential
        probes = 0
        for g in w.grants:
            if g["identity"].startswith("coach_") and g["space"] in revoked_spaces and g["valid_to"] is None:
                for t in [t for t in w.tasks if t["requester"] == g["identity"]][:10]:
                    ctx = b.assemble(t, dict(prefix="none"), maxk=50, maxt=0)
                    ids = [b.ix.ids[p] for p in ctx]
                    vis_now = visible_now(g["identity"])
                    probes += 1
                    leaks["probe_no_exit"] += sum(1 for i in ids if b.docs[b.ix.pos[i]]["space"] not in vis_now or i in erased)
                    leaks["probe_exit"] += 0
        st[s] = dict(rows=dict(rows), leaks=dict(leaks), probes=probes, revoked=revoked_spaces, erased=len(erased))
        log(f"[exit] s{s}: {dict(leaks)}")
        b = None; gc.collect()
    return st


def run_all(seeds, log=print, save=None, load=None):
    """BB3_ADR selects checks (comma list; default all). Each check checkpoints per unit, so a stopped run resumes."""
    import os
    st = load("adr") or {}
    sel = [x for x in os.environ.get("BB3_ADR", "da1_4,exit,da1_6,da1_7,s2").split(",") if x]

    def merge_save():
        disk = load("adr") or {}          # another process may have saved other checks meanwhile: merge, never clobber
        for k in sel:
            if k in st:
                disk[k] = st[k]
        save("adr", disk)
    CK[0] = merge_save
    for name, fn in (("da1_4", lambda d: da1_4(seeds, log, d)), ("exit", lambda d: exit_check(seeds, log, d)),
                     ("da1_6", lambda d: da1_6(seeds, log, d)), ("da1_7", lambda d: da1_7(seeds, log, d)),
                     ("s2", lambda d: s2(log, d))):
        if name not in sel:
            continue
        if name == "s2" and "s2" in st.get("s2", {}):
            continue
        d = st.setdefault(name, {})
        fn(d)
        merge_save()
    return st
