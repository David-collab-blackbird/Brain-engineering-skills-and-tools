#!/usr/bin/env python3
"""Engineer hand-check (PREREGISTRATION §7): 36 block-1 runs, 9 per arm A-D, seeded random sample.

usage: handcheck.py sample            -> logs/handcheck_sample.json + logs/handcheck_traces.txt (no scorer verdicts)
       handcheck.py agree             -> reads logs/handcheck_judgments.json {run: {"correct_use": bool, "full_compliance": bool|null,
                                         "outcome": bool}} and reports agreement with score.json (percent, Cohen's kappa)
"""
import glob
import json
import random
import subprocess
import sys

E = "/home/claude/epm1"


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa = sum(a) / n
    pb = sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0


def main():
    if sys.argv[1] == "sample":
        rng = random.Random(3636)
        pick = []
        for arm in "ABCD":
            runs = sorted(glob.glob(f"{E}/runs/full/{arm}-40-sonnet55/*/*"))
            runs = [r for r in runs if not r.split("/")[-2].endswith("-H")]
            pick += rng.sample(runs, 9)
        json.dump(pick, open(f"{E}/logs/handcheck_sample.json", "w"), indent=1)
        with open(f"{E}/logs/handcheck_traces.txt", "w") as f:
            for r in pick:
                f.write("=" * 100 + "\n")
                f.write(subprocess.run([sys.executable, f"{E}/harness/trace.py", r, "--maxarg", "700"], capture_output=True, text=True).stdout)
        print(len(pick))
    else:
        J = json.load(open(f"{E}/logs/handcheck_judgments.json"))
        rows = {"correct_use": ([], []), "full_compliance": ([], []), "outcome": ([], [])}
        dis = []
        for run, j in J.items():
            s = json.load(open(f"{run}/score.json"))
            for k, sk in (("correct_use", "correct_use"), ("full_compliance", "full_compliance"), ("outcome", "outcome_pass")):
                if j.get(k) is None or s.get(sk) is None:
                    continue
                rows[k][0].append(bool(j[k]))
                rows[k][1].append(bool(s[sk]))
                if bool(j[k]) != bool(s[sk]):
                    dis.append((run.split("/runs/full/")[1], k, "hand", j[k], "scorer", s[sk], j.get("note", "")))
        out = {k: {"n": len(v[0]), "agree": sum(x == y for x, y in zip(*v)), "pct": round(sum(x == y for x, y in zip(*v)) / max(1, len(v[0])), 4),
                   "kappa": kappa(*v)} for k, v in rows.items()}
        out["disagreements"] = dis
        json.dump(out, open(f"{E}/logs/handcheck_agreement.json", "w"), indent=1)
        print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
