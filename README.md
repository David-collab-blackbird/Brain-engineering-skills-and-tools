# Brain engineering skills and tools

Skills (procedures for Claude agents) and tools (tested code) for building and engineering the brain and the apps around it. Run on the principle **the engineer builds the instruments; the builder builds the brain**, and on the owner's rule that **nobody designs their own test and marks it**, the engineer included (`QUALITY.md`).

## Layout

| Path | Holds | Who uses it |
|---|---|---|
| `.claude/skills/<name>/SKILL.md` | Engineer skills. They load automatically into any engineer session that attaches this repo | Engineer |
| `skills-shared/<name>/` | Skills for other agents (builder, app agents), copied into each product repo at a released version | Builder and app agents |
| `tools/<name>/` | Tools: `SPEC.md` (what it must do), `src/`, `tests/` (written independently from the spec), `CHANGELOG.md` | CI in the product repos, the engineer's lab |
| `releases/` | Release notes: which version of which skill or tool went where | Everyone |

## How a skill or tool reaches other agents

1. Built here to its spec. Tests are written independently and passing in CI (`QUALITY.md`).
2. Reviewed in a pull request and **approved by the owner's main account**. The engineer's account never approves its own work.
3. Tagged as a release.
4. Copied into the product repo (e.g. `blackbird-hub/.github/guards/`, later the brain and Aviary repos) at that release, **pinned by checksum**. A change here never reaches a product repo until a new release is copied over by pull request.
5. Proven engineer skills are also released to the owner's claude.ai account, so ordinary chats use the same versions.

## Planned first contents

- **Guard tools** (specs in `blackbird-hub/blueprint/GUARD-TOOLS.md`): acceptance-test hash-manifest check, cheat flagger (regression suite: every planted cheat in E16 must stay caught), main-branch tripwire, privacy and secret scan, standards lint, decision-marker checker, and the hidden-test runner that reports only pass/fail counts.
- **Lab instruments:** certification statistics (Clopper–Pearson, Wilson), preregistration hashing, spend cap and process reaper, project-mirror sync.
- **Skills:** the brain research protocol v2, running a preregistered experiment, making a blueprint change, writing a package brief with its hidden tests, running a consistency review, briefing a sub-agent.
