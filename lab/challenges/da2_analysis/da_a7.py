# DA2 analysis 7: candidate-recall ceiling for a "generous assembly -> reader selects" design.
# CR@K for K in {10,30,50,100,200} and approx token cost; arms: query-only, cards+slots (lexical linker), cards (oracle linker),
# plus "cards + entity neighbourhood (all visible items tagged with linked entities) + search" union.
import sys, os, collections, time
os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,'/home/claude/brainbench')
import numpy as np
from bb.ctx2 import Ctx, CLASSES2, query_ranked, fill, ids_of, live
from bb.experiments2 import Assembler, required_entities
from bb.retrieval import item_text
t0=time.time()
ctx=Ctx(1, embedders=("bge-small",), lsa=False)
A=Assembler(ctx, method="wsum", emb="bge-small", alpha=0.2)
w, bc = ctx.w, ctx.bc
tok=np.array([max(1,int(len(item_text(it,True).split())*1.3)) for it in bc.ix.items])
byent=collections.defaultdict(list)
for i,it in enumerate(bc.ix.items):
    if it.get('derived'): continue
    for e in it.get('entities') or []: byent[e].append(i)
KS=(10,30,50,100,200)
def evalr(ids,t,K):
    got=set(ids[:K])
    for i in ids[:K]: got|=ctx.covers.get(i,set())
    return set(t['required'])<=got
res=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
toks=collections.defaultdict(lambda: collections.defaultdict(list))
for t in ctx.tasks:
    ranked=query_ranked(bc, A.sc, t, n=260)
    arms={}
    arms['query-only']=ids_of(bc,ranked)
    pre=A.card_prefix(t,3,True)
    arms['cards+slots']=ids_of(bc,fill(pre,ranked,260))
    ents_o=required_entities(ctx,t)
    preo=A.card_prefix(t,3,False,(lambda tt: ents_o))
    arms['cards(oracle linker)']=ids_of(bc,fill(preo,ranked,260))
    # neighbourhood union (lexical linker): cards, then entity-tagged live visible items ranked by query score, then search
    ents=ctx.L.link(t['query'],t['requester'])
    m,temporal=live(bc,t)
    s=A.sc.fused(t['query'],t['requester'],m)
    nb=sorted({i for e in ents for i in byent[e] if m[i] and np.isfinite(s[i])}, key=lambda i:-s[i])
    arms['cards+slots+entity-nbhd']=ids_of(bc,fill(pre+[i for i in nb if i not in pre],ranked,260))
    for a,ids in arms.items():
        for K in KS:
            res[a][t['cls']][(t['set_id'],K)].append(evalr(ids,t,K))
            toks[a][K].append(sum(tok[bc.pos[i]] for i in ids[:K]))
for a in res:
    print('##',a, ' mean tokens @K:', ' '.join(f"{K}:{np.mean(toks[a][K]):.0f}" for K in KS))
    for c in CLASSES2:
        line=[]
        for K in KS:
            v=[np.mean(x) for (sid,k),x in res[a][c].items() if k==K]
            line.append(f"{100*np.mean(v):5.1f}")
        print(f"   {c:26s} CR@{KS}: "+' '.join(line))
print('t',round(time.time()-t0))
