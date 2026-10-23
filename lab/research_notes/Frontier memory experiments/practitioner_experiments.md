# Practitioner Experiments in AI Assistant / Agent Long-Term Memory and Retrieval (2025–2026)

Scope note: Compiled 2026-10-23. Each entry says whether the evidence is **[MEASURED]** (numbers from a stated eval), **[VENDOR-MEASURED]** (numbers from the party that sells the system), or **[ANECDOTE]** (qualitative or n=1). "Test for us" lines in the Inferences sections are proposed experiments for the self-hosted brain (target: >=90% of tasks get every required context item in top-k). Many write-ups are from vendors. Their bias is flagged where relevant.

---

## Q1. Context engineering practice: what frontier teams (Anthropic, Manus, Cognition, LangChain, Dropbox) tried, measured and learned

### Takeaway
Across teams the pattern is the same. Keep the always-loaded context small and stable, so it hits the prefix cache. Push bulk content to files or tools and keep lightweight references to it. Isolate noisy work in sub-agents that return short summaries. Make compression restorable. Anthropic's internal agentic-search eval is the only published measurement that isolates memory and context management: memory tool plus context editing gave **+39%**, context editing alone gave **+29%**, and token use fell **84%** on a 100-turn task. The rest of the evidence is mostly design lessons with few numbers.

### Cited Findings
**Anthropic**
- [MEASURED, internal] Combining the memory tool with context editing improved performance by 39% over baseline on an internal agentic-search eval of complex multi-step tasks. Context editing alone gave 29%. In a 100-turn web-search eval, context editing cut token consumption by 84% (Sep 29, 2025). — [Claude: Managing context on the Claude Developer Platform](https://claude.com/resources/articles/context-management)
- [DESIGN] "Effective context engineering for AI agents" (Sep 29, 2025) lists the toolkit:
  - Compaction: Claude Code keeps the summary plus the 5 most recently accessed files. Tune the compaction prompt for recall first, then precision.
  - Tool-result clearing: the "lightest touch" form of compaction.
  - Structured note-taking: NOTES.md or a to-do list. In the Pokémon example the agent kept objectives across 1,234+ steps.
  - Sub-agents: each returns a condensed 1,000–2,000-token summary.
  - Just-in-time retrieval: hold file paths and queries as references and load data when needed.
  - Hybrid: CLAUDE.md is loaded up front and glob/grep handle the rest.
  - The article gives no benchmark numbers for compaction or note-taking. — [Anthropic Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [MEASURED, internal] Multi-agent research system (Jun 13, 2025):
  - An Opus 4 lead with Sonnet 4 sub-agents beat a single Opus 4 agent by 90.2% on an internal research eval.
  - On BrowseComp, token usage alone explained 80% of performance variance. Token usage, tool calls and model choice together explained 95%.
  - Multi-agent runs use about 15x the tokens of chat. Agents in general use about 4x.
  - The lead agent saves its plan to memory because context beyond 200K tokens is truncated.
  - Sub-agents write their outputs to external storage and pass references back.
  - Eval practice: they started with about 20 real queries, because early changes moved success from 30% to 80%. They used an LLM judge with a rubric. Human testers caught a bias toward SEO content farms that the judge missed. — [Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system)
- [DESIGN + failure modes] Long-running-agent harness (Nov 26, 2025, Justin Young):
  - An initializer agent writes `init.sh`, `claude-progress.txt`, a JSON feature list (200+ features, all marked failing) and an initial git commit.
  - Every later session reads the progress file, the git log and the feature list, runs a smoke test, does one feature, then commits.
  - They chose JSON over Markdown because "the model is less likely to inappropriately change or overwrite JSON".
  - Observed failures: trying to one-shot the whole app, declaring victory early, leaving undocumented state, and marking features passing without end-to-end tests. Explicit browser-automation testing "significantly improved" results. — [Anthropic Engineering](https://anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [MEASURED] Contextual Retrieval (Sep 2024, still the reference result). Top-20 retrieval failure rate (1 − recall@20):
  - Baseline: 5.7%.
  - Contextual embeddings: 3.7% (−35%).
  - Plus contextual BM25: 2.9% (−49%).
  - Plus reranking: 1.9% (−67%).
  - The added context is 50–100 tokens per chunk and costs about $1.02 per million document tokens. — [Anthropic](https://anthropic.com/news/contextual-retrieval)

**Manus (Yichao "Peak" Ji, Jul 18, 2025)**
- [DESIGN + numbers] They call KV-cache hit rate "the single most important metric".
  - The average input:output ratio is about 100:1. Cached Sonnet input costs $0.30/MTok versus $3/MTok uncached, a 10x gap.
  - Rules that follow: no timestamps in the prompt prefix, append-only context, deterministic serialization, and masking tool logits instead of removing tools.
  - Use the file system as restorable memory: drop a page but keep its URL.
  - Recite goals in a `todo.md`. A typical task takes about 50 tool calls.
  - Keep errors in context.
  - Add controlled variation to avoid few-shot ruts. In a 20-resume batch the agent drifted into a repetitive pattern.
  - They rebuilt the framework 4 times. — [Manus blog](https://manus.im/en/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [SECOND-HAND] One memory-vendor author cites about 30% token overhead from Manus constantly rewriting `todo.md`, and calls it a single example. — [Nicolò Boschi](https://buttondown.com/nicoloboschi/archive/file-based-agent-memory-great-demo-good-luck-in/)

**Cognition**
- [DESIGN, Jun 12, 2025] "Share full agent traces, not just individual messages" and "actions carry implicit decisions".
  - Flappy Bird failure example: parallel sub-agents produced a Mario-style background and a mismatched bird.
  - They recommend a dedicated, possibly fine-tuned, LLM to compress history. — [Cognition](https://cognition.com/blog/dont-build-multi-agents)
- [UPDATE, Apr 22, 2026] What works now is that "agents contribute intelligence... while writes stay single-threaded".
  - A code reviewer with **no** shared context works best, because it avoids context rot from the coder's history.
  - "Smart friend" pattern: a stronger model receives a fork of the full context, which they call the 80/20 solution.
  - Manager Devins split work into child Devins over an internal MCP. Failures: managers are too prescriptive, children assume shared state that doesn't exist, and cross-agent messages don't happen by default.
  - Unstructured swarms are "mostly a distraction".
  - Devin Review averages 2 bugs per PR, about 58% severe. — [Cognition](https://cognition.com/blog/multi-agents-working)

**LangChain (Jul 2, 2025)**
- [TAXONOMY] Four strategies: Write, Select, Compress, Isolate.
  - Memory misfire: ChatGPT injected Simon Willison's location into an image he asked for.
  - Retrieval over tool descriptions reportedly improved tool selection about 3x (per cited papers).
  - Windsurf found embedding search unreliable as codebases grow and combines grep, a knowledge graph and reranking.
  - Claude Code auto-compacts at 95% of the window. — [LangChain blog](https://langchain.com/blog/context-engineering-for-agents)

**Dropbox Dash (Josh Clemm, Jan 28, 2026)**
- [PRODUCTION LESSONS]
  - They chose an index over federated retrieval: "We do find the index is superior."
  - Graph databases were too slow, so they build graph relationships offline and compress them into "knowledge bundles". The bundles are chunked and embedded like any other document, so lexical and semantic search both reach them.
  - A canonical cross-app person ID is a key piece.
  - Context is capped at about 100K tokens. A simple MCP-based query could take up to 45 s, versus a few seconds with direct index access.
  - Fixes: replace 5–10 retrieval tools with one "super tool", store large tool results outside the context, and use classifier-routed sub-agents with narrow tool sets.
  - LLM relevance judge: disagreement with human labels started at 8% and fell further with required explanations, an upgrade to o3, and letting the judge fetch context. Later figures are not given.
  - DSPy optimizes the judge prompt. Dash has 30+ prompts edited by 5–15 engineers. — [Dropbox Tech](https://dropbox.tech/machine-learning/vp-josh-clemm-knowledge-graphs-mcp-and-dspy-dash)

**Context rot evidence (Chroma, Jul 14, 2025)**
- [MEASURED] Study of 18 LLMs:
  - Performance degrades with input length even on simple tasks.
  - Lower needle–question similarity makes the degradation faster.
  - One distractor hurts, and four hurt more.
  - Shuffled haystacks beat coherent ones across all 18 models.
  - On LongMemEval, focused prompts (about 300 tokens) beat full prompts (about 113K tokens) significantly for every model family, even with thinking enabled. — [Chroma Research](https://www.trychroma.com/research/context-rot)

**Tool overload as a retrieval problem**
- [VENDOR-MEASURED, Anthropic via third party] Tool Search Tool on MCP evals:
  - Opus 4 went from 49% to 74%. Opus 4.5 went from 79.5% to 88.1%.
  - Context fell 85%, saving about 191K tokens.
- [VENDOR-MEASURED, Stacklok] Stacklok's head-to-head on 2,792 tools, with one synthetic query per tool:
  - Their hybrid semantic+BM25 optimizer: 94% selection and 98% retrieval accuracy.
  - Anthropic's Tool Search Tool: 34% selection and 48% retrieval accuracy.
  - Stacklok is a competitor, and Anthropic's datasets aren't public. — [Stacklok](https://stacklok.com/blog/stackloks-mcp-optimizer-vs-anthropics-tool-search-tool-a-head-to-head-comparison/)

### Inferences
- The two largest measured context-engineering levers are smaller context (context rot, Chroma) and more relevant context (Contextual Retrieval, Anthropic's memory plus context editing). This supports a brain built to return a small, high-precision bundle, not a stuffed window.
- Prefix-cache discipline (Manus, Hermes, Mastra) is a design constraint on memory. The always-loaded profile or index should change rarely, for example once per session, while live updates go through tools.
- Dropbox's knowledge bundles are a practical answer to "graph DB too slow". Build relationships offline, then serialize them into retrievable text. This is cheap to test.
- **Test for us:**
  - (a) Measure recall@k on our gold set with and without contextual chunk headers (Anthropic-style 50–100-token context).
  - (b) Measure the A/B task-success effect of returning one bundled "context pack" versus raw top-k chunks.
  - (c) Measure tool-selection accuracy when the brain exposes one "super tool" versus 5+ specialised tools.

### Gaps
- No independent replication of Anthropic's +39% / +29% / −84% figures. The eval set isn't public.
- Dropbox did not publish its later judge-disagreement figures or end-to-end retrieval recall.
- No public quantitative comparison of compaction-prompt variants (recall versus precision tuning).

---

## Q2. File-based memory (CLAUDE.md / AGENTS.md, Markdown vaults, the "LLM wiki", memory in git) versus vector-DB memory: what's the evidence?

### Takeaway
Files plus agentic search (grep, read, an index file) match or beat specialised memory stores on **small conversational benchmarks**. Letta's grep-over-files agent scored 74.0% on LoCoMo versus Mem0's reported 68.5%. Files are also inspectable and versionable. But always-loaded instruction files show **small or negative effects** in controlled tests: about +4% for developer-written files, about −0.5% to −3% for LLM-generated ones, and 20%+ higher cost. Vercel's eval did find that a compressed docs **index** in AGENTS.md beat on-demand skills (100% vs 53–79%). The supported position is "files are necessary, not sufficient". Nobody has shown file-only memory holding up at 10K+ heterogeneous items.

### Cited Findings
- [VENDOR-MEASURED] Letta (Aug 12, 2025) loaded LoCoMo histories into a file and gave a GPT-4o-mini agent only grep, search_files and open/close.
  - Score: 74.0%, versus Mem0's reported 68.5% for its best graph variant.
  - Conclusion: "memory is more about how agents manage context than the exact retrieval mechanism". Retrieval-focused memory benchmarks may not be meaningful. — [Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- [COUNTER-ARGUMENT, memory vendor Hindsight, discloses bias] Boschi (Feb 2, 2026) argues files break in production:
  - Context rot, multi-hop chains (person → project → infra → incident), temporal queries, management overhead.
  - Indexing reportedly degrades around 2,500+ files, and files over 500KB are excluded.
  - He suggests files suit corpora under about 100K tokens. He admits he has no controlled benchmark. — [Nicolò Boschi](https://buttondown.com/nicoloboschi/archive/file-based-agent-memory-great-demo-good-luck-in/)
- [MEASURED, small] Grep smoke test (Ali Süleyman Topuz, Oct 10, 2026): 33 memory writes over 60 simulated days, 26 questions.
  - Raw grep: hit@1 19/26, hit@3 24/26, stale@1 2/6.
  - "Governed" grep (only active, unexpired entries): hit@1 21/26, hit@3 25/26, stale@1 0/6.
  - Paraphrase was the main failure. Supersession only worked when the new fact reused the old words. A recency tie-break made one query worse.
  - The embedding results are missing, and he calls it "a smoke test, not a benchmark". — [Towards AI](https://pub.towardsai.net/agent-memory-after-the-hype-what-jev-mem-knowledgex-and-blogwriter-taught-me-about-my-own-grep-5a021886fdb3)
- [MEASURED, academic] "Is Grep All You Need?" (arXiv 2605.15184, May 2026): on 116 LongMemEval questions run through the Claude Code, Codex and Gemini CLIs, grep generally beat vector retrieval. Scores depended strongly on harness and tool-calling style. The summary page gives no figures. — [DAIR.AI summary](https://academy.dair.ai/papers/is-grep-all-you-need)
- [MEASURED, peer-reviewed] "Evaluating AGENTS.md" (Gloaguen et al., ETH/LogicStar, arXiv 2602.11988, Feb 2026; ICLR 2026).
  - Setup: AGENTbench (138 instances, 12 repos) and SWE-bench Lite (300 tasks). Agents: Claude Code + Sonnet 4.5, Codex + GPT-5.2 / 5.1-mini, Qwen Code.
  - Developer-written context files: about +4% success.
  - LLM-generated files: −0.5% (SWE-bench Lite) to −2% (AGENTbench), about −3% in the intro.
  - Cost rose about 20–23% and steps rose 2.45–3.92.
  - Repository overviews didn't help, but non-standard instructions were followed. — [arXiv HTML](https://arxiv.org/html/2602.11988v1); [abstract](https://arxiv.org/abs/2602.11988v1)
- [MEASURED, vendor eval] Vercel (Jude Gao, Jan 27, 2026) tested Next.js 16 APIs absent from training data:
  - Baseline: 53%.
  - Skill with default behaviour: 53%. The skill was never invoked in 56% of cases.
  - Skill plus explicit instruction: 79%.
  - Compressed 8KB docs index in AGENTS.md (down from 40KB): 100% on build, lint and test.
  - Their explanation: passive context removes the decision point. — [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)
- [PRACTITIONER GUIDANCE] HumanLayer (Nov 25, 2025):
  - Frontier models follow about 150–200 instructions consistently (citing arXiv 2507.11538). Adherence decays uniformly as instructions are added.
  - Claude Code's system prompt already holds about 50 instructions, and CLAUDE.md is wrapped in a reminder saying it "may not be relevant".
  - Advice: under 300 lines (their own file is under 60), progressive disclosure via pointer files, prefer `file:line` pointers to copies, and don't auto-generate the file. — [HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [ANECDOTE, product decision] Claude Code's team tried local vector DBs and recursive model-based indexing. Agentic glob and grep "beat everything", and the alternatives had "stale indexes" and "permission complexity". No benchmark was published. — [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny?open=false)
- [ANECDOTE + design] Karpathy's "LLM wiki" (Apr 2026):
  - Layout: `raw/` holds immutable sources and `wiki/` is written by the LLM, with `index.md` and `log.md`.
  - Operations: ingest, query (good answers are written back into the wiki), and lint (contradictions, orphans, stale claims).
  - Scale: about 100 articles and 400K words, workable without RAG. Karpathy calls it a "hacky collection of scripts".
  - Critique: one hallucination can compound in shared memory. — [VentureBeat](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an); [adapted spec gist](https://gist.github.com/acmerfight/1c26b29ef39c0acc20f2e6f1f84e025f)
- [ANECDOTE] A practitioner ran Karpathy's method for half a day on 7 sources and compared it with 6 months of his own Obsidian + Claude Code system.
  - The structures were nearly identical. The differences were contradiction detection at ingest, cross-page updates (one source touching 10–15 pages) and periodic lint.
  - Ingest stalled on deciding topic boundaries, which he calls an ad hoc judgement. — [Yu Wenhao](https://yu-wenhao.com/en/blog/karpathy-zettelkasten-comparison/)
- [DESIGN] Letta Context Repositories (Feb 12, 2026):
  - Memory is a git repo of Markdown files with frontmatter. The file tree is always in the prompt, and `system/` files are always loaded in full.
  - Sub-agents write in isolated git worktrees and merge.
  - Background "reflection" saves information from recent conversations, and "defragmentation" restructures memory into 15–25 focused files.
  - No benchmarks. — [Letta](https://www.letta.com/blog/context-repositories)
- [ANECDOTE + one measurement] ADRs as memory (Tatsuya Shimomoto, Aug 2026).
  - Recommends Architecture Decision Records with status fields for superseded decisions, before trying memory RAG.
  - On local Ollama, a byte-identical system prompt prefilled about 600x faster (0.06 s vs 38.85 s cold).
  - Embedding clustering failed for skill dedup: shared boilerplate gave distinct skills cosine similarity of 0.90+ and merged 18 skills into one. One LLM call grouped them correctly. — [DEV](https://dev.to/shimo4228/claude-codes-memory-has-no-vectors-try-adrs-before-memory-rag-4kik)

### Inferences
- File-versus-vector is the wrong axis. The measured differences come from the **harness** (how well the agent searches), **governance** (supersession and TTL), and **what is always loaded versus fetched**.
- Vercel's result and the ETH AGENTS.md paper are consistent. A compact, high-signal **index of what exists** helps. Verbose overviews and instructions mostly add cost. For the brain, an always-loaded "map" (entity and topic index under about 8KB) plus fetch-on-demand bodies is the pattern with evidence behind it.
- Karpathy-style wikis are attractive for synthesis but have no recall measurements at our scale (10K+ multimodal items). Treat them as a *derived* layer over raw sources, not the source of truth.
- **Test for us:**
  - (a) Same gold set, three harnesses: grep/FTS-only agent, hybrid search tool, hybrid plus always-loaded index. Measure all-items-in-top-k.
  - (b) Measure task success with and without a compressed entity index in the system prompt.
  - (c) Track stale@1 with and without supersession governance (Topuz's metric).

### Gaps
- No public head-to-head of file/grep memory versus hybrid vector memory above about 5K documents with multimodal content.
- No measurement of LLM-wiki drift or compounding errors over months.
- The "Is Grep All You Need?" figures weren't available on the summary page.

---

## Q3. Personal AI / second-brain builders (OpenClaw, Hermes, Screenpipe, Limitless/Rewind, Granola, Obsidian vaults, consumer ChatGPT/Claude memory): what did they build and what broke?

### Takeaway
Hobbyist and indie personal assistants converged on Markdown memory files, daily logs, hybrid FTS+vector search and a pre-compaction "flush". The common failures are:
- Agents don't save on their own.
- Summaries lose detail.
- Keyword search misses synonyms.
- Projects bleed into each other.
- There is no provenance.
- Facts go stale or become false history.
- Memory files are injectable (MemGhost: 87.5% attack effectiveness on OpenClaw).

Consumer products (ChatGPT, Claude) converged on **a small editable profile plus on-demand search of raw past conversations**.

### Cited Findings
**OpenClaw (formerly Clawdbot/Moltbot)**
- [DESIGN] Default memory, per an analysis (Feb 2026):
  - Files: `MEMORY.md` holds curated facts and loads only in private sessions. `memory/YYYY-MM-DD.md` holds daily logs, and today's and yesterday's load at start. Session transcripts become searchable when enabled.
  - Hybrid search: 0.7 vector (sqlite-vec) + 0.3 BM25 (FTS5), weighted score fusion over a union of results with a 4x candidate multiplier. They chose this over RRF to keep score magnitude.
  - Chunks: about 400 tokens with 80-token overlap.
  - Pre-compaction flush: a silent turn at about 176K of 200K tokens asks the model to save durable memories. — [Shivam Agarwal](https://shivamagarwal7.medium.com/agentic-ai-openclaw-moltbot-clawdbots-memory-architecture-explained-61c3b9697488)
- [ANECDOTE] Failures (Feb 18, 2026): "Summaries lose details". The bot often fails to save context, especially during tool calls or multiple requests. Keyword search misses synonyms ("deployment pipeline" vs "CI/CD").
  - Fix: Tobi Lütke's QMD, which runs local BM25, vectors, query expansion and an LLM reranker through node-llama-cpp.
  - Measurements: semantic search ran out of memory on a Raspberry Pi 4 (4GB) but worked on an M1 (16GB). The reranker model is 1.28GB. Cold first query takes 10–30 s.
  - No retrieval-quality numbers. — [Travis Media](https://travis.media/blog/openclaw-memory-qmd-guide/)
- [ANECDOTE] Failures (Akshay Pachaar, Feb 17, 2026): compaction loses details, cross-project noise, no relationships, no provenance, no per-user isolation. Proposed fix: a Cognee knowledge-graph plugin running alongside the Markdown files. No benchmarks. — [Daily Dose of DS](https://blog.dailydoseofds.com/p/openclaws-memory-is-broken-heres)
- [DESIGN] The memory-wiki plugin (shipped in 2026.4.7) compiles memory into `entities/`, `concepts/`, `syntheses/` and `sources/` pages.
  - Pages hold structured claims with evidence and provenance. Generated blocks are managed, and human-written blocks survive regeneration.
  - Vault modes: isolated, bridge, or per-agent. — [OpenClaw docs](https://docs.openclaw.ai/plugins/memory-wiki)
- [VENDOR ANECDOTE, BetterClaw sells a competing host] Using memory-wiki:
  - The agent ignored the wiki until a SOUL.md line told it to check first.
  - `wiki_search` missed facts in MEMORY.md because the corpus defaulted to the wiki only.
  - Search broke after the 2.0 upgrade until the index was rebuilt.
  - Claims carry confidence scores (example values 0.92 and 0.88). Daily notes lose half their weight every 30 days. — [BetterClaw](https://www.betterclaw.io/blog/openclaw-memory-wiki-guide)
- [ANECDOTE, vendor blog] A practitioner settled on SQLite FTS5 plus local Ollama embeddings with strict namespaces to prevent "knowledge bleed" between agents and clients. Rejected options: pure vectors (weak on identifiers and names) and FTS alone (misses paraphrase). No measurements. — [DEV / Standard Compute](https://dev.to/lars_winstand/i-finally-found-an-openclaw-memory-setup-id-trust-with-my-real-notes-369l)

**Hermes Agent (Nous Research)**
- [DESIGN] "Bounded, curated memory":
  - `MEMORY.md` is capped at 2,200 characters (about 800 tokens) and `USER.md` at 1,375 characters (about 500 tokens).
  - An overflow returns an error, and the agent must consolidate in the same turn.
  - Memory is a frozen snapshot per session so the prefix cache stays valid. Mid-session writes apply next session.
  - Tool actions are add, patch and remove. A full "replace" was removed because it overwrote multi-fact entries.
  - SQLite FTS5 session search returns raw messages, with no LLM summarization.
  - Skills serve as procedural memory.
  - Writes are scanned for injection and invisible Unicode, and an optional write-approval step exists. — [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)

**Consumer assistants**
- [OBSERVATIONAL, external reverse engineering] Shlok Khemani (AI Engineer World's Fair 2026):
  - ChatGPT's saved-facts list (Feb 2024) went stale.
  - Its running profile (about 4K tokens, refreshed every few days, from Apr 2025) merged a *considered* Turkey trip with the *actual* Thailand trip. It "converted uncertainty into false history" and couldn't be inspected.
  - Claude started with on-demand search of past chats (Aug 2025), then added an editable profile of about 1K tokens refreshed every 24h.
  - By 2026 both converged on a profile plus search.
  - His summary: "Memory is a function of compute" and is capped by the context it can gather (bookings made in email were never seen). — [AI Engineer talk](https://ai.engineer/talks/lessons-from-studying-every-memory-system)
- [OPINION] Simon Willison prefers Claude's memory as "visible tool calls" (`conversation_search`, `recent_chats`) over ChatGPT's automatic injection (Sep 12, 2025). — [Simon Willison](https://simonwillison.net/2025/Sep/12/claude-memory/)
- [ANECDOTE] Mike Taylor (Head of Evals at Every) turned ChatGPT memory off (Feb 2026).
  - A Kanye quote in his custom instructions skewed a website task.
  - Rib advice seemed tailored to his zip code.
  - He calls the build-up of stale preferences "context rot". — [Every](https://every.to/also-true-for-humans/why-i-turned-off-chatgpt-s-memory)

**Lifelogging and meeting memory**
- [DESIGN] Screenpipe:
  - Capture is event-driven (app switch, click, typing pause) rather than continuous. The accessibility tree comes first, with OCR as fallback, and Whisper transcribes audio.
  - Storage is SQLite FTS5 plus media files, queried over MCP and REST.
  - Resource use: about 5–20% CPU and 0.5–3GB RAM. Telemetry is on by default. — [Screenpipe README](https://cdn.jsdelivr.net/gh/screenpipe/screenpipe@main/README.md)
- [VENDOR-REPORTED, competitor] Rewind/Limitless:
  - Rewind began local-first, then pivoted to the cloud and a pendant.
  - Meta acquired Limitless on Dec 5, 2025. Screen and audio capture were disabled Dec 19, 2025, and the export window closed.
  - Lesson: data ownership matters as much as features. Dates are unverified in that source. — [Screenpipe blog](https://screenpipe.com/blog/rewind-ai-alternative-2026)
- [PRODUCT] Granola rebuilt "agentic" Chat across thousands of notes, team spaces and shared notes (Apr 21, 2026).
  - Added inline citations and a "which notes I used" disclosure so users can redirect it.
  - No retrieval method or numbers disclosed. — [Granola](https://www.granola.ai/blog/granola-chat-just-got-smarter)

**Obsidian vaults plus coding agents**
- [ANECDOTE] Steve Phelps (Feb 2026) runs a flat Obsidian vault with hierarchical tags and wiki-links, plus four Claude Code skills: vault manager, vault auditor (reports inconsistencies with severity ratings), Notion sync (human-confirmed preview) and a WIP dashboard. No measurements or failures reported. — [The Life Algorithmic](https://sphelps.substack.com/p/a-shared-memory-for-claude-code)

**Security**
- [MEASURED, security research] MemGhost (CSA, Jul 2026): one crafted email makes the agent write false facts into MEMORY.md.
  - Effectiveness: 87.5% on OpenClaw/GPT-5.4 and 71.4% on a Claude Code SDK agent (Sonnet 4.6). Injection success was 96.4%.
  - Payloads transferred to NanoClaw, Hermes and Mem0.
  - Mitigations: a reader agent without write access, approval before writing externally sourced facts, and provenance tags plus a write log. — [Cloud Security Alliance](https://labs.cloudsecurityalliance.org/research/csa-research-note-memghost-ai-agent-memory-injection-2026072/)

### Inferences
- The recurring indie failure is *write-side*: deciding what to save and when. Retrieval is less often the problem. Pre-compaction flushes, background consolidation and observer agents all address it, but none has published recall numbers in a personal setting.
- For our partitions requirement, the OpenClaw "knowledge bleed" complaints and per-agent vaults (described as a "process-level boundary, not an OS security boundary") show that namespace isolation must be enforced in the retrieval service, not by prompt.
- Khemani's Turkey/Thailand case is a concrete test-case template: considered versus actual events. Store event status (planned, cancelled, done) and ask rather than assert.
- MemGhost makes memory-write provenance and approval for externally sourced content a requirement, not an option.
- **Test for us:**
  - (a) Seed the gold set with "considered versus actual" pairs and synonyms (CI/CD vs deployment pipeline).
  - (b) Red-team writes with injected emails and measure the rate of false facts persisted.
  - (c) Measure cross-partition leakage rate (should be 0) under adversarial queries.

### Gaps
- No published recall or accuracy evaluation from any indie personal-assistant memory setup (OpenClaw, Hermes, QMD, Screenpipe).
- Couldn't find first-hand technical post-mortems from Khoj or Basic Memory maintainers in 2025–26.
- No measured data on Granola's or Limitless's retrieval quality.

---

## Q4. Memory hacks in coding agents (Claude Code, Cursor, Codex, Devin): memory banks, rules files, skills, session search, semantic vs grep. What's the evidence?

### Takeaway
The only rigorous online evidence comes from Cursor's A/B test. Semantic search plus grep beat grep alone: +12.5% offline accuracy, +2.6% code retention in 1,000+ file repos, and 2.2% fewer dissatisfied follow-ups. Auto-memory features (Claude Code auto memory and /dream, Cursor Memories) bring silent truncation, drift, consolidation that deletes needed facts, and growing overconfidence. Skills (procedural memory) fail when they aren't triggered (56% never invoked in Vercel's eval).

### Cited Findings
- [MEASURED, vendor A/B] Cursor (Nov 6, 2025):
  - Offline Context Bench: semantic search gave +12.5% average accuracy (range 6.5–23.5% by model).
  - Online A/B: code retention +0.3% overall and +2.6% on 1,000+ file repos. Without semantic search, dissatisfied follow-ups rose 2.2%.
  - The embedding model was trained on agent-session traces, with an LLM ranking which content would have helped at each step.
  - "Combining it with grep gives the best outcomes." — [Cursor](https://cursor.com/en-US/blog/semsearch)
- [MEASURED, small] turbopuffer (Kuba Rogut, AI Engineer Europe 2026), 50 tasks scored against ContextBench-style annotations:
  - File precision: 65% for stock Claude Code versus 87% with windowed reads plus semantic search.
  - Off-target reads fell from about 1 in 3, to 1 in 5 (windowed reads), to 1 in 8 (windowed plus semantic).
  - Stock Claude Code had the highest file recall but the weakest line recall.
  - Semantic search helped when related files used different keywords. Grep was better for tracing imports.
  - Claude Code "isn't good at deciding when" to use an added semantic tool. turbopuffer sells vector search. — [AI Engineer](https://ai.engineer/talks/zKk7sDMGDEQ-benchmarking-semantic-code-retrieval-on-claude)
- [VENDOR-MEASURED, Morph] 500 tasks across 50 repos:
  - Grep only: 64.2%. Semantic only: 71.8%. Combined: 84.1%.
  - On 1,000+ file repos: 52.3%, 66.1% and 81.7% respectively.
  - Few methodological details. — [Morph](https://morphllm.com/blog/semantic-search)
- [ANECDOTE, 2 weeks] Claude Code /dream (Mejba Ahmed, Mar 2026):
  - It triggers after more than 24h and at least 5 sessions. It converts relative dates to absolute, resolves contradictions by recency, merges duplicates and rebuilds a MEMORY.md index under 200 lines.
  - Benefit: answers became "more committed".
  - Failures: deleting superseded entries removed facts he still needed. Recency resolution keeps the wrong version after a correction is reverted. It can't tell a stale debug note from a recurring bug.
  - Mitigation: keep memory in git and review each diff. — [mejba.me](https://www.mejba.me/blog/claude-code-autodream-tested)
- [ANECDOTE] Claude Code auto memory pitfalls:
  - "Only the first 200 lines get loaded". Entries past that are silently ignored, and freshness warnings don't fire for unloaded entries.
  - Drift: one illustration has 15 feedback entries after 6 weeks, 2 contradictory.
  - "Consolidation isn't verification." The agent grows more confident while becoming less accurate. — [blume.codes](https://blume.codes/blog/claude-code-has-a-memory-now-thats-the-good-news-and-the-bad-news)
- [USER REPORTS] Cursor Memories (Aug 2025 forum thread): memories were machine-specific, capture was "random and arbitrary", there was no scoping, export or manual add, and precedence versus rules was unclear. The author stopped accepting new memories. — [Cursor Forum](https://forum.cursor.com/t/saved-memories-in-cursor-and-their-viability/128968)
- [DESIGN, vendor claim] claude-mem:
  - Lifecycle hooks capture tool use. An LLM compresses observations into SQLite FTS5, with Chroma optional.
  - Search is three-layer progressive disclosure: search, then timeline, then get_observations.
  - The project claims about 2,250 tokens saved per session versus MCP, with method unstated. — [claude-mem docs](https://docs.claude-mem.ai/architecture/overview)
- [DESIGN] Anthropic Agent Skills (Oct 16, 2025):
  - Three-level progressive disclosure: name and description in the system prompt, SKILL.md body on trigger, linked files on demand.
  - Advice: start with evaluation, and watch how Claude uses the name and description to decide triggering. — [Anthropic Engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [MEASURED] Skills went uninvoked in 56% of Vercel eval cases (see Q2). — [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)

### Inferences
- In coding agents, hybrid retrieval (lexical plus a trained or strong embedding) gives a reliable gain that grows with corpus size. That size dependence is directly relevant to the 10K+ item target.
- Whether the agent calls the memory tool at all is a first-order failure mode (Vercel 56%, Rogut). The brain should push a small top-k bundle automatically on each turn, as OpenClaw auto-recall and Mastra do, rather than relying only on agent-initiated search.
- Auto-consolidation needs version control and review diffs. Recency-wins conflict resolution is a known bug source.
- **Test for us:**
  - (a) Agent-pull versus system-push retrieval: measure tool-invocation rate and all-items-in-top-k.
  - (b) Run consolidation over a seeded memory with known "correction then revert" sequences and recurring-bug notes, and count wrongful deletions.

### Gaps
- No public numbers on Claude Code auto memory or /dream quality (Anthropic hasn't published, and practitioners only report anecdotes).
- Devin and Codex memory features: found no measured practitioner evidence.

---

## Q5. Retrieval tuning stories with before/after numbers: which specific changes moved the number?

### Takeaway
The changes that repeatedly moved recall were:
- Hybrid BM25 plus dense, the largest and most consistent gain.
- Contextual chunk headers.
- Rerankers, which add latency.
- Better parsing of visual documents.
- Bigger chunks and higher top-k in one KB setting.
- Direct multimodal embeddings over caption-then-embed.

Several popular tricks failed on enterprise data even after helping on academic sets: RAG-Fusion multi-query, many score-fusion variants, LLM synonym enrichment, truncated vectors and relation graphs. **Validate on your own enterprise-like data.**

### Cited Findings
- [MEASURED] AIUI (Sep 20, 2026), with enterprise Jira, GitHub and Confluence sets plus BEIR. Recall@10 going from BM25 to hybrid:
  - erag-jira: 79.7% → 93.1%.
  - erag-confluence: 60.6% → 79.8%.
  - erag-3src (19,361 docs, 178 queries): 70.8% → 86.3%.
  - fiqa: 31.3% → 45.7%.

  Single-change trials on top of hybrid:
  - Convex fusion α=0.2 *hurt* Jira (R@10 0.931 → 0.881).
  - RRF k 120 → 40 failed on Jira.
  - Dense pseudo-relevance feedback failed.
  - LLM-generated synonyms added BM25 noise.
  - Relation-graph edges failed on GitHub ($7.13).
  - 768-d and 1024-d truncated vectors regressed slightly.
  - Subtopic chunking and sibling-chunk graph collapse regressed.
  - Reranking the top 200 gave the largest top-10 gain (e.g. SciFact +6.4 points) but costs 2.6 s per query uncached.
  - A free "same-title group boost" was accepted (+1.7 points R@10 on ArguAna).
  - Notably, 59 of 60 missed ArguAna documents were one hop from the top 10, yet term-sharing relations couldn't find them. — [AIUI](https://aiui.tech/blog/recall-experiments-week-one/)
- [MEASURED] Contextual Retrieval: 49% fewer top-20 failures with contextual embeddings plus BM25, and 67% fewer with a reranker added (see Q1). — [Anthropic](https://anthropic.com/news/contextual-retrieval)
- [MEASURED, industry deployment] RAG-Fusion (Medrano et al., arXiv 2603.02153, Mar 2026): fusion raised raw recall, but the gains vanished after reranking and truncation. No variant beat the single-query baseline, and Hit@10 fell from 0.51 to 0.48 in several configurations while latency rose. — [arXiv](https://arxiv.org/abs/2603.02153v1)
- [VENDOR-MEASURED] Salesforce Data 360 (Sep 2, 2026):
  - Intelligent parsing (vision models for visual pages), on OHR-Bench v2: end-to-end 65% → 84.4%, charts 57.9% → 76.3%, reading order 11.9% → 67.1%.
  - Enriched indexing (titles, keywords, summaries, generated questions) added +2.4 points.
  - On WixQA, three config changes took accuracy from 62.5% to 92.5%: chunk size 512 → 2048, top-k 10 → 30, and a domain-tuned prompt. — [Salesforce Developers](https://developer.salesforce.com/blogs/2026/09/improve-enterprise-rag-accuracy-in-data-360)
- [MEASURED, small] Lumer et al. (arXiv 2511.16654, Nov 2025), financial earnings-call benchmark with 40 QA pairs: direct multimodal embeddings beat LLM-caption-then-embed by +13 points mAP@5 (32% relative) and +11 points nDCG@5 (20% relative). — [arXiv](https://arxiv.org/abs/2511.16654v1)
- [PRACTITIONER] Multimodal production notes (May 2026):
  - Caption-then-embed loses information, and tables collapse into linear text.
  - ColPali needs about 1,000 × 128-d vectors per page, roughly 8–10x the storage.
  - CLIP degrades on technical diagrams.
  - Labelling chunks by source and modality reduced cross-modal hallucination.
  - Video and audio retrieval are not first-class in any framework. — [Towards AI](https://pub.towardsai.net/multimodal-rag-architecture-tradeoffs-and-what-actually-works-in-production-4cf436f048be)
- [PRACTITIONER, Jason Liu playbook]
  - Synthetic per-chunk questions as a recall baseline, aiming for about 80–90%. On GitHub issues, full-text reached about 55% recall versus about 65% for embeddings.
  - Feedback-button copy change took feedback rate from 0.5% to 8.2%.
  - Segmentation: a 70% overall satisfaction hid scheduling queries at 35%.
  - Temporal-capability issues were about 40% of failures in one case.
  - Illustrative trade-offs: hybrid +12% recall for +25% latency, and a reranker +8% recall for +200% latency. — [Decoding ML](https://decodingml.substack.com/p/the-real-battle-tested-rag-playbook)
- [PRACTITIONER, Hamel Husain's RAG series]
  - Late interaction on BRIGHT: 19.61 versus 12.31 for dense with the same backbone. Reason-ModernColBERT (150M) beat 7B models.
  - Rank1 reasoning reranker: training on reasoning traces added about 10 points.
  - Bryan Bischof: build multiple "maps" (summaries, tables, entities) and route queries, using an LLM router for a few routes and a classifier for many.
  - Jo Bergum: exhaust simpler options before graph DBs, and for about 300 documents just stuff the context. — [hamel.dev](https://hamel.dev/notes/llm/rag/beyond-naive-rag.html)

### Inferences
- Default stack with measured support: hybrid BM25 plus dense, contextual chunk headers, a reranker on the top 50–200, vision-aware parsing for documents, and direct multimodal or late-interaction embeddings for images and pages.
- Things to *not* assume will help without testing on our data: query fusion and multi-query, fusion-weight tweaks, LLM keyword expansion, graph edges for recall, Matryoshka truncation.
- Salesforce's chunk 2048 / top-k 30 result shows that "required items in top-k" depends heavily on k and chunk granularity. Set k from the context budget and evaluate at several k.
- **Test for us:** an ablation ladder on our own gold set, adding one change at a time, with a held-out enterprise-like slice as a veto set. This is AIUI's method: a change must not regress any enterprise source.

### Gaps
- Few enterprise write-ups give end-to-end before/after numbers with methods. Many "60% → 95%" blog posts found were marketing without methodology and were excluded.
- No measured production numbers on query routing or metadata filtering specifically.

---

## Q6. Evaluation in the wild: how small teams build gold sets, use production failures and calibrate LLM judges

### Takeaway
Practitioners agree on the following:
- Error-analyse real traces first.
- Evaluate retrieval separately from generation, using recall@k for first-pass retrieval.
- Build gold sets from real queries plus filtered synthetic and adversarial questions.
- Use binary judges calibrated against human labels.
- Start small: about 20 queries finds big effects, and about 200 labels with 50–100 failures calibrates a judge.

Public memory benchmarks (LoCoMo, LongMemEval) are contested and partly gamed, so they can't replace a domain gold set.

### Cited Findings
- [METHOD] Hamel Husain's evaluate-rag skill:
  - Synthetic QA: one fact per chunk, then one question that fact answers.
  - Adversarial questions: use the vocabulary of similar distractor chunks to ask a question only the target chunk answers.
  - Filter synthetic questions with a few-shot 1–5 realism score and keep 4–5.
  - Optimise recall@k first-pass and precision, MRR or NDCG for reranking.
  - Treat chunking as a hyperparameter to grid-search.
  - Two-hop recall@k: both gold chunks must appear in the top k. — [Tessl registry (hamelsmu/evals-skills)](https://tessl.io/registry/skills/github/hamelsmu/evals-skills/evaluate-rag)
- [METHOD] Eugene Yan (Nov 23, 2025):
  - Use binary pass/fail and avoid 1–5 scales. Collect 50–100 failures and at least 200 samples.
  - Build one evaluator per dimension, with a 75/25 dev/test split.
  - Target Cohen's κ of 0.4–0.6 (substantial) or above 0.7 (excellent). Human-human κ is often 0.2–0.3.
  - Margin of error: n=200 at a 3% defect rate gives about ±2.4%. — [eugeneyan.com](https://eugeneyan.com/writing/product-evals/)
- [MEASURED, academic] Synthetic versus human benchmarks (van Elburg et al. 2025, about 100 questions × 4 datasets): synthetic sets ranked *retriever* configurations reliably (Kendall τ 0.67–0.84), but generator rankings were inconsistent. — [Beri.net summary](https://www.beri.net/article/rag-evaluation-dataset-200-hand-written-questions-synthetic-ragas-deepeval-langfuse-2026)
- [PRODUCTION] Dropbox calibrated its LLM relevance judge to engineer labels (8% initial disagreement) and used DSPy to optimise against listed disagreements (see Q1). — [Dropbox Tech](https://dropbox.tech/machine-learning/vp-josh-clemm-knowledge-graphs-mcp-and-dspy-dash)
- [PRODUCTION] Anthropic started with about 20 real queries and used a rubric judge plus human review, which caught source-quality bias (see Q1). — [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- [BENCHMARK CRITIQUE] LoCoMo:
  - The harness drops category 5, the 446 adversarial or abstention questions (22.5%).
  - The answer prompt forbids "not specified".
  - The judge allows ±14 days.
  - An independent audit found the judge accepts 62.8% of deliberately wrong answers and the key is partly corrupted, putting the honest ceiling around 93.6. — [DEV](https://dev.to/gde03/the-ai-memory-benchmark-everyone-quotes-forbids-saying-i-dont-know-o1n)
- [BENCHMARK DISPUTE] Zep says LoCoMo conversations (16–26K tokens) fit in context, so full-context beats memory systems, and that the benchmark lacks knowledge-update questions. Zep reports its corrected score as 75.14% versus Mem0's reported 65.99% for Zep. — [Zep](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- [VENDOR SCORES, unreplicated] Vendor-reported scores, per a compilation:
  - Mem0: 94.4% LongMemEval and 92.5% LoCoMo, with GPT-5 as reader at top-200. Its committed traces show 93.4% / 90.4%.
  - Zep: 90.2% LongMemEval and 94.7% LoCoMo. Retrieval p50 is 104 ms.
  - No neutral harness exists, and at BEAM's 10M-token setting Mem0 scores 0.486. — [Particula](https://particula.tech/blog/agent-memory-frameworks-tested-mem0-zep-letta-cognee-2026)
- [DATASET ANALYSIS] LongMemEval: 500 questions, of which temporal reasoning is 133 (27%) and knowledge update is 78 (16%). About 50 sessions per question with 2–3 containing the answer. 30 abstention questions. Report sub-scores rather than one number. — [DEV (Preeti Soni)](https://dev.to/preeti_2528/what-temporal-reasoning-actually-means-in-longmemeval-1llh)
- [MEASURED, academic] FORGETEVAL (Yang, arXiv 2606.15903, Jun 2026): MemPalace scored 0/385 on adversarial forgetting but 60/150 on the Memora recall benchmark. Recall benchmarks don't measure correct forgetting. — [arXiv](https://arxiv.org/pdf/2606.15903)

### Inferences
- Our ">=90% of tasks with every required item in top-k" metric matches Hamel's multi-hop recall@k (all gold items present). It should be reported per slice: temporal, update, multi-hop, multimodal, abstention, partition-boundary.
- Gold-set recipe with practitioner support:
  1. Real queries and production failures.
  2. Synthetic per-item questions filtered for realism (fine for *ranking retrievers*).
  3. Adversarial distractor-vocabulary questions.
  4. Forgetting and supersession cases, FORGETEVAL-style.
  5. Abstention decoys.
- Don't use LoCoMo scores to pick a vendor. Run a neutral harness on our own data.

### Gaps
- No public example of a team publishing a 10K+ item multimodal gold set with all-items-in-top-k results.
- Limited evidence on how many gold queries are needed for stable per-slice estimates at a 90% target. Yan's margin-of-error maths implies a few hundred per slice.

---

## Q7. Unconventional ideas people are trying: memory gardeners and sleep-time consolidation, entity pages with claims and evidence, temporal validity, observational memory, KG+Markdown hybrids, MCP memory servers, access partitions

### Takeaway
The most promising tested ideas share one trait: they treat **fact lifecycle** as a first-class concern.
- Explicit supersession and validity intervals: stale-fact error went from 15–40% to about 0% on structured tests.
- Claims with evidence versions: stale claims per update went from 80 to 9, and hallucinated claims from 15 to 0.
- Relational versioning plus dual timestamps.
- Observer and reflector compression: 84–95% on LongMemEval without per-query retrieval.

Sleep-time consolidation is widely deployed but unmeasured in practice, and it brings over-consolidation risks. KG layers are popular in plugins, but measured recall gains from graphs were negative in the one independent ablation found (AIUI).

### Cited Findings
**Lifecycle, supersession and temporal validity**
- [MEASURED, single author] MemStrata (arXiv 2606.26511, Jun 2026):
  - Mechanism: normalise (subject, relation) keys. A new object closes the old row's `valid_to` and links `superseded_by`. Only active rows are retrievable. No LLM is on this path.
  - Evolving-knowledge tasks: 0.95–1.00 versus RAG's 0.20–0.47.
  - When forced to answer, RAG served the superseded value 15–40% of the time, versus about 0% for MemStrata.
  - Ablation: removing supersession dropped accuracy from 0.99 to 0.33.
  - Limitations: templated single-value facts. Extraction keyed on only about 44% of messy natural-language scenarios.
  - Cosine similarity can't separate contradictions from duplicates (AUROC 0.59). — [arXiv](https://arxiv.org/pdf/2606.26511)
- [MEASURED, academic] FORGETEVAL across 13 configurations:
  - An LLM hook at *mutation time* (planning supersede and purge actions when memory changes) scored 91.7–93.2%, versus 63–68% for deterministic stores. Cost is about $0.17 per 385-case run at about 2.3 s per mutation.
  - An LLM at *inscribe time* (Mem0 v3 infer) fell to 43.6% because it keeps old facts alongside new ones.
  - The lift depends on JSON-following: Llama-3.1-70B failed the contract. — [arXiv](https://arxiv.org/pdf/2606.15903)
- [MEASURED, vendor] LangChain OpenWiki "self-correcting memory" (Colin Francis, Aug 25, 2026):
  - Every wiki claim stores its code evidence and an evidence version. A changed version marks the claim stale, a deterministic check with no LLM call. Stale claims are re-verified on update.
  - Evaluation replayed git history across 2,000 claims:
    - Supported: 92.9% → 97.8%.
    - Stale: 3.5% → 0.5%.
    - Hallucinated: 0.7% → 0%.
    - Stale claims per update: 80 → 9. Hallucinated claims: 15 → 0.
  - Lesson: "Forgetting means flagging beliefs for review, not deleting them." — [LangChain blog](https://langchain.com/blog/self-correcting-memory-openwiki)
- [VENDOR-MEASURED] Supermemory on LongMemEval-S, recall@20 with aggregation:
  - Temporal: 95% (Zep 62.4%, full context 45.1%). Knowledge update: 100%. Multi-session: 96%.
  - Techniques: atomic memories linked to their source chunk (both returned), relational versioning (updates, extends, derives), dual timestamps (document date and event date), session-level ingestion.
  - LLM-judge accuracy is lower: about 75–90% by category with GPT-5. — [Supermemory](https://supermemory.ai/research/longmembench)
- [ANECDOTE, failure] Mem0's auto conflict resolution silently DELETEd a still-valid, context-scoped preference (async feedback for design reviews versus sync calls for incidents). It was noticed weeks later.
  - Fixes: scope-tag the fact text, add an audit wrapper that diffs memories before and after each `add()`, and recover with `history()`. — [DEV (Mukesh)](https://dev.to/mukesh_13/mem0-auto-resolves-memory-conflicts-for-you-until-it-silently-deletes-one-you-still-need-4f4m)

**Observer / reflector ("observational memory")**
- [VENDOR-MEASURED] Mastra Observational Memory (Tyler Barnes, Feb 9, 2026):
  - Two background agents. The Observer turns messages into dated notes with emoji priorities. The Reflector merges notes and drops superseded ones.
  - Observations sit in a stable prefix, so the cache is hit, and there is no per-query retrieval.
  - LongMemEval-S scores: 84.23% with gpt-4o (above the 82.4% oracle), 93.27% with gemini-3-pro and 94.87% with gpt-5-mini. Knowledge-update reached 96.2% and temporal 95.5% (gpt-5-mini).
  - Compression is about 6x on text and 5–40x on tool-heavy workloads (anecdotal). Multi-session tops out around 87%. — [Mastra Research](https://mastra.ai/research/observational-memory)

**Sleep-time / "memory gardener" consolidation**
- [DESIGN] Letta sleep-time agents (Apr 2025): a separate agent owns memory-block edits and runs asynchronously, possibly on a bigger model. The research results are on math benchmarks (AIME and GSM), not memory recall. — [Letta](https://letta.com/blog/sleep-time-compute)
- [COMMUNITY PRACTICE] Letta forum (Jan 6, 2026):
  - Schedule: dedup on every pass, light consolidation at session end, weekly reorganisation, monthly roll-ups.
  - "Don't over-consolidate - you lose granularity."
  - Observed problems: "auth" not matching "authentication", recency bias, "consolidation debt", flat compound tags.
  - Fixes: hierarchical tags (`project:slate`), and "reference count matters more than age". — [Letta Forum](https://forum.letta.com/t/sleeptime-agents-for-memory-consolidation-best-practices-guide/154)
- [DESIGN] Honcho "dreaming":
  - Triggers when at least 50 new conclusions exist, at least 8h have passed and the user has been idle 60 min.
  - A deduction agent replaces outdated facts and flags contradictions. An induction agent proposes patterns backed by at least 2 conclusions, with confidence levels.
  - Dreams are scoped per (workspace, observer, observed) tuple. No metrics published. — [Honcho docs](https://honcho.dev/docs/v3/documentation/features/advanced/dreaming)
- [ANECDOTE] Claude Code /dream and its failure modes (see Q4). — [mejba.me](https://www.mejba.me/blog/claude-code-autodream-tested)

**KG + Markdown hybrids and entity pages**
- [DESIGN] OpenClaw memory-wiki (entity and concept pages with claims and provenance, human blocks preserved) and the Cognee graph plugin alongside Markdown. Neither has published measurements. — [OpenClaw docs](https://docs.openclaw.ai/plugins/memory-wiki); [Daily Dose of DS](https://blog.dailydoseofds.com/p/openclaws-memory-is-broken-heres)
- [PRODUCTION] Dropbox: build graph relationships offline, serialize them into retrievable "knowledge bundles", and use a canonical person ID instead of a live graph DB. — [Dropbox Tech](https://dropbox.tech/machine-learning/vp-josh-clemm-knowledge-graphs-mcp-and-dspy-dash)
- [MEASURED, negative] AIUI: relation-graph edges and graph collapse over sibling chunks *regressed* or failed on enterprise sets (see Q5). — [AIUI](https://aiui.tech/blog/recall-experiments-week-one/)

**MCP memory servers comparisons**
- [NO HANDS-ON] The comparison found covers Hjarni, Mem0/OpenMemory, Supermemory, Zep/Graphiti, Letta, Basic Memory and the MCP reference KG server. It is explicitly "not... a hands-on benchmark", and the author founded Hjarni, which ranks first. — [Hjarni](https://hjarni.com/blog/best-mcp-memory-server)

**Access partitions (enterprise)**
- [PRACTITIONER GUIDANCE] Wavect (Kevin Riedl, Jun 2026):
  - Enforce ACLs in the retrieval service as a mandatory pre-filter ("early binding"). Post-filtering is acceptable only if it keeps fetching until it has k authorised results, and rejected content never reaches context or logs.
  - Ingest-time ACLs create a revocation window. Combine change feeds with reconciliation and fail closed past a freshness threshold.
  - Entra group-claim overage happens at 200 (JWT) or 150 (SAML) groups.
  - Confluence ancestor restrictions and Drive limited-access folders are common traps.
  - Postgres RLS is bypassable by owners and superusers unless FORCE is set. — [Wavect](https://wavect.io/blog/rag-permissions-sharepoint-confluence-drive/)

### Inferences
- Fast-changing facts are best handled by **structured supersession at write or mutation time**: validity intervals, superseded-by links, evidence versions. Recency decay in ranking alone doesn't do it. MemStrata, FORGETEVAL, OpenWiki and Supermemory all point the same way. The closest recall numbers are on templated or code facts, so natural-language extraction quality (about 44% in MemStrata's messy set) is the open risk.
- Return **atomic fact plus source chunk** together (Supermemory). This combines precision for top-k with evidence for grounding, and it fits a "required items in top-k" metric.
- Consolidation agents should *flag* rather than delete (OpenWiki, Mejba). They should also be version-controlled (Letta git, Mejba git), scope-aware (Mem0 failure), and triggered by thresholds plus idle time (Honcho, Claude Code /dream).
- KG value appears to come from *entity resolution* (canonical IDs) and *derived summaries*, not graph traversal at query time. Graph edges for recall regressed in the one independent ablation.
- **Test for us:**
  - (a) Supersession ledger versus recency-decay ranking versus none, on a seeded "changing facts" slice. Metrics: stale@1 and all-items-in-top-k.
  - (b) Observer/reflector always-loaded memory versus retrieval, on personal-assistant conversational tasks.
  - (c) Entity pages with claims and evidence as an extra retrievable document type. Measure whether multi-hop all-items-in-top-k rises.
  - (d) Partition leakage tests with revoked-ACL scenarios.

### Gaps
- No measured, in-the-wild results for sleep-time or dream consolidation on recall quality (Letta, Honcho and Claude Code publish none).
- No independent replication of Supermemory, Mastra, Mem0 or Zep LongMemEval numbers under one neutral harness.
- No hands-on comparison of MCP memory servers.
- Time-decay ranking: found only vendor explainers (e.g. Mem0 blog) and an Ebbinghaus-curve DEV post, with no measured comparison against supersession. Not cited for that reason.
