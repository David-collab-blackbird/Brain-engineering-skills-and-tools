# Independent test author session, written from GUARD-TOOLS.md @ 0a932426d49848d4afdd43fe18a34ac2bcdbf06e on 2026-10-24; implementation not seen.
"""ET-01 `manifest_check.py verify --manifest M --root D...`: MISSING, CHANGED,
UNLISTED, COUNTS-INVALID, the hash rule (SHA-256 after CRLF->LF), comments, the
manifest excluding itself, ignored caches, and the §0 output contract."""
import json
import sys
import unittest
from pathlib import Path

try:
    from . import support_et01 as S
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import support_et01 as S
K = S.K


class VerifyBase(unittest.TestCase):
    def setUp(self):
        self.tmp = K.TempDir(self)
        self.root = self.tmp.path / "repo"
        self.root.mkdir()
        for rel, content in S.SUITE.items():
            K.write_bytes(self.root, rel, content)

    def seal(self, **kw):
        S.write_manifest(self.root, **kw)

    def verify(self, *extra, roots=(S.ROOT,), manifest=S.MANIFEST, as_json=True, env=None):
        args = ["verify", "--repo", self.root, "--manifest", manifest, "--root", *roots, *extra]
        if as_json:
            args.append("--json")
        return K.run(S.tool(), args, cwd=self.root, env=env or K.child_env())


class TestVerifyFindings(VerifyBase):
    def test_sealed_suite_verifies_clean(self):
        self.seal()
        r = self.verify()
        K.assert_clean(self, r)
        K.assert_json_contract(self, r)

    def test_changed_file_is_CHANGED(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/test_alpha.py", S.TEST_ALPHA + "# edited\n")
        r = self.verify()
        K.assert_exit(self, r, 1)
        K.assert_rule(self, r, "CHANGED", path="tests/acceptance/WP-A/test_alpha.py")

    def test_missing_file_is_MISSING(self):
        self.seal()
        (self.root / "tests/acceptance/WP-B/test_beta.py").unlink()
        r = self.verify()
        K.assert_exit(self, r, 1)
        K.assert_rule(self, r, "MISSING", path="tests/acceptance/WP-B/test_beta.py")

    def test_unlisted_file_is_UNLISTED(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/test_extra.py", "import unittest\n")
        r = self.verify()
        K.assert_exit(self, r, 1)
        K.assert_rule(self, r, "UNLISTED", path="tests/acceptance/WP-A/test_extra.py")

    def test_golden_regenerated_is_CHANGED(self):
        # E16 RH-3: a regenerated golden file differs from the sealed hash.
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/golden/receipts.json", '{"receipt": "r-999"}\n')
        r = self.verify()
        K.assert_rule(self, r, "CHANGED", path="tests/acceptance/WP-A/fixtures/golden/receipts.json")

    def test_fixture_tampering_is_CHANGED(self):
        # E16 X2: fixture edited so expectations match the code.
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/world.json", '{"items": [1, 2]}\n')
        r = self.verify()
        K.assert_rule(self, r, "CHANGED", path="tests/acceptance/WP-A/fixtures/world.json")

    def test_renamed_test_file_is_MISSING_and_UNLISTED(self):
        # E16 PL-2 / RH-1: rename a test file so it is no longer collected.
        self.seal()
        src = self.root / "tests/acceptance/WP-B/test_beta.py"
        src.rename(self.root / "tests/acceptance/WP-B/beta_disabled.py")
        r = self.verify()
        K.assert_rule(self, r, "MISSING", path="tests/acceptance/WP-B/test_beta.py")
        K.assert_rule(self, r, "UNLISTED", path="tests/acceptance/WP-B/beta_disabled.py")

    def test_deleted_suite_is_MISSING_for_every_file(self):
        self.seal()
        for p in sorted((self.root / "tests/acceptance/WP-A").rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        (self.root / "tests/acceptance/WP-A").rmdir()
        r = self.verify()
        missing = {K.norm_path(f["path"]) for f in K.with_rule(r.json["findings"], "MISSING")}
        self.assertTrue({
            "tests/acceptance/WP-A/test_alpha.py",
            "tests/acceptance/WP-A/fixtures/world.json",
            "tests/acceptance/WP-A/fixtures/golden/receipts.json",
        } <= missing, r.describe())

    def test_all_three_kinds_reported_together(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/test_alpha.py", "changed\n")
        (self.root / "tests/acceptance/WP-B/test_beta.py").unlink()
        K.write_bytes(self.root, "tests/acceptance/WP-B/test_new.py", "new\n")
        r = self.verify(as_json=False)
        K.assert_text_contract(self, r)
        self.assertEqual(sorted(K.rules(r.findings)), ["CHANGED", "MISSING", "UNLISTED"], r.describe())
        self.assertEqual(r.summary, 3, r.describe())


class TestHashRule(VerifyBase):
    def test_crlf_checkout_matches_lf_manifest(self):
        self.seal()
        crlf = S.TEST_ALPHA.replace("\n", "\r\n")
        K.write_bytes(self.root, "tests/acceptance/WP-A/test_alpha.py", crlf)
        r = self.verify()
        K.assert_clean(self, r)

    def test_lone_cr_is_not_normalised(self):
        # The rule is CRLF->LF only; a lone CR is content.
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/test_alpha.py", S.TEST_ALPHA.replace("\n", "\r", 1))
        r = self.verify()
        K.assert_rule(self, r, "CHANGED", path="tests/acceptance/WP-A/test_alpha.py")

    def test_hash_is_sha256_of_lf_content(self):
        # A hand-written manifest line with the oracle hash of the LF content verifies.
        K.write_bytes(self.root, "tests/acceptance/WP-B/test_beta.py", S.TEST_BETA.replace("\n", "\r\n"))
        self.seal()  # oracle hashes after CRLF->LF
        lines = (self.root / S.MANIFEST).read_text(encoding="utf-8")
        expected = K.sha256_hex(S.TEST_BETA.encode("utf-8"))
        self.assertIn(f"{expected}  tests/acceptance/WP-B/test_beta.py", lines)
        K.assert_clean(self, self.verify())

    def test_binary_file_is_hashed_with_the_same_rule(self):
        # SPEC-AMBIGUITY: the spec makes no exception for binary files, so CRLF
        # bytes inside a binary fixture are normalised too.
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/blob.bin", b"\x00\x01\r\n\xff\xfe\r\n")
        self.seal()
        K.assert_clean(self, self.verify())

    def test_one_byte_change_is_detected(self):
        self.seal()
        data = (self.root / "tests/acceptance/WP-A/fixtures/world.json").read_bytes()
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/world.json", data.replace(b"3", b"4"))
        K.assert_rule(self, self.verify(), "CHANGED")


class TestManifestFormat(VerifyBase):
    def test_comment_lines_are_ignored(self):
        self.seal()
        text = (self.root / S.MANIFEST).read_text(encoding="utf-8").splitlines()
        text.insert(3, "# a comment between entries")
        text.append("# trailing comment")
        K.write_bytes(self.root, S.MANIFEST, "\n".join(text) + "\n")
        K.assert_clean(self, self.verify())

    def test_manifest_with_crlf_line_endings_parses(self):
        self.seal(newline="\r\n")
        K.assert_clean(self, self.verify())

    def test_manifest_excludes_itself(self):
        self.seal()
        r = self.verify()
        K.assert_no_rule(self, r, "UNLISTED", path=S.MANIFEST)
        K.assert_clean(self, r)

    def test_pycache_and_pyc_are_ignored(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/__pycache__/test_alpha.cpython-313.pyc", b"\x00cache")
        K.write_bytes(self.root, "tests/acceptance/WP-A/stray.pyc", b"\x00cache")
        K.write_bytes(self.root, "tests/acceptance/__pycache__/x.txt", "cache dir content\n")
        r = self.verify()
        K.assert_clean(self, r)

    def test_listed_pyc_is_not_required(self):
        # A cache file that disappears is not MISSING either.
        K.write_bytes(self.root, "tests/acceptance/WP-A/__pycache__/m.cpython-313.pyc", b"\x00")
        self.seal()
        (self.root / "tests/acceptance/WP-A/__pycache__/m.cpython-313.pyc").unlink()
        K.assert_no_rule(self, self.verify(), "MISSING")

    def test_unicode_file_name(self):
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/café-über.json", '{"k": "é"}\n')
        self.seal()
        K.assert_clean(self, self.verify())
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/café-über.json", '{"k": "e"}\n')
        r = self.verify()
        K.assert_rule(self, r, "CHANGED", path="tests/acceptance/WP-A/fixtures/café-über.json")

    def test_unicode_file_name_under_platform_default_encoding(self):
        # Windows CI pipes stdout in the ANSI code page unless told otherwise; the
        # tool must still report (exit 1), not crash.
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/ümläut.json", "{}\n")
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/fixtures/ümläut.json", "[]\n")
        r = self.verify(as_json=False, env=K.child_env(utf8=False))
        K.assert_exit(self, r, 1)
        self.assertEqual(r.summary, 1, r.describe())

    def test_paths_are_repo_relative_with_forward_slashes(self):
        K.write_bytes(self.root, "tests/acceptance/WP-A/sub/deep/test_deep.py", "x = 1\n")
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/sub/deep/test_deep.py", "x = 2\n")
        r = self.verify()
        hits = K.assert_rule(self, r, "CHANGED")
        self.assertEqual(hits[0]["path"], "tests/acceptance/WP-A/sub/deep/test_deep.py", r.describe())

    def test_multiple_roots(self):
        K.write_bytes(self.root, "tests/contract/test_c1.py", "c = 1\n")
        S.write_manifest(self.root, roots=(S.ROOT, "tests/contract"))
        K.assert_clean(self, self.verify(roots=(S.ROOT, "tests/contract")))
        K.write_bytes(self.root, "tests/contract/test_c2.py", "c = 2\n")
        r = self.verify(roots=(S.ROOT, "tests/contract"))
        K.assert_rule(self, r, "UNLISTED", path="tests/contract/test_c2.py")

    def test_empty_root_and_empty_manifest_is_clean(self):
        empty = self.root / "tests/empty"
        empty.mkdir(parents=True)
        K.write_bytes(self.root, "tests/empty/MANIFEST.sha256", "# nothing sealed\n")
        r = self.verify(roots=("tests/empty",), manifest="tests/empty/MANIFEST.sha256")
        K.assert_clean(self, r)

    def test_empty_manifest_with_files_lists_each_as_UNLISTED(self):
        K.write_bytes(self.root, S.MANIFEST, "# nothing sealed\n")
        r = self.verify()
        unlisted = {K.norm_path(f["path"]) for f in K.with_rule(r.json["findings"], "UNLISTED")}
        self.assertEqual(unlisted, set(S.SUITE), r.describe())

    def test_malformed_manifest_line_fails_closed(self):
        self.seal()
        with open(self.root / S.MANIFEST, "ab") as fh:
            fh.write(b"not-a-hash tests/acceptance/WP-A/test_alpha.py\n")
        K.assert_fail_closed(self, self.verify())

    def test_single_space_separator_fails_closed(self):
        # Lines are `<hex>` + two spaces + `<path>`.
        entries = S.manifest_entries(self.root)
        K.write_bytes(self.root, S.MANIFEST, "".join(f"{h} {rel}\n" for rel, h in entries))
        K.assert_fail_closed(self, self.verify())

    def test_missing_manifest_file_fails_closed(self):
        K.assert_fail_closed(self, self.verify())

    def test_missing_root_fails_closed(self):
        self.seal()
        K.assert_fail_closed(self, self.verify(roots=("tests/no-such-root",)))


class TestExpectedCounts(VerifyBase):
    def counts(self, value):
        K.write_bytes(self.root, "tests/acceptance/EXPECTED_COUNTS.json", value)
        self.seal()
        return self.verify()

    def test_valid_counts_pass(self):
        r = self.counts(json.dumps({"WP-A": 2, "WP-B": 1}))
        K.assert_no_rule(self, r, "COUNTS-INVALID")
        K.assert_clean(self, r)

    def test_suite_folder_must_exist(self):
        r = self.counts(json.dumps({"WP-A": 2, "WP-Z": 4}))
        K.assert_exit(self, r, 1)
        K.assert_rule(self, r, "COUNTS-INVALID")

    def test_non_positive_or_non_integer_counts_are_invalid(self):
        for bad in (0, -1, "2", 2.5, None, [2], {"n": 2}):
            with self.subTest(value=bad):
                r = self.counts(json.dumps({"WP-A": bad, "WP-B": 1}))
                K.assert_rule(self, r, "COUNTS-INVALID")

    def test_boolean_is_not_an_integer(self):
        # JSON true must not pass as the integer 1.
        r = self.counts(json.dumps({"WP-A": True, "WP-B": 1}))
        K.assert_rule(self, r, "COUNTS-INVALID")

    def test_float_with_integer_value_is_invalid(self):
        # SPEC-AMBIGUITY: "positive integer" read as the JSON integer type; 2.0 fails.
        r = self.counts('{"WP-A": 2.0, "WP-B": 1}')
        K.assert_rule(self, r, "COUNTS-INVALID")

    def test_top_level_must_be_an_object(self):
        r = self.counts(json.dumps([["WP-A", 2]]))
        K.assert_rule(self, r, "COUNTS-INVALID")

    def test_malformed_json_is_invalid(self):
        r = self.counts('{"WP-A": 2,,}')
        K.assert_rule(self, r, "COUNTS-INVALID")

    def test_empty_counts_file_is_invalid(self):
        r = self.counts("")
        K.assert_rule(self, r, "COUNTS-INVALID")

    def test_root_without_counts_file_is_not_flagged(self):
        # SPEC-AMBIGUITY: ET-07 reuses `verify` on the hidden repo, whose suites carry
        # expected.json instead, so an absent EXPECTED_COUNTS.json is not a finding.
        (self.root / "tests/acceptance/EXPECTED_COUNTS.json").unlink()
        self.seal()
        r = self.verify()
        K.assert_no_rule(self, r, "COUNTS-INVALID")
        K.assert_clean(self, r)


class TestOutputContract(VerifyBase):
    def test_text_output_clean(self):
        self.seal()
        r = self.verify(as_json=False)
        K.assert_text_contract(self, r)
        self.assertEqual(r.lines, ["OK"], r.describe())

    def test_text_output_findings(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-B/test_beta.py", "edited\n")
        r = self.verify(as_json=False)
        K.assert_text_contract(self, r)
        self.assertEqual(r.findings[0]["rule"], "CHANGED")
        self.assertEqual(r.findings[0]["path"], "tests/acceptance/WP-B/test_beta.py")

    def test_json_contract_with_findings(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-B/test_beta.py", "edited\n")
        data = K.assert_json_contract(self, self.verify())
        self.assertFalse(data["ok"])

    def test_fingerprints_are_stable_and_distinct(self):
        self.seal()
        K.write_bytes(self.root, "tests/acceptance/WP-A/test_alpha.py", "edited a\n")
        K.write_bytes(self.root, "tests/acceptance/WP-B/test_beta.py", "edited b\n")
        first = self.verify().json["findings"]
        second = self.verify().json["findings"]
        fp1 = sorted(f["fingerprint"] for f in first)
        fp2 = sorted(f["fingerprint"] for f in second)
        self.assertEqual(fp1, fp2, "fingerprints must be deterministic")
        self.assertEqual(len(set(fp1)), len(fp1), "different paths must give different fingerprints")

    def test_never_runs_code_from_the_scanned_repo(self):
        sentinel = self.tmp.path / "SENTINEL-ran.txt"
        for rel, content in K.sentinel_files(sentinel).items():
            K.write_bytes(self.root, rel, content)
        K.write_bytes(self.root, "tests/acceptance/conftest.py", f"open({str(sentinel)!r}, 'a').write('x')\n")
        self.seal()
        r = self.verify()
        self.assertFalse(sentinel.exists(), f"the tool executed repo code{r.describe()}")
        K.assert_clean(self, r)


if __name__ == "__main__":
    unittest.main()
