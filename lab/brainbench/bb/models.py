"""Real-model wrappers for batch 2 (CPU): embedders, cross-encoder / LLM rerankers, a small instruct LLM.
Everything caches to disk so experiments are re-runnable without recomputing model calls.

Official templates are used where the model card defines one:
  * Qwen3-Embedding-0.6B: queries get "Instruct: {task}\\nQuery:{q}"; documents get no prefix (last-token pooling).
  * bge-small-en-v1.5: queries get "Represent this sentence for searching relevant passages: ".
  * Qwen3-Reranker-0.6B: system/user/assistant chat frame, "<Instruct>: ..\\n<Query>: ..\\n<Document>: ..",
    empty think block, score = P("yes") from softmax over the yes/no logits at the last position.
  * mxbai-rerank-base-v2: the mxbai_rerank package's v2 prompt (query:/document:/task prompt in a Qwen chat frame),
    score = logit("1") - logit("0").
  * bge-reranker-v2-m3: sequence-classification logit.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import numpy as np

os.environ.setdefault("HF_HOME", "/home/claude/models/hf")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from .common import ROOT  # noqa: E402

CACHE = os.path.join(ROOT, "cache_v02")


def _bf16_native() -> bool:
    """bf16 is only fast on CPUs with AMX / AVX512-BF16; elsewhere torch emulates it (~4x slower than fp32)."""
    try:
        flags = open("/proc/cpuinfo").read()
    except OSError:
        return False
    return ("amx_bf16" in flags) or ("avx512_bf16" in flags)


BF16_NATIVE = _bf16_native()
TIMING: dict[str, list] = {}


def _t(name, n, dt):
    TIMING.setdefault(name, []).append((n, dt))


def h(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


# ============================================================================ embedders
EMBEDDERS = {
    "bge-small": dict(hf="BAAI/bge-small-en-v1.5", qprefix="Represent this sentence for searching relevant passages: ", dtype="float32", maxlen=512),
    "qwen3-emb": dict(hf="Qwen/Qwen3-Embedding-0.6B", qprefix="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:", dtype="bfloat16", maxlen=512),
    # same model, task-specific instruction (instruction-sensitivity check)
    "qwen3-emb-task": dict(hf="Qwen/Qwen3-Embedding-0.6B", qprefix="Instruct: Given a request to a personal assistant, retrieve the notes, facts, messages, documents and photos needed to answer it\nQuery:", dtype="bfloat16", maxlen=512, doc_model="qwen3-emb"),
}


class Embedder:
    _models: dict = {}

    def __init__(self, name: str):
        self.name = name
        self.cfg = EMBEDDERS[name]
        self.doc_name = self.cfg.get("doc_model", name)
        self._qcache_path = os.path.join(CACHE, f"q_{name}.npz")
        self._q = None

    def model(self):
        hf = self.cfg["hf"]
        if hf not in Embedder._models:
            import torch
            from sentence_transformers import SentenceTransformer
            dt = torch.bfloat16 if (self.cfg["dtype"] == "bfloat16" and BF16_NATIVE) else torch.float32   # bf16 ≈ fp32 quality (checked)
            m = SentenceTransformer(hf, device="cpu", model_kwargs={"torch_dtype": dt})
            m.max_seq_length = self.cfg["maxlen"]
            Embedder._models[hf] = m
        return Embedder._models[hf]

    def docs(self, texts: list[str], cache_key: str, batch_size: int = 16) -> np.ndarray:
        """Embeds documents with a per-text cache (so variants that share most texts are cheap)."""
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, f"d_{self.doc_name}.npz")
        store = {}
        if os.path.exists(path):
            z = np.load(path)
            store = dict(zip(z["keys"].tolist(), z["vecs"]))
        keys = [h(t) for t in texts]
        todo = sorted({k: t for k, t in zip(keys, texts) if k not in store}.items())
        if todo:
            print(f"[emb {self.doc_name}] encoding {len(todo)} new docs for {cache_key}", flush=True)
            m = self.model()
            CH = 1024
            for i in range(0, len(todo), CH):
                chunk = todo[i:i + CH]
                t0 = time.time()
                v = m.encode([t for _, t in chunk], batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
                _t(f"embed-docs:{self.doc_name}", len(chunk), time.time() - t0)
                for (k, _), vv in zip(chunk, v):
                    store[k] = vv
                np.savez(path, keys=np.array(list(store.keys())), vecs=np.stack(list(store.values())))
                print(f"  {min(i+CH, len(todo))}/{len(todo)}  {len(chunk)/(time.time()-t0):.1f} docs/s", flush=True)
        return np.stack([store[k] for k in keys])

    def queries(self, qs: list[str]) -> np.ndarray:
        if not qs:
            return np.zeros((0, 1), dtype=np.float32)
        if self._q is None:
            self._q = {}
            if os.path.exists(self._qcache_path):
                z = np.load(self._qcache_path)
                self._q = dict(zip(z["keys"].tolist(), z["vecs"]))
        keys = [h(q) for q in qs]
        todo = sorted({k: q for k, q in zip(keys, qs) if k not in self._q}.items())
        if todo:
            m = self.model()
            t0 = time.time()
            v = m.encode([self.cfg["qprefix"] + q for _, q in todo], batch_size=32, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
            _t(f"embed-queries:{self.name}", len(todo), time.time() - t0)
            for (k, _), vv in zip(todo, v):
                self._q[k] = vv
            os.makedirs(CACHE, exist_ok=True)
            np.savez(self._qcache_path, keys=np.array(list(self._q.keys())), vecs=np.stack(list(self._q.values())))
        return np.stack([self._q[k] for k in keys])


# ============================================================================ rerankers
QWEN_RR_PREFIX = ("<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. "
                  "Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n")
QWEN_RR_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
QWEN_RR_GENERIC = "Given a web search query, retrieve relevant passages that answer the query"
MXB_TASK = ("You are a search relevance expert who evaluates how well documents match search queries. For each query-document pair, carefully "
            "analyze the semantic relationship between them, then provide your binary relevance judgment (0 for not relevant, 1 for relevant).\nRelevance:")
MXB_PREFIX = "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n<|im_start|>user\n"
MXB_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n"

RERANKERS = {"bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3", "mxbai-rerank-base-v2": "mixedbread-ai/mxbai-rerank-base-v2",
             "qwen3-reranker": "Qwen/Qwen3-Reranker-0.6B"}


class Reranker:
    def __init__(self, name: str, batch_size: int = 16, max_doc_tokens: int = 384):
        self.name = name
        self.hf = RERANKERS[name]
        self.bs = batch_size
        self.max_doc_tokens = max_doc_tokens
        self.path = os.path.join(CACHE, f"rr_{name}.json")
        self.cache = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.cache = json.load(f)
        self._m = None
        self._dirty = 0

    def _load(self):
        if self._m is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer
        dt = torch.bfloat16 if BF16_NATIVE else torch.float32      # cached scores are dtype-agnostic (bf16 vs fp32 diff is tiny)
        if self.name == "bge-reranker-v2-m3":
            self.tok = AutoTokenizer.from_pretrained(self.hf)
            self._m = AutoModelForSequenceClassification.from_pretrained(self.hf, dtype=dt).eval()
        else:
            self.tok = AutoTokenizer.from_pretrained(self.hf, padding_side="left")
            self._m = AutoModelForCausalLM.from_pretrained(self.hf, dtype=dt).eval()
            if self.name == "qwen3-reranker":
                self.yes = self.tok.convert_tokens_to_ids("yes"); self.no = self.tok.convert_tokens_to_ids("no")
            else:
                self.yes = self.tok("1", add_special_tokens=False)["input_ids"][0]; self.no = self.tok("0", add_special_tokens=False)["input_ids"][0]

    def _trunc(self, d):
        ids = self.tok(d, add_special_tokens=False)["input_ids"]
        return d if len(ids) <= self.max_doc_tokens else self.tok.decode(ids[: self.max_doc_tokens])

    def _fmt(self, q, d, instruction):
        if self.name == "qwen3-reranker":
            return QWEN_RR_PREFIX + f"<Instruct>: {instruction or QWEN_RR_GENERIC}\n<Query>: {q}\n<Document>: {d}" + QWEN_RR_SUFFIX
        if self.name == "mxbai-rerank-base-v2":
            qp = (f"instruction: {instruction}\n" if instruction else "") + f"query: {q}"
            return MXB_PREFIX + qp + "\n" + f"document: {d}" + "\n" + MXB_TASK + MXB_SUFFIX
        raise ValueError

    def score(self, q: str, docs: list[str], instruction: str | None = None) -> np.ndarray:
        keys = [h(f"{instruction}\x1f{q}\x1f{d}") for d in docs]
        todo = [(k, d) for k, d in dict(zip(keys, docs)).items() if k not in self.cache]
        if todo:
            import torch
            self._load()
            todo.sort(key=lambda kd: len(kd[1]))          # length-sorted batches: less padding
            t0 = time.time()
            for i in range(0, len(todo), self.bs):
                ch = todo[i:i + self.bs]
                with torch.inference_mode():
                    if self.name == "bge-reranker-v2-m3":
                        b = self.tok([q] * len(ch), [d for _, d in ch], padding=True, truncation="only_second", max_length=512, return_tensors="pt")
                        s = self._m(**b).logits.view(-1).float().numpy()
                    else:
                        txt = [self._fmt(q, self._trunc(d), instruction) for _, d in ch]
                        b = self.tok(txt, padding=True, return_tensors="pt", add_special_tokens=False)
                        lg = self._m(**b, logits_to_keep=1).logits[:, -1, :].float()
                        if self.name == "qwen3-reranker":
                            s = torch.log_softmax(torch.stack([lg[:, self.no], lg[:, self.yes]], 1), 1)[:, 1].exp().numpy()
                        else:
                            s = (lg[:, self.yes] - lg[:, self.no]).numpy()
                for (k, _), v in zip(ch, s):
                    self.cache[k] = float(v)
            _t(f"rerank:{self.name}", len(todo), time.time() - t0)
            self._dirty += len(todo)
            if self._dirty >= 256:          # checkpoint often (container restarts)
                self.save()
        return np.array([self.cache[k] for k in keys])

    def save(self):
        os.makedirs(CACHE, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.cache, f)
        os.replace(tmp, self.path)
        self._dirty = 0


# ============================================================================ small instruct LLM
class LLMDeferred(Exception):
    """Raised in split mode (env BB_LLM_QUEUE set): uncached prompts were queued for the LLM worker process."""


class LLM:
    def __init__(self, hf: str = "Qwen/Qwen3-1.7B", batch_size: int = 8):
        self.hf = hf
        self.bs = batch_size
        self.path = os.path.join(CACHE, f"llm_{hf.split('/')[-1]}.json")
        self.cache = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.cache = json.load(f)
        self._m = None
        self.calls = 0
        self.gen_seconds = 0.0

    def _load(self):
        if self._m is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tok = AutoTokenizer.from_pretrained(self.hf, padding_side="left")
            # bf16 weights halve RAM (1.7B fits under the ~6 GB cap); on hosts without native bf16 it is ~4x slower than fp32
            self._m = AutoModelForCausalLM.from_pretrained(self.hf, dtype=torch.bfloat16).eval()

    def generate(self, prompts: list[str], max_new_tokens: int = 80, system: str | None = None) -> list[str]:
        """Greedy, thinking disabled. Returns completions; caches by (system, prompt, max_new_tokens)."""
        keys = [h(f"{system}\x1f{p}\x1f{max_new_tokens}") for p in prompts]
        todo = [(k, p) for k, p in dict(zip(keys, prompts)).items() if k not in self.cache]
        qpath = os.environ.get("BB_LLM_QUEUE")
        if todo and qpath:
            # split mode: never hold the LLM and the indexes in RAM at the same time (container memory cap)
            with open(qpath, "a") as f:
                for k, p in todo:
                    f.write(json.dumps(dict(key=k, prompt=p, system=system, max_new_tokens=max_new_tokens, hf=self.hf)) + "\n")
            raise LLMDeferred(f"{len(todo)} prompts queued")
        if todo:
            import torch
            self._load()
            todo.sort(key=lambda kp: len(kp[1]))
            for i in range(0, len(todo), self.bs):
                ch = todo[i:i + self.bs]
                msgs = [([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": p}] for _, p in ch]
                txt = [self.tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False) for m in msgs]
                b = self.tok(txt, return_tensors="pt", padding=True)
                t0 = time.time()
                with torch.inference_mode():
                    out = self._m.generate(**b, max_new_tokens=max_new_tokens, do_sample=False, temperature=None, top_p=None, top_k=None)
                dt = time.time() - t0
                ntok_in = int(b["attention_mask"].sum())
                _t(f"llm:{self.hf.split('/')[-1]}", len(ch), dt)
                TIMING.setdefault(f"llm-tokens-in:{self.hf.split('/')[-1]}", []).append((ntok_in, dt))
                for (k, _), o in zip(ch, out):
                    self.cache[k] = self.tok.decode(o[b["input_ids"].shape[1]:], skip_special_tokens=True).strip()
                self.save()
        self.calls += len(prompts)
        return [self.cache[k] for k in keys]

    def save(self):
        os.makedirs(CACHE, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.cache, f)
        os.replace(tmp, self.path)

    def run_queue(self, qpath):
        """Worker side of split mode: generate every queued prompt (grouped by system / max_new_tokens), cache, clear queue."""
        if not os.path.exists(qpath):
            return 0
        rows = [json.loads(x) for x in open(qpath) if x.strip()]
        groups = {}
        for r in rows:
            if r["key"] not in self.cache:
                groups.setdefault((r["system"], r["max_new_tokens"]), {})[r["key"]] = r["prompt"]
        n = 0
        for (system, mnt), d in groups.items():
            self.generate(list(d.values()), max_new_tokens=mnt, system=system)
            n += len(d)
        os.remove(qpath)
        return n


def free_models():
    """Drop cached embedding models (keeps RAM headroom for the LLM under the ~6 GB limit)."""
    import gc
    Embedder._models.clear()
    gc.collect()


def save_timing(path=None):
    path = path or os.path.join(CACHE, "timing.json")
    old = {}
    if os.path.exists(path):
        with open(path) as f:
            old = json.load(f)
    for k, v in TIMING.items():
        old.setdefault(k, []).extend(v)
    with open(path, "w") as f:
        json.dump(old, f)
    TIMING.clear()
