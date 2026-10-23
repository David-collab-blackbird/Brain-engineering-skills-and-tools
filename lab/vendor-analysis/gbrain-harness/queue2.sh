#!/bin/bash
# Misconfigured-grant leak probes, one identity per process, with peak RSS recorded. Runs after queue.sh finishes.
D=/tmp/claude-0/-home-claude/4c8492a6-f948-5903-9334-5b76eec5c7f7/scratchpad/gbt
cd $D
export GBRAIN_HOME=$D/gbhome HOME=$D/gbhome NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 GBRAIN_QUERY_EMBED_TIMEOUT_MS=30000
until grep -q "ALLDONE" queue.log 2>/dev/null; do sleep 15; done
for id in grant_empty_array grant_default_only no_grant_legacy_floor; do
  IDENTS=$id nice -n 5 /root/.bun/bin/bun --smol run leak.ts probe $D/db/leak.pglite $D/leak_probe_$id.json > leak_$id.log 2>&1; echo "[q2] $id exit=$?"
done
echo "[q2] ALLDONE $(date +%T)"
