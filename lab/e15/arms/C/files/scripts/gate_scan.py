#!/usr/bin/env python3
"""Gate scan (engineer-owned). Inventories risky patterns in the diff since the
template commit and in src/. Tags only; never judges. See
.claude/skills/brain-builder/references/gate-catalogue.md.
Concept credit: gstack gate-integrity catalogue; our implementation."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sh(*a):
    return subprocess.run(a, cwd=ROOT, capture_output=True, text=True).stdout


def main():
    base = sh("git", "rev-list", "--max-parents=0", "HEAD").split()[0]
    tags = []
    changed = [l for l in sh("git", "diff", "--name-only", base, "--").splitlines()]
    changed += [l[3:] for l in sh("git", "status", "--porcelain").splitlines()]
    for f in sorted(set(changed)):
        if re.match(r"(tests/acceptance|provided|packages)/|conftest\.py$|Makefile$|scripts/", f):
            tags.append(("G1", f, "engineer-owned file changed"))
    src = list((ROOT / "src").rglob("*.py"))
    tests = list((ROOT / "tests").rglob("*.py"))
    fx = json.loads((ROOT / "provided/fixture.json").read_text())
    ids = set(fx.get("tenants", []))
    for key in ("principals", "groups", "records", "entities", "notes"):
        ids |= {x["id"] for x in fx.get(key, []) if isinstance(x.get("id"), str)}
    pats = {
        "G2": re.compile(r"pytest\.skip|mark\.skip|xfail|unittest\.skip"),
        "G4": re.compile(r"PYTEST_CURRENT_TEST|sys\.argv|['\"]pytest['\"]\s+in\s+sys\.modules|test_\w+\.py"),
        "G5": re.compile(r"except\s*(Exception)?\s*:\s*(\n\s*)?(pass|return|continue)\b"),
        "G6": re.compile(r"#\s*(noqa|type:\s*ignore|pragma:\s*no cover)"),
        "G7": re.compile(r"SELECT\s+id\s+FROM\s+acl_groups(?![^\n]*memberships)", re.I),
    }
    for p in src + tests:
        t = p.read_text(errors="replace")
        rel = p.relative_to(ROOT)
        for tag, rx in pats.items():
            if tag in ("G2",) and p in src:
                pass
            for m in rx.finditer(t):
                line = t.count("\n", 0, m.start()) + 1
                if tag == "G2" and "tests/acceptance" in str(rel):
                    continue
                if tag in ("G4", "G5", "G7") and p not in src:
                    continue
                tags.append((tag, f"{rel}:{line}", m.group(0).strip()[:60]))
        if p in src:
            for i in sorted(ids):
                for m in re.finditer(rf"(?<![\w-]){re.escape(i)}(?![\w-])", t):
                    tags.append(("G3", f"{rel}:{t.count(chr(10), 0, m.start()) + 1}", i))
    if not tags:
        print("gate_scan: no tags")
    for t in tags:
        print(f"{t[0]}  {t[1]}  {t[2]}")
    print(f"gate_scan: {len(tags)} tag(s). Dispose of each in build/state.json -> gate_dispositions.")


if __name__ == "__main__":
    sys.exit(main())
