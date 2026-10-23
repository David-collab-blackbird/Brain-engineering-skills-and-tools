#!/bin/bash
# Remaining arms after OOM kills (the shared memory cgroup is used by other experiments). Each step waits until
# >= 2.8 GB is available, and is retried up to 3 times; score.py skips sets already cached.
cd /home/claude/sysone/scripts
export HF_HOME=/home/claude/models/hf HF_HUB_OFFLINE=1 SYSONE_THREADS=1 SYSONE_INT8=0
L=/home/claude/sysone/results/logs
# headroom in OUR memory cgroup (6.27 GB shared with other sessions' jobs), not host MemAvailable
CG=$(ls -d /sys/fs/cgroup/memory/process_api/*/claude-code-bash | head -1)
headroom() { echo $(( ( $(cat $CG/memory.limit_in_bytes) - $(cat $CG/memory.usage_in_bytes) + $(awk '/^total_inactive_file/ {print $2}' $CG/memory.stat) ) / 1048576 )); }
waitmem() { until [ $(headroom) -ge ${1:-2800} ]; do sleep 20; done; }
step() {  # step <log> <need_mb> <cmd...>
  local log=$1 need=$2; shift 2
  for t in 1 2 3; do waitmem $need; "$@" >> $L/$log 2>&1 && return 0; echo "[retry $t] $*" >> $L/$log; sleep 60; done
}
step laya.log 2800 python3 -I score.py --model laya --sets J1_test,J2_test:600,J3_test,J1_pool:1000,J2_pool:1000,J3_pool:600 --batch 8
step qwen06.log 3000 python3 -I score.py --model qwen06 --sets J1_test:300,J2_test:400,J3_test:300,J1_pool:400,J2_pool:400,J3_pool:300 --batch 4
step bge_rr.log 3000 python3 -I score.py --model bge_rr --sets J1_test,J2_test:600,J3_test,J1_pool:600,J2_pool:600,J3_pool:300 --batch 8
step jeff.log 2600 python3 -I score.py --model jeff --sets J1_test:200,J2_test:200,J3_test:120,J1_pool:200,J2_pool:200,J3_pool:200 --batch 4
step jeff_ground.log 2600 python3 -I score.py --model jeff_ground --sets J1_test:200,J2_test:200,J1_pool:200,J2_pool:200 --batch 4
step verbal.log 2600 python3 -I verbal.py --sets J1_test:100,J2_test:100,J3_test:100
step ft_laya.log 1800 ./run_ft.sh laya
step j4.log 2800 bash -c "python3 -I score.py --model nli_xs --sets J4_test,J4_pool --batch 16 && python3 -I score.py --model julia --sets J4_test,J4_pool --batch 8 && python3 -I score.py --model laya --sets J4_test,J4_pool:400 --batch 8"
echo RESTDONE > $L/rest_done.flag
