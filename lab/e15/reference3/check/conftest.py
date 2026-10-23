# Engineer-owned: puts the package and the provided store on sys.path.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (ROOT / "src", ROOT / "provided"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
