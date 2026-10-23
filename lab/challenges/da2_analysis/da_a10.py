# DA2 analysis 10: entity-neighbourhood assembly (the U1 bet) under REALISTIC extraction error:
# errors concentrate on implicit mentions (entity tag present in gold but no alias of the entity in the item's text).
import sys, os, collections, time, random, re
os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,'/home/claude/brainbench')
import numpy as np
from bb.ctx2 import Ctx, CLASSES2, query_ranked, fill, ids_of, live
from bb.experiments2 import Assembler
from bb.retrieval import item_text
t0=time.time()
ctx=Ctx(1, embedders=("bge-small",), lsa=False)
A=Assembler(ctx, method="wsum", emb="bge-small", alpha=0.2)
w, bc = ctx.w, ctx.bc
COMPLEX=["decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain"]
tasks=[t for t in ctx.tasks if t['cls'] in COMPLEX]
ent_ids=sorted(w.entities)
def explicit(it,e):
    txt=item_text(it,True).lower()
    return any(len(a)>=3 and re.search(r"(?<![a-z0-9])"+re.escape(a.lower())+r"(?![a-z0-9])", txt) for a in w.entities[e]['aliases'])
expl={}
for i,it in enumerate(bc.ix.items):
    if it.get('derived') or it['type']=='fact': continue
    for e in it.get('entities') or []: expl[(i,e)]=explicit(it,e)
# implicit share among required free-text items
imp=collections.Counter(); tot=collections.Counter()
for t in tasks:
    for r in t['required']:
        it=w.by_id[r]
        if it['type']=='fact': continue
        i=bc.pos[r]
        for e in it.get('entities') or []:
            tot[t['cls']]+=1; imp[t['cls']]+= (not expl[(i,e)])
print('share of (required free-text item, entity) tags that are IMPLICIT (no alias in text):', {c: f"{100*imp[c]/tot[c]:.0f}%" for c in COMPLEX})
def tagmap(p_imp_drop, p_exp_drop, p_spur, seed=11):
    R=random.Random(seed); inv=collections.defaultdict(set)
    for (i,e),ex in expl.items():
        p = p_exp_drop if ex else p_imp_drop
        if R.random()>=p: inv[e].add(i)
    for i,it in enumerate(bc.ix.items):
        if it.get('derived') or it['type']=='fact': continue
        if R.random()<p_spur: inv[R.choice(ent_ids)].add(i)
    return inv
KS=(10,50,100)
def run(inv, label):
    res=collections.defaultdict(lambda: collections.defaultdict(list))
    for t in tasks:
        ranked=query_ranked(bc, A.sc, t, n=120)
        pre=A.card_prefix(t,3,True)
        ents=ctx.L.link(t['query'],t['requester'])
        m,temporal=live(bc,t)
        s=A.sc.fused(t['query'],t['requester'],m)
        nb=sorted({i for e in ents for i in inv.get(e,()) if m[i] and np.isfinite(s[i])}, key=lambda i:-s[i])
        ids=ids_of(bc,fill(pre+[i for i in nb if i not in pre],ranked,120))
        req=set(t['required'])
        for K in KS:
            got=set(ids[:K])
            for i in ids[:K]: got|=ctx.covers.get(i,set())
            res[(t['cls'],K)][t['set_id']].append(req<=got)
    line=label.ljust(52)
    for c in COMPLEX:
        line+=' '+'/'.join(f"{100*np.mean([np.mean(v) for v in res[(c,K)].values()]):.0f}" for K in KS)
    print(line, flush=True)
print('config'.ljust(52)+' '+'  '.join(f"{c[:10]}@10/50/100" for c in COMPLEX))
run(tagmap(0,0,0),'gold tags')
run(tagmap(0.5,0.05,0.05),'implicit miss 50%, explicit miss 5%, spurious 5%')
run(tagmap(0.8,0.1,0.1),'implicit miss 80%, explicit miss 10%, spurious 10%')
run(tagmap(1.0,0.0,0.0),'implicit miss 100% (string-match extractor)')
print('t',round(time.time()-t0))
