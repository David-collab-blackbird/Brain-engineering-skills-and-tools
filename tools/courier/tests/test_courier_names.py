"""Independent test author session (model: haiku), written from SPEC.md v0.1.1 on 2026-10-24; implementation not seen.

Black-box tests for the party names of courier v0.1.1: SPEC section 1 (rule R1) and the
section 2 `template` bullet. Written from SPEC.md only. Standard library unittest only.
Synthetic data only (invented content, example.com).
Run from tools/courier:  python3 -I tests/test_courier_names.py

Revised 2026-10-24: SPEC.md section 1 now says each frontmatter value is trimmed of leading
and trailing whitespace before any check (as YAML plain values are). So `from: Aviary Builder `
(trailing space) is expected to PASS, and internal double spacing (`Aviary  Builder`) is a
near-miss that FAILS R1. The earlier version expected the trailing-space case to fail.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

COURIER = os.path.join(os.path.dirname(__file__), "..", "courier.py")
TX_ID = "TX-ENG-20261024-01"
PLAIN_NAMES = ["Engineer", "Brain builder", "Owner", "Aviary Orchestrator",
               "Aviary Builder", "Personal Builder"]
LEGACY_NAMES = ["Coordinator", "Agent 1", "Agent 2"]
ALL_NAMES = PLAIN_NAMES + LEGACY_NAMES
NEAR_MISSES = ["aviary orchestrator", "Aviary orchestrator", "Orchestrator",
               "Aviary  Builder", "Personal builder", "Agent 3", "Health Builder",
               "Brain Builder", "agent 1"]
HEADINGS = ["Purpose", "Asks", "Decisions relied on", "Supersedes", "Don't",
            "Reply format", "Needs the owner", "For the brain"]
BRAIN_COLS = ["id", "kind", "what", "why", "evidence", "limits", "sources", "drawer"]
BRAIN_ROW = ["B-1", "decision", "Use stdlib only", "Simple install",
             "strong: two passing tests", "none known", "OD-14, SPEC",
             "project-courier/tools"]


def out(r):
    return r.stdout + r.stderr


def run(*args):
    return subprocess.run([sys.executable, "-I", COURIER] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def brain_table(row):
    lines = ["| " + " | ".join(BRAIN_COLS) + " |", "|" + "---|" * len(BRAIN_COLS),
             "| " + " | ".join(row) + " |"]
    return "\n".join(lines)


def default_bodies():
    return {
        "Purpose": "Party-name test transmittal for the courier tests.",
        "Asks": "1. Review section 1 of the spec.\n2. Confirm the drawer name.",
        "Decisions relied on": "| id | decision | why | source |\n|---|---|---|---|\n"
                               "| D-1 | Use stdlib only | Keeps install simple | OD-14 |",
        "Supersedes": "none",
        "Don't": "none",
        "Reply format": "Reply with a READBACK file, one line per ask.",
        "Needs the owner": "- Approve the drawer name.",
        "For the brain": brain_table(BRAIN_ROW),
    }


def build_tx(fm=None):
    """Valid TRANSMITTAL.md text; fm overrides frontmatter keys (from/to by default Engineer/Owner)."""
    front = {"transmittal": "1", "id": TX_ID, "from": "Engineer", "to": "Owner",
             "date": "2026-10-24T18:59+10:30", "reply_to": "none"}
    front.update(fm or {})
    bodies = default_bodies()
    lines = ["---"] + [f"{k}: {v}" for k, v in front.items()] + ["---", f"# Transmittal {TX_ID}"]
    for h in HEADINGS:
        lines += [f"## {h}", bodies[h], ""]
    return "\n".join(lines) + "\n"


def other_party(name):
    return "Engineer" if name == "Owner" else "Owner"


def frontmatter_line(text, key):
    for line in text.splitlines():
        if line.strip().startswith(key + ":"):
            return line.strip()
    return None


class NameCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="courier-names-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make_pkg(self, text):
        root = tempfile.mkdtemp(dir=self.tmp)
        folder = os.path.join(root, TX_ID)
        os.mkdir(folder)
        write_file(os.path.join(folder, "TRANSMITTAL.md"), text)
        return folder

    def pack(self, folder):
        zpath = folder + ".zip"
        return run("pack", folder, "--out", zpath), zpath

    def assert_packs_and_checks(self, fm):
        rp, zpath = self.pack(self.make_pkg(build_tx(fm)))
        self.assertEqual(rp.returncode, 0, out(rp))
        rc = run("check", zpath)
        self.assertEqual(rc.returncode, 0, out(rc))

    def assert_r1_fail(self, fm):
        rp, zpath = self.pack(self.make_pkg(build_tx(fm)))
        o = out(rp)
        self.assertEqual(rp.returncode, 1, o)
        self.assertTrue(any(l.startswith("FAIL R1") for l in o.splitlines()), o)
        self.assertFalse(os.path.exists(zpath), "a zip was written for a failing package")
        return o


class PlainAndLegacyPassTests(NameCase):
    def test_plain_names_pass_in_from(self):
        for name in PLAIN_NAMES:
            with self.subTest(name=name):
                self.assert_packs_and_checks({"from": name, "to": other_party(name)})

    def test_plain_names_pass_in_to(self):
        for name in PLAIN_NAMES:
            with self.subTest(name=name):
                self.assert_packs_and_checks({"from": other_party(name), "to": name})

    def test_legacy_names_pass_in_from(self):
        for name in LEGACY_NAMES:
            with self.subTest(name=name):
                self.assert_packs_and_checks({"from": name, "to": other_party(name)})

    def test_legacy_names_pass_in_to(self):
        for name in LEGACY_NAMES:
            with self.subTest(name=name):
                self.assert_packs_and_checks({"from": other_party(name), "to": name})

    def test_trailing_space_is_trimmed_and_passes(self):
        # SPEC v0.1.1 section 1: values are trimmed before any check.
        self.assert_packs_and_checks({"from": "Aviary Builder ", "to": "Owner"})
        self.assert_packs_and_checks({"from": "Owner", "to": "Aviary Builder "})


class NearMissTests(NameCase):
    def test_near_misses_in_from_fail_r1(self):
        for bad in NEAR_MISSES:
            with self.subTest(side="from", value=bad):
                self.assert_r1_fail({"from": bad, "to": "Owner"})

    def test_near_misses_in_to_fail_r1(self):
        for bad in NEAR_MISSES:
            with self.subTest(side="to", value=bad):
                self.assert_r1_fail({"from": "Owner", "to": bad})

    def test_r1_failure_line_lists_all_nine_names(self):
        for side in ("from", "to"):
            with self.subTest(side=side):
                o = self.assert_r1_fail({side: "Janitor"})
                r1_lines = [l for l in o.splitlines() if l.startswith("FAIL R1")]
                self.assertTrue(any(all(n in l for n in ALL_NAMES) for l in r1_lines),
                                "no FAIL R1 line lists all nine names:\n" + o)

    def test_from_equal_to_fails_r1(self):
        for name in ALL_NAMES:
            with self.subTest(name=name):
                self.assert_r1_fail({"from": name, "to": name})


class TemplateTests(NameCase):
    def test_template_from_line_lists_plain_names_and_no_legacy_names(self):
        r = run("template")
        self.assertEqual(r.returncode, 0, out(r))
        line = frontmatter_line(r.stdout, "from")
        self.assertIsNotNone(line, r.stdout)
        for name in PLAIN_NAMES:
            self.assertIn(name, line)
        for name in LEGACY_NAMES:
            self.assertNotIn(name, line)

    def test_template_still_fails_pack(self):
        r = run("template")
        self.assertEqual(r.returncode, 0, out(r))
        rp, zpath = self.pack(self.make_pkg(r.stdout))
        o = out(rp)
        self.assertEqual(rp.returncode, 1, o)
        self.assertTrue(any(l.startswith("FAIL R3") for l in o.splitlines()), o)
        self.assertFalse(os.path.exists(zpath), "a zip was written for the template")


class AviaryOrchestratorPackageTests(NameCase):
    def test_aviary_orchestrator_package_checks_and_reads_back(self):
        folder = self.make_pkg(build_tx({"from": "Aviary Orchestrator", "to": "Owner"}))
        rp, zpath = self.pack(folder)
        self.assertEqual(rp.returncode, 0, out(rp))
        rc = run("check", zpath)
        self.assertEqual(rc.returncode, 0, out(rc))
        self.assertIn("Aviary Orchestrator", out(rc))
        rf = run("check", folder)
        self.assertEqual(rf.returncode, 0, out(rf))
        rr = run("readback", zpath)
        self.assertEqual(rr.returncode, 0, out(rr))
        rrf = run("readback", folder)
        self.assertEqual(rrf.returncode, 0, out(rrf))


if __name__ == "__main__":
    unittest.main()
