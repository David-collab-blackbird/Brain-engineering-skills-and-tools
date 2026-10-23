"""DA1 check: are 'cards (<=3) + query' vs 'query-only' compared at equal reader budget?
Recomputes both arms on seed 1 (cached embeddings, wsum BM25+bge-small a=0.2) and compares at equal WORD budget."""
import sys, time, statistics, collections
sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx, query_ranked, CLASSES2
from bb.experiments2 import Assembler

t0 = time.time()
ctx = Ctx(1, embedders=("bge-small",), lsa=False)
A = Assembler(ctx, "wsum", "bge-small", 0.2)
A.prefetch(ctx.tasks)
print("ctx", round(time.time() - t0), "s", flush=True)

def words_b(b, iid):
    it = b.ix.items[b.pos[iid]]
    return len((it.get("title", "") + " " + it["text"]).split())

res = collections.defaultdict(lambda: collections.defaultdict(list))
card_words = []
for t in ctx.tasks:
    req = set(t["required"])
    ids, cov, pre = A.cards(t, 3)
    got = set(ids)
    for i in ids:
        got |= cov.get(i, set())
    ok_cards = req <= got
    W = sum(words_b(ctx.bc, i) for i in ids)
    for p in pre:
        card_words.append(words_b(ctx.bc, p))
    qr = [ctx.b.ids[i] for i in query_ranked(ctx.b, A.s, t, n=120)]
    cum, kk = 0, 0
    for i in qr:
        if cum >= W: break
        cum += words_b(ctx.b, i); kk += 1
    ok_q10 = req <= set(qr[:10])
    ok_qW = req <= set(qr[:kk])
    Wq10 = sum(words_b(ctx.b, i) for i in qr[:10])
    r = res[t["cls"]]
    r["cards"].append(ok_cards); r["q10"].append(ok_q10); r["qW"].append(ok_qW)
    r["W"].append(W); r["Wq10"].append(Wq10); r["kW"].append(kk); r["npre"].append(len(pre))
print("elapsed", round(time.time() - t0), "s")
print("pinned card words: mean %.1f median %.1f p90 %.1f max %d" % (statistics.mean(card_words), statistics.median(card_words),
      sorted(card_words)[int(.9 * len(card_words))], max(card_words)))
print("%-26s %6s %6s %6s %8s %8s %6s %5s" % ("class", "q@10", "cards", "q@=W", "words_c", "words_q", "k_eq", "pre"))
allr = collections.defaultdict(list)
for c in CLASSES2:
    r = res[c]
    for k in r: allr[k] += r[k]
    m = lambda x: 100 * sum(x) / len(x)
    print("%-26s %6.1f %6.1f %6.1f %8.0f %8.0f %6.1f %5.2f" % (c, m(r["q10"]), m(r["cards"]), m(r["qW"]), statistics.mean(r["W"]),
          statistics.mean(r["Wq10"]), statistics.mean(r["kW"]), statistics.mean(r["npre"])))
r = allr; m = lambda x: 100 * sum(x) / len(x)
print("%-26s %6.1f %6.1f %6.1f %8.0f %8.0f %6.1f %5.2f" % ("ALL (task-weighted)", m(r["q10"]), m(r["cards"]), m(r["qW"]), statistics.mean(r["W"]),
      statistics.mean(r["Wq10"]), statistics.mean(r["kW"]), statistics.mean(r["npre"])))
