"""R9 sandbox check A: the router as a System One decision, with an ASYMMETRIC (veto-style) certified threshold.

Reuses the R7/E13a saved scores for the J3 'request type' router (BrainBench v0.2; test = world s2, pool = s1/s3),
fitted exactly as in sysone/scripts/conformal.py (2/3 of the pool fits a temperature or linear head, 1/3 calibrates).

Question: if the dispatcher may send a request to the cheap rung ONLY when the router says it is a cheap-eligible type,
how often does a hard request slip to the cheap rung (under-routing), and how much traffic can go cheap when the
threshold is certified by Learn-then-Test so that P(hard | routed cheap) <= eps at 95% confidence?

Variants (cheap-eligible types): A = {lookup}; B = {lookup, media}. Everything else (history, advice, cross_area) must
go to a strong rung. No paid calls; numpy/scipy only.
  python3 -I router_asym.py   (run from anywhere; it imports the sysone scripts by absolute path)
"""
import json
import sys

sys.path.insert(0, "/home/claude/sysone/scripts")
import numpy as np
from common import load_rows, wilson
from conformal import arm_probs, cp_upper

TYPES = ["lookup", "history", "advice", "cross_area", "media"]


def ltt(p_easy, is_hard, eps, n_min=20, conf=0.95):
    """Fixed-sequence LTT on calibration: descending p_easy; keep lowering tau while the one-sided CP upper bound on
    P(hard | accepted as cheap) stays <= eps. Returns tau (inf = nothing may go cheap)."""
    order = np.argsort(-p_easy)
    best, k = np.inf, 0
    for j, i in enumerate(order):
        k += int(is_hard[i])
        n = j + 1
        if j + 1 < len(order) and p_easy[order[j + 1]] == p_easy[i]:
            continue
        if n < n_min:
            continue
        if cp_upper(k, n, conf) <= eps:
            best = p_easy[i]
        else:
            break
    return best


def main():
    rows = {r["id"]: r for name in ["J3_pool", "J3_test"] for r in load_rows(name)}
    out = {}
    for model in ["julia", "nli_xs", "laya"]:
        for arm in ["temp", "head"]:
            try:
                A = arm_probs(model, "J3", "J3t", arm, rows)
            except Exception as e:  # missing pool scores for some models
                out[f"{model}/{arm}"] = {"error": str(e)[:80]}
                continue
            if A is None or A["Pt"] is None:
                continue
            for vname, easy in [("A_lookup", {"lookup"}), ("B_lookup+media", {"lookup", "media"})]:
                eidx = [TYPES.index(t) for t in easy]
                pc, pt = A["Pc"][:, eidx].sum(1), A["Pt"][:, eidx].sum(1)
                hard_c = ~np.isin(A["yc"], eidx)
                hard_t = ~np.isin(A["yt"], eidx)
                # naive router: argmax type decides the rung
                naive_cheap = np.isin(A["Pt"].argmax(1), eidx)
                rec = {"n_test": int(len(pt)), "n_cal": int(len(pc)), "easy_share_test": float((~hard_t).mean()),
                       "naive": {"cheap_share": float(naive_cheap.mean()),
                                 "hard_routed_cheap": int((naive_cheap & hard_t).sum()),
                                 "hard_n": int(hard_t.sum()),
                                 "under_routing_rate_among_hard": float((naive_cheap & hard_t).sum() / max(1, hard_t.sum())),
                                 "hard_share_among_cheap": float((naive_cheap & hard_t).sum() / max(1, naive_cheap.sum()))}}
                for eps in [0.01, 0.02, 0.05]:
                    tau = ltt(pc, hard_c, eps)
                    cheap = pt >= tau
                    k, n = int((cheap & hard_t).sum()), int(cheap.sum())
                    rec[f"ltt_eps{eps}"] = {"tau": None if not np.isfinite(tau) else float(tau),
                                            "cheap_share": float(cheap.mean()),
                                            "easy_recovered": float(cheap[~hard_t].mean()) if (~hard_t).any() else 0.0,
                                            "hard_routed_cheap": k, "routed_cheap_n": n,
                                            "hard_share_among_cheap": (k / n) if n else None,
                                            "wilson_95": wilson(k, n) if n else None}
                out[f"{model}/{arm}/{vname}"] = rec
    print(json.dumps(out, indent=1))


if __name__ == "__main__" and "--rc" not in sys.argv:
    main()


def risk_coverage():
    """Uncertified view: pooled calibration+test (300 requests), error = hard request among the top-q most 'easy'."""
    from common import auroc
    rows = {r["id"]: r for name in ["J3_pool", "J3_test"] for r in load_rows(name)}
    res = {}
    for model in ["julia", "nli_xs", "laya"]:
        for arm in ["temp", "head"]:
            A = arm_probs(model, "J3", "J3t", arm, rows)
            if A is None or A["Pt"] is None:
                continue
            for vname, easy in [("A_lookup", {"lookup"}), ("B_lookup+media", {"lookup", "media"})]:
                eidx = [TYPES.index(t) for t in easy]
                p = np.concatenate([A["Pc"][:, eidx].sum(1), A["Pt"][:, eidx].sum(1)])
                hard = ~np.isin(np.concatenate([A["yc"], A["yt"]]), eidx)
                order = np.argsort(-p)
                r = {"auroc_easy_vs_hard": float(auroc(p, (~hard).astype(int))), "n": int(len(p)), "easy_n": int((~hard).sum())}
                for q in [0.05, 0.10, 0.20]:
                    top = order[: max(1, int(q * len(p)))]
                    r[f"hard_share_top{int(q*100)}"] = float(hard[top].mean())
                res[f"{model}/{arm}/{vname}"] = r
    return res


if __name__ == "__main__" and "--rc" in sys.argv:
    print(json.dumps(risk_coverage(), indent=1))
