"""Batch 3 runner: BrainBench v0.3 + E9 (write gate), fabrication suite, E10/E10b (double entry), E-SCR (owner's scribe),
I15 (certified recall), ADR checks (DA1-4, S2/S3 twin world, DA1-6, DA1-7, exit check), H17 aggregation, E11.
Batches 1 and 2 (run_all.py, run_batch2.py, data/, data_v02/, results/, results_v02/, cache_v02/) are untouched.

    python run_batch3.py --stages gen,dryrun                     # free: world + validator/scorer dry run
    python run_batch3.py --stages gate --model haiku --seeds 1   # paid: write gate (claude -p), checkpointed via cache_v03/llm
    python run_batch3.py --stages fab,escr                       # paid, small
    python run_batch3.py --stages e9,e10,agg,i15,adr,e11,report  # free analysis stages (checkpoint per stage in results_v03/)
Every claude call is cached (cache_v03/llm/), serialised (one process at a time) and logged (results_v03/spend_ledger.jsonl).
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bb.common import ROOT  # noqa: E402

OUT = os.path.join(ROOT, "results_v03")
SEEDS = (1, 2, 3)


def log(*a):
    msg = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(msg, flush=True)
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    with open(os.path.join(OUT, "logs", "run_batch3.log"), "a") as f:
        f.write(msg + "\n")


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, name + ".pkl.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(obj, f)
    os.replace(tmp, os.path.join(OUT, name + ".pkl"))


def load(name):
    p = os.path.join(OUT, name + ".pkl")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


def stage_gen(seeds):
    from bb import world3
    for s in seeds:
        g, items, tasks = world3.main(s)
        log(f"[gen] seed {s}: {len(items)} items, {len(tasks)} tasks")


def stage_dryrun(seeds):
    from bb import dryrun3
    ok = all(dryrun3.main(s) for s in seeds)
    log("[dryrun]", "PASS" if ok else "FAIL")
    if not ok:
        sys.exit(1)


def stage_gate(seeds, model, max_new_calls=None):
    from bb import gate3, llm3
    from bb.pipe3 import World3
    for s in seeds:
        name = f"gate_{model}"
        if gate3.load_gate(name, s):
            log(f"[gate] {name} s{s} already done")
            continue
        w = World3(s)
        t0 = time.time()
        raw, meta = gate3.run_gate(w, model, stage=f"gate-{model}-s{s}", log=log, max_new_calls=max_new_calls)
        if raw is None:
            log(f"[gate] {name} s{s}: bounded chunk finished at batch {meta['stopped_at']}/{meta['batches']}; run again to continue")
            return
        L, R, A, E, st = gate3.validate(w, raw)
        meta.update(secs=time.time() - t0, model=llm3.MODELS[model])
        gate3.save_gate(name, s, L, R, A, E, st, meta)
        with open(os.path.join(gate3.GATE_DIR, f"{name}_s{s}_raw.json"), "w") as f:
            json.dump(raw, f)
        log(f"[gate] {name} s{s} done in {meta['secs']/60:.0f} min; validator stats {st}; spent ${llm3.spent():.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", required=True)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--max-new-calls", type=int, default=None, help="bound one invocation (each run stays under the 2 h job limit); resumes from cache")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    for st in a.stages.split(","):
        if st == "gen":
            stage_gen(seeds)
        elif st == "dryrun":
            stage_dryrun(seeds)
        elif st == "gate":
            stage_gate(seeds, a.model, a.max_new_calls)
        elif st == "regate":      # re-parse and re-validate from the claude cache (no new calls) after a parser/validator fix
            from bb import gate3
            for s in seeds:
                p = os.path.join(gate3.GATE_DIR, f"gate_{a.model}_s{s}.json")
                if os.path.exists(p):
                    os.remove(p)
            stage_gate(seeds, a.model)
        else:
            from bb import exp3
            getattr(exp3, "stage_" + st)(seeds, log=log, save=save, load=load)


if __name__ == "__main__":
    main()
