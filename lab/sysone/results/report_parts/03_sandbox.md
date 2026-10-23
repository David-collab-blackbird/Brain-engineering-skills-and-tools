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
