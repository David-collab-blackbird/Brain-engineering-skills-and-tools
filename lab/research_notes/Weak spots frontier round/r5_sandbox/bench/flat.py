import numpy as np, time, os
rng=np.random.default_rng(0)
def bench(n,d,dtype=np.float32,q=1,reps=5):
    X=rng.standard_normal((n,d),dtype=np.float32).astype(dtype)
    Q=rng.standard_normal((q,d),dtype=np.float32).astype(dtype)
    ts=[]
    for _ in range(reps):
        t=time.perf_counter(); s=X@Q.T
        if q==1: idx=np.argpartition(-s[:,0],150)[:150]
        ts.append(time.perf_counter()-t)
    del X
    return min(ts)*1000, np.median(ts)*1000
print("threads",os.environ.get("OPENBLAS_NUM_THREADS"),"cpus",os.cpu_count())
for n,d in [(100_000,768),(100_000,1024),(100_000,4096),(1_000_000,384),(1_000_000,768)]:
    mn,md=bench(n,d)
    gb=n*d*4/1e9
    print(f"fp32 n={n} d={d} single-query top150: min {mn:.1f} ms, median {md:.1f} ms  (data {gb:.2f} GB -> {gb/(mn/1000):.1f} GB/s)")
# batch of 64 queries amortised
mn,md=bench(1_000_000,768,q=64,reps=3); print(f"fp32 n=1M d=768 batch64 matmul: {mn:.0f} ms total, {mn/64:.1f} ms/query")
# binary: packed bits hamming via popcount on uint8 using np.bitwise_count (numpy>=2)
n,d=1_000_000,768
B=rng.integers(0,256,(n,d//8),dtype=np.uint8); qb=rng.integers(0,256,(d//8,),dtype=np.uint8)
B64=B.view(np.uint64); q64=qb.view(np.uint64)
ts=[]
for _ in range(5):
    t=time.perf_counter(); h=np.bitwise_count(B64^q64).sum(1,dtype=np.uint16); idx=np.argpartition(h,1500)[:1500]; ts.append(time.perf_counter()-t)
print(f"binary n=1M d=768 hamming top1500: min {min(ts)*1000:.1f} ms")
