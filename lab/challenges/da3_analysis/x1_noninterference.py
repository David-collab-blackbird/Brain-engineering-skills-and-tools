"""DA3-X1: twin-world noninterference test vs the canary monitor.

Question: does the canary monitor (ADR-007 item 7, I11) detect side channels that do not return a
hidden item? The charter (s3a) forbids leakage "even in ranking, snippets, counts". A noninterference
test (Goguen-Meseguer) asks instead: if only rows the requester cannot see change, does anything the
requester can observe change?

World W  = BrainBench v0 seed data (data/).
World W' = W plus M hidden owner-partition notes about a chosen topic (the "secret": e.g. that the
           owner is planning a refinance). Nothing visible to the attacker changes.
Attacker = each non-owner identity (partners, household, members), using its own task queries plus
           probe queries.

Retriever arms (all pre-filter to the requester's visible rows, so no hidden row is ever returned):
  A  BM25 global statistics                         (known leak, E4)
  B  BM25 visible-set statistics                    (ADR-006 reference)
  C  RRF(BM25 visible-set, LSA fitted on ALL rows)  (BrainBench default Searcher; "fitted across partitions")
  D  RRF(BM25 visible-set, LSA fitted on public rows only = frozen/external stand-in)

Observables per query: top-10 ID list, top-50 ID list, visible-set scores.
Canary monitor: per arm, probe from every non-entitled identity; alarm if a canary is returned.
Run:  cd /home/claude/brainbench && python3 -I ../challenges/da3_analysis/x1_noninterference.py
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, "/home/claude/brainbench")
import numpy as np  # noqa: E402
from sklearn.decomposition import TruncatedSVD  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.preprocessing import normalize  # noqa: E402

from bb.brain import World  # noqa: E402
from bb.common import NOW_DAY, tokenize  # noqa: E402
from bb.retrieval import Index, rrf, topn  # noqa: E402

LSA_DIM = 64
OUT = "/home/claude/challenges/da3_analysis/x1_results.json"


class Arms:
    def __init__(self, items, public_parts=("public/gym",)):
        self.ix = Index(items, with_origin=True, lsa_dim=LSA_DIM)
        self.items = self.ix.items
        # D: LSA fitted only on public rows (stand-in for a frozen external model; identical in W and W')
        pub = [i for i, it in enumerate(self.items) if it["partition"] in public_parts]
        self.vec_pub = TfidfVectorizer(analyzer=tokenize, sublinear_tf=True)
        Xp = self.vec_pub.fit_transform([self.ix.texts[i] for i in pub])
        self.svd_pub = TruncatedSVD(n_components=min(LSA_DIM, Xp.shape[1] - 1, Xp.shape[0] - 1),
                                    random_state=0, n_iter=7).fit(Xp)
        self.lsa_pub = normalize(self.svd_pub.transform(self.vec_pub.transform(self.ix.texts))).astype(np.float32)

    def scores(self, arm, q, vis):
        ix = self.ix
        if arm == "A":
            return ix.bm25(q)
        if arm == "B":
            return ix.bm25(q, stats_mask=vis)
        b = ix.bm25(q, stats_mask=vis)
        if arm == "C":
            l = ix.lsa_cos(q)
        else:
            z = normalize(self.svd_pub.transform(self.vec_pub.transform([q]))).ravel()
            l = self.lsa_pub @ z
        return rrf([topn(b, vis & (b > 0), 200), topn(l, vis, 200)], ix.N)

    def rank(self, arm, q, vis, n):
        s = self.scores(arm, q, vis)
        s = np.where(vis, s, -np.inf)
        if arm in ("A", "B"):
            s = np.where(s > 0, s, -np.inf)
        idx = topn(s, np.isfinite(s), n)
        return [self.ix.ids[i] for i in idx], {self.ix.ids[i]: float(s[i]) for i in idx}


def main():
    t0 = time.time()
    w = World()
    secret_terms = "refinance bridging loan Halyard equity release lender valuation"
    M = 20
    hidden = [dict(id=f"secret_{j}", type="note", partition="owner", scope="finance/investments", title="",
                   text=f"Private: {secret_terms} discussion {j}", created_day=NOW_DAY, recorded_day=NOW_DAY,
                   entities=["prop_halyard"]) for j in range(M)]
    W = Arms(w.items)
    W2 = Arms(list(w.items) + hidden)
    print(f"built in {time.time()-t0:.0f}s", flush=True)

    attackers = [i for i in w.identities if i != "owner"]
    res = {"M_hidden": M, "secret": secret_terms, "arms": {}}
    probes_extra = ["refinance", "bridging loan lender", "Halyard equity valuation", "anything new about 18 Halyard Way?"]
    for arm in "ABCD":
        changed10 = changed50 = nq = 0
        max_dscore = 0.0
        by_att = {}
        for a in attackers:
            parts = set(w.identities[a]["partitions"])
            vis1 = np.array([p in parts for p in W.ix.partition])
            vis2 = np.array([p in parts for p in W2.ix.partition])
            qs = [t["query"] for t in w.tasks if t["requester"] == a][:40] + probes_extra
            c10 = 0
            for q in qs:
                r1, s1 = W.rank(arm, q, vis1, 50)
                r2, s2 = W2.rank(arm, q, vis2, 50)
                assert not any(x.startswith("secret_") for x in r2), "hidden row returned"
                nq += 1
                if r1[:10] != r2[:10]:
                    changed10 += 1; c10 += 1
                if r1 != r2:
                    changed50 += 1
                common = set(s1) & set(s2)
                if common:
                    max_dscore = max(max_dscore, max(abs(s1[k] - s2[k]) for k in common))
            by_att[a] = dict(queries=len(qs), top10_changed=c10)
        # canary monitor on W2 (same protocol as E5: 'anything new about <entity>?' + unique token)
        alarms = probes = 0
        canaries = [it for it in W2.items if it["type"] == "canary"]
        for a in attackers:
            parts = set(w.identities[a]["partitions"])
            vis = np.array([p in parts for p in W2.ix.partition])
            for c in canaries:
                if c["partition"] in parts:
                    continue
                for q in [f"anything new about {w.entities[e]['name']}?" for e in c["entities"]] + [c["text"].split()[2]]:
                    ids, _ = W2.rank(arm, q, vis, 10)
                    probes += 1
                    alarms += int(c["id"] in ids)
        res["arms"][arm] = dict(queries=nq, top10_changed=changed10, top50_changed=changed50,
                                max_abs_score_delta=max_dscore, canary_probes=probes, canary_alarms=alarms,
                                by_attacker={k: v for k, v in by_att.items() if v["top10_changed"]})
        print(arm, res["arms"][arm]["queries"], changed10, changed50, f"{max_dscore:.3g}", f"canary {alarms}/{probes}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print(f"done {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
