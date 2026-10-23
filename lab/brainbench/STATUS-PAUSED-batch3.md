# Batch 3 (BrainBench v0.3) paused 2026-10-24 10:06 (owner: usage limit; resumes after Thursday's reset)
- Stopped by the engineer; processes killed; caches and results intact.
- Computed so far (results_v03/): adr, agg, e9, e10, e11, escr, fab, i15, release stage pickles; `summary.json`; `tables.md`; pilots (haiku, haiku low effort, sonnet); spend in `spend_ledger.jsonl`.
- Interrupted: stage `e10` seed 1 rerun and stage `gate` (haiku, seed 2, bounded continuation).
- Resume: `cd /home/claude/brainbench && python3 run_batch3.py --stages gate --model haiku --seeds 1,2 --max-new-calls 85` and `--stages e10 --seeds 1`; then regenerate tables and write RESULTS_batch3.md (not yet written). Results enter the board (v1.2) once.
