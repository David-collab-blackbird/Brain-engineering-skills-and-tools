"""Batch 2 runner: BrainBench v0.2 + E8 (real retrieval / reranking / batch-1 arms), E6 (decomposition, gap-check),
N4 (entity linkers), M1, H13-lite. Batch 1 (run_all.py, data/, results/) is untouched.

    python run_batch2.py                         # everything (several hours on 2 CPUs; model calls are cached)
    python run_batch2.py --stages e8a,report     # selected stages
Stages: gen, embed, e8a, e8b, e8c, e8d, e8e, e6, n4, h13, h11, i2, report. Intermediate rows: results_v02/<stage>.pkl.
Model caches: cache_v02/. Sub-sampling sizes are set in CONFIG below and reported in the tables.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bb.common import ROOT  # noqa: E402

OUT = os.path.join(ROOT, "results_v02")
SEEDS = (1, 2, 3)
CONFIG = dict(
    rerank_sets_per_class={1: 40, 2: 15, 3: 10},   # stratified distinct sets per class for reranking (CPU budget; host lost bf16 after seed 1)
    rerank_depth=50,
    e6_sets_per_class=40,                         # model-free E6 arms, all seeds (complex classes only)
    e6_llm_seeds=(1,), e6_llm_sets_per_class=12,  # LLM arms (decomposition, gap-check): seed 1 only (CPU budget after host lost bf16)
    e6_rerank=False, e6_rerank_depth=20, e6_reranker="mxbai-rerank-base-v2",  # off: OOM under shared-container memory pressure  # reranking of decomposition / gap pools (fastest LLM reranker in fp32)
    n4_seeds=(1, 2), n4_sets_per_class=20, n4_llm_seeds=(1,), n4_llm_sets_per_class=6,
    llm="Qwen/Qwen3-1.7B",
    tune_seed=1,                                  # weighted-fusion alpha tuned here; seeds 2-3 are held out
    i2_seeds=(1,), i2_groups=8,                   # LLM-written-card kill test (CPU budget)
    h13_seeds=(1,), h13_sets=16,  # multimodal distinct sets; LLM expansion (first stage = best hybrid)
)


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".pkl"), "wb") as f:
        pickle.dump(obj, f)


def load(name):
    p = os.path.join(OUT, name + ".pkl")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


_ctx = {}


def done_seeds(name, key="rows"):
    """Seeds already completed by a previous (interrupted) run of a stage, from its checkpoint pickle."""
    d = load(name)
    return (d or {}).get(key, {}) if d else {}


def ctx(seed, extra_emb=(), lsa=True):
    from bb.ctx2 import Ctx
    key = (seed, lsa)
    if key not in _ctx:
        _ctx.clear(); gc.collect()
        _ctx[key] = Ctx(seed, lsa=lsa)
    seed = key
    for e in extra_emb:
        if e not in _ctx[seed].emb:
            _ctx[seed].add_embedder(e)
    return _ctx[seed]


def stage_gen():
    from bb import world2
    for s in SEEDS:
        g = world2.main(s)
        print(f"[gen] seed {s}: {len(g.items)} items, {len(g.tasks)} tasks")


def stage_embed():
    from bb import models
    for s in SEEDS:
        c = ctx(s, ("qwen3-emb-task",))
        c.noorig("bge-small"); c.noorig("qwen3-emb")
    models.save_timing()


def best_first_stage(e8a):
    """Pick the first stage for reranking / arms from the TUNING seed only."""
    import numpy as np
    cand = [k for k in e8a[CONFIG["tune_seed"]] if not k.endswith("#secs") and k.startswith(("rrf", "wsum"))]
    sc = {k: np.mean([r["ok@10"] for r in e8a[CONFIG["tune_seed"]][k]]) + np.mean([r["rec@10"] for r in e8a[CONFIG["tune_seed"]][k]]) for k in cand}
    return max(sc, key=sc.get), sc


def first_stage_searcher(c, name, alpha):
    emb = name.split("(")[1].split(")")[0].split("+")[1].strip()
    if name.startswith("rrf"):
        return c.searcher("rrf", emb)
    return c.searcher("wsum", emb, alpha=alpha[emb])


def stage_e8a():
    from bb import experiments2 as X
    from bb import models
    res, meta = {}, {}
    c1 = ctx(CONFIG["tune_seed"], ("qwen3-emb-task",))
    alpha = {}
    for emb in ("bge-small", "qwen3-emb"):
        a, grid = X.tune_alpha(c1, emb)
        alpha[emb] = a
        meta[f"alpha_grid_{emb}"] = grid
    meta["alpha"] = alpha
    print("[e8a] tuned alpha", alpha)
    for s in SEEDS:
        c = ctx(s, ("qwen3-emb-task",))
        methods = {"BM25": c.searcher("bm25"), "LSA-256 (batch-1 proxy)": c.searcher("lsa"), "RRF(BM25+LSA) (batch-1 default)": c.searcher("rrf-lsa"),
                   "bge-small": c.searcher("dense", "bge-small"), "Qwen3-Emb-0.6B": c.searcher("dense", "qwen3-emb"),
                   "Qwen3-Emb-0.6B, task instruction": c.searcher("dense", "qwen3-emb-task"),
                   "rrf(BM25+bge-small)": c.searcher("rrf", "bge-small"), "rrf(BM25+qwen3-emb)": c.searcher("rrf", "qwen3-emb"),
                   "wsum(BM25+bge-small)": c.searcher("wsum", "bge-small", alpha=alpha["bge-small"]), "wsum(BM25+qwen3-emb)": c.searcher("wsum", "qwen3-emb", alpha=alpha["qwen3-emb"])}
        t0 = time.time()
        res[s] = X.e8_retrievers(c, methods)
        print(f"[e8a] seed {s} {time.time()-t0:.0f}s")
        models.save_timing()
    meta["best"], meta["best_scores"] = best_first_stage(res)
    print("[e8a] best first stage (tuning seed):", meta["best"])
    save("e8a", dict(rows=res, meta=meta))


def stage_e8b():
    from bb import experiments2 as X
    from bb import models
    e8a = load("e8a")
    best, alpha = e8a["meta"]["best"], e8a["meta"]["alpha"]
    out = dict(done_seeds("e8b"))
    for s in SEEDS:
        if s in out and "qwen3-reranker" in out[s]:
            print(f"[e8b] seed {s} already done (checkpoint)", flush=True)
            continue
        c = ctx(s)
        fs = first_stage_searcher(c, best, alpha)
        tasks = X.subsample(c, CONFIG["rerank_sets_per_class"][s])
        fs.prefetch([t["query"] for t in tasks])
        names = ["bge-reranker-v2-m3", "mxbai-rerank-base-v2", "qwen3-reranker"]
        variants = {}
        if s == 1:   # H12 instruction variants: seed 1 only (CPU budget)
            variants["qwen3-reranker + scope-templated instruction (H12)"] = ("qwen3-reranker", X.scope_instruction)
            variants["mxbai-rerank-base-v2 + scope-templated instruction"] = ("mxbai-rerank-base-v2", X.scope_instruction)
        res = {}
        for n in names:   # one model in memory at a time
            rr = models.Reranker(n)
            vv = {k: v for k, v in variants.items() if v[0] == n}
            r = X.e8_rerank(c, fs, tasks, {n: rr}, depth=CONFIG["rerank_depth"], variants=vv)
            res.update(r)
            rr.save(); del rr; gc.collect()
            models.save_timing()
            print(f"[e8b] seed {s} {n} done", flush=True)
        out[s] = res
        save("e8b", dict(rows=out, first_stage=best))
    save("e8b", dict(rows=out, first_stage=best))


def first_stage_cfg():
    e8a = load("e8a")
    best = e8a["meta"]["best"]
    method = "rrf" if best.startswith("rrf") else "wsum"
    emb = "qwen3-emb" if "qwen" in best else "bge-small"
    return method, emb, e8a["meta"]["alpha"].get(emb, 0.5)


def stage_e8c():
    from bb import experiments2 as X
    method, emb, alpha = first_stage_cfg()
    out, orig, lsa = {}, {}, {}
    for s in SEEDS:
        c = ctx(s)
        out[s], _ = X.e8_arms(c, method, emb, alpha)
        orig[s] = X.e8_origin(c, emb, alpha)
        lsa[s], _ = X.e8_arms(c, "rrf-lsa", None, ksweep=False)   # batch-1 retriever, same arms, same tasks
        print(f"[e8c] seed {s} done", flush=True)
    save("e8c", dict(rows=out, origin=orig, lsa_rows=lsa, first_stage=f"{method}/{emb}/alpha={alpha}"))


def stage_e6():
    """Model-free arms (one-shot, deterministic facets, embedder swaps, +cards/slots) on all seeds; LLM arms
    (decomposition, gap-check, + rerank) on CONFIG['e6_llm_seeds']. Checkpointed per seed and per part."""
    from bb import experiments2 as X
    from bb import models
    from bb.ctx2 import COMPLEX
    method, emb, alpha = first_stage_cfg()
    al = load("e8a")["meta"]["alpha"]
    st = load("e6") or {}
    st.setdefault("nonllm", {}); st.setdefault("rows", {}); st.setdefault("stats", {}); st.setdefault("examples", {})
    for s in SEEDS:
        if s in st["nonllm"]:
            continue
        c = ctx(s)
        A = X.Assembler(c, method, emb, alpha)
        tasks = X.subsample(c, CONFIG["e6_sets_per_class"], classes=COMPLEX)
        A.prefetch(tasks)
        swaps = {"one-shot, LSA (batch-1 rrf)": c.searcher("rrf-lsa"), "one-shot, BM25 only": c.searcher("bm25"),
                 "one-shot, bge-small dense": c.searcher("dense", "bge-small"), "one-shot, Qwen3-Emb dense": c.searcher("dense", "qwen3-emb"),
                 "one-shot, wsum BM25+Qwen3-Emb": c.searcher("wsum", "qwen3-emb", alpha=al["qwen3-emb"])}
        st["nonllm"][s] = X.e6_nonllm(c, A, tasks, swaps)
        save("e6", st)
        print(f"[e6] seed {s} model-free arms done", flush=True)
    for s in CONFIG["e6_llm_seeds"]:
        if s in st["rows"]:
            continue
        models.free_models()
        c = ctx(s, lsa=False)
        A = X.Assembler(c, method, emb, alpha)
        tasks = X.subsample(c, CONFIG["e6_llm_sets_per_class"], classes=COMPLEX)
        A.prefetch(tasks)
        llm = models.LLM(CONFIG["llm"])
        swaps = {"one-shot, bge-small dense": c.searcher("dense", "bge-small"), "one-shot, Qwen3-Emb dense": c.searcher("dense", "qwen3-emb"),
                 "one-shot, BM25 only": c.searcher("bm25"), "one-shot, wsum BM25+Qwen3-Emb": c.searcher("wsum", "qwen3-emb", alpha=al["qwen3-emb"])}
        r, stt, exm = X.e6_decomposition(c, A, llm, tasks, reranker=None)
        for name, ss in swaps.items():
            ss.prefetch([t["query"] for t in tasks])
            r[name] = X.tag([X.row(t, X.ids_of(c.b, X.query_ranked(c.b, ss, t, n=30)), ks=(10, 20)) for t in tasks], seed=s, arm=name)
        llm._m = None; gc.collect(); models.free_models()
        st["rows"][s], st["stats"][s], st["examples"][s] = r, stt, exm
        save("e6", st)
        print(f"[e6] seed {s} LLM arms done", flush=True)
        if not CONFIG.get("e6_rerank", True):
            continue
        # rerank the one-shot / decomposition / gap pools with a reranker (optional: CONFIG['e6_rerank'])
        bestrr = CONFIG["e6_reranker"]
        rr = models.Reranker(bestrr)
        r2, _, _ = X.e6_decomposition(c, A, llm, tasks, reranker=rr, rr_depth=CONFIG["e6_rerank_depth"])   # LLM outputs come from cache
        for k in r2:
            if "rerank" in k:
                st["rows"][s][k + f" ({bestrr}, top-{CONFIG['e6_rerank_depth']})"] = r2[k]
        rr.save(); del rr; gc.collect()
        save("e6", st)
        print(f"[e6] seed {s} reranked arms done", flush=True)
        models.save_timing()


def stage_n4():
    from bb import experiments2 as X
    from bb import models
    method, emb, alpha = first_stage_cfg()
    prev = load("n4") or {}
    out, stats = dict(prev.get("res", {})), dict(prev.get("stats", {}))
    for s in CONFIG["n4_seeds"]:
        if s in out:
            print(f"[n4] seed {s} already done (checkpoint)", flush=True)
            continue
        c = ctx(s, lsa=False)
        A = X.Assembler(c, method, emb, alpha)
        tasks = X.subsample(c, CONFIG["n4_sets_per_class"])
        A.prefetch(tasks)
        linkers, info = X.make_linkers(c)
        llm_tasks = X.subsample(c, CONFIG["n4_llm_sets_per_class"])
        for t in tasks + llm_tasks:
            info["emb_top"](t, 1)          # warm the query-embedding cache, then drop the embedding model
        A.prefetch(llm_tasks)
        models.free_models()
        llm = models.LLM(CONFIG["llm"]) if s in CONFIG["n4_llm_seeds"] else None
        if llm:   # first the cheap linkers on the full subsample, then all linkers incl. LLM on a smaller one
            res0, _ = X.n4_linkers(c, A, linkers, info, tasks, llm=None)
            res1, st1 = X.n4_linkers(c, A, linkers, info, tasks, llm=llm, llm_tasks=llm_tasks)
            out[s] = res0
            for k, v in res1.items():
                out[s][k + " [LLM subsample]" if k in res0 else k] = v
            stats[s] = st1
        else:
            out[s], stats[s] = X.n4_linkers(c, A, linkers, info, tasks, llm=None)
        if llm:
            llm._m = None
        gc.collect()
        models.save_timing()
        print(f"[n4] seed {s} done", flush=True)
        save("n4", dict(res=out, stats=stats))


def stage_h13():
    from bb import experiments2 as X
    from bb import models
    method, emb, alpha = first_stage_cfg()
    prev = load("h13") or {}
    out, stats = dict(prev.get("rows", {})), dict(prev.get("stats", {}))
    for s in CONFIG["h13_seeds"]:
        if s in out:
            continue
        models.free_models()
        c = ctx(s, lsa=False)
        llm = models.LLM(CONFIG["llm"])
        out[s], stats[s] = X.h13_lite(c, llm, method, emb, alpha, n_sets=CONFIG["h13_sets"])
        llm._m = None; gc.collect()
        models.save_timing()
        save("h13", dict(rows=out, stats=stats))
        print(f"[h13] seed {s} done", flush=True)


def stage_e8d():
    from bb import experiments2 as X
    method, emb, alpha = first_stage_cfg()
    out, acc = {}, {}
    for s in SEEDS:
        c = ctx(s)
        out[s], acc[s] = X.e8_router(c, method, emb, alpha)
        print(f"[e8d] seed {s} done", flush=True)
    save("e8d", dict(rows=out, routing=acc))


def stage_h11():
    from bb import h11
    from bb import experiments2 as X
    method, emb, alpha = first_stage_cfg()
    prev = load("h11") or {}
    out, stats = dict(prev.get("rows", {})), dict(prev.get("stats", {}))
    for s in SEEDS:
        if s in out:
            continue
        c = ctx(s)
        out[s], stats[s] = h11.run(c, c.searcher(method, emb, alpha=alpha))
        print(f"[h11] seed {s}", stats[s], flush=True)
        save("h11", dict(rows=out, stats=stats))


def stage_i2():
    from bb import i2cards, models
    prev = load("i2") or {}
    out, ex = dict(prev.get("rows", {})), dict(prev.get("examples", {}))
    for s in CONFIG["i2_seeds"]:
        if s in out:
            continue
        from bb.brain import World
        from bb.ctx2 import DATA2
        _ctx.clear(); models.free_models()
        w = World(os.path.join(DATA2, f"s{s}"))
        llm = models.LLM(CONFIG["llm"])
        out[s], ex[s] = i2cards.run(w, llm, seed=s, max_groups=CONFIG["i2_groups"], max_new_tokens=120)
        llm._m = None; gc.collect()
        models.save_timing()
        print(f"[i2] seed {s}: {len(out[s])} key checks", flush=True)
        save("i2", dict(rows=out, examples=ex))


def stage_e8e():
    from bb import experiments2 as X
    method, emb, alpha = first_stage_cfg()
    out, share = {}, {}
    for s in SEEDS:
        c = ctx(s)
        out[s], share[s] = X.e8_oracle(c, method, emb, alpha)
        print(f"[e8e] seed {s} done", flush=True)
    save("e8e", dict(rows=out, share=share))


def stage_report():
    from bb import report2
    report2.main(OUT, CONFIG)


def run_split(stages):
    """Run each stage in a subprocess with the LLM deferred to a separate worker process, alternating until the stage
    finishes. Peak RAM = max(index process, LLM process) instead of their sum. All work is cached/checkpointed."""
    import subprocess
    q = os.path.join(ROOT, "cache_v02", "llm_queue.jsonl")
    for st in stages:
        for it in range(20):
            env = dict(os.environ, BB_LLM_QUEUE=q)
            r = subprocess.run([sys.executable, __file__, "--stages", st], env=env)
            if r.returncode == 0:
                break
            if os.path.exists(q):
                print(f"[split] {st}: running LLM worker for queued prompts (round {it+1})", flush=True)
                w = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {ROOT!r}); from bb.models import LLM, save_timing; "
                                    f"n = LLM({CONFIG['llm']!r}).run_queue({q!r}); save_timing(); print('[worker] generated', n)"])
                if w.returncode != 0:
                    raise SystemExit(f"LLM worker failed ({w.returncode})")
            else:
                raise SystemExit(f"stage {st} failed with code {r.returncode} and no queued prompts")


STAGES = dict(gen=stage_gen, embed=stage_embed, e8a=stage_e8a, e8b=stage_e8b, e8c=stage_e8c, e8d=stage_e8d, e8e=stage_e8e, e6=stage_e6, n4=stage_n4, h13=stage_h13, h11=stage_h11, i2=stage_i2, report=stage_report)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--split-llm", action="store_true", help="run LLM calls in a separate worker process (low-RAM hosts)")
    a = ap.parse_args()
    if a.split_llm:
        run_split(a.stages.split(","))
        sys.exit(0)
    for st in a.stages.split(","):
        t = time.time()
        print(f"===== {st}", flush=True)
        STAGES[st]()
        print(f"===== {st} done in {time.time()-t:.0f}s", flush=True)
