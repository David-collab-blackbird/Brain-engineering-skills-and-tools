# Independent test author session, written from GUARD-TOOLS.md @ 0a932426d49848d4afdd43fe18a34ac2bcdbf06e on 2026-10-24; implementation not seen.
"""Shared helpers for the guard-tool tests (ET-01 to ET-09 and run_guards.py).

Written from blueprint/GUARD-TOOLS.md alone. Nothing here knows how a tool is
implemented: tools are only ever invoked as separate processes, exactly as the
spec names them (`python <tool>.py <subcommand> --repo <dir> ...`).

Where the tools are looked for:
  * `GUARD_TOOLS_DIR` (optional): a vendored `.github/guards/` folder, flat layout
    (`<dir>/manifest_check.py`, `<dir>/hooks/protect.py`, ...). Lets the same tests
    run against a vendored copy in a product repo.
  * otherwise `tools/<tool-dir>/src/<script>` in this repo (README layout).

A missing tool is a test FAILURE (AssertionError), never a skip, so the suite
fails until the tool exists. Standard library only; Windows and Linux.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path

BLUEPRINT_COMMIT = "0a932426d49848d4afdd43fe18a34ac2bcdbf06e"
TOOLS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 300

# Synthetic logins (generic roles, invented). Logins reach the tools only through
# the repository variables named in GUARD-TOOLS §0, never from code.
OWNER = "owner-account"
ENGINEER = "engineer-machine"
BUILDER = "builder-account"
STRANGER = "stranger-account"
LOGINS_T3 = {  # after T-3: three distinct identities
    "BRAIN_OWNER_LOGIN": OWNER,
    "BRAIN_ENGINEER_LOGIN": ENGINEER,
    "BRAIN_BUILDER_LOGIN": BUILDER,
}
LOGINS_PRE_T3 = {  # before T-3 the builder uses the owner's login (TANDEM §4)
    "BRAIN_OWNER_LOGIN": OWNER,
    "BRAIN_ENGINEER_LOGIN": ENGINEER,
    "BRAIN_BUILDER_LOGIN": OWNER,
}

# Environment the child tool must not inherit from the machine running the tests,
# so results do not depend on where the tests run. Tests set these explicitly.
SCRUB = (
    "BRAIN_OWNER_LOGIN", "BRAIN_ENGINEER_LOGIN", "BRAIN_BUILDER_LOGIN",
    "PRIVACY_ALIAS_TABLE", "GITHUB_TOKEN", "GH_TOKEN", "CI", "GITHUB_ACTIONS",
    "GITHUB_EVENT_PATH", "GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF",
    "PYTEST_CURRENT_TEST", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME",
    "CLAUDE_PROJECT_DIR", "CLAUDE_CONFIG_DIR",
)

# Canonical engineer-owned configuration, copied from GUARD-TOOLS.md (§0 and the
# `protected_paths.json` paragraph). Tests install these into fixture repos at
# `.github/guards/`; they are also what a tool shipped with its own copy must hold.
PROTECTED_PATHS = {
    "write_protected": [
        "tests/acceptance/**", "blueprint/**", "packages/**", ".github/**", ".claude/**",
        "ops/**", "eval/results/**", ".githooks/**", "CLAUDE.md", ".gitattributes",
    ],
    "protected_areas": [
        "src/brain/access/**", "src/brain/gate/**", "src/brain/egress/**",
        "src/brain/crypto/**", "src/brain/consent/**", "src/brain/money/**",
        "src/brain/approvals/**", "src/brain/release/**", "src/brain/dispatch/**",
        "src/brain/access/credentials*", "src/brain/store/erasure*",
        "src/brain/store/migrations/**",
    ],
}
PROTECTED_AREA_NAMES = (
    "access", "gate", "egress", "crypto", "consent", "money", "approvals", "release", "dispatch",
)
# SPEC-AMBIGUITY: GUARD-TOOLS §0 names the checks and that each maps to "its
# workflow file"; the file names come from WP-G0a (guards.yml, visible-acceptance.yml)
# and WP-G0b (hidden-acceptance.yml). Values are repo-relative workflow paths.
REQUIRED_CHECKS = {
    "guard-manifest": ".github/workflows/guards.yml",
    "guard-flagger": ".github/workflows/guards.yml",
    "guard-privacy": ".github/workflows/guards.yml",
    "guard-lint": ".github/workflows/guards.yml",
    "guard-markers": ".github/workflows/guards.yml",
    "guard-state": ".github/workflows/guards.yml",
    "visible-acceptance (ubuntu-latest)": ".github/workflows/visible-acceptance.yml",
    "visible-acceptance (windows-latest)": ".github/workflows/visible-acceptance.yml",
    "hidden-acceptance": ".github/workflows/hidden-acceptance.yml",
}

HEX16 = re.compile(r"^[0-9a-f]{16}$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+")
FINDING_RE = re.compile(r"^FINDING (?P<rule>\S+) (?P<loc>\S+)(?: (?P<detail>.*))?$")
SUMMARY_RE = re.compile(r"^(OK|FINDINGS (?P<n>\d+))$")


# --------------------------------------------------------------------------- tools

def tool_path(tool_dir: str, script: str) -> Path:
    """Path of a guard tool script; AssertionError (a test failure) if absent."""
    override = os.environ.get("GUARD_TOOLS_DIR")
    if override:
        path = Path(override) / script
    else:
        path = TOOLS_DIR / tool_dir / "src" / script
    if not path.is_file():
        raise AssertionError(
            f"guard tool not found: {path} (spec: blueprint/GUARD-TOOLS.md @ {BLUEPRINT_COMMIT[:7]}; "
            f"expected tools/{tool_dir}/src/{script} or $GUARD_TOOLS_DIR/{script})"
        )
    return path


_EMPTY_GITCONFIG: str | None = None


def _empty_gitconfig() -> str:
    global _EMPTY_GITCONFIG
    if _EMPTY_GITCONFIG is None or not Path(_EMPTY_GITCONFIG).exists():
        fd, name = tempfile.mkstemp(prefix="guardkit-gitconfig-")
        os.close(fd)
        _EMPTY_GITCONFIG = name
    return _EMPTY_GITCONFIG


GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "author@example.com",
}


def child_env(extra: dict | None = None, remove: tuple = (), utf8: bool = True) -> dict:
    env = dict(os.environ)
    for key in SCRUB:
        env.pop(key, None)
    if utf8:
        env["PYTHONIOENCODING"] = "utf-8"
    else:
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONUTF8", None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = _empty_gitconfig()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.update(GIT_IDENTITY)
    if extra:
        env.update(extra)
    for key in remove:
        env.pop(key, None)
    return env


@dataclass
class Result:
    rc: int
    out: str
    err: str
    args: list = field(default_factory=list)

    def describe(self) -> str:
        return (f"\n--- command: {self.args}\n--- exit code: {self.rc}\n--- stdout:\n{self.out[-4000:]}"
                f"\n--- stderr:\n{self.err[-4000:]}")

    @property
    def lines(self) -> list[str]:
        return [ln.rstrip("\r") for ln in self.out.splitlines() if ln.strip()]

    @property
    def findings(self) -> list[dict]:
        """FINDING lines parsed from text output."""
        found = []
        for ln in self.lines:
            m = FINDING_RE.match(ln)
            if not m:
                continue
            loc = m.group("loc")
            path, line = loc, None
            if ":" in loc:
                head, tail = loc.rsplit(":", 1)
                if tail.isdigit():
                    path, line = head, int(tail)
            found.append({"rule": m.group("rule"), "path": path, "line": line,
                          "detail": m.group("detail") or ""})
        return found

    @property
    def summary(self):
        """'OK', an int n for 'FINDINGS n', or None if the last line is neither."""
        if not self.lines:
            return None
        m = SUMMARY_RE.match(self.lines[-1].strip())
        if not m:
            return None
        return "OK" if m.group(1) == "OK" else int(m.group("n"))

    @property
    def json(self) -> dict:
        try:
            return json.loads(self.out)
        except ValueError as exc:
            raise AssertionError(f"--json output is not one JSON document: {exc}{self.describe()}")


def run(script: Path, args: list, cwd: Path | None = None, env: dict | None = None,
        stdin: str | bytes | None = None, timeout: int = DEFAULT_TIMEOUT) -> Result:
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    data = stdin.encode("utf-8") if isinstance(stdin, str) else stdin
    proc = subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, env=env if env is not None else child_env(),
        input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    return Result(proc.returncode, out, err, cmd)


# ---------------------------------------------------------------------- assertions

def rules(findings: list[dict]) -> list[str]:
    return [f.get("rule") for f in findings]


def rule_matches(rule: str, alternatives) -> bool:
    if isinstance(alternatives, str):
        alternatives = (alternatives,)
    norm = rule.replace(" ", "")
    return any(norm == a.replace(" ", "") for a in alternatives)


def with_rule(findings: list[dict], alternatives) -> list[dict]:
    return [f for f in findings if rule_matches(str(f.get("rule")), alternatives)]


def findings_of(result: Result, data: dict | None = None) -> list[dict]:
    """Findings from --json output when the run used --json, else from text output."""
    if data is not None:
        return data["findings"]
    if "--json" in result.args:
        data = result.json
        if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
            raise AssertionError(f"--json output has no findings list{result.describe()}")
        return data["findings"]
    return result.findings


def assert_rule(tc: unittest.TestCase, result: Result, alternatives, path: str | None = None,
                data: dict | None = None) -> list[dict]:
    """Assert at least one finding with one of the rule names (optionally on `path`)."""
    findings = findings_of(result, data)
    hits = with_rule(findings, alternatives)
    if path is not None:
        hits = [f for f in hits if norm_path(f.get("path")) == path]
    tc.assertTrue(hits, f"expected a {alternatives} finding" + (f" on {path}" if path else "")
                  + f"; got rules {rules(findings)}{result.describe()}")
    return hits


def assert_no_rule(tc: unittest.TestCase, result: Result, alternatives, path: str | None = None,
                   data: dict | None = None) -> None:
    findings = findings_of(result, data)
    hits = with_rule(findings, alternatives)
    if path is not None:
        hits = [f for f in hits if norm_path(f.get("path")) == path]
    tc.assertFalse(hits, f"unexpected {alternatives} finding(s): {hits}{result.describe()}")


def norm_path(path) -> str | None:
    if path is None:
        return None
    return str(path).replace("\\", "/")


def assert_exit(tc: unittest.TestCase, result: Result, code: int) -> None:
    tc.assertEqual(result.rc, code, f"expected exit {code}{result.describe()}")


def assert_clean(tc: unittest.TestCase, result: Result) -> None:
    """Exit 0 with no findings (works for text and --json runs)."""
    assert_exit(tc, result, 0)
    if "--json" in result.args:
        data = result.json
        tc.assertEqual(data.get("findings"), [], result.describe())
        tc.assertIs(data.get("ok"), True, result.describe())
    else:
        tc.assertEqual(result.summary, "OK", f"expected final line OK{result.describe()}")


def assert_usage_error(tc: unittest.TestCase, result: Result) -> None:
    """GUARD-TOOLS §0: exit 2 on usage or internal error."""
    tc.assertEqual(result.rc, 2, f"expected exit 2 (usage or internal error){result.describe()}")


def assert_fail_closed(tc: unittest.TestCase, result: Result) -> None:
    """Bad input with no named rule: never exit 0. Either exit 2 (usage or internal
    error) or exit 1 with a well-formed findings report (a deliberate finding)."""
    tc.assertNotEqual(result.rc, 0, f"bad input must never exit 0{result.describe()}")
    if result.rc == 1:
        if "--json" in result.args:
            data = result.json
            tc.assertTrue(data.get("findings"), f"exit 1 without findings{result.describe()}")
        else:
            tc.assertIsInstance(result.summary, int, f"exit 1 must end with FINDINGS <n>{result.describe()}")
    else:
        tc.assertEqual(result.rc, 2, f"expected exit 2 or a reported finding{result.describe()}")


def assert_text_contract(tc: unittest.TestCase, result: Result) -> None:
    """GUARD-TOOLS §0 text output: FINDING lines, then OK or FINDINGS <n>; exit 0/1."""
    lines = result.lines
    tc.assertTrue(lines, f"no output{result.describe()}")
    body, last = lines[:-1], lines[-1].strip()
    for ln in body:
        tc.assertRegex(ln, FINDING_RE, f"non-FINDING line before the summary{result.describe()}")
        loc = FINDING_RE.match(ln).group("loc")
        tc.assertRegex(loc, r"^.+:\d+$", f"location must be <path>:<line>{result.describe()}")
    tc.assertRegex(last, SUMMARY_RE, f"last line must be OK or FINDINGS <n>{result.describe()}")
    if last == "OK":
        tc.assertEqual(body, [], result.describe())
        tc.assertEqual(result.rc, 0, result.describe())
    else:
        tc.assertEqual(int(last.split()[1]), len(body), f"FINDINGS count != FINDING lines{result.describe()}")
        tc.assertGreater(len(body), 0, result.describe())
        tc.assertEqual(result.rc, 1, result.describe())


def assert_json_contract(tc: unittest.TestCase, result: Result) -> dict:
    """GUARD-TOOLS §0 --json: {tool, version, check, ok, findings: [{rule, path, line,
    fingerprint, detail}]}; fingerprint = 16 hex."""
    data = result.json
    tc.assertIsInstance(data, dict, result.describe())
    for key in ("tool", "version", "check", "ok", "findings"):
        tc.assertIn(key, data, f"--json output lacks '{key}'{result.describe()}")
    tc.assertIsInstance(data["tool"], str)
    tc.assertTrue(data["tool"].strip(), "tool must be named")
    tc.assertIsInstance(data["version"], str)
    # SPEC-AMBIGUITY: VERSION holds "ET-NN <semver>" lines; we expect the JSON
    # version to be that semver.
    tc.assertRegex(data["version"], SEMVER, "version should be a semver string")
    tc.assertIsInstance(data["check"], str)
    tc.assertTrue(data["check"].strip(), "check must be named")
    tc.assertIsInstance(data["ok"], bool)
    tc.assertIsInstance(data["findings"], list)
    for f in data["findings"]:
        for key in ("rule", "path", "line", "fingerprint", "detail"):
            tc.assertIn(key, f, f"finding lacks '{key}': {f}")
        tc.assertIsInstance(f["rule"], str)
        tc.assertRegex(str(f["fingerprint"]), HEX16, f"fingerprint must be 16 lowercase hex: {f}")
        tc.assertIsInstance(f["detail"], str)
        # SPEC-AMBIGUITY: file-level findings have no natural line; we accept a
        # non-negative integer or null.
        tc.assertTrue(f["line"] is None or (isinstance(f["line"], int) and not isinstance(f["line"], bool)
                                            and f["line"] >= 0), f"line must be int >= 0 or null: {f}")
    tc.assertEqual(data["ok"], len(data["findings"]) == 0, f"ok must mirror findings{result.describe()}")
    tc.assertEqual(result.rc, 0 if data["ok"] else 1, f"exit code must match ok{result.describe()}")
    return data


def assert_not_leaked(tc: unittest.TestCase, result: Result, secret: str) -> None:
    blob = (result.out + result.err).lower()
    tc.assertNotIn(secret.lower(), blob, f"secret or alias term printed{result.describe()}")


# ---------------------------------------------------------------------- files, git

def write_bytes(root: Path, rel: str, content) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.write_bytes(content)  # bytes: no newline translation on Windows
    return path


def lf_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TempDir:
    """Context-free temp dir with Windows-safe cleanup (git objects are read-only)."""

    def __init__(self, tc: unittest.TestCase | None = None, prefix: str = "guardtest-"):
        self._tmp = tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True)
        self.path = Path(self._tmp.name).resolve()
        if tc is not None:
            tc.addCleanup(self.cleanup)

    def cleanup(self):
        def onerror(func, p, exc):
            try:
                os.chmod(p, 0o700)
                func(p)
            except OSError:
                pass
        if self.path.exists():
            shutil.rmtree(self.path, onerror=onerror) if sys.version_info < (3, 12) else \
                shutil.rmtree(self.path, onexc=onerror)
        self._tmp.cleanup()


class Repo:
    """A throwaway git repository for one test."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.safecrlf", "false")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args, check: bool = True) -> str:
        proc = subprocess.run(["git", *args], cwd=str(self.root), env=child_env(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and proc.returncode != 0:
            raise RuntimeError(f"git {args} failed: {proc.stderr.decode('utf-8', 'replace')}")
        return proc.stdout.decode("utf-8", errors="replace").strip()

    def write(self, rel: str, content) -> Path:
        return write_bytes(self.root, rel, content)

    def write_many(self, files: dict) -> None:
        for rel, content in files.items():
            if content is None:
                self.delete(rel)
            else:
                self.write(rel, content)

    def delete(self, rel: str) -> None:
        path = self.root / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()

    def rename(self, old: str, new: str) -> None:
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        self.git("mv", old, new)

    def commit(self, message: str = "change", allow_empty: bool = True) -> str:
        self.git("add", "-A")
        args = ["commit", "-q", "--no-verify", "-m", message]
        if allow_empty:
            args.insert(1, "--allow-empty")
        self.git(*args)
        return self.head()

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def checkout(self, ref: str, new_branch: str | None = None) -> None:
        if new_branch:
            self.git("checkout", "-q", "-B", new_branch, ref)
        else:
            self.git("checkout", "-q", ref)

    def diff(self, base: str, head: str) -> str:
        return self.git("diff", "--no-color", "--no-ext-diff", "-M", base, head) + "\n"


def make_repo(tc: unittest.TestCase, files: dict, message: str = "base") -> tuple[Repo, str]:
    tmp = TempDir(tc)
    repo = Repo(tmp.path / "repo")
    repo.write_many(files)
    sha = repo.commit(message)
    return repo, sha


def install_guard_config(root: Path, protected=True, checks=True) -> None:
    """Write the canonical engineer-owned config into <root>/.github/guards/."""
    if protected:
        write_bytes(root, ".github/guards/protected_paths.json", json.dumps(PROTECTED_PATHS, indent=2) + "\n")
    if checks:
        write_bytes(root, ".github/guards/required-checks.json", json.dumps(REQUIRED_CHECKS, indent=2) + "\n")


def sentinel_files(sentinel: Path) -> dict:
    """Files that write `sentinel` if anything in the scanned repo is ever executed
    or imported (GUARD-TOOLS §0: never runs code from the repo it scans)."""
    s = repr(str(sentinel))
    payload = f"open({s}, 'a').write('ran\\n')\n"
    return {
        "sitecustomize.py": payload,
        "usercustomize.py": payload,
        "conftest.py": payload,
        "setup.py": payload,
        "src/sitecustomize.py": payload,
        "src/conftest.py": payload,
        "src/brain/__init__.py": payload,
        "src/brain/constants.py": payload + "LABEL = 'harbour-tide-label'\n",
        "tests/conftest.py": payload,
        "tests/__init__.py": payload,
    }


# ------------------------------------------------------------ synthetic PII values

def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def tfn_ok(digits: str) -> bool:
    weights = (1, 4, 3, 7, 5, 8, 6, 9, 10)
    return len(digits) == 9 and sum(int(d) * w for d, w in zip(digits, weights)) % 11 == 0


def abn_ok(digits: str) -> bool:
    if len(digits) != 11:
        return False
    weights = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
    nums = [int(d) for d in digits]
    nums[0] -= 1
    return sum(n * w for n, w in zip(nums, weights)) % 89 == 0


def first_valid(start: int, width: int, ok) -> str:
    n = start
    while True:
        s = str(n).zfill(width)
        if ok(s):
            return s
        n += 1


def synthetic_tfn() -> str:
    """A checksum-valid 9-digit number computed at run time (no literal in the repo)."""
    return first_valid(870_000_000, 9, tfn_ok)


def synthetic_abn() -> str:
    return first_valid(53_100_000_000, 11, abn_ok)


def synthetic_card() -> str:
    """A Luhn-valid 16-digit number in the 4111... test range, computed at run time."""
    return first_valid(4111_1111_1111_1100, 16, luhn_ok)


def spaced(digits: str, groups) -> str:
    out, i = [], 0
    for g in groups:
        out.append(digits[i:i + g])
        i += g
    return " ".join(out)
