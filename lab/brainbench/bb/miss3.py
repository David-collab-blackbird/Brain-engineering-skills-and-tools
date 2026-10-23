"""Miss attribution for the A3 pipeline (seed-level): for every VITAL item missing from the context at K=50, why?
  vocab      the request names its entity in a form the linker cannot resolve (held-out nickname/descriptor) and no other entity linked
  unlinked   the item is not linked (by the gate) to any entity the query linked, and not to their registry parents
  parent     the item is linked only to a parent of a query-linked entity (portfolio/company)
  budget     the item IS linked to a query-linked entity (or is on a linked card) but ranked below K
  card_miss  a keyed fact whose value the store does not state correctly (extraction miss) and that search did not find
"""
from __future__ import annotations

from collections import Counter

from .exp3 import alias_table, load_gate_obj
from .pipe3 import TARGET5, Brain3, World3


def attribute(seed, gate_name="gate_haiku", K=50, classes=TARGET5):
    w = World3(seed)
    g = load_gate_obj(w, gate_name)
    b = Brain3(w, g, alias_table=alias_table(g))
    arm = dict(prefix="router", nbhd=True, nbhd_router=True, typed_first=True)
    cnt, per_cls = Counter(), {c: Counter() for c in classes}
    for t in w.tasks:
        if t["cls"] not in classes:
            continue
        ctx = b.assemble(t, arm)
        got = set()
        for p in ctx[:K]:
            did = b.ix.ids[p]
            got.add(did); got |= b.card_cover.get(did, set())
        vis = w.visible(t["requester"])
        ents = set(b.link_query(t["query"], t["requester"], vis))
        pents = {p for e in ents for p in b.parents_of(e)}
        for v in t["vital"]:
            if v in got:
                cnt["found"] += 1; per_cls[t["cls"]]["found"] += 1
                continue
            it = w.by_id[v]
            lk = set(b.links.get(v, []))
            if it.get("connector") or w.gold[v].get("extract_only"):
                card = any(v in b.card_cover.get(cid, set()) for e in ents for cid in b.card_of.get(e, []))
                if card:
                    why = "budget"
                elif it.get("connector") and it["connector"]["entity_id"] in ents:
                    why = "budget"
                elif w.gold[v].get("extract_only") and not any(v in s for s in b.card_cover.values()):
                    why = "card_miss" if (lk & ents) else ("vocab" if (not ents and t.get("ref_form") in ("heldout_nick", "heldout_desc", "seen")) else "unlinked")
                else:
                    why = "vocab" if (not ents and t.get("ref_form") in ("heldout_nick", "heldout_desc", "seen")) else "unlinked"
            elif lk & ents:
                why = "budget"
            elif not ents and t.get("ref_form") in ("heldout_nick", "heldout_desc", "seen"):
                why = "vocab"
            elif lk & pents:
                why = "parent"
            else:
                why = "unlinked"
            cnt[why] += 1; per_cls[t["cls"]][why] += 1
    return cnt, per_cls


if __name__ == "__main__":
    import sys
    c, pc = attribute(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    tot = sum(v for k, v in c.items() if k != "found")
    print("missing vital items:", tot, {k: f"{v} ({100 * v / max(1, tot):.0f}%)" for k, v in c.items() if k != "found"}, "found", c["found"])
    for cl, cc in pc.items():
        t2 = sum(v for k, v in cc.items() if k != "found")
        print(" ", cl, {k: f"{100 * v / max(1, t2):.0f}%" for k, v in cc.items() if k != "found"}, "missing", t2, "found", cc["found"])
