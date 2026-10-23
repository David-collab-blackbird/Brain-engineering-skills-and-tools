run() { su postgres -c "psql -At" <<SQL
SET max_parallel_workers_per_gather=0;
$1
SQL
}
echo "### A: owner/superuser bypass? (postgres is superuser -> bypasses even FORCE). Baseline with explicit filter, no RLS role:"
run "EXPLAIN (ANALYZE, COSTS OFF, TIMING ON) SELECT id FROM docs WHERE tenant_id=7 AND tsv @@ to_tsquery('simple','omega & memo');" | grep -E "Scan|Execution|Filter|Recheck"
echo "### B: as role app, RLS current_setting policy, FTS predicate only (ts_match_vq NOT leakproof):"
run "SET app.tenant='7'; SET ROLE app; EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tsv @@ to_tsquery('simple','omega & memo');" | grep -E "Scan|Execution|Filter|Recheck|Rows Removed"
echo "### C: as role app, RLS + explicit tenant filter + FTS:"
run "SET app.tenant='7'; SET ROLE app; EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tenant_id=7 AND tsv @@ to_tsquery('simple','omega & memo');" | grep -E "Scan|Execution|Filter|Recheck|Rows Removed"
echo "### D: as role app, ranking ORDER BY ts_rank LIMIT 10 (FTS scoring path):"
run "SET app.tenant='7'; SET ROLE app; EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tsv @@ to_tsquery('simple','omega') ORDER BY ts_rank(tsv, to_tsquery('simple','omega')) DESC LIMIT 10;" | grep -E "Scan|Execution|Filter|Rows Removed|Sort"
echo "### E: same as D without RLS (superuser) but explicit tenant filter:"
run "EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tenant_id=7 AND tsv @@ to_tsquery('simple','omega') ORDER BY ts_rank(tsv, to_tsquery('simple','omega')) DESC LIMIT 10;" | grep -E "Scan|Execution|Filter|Rows Removed|Sort"
