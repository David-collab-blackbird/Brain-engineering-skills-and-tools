"""Independent test author session (model: haiku), written from SPEC.md v0.1 on 2026-10-24; implementation not seen.

Black-box tests for tools/courier/courier.py, written from SPEC.md only.
Standard library unittest only. Synthetic data only (invented names, example.com).
Run: python3 -I tools/courier/tests/test_courier.py
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

COURIER = os.path.join(os.path.dirname(__file__), "..", "courier.py")
TX_ID = "TX-ENG-20261024-01"
RB_ID = "RB-ENG-20261024-01"
FOLDER = TX_ID
HEADINGS = ["Purpose", "Asks", "Decisions relied on", "Supersedes", "Don't",
            "Reply format", "Needs the owner", "For the brain"]
FRONT_KEYS = ["transmittal", "id", "from", "to", "date", "reply_to"]
BRAIN_COLS = ["id", "kind", "what", "why", "evidence", "limits", "sources", "drawer"]
BRAIN_ROW = ["B-1", "decision", "Use stdlib only", "Simple install",
             "strong: two passing tests", "none known", "OD-14, SPEC",
             "project-courier/tools"]
EXTRA_FILES = {"notes.md": b"Notes for the owner.\r\nSecond line.\n",
               "attachments/readme.txt": b"plain text\n"}


def out(r):
    return r.stdout + r.stderr


def run(*args):
    return subprocess.run([sys.executable, "-I", COURIER] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def write_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    with open(path, "wb") as f:
        f.write(data)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def mem(rel):
    return FOLDER + "/" + rel


def brain_table(rows):
    lines = ["| " + " | ".join(BRAIN_COLS) + " |", "|" + "---|" * len(BRAIN_COLS)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def dec_table(rows, header="| id | decision | why | source |", sep="|---|---|---|---|"):
    return "\n".join([header, sep] + ["| " + " | ".join(r) + " |" for r in rows])


def default_bodies():
    return {
        "Purpose": "Test transmittal for the courier tests.",
        "Asks": "1. Review section 2 of the spec.\n2. Confirm the drawer name.",
        "Decisions relied on": dec_table([["D-1", "Use stdlib only", "Keeps install simple", "OD-14"]]),
        "Supersedes": "none",
        "Don't": "none",
        "Reply format": "Reply with a READBACK file, one line per ask.",
        "Needs the owner": "- Approve the drawer name.",
        "For the brain": brain_table([BRAIN_ROW]),
    }


def build_tx(fm=None, bodies=None, order=None):
    """Build a TRANSMITTAL.md. fm: frontmatter overrides (None drops a key).
    bodies: section body overrides (None drops the heading). order: heading order."""
    front = {"transmittal": "1", "id": TX_ID, "from": "Engineer", "to": "Owner",
             "date": "2026-10-24T18:59+10:30", "reply_to": "none"}
    if fm:
        front.update(fm)
    text_bodies = default_bodies()
    if bodies:
        text_bodies.update(bodies)
    lines = ["---"]
    lines += [f"{k}: {v}" for k, v in front.items() if v is not None]
    lines += ["---", f"# Transmittal {front.get('id') or TX_ID}"]
    for h in order or HEADINGS:
        body = text_bodies.get(h)
        if body is None:
            continue
        lines += [f"## {h}", body, ""]
    return "\n".join(lines) + "\n"


def rewrite_zip(src, dst, replace=None, drop=(), add=None):
    """Copy zip src to dst, replacing/dropping members; add keys may be ZipInfo objects."""
    replace = replace or {}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename in drop:
                continue
            data = replace[info.filename] if info.filename in replace else zin.read(info.filename)
            zout.writestr(info.filename, data)
        for name, data in (add or {}).items():
            zout.writestr(name, data)
    return dst


class CourierCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="courier-tests-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make_pkg(self, text=None, extra=None, bodies=None, fm=None, order=None):
        """Create <tmp>/<random>/TX-ENG-20261024-01/ with TRANSMITTAL.md and extra files.
        Without text, the transmittal is built by build_tx(fm, bodies, order)."""
        root = tempfile.mkdtemp(dir=self.tmp)
        folder = os.path.join(root, FOLDER)
        os.mkdir(folder)
        if text is None:
            text = build_tx(fm=fm, bodies=bodies, order=order)
        write_file(os.path.join(folder, "TRANSMITTAL.md"), text)
        for rel, data in (extra or {}).items():
            write_file(os.path.join(folder, rel), data)
        return folder

    def pack(self, folder, alias=None):
        zpath = folder + ".zip"
        args = ["pack", folder, "--out", zpath]
        if alias:
            args += ["--alias-file", alias]
        return run(*args), zpath

    def packed(self, folder):
        r, zpath = self.pack(folder)
        self.assertEqual(r.returncode, 0, out(r))
        return zpath

    def assert_fail(self, r, rule=None):
        o = out(r)
        self.assertEqual(r.returncode, 1, o)
        fails = [l for l in o.splitlines() if l.startswith("FAIL")]
        self.assertTrue(fails, "no line starting FAIL:\n" + o)
        if rule:
            self.assertTrue(any(re.search(r"\b%s\b" % rule, l) for l in fails),
                            f"no FAIL line names {rule}:\n{o}")

    def expect_pack_fail(self, text, rule=None, extra=None):
        folder = self.make_pkg(text, extra)
        r, zpath = self.pack(folder)
        self.assert_fail(r, rule)
        self.assertFalse(os.path.exists(zpath), "a zip was written for a failing package")

    def expect_pack_ok(self, text=None, extra=None, alias=None):
        folder = self.make_pkg(text, extra)
        r, zpath = self.pack(folder, alias)
        self.assertEqual(r.returncode, 0, out(r))
        return folder, zpath


class TemplateAndValidPackageTests(CourierCase):
    def test_template_prints_skeleton_with_all_headings_in_order(self):
        r = run("template")
        self.assertEqual(r.returncode, 0, out(r))
        lines = [l.strip() for l in r.stdout.splitlines()]
        self.assertIn("transmittal: 1", lines)
        positions = []
        for h in HEADINGS:
            self.assertIn("## " + h, lines)
            positions.append(lines.index("## " + h))
        self.assertEqual(positions, sorted(positions))
        self.assertIn("<", r.stdout)

    def test_template_output_fails_pack_on_placeholders(self):
        rt = run("template")
        self.assertEqual(rt.returncode, 0, out(rt))
        folder = self.make_pkg(text=rt.stdout)
        r, zpath = self.pack(folder)
        self.assert_fail(r, "R3")
        self.assertFalse(os.path.exists(zpath))

    def test_valid_transmittal_packs(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        r, zpath = self.pack(folder)
        o = out(r)
        self.assertEqual(r.returncode, 0, o)
        self.assertIn("PACKED", r.stdout)
        self.assertTrue(os.path.isfile(zpath))

        sums = os.path.join(folder, "SHA256SUMS")
        self.assertTrue(os.path.isfile(sums))
        with open(sums, "rb") as f:
            raw = f.read().decode("utf-8")
        entries = []
        for line in raw.splitlines():
            m = re.fullmatch(r"([0-9a-f]{64})  (\S.*)", line)
            self.assertIsNotNone(m, "bad SHA256SUMS line: " + line)
            entries.append((m.group(2), m.group(1)))
        paths = [p for p, _ in entries]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(sorted(paths), ["TRANSMITTAL.md", "attachments/readme.txt", "notes.md"])
        self.assertNotIn("SHA256SUMS", paths)
        for p, digest in entries:
            self.assertNotIn("\\", p)
            self.assertEqual(digest, sha256_file(os.path.join(folder, *p.split("/"))), p)

        m = re.search(r"PACKED (.+?) SHA-256 ([0-9a-f]{64})", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertIn(os.path.basename(zpath), m.group(1))
        self.assertEqual(m.group(2), sha256_file(zpath))

        with zipfile.ZipFile(zpath) as zf:
            self.assertIsNone(zf.testzip())
            names = zf.namelist()
        self.assertIn(mem("TRANSMITTAL.md"), names)
        self.assertIn(mem("SHA256SUMS"), names)
        self.assertIn(mem("attachments/readme.txt"), names)
        for n in names:
            self.assertTrue(n.startswith(FOLDER + "/"), n)
            self.assertNotIn("\\", n)

    def test_valid_package_checks_ok_as_zip_folder_and_unpacked_copy(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        zpath = self.packed(folder)
        dest = tempfile.mkdtemp(dir=self.tmp)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(dest)
        targets = {"zip": zpath, "folder": folder, "unpacked": os.path.join(dest, FOLDER)}
        for label, target in targets.items():
            with self.subTest(target=label):
                r = run("check", target)
                self.assertEqual(r.returncode, 0, out(r))
                self.assertIn("NEEDS THE OWNER:", out(r))

    def test_check_summary_shows_identity_and_purpose(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        zpath = self.packed(folder)
        o = out(run("check", zpath))
        for needle in [TX_ID, "Engineer", "Owner", "Test transmittal for the courier tests."]:
            self.assertIn(needle, o)

    def test_check_lists_needs_the_owner_items(self):
        folder = self.make_pkg(
            bodies={"Needs the owner": "- Approve the drawer name.\n- Choose the reviewer."})
        zpath = self.packed(folder)
        o = out(run("check", zpath))
        self.assertIn("NEEDS THE OWNER:", o)
        block = o[o.index("NEEDS THE OWNER:"):]
        self.assertIn("Approve the drawer name.", block)
        self.assertIn("Choose the reviewer.", block)

    def test_check_needs_the_owner_none(self):
        folder = self.make_pkg(bodies={"Needs the owner": "none"})
        zpath = self.packed(folder)
        o = out(run("check", zpath))
        self.assertIn("NEEDS THE OWNER: none", o)


class R1FrontmatterTests(CourierCase):
    def test_r1_missing_or_empty_frontmatter_key(self):
        for key in FRONT_KEYS:
            with self.subTest(key=key, case="missing"):
                self.expect_pack_fail(build_tx(fm={key: None}), "R1")
            with self.subTest(key=key, case="empty"):
                self.expect_pack_fail(build_tx(fm={key: ""}), "R1")

    def test_r1_bad_id_pattern(self):
        bad_ids = ["TX-eng-20261024-01", "TX-ENG-2026102-01", "TX-ENG-20261024-1",
                   "TX-ENG-20261024-001", "XX-ENG-20261024-01", "TX--20261024-01"]
        for bad in bad_ids:
            with self.subTest(id=bad):
                self.expect_pack_fail(build_tx(fm={"id": bad}, ), "R1")

    def test_r1_from_equals_to(self):
        self.expect_pack_fail(build_tx(fm={"from": "Owner", "to": "Owner"}), "R1")

    def test_r1_from_or_to_outside_the_set(self):
        self.expect_pack_fail(build_tx(fm={"from": "Janitor"}), "R1")
        self.expect_pack_fail(build_tx(fm={"to": "Janitor"}), "R1")

    def test_r1_all_six_senders_are_accepted(self):
        for name in ["Engineer", "Coordinator", "Agent 1", "Agent 2", "Brain builder", "Owner"]:
            other = "Engineer" if name == "Owner" else "Owner"
            with self.subTest(sender=name):
                self.expect_pack_ok(build_tx(fm={"from": name, "to": other}))

    def test_r1_bad_date(self):
        bad_dates = ["2026-10-24", "2026-10-24T18:59", "2026-10-24 18:59+10:30",
                     "24/10/2026T18:59+10:30", "2026-10-24T18:59+1030"]
        for bad in bad_dates:
            with self.subTest(date=bad):
                self.expect_pack_fail(build_tx(fm={"date": bad}), "R1")

    def test_r1_good_dates_are_accepted(self):
        for good in ["2026-10-24T18:59:30Z", "2026-10-24T18:59-05:00", "2026-10-24T18:59+10:30"]:
            with self.subTest(date=good):
                self.expect_pack_ok(build_tx(fm={"date": good}))

    def test_r1_reply_to_must_be_none_or_tx_id(self):
        for bad in ["TX-bad", "nothing", "TX-ENG-2026102-01"]:
            with self.subTest(reply_to=bad):
                self.expect_pack_fail(build_tx(fm={"reply_to": bad}), "R1")
        self.expect_pack_ok(build_tx(fm={"reply_to": "TX-OWNER-20261023-03"}))

    def test_r1_transmittal_must_be_1(self):
        self.expect_pack_fail(build_tx(fm={"transmittal": "2"}), "R1")


class R2HeadingTests(CourierCase):
    def test_r2_each_heading_missing(self):
        for h in HEADINGS:
            with self.subTest(missing=h):
                self.expect_pack_fail(build_tx(bodies={h: None}), "R2")

    def test_r2_duplicated_heading(self):
        self.expect_pack_fail(build_tx(order=HEADINGS + ["Purpose"]), "R2")
        self.expect_pack_fail(build_tx(order=HEADINGS + ["For the brain"]), "R2")

    def test_r2_headings_out_of_order(self):
        for i in range(len(HEADINGS) - 1):
            swapped = HEADINGS[:]
            swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
            with self.subTest(swapped=(HEADINGS[i], HEADINGS[i + 1])):
                self.expect_pack_fail(build_tx(order=swapped), "R2")


class R3R4R5ContentTests(CourierCase):
    def test_r3_empty_section_fails(self):
        for h in ["Purpose", "Decisions relied on", "Supersedes", "Don't",
                  "Reply format", "Needs the owner"]:
            with self.subTest(section=h):
                self.expect_pack_fail(build_tx(bodies={h: ""}), "R3")

    def test_r3_placeholder_text_fails(self):
        self.expect_pack_fail(build_tx(bodies={"Purpose": "<what this transmittal is for>"}), "R3")

    def test_r3_html_comment_only_fails(self):
        self.expect_pack_fail(build_tx(bodies={"Reply format": "<!-- fill in later -->"}), "R3")

    def test_r3_none_is_real_content_case_insensitively(self):
        self.expect_pack_ok(build_tx(bodies={"Supersedes": "NONE", "Don't": "None",
                                             "Needs the owner": "none"}))

    def test_r4_asks_not_a_numbered_list(self):
        self.expect_pack_fail(build_tx(bodies={"Asks": "- Review the spec.\n- Confirm the drawer."}), "R4")
        self.expect_pack_fail(build_tx(bodies={"Asks": "Please review the spec."}), "R4")

    def test_r4_asks_not_numbered_from_one(self):
        self.expect_pack_fail(build_tx(bodies={"Asks": "0. Review.\n1. Confirm."}), "R4")
        self.expect_pack_fail(build_tx(bodies={"Asks": "2. Review.\n3. Confirm."}), "R4")

    def test_r4_asks_not_consecutive(self):
        self.expect_pack_fail(build_tx(bodies={"Asks": "1. Review.\n3. Confirm."}), "R4")
        self.expect_pack_fail(build_tx(bodies={"Asks": "1. Review.\n1. Confirm."}), "R4")

    def test_r4_consecutive_numbered_asks_accepted(self):
        self.expect_pack_ok(build_tx(bodies={"Asks": "1. One.\n2. Two.\n3. Three."}))

    def test_r5_decision_missing_why(self):
        t = build_tx(bodies={"Decisions relied on": dec_table([["D-1", "Use stdlib only", "", "OD-14"]])})
        self.expect_pack_fail(t, "R5")

    def test_r5_decision_missing_source(self):
        t = build_tx(bodies={"Decisions relied on": dec_table([["D-1", "Use stdlib only", "Keeps it simple", ""]])})
        self.expect_pack_fail(t, "R5")

    def test_r5_decision_with_any_empty_cell_fails(self):
        base = ["D-1", "Use stdlib only", "Keeps it simple", "OD-14"]
        for i in range(4):
            cells = base[:]
            cells[i] = ""
            with self.subTest(empty_cell=i):
                t = build_tx(bodies={"Decisions relied on": dec_table([cells])})
                self.expect_pack_fail(t, "R5")

    def test_r5_wrong_decision_columns_fail(self):
        t = build_tx(bodies={"Decisions relied on": dec_table(
            [["D-1", "Use stdlib only", "OD-14"]], header="| id | decision | source |",
            sep="|---|---|---|")})
        self.expect_pack_fail(t, "R5")

    def test_r5_none_accepted(self):
        self.expect_pack_ok(build_tx(bodies={"Decisions relied on": "none"}))
        self.expect_pack_ok(build_tx(bodies={"Decisions relied on": "None"}))


class R6R7BrainAndOwnerTests(CourierCase):
    def brain(self, *rows):
        return build_tx(bodies={"For the brain": brain_table([list(r) for r in rows])})

    def test_r6_bad_kind_fails(self):
        for kind in ["idea", "policy", "fact"]:
            with self.subTest(kind=kind):
                self.expect_pack_fail(self.brain(["B-1", kind] + BRAIN_ROW[2:]), "R6")

    def test_r6_each_allowed_kind_accepted(self):
        for kind in ["decision", "method", "killed", "lesson", "ruling"]:
            with self.subTest(kind=kind):
                self.expect_pack_ok(self.brain(["B-1", kind] + BRAIN_ROW[2:]))

    def test_r6_bad_evidence_word_fails(self):
        for ev in ["medium: x", "maybe: x", "unknown", "very strong"]:
            with self.subTest(evidence=ev):
                row = BRAIN_ROW[:4] + [ev] + BRAIN_ROW[5:]
                self.expect_pack_fail(self.brain(row), "R6")

    def test_r6_evidence_starting_with_allowed_word_accepted(self):
        for ev in ["strong: x", "moderate: two runs", "weak: one run", "weak"]:
            with self.subTest(evidence=ev):
                row = BRAIN_ROW[:4] + [ev] + BRAIN_ROW[5:]
                self.expect_pack_ok(self.brain(row))

    def test_r6_bad_drawer_fails(self):
        bad = ["Project-Courier", "project courier", "project_courier", "/project-courier",
               "project-courier/", "project//courier", "project-courier/Tools"]
        for d in bad:
            with self.subTest(drawer=d):
                row = BRAIN_ROW[:7] + [d]
                self.expect_pack_fail(self.brain(row), "R6")

    def test_r6_good_drawers_accepted(self):
        for d in ["project-courier", "project-aviary/health", "a1/b2/c3"]:
            with self.subTest(drawer=d):
                row = BRAIN_ROW[:7] + [d]
                self.expect_pack_ok(self.brain(row))

    def test_r6_any_empty_cell_fails(self):
        for i, col in enumerate(BRAIN_COLS):
            with self.subTest(empty=col):
                row = BRAIN_ROW[:i] + [""] + BRAIN_ROW[i + 1:]
                self.expect_pack_fail(self.brain(row), "R6")

    def test_r6_nothing_settled_accepted(self):
        self.expect_pack_ok(build_tx(bodies={"For the brain": "nothing settled"}))

    def test_r7_owner_list_must_be_a_list_or_none(self):
        self.expect_pack_fail(build_tx(bodies={"Needs the owner": "Approve the drawer name."}), "R7")

    def test_r7_numbered_list_and_none_accepted(self):
        self.expect_pack_ok(build_tx(bodies={"Needs the owner": "1. Approve the drawer name.\n2. Pick a reviewer."}))
        self.expect_pack_ok(build_tx(bodies={"Needs the owner": "none"}))
        self.expect_pack_ok(build_tx(bodies={"Needs the owner": "None"}))

    def test_none_and_nothing_settled_accepted_together(self):
        self.expect_pack_ok(build_tx(bodies={"Supersedes": "none", "Don't": "none",
                                             "Decisions relied on": "none",
                                             "Needs the owner": "none",
                                             "For the brain": "nothing settled"}))


class PackOverwriteTests(CourierCase):
    def test_pack_refuses_to_overwrite_existing_zip(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        zpath = folder + ".zip"
        write_file(zpath, b"existing archive bytes")
        r, _ = self.pack(folder)
        self.assertEqual(r.returncode, 1, out(r))
        with open(zpath, "rb") as f:
            self.assertEqual(f.read(), b"existing archive bytes")


PRIVACY_TOKENS = {
    "ghp_": "ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8",
    "github_pat_": "github_pat_Z9y8X7w6V5u4T3s2R1q0Pa",
    "sk-ant-": "sk-ant-api03-Qw3rTy6UiOpAsD9fGhJkLz",
    "AKIA": "AKIAQ7XW3ZT2LMNV5RKB",
}


class PrivacyScanTests(CourierCase):
    """Body text is placed on line 3 of notes.md so the reported line can be checked."""

    def body_file(self, body, filename="notes.md"):
        return {filename: "Intro line.\nSecond line.\n" + body + "\n"}

    def expect_privacy_fail(self, body, filename="notes.md", secret=None):
        folder = self.make_pkg(extra=self.body_file(body, filename))
        r, zpath = self.pack(folder)
        o = out(r)
        self.assertEqual(r.returncode, 1, o)
        fails = [l for l in o.splitlines() if l.startswith("FAIL privacy")]
        self.assertTrue(fails, o)
        self.assertTrue(any(re.search(re.escape(filename) + r":3\b", l) for l in fails), o)
        if secret:
            self.assertNotIn(secret.lower(), o.lower(), "matched text was printed")
        self.assertFalse(os.path.exists(zpath))

    def expect_privacy_ok(self, body, filename="notes.md", alias=None):
        folder = self.make_pkg(extra=self.body_file(body, filename))
        r, _ = self.pack(folder, alias)
        self.assertEqual(r.returncode, 0, out(r))

    def test_email_outside_allowed_domains_fails(self):
        for email in ["pat@acme-widgets.com", "x.y@widgets.co.nz"]:
            with self.subTest(email=email):
                self.expect_privacy_fail("Contact " + email + " today.", secret=email)

    def test_allowed_email_domains_pass(self):
        for email in ["pat@example.com", "pat@example.org", "pat@example.net",
                      "12345678+pat@users.noreply.github.com"]:
            with self.subTest(email=email):
                self.expect_privacy_ok("Contact " + email + " today.")

    def test_au_mobile_numbers_fail(self):
        for num in ["0412 345 678", "0412345678", "0498 765 432"]:
            with self.subTest(number=num):
                self.expect_privacy_fail("Call " + num + " after lunch.", secret=num)

    def test_non_mobile_fragments_pass(self):
        for num in ["0312 345 678", "0412 34"]:
            with self.subTest(number=num):
                self.expect_privacy_ok("Reference " + num + " in the log.")

    def test_luhn_valid_card_numbers_fail(self):
        for card in ["4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111",
                     "378282246310005"]:
            with self.subTest(card=card):
                self.expect_privacy_fail("Card " + card + " on file.", secret=card)

    def test_luhn_invalid_16_digit_number_passes(self):
        for num in ["4111 1111 1111 1112", "4111111111111113"]:
            with self.subTest(number=num):
                self.expect_privacy_ok("Reference " + num + " in the log.")

    def test_private_key_block_fails(self):
        for header in ["-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN OPENSSH PRIVATE KEY-----",
                       "-----BEGIN PRIVATE KEY-----"]:
            with self.subTest(header=header):
                self.expect_privacy_fail(header + "\nMIIBOgIBAAJBAK\n-----END PRIVATE KEY-----")

    def test_public_key_block_passes(self):
        self.expect_privacy_ok("-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE\n-----END PUBLIC KEY-----")

    def test_token_prefixes_fail_and_are_not_printed(self):
        for prefix, token in PRIVACY_TOKENS.items():
            with self.subTest(prefix=prefix):
                self.expect_privacy_fail("token value " + token, secret=token)

    def test_scanned_extensions_each_fail(self):
        for ext in [".md", ".txt", ".json", ".jsonl", ".csv", ".py", ".js", ".html", ".yml", ".yaml"]:
            with self.subTest(ext=ext):
                self.expect_privacy_fail("Contact pat@acme-widgets.com today.", filename="data" + ext)

    def test_unscanned_extension_is_not_scanned(self):
        self.expect_privacy_ok("Contact pat@acme-widgets.com today.", filename="blob.bin")

    def test_alias_terms_whole_word_case_insensitive(self):
        alias = os.path.join(self.tmp, "aliases.txt")
        write_file(alias, "# this line is a comment, not a term\nHarbourside\n\nAda\n")
        folder = self.make_pkg(extra=self.body_file("We met at the HARBOURSIDE cafe."))
        r, zpath = self.pack(folder, alias)
        o = out(r)
        self.assertEqual(r.returncode, 1, o)
        alias_fails = [l for l in o.splitlines() if l.startswith("FAIL privacy alias")]
        self.assertTrue(any(re.search(r"notes\.md:3\b", l) for l in alias_fails), o)
        self.assertNotIn("harbourside", o.lower(), "alias match was printed")
        self.assertFalse(os.path.exists(zpath))

    def test_alias_whole_word_hit_fails(self):
        alias = os.path.join(self.tmp, "aliases.txt")
        write_file(alias, "Ada\n")
        folder = self.make_pkg(extra=self.body_file("Ada reviewed it."))
        r, _ = self.pack(folder, alias)
        self.assertEqual(r.returncode, 1, out(r))
        self.assertTrue(any(l.startswith("FAIL privacy alias") for l in out(r).splitlines()))

    def test_alias_substring_inside_longer_word_passes(self):
        alias = os.path.join(self.tmp, "aliases.txt")
        write_file(alias, "Ada\n")
        self.expect_privacy_ok("The Adaptive planner and Adamant plan.", alias=alias)

    def test_alias_comment_lines_and_blank_lines_are_not_terms(self):
        alias = os.path.join(self.tmp, "aliases.txt")
        write_file(alias, "# Ada\n\n")
        self.expect_privacy_ok("Ada reviewed it.", alias=alias)

    def test_alias_file_inside_folder_is_usage_error(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        write_file(os.path.join(folder, "aliases.txt"), "Ada\n")
        r, _ = self.pack(folder, os.path.join(folder, "aliases.txt"))
        self.assertEqual(r.returncode, 2, out(r))

    def test_alias_file_in_subfolder_is_usage_error(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        sub_alias = os.path.join(folder, "sub", "aliases.txt")
        write_file(sub_alias, "Ada\n")
        r, _ = self.pack(folder, sub_alias)
        self.assertEqual(r.returncode, 2, out(r))


class CheckIntegrityTests(CourierCase):
    def packed_pkg(self):
        folder = self.make_pkg(extra=EXTRA_FILES)
        zpath = self.packed(folder)
        return folder, zpath

    def test_tampered_file_in_folder_fails_changed(self):
        folder, _ = self.packed_pkg()
        with open(os.path.join(folder, "notes.md"), "ab") as f:
            f.write(b"edited after packing\n")
        r = run("check", folder)
        self.assert_fail(r)
        self.assertTrue(any(l.startswith("FAIL changed") and "notes.md" in l
                            for l in out(r).splitlines()), out(r))

    def test_tampered_member_in_zip_fails_changed(self):
        _, zpath = self.packed_pkg()
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          replace={mem("notes.md"): b"edited after packing\n"})
        r = run("check", bad)
        self.assert_fail(r)
        self.assertTrue(any(l.startswith("FAIL changed") and "notes.md" in l
                            for l in out(r).splitlines()), out(r))

    def test_deleted_file_in_folder_fails_missing(self):
        folder, _ = self.packed_pkg()
        os.remove(os.path.join(folder, "notes.md"))
        r = run("check", folder)
        self.assert_fail(r)
        self.assertTrue(any(l.startswith("FAIL missing") and "notes.md" in l
                            for l in out(r).splitlines()), out(r))

    def test_deleted_member_in_zip_fails_missing(self):
        _, zpath = self.packed_pkg()
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          drop=[mem("notes.md")])
        r = run("check", bad)
        self.assert_fail(r)
        self.assertTrue(any(l.startswith("FAIL missing") and "notes.md" in l
                            for l in out(r).splitlines()), out(r))

    def test_added_file_in_folder_fails_unlisted(self):
        folder, _ = self.packed_pkg()
        write_file(os.path.join(folder, "extra.txt"), "not in the sums\n")
        r = run("check", folder)
        self.assert_fail(r)
        self.assertTrue(any(l.startswith("FAIL unlisted") and "extra.txt" in l
                            for l in out(r).splitlines()), out(r))

    def test_added_member_in_zip_fails_unlisted(self):
        _, zpath = self.packed_pkg()
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          add={mem("extra.txt"): b"not in the sums\n"})
        r = run("check", bad)
        self.assert_fail(r)
        self.assertTrue(any(l.startswith("FAIL unlisted") and "extra.txt" in l
                            for l in out(r).splitlines()), out(r))

    def test_package_without_sha256sums_fails(self):
        folder, zpath = self.packed_pkg()
        os.remove(os.path.join(folder, "SHA256SUMS"))
        self.assertEqual(run("check", folder).returncode, 1)
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          drop=[mem("SHA256SUMS")])
        self.assertEqual(run("check", bad).returncode, 1)

    def test_unsafe_relative_path_member_is_rejected(self):
        _, zpath = self.packed_pkg()
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          add={FOLDER + "/../evil.txt": b"escaped\n"})
        r = run("check", bad)
        self.assertEqual(r.returncode, 1, out(r))
        self.assertTrue(any(l.startswith("FAIL unsafe-path") for l in out(r).splitlines()), out(r))
        for dirpath, _dirs, files in os.walk(self.tmp):
            self.assertNotIn("evil.txt", files, "a member escaped the extraction directory")

    def test_absolute_path_member_is_rejected(self):
        _, zpath = self.packed_pkg()
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          add={"/tmp/courier-evil.txt": b"escaped\n"})
        r = run("check", bad)
        self.assertEqual(r.returncode, 1, out(r))
        self.assertTrue(any(l.startswith("FAIL unsafe-path") for l in out(r).splitlines()), out(r))

    def test_symlink_member_is_rejected(self):
        _, zpath = self.packed_pkg()
        link = zipfile.ZipInfo(mem("link-to-passwd"))
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bad = rewrite_zip(zpath, os.path.join(tempfile.mkdtemp(dir=self.tmp), "bad.zip"),
                          add={link: "/etc/passwd"})
        r = run("check", bad)
        self.assertEqual(r.returncode, 1, out(r))
        self.assertTrue(any(l.startswith("FAIL unsafe-path") for l in out(r).splitlines()), out(r))


class ReadbackTests(CourierCase):
    def readback_lines(self, r):
        return [l.strip() for l in r.stdout.splitlines()]

    def test_readback_template_has_required_parts(self):
        folder = self.make_pkg(bodies={
            "Asks": "1. Review.\n2. Confirm.\n3. Reply by Friday.",
            "Decisions relied on": dec_table([["D-1", "Use stdlib only", "Keeps install simple", "OD-14"],
                                              ["D-2", "Frozen schema", "Stable contract", "OD-16"]]),
        })
        r = run("readback", folder)
        self.assertEqual(r.returncode, 0, out(r))
        lines = self.readback_lines(r)
        self.assertIn("readback: 1", lines)
        self.assertIn("reply_to: " + TX_ID, lines)
        self.assertIn("id: " + RB_ID, lines)
        for n in (1, 2, 3):
            self.assertEqual(sum(1 for l in lines if l.startswith(f"Ask {n}: I understand this as:")), 1, n)
        self.assertEqual(sum(1 for l in lines if l.startswith("Ask ")), 3)
        for d in ("D-1", "D-2"):
            self.assertEqual(sum(1 for l in lines if l.startswith(f"{d}: I understand this as:")), 1, d)
        self.assertIn("## Ambiguities", lines)

    def test_readback_works_on_zip(self):
        folder = self.make_pkg()
        zpath = self.packed(folder)
        r = run("readback", zpath)
        self.assertEqual(r.returncode, 0, out(r))
        lines = self.readback_lines(r)
        self.assertIn("readback: 1", lines)
        self.assertIn("id: " + RB_ID, lines)
        self.assertIn("## Ambiguities", lines)


class BrainCardTests(CourierCase):
    def cards(self, r):
        return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]

    def test_one_card_per_row_with_required_fields(self):
        zpath = self.packed(self.make_pkg())
        r = run("brain", zpath)
        self.assertEqual(r.returncode, 0, out(r))
        objs = self.cards(r)
        self.assertEqual(len(objs), 1)
        obj = objs[0]
        self.assertEqual(obj["protocol_version"], "0")
        self.assertEqual(obj["writer_role"], "agent")
        self.assertEqual(obj["status"], "candidate")
        self.assertEqual(obj["pocket"], "project-courier/tools")
        self.assertEqual(obj["derived_from"], "transmittal:" + TX_ID)
        self.assertEqual(obj["idempotency_key"],
                         sha256_bytes((TX_ID + "|B-1|Use stdlib only|Simple install").encode("utf-8")))
        self.assertIsInstance(obj["text"], str)
        self.assertIn("Use stdlib only", obj["text"])
        self.assertIn("Simple install", obj["text"])
        s = obj["structured"]
        self.assertEqual(s["id"], "B-1")
        self.assertEqual(s["kind"], "decision")
        self.assertEqual(s["what"], "Use stdlib only")
        self.assertEqual(s["why"], "Simple install")
        self.assertEqual(s["evidence"], "strong: two passing tests")
        self.assertEqual(s["limits"], "none known")
        self.assertIsInstance(s["sources"], list)
        self.assertEqual(s["sources"], ["OD-14", "SPEC"])
        self.assertEqual(s["drawer"], "project-courier/tools")
        self.assertEqual(obj["pocket"], s["drawer"])

    def test_multiple_rows_give_multiple_cards_in_order(self):
        rows = [BRAIN_ROW,
                ["B-2", "killed", "Drop the cache", "Too slow", "moderate: one benchmark",
                 "single machine", "E-batch-2", "project-courier/perf"]]
        zpath = self.packed(self.make_pkg(bodies={"For the brain": brain_table(rows)}))
        objs = self.cards(run("brain", zpath))
        self.assertEqual([o["structured"]["id"] for o in objs], ["B-1", "B-2"])
        self.assertEqual(objs[1]["pocket"], "project-courier/perf")
        self.assertEqual(objs[1]["structured"]["sources"], ["E-batch-2"])
        self.assertEqual(objs[1]["idempotency_key"],
                         sha256_bytes((TX_ID + "|B-2|Drop the cache|Too slow").encode("utf-8")))

    def test_nothing_settled_writes_nothing_and_exits_zero(self):
        zpath = self.packed(self.make_pkg(bodies={"For the brain": "nothing settled"}))
        r = run("brain", zpath)
        self.assertEqual(r.returncode, 0, out(r))
        self.assertEqual(r.stdout.strip(), "")
        outfile = os.path.join(tempfile.mkdtemp(dir=self.tmp), "cards.jsonl")
        r2 = run("brain", zpath, "--out", outfile)
        self.assertEqual(r2.returncode, 0, out(r2))
        if os.path.exists(outfile):
            with open(outfile, "rb") as f:
                self.assertEqual(f.read().strip(), b"")

    def test_out_option_writes_the_same_json_lines(self):
        zpath = self.packed(self.make_pkg())
        stdout_run = run("brain", zpath)
        outfile = os.path.join(tempfile.mkdtemp(dir=self.tmp), "cards.jsonl")
        r = run("brain", zpath, "--out", outfile)
        self.assertEqual(r.returncode, 0, out(r))
        self.assertTrue(os.path.isfile(outfile))
        with open(outfile, encoding="utf-8") as f:
            file_objs = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(file_objs, self.cards(stdout_run))

    def test_repeated_runs_give_identical_output(self):
        zpath = self.packed(self.make_pkg())
        self.assertEqual(run("brain", zpath).stdout, run("brain", zpath).stdout)

    def test_brain_applies_validation_rules(self):
        folder = self.make_pkg(bodies={"For the brain": brain_table([["B-1", "idea"] + BRAIN_ROW[2:]])})
        self.assert_fail(run("brain", folder), "R6")


class UsageErrorTests(CourierCase):
    def expect_usage_error(self, *args):
        self.assertTrue(os.path.isfile(COURIER), "courier.py is missing")
        r = run(*args)
        self.assertEqual(r.returncode, 2, f"args={args}\n{out(r)}")

    def test_no_arguments(self):
        self.expect_usage_error()

    def test_unknown_command(self):
        self.expect_usage_error("frobnicate", self.make_pkg())

    def test_pack_without_folder(self):
        self.expect_usage_error("pack", "--out", os.path.join(self.tmp, "x.zip"))

    def test_pack_without_out(self):
        self.expect_usage_error("pack", self.make_pkg())

    def test_pack_missing_folder_path(self):
        self.expect_usage_error("pack", os.path.join(self.tmp, "no-such-folder"), "--out",
                                os.path.join(self.tmp, "x.zip"))

    def test_check_without_path(self):
        self.expect_usage_error("check")

    def test_check_missing_path(self):
        self.expect_usage_error("check", os.path.join(self.tmp, "no-such-package.zip"))

    def test_readback_without_path(self):
        self.expect_usage_error("readback")

    def test_brain_without_path(self):
        self.expect_usage_error("brain")


# @@APPEND@@


if __name__ == "__main__":
    unittest.main()
