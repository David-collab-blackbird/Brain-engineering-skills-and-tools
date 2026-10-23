"""Summarise leak_probe.json: per identity probes, leaking rows, by op and by leaked source; override-attempt outcomes.
  python3 -I leak_sum.py leak_probe.json"""
import collections
import json
import sys

d = json.load(open(sys.argv[1]))
print("total probes", d["probes"], "errors", d["errors"], "leaking rows", len(d["leaks"]))
for k, v in d["by_identity"].items():
    print(f"  {k:40s} {v}")
c = collections.Counter((x["identity"], x["op"], x["row"].get("src")) for x in d["leaks"])
print("leaks by (identity, op, src):")
for k, v in c.most_common(40):
    print("  ", k, v)
qs = collections.Counter((x["identity"], x["q"][:60]) for x in d["leaks"])
print("leaks by (identity, query):")
for k, v in qs.most_common(20):
    print("  ", k, v)
for x in d["leaks"][:5]:
    print("EX", json.dumps(x)[:400])
