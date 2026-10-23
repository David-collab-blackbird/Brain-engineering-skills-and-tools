"""Sandbox-grade retrievers: exact BM25 (own implementation), TF-IDF cosine, LSA "dense proxy",
RRF and weighted-sum hybrid. Exact (brute-force) search everywhere. Access control as a pre-filter.

IMPORTANT: LSA (TruncatedSVD on TF-IDF) is a WEAK stand-in for real neural embeddings. It captures
corpus co-occurrence, not paraphrase knowledge (it does not know "worth" ~ "valuation" unless the
corpus teaches it). Treat every "dense" number here as a lower bound placeholder.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import normalize

from .common import tokenize


def origin_text(it: dict) -> str:
    m = it.get("media")
    if not m:
        return ""
    o = m.get("origin", {})
    parts = [o.get("folder", "").replace("/", " "), o.get("album", ""), o.get("chat", ""),
             ("shared by " + o["shared_by"]) if o.get("shared_by") else "", o.get("adjacent_text", "")]
    return " ".join(p for p in parts if p)


def item_text(it: dict, with_origin: bool = True) -> str:
    t = (it.get("title") or "") + " " + it["text"]
    if with_origin:
        t += " " + origin_text(it)
    return t


class Index:
    """Holds every item (all versions, all partitions). Variants are expressed as masks."""

    def __init__(self, items: list[dict], with_origin: bool = True, lsa_dim: int = 256, seed: int = 0,
                 extra_docs: list[dict] | None = None):
        self.items = list(items) + list(extra_docs or [])
        self.ids = [it["id"] for it in self.items]
        self.pos = {iid: i for i, iid in enumerate(self.ids)}
        self.N = len(self.items)
        texts = [item_text(it, with_origin) for it in self.items]
        self.texts = texts
        self.cv = CountVectorizer(analyzer=tokenize)
        tf = self.cv.fit_transform(texts).astype(np.float32)          # N x V counts
        self.tf_csc = tf.tocsc()
        self.dl = np.asarray(tf.sum(axis=1)).ravel()
        self.vocab = self.cv.vocabulary_
        self.partition = np.array([it["partition"] for it in self.items])
        self.tfidf_vec = TfidfVectorizer(analyzer=tokenize, sublinear_tf=True)
        self.tfidf = self.tfidf_vec.fit_transform(texts)             # global idf (see E4 caveat)
        svd = TruncatedSVD(n_components=lsa_dim, random_state=seed, algorithm="randomized", n_iter=7)
        Z = svd.fit_transform(self.tfidf)
        self.lsa = normalize(Z).astype(np.float32)
        self.svd = svd
        self.created = np.array([it["created_day"] for it in self.items])

    # ------------------------------------------------------------- BM25
    def bm25(self, query: str, stats_mask: np.ndarray | None = None, k1: float = 1.2, b: float = 0.75,
             per_partition: bool = False) -> np.ndarray:
        """Exact BM25 over all docs. Statistics (N, df, avgdl) are computed over `stats_mask`
        (None = global). per_partition=True computes stats separately for each partition and scores
        each document with the stats of its own partition."""
        terms = [self.vocab[t] for t in tokenize(query) if t in self.vocab]
        scores = np.zeros(self.N, dtype=np.float64)
        if not terms:
            return scores
        if per_partition:
            for p in np.unique(self.partition):
                pm = self.partition == p
                scores[pm] = self._bm25_core(terms, pm, k1, b)[pm]
            return scores
        mask = np.ones(self.N, dtype=bool) if stats_mask is None else stats_mask
        return self._bm25_core(terms, mask, k1, b)

    def _bm25_core(self, terms, mask, k1, b):
        n = mask.sum()
        avgdl = self.dl[mask].mean() if n else 1.0
        scores = np.zeros(self.N, dtype=np.float64)
        for t in terms:                       # repeated query terms count repeatedly (standard)
            col = self.tf_csc.getcol(t)
            rows = col.indices
            tfv = col.data
            df = mask[rows].sum()
            idf = np.log(1 + (n - df + 0.5) / (df + 0.5))
            denom = tfv + k1 * (1 - b + b * self.dl[rows] / avgdl)
            scores[rows] += idf * tfv * (k1 + 1) / denom
        return scores

    # ------------------------------------------------------------- vector
    def tfidf_cos(self, query: str) -> np.ndarray:
        q = self.tfidf_vec.transform([query])
        return np.asarray((self.tfidf @ q.T).todense()).ravel()

    def lsa_cos(self, query: str) -> np.ndarray:
        q = self.tfidf_vec.transform([query])
        z = normalize(self.svd.transform(q)).astype(np.float32).ravel()
        return self.lsa @ z


# ------------------------------------------------------------- fusion helpers
def topn(scores: np.ndarray, mask: np.ndarray, n: int) -> np.ndarray:
    s = np.where(mask, scores, -np.inf)
    n = min(n, int(mask.sum()))
    if n <= 0:
        return np.array([], dtype=int)
    idx = np.argpartition(-s, n - 1)[:n]
    idx = idx[np.argsort(-s[idx], kind="stable")]
    return idx[np.isfinite(s[idx])]


def rrf(rank_lists: list[np.ndarray], N: int, k: int = 60, weights=None) -> np.ndarray:
    out = np.zeros(N)
    weights = weights or [1.0] * len(rank_lists)
    for w, rl in zip(weights, rank_lists):
        rl = np.asarray(rl, dtype=int)
        out[rl] += w / (k + np.arange(1, len(rl) + 1))
    return out


def minmax(scores: np.ndarray, mask: np.ndarray) -> np.ndarray:
    s = scores[mask]
    if s.size == 0:
        return np.zeros_like(scores)
    lo, hi = s.min(), s.max()
    if hi - lo < 1e-12:
        return np.zeros_like(scores)
    return np.where(mask, (scores - lo) / (hi - lo), 0.0)


class Retriever:
    """method in {bm25, tfidf, lsa, rrf, wsum}. Returns a fused score array (higher is better);
    -inf outside `mask`."""

    def __init__(self, index: Index, method: str = "rrf", depth: int = 200, alpha: float = 0.6,
                 bm25_stats: str = "visible"):
        self.ix = index
        self.method = method
        self.depth = depth
        self.alpha = alpha
        self.bm25_stats = bm25_stats  # global | visible | partition

    def _bm25(self, q, mask):
        if self.bm25_stats == "global":
            return self.ix.bm25(q)
        if self.bm25_stats == "partition":
            return self.ix.bm25(q, per_partition=True)
        return self.ix.bm25(q, stats_mask=mask)

    def score(self, query: str, mask: np.ndarray) -> np.ndarray:
        m = self.method
        N = self.ix.N
        if m == "bm25":
            s = self._bm25(query, mask)
        elif m == "tfidf":
            s = self.ix.tfidf_cos(query)
        elif m == "lsa":
            s = self.ix.lsa_cos(query)
        elif m == "rrf":
            b = self._bm25(query, mask)
            l = self.ix.lsa_cos(query)
            s = rrf([topn(b, mask & (b > 0), self.depth), topn(l, mask, self.depth)], N)
        elif m == "rrf3":
            b = self._bm25(query, mask)
            t = self.ix.tfidf_cos(query)
            l = self.ix.lsa_cos(query)
            s = rrf([topn(b, mask & (b > 0), self.depth), topn(t, mask & (t > 0), self.depth), topn(l, mask, self.depth)], N)
        elif m == "wsum":
            b = minmax(self._bm25(query, mask), mask)
            l = minmax(self.ix.lsa_cos(query), mask)
            s = self.alpha * b + (1 - self.alpha) * l
        else:
            raise ValueError(m)
        return np.where(mask, s, -np.inf)
