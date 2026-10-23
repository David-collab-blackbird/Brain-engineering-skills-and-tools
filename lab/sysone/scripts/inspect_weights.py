"""Header-only safetensors inspector (reads the JSON header; never loads tensors). Verifies parameter counts, dtypes and
module structure against README claims.  Usage: python3 -I inspect_weights.py <file.safetensors> [...]"""
import collections
import json
import struct
import sys

DT = {"F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I8": 1, "U8": 1, "BOOL": 1, "F8_E4M3": 1}

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        hdr = json.loads(f.read(n))
    meta = hdr.pop("__metadata__", {})
    total, by_dtype, by_prefix = 0, collections.Counter(), collections.Counter()
    for k, v in hdr.items():
        c = 1
        for s in v["shape"]:
            c *= s
        total += c
        by_dtype[v["dtype"]] += c
        by_prefix[".".join(k.split(".")[:1 if not k.startswith(("encoder", "model")) else 2])] += c
    print(f"== {path}\n tensors {len(hdr)}  params {total/1e6:.1f}M  dtypes { {k: f'{v/1e6:.1f}M' for k, v in by_dtype.items()} }  meta {meta}")
    for p, c in by_prefix.most_common(12):
        print(f"   {p:40s} {c/1e6:9.2f}M")
