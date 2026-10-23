import json, collections
S='/home/claude/brainbench/data_v02/s1/'
items={}
for l in open(S+'items.jsonl'):
    d=json.loads(l); items[d['id']]=d
keys={json.loads(l)['key']:json.loads(l) for l in open(S+'keys.jsonl')}
tasks=[json.loads(l) for l in open(S+'tasks.jsonl')]
print('key families:', collections.Counter(k['family'] for k in keys.values()).most_common())
CL=["decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain"]
fam=collections.defaultdict(collections.Counter)
for t in tasks:
    if t['cls'] not in CL: continue
    for r in t['required']:
        it=items[r]
        f = keys[it['key']]['family'] if it['type']=='fact' else 'FREE:'+it['type']
        fam[t['cls']][f]+=1
for c in CL:
    tot=sum(fam[c].values())
    print(c, ' '.join(f"{k}:{100*v/tot:.0f}%" for k,v in fam[c].most_common()))
print()
gen=[k for k in keys.values() if k['family']=='generic']
print('generic examples:', [ (k['key'],k['label']) for k in gen[:25]])
# connector-plausible families vs extraction-dependent
CONN={'valuation','loan','rate','rent','lease_end','units','mvalue','revenue','price','cost','count','cash','retention','sessions','bodyweight','runtime','reading_count','pb','lift','borrowing'}
for c in CL:
    tot=0; conn=0; ext=0; free=0
    for t in tasks:
        if t['cls']!=c: continue
        for r in t['required']:
            it=items[r]; tot+=1
            if it['type']!='fact': free+=1
            elif keys[it['key']]['family'] in CONN: conn+=1
            else: ext+=1
    print(f"{c:26s} connector-plausible keyed {100*conn/tot:4.0f}% | keyed but would need free-text extraction (goal/plan/strategy/rule/status/supplier/...) {100*ext/tot:4.0f}% | free text {100*free/tot:4.0f}%")
