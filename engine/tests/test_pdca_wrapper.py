"""Engine tests: scripts/pdca resolves this project's CLI in every install layout (#31 item 3).

A gate row is a shell command run from the project root, so the row that invokes the
harness must name something that exists whichever way the harness was installed. Bare
`pdca-pdca` isn't that — the console script lives in the project venv and running it does
not put its own directory on PATH — and the T4 row kept coming back to reviewers as 127,
read as an absent gate (upstream eduralph/pdca-harness#441).

Each case builds a throwaway project root containing only the layout under test, drops the
real script into `<root>/scripts/pdca`, and runs it with a hermetic PATH. The stubs print a
marker so the resolved branch is identifiable from stdout.

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
SCRIPT = INSTANCE / "scripts" / "pdca"


class PdcaWrapper(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-cli-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "proj"
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(SCRIPT, self.root / "scripts" / "pdca")
        self.stub_bin = self.tmp / "stub-bin"          # the hermetic PATH
        self.stub_bin.mkdir()

    def _stub(self, path: Path, marker: str) -> Path:
        """An executable that identifies itself and echoes the args it was handed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'#!/bin/sh\necho "{marker} $*"\n', encoding="utf-8")
        path.chmod(0o755)
        return path

    def _venv(self, marker: str = "VENV") -> Path:
        return self._stub(self.root / ".venv" / "bin" / "pdca-pdca", marker)

    def _src(self) -> None:
        """A source checkout: the file the wrapper probes, plus an importable package."""
        pkg = self.root / "src" / "pdca_harness"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "cli.py").write_text("", encoding="utf-8")

    def _run(self, *args: str, **env_over: str) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": f"{self.stub_bin}:/usr/bin:/bin",
            "HOME": str(self.tmp),
        }
        env.update(env_over)
        return subprocess.run(
            ["bash", str(self.root / "scripts" / "pdca"), *args],
            capture_output=True, text=True, env=env, cwd=self.root,
        )

    # --- layout resolution ---------------------------------------------------------

    def test_venv_layout(self) -> None:
        self._venv()
        r = self._run("contribcheck", "42")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "VENV contribcheck 42")

    def test_windows_venv_layout(self) -> None:
        self._stub(self.root / ".venv" / "Scripts" / "pdca-pdca.exe", "WINVENV")
        r = self._run("status")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "WINVENV status")

    def test_source_tree_when_no_venv(self) -> None:
        self._src()
        py = self._stub(self.stub_bin / "fakepy", "SRC")
        r = self._run("status", PDCA_PYTHON=str(py))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "SRC -m pdca_harness.cli status")

    def test_source_tree_beats_a_cli_on_path(self) -> None:
        """The worktree hazard: a Do/Check worktree has no .venv, and a ~/.local/bin
        console script there belongs to the MAIN checkout's venv. This tree's own source
        must win, or the gate lints the bundle with a different tree's harness."""
        self._src()
        self._stub(self.stub_bin / "pdca-pdca", "PATH")
        py = self._stub(self.stub_bin / "fakepy", "SRC")
        r = self._run("status", PDCA_PYTHON=str(py))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SRC", r.stdout)
        self.assertNotIn("PATH", r.stdout)

    def test_venv_beats_source_tree(self) -> None:
        self._venv()
        self._src()
        r = self._run("status")
        self.assertEqual(r.stdout.strip(), "VENV status")

    def test_path_fallback_when_no_venv_and_no_src(self) -> None:
        self._stub(self.stub_bin / "pdca-pdca", "PATH")
        r = self._run("doctor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "PATH doctor")

    def test_nothing_found_exits_127_with_a_hint(self) -> None:
        r = self._run("status")
        self.assertEqual(r.returncode, 127, r.stdout + r.stderr)
        self.assertIn("no pdca-pdca CLI found", r.stderr)
        self.assertIn("make install", r.stderr)

    def test_never_falls_back_to_a_bare_pdca(self) -> None:
        """A bare `pdca` on this machine is a sibling project's install. Running the
        wrong harness is worse than not finding one."""
        self._stub(self.stub_bin / "pdca", "SIBLING")
        r = self._run("status")
        self.assertEqual(r.returncode, 127, r.stdout + r.stderr)
        self.assertNotIn("SIBLING", r.stdout)

    # --- the $PDCA_CLI override ----------------------------------------------------

    def test_override_wins_over_every_layout(self) -> None:
        self._venv()
        over = self._stub(self.tmp / "elsewhere" / "cli", "OVERRIDE")
        r = self._run("status", PDCA_CLI=str(over))
        self.assertEqual(r.stdout.strip(), "OVERRIDE status")

    def test_override_path_with_spaces_is_taken_whole(self) -> None:
        over = self._stub(self.tmp / "My Tools" / "pdca-pdca", "SPACED")
        r = self._run("status", PDCA_CLI=str(over))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "SPACED status")

    def test_override_may_be_a_command_line(self) -> None:
        py = self._stub(self.stub_bin / "fakepy", "CMDLINE")
        r = self._run("status", PDCA_CLI=f"{py} -m pdca_harness.cli")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "CMDLINE -m pdca_harness.cli status")

    def test_unparseable_override_fails_closed(self) -> None:
        self._venv()
        r = self._run("status", PDCA_CLI='"unbalanced')
        self.assertEqual(r.returncode, 127, r.stdout + r.stderr)
        self.assertIn("not a parseable command line", r.stderr)
        self.assertNotIn("VENV", r.stdout)   # never falls through to the next layout

    def test_empty_override_names_no_command(self) -> None:
        # A gating row must not run its own arguments as a command.
        self._venv()
        r = self._run("status", PDCA_CLI="   ")
        self.assertEqual(r.returncode, 127, r.stdout + r.stderr)
        self.assertIn("names no command", r.stderr)


class RealScriptIsWired(unittest.TestCase):
    """The instance's own layout, and the gate row that has to name the wrapper."""

    def test_wrapper_is_executable(self) -> None:
        self.assertTrue(os.access(SCRIPT, os.X_OK), f"{SCRIPT} must be executable")

    def test_resolves_in_this_checkout(self) -> None:
        r = subprocess.run(
            ["bash", str(SCRIPT), "contribcheck", "--help"],
            cwd=INSTANCE, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("contribcheck", r.stdout)

    def test_t4_gate_row_names_the_wrapper(self) -> None:
        toml = (INSTANCE / "pdca.toml").read_text(encoding="utf-8")
        self.assertIn('cmd = "./scripts/pdca contribcheck"', toml)


if __name__ == "__main__":
    unittest.main()
