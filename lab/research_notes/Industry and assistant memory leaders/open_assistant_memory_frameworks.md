# Open-Source and Startup Assistant Memory / User-Modelling Frameworks (Honcho, Hermes, "dots", and the 2026 Ecosystem)

Research date: 2026-10-23. Sources fetched: vendor docs and blogs, GitHub READMEs, one arXiv paper, and secondary write-ups. Vendor claims are labelled **[VENDOR]**. Independent or third-party material is labelled **[3P]**. Unless stated otherwise, no benchmark figure below has been independently reproduced. One 2026 author makes this point explicitly: "not one number in agent memory has been independently reproduced by a party that did not build one of the systems" ([Towards AI, Jul 2026](https://pub.towardsai.net/mem0-vs-zep-vs-letta-a-folder-of-text-files-shouldnt-beat-the-61k-star-memory-layer-9d7e65c5799c)).

## Q1. Honcho (Plastic Labs): user modelling, peers/sessions, dialectic, deriver, benchmarks, licence, self-hosting

### Takeaway
Honcho is the most developed open-source "user-model" memory available. It treats memory as asynchronous *reasoning* rather than storage. A cheap ingestion model extracts explicit facts and deductions. A background "dreamer" consolidates them and draws inductive and abductive conclusions plus peer cards. An agentic "dialectic" endpoint answers natural-language questions about a peer. It is AGPL-3.0 and self-hostable on Postgres+pgvector. Its own published scores are strong (LongMemEval-S 90.4%, LoCoMo 89.9%, BEAM 10M 0.409). The vendor itself concedes these benchmarks are saturating, and none of the scores has been independently reproduced.

### Cited Findings
**Architecture and primitives**
- Data model: **Workspaces** (isolation between use cases), **Peers** (any participant, human or AI), **Sessions** (group peers and messages, optionally within named **scopes** that limit recall), and **Messages** (labelled by source peer) — [GitHub plastic-labs/honcho](https://github.com/plastic-labs/honcho)
- Two services. Storage is synchronous. Insights (reasoning, conclusions, representations, summaries, chat) is asynchronous: "Insights is asynchronous via a background queue consumed by the deriver worker process." The deriver runs as `python -m src.deriver` and scales horizontally — [GitHub](https://github.com/plastic-labs/honcho)
- "Representations" are "static, low-latency snapshots of what Honcho knows about a peer," optionally session-scoped. "Peer cards" are "compact identity summaries" — [GitHub](https://github.com/plastic-labs/honcho)
- The Peer paradigm (Aug 2025) replaces the user/assistant split: a Peer can be "a human, an AI, an NPC, an API." By default a peer's representation is built from every message it sends. With `SessionPeerConfig(observe_others=True)`, each peer forms "its own representation of the others from only the messages it has actually seen." These perspective-scoped ("local") representations let you query, for example, `charlie.chat(..., target="alice")` — [Honcho blog: Introducing Peers](https://honcho.dev/blog/blog/introducing-peers)
- Reasoning pipeline: the explicit model (Neuromancer XR) outputs "things that were explicitly stated" as premises. Deductive entries store `premises` + `conclusion`. The Dreamer "periodically" revisits conclusions to consolidate them, flag redundancy and contradictions, and draw inductive conclusions. All outputs (conclusions, summaries, peer cards) are stored in peer representations and indexed in vector collections. Session-based queues keep ordering per representation — [Honcho docs: Reasoning](https://honcho.dev/docs/v3/documentation/core-concepts/reasoning)
- Philosophy ("Memory as Reasoning", Aug 2025): memory is prediction, and "Prediction requires reasoning." Conclusions are deductive ("certain statements supported by premises that were explicitly stated or observed"), inductive, or abductive. Certainty is expressed in natural language with premises, avoiding "arbitrary numerical tokens representing degrees of certainty." Static storage (relational, vector, graph) is "brittle" and "deal[s] poorly with contradictions and incomplete information" — [Honcho blog: Memory as Reasoning](https://honcho.dev/blog/blog/memory-as-reasoning)

**Honcho 3 (Jan 26, 2026)**
- The deriver became "Ingestion Reasoning," limited to "exhaustive *explicit* information capture" so it is faster, cheaper, and parallel. A new asynchronous **Dreaming Agent** produces summaries, peer cards, and deductive, inductive, and abductive conclusions, and "reorganize[s] data for faster retrieval." Dreaming may be concentrated in cheap evening hours. Caveat: peer cards and summaries "won't be available for sessions and peers that haven't undergone dreaming" — [Honcho 3 announcement](https://honcho.dev/blog/blog/honcho-3)
- The **Dialectic Agent** "replaces a prior fixed-path architecture." Retrieval methods became tools in an agent loop. `.chat()` reasoning levels run `minimal`→`max`, priced at $0.001 / $0.01 / $0.05 / $0.10 / $0.50 per query. `context()` is "fast enough to call on every turn (~200ms)" and free. Ingestion costs $2/M tokens — [Honcho 3](https://honcho.dev/blog/blog/honcho-3) **[VENDOR]**
- The chat endpoint is `POST /peers/{peer_id}/chat`. Config has `[dialectic]` and `[dream]` sections — [GitHub](https://github.com/plastic-labs/honcho)

**Benchmarks [VENDOR], Dec 2025 evals page**
- LongMemEval-S: **90.4%** vs Haiku 4.5 full-context **62.6%**. With Gemini 3 Pro: **92.6%**. Categories: SS-assistant 96.4, SS-user 94.3, knowledge-update 94.9, SS-preference 90.0 (baseline 23.3), temporal 88.7, multi-session 85.0 (baseline 46.6). It uses 11.4% of full context on average ("89% fewer tokens") — [honcho.dev/evals](https://honcho.dev/evals/)
- LoCoMo: **89.9%** vs Haiku 4.5 **75.6%** (previous Honcho 86.9%). Uses an LLM judge instead of the paper's token-F1 — [honcho.dev/evals](https://honcho.dev/evals/)
- BEAM: 0.630 (100K), 0.646 (500K), 0.618 (1M), **0.409 (10M)**. Haiku baseline at 100K is 0.533. At 100K, abstention is the one ability where Honcho loses (36.3 vs 60). Preference following falls from 86 to 41 and temporal reasoning from 64 to 26 between 100K and 10M — [honcho.dev/evals](https://honcho.dev/evals/)
- Default eval models: gemini-2.5-flash-lite as deriver, claude-haiku-4.5 as dreamer and dialectic. Raw data is at github.com/plastic-labs/honcho-benchmarks — [honcho.dev/evals](https://honcho.dev/evals/)
- Caveats in the vendor's own benchmark post: Gemini 3 Pro *alone* scores 92.0% on LongMem-S, so frameworks may be "degrading" latent capability and Honcho's +0.6 is marginal. LongMem-M scored 88.8% on only 98 questions. Dreaming was ON only for LoCoMo and BEAM-100K, with **no with/without-dreaming ablation**. Batch sizes vary from 128 to 16,384 tokens with no ablation. There are no confidence intervals or repeated runs. Datasets contain "dozens of questions with ambiguous answers." Temporal reasoning is the weakest area. The authors say "Benchmarks don't test for" identity modelling — [Benchmarking Honcho, Dec 19 2025](https://honcho.dev/blog/blog/benchmarking-honcho)
- The vendor reports near-zero S-vs-Oracle drop (90.4 vs 91.8), while Haiku drops 89.2→62.6 when ~115K distractor tokens are added — [Benchmarking Honcho](https://honcho.dev/blog/blog/benchmarking-honcho)
- **[3P] contradiction:** a review table lists Hindsight at 91.4% on LongMemEval, above Honcho's 90.4%, which contradicts "top of leaderboard" framing. It also flags the "beats oracle" claim as a cross-configuration comparison — [DEV/andrew.ooo review 2026](https://dev.to/andrew-ooo/honcho-review-plastic-labs-agent-memory-layer-2026-2kb4)

**Licence and self-hosting**
- Licence: **AGPL-3.0** ("Honcho is licensed under the AGPL-3.0 License"). Server version badge: 3.4.0 — [GitHub](https://github.com/plastic-labs/honcho). The [3P review](https://dev.to/andrew-ooo/honcho-review-plastic-labs-agent-memory-layer-2026-2kb4) is internally inconsistent ("Apache 2.0 / AGPL-style"), so treat the repo's AGPL statement as authoritative.
- Requirements: PostgreSQL + pgvector (migrations need a session-mode connection, not a transaction pooler), uv/Python 3.13+, one LLM provider key (defaults `gpt-5.4-mini` and `text-embedding-3-small`; "Models must support tool calling"), and optional Redis (cache off by default). Auth is off by default (`AUTH_USE_AUTH=false`) and must be enabled before network exposure. An MCP server is available (hosted at `mcp.honcho.dev`) — [GitHub](https://github.com/plastic-labs/honcho)
- **[3P]** "It's not the simplest to operate." Setup takes about 30 minutes vs about 30 seconds for Mem0 managed. A quote from glukhov.org: "Honcho and Mem0 require the most moving parts" — [DEV review](https://dev.to/andrew-ooo/honcho-review-plastic-labs-agent-memory-layer-2026-2kb4)

**Recommended partitioning patterns [VENDOR], Jul 2026**
- Reuse one user peer "across every conversation so their representation deepens instead of fragmenting." Use a workspace per client or engagement for isolation. Plugins default to a separate workspace per host, so unified cross-tool memory requires deliberately sharing both workspace and user peer. For trickle inputs, use one ongoing per-source session, because thin sessions "reason with too little context." Teams treat conclusions as the highest-signal layer and filter them by space — [Common Patterns for Building with Honcho](https://honcho.dev/blog/blog/common-patterns-for-building-with-honcho)

### Inferences
- What is genuinely novel: (a) **asynchronous, typed reasoning over messages** (explicit → deductive → inductive/abductive) with premises stored alongside conclusions, which gives provenance and an alternative to numeric confidence; (b) **perspective-scoped peer models** (what A knows about B), which fits multi-user enterprise use and agent-to-agent setups; (c) **an agentic retrieval endpoint with a cost/latency dial** (reasoning levels); (d) **"dreaming" as scheduled offline consolidation**.
- For the 90% target at 10K+ items, the BEAM-10M score (0.409, falling to ~26 on temporal reasoning) is the relevant warning. Even the vendor's best system degrades sharply at very large scale. Temporal reasoning and abstention ("I don't know") are the weak spots to test hardest.
- AGPL matters for an enterprise deployment that serves other users over a network. Network users must be able to receive the source of a modified Honcho. Self-hosting unmodified is generally fine, but get legal review.
- Pattern to adopt: a "context() every turn (cheap, cached) + chat() on demand (expensive, agentic)" split.

### Gaps
- No independent reproduction of Honcho's benchmark numbers was found.
- How contradictory or stale conclusions are *resolved* (deleted, superseded, versioned) is not documented on the pages fetched. The docs only say consolidation "identifies redundant or contradictory information."
- The dream trigger schedule and conditions are undocumented ("periodically").
- No dreaming ablation exists, so the value of dreaming is unproven.
- Neuromancer model weights and licence were not verified in this pass.

## Q2. "Hermes": identification and memory design

### Takeaway
"Hermes" almost certainly refers to **Nous Research's Hermes Agent** (MIT). It is an open-source self-improving personal agent first released Mar 12, 2026, with about 253K GitHub stars by Oct 2026. Its memory has three layers:
1. Two tiny, hard-capped markdown files injected into the system prompt (MEMORY.md 2,200 chars, USER.md 1,375 chars).
2. A SQLite FTS5 archive of all sessions, searched on demand.
3. Self-written SKILL.md procedural memory.

Pluggable external providers can be added, and **Honcho is the flagship user-modelling provider**. The Hermes LLM models are not memory systems.

### Cited Findings
**Identification and adoption**
- MIT licence, 253.6K stars, 55.0K forks. Features: "Agent-curated memory with periodic nudges," "FTS5 session search with LLM summarization for cross-session recall," "Honcho dialectic user modeling," "Autonomous skill creation after complex tasks," agentskills.io compatible — [GitHub NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- First public release v0.2.0 on Mar 12, 2026. Latest v0.21.6 on Oct 8, 2026. 252,576 stars vs OpenClaw's 391,638 on Oct 10, 2026. Both are MIT and self-hosted. A `hermes claw` command migrates from OpenClaw — [Parallel.ai, Oct 2026](https://parallel.ai/articles/what-is-hermes-agent) **[3P]**

**Built-in memory (official docs)**
- MEMORY.md (agent notes) is capped at **2,200 chars (~800 tokens)**. USER.md (user profile) is capped at **1,375 chars (~500 tokens)**. Both live in `~/.hermes/memories/`, typically holding 8–15 and 5–10 entries. There is no auto-compaction. An over-limit write returns an error "instead of silently dropping entries," forcing the agent to consolidate and retry — [Hermes docs: Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- Tool actions are `add` / `patch` / `remove` with `target` "memory" or "user". There is no `read`, because memory is always in the prompt. `replace` was removed in favour of `patch`. Exact duplicates are rejected — [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- **Frozen snapshot:** memory loads once at session start. Mid-session writes go to disk but reach the prompt only next session, to preserve the prefix cache ("never changes mid-session") — [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- **Session search:** all sessions are stored in `~/.hermes/state.db` (SQLite FTS5). Queries take about 20 ms with no LLM cost. The docs say raw messages are returned with "no LLM summarization, no truncation" — [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory). *Conflict:* the README and a 3P article describe LLM summarization of search results ([GitHub](https://github.com/NousResearch/hermes-agent); [Substack, Apr 2026](https://mranand.substack.com/p/inside-hermes-agent-how-a-self-improving)). The behaviour may have changed between versions.
- **Security scanning** of memory entries before acceptance blocks prompt-injection, credential-exfiltration, and SSH-backdoor patterns, and invisible Unicode — [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- Optional write approval: `memory.write_approval` and `skills.write_approval: true` — [Parallel.ai](https://parallel.ai/articles/what-is-hermes-agent)
- External providers run *alongside* built-in memory. RetainDB and ByteRover are bundled. Honcho, Hindsight, Supermemory, Mem0, OpenViking, and Holographic come via `hermes plugins install` — [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)

**Nudges and skills (procedural memory)**
- Periodic system-level nudges ask the agent to review recent activity and decide what to persist. A skill is created after 5+ tool calls, error recovery, a user correction, or a non-obvious successful workflow. `skill_manage` defaults to `patch` edits. Skills are in `~/.hermes/skills/` with progressive disclosure (only names and summaries in the prompt) — [Substack, Apr 2026](https://mranand.substack.com/p/inside-hermes-agent-how-a-self-improving) **[3P]**
- Community: users switched to Hermes chiefly for out-of-the-box memory management. Complaints: the agent "always thinks it did a good job, always," and fears that self-modification can "reduce a working setup to a tangled mess." About 15% suspected astroturfing. This is based on a Kilo analysis of 1,300+ r/openclaw comments — [pasqualepillitteri.it, May 2026](https://pasqualepillitteri.it/en/news/3864/hermes-agent-review-community-opinions) **[3P, secondary]**

**Honcho integration**
- Plugin `hermes-plugin-honcho` (`hermes plugins install honcho`; `hermes memory setup honcho`). There are two peers: a **user peer** (preferences, goals, style) and an **AI peer** (the agent's self-representation). Representations are injected into the *user message* at call time, "not the system prompt, which keeps prompt caching intact" — [Honcho docs: Hermes](https://honcho.dev/docs/v3/guides/integrations/hermes.md)
- `recallMode`: `hybrid` (default; inject + tools), `context`, or `tools`. Tools: `honcho_profile` (fast, no LLM), `honcho_search` (hybrid semantic+keyword over messages), `honcho_context` (summary, representation, peer card, recent messages; no LLM), `honcho_reasoning` (dialectic Q&A), and `honcho_conclude` (write/list/search/delete durable conclusions) — [Honcho docs: Hermes](https://honcho.dev/docs/v3/guides/integrations/hermes.md)
- Config: `writeFrequency` (async/turn/session/N), `sessionStrategy` (per-directory default / per-repo / per-session / global), `dialecticReasoningLevel` (default low), `reasoningHeuristic` (raises level for longer queries), `dialecticDynamic` (agent chooses level), `messageMaxChars` 25,000 — [Honcho docs: Hermes](https://honcho.dev/docs/v3/guides/integrations/hermes.md)
- An earlier in-repo spec (a mirror copy, ~Apr 2026) describes background daemon threads at turn end that prefetch context and dialectic into caches for the next turn ("no HTTP on the response path"), per-peer memory modes (hybrid/honcho/local), and no message dedup — [Hermes honcho-integration-spec (mirror)](https://download.ai.regdesk.co/youtube/2026-04-18-hermes-vs-openclaw/hermes-agent/docs/honcho-integration-spec.html) **[mirror of repo doc; may be outdated]**

### Inferences
- Hermes's key design insight is **tight caps as a forcing function for curation**: about 1,300 tokens of always-on memory, with errors instead of silent truncation. Everything else is retrieved on demand. This directly counters the "prompt debt" failure mode reported for unbounded markdown memory (see Q5).
- The three-tier split maps cleanly onto cognitive categories: core semantic (always-on) / episodic (FTS archive) / procedural (skills). Add a fourth, a user model (Honcho), as a separate service.
- The prefetch-async-into-cache pattern (compute next-turn context in the background at turn end) is a cheap latency win worth copying.
- Cache-preserving injection (frozen snapshot at session start, or injecting dynamic memory into the user turn instead of the system prompt) is a concrete cost optimisation for Claude-based builders.

### Gaps
- No quantitative evaluation of Hermes's built-in memory (benchmarks or retrieval accuracy) was found.
- The exact current behaviour of session-search summarization is unresolved (docs vs README conflict).
- Whether the "12 identity layers" Honcho claim in the Substack article is real could not be verified in Honcho docs.

## Q3. "dots as a wrapper": identification

### Takeaway
The most plausible referent, given "late 2026" and "wrapper," is **OpenAI Dots**, launched at DevDay on Sep 29, 2026. Dots are named, always-on personal agents, each with its own cloud computer, that start from ChatGPT memory and form their own memories. Their memory **cannot be viewed, edited, or exported**, which is the opposite of what a self-hosted brain should do. That makes Dots a useful anti-pattern and a competitive reference rather than something to adopt. The other candidates:
- **New Computer's Dot** (2024–25): a memory-centric companion, shut down in Oct 2025.
- **rednote dots.llm / dots.ocr**: models, not memory systems. Not researched further.
- **dotagents**: a small MIT tool, "Dotfiles for your AI agents," that syncs skills, MCP, and hooks across Claude Code, Codex, and Hermes and has optional review-gated memory.

The user should confirm which one they meant.

### Cited Findings
**OpenAI Dots (most likely)**
- Announced Sep 29, 2026. "A personal always-on agent you name and grow." Each dot gets its own cloud computer and browser and runs 24/7 toward goals. It runs on GPT-6 Astra, connects to 4,000+ apps via plugins, and can be started from Codex or ChatGPT. Available on Pro and Business Premium — [WikiDocs summary of DevDay coverage](https://wikidocs.net/blog/@openwiki/32110/) (cites TechCrunch, CBS, 9to5Google)
- Memory: a dot "starts with context from ChatGPT memory." Dots keep their own notes, "separate from ChatGPT's saved memory and... not a complete transcript." Memory flows both ways with ChatGPT memory. Dots form memories from connected apps, including during background research — [MemoryLake blog](https://www.memorylake.ai/en/blogs/chatgpt-dots-own-memory) **[3P, vendor-biased competitor]**
- You "can't view, edit or delete individual dot memories." The only option is deleting the whole dot, and disconnecting an app doesn't remove learned data — [dsebastien.net, Oct 3 2026](https://www.dsebastien.net/2026-10-03-openai-dots-always-on-agents-with-a-memory-you-cant-inspect/); corroborated by [eesel.ai](https://www.eesel.ai/blog/openai-dots) **[3P]**
- Architecture: a separate Auto-review system checks planned actions against Custom Rules. Background research is read-only, "enforce[d] in code." No MCP or external-memory hook is documented — [eesel.ai](https://www.eesel.ai/blog/openai-dots)
- Practitioner response: keep agent memory as plain Markdown in Obsidian so it can be read, fixed, and moved. Users won't trust an assistant that "knows me but can't show me what it knows" — [dsebastien.net](https://www.dsebastien.net/2026-10-03-openai-dots-always-on-agents-with-a-memory-you-cant-inspect/)

**New Computer "Dot" (historical)**
- Founded 2022 by Sam Whitmore and Jason Yuan. About $12M raised (OpenAI Startup Fund, a16z). TechCrunch (Sep 5, 2025) reported a shutdown in Oct 2025. Stated reason: retention and conversion — [ideaproof.io](https://ideaproof.io/failure/dot-new-computer) **[3P, partly interpretive]**
- Memory: an "agentic memory system" that pre-computes documents rather than storing raw conversation, evaluated with LangSmith. It claimed 50% higher recall and 40% higher precision vs its previous implementation, with metrics undefined (Jul 2024) — [LangChain case study via Plushcap](https://plushcap.com/analysis/langchain/langchain-customers-new-computer) **[VENDOR]**

**dotagents ("dots" as a wrapper/config layer)**
- "Dotfiles for your AI agents": one versioned repo of skills, MCP servers, hooks, and roles, rendered into Claude Code, Codex, and Hermes native formats. It does not wrap or run agents. Memory tiers: off / basic (session digests) / memsearch (indexed). The `rem` helper captures candidate facts that stay inactive until a human promotes them, and consolidation is report-first. MIT. v0.9.0 dated Sep 22, 2026 — [pkg.go.dev dotagents](https://pkg.go.dev/github.com/yourconscience/dotagents)

### Inferences
- If the user meant OpenAI Dots "as a wrapper" around ChatGPT, Codex, and plugins, the lesson is: **inspectability and editability of memory are a differentiator**. A self-hosted brain should expose every derived belief with provenance and allow edit/delete. Dots also validates the "always-on agent with background read-only research forming memories" pattern.
- New Computer's pre-computed-document approach (write-time synthesis rather than raw-transcript retrieval) is an early instance of what Honcho and Hindsight now formalise.
- dotagents' **"candidate → human-promoted" memory** is a pattern worth testing for high-stakes enterprise facts.

### Gaps
- I could not confirm which "dots" the user meant. The phrase "dots as a wrapper" did not match any memory framework in search results.
- OpenAI's own Dots help-centre pages were not fetched directly. Memory details come via third parties.
- rednote dots.llm / dots.ocr were not investigated (judged not memory-relevant). dots.ocr could matter for an image/PDF ingestion pipeline.

## Q4. Other personal-assistant memory designs (2026 ecosystem)

### Takeaway
The ecosystem has converged on **markdown-as-source-of-truth with a SQLite hybrid (BM25+vector) index** (OpenClaw, Basic Memory, Letta MemFS, Hermes). Alongside sit **reasoning or graph memory services** exposed over MCP (Honcho, Hindsight, Supermemory, Graphiti, Cognee). Capture-everything wearables (Rewind/Limitless) collapsed into Meta. Meeting memory (Granola) became an enterprise "memory layer" via MCP.

### Cited Findings
**OpenClaw (formerly Clawdbot/Moltbot), MIT**
- Layers: an append-only daily log `memory/YYYY-MM-DD.md` (today's and yesterday's read at session start) and a curated `MEMORY.md` loaded *only in the main private session, never in group contexts*. "The model only 'remembers' what gets written to disk" — [OpenClaw memory docs (HF mirror)](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)
- **Pre-compaction memory flush:** a silent `NO_REPLY` turn fires when tokens cross `contextWindow − reserveTokensFloor(20000) − softThresholdTokens(4000)`, once per compaction cycle — [OpenClaw memory docs (mirror)](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)
- Tools: `memory_search` (~400-token chunks, 80 overlap, ~700-char snippets with path, line range, and score) and `memory_get` (read by path and line range). Hybrid scoring: `vectorWeight 0.7` / `textWeight 0.3`, `candidateMultiplier 4`, `textScore = 1/(1+bm25Rank)`. Per-agent SQLite index. Session indexing is opt-in — [OpenClaw memory docs (mirror)](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)
- Current builtin engine (2026): indexes MEMORY.md, root USER.md, and memory/*.md. FTS5/BM25 + embeddings (sqlite-vec optional). Ranking combines hybrid relevance + **recency decay** + **write-time importance**, then **MMR (on by default)**. Each chunk carries **provenance metadata** (origin class, session kind, observation time, optional **supersession key**). Trigger recall injects only curated or promoted-trusted entries. A keyword fallback applies at the 30-second deadline. File reindex runs after a 1.5 s debounce. **QMD removed**, along with its cross-encoder reranking and HyDE. Honcho is suggested for "cross-session memory with automatic user modeling" — [docs.openclaw.ai memory-builtin](https://docs.openclaw.ai/concepts/memory-builtin.md)
- Stars: 391,638 (Oct 10, 2026) — [Parallel.ai](https://parallel.ai/articles/what-is-hermes-agent)

**Letta (MemGPT lineage)**
- **Context Repositories / MemFS (Feb 12, 2026):** agent memory is a **git-backed markdown repo** cloned locally. Every change is auto-committed. Files in `system/` are always fully in the prompt. The file tree plus frontmatter descriptions give progressive disclosure, modelled on SKILL.md. **Reflection (sleep-time) subagents** run in separate git worktrees and merge back, so concurrent writers merge via git conflict resolution. **Memory defragmentation** splits and merges into "a clean hierarchy of 15–25 focused files." `/init` learns from existing Claude Code and Codex histories — [Letta: Context Repositories](https://www.letta.com/blog/context-repositories)
- "Why Memory Isn't a Plugin" (Apr 2026, Letta CTO): "Asking to plug memory into an agent harness is like asking to plug driving into a car." "Retrieval is a small part of memory." Plugins can't control instruction-file loading, what survives compaction, or self-editing of system instructions — [Letta blog](https://www.letta.com/blog/why-memory-isnt-a-plugin/) **[VENDOR opinion]**
- Filesystem benchmark (Aug 2025): LoCoMo history placed in a file, with GPT-4o-mini using `grep`, `search_files` (semantic), and `open`/`close`, scored **74.0%** vs Mem0's reported 68.5% (graph variant). The conclusion: whether an agent remembers "depends more on its ability to use a retrieval tool than on the retrieval mechanism." Iterative re-querying beats single-shot retrieval — [Letta: Benchmarking AI Agent Memory](https://www.letta.com/blog/benchmarking-ai-agent-memory) **[VENDOR]**
- 2026 personal-agent posts: Letta Code App (Apr), Building Draft (Mar; "memory, reflection, and self-managed skills"), and Conversations (Jan; shared memory across concurrent experiences) — [Letta blog index](https://www.letta.com/blog)

**Hindsight (Vectorize)**
- Four memory networks: **world facts**, **experience** (agent first-person), **opinions with confidence scores**, and **observations** (entity summaries). Three operations: retain / recall (token-budgeted) / **reflect** (generates responses and *updates opinions*). TEMPR builds a temporal, entity-aware graph. CARA adds a behavioural profile — [arXiv 2512.12818](https://ar5iv.labs.arxiv.org/html/2512.12818v1)
- LongMemEval: 39% → **83.6%** with an open 20B backbone vs full context, and **91.4%** with a larger backbone. LoCoMo: 75.78% → 85.67% (20B) and **89.61%** (larger) — [arXiv 2512.12818](https://ar5iv.labs.arxiv.org/html/2512.12818v1) **[VENDOR paper]**

**Supermemory**
- MIT repo (31.3K stars). Local mode via `npx supermemory local` ("One binary. Zero config."), API at localhost:6767, local embeddings `bge-base-en-v1.5` by default, offline with Ollama. MCP tools: `memory` (save/forget), `recall`, `context` (profile injection). Clients include Claude Code, OpenClaw, and Hermes. It "tracks updates," "resolves contradictions," and expires temporary facts after their date. Open-core boundary unclear (an Enterprise tier exists) — [GitHub supermemoryai/supermemory](https://github.com/supermemoryai/supermemory)
- [VENDOR] LongMemEval-S **97% Recall@20 with aggregation** vs Zep 71.2%. Note this is a *retrieval recall* metric, not QA accuracy, so it is **not comparable** to Honcho's or Hindsight's accuracy figures — [Supermemory research](https://supermemory.ai/research.md)

**Graphiti (Zep)**: Apache-2.0, 31.9K stars. "Explicit bi-temporal tracking with automatic fact invalidation" (facts are invalidated, not deleted). Hybrid retrieval: embeddings + BM25 + graph traversal. MCP server included. Backends: Neo4j 5.26, FalkorDB, Neptune, and Kuzu (deprecated) — [GitHub getzep/graphiti](https://github.com/getzep/graphiti)

**Cognee**: Apache-2.0, 31.2K stars. Operations: remember / recall / improve / forget. Graph + vector + code context. `cognee-mcp` on port 8001. Postgres graph storage is "a demo feature." [VENDOR] BEAM 0.79 at 100K (20 questions, one conversation) and 0.67 at 10M (exploratory). It warns these aren't directly comparable. v1.6.1 dated Sep 24, 2026 — [GitHub topoteretes/cognee](https://github.com/topoteretes/cognee)

**Basic Memory (MCP)**: AGPL-3.0. A "file-first architecture" where markdown is the source of truth and "the database serves as a secondary index." Observations are written as `- [category] fact #tag` and relations as `relation_type [[Wiki Link]]`. YAML frontmatter. A file watcher syncs the index. Hybrid full-text + semantic search. `memory://` URLs with wildcards and graph traversal — [Basic Memory technical info](https://docs.basicmemory.com/reference/technical-information)

**Khoj**: AGPL-3.0, ~37.5K stars, "open-source, self-hostable. Always." Clients include Obsidian, Emacs, and WhatsApp. It is primarily semantic search over documents, and the README describes no persistent user memory — [GitHub khoj-ai/khoj](https://github.com/khoj-ai/khoj)

**Reor**: local-first, Ollama, plain .md notes. Maintenance status and licence were unverified from the source fetched — [devtoollab](https://devtoollab.com/ai-tools/reor)

**Limitless / Rewind**: Meta acquired Limitless (Dec 5, 2025). Rewind's Mac capture stopped Dec 19, 2025. Pendant sales stopped. Service was withdrawn from the EU, UK, and other regions, with data deleted after Dec 19, 2025 — [9to5Mac](https://9to5mac.com/2025/12/05/rewind-limitless-meta-acquisition/)

**Granola**: $125M Series C at a $1.5B valuation (Mar 25, 2026). MCP server launched Feb 2026. "Spaces" pools team meeting context into a role-gated shared knowledge graph. Positioned as an "enterprise AI memory layer" — [AI Automation Global](https://aiautomationglobal.com/blog/granola-125m-enterprise-ai-memory-2026) **[3P, low-reliability blog]**

### Inferences
- OpenClaw's 2026 builtin engine is effectively a free, MIT, production-hardened reference implementation of a "markdown + SQLite hybrid + recency + importance + MMR + provenance + supersession key" retriever. It is the best code to read before building. Its removal of cross-encoder reranking and HyDE in favour of fixed rules is a notable simplicity choice. Whether that cost accuracy is unmeasured.
- Letta MemFS and OpenClaw both point to **git as the memory audit log and concurrency control**. Every belief change becomes a diff, which answers the Dots "can't inspect" problem and makes rollback trivial.
- Hindsight's **separation of facts, experiences, and opinions-with-confidence** is the most explicit published schema for "facts about the user with confidence." Honcho's typed conclusions with premises are the alternative, without numeric confidence. Both are worth A/B testing.
- The demise of Rewind/Limitless and New Computer Dot shows that capture-everything and companion-only products struggled. Durable value accrued to memory *infrastructure* (Honcho, Supermemory, Granola MCP).

### Gaps
- Letta server/Letta Code licence was not verified in this pass (the Letta server repo is believed to be Apache-2.0, but this was unconfirmed here).
- Mem.ai, Rabbit, and Obsidian+AI plugins (Smart Connections, Copilot) were not researched due to the tool-call budget. Mem.ai's 2026 status is unknown.
- Basic Memory's MCP tool list, project partitioning, and DB backend were not captured.
- Granola details come from a low-reliability source.

## Q5. Cross-cutting patterns and file-based vs vector evidence

### Takeaway
Six patterns converge:
1. Small always-on core memory plus on-demand retrieval.
2. Markdown or git as the human-inspectable source of truth, with a derived hybrid index.
3. Background reflection, "dreaming," or "sleep-time" consolidation.
4. Skills as procedural memory with progressive disclosure.
5. Typed, provenance-bearing beliefs about the user.
6. MCP as the cross-tool interface, partitioned by workspace or peer.

The only measured file-vs-specialised-memory comparison is Letta's LoCoMo test (file + grep 74.0% vs Mem0 68.5%). It is vendor-run, on a small saturating benchmark. Anecdotal evidence warns that unbounded markdown memory accrues "prompt debt."

### Cited Findings
- **Bounded core memory:** Hermes caps memory at about 1,300 tokens with errors on overflow ([Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)). Letta pins only `system/` files ([Letta](https://www.letta.com/blog/context-repositories)). OpenClaw loads MEMORY.md only in private sessions ([OpenClaw mirror](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)).
- **Consolidation jobs:** Honcho's Dreaming Agent ([Honcho 3](https://honcho.dev/blog/blog/honcho-3)). Letta reflection subagents plus defragmentation to 15–25 files ([Letta](https://www.letta.com/blog/context-repositories)). Hermes periodic nudges ([Substack](https://mranand.substack.com/p/inside-hermes-agent-how-a-self-improving)). OpenClaw pre-compaction flush ([OpenClaw mirror](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)). Hindsight `reflect` updates opinions ([arXiv](https://ar5iv.labs.arxiv.org/html/2512.12818v1)).
- **Staleness handling:** Graphiti bi-temporal invalidation ([GitHub](https://github.com/getzep/graphiti)). OpenClaw supersession key + recency decay ([OpenClaw docs](https://docs.openclaw.ai/concepts/memory-builtin.md)). Supermemory supersedes contradictions and expires dated facts ([GitHub](https://github.com/supermemoryai/supermemory)). Honcho "identifies" contradictions, with the resolution undocumented ([Honcho docs](https://honcho.dev/docs/v3/documentation/core-concepts/reasoning)).
- **Independent probe on staleness:** in a 20-probe test of whether a system notices a changed fact, "the semantic-retrieval arm handed back the outdated fact on 19 of 20 probes." The system tested is not named in the excerpt — [Towards AI, Jul 2026](https://pub.towardsai.net/mem0-vs-zep-vs-letta-a-folder-of-text-files-shouldnt-beat-the-61k-star-memory-layer-9d7e65c5799c) **[3P, limited detail]**
- **Procedural memory:** Hermes SKILL.md with agentskills.io, auto-created after 5+ tool calls or corrections ([Substack](https://mranand.substack.com/p/inside-hermes-agent-how-a-self-improving)). Letta frontmatter modelled on SKILL.md ([Letta](https://www.letta.com/blog/context-repositories)).
- **MCP as interface:** Honcho MCP ([GitHub](https://github.com/plastic-labs/honcho)), Supermemory MCP with 3 tools ([GitHub](https://github.com/supermemoryai/supermemory)), Graphiti MCP ([GitHub](https://github.com/getzep/graphiti)), Cognee MCP ([GitHub](https://github.com/topoteretes/cognee)), Basic Memory ([docs](https://docs.basicmemory.com/reference/technical-information)), and Granola MCP ([AAG](https://aiautomationglobal.com/blog/granola-125m-enterprise-ai-memory-2026)). Counter-argument: memory is a harness responsibility, not a plugin ([Letta](https://www.letta.com/blog/why-memory-isnt-a-plugin/)).
- **Partitioning:** Honcho workspace per client and shared user peer for unified memory ([Honcho patterns](https://honcho.dev/blog/blog/common-patterns-for-building-with-honcho)). Hermes `sessionStrategy` per-directory/per-repo/per-session/global ([Honcho docs: Hermes](https://honcho.dev/docs/v3/guides/integrations/hermes.md)). OpenClaw per-agent index and private-only MEMORY.md ([OpenClaw mirror](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)). Honcho perspective-scoped peer models ([Peers](https://honcho.dev/blog/blog/introducing-peers)).
- **File vs vector, measured:** Letta file + grep/semantic search scored 74.0% on LoCoMo vs Mem0 68.5% ([Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory)). Supermemory claims its filesystem interface (SMFS) cuts cumulative tokens 3× on Claude and 1.75× on Codex over 110 questions ([Supermemory research](https://supermemory.ai/research.md)) **[VENDOR]**.
- **File-memory risk, anecdotal:** markdown memory accrues "prompt debt." Files grow to "thousands of lines," contradict themselves, and go stale, and agents drift silently. Based on one Reddit retrospective, with no benchmarks — [AI Weekly](https://aiweekly.co/alerts/markdown-agent-memory-accumulates-prompt-debt) **[3P, anecdotal]**
- **Security:** Hermes scans memory writes for injection and exfiltration patterns ([Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)). OpenClaw notes disk access is the trust boundary ([OpenClaw mirror](https://huggingface.co/spaces/nikhtu10/OpenClawBot/blob/main/docs/concepts/memory.md)).

### Inferences: patterns to adopt or test for the brain
1. **Hybrid architecture (recommended baseline):** use markdown or git as the canonical, human-editable store (Letta MemFS / Basic Memory style) with a derived SQLite or Postgres hybrid index (OpenClaw's recipe: BM25 + vector 0.3/0.7, ×4 candidates, recency decay, importance, MMR, provenance + supersession key). Add a separate asynchronous **user-model service** (Honcho, or a Hindsight-style opinions-with-confidence network) for derived beliefs. Expose all of it over MCP for Claude Code, and keep harness-level hooks (pre-compaction flush, session-start injection) because MCP alone can't control context (Letta's argument).
2. **Tiered memory with hard budgets:** core (≤~1–2K tokens, always on, capped with overflow errors) / episodic (FTS + vector archive, on demand) / procedural (SKILL.md, progressive disclosure) / user model (async reasoning, cached `context()` per turn plus agentic `chat()` on demand).
3. **Typed beliefs with provenance:** store each derived fact with type (explicit/deductive/inductive/abductive or world/experience/opinion), premises or source message IDs, observed time, valid-from/valid-to (Graphiti bi-temporal), and a supersession key. Never delete. Invalidate instead.
4. **Scheduled consolidation ("dreaming") with ablation:** run nightly. Test with and without it, because no vendor has published that ablation.
5. **Human-in-the-loop promotion for high-stakes or enterprise facts** (dotagents `rem`, Hermes `write_approval`, OpenClaw "promoted-trusted" recall).
6. **Inspectability as a hard requirement** (the Dots anti-pattern): every belief should be viewable, editable, and deletable, with a git history.
7. **Agentic iterative retrieval over single-shot:** Letta's result suggests the agent's search loop matters more than the index, so give Claude Code grep + semantic + graph tools and let it iterate.
8. **Test plan for the 90% at 10K+ standard:** benchmark on BEAM-1M/10M-like scale and on your own corpus. Weight temporal reasoning, knowledge-update/staleness (the 19/20 outdated-fact failure), and abstention, since these are where every published system is weakest. Treat LongMemEval-S and LoCoMo as saturated smoke tests only (Honcho's own admission).
9. **Licence screen:** Honcho (AGPL), Basic Memory (AGPL), and Khoj (AGPL) need care for a network-served enterprise product. Graphiti and Cognee (Apache-2.0) and Supermemory, OpenClaw, and Hermes (MIT) are permissive.

### Gaps
- There is **no independent, controlled file-vs-vector-vs-graph comparison** at 10K+ items. The Letta result is vendor-run on LoCoMo (~16K-token conversations, which Honcho calls not "useful at all" for evaluating memory).
- No published dreaming or reflection ablation exists from any framework.
- No benchmark covers multimodal (image and video) personal memory in these assistant frameworks. All published numbers are text-only.
- Cross-vendor numbers use different metrics (QA accuracy vs Recall@20 vs BEAM rubric) and judges, so leaderboard comparisons are unreliable.
