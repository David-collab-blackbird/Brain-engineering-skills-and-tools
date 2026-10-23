# BUILD-INDEX

Purpose: build the work package in `packages/` (one brief, `WP-*.md`). The brief is the specification: read it fully before writing code. Then follow the `brain-builder` skill (`.claude/skills/brain-builder/SKILL.md`).

Where things live: `packages/WP-*.md` (brief) · `provided/` (provided store and fixture; read-only) · `tests/acceptance/` (engineer's tests; read-only) · `src/` (your code) · `build/state.json` (state) · `build/questions.json` (questions for the owner) · `scripts/` (gate scripts).

## Hard rules
1. Never edit `tests/acceptance/`, `provided/`, `packages/`, `conftest.py`, `Makefile`, `scripts/` or `.claude/` (read-only; a hook blocks edits). If a test looks wrong, file a test-change request in `build/questions.json`.
2. Protected areas (access control, visibility, erasure, anything that could expose data): never invent a decision. If the brief is unclear or contradictory there: write the question to `build/questions.json`, build that part fail-closed, finish the rest, and say so in your final message.
3. Unprotected gaps: choose the most reversible option and log it in `build/state.json` → `rulings`.
4. No hard-coded identities, no special cases for test data.
5. Work in place on the current branch; no worktrees; never push.
6. A claim is not evidence. "Done" needs the gate in the skill: tests run by you, reviewer verdict, gate-scan output.
