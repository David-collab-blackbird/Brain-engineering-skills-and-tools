#!/bin/bash
# Jeff v1.3 (Qwen3.5-0.8B, 255-code readout) zero-shot base + 'ground' adapter. CPU-slow (~2-4 s/decision: reference
# PyTorch linear-attention kernels), so subsets. Waits for run_all_scores.sh to finish (one model in RAM at a time).
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1
L=/home/claude/sysone/results/logs
until [ -f $L/done.flag ]; do sleep 30; done
python3 -I score.py --model jeff --sets J1_test,J2_test:300,J3_test:200,J1_pool:300,J2_pool:300,J3_pool:300 --batch 4 > $L/jeff.log 2>&1
python3 -I score.py --model jeff_ground --sets J1_test,J2_test:300,J1_pool:300,J2_pool:300 --batch 4 > $L/jeff_ground.log 2>&1
echo JEFFDONE > $L/jeff_done.flag
