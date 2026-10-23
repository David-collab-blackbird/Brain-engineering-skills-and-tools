import random, re, math, time, numpy as np, collections, sys, torch
torch.set_num_threads(2)
from sentence_transformers import SentenceTransformer
random.seed(7)
names=["Alice Moreno","Bilal Shah","Chen Wei","Dana Kowalski","Elif Demir","Femi Adeyemi","Grace Liu","Hugo Martin","Ines Costa","Jonas Berg","Kenji Sato","Lara Novak","Mateo Ruiz","Nadia Haddad","Omar Farouk","Priya Nair","Quinn Walsh","Rosa Ferreira","Sven Olsen","Tara Singh"]
devices=[("laptop","notebook computer"),("router","wifi box"),("printer","office printer"),("phone","mobile handset"),("monitor","display screen"),("tablet","ipad-style device"),("headset","headphones"),("server","rack machine")]
symptoms=[("overheats","gets very hot"),("will not boot","fails to start up"),("drops the connection","keeps losing network"),("shows a blank screen","displays nothing"),("makes a grinding noise","sounds like scraping metal"),("drains the battery","loses charge quickly")]
events=[("a firmware update","installing new firmware"),("a power cut","an electrical outage"),("being dropped","falling on the floor"),("a move to a new office","relocating desks")]
teams=["Hardware","Network","Field Ops","Desk Support"]
docs=[];Qid=[];Qpar=[]
used=set()
while len(docs)<800:
    n=random.choice(names); d=random.choice(devices); s=random.choice(symptoms); e=random.choice(events)
    key=(n,d[0],s[0],e[0])
    if key in used: continue
    used.add(key)
    tid=f"TCK-{random.randint(10000,99999)}-{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
    i=len(docs)
    docs.append(f"Ticket {tid}: customer {n} reported that the {d[0]} {s[0]} after {e[0]}. Assigned to {random.choice(teams)}. Priority P{random.randint(1,4)}.")
    if i<150:
        Qid.append((f"status of ticket {tid}",i))
        Qpar.append((f"{n.split()[0]}'s {d[1]} {s[1]} since {e[1]}",i))
print("docs",len(docs))
# BM25
tok=lambda t:re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*",t.lower())
D=[tok(d) for d in docs]; N=len(D); avg=sum(map(len,D))/N
df=collections.Counter(w for d in D for w in set(d))
def bm25(q,k1=1.2,b=0.75):
    qs=tok(q); sc=np.zeros(N)
    for j,d in enumerate(D):
        tf=collections.Counter(d)
        for w in qs:
            if w in tf:
                idf=math.log(1+(N-df[w]+0.5)/(df[w]+0.5)); f=tf[w]
                sc[j]+=idf*f*(k1+1)/(f+k1*(1-b+b*len(d)/avg))
    return sc
def evalr(S,Q):
    r1=r10=0
    for row,(q,g) in zip(S,Q):
        top=np.argsort(-row)[:10]; r1+=top[0]==g; r10+=g in top
    return r1/len(Q), r10/len(Q)
res={}
for name,Q in [("ID",Qid),("PARA",Qpar)]:
    S=np.stack([bm25(q) for q,_ in Q]); res[("BM25",name)]=evalr(S,Q); print("RESULT BM25",name,"R@1=%.3f R@10=%.3f"%res[("BM25",name)],flush=True)
def run(model_id, qfmt, label, doc_kwargs={}, q_kwargs={}):
    t=time.time(); m=SentenceTransformer(model_id, device="cpu", model_kwargs={"torch_dtype": torch.float32}); m.max_seq_length=64; print(label,"loaded %.0fs"%(time.time()-t),flush=True)
    E=m.encode(docs,batch_size=32,normalize_embeddings=True,**doc_kwargs)
    for name,Q in [("ID",Qid),("PARA",Qpar)]:
        qe=m.encode([qfmt(q) for q,_ in Q],batch_size=32,normalize_embeddings=True,**q_kwargs)
        res[(label,name)]=evalr(qe@E.T,Q); print("RESULT",label,name,"R@1=%.3f R@10=%.3f"%res[(label,name)],flush=True)
    print(label,"done in %.0fs"%(time.time()-t),flush=True)
run("BAAI/bge-small-en-v1.5", lambda q:"Represent this sentence for searching relevant passages: "+q, "bge-small (+query prefix)")
run("BAAI/bge-small-en-v1.5", lambda q:q, "bge-small (no prefix)")
inst="Instruct: Given a support request, retrieve the IT ticket that matches it\nQuery:"
run("Qwen/Qwen3-Embedding-0.6B", lambda q:inst+q, "Qwen3-0.6B (+instruction)")
run("Qwen/Qwen3-Embedding-0.6B", lambda q:q, "Qwen3-0.6B (no instruction)")
print("\n%-30s %-14s %-14s"%("model","ID R@1/R@10","PARA R@1/R@10"))
for lab in ["BM25","bge-small (+query prefix)","bge-small (no prefix)","Qwen3-0.6B (+instruction)","Qwen3-0.6B (no instruction)"]:
    a=res.get((lab,"ID"));b=res.get((lab,"PARA"))
    print("%-30s %.2f/%.2f      %.2f/%.2f"%(lab,a[0],a[1],b[0],b[1]))
