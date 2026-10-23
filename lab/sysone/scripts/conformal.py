"""Brain-integration analyses on saved scores (zero-shot logits + frozen features):

  J1 write gate (maker-checker): auto-accept an extracted record only if P(supported) >= tau, tau chosen on calibration
     labels by fixed-sequence Learn-then-Test so that the error rate among accepted records <= eps with 95% confidence
     (one-sided Clopper-Pearson). Reports automation rate, realised error among accepted, catch rate per error kind,
     and the hybrid with a deterministic value-token validator (U4: deterministic checks first).
  J2 certified recall (I15 on the grader): per task, s = min P(vital) over its vital candidates; lambda = conformal
     quantile so that P(all vital candidates kept) >= 1 - alpha; reports coverage and kept-set size on test tasks.
  J3 router sets: split-conformal LAC prediction sets over request types / areas; coverage, mean set size, singletons.

Pool split for every arm (group level): first 2/3 of the label pool = fit (temperature or linear head), last 1/3 =
conformal calibration. Test = world s2.  python3 -I conformal.py
"""
import json
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.stats import beta
from sklearn.decomposition import PCA

from analyze import MODELS, NAMES, fit_head, groups_of, load_scores, logits_of, split_j3
from common import RES, Temperature, load_rows, softmax, wilson

warnings.filterwarnings("ignore")


def cp_upper(k, n, conf=0.95):
    return 1.0 if n == 0 else float(beta.ppf(conf, k + 1, n - k)) if k < n else 1.0


def cp_lower(k, n, conf=0.95):
    return 0.0 if k == 0 else float(beta.ppf(1 - conf, k, n - k + 1))


def group_cut(groups, frac):
    """Index of the first row of the group that crosses frac of the rows (pool is group-shuffled)."""
    n = len(groups)
    i = int(frac * n)
    while 0 < i < n and groups[i] == groups[i - 1]:
        i += 1
    return i


def arm_probs(model, job, sub, arm, rows_by_id):
    te, po = load_scores(model, f"{job}_test"), load_scores(model, f"{job}_pool")
    if te is None or po is None:
        return None
    if job == "J3":
        te, po = split_j3(te, rows_by_id)[sub], split_j3(po, rows_by_id)[sub]
    Zt, yt, gt = logits_of(te), te["label"].astype(int), groups_of(te, rows_by_id)
    Zp, yp, gp = logits_of(po), po["label"].astype(int), groups_of(po, rows_by_id)
    K = Zt.shape[1]
    if Zp.shape[1] < K:
        Zp = np.hstack([Zp, np.full((len(Zp), K - Zp.shape[1]), -1e4)])
    c = group_cut(gp, 2 / 3)
    fit, cal = np.arange(c), np.arange(c, len(yp))
    if arm == "temp":
        T = Temperature().fit(Zp[fit], yp[fit])
        Pc, Pt = T(Zp[cal]), T(Zt)
    else:
        Fp, Ft = po["feats"].astype(np.float32), te["feats"].astype(np.float32)
        w = min(Fp.shape[1], Ft.shape[1])
        Fp, Ft = Fp[:, :w], Ft[:, :w]
        pca = PCA(n_components=min(64, len(fit) - 1, w), random_state=0).fit(Fp[fit])
        Pc = fit_head(Fp[fit], Zp[fit], yp[fit], Fp[cal], Zp[cal], K, pca)
        Pt = fit_head(Fp[fit], Zp[fit], yp[fit], Ft, Zt, K, pca)
    return dict(Pc=Pc, yc=yp[cal], gc=gp[cal], idc=po["ids"][cal], Pt=Pt, yt=yt, gt=gt, idt=te["ids"], n_fit=len(fit))


# ------------------------------------------------------------------------------------------------ J1 gate
def det_value_check(row):
    """Deterministic validator: the claimed value (core, normalised) must appear in the quoted span."""
    from build_sets import core_value, norm
    claim, span = row["parts"]["claim"], row["parts"]["span"]
    value = claim.split(": ", 1)[1] if ": " in claim else claim
    return norm(core_value(value)) in norm(span)


def ltt_threshold(p, y, eps, conf=0.95, n_min=30):
    """Fixed-sequence Learn-then-Test: candidate thresholds are the calibration scores in decreasing order, starting at
    the first one that accepts >= n_min rows (a label-free ordering, so the procedure stays valid). Lower tau while the
    one-sided Clopper-Pearson upper bound on the error rate among accepted (p >= tau) stays <= eps; stop at the first
    failure. Returns tau (inf if the first test already fails)."""
    order = np.argsort(-p)
    best = np.inf
    k = 0
    for j, i in enumerate(order):
        k += int(y[i] == 0)
        n = j + 1
        if j + 1 < len(order) and p[order[j + 1]] == p[i]:
            continue
        if n < n_min:
            continue
        if cp_upper(k, n, conf) <= eps:
            best = p[i]
        else:
            break
    return best


def j1_gate(A, rows_by_id, eps, prevalence=None, draws=30, n_min=60):
    """prevalence=None: the set as built (50% seeded errors). prevalence=0.1: errors subsampled (in calibration AND test)
    to a realistic 10% error rate, repeated `draws` times; results are averaged (automation, realised error) and the
    certification rate (share of draws where LTT certified a threshold) is reported."""
    pc, pt = A["Pc"][:, 1], A["Pt"][:, 1]
    kinds_t = np.array([rows_by_id[i]["meta"]["kind"] for i in A["idt"]])
    dc = np.array([det_value_check(rows_by_id[i]) for i in A["idc"]])
    dt = np.array([det_value_check(rows_by_id[i]) for i in A["idt"]])
    out = {}
    rng = np.random.default_rng(0)

    def sub(y, prev):
        pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
        k = int(round(prev / (1 - prev) * len(pos)))
        return np.sort(np.concatenate([pos, rng.choice(neg, min(k, len(neg)), replace=False)]))

    for mode in ["model_only", "hybrid"]:
        pc_ = np.where(dc, pc, 0.0) if mode == "hybrid" else pc
        pt_ = np.where(dt, pt, 0.0) if mode == "hybrid" else pt
        recs = []
        for d in range(1 if prevalence is None else draws):
            ic = np.arange(len(pc_)) if prevalence is None else sub(A["yc"], prevalence)
            it = np.arange(len(pt_)) if prevalence is None else sub(A["yt"], prevalence)
            tau = ltt_threshold(pc_[ic], A["yc"][ic], eps, n_min=n_min)
            acc = pt_[it] >= tau
            y = A["yt"][it]
            n_acc, k_err = int(acc.sum()), int((acc & (y == 0)).sum())
            kd = kinds_t[it]
            recs.append(dict(tau=float(tau), certified=bool(np.isfinite(tau)), automation=float(acc.mean()),
                             auto_true=float(acc[y == 1].mean()), n_accepted=n_acc, k_err=k_err,
                             catch_by_kind={k: float(1 - acc[kd == k].mean()) for k in sorted(set(kd)) if k != "true"}))
        n_acc = sum(r["n_accepted"] for r in recs)
        k_err = sum(r["k_err"] for r in recs)
        out[mode] = dict(tau=float(np.median([r["tau"] for r in recs])), certified_share=float(np.mean([r["certified"] for r in recs])),
                         automation=float(np.mean([r["automation"] for r in recs])),
                         auto_true=float(np.mean([r["auto_true"] for r in recs])),
                         err_among_accepted=(k_err / n_acc if n_acc else float("nan")),
                         err_ucb95=cp_upper(k_err // max(1, len(recs)), n_acc // max(1, len(recs))) if n_acc else 1.0,
                         n_accepted=n_acc // max(1, len(recs)),
                         catch_by_kind={k: float(np.nanmean([r["catch_by_kind"].get(k, np.nan) for r in recs])) for k in sorted({k for r in recs for k in r["catch_by_kind"]})},
                         prevalence=prevalence or 0.5, draws=len(recs))
    return out


def selective(A, rows_by_id, qs=(0.1, 0.25, 0.5)):
    """Test-set risk-coverage (no certification): error among the top-q most confident 'supported' calls, model-only and
    hybrid (deterministic value check first), at 50% and 10% error prevalence (10%: errors subsampled, 30 draws)."""
    pt = A["Pt"][:, 1]
    y = A["yt"]
    dt = np.array([det_value_check(rows_by_id[i]) for i in A["idt"]])
    rng = np.random.default_rng(1)
    out = {}
    for mode in ["model_only", "hybrid"]:
        p = np.where(dt, pt, -1.0) if mode == "hybrid" else pt
        for prev in (0.5, 0.1):
            errs = {q: [] for q in qs}
            for d in range(1 if prev == 0.5 else 30):
                if prev == 0.5:
                    idx = np.arange(len(y))
                else:
                    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
                    k = int(round(prev / (1 - prev) * len(pos)))
                    idx = np.concatenate([pos, rng.choice(neg, k, replace=False)])
                pp, yy = p[idx], y[idx]
                o = np.argsort(-pp, kind="stable")
                for q in qs:
                    n = max(1, int(q * len(o)))
                    if mode == "hybrid":
                        ok = o[pp[o] > -1][:n]
                        n = len(ok)
                    else:
                        ok = o[:n]
                    errs[q].append(float((yy[ok] == 0).mean()) if n else float("nan"))
            out[f"{mode}@prev{prev}"] = {f"top{int(q*100)}%": float(np.nanmean(v)) for q, v in errs.items()}
    return out


# ------------------------------------------------------------------------------------------------ J2 certified recall
def j2_recall(A, alpha):
    def per_task(P, y, g):
        tasks = {}
        for p, yy, gg in zip(P[:, 1], y, g):
            tasks.setdefault(gg, []).append((p, yy))
        return tasks
    cal = per_task(A["Pc"], A["yc"], A["gc"])
    s = np.array([min(p for p, yy in v if yy == 1) for v in cal.values() if any(yy == 1 for _, yy in v)])
    n = len(s)
    k = int(np.floor((n + 1) * alpha))
    lam = np.sort(s)[k - 1] if k >= 1 else -np.inf
    test = per_task(A["Pt"], A["yt"], A["gt"])
    cov, size, nc = [], [], []
    for v in test.values():
        if not any(yy == 1 for _, yy in v):
            continue
        kept = [p >= lam for p, _ in v]
        cov.append(all(kp for kp, (_, yy) in zip(kept, v) if yy == 1))
        size.append(np.mean(kept))
        nc.append(len(v))
    c = int(np.sum(cov))
    return dict(alpha=alpha, lam=float(lam), n_cal_tasks=n, n_test_tasks=len(cov), coverage=c / len(cov),
                coverage_wilson=wilson(c, len(cov)), coverage_cp_lower95=cp_lower(c, len(cov)),
                kept_fraction=float(np.mean(size)), mean_candidates=float(np.mean(nc)))


# ------------------------------------------------------------------------------------------------ J3 sets
def j3_sets(A, alpha):
    yc, yt = A["yc"], A["yt"]
    sc = 1 - A["Pc"][np.arange(len(yc)), yc]
    n = len(sc)
    q = np.sort(sc)[min(n - 1, int(np.ceil((n + 1) * (1 - alpha))) - 1)]
    S = (1 - A["Pt"]) <= q
    cov = S[np.arange(len(yt)), yt]
    return dict(alpha=alpha, qhat=float(q), n_cal=n, coverage=float(cov.mean()), coverage_wilson=wilson(int(cov.sum()), len(cov)),
                mean_set=float(S.sum(1).mean()), singleton=float((S.sum(1) == 1).mean()),
                singleton_acc=float(cov[S.sum(1) == 1].mean()) if (S.sum(1) == 1).any() else float("nan"))


def main():
    rows_by_id = {}
    for s in ["J1_test", "J2_test", "J3_test", "J4_test", "J1_pool", "J2_pool", "J3_pool", "J4_pool"]:
        for r in load_rows(s):
            rows_by_id[r["id"]] = r
    res = {}
    for model in MODELS:
        for arm in ["temp", "head"]:
            key = f"{model}/{arm}"
            A = arm_probs(model, "J1", None, arm, rows_by_id)
            if A is not None:
                res.setdefault("J1_gate", {})[key] = {f"eps={e}": j1_gate(A, rows_by_id, e) for e in (0.02, 0.05, 0.10)}
                res.setdefault("J1_gate_prev10", {})[key] = {f"eps={e}": j1_gate(A, rows_by_id, e, prevalence=0.1) for e in (0.02, 0.05)}
                res.setdefault("J1_selective", {})[key] = selective(A, rows_by_id)
                res["J1_gate"][key]["n_fit"], res["J1_gate"][key]["n_cal"] = A["n_fit"], int(len(A["yc"]))
            A = arm_probs(model, "J2", None, arm, rows_by_id)
            if A is not None:
                res.setdefault("J2_recall", {})[key] = {f"alpha={a}": j2_recall(A, a) for a in (0.1, 0.05)}
            for sub in ["J3t", "J3a"]:
                A = arm_probs(model, "J3", sub, arm, rows_by_id)
                if A is not None:
                    res.setdefault(f"{sub}_sets", {})[key] = {f"alpha={a}": j3_sets(A, a) for a in (0.1, 0.05)}
            print("done", key, flush=True)
    # deterministic-only J1 baseline
    te = [rows_by_id[i] for i in rows_by_id if i.startswith("J1-s2")]
    dv = np.array([det_value_check(r) for r in te])
    y = np.array([r["label"] for r in te])
    kinds = np.array([r["meta"]["kind"] for r in te])
    res["J1_deterministic_value_check"] = dict(
        pass_true=float(dv[y == 1].mean()),
        catch_by_kind={k: float(1 - dv[kinds == k].mean()) for k in sorted(set(kinds)) if k != "true"})
    json.dump(res, open(f"{RES}/conformal.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
