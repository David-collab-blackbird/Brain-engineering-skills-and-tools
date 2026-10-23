#!/usr/bin/env python3
"""Write the full E-PM1 plan (PREREGISTRATION.md §5) to logs/plan_full.json, with the §9 reduction rule applied
through command-line options. usage: make_plan.py [--block6-tasks 60] [--block4-reps 2] [--block3-reps 3] [--block1-reps 3]
[--haiku-coprimary]"""
import json
import sys

MAT = "/home/claude/epm1/materials"
S, H = "claude-sonnet-5-5", "claude-haiku-5-5"
CLIENTS = [(S, None), (H, "low")]


def opt(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    tasks = json.load(open(f"{MAT}/tasks.json"))
    gtasks = json.load(open(f"{MAT}/gated.json"))["tasks"]
    ids = [t["id"] for t in tasks]
    ladder = [t["id"] for t in tasks if t["ladder"]]
    gold = [t["id"] for t in tasks if t["gold"]]
    r1, r3, r4, t6 = opt("--block1-reps", 3), opt("--block3-reps", 3), opt("--block4-reps", 2), opt("--block6-tasks", 60)
    b1 = [["full", arm, "40", S, None, t, r] for arm in "ABCD" for t in ids for r in range(1, r1 + 1)]
    b2 = [["full", arm, "40", m, e, g["id"], r] for arm in ("G", "P") for g in gtasks for m, e in CLIENTS for r in (1, 2, 3)]
    b3 = [["full", arm, size, S, None, t, r] for arm in "AC" for size in ("10", "120") for t in ladder for r in range(1, r3 + 1)]
    b4 = [["full", "W", "40", S, None, t, r] for t in gold for r in range(1, r4 + 1)]
    b5 = [["full", "GB", "40", m, e, g["id"], r] for g in gtasks for m, e in CLIENTS for r in (1, 2)]
    h_reps = 3 if "--haiku-coprimary" in sys.argv else 1
    b6 = [["full", arm, "40", H, None, t, r] for arm in "ABCD" for t in ids[:t6] if True for r in range(1, h_reps + 1)]
    if t6 < 60:  # keep a balanced subset: first t6/60 of each kind
        keep = [t["id"] for t in tasks if t["gold"]][: round(t6 * 50 / 60)] + [t["id"] for t in tasks if not t["gold"]][: round(t6 * 10 / 60)]
        b6 = [r for r in [["full", arm, "40", H, None, t, rr] for arm in "ABCD" for t in keep for rr in range(1, h_reps + 1)]]
    htasks = [t["id"] for t in json.load(open(f"{MAT}/tasks_h.json"))]
    bH = [["full", arm, "40", S, None, t, r] for arm in "ABCD" for t in htasks for r in (1, 2)]
    bN = [["full", arm, "40", S, None, t, r] for arm in ("AN", "BN", "CN") for t in htasks for r in (1, 2)]
    b7 = [["full", arm, "40", H, None, t, 1] for arm in "ABCD" for t in htasks]
    bNH = [["full", arm, "40", H, None, t, 1] for arm in ("AN", "BN", "CN") for t in htasks]
    blocks = [{"name": "1-main", "runs": b1}, {"name": "2-pm6", "runs": b2}, {"name": "H-hardened", "runs": bH},
              {"name": "N-minimal-client", "runs": bN}]
    if "--haiku-coprimary" in sys.argv:
        blocks.append({"name": "6-haiku", "runs": b6})
    blocks += [{"name": "3-ladder", "runs": b3}, {"name": "4-wrongscope", "runs": b4}, {"name": "5-pm6-bound", "runs": b5}]
    if "--haiku-coprimary" not in sys.argv:
        blocks.append({"name": "6-haiku", "runs": b6})
    blocks += [{"name": "7-haiku-H", "runs": b7}, {"name": "N-haiku", "runs": bNH}]
    if "--no-d" in sys.argv:
        for b in blocks:
            b["runs"] = [r for r in b["runs"] if r[1] not in ("D",)]
    plan = {"name": "full", "seed": 2024, "blocks": blocks}
    json.dump(plan, open("/home/claude/epm1/logs/plan_full.json", "w"), indent=0)
    print({b["name"]: len(b["runs"]) for b in blocks}, sum(len(b["runs"]) for b in blocks))


if __name__ == "__main__":
    main()
