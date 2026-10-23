# DA2 analysis 3: how big is the "read it all" alternative? Partition/scope sizes in tokens, and entity-neighbourhood reach.
import json, collections, re, sys, statistics as st
sys.path.insert(0,'/home/claude/brainbench')
from bb.tasks import scope_group
S='/home/claude/brainbench/data_v02/s1/'
items={}
for l in open(S+'items.jsonl'):
    d=json.loads(l); items[d['id']]=d
tasks=[json.loads(l) for l in open(S+'tasks.jsonl')]
meta=json.load(open(S+'meta.json')); ident=meta['identities']
ents={json.loads(l)['id']:json.loads(l) for l in open(S+'entities.jsonl')}
live=[i for i in items.values() if not (i['type']=='fact' and i.get('superseded_by'))]
def ntok(i): return max(1,len(((i.get('title') or '')+' '+i['text']).split())*1.3)
tot=sum(ntok(i) for i in live)
print(f"live items {len(live)}, ~{tot/1000:.0f}k tokens total (text+title, words*1.3); mean {tot/len(live):.0f} tok/item")
bygrp=collections.defaultdict(list)
for i in live: bygrp[scope_group(i.get('scope'))].append(i)
for g,v in sorted(bygrp.items(), key=lambda x:-len(x[1])):
    print(f"  scope group {str(g):14s} items {len(v):5d}  ~{sum(ntok(i) for i in v)/1000:6.0f}k tok")
# entity tagging of required free-text items
CL=["decision_support","option_analysis","goal_tracking","preference_recommendation","cross_domain"]
# simple lexical linker
pats=[]
for e in ents.values():
    for a in e['aliases']:
        if len(a)>=3 and a.lower() not in ("me","training","portfolio","offset","reading list","my training","my reading"): pats.append((a.lower(),e['id']))
def link(q):
    ql=q.lower(); return {eid for a,eid in pats if re.search(r"(?<![a-z0-9])"+re.escape(a)+r"(?![a-z0-9])", ql)}
byent=collections.defaultdict(set)
for i in live:
    for e in (i.get('entities') or []): byent[e].add(i['id'])
res=collections.defaultdict(lambda: collections.defaultdict(list))
for t in tasks:
    if t['cls'] not in CL: continue
    parts=set(ident[t['requester']]['partitions'])
    req=set(t['required'])
    free=[r for r in req if items[r]['type']!='fact']
    tagged=[r for r in free if items[r].get('entities')]
    res[t['cls']]['free_tagged'].append(len(tagged)/max(1,len(free)) if free else None)
    L=link(t['query'])
    # oracle entities = union of entities on required items
    O=set(e for r in req for e in (items[r].get('entities') or []))
    for name,E in (('lex',L),('oracle',O)):
        nb={j for e in E for j in byent[e] if items[j]['partition'] in parts}
        res[t['cls']][name+'_size'].append(len(nb))
        res[t['cls']][name+'_tok'].append(sum(ntok(items[j]) for j in nb))
        res[t['cls']][name+'_allreq'].append(req<=nb)
        res[t['cls']][name+'_freereq'].append(sum(r in nb for r in free)/len(free) if free else None)
    # scope-group partition (visible ∩ required scope groups) size
    grps=set(t['required_scope_groups'])
    sp=[i for i in live if i['partition'] in parts and scope_group(i.get('scope')) in grps]
    res[t['cls']]['scopeunion_tok'].append(sum(ntok(i) for i in sp))
    vis=[i for i in live if i['partition'] in parts]
    res[t['cls']]['visible_tok'].append(sum(ntok(i) for i in vis))
def m(x): 
    x=[v for v in x if v is not None]; return st.mean(x) if x else float('nan')
def med(x): return st.median(x)
print("\nclass | free-text req items carrying entity tags | lexical-linked entity neighbourhood: median items / median ktok / all-required-inside / free-req inside | oracle-entity neighbourhood: same | union of required scope groups ktok (median) | all visible ktok (median)")
for c in CL:
    r=res[c]
    print(f"{c:26s} tagged {100*m(r['free_tagged']):5.1f}% | lex {med(r['lex_size']):5.0f} it {med(r['lex_tok'])/1000:6.1f}k all {100*m(r['lex_allreq']):5.1f}% free {100*m(r['lex_freereq']):5.1f}% | oracle {med(r['oracle_size']):5.0f} it {med(r['oracle_tok'])/1000:6.1f}k all {100*m(r['oracle_allreq']):5.1f}% free {100*m(r['oracle_freereq']):5.1f}% | scopes {med(r['scopeunion_tok'])/1000:6.0f}k | visible {med(r['visible_tok'])/1000:6.0f}k")
