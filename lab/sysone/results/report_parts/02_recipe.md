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
