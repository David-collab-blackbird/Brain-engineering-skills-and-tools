run() { su postgres -c "psql -At" <<SQL
SET max_parallel_workers_per_gather=0;
$1
SQL
}
TOK=$(su postgres -c "psql -Atc \"select md5('507'::text)\"")   # doc g=507 -> tenant (507%100)+1 = 8
echo "rare token $TOK (1 doc, tenant 8)"
echo "### F: superuser, no tenant filter, rare token (GIN):"
run "EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tsv @@ to_tsquery('simple','$TOK');" | grep -E "Scan|Execution|Rows Removed"
echo "### G: role app (RLS tenant=8), rare token, no explicit tenant filter:"
run "SET app.tenant='8'; SET ROLE app; EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tsv @@ to_tsquery('simple','$TOK');" | grep -E "Scan|Execution|Rows Removed|Filter"
echo "### H: role app, policy variant using (select current_setting(...)) initplan:"
run "ALTER POLICY p_setting ON docs USING (tenant_id = (select current_setting('app.tenant')::int));" >/dev/null
run "SET app.tenant='8'; SET ROLE app; EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tsv @@ to_tsquery('simple','$TOK');" | grep -E "Scan|Execution|Rows Removed|Filter|InitPlan"
echo "### I: same, 5 repeated timings (ms) RLS vs superuser+explicit filter:"
for i in 1 2 3; do
 run "SET app.tenant='8'; SET ROLE app; EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tsv @@ to_tsquery('simple','$TOK');" | grep Execution
 run "EXPLAIN (ANALYZE, COSTS OFF) SELECT id FROM docs WHERE tenant_id=8 AND tsv @@ to_tsquery('simple','$TOK');" | grep Execution
done
run "ALTER POLICY p_setting ON docs USING (tenant_id = current_setting('app.tenant')::int);" >/dev/null
