"""The two docs-checker gates declare a verdict on the FAILING path, not just the green one.

`gates._declared_evidence` takes the last `PDCA-EVIDENCE:` line as the row's evidence and,
finding none, falls back to the command's final output line (`gates.py:771`) — "only ever
the gate's verdict by luck". Both scripts used to run under `set -e`, so a red checker
aborted the script BEFORE its declaration: green runs declared, red runs did not. That
left the fallback in force on exactly the row a human opens to find out what broke, and
for `run-host-ci.sh` a red also blocks a push rather than filing a §6 item.

Codex review, 2026-08-13. Both scripts now run each checker with `|| rc=$?` and declare
either way.

The target's checkers are stubbed by planting real `docs/publishing/tools/*.py` files in a
throwaway worktree — not by stubbing the interpreter, which would not work for
`run-host-ci.sh` (it resolves the instance venv from its own location by design, so an
interpreter planted in cwd or on PATH is never consulted). Neither the target checkout nor
the network is touched.

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
DOCS_CHECK = INSTANCE / "engine" / "scripts" / "run-docs-check.sh"
HOST_CI = INSTANCE / "engine" / "scripts" / "run-host-ci.sh"

# Stands in for one of the target's checkers. Prints a decoy final line — the shape that
# got a GREEN run filed as `/tmp/…/split-proposal.md` — then exits as the case asks.
CHECKER = """\
import sys
print("checker {name} ran")
print("/tmp/scratch-that-no-longer-exists/site/index.html")
sys.exit({rc})
"""


class _GateContract:
    """The contract both scripts owe. Concrete subclasses supply `_run`."""

    script: Path

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-docs-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "instance"     # cwd for run-docs-check.sh
        self.wt = self.tmp / "wt"             # $PDCA_WORKTREE / the patched tree
        self.tools = self.wt / "docs" / "publishing" / "tools"
        self.root.mkdir(parents=True)
        self.tools.mkdir(parents=True)
        self._checkers(lint_rc=0, render_rc=0)

    def _checkers(self, *, lint_rc: int, render_rc: int) -> None:
        for name, rc in (("lint_docs", lint_rc), ("render_site", render_rc)):
            (self.tools / f"{name}.py").write_text(
                CHECKER.format(name=name, rc=rc), encoding="utf-8")

    def _exec(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PDCA_WORKTREE"] = str(self.wt)
        env["PDCA_BUNDLE"] = str(self.tmp / "bundle")
        return subprocess.run(["bash", str(self.script)], cwd=cwd, env=env,
                              capture_output=True, text=True)

    def run_gate(self, *, lint_rc: int = 0, render_rc: int = 0):
        raise NotImplementedError

    @staticmethod
    def evidence(r: subprocess.CompletedProcess[str]) -> str | None:
        """Resolved the way `gates._declared_evidence` resolves it: the LAST non-empty
        `PDCA-EVIDENCE:` line over the combined stream."""
        declared = [ln for ln in (r.stdout + r.stderr).splitlines()
                    if ln.startswith("PDCA-EVIDENCE:") and ln[len("PDCA-EVIDENCE:"):].strip()]
        return declared[-1] if declared else None

    # --- the contract ------------------------------------------------------------

    def test_green_declares_both_legs_clean(self) -> None:
        r = self.run_gate()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ev = self.evidence(r)
        self.assertIn("docs lint clean", ev or "")
        self.assertIn("site render + link audit clean", ev or "")

    def test_a_red_checker_still_declares_and_names_which_leg(self) -> None:
        r = self.run_gate(lint_rc=1)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        ev = self.evidence(r)
        self.assertIsNotNone(ev, "a FAILING run declared no evidence — the "
                                 "last-output-line fallback is back in force")
        self.assertIn("docs lint FAILED", ev)
        self.assertIn("site render + link audit clean", ev)

    def test_the_decoy_last_line_never_becomes_the_evidence(self) -> None:
        r = self.run_gate(render_rc=1)
        # The decoy really is the checker's final output line.
        self.assertIn("scratch-that-no-longer-exists", r.stdout)
        self.assertNotIn("scratch-that-no-longer-exists", self.evidence(r) or "")

    def test_both_legs_run_even_when_the_first_is_red(self) -> None:
        # `set -e` aborted at the first red, so the second checker never ran and the
        # verdict could not describe it.
        r = self.run_gate(lint_rc=1, render_rc=1)
        ev = self.evidence(r)
        self.assertIn("docs lint FAILED", ev)
        self.assertIn("site render + link audit FAILED", ev)
        self.assertIn("checker render_site ran", r.stdout)

    def test_the_exit_status_still_reports_the_failure(self) -> None:
        # Declaring on the red path must not turn a red into a pass: the marker carries
        # evidence only — `gates._classify` decides pass/fail from the exit code alone.
        self.assertNotEqual(self.run_gate(lint_rc=1).returncode, 0)
        self.assertNotEqual(self.run_gate(render_rc=1).returncode, 0)
        self.assertEqual(self.run_gate().returncode, 0)


class DocsCheckGate(_GateContract, unittest.TestCase):
    """T2, advisory, run from the instance root against $PDCA_WORKTREE."""

    script = DOCS_CHECK

    def run_gate(self, *, lint_rc: int = 0, render_rc: int = 0):
        self._checkers(lint_rc=lint_rc, render_rc=render_rc)
        return self._exec(cwd=self.root)


class HostCiGate(_GateContract, unittest.TestCase):
    """host_ci, gating, run FROM the patched tree — so its cwd is the worktree itself."""

    script = HOST_CI

    def run_gate(self, *, lint_rc: int = 0, render_rc: int = 0):
        self._checkers(lint_rc=lint_rc, render_rc=render_rc)
        return self._exec(cwd=self.wt)

    def test_it_audits_the_tree_it_was_handed(self) -> None:
        """The #296 doctrine. The checkers exist ONLY under the patched tree, so running
        them at all proves the script did not cd away from it."""
        r = self.run_gate()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("checker lint_docs ran", r.stdout)
        self.assertIn("checker render_site ran", r.stdout)

    def test_a_missing_checker_is_unverifiable_not_a_pass(self) -> None:
        """A tree without the checkers is no evidence either way — and at publish, exit 77
        blocks the push rather than shipping content the declared CI never saw."""
        self._checkers(lint_rc=0, render_rc=0)
        (self.tools / "render_site.py").unlink()
        r = self._exec(cwd=self.wt)
        self.assertEqual(r.returncode, 77, r.stdout + r.stderr)
        self.assertIn("PDCA-UNVERIFIABLE", r.stdout)


if __name__ == "__main__":
    unittest.main()
