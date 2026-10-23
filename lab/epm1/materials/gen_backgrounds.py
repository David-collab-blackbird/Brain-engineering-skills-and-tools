#!/usr/bin/env python3
"""Generate a short 'Background' paragraph per procedure so bodies reach realistic SOP length (R8 §3: the owner's
procedural text is ~10k tokens for ~15 documents). Model: claude-sonnet-5-5 (materials phase, logged in spend.csv).
The paragraph may NOT add or change steps: it is linted (no digits, no tool names, no tags, no backticks) and
regenerated once on failure; still-failing entries get no background. Output: backgrounds.json {slug: text}."""
import json
import re
import sys

sys.path.insert(0, "/home/claude/epm1/harness")
sys.path.insert(0, "/home/claude/epm1/materials")
from common import plain_call
from library_core import CORE
from library_extra import EXTRA
from gated import GATED_PROCS

OUT = "/home/claude/epm1/materials/backgrounds.json"
TOOLS = ["records_", "ledger_", "notes_add", "record_update", "record_create", "task_create", "draft_message",
         "calendar_add", "procedures_", "payments_", "email_send", "request_owner"]
SYSTEM = ("You write background paragraphs for a small business group's internal procedure manual. The group is "
          "fictional: Marrowbank Landscapes (landscaping), Copperleaf Bakehouse (bakery cafe) and Tidewell Music School. "
          "Output only JSON.")


def lint(slug, text, tags):
    probs = []
    if re.search(r"\d", text):
        probs.append("digit")
    if "`" in text:
        probs.append("backtick")
    low = text.lower()
    for t in TOOLS:
        if t in low:
            probs.append("tool:" + t)
    for tg in tags:
        if re.search(r"(?<![a-z-])" + re.escape(tg) + r"(?![a-z-])", low) and "-" in tg:
            probs.append("tag:" + tg)
    n = len(text.split())
    if n < 70 or n > 190:
        probs.append(f"words:{n}")
    return probs


def main():
    procs = CORE + EXTRA + [p for p in GATED_PROCS if p.get("status") != "deprecated"]
    tags = [p["tag"] for p in procs]
    try:
        done = json.load(open(OUT))
    except FileNotFoundError:
        done = {}
    todo = [p for p in procs if p["slug"] not in done]
    for attempt in range(2):
        for i in range(0, len(todo), 10):
            batch = todo[i:i + 10]
            spec = [{"slug": p["slug"], "title": p["title"], "when_to_use": p["when"]} for p in batch]
            prompt = ("For each procedure below, write a Background paragraph of 100-150 words for the manual: why the "
                      "business has this procedure and what tends to go wrong without it, in plain business English. "
                      "Rules: describe only the situation named in when_to_use; do NOT state or add any steps, rules, "
                      "thresholds, amounts, dates, time limits or numbers of any kind (no digits at all); do not name "
                      "software, tools or tags; do not address the reader as an AI. Return a JSON object mapping each "
                      "slug to its paragraph, and nothing else.\n\n" + json.dumps(spec, indent=1))
            text, cost, _ = plain_call(prompt, SYSTEM, "claude-sonnet-5-5", "materials", f"backgrounds-{attempt}-{i}",
                                       budget=0.5)
            m = re.search(r"\{.*\}", text, re.S)
            try:
                got = json.loads(m.group(0)) if m else {}
            except json.JSONDecodeError:
                got = {}
            for p in batch:
                t = (got.get(p["slug"]) or "").strip()
                pr = lint(p["slug"], t, tags) if t else ["missing"]
                if not pr:
                    done[p["slug"]] = t
                else:
                    print("lint", p["slug"], pr, flush=True)
            json.dump(done, open(OUT, "w"), indent=1)
            print(f"attempt {attempt} batch {i}: {len(done)} done, cost {cost:.4f}", flush=True)
        todo = [p for p in procs if p["slug"] not in done]
        if not todo:
            break
    print("missing after retries:", [p["slug"] for p in todo])


if __name__ == "__main__":
    main()
