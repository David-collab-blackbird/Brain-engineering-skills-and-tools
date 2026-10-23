#!/bin/bash
# Final arms (each well under the 2 h background limit): Jeff J2 pool (smaller), Jeff+ground on J1.
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0 SYSONE_LOWMEM=1
L=/home/claude/sysone/results/logs
python3 -I score.py --model jeff_ground --sets J1_test:160,J1_pool:120 --batch 2 >> $L/jeff_ground.log 2>&1
python3 -I score.py --model jeff --sets J2_pool:120 --batch 2 >> $L/jeff.log 2>&1
echo RESTDONE > $L/rest_done.flag
