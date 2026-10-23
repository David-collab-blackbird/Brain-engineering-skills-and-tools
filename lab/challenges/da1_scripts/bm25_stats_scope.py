"""DA1: what an off-the-shelf Postgres BM25 extension would actually give.
visible-set stats (what BrainBench + ADR-006 assume; custom code) vs per-partition stats (pg_textsearch on a partitioned
table; scores from different IDF spaces are mixed for multi-partition requesters) vs global stats (leaks, E4)."""
import sys, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx, live, CLASSES2
from bb.retrieval import minmax, topn

ctx = Ctx(1, embedders=("bge-small",), lsa=False)
b = ctx.b; em = ctx.emb["bge-small"]; E = ctx.E[("bge-small", "base")]
em.queries(list(dict.fromkeys(t["query"] for t in ctx.tasks)))
res = collections.defaultdict(lambda: collections.defaultdict(list))
for t in ctx.tasks:
    m, temporal = live(b, t)
    req = set(t["required"])
    acc = b.access(t["requester"])
    dv = E @ em.queries([t["query"]])[0]
    nparts = len(set(ctx.w.identities[t["requester"]]["partitions"]))
    for mode in ("visible", "per_partition", "global"):
        if mode == "visible":
            bm = b.ix.bm25(t["query"], stats_mask=acc)
        elif mode == "per_partition":
            bm = b.ix.bm25(t["query"], per_partition=True)
        else:
            bm = b.ix.bm25(t["query"])
        for name, s in (("bm25", np.where(m & (bm > 0), bm, -np.inf)),
                        ("wsum", np.where(m, 0.2 * minmax(bm, m) + 0.8 * minmax(dv, m), -np.inf))):
            ranked = b.forward(list(topn(s, np.isfinite(s), 40)), temporal)[:10]
            ok = req <= set(b.ids[i] for i in ranked)
            res[(name, mode)][t["cls"]].append(ok)
            res[(name, mode)]["ALL"].append(ok)
            res[(name, mode)]["multi-partition requester" if nparts > 1 else "single-partition requester"].append(ok)
cols = CLASSES2 + ["ALL", "multi-partition requester", "single-partition requester"]
print("arm".ljust(22) + "".join(c[:10].rjust(11) for c in cols))
for k, v in res.items():
    print(("%s/%s" % k).ljust(22) + "".join(("%.1f" % (100 * sum(v[c]) / max(1, len(v[c])))).rjust(11) for c in cols))
print("n:", {c: len(res[("bm25", "visible")][c]) for c in cols})
