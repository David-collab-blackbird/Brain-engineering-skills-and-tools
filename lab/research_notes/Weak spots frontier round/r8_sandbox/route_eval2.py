# E-R8a part 2: split fixtures into "trigger-verbatim" (intent contains a trigger of its expected skill) vs "paraphrase"
# and re-score key arms; plus top-k sizing for a fetch-on-demand shortlist.
import json, re, sys, numpy as np, math
exec(open("route_eval.py").read().split("from sentence_transformers")[0])  # reuse BM25, text(), toks
from sentence_transformers import SentenceTransformer
import torch; torch.set_num_threads(2)
M = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu", cache_folder="/home/claude/models/hf/hub"); M.max_seq_length=512
QP="Represent this sentence for searching relevant passages: "
norm=lambda t:" ".join(re.findall(r"[a-z0-9]+",t.lower()))
byid={s["id"]:s for s in S_all}
pos=[f for f in FX if f["expected"]]
def mask(f):
    t=norm(f["intent"])
    for tr in sorted(byid[f["expected"]]["triggers"],key=lambda x:-len(norm(x))):
        nt=norm(tr)
        if nt: t=re.sub(r"\b"+re.escape(nt)+r"\b"," ",t)
    t=" ".join(t.split()); return t
verb=pos
para=[]
for f in pos:
    m=mask(f)
    if len([w for w in toks(m)])>=3: para.append(dict(f,intent=m))
print("positives",len(pos),"masked-kept",len(para)); print("examples:",[p["intent"] for p in para[:4]])
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
def rrf(*scs,k=60):
    out=np.zeros(len(scs[0]))
    for sc in scs:
        r=np.argsort(-sc); rank=np.empty_like(r); rank[r]=np.arange(len(r)); out+=1/(k+rank+1)
    return out
S=S_all; ids=[s["id"] for s in S]
for arm in ["name+desc","name+desc+trig","desc+body"]:
    docs=[text(s,arm) for s in S]; bm=BM25(docs); E=M.encode(docs,normalize_embeddings=True,batch_size=16)
    for subset,name in [(verb,"verbatim"),(para,"paraphrase")]:
        qE=M.encode([QP+f["intent"] for f in subset],normalize_embeddings=True,batch_size=32)
        for ret in ["bm25","dense","hybrid"]:
            h={1:0,3:0,5:0,10:0}
            for i,f in enumerate(subset):
                b=bm.score(f["intent"]); d=E@qE[i]; sc=b if ret=="bm25" else d if ret=="dense" else rrf(b,d)
                top=[ids[j] for j in np.argsort(-sc)[:10]]; ok=set([f["expected"]]+f["ok"])
                for k in h: h[k]+=any(t in ok for t in top[:k])
            n=len(subset); lo,hi=wilson(h[1],n); lo5,hi5=wilson(h[5],n); lo10,hi10=wilson(h[10],n)
            print(f"all-packs {arm:15s} {name:10s} {ret:6s} n={n} Hit@1={h[1]/n:.3f} [{lo:.2f},{hi:.2f}] Hit@3={h[3]/n:.3f} Hit@5={h[5]/n:.3f} [{lo5:.2f},{hi5:.2f}] Hit@10={h[10]/n:.3f} [{lo10:.2f},{hi10:.2f}]",flush=True)
