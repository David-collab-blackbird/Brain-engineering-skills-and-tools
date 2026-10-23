# Gate catalogue (what scripts/gate_scan.py tags)

Concept credit: gstack's gate-integrity catalogue (itself adapted from a third-party reward-hacking list); our wording and our script. The scanner inventories and tags; it never judges. You dispose of every tag.

| Tag | Pattern | Why it matters |
|---|---|---|
| G1 test-protected-edit | any change under tests/acceptance, provided, packages, conftest.py, Makefile | engineer-owned; editing them is tampering |
| G2 skip-or-xfail | `pytest.skip`, `@pytest.mark.skip`, `xfail`, `unittest.skip` added | silences a gate |
| G3 fixture-literal | an id from provided/fixture.json appears in src/ | special-casing test data |
| G4 test-name-branch | src/ reads `PYTEST_CURRENT_TEST`, `sys.argv`, `"pytest" in sys.modules`, or test file names | behaves differently under test |
| G5 swallowed-exception | `except:` or `except Exception:` followed by `pass`/`return`/`continue` in src/ | hides failures, may fail open |
| G6 suppression | `# noqa`, `# type: ignore`, `# pragma: no cover` added | silences tooling |
| G7 broad-allow | src/ grants all groups, all rows, or bypasses the visible set (e.g. `SELECT id FROM acl_groups` without a membership join) | fail-open access |
| G8 relaxed-threshold | a numeric constant in src/ that differs from the brief's stated value | silent spec drift (reviewer checks; not scanned) |
