# BUILD-INDEX

Purpose: build the work package in `packages/` (one brief, `WP-*.md`). The brief is the specification: read it fully before writing code.

Where things live: `packages/WP-*.md` (brief) · `provided/` (provided store and fixture; read-only) · `tests/acceptance/` (engineer's tests; read-only) · `src/` (your code) · `build/state.json` (state) · `build/questions.json` (questions for the owner).

## Hard rules
1. Never edit `tests/acceptance/`, `provided/`, `conftest.py`, `Makefile` or `.claude/` (read-only; a hook blocks edits). If a test looks wrong, file a test-change request in `build/questions.json`.
2. Never invent a decision in a protected area (access control, visibility, erasure, anything that could expose data). If the brief is unclear or contradictory there: write the question to `build/questions.json`, build that part fail-closed, finish the rest, and say so in your final message.
3. Unprotected gaps (formatting, defaults, internal structure): choose the most reversible option and note it in `build/state.json` under `"rulings"`.
4. No hard-coded identities, no special cases for test data.
5. Work in place on the current branch; no worktrees; never push.

## Session loop
Read `build/state.json` → read the brief → build step by step → `make test` → commit and update `build/state.json` after each step → stop at the done line or a stop rule.

## Stop rules
Three identical failures → blocker note in `build/state.json`, stop. Protected question → rule 2. Context running low → checkpoint, stop.

## Verification (once, at the end, before claiming done)
Run the saved workflow `wp-verify` with the Workflow tool. Check each finding yourself, fix the confirmed ones, re-run `make test`, then checkpoint. Never claim "done" without that evidence.

Keep tool output small: concise test output; search large files rather than reading them whole.
