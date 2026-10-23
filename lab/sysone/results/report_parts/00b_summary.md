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
