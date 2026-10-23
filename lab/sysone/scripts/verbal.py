"""Arm (d): LLM verbalised confidence. Qwen3-0.6B (int8, thinking off) answers in text and states a 0-100 confidence;
greedy decoding, parsed with a regex. Small n (CPU budget).

  python3 -I verbal.py --sets J1_test:120,J2_test:120,J3_test:120
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import numpy as np
import torch

from common import RES, CastEmbedding, cur_rss_mb, detach_mmap, float_rest, int8_linears, load_rows, trim

torch.set_num_threads(int(os.environ.get("SYSONE_THREADS", "1")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="J1_test:120,J2_test:120,J3_test:120")
    a = ap.parse_args()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from score import snap
    p = snap("Qwen/Qwen3-0.6B")
    tok = AutoTokenizer.from_pretrained(p)
    m = AutoModelForCausalLM.from_pretrained(p, dtype=torch.bfloat16)
    int8_linears(m.model)
    m.model.embed_tokens = CastEmbedding.patch(m.model.embed_tokens)
    # tied lm_head: keep a float32 copy of the embedding matrix as the output projection
    W = m.model.embed_tokens.weight.float().clone()
    m.lm_head = torch.nn.Linear(W.shape[1], W.shape[0], bias=False)
    m.lm_head.weight = torch.nn.Parameter(W, requires_grad=False)
    float_rest(m.model)
    detach_mmap(m)
    m.eval()
    print("rss", cur_rss_mb(), flush=True)
    out = {}
    for spec in a.sets.split(","):
        sname, _, cap = spec.partition(":")
        rows = load_rows(sname)
        # stratified take: alternate labels so small n is balanced-ish
        rows = rows[: int(cap)] if cap else rows
        recs = []
        t0 = time.time()
        for r in rows:
            opts = r["options"]
            if r["qtype"] == "noul":
                ask = "Answer yes or no."
                names = ["no", "yes"]
            else:
                ask = "Answer with one of: " + "; ".join(f"'{o[0]}' ({o[1]})" for o in opts) + "."
                names = [o[0] for o in opts]
            text = (r["state"] + "\n\nQuestion: " + r["question"] + "\n" + ask +
                    "\nReply exactly in the form: ANSWER: <answer>; CONFIDENCE: <0-100>")
            ids = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=True, add_generation_prompt=True,
                                          enable_thinking=False, return_tensors="pt", return_dict=True)
            with torch.inference_mode():
                g = m.generate(**ids, max_new_tokens=24, do_sample=False)
            s = tok.decode(g[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)
            ans = re.search(r"ANSWER:\s*'?([\w/ _-]+?)'?\s*[;,\n]", s + "\n", re.I)
            conf = re.search(r"CONFIDENCE:\s*(\d{1,3})", s, re.I)
            a_ = ans.group(1).strip().lower() if ans else ""
            k = next((j for j, n in enumerate(names) if n.lower() == a_), None)
            if k is None:
                k = next((j for j, n in enumerate(names) if n.lower() in s.lower()), None)
            c = min(100, int(conf.group(1))) / 100 if conf else None
            recs.append(dict(id=r["id"], label=r["label"], pred=k, conf=c, raw=s, K=len(opts)))
        out[sname] = dict(recs=recs, s_per_row=(time.time() - t0) / len(rows))
        ok = [x for x in recs if x["pred"] is not None and x["conf"] is not None]
        acc = np.mean([x["pred"] == x["label"] for x in recs if x["pred"] is not None]) if ok else float("nan")
        print(f"{sname}: n={len(recs)} parsed={len(ok)} acc={acc:.3f} mean_conf={np.mean([x['conf'] for x in ok]) if ok else float('nan'):.2f} "
              f"{out[sname]['s_per_row']:.1f}s/row", flush=True)
        json.dump(out, open(f"{RES}/verbal_qwen06.json", "w"), indent=1)


if __name__ == "__main__":
    main()
