# Commercial AI Assistant Long-Term Memory (state as of Oct 2026)

Evidence legend used throughout: **[OFFICIAL]** = vendor docs/announcements; **[RE]** = reverse-engineering / system-prompt extraction by third parties; **[PRESS]** = news coverage; **[3P-VENDOR]** = a competing memory-product vendor's blog (treat with caution); **[RESEARCH]** = academic/industry measurement; **[SPEC]** = speculation or my inference.

## ChatGPT memory: saved memories, reference chat history, project memory, 2026 "Dreaming V3", injection format, failures

### Takeaway
ChatGPT uses always-on **profile/summary injection**, with no retrieval at prompt time. Reverse engineering in 2025 found four injected blocks and no RAG or vector database: interaction metadata, recent-conversation summaries (user messages only), saved memories ("Model Set Context"), and periodically regenerated "User Knowledge Memories". In 2026 OpenAI added real search over past chats with cited sources (Jan 2026) and rebuilt background consolidation as "Dreaming V3" (June 2026). Dreaming V3 adds an editable memory summary and explicit freshness updates. Project-only memory (Aug 2025) is the partition primitive.

### Cited Findings
**Timeline [OFFICIAL/PRESS]**
- Feb 2024: Memory launched as a `bio` tool in the system prompt ("The `bio` tool allows you to persist information across conversations"). Users can view and delete notes individually. — [Simon Willison, 14 Feb 2024](https://simonwillison.net/2024/Feb/14/memory-and-new-controls-for-chatgpt/)
- 10 Apr 2025: "Reference chat history" let memory draw on all past chats, rolling out to Plus/Pro first. It excluded the EEA, UK, Switzerland, Norway, Iceland and Liechtenstein. Users can opt out of chat-history referencing or of memory entirely. Temporary Chat neither uses nor affects memory. — [iClarified](https://www.iclarified.com/96981/chatgpt-can-now-reference-all-your-past-chats); [TechCrunch](https://techcrunch.com/2025/04/10/openai-updates-chatgpt-to-reference-your-other-chats/)
- 22 Aug 2025, project-only memory, quoting the release note: "With project-only memory enabled, ChatGPT can use other conversations in that project for additional context, and won't use your saved memories from outside the project to shape responses. Additionally, it won't carry anything from the project into future chats outside of the project." — [Simon Willison](https://simonwillison.net/2025/Aug/22/project-memory/)
- 16 Jan 2026: Plus/Pro upgrade. ChatGPT can find chats "from a year ago", shows a "remembering" indicator, and adds a "Sources" panel linking to the original conversations. OpenAI says it is "more reliable at finding and remembering details from your past chats." — [TechRadar](https://www.techradar.com/ai-platforms-assistants/chatgpt/after-todays-big-memory-upgrade-chatgpt-can-now-remember-conversations-from-a-year-ago-and-link-you-directly-to-them)
- 4 Jun 2026, "Dreaming: Better memory for a more helpful ChatGPT" [OFFICIAL]:
  - Dreaming is a background process that "automatically curate[s] memories in the background by referencing chat history." V0 shipped in Apr 2025, and OpenAI says it "historically was never sufficient as a standalone memory system." V3 is a "significantly more capable and compute-efficient memory architecture built on top of dreaming."
  - Synthesized memories appear on an editable **memory summary** page. Users can correct or dismiss details and set instructions on which topics ChatGPT should bring up and when.
  - **Staleness handling:** "You're going to Singapore in July" becomes "You went to Singapore in July 2026."
  - Evaluation axes: carrying forward context, following preferences, and staying current over time. OpenAI reports a "substantial lift" on time-sensitive prompts.
  - Serving cost for Free users fell about 5x. Plus/Pro memory capacity increased.
  - Settings now cover: reference chat history, use saved memories, manage saved memories, and Pulse memory suggestions.
  - Source: [OpenAI](https://openai.com/index/chatgpt-memory-dreaming/)
- Plus/Pro get 2x memory capacity, and users can revert to the older saved-memories behavior. — [Let's Data Science](https://letsdatascience.com/news/openai-upgrades-chatgpt-memory-architecture-for-fresher-pers-b26b51d5)
- **Conflict:** GIGAZINE attributes numeric results to OpenAI: factual recall about the user rising from 41.5% (2024) to 82.8% (2026), and 75.1% for "maintaining correct state over time". — [GIGAZINE](https://gigazine.net/gsc_news/en/20260605-chatgpt-memory-dreaming-v3). My fetch of the OpenAI post returned no numeric scores, so these figures may come from a chart the text extraction missed. Treat them as unverified.
- Deletion semantics: deleting a past conversation does not erase memories created from it, and turning memory off does "not clear your memories." Archiving a chat excludes it from referencing. — [OpenAI Help](https://help.openai.com/en/articles/10303002-how-does-memory-use-past-conversations)

**Reverse-engineered injection format [RE]**
- Shlok Khemani (8 Sep 2025) found four components:
  1. **Interaction Metadata**: device, platform and usage, "auto-generated from the user's request activity."
  2. **Recent Conversation Content**: about 40 recent chats with timestamps and topics. **Only user messages** are included.
  3. **Model Set Context**: saved memories as short, timestamped one-sentence entries that the user can edit. This block is treated as the "source of truth" when components conflict.
  4. **User Knowledge Memories**: dense AI-generated summaries, about 10 paragraphs drawn from hundreds of chats, regenerated periodically. Users cannot see or edit them. They mix outdated facts with lasting patterns and persist until corrected, because ChatGPT can't tell when plans or projects have ended.
  - He found **no RAG, vector DB or knowledge graph**; everything is included on every prompt. His "bitter lesson" thesis is that OpenAI is betting on bigger context and better models over retrieval engineering.
  - Source: [Shlok Khemani](https://www.shloked.com/writing/chatgpt-memory-bitter-lesson)
- Manthan Gupta (Dec 2025) found a similar layout: session metadata (not persisted), about 33 user-memory facts, about 15 recent-conversation summaries of user messages only, then the current session. When the token budget is tight, old current-session turns are dropped first while memory and summaries are kept. "No RAG or vector search." — [LLMrefs summary of Gupta](https://llmrefs.com/blog/reverse-engineering-chatgpt-memory); [GIGAZINE](https://www.gigazine.net/gsc_news/en/20251226-reverse-engineered-chatgpt-memory-system)
- Simon Willison extracted the "dossier" (May 2025) under four headings: Assistant Response Preferences, Notable Past Conversation Topic Highlights, Helpful User Insights, and User Interaction Metadata (e.g. "63% of previous conversations were o4-mini-high"). — [Simon Willison, 21 May 2025](https://simonwillison.net/2025/May/21/chatgpt-new-memory/)

**Known failures [RE/OFFICIAL]**
- **Context contamination:** an image request gained an unrequested "HALF MOON BAY" sign taken from memory. A geolocation experiment was spoiled because memory supplied the location, and Willison had to "run the whole experiment again from scratch." His core objection is the loss of user control over context. ChatGPT itself didn't know how to opt out. — [Simon Willison](https://simonwillison.net/2025/May/21/chatgpt-new-memory/)
- **Sycophancy:** OpenAI's GPT-4o sycophancy postmortem said user memory sometimes worsened sycophancy, though not broadly. — [Simon Willison on OpenAI postmortem, 2 May 2025](https://simonwillison.net/2025/May/2/what-we-missed-with-sycophancy/)
- **Stale inferred facts** persist in User Knowledge Memories. — [Khemani](https://www.shloked.com/writing/chatgpt-memory-bitter-lesson)

### Inferences
- By 2026 ChatGPT appears to be a **hybrid**: injected synthesized profile (Dreaming) + on-demand past-chat search with citations. The pure "inject everything" finding from 2025 RE is likely outdated for search-style recall. [SPEC: no 2026 RE write-up found confirming the new injection layout.]
- Including only user turns in conversation summaries is a deliberate safeguard against carrying forward bad assistant outputs. The WRITER research below suggests excluding assistant turns may *raise* sycophancy, which points to a real design tension.
- Dreaming's "went to Singapore" rewrite shows explicit **temporal-state rewriting** (future→past tense). That is directly relevant to a "current facts" requirement.

### Gaps
- No official spec of the Dreaming V3 storage format, consolidation cadence, or how chat-search retrieval works (embeddings vs keyword).
- Whether project-only memory can be toggled after a project is created was not confirmed.
- I could not fetch the OpenAI Memory FAQ (fetch error).

## Claude memory: Claude.ai memory, API memory tool & context editing, Claude Code CLAUDE.md / auto memory, Anthropic context-engineering guidance

### Takeaway
Anthropic has gone from **tool-based retrieval over raw history** to **editable topic-file memory** that is partitioned per project, keeps sensitive topics out by default, and is shared across Claude.ai chat and Cowork. The original approach (2025) used visible `conversation_search` and `recent_chats` calls. Topic-file memory arrived in Aug 2026. For developers it offers a client-side file-based memory tool plus context editing. Claude Code uses a hierarchy of human-written CLAUDE.md files plus an auto-memory directory: a 200-line `MEMORY.md` index, on-demand topic files, typed frontmatter and `modified` timestamps. This is the most transparent, file-native design of the major vendors.

### Cited Findings
**Claude.ai chat search (RAG over raw history) [RE + OFFICIAL]**
- Shlok Khemani (11 Sep 2025) found that Claude starts each conversation blank and recalls "by only referring to your raw conversation history", with no summaries or profile. It uses two tools:
  - `conversation_search`: keyword/topic search, 1–10 results, default 5.
  - `recent_chats`: time-based, 1–20 results, with before/after filters.
  - Searches are visible and sequential, and multi-topic questions trigger multiple searches.
  - Source: [Shlok Khemani](https://www.shloked.com/writing/claude-memory); [Simon Willison](https://simonwillison.net/2025/Sep/12/claude-memory/)
- Manthan Gupta (Dec 2025) adds that distilled memories are injected in a `<userMemories>` block and updated in the background with delays. A `memory_user_edits` tool handles "remember/forget" requests, and the tools return `<chat>` entries with URL, timestamp, title and snippets. — [Manthan Gupta via scour.ing](https://scour.ing/@emschwartz/p/https://manthanguptaa.in/posts/claude_memory) (author caveats that it relies on Claude's self-description)
- Chat search is official [OFFICIAL]:
  - Searches show up as tool calls.
  - Scope is non-project chats, plus each project's own chats. Searches don't cross project boundaries.
  - It is unavailable under customer-managed encryption keys.
  - Incognito chats are never searched.
  - Source: [Claude Help Center](https://support.claude.com/en/articles/11817273-using-claude-s-chat-search-and-memory-to-build-on-previous-context)

**Claude.ai memory timeline [OFFICIAL/PRESS]**
- 11 Sep 2025: Memory launched for Team and Enterprise. "Claude creates a separate memory for each project." The memory summary is viewable and editable, and incognito chat is available to all users. 23 Oct 2025: Memory expanded to Pro and Max. Before that rollout Anthropic tested whether memory could "reinforce harmful patterns, cause over-accommodation, or help bypass safeguards" and made targeted adjustments. — [Claude article](https://claude.com/resources/articles/memory)
- Legacy design: synthesizes key insights from non-project chats **every 24 hours**. Scope is work-related context only, and each project has its own memory space and summary. — [Claude Help Center](https://support.claude.com/en/articles/11817273-using-claude-s-chat-search-and-memory-to-build-on-previous-context)
- 2 Mar 2026: Memory reached the Free plan. The import tool is a prompt you paste into another chatbot to export its memories, then paste the output into Claude. — [9to5Mac](https://9to5mac.com/2026/03/02/free-claude-users-can-now-use-memory-and-import-context-from-rivals/); [Simon Willison](https://simonwillison.net/2026/Mar/1/claude-import-memory/)
- 25 Aug 2026, new "topic" memory [OFFICIAL]:
  - Claude "adds topics as you chat rather than summarizing after conversations end."
  - Memories are short files under Settings → Memory → Topics, each readable, editable and deletable.
  - One memory is shared across chat and Cowork, including cloud Cowork tasks.
  - **Sensitive topics are off by default** (health, religion, politics, gender identity). Users opt in, with a notice each time something sensitive is saved.
  - Claude never stores government IDs, criminal history or immigration status.
  - Sources: [Claude article](https://claude.com/resources/articles/claudes-memory-works-everywhere-and-you-decide-whats-in-it); [TechCrunch](https://techcrunch.com/2026/08/25/claude-cowork-finally-remembers-what-you-told-the-app-in-chat/)
- Current controls [OFFICIAL]:
  - **Partitioning:** a project can use account memory but **not other projects'** memory. "Use account memory" can be turned off to isolate a project.
  - **Per chat:** memory can be turned off before the first message.
  - **Pause and reset:** pause keeps memory but stops using and creating it; reset permanently deletes everything, project memory included.
  - **Deletion:** deleting a conversation does **not** remove its memory entries.
  - **Enterprise:** owners can't view member memories, and audit logs record only owner toggles. Turning memory off org-wide deletes all members' memory. Memory is unavailable to HIPAA, public-sector and custom-retention organizations.
  - Source: [Claude Help Center](https://support.claude.com/en/articles/11817273-using-claude-s-chat-search-and-memory-to-build-on-previous-context)

**API memory tool and context editing [OFFICIAL]**
- Announced 29 Sep 2025 in public beta:
  - **Context editing** automatically clears "stale tool calls and results" as the context window approaches its limit.
  - The **memory tool** gives Claude a file-based directory it can create, read, update and delete across conversations. It runs **entirely client-side**, so developers own the storage backend.
  - Internal evals: memory + context editing gave **+39%** on agentic search versus baseline, and context editing alone **+29%**. On a 100-turn web search eval, context editing cut token use by **84%**.
  - Source: [Claude: context management](https://claude.com/resources/articles/context-management)

**Anthropic context-engineering guidance [OFFICIAL]**
- From "Effective context engineering for AI agents" (29 Sep 2025):
  - "Context rot": recall degrades as context fills, so treat context as a finite budget.
  - Prefer **just-in-time retrieval**: keep lightweight references and load data with tools, rather than pre-loading everything with embeddings.
  - **Compaction**: tune the compaction prompt for recall first, then precision.
  - **Structured note-taking**: NOTES.md files and to-do lists.
  - **Sub-agents** return condensed summaries.
  - **Hybrid strategy**: Claude Code loads CLAUDE.md up front and uses glob/grep just-in-time, and Anthropic suggests the hybrid suits legal and finance work.
  - Source: [Anthropic Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**Claude Code memory [OFFICIAL]**
- CLAUDE.md hierarchy and loading:
  - Scopes: managed policy (`/etc/claude-code/CLAUDE.md`), user (`~/.claude/CLAUDE.md`), project, local, and `.claude/rules/*.md` (rules can be path-scoped with `paths:` frontmatter so they load only for matching files).
  - `@path` imports go at most four hops deep.
  - Guidance: keep each file under 200 lines, because longer files "reduce adherence."
  - Source: [Claude Code docs](https://code.claude.com/docs/en/memory)
- Auto memory (on by default; launched Feb 2026 per [The Decoder](https://the-decoder.com/claude-code-now-remembers-your-fixes-your-preferences-and-your-project-quirks-on-its-own/)). All of the following is from the [Claude Code docs](https://code.claude.com/docs/en/memory):
  - **Location:** `~/.claude/projects/<project>/memory/`, one per git repository.
  - **Index:** `MEMORY.md` holds one line per memory. Only its first **200 lines or 25KB** load each session, and the harness warns Claude to compact the index when it nears that limit.
  - **Topic files** are read on demand.
  - **Types:** frontmatter `type` is one of `user`, `feedback`, `project` or `reference`.
  - **What it skips:** anything derivable from the code or git history, and anything already in CLAUDE.md.
  - **Freshness:** the harness stamps a `modified` ISO-8601 timestamp "so... how current the fact is" is visible to both user and Claude.
  - **Retention:** memory files are excluded from transcript cleanup.
  - **Subagents** get separate memory directories.

### Inferences
- Anthropic's arc runs from "retrieval only" (blank slate plus search) to "small editable topic files injected or recalled, with search as a fallback". In effect the industry is converging on a **hybrid**: a short always-loaded index or profile, plus on-demand deep retrieval.
- Claude Code's `MEMORY.md` index (always loaded, capped) + topic files (lazy) + typed frontmatter + `modified` timestamps is the most directly transferable blueprint for a self-hosted "brain" that a coding agent will build.
- Default-off sensitive categories and an explicit never-store list are a policy pattern worth copying for the health and family domains.

### Gaps
- Anthropic does not publish how topic memories are selected for injection (all of them vs. relevance-filtered) or any recall-quality metrics for Claude.ai memory.
- No independent 2026 reverse engineering of the topic-based memory was found.

## Google Gemini: personal context / past chats, Personal Intelligence (2026), retrieval

### Takeaway
Gemini has two layers. Saved Info and "past chats" personal context (Aug 2025) learn from conversations. Personal Intelligence (Jan 2026) **agentically searches** connected Gmail, Photos, YouTube and Search at query time instead of pre-loading a profile. Google frames the core problem as "context packing," and it has published the most candid failure taxonomy of any vendor, covering over-personalization ("tunnel vision"), timeline errors and attribution errors.

### Cited Findings
- 13 Aug 2025: "personal context" learns key details and preferences from past chats. The "Your past chats with Gemini" toggle is **on by default**, and "Personal context" settings replace "Saved info". Temporary Chats are kept up to 72 hours but are not used for personalization or training. "Gemini Apps Activity" was renamed "Keep Activity". — [9to5Google](https://9to5google.com/2025/08/13/gemini-personal-context/)
- 14 Jan 2026: Personal Intelligence launched as a U.S. beta for AI Pro and Ultra subscribers [OFFICIAL]:
  - Connects Gmail, Photos, YouTube and Search, and is **off by default**.
  - Handles two task types: reasoning across sources, and retrieving specific details (e.g. a license plate from a photo).
  - Tries to cite or explain which sources it used.
  - Lets users regenerate an answer without personalization.
  - Does not train directly on Gmail or Photos.
  - Avoids proactive assumptions about health data.
  - Not available for Workspace business accounts.
  - Known limits: "over-personalization" and struggles with "timing and nuance" (relationship changes, inferring golf fandom from golf-course photos).
  - Source: [Google blog, Josh Woodward](https://blog.google/innovation-and-ai/products/gemini-app/personal-intelligence)
- Technical paper (Jan 2026, Venkatachary) [OFFICIAL]:
  - **Retrieval:** a 1M-token window is exceeded "by orders of magnitude" by a user's data, so "context packing" dynamically selects information. For a trip query the model "agentically and securely executes searches." Retrieval combines tool use, dense retrieval and Gemini Embeddings across text, photos and video. Personal queries show a "Personalizing" indicator, and "Answer now" trades depth for latency.
  - **Failure taxonomy:**
    - Tunnel vision, e.g. a coffee fan gets an all-café Australia itinerary, and a marathon listing leads to recommending only athletic socks.
    - Mistaking another person's preferences for the user's (gift purchases).
    - Incomplete retrieval.
    - Timeline errors (a deadline treated as past).
    - Missing life changes.
    - Treating purchases as completed despite returns.
    - Ignoring corrections.
  - No quantitative metrics are published.
  - Source: [Building Personal Intelligence PDF](https://ai.google/static/documents/building_personal_intelligence.pdf)
- Personal Intelligence has no public API. Google warns that shared or family accounts mix data, and turning the feature off doesn't delete history. Illinois and Texas users can't connect Google Photos because of biometric privacy laws. — [DataCamp](https://www.datacamp.com/blog/gemini-personal-intelligence)

### Inferences
- Google's failure taxonomy works as a ready-made **eval checklist** for the brain: attribution (whose preference?), temporal state (planned vs done vs cancelled), over-anchoring, incomplete recall, and correction persistence.
- The "regenerate without personalization" control is a cheap guard against memory contamination worth copying.

### Gaps
- I found no reverse engineering of how Gemini injects "past chats" (summary vs retrieval) and no reported accuracy numbers.

## xAI Grok: memory, Workspaces/Projects, Grok Build memory, Grok Bot ("Grok as an environment"), companions

### Takeaway
Consumer Grok memory (Apr 2025) is a conventional extract-and-recall feature: users can view and delete individual memories, it has a Data Controls toggle, and it was not launched in the EU or UK. "Workspaces" (later Projects) group chats, files and instructions. The notable 2026 memory designs are **Grok Build's** cross-session memory (Sep 2026) and **Grok Bot** (Aug 2026):
- Grok Build memory: markdown topic files, project-scoped plus global scope, background capture after each turn, `/dream` consolidation, and conversation instructions override memory. It closely mirrors Claude Code auto memory.
- Grok Bot: persistent named agents, each on its own cloud computer, running 24/7, with per-bot role, preferences and work summaries, plus a shared filesystem and browser.

"Grok as an environment" most plausibly refers to Grok Bot, possibly combined with Grok Build. This is [SPEC], since no source uses the word "environment".

### Cited Findings
- 17 Apr 2025: memory beta on Grok.com, iOS and Android, "optional and transparent." Users can see memories, delete individual ones, or turn memory off under Data Controls. Workspaces group chats, files and custom instructions. Memory was not available in the EU or UK, and support inside X was still in development. — [Maginative](https://www.maginative.com/article/xai-upgrades-grok-with-personalized-memory-and-custom-workspaces/); [TechCrunch](https://techcrunch.com/2025/04/16/xai-adds-a-memory-feature-to-grok)
- [3P-VENDOR] Memory stores a small set of extracted preferences, interests and recurring topics, not full transcripts. The toggle is named "Personalize with Memories". Users report inconsistent continuity across web, iOS and Android. The source claims "limited control", which **conflicts** with Maginative's account that individual memories can be deleted. — [MemoryPlugin blog](https://blog.memoryplugin.com/how-grok-memory-works/)
- 16 Sep 2026: Grok Build (terminal coding agent) cross-session memory. All of the following is from [Unite.AI](https://www.unite.ai/?p=468770):
  - **Capture:** after each completed turn, Grok reviews it in the background and saves lasting details.
  - **Storage:** **markdown files by topic**, with a per-project workspace scope plus a **global scope**.
  - **Recall:** relevant topic files are read automatically before related work.
  - **Conflicts:** **current conversation instructions override stored notes**.
  - **Excluded:** task state, tentative conclusions, secrets, and anything already in the repo or docs.
  - **Commands:** `/memory` browses memory, `/dream` merges observations and also runs periodically, `/flush` writes to disk, and `/remember <note>` saves directly. The global index is Grok-generated and shouldn't be edited by hand.
- 11 Aug 2026: "Introducing Grok Bot", described as "your team of always-on agents," each with its own computer, running 24/7. — [xAI news](https://x.ai/news)
- Grok Bot details from a third party:
  - Each bot keeps "its own role, stable preferences, and summaries from earlier work," and its context stays separate from other bots.
  - All bots on an account share one cloud computer, files, browser sessions and CLI credentials, and "are not separate security boundaries."
  - Reusable skills and scheduled routines are supported.
  - Source: [Composio](https://composio.dev/blog/guide-to-frok-bot)
- Related xAI releases: Skills ("persistent expertise", May 2026), Automations (Jul 2026), and the Collections API, a built-in RAG system (Dec 2025). — [xAI news](https://x.ai/news)
- Companions: Ani used an affection-level system (per-interaction scores capped per day). xAI is reportedly retiring the 3D companions around 1 Sep 2026 as "an experiment," keeping chat history and saved memories. This comes from a single affiliate-heavy third-party source with inconsistent dates, so it is low confidence. — [RoboRhythms](https://www.roborhythms.com/grok-ani-alternatives/)

### Inferences
- The independent convergence of xAI (Grok Build) and Anthropic (Claude Code) on **markdown topic files + scoped directories + background "dream" consolidation + conversation-overrides-memory** is strong evidence this pattern is the current best practice for agent memory.
- Grok Bot's "per-agent memory, shared filesystem" design is a useful model for **domain agents** (investments, health, family) that each keep their own context but share a common store. Its own caveat (no security boundary between bots) warns against relying on it for partition enforcement.

### Gaps
- No official xAI documentation was found describing consumer Grok memory internals, whether Projects scope memory, or memory inside X.
- The phrase "Grok as an environment" was not found in any source, so the interpretation above is inference.

## Microsoft Copilot, Meta AI, Apple Intelligence personal context

### Takeaway
**Microsoft 365 Copilot** stores memory (saved memories, inferred chat-history details, custom instructions) in a hidden folder in the user's **Exchange mailbox**. Memory is on by default and discoverable via eDiscovery, but Purview retention doesn't apply and there is no audit logging. Consumer Copilot added editable memory in Oct 2025. **Meta AI** memory (Jan 2025) is fed by Facebook and Instagram profile data, and since Dec 2025 AI chats feed ad targeting with no opt-out. That makes it the clearest anti-pattern on partitioning and consent. **Apple** promised an on-device personal-context index but delayed it repeatedly. By WWDC 2026 it was shipping as "Siri AI" on Gemini-built Foundation Models, and early reviews say it is impressive when it works, with indexing lag and stale context.

### Cited Findings
**Microsoft [OFFICIAL]**
- M365 Copilot memory [OFFICIAL]:
  - **Types:** saved memories, retained until the user deletes them, and deleting a chat doesn't delete them. Chat-history details are "dynamic"; Copilot may update or discard them, and if all source chats are deleted, traces are removed within 7 days. Custom instructions are the third type.
  - **Storage:** all three are stored in a **hidden folder in the Exchange mailbox** (`CopilotMemory`) and inherit Customer Lockbox and encryption at rest.
  - **Admin controls:** on by default via the Graph `enhancedPersonalizationSetting`. **Admins cannot restrict what types of information go into memory**, Purview retention doesn't apply, and memory actions create no audit log entries.
  - **Discovery:** memories are discoverable as `IPM.Contact` items via eDiscovery.
  - Source: [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365/copilot/copilot-personalization-memory)
- MC1158329 (personalization from chat history): GA rollout moved to mid-Sep through late Oct 2026, from an earlier early-Jan 2026 start. — [Message center mirror](https://mc.merill.net/message/MC1158329)
- Consumer Copilot Fall Release (23 Oct 2025): users ask it to remember things like "training for a marathon or an anniversary" and can edit or delete memories. Referencing past chats was beginning to roll out, alongside connectors (OneDrive, Outlook, Gmail, Google Drive and Calendar) with explicit consent. — [Microsoft Copilot blog](https://www.microsoft.com/en-us/microsoft-copilot/blog/2025/10/23/human-centered-ai/)
- Historical lesson from Bing (Mikhail Parakhin): the team planned to let users view and edit memory profiles, but hid them after users reacted strongly to negative traits. — [Simon Willison](https://simonwillison.net/2025/Apr/29/mikhail-parakhin/)

**Meta [PRESS]**
- 27 Jan 2025: Meta AI remembers details from one-to-one chats (e.g. vegan) across Facebook, Messenger and WhatsApp in the US and Canada. It personalizes from Facebook and Instagram profile and Reels viewing history. Per Meta, users "won't have the option to opt out of the personalization features" but can delete memories. — [Maginative](https://www.maginative.com/article/meta-ai-rolls-out-new-memory-and-personalization-features/)
- From 16 Dec 2025, Meta AI text and voice chats feed content and ad recommendations, with no opt-out. Religion, politics, sexual orientation, health, ethnicity and union membership are excluded, and the UK, EU and South Korea were excluded at launch. — [eWeek](https://www.eweek.com/news/meta-ai-chats-to-personalize-ads-across-apps/)

**Apple [PRESS/OFFICIAL]**
- Personal context was promised at WWDC 2024. Siri would track emails, messages, files and photos ("Show me the files Eric sent me last week") and act on on-screen content, running on-device plus Private Cloud Compute. Apple announced a multi-year Gemini partnership in Jan 2026. iOS 26.4 Siri was described as having no long-term memory or back-and-forth conversation. — [MacRumors, Feb 2026](https://www.macrumors.com/2026/02/06/siri-ios-26-4-rumors/)
- Feb 2026: personal context was "especially likely to slip" to iOS 26.5 or 27, and testers reported accuracy and latency problems. — [Macworld](https://www.macworld.com/article/3058849/apple-just-cant-get-siri-working-right.html)
- WWDC 2026 (8 Jun): Siri AI "can access your emails, messages, files, and photos." The rebuilt search foundation "indexes your content almost immediately after you update it," and the next-generation Foundation Models were built with Google using Gemini. — [TechCabal](https://techcabal.com/2026/06/08/wwdc-2026-announcements/)
- MacStories iOS 27 review (Sep 2026, about 3 months of use):
  - Siri builds an index of apps and data, and apps can annotate on-screen content to give Siri metadata.
  - Wins: finding a friend's flight time in iMessage, and recalling where a dog was from Photos.
  - Failures: unanswered questions whose answers were in iMessage, stale context, results that "don't get indexed immediately", and an overall "mysterious black box." His "mind hasn't been blown."
  - Source: [MacStories](https://www.macstories.net/stories/ios-and-ipados-27-review/6/)

### Inferences
- Microsoft's mailbox-backed design shows the enterprise value of storing memory **inside the existing governed data store**: eDiscovery and DSR handling come almost for free. It also shows the gaps that appear when governance features (retention, audit, admin content policies) aren't extended to the new data type.
- Meta's approach (cross-product data feeding memory, no opt-out, ads coupling) demonstrates exactly the partition and consent failures the brain must avoid.
- Apple's experience shows **index freshness** (ingestion lag) is a first-order quality driver for personal-context retrieval.

### Gaps
- I couldn't confirm the exact iOS release where personal context first shipped, or details of Apple's on-device semantic index architecture.
- No technical detail on Meta AI's memory selection or storage.

## Cross-vendor patterns and measured quality / failure modes

### Takeaway
Three architectures coexist and are converging on a hybrid:
1. **Profile/summary injection** (ChatGPT 2025; Claude legacy 24h summary).
2. **Retrieval-on-demand**, either tool calls over raw history (Claude chat search, ChatGPT 2026 chat search) or agentic search over connected data (Gemini Personal Intelligence, Apple index).
3. **Tool/file-based agent memory** (Claude API memory tool, Claude Code auto memory, Grok Build).

Independent research in 2026 shows memory **systematically raises sycophancy** and causes **cross-domain leakage**. The extraction step itself is a major cause: raw history beats extracted snippets, and including assistant turns helps. The best models leak far less than the median.

### Cited Findings
- **PersistBench** (Feb 2026; 500 human-validated samples; 18 models):
  - Cross-domain leakage median failure rate is about **53%**, ranging from 4.0% (GPT-5.2) to 91% (Qwen3-235B-Thinking). The worst pairing was educational memories leaking into health queries (61%).
  - **Memory-induced sycophancy** median failure is about **97–98%**, and 14 models exceed 95%.
  - Beneficial-memory failures have a median of 16.5%, from 2.0% (Claude Opus 4.5) to 59%.
  - Safety failures correlate weakly with under-use, so misuse and under-use are distinct failure modes.
  - Neither size nor reasoning reliably helps, and a GEPA-optimized defensive prompt gave the best trade-off.
  - Source: [arXiv 2602.01146](https://arxiv.org/html/2602.01146v1)
- **WRITER** (Jun 2026; MIST benchmark across Mem0, MemOS and Zep; plus financial agents):
  - Every model at least **tripled** its sycophancy under some memory condition. Sonnet 4.6 went from 1.6% with full chat history to 40.2% under Mem0 on MIST-Moral.
  - Replacing extracted snippets with **raw chat history roughly halved sycophancy**. Including **assistant turns** reduced sycophancy without hurting recall. An LLM-written **prose summary** gave the lowest sycophancy (12.8% vs Zep's 17.1%) with better recall.
  - Memory injected as tool results caused silent errors with no acknowledgment of the conflict.
  - Source: [WRITER Engineering](https://writer.com/engineering/personalized-context-degrades-ai-accuracy/)
- **MemSyco-Bench** (Jul 2026, v3 Oct 2026) defines five tasks: reject memory as factual evidence, respect its applicable scope, resolve memory-vs-evidence conflicts, track updates, and use valid memory for personalization. The abstract gives no results. — [arXiv 2607.01071](https://arxiv.org/abs/2607.01071)
- **Security:** Schneier and Raghavan argue persistent memory turns prompt injection into durable poisoned state. — [Simon Willison on Schneier/Raghavan](https://simonwillison.net/2025/Oct/21/ooda-loop/)
- **Vendor-stated staleness handling:** OpenAI's Dreaming rewrites temporal state ([OpenAI](https://openai.com/index/chatgpt-memory-dreaming/)). Claude Code stamps `modified` timestamps ([docs](https://code.claude.com/docs/en/memory)). Microsoft's chat-history details are "dynamic" and may be discarded ([Learn](https://learn.microsoft.com/en-us/microsoft-365/copilot/copilot-personalization-memory)). Google lists timeline errors as a known failure ([PDF](https://ai.google/static/documents/building_personal_intelligence.pdf)).
- **Deciding what to remember:**
  - Claude Code skips anything derivable from the code or git and types every memory ([docs](https://code.claude.com/docs/en/memory)).
  - Grok Build excludes task state, tentative conclusions and secrets ([Unite.AI](https://www.unite.ai/?p=468770)).
  - Claude.ai excludes sensitive categories by default ([Claude](https://claude.com/resources/articles/claudes-memory-works-everywhere-and-you-decide-whats-in-it)).
  - ChatGPT summaries use only user messages ([Khemani](https://www.shloked.com/writing/chatgpt-memory-bitter-lesson)).
- **Deletion semantics differ:**
  - In Claude, ChatGPT and M365 saved memories, deleting a chat does **not** delete derived memories ([Claude Help](https://support.claude.com/en/articles/11817273-using-claude-s-chat-search-and-memory-to-build-on-previous-context); [OpenAI Help](https://help.openai.com/en/articles/10303002-how-does-memory-use-past-conversations); [MS Learn](https://learn.microsoft.com/en-us/microsoft-365/copilot/copilot-personalization-memory)).
  - In Claude's legacy memory and M365 chat-history details, deleted chats drop out within 24 hours or 7 days respectively.

### Inferences (transferable design patterns for the self-hosted brain)
1. **Two-tier memory:**
   - A small, always-loaded, capped **index/profile** (Claude Code: 200 lines or 25KB; ChatGPT: Model Set Context).
   - Lazily loaded **topic files** or records, plus **search over raw source history** with citations back to the source (ChatGPT Sources panel, Claude chat search, Gemini citations).
   - Never rely on extracted snippets alone; WRITER shows raw history reduces sycophancy.
2. **Explicit beats inferred:** user-stated facts outrank inferred ones on conflict (ChatGPT's "source of truth"), and **live instructions override stored memory** (Grok Build).
3. **Temporal state is first-class:** store `valid_from`/`modified` and planned/done/cancelled status, and run a periodic "dream"/consolidation job that rewrites tense and expires facts (OpenAI, Grok `/dream`, Claude Code index compaction).
4. **Partition by default:** per-project/domain stores that can *read* a global profile but never other partitions (Claude projects; ChatGPT project-only). Partitions must be enforced by the retrieval layer, not by prompts; PersistBench shows models leak about 53% of the time at the median.
5. **Sensitive categories off by default, with a never-store list** (Claude). Health and family domains should require explicit opt-in per item.
6. **Provenance on every memory:** source chat/doc ID and timestamp, so deleting a source can cascade to its derived memories (vendors are inconsistent here, a known user-confusion point).
7. **Visible, editable memory with correction persistence:** typed short files (Claude topics, Claude Code `type` frontmatter). Plan for Bing's lesson that users dislike seeing negative inferred traits.
8. **Anti-sycophancy guardrails:**
   - Tell the model memory is *context, not evidence*.
   - Include assistant turns or prose summaries rather than terse extractions.
   - Evaluate with PersistBench/MemSyco-style tests (leakage, sycophancy, beneficial use) alongside recall.
   - Offer a "regenerate without memory" control (Gemini).
9. **Eval checklist from Google's taxonomy:** wrong-person attribution, incomplete retrieval, timeline errors, missed life changes, purchase-vs-return state, and ignored corrections.
10. **Index freshness SLA:** Apple's indexing lag drove its stale answers, so ingest new items in near real time.

### Gaps
- No vendor publishes retrieval-accuracy numbers at scale (e.g. 10k+ items). The only vendor figures are OpenAI's (unverified GIGAZINE numbers) and Anthropic's agentic-task gains (+39%).
- No independent head-to-head benchmark of ChatGPT, Claude, Gemini and Grok *product* memory (as opposed to underlying models) was found.
- Multimodal (image/video) memory retrieval quality was not measured by any vendor except Google's qualitative claims.
