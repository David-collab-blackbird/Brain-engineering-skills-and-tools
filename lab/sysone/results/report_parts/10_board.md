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
