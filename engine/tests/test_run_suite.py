"""Engine tests: run-suite.sh keeps the T3 evidence a red leaves behind (issue #31 item 2).

The frozen record keeps only a gate's LAST output line, so a red T3 used to freeze as
`driver suite FAILED (rc 1)` and nothing else — no failing test name, no traceback. These
cases pin the interim log the script writes alongside the bundle, and the last-line rule
the 2026-08-02 verdict stopgap depends on.

Both suites are stubbed: the script resolves its interpreter as `$(pwd)/.venv/bin/python3`
before it cds into the worktree, so a throwaway instance root with a stub there drives the
script without running the target's real (minutes-long) suites.

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
SCRIPT = INSTANCE / "engine" / "scripts" / "run-suite.sh"

# Stands in for `python3 -m unittest …`: writes to BOTH streams (unittest puts its report,
# the part worth keeping, on stderr) and exits with a caller-chosen status.
STUB = """\
#!/bin/sh
echo "stdout: {tmp}/results/issue_500/split-proposal.md"
echo "FAIL: test_the_one_that_broke" >&2
echo "Ran 3 tests in 0.01s" >&2
exit {rc}
"""


class RunSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-t3-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "instance"          # cwd: stands in for the instance root
        self.wt = self.tmp / "wt"                  # $PDCA_WORKTREE: the target checkout
        self.bundle = self.tmp / "bundle"
        for p in (self.root / ".venv" / "bin", self.wt / "tests",
                  self.wt / "template" / "tests", self.bundle):
            p.mkdir(parents=True)

    def _stub_python(self, rc: int) -> None:
        py = self.root / ".venv" / "bin" / "python3"
        py.write_text(STUB.format(tmp=self.tmp, rc=rc), encoding="utf-8")
        py.chmod(0o755)

    def _run(self, *, bundle: bool = True) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PDCA_WORKTREE"] = str(self.wt)
        if bundle:
            env["PDCA_BUNDLE"] = str(self.bundle)
        else:
            env.pop("PDCA_BUNDLE", None)
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=self.root, env=env,
            capture_output=True, text=True,
        )

    @property
    def _log(self) -> Path:
        return self.bundle / "gate-logs" / "T3-suite.log"

    def test_red_suite_leaves_the_failing_test_name_behind(self) -> None:
        self._stub_python(1)
        r = self._run()
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self._log.exists(), r.stdout + r.stderr)
        log = self._log.read_text(encoding="utf-8")
        # The whole point: stderr's report survives the freeze, per suite.
        self.assertIn("FAIL: test_the_one_that_broke", log)
        self.assertIn("template-repo suite", log)
        self.assertIn("offline driver suite", log)

    def test_verdict_is_still_the_last_line(self) -> None:
        # The 2026-08-02 stopgap: the frozen evidence is the last line, and it must be the
        # verdict — not a scratch path the target's tests printed to stdout.
        self._stub_python(1)
        r = self._run()
        last = r.stdout.strip().splitlines()[-1]
        self.assertIn("== T3: root suite FAILED", last)
        self.assertIn("driver suite FAILED", last)
        self.assertNotIn("split-proposal.md", last)

    def test_green_suite_logs_and_exits_zero(self) -> None:
        self._stub_python(0)
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Ran 3 tests", self._log.read_text(encoding="utf-8"))
        self.assertIn("== T3: root suite OK, driver suite OK",
                      r.stdout.strip().splitlines()[-1])

    def test_runs_without_a_bundle(self) -> None:
        # By hand, outside the driver: no $PDCA_BUNDLE, no log, and no failure over it.
        self._stub_python(0)
        r = self._run(bundle=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self._log.exists())
        self.assertIn("FAIL: test_the_one_that_broke", r.stdout)  # still on the gate's output


if __name__ == "__main__":
    unittest.main()
