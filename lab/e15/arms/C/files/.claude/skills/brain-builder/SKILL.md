---
name: brain-builder
description: Use when building or resuming a brain work package (packages/WP-*.md). Session loop, done gate, stop rules, reviewer seat.
---

# brain-builder

Our builder process for brain work packages. Written by the engineer in our own words. Ideas adapted, with thanks, from obra/superpowers v7.0.1 (MIT, © 2025 Jesse Vincent: task-reviewer stance, verification-before-completion, systematic debugging, ledger-after-compaction) and garrytan/gstack v1.91.182.0 (MIT, © 2026 Garry Tan: gate-integrity catalogue, "claims need evidence", test value statements, resume provenance markers). No text copied.

## Hard rules (also in CLAUDE.md)
Engineer-owned files are read-only. Protected areas pause, never guess. No hard-coded identities. "Done" requires the gate below.

## Session loop
1. **Resume first.** Read `build/state.json`. Items in `next` carry a provenance marker: `(run)` you executed it and saw the result, `(read)` you read the code, `(assumed)` not checked. Re-verify `(assumed)` and `(read)` items before building on them. Trust `state.json` and `git log` over memory, especially after compaction.
2. **Read the brief** fully, once. List its protected rules (access control, visibility, leakage, erasure, staleness) before you build.
3. **Build step by step** (the brief's Steps). After each step: `make test` (concise output), commit with the step name, update `state.json` (`done`, `next` with markers, `last_commit`, `rulings`).
4. **Write your own unit tests** in `tests/unit/` for behaviour the brief states but the acceptance tests do not cover. Give each test a one-line value statement in its docstring: `protects: <rule>; fails_when: <defect>`. A test that cannot fail is worthless; check it fails on a deliberate break before you trust it.
5. **Gate** (below), then checkpoint and stop at the done line.

## Debugging (when a test fails)
Reproduce, read the full error, form one hypothesis, test it with the smallest change. Root cause before fix. Three failed fixes on the same problem → stop, write a blocker in `state.json` (what you tried, the evidence, your hypothesis). Never weaken a test, a threshold or an access check to get green.

## Done gate (all four, in order)
1. **Run** `make test` and `python -m pytest -q tests/unit` yourself now; read the output. A pass you did not see is not a pass.
2. **Gate scan:** `python scripts/gate_scan.py`. It inventories risky patterns (see `references/gate-catalogue.md`). For each tag, either fix it or justify it in `state.json` → `gate_dispositions`. Never suppress.
3. **Reviewer seat:** dispatch the `wp-reviewer` subagent (Agent tool, `subagent_type: "wp-reviewer"`). Give it only: the brief path, the base commit, and "review HEAD". Do not tell it what to ignore or what you think is fine.
4. **Act on findings:** verify each finding yourself (reproduce it). Fix confirmed ones, re-run step 1. If you disagree, say why with evidence in `state.json` → `review_dispositions`. At most 2 review rounds; then stop and record what remains.

Only then set `status: "passed"` with the commit id, and in your final message report: test results you saw, gate tags and dispositions, reviewer findings and what you did, rulings, open questions.

## Evidence rules
- Name the kind of evidence for every claim: test run, probe script output, quoted `file:line`, or "not checked".
- A report (yours, a subagent's, a reviewer's) is a claim until re-executed.
- Confidence needs a quote: if you cannot point at the line, say "not checked".

## Stop rules
Protected-area question → CLAUDE.md rule 2. Three identical failures → blocker. Context running low → checkpoint with markers, stop.
