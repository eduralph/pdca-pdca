"""Regression test for the shared copier-availability probe (issue #495).

Drives `tests._copier_probe` directly with the import and the `PATH` lookup
both controlled, so the two postures at stake — copier importable, and
copier NOT importable in this interpreter while a pipx-style executable
sits on `PATH` — are deterministic regardless of what this host actually has
installed (brief criterion iv: "obtainable without re-running the suite").
It does not re-run `test_render_and_run.py` / `test_update_compat.py` /
`test_render_cli_name.py`; what those 7 tests assert is out of this slice's
scope, only the probe they share and what a wholesale skip reports.
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    from tests._copier_probe import (
        CopierProbe,
        classify,
        in_gate_context,
        probe_copier,
        unverifiable_message,
    )
except ImportError:  # pragma: no cover - `unittest discover -s tests` puts tests/ on sys.path
    from _copier_probe import (
        CopierProbe,
        classify,
        in_gate_context,
        probe_copier,
        unverifiable_message,
    )

ROOT = Path(__file__).resolve().parent


class ProbeCopierReason(unittest.TestCase):
    """(i): the reason states the proposition actually tested."""

    def test_importable_reports_available(self) -> None:
        probe = probe_copier(import_copier=lambda: None, which=lambda name: None)
        self.assertTrue(probe.available)
        self.assertIn("importable", probe.reason)

    def test_unimportable_with_path_executable_names_it_and_never_claims_uninstalled(
        self,
    ) -> None:
        """The pipx posture reproduced on this host: import fails, `copier` is on PATH."""

        def boom() -> None:
            raise ModuleNotFoundError("No module named 'copier'")

        probe = probe_copier(
            import_copier=boom,
            which=lambda name: "/home/x/.local/bin/copier" if name == "copier" else None,
            executable="/usr/bin/python3",
        )
        self.assertFalse(probe.available)
        self.assertIn("/usr/bin/python3", probe.reason)
        self.assertIn("/home/x/.local/bin/copier", probe.reason)
        self.assertIn("not importable in this interpreter", probe.reason)
        # The defect this regresses: telling the reader to install a tool that
        # is already there. "not installed" must never appear once an
        # executable was actually found on PATH.
        self.assertNotIn("not installed", probe.reason)

    def test_unimportable_with_no_path_executable_reports_truly_absent(self) -> None:
        def boom() -> None:
            raise ModuleNotFoundError("No module named 'copier'")

        probe = probe_copier(import_copier=boom, which=lambda name: None)
        self.assertFalse(probe.available)
        self.assertIn("no copier executable was found on PATH", probe.reason)


class GateContext(unittest.TestCase):
    """`$PDCA_BUNDLE` — the driver's own gate-vs-dev-run signal — decides posture."""

    def test_pdca_bundle_set_is_a_gate_run(self) -> None:
        self.assertTrue(in_gate_context({"PDCA_BUNDLE": "/tmp/bundle"}))

    def test_pdca_bundle_unset_is_a_bare_run(self) -> None:
        self.assertFalse(in_gate_context({}))

    def test_pdca_bundle_empty_string_is_still_a_bare_run(self) -> None:
        self.assertFalse(in_gate_context({"PDCA_BUNDLE": ""}))


class Classify(unittest.TestCase):
    """(ii)+(iii): a wholesale skip is a pass only outside a gate."""

    def test_available_always_runs(self) -> None:
        probe = CopierProbe(True, "copier is importable in this interpreter")
        self.assertEqual(classify(probe, gate=False), "run")
        self.assertEqual(classify(probe, gate=True), "run")

    def test_unavailable_bare_run_skips(self) -> None:
        probe = CopierProbe(False, "copier is not importable here")
        self.assertEqual(classify(probe, gate=False), "skip")

    def test_unavailable_gate_run_fails_not_skips(self) -> None:
        probe = CopierProbe(False, "copier is not importable here")
        self.assertEqual(classify(probe, gate=True), "fail")

    def test_unverifiable_message_carries_the_harness_gate_vocabulary(self) -> None:
        probe = CopierProbe(False, "copier is not importable in this interpreter")
        msg = unverifiable_message(probe)
        self.assertTrue(msg.startswith("PDCA-UNVERIFIABLE:"))
        self.assertIn(probe.reason, msg)


class AllThreeModulesShareTheProbe(unittest.TestCase):
    """Self-test: the invariant is about the run as a whole, not one module.

    A partial fix — correcting the reason in one module while the other two
    still carry the byte-identical `HAVE_COPIER = True/False` probe and the
    old `"copier not installed"` skip reason — would leave two thirds of the
    suite still silently green under a gate. This reads the module source
    (no import of copier, no interpreter dependency), so it binds on every
    host regardless of whether copier happens to be importable here.
    """

    MODULES = ("test_render_and_run.py", "test_update_compat.py", "test_render_cli_name.py")

    def test_none_carry_the_old_bare_have_copier_probe(self) -> None:
        for name in self.MODULES:
            text = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(module=name):
                self.assertNotIn(
                    'skipUnless(HAVE_COPIER, "copier not installed")',
                    text,
                    f"{name} still reports the old false reason",
                )
                self.assertIn(
                    "_copier_probe", text, f"{name} does not use the shared probe"
                )


if __name__ == "__main__":
    unittest.main()
