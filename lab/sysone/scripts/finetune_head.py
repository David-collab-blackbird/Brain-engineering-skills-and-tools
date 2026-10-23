"""'Self-learning' arm for the marker decision models: fine-tune the NATIVE decision head (2 transformer layers + type
embedding + scorer) on cached frozen-encoder states. This is the CPU analogue of Unsloth's Laya head-only mode
(devrecated/jev-alternative train_laya.py --mode head: encoder frozen, head trains at head_lr 1e-4); LoRA on the encoder
needs a GPU and is not run here.

  python3 -I finetune_head.py --model julia --job J1 --ns 50,200,1000 --reps 3

Loss = cross-entropy + 0.5 * Brier (von / RLCD-style proper-score composite), then one temperature fitted on a held-out
20% slice of the same label budget (never on test). Saves results/finetune/<model>_<job>.json.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import numpy as np
import torch
import torch.nn as nn

from common import RES, Temperature, load_rows, metrics, softmax

torch.set_num_threads(int(os.environ.get("SYSONE_THREADS", "1")))


def load_states(model, sname):
    z = np.load(f"{RES}/scores/{model}/{sname}_states.npz", allow_pickle=True)
    return {k: z[k] for k in z.files}


class Head(nn.Module):
    """Mirror of DecisionModel minus the encoder; initialised from the shipped checkpoint."""

    def __init__(self, sd, d):
        super().__init__()
        layer = nn.TransformerEncoderLayer(d, max(1, d // 64), 4 * d, 0.1, batch_first=True, norm_first=True)
        self.head = nn.TransformerEncoder(layer, 2, enable_nested_tensor=False)
        self.type_emb = nn.Embedding(3, d)
        self.scorer = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))
        own = {k: v.float() for k, v in sd.items() if k.split(".")[0] in ("head", "type_emb", "scorer")}
        missing = self.load_state_dict(own, strict=False)
        assert not missing.missing_keys, missing.missing_keys

    def forward(self, h, am, mp, mm, qt):
        h = h + self.type_emb(qt)[:, None, :]
        pad = ~am
        for layer in self.head.layers:
            h = layer(h, src_key_padding_mask=pad)
        m = torch.gather(h, 1, mp.clamp(min=0)[:, :, None].expand(-1, -1, h.size(-1)))
        return self.scorer(m).squeeze(-1).masked_fill(~mm, -1e4)


def batchify(S, idx):
    st, off, mk, qt = S["states"], S["offsets"], S["markers"], S["qtype"]
    L = max(off[i + 1] - off[i] for i in idx)
    K = max(2, max((mk[i] >= 0).sum() for i in idx))
    d = st.shape[1]
    h = torch.zeros((len(idx), L, d))
    am = torch.zeros((len(idx), L), dtype=torch.bool)
    mp = torch.zeros((len(idx), K), dtype=torch.long)
    mm = torch.zeros((len(idx), K), dtype=torch.bool)
    for j, i in enumerate(idx):
        n = off[i + 1] - off[i]
        h[j, :n] = torch.from_numpy(st[off[i]:off[i + 1]].astype(np.float32))
        am[j, :n] = True
        k = (mk[i] >= 0).sum()
        mp[j, :k] = torch.from_numpy(mk[i][:k].astype(np.int64))
        mm[j, :k] = True
    return h, am, mp, mm, torch.from_numpy(qt[idx].astype(np.int64))


@torch.no_grad()
def predict(head, S, idx, bs=32):
    head.eval()
    out = []
    for s in range(0, len(idx), bs):
        ch = idx[s:s + bs]
        z = head(*batchify(S, ch)).numpy()
        out.append(z)
    K = max(o.shape[1] for o in out)
    Z = np.concatenate([np.pad(o, ((0, 0), (0, K - o.shape[1])), constant_values=-1e4) for o in out])
    return Z


def train(head, S, idx, y, epochs, lr=1e-4, bs=16, brier_w=0.5, seed=0):
    g = torch.Generator().manual_seed(seed)
    opt = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=0.01)
    steps = max(1, epochs * int(np.ceil(len(idx) / bs)))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.1)
    head.train()
    t = 0
    for ep in range(epochs):
        perm = torch.randperm(len(idx), generator=g).numpy()
        for s in range(0, len(idx), bs):
            ch = perm[s:s + bs]
            z = head(*batchify(S, idx[ch]))
            yt = torch.from_numpy(y[idx[ch]].astype(np.int64))   # labels of the SAME rows as the batch
            p = torch.softmax(z, -1)
            if int(yt.max()) >= z.shape[1]:     # batch narrower than a label index (masked option slots): pad logits
                z = torch.nn.functional.pad(z, (0, int(yt.max()) + 1 - z.shape[1]), value=-1e4)
                p = torch.softmax(z, -1)
            onehot = torch.nn.functional.one_hot(yt, z.shape[1]).float()
            loss = nn.functional.cross_entropy(z, yt) + brier_w * ((p - onehot) ** 2).sum(1).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            t += 1
    return head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="julia")
    ap.add_argument("--job", default="J1")
    ap.add_argument("--ns", default="50,200,1000")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--sub", default=None, help="J3 subjob: type|area")
    ap.add_argument("--lr", type=float, default=1e-4, help="head LR (Unsloth Laya default 1e-4)")
    a = ap.parse_args()
    from safetensors.torch import load_file
    from score import snap
    repo = {"laya": "convaiinnovations/laya", "julia": "SupersonicLabs/Julia-1"}[a.model]
    sd = load_file(os.path.join(snap(repo), "model.safetensors"))
    sd = {k: v for k, v in sd.items() if not k.startswith("encoder.")}
    d = sd["type_emb.weight"].shape[1]
    Ste, Spo = load_states(a.model, f"{a.job}_test"), load_states(a.model, f"{a.job}_pool")
    rows = {r["id"]: r for s in (f"{a.job}_test", f"{a.job}_pool") for r in load_rows(s)}
    tag = f"{a.model}_{a.job}" + (f"_{a.sub}" if a.sub else "") + (f"_lr{a.lr:g}" if a.lr != 1e-4 else "")

    def sel(S):
        idx = np.arange(len(S["ids"]))
        if a.sub:
            idx = np.array([i for i in idx if rows[S["ids"][i]]["subjob"] == a.sub])
        return idx

    te_idx, po_idx = sel(Ste), sel(Spo)
    yte, ypo = Ste["label"].astype(int), Spo["label"].astype(int)
    gpo = np.array([rows[i]["group"] for i in Spo["ids"]])
    from analyze import pool_order
    res = {"model": a.model, "job": a.job, "sub": a.sub, "n_test": int(len(te_idx)), "runs": {}}
    base = Head(sd, d)
    Z0 = predict(base, Ste, te_idx)
    res["zero_shot_check"] = metrics(softmax(Z0), yte[te_idx])
    for N in [int(x) for x in a.ns.split(",")]:
        if N > len(po_idx):
            N = len(po_idx)
        runs = []
        for rep in range(a.reps if N < 1000 else 1):
            order = pool_order(gpo[po_idx], rep)
            o = po_idx[order][:N]
            ncal = max(10, int(0.2 * N))
            tr, ca = o[:-ncal], o[-ncal:]
            head = Head(sd, d)
            epochs = 8 if N <= 50 else (5 if N <= 200 else 3)
            t0 = time.time()
            train(head, Spo, tr, ypo, epochs, lr=a.lr, seed=rep)
            ttrain = time.time() - t0
            T = Temperature().fit(predict(head, Spo, ca), ypo[ca])
            Z = predict(head, Ste, te_idx)
            m_raw = metrics(softmax(Z), yte[te_idx])
            m_cal = metrics(T(Z), yte[te_idx])
            runs.append(dict(raw=m_raw, cal=m_cal, T=T.T, train_s=ttrain, n_train=int(len(tr)), n_cal=int(ncal)))
            print(f"{tag} N={N} rep={rep} acc {m_cal['acc']:.3f} ece {m_cal['ece']:.3f} brier {m_cal['brier']:.3f} "
                  f"auroc_err {m_cal['auroc_err']:.3f} train {ttrain:.0f}s", flush=True)
            if rep == 0:
                np.save(f"{RES}/finetune/{tag}_N{N}_probs.npy", T(Z))
        res["runs"][N] = runs
        json.dump(res, open(f"{RES}/finetune/{tag}.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    os.makedirs(f"{RES}/finetune", exist_ok=True)
    main()
