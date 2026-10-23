#!/bin/bash
# Assemble REPORT.md from results/report_parts (parts are hand-written; numbers come from results/tables.md et al.)
P=/home/claude/sysone/results/report_parts
out=/home/claude/sysone/REPORT.md
: > $out
for f in 00_head 00b_summary 01_survey 02_recipe 03_sandbox 035_integration 04_design 05_risks 07_verdicts 08_ledger 09_rerun 10_board; do
  cat $P/$f.md >> $out; printf '\n\n' >> $out
done
wc -w $out
