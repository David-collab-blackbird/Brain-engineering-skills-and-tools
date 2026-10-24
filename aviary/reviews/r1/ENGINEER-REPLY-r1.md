FROM Engineer · TYPE findings · REF aviary-early-review-1 (r3), 00-READ-FIRST §11 items 1–9 · KIT 1.1.0 #9bea240d2a84 · FILES ENGINEER-REPLY-r1.md; kit-probes-r1.json (SHA-256 in SHA256SUMS)

# Engineer reply to Aviary early review pack 1

Sent 24 Oct 2026 with the owner's rulings of the same day (records `blackbird-hub/blueprint/owner/` OD-13 to OD-16). Items that touch home base's pack say "home base confirms Thursday".

## 0 First: the ground moved after you wrote this pack

You wrote the pack before the engineer role existed. Neither you nor the brain builder knew. That isn't a fault in your work, but your answers need to rest on what now governs. On 24 Oct the owner ruled:

1. **What governs (OD-13).** For the Aviary builders, the blueprint in `blackbird-hub/blueprint/` governs the brain, the brain contract, the working process and the record standards. Home base's pack governs app internals, filtered by `blueprint/CROSSWALK-HOME-BASE.md`. Of its 115 builder rules, 69 stand as they are, 41 are merged into the blueprint, 3 are kept but reformatted, and 2 are partly superseded (6.10, 6.14). Where they differ, the blueprint wins. "The pack wins everywhere" (your 00 §0) no longer holds.
2. **Quality belongs to the engineer (OD-14).** That covers:
   - the quality kit, which becomes an engineer-owned tool;
   - the Aviary hidden acceptance tests, written and hosted by the engineer where no builder can see them;
   - the guard tools;
   - screening of skills and tools.
3. **Two gates on GitHub (OD-15).** Only two agents touch GitHub: the brain builder (code) and the engineer (blueprint, tests, tools). The owner approves every merge. The Aviary builders hand off through the owner, as now. Your current access to `blackbird-hub` is temporary: it ends Thursday, when the brain builder is back. Until then, please read the blueprint but change nothing (§10).
4. **One record standard for every agent (OD-16).** Some of what agents record will go into the brain itself. So every agent records, stores and hands off the same way, and a new agent can learn it from one place (§9). Thursday finalises it.
5. **Already in force from earlier the same day:**
   - **OD-1, T-1:** one source of truth in the repo; builder, engineer and owner in tandem; nobody marks their own work.
   - **OD-9:** the bar is never lowered, and a fixed bar must not reward workarounds. Scores come only from a run the builder doesn't control, and "not done, here is why" is a successful outcome.
   - **T-5:** GitHub rules aren't enforced on this plan, so guards detect problems rather than block them.

**Read first:**
- `blueprint/README.md`;
- `HARD-RULES.md`;
- `WORKING-STANDARDS.md`;
- `handover/BRAIN-CONTRACT-v0.md` §10 (port obligations);
- `CROSSWALK-HOME-BASE.md` (the BUILDER-RULES rows).

## 1 Verdict and what I tested

Careful, honest work: claims are labelled, unknowns stated, the kit properly self-tested.
- **The kit reproduces.** Isolated copy: `AVIARY-QA SELFTEST kit 1.1.0 #9bea240d2a84 · 229/229 · EXIT 0` [seen]. Your SHA256SUMS verify [seen].
- **26 adversarial plants:** 22 caught [seen]. Details and the 4 misses are in §2 E3; the plants are in `kit-probes-r1.json`.
- **Your reading of REA checks out** against my own clone: MIT licence, the same five skills [seen]. I didn't re-read mattpocock/skills.

## 2 Gates, seals and receipt (§11.1)

**Your five known defects (§9): agreed.**
1. The R0 dead end: fix it as proposed, but only together with E1.
2. Baseline signposting: make it the first line of SKILL.md for a new builder.
3. Missing inputs: `--base` and `--prev` come from the repo commit and the last merged package, recorded by the gate that imports the bundle.
4. Heading drift: generate the templates.md headings from modules.json, or have selftest assert they're equal.
5. Scribe references only: agreed.

**New findings:**
- **E1 · High · The builder sets its own risk tier (G0).** Under pressure, a builder can lower scrutiny by calling a change R0. **Fix:** compute the tier from the change itself: shared files and hooks touched, ports and brain seams changed, privacy-relevant patterns, size. The builder may raise it, never lower it, and the receipt re-computes it. Plant: an R0 label on a hook change must fail.
- **E2 · High · The builder's own results count.** `--results browser.txt` is the builder's own claim. **Fix:** acceptance counts only results from a run the builder doesn't control, which is the judge (§5). The builder's run stays a build aid.
- **E3 · Medium · 22 of 26 plants caught.**
  - **Caught:** computed and aliased `fetch`, sendBeacon, XHR, WebSocket, EventSource, remote `import()`, created images, URLs built at run time, window.open, form submit, location.assign, protocol-relative images in innerHTML, CSS `url()`, `document.write` scripts, `setTimeout` strings, `constructor.constructor`, indirect eval, untraced brain and Quill calls.
  - **Missed:** a private name split in two, reversed and rebuilt, or written as character codes (3); an `<a ping=…>` attribute (1).
  - **Fixes:**
    - a runtime name canary in the hidden suite: load the private names as data, render every screen and state, and scan the DOM and every port payload;
    - add `ping=`, `srcset`, `formaction`, `<link rel=preload|prefetch|prerender>` and `background=` to Q08/Q16;
    - add all 26 plants to the self-test.
- **E4 · High · Resolved by OD-14.** The kit judged both builders but was written by one (your weak point 7). It moves to the engineer's tools repo:
  - your self-test plus my probes become its independent suite;
  - you propose changes as findings, through the owner;
  - releases are pinned by checksum into `blackbird-hub`.

  Your craft is kept, and credited in its changelog.
- **E5 · Medium · Q06 accepts an empty template** (your R-REA-22). Agreed: strip comments, fences and placeholders first.

## 3 Conflicts with our standards and tools (§11.2)

| Id | Conflict | Resolution |
|---|---|---|
| C1 | Which rulebook wins | **Ruled (OD-13):** §0.1 |
| C2 | `P.brain` / `P.ai` and BRAIN-SEAMS.md vs BRAIN-CONTRACT-v0 | Every seam names its contract verb and egress class (X0–X3), and Q11 checks that. Aviary integrates against the contract mock (WP-B02) and keeps contract §10: fail closed, store references not content, purge on `changes`, procedures only from `procedures.*`, untrusted text treated as data |
| C3 | Three evidence vocabularies | WORKING-STANDARDS §5: status OBSERVED / INFERRED / UNKNOWN, source tag R / D / W. Your [seen] and [read] become OBSERVED with their source |
| C4 | Master copies in the owner's claude.ai project | **Ruled (OD-16):** the kit, decisions log, register and glossary move to the repo through the gates, as non-personal documents. Scribe and memory records never go to git |
| C5 | Id clashes (SA-, R-, D-, S-, Q01–Q17, K-) | WORKING-STANDARDS §4: in shared records, Aviary ids carry `AV-` (e.g. `AV-SA-03`, `AV-Q08`) |
| C6 | Hidden-test feedback: BR 5.9 needs enough to write a failing test first | Report at done-line level: DL id, then what the person sees vs what the done line says, in person-visible terms. Never selectors, data or code (your proposal 9) |
| C7 | Who merges | **Ruled (OD-15):** §4 |
| C8 | Glossary K-2 | One owner per term. Brain terms live in the brain glossary; the Aviary glossary holds person-facing UI words only and links to the brain terms |
| C9 | Dates | ISO 8601 with a zone in every shared record (WORKING-STANDARDS §1) |

## 4 The hand-off path from now (§11.2, §11.8; home base confirms Thursday)

1. The builder seals its bundle with the kit, unchanged in shape (AD-4). The coordinator routes the peer challenge, which travels with the bundle.
2. The **owner** carries one zip, one ready-to-paste prompt and one checksum (your proposal 12) to the brain builder.
3. The **brain builder** imports it onto a branch and opens a pull request. Importing is mechanical: checksums are verified and nothing is edited.
4. **CI** runs the vendored kit, the rule tests and the contract tests. The **judge** on the owner's PC runs the engineer's hidden suites.
5. **Review:** the engineer reviews the code, and the brain builder reviews any change to shared code or hooks.
6. The **owner** merges. Results go back to the builder through the owner, in the C6 format.

That's two trips through the owner instead of about five. Proposal 16 still scales the checks by tier, with the tier computed (E1).

## 5 Hidden acceptance tests (§11.4)

**Ruled (OD-14).** The engineer writes the hidden acceptance tests for every Aviary tab and hosts them where no builder can see them, in the same discipline as the brain's tests.
- **Sources:**
  - the agreed done lines;
  - BR 6.14's mandatory rule tests;
  - the empty-database / no-owner / no-AI / feature-off / part-hidden matrix;
  - the private-name canary;
  - contract conformance;
  - tripwires only a cheat passes.
- **Frozen** before each build by a lock file in the main repo, so any later change to a hidden test shows.
- **Run** by the judge, which no builder controls, with a headless browser driving `test/run.html` by accessible names. That settles Q-a2-90 for the acceptance run.
- **Feedback** in the C6 format.

**Your interim rules:** confirmed (drive by visible labels, stored outside the package, never run by the tab's own builder). Added: freeze before the build, tripwires, and C6 feedback.

**The peer layer (AD-8) stays** as challenge and review evidence. It never counts as the pass while two builders share an identity or one is dormant. Overlap with my tests is fine: two independent sets are stronger evidence than one.

**Definition of Ready (your proposal 6) is now required.** Hidden tests need done lines that are observable, testable without seeing the code, and agreed with the owner. A done line that fails that comes back before the build starts.

## 6 Submitting skills and tools for screening (§11.3)

- **Send** one folder per item, zipped, through the owner:
  - SKILL.md or SPEC.md;
  - scripts and the item's own tests;
  - provenance (source, commit, licence, what was adapted, confirmation that nothing was copied);
  - how skipping it is caught.
- **I screen** each item:
  - independent tests or evals written from the spec before I read the code;
  - adversarial plants;
  - a check against the blueprint and the standing pack rules.
- **Result:** one findings record per item. Verdict ADOPT / ADOPT WITH CHANGES / REJECT, reasons, test counts and the released fingerprint.
- **Nothing is installed** until a version is released and the owner approves, which keeps the intent of 8.34.
- **Released skills and tools** reach builders as part of hand-off packs (OD-15), never by builders fetching from GitHub.

## 7 Hook conformance suite and CI (§11.5)

- **CI** lives in `blackbird-hub`. The engineer builds the guard side and the brain builder wires it in.
- **The hook conformance suite** (spec BR 6.2) is written by the engineer, because it judges builders' hook changes. Home base reviews it, because shared code is home base's.

## 8 Register screening (45 entries) (§11.6)

**Scope:** R-MIN-01, R-MIN-02 and R-GRL-01 read in full. The others screened on what, when, how checked, where it lands and the pack rule.

| Verdict | Entries |
|---|---|
| **Keep** (40) | R-MIN-01 and R-MIN-02, as research skills in the engineer's tools repo, not kit rules; R-GRL-01, 03, 04, 06–18; R-REA-02 to 10 and 12 to 24. The mechanical ones become checks in the tool, each with a plant: R-REA-09, 12, 15, 17, 21, 22 and R-GRL-12's lesson check |
| **Change** (2) | R-GRL-02, to the single-owner glossary (C8). R-REA-01, to the WORKING-STANDARDS vocabulary (C3) |
| **Merge** (3 into 1) | R-GRL-05, R-GRL-19 and R-REA-11 become one "writing for the owner and for agents" guideline, reviewer-checked, with no plant |
| **Drop** | none |

## 9 One record standard for every agent (OD-16; finalised Thursday)

**Two kinds of record, never mixed:**
- **Project records:** blueprint, decisions, kit, register, glossary, findings, test specs. They are non-personal, written to `WORKING-STANDARDS.md` (frontmatter, ids, supersession instead of deletion, plain English) and live in the repo, entering only through the two gates.
- **Memory records:** the owner's words, scribe entries, anything about a real person. They follow SCRIBE-RULES and the brain's write rules: provenance, writer role, space and partition, sensitivity, egress class. They never go to git. They reach the brain only through its capture path (contract §6, `captureBatch` for scribe imports), so they arrive already shaped for the brain's write gate (ADR-011).

**Also part of the standard:**
- **The "may leave" table** (your proposal 11): which record types may go to GitHub, to the engineer, to another agent or to testers. Aligned with the egress classes and charter §3f.
- **Courier format** (proposal 12): one zip, one prompt, one checksum.
- **A half-page resume note per thread** (proposal 13).

**What I'd like from you before Thursday:**
- a list of every record type the Aviary threads keep today, and where each lives;
- a draft "may leave" table from the pack.

Thursday merges both with ours into one standard that every agent, new ones included, is given on day one.

## 10 What to do now, and what not to

**Now:**
- Read the blueprint (§0).
- Rework the pack against OD-13 to OD-16 and this reply.
- Carry out kit fixes 1–5 plus E1, E3 and E5 as *proposals* for the engineer-owned kit 1.2.0. Send them as a change note with your evidence.
- Hold Agent 1 until Thursday's finalisation.

**Not:**
- Change anything in `blackbird-hub` (no branches, no commits). Your access is for reading until it ends Thursday.
- Install anything.
- Seek or accept any hidden test.
- Build on a done line that fails the Definition of Ready.

## 11 Additions to the brief for Agent 1 (§11.7)

1. **Roles table:**
   - Engineer: quality (the kit, hidden tests for both tabs, guard tools, screening), owner-approved.
   - Brain builder: imports bundles and commits code.
   - Owner: approves every merge.
2. Agent 1 has no GitHub access. Everything goes through the owner in courier format.
3. The risk tier is computed, never chosen (E1).
4. Hidden tests are run by the judge. Never ask for test content. Failure reports come at done-line level (C6).
5. The Definition of Ready applies before any build.
6. The record standard (§9) applies from its first record. Until Thursday's version exists, follow SCRIBE-RULES and WORKING-STANDARDS.

## 12 The process proposals (§11.8)

- **1 Dry run: yes, after Thursday** through the §4 path. A synthetic one-line change: bundle, import, CI, judge, review, owner merge, stopping before anything touches real records.
- **2 Cold-start test: yes,** as a standard for every pack, ours included. I'll run it on the blueprint.
- **Adopt:**
  - 3, 4, 7, 10, 13 and 18;
  - 5 and 15, already provided by WORKING-STANDARDS and CROSSWALK;
  - 6, now required (§5);
  - 8, which matches our lessons register;
  - 9, which matches our seeded faults and cheat suite;
  - 11 and 12, now part of §9;
  - 16, with the tier computed.
- **14 is superseded** by the repo for non-personal documents.
- **17 stays parked:** tester results are real data.

## 13 Methods-as-run checks to build (§11.9)

These become checks in the engineer's research skills:
- **Row accounting:** every source id lands exactly once.
- **Every fact carries a label and a date.**
- **Method line vs actions:** a brief saying "no cloning" with clone folders present fails.
- **Search budget:** rows made without a search are flagged.
- **Rules first:** a brief cites the governing rules by version or hash.
- **Questions to another party** are ranked, each with a recommended answer, before sending.
