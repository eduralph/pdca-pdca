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
import tempfile
import unittest
from pathlib import Path

INSTANCE = Path(__file__).resolve().parents[2]
TARGET = INSTANCE.parent / "pdca-harness"
SCRIPT = INSTANCE / "engine" / "scripts" / "run-verify.sh"

SMOKE_PROD = "template/src/pdca_harness/_c4_smoke.py"
SMOKE_TEST = "template/tests/test_c4_smoke.py"

CAPTURING_TEST = """\
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


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


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

    def test_red_green_passes(self) -> None:
        r = self._verify(self._bundle({
            SMOKE_PROD: "X = 1\n",
            SMOKE_TEST: CAPTURING_TEST,
        }))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("C4 PASS", r.stdout)
        # restore left base + full patch in place for later gates
        self.assertTrue((self.wt / SMOKE_PROD).exists())

    def test_vacuous_test_fails(self) -> None:
        r = self._verify(self._bundle({
            SMOKE_PROD: "X = 1\n",
            SMOKE_TEST: VACUOUS_TEST,
        }))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("still green WITHOUT the fix", r.stdout)

    def test_no_test_is_unverifiable(self) -> None:
        readme = (self.wt / "README.md").read_text(encoding="utf-8")
        r = self._verify(self._bundle({"README.md": readme + "\nx\n"}))
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("PDCA-UNVERIFIABLE", r.stdout)

    def test_test_only_is_unverifiable(self) -> None:
        r = self._verify(self._bundle({SMOKE_TEST: VACUOUS_TEST}))
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("no behavioral production change", r.stdout)


if __name__ == "__main__":
    unittest.main()
