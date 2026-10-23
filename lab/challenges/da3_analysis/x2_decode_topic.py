"""DA3-X2: is the arm-C change (LSA fitted on all partitions) decodable information or just refit noise?

Attacker = partner_cafe (sees biz/cafe + public/gym). It plants one probe note per candidate topic in its
own partition (allowed: partners can write notes). It observes its own probe notes' scores before and after
(longitudinal monitoring: e.g. it queries weekly). The owner secretly adds M hidden notes on ONE topic.
Attacker guesses the topic whose probe note's score moved most (largest increase).
Chance = 1/len(TOPICS). Arms as in X1: A global BM25, B visible BM25, C RRF(visible BM25, LSA-all) scored
on the LSA component, D LSA fitted on public rows only.
Run: cd /home/claude/brainbench && python3 -I ../challenges/da3_analysis/x2_decode_topic.py
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "/home/claude/brainbench")
sys.path.insert(0, "/home/claude/challenges/da3_analysis")
import numpy as np  # noqa: E402
from sklearn.preprocessing import normalize  # noqa: E402

from bb.brain import World  # noqa: E402
from bb.common import NOW_DAY  # noqa: E402
from x1_noninterference import Arms  # noqa: E402

TOPICS = {
    "refinance": "refinance bridging loan lender equity release",
    "divorce": "separation lawyer custody mediation settlement",
    "sale": "sell business broker buyer due diligence",
    "illness": "oncology diagnosis biopsy specialist treatment",
    "lawsuit": "lawsuit claim solicitor damages court",
    "hire": "recruit manager salary offer contract",
}
ATT = "partner_cafe"
OUT = "/home/claude/challenges/da3_analysis/x2_results.json"


def probe_docs():
    return [dict(id=f"probe_{k}", type="note", partition="biz/cafe", scope="business/cafe/ops", title="",
                 text=f"note {v}", created_day=NOW_DAY, recorded_day=NOW_DAY, entities=[]) for k, v in TOPICS.items()]


def observe(A: Arms, w):
    parts = set(w.identities[ATT]["partitions"])
    vis = np.array([p in parts for p in A.ix.partition])
    obs = {}
    for k, v in TOPICS.items():
        pos = A.ix.pos[f"probe_{k}"]
        o = {}
        o["A"] = float(A.ix.bm25(v)[pos])
        o["B"] = float(A.ix.bm25(v, stats_mask=vis)[pos])
        o["C"] = float(A.ix.lsa_cos(v)[pos])
        z = normalize(A.svd_pub.transform(A.vec_pub.transform([v]))).ravel()
        o["D"] = float((A.lsa_pub @ z)[pos])
        obs[k] = o
    return obs


def main():
    t0 = time.time()
    w = World()
    base_items = list(w.items) + probe_docs()
    base = observe(Arms(base_items), w)
    res = {"trials": [], "summary": {}}
    for M in (5, 20):
        for true in TOPICS:
            hidden = [dict(id=f"h_{j}", type="note", partition="owner", scope="finance/investments", title="",
                           text=f"Private: {TOPICS[true]} ({j})", created_day=NOW_DAY, recorded_day=NOW_DAY,
                           entities=[]) for j in range(M)]
            after = observe(Arms(base_items + hidden), w)
            row = dict(M=M, true=true)
            for arm in "ABCD":
                # BM25 score DROPS when df rises (idf falls); LSA cosine RISES with co-occurrence. Attacker knows
                # the model family, so uses the signed direction; also record the |delta| guess.
                d = {k: after[k][arm] - base[k][arm] for k in TOPICS}
                sign = -1 if arm in "AB" else 1
                guess = max(d, key=lambda k: sign * d[k])
                row[arm] = dict(guess=guess, correct=guess == true,
                                max_abs_delta=max(abs(x) for x in d.values()))
            res["trials"].append(row)
            print(M, true, {a: (row[a]["guess"], f"{row[a]['max_abs_delta']:.2g}") for a in "ABCD"}, flush=True)
    for M in (5, 20):
        rows = [r for r in res["trials"] if r["M"] == M]
        res["summary"][str(M)] = {a: f"{sum(r[a]['correct'] for r in rows)}/{len(rows)}" for a in "ABCD"}
    res["chance"] = f"1/{len(TOPICS)}"
    json.dump(res, open(OUT, "w"), indent=1)
    print(res["summary"], f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
