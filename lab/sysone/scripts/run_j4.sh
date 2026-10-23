#!/bin/bash
# J4 coverage checker (added after the main batch): small models now, Laya after the tail batch.
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0
L=/home/claude/sysone/results/logs
until [ -f $L/tail_done.flag ]; do sleep 30; done
python3 -I score.py --model nli_xs --sets J4_test,J4_pool --batch 16 > $L/j4_nli.log 2>&1
python3 -I score.py --model julia --sets J4_test,J4_pool --batch 8 > $L/j4_julia.log 2>&1
python3 -I score.py --model laya --sets J4_test,J4_pool:400 --batch 8 > $L/j4_laya.log 2>&1
echo J4DONE > $L/j4_done.flag
