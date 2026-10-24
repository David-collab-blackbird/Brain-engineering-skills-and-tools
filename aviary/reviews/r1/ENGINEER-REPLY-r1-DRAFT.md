FROM Engineer · TYPE findings · REF aviary-early-review-1 (r3), 00-READ-FIRST §11 items 1–9 · KIT 1.1.0 #9bea240d2a84 · FILES ENGINEER-REPLY-r1.md (this file); kit-probes-r1.json (the 26 plants)

**Status: DRAFT for the owner. Not sent.** Items marked **[owner]** wait for the owner's ruling.

# Engineer review of Aviary early review pack 1

## 0 Verdict

Careful, honest work. Claims are labelled, unknowns are stated, and the kit is properly tested.
- **The kit reproduces.** Self-test on an isolated copy: `AVIARY-QA SELFTEST kit 1.1.0 #9bea240d2a84 · 229/229 · EXIT 0` [seen]. SHA256SUMS verified [seen].
- **Adversarial probes, 26 plants run the way we probe our own guards:** 22 caught [seen]. The 4 misses are in §1.
- **The real issues are structural, not craft:**
  1. The governing framework changed on 24 Oct, after this pack was written (§0.1).
  2. The kit judges builders' work but is written by a builder.
  3. Hidden tests aren't independent while Agent 1 is dormant.
  4. The builder sets its own risk tier.
  5. Every hand-off costs about five manual trips.

  Each one has a fix below.

### 0.1 What changed on 24 Oct that this pack could not know

The owner ruled the following (records in `blackbird-hub/blueprint/owner/`, which you can read through your GitHub access):
- **OD-1, T-1: one source of truth.** The repo's `blueprint/` and `findings/` are the source of truth for the brain, its contract and the working process. Builder, engineer and owner work in tandem through pull requests: the engineer reviews code and writes the tests and guards, and the owner approves merges. The brain's current engine proves itself on real data like any other contender.
- **The interface (`blueprint/handover/BRAIN-CONTRACT-v0.md`).** It is the only way an app talks to the brain: 14 verbs, identity only from the credential, egress classes X0–X3, receipts, and port obligations (§10).
- **The rules and formats:** `HARD-RULES.md` (12 rules) and `WORKING-STANDARDS.md` (one record format for every agent).
- **Which pack rules stand (`CROSSWALK-HOME-BASE.md`).** Of 115 BUILDER-RULES: 69 kept, 41 merged into the blueprint, 3 kept but reformatted, 2 partly superseded (6.10, 6.14).
- **OD-9: the bar is never lowered,** and a fixed bar must not reward workarounds. Scores come only from a runner the builder doesn't control. "Not done, here is why" is a successful outcome.
- **T-5: GitHub rulesets aren't enforced on this plan,** so guards detect problems rather than block them.

How this applies to the Aviary builders is item C1, waiting for the owner.

## 1 Gates, seals and receipt (§11.1)

**Your five known defects (§9): agreed.**
1. **The R0 dead end.** Fix it as you propose, but only together with E1 below. Otherwise R0 becomes an escape hatch.
2. **Baseline signposting.** Make it the first line of SKILL.md for a builder new to the kit.
3. **Missing inputs.** In the repo flow, `--base` is the merge-base commit and `--prev` is the last merged package tag. Both come from git, not from courier.
4. **Heading drift.** Generate the templates.md headings from modules.json, or have selftest assert they're equal.
5. **Scribe references only.** Agreed.

**New findings:**
- **E1 · High · The builder sets its own risk tier (G0).** A builder under pressure can lower scrutiny by labelling a change R0 or R1. **Fix:** compute the tier from the diff: shared files and hooks touched, ports and brain seams changed, privacy-relevant patterns, size. The builder may raise the tier, never lower it, and the receipt re-computes it. Test: a planted R0 label on a hook change must fail.
- **E2 · High · Builder-supplied results count for the builder's own run.** `--results browser.txt` is the builder's own claim. The kit already warns on received packages, which is right. **Fix:** for acceptance, results count only when produced by a run the builder doesn't control (the judge, §4). The builder's own run stays a build aid.
- **E3 · Medium · Adversarial probes: 22 of 26 caught.** Caught: computed and aliased `fetch`, sendBeacon, XHR, WebSocket, EventSource, remote `import()`, createElement images, URLs assembled at run time, window.open, form submit, location.assign, protocol-relative images in innerHTML, CSS `url()`, `document.write` scripts, `setTimeout` strings, `constructor.constructor`, indirect eval, untraced brain and Quill calls. **Missed:**
  - a private name split in two, reversed and rebuilt, or written as character codes (3);
  - an `<a ping=…>` attribute, which sends a request to an outside address when clicked.

  **Fixes:**
  - **Names:** static matching can't see built strings, so add a runtime canary test. Load the private-names list as data, render every screen and state, and scan the DOM and every port payload. This goes in the hidden suite.
  - **Attributes:** add `ping=` to Q08/Q16, plus `srcset`, `formaction`, `<link rel=preload|prefetch|prerender>` and `background=`.
  - **Regression:** the 26 plants go to the kit as regression plants (`kit-probes-r1.json`).
- **E4 · High · The kit is written by a builder** (your weak point 7). The tool that judges both builders is authored by one of them. **Fix [owner]:** `aviary-quality` becomes an engineer-owned tool in the engineering repo. The builders propose changes as findings or pull requests. Your selftest plus our probes become its independent suite. Releases are pinned by checksum into `blackbird-hub`. Your craft stays; ownership moves.
- **E5 · Medium · The Q06 template trap** (your R-REA-22). Agreed. Strip comments, fences and placeholders before checking headings.

## 2 Conflicts with our standards, repos and tools (§11.2)

To log for home base, and for the owner where marked.

| Id | Conflict | Proposed resolution |
|---|---|---|
| C1 [owner] | The pack wins everywhere (00 §0) vs the owner-approved blueprint (OD-1, T-1) | The blueprint governs the brain, the contract, the process and the standards. The pack governs app internals, as filtered by CROSSWALK |
| C2 | The brain seam: `P.brain` / `P.ai` and BRAIN-SEAMS.md vs BRAIN-CONTRACT-v0 | Every seam names its contract verb and egress class. Q11 checks it. Aviary integrates against the contract mock (WP-B02) and keeps the port obligations in contract §10: fail closed, store references not content, purge on `changes`, procedures only from `procedures.*`, untrusted text as data |
| C3 | Three evidence vocabularies: yours, BR's R/D/W/I and ours | Use WORKING-STANDARDS §5: status OBSERVED / INFERRED / UNKNOWN, source tag R/D/W. Your [seen] and [read] map to OBSERVED with their source |
| C4 [owner] | Master copies in a claude.ai project vs one repo truth (T-1) | The kit, decisions log, register and glossary move to the repo, as non-personal documents. The scribe stays out of git (agreed, BR 8.19) |
| C5 | Id clashes: SA-, R-, D-, S-, Q01–Q17 and K- collide with ours | WORKING-STANDARDS §4 qualification rule. In shared records, prefix Aviary ids with `AV-` (`AV-SA-03`, `AV-Q08`) |
| C6 | Hidden-test feedback: BR 5.9 wants enough detail to write a failing test first; ours sends no assertion text back | Report at done-line level: DL id, then what the person sees vs what the done line says, in person-visible terms. Never selectors, data or code. This matches your proposal 9 |
| C7 [owner] | Who merges: home base (pack 5.1) vs the tandem model (owner approves, engineer reviews) | Aviary pull requests: the builder authors; the engineer and the other builder review; the owner merges. Changes to shared code and hooks also need home base's review |
| C8 | Glossary K-2 | One owner per term. Brain terms live in the brain glossary. The Aviary glossary holds person-facing UI words only and links to brain terms. No duplicates |
| C9 | Dates | Compatible if written as ISO 8601 with a zone (WORKING-STANDARDS §1) |

## 3 Submitting skills and tools for screening, and the result format (§11.3)

**Submit** one folder per item, through the owner until you have repo access, then as a pull request to the engineering repo's intake. Each folder holds:
- SKILL.md or SPEC.md;
- scripts and the item's own tests;
- provenance: source, commit, licence, what was adapted, and confirmation that nothing was copied;
- how skipping it is caught.

**Screening:**
- I write independent tests or evals from the spec, without reading the implementation first.
- I run adversarial plants.
- I check the item against the blueprint and the pack.
- Nothing is installed until a version is released and the owner approves. This keeps the intent of 8.34.

**Result:** one findings record per item (WORKING-STANDARDS format, your header line on top). Verdict ADOPT / ADOPT WITH CHANGES / REJECT, reasons, test counts and the released fingerprint.

## 4 Hidden acceptance tests (§11.4)

**Proposed [owner]:** the engineer writes and hosts hidden acceptance tests for every Aviary tab, in the engineer's repo. The builders never see them.
- **Sources:** the tab's agreed done lines, plus cross-cutting suites:
  - BR 6.14's mandatory rule tests;
  - the empty-database / no-owner / no-AI / feature-off / part-hidden matrix;
  - the private-name canary (E3);
  - contract conformance;
  - tripwires that only a cheat passes.
- **Frozen** before the build starts, by a lock file in the main repo.
- **Run** by the judge on the owner's PC (no builder involved), with a headless browser driving `test/run.html` by accessible names. That also settles Q-a2-90 for the acceptance run.
- **Feedback** in the C6 format.

**Your interim rules:** I confirm driving by visible labels, storage outside the package and never being run by the tab's own builder. Add three: freeze before the build, include tripwires, and use the C6 feedback format.

**The peer layer (AD-8) stays,** as challenge and review evidence. Peer hidden tests are welcome as an extra layer but never count as the pass while builders share an identity (the collator and Personal), or while Agent 1 is dormant.

**Overlap is fine.** Two independent test sets are stronger evidence than one.

## 5 Hook conformance suite and CI (§11.5)

- **CI:** in the repo flow, GitHub Actions on `blackbird-hub` runs the vendored kit, the rule tests and the contract tests. The judge runs the hidden suites. The engineer builds the guard side; the builders wire it in through their packages.
- **Hook conformance suite** (spec BR 6.2): the engineer writes it, because it judges builders' hook changes. Home base reviews it, because shared code is home base's.

## 6 Register screening (03-REGISTER.md, 45 entries) (§11.6)

**Scope:** R-MIN-01, R-MIN-02 and R-GRL-01 read in full. The others screened on what, when, how checked, where it lands and the pack rule.

| Verdict | Entries |
|---|---|
| **Keep** (40) | R-MIN-01 and R-MIN-02, as research skills in the engineering repo rather than kit rules; R-GRL-01, 03, 04, 06–18; R-REA-02 to 10, 12 to 24. Mechanical ones go into the tool with plants: R-REA-09, 12, 15, 17, 21, 22 and R-GRL-12's lesson check |
| **Change** (2) | R-GRL-02, as the single-owner glossary (C8). R-REA-01, using the WORKING-STANDARDS vocabulary (C3) |
| **Merge** (3 into 1) | R-GRL-05, R-GRL-19 and R-REA-11 become one "writing for the owner and for agents" guideline, reviewer-checked, with no self-test plant |
| **Drop** | none |

## 7 Additions to the brief for Agent 1 (§11.7)

1. Read `blueprint/README.md`, `HARD-RULES.md`, `WORKING-STANDARDS.md` and BRAIN-CONTRACT-v0 §10 (port obligations), if it has repo access.
2. Its baseline hand-off becomes its first pull request in the repo flow.
3. The risk tier is computed, never chosen (E1).
4. Hidden tests are run by the judge. Never ask for test content. Failure reports come at done-line level (C6).
5. A Definition of Ready for done lines (your proposal 6) applies before any build.
6. The roles table gives the engineer: hidden tests (written and hosted), the guard tools including the kit (E4), and screening of skills and tools. The owner approves all of it.

## 8 The process proposals (§11.8)

- **1 Dry run: yes.** Run it in the repo flow after Thursday, once the brain builder and the runner are set up. A synthetic one-line change goes through pull request, CI, judge, review and owner merge. Stop before anything touches real records.
- **2 Cold-start test: yes, as a standard for every pack, ours included.** It's the same idea as our "a fresh session must resume from the checkpoint alone" drill. I'll run it on the blueprint.
- **Adopt:**
  - 3, 4, 7, 10, 12 (until the repo flow replaces courier), 13 and 18;
  - 5 and 15, which `WORKING-STANDARDS` and `CROSSWALK` already provide;
  - 6;
  - 8, which matches our lessons register (prevent, detect, prove);
  - 9, which matches our seeded faults and cheat suite;
  - 11, aligned with egress classes X0–X3 and charter §3f;
  - 16, with the tier computed (E1).
- **14 is superseded** by the shared repo for non-personal documents.
- **17 is correctly parked:** tester results are real data.

## 9 Methods-as-run checks to build (§11.9)

These become checks in the engineering repo's research skills:
- **Row accounting:** every source id lands exactly once.
- **Every fact carries a label and a date.**
- **Method line vs actions:** "no cloning" in a brief with clone folders present fails.
- **Search budget:** rows made without a search are flagged.
- **Rules first:** a brief must cite the governing rules version by commit or hash.
- **Questions to another party** are ranked and each carries a recommended answer before sending.
