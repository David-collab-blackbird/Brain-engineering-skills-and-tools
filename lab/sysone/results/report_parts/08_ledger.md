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
