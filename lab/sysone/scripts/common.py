"""Shared helpers: data loading, memory-light CPU model loading, metrics, calibrators, bootstrap CIs.

All model loading here keeps RSS low (host has ~2 GB free): weights load in bf16, every nn.Linear is converted to
dynamic int8 (fast on AVX512-VNNI CPUs, ~3x faster than fp32 here), embeddings stay bf16 behind a float32 cast.
"""
import json
import math
import os
import resource
import time

import numpy as np

DATA = "/home/claude/sysone/data"
RES = "/home/claude/sysone/results"
HF_HOME = "/home/claude/models/hf"
os.environ.setdefault("HF_HOME", HF_HOME)
os.makedirs(RES, exist_ok=True)


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def load_rows(name):
    return [json.loads(l) for l in open(f"{DATA}/{name}.jsonl")]


# ----------------------------------------------------------------------------------------------- model loading
INT8 = os.environ.get("SYSONE_INT8", "0") == "1"
LOWMEM = os.environ.get("SYSONE_LOWMEM", "0") == "1"   # 16-bit weight storage + fp32 compute (lossless for bf16/fp16 checkpoints)


def CastLinear(lin):
    import torch

    class _CL(torch.nn.Module):
        def __init__(self, l):
            super().__init__()
            self.weight = l.weight
            self.bias = l.bias
            self.in_features, self.out_features = l.in_features, l.out_features

        def forward(self, x):
            b = self.bias.float() if self.bias is not None else None
            return torch.nn.functional.linear(x.float(), self.weight.float(), b)

    return _CL(lin)


def int8_linears(model, skip=(), force=False):
    """Replace every nn.Linear (except names in skip) by a dynamic-int8 Linear, one module at a time (low peak RAM).
    DISABLED by default (SYSONE_INT8=1 to enable): measured on Julia-1, dynamic int8 flipped 68% of typed-decision
    answers vs fp32 (accuracy 0.42 vs 0.65 on 60 typed-decisions rows). Without int8 every Linear is cast to fp32."""
    if not (INT8 or force):
        import torch
        if LOWMEM:   # keep the checkpoint's 16-bit weights; upcast one layer at a time inside forward (fp32 compute)
            names = [n for n, m in model.named_modules() if isinstance(m, torch.nn.Linear) and not any(s in n for s in skip)]
            for name in names:
                parent = model.get_submodule(name.rsplit(".", 1)[0]) if "." in name else model
                child = name.rsplit(".", 1)[-1]
                setattr(parent, child, CastLinear(getattr(parent, child)))
            return model
        for n, mod in model.named_modules():
            if isinstance(mod, torch.nn.Linear):
                mod.weight.data = mod.weight.data.float()
                if mod.bias is not None:
                    mod.bias.data = mod.bias.data.float()
        return model
    import torch
    import torch.ao.nn.quantized.dynamic as nnqd
    from torch.ao.quantization import default_dynamic_qconfig, per_channel_dynamic_qconfig
    if os.environ.get("SYSONE_INT8_PERCHANNEL", "1") == "1":
        default_dynamic_qconfig = per_channel_dynamic_qconfig
    import gc
    names = [n for n, m in model.named_modules() if isinstance(m, torch.nn.Linear) and not any(s in n for s in skip)]
    for name in names:   # names only: holding module references would keep every bf16 weight alive (peak RAM x2)
        parent = model.get_submodule(name.rsplit(".", 1)[0]) if "." in name else model
        child = name.rsplit(".", 1)[-1]
        lin = getattr(parent, child)
        f = torch.nn.Linear(lin.in_features, lin.out_features, bias=lin.bias is not None)
        with torch.no_grad():
            f.weight.copy_(lin.weight.float())
            if lin.bias is not None:
                f.bias.copy_(lin.bias.float())
        f.qconfig = default_dynamic_qconfig
        setattr(parent, child, nnqd.Linear.from_float(f))
        lin.weight.data = torch.empty(0)
        del f, lin
    gc.collect()
    trim()
    return model


def detach_mmap(model):
    """Copy every remaining parameter/buffer into anonymous memory so the safetensors mmap is released (otherwise the
    touched file pages stay mapped and count towards RSS)."""
    import gc
    import torch
    with torch.no_grad():
        for p in list(model.parameters()) + list(model.buffers()):
            if p.numel():
                p.data = p.data.clone()
    gc.collect()
    trim()
    return model


def trim():
    """Return freed heap pages to the OS (glibc)."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def cur_rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024
    return float("nan")


class CastEmbedding:
    """Wrap an nn.Embedding so weights stay bf16 but outputs are float32."""

    @staticmethod
    def patch(emb):
        import torch

        class _E(torch.nn.Module):
            def __init__(self, e):
                super().__init__()
                self.weight = e.weight
                self.padding_idx = e.padding_idx
                self.num_embeddings, self.embedding_dim = e.num_embeddings, e.embedding_dim

            def forward(self, ids):
                return torch.nn.functional.embedding(ids, self.weight, self.padding_idx).float()

        return _E(emb)


def float_rest(model):
    """Cast all remaining floating parameters/buffers that are not embeddings to float32 (norms, biases, heads)."""
    import torch
    for n, p in model.named_parameters():
        if LOWMEM and n.endswith(("weight", "bias")) and p.dim() == 2:
            continue   # Linear weights stay 16-bit (CastLinear upcasts per call)
        if p.dtype == torch.bfloat16 and "embed" not in n and "word_embeddings" not in n:
            p.data = p.data.float()
    for n, b in model.named_buffers():
        if b.dtype == torch.bfloat16:
            b.data = b.data.float()
    return model


# ----------------------------------------------------------------------------------------------- metrics
def softmax(z, T=1.0):
    z = np.asarray(z, dtype=np.float64) / T
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def ece(P, y, bins=15):
    """Top-label ECE (equal-width bins)."""
    P = np.asarray(P)
    conf = P.max(1)
    hit = (P.argmax(1) == y).astype(float)
    e = 0.0
    edges = np.linspace(0, 1, bins + 1)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (conf > a) & (conf <= b) if a > 0 else (conf >= a) & (conf <= b)
        if m.any():
            e += m.mean() * abs(conf[m].mean() - hit[m].mean())
    return e


def brier(P, y):
    P = np.asarray(P)
    Y = np.zeros_like(P)
    Y[np.arange(len(y)), y] = 1
    return float(((P - Y) ** 2).sum(1).mean())


def nll(P, y):
    P = np.asarray(P)
    return float(-np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)).mean())


def auroc(score, label):
    """P(score_pos > score_neg), ties half. label 1 = positive."""
    score, label = np.asarray(score, float), np.asarray(label, int)
    pos, neg = score[label == 1], score[label == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    allv = np.concatenate([pos, neg])[order]
    ranks = np.empty(len(allv))
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2 + 1
        i = j + 1
    r = np.empty(len(allv))
    r[order] = ranks
    rp = r[: len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def metrics(P, y, err_score=True):
    """P: [n,K] calibrated probabilities. Returns acc, ece, brier, nll and AUROC of (1-confidence) for catching errors
    of the model's own answer (error-catching AUROC: does low confidence flag the wrong answers?)."""
    P, y = np.asarray(P), np.asarray(y)
    pred = P.argmax(1)
    wrong = (pred != y).astype(int)
    out = dict(n=len(y), acc=float((pred == y).mean()), ece=ece(P, y), brier=brier(P, y), nll=nll(P, y))
    out["auroc_err"] = auroc(1 - P.max(1), wrong) if err_score else float("nan")
    if P.shape[1] == 2:
        out["auroc"] = auroc(P[:, 1], y)  # discrimination of the yes-probability
    return out


def cluster_bootstrap(fn, groups, B=1000, seed=0):
    """95% CI for statistic fn(idx) resampling clusters (groups)."""
    rng = np.random.default_rng(seed)
    groups = np.asarray(groups)
    uniq = np.unique(groups)
    members = {g: np.where(groups == g)[0] for g in uniq}
    vals = []
    for _ in range(B):
        pick = rng.choice(uniq, len(uniq), replace=True)
        idx = np.concatenate([members[g] for g in pick])
        try:
            vals.append(fn(idx))
        except Exception:
            pass
    vals = np.array(vals)
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


# ----------------------------------------------------------------------------------------------- calibrators
class Temperature:
    """Single scalar T minimising NLL (grid + golden refinement). Works on logits [n,K]."""

    def fit(self, Z, y):
        Z, y = np.asarray(Z, float), np.asarray(y)
        f = lambda T: nll(softmax(Z, T), y)
        grid = np.exp(np.linspace(np.log(0.05), np.log(20), 120))
        T = grid[np.argmin([f(t) for t in grid])]
        lo, hi = T / 1.2, T * 1.2
        for _ in range(40):
            a, b = lo + (hi - lo) * 0.382, lo + (hi - lo) * 0.618
            if f(a) < f(b):
                hi = b
            else:
                lo = a
        self.T = (lo + hi) / 2
        return self

    def __call__(self, Z):
        return softmax(Z, self.T)


class Platt:
    """Binary: p = sigmoid(a*s + b) on a scalar score (for 2-option logits use s = z1 - z0). Multi-class: vector scaling
    is overkill at small n, so Platt is binary only."""

    def fit(self, s, y, C=1.0):
        from sklearn.linear_model import LogisticRegression
        s = np.asarray(s, float).reshape(-1, 1)
        self.lr = LogisticRegression(C=C).fit(s, y)
        return self

    def __call__(self, s):
        p = self.lr.predict_proba(np.asarray(s, float).reshape(-1, 1))[:, 1]
        return np.stack([1 - p, p], 1)


class Isotonic:
    def fit(self, s, y):
        from sklearn.isotonic import IsotonicRegression
        self.ir = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=1 - 1e-4).fit(np.asarray(s, float), y)
        return self

    def __call__(self, s):
        p = self.ir.predict(np.asarray(s, float))
        return np.stack([1 - p, p], 1)


def timer():
    t0 = time.perf_counter()
    return lambda: time.perf_counter() - t0
