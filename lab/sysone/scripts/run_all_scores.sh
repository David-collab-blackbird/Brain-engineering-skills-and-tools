#!/bin/bash
# Sequential zero-shot scoring of every arm, fp32 (int8 disabled: it flipped 35-65% of decisions for Qwen/Laya/Julia).
# One model in RAM at a time; re-runnable (cached sets skipped). ~4 h on 1 contended vCPU.
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0
L=/home/claude/sysone/results/logs
python3 -I score.py --model nli_xs --sets J1_test,J2_test,J3_test,J1_pool,J2_pool,J3_pool:600 --batch 16 > $L/nli_xs.log 2>&1
python3 -I score.py --model julia  --sets J1_test,J2_test,J3_test,J1_pool,J2_pool,J3_pool:600 --batch 8 > $L/julia.log 2>&1
python3 -I score.py --model laya   --sets J1_test,J2_test:600,J3_test,J1_pool:1000,J2_pool:1000,J3_pool:600 --batch 8 > $L/laya.log 2>&1
python3 -I score.py --model qwen06 --sets J1_test:300,J2_test:400,J3_test:300,J1_pool:400,J2_pool:400,J3_pool:300 --batch 4 > $L/qwen06.log 2>&1
python3 -I score.py --model bge_rr --sets J1_test,J2_test:600,J3_test,J1_pool:600,J2_pool:600,J3_pool:300 --batch 8 > $L/bge_rr.log 2>&1
echo ALLDONE > $L/done.flag
