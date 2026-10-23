"""Minimal OpenAI-compatible /v1/embeddings server backed by bge-small-en-v1.5 (CPU), for the GBrain test.

GBrain's `llama-server` recipe calls POST {base}/embeddings with {"model": ..., "input": [...]}.
Query-side instruction is added by GBrain itself via the `embedding_query_prefix` config key, so this server
embeds text exactly as received (documents unprefixed, queries carry the bge prefix).
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("HF_HOME", "/home/claude/models/hf")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

torch.set_num_threads(int(os.environ.get("EMB_THREADS", "1")))
MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")
MODEL.max_seq_length = 512
LOCK = threading.Lock()
STATS = {"calls": 0, "texts": 0}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._send(200, {"object": "list", "data": [{"id": "bge-small", "object": "model"}]})
        if self.path.rstrip("/").endswith("/stats"):
            return self._send(200, STATS)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        req = json.loads(self.rfile.read(n) or b"{}")
        if not self.path.rstrip("/").endswith("/embeddings"):
            return self._send(404, {"error": "not found"})
        inp = req.get("input", [])
        if isinstance(inp, str):
            inp = [inp]
        with LOCK:
            v = MODEL.encode(inp, batch_size=32, normalize_embeddings=True, convert_to_numpy=True)
        STATS["calls"] += 1
        STATS["texts"] += len(inp)
        data = [{"object": "embedding", "index": i, "embedding": [float(x) for x in vec]} for i, vec in enumerate(v)]
        self._send(200, {"object": "list", "data": data, "model": req.get("model", "bge-small"),
                         "usage": {"prompt_tokens": 0, "total_tokens": 0}})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8089
    print(f"[embed] serving bge-small on 127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
