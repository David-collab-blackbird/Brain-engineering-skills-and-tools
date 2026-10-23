# E-R8a part 4: "System One" proxy: local cross-encoder reranks a hybrid top-10 shortlist (desc+body+examples, 2-fold), trigger-masked queries.
import json, re, sys, numpy as np, math, random, collections, time
src=open("route_eval3.py").read()
pre=src.split("S=S_all; ids=")[0]
exec(pre)
from sentence_transformers import CrossEncoder
CE = CrossEncoder("BAAI/bge-reranker-v2-m3", device="cpu", max_length=256, cache_folder="/home/claude/models/hf/hub")
S=S_all; ids=[s["id"] for s in S]
def short(s): return s["name"].replace("-"," ")+". "+s["description"]+"\n"+s["body"][:600]
c=collections.Counter(); base=collections.Counter(); cands_hit=0; n=0; t0=time.time()
for test_fold in (0,1):
    ex=collections.defaultdict(list)
    for f in folds[1-test_fold]: ex[f["expected"]].append(f["intent"])
    queries=[dict(f,intent=mask(f)) for f in folds[test_fold]]
    queries=[q for q in queries if len(toks(q["intent"]))>=3]
    random.Random(5).shuffle(queries); queries=queries[:60]
    docs=[text(s,"desc+body")+"\nExample requests: "+" | ".join(ex.get(s["id"],[])) for s in S]
    bm=BM25(docs); E=M.encode(docs,normalize_embeddings=True,batch_size=16)
    qE=M.encode([QP+q["intent"] for q in queries],normalize_embeddings=True,batch_size=32)
    for i,q in enumerate(queries):
        sc=rrf(bm.score(q["intent"]),E@qE[i]); top=list(np.argsort(-sc)[:10])
        ok=set([q["expected"]]+q["ok"]); n+=1
        cands_hit+=any(ids[j] in ok for j in top)
        pairs=[(q["intent"], short(S[j])+("\nExample requests: "+" | ".join(ex.get(S[j]["id"],[])[:6]))) for j in top]
        r=CE.predict(pairs, batch_size=10)
        order=[top[k] for k in np.argsort(-r)]
        for k in (1,3,5): c[k]+=any(ids[j] in ok for j in order[:k]); base[k]+=any(ids[j] in ok for j in top[:k])
        if n%10==0: print(n, "queries", round(time.time()-t0), "s", flush=True)
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; cc=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((cc-h)/d,(cc+h)/d)
print(f"BASELINE same queries: Hit@1={base[1]/n:.3f} Hit@3={base[3]/n:.3f} Hit@5={base[5]/n:.3f}")
print(f"n={n} shortlist recall@10={cands_hit/n:.3f}  reranked Hit@1={c[1]/n:.3f} {wilson(c[1],n)} Hit@3={c[3]/n:.3f} Hit@5={c[5]/n:.3f} {wilson(c[5],n)}")
