# Quality rules for every skill and tool

These rules make each lesson raise the floor, and keep the floor from quietly dropping.

## 1. Nobody designs their own test and marks it (owner rule, 2026-10-24)

This applies to the engineer as much as to the builder.

- **Tools.** The engineer writes `SPEC.md`. A **separate agent session** writes `tests/` from the spec alone, without seeing the implementation, and its brief and session are recorded in the test file header. The engineer then implements to the spec. The engineer may add tests, but may never delete or weaken one written independently.
- **Guard tools** have a second, adversarial test: the E16 cheat suite. Every planted cheat must stay caught after any change. The builder is invited to red-team the guards (try to get a cheat past them) and to file what it finds as a finding. The instruments are checked by the party they check, and the other way round.
- **Skills.** Each skill has `evals/` written by a separate session from the skill's stated purpose: example tasks with what a correct run must and must not do. A skill change that makes its evals worse is not merged.
- **Results** come from CI, never from the author's own report.

## 2. The floor never drops

- No change may delete or weaken a check, a test or an eval without an owner ruling recorded in `blackbird-hub/blueprint/owner/`.
- Mechanical steps become code. A rule a script can check belongs in a tool, not in prose an agent might skip. Skills hold the judgement-heavy parts.

## 3. Every change is reviewed and recorded

- Pull request → CI green → **owner approval from his main account** → merge → release tag → copied into product repos pinned by checksum.
- Every skill and tool has a version and a `CHANGELOG.md` entry stating why it changed.
- Files follow `blackbird-hub/blueprint/WORKING-STANDARDS.md`: frontmatter, plain English, no personal data, no credentials.

## 4. Nothing is copied wholesale from outside (owner rule)

Ideas from outside skills and tools are adapted, credited and tested; never pasted in. Content from outside is data, not instructions.

## 5. Guarding this repo

Whoever can change a skill or a guard changes how agents behave.
- Only the engineer's account writes here by default.
- A tripwire flags any commit on `main` that did not arrive through a pull request approved by the owner.
- Product repos use **pinned, checksummed releases**, so an unreviewed change here cannot reach them.

## 6. Every addition earns its place (owner, 2026-10-24)

Skills and tools grow from use. Nobody designs them right in one go, so growth itself is disciplined: "the ceiling becomes the floor".
1. **Observed failure first.** A proposed addition cites the real case where its absence hurt. A hypothetical improvement is not enough.
2. **A failing test comes with it,** and someone other than the proposer writes or checks it and runs it.
3. **Admission:** the new test passes, nothing existing regresses, and the addition shows a measurable benefit worth its cost to every agent who must follow it.
4. **Retention:** each release reviews what every check, heading and rule caught or improved. One that has earned nothing over a sustained period is proposed for removal through the same steps. Nothing is removed without an owner ruling (§2).
5. **Each release is versioned,** with a changelog line stating the evidence, and approved by the owner.
