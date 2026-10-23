"""R9 sandbox check B2 (follow-up to probe_power.py): the sliding-window UCB rule false-vetoes almost surely when the
in-control harm rate p0 is within ~4x of delta (expected harms per window ~1-2, and 2 harms already push the UCB over
delta). Compare deployable variants:
  CUSUM-20k : Bernoulli CUSUM tuned to median in-control run length >= 20,000 probes -> SUSPEND (route goes strong,
              re-admission batch required), not a permanent veto
  LCB-W     : veto when the 95% lower bound over the last W probes > delta (hard evidence of harm)
  CUM-UCB   : re-certification: UCB over all probes since the last admission must stay <= delta (checked every 50)
Outputs as before.  python3 -I probe_power2.py
"""
import json, math
import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_power import ucb, lcb_table, run_window, run_cusum, RNG

def tune_h(p0, p1, target, trials=300, horizon=60000):
    lo = None
    for h in np.arange(3.0, 14.01, 0.5):
        runs = []
        for _ in range(trials):
            x = RNG.random(horizon) < p0
            a = run_cusum(x, p0, p1, h)
            runs.append(horizon if a is None else a)
        if np.median(runs) >= target:
            return float(h)
    return 14.0

def cum_ucb_first_fail(x, delta, start, every=50, n_min=None):
    """Checks begin only once the route could have been admitted (n_min clean-run length for delta)."""
    c = np.cumsum(x)
    n_min = n_min or next(n for n in range(1, 5000) if ucb(0, n) <= delta)
    for t in range(start + max(every, n_min) - 1, len(x), every):
        k = int(c[t] - (c[start - 1] if start > 0 else 0)); n = t - start + 1
        if ucb(k, n) > delta:
            return t
    return None

res = []
trials = 300
for (p0, p1, delta, W) in [(0.005, 0.03, 0.02, 300), (0.005, 0.05, 0.02, 300), (0.005, 0.10, 0.02, 300),
                           (0.01, 0.05, 0.03, 200), (0.002, 0.02, 0.01, 600)]:
    h = tune_h(p0, p1, 20000)
    lt = lcb_table(W)
    rec = {"p0": p0, "p1": p1, "delta": delta, "W": W, "cusum_h": h}
    for name in ["CUSUM-20k", "LCB-W", "CUM-UCB"]:
        fa, delays = 0, []
        for _ in range(trials):
            x0 = RNG.random(W + 5000) < p0
            x1 = np.concatenate([RNG.random(W + 300) < p0, RNG.random(4000) < p1])
            if name == "CUSUM-20k":
                a = run_cusum(x0[W:], p0, p1, h); b = run_cusum(x1[W:], p0, p1, h); b = None if b is None else b + W
            elif name == "LCB-W":
                a = run_window(x0, W, lt, delta, "lcb"); b = run_window(x1, W, lt, delta, "lcb")
            else:
                a = cum_ucb_first_fail(x0, delta, W); b = cum_ucb_first_fail(x1, delta, W)
            fa += a is not None
            if b is None: delays.append(4000)
            elif b < W + 300: delays.append(0)
            else: delays.append(b - (W + 300))
        rec[name] = {"false_alarm_share_5000_probes": round(fa / trials, 3),
                     "median_delay": float(np.median(delays)), "p90_delay": float(np.percentile(delays, 90)),
                     "missed_within_4000": round(float(np.mean(np.array(delays) >= 4000)), 3)}
    res.append(rec)
print(json.dumps(res, indent=1))
