# DA2 analysis 5: (a) equal-k vs equal-token budget (cards pack many facts into one "item");
# (b) entity-neighbourhood evidence arm ("N8 / structure for free text") and its sensitivity to entity-tag noise (extraction errors)
import sys, os, collections, time, random
os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,'/home/claude/brainbench')
import numpy as np
from bb.ctx2 import Ctx, CLASSES2, query_ranked, fill, ids_of
from bb.experiments2 import Assembler
from bb.retrieval import item_text
t0=time.time()
ctx=Ctx(1, embedders=("bge-small",), lsa=False)
A=Assembler(ctx, method="wsum", emb="bge-small", alpha=0.2)
w, bc = ctx.w, ctx.bc
def ntok(iid):
    it=bc.ix.items[bc.pos[iid]]
    return max(1,int(len(item_text(it,True).split())*1.3))
cardtok=[ntok(c['id']) for c in ctx.cards]
print('cards', len(cardtok), 'mean tok', round(np.mean(cardtok)), 'max', max(cardtok))
alltok=[ntok(i['id']) for i in w.items]
print('items mean tok (incl origin)', round(np.mean(alltok)))
# ---- (a) equal tokens
res=collections.defaultdict(lambda: collections.defaultdict(list))
budgets=[]
for t in ctx.tasks:
    ids,covers,pre=A.cards(t, with_slots=True)
    top=ids[:10]; got=set(top)
    for i in top: got|=covers.get(i,set())
    req=set(t['required'])
    B=sum(ntok(i) for i in top); budgets.append((t['cls'],B))
    q=ids_of(ctx.b, query_ranked(ctx.b, A.s, t, n=400))
    acc=0; sel=[]
    for i in q:
        if acc>=B: break
        sel.append(i); acc+=ntok(i)
    qo10=set(q[:10])
    res[t['cls']][t['set_id']].append((req<=got, req<=qo10, req<=set(sel), len(sel)))
print('class | cards+slots CR@10 | query-only CR@10 | query-only CR at the SAME token budget | mean tokens of cards+slots top-10 | mean k query-only needs')
bud=collections.defaultdict(list)
for c,B in budgets: bud[c].append(B)
for c in CLASSES2:
    sets=res[c]
    def m(i): return 100*sum(sum(x[i] for x in v)/len(v) for v in sets.values())/len(sets)
    kk=np.mean([x[3] for v in sets.values() for x in v])
    print(f"{c:26s} {m(0):5.1f} {m(1):5.1f} {m(2):5.1f}   tok {np.mean(bud[c]):6.0f}  k~{kk:5.1f}")
print('t',round(time.time()-t0))
