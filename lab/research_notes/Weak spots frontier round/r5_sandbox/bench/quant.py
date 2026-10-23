# Recall of binary / int8 / MRL-truncation-style exact search vs fp32 ground truth on synthetic clustered data
# NOTE: synthetic Gaussian-mixture vectors, not real embeddings -> directional only.
import numpy as np
rng=np.random.default_rng(1)
n,d,k=200_000,768,10
C=rng.standard_normal((2000,d),dtype=np.float32)
X=C[rng.integers(0,2000,n)]+0.6*rng.standard_normal((n,d),dtype=np.float32)
X/=np.linalg.norm(X,axis=1,keepdims=True)
Q=X[rng.choice(n,200,replace=False)]+0.3*rng.standard_normal((200,d),dtype=np.float32); Q/=np.linalg.norm(Q,axis=1,keepdims=True)
G=np.argsort(-(Q@X.T),axis=1)[:,:k]
def rec(I): return np.mean([len(set(a[:k])&set(b))/k for a,b in zip(I,G)])
# int8 (symmetric per-dim scale)
s=np.abs(X).max(0)/127; X8=np.round(X/s).astype(np.int8); S8=(Q/s)@X8.T.astype(np.float32)
print("int8 no rescore R@10:",round(rec(np.argsort(-S8,1)),3))
# binary sign
XB=(X>0); QB=(Q>0)
H=(QB.astype(np.int16)@XB.T.astype(np.int16)) + ((~QB).astype(np.int16)@(~XB).T.astype(np.int16))
for m in [1,4,10,40]:
    cand=np.argsort(-H,1)[:,:k*m]
    I=[c[np.argsort(-(X[c]@q))] for c,q in zip(cand,Q)]
    print(f"binary + fp32 rescore of top {k*m}: R@10 {rec(I):.3f}" if m>1 else f"binary no rescore R@10: {rec(cand):.3f}")
