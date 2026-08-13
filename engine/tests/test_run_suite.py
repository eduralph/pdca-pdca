"""Engine tests: run-suite.sh declares its T3 verdict as evidence (issue #402).

A gate's frozen evidence used to be its LAST output line, which this suite could not
control: the target's tests print scratch bundle paths to stdout and, under a pipe,
that block-buffered stream flushes after unittest's own (stderr) report — so a GREEN
run was filed as `/tmp/…/split-proposal.md`. The v0.57.0 driver scans for a declared
`PDCA-EVIDENCE:` line instead (gates.py:91), and persists every gate's full combined
output to `gate-logs/<rule_id>.log` itself (issue #370, gates.py:192).

So the two 2026-08-02/08-06 stopgaps this file used to pin — the script's own tee into
the bundle, and the "verdict must be the last line" ordering — are gone. What is left to
pin is the contract that replaced them: the declaration carries the verdict for BOTH
suites, and the failing test names still reach the script's own output stream, which is
what the driver captures.

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
# the part worth keeping, on stderr) and exits with a caller-chosen status. The stdout line
# is the decoy — the scratch path that used to be filed as a green run's evidence.
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

    @staticmethod
    def _evidence(r: subprocess.CompletedProcess[str]) -> str:
        """The declared evidence line, resolved the way the driver resolves it: the LAST
        line starting with the marker, over the combined stream."""
        declared = [ln for ln in (r.stdout + r.stderr).splitlines()
                    if ln.startswith("PDCA-EVIDENCE:")]
        assert declared, f"no PDCA-EVIDENCE line:\n{r.stdout}\n{r.stderr}"
        return declared[-1]

    def test_red_suite_leaves_the_failing_test_name_on_the_gate_output(self) -> None:
        # The driver persists this stream verbatim to gate-logs/T3-suite.log, so a red
        # T3 stays diagnosable without the script teeing anything itself.
        self._stub_python(1)
        r = self._run()
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        combined = r.stdout + r.stderr
        self.assertIn("FAIL: test_the_one_that_broke", combined)
        self.assertIn("template-repo suite", combined)
        self.assertIn("offline driver suite", combined)

    def test_the_declaration_carries_the_verdict_not_the_decoy_path(self) -> None:
        self._stub_python(1)
        r = self._run()
        evidence = self._evidence(r)
        self.assertIn("root suite FAILED", evidence)
        self.assertIn("driver suite FAILED", evidence)
        self.assertNotIn("split-proposal.md", evidence)

    def test_green_suite_declares_green_and_exits_zero(self) -> None:
        self._stub_python(0)
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual("PDCA-EVIDENCE: root suite OK, driver suite OK",
                         self._evidence(r))

    def test_the_script_writes_nothing_into_the_bundle(self) -> None:
        # Gate-log retention is the driver's job now (issue #370). The script must not
        # write a competing file next to the bundle.
        self._stub_python(1)
        self._run()
        self.assertEqual([], list(self.bundle.iterdir()))

    def test_runs_without_a_bundle(self) -> None:
        # By hand, outside the driver: no $PDCA_BUNDLE and no failure over its absence.
        self._stub_python(0)
        r = self._run(bundle=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FAIL: test_the_one_that_broke", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
