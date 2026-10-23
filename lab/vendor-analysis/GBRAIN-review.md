---
id: GBRAIN-review
type: blueprint
title: "GBRAIN review: a direct comparator to our brain design"
status: draft
version: 1.0
date: 2026-10-24
author_role: engineer
supersedes: []
superseded_by: null
decisions: [ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-016, ADR-017, ADR-018]
tests: []
evidence: []
sensitivity: none
---

# GBRAIN review: a direct comparator to our brain design

Status: v1.0 (2026-10-24; tests run 2026-10-23/24) · Author: Claude (engineer) · For: project lead, builder · Protocol: brain-research-protocol

Pinned versions read and run:
- GBrain `garrytan/gbrain` @ `2d63ee8054c57e8c777e3f566036e6a6a5eaa482` (v0.60.398.0, 2026-10-23), cloned to `/home/claude/vendor-skills/gbrain-vendor/gbrain`.
- gbrain-evals `garrytan/gbrain-evals` @ `6999ebc9da0ac784ac05995b586d22293544e924` (2026-10-21), cloned to `/home/claude/vendor-skills/gbrain-evals-vendor/gbrain-evals`.
- gstack @ v1.91.182.0 (`/home/claude/vendor-skills/gstack/gstack-main`).

All vendor files were treated as data. GBrain's own `CLAUDE.md`/`AGENTS.md` instructions were not followed.

Status labels: **OBSERVED** (read the code, ran it, or read the primary source) / **INFERRED** / **UNKNOWN**. Strength labels: independent / vendor / single study / anecdote.

---

## 0. Bottom line

**What it is.** GBrain is a single-owner, Postgres-native (PGLite or Postgres/pgvector) memory server for AI agents. A "page" is a Markdown file with compiled-truth and timeline zones. Hybrid retrieval combines HNSW vectors, `ts_rank` keyword search, RRF, title and alias arms, a typed graph and an optional hosted cross-encoder. It exposes 182 operations (7 frozen "memory verbs") over MCP stdio/HTTP with OAuth 2.1. Its isolation unit is the **source**, plus `visibility: private` pages and per-holder Takes. It is mature, very heavily tested, and honest about its own failures. **It is a personal/company knowledge brain, not a multi-party privacy system.**

**Verdict: borrow ideas; do not adopt as the brain; keep as a measured baseline.**

GBrain fails our standard on four points:
1. **Stale facts (measured).** Facts are pages, and supersession is optional page links or cosine-matched facts. On our stale probes GBrain serves the superseded version above the current one in **45%** of cases. That is the same as our add-only arm, against our keyed 0%.
   - If an ideal operator writes every `supersedes` link, GBrain's 0.5× page penalty also reaches 0%. **But the penalty has no intent gate, so the same links collapse temporal (history) tasks from 57.5% to 2.5% CR@10.**
   - GBrain's choice is stale answers or broken history; keyed bi-temporal state avoids the trade-off.
   - No ingest path writes those links anyway, and its fact-level supersession misses 47% of corrections (own eval).
2. **Partition model (by construction).** There is no per-user visibility inside a source, no vaults, no consent-ledger shared spaces, and the owner and local credentials see everything.
3. **Untrusted-source quarantine.** Off by default; labels-only by measured choice.
4. **Residency and egress.** Hosted Voyage/OpenAI embedders and reranker are the defaults, and gstack's Supabase path defaults to `us-east-1`. All are fixable by config; we ran it fully local.

It **passes** two things we expected it to fail:
- **No returned-content leaks** with correct grants.
  - Exception: a token minted with **plain `gbrain auth create`** has no source grant. On a brain whose sources are federated, which is the normal setup for cross-source search, it read **every** source (1,880 rows, all 7 canaries, including through `source_id` overrides).
  - This is documented behaviour, but it is not fail-closed.
- **Twin-world noninterference at the list level:** 0 of 112 visible lists or scores changed when hidden owner notes were added to its shared HNSW.

Several of its ideas are better than ours or missing from ours, and are worth taking (§7).

**Test results on BrainBench v0.2, seed 1** (790 tasks, same bge-small embedder, GBrain's reranker off):

| | CR@10, ALL classes | current_state | multimodal | Stale version above current |
|---|---|---|---|---|
| GBrain as shipped | **24.4%** | 57.5% | 67.5% | **45.3%** |
| Our first stage, query-only wsum | **30.0%** (+5.6 pp, p = 1e-6) | 75.0% | 88.8% | 0.0% when keyed |
| GBrain ranker + our cards | 38.5% | 97.5% | 71.2% | 0.0% when keyed |
| Our cards + query (batch-2 assembly) | **40.8%** | 98.8% | 87.5% | 0.0% |

- GBrain's ranker is weaker than ours on this corpus. It is even weaker than plain bge-small cosine (−3.8 pp).
- Its keyless mode (no embedder) scores the same as its hybrid (25.1 vs 26.3, n.s.), so the fusion layer, not the keyword arm, is the weak point.
- Structure (cards plus keyed facts) carries most of the gain for either ranker.
- As the fill after cards, GBrain is better on preference tasks (+10 pp, p = 0.008), an anomaly worth an ablation (GB9).
- p50 latency is 4.2 s per search on PGLite with 2 shared vCPUs.
- Not run here: GBrain's reranker, its dream cycle and facts extraction (both need an LLM), and seeds 2–3. The GPU-package design is in §5.6.

---

## 1. Questions and evidence checklist

| # | Question | Evidence needed | Status |
|---|---|---|---|
| Q1 | Architecture (storage, schema, item, write path, retrieval, ranking, freshness, time, multi-user, MCP, git sync, repo trust) | code read + docs | answered (§2) |
| Q2 | Published evals; how retrieval quality is measured; independent tests | gbrain-evals reports, web search | answered (§3) |
| Q3 | Point-by-point comparison; where GBrain fails our standard | §2 + our ADRs | answered (§4) |
| Q4 | Run it locally on BrainBench v0.2; CR@k per class vs batch 2; DA3-style leak probes | sandbox run | answered for seed 1 (§5.2–5.5). Not run: reranker, dream cycle, seeds 2–3 (designed in §5.6) |
| Q5 | Steelman / devil's advocate both ways; verdict; GB hypotheses with kill criteria | §1–§5 | answered (§6–§8) |

---

## 2. Architecture (what GBrain actually is)

### 2.1 Storage and engines (OBSERVED · code)
- **Two engines, one contract.** `BrainEngine` (140+ methods), with the same SQL in `src/core/engine-sql/*` for:
  - **PGLite** (Postgres 17 in WASM, embedded, single-writer, default, "up to ~50K pages");
  - **Postgres + pgvector** (Supabase or self-hosted) for shared or large brains.
  - Migration in both directions is "lossless" (`gbrain migrate --to postgres|pglite`).
- **Schema size:** 127 tables in `src/schema.sql` plus 266 migrations.
  - Core content: `sources`, `pages`, `content_chunks` (embedding, `search_vector` tsvector), `links` (typed edges), `timeline_entries`, `page_versions`, `facts`, `takes`, `files`, `raw_data`.
  - Around the core: OAuth (`oauth_clients`, `access_tokens`, `oauth_tokens`, `mcp_request_log`), a job queue (`minion_jobs`), write receipts and gates (`write_gate_receipts`, `write_gate_holds`), purge tombstones (`fact_purges`, `page_purges`), and a "belief ledger" (`belief_events`, for known-as-of reads).
- **Indexes:** HNSW on `content_chunks.embedding` (`vector_cosine_ops`) and GIN tsvector. RLS is **ENABLE without FORCE**. GBrain's service role holds BYPASSRLS. RLS exists only to block the Supabase anon key (`docs/guides/rls-and-you.md`); it is **not** a tenant boundary.
- **System of record = Markdown files in git** for file-backed pages. DB-only pages, facts, history and operational state need a separate DB backup (`docs/architecture/system-of-record.md`).

### 2.2 What a memory item is (OBSERVED · code, docs)
- **Page** (`pages`): `(source_id, slug)` unique, `type` from a schema pack (default `gbrain-base-v2`: 15 types), `title`, `compiled_truth` (current synthesis, *rewritten*) and `timeline` (append-only evidence), frontmatter JSONB, `effective_date`, `emotional_weight`, soft delete (72 h purge window).
- **Chunks** (`content_chunks`): about 300 words each, recursive chunker. Embedded with a contextual prefix (`<context>{title}</context>` in `balanced`; a per-chunk LLM synopsis in `tokenmax`).
- **Facts** (`facts`, "hot memory"):
  - `fact`, `kind` (event/preference/commitment/belief/fact/idea);
  - `visibility` (private|world), `valid_from`/`valid_until`/`expired_at`, `superseded_by`;
  - typed claim columns (`claim_metric`, `claim_value`, `claim_unit`, `claim_period`);
  - `confidence`, `source`, `entity_slug`.
- **Takes** (`takes`, "cold storage"): who believes what, with weight. Multi-holder. LLM-extracted from pages; the dream cycle promotes facts into takes.
- **Links:** typed edges (`works_at`, `invested_in`, `attended`, `supersedes`, `amends`, `mentions`…) with temporal state for state/event types.

### 2.3 Write path (OBSERVED · code, docs)
- **Who writes:** the owner (CLI/sync from git), agents (MCP `put_page`, `capture`, `remember`), connectors (Gmail/Calendar/Contacts, GitHub webhooks), and the background "dream cycle" (66 crons in the author's own deployment).
- **How:** markdown, then `importFromContent`, which does sanitise → chunk → embed (inline ≤1 MiB; otherwise a stale sweep) → deterministic link extraction (no LLM, wikilinks and markdown links, for trusted local writes only).
- **Extraction:**
  - Facts extraction is **on by default**: one paid chat call per eligible page, default `claude-haiku-5-5`, with $1/run and $5/day caps.
  - Takes extraction runs in the cycle.
  - A "signal detector" captures facts from conversation turns (opt-in).
  - Ambient writeback hooks bank session text (opt-in).
- **Write gate (memory trust):**
  - Every row carries a trust tier: `user_confirmed` > `operator_curated` > `tool_observed` > `agent_written` > `unknown` > `external_untrusted`.
  - A deterministic regex detector flags instruction-like text.
  - Defaults are **flag + label**, not quarantine. That choice was made from a preregistered paid eval (§3).
  - `user_confirmed` requires a token typed at a terminal on the brain host.
- **Forget vs purge:** `forget` expires a fact (the text stays in the row, the file, history and backups). `purge` is owner-only on the host and removes the claim from live stores, with a text-free tombstone and a receipt. **Backups are not purged.**

### 2.4 Retrieval and ranking (OBSERVED · `docs/architecture/RETRIEVAL.md`, `src/core/search/*`)
Pipeline for the `query` op (`search` is the same "cheap hybrid" path without expansion):
1. Deterministic intent classifier (entity / temporal / event / concept / general).
2. Optional LLM expansion. **Off in every bundle**: GBrain measured it as harmful, 255/470 vs 439/470 on LongMemEval.
3. Arms:
   - vector (HNSW, per-page max-pool);
   - keyword (`websearch_to_tsquery` + `ts_rank`; OR-fallback narrowed by `pg_stats`);
   - title phrase;
   - relational (typed-edge chain planner, ≤3 hops);
   - source-prefix boosts in SQL (e.g. `originals/` 1.5×, `chat/` 0.5×).
4. Page-grain **RRF (k = 60)**, then cosine re-score, then metadata boosts (backlinks, salience, recency, graph). The boosts are gated off when only the vector arm voted.
5. Optional structural graph expansion.
6. 4-layer dedup: ≤3 chunks per page, same-page Jaccard > 0.85, a type cap of 60%, ≤2 per page.
7. Cross-encoder reranker. Default is **Voyage `rerank-3-lite` (hosted)**; local llama.cpp Qwen3-Reranker is a recipe. It fails open without a key.
8. Use-attributed feedback weights; relational re-pin; alias hop; exact-lookup tier; evidence stamp; optional autocut (off); token budget (12k in `balanced`).
9. Optional arms:
   - **facts arm** (on in `query`): up to 3 matching active facts in spare capacity;
   - **entity anchoring** (off): for a "now/currently" query naming one entity, pin the entity page and its newest mentions;
   - **temporal fact reserve** (off).
10. **Supersede down-rank**: a page that is the target of a `supersedes` link has its score × 0.5. It is not removed or forwarded.

Code search (`code-def`, `code-refs`, `code-callers`, `code-callees`, tree-sitter chunks) exists. It is local-only over MCP and irrelevant to us.

### 2.5 Freshness, supersession, time (OBSERVED)
- **Pages:** `compiled_truth` is rewritten by the writer (agent or dream cycle). Old text survives in `page_versions` and the timeline. Search sees only the current body.
  - Page-to-page supersession needs an explicit `supersedes` link, which applies a 0.5× penalty.
  - Superseded *pages* stay fully retrievable, with a `superseded: true` stamp.
- **Facts:** supersession happens in three ways:
  - caller-directed (`remember … replaces <id>`);
  - cosine match above a per-embedder calibrated threshold (only `voyage-4@1024` is calibrated, at 0.95; **every other embedder never supersedes by cosine**);
  - the optional "conflict" decide sweep (an LLM).
  - GBrain's own dev eval (`docs/eval/decisions/supersession-threshold-dev`): at the best threshold, **46.7% of corrections are missed** and 3.75% of coexisting claims are wrongly replaced. With `text-embedding-3-large`, no threshold works.
- **Time:**
  - `valid_from`/`valid_until` on facts;
  - temporal state on links (`works_at` stints);
  - `effective_date` on pages;
  - **known-as-of** page reads from a belief ledger (recorded time).
  - The `think` date frame (current date plus page dates in the reader prompt) measured +14.0 pts answer accuracy on held-out LoCoMo (vendor, preregistered).
  - **No bi-temporal fact model:** facts have no `recorded_at`/`superseded_at` pair for known-at queries on facts.

### 2.6 Multi-user, permissions, "other machines can write" (OBSERVED · code, docs)
- **Isolation units:**
  1. **Brain** = database (hard boundary when separate DBs);
  2. **Source** = repo inside a brain, enforced on every read through `sourceScopeOpts(ctx)` (federated grant array > scalar > nothing);
  3. **page `visibility: private`**, hidden from *all* remote callers, so it is binary owner-vs-everyone-remote, not per user;
  4. **Takes holders**, a per-token allow-list;
  5. **slug-prefix write fences**.
- **Auth:** `gbrain serve --http` is an OAuth 2.1 resource and authorization server. Scopes are `read`/`write`/`admin`/`agent`. Dynamic client registration is optional and off by default. Owner approval is required for auth-code connections. There are per-client source grants, operation snapshots and surfaces, and a redacted per-request audit log.
- **Trust model statement (vendor, verbatim intent):** "Authenticated remote clients are constrained by source and operation grants plus visibility filters. **Local files and shared database credentials are a different trust boundary: sources alone do not isolate those callers.** The authorization tests exercise specific access paths, not a universal no-leak guarantee."
- **gstack Path 1/4:** pasting a Supabase pooler URL "gives your local Claude Code full read/write access to every page in the shared brain". A remote MCP bearer token is shared by "your laptop, your desktop, and a teammate's machine". The **trust-policy triad** (`read-write`/`read-only`/`deny`) is a **per-repo, client-side** decision stored in `~/.gstack/gbrain-repo-policy.json`. The binary says it "just stores the decision": it governs what gstack *imports*, not what the server allows. The "personal vs shared" brain trust policy is likewise client-side.
- **Hazard (OBSERVED · `src/mcp/http-transport.ts`):** a legacy bearer token **with no source grant** falls to the historical `'default'` floor. On HTTP it then reads the whole *federated* source set (`localFederatedSourceIds`). A token minted without `--sources` is wider than it looks. (Measured in §5.4 P2: with federated sources, it read every source.)
- **Encryption:** the credential vault is encrypted. **No per-tenant or per-person encryption of content, embeddings or backups** (searched `src/core` for encrypt/pgcrypto/envelope; only `creds/vault.ts` and export).

### 2.7 MCP surface (OBSERVED · code)
- 182 operations: 85 read, 50 write, 43 admin, 2 agent, 2 sources_admin; 21 local-only.
- Surfaces: `verbs` (7 frozen memory verbs: `recall`, `remember`, `entity`, `synthesize`, `forget`, `context_pack`, `delta`, all at `protocol_version: 1`), `starter` (40) and `full`.
- A conformance kit lets other servers certify against MEMORY_VERBS v1.
- Lean result rows for remote callers. Evidence delivery (`return_unit`: chunk/window/section/page/auto) re-authorises every page.

### 2.8 Sync to git and gstack integration (OBSERVED)
- GBrain indexes git repos as sources (`gbrain sources add`, `gbrain sync --strategy code|markdown`). Git deletes become soft deletes. The watermark is the commit hash.
- gstack adds:
  - `/setup-gbrain` (4 paths: Supabase URL, Supabase auto-provision with **region default `us-east-1`**, PGLite, remote MCP);
  - `/sync-gbrain` (code, memory and artifacts stages, with a fail-closed **egress receipt ledger** `~/.gstack/security/egress.jsonl` hash-chained before any off-machine send);
  - artifacts sync to a private git repo, secret-scanned (AWS keys, GitHub tokens, JWTs, PEM), with privacy modes `off`/`artifacts-only`/`full`;
  - a CLAUDE.md "search guidance" block that is **removed automatically when the capability round-trip fails**.

---

## 3. Evidence: what GBrain publishes, and independent tests

### 3.1 Vendor-published evaluations (all by GBrain's author; strength = vendor)
| Claim | Conditions | Status |
|---|---|---|
| LongMemEval-S strict `recall_all@5` **95.53%** (449/470) release default; **93.40%** reranker off | cleaned S split, 470 scored, k = 5 *sessions*, OpenAI 3-large 1536-d embeddings, Voyage rerank-2.5, single run, 2026-09-06; confirmed with opaque ids 2026-10-04 | OBSERVED (report read) · vendor |
| LongMemEval-M strict R@5 **78.1%** (367/470) | 500-session haystacks | vendor |
| BrainBench (theirs) relational, P@5 0.342 / R@5 0.979 vs plain hybrid 0.192 / 0.687 | 240 Opus-generated pages, 145 relationship questions, adapter that recognises **4 question templates** and follows the fixture graph | vendor. They themselves say "not a graph-only effect… does not predict accuracy on a different corpus"; the older 49.1% headline is withdrawn |
| PrecisionMemBench: tight adaptive + rerank precision 0.586 / recall 0.825 vs broad hybrid 0.057 / 0.988 | 77 cases | vendor |
| Memory trust (paid, preregistered): labels cut attack success from 5.1–10.6% to 1.5–5%; gate and suppression add no measurable effect on top of labels; 0/360 instruction-worded attacks followed in any arm | Opus 5.5, Sonnet 5.5, GPT-6.1 Sol; 200 attack sessions per model per arm; templated attacks | vendor, preregistered |
| N6 visibility fuzz: **0 leaks / 3,854 probes**, 0 existence oracles, 0/90 access gates bypassed (after fixing an entity-card private-backlink leak found by the same fuzz) | 74 read ops × 6 caller types, public-twin and ghost controls, seeded ledger | vendor; strong design; **returned-content and existence only, no ranking or timing channels** |
| Cat 22 source isolation 8/8, 0 leaks | engine-level, 8 probes | vendor, small |
| Fact supersession threshold dev: 46.7% corrections missed at voyage-4 0.95; 3-large has no working threshold | C2 fixture, 240 correction probes | vendor, **negative result published** |
| `think` date frame +14.0 pts held-out LoCoMo | 1,399 paired questions | vendor, preregistered, sealed |

**How they measure retrieval:** strict all-gold-in-top-k on public datasets (LongMemEval `recall_all@5`, the same shape as our CR@k_all, but k is *sessions*, not items), plus template corpora they generated. Preregistration, sealed splits, published losses and recount receipts are present: methodologically above average. The **gold sets are generator-derived** (their in-repo BrainBench uses "the same PRNG step that authors a turn authors its annotation"). That is our approach too, and it has the same circularity limit.

### 3.2 Independent evidence (bounded search: web search on 3 queries, 4 articles fetched, 2026-10-23)
- **No independent reproduction of any GBrain number exists** (explainx.ai, 2026-09-01: "No third party has reproduced these numbers"). [anecdote/commentary]
- Slite review (vendor competitor, code read only, no run): "does almost nothing to keep it true"; "no real permission model… largely remains a single-player tool… has since added scoped multi-user access". [secondary, conflicted]
- Vectorize review (sells Hindsight, a competitor; code and docs read, not run): multi-tenant readiness 1/5, integration breadth 2/5, maturity concerns (frequent breaking changes, npm-squat footgun). [secondary, conflicted]
- Adoption signals: the author's own deployment (155,795 pages, self-reported), a hosted product (gbrain.io, hosting region **not stated** on the home page), plugins for Hermes/OpenClaw/Codex/Claude Code. [anecdote]
- Not found: academic evaluation, security audit, CVE against gbrain itself. Search returned unrelated CVEs. Bounded: did not search Discord or X threads.

**Our sandbox run (§5) is, as far as I found, the first independent measurement of GBrain retrieval on a corpus it was not tuned on.** It is synthetic and one seed.

---

## 4. Point-by-point comparison with our design

Legend: **G+** GBrain better or simpler · **O+** ours stronger · **≈** equivalent · **✗** GBrain fails our standard.

| Area | GBrain | Ours (charter, ADRs) | Verdict |
|---|---|---|---|
| Store | Postgres/PGLite, one store, pgvector HNSW, tsvector | Postgres system of record (ADR-003, being narrowed to SoR plus a possibly separate index) | ≈. GBrain proves the single-Postgres stack works at 155k pages for one owner. **G+** PGLite↔Postgres parity is a real operational gift for staging (home PC → server) |
| Exact vs ANN | HNSW default; iterative scan with relaxed order; reports `vector_pool_underfilled` | Exact search ≤100k per partition (ADR-004, R5) | O+ for recall under filters; G+ for honesty about shortfall (degraded flags) |
| Memory item | Page (compiled truth + timeline) + facts + takes + typed links | Append-only episodes + bi-temporal typed facts + typed records + mentions (ADR-008) | O+ on keyed state (one current row per key, enforced). **G+** on the human-readable page as the unit agents and owners actually edit. Takes (multi-holder beliefs with weight) are a concept we lack |
| Write path | Markdown import; LLM facts extraction on by default; dream cycle rewrites compiled truth | Path A keyed upsert, no LLM; Path B planner with review; write gate (ADR-009/011) | O+ (deterministic keyed path). GBrain has no keyed connector upsert for state; everything is text |
| Supersession | `supersedes` link → 0.5× rank; facts by caller `replaces` or calibrated cosine; **47% of corrections missed** (own eval) | Keyed supersession in one transaction, forward-to-head at read time, mention linking (ADR-008/009); E1 0.0% stale versions keyed | **✗ GBrain** for the ≤2% stale constraint (and see §5 stale probes) |
| Time | valid_from/until on facts, temporal edges, page effective_date, **known-as-of pages from a belief ledger**, date frame in reader | Bi-temporal facts, as-of and known-at (ADR-008, I13) | ≈ in ambition; **G+** the date frame in the reader prompt is cheap, measured (+14 pts), and we have not specified it |
| Hybrid first stage | vector + ts_rank keyword + title + alias + relational, RRF k = 60, source boosts | BM25 + dense, RRF untuned → convex tuned per class (ADR-005) | **O+ (measured).** GBrain is −5.6 pp CR@10 vs our wsum and −3.8 pp vs bge-small cosine alone, same embedder, reranker off (§5.3). Losses are on current_state and multimodal. **G+** title/alias arms, evidence stamps and `create_safety`; possible pref gain as the fill after cards (GB9). Its `ts_rank` has no cross-partition IDF channel |
| Reranker | Hosted Voyage default; fail-open; measured +2.1 pts LongMemEval | Local cross-encoder, per-class gate (ADR-017) | O+ for residency; ≈ in mechanism. **G+** "relational re-pin" (edge answers survive reranker demotion), a real failure mode we have not designed for |
| Context assembly | Facts arm in spare capacity; entity anchoring (off); token budget; evidence delivery by unit | Entity cards pinned first, router, CR@T (ADR-010) | O+ (cards measured +12.3 pp). GBrain's entity anchoring is the same idea, gated off pending its own gate 3 |
| Aggregation / find-all | `list_pages` enumeration; explicitly "search is not proof of coverage" | Routed to computation over keyed facts (ADR-013) | O+ in design; ≈ in honesty |
| Access model | Brain (DB) ⊃ source ⊃ private page (owner vs all remote) ⊃ takes holders | Tenant DB ⊃ ACL group per row ⊃ vaults with keys owner lacks ⊃ shared spaces as views with consent ledger; per-hop checks; fail closed (ADR-007, charter §3e) | **✗ GBrain** for our partitions. No per-user visibility inside a source, no vaults, no consent ledger, no couple/member-trainer spaces. Owner and local CLI see everything, including members' health data. The "private" flag is binary |
| Leakage testing | N6 fuzz on returned content and existence (0/3,854); Cat 22 | Twin-world noninterference as certification gate (DA3); canaries as smoke alarm | **G+** N6's public-twin plus ghost design is better engineered than our canary monitor and runs over every op automatically. O+ noninterference covers ranking and timing channels; N6 does not. Our probes: 0 returned rows from ungranted sources in 240 probes plus 790 benchmark tasks with correct grants; the no-grant default token read everything (§5.4 P2) |
| Cross-partition statistics | ts_rank (no IDF): E4 channel absent in the keyword arm. But HNSW graph, `pg_stats` OR-fallback narrowing, page-generation clock and backlink/salience are global or partly global | No statistic over unseen rows (ADR-006, reframed as noninterference) | **G+ (measured, list level).** Twin-world X1: 0 of 112 visible lists or scores changed after 20, and then 200, hidden owner notes were embedded into the shared HNSW (§5.4). That is better than our batch-2 BM25, whose global IDF leaks. Timing not tested. GBrain's semantic cache is hard-disabled at this commit; if re-enabled, its global page-generation clock would turn any hidden write into a cache flush for every caller, a latency channel (INFERRED) |
| Untrusted sources | Trust tiers on every row; external content wrapped as data; gate defaults flag (not quarantine) after paid eval | T0–T4, readers of untrusted content cannot write; candidates quarantined (ADR-014) | **G+** they *measured* that labels carry the protection (and published it). O+ our quarantine is the conservative default the charter demands (≤1% poisoning served as trusted). ✗ against charter principle 12 as shipped (defaults) |
| Egress classes | Egress receipt ledger (gstack); "where text goes" doc; no per-client egress classes; hosted embedders by default | Egress classes per client; local embedding and reranking for every partition (charter §3f, §6.2) | ✗ GBrain defaults. ≈ capability: the llama-server/Ollama recipes make it local (we ran it fully local) |
| Hosting / residency | PGLite local or Supabase (gstack default `us-east-1`); gbrain.io hosting region not stated | Self-hosted GPU server in Australia | ✗ defaults; fixable by config (self-host Postgres in AU). INFERRED |
| Erasure | forget = expire; purge = owner-only, text-free tombstone, receipts, rederive marks; backups not purged | Crypto-shredding per person (ADR-008 pending), APP 11.2 backups | ≈ in mechanism (purge receipts are good); O+ in requirement (backups) |
| Eval discipline | Preregistration, sealed splits, published negatives, receipts, CI gates on retrieval and leak metrics | ADR-018 certification (Clopper-Pearson, three-group audit) | ≈. **G+** they *operate* it: every memory PR must move or hold a BrainBench number |
| Interface | MCP stdio/HTTP, OAuth 2.1, 7 frozen verbs + conformance kit, lean rows | MCP remote HTTPS, OAuth 2.1, small tool set (ADR-002) | **G+** the frozen verb protocol and conformance kit are exactly the client-agnostic contract we want; adopt the idea |
| Ops maturity | 266 migrations, crash robot, doctor with fix commands, CI shards | Not built | G+ by a mile (but also: 893 KB TODOS, 4.4 MB CHANGELOG, breaking changes weekly) |

---

## 5. Test: GBrain on BrainBench v0.2

### 5.1 Method (OBSERVED · our sandbox run, 2026-10-23)

**Feasibility.** GBrain runs fully locally:
- Bun 1.4.2 was already installed. Install was `bun install --frozen-lockfile --ignore-scripts`: 281 packages, no postinstall run, after reading `scripts/postinstall.ts`.
- PGLite file database; no Supabase, no hosted provider, no API key.
- Embeddings through GBrain's own **`llama-server` recipe** (OpenAI-compatible `/v1/embeddings`), pointed at a 60-line local server running **bge-small-en-v1.5** on CPU. This is the same embedder as our batch-2 best first stage.
- The query instruction is set through GBrain's `embedding_query_prefix` config key, using bge's official query prefix. Documents are embedded with GBrain's own `title` contextual wrapper (`balanced` default).

**Configuration under test.** GBrain v0.60.398.0, `search.mode = balanced` (the release default), with three overrides:
1. **reranker off** (the default is hosted Voyage; this equals GBrain's own "like-for-like A1" row);
2. **facts extraction off** (paid hosted Haiku);
3. no dream cycle.

Everything else is shipped behaviour: hybrid vector + `ts_rank` keyword + title + alias + relational arms, RRF k = 60, source boosts, intent classifier, dedup, supersede down-rank, facts arm, evidence stamps.

**Data mapping.** BrainBench v0.2 seed 1: 10,869 items, 48 partitions.
- One **GBrain source per partition**; one **page per item**: frontmatter `title` (item title, or first sentence), `type: note`, `date: <item date>`; body = text + media origin context (as batch 2).
- All fact versions are imported as pages, because GBrain has no keyed-fact path for connector values.
- 10,869 chunks embedded. Build time on 2 shared vCPUs: about 56 ms/page import, about 5–11 chunks/s embedding.
- The first full-batch import was OOM-killed at about 3.8k pages (another experiment held 3 GB). It was resumed in 1,500-page batches per process (`build.ts` is resumable).

**Access.** Every task runs through GBrain's real **`search` operation** (`operations.find(name=='search').handler`) as a **remote caller** (`remote: true`, `transport: 'http'`). The OAuth `auth.allowedSources` is set to exactly the requester identity's partitions. This is the code path `gbrain serve --http` uses after token verification. It enforces GBrain's source isolation, private-page filter, safe chunks and lean-row redaction.

**Tasks.** A stratified subset: for each of the 8 classes, 80 distinct required sets (one task per set, seeded), plus 150 stale probes, for 790 tasks in total. Limit 100 results per search. This is smaller than batch 2's all-tasks run because of the CPU budget (about 3–5 s per search on PGLite under load). Batch-2 comparators are re-read from `results_v02/e8a.pkl` / `e8c.pkl` **for exactly the same task ids** (paired).

**Metric.** As batch 2:
- CR@k = every required item in the top k;
- mean over distinct required sets, Wilson 95% with n = distinct sets;
- paired exact sign test over sets, with a cluster-bootstrap CI.
- k = 10, 20, 50, 100.

**Arms scored.**

| Arm | What it is |
|---|---|
| **GB hybrid** | GBrain as shipped (minus hosted reranker / extraction), raw top-100 |
| **GB keyless** | Same brain, no embedding provider: GBrain's "start keyless" keyword + title path. Run on a 40-sets-per-class subset (371 tasks) because of CPU |
| **GB hybrid, keyed** | GBrain ranking, then batch-2 store semantics applied post hoc: superseded fact versions dropped for non-temporal queries (what batch 2's `live_mask` does). Isolates "GBrain lacks keyed supersession" from "GBrain ranks worse" |
| **GB hybrid + our cards** | Our batch-2 `cards(≤3)` prefix (lexical linker, ACL-checked) pinned in front of GBrain's keyed ranking. Asks: is GBrain's ranker a usable fill for our assembly? |
| B2 BM25 / bge-small dense / rrf / **wsum = query-only** / **cards(≤3)+query** / cards+slots+query | our batch-2 arms on the same tasks |

**Threats to validity.**
1. Synthetic templated world, one seed, 80 sets per class (CIs about ±10 pp).
2. bge-small instead of GBrain's default Voyage-4 or OpenAI-3-large. This helps comparability with batch 2; GBrain may do better with its native embedder.
3. The reranker is off. GBrain measured +2.1 pts with Voyage on LongMemEval; our E8b found +3.6 pp for Qwen3-Reranker at depth 50.
4. Every page is `type: note`, so type-based boosts and the dedup type cap are inert.
5. Items are one-chunk pages, so GBrain's page-level max-pool and evidence delivery are neutral.
6. No dream cycle, no compiled-truth rewriting, no extracted facts or takes. These are GBrain's main freshness mechanisms, but they need a hosted or local LLM and an always-on host. GB2 therefore measures GBrain's *retrieval-time* supersession only.
7. Batch-2 numbers were computed with exact NumPy search; GBrain uses HNSW (ef_search ≥ 40, iterative scan).
8. **A shared, loaded host.** Another experiment held 1–3 GB and up to 1.5 CPUs throughout.
   - GBrain's 6 s query-embed deadline was hit at least 3 times. Each time it silently salvaged the search keyword-only.
   - The local embedding server was restarted once, about 40 s down. The affected multimodal class was rerun in full.
   - A sensitivity analysis on the 540 tasks under 6 s (§5.3) gives the same conclusions.
9. The semantic query cache was not a factor: the semantic result cache is **hard-disabled in code at this commit** (`semanticResultCacheAvailable()` returns `false` in `src/core/search/query-cache.ts`: "Stored semantic responses are unavailable until all response dependencies can be revalidated"). The `search.cache.enabled` config key is still read, but nothing is stored or served; `query_cache` stayed at 0 rows in every probe DB.

### 5.2 Stale facts (GB2): GBrain serves superseded values as current

150 stale probes (distinct keys, owner and partner requesters). E1 definitions, top-10, same world. "Ours" uses batch 2's first stage `wsum(BM25+bge-small, α=0.2)` with the same probes.

| Arm | Stale version above current | Stale-quoting note above current | Current value not in top-10 | **First value-bearing item is stale** |
|---|---|---|---|---|
| **GBrain as shipped** (hybrid, balanced, no reranker) | **45.3% [37.6–53.3]** (68/150) | 46.7% [38.9–54.6] | 39.3% [31.9–47.3] | **58.1% [49.3–66.4]** (72/124) |
| GBrain ranking + our keyed store (superseded versions not live) | 0.0% [0–2.5] | 46.7% | 34.7% | 42.7% [34.4–51.5] |
| Ours, add-only (every version live) | 47.3% [39.5–55.3] | 35.3% | 30.7% | 57.3% [48.5–65.6] |
| **Ours, keyed** (batch-2 default) | **0.0% [0–2.5]**, one-sided CP95 upper 2.0% | 37.3% | 25.3% | 37.2% [29.4–45.8] |

Reading:
- **GBrain behaves exactly like our add-only arm** (45 vs 47% stale versions; 58 vs 57% first-value-stale). Its recency, intent and source-boost machinery does not change that, because:
  - the recency boost fires only on explicit cues ("latest", "currently", "right now"); 0 of 3 typical probe phrasings tested carried one;
  - `supersede` down-ranking needs explicit `supersedes` links, which no ingest path writes for connector values.
- Typical failure (OBSERVED, probe "who's the lead on coffee at the café?"): GBrain's top 3 were two chats naming the *old* head barista, then the superseded fact version. The current fact was 4th. Far from the ≤2% bar.
- Keyed supersession (our ADR-008) removes the version-level error **by construction**, both under GBrain's ranker and ours. The stale-*note* problem (35–47%) remains for both. That is our known open item (N1 mention forwarding; batch 1 cut traps to 0.7% with simulated 90% extraction recall).
- **GB2: supported.** GBrain as shipped fails the ≤2% stale constraint by a factor of about 20–30. Caveat: no dream cycle ran. GBrain's answer to this is LLM-rewritten compiled-truth pages plus fact supersession. Its *own* measurement of the fact path (47% of corrections missed at the best cosine threshold, §2.5) says that would not close the gap either. The GPU package tests it after 2 simulated weeks of cycles.

### 5.2b Best case for GBrain: a perfect operator writes every `supersedes` link

On a copy of the brain, we wrote 1,779 `supersedes` links, one from every newer keyed-fact version to every older one in the same source. This is what an ideal agent or operator would maintain. GBrain then multiplies each superseded page's final score by **0.5** (`SUPERSEDE_PENALTY`, applied last, after all boosts) and stamps `superseded_by`.

| Arm (top-10) | Stale version above current | Stale-quoting note above current | Current value missing | First value-bearing item stale | CR@10 current_state |
|---|---|---|---|---|---|
| GBrain as shipped | 45.3% | 46.7% | 39.3% | 58.1% | 57.5% |
| **GBrain + perfect supersedes links** | **0.0%** [0–2.5] | 47.3% | 34.0% | 43.2% [34.8–52.0] | 63.7% |
| Ours, keyed | 0.0% [0–2.5] | 37.3% | 25.3% | 37.2% [29.4–45.8] | 75.0% (query-only) |

Reading:
- **Given perfect links, GBrain's page-level supersession is as effective as our keyed store on version errors.** A 0.5× penalty was always enough to drop the old version below the current one on these probes. That is a fair point in GBrain's favour: the mechanism exists.
- **The links are the whole problem.**
  - No GBrain ingest path writes them for connector values.
  - Its fact-level supersession misses 47% of corrections (own eval).
  - A 0.5× multiplier is a soft rank penalty, not removal. A superseded page with twice the score of the current one still wins. It held here because every version shares a near-identical template.
- With links, GBrain still trails our keyed arm by 8.7 pp on current-value-missing and 6 pp on first-value-stale. Its stale-*note* rate (47%) is higher than ours (37%). These residuals come from ranking and from notes quoting old values, not from version handling.
- **The links break history (measured).** The supersede stage has no intent gate in code (`stampSuperseded` applies the 0.5× penalty to every result, on every query). On the 80 temporal_change sets, where the old versions *are* the required items:

  | Temporal tasks (80 sets) | CR@10 | CR@20 | CR@50 | CR@100 | Item recall@10 |
  |---|---|---|---|---|---|
  | GBrain as shipped | 57.5% | 77.5% | 86.2% | 88.8% | 66.1% |
  | **GBrain + perfect supersedes links** | **2.5%** | **2.5%** | **2.5%** | 88.8% | 30.2% |
  | Ours, keyed (history visible to temporal queries) | 57.5% (query-only) | 76.2% | 86.2% | 90.0% | – |

  Paired: −55 pp vs our query-only at CR@10 (0 better / 44 worse, p = 1e-13). At k ≤ 50 the old versions are pushed below the cutoff almost every time.
- So GBrain offers a trade-off, not a fix: **either stale current-state answers (no links) or broken history (links)**.
- Our ADR-008/009 design avoids this by construction: keyed state with valid_from/valid_to, `live_mask` for non-temporal queries, and history visible to temporal ones. This is the strongest measured argument in this review for keyed bi-temporal state over page-level supersession. It is also a warning for us: our temporal routing (TEMPORAL_RE) must stay accurate, because the same failure appears the moment it misroutes.
  - Measured on this subset: 75 of 80 temporal tasks routed temporal (6% miss), and 19 of 710 others misrouted temporal (2.7%).
  - The template-matched regex is a benchmark artefact; a real router will be worse. This belongs in H-series routing work.

### 5.3 Retrieval: CR@k per class (GB1)

**Setup.** 790 tasks: 80 distinct required sets per class plus 150 stale probes. Seed 1. Paired against batch-2 arms on the same task ids. Wilson 95% intervals; n = distinct sets.

**CR@10 (%)**

| Arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| **GB hybrid** (as shipped) | 0.0 | 2.5 | **57.5** [47–68] | 57.5 | 3.8 | 6.2 | 0.0 | **67.5** [57–77] | **24.4** [21–28] |
| GB hybrid, keyed | 0.0 | 6.2 | 63.7 | 52.5 | 7.5 | 6.2 | 0.0 | 72.5 | 26.1 |
| **GB hybrid + our cards** | 11.2 | 15.0 | 97.5 | 51.2 | 38.8 | **21.2** [14–31] | 1.2 | 71.2 | **38.5** [35–42] |
| B2 BM25 | 0.0 | 1.2 | 47.5 | 45.0 | 8.8 | 6.2 | 1.2 | 73.8 | 22.9 |
| B2 bge-small dense (same embedder) | 0.0 | 3.8 | 68.8 | 55.0 | 7.5 | 6.2 | 0.0 | 83.8 | 28.2 |
| **B2 wsum = query-only** (our first stage) | 0.0 | 3.8 | **75.0** [65–83] | 57.5 | 8.8 | 5.0 | 1.2 | **88.8** [80–94] | **30.0** [27–34] |
| **B2 cards(≤3) + query** (our assembly) | 10.0 | 17.5 | 98.8 | 55.0 | 43.8 | 11.2 [6–20] | 2.5 | 87.5 | **40.8** [37–45] |
| B2 cards + slots + query | 18.8 | 17.5 | 100.0 | 32.5 | 42.5 | 11.2 | 6.2 | 76.2 | 38.2 |

**Larger budgets, ALL classes (CR %).** Multimodal is in brackets.

| Arm | @20 | @50 | @100 |
|---|---|---|---|
| GB hybrid | 31.3 (76.2) | 37.6 (81.2) | 45.9 (91.2) |
| GB hybrid + our cards | 43.0 (77.5) | 49.2 (83.8) | 54.4 (91.2) |
| B2 bge-small dense | 33.4 (87.5) | 41.7 (90.0) | 49.5 (96.2) |
| B2 wsum = query-only | 35.3 (90.0) | 44.5 (93.8) | 52.4 (97.5) |

Item recall@10 / @100, ALL: GB hybrid 42.4 / 70.0; GB + cards 65.8 / 77.7.

**Paired tests at CR@10** (exact sign test over distinct sets; Δ = GB − ours, cluster-bootstrap 95% CI):

| Comparison | ALL | Significant classes |
|---|---|---|
| GB hybrid vs **our query-only** | **−5.6 pp** [−7.8, −3.4], 10 better / 46 worse, p = 1e-6 | current −17.5 (p = 5e-4); multimodal −21.2 (p = 8e-5); the other six classes tie (decision, cross and goal are at the floor for both) |
| GB hybrid vs **bge-small dense alone** | −3.8 pp [−6.0, −1.7], p = 0.001 | current −11.2; multimodal −16.2 |
| GB hybrid, keyed vs our query-only | −3.9 pp [−6.0, −2.0], p = 1e-4 | current −11.2; multimodal −16.2 |
| GB hybrid vs our cards + query | −16.5 pp, p = 3e-24 | every class except temporal, pref and cross |
| **GB + our cards** vs our query-only | **+8.5 pp** [+5.3, +11.6], p = 2e-7 | current +22.5, goal +30, pref +16, decision +11, option +11; multimodal −17.5 |
| **GB + our cards** vs **our cards + query** | **−2.4 pp** [−4.5, −0.2], 18 better / 33 worse, p = 0.049 | **pref +10.0** (8 better / 0 worse, p = 0.008); **multimodal −16.2** (p = 0.001); the rest are ties |

**Leakage in the benchmark run:** 0 returned rows from ungranted sources across 790 tasks × top-100.

**Latency:** p50 4.2 s, p95 9.8 s per `search` on PGLite (WASM), 10.9k pages, 2 shared vCPUs. This is not comparable with batch 2's in-memory NumPy ranking.

**Reading.**
1. **GB1 is contradicted.** GBrain as shipped (reranker off, same embedder) is **5.6 pp below our query-only first stage** and **3.8 pp below plain bge-small cosine** on CR@10. Its fusion stack subtracts on this corpus. The losses concentrate in two classes:
   - **current_state.** Examples (OBSERVED):
     - "What program have I been given?": five "Booked … class" logs ranked first; the keyed fact was 65th.
     - "What were my latest numbers?": "Checked in at 6:31am" logs first; the fact was 12th.
     - "Weekly income from Nettle Rd": the right value appears in a note at rank 1, but the keyed fact is 24th.
     - Mechanism (INFERRED, not ablated): `ts_rank` has no IDF and the title arm gets first-sentence titles. Together they favour short, repetitive logs. RRF k = 60 then flattens the vector arm's preference for the fact.
   - **multimodal.** Generic image captions ("pic", "photo close-up") and job-site chats outrank the specific defect photo. Example: "sagging gutter … 3 Marram Drive" put the target image at rank 54.
2. **The keyed transform helps GBrain.** It adds +6 pp on current and +5 pp on multimodal. Stale versions crowd its lists just as they crowd ours in add-only mode.
3. **Our cards rescue GBrain's ranker.** With the card prefix in front, GBrain lands within 2.4 pp of our assembly overall. This repeats batch 2's lesson: **structure, not the ranker, carries current, goal, decision and option**. No first stage (ours or GBrain's) gets above 9% on decision, option or goal at k = 10.
4. **One GBrain win worth chasing: pref +10 pp** (8 better / 0 worse) when used as the fill after cards.
   - In 7 of the 8 winning cases (inspected without the keyed drop; 5 member requesters, 2 owner), GBrain placed the requester's **own short preference note** at ranks 4–9 below the public class list. Our wsum missed it in the top 10. Examples: "Bad knees, needs low-impact … Evenings only"; "First time in a gym, a bit intimidated…".
   - GBrain's raw pref CR@10 (6.2) is no better than ours (5.0). The gain only shows once the card fills the other required slot.
   - Mechanism UNKNOWN. Candidates: GBrain's title-match arm on untitled items, RRF over 4–5 arms instead of our two-arm wsum, or per-page dedup. Recorded as **GB9**.
5. **Larger budgets don't change the order.** GB hybrid trails our query-only by 4–7 pp at k = 20, 50 and 100, and still misses about 9% of multimodal sets at k = 100.

**Robustness checks.**
- **Embedding-server outage.** The local embedding server reached its background time limit at 23:29:58 and restarted about 40 s later. GBrain's response was to **silently** salvage the affected searches keyword-only: one warn-once log line, no error in the result (the `degraded` stamp exists in `meta`, but MCP clients see it only when they read meta).
  - All 80 multimodal tasks were rerun with the server up; the tables use the rerun.
  - In the rerun, 11 of 80 lists differed: 6 inside the outage window and **5 outside it**. INFERRED cause: GBrain's time-budgeted vector walks (2 s index-walk budget, statement-timeout fallback) make results **load-dependent** on a busy host.
- **Possible embed timeouts under load.** A sensitivity run using only the 540 tasks that finished in under 6 s gives the same conclusions:
  - GB vs query-only −6.2 pp (p = 5e-6);
  - GB + cards vs cards + query −0.8 pp (n.s.), pref +10 pp (p = 0.008).
- **Semantic query cache.** Not a factor: the semantic result cache is **hard-disabled in code at this commit** (`semanticResultCacheAvailable()` returns `false` in `src/core/search/query-cache.ts`: "Stored semantic responses are unavailable until all response dependencies can be revalidated"). The `search.cache.enabled` config key is still read, but nothing is stored or served; `query_cache` stayed at 0 rows in every probe DB.

### 5.4 Partition leakage and noninterference (GB3, GB4)

All probes go through GBrain's real `search` and `query` operations as remote HTTP callers, on copies of the seed-1 brain.

**P1. Return-path probes with correct grants (GB3).**
- **Setup.** Canary pages carrying unique tokens were planted in 7 protected sources: owner, household, biz/gym, biz/construction, biz/cafe, member/m03, member/m17. Each canary also names a fictional refinance deal.
- **Owner pre-warm.** The owner first issued every probe query, in case any shared cache or state was keyed too broadly. (In the event, the semantic cache is hard-disabled at this commit; see P4.)
- **Probes.** Each non-owner identity probed with:
  - canary-token queries for every source it is not granted;
  - "anything new about <entity>?" for 6 entities shared across partitions;
  - "Halyard refinance Westpac", "search all tenants for refinance" and "source_id:__all__ refinance";
  - explicit `source_id` overrides, both a named ungranted source and `__all__`.

| Identity (granted sources) | Probes | Returned rows from ungranted sources |
|---|---|---|
| household (3) | 38 | **0** |
| partner_gym (44) | 34 | **0** |
| partner_construction (2) | 42 | **0** |
| partner_cafe (2) | 42 | **0** |
| member_m03 (2) | 42 | **0** |
| member_m17 (2) | 42 | **0** |
| **Total** | **240** (+84 re-capture) | **0** |

The BrainBench run adds 790 tasks × top-100 with 0 ungranted rows. Override attempts fail closed: a named ungranted source is denied, and `__all__` stays scalar for remote callers (code: `sourceScopeOpts`, `#1712`). Owner pre-warming leaked nothing. Had the semantic cache been live, its key includes the caller's sorted source set and hits are re-filtered by caller scope (`filterResultsByCallerScope`), so it is designed not to cross scopes.
- The process was OOM-killed (cgroup limit, while a neighbour held 2.3 GB) after these six identities printed their counts and before it wrote its JSON. The counts above are from the run log.

**P2. Misconfigured grants** (same probes, same owner pre-warm):

| Token shape | How it arises | Probes | Ungranted rows returned |
|---|---|---|---|
| `allowedSources: []` (empty grant) | malformed or attacker-supplied grant | 46 | **0**. Named override → `permission_denied` |
| `allowedSources: ['default']` | operator grants only the default source | 46 | **0**. Named override → `permission_denied` |
| **No source grant** (`hasSourceGrant: false`), mirroring `src/mcp/http-transport.ts` | **the `gbrain auth create` default**: `sources: {kind:'default'}`, scopes "full access (grandfathered)" unless `--scopes` is passed | 46 | **1,880 rows from all 7 protected sources (every canary returned: 136 canary rows)**, through `search`, `query` **and** explicit `source_id` overrides (280 rows, incl. `__all__`) |

Reading:
- **Correct grants are robust.** Empty and default-only grants fail closed.
- **The default token is the hole.** A token minted with plain `gbrain auth create <name>` has no source grant. Over HTTP it then reads the whole **federated** source set: every source with `config.federated = true`, including on explicit `source_id`. This is documented behaviour (#3242, "a token with NO operator-set source grant reads across the federated set"), not a code bug.
- **It bit here because this test created all 48 sources `federated: true`.** An owner would do the same to get unqualified cross-source search; GBrain's own architecture doc shows its canonical brain with most sources federated, and github/google mirrors default to federated.
  - Had the sources been left unset (the plain `sources add` default), the no-grant token would have read only `default`, which is empty in this brain.
- **Verdict for GB3: supported, with the condition stated.** No returned-content leak with a correct grant. But the **default** token shape plus a common source setting silently grants everything, and nothing at mint time warns about it.
- Our charter requires fail-closed defaults (principle 8). The borrowable lesson is the opposite design: **a token with no explicit grant must read nothing**.
- Re-captured with full JSON for partner_cafe and member_m17 (84 probes): **0 ungranted rows**. A named ungranted `source_id` returns `permission_denied`. `source_id: __all__` returns no error and no foreign rows: it stays scalar for remote callers.

**P3. Twin-world noninterference, X1 (GB4).**
- **Worlds.** W is a copy of the seed-1 brain. W′ is W plus 20 hidden owner-source notes on a "Halyard refinance" topic. The notes were imported and **embedded into the same HNSW index**, which was verified.
- **Replay.** 7 non-owner identities (household, the three partners, members m03, m17 and m28) each replayed up to 10 of their own task queries plus 7 topic probes ("Halyard refinance", "refinance loan bank", "divorce lawyer", …). That gives 112 observations, with the semantic cache off so that cached rows cannot mask the index.
- **Control.** W was replayed twice.

| Comparison | Lists changed | Set changed | Queries with any score delta | Max abs score delta | Owner rows visible |
|---|---|---|---|---|---|
| W vs W (repeat, noise control) | 0 / 112 | 0 | 0 | 0 | 0 |
| **W vs W′** (+20 hidden notes) | **0 / 112** | 0 | **0** | **0.0** | **0** |
| W_a vs W_a (repeat), after ANALYZE | 0 / 112 | 0 | 0 | 0 | 0 |
| **W_a vs W′_a** (+200 varied hidden notes on 12 topic words, then ANALYZE) | **0 / 112** | 0 | **0** | **0.0** | **0** |
| W vs W_a (ANALYZE alone) | 0 / 112 | 0 | 0 | 0 | 0 |

Reading:
- On this probe set GBrain is **noninterfering at the ranking level**: identical ids, order and scores to full float precision.
- The mechanisms are visible in code:
  - `ts_rank` has no corpus statistics (no IDF), so hidden documents cannot shift keyword scores;
  - vector scores are pure cosine;
  - RRF uses only within-list ranks;
  - source filtering is applied inside the SQL before fusion, so hidden rows never enter the fused lists;
  - HNSW with iterative scan (`hnsw.iterative_scan`) refills past filtered-out neighbours.
- This is **stronger than our own batch-2 baseline**, where BM25's global IDF is a known E4 leakage channel (DA3 X1 found it).
- Limits:
  - the probe set is small;
  - timing was not measured;
  - HNSW graph changes can in principle alter which neighbours an approximate walk finds, and planner statistics change with ANALYZE. The 200-note + ANALYZE run tested the latter: still 0 changes.
- **GB4 as worded (GBrain fails noninterference) is contradicted on this probe set.** That is useful evidence for our ADR-006 question: a shared HNSW with in-SQL partition filtering *can* be noninterfering at the list level. It does not certify timing channels.

**P4. Semantic query cache and freshness.**
- **The risk examined in code.** The cache would have a TTL of 3,600 s and a cosine threshold of 0.92. A cached row stays valid unless the global page clock moved *or* a page in the cached result changed.
- **Not testable at this commit.** The cache is **hard-disabled in code at this commit** (`semanticResultCacheAvailable()` returns `false` in `src/core/search/query-cache.ts`: "Stored semantic responses are unavailable until all response dependencies can be revalidated"). The `search.cache.enabled` config key is still read, but nothing is stored or served; `query_cache` stayed at 0 rows in every probe DB. Our cache-freshness probe (12 queries, a correction page inserted, then repeated) therefore measured the uncached path:
  - the new page appeared in 4 of 12 repeats, in all 4 cases where a cache-bypassed control also surfaced it;
  - this is a sanity check, not a cache test.
- **Design note (code, INFERRED).** If re-enabled, Layer 1 (the global `page_generation_clock_seq`) advances on *every* page write, so any write would invalidate every cached row. That is safe for freshness, but any hidden write would become a visible cache-miss latency change for every caller (borrow item 14).

### 5.5 Keyless mode (no embedding provider)

GBrain's documented "start keyless" path is keyword (`ts_rank`), title and alias arms only. It was run on a 40-sets-per-class subset (371 tasks).

**CR@10 (%), 40 sets per class (n = 40–51), same task ids for every arm**

| Arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| **GB keyless** (keyword + title + alias) | 0.0 | 0.0 | 60.8 | **70.0** [55–82] | 2.5 | 5.0 | 0.0 | **52.5** [37–67] | **25.1** [21–30] |
| GB hybrid | 0.0 | 2.5 | 62.7 | 55.0 | 2.5 | 5.0 | 0.0 | 72.5 | 26.3 |
| B2 BM25 | 0.0 | 0.0 | 56.9 | 42.5 | 10.0 | 5.0 | 0.0 | 75.0 | 24.8 |
| B2 wsum = query-only | 0.0 | 5.0 | 78.4 | 55.0 | 7.5 | 5.0 | 0.0 | 90.0 | 31.7 |

**ALL at larger budgets:**

| Arm | CR@20 | CR@50 | CR@100 |
|---|---|---|---|
| GB keyless | 30.5 | 39.0 | 49.8 |
| GB hybrid | 33.2 | 39.0 | 47.4 |
| B2 BM25 | 29.3 | 39.0 | 41.7 |
| Ours | 36.6 | 44.7 | 53.2 |

**Paired tests:**
- Keyless vs hybrid: 22 better / 26 worse, p = 0.67 overall.
- By class: hybrid wins multimodal (9 vs 1); keyless wins temporal (12 vs 6); current is even (8 vs 9).
- Keyless vs our query-only: −6.6 pp (p = 0.003).

**Stale probes (n = 40):** keyless puts the stale version above current in 50%, and its first value-bearing item is stale in 76%.

**p50 latency:** 5.5 s. That is *slower* than hybrid on this host, because the keyword path does the counting and OR-fallback work.

Reading:
- **Adding GBrain's vector arm buys about nothing overall** on this corpus (+1.2 pp, n.s.). It helps multimodal (captions) and hurts temporal: history queries do better with keyword ranking than with RRF-fused cosine.
- GBrain's keyless keyword path (`ts_rank` + title + alias) is about equal to our BM25 at k = 10, and better at k = 100 (49.8 vs 41.7).
- Its fusion layer is the weak point, not its keyword arm. This is consistent with §5.3: its hybrid is below plain bge-small cosine.

### 5.6 What could not run here, and the design for the GPU validation package

Not run here, with the reason for each:
1. **The reranker.** GBrain's default is hosted Voyage (no key, and offshore). Its local alternative is the `llama-server-reranker` recipe. A local Qwen3-Reranker-0.6B at depth 25–50 on 2 shared vCPUs would add about 5–10 s per query, roughly 2–3 h for the subset, and the CPU is shared with another experiment.
2. **GBrain's default embedders** (Voyage-4 1024-d or OpenAI-3-large): both hosted.
3. **The dream cycle, facts extraction and takes.** These need a chat LLM (hosted Haiku by default), and the cycle needs an always-on host. Without them, GBrain's freshness mechanism is retrieval-time only.
4. **Seeds 2 and 3, and the full 6.5k-task set.** CPU time: about 3–6 s per search under load.
5. **The `query` op (facts arm) as a benchmark arm.** The facts table is empty without extraction, so `query` would equal `search` plus nothing. It was used only in the leak probes.
6. **Timing side channels.** These need an idle host, and ours shared its CPU.

**Reproduce this review's run.** Scripts are copied to `/home/claude/vendor-skills/analysis/gbrain-harness/`. Run outputs stay in the scratchpad (`.../scratchpad/gbt/`). Paths inside the scripts point at the scratchpad and the vendor clone; edit `GB` and `D` to relocate.
1. `python3 -I embed_server.py 8089` starts a local OpenAI-compatible bge-small server.
2. `bun --smol run build.ts 1 db/s1.pglite 1500 noembed`, repeated until all 10,869 pages are in. It is resumable.
3. `bun run embed.ts db/s1.pglite all`.
4. `bun --smol run run.ts 1 db/s1.pglite out.jsonl search 100 @task_ids_s1.txt 0 embed`.
5. `python3 -I score.py 1 "GB=out.jsonl" "GB keyed=out.jsonl:keyed" "GB+cards=out.jsonl:pincardskeyed"`.
6. For security: `bun run leak.ts plant|probe|twin|secret|secret200|analyze|cachefresh <db> <out>`; then `python3 -I twin_cmp.py W.json W_repeat.json Wp.json` and `python3 -I leak_sum.py leak_probe.json`.
7. Set `GBRAIN_HOME`/`HOME` to a scratch directory and `GBRAIN_QUERY_EMBED_TIMEOUT_MS=30000` on a loaded host.

**GBrain arm for the GPU package** (add to E12, the engine bake-off, as a "whole-system baseline"):
- **Build.** Same three BrainBench v0.2 seeds plus the v0.3 corpus (when v0.3 fixes the member-access defect).
  - Pin GBrain at a commit.
  - PGLite **and** Postgres engines.
  - Embedder: Qwen3-Embedding-4B through `llama-server` (the same model on both sides).
  - Reranker: Qwen3-Reranker-4B through `llama-server-reranker`, `balanced` (top_n_in 25) and `tokenmax` (50).
  - Facts extraction and the dream cycle via a local LLM (R1 line-up) through the `llama-server` chat recipe. Give it 2 simulated weeks of cycles so compiled truth is rewritten.
- **Arms.** (a) GBrain as shipped, local providers; (b) GBrain + our card prefix (as here); (c) our pipeline (cards + query + reranker) with identical models; (d) GBrain with entity anchoring on; (e) GBrain `query` op (facts arm) after extraction.
- **Metrics.**
  - CR@10/20/50 per class with Clopper-Pearson bounds over distinct sets;
  - stale probes (all four E1 metrics) **after** the dream cycle (decisive for GB2's "compiled truth fixes staleness" counter-argument);
  - p50/p95 latency;
  - GBrain's own LongMemEval-S `recall_all@5` with the same local models, as a sanity anchor (expect ≥90%; if far lower, our local configuration is wrong, not GBrain).
- **Security on Postgres + `serve --http`** with real OAuth clients per identity:
  - twin-world noninterference (X1) on top-10 lists **and** response timing (KS test, 1,000 trials);
  - N6 fuzz rerun with our identities;
  - the default-floor token probe.
- **Kill / decision rules.** Those in §8 (GB1–GB4, GB8).

---

## 6. Steelman and devil's advocate, both ways

### 6.1 Steelman for GBrain ("just use GBrain and stop designing")
1. **It exists, runs and is tested.** 266 migrations, a crash robot that SIGKILLs the writer 69–75 times per 10-minute run with zero lost writes, PGLite↔Postgres parity, 182 MCP operations, OAuth 2.1, and receipts and doctors everywhere. Our design has zero lines of code. The owner's last builder ran out of tokens. A working system today beats a certified one never.
2. **It is honest.** It publishes its losses: expansion −187 questions, autocut −70, fact keys killed, core memory killed, supersession misses 47%, an entity-card leak found and fixed by its own fuzz. Its eval culture (preregistration, sealed splits, custodian-run held-out cells, CI gates) is what ADR-018 asks for, and it is already operating.
3. **Its retrieval is genuinely strong where it is tuned.** 93.4% strict all-sessions@5 with no reranker on LongMemEval-S is above every other published strict number they found.
4. **Its isolation is good enough for most of our users.** Owner, wife and partners could each get their own *brain* (a separate database) and mount shared team brains. That is a hard DB boundary. Members could get their own brain or source.
   - N6 shows 0 returned-content leaks across 74 ops.
   - *Our test agrees:* 0 ungranted rows with correct grants, and **list-level noninterference held** with 20 and 200 hidden notes in a shared HNSW (§5.4). Our own batch-2 BM25 does not have that property.
5. **Labels beat quarantine (measured).** Their paid eval says frontier readers ignore instruction-worded injections anyway, and that labels cut false-statement adoption by half. Our quarantine may cost owner friction for no measured gain.
6. **It is MIT-licensed and self-hostable.** Local llama-server embeddings and reranker recipes exist; we ran it fully offline. Australian hosting is a deployment choice, not a code change.

### 6.2 Devil's advocate against GBrain (why it fails us)
1. **Stale facts are not a design constraint in GBrain.**
   - Truth lives in rewritten prose (`compiled_truth`), kept current by an LLM dream cycle.
   - Facts supersede by cosine at a calibrated threshold, or by a caller who knows the fact id.
   - Their own measurement: 47% of corrections missed at the best threshold. With OpenAI 3-large, no threshold works, so cosine supersession is off and every correction coexists with the old value.
   - Nothing in GBrain is a "one current row per key" invariant. Our ≤2% stale bar has no mechanism in GBrain to hit it. (§5.2 measures what this does on our stale probes.)
2. **Its access model has the wrong shape for us.**
   - `visibility: private` means "hidden from every remote caller", not "visible to Priya but not Lachlan".
   - The owner and any local CLI or DB credential see everything. GBrain says so itself: "Local files and shared database credentials are a different trust boundary."
   - Our charter forbids standing owner access to member health data and requires vaults with keys the owner does not hold. GBrain has neither.
   - Using a separate brain per person moves the problem: cross-brain federation is "the agent's job… not deterministic". So shared spaces, consent ledgers and per-hop checks would be reimplemented in agent prompts. That is exactly what charter principle 8 forbids.
3. **Security testing covers returned content only.**
   - N6 is excellent at "did a protected string or slug come back". It does not test whether rankings, scores or tie-breaks change when hidden data changes.
   - DA3/X1 showed that this class is real and that canary-style tests miss it 744/744.
   - GBrain's HNSW graph and planner statistics are shared across sources. The OR-fallback narrowing reads `pg_stats` over all chunks. Per-page feedback weights are shared across callers with write grants.
   - *Measured rebuttal (§5.4):* our twin-world replay found **0 of 112 lists or scores changed**. The list-level channel we feared is absent on this probe set. What remains untested is timing (and, if GBrain re-enables its semantic cache, the global invalidation clock, where any hidden write would flush everyone's cache).
4. **Defaults egress text overseas.**
   - Facts extraction is on by default and calls hosted Haiku on every eligible page write.
   - The default embedder is Voyage, the default reranker is Voyage, System One sends to TypeSafe (US) when a key is present, and gstack's Supabase path defaults to `us-east-1`.
   - All of this can be configured away, but every new install, upgrade or default flip is a regression risk under APP 8. Our design makes local the only path for member data.
5. **Churn.** v0.60.398 with a 4.4 MB CHANGELOG, an 893 KB TODOS file, frequent schema migrations, and "upgrade recovery" guides (rebuild chunks after v0.48.3). For a 10-year family and business brain, adopting a fast-moving upstream means taking its release train or forking 600k+ lines.
6. **Its retrieval is tuned to conversation sessions and entity pages** (LongMemEval, people and companies). It is not tuned to multi-item personal-context tasks (decision support needing 5–7 items), where our M1 arithmetic says ranking alone cannot reach 90%.
   - *Measured (§5.3):* 24.4% CR@10 overall, 0% on decision and cross-domain, and below plain bge-small cosine. Its fusion stack subtracts on our corpus.
   - It is also **load-sensitive**: time-budgeted vector walks and embed deadlines silently fall back to partial or keyword-only results on a busy host (GB10).

### 6.3 Steelman for our design (against "you're over-engineering")
- The charter's hard constraints (zero leakage including ranking channels, ≤2% stale, member health data never reaching the owner, Australian residency) are **legal and relationship requirements**, not preferences. No off-the-shelf system meets them. GBrain doesn't claim to.
- Our largest measured gains, cards (+12.3 pp) and keyed supersession (0% stale versions), come from structure that GBrain lacks (keyed facts) or keeps off (entity anchoring).
- *Measured here:*
  - GBrain's ranker plus our cards comes within 2.4 pp of our assembly, while GBrain alone is 16.5 pp behind. The structure is the product.
  - GBrain's best available supersession (perfect links) trades stale answers for broken history (−55 pp temporal), which our keyed bi-temporal design avoids.

### 6.4 Devil's advocate against our design, informed by GBrain
1. **GBrain shows labels may do the work we assigned to quarantine** (paid, preregistered, three frontier models). If true for our readers, ADR-014's quarantine adds owner friction (a review queue nobody keeps up with; DA1 already flagged five queues) for no gain. *Counter:* their attacks were templated and their readers frontier-class; our local models may be weaker readers (see GB5).
2. **GBrain killed several ideas we are about to build:**
   - fact keys merged into embeddings (close to our U2 scribe entry), killed on LoCoMo;
   - always-loaded core memory (close to our H19 small index and standing packets), failed held-out;
   - LLM query expansion, −187 questions;
   - autocut, −70.
   - Our U2/U2a and H19 should expect the same headwinds, and their kill criteria should be pre-registered as tightly as GBrain's.
3. **GBrain's operational surface shows how much we haven't specified:** doctor checks with fix commands, projection readiness, degraded flags, write receipts, request-id replay, and purge receipts that list residuals. Our ADRs barely mention operability. A brain without these will silently degrade.
4. **Their date frame (+14 pts on held-out answers, no retrieval change) is a free win our reader contract lacks.**
5. **Their "frozen verb protocol + conformance kit"** is a cleaner client-agnostic contract than our "small tool set" (ADR-002, H14).
6. **GBrain passed list-level noninterference; our batch-2 first stage would not** (global BM25 IDF, DA3 X1). We have been treating noninterference as hard. GBrain shows that a single Postgres with in-SQL filters and no corpus statistics gets most of the way for free. That argues for simplifying ADR-006 (filter-first SQL, per-partition IDF) before reaching for per-partition indexes.
7. **Our cards path depends on the lexical linker and the temporal regex.** GBrain's links experiment shows how badly a misrouted temporal query can fail. Our 6% temporal routing miss on templated queries is a floor, not an estimate.

---

## 7. Verdict

**Borrow ideas; do not adopt as the brain; keep GBrain as a measured baseline arm in the GPU validation package.**

| Option | Verdict | Why |
|---|---|---|
| Adopt GBrain as the brain | **Reject** | Fails ≤2% stale (measured 45% stale versions; no keyed supersession) and the partition model (no per-user visibility, no vaults, owner sees all). Fixes would be forks of a 0.60.x project that changes daily. (It passed return-path leakage and list-level noninterference, so security is *not* the main reason) |
| Adopt as a component (e.g. the retrieval engine under our access layer) | **Reject** (GB1 contradicted) | Its ranker is 5.6 pp below our first stage and 3.8 pp below plain cosine on CR@10 with the same embedder. It adds latency (p50 4.2 s on PGLite) and silent degradation under load. Revisit only if the GPU run with its reranker beats our cards + query + reranker arm |
| Run GBrain for the owner's *personal* coding/notes memory (gstack) | **Allowed, outside the brain**: PGLite local, keyless or local embedder, no Supabase, no member or partner data. If `serve --http` is used, mint every token with `--sources` and `--scopes` (a plain `auth create` token reads all federated sources) | It is excellent at what it was built for. Keep it out of the family and business brain |
| Borrow ideas | **Yes** (list below) | Cheap, measured, compatible with our design |
| **Do not borrow** | page-level supersession by rank penalty; no-grant-means-default-floor tokens; its untuned 4–5-arm RRF (k = 60) fusion as-is (measured below plain cosine); time-budgeted silent fallbacks without a client-visible degraded flag | Each measured to fail here (§5.2b, §5.4 P2, §5.3, §5.5). Its keyword arm on its own is fine: keyless ≈ our BM25 at k = 10 |

**Borrow list** (each becomes a doc 02 revision or a doc 04 spec item):
1. **N6-style visibility fuzz harness** (public twin + ghost + presence controls, auto-enumerating every read op and parameter variant). Add to ADR-007 alongside the twin-world noninterference test. It replaces our weaker canary-monitor certification evidence.
2. **Frozen memory-verb protocol plus a conformance kit**, with `protocol_version` on every response, enumerated error codes with `fix` objects, and additive-forever fields. Use it for ADR-002's tool set and test it against H14.
3. **Trust tier on every row and label on every read**, external content wrapped as data, with a confirmation only a human at a trusted surface can give. Our ADR-014 has tiers; add *read-time labels* and measure (GB5) whether quarantine adds anything over labels with our local readers.
4. **Date frame in the reader contract**: current date plus each item's content date in every context packet. Measured +9–14 pts on answers.
5. **Purge receipts**: list residuals first, text-free tombstone refusing re-ingest, rederive marks on derived rows. Fold into ADR-008's erasure cascade and S5.
6. **Evidence stamps** (`alias_hit | exact_title_match | high_vector_match | keyword_exact | weak_semantic`) and **`create_safety`** on every result. Also add the **degraded / projection-readiness flags** so "no results" is never mistaken for "not in the brain" (charter §3a interacts: compute these over the visible set only).
7. **Relational re-pin**: rows from a structural arm (cards, keyed facts, graph) must not be demoted by a text cross-encoder. Directly relevant to ADR-010 + ADR-017 (cards pinned before reranking, then the reranker must not reorder them out).
8. **Their published negatives as priors**: expansion harmful at small k; autocut harmful for multi-evidence questions; fact keys in embeddings marginal; always-loaded core mixed. Update H13, U2, H19 and I10 accordingly.
9. **Spend caps and egress receipts per pipeline** (gstack's hash-chained egress ledger is fail-closed). Fold into ADR-016 egress classes.
10. **Owner-terminal-only confirmation**: nothing reaches `user_confirmed` without a token typed on the host, and `--yes` never confirms. A good pattern for our one-tap review queue, which needs out-of-band, unforgeable confirmation (see the existing scribe review's `home:` spoof finding).
11. **AGENT_OPERATOR contract** (`docs/protocol/AGENT_OPERATOR_v1.md`): every refusal, degraded result and recommendation carries a stable `code`, `why`, one `fix.next` (`run | ask_user | tell_user_to_run | wait | report`) and a read-only `fix.verify`, and states that "a degraded result is not proof of 'no notes'". This is the machine contract the brain owes any client AI (charter principle 3). Adopt it for ADR-002.
12. **Session-boundary verbs** (`context_pack` at session start and after compaction, `delta` for "what changed since my last wake"). GBrain's observation is that misses come from *placement*: moments when no question fires. That is a useful frame for our standing-context work, distinct from the H3 packets that were contradicted (packets lost because they consumed the *query's* budget, not because boundary injection is wrong). Test as part of H19.
13. **In-SQL partition filtering before fusion, no corpus-level lexical statistics.** This is why GBrain passed list-level X1 (§5.4). Our first stage should get the same property: BM25 IDF per partition or per caller's visible set (ADR-006), filters inside the candidate query, and RRF or convex fusion on within-list values only. Add the twin-world replay harness from this review (`leak.ts twin`) to the ADR-007 CI gate.
14. **A cache invalidated by a global write clock** is safe but turns any hidden write into a visible latency change for every caller. If we add a semantic cache, key it by the caller's visible set **and** invalidate per partition. Include cache-hit timing in the X1 timing test.

---

## 8. Hypotheses (GB series)

| ID | Hypothesis | Where | Decisive test | Kill criterion | Status |
|---|---|---|---|---|---|
| GB1 | GBrain's retrieval as shipped (balanced, local embedder, reranker per GB4) reaches within 2 pp of our best *first stage* on CR@10 per class on BrainBench | S (done for seed 1, §5) → GPU package (3 seeds, Qwen3-Emb-4B both sides) | §5 run; repeat on 3 seeds with matched embedders | GBrain > our assembled pipeline (cards + query) by ≥2 pp on any class → study and borrow that mechanism. GBrain < our first stage by ≥5 pp on ALL → stop treating it as a retrieval reference | **Contradicted (seed 1, reranker off).** −5.6 pp vs our query-only (p = 1e-6) and −3.8 pp vs plain bge-small cosine. The kill line (≥5 pp below on ALL) is met, so stop using it as a retrieval reference **unless the GPU run with its reranker closes the gap**. The first clause also fired: as the fill after cards it is +10 pp on pref (p = 0.008), which is spun out as GB9 |
| GB2 | Without keyed supersession, GBrain serves superseded values as current above the ≤2% bar on our stale probes | S (done, §5.2) | Stale probes: stale version above current / first value-bearing item stale, top-10 | ≤2% upper bound on GBrain as shipped → our keyed-supersession thesis (H4/I3) loses its "necessary" claim | **Supported.** 45.3% [37.6–53.3] stale version above current; 58.1% first value stale. Identical to our add-only arm (47.3 / 57.3). Keyed semantics drive it to 0.0% under either ranker. Caveat: no dream cycle; that is the GPU package's job |
| GB3 | GBrain's source isolation leaks no *returned* content to a correctly granted client, but its default-floor and ungranted tokens widen silently | S (done, §5.4) | DA3-style probes for each non-owner identity × canary tokens × shared entities × `search` and `query`, plus misconfigured grants | Any returned row from an ungranted source with a correct grant → GBrain unfit even as a component | **Supported as worded.** Correct, empty and default-only grants: 0 ungranted rows in 416 probes plus 790 tasks, including after owner pre-warming. **No-grant token (the `auth create` default) with federated sources: 1,880 ungranted rows, all canaries, overrides included** (§5.4 P2) |
| GB4 | GBrain fails twin-world noninterference: adding hidden owner-source notes changes non-owner identities' visible top-10 or scores | S (done, §5.4) | X1 replay: identical queries in W and W′ = W + 20 hidden owner notes; compare visible lists and scores | 0 changed lists and 0 score deltas → GBrain's shared index is noninterfering on this probe set (useful evidence for our ADR-006 HNSW question) | **Contradicted (kill criterion met) on this probe set.** 0 of 112 lists and 0 score deltas with +20 hidden notes embedded in the shared HNSW. Repeated with +200 varied notes and refreshed planner statistics: still 0 of 112. Timing untested |
| GB5 | With *our* local reader models, read-time trust labels alone keep write poisoning ≤1%; quarantine adds no measurable protection (GBrain's frontier-model finding transfers) | S+ / GPU package | Replicate gbrain-evals Cat 37 (external and agent-relayed arms) with the local reader (R1 line-up) and with Claude; arms: labels-only vs labels + quarantine | Labels-only > 1% adoption with the local reader → keep ADR-014 quarantine as default. Labels-only ≤1% on both readers → demote quarantine to opt-in, keep provenance |
| GB6 | A reader date frame (current date + item content dates) adds ≥5 pp answer accuracy on our temporal and current-state classes at equal retrieval | S+ (Claude reader on BrainBench answers) | Paired reader eval, same context, with vs without the date frame | <2 pp gain → don't add it to the reader contract |
| GB7 | An N6-style visibility fuzz catches every *return-path* leak class our canary monitor catches, plus classes it misses, at equal cost | S | Inject our 10 known leak classes (S3) into a test build; run canaries vs N6-style fuzz vs twin-world noninterference | N6-style ≤ canaries on detection → don't adopt it; keep noninterference as the gate |
| GB8 | Structural rows (cards, keyed facts) lose CR when passed through a text cross-encoder without a re-pin; a re-pin recovers it | S+ (GPU reranker) | Cards + query + Qwen3-Reranker with and without a "pinned rows bypass rerank" rule | <1 pp difference → re-pin unnecessary |
| GB9 | GBrain's multi-arm fill beats our two-arm wsum on preference tasks *after* the card prefix (+10 pp CR@10, 8 better / 0 worse, seed 1) because one of its arms surfaces the requester's own short, untitled preference note. Candidate mechanisms: the title arm on first-sentence titles, 4–5-arm RRF, or per-page dedup | S (cheap: our harness) | Ablate on seeds 1–3: our cards + {wsum, wsum + title-arm RRF, wsum + home-partition boost}; and GBrain + cards with each arm disabled | No ablated arm of ours reproduces ≥ +5 pp on pref across 3 seeds → artefact of seed 1; drop. Reproduces → add that arm to ADR-010's fill stage | Open (new) |
| GB10 | GBrain returns different results for the same query under load: time-budgeted vector walks and embed deadlines silently downgrade to partial or keyword-only results | S | Replay 200 tasks 3× at idle and 3× under a CPU-burn neighbour; count list changes; read `meta.degraded` | ≤1% list changes under load → not an issue. Our design should state its own determinism and degraded-result contract either way (see borrow item 6) | **Observed, not quantified**: 11 of 80 multimodal lists changed on rerun, 5 of them outside the embedder outage |
| GB11 | A brain whose *default* credential has no explicit grant will, in practice, be deployed with an over-broad credential; fail-closed default grants prevent it | Design rule (ours) + S | Our MCP auth: mint a token with no flags, then run the §5.4 P2 probe; it must return 0 rows from any source | Any row returned → block release (ADR-007 CI gate) | Open. GBrain's case is the motivating evidence |
| GB12 | Page-level supersession (a rank penalty) cannot satisfy both ≤2% stale on current-state queries and ≥ baseline CR on temporal queries without intent routing; keyed bi-temporal state can | S (done for GBrain, §5.2b) | Same world: GBrain ± links vs our keyed, on stale probes **and** temporal tasks | GBrain + links ≤2% stale **and** temporal CR@10 within 5 pp of no-links → page-level supersession is sufficient; drop keyed state's "necessary" claim | **Supported.** Links: 0.0% stale but temporal CR@10 2.5% vs 57.5% (−55 pp, p = 1e-13) |

---

## 8b. Paste-ready entry for the hypotheses board (doc 06)

### GBrain review (2026-10-24)

Source: vendor-skills/analysis/GBRAIN-review.md. GBrain @ 2d63ee8 run fully local (PGLite plus bge-small through its llama-server recipe) on BrainBench v0.2 seed 1: 790 tasks, real `search` op as remote OAuth callers, reranker off.

- **Verdict: borrow ideas; do not adopt as the brain or as the retrieval component; keep as a GPU-package baseline arm.**
- **Retrieval (GB1 contradicted).**
  - CR@10, ALL: GBrain 24.4% vs our query-only wsum 30.0% (−5.6 pp, p = 1e-6) and vs plain bge-small cosine (−3.8 pp). Losses are on current_state (57.5 vs 75.0) and multimodal (67.5 vs 88.8).
  - GBrain ranker + our cards: 38.5% vs our cards + query 40.8% (−2.4 pp). Structure carries it.
  - One anomaly: pref +10 pp as the fill after cards (GB9).
- **Stale (GB2 supported).** 45.3% stale version above current, the same as our add-only (47.3%); keyed 0%.
- **Best case: perfect `supersedes` links (GB12 supported).** 0.0% stale, but temporal CR@10 collapses from 57.5% to 2.5% (the penalty has no intent gate). Page-level supersession trades stale answers for broken history. This is the strongest measured case yet for keyed bi-temporal state (ADR-008/009).
- **Leakage (GB3).**
  - 0 ungranted rows with correct, empty or default-only grants (416 probes + 790 tasks).
  - **A token from plain `gbrain auth create` (no source grant) read every federated source: 1,880 rows, all 7 canaries, `source_id` overrides included.** Documented behaviour, not fail-closed (GB11).
- **Noninterference (GB4 contradicted, as hoped).** Twin-world X1 found 0 of 112 lists or scores changed with +20 and then +200 hidden notes in the shared HNSW (plus ANALYZE). Mechanism: in-SQL source filter before fusion, `ts_rank` without IDF, pure cosine, rank-only RRF. Our batch-2 BM25 would fail this; simplify ADR-006 toward filter-first SQL and per-partition IDF.
- **Ops findings.**
  - Its semantic result cache is hard-disabled in code at this commit.
  - Silent keyword-only fallback on embed timeouts (6 s default), with only a `meta.degraded` stamp.
  - 11 of 80 lists changed on rerun under load (GB10).
- **Borrow (14 items, §7)**: N6 fuzz harness; frozen verbs and conformance kit; trust labels on read; reader date frame; purge receipts; evidence stamps and degraded flags; relational re-pin; their negatives as priors; spend caps and egress receipts; owner-terminal confirmation; AGENT_OPERATOR contract; session-boundary verbs; filter-first, no-corpus-stats ranking; per-partition cache invalidation.
- **Do not borrow**: rank-penalty supersession; no-grant tokens that widen to a floor; untuned multi-arm RRF as-is; silent time-budget fallbacks.
- **New hypotheses: GB1–GB12** (GB1 contradicted; GB2 supported; GB3 supported with condition; GB4 contradicted; GB5–GB8 open; GB9 open; GB10 observed; GB11 open; GB12 supported).

## 9. Sources

Code and docs (OBSERVED; paths are in the GBrain clone at the pinned commit):
- `README.md`; `CLAUDE.md` (read as data); `docs/architecture/RETRIEVAL.md`, `brains-and-sources.md`, `system-of-record.md`
- `docs/guides/memory-trust.md`, `memory-boundaries.md`, `rls-and-you.md`, `retrieval-feedback.md`, `core-memory.md`, `facts-drain.md`, `system-one.md`, `temporal-edges.md`, `time-aware-recall.md`, `compiled-truth.md`, `entity-records.md`
- `docs/takes-vs-facts.md`; `docs/protocol/MEMORY_VERBS_v1.md`; `docs/mcp/ADMIN.md`, `TOOL_REFERENCE.md`; `SECURITY.md`
- `docs/eval/BRAINBENCH.md`; `docs/eval-bench.md`; `docs/eval/decisions/{supersession-threshold-dev, entity-anchoring-query, query-facts-arm, p6-fact-keys, p4-heldout-core-2026-10-06, p3-retrieval-feedback}`; `docs/eval/system-one/README.md`; `docs/eval/TIME_AWARE_RETRIEVAL_RESULTS.md`
- `src/schema.sql`; `src/core/schema-migrations/v045-facts-hot-memory-v0-31.ts`, `v067-facts-typed-claim-columns.ts`
- `src/core/search/{hybrid.ts, keyword-statement.ts, keyword-or-narrow.ts, dedup.ts, source-boost.ts, mode.ts, lean-rows.ts, vector-statement.ts, hub-dampening.ts}`
- `src/core/search/{query-cache.ts (semanticResultCacheAvailable() = false), query-cache-gate.ts, vector-pool.ts, hybrid/arms.ts, hybrid/cache-stages.ts}`; `src/core/grants/model.ts` (`authSourcesFromGrant`); `src/commands/auth.ts` (token default `sources: {kind:'default'}`); `src/core/source-resolver.ts` (`federatedSetFor`); `src/core/sources-ops.ts` (mirror sources default `federated: true`)
- `src/core/facts/supersession-threshold.ts`; `src/core/ops/{search.ts, context.ts, contract.ts}`; `src/mcp/http-transport.ts`; `src/core/embed-stale.ts`; `src/core/import-file.ts`; `src/core/ai/recipes/{llama-server.ts, llama-server-reranker.ts}`

gbrain-evals (vendor reports; pinned commit): `docs/benchmarks/2026-09-09-retrieval-refresh.md`, `2026-09-30-n6-visibility-fuzz.md`, `2026-10-06-n6-postgres-http.md`, `2026-10-08-memory-trust-results-paid.md`.

gstack: `USING_GBRAIN_WITH_GSTACK.md`, `docs/gbrain-sync.md`, `setup-gbrain/SKILL.md` and `sections/brain-init.md` (region default `us-east-1`), `sync-gbrain/SKILL.md`, `bin/gstack-gbrain-repo-policy`, README GBrain section, CHANGELOG 1.43.1.0.

Web (fetched 2026-10-23; all secondary, conflicts noted):
- [Slite: GBrain, reviewed](https://slite.com/learn/gbrain-review) (competitor; code read, not run)
- [Vectorize: GBrain review](https://vectorize.io/articles/gbrain-review) (competitor; code and docs read, not run)
- [explainx.ai: GBrain evals are self-graded](https://explainx.ai/blog/garry-tan-gbrain-evals-self-graded-benchmark-agent-memory-2026) (commentary; no measurement)
- [gbrain.io](https://gbrain.io/) (hosted product page; hosting region not stated)
- [garrytan/gbrain](https://github.com/garrytan/gbrain), [garrytan/gbrain-evals](https://github.com/garrytan/gbrain-evals) (cloned)

Our docs: `/home/claude/00-charter.md` v0.6.1; `/home/claude/docs02/README.md` + ADR-003/005/006/007/008/009/010/011/018; `/home/claude/06-hypotheses-board.md` v1.1; `/home/claude/brainbench/results_v02/tables.md`; `/home/claude/challenges/DA3-security-privacy.md`.

Test artefacts:
- Harness (durable copy): `/home/claude/vendor-skills/analysis/gbrain-harness/`. Contents: `embed_server.py`, `build.ts`, `embed.ts`, `run.ts`, `leak.ts`, `supersede_links.ts`, `score.py`, `card_prefix.py`, `stale_ref.py`, `twin_cmp.py`, `leak_sum.py`, `setcfg.ts`, `dbcheck.ts`, `cachecheck.ts`, `queue*.sh`, the task-id lists and `card_prefix_s1.json`.
- Outputs (scratchpad, `/tmp/claude-0/-home-claude/4c8492a6-f948-5903-9334-5b76eec5c7f7/scratchpad/gbt/`):
  - runs: `run_hybrid_final.jsonl` (790 tasks, multimodal rerun merged), `run_suplinks.jsonl`, `run_suplinks_temporal.jsonl`, `run_keyless.jsonl`;
  - scores: `tables_s1_hybrid_final.md`, `sup/tables_s1.md`, `supt/tables_s1.md`, `kl/tables_s1.md`, `sens/tables_s1.md`;
  - security: `leak_probe_granted.json`, `leak_probe_{grant_empty_array,grant_default_only,no_grant_legacy_floor}.json`, `twin_{W,W_repeat,Wp}.json`, `twin2_{W,W_repeat,Wp}.json`, `cachefresh.json`;
  - DBs under `db/`: `s1` (base brain, 10,869 pages embedded) and `sup` (+1,779 supersedes links). The probe copies (`leak`, `twin`, `twin2`, `fresh`) were deleted to free disk; rebuild them from `s1` with `queue*.sh`.
