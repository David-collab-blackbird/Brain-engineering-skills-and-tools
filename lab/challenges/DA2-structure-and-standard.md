---
id: DA2-structure-and-standard
type: blueprint
title: "DA2: Devil's-advocate review of structure-first retrieval and the standard"
status: draft
version: 0.5
date: 2026-10-23
author_role: engineer
supersedes: []
superseded_by: null
decisions: [ADR-001, ADR-006, ADR-009, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014, ADR-016, ADR-017, ADR-018, ADR-020]
tests: []
evidence: []
sensitivity: none
---

# DA2: Devil's-advocate review of structure-first retrieval and the standard

Status: challenge v1 (2026-10-23) · Reviewer: Claude (devil's advocate, cluster 2) · Scope: M1, U1/U2/U2a/U2b (ADR-011), ADR-012, ADR-013, ADR-017, ADR-020, charter §8.
Inputs read: charter v0.5, hypotheses board v0.6 (M1, B2, B3), docs02 README and ADRs 010–013, 017, 018, 020, `brainbench/RESULTS.md`, `RESULTS_batch2.md`, `results_v02/tables.md`, the generator (`bb/tasks2.py`, `bb/world2.py`) and seed-1 data.

**New evidence in this review.** I ran 10 small re-analyses on the existing BrainBench v0.2 data and caches (no new model downloads; CPU; ≤2.5 min each). Scripts and raw outputs are in `challenges/da2_analysis/` (`da_a1.py` … `da_a10.py`). A1 pools 3 seeds from the batch 2 pickles. A2–A10 use seed 1 only (≈2.2k tasks, 129–554 distinct sets per class). All rates are means over distinct required sets, as in batch 2. The same caveat applies as everywhere else: synthetic, templated world, so directions count for more than sizes.

---

## 0. Bottom line

1. **M1's direction survives. Its framing does not.** Search alone does fail on multi-item classes even with 20× the budget: query-only CR@200 is decision 25%, cross 20%, preference 42% (A7). But the binding constraint in every result so far is **k = 10 items**, which nobody has measured and which equals only ~170–230 tokens in BrainBench. At **K = 50**, cards plus entity-tagged evidence ranked by the query reach goal 92%, option 77% and decision 57%. At the same K, cards + slots reach 52%, 37% and 36% (A7). The architecture is being tuned to a placeholder.
2. **The standard is dominated by its most debatable item.** Allowing one missing item lifts cards + slots on decision from 15.5% to 69.5% and on goal from 42% to 93.5%. With perfect slots, decision goes from 19.8% to 84.6% (A1). Human assessors agree on binary relevance only ~0.36–0.48 overlap (κ 0.31–0.44) ([Variations in Relevance Judgments](https://arxiv.org/html/2502.20937v2)). A pass/fail on "every generator-chosen item" therefore measures label idiosyncrasy as much as retrieval.
3. **BrainBench is tilted toward structure in exactly the ways that support M1.** It is hard for search and easy for structure, and neither in a realistic way:
   - **Free entity tags:** gold tags sit on 100% of required free-text items, and 49–80% of them are *implicit* (no alias appears in the text), so the generator does coreference for free.
   - **Free keyed facts:** 31–67% of the required items in complex classes are keyed facts (goals, strategies, rules, plans, suppliers) that in real life would need free-text extraction.
   - **Cloned templates:** 27–58% of required free-text items have a near-duplicate that differs only in the entity name.
   - **Shared aliases:** queries name entities with aliases from the same list a scribe would write (A2, A3, A8, A9).
4. **Structure does not escape the p^m arithmetic. It moves it to write time.** Under realistic extraction misses (implicit mentions missed), the entity-neighbourhood gain at K = 50 roughly halves: goal 92 → 55–67 (A10). Aggregation over 10 extracted decisions needs about 99% extraction recall per item. **Extraction and coreference recall are the real bottleneck, and no SLO is set for them.**
5. **The write gate's "complete or queue" design invites fabrication and rubber-stamping.**
   - Forced fields fabricate: required-field schemas made 10 of 13 models fabricate 100% of the time, and open models fabricated 60–100% even when an escape value was offered ([PhantomFill](https://arxiv.org/pdf/2607.20492)).
   - Reviewers habituate: approval rose 14.5 pp with exposure ([Habituation at the Gate](https://arxiv.org/pdf/2606.22721)).
   - Extraction alone loses information: extraction-only stores lost 16–22 pp against verbatim chunks ([Fidelity Before Structure](https://arxiv.org/pdf/2601.00821)).
   - Keep the deterministic always-run pipeline, but make it **non-blocking, span-grounded and abstention-first**.

**Verdicts**

| Item | Verdict | Required change |
|---|---|---|
| M1 | Keep-with-changes (reframe) | Budget in tokens; use a two-stage recall set and reader; state the write-time p^m explicitly |
| U1 | Keep-with-changes | Non-blocking; span-grounded; nullable fields; capped digest instead of a per-item queue |
| U2 | **Rethink** | Deterministic alias and header propagation first; filtered question generation only where it wins on non-generator vocabulary |
| U2a | Keep (cheap), de-prioritise | Merge into the ADR-009 mention-linking rule |
| U2b | Keep-with-changes | Entity-level, time-scoped, decaying aliases with a regression guard |
| ADR-012 | Keep-with-changes | Drop strict mode; treat scope as the unit for context and long reads, not a ranking feature |
| ADR-013 | Keep-with-changes | Answer-level metric with tolerance; extraction-recall SLO; completeness receipts; run H17 on local models |
| ADR-017 | Keep-with-changes | Default to single-item classes only; spend on a set-aware stage |
| ADR-020 | Keep-with-changes | Field-weighted origin; per-ACL-group stand-ins; test against noisy real origin data |
| Standard (§8) | Keep-with-changes | CR at a token-budgeted K over consensus "vital" items; answer-validity calibration; 2-call session recall |

---

## 1. New evidence from re-analysis (A1–A10)

### A1. All-or-nothing vs one-miss tolerance (3 seeds, pickled batch 2 rows)

CR@10 under four scoring rules: all required items; all but one; at least 80% of items; and mean item recall.

| Arm | Class | All required | Tolerate 1 miss | ≥80% items | Item recall |
|---|---|---|---|---|---|
| query-only | decision | 0.2 | 6.0 | 6.0 | 30.8 |
| query-only | goal | 11.6 | 47.8 | 45.6 | 50.7 |
| cards + static slots | decision | 15.5 | **69.5** | 69.5 | 74.0 |
| cards + static slots | option | 16.1 | **78.8** | 78.8 | 69.0 |
| cards + static slots | goal | 42.2 | **93.5** | 91.0 | 79.9 |
| cards + static slots | cross | 4.6 | 27.8 | 27.8 | 50.7 |
| cards + static slots | pref | 9.8 | 33.8 | 22.4 | 27.4 |
| oracle: every keyed fact pinned | decision | 19.8 | **84.6** | 84.6 | 79.6 |
| oracle: every keyed fact pinned | goal | 48.4 | **97.9** | 96.5 | 84.9 |

**Reading.** On decision, option and goal, the gap between today and 90% is mostly **the last item**. Whether that item is truly required decides whether the architecture is 70 pp short or 5–20 pp short. Example:

> "should we sell 5/9 Vireo Drive?" requires valuation, loan, **rent**, strategy and the meeting decision.

Is rent required to answer, or merely helpful? The generator says required. A human might not.

### A2. Substitutability and template clones (seed 1)

- Required keyed-fact heads that some accessible note quotes at the **same current value**: decision 75%, option 73%, goal 62%, pref 83%, cross 64%.
- Required free-text items with a near-duplicate (token Jaccard ≥ 0.5): decision 50%, option 58%, goal 53%, pref 32%, cross 27%. **96% of these near-duplicate pairs (2,068 of 2,160) have a different entity set** (`da_a2b.py`): they are the same template about a different entity. Example:

  > "Hot water system at 3 Marram failed — PM has two replacement quotes, $1,900 and $2,600."

  has clones at Mallee Close and 66 Ibis Place with identical wording and figures.
- **Consequence:** BrainBench's hardest negatives can be told apart *only* by entity identity, which is exactly what entity cards and entity linking exploit. Real corpora do not clone emails across 14 properties.

### A3. Corpus scale and "just read it" feasibility (seed 1)

- Live corpus: 10,107 items, about **96k tokens in total** (mean ~10 tokens per item; ~12 with origin text).
- Scope groups: 4–29k tokens.
- Oracle entity neighbourhoods (all visible items tagged with a required entity), median: decision 2.7k tokens, option 1.0k, goal 0.4k, pref 7.2k, cross 17.9k. Each contains 100% of required items.
- **Consequence:** in BrainBench, the owner's whole visible corpus fits in one long-context call. "k = 10" is ~170 tokens of context (A7). The benchmark cannot test long-context or recursive-LM alternatives fairly, and it inflates the apparent need to squeeze context into 10 items. Real items are 20–50× longer, so real neighbourhoods are tens to hundreds of thousands of tokens. That is still within reach of long-context or RLM reading for one entity or scope.

### A4. Crediting organic substitutes (seed 1)

The scorer credits an entity card as covering the facts it lists. It does not credit a note that quotes the same **current** value. Crediting such notes symmetrically changes CR@10 as follows:

- query-only: decision 0.0 → 0.6, option 3.1 → 6.6, pref 2.9 → 5.4; item recall +4 to +9 pp;
- cards + slots: ≤0.7 pp.

**Verdict on my own objection: mostly fails.** The asymmetry is real but small, and should be fixed for fairness. It does not rescue search.

### A5. Equal *token* budget instead of equal item count (seed 1)

| Class | cards + slots @10 | query-only @10 | query-only at the same token budget (~16–23 items) |
|---|---|---|---|
| decision | 17.9 | 0.0 | 0.0 |
| option | 17.1 | 3.1 | 5.8 |
| goal | 40.6 | 12.5 | 14.2 |
| current | 97.7 | 70.5 | 78.2 |
| temporal | 40.9 | 64.4 | **73.7** |
| multimodal | 76.4 | 85.3 | **88.4** |

**Verdict on my own objection ("cards win by packing many facts into one item"): fails.** Cards win at an equal token budget too. The N5 router remains necessary for temporal and multimodal.

### A6. "Structure for free text" at k = 10 (seed 1)

Arm: pin the cards, then pin the top 4 free-text items tagged with the linked entities (ranked by query score), then fill by search.

| Arm | decision | option | goal | pref | cross |
|---|---|---|---|---|---|
| cards (≤3) + query | 8.0 | 17.8 | 42.4 | 8.9 | 1.4 |
| + entity evidence E=4, clean tags | 9.9 | 19.0 | 43.8 | 10.7 | 1.4 |
| + entity evidence, 60% tags dropped and 30% spurious | 8.3 | 19.0 | 44.1 | 9.6 | 0.4 |
| oracle linker + entity evidence | 23.5 | 24.0 | 48.6 | 14.3 | 17.0 |

**Prediction for the board:** N8 ("link free-text evidence at ingest") will **fail its <5 pp kill criterion at k = 10**, but for the wrong reason. At k = 10 there is no room left once the cards are pinned. See A7.

### A7. The ceiling for a generous recall set (seed 1; CR@K, with mean tokens at K)

| Arm | K | decision | option | goal | pref | cross | tokens |
|---|---|---|---|---|---|---|---|
| query-only | 10 / 50 / 100 / 200 | 2.5 / 15.7 / 20.7 / **25.3** | 15.1 / 32.2 / 39.5 / 50.4 | 31.9 / 49.3 / 55.9 / 70.1 | 2.9 / 16.8 / 28.6 / 41.8 | 1.1 / 4.7 / 9.4 / **19.9** | 166 / 736 / 1,415 / 2,697 |
| cards + slots | 10 / 50 / 100 | 17.9 / 35.8 / 43.8 | 17.1 / 37.2 / 43.4 | 40.6 / 52.4 / 56.9 | 8.9 / 24.6 / 31.8 | 5.8 / 22.5 / 34.1 | 222 / 784 / 1,459 |
| cards (oracle linker) | 10 / 50 / 100 | 22.5 / 42.6 / 51.5 | 22.1 / 38.8 / 45.0 | 47.2 / 55.9 / 60.4 | 13.6 / 31.4 / 38.2 | 16.7 / 34.1 / 47.5 | 202 / 762 / 1,437 |
| **cards + slots + entity neighbourhood** (lexical linker, gold tags) | 10 / 50 / 100 | 24.4 / **56.8** / 63.9 | 19.8 / **76.7** / 81.4 | 43.8 / **92.4** / 92.4 | 4.6 / **45.7** / 53.6 | 2.5 / 18.8 / 37.7 | 221 / 735 / 1,378 |

**Readings.**
- Query-only stays far below 90% on every complex class even at K = 200, so M1's direction holds.
- Structure plus a generous K changes the picture: goal reaches 92% at K = 50 with a *lexical* linker.
- **Cross-domain fails in every arm.** Its required items are concept-linked ("can we swing both purchases?" needs the offset balance and the buffer goal, neither of which is named), so neither entity structure nor search finds them. Cross-domain needs a different mechanism (§3, alternatives).

### A8. Where the "structure" in BrainBench comes from (seed 1)

Share of required items in complex classes by origin:

| Class | Connector-plausible keyed facts (valuation, loan, rent, revenue, count …) | Keyed facts that would need free-text extraction in real life (goal, plan, strategy, rule, status, supplier, program …) | Free text |
|---|---|---|---|
| decision | 39% | 31% | 30% |
| option | 19% | 40% | 41% |
| goal | 8% | **67%** | 25% |
| pref | 0% | 32% | 68% |
| cross | 25% | 18% | 57% |

The headline card gains (goal +31.9 pp, option +14.5 pp) rest on keyed facts that the generator wrote in perfectly extracted, keyed form. In production these come through path B or U1 extraction, at ~44% success on messy prose (MemStrata, cited in ADR-011).

### A9. Would E10 (the scribe) pass by construction? (seed 1)

Share of required free-text items that share a content word with the request:
- raw text only: decision 66%, option 70%, goal 30%, pref 39%, cross 81%;
- raw text plus the aliases of the item's entities: decision 81%, option **96%**, goal **66%**, pref 58%, cross 96%.

Queries draw entity names from the same alias list. A scribe given the entity registry "wins" without learning anything about the person. **E10 as specified cannot tell a working scribe from a copied alias list.**

### A10. Entity-neighbourhood assembly under realistic extraction error (seed 1)

Share of (required free-text item, entity) tags that are **implicit**, meaning the item names no alias of the entity: decision 49%, option 58%, goal 80%, pref 58%, cross 48%. Errors were simulated where real extractors make them: on implicit mentions.

| Tag quality | decision @10/50/100 | option | goal | pref | cross |
|---|---|---|---|---|---|
| Gold tags | 26 / 57 / 64 | 21 / 79 / 81 | 47 / **92** / 92 | 5 / 46 / 54 | 3 / 20 / 38 |
| 50% of implicit tags missed, 5% of explicit missed, 5% spurious | 23 / 47 / 55 | 21 / 62 / 65 | 36 / **67** / 71 | 5 / 42 / 50 | 2 / 21 / 37 |
| 80% / 10% / 10% | 23 / 44 / 51 | 21 / 55 / 60 | 32 / **60** / 64 | 3 / 33 / 41 | 1 / 21 / 38 |
| String-match extractor (every implicit tag missed) | 26 / 44 / 50 | 21 / 50 / 53 | 32 / **55** / 58 | 5 / 34 / 41 | 3 / 24 / 43 |

For scale: GPT-4o resolves long-context mentions at 81.9% and 7–8B open models at 51–53% ([IdentifyMe](https://arxiv.org/html/2411.07466v2)). With local-first hosting (ADR-016), the realistic band is somewhere between the 50% and 80% rows. Even there, neighbourhood assembly beats cards + slots at K = 50 by +8 to +25 pp on decision, option, goal and preference. **The direction is robust. The size depends on coreference quality.**

---

## 2. M1: "search alone cannot reach 90% on multi-item tasks; assemble structurally"

### 2.1 Strongest case against (steelmanned)

1. **The p^m premise conflates budget with method.** The p in p^m is per-item recall *at k = 10 items*. In BrainBench, k = 10 is ~170–230 tokens, far below the charter's own definition of k ("the largest context the assistants use well before answer quality drops"). No answer-quality experiment has set k. At K = 50 (still only ~750 synthetic tokens), structured assembly reaches 92% on goal (A7). The honest form of M1 is: *at a fixed, small item budget, search alone cannot reach 90%.* That is a statement about the budget as much as about search.
2. **The empirical support is generator-assisted.**
   - Cards cover keyed facts that the generator gave in clean form, including the 31–67% that would need extraction in real life (A8).
   - Entity linking succeeds partly because hard negatives are entity-name clones (A2).
   - The oracle analyses use gold tags that already resolve the 49–80% implicit mentions (A10).
3. **Structure does not escape p^m; it relocates it.** If a required item reaches the context only through a write-time extraction with recall r, then a structurally assembled task passes with roughly Π(r_i × p_link). For a 10-decision aggregation that is r^10, so 90% needs r ≈ 0.99. M1 presents structure as "near-certain", but certainty here means **extraction recall ≥ 98–99% per item type**. Nothing in the design measures that or sets it as a target.
4. **Independence is not the right model either way.** Batch 2 found ρ = 0.66 for temporal and −0.05 to −0.09 under pinned prefixes. The two-term model (N9) is better, but it still treats "required" as fixed, and A1 shows the fixed label set dominates the outcome.

### 2.2 Failure scenarios in real use

- A new topic arrives that has no keyed facts yet ("thinking about a food truck"). Cards are empty, and M1's structural half contributes nothing. That is the cold-start problem for every new idea, which is also when the owner most needs context.
- The linker misses the entity ("the Ballarat one", "Mum's place", "the bottleneck"). Then **every** structural path fails at once: correlated failure, the worst case for p^m.
- Extraction mis-keys a strategy ("next purchases interstate" read as a constraint on the current property). The card then confidently serves a wrong "current strategy", and pinning gives it priority over the verbatim note.

### 2.3 Alternatives and when each wins

| Alternative | Wins when | Evidence | Risk |
|---|---|---|---|
| **Two-stage: high-recall set (K = 50–100, token-budgeted) passed to a reader or selector** | Reader models handle 10–30k tokens of mostly relevant context | A7: goal 92% at K = 50. Emergence on LongMemEval: retrieving whole sessions plus light chain of thought gave 83–86%, above the 82% that GPT-4o reached given only the relevant turns ([Emergence](https://www.emergence.ai/blog/og2q4h3p2zcmkxjdvj099ogqm21a4a)) | Context rot: every one of 18 models was worse on full (~113k) than focused (~300-token) LongMemEval prompts ([Chroma](https://trychroma.com/research/context-rot)). Distractors cost 5–9 pp ([UDCG](https://arxiv.org/pdf/2510.21440)) |
| **Agentic iterative retrieval in the client** (2–3 calls with a gap check) | Cross-domain and concept-linked needs; strong client models | IRCoT up to +21 pp (doc 01). Token budget explained 80% of BrowseComp variance (doc 01) | Client-dependent (charter principle 3); latency |
| **Long-context read of a scoped entity neighbourhood** | Neighbourhood ≤ ~50–100k real tokens | A3: oracle neighbourhoods hold 100% of required items in 0.4–18k synthetic tokens | Context rot; cost per request |
| **Recursive LM over the neighbourhood** | Exhaustive or aggregation tasks | BrowseComp-Plus (1k docs): RLM(GPT-5) 91.3; RLM(Qwen3-Coder-480B) only 44.7 ([RLM](https://arxiv.org/html/2512.24601v1)) | With local models (ADR-016), roughly half the quality; heavy cost tail ($0.99 ± $1.22) |
| **Late interaction (ColBERT) first stage** | Compositional, multi-attribute requests | LIMIT R@100: ColBERT 54.8 vs ≤18.9 for single-vector (doc 01) | Storage; does not address concept-linked needs |

### 2.4 Verdict: Keep-with-changes (reframe)

Restate M1 as follows:
> At a fixed context budget, multi-item classes need (a) structural candidate generation (cards **and** entity-tagged evidence) **plus** (b) a recall budget measured in tokens and set by answer quality. Structural certainty is bounded by extraction and coreference recall, so it needs its own SLO: implicit-mention tag recall ≥95% and typed-record recall ≥98% for decision and commitment types, on human-written text.

### 2.5 Decisive test and kill criterion

**DT-M1, "structure on real text".** Build ~300 tasks from human-written (or other-model-paraphrased) items:
- no template clones;
- realistic item length (100–500 tokens);
- implicit references kept.

Structure must be **model-extracted** by the local pipeline: no gold tags and no gifted keyed facts. Arms:
1. query-only;
2. cards + slots;
3. cards + slots + entity neighbourhood;
4. long-context read of the linked neighbourhood;
5. 2-call client agent.

Measure each at K ∈ {10, 50, 100} and at token budgets of {4k, 16k, 32k}.

**Kill the structure-first thesis** if arm (3) beats arm (1) by less than 5 pp CR at the knee budget on the complex classes, *or* if arm (4) or (5) beats arm (3) by 10 pp or more at equal cost.

---

## 3. U1: the write gate (nothing is filed until its card is complete)

### 3.1 Strongest case against

1. **"Complete" forces invention.** With required-field schemas, models fabricated in 40 of 40 trials (GPT-5.5) and 10 of 13 models did so 100% of the time, while the same models said "no evidence" 98% of the time in prose. With an escape value, nine open models still fabricated 60–100% of the time ([PhantomFill](https://arxiv.org/pdf/2607.20492); single-group preprint, COLM workshop). ADR-016 is local-first, so the open-model numbers are the relevant ones. A completeness validator rewards the extractor for filling slots.
2. **Extraction-centred stores lose information.** With the pipeline held fixed:
   - typed artifacts scored 28.0% vs 43.9% for verbatim chunks on LoCoMo, and 45.4% vs 67.4% on LongMemEval-S;
   - 78.8% of the missing keywords were facts the extractor never flagged (implicit attributes, negations, emotional states);
   - a union store (artifacts plus chunks) only *matched* chunks ([Fidelity Before Structure](https://arxiv.org/pdf/2601.00821)).

   Across 12 systems, "each layer of abstraction progressively discards information", and the authors recommend extracting conservatively and avoiding aggressive write-time filtering ([Agent-native memory](https://arxiv.org/pdf/2606.24775)). The ADRs keep episodes (append-only), which helps, but the gate still treats the card as the thing that matters.
3. **The confirmation queue will become a rubber stamp.**
   - Approval rates rose from 27.9% to 42.4% with reviewer experience, and inline comments fell 22% ([Habituation at the Gate](https://arxiv.org/pdf/2606.22721)).
   - Secondary report of Anthropic data: about 97% of permission prompts were approved, and the human block rate fell from ~17% to ~5% after 50+ prompts ([summary](https://yage.ai/share/claude-auto-mode-approval-illusion-en-20260808.html); not primary).

   The owner runs three businesses and has three kids. A "one-tap confirmation" on every decision and strategy record will be approved unread within weeks, and the system will then report "owner-confirmed" for records nobody checked.
4. **Errors compound.** P(card correct) ≈ P(classify) × P(link) × P(extract) × P(coreference). With today's figures (linker recall 31–45% lexical; coreference 52–82%; typed extraction ~44%), most cards built from free text will be incomplete or wrong.
5. **Cost and latency on every write.** Classify, link, extract, scribe (U2) and checker (U4) add up to 3–5 model calls per write. Even "lol ok" in a group chat pays the full price. In BrainBench, 52% of items are chats and logs.
6. **The gate conflicts with principle 1 (domain-agnostic).** Per-type mandatory schemas mean any new domain, field or connector version sends everything to `needs_completion` until someone writes a schema.

### 3.2 Failure scenarios

- **A member logs a workout in the app.** The schema requires a goal link, and the member has none, so the write is queued. The member sees nothing. Repeated across members, this produces a silent backlog.
- **An email offers "5.59% to keep Marram Dr".** The extractor must fill `rate` and `property`, but the property alias is ambiguous across two Marram addresses. It guesses, the validator passes, and a wrong keyed rate enters the card that `current_state` reads with 98% "certainty".
- **The queue reaches 400 items.** The owner bulk-approves. Every poisoned candidate the ADR-014 quarantine held is now "human-approved trusted memory", which defeats the write-poisoning constraint.

### 3.3 Alternatives

- **Write-ahead, structure-behind (recommended).**
  - Every write is accepted immediately as a verbatim episode, searchable within seconds.
  - Extraction runs asynchronously as non-blocking enrichment.
  - The pipeline is still deterministic and mandatory, as U1 rightly wants; what changes is that it never blocks the write.
- **Abstention-first, span-grounded schemas.**
  - Every field is nullable with an explicit `not_stated`.
  - Every non-null value must carry a verbatim source span that a deterministic validator string-matches. No span, no value.
  - Google's LangExtract pattern of source-grounded spans is a ready template ([LangExtract](https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/)).
- **Triage depth.** A cheap classifier picks the processing tier: discard-index, light (entities only) or full. Full extraction is reserved for items with decision, commitment or value cues.
- **Exception digest, not a per-item queue.**
  - Humans see only *conflicts that would change a keyed value already used by a card*, batched weekly and capped (e.g., ≤15 per week).
  - Auto-accepted items get random blind audits, a sampled maker–checker setup in place of per-item approvals.
  - Approval-streak monitoring catches habituation.
- **Lazy structure.** Extract on first read of an entity neighbourhood and cache the result. LazyGraphRAG cut indexing to ~0.1% of GraphRAG's cost (doc 01).

### 3.4 Verdict: Keep-with-changes

Keep "every write passes one deterministic pipeline" and drop "blocked until complete". Replace completeness validation with **grounding validation** (span present, value tokens appear in the span, entity exists). Replace per-item confirmation with a capped exception digest plus sampled audits.

### 3.5 Decisive tests

- **DT-U1a, fabrication suite.** 300 items with deliberately missing fields, run on the local extractor with three schemas: required; nullable; nullable + span-required.
  - *Kill the required-field gate* if fabrication is ≥5% under it.
  - *Accept span-grounded* if fabrication is ≤1% and true-field recall stays within 3 pp of the required schema.
- **DT-U1b, E9 at the right budget with realistic tags.** Replicate A10 with *model-extracted* tags on human-written text, at K ∈ {10, 50, 100}.
  - *Kill U1's typed-extraction step* if, at the knee budget, neighbourhood assembly with model tags gains less than 5 pp over cards + slots on decision, option and goal.
  - Report implicit-mention tag recall. If it is below 80%, invest in coreference before more schema work.
- **DT-U1c, queue simulation.** Replay a simulated month of real write volume and count queue items per day.
  - *Kill per-item confirmation* if it exceeds 10 per day. Measure habituation with seeded bad records: catch rate in week 1 vs week 4.

---

## 4. U2: double entry (fixed entry plus the scribe's searchable entry)

### 4.1 Strongest case against

1. **At write time the scribe does not know the future requester's words.** It knows the author's words, which are already in the raw text, plus guesses. The personal vocabulary that matters ("the bottleneck") emerges later, in requests, and only U2b sees it. At write time, U2 reduces to generic synonyms plus registered aliases plus generated questions:
   - generic synonyms added noise ([AIUI](https://aiui.tech/blog/recall-experiments-week-one/), cited in ADR-011);
   - the deterministic part (aliases in a contextual header) needs no LLM.
2. **This is doc2query / HyPE under another name, and the unfiltered form is noisy.**
   - Doc2Query--: filtering out ~70% of generated queries raised RR@10 by 16% and shrank the index by 33% ([Doc2Query--](https://arxiv.org/pdf/2301.03266)).
   - HyPE raises precision and recall on QA corpora but has worse noise sensitivity (21.0 vs 13.8) and is flat on MS MARCO ([HyPE](https://arxiv.org/pdf/2607.29402)).
   - ADR-011's "up to 5 questions" has no filter.
3. **Hallucinated aliases are invisible and self-reinforcing.**
   - Searchable entries are "never shown as content", so a wrong alias ("the Ballarat one" attached to the wrong property) misroutes silently.
   - U2b then reinforces the error whenever the user picks among the wrong results.
4. **E10 would pass by construction** (A9). Queries use entity aliases drawn from the same list.
5. **Index bloat and IDF drift.** Five questions per item over 10k items means 50k generic strings ("what is the status of the project?"). That causes hubness, and with per-partition BM25 statistics (ADR-006) small partitions get noisy IDF.

### 4.2 Alternatives

- **Deterministic alias and header propagation (cheap 80%).**
  - Copy the registered names and aliases of each item's linked entities, plus its folder, thread and title, into a contextual header field.
  - No LLM; auditable; this is the BrainBench equivalent of A9's alias gain.
  - Anthropic's contextual retrieval (−49% failures, doc 01) is the LLM version of the same idea.
- **Learned sparse retrieval (SPLADE family).** Frozen expansion vocabulary, no per-write LLM, and no cross-partition statistics if the model is frozen. It covers the synonym job.
- **Filtered question generation** (Doc2Query-- style). Generate, score against the item with the local reranker, keep the top ~30%, and only for item types where the dev set shows a gain.
- **Query-log expansion at entity level** (U2b, below). Click-query expansion gave +16–31% NDCG ([NeuDEF](https://arxiv.org/pdf/1908.02938)), but items with no clicks get no benefit, which argues for attaching words to entities rather than items.

### 4.3 Verdict: Rethink

Build deterministic alias and header propagation now; it is cheap and auditable. Keep the LLM scribe off until it beats alias propagation on held-out personal vocabulary. Make every scribe-derived match visible in receipts ("matched via scribe alias X").

### 4.4 Decisive test

**DT-U2, held-out vocabulary E10.** Generate the requester vocabulary *independently* of the scribe: nicknames and descriptors written by a different model or by humans, never placed in the entity registry. Arms:
1. raw;
2. raw + deterministic alias header;
3. raw + header + unfiltered scribe;
4. raw + header + filtered scribe.

Report CR at the knee K and precision@K.

*Kill the LLM scribe* if arm 3 or 4 beats arm 2 by less than 3 pp, or lowers precision@K by more than 3 pp.

---

## 5. U2a: no values in the searchable entry

### 5.1 Case against

U2a solves a problem the searchable entry barely has. The stale-value risk lives in **raw text** (notes quoting old values in 34% of probes), and ADR-009's mention linking and forwarding already handle that. A scribe that writes no values cannot go stale, but neither can one whose value mentions go through the same mention linking. Two further problems:
- **Lost search keys.** Values are often the user's handle on a request: "the $750k cap", "the 5.39% refix", "the 12% margin rule". Stripping them from the scribe entry removes keys.
- **Validator false positives.** The identifier whitelist only covers registered aliases, so "the 5.39% offer" is stripped.

### 5.2 Verdict: Keep (cheap), de-prioritise E10b

Fold the rule into one policy for all indexed text: *every value token in any indexed text is a linked mention (`fact_refs`) and is forwarded or annotated at serve time.* Expect E10b to show "no difference". Spend its budget on DT-U2 instead.

---

## 6. U2b: self-healing vocabulary

### 6.1 Case against

1. **Corrections are rare and noisy.** People rephrase or give up rather than say "no, I meant X". When they do pick something, the pick can be wrong, and the wrong item then permanently absorbs the words.
2. **Vocabulary drifts.** "The bottleneck" meant the produce supplier in March and the coach roster in November. Item-level appends carry no validity time, so old words keep pulling old items.
3. **Rich get richer.** Frequently retrieved items accumulate words and crowd out cold items, the known cold-start problem of click expansion (NeuDEF).
4. **Poisoning surface.** Inside one ACL group, a shared space (U6) lets one partner's habits rewrite another's retrieval. Appending query text to documents is the mechanism behind click spam.
5. **A weak kill criterion.** "No improvement after 100 corrections" ignores regressions on *other* requests.

### 6.2 Alternative and verdict: Keep-with-changes

Learn **entity-level aliases** from corrections: (`phrase` → `entity`, principal, `valid_from`, confidence, decay).
- The linker consumes them, so one correction fixes the cards and the neighbourhood for every item about that entity.
- They are auditable in one table and can be time-scoped.
- Item-level appends are only for items with no entity.

### 6.3 Decisive test

**DT-U2b.** Replay a simulated year with referent drift: 20% of nicknames change referent mid-year, and 10% of user picks are wrong.
- *Kill item-level appends* if entity-level aliases achieve ≥ the gain with ≤ half the regressions on non-corrected requests.
- *Kill U2b entirely* if net CR change, counting regressions, is below +2 pp after 100 corrections.

---

## 7. ADR-012: scope handling

### 7.1 Case against

1. **The measured benefit is tiny and the ceiling is optimistic.** Declared boost gave +0.8 pp. In BrainBench the declared scope is the task author's primary scope, essentially an oracle, so +0.8 pp is an *upper bound*. The trail is drawn 70% from the declared scope and 30% from the required scope groups, so it is also derived from the gold (already acknowledged).
2. **Real declared scope is noisy.** People ask about the school holiday while the gym dashboard is open. The boost limits the harm, but every point of the 0.8 pp is at risk.
3. **Strict mode is a footgun with no measured benefit:** hard 45.5 vs boost 45.4.
4. **The real value of scope is elsewhere.** It is the unit of access, of the scope index (H19), of static slots and, potentially, of long-context reading.

### 7.2 Verdict: Keep-with-changes

- Remove `scope_mode = strict` until a measured ≥2 pp win.
- Log real UI-declared scope against the scope of the items the user actually used, to get the true accuracy of declared scope.
- Recast scope as **a context provider**: the scope index, slots and a long-read unit when the scoped partition is small enough.

### 7.3 Decisive test

**DT-012.** On pilot logs: measure declared-scope accuracy (does the declared scope contain the used items?) and boost vs none on real requests.
- *Kill the scope boost* if it is ≤0 pp, or if declared-scope accuracy is below 70%.

---

## 8. ADR-013: aggregation routed to computation

### 8.1 Case against

1. **Exact-set recall over extracted records inherits p^m at write time.** "Every decision we made about the cafe" is complete only if each decision was extracted as a typed record. At 90% extraction recall, a 10-decision set passes 0.9^10 ≈ 35% of the time. SQL is exact; the table is not.
2. **The router fails silently.** Cue words are ambiguous ("all good?", "every time I…"). The Adaptive-RAG complexity classifier was 54.5% accurate (doc 01).
3. **Natural language to structured spec is text-to-SQL in a smaller form.** Enterprise text-to-SQL reached ~21% at launch on Spider 2.0 against 73% on BIRD ([Spider 2.0](https://www.aiwiki.ai/wiki/spider_2), secondary). A constrained spec over a small schema is easier, but entity resolution in filters ("cafe suppliers") is the same linker problem.
4. **The RLM fallback degrades sharply with local models:** OOLONG-Pairs F1 58.0 for GPT-5 vs 23.1 for Qwen3-Coder-480B ([RLM](https://arxiv.org/html/2512.24601v1)).
5. **Exact-set recall is the wrong metric for totals.** Missing an immaterial $3 receipt fails the task. Double-counting a superseded invoice can pass the recall test with a wrong total. Precision and value tolerance matter as much as recall.

### 8.2 Alternatives

- **Completeness receipts.** Return "N candidate items in scope mention X; M used; K unclassified (listed)", so the assistant and user can see the gap.
- **Recall-oriented harvest.** A union of the entity neighbourhood, BM25/dense at large depth and typed records, followed by an exhaustive local map/classify step over the harvested set, as an async "report" mode.

### 8.3 Verdict: Keep-with-changes

- **Metric:** list tasks use exact-set recall **and** precision; total tasks use value within tolerance plus correct supersession.
- **New SLO:** typed-record extraction recall ≥98% for decision and commitment types on the dev set, otherwise answers return `complete = false`.
- **Receipts:** mandatory.
- **H17:** run with the local LLM, not GPT-5.

### 8.4 Decisive test

**DT-013.** Add an aggregation class to BrainBench where the records must be *extracted* from free-text meetings, emails and chats by the local pipeline.
- *Kill "SQL first"* if exact-set recall is below 80% because of extraction misses. In that case harvest + map becomes primary and SQL serves only connector-keyed data.
- Router recall on aggregation below 95% → route on explicit request only ("report mode").

---

## 9. ADR-017: reranker stage

### 9.1 Case against

1. **It helps the classes that are already fine.** The +3.7 pp gains land on current, temporal and multimodal. Decision and cross have pool ceilings of 8% and 3%, so no reranker moves them.
2. **Pointwise cross-encoders are the wrong inductive bias for set completion.** They cannot know that the LVR rule matters *because* a purchase is under consideration. Set-level need calls for listwise or setwise LLM selection or a gap check.
3. **The evidence does not transfer.** It comes from 10–12-token records truncated at 384 tokens. bge-reranker "helps nothing on these short records". Real items are long and noisy, so the model ranking may flip.
4. **In a two-stage design its job changes.** It should filter K = 100 down to ~30 for the reader, not to 10.

### 9.2 Verdict: Keep-with-changes

- Default the stage to single-item classes (current, temporal, multimodal).
- Multi-item classes bypass it until a set-aware stage (listwise LLM over top 50 with a "what is missing?" prompt, I6) is tested.
- Re-run E8b on long, realistic items before choosing the model size.

### 9.3 Decisive test

**DT-017.** On realistic-length items, for multi-item classes: cross-encoder to 30 vs listwise LLM selection to 30 vs no rerank, scored on CR@30 and answer quality.
- *Kill the cross-encoder for multi-item classes* if it is within 1 pp of no rerank.

---

## 10. ADR-020: media origin context

### 10.1 Case against

1. **The size of the gain is generator-set.** 261 of 387 sets have identifying words only in origin fields.
2. **Real origin metadata is noisy:**
   - filenames like `IMG-20260412-WA0003.jpg`;
   - a "Camera" folder;
   - forwarded images that lose the sender;
   - group chats interleaving threads, so ±2 adjacent messages are often "lol" or about a different topic.

   Adjacent text can act as a **distractor**, mis-associating photos.
3. **"Take the intersection ACL" loses recall.** A photo the gym partner can see, also shared in the owner's family chat, gets a stand-in restricted to the intersection. The partner then cannot find a photo they are allowed to see. Stand-ins need one version per ACL group, the same rule as cards.

### 10.2 Verdict: Keep-with-changes

- Index origin text as a **separate weighted field** (BM25F-style weights fitted per source) rather than concatenated.
- Choose adjacency by reply threading or quoted-reply metadata where it exists, else by a small "refers to the image?" classifier.
- Build **one stand-in per ACL group**.
- Add a noisy-origin stratum to the eval.

### 10.3 Decisive test

**DT-020.** Real sample of 200 photos and clips from the owner's devices and chats, with requests written blind.
- *Accept* if origin context gives ≥3 pp with no rise in wrong-item-in-top-1 (distractor) rate.
- If adjacency text raises the wrong-item rate by more than 2 pp, restrict it to threaded replies.

---

## 11. The standard itself (charter §8)

### 11.1 Is "≥90% of tasks with every required item in top-k, per class" the right target? Case against

1. **"Required" is not well defined, so the target has no stable referent.**
   - Assessor overlap on binary relevance is ~0.36–0.48, with κ 0.31–0.44 ([Variations in Relevance Judgments](https://arxiv.org/html/2502.20937v2)).
   - Human TAR-assessor agreement is ~67% (Grossman & Cormack, cited in ADR-018).
   - If two raters agree on each item with probability 0.85, they produce the same 5-item set only 0.85^5 ≈ 44% of the time.
   - Scored against a second rater, a human would not reach 90%. Certifying a machine at 90% against one rater's set partly certifies that rater's idiosyncrasy.
   - A1 shows the pass rate swings by 50+ pp on exactly one item per task.
2. **It is item-level, not information-level.** It penalises returning the email recap instead of the meeting note that holds the same decision. A4 shows the effect is small in BrainBench, which has little genuine redundancy. Real corpora repeat decisions across meeting notes, recaps and chats.
3. **It ignores what the user experiences.**
   - Answer quality depends on distractors (5–9 pp; UDCG), position, and whether the model abstains when context is insufficient.
   - Models answer wrongly rather than abstaining on insufficient context, and selective generation using a sufficiency signal improves accuracy-when-answering by 2–10% ([Sufficient Context](https://arxiv.org/abs/2411.06037)).
   - Relevance-label metrics correlate weakly with downstream RAG performance. Per-document downstream utility improved Kendall τ by 0.17–0.49 ([eRAG](https://arxiv.org/abs/2404.13781)).
4. **k counts items, not tokens.** In BrainBench, k = 10 is ~170–230 tokens, and real items are 20–50× longer. The "assistant's usable context" premise has never been measured.
5. **It assumes a single shot.** ADR-001 puts reasoning in the client, and the client can call again. Doc 01 §4 itself says to "measure recall over the final context the client assembles across a multi-call session", but §8 does not.
6. **It is stricter than the field it borrows from.** E-discovery certifies an *item-level* recall estimate over a population, with error margins, under reasonableness and proportionality. Rio Tinto sets no recall threshold and says it is "inappropriate to hold TAR to a higher standard than keywords or manual review" ([Rio Tinto v. Vale](https://www.steptoe.com/a/web/3oS1yD7SDvnQ7xm4REpsZf/3ZFuHj/20150303-rio-tinto-opinion-re-computer-assisted-review.pdf)). The charter's standard, per-task completeness on 90% of tasks in every class, has no precedent there.

### 11.2 Steelman for keeping CR@k

- It is **model-independent**, which the client-agnostic principle (3) requires. An answer-level metric would tie certification to one reader model.
- It is cheap, decomposable by stage, and hard to game with a judge.
- Answer metrics are noisy per topic: automatic nugget evaluation reached run-level τ ≈ 0.89 but only 0.36–0.54 per topic ([TREC RAG nuggets](https://arxiv.org/html/2504.15068v1)).

So: **keep CR as the engineering metric, but fix what it measures and prove that it predicts answers.**

### 11.3 Does BrainBench measure anything real? Could we be optimising for our own generator?

**Unrealistically hard for search:**
- Requests are written to avoid lexical overlap.
- Hard negatives are entity-name clones (A2).
- All-or-nothing scoring applies to 4–7 generator-chosen items.
- k is ~200 tokens.

**Unrealistically easy for structure:**
- Gold entity tags resolve 49–80% implicit mentions (A10).
- 31–67% of the complex-class items are pre-keyed (A8).
- Query aliases come from the registry (A9).
- Declared scope and trail are derived from the gold.
- Items are 10–12 tokens, so cards hold whole entity histories.

**Overfit risk already present:**
- The temporal regex was written while looking at the gold.
- The router uses generator media words.
- α was tuned on seed 1 of the same templates; seeds 2–3 share templates.
- Hand slots were written knowing the templates.

**Net:** BrainBench is a good **plumbing and ablation rig** (access, staleness, leakage, router mechanics), and its *directions* agree with external evidence. It cannot set magnitudes or certify the architectural thesis. Every ADR marked "Accepted" on BrainBench magnitudes should carry "pending DT-M1 on realistic text".

### 11.4 Verdict: Keep-with-changes. Proposed revision of §8

1. **Primary:** CR@K_tok over **consensus vital items**.
   - K_tok is a token budget per class, set by the answer-quality knee (DT-S3).
   - An item is vital when ≥2 of 3 raters mark it required. Items marked by one rater are "helpful" and reported as graded recall.
   - Pass = all vital items present, or an information-equivalent substitute present.
2. **Ceiling report:** human-as-system CR (rater B's set scored against the consensus) per class. The target is min(90%, human ceiling − 2 pp) until DT-S1 reports.
3. **Validity:** CR pass must predict answer pass (DT-S2) before CR is used to accept architecture.
4. **Session recall:** CR of the context after ≤2 brain calls by a reference client, reported next to single-call CR. The brain's completeness receipt (§12, I-5) is what makes the second call targeted.
5. **Secondary:** a distractor-aware utility (UDCG-style), and abstention correctness given a sufficiency signal.

### 11.5 Decisive tests for the standard

- **DT-S1, inter-annotator set agreement.** 100 tasks × 3 raters (owner + 2), required sets labelled from the source side.
  - Report set-level Jaccard and human-as-system CR.
  - *Kill single-annotator gold* if human-as-system CR is below 85%; then move to consensus vital/helpful labels.
- **DT-S2, necessity and validity.** For 300 tasks, two different reader models answer with:
  - (a) the full required set;
  - (b) each item ablated in turn;
  - (c) the system's top-K.

  Nugget-grade the answers.
  - *Relabel* as "helpful" any "required" item whose ablation leaves answer quality unchanged in ≥70% of runs.
  - *Kill CR as the acceptance metric* if CR-pass predicts answer-pass with AUC below 0.70.
- **DT-S3, token-budget knee.** Answer quality vs context of 2k / 4k / 8k / 16k / 32k tokens, built from the system's assembly with realistic distractors, per class, with the actual client models. K_tok is the budget beyond which quality gains are under 1 pp.
- **DT-S4, generator overfit.** Re-score every accepted ADR effect on BrainBench-H (human or other-model text, no clones, model-extracted structure).
  - *Flag* any ADR whose effect shrinks by more than half or flips.

---

## 12. Innovations that came out of the attack

**I-1. A two-budget standard with a recall set and a reader.**
- Separate the brain's **recall budget** (K = 50–100 items or a token budget, certified with CR) from the **reader's working set**, which a reader, listwise selector or client agent chooses from the recall set.
- Evidence: A7 (goal 52 → 92%, option 37 → 77%, decision 36 → 57% vs cards + slots at K = 50); session-level retrieval on LongMemEval (Emergence 83–86%).
- This changes the arithmetic of M1: p at K = 50 is far higher than p at k = 10, and the reader resolves the rest.
- Test: DT-M1 plus DT-S3.

**I-2. Entity-neighbourhood assembly: evidence by entity, ranked by query.**
- Order: cards → all permitted free-text items tagged with the linked entities, ranked by query score → search fills the rest.
- The structural recall path for free text that ADR-011 was looking for, and it needs no scribe.
- Robust to random tag noise (A6). Sensitive to missed implicit mentions (A10), so **implicit-mention tag recall becomes the headline extraction SLO** (target ≥95% on human text).
- Kill: <5 pp over cards + slots at the knee budget with model-extracted tags.

**I-3. A span-grounded, abstention-first write contract (the inverse of "complete").**
- Every extracted value must cite a verbatim span checked by a deterministic validator.
- Every field may be `not_stated`.
- Completeness is never a validation criterion.
- This turns U1 from a fabrication incentive into a fabrication filter, and gives U4's checker something deterministic to check.
- Kill (DT-U1a): fabrication above 1% with spans, or recall loss above 3 pp.

**I-4. Consensus vital/helpful labels with a human-as-system ceiling.**
- Certify against what at least two humans agree is vital.
- Publish the human-vs-human CR as the realistic ceiling.
- Stops the project from spending architecture on the most debatable item in each set (A1).

**I-5. Completeness receipts and a sufficiency signal.**
With every response, the brain returns:
- which linked entities and slots were filled;
- which linked entities have more evidence beyond K (with counts);
- unclassified candidates for aggregation;
- an autorater-style sufficiency estimate. Google's sufficient-context autorater reached ≥93% accuracy against 115 human labels ([Google Research](https://research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/)).

This turns single-shot misses into a cheap, *targeted* second call by the client, lets the assistant abstain correctly, and keeps the brain a service, not an agent. Test: 2-call session CR vs 1-call CR, and abstention correctness, on cross-domain, the class that fails in every structural arm.

---

## 13. Priority order for the experiment queue (proposed)

1. **DT-S1 and DT-S3.** Cheap and human-light. They decide what to measure and at what budget. Everything else depends on them.
2. **DT-M1 / DT-U1b on BrainBench-H** with model-extracted tags, at K ∈ {10, 50, 100}. Decides structure-first vs read-or-agent.
3. **DT-U1a fabrication suite** on the local extractor. Days, not weeks; decides the gate's validation rule.
4. **DT-S2 necessity/validity.** Decides whether CR may accept architecture.
5. **DT-U2 held-out vocabulary**, then DT-013 (extracted aggregation), DT-017, DT-020, DT-U2b, DT-012.

## 14. Corrections to existing docs implied by this review

- **Doc 06, M1:** add "write-time p^m" and "budget-dependence". N8 is predicted to be killed at k = 10 and to succeed at K ≥ 50; test both.
- **ADR-018:** the scorer should credit an information-equivalent current-value item the same way it credits cards (A4), or stop crediting cards for covering facts. Add set-level inter-rater agreement and the human-as-system ceiling to the report format.
- **ADR-011:** E10 must use held-out vocabulary (A9), and E9 must report results at multiple K with model-extracted, implicit-heavy tags (A10).
- **ADR-012:** state that BrainBench's declared scope is near-oracle, so +0.8 pp is an upper bound.
- **ADR-010 / ADR-013:** add the extraction-recall and coreference SLOs as acceptance checks.

## Sources (external, beyond docs 00/01/06 and the ADRs)

- Joren et al., *Sufficient Context*, ICLR 2025: https://arxiv.org/abs/2411.06037 ; Google Research blog: https://research.google/blog/deeper-insights-into-retrieval-augmented-generation-the-role-of-sufficient-context/
- Salemi & Zamani, *eRAG*: https://arxiv.org/abs/2404.13781
- *Redefining Retrieval Evaluation in the Era of LLMs* (UDCG): https://arxiv.org/pdf/2510.21440
- Pradeep et al., *The Great Nugget Recall* (TREC 2024 RAG): https://arxiv.org/html/2504.15068v1
- *Variations in Relevance Judgments and the Shelf Life of Test Collections*: https://arxiv.org/html/2502.20937v2
- Gospodinov et al., *Doc2Query--*: https://arxiv.org/pdf/2301.03266
- *HyPE: Hypothetical Prompt Embeddings*: https://arxiv.org/pdf/2607.29402
- Yin et al., *Neural Document Expansion with User Feedback*: https://arxiv.org/pdf/1908.02938
- *PhantomFill* (single-group preprint; COLM 2026 workshop per author): https://arxiv.org/pdf/2607.20492 ; summary: https://hackernoon.com/a-language-model-can-be-honest-in-prose-and-still-fabricate-in-json
- *Habituation at the Gate*: https://arxiv.org/pdf/2606.22721
- Anthropic approval data (secondary report, not primary): https://yage.ai/share/claude-auto-mode-approval-illusion-en-20260808.html
- *Fidelity Before Structure*: https://arxiv.org/pdf/2601.00821
- *Are We Ready For An Agent-Native Memory System?*: https://arxiv.org/pdf/2606.24775
- Chroma, *Context Rot*: https://trychroma.com/research/context-rot
- Zhang et al., *Recursive Language Models*: https://arxiv.org/html/2512.24601v1
- *IdentifyMe* mention-resolution benchmark: https://arxiv.org/html/2411.07466v2
- Spider 2.0 summary (secondary): https://www.aiwiki.ai/wiki/spider_2
- *Rio Tinto v. Vale* (S.D.N.Y. 2015) opinion: https://www.steptoe.com/a/web/3oS1yD7SDvnQ7xm4REpsZf/3ZFuHj/20150303-rio-tinto-opinion-re-computer-assisted-review.pdf
- Emergence AI, LongMemEval results: https://www.emergence.ai/blog/og2q4h3p2zcmkxjdvj099ogqm21a4a
- Google, LangExtract: https://developers.googleblog.com/introducing-langextract-a-gemini-powered-information-extraction-library/
- Karpathy LLM-wiki pattern (alternative considered; use as an index, never as evidence, given H5): https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an
