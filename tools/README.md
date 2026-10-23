# Guard tools: independent tests (work in progress)

Tests are written by a separate test-author session from `blackbird-hub/blueprint/GUARD-TOOLS.md` @ `0a93242` (QUALITY.md §1); implementation not seen. Shared helpers: `tools/_testkit/guardkit.py`. Tools are looked for at `tools/<tool-dir>/src/<script>` or `$GUARD_TOOLS_DIR/<script>` (a vendored `.github/guards/`). A missing tool is a test failure, never a skip.

Run all tests: `python -m unittest discover -s tools -p "test_*.py"`

| Tool | Folder | Script(s) | Tests |
|---|---|---|---|
| ET-01 test-hash manifest | `et-01-manifest/` | `manifest_check.py` | 43 (`verify` only; `generate`, `pr` and CLI tests not yet written; no SPEC.md copy yet) |
| ET-02 cheat flagger | — | `gate_tags.py`, `literal_scan.py`, `claim_verify.py` | not yet |
| ET-03 main-branch tripwire | — | `tripwire.py` | not yet |
| ET-04 privacy and secret scan | — | `privacy_scan.py` | not yet |
| ET-05 standards lint | — | `standards_lint.py` | not yet |
| ET-06 decision-marker checker | — | `marker_check.py` | not yet |
| ET-07 judge | — | `judge.py` | not yet |
| ET-08 build-state checker | — | `state_check.py` | not yet |
| ET-09 session hooks | — | `hooks/protect.py`, `hooks/session_start.py` | not yet |
| run_guards.py (§0 entry) | — | `run_guards.py` | not yet |

Stopped early on 2026-10-24 (owner instruction: usage limit). All 43 ET-01 tests fail without an implementation.
