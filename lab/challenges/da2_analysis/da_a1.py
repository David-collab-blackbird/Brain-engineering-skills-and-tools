# DA2 analysis 1: harshness of all-or-nothing; tolerance of one miss; by arm & class (from e8c/e8e/e8d pickles)
import pickle, sys, collections, json
sys.path.insert(0, '/home/claude/brainbench')
B='/home/claude/brainbench/results_v02/'
d=pickle.load(open(B+'e8c.pkl','rb'))['rows']
e=pickle.load(open(B+'e8e.pkl','rb'))['rows']
r=pickle.load(open(B+'e8d.pkl','rb'))['rows']
arms={'query-only':d,'cards(<=3) + query':d,'cards(<=3) + static slots + query':d,
      'oracle slots: every required keyed fact pinned + query':e,
      'router: temporal/media -> query-only, else cards+slots':r}
CL=["decision_support","option_analysis","current_state","temporal_change","goal_tracking","preference_recommendation","cross_domain","multimodal"]
out={}
for arm,src in arms.items():
    # mean over distinct sets: per (seed,set_id) mean of indicator
    agg=collections.defaultdict(lambda: collections.defaultdict(list))
    for seed in (1,2,3):
        for row in src[seed][arm]:
            m=int(row['size']); rec=float(row['rec@10']); found=round(rec*m)
            agg[row['cls']][(seed,row['set_id'])].append((found==m, found>=m-1, rec, found>=max(1,round(0.8*m)) ))
    res={}
    for c in CL:
        sets=agg[c]
        def mean(i): 
            return 100*sum(sum(x[i] for x in v)/len(v) for v in sets.values())/len(sets)
        res[c]=(round(mean(0),1), round(mean(1),1), round(mean(3),1), round(mean(2),1))
    out[arm]=res
print("arm | class | all-required | tolerate-1-miss | >=80% items | item recall")
for arm,res in out.items():
    print('##',arm)
    for c,v in res.items(): print(f"  {c:28s} {v[0]:6.1f} {v[1]:6.1f} {v[2]:6.1f} {v[3]:6.1f}")
