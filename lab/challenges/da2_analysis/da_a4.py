# DA2 analysis 4: does crediting organic substitutes (a note quoting the CURRENT value of a required fact) change pass rates?
# Note the scorer already credits entity cards as covering their facts (covers) -> asymmetric.
import sys, os, collections, time
os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,'/home/claude/brainbench')
from bb.ctx2 import Ctx, CLASSES2
from bb.experiments2 import Assembler
t0=time.time()
ctx=Ctx(1, embedders=("bge-small",), lsa=False)
A=Assembler(ctx, method="wsum", emb="bge-small", alpha=0.2)
w=ctx.w
quote=collections.defaultdict(set)   # head id -> items quoting it
for it in w.items:
    for f in it.get('fact_refs') or []:
        if w.head_of.get(f)==f: quote[f].add(it['id'])
print('built in', round(time.time()-t0), 's')
res=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
arms={'query-only':lambda t:A.query_only(t),'cards+slots':lambda t:A.cards(t, with_slots=True)}
for name,fn in arms.items():
    for t in ctx.tasks:
        ids,covers,_=fn(t)
        top=ids[:10]; got=set(top)
        if covers:
            for i in top: got|=covers.get(i,set())
        req=set(t['required'])
        strict=req<=got
        # substitute credit: a fact head counts if any top-10 item quotes its current value
        sub=set(got)
        for r in req:
            if r not in got and quote.get(r) and (quote[r] & set(top)): sub.add(r)
        res[name][t['cls']][t['set_id']].append((strict, req<=sub, len(req & got)/len(req), len(req&sub)/len(req)))
print('arm | class | strict CR@10 | substitute-credited CR@10 | item recall strict -> credited')
for name in arms:
    for c in CLASSES2:
        sets=res[name][c]
        def m(i): return 100*sum(sum(x[i] for x in v)/len(v) for v in sets.values())/len(sets)
        print(f"{name:12s} {c:26s} {m(0):5.1f} {m(1):5.1f} | {m(2):5.1f} -> {m(3):5.1f}  (n={len(sets)})")
print('done', round(time.time()-t0),'s')
