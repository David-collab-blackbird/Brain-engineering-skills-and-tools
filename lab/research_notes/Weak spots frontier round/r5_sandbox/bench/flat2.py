import numpy as np, time, os, gc
rng=np.random.default_rng(0)
def make(n,d,dtype=np.float32):
    X=np.empty((n,d),dtype=dtype)
    for i in range(0,n,50_000):
        X[i:i+50_000]=rng.standard_normal((min(50_000,n-i),d),dtype=np.float32)
    return X
def t_single(X,Q,k=150,reps=7):
    ts=[]
    for _ in range(reps):
        t=time.perf_counter(); s=X@Q; idx=np.argpartition(-s,k)[:k]; ts.append(time.perf_counter()-t)
    return min(ts)*1000, float(np.median(ts))*1000
print("cpus",os.cpu_count())
for n,d in [(100_000,768),(100_000,1024),(100_000,4096),(1_000_000,384),(1_000_000,768)]:
    X=make(n,d); Q=rng.standard_normal(d,dtype=np.float32)
    mn,md=t_single(X,Q); gb=X.nbytes/1e9
    print(f"fp32 n={n} d={d}: min {mn:.1f} ms, median {md:.1f} ms (scan {gb:.2f} GB, {gb/(mn/1e3):.1f} GB/s)",flush=True)
    if n==1_000_000 and d==768:
        Qb=rng.standard_normal((d,32),dtype=np.float32)
        t=time.perf_counter(); S=X@Qb; el=(time.perf_counter()-t)*1000
        print(f"  batch32 matmul: {el:.0f} ms total = {el/32:.1f} ms/query",flush=True); del S
        Xh=X.astype(np.float16); del X; gc.collect()
        # int8 via scale
        mn2,_=t_single(Xh,Q.astype(np.float16),reps=3); print(f"  fp16 numpy (no native fp16 BLAS): {mn2:.0f} ms",flush=True)
        del Xh
    else:
        del X
    gc.collect()
n,d=1_000_000,768
B=rng.integers(0,256,(n,d//8),dtype=np.uint8).view(np.uint64); q=rng.integers(0,256,(d//8,),dtype=np.uint8).view(np.uint64)
ts=[]
for _ in range(5):
    t=time.perf_counter(); h=np.bitwise_count(B^q).sum(1,dtype=np.uint16); idx=np.argpartition(h,1500)[:1500]; ts.append(time.perf_counter()-t)
print(f"binary(1-bit) n=1M d=768 hamming top1500 numpy: min {min(ts)*1000:.1f} ms ({B.nbytes/1e6:.0f} MB)")
