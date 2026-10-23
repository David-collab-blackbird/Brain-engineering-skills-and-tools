#!/bin/bash
# After the main zero-shot batch: Jeff base + ground adapter (subsets; slow on CPU), verbalised-confidence baseline,
# Laya native-head fine-tuning, then J4 (run_j4.sh waits for tail_done.flag).
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0
L=/home/claude/sysone/results/logs
until [ -f $L/done.flag ]; do sleep 30; done
python3 -I score.py --model jeff --sets J1_test:200,J2_test:200,J3_test:120,J1_pool:200,J2_pool:200,J3_pool:200 --batch 4 > $L/jeff.log 2>&1
python3 -I score.py --model jeff_ground --sets J1_test:200,J2_test:200,J1_pool:200,J2_pool:200 --batch 4 > $L/jeff_ground.log 2>&1
python3 -I verbal.py --sets J1_test:100,J2_test:100,J3_test:100 > $L/verbal.log 2>&1
until grep -q FTDONE $L/ft_julia.log 2>/dev/null; do sleep 30; done
./run_ft.sh laya
echo TAILDONE > $L/tail_done.flag
