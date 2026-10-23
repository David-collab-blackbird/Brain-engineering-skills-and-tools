"""Tiny deterministic embedder for WP-E15 (provided; builders must not modify it).

embed(text) -> list[float] of length DIM, L2-normalised. Words and their
character trigrams are hashed into DIM buckets with a stable hash, so the same
text always gives the same vector on every machine. Text with no tokens gives
the zero vector.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata

DIM = 64
_TOKEN = re.compile(r"\w+")


def tokens(text: str) -> list[str]:
    """The tokeniser WP-E15 uses everywhere (rule R1)."""
    return _TOKEN.findall(unicodedata.normalize("NFKC", text).casefold())


def _bucket(feature: str) -> tuple[int, float]:
    h = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h[:4], "little") % DIM, (1.0 if h[4] & 1 else -1.0)


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in tokens(text):
        i, s = _bucket("w:" + tok)
        vec[i] += s
        padded = f"#{tok}#"
        for j in range(len(padded) - 2):
            i, s = _bucket("c:" + padded[j:j + 3])
            vec[i] += 0.3 * s
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]
