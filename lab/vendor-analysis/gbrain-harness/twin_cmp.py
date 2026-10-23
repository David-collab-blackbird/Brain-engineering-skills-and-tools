"""Twin-world (X1) comparison for GBrain: W vs W' (W + 20 hidden owner notes), with W vs W_repeat as the noise control.
For each (identity, query): did the visible top-10 id list change? max |score delta| over shared ids? any owner-source row?
  python3 -I twin_cmp.py twin_W.json twin_W_repeat.json twin_Wp.json"""
import json
import sys

W, R, P = (json.load(open(p)) for p in sys.argv[1:4])
assert len(W) == len(R) == len(P)


def cmp(a, b):
    lists_changed = order_changed = set_changed = 0
    max_d = 0.0
    n_d = 0
    per = []
    for x, y in zip(a, b):
        assert x["k"] == y["k"] and x["q"] == y["q"]
        ch = x["ids"] != y["ids"]
        sc = set(x["ids"]) != set(y["ids"])
        lists_changed += ch
        set_changed += sc
        order_changed += ch and not sc
        sx = dict(zip(x["ids"], x["scores"]))
        sy = dict(zip(y["ids"], y["scores"]))
        d = [abs((sx[i] or 0) - (sy[i] or 0)) for i in sx if i in sy and sx[i] is not None and sy[i] is not None]
        md = max(d) if d else 0.0
        if md > 1e-9:
            n_d += 1
        max_d = max(max_d, md)
        per.append(dict(k=x["k"], q=x["q"], changed=ch, set_changed=sc, max_score_delta=md))
    return dict(n=len(a), lists_changed=lists_changed, set_changed=set_changed, order_only=order_changed,
                queries_with_score_delta=n_d, max_score_delta=max_d), per


ctrl, _ = cmp(W, R)
treat, per = cmp(W, P)
owner_rows = sum(1 for x in P for s in x["srcs"] if s == "owner")
secret_rows = sum(1 for x in P for i in x["ids"] if str(i).startswith("secret/"))
print("control W vs W_repeat:", ctrl)
print("treatment W vs W':   ", treat)
print("owner-source rows visible to non-owners in W':", owner_rows, " secret pages visible:", secret_rows)
by_id = {}
for r in per:
    d = by_id.setdefault(r["k"], [0, 0, 0])
    d[0] += 1
    d[1] += r["changed"]
    d[2] += r["max_score_delta"] > 1e-9
print("per identity (n, lists changed, queries with score delta):")
for k, v in sorted(by_id.items()):
    print(f"  {k:28s} {v}")
ex = [r for r in per if r["changed"] or r["max_score_delta"] > 1e-9][:12]
print("examples:")
for r in ex:
    print("  ", r)
json.dump(dict(control=ctrl, treatment=treat, owner_rows=owner_rows, secret_rows=secret_rows, by_identity=by_id, examples=ex),
          open("twin_summary.json", "w"), indent=1)
