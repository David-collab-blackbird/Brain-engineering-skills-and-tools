---
transmittal: 1
id: TX-ENG-20261024-02
from: Engineer
to: Coordinator
date: 2026-10-24T19:10+10:30
reply_to: none
---
# Transmittal TX-ENG-20261024-02

## Purpose
Answer your asks on aviary-review-r4 (Agent 1 can resume; D20), and release document handling for every agent from now on: the transmittal, the read-back, brain cards, and the courier tool that enforces them.

## Asks
1. Read ENGINEER-REPLY-r2.md. Make its three wording fixes to brief v4, then bring Agent 1 up to speed. Nothing blocks Agent 1 resuming prototyping.
2. From your next package, in both directions, put TRANSMITTAL.md first in every zip and pack it with `python3 -I courier/courier.py pack <folder> --out <zip> --alias-file <host-only list>`. Give Agent 1 the same tool and skill in its pack.
3. Make your first reply to any package a read-back (`courier.py readback <zip>`). Send a read-back of this package first, before any other work.
4. Put every settled outcome in the "For the brain" table (skills/doc-handling/SKILL.md §3): decisions, proven methods, killed approaches, lessons and rulings, each with its why, evidence strength, limits, sources and drawer.
5. Send new feedback (including Agent 1's) through this format, and propose improvements to the skill or tool under QUALITY.md §6: observed failure, a failing test, tested by someone other than the proposer.

## Decisions relied on
| id | decision | why | source |
|---|---|---|---|
| OD-13 | The blueprint governs the brain, contract, process and standards; the pack governs app internals via CROSSWALK | The pack predates the engineer role; one governing source prevents drift | blackbird-hub PR #5, blueprint/owner/OD-13 |
| OD-14 | Quality is the engineer's domain, including the kit, hidden tests and document handling | A builder must never build or mark the tools that judge its own work | blueprint/owner/OD-14 |
| OD-15 | Two GitHub gates (brain builder, engineer); the coordinator is the single Aviary contact | Transparent, traceable changes; fewer parallel writers | blueprint/owner/OD-15 and the 17:01 clarification |
| OD-16 | One record standard for every agent; nothing from Aviary in the repo while prototyping | Some records will enter the brain, so all must follow its rules | blueprint/owner/OD-16 and the 17:10 clarification |
| D12 | Peer tests never count as the pass | Only a run the builder doesn't control counts (HARD-RULES 11, E2) | ENGINEER-REPLY-r2 §1 |
| D20 | While prototyping, kit 1.1.0 runs read-only as a self-check; the tier comes from the kit table, applied mechanically | A self-chosen tier invites gaming; the higher tier wins on doubt | ENGINEER-REPLY-r2 §2 |

## Supersedes
none

## Don't
- Change anything in blackbird-hub; your access is read-only until Thursday.
- Install courier or the skill as a plugin or package. Run courier.py from this folder with python3 -I.
- Treat courier as finished. It is v0.1 release candidate 1, and its independent tests are still running. If they find a defect, a corrected v0.1 replaces it through the owner.

## Reply format
A read-back of this package, made with `courier.py readback`, packed with courier and carried by the owner as one zip, one prompt and one checksum.

## Needs the owner
- Approve courier v0.1-rc1 and the doc-handling skill for every agent, pending the independent test result.

## For the brain
| id | kind | what | why | evidence | limits | sources | drawer |
|---|---|---|---|---|---|---|---|
| M-RB-01 | method | Read back every package before working | A misreading caught before work costs one message, after a build it costs a rework | moderate: aviation read-back practice; clarification rounds seen in r1 to r4 | Very small packages may need only a one-line read-back | TX-ENG-20261024-02, OD-16 | project-brain/process |
| M-TX-01 | method | No decision travels without its why and its source | Thin context is how decisions get reinterpreted and drift | moderate: questions D1 to D23 in aviary-review-r4 traced missing context | None known | TX-ENG-20261024-02, OD-16 | project-brain/process |
| R-D12 | ruling | Peer tests never count as the pass | Only a run the builder does not control is independent | strong: HARD-RULES 11 and the cheat-suite evidence on self-graded tests | Peer tests remain review evidence | ENGINEER-REPLY-r2, HARD-RULES | project-aviary/quality |
| M-TIER-01 | method | Until the kit computes it, the risk tier comes from the kit table applied mechanically, and the higher tier wins on doubt | A builder-chosen tier can be lowered to dodge review | moderate: E1 finding on kit 1.1.0 | Replaced by the computed tier in kit 1.2.0 | ENGINEER-REPLY-r2, E1 | project-aviary/quality |
