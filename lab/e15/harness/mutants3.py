#!/usr/bin/env python3
"""Free dry run for P3: broken variants of reference3 must each fail >= 1 hidden test (incl. the targeted one)."""
import json
import shutil
import sys
from pathlib import Path

E15 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E15 / "harness"))
from grade import grade  # noqa: E402

REF = (E15 / "reference3/src/cards/core.py").read_text()
M = {
    "merge_groups_one_card": (
        '            if g not in vs.groups:                # DECISION: ADR-007 card ACL\n                continue',
        '            pass', ["test_h07_two_cards_two_groups"]),
    "agent_full_delegation": ("                groups &= self._own(person)", "                groups = self._own(person)",
                              ["test_h05_agent_intersection"]),
    "revoked_allowed": ('if p is None or p["status"] != "active":', "if p is None:", ["test_h01_revoked_and_unknown"]),
    "trust_rows": ('            if g is not None and g["tenant"] == p["tenant"]:\n                out.add(gid)',
                   "            out.add(gid)", ["test_h03_ghost_and_cross_tenant_rows"]),
    "leak_hidden_head": ('            if h is not None and h["acl_group"] in vs.groups:', "            if h is not None:",
                         ["test_h26_forward_hidden_head_redacted"]),
    "no_forwarding": ("            if f is None or f[\"superseded_by\"] is None:\n                continue",
                      "            continue", ["test_h25_forward_visible_head"]),
    "global_bm25": ('        notes = [n for n in self.store.notes()\n                 if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]',
                    '        allnotes = [n for n in self.store.notes() if n["state"] == "active"]\n        notes = allnotes',
                    ["test_h30_noninterference_hidden_notes"]),
    "no_recompile_on_upsert": ("            for e, g in sorted(touched):\n                self._write_card(e, g)", "            pass",
                               ["test_h12_upsert_supersedes"]),
    "recompile_new_group_only": ("                touched.add((old[\"entity_id\"], old[\"acl_group\"]))", "                pass",
                                 ["test_h13_upsert_group_move"]),
    "no_noop": ("            if old is not None and old[\"value\"] == value", "            if False and old[\"value\"] == value",
                ["test_h11_upsert_noop"]),
    "cap_ignored": ("                if len(items) < min(MAX_CARDS, k):", "                if len(items) < k:",
                    ["test_h20_cap_three_cards_in_order"]),
    "shorter_alias_also_links": ("            if any(not (t <= a or s >= b) and eid != oe for a, b, oe in taken):\n                continue",
                                 "            pass", ["test_h18_longest_alias_wins"]),
    "link_other_tenant": ("            if e[\"tenant\"] != tenant:\n                continue", "            pass",
                          ["test_h19_tenant_scoped_linking"]),
    "unsorted_aliases": ('        al = sorted(self.store.aliases(entity_id))', '        al = list(reversed(self.store.aliases(entity_id)))',
                         ["test_h06_card_text_exact_all"]),
    "no_card_exit_check": ("            if ok and ids:", "            if ids:", ["test_h39_card_exit_check_on_external_change"]),
    "default_k_8": ("    def assemble(self, request, principal_id, k=10):", "    def assemble(self, request, principal_id, k=8):",
                    ["test_h34_default_k_is_ten"]),
    "owner_bypass": ('        groups = self._own(p)\n', '        groups = self._own(p)\n        if "owner" in p["display_name"].lower():\n'
                     '            groups |= {g for (g,) in self.conn.execute("SELECT id FROM acl_groups WHERE tenant = ?", (p["tenant"],))}\n',
                     ["test_h04_owner_no_member_health"]),
    "special_case_owner": ('        groups = self._own(p)\n', '        groups = self._own(p)\n        if p["id"] == "p-owner":\n            groups.add("g-health-m7")\n',
                           ["test_h04_owner_no_member_health", "test_h37_no_hardcoded_ids"]),
    "no_atomic_upsert": ("        with self.store.transaction():\n            old = self.store.head(",
                         "        if True:\n            old = self.store.head(", ["test_h16_upsert_atomic"]),
    "include_inactive_notes": ('if n["state"] == "active" and n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]',
                               'if n["tenant"] == vs.tenant and n["acl_group"] in vs.groups]', ["test_h40_inactive_notes_not_in_statistics"]),
}


def main():
    work = E15 / "reference3/mutants"
    if work.exists():
        shutil.rmtree(work)
    res = {}
    for name, (old, new, exp) in M.items():
        assert old in REF, f"{name}: anchor not found"
        d = work / name / "src/cards"
        d.mkdir(parents=True)
        shutil.copy(E15 / "reference3/src/cards/__init__.py", d / "__init__.py")
        (d / "core.py").write_text(REF.replace(old, new, 1))
        g = grade(work / name, "P3")
        failed = sorted(k for k, v in g["hidden"].items() if v != "passed")
        ok = bool(failed) and all(e in failed for e in exp)
        res[name] = {"failed": failed, "ok": ok, "impossible": g["impossible_test"], "visible": g["visible_pass"]}
        print(f"{name:26} hidden {g["hidden_pass"]:2}/40 visible {g['visible_pass']}/8 ok={ok} imp={g['impossible_test']} {failed[:4]}")
    (E15 / "reference3/mutants_result.json").write_text(json.dumps(res, indent=1))
    allok = all(v["ok"] for v in res.values())
    print("ALL MUTANTS CAUGHT AS EXPECTED" if allok else "SOME MUTANTS NOT CAUGHT AS EXPECTED")


if __name__ == "__main__":
    main()
