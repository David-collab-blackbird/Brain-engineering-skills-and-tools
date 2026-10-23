import json, collections, re
S='/home/claude/brainbench/data_v02/s1/'
items={}
for l in open(S+'items.jsonl'):
    d=json.loads(l); items[d['id']]=d
tasks=[json.loads(l) for l in open(S+'tasks.jsonl')]
ident=json.load(open(S+'meta.json'))['identities']
def toks(s): return set(re.findall(r"[a-z0-9$]+", s.lower()))
nf=[i for i in items.values() if i['type']!='fact']
tok={i['id']:toks((i.get('title') or '')+' '+i['text']) for i in nf}
inv=collections.defaultdict(set)
for iid,ts in tok.items():
    for t in ts: inv[t].add(iid)
def nd(iid,thr=0.5):
    ts=tok[iid]; c=collections.Counter()
    for t in ts:
        if len(inv[t])<300:
            for j in inv[t]: c[j]+=1
    return [j for j,n in c.items() if j!=iid and n/len(ts|tok[j])>=thr]
diff=same=0
for t in tasks:
    if t['cls'] not in ("decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain"): continue
    parts=set(ident[t['requester']]['partitions'])
    for r in t['required']:
        if items[r]['type']=='fact': continue
        for j in nd(r):
            if items[j]['partition'] not in parts: continue
            if set(items[j].get('entities') or [])!=set(items[r].get('entities') or []): diff+=1
            else: same+=1
print(f"near-duplicate pairs: different entity set {diff} ({100*diff/(diff+same):.0f}%), same entity set {same}")
