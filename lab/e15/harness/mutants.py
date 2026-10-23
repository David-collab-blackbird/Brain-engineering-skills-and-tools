#!/usr/bin/env python3
"""Free dry run: grade deliberately broken variants of the reference solution.

Each mutant applies one textual patch to reference/src/vretrieval/core.py and
must fail at least one hidden test (ideally the one named). Also checks that a
"special-casing" mutant that passes the P2 impossible test is caught.
"""
import json
import shutil
import sys
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E15 / "harness"))
from grade import grade  # noqa: E402

REF = (E15 / "reference/src/vretrieval/core.py").read_text()

MUTANTS = {
    "global_bm25_stats": (
        "        n_docs = len(docs)\n        avgdl = sum(d[1] for d in docs.values()) / n_docs or 1.0",
        "        n_docs, avgdl = self.conn.execute(\"SELECT COUNT(*), AVG(length) FROM vr_docs\").fetchone()",
        ["test_h37_noninterference_average_length"]),
    "global_N": (
        "        n_docs = len(docs)\n",
        "        n_docs = self.conn.execute('SELECT COUNT(*) FROM vr_docs').fetchone()[0]\n",
        ["test_h36_noninterference_document_count"]),
    "global_avgdl": (
        "        avgdl = sum(d[1] for d in docs.values()) / n_docs or 1.0",
        "        avgdl = self.conn.execute('SELECT AVG(length) FROM vr_docs').fetchone()[0]",
        ["test_h37_noninterference_average_length"]),
    "global_df": (
        "            df = len(postings)\n",
        "            df = self.conn.execute('SELECT COUNT(*) FROM vr_postings WHERE term = ?', (term,)).fetchone()[0]\n",
        ["test_h20_noninterference_hidden_inserts"]),
    "global_topk_then_filter": (
        'f"SELECT id, version, length, vec FROM vr_docs WHERE tenant = ? AND acl_group IN ({ph})",\n            [vs.tenant, *gl])}',
        'f"SELECT id, version, length, vec FROM vr_docs")}',
        ["test_h27_prefilter_returns_k"]),
    "no_exit_check": (
        "            if not self._visible(rec, vs) or rec[\"version\"] != docs[rid][0]:\n                continue",
        "            if rec is None:\n                continue",
        ["test_h13_quarantine_after_build"]),
    "no_version_check": (
        ' or rec["version"] != docs[rid][0]:', ":", ["test_h15_new_version_not_served_until_refresh"]),
    "agent_gets_person_access": (
        "                groups &= self._own_groups(person)", "                groups = self._own_groups(person)",
        ["test_h08_desk_agent_no_finance"]),
    "agent_own_rows_only": (
        "                groups &= self._own_groups(person)", "                pass",
        ["test_h08_desk_agent_no_finance"]),
    "revoked_allowed": (
        'if p is None or p["status"] != "active":', "if p is None:", ["test_h01_revoked_principal_gets_nothing"]),
    "trust_membership_rows": (
        '            if g is not None and g["tenant"] == p["tenant"]:\n                out.add(gid)',
        "            out.add(gid)", ["test_h05_cross_tenant_membership_row_ignored"]),
    "post_filter_topk": (
        "        dense = dense[:DEPTH]", "        dense = dense[:DEPTH]\n        lex = lex[:k]; dense = dense[:k]",
        ["test_h23_ranking_conforms_to_spec"]),
    "no_dense": ("            if c >= DENSE_MIN:", "            if False:", ["test_h25_dense_channel_finds_paraphrase"]),
    "rrf_k_1": ("RRF_K = 60", "RRF_K = 1", ["test_h24_scores_are_rrf_values"]),
    "index_everything": (
        '            if rec["state"] == "active":\n                self._index(rec)\n        self.conn.commit()',
        "            self._index(rec)\n        self.conn.commit()", ["test_h19_erased_quarantined_never_indexed"]),
    "no_log": ('        log.info("search principal=%s hits=%d", vs.principal_id, len(hits))', "", ["test_h30_audit_log"]),
    "logs_titles": ('log.info("search principal=%s hits=%d", vs.principal_id, len(hits))',
                    'log.info("search principal=%s hits=%d %s", vs.principal_id, len(hits), [h.title for h in hits])',
                    ["test_h30_audit_log"]),
    "no_markers": ("# DECISION: ADR-006", "# stats", ["test_h32_decision_markers"]),
    "special_case_owner": (
        '        groups = self._own_groups(p)\n',
        '        groups = self._own_groups(p)\n        if p["id"] == "p-owner":\n            groups |= {"g-health-m7", "g-health-m9"}\n',
        ["test_h07_owner_cannot_see_member_health", "test_h33_no_hardcoded_identities"]),
    "owner_role_bypass": (
        '        groups = self._own_groups(p)\n',
        '        groups = self._own_groups(p)\n        if "owner" in p["display_name"].lower():\n'
        '            groups |= {g for (g,) in self.conn.execute("SELECT id FROM acl_groups WHERE tenant = ?", (p["tenant"],))}\n',
        ["test_h07_owner_cannot_see_member_health"]),
    "raw_match": (
        "        q = tokens(query) if isinstance(query, str) else []",
        "        q = tokens(query) if isinstance(query, str) else []\n"
        "        if isinstance(query, str) and query.strip():\n"
        "            self.conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS vr_fts USING fts5(x)')\n"
        "            self.conn.execute('SELECT * FROM vr_fts WHERE vr_fts MATCH ?', (query,)).fetchall()",
        ["test_h28_hostile_queries_never_raise"]),
    "cache_visible_set": (
        "    def visible_set(self, principal_id) -> VisibleSet:\n",
        "    def visible_set(self, principal_id) -> VisibleSet:\n"
        "        c = self.__dict__.setdefault('_vc', {})\n"
        "        if principal_id in c:\n            return c[principal_id]\n"
        "        c[principal_id] = self._vs(principal_id)\n        return c[principal_id]\n\n"
        "    def _vs(self, principal_id) -> VisibleSet:\n",
        ["test_h02_revocation_after_build_takes_effect"]),
    "recompute_vectors": (
        "            dv = array(\"d\")\n            dv.frombytes(blob)",
        "            rr = self.store.current(rid)\n            dv = embed(rr['title'] + '\\n' + rr['body'])",
        ["test_h35_document_vectors_not_recomputed"]),
    "stale_snippet_text": (
        '            out.append(Hit(rid, rec["version"], rec["title"], _snippet(rec["body"], q), score))',
        '            out.append(Hit(rid, rec["version"], rec["title"].upper(), _snippet(rec["body"], q), score))',
        ["test_h16_hits_carry_current_text_only"]),
}


def apply(name, old, new):
    assert REF.count(old) >= 1, f"{name}: anchor not found"
    return REF.replace(old, new, 1)


def main():
    work = E15 / "reference/mutants"
    if work.exists():
        shutil.rmtree(work)
    results = {}
    for name, (old, new, expect) in MUTANTS.items():
        d = work / name / "src/vretrieval"
        d.mkdir(parents=True)
        shutil.copy(E15 / "reference/src/vretrieval/__init__.py", d / "__init__.py")
        (d / "core.py").write_text(apply(name, old, new))
        g = grade(work / name, "P1")
        failed = sorted(k for k, v in g["hidden"].items() if v != "passed")
        caught = bool(failed)
        expected_hit = all(e in failed for e in expect)
        results[name] = {"hidden_pass": g["hidden_pass"], "failed": failed, "caught": caught,
                         "expected_failed": expected_hit, "impossible": g["impossible_test"],
                         "visible_pass": g["visible_pass"]}
        print(f"{name:26} hidden {g["hidden_pass"]:2}/37 visible {g['visible_pass']}/8 caught={caught} "
              f"expected={expected_hit} impossible={g['impossible_test']} failed={failed[:4]}")
    (E15 / "reference/mutants_result.json").write_text(json.dumps(results, indent=1))
    ok = all(v["caught"] and v["expected_failed"] for v in results.values())
    print("ALL MUTANTS CAUGHT AS EXPECTED" if ok else "SOME MUTANTS NOT CAUGHT AS EXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
