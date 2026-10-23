import sys, collections, statistics
sys.path.insert(0, "/home/claude/brainbench")
from bb.brain import World
from bb.experiments import build_cards
import os
w = World("/home/claude/brainbench/data_v02/s1")
cards, covers, card_of = build_cards(w)
multi = {e: c for e, c in card_of.items() if len(c) > 1}
print("entities", len(w.entities), "entities with cards", len(card_of), "entities split across >1 partition card", len(multi))
for e, c in list(multi.items())[:8]:
    print("  ", w.entities[e]["name"], c)
# requesters who can see >1 card for same entity
idn = w.identities
cnt = collections.Counter()
for e, cs in multi.items():
    for r, meta in idn.items():
        parts = set(meta["partitions"])
        vis = [c for c in cs if next(d for d in cards if d["id"] == c)["partition"] in parts]
        if len(vis) > 1: cnt[r] += 1
print("identity -> #entities where they see >1 partial card:", dict(cnt))
# facts per card distribution and words
wc = [len(d["text"].split()) for d in cards]
print("card words mean %.0f max %d" % (statistics.mean(wc), max(wc)))
# how much of required set is covered by cards that the query never mentions? (circularity proxy)
