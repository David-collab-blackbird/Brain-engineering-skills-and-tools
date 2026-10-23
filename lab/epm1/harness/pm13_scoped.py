#!/usr/bin/env python3
"""PM13 free analysis: scoped search vs declared mapping. For each masked (and verbatim) gold request, search only
the procedures filed under the task's declared scope in the 120-library (13 per scope: 5 declared + 8 near-miss)
and in the 40-library (5 per scope), with BM25 and dense bge-small. Declared-mapping delivery is 100% by
construction (oracle scope). Output: materials/pm13_scoped.json. $0, local."""
import json
import math
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, "/home/claude/epm1/harness")
import numpy as np

MAT = "/home/claude/epm1/materials"
LIB = json.load(open(f"{MAT}/library.json"))
TASKS = [t for t in json.load(open(f"{MAT}/tasks.json")) if t["gold"]]
P = {p["slug"]: p for p in LIB["procedures"]}
spec = __import__("importlib.util").util.spec_from_file_location("rt", "/home/claude/epm1/harness/router.py")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 3), round((c + h) / d, 3)]


def main():
    import importlib.util
    s = importlib.util.spec_from_file_location("rt", "/home/claude/epm1/harness/router.py")
    rt = importlib.util.module_from_spec(s)
    s.loader.exec_module(rt)
    from sentence_transformers import SentenceTransformer
    E = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu", cache_folder="/home/claude/models/hf/hub")
    QP = "Represent this sentence for searching relevant passages: "
    out = {}
    for size in ("40", "120"):
        members = LIB["sizes"][size]
        for variant in ("masked", "verbatim"):
            hits = {"bm25": {1: 0, 5: 0}, "dense": {1: 0, 5: 0}}
            ncand = []
            for t in TASKS:
                cands = [x for x in members if P[x]["scopes"][0] == t["scope"]]
                ncand.append(len(cands))
                docs = [rt.doc(P[x]) for x in cands]
                bm = rt.BM25(docs)
                sc = bm.score(t[variant])
                ob = [cands[j] for j in np.argsort(-sc)]
                emb = E.encode([d[:2000] for d in docs], normalize_embeddings=True)
                q = E.encode([QP + t[variant]], normalize_embeddings=True)[0]
                od = [cands[j] for j in np.argsort(-(emb @ q))]
                for name, o in (("bm25", ob), ("dense", od)):
                    for k in (1, 5):
                        hits[name][k] += t["gold"] in o[:k]
            n = len(TASKS)
            out[f"{size}/{variant}"] = {"n": n, "candidates_per_scope_mean": round(sum(ncand) / n, 1),
                                        **{f"{name}_hit{k}": {"k": hits[name][k], "rate": round(hits[name][k] / n, 3), "wilson": wilson(hits[name][k], n)}
                                           for name in hits for k in (1, 5)},
                                        "declared_mapping_delivery": {"k": n, "rate": 1.0, "note": "by construction (oracle scope)"}}
            print(size, variant, json.dumps(out[f"{size}/{variant}"]), flush=True)
    json.dump(out, open(f"{MAT}/pm13_scoped.json", "w"), indent=1)


if __name__ == "__main__":
    main()
