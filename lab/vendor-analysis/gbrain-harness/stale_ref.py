"""Same-world stale-probe comparator: batch-2 first stage wsum(BM25+bge-small, alpha=0.2) on the stale probes GBrain ran,
under (a) add-only (every version live), (b) keyed (superseded versions not live), (c) keyed + forward-to-head.
Writes run-format jsonl so score.py computes identical E1 metrics.  python3 card... stale_ref.py <seed> <task_ids> <outprefix>"""
import json
import sys

sys.path.insert(0, "/home/claude/brainbench")
import numpy as np  # noqa: E402
from bb.ctx2 import Ctx  # noqa: E402

seed, ids_path, outp = int(sys.argv[1]), sys.argv[2], sys.argv[3]
keep = set(open(ids_path).read().split())
ctx = Ctx(seed, embedders=("bge-small",), lsa=False)
b = ctx.b
s = ctx.searcher("wsum", "bge-small", alpha=0.2)
probes = [t for t in ctx.w.tasks if t["cls"] == "stale_probe" and t["id"] in keep]
s.prefetch([t["query"] for t in probes])
outs = {k: open(f"{outp}_{k}.jsonl", "w") for k in ("addonly", "keyed", "keyedfwd")}
for t in probes:
    acc = b.access(t["requester"])
    for name, m, fwd in (("addonly", acc, False), ("keyed", acc & ~b.is_super, False), ("keyedfwd", acc & ~b.is_super, True)):
        ranked = s.rank(t["query"], t["requester"], m, n=120)
        if fwd:
            ranked = b.forward(ranked, temporal=False)
        ids = [b.ids[i] for i in ranked][:100]
        outs[name].write(json.dumps(dict(id=t["id"], cls=t["cls"], requester=t["requester"], ids=ids, srcs=[b.ix.items[b.pos[i]]["partition"].replace("/", "-") for i in ids], ms=0, err=None)) + "\n")
print(len(probes), "probes")
