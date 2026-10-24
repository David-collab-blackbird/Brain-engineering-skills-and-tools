# courier v0.1: transmittals, read-backs and brain cards

Status: SPEC v0.1 (2026-10-24) · Owner: engineer (OD-14) · Implements: owner request 2026-10-24 (document handling for every agent; plan for brain ingestion), OD-16 (one record standard)

A single-file Python 3.11+ tool, `courier.py`, standard library only, Windows- and Linux-safe. Every package that one agent sends another, through the owner, is a folder with `TRANSMITTAL.md` first, zipped with checksums. The tool refuses to pack an incomplete transmittal, verifies packages on arrival, prints the owner a one-screen summary, makes a read-back template, and turns the "For the brain" section into capture-ready records.

## 1 TRANSMITTAL.md format

YAML-style frontmatter (simple `key: value` lines between `---` lines; no nesting), then these level-2 headings in this order:

```
---
transmittal: 1
id: TX-<SENDER>-<YYYYMMDD>-<NN>
from: <Engineer | Coordinator | Agent 1 | Agent 2 | Brain builder | Owner>
to: <same set>
date: <ISO 8601 with zone, e.g. 2026-10-24T18:59+10:30>
reply_to: <a TX id, or none>
---
# Transmittal <id>
## Purpose
## Asks
## Decisions relied on
## Supersedes
## Don't
## Reply format
## Needs the owner
## For the brain
```

Rules (each is checked by `pack` and `check`):
- R1. All six frontmatter keys present and non-empty. `transmittal` is `1`. `id` matches `^TX-[A-Z0-9]+-\d{8}-\d{2}$`. `from` and `to` are in the set above and differ. `date` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2}|Z)$`. `reply_to` is `none` or a TX id.
- R2. All eight headings present, exactly once each, in the order shown.
- R3. Every section has real content: at least one line that is not blank, not an HTML comment, and not a template placeholder (a line containing `<` … `>` placeholder text such as `<what>`). The words `none` (case-insensitive) are real content for Supersedes, Don't and Needs the owner. `nothing settled` is real content for For the brain.
- R4. **Asks** is a numbered list (`1.`, `2.` …) with at least one item, numbered consecutively from 1.
- R5. **Decisions relied on** is either `none` or a Markdown table with columns `id | decision | why | source`, and every row has all four cells non-empty. A decision without its "why" or its "source" fails.
- R6. **For the brain** is either `nothing settled` or a table with columns `id | kind | what | why | evidence | limits | sources | drawer`. Every cell is non-empty. `kind` is one of `decision`, `method`, `killed`, `lesson`, `ruling`. `evidence` begins with one of `strong`, `moderate`, `weak`. `drawer` matches `^[a-z0-9-]+(/[a-z0-9-]+)*$` (for example `project-aviary/health`).
- R7. **Needs the owner** is `none` or a list (`-` or numbered) of items.

## 2 Commands

All commands print plain English. Exit code 0 = OK, 1 = the package or transmittal fails a rule, 2 = usage error (bad arguments, missing path).

- `courier.py template` prints a TRANSMITTAL.md skeleton with placeholders. A skeleton must FAIL `pack` (R3).
- `courier.py pack <folder> --out <zip> [--alias-file <file>]`:
  1. Validates `<folder>/TRANSMITTAL.md` against R1–R7. Each failure prints one line `FAIL <rule> <detail>`.
  2. Runs the privacy scan (§3) over every text file in the folder.
  3. On any failure, writes no zip and exits 1.
  4. Otherwise writes `<folder>/SHA256SUMS`: one line per file except SHA256SUMS itself, `<sha256hex>  <relative/path>` with forward slashes, sorted by path, hashing exact bytes.
  5. Zips the folder with the folder name as the top-level directory, prints `PACKED <zip> SHA-256 <hex>` and exits 0.
  6. Refuses to overwrite an existing zip (exit 1).
- `courier.py check <zip-or-folder>`:
  1. Opens the package. A zip is extracted to a temporary directory. Reject (exit 1, `FAIL unsafe-path`) any member with an absolute path, a `..` component, or a symlink.
  2. Verifies SHA256SUMS: `FAIL missing <path>` for a listed file that is absent, `FAIL changed <path>` for a hash mismatch, `FAIL unlisted <path>` for a file not listed (SHA256SUMS itself excepted). A package without SHA256SUMS fails.
  3. Validates the transmittal (R1–R7).
  4. Prints the owner summary: from, to, id, purpose (first line), the number of asks, the number of files, and a block that starts `NEEDS THE OWNER:` followed by each item, or `NEEDS THE OWNER: none`.
  5. Exits 0 only if everything passes.
- `courier.py readback <zip-or-folder>` prints a READBACK.md template. It has frontmatter `readback: 1`, `id: RB-…` (the TX id with `TX` replaced by `RB`) and `reply_to: <TX id>`, then one line per ask (`Ask 1: I understand this as: …`) and per decision id (`<id>: I understand this as: …`), and a `## Ambiguities` heading.
- `courier.py brain <zip-or-folder> [--out <file>]` writes JSON Lines (to stdout or the file), one object per For the brain row:
  - `protocol_version: "0"`, `writer_role: "agent"`, `status: "candidate"`;
  - `pocket` = the drawer;
  - `derived_from` = `"transmittal:<TX id>"`;
  - `idempotency_key` = SHA-256 hex of `<TX id>|<row id>|<what>|<why>`;
  - `text` = one readable paragraph built from the row;
  - `structured` = `{id, kind, what, why, evidence, limits, sources (a list split on commas), drawer}`.

  `nothing settled` writes nothing and exits 0. The validation rules still apply.

## 3 Privacy scan (pack)

Scans every file with extension .md, .txt, .json, .jsonl, .csv, .py, .js, .html, .yml, .yaml. Each hit prints `FAIL privacy <kind> <path>:<line>` and never prints the matched text.
- Email addresses, except `example.com`, `example.org`, `example.net` and `users.noreply.github.com`.
- Australian mobile numbers (`04` followed by 8 digits, spaces allowed).
- Card numbers: 13–19 digits, spaces or dashes allowed, passing the Luhn check.
- Private key blocks (`-----BEGIN … PRIVATE KEY-----`), and tokens beginning `ghp_`, `github_pat_`, `sk-ant-` or `AKIA`.
- With `--alias-file`: each non-empty, non-`#` line is a term, matched as a whole word, case-insensitive. Hits print `FAIL privacy alias <path>:<line>`. The alias file itself must sit outside the folder (exit 2 if inside).
