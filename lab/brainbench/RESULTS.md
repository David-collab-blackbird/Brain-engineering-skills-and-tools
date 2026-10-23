# BrainBench v0 — sandbox results (E0, E1, E2, E3, E4, E5, E7, I8)

Run: 2026-10-23 · Author: Claude (engineer) · Re-run with `python run_all.py` (~100 s on 2 CPUs; deterministic, two runs gave identical results).
Full generated tables, including every arm and paired test: `results/tables.md`. Raw numbers: `results/results.json`. Data schema: `data/README.md`.

**Read this first.** Every number below comes from lexical retrieval (BM25, TF-IDF, and LSA as a weak stand-in for embeddings) over a synthetic, templated world that I generated myself. The numbers are good for comparing arms against each other. They are not estimates of how a real system would score. Brackets are Wilson 95% intervals. Paired comparisons use exact McNemar tests. Tasks in several classes reuse the same required sets with different wording, so the intervals are too narrow (see §Threats).

## Headline findings

1. **Keyed upsert gets stale *fact versions* to zero, but most stale answers come from notes, not facts.** Under keyed upsert, no superseded version ever outranks the current one (0.0% [0–1.3], n=286). But a free-text note quoting an old value outranks the current fact in **33.9% [28.7–39.6]** of probes, and the first value-bearing item in the top-10 is stale **38.4%** of the time. Linking each value mention to its fact at ingest, then forwarding it to the current value, cuts this to **0.7% [0.2–2.5] traps and 1.0% [0.3–3.6] first-value-stale**. That combination hits the ≤2% stale target on its point estimate; the upper bound does not yet certify it.
2. **Forwarding a mention to its current fact is also a recall win.** A retrieved note that quotes a fact pulls that fact's current version into context. This cut "current fact missing from top-10" from 52.4% to 29.7% (69 wins / 4 losses, p=2e-16). It also raised current_state CR@10 from 43.2% to 59.0%. Notes are better entry points to facts than the facts themselves are.
3. **Entity cards compiled in code, plus slot lookups, are the biggest assembly win** (ALL 18.4% → 30.1%, +178/−27, p=2e-28). current_state goes from 43% to 98%. **Standing scope packets lose** to query-only at equal k (16.4% vs 18.4%, p=0.003). Even an oracle packet only ties.
4. **Origin context for media (I8) roughly doubles multimodal recall** (28.0% → 54.7% with RRF, 40 wins / 0 losses), with no loss on items whose caption was already enough.
5. **Global BM25 statistics leak exact counts from hidden partitions** (E4). An attacker recovered the exact number of hidden documents containing a chosen word, for every word tried. Computing statistics per partition, or over the requester's visible set, closes the leak (Δ score exactly 0). TF-IDF and LSA fitted on the whole corpus also leak a little.
6. **Graph expansion without per-hop access checks leaks; with them it doesn't.** Without per-hop checks, 4.5–8.5% of tasks leaked data from other partitions. With them, 0 of 1,291 leaked. The canary monitor fired in every leaking configuration (18–278 alarms out of 501 probes) and never in a safe one. Graph expansion added little recall (≤ +1.1 pp).
7. **The indirect classes fail at candidate generation, not ranking.** At depth 200, decision_support has all of its required items for only 22% of tasks; cross_domain for only 10%. No reranker can fix that. CR@10 also drops sharply as the required set grows: from 85% at size 1 to 10% at size 4 and about 0% at size 5 or more, even with the best pipeline.
8. **Coverage packing over generic facets hurt** (−1.4 pp, p=0.012). MMR did nothing (p=0.83). I7 is killed in this form.

## E0 — BrainBench v0

**World.** 8,038 items (2,516 chat, 1,838 log, 1,016 note, 537 email, 514 fact versions, 1,553 media stand-ins, 39 preferences, 7 meetings, 18 canaries). 130 entities, 186 keyed facts, 90 graph edges, 18 partitions, 16 identities. Keyed facts change over 18 simulated months, with 1–6 versions each. Each version records valid_from, valid_to, the day it was recorded (lagged 0–9 days) and supersession pointers. 835 notes quote a specific fact version; 568 of those quote a value that was later superseded (stale traps). Media items have caption, OCR or transcript plus origin fields. In 29 target media items, the identifying words appear only in the origin fields. Six real-world entities cross access boundaries: a linen supplier and a plumber each used by two businesses, a staff member at both gym and cafe, Priya as household member and gym member, the head coach who is also the owner's personal coach, and a property that the construction firm is renovating.

**Tasks.** 1,577 tasks: 150–222 per class across 8 classes, plus 286 stale probes. Required-set sizes run from 1 to 10. Every task has a requester identity and a declared scope, and every required item is accessible to that requester (asserted at build time). Requests are written to avoid lexical overlap. In decision_support, 43% of required items share no token with the request, and 84% of tasks have at least one such item (current_state: 7%).

**Baselines** (keyed store, access pre-filter, regex temporal router, no scope), CR@10 %:

| retriever | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| BM25 | 0.0 [0–2] | 13.8 [9–20] | 40.5 [34–47] | 22.3 [16–29] | 1.3 [0–5] | 8.4 [5–14] | 2.0 [1–6] | 68.7 [61–76] | 20.7 [19–23] |
| TF-IDF cosine | 0.0 | 11.8 | 40.1 | 24.8 | 1.3 | 7.1 | 2.0 | 60.7 | 19.6 [18–22] |
| LSA-256 "dense proxy" | 0.0 | 2.0 | 43.7 | 24.8 | 0.0 | 4.5 | 0.0 | 49.3 | 17.0 [15–19] |
| RRF(BM25, LSA) — **default** | 0.0 | 5.9 | 45.9 | 27.4 | 0.0 | 3.9 | 0.7 | 54.0 | 18.7 [17–21] |
| weighted sum 0.6/0.4 | 0.0 | 5.9 | 45.5 | 29.9 | 0.0 | 5.8 | 0.7 | 66.7 | 20.7 [19–23] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

(The default arm scores 18.4% in E2/E3/E5/E7, against 18.7% here. Those experiments compute BM25 statistics over everything the requester can access, including superseded versions; E0 computes them over the live set only. The gap is within noise.)

**Depth diagnostic** (default hybrid; item recall / CR at depth d):

| class | d=10 | d=50 | d=200 |
|---|---|---|---|
| decision | 12 / 0 | 30 / 1 | 63 / 22 |
| cross | 8 / 1 | 23 / 1 | 48 / 10 |
| goal | 34 / 0 | 51 / 7 | 77 / 52 |
| current | 47 / 43 | 78 / 76 | 91 / 90 |
| multimodal | 57 / 55 | 83 / 81 | 97 / 96 |

LSA is the weakest single retriever here. It cannot bridge paraphrases it never saw in this small corpus, and it pulls RRF down on option and preference tasks. **Do not read this as "dense hurts".** Read it as "LSA is not an embedding model". Item-level recall is reported alongside CR because many cells sit at the 0% floor.

## E1 — Write paths and stale facts (H4, I3, H5)

**Setup.** 286 stale probes: 143 keys with at least two versions, two phrasings each, all asking for the current value. Metrics:
- **stale-fact**: a superseded version of the same key ranks above the current version.
- **stale-trap**: a note quoting an old value ranks above the current version.
- **stale-summary**: a derived summary holding an old value ranks above it.
- **head miss**: the current version is not in the top-10.
- **first value stale**: the first value-bearing item in the top-10 is stale. This is the closest proxy for what an assistant would actually answer with.

No LLM was available, so model-based invalidation is simulated as keyed upsert where a share of superseded versions is missed (stays live).

| arm | stale-fact | stale-trap | head miss@10 | first value stale |
|---|---|---|---|---|
| (c) add-only, no recency | **28.7 [23.7–34.2]** | 33.2 | 58.0 | 64.4 [57.6–70.6] |
| (b) add-only + recency prior (RRF w=1) | 1.7 [0.7–4.0] | 24.1 | 55.9 | 13.7 [9.7–19.0] |
| (b) add-only + recency prior (w=2) | 0.0 [0–1.3] | 11.5 | **63.6** | 4.6 [2.4–8.5] |
| simulated invalidation, 2% / 5% / 10% / 20% missed | 1.7 / 3.1 / 4.5 / 8.7 | ≈34 | ≈53 | 41–44 |
| I3 alone: add-only + forward-to-head | 0.0 [0–1.3] | 28.7 | 48.6 | 34.3 |
| (a) keyed upsert | **0.0 [0–1.3]** | **33.9 [28.7–39.6]** | 52.4 | 38.4 [32.1–45.1] |
| (a) + I3 + mention→head forwarding | 0.0 | 27.3 | **29.7** | 38.2 |
| (a) + I3 + stale-mention suppression, extraction recall 70 / 90 / 100% | 0.0 | 18.2 / 8.0 / 0.0 | 48.3 / 45.5 / 44.8 | 21.2 / 8.9 / 0.0 |
| **(a) + I3 + suppression (90%) + mention forwarding + recency** | **0.0** | **0.7 [0.2–2.5]** | 33.6 | **1.0 [0.3–3.6]** |
| (a) + I3 + entity summaries from month 6, never regenerated | 0.0 | 35.0 | 52.4 | stale-summary **3.8 [2.2–6.8]** |
| (a) + I3 + summaries regenerated when their facts change | 0.0 | 33.9 | 49.7 | stale-summary 0.0 |

Paired head-found: add-only + forwarding finds the current version where keyed deletion does not in 12 cases, and the reverse happens in 1 (p=0.003). Mention forwarding against plain keyed: 69 / 4 (p=2e-16).
The 39 month-6 summaries contained 122 values that were later superseded.
temporal_change CR@10: keyed with history never searched 0.0%; keyed with the temporal router opening history 27.4% [21–35]; add-only 35.0% [28–43].

**Verdicts**
- **H4: Supports the necessary half; the sufficiency claim is contradicted.** Keyed upsert removes version-versus-version staleness by construction (upper bound 1.3%). Add-only without recency is 14× over target. Add-only with a strong recency prior can match keyed on fact versions, but only by losing the current value more often (head miss 63.6% at w=2, against 52.4% for keyed). Simulated invalidation is only within target at a ≤2% miss rate, and even then the upper bound (4.0%) does not certify it. But keyed facts alone leave stale answers in about 34–38% of probes, through notes. The stale-fact constraint as the charter means it ("the brain returns current facts") **cannot be met by the write path alone**.
- **I3: Supports, with a twist.** On fact versions, forwarding adds nothing on top of keyed upsert (both 0%). But "keep superseded versions indexed and forward them" beats "delete them from the live index" on finding the current value (p=0.003): old versions act as extra entry points. The extension, forwarding mentions to the current fact, is the bigger effect.
- **H5: Supports.** Summaries that were never regenerated put an old value above the current one in 3.8% [2.2–6.8] of probes. That alone exceeds the 2% budget. Regenerating when facts change brings it to 0.

## E2 — Scope modes (H1, H2, I12)

**Setup.** Default hybrid. Scope groups: finance, gym, construction, cafe, health, family, reading.
- **Hard filter**: restrict to the scope group.
- **Boost**: add the in-scope ranking as a third RRF list.
- **Inferred from query**: nearest scope centroid in TF-IDF space, abstaining when unsure.
- **Trail**: majority vote over a simulated 6-item activity trail with noise 0.3 or 0.6.

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL | paired vs none |
|---|---|---|---|---|---|---|---|---|---|---|
| none | 0.0 | 5.9 | 43.2 | 27.4 | 0.0 | 3.9 | 0.7 | 54.7 | 18.4 [16–21] | – |
| declared, hard filter | 0.0 | 5.9 | 46.8 | 32.5 | 1.3 | 5.8 | **0.0** | 57.3 | 20.2 [18–22] | +26/−2, p=3e-6 |
| declared, boost w=1 | 0.0 | 5.9 | 46.4 | 31.8 | 1.3 | 5.8 | 0.7 | 58.7 | 20.3 [18–23] | +25/−0, p=6e-8 |
| inferred from query, boost | 0.0 | 5.9 | 45.0 | 28.0 | 0.0 | 3.9 | 0.7 | 52.0 | 18.4 | +6/−5, ns |
| inferred from query, hard | 0.0 | 5.9 | **36.5** | 26.8 | 0.0 | 3.9 | 0.7 | 52.0 | **16.8** | **+7/−27, p=8e-4** |
| trail (noise 0.3), boost | 0.0 | 5.9 | 45.5 | 31.8 | 1.3 | 5.8 | 0.7 | 58.7 | 20.1 | +25/−2, p=6e-6 |

Item recall@10, decision / goal / cross: none 12.1 / 34.7 / 8.4; declared hard 15.2 / 41.1 / 9.7; declared boost 14.9 / 40.4 / 10.6.
**Hard-filter ceiling**: share of tasks whose required items all sit in the declared scope: cross 0%, option 90%, decision 95%.
**Scope inference accuracy**: query 39.1% (abstains on 618 of 1,291); trail at noise 0.3: 97.3%; trail at noise 0.6: 82.3%; trail + query at noise 0.6: 90.2%.
With a BM25-only first stage, a hard filter lowers option_analysis from 13.8% to 8.6%; boost gives 10.5%.

**Verdicts**
- **H1 (≥10 pp on decision and goal): Contradicted at this retrieval quality**, with a floor caveat. CR@10 goes 0→0 (decision) and 0→1.3 (goal). Item recall rises by 3 and 6 pp. Declared scope gives a real but small overall gain (+1.8–2.1 pp, highly significant), mostly on current_state and temporal_change. The indirect classes are limited by candidate generation, which scope cannot fix. Re-test H1 with real embeddings once those classes are off the floor.
- **H2 (boost beats hard filter on cross_domain): Structurally supported, empirically inconclusive.** A hard filter on one declared scope caps cross_domain at 0% by construction, and it hurt option_analysis under BM25. Boost never lost a task against "none" (+25/−0). The observed cross_domain gap (0.0 vs 0.7) is at the floor.
- **I12 (trail beats query for scope inference): Supports, with a large caveat.** The trail is 97% accurate against the query's 39%. But the trail simulator draws 70%+ of items from the true scope, so the result follows from how the trail was built. The robust finding is the negative one: **a hard filter inferred from the query is net harmful** (−27/+7, current_state −6.7 pp). Inferred scope should only ever boost.

## E3 — Context assembly at equal k=10 (H3, I1, I2)

**Arms**
- **Packet**: a task-agnostic standing set per scope: current goal, strategy and rule facts, plus recent meeting decisions.
- **Oracle packet**: the items most often required by tasks in that scope, computed from the test set itself. This is a ceiling for any packet.
- **Hand slot contract**: per-scope slots, filled with current facts of entities that a lexical entity linker finds in the query, plus static scope slots.
- **Generic slots**: all current facts of the linked entities, then the packet.
- **Entity cards**: one card per entity and partition, compiled in code from current keyed facts. Cards are indexed, and the top 3 linked cards are pinned. A card counts as covering the fact versions it contains.

The remaining slots go to query search in every arm.

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL | paired vs query-only |
|---|---|---|---|---|---|---|---|---|---|---|
| query-only | 0.0 | 5.9 | 43.2 | 27.4 | 0.0 | 3.9 | 0.7 | 54.7 | 18.4 [16–21] | – |
| packet(5) + query(5) | 0.0 | 7.2 | 39.6 | 19.1 | 2.0 | 3.9 | 0.7 | 48.7 | **16.4** [15–19] | +20/−45, p=0.003 |
| ORACLE packet(5) + query(5) | 0.0 | 10.5 | 37.8 | 15.9 | 6.6 | 22.7 | 0.7 | 46.7 | 18.7 | +58/−54, ns |
| query + mention→head forwarding | 0.0 | 5.9 | 59.0 | 26.8 | 4.6 | 5.8 | 0.7 | 54.7 | 21.8 [20–24] | +52/−8, p=5e-9 |
| hand slot contract + query | 1.3 | 6.6 | 85.6 | 21.7 | 11.3 | 3.2 | 0.7 | 46.7 | 25.5 [23–28] | +116/−24, p=1e-15 |
| generic slots + query | 1.3 | 5.9 | 90.1 | 22.3 | 5.3 | 3.9 | 0.7 | 48.0 | 25.8 [23–28] | +118/−22, p=4e-17 |
| entity cards (≤3) + query | 4.6 | 13.2 | 94.6 | **33.8** | 8.6 | 3.2 | 0.7 | 53.3 | **30.1** [28–33] | +159/−7, p=1e-38 |
| cards + hand static slots + query | **8.5** | 13.2 | **98.2** | 25.5 | **13.2** | 2.6 | 0.7 | 48.0 | **30.1** [28–33] | +178/−27, p=2e-28 |

Item recall@10, cards + slots against query-only: decision 70.6 vs 12.1; goal 65.7 vs 34.7; cross 37.5 vs 8.4; ALL 60.5 vs 30.4.
**Prefix-alone coverage** (mean share of required items): packet(5) covers 4–28% depending on class and fully covers 0% of tasks outside current_state (9%). Cards + slots cover 95% on current, 69% on decision and 62% on goal, but fully cover only 5% / 9% of decision / goal tasks.
**Entity-linker recall** on required fact entities (lexical alias matching): current 88%, decision 45%, cross 31%.
The BM25-only robustness re-run gives the same ordering: cards 32.8%, slots 27.4%, query-only 19.3%, packet 17.0%.

**Verdicts**
- **H3: Contradicted.** Standing packets do not cover most required items, and at equal k they lose to query-only (p=0.003). Even an oracle packet built from the test set only ties overall. Packets win on goal and preference tasks and lose on current, temporal and multimodal.
- **I1: Supports. It survives the kill criterion** (+9.1 pp over packet(5), kill threshold <5 pp). But hand-designed contracts barely beat generic "all current facts of the linked entities" overall (25.5 vs 25.8). Hand contracts do better on item recall for decision (50.7 vs 46.6) and cross_domain (28.2 vs 19.3). The active ingredients are entity linking plus a keyed-fact lookup. A schema helps the indirect classes on top.
- **I2: Supports the recall benefit; the code-compiled versus model-written comparison is deferred** (needs a model). Cards are the strongest single arm (+11.7 pp ALL), with 7 losses against 159 wins. E1's stale-summary result (3.8%) is the risk a model-written or never-regenerated card would carry.
- Pinned prefixes **cost** multimodal (−6.7 pp) and, for hand slots, temporal (−5.7 pp). Assembly needs a per-class budget.

## E4 — BM25 statistics side channel (H10)

**Attacker.** partner_cafe can see biz/cafe and public/gym. It plants a one-word note in its own partition, queries that word, and inverts the BM25 formula to estimate the word's document frequency.

| probe term | docs containing it (all) | of which hidden from attacker | estimated df, global stats | visible-set stats | per-partition stats |
|---|---|---|---|---|---|
| halyard (owner property) | 327 | 326 | **327.0** | 1.0 | 1.0 |
| refix (refinance emails) | 7 | 6 | **7.0** | 1.0 | 1.0 |
| glyph (word from the owner's canary) | 3 | 2 | **3.0** | 1.0 | 1.0 |

Controlled insertion of M hidden owner documents containing a rare term changes the score of the attacker's own visible document:

| M | global stats | visible-set stats | per-partition stats |
|---|---|---|---|
| 0 | 12.262 | 9.497 | 9.383 |
| 1 | 11.532 (Δ −0.729) | Δ 0.000 | Δ 0.000 |
| 5 | 10.168 (Δ −2.093) | Δ 0.000 | Δ 0.000 |
| 20 | 8.462 (Δ −3.800) | Δ 0.000 | Δ 0.000 |

With 3 or more hidden documents, the order of two visible documents flips under global statistics, so rank alone leaks. Vector models fitted on all partitions leak too. Adding 10 hidden documents moved a visible document's TF-IDF cosine by −0.039 and its LSA cosine by +0.004.

**Verdict — H10: Supports (demonstrated exactly).** Global statistics reveal exact hidden document counts, and could confirm that a canary word exists in the owner partition. Visible-set or per-partition statistics close the channel completely. **Builder rule: any statistic fitted on the union of partitions is a side channel.** That covers IDF, avgdl, SVD or LSA bases, and corpus-trained vocabularies. Fit these per partition, over the requester's visible set, or use frozen external models. My own sandbox retriever fits TF-IDF and LSA globally, which is acceptable only because this is a benchmark.

## E5 — Entity-graph expansion (H6, I11)

**Setup.** Seeds are the entities on the top-5 hybrid results. Expansion goes 1 or 2 hops over typed edges, skipping hub entities with more than 150 items. Expanded items are merged in two ways: 3 reserved slots, or RRF with weight 1.
- **Per-hop ACL**: an edge is followed only if its owning partition, and the destination entity, are visible to the requester; items are re-checked.
- **No per-hop ACL**: only the seeds are access-checked. This is the injected bug.

| arm | ALL CR@10 | tasks with leak | leaked items | canary-monitor alarms / probes |
|---|---|---|---|---|
| no graph | 18.4 [16–21] | 0 [0–0.3%] | 0 | 0/501 |
| 1-hop, per-hop ACL, RRF | 19.5 [17–22] (+27/−12, p=0.024) | **0** | 0 | **0/501** |
| 2-hop, per-hop ACL, RRF | 19.3 | 0 | 0 | 0/501 |
| 1-hop, NO per-hop ACL, reserved | 19.0 | **4.5% [3.5–5.8]** (58 tasks) | 111 (32 tasks leaked a canary) | **278/501** |
| 2-hop, NO per-hop ACL, reserved | 18.7 | **8.5% [7.1–10.2]** (110 tasks) | 252 | **193/501** |
| 2-hop, NO per-hop ACL, RRF | 19.3 | 1.0% [0.6–1.7] | 35 | **18/501** |

The leaking requesters were partners and members, plus 3 household tasks. Leaks travelled through exactly the shared entities: the linen supplier, the plumber, the dual-role staff member, Priya and the coach. option_analysis and cross_domain CR@10 did not change in any arm (0 wins / 0–1 losses). With a BM25 base, 1-hop gains +1.7 pp ALL.

**Verdicts**
- **H6: Leakage half supported, recall half contradicted.** Per-hop authorisation gave 0 leaks in 1,291 tasks, while the seed-only check leaked in 1–8.5%. The ≥5 pp lift on multi-hop classes did not appear (0 pp on option and cross; +1.1 pp ALL, mostly temporal and multimodal). In this world the needed items are linked through *concepts* ("buffer goal" ↔ "next purchase"), not through entity edges.
- **I11: Supports.** Canary probes ("anything new about <shared entity>?" from every non-owner identity) fired in every leaking configuration, including the subtle one where only 1% of gold tasks leaked (18 alarms). They never fired in a safe configuration. Build it as a CI test.

## E7 — Packing and required-set size (I7, H9)

**Packing at equal k=10** (pool = top 100 of the hybrid). Coverage packing scores each item as relevance + λ × new facet weight. Facets are entity (IDF-weighted), attribute, scope, quarter and type.

| arm | ALL CR@10 | paired vs top-k |
|---|---|---|
| top-k | 18.4 [16–21] | – |
| MMR (λ=0.7, LSA similarity) | 18.6 | +43/−40, p=0.83 |
| coverage packing, λ=0.25 / 0.5 / 1.0 | 17.4 / 17.0 / 12.8 | p=0.019 / 0.012 / 2e-13 (all worse) |

**CR@k by required-set size, best pipeline (cards + static slots + query):**

| k | size 1 (n=276) | 2 (228) | 3 (240) | 4 (275) | 5 (145) | 6 (71) | 7 (49) |
|---|---|---|---|---|---|---|---|
| 10 | 85.1 [80–89] | 32.9 [27–39] | 20.4 [16–26] | 9.8 [7–14] | 0.7 [0–4] | 0.0 [0–5] | 2.0 [0–11] |
| 20 | 90.2 | 37.3 | 29.6 | 16.0 | 4.8 | 1.4 | 8.2 |
| 30 | 93.5 [90–96] | 45.6 | 37.5 | 21.5 [17–27] | 5.5 | 2.8 | 8.2 |

By class at k=10 / 20 / 30: decision 8.5 / 17.0 / 23.5; multimodal 48 / 61 / 72; temporal 26 / 36 / 41; current 98 / 98 / 99.

**Verdicts**
- **I7: Killed in this form** (kill threshold: gain <2 pp; observed: a 1.4 pp loss, significant). Generic facets reward diversity the task does not need. Revisit only with *task-derived* facets, after decomposition (E6/H8).
- **H9: Direction supported, threshold contradicted.** k matters a lot (decision CR nearly triples from k=10 to k=30) and pass rate falls steeply with required-set size. But the collapse starts at size 2, not around 6, and above size 5 more k barely helps (<10% even at k=30). Lexical retrieval is the likely cause. The threshold needs re-measuring with real embeddings.

## I8 — Origin-context enrichment (multimodal, n=150)

| index | retriever | all | caption sufficient (n=31) | needs an origin-only item (n=119) |
|---|---|---|---|---|
| no origin context | RRF | 28.0 [21–36] | 71.0 | 16.8 [11–25] |
| **with origin context** | RRF | **54.7 [47–62]** | 71.0 | **50.4 [42–59]** |
| no origin context | BM25 | 38.0 [31–46] | 83.9 | 26.1 |
| **with origin context** | BM25 | **68.7 [61–76]** | 83.9 | **64.7** |

Paired: RRF 40 wins / 0 losses (p=2e-12); BM25 47 / 1 (p=4e-13).
**Verdict — I8: Supports, far above the kill threshold (+26.7 pp against 3 pp), with no cost on items whose caption was already enough.** The *size* of the gain depends on a generator choice: 119 of 150 tasks need an origin-only item. The *no-harm* result is the robust part. Half of the origin-only tasks still fail.

## Hypothesis scoreboard

| ID | verdict | key number |
|---|---|---|
| H1 | Contradicted at this retrieval quality (floor) | decision 0→0, goal 0→1.3 pp CR@10; ALL +1.8–2.1 pp (p<1e-5) |
| H2 | Structurally supported; empirically inconclusive | hard-filter ceiling on cross = 0%; boost never lost a task (+25/−0) |
| H3 | **Contradicted** | packet 16.4 vs query-only 18.4 (p=0.003); oracle packet only ties |
| H4 | Necessary, not sufficient | keyed 0.0% stale versions, but 33.9% stale-trap / 38.4% first-value-stale |
| H5 | **Supports** | never-regenerated summaries 3.8% [2.2–6.8]; regenerated 0 |
| H6 | Leakage half supported, recall half contradicted | 0 leaks with per-hop ACL vs 4.5–8.5%; ≤+1.1 pp recall |
| H9 | Direction supported; threshold wrong | collapse from size 2; sizes ≥5 under 10% even at k=30 |
| H10 | **Supports (exact)** | estimated hidden df = true df; Δ score −0.73 per hidden doc; per-partition Δ 0 |
| I1 | Supports (survives kill) | +9.1 pp over packet; hand ≈ generic overall |
| I2 | Supports (recall); code-vs-model deferred | cards 30.1 vs 18.4 (+159/−7) |
| I3 | Supports; adds nothing on top of keyed for fact versions | keeping history indexed + forwarding finds more current values (p=0.003) |
| I7 | **Killed (generic facets)** | −1.4 pp, p=0.012 |
| I8 | **Supports** | 28.0 → 54.7 (+40/−0) |
| I11 | **Supports** | alarms in every leaking configuration (18–278/501), 0 in safe ones |
| I12 | Supports (caveat: simulated trail) | 97% vs 39%; query-inferred hard filter harmful (−27/+7) |

## New hypotheses suggested by these results (for doc 06)

- **N1 — Mention linking at ingest.** Extract value mentions from every free-text item and link them to keyed-fact versions (`fact_refs`). When a version is superseded, demote, annotate or forward each mention. *Evidence:* notes quoting old values are the dominant stale source under keyed upsert (34%). At 90% extraction recall plus forwarding plus recency, traps fall to 0.7% and first-value-stale to 1.0%. *Test (S+, needs a model):* real extraction recall on real notes. *Kill:* extraction recall <80% on real text.
- **N2 — Index history as entry points; always serve the current value.** Keep superseded versions and stale mentions *indexed*, but forward them to the current value. Never serve them except to temporal queries. *Evidence:* better head recall than deletion (p=0.003); mention forwarding 52→30% head miss, current_state +15.8 pp.
- **N3 — Corpus-fitted representations are side channels.** This generalises H10: IDF, avgdl, LSA/SVD bases, and any vocabulary, quantiser codebook or model fine-tuned on all partitions. The quantiser and fine-tuning cases are my extrapolation and untested. *Test:* the same insertion probe against each component.
- **N4 — The entity linker is the real bottleneck for slots and cards.** Linker recall is 31% on cross_domain and 45% on decision, yet cards and slots already deliver the largest gains. *Test (S+):* embedding or LLM linker against the lexical one at a fixed assembly. *Kill:* <5 pp CR gain.
- **N5 — Class-conditional assembly budget.** Pinned prefixes help current, decision and goal but cost multimodal (−6.7 pp) and temporal (−5.7 pp). A router should decide the prefix size per class, together with H9's per-class k.
- **N6 — Indirect classes need recall at candidate generation.** CR@200 is 22% for decision and 10% for cross, so rerankers are irrelevant until decomposition, slots or gap-checks put the items in the pool. **Prioritise E6 (decomposition vs gap-check) and N4 over reranker work.**
- **N7 — Never hard-filter on inferred scope** (−27/+7). Inferred scope only boosts; only declared scope may filter, and only for classes that stay within one scope.

## What a builder should take from this (sandbox-grade, re-validate in S+)

1. Store keyed facts with supersession pointers. Keep history indexed but serve only current values (forward-to-head), except when the temporal router fires.
2. At ingest, link every free-text value mention to its fact version. Demote or annotate superseded mentions, and forward them to the current value.
3. Regenerate derived artefacts (cards, summaries, packets) from a dependency graph whenever a source fact changes.
4. Compute BM25 and any corpus statistics over the requester's visible set or per partition, never globally. Use frozen embedding models.
5. Check access on every graph hop and on every expanded item. Run the canary monitor as a CI test.
6. Use scope as a boost. Hard-filter only on declared scope, and only for single-scope classes.
7. Compile entity cards in code, pin the linked cards, then fill the remaining slots by search. Invest in the entity linker.
8. Index origin context (folder, album, chat, sender, adjacent text) with every media item.
9. Do not ship coverage packing on generic facets.

## Threats to validity

- **Synthetic, templated text.** One author wrote both the world templates and the requests, so vocabulary overlap is an author decision. I deliberately avoided overlap: 43% of decision required items share no token with the request, which may make the set harder than real life. Real notes are messier, longer, multilingual and full of implicit references. Free text such as "Busy morning, 241 covers" mentions values that are not labelled as fact mentions, so stale-trap rates are probably **under**-counted.
- **Lexical-only retrieval.** LSA is a weak proxy: it is fitted on 8k short documents and knows no paraphrases. Real embeddings should lift the indirect classes off the 0% floor, which would make H1, H2 and H6 testable. That could shrink the relative value of cards, slots and mention forwarding. Or it could increase it, because embeddings fix lexical gaps but not "which facts does this decision need".
- **Clustered tasks.** Several classes reuse a need-set across phrasings and requesters (distinct required sets: decision 47, goal 38, pref 34, cross 44, multimodal 54; stale probes are 143 keys × 2). The Wilson intervals assume independence and are therefore too narrow; treat the effective n as roughly the number of distinct sets. Paired McNemar tests are less affected but still assume independent pairs.
- **Floor effects.** CR@10 is about 0% for decision, goal and cross in most arms, so many "no difference" results there are uninformative. Item recall is reported to compensate.
- **Components tuned with knowledge of the generator.** The temporal router regex was written while looking at the gold queries (141/157 recall, 46/1,420 false fires); it is overfitted. I wrote the hand slot contracts knowing the task templates, which makes them optimistic. The fact that generic slots score the same partly offsets this. Cards are compiled from the same keyed facts that current_state requires, so 98% on current_state is close to circular. It demonstrates the plumbing, not generalisation.
- **Simulated components.** Model-based invalidation is modelled as a random miss rate. Real misses are correlated with hard cases. Activity trails come from the true scope at a fixed noise level, so the I12 accuracy is by construction. Mention extraction recall is simulated, not measured.
- **Generator choices drive effect sizes.** The share of origin-only media (I8), the density of stale mentions (E1) and the graph topology (E5) set the magnitudes. The direction of each effect is more trustworthy than its size.
- **One seed, one world, about 8k items.** The charter targets 10k+ items with images and video. Variance across seeds and scaling behaviour were not measured. Run `bb.world.main(seed)` with several seeds before relying on any small difference.
- **Not run:** E6 (decomposition and gap-check, needs a model in the loop), E8 (real embedders, rerankers, multimodal), and the model-written versus code-compiled card comparison (I2 kill test).
