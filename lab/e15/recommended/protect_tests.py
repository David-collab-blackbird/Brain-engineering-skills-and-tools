#!/usr/bin/env python3
"""PreToolUse hook: engineer-owned files are read-only to the builder (arms A, C, AU).

Blocks Edit/Write/MultiEdit/NotebookEdit on tests/acceptance/**, provided/**,
conftest.py, Makefile, packages/** and .claude/**, and Bash command segments
that write to those paths (redirection target, sed/perl -i, rm, mv, cp/install
destination, tee, chmod/chown, truncate, ln, touch, git checkout/restore/rm/mv,
python file writes). Reading them is always allowed.

Every denial is appended to $HOME/e15-hook-denials.log (outside the repository).
Exit code 2 = block; the reason on stderr is shown to Claude. File permissions are
the hard layer; this hook gives the builder a clear message and a denial log.
"""
import json
import os
import re
import shlex
import sys
import time

PROT = r"(?:tests/acceptance|provided|packages|\.claude)(?:/\S*)?|conftest\.py|Makefile"
PROT_RE = re.compile(r"(^|[\s'\"=/(])(\./)?(" + PROT + r")(?=$|[\s'\";|&)])")
REL_RE = re.compile(r"^(tests/acceptance|provided|packages|\.claude)(/|$)|^(conftest\.py|Makefile)$")
REDIRECT = re.compile(r"(?:^|[^0-9&<>])>{1,2}\s*['\"]?(\./)?(" + PROT + r")(?=$|[\s'\";|&)])")
VERBS = re.compile(r"(?:^|\s|;|&&|\|\|?)(sed\s+-i|perl\s+-[a-z]*i|rm|rmdir|unlink|tee|chmod|chown|chattr|truncate|"
                   r"ln|touch|shred|git\s+(?:checkout|restore|rm|mv|reset|apply|am|stash))\b")
# a Python write counts only when the protected path is the write target (permissions remain the hard layer)
PY_WRITE = re.compile(r"(open\(\s*['\"](\./)?(" + PROT + r")['\"]\s*,\s*['\"][wax+]|"
                      r"Path\(\s*['\"](\./)?(" + PROT + r")['\"]\s*\)\.(write_text|write_bytes|unlink|rename|chmod)|"
                      r"(os\.remove|os\.unlink|os\.rename|os\.chmod|shutil\.(move|copy\w*|rmtree))\(\s*['\"](\./)?(" + PROT + r"))")


def deny(reason, payload):
    try:
        with open(os.path.join(os.environ.get("HOME", "/tmp"), "e15-hook-denials.log"), "a") as f:
            f.write(json.dumps({"t": time.time(), "tool": payload.get("tool_name"),
                                "input": payload.get("tool_input")}) + "\n")
    except OSError:
        pass
    print(reason, file=sys.stderr)
    sys.exit(2)


def segments(cmd):
    return [s for s in re.split(r"\n|;|&&|\|\||\|", cmd) if s.strip()]


def bash_writes_protected(cmd):
    if REDIRECT.search(cmd) or PY_WRITE.search(cmd):
        return True
    for seg in segments(cmd):
        if not PROT_RE.search(seg):
            continue
        if VERBS.search(seg):
            return True
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        if words and os.path.basename(words[0]) in ("cp", "install", "rsync") and len(words) >= 3:
            if PROT_RE.search(" " + words[-1]):
                return True
        if words and os.path.basename(words[0]) == "mv" and len(words) >= 3:
            return True
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    root = payload.get("cwd") or os.getcwd()
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path") or ""
        rel = os.path.relpath(os.path.abspath(os.path.join(root, path)), root)
        if REL_RE.search(rel):
            deny(f"BLOCKED: {rel} is engineer-owned and read-only (brief rule R12). "
                 "If you believe it is wrong, add a test-change request to build/questions.json.", payload)
    elif tool == "Bash":
        if bash_writes_protected(ti.get("command", "")):
            deny("BLOCKED: this command appears to modify engineer-owned files (tests/acceptance, provided, "
                 "packages, conftest.py, Makefile, .claude). Read them freely; never change them (rule R12).", payload)


if __name__ == "__main__":
    main()
