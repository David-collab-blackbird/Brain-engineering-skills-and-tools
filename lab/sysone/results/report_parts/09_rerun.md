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
