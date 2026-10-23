#!/bin/bash
# Stronger twin-world: W_a = s1 + ANALYZE (observe x2), W'_a = W_a + 200 hidden owner notes + ANALYZE (observe). Cache off in twin phase.
D=/tmp/claude-0/-home-claude/4c8492a6-f948-5903-9334-5b76eec5c7f7/scratchpad/gbt
cd $D
export GBRAIN_HOME=$D/gbhome HOME=$D/gbhome NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 GBRAIN_QUERY_EMBED_TIMEOUT_MS=30000
B="nice -n 5 /root/.bun/bin/bun --smol run"
until grep -q "ALLDONE" queue2.log 2>/dev/null; do sleep 15; done
rm -rf db/twin2.pglite db/twin2.pglite.gbrain-owner.json; cp -a db/s1.pglite db/twin2.pglite; cp db/s1.pglite.gbrain-owner.json db/twin2.pglite.gbrain-owner.json
$B leak.ts analyze $D/db/twin2.pglite
$B leak.ts twin $D/db/twin2.pglite $D/twin2_W.json && $B leak.ts twin $D/db/twin2.pglite $D/twin2_W_repeat.json && $B leak.ts secret200 $D/db/twin2.pglite && $B leak.ts twin $D/db/twin2.pglite $D/twin2_Wp.json
echo "[q3] TWIN2 EXIT=$? $(date +%T)"
echo "[q3] ALLDONE $(date +%T)"
