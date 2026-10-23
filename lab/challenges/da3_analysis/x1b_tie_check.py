"""DA3-X1b: why did arm D (no fitted cross-partition component) change one top-50 list? Check for tie-breaking."""
import sys
sys.path.insert(0, "/home/claude/brainbench"); sys.path.insert(0, "/home/claude/challenges/da3_analysis")
import numpy as np
from bb.brain import World
from bb.common import NOW_DAY
from x1_noninterference import Arms
w = World()
hidden = [dict(id=f"secret_{j}", type="note", partition="owner", scope="finance/investments", title="",
               text=f"Private: refinance bridging loan Halyard equity release lender valuation discussion {j}",
               created_day=NOW_DAY, recorded_day=NOW_DAY, entities=["prop_halyard"]) for j in range(20)]
W, W2 = Arms(w.items), Arms(list(w.items) + hidden)
extra = ["refinance", "bridging loan lender", "Halyard equity valuation", "anything new about 18 Halyard Way?"]
for a in [i for i in w.identities if i != "owner"]:
    parts = set(w.identities[a]["partitions"])
    v1 = np.array([p in parts for p in W.ix.partition]); v2 = np.array([p in parts for p in W2.ix.partition])
    for q in [t["query"] for t in w.tasks if t["requester"] == a][:40] + extra:
        r1, s1 = W.rank("D", q, v1, 50); r2, s2 = W2.rank("D", q, v2, 50)
        if r1 != r2:
            diff = [(i, x, y, round(s1.get(x, -1), 6), round(s2.get(y, -1), 6)) for i, (x, y) in enumerate(zip(r1, r2)) if x != y]
            print(a, repr(q[:60]), diff[:6])
            b1 = W.ix.bm25(q, stats_mask=v1); b2 = W2.ix.bm25(q, stats_mask=v2)
            print(" bm25 identical on visible:", np.allclose(b1[:W.ix.N][v1[:W.ix.N]], b2[:W.ix.N][v2[:W.ix.N]]))
