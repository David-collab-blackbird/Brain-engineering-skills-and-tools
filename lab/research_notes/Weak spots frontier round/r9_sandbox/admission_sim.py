"""R9 sandbox check B3: admitting a cheap route (sequential UCB looks every 50 probes, up to 1,000 probes).
Multiple looks inflate FALSE admission (a route whose true harm rate is at or above delta gets admitted), so the
per-look confidence is Bonferroni-adjusted: 20 looks -> conf 1 - 0.05/20 = 0.9975.
Reports P(admitted by 1,000 probes) and median probes to admission, for true harm p in {0.2d, 0.5d, d, 2d}.
python3 -I admission_sim.py"""
import json
import numpy as np
from scipy.stats import beta
rng = np.random.default_rng(7)
def ucb(k, n, conf):
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))
out = []
for delta in [0.01, 0.02, 0.05]:
    for conf_name, conf in [("naive_0.95", 0.95), ("bonferroni_0.9975", 1 - 0.05 / 20)]:
        tbl = {}
        for mult in [0.2, 0.5, 1.0, 2.0]:
            p = mult * delta
            adm, when = 0, []
            for _ in range(2000):
                x = rng.random(1000) < p
                c = np.cumsum(x)
                for n in range(50, 1001, 50):
                    if ucb(int(c[n - 1]), n, conf) <= delta:
                        adm += 1; when.append(n); break
            tbl[f"p={mult}*delta"] = {"P_admit_by_1000": round(adm / 2000, 3),
                                       "median_probes_if_admitted": float(np.median(when)) if when else None}
        out.append({"delta": delta, "rule": conf_name, **tbl})
print(json.dumps(out, indent=1))
