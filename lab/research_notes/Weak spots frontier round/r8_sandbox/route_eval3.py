# E-R8a part 3: does harvested request vocabulary (U2 applied to procedures) help retrieval of held-out, trigger-masked requests?
# 2-fold split per skill: fold A fixtures become "example requests" stored in the procedure's searchable entry; fold B (trigger-masked) are queries; then swap.
import json, re, sys, numpy as np, math, random
exec(open("route_eval.py").read().split("from sentence_transformers")[0])
exec(open("route_eval2.py").read().split("def mask(f):")[1].split("verb=pos")[0].join(["def mask(f):",""]) if False else "")
from sentence_transformers import SentenceTransformer
import torch; torch.set_num_threads(2)
M = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu", cache_folder="/home/claude/models/hf/hub"); M.max_seq_length=512
QP="Represent this sentence for searching relevant passages: "
norm=lambda t:" ".join(re.findall(r"[a-z0-9]+",t.lower()))
byid={s["id"]:s for s in S_all}
def mask(f):
    t=norm(f["intent"])
    for tr in sorted(byid[f["expected"]]["triggers"],key=lambda x:-len(norm(x))):
        nt=norm(tr)
        if nt: t=re.sub(r"\b"+re.escape(nt)+r"\b"," ",t)
    return " ".join(t.split())
random.seed(1)
pos=[f for f in FX if f["expected"]]
by=collections.defaultdict(list)
for f in pos: by[f["expected"]].append(f)
folds={0:[],1:[]}
for k,v in by.items():
    v=v[:]; random.shuffle(v)
    for i,f in enumerate(v): folds[i%2].append(f)
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
def rrf(*scs,k=60):
    out=np.zeros(len(scs[0]))
    for sc in scs:
        r=np.argsort(-sc); rank=np.empty_like(r); rank[r]=np.arange(len(r)); out+=1/(k+rank+1)
    return out
S=S_all; ids=[s["id"] for s in S]
agg=collections.defaultdict(lambda: collections.Counter()); per=collections.defaultdict(list)
for test_fold in (0,1):
    ex=collections.defaultdict(list)
    for f in folds[1-test_fold]: ex[f["expected"]].append(f["intent"])
    queries=[dict(f,intent=mask(f)) for f in folds[test_fold]]
    queries=[q for q in queries if len(toks(q["intent"]))>=3]
    qE=M.encode([QP+q["intent"] for q in queries],normalize_embeddings=True,batch_size=32)
    for arm in ["name+desc","name+desc+examples","desc+body","desc+body+examples"]:
        base="desc+body" if arm.startswith("desc+body") else "name+desc"
        docs=[text(s,base)+(("\nExample requests: "+" | ".join(ex.get(s["id"],[]))) if arm.endswith("examples") else "") for s in S]
        bm=BM25(docs); E=M.encode(docs,normalize_embeddings=True,batch_size=16)
        for ret in ["bm25","dense","hybrid"]:
            for i,q in enumerate(queries):
                b=bm.score(q["intent"]); d=E@qE[i]; sc=b if ret=="bm25" else d if ret=="dense" else rrf(b,d)
                top=[ids[j] for j in np.argsort(-sc)[:10]]; ok=set([q["expected"]]+q["ok"])
                c=agg[(arm,ret)]; c["n"]+=1
                for k in (1,3,5,10): c[k]+=any(t in ok for t in top[:k])
                per[(arm,ret)].append(int(any(t in ok for t in top[:5])))
for (arm,ret),c in agg.items():
    n=c["n"]; lo,hi=wilson(c[5],n)
    print(f"{arm:20s} {ret:6s} n={n} Hit@1={c[1]/n:.3f} Hit@3={c[3]/n:.3f} Hit@5={c[5]/n:.3f} [{lo:.2f},{hi:.2f}] Hit@10={c[10]/n:.3f}")
from math import comb
def mcn(a,b):
    b01=sum(1 for x,y in zip(a,b) if x==0 and y==1); b10=sum(1 for x,y in zip(a,b) if x==1 and y==0); n=b01+b10
    k=min(b01,b10); return b01,b10,(min(1.0,2*sum(comb(n,i) for i in range(k+1))/2**n) if n else 1.0)
for r in ["bm25","dense","hybrid"]:
    print("McNemar Hit@5", r, "name+desc -> +examples", mcn(per[("name+desc",r)],per[("name+desc+examples",r)]))
    print("McNemar Hit@5", r, "desc+body -> +examples", mcn(per[("desc+body",r)],per[("desc+body+examples",r)]))
