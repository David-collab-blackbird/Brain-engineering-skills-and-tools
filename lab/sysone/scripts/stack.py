"""Diversity / stacking test for the J1 checker (U4: different signals catch different errors).
Logistic stack on [Laya margin, NLI margin, deterministic value check] (and subsets), fit on N pool labels, test on s2.
Also: error overlap - of the errors each zero-shot checker misses, how many does the other catch?
  python3 -I stack.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sklearn.linear_model import LogisticRegression
from analyze import load_scores, pool_order, groups_of
from common import RES, load_rows, metrics, cluster_bootstrap
from conformal import det_value_check

rows = {r["id"]: r for s in ("J1_test", "J1_pool") for r in load_rows(s)}
models = [m for m in ("laya", "nli_xs", "julia", "bge_rr") if load_scores(m, "J1_test") is not None]   # qwen06 scored on a 160-row subset: excluded to keep n

def margins(split):
    D = {m: load_scores(m, f"J1_{split}") for m in models}
    ids = sorted(set.intersection(*[set(D[m]["ids"]) for m in models]))
    X = {}
    for m in models:
        pos = {i: k for k, i in enumerate(D[m]["ids"])}
        Z = D[m]["logits"][[pos[i] for i in ids], :2].astype(float)
        X[m] = Z[:, 1] - Z[:, 0]
    X["det"] = np.array([float(det_value_check(rows[i])) for i in ids])
    y = np.array([rows[i]["label"] for i in ids])
    g = np.array([rows[i]["group"] for i in ids])
    k = np.array([rows[i]["meta"]["kind"] for i in ids])
    return X, y, g, k, ids

Xt, yt, gt, kt, idt = margins("test")
Xp, yp, gp, kp, idp = margins("pool")
out = {"models": models, "n_test": int(len(yt)), "n_pool": int(len(yp))}
combos = [["laya"], ["nli_xs"], ["laya", "nli_xs"], ["laya", "det"], ["nli_xs", "det"], ["laya", "nli_xs", "det"]]
if "bge_rr" in models: combos += [["laya", "nli_xs", "bge_rr", "det"]]
if "qwen06" in models: combos += [["laya", "nli_xs", "qwen06", "det"]]
for N in (50, 200, len(yp)):
    for c in combos:
        res = []
        for rep in range(5 if N < len(yp) else 1):
            o = pool_order(gp, rep)[:N]
            A = np.stack([Xp[f][o] for f in c], 1)
            mu, sd = A.mean(0), A.std(0) + 1e-6
            lr = LogisticRegression(C=1.0, max_iter=1000).fit((A - mu) / sd, yp[o])
            P = lr.predict_proba((np.stack([Xt[f] for f in c], 1) - mu) / sd)
            m = metrics(P, yt)
            pred = P.argmax(1)
            m["catch_by_kind"] = {kk: float((pred[kt == kk] == 0).mean()) for kk in sorted(set(kt)) if kk != "true"}
            if rep == 0 and N == len(yp):
                m["acc_ci"] = cluster_bootstrap(lambda ix: (pred[ix] == yt[ix]).mean(), gt)
            res.append(m)
        key = f"N={N}|" + "+".join(c)
        out[key] = {kk: (float(np.mean([r[kk] for r in res])) if not isinstance(res[0][kk], (dict, tuple)) else res[0][kk]) for kk in res[0]}
        print(key, {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in out[key].items() if kk in ("acc", "ece", "brier", "auroc", "catch_by_kind")}, flush=True)
# error overlap of zero-shot decisions (threshold 0)
for a in models:
    for b in models:
        if a < b:
            ea = (Xt[a] > 0).astype(int) != yt
            eb = (Xt[b] > 0).astype(int) != yt
            out[f"overlap|{a}|{b}"] = dict(err_a=int(ea.sum()), err_b=int(eb.sum()), both=int((ea & eb).sum()),
                                          corr_margins=float(np.corrcoef(Xt[a], Xt[b])[0, 1]))
            print(a, b, out[f"overlap|{a}|{b}"])
json.dump(out, open(f"{RES}/stack_J1.json", "w"), indent=1, default=float)
