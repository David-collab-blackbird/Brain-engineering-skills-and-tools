# Security Frontier for a Multi-Tenant AI Memory "Brain" (as of 23 Oct 2026)

Evidence labels used throughout:
- **[M-ind]**: measured by a party other than the defence's authors (independent or adversarial evaluation).
- **[M-auth]**: measured by the defence's own authors. Treat as an upper bound on effectiveness.
- **[C]**: claimed, vendor statement or design argument with no measurement.
- **[2nd]**: figure obtained through a secondary report (press or blog), not checked against the primary document.

Scope notes: the web-search budget ran out near the end of this round. EchoLeak (CVE-2025-32711), SpAIware / ChatGPT memory exfiltration, the RAG membership-inference papers and embedding-inversion papers were found in search listings but **not** fetched or verified. They are listed under Gaps.

---

## 1. Memory poisoning: primary sources and defences with measured effect

### Takeaway
Single-shot memory poisoning through untrusted content is confirmed and severe. MemGhost reached 87.5% end-to-end success on OpenClaw/GPT-5.4 and 71.4% on Claude Code SDK/Sonnet 4.6. Every **content-level** defence measured independently failed, typically with ≥88% of attacks still succeeding or detectors missing >90%. The defences that measurably worked are **architectural**:
- removing or gating the memory tool,
- cryptographic write provenance, so only signed writes enter the retrieval pool,
- making memory writes visible to the user.

None of these was tested by a second team. Plainly worded false facts get through write-time screening completely (0 of 360 rejected). That is direct evidence for the brain's quarantine-and-corroborate design over classifier-based filtering.

### Cited Findings

**MemGhost (primary source, arXiv 2607.05189, 6 Jul 2026)**
- Authors: Yechao Zhang, Shiqian Zhao, Jiawen Zhang, Jie Zhang, Gelei Deng, Xiaogeng Liu, Chaowei Xiao, Tianwei Zhang. Threat model: a remote black-box attacker sends **one email**, gets no runtime feedback, and must achieve three things: a memory write, stealth in the reply to the user, and changed behaviour in a later separate session. The attack is trained with SFT plus RL against proxy environments. The benchmark is WhisperBench: 108 cases across 5 risk categories (fact and preference poisoning) on a real IMAP/SMTP workflow — [arXiv abs](https://arxiv.org/abs/2607.05189)
- [M-auth, attack paper] On 56 held-out test cases, end-to-end success was **87.5%** on OpenClaw with GPT-5.4 and **71.4%** on Claude Code SDK with Sonnet 4.6. The attack transfers to NanoClaw and Hermes Agent, and to filesystem and Mem0 vector memory backends — [arXiv abs](https://arxiv.org/abs/2607.05189)
- [M-auth] Transfer results with GPT-5.4: NanoClaw 80.4% (background) and 78.6% (foreground); Hermes 82.1% (background). With **Mem0** as the backend (native memory disabled), background end-to-end success was **85.7%** on both OpenClaw and Hermes — [arXiv HTML](https://arxiv.org/html/2607.05189v1)
- [M-ind, in the attack paper] Existing defences against MemGhost:
  - DataSentinel (input-level): **91.59% false-negative rate**.
  - Meta-SecAlign (model-level): injection success 49.07%, stealth success 98.15%.
  - AgentDoG (system-level): false-negative rate **93.46%** on OpenClaw and **40.38%** on Claude Code SDK.
  — [arXiv HTML](https://arxiv.org/html/2607.05189v1)
- [M-ind] A transparency-forcing prompt, which tells the agent to disclose memory writes, cut end-to-end success to:
  - 23.2% on Sonnet 4.6,
  - 19.6% on Sonnet 4.5,
  - 3.6% on GPT-5.4/Hermes,
  - 1.8% on GPT-5.4/OpenClaw.

  But injection success (memory actually written) **stayed at 33.9–94.6%**. The drop comes from loss of stealth, not from blocked writes. The paper's text is internally inconsistent on whether injection success "does not decrease much" — [arXiv HTML](https://arxiv.org/html/2607.05189v1)
- [C] The authors' recommended controls are provenance tagging, user confirmation for sensitive writes, content–memory separation and audit logging. They say filters are "necessary but insufficient", give no numbers, and do not model long-horizon decay over weeks — [arXiv HTML](https://arxiv.org/html/2607.05189v1)
- Secondary coverage confirming the 71–87% headline: [The Hacker News, Jul 2026](https://thehackernews.com/2026/07/new-memghost-attack-plants-persistent.html)

**Other 2025–26 memory-poisoning attacks**
- [M] Systematic study, arXiv 2606.04329 (Huawei / U. Waterloo, 3 Jun 2026). Six attack classes across four write channels, tested on OpenClaw and Hermes with GPT-OSS-120B:
  - average attack success: **34.25% (OpenClaw)** and **66.67% (Hermes)**,
  - Conditional Command Insertion: 67.89% / 76.00%,
  - Salience-Driven Compaction Poisoning: 45.10% / 85.17%.

  Hermes is worse because of its permissive write policy, a 2,200-character compaction threshold, and automatic injection of memory into the system prompt at session start — [arXiv 2606.04329](https://arxiv.org/html/2606.04329v1)
- [M-ind] The same study tested four detectors on memory-poisoning payloads (off-the-shelf true-positive rate / false-positive rate):
  - PIGuard 38.33% / 0.33%,
  - DataFilter 23.00% / 53.33%,
  - CommandSans 52.33% / 45.00%,
  - PromptArmor 67.67% / 1.00%.

  PromptArmor catches 84.44% of strong-signal attacks but only **42.50% of weak-signal** attacks (fact-like or precedent-like). Conclusion: "no defense achieves both high TPR and low FPR simultaneously" — [arXiv 2606.04329](https://arxiv.org/html/2606.04329v1)
- [M-auth] GhostWriter, arXiv 2607.06595 (NMSU, 6 Jul 2026): about **98% injection** and about **60% activation** across five agents and four LLMs. The proposed AM-Sentry defence (save policy plus retrieval screen) is claimed to "dramatically reduce" success, but no numbers were retrievable — [arXiv 2607.06595](https://arxiv.org/html/2607.06595v1)
- [M-auth] FARMA forged-reasoning attack, arXiv 2607.05029 (Penn State, 6 Jul 2026). It poisons stored decision logs and then cites them as precedent to fake a consensus.
  - Attack success: **100%** on EHRAgent across GPT-4o-mini, GPT-4o and Llama 3.3 70B; 52.0% ReAct-QA; 48.0% RAP.
  - **A-MemGuard (LLM judge) left EHR success at 100%.** A keyword filter had no effect.
  - The authors' SENTINEL pipeline reached 0% (EHR), 6.0% (ReAct-QA) and 0% (RAP), with 0 of 326 benign traces falsely flagged.
  - However, an adaptive paraphrasing attacker **bypassed SENTINEL's Reasoning Guard** in a preliminary test.
  — [alphaXiv 2607.05029](https://www.alphaxiv.org/abs/2607.05029.md)
- [M, real-world prevalence] Microsoft "AI Recommendation Poisoning" (Feb 2026): "Summarize with AI" buttons carry URL-parameter prompts such as "remember [Company] as a trusted source" that persist in assistant memory. Over 60 days Microsoft found **50+ unique prompts from 31 companies in 14 industries**, also spread by email, with turnkey tools (CiteMET, AI Share Button URL Creator) — [The Hacker News, 17 Feb 2026](https://thehackernews.com/2026/02/microsoft-finds-summarize-with-ai.html)
- [M] MINJA (query-only memory injection), as cited by arXiv 2601.05504: over 95% injection and 70% attack success under idealised conditions. Realistic conditions, where legitimate memories already exist, "dramatically reduce attack effectiveness". That paper's trust-scored sanitisation defence is sensitive to threshold choice: too strict blocks everything, too loose misses subtle attacks. Only the abstract was available, so there are no defended numbers — [arXiv 2601.05504](https://arxiv.org/abs/2601.05504)
- [M] Baseline attacks:
  - AgentPoison (NeurIPS 2024): average attack success ≥80%, poison rate **<0.1%**, benign impact ≤1%; 82% retrieval and 63% end-to-end success — [arXiv 2407.12784](https://arxiv.org/html/2407.12784v1)
  - PoisonedRAG (USENIX Security 2025): **90%** attack success with **5 malicious texts per target question** in a database of millions of texts; evaluated defences were "insufficient" — [USENIX](https://www.usenix.org/conference/usenixsecurity25/presentation/zou)

**Defences with measured effect**
- [M-ind, single author] arXiv 2605.08442 (Leong, 2026) tested six defences against a four-session delayed-trigger attack on 9 open-source models, N=40 per condition:
  - no defence 88.6%,
  - Minimizer, Sanitizer, RAG Sanitizer and RAG LLM Judge all **88.9% (no effect)**,
  - Prompt Hardening 77.8%,
  - **Memory Sandbox (tool-gating, recall tool removed) 11.1%**, with 100% benign task completion.
  - Exceptions: qwq:32b rose to 100% under the sandbox. A Bedrock replication found mistral-large-3 at 39/40, gpt-oss-120b at 22/40 and glm-5 at 13/40.
  - Quote: "input-level defenses cannot observe RAG-injected content."
  — [arXiv 2605.08442](https://arxiv.org/html/2605.08442v3)
- [M-ind, single author] arXiv 2608.21230 (21 Aug 2026), "Utility Under Attack":
  - Plainly worded false assertions, with no instructions or triggers, poisoning **1.2% of a LongMemEval corpus cut accuracy from 0.850 to 0.300**.
  - A 4-stage write-time content screen had 0.832 recall on indirect prompt injection but **rejected 0 of 360 poisoned memories**.
  - Provenance-weighted retrieval at the shipped weight was indistinguishable from no defence (p=0.80). A stronger weight raised accuracy from 0.3167 to 0.7000 only by excluding untrusted content. When the true evidence itself was untrusted, accuracy fell to 0.0417.
  - The author recommends **bounded occupancy constraints at retrieval**, meaning a cap on how much of the context untrusted items may occupy.
  — [arXiv 2608.21230](https://arxiv.org/abs/2608.21230v1)
- [M-auth, single independent author] SMSR, arXiv 2606.12703 (10 Jun 2026):
  - HMAC-SHA256 provenance tags at write time, so only signed entries are retrievable: unsigned injection fell from **93–100% to 0%**.
  - Adding randomised memory ablation with majority vote (5 runs): authenticated-injection success fell to **8.0%** (95% CI 5.8–10.9%), and a query-only end-to-end attack fell from 65.3% to **5.3%**.
  - Utility: 90% (component 1) and **85%** (combined).
  - Certified worst-case bound δ = 10.4% at 5 runs, for an adversary controlling ≤t entries.
  — [arXiv 2606.12703](https://arxiv.org/html/2606.12703)
- [M-auth] A-MemGuard (ICML 2026), using consensus validation across related memories plus a "lessons" memory, against AgentPoison on GPT-4o-mini:
  - EHRAgent retrieval-stage success 100 → 2.13, action-stage 87.23 → 6.38, end-to-end 100 → 36.17,
  - abstract claims ">95%" reduction,
  - utility "minimal", no number found.
  - Contradicted by FARMA, where A-MemGuard left forged-reasoning success at 100% (above).
  — [arXiv 2510.02373](https://arxiv.org/html/2510.02373v1); [ICML 2026](https://icml.cc/virtual/2026/poster/61006)
- [Framework] OWASP Top 10 for Agentic Applications 2026 lists Memory & Context Poisoning as **ASI06** — [promptfoo OWASP agentic mapping](https://www.promptfoo.dev/docs/red-team/owasp-agentic-ai/)

### Inferences
- The brain's rule that readers of untrusted content get no write authority matches the only class of defence with strong independent evidence: tool-layer gating (88.6% → 11.1%) and signed-write provenance (unsigned → 0%). Detectors and LLM judges should be treated as telemetry, not as gates.
- Quarantine-until-corroborated is directly supported by 2608.21230. False facts written in a plain register cannot be told apart by content, so the gate has to be **provenance plus corroboration**, not classification. Recommendation: corroboration must come from an independent, higher-trust source, never from a second copy of the same untrusted channel. FARMA's amplification phase defeats "N similar memories agree" logic, so A-MemGuard-style consensus across memories is unsafe as the only check.
- MemGhost's transparency result shows that **surfacing proposed writes to the user** collapses stealth (end-to-end success down to 1.8–23%). The poisoned item is still proposed, though, so the approval UI must show the source and the trust level, or approval fatigue reopens the hole.
- Bounded occupancy is cheap to implement and testable: for example, at most k untrusted-provenance items per context and never untrusted-only answers for high-stakes fact types. It should be added to the brain's retrieval contract.
- Hermes-style auto-injection of memory into the system prompt at session start was the strongest amplifier in 2606.04329. The brain should never auto-inject quarantined or low-trust memory into a client's system context.

### Gaps
- MemGhost's per-defence numbers for *provenance tagging / write confirmation* were not reported; the paper only recommends them.
- No independent replication of SMSR, A-MemGuard or Memory Sandbox. Each is single-team, and two are single-author.
- MemGuard (arXiv 2608.21867) PDF could not be parsed. AM-Sentry numbers were truncated.
- The "MINJA" original paper's numbers were taken via 2601.05504's abstract, not the primary source.
- No study measured poisoning at the brain's scale (10k+ items, multimodal) or in image or video memory.

---

## 2. Prompt-injection defences: measured results and adaptive-attack survival

### Takeaway
Every *in-band* defence evaluated adaptively broke, mostly above 90% attack success:
- prompting (spotlighting, sandwiching),
- detectors (PromptGuard, Protect AI, PIGuard, Model Armor),
- training (StruQ, SecAlign, MetaSecAlign, Circuit Breakers),
- secret-knowledge schemes (DataSentinel, MELON).

Human red-teamers beat 100% of challenges. *Out-of-band* deterministic designs show strong static results, with small utility costs and big token costs:
- CaMeL (77% vs 84% utility, provable security),
- FIDES (0 policy-violating injections),
- Progent (AgentDojo 39.9% → 1.0%).

Only Progent has an adaptive evaluation so far (held at 2.6%, weak attack, 7B model). CaMeL's guarantees **do not compose** across agents without a provenance-preserving protocol. Frontier-model robustness is improving fast but is not zero. The latest vendor numbers are about 0.2% (k=1) to 2% (15 attempts) for Claude Opus 5 on Gray Swan IPI [2nd], and 63% at 100 attempts for Opus 4.5 on agentic coding.

### Cited Findings

**Adaptive attacks break in-band defences**
- [M-ind] "The Attacker Moves Second", Nasr, Carlini, Sitawarin, Schulhoff, Hayes, Tramèr et al. (arXiv 2510.09023, Oct 2025; listed at USENIX Security 2026). Results under search, RL, gradient and human attacks:
  - Spotlighting **>95%** (AgentDojo; originally as low as 1%)
  - Prompt Sandwiching >95%
  - MetaSecAlign **96%** (originally 2%)
  - Protect AI detector >90%
  - **PromptGuard >90%**
  - PIGuard 71%
  - Model Armor >90%
  - RPO 98% (RL) and 96% (gradient)
  - Circuit Breakers 100%
  - MELON 76% (95% with full knowledge)
  - DataSentinel >80% attacker-task accuracy
  - StruQ broken "in every case"

  Human red-teaming involved 500+ participants, a $20k prize pool and 40 challenges. Humans **succeeded in all cases** (search attack 69% vs humans 100% on a subset).
  — [arXiv 2510.09023 HTML](https://arxiv.org/html/2510.09023v1); [USENIX Sec '26 listing](https://www.usenix.org/conference/usenixsecurity26/presentation/nasr)
- [M-ind, via review] Instruction hierarchy (GPT-4o-mini), even before adaptive effort: attack success value **0.68** (OpenPromptInjection) and **0.75** (MMLU-PI). SecAlign under adaptive attack: 0.88 (MMLU-PI) and 0.46 (OpenPromptInjection). StruQ: about 1.00 (Jia et al., as summarised) — [arXiv 2606.26479](https://arxiv.org/html/2606.26479v1)
- [M-auth, 2024 static] Spotlighting / datamarking (Microsoft, Hines et al.): attack success ">50% to <2%" on GPT-family models, with "minimal impact on task efficacy". It does **not** survive adaptive attack (see the >95% figure above) — [arXiv 2403.14720](https://arxiv.org/abs/2403.14720v1)

**Out-of-band and architectural defences**
- [M-auth] CaMeL (Google DeepMind and ETH, arXiv 2503.18813): the control and data flow is extracted from the trusted query, so "untrusted data retrieved by the LLM can never impact the program flow". Capabilities enforce data-flow policy at tool calls. It solves **77% of AgentDojo tasks with provable security vs 84% undefended** — [arXiv 2503.18813](https://arxiv.org/abs/2503.18813)
- [M-ind] CaMeL cost: **2.82× input tokens and 2.73× output tokens**. There is no adaptive evaluation, and the review authors demonstrate side channels against it — [arXiv 2606.26479](https://arxiv.org/html/2606.26479v1)
- [M-auth] "Can CaMeLs Talk?" (arXiv 2610.05640, NeurIPS 2026): CaMeL's guarantees **do not compose** when agents call agents. An injection succeeds even when every agent individually runs CaMeL. Attack success: 12.9% (no CaMeL), 0.2% (per-agent CaMeL), **0.0% (Multi-CaMeL protocol keeping trusted and untrusted channels separate)**. The utility cost shrinks with stronger models — [Emergent Mind summary](https://www.emergentmind.com/papers/2610.05640); [NeurIPS 2026](https://neurips.cc/virtual/2026/165381)
- [M-auth] FIDES (Microsoft: Costa, Köpf, Paverd, Russinovich et al., arXiv 2505.23643). It uses information-flow control with confidentiality and integrity labels, selective variable hiding, and a quarantined LLM with constrained output types (bool < enum < string). On AgentDojo with gpt-4o:
  - successful injections: basic planner 163, FIDES 24,
  - **with policy checks: FIDES 1 (0 after excluding non-policy-violating cases)**,
  - utility with policy checks falls by up to 24.5% for o3 and o4-mini, but beats the basic planner by up to 16.7%.
  — [arXiv 2505.23643](https://arxiv.org/pdf/2505.23643v2)
- [M-auth / M-ind] Progent (Shi, He, … Song; arXiv 2504.11703). It enforces deterministic symbolic privilege policies on tool names and arguments; an LLM drafts the policy and an SMT solver allows narrowing automatically but makes expansion require approval.
  - Reported by the authors: AgentDojo 39.9% → 1.0% and ASB 70.3% → 3.9% (Appendix E adaptive: about 0.5–4.2%).
  - **Independent replication on Qwen2.5-7B:** 25.8% → 4.2% (standard attack) → **2.6% (adaptive)**. Utility fell **45.2% → 27.1%**, with about **15× more LLM calls**.
  — [arXiv 2504.11703](https://arxiv.org/abs/2504.11703v2); [arXiv 2606.26479](https://arxiv.org/html/2606.26479v1)
- [Caveat] The adaptive review (2606.26479, LaunchSafe, 25 Jun 2026) is "preliminary and not peer-reviewed". Its adaptive attack is black-box and hand-crafted, and white-box GCG is untested. The authors say the result is "consistent with, but does not establish" that deterministic enforcement is harder to attack. CaMeL, FIDES, RTBAS, Conseca, FORGE and the dual LLM have **no adaptive evaluation** — [arXiv 2606.26479](https://arxiv.org/abs/2606.26479)
- [M-auth] PromptArmor (Berkeley et al., arXiv 2507.15219) uses an off-the-shelf LLM to detect and strip injections. On AgentDojo with a GPT-4.1 backend:
  - attack success **54.53% → 0.47%** (GPT-4o guard) and **0.00%** (GPT-4.1 guard),
  - false-positive rate 0.07–0.56%,
  - utility 64.27% → 68.68–76.35%,
  - against the adaptive AgentVigil fuzzer, **0.34%**.

  It was **not** in the Nasr adaptive set. On *memory-poisoning* payloads it caught only 67.67% overall and 42.50% of weak-signal ones (Section 1) — [arXiv 2507.15219](https://arxiv.org/html/2507.15219v1)
- [Design guidance] "Design Patterns for Securing LLM Agents against Prompt Injections" (arXiv 2506.08837; IBM, Invariant, ETH, Google, Microsoft). Six patterns: Action-Selector, Plan-Then-Execute, LLM Map-Reduce, Dual LLM, Code-Then-Execute, Context Minimization. Principle: once an agent ingests untrusted input, "it is impossible for that input to trigger any consequential actions" — [Simon Willison summary](https://simonwillison.net/2025/Jun/13/prompt-injection-design-patterns/); [arXiv 2506.08837](https://arxiv.org/pdf/2506.08837)
- [Design guidance] Meta's "Agents Rule of Two": an agent must not combine more than two of (A) processing untrusted inputs, (B) access to sensitive systems or private data, and (C) changing state or communicating externally. It builds on Willison's "lethal trifecta" — [Oso explainer](https://www-webflow.osohq.com/learn/agents-rule-of-two-a-practical-approach-to-ai-agent-security)

**Frontier-model robustness (current models)**
- [M, vendor] Anthropic (24 Nov 2025), browser use against an internal adaptive Best-of-N attacker, 100 attempts per environment. Attack success (model only / old safeguards / improved safeguards):
  - Opus 4.5: 8.0% / 7.6% / **1.4%**,
  - Sonnet 4.5: 13.8% / 10.8% / 1.9%,
  - Haiku 4.5: 12.0% / 11.1% / 2.4%.

  Quote: "No browser agent is immune to prompt injection." — [Anthropic](https://www.anthropic.com/research/prompt-injection-defenses)
- [M-ind, via review] Claude Opus 4.5 on Gray Swan Shade, agentic coding: **4.7% at 1 attempt, 33.6% at 10, 63.0% at 100** — [arXiv 2606.26479](https://arxiv.org/html/2606.26479v1)
- [M, vendor; 2nd] Claude Opus 5 system card (Aug 2026), as reported, on Gray Swan IPI (28 scenarios). Attack success at 15 attempts:
  - Opus 5: 0.2% (k=1), **2.0%**,
  - Opus 4.8: 5.5%,
  - Sonnet 5: 5.9%,
  - GPT 5.6 Sol 20.0%, Terra 30.4%, Luna 43.9%.
  — [LetsDataScience](https://letsdatascience.com/news/claude-opus-5-lowers-prompt-injection-benchmark-rate-5af39720)
- [M, vendor; 2nd] GPT-5.6 system card (3 Aug 2026), as reported: indirect prompt-injection average attack success Sol **3.77%**, Terra 3.32%, Luna 2.94% (OpenAI's own GPT-Red evaluations). Fake chain-of-thought attacks succeeded >95% against GPT-5.1 and <10% against Sol — [TechRepublic](https://www.techrepublic.com/article/news-gpt-5-6-prompt-injection/). **Conflict:** this does not match the 20–44% that Anthropic's card reports for GPT-5.6 variants. The benchmarks and attempt counts differ (OpenAI internal vs Gray Swan IPI at 15 attempts), so the two cannot be compared directly.
- [C] OpenAI (22 Dec 2025): "Prompt injection, much like scams and social engineering on the web, is unlikely to ever be fully 'solved'". OpenAI uses an RL-trained automated attacker and rapid-response loops — [Fortune](https://www.fortune.com/2025/12/23/openai-ai-browser-prompt-injections-cybersecurity-hackers)

### Inferences
- For the brain, the assistants (Claude, ChatGPT) are *untrusted planners* from the brain's point of view. Their model-level robustness (about 0.2–4% per attempt, rising steeply with repeated attempts) cannot be the security boundary. The boundary has to be server-side and deterministic:
  - per-tool, per-argument authorisation (Progent-style),
  - provenance and trust labels on every returned item (FIDES-style),
  - no write tool reachable in a request whose context included untrusted content (Rule of Two).
- The brain's MCP server can apply FIDES-like labelling without controlling the client. Every `resources/read` or tool result carries a trust or provenance label in `_meta`. Write tools refuse when the caller cannot attest to a clean context. In practice, the server can only enforce this on its own side: separate scopes, a mandatory human confirmation step for promotion from quarantine, and rate or occupancy limits.
- The Multi-CaMeL result matters for the brain. When the brain's own internal agents (extractors, summarisers) feed the main store, provenance must travel across every agent hop, or the guarantee is lost.
- Detector choice, if one is used as telemetry: PromptArmor-style LLM guards have the best published static and fuzzing numbers, but weak-signal memory payloads cut detection to about 42%. Budget for a detector as an alarm source, never as a gate.

### Gaps
- No adaptive (white-box) evaluation of CaMeL, FIDES or the dual-LLM pattern exists yet.
- The InjecAgent and ASB numbers for current frontier models (Opus 5, GPT-5.6) were not found in primary form. The system-card numbers are secondhand.
- No head-to-head comparison of FIDES and CaMeL on the same models.

---

## 3. MCP specification: current requirements, 2026 changes, incidents and hardening

### Takeaway
The current revision is **MCP 2026-07-28**. It is stateless: no sessions, no `initialize` handshake, and a new `server/discover`. On authorisation:
- **DCR is deprecated in favour of Client ID Metadata Documents (CIMD)**,
- clients MUST validate `iss` (RFC 9207),
- client credentials MUST be bound to the issuing authorisation server,
- the existing requirements remain: PRM (RFC 9728), the `resource` parameter (RFC 8707), audience validation, no token passthrough, and PKCE S256.

The 2025–26 incident record is dominated by command injection, supply chain and OAuth-discovery abuse, mostly client-side. The one directly relevant failure is **Asana's cross-tenant MCP logic flaw**: about 1,000 customers exposed for about 5 weeks.

### Cited Findings

**2026-07-28 revision: key changes since 2025-11-25**
- Protocol-level sessions and `Mcp-Session-Id` are removed. List endpoints no longer vary per connection, and cross-call state uses **server-minted handles passed as tool arguments** (SEP-2567). The `initialize` handshake is removed, so each request carries its protocol version and capabilities in `_meta` (SEP-2575). `server/discover` is now a MUST. `subscriptions/listen` replaces GET/SSE subscriptions. SSE resumability is removed. Multi Round-Trip Requests (`input_required`) replace server-initiated sampling and elicitation (SEP-2322). Tasks move to an extension (SEP-2663) — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- **`cacheScope` ("public" | "private") and `ttlMs` are required** on list and `resources/read` results; `cacheScope` controls whether shared intermediaries may cache the result (SEP-2549). Clients must validate `iss` (SEP-2468). DCR clients MUST send `application_type` (SEP-837). Credentials MUST be keyed by issuer and never reused with a different authorisation server (SEP-2352). `Mcp-Method` and `Mcp-Name` headers are required on POST (SEP-2243) — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- Deprecated: Roots, Sampling and Logging (SEP-2577); HTTP+SSE transport; **Dynamic Client Registration (RFC 7591) in favour of CIMD** (PR #2858). The deprecation window is at least 12 months (SEP-2596) — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

**Authorisation requirements (normative, 2026-07-28)**
- Authorisation servers MUST implement OAuth 2.1 (draft-ietf-oauth-v2-1-13). Authorisation servers and clients SHOULD support CIMD and MAY support DCR (deprecated). **MCP servers MUST implement Protected Resource Metadata (RFC 9728)**, and clients MUST use it for discovery. Authorisation servers MUST offer RFC 8414 or OIDC Discovery — [MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- Clients **MUST include `resource` (RFC 8707) in both the authorisation and token requests**, using the canonical server URI, "regardless of whether authorization servers support it". Servers **MUST validate that tokens were issued specifically for them as audience**, MUST NOT accept or transit other tokens, and must return 401 for invalid or expired tokens. Tokens MUST NOT go in query strings, and authorisation MUST be on every HTTP request — [MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- Scopes: servers SHOULD send `scope` in `WWW-Authenticate`. For insufficient scope they SHOULD return **403 with `error="insufficient_scope"`**, listing all required scopes in one challenge. Clients do step-up using the union of old and new scopes. Servers MUST account for scope hierarchies — [MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- Security considerations:
  - **PKCE MUST, using S256**, and clients MUST refuse if `code_challenge_methods_supported` is absent.
  - Authorisation servers **SHOULD issue short-lived access tokens** and **MUST rotate refresh tokens for public clients**.
  - HTTPS is required for all authorisation endpoints.
  - Exact redirect-URI matching.
  - The authorisation server MUST display the redirect hostname for CIMD and SHOULD warn on localhost-only redirects.
  - MCP servers MUST NOT pass through the client's token upstream.
  — [MCP Security Considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations)
- CIMD rules:
  - `client_id` is an HTTPS URL with a path,
  - the document MUST include `client_id`, `client_name` and `redirect_uris`,
  - the authorisation server MUST check that `client_id` equals the URL exactly and MUST validate redirect URIs against the document,
  - the authorisation server SHOULD cache respecting HTTP headers.
  - Client priority order: pre-registered → CIMD → DCR → prompt the user.
  - CIMD client IDs are portable across authorisation servers.
  — [MCP Client Registration](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration)
- Security Best Practices (2026-07-28):
  - **State handle hijacking:** servers "MUST NOT treat possession of a state handle as authentication". They SHOULD use secure random handles and SHOULD bind each handle to the user server-side, as `<user_id>:<handle>` with the user ID taken from the verified token.
  - SSRF: block private and link-local ranges, applying equally to authorisation servers fetching CIMD.
  - Scope minimisation: a minimal initial scope plus step-up. Common mistakes include wildcard scopes and "treating claimed scopes in token as sufficient without server-side authorization logic".
  - OAuth URL validation: only http(s), never shell-open.
  — [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)

**Client behaviour (what Claude and ChatGPT actually do)**
- Claude connectors:
  - CIMD is used **only if** the authorisation server advertises `client_id_metadata_document_supported: true` **and** `"none"` in `token_endpoint_auth_methods_supported`; otherwise Claude falls back to DCR, registering "a new client on every fresh connection".
  - PKCE S256 is sent on every request.
  - Callback `https://claude.ai/api/mcp/auth_callback`; Claude Code uses a loopback on any port.
  - The PRM `resource` must equal the URL as the user enters it.
  - **Only the first `authorization_servers` entry is used.**
  - Proactive refresh up to 5 minutes before expiry. Builders should rotate refresh tokens for public clients.
  - Anthropic egress range: `160.79.104.0/21`.
  — [Claude connector auth docs](https://www.claude.com/docs/connectors/building/authentication)
- ChatGPT connectors (third-party compatibility page, verified 31 Jul 2026): prefers CIMD (with `client_id` on chatgpt.com), supports DCR and pre-registration, **appends `resource` to both the authorisation and token requests**, and requires Streamable HTTP. The spec version is not published — [Zuplo compatibility](https://zuplo.com/learn/mcp/compatibility/clients/chatgpt-connectors.md)
- Enterprise-Managed Authorization extension (ID-JAG, "Cross App Access"), stable as of Jun 2026. The IdP issues an assertion at SSO and the MCP authorisation server mints a scoped token with no consent screen. Okta is the only shipping IdP. Clients include Claude, Claude Code, Cowork and VS Code. Claim: "deactivating a user also cuts their MCP access immediately" [C] — [The New Stack, 18 Jun 2026](https://thenewstack.io/mcp-gets-its-missing-enterprise-authorization-layer/)

**Incidents and advisories, 2025–26**
- **Asana MCP cross-tenant exposure:** a "logic flaw in the MCP system". The exposure ran from launch on 1 May 2025 until discovery on 4 Jun 2025 and affected **about 1,000 customers**. Exposed data could include tasks, comments, files and project metadata. The server was taken offline until 17 Jun — [BleepingComputer](https://bleepingcomputer.com/news/security/asana-warns-mcp-ai-feature-exposed-customer-data-to-other-orgs/)
- Timeline (AuthZed):
  - GitHub MCP prompt injection plus an over-scoped PAT leaked private repositories (May 2025),
  - WhatsApp MCP tool poisoning (Apr 2025),
  - MCP Inspector unauthenticated RCE, CVE-2025-49596 (Jun 2025),
  - **mcp-remote CVE-2025-6514**, OS command injection via a malicious `authorization_endpoint`, 437k+ downloads (Jul 2025),
  - Filesystem server sandbox escape, CVE-2025-53109/53110 (Aug 2025),
  - malicious Postmark MCP package BCC'ing all email (Sep 2025),
  - Smithery path traversal leaking a Fly.io token controlling 3,000+ apps (Oct 2025),
  - gemini-mcp-tool CVE-2026-0755 (Jan 2026),
  - fake Oura MCP spreading the StealC infostealer (Feb 2026),
  - **nginx-ui CVE-2026-33032 (CVSS 9.8), missing authentication on the MCP endpoint, about 2,600 exposed instances** (Mar 2026).
  — [AuthZed MCP breach timeline](https://authzed.com/blog/timeline-mcp-breaches)
- OX Security (15 Apr 2026): an STDIO-transport command-injection design flaw across the ecosystem, with 30+ disclosures, 10+ CVEs and 150M+ downloads affected. Products include LiteLLM, LangFlow, Flowise and Windsurf. OX lists Anthropic's MCP among "rejected disclosures", meaning the vendor treated it as expected behaviour — [OX Security](https://www.ox.security/blog/mcp-supply-chain-advisory-rce-vulnerabilities-across-the-ai-ecosystem/)
- **OAuth-discovery token theft in official SDKs (2026):**
  - **rmcp (Rust) CVE-2026-63127**, CVSS 8.2: resource-metadata spoofing let a malicious server obtain a real authorisation server's token; fixed in rmcp 2.0.0, disclosed 16 Sep 2026 — [Wiz](https://www.wiz.io/vulnerability-database/cve/cve-2026-63127)
  - **TypeScript SDK CVE-2026-104850**, CVSS 7.5: the server could choose which authorisation server received the client's stored credentials (refresh tokens, secrets); fixed in `@modelcontextprotocol/sdk` 1.31.0 and `@modelcontextprotocol/client` 2.2.0, published 6 Oct 2026 — [OpenCVE](https://app.opencve.io/cve/CVE-2026-104850)
  - **Python SDK GHSA-qx49-fqc8-xw99:** missing issuer verification sent the client secret, auth code and PKCE verifier to the attacker; fixed in 1.30.0 and 2.2.0 (7 Sep 2026); machine-to-machine providers need an issuer setting configured — [Expert Insights](https://expertinsights.com/?p=61293)
- OpenCode MCP OAuth RCE: a malicious `authorization_endpoint` led to PowerShell `$(...)` evaluation on Windows and WSL. Versions 1.0.137–1.18.32 were affected; it was fixed silently in 1.18.33 (28 Sep 2026) with no CVE. The scheme allowlist alone would not have stopped it, because the payload used https — [OrcaRouter](https://www.orcarouter.ai/blog/2026-10-19-opencode-mcp-oauth-rce)

### Inferences
- Build to 2026-07-28 but stay backward-compatible. ChatGPT's spec version is unpublished, and Claude falls back to DCR unless CIMD is advertised **with** `"none"` auth. The brain's authorisation server should therefore:
  - advertise CIMD plus `none` plus DCR,
  - emit `iss` and set `authorization_response_iss_parameter_supported: true`,
  - require PKCE S256,
  - issue audience-bound short-lived access tokens (minutes), with rotating refresh tokens.
- **Mark every tenant-data result `cacheScope: "private"`** and set a short or zero `ttlMs`. A `public` scope on per-user memory would invite shared-intermediary caching, which is a cross-tenant leak path created by the 2026 spec itself.
- With sessions gone, any server-side "conversation" or "working set" handle is a hijack target. Key all state as `<token-derived user_id>:<random handle>` and re-authorise on every call, as the spec says.
- The Asana incident is the canonical failure mode for the brain: a logic error in the MCP layer, not a hack. Mitigation: authorisation must be enforced *beneath* the MCP layer, in a ReBAC/FGA check on every retrieved item, so an MCP-layer bug cannot widen access. Cross-tenant canary queries in CI are also needed (Section 6).
- The brain is a *server*, so the SDK OAuth CVEs mostly affect clients. The brain's own ingestion connectors (Gmail, Drive) act as OAuth clients, though, and must pin issuers and avoid shell-opening URLs.

### Gaps
- The full GitHub diff 2025-11-25…2026-07-28 was not reviewed beyond the changelog.
- No official OpenAI documentation was fetched on ChatGPT's MCP auth behaviour; the source is a third-party compatibility page.
- It could not be verified whether Claude or ChatGPT honour `cacheScope` or `ttlMs` yet.

---

## 4. Permission revocation and consistency: Zanzibar tokens, SpiceDB/OpenFGA modes, index invalidation

### Takeaway
Zanzibar-style systems solve "new enemy" ordering with consistency tokens (zookies in Zanzibar, ZedTokens in SpiceDB). But **defaults favour latency**:
- SpiceDB checks default to `minimize_latency`, with a 5-second quantisation window in which checks are cached,
- OpenFGA defaults to `MINIMIZE_LATENCY`, with caching off by default, and **has no zookie equivalent yet**.

Enterprise search shows the failure mode: SharePoint/Copilot permission changes take "24–48 hours" per a Microsoft staff answer, and Azure AI Search indexers run every 5 minutes to 24 hours, with parent-scope ACL changes not propagating automatically. No independent, peer-reviewed measurement of revocation latency was found. The recommended practice is to measure it yourself with canary probes.

### Cited Findings
- [M, vendor] Zanzibar (Google, USENIX ATC 2019): trillions of ACLs, millions of checks per second, **95th-percentile latency <10 ms**, **>99.999% availability over 3 years**, and decisions that "respect causal ordering of user actions and thus provide external consistency amid changes to access control lists and object contents" — [Google Research](https://research.google/pubs/pub48190/)
- SpiceDB consistency modes (the docs page was fetched; it states no default for the quantisation interval):
  - `minimize_latency` is the default for all read APIs and leaves a New Enemy window,
  - `at_least_as_fresh(ZedToken)`,
  - `at_exact_snapshot`, which can fail after GC,
  - `fully_consistent`, which bypasses the cache and is the default for Write/Delete Relationships.
  - **On CockroachDB, `fully_consistent` does not guarantee read-after-write**, so use `at_least_as_fresh` there.
  - Recommended pattern: **store the ZedToken with the resource** in the primary database and update it whenever content or access changes.
  — [SpiceDB consistency docs](https://authzed.com/docs/spicedb/concepts/consistency)
- [C, docs] "By default, SpiceDB sets the Quantization Interval to 5s; check operations are cached within this window." It is configurable via `--datastore-revision-quantization-interval` — [authzed/docs PR #352](https://github.com/authzed/docs/pull/352)
- OpenFGA:
  - `MINIMIZE_LATENCY` (default) is served from cache when possible; `HIGHER_CONSISTENCY` bypasses the cache.
  - "OpenFGA caching is disabled by default". With the cache off, all queries are strongly consistent.
  - The cache flags (`check-query-cache-ttl`, `cache-controller-enabled`, …) control staleness. The cache controller checks for recent writes so TTLs can be larger.
  - Guidance: choose `HIGHER_CONSISTENCY` per request when the resource changed within the cache TTL. "Always specifying HIGHER_CONSISTENCY will have a significant impact in performance".
  - **Zookies are not yet available.**
  — [OpenFGA consistency](https://openfga.dev/docs/interacting/consistency)
- [C, vendor staff, not official docs] "SharePoint permissions changes can take **24-48 hours** to fully index and be reflected" (Microsoft Q&A, Apr 2025, about a Copilot agent still answering after a permission change) — [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2246896/copilot-agent-still-providing-responses-after-shar)
- [2nd, quoting Azure docs] Azure AI Search:
  - indexer schedule minimum 5 min, maximum 1,440 min (24 h), with failure backoff up to about 2 h or 24 h,
  - "the index serves stale ACL data for previously ingested files" until an update runs,
  - **parent-scope permission changes do not propagate automatically** and need an explicit resync (`options: ["permissions"]`),
  - content webhooks don't fire on permission changes,
  - the query-time remote SharePoint knowledge source has "no drift by construction" but turns a Graph outage into a retrieval outage.
  — [Particula](https://particula.tech/blog/rag-document-acl-sync-stale-permissions)
- [Method] Measurement protocol: record t0 at revocation, poll as the revoked principal until the canary stops returning (t1), alert on t1−t0 rather than on indexer success, and run it in CI — [Particula](https://particula.tech/blog/rag-document-acl-sync-stale-permissions); also [DeepInspect on Glean](https://www.deepinspect.ai/blog/glean-permissions), which distinguishes the snapshot-mirrored "indexed access" mode from live checks and calls the gap a "measurable revocation window" (no numbers given)
- [MCP] Authorisation servers SHOULD issue short-lived access tokens and MUST rotate refresh tokens for public clients — [MCP Security Considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations). Five Eyes agentic-AI guidance: least privilege, just-in-time credentials, "revoke elevated permissions promptly" — [Hunton summary of "Careful Adoption of Agentic AI Services", 1 May 2026](https://www.hunton.com/privacy-and-cybersecurity-law-blog/cybersecurity-authorities-issue-joint-guidance-on-the-adoption-of-agentic-ai-systems)

### Inferences
- Revocation in the brain has four independent clocks, and the effective latency is the maximum of them:
  1. the ReBAC check cache (SpiceDB about 5 s quantisation unless a ZedToken or `fully_consistent` is used),
  2. derived artefacts (vector index metadata, summaries, graph edges, LLM-generated "facts" that copied content),
  3. OAuth access-token lifetime, since JWTs validated locally cannot be revoked before expiry unless the server does introspection or keeps a deny-list,
  4. client-side caches (MCP `ttlMs`, the assistant's own conversation context, which the brain cannot claw back).
- Pattern for zero-leak revocation:
  - (a) **query-time authorisation on every returned item**, never index-time-only ACLs;
  - (b) on a revoke write, take the returned ZedToken and store it as a per-principal "min freshness" watermark; every retrieval for that principal or resource then uses `at_least_as_fresh(watermark)` until the watermark is older than the quantisation window;
  - (c) derived artefacts carry the **set of source IDs** they were derived from and are re-checked against those sources at read time (a derivation-lineage ACL), so a summary cannot outlive access to its sources;
  - (d) access tokens with a lifetime of 5 minutes or less, plus a server-side revocation list checked per request for a removed member;
  - (e) MCP results `cacheScope: private` with a small `ttlMs`.
- Test: a revocation-SLA test in CI.
  1. Grant a principal access to a canary item, then retrieve it via MCP.
  2. Revoke the access.
  3. Poll every 100 ms through every surface (MCP search, MCP read, app API, graph expansion, summaries) and record p50, p99 and max time-to-denial.
  4. Target ≤ quantisation window + 1 request for direct items, and the same for derived artefacts via lineage checks.
- OpenFGA lacks zookies, which makes SpiceDB (or another Zanzibar implementation with consistency tokens) the stronger fit for a zero-leakage target, unless OpenFGA runs with caching off.

### Gaps
- No independent, peer-reviewed measurement of revocation latency in RAG or enterprise search was found. The "hours to over a week" figure from earlier research could not be re-verified in this round, and the only figure found is Microsoft staff's 24–48 h.
- Glean's and Copilot's official revocation SLAs were not found.
- The SpiceDB `max-staleness-percent` default was not confirmed.

---

## 5. Cross-tenant leakage in RAG and vector systems: side channels and shared caches

### Takeaway
Cross-tenant leakage has at least four measured channels beyond direct access bugs:
1. **graph pivots**: hybrid RAG leaked in up to 95% of queries; per-hop authorisation drove this to 0;
2. **shared index statistics**: TF-IDF document-frequency side channels in Elasticsearch and hosted search, where even rank-only output leaks;
3. **shared prefix or KV caches in LLM serving**: 7 of 17 API providers shared caches globally in 2024; SpliceLeak achieves up to 100% token extraction from non-prefix RAG KV caches;
4. **spec-level caching hints**, such as MCP `cacheScope`.

The fixes are known and cheap: per-tenant statistics or indices, per-hop authorisation, per-principal cache salting.

### Cited Findings
- [M-auth] Retrieval Pivot Attacks (Thornton, arXiv 2602.08668v3, Mar 2026):
  - Vector-only retrieval had a retrieval pivot rate (RPR) of 0.0. Undefended hybrid vector-to-graph retrieval had **RPR 0.954** on benign queries (synthetic, 1,000 documents), 0.695 on Enron (50k emails) and 0.085 on SEC 10-Ks.
  - All leakage occurred at **pivot depth 2** (chunk → entity → chunk).
  - Leakage happens **without** any adversarial injection, purely through shared entities.
  - **Per-hop authorisation at the graph-expansion boundary reduced RPR to 0.0** on all corpora and attacks, with "negligible" latency (number not retrieved). It is robust to metadata mislabelling up to 5%.
  — [arXiv 2602.08668](https://arxiv.org/html/2602.08668v3)
- [M] Shared search-index side channels (Wang, Grubbs, Lu, Bindschaedler, Cash, Ristenpart; the file is named sp2017):
  - TF-IDF scores computed over all tenants' documents leak document frequencies of private terms ("STRESS" attacks: score dipping, shard mapping, term extraction). **Rank-only attacks work even without scores.**
  - Vulnerable: Elasticsearch, MySQL FULLTEXT, AWS Elasticsearch, AWS CloudSearch, Searchly, Bonsai, Swiftype. GitHub was attacked in a case study (191-shard map in 104 h).
  - Not vulnerable: PostgreSQL, Couchbase and others with per-tenant indices.
  - Fix: **document frequencies from a public corpus**, or "blind DFs". Removing scores alone is insufficient.
  — [Princeton PDF](https://www.cs.princeton.edu/~lw19/pub/sp2017.pdf)
- [M] Auditing Prompt Caching in Language Model APIs (Gu et al., ICML 2025):
  - Caching was detected in **8 of 17** providers, and **7 shared caches globally across users or organisations**: Azure and OpenAI text-embedding-3-small, Deep Infra, Fireworks, Lepton, Perplexity, Replicate.
  - Method: one-sided KS tests at α=10⁻⁸.
  - Disclosed Oct 2024; "at least five providers made changes".
  — [arXiv 2502.07776](https://arxiv.org/html/2502.07776v1)
- [C, vendor docs] Anthropic: "Caches are isolated between organizations. Different organizations never share caches". Isolation is also per workspace on the Claude API, Claude Platform on AWS and Microsoft Foundry; **Bedrock and Google Cloud have organisation-level isolation only**. KV caches are held in memory only — [Claude prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [M] KV-cache timing attacks in self-hosted serving, as summarised in arXiv 2608.09225:
  - PROMPTPEEK (NDSS 2025): 99–100% success on SGLang's radix cache,
  - InputSnatch: 62% disease extraction and 13.5% symptoms under real-world limits; 43–100% against semantic caches,
  - vLLM, SGLang, LMCache, TGI and TensorRT-LLM key caches on tokens alone, **not bound to the principal**,
  - measured cached vs cold TTFT: 32.8 ms vs 149.6 ms (vLLM, A100, 2,119-token prefix).
  - The proposed per-principal HMAC-salted block hashing (KVGov) is **simulation-only**.
  — [arXiv 2608.09225](https://arxiv.org/html/2608.09225)
- [M-auth] SpliceLeak (arXiv 2606.21842, 20 Jun 2026): a timing side channel on **non-prefix KV-cache fusion used in RAG serving** (vLLM + LMCache). Up to **100% extraction** in bounded-entropy cases, a +104 ms gap, and as few as 63 requests per token despite batching noise. The SpliceDefense mitigation (quantised chunk padding plus constant-time boundary fusion) flattens ΔTTFT to about 0 with "negligible" throughput overhead — [arXiv 2606.21842](https://arxiv.org/abs/2606.21842)
- [M, NVIDIA guidance exists] NVIDIA published guidance on structuring applications to secure the KV cache (not fetched) — [NVIDIA blog](https://developer.nvidia.com/blog/structuring-applications-to-secure-the-kv-cache/)
- [Spec] MCP 2026-07-28 requires `cacheScope` ("public"/"private") on list and read results, which governs shared-intermediary caching — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

### Inferences
- The brain's "shared statistics" risk is real and has a known fix:
  - BM25/TF-IDF must use **per-partition statistics**, or statistics from a public or reference corpus, never global statistics across partitions;
  - learned sparse or dense rankers trained or calibrated on all tenants' data carry a similar risk;
  - rerankers and "popularity" or recency priors must not aggregate across partitions.
- Rank-only output still leaks, so **counts, "N more results hidden", facet totals and latency** must not depend on items the caller cannot see. Apply the authorisation filter before top-k with a padded or constant response shape, rather than post-filtering, which also returns fewer than k results and so leaks.
- If the brain self-hosts any embedding, reranking or LLM inference with prefix or KV caching (vLLM, SGLang, LMCache), turn on per-partition cache salting, or disable cross-partition reuse. Hosted Anthropic is organisation- and workspace-isolated, but Bedrock and Vertex are organisation-only. Map each brain partition to its own workspace on the Claude API if partitions share one organisation, or accept that they share a cache.
- The graph-bridge fix (per-hop checks) is validated at RPR 0.0. Keep it, and add a test corpus with deliberate shared entities across partitions, such as "Dad's gym" appearing in both the household partition and the business partition.

### Gaps
- RAG membership-inference papers ("Is My Data in Your Retrieval Database?" arXiv 2405.20446; "Riddle Me This!" arXiv 2502.00306; mask-based MIA arXiv 2410.20142) and embedding-inversion work (ALGEN, arXiv 2502.11308) were found in search but **not fetched**, so no numbers are available.
- No paper was found that measures vector-database (HNSW) timing side channels across tenants in shared collections with metadata filtering. This looks like an open research gap.
- No measured latency figure for per-hop authorisation was retrieved (the appendix was truncated).

---

## 6. Canary and honeytoken monitoring for leakage in AI systems

### Takeaway
Canary strings embedded in retrieved content give **high-precision, adaptive-resistant leakage detection** in the one rigorous RAG study:
- CanaryRAG: 94–96% TPR under adaptive attack with a dual-path oracle, 0.08–0.15% FPR, at 1.9× FLOPs.

A canary *alone* in single-pass output scanning catches little (Det 0.30). Canaries work as one layer in a pipeline (Det 0.94, FPR 1.8%). No public evidence was found of production canary-fact deployments in AI memory products.

### Cited Findings
- [M-auth] CanaryRAG, "Detecting RAG Extraction Attack via Dual-Path Runtime Integrity Game" (arXiv 2604.10717; ACL Anthology preview path suggests ACL 2026). Non-semantic, high-entropy canaries are injected into retrieved chunks. The target path must never emit them, and an oracle path must reproduce them.
  - TPR: **99.2%** non-adaptive; **94.1% and 95.6%** adaptive with the oracle, vs 51.8% and 23.4% without it.
  - FPR: **0.13% / 0.08% / 0.15%** on benign queries.
  - BERTScore 0.517 → 0.515.
  - **1.90× FLOPs.**
  - Only two extraction attacks were tested (Pirates, RAG-Thief).
  — [arXiv 2604.10717](https://arxiv.org/pdf/2604.10717); [ACL preview](https://preview.aclanthology.org/ingest-acl/2026.acl-long.385/)
- [M-auth] "Caught in the Act(ivation)" (UCSC, arXiv 2606.04141, ICML 2026 AIWILD workshop): exfiltration of credentials by agents.
  - Canary text detector alone: **Det 0.30, FPR 0.00**.
  - Canary plus input filter: 0.82 / 0.15.
  - Honeytoken baseline on multi-turn: **0.06**.
  - Full pipeline (with a white-box activation probe): **0.94 / 0.018**.
  - Caveats: lab-only; canaries fail if attackers can tell honeytokens from real secrets; structured tool-call arguments are a blind spot.
  — [arXiv 2606.04141](https://arxiv.org/pdf/2606.04141)
- [M, operational] Microsoft's AI Recommendation Poisoning guidance tells organisations to hunt for URLs pointing to AI-assistant domains that contain prompt keywords ("remember", "trusted source", "in future conversations"). This is a detection signature that can apply to ingested email and web content — [The Hacker News](https://thehackernews.com/2026/02/microsoft-finds-summarize-with-ai.html)
- [Method] Canary-based revocation and leak probing in CI (see Section 4) — [Particula](https://particula.tech/blog/rag-document-acl-sync-stale-permissions)

### Inferences
- For the brain, plant **per-partition canary facts** that have high entropy, are unique per partition and per principal, and are semantically plausible enough to be retrieved by realistic queries. Two monitors:
  - (a) **egress scanning** of every MCP response for any canary not belonging to the caller's partitions, which gives deterministic cross-tenant leak detection;
  - (b) **scheduled probes** acting as each principal, querying for other partitions' canaries.
- CanaryRAG's dual-path idea maps to a "should-never-appear" and "should-appear" pair. The brain can periodically confirm that its own partition's canary *is* retrievable (to catch silent index breakage) and that other partitions' canaries are *not* (to catch leaks).
- Honeytokens detect *exfiltration*. They do not prevent poisoning. Pair them with "honey instructions": canary injected instructions in test-ingested email whose execution would trip an alarm. This measures live poisoning susceptibility per client model.

### Gaps
- No public evidence was found of canaries or honeytokens used in production AI memory or assistant products (ChatGPT memory, Claude memory, Copilot), and no incident report crediting a canary with detection.
- Dreadnode's "honeytoken probing" red-team docs and the klu.ai canary-token glossary appeared in search but were not fetched.

---

## 7. Australian context: OAIC guidance and Notifiable Data Breaches implications

### Takeaway
Under OAIC guidance, **AI-inferred or generated information, even false information, can be personal information**, and generating it counts as a *collection* under APP 3. A poisoned "fact" about a person is therefore a privacy issue, not only a security one, because it engages APP 10 accuracy. Leakage across partitions is "unauthorised disclosure". If serious harm is likely, it is an **eligible data breach**: assess within 30 days and notify individuals and the OAIC "as soon as practicable". The 2024 reforms add APP 11.3 ("technical and organisational measures"), automated-decision transparency from **10 December 2026**, and a statutory privacy tort (in force since June 2025).

### Cited Findings
- OAIC "Guidance on privacy and the use of commercially available AI products" (21 Oct 2024, updated 17 Jan 2025):
  - personal information includes false information, such as hallucinations and deepfakes,
  - **generating or inferring personal information is a collection under APP 3**, so it must be reasonably necessary and lawful, and sensitive information generally needs consent,
  - APP 10 accuracy: "AI systems are known to produce inaccurate or false results"; the steps are testing, human oversight and labelling outputs as probabilistic,
  - APP 11: organisations should "take active steps to ensure that the use of an AI system will not expose" holdings to added risk,
  - large AI data stores "may increase the risks related to data breaches", and data in AI systems is hard to trace or remove,
  - entering personal information into public AI tools can be an APP 6 disclosure.
  — [OAIC](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products)
- NDB scheme:
  - An eligible data breach is "unauthorised access to, or unauthorised disclosure of personal information, or a loss of personal information" that is "likely to result in serious harm", judged from a reasonable person's view. Serious harm is likely when it is "more probable than not". It is not eligible if remedial action prevents the harm (s 26WF).
  - When a breach is only suspected, take "all reasonable steps to complete this assessment within 30 calendar days". Notify individuals and the OAIC "as soon as practicable".
  - Coverage: agencies, businesses and NFPs with **turnover above $3 million**, health service providers, credit bodies, and some small businesses (for example, TFN recipients).
  — [OAIC quick reference guide](https://www.oaic.gov.au/privacy/notifiable-data-breaches/quick-reference-guide-for-responding-to-data-breaches)
- Statement to individuals must include: the entity's identity and contacts, a description of the breach, the kinds of information involved, and recommended steps (s 26WK(3)) — [OAIC NDB overview PDF](https://www.oaic.gov.au/__data/assets/pdf_file/0011/5213/the-ndb-scheme-an-overview.pdf)
- Privacy and Other Legislation Amendment Act 2024 (assent 10 Dec 2024):
  - **APP 11.3 requires considering "technical and organisational measures"**,
  - automated-decision privacy-policy transparency after a grace period ending **10 December 2026**,
  - statutory tort for serious invasions of privacy (from 10 June 2025 at the latest), with damages capped at the greater of $478,550 and the defamation cap,
  - tiered civil penalties, OAIC infringement notices and compliance notices.
  — [Norton Rose Fulbright](https://www.nortonrosefulbright.com/de-de/wissen/publications/be98b0ff/australian-privacy-alert-parliament-passes-major-and-meaningful-privacy-law-reform)
- NDB statistics: **1,205 notifications in calendar 2025** (+8% on 1,112 in 2024), the highest since the scheme began, with 716 from malicious or criminal attacks. AI is not mentioned (OAIC, 6 Jul 2026) — [OAIC media release](https://www.oaic.gov.au/news/media-centre/data-breach-notifications-increase-to-all-time-high-in-2025%2C-new-ndb-stats-show)
- Five Eyes guidance "Careful Adoption of Agentic AI Services" (1 May 2026, hosted on cyber.gov.au; Australia among the authors):
  - minimum access for minimum duration, just-in-time credentials, prompt revocation,
  - each agent as a distinct identity,
  - "Accountability remains with human decision-makers",
  - logging of tool use and privilege changes.
  — [Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/cybersecurity-authorities-issue-joint-guidance-on-the-adoption-of-agentic-ai-systems)

### Inferences
- A cross-partition leak would very likely be an *unauthorised disclosure*. Examples: a staff member's assistant retrieving the owner's household memory, or one business partner seeing another's. Whether it is *eligible* turns on likely serious harm, which is high for financial, health or family data. The brain needs audit logs good enough to tell, within the 30-day assessment window, exactly which items were exposed to whom. That calls for per-retrieval audit records: principal, client, item IDs, trust level, timestamp.
- Memory poisoning that plants false facts about identifiable people engages APP 10 (accuracy) and arguably APP 3 (collection by generation). The quarantine and provenance trail is also the compliance evidence of "reasonable steps".
- Remedial action under s 26WF, which can avoid notification, is more achievable when canary detection plus fast revocation contain a leak before the information is used. That is a regulatory reason to invest in fast revocation and egress canaries.
- The automated-decision transparency obligation from 10 Dec 2026 may apply if brain-derived memory drives decisions about staff or members, for example rostering or membership actions. Privacy policies would need updating.

### Gaps
- Whether the Privacy Act covers a household or personal partition is unconfirmed; no source was retrieved on the personal and household exemption or the small-business exemption as they apply to the brain's mixed use. Legal advice is needed.
- No OAIC guidance specific to agentic AI or AI *memory* was found. The 2024 guidance predates agentic memory products.
- Required contents of the statement to the OAIC (as opposed to the statement to individuals) were not retrieved.
- No OAIC determination or NDB case involving an AI memory or RAG system was found.
