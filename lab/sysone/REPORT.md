# Open "System One" calibrated decision models: survey, reverse-engineered recipe, BrainBench sandbox, and a local self-learning grader for the brain

*Stream R7 / experiment E13a. Claude (engineer), 23–24 Oct 2026. Builder: Claude Code. All scripts are in
`/home/claude/sysone/scripts/` and re-runnable (§9). Vendor code was cloned into `/home/claude/sysone/vendor/<repo>/repo` and
read; no vendor code was imported or installed. Every model was loaded through re-implemented code paths, with checks
against published numbers.*

Hypotheses moved: **U7** (self-learning confidence grader), **U4** (maker–checker), **I15** (certified recall),
**I16** (three tiers), **W11** (no cross-partition statistics in trained models).

Evidence tags: **OBSERVED** (read the code, ran it, or read the primary source), **INFERRED**, **UNKNOWN**.
Strength: independent / vendor / single study / sandbox (synthetic).


## Summary (read this first)

1. **The open "System One" ecosystem is large but repetitive.** About 30 runnable projects reduce to one pattern: one
   forward pass, a softmax restricted to option tokens or `[MASK]` markers, and **a post-hoc temperature fitted on
   held-out labels**. In code, "RL for calibrated decisions" is either a minor term (Laya's own ablation found no gain
   over soft cross-entropy) or not RL at all (Von's "RLCD" is CE + Brier). **No RL is needed; calibration comes
   from the temperature and the labels.**
2. **Licence and provenance traps are real.** Von trains on soft targets distilled from Jev 1.13 (and is archived).
   JevK5 distils GPT-6 Luna. Liquid's d1 uses a revenue-capped licence. d1-ultra is hosted only. **Elephant-1 (MIT, 9B)**,
   **Jeff (MIT/Apache, 0.8B, LoRA adapters, open-teacher data)**, **Kev** and **Laya** (Apache) are the clean
   candidates.
3. **Sandbox on BrainBench (CPU, fp32): zero-shot quality is job-specific, and leaderboards don't predict it.**
   - Laya is a strong zero-shot extraction checker: J1 acc 0.863, AUROC 0.943.
   - The **Jeff v1.3 base (0.8B)** is the best all-round zero-shot arm: J1 0.838 at ECE 0.044, J3-area 0.85
     (small n). An off-the-shelf adapter for a neighbouring task ("ground") made J1 worse.
   - Julia-1 is near chance on J1 and J2 but the best zero-shot area router (0.70).
   - Both S1 encoders are below chance on J4 omission-detection, where a 71M NLI cross-encoder scores 0.77.
   - No open S1 model is good on all four jobs zero-shot.
4. **Self-learning works.** With 200–1,000 of the brain's own labels, a linear probe on frozen features lifts almost
   every arm on every job (one exception: Qwen J3-area, flat at 0.70 with only 60 labels). ECE reaches ≤ 0.07 on
   J1/J2/J4 and 0.05–0.13 on J3, in seconds on CPU:
   - J1: 0.92–0.93 (NLI-xsmall 71M matches Laya 421M);
   - J2: up to 0.83 (Jeff base reaches 0.82 with only 123 labels);
   - J3-type: up to 0.83;
   - J4: up to 0.94.
   Native-head fine-tuning (Unsloth head-mode analogue) on CPU reaches 0.77–0.84 for Julia, **but only with a
   higher learning rate than the vendor default**. Small label counts (N = 50) can make things worse, so promotion must
   be gated.
5. **For the brain:**
   - **Write gate:** deterministic checks first, then a calibrated checker. At a realistic 10% error rate a Laya-class
     checker auto-accepts about half the records with 1–2% residual error. *Certifying* ε = 5% needs ≥ 59 (ε = 2%:
     ≥ 149) audited, error-free accepted records per partition × record type.
   - **Router:** with about 300 labels (200 fit + 100 calibrate) the best arm gives conformal singletons for 72–84% of
     requests at 84–93% singleton accuracy.
   - **Relevance grader:** certifies all-vital recall but prunes too little at today's AUROC (0.74–0.89).
6. **Never quantise these small graders to int8 on CPU without an agreement test.** Int8 flipped 35–65% of
   decisions; the first pass of this sandbox was invalid because of it.

**Recommended design:** a frozen open base on the GPU host (Jeff base + per-partition LoRA adapters, or Laya), a diverse
NLI/cross-encoder second checker, and per-partition calibration artefacts. Promote any learned upgrade only through a
family-split dev set, and give every automation threshold a Learn-then-Test certificate on random-audit labels. Full
design in §5.


## 1. Survey: open "System One" implementations (verified 23 Oct 2026)

**How to read this.** "Read" = I read the repository or Hub code at the stated commit; "card" = model card/README only.
Stars come from the VoltAgent list snapshot (the GitHub API is blocked here), so treat them as approximate. Licences are
read from LICENSE files and Hub metadata. Independent numbers come from JevBench v1.4.2.2 (Benchmark Heaven, 27 Sep 2026,
`results/jevbench_v1422_rows.tsv`): the standard-tier accuracy on its public typed decisions, followed by the Calibration
axis score (0–100). Numbers from different benchmarks are not comparable.

### 1a. Models you can download and run

| Project (link) | Stars / last commit | Licence (weights) | Base, size | Architecture (code-verified) | How calibration is obtained (code-verified) | Self-claim vs independent |
|---|---|---|---|---|---|---|
| [Laya](https://github.com/NandhaKishorM/laya) + [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) (read) | 31.7k / 2026-10-21 | Apache-2.0 | ModernBERT-large encoder, 421.3M fp16 (header count); multilingual variant on mmBERT-base, 322M | **Non-autoregressive encoder.** `[CLS] type question [SEP] [MASK] opt0 [MASK] opt1 … [SEP] state [SEP]`, 2-layer transformer head, MLP scorer at each `[MASK]`, softmax over options; extra "act/escalate" head | "RLCD": REINFORCE with a group-mean baseline on Gaussian-noised logits, reward = log + spherical (+ ranked-probability) proper scores, **plus soft cross-entropy**. Laya's own `train.py` notes that issue #741 found **no gain from the RL term** over soft-CE. Post-hoc temperature per question type and option-count bucket. The shipped `choice:11+` temperature is a bug (0.1006 → clamped). | Claims: in-task ECE 0.030, zero-shot ECE 0.204 (own eval). JevBench: std 0.729, cal 63.7. Typed-decisions base 0.360 (3rd-party). **Mine: 0.387** on a 300-question subset |
| [receptron/laya](https://github.com/receptron/laya) (read) | — / 2026-10-16 | MIT code; weights Apache-2.0 | same Laya, ONNX fp32 1.7 GB | Node/TS ONNX Runtime port of `rl_agent_api.system_one`; output matches Python to 4 dp | Uses Laya's temperatures; overrides `choice:11+` to 0.945 | Port, not a new model |
| [Julia-1](https://huggingface.co/SupersonicLabs/Julia-1) (read) | HF ≈6k downloads / 2026-09-26 | Apache-2.0 | mmBERT-small, **144.3M** fp32 | Laya-identical head layout on a small multilingual encoder (state-dict compatible) | `inference-policy.json`: `calibration: null`; `provenance.json`: `quality_gate: false` (raw softmax) | Claims typed-decisions 0.71 / 0.805 / 0.678 (choice / noul / score). **I reproduced choice exactly: 0.710 on all 600.** On 300 subset questions: 0.578 / 0.811 / 0.642 |
| [Von](https://github.com/wfzyx/von) (read) | 875 / 2026-10-19, **archived** | Apache-2.0 | ModernBERT-large option-marker, 395M (~3 GB with both checkpoints) | Option markers with optional per-option attention isolation (order-invariant); "chain-of-options" regex+operator library for dates and amounts | Code: CE + 0.5·Brier (soft targets allowed) — **no RL despite the "RLCD" name**. Post-hoc temperature map T = f(entropy, log tokens, K), refittable on CPU with `von calibrate`. **Trains on `SargeDev/jev-distill-corpus-v3` (soft targets "distilled from Jev 1.13")** | JevBench: std 0.687, cal 75.7. Author points to d1-omni-600M instead |
| [Jeff](https://github.com/firelex/jeff) + [mstrasser/jeff-base](https://huggingface.co/mstrasser/jeff-base) (read) | 1.5k / 2026-10-07 | MIT code; weights Apache-2.0 (some adapters CC BY-NC or data-source terms) | **Full fine-tune of Qwen3.5-0.8B** (853M incl. 100.6M vision) | Causal LM, chat prompt, last-token hidden state → 255-way readout `Linear` initialised from the lm_head rows of codes A..Z, AA..; **swappable LoRA adapters** (r16/α32 on all attention, MLP and DeltaNet projections, 10.2M params plus their own readout and temperature) | One fitted temperature per base and per adapter, on a separate calibration split; adapter kit checks shortcuts and leaks and splits by family | Claims: adapters reach 94.6% mean on 8 tasks vs 86.6% for Qwen3.8-27B; label curve 250→76%, 1k→81%, 72k→91.5%. Base synthetic data written by open Qwen3.8-Flash-Next (not Jev). **Ran it on CPU here** (my re-implementation, reference DeltaNet kernels, about 2.5–3 s per decision): J1 0.838, ECE 0.044 zero-shot (§3) |
| [Kev](https://github.com/jaredpalmer/kev) (read) | 8.7k / 2026-10-22 | Apache-2.0 | Qwen3.5-0.8B / 4B / 9B adapters on frozen base; 27B full | Causal backbone with a **block-causal branch mask** (questions share the state, never each other), pointer head (q·k between the `<decide>` token and option-end tokens) | CE (+ optional label smoothing / Brier / focal) + ordinal CDF term + permutation-KL; post-hoc temperature per checkpoint (2.2–2.4 small, 1.32 27B). Fine-tune skill: train/calibration/development split by state; `plan_size.py` sizes the label set | Claims Kev-27B Brier 0.225 vs Jev 0.211 on new sources. JevBench (research-preview builds): kev-4B std 0.916, cal 39.6; kev-0.6B std 0.812 |
| [JevK5](https://github.com/allebee/jevk5) (README) | 144 / 2026-09-28 | Apache-2.0 | Qwen3.5-4B / 9B + merged LoRA | Letter-logit readout (SemIf protocol), one pass per question, CUDA graphs (13 ms on H100) | One temperature + "knockout" temperature; **distilled from Qwen3.6-27B and GPT-6 Luna** | JevBench std 0.958, cal 74.5 (#2 of 76 at v1.4) |
| [imajev](https://github.com/mohit67890/imajev) (read) | 344 / 2026-10-11 | Apache-2.0 | Qwen3.5-2B / 4B / 9B LoRA r16 + 255-code readout; vision tower frozen | Image + state → option codes, plus a trained `unknown` option (abstention) | Temperature per (type, option-count bucket) plus a fitted unknown-logit offset (moves the abstention boundary); 4-rotation option averaging. Phase-3 adapter worsened DecisionBench ECE (0.024 → 0.069) | JevBench v1.4.2.2 #1 (std 0.989, cal 80.4), Image JevBench #1 |
| [d1-omni-600M / d1-3B](https://huggingface.co/LiquidAI/d1-omni-600M) (card) | HF 16k / 25k downloads | **LFM Open License v1.0** (commercial use restricted above USD 10M annual revenue) | LFM2.5 encoder 350M (+audio, vision); d1-3B on LFM2.5-VL | One forward pass; text cut to 896 tokens | Per-type temperatures in `config.json` for text; image/audio answers uncalibrated | d1-3B: Decision Index public 48.57 (vendor) |
| [Elephant-1](https://huggingface.co/baselabs/elephant-1) (card + API) | HF 85 downloads / 2026-10-19 | **MIT** | Qwen3.5-9B full fine-tune, 18.8 GB; mammoth-1 27B sibling | Block-bidirectional mask on full-attention layers; all questions from one shared-prefix prefill; text + image | "Calibrated probability per option" (method not read) | Vendor: Decision Index 0.4 62.65 (best under 15B); AA-replica 65.2 ≈ d1-ultra. **Open weights: yes** |
| d1-ultra (Liquid) | — | **Hosted only**; weights and licence unpublished | "larger open-weight base", undisclosed | — | "specifically trained" for calibration, method undisclosed | AIM System One Index #1 (60; Jev 1.14 = 58); claims AA Decision Index lead by ≥8 points |
| [CLM-8B](https://github.com/Contrastive-LM/CLM) (README) | 2.9k / 2026-10-05 | Apache-2.0 | frozen Qwen3-8B embeddings (vLLM pooling) + 20M state/action heads | **Dual encoder:** state and actions embedded separately and cached; contrastive scoring | Head fine-tuning recipe (DeepSWE / T-Bench heads) | Claims Jev parity on agent tasks, verifier SOTA after fine-tune |
| [Vela 2.0](https://huggingface.co/vllm-sr/Vela-2.0-0.3B) (card) | HF 3.9k / 2026-10-07 | Apache-2.0, with Gemma terms bundled for derived parts | ModernBERT-style bidirectional encoder, 0.3B–9B; ONNX fp16 | Choice / Noul / Score plus **Span** (labelled spans with offsets, e.g. unsupported claims) and Set (multi-label) | calibration.json per head | Router-oriented (vLLM Semantic Router) |
| [GLiNER2.5-Decide](https://huggingface.co/fastino/GLiNER2.5-Decide) (card) | HF 138k / 2026-10-08 | Apache-2.0 | GLiNER2-large, 340M | Schema-conditioned encoder, any label set at call time | not described | Own suite 60.2% vs JevK5 57.6%; near chance on JevBench multi-step items |
| [decider](https://github.com/Mapika/decider), [Tev1](https://github.com/togethercomputer/tev1), [reflex](https://github.com/kshetrajna12/reflex), [Nimble](https://github.com/bespokelabsai/nimble), [AnyJev Tacit](https://github.com/nokia-applied-research/AnyJev) (README) | 1.1k / 226 / 163 / 2.1k / 1.1k | Apache-2.0 / MIT | Qwen3.5 0.8B–35B fine-tunes or LoRA; Tacit 1.7B–9B self-distilled | Letter/code readout from next-token logits (single pass); Tacit adds capped escalation to its own reasoning | Per-type temperatures (decider: Choice 1.5, Noul 0.05, Score 1.0); AnyJev "L0" = average over option rotations ÷ label prior estimated without labels (ECE 0.240 → 0.184) | JevBench: decider-4b v2 std 0.97; reflex-4B 0.95; Nimble-9B 0.95 |

### 1b. Training-free layers (turn any open LLM into a decision model)

| Project | What it does (code-verified where marked) | Calibration |
|---|---|---|
| [open-alternative-jev](https://github.com/ikermoel/open-alternative-jev) (read, Apache-2.0, 67★) | Renders each question as a ChatML user turn and reads the next-token distribution restricted to option letters at the assistant position; packs several questions about one state into one sequence (fixed placeholder answers between turns); `permutations=2` averages over reversed option order | Single scalar temperature by NLL grid (0.2–4.0) on a few hundred labels. Their measurements: packing causes interference below 4B (Qwen3-0.6B loses 7.5 pts on RACE-H); reversing options moves Qwen3.5-4B yes/no accuracy by 13.5 pts; averaging both orders halves ECE. Independent JevBench (Qwen3.5-4B): std 0.843 |
| [AnyJev](https://github.com/nokia-applied-research/AnyJev) (README, Apache-2.0) | Raw letter readout or "L0": rotation averaging + label-prior division, with a label-free rotation budget | Zero-label debiasing; not label calibration |
| [SemIf](https://github.com/TheoLeeCJ/SemIf), [system-one](https://github.com/sgoedecke/system-one), [simple-jev](https://github.com/featherless-ai/simple-jev), [openjev-sglang](https://github.com/ekzhang/openjev-sglang), [jevmlx](https://github.com/bnsd55/jevmlx) (list entries) | Same letter-logit idea on CUDA, MLX, WebGPU or SGLang | Mostly one temperature |

### 1c. Serving and tooling (relevant to the brain)

| Project | Relevance | Note |
|---|---|---|
| [stuntd](https://github.com/bladedevoff/stuntd) (read, Apache-2.0) | **The closest existing implementation of the owner's U7 idea.** A proxy records typed decisions from the app (or from an upstream LLM/Jev), trains one head per decision site on a frozen Laya or sentence encoder, fits a temperature, and serves locally only above a threshold. The threshold is the widest operating point that reaches a target agreement; anything else falls back. | Its threshold rule is a point estimate. Our design adds a Clopper-Pearson bound and random audits (§4) |
| [ollaya](https://github.com/ollaya-dev/ollaya) (Apache-2.0) | "Ollama for decision models": pulls Laya, decider, NLI and GLiClass and serves them behind `/v1/systemone` | install via `curl …/install.sh \| sh`; do not run blindly |
| [sys1](https://github.com/alvarobartt/sys1) (Apache-2.0, Rust/candle) | Self-hosted `/v1/systemone` server for ModernBERT and Qwen3.5 decision models, token-based batching | Small project (51★) |
| [pg-jev](https://github.com/realZachi/pg-jev) (PostgreSQL licence) | SQL functions `jev()`, `jev_prob()`, `jev_choice()` that batch 20 rows per request; `jev.api_url` can point at a **local** `/v1/systemone` server | Needs superuser (plpython3u is untrusted); calling a model from SQL inside RLS'd queries is a privacy hazard (see §5) |
| [pg_typesafe](https://github.com/giuliosmall/pg_typesafe) (MIT, pre-alpha) | C extension calling TypeSafe from SQL | Hosted Jev only, so not usable for member data |
| [Verdict-open-jev](https://github.com/Heman10x-NGU/Verdict-open-jev) (Apache-2.0) | 151M ModernBERT/GLiClass engine plus a "Jev benchmark audit"; its 1.4 update fixed a calibrator that never loaded | JevBench std 0.677, cal 72.0 |
| [JevBench](https://github.com/fstandhartinger/jevbench) (MIT) | Independent board: sealed items, evaluator-run containers, versioned methods; source of the independent numbers above | Calibration axis formula changes by version; do not mix versions |

### 1d. Bounded negative searches
- **Laya underlying weights:** found at `convaiinnovations/laya` (English root, multilingual and typed-decisions subfolders); ONNX at `receptron/laya-onnx`.
- **d1-ultra open weights:** searched the HF API (author LiquidAI, "d1") and Liquid's blog. Only d1-3B and d1-omni-600M are open; d1-ultra is hosted.
- **Elephant-1:** found at `baselabs/elephant-1` (MIT).
- **"AIM System One Index"** is AIMultiple's index (aimultiple.com/system-one, v1.2): z-scored over browser (n=50), classification (n=1,655) and bias tasks, with no calibration component. Elephant-1 and OpenAI Decisions are not on its first page. I did not open the TechCrunch article.
- **REA model inspector:** `rea-agents@6.7.0` has no `inspect-model-artifact` command (COMMAND_NOT_FOUND), and listing its commands was blocked by the sandbox permission classifier. Weights were verified with my own header-only reader (`scripts/inspect_weights.py`).
- **Not opened:** Clef (27B, outside the CPU budget), CLM code, Vela code, imajev serving code beyond calibration and scoring.


## 2. The reverse-engineered pattern: minimal recipe for a calibrated closed-question grader

Every open implementation I read reduces to the same four parts. Jev's own architecture is unpublished; this section
describes what the open replications do, verified in code. It makes no claim about what TypeSafe does.

### 2.1 The four parts
1. **Typed question → one sequence.** The state and one question go into one sequence, with the options rendered
   inline. Two families exist:
   - **Encoder / marker** (Laya, Julia, Von, Vela, Verdict). The sequence is `[CLS] {type} question: {instructions} [SEP] [MASK] opt0 [MASK] opt1 … [SEP] {state} [SEP]`, with each option
     capped at 48 tokens and the head block at 192–512 tokens. A small head scores the hidden state at each `[MASK]`.
     Bidirectional attention lets every option see the state, and other options too, unless they are isolated as in
     Von 1.2 and Kev with `option_isolation`.
   - **Decoder / letter readout** (open-alternative-jev, Jeff, JevK5, Kev, decider, imajev, Elephant-1). A chat prompt
     lists the options as `A. …`, `B. …`, and the model reads the next-token logits of the option codes at the
     assistant position (Jeff and imajev extend this to 255 codes: A–Z then AA, AB, …). Packing several questions per
     state shares one prefill: Kev uses a block-causal branch mask, so questions never see each other;
     open-alternative-jev uses placeholder turns, which causes measurable interference below 4B.
2. **One forward pass, no generation.** Softmax over the K option logits only, so the answer is always a valid option.
   Score questions (ordered scales) use the expected level ∑ i·p_i; Noul (yes/no) is p(true).
3. **Calibration = a post-hoc temperature, always.** Every project fits T (one per model, per question type, or per
   question type × option-count bucket) by minimising NLL on held-out labels. Some add training-time help:
   - Brier or proper-score terms in the loss (Von, Kev);
   - REINFORCE on proper scores (Laya's RLCD; its own ablation found no gain over soft-CE);
   - soft teacher targets (Von, from Jev; JevK5, from Qwen3.6 and GPT-6 Luna);
   - option-order averaging or isolation (so1 `permutations=2`, AnyJev rotations, Von isolation, imajev rotations);
   - an explicit `unknown` option with a fitted offset (imajev).
   Nobody ships conformal sets except vegaml (Laya's author) and kadi (list entries, not read).
4. **Serving.** A `/v1/systemone` HTTP wire with state plus a `questions` map of `{type, instructions, criteria}`,
   returning probabilities. Thresholds live in the caller ("act / review / escalate"). TypeSafe's own docs say
   confidence is not a probability of being right and that thresholds must be tested per domain.

### 2.2 Minimal recipe the builder can implement (CPU now, GPU later)

```text
Question  := {type: choice|noul|score, instructions: str, options: [(key, description)]}
Request   := {state: str|json, questions: {qid: Question}, partition: str}
Decision  := {qid, probs: {key: p}, answer: key, confidence: max p, model_version, calib_version}

1  encode(state, q)        -> model-specific sequence (marker or letter layout; options short, state truncated from the
                              middle, never silently)
2  z = logits(model, seq)  -> K raw scores (one pass; batch questions; prefix-cache the state on vLLM)
3  p = softmax(z / T[partition][q.kind][bucket(K)])     # bucket: 2 | 3-5 | 6-10 | 11+
4  if order-sensitive (decoder <4B): average log-probs over the given and reversed option orders
5  return Decision; the CALLER applies a certified threshold or conformal set (section 4)
```

Fitting T: minimise NLL over a grid, then golden-section on log T (`scripts/common.py:Temperature`). For a binary
question also fit Platt (logistic on z₁−z₀); use isotonic only above about 1,000 labels.

### 2.3 Per-partition fine-tuning ("self-learning"): data, label counts, method
**Data format (one decision per line, compatible with Laya/Unsloth, Kev and the Jeff kit):**
```json
{"id": "...", "partition": "member/m07", "family": "<task or entity id, used for group splits>",
 "state": "...", "question": {"type": "noul", "instructions": "...", "criteria": {"true": "...", "false": "..."}},
 "label": "true", "source": {"kind": "audit|correction|confirmation|seeded", "inclusion_prob": 0.05, "ts": "..."}}
```
- Split by **family** (task, entity or document), never by row. Jeff's kit and Kev's `split_data.py` both enforce this.
- Keep `inclusion_prob`. Labels that come only from items the system showed or flagged are biased (see r6 Q3). A small
  random-audit stream with known inclusion probability is what makes calibration valid.

**How many labels** (vendor evidence, plus my measurements in §3):
- Temperature only: 30–200 labels per question type is enough. Von's `calibrate` picks scalar vs feature map by k-fold
  CV and says "a few dozen labels give a safe scalar".
- Linear probe or head: hundreds. LoRA or adapter: 250 → 76%, 1,000 → 81%, 72,000 → 91.5% on Jeff triage (vendor).
- Kev's planner: about 1,000 records to detect +5 points at 80% power (400 records gave +0.6 ± 6 points, i.e. nothing).

**Methods by compute:**
| Level | What trains | Hardware | Time (vendor or measured) |
|---|---|---|---|
| L0 | nothing; temperature or Platt per partition × question type | CPU, seconds | measured: <1 s |
| L1 | linear probe on frozen features + zero-shot logits (this sandbox) | CPU, seconds | measured: <2 s at N=1,000 |
| L2 | native decision head only (Unsloth `--mode head`; `finetune_head.py` here) | CPU feasible for small encoders; GPU preferred | measured on CPU in §3 |
| L3 | LoRA on the backbone (Unsloth Laya r64/α64 lr 8e-4; Jeff r16/α32, one epoch; Kev adapters) | one GPU; Unsloth reports ≈2.5 GB VRAM for Laya | Kev: ~12–15 min on an H100 for 400–1,000 records |
| L4 | full fine-tune | GPU | Jeff chess: 600k positions in 3.5 h |

**Partition isolation.** One base model is shared and frozen. Each partition gets its own (adapter | head | T) file
trained only on that partition's labels. Jeff serves 15 adapters on one base for +0.35 GB with about 5 ms switching
overhead (vendor measurement on an RTX PRO 6000), so per-partition adapters are cheap to serve. Small partitions
(e.g. a single gym member) never have enough labels for L2/L3. They get L0 calibration on a pooled, consented,
partition-type model (e.g. "member" type), or stay uncalibrated and flagged.


## 3. Sandbox evaluation on BrainBench v0.2 (CPU, fp32)

### 3.1 Set-up (OBSERVED; `scripts/build_sets.py`, `build_j4.py`)
- **Worlds.** The test set is BrainBench world **s2**. Labels for calibration and learning come from worlds **s1** (+ **s3** for
  J1/J4), which have different people, properties and records from the same generator. This simulates "the brain's own
  outcomes" on one partition generalising to new records. It is **not** a cross-domain test.
- **J1 extraction checker** (Noul): the state is a quoted source span (note, chat or log) plus an extracted record
  `entity — attribute: value`. True records are the span's own keyed fact. Errors are seeded 50/50 as numeric drift
  (±5–25%, or a shifted date), value swap (the same attribute's value from another record), entity swap (same kind and
  attribute, different entity) or attribute swap (the same value under another attribute of the same value type). Spans
  with only approximate values ("about 271 grand") are excluded. Test n = 400 (102 entities); pool n = 1,200.
- **J2 relevance** (Noul): request (with requester role) plus one candidate item. Candidates are up to 4 required items
  plus 5 TF-IDF hard negatives from the requester's own partitions plus 1 random item. Hard negatives are often
  "related" (same entity) and include superseded versions. Test n = 928 (108 tasks); Laya was run on the first 600 rows
  (71 tasks).
- **J3 router** (Choice): request type (5 options, mapped from the 9 task classes) and area (7 options = declared
  scope). Test n = 200 + 200; pool n = 300 + 300.
- **J4 coverage** (Noul): a message made of 1–3 source sentences plus an extracted record list that is complete or
  drops one item. Test n = 243; pool n = 611.
- **Arms.**
  - (a) Open S1 models: **Laya 421M**, **Julia-1 144M**, **Jeff v1.3 0.8B** (+ `ground` adapter; small subset, CPU-slow).
  - (b) **Qwen3-0.6B letter readout** (open-alternative-jev layout, both option orders averaged).
  - (c) Cross-encoders: **bge-reranker-v2-m3 568M** (relevance logit) and **nli-deberta-v3-xsmall 71M** (entailment
    margin).
  - (d) **Verbalised confidence** (Qwen3-0.6B, greedy).
- **Calibration-only:** temperature, Platt and isotonic on N pool labels. **Self-learning (light):** a logistic head
  on [PCA-64 of frozen features + zero-shot logits], and the **native decision head** fine-tuned on cached
  frozen-encoder states (the CPU analogue of Unsloth `--mode head`).
- **Metrics:** accuracy (95% cluster-bootstrap CI over test groups), top-label ECE (15 bins), Brier, AUROC of P(yes),
  AUROC-err (does 1 − confidence rank the model's own errors?), and batch-1 p50 latency on **one contended vCPU**.
- **Implementation checks (OBSERVED):** Julia-1 reproduces its published typed-decisions choice accuracy exactly
  (0.710 on all 600 questions). Laya gives 0.387 on a 300-question subset vs 0.360 published full-test.

### 3.2 A finding that changes deployment advice: CPU int8 silently breaks small decision models
Dynamic int8 quantisation of every Linear layer (per-tensor or per-channel) changed the argmax for **35–65% of
decisions** vs fp32: Qwen3-0.6B agreement 0.35–0.39, Laya 0.51–0.63, Julia 0.44. bge-reranker held at 0.92 and the
NLI model at 0.81 (48–72 rows each). The first pass of this sandbox ran in int8 and made Laya look near chance on J1.
All numbers below are fp32. **Any quantised grader must pass a decision-agreement gate before use** (§6).

### 3.3 Zero-shot and calibration-only results (test = world s2)

| Job | Arm | n (groups) | Zero-shot acc [95% CI] | ECE raw | AUROC P(yes) | AUROC-err | ECE after T(200) | Brier after T(200) | Platt(200) acc / ECE | p50 ms (1 vCPU) |
|---|---|---|---|---|---|---|---|---|---|---|
| J1 | **Laya** | 400 (102) | **0.863** [0.83–0.89] | 0.086 | **0.943** | **0.836** | 0.052 | 0.195 | 0.863 / 0.053 | 1,974 |
| J1 | Julia-1 | 400 (102) | 0.550 [0.50–0.60] | 0.243 | 0.552 | 0.501 | 0.027 | 0.497 | 0.516 / 0.024 | 298 |
| J1 | NLI-xsmall | 400 (102) | 0.660 [0.61–0.71] | 0.289 | 0.874 | 0.748 | 0.131 | 0.407 | 0.755 / 0.071 | 120 |
| J1 | bge-reranker-v2-m3 | 400 (102) | 0.785 [0.75–0.83] | 0.133 | **0.949** | 0.786 | 0.051 | – | – | 1,705 |
| J1 | Qwen3-0.6B letter readout | 160 (41) | 0.500 [0.43–0.57] (always "yes") | 0.489 | 0.774 | 0.774 | 0.051 | – | 0.700 / 0.106 | 2,429 |
| J1 | **Jeff v1.3 base** (Qwen3.5-0.8B) | 160 (77) | 0.838 [0.77–0.90] | **0.044** | 0.934 | **0.866** | 0.059 | – | – | 2,482 |
| J1 | Jeff + `ground` adapter | 160 (77) | 0.800 | 0.126 | 0.916 | 0.852 | – | – | – | 2,585 |
| J2 | Laya | 600 (71) | 0.700 [0.66–0.74] (majority 0.71) | 0.230 | **0.684** | **0.698** | 0.042 | 0.383 | 0.704 / 0.046 | 1,610 |
| J2 | Julia-1 | 928 (108) | 0.346 [0.32–0.37] | 0.567 | 0.623 | 0.549 | 0.198 | 0.524 | 0.701 / 0.037 | 154 |
| J2 | NLI-xsmall | 928 (108) | 0.698 [0.68–0.72] (always "no") | 0.296 | 0.559 | 0.559 | 0.025 | 0.420 | 0.696 / 0.025 | 112 |
| J2 | bge-reranker-v2-m3 | 407 (47) | 0.700 [0.67–0.74] | 0.256 | 0.586 | 0.624 | 0.032 | – | – | 1,608 |
| J2 | Qwen3-0.6B letter readout | 206 (24) | 0.272 [0.23–0.31] | 0.700 | 0.633 | 0.633 | 0.268 | – | 0.728 / 0.066 | 2,570 |
| J2 | Jeff v1.3 base | 166 (20) | 0.717 [0.67–0.77] | 0.195 | 0.568 | 0.581 | – | – | – | 2,707 |
| J3 type | **Laya** | 200 | **0.555** [0.48–0.62] | 0.125 | – | **0.771** | 0.082 | 0.548 | – | 1,739 |
| J3 type | Julia-1 | 200 | 0.395 [0.33–0.46] | 0.471 | – | 0.615 | 0.086 | 0.742 | – | 160 |
| J3 type | NLI-xsmall | 200 | 0.425 [0.35–0.50] | 0.261 | – | 0.534 | 0.110 | 0.737 | – | 429 |
| J3 type | bge-reranker-v2-m3 | 100 | 0.420 [0.33–0.52] | 0.191 | – | 0.702 | – | – | – | 3,917 |
| J3 type | Qwen3-0.6B letter readout | 60 | **0.683** [0.57–0.78] | 0.293 | – | 0.474 | 0.171 | – | – | 2,910 |
| J3 type | Jeff v1.3 base | 40 | 0.700 [0.55–0.85] | 0.154 | – | 0.756 | – | – | – | 3,020 |
| J3 area | Laya | 200 | 0.655 [0.59–0.72] | 0.125 | – | 0.703 | 0.124 | 0.478 | – | 1,739 |
| J3 area | **Julia-1** | 200 | **0.700** [0.64–0.77] | 0.213 | – | 0.709 | 0.085 | 0.448 | – | 160 |
| J3 area | NLI-xsmall | 200 | 0.360 [0.30–0.42] | 0.207 | – | 0.550 | 0.131 | 0.814 | – | 429 |
| J3 area | bge-reranker-v2-m3 | 100 | 0.390 [0.29–0.49] | 0.422 | – | 0.697 | – | – | – | 3,917 |
| J3 area | Qwen3-0.6B letter readout | 60 | 0.700 [0.58–0.82] | 0.207 | – | 0.722 | 0.137 | – | – | 2,910 |
| J3 area | **Jeff v1.3 base** | 40 | **0.850** [0.72–0.95] | 0.189 | – | 0.515 | – | – | – | 3,020 |
| J4 | Laya | 243 (65) | 0.494 [0.44–0.55] | 0.442 | 0.443 | 0.436 | 0.132 | 0.511 | 0.560 / 0.098 | 3,082 |
| J4 | Julia-1 | 243 (65) | 0.473 [0.41–0.54] | 0.363 | 0.478 | 0.499 | 0.054 | 0.506 | 0.517 / 0.077 | 379 |
| J4 | **NLI-xsmall** | 243 (65) | **0.774** [0.72–0.83] | 0.153 | **0.878** | **0.767** | 0.065 | 0.304 | 0.784 / 0.055 | 243 |

J4 ("does this extraction miss a stated item?") is an entailment question at heart: the NLI cross-encoder is the
only arm above chance zero-shot. Both S1 encoders score below 0.5 with *inverted* AUROC (0.44–0.48). Rows for
Qwen3-0.6B and Jeff were scored on smaller group-aligned subsets (40–206 rows) because each decision takes 2.5–3 s on
this host, so their CIs are wider and their rows are not paired with the others.

**What this says.**
1. **Zero-shot quality is job-specific, and size or recency does not predict it.** Laya (trained on fact-checking and
   NLI families) is a strong zero-shot J1 checker (AUROC 0.94) but only at majority-class level on J2 (0.70 vs 0.71). Julia-1, the newer and smaller model,
   is near chance on J1 and J2, yet best at J3-area. No single open S1 model is good zero-shot on all four jobs.
2. **Calibration-only fixes ECE, never ranking.** A temperature fit on 200 labels brings ECE to 0.03–0.13 for every
   arm, but AUROC-err is unchanged by construction. A Platt refit can move the binary threshold (NLI J1: 0.66 → 0.755
   accuracy) but cannot fix bad ranking (Julia J1 stays at chance). This matches r6/U4: rescaling cannot improve which
   errors are caught.
3. **The training-free letter-readout recipe (open-alternative-jev) at 0.6B is position-biased.** Qwen3-0.6B
   says "yes" to every J1 record and is wrong on most J2 items. Its probabilities still rank errors (AUROC 0.77 J1,
   0.63 J2), so a Platt refit recovers 0.70–0.73. It is the best zero-shot request-type router (0.68 on 60 items),
   in line with the vendor's own finding that this recipe needs ≥ 4B parameters for packed or yes/no questions.
4. **Jeff v1.3 base is the best all-round zero-shot grader we could run**, even though it is "adapter-first":
   J1 0.838 at ECE 0.044 (calibrated out of the box), J3-area 0.85 and J3-type 0.70 (small n: 40–160), with
   **attribute swaps still caught only 40%**. The off-the-shelf `ground` adapter (trained to judge answers against
   retrieved passages) makes J1 *worse* (0.80; attribute-swap catch 0.13). Adapters are task-specific; a partition
   needs **its own** adapter, trained on its own labels.
5. **Latency on this host is not the headline.** These are fp32 times on one contended vCPU. Laya at 1.5–2 s is far
   from its vendor-claimed 33–40 ms on a T4. Julia (144M) and the NLI model (71M) run at 100–300 ms. GPU numbers are
   in §5.5.

**Verbalised confidence (arm d; Qwen3-0.6B, greedy, "ANSWER; CONFIDENCE 0–100", n = 80 per job).**
J1: acc 0.500, mean stated confidence 1.00, ECE 0.497, AUROC-err 0.51 (79 of 80 answers were "yes, 100"). J2: 0.287 /
0.99 / 0.701 / 0.48. J3: 0.684 / 0.95 / 0.269 / 0.52. It costs 8.8–9.6 s per decision (it generates text).
**Stated confidence carries no error signal (AUROC-err ≈ 0.5).** The same model's option-logit probabilities do
(J1 AUROC 0.77), so read logits, never ask a small model how sure it is.

### 3.4 Self-learning curves (labels from the pool; mean of 5 group-level resamples)
Arm = logistic head on [PCA-64(frozen features) + zero-shot logits]. Fitting takes under 2 s on CPU even at N = 1,000.

| Job | Arm | 0 (zero-shot) | N = 50 | N = 200 | N = 1,000 (J3: 300) | AUROC at max N | ECE at max N |
|---|---|---|---|---|---|---|---|
| J1 | Laya | 0.863 | 0.808 [0.68–0.88] | 0.882 [0.87–0.90] | **0.922** [0.90–0.95] | 0.964 | 0.037 |
| J1 | Julia-1 | 0.550 | 0.672 | 0.723 | 0.784 [0.76–0.83] | 0.874 | 0.046 |
| J1 | NLI-xsmall | 0.660 | **0.896** | 0.895 | **0.926** [0.91–0.96] | **0.969** | **0.026** |
| J2 | Laya | 0.700 | 0.582 | 0.646 | 0.725 [0.69–0.76] | 0.737 | 0.067 |
| J2 | Julia-1 | 0.346 | 0.678 | 0.725 | 0.786 [0.75–0.81] | 0.833 | 0.055 |
| J2 | NLI-xsmall | 0.698 | 0.644 | 0.771 | **0.827** [0.80–0.86] | **0.887** | 0.068 |
| J3 type | NLI-xsmall | 0.425 | 0.633 | 0.827 | **0.830** [0.78–0.88] | – | 0.080 |
| J3 type | Julia-1 / Laya | 0.395 / 0.555 | 0.524 / 0.475 | 0.664 / 0.652 | 0.700 / 0.676 | – | 0.13 / 0.19 |
| J3 area | Laya / Julia / NLI | 0.655 / 0.700 / 0.360 | 0.64 / 0.70 / 0.68 | 0.77 / 0.78 / 0.79 | 0.79 / 0.78 / 0.79 | – | 0.09–0.11 |
| J1 / J2 | Qwen3-0.6B letter readout (hidden-state probe) | 0.500 / 0.272 | 0.715 / 0.629 | 0.801 / 0.739 (N ≈ 200) | – | – | 0.095 / 0.134 |
| J1 | Jeff v1.3 base (hidden-state probe; n = 160 test) | 0.838 | 0.871 | 0.880 [0.82–0.92] (N = 173, pool cap) | – | 0.957 | 0.052 |
| J1 | Jeff + `ground` adapter (probe; n = 160) | 0.800 | 0.860 | 0.869 [0.80–0.93] (N = 122) | – | 0.950 | 0.046 |
| J2 | Jeff v1.3 base (probe; n = 166, 20 tasks) | 0.717 | 0.672 | 0.817 [0.76–0.88] (N = 123) | – | 0.866 | 0.066 |
| J1 / J2 | bge-reranker-v2-m3 | 0.785 / 0.700 | 0.846 / 0.688 | 0.902 / 0.755 | 0.916 / 0.797 (N ≈ 400) | – | 0.028 / 0.095 |
| J3 type / area | bge-reranker-v2-m3 | 0.420 / 0.390 | 0.622 / 0.766 | – | 0.748 / **0.850** (N = 100) | – | 0.10 / 0.07 |
| J4 | NLI-xsmall | 0.774 | 0.579 [0.42–0.82] | 0.902 | **0.938** [0.90–0.97] (N = 611) | – | 0.034 |
| J4 | Julia-1 / Laya | 0.473 / 0.494 | 0.567 / 0.527 | 0.779 / 0.690 | 0.805 / 0.714 (N = 611 / 406) | – | 0.07 / 0.10 |

**Native decision-head fine-tune** (Julia-1; frozen encoder, CE + 0.5·Brier, temperature on a held-out 20% of the
same label budget; head LR 3e-3, chosen on pool data; the Unsloth default of 1e-4 is shown in `tables.md`):

| Job | 0 | N = 50 | N = 200 | N = 1,000 (J3: 300) | ECE at max N | CPU train time at max N |
|---|---|---|---|---|---|---|
| J1 | 0.550 | 0.615 | 0.704 | 0.770 | 0.045 | 146 s |
| J2 | 0.346 | 0.745 | 0.767 | **0.841** | 0.024 | 183 s |
| J3 type | 0.395 | 0.443 | 0.578 | 0.547 | 0.088 | 43 s |
| J3 area | 0.700 | 0.690 | 0.755 | 0.753 | 0.085 | 40 s |

At LR 1e-4 the same runs reach only 0.700 (J1) and 0.741 (J2) at N = 1,000: the vendor default is tuned for large
datasets. **Laya's native head** on J1 (LR 3e-3) stays at its zero-shot accuracy (0.860–0.868 at N = 50 and 200),
while its error ranking improves (AUROC-err 0.70 → 0.88). Each run takes 3–7 min on CPU (1024-d states), so J2/J3
were not run. Fine-tuning helps most where zero-shot is weak; a strong zero-shot head is already near its ceiling.

![Self-learning curves (probe on frozen features)](results/curves.png)

**What this says about U7 ("a grader that learns from the brain's own outcomes").**
- **It works, and fast.** With 200 labels nearly every arm improves on its zero-shot accuracy on every job (exceptions:
  Laya on J2/J3-type, where the probe needs ~1,000 labels to pass zero-shot, and Qwen on J3-area with only 60 labels). Small encoders
  that were useless zero-shot (Julia J2: 0.35) become usable (0.77–0.84) after 200–1,000 labels, with ECE ≤ 0.07 and no
  GPU. The gains continue to N = 1,000 on J1/J2 and plateau around 200–300 on J3 (where the pool is capped at 300).
- **The model that learns best is not the one that starts best.** A 71M NLI cross-encoder plus a linear probe matched
  or beat the 421M Laya on J1 (0.926 vs 0.922) and beat it on J2 and J3-type. Choose the base by its *learning curve* on
  our labels, not its zero-shot leaderboard rank.
- **Jeff learns fastest per label on J2.** Its probe reaches 0.817 with only 123 labels, where NLI needs about 1,000
  for 0.827 and is at 0.771 with 200 (different test subsets, so this is indicative only). On J1 the probe lifts
  Jeff by 4 pp (0.838 → 0.880 at N = 173). Even after a probe, the off-the-shelf `ground` adapter stays below the
  base (0.869).
- **Small-N risk.** At N = 50 a learned head can be *worse* than zero-shot (Laya J1 0.81 vs 0.86; NLI J2 0.64 vs 0.70)
  with wide variance across resamples (Laya J1 0.68–0.88). The promotion rule must be "beat the incumbent on a
  held-out per-partition dev set", never "train when labels arrive" (§5.3).

### 3.5 Checker diversity (U4) — `scripts/stack.py`
- Zero-shot errors overlap only partly: Laya 55 errors, NLI 136, both wrong 19, margin correlation 0.74. Julia is
  nearly independent of both (correlation 0.09 / −0.01) but weak.
- A logistic stack of [Laya, NLI, deterministic value-token check] reaches **acc 0.897, ECE 0.021, AUROC 0.959**
  (Laya alone: 0.86–0.87 / 0.05 / 0.943). Adding bge-reranker gives **acc 0.917, ECE 0.030, AUROC 0.974**, already
  at 200 labels. These stacks are fit on the 407 pool rows that every arm scored and tested on all 400 test rows
  (`results/stack_J1.json`). Most of the gain comes from the **deterministic check**, which catches
  100% of numeric and value-swap errors by construction. Attribute swaps remain the hardest error for every model
  (caught 41–53%).

### 3.6 Where the full tables are
`results/tables.md` (generated) has every arm × job: zero-shot, temperature/Platt/isotonic at N = 50/200/max, probe
curves with resample ranges, native-head runs at both LRs, verbalised confidence, the J1 gate at three ε and two
prevalences, risk–coverage, J2 conformal recall, J3 conformal sets, and the J1 stacks. `results/curves.png` (+ `_dark`)
plots the probe curves.


## 4. Integration experiments: write gate, certified recall, router sets (`scripts/conformal.py`)

The pool is split by group: the first 2/3 fits the temperature or head, the last 1/3 calibrates thresholds. Test =
world s2. These are sandbox numbers on synthetic, templated text: they compare approaches and are not estimates for
the real brain.

### 4.1 J1 write gate (maker–checker): how much can be auto-accepted, with how many errors?
**Certification is label-hungry.** Learn-then-Test with a one-sided 95% Clopper–Pearson bound needs **≥ 59
accepted, audited records with zero errors** to certify ε = 5%, and **≥ 149** for ε = 2% (93 / 236 with one error).
With 334–397 calibration records (one third of the pool) at 50% error prevalence, nothing certifies at ε ≤ 5% and only one arm certifies
at 10% (bge + linear head: automation 0.50, realised error 9.0% at a 13% bound). This is the honest result: the seeded
set is too error-dense and too small for a strict certificate.

**At a realistic 10% error prevalence** (errors subsampled in calibration and test, 30 draws):
| Arm | ε | Certified (share of draws) | Automation | True records auto-accepted | Realised error among accepted | Catch: numeric / value swap / entity swap |
|---|---|---|---|---|---|---|
| Laya + temperature | 5% | 0.73 | 0.47 | 0.51 | **1.6%** | 0.97 / 0.94 / 0.94 |
| Laya + temperature, hybrid (deterministic value check first) | 5% | 0.73 | 0.44 | 0.49 | **1.1%** | 1.00 / 1.00 / 0.91 |
| Laya + linear head | 5% | 0.50 | 0.40 | 0.44 | 1.4% | 0.97 / 0.98 / 0.95 |
| NLI-xsmall + temperature | 5% | 0.30 | 0.13 | 0.14 | 1.8% | 1.00 / 0.99 / 0.97 |
| bge-reranker + temperature, hybrid | 5% | 0.53 | 0.48 | 0.52 | 2.2% | 1.00 / 1.00 / 0.86 |
| Julia-1 + linear head, hybrid | 5% | 0.23 | 0.11 | 0.12 | 1.0% | 1.00 / 1.00 / 0.98 |
| any arm | 2% | 0.00 | 0 | 0 | – | – |

(The attribute-swap catch rate is undefined at 10% prevalence in most draws; see the 50% table in `tables.md`.)

**Risk–coverage without certification** (test set, error among the top-q most confident "supported" calls):
| Arm | 50% error prevalence: top 10% / 25% / 50% | 10% error prevalence: top 10% / 25% / 50% |
|---|---|---|
| Laya + temperature (hybrid) | 0.000 / 0.040 / 0.105 | 0.000 / 0.000 / 0.005 |
| Laya + linear head (hybrid) | 0.000 / 0.020 / 0.085 | 0.000 / 0.002 / 0.003 |
| NLI-xsmall + linear head | 0.025 / 0.020 / 0.085 | 0.005 / 0.002 / 0.004 |
| bge-reranker + temperature (hybrid) | 0.000 / 0.040 / 0.080 | 0.000 / 0.001 / 0.005 |
| Julia-1 + temperature (hybrid) | 0.275 / 0.230 / 0.225 | 0.035 / 0.035 / 0.036 |

**Reading.** A local checker can route about half of the extracted records past review at under 1–2% residual error,
*if* the base has good ranking (Laya, or a probe on NLI). Certifying that at 95% confidence needs a few hundred
**audited** records per partition × record type, so certification is a per-partition milestone, not a day-0 feature.
The deterministic value-token check is free and removes the numeric and value-swap classes outright (§3.5).

### 4.2 J2 certified recall (I15 applied to the grader; DA2's two-budget design)
Per test task: keep every candidate with P(vital) ≥ λ, where λ is the conformal quantile of the **minimum** P(vital)
over each calibration task's vital items, so P(all vital candidates kept) ≥ 1 − α.
| Arm | α | Calibration tasks | Test tasks | Coverage [Wilson] | CP lower 95% | Kept share of candidates |
|---|---|---|---|---|---|---|
| NLI + linear head | 0.10 | 60 | 108 | 0.944 [0.88–0.97] | 0.893 | **0.664** |
| NLI + linear head | 0.05 | 60 | 108 | 0.991 [0.95–1.00] | 0.957 | 0.851 |
| Julia + linear head | 0.10 | 60 | 108 | 0.926 [0.86–0.96] | 0.870 | 0.760 |
| Laya + temperature | 0.10 | 38 | 71 | 0.944 [0.86–0.98] | 0.876 | 0.870 |
| NLI + temperature | 0.10 | 60 | 108 | 0.870 [0.79–0.92] | 0.805 | 0.886 |

**Reading.** Coverage of the *all-vital* event meets the target, but the candidate set shrinks only to 66–87% of
its size, because the grader is not discriminative enough on these hard negatives (same entity, superseded versions).
The structural point from r6 stands: conformal certifies the recall that the scorer and upstream structure already
provide. A relevance grader is useful as stage-1 pruning only once its AUROC is well above 0.9; here it is
0.74–0.89 after 1,000 labels. Calibration n here (60 tasks) is far below the 300+ distinct sets per class that r6
recommends for a stable certificate.

### 4.3 J3 router: conformal prediction sets
| Arm | Target | Request type: coverage / mean set size / singleton share (singleton accuracy) | Area: coverage / mean set size / singleton share (singleton accuracy) |
|---|---|---|---|
| NLI + linear head | 90% | 0.940 / **1.32** / 0.72 (0.93) | 0.835 / 1.16 / 0.84 (0.84) |
| NLI + linear head | 95% | 0.955 / 1.57 / 0.55 (0.95) | 0.910 / 1.95 / 0.41 (0.94) |
| Julia + linear head | 90% | 0.895 / 1.92 / 0.37 (0.88) | 0.905 / **1.48** / 0.63 (0.92) |
| Laya + temperature | 90% | 0.890 / 2.48 / 0.25 (0.92) | 0.895 / 1.79 / 0.51 (0.84) |
| zero-shot + temperature (any) | 90% | sets of 3.4–4.4 of 5 | sets of 1.8–4.6 of 7 |

**Reading.** With 200 fitting plus 100 calibration labels, the best router (NLI + linear head) produces singletons for
72% (type) and 84% (area) of requests at 84–93% singleton accuracy, and small sets otherwise; weaker bases give
singletons for only 25–63%. A set of size > 1 can route to all areas in the set, since retrieval across two
areas is cheap. Zero-shot routers produce near-uninformative sets, so routing *needs* the brain's own labels or a
strong prior (the dashboard section the user is in).


## 5. How this plugs into the brain: recommended design for the local self-learning grader

### 5.1 One service, three tiers (I16), per partition
```text
               ┌──────────── tier 0: deterministic validators (schema, value-token-in-span, entity exists, provenance) ──┐
request/write ─┤                                                                                                       ├─► decision
               └── tier 1: Grader (System One)  ──[certified threshold / conformal set]──► act | review | escalate ─────┘
                                      │                                     │
                                      │ low-confidence or outside set       └─► tier 2: System Two (local LLM, 9B–27B)
                                      ▼                                               or human review queue
                       label store (per partition, with inclusion probability)  ──► nightly refit of T / head / adapter
```
- **Grader = frozen shared base + per-partition calibration files + optional per-partition adapter/head.**
  - Base for the GPU host: Jeff base or Kev-4B (Apache-2.0, adapters, documented non-Jev provenance), or Elephant-1
    (MIT, 9B) if budget allows. On CPU only: the NLI-xsmall cross-encoder + probes (best learning curves at
    100–300 ms per decision), plus deterministic validators.
  - **Keep a cross-encoder (bge-reranker-v2-m3 class) and an NLI model as diverse checkers.** The maker–checker rule (U4)
    needs a checker from a *different* model family than the extractor (a Qwen-family LLM).
- **Calibration state is a versioned artefact.** It is keyed `(partition, job, question_type, option_bucket,
  base_model_sha, prompt_sha)`. Any change to the model, prompt or index invalidates it, and the job falls back to
  "uncalibrated → review".
- **Label stream per partition.** Sources: confirmations, corrections, failed-then-rephrased searches, seeded errors
  and **random audits** (2–5% of decisions, recorded inclusion probability). Only audited plus seeded labels are used
  for *certification*. All labels may be used for *training*, with inverse-propensity weights.

### 5.2 Job by job
| Job | Question form | Gate / use | Certified quantity | What the sandbox says (§3–4) |
|---|---|---|---|---|
| **J1 write-gate checker (U4)** | Noul: "Is this extracted record fully supported by the quoted span?" | Deterministic value-token check first (catches numeric drift and value swaps 100% in the sandbox), plus a **schema check** (does this attribute admit this value type/range? — the only cheap answer to attribute swaps), then the grader for entity and attribute errors; auto-accept iff P ≥ τ, τ from Learn-then-Test so that **error among auto-accepted ≤ ε at 95% confidence**; the rest go to review | ε (e.g. 2–5%) per partition × source type, with Clopper–Pearson on audited labels | see §4.1 |
| **J2 relevance grader (two-budget standard, DA2 I-1)** | Noul per candidate: "Is this item needed for this request?" (or 3-way vital / helpful / irrelevant) | Stage 1 (recall budget): keep every candidate with P(vital) ≥ λ, λ from per-class conformal on the **least-scored vital item per task**, so P(all vital kept) ≥ 1−α. Stage 2 (reader budget): rank the kept set and fill the context budget | per-class coverage of the *all-vital* event, with a CP lower bound on held-out tasks | see §4.2 |
| **J3 router** | Choice: request type (lookup / history / advice / cross-area / media) and area (gym / construction / cafe / finance / family / health / reading) | Conformal *set*: a singleton routes directly; a set of size > 1 routes to all areas in the set (cheap) or asks; the dashboard's open section ("packets") gives a strong prior | marginal coverage ≥ 1−α per class | see §4.3 |
| **J4 coverage checker** | Noul per sentence/span: "Does this span state a decision, preference or plan not captured in the extraction?" | An NLI cross-encoder over (extraction ⇒ message) plus a per-partition probe, or a span-type model (Vela 2.0 has a native Span question type); flagged messages go back to the extractor | catch rate on seeded omissions, per message | NLI-xsmall 0.774 zero-shot → 0.938 with 611 labels; S1 encoders below chance zero-shot (§3.3–3.4) |

### 5.3 Self-learning loop (U7), made safe
1. **Cold start (day 0):** zero-shot grader plus a pooled temperature fitted on BrainBench-style gold for each job.
   Everything below the certified threshold goes to review.
2. **Warm (≥ 30–50 audited labels per partition × job):** per-partition temperature or Platt (L0). Thresholds are
   re-certified by LTT on audited labels only.
3. **Hot (≥ 200–1,000 labels):** per-partition linear head (L1, CPU) or adapter (L3, GPU nightly). Promote it only if
   it beats the incumbent on a frozen per-partition dev set (paired bootstrap, family-split) **and** its decision
   agreement on a canary set stays within tolerance.
4. **Drift:** run a conformal test martingale on audit misses. Recalibrate with a rolling window, and freeze
   automation when the alarm fires (r6 Q3).
5. **Unlearning:** a deleted item's labels leave the store. Per-partition heads and adapters retrain from the store,
   so deletion propagates on the next refit (ADR-006 / W11: per-partition artefacts mean no cross-partition leakage
   path through shared weights).

### 5.4 Privacy and partition implications
- Models trained on partition P serve only P. Shared base weights are frozen public weights, so member data never
  enters a shared artefact. Pooled "partition-type" calibration (e.g. across members) needs consent and a
  de-identified aggregate (U5, APP 6). A temperature or a 64-d probe trained on a single member's labels can still
  memorise; store it inside that partition's encrypted scope.
- Never call a grader from inside SQL over RLS'd rows (pg-jev pattern). The grader must receive only what the
  requester's partition grants already allow.
- Hosted graders (Jev, d1-ultra, Elephant-1 on Baseten) only for the owner's own data, by policy flag. Member health
  data stays local.

### 5.5 GPU needs for the full-size version
| Component | Model class | VRAM (bf16) | Throughput note |
|---|---|---|---|
| Grader base + 15 partition adapters | Jeff (0.8B) | ~2.1 GB (vendor-measured) | ~30 ms per decision (vendor, RTX PRO 6000) |
| Stronger grader | Kev-4B / JevK5-4B / imajev-4B | ~9–10 GB | 13–40 ms per decision on H100/L40S (vendor) |
| Best open grader | Elephant-1 9B | ~19 GB | one shared prefill for all questions |
| Diverse checkers | bge-reranker-v2-m3 (568M) + NLI deberta-v3-large | ~2.5 GB | already in the retrieval stack |
| Adapter training | LoRA on 0.8–4B | 2.5–16 GB | minutes per partition (vendor: Kev-4B 12–15 min on H100 for 400–1,000 records) |

A single 24 GB card (e.g. L4 / RTX 4090 / A10) holds the 0.8B grader with adapters, both checkers and nightly LoRA
jobs. A 48 GB card (L40S / A6000) adds a 4B–9B grader. Sizing should be folded into W2/R1 (GPU host).


## 6. Risks: licences, weight provenance, distillation and ToS

| Risk | Evidence (status) | Consequence for the brain | Mitigation |
|---|---|---|---|
| **Weights trained on Jev outputs** | OBSERVED: Von's training pipeline harvests `SargeDev/jev-distill-corpus-v3`, whose `yuri_v3` stream carries "soft distributions distilled from Jev 1.13" (`training/prepare_distill_dataset.py`). stuntd can learn from upstream Jev answers. jimothy uses `typesafe-ai/jev` as teacher (list entry). | TypeSafe's terms were **not read** (UNKNOWN; their docs site was not fetched this round). Most hosted-model ToS forbid using outputs to train competing models. A derived model inherits the dispute even though the weights are Apache-2.0. | Do not adopt Von (also archived). Prefer bases whose training data is documented as not from Jev: Jeff (open Qwen teacher), Kev (open-weight teachers plus public data), Julia and Laya (Laya's data provenance is only partly documented; INFERRED not Jev-distilled, but its 0.766 typed-decisions checkpoint is fit to a teacher's labels). Our own per-partition heads train on our own labels only. |
| **Distillation from closed frontier LLMs** | OBSERVED: JevK5 distils GPT-6 Luna (plus Qwen3.6-27B) | Same class of ToS question for OpenAI outputs | Avoid as a base for a commercial product, or obtain legal review |
| **Non-permissive licences** | OBSERVED: d1 family = LFM Open License v1.0 (commercial use restricted above USD 10M revenue); Torchcast decision = CC BY-NC; Drex = Open RAIL-M; some Jeff adapters CC BY-NC (sanctions, soc) or data-source terms; devrecated trainer = AGPL-3.0; Vela bundles Gemma terms | The owner's businesses are small today, but the LFM threshold and NC clauses can bite later or block resale | Shortlist only Apache-2.0 / MIT weights (Laya, Julia, Jeff base and most adapters, Kev, Elephant-1, decider). Record licence plus SHA-256 per artefact in the model registry. |
| **Unverified claims and benchmark gaming** | OBSERVED: vendor tables disagree with JevBench (e.g. Laya's in-task ECE 0.030 vs JevBench cal 63.7; Julia ships `quality_gate: false`). Laya's 0.766 typed-decisions checkpoint exceeds the teacher ceiling (fit to a teacher's quirks, per the benchmark card). TypeSafe's own blog asks readers not to trust public benchmarks. | Leaderboards do not predict our closed questions (§3: Julia-1 is near chance on our J1/J2 despite strong vendor numbers; Laya ranks low on JevBench yet is our best zero-shot J1 checker) | Qualify every model on BrainBench-style gold sets per job before use (§5.3 promotion gate) |
| **CPU quantisation silently changes decisions** | OBSERVED (this sandbox): dynamic int8, per-tensor or per-channel, flips 35–65% of answers for Qwen3-0.6B, Laya and Julia vs fp32 | A "cheap" int8 deployment can turn a calibrated grader into noise without any error message | Any quantised build must pass a decision-agreement test (≥99% vs reference) plus recalibration. On GPU use bf16 or FP8 with a measured agreement check (open-alternative-jev found FP8 neutral for Qwen3-0.6B on GPU). |
| **Option-order and position bias** | OBSERVED (open-alternative-jev): reversing options moved Qwen3.5-4B yes/no accuracy by 13.5 points | Graders whose answer depends on option order give unstable maker-checker verdicts | Average both orders (decoder models), use order-isolated encoders (Von 1.2 / Kev isolation), or randomise order in training (Laya `shuffle_options`) |
| **Supply-chain** | OBSERVED: several projects install via `curl … \| sh` (ollaya, pg_typesafe); some HF repos need `trust_remote_code` (d1, Vela, Elephant-1 engine.py) | Arbitrary code execution on the brain host | Pin revisions plus SHA-256, read remote code, load with `trust_remote_code=False` where possible (all models in this sandbox were loaded from re-implemented code paths) |
| **Hosted graders and member data** | OBSERVED (r6): Jev is US-hosted, with zero retention enterprise-only | Member health data cannot go to Jev, d1-ultra or other hosted graders (ADR-016 / U5) | Local-only graders for member partitions; hosted graders allowed only for the owner's own data, by explicit policy |


## 7. Verdicts

| Question | Verdict | Evidence (status · strength) | Decisive next test / kill criterion |
|---|---|---|---|
| Do we need Jev (or any hosted S1) for the brain's graders? | **No: build locally.** | Open models plus a calibration layer reach ECE 0.03–0.13 with 200 labels (≤ 0.05 for the best arm on each binary job) (OBSERVED · sandbox). Member data cannot leave AU (r6, OBSERVED · vendor docs). | — |
| Is "RL for calibrated decisions" (RLCD) needed? | **No.** | Every open replication ends in a post-hoc temperature. Laya's own ablation (#741) found no gain from its RL term over soft-CE; Von's "RLCD" is CE + Brier (OBSERVED · code). Our probes reach ECE 0.02–0.07 with plain LR + temperature (OBSERVED · sandbox). | — |
| Which open S1 model should the brain adopt as its grader base? | **None as-is; choose per job by learning curve.** On a GPU host, shortlist **Jeff base + per-partition adapters** (MIT/Apache, documented non-Jev data, adapter-native) and **Laya** (strong zero-shot fact-checking); keep a **cross-encoder/NLI** as the diverse second checker. | Zero-shot rankings flip by job (Laya J1 0.86 vs Julia 0.55; Julia J3-area 0.70 vs NLI 0.36). A 71M NLI + probe matches Laya + probe on J1 (OBSERVED · sandbox). Jeff v1.3 base (run on CPU at ~2.5 s/decision with reference DeltaNet kernels) is the best all-round zero-shot arm (J1 0.838 ECE 0.044; J3-area 0.85, n = 40–160), Its probe gives the steepest J2 curve (0.817 at N = 123). An off-the-shelf adapter for a neighbouring task hurt J1 (0.80; 0.869 after a probe vs 0.880 for the base). | GPU validation package: Jeff + adapter, Kev-4B, Elephant-1 on BrainBench J1–J4 at N = 0 / 200 / 1,000; kill a base whose N = 1,000 accuracy is > 3 pp below the best per job. |
| U7: does a grader that learns from the brain's own labels work? | **Supported (sandbox), keep with changes.** | With 200–1,000 labels the best probe per job reaches J1 0.93, J2 0.83, J3 0.83–0.85, J4 0.94 (zero-shot best 0.86 / 0.72 / 0.70–0.85 / 0.77); weak bases gain up to +44 pp (Julia J2); ECE ≤ 0.07 on J1/J2/J4; probe fits in < 2 s, head fine-tune in < 3 min on CPU (OBSERVED · sandbox). Small-N regressions occur (N = 50). | Real-data pilot: one owner partition, 4 weeks of audited labels; promote a per-partition head only when it beats the incumbent on a family-split dev set (paired bootstrap, p < 0.05). Kill if no partition beats the pooled model after 1,000 labels. |
| U4: maker–checker with a different model family | **Supported, refined.** | Deterministic value check + Laya + NLI stack: acc 0.897, ECE 0.021 (+ bge: 0.917, AUROC 0.974); zero-shot errors overlap only partly (19 of 55/136). Attribute swaps remain hard for all models (OBSERVED · sandbox). | Seed attribute and entity swaps in real extractions (E14); target ≥ 90% catch at ≤ 5% false-block. |
| I15: conformal certified recall via the grader | **Mechanism works; utility limited by grader AUROC.** | Coverage on target (0.94 at α = 0.1) but keeps 66–87% of candidates (OBSERVED · sandbox, n = 60 calibration tasks). | Re-run with a GPU grader (AUROC ≥ 0.9 needed) and ≥ 300 calibration tasks per class; kill stage-1 grader pruning if the kept share stays > 50% at α = 0.1. |
| J4 coverage checker (omissions) | **Use an NLI-type entailment model, not today's S1 encoders.** | Zero-shot NLI 0.774 (AUROC 0.878), 0.938 with 611 labels; Laya and Julia below chance zero-shot (inverted AUROC 0.44–0.48) (OBSERVED · sandbox). | Seed omissions in real extractions; target ≥ 90% catch at ≤ 10% false flags per message. |
| I16 three tiers | **Supported.** | Deterministic checks catch whole error classes for free; S1 for semantic checks; S2 or human for the rest. | — |
| Verbalised confidence as a grader signal | **Killed.** | Qwen3-0.6B stated 95–100% confidence on everything; AUROC-err 0.48–0.52; 9 s per decision (OBSERVED · sandbox, n = 80 per job). | — |
| CPU int8 for small decision models | **Killed (as a default).** | 35–65% of decisions flipped (OBSERVED · sandbox). | Any quantised build must reach ≥ 99% decision agreement vs reference before use. |
| Von / devrecated trainer / JevK5 / d1 as dependencies | **Avoid.** | Von trains on Jev outputs and is archived; the devrecated trainer is AGPL and untested by its author; JevK5 distils GPT-6 Luna; d1 is under the LFM licence (OBSERVED · code/cards). | — |


## 8. Investigation checklist and findings ledger

### 8.1 Checklist (revisited at close)
| # | Question | Evidence needed | Status |
|---|---|---|---|
| Q1 | Which open S1 implementations are serious (stars, activity, licence, base, size, architecture)? | clone, code, HF API | **Answered** (§1; stars are an approximate snapshot because the GitHub API is blocked) |
| Q2 | How does each obtain calibration? | training and serving code | **Answered** for Laya, Von, Kev, Jeff, Julia, so1, imajev, devrecated, stuntd (code); **partly** for JevK5, decider, Elephant-1, d1, CLM, Vela (README/card only) |
| Q3 | Claims vs independent benchmarks | JevBench rows, own reproductions | **Answered** for those on JevBench v1.4.2.2 plus own reproduction of Julia and Laya; d1-ultra and Elephant-1 vendor-only |
| Q4 | Minimal recipe | code of so1, Laya, Von, Kev, Jeff | **Answered** (§2) |
| Q5 | Per-partition fine-tuning: data, label counts, LoRA, Unsloth | devrecated, Jeff kit, Kev skill, measured curves | **Answered**, with CPU measurements; LoRA/Unsloth **not run** (no GPU) |
| Q6 | Sandbox J1–J3 for arms (a)–(d) | CPU runs | **Answered**: Laya, Julia, NLI on all jobs (plus J4); bge-reranker on subsets (400/407/100); Qwen3-0.6B letter readout (160/206/60); Jeff base (160/166/40; probe pools 173/123) and Jeff + `ground` (J1, 160; probe pool 122); verbalised confidence (80 per job). Smaller n for the slow arms is reported in each row |
| Q7 | Self-learning curve at 50/200/1000 labels | CPU runs | **Answered**: linear probe for all arms (N up to the scored pool); native head for Julia at 2 LRs on all jobs; Laya native head J1 at N = 50/200 only (CPU budget) |
| Q8 | Brain integration: write gate, relevance, router, conformal | analyses on scores | **Answered** in sandbox (§4); certification sample sizes derived |
| Q9 | Risks: licences, provenance, distillation from Jev, ToS | code and cards | **Partly**: provenance OBSERVED for Von and Jeff; TypeSafe ToS **not read** (UNKNOWN) |
| Q10 | Do Liquid D1 / Elephant-1 have open weights? | HF API, vendor pages | **Answered**: d1-3B and d1-omni-600M open (LFM licence); d1-ultra hosted only; Elephant-1 open (MIT) |

### 8.2 Findings ledger
`results/ledger.tsv` holds every finding with its tag and source (file + commit, command or URL). Key rows:

| ID | Tag | Finding | Source |
|---|---|---|---|
| F01 | OBSERVED | open-alternative-jev: training-free letter readout, one scalar temperature by NLL grid; `permutations=2` reverses option order | `ikermoel_open-alternative-jev@3689c67 so1/*.py` |
| F02 | OBSERVED | Laya 421.3M fp16 (header count), marker head; shipped `choice:11+` temperature is a bug | HF `convaiinnovations/laya` `rl_common.py`; `scripts/inspect_weights.py` |
| F03 | OBSERVED | Laya RLCD = REINFORCE on proper scores + soft-CE; own ablation (#741) found no gain from RL | `NandhaKishorM_laya@6f0496f laya/train.py` |
| F04 | OBSERVED | Von "RLCD" = CE + Brier; trains on Jev-1.13-distilled soft targets; archived | `wfzyx_von@fd577a8 training/*.py` |
| F06 | OBSERVED | Jeff = full fine-tune of Qwen3.5-0.8B + 255-code readout; LoRA r16 adapters with their own readout and temperature; base data from an open teacher | `firelex_jeff@3720e7c`; HF `mstrasser/jeff-*` |
| F12/F13 | OBSERVED | Elephant-1 open (MIT); d1 family LFM licence; d1-ultra hosted only | HF API; liquid.ai blog |
| F15 | OBSERVED | CPU int8 flips 35–65% of small-model decisions | `scripts/score.py` + `common.py` check |
| F16 | OBSERVED | Julia port reproduces its published 0.710 choice accuracy exactly | `results/scores/julia/TDC_test.npz` |
| F18 | OBSERVED | Own bug (label misalignment in the head fine-tune) caught and the run discarded | `results/finetune_buggy/` |
| F21–F27 | OBSERVED (sandbox) | §3–4 numbers | `results/analysis.json`, `conformal.json`, `stack_J1.json` |
| F28 | INFERRED | Choose the base by per-job learning curve, not leaderboard | F21–F23 vs F14 |
| F29 | UNKNOWN | TypeSafe ToS on output training; Laya training-data provenance; d1-ultra size and licence; CLM/Vela calibration code | bounded search stated in §1d |
| F30 | UNKNOWN | GPU behaviour of Jeff, Kev, Elephant-1; behaviour on real text; membership inference from per-partition heads (W11) | not run |
| F31 | OBSERVED (sandbox) | J4: NLI-xsmall 0.774 zero-shot → 0.938 with 611 labels; S1 encoders below chance | `results/analysis.json` |
| F38/F39 | OBSERVED (sandbox) | Jeff v1.3 base J1 0.838, ECE 0.044 (n = 160); `ground` adapter lowers J1 to 0.80 | `results/scores/jeff*/` |
| F40 | INFERRED | Jeff port not checked against a published number; out-of-the-box ECE 0.044 suggests the readout path is right | – |
| F41 | OBSERVED (sandbox) | Jeff J1 probe 0.880 at N = 173 (AUROC 0.957) | `results/analysis.json` |
| F42 | OBSERVED (sandbox) | Jeff J2 probe 0.817 at N = 123 (steepest J2 curve per label); `ground` probe J1 0.869 | `results/analysis.json` |

### 8.3 Threats to validity
- **Synthetic, templated text.** BrainBench sources are short and generated. Error seeding is rule-based, so the
  deterministic value check catches numeric and value-swap errors *by construction*. Real extraction errors are
  messier: partial values, units, paraphrase.
- **Same generator for pool and test.** s1/s3 → s2 generalises across records, not across domains or writing styles.
  The learning curves are therefore optimistic for a real partition's early life.
- **Small calibration sets for conformal** (60 tasks for J2, 100 for J3 per subjob). Coverage figures carry wide CIs.
- **Subsets for slow arms** (Laya J2 600 rows; Qwen, bge and Jeff on group-aligned prefixes). Rows are
  group-shuffled, so prefixes are random groups.
- **CPU, fp32, one contended vCPU.** Latencies are not representative of a GPU host.
- **Head LR chosen on pool data** (no test peeking), but only one alternative LR was tried.


## 9. Re-running everything (builder instructions)

All scripts live in `/home/claude/sysone/scripts/`. Run with `python3 -I`, with `HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1
SYSONE_THREADS=1 SYSONE_INT8=0`. Vendor repositories are only read, never imported.

| Step | Command | Output |
|---|---|---|
| 1. Build labelled sets | `python3 -I build_sets.py && python3 -I build_j4.py && python3 -I build_typed.py` | `data/J{1..4}_{pool,test}.jsonl`, `data/TD_test.jsonl` |
| 2. Weights (once) | `huggingface_hub.snapshot_download` for `convaiinnovations/laya`, `SupersonicLabs/Julia-1`, `cross-encoder/nli-deberta-v3-xsmall`, `mstrasser/jeff-base@v1.3`, `mstrasser/jeff-adapter-ground@v1.3` (Qwen3-0.6B and bge-reranker-v2-m3 were already present) | `models/hf` |
| 3. Header check | `python3 -I inspect_weights.py <model.safetensors>` | parameter counts and dtypes |
| 4. Zero-shot scores | `python3 -I score.py --model {laya,julia,jeff,jeff_ground,qwen06,bge_rr,nli_xs} --sets J1_test,J1_pool,...` (or `run_rest3.sh`, memory-aware with retries; Jeff arms: `run_jeff.sh` / `run_rest7.sh`, CPU-slow at ~2.5–4 s per decision, so group-aligned subsets `SET:N`) | `results/scores/<model>/<set>.npz` (+ `_states.npz` for marker models) |
| 5. Implementation check | `score.py --model julia --sets TDC_test` → choice accuracy should be 0.710 | |
| 6. Calibration + probe curves | `python3 -I analyze.py` | `results/analysis.json` |
| 7. Native head fine-tune | `./run_ft.sh julia` (CPU, about 1 h) | `results/finetune/*.json` |
| 8. Integration | `python3 -I conformal.py && python3 -I stack.py` | `results/conformal.json`, `stack_J1.json` |
| 9. Verbalised baseline | `python3 -I verbal.py` | `results/verbal_qwen06.json` |
| 10. Tables and plot | `python3 -I tables.py && python3 -I plot_curves.py` | `results/tables.md`, `curves.png`, `curves_dark.png` |

**Do not** enable `SYSONE_INT8=1` for decision models without re-running the agreement check (§3.2).


## 10. Proposed updates for the hypotheses board (06) and experiment results (07)

*Proposed text only. I did not write to the project docs; the coordinating engineer owns them.*

| ID | Proposed status | Change |
|---|---|---|
| **U7** self-learning grader | **Supported (sandbox) → Testing (real data)** | Evidence: §3.4 (probes and heads lift every job with 200–1,000 labels, ECE ≤ 0.07). Design: frozen open base + per-partition calibration + optional per-partition adapter or probe; promotion gate on a family-split dev set; certification only from random-audit labels. Kill: no partition beats the pooled model after 1,000 labels in the pilot. |
| **U4** maker–checker | **Supported, refined** | Deterministic value-token check first (free, catches numeric and value swaps); then ≥ 2 diverse semantic checkers (S1 encoder + cross-encoder/NLI); stack them. Attribute swaps are the open weakness (≤ 53% caught by any model) and need a schema check (does this attribute admit this value type and range?). |
| **I15** certified recall | **Mechanism supported; utility unproven** | The grader must reach AUROC ≥ 0.9 on vital vs related before stage-1 pruning pays; re-test on GPU graders with ≥ 300 calibration tasks per class. |
| **I16** three tiers | **Supported** | Add: "never int8 a small grader on CPU without a ≥ 99% decision-agreement test". |
| **New: I17** grader base chosen by learning curve | **Proposed** | Select the S1 base per job by its accuracy at N = 200 and N = 1,000 of our own labels on BrainBench and the pilot, not by public leaderboard rank (F21–F28). |
| **New: E15** GPU grader bake-off | **Queued** | Jeff + per-partition LoRA, Kev-4B, Elephant-1, Laya, bge-reranker-v2-m3, NLI-large on BrainBench J1–J4 (plus real-text pilot) at N = 0 / 200 / 1,000; measure accuracy, ECE, AUROC, p50 latency, VRAM; also membership-inference on per-partition adapters (W11). |
| **New: E16** attribute-swap checker | **Queued** | Seed attribute swaps; test schema-type validation + S1 + stack; target ≥ 90% catch. |


