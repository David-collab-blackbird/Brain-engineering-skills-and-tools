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
