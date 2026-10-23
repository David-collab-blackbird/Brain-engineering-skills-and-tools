"""DA1 / ADR-006 alternative: BM25 with FROZEN EXTERNAL statistics (IDF + avgdl fitted on a different corpus: seed-2 world,
no shared documents) vs visible-set statistics (ADR-006 reference) vs global (leaky). Leak-free by construction and
needs no per-request df computation. Seed 1, BM25-only, CR@10 after forward-to-head."""
import sys, math, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.brain import World, Brain, is_temporal_query
from bb.ctx2 import CLASSES2
from bb.retrieval import tokenize, item_text, topn

w1 = World("/home/claude/brainbench/data_v02/s1"); b = Brain(w1, lsa_dim=16)
w2 = World("/home/claude/brainbench/data_v02/s2")
df2 = collections.Counter(); dl2 = []
for it in w2.items:
    toks = tokenize(item_text(it, True)); dl2.append(len(toks)); df2.update(set(toks))
N2 = len(w2.items); avgdl2 = float(np.mean(dl2))
inv = {v: k for k, v in b.ix.vocab.items()}
def bm25_frozen(q, k1=1.2, bb=0.75):
    s = np.zeros(b.N)
    for t in [b.ix.vocab[x] for x in tokenize(q) if x in b.ix.vocab]:
        col = b.ix.tf_csc.getcol(t); rows, tfv = col.indices, col.data
        d = df2.get(inv[t], 0); idf = math.log(1 + (N2 - d + 0.5) / (d + 0.5))
        s[rows] += idf * tfv * (k1 + 1) / (tfv + k1 * (1 - bb + bb * b.ix.dl[rows] / avgdl2))
    return s
tasks = [t for t in w1.tasks if t["cls"] in CLASSES2]
res = collections.defaultdict(lambda: collections.defaultdict(list)); oov = []
for t in tasks:
    temporal = is_temporal_query(t["query"]); acc = b.access(t["requester"])
    m = acc & ~b.is_super if not temporal else acc.copy()
    qt = [x for x in tokenize(t["query"]) if x in b.ix.vocab]; oov.append(np.mean([df2.get(x, 0) == 0 for x in qt]) if qt else 0)
    for name, s in (("visible-set stats (ADR-006 a)", b.ix.bm25(t["query"], stats_mask=acc)), ("global stats (leaky)", b.ix.bm25(t["query"])),
                    ("frozen external stats (seed-2 corpus)", bm25_frozen(t["query"]))):
        sc = np.where(m & (s > 0), s, -np.inf)
        ranked = b.forward(list(topn(sc, np.isfinite(sc), 40)), temporal)[:10]
        ok = set(t["required"]) <= set(b.ids[i] for i in ranked)
        res[name][t["cls"]].append(ok); res[name]["ALL"].append(ok)
print("share of query terms unseen in external corpus: %.2f" % np.mean(oov))
cols = CLASSES2 + ["ALL"]
print("arm".ljust(40) + "".join(c[:9].rjust(10) for c in cols))
for k, v in res.items():
    print(k.ljust(40) + "".join(("%.1f" % (100 * np.mean(v[c]))).rjust(10) for c in cols))
a = res["visible-set stats (ADR-006 a)"]["ALL"]; f = res["frozen external stats (seed-2 corpus)"]["ALL"]
print("paired frozen vs visible: better", sum(1 for x, y in zip(a, f) if y and not x), "worse", sum(1 for x, y in zip(a, f) if x and not y))
