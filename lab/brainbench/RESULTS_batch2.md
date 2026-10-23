# BrainBench v0.2 — batch 2 results (E8, E6, N4, M1, N5, H11-lite, H13-lite, I2 kill test)

Run: 2026-10-23/24 · Author: Claude (engineer) · Re-run: `python run_batch2.py` (add `--split-llm` on hosts with <8 GB RAM, which runs the LLM in a separate worker process; stages `gen, embed, e8a, e8b, e8c, e8d, e8e, e6, n4, h13, h11, i2, report`; every stage checkpoints per seed to `results_v02/<stage>.pkl`, and every model call is cached in `cache_v02/`, so an interrupted run resumes without recomputing).
Generated tables with every arm and every paired test: `results_v02/tables.md` (also `summary.json`). Batch 1 (`run_all.py`, `data/`, `results/`, `RESULTS.md`) is untouched.

**Read this first.** These are sandbox numbers on a synthetic world I generated (v0.2). Use them to compare approaches with each other, not as estimates of a real deployment. Unlike batch 1, the retrievers and rerankers here are real models, run with exact search. **Every rate is a mean over distinct required sets.** A need-set that appears with two phrasings counts once, with its mean score. Brackets are Wilson 95% intervals with n = number of distinct sets, pooled over 3 seeds. Paired comparisons are exact sign tests over distinct sets, with a 95% cluster-bootstrap CI on the difference.


## Headline findings

1. **Real embedders end batch 1's "dense hurts" artefact, but the bottleneck for indirect classes is unchanged.** The best first stage is weighted BM25 + bge-small-en-v1.5 (α = 0.2, tuned on seed 1, held out on seeds 2–3): **CR@10 44.6% [43–46] vs BM25 31.4% and batch-1 RRF(BM25, LSA) 28.1%** (+13.3 pp vs BM25, p=2e-149). Qwen3-Embedding-0.6B loses to bge-small on this short-record corpus (−3.3 pp, p=3e-9); its task-specific instruction adds +1.1 pp. Even so, decision and cross_domain CR@10 stay near 0. At depth 200, only 23% / 12% of those tasks have every required item in the pool.
2. **Structure, not search, moves the multi-item classes.** Code-compiled entity cards (≤3 pinned) give **+12.3 pp ALL (56.9%), +749 / −41 sets, p=2e-169**: goal +32, current +25, option +15, decision +8. Adding static slots lifts decision to 15.5% (+15.3). A two-regex router that drops the prefix for temporal and media requests beats every fixed arm (**57.8%**, +0.9 pp, p=9e-4). Standing packets lose 12.5 pp; even an oracle packet loses 10.7.
3. **Rerankers help only where the pool is complete.** Qwen3-Reranker-0.6B with its official template: **+3.7 pp CR (p=0.002), +6.4 pp item recall (p=3e-11)**; within complete pools +8.1 pp. mxbai-v2 +1.7 (ns); bge-reranker-v2-m3 ±0. **Zero effect on decision and cross** (pool ceilings 8% / 3%). **H12 contradicted:** the scope-templated instruction *costs* 4.7 pp (p=0.006) on Qwen3 and 11.6 pp on mxbai.
4. **Small-LLM decomposition and gap-check do not pay.** With Qwen3-1.7B: decomposition +1.5 pp item recall (ns), gap-check +0.3 (ns, 1.98 calls per request, almost never says "nothing missing"). A deterministic facet decomposer gives +5.5 pp item recall (p=1e-11) and +3.7 CR@20, but 0 CR@10. All are dwarfed by the cards + slots prefix (+17 to +29 pp) and add nothing on top of it. **I6 killed at this model size; H8 only weakly supported (item recall).**
5. **The linker's ceiling is large, but recall-oriented linkers do not reach it.** An oracle linker adds +12.6 pp (decision) and +14.3 pp (cross). Embedding and LLM linkers raise entity recall (74 → 83%) but halve precision, so CR is flat or falls (−4.7 pp with 5 cards). **Precision of pinning is the lever.**
6. **M1 holds in its refined form, and the binding term is now free-text evidence.** Under query-only, heterogeneous classes follow p^m within 0–2 pp. Homogeneous temporal need-sets beat it by 22 pp (ρ=0.66). With pinned prefixes, mixed classes fall 6–10 pp *below* p^m (ρ<0) because structure finds the facts and search misses the evidence. Even with *every* required fact pinned (oracle), decision CR@10 is only 19.8%: search finds 14–35% of the required free-text items (meeting decisions, quotes, feedback, preferences).
7. **Replicated with real models:** I8 origin context (+21 to +30 pp on media, no harm), never hard-filter on inferred scope (N7: −4.2 pp), declared scope small but positive (+0.9 pp), mention forwarding (+2.1 pp). **New:** model-written cards held a stale value in 80–87% of checks vs 0% for code-compiled cards (I2 survives its kill test), and a single-vector image model (SigLIP2) adds nothing over text twins for text-bearing images.

**Design consequence.** The context-assembly layer should be: (a) weighted BM25 + small dense first stage; (b) a class router choosing the prefix; (c) code-compiled cards and slots for facts; (d) **ingest-time links from free-text evidence to entities and keys** (new N8), so decisions, quotes and feedback become structural lookups too; (e) a cross-encoder reranker only on the search remainder. Query-side LLM loops are not worth their latency at small model sizes.

## Part 1 — BrainBench v0.2 (validity fixes)

**What changed versus v0** (`bb/world2.py`, `bb/tasks2.py`; v0 is unchanged):

| threat in batch 1 | v0 | v0.2 |
|---|---|---|
| Too few distinct required sets | 34–54 per complex class | **129–162 per class per seed** (387–486 pooled over 3 seeds); current_state 554, temporal 402–424 |
| One seed, fixed names | one world | 3 seeds; each seed redraws property and street names, holdings, members, project sites, tenders, values, dates and document wording |
| Templated wording | one template per need, few phrasings | 3–8 phrasing templates per need. About 30% of sets get a second phrasing, with a different requester where access allows. Random greetings, sign-offs, capitalisation and dropped "?" added. Paraphrased attribute labels in temporal requests. Four fact-rendering formats. Larger mention-template pools |
| Intervals too narrow | Wilson over tasks | Wilson over distinct sets. Paired sign tests and bootstrap CIs over sets |
| Scale | 8,038 items | **10,829–10,869 items per seed** (216 entities, 468 keyed facts, 1,231 fact versions, about 1,900 media stand-ins), still under the 10k+ multimodal target |

More entities give the multi-item classes their distinct need-sets: 14 properties, 14 holdings, 10 projects, 8 tenders, 42 gym members, 7 coaches with specialties and retention keys, 7 cafe supply categories, 6 gym-equipment categories, 4 dual-role staff, 6 capital commitments, 5 trips, 5 dining occasions, and 12 family places. The design is otherwise the same as v0: keyed facts with versions and supersession pointers, stale mentions, partitions and identities, cross-boundary shared entities, media with origin context, and canaries.

| class | distinct sets / seed | tasks / seed | required-set sizes (pooled) |
|---|---|---|---|
| decision_support | 162 | 202–218 | 3:15, 4:237, 5:283, 6:35, 7:58 |
| option_analysis | 129 | 163–170 | 3:187, 4:303, 5–9:9 |
| current_state | 554 | 623–642 | 1:1633, 2:156, 3:102 |
| temporal_change | 402–424 | 473–503 | 2:861, 3:98, 4:233, 5:25, 6:239 |
| goal_tracking | 144–146 | 175–185 | 2:71, 3:281, 4:165, 6–10:23 |
| preference_recommendation | 140 | 173–178 | 1:12, 2:313, 3:183, 4–7:18 |
| cross_domain | 138 | 175–180 | 3:14, 4:313, 5:200, 6–7:8 (all span ≥2 scope groups) |
| multimodal | 129 | 145–150 | 1:296, 2:125, 3:20 |

Lexical difficulty, seed 1: share of required items with no token overlap with the request, and share of tasks with at least one such item. decision 26% / 71%, option 19% / 58%, goal 31% / 63%, pref 60% / 78%, cross 31% / 87%, current 14% / 16%, temporal 1% / 1%, multimodal 0% / 0%. That makes v0.2 a little less adversarial than v0 on decision support (v0: 43% / 84%). Of 2,537 task queries in seed 1, 2,179 are distinct strings.

Per-seed stability is good. The ALL CR@10 spread across seeds is at most 2 pp for every arm (for example, query-only 44.1 / 44.1 / 45.8; cards 56.4 / 56.6 / 57.8). Small differences between arms are therefore not seed artefacts.

## Part 2 — E8: real dense retrieval and reranking

### E8a — first stage (all 6,516 tasks / 5,411 distinct sets, 3 seeds, exact search)

Setup: same store as batch 1 (keyed upsert, access pre-filter, regex temporal router, forward-to-head). BM25 statistics are computed over the requester's visible set. Embeddings cover title + text + origin context. Queries use each model's official instruction. Weighted fusion: min-max normalised BM25 × α + dense × (1 − α), with α tuned on seed 1 only (bge-small 0.2, Qwen3 0.3). Seeds 2–3 are held out.

CR@10 % [Wilson over distinct sets]:

| retriever | decision | option | current | temporal | goal | pref | cross | multimodal | **ALL** | item recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|
| BM25 | 0.0 | 1.8 | 45.1 | 47.2 | 11.5 | 4.3 | 1.7 | 73.6 | 31.4 [30–33] | 41.9 |
| LSA-256 (batch-1 proxy) | 0.7 | 1.4 | 43.0 | 31.0 | 7.9 | 2.5 | 0.0 | 57.1 | 25.3 [24–27] | 36.1 |
| RRF(BM25, LSA) (batch-1 default) | 0.2 | 0.4 | 45.2 | 38.2 | 6.8 | 2.0 | 0.8 | 65.2 | 28.1 [27–29] | 38.9 |
| bge-small-en-v1.5 (dense) | 0.4 | 2.5 | 68.6 | 61.4 | 9.2 | 3.3 | 0.0 | 81.4 | 42.1 [41–43] | 54.1 |
| Qwen3-Embedding-0.6B (dense, official instruction) | 0.2 | 4.8 | 64.1 | 55.0 | 11.1 | 3.1 | 1.7 | 69.9 | 38.8 [37–40] | 51.6 |
| Qwen3-Embedding-0.6B, task-specific instruction | 0.2 | 5.4 | 65.3 | 57.1 | 12.2 | 3.1 | 1.9 | 71.2 | 39.9 [39–41] | 53.0 |
| RRF(BM25, bge-small) | 0.4 | 2.3 | 65.3 | 59.7 | 13.5 | 3.8 | 1.1 | 80.7 | 41.1 [40–42] | 55.0 |
| RRF(BM25, Qwen3) | 0.2 | 3.4 | 62.6 | 58.2 | 13.9 | 3.8 | 2.2 | 75.2 | 39.6 [38–41] | 53.1 |
| **weighted(BM25, bge-small), α=0.2** | 0.2 | 2.5 | 72.4 | 65.3 | 11.6 | 3.6 | 0.8 | 85.1 | **44.6 [43–46]** | **58.0** |
| weighted(BM25, Qwen3), α=0.3 | 0.2 | 4.5 | 66.5 | 62.1 | 12.2 | 3.3 | 2.3 | 77.3 | 41.8 [40–43] | 55.5 |
| *n distinct sets* | 486 | 387 | 1662 | 1236 | 434 | 420 | 414 | 387 | 5411 | |

Paired tests:
- Every real embedder beats BM25. bge-small: +10.8 pp [9.6, 11.9], +935/−305 sets. Weighted bge hybrid: +13.3 pp [12.2, 14.3], p=2e-149.
- **LSA was a misleading proxy.** It scores −6.0 pp against BM25, and batch 1's RRF(BM25, LSA) default scores −3.3 pp. Batch 1's "dense hurts" pattern was LSA, not dense retrieval.
- **Qwen3-Embedding-0.6B loses to bge-small overall** (−3.3 pp [−4.4, −2.4], p=3e-9). It loses on current (−4.4), temporal (−6.4) and multimodal (−11.5), wins on cross_domain (+1.7 pp, p=0.004), and is directionally better on option and goal. The likely cause is that short, terse items (fact records, captions, "IMG close-up") suit a small symmetric model. Qwen3 is better on long, indirect requests.
- The task-specific Qwen3 instruction beats the generic one: +1.1 pp CR [0.5, 1.6], p=6e-5; +1.3 pp item recall, p=1e-9. The instruction matters, but it does not close the gap to bge-small.
- **Hybrid > dense.** Weighted(BM25, Qwen3) vs Qwen3 alone: +3.0 pp [2.3, 3.8], p=3e-14. On held-out seeds 2–3, the tuned weighted fusion beats RRF: +1.8 pp [1.0, 2.6], p=2e-6. α generalised across seeds, and RRF with equal weights over-weights BM25 here.
- Exact-search cost per query over about 11k items (BM25 + dense matmul, embeddings cached): 0.6–2.3 ms on 2 vCPU. Exact search is not a bottleneck at this scale.

Depth diagnostic for the best first stage (item recall / CR at depth d), showing where candidate generation fails:

| class | d=10 | d=20 | d=50 | d=100 | d=200 |
|---|---|---|---|---|---|
| decision | 31 / 0 | 42 / 2 | 56 / 11 | 64 / 18 | 70 / 23 |
| option | 41 / 2 | 58 / 10 | 72 / 28 | 79 / 39 | 83 / 49 |
| goal | 50 / 12 | 61 / 17 | 72 / 30 | 82 / 51 | 89 / 68 |
| pref | 17 / 4 | 25 / 7 | 34 / 14 | 44 / 25 | 55 / 42 |
| cross | 25 / 1 | 34 / 1 | 47 / 3 | 58 / 6 | 64 / 12 |
| current | 75 / 72 | 83 / 82 | 89 / 88 | 93 / 93 | 97 / 97 |
| temporal | 74 / 65 | 87 / 81 | 92 / 88 | 94 / 91 | 95 / 92 |
| multimodal | 88 / 85 | 90 / 89 | 96 / 94 | 99 / 98 | 100 / 99 |

Even at depth 200, real embeddings find all required items for only 23% of decision, 12% of cross and 42% of preference tasks. **N6 holds with real models.** For the indirect classes, the missing items are not in the candidate pool.

### E8b — rerankers on the top-50 of the best hybrid (stratified distinct sets: 40 / 15 / 10 per class for seeds 1 / 2 / 3 → 65 per class, 519 sets)

Official templates throughout. Qwen3-Reranker uses its chat frame with `<Instruct>/<Query>/<Document>` and an empty think block, scored as P(yes). mxbai-v2 uses the mxbai_rerank package's v2 prompt, scored as logit(1) − logit(0). bge-reranker-v2-m3 uses its classification logit. Documents are truncated to 384 tokens.

| reranker | decision | option | current | temporal | goal | pref | cross | multimodal | **ALL CR@10** | item recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|
| none (weighted BM25 + bge-small) | 0.0 | 1.5 | 72.3 | 64.6 | 12.3 | 3.1 | 0.0 | 86.2 | 30.1 [26–34] | 51.1 |
| bge-reranker-v2-m3 | 0.0 | 3.1 | 67.7 | 61.5 | 12.3 | 6.2 | 0.0 | 87.7 | 29.9 [26–34] | 51.8 |
| mxbai-rerank-base-v2 | 0.0 | 1.5 | 75.4 | 72.3 | 12.3 | 6.2 | 0.0 | 86.2 | 31.8 [28–36] | 53.4 |
| **Qwen3-Reranker-0.6B** | 0.0 | **9.2** | **76.9** | **72.3** | **15.4** | 6.2 | 0.0 | **89.2** | **33.7 [30–38]** | **57.5** |
| *pool ceiling: CR@50 of the candidates* | 8 | 31 | 86 | 91 | 29 | 22 | 3 | 92 | | |

(ALL is lower than in E8a because the subsample weights the 8 classes equally.)

Paired vs no reranker:
- **Qwen3-Reranker: +3.7 pp CR [1.5, 5.8], +27 / −8 sets, p=0.002. Item recall +6.4 pp [4.3, 8.4], p=3e-11.** Within sets whose top-50 pool already contains every required item (n=235), CR@10 rises from 66.4 to 74.5 (p=0.002).
- mxbai-v2: +1.7 CR (p=0.12), +2.3 item recall (p=0.06).
- bge-reranker-v2-m3: −0.2 (ns). It helps nothing on these short records.
- **No reranker moves decision or cross_domain**: the pool ceiling is 8% and 3%. N6 confirmed with real models.

**H12, scope-templated instruction vs generic (seed 1, 40 sets per class): contradicted.** Qwen3-Reranker with the scope instruction scores −4.7 pp CR [−7.8, −1.6], +6 / −21 sets, p=0.006; item recall −5.4 pp, p=2e-4. The loss falls on current (−17.5) and temporal (−10). Small gains on pref (+0 to +5) and option are ns. The same instruction on mxbai-v2 is catastrophic: −11.6 pp, p=9e-9. My instruction ("retrieve every note, fact, … needed … even if they do not repeat the request's words") made the rerankers favour loosely related items over the exact record. A narrower instruction might help on the indirect classes. On this evidence, ship the generic instruction.

### E8c — batch-1 arms re-run with the best real first stage (weighted BM25 + bge-small, all tasks, 3 seeds, k=10)

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | **ALL** | item recall |
|---|---|---|---|---|---|---|---|---|---|---|
| query-only | 0.2 | 2.5 | 72.4 | 65.3 | 11.6 | 3.6 | 0.8 | 85.1 | 44.6 [43–46] | 58.0 |
| query + mention→head forwarding | 0.5 | 7.4 | 78.5 | 63.4 | 16.0 | 5.8 | 1.1 | 80.9 | 46.7 [45–48] | 63.9 |
| packet(5) + query | 0.0 | 1.0 | 57.9 | 34.7 | 7.7 | 3.6 | 0.5 | 75.2 | 32.1 [31–33] | 48.2 |
| ORACLE packet(5) + query | 1.1 | 4.0 | 58.0 | 35.0 | 15.4 | 13.2 | 1.3 | 75.2 | 33.9 [33–35] | 52.8 |
| hand slot contract + query | 5.1 | 11.8 | 91.1 | 45.5 | 38.7 | 3.6 | 5.2 | 75.5 | 48.8 [48–50] | 70.0 |
| generic slots + query | 6.6 | 8.7 | 94.6 | 46.5 | 37.2 | 3.8 | 0.2 | 75.5 | 49.6 [48–51] | 69.9 |
| **entity cards (≤3) + query** | 8.2 | **16.9** | 97.4 | 64.6 | **43.5** | **10.0** | 1.2 | 83.9 | **56.9 [56–58]** | **75.0** |
| cards (≤3) + static slots + query | **15.5** | 16.1 | **97.8** | 42.9 | 42.2 | 9.8 | **4.6** | 74.9 | 52.2 [51–54] | 74.4 |
| declared scope: hard filter | 0.2 | 3.5 | 74.0 | 65.7 | 13.4 | 3.8 | 0.0 | 86.0 | 45.5 [44–47] | 58.6 |
| declared scope: boost | 0.2 | 3.2 | 73.9 | 65.5 | 13.4 | 3.8 | 0.0 | 86.0 | 45.4 [44–47] | 58.6 |
| query-inferred scope: hard | 0.2 | 2.7 | 64.0 | 60.4 | 10.4 | 3.3 | 0.7 | 79.3 | 40.4 [39–42] | 52.6 |
| query-inferred scope: boost | 0.2 | 2.5 | 71.6 | 64.6 | 10.6 | 3.3 | 0.7 | 79.8 | 43.8 [42–45] | 56.9 |

Paired vs query-only (sets better / worse; Δ pp [CI]; p):
- **Cards (≤3): +749 / −41, +12.3 [11.4, 13.2], p=2e-169.** They win on decision (+8.0), option (+14.5), current (+25.0), goal (+31.9) and pref (+6.4). Temporal is unchanged (−0.6, ns) and multimodal loses slightly (−1.3, p=0.02).
- Cards + static slots: +7.6 [6.5, 8.7] overall, and the best arm on decision (+15.3, +82 / −1) and cross (+3.7). The pinned static slots cost temporal −22.4 pp and multimodal −10.2 pp.
- Packets: −12.5 [−13.5, −11.6]. Even an oracle packet built from the test set loses −10.7 pp overall. It helps only pref (+9.6) and goal (+3.8).
- Mention forwarding: +2.1 [1.5, 2.6], p=2e-11, with large gains on current (+6.1) and option (+4.9) and losses on temporal (−1.9) and multimodal (−4.3).
- Declared scope: hard +0.9 [0.6, 1.2], boost +0.8 [0.5, 1.1], both p<1e-7. Inferred-from-query scope: hard −4.2 (+23 / −292), boost −0.9 (p=8e-9).
- With the batch-1 LSA retriever, the same arms score 7–17 pp lower (every arm p<1e-60). The ordering of arms is unchanged: cards > slots > query-only > packets.

H9 k-sweep (CR@k):

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only @10 / @20 / @30 | 0.2 / 2.1 / 6.4 | 2.5 / 10.1 / 19.0 | 72 / 82 / 85 | 65 / 81 / 85 | 12 / 17 / 20 | 4 / 7 / 11 | 0.8 / 1.1 / 1.7 | 85 / 89 / 91 | 44.6 / 52.8 / 56.3 |
| cards+slots @10 / @20 / @30 | 15.5 / 21.1 / 25.8 | 16.1 / 25.3 / 29.1 | 98 / 98 / 99 | 43 / 79 / 85 | 42 / 48 / 51 | 10 / 17 / 20 | 4.6 / 10.7 / 14.4 | 75 / 88 / 90 | 52.2 / 64.1 / 67.1 |

CR@10 by required-set size (cards + static slots): size 1 96.5 [96–97], 2 49.1, 3 47.3, 4 14.6 [13–17], 5 9.0, 6 12.1, 7 1.0, 8+ 0.0 (n=9 sets).

### I8 — origin context for media (all multimodal tasks, 387 distinct sets)

| index | BM25 | dense (Qwen3) | RRF | weighted |
|---|---|---|---|---|
| caption/OCR only | 52.5 | 52.3 | 55.7 | 55.3 |
| + origin context | **73.6** | **81.4** | **80.7** | **85.1** |
| paired gain, sets +/− | +21.2 pp, +90/−2 | +29.1 pp, +118/−0 | +25.1 pp, +107/−5 | +29.8 pp, +125/−4 (p=3e-32) |

On "needs an origin-only item" tasks (n=261 sets), weighted fusion goes from 37.4 to 80.7. On caption-sufficient tasks (n=126) there is no harm: dense +5.6 pp (+7/−0, p=0.016), weighted +2.0 (ns).

### N5 — class-conditional prefix with a two-regex router (new, cheap)

The router sends a request to query-only if the batch-1 temporal regex or a media-word regex fires, and to cards (≤3) + static slots otherwise.

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | **ALL** |
|---|---|---|---|---|---|---|---|---|---|
| cards (≤3) + query (best fixed) | 8.2 | 16.9 | 97.4 | 64.6 | 43.5 | 10.0 | 1.2 | 83.9 | 56.9 [56–58] |
| **router → query-only / cards+slots** | **15.5** | 14.5 | **97.8** | **65.3** | 42.2 | 9.8 | **4.6** | 83.1 | **57.8 [56–59]** |

Versus the best fixed arm: +0.9 pp [0.4, 1.4], +139 / −88 sets, p=9e-4. The router recovers decision +7.3 and cross +3.4 without the temporal −22 / multimodal −9 penalty, at a cost of option −2.5 (ns). Routing was correct for 95% of temporal and 93% of multimodal tasks; 8 of 628 decision tasks were mis-routed to query-only. **N5 supported.**

### Structural ceilings (oracle analyses)

Share of required items that are keyed facts (and so reachable by slots or cards): decision 70%, option 59%, goal 76%, cross 44%, pref 30%, current and temporal 100%, multimodal 0%.

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL | item recall |
|---|---|---|---|---|---|---|---|---|---|---|
| cards (≤3), lexical linker | 8.2 | 16.9 | 97.4 | 64.6 | 43.5 | 10.0 | 1.2 | 83.9 | 56.9 | 75.0 |
| cards (≤3), **oracle linker** | 20.8 | 21.2 | 100 | 65.0 | 48.4 | 14.3 | 15.5 | 84.1 | 61.1 | 81.6 |
| **every required keyed fact pinned** (perfect slot contract) | 19.8 | 21.1 | 100 | 100 | 48.4 | 15.1 | 16.3 | 85.1 | 69.2 | 85.8 |

Even with perfect structure, decision CR@10 stays near 20%, because search then has to find the free-text items (meeting decisions, emails, notes, quotes). Under perfect slots, search finds only 33% of decision free-text items (19% of tasks get all of them), 35% / 22% for option, 30% / 31% for goal, 14% / 14% for pref and 31% / 15% for cross. **The bottleneck has moved from facts to free-text evidence.**

## M1 — measured CR@10 vs the independence prediction

Per class, prediction = mean over tasks of p^m, with p = class item recall@10. "Item model" = Π over required items of each item's leave-one-task-out hit rate. ρ = intra-task correlation of item hits implied by the variance of the found count (beta-binomial).

| arm | class | measured | p_class^m | Π p_item | ρ |
|---|---|---|---|---|---|
| query-only | current | 72.9 | 71.8 | 71.0 | 0.41 |
| query-only | temporal | **65.7** | 43.1 | 51.7 | **0.66** |
| query-only | multimodal | 82.5 | 83.5 | 75.7 | 0.25 |
| query-only | decision / option / goal / cross | 0.2 / 2.6 / 12.4 / 0.9 | 0.6 / 4.3 / 12.0 / 0.3 | 0.2 / 3.3 / 9.0 / 0.7 | ≈0 |
| cards + static slots | decision | **15.0** | 24.3 | 22.1 | −0.06 |
| cards + static slots | option | **18.0** | 27.5 | 24.4 | −0.09 |
| cards + static slots | goal | **40.6** | 47.1 | 35.4 | −0.05 |
| cards + static slots | cross | 4.7 | 5.2 | 7.1 | −0.06 |
| cards + static slots | pref | 8.0 | 5.1 | 1.4 | 0.01 |
| cards + static slots | ALL | 50.1 | 49.4 | 48.9 | 0.17 |

**Where independence breaks:**
1. **Positive correlation: temporal (ρ=0.66) and current (ρ=0.41).** Versions of one key are near-duplicates, so they are found together. Measured CR is 22 pp above p^m. For homogeneous need-sets, p^m is too pessimistic.
2. **Negative correlation under pinned prefixes: decision, option, goal (ρ −0.05 to −0.09).** The prefix finds the fact half of the set with near-certainty, and search must find the free-text half. Item recall is bimodal by item type, so CR is 6–10 pp below p_class^m. For mixed need-sets, p^m with a class-average p is too optimistic. The right model is **CR ≈ (p_struct)^m_struct × (p_search)^m_search**.
3. For heterogeneous query-only classes, independence holds well (decision, option, goal, cross within 0–2 pp; ρ≈0).

The M1 thesis survives with the refinement above. It needs p ≈ 0.98+ per item *for each item type*, and today's binding term is p_search on free-text evidence (0.14–0.35 even when every fact is pinned).

## Part 3 — E6: decomposition and gap-check (H8, I6, N6)

### E6a — model-free arms (complex classes, 40 distinct sets per class × 3 seeds = 478 sets)

| arm | decision | option | goal | cross | **ALL CR@10** | item recall@10 | CR@20 |
|---|---|---|---|---|---|---|---|
| one-shot, weighted BM25 + bge-small (best hybrid) | 0.0 | 2.5 | 11.7 | 1.7 | 3.9 [2–6] | 36.3 | 7.4 |
| deterministic facet decomposition (≤4 sub-queries from linked entities' attribute labels + scope slot labels; RRF union) | 0.8 | 2.5 | 10.0 | 1.7 | 3.7 [2–6] | **41.9** | **11.1** |
| embedder swap: BM25 only | 0.0 | 1.7 | 13.3 | 2.5 | 4.2 | 31.3 | 7.1 |
| embedder swap: bge-small dense | 0.8 | 1.7 | 9.2 | 0.0 | 2.9 | 31.0 | 5.4 |
| embedder swap: Qwen3-Emb dense | 0.0 | 4.2 | 14.2 | 0.8 | 4.6 | 32.8 | 6.5 |
| embedder swap: weighted BM25 + Qwen3-Emb | 0.0 | 4.2 | 13.3 | 1.7 | 4.6 | 37.0 | 7.7 |
| embedder swap: batch-1 RRF(BM25, LSA) | 0.0 | 0.0 | 8.3 | 0.8 | 2.2 | 25.9 | 4.7 |
| **cards + static slots + one-shot** | **13.3** | **20.0** | **44.2** | **5.8** | **20.8 [17–25]** | **68.8** | 20.8 |
| cards + static slots + facets | 6.7 | 12.5 | 33.3 | 2.5 | 13.8 | 64.8 | 13.8 |

- **Facets vs one-shot:** CR@10 unchanged (+3 / −4 sets). Item recall@10 +5.5 pp [3.9, 7.2] (p=1e-11). CR@20 +3.7 pp [1.5, 5.9] (p=0.001); item recall@20 +6.8 pp.
- **Embedder swaps vs the best hybrid:** every swap is within ±1 pp CR@10 (all ns). On item recall, swaps cost −3.6 to −5.3 pp (Qwen3 dense, BM25, bge dense) or tie (weighted BM25 + Qwen3, +0.5 ns).
- **Facets inside the structural prefix hurt:** −7.0 pp CR (+1 / −35, p=1e-9). The sub-queries pull in more fact-like items that duplicate what the cards already cover, and push free-text evidence out of the remaining slots.
- The structural prefix dwarfs both: +16.9 pp CR (+85 / −4, p=8e-21).

### E6b — LLM decomposition and gap-check (seed 1, 12 distinct sets per complex class = 48 sets; Qwen3-1.7B, greedy, thinking off, few-shot prompts)

Decomposition: one call per request, ≤4 sub-queries, RRF union with the original query. Gap-check: show the LLM the top-8 retrieved items and ask what is missing (up to 3 queries per round, at most 2 rounds), then RRF-union the original query and all gap queries. Small n: read the item-recall column, not CR.

| arm | ALL CR@10 | **item recall@10** | CR@20 | LLM calls / request |
|---|---|---|---|---|
| one-shot (best hybrid) | 10.4 [5–22] | 35.7 | 10.4 | 0 |
| LLM decomposition (≤4, union) | 10.4 | 37.2 (+1.5, p=0.65) | 12.5 | 1 |
| deterministic facets | 10.4 | 39.0 (+3.3, p=0.18) | 16.7 | 0 |
| gap-check (≤2 rounds) | 10.4 | 36.0 (+0.3, p=0.65) | 14.6 | 1.98 |
| embedder swaps (bge dense / Qwen3 dense / BM25 / weighted BM25+Qwen3) | 4.2–8.3 | 27.0–32.7 (−3 to −9) | 4.2–12.5 | 0 |
| **cards + static slots + one-shot** | **27.1 [17–41]** | **64.8 (+29.2, p=7e-8)** | 27.1 | 0 |
| cards + slots + LLM decomposition | 25.0 | 64.3 | 25.0 | 1 |
| cards + slots + gap-check queries | 25.0 | 64.4 | 25.0 | 1.98 |
| cards + slots + facets | 22.9 | 62.4 | 22.9 | 0 |

Calls and behaviour: the decomposer produced 3.88 sub-queries on average and hit the cap of 4 in 92% of requests, the same over-generation the research reported. Gap-check almost never said NONE: 44 of 48 requests continued to round 2, for 1.98 calls and 5.2 gap queries per request. Gap queries often ask for things the store does not hold ("tenant's contact details", "metrics or KPIs for the safety goal"), or restate the request. Decomposition sub-queries often paraphrase the request ("Siobhan's current membership type" ×2). Neither reliably names the missing *kind* of evidence (the related-party policy, the meeting decision, the supply contract). Examples are in `results_v02/tables.md`.

**E6 conclusion:** with a small local LLM, decomposition and gap-check give at most +1.5 pp item recall (ns). Deterministic facets give +3.3 here and +5.5 pp (p=1e-11) on the larger E6a sample, which is better and needs no model. Embedder swaps lose 3–9 pp. The cards + slots prefix gives +29 pp, an order of magnitude more than any query-side method. None of the query-side methods adds anything on top of the prefix (all −2 to −4 pp, ns).

## Part 4 — N4 entity linkers (20 distinct sets per class × seeds 1–2 = 320 sets; LLM linker on seed 1 only, 6 sets per class = 48 sets)

Linkers: **lexical** (batch-1 alias regex + member self-reference); **embedding@k** (Qwen3-Embedding similarity between the request and an entity descriptor, which is name, kind, aliases and the entity card text, top-k accessible entities); **lexical + embedding@3**; **LLM-assisted** (Qwen3-1.7B picks up to 5 of the lexical ∪ embedding@15 candidates, few-shot). Assembly is held fixed: cards (≤3) + static slots + query, or cards (≤5) + query.

| linker | entity recall: decision | option | pref | cross | **ALL** | all required entities linked | precision | entities linked |
|---|---|---|---|---|---|---|---|---|
| lexical | 43 | 85 | 36 | 55 | 74 | 65% | **57%** | 1.5 |
| embedding@3 | 52 | 92 | 67 | 52 | 81 | 74% | 28% | 2.9 |
| embedding@5 | 53 | 95 | 71 | 55 | 83 | 75% | 20% | 4.7 |
| lexical + embedding@3 | 53 | 95 | 71 | 57 | 83 | 75% | 21% | 4.7 |
| *LLM subsample (seed 1, 48 sets):* lexical | 47 | 67 | 50 | 6 | 69 | 61% | 56% | 1.4 |
| LLM-assisted (from candidates@15) | 64 | 83 | 75 | 6 | 65 | 58% | 29% | 2.6 |
| lexical + LLM-assisted | 64 | 83 | 100 | 6 | 77 | 71% | 30% | 3.2 |
| candidates@15 (LLM ceiling) | 64 | 83 | 100 | 17 | 79 | 71% | 12% | 13.4 |

CR@10 at fixed assembly (cards ≤3 + static slots; 320 sets): lexical 38.8 [34–44], embedding@3 38.1, embedding@5 38.4, lexical+embedding 38.8. All Δ within ±0.6 pp, ns. With cards (≤5), no static slots: embedding@5 −4.7 pp (+3 / −18, p=0.002) and lexical+embedding −3.8 pp (p=0.01) vs lexical. On the LLM subsample, the LLM-assisted linker is −7.7 pp vs lexical (1 set worse, ns). It also drops entities the lexical linker gets right ("current" recall 50%).

**N4 verdict: the ceiling is real, but none of the linkers I built reaches it.** An oracle linker is worth +4.2 pp ALL (+12.6 decision, +14.3 cross; 259 / 5 sets, p=7e-70). The embedding and LLM linkers raise entity recall by 7–9 pp, yet CR does not move, because they buy recall with precision (57% → 20–28%). Every wrongly pinned card evicts a search slot. The cross_domain entities the embedding linker misses are abstract ones: "the property portfolio" and "offset account" for "can we afford X", and suppliers named only by category. **The linker needs to be precise on the right entity, not just high-recall.** Two fixes follow (N13): pin a card only above a calibrated similarity, and rank facts *within* linked cards so that only the needed facts are pinned (N12). Kill criterion for N4 as stated (<5 pp CR gain): **killed for these linkers** (gain ≤0), **not killed for the idea** (oracle ceiling +4.2 ALL, +12–14 pp on the target classes).

## H13-lite — index-time enrichment vs query-side expansion (multimodal, seed 1, 16 distinct sets; best first stage)

The LLM rewrites each request into 3 alternative queries ("how the file is captioned, which folder or album, who shared it"), RRF-unioned with the original.

| index | raw query | + LLM query expansion |
|---|---|---|
| caption / OCR only | 50.0 (item recall 59.4) | 50.0 (62.5) |
| + origin context (index-time enrichment) | **81.2 (87.5)** | 81.2 (87.5) |

Enrichment alone vs expansion alone: +31.2 pp (+5 / −0 sets, p=0.06 at n=16). Expansion adds 0 pp on either index. On the full multimodal set, I8 already showed enrichment at +21 to +30 pp (all p ≤ 2e-24). **H13 supported** for media: expansion cannot invent folder or album names it has never seen. That is exactly H13's rationale (the LLM does not know the private corpus).

## H11-lite — SigLIP2 image vectors vs text twins (synthetic text-bearing images)

Real photos are absent, so I rendered every OCR-bearing media item to a 448×448 PNG: the OCR text on a board or paper background, with random rotation, blur and noise. That covers whiteboards, menu boards, receipts and report pages (247–269 images per seed). Retrieval is restricted to these media items (within-media search). There are 124 tasks over 3 seeds whose targets all carry OCR text, giving 99 distinct sets. Photos of scenes (defects, family events, rooms) are excluded: pixels would be meaningless without real images.

| arm | CR@10 | item recall@10 |
|---|---|---|
| text twin, system hybrid (caption + OCR + origin) | 97.5 [92–99] | 98.0 |
| text twin, Qwen3 dense (caption + OCR + origin) | 91.4 [84–95] | 93.1 |
| text twin without OCR (caption + origin), Qwen3 dense | **98.5 [94–100]** | 98.8 |
| SigLIP2-base image vector only | 61.1 [51–70] | 62.9 |
| RRF(text twin without OCR, SigLIP2) | 78.8 | 79.8 |
| RRF(text twin with OCR, SigLIP2) | 82.3 | 81.9 |

SigLIP2 alone is −37.4 pp vs the text twin (+0 / −40 sets, p=2e-12). **Fusing SigLIP2 hurts:** −19.7 pp (p=5e-7) and −9.1 pp (p=0.01). Origin context, not OCR, carries these targets. Removing OCR from the text twin even raised dense recall (91.4 → 98.5): the OCR strings (prices, times) add noise for a dense model. **H11 (text twins capture most recall) is supported. The visual half (≥5 pp on text-bearing images) is contradicted for a single-vector SigLIP2-base.** This says nothing about real photos, charts or layout-heavy pages, or about multi-vector visual retrievers (ColPali-class), which remain untested. SigLIP2-base encodes about 1.6–2.0 images/s on host B in fp32.

## I2 kill test — LLM-written cards vs code-compiled cards (seed 1, 8 entities × 2 input orders, 30 key checks)

The LLM (Qwen3-1.7B) writes a "current facts" card from 3–24 dated notes about an entity. The scored checks are keyed facts where those notes quote both the current and a superseded value. Code-compiled cards come from keyed heads, so they can only state the current value.

| input order | checks | current only | stale only | both | neither | **stale value present** |
|---|---|---|---|---|---|---|
| random (as retrieved) | 15 | 6.7% | 6.7% | 80.0% | 6.7% | **86.7% [62–96]** |
| newest-first | 15 | 20.0% | 6.7% | 73.3% | 0% | **80.0% [55–93]** |
| code-compiled cards | – | 100% | 0% | 0% | 0% | **0% (by construction)** |

**I2 kill criterion ("model-written cards match the stale rate of code-compiled ones") is not met, by a wide margin: I2 survives.** Caveat: the small model often copied every dated note instead of resolving to a current value (see the examples in tables.md). A frontier model would do better, but the result shows the failure mode is real and the code path removes it entirely. This also extends H5: never let a model write the card a pipeline pins.

## Runtime and latency per component (useful for GPU sizing)

Two hosts, because the container restarted mid-run. **Host A:** Xeon @2.1 GHz, 2 vCPU, AVX-512 + AMX/AVX512-BF16; models in bf16. **Host B** (after the restart): Xeon @2.8 GHz, 2 vCPU, AVX-512 without BF16/AMX. On host B bf16 is emulated (about 4× slower than fp32), so rerankers ran in fp32. The 1.7B LLM stayed in bf16 because fp32 does not fit the ~6 GB cap with the indexes loaded. No GPU. Throughputs are measured over the uncached calls in this run (`cache_v02/timing.json`).

| component | host A (bf16, AMX) | host B (fp32 / emulated bf16) | notes |
|---|---|---|---|
| bge-small-en-v1.5 doc embedding | 177 docs/s (6 ms) | – | max 512 tokens; mean item ≈ 43 tokens |
| Qwen3-Embedding-0.6B doc embedding | 31 docs/s (32 ms) | – | 11k items ≈ 6 min; bf16 = fp32 quality (cos ≥ 0.998) |
| query embedding, bge-small / Qwen3 (batched) | 36 / 10–22 q/s | – | single query ≈ 0.1 s (Qwen3) |
| exact hybrid search over 11k items (BM25 + dense matmul) | 0.6–2.3 ms/query | – | exact search is not a bottleneck at 10k scale |
| bge-reranker-v2-m3 | 17.6 pairs/s | 9.6 pairs/s | top-50 ≈ 3–5 s/query |
| mxbai-rerank-base-v2 | 7.4 pairs/s | 3.8 pairs/s | top-50 ≈ 7–13 s/query |
| Qwen3-Reranker-0.6B (generic instruction) | 6.8 pairs/s | 2.9 pairs/s | top-50 ≈ 7–17 s/query; scope instruction ~30% slower (longer prompt) |
| Qwen3-1.7B generation (batch 8, greedy, 20–120 new tokens) | ≈ 31 tok/s aggregate; ≈ 2.5 s per request in batch | ≈ 0.5 tok/s; **≈ 150 s per request** in batch (emulated bf16, CPU shared with other jobs) | 158 uncached generations in this run took 6.7 h on host B |
| SigLIP2-base image encoding (fp32) | – | 1.6–2.0 img/s | text tower ≈ 0.1–0.3 s per query batch |

**What this means for the build.** A small local LLM in the retrieval loop is unaffordable on CPU (2.5–150 s per call) and, per E6, also not worth it. **GPU sizing, back of the envelope.** The only components that are slow on CPU are the cross-encoder rerankers (Qwen3-Reranker top-50 takes 7–17 s per query) and the LLM loop (2.5 s per call on host A, about 150 s on host B). INFERRED, not measured here: both should be roughly two orders of magnitude faster on a single L4 / A10-class GPU, putting a top-50 rerank at tens of milliseconds and a 1.7B call well under a second. Measure this in the GPU validation package before sizing. Embedding 10k items with Qwen3-0.6B takes about 6 min on 2 CPU cores; ingest-time embedding does not need a GPU at personal-brain scale. Exact search at 11k items costs ≤2.3 ms per query (OBSERVED). Linear extrapolation (INFERRED) suggests exact search stays practical well beyond the charter's 10k+ scale, so ANN indexing is an optimisation, not a requirement, at personal-brain scale.

## Hypothesis verdicts

| ID | verdict | key number (distinct sets, 3 seeds unless noted) |
|---|---|---|
| **H1** declared scope adds ≥10 pp on decision and goal | **Contradicted with real embedders** (no floor excuse left for goal) | decision CR +0.0, item recall +0.8; goal CR +1.7 (p=0.008), item recall +2.2. ALL +0.9 pp (p=8e-9) |
| **H2** boost beats hard filter on cross_domain | **Weakly supported, but both lose to no scope** | cross item recall: boost vs hard +1.4 pp (+19/−9, p=0.09); both below query-only (hard −5.8, boost −4.5 pp item recall); cross CR 0 in both |
| **H3** standing packets beat query-only at equal k | **Contradicted (stronger than batch 1)** | packet −12.5 pp [−13.5, −11.6]; even an oracle packet −10.7 pp |
| **H8** capped decomposition beats any embedder swap on decision support | **Weakly supported on item recall; neither moves CR** | E6a (478 sets): facets +5.5 pp item recall (p=1e-11), CR@10 +0.0, CR@20 +3.7 (p=0.001); every embedder swap −5 to +0.5 pp item recall, ±1 pp CR. LLM decomposition (48 sets) +1.5 pp item recall (ns). Both are dwarfed by structure (+17 to +29 pp) |
| **H11** text twins capture most multimodal recall; visual vectors add ≥5 pp on text-bearing images | **First half supported; visual half contradicted (single-vector SigLIP2, synthetic text images)** | text twin 97.5–98.5% vs SigLIP2 61.1%; fusion −9 to −20 pp. Real photos, charts and multi-vector models untested |
| **H12** scope-templated reranker instruction adds ≥2 pp | **Contradicted (kill criterion met: losses in classes)** | Qwen3-Reranker −4.7 pp CR [−7.8, −1.6], p=0.006; current −17.5; mxbai −11.6 pp (seed 1, 40 sets per class) |
| **H13** index-time enrichment beats query-side expansion | **Supported (media)** | enrichment +31 pp (16 sets, p=0.06; I8 full set +21 to +30 pp, p ≤ 2e-24); LLM expansion +0 pp on either index |
| **I1** slot contracts | **Supported vs packets; hand ≈ generic overall** | hand slots +4.2, generic +4.9 pp vs query-only; +16.7 / +17.5 pp vs packet. Hand wins cross (+5.2 vs 0.2) and option; generic wins current and decision |
| **I2** code-compiled entity cards | **Supported — strongest single arm; survives the kill test** | cards (≤3) +12.3 pp [11.4, 13.2], +749 / −41 sets; LLM-written cards hold a stale value in 80–87% of checks vs 0% for code-compiled (n=30) |
| **I6** gap-check loop | **Killed (with a 1.7B local model)** | +0.3 pp item recall, +0 CR (48 sets) at 1.98 LLM calls per request; did not answer NONE in round 1 for 44 of 48 requests (kill: <3 pp over one-shot) |
| **I8** origin context for media | **Supported (replicated with real embedders, no harm)** | +21 to +30 pp CR by retriever; weighted hybrid 55.3 → 85.1 (+125 / −4, p=3e-32) |
| **N4** the linker is the bottleneck for cards and slots | **Ceiling supported; built linkers killed** | oracle linker +4.2 pp ALL (+12.6 decision, +14.3 cross; p=7e-70). Embedding / LLM linkers raise entity recall 74 → 81–83% but CR ±0 (cards + slots) or −4 to −5 pp (cards ≤5): precision falls 57% → 20–28% |
| **N5** class-conditional prefix budget | **Supported** | two-regex router +0.9 pp vs best fixed arm (p=9e-4); removes temporal −22 / multimodal −9 pinning penalty |
| **N6** decomposition / gap-check / linker matter more than the reranker for multi-item classes | **Supported for structure (linker, slots); contradicted for decomposition and gap-check** | rerankers: 0.0 pp on decision and cross (pool ceilings 8% and 3%). Oracle linker +12.6 / +14.3 pp. Decomposition and gap-check ≤ +1.5 pp item recall. Only structure moves these classes |
| **N7** never hard-filter on inferred scope | **Supported (replicated)** | query-inferred hard −4.2 pp (+23 / −292); inferred boost −0.9 pp (p=8e-9); keep inferred scope off entirely or validate a better inferrer first |
| **H9** k must vary by class | **Supported** | query-only decision 0.2 → 6.4 at k=30; cards+slots cross 4.6 → 14.4; collapse from size 2 persists (size-4 CR 14.6%) |
| **M1** CR ≈ p^m | **Holds for heterogeneous need-sets under query-only; breaks two ways** | temporal measured 65.7 vs 43.1 predicted (ρ=0.66); under pinned prefixes decision 15.0 vs 24.3 (ρ<0). Refined to a two-term model (N9) |
| H4 / I3 / N2 (mention forwarding, re-checked) | **Supported** | mention→head forwarding +2.1 pp ALL (current +6.1, option +4.9) |
| embedder choice (not a numbered hypothesis) | bge-small > Qwen3-Emb-0.6B on this corpus | −3.3 pp for Qwen3 (p=3e-9); Qwen3 better only on cross (+1.7) |

## Threats to validity

- **Still synthetic, and one author wrote both sides.** v0.2 widens the vocabulary and phrasing but stays templated. 2,179 distinct query strings over 2,537 tasks (seed 1) is far from the variety of real requests. Lexical difficulty is a little lower than v0 on decision support (26% vs 43% zero-overlap items). Embedders benefit from short canonical fact texts, which probably explains why bge-small beats Qwen3 here. On longer, messier real documents the ranking could flip. **Do not pick the production embedder from this table.** Pick it on real data, with this harness.
- **Distinct sets fix the cluster problem only partly.** Sets in one class share templates and entities (14 properties × several need templates), so sets are not fully independent either. The intervals are honest about task duplication but still somewhat narrow.
- **Subsampling.** E8b reranking ran on stratified distinct-set subsamples: 40 / 15 / 10 sets per class for seeds 1 / 2 / 3. The H12 and instruction variants ran on seed 1 only (40 sets per class). E6 LLM arms ran on seed 1 only (12 sets per complex class = 48 sets); model-free E6 arms on 40 sets per class × 3 seeds. N4 ran on seeds 1–2 (20 sets per class); its LLM linker on seed 1 only (6 sets per class). H13-lite (16 sets) and the I2 kill test (8 entities) ran on seed 1 only. **The reranking step after decomposition and gap-check was dropped:** it was out-of-memory killed under shared-container memory pressure. Reranker effects are measured on single-query pools in E8b, and E6 compares the candidate pools themselves. Small-n results are flagged as such. 
- **Hardware changed mid-run.** The container restarted onto a CPU without AMX / AVX512-BF16. All document and query embeddings, all seed-1 reranking, seed-2 bge/mxbai reranking and half of seed-2 Qwen3 reranking ran in bf16 on the first host. The remaining reranking ran in fp32 on the second host, and the LLM in emulated bf16. I checked on 300 docs that bf16 and fp32 embeddings match: cosine ≥ 0.998, identical recall@10. Reranker scores are cached by text, so the precision mix cannot bias comparisons within a seed. Latencies are reported per host.
- **Small LLM, small budget.** Decomposition, gap-check, linking and card writing used Qwen3-1.7B (greedy, thinking off, few-shot prompts written once on seed-2 examples and not tuned on test tasks). A frontier model would likely decompose and gap-check better. E6 therefore tests "cheap local LLM in the loop", not the ceiling of the idea.
- **Oracle arms use gold labels.** The oracle linker and the oracle slot contract are ceilings, not deployable systems.
- **Generator choices still set effect sizes.** Examples: the 70% fact share in decision support, the share of origin-only media (261 of 387 multimodal sets), and fixed templates for free-text evidence. Directions are more trustworthy than magnitudes.
- **H11 has no real pixels.** H11-lite renders OCR text onto synthetic boards and pages. It tests "can a single-vector image model read text in images as well as an OCR text twin", not real photos, charts or layout.
- **The gap-check prompt shows the top-8 items truncated to 110 characters**, with no metadata beyond item text. A production gap-check would see richer context.

## New hypotheses (for doc 06)

- **N8 — Free-text evidence is the new bottleneck: link it at ingest.** With every required keyed fact pinned, search still finds only 14–35% of required free-text items (meeting decisions, quotes, feedback, preferences) on the complex classes. *Proposal:* at ingest, attach each decision, quote, feedback item and preference to the entities and keys it is about (decision → topic entity, quote → supplier + category, feedback → supplier × business). Cards then list linked evidence IDs, so evidence becomes a structural lookup like facts. *Test:* card + linked-evidence prefix vs cards. *Kill:* <5 pp CR gain on decision / option / cross.
- **N9 — Two-term M1.** Use CR ≈ p_struct^m_struct × p_search^m_search, not p^m with a class-average p. Under pinned prefixes, item hits are negatively correlated (ρ ≈ −0.05 to −0.09) and CR is 6–10 pp below p_class^m. For homogeneous need-sets (temporal, ρ=0.66) CR is 22 pp above it. Budget the standard per item type.
- **N10 — Route the prefix, not just k.** A two-regex router (temporal / media → no prefix, else cards + slots) beats every fixed assembly (+0.9 pp ALL, p=9e-4) and removes the −22 pp temporal / −9 pp multimodal penalty of pinning. A learned router over the 8 classes should do better. *Kill:* a learned router adds <1 pp over the regex one.
- **N11 — Pick the embedder on short-record recall, then fuse with BM25 using a tuned weight.** bge-small (33M parameters) beat Qwen3-Embedding-0.6B by 3.3 pp on this corpus of short records. Weighted fusion with α tuned on one seed transferred to held-out seeds and beat RRF by 1.8 pp. *Test on real data:* are real-corpus embedder rankings consistent with sandbox rankings?
- **N12 — Card selection, not card count.** The oracle linker moves cards (≤3) from 56.9 to 61.1% ALL, and pinning all required facts reaches 69.2%. The gap between "cards for linked entities" and "the right facts" (8 pp) suggests ranking facts within and across cards by the request (fact-level pinning) rather than pinning whole cards.
- **N13 — Calibrated, precision-first pinning.** Pin a card only when linker confidence clears a threshold calibrated per class. Embedding / LLM linkers raised entity recall by 7–9 pp but cut precision from 57% to 20–28%, leaving CR flat or −4.7 pp; the oracle linker is worth +12.6 / +14.3 pp on decision / cross. Also add abstract "household finance" entities (portfolio, offset, budget) that the linker can reach from "can we afford X" requests. *Test:* threshold sweep, CR vs pinned-card precision. *Kill:* no threshold beats the lexical linker by ≥2 pp ALL.
- **N14 — Narrow, class-specific reranker instructions only.** The broad "retrieve everything needed" instruction cost 4.7 pp (Qwen3) and 11.6 pp (mxbai), mainly on lookup classes. If instructions are used at all, use them only for the indirect classes, behind the router, and test against the generic default per class. *Kill:* no class gains ≥2 pp.

