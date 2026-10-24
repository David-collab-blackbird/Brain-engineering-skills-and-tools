#!/usr/bin/env python3
"""courier v0.1: transmittals, read-backs and brain cards for every agent hand-off (SPEC.md).

  courier.py template
  courier.py pack <folder> --out <zip> [--alias-file <file>]
  courier.py check <zip-or-folder>
  courier.py readback <zip-or-folder>
  courier.py brain <zip-or-folder> [--out <file>]

Exit codes: 0 OK, 1 a rule fails, 2 usage error. Python 3.11+ standard library only.
"""
import hashlib, json, os, re, shutil, sys, tempfile, zipfile

VERSION = "0.1.0"
PARTIES = {"Engineer", "Coordinator", "Agent 1", "Agent 2", "Brain builder", "Owner"}
KEYS = ["transmittal", "id", "from", "to", "date", "reply_to"]
HEADINGS = ["Purpose", "Asks", "Decisions relied on", "Supersedes", "Don't", "Reply format", "Needs the owner", "For the brain"]
TX_ID = re.compile(r"^TX-[A-Z0-9]+-\d{8}-\d{2}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)$")
KINDS = {"decision", "method", "killed", "lesson", "ruling"}
DRAWER = re.compile(r"^[a-z0-9-]+(/[a-z0-9-]+)*$")
DEC_COLS = ["id", "decision", "why", "source"]
BRAIN_COLS = ["id", "kind", "what", "why", "evidence", "limits", "sources", "drawer"]
TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".csv", ".py", ".js", ".html", ".yml", ".yaml"}
PLACEHOLDER = re.compile(r"<[^<>\n]+>")

TEMPLATE = """---
transmittal: 1
id: TX-<SENDER>-<YYYYMMDD>-<NN>
from: <Engineer | Coordinator | Agent 1 | Agent 2 | Brain builder | Owner>
to: <recipient>
date: <YYYY-MM-DDTHH:MM+10:30>
reply_to: <TX id or none>
---
# Transmittal <id>

## Purpose
<one or two lines: why this package exists>

## Asks
1. <what the receiver must do>

## Decisions relied on
| id | decision | why | source |
|---|---|---|---|
| <id> | <what was decided> | <why, in one line> | <where it is recorded> |

## Supersedes
<earlier package or document ids, or none>

## Don't
<what the receiver must not do, or none>

## Reply format
<what the reply must contain>

## Needs the owner
<- each item needing the owner's decision, or none>

## For the brain
| id | kind | what | why | evidence | limits | sources | drawer |
|---|---|---|---|---|---|---|---|
| <id> | <decision/method/killed/lesson/ruling> | <what> | <why it works or failed> | <strong/moderate/weak: basis> | <when it does not apply> | <ids> | <space/drawer> |
"""


class Fail(Exception):
    pass


def out(line):
    print(line, flush=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def real_lines(body):
    """Lines that count as content: not blank, not an HTML comment, not a placeholder."""
    text = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or PLACEHOLDER.search(s) or re.fullmatch(r"\|?[\s|:-]*\|?", s) and "-" in s and set(s) <= set("|-: "):
            continue
        lines.append(s)
    return lines


def parse(text):
    """Return (frontmatter dict, list of (heading, body)) or raise Fail for a malformed file."""
    m = re.match(r"^﻿?---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    if not m:
        raise Fail("R1 no frontmatter block between --- lines")
    fm = {}
    for ln in m.group(1).splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            fm[k.strip()] = v.strip()
    sections, cur = [], None
    for ln in m.group(2).splitlines():
        h = re.match(r"^##\s+(.+?)\s*$", ln)
        if h and not ln.startswith("###"):
            cur = [h.group(1), []]
            sections.append(cur)
        elif cur is not None:
            cur[1].append(ln)
    return fm, [(h, "\n".join(b)) for h, b in sections]


def table_rows(body):
    rows = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("|")]
    if not rows:
        return None, []
    split = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    header = [c.lower() for c in split(rows[0])]
    data = [split(r) for r in rows[1:] if not set(r.replace(" ", "")) <= set("|-:")]
    return header, data


def is_word(body, word):
    lines = real_lines(body)
    return len(lines) == 1 and lines[0].strip().rstrip(".").lower() == word


def validate(text):
    """Return a list of 'FAIL <rule> <detail>' lines; empty means valid. Also returns parsed parts."""
    fails = []
    try:
        fm, sections = parse(text)
    except Fail as e:
        return [f"FAIL {e}"], {}, {}
    for k in KEYS:
        if not fm.get(k):
            fails.append(f"FAIL R1 frontmatter key missing or empty: {k}")
    if fm.get("transmittal") and fm["transmittal"] != "1":
        fails.append("FAIL R1 transmittal must be 1")
    if fm.get("id") and not TX_ID.match(fm["id"]):
        fails.append("FAIL R1 id must look like TX-<SENDER>-<YYYYMMDD>-<NN>")
    for k in ("from", "to"):
        if fm.get(k) and fm[k] not in PARTIES:
            fails.append(f"FAIL R1 {k} must be one of: " + ", ".join(sorted(PARTIES)))
    if fm.get("from") and fm.get("from") == fm.get("to"):
        fails.append("FAIL R1 from and to must differ")
    if fm.get("date") and not DATE.match(fm["date"]):
        fails.append("FAIL R1 date must be ISO 8601 with a zone")
    if fm.get("reply_to") and fm["reply_to"].lower() != "none" and not TX_ID.match(fm["reply_to"]):
        fails.append("FAIL R1 reply_to must be none or a TX id")
    names = [h for h, _ in sections]
    for h in HEADINGS:
        if names.count(h) == 0:
            fails.append(f"FAIL R2 heading missing: ## {h}")
        elif names.count(h) > 1:
            fails.append(f"FAIL R2 heading repeated: ## {h}")
    present = [h for h in names if h in HEADINGS]
    if present != [h for h in HEADINGS if h in present] and not any(f.startswith("FAIL R2 heading repeated") for f in fails):
        fails.append("FAIL R2 headings out of order")
    body = {h: b for h, b in sections if h in HEADINGS}
    for h in HEADINGS:
        if h in body and not real_lines(body[h]):
            fails.append(f"FAIL R3 section has no real content: ## {h}")
    if "Asks" in body and real_lines(body["Asks"]):
        nums = [int(m.group(1)) for ln in body["Asks"].splitlines() if (m := re.match(r"^\s*(\d+)\.\s+\S", ln))]
        if not nums:
            fails.append("FAIL R4 Asks must be a numbered list")
        elif nums != list(range(1, len(nums) + 1)):
            fails.append("FAIL R4 Asks must be numbered 1, 2, 3 ... without gaps")
    if "Decisions relied on" in body and real_lines(body["Decisions relied on"]) and not is_word(body["Decisions relied on"], "none"):
        header, rows = table_rows(body["Decisions relied on"])
        if header != DEC_COLS:
            fails.append("FAIL R5 Decisions relied on must be none or a table: id | decision | why | source")
        elif not rows:
            fails.append("FAIL R5 Decisions table has no rows")
        for r in rows if header == DEC_COLS else []:
            r = (r + [""] * 4)[:4]
            for col, cell in zip(DEC_COLS, r):
                if not cell or PLACEHOLDER.search(cell):
                    fails.append(f"FAIL R5 decision '{r[0] or '?'}' has no {col}")
    if "For the brain" in body and real_lines(body["For the brain"]) and not is_word(body["For the brain"], "nothing settled"):
        header, rows = table_rows(body["For the brain"])
        if header != BRAIN_COLS:
            fails.append("FAIL R6 For the brain must be 'nothing settled' or a table: " + " | ".join(BRAIN_COLS))
        elif not rows:
            fails.append("FAIL R6 For the brain table has no rows")
        for r in rows if header == BRAIN_COLS else []:
            r = (r + [""] * 8)[:8]
            rid = r[0] or "?"
            for col, cell in zip(BRAIN_COLS, r):
                if not cell or PLACEHOLDER.search(cell):
                    fails.append(f"FAIL R6 brain row '{rid}' has no {col}")
            if r[1] and r[1] not in KINDS:
                fails.append(f"FAIL R6 brain row '{rid}' kind must be one of: " + ", ".join(sorted(KINDS)))
            if r[4] and not re.match(r"^(strong|moderate|weak)\b", r[4], re.I):
                fails.append(f"FAIL R6 brain row '{rid}' evidence must start with strong, moderate or weak")
            if r[7] and not DRAWER.match(r[7]):
                fails.append(f"FAIL R6 brain row '{rid}' drawer must look like space/drawer in lower case")
    if "Needs the owner" in body and real_lines(body["Needs the owner"]) and not is_word(body["Needs the owner"], "none"):
        if not all(re.match(r"^(-|\*|\d+\.)\s+\S", ln) for ln in real_lines(body["Needs the owner"])):
            fails.append("FAIL R7 Needs the owner must be none or a list")
    return fails, fm, body


def luhn(digits):
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
        alt = not alt
    return total % 10 == 0


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
SAFE_DOMAINS = ("example.com", "example.org", "example.net", "users.noreply.github.com")
MOBILE = re.compile(r"(?<!\d)04\d{2}[ ]?\d{3}[ ]?\d{3}(?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
SECRET = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bghp_[A-Za-z0-9]{10,}|\bgithub_pat_[A-Za-z0-9_]{10,}|\bsk-ant-[A-Za-z0-9-]{6,}|\bAKIA[A-Z0-9]{12,}")


def privacy(folder, aliases):
    fails = []
    for rel in files_in(folder):
        if os.path.splitext(rel)[1].lower() not in TEXT_EXT:
            continue
        with open(os.path.join(folder, rel), encoding="utf-8", errors="replace") as f:
            for n, ln in enumerate(f, 1):
                for m in EMAIL.finditer(ln):
                    dom = m.group(1).lower()
                    if not any(dom == d or dom.endswith("." + d) for d in SAFE_DOMAINS):
                        fails.append(f"FAIL privacy email {rel}:{n}")
                        break
                if MOBILE.search(ln):
                    fails.append(f"FAIL privacy phone {rel}:{n}")
                for m in CARD.finditer(ln):
                    digits = re.sub(r"\D", "", m.group(0))
                    if 13 <= len(digits) <= 19 and luhn(digits):
                        fails.append(f"FAIL privacy card {rel}:{n}")
                        break
                if SECRET.search(ln):
                    fails.append(f"FAIL privacy secret {rel}:{n}")
                for term in aliases:
                    if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", ln, re.I):
                        fails.append(f"FAIL privacy alias {rel}:{n}")
                        break
    return fails


def files_in(folder):
    found = []
    for d, _, fs in os.walk(folder):
        for f in fs:
            found.append(os.path.relpath(os.path.join(d, f), folder).replace(os.sep, "/"))
    return sorted(found)


def open_package(path, tmp):
    """Return the package folder (extracting a zip safely into tmp)."""
    if os.path.isdir(path):
        return path
    if not zipfile.is_zipfile(path):
        raise Fail("not a folder or zip")
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename
            mode = (info.external_attr >> 16) & 0o170000
            if name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name) or ".." in re.split(r"[\\/]", name) or mode == 0o120000:
                raise Fail("unsafe-path " + name)
        z.extractall(tmp)
    tops = [e for e in os.listdir(tmp)]
    return os.path.join(tmp, tops[0]) if len(tops) == 1 and os.path.isdir(os.path.join(tmp, tops[0])) else tmp


def verify_sums(folder):
    fails, sums = [], os.path.join(folder, "SHA256SUMS")
    if not os.path.exists(sums):
        return ["FAIL missing SHA256SUMS"]
    listed = {}
    for ln in open(sums, encoding="utf-8").read().splitlines():
        if ln.strip():
            h, _, p = ln.partition("  ")
            listed[p.strip()] = h.strip()
    actual = [p for p in files_in(folder) if p != "SHA256SUMS"]
    for p, h in listed.items():
        fp = os.path.join(folder, p)
        if not os.path.exists(fp):
            fails.append(f"FAIL missing {p}")
        elif sha(open(fp, "rb").read()) != h:
            fails.append(f"FAIL changed {p}")
    fails += [f"FAIL unlisted {p}" for p in actual if p not in listed]
    return fails


def read_tx(folder):
    p = os.path.join(folder, "TRANSMITTAL.md")
    if not os.path.exists(p):
        raise Fail("R0 TRANSMITTAL.md missing")
    return open(p, encoding="utf-8").read()


def owner_items(body):
    b = body.get("Needs the owner", "")
    if not real_lines(b) or is_word(b, "none"):
        return []
    return [re.sub(r"^(-|\*|\d+\.)\s+", "", ln) for ln in real_lines(b)]


def cmd_pack(args):
    if not args or "--out" not in args:
        return usage()
    folder = args[0]
    zpath = args[args.index("--out") + 1] if args.index("--out") + 1 < len(args) else None
    alias_file = args[args.index("--alias-file") + 1] if "--alias-file" in args else None
    if not zpath or not os.path.isdir(folder):
        return usage()
    aliases = []
    if alias_file:
        if not os.path.exists(alias_file):
            return usage()
        if os.path.abspath(alias_file).startswith(os.path.abspath(folder) + os.sep):
            out("USAGE the alias file must sit outside the folder being packed")
            return 2
        aliases = [ln.strip() for ln in open(alias_file, encoding="utf-8") if ln.strip() and not ln.strip().startswith("#")]
    if os.path.exists(zpath):
        out(f"FAIL exists {zpath}: a delivered package is never overwritten; use a new name")
        return 1
    try:
        fails, _, _ = validate(read_tx(folder))
    except Fail as e:
        fails = [f"FAIL {e}"]
    fails += privacy(folder, aliases)
    if fails:
        for f in fails:
            out(f)
        out(f"NOT PACKED: {len(fails)} problem(s)")
        return 1
    lines = [f"{sha(open(os.path.join(folder, p), 'rb').read())}  {p}" for p in files_in(folder) if p != "SHA256SUMS"]
    with open(os.path.join(folder, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    top = os.path.basename(os.path.normpath(folder))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files_in(folder):
            z.write(os.path.join(folder, p), f"{top}/{p}")
    out(f"PACKED {zpath} SHA-256 {sha(open(zpath, 'rb').read())}")
    return 0


def with_package(args, fn):
    if not args or not os.path.exists(args[0]):
        return usage()
    tmp = tempfile.mkdtemp(prefix="courier-")
    try:
        try:
            folder = open_package(args[0], tmp)
        except Fail as e:
            out(f"FAIL {e}")
            return 1
        return fn(folder, args[1:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_check(args):
    def go(folder, _):
        fails = verify_sums(folder)
        try:
            vf, fm, body = validate(read_tx(folder))
        except Fail as e:
            vf, fm, body = [f"FAIL {e}"], {}, {}
        fails += vf
        purpose = (real_lines(body.get("Purpose", "")) or ["?"])[0]
        asks = len([1 for ln in body.get("Asks", "").splitlines() if re.match(r"^\s*\d+\.\s+\S", ln)])
        n_files = len([p for p in files_in(folder) if p != "SHA256SUMS"])
        out(f"PACKAGE {fm.get('id', '?')} · from {fm.get('from', '?')} to {fm.get('to', '?')} · {n_files} files · {asks} asks")
        out(f"PURPOSE {purpose}")
        items = owner_items(body)
        out("NEEDS THE OWNER: none" if not items else "NEEDS THE OWNER:")
        for it in items:
            out(f"  - {it}")
        for f in fails:
            out(f)
        out("CHECK OK" if not fails else f"CHECK FAILED: {len(fails)} problem(s)")
        return 0 if not fails else 1
    return with_package(args, go)


def cmd_readback(args):
    def go(folder, _):
        try:
            fails, fm, body = validate(read_tx(folder))
        except Fail as e:
            out(f"FAIL {e}")
            return 1
        if fails:
            for f in fails:
                out(f)
            return 1
        tx = fm["id"]
        lines = ["---", "readback: 1", "id: " + tx.replace("TX-", "RB-", 1), "reply_to: " + tx, "---", f"# Read-back of {tx}", "", "## Asks"]
        asks = [m.group(1) for ln in body["Asks"].splitlines() if (m := re.match(r"^\s*(\d+)\.\s+\S", ln))]
        lines += [f"Ask {n}: I understand this as: " for n in asks]
        lines += ["", "## Decisions"]
        if not is_word(body["Decisions relied on"], "none"):
            _, rows = table_rows(body["Decisions relied on"])
            lines += [f"{r[0]}: I understand this as: " for r in rows]
        lines += ["", "## Ambiguities", "- "]
        out("\n".join(lines))
        return 0
    return with_package(args, go)


def cmd_brain(args):
    dest = args[args.index("--out") + 1] if "--out" in args and args.index("--out") + 1 < len(args) else None

    def go(folder, _):
        try:
            fails, fm, body = validate(read_tx(folder))
        except Fail as e:
            out(f"FAIL {e}")
            return 1
        if fails:
            for f in fails:
                out(f)
            return 1
        recs = []
        if not is_word(body["For the brain"], "nothing settled"):
            _, rows = table_rows(body["For the brain"])
            for r in rows:
                d = dict(zip(BRAIN_COLS, r))
                text = (f"{d['kind'].capitalize()} {d['id']}: {d['what']}. Why: {d['why']}. Evidence: {d['evidence']}. "
                        f"Limits: {d['limits']}. Sources: {d['sources']}.")
                recs.append({"protocol_version": "0", "idempotency_key": sha(f"{fm['id']}|{d['id']}|{d['what']}|{d['why']}".encode()),
                             "text": text, "writer_role": "agent", "status": "candidate", "pocket": d["drawer"],
                             "derived_from": f"transmittal:{fm['id']}",
                             "structured": {"id": d["id"], "kind": d["kind"], "what": d["what"], "why": d["why"], "evidence": d["evidence"],
                                            "limits": d["limits"], "sources": [s.strip() for s in d["sources"].split(",") if s.strip()],
                                            "drawer": d["drawer"]}})
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
        if dest:
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(payload)
        else:
            sys.stdout.write(payload)
        return 0
    rest = [a for i, a in enumerate(args) if a != "--out" and (i == 0 or args[i - 1] != "--out")]
    return with_package(rest, go)


def usage():
    out(__doc__.strip())
    return 2


def main(argv):
    if not argv:
        return usage()
    cmd, args = argv[0], argv[1:]
    if cmd == "template":
        sys.stdout.write(TEMPLATE)
        return 0
    if cmd == "--version":
        out(f"courier {VERSION}")
        return 0
    table = {"pack": cmd_pack, "check": cmd_check, "readback": cmd_readback, "brain": cmd_brain}
    return table[cmd](args) if cmd in table else usage()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
