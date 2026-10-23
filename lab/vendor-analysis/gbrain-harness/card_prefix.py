"""Compute the batch-2 card prefix (cards(<=3), lexical linker, ACL-checked) per task, so it can be pinned in front of
GBrain's ranking ("our structure + GBrain ranker" arm). Uses /home/claude/brainbench code unchanged.
python3 -I card_prefix.py <seed> <task_ids.txt> <out.json>"""
import json
import sys

sys.path.insert(0, "/home/claude/brainbench")
from bb.ctx2 import Ctx  # noqa: E402

seed, ids_path, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
ids = set(open(ids_path).read().split())
ctx = Ctx(seed, embedders=(), lsa=False)
bc = ctx.bc
res = {}
for t in ctx.tasks:
    if t["id"] not in ids:
        continue
    ents = ctx.L.link(t["query"], t["requester"])
    pre = []
    for eid in ents:
        for cid in ctx.card_of.get(eid, []):
            if bc.access(t["requester"])[bc.pos[cid]] and cid not in pre and len(pre) < 3:
                pre.append(cid)
    res[t["id"]] = pre
json.dump({"prefix": res, "covers": {k: sorted(v) for k, v in ctx.covers.items()}}, open(out, "w"))
print(len(res), "tasks;", sum(1 for v in res.values() if v), "with >=1 card")
