"""J4 coverage checker set: a message made of 1-3 BrainBench source sentences that each state one keyed fact, and an
extraction listing records for all of them (label 0 = nothing missing) or for all but one (label 1 = misses an item).
Pool = worlds s1+s3, test = world s2.  python3 -I build_j4.py"""
import collections, json, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_sets import load, mentions, group_shuffle, write

def build(seed, n, rng):
    items, keys, ents, tasks, meta = load(seed)
    srcs = []
    for s in items.values():
        if not s.get("fact_refs"):
            continue
        f = items[s["fact_refs"][0]]
        if f.get("key") in keys and f["entity_id"] in ents and mentions(s["text"], f["value_str"]):
            srcs.append((s, f))
    by_part = collections.defaultdict(list)
    for s, f in srcs:
        by_part[s["partition"]].append((s, f))
    parts = [p for p in by_part if len(by_part[p]) >= 3]
    out = []
    for i in range(n):
        p = rng.choice(parts)
        k = rng.choice([1, 2, 2, 3, 3])
        pick = rng.sample(by_part[p], k)
        if len({f["key"] for _, f in pick}) < k:
            continue
        msg = " ".join(s["text"].rstrip(".") + "." for s, _ in pick)
        recs = [f"{ents[f['entity_id']]['name']} — {keys[f['key']]['label']}: {f['value_str']}" for _, f in pick]
        missing = (i % 2 == 1)
        if missing:
            drop = rng.randrange(k)
            recs = [r for j, r in enumerate(recs) if j != drop]
        ext = "\n".join(f"- {r}" for r in recs) if recs else "(no records extracted)"
        out.append(dict(id=f"J4-s{seed}-{len(out):05d}", job="J4", group=f"{seed}:{pick[0][1]['entity_id']}", qtype="noul",
                        state=f"Message: \"{msg}\"\nExtracted records:\n{ext}",
                        question="Does the extracted record list miss any fact, decision, preference or plan stated in the message?",
                        options=[["false", "no, every item stated in the message is captured"], ["true", "yes, at least one stated item is missing"]],
                        label=int(missing), meta=dict(k=k), parts=dict(msg=msg, ext="; ".join(recs) if recs else "nothing")))
    return out

if __name__ == "__main__":
    rng = random.Random(11)
    write(group_shuffle(build(1, 500, rng) + build(3, 500, rng), rng, 800), "J4_pool")
    write(group_shuffle(build(2, 400, rng), rng), "J4_test")
