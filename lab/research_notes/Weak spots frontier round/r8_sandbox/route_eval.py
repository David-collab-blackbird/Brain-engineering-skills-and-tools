# E-R8a: free local test of procedure retrieval by task intent.
# Arms: index text (name / name+desc / name+desc+triggers / body / desc+body), retriever (BM25 / dense bge-small / RRF hybrid),
# library size (gbrain-only 75 vs all three packs 146). Fixtures: gbrain routing-eval.jsonl (281 positive, 34 negative).
import json, re, math, sys, collections, random, numpy as np
random.seed(0); np.random.seed(0)
D = json.load(open(sys.argv[1]))
S_all = D["skills"]; FX = D["fixtures"]
tok = lambda t: re.findall(r"[a-z0-9]+", t.lower())
STOP = set("the a an and or of to in for on with is are be this that it as by from at use when you your i my me we our".split())
def toks(t): return [w for w in tok(t) if w not in STOP]
class BM25:
    def __init__(s, docs, k1=1.2, b=0.75):
        s.D=[toks(d) for d in docs]; s.N=len(s.D); s.avg=sum(map(len,s.D))/max(1,s.N); s.k1=k1; s.b=b
        s.df=collections.Counter(w for d in s.D for w in set(d)); s.tf=[collections.Counter(d) for d in s.D]
    def score(s,q):
        out=np.zeros(s.N)
        for w in set(toks(q)):
            if w not in s.df: continue
            idf=math.log(1+(s.N-s.df[w]+0.5)/(s.df[w]+0.5))
            for j,tf in enumerate(s.tf):
                f=tf.get(w)
                if f: out[j]+=idf*f*(s.k1+1)/(f+s.k1*(1-s.b+s.b*len(s.D[j])/s.avg))
        return out
def text(s, arm):
    if arm=="name": return s["name"].replace("-"," ")
    if arm=="name+desc": return s["name"].replace("-"," ")+". "+s["description"]
    if arm=="name+desc+trig": return s["name"].replace("-"," ")+". "+s["description"]+" Triggers: "+"; ".join(s["triggers"])
    if arm=="body": return s["body"][:6000]
    if arm=="desc+body": return s["name"].replace("-"," ")+". "+s["description"]+"\n"+s["body"][:6000]
from sentence_transformers import SentenceTransformer
import torch; torch.set_num_threads(2)
M = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu", cache_folder="/home/claude/models/hf/hub")
M.max_seq_length = 512
QP = "Represent this sentence for searching relevant passages: "
pos = [f for f in FX if f["expected"]]; neg = [f for f in FX if not f["expected"]]
qE = M.encode([QP+f["intent"] for f in FX], normalize_embeddings=True, batch_size=32)
qi = {id(f):i for i,f in enumerate(FX)}
def wilson(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
def rrf(*scs, k=60):
    out=np.zeros(len(scs[0]))
    for sc in scs:
        r=np.argsort(-sc); rank=np.empty_like(r); rank[r]=np.arange(len(r)); out+=1/(k+rank+1)
    return out
results=[]; detail={}
for lib in ["gbrain-only","all-packs"]:
    S=[s for s in S_all if lib=="all-packs" or s["pack"]=="gbrain"]
    ids=[s["id"] for s in S]
    for arm in ["name","name+desc","name+desc+trig","body","desc+body"]:
        docs=[text(s,arm) for s in S]
        bm=BM25(docs); E=M.encode(docs, normalize_embeddings=True, batch_size=16)
        for ret in ["bm25","dense","hybrid"]:
            hits={1:0,3:0,5:0}; top1_scores_pos=[]; top1_scores_neg=[]; perq=[]
            for f in FX:
                b=bm.score(f["intent"]); d=E@qE[qi[id(f)]]
                sc = b if ret=="bm25" else d if ret=="dense" else rrf(b,d)
                order=np.argsort(-sc); top=[ids[j] for j in order[:5]]
                ok=set([f["expected"]]+f["ok"]) if f["expected"] else set()
                if f["expected"]:
                    h1 = top[0] in ok
                    for k in (1,3,5): hits[k]+= any(t in ok for t in top[:k]) if k>1 else h1
                    top1_scores_pos.append(float(d[order[0]] if ret!="bm25" else b[order[0]]))
                    perq.append(int(h1))
                else:
                    top1_scores_neg.append(float(d[order[0]] if ret!="bm25" else b[order[0]]))
            n=len(pos)
            # abstention: AUC of top-1 score separating positives (any) from negatives
            P=np.array(top1_scores_pos); Ng=np.array(top1_scores_neg)
            auc=float((P[:,None]>Ng[None,:]).mean()+0.5*(P[:,None]==Ng[None,:]).mean())
            row=dict(lib=lib,arm=arm,ret=ret,n=n,hit1=hits[1]/n,hit3=hits[3]/n,hit5=hits[5]/n,
                     ci1=wilson(hits[1],n),ci5=wilson(hits[5],n),abstain_auc=auc)
            results.append(row); detail[(lib,arm,ret)]=perq
            print(f"{lib:11s} {arm:15s} {ret:6s} Hit@1={row['hit1']:.3f} [{row['ci1'][0]:.3f},{row['ci1'][1]:.3f}] Hit@3={row['hit3']:.3f} Hit@5={row['hit5']:.3f} [{row['ci5'][0]:.3f},{row['ci5'][1]:.3f}] negAUC={auc:.2f}", flush=True)
# paired McNemar: name+desc vs desc+body (hybrid, all-packs); gbrain-only vs all-packs (name+desc, hybrid)
def mcnemar(a,b):
    b01=sum(1 for x,y in zip(a,b) if x==0 and y==1); b10=sum(1 for x,y in zip(a,b) if x==1 and y==0)
    n=b01+b10
    if n==0: return b01,b10,1.0
    from math import comb
    k=min(b01,b10); p=sum(comb(n,i) for i in range(0,k+1))/2**n*2
    return b01,b10,min(1.0,p)
for (x,y) in [(("all-packs","name+desc","hybrid"),("all-packs","desc+body","hybrid")),
              (("all-packs","name+desc","dense"),("all-packs","desc+body","dense")),
              (("gbrain-only","name+desc","hybrid"),("all-packs","name+desc","hybrid")),
              (("gbrain-only","desc+body","hybrid"),("all-packs","desc+body","hybrid")),
              (("all-packs","name+desc","bm25"),("all-packs","name+desc","dense"))]:
    print("McNemar", x, "->", y, "(worse->better, better->worse, p)=", mcnemar(detail[x],detail[y]))
json.dump(results, open(sys.argv[2],"w"), indent=1)
