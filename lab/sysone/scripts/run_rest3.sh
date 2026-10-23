#!/bin/bash
# Final queue (trimmed for a contended 1-vCPU host; subsets are group-aligned prefixes of the group-shuffled files).
# Waits for cgroup headroom before each step and retries OOM-killed steps; score.py skips cached sets.
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0
L=/home/claude/sysone/results/logs
CG=$(ls -d /sys/fs/cgroup/memory/process_api/*/claude-code-bash | head -1)
headroom() { echo $(( ( $(cat $CG/memory.limit_in_bytes) - $(cat $CG/memory.usage_in_bytes) + $(awk '/^total_inactive_file/ {print $2}' $CG/memory.stat) ) / 1048576 )); }
waitmem() { until [ $(headroom) -ge ${1:-2800} ]; do sleep 20; done; }
step() { local log=$1 need=$2; shift 2
  for t in 1 2 3; do waitmem $need; "$@" >> $L/$log 2>&1 && return 0; echo "[retry $t] $*" >> $L/$log; sleep 60; done; }
step j4.log 2600 bash -c "python3 -I score.py --model nli_xs --sets J4_test,J4_pool --batch 16 && python3 -I score.py --model julia --sets J4_test,J4_pool --batch 8 && python3 -I score.py --model laya --sets J4_test,J4_pool:400 --batch 8"
step bge_rr.log 2600 python3 -I score.py --model bge_rr --sets J1_test,J2_test:400,J3_test:200,J1_pool:400,J2_pool:400,J3_pool:200 --batch 8
step qwen06.log 3000 python3 -I score.py --model qwen06 --sets J1_test:200,J2_test:300,J3_test:200,J1_pool:300,J2_pool:300,J3_pool:200 --batch 4
step verbal.log 2400 python3 -I verbal.py --sets J1_test:100,J2_test:100,J3_test:100
step jeff.log 2400 python3 -I score.py --model jeff --sets J1_test:200,J2_test:200,J3_test:100,J1_pool:200,J2_pool:200,J3_pool:200 --batch 4
step jeff_ground.log 2400 python3 -I score.py --model jeff_ground --sets J1_test:200,J1_pool:200 --batch 4
step ft_laya.log 1500 bash -c "for spec in 'J1' 'J2' 'J3 area'; do set -- \$spec; python3 -I finetune_head.py --model laya --job \$1 \${2:+--sub \$2} --ns 50,200,1000 --reps 3 --lr 3e-3 || exit 1; done; echo FTDONE"
echo RESTDONE > $L/rest_done.flag
