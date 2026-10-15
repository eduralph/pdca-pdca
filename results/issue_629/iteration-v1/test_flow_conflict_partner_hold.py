"""Stack mode holds a `Conflicts with` partner of a bundle that pushed no branch (#629).

`waves.compute_waves` orders a `Conflicts with` pair (the name-lower id builds first), so the
second is built on a line meant to hold the first. When the first is accepted but its publish
pushes no branch this run, the fold leaves it out (`held_unpushed`, #593). Its partner must
then be held — named on its own stderr line — exactly as a `Depends on` dependent is, while
the rest of the run goes on.

Offline: bundles on disk, the build leaf replaced by a stub that accepts each bundle it is
given (a non-empty patch.diff, `accept` in §9), publishing stubbed, `gh` stubbed. The
publisher is NOT a stub (a stub publisher is a dry-run, which holds nothing). Driven through
``flow.flow_ids`` in stack mode, publishing on.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_conflict_partner_hold
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import flow, leaves, publish, signoff, state
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
TODAY = "2026-10-10"
TARGET = "org/repo @ main"


def _patch(name: str) -> str:
    """A non-empty patch adding a file of ``name``'s own, so no two bundles share a path."""
    return (f"diff --git a/{name}.txt b/{name}.txt\nnew file mode 100644\n--- /dev/null\n"
            f"+++ b/{name}.txt\n@@ -0,0 +1 @@\n+p\n")


def _cfg(root: Path) -> Config:
    return Config(
        root=root, bundle_root=root / "results", process_dir=root / "process",
        templates_dir=TEMPLATES, default_branch="main", tracker_system="github",
        tracker_url="", issue_id_example="#1",
        builder=LeafConfig(mode="stub"), reviewer=LeafConfig(mode="stub"),
        planner=LeafConfig(mode="stub", interactive=True),
        signoff=LeafConfig(mode="stub", interactive=True),
        publisher=LeafConfig(mode="command", interactive=True),
        act=LeafConfig(mode="stub", interactive=True), gates_checks=[],
        # Inside the temp dir, and never git checkouts: nothing outside it is looked at.
        repo_checkouts={"org/repo": str(root / "repo")})


class ConflictPartnerHold(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = _cfg(self.tmp)
        self.built: list[str] = []
        self.unpushed: set[str] = set()   # bundle dir names whose publish pushes nothing
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _brief(self, iid: str, extra: str = "", target: str | None = TARGET) -> Path:
        """A PLANNED bundle; ``target`` None: its brief has no ``Repo + branch target``."""
        d = self.cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        tgt = f"- **Repo + branch target:** {target}\n" if target is not None else ""
        (d / "brief.md").write_text(f"- **Slug:** s{iid}\n{tgt}{extra}", encoding="utf-8")
        return d

    def _fixture(self) -> None:
        self._brief("701")                                         # CA
        self._brief("702", "- **Conflicts with:** 701\n")           # CJ
        self._brief("704", target=None)
        self._brief("703", "- **Depends on:** 704\n", target=None)  # U
        self._brief("705", "- **Depends on:** 702\n", target=None)

    # -- stubs -----------------------------------------------------------------------------

    def _gh_stub(self, args, *a, **kw):
        if not (isinstance(args, list) and args[:1] == ["gh"]):
            return self._real_run(args, *a, **kw)
        return subprocess.CompletedProcess(
            args, 0, json.dumps({"state": "OPEN", "headRefOid": "0" * 40}), "")

    def _drive_wave(self, cfg, wave: list[Path], **_kw) -> int:
        """The build leaf ran on each bundle and the human accepted it."""
        for d in wave:
            self.built.append(d.name)
            (d / "patch.diff").write_text(_patch(d.name), encoding="utf-8")
            (d / "check-gates.json").write_text("{}", encoding="utf-8")
            shutil.copyfile(TEMPLATES / "SUMMARY.md.tpl", d / "SUMMARY.md")
            signoff.record(d / "SUMMARY.md", action="accept", by="T", date=TODAY)
        return 0

    def _publish(self, cfg, d: Path, *a, **k) -> bool:
        """Push ``d``'s branch (a ``publish.json`` naming it, True) — unless it is one of
        ``self.unpushed``: its publish failed before the push (False, nothing recorded)."""
        if d.name in self.unpushed:
            return False
        (d / "publish.json").write_text(json.dumps({
            "mode": "new-pr", "branch": f"fix/{d.name}", "base": "main", "repo": "org/repo",
            "pr_url": f"https://github.com/org/repo/pull/{d.name}", "by": "T",
            "date": TODAY}), encoding="utf-8")
        return True

    def _run(self, ids: list[str]) -> None:
        err, out = io.StringIO(), io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
            stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
            stack.enter_context(mock.patch.object(flow, "_publish_bundle", self._publish))
            # No git checkout here: a fold of the bundles that DID push merges nothing.
            stack.enter_context(mock.patch.object(flow, "_fold_lines",
                                                  lambda *a, **k: ({}, {}, [])))
            stack.enter_context(mock.patch.object(publish, "draft_texts",
                                                  lambda *a, **k: True))
            stack.enter_context(mock.patch.object(leaves, "do_plan_batch",
                                                  lambda *a, **k: None))
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(err))
            self.results = flow.flow_ids(self.cfg, ids, do_publish=True, do_act=False,
                                         by="T", today=TODAY)
        self.err = err.getvalue()
        self.assertNotIn("Traceback", self.err)

    def _state(self, iid: str) -> str:
        return state.state(self.cfg.bundle(iid))

    # -- cases -----------------------------------------------------------------------------

    def test_partner_of_an_unpushed_bundle_is_held_and_the_run_goes_on(self) -> None:
        self._fixture()
        self.unpushed = {"issue_701"}
        self._run(["701", "702", "703", "704", "705"])

        # CA was built and accepted in wave 0, but pushed nothing.
        self.assertIn("issue_701", self.built)
        self.assertEqual(self._state("701"), state.COMPLETE)
        # (a) CJ is never built and stays PLANNED.
        self.assertNotIn("issue_702", self.built, self.err)
        self.assertEqual(self._state("702"), state.PLANNED)
        # (b) ONE line names CJ, CA, the conflict edge and why.
        lines = [ln for ln in self.err.splitlines()
                 if "issue_702" in ln and "issue_701" in ln and "Conflicts with" in ln
                 and "pushed no branch" in ln]
        self.assertEqual(len(lines), 1, self.err)
        self.assertNotIn("prerequisite", lines[0])
        self.assertNotRegex(self.err, r"issue_702 skipped — prerequisite")
        # (c) U, in the SAME later wave as CJ, is built and COMPLETE.
        self.assertIn("issue_703", self.built)
        self.assertEqual(self._state("703"), state.COMPLETE)
        # (d) 705 (`Depends on: 702`) cascades: not built.
        self.assertNotIn("issue_705", self.built)
        self.assertEqual(self._state("705"), state.PLANNED)
        # (e) The announcement names the conflict partners too.
        ann = [ln for ln in self.err.splitlines()
               if "issue_701 pushed no branch this run" in ln]
        self.assertEqual(len(ann), 1, self.err)
        self.assertIn("Conflicts with", ann[0])
        self.assertIn("held", ann[0])

    def test_partner_builds_when_the_first_pushed_its_branch(self) -> None:
        """Unchanged: CA's publish pushes its branch, so CJ is built on the line as today."""
        self._fixture()
        self.unpushed = set()
        self._run(["701", "702", "703", "704", "705"])
        for iid in ("701", "702", "703", "704", "705"):
            self.assertIn(f"issue_{iid}", self.built, self.err)
            self.assertEqual(self._state(iid), state.COMPLETE, self.err)
        self.assertNotIn("Conflicts with", self.err)


if __name__ == "__main__":
    unittest.main()
