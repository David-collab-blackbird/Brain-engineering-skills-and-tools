# DA2 analysis 9: would an alias-writing scribe (U2) win in BrainBench "by construction"?
# Queries name entities with a random alias drawn from the same alias list a scribe would write into the search entry.
import json, collections, re
S='/home/claude/brainbench/data_v02/s1/'
items={}
for l in open(S+'items.jsonl'):
    d=json.loads(l); items[d['id']]=d
ents={}
for l in open(S+'entities.jsonl'):
    e=json.loads(l); ents[e['id']]=e
tasks=[json.loads(l) for l in open(S+'tasks.jsonl')]
STOP=set("the a an of and or to in on for at with my our is are be it this that what how do we i me".split())
def toks(s): return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP and len(t)>2}
CL=["decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain"]
st=collections.defaultdict(lambda:[0,0,0,0])
for t in tasks:
    if t['cls'] not in CL: continue
    q=toks(t['query'])
    for r in t['required']:
        it=items[r]
        if it['type']=='fact': continue
        base=toks((it.get('title') or '')+' '+it['text'])
        al=set()
        for e in it.get('entities') or []:
            for a in ents[e]['aliases']: al|=toks(a)
        s=st[t['cls']]; s[0]+=1
        s[1]+= bool(q & base)
        s[2]+= bool(q & (base|al))
        s[3]+= bool((q & al) - base)
for c in CL:
    n,b,ba,new=st[c]
    print(f"{c:26s} free-text required items {n:4d} | share overlapping the query: raw {100*b/n:5.1f}% -> raw+entity aliases {100*ba/n:5.1f}%  (items whose ONLY new overlap comes from alias list: {100*new/n:5.1f}%)")
