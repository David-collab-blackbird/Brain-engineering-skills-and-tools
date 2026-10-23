"""Analysis of saved scores: zero-shot, calibration-only (temperature / Platt / isotonic), learned heads on frozen
features ("self-learning"), label-count curves, conformal sets. Writes results/analysis.json and results/tables.md.

  python3 -I analyze.py

Protocol
- Test = world s2 (J*_test). Labels for calibration/learning come from the label pool (worlds s1/s3, J*_pool), taken as
  the FIRST N rows of the group-shuffled pool (whole tasks/entities), N in {50, 200, 1000 (or max)}; 5 resamples of the
  pool order (group-level) per N for the curve -> mean and range.
- Calibration-only arms never change the decision (argmax) except Platt/isotonic on binary jobs (threshold moves).
- Learned head ("self-learning, light"): logistic regression on [frozen features (PCA-64 fitted on pool) + zero-shot logit
  margin], i.e. a linear probe that a per-partition server can refit in seconds on CPU. LoRA is not run on CPU (see report).
- CIs: cluster bootstrap over test groups (tasks / entities), 1,000 resamples.
"""
import json
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression

from common import RES, Isotonic, Platt, Temperature, cluster_bootstrap, load_rows, metrics, softmax

warnings.filterwarnings("ignore")
MODELS = ["laya", "julia", "jeff", "jeff_ground", "qwen06", "bge_rr", "nli_xs"]
NAMES = {"laya": "Laya 421M (open S1, ModernBERT-L)", "julia": "Julia-1 144M (open S1, mmBERT-small)",
         "qwen06": "Qwen3-0.6B letter readout (so1 recipe, 2 orders)", "bge_rr": "bge-reranker-v2-m3 568M (cross-encoder)",
         "nli_xs": "nli-deberta-v3-xsmall 71M (NLI cross-encoder)", "jeff": "Jeff v1.3 base (Qwen3.5-0.8B, open S1)",
         "jeff_ground": "Jeff v1.3 + 'ground' adapter (grounding LoRA)"}
JOBS = {"J1": "J1 extraction checker", "J2": "J2 relevance (vital?)", "J3t": "J3 router: request type (5)",
        "J3a": "J3 router: area (7)", "J4": "J4 coverage checker (missing item?)"}
NS = [50, 200, 1000]
REPS = 5


def load_scores(model, sname):
    p = f"{RES}/scores/{model}/{sname}.npz"
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    return {k: z[k] for k in z.files}


def subset(d, mask):
    return {k: (v[mask] if isinstance(v, np.ndarray) and len(v) == len(mask) else v) for k, v in d.items()}


def split_j3(d, rows_by_id):
    sub = np.array([rows_by_id[i]["subjob"] for i in d["ids"]])
    return {"J3t": subset(d, sub == "type"), "J3a": subset(d, sub == "area")}


def logits_of(d):
    K = int(d["K"].max())
    return d["logits"][:, :K].astype(float)


def groups_of(d, rows_by_id):
    return np.array([rows_by_id[i]["group"] for i in d["ids"]])


def ci(fn, groups):
    return cluster_bootstrap(fn, groups, B=1000)


def summarize(P, y, groups):
    m = metrics(P, y)
    pred = P.argmax(1)
    m["acc_ci"] = ci(lambda ix: (pred[ix] == y[ix]).mean(), groups)
    from common import ece as _ece, auroc as _auroc
    m["ece_ci"] = ci(lambda ix: _ece(P[ix], y[ix]), groups)
    wrong = (pred != y).astype(int)
    m["auroc_err_ci"] = ci(lambda ix: _auroc(1 - P[ix].max(1), wrong[ix]), groups)
    if P.shape[1] == 2:
        m["auroc_ci"] = ci(lambda ix: _auroc(P[ix, 1], y[ix]), groups)
    m["n_groups"] = int(len(np.unique(groups)))
    return m


def pool_order(pool_groups, rep):
    """Group-level permutation of the pool (rep 0 = file order, already group-shuffled)."""
    if rep == 0:
        return np.arange(len(pool_groups))
    rng = np.random.default_rng(100 + rep)
    uniq = list(dict.fromkeys(pool_groups))
    rng.shuffle(uniq)
    pos = {g: k for k, g in enumerate(uniq)}
    return np.array(sorted(range(len(pool_groups)), key=lambda i: (pos[pool_groups[i]], i)))


def fit_head(Ftr, ztr, ytr, Fte, zte, K, pca=None):
    """Linear probe on [PCA(feats), zero-shot logits]; returns probabilities on test."""
    Xtr = np.hstack([pca.transform(Ftr), ztr]) if pca is not None else ztr
    Xte = np.hstack([pca.transform(Fte), zte]) if pca is not None else zte
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
    if len(np.unique(ytr)) < 2:
        return None
    lr = LogisticRegression(C=0.5, max_iter=2000).fit(Xtr, ytr)
    P = np.zeros((len(Xte), K))
    P[:, lr.classes_] = lr.predict_proba(Xte)
    P = np.clip(P, 1e-6, 1)
    return P / P.sum(1, keepdims=True)


def binary_margin(Z):
    return Z[:, 1] - Z[:, 0]


def run():
    rows_by_id = {}
    for s in ["J1_test", "J2_test", "J3_test", "J4_test", "J1_pool", "J2_pool", "J3_pool", "J4_pool"]:
        for r in load_rows(s):
            rows_by_id[r["id"]] = r
    out = {}
    for model in MODELS:
        lat = {}
        lp = f"{RES}/scores/{model}/latency.json"
        if os.path.exists(lp):
            lat = json.load(open(lp))
        for job in ["J1", "J2", "J3", "J4"]:
            te, po = load_scores(model, f"{job}_test"), load_scores(model, f"{job}_pool")
            if te is None:
                continue
            pairs = split_j3(te, rows_by_id).items() if job == "J3" else [(job, te)]
            pool_parts = (split_j3(po, rows_by_id) if job == "J3" else {job: po}) if po is not None else {}
            for sub, d in pairs:
                Z, y, g = logits_of(d), d["label"].astype(int), groups_of(d, rows_by_id)
                K = Z.shape[1]
                res = {"latency_p50_ms": lat.get(f"{job}_test", {}).get("p50_ms"),
                       "bulk_ms_per_row": 1000 * lat.get(f"{job}_test", {}).get("bulk_s_per_row", float("nan"))}
                # zero-shot: raw logits (Laya/Julia ship temperatures; we apply raw then calibrated variants)
                res["zero_shot_raw"] = summarize(softmax(Z), y, g)
                if model == "laya":
                    T0 = {"J1": 1.983, "J2": 1.983, "J3t": 1.760, "J3a": 1.000, "J4": 1.983}[sub]   # shipped per-bucket temperatures
                    res["zero_shot_shipped_T"] = summarize(softmax(Z, T0), y, g)
                pd_ = pool_parts.get(sub)
                if pd_ is not None:
                    Zp, yp, gp = logits_of(pd_), pd_["label"].astype(int), groups_of(pd_, rows_by_id)
                    Kp = Zp.shape[1]
                    if Kp < K:
                        Zp = np.hstack([Zp, np.full((len(Zp), K - Kp), -1e4)])
                    Fp, Ft = pd_["feats"].astype(np.float32), d["feats"].astype(np.float32)
                    if Fp.shape[1] != Ft.shape[1]:
                        w = min(Fp.shape[1], Ft.shape[1])
                        Fp, Ft = Fp[:, :w], Ft[:, :w]
                    curve = {}
                    Ns = sorted({n for n in NS if n < len(yp)} | {min(NS[-1], len(yp))})
                    for N in Ns:
                        reps = []
                        for rep in range(REPS):
                            o = pool_order(gp, rep)[:N]
                            Zn, yn, Fn = Zp[o], yp[o], Fp[o]
                            r = {}
                            T = Temperature().fit(Zn, yn)
                            r["temperature"] = metrics(T(Z), y) | {"T": T.T}
                            if K == 2:
                                r["platt"] = metrics(Platt().fit(binary_margin(Zn), yn)(binary_margin(Z)), y)
                                r["isotonic"] = metrics(Isotonic().fit(binary_margin(Zn), yn)(binary_margin(Z)), y)
                            pca = PCA(n_components=min(64, N - 1, Fn.shape[1]), random_state=0).fit(Fn) if N >= 20 else None
                            Ph = fit_head(Fn, Zn, yn, Ft, Z, K, pca)
                            if Ph is not None:
                                r["linear_head"] = metrics(Ph, y)
                                if N == Ns[-1] and rep == 0:
                                    r["linear_head_ci"] = summarize(Ph, y, g)
                            reps.append(r)
                        agg = {}
                        for arm in reps[0]:
                            if arm.endswith("_ci"):
                                agg[arm] = reps[0][arm]
                                continue
                            agg[arm] = {k: (float(np.mean([rr[arm][k] for rr in reps if arm in rr])),
                                            float(np.min([rr[arm][k] for rr in reps if arm in rr])),
                                            float(np.max([rr[arm][k] for rr in reps if arm in rr])))
                                        for k in reps[0][arm] if isinstance(reps[0][arm][k], (int, float))}
                        curve[N] = agg
                    res["curve"] = curve
                    res["pool_n"] = int(len(yp))
                out.setdefault(sub, {})[model] = res
                print(f"{model:7s} {sub:4s} zs acc {res['zero_shot_raw']['acc']:.3f} ece {res['zero_shot_raw']['ece']:.3f}"
                      + (f" | head@max acc {max(res.get('curve', {}).items())[1].get('linear_head', {}).get('acc', (np.nan,))[0]:.3f}"
                         if res.get("curve") else ""), flush=True)
    json.dump(out, open(f"{RES}/analysis.json", "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    run()
