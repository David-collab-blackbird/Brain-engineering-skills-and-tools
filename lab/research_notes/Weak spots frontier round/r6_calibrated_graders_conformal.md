# R6: Calibrated decision models, self-learning confidence graders, certified recall (as of 23 Oct 2026)

Scope: (1) calibrated decision/grader models, hosted and local, with Jev (TypeSafe AI) checked in detail; (2) graders that improve from the system's own outcomes; (3) conformal guarantees for retrieval sets and extraction checks. Open-source Jev replications (repos, code, licences, sandbox runs) belong to stream R7 and are not duplicated here. Papers that explain how System One models are trained are included.

Evidence labels used throughout:
- **[V]** vendor or first-party claim
- **[I]** independent measurement
- **[S]** single study / preprint
- **[2nd]** secondary write-up
- **[A]** anecdote / small-n developer report
- **[OBS]** Claude read the primary source or ran the code; **[INF]** inferred

Hypotheses this round can move: **U7** (self-learning confidence grader), **I15** (certified recall by conformal prediction), **I16** (three tiers: code / System One / System Two), **DA2 I-1** (two-budget standard), and the R3 human-review findings (31% catch rate, habituation).

---

## Q1. Jev / TypeSafe AI: what is verifiable

### Takeaway
Jev is real, hosted only, US-hosted, closed. The models page lists input as "Text" and "does not accept audio or video"; the docs also describe image state and a Box primitive, so image support is inconsistently documented. It returns probabilities for Choice, Score and Noul (yes/no) questions. Only Choice and Score carry a `confidence` field, and that field measures the *shape* of the distribution, not correctness.

TypeSafe has published no paper, no architecture, no parameter count and no RLCD recipe. Its claims of "zero hallucinations" and calibration have no published reliability data behind them.

Independent results converge:
- Jev is about as accurate as mid-price LLMs and behind the frontier on most labelled tasks.
- Its raw probabilities are usually better calibrated than LLM *verbalised* confidence, but often *worse* than a temperature-refit LLM or a trained classifier.
- Calibration error varies widely by task (median per-benchmark ECE 0.168 in the largest study). Overconfidence and underconfidence both occur.
- A cheap refit (temperature/Platt) on a few hundred labels fixes most of it.

For the brain, the data-residency facts are decisive: member data cannot go to Jev. Australian-hosted and on-prem options do not exist. Zero data retention is enterprise-only.

### Cited Findings

**Product and API (vendor)**
- [V][OBS] TypeSafe calls Jev its "first public System One Model". Its home page claims "a new architecture, a new sampler, and a new training algorithm" (RLCD), "Zero Hallucinations", 0.114 s vs 8.566 s for LLMs ("193.6x faster"), and $42 per *billion* input tokens. It gives no technical detail, and its FAQ questions ("How can Jev be so fast?", "Are prices subsidized?") have no answers — [typesafe.ai](https://typesafe.ai/)
- [V][OBS] Docs: three primitives plus Box (image).
  - **Choice** returns `choice`, `probabilities`, `confidence`.
  - **Score** returns `score`, `probabilities`, `confidence`.
  - **Noul** returns P(yes) only.
  - Several questions per call are "evaluated in parallel, each in isolation against the same state"; docs advise keeping questions narrow and combining factors in code.

  — [docs intro](https://docs.typesafe.ai/introduction)
- [V][OBS] **Confidence is not a probability of being right.**
  - Choice: confidence = (p_max − 1/n)/(1 − 1/n).
  - Score: 1 − (expected distance from mode)/(uniform MAD).
  - Noul has no confidence field; docs suggest |2p − 1|.
  - Threshold advice: three bands; 0.7/0.3 starting points for Noul; "The correct threshold values depend on your domain and the performance of the model for your use case"; "test with your own data". The page never uses the word calibration.

  — [docs: Confidence](https://docs.typesafe.ai/confidence.md)
- [V][OBS] Models page:
  - `jev-1.14.0` released 14 Oct 2026 (alias `jev-preview`); `jev-1.13.0` is `jev-latest`.
  - Context: 64k per request, 32k per question; up to 262k with a `TypeSafe-Danger-Zone-Long-Context` header, "slower and less accurate".
  - $0.042 per million input tokens; output free; text only.
  - Rate limits are set per organisation in the console. Request body ≤32 MiB.

  — [docs: Models](https://docs.typesafe.ai/models.md); [docs: errors](https://docs.typesafe.ai/api/errors.md)
- [V][OBS] Known weaknesses of jev-1.13 (vendor "jaggedness" page):
  - literal reading; unreliable counting ("count in code"); numeric representations
  - Score levels "weak in numerical calibration"; dates handled as text
  - indirection / multi-hop; accuracy drops with large or irrelevant state ("context rot")
  - adversarial content not treated as hostile; contradictory instructions
  - **Choice "leans toward the option that comes first"**; not for generation

  — [docs: Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- [V][OBS] Cookbooks touch our use cases, all on tiny samples with no precision/recall reported:
  - RAG passage classifier: 81 passages, 6 queries, thresholds 0.45 relevance / 0.55 answer-evidence / 0.70 injection, described as "starting points for this corpus".
  - "Simple memory system": a Noul "remember?" gate at 0.5, two customers, five tickets; limitations listed include "reinforced mistakes" and unbounded growth.
  - Self-consistency cookbook: mean per-question probability SD 0.0102 over 15 repeated calls; two questions oscillated 0.43–0.53 and 0.53–0.62 around 0.5.
  - Feature-discovery cookbook: Jev answers become features for a CatBoost model trained on outcomes. Held-out RMSE 1.772 vs 2.466 for word counts. Learning happens in the downstream model, not in Jev.

  — [RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages.md); [memory](https://docs.typesafe.ai/cookbooks/basic_memory.md); [self-consistency](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook.md); [feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md)

**Company, launch and RLCD**
- [2nd] Founder and CEO Diogo Almeida (ex-OpenAI; TypeSafe says he co-invented RLHF/InstructGPT). $40M seed led by DCVC after two years in stealth. Launched 15 Sep 2026. Vercel said ~13% of paid AI Gateway teams used Jev within 24 h — [The New Stack](https://thenewstack.io/typesafe-jev-system-one/)
- [2nd] TypeSafe's own launch evals:
  - 4 workflows, with reference answers = average of GPT-6 Astra and Fable predictions.
  - Accuracy: Jev 67.8% vs GPT-5.6 Terra 67.9%, Sol 74.1%, Opus 5 73.1%. Latency 0.4 s vs 10.1–37.8 s.
  - "End-to-end latency of 70–500ms"; "no large-scale independent reproduction" at time of writing. The article's 50M-row "$20" cost estimate is arithmetically wrong (≈$20,000 at its own per-case figure).

  — [DataCamp](https://www.datacamp.com/blog/system-one-models-jev)
- [2nd] Almeida said "100% of our data is synthetic". TypeSafe evals ran "from our laptops on the West Coast". TechCrunch suspects open-weight LLM bases. All undisclosed — [AgentConn roundup](https://agentconn.com/blog/jev-typesafe-new-agent-layer-if-calibration-holds)
- [OBS] **No RLCD paper exists.** The Griffith/NTU/UNSW paper says RLCD is "attributed to TypeSafe AI (2026)", with training objective and reward "not stated". The StartLux paper says Jev's training "has not been publicly disclosed". The Harvard paper says weights and recipe "are not public" — [arXiv 2609.29429](https://arxiv.org/pdf/2609.29429); [arXiv 2610.17309](https://arxiv.org/html/2610.17309); [arXiv 2610.17205](https://arxiv.org/html/2610.17205v1)

**Data handling, region, deployment**
- [V][OBS] Privacy Policy:
  - "The Services are hosted in the United States"
  - "We will not train or fine tune any artificial intelligence or machine learning models on your prompts or other Input"
  - retention "as long as reasonably necessary to provide you with the Services"; no specific retention period
  - users outside the US are "transferring your personal data … to the U.S."
  - last updated 19 Nov 2025

  — [TypeSafe Privacy Policy](https://typesafe.ai/legal/privacy-policy)
- [V][OBS] "We also offer zero data retention (ZDR) for enterprise customers" (contact sales). DPA and MCA are linked. No region options, sub-processor list or on-prem offer appear — [docs: Legal](https://docs.typesafe.ai/legal.md)
- [2nd] A third-party model registry lists Jev as US-only, ZDR "not offered" (outside enterprise), and "never on-prem or air-gapped" because weights are closed — [Safeguard](https://safeguard.sh/models/typesafe-jev)
- [S][OBS] Academic users note "the developer states no retention period". The versioned model ID was still accepted on 2026-09-20 — [arXiv 2609.29429](https://arxiv.org/pdf/2609.29429)
- [2nd] OpenRouter: "there are no published weights and no paper" — [OpenRouter](https://openrouter.ai/blog/insights/what-is-jev/)

**Independent and academic tests**
- [S][OBS] Largest academic use (jev-1.13.0, 44 benchmarks, 7,193 instances, alignment-failure detection):
  - Generic yes/no AUROC median 0.886.
  - **Pooled ECE 0.047, but median per-benchmark ECE 0.168** (null 0.074); 24 of 31 benchmarks exceed the null's 95th percentile.
  - Mean probability misses the positive rate by a median 0.125. Median F1-optimal threshold was 0.35, not 0.5.
  - **A threshold fitted on 10 labelled items** raised median F1 from 0.706 (t = 0.5) to 0.793.
  - Keeping the half of decisions with largest |p − 0.5| raised median accuracy from 0.793 to 0.933.
  - Human agreement on StrongREJECT: κ 0.809 vs reference scorer 0.811.
  - Cost $0.30 vs $18.96 for judges.
  - Median latency 0.31 s for 11.4 questions per call.

  — [arXiv 2609.29429](https://arxiv.org/pdf/2609.29429)
- [S][OBS] Social-science annotation (18 tasks, 7,977 items, zero-shot):
  - Jev trails the per-task best LLM on 14 of 15 tasks, median −11.6 macro-F1, at ~44× lower cost.
  - Calibration better than verbalised confidence of 16 of 19 LLMs, but three frontier models were better.
  - Median accuracy at confidence > 0.9 was only **0.815**; on empathy it was confidently near chance.
  - Recommends Jev as a first pass, routing low-confidence items to an LLM ("matches or exceeds the LLM alone at about a quarter to half of its cost").

  — [arXiv 2609.24574](https://arxiv.org/abs/2609.24574)
- [S][OBS] **Option-name sensitivity:** with yes/no-named options, reassigning name↔definition flipped decisions up to 70.4 pp more than a 0/1 control, and dropped mean AUC from 93.8% to 23.2%. Type-error rate stayed 0% throughout: "type-safe is not error-free" — [arXiv 2609.26758](https://arxiv.org/abs/2609.26758)
- [2nd][I-aggregated] Roundup of independent tests to 23 Sep 2026 (re-scored where logs were committed):
  - Jev median ECE 0.157 on social-science tasks beat 16 of 19 LLMs' verbalised confidence. **After one shared temperature was fitted, 15 of those LLMs beat it.**
  - Janardhan: calibration error 0.161, highest among full-distribution models. sanand0 pilot: 0.138 on Banking77.
  - Overconfident on GoEmotions: labels scored 0.80–0.95 matched humans 15% of the time.
  - Refit temperatures across one study ranged 0.65–4.45.
  - **A two-parameter refit cut civil_comments ECE from 0.16–0.21 to < 0.025** on a held-out half; Platt cut crash-narrative ECE 3.35×.
  - 70.4% of Choice probabilities were exactly 0. Noul is clamped to 0.01–0.98.
  - Russian XNLI accuracy 88.3% → 77.3% with ECE tripled.
  - Repeatability: 1.33–2.2% of answers changed between identical passes.

  — [Plain English roundup](https://ai.plainenglish.io/jev-after-eight-days-of-independent-tests-level-with-mid-price-llms-behind-the-frontier-05daa8f21e2e)
- [A] 60-case agent-tool-call benchmark: accuracy 91.7%; ECE (10 bins) 0.071 (jev-latest) and 0.051 (jev-preview); 67% of answers at confidence exactly 1.000; none of the 5 misses at 1.000; p50 latency 378–422 ms from a Portland residential line — [jev-benchmark README](https://raw.githubusercontent.com/themsquared/jev-benchmark/main/README.md)
- [A] r/MachineLearning post citing jevals.com, "calibration gap vs human labels" (method undisclosed): yes/no Jev 5.0 vs Gemini 3.8 Flash 2.0; pick-one 9.8 vs 2.8; rubric 19.7 vs 12.9. Summary: "worse calibrated, better at knowing when it's right" — [Prismix mirror](https://prismix.dev/news/087a26a05b07)
- [A] Community scam-ads benchmark: ECE 0.046, but "at 0.9 confidence it acts on 8 ads and catches 7 of the 53 scams". TF-IDF+LR F1 0.700 vs Jev 0.312 — [AgentConn](https://agentconn.com/blog/jev-typesafe-new-agent-layer-if-calibration-holds)
- [A] OpenRouter author:
  - Same input gave Noul 0.42 then 0.44; rewording raised confidence from 0.44 to 0.95.
  - Recommends thresholds on bands, "calibrate thresholds on a few hundred labeled examples".
  - Context 262,144; "64k tokens per request"; "32k for your state plus any one question".

  — [OpenRouter](https://openrouter.ai/blog/insights/what-is-jev/)
- [A] HN launch thread (item 49717558):
  - Calibration scepticism (elil17: a 0.9 should be right ~900/1000).
  - "privacy by contract, not privacy by design" (hobofan).
  - Architecture guesses (encoder-like with scalar/ordinal heads).
  - ActivePattern asks for accuracy-at-threshold benchmarks.

  — [HN API](https://hn.algolia.com/api/v1/items/49717558)

**Similar decision models from others (vendor-reported unless marked)**
- [V][2nd] **OpenAI Decisions API** (public beta 6 Oct 2026, `gpt-6-luna`):
  - Predicate / Choice / Score; $0.10 per M input tokens; output free; "about 10x faster than the Responses API".
  - ZDR and HIPAA for eligible customers; regional processing in US and Europe only (Australia not mentioned).
  - Advises calibrating thresholds on labelled production examples.

  — [Unite.AI](https://unite.ai/openai-releases-decisions-api-in-public-beta-powered-by-gpt-6-luna)
- [V][2nd] **Cloudflare Clef / Clef-flash** (1 Oct 2026):
  - Post-trained Qwen3.8-27B / Qwen3.5-9B; Apache-2.0 weights on HF; training data not public; "fully Jev compatible".
  - VRAM 85 GB / 41 GB at 64k context single concurrency.
  - Cloudflare-run benchmarks: BANKING77 macro-F1 94.20 vs Jev 79.74; Jev ahead on When2Call and BRIGHT.
  - No calibration figures.

  — [The Register](https://www.theregister.com/a/5300649); [Digital Applied](https://www.digitalapplied.com/blog/open-decision-models-compared-clef-decider-jev)
- [V][2nd] **Perplexity pplx-decider v1.1/v1.2 27B and Flash 4B:**
  - Qwen3.8-27B with **bidirectional (non-causal) attention** and a 255-row decision head replacing `lm_head`; learned temperature applied in `predict`.
  - BF16 ≈ 49–52 GiB (one 80–96 GB GPU); not vLLM-compatible as of writing.
  - Decision Index 0.3: 62.8 vs Jev 60.1.

  — [BestHub](https://www.besthub.dev/articles/perplexity-s-pplx-decider-v1-1-27b-open-weight-decision-model-beats-jev-runs-locally-d08e6d61587a)
- [V][2nd] **Amazon Strands Decider 2B:** Qwen3.5-2B-Base with a pointer head; Apache-2.0 with weights, training data and scripts; ~115 ms on an RTX 3090; Brier trend reported across versions, no ECE — [Digital Applied](https://www.digitalapplied.com/blog/open-decision-models-compared-clef-decider-jev)
- [2nd] JevBench v1.5.4 (106 systems): open-weights Cygnet and Winnow-12B tie at the top (73.7/73.2) above Jev 1.13 (72.1). Calibration sub-index: Jev 88.03, several 4B open models 85–88.6. The composite mixes intelligence, calibration, speed and cost — [BenchLM decision models](https://benchlm.ai/md/decision-models.md)

**How System One / calibrated decision models are trained (papers since Jev)**
- [S][OBS] **"Releasing the Inner Jev" (Harvard, 12 Oct 2026):**
  - Recipe: answer-letter logits at the last token, one forward pass; rank-32 LoRA + decision head; cross-entropy on (soft) targets; 417,825 questions.
  - **"We use no reinforcement learning, reward models, or auxiliary losses"**; calibration by **temperature scaling per question type** fitted on 3,884 held-out questions.
  - Results: trained Gemma 4 31B leads Jev by 4.3 ± 2.5 capability points; ECE 0.047 vs Jev 0.066 over six public sets; zero-shot Qwen3.6-27B already 0.052.
  - Training ~78 min on 4×H200.

  — [arXiv 2610.17205](https://arxiv.org/html/2610.17205v1)
- [S][OBS] **"LLM-as-Jev" (4 Oct 2026):**
  - Any causal LLM is already a Jev-style model: prefill "Best answer: [", score option suffix log-probs, softmax.
  - Training-free Qwen3.5-4B: JevBench-public accuracy 81.4%, ECE 0.057 (raw, no temperature scaling); LoRA 84.0%, ECE 0.050.
  - The 0.6B model is poorly calibrated training-free (ECE 0.278) and improves with fine-tuning (0.118).
  - Fine-tuning gains are "targeted rather than universal".

  — [arXiv 2610.02076](https://arxiv.org/html/2610.02076v2)
- [S][OBS] **UniJev (Fudan/JD, 19 Oct 2026):** SFT improves accuracy, but "existing RLCD algorithms change accuracy little and have inconsistent effects on visual calibration".
  - Their CORA loss trains confidence toward binned empirical accuracy: 2B ECE text 0.055 / image 0.030 / video 0.052.
  - Local RLCD variants: Shaped RLCD image/video 0.099/0.173; RLCD-lite 0.143/0.220; CtR 0.025/0.054.

  — [arXiv 2610.25784](https://arxiv.org/html/2610.25784)
- [S][OBS] **StartLux RLCD² (Oct 2026):**
  - Reward = proper-score improvement from before to after reasoning (decision-weighted proper score; Brier and log ablated), with a length penalty.
  - Calibration error on held-out default answers 3.7 / 2.2 / 1.6 pp at 4B / 9B / 27B.
  - Readout latency 41 ms (4B) to 98 ms (27B) on H200/vLLM.
  - Warns that calibration of individual predictions does not survive best-of-32 selection (80–90% confidence bucket fell from 92% to 78% accurate) and that overconfidence up to 6.1 pp appears under shift.
  - Recommends calibrating "on the outputs of the deployed policy".

  — [arXiv 2610.17309](https://arxiv.org/html/2610.17309)
- [S][OBS] Exact theory (Sudjianto & Burakov, 19 Oct 2026): a student trained on a teacher's soft targets inherits the teacher's bias. "Neither [pretrained representations nor calibration] corrects a biased teacher, so the probabilities have to be checked against realized outcomes." Temperature scaling is the exact recalibration map in their probit model, but leaves an undetectable residual when the teacher's direction is wrong — [arXiv 2610.26797](https://arxiv.org/abs/2610.26797)

### Inferences
- [INF] **Jev cannot be used on member data.** It is US-hosted, has no stated retention period outside enterprise ZDR, and offers no AU region or on-prem. Even ZDR is "privacy by contract". At most it could serve on synthetic or owner-approved non-member data (e.g. BrainBench), or as a *benchmark reference* for local decision models.
- [INF] **The "Jev pattern" is reproducible locally without RL.** Three October 2026 papers show a local instruction-tuned LLM read as a decision model (option logits, one forward pass), optionally LoRA-tuned and temperature-scaled per question type, matches or beats Jev on public sets with similar or lower ECE (0.047–0.057 vs 0.066). This fits the brain's GPU server: 4B models run at ~40 ms per readout on H200-class hardware; 27–31B models need one 80 GB card. R7 owns the hands-on replication.
- [INF] **RLCD is not a necessary ingredient.** Where RLCD-like rewards were reproduced (UniJev, StartLux), they helped calibration inconsistently. Plain cross-entropy plus per-type temperature, or a binned-accuracy loss (CORA), did as well or better. Proper-scoring-rule RL (RLCR, Rewarding Doubt, Q2) matters mainly for models that must *verbalise* confidence after reasoning, which a classifier-style grader does not.
- [INF] **Vendor calibration must be refitted on our labels regardless.** Every independent study found task-dependent miscalibration (per-benchmark ECE 0.14–0.17) that a 1–2 parameter refit fixes. The 10-item threshold result is the practical lower bound; a few hundred labels per decision type is the working number.
- [INF] **Option naming and order are real attack surfaces for every System One model.** Use neutral option names, randomise order, and average over two orderings for any high-stakes decision. This adds a test to E13a.

### Gaps
- No primary TypeSafe source (blog, paper or docs) gives any calibration metric, architecture, parameter count or RLCD objective. The launch blog posts were not fetched directly; content came via docs and secondary write-ups.
- TypeSafe DPA retention terms were not read (linked but not fetched).
- No independent test of Jev on personal-memory or extraction-checking tasks, and none of how its calibration changes between 1.13 and 1.14.
- JevBench and Decision Index protocols differ; numbers across them are not comparable.

---

## Q2. Calibration methods for LLM judges and classifiers (2024–26)

### Takeaway
The measured ranking for our use is clear.
1. **Weakest:** raw verbalised confidence. It is overconfident and bunched near the top (e.g. 86% of predictions above 0.8; Gemini at 100% confidence on up to 73% of cases).
2. **Better:** token/option probabilities, sampled self-consistency, or a small trained probe/classifier.
3. **Best calibrated:** any of these plus a post-hoc fit on a few hundred in-domain labels. Platt/temperature when labels are few; isotonic once there are many.

RL with proper-scoring rewards (RLCR, Rewarding Doubt) fixes verbalised confidence in-domain (ECE 0.37 → 0.03), but transfers only partly out of domain (0.21).

Calibration (ECE) and discrimination (AUROC, error-catch) are different properties. Monotone recalibration cannot improve which errors get caught. Only better signals can, such as grounding/NLI, ensembles of different models, or option-logit readouts.

### Cited Findings

**RL with calibration rewards**
- [S][OBS] **RLCR (MIT, arXiv 2507.16806; ICLR 2026 poster):** reward = correctness + Brier on a verbalised confidence after reasoning; proven to incentivise accuracy and calibration for bounded proper scoring rules. Qwen2.5-7B on HotpotQA:

  | Method | Accuracy | ECE | AUROC | OOD ECE |
  |---|---|---|---|---|
  | RLCR | 62.1% | 0.03 | 0.69 | 0.21 |
  | RLVR | 63.0% | 0.37 | 0.50 | 0.46 |
  | RLVR + BCE classifier | — | 0.07 | 0.66 | 0.24 |

  "RLVR worsens calibration relative to the base model". Unbounded log loss "does not incentivize correctness" — [arXiv 2507.16806](https://arxiv.org/html/2507.16806); [ICLR 2026](https://iclr.cc/virtual/2026/poster/10011036)
- [S][OBS] **Rewarding Doubt (ICLR 2026):** PPO with a clipped log-score betting reward on 0–10 verbalised confidence; Llama-3-8B, LoRA, 4-bit.
  - TriviaQA: ECE 0.0226 / AUROC 0.859 vs verbalised 0.346 / 0.586 and self-consistency 0.113 / 0.821.
  - A trained probe has similar ECE (0.019) but lower AUROC.
  - OOD MedQA ECE 0.115 vs 0.448 verbalised; CommonsenseQA no ECE gain.

  — [arXiv 2503.02623](https://arxiv.org/html/2503.02623v4); [ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/bf8065446507b0d3842838564ac4f1f3-Abstract-Conference.html)
- [S][OBS] **RLSR (ICML 2026 workshop):** RL directly on the area under the risk-coverage curve, for selective prediction and human handoff. No numbers in abstract — [arXiv 2607.03528](https://arxiv.org/abs/2607.03528)

**Verbalised vs sampled vs probability confidence for judges/graders**
- [S][OBS] LLM graders (UCF, 3 datasets of 3.5k–10.8k responses):

  | Method | ECE | Brier |
  |---|---|---|
  | Self-reported | 0.166 | 0.223 |
  | Self-consistency (5 samples) | 0.229 | 0.241 |
  | Token probability | 0.235 | 0.244 |

  - Self-consistency is "38% worse despite 5× inference cost". Best single model: GPT-OSS-120B self-reported, ECE 0.100.
  - **86% of predictions above 0.8.** Coverage at 5% risk only 11.5–19.5%.
  - "Thresholds should be set relative to each model/method's observed scores rather than an intuitive midpoint."

  — [arXiv 2603.29559](https://www.alphaxiv.org/abs/2603.29559.md)
- [S][OBS] Post-2025 proprietary judges: verbalised confidence is now the more robust soft signal vs logprob G-Eval on top GPT releases (18 LLMs, SummEval/AggreFact/HelpSteer2). An overconfidence advisory plus self-debate improves calibration; pre-2025 models pay a balanced-accuracy cost — [arXiv 2609.10996](https://arxiv.org/abs/2609.10996)
- [S][OBS] Protocol sensitivity: across 12 protocol variants (3 × 7–8B models, 4 QA sets), which signal "wins" flips in 4/12 settings under ECE and 9/12 under AUROC. Correct alias vs canonical answer shifts verbalised confidence by 0.072 — [arXiv 2605.27752](https://arxiv.org/abs/2605.27752)
- [S][OBS] Enterprise agents: Gemini reports 100% confidence on up to 73% of cases; AUROC of self-stated confidence 0.563–0.711. Autonomous accuracy and AUROC are uncorrelated (ρ = −0.12). Qualification used a one-sided 95% Clopper-Pearson bound on 375 qualification cases — [arXiv 2609.02095](https://arxiv.org/pdf/2609.02095)
- [S] Overconfidence in LLM judges confirmed. "LLM-as-a-Fuser" ensembles are proposed (abstract only, no numbers obtained) — [arXiv 2508.06225](https://arxiv.org/abs/2508.06225)

**Post-hoc scaling and its limits**
- [S][OBS] Temperature scaling **cannot** calibrate a model whose confidence stays above 0.5 while accuracy falls below it. 8 of 22 model-task pairs (11 models, 0.5–14B) hit that floor. Platt reached ECE as low as 0.02. "Strictly monotone calibration preserves the risk-coverage frontier and error-detection AUROC." A Clopper-Pearson certificate from 200 calibration questions granted autonomy at 20% risk to only 3 pairs, and at 10% to none — [arXiv 2608.05064](https://arxiv.org/abs/2608.05064)
- [S][OBS] Temperature scaling fitted on hard majority labels stays miscalibrated against soft human label distributions (Brier gap mean 0.079 for language); isotonic does not fix it — [arXiv 2607.13423](https://arxiv.org/abs/2607.13423)
- [S][OBS] Judge-score calibration with mean-preserving isotonic regression on **~250 oracle labels (5%)**: naive CIs on uncalibrated scores have "near-0% coverage"; oracle-uncertainty-aware CIs reach ~86–96% — [arXiv 2512.11150](https://fugumt.com/fugumt/paper_check/2512.11150v1)
- [S] Linear probes on judge hidden states, trained with a Brier loss: better calibrated than verbalised or multi-generation, "≈10x computational savings", conservative on easy sets (abstract only) — [arXiv 2512.22245](https://arxiv.org/abs/2512.22245)
- [S] Pinocchio external calibrator for black-box models: AUROC 0.862; a 0.8B text-only checkpoint matches the largest (abstract only) — [arXiv 2609.24881](https://arxiv.org/abs/2609.24881)

**Ensembles**
- [S][OBS] Keep the full judge panel rather than the top-k by accuracy: NLL 0.006 vs 0.013 on RewardBench2. "Do not discard weak judges by accuracy alone; keep them when they are parseable, non-redundant, and calibratable" — [arXiv 2605.09702](https://arxiv.org/abs/2605.09702)
- [S][OBS] Trust or Escalate (ICLR 2025): simulated-annotator ensemble (K = N = 5) halves ECE and raises AUROC 13% vs baselines for GPT-4 — [arXiv 2407.18370](https://arxiv.org/pdf/2407.18370)

**Small fine-tuned classifiers vs LLM judges**
- [S][OBS] Fine-tuned RoBERTa/DeBERTa beat zero-shot GPT-4 / Claude 3 Opus in all four text-classification case studies (sentiment accuracy 0.92 vs 0.87 / 0.86), "especially pronounced for more specialized … tasks" — [arXiv 2406.08660](https://arxiv.org/html/2406.08660v2)
- [S][OBS] MiniCheck-FT5 (770M) reaches GPT-4-level grounding fact-check accuracy at ~400× lower cost, trained on ~14–35k synthetic examples. LLM-AggreFact average balanced accuracy: Bespoke-MiniCheck-7B 77.4%, MiniCheck-FT5 75.3%, GPT-4 74.7% (snapshot of 2024 leaderboard) — [arXiv 2404.10774](https://arxiv.org/html/2404.10774v2); [alphaXiv leaderboard](https://www.alphaxiv.org/benchmarks/the-university-of-texas-at-austin/llm-aggrefact)
- [A] Community baselines: logistic regression on embeddings at ~95% with 50–100 examples (HN). A 310M encoder trained on 200 rows beat Jev 88.8% vs 76.8% on Japanese news topics — [AgentConn](https://agentconn.com/blog/jev-typesafe-new-agent-layer-if-calibration-holds); [Plain English roundup](https://ai.plainenglish.io/jev-after-eight-days-of-independent-tests-level-with-mid-price-llms-behind-the-frontier-05daa8f21e2e)

**Error-catch (selecting items for review)**
- [S][OBS] Choosing the lowest-confidence 20% of classifications for human review (individual verbalised confidence) beat random for GPT-4o, GPT-4o-mini and Llama-3.1-8B in most events (e.g. effective accuracy 0.87 vs 0.73). Asking the model to pick the check set from a list was unreliable — [ACL Findings 2025](https://aclanthology.org/2025.findings-acl.836.pdf)
- [S][OBS] (from R3, carried for completeness) Span alignment + NLI flags 85.7% of unsupported extractions at 92.8% precision (SafePassage). Humans catch rule/semantic errors only ~31% of the time — see r3 notes; [SafePassage](https://arxiv.org/html/2510.00276v1); [arXiv 2509.08514](https://arxiv.org/html/2509.08514v1)

### Inferences
- [INF] **The grader should be classifier-style, not verbalised.** Read option logits from a local LLM (Harvard / LLM-as-Jev recipe), or use a small trained head or encoder. Then fit temperature/Platt per decision type on our labels; move to isotonic or binned once a type has ≥1,000 labels. Verbalised confidence becomes at most one feature among several.
- [INF] **Separate the two goals in E13a.** Calibration (ECE, Brier, reliability per decision type) decides whether probabilities can drive conformal sets and queue thresholds. Error-catch (AUROC, recall of seeded errors at a fixed review budget) decides whether the queue finds mistakes. Recalibration only moves the first, so E13a must report both.
- [INF] **Diversity buys discrimination.** Combine signals that fail differently: grounding/NLI vs source span, an option-logit decision from a *different model family* than the extractor, and ordering-swapped repeats. Stack them with a logistic layer (the "conformal alignment" predictor in Q3 used exactly this: logistic regression on self-eval, lexical similarity, entailment and semantic-entropy features).

### Gaps
- Few studies report ECE for *field-level extraction* on open 4–70B models on conversational text. Our numbers must come from BrainBench seeded errors.
- No head-to-head of option-logit local decision models vs a fine-tuned 300M–800M encoder on the same grading task with matched label budgets.
- RLCR numbers for the Big-Math setting and the confidence-weighted voting section were truncated in the fetched page.

---

## Q3. Learning from outcomes: online calibration, active review, deferral with guarantees, biased feedback, drift

### Takeaway
A self-learning grader is feasible and well-supported statistically, under one condition: **the labels it learns from must be partly random, not only the items the system chose to show a human.**
- Feedback from reviewers who habituate, and from the system's own routing, is biased. It is selective (labels exist only for flagged or shown items) and drifts with fatigue.
- The literature's answer:
  1. Keep a small, **randomly sampled audit stream** with known inclusion probabilities.
  2. Seed known errors to measure reviewer catch rate.
  3. Correct estimates with inverse-probability weighting or prediction-powered inference.
  4. Certify thresholds with Learn-then-Test / Clopper-Pearson.
  5. Recalibrate online (ACI / online Platt) while a conformal test martingale watches for exchangeability breaks.

### Cited Findings

**Selective prediction / learning to defer with guarantees**
- [S][OBS] **Trust or Escalate (ICLR 2025):** fixed-sequence testing over thresholds gives P(human agreement on non-abstained ≥ 1 − α) ≥ 1 − δ.
  - Calibration sets: 500 (TL;DR, ChatArena), 392 (Auto-J).
  - TL;DR at target 0.9: 55.7% coverage, guarantee held in 90.8% of 1,000 splits.
  - ChatArena at 0.8: 79.1% coverage. Auto-J at 0.8: 42.6%.
  - Cascades cut cost up to 78.5–87.4% vs GPT-4 alone.

  — [arXiv 2407.18370](https://arxiv.org/pdf/2407.18370)
- [S][OBS] **Conformal Alignment (NeurIPS 2024):** train a lightweight alignment predictor (logistic regression on features such as Self_Eval, lexical similarity, entailment-graph degree/eccentricity, semantic entropy). Select outputs by conformal p-values + Benjamini–Hochberg, which gives **FDR ≤ α** among auto-accepted outputs, finite-sample, any model.
  - "a few hundred high-quality samples suffice"; |D| = 500 suffices for radiology.
  - LLaMA-2-13B on TriviaQA: power up to 0.50 at FDR 0.05.
  - Thresholding Self_Eval at 1 − α does *not* control FDR.

  — [arXiv 2405.10301](https://arxiv.org/html/2405.10301v3); [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/870ccde24673d3970a680bb48496ed63-Abstract.html)
- [S][OBS] Selective Conformal Risk Control: first select confident items, then run CRC on the selected subset. Transductive variant exact; inductive variant PAC via a DKW bound. Feasibility needs m ≥ ⌈1/α⌉ − 1 selected calibration points — [arXiv 2512.12844](https://arxiv.org/pdf/2512.12844v1)
- [S][OBS] Clinical EHR extraction (10k visits, 898 practices): LLM extraction + LLM-judge verification + calibration + conformal acceptance, so that "the future expected proportion of accepted but incorrect extractions remains below a pre-specified risk level". Numbers are not in the abstract — [AAAI-SS 2025](https://ojs.aaai.org/index.php/AAAI-SS/article/view/36929)
- [S][OBS] Learn then Test: risk control as multiple hypothesis testing, which handles non-monotone risks and high-probability guarantees. It underlies Trust or Escalate and MAPIE's precision control — [arXiv 2110.01052](https://arxiv.org/abs/2110.01052)

**Active labelling and correcting biased / noisy labels**
- [S][OBS] **Active statistical inference** (Zrnic & Candès, ICML 2024): label where the model is uncertain, rely on predictions elsewhere, and keep valid CIs via inverse-probability weighting. Robust version (NeurIPS 2025) interpolates toward uniform sampling so the estimator "is never worse than … uniform sampling" when uncertainty is miscalibrated — [arXiv 2403.03208](https://arxiv.org/abs/2403.03208v2); [arXiv 2511.08991](https://arxiv.org/html/2511.08991v1)
- [S][OBS] Prediction-powered inference: valid CIs combining a small labelled set with many model predictions — [arXiv 2301.09633](https://arxiv.org/abs/2301.09633)
- [S][OBS] **Correcting an LLM judge's pass rate** with sensitivity/specificity from a human calibration set (Rogan–Gladen):
  - "an interval shorter than 0.1 requires m ≈ 200 calibration examples" (example q0 = 0.7, q1 = 0.9).
  - Pilot 10 per label type, then allocate the budget by error ratio.
  - Coverage 96–99% on Chatbot Arena.

  — [arXiv 2511.21140](https://arxiv.org/pdf/2511.21140)
- [S] PPI-style estimators can have strictly smaller variance than measurement-error correction under stated conditions — [arXiv 2601.05420](https://arxiv.org/abs/2601.05420)
- [S][OBS] **Label noise and conformal:** with *dispersive* noise, conformal and risk-controlling methods stay conservative w.r.t. clean labels. Adversarial noise needs an explicit bounded-noise correction (extends to false-negative-proportion losses) — [JMLR 2024](https://www.jmlr.org/beta/papers/v25/23-1549.html)
- [S] Corrupted-label conformal via uncertain imputation and robust re-weighting — [arXiv 2505.04733](https://arxiv.org/html/2505.04733v1)

**Reviewer habituation (the bias in human feedback)**
- [S][OBS] Code review of AI-agent PRs: 400 repeat reviewers, 11,429 reviews over 7 months.
  - Approval rose 30.1% → 36.8%; +14.5 pp from first to tenth experience decile.
  - Inline comments fell 22%; latency rose 3.5×.
  - Persists after controlling for calendar time: "reflexive habituation under growing workload". No mitigations tested.

  — [arXiv 2606.22721](https://arxiv.org/abs/2606.22721)
- [S][OBS] Prevalence effect: when targets are rare, people miss them about twice as often (≈18% misses at 50% prevalence, roughly doubling at low prevalence). Sensitivity (d′) is unchanged; the decision criterion shifts. Telling people about the effect did nothing — [Psychonomic Society](https://featuredcontent.psychonomic.org/misses-are-up-when-item-occurrence-is-down/)
- [OBS] Airport screening uses Threat Image Projection (synthetic threats inserted into live X-ray streams) both to measure individual screener detection and to raise effective prevalence — [WIT Press 2005](https://doi.org/10.2495/SAFE050411); [CASRA newsletter](https://casra.ch/wp-content/uploads/2023/07/Science_Security_CASRA_Newsletter19_July2018.pdf)

**Online recalibration and drift**
- [S][OBS] ACI: α_{t+1} = α_t + γ(α − err_t), with long-run coverage under arbitrary shift. DtACI tunes γ online, with small regret over local windows — [Gibbs & Candès NeurIPS 2021](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html); [arXiv 2208.08401](https://arxiv.org/html/2208.08401v3)
- [S][OBS] ACI under delayed feedback: a finite-sample long-run coverage bound with explicit dependence on delay τ; the diagnostic r = τ/L (delay vs memory of the drift) organises performance — [arXiv 2609.07251](https://arxiv.org/abs/2609.07251)
- [S][OBS] **Semi-bandit feedback** (label seen only if it was in the returned set: "a user would only be able to provide the true label if the target document is in the prediction set"). Õ(√T) regret and PAC-style coverage. Motivated by RAG retrieval — [arXiv 2405.13268](https://arxiv.org/html/2405.13268v3). The adversarial version links long-run coverage to regret — [arXiv 2604.17984](https://arxiv.org/abs/2604.17984)
- [S][OBS] Online Platt Scaling (+calibeating) adapts between i.i.d. and drifting data and stays calibrated even for adversarial sequences — [arXiv 2305.00070](https://arxiv.org/abs/2305.00070)
- [S][OBS] Weighted conformal under drift: weights w_i (e.g. fixed window or 0.99^(n−i+1)) with coverage ≥ 1 − α − 2Σ w̃_i ε_i, where the effective sample size (Σw)²/Σw² governs variance — [Angelopoulos & Bates, Gentle Intro](https://arxiv.org/pdf/2107.07511); [Barber et al., Beyond Exchangeability](https://arxiv.org/abs/2202.13415)
- [S][OBS] WATCH: weighted conformal test martingales that adapt to mild covariate shift and raise alarms on harmful (concept or out-of-support) shifts, with false-alarm control — [arXiv 2505.04608](https://arxiv.org/abs/2505.04608)
- [OBS] Libraries ship martingale exchangeability tests: `crepes.martingales` (crepes 0.9.1, 12 Jun 2026) and a MAPIE example for online martingale tests of a deployed classifier — [crepes PyPI](https://pypi.org/project/crepes/); [MAPIE example](https://mapie.readthedocs.io/en/stable/examples_exchangeability_testing/2-advanced-analysis/plot_online_martingale_tests_for_deployed_classification_model.html)
- [S][OBS] Requalification rules: changing the agent, environment or task population requires re-execution and requalification. Changing policy after seeing qualification results requires a fresh held-out set — [arXiv 2609.02095](https://arxiv.org/pdf/2609.02095)

### Inferences
- [INF] **Design for U7 (self-learning grader), per partition.** There are four label streams, weighted by trust:
  - **(a) Random audit:** ~2–5% of auto-accepted items, inclusion probability logged. Unbiased; used for certification and the IPW/PPI estimators.
  - **(b) Seeded errors:** synthetic wrong values and missing vital items injected into review queues at a known rate (Threat-Image-Projection style), to measure each reviewer's catch rate and raise effective prevalence.
  - **(c) Uncertainty-sampled review:** active stream; IPW-weighted when used for estimates.
  - **(d) Implicit outcomes:** rephrased search, correction, "that's wrong". Treat these as noisy features, never as certification labels.
- [INF] **Reviewer labels pass through the reviewer's measured catch rate.** If seeded-error catch falls (week 1 vs week 4), down-weight that reviewer's "accept" labels or Rogan–Gladen-correct the estimated error rate. This makes the 31% catch rate a *measured parameter* rather than a silent bias.
- [INF] **Retraining cadence.** Refit the calibration layer (Platt/temperature per decision type) nightly from (a)+(c) with IPW. Retrain the underlying head or LoRA only when a type has ≥1,000 new labels *and* the martingale or ACI miss-rate shows drift. Each retrain triggers requalification on a fresh audit slice before thresholds go live.
- [INF] **Trained models stay inside partitions.** The per-partition calibration layer is cheap: a few parameters per decision type. A *shared* base decision model trained only on synthetic or owner-approved data is fine; partition-specific LoRA or heads and calibration maps are trained only on that partition's labels. Too-small partitions fall back to the shared calibration (the clustered / "null cluster" logic in Q4).

### Gaps
- No study measures how fast reviewer catch-rate decays over months in a *personal memory* setting, or whether seeded errors restore vigilance in LLM-assisted review (TIP evidence is from X-ray screening).
- No study evaluates conformal guarantees using labels from habituating reviewers specifically.

---

## Q4. Conformal prediction for retrieval and RAG: certified recall

### Takeaway
Conformal methods can certify retrieval sets, but **almost all published retrieval guarantees are the weaker kinds:**
- "at least one relevant item" (score-refinement, TRAQ, CAS);
- "expected fraction of relevant items retained" / FNR (CRC, ConRAD, two-stage risk control, the NeuCLIR/RAGTIME filter).

The brain's standard is the **all-vital-items** event per task. It *can* be certified directly: define the per-task score as the rank (or score threshold) of the *worst-ranked* vital item and take its conformal quantile. Guarantees are always marginal per class, never per request, and assume exchangeability.

Set sizes can be large for hard classes. Published refined-score sets were 1–347 items depending on dataset and α.

In BrainBench (sandbox block below), easy classes certify at small K: 1–30 items with cards/neighbourhoods. Goal tracking needs ≈72. Four complex classes cannot be certified at any K ≤ 400 with the current retriever.

This **supports DA2's two-budget design** (a certified recall set, then a reader), and shows conformal can only certify recall the upstream structure already reaches.

### Cited Findings

**Core theory**
- [S][OBS] **Conformal Risk Control (ICLR 2024):**
  - Guarantee: E[L(C_λ̂)] ≤ α for any bounded, monotone loss.
  - λ̂ = smallest λ with (n/(n+1)) R̂_n(λ) + B/(n+1) ≤ α.
  - Lower bound α − 2B/(n+1).
  - Under shift, the upper bound degrades to α + B·ΣTV.
  - MS COCO multilabel FNR at α = 0.1, n = 4,000: mean risk 0.0996.
  - It is "a guarantee in expectation versus a guarantee in probability" (RCPS/LTT give the latter).

  — [ICLR 2024 paper](https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf)
- [S][OBS] **Calibration-set randomness:** coverage conditional on the calibration set ~ Beta(n + 1 − l, l) with l = ⌊(n + 1)α⌋. "With n = 1000 … coverage typically between .88 and .92". Table: n(ε) = 22 / 102 / 2,491 for slack ε = 0.1 / 0.05 / 0.01 (δ = α = 0.1). Mondrian/group-balanced conformal: one quantile per group. Size-stratified coverage is a diagnostic for conditional failure — [Gentle Intro](https://arxiv.org/pdf/2107.07511)
- [S][OBS] **Multilabel "contains ALL true labels":** Cauchois, Gupta & Duchi (JMLR 2021) give inner/outer sets containing the full true label configuration with probability ≥ 1 − α (union bound otherwise gives only 1 − Kα). Sets can blow up when labels "repel each other"; tree-structured scores keep them near oracle size — [JMLR 2021](https://jmlr.org/papers/v22/20-753.html); [arXiv 2004.10181](https://arxiv.org/pdf/2004.10181v3)
- [S][OBS] **Mondrian (class-conditional) with few examples:**
  - Any group with fewer than 1/α − 1 calibration examples (9 at α = 0.1) gets an infinite threshold (return everything).
  - Clustered conformal pools similar groups. It wins at ~20–75 examples per group; classwise is fine once the rarest group has ~100+.
  - ImageNet, n_avg = 10: classwise set size 354 vs clustered 2.5.

  — [Ding et al., NeurIPS 2023](https://www.stat.berkeley.edu/~ryantibs/papers/classconf.pdf)

**Retrieval-specific conformal**
- [S][OBS] **Score-refinement conformal IR (FEVER workshop 2024):** guarantee is ≥ 1 relevant document ("uses the highest-scoring relevant one"). Average set sizes (baseline → refined, BGE-large):

  | Dataset | α | Baseline | Refined | Coverage |
  |---|---|---|---|---|
  | FEVER | 0.05 | 9.47 | 1.67 | 0.93 |
  | SCIFACT | 0.05 | 760.75 | 29.59 | — |
  | FIQA | 0.03 | 1,206.93 | 347.16 | — |

  Refinement coverage was slightly *below* target in several cases. "Our method does not handle cases where no relevant information exists" — [arXiv 2410.02914](https://arxiv.org/html/2410.02914v1)
- [S][OBS] **Two-stage risk control for ranked retrieval:** retrieval loss = missed fraction of relevant docs, then nDCG-style ranking loss, via LTT/CRC. At α1 = α2 = 0.1, final set sizes ~68–77 (MSLR-Web) and ~28–29 (Yahoo LTR); recall (rel ≥ 2) 0.93–0.96 — [arXiv 2404.17769](https://arxiv.org/pdf/2404.17769)
- [S][OBS] **ConRAD (neural graph databases, 2026):**
  - CRC on per-query FNR through multi-hop query DAGs; "marginal guarantees" on average recall.
  - Calibration 2,000 queries; ground-truth sets capped at 50.
  - Worst downward deviation from target 0.046.
  - "Achieving strict conditional (per-query) coverage is impossible without restrictive assumptions."

  — [arXiv 2605.03806](https://arxiv.org/pdf/2605.03806)
- [S][OBS] **Conformal context filtering for RAG (Nov 2025):** guarantee per *snippet* ("a labeled-relevant snippet is retained with probability ≥ 1 − α"), not per query; labels from Llama-3.3-70B with 10% manual check. Calibration 1,440–1,710 snippets. 2–3× context reduction (e.g. Conformal-LLM removes 46–70% at α ≤ 0.2) with stable or better ARGUE F1 — [arXiv 2511.17908](https://arxiv.org/html/2511.17908)
- [S][OBS] **TRAQ (NAACL 2024):** conformal on the retriever (relevant passage in set w.p. ≥ 1 − α_Ret) and on generator clusters, combined by Bonferroni. Calibration 300, optimisation 300, test 400 per dataset; Bayesian optimisation of the α split shrinks sets by 16.2% — [NAACL 2024](https://aclanthology.org/2024.naacl-long.210.pdf)
- [S][OBS] **CAS (Aug 2026):** APS-style adaptive retrieval sets capped at 1–5 docs; ~3.4 docs at α = 0.2 and 4.8 at α = 0.05; calibration 239 queries. Multi-hop calibrated per hop; "primarily focuses on outcome reliability" — [arXiv 2608.20771](https://www.alphaxiv.org/abs/2608.20771.md)
- [S][OBS] **C-RAG (ICML 2024):** certifies an upper bound on *generation risk* with probability 1 − δ, under exchangeability plus strong simplifying assumptions (one-layer transformer). It does **not** guarantee that all needed documents are retrieved — [arXiv 2402.03181](https://arxiv.org/html/2402.03181v4)
- [S][OBS] **PASC (May 2026):** joint coverage across K pipeline stages via the max of per-stage scores with one quantile, P(all stages covered) ≥ 1 − α. NER→NED→typing, α = 0.1, n = 1,000: end-to-end coverage 0.964 vs Bonferroni 0.934 vs independent 0.865. At n = 200 Bonferroni was better (0.964 vs 0.934). Single-author preprint — [arXiv 2605.18812](https://arxiv.org/pdf/2605.18812)
- [S] DCR (full-ranking conformal, Jan 2026): exact non-conformity distribution via negative hypergeometric ranks; up to 36% smaller sets (abstract only) — [arXiv 2601.23128](https://arxiv.org/abs/2601.23128v1)

**Exchangeability and what breaks it**
- [S][OBS] Even short-range temporal dependence strongly violates exchangeability. Split conformal still works well for stationary β-mixing series, with loss bounded by a "switch coefficient" — [arXiv 2510.02471](https://www.arxiv.org/abs/2510.02471)
- [S][OBS] Covariate-shift weighting restores CRC control when likelihood ratios are known or estimated — [ICLR 2024 CRC](https://proceedings.iclr.cc/paper_files/paper/2024/file/f3549ef9b5ff520a7e41ff3cc306ab2b-Paper-Conference.pdf)

**Libraries**
- [OBS] **MAPIE 1.6.0** (19 Oct 2026, BSD-3, Python ≥ 3.10). `MultiLabelClassificationController(risk='recall'|'precision', method='crc'|'rcps'|'ltt', target_level, confidence_level)`; recall defaults to CRC, precision requires LTT; supports batched `compute_risks` — [PyPI](https://pypi.org/project/MAPIE/); [docs](https://mapie.readthedocs.io/en/stable/generated/mapie.risk_control.MultiLabelClassificationController.html)
- [OBS] **crepes 0.9.1** (12 Jun 2026, BSD-3): conformal classifiers, regressors and predictive systems; Mondrian via `MondrianCategorizer`; conformal test martingales — [PyPI](https://pypi.org/project/crepes/)
- [OBS] **TorchCP** (JMLR 2025, LGPL-3.0): GPU batch CP for DNNs, GNNs and LLMs; online CP; "up to 90% reduction in inference time on large datasets" — [JMLR](https://www.jmlr.org/beta/papers/v26/24-2141.html)
- [OBS] **conditional-conformal** (Cherian, Gibbs & Candès; PyPI): conditional / level-adaptive conformal — [arXiv 2406.09714](https://arxiv.org/html/2406.09714v2)
- [INF] Compute cost is negligible. Calibration is a sort or quantile over n scores per class (PASC calibration 0.17 ms). The real cost is labelled calibration tasks and per-candidate scores (reranker or decision-model calls).

#### Sandbox check on BrainBench v0.2 (this round)
[OBS] **What was run.** E13b-lite on BrainBench v0.2's existing retrieval (bge-small, wsum fusion over the card index; the same arms as DA2 A7).
- **Arms:**
  - **query**: search only.
  - **nbhd**: cards + slots + entity-tagged neighbourhood, then search.
- **Per task:** r = the smallest K such that *every* vital item is in the top K (cards cover their items). Rankings were capped at 400 items; tasks needing more count as unreachable (r = ∞).
- **Splits:** calibration/test by distinct required set (50/50), one task per set in calibration, 200 random splits, α = 0.10. Coverage is set-weighted.
- **Cross-seed:** calibrate on all of seed 1, test on seeds 2 and 3.
- **Methods compared:**
  - **(a)** split conformal on r (fixed K̂ per class), the all-items guarantee;
  - **(b)** CRC on the FNR/recall loss;
  - **(c)** adaptive per-request sets: threshold on the normalised score gap of the worst vital item, set = all items within that gap (query arm, cards not counted).
- **Files:** script and summaries in `/home/claude/research_notes/Weak spots frontier round/r6_sandbox/` (`r6_conformal.py`, `summary.json`). Seeds s1 to s3 have 2,207 / 2,164 / 2,145 tasks.

**Results.** Means over 200 splits, [5th–95th percentile] in brackets. "inf" means K̂ = ∞ because more than 10% of calibration sets have a vital item that is unreachable within 400.

| Class (distinct sets, s1) | Unreachable@400 (query / nbhd) | Conformal K̂, query (test cov) | Conformal K̂, nbhd (test cov, ≈tokens) | CRC on recall: K (mean recall / all-items rate) | Adaptive gap sets: cov, mean size | Cross-seed nbhd: K̂ → cov s2 / s3 |
|---|---|---|---|---|---|---|
| current_state (554) | 0.01 / 0.01 | 26 [15–46] (0.903) | 1 (0.924, ≈59) | 26 (0.903 / 0.903) | 0.903, 353 | K̂=1 → 0.923 / 0.918 |
| temporal_change (424) | 0.06 / 0.05 | 61 [35–121] (0.903) | 30 [24–42] (0.904, ≈555) | 23 (**0.911 / 0.842**) | 0.902, 79 | K̂=28 → 0.901 / 0.903 |
| multimodal (129) | 0.00 / 0.00 | 35 [14–60] (0.911) | 22 [14–33] (0.909, ≈420) | 19 (0.883 / 0.877) | 0.906, 27 | K̂=18 → **0.884** / 0.907 |
| goal_tracking (144) | 0.25 / 0.04 | inf | 72 [39–129] (0.908, ≈843) | 203 (**0.906 / 0.702**) | 0.907, 1,442 | K̂=45 → 0.920 / 0.925 |
| option_analysis (129) | 0.39 / 0.10 | inf | finite in only 36/200 splits; when finite 582 [150–1,062] (≈4,100 tokens) | inf | 0.903, 1,804 | inf |
| decision_support (162) | 0.66 / 0.24 | inf | inf | inf | 0.908, 1,974 | inf |
| preference_recommendation (140) | 0.54 / 0.41 | inf | inf | inf | 0.901, 1,492 | inf |
| cross_domain (138) | 0.66 / 0.38 | inf | inf | inf | 0.907, 2,000 (whole visible corpus) | inf |

**Readings (OBS from this run; INF where marked):**
1. **Coverage is valid where finite.** Split-conformal K̂ hit 0.903–0.924 mean test coverage on every class with a finite threshold. The 5th percentile across splits fell to ~0.83–0.87 for classes with 129–162 sets: the Beta-law spread at this n.
2. **Cross-seed transfer held** for current_state, temporal_change and goal_tracking (0.901–0.925). Multimodal on s2 dipped to 0.884: one draw below target, consistent with n = 129.
3. **CRC on recall is not the all-items standard.** Where per-task need is multi-item, CRC hit its *recall* target but the share of tasks with *every* vital item was far lower: temporal 0.842, goal **0.702**. It matches only when sets are size-1 (current_state).
4. **Structure shrinks certified sets a lot.**
   - nbhd vs query K̂: current_state 26 → 1; temporal 61 → 30; multimodal 35 → 22.
   - goal_tracking goes from uncertifiable (query) to K̂ ≈ 72 (≈840 synthetic tokens).
5. **Four complex classes cannot be certified at 90% by any K ≤ 400** with this retriever: decision_support, preference, cross_domain, and option_analysis in most splits. 24–41% of their sets have a vital item that never reaches the top 400 even in the nbhd arm.
6. **The adaptive score-gap version (query arm only) has valid coverage but is useless for hard classes.** Mean set sizes of 1,400–2,000 items mean "return almost everything". It shines only on easy classes (multimodal mean 27, temporal 79).
7. [INF] Conformal certifies whatever the upstream retriever achieves; it cannot create recall. The classes where certification fails are the same ones where DA2 A7 found the K = 50–200 ceiling below 90%. The certified-recall plan therefore depends on the structural fixes (entity linking, cards, neighbourhoods) making the worst vital item reachable.
8. **Threats to validity.**
   - Synthetic short items (≈15–20 tokens each), so token figures understate real sizes 20–50×.
   - One retriever (bge-small), seeds generated by one generator.
   - The rank cap at 400 makes "inf" a lower bound on the needed K.
   - Calibration and test sets come from the same generator, so exchangeability holds by construction, which real use will not give.
   - Seeds are separate generated worlds. 275–398 set-ID hashes collide across seeds because item IDs are reused, but they point at different worlds' items.

### Inferences
- [INF] **I15 is valid in a specific form.**
  - Per class c, score each calibration task by r = the rank (or the worst normalised score gap) of its *least-retrievable* vital item. Take K̂_c = the ⌈(n_c + 1)(1 − α)⌉-th smallest r.
  - This gives P(all vital items in top K̂_c) ≥ 0.90, marginal over tasks of class c, under exchangeability. It is the split-conformal guarantee on a max-type score (same reduction as PASC and Cauchois et al.).
  - **CRC on recall/FNR is the wrong tool for the standard.** It controls *expected recall*, which can be 90% while far fewer than 90% of tasks get *every* item (shown in the sandbox block).
- [INF] **One-shot certificate vs statistical guarantee.** Conformal gives *expected* coverage over calibration draws. A single calibration of n = 150 sets lands below 90% about half the time (Beta law; at n = 200, P(cov ≥ 0.90) ≈ 0.53). For a *certificate*, use the PAC/RCPS version (target α_eff ≈ 0.065 at n = 200 or 0.078 at n = 500 for 95% confidence), or report a one-sided Clopper-Pearson bound on held-out tasks, as the protocol requires. Zero failures in 29 held-out sets already certifies ≥ 90% at 95%. With failures, 300 sets at 93% observed gives a lower bound ≈ 0.901. [computed, OBS]
- [INF] **Per class (Mondrian) is mandatory; n per class is the bottleneck.** Each class needs ≥ 9 calibration sets just for a finite threshold at α = 0.1, roughly 100+ distinct required sets for a stable one, and 300–500 for a tight certificate. Rare classes, new partitions and new users fall back to a pooled or clustered threshold, flagged "uncertified".
- [INF] **Exchangeability breaks in a personal memory system in predictable ways.**
  1. Corpus growth: ranks inflate as items accumulate, so a fixed K̂ loses coverage. Use a *score-gap* nonconformity score, not raw rank, and recalibrate on a rolling window.
  2. Query-mix drift (new projects, seasons).
  3. Model or index changes. Every embedder, reranker or prompt change invalidates the calibration and needs requalification.
  4. Feedback loops: the system only learns about items it showed (semi-bandit).
  5. Temporal dependence within sessions.
  6. Per-user non-exchangeability across partitions.

  Mitigations: rolling or weighted calibration, ACI on the miss indicator from audits, a martingale alarm, and calibration labels from random audits rather than shown items.
- [INF] **Where the set gets its labels.** Calibration needs tasks whose *full* vital set is known. Sources: the BrainBench-style gold set per class, a random audit where a reviewer marks missing vital items (the only way to see omissions), and seeded tasks with planted vital items. Implicit feedback cannot provide the "all items" label.
- [INF] **Revised I15 test and kill criteria.** The test is E13b at full scale:
  - per class, split-conformal K̂ on the worst-vital-item score;
  - calibration and certification splits each ≥ 300 distinct sets;
  - report realised coverage with a one-sided Clopper-Pearson bound and K̂ in tokens.

  Kill I15 for a class if either holds:
  - its certified K̂ (tokens) exceeds the reader's budget after the structural fixes;
  - coverage on a later-time or other-seed split falls > 2 pp below target.

  Keep CRC-on-recall only as a secondary diagnostic, never as the standard.
- [INF] **Two budgets reconcile the guarantee with the context limit (DA2 I-1).** Certify the *recall set* (K̂_c items or tokens) with conformal, then let a reader or listwise selector choose the working set. Report two numbers per class: certified recall-set coverage, and end-to-end task success with the reader. If K̂_c exceeds the reader's token budget for a class, that class needs better upstream structure (cards, entity neighbourhoods), not a bigger set.

### Gaps
- No published method certifies *all-required-items* coverage for retrieval in a memory/RAG system with real data. The max-score reduction is standard theory (PASC, Cauchois) applied here by inference.
- No paper evaluates conformal retrieval under corpus *growth* over months.
- Set sizes for real personal-memory corpora are unknown. BrainBench items are 20–50× shorter than real ones (DA2).

---

## Q5. Conformal and calibrated checks for extraction (claims, value-vs-source)

### Takeaway
Two mature families apply to the write gate:
- **(1) Conformal factuality / claim filtering.** Split the output into sub-claims, score each, drop those below a calibrated threshold, and guarantee that all retained claims are correct with probability ≥ 1 − α.
- **(2) Calibrated grounding checkers** (MiniCheck, HHEM, LettuceDetect, NLI cross-encoders) that score "is this value supported by this source span".

The known failure is utility. Marginal guarantees with weak scores remove most content: 86.8% removal for LLM-confidence scores vs 8.9% for retrieval-grounded scores at the same 85% target; multi-hop retains only 4–31% of claims. Better scores (grounding, learned combinations) and conditional / level-adaptive conformal are the fixes.

Conformal FDR control (Conformal Alignment) is the right shape for "auto-accept extracted records with ≤ α wrong among the accepted".

### Cited Findings
- [S][OBS] **Conformal factuality (Mohri & Hashimoto, ICML 2024):** back-off by removing least-confident sub-claims; threshold = conformal quantile; P(output entailed by truth) ≥ 1 − α under exchangeability. FActScore 30% → 80%, NQ 78% → 93%, MATH 75% → 95% factuality — [arXiv 2402.10978](https://arxiv.org/html/2402.10978v1); [PMLR](https://proceedings.mlr.press/v235/mohri24a.html)
- [S][OBS] **Enhanced conformal (Cherian, Gibbs & Candès, NeurIPS 2024):** Mohri–Hashimoto removes too much because guarantees are marginal and scores weakly correlated. Two fixes:
  - Level-adaptive CP: issue a per-prompt probability while keeping ≥ 70% of claims.
  - Conditional boosting: learn the scoring function by differentiating through the cutoff.

  MedLFQA retention 39% boosted vs 24% unboosted; calibration 2,354 points. Package `conditional-conformal` — [arXiv 2406.09714](https://arxiv.org/html/2406.09714v2)
- [S][OBS] **Conformal-RAG (SIGIR 2025):** sub-claim score = max over retrieved docs of cos(query, doc) × cos(claim, doc); Mondrian (group-conditional) calibration. At 85% target on FActScore it removes 8.9% of sub-claims vs **86.8%** for LLM-confidence scoring; "retains up to 60% more" claims. Guarantee depends on correct GPT-4o annotation of calibration claims — [arXiv 2506.20978](https://arxiv.org/html/2506.20978v1)
- [S][OBS] **Multi-hop conformal factuality (Sep 2026):** at 95% target, fully supported responses 95.8–97.2% (vs 55.6–76.0% unfiltered), but claim retention only 4.41–31.09% and non-empty responses 9.7–51.4% — [arXiv 2609.38222](https://arxiv.org/abs/2609.38222)
- [S][OBS] Conformal Language Modeling: sample until a calibrated stopping rule, reject low-quality samples, then identify component phrases that are each correct with guarantees — [arXiv 2306.10193](https://arxiv.org/abs/2306.10193)
- [S][OBS] Clinical extraction with conformal acceptance bounding the expected share of accepted-but-wrong extractions — [AAAI-SS 2025](https://ojs.aaai.org/index.php/AAAI-SS/article/view/36929)
- [S][OBS] PASC applies one joint conformal quantile across an NER → entity-disambiguation → typing pipeline, a close analogue of extract → link → type in the write gate. End-to-end coverage 0.964 at α = 0.1 (n = 1,000). Under shift (WNUT/WikiNEuRal) coverage stayed 1.000 for joint methods vs 0.59–0.65 independent — [arXiv 2605.18812](https://arxiv.org/pdf/2605.18812)
- [S][OBS] Local grounding checkers:
  - MiniCheck-FT5 770M ≈ GPT-4 on LLM-AggreFact (75.3% vs 74.7% BAcc); Bespoke-MiniCheck-7B 77.4% — [arXiv 2404.10774](https://arxiv.org/html/2404.10774v2); [leaderboard](https://www.alphaxiv.org/benchmarks/the-university-of-texas-at-austin/llm-aggrefact)
  - HHEM-2.1-open: < 1.5 s on CPU for 2k tokens, runs on RTX-3080-class GPUs (vendor) — [Vectara](https://www.vectara.com/blog/hhem-2-1-a-better-hallucination-detection-model/)
  - LettuceDetect: MIT; token-level; ModernBERT 4k context; TinyLettuce 17–68M — [README](https://cdn.jsdelivr.net/gh/KRLabsOrg/LettuceDetect@main/README.md)
- [S][OBS] Jev's own citation-check cookbook frames "does this quote support this claim" as a Noul — [docs index](https://docs.typesafe.ai/llms.txt). An NLI cross-encoder plus a calibrator cut Brier roughly in half in R2VC's ablation (0.161 without calibration) — [arXiv 2609.11955](https://arxiv.org/abs/2609.11955)

### Inferences
- [INF] **Write-gate design (U1/U4 with I16):**
  - For each extracted field, ask a local System One check: "is value V stated in span S?" (Noul) plus "not stated" / "contradicted" options (Choice), with neutral option names and swapped order.
  - Ensemble with a MiniCheck-class grounding model from a different family than the extractor.
  - Stack the signals into a logistic "correct" score per field type; calibrate per type.
  - Auto-accept with **Conformal Alignment (BH on conformal p-values) at FDR ≤ α per record type**, calibrated on ~500 audited records. Everything else goes to the owner queue.
  - Guarantee: among auto-accepted fields, the expected share of wrong values ≤ α, under exchangeability with the audit stream.
- [INF] **Omissions need their own conformal check.** FDR on accepted values says nothing about missing records (R3: "omissions carry no confidence"). Treat "are all records in this message extracted?" as a max-type coverage problem, like Q4. Ask a System One "is there an un-extracted decision / commitment / fact in this message?" per message, calibrate it on audited messages with planted omissions, and use the per-message miss score's conformal quantile to route messages (not fields) to review.
- [INF] Use Mondrian groups by record type and stakes (money/legal/health). Pool rare types by clustering (≥ 20–75 audited records per cluster).

### Gaps
- No public benchmark of conformal FDR control for *field-level* extraction from conversational business text.
- No measured omission-detection calibration for any model.
- HHEM-2.1-open and MiniCheck numbers on conversational, non-English-business text are unknown.

---

## Q6. Practical: libraries, compute, calibration examples per class

### Takeaway
Use MAPIE 1.6 (risk control, LTT, martingales) or crepes 0.9.1 (Mondrian, martingales) for conformal. Use scikit-learn for Platt/isotonic. TorchCP only if GPU batch CP is needed. Compute is trivial; labels are the budget.

Working numbers per class or decision type:
- **≥ 9** sets for any finite threshold at α = 0.1.
- **~100** for a usable marginal threshold.
- **200–500** for a tight one-sided certificate; ~200 to estimate a judge's error rate within ±0.05.
- **~500** for Trust-or-Escalate / Conformal-Alignment-style guarantees with useful coverage.
- **≥ 1,000** to keep realised coverage within ±2 pp of target on most draws.

### Cited Findings
- [S][OBS] n = 1,000 gives coverage "typically between .88 and .92"; n(ε) = 22 / 102 / 2,491 for ε = 0.1 / 0.05 / 0.01 — [Gentle Intro](https://arxiv.org/pdf/2107.07511)
- [S][OBS] Groups with fewer than 1/α − 1 examples get infinite thresholds; clustered conformal is best at ~20–75 per class, classwise at 100+ for the rarest — [Ding et al.](https://www.stat.berkeley.edu/~ryantibs/papers/classconf.pdf)
- [S][OBS] ~200 calibration labels for a < 0.1-wide CI on a corrected judge pass rate — [arXiv 2511.21140](https://arxiv.org/pdf/2511.21140)
- [S][OBS] 500 / 392 calibration items in Trust or Escalate — [arXiv 2407.18370](https://arxiv.org/pdf/2407.18370); "a few hundred" for Conformal Alignment — [arXiv 2405.10301](https://arxiv.org/html/2405.10301v3)
- [S][OBS] A threshold fitted on 10 labelled items recovered most F1 for Jev in alignment detection; refits of 1–2 parameters fixed Jev ECE on a held-out half — [arXiv 2609.29429](https://arxiv.org/pdf/2609.29429); [roundup](https://ai.plainenglish.io/jev-after-eight-days-of-independent-tests-level-with-mid-price-llms-behind-the-frontier-05daa8f21e2e)
- [OBS][computed with scipy, Beta law of split conformal at α = 0.1]:

  | n | P(realised coverage ≥ 0.90) | α_eff for 95%-confidence (PAC) coverage |
  |---|---|---|
  | 50 | 0.57 | 0.039 |
  | 100 | 0.55 | 0.050 |
  | 200 | 0.53 | 0.065 |
  | 500 | 0.52 | 0.078 |
  | 1,000 | 0.52 | 0.085 |

  One-sided 95% Clopper-Pearson lower bounds for an observed 93% all-vital success: 0.873 at n = 100, 0.893 at 200, 0.901 at 300, 0.908 at 500. 29 straight successes certify ≥ 0.90.
- [OBS] Library versions and licences: MAPIE 1.6.0 BSD-3 — [PyPI](https://pypi.org/project/MAPIE/); crepes 0.9.1 BSD-3 — [PyPI](https://pypi.org/project/crepes/); TorchCP LGPL-3.0 — [JMLR](https://www.jmlr.org/beta/papers/v26/24-2141.html)

### Inferences
- [INF] For BrainBench certification per class, plan **≥ 300 distinct required sets per class** in the held-out certification split, plus a separate calibration split of similar size. The current v0.2 has 129–162 distinct sets for the complex classes per seed (pooling three seeds gives ~400–480).
- [INF] For the live system, a new partition starts "uncertified" on a pooled threshold. It earns its own per-class threshold after ~100 audited tasks per class, and a certificate after ~300.

### Gaps
- No guidance found on calibration-set size for *max-type* (all-items) scores specifically. The Beta law applies unchanged because the score is per task.
