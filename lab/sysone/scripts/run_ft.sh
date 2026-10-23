#!/bin/bash
# Native-head fine-tuning curves (frozen encoder states cached by score.py), at the Unsloth Laya head LR (1e-4) and a
# small-data LR (3e-3, chosen on J1 N=200 pool data only). Usage: run_ft.sh <model>
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1
M=$1; L=/home/claude/sysone/results/logs
for lr in 3e-3 1e-4; do
for spec in "J1" "J2" "J3 type" "J3 area"; do
  set -- $spec
  python3 -I finetune_head.py --model $M --job $1 ${2:+--sub $2} --ns 50,200,1000 --reps 3 --lr $lr >> $L/ft_$M.log 2>&1
done
done
echo FTDONE >> $L/ft_$M.log
