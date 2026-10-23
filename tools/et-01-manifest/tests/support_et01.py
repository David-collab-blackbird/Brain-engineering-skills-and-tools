# Independent test author session, written from GUARD-TOOLS.md @ 0a932426d49848d4afdd43fe18a34ac2bcdbf06e on 2026-10-24; implementation not seen.
"""Fixtures for the ET-01 tests: a synthetic acceptance suite and an independent
oracle for the manifest format in GUARD-TOOLS ET-01 (SHA-256 after CRLF->LF,
lines `<hex>  <path>`, sorted, `#` comments, manifest excludes itself,
`__pycache__/` and `*.pyc` ignored)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_testkit"))
import guardkit as K

TOOL_DIR = "et-01-manifest"
SCRIPT = "manifest_check.py"
MANIFEST = "tests/acceptance/MANIFEST.sha256"
ROOT = "tests/acceptance"

TEST_ALPHA = (
    "import unittest\n\n\n"
    "class AlphaTests(unittest.TestCase):\n"
    "    def test_one(self):\n"
    "        self.assertTrue(True)\n\n"
    "    def test_two(self):\n"
    "        self.assertEqual(1, 1)\n"
)
TEST_BETA = (
    "import unittest\n\n\n"
    "class BetaTests(unittest.TestCase):\n"
    "    def test_three(self):\n"
    "        self.assertIn(3, [1, 2, 3])\n"
)

SUITE = {
    "tests/acceptance/EXPECTED_COUNTS.json": json.dumps({"WP-A": 2, "WP-B": 1}, indent=2) + "\n",
    "tests/acceptance/WP-A/test_alpha.py": TEST_ALPHA,
    "tests/acceptance/WP-A/fixtures/world.json": '{"items": [1, 2, 3]}\n',
    "tests/acceptance/WP-A/fixtures/golden/receipts.json": '{"receipt": "r-001"}\n',
    "tests/acceptance/WP-B/test_beta.py": TEST_BETA,
}


def tool():
    return K.tool_path(TOOL_DIR, SCRIPT)


def manifest_entries(root: Path, roots=(ROOT,), exclude=(MANIFEST,)):
    entries = []
    for r in roots:
        base = root / r
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if rel in exclude:
                continue
            if "__pycache__" in p.relative_to(root).parts or p.name.endswith(".pyc"):
                continue
            entries.append((rel, K.lf_sha256(p.read_bytes())))
    entries.sort(key=lambda e: e[0])
    return entries


def manifest_text(root: Path, roots=(ROOT,), exclude=(MANIFEST,), comments=True, newline="\n"):
    lines = []
    if comments:
        lines.append("# SHA-256 of every visible acceptance-test file (CRLF normalised to LF).")
        lines.append("# Synthetic fixture written by the ET-01 tests.")
    lines += [f"{h}  {rel}" for rel, h in manifest_entries(root, roots, exclude)]
    return newline.join(lines) + newline


def write_manifest(root: Path, roots=(ROOT,), path=MANIFEST, **kw):
    K.write_bytes(root, path, manifest_text(root, roots, exclude=(path,), **kw))


GUARDS = {
    ".github/guards/VERSION": "tools v0.1.0 " + "0" * 40 + "\nET-01 0.1.0\nET-02 0.1.0\n",
    ".github/guards/gate_tags.py": "# vendored guard (fixture placeholder, never executed)\n",
    ".github/guards/hooks/protect.py": "# vendored hook (fixture placeholder, never executed)\n",
    ".github/guards/protected_paths.json": json.dumps(K.PROTECTED_PATHS, indent=2) + "\n",
}


def sha256sums_text(root: Path) -> str:
    # SPEC-AMBIGUITY: SHA256SUMS paths are taken relative to .github/guards/ (as
    # sha256sum prints them when run there) and the file excludes itself. Fixture
    # files are LF-only, so CRLF normalisation makes no difference here.
    gdir = root / ".github/guards"
    entries = []
    for p in gdir.rglob("*"):
        if p.is_file() and p.name != "SHA256SUMS" and "__pycache__" not in p.parts:
            entries.append((p.relative_to(gdir).as_posix(), K.sha256_hex(p.read_bytes())))
    entries.sort(key=lambda e: e[0])
    return "".join(f"{h}  {rel}\n" for rel, h in entries)


def write_sums(root: Path):
    K.write_bytes(root, ".github/guards/SHA256SUMS", sha256sums_text(root))
