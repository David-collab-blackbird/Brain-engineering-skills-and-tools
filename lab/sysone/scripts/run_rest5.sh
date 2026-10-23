#!/bin/bash
# Last queue. Batch 1 for the generative arms (lowest activation memory); Qwen on a smaller subset.
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0 SYSONE_LOWMEM=1
L=/home/claude/sysone/results/logs
CG=$(ls -d /sys/fs/cgroup/memory/process_api/*/claude-code-bash | head -1)
headroom() { echo $(( ( $(cat $CG/memory.limit_in_bytes) - $(cat $CG/memory.usage_in_bytes) + $(awk '/^total_inactive_file/ {print $2}' $CG/memory.stat) ) / 1048576 )); }
waitmem() { until [ $(headroom) -ge ${1:-2800} ]; do sleep 20; done; }
step() { local log=$1 need=$2; shift 2
  for t in 1 2 3; do waitmem $need; "$@" >> $L/$log 2>&1 && return 0; echo "[retry $t] $*" >> $L/$log; sleep 60; done; }
step ft_laya.log 1200 bash -c "for spec in 'J1' 'J2' 'J3 area'; do set -- \$spec; python3 -I finetune_head.py --model laya --job \$1 \${2:+--sub \$2} --ns 50,200,1000 --reps 3 --lr 3e-3 || exit 1; done; echo FTDONE"
step qwen06.log 2200 python3 -I score.py --model qwen06 --sets J1_test:160,J2_test:200,J3_test:120,J1_pool:200,J2_pool:200,J3_pool:120 --batch 2
step verbal.log 2200 python3 -I verbal.py --sets J1_test:80,J2_test:80,J3_test:80
step jeff.log 2200 python3 -I score.py --model jeff --sets J1_test:160,J2_test:160,J3_test:80,J1_pool:160,J2_pool:160,J3_pool:160 --batch 2
step jeff_ground.log 2200 python3 -I score.py --model jeff_ground --sets J1_test:160,J1_pool:160 --batch 2
echo RESTDONE > $L/rest_done.flag
