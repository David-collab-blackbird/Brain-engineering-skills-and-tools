"""DA1 extra checks (seed 1, wsum BM25+bge-small a=0.2):
 (1) ADR-006 option (b): per-partition BM25 lists merged by RRF (no hidden counts) vs visible-set stats.
 (2) Read-time fact-level pinning (N12 / DA1 innovation 2) vs whole materialised cards, at EQUAL word budget."""
import sys, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx, live, query_ranked, CLASSES2
from bb.experiments2 import Assembler
from bb.retrieval import minmax, topn, rrf

ctx = Ctx(1, embedders=("bge-small",), lsa=False)
A = Assembler(ctx, "wsum", "bge-small", 0.2); A.prefetch(ctx.tasks)
b, bc, w = ctx.b, ctx.bc, ctx.w
em = ctx.emb["bge-small"]; E = ctx.E[("bge-small", "base")]
def words(bb, iid):
    it = bb.ix.items[bb.pos[iid]]; return len((it.get("title", "") + " " + it["text"]).split())
res = collections.defaultdict(lambda: collections.defaultdict(list))
for t in ctx.tasks:
    req = set(t["required"]); m, temporal = live(b, t); acc = b.access(t["requester"])
    # (1) per-partition BM25 lists -> RRF
    parts = sorted(set(w.identities[t["requester"]]["partitions"]))
    lists = []
    for p in parts:
        pm = (b.ix.partition == p)
        sc = b.ix._bm25_core([b.ix.vocab[x] for x in __import__("bb.retrieval", fromlist=["tokenize"]).tokenize(t["query"]) if x in b.ix.vocab], pm, 1.2, 0.75) if True else None
        mm = m & pm & (sc > 0)
        if mm.any(): lists.append(topn(sc, mm, 200))
    if lists:
        r = rrf(lists, b.N); s = np.where(m & (r > 0), r, -np.inf)
        ranked = b.forward(list(topn(s, np.isfinite(s), 40)), temporal)[:10]
    else:
        ranked = []
    res["bm25 per-partition lists + RRF"][t["cls"]].append(req <= set(b.ids[i] for i in ranked))
    bm = b.ix.bm25(t["query"], stats_mask=acc); s = np.where(m & (bm > 0), bm, -np.inf)
    ranked = b.forward(list(topn(s, np.isfinite(s), 40)), temporal)[:10]
    res["bm25 visible-set stats"][t["cls"]].append(req <= set(b.ids[i] for i in ranked))
    # (2) cards vs fact-level pinning at equal words
    ids, cov, pre = A.cards(t, 3)
    got = set(ids)
    for i in ids: got |= cov.get(i, set())
    res["cards(<=3)+query @k=10"][t["cls"]].append(req <= got)
    Wtot = sum(words(bc, i) for i in ids); Wpre = sum(words(bc, i) for i in pre)
    dv = E @ em.queries([t["query"]])[0]
    score = 0.2 * minmax(bm, m) + 0.8 * minmax(dv, m)
    ents = [e for e in ctx.L.link(t["query"], t["requester"])]
    cand = []
    for e in ents:
        for kk in ctx.L.keys_by_entity[e]:
            hh = kk["versions"][-1]
            if acc[b.pos[hh]]: cand.append((-score[b.pos[hh]], hh))
    cand.sort()
    out, cw = [], 0
    for _, hh in cand:
        if cw >= Wpre: break
        out.append(hh); cw += words(b, hh)
    for i in query_ranked(b, A.s, t, n=150):
        if cw >= Wtot: break
        iid = b.ids[i]
        if iid not in out: out.append(iid); cw += words(b, iid)
    res["fact-level pinning (read-time) @equal words"][t["cls"]].append(req <= set(out))
    out2, cw = [], 0
    for i in query_ranked(b, A.s, t, n=150):
        if cw >= Wtot: break
        out2.append(b.ids[i]); cw += words(b, b.ids[i])
    res["query-only @equal words"][t["cls"]].append(req <= set(out2))
cols = CLASSES2 + ["ALL"]
print("arm".ljust(46) + "".join(c[:9].rjust(10) for c in cols))
for k, v in res.items():
    allv = sum((v[c] for c in CLASSES2), [])
    print(k.ljust(46) + "".join(("%.1f" % (100 * np.mean(v[c] if c != "ALL" else allv))).rjust(10) for c in cols))
