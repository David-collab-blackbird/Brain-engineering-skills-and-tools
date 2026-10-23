"""DA1 / ADR-008: what happens to 'superseded versions indexed as entry points + forward-to-head' when history grows
(3-5 years of connector updates)? Clone B extra superseded versions per key (perturbed value/date, near-duplicate text),
then compare (a) history masked for non-temporal queries (what batch 2 actually ran) vs (b) history indexed + forwarded
(what ADR-008 §7 specifies), at depth 200 -> forward -> top 10. Seed 1, wsum BM25+bge-small a=.2, query-only."""
import sys, copy, random, collections, numpy as np
sys.path.insert(0, "/home/claude/brainbench")
from bb.brain import World, Brain, is_temporal_query
from bb.ctx2 import CLASSES2
from bb.models import Embedder
from bb.retrieval import item_text, minmax, topn

R = random.Random(7)
em = Embedder("bge-small")
base_w = World("/home/claude/brainbench/data_v02/s1")
b0 = Brain(base_w, lsa_dim=16)
E0 = em.docs([item_text(it, True) for it in b0.ix.items], "s1/base")   # cache hit only
tasks = [t for t in base_w.tasks if t["cls"] in CLASSES2]
em.queries(list(dict.fromkeys(t["query"] for t in tasks)))
model = em.model()

def bloat(B):
    w = copy.copy(base_w); w.items = list(base_w.items); w.by_id = dict(base_w.by_id); w.head_of = dict(base_w.head_of)
    new = []
    for k in base_w.keys.values():
        v1 = base_w.by_id[k["versions"][0]]; head = k["versions"][-1]
        for j in range(B):
            it = dict(v1); it["id"] = f"bl_{k['key']}_{j}"
            day = max(0, v1.get("valid_from", 0) - R.randint(30, 1500)); it["created_day"] = it["recorded_day"] = day
            it["superseded_by"] = head
            vs = v1["value_str"]
            if isinstance(v1.get("value"), (int, float)) and not isinstance(v1.get("value"), bool):
                nv = type(v1["value"])(v1["value"] * R.uniform(0.7, 1.3)); vs2 = vs.replace(str(v1["value"]), str(nv))
                if vs2 == vs and vs.startswith("$"): vs2 = "${:,}".format(int(nv))
                it["text"] = v1["text"].replace(vs, vs2)
            new.append(it); w.head_of[it["id"]] = head
    w.items += new
    for it in new: w.by_id[it["id"]] = it
    b = Brain(w, lsa_dim=16)
    V = model.encode([item_text(it, True) for it in new], batch_size=32, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32) if new else np.zeros((0, E0.shape[1]), np.float32)
    return w, b, np.vstack([E0, V])

print("B extra versions/key | arm | " + " ".join(c[:9] for c in CLASSES2) + " | ALL | mean unique items in top10")
for B in (0, 10, 40):
    import gc; gc.collect()
    w, b, E = bloat(B)
    for arm in ("masked (batch-2)", "indexed+forward (ADR-008)"):
        res = collections.defaultdict(list); uniq = []
        for t in tasks:
            temporal = is_temporal_query(t["query"])
            m = b.access(t["requester"]).copy()
            if arm.startswith("masked") and not temporal:
                m &= ~b.is_super
            bm = b.ix.bm25(t["query"], stats_mask=b.access(t["requester"]))
            dv = E @ em.queries([t["query"]])[0]
            s = np.where(m, 0.2 * minmax(bm, m) + 0.8 * minmax(dv, m), -np.inf)
            ranked = b.forward(list(topn(s, np.isfinite(s), 200)), temporal)[:10]
            uniq.append(len(ranked))
            ok = set(t["required"]) <= set(b.ids[i] for i in ranked)
            res[t["cls"]].append(ok); res["ALL"].append(ok)
        print(f"B={B:<3} | {arm:<26} | " + " ".join(f"{100*np.mean(res[c]):8.1f}" for c in CLASSES2) + f" | {100*np.mean(res['ALL']):5.1f} | {np.mean(uniq):.2f}", flush=True)
