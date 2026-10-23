#!/bin/bash
# Sequential, modest: leak probes -> twin world -> cache freshness -> supersedes links -> keyless subset. Each on its own DB copy.
set -u
D=/tmp/claude-0/-home-claude/4c8492a6-f948-5903-9334-5b76eec5c7f7/scratchpad/gbt
cd $D
export GBRAIN_HOME=$D/gbhome HOME=$D/gbhome NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
export GBRAIN_QUERY_EMBED_TIMEOUT_MS=30000
B="nice -n 5 /root/.bun/bin/bun --smol run"
cpdb() { rm -rf db/$1.pglite db/$1.pglite.gbrain-owner.json; cp -a db/s1.pglite db/$1.pglite; cp db/s1.pglite.gbrain-owner.json db/$1.pglite.gbrain-owner.json; }
echo "[q] start $(date +%T)"
cpdb leak; $B leak.ts plant $D/db/leak.pglite && $B leak.ts probe $D/db/leak.pglite $D/leak_probe.json; echo "[q] LEAK EXIT=$? $(date +%T)"
cpdb twin; $B leak.ts twin $D/db/twin.pglite $D/twin_W.json && $B leak.ts twin $D/db/twin.pglite $D/twin_W_repeat.json && $B leak.ts secret $D/db/twin.pglite && $B leak.ts twin $D/db/twin.pglite $D/twin_Wp.json; echo "[q] TWIN EXIT=$? $(date +%T)"
cpdb fresh; $B leak.ts cachefresh $D/db/fresh.pglite $D/cachefresh.json; echo "[q] FRESH EXIT=$? $(date +%T)"
cpdb sup; $B supersede_links.ts $D/db/sup.pglite && $B run.ts 1 $D/db/sup.pglite $D/run_suplinks.jsonl search 100 @$D/task_ids_s1_stale_current.txt 0 embed > run_suplinks.log 2>&1; echo "[q] SUP EXIT=$? $(date +%T)"
$B run.ts 1 $D/db/s1.pglite $D/run_keyless.jsonl search 100 @$D/task_ids_keyless.txt 0 keyless > run_keyless2.log 2>&1; echo "[q] KEYLESS EXIT=$? $(date +%T)"
echo "[q] ALLDONE $(date +%T)"
