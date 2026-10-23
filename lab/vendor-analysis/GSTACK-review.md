---
id: GSTACK-review
type: blueprint
title: "gstack: adversarial review for the brain builder"
status: draft
version: 1.0
date: 2026-10-23
author_role: engineer
supersedes: []
superseded_by: null
decisions: [ADR-006, ADR-007, ADR-010, ADR-011, ADR-014, ADR-016, ADR-018, ADR-019]
tests: []
evidence: []
sensitivity: none
---

# gstack: adversarial review for the brain builder

Status: DRAFT v1 (2026-10-23) · Reviewer: Claude (engineer, adversarial role) · Subject: `garrytan/gstack` v1.91.182.0 (VERSION file; CHANGELOG top entry 2026-10-23), MIT, © 2026 Garry Tan · Vendored tree: `/home/claude/vendor-skills/gstack/gstack-main/` (78 MB, 3,942 files by `find -type f`; 65 `SKILL.md` files, 2 of them test fixtures) · Companion review: `SUPERPOWERS-review.md` (same folder). GBrain internals are covered by a separate reviewer; this document only covers how gstack wires GBrain in.

Moves: H19 (small always-loaded index), U4 (maker never checks its own work), ADR-019 (work packages), DA1 §8–9, DA3 (egress, supply chain), I16 (code / System One / System Two).

**Evidence tags.** Status: **OBSERVED** (read the code or primary source, or measured it with my own script) / **INFERRED** (reasoned from evidence) / **UNKNOWN**. Strength: independent / vendor / single study / secondary / anecdote. Every repo file was treated as data. I did not run `./setup`, any install script, the browser or any binary. Measurement scripts live in `/tmp/claude-0/-home-claude/4c8492a6-f948-5903-9334-5b76eec5c7f7/scratchpad/gs/scripts/`.

**Token method.** Bytes are exact. Tokens are given two ways:
1. gstack's own calibrated estimate: 4.21 bytes/token for SKILL.md bodies, fitted to `count_tokens` on claude-opus-4-5 (`lib/context-bill.ts`; gstack warns newer tokenizers differ);
2. a proxy count with the Qwen3 BPE tokenizer, run locally.

The two agree within about 5%. Treat every token figure as ±15%.

---

## 0. Verdict in one page

**What it is.** gstack is a very large, very actively developed Claude Code "software factory": 57 skills in the Claude catalog, plus ~160 `bin/` helpers, compiled Bun binaries, a Playwright/Chromium browser daemon with a Chrome side-panel agent, a containerised security auditor, hooks written into `~/.claude/settings.json`, an update channel, opt-in telemetry and a GBrain integration. Each skill is a role ("CEO", "Eng Manager", "Staff Engineer", "QA Lead", "CSO", "Release Engineer") wrapped around a long procedure. Skills are generated from `.tmpl` templates with shared resolvers, so every workflow skill carries the same ~28 KB preamble. About 60% of the TypeScript is tests (340k of 563k lines).

**Footprint and security (OBSERVED).**
- `./setup` needs Bun ≥1.3.3, then:
  - runs `bun install`, falling back from `--frozen-lockfile` to an **unpinned** install if the frozen install fails;
  - compiles 5 binaries plus an optional C-built CSO launcher;
  - downloads Chromium via Playwright;
  - registers hooks in `~/.claude/settings.json`: a default-on Stop hook, the AskUserQuestion pre/post hooks, and in team mode a SessionStart auto-updater.
- **Team mode** silently fast-forwards from GitHub and re-runs `./setup` within an hour on every teammate's machine. It checks that hooks parse; it does not verify signatures.
- **Outside reviews are on by default.** Plan, review and ship passes send code, diffs and plans to OpenAI Codex.
- Telemetry is opt-in, off by default, but the prompt marks "Yes" as recommended.
- The install instructions tell Claude to write "never use `mcp__claude-in-chrome__*` tools" into CLAUDE.md. Other skills append routing rules, config blocks and GBrain guidance to CLAUDE.md, and one of them commits the change itself.
- Much of the security engineering is genuinely good: hash-chained egress receipts, session-bound instruction blocks, fail-closed edit fences, digest-pinned CSO containers and a secret-leak harness.

**Token cost.**

*Always loaded (OBSERVED, small):*
- The skill catalog is ~5.1 KB (~1.3k tokens).
- CLAUDE.md additions are 2–5 KB.
- Together, ~1.8–2.6k tokens per session. That nearly doubles our ≤8 KB index layer.

*Per invocation (OBSERVED, large):*

| Invocation | Tokens of process text |
|---|---|
| Shared preamble alone | 6.6–7.8k |
| `/plan-eng-review` | ~35k |
| `/review` | ~38k |
| `/ship` | ~70k |
| `/autoplan` (CEO plus Eng, no UI or DX) | **~97–115k** |

All figures are process text only, before any plan, code or tool output. `/autoplan` alone is 1.7–2× the 58k of mandatory reading that stalled the owner's last builder, and 12× our 8k package budget. Invoked skills stay in context for the rest of the session, so `/review` + `/qa` + `/ship` in one session stack to ~125k tokens, including the same 28 KB preamble three times.

**Top 5 for:**
1. **Gate-integrity machinery.** A catalog of 13 reward-hacking patterns: test removed, test skipped, golden regenerated, timeout or threshold relaxed, suppression pragma, `--no-verify`, environment sniffing, swallowed exceptions. A deterministic diff tagger (`gstack-gate-diff`) inventories and tags hunks and never judges; a human disposes of each finding. This is the best defence-in-depth complement to our read-only tests.
2. **Evidence discipline written as rules.**
   - "Claims Need Evidence": name the evidence kind; a mock is not a live check.
   - "Quote the line or confidence ≤5."
   - A test value card: `protects` / `fails_when` / `no_claim`.
   - "A report is a claim until re-executed."
   - Provenance markers on resume items: `(path run)`, `(path read)`, `(path assumed)`.
3. **Systematic plan-review coverage.** Error and rescue map, failure-modes registry, "NOT in scope", "what already exists", observability, rollout, test plan. Our DA reviews do not systematically cover the operational sections.
4. **Eval spend discipline (`/eval-plan`).** Preregistration (bars, arms, decoys, stop rules, held-out exposure), a $0 stub-model dry run over the real rows, a priced n≈3 pilot with a locked spend ledger, and an approval gate. It maps directly onto ADR-018 certification runs.
5. **Reusable primitives that connect to the brain's own design:**
   - the egress receipt ledger (receipt before send, fail-closed for sensitive sinks), which is the same primitive as DA3's delivered-content ledger;
   - the agent-ready error contract, since agents are the readers of the brain's MCP errors;
   - a context-budget ratchet test that caps per-skill tokens in CI (H19);
   - a decision log JSONL with supersede.

**Top 5 against:**
1. **Token cost and context rot.** The cost above, plus a layout that puts 28 KB of identical boilerplate first in every skill. After compaction, Claude Code re-attaches only the first 5,000 tokens of each invoked skill, which for gstack is nearly all preamble.
2. **Egress and supply chain against our posture:**
   - default-on cross-vendor outside reviews;
   - web research routed through a third-party agentic browser (Aside) first;
   - team-mode auto-update without signatures;
   - an unpinned 112 MB HuggingFace model download;
   - an unpinned-dependency fallback in setup;
   - about 6 releases a day in October 2026, so nobody can review what they run.
3. **Same model in every "specialist" seat.** Role personas do not improve accuracy (Wharton GAIL, six models). Homogeneous debate is unreliable. The 1–10 confidence scores are uncalibrated self-reports. The only diversity lever, Codex as outside voice, is exactly the egress we restrict.
4. **Autonomy and scope bias against our stop rules:**
   - "Boil the Ocean";
   - `/autoplan`'s six auto-decide principles ("Bias toward action — Merge > review cycles"; auto-approve expansions under a day of effort);
   - spawned sessions auto-choose the recommended option at every decision point.

   Our protocol is "never invent a decision; stop at the done line." gstack does carve out user challenges and destructive options.
5. **Builder writes and owns tests; lock-in; churn.**
   - `/ship` and `/qa` bootstrap test frameworks and write tests.
   - It is Bun, Git Bash and Playwright-centric, and Windows is second-class (the owner's host is Windows).
   - CLAUDE.md rewrites and team-mode "required" hooks block work without gstack.
   - 422 releases in 7 months, with versions chosen autonomously by an agent.
   - Much of the surface is irrelevant to us: iOS, design, landing reports, office hours, PDF, browser stealth, pair-agent tunnels.

**Verdicts (detail in §7):**
- **Adopt** (rewritten, attributed): gate-integrity patterns plus a tagger; evidence rules; test value card; resume provenance markers; eval preregistration and priced pilot; confidence-requires-quote; the investigate core; the context-budget ratchet.
- **Adapt:**
  - plan-review section list → DA coverage checklist;
  - review specialists → reviewer-seat checklists, cross-family and local;
  - CSO phases 7 (LLM/agentic/MCP), 10 (STRIDE) and 11 (data classification) → security review checklist;
  - context-save → `state.json`;
  - learnings with decay → reviewed build-learnings file;
  - qa-only → MCP and API surface QA;
  - egress receipts and the agent-ready error contract → brain design inputs.
- **Reject:**
  - installing gstack in any environment that touches brain data;
  - team mode and auto-update;
  - CLAUDE.md rewrites and the routing injection;
  - the "never use Claude in Chrome" instruction;
  - default-on outside reviews;
  - autoplan's auto-decide principles;
  - `/ship`, `/land-and-deploy`, `/canary`;
  - the GBrain integration;
  - telemetry and Aside research;
  - all design, iOS, browser and productivity skills.

**gstack as part of the brain: procedural memory (§9A).**
- About ten gstack procedures are generic and good enough to rewrite, with attribution, as brain SOPs:
  - Diagnose a fault, from investigate;
  - Run a costed batch job, from eval-plan;
  - Ask the owner for a decision, from the decision brief;
  - Hand off a task, from context-save/restore;
  - Write a task brief, from spec;
  - Review a plan, from the plan-review registries;
  - Assess an incident or finding, from the CSO evidence rubric;
  - Verify a system works, from qa-only;
  - Memory hygiene, from learn prune;
  - Failure reporting, from agent-ready errors.
- The mechanisms teach more than the texts do:
  - two-tier delivery with a CI-capped index;
  - a skeleton plus condition-triggered sections;
  - code-derived state lines;
  - nonce-bound directives that retrieved content cannot forge;
  - per-procedure declarative context queries;
  - a tested, approved promotion pipeline (skillify);
  - one-way/two-way door tagging;
  - per-client "enforced vs advisory" labels.
- What to avoid:
  - procedures that grant tools (`allowed-tools`) or run code (frontmatter hooks, bash);
  - procedures that persist instructions to CLAUDE.md;
  - unsigned remote updates;
  - default egress;
  - auto-logged learnings injected into every run;
  - auto-promotion by "3 uses without a classifier flag".

**Ultracode (§9A.4).**
- gstack never references ultracode or dynamic workflows. Its gates assume AskUserQuestion, which workflow subagents do not have. INFERRED: under ultracode, its human gates turn into unanswered result strings.
- More important for us: ultracode plans several workflows per request, and every subagent loads CLAUDE.md. The owner's previous builder likely paid its 58k of mandatory reading many times per request (GS14).
- Recommendation: ultracode off by default for builders; saved, reviewed workflows only for genuine fan-out packages.

**Hypotheses:** GS1–GS12 (§8) and GS13–GS15 (§9A.5). The two the caller asked for:
- **GS1:** gstack's plan-review roles as our devil's-advocate process. Prediction: complementary coverage, not a replacement.
- **GS2:** context-save/restore versus our checkpoint. Prediction: its provenance markers help, its LLM-written Markdown summary does not.

---

## 1. Frame: questions and evidence needed

| # | Question | Evidence used | Status |
|---|---|---|---|
| 1 | What it is: roles, processes, template generation, always-loaded additions, per-skill reading cost | Read README, ETHOS, ARCHITECTURE (template and security sections), CLAUDE.md, AGENTS.md, SECURITY, DESIGN, BROWSER (outline), root and all focus SKILL.md files and their sections; byte and token measurement of all 65 SKILL.md files and referenced sections | Answered |
| 2 | Install and runtime footprint, security | Read `setup` (4,794 lines, key steps), `scripts/build.sh`, `bin/gstack-skill-start`, `gstack-session-update`, `gstack-team-init`, `gstack-telemetry-sync`, `gstack-config`, `lib/outside-consent.ts`, `browse/src/security-classifier.ts`, `lib/cso/*.json`, `setup-gbrain` sections; third-party scanner pages | Answered (static only) |
| 3 | Case for | Code read; vendor docs; anecdotal reviews; prompting research | Answered; evidence mostly vendor or anecdote |
| 4 | Case against | Code read; measurements; Claude Code docs (skills, memory); research on personas and debate; DA1, DA3, R4 | Answered |
| 5 | Steelman both ways; verdict per component | Synthesis | Answered |
| 6 | Testable hypotheses | Design | Designed, not run |
| 7 | Custom brain-builder skill: take and leave | Synthesis, aligned with the Superpowers review §9 | Answered (outline) |

Prior project inputs reused:
- `handover/BUILDER-PROTOCOL.md`;
- `docs02/ADR-019-resumable-work-packages.md`;
- `challenges/DA1-architecture.md` §8 (ADR-019) and §9 (U4);
- `challenges/DA3-security-privacy.md` §0, §8, §13;
- `research_notes/Weak spots frontier round/r4_security_frontier.md` §1–3;
- `existing/analysis/C-app.md` §3 (the 58k figure);
- `06-hypotheses-board.md` I16 and U4;
- `vendor-skills/analysis/SUPERPOWERS-review.md` (bake-off design and SP hypotheses).

---

## 2. What it is, mechanically

### 2.1 Shape of the repository (OBSERVED)

| Item | Value | Source |
|---|---|---|
| Version | 1.91.182.0 (4-part; `package.json` 1.91.182) | `VERSION`, `package.json` |
| Release cadence | 422 CHANGELOG entries, 2026-03-17 → 2026-10-23; 138 in October alone (~6/day); first entry v0.6.1.0 | `CHANGELOG.md` (1.67 MB) |
| Who picks versions | "Choose versions autonomously; default to PATCH. Garry delegates release version decisions to the agent" | `CLAUDE.md` § CHANGELOG + VERSION style |
| Size | 78 MB; 3,942 files; 563k lines of `.ts`, 341k of them under `test/`; 159 entries in `bin/`; 76 top-level directories | `find`, `wc` |
| Runtime | Bun ≥1.3.3 (setup refuses older: older Bun lets compiled tools read a project `.env`); Bun 1.4.2 tested; Node on Windows | `setup` l.307–330; README |
| Skills | 65 SKILL.md files: 57 authored for the Claude catalog (incl. root router), 4 OpenClaw, 1 Capy, 1 browser-skill example, 2 test fixtures | `find . -name SKILL.md` |
| Hosts | Claude Code (full), Codex, OpenCode, Cursor, Factory, Kiro, Copilot, Antigravity (experimental); Slate, OpenClaw, Hermes, GBrain (instruction-only) | README "Other AI Agents" |
| Dependencies | `playwright` (patched), `@huggingface/transformers`, `@ngrok/ngrok`, `sharp`, `marked`, `html-to-docx`, `socks`, `diff`, `cross-spawn` | `package.json` |

### 2.2 Roles and processes (OBSERVED; focus skills)

The README sells a sprint: **Think → Plan → Build → Review → Test → Ship → Reflect**. Each skill writes an artifact that the next reads: design doc → CEO plan → eng test plan → QA → ship.

| Skill (role) | Process in brief | Mechanical parts |
|---|---|---|
| `/office-hours` (YC partner) | Six forcing questions, premise challenge, three approaches; writes a design doc | — |
| `/plan-ceo-review` (CEO) | Step 0 "Nuclear Scope Challenge" with 4 modes (Expansion, Selective Expansion, Hold, Reduction); premise table; dream-state delta; 11 sections: architecture, error and rescue map, security and threat model, data flow and edge cases, code quality, tests, performance, observability, deployment and rollout, long-term trajectory, design; failure-modes registry; "NOT in scope"; "What already exists"; default-on outside voice (Codex) | `gstack-plan-reality` rows with `file:line` receipts; review log; PostToolUse hook |
| `/plan-eng-review` (Eng Manager) | Scope challenge with a complexity gate (≥8 files or ≥2 new classes → ask), then architecture, code quality, tests, performance; ASCII diagrams; test plan artifact; failure modes; implementation tasks JSONL; outside voice; "EXIT PLAN MODE GATE" checks the report's exact structure | `gstack-plan-reality`, `gstack-review-log`, `gstack-review-read` |
| `/plan-devex-review` (DX lead) | Personas, time-to-hello-world, friction trace, **agent-ready error** rubric (`docs/agent-ready-errors.md`) | — |
| `/autoplan` (pipeline) | Reads the full CEO, then design if UI, then DX if developer-facing, then Eng methodologies from disk. Answers intermediate questions with six principles; surfaces only "taste" decisions and "user challenges" at one final gate | PreToolUse hooks on Read and Agent deny out-of-order phase loading; snapshot tool hashes; `gstack-gate` parses replies |
| `/review` (Staff Engineer) | Scope drift; checklist; diff scans; critical pass; confidence calibration (quote the line or ≤5); "Review Army" parallel specialists (testing, maintainability, security, performance, data-migration, API contract, design, simplification, state machines); exploratory QA; adversarial pass; Fix-First (auto-fix obvious, ASK others); gate integrity | `gstack-gate-diff`, `gstack-specialist-stats` (auto-gates specialists with 0 findings in ≥10 dispatches, except security, data-migration and state-machines), review receipts bound to a working-tree fingerprint |
| `/investigate` (Debugger) | Iron Law: no fixes without root cause; hypothesis → test; 3 failed hypotheses → stop and ask; regression test must fail before and pass after; >5 files → ask; recipes for flakes, test polluters, races, eval bisects | Auto-freeze of edits to the module under investigation (hook) |
| `/qa`, `/qa-only` (QA Lead / Reporter) | Surface selection (browser, API, CLI, job, webhook); exploratory probes with `exploration-NNN.json` evidence notes; repro → failing regression → fix → re-verify; stop after 2 reverts, after an unrelated-file edit, or at 50 fixes. `/qa-only` is report-only | Executable deadline guard; evidence ledger |
| `/cso` (CSO) | Phase 0 application model; Phase 1 attack-surface census; Phases 2–11 (infra, supply chain, CI/CD, containers, LLM/agentic/MCP, skill supply chain, OWASP Top 10:2025, ASVS 5.0, STRIDE, data classification); Phase 12 evidence rubric with an independent challenge; reproduction only in hardened containers | Trusted launcher; Docker images pinned by sha256; source read only through the helper's redacted reader; findings never sent to gbrain or telemetry |
| `/careful`, `/freeze`, `/guard`, `/unfreeze` | Session-scoped PreToolUse hooks. careful: warn (ask) on `rm -rf`, `DROP TABLE`, `TRUNCATE`, force-push, `reset --hard`, `kubectl delete` and others; hard-deny `rm -r /`, `~`, `$HOME` and force-push to the default branch. freeze: deny Edit/Write/NotebookEdit outside a directory, fail-closed on unparseable payloads, symlink-aware | `careful/bin/check-careful.sh` (407 lines), `freeze/bin/check-freeze.sh` (210 lines). Both say "not a security boundary": Bash can still write anywhere |
| `/context-save`, `/context-restore` | Save: git state plus an LLM summary (working on, decisions, remaining work with provenance markers, notes) to an append-only timestamped Markdown file under `~/.gstack/projects/<slug>/checkpoints/`, stamped with project identity. Restore: newest checkpoint for this branch; items marked `(path assumed)` or `(code read)`, or naming paths without a marker, go to **Verify first** | Bash-side filename sanitisation; identity stamping |
| `/learn` | Show, search, prune (deleted-file staleness, contradictions), export learnings from `learnings.jsonl` | Confidence decay (1 point per 30 days for observed or inferred); cross-project rows only if `trusted:true` |
| `/retro` | Weekly metrics from git (commits, sessions, hotspots, streaks, shortcut-debt ledger); `/retro global` reads Claude Code, Codex and Gemini session folders | `gstack-global-discover` |
| `/eval-plan` | Preregistration → arms with prices → $0 stub dry run → n≈3 priced pilot under a locked spend ledger → approval ask | `gstack-eval-plan` |
| `/benchmark-models` | Same prompt through Claude, GPT and Gemini; latency, tokens, cost, optional LLM judge | `gstack-model-benchmark` |
| `/test-audit` | Report-only sweep for low-value tests (assertion-free, self-comparisons, source greps, duplicates); retirement cards; edits only an approved batch | Mechanical pre-filter in bash |
| `/spec` | Five phases (why, scope, technical with mandatory code reading, draft, file); outside-review gate blocks below 7/10; "Rules for the implementing agent" | Redaction; dedupe against issues |
| `/ship` (Release Engineer) | Merge base, tests, coverage audit, plan completion, review army, adversarial, version bump, CHANGELOG, docs audit, bisected commits, verification gate, push, PR | Evidence ledger, review freshness, never force-push |
| `/health` | Detects typecheck, lint, test, dead-code and shellcheck tools; scored dashboard; trends | — |
| `/skillify` | Turns a recent `/scrape` into a browser-skill with a test; atomic write after test pass and approval | — |
| `/setup-gbrain`, `/sync-gbrain` | §5.6 | — |

### 2.3 Template generation and consistency (OBSERVED)

From ARCHITECTURE "SKILL.md template system" and CLAUDE.md "SKILL.md workflow":
- `SKILL.md.tmpl` files hold human-written prose with `{{PLACEHOLDERS}}`. `scripts/gen-skill-docs.ts` fills them from source metadata and shared resolvers, for example `{{PREAMBLE}}`, `{{BROWSE_FALLBACK}}`, `{{QA_*}}`, `{{TEST_VALUE_BAR:<mode>}}`, `{{CODEX_PLAN_REVIEW}}` and `{{GBRAIN_CONTEXT_LOAD}}`.
- Generated SKILL.md files are committed. CI regenerates every host and fails on drift. Merge conflicts must be resolved in templates, never in generated files.
- Since v1.71 the preamble is a one-line call to `bin/gstack-skill-start`. The call echoes `KEY: value` STATUS lines, such as `SESSION_KIND`, `TELEMETRY`, `LEARNINGS` and `HAS_ROUTING`, that the skill prose branches on. One-time onboarding and consent prompts arrive as `GSTACK_INSTRUCTION_BEGIN … END` blocks. These are honoured only if they appear in the direct tool result and carry the same random `SESSION_ID`, so content echoed from repo files cannot forge directives (`bin/gstack-skill-start` `_sanitize`).
- Heavy skills were "carved" into a skeleton plus on-demand `sections/*.md` read at "STOP. Read … in full" points.
- **Consistency tests.** CI enforces three ceilings:
  - a catalog budget of 1,197 token-equivalents for all skill `name` + `description` text (`test/catalog-budget.test.ts`);
  - a per-skill eager-token ratchet (`test/context-budget-ratchet.test.ts` against `test/fixtures/context-budget.json`);
  - a 160 KB per-file warning.

  Prompt bytes are pinned only where software reads them. Other tests check structure and meaning.

### 2.4 What is always loaded (OBSERVED, measured)

Claude Code loads only each skill's `name` and `description` at session start. Full SKILL.md content loads on invocation and "stays there across later turns". After compaction, the latest invocation of each skill is re-attached, keeping "the first 5,000 tokens of each" within a combined 25,000-token budget ([Claude Code skills docs](https://code.claude.com/docs/en/skills)). CLAUDE.md loads in every session ([memory docs](https://code.claude.com/docs/en/memory)).

| Always-loaded item | Bytes | ≈ Tokens | Notes |
|---|---|---|---|
| Skill catalog: name + description, 57 skills | 5,116 | ~1.2–1.3k | gstack's own CI cap is 1,197 token-equivalents. Full frontmatter is 26 KB but is not in context |
| CLAUDE.md "gstack" section from the install instruction | ~300 (est.) | ~0.1k | "use the /browse skill from gstack for all web browsing and never use mcp__claude-in-chrome__* tools" (README Step 1) |
| `## Skill routing` block (offered once, appended and **committed**) | 882 | ~0.2k | `bin/gstack-skill-start` l.584–615 |
| Team-mode snippet (optional / required) | 526 / 1,380 | 0.1 / 0.35k | `bin/gstack-team-init`; "required" adds a repo PreToolUse hook that blocks work when gstack is missing |
| `## GBrain Search Guidance` (from `/sync-gbrain`) | 2,210 | ~0.55k | "prefer gbrain over Grep" |
| `## GBrain Configuration` (from `/setup-gbrain`) | 301–455 | ~0.1k | |
| Project config blocks (`/setup-deploy`, `/health`, test-coverage keys) | variable | — | "Persist the answer to CLAUDE.md so we never have to ask again" (CLAUDE.md "Platform-agnostic design") |
| **Total for a fully set-up project** | **~7.3–10.3 KB** | **~1.8–2.6k** | Our BUILD-INDEX cap is 8 KB; gstack alone is about the size of the whole index |

For contrast, gstack's own development CLAUDE.md is 34 KB (~8.7k tokens), more than 4× our index cap. Its CHANGELOG records cutting it from 66.4 KB.

### 2.5 Per-skill reading cost (OBSERVED bytes; tokens ±15%)

The shared preamble is identical across skills. It covers Preamble, plan-mode rules, AskUserQuestion format (~11 KB alone), Voice, Context Recovery, Writing Style, Completeness ("Boil the Ocean"), Confusion Protocol, Claims Need Evidence, Context Health, Question Tuning, Search Before Building, Completion Status, Operational Self-Improvement, Telemetry and Plan Status Footer.

Across the 50 skills that carry it, the preamble measures median **27,970 bytes**, min 8,087, max 30,056, ≈6.6–7.8k tokens, and makes up 36–84% of each focus skill. It sits **first** in the file, right after the frontmatter.

| Path (what a builder would load) | Bytes | Qwen3 tokens | Our 8k package budget |
|---|---|---|---|
| `careful` / `freeze` / `guard` | 4.7k / 4.3k / 3.8k | 1.3k / 1.0k / 0.9k | OK |
| `benchmark-models` | 15.6k | 3.9k | 0.5× |
| `cso` (+ audit phases) | 33.3k | 7.0k | 0.9× |
| `learn` | 33.0k | 8.1k | 1.0× |
| `eval-plan` | 38.6k | 9.5k | 1.2× |
| `test-audit` | 39.5k | 9.7k | 1.2× |
| `context-save` / `context-restore` | 41.2k / 42.5k | 10.1k / 10.4k | 1.3× each |
| `health` | 43.8k | 11.2k | 1.4× |
| `investigate` (no recipe) | 51.1k | 12.4k | 1.5× |
| `qa-only` (+ exploratory, reporting) | 57.2k | 12.9k | 1.6× |
| `qa`, non-browser path (+ scope, exploratory, system-functional) | 64.6k | 15.2k | 1.9× |
| `retro` (+ report format) | 78.3k | 20.1k | 2.5× |
| `spec` (+ gate-and-file) | 87.1k | 22.1k | 2.8× |
| `plan-devex-review` (+ review sections) | 132.9k | 31.6k | 4.0× |
| `plan-eng-review` (+ review sections) | 149.7k | 34.7k | 4.3× |
| `plan-ceo-review` (+ review sections) | 162.6k | 37.6k | 4.7× |
| `review` core path (+ checklist, plan-completion, review-army, adversarial) | 158.6k | 38.2k | 4.8× |
| `ship` typical path (+ 9 sections) | 278.4k | 69.7k | 8.7× |
| `autoplan`, CEO + Eng, no UI or DX (full methodologies) | 415.0k | **97.5k** | **12×** |
| `autoplan` with DX | 563.0k | ~134–156k (estimate) | 17–20× |

**Not measured.** `gstack-skill-start` output: STATUS lines, the top 3 learnings and any instruction blocks; INFERRED 1–3 KB. Also not measured: review-army specialist files (2–9 KB each, 33.5 KB total), loaded inside subagents.

Two independent confirmations:
- gstack's own ratchet fixture lists eager per-invocation ceilings in the same range: `review` 21,047, `ship` 21,081, `plan-ceo-review` 21,007 and `autoplan` 17,005 tokens for SKILL.md alone, before sections.
- The CHANGELOG cites a third-party review in May 2026: "10K+ tokens before any real code is written". It reports the catalog cut 56.6%, from ~9,319 to ~4,045 tokens, and the `/review` eager load halved, from 26.6k to 13.0k tokens.

The authors know about the cost and are working on it. The per-run total is still large.

### 2.6 How gstack wires GBrain in (OBSERVED; GBrain internals out of scope)

- **`/setup-gbrain`, four paths:**
  - PGLite local;
  - Supabase with an existing URL;
  - Supabase auto-provisioned via a **Personal Access Token**. The skill discloses verbatim that the token has "full read/write/delete access to every project in your Supabase account", keeps it in an env var only, and recommends revoking it after setup;
  - remote gbrain MCP with a bearer token. The token sits on argv for ~10 ms during `claude mcp add`, then rests in `~/.claude.json` with mode 0600.
- **MCP registration** is at **user scope**, so every Claude Code session on the machine gets it.
- **Per-repo trust triad:** read-write / read-only / deny.
- **`/sync-gbrain`** registers the repo as a source, runs `gbrain sync --strategy code` and rewrites the CLAUDE.md guidance block. Embeddings call Voyage (`voyage-code-3`) or OpenAI during sync, so repo code goes to the embedding provider.
- **Brain-aware skills:** template resolvers inject `GBRAIN_CONTEXT_LOAD` and `GBRAIN_SAVE_RESULTS` into 10 skills. Five planning skills also read cached digests ("product", "recent-decisions"), filtered by an allowlist (`projects/`, `gstack/`, `concepts/`) (`scripts/resolvers/gbrain.ts`).
- **Transcript ingestion.** Claude Code and Codex session transcripts are ingested into the brain only after an explicit choice of `recent`, `all` or `new`, never auto-chosen in spawned sessions. Gitleaks scanning of ingested pages is **opt-in, off by default**; the cross-machine push has its own scanner (`bin/gstack-memory-ingest.ts` l.126–132).
- **Fit (secondary).** An independent explainer describes GBrain as single-operator by design, with no multi-tenant memory ([vectorize.io](https://vectorize.io/articles/what-is-gbrain)). That is the opposite of our partitioned, multi-principal brain.

---

## 3. Install and runtime footprint, security

### 3.1 What `./setup` does (OBSERVED, `setup`, `scripts/build.sh`)

1. **Checks Bun.** It refuses below the floor and prints a checksum-verified Bun install recipe rather than piping to bash (l.309–318). An older third-party scan flagged `curl … | bash` in `setup-browser-cookies`; that is no longer in the current tree.
2. **Builds** when sources are newer than the build stamp:
   - `bun install --frozen-lockfile 2>/dev/null || bun install` (l.1931 and 6 other sites). **If the frozen install fails for any reason, it silently re-resolves the `^` ranges in `package.json`.** That is an unpinned supply-chain path;
   - renders skills for installed hosts;
   - compiles `browse`, `find-browse`, `design`, `make-pdf` and `gstack-global-discover` with `--no-compile-autoload-dotenv --no-compile-autoload-bunfig`, so a project `.env` or bunfig cannot reach the binaries;
   - optionally builds the CSO launcher, core and watchdog with a C toolchain.
3. **Downloads Chromium:** `bun x playwright install chromium` (l.2255–2280).
4. **Creates state** under `~/.gstack/` and installs skills for each selected host: symlinks on macOS and Linux, copies on Windows (re-run setup after every pull).
5. **Runs migrations and a welcome.**
6. **Registers hooks** in `~/.claude/settings.json`:
   - SessionStart `gstack-session-update` in team mode;
   - Stop `gstack-timeline-stop` (default on);
   - PreToolUse/PostToolUse AskUserQuestion hooks for `/plan-tune` (with consent; skipped on a non-TTY unless flagged);
   - an AUQ error-fallback hook.

   A parse gate refuses hooks that do not parse, and a heal step removes dead entries.
7. **CSO images.** When qualified, it preloads runtime and scanner images from `ghcr.io/garrytan/...@sha256:<digest>`, pinned by digest. Each image gets 30 s, the total is capped at one hour, and partial progress resumes (README, `lib/cso/runtime-catalog.json`).

Uninstall leaves hook entries behind unless `gstack-uninstall` is used, and never edits CLAUDE.md (README "Uninstall").

### 3.2 Network calls at runtime (OBSERVED unless noted)

| Sink | Default | What leaves | Control |
|---|---|---|---|
| Update check (`gstack-update-check`) | **On** | `git ls-remote` github.com plus GET of `VERSION` from raw.githubusercontent.com, at most hourly; with telemetry on, version and OS also go to Supabase | `update_check false` |
| Team-mode auto-update (`gstack-session-update`, SessionStart hook) | On in team mode | `git fetch`, fast-forward, then `./setup -q --refresh-registered` in the background, throttled hourly. Pre-checks: Bun floor and that the incoming hooks parse. **No commit or tag signature check** (grep for `verify-commit`, `verify-tag`, gpg, cosign: none) | `./setup --no-team` |
| `auto_upgrade` (non-team) | Off | — | config |
| Telemetry (`gstack-telemetry-sync`) | **Off** until answered. The first-run prompt marks "Help gstack get better! (recommended)" | Per skill run: skill, outcome, duration, version, OS/arch, session id, redacted error (200 chars), failed step; "community" adds a stable device ID. Repo and branch are stripped before upload. Injection detections add domain, payload hash, score and layer. Destination: Supabase project `frugpmstpnojnhfyimgv.supabase.co` edge function | `telemetry off` |
| **Outside reviews** (Codex from Claude Code; Claude Code from Codex) | **On** ("enabled (default; the first send prints a notice once)") | Review prompt plus repository content, diff or plan, to OpenAI via the user's Codex login. Used by plan reviews, `/autoplan`, `/review` and `/ship` adversarial passes, design review, `/office-hours`, `/document-release`, `/spec`. Plan bodies above 30 KB are truncated | `codex_reviews disabled` (`lib/outside-consent.ts`; an unreadable config counts as disabled) |
| Web research | When a skill researches | Prompt sent to Aside's agent (aside.com) first, then host WebSearch. Skills tell the agent to sanitise: no hostnames, paths, SQL or secrets | Aside absent: falls back to WebSearch |
| Prompt-injection classifier | First use of the sidebar agent (fallback browser) | Downloads ~112 MB ONNX plus tokenizer from `huggingface.co/testsavantai/…/resolve/main`. **Unpinned branch, no checksum** (`browse/src/security-classifier.ts` l.50, 82–132) | `GSTACK_SECURITY_OFF=1` |
| impeccable design engine | On user accept | Binary from GitHub release, **checksum-pinned** | config |
| GBrain embeddings | During `/sync-gbrain` | Repo code chunks to Voyage or OpenAI | Do not use gbrain |
| Artifacts and memory sync | Opt-in | Learnings, plans, retros and timeline to a private git repo; secret scanner before push | `artifacts_sync_mode off` |
| ngrok tunnel (`/pair-agent`) | On use | Exposes a browser-control listener to remote agents with scoped tokens and an allowlist | Do not use |

**Egress receipts (OBSERVED, good).** Every enumerated off-machine sink writes a hash-chained receipt to `~/.gstack/security/egress.jsonl` **before** sending. Sensitive sinks fail closed: brain sync, memory ingest, telemetry, ngrok, Supabase provisioning. User-facing sinks fail open with a warning: design calls, update check. A CI scanner fails on unwired sinks. The authors state the limit: "an audit trail, not a network firewall".

### 3.3 CLAUDE.md and settings rewrites (OBSERVED)

- **Browser exclusivity.** The README install prompt has Claude write a CLAUDE.md section saying "use the /browse skill from gstack for all web browsing and never use mcp__claude-in-chrome__* tools". gstack's own CLAUDE.md says "NEVER use `mcp__claude-in-chrome__*` tools — they are slow, unreliable".
  - INFERRED: the install prompt does not say which CLAUDE.md. A user-level file would override the owner's chosen browser tooling in every project.
- **Routing injection.** The first interactive skill run asks to append `## Skill routing` to the project CLAUDE.md and then runs `git add CLAUDE.md && git commit` (`bin/gstack-skill-start` l.595).
- **Team "required" mode** writes a CLAUDE.md block, "Before doing ANY work, verify gstack is installed… If GSTACK_MISSING: STOP", plus a repo-level PreToolUse enforcement hook.
- **Config persistence.** `/setup-deploy`, `/health`, `/setup-gbrain` and `/sync-gbrain` write sections to CLAUDE.md by design ("The project owns its config; gstack reads it").

### 3.4 Credentials (OBSERVED)

- **Browser cookies** (`/setup-browser-cookies`, fallback browser only):
  - decrypts Chrome, Chromium, Brave, Edge and others' cookie databases through Keychain, libsecret or DPAPI, from a read-only temp copy, into the bundled Playwright context;
  - receipts never contain values;
  - the browser registry is hardcoded and spawned with argument arrays;
  - verification requires an exact identity match.

  Third parties flag this as the main security surface:
  - Socket: "Warn", 14 alerts, MEDIUM on `cookie-import-browser.ts` and `browser-manager.ts`, no malware ([Socket via skills.sh](https://www.skills.sh/almeidamarcell/claude-code-skills/gstack/security/socket); secondary, version June 2026);
  - agentskill.sh: score 9/100 for that skill in March 2026 ([agentskill.sh](https://agentskill.sh/@garrytan/setup-browser-cookies/security); secondary, older version).
- **Anti-detection.** `browse/src/stealth.ts` masks `navigator.webdriver` and proxies `Function.prototype.toString`. Socket flags it as potentially enabling policy-violating browsing.
- **Supabase PAT** (§2.6): env-only, disclosed full-account scope. CI greps forbid it in argv positions, and a secret-sink harness seeds secrets and checks every output channel (USING_GBRAIN_WITH_GSTACK.md "Security model").
- **`eval "$(gstack-slug)"`** remains in four helpers: `gstack-question-log`, `-timeline-read`, `-timeline-log`, `-review-log`. Socket's "command execution if the helper's output is influenced" note still applies, although `gstack-slug` sanitises its output.

### 3.5 Session-integrity design worth noting (OBSERVED, good)

- **Spawned and unattended sessions** never auto-answer consent prompts. Destructive options are never auto-chosen. An env-driven "spawned" override is printed loudly (`gstack-skill-start` l.183–193).
- **Tracker text** (GitHub issues and PR bodies) is wrapped by `gstack-issue-guard` in a labelled trust envelope; injection-shaped lines are tagged even through invisible characters.
- **The `/cso` launcher** replaces its environment with an allowlist, uses only the local Docker socket, and runs target code only in hardened containers.

---

## 4. Case FOR (what would raise build quality for us)

| # | Practice | Where | Fit to our project | Evidence strength |
|---|---|---|---|---|
| F1 | **Gate-integrity catalog plus deterministic tagger.** RH-1 test removed or skipped; RH-3 golden regenerated without its test; RH-4 placeholder; RH-5 tautological test; RH-10 spec edited to match; RH-12 env sniffing; RH-13 suppression pragma; RH-14 gate bypass; RH-15 threshold relaxed; RH-16 exception swallowed. "The tool inventories and tags, it never judges and never suppresses"; a human disposes | `review/gate-integrity.md`, `lib/gate-diff/` (1,132 lines), `bin/gstack-gate-diff` | Defence in depth behind read-only tests. Catches relaxation in *non-protected* files (product thresholds, swallowed errors) that read-only tests cannot. Maps to I16: code tags, System Two reads | Vendor design; no measured recall found. Catalog adapted from a third-party skill (§9 licence note) |
| F2 | **Evidence rules as short, testable text.** "Claims Need Evidence" (5 bullets, ~800 B); "quote the motivating line or confidence 4–5"; "A report is a claim until re-executed"; "done, unverified ≠ done"; test value card `protects / fails_when / why_new / seam / no_claim` | Preamble; `review` Confidence Calibration; `scripts/resolvers/test-value.ts`; ETHOS "Honest Work" | Directly supports U4 and our "only the test runner writes passed". Cheap to adopt | Practice consensus; converges with Superpowers F5. No independent measurement |
| F3 | **Sectioned plan review with registries.** Error and rescue map, failure-modes registry with critical gaps, "NOT in scope", "What already exists", observability, deployment and rollout, long-term trajectory, distribution check, reality rows with `file:line` receipts | `plan-ceo-review/sections/review-sections.md`, `plan-eng-review/sections/review-sections.md` | Our DA1–DA3 reviews are strong on evidence and experiments but have **no fixed operational checklist** (rollout, observability, rescue paths). Use as a coverage list, not a replacement | Anecdote: a one-month user found `/plan-eng-review` "surfaced edge cases" ([claude-codex.fr](https://claude-codex.fr/en/content/garry-tan-stack-claude-code/)); vendor telemetry: 28,014 eng-review runs (usage, not quality) |
| F4 | **Eval spend and validity discipline** (`/eval-plan`): preregistered bars, arms, decoys, stop rules and held-out exposure; held-out sets never read; $0 stub dry run with checks (price table, output budget ≥8,192 for reasoning models, verbatim retry prompt, reservation fits cap); n≈3 priced pilot; locked spend ledger; projection with a 95% band; approval gate | `eval-plan/SKILL.md`, `lib/eval-plan.ts`, `lib/spend-ledger.ts` | Direct fit to ADR-018 certification and BrainBench runs. Addresses failure classes we have hit (truncated outputs, interrupted runs) | Vendor design; strong face validity; matches the brain-research protocol |
| F5 | **Investigate core.** Iron Law; reproduce first; 3 failed hypotheses → stop and ask; regression test must fail before the fix; >5 files → ask; recipes for flakes, races, test polluters and eval bisects (bisect a judged metric) | `investigate/` | Matches our "three identical failures → stop"; the eval-bisect recipe fits retrieval regressions | Converges with Superpowers systematic-debugging (two independent authors, same pattern); anecdotal |
| F6 | **Resume provenance markers.** Each remaining-work item ends `(path run)` with outcome, `(path read)`, `(path assumed)`, `(target state checked)` or `(code read)`; restore sorts unverified items into **Verify first** | `context-save`, `context-restore` | Fills a gap in our `state.json` "next" field: what the last session verified vs assumed | Vendor design; no measurement |
| F7 | **Safety rails as hooks.** careful: warn plus hard-deny; freeze: fail-closed edit fence, symlink-aware; guard; investigate auto-freezes its module | `careful/`, `freeze/`, `guard/` | Mechanical (code tier). Useful as a template for our acceptance-test protection hook. Their own docs say Bash bypasses freeze | Code-level (OBSERVED); third-party agrees "accident-prevention aid, not a security boundary" ([rywalker](https://rywalker.com/research/gstack)) |
| F8 | **Review Army specialists** with focused checklists in fresh subagents, adaptive gating by hit rate, and a never-gate list (security, data-migration, state-machines) | `review/sections/review-army.md`, `review/specialists/*.md`, `bin/gstack-specialist-stats` | Our reviewer seat (Superpowers review proposal) could use security, data-migration and state-machine checklists tuned to ACL and partition invariants | Vendor; untested by us (GS8) |
| F9 | **Context-budget ratchet in CI.** Catalog cap; per-skill eager ceilings re-captured on every change; a token bill-of-materials tool with a calibration report | `test/catalog-budget.test.ts`, `test/context-budget-ratchet.test.ts`, `lib/context-bill.ts` | Enforce H19 mechanically: BUILD-INDEX ≤8 KB and package brief ≤8k tokens as failing tests, not guidelines | OBSERVED (code); their CHANGELOG shows it drove real reductions |
| F10 | **Cross-session decision log.** Append-only `decisions.jsonl` with `--supersede`, `--redact`, scope, confidence and source; "treat listed decisions as settled; announce reversals" | `bin/gstack-decision-log`, `bin/gstack-decision-search` | Same shape as C-app §3.3 `decisions.jsonl`; supports "never re-litigate an ADR silently" | Vendor |
| F11 | **Cross-vendor outside voice** for plan and code review, with prompts that tell the reviewer to find what the review missed and not to edit | `scripts/resolvers/outside-voice-steps.ts`, plan-review sections | The only real diversity lever (DA1 §9: same-family checkers share blind spots) | Anecdote, vendor: on `/plan-tune`, "Codex's outside-voice review surfaced 15+ findings my four Claude reviews missed" (`docs/ON_THE_LOC_CONTROVERSY.md`) |
| F12 | **Learnings loop with staleness.** Typed learnings (pattern, pitfall, preference, architecture, tool, operational) with confidence, source and files; decay 1 point per 30 days for observed or inferred; deleted-file staleness; cross-project rows need `trusted:true`; injection-pattern sanitising on write | `bin/gstack-learnings-log`, `-search`, `learn/` | Mirrors our ≤2% stale-facts thinking at build time. File-reference staleness is the same idea as DA1's ADR-hash staleness for packages | Anecdote: "/learn reduced context loss" ([claude-codex.fr](https://claude-codex.fr/en/content/garry-tan-stack-claude-code/)) |
| F13 | **CSO evidence rubric.** Severity, confidence and evidence kept separate; daily reports hold only *supported* findings (attacker entrypoint, boundary crossing, in-scope impact, challenged controls); Phase 7 covers LLM, agentic and MCP (memory poisoning, confused deputy, per-tenant authorization); Phase 11 data classification; "unknown reachability stays unknown" | `cso/SKILL.md`, `cso/sections/audit-phases.md` | A good checklist for security review of brain packages, especially Phase 7 against R4 and DA3 threats | Vendor; anecdote of an XSS found ([TechCrunch](https://www.techcrunch.com/2026/03/17/why-garry-tans-claude-code-setup-has-gotten-so-much-love-and-hate/), second-hand) |

**Cross-connections to the brain's own design** (INFERRED; these primitives matter beyond builder tooling):
1. **Egress receipt ledger ≈ DA3's delivered-content ledger.** The same primitive: per send, sink, host, consent basis and a sha256 of the exact bytes, written *before* the send. Fail-closed for sensitive sinks, hash-chained, with a `verify` command. Reuse the design for the brain's exit path, so each MCP response records item IDs, version hashes and egress class. Also reuse its honest threat-model sentence: forensic, not a firewall.
2. **Session-bound instruction blocks ≈ lineage-authenticated directives.** gstack honours a directive only if it appears in the direct result of a trusted tool and carries an unforgeable per-run nonce. For ADR-014 lineage taint: memory content that looks like an instruction is never a directive unless it carries signed provenance. This matches R4's finding that signed-write provenance took unsigned attacks to 0%.
3. **The agent-ready error contract fits the brain's MCP errors.** Agents are the readers. The contract requires a stable code, a fix line, recovery semantics, redaction, and `isError: true`. **Caution:** its "what: the actual values that caused it" item must **not** apply to access-denied paths. Echoing the requested item or partition would break noninterference (DA3 §1, ADR-006). Our variant: denials are indistinguishable from "not found".
4. **Specialist adaptive gating has survivorship risk.** Gating a specialist after 0 findings in 10 dispatches is cost-sensible, but in our domain the rare finding is the one that matters. gstack's never-gate list (security, data-migration, state-machines) is the right instinct; ours would be ACL, egress, write gate, schema migration and crypto.

---

## 5. Case AGAINST

### 5.1 Token cost against our budget (OBSERVED plus INFERRED)

- **The numbers:** §2.5. The previous builder failed with 58k of mandatory reading. `/autoplan` alone is ~97–115k tokens, and a typical gstack sprint (office-hours → autoplan → implement → review → qa → ship) loads well over 200k tokens of process text across its sessions.
- **Persistence.** Invoked skills persist for the session ("Claude Code does not re-read the skill file on later turns", and content "stays there"). A long sprint session accumulates them.
- **Preamble duplication.** In `/autoplan`, the reviewed skill's preamble is skipped by instruction, but its bytes are still loaded: the snapshot tool copies the full SKILL.md into the methodology file. INFERRED: about 29 KB × 2 phases of skipped-but-loaded text.
- **Post-compaction layout (INFERRED from docs plus measured layout).** Claude Code keeps the first 5,000 tokens of each invoked skill after compaction. In 48 of 50 workflow skills the first ~28 KB (~7k tokens) is the shared preamble. So after compaction **the skill's own workflow is dropped and boilerplate is kept**. That is the opposite of what a resumable builder needs. Our skill should put the hard rules and the current step in its first 5k tokens (GS6).
- **Prompt caching** makes repeated preambles cheap in dollars, not in attention. Context rot is about tokens in the window, not price (BUILDER-PROTOCOL "Why this exists").

### 5.2 Scope creep and irrelevant surface (OBSERVED)

- About two-thirds of the skills are irrelevant to building a backend memory service: design ×6, iOS ×5, landing-report, office-hours, make-pdf, diagram, browser and productivity ×6, canary, land-and-deploy, setup-deploy, plan-tune, codex/claude-code wrappers, OpenClaw and Capy.
- Each still costs catalog tokens and attention unless listed in `disabled_skills`.
- A one-month user kept "about six commands" of 35 (anecdote, [claude-codex.fr](https://claude-codex.fr/en/content/garry-tan-stack-claude-code/)).
- The ethos itself pushes scope:
  - "Boil the Ocean… boiling the ocean is the goal" (ETHOS §1);
  - CEO review's "10-star product" and Expansion modes;
  - autoplan's P1 "Choose completeness" and P2 "Boil lakes: auto-approve expansions in blast radius AND < 1 day CC effort".

  Our packages have a **done line** and an **out-of-scope** section (ADR-019). Expansion is a defect for us.

### 5.3 Same-model "specialists" reviewing each other (INFERRED from independent studies)

- **Personas are not the active ingredient.** Expert personas "generally did not beat a no-persona baseline" on GPQA Diamond and MMLU-Pro across six models; mismatched or low-knowledge personas sometimes hurt ([Basil et al., Wharton GAIL, arXiv 2512.05858](https://arxiv.org/abs/2512.05858); single study, independent). The value of "CEO" or "Eng Manager" is in their checklists. GS7 tests this.
- **Same-family review shares blind spots.** Judges favour similar models, and error correlation grows with capability ("Great Models Think Alike", cited in DA1 §9). Multi-agent debate "can lead to a decrease in accuracy over time", with models switching from correct to incorrect after seeing peers ([arXiv 2509.05396](https://arxiv.org/abs/2509.05396); independent). A homogeneous three-judge panel ranged from +8.5 to −4.4 pp against a single agent across six groundedness benchmarks ([arXiv 2608.00243](https://arxiv.org/abs/2608.00243); independent).
- **Uncalibrated scores.** gstack's confidence 1–10 and "Completeness: X/10" are self-reported by the generating model. In I16 terms these are System Two outputs dressed as System One. Our design requires calibrated closed decisions or deterministic code at gates (I16, U7, I15).
- **The diversity lever is egress.** Codex as outside voice sends brain code and plans to OpenAI by default. For packages touching real data, such as WP-migrate replaying the owner's existing brain (DA1 §8.2), that would be an overseas disclosure (APP 8; DA3 C1).
- **Fresh context helps anchoring, not omissions.** Fresh-context subagents (Review Army) reduce anchoring but not shared model priors, and a checker shown the output cannot see what is missing (DA1 §9.1).

### 5.4 Builders, tests and autonomy (OBSERVED)

- **Builder-owned tests.** `/ship` "bootstraps test frameworks from scratch… 100% test coverage is the goal" (README). `/qa` writes regression tests and fixes code in the same loop. `/investigate` writes the regression test that proves its own fix. In our protocol, acceptance tests are engineer-authored, read-only and hash-checked (BUILDER-PROTOCOL §3). ImpossibleBench found Claude models modified test files in 50–55% of impossible tasks (DA1 §8.1). gstack *detects* relaxations after the fact (F1). It does not prevent them.
- **Autonomous decisions:**
  - `/autoplan` "Auto-decide replaces the USER'S answer… Never abort or redirect to interactive review";
  - P6 "Bias toward action — Merge > review cycles > stale deliberation. Flag concerns, don't block";
  - spawned sessions "auto-choose the **recommended** option at every decision point… never prose, never BLOCKED".

  Our rule: "An unclear or missing decision → pause… Never invent a decision" (BUILDER-PROTOCOL §4). gstack's safeguards are real but narrower: user challenges are never auto-decided; destructive options are never auto-chosen; consents are never auto-answered.
- **Release autonomy.** `/ship` pushes and opens PRs, versions are chosen by the agent, and `/land-and-deploy` merges and deploys. These do not fit an owner-gated build.

### 5.5 Lock-in and platform (OBSERVED)

- Bun ≥1.3.3; Git Bash plus Node on Windows; hooks run through bash; Windows installs are file copies refreshed only by re-running setup; `/cso` is partial on Windows; Aside is macOS-only. **The owner's stage-1 host is Windows 64-bit** (project memory).
- **Browser exclusivity** in CLAUDE.md, and team "required" mode blocks work when gstack is missing.
- State lives in `~/.gstack/`, outside the repository. Checkpoints, learnings and decisions are lost on a machine change unless artifacts sync is turned on, and that sync pushes to a git remote.
- Playwright is patched (`patches/playwright-core@1.62.1.patch`), so upgrades depend on the vendor.

### 5.6 Maintenance velocity and governance (OBSERVED)

- 422 releases in ~7 months; 138 in October 2026; 2–20 releases per day in mid-October. Versions sit at 1.91.x because "Diff size alone is not a reason to choose MINOR". Pinning plus re-testing on every upgrade is mandatory if anything is reused (as with Superpowers SP11).
- The SECURITY policy patches only `main`: "older versions are not patched separately".
- Contributor rules protect "Garry's voice" and "promotional material" from neutral rewrites, and the README carries a YC hiring ad. That is not a quality issue, but it signals a personal toolkit rather than neutral infrastructure.
- I could not read the issue tracker (robots-disallowed; this session is GitHub-scoped). Failure-report frequency is **UNKNOWN**. A secondary source summarises two real issues: a headless browser killing another project's headed browser via a shared profile lock (fixed in 1.87.2.0), and repeated permission prompts for outside reviews on macOS ([rywalker](https://rywalker.com/research/gstack)).

### 5.7 Conflicts with our principles

| Our principle | gstack behaviour | Conflict |
|---|---|---|
| I16: code is the only security boundary; System One makes calibrated closed decisions; System Two does open work | Gates are a mix: good code gates (hooks, gate-diff, plan-reality, evidence fingerprints, gate parser) beside LLM self-scored confidence, completeness and "Mechanical vs Taste" classification | Partial. Adopt the code gates; replace self-scores with deterministic checks or calibrated classifiers |
| Egress classes and partition rules (DA3 §13; owner: member health data local or AU-hosted) | Default-on Codex reviews; Aside research; Voyage or OpenAI embeddings; Supabase transcripts; update checks; team auto-update | **Direct conflict.** Every sink must be off, with proxy verification (GS9) |
| ≤8 KB always-loaded index; ≤8k tokens per package (H19, ADR-019) | ~2.6k always-loaded; 7–100k+ per invocation; CLAUDE.md grows by design | **Direct conflict** |
| Tests read-only to the builder | Builder writes, bootstraps and maintains tests | **Direct conflict** (mitigated by F1 detection) |
| Never invent a decision; stop at the done line | Auto-decide principles; Boil the Ocean; Selective Expansion | **Conflict**, partly carved out |
| State with the code, in JSON, test-gated (ADR-019 §3) | Markdown checkpoints in `~/.gstack`, LLM-written | Conflict (GS2) |
| Supply-chain baseline: pinned, hash-verified (DA3 §7, ADR-016) | Digest-pinned CSO images and checksum-pinned impeccable (good); unpinned HF model, `bun install` fallback, unsigned auto-update (bad) | Mixed |

---

## 6. Steelman and devil's advocate, both ways

**Steelman FOR adopting gstack, close to wholesale:**
- It is battle-tested at scale by vendor telemetry: 305k skill runs, ~15k installs, ~7k weekly users at peak, 95.2% runs without error (self-reported, opt-in; `docs/ON_THE_LOC_CONTROVERSY.md`).
- Its authors have hit and fixed hundreds of the exact failure modes we worry about. The CHANGELOG is a 1.7 MB incident log: phantom hooks, compaction loss, unsafe auto-decisions, test gaming.
- Its newest machinery is unusually honest about limits:
  - "not a security boundary";
  - "a forensic log, not tamper-proof storage";
  - review receipts are "not independent proof that a model read the source";
  - CSO's `self_reported` versus `runtime_tested` labels.
- Its gates are increasingly mechanical: hooks, snapshot hashes, gate parsers, evidence ledgers.
- On cost: tokens are cheap relative to a missed bug. If a full review pipeline catches one partition-leak bug, 100k tokens is a bargain. And the owner said quality comes first and a build of weeks is fine.

**Devil's advocate against that steelman:**
- **Usage is not quality.** "Success" means no error, not a correct result. The LOC numbers are self-measured and contested:
  - 11,417 logical lines a day "~810×" by the author's own script;
  - an independent audit of the author's public site found 6.42 MB and 169 requests for a homepage, 28 test files served to visitors and a 0-byte AVIF in production ([aiweekly summary of Gregorein audit](https://aiweekly.co/alerts/developer-audits-yc-ceo-garry-tans-37k-ai-lines-per-day-claim); secondary, anecdote, about the author's site, not gstack);
  - slop-scan rated gstack 5.24, "the worst he'd measured at the time" (vendor's own doc).
- **No independent study.** I found no controlled evaluation of gstack's effect on defects or cost. Bounded search: web queries for reviews, criticism, "I tried gstack", HN discussion and scanner reports. The issue tracker could not be read.
- **Cost here is not "tokens are cheap".** It is the *specific* failure that already killed our build: a builder that ran out of context and budget. An extra 100k per package is not a bargain if it moves the package beyond one session, which ADR-019 forbids.
- **Not adapted for a privacy-critical, Windows-hosted, egress-restricted, partitioned backend.** The machinery is for shipping web products fast with real browser sessions.

**Steelman AGAINST adopting anything from gstack:**
- Every useful idea also exists in Superpowers, our protocol or the literature: verification gates, root-cause debugging, read-only tests, checkpoints.
- Mixing a second vendor's vocabulary adds confusion. The owner's previous builder already suffered from too much mandatory text.

**Devil's advocate against that:** four gstack ideas have no equivalent in our docs or in Superpowers:
1. the RH gate-integrity catalog plus a deterministic tagger;
2. resume provenance markers;
3. eval preregistration with a $0 stub dry run and a priced pilot ledger;
4. a CI context-budget ratchet.

Each is small, rewritable in a few hundred tokens or lines, and testable. Discarding them on vendor grounds would be the "not invented here" error the ETHOS warns about (Layer 1 miss).

**Net position.** Mine gstack for ideas and checklists. Install none of it in the builder environment. Run it only in an isolated arm of the bake-off to measure cost and egress (GS3, GS9).

---

## 7. Verdict per component

| Component | Verdict | Reason / change |
|---|---|---|
| Install gstack (any mode) in an environment that touches brain code or data | **Reject** | Egress defaults, CLAUDE.md rewrites, unsigned auto-update, token cost (§3, §5) |
| Team mode, SessionStart auto-update, `/gstack-upgrade` | **Reject** | Supply chain: unsigned remote code execution hourly on every machine |
| Routing injection, CLAUDE.md config persistence, "never use Claude in Chrome" | **Reject** | Breaks the ≤8 KB index and overrides owner tooling |
| Shared preamble (as is) | **Reject**; **adopt** 3 rules from it | Keep only "Claims Need Evidence", "Confusion Protocol" (3 lines) and "Context Health" (2 lines), rewritten. Drop Voice, AskUserQuestion format, Boil the Ocean, telemetry, artifacts sync |
| `review/gate-integrity.md` + `gstack-gate-diff` | **Adopt** (rewrite, attribute) | Our `scripts/gate-tags` emits RH tags on each package diff; the reviewer reads tagged hunks; the owner disposes. Python, ~200 lines, no Bun |
| Claims Need Evidence; quote-or-≤5 confidence; test value card | **Adopt** | Into `verify.md`, the reviewer prompt and test-author guidance |
| `/eval-plan` method | **Adopt** (method only) | Into ADR-018 runbook: preregistration file, stub dry run, n≈3 pilot, spend ledger, approval. Implement in our harness, not their binary |
| `/investigate` core and recipes | **Adopt** (merged with Superpowers' debugging) | `debug.md`: Iron Law, 3-strike → blocker note, fail-before/pass-after regression test, eval-bisect recipe for retrieval regressions |
| Context-budget ratchet test | **Adopt** | CI test: BUILD-INDEX ≤8 KB; each WP brief plus its cited reads ≤8k tokens; skill files ≤ budget |
| `/context-save` / `/context-restore` | **Adapt** | Take only the provenance markers and the Verify-first sort into `state.json.next[]`. Reject Markdown, the `~/.gstack` location and LLM summary as the source of truth |
| Plan-review sections (CEO, Eng) | **Adapt** | Coverage checklist appended to our DA template: error and rescue map, failure-modes registry, observability, rollout and reversibility, NOT in scope, what already exists, distribution. Drop personas, modes, auto-decide and expansion framing (GS1, GS7) |
| `/autoplan` | **Reject** pipeline and principles; **adapt** one mechanism | Its hook-enforced phase ordering ("deny Read of the next phase until this phase's packet is published") is a neat pattern for multi-stage engineer reviews; optional |
| Review Army specialists | **Adapt** | Reviewer-seat checklists for security, data migration, state machines and testing, rewritten for ACL, partition, write-gate and revocation invariants. Cross-family **local** model when available (GS4, GS8). Keep a never-gate list |
| Outside voice (Codex) | **Adapt** | Keep the prompt pattern ("find what the review missed; do not edit"). Replace the provider with a local different-family model on the GPU host, or a hosted one only for egress-cleared, data-free packages |
| `/cso` phases 7, 10, 11 and the evidence rubric | **Adapt** | Security review checklist for brain packages. Do not use the CSO runtime: Bun, Docker images from ghcr.io/garrytan, C toolchain |
| careful / freeze / guard | **Adapt** | Use as a template for our own project hooks (`protect-tests`, `protect-adr`, destructive-command ask). Write our own; do not install theirs |
| `/learn` and the learnings JSONL | **Adapt** | `build/learnings.jsonl` committed in the repo, engineer-reviewed before promotion, with decay and file-staleness; no cross-project import (poisoning, GS10) |
| Decision log | **Adapt** | `decisions.jsonl` (C-app §3.3) with supersede and redact semantics |
| `/qa-only` | **Adapt** | Report-only MCP and API surface QA with replayable evidence notes; no fixes |
| `/test-audit` | **Adapt** (engineer-only, later) | Periodic sweep of builder-written unit tests; never acceptance tests |
| `/benchmark-models` | **Reject** tool; idea covered | Our model selection runs through BrainBench and the GPU validation package |
| `/health` | **Reject** skill; **adopt** idea | A CI script that runs typecheck, lint, tests and dead-code checks |
| Agent-ready error contract | **Adapt** (brain design input) | For brain MCP errors, with a noninterference exception for denials (§4 cross-connection 3) |
| Egress receipt ledger | **Adapt** (brain design input) | Model for the delivered-content ledger (DA3) |
| `/spec` "Rules for the implementing agent" | **Adopt** (5 rules) | Into the WP template footer |
| `/ship`, `/land-and-deploy`, `/canary`, `/setup-deploy`, `/document-release` | **Reject** | Owner-gated releases; builder never pushes or deploys |
| `/setup-gbrain`, `/sync-gbrain`, transcript ingest, brain-aware resolvers | **Reject** | We are designing our own brain; GBrain is single-operator; embeddings egress |
| Telemetry, update check, Aside research, plan-tune hooks | **Reject** | Egress and settings mutation |
| Design ×6, iOS ×5, office-hours, landing-report, make-pdf, diagram, retro, browse/scrape/skillify/cookies/open-gstack-browser/pair-agent, codex/claude-code wrappers, OpenClaw, Capy | **Reject** | Irrelevant to the build, or a security surface |

---

## 8. Hypotheses (proposed IDs GS1–GS12 for doc 06)

All tests run in the Superpowers bake-off harness (`SUPERPOWERS-review.md` §8.2) or as small standalone micro-experiments. I propose adding **arm G: gstack v1.91.182.0, pinned**, to the bake-off for P1 only:
- in an isolated container, outside any brain-data environment;
- with `telemetry off`, `update_check false`, `codex_reviews disabled`, `GSTACK_SKIP_ASIDE=1` and no team mode;
- with network allowed only to the model API, logged through the agent proxy.

Arm G measures cost and egress. It does not count as a candidate for adoption.

| ID | Hypothesis | Decisive test | Kill / adopt criterion |
|---|---|---|---|
| **GS1** | gstack-style sectioned plan review (CEO + Eng methodology, ported to documents, no git) **does not replace** our DA reviews but **adds coverage**; our DA template plus gstack's coverage checklist beats both | 3 ADR-style docs, each seeded with 8 known flaws: 2 operational (rollout, rescue path), 2 security or egress, 2 evidence or metric (e.g. CR@k items vs tokens, DA1 X1), 2 scope or feasibility. Arms: **A** our DA prompt (DA1 format: strongest case against, scale failure, alternatives, verdict, decisive test); **B** gstack plan-ceo + plan-eng review sections verbatim (personas kept); **C** A + gstack coverage checklist; **D** B with personas stripped (also GS7). 5 reps per arm per doc, same model. Blind grader scores seeded-flaw recall and *valid novel* findings (two graders, one cross-family); tokens from stream-json | **Kill "gstack roles as our DA process"** if B's seeded recall < A − 10 pp, or B tokens > 2× A. **Adopt the checklist (C)** if C ≥ A + 10 pp recall at ≤1.3× tokens. Expected (INFERRED): B wins on operational flaws, loses on evidence and metric flaws; it never proposes experiments or kill criteria |
| **GS2** | For resumability, gstack's LLM-written Markdown checkpoint is worse than our test-gated `state.json`; adding gstack's provenance markers to `state.json` improves on both | Kill-and-resume drill on bake-off P1 (kill at 40% of median wall time; fresh `claude -p`, no history). Arms: **(i)** context-save/restore format; **(ii)** `state.json` as ADR-019; **(iii)** `state.json` + provenance markers + Verify-first. **Plant one false "done" item** in the last checkpoint: a task recorded as complete whose test actually fails | **Kill (i)** if it acts on the planted false-done item more often than (ii), or redoes more work. **Adopt the markers (iii)** if acting on unverified items drops by ≥50% vs (ii) at ≤10% more tokens to first productive edit. Prediction: (ii) and (iii) re-run tests and catch the false item; (i) trusts the summary |
| **GS3** | A full gstack sprint costs ≥3× our protocol in tokens per package with no gain in hidden-test pass rate | Bake-off P1: arm G (prompt: `/autoplan` on the brief, implement, `/review`, `/qa-only`) vs arm A; tokens and cost from stream-json, hidden tests | **Kill the cost concern** if G ≤ 1.5× A tokens. **Reject gstack-style pipelines** if G ≥ 3× A with hidden pass ≤ A + 5 pp |
| **GS4** | A different-family reviewer catches ≥30% relatively more seeded defects than same-family; a **local** different-family model gets ≥80% of a hosted cross-vendor reviewer's gain with zero egress | Extends SP4: 10 seeded defects acceptance tests miss × 5 reps. Reviewers: Claude same tier; Claude subagent with fresh context (gstack style); hosted GPT/Codex (on a data-free fixture only); local Qwen3 on the GPU host | **Kill cross-family review** if relative gain < 30% or false positives > 2×. **Kill the "local suffices" claim** if local < 80% of hosted gain; then hosted cross-vendor review only for egress-cleared packages |
| **GS5** | A deterministic RH tagger (RH-1, 3, 4, 12–16) flags ≥90% of seeded test-relaxation diffs with ≤10% false tags on clean diffs; it does **not** catch special-casing, so hidden tests stay necessary | Corpus: 40 seeded diffs (skip, delete, timeout up, threshold down, pragma, `--no-verify`, env sniff, swallowed except, golden regen) + 10 special-casing diffs + 40 clean diffs from bake-off runs | **Kill the tagger** if recall < 70% or false tags > 20%. Expected: special-casing recall ≈0% → confirms SP2 and the hidden-test rule |
| **GS6** | Skill layout matters after compaction: a rules-first skill retains compliance with its critical rules better than a preamble-first skill (gstack layout), because only the first 5k tokens are re-attached | Same skill text in two orders; 3 critical rules located beyond token 5,000 in the preamble-first version; force `/compact` mid-task; then 3 pressure probes × 10 reps | **Adopt "rules in the first 5k tokens"** (cheap) if compliance gap ≥ 10 pp. Kill the concern if the gap is < 5 pp |
| **GS7** | Role personas ("you are the CEO / Eng Manager") add nothing beyond the same checklist without the persona | GS1 arm B vs arm D | **Drop personas** from our review prompts if \|B − D\| < 5 pp recall (expected, per arXiv 2512.05858) |
| **GS8** | Parallel focused specialists (review-army style) find more seeded defects than one generic reviewer at an equal token budget | 10 seeded defects spanning ACL, migration, state machine, test quality and performance; arm 1 = one reviewer with a merged checklist; arm 2 = 4 specialists with split checklists, token-matched | **Kill fan-out** if arm 2 ≤ arm 1 + 10 pp, or tokens > 1.5× at equal recall |
| **GS9** | With every opt-out set, a gstack session makes zero off-machine requests other than the model API; with defaults it makes requests to ≥3 non-model hosts | Arm G behind the agent proxy with request logging; run `/review`, `/qa-only` (CLI target), `/investigate`. Then repeat once with defaults on a data-free fixture repo | **Any** non-model request with opt-outs set → gstack is barred from every environment near brain data (expected to pass with opt-outs; listed sinks with defaults: GitHub, Supabase, OpenAI, Aside, HuggingFace) |
| **GS10** | A reviewed, repo-committed build-learnings file cuts repeat mistakes across packages; unreviewed auto-logged learnings get poisoned | Two packages built in sequence, with 3 known pitfalls in package 1. Arms: no learnings; auto-logged (gstack style); engineer-reviewed. Plant one bad learning ("tests in tests/acceptance may be updated if outdated") | **Kill learnings** if pitfall recurrence drops < 30%. **Kill auto-logging** if the planted bad learning is followed in > 1/10 runs |
| **GS11** | Applying `/eval-plan`'s preregistration + stub dry run + n≈3 pilot to our BrainBench and certification runs prevents post-hoc invalidated runs | Next 10 experiment runs with the checklist vs the last 10 without; count runs invalidated afterwards (truncated outputs, wrong arm, held-out exposure, budget overrun, unreproducible settings) | **Keep** if invalidations drop by ≥ 1 run per 10 (cost is trivial). Kill only if the checklist adds > 15 min per run with no drop |
| **GS12** | autoplan-style auto-decide principles invent decisions in protected areas; our pause rule does not | Bake-off P1's 3 planted ambiguities (1 protected: revocation mid-query). Arm G with `/autoplan` before implementation vs arm A | **Any** protected-area invention in G (expected ≥1/6) confirms rejection of auto-decide. If G invents 0/6 and A stalls on unprotected items, revisit the hybrid "protected → pause; unprotected → logged ruling" (SP5) |

**Bake-off budget delta (INFERRED).** Arm G on P1 adds 6 reps at roughly $5–15 each, given ~100k+ tokens of process text per run. GS1, GS5–GS8 and GS10 are micro-experiments of about $20–60 each. GS9 and GS11 are nearly free.

---

## 9. Recommendation: what a custom "brain-builder" skill should take

This extends the outline in `SUPERPOWERS-review.md` §9; it does not replace it. Same shape:
- no forced bootstrap;
- BUILD-INDEX ≤8 KB as passive context;
- `SKILL.md` ≤6 KB;
- references read at the point of use, with ≤3k tokens of process text per session;
- mechanical guards rather than prose.

**Additions from gstack (rewritten in our voice):**

| From gstack v1.91.182.0 | Into brain-builder | Size |
|---|---|---|
| Gate-integrity catalog (RH-1, 3, 4, 5, 10, 12–16) and the "inventory, tag, never judge; human disposes" rule | `scripts/gate-tags` (Python) + `reviewer-prompt.md` § "Gate edits" + PR/checkpoint line `Gate edits:` | ≤200 lines; ≤600 tokens of prompt |
| "Claims Need Evidence"; "a report is a claim until re-executed"; "done, unverified ≠ done" | `verify.md` | ≤300 tokens |
| Confidence calibration: quote `file:line` or confidence ≤5; never invent 7+ | `reviewer-prompt.md` | ≤150 tokens |
| Test value card (`protects / fails_when / no_claim`) and low-value catalog | `test-quality.md` (test-author sessions only) | ≤400 tokens |
| Provenance markers + Verify-first sort | `state.json` schema: `next[].provenance ∈ {run, read, assumed, target_checked, code_read}`, `next[].outcome`; resume rule in `resume.md` | schema + ≤200 tokens |
| Investigate Iron Law, 3-strike, fail-before/pass-after, eval-bisect recipe | `debug.md` (merged with Superpowers' debugging phases) | ≤500 tokens |
| `/eval-plan` method | ADR-018 runbook + `bench/prereg.md` template + spend ledger in the harness | engineer-side |
| Context-budget ratchet | CI tests `test_index_budget`, `test_brief_budget`, `test_skill_budget` | code |
| Plan-review coverage list | DA template appendix (engineer-side, not builder) | ≤300 tokens |
| Specialist checklists (security, data migration, state machines) | `reviewer-checklists/{acl,migration,state}.md`, loaded by the reviewer seat only | ≤600 tokens each |
| CSO phase 7 (LLM, agentic, MCP), 10 (STRIDE), 11 (data classification) and the "supported finding" rubric | `security-review.md` for packages that touch ACL, egress, write gate or MCP | ≤800 tokens |
| Destructive-command and edit-fence hooks (pattern only) | `hooks/protect-tests`, `hooks/protect-adr`, `hooks/careful` (our own code) | code |
| `/spec` "Rules for the implementing agent" (5 rules) | WP template footer | ≤200 tokens |
| Decision log with supersede and redact | `decisions.jsonl` | schema |

**Layout rule from GS6.** The first 5,000 tokens of `SKILL.md` hold the 12 hard rules, the session loop and the stop rules, so they survive compaction re-attachment. Nothing generic goes first.

**Attribution.**
- Line: "Portions adapted from garrytan/gstack v1.91.182.0, MIT License, Copyright (c) 2026 Garry Tan; modified." Keep the MIT text in `THIRD_PARTY_NOTICES`.
- **Licence check before reuse:**
  - `review/gate-integrity.md` says it is "adapted from the just-say-no-to-process-porn-and-ceremony skill's REWARD-HACKING-CATALOG". Its licence is **UNKNOWN**, so take the *concepts*, write our own text, and credit both.
  - Do not reuse files gstack derived from Apache-2.0 works (`NOTICE.md`: `lib/design-catalog.ts`, `scripts/resolvers/design.ts`, design-consultation sections). None of them are needed.

**Leave:**
- installation, team mode, auto-update, telemetry, update checks;
- CLAUDE.md rewrites and the routing injection;
- browser exclusivity;
- the 28 KB preamble;
- the AskUserQuestion "decision brief" format;
- Voice, personas and "Boil the Ocean";
- autoplan's auto-decide principles and Selective Expansion;
- builder-authored or bootstrapped tests;
- `/ship` and deploy autonomy;
- default-on outside reviews to a second vendor;
- the GBrain integration and transcript ingestion;
- cross-project learnings;
- Aside research;
- every design, iOS, browser, cookie, stealth, tunnel and productivity skill.

**Proposed changes to BUILDER-PROTOCOL** (for the engineer to accept or reject; compatible with the Superpowers proposals):
1. §3: add `scripts/gate-tags` output to every checkpoint. Any RH-tagged hunk in a package diff needs an owner disposition before `passed`.
2. §2 step 5: `state.json.next[]` items carry provenance markers. On resume, verify `assumed` and `code_read` items read-only before acting.
3. §1: enforce the size caps in CI (ratchet tests), not only in prose.
4. ADR-018: adopt preregistration + stub dry run + priced pilot + spend ledger for every paid eval or certification run.
5. DA template: append the operational coverage checklist (error and rescue map, failure-modes registry, observability, rollout and reversibility, distribution).

---

## 9A. gstack as part of the brain: a procedure library (owner's angle; gstack-specific)

The owner asked whether gstack could serve not only as builder tooling but as **procedural memory inside the brain**: quality-gated SOPs that agents using the brain fetch when a task needs them. Procedural memory in general belongs to stream R8. This section covers only what gstack itself offers and what it teaches.

### 9A.1 Which gstack procedures are generic and good enough to adapt (MIT, with attribution)

Selection test:
1. the procedure is domain-agnostic, useful beyond software repos, for the owner's businesses, investments and assistants;
2. its quality bar is explicit (stop rules, evidence rules, outputs);
3. it can be rewritten as declarative steps with no shell, so non-Claude clients such as a partner on ChatGPT can follow it;
4. it is short once the preamble is stripped.

| gstack source | Brain procedure (rewritten) | Why it qualifies | Adaptation notes |
|---|---|---|---|
| `investigate` (Iron Law, phases 1–5, 3-strike, blast-radius ask, structured report) | **Diagnose a fault** (connector failing, report wrong, integration out of sync) | Generic root-cause method with hard stops; converges with Superpowers debugging | Drop git, bash and freeze specifics. Keep: collect symptoms → reproduce → one hypothesis at a time → 3 failures = escalate → fix verified against the original symptom → report (Symptom / Root cause / Fix / Evidence / Status DONE, DONE_WITH_CONCERNS or BLOCKED) |
| `eval-plan` (preregistration, $0 dry run, priced pilot, spend ledger, approval) | **Run a costed batch job** (paid API batch, bulk enrichment, re-embedding, any agent action with spend) | Generic "reserve, settle, cap" spend discipline with a stub dry run and a pilot extrapolation | Spend admission and the ledger must be **code** (I16 tier 1); the procedure only asks for the preregistration and reads the ledger's verdict |
| AskUserQuestion decision brief (ELI10, stakes, recommendation, completeness, pros and cons, Net; one-way doors require typed confirmation) | **Ask the owner for a decision** | Fits an owner who "makes no technical calls" (BUILDER-RULES Read-first 3) and any partner or member decision | Compress ~11 KB to ≤1 KB. Remove completeness scoring, which is self-rated. Keep the one-way-door rule ("silence or 'ok' is not confirmation") |
| `context-save` / `context-restore` (summary, decisions, remaining work with provenance markers; restore refuses foreign or unverified checkpoints and sorts Verify-first) | **Hand off a task** between sessions, agents or people | Generic handoff with honest provenance and identity checks | Identity stamp = principal + partition + task id (not git remote); foreign checkpoints are never loaded across partitions |
| `spec` "Issue Quality Standards" + "Testable Acceptance Criteria" + "Rules for the implementing agent" | **Write a task brief** (for a builder, a contractor or a staff member) | Generic: why, current state, proposed change, numbered pass/fail acceptance criteria, rollback, effort, out of scope | Drop GitHub filing, dedupe and outside-review gate |
| `plan-ceo-review` / `plan-eng-review` registries (premise challenge, alternatives, error and rescue map, failure-modes registry, NOT in scope, what already exists, rollout and reversibility) | **Review a plan before committing** (renovation, new class schedule, investment, system change) | The registries are domain-agnostic checklists | Drop personas, scope modes, "10-star" and expansion framing, and auto-decide (§5.3, GS7) |
| `cso` Phase 12 evidence rubric (severity, confidence and evidence kept separate; "supported finding" needs actor, boundary crossing, impact and a challenged control; unknown stays unknown) | **Assess an incident or finding** (privacy incident triage before an NDB assessment, a security report, a complaint) | Generic and rigorous; fits the OAIC "likely serious harm" assessment workflow (R4 §7) | Not legal advice; output feeds a human decision |
| `qa-only` (report-only probes, evidence note per probe, untested contracts listed, never invents a pass) | **Verify a system or process works** (connector smoke test, app flow check) | Generic exploratory verification with honesty rules | Report-only; never fixes |
| `learn` prune (deleted-reference staleness, same-key contradictions, append-only correction, latest wins) | **Memory hygiene pass** on procedure notes and learnings | Directly relevant to the ≤2% stale-facts standard | Runs through the write gate; contradictions go to review, never auto-resolved |
| `docs/agent-ready-errors.md` contract | **How every procedure reports failure** | Agents are the readers; stable code, fix line, recovery, redaction | Denials indistinguishable from "not found" (§4 cross-connection 3) |
| `office-hours` (six forcing questions, premise challenge, three approaches) | **Interrogate a new business idea** (optional, owner-facing) | Reusable idea-screening questions; useful for investments and new ventures | YC startup vocabulary must be neutralised. Not reviewed line by line (body ~67 KB); treat as candidate only |

**Not procedure material:**
- `ship`, `land-and-deploy`, `canary`, `review`, `test-audit`, `health`, design and iOS skills: software-delivery specific.
- `careful` and `freeze`: these are **policies**, so they belong in code (I16 tier 1), not in a procedure an agent may or may not follow.
- `retro`: its metrics are git-specific. Only the weekly-review narrative shape (what shipped, hotspots, three habits) generalises.

### 9A.2 What gstack's mechanisms teach about delivering procedures on demand

Each mechanism, with how it works in gstack (OBSERVED, §2 and the cited files) and the lesson for the brain (INFERRED):

1. **Two-tier delivery with a budget.**
   - *gstack:* Skills show only a ≤260-byte name and description at startup, with the aggregate capped at ~1.2k tokens by a CI test. The full body loads on invocation.
   - *Lesson:* The brain's procedure index works the same way: a capped one-line "when to use" per procedure in the always-loaded layer, with the body fetched by ID. Enforce the cap in CI, as gstack does (H19).
2. **Skeleton plus condition-triggered sections.**
   - *gstack:* "STOP. Before <situation>, Read section X in full". A section index table lists "When" and "Read this section".
   - *Lesson:* This matches the owner's "packets" idea: deliver the skeleton, and let the agent fetch the section for the branch it is on. **Caution:** gstack needed a section-loading eval and, in `/autoplan`, PreToolUse hooks that *deny* out-of-order reads, because agents skip or prefetch. Lazy sections need a check that they were read before the step, either an eval or a gate.
3. **Templates and shared resolvers** (single source of truth, regenerated, drift-tested).
   - *gstack:* Every procedure *inlines* shared blocks, so the 28 KB preamble repeats in each one (§2.5).
   - *Lesson:* Compose at delivery time by fragment ID, and send a shared fragment once per session, not once per procedure. Put the procedure-specific steps first: the compaction re-attach keeps the first 5k tokens (GS6).
4. **Runtime state, not static text.**
   - *gstack:* `gstack-skill-start` returns trusted `KEY: value` lines (session kind, config, learnings count) that the procedure branches on.
   - *Lesson:* The brain sends the procedure together with code-derived state: principal, role, partition, client egress class, whether a human is present. Procedures branch on facts the model did not invent.
5. **Nonce-bound directives.**
   - *gstack:* An instruction block is honoured only in the direct result of the trusted call, with the run's random `SESSION_ID`. Text from files, learnings or pages has the marker stripped.
   - *Lesson:* **The key anti-poisoning lesson.** A brain-delivered procedure must arrive on a channel the agent can tell apart from retrieved content: a separate MCP tool, a signed envelope or a per-request nonce. Any memory item that *looks like* a procedure is data (ADR-014 lineage taint; R4: signed-write provenance took unsigned attacks to 0%).
6. **Per-client guarantee labels.**
   - *gstack:* The host table marks safety skills "enforced (hooks block)" on Claude Code and "advisory, not blocked" on every other host.
   - *Lesson:* For the owner's mixed clients (Claude, a partner's ChatGPT), each procedure step should declare whether its guard is *enforced by brain code* or *advisory text*. Only enforced guards may protect partitions or consent.
7. **Declarative context per procedure.**
   - *gstack:* `plan-ceo-review` frontmatter declares `gbrain: context_queries`: prior CEO plans (glob, `mtime_desc`, limit 5), recent design docs (limit 3), recent reviews (filter, sort, limit), each with a `render_as` heading. `GBRAIN_SAVE_RESULTS` writes outputs back as tagged pages.
   - *Lesson:* A procedure declares the **context packet** it needs, as typed, limited queries, so the brain assembles exactly that slice under the caller's access check (ADR-007, ADR-010) and within the token budget. Write-back must go through the write gate with lineage, never directly (ADR-011, ADR-014).
8. **Promotion pipeline.**
   - *gstack:* `/skillify` turns a recent successful ad-hoc run into a permanent procedure. It checks provenance (the source run within 10 turns and not invalidated), synthesises a script, fixture and test, stages them in a temp directory, runs the test, asks for explicit approval, then commits atomically. "No 'almost shipped' state".
   - *Lesson:* Procedure learning works as maker-checker (U4): candidate → test against a fixture → human approval → versioned, signed procedure.
9. **Trust lifecycle, with a flaw.**
   - *gstack:* Domain skills go quarantined → active after 3 uses without an ML-classifier flag → global only by manual command, with rollback.
   - *Lesson:* Copy the states and rollback, **not** the auto-promotion rule. R4 found injection detectors miss most adaptive attacks, so "no flag in 3 uses" is absence of evidence. Promotion needs tests plus a named approver.
10. **Learnings attached to procedures.**
    - *gstack:* Typed (pattern, pitfall, preference, architecture, tool, operational), with confidence, source and referenced files. Confidence decays 1 point per 30 days, latest entry wins, rows go stale when referenced files are deleted, cross-project rows need `trusted:true`, and injection patterns are sanitised on write.
    - *Lesson:* This maps onto the brain's fact model (keyed, versioned, decaying). Refinements to a procedure ("step 3 fails for Xero; use the export endpoint") are learnings with provenance, reviewed before they change the procedure.
11. **One-way and two-way door registry.**
    - *gstack:* Every registered question declares `door_type`: 15 one-way, 42 two-way in `scripts/question-registry.ts`. A learned "never ask" preference can auto-decide only two-way questions. Unknown questions fall back to a keyword check that errs toward asking.
    - *Lesson:* Brain procedures tag each decision step one-way (irreversible, consent, publishing, spend, partition-crossing) or two-way. **Code** enforces that one-way steps always reach the human and that learned preferences never suppress them.
12. **Ratchet tests on size.**
    - *gstack:* CI caps the catalog and per-procedure tokens.
    - *Lesson:* The library needs the same, or procedures grow, as gstack's did, to 80 KB.

### 9A.3 What to avoid (poisoning and permission widening)

| Risk | Where gstack shows it | Rule for a brain procedure library |
|---|---|---|
| **Procedures that grant tools** | Skill frontmatter `allowed-tools` pre-approves tools while the skill is active. Many gstack skills list Bash, Write, Edit, Agent and WebSearch | A procedure is **text only**. It never carries tool grants; permissions come from the client's code and config. If procedures are ever exported as Claude Code skills, code generates them from a signed template with a fixed, empty or minimal `allowed-tools` |
| **Procedures that run code** | Frontmatter `hooks` register shell commands that "keep running for the rest of the session" (careful, freeze, autoplan, investigate, plan-ceo-review). Bodies contain executable bash blocks | No hooks and no shell in brain procedures. Actions go through typed MCP tools whose checks are code. A poisoned procedure with a hook would be session-long code execution |
| **Procedures that persist instructions** | "Persist the answer to CLAUDE.md so we never have to ask again"; routing injection commits CLAUDE.md | A procedure never writes to client instruction files. Persistent state goes through the write gate into typed records |
| **Remote auto-update of procedures** | Team mode fast-forwards and re-runs setup hourly, unsigned | Procedure versions are immutable and signed at promotion; clients pin a version; changes are reviewed diffs |
| **Default egress inside a procedure** | Outside voice to Codex by default; Aside research; telemetry prompt; embeddings to Voyage or OpenAI | Steps that send data off-machine are one-way doors bound to the egress class of the caller's client (DA3 innovation 2), checked in code |
| **Auto-logged learnings injected into every run** | "Operational Self-Improvement… runs every time"; the preamble injects the top 3 learnings into each skill start | Learnings attach to a procedure only after review; the agent's own logs are candidates (T3) until then; nothing is injected unreviewed |
| **Auto-promotion by usage** | Domain skills go active after 3 unflagged uses | Promotion = passing tests + named approver; usage counts are telemetry, not trust |
| **Learned preferences that silence safety questions** | `/plan-tune` never-ask preferences, mitigated by the one-way registry | Preferences may suppress only two-way steps, enforced by code; one-way steps cannot be preference-suppressed |
| **Persona, ethos and scope bias** | "Boil the Ocean", CEO "10-star", "Bias toward action" | Procedures carry no persona or ethos text; scope is a declared input |
| **Bloat** | 28 KB preamble per procedure | Per-procedure token budget with a CI ratchet; shared fragments sent once |
| **Cross-partition procedure state** | gstack refuses FOREIGN checkpoints only with a warning, and lets the user load them deliberately | Procedure state (handoffs, checkpoints, learnings) carries partition labels and goes through the same access pre-filter as facts; no "load anyway" across partitions |

**Fit with the three-tier principle (I16).** A procedure is System Two guidance. Its gates are code (tier 1): spend caps, one-way doors, egress class, access checks. The closed checks inside it ("is this step's evidence present?", "is this a one-way action?") are System One decisions with calibrated confidence. gstack mixes the three; its best parts, the hooks, gate parser, snapshot hashes and evidence ledger, are the ones already in code.

### 9A.4 Does gstack interact with or assume Claude Code "ultracode"?

**OBSERVED (gstack).**
- No reference to `ultracode`, dynamic workflows, the Workflow tool or `.claude/workflows/` anywhere in the tree. Bounded search: grep for `ultracode|ultrathink|ultraplan`, then `dynamic workflow|Workflow tool|.claude/workflows`. The only hits are `.github/workflows` in deploy skills.
- gstack assumes the **Agent tool** (subagents) for:
  - Review Army specialists;
  - autoplan voices;
  - CSO independent challengers;
  - `/ship`'s documentation subagent.
- Its shared note says "subagents run in the background by default since Claude Code v2.1.198" and tells the agent to pass `run_in_background: false` (`scripts/resolvers/constants.ts` l.236–242).
- For parallelism it assumes **separate sessions in separate worktrees** (Conductor, 10–15 parallel sprints), not in-session fan-out.

**OBSERVED (Claude Code docs).**
- Ultracode (`/effort ultracode`, or `claude --effort ultracode`, which also sets effort `xhigh`) makes Claude "plan a workflow for each substantive task". "A single request can turn into several workflows in a row: one to understand the code, one to make the change, and one to verify it… each request uses more tokens."
- With ultracode on:
  - the large-workflow warning is off;
  - the session's concurrent subagent limit is not enforced;
  - in auto mode the first-launch approval is skipped.
- Workflow runs allow "no mid-run user input".
- Subagents cannot use AskUserQuestion, and they **load CLAUDE.md** unless a custom subagent sets `omitClaudeMd`.
- Settings hooks fire inside subagents.
- Workflow results are resumable only within the same session, or via `claude --resume`.
- Before v2.1.210, the `ultracode` keyword could be triggered by relayed webhook payloads or PR comments.

Sources: [workflows docs](https://code.claude.com/docs/en/workflows.md), [subagents docs](https://code.claude.com/docs/en/sub-agents.md).

**INFERRED: gstack under ultracode.**
1. **Decision gates degrade silently.**
   - gstack's workflows are built around AskUserQuestion briefs (D1, D2…). A workflow agent has no AskUserQuestion, and its environment inherits the interactive CLI's markers.
   - So `gstack-session-kind` reports `interactive`, unless the script prefixes `GSTACK_SESSION_KIND=spawned`, which a Claude-written workflow script will not know to do.
   - The documented fallback for interactive sessions is "send the complete brief as the turn's final message and STOP". In a workflow agent, that message becomes the agent's *result*, returned to the script, which carries on. **A human gate turns into a string nobody answers.**
   - The spawned escape (auto-choose the recommended option) triggers only if the dispatch prompt explicitly says so.
2. **Token multiplication.**
   - Each workflow agent that invokes a gstack skill loads its 10–100k tokens of process text into a fresh context.
   - With CLAUDE.md loaded in every subagent, any always-loaded mandatory text is paid **per agent**.
   - A 16-agent fan-out of `/review` would carry roughly 600k tokens of process text (16 × 38k). Sibling prompt-cache sharing lowers dollars but not context.
3. **State collisions.**
   - gstack keys session markers to the harness process ID, so all subagents in one Claude process share it.
   - It writes per-project state under `~/.gstack/projects/<slug>/`, with machine-wide locks.
   - Parallel workflow agents in one checkout contend for the same branch, reports and locks. gstack's own design avoids this by giving each session its own Conductor worktree.

**Implication for the owner's previous build (INFERRED; testable as GS14).**
- The builder ran with ultracode. The docs say each request becomes several workflows and every subagent loads CLAUDE.md, and BUILDER-RULES §1.1 requires re-reading the Read-first box and milestone sections at every session start.
- So the **58k mandatory reading may have been paid many times per request, not once per session**. That would explain running out within ~24 hours better than the 58k figure alone.

**Recommendations for our builder:**
- Ultracode **off** by default (`/effort ultracode off`; do not set the `ultracode` setting).
- Workflow size guideline `small`.
- Workflows only for packages that are genuinely fan-out (migration replay, leakage sweeps, bulk audits), as a **saved, reviewed** `.claude/workflows/*.js` with explicit models per stage and minimal allow rules.
- Keep CLAUDE.md ≤8 KB because every subagent pays for it; use `omitClaudeMd` on custom subagents that need only their brief.
- Never rely on workflow resumability for build state; `state.json` remains the source (ADR-019).
- Do not combine gstack skills with workflows.

### 9A.5 Hypotheses added by this angle

| ID | Hypothesis | Decisive test | Kill / adopt criterion |
|---|---|---|---|
| **GS13** | A brain-served procedure (rules-first skeleton ≤1.5k tokens + condition-triggered sections fetched by ID + code-derived state lines) gets the same step compliance as the same content installed as a full gstack-style skill, at ≤40% of the tokens, and works on a non-Claude client | 3 procedures (Diagnose a fault, Ask the owner for a decision, Hand off a task) × 2 delivery modes × 10 reps on Claude; the brain-served mode also × 10 reps on one non-Claude client. Blind checklist grader scores step compliance; tokens from usage | **Kill brain-served delivery** if compliance drops >10 pp vs the skill mode. **Adopt** if within 5 pp at ≤40% tokens and the non-Claude client is within 10 pp |
| **GS14** | Under ultracode, mandatory-reading cost multiplies with agent count; turning ultracode off (with a ≤8 KB CLAUDE.md) cuts tokens per package by ≥50% with no loss in hidden-test pass rate | Bake-off P1, arm A with `--effort ultracode` vs without (same model, same effort otherwise), 6 reps each; tokens from stream-json; count agents per run; hidden tests | **Keep ultracode allowed** if the token difference is <20% at equal pass. **Default off** (protocol rule) if ≥50% saving with pass within 5 pp |
| **GS15** | A procedure library with signed promotion (tests + named approver) and nonce-bound delivery admits and executes 0 poisoned procedures, while gstack-style auto-promotion (3 unflagged uses) admits ≥1 | Plant 10 poisoned candidates through write paths (a step that widens tools, one that exfiltrates to an outside URL, one that says "skip the acceptance test", one disguised as a memory note that imitates a procedure, and similar). Arm 1: auto-promote after 3 uses without a classifier flag. Arm 2: signed promotion + nonce channel. Measure promotion and agent compliance | **Any** poisoned procedure promoted or followed in arm 2 → redesign before the library ships. Arm 1 admitting ≥1 confirms rejecting usage-based promotion |

---

## 10. Findings ledger

| ID | Finding | Status | Strength | Source |
|---|---|---|---|---|
| G01 | Version 1.91.182.0; 422 releases 2026-03-17 → 2026-10-23; 138 in October | OBSERVED | measured | `VERSION`, `CHANGELOG.md` (grep of `## [` headings) |
| G02 | Agent chooses release versions autonomously, default PATCH | OBSERVED | code | `CLAUDE.md` § CHANGELOG + VERSION style |
| G03 | 3,942 files, 78 MB; 563k lines `.ts`, 341k in `test/`; 159 `bin/` entries | OBSERVED | measured | `find`, `wc` |
| G04 | 65 SKILL.md files; 57 in the Claude catalog; 2 test fixtures | OBSERVED | measured | `skills.txt` |
| G05 | SKILL.md generated from `.tmpl`; CI drift checks; resolvers listed | OBSERVED | code | ARCHITECTURE "SKILL.md template system"; CLAUDE.md |
| G06 | Shared preamble median 27,970 B (min 8,087, max 30,056) in 50 skills, placed first | OBSERVED | measured | `pre2.py` |
| G07 | Always-loaded catalog 5,116 B (~1.3k tokens); gstack CI cap 1,197 token-equivalents | OBSERVED | measured / code | `fm.py`; `test/catalog-budget.test.ts` |
| G08 | CLAUDE.md additions 2.2–5.2 KB (routing 882 B, team snippet 526/1,380 B, GBrain guidance 2,210 B, config 301–455 B) | OBSERVED | measured | `bin/gstack-skill-start`, `bin/gstack-team-init`, `CLAUDE.md`, `setup-gbrain/sections/claude-md-persist.md` |
| G09 | Per-path reading cost: review 38k, ship 70k, plan-eng 35k, plan-ceo 38k, autoplan (CEO+Eng) 97k Qwen3 tokens | OBSERVED (bytes) / INFERRED (tokens ±15%) | measured | `tok.py`, `reads.py` |
| G10 | Claude Code loads only descriptions at start; invoked skills persist; after compaction the first 5,000 tokens of each are re-attached (25k total) | OBSERVED | primary docs | [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) |
| G11 | Post-compaction re-attach of gstack skills keeps mostly preamble, not workflow | INFERRED | G06 + G10 | — |
| G12 | autoplan copies full reviewed SKILL.md + review sections into a methodology file and requires reading every 600-line range | OBSERVED | code | `bin/gstack-autoplan-snapshot.ts` l.516–592 |
| G13 | setup falls back from `bun install --frozen-lockfile` to unpinned `bun install` | OBSERVED | code | `setup` l.1931, 2082–2135 |
| G14 | setup downloads Chromium via `bun x playwright install chromium` | OBSERVED | code | `setup` l.2255–2280 |
| G15 | Compiled binaries built with `--no-compile-autoload-dotenv/bunfig` | OBSERVED | code | `scripts/build.sh` |
| G16 | Hooks registered in `~/.claude/settings.json`: Stop timeline (default on), AUQ pre/post (consent), SessionStart auto-update (team) | OBSERVED | code | `setup` §10–11; README |
| G17 | Team-mode auto-update: background fetch + fast-forward + `./setup`, hourly; hook-parse and Bun-floor checks; no signature verification | OBSERVED | code + negative grep | `bin/gstack-session-update` |
| G18 | Update check on by default (GitHub `ls-remote` + raw VERSION) | OBSERVED | code / docs | README "Privacy & Telemetry"; `bin/gstack-config` defaults |
| G19 | Telemetry off by default; prompt recommends "community" (stable device ID); Supabase edge function; fields stripped before upload | OBSERVED | code | `bin/gstack-skill-start` l.526–543; `bin/gstack-telemetry-sync`; `supabase/config.sh` |
| G20 | Outside reviews (Codex) enabled by default; first send prints a notice | OBSERVED | code | `bin/gstack-config` l.200–210; `lib/outside-consent.ts` |
| G21 | Web research goes through Aside's agent first (aside.com), sanitisation instructed | OBSERVED | code | skill sections "Web research runs in Aside" |
| G22 | Sidebar injection classifier downloads ~112 MB from HuggingFace `resolve/main`, no checksum | OBSERVED | code | `browse/src/security-classifier.ts` l.50–132 |
| G23 | CSO images pinned by sha256 digest from ghcr.io/garrytan | OBSERVED | code | `lib/cso/runtime-catalog.json`, `lib/cso/scanner-images/build-inputs.json` |
| G24 | Egress receipts: hash-chained, before send, fail-closed for sensitive sinks; "not a firewall" | OBSERVED | code / docs | ARCHITECTURE "Egress receipt ledger"; `lib/egress-receipt.ts` |
| G25 | Install prompt writes "never use mcp__claude-in-chrome__* tools" into CLAUDE.md | OBSERVED | docs | README Step 1; `CLAUDE.md` "Browser interaction" |
| G26 | Routing injection appends to CLAUDE.md **and commits** | OBSERVED | code | `bin/gstack-skill-start` l.584–615 |
| G27 | Team "required" mode adds a STOP block + repo PreToolUse hook enforcing gstack | OBSERVED | code | `bin/gstack-team-init` |
| G28 | Cookie import decrypts browser cookie DBs; values never in receipts | OBSERVED | docs / code | ARCHITECTURE "Cookie security" |
| G29 | Socket: "Warn", 14 alerts, no malware; eval-of-helper, remote update, stealth, over-scope | OBSERVED (page) | secondary, automated, June 2026 | [skills.sh Socket page](https://www.skills.sh/almeidamarcell/claude-code-skills/gstack/security/socket) |
| G30 | `eval "$(gstack-slug)"` still present in 4 helpers | OBSERVED | code | `bin/gstack-question-log` l.36 etc. |
| G31 | agentskill.sh scored `setup-browser-cookies` 9/100 (curl\|bash); that pattern is not in the current tree | OBSERVED | secondary, March 2026 | [agentskill.sh](https://agentskill.sh/@garrytan/setup-browser-cookies/security); `setup` l.309–318 |
| G32 | Supabase PAT: full-account scope disclosed; env-only; revoke advised; CI argv greps; secret-sink harness | OBSERVED | code / docs | `setup-gbrain/sections/brain-init.md` l.36–50; USING_GBRAIN_WITH_GSTACK.md "Security model" |
| G33 | GBrain MCP registered at user scope; bearer token on argv ~10 ms, rests in `~/.claude.json` 0600 | OBSERVED | docs | `setup-gbrain/SKILL.md` l.590–604 |
| G34 | Transcript ingest needs explicit consent; gitleaks at ingest opt-in, off by default | OBSERVED | code | `setup-gbrain/sections/transcript-gate.md`; `bin/gstack-memory-ingest.ts` l.126–132 |
| G35 | GBrain is single-operator, not multi-tenant | OBSERVED (page) | secondary | [vectorize.io](https://vectorize.io/articles/what-is-gbrain) |
| G36 | `/retro global` reads `~/.claude/projects`, `~/.codex/sessions`, `~/.gemini` | OBSERVED | code | `bin/gstack-global-discover.ts` l.215, 352, 421 |
| G37 | Gate-integrity catalog RH-1…RH-16 plus deterministic tagger; human disposes | OBSERVED | code | `review/gate-integrity.md`; `lib/gate-diff/` |
| G38 | Catalog adapted from a third-party skill of unknown licence | OBSERVED / UNKNOWN (licence) | docs | `review/gate-integrity.md` l.3–4; `docs/designs/HONEST_WORK_GATE_INTEGRITY.md` |
| G39 | Review specialists auto-gated after 0 findings in ≥10 dispatches, except security, data-migration, state-machines | OBSERVED | code | `bin/gstack-specialist-stats` l.36–63 |
| G40 | Confidence calibration requires quoting the motivating line, else confidence 4–5 | OBSERVED | code | `review/SKILL.md` "Confidence Calibration" |
| G41 | autoplan six principles incl. "Boil lakes: auto-approve expansions…" and "Bias toward action"; user challenges never auto-decided | OBSERVED | code | `autoplan/SKILL.md` "The 6 Decision Principles", "Decision Classification" |
| G42 | Spawned sessions auto-choose the recommended option at every decision point; never destructive; never consent | OBSERVED | code | `review/SKILL.md` "Tool resolution"; `bin/gstack-skill-start` l.475–481 |
| G43 | context-save: LLM summary + git state to Markdown in `~/.gstack`, append-only, provenance markers; restore sorts Verify-first | OBSERVED | code | `context-save/SKILL.md`, `context-restore/SKILL.md` |
| G44 | Learnings: decay 1 pt/30 days (observed, inferred); cross-project rows need `trusted:true`; injection sanitising on write | OBSERVED | code | `bin/gstack-learnings-search` l.89, 43–52; `bin/gstack-learnings-log` l.43, 64 |
| G45 | `/eval-plan`: prereg sections, $0 stub dry run with 4 checks, n≈3 priced pilot, locked spend ledger, approval gate | OBSERVED | code | `eval-plan/SKILL.md` |
| G46 | careful hard-denies `rm -r` of `/`, `~`, `$HOME` and force-push to the default branch; freeze fails closed; both "not a security boundary" | OBSERVED | code | `careful/SKILL.md`, `freeze/SKILL.md` |
| G47 | CSO keeps findings out of gbrain, telemetry and learning; reads source only through the redacting helper | OBSERVED | code | `cso/SKILL.md` |
| G48 | Windows: Git Bash + Bun + Node; copies, not symlinks; Aside macOS-only; CSO partial | OBSERVED | docs | AGENTS.md "Platform support"; `setup.ps1`; README |
| G49 | gstack's own ratchet: eager ceilings review 21,047 / ship 21,081 / plan-ceo 21,007 / autoplan 17,005 tokens (SKILL.md only) | OBSERVED | code | `test/fixtures/context-budget.json` |
| G50 | CHANGELOG cites third-party criticism "10K+ tokens before any real code" and a 56.6% catalog cut | OBSERVED | vendor | `CHANGELOG.md` v1.46.0.0 |
| G51 | Author's LOC claim: 11,417 logical lines/day, "810×" vs 2013; 2% revert rate; usage telemetry 305k runs, 95.2% success | OBSERVED (claim) | vendor, self-measured | `docs/ON_THE_LOC_CONTROVERSY.md`; README |
| G52 | Independent audit of the author's public site: 6.42 MB homepage, 169 requests, 28 test files served | OBSERVED (page) | secondary, anecdote; not gstack | [aiweekly](https://aiweekly.co/alerts/developer-audits-yc-ceo-garry-tans-37k-ai-lines-per-day-claim) |
| G53 | Critics: "a bunch of prompts" (Mo Bitar); "wouldn't be featured without the YC title" (Sherveen Mashayekhi) | OBSERVED (page) | secondary, opinion | [TechCrunch](https://www.techcrunch.com/2026/03/17/why-garry-tans-claude-code-setup-has-gotten-so-much-love-and-hate/) |
| G54 | One-month user: kept ~6 of 35 commands; `/qa` and `/plan-eng-review` most useful; vocabulary and culture mismatch; no measurements | OBSERVED (page) | anecdote | [claude-codex.fr](https://claude-codex.fr/en/content/garry-tan-stack-claude-code/) |
| G55 | Expert personas do not improve accuracy (6 models, GPQA Diamond, MMLU-Pro) | OBSERVED (abstract) | independent, single study | [arXiv 2512.05858](https://arxiv.org/abs/2512.05858) |
| G56 | Multi-agent debate can decrease accuracy over time | OBSERVED (abstract) | independent | [arXiv 2509.05396](https://arxiv.org/abs/2509.05396) |
| G57 | Homogeneous 3-agent panel: +8.5 to −4.4 pp across 6 groundedness benchmarks | OBSERVED (abstract) | independent | [arXiv 2608.00243](https://arxiv.org/abs/2608.00243) |
| G58 | Vendor anecdote: Codex outside voice found 15+ issues four Claude reviews missed | OBSERVED (claim) | vendor, anecdote | `docs/ON_THE_LOC_CONTROVERSY.md` |
| G59 | Field reports: shared profile lock killed another project's browser (fixed 1.87.2.0); repeated permission prompts | OBSERVED (page) | secondary | [rywalker.com](https://rywalker.com/research/gstack) |
| G60 | Independent controlled evaluation of gstack quality or cost | UNKNOWN | bounded negative search | see below |
| G61 | Anyone using gstack to build an enterprise or multi-tenant brain with measured outcomes | UNKNOWN | bounded negative search | see below |
| G62 | Issue-tracker failure frequency | UNKNOWN | not accessible | GitHub robots-disallowed; session not authorised for the repo |
| G63 | No reference to ultracode, dynamic workflows, the Workflow tool or `.claude/workflows` in gstack | OBSERVED | bounded grep | §9A.4 |
| G64 | gstack dispatches subagents via the Agent tool with `run_in_background: false`; parallelism assumed via separate Conductor worktrees | OBSERVED | code | `scripts/resolvers/constants.ts` l.236–242; README "10-15 parallel sprints" |
| G65 | Ultracode: a workflow per substantive task, possibly several per request; no large-workflow warning, no concurrent-subagent limit, no auto-mode first-launch approval; no mid-run user input | OBSERVED | primary docs | [workflows docs](https://code.claude.com/docs/en/workflows.md) |
| G66 | Subagents cannot use AskUserQuestion; load CLAUDE.md unless `omitClaudeMd`; settings hooks fire inside subagents | OBSERVED | primary docs | [subagents docs](https://code.claude.com/docs/en/sub-agents.md) |
| G67 | gstack session-kind detection inherits env; subagents inherit parent env byte-for-byte; spawned only via an explicit `GSTACK_SESSION_KIND` prefix or `OPENCLAW_SESSION` | OBSERVED | code | `bin/gstack-session-kind` |
| G68 | Under ultracode, gstack AskUserQuestion gates become unanswered result strings | INFERRED | G65–G67 + AUQ fallback text | §9A.4 |
| G69 | The previous builder's 58k mandatory reading may have been paid per workflow agent under ultracode | INFERRED | G65, G66, BUILDER-RULES §1.1 | GS14 |
| G70 | `plan-ceo-review` frontmatter declares `gbrain.context_queries` (glob or list, sort, limit, `render_as`) | OBSERVED | code | `plan-ceo-review/SKILL.md` frontmatter |
| G71 | Skillify: provenance guard, test in temp dir, explicit approval, atomic commit | OBSERVED | code | `skillify/SKILL.md` |
| G72 | Domain-skills: quarantined → active after 3 uses without classifier flag → global by manual command; rollback | OBSERVED | docs | `docs/domain-skills.md` l.47–63 |
| G73 | Question registry: 15 one-way and 42 two-way questions; keyword fallback errs to asking | OBSERVED | code | `scripts/question-registry.ts`; `scripts/one-way-doors.ts` |
| G74 | Host table labels safety skills "enforced (hooks block)" on Claude Code vs "advisory, not blocked" elsewhere | OBSERVED | docs | README "Other AI Agents" table |
| G75 | Ultracode keyword could be triggered by relayed webhook or PR-comment text before v2.1.210 | OBSERVED | primary docs | [workflows docs](https://code.claude.com/docs/en/workflows.md) "Where the keyword works" |

**Bounded negative searches.**
- **Independent evaluations (G60).** Web queries for "gstack Garry Tan criticism", "gstack review hacker news", "I tried gstack", "gstack token usage", "gstack security vulnerability … CVE", "gstack lines of code controversy". Found news coverage, explainers, scanner pages and anecdotal reviews; no controlled study and no CVE. Not searched: X/Twitter threads, YouTube, Discord.
- **Brains built with gstack (G61).** Query "gstack gbrain second brain build memory agent". Found GBrain setup guides (operator.io, Railway template, vectorize.io, lucaberton.com) and Tan's personal deployment; no enterprise or multi-tenant case with outcomes.
- **Issue tracker (G62).** Not read. A WebFetch of GitHub issues was robots-disallowed, and `gh api` refused because the repo is outside this session.

---

## 11. Checklist closure and threats to validity

| # | Question | Status |
|---|---|---|
| 1 | What it is, template generation, always-loaded size, per-skill cost | **Answered** (§2) |
| 2 | Footprint and security | **Answered statically** (§3). Not verified at runtime; GS9 would verify |
| 3 | Case for | **Answered** (§4); evidence mostly vendor or anecdote |
| 4 | Case against | **Answered** (§5) |
| 5 | Steelman, devil's advocate, verdicts | **Answered** (§6–7) |
| 6 | Hypotheses incl. DA-process and resumability comparisons | **Designed** (§8: GS1, GS2 and 10 more); not run |
| 7 | Custom skill: take and leave | **Answered** (§9) |
| 8 | gstack as a source for a brain procedure library (owner's angle) | **Answered, gstack-specific** (§9A.1–9A.3); general procedural memory belongs to R8 |
| 9 | Interaction with Claude Code ultracode | **Answered** (§9A.4): gstack does not reference it; the degradation is inferred; GS14 tests the build-cost implication |

**Threats to validity:**
- **Static review only.** Runtime behaviour, including actual network calls and hook output sizes, is inferred from code.
- **Token figures use proxies** (Qwen3 BPE; gstack's Opus 4.5 calibration). Current Claude tokenizers may differ by 10–20%.
- **Section-loading paths** ("typical" `/ship`, `/review`, `/qa`) are my reading of the section-index conditions. Real runs may load fewer or more sections.
- **The repo moves ~6 releases a day,** so every observation is tied to v1.91.182.0.
- **Bias.** As in the Superpowers review, the engineer wrote the protocol being compared against. GS1 and GS2 use blind grading and a cross-family grader to reduce this.
- **Third-party scanner results are older** than the reviewed version.
