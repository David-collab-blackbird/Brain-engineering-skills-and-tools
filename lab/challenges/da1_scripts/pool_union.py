"""DA1 / ADR-005: when a reranker follows, fusion only decides the rerank POOL. Compare pool recall at equal pool size:
wsum (alpha .2) top-P vs RRF top-P vs union of BM25 top-P/2 and dense top-P/2 (round-robin fill to P)."""
import sys, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx, live, CLASSES2
from bb.retrieval import minmax, topn, rrf

ctx = Ctx(1, embedders=("bge-small",), lsa=False)
b = ctx.b; em = ctx.emb["bge-small"]; E = ctx.E[("bge-small", "base")]
em.queries(list(dict.fromkeys(t["query"] for t in ctx.tasks)))
Ps = (50, 100, 150)
res = collections.defaultdict(lambda: collections.defaultdict(list))
for t in ctx.tasks:
    m, temporal = live(b, t)
    req = set(t["required"])
    bm = b.ix.bm25(t["query"], stats_mask=b.access(t["requester"]))
    dv = E @ em.queries([t["query"]])[0]
    lb = b.forward(list(topn(bm, m & (bm > 0), 400)), temporal)
    ld = b.forward(list(topn(dv, m, 400)), temporal)
    ws = b.forward(list(topn(np.where(m, 0.2 * minmax(bm, m) + 0.8 * minmax(dv, m), -np.inf), m, 400)), temporal)
    rr = rrf([topn(bm, m & (bm > 0), 400), topn(dv, m, 400)], b.N)
    rr = b.forward(list(topn(np.where(m & (rr > 0), rr, -np.inf), m & (rr > 0), 400)), temporal)
    for P in Ps:
        u, i = [], 0
        while len(u) < P and (i < len(lb) or i < len(ld)):
            for L in (lb, ld):
                if i < len(L) and L[i] not in u and len(u) < P:
                    u.append(L[i])
            i += 1
        for name, pool in (("wsum", ws[:P]), ("rrf", rr[:P]), ("union", u)):
            got = req & set(b.ids[j] for j in pool)
            res[(name, P)][t["cls"]].append((len(got) == len(req), len(got) / len(req)))
            res[(name, P)]["ALL"].append((len(got) == len(req), len(got) / len(req)))
cols = CLASSES2 + ["ALL"]
print("pool CR (all required in pool) %, task-weighted, seed 1 | last col = ALL item recall")
print("arm".ljust(12) + "".join(c[:9].rjust(10) for c in cols) + "  itemrec")
for P in Ps:
    for name in ("wsum", "rrf", "union"):
        v = res[(name, P)]
        print(("%s@%d" % (name, P)).ljust(12) + "".join(("%.1f" % (100 * np.mean([x[0] for x in v[c]]))).rjust(10) for c in cols)
              + ("%.1f" % (100 * np.mean([x[1] for x in v["ALL"]]))).rjust(9))
