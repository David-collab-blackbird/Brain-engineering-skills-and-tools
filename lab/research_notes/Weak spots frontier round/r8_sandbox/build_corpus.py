# Build a procedure-library corpus from three vendored skill packs (read as data only).
import os, re, json, sys, glob, yaml
ROOTS = {
 "gbrain": "/home/claude/vendor-skills/gbrain-vendor/gbrain/skills",
 "gstack": "/home/claude/vendor-skills/gstack/gstack-main",
 "superpowers": "/home/claude/vendor-skills/superpowers/superpowers-main/skills",
}
def parse(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
    if not m: return None
    try: fm = yaml.safe_load(m.group(1)) or {}
    except Exception: fm = {}
    return fm, m.group(2)
out = []
for pack, root in ROOTS.items():
    for p in sorted(glob.glob(os.path.join(root, "*", "SKILL.md"))):
        r = parse(p)
        if not r: continue
        fm, body = r
        name = str(fm.get("name") or os.path.basename(os.path.dirname(p)))
        desc = fm.get("description") or ""
        if isinstance(desc, list): desc = " ".join(map(str, desc))
        trig = fm.get("triggers") or []
        if isinstance(trig, str): trig = [trig]
        out.append({"id": f"{pack}:{os.path.basename(os.path.dirname(p))}", "pack": pack,
                    "name": name, "description": " ".join(str(desc).split()),
                    "triggers": [str(t) for t in trig], "body": body})
fx = []
for p in sorted(glob.glob(os.path.join(ROOTS["gbrain"], "*", "routing-eval.jsonl"))):
    for line in open(p):
        line = line.strip()
        if not line.startswith("{"): continue
        r = json.loads(line)
        exp = r.get("expected_skill")
        fx.append({"intent": r["intent"], "expected": f"gbrain:{exp}" if exp else None,
                   "ok": [f"gbrain:{a}" for a in (r.get("ambiguous_with") or [])]})
json.dump({"skills": out, "fixtures": fx}, open(sys.argv[1], "w"))
from collections import Counter
print(Counter(s["pack"] for s in out), len(fx), "fixtures", sum(1 for f in fx if f["expected"] is None), "negatives")
idx = "\n".join(f"- {s['name']}: {s['description']}" for s in out)
print("index chars all packs:", len(idx), "~tokens", len(idx)//4)
for pk in ROOTS:
    i = "\n".join(f"- {s['name']}: {s['description']}" for s in out if s["pack"]==pk)
    print(pk, "index chars", len(i))
