# E15 paused 2026-10-24 10:06 (owner: usage limit; resumes after Thursday's reset)
- Stopped by the engineer; all processes killed; data intact (`runs/`, `spend.csv`, `grades/`, `reviews/`).
- Spend at stop: $145.98 list price (cap $500).
- Full runs logged per arm-package (spend.csv, phase=full): A-P1 4, A-P2 4, B-P2 2, B-P3 6, B-P4 4, C-P1 4, C-P2 2, C-P3 9, C-P4 2, D-P1 1, D-P2 1, D-P3 3, D-P4 4, AU-P3 4, AR-P3 4. Two D runs (P4) were killed mid-run (no total_cost_usd; estimate from transcripts per Amendment notes).
- Missing for the preregistered primary analysis (P3+P4, 5 reps per arm): mainly arm D reps (P3 2 more, P4 1+), A on P3/P4, B on P3, C on P4; blind reviews of the latest runs; drills.
- Resume: `cd /home/claude/e15 && python3 harness/schedule.py harness/plan_full.json --concurrency 2 --stop-usd 500` (the scheduler skips completed runs), then `harness/analyze.py` and `harness/report_tables.py`.
