# E-PM1 paused 2026-10-24 10:06 (owner: usage limit; resumes after Thursday's reset)
- Stopped by the engineer mid full run; processes killed; data intact.
- Built: materials (library 10/40/120, 60 tasks incl. no-gold, 12 gated variants), PREREGISTRATION.md (+ .sha256, locked copy in logs/), dry run (`dryrun_report.json`), conformance (`conformance.json`), two pilots (`analysis_pilot*.json`), partial full run (`analysis_full.json` may be partial; `runs/full/`).
- Spend at stop: $30.28 list price (cap $480).
- Resume: re-run the full phase from `logs/full*.runs.log` (the harness skips completed runs), then the analysis and RESULTS.md. Check `runs_invalid/` before resuming.
