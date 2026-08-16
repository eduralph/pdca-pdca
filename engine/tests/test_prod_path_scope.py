"""The C5 prod-path wrapper asks the #154 question only where it is a fair one.

`scripts/checks/test_exercises_production.py` (template-shipped, with its own suite at
tests/test_prod_path_gate.py) flags any newly added test file that imports nothing from the
production package. The target has two test roots and that is only meaningful in one:

  * `template/tests/…` exercises `pdca_harness` — 72 of 78 modules import it. In scope.
  * `tests/…` RENDERS the template and drives it as a subprocess, so NOT importing is
    correct — 1 of 3 does. Asking there files a §6 item against correct code.

These cases pin the scoping, and that the wrapper delegates the actual import test to the
shipped checker rather than reimplementing it (the synthetic-diff round trip).

Run: python3 -m unittest discover -s engine/tests
"""

from __future__ import annotations

import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

INSTANCE = Path(__file__).resolve().parents[2]
SCRIPT = INSTANCE / "engine" / "scripts" / "run-prod-path.py"

EVIDENCE = "PDCA-EVIDENCE:"
UNVERIFIABLE = "PDCA-UNVERIFIABLE:"


def _added_file(path: str, body: str) -> str:
    """A unified-diff block for one newly added file."""
    lines = [f"diff --git a/{path} b/{path}", "new file mode 100644",
             "--- /dev/null", f"+++ b/{path}"]
    lines += [f"+{ln}" for ln in body.splitlines()]
    return "\n".join(lines) + "\n"


IMPORTS_PROD = "from pdca_harness import gates\n\n\ndef test_x():\n    assert gates\n"
NO_IMPORT = "def helper():\n    return 1\n\n\ndef test_x():\n    assert helper() == 1\n"


class ProdPathScope(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-c5-scope-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_gate(self, diff: str) -> subprocess.CompletedProcess[str]:
        (self.tmp / "patch.diff").write_text(diff, encoding="utf-8")
        env = dict(os.environ)
        env["PDCA_BUNDLE"] = str(self.tmp)
        env["PDCA_PROD_PACKAGE"] = "pdca_harness"
        return subprocess.run(["python3", str(SCRIPT)], env=env,
                              capture_output=True, text=True)

    def test_a_driver_suite_test_that_imports_production_passes(self) -> None:
        r = self.run_gate(_added_file("template/tests/test_new.py", IMPORTS_PROD))
        self.assertEqual(r.returncode, 0)
        self.assertIn(EVIDENCE, r.stdout)
        self.assertNotIn(UNVERIFIABLE, r.stdout)

    def test_a_driver_suite_test_that_imports_nothing_is_flagged(self) -> None:
        """The whole point of #154: green against a hand-ported copy proves nothing."""
        r = self.run_gate(_added_file("template/tests/test_copy.py", NO_IMPORT))
        self.assertIn(UNVERIFIABLE, r.stdout)
        self.assertIn("template/tests/test_copy.py", r.stdout)

    def test_a_root_suite_test_is_out_of_scope_not_flagged(self) -> None:
        """The false positive the scoping exists to prevent — these MUST not import."""
        r = self.run_gate(_added_file("tests/test_render_thing.py",
                                      "import subprocess\n\n\ndef test_r():\n    pass\n"))
        self.assertNotIn(UNVERIFIABLE, r.stdout)
        self.assertIn("out of scope", r.stdout)

    def test_a_mixed_patch_judges_only_the_driver_suite_file(self) -> None:
        r = self.run_gate(_added_file("tests/test_render_thing.py", "import subprocess\n")
                          + _added_file("template/tests/test_new.py", IMPORTS_PROD))
        self.assertNotIn(UNVERIFIABLE, r.stdout)
        self.assertIn("out of scope", r.stdout)
        self.assertIn("import the production package", r.stdout)

    def test_a_patch_with_no_new_test_asserts_nothing(self) -> None:
        r = self.run_gate("diff --git a/template/src/pdca_harness/gates.py "
                          "b/template/src/pdca_harness/gates.py\n"
                          "--- a/template/src/pdca_harness/gates.py\n"
                          "+++ b/template/src/pdca_harness/gates.py\n+# tweak\n")
        self.assertIn(EVIDENCE, r.stdout)
        self.assertNotIn(UNVERIFIABLE, r.stdout)

    def test_an_edited_test_is_not_judged_only_an_added_one(self) -> None:
        """The reference's own rule: an EDIT may already import production as unchanged
        context, so requiring the import among added lines would false-positive."""
        r = self.run_gate("diff --git a/template/tests/test_old.py b/template/tests/test_old.py\n"
                          "--- a/template/tests/test_old.py\n"
                          "+++ b/template/tests/test_old.py\n"
                          "+    self.assertTrue(True)\n")
        self.assertNotIn(UNVERIFIABLE, r.stdout)

    def test_it_never_blocks(self) -> None:
        """Advisory by the reference's construction — every path exits 0."""
        for diff in (_added_file("template/tests/test_copy.py", NO_IMPORT),
                     _added_file("template/tests/test_new.py", IMPORTS_PROD),
                     ""):
            self.assertEqual(self.run_gate(diff).returncode, 0, diff[:60])

    def test_a_close_disposition_has_nothing_to_assert(self) -> None:
        r = self.run_gate("")
        self.assertEqual(r.returncode, 0)
        self.assertIn(EVIDENCE, r.stdout)

    def test_the_import_test_is_delegated_to_the_shipped_checker(self) -> None:
        """The wrapper must not reimplement the reference's regex — it round-trips the
        in-scope blocks back through it. Guarded by behaviour the reference owns: a
        submodule import (`from pdca_harness.gates import x`) counts as production."""
        r = self.run_gate(_added_file(
            "template/tests/test_sub.py",
            "from pdca_harness.gates import EVIDENCE_MARKER\n\n\ndef test_x():\n    pass\n"))
        self.assertNotIn(UNVERIFIABLE, r.stdout)


if __name__ == "__main__":
    unittest.main()
