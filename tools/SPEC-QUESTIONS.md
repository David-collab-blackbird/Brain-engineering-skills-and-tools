# Spec questions for the engineer (GUARD-TOOLS.md @ 0a93242)

Found so far while writing tests. Each is marked `# SPEC-AMBIGUITY` where a test relies on it.

## All tools (§0)
1. Bad input with no named rule (malformed manifest, missing file): tests accept exit 2, or exit 1 with a reported finding; never 0.
2. `line` for file-level findings (MISSING, UNLISTED): tests accept an integer ≥0 or null; text form must still be `<path>:<line>`.
3. "evidence" in the fingerprint (`rule|path|evidence`) is undefined; tests check only 16 hex, determinism, and distinct paths giving distinct fingerprints.
4. JSON `version`: assumed to be the tool's semver from `VERSION`.
5. `D…` arguments (`--root D…`) read as several values after one flag (`--root a b`), not a repeated flag.
6. Output encoding: tests pin `PYTHONIOENCODING=utf-8`, plus one test with the platform default to check a unicode path does not crash the tool on Windows.
7. Where tools read engineer config (`protected_paths.json`, `required-checks.json`): beside the script (base checkout) or in `--repo`? Tests will install canonical copies in the fixture repo.
8. `run_guards.py` has no ET number: which folder owns it?

## ET-01
9. Manifest "sorted": the real manifest is sorted by path, not by line; tests assume codepoint order of the POSIX path.
10. An absent `EXPECTED_COUNTS.json` is assumed not to be a finding (ET-07 reuses `verify` on the hidden repo, which has `expected.json` instead).
11. "Positive integer": `true`, `2.0`, `"2"` are assumed invalid.
12. Binary files: CRLF→LF assumed to apply too (the spec makes no exception).
13. `generate`: how does it know which file is the manifest, to exclude it?
14. `SHA256SUMS`: paths assumed relative to `.github/guards/`, file excludes itself; CRLF normalisation unstated.
15. `pr`: rule name when an unchanged suite fails against the base manifest (`CHANGED` or `MANIFEST-MISMATCH`)?

## Other tools (noted before stopping, no tests yet)
16. ET-02: E16 RH-12 requires a tag on the `sys.argv` sniff variant, but the RH-12 row in GUARD-TOOLS does not list `sys.argv`.
17. ET-02: the E16 RH-1 variant `-k` deselect via builder `pytest.ini` has no trigger in the tag table.
18. ET-02: `RH-3 / X2` and `PL-1 / PL-2`: which rule name is emitted?
19. ET-02: `literal_scan` is "advisory": exit 1 on findings (§0) or exit 0?
20. ET-03: how does the tool know T-3 exists (builder login equal to owner login?), and how does it treat owner-login PRs before T-3 (no SELF-MERGE / NO-OWNER-APPROVAL)? The facts schema has no labels, so `known-gap-T3` cannot be seen.
21. ET-03: are `skipped` and `neutral` conclusions "unsuccessful"?
22. ET-04: `privacy-baseline.json` format; whether an empty `PRIVACY_ALIAS_TABLE` (what GitHub passes for an unset secret) counts as absent.
23. ET-05: rule 11 (`eval/results/`) is outside the lint scope; rule 16 and "process text ≤3k tokens" have no checkable definition.
24. ET-07: hidden manifest file name, unittest ID format in `expected.json`, `request` inbox/outbox protocol and timeout.
25. ET-08: `sign` arguments; HMAC key file encoding (raw bytes or hex); whether `claim` writes the state file.
26. ET-09: where `protect.py` logs decisions (E16-L7); whether mixed-case protected paths are denied on Linux too.
