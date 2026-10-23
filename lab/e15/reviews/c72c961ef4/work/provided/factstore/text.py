"""Text helpers for WP-E15C (provided; do not modify)."""
from __future__ import annotations

import json
import re
import unicodedata

_TOKEN = re.compile(r"\w+")


def tokens(text: str) -> list[str]:
    """NFKC + casefold + \\w+ runs. The tokeniser WP-E15C uses everywhere."""
    return _TOKEN.findall(unicodedata.normalize("NFKC", text or "").casefold())


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
