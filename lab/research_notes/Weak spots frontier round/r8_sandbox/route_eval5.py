# E-R8a part 5: does a declared scope (library narrowed to the functional area, here = the RESOLVER.md section) lift routing on trigger-masked requests?
# Oracle scope (upper bound). BM25 + dense + hybrid on desc+body; 146-skill library vs in-scope subset (gbrain skills in the expected skill's section).
import json, re, sys, numpy as np, math, random, collections
src=open("route_eval3.py").read(); exec(src.split("S=S_all; ids=")[0])
res=open("/home/claude/vendor-skills/gbrain-vendor/gbrain/skills/RESOLVER.md").read()
sec=None; sec_of={}
for line in res.splitlines():
    if line.startswith("## "): sec=line[3:].strip(); continue
    for m in re.finditer(r"skills/([a-z0-9-]+)/SKILL\.md", line):
        sec_of.setdefault("gbrain:"+m.group(1), sec)
S=S_all; ids=[s["id"] for s in S]
queries=[dict(f,intent=mask(f)) for f in FX if f["expected"]]
queries=[q for q in queries if len(toks(q["intent"]))>=3 and q["expected"] in sec_of]
print("queries",len(queries),"sections",collections.Counter(sec_of[q["expected"]] for q in queries).most_common())
docs=[text(s,"desc+body") for s in S]; bm=BM25(docs); E=M.encode(docs,normalize_embeddings=True,batch_size=16)
qE=M.encode([QP+q["intent"] for q in queries],normalize_embeddings=True,batch_size=32)
def rrf(*scs,k=60):
    out=np.zeros(len(scs[0]))
    for sc in scs:
        r=np.argsort(-sc); rank=np.empty_like(r); rank[r]=np.arange(len(r)); out+=1/(k+rank+1)
    return out
def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
agg=collections.defaultdict(collections.Counter); sizes=[]
for i,q in enumerate(queries):
    b=bm.score(q["intent"]); d=E@qE[i]; ok=set([q["expected"]]+q["ok"])
    inscope=np.array([sec_of.get(x)==sec_of[q["expected"]] for x in ids]); sizes.append(int(inscope.sum()))
    for ret in ["bm25","dense","hybrid"]:
        for scope in ["none","declared"]:
            if scope=="none": sc = b if ret=="bm25" else d if ret=="dense" else rrf(b,d)
            else:
                idx=np.where(inscope)[0]; bb=b[idx]; dd=d[idx]
                sc_sub = bb if ret=="bm25" else dd if ret=="dense" else rrf(bb,dd)
                sc=np.full(len(ids),-1e9); sc[idx]=sc_sub
            top=[ids[j] for j in np.argsort(-sc)[:5]]; c=agg[(ret,scope)]; c["n"]+=1
            for k in (1,3,5): c[k]+=any(t in ok for t in top[:k])
print("in-scope library size median",int(np.median(sizes)),"min",min(sizes),"max",max(sizes))
for (ret,scope),c in sorted(agg.items()):
    n=c["n"]; print(f"{ret:6s} scope={scope:8s} n={n} Hit@1={c[1]/n:.3f} {tuple(round(x,2) for x in wilson(c[1],n))} Hit@3={c[3]/n:.3f} Hit@5={c[5]/n:.3f} {tuple(round(x,2) for x in wilson(c[5],n))}")
