"""Engine tests: run-verify.sh honours the C4 contract (engine/README.md).

Each case builds a throwaway local clone of the sibling target checkout
(../pdca-harness), synthesizes a bundle whose patch.diff is applied to the
clone's working tree — exactly the state the driver hands a gate — and runs the
script as the driver would: cwd = the instance root, $PDCA_BUNDLE and
$PDCA_WORKTREE exported. Skips cleanly when the sibling checkout is missing
(the doctor's required `target` row reports that with the clone hint).

Run: python3 -m unittest discover -s engine/tests
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INSTANCE = Path(__file__).resolve().parents[2]
TARGET = INSTANCE.parent / "pdca-harness"
SCRIPT = INSTANCE / "engine" / "scripts" / "run-verify.sh"

SMOKE_PROD = "template/src/pdca_harness/_c4_smoke.py"
SMOKE_TEST = "template/tests/test_c4_smoke.py"

# The genuine red: the patch MODIFIES an existing production module, so the test imports
# cleanly on both legs and the red leg is a real failing assertion. A fixture that adds a
# NEW module instead (NEW_MODULE_PROD/_TEST below) cannot import once the fix is reverted,
# which is the false red the loader guard exists to catch — not a red→green proof.
INIT_PROD = "template/src/pdca_harness/__init__.py"
INIT_MARKER = "_C4_SMOKE = 1\n"

CAPTURING_TEST = """\
import unittest

import pdca_harness


class Smoke(unittest.TestCase):
    def test_smoke(self) -> None:
        self.assertEqual(pdca_harness._C4_SMOKE, 1)
"""

# Imports a symbol the patch ADDS: reverting production removes it, so the module fails to
# load and unittest reports `unittest.loader._FailedTest` — non-zero, but nothing ran.
NEW_MODULE_TEST = """\
import unittest

from pdca_harness import _c4_smoke


class Smoke(unittest.TestCase):
    def test_smoke(self) -> None:
        self.assertEqual(_c4_smoke.X, 1)
"""

VACUOUS_TEST = """\
import unittest


class Smoke(unittest.TestCase):
    def test_smoke(self) -> None:
        self.assertTrue(True)
"""

# A test file carrying no TestCase at all: unittest exits 0 reporting "Ran 0 tests".
NO_CASES_TEST = """\
import unittest  # noqa: F401  -- deliberately declares no TestCase
"""


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _bash_path(p: Path) -> str:
    """A path git-bash can test with -s/cd: /c/... on Windows, as-is elsewhere."""
    if os.name != "nt":
        return str(p)
    drive, rest = str(p).split("\\", 1)
    return f"/{drive[0].lower()}/{rest.replace(chr(92), '/')}"


def _git_bash() -> str:
    """The bash this suite must drive the gates with.

    On Windows ``shutil.which("bash")`` finds the WSL shim in system32 (which
    is inserted ahead of PATH and cannot see C:\\ paths); the gates need
    Git-bash. Upstream CI is Linux, where this is just ``bash``.
    """
    found = shutil.which("bash") or "bash"
    if os.name != "nt":
        return found
    candidates = [found, r"C:\Program Files\Git\bin\bash.exe"]
    for cand in candidates:
        if os.path.basename(cand).lower() == "bash.exe" and "Git" in cand:
            return cand
    root = os.environ.get("ProgramFiles", r"C:\Program Files")
    return os.path.join(root, "Git", "bin", "bash.exe")


@unittest.skipUnless((TARGET / ".git").exists(), "sibling ../pdca-harness missing")
class RunVerify(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-c4-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.wt = self.tmp / "wt"
        subprocess.run(
            ["git", "clone", "-q", str(TARGET), str(self.wt)],
            check=True, capture_output=True,
        )

    def _bundle(self, files: dict[str, str]) -> Path:
        """Write files into the clone, capture them as patch.diff, leave them
        applied to the working tree (the driver's base + patch state)."""
        for rel, content in files.items():
            p = self.wt / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        _git(self.wt, "add", "-A")
        patch = _git(self.wt, "diff", "--cached").stdout
        _git(self.wt, "reset", "-q")
        bundle = self.tmp / "bundle"
        bundle.mkdir(exist_ok=True)
        (bundle / "patch.diff").write_text(patch, encoding="utf-8")
        return bundle

    def _verify(self, bundle: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PDCA_BUNDLE"] = str(bundle)
        env["PDCA_WORKTREE"] = str(self.wt)
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=INSTANCE, env=env,
            capture_output=True, text=True,
        )

    def _patched_init(self) -> str:
        """The target's package init with the smoke marker appended — a MODIFIED
        existing production file, so both legs can import it."""
        return (self.wt / INIT_PROD).read_text(encoding="utf-8") + INIT_MARKER

    def test_red_green_passes(self) -> None:
        r = self._verify(self._bundle({
            INIT_PROD: self._patched_init(),
            SMOKE_TEST: CAPTURING_TEST,
        }))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # DECLARED (issue #402): the verdict is what the driver files as the row's
        # evidence, not whichever line the sub-runs happened to flush last.
        self.assertIn("PDCA-EVIDENCE: C4 PASS", r.stdout)
        # restore left base + full patch in place for later gates
        self.assertIn(INIT_MARKER, (self.wt / INIT_PROD).read_text(encoding="utf-8"))

    def test_vacuous_test_fails(self) -> None:
        r = self._verify(self._bundle({
            INIT_PROD: self._patched_init(),
            SMOKE_TEST: VACUOUS_TEST,
        }))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("still green WITHOUT the fix", r.stdout)

    def test_red_leg_import_failure_is_unverifiable(self) -> None:
        """The #439 class: the patch adds a module the test imports, so the red leg
        cannot load it. Non-zero exit, but NOTHING RAN — it must not read as a red."""
        r = self._verify(self._bundle({
            SMOKE_PROD: "X = 1\n",
            SMOKE_TEST: NEW_MODULE_TEST,
        }))
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("failed to IMPORT", r.stdout)
        self.assertNotIn("C4 PASS", r.stdout)

    def test_zero_tests_ran_is_unverifiable(self) -> None:
        """A test file declaring no case exits 0 having asserted nothing — the absence
        of a measurement, not a green."""
        r = self._verify(self._bundle({
            INIT_PROD: self._patched_init(),
            SMOKE_TEST: NO_CASES_TEST,
        }))
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("0 tests ran with the fix applied", r.stdout)

    def test_no_test_is_unverifiable(self) -> None:
        readme = (self.wt / "README.md").read_text(encoding="utf-8")
        r = self._verify(self._bundle({"README.md": readme + "\nx\n"}))
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("PDCA-UNVERIFIABLE", r.stdout)

    def test_test_only_is_unverifiable(self) -> None:
        r = self._verify(self._bundle({SMOKE_TEST: VACUOUS_TEST}))
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("no behavioral production change", r.stdout)

    def test_each_leg_uses_an_isolated_python_bytecode_cache(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('CACHE_ROOT="$(mktemp -d', script)
        self.assertIn('RUN_CACHE="$(mktemp -d "$CACHE_ROOT/leg.', script)
        self.assertIn('PYTHONPYCACHEPREFIX="$RUN_CACHE" PYTHONPATH=src', script)
        self.assertIn('PYTHONPYCACHEPREFIX="$RUN_CACHE" "$PY" -m unittest "$mod"', script)


# Issue #100's hazard does not need the sibling target: a reverted source that
# keeps the patched file's SIZE and whole-second MTIME makes Python reuse the
# green leg's .pyc, and the red leg executes the FIXED bytecode — a false
# "C4 FAIL — still green without the fix". This class drives the real script
# against a synthetic target whose patch is a same-length one-char flip
# (`X = 1 - 1` -> `X = 1 + 1`), aligns the revert into the second the green
# bytecode was compiled in, and pins that the gate still reports a genuine red.
class StaleBytecode(unittest.TestCase):
    # The stale load only fires when the red leg's revert lands in the whole
    # second the green .pyc's header recorded. Each attempt parks the patched
    # source a different step ahead of "now" so the sweep crosses that second;
    # with a shared cache one attempt goes falsely green, with per-leg caches
    # every attempt reports a genuine red.
    ATTEMPTS = 10

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-c4-pyc-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.wt = self.tmp / "wt"
        (self.wt / "tests").mkdir(parents=True)
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.invalid")
        self._git("config", "user.name", "t")
        # Byte sizes drive the .pyc validity check; CRLF rewriting would break
        # the same-size premise on a Windows contributor host.
        self._git("config", "core.autocrlf", "false")
        (self.wt / "m.py").write_text("X = 1 - 1\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")
        (self.wt / "tests" / "test_m.py").write_text(
            "import unittest\n\nimport m\n\n\nclass T(unittest.TestCase):\n"
            "    def test_sum(self) -> None:\n"
            "        self.assertEqual(m.X, 2)\n",
            encoding="utf-8",
        )
        (self.wt / "m.py").write_text("X = 1 + 1\n", encoding="utf-8")
        bundle = self.tmp / "bundle"
        bundle.mkdir()
        self._git("add", "-A")
        patch = self._git("diff", "--cached").stdout
        (bundle / "patch.diff").write_text(patch, encoding="utf-8")
        self._git("reset", "-q")   # driver state: base + patch applied to the tree

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.wt, check=True, capture_output=True, text=True
        )

    def _run_gate(self) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PDCA_BUNDLE"] = _bash_path(self.tmp / "bundle")
        env["PDCA_WORKTREE"] = _bash_path(self.wt)
        return subprocess.run(
            [_git_bash(), _bash_path(SCRIPT)], cwd=INSTANCE, env=env,
            capture_output=True, text=True,
        )

    def test_the_red_leg_never_runs_the_green_legs_cached_bytecode(self) -> None:
        stale = "still green WITHOUT the fix"
        for attempt in range(self.ATTEMPTS):
            shutil.rmtree(self.wt / "__pycache__", ignore_errors=True)
            shutil.rmtree(self.wt / "tests" / "__pycache__", ignore_errors=True)
            # Park the patched source step*0.23s ahead of now, then compile the
            # green bytecode: its header records (size=10, that second). The
            # gate's green leg reuses it; the red leg's `git apply -R` restores
            # the same-size base file with mtime=now, and whenever that lands
            # in the parked second a shared cache hands the red leg the FIXED
            # bytecode — the false C4 FAIL of issue #100.
            subprocess.run(
                [sys.executable, "-c",
                 "import os, sys, time\n"
                 "now = time.time() + float(sys.argv[2])\n"
                 "os.utime(sys.argv[1], (now, now))\n",
                 str(self.wt / "m.py"), str(attempt * 0.23)],
                check=True,
            )
            subprocess.run(
                [sys.executable, "-c", "import m"], cwd=self.wt, check=True,
                capture_output=True,
            )
            r = self._run_gate()
            combined = r.stdout + r.stderr
            self.assertNotIn(
                stale, combined,
                f"attempt {attempt}: the red leg executed the green leg's cached "
                f"bytecode — the false C4 FAIL of issue #100:\n{combined}",
            )
            self.assertIn("C4 PASS", combined, combined)


if __name__ == "__main__":
    unittest.main()
