"""R9 sandbox check B: does a shadow-probe rule catch drift on a cheap route fast enough, without false vetoes?

A 'probe' = a random cheap-routed task re-run on the strong rung (or judged against it); outcome 1 = 'harm'
(cheap answer materially worse than strong), 0 otherwise. In-control harm rate p0; at probe t0 the route drifts to p1.

Rules compared (all per task class):
  R1 window-UCB : veto when the one-sided 95% Clopper-Pearson UPPER bound of harm over the last W probes > delta
                  (fail-closed: a route must keep proving itself; also the admission rule)
  R2 CUSUM      : Bernoulli CUSUM for p0 -> p1 (log-likelihood ratio), veto when S > h (h tuned for ARL0)
  R3 window-LCB : veto only when the 95% LOWER bound over the last W probes > delta (evidence of harm; fail-open)
Outputs: false-veto rate per 1,000 in-control probes, and median / 90th-percentile detection delay in probes.
Also: probes needed to ADMIT a route (zero-harm run needed for UCB <= delta) and days to admit at a given traffic.
numpy/scipy only, seeded, no paid calls.  python3 -I probe_power.py
"""
import json
import math

import numpy as np
from scipy.stats import beta

RNG = np.random.default_rng(20261023)


def ucb(k, n, conf=0.95):
    return 1.0 if n == 0 else (1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k)))


def lcb(k, n, conf=0.95):
    return 0.0 if k == 0 else float(beta.ppf(1 - conf, k, n - k + 1))


def ucb_table(W, conf=0.95):
    return np.array([ucb(k, W, conf) for k in range(W + 1)])


def lcb_table(W, conf=0.95):
    return np.array([lcb(k, W, conf) for k in range(W + 1)])


def run_window(x, W, table, delta, mode):
    """First index (probe number) at which the rule vetoes; windows shorter than W are judged on what exists
    (UCB mode therefore vetoes during warm-up unless pre-admitted; we pre-fill the window with an admission run)."""
    c = np.cumsum(x)
    for t in range(W, len(x)):
        k = c[t] - c[t - W]
        if mode == "ucb" and table[k] > delta:
            return t
        if mode == "lcb" and table[k] > delta:
            return t
    return None


def run_cusum(x, p0, p1, h):
    up, dn = math.log(p1 / p0), math.log((1 - p1) / (1 - p0))
    s = 0.0
    for t, v in enumerate(x):
        s = max(0.0, s + (up if v else dn))
        if s > h:
            return t
    return None


def tune_h(p0, p1, target_arl0, trials=400, horizon=20000):
    for h in np.arange(1.0, 12.01, 0.25):
        hits = []
        for _ in range(trials):
            x = RNG.random(horizon) < p0
            a = run_cusum(x, p0, p1, h)
            hits.append(horizon if a is None else a)
        if np.median(hits) >= target_arl0:
            return float(h)
    return 12.0


def admission(delta, conf=0.95):
    """Smallest n with 0 harms such that UCB <= delta, and with 1 or 2 harms."""
    out = {}
    for k in [0, 1, 2]:
        n = k + 1
        while ucb(k, n, conf) > delta:
            n += 1
        out[f"n_needed_with_{k}_harms"] = n
    return out


def main():
    res = {"admission": {}, "scenarios": []}
    for delta in [0.01, 0.02, 0.05]:
        a = admission(delta)
        a["days_to_admit_at"] = {f"{tpd}_tasks_per_day_f{f}": round(a["n_needed_with_0_harms"] / (tpd * f), 1)
                                 for tpd in [20, 100, 500] for f in [0.1, 0.25]}
        res["admission"][str(delta)] = a

    trials = 300
    for (p0, p1, delta, W) in [(0.005, 0.03, 0.02, 300), (0.005, 0.05, 0.02, 300), (0.005, 0.10, 0.02, 300),
                               (0.01, 0.05, 0.03, 200), (0.01, 0.10, 0.03, 200), (0.02, 0.08, 0.05, 120)]:
        h = tune_h(p0, p1, target_arl0=5000)
        ut, lt = ucb_table(W), lcb_table(W)
        rec = {"p0": p0, "p1": p1, "delta": delta, "W": W, "cusum_h": h}
        # in-control false vetoes over 5,000 probes (window pre-filled by a clean-at-p0 admission run)
        for name in ["R1_window_UCB", "R2_CUSUM", "R3_window_LCB"]:
            fa, delays = 0, []
            for _ in range(trials):
                x0 = RNG.random(W + 5000) < p0
                if name == "R1_window_UCB":
                    a = run_window(x0, W, ut, delta, "ucb")
                elif name == "R3_window_LCB":
                    a = run_window(x0, W, lt, delta, "lcb")
                else:
                    a = run_cusum(x0[W:], p0, p1, h)
                fa += a is not None
                # drift: W in-control probes (pre-fill) + 300 in-control, then p1
                x1 = np.concatenate([RNG.random(W + 300) < p0, RNG.random(4000) < p1])
                if name == "R1_window_UCB":
                    b = run_window(x1, W, ut, delta, "ucb")
                elif name == "R3_window_LCB":
                    b = run_window(x1, W, lt, delta, "lcb")
                else:
                    b = run_cusum(x1[W:], p0, p1, h)
                    b = None if b is None else b + W
                if b is not None and b >= W + 300:
                    delays.append(b - (W + 300))
                elif b is None:
                    delays.append(4000)
                else:
                    delays.append(0)  # vetoed before drift (counts as a false veto, delay 0)
            rec[name] = {"false_veto_share_5000_probes": round(fa / trials, 3),
                         "median_delay_probes": float(np.median(delays)),
                         "p90_delay_probes": float(np.percentile(delays, 90)),
                         "missed_within_4000": round(float(np.mean(np.array(delays) >= 4000)), 3)}
        res["scenarios"].append(rec)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
