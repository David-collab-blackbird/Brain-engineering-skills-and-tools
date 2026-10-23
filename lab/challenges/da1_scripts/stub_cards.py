"""DA1 innovation test: values-free card STUBS indexed (name + aliases + attribute labels, no values);
values compiled at read time. Compare against materialised cards (values in the indexed text). Seed 1, wsum bge-small a=.2.
Does NOT write to the shared embedding cache (stub vectors computed in memory)."""
import sys, copy, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx, CLASSES2
from bb.experiments2 import Assembler
from bb.brain import Brain
from bb.retrieval import item_text

ctx = Ctx(1, embedders=("bge-small",), lsa=False)
w = ctx.w; em = ctx.emb["bge-small"]
labels = collections.defaultdict(list)
for k in w.keys.values():
    labels[(k["entity"], k["partition"])].append(k["label"])
stubs = []
for d in ctx.cards:
    eid = d["entities"][0]; e = w.entities[eid]
    s = dict(d); s["text"] = f"{e['name']} ({', '.join(e['aliases'][1:])}). Facts held: {'; '.join(labels[(eid, d['partition'])])}."
    stubs.append(s)
bstub = Brain(w, extra_docs=stubs, lsa_dim=16)
assert bstub.ix.N == ctx.bc.ix.N and bstub.ids == ctx.bc.ids
Eb = ctx.E[("bge-small", "base")]
assert Eb.shape[0] == ctx.b.ix.N
V = em.model().encode([item_text(s, True) for s in stubs], batch_size=16, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
ctx2 = copy.copy(ctx); ctx2.E = dict(ctx.E); ctx2.bc = bstub; ctx2.E[("bge-small", "cards")] = np.vstack([Eb, V])
A1 = Assembler(ctx, "wsum", "bge-small", 0.2); A1.prefetch(ctx.tasks)
A2 = Assembler(ctx2, "wsum", "bge-small", 0.2)
res = collections.defaultdict(lambda: collections.defaultdict(list))
for t in ctx.tasks:
    req = set(t["required"])
    for name, A in (("materialised cards (values indexed)", A1), ("stub cards (no values indexed) + read-time values", A2)):
        ids, cov, pre = A.cards(t, 3)
        got = set(ids)
        for i in ids: got |= cov.get(i, set())
        res[name][t["cls"]].append(req <= got)
cols = CLASSES2 + ["ALL"]
print("arm".ljust(52) + "".join(c[:9].rjust(10) for c in cols))
for k, v in res.items():
    allv = sum((v[c] for c in CLASSES2), [])
    print(k.ljust(52) + "".join(("%.1f" % (100 * np.mean(v[c] if c != "ALL" else allv))).rjust(10) for c in cols))
a = sum((res["materialised cards (values indexed)"][c] for c in CLASSES2), []); b_ = sum((res["stub cards (no values indexed) + read-time values"][c] for c in CLASSES2), [])
print("paired: stub better", sum(1 for x, y in zip(a, b_) if y and not x), "worse", sum(1 for x, y in zip(a, b_) if x and not y))
