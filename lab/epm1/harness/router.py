#!/usr/bin/env python3
"""Free (local, $0) routing analysis for E-PM1 and the arm-D routing table.

System One router = Jeff v1.3 base (Qwen3.5-0.8B decision model, 255-code readout; the best all-round zero-shot
grader in E13a), reused read-only from /home/claude/sysone/scripts/score.py (JeffScorer), fp32 compute with 16-bit
weights (SYSONE_LOWMEM=1), both option orders averaged. Closed choice: the scope's declared procedures (<=5) + "none".
Baselines: BM25 (title+when+body+examples) and dense bge-small-en-v1.5, scoped (declared set) and unscoped (40/120).
Also: Jeff over the unscoped BM25 top-10 of the 40-library + "none" (PM4's <=10-candidate form).

usage: SYSONE_LOWMEM=1 HF_HUB_OFFLINE=1 python3 -I router.py   -> materials/routing.json, materials/routing_analysis.json
Never imports harness/common.py (name clash with sysone's common.py).
"""
import collections
import importlib.util
import json
import math
import os
import re
import sys
import time

os.environ.setdefault("HF_HOME", "/home/claude/models/hf")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("SYSONE_THREADS", "1")
MAT = "/home/claude/epm1/materials"
sys.path.insert(0, "/home/claude/sysone/scripts")
import numpy as np

LIB = json.load(open(f"{MAT}/library.json"))
TASKS = json.load(open(f"{MAT}/tasks.json"))
P = {p["slug"]: p for p in LIB["procedures"]}
BIZ = {"ML": "Marrowbank Landscapes", "CB": "Copperleaf Bakehouse", "TW": "Tidewell Music School", "GRP": "the whole group"}
NONE_OPT = "None of these procedures fits this request"

TOK = re.compile(r"[a-z0-9]+")
STOP = set("the a an and or of to in for on with is are be this that it as by from at use when".split())


def toks(t):
    return [w for w in TOK.findall(t.lower()) if w not in STOP]


class BM25:
    def __init__(s, docs, k1=1.2, b=0.75):
        s.D = [toks(d) for d in docs]
        s.N = len(s.D)
        s.avg = sum(map(len, s.D)) / max(1, s.N)
        s.k1, s.b = k1, b
        s.df = collections.Counter(w for d in s.D for w in set(d))
        s.tf = [collections.Counter(d) for d in s.D]

    def score(s, q):
        out = np.zeros(s.N)
        for w in set(toks(q)):
            if w not in s.df:
                continue
            idf = math.log(1 + (s.N - s.df[w] + 0.5) / (s.df[w] + 0.5))
            for j, tf in enumerate(s.tf):
                f = tf.get(w)
                if f:
                    out[j] += idf * f * (s.k1 + 1) / (f + s.k1 * (1 - s.b + s.b * len(s.D[j]) / s.avg))
        return out


def doc(p):
    return f"{p['title']} {p['when_to_use']} {p['body']} {' '.join(p['example_requests'])}"


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 3), round((c + h) / d, 3)]


def ece(conf, correct, bins=10):
    conf, correct = np.array(conf), np.array(correct, dtype=float)
    e = 0.0
    for i in range(bins):
        m = (conf > i / bins) & (conf <= (i + 1) / bins)
        if m.any():
            e += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(e)


def auroc(score, label):
    s, y = np.array(score), np.array(label)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())


def load_jeff():
    spec = importlib.util.spec_from_file_location("sysone_score", "/home/claude/sysone/scripts/score.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.JeffScorer()


def jeff_choice(J, task, req, cands):
    """Average option probabilities over the given order and its reverse. cands: list of slugs; last option = none."""
    state = f"Request from the {task['frm']} (declared scope {task['scope']}, business: {BIZ[task['business']]}):\n{req}"
    q = "Which one of the business's procedures should be followed for this request?"
    opts = [(f"{P[s]['title']}", P[s]["when_to_use"]) for s in cands] + [("None", NONE_OPT)]
    k = len(opts)
    prob = np.zeros(k)
    for order in (list(range(k)), list(reversed(range(k)))):
        row = {"state": state, "question": q, "qtype": "choice", "options": [opts[i] for i in order]}
        z = J([row])[0][0]
        e = np.exp(z - z.max())
        pr = e / e.sum()
        for pos, i in enumerate(order):
            prob[i] += pr[pos] / 2
    keys = cands + [None]
    return keys[int(prob.argmax())], {str(kk): round(float(v), 4) for kk, v in zip(keys, prob)}


def main():
    t0 = time.time()
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(1)
    E = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu", cache_folder="/home/claude/models/hf/hub")
    QP = "Represent this sentence for searching relevant passages: "
    libs = {s: [P[x] for x in LIB["sizes"][s]] for s in ("40", "120")}
    bm = {s: BM25([doc(p) for p in libs[s]]) for s in libs}
    emb = {s: E.encode([doc(p)[:2000] for p in libs[s]], normalize_embeddings=True, batch_size=16) for s in libs}
    J = load_jeff()
    print(f"models loaded in {time.time() - t0:.0f}s", flush=True)
    rows = []
    routing = {"40": {}}
    cache_p = f"{MAT}/router_cache.json"
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}

    def cached(key, fn):
        if key not in cache:
            cache[key] = fn()
            json.dump(cache, open(cache_p, "w"))
        return cache[key]
    # pass 1 (needed by arm D): masked request, closed choice among the declared set + none
    for t in TASKS:
        decl = LIB["declared"]["40"][t["scope"]]
        ch, pr = cached(f"{t['id']}|masked|scoped", lambda: jeff_choice(J, t, t["masked"], decl))
        routing["40"][t["id"]] = {"push": ch, "probs": pr, "declared": decl}
        print(f"pass1 {t['id']}: gold={t['gold']} s1={ch} ({time.time() - t0:.0f}s)", flush=True)
    json.dump(routing, open(f"{MAT}/routing.json", "w"), indent=1)
    print("routing.json written (masked)", flush=True)
    # pass 1H (amendment 1): the hardened request variants, same method
    if os.path.exists(f"{MAT}/tasks_h.json"):
        routing["40H"] = {}
        for t in json.load(open(f"{MAT}/tasks_h.json")):
            decl = LIB["declared"]["40"][t["scope"]]
            ch, pr = cached(f"{t['id']}|masked|scoped", lambda: jeff_choice(J, t, t["masked"], decl))
            routing["40H"][t["id"]] = {"push": ch, "probs": pr, "declared": decl}
            print(f"pass1H {t['id']}: gold={t['gold']} s1={ch} ({time.time() - t0:.0f}s)", flush=True)
        json.dump(routing, open(f"{MAT}/routing.json", "w"), indent=1)
        print("routing.json written (masked + H)", flush=True)
    # pass 2: everything else for the free analysis
    for t in TASKS:
        for variant in ("masked", "verbatim"):
            req = t[variant]
            decl = LIB["declared"]["40"][t["scope"]]
            r = {"task": t["id"], "gold": t["gold"], "variant": variant, "scope": t["scope"]}
            for s in ("40", "120"):
                sc = bm[s].score(req)
                order = [libs[s][j]["slug"] for j in np.argsort(-sc)]
                r[f"bm25_{s}_top"] = order[:10]
                r[f"bm25_{s}_topscore"] = float(sc.max())
                qe = E.encode([QP + req], normalize_embeddings=True)[0]
                ds = emb[s] @ qe
                r[f"dense_{s}_top"] = [libs[s][j]["slug"] for j in np.argsort(-ds)][:10]
            idx40 = {p["slug"]: j for j, p in enumerate(libs["40"])}
            sc40 = bm["40"].score(req)
            r["bm25_scoped_top"] = sorted(decl, key=lambda x: -sc40[idx40[x]])
            qe = E.encode([QP + req], normalize_embeddings=True)[0]
            r["dense_scoped_top"] = sorted(decl, key=lambda x: -float(emb["40"][idx40[x]] @ qe))
            ch, pr = cached(f"{t['id']}|{variant}|scoped", lambda: jeff_choice(J, t, req, decl))
            r["s1_scoped_choice"], r["s1_scoped_probs"] = ch, pr
            if variant == "masked":
                top10 = r["bm25_40_top"][:10]
                ch10, pr10 = cached(f"{t['id']}|masked|top10", lambda: jeff_choice(J, t, req, top10))
                r["s1_top10_choice"], r["s1_top10_probs"] = ch10, pr10
            rows.append(r)
            print(f"pass2 {t['id']} {variant}: gold={t['gold']} s1={r['s1_scoped_choice']} bm25s={r['bm25_scoped_top'][0]} ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- analysis
    an = {}
    for variant in ("masked", "verbatim"):
        R = [r for r in rows if r["variant"] == variant]
        G = [r for r in R if r["gold"]]
        n = len(G)
        res = {"n_gold": n, "n_none": len(R) - n}

        def hit(key, k):
            c = sum(1 for r in G if r["gold"] in r[key][:k])
            return {"k": c, "n": n, "rate": round(c / n, 3), "wilson": wilson(c, n)}
        for key in ("bm25_40_top", "bm25_120_top", "dense_40_top", "dense_120_top", "bm25_scoped_top", "dense_scoped_top"):
            res[key] = {"hit1": hit(key, 1), "hit5": hit(key, 5)}
        c = sum(1 for r in G if r["s1_scoped_choice"] == r["gold"])
        res["s1_scoped_hit1"] = {"k": c, "n": n, "rate": round(c / n, 3), "wilson": wilson(c, n)}
        cn = sum(1 for r in R if not r["gold"] and r["s1_scoped_choice"] is None)
        res["s1_scoped_none_correct"] = {"k": cn, "n": len(R) - n}
        allc = sum(1 for r in R if r["s1_scoped_choice"] == r["gold"])
        res["s1_scoped_overall_acc"] = {"k": allc, "n": len(R), "rate": round(allc / len(R), 3), "wilson": wilson(allc, len(R))}
        conf = [max(r["s1_scoped_probs"].values()) for r in R]
        corr = [r["s1_scoped_choice"] == r["gold"] for r in R]
        res["s1_scoped_ece"] = round(ece(conf, corr), 4)
        res["s1_abstain_auc"] = auroc([1 - r["s1_scoped_probs"]["None"] for r in R], [1 if r["gold"] else 0 for r in R])
        res["bm25_abstain_auc"] = auroc([r["bm25_40_topscore"] for r in R], [1 if r["gold"] else 0 for r in R])
        # McNemar S1 vs BM25 scoped (Hit@1, gold tasks)
        a = [r["s1_scoped_choice"] == r["gold"] for r in G]
        b = [r["bm25_scoped_top"][0] == r["gold"] for r in G]
        b01 = sum(1 for x, y in zip(a, b) if not x and y)
        b10 = sum(1 for x, y in zip(a, b) if x and not y)
        nn = b01 + b10
        p = min(1.0, 2 * sum(math.comb(nn, i) for i in range(0, min(b01, b10) + 1)) / 2 ** nn) if nn else 1.0
        res["mcnemar_s1_vs_bm25_scoped"] = {"s1_only": b10, "bm25_only": b01, "p_exact": round(p, 4)}
        if variant == "masked":
            c10 = sum(1 for r in G if r["s1_top10_choice"] == r["gold"])
            res["s1_top10_hit1"] = {"k": c10, "n": n, "rate": round(c10 / n, 3), "wilson": wilson(c10, n)}
            res["s1_top10_none_correct"] = sum(1 for r in R if not r["gold"] and r["s1_top10_choice"] is None)
        res["declared_mapping_delivery"] = {"k": n, "n": n, "note": "oracle scope: gold is in the declared set by construction"}
        an[variant] = res
    an["elapsed_s"] = round(time.time() - t0)
    an["rows"] = rows
    json.dump(an, open(f"{MAT}/routing_analysis.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in an.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
