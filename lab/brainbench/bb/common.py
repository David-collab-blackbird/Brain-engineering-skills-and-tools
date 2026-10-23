"""Shared utilities: tokenisation, statistics, IO, dates.

Everything here is deterministic. No network, no model downloads.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
from typing import Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")

# Simulated timeline: 18 months. "NOW" is the end of month 18.
START = _dt.date(2025, 1, 1)
NOW = _dt.date(2026, 6, 30)
NOW_DAY = (NOW - START).days


def day_to_date(d: int) -> str:
    return (START + _dt.timedelta(days=int(d))).isoformat()


def month_start_day(m: int) -> int:
    """Day index of the first day of simulated month m (0-based)."""
    y = 2025 + (m // 12)
    mo = (m % 12) + 1
    return (_dt.date(y, mo, 1) - START).days


def month_name(m: int) -> str:
    y = 2025 + (m // 12)
    mo = (m % 12) + 1
    return _dt.date(y, mo, 1).strftime("%B %Y")


def quarter_label(m: int) -> str:
    y = 2025 + (m // 12)
    q = (m % 12) // 3 + 1
    return f"{y}Q{q}"


# ---------------------------------------------------------------- tokeniser
STOP = set(
    """a an and are as at be been but by for from has have had he her his i if in into is it its
    me my of on or our so that the their them then there these they this to us was we were what when
    where which who will with you your just about any can could do does did up out how should would
    i'm it's we're they're im ive i've get got than too very also re vs""".split()
)
_TOK = re.compile(r"[a-z0-9]+")


def stem(t: str) -> str:
    """Tiny suffix stripper (Porter-lite). Deterministic, crude, adequate for a sandbox."""
    if len(t) <= 3 or t.isdigit():
        return t
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    for suf in ("ing", "edly", "ed", "es", "ly", "s", "e"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in _TOK.findall(text.lower()) if t not in STOP]


def analyzer(text: str) -> list[str]:
    return tokenize(text)


# ---------------------------------------------------------------- stats
def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Wilson score interval. Returns (p, lo, hi)."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def fmt_wilson(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    if n == 0:
        return "n/a"
    return f"{100*p:.1f} [{100*lo:.1f}–{100*hi:.1f}]"


def mcnemar_exact(a: Iterable[bool], b: Iterable[bool]) -> tuple[int, int, float]:
    """Exact two-sided McNemar test on paired 0/1 outcomes.
    Returns (b_only, a_only, p_value) where b_only = cases b passed and a failed."""
    a = list(a)
    b = list(b)
    n01 = sum(1 for x, y in zip(a, b) if (not x) and y)
    n10 = sum(1 for x, y in zip(a, b) if x and (not y))
    n = n01 + n10
    if n == 0:
        return n01, n10, 1.0
    k = min(n01, n10)
    # two-sided binomial tail with p=0.5
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return n01, n10, min(1.0, 2 * tail)


# ---------------------------------------------------------------- io
def write_jsonl(path: str, rows: Iterable[dict]) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
