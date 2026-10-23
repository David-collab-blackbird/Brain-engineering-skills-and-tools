# DA2 analysis 6: "structure for free text" (the bet behind U1/N8): pin cards, then pin the top-E free-text items TAGGED with the linked
# entities (ranked by the query), then fill by search. Sweep entity-tag noise to simulate write-gate extraction error.
import sys, os, collections, time, random
os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,'/home/claude/brainbench')
import numpy as np
from bb.ctx2 import Ctx, CLASSES2, query_ranked, fill, ids_of, live
from bb.experiments2 import Assembler, required_entities
from bb.retrieval import topn
t0=time.time()
ctx=Ctx(1, embedders=("bge-small",), lsa=False)
A=Assembler(ctx, method="wsum", emb="bge-small", alpha=0.2)
w, bc = ctx.w, ctx.bc
COMPLEX=["decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain"]
tasks=[t for t in ctx.tasks if t['cls'] in COMPLEX]
isfree=np.array([(it['type'] not in ('fact',)) and not it.get('derived') for it in bc.ix.items])
ent_ids=sorted(w.entities)
def tagmap(p_drop, p_spur, seed=7):
    R=random.Random(seed); out={}
    for i,it in enumerate(bc.ix.items):
        if not isfree[i]: continue
        es=[e for e in (it.get('entities') or []) if R.random()>=p_drop]
        if R.random()<p_spur: es.append(R.choice(ent_ids))
        out[i]=set(es)
    inv=collections.defaultdict(set)
    for i,es in out.items():
        for e in es: inv[e].add(i)
    return inv
def arm(t, inv, E=4, C=3, oracle=False):
    ents = required_entities(ctx,t) if oracle else ctx.L.link(t["query"], t["requester"])
    pre = A.card_prefix(t, C, False, (lambda tt: ents))
    m,temporal = live(bc,t)
    acc = bc.access(t['requester'])
    s = A.sc.fused(t["query"], t["requester"], m)
    cand = set()
    for e in ents: cand |= inv.get(e,set())
    cand=[i for i in cand if acc[i] and m[i] and np.isfinite(s[i])]
    cand.sort(key=lambda i:-s[i])
    pre2 = pre + [i for i in cand[:E] if i not in pre]
    ranked = query_ranked(bc, A.sc, t, n=60)
    return ids_of(bc, fill(pre2, ranked, 10))
def score(ids, t):
    got=set(ids[:10])
    for i in ids[:10]: got|=ctx.covers.get(i,set())
    req=set(t['required']); return req<=got, len(req&got)/len(req)
def run(fn):
    res=collections.defaultdict(lambda: collections.defaultdict(list))
    for t in tasks:
        ok,rec=score(fn(t),t); res[t['cls']][t['set_id']].append((ok,rec))
    out={}
    for c in COMPLEX:
        sets=res[c]; out[c]=(100*np.mean([np.mean([x[0] for x in v]) for v in sets.values()]), 100*np.mean([np.mean([x[1] for x in v]) for v in sets.values()]))
    return out
rows={}
rows['cards(<=3)+query']=run(lambda t: A.cards(t)[0])
rows['cards+slots+query']=run(lambda t: A.cards(t, with_slots=True)[0])
for pd_,ps in ((0,0),(0.2,0.1),(0.4,0.2),(0.6,0.3)):
    inv=tagmap(pd_,ps)
    rows[f'cards+entity-evidence(E=4) tags drop {pd_} spur {ps}']=run(lambda t: arm(t,inv))
inv=tagmap(0,0)
rows['ORACLE linker cards+entity-evidence, clean tags']=run(lambda t: arm(t,inv,oracle=True))
inv=tagmap(0.4,0.2)
rows['ORACLE linker cards+entity-evidence, drop .4 spur .2']=run(lambda t: arm(t,inv,oracle=True))
print('arm | ' + ' | '.join(COMPLEX) + '   (CR@10 / item recall)')
for k,v in rows.items():
    print(f"{k:58s} " + '  '.join(f"{v[c][0]:5.1f}/{v[c][1]:4.1f}" for c in COMPLEX))
print('t',round(time.time()-t0))
