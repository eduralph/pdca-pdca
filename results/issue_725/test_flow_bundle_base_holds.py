"""A failure that belongs to one bundle holds that bundle, not the run (#725).

Since #727 a stack-mode bundle is built on a base of its own (``integrate.build_bundle_base``,
#723) holding only what it declares. When that base could not be built — the base moved and
now clashes with a prerequisite's branch, a prerequisite's branch was rewritten or cut from
somewhere its record does not say, the fetch failed, origin refused the push — the flow
printed ``STOPPING`` and dropped the rest of the run, bundles that had nothing to do with
the failure included. So did a fold whose merge of one bundle's branch clashed with the
branch of a bundle from an earlier wave (#674 held only a clash with a bundle of the same
wave). Now such a bundle is held, named on one stderr line with the cause and the fix, the
bundles that depend on it wait, and the rest of the run goes on. A failure of the run's
shared line — a conflict with what the fold took in from the base, a red re-gate — still
stops it.

These cases drive ``flow._drive_and_act`` through real folds on the ``StackFoldGit`` fixture
of tests/test_integrate_stack_bases.py (a bare ``origin`` and a primary checkout), loaded by
path exactly as tests/test_flow_same_wave_conflict.py does, with that file's stubs: the
build and sign-off leaves stubbed (``flow._drive_wave`` writes a ``patch.diff`` and
accepts), ``flow._publish_bundle`` cutting and pushing each PR branch from the recorded
stack-base tip, and ``gh`` answered by a stub in front of ``subprocess.run``. The publisher
is NOT a stub (a stub turns every fold into a dry-run). The exit code is the one
``cli._flow`` gives the same run: ``cli._results_rc`` over the results and holds.

Case (2) is driven with prerequisites a fold of THIS run carried (#633's sense of
"carried"): on this base a dependent of a prerequisite finished in an earlier run is cut
from the run's line, not from a base of its own (#728 left that to #735), so its base is
never built. (2a) is a prerequisite whose branch was cut from an old line instead of where
its record says: the base build refuses its ancestry (#723's cut-point check). Case (5)'s
clash between two prerequisites finished in an earlier run is refused by the carry's fold
(#694) before any base is built; it pins that the outcome holds.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_bundle_base_holds
"""

from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import subprocess
import unittest
from collections.abc import Callable
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import cli, flow, integrate, publish, state

_SPEC = importlib.util.spec_from_file_location(
    "stack_bases_fixture", Path(__file__).with_name("test_integrate_stack_bases.py"))
sb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sb)

TODAY = "2026-10-17"


class BundleBaseHolds(unittest.TestCase):

    def setUp(self) -> None:
        self.fx = sb.StackFoldGit()          # the fixture's real-git setUp/tearDown and helpers
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.cfg = self.fx.cfg
        self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
        self.changes: dict[str, dict[str, str]] = {}   # id → the files its build adds
        self.cut_from: dict[str, str] = {}             # id → where publish cuts it (override)
        self.after_fold: list[Callable[[], None]] = []  # run once, after the run's next fold
        self.fetch_fails_for: set[str] = set()         # ids whose own base's fetch fails
        self.seen: dict[str, tuple[str, str]] = {}     # bundle → (stack base, tip) when built
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _plan(self, iid: str, files: dict[str, str], depends_on: str = "") -> None:
        sb._brief(self.cfg.bundle(iid),
                  extra=f"- **Depends on:** {depends_on}\n" if depends_on else "")
        self.changes[iid] = files

    def _finished(self, iid: str, files: dict[str, str]) -> None:
        """``iid`` finished in an earlier run: published from the base and accepted."""
        sb._accept(self.fx._publish(iid, files))

    def _a_z_then_b_w(self) -> list[str]:
        """``A`` and ``Z`` (wave 0, files of their own); ``B`` (``Depends on: A``) and ``W``
        (``Depends on: Z``) in wave 1, each built on a base of its own. Returns the ids."""
        self._plan("A", {"a.txt": "a\n"})
        self._plan("Z", {"z1.txt": "z1\n", "z2.txt": "z2\n"})
        self._plan("B", {"b.txt": "b\n"}, "A")
        self._plan("W", {"w.txt": "w\n"}, "Z")
        return ["A", "Z", "B", "W"]

    # -- stubs -----------------------------------------------------------------------------

    def _gh_stub(self, args, *a, **kw):
        """Any ``gh`` call is answered OPEN with the PR's head, its branch's tip on origin;
        everything else runs for real."""
        if not (isinstance(args, list) and args[:1] == ["gh"]):
            return self._real_run(args, *a, **kw)
        iid = str(args[3]).rsplit("/", 1)[-1]
        head = self.fx._tip(f"fix/{iid}") if self.fx._has(f"fix/{iid}") else ""
        return subprocess.CompletedProcess(
            args, 0, json.dumps({"state": "OPEN", "headRefOid": head}), "")

    def _drive_wave(self, cfg, wave: list[Path], **_kw) -> int:
        """Build and accept each bundle, recording what it was built on."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            self.seen[d.name] = (publish.read_stack_base(d), publish.read_stack_base_tip(d))
            (d / "patch.diff").write_text("".join(
                sb._new_file_patch(n, t.rstrip("\n")) for n, t in self.changes[iid].items()),
                encoding="utf-8")
            sb._accept(d)
        return 1

    def _publish_bundle(self, cfg, d: Path, **_kw) -> bool:
        """What publish does: cut the PR branch from the recorded stack-base tip (else that
        branch, else the base), push it, record it. The run's brief is kept as it was."""
        iid = d.name.removeprefix("issue_")
        tip, base = publish.read_stack_base_tip(d), publish.read_stack_base(d)
        cut = self.cut_from.get(iid) or tip or (f"origin/{base}" if base else "origin/main")
        brief = (d / "brief.md").read_text(encoding="utf-8")
        self.fx._publish(iid, self.changes[iid], cut_from=cut)
        (d / "brief.md").write_text(brief, encoding="utf-8")
        return True

    def _run(self, ids: list[str], *, drive: list[str] | None = None) -> None:
        """One stack-mode run asked for ``ids``, driving ``drive`` (default: all of them)."""
        self.ids = list(ids)
        self.line = integrate.integration_branch(self.cfg, "main", ids)
        self.holds: dict[str, str] = {}
        real_fold, real_build = integrate.fold, integrate.build_bundle_base

        def fold(*a, **kw):
            out = real_fold(*a, **kw)
            hooks, self.after_fold = self.after_fold, []
            for hook in hooks:
                hook()
            return out

        def build(cfg, d: Path, *a, **kw):
            """The base build, its fetch failing for a bundle of ``fetch_fails_for``."""
            if d.name.removeprefix("issue_") not in self.fetch_fails_for:
                return real_build(cfg, d, *a, **kw)
            real_git = integrate._git

            def git(repo: Path, *args: str) -> int:
                return 1 if args[:1] == ("fetch",) else real_git(repo, *args)

            with mock.patch.object(integrate, "_git", git):
                return real_build(cfg, d, *a, **kw)

        self._err = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
            stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
            stack.enter_context(mock.patch.object(flow, "_publish_bundle",
                                                  self._publish_bundle))
            stack.enter_context(mock.patch.object(publish, "draft_texts",
                                                  lambda *a, **k: True))
            stack.enter_context(mock.patch.object(integrate, "fold", fold))
            stack.enter_context(mock.patch.object(integrate, "build_bundle_base", build))
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(self._err))
            self.results = flow._drive_and_act(
                self.cfg, [self.cfg.bundle(i) for i in (drive or ids)], do_publish=True,
                do_act=False, by="T", today=TODAY, batch=ids, holds=self.holds)
        self.err = self._err.getvalue()
        self.rc = cli._results_rc(self.results, holds=self.holds)
        self.assertNotIn("Traceback", self.err)

    # -- helpers ---------------------------------------------------------------------------

    def _lines(self, *parts: str) -> list[str]:
        """The stderr lines holding every one of ``parts``."""
        return [x for x in self.err.splitlines() if all(p in x for p in parts)]

    def _held(self, iid: str, *parts: str) -> str:
        """``iid`` was never built and is left PLANNED, the run did not stop, and ONE stderr
        line names it — saying it is held, with each of ``parts``. Returns that line."""
        self.assertNotIn("STOPPING", self.err)
        self.assertNotIn(f"issue_{iid}", self.seen, self.err)
        self.assertEqual(self.results[iid], state.PLANNED, self.err)
        lines = self._lines(f"issue_{iid}")
        self.assertEqual(len(lines), 1, self.err)
        self.assertIn(f"flow: issue_{iid} held — ", lines[0])
        for part in parts:
            self.assertIn(part, lines[0])
        return lines[0]

    def _complete(self, iid: str) -> None:
        """``iid`` was built and is COMPLETE."""
        self.assertIn(f"issue_{iid}", self.seen, self.err)
        self.assertEqual(self.results[iid], state.COMPLETE, self.err)

    def _head(self, iid: str) -> str:
        return self.fx._tip(f"fix/{iid}")

    # -- (1) the base moved under a prerequisite --------------------------------------------

    def test_a_base_that_moved_under_a_prerequisite_holds_only_its_dependent(self):
        # After wave 0's fold, main gets an a.txt of its own: A's branch no longer merges
        # onto it, so no base of B's can hold A. Before: STOPPING, and W stayed PLANNED.
        ids = self._a_z_then_b_w()
        self.after_fold.append(lambda: self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(ids)
        self._held("B", "issue_A's branch origin/fix/A does not merge cleanly onto origin/main",
                   "Rebuild issue_A's branch on the new origin/main")
        self._complete("W")
        for iid in ("A", "Z"):
            self._complete(iid)
        self.assertEqual(self.holds, {"B": "base"})
        self.assertEqual(self.rc, 3, self.err)

    # -- (2) a prerequisite's branch the base cannot trust -----------------------------------

    def test_a_prerequisite_cut_from_an_old_line_holds_only_its_dependent(self):
        # (2a) An earlier run's line holds X's work. P's branch is cut from that line, not
        # from where its record says, so D's base cannot tell P's own work from X's: the
        # build refuses P's ancestry. W, of D's wave, is built.
        sb._accept(self.fx._publish("X", {"x.txt": "x\n"}))
        old = "pdca-integration/main-rearlier"
        sb._git(self.fx.origin, "branch", old, "main")
        self.fx._merge_pr("X", into=old)
        self._plan("P", {"p.txt": "p\n"})
        self._plan("Z", {"z.txt": "z\n"})
        self._plan("D", {"d.txt": "d\n"}, "P")
        self._plan("W", {"w.txt": "w\n"}, "Z")
        self.cut_from["P"] = f"origin/{old}"
        self._run(["P", "Z", "D", "W"])
        self.assertTrue(self.fx._ancestor(self._head("X"), self._head("P")))
        self._held("D", "could not build issue_D's own base from issue_P", "Re-publish issue_P")
        self._complete("W")
        self.assertEqual(self.holds, {"D": "base"})

    def test_a_prerequisite_rewritten_after_the_fold_holds_only_its_dependent(self):
        # (2b) After the fold carried A, fix/A is force-pushed to another commit (#633): B's
        # base refuses it. The line still holds A's old commits, so the run exits 1 — and
        # the rewrite is named once, by B's hold, not again at the end of the run.
        ids = self._a_z_then_b_w()
        took: list[str] = []

        def rewrite_a() -> None:
            took.append(self._head("A"))
            self.fx._push_from_human({"a2.txt": "A, rebuilt\n"}, to="fix/A", force=True)

        self.after_fold.append(rewrite_a)
        self._run(ids)
        rewritten = "issue_A's branch origin/fix/A was rewritten"
        self._held("B", rewritten, took[0][:12], "Restore origin/fix/A")
        self.assertEqual(len(self._lines(rewritten)), 1, self.err)
        self._complete("W")
        self.assertEqual(self.holds, {"B": "base", "A": "rewritten"})
        self.assertEqual(self.rc, 1, self.err)

    # -- (3) an undeclared overlap with an earlier wave, at the line's fold -----------------

    def test_an_overlap_with_an_earlier_wave_holds_the_bundle_out_of_the_line(self):
        # Y (built on A) and Z (wave 0, unrelated) both add shared.txt. The fold after wave 1
        # cannot merge Y onto the line holding Z. That clash is Y's with Z: Y is held out of
        # the line as #674 holds a same-wave clash, C (built on Y) waits, W goes on.
        self._plan("A", {"a.txt": "a\n"})
        self._plan("Z", {"shared.txt": "from z\n", "z.txt": "z\n"})
        self._plan("Y", {"shared.txt": "from y\n"}, "A")
        self._plan("C", {"c.txt": "c\n"}, "Y")
        self._plan("W", {"w.txt": "w\n"}, "Z")
        self._run(["A", "Z", "Y", "C", "W"])
        self.assertNotIn("STOPPING", self.err)
        self.assertNotIn("did not integrate", self.err)
        held = self._lines("issue_Y held out of the integration fold")
        self.assertEqual(len(held), 1, self.err)
        for part in ("conflicts with issue_Z's", "shared.txt"):
            self.assertIn(part, held[0])
        self.assertFalse(self.fx._ancestor(self._head("Y"), self.fx._tip(self.line)))
        self.assertNotIn("issue_C", self.seen, self.err)
        self.assertEqual(self.results["C"], state.PLANNED, self.err)
        for iid in ("A", "Z", "Y", "W"):
            self._complete(iid)
        self.assertEqual(self.holds, {"Y": "conflict"})

    # -- (4) the fetch of one bundle's base fails ------------------------------------------

    def test_a_fetch_that_fails_for_one_base_holds_only_that_bundle(self):
        ids = self._a_z_then_b_w()
        self.fetch_fails_for.add("B")
        self._run(ids)
        self._held("B", "could not build issue_B's own base from issue_A",
                   f"could not fetch origin in {self.fx.primary.resolve()}", "then re-run")
        self._complete("W")
        self.assertEqual(self.holds, {"B": "base"})

    def test_a_push_origin_refuses_holds_only_that_bundle(self):
        # (4b) Origin refuses non-fast-forwards and already has B's base branch at a commit
        # of its own: the build's forced push is refused, with #723's remedy.
        ids = self._a_z_then_b_w()
        name = integrate.bundle_base_branch(self.cfg, "main", ids, "issue_B")
        stale = self.fx._push_from_human({"stale.txt": "stale\n"}, to=name)
        sb._git(self.fx.origin, "config", "receive.denyNonFastForwards", "true")
        self._run(ids)
        self._held("B", f"could not push {name} to origin", f"delete {name} there",
                   "allow force-pushes on pdca-integration/*")
        self.assertEqual(self.fx._tip(name), stale)
        self._complete("W")
        self.assertEqual(self.holds, {"B": "base"})

    # -- (5) two prerequisites that clash with each other -----------------------------------

    def test_two_finished_prerequisites_that_clash_hold_only_their_dependent(self):
        # P and Q, finished in an earlier run on an unmoved main, add different s.txt; D
        # depends on both. W, unrelated, is built.
        self._finished("P", {"s.txt": "from p\n"})
        self._finished("Q", {"s.txt": "from q\n"})
        self._plan("D", {"d.txt": "d\n"}, "P, Q")
        self._plan("W", {"w.txt": "w\n"})
        self._run(["P", "Q", "D", "W"], drive=["D", "W"])
        self.assertNotIn("STOPPING", self.err)
        self.assertNotIn("issue_D", self.seen, self.err)
        self.assertEqual(self.results["D"], state.PLANNED, self.err)
        self.assertEqual(len(self._lines("issue_D", "issue_P", "issue_Q")), 1, self.err)
        self._complete("W")


if __name__ == "__main__":
    unittest.main()
