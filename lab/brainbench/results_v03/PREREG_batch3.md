# Batch 3 preregistration (BrainBench v0.3)

Frozen: 2026-10-24, before any paid LLM call of batch 3. Author: Claude (engineer). Changes after this point are listed at the bottom with a reason and a timestamp.

## 0. Spend discipline
- Cap: **$200 total** for batch-3 LLM calls (env `BB3_CAP_USD`, enforced in `bb/llm3.py` before every call). The ledger is `results_v03/spend_ledger.jsonl`. It records each call's model ID (from the CLI's `modelUsage`), tokens, USD (`total_cost_usd`, cost basis "list"), wall time, stage and batch id.
- Order: (1) free dry run: validators and scorers must pass a gold reference and fail planted broken solutions; (2) a priced pilot of 3 gate batches per model, then a cost estimate per seed; (3) scale only inside the cap, in this priority order: E9 small writer (claude-haiku-5-5) on 3 seeds → E9 frontier writer (claude-sonnet-5-5) on seed 1 → the fabrication suite → E-SCR writers → E9 frontier on seeds 2–3 if the budget allows.
- One claude process at a time (file lock shared by all batch-3 stages). Minimal CLI context: no tools, MCP, settings, slash commands or session persistence. `--bare` is not usable because it needs an API key and this account signs in with OAuth.
- Models are pinned per arm: W-small = `claude-haiku-5-5`, W-frontier = `claude-sonnet-5-5`. Neither is a local model. "Small" stands in for the ADR-016 local extractor, which this sandbox cannot run at this scale. This is a threat to validity, stated up front.

## 1. Benchmark v0.3 (fixed before results)
- 3 seeds (1, 2, 3). Each has about 11.15k items, 2.64–2.72k tasks, and 13–534 distinct need-sets per class. The v0.2 classes have 124–534 sets per class per seed. The new classes are smaller (13–75 per seed); see the threats.
- Pipeline view: no entity tags, fact_refs, scope or special tags. 293 keys per seed are extract-only (goals, rules, strategy, suppliers, roles, stages, programs, activities, property managers, hours, budgets). They are rendered as free-text statements. Connector keys keep their entity id.
- Held-out vocabulary: per task, the reference form is drawn as registry 0.35 / seen 0.25 / held-out descriptor 0.20 / held-out nickname 0.20. Seen nicknames appear in 1–2 of the person's own earlier messages. Held-out nicknames appear nowhere in the corpus (checked by code). Held-out descriptors share no token with registered aliases.
- Access: generic space templates (company, trust, household, person, member). There is no standing owner or partner access to member spaces. Member account records are company records. Coaches get consented, time-boxed shares (about 20% expired). Spouse and partners have personal vaults. A credential with no grant reads nothing.
- Vital and helpful labels are fixed per template in `bb/tasks3.py` (`RULES`, `label_vital`) before any run.

## 2. Metrics (all experiments)
- **CR_vital@B**: every vital required item is in the context. Cards and timelines credit an item only when they state that item's value correctly. Also reported: CR_all@B (vital + helpful).
- Budgets: K = 10 / 50 / 100 items and T = 1k / 4k / 8k tokens (bge tokenizer over the text shown to the reader).
- **Primary budget: K = 50 and T = 4k** (DA2's knee). The others are secondary.
- Rates are means over distinct sets, with Wilson 95% intervals (n = distinct sets pooled over seeds). Paired comparisons use an exact sign test over distinct sets, with a cluster-bootstrap 95% CI on the difference. Certification uses one-sided Clopper-Pearson.
- **Target pool**: decision_support, option_analysis, goal_tracking, preference_recommendation, cross_domain. **N8 pool**: decision, option, cross.

## 3. Experiments, arms and decision rules

### E9 / N8 / U1: structure at write
Arms (same retriever for all: weighted BM25 + bge-small, α = 0.2, visible-set BM25 statistics, forward-to-head):
- A0 query-only.
- **A1 batch-2 best arm re-implemented on v0.3**: two-regex router → cards (≤3) + static slots, with no write gate (cards from connector keys only). Batch 2's 57.8% was measured on v0.2 with free gold structure and is not comparable; A1 is the comparator.
- A2 code gate: registry string-match links plus the space's owner entity; no typed records. Router + connector cards + entity neighbourhood (evidence linked to query-linked entities, ranked by query score).
- **A3 LLM gate (haiku)**: links, typed records, extracted keyed facts (with code validators) and learned aliases. Router + cards from connector and extracted keys + slots + entity neighbourhood, with typed records first.
- A4 LLM gate (sonnet): same as A3 (seed 1; 3 seeds if the budget allows).
- A5 gold gate (oracle ceiling): same as A3 with gold links and records.
- Ablations on the A3 gate: cards only (no neighbourhood); neighbourhood without typed-first ordering.

Extraction metrics: linking precision and recall (all items; required evidence; implicit vs explicit mentions); typed-record coverage per type (and on implicit-mention items); extract-only keyed-fact recall and wrong-value rate; invented-value rate (records the validators drop because the value is not in the item); validator drop counts.

Decision rules (primary = A3 vs A1, CR_vital@K50, 3 seeds):
- **N8 supported** if Δ ≥ +5 pp on the N8 pool with sign-test p < 0.05. **Killed** if the point estimate is < +5 pp at both K = 50 and T = 4k. If it passes at K = 50 but not at K = 10, record "budget-dependent" (DA2's prediction).
- **U1 / E9**: kill if Δ < +10 pp on the target pool, or if structure reaches < 50% of the required vital free-text items. "Reaches" = the gate links the item to an entity the query linker finds, or a card states its value correctly.
- **DT-U1b** (DA2): kill U1's typed-extraction step if A3 minus "A3 cards only" < +5 pp on decision + option + goal at K = 50.
- **Coreference SLO**: implicit-mention link recall < 80% → "invest in coreference before more schema work".

### Fabrication suite (DT-U1a, part of E9)
200 items per seed-1 sample: 100 where the asked attribute is stated, 100 where it is not. Three instruction schemas: required, nullable, nullable + span-required. W-small and W-frontier. Fabrication = a value returned for a not-stated field. For the span schema, fabrication is measured after the code validator (value in span, span verbatim).
- Kill the required-field schema if fabrication ≥ 5%.
- Accept span-grounding if fabrication ≤ 1% and true-field recall is within 3 pp of the required schema.

### E10 / E10b / U2 / U2a: double entry
The searchable entry is appended to the index text only (the reader sees the item text). Arms, on the A3 gate's links:
- (c) raw.
- (a) code header: registered aliases of linked entities + learned aliases (alias statements validated by span) + thread/sender (already in raw).
- (b) LLM scribe phrases (the gate's `k`), unfiltered.
- (b′) scribe filtered (keep phrases whose bge cosine to the item is ≥ the 30th percentile of the seed's phrase scores, i.e. drop the worst 30%, Doc2Query-- style).
- (a+b′).
- Values-included variant of (a): extracted fact values added to the header.

Query side: query-only and A3 assembly. Report CR_vital@K50 by ref_form (registry / seen / heldout_desc / heldout_nick).

Decision rules:
- **U2** (LLM scribe) killed if (a+b′) − (a) < +3 pp on the held-out forms pooled (heldout_desc + heldout_nick), or precision@10 falls by > 3 pp.
- **U2-code** (deterministic header) supported if (a) − (c) ≥ +3 pp on the seen form.
- **U2a**: stale exposure with values vs without. Kill U2a if there is no difference: |Δ stale| < 1 pp with the 95% CI inside ±2 pp.
- Stale and temporal pairs are always reported together: stale exposure on stale probes, plus temporal CR on the same keys.
- Stale exposure = a superseded version, or an item quoting a superseded value, ranks above the current value in the top 10, or appears in the top 10 with the current value absent.

### E-SCR: the owner's scribe (scaled down, seed 1)
- Inputs: 240 owner-voice conversation turns from the owner's own spaces (household, person, trust, companies), including 40 spouse-chat turns that SCRIBE-RULES forbids recording.
- Writers: W-small and W-frontier, with SCRIBE-RULES.md as the system prompt plus a BrainBench handle map.
- Checker arms: G0 = scribe_check.py as shipped; G1 = G0 + C2 (value-level evidence quotes: verbatim span + value-token-in-span) + C4 (origin↔source); G2 = G1 + an advisory System One pass (NLI-xsmall cross-encoder support score on summary vs words).
- Metrics:
  - format validity at first check;
  - extraction coverage (all and implicit);
  - invented-value rate;
  - linking precision and recall;
  - forbidden-capture rate (spouse chats);
  - catch rate on 5% seeded bad readings (wrong value, wrong entity, unsupported claim) per checker arm;
  - spoof count (`home:` self-confirmation) under G0 vs G1+C1.
- Kill rules (B-scribe §5.3): span-required rules must keep fabrication ≤ 1% with ≤ 3 pp coverage loss. Model-written keywords must beat a handle header by ≥ 3 pp (tested in E10) or be dropped.

### I15: certified recall
Nonconformity = the item rank and the token count at which the last vital item enters the A3 context (up to 400 items). Calibrate on seeds 1–2 (one task per distinct set), test on seed 3, plus split-conformal within seeds (200 splits). Per class: K̂ and T̂ at α = 0.10, realised coverage, and the one-sided 95% Clopper-Pearson lower bound on held-out coverage.
- Kill for a class if coverage misses the target by > 2 pp on the other-seed split, or if T̂ > 8k tokens (reader budget).

### ADR checks (no LLM)
- **DA1-4**: BM25 with frozen external statistics (WikiText-2 train; real general-domain text, not a twin world) vs visible-set vs per-partition statistics. Query-only BM25 and hybrid, 3 seeds. Kill frozen IDF if the loss is ≥ 1 pp vs visible-set.
- **S2 / S3**: twin-world noninterference. A reference engine plus 10 injected leak classes (DA3 §5.7 list). For every non-owner identity, W′ = W + random mutations confined to spaces it cannot see. Observables: ids, order, rounded scores, counts, snippets, errors, cache/latency class.
  - S2 passes if it detects 10/10 classes and the reference engine shows 0 differences.
  - S3: canaries detect ≥ 50% of classes, or they are demoted.
  - GBrain lesson: a no-grant credential returns 0 rows in every arm.
- **DA1-6**: key timelines vs indexed version rows at +0 / +10 / +40 synthetic versions per connector key. Kill timelines if temporal CR_vital@10 at +40 is > 5 pp below +0.
- **DA1-7**: values-free stub cards (read-time values) vs stored cards. Kill if the loss is > 1 pp on 3 seeds.
- **Exit check**: delayed index (stale ACL snapshot plus erased items still indexed) with vs without a read-time exit check. Pass if leaks drop to 0 with ≤ 1 pp recall cost.

### H17: aggregation (exact-set)
- "Records" arm: a deterministic spec parser (cue words → record type; query linker → entity; else visible spaces) over the gate's typed records, compared with top-K retrieval and the gold-record ceiling.
- H17 supported if records ≥ 90% exact-set recall (CR_vital) where top-K at K ≤ 50 is < 60%. Killed for "SQL first" if records < 80% because of extraction misses (DA2 DT-013).
- Absence tasks: correct = empty set returned.

### E11: self-healing vocabulary (if time)
Simulated year of requests with held-out nicknames, corrections, 20% referent drift and 10% wrong picks. Arms: none / item-level append / entity-level alias with time scope. Kill U2b if net CR change after 100 corrections is < +2 pp, counting regressions. Kill item-level appends if entity-level gives ≥ the gain with ≤ half the regressions.

## 4. Change log after freezing
(entries appended below)
- 2026-10-24 (after the priced pilot, before any main run): the gate prompt gains one line asking for compact JSON (one object per line). Reason: the pilot showed haiku emitting 9–17k output tokens per 50-item batch (about 45 s each). Content instructions are unchanged. The quality report gains a lenient link precision: a predicted entity outside gold counts as correct when the item text names a registered alias of it. Reason: the pilot showed v0.2-derived gold tags on filler items omit explicitly named staff. Pilot cost: haiku $0.0073–0.0114 per batch, sonnet $0.093–0.136 per batch. Projected: haiku about $1.7 per seed, sonnet about $16 per seed. Execution order inside the frozen priority list: haiku s1 → sonnet s1 → fabrication suite → E-SCR → haiku s2, s3 → sonnet s2, s3 (decision rules unchanged).
- 2026-10-24 05:25: pilot of haiku with --effort low (3 batches, $0.025): link precision 0.67 vs 0.84 at default effort, about the same speed (34–41 s vs 45–56 s per batch). Default effort kept for the gate. The parser now also accepts JSONL output (one pilot output came without array brackets). The haiku s1 gate files will be re-validated from the cache with the fixed parser before analysis (no new calls).
- 2026-10-24 06:05 (analysis-time correction, fabrication suite): (1) null detection now treats answers that begin "not stated…" (e.g. "not stated in item") as abstentions. The first scorer counted them as fabricated values and inflated required-schema fabrication from about 6% to 55%. (2) 1 of the 100 'not stated' items actually stated an older value of the asked key (rendered '$461k' vs canonical '$461,000'). It is excluded from both fabrication and recall (n = 99). The raw model outputs are unchanged and kept in fab.pkl.
- 2026-10-24 07:35 (implementation fix, DA1-6): the first timeline arm pinned every timeline of every query-linked entity. That flooded the context (e.g. 12 business timelines for a member-plan question) and is not DA1's design. Re-implemented as DA1 specifies it: version rows collapse to their key's timeline in ranking (each version hit is replaced by its key's timeline doc, deduplicated). The first-implementation numbers are kept in the log; the DA1-6 verdict uses the corrected arm.
- 2026-10-24 08:35 (implementation fixes, S2/S3, before the verdict): (1) the canary monitor counted canaries the prober was ALLOWED to see as alarms (122/360 on the reference engine). It now alarms only on canaries from spaces the prober cannot see. (2) The twin-world mutation never changed a hidden keyed fact, so derived-card widening could not be observed. W' now also adds a new hidden version of up to 3 connector keys of entities the prober shares, as DA3's S2 specification requires. The S2 run was redone; the first run is kept as s2_v1. The hash()-based mutation seed was also replaced with a deterministic one.
- 2026-10-24 09:25 (parser fix, no new calls): sonnet sometimes emits '[{first object}]' followed by JSONL lines. The parser took the 1-object array and dropped the rest, leaving 572 items 'missing' on s1. It now keeps whichever parse (array or lines) yields more objects. s1 gates were re-validated from the cache: sonnet 9 missing, haiku 25 missing (of 8,324 text items). E9 haiku s1 arms ran on the 26-missing version (1 item difference). All later gates are re-validated the same way.
