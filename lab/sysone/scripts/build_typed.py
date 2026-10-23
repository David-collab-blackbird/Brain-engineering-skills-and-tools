"""Convert the pinned LocalLLaMA/typed-decisions test split (rev c76749ec, sha256 4f294f21...) into our row format so the
same scorers can reproduce published numbers (implementation check: Julia-1 publishes 0.71/0.805/0.6775 on CPU fp32;
Laya base 0.360 per open-alternative-jev's reproduction).  Subsample: first 60 cases x all questions (deterministic).

  python3 -I build_typed.py
"""
import json

import pyarrow.parquet as pq

SRC = "/home/claude/sysone/data/ext/td_test.parquet"
OUT = "/home/claude/sysone/data/TD_test.jsonl"
allc = pq.read_table(SRC).to_pylist()
import collections as _c
byw = _c.defaultdict(list)
for c in allc:
    byw[c["id"].rsplit("_", 1)[0]].append(c)
cases = [c for w in sorted(byw) for c in byw[w][:15]]   # 15 cases per workflow (4 workflows) = 60 cases
rows = []
for case in cases:
    state = json.loads(case["state"])
    gold = json.loads(case["gold"])
    st = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
    for qid, q in json.loads(case["questions"]).items():
        kind = q["type"]
        crit = q.get("criteria")
        if kind == "noul":
            c = crit or {}
            opts = [["false", c.get("false")], ["true", c.get("true")]]   # None = no description (vendor default applies)
            keys = ["false", "true"]
        elif kind == "score":
            opts = [[str(i), v] for i, v in enumerate(crit)]
            keys = [str(i) for i in range(len(crit))]
        else:
            if isinstance(crit, list):
                crit = {k: None for k in crit}
            opts = [[k, v] for k, v in crit.items()]
            keys = list(crit)
        g = str(gold[qid]["label"]).lower()
        lab = keys.index(g) if g in keys else None
        if lab is None:
            continue
        rows.append(dict(id=f"TD-{case['id']}-{qid}", job="TD", group=case["id"], qtype=kind, state=st,
                         question=q["instructions"] if isinstance(q["instructions"], str) else json.dumps(q["instructions"]),
                         options=opts, label=lab, meta=dict(type=kind), parts={}))
with open(OUT, "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
import collections
print(len(rows), collections.Counter(r["qtype"] for r in rows))
