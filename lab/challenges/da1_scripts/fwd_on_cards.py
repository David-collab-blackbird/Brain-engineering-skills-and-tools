"""DA1 / ADR-009: does mention forwarding still add anything ON TOP OF cards (+N5 router)? Seed 1, wsum bge-small a=.2, k=10."""
import sys, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx, query_ranked, fill, ids_of, CLASSES2
from bb.experiments2 import Assembler
from bb.brain import is_temporal_query
import re
MEDIA = re.compile(r"\b(photo|picture|pic|image|video|clip|footage|scan|screenshot|whiteboard|recording|page)\b", re.I)
ctx = Ctx(1, embedders=("bge-small",), lsa=False)
A = Assembler(ctx, "wsum", "bge-small", 0.2); A.prefetch(ctx.tasks)
b, bc, w = ctx.b, ctx.bc, ctx.w
def fwd_fill(t, pre, k=10):
    acc = bc.access(t["requester"]); out = list(pre)
    covered = set()
    for p_ in pre: covered |= ctx.covers.get(bc.ids[p_], set())
    for i in query_ranked(bc, A.sc, t, n=k + 30):
        for j in [i] + [bc.pos[w.head_of[f]] for f in bc.ix.items[i].get("fact_refs", []) if f in w.head_of]:
            if j not in out and acc[j] and len(out) < k and bc.ids[j] not in covered: out.append(j)
        if len(out) >= k: break
    return out
res = collections.defaultdict(lambda: collections.defaultdict(list))
for t in ctx.tasks:
    req = set(t["required"]); route_none = is_temporal_query(t["query"]) or bool(MEDIA.search(t["query"]))
    for name in ("router cards+slots", "router cards+slots + mention fwd"):
        if route_none:
            ids = A.query_only(t)[0] if "fwd" not in name else A.mention_fwd(t)[0]
            if "fwd" in name and is_temporal_query(t["query"]): ids = A.query_only(t)[0]   # ADR-009: skip fwd for temporal/media
            if "fwd" in name and MEDIA.search(t["query"]): ids = A.query_only(t)[0]
            got = set(ids)
        else:
            pre = A.card_prefix(t, 3, True)
            idx = fill(pre, query_ranked(bc, A.sc, t, n=40), 10) if "fwd" not in name else fwd_fill(t, pre)
            ids = ids_of(bc, idx); got = set(ids)
            for i in ids: got |= ctx.covers.get(i, set())
        res[name][t["cls"]].append(req <= got)
cols = CLASSES2 + ["ALL"]
print("arm".ljust(36) + "".join(c[:9].rjust(10) for c in cols))
for k, v in res.items():
    allv = sum((v[c] for c in CLASSES2), [])
    print(k.ljust(36) + "".join(("%.1f" % (100 * np.mean(v[c] if c != "ALL" else allv))).rjust(10) for c in cols))
a = sum((res["router cards+slots"][c] for c in CLASSES2), []); f = sum((res["router cards+slots + mention fwd"][c] for c in CLASSES2), [])
print("paired fwd vs no fwd: better", sum(1 for x, y in zip(a, f) if y and not x), "worse", sum(1 for x, y in zip(a, f) if x and not y))
