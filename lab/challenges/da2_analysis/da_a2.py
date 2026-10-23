# DA2 analysis 2: substitutability. For required keyed-fact heads, how many other accessible, live items quote the SAME current value (fact_refs -> head)?
# For required free-text items, how many near-duplicate items exist (high token Jaccard)?
import json, collections, re, sys
S='/home/claude/brainbench/data_v02/s1/'
items={}
for l in open(S+'items.jsonl'):
    d=json.loads(l); items[d['id']]=d
tasks=[json.loads(l) for l in open(S+'tasks.jsonl')]
meta=json.load(open(S+'meta.json'))
ident=meta['identities']
refs=collections.defaultdict(list)
for i in items.values():
    for r in (i.get('fact_refs') or []): refs[r].append(i['id'])
def toks(s): return set(re.findall(r"[a-z0-9$]+", s.lower()))
CL=["decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain","current_state"]
# free-text near duplicates: build token sets for non-fact items
nf=[i for i in items.values() if i['type'] not in ('fact',)]
tok={i['id']:toks((i.get('title') or '')+' '+i['text']) for i in nf}
inv=collections.defaultdict(set)
for iid,ts in tok.items():
    for t in ts: inv[t].add(iid)
def neardups(iid, thr=0.5):
    ts=tok[iid]; cand=collections.Counter()
    for t in ts:
        if len(inv[t])<300:
            for j in inv[t]: cand[j]+=1
    out=[]
    for j,c in cand.items():
        if j==iid: continue
        jac=c/len(ts|tok[j])
        if jac>=thr: out.append((round(jac,2),j))
    return sorted(out,reverse=True)
stats=collections.defaultdict(lambda: collections.Counter())
examples=[]
for t in tasks:
    if t['cls'] not in CL: continue
    parts=set(ident[t['requester']]['partitions'])
    for r in t['required']:
        it=items[r]
        if it['type']=='fact':
            subs=[j for j in refs.get(r,[]) if items[j]['partition'] in parts]
            stats[t['cls']]['fact_req']+=1
            if subs: stats[t['cls']]['fact_req_with_value_quote']+=1
        else:
            stats[t['cls']]['free_req']+=1
            nd=[x for x in neardups(r) if items[x[1]]['partition'] in parts]
            if nd:
                stats[t['cls']]['free_req_with_neardup']+=1
                if len(examples)<6 and t['cls'] in ('decision_support','preference_recommendation','cross_domain'): examples.append((t['cls'],it['text'][:120],[(x[0],items[x[1]]['type'],items[x[1]]['text'][:120]) for x in nd[:2]]))
for c in CL:
    s=stats[c]
    fr=s['fact_req'] or 1; fe=s['free_req'] or 1
    print(f"{c:28s} fact-req {s['fact_req']:5d}  with a note quoting the same current value: {100*s['fact_req_with_value_quote']/fr:5.1f}% | free-req {s['free_req']:5d} with near-dup (Jaccard>=.5): {100*s['free_req_with_neardup']/fe:5.1f}%")
for e in examples: print(e)
