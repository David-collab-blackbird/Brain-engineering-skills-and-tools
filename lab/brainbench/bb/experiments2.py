"""Batch-2 experiments on BrainBench v0.2: E8 (real retrieval, rerankers, batch-1 arms re-run), E6 (decomposition,
gap-check), N4 (entity linkers), M1 (p^m check), H13-lite. Each function returns plain dicts of per-task rows so the
runner can compute cluster-aware statistics and save everything."""
from __future__ import annotations

import random
import re
import time
from collections import Counter, defaultdict

import numpy as np

from .brain import is_temporal_query
from .ctx2 import (CLASSES2, COMPLEX, DEPTH, K, Ctx, fill, ids_of, live, query_ranked, row)
from .experiments import ScopeInfer, scope_packets
from .retrieval import item_text, topn
from .tasks import SCOPE_GROUPS

HAND_SLOTS2 = {
    "finance": dict(static=["portfolio.strategy", "portfolio.lvr_rule", "offset.balance", "portfolio.borrowing_capacity", "offset.savings_goal"],
                    attrs={"property": ["valuation", "loan", "rent", "lease_end", "rate", "pm"], "holding": ["units", "value"]}),
    "business/gym": dict(static=["gym.members", "gym.member_target", "gym.price", "gym.staff_count", "gym.equipment_supplier"],
                         attrs={"person": ["plan", "program", "goal", "progress", "coach", "retention", "retention_target"]}),
    "business/cafe": dict(static=["cafe.cash_reserve", "cafe.covers", "cafe.revenue_goal", "cafe.head_barista", "cafe.hours"],
                          attrs={"person": ["training_goal"]}),
    "business/construction": dict(static=["con.pipeline", "con.strategy", "con.supervisor", "con.active_projects", "con.margin"],
                                  attrs={"project": ["status", "budget", "cost"]}),
    "health": dict(static=["train.program", "train.sessions", "goal_squat.target", "train.squat_1rm", "goal_run.target"], attrs={}),
    "family": dict(static=["family.school_break", "family.holiday_budget", "mila.activity", "theo.activity", "ruby.activity"],
                   attrs={"person": ["activities", "swim_pb", "swim_goal", "basketball_goal", "piano_goal"]}),
    "reading": dict(static=["reading.goal", "reading.finished", "reading.current"], attrs={}),
}


def subsample(ctx: Ctx, per_class: int, classes=CLASSES2, seed=0):
    """Stratified: one task per distinct required set, then `per_class` sets per class."""
    R = random.Random(seed * 1000 + ctx.seed)
    out = []
    for c in classes:
        first = {}
        for t in ctx.tasks:
            if t["cls"] == c and t["set_id"] not in first:
                first[t["set_id"]] = t
        ts = sorted(first.values(), key=lambda t: t["id"])
        out += R.sample(ts, min(per_class, len(ts)))
    return out


def tag(rows, **kw):
    for r in rows:
        r.update(kw)
    return rows


# ============================================================================ E8a retrievers
def e8_retrievers(ctx: Ctx, methods: dict, depths=(10, 20, 50, 100, 200)):
    """methods: name -> DSearcher. Returns name -> rows (with ok/rec at several depths)."""
    out = {}
    for name, s in methods.items():
        s.prefetch([t["query"] for t in ctx.tasks])
        rows = []
        t0 = time.time()
        for t in ctx.tasks:
            ranked = query_ranked(ctx.b if s.b is ctx.b else s.b, s, t, n=max(depths))
            rows.append(row(t, ids_of(s.b, ranked), ks=depths))
        out[name] = tag(rows, seed=ctx.seed, arm=name)
        out[name + "#secs"] = (time.time() - t0) / len(ctx.tasks)
    return out


def tune_alpha(ctx: Ctx, emb, grid=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)):
    best, res = None, {}
    for a in grid:
        s = ctx.searcher("wsum", emb, alpha=a)
        rows = [row(t, ids_of(ctx.b, query_ranked(ctx.b, s, t, n=10))) for t in ctx.tasks]
        sc = np.mean([r["rec@10"] for r in rows]) + np.mean([r["ok@10"] for r in rows])
        res[a] = float(sc)
        if best is None or sc > res[best]:
            best = a
    return best, res


# ============================================================================ E8b rerankers
def scope_instruction(t):
    sg = t["declared_scope"]
    who = {"owner": "the owner", "household": "a family member", "partner_gym": "the gym business partner", "partner_construction": "the construction business partner",
           "partner_cafe": "the cafe business partner"}.get(t["requester"], "a gym member")
    area = {"finance": "personal finances and the investment property portfolio", "business/gym": "the IronBark gym business", "business/cafe": "the Copperleaf cafe business",
            "business/construction": "the Stonefield construction business", "health": "personal training and health goals", "family": "family life, the kids and holidays",
            "reading": "books and reading"}[sg]
    return (f"Given a request from {who} about {area}, retrieve every note, fact, message, email, decision or photo that is needed to answer it, "
            f"including current figures, goals, rules, prior decisions and quotes, even if they do not repeat the request's words")


def e8_rerank(ctx: Ctx, s, tasks, rerankers: dict, depth=50, variants=None):
    """rerankers: name -> Reranker. variants: optional dict name -> (reranker_name, instruction_fn)."""
    out = {}
    cands = {}
    for t in tasks:
        cands[t["id"]] = query_ranked(ctx.b, s, t, n=depth)
    out["none"] = tag([row(t, ids_of(ctx.b, cands[t["id"]]), ks=(10, depth)) for t in tasks], seed=ctx.seed, arm="none")
    jobs = [(n, n, None) for n in rerankers] + [(vn, rn, fn) for vn, (rn, fn) in (variants or {}).items()]
    for vname, rname, ifn in jobs:
        rr = rerankers[rname]
        rows = []
        t0 = time.time()
        npairs = 0
        for t in tasks:
            c = cands[t["id"]]
            docs = [item_text(ctx.b.ix.items[i], True) for i in c]
            sc = rr.score(t["query"], docs, instruction=ifn(t) if ifn else None)
            npairs += len(docs)
            order = [c[j] for j in np.argsort(-sc, kind="stable")]
            rows.append(row(t, ids_of(ctx.b, order), ks=(10, depth)))
        rr.save()
        out[vname] = tag(rows, seed=ctx.seed, arm=vname)
        out[vname + "#wall"] = (time.time() - t0, npairs)
    return out


# ============================================================================ E8c batch-1 arms with real retrievers
def make_linkers(ctx: Ctx, emb="qwen3-emb"):
    """Entity linkers. Returns dict name -> fn(task) -> [entity ids]. Embedding linker uses entity descriptor texts
    (name, aliases, kind and current facts = the card text) and the dense query vector."""
    w = ctx.w
    ents = sorted(w.entities)
    cardtxt = {}
    for d in ctx.cards:
        eid = d["entities"][0]
        cardtxt[eid] = cardtxt.get(eid, "") + " " + d["text"]
    desc = []
    for e in ents:
        en = w.entities[e]
        desc.append(f"{en['name']} ({en['kind']}; also called {', '.join(en['aliases'][1:])}).{cardtxt.get(e, '')}")
    E = ctx.emb[emb].docs(desc, f"s{ctx.seed}/entities")
    em = ctx.emb[emb]
    ent_acc = {}

    def accessible(eid, requester):
        key = (eid, requester)
        if key not in ent_acc:
            parts = set(w.identities[requester]["partitions"])
            ent_acc[key] = bool(set(w.entities[eid]["partitions"]) & parts) or not w.entities[eid]["partitions"]
        return ent_acc[key]

    def lexical(t):
        return [e for e in ctx.L.link(t["query"], t["requester"]) if accessible(e, t["requester"])]

    def emb_top(t, k=5, tau=None):
        q = em.queries([t["query"]])[0]
        sims = E @ q
        order = np.argsort(-sims)
        out = []
        for j in order:
            if tau is not None and sims[j] < tau:
                break
            e = ents[j]
            if accessible(e, t["requester"]):
                out.append(e)
            if len(out) >= k:
                break
        return out

    def union(t, k=3):
        out = lexical(t)
        for e in emb_top(t, k=k + len(out)):
            if e not in out and len(out) < max(k, len(lexical(t))) + k:
                out.append(e)
        return out

    linkers = {"lexical": lexical, "embedding@3": lambda t: emb_top(t, 3), "embedding@5": lambda t: emb_top(t, 5),
               "lexical+embedding@3": lambda t: union(t, 3)}
    return linkers, dict(ents=ents, E=E, desc=desc, emb_top=emb_top, lexical=lexical, accessible=accessible)


def required_entities(ctx, t):
    return {ctx.w.by_id[r]["entity_id"] for r in t["required"] if ctx.w.by_id[r].get("entity_id")}


class Assembler:
    """Batch-1 E3 arms on top of a real retriever: query-only, mention forwarding, packets, slots, cards(+slots)."""

    def __init__(self, ctx: Ctx, method="rrf", emb="qwen3-emb", alpha=0.5):
        self.ctx = ctx
        self.s = ctx.searcher(method, emb, "base", alpha=alpha)
        self.sc = ctx.searcher(method, emb, "cards", alpha=alpha)
        self.packets = scope_packets(ctx.w, ctx.b, 5)
        freq = defaultdict(Counter)
        for t in ctx.tasks:
            for r in t["required"]:
                freq[t["declared_scope"]][r] += 1
        self.oracle = {g: [i for i, _ in freq[g].most_common(40)] for g in freq}
        self.si = ScopeInfer(ctx.b)

    def prefetch(self, tasks):
        self.s.prefetch([t["query"] for t in tasks]); self.sc.prefetch([t["query"] for t in tasks])

    def acc(self, b, t, iid):
        return b.access(t["requester"])[b.pos[iid]]

    # -------- arms; each returns (final_ids, covers or None, prefix_ids)
    def query_only(self, t, k=K, mask=None, **kw):
        b = self.ctx.b
        return ids_of(b, fill([], query_ranked(b, self.s, t, n=k + 30, mask=mask, **kw), k)), None, []

    def mention_fwd(self, t, k=K):
        b, w = self.ctx.b, self.ctx.w
        acc = b.access(t["requester"])
        out = []
        for i in query_ranked(b, self.s, t, n=k + 30):
            for j in [i] + [b.pos[w.head_of[f]] for f in b.ix.items[i].get("fact_refs", []) if f in w.head_of]:
                if j not in out and acc[j] and len(out) < k:
                    out.append(j)
            if len(out) >= k:
                break
        return ids_of(b, out), None, []

    def packet(self, t, P=5, oracle=False, k=K):
        b = self.ctx.b
        src = self.oracle if oracle else self.packets
        pk = [b.pos[i] for i in src.get(t["declared_scope"], []) if self.acc(b, t, i)][:P]
        return ids_of(b, fill(pk, query_ranked(b, self.s, t, n=k + 30), k)), None, ids_of(b, pk)

    def slot_ids(self, t, kind, ents, cap=5):
        w, b = self.ctx.w, self.ctx.b
        g = t["declared_scope"]
        L = self.ctx.L
        out = []
        if kind == "hand":
            spec = HAND_SLOTS2[g]
            for eid in ents:
                for attr in spec["attrs"].get(w.entities[eid]["kind"], []):
                    for kk in L.keys_by_entity[eid]:
                        if kk["key"].split(".")[-1] == attr or kk["attr"] == attr:
                            out.append(kk["versions"][-1])
            out += [w.keys[kk]["versions"][-1] for kk in spec["static"] if kk in w.keys]
        else:
            bm, dv = self.s.raw(t["query"], t["requester"])
            ef = []
            for eid in ents:
                for kk in L.keys_by_entity[eid]:
                    hh = kk["versions"][-1]
                    ef.append((-(bm[b.pos[hh]] / 10 + dv[b.pos[hh]]), hh))
            out += [hh for _, hh in sorted(ef)] + self.packets.get(g, [])
        seen, res = set(), []
        for i in out:
            if i not in seen and self.acc(b, t, i):
                seen.add(i); res.append(b.pos[i])
        return res[:cap]

    def slots(self, t, kind="hand", linker=None, k=K):
        b = self.ctx.b
        ents = linker(t) if linker else self.ctx.L.link(t["query"], t["requester"])
        sl = self.slot_ids(t, kind, ents)
        return ids_of(b, fill(sl, query_ranked(b, self.s, t, n=k + 30), k)), None, ids_of(b, sl)

    def card_prefix(self, t, C=3, with_slots=False, linker=None, total_prefix=5):
        ctx, bc, w = self.ctx, self.ctx.bc, self.ctx.w
        ents = linker(t) if linker else ctx.L.link(t["query"], t["requester"])
        pre = []
        for eid in ents:
            for cid in ctx.card_of.get(eid, []):
                if self.acc(bc, t, cid) and len(pre) < C and bc.pos[cid] not in pre:
                    pre.append(bc.pos[cid])
        if with_slots:
            for kk in HAND_SLOTS2[t["declared_scope"]]["static"]:
                if kk not in w.keys:
                    continue
                hh = w.keys[kk]["versions"][-1]
                if self.acc(bc, t, hh) and len(pre) < total_prefix and bc.pos[hh] not in pre and not any(hh in ctx.covers.get(bc.ids[p], ()) for p in pre):
                    pre.append(bc.pos[hh])
        return pre

    def cards(self, t, C=3, with_slots=False, linker=None, k=K, fill_ranked=None):
        bc = self.ctx.bc
        pre = self.card_prefix(t, C, with_slots, linker)
        ranked = fill_ranked if fill_ranked is not None else query_ranked(bc, self.sc, t, n=k + 30)
        return ids_of(bc, fill(pre, ranked, k)), self.ctx.covers, ids_of(bc, pre)

    def scope(self, t, mode, group_fn, wt=1.0, k=K):
        b = self.ctx.b
        g = group_fn(t)
        if not g:
            return self.query_only(t, k)
        if mode == "hard":
            return self.query_only(t, k, mask=b.scope_mask(g))
        m, temporal = live(b, t)
        fs = self.s.fused(t["query"], t["requester"], m & b.scope_mask(g))
        lst = topn(fs, np.isfinite(fs), DEPTH)
        return self.query_only(t, k, extra_lists=[lst], extra_w=[wt])


def run_arm(tasks, fn, seed, name, ks=(10,)):
    rows = []
    for t in tasks:
        ids, cov, pre = fn(t)
        r = row(t, ids, cov, ks=ks)
        if pre is not None:
            got = set(pre)
            if cov:
                for p in pre:
                    got |= cov.get(p, set())
            r["prefix_cov"] = len(got & set(t["required"])) / len(set(t["required"]))
        rows.append(r)
    return tag(rows, seed=seed, arm=name)


def e8_arms(ctx: Ctx, method="rrf", emb="qwen3-emb", alpha=0.5, ksweep=True):
    A = Assembler(ctx, method, emb, alpha)
    A.prefetch(ctx.tasks)
    tasks = ctx.tasks
    decl = lambda t: t["declared_scope"]
    qinf = lambda t: A.si.from_query(t["query"])
    arms = {
        "query-only": A.query_only,
        "query + mention forwarding": A.mention_fwd,
        "packet(5) + query": lambda t: A.packet(t, 5),
        "ORACLE packet(5) + query": lambda t: A.packet(t, 5, oracle=True),
        "hand slots + query": lambda t: A.slots(t, "hand"),
        "generic slots + query": lambda t: A.slots(t, "generic"),
        "cards(<=3) + query": lambda t: A.cards(t, 3),
        "cards(<=3) + static slots + query": lambda t: A.cards(t, 3, True),
        "declared scope: hard filter": lambda t: A.scope(t, "hard", decl),
        "declared scope: boost w=1": lambda t: A.scope(t, "boost", decl, 1.0),
        "query-inferred scope: hard": lambda t: A.scope(t, "hard", qinf),
        "query-inferred scope: boost": lambda t: A.scope(t, "boost", qinf),
    }
    out = {}
    for name, fn in arms.items():
        out[name] = run_arm(tasks, fn, ctx.seed, name)
    # k sweep on the best assembly for H9 / M1
    for k in ((20, 30) if ksweep else ()):
        out[f"query-only@{k}"] = run_arm(tasks, lambda t: A.query_only(t, k), ctx.seed, f"query-only@{k}", ks=(k,))
        out[f"cards+slots@{k}"] = run_arm(tasks, lambda t: A.cards(t, 3, True, k=k), ctx.seed, f"cards+slots@{k}", ks=(k,))
    return out, A


def e8_origin(ctx: Ctx, emb="qwen3-emb", alpha=0.5):
    tasks = [t for t in ctx.tasks if t["cls"] == "multimodal"]
    out = {}
    for idx in ("base", "noorig"):
        for meth in ("bm25", "dense", "rrf", "wsum"):
            s = ctx.searcher(meth, emb, idx, alpha=alpha)
            b = s.b
            rows = []
            for t in tasks:
                m, temporal = live(b, t)
                ids = ids_of(b, s.rank(t["query"], t["requester"], m, n=K))
                r = row(t, ids)
                r["sub"] = "needs origin-only" if any(ctx.w.by_id[x].get("media", {}).get("origin_only") for x in t["required"]) else "caption sufficient"
                rows.append(r)
            out[f"{idx}/{meth}"] = tag(rows, seed=ctx.seed, arm=f"{idx}/{meth}")
    return out


# ============================================================================ LLM helpers (E6, N4, H13)
SYS = ("You help a personal assistant search a private memory (notes, keyed facts, emails, chats, meeting minutes, photos and scans) "
       "for Dane Halloran's family. Dane and his wife Priya have three kids (Mila, Theo, Ruby), an investment property portfolio and share "
       "holdings, and co-own three businesses: IronBark Fitness (a gym, partner Lachlan), Stonefield Builders (construction, partner Rhea) and "
       "Copperleaf Cafe (partner Tomas). Be brief.")


def parse_lines(txt, cap):
    out = []
    for ln in txt.splitlines():
        ln = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", ln.replace("**", ""))
        ln = re.sub(r"\s*\([^)]*\)?", "", ln).strip().strip('"').strip()
        if not ln or ln.upper().startswith("NONE") or len(ln) < 3:
            continue
        if ln.endswith(":"):
            continue
        out.append(ln[:160])
        if len(out) >= cap:
            break
    return out


DEC_PROMPT = """Turn a request into search queries for a personal memory store. Each query names ONE specific piece of stored information the answer depends on (a current number, a goal or target, a rule or policy, an earlier decision, a quote, feedback, a preference, a schedule). Use concrete nouns, not question words.

Example request: "should we replace the delivery van at the bakery?"
van servicing costs and breakdowns
bakery vehicle budget or capex rule
quotes for a new delivery van
bakery revenue this quarter

Example request: "is my sister's wedding trip affordable?"
wedding date and travel dates
holiday budget
savings account balance
flight and accommodation quotes

Request: "{q}"
"""
GAP_PROMPT = """A personal assistant must answer a request using items retrieved from a memory store. Look at what was retrieved and name the information that is still missing.

Example request: "should we replace the delivery van at the bakery?"
Retrieved: 1. Van rego renewal due in March. 2. Driver roster for May. 3. Van broke down again on Tuesday, towed.
Missing (search queries):
quotes for a new delivery van
bakery capex budget or spending rule
bakery revenue this quarter

Example request: "what's the wifi password at the office?"
Retrieved: 1. Office wifi: network StarNet, password blue-heron-42.
Missing (search queries):
NONE

Request: "{q}"
Retrieved:
{items}
Missing (search queries):
"""
LINK_PROMPT = """Pick the records that hold information needed to answer the request. Answer with record numbers separated by commas (up to 5, most important first).

Example request: "is the bakery van worth keeping?"
Records: 1. Bakery van (vehicle) 2. Sunrise Bakery (business) 3. Dane's training (person_profile) 4. offset account (account)
Answer: 1, 2

Request: "{q}"
Records: {cands}
Answer:"""


def decompose_prompt(q):
    return DEC_PROMPT.format(q=q)


def gap_prompt(q, items_txt):
    return GAP_PROMPT.format(q=q, items="\n".join(f"{i+1}. {x}" for i, x in enumerate(items_txt)))


def short_text(it, n=160):
    t = (it.get("title") + ": " if it.get("title") else "") + it["text"]
    return t[:n]


def facet_queries(ctx: Ctx, t, A):
    """Deterministic facet decomposer: linked entities x their attribute labels + the scope's static slot labels."""
    w = ctx.w
    ents = ctx.L.link(t["query"], t["requester"])
    qs = []
    for eid in ents[:2]:
        nm = w.entities[eid]["name"]
        labels = [kk["label"] for kk in ctx.L.keys_by_entity[eid]][:3]
        qs.append(nm + " " + " ".join(labels))
    spec = HAND_SLOTS2[t["declared_scope"]]
    labels = [w.keys[k]["label"] for k in spec["static"] if k in w.keys]
    qs.append(" ".join(labels[:3]))
    qs.append(t["query"] + " decision rule goal policy")
    return qs[:4]


def multi_query_ranked(b, s, t, subqs, n_each=30, w_orig=1.0):
    """Union of the original query and sub-queries, fused by RRF (original weight w_orig)."""
    m, temporal = live(b, t)
    lists, wts = [], []
    for j, q in enumerate([t["query"]] + list(subqs)):
        sc = s.fused(q, t["requester"], m)
        lists.append(topn(sc, np.isfinite(sc), n_each))
        wts.append(w_orig if j == 0 else 1.0)
    from .retrieval import rrf
    fused = rrf(lists, b.N, weights=wts)
    order = topn(fused, fused > 0, 200)
    return b.forward(list(order), temporal)


def e6_nonllm(ctx: Ctx, A: Assembler, tasks, swaps: dict):
    """Model-free E6 arms (cheap, all seeds): one-shot, deterministic facet decomposition, embedder swaps, and the
    same with the cards+static-slots prefix."""
    b, s, bc = ctx.b, A.s, ctx.bc
    fac = {t["id"]: facet_queries(ctx, t, A) for t in tasks}
    allq = [q for v in fac.values() for q in v]
    s.prefetch(allq); A.sc.prefetch(allq)
    out = {}
    out["one-shot"] = tag([row(t, ids_of(b, query_ranked(b, s, t, n=30)), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="one-shot")
    out["facet decomposition (deterministic)"] = tag([row(t, ids_of(b, multi_query_ranked(b, s, t, fac[t["id"]])), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="facets")
    for name, ss in swaps.items():
        ss.prefetch([t["query"] for t in tasks])
        out[name] = tag([row(t, ids_of(b, query_ranked(b, ss, t, n=30)), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm=name)
    rows1, rows2 = [], []
    for t in tasks:
        ids, cov, _ = A.cards(t, 3, True, fill_ranked=query_ranked(bc, A.sc, t, n=100)); rows1.append(row(t, ids, cov, ks=(10, 20)))
        ids, cov, _ = A.cards(t, 3, True, fill_ranked=multi_query_ranked(bc, A.sc, t, fac[t["id"]])); rows2.append(row(t, ids, cov, ks=(10, 20)))
    out["cards+slots + one-shot"] = tag(rows1, seed=ctx.seed, arm="cs")
    out["cards+slots + facets"] = tag(rows2, seed=ctx.seed, arm="cs+facets")
    return out


def e6_decomposition(ctx: Ctx, A: Assembler, llm, tasks, reranker=None, rr_depth=50, rounds=2):
    """One-shot vs capped decomposition (<=4 sub-queries, union, optional rerank) vs gap-check loop (<=2 rounds),
    plus deterministic facets, and combinations with the cards+slots prefix. Returns rows per arm and call/latency stats."""
    b, s = ctx.b, A.s
    out, stats = {}, {}
    # ---- LLM decomposition (one call per task)
    t0 = time.time()
    dec_txt = llm.generate([decompose_prompt(t["query"]) for t in tasks], max_new_tokens=72, system=SYS)
    stats["decompose"] = dict(calls=len(tasks), wall=time.time() - t0)
    dec = {t["id"]: parse_lines(x, 4) for t, x in zip(tasks, dec_txt)}
    stats["decompose"]["mean_subqueries"] = float(np.mean([len(v) for v in dec.values()]))
    stats["decompose"]["share_at_cap"] = float(np.mean([len(v) == 4 for v in dec.values()]))
    allq = [q for v in dec.values() for q in v]
    s.prefetch(allq); A.sc.prefetch(allq)
    fac = {t["id"]: facet_queries(ctx, t, A) for t in tasks}
    s.prefetch([q for v in fac.values() for q in v]); A.sc.prefetch([q for v in fac.values() for q in v])

    def rr(t, cand):
        if reranker is None:
            return cand
        docs = [item_text(b.ix.items[i], True) for i in cand[:rr_depth]]
        sc = reranker.score(t["query"], docs)
        return [cand[j] for j in np.argsort(-sc, kind="stable")] + cand[rr_depth:]

    one = {t["id"]: query_ranked(b, s, t, n=100) for t in tasks}
    out["one-shot"] = tag([row(t, ids_of(b, one[t["id"]]), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="one-shot")
    if reranker is not None:
        out["one-shot + rerank"] = tag([row(t, ids_of(b, rr(t, one[t["id"]])), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="one-shot + rerank")
    decr = {t["id"]: multi_query_ranked(b, s, t, dec[t["id"]]) for t in tasks}
    out["decomposition (LLM, <=4, RRF union)"] = tag([row(t, ids_of(b, decr[t["id"]]), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="decomp")
    if reranker is not None:
        out["decomposition + rerank"] = tag([row(t, ids_of(b, rr(t, decr[t["id"]])), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="decomp+rr")
    facr = {t["id"]: multi_query_ranked(b, s, t, fac[t["id"]]) for t in tasks}
    out["facet decomposition (deterministic)"] = tag([row(t, ids_of(b, facr[t["id"]]), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="facets")

    # ---- gap-check loop
    cur = {t["id"]: list(one[t["id"]]) for t in tasks}
    gapq = {t["id"]: [] for t in tasks}
    active = list(tasks)
    gstats = []
    for rnd in range(rounds):
        if not active:
            break
        prompts = [gap_prompt(t["query"], [short_text(b.ix.items[i], 110) for i in cur[t["id"]][:8]]) for t in active]
        t0 = time.time()
        res = llm.generate(prompts, max_new_tokens=48, system=SYS)
        gstats.append(dict(round=rnd + 1, calls=len(active), wall=time.time() - t0))
        nxt = []
        for t, x in zip(active, res):
            qs = parse_lines(x, 3)
            if not qs:
                continue
            qs = [x for x in qs if x not in gapq[t["id"]]]
            if not qs:
                continue
            gapq[t["id"]] += qs
            nxt.append(t)
        allg = [q for t in nxt for q in gapq[t["id"]]]
        s.prefetch(allg); A.sc.prefetch(allg)
        for t in nxt:
            cur[t["id"]] = multi_query_ranked(b, s, t, gapq[t["id"]], n_each=30, w_orig=1.0)
        gstats[-1]["continued"] = len(nxt)
        active = nxt
    stats["gap"] = gstats
    stats["gap_calls_per_task"] = sum(g["calls"] for g in gstats) / len(tasks)
    stats["gap_queries_per_task"] = float(np.mean([len(v) for v in gapq.values()]))
    out["gap-check (<=2 rounds)"] = tag([row(t, ids_of(b, cur[t["id"]]), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="gap")
    if reranker is not None:
        out["gap-check + rerank"] = tag([row(t, ids_of(b, rr(t, cur[t["id"]])), ks=(10, 20)) for t in tasks], seed=ctx.seed, arm="gap+rr")

    # ---- with the structural prefix (cards + static slots), search fills the rest
    bc = ctx.bc
    def on_cards(subqs_of):
        rows = []
        for t in tasks:
            fr = multi_query_ranked(bc, A.sc, t, subqs_of(t)) if subqs_of else query_ranked(bc, A.sc, t, n=100)
            ids, cov, pre = A.cards(t, 3, True, fill_ranked=fr)
            rows.append(row(t, ids, cov, ks=(10, 20)))
        return rows
    out["cards+slots + one-shot"] = tag(on_cards(None), seed=ctx.seed, arm="cs")
    out["cards+slots + decomposition"] = tag(on_cards(lambda t: dec[t["id"]]), seed=ctx.seed, arm="cs+decomp")
    out["cards+slots + gap-check queries"] = tag(on_cards(lambda t: gapq[t["id"]]), seed=ctx.seed, arm="cs+gap")
    out["cards+slots + facets"] = tag(on_cards(lambda t: fac[t["id"]]), seed=ctx.seed, arm="cs+facets")
    examples = [dict(q=t["query"], cls=t["cls"], decomposition=dec[t["id"]], gap_queries=gapq[t["id"]], facets=fac[t["id"]]) for t in tasks[:: max(1, len(tasks) // 12)]]
    return out, stats, examples


def llm_link_prompt(q, cands):
    return LINK_PROMPT.format(q=q, cands=" ".join(f"{i+1}. {c}" for i, c in enumerate(cands)))


def n4_linkers(ctx: Ctx, A: Assembler, linkers: dict, info: dict, tasks, llm=None, ncand=15, llm_tasks=None):
    """Linker recall/precision on required fact entities, and CR@10 with cards(<=3)+static slots and cards(<=5) at fixed
    assembly, for each linker. LLM-assisted linker picks from lexical ∪ embedding top-ncand candidates."""
    w = ctx.w
    L = dict(linkers)
    stats = {}
    if llm is not None:
        cand = {}
        prompts = []
        llm_tasks = llm_tasks or tasks
        tasks = llm_tasks            # LLM linker and its comparison arms run on the LLM subsample
        for t in tasks:
            c = info["lexical"](t)
            for e in info["emb_top"](t, k=ncand):
                if e not in c:
                    c.append(e)
            c = c[:ncand]
            cand[t["id"]] = c
            prompts.append(llm_link_prompt(t["query"], [f"{w.entities[e]['name']} ({w.entities[e]['kind']})" for e in c]))
        t0 = time.time()
        res = llm.generate(prompts, max_new_tokens=20, system=SYS)
        stats["llm_wall"] = time.time() - t0
        stats["llm_calls"] = len(prompts)
        pick = {}
        for t, x in zip(tasks, res):
            nums = [int(n) for n in re.findall(r"\d+", x)]
            c = cand[t["id"]]
            pick[t["id"]] = list(dict.fromkeys(c[n - 1] for n in nums if 1 <= n <= len(c)))[:5]
        L["LLM-assisted (picks from lexical+embedding@15)"] = lambda t: pick[t["id"]]
        L["lexical + LLM-assisted"] = lambda t: list(dict.fromkeys(info["lexical"](t) + pick[t["id"]]))
        L["candidates@15 (ceiling of LLM linker)"] = lambda t: cand[t["id"]]
    out = {}
    for name, fn in L.items():
        recs, precs, nlinked = [], [], []
        rows3, rows5 = [], []
        for t in tasks:
            need = required_entities(ctx, t)
            got = fn(t)
            if need:
                recs.append(dict(cls=t["cls"], set_id=t["set_id"], rec=len(need & set(got)) / len(need), all=need <= set(got)))
            precs.append(len(need & set(got)) / len(got) if got else float("nan"))
            nlinked.append(len(got))
            ids, cov, pre = A.cards(t, 3, True, linker=fn)
            rows3.append(row(t, ids, cov))
            ids, cov, pre = A.cards(t, 5, False, linker=fn)
            rows5.append(row(t, ids, cov))
        out[name] = dict(linker=recs, precision=float(np.nanmean(precs)), mean_linked=float(np.mean(nlinked)),
                         rows_cards3_slots=tag(rows3, seed=ctx.seed, arm=name), rows_cards5=tag(rows5, seed=ctx.seed, arm=name))
    return out, stats


def h13_lite(ctx: Ctx, llm, method="rrf", emb="qwen3-emb", alpha=0.5, n_sets=None):
    """Index-time enrichment (origin context) vs query-side expansion (LLM rewrites the request into keyword
    variants) on multimodal tasks."""
    tasks = subsample(ctx, n_sets, classes=["multimodal"]) if n_sets else [t for t in ctx.tasks if t["cls"] == "multimodal"]
    prompts = [f"Request: \"{t['query']}\"\n\nThe target is a photo, video or scanned page in the memory. Write 3 alternative short search queries "
               f"that might match how the file is captioned, which folder or album it is in, or who shared it. One per line, no numbering." for t in tasks]
    t0 = time.time()
    res = llm.generate(prompts, max_new_tokens=60, system=SYS)
    wall = time.time() - t0
    exp = {t["id"]: parse_lines(x, 3) for t, x in zip(tasks, res)}
    out = {}
    for idx in ("noorig", "base"):
        s = ctx.searcher(method, emb, idx, alpha=alpha)
        s.prefetch([q for v in exp.values() for q in v] + [t["query"] for t in tasks])
        b = s.b
        for name, use in (("raw query", False), ("LLM query expansion", True)):
            rows = []
            for t in tasks:
                ranked = multi_query_ranked(b, s, t, exp[t["id"]]) if use else query_ranked(b, s, t, n=K)
                rows.append(row(t, ids_of(b, ranked)))
            out[f"{'origin-enriched index' if idx == 'base' else 'caption-only index'} + {name}"] = tag(rows, seed=ctx.seed, arm=name)
    return out, dict(calls=len(tasks), wall=wall)


# ============================================================================ M1
def m1_analysis(rows_by_arm: dict, key_ok="ok@10", key_rec="rec@10"):
    """Per class: measured CR vs E[p_c^m] (p_c = class item recall), and the intra-task correlation rho implied by the
    variance of the found fraction (beta-binomial: Var(X) = m p (1-p) [1 + (m-1) rho])."""
    out = {}
    for arm, rows in rows_by_arm.items():
        res = {}
        for c in CLASSES2 + ["ALL"]:
            rr = [r for r in rows if c == "ALL" or r["cls"] == c]
            if not rr:
                continue
            p = float(np.mean([r[key_rec] for r in rr]))
            meas = float(np.mean([r[key_ok] for r in rr]))
            pred = float(np.mean([p ** r["size"] for r in rr]))
            # per-task-size p (class x size) prediction
            bys = defaultdict(list)
            for r in rr:
                bys[r["size"]].append(r)
            pred_s = float(np.mean([np.mean([x[key_rec] for x in bys[r["size"]]]) ** r["size"] for r in rr]))
            num, den = 0.0, 0.0
            for m, xs in bys.items():
                if m < 2:
                    continue
                pm = np.mean([x[key_rec] for x in xs])
                if pm <= 0 or pm >= 1:
                    continue
                varx = np.var([x[key_rec] * m for x in xs])
                rho = (varx / (m * pm * (1 - pm)) - 1) / (m - 1)
                num += rho * len(xs); den += len(xs)
            res[c] = dict(p_item=p, measured=meas, pred_class_p=pred, pred_size_p=pred_s, rho=(num / den if den else float("nan")), n=len(rr))
        out[arm] = res
    return out


# ============================================================================ N5 router (cheap, regex) and M1 item-level model
MEDIA_RE = re.compile(r"\b(photos?|pics?|pictures?|images?|videos?|clips?|footage|recordings?|scans?|scanned|receipts?|pdf|document|report|whiteboard|chalkboard|album|shot|listing photos)\b", re.I)


def e8_router(ctx: Ctx, method="wsum", emb="bge-small", alpha=0.2):
    """N5: decide the pinned prefix per request with two regexes (batch-1 temporal router + a media regex).
    temporal or media -> query-only (no prefix); otherwise cards(<=3)+static slots (or cards only)."""
    A = Assembler(ctx, method, emb, alpha)
    A.prefetch(ctx.tasks)
    def route(t):
        if is_temporal_query(t["query"]) or MEDIA_RE.search(t["query"]):
            return "none"
        return "prefix"
    arms = {
        "router: temporal/media -> query-only, else cards+slots": lambda t: A.query_only(t) if route(t) == "none" else A.cards(t, 3, True),
        "router: temporal/media -> query-only, else cards": lambda t: A.query_only(t) if route(t) == "none" else A.cards(t, 3, False),
        "router: temporal/media -> cards, else cards+slots": lambda t: A.cards(t, 3, False) if route(t) == "none" else A.cards(t, 3, True),
    }
    out = {n: run_arm(ctx.tasks, f, ctx.seed, n) for n, f in arms.items()}
    acc = Counter((t["cls"], route(t)) for t in ctx.tasks)
    return out, {f"{c}|{r}": v for (c, r), v in acc.items()}


def m1_item_model(rows, key_found="found", classes=CLASSES2):
    """Item-specific independence model: p_i = leave-one-task-out success rate of required item i (same seed, same
    class, same arm); predicted CR for a task = prod_i p_i. Falls back to the class item recall when an item occurs once."""
    by = defaultdict(list)        # (seed, cls, item) -> list of (task id, found?)
    for r in rows:
        f = set(r.get(key_found, []))
        for it in r["_req"]:
            by[(r["seed"], r["cls"], it)].append((r["id"], it in f))
    cls_p = {c: np.mean([r["rec@10"] for r in rows if r["cls"] == c]) for c in classes}
    out = {}
    for c in classes + ["ALL"]:
        rr = [r for r in rows if c == "ALL" or r["cls"] == c]
        preds, used = [], 0
        for r in rr:
            p = 1.0
            for it in r["_req"]:
                obs = [ok for tid, ok in by[(r["seed"], r["cls"], it)] if tid != r["id"]]
                if obs:
                    p *= np.mean(obs); used += 1
                else:
                    p *= cls_p[r["cls"]]
            preds.append(p)
        out[c] = dict(measured=float(np.mean([r["ok@10"] for r in rr])), pred_item=float(np.mean(preds)), n=len(rr),
                      share_items_with_loo=used / max(1, sum(len(r["_req"]) for r in rr)))
    return out


def e8_oracle(ctx: Ctx, method="wsum", emb="bge-small", alpha=0.2):
    """Ceilings for structural assembly (M1 thesis, N4):
    - share of required items that are keyed facts (structurally reachable) vs free text / media;
    - oracle-entity cards: pin the cards of exactly the required fact entities (perfect linker), <=3 or all, then search;
    - oracle-facts: pin every required keyed fact (perfect slot contract), then search fills the rest of k=10."""
    A = Assembler(ctx, method, emb, alpha)
    A.prefetch(ctx.tasks)
    w, bc = ctx.w, ctx.bc
    def oracle_linker(t):
        return sorted(required_entities(ctx, t))
    def oracle_facts(t):
        b = ctx.b
        pre = [b.pos[r] for r in t["required"] if w.by_id[r]["type"] == "fact"]
        return ids_of(b, fill(pre, query_ranked(b, A.s, t, n=40), K)), None, ids_of(b, pre)
    def oracle_cards(C):
        def f(t):
            ids, cov, pre = A.cards(t, C, False, linker=oracle_linker)
            return ids, cov, pre
        return f
    arms = {"oracle linker: cards(<=3) + query": oracle_cards(3), "oracle linker: cards(all required entities) + query": oracle_cards(99),
            "oracle slots: every required keyed fact pinned + query": oracle_facts}
    out = {n: run_arm(ctx.tasks, f, ctx.seed, n) for n, f in arms.items()}
    share = defaultdict(lambda: [0, 0, 0])
    for t in ctx.tasks:
        for r in t["required"]:
            it = w.by_id[r]
            s = share[t["cls"]]
            s[0] += it["type"] == "fact"; s[1] += 1; s[2] += bool(it.get("media"))
    return out, {c: dict(fact=v[0] / v[1], media=v[2] / v[1], n=v[1]) for c, v in share.items()}
