import numpy as np, time
rng = np.random.default_rng(0)
def bench(N, d, dtype=np.float32, reps=5, frac=None):
    E = rng.standard_normal((N, d), dtype=np.float32).astype(dtype)
    q = rng.standard_normal(d).astype(dtype)
    E @ q
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); s = E @ q; idx = np.argpartition(-s, 200)[:200]; ts.append(time.perf_counter() - t)
    out = dict(N=N, d=d, dtype=np.dtype(dtype).name, GB=E.nbytes / 1e9, full_ms=1000 * np.median(ts))
    if frac:
        mask = rng.random(N) < frac
        ts = []
        for _ in range(reps):
            t = time.perf_counter(); sub = E[mask]; s = sub @ q; ts.append(time.perf_counter() - t)
        out["fancy_index_subset_ms"] = 1000 * np.median(ts)
        ts = []
        for _ in range(reps):
            t = time.perf_counter(); s = E @ q; s[~mask] = -np.inf; ts.append(time.perf_counter() - t)
        out["full_then_mask_ms"] = 1000 * np.median(ts)
    del E
    return out
for args in [(100_000, 1024), (300_000, 1024), (500_000, 1024), (1_000_000, 384)]:
    print(bench(*args, frac=0.3), flush=True)
print(bench(1_000_000, 1024, dtype=np.float16, reps=3), flush=True)
