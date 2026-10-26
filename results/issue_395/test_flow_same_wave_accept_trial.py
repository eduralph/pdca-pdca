"""A same-wave conflict is refused at accept, never published and then held (#395).

Two bundles of one wave can both pass Check while their branches conflict textually, with no
`Conflicts with` between them. Since #674 the fold after the wave holds the later one — but
only after both were accepted and both PRs opened, so the run left two conflicting draft
PRs, and an accepted bundle whose PR the human had to close or redo. Now, on every wave the
fold runs after, the accept that would add such a conflict is refused the way C6 refuses
one: the bundle stays AWAITING_SIGNOFF with an open §6 row naming the bundles it conflicts
with, the files, and the step. It is never published. Every accepted bundle still ends in a
PR. When the check cannot run, the files each patch touches decide, read as git wrote them
(a quoted non-ASCII path included), and a patch whose files cannot be read may share any.
An iterate-plan recorded after the refusal is re-planned by the next run, not this one,
which would only rebuild the bundle beside the one it conflicts with.

These cases drive ``flow._drive_and_act`` over real git — the ``StackFoldGit`` fixture of
tests/test_integrate_stack_bases.py (a bare ``origin`` and a primary checkout), through the
``SameWaveConflict`` stubs of tests/test_flow_same_wave_conflict.py, both loaded by path.
Unlike that suite, ``flow._drive_wave`` is NOT stubbed: every accept goes through the real
``_drive_wave`` → ``_apply_decision`` path, as tests/test_signoff_orphan.py drives it. Do and
Check are stubbed (``flow._build_all`` runs the real Plan pre-pass the driver's own
``_build_all`` runs first, with the Plan leaf stubbed, then writes each bundle's
``patch.diff`` and the SUMMARY the driver's own assembly step writes), a decision is either
recorded in the bundle before its wave signs off (``leaves.SIGNOFF_DECISION``) or written by
the stubbed sign-off session (``leaves.run_signoff_batch``), ``flow._publish_bundle`` cuts,
pushes and records the PR branch and then runs the ``gh pr create`` publish runs, and ``gh``
is answered by a stub in front of ``subprocess.run``. The publisher is NOT a stub (a stub
turns every fold into a dry-run). Nothing here calls ``signoff.record(... "accept")``.
``GitWrittenPaths`` reads the paths of patches a real ``git diff`` wrote, as that check's
fallback reads them.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_same_wave_accept_trial
"""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pdca_harness import (assemble, brief, cli, flow, integrate, leaves, publish, signoff, state,
                          waves)

_SPEC = importlib.util.spec_from_file_location(
    "same_wave_conflict_fixture", Path(__file__).with_name("test_flow_same_wave_conflict.py"))
swc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(swc)
sb = swc.sb                     # the StackFoldGit fixture module, loaded by path there

TODAY = "2026-10-25"
NINE = swc.NINE                 # a nine-line file on the base
_edit = swc._edit

# A Check review with nothing for the human, closed as a finished leaf closes it: the
# SUMMARY assembled over it has an empty §6, so only what the run adds there can refuse.
REVIEW = ("# Cross-vendor reviewer (advisory, artifact-only)\n\nNo finding for the human.\n\n"
          f"{assemble.LEAF_COMPLETE_TRAILER}\n")


class SameWaveAcceptTrial(unittest.TestCase):
    # The SameWaveConflict fixture and stubs, borrowed method by method: subclassing it
    # would collect and run its own cases again here.
    _on_base = swc.SameWaveConflict._on_base
    _plan = swc.SameWaveConflict._plan
    _patch = swc.SameWaveConflict._patch
    _gh_stub = swc.SameWaveConflict._gh_stub

    def setUp(self) -> None:
        swc.SameWaveConflict.setUp(self)     # real git; the publisher in command mode
        self.recorded: dict[str, str] = {}   # id → the decision its bundle carries at build
        self.check_rows: dict[str, str] = {}  # id → an open §6 row Check gave it
        # id → what its n-th sign-off session does (None, or past the list: nothing)
        self.session: dict[str, list[Callable[[Path], None] | None]] = {}
        self.sessions_had: dict[str, int] = {}
        self.session_calls: list[list[str]] = []
        self.built: list[str] = []
        self.patches: list = []              # extra patches for one case's run
        self.at_session: dict[str, tuple[str, str, str]] = {}   # id → the integration tree
        self.planned: list[str] = []         # the bundles the Plan leaf (re-)planned
        self.replans: dict[str, str] = {}    # id → `Conflicts with` its re-planned brief gets
        self.git_made: set[str] = set()      # ids whose patch.diff `git diff` writes
        self.plain: set[str] = set()         # ids whose patch.diff is a plain (non-git) diff

    # -- stubs -----------------------------------------------------------------------------

    def _build_all(self, cfg, bundles: list[Path]) -> None:
        """Plan, then Do + Check, stubbed. First the Plan pre-pass the driver's own
        ``_build_all`` runs over the bundles it is handed (``flow._plan_if_unplanned``, the
        Plan leaf stubbed by ``_plan_leaf``): a bundle an iterate-plan re-opened is re-planned
        here unless the wave holds it back. Then each bundle still PLANNED gets its change
        against the base as its ``patch.diff`` (written by ``git diff`` for ``git_made``, a
        plain diff for ``plain``), a clean gate record and review, and the SUMMARY the driver's
        own assembly step writes (``assemble.assemble_summary``): AWAITING_SIGNOFF. A §6 row
        of ``check_rows`` is added as Check would, and a decision of ``recorded`` is written
        into the bundle, as a session that ended before the driver applied it leaves one."""
        for d in bundles:
            flow._isolate(d, "plan", lambda d=d: flow._plan_if_unplanned(cfg, d, None))
        for d in bundles:
            if state.state(d) != state.PLANNED:
                continue
            iid = d.name.removeprefix("issue_")
            self.built.append(d.name)
            files = self.changes[iid]
            patch = self._git_patch(files) if iid in self.git_made else self._patch(files)
            if iid in self.plain:      # no `diff --git` header: a plain unified diff
                patch = "".join(x for x in patch.splitlines(keepends=True)
                                if not x.startswith(("diff --git ", "new file mode ")))
            (d / "patch.diff").write_text(patch, encoding="utf-8")
            (d / "check-gates.json").write_text(json.dumps({"overall": "pass", "rows": []}),
                                                encoding="utf-8")
            (d / "check-review.md").write_text(REVIEW, encoding="utf-8")
            assemble.assemble_summary(d, cfg)
            if iid in self.check_rows:
                signoff.ensure_needs_human_item(d / "SUMMARY.md", self.check_rows[iid])
            if iid in self.recorded:
                (d / leaves.SIGNOFF_DECISION).write_text(self.recorded[iid], encoding="utf-8")

    def _plan_leaf(self, d: Path, cfg, csv: str | None = None) -> None:
        """The Plan leaf, stubbed: records the bundle, and re-plans it — its brief written as
        planned, with `Conflicts with` the ids ``replans`` names for it — or, for one
        ``replans`` does not name, writes nothing (the planner declined)."""
        iid = d.name.removeprefix("issue_")
        self.planned.append(d.name)
        if iid in self.replans:
            self._plan(iid, self.changes[iid], conflicts_with=self.replans[iid])

    def _plan_batch(self, cfg, csv: str | None = None, ids: list[str] | None = None) -> None:
        """``flow_ids``' shared Plan pre-pass, stubbed: the Plan leaf over each id."""
        for iid in ids or []:
            self._plan_leaf(cfg.bundle(iid), cfg, csv)

    def _git_patch(self, files: dict[str, str]) -> str:
        """``files``' change against the base as git writes it: ``git diff`` in the primary
        checkout, with git's default ``core.quotePath`` (a non-ASCII path written quoted,
        ``"a/caf\\303\\251.txt"``), then undone."""
        repo = self.fx.primary
        for name, text in files.items():
            (repo / name).write_text(text, encoding="utf-8")
        sb._git(repo, "add", "--all")
        patch = sb._git(repo, "-c", "core.quotePath=true", "diff", "--cached")
        sb._git(repo, "reset", "-q", "--hard")
        return patch

    def _sessions(self, cfg, bundles: list[Path]) -> None:
        """The sign-off leaf, stubbed: records which bundles each session covers, and does
        for each what ``session`` says for its n-th session. The integration tree, as the
        session finds it, is recorded too."""
        self.session_calls.append([b.name for b in bundles])
        for b in bundles:
            iid = b.name.removeprefix("issue_")
            n = self.sessions_had[iid] = self.sessions_had.get(iid, 0) + 1
            self.at_session[iid] = self._integration_tree()
            steps = self.session.get(iid, [])
            if n <= len(steps) and steps[n - 1] is not None:
                steps[n - 1](b)

    def _publish_bundle(self, cfg, d: Path, **kw) -> bool:
        """SameWaveConflict's publish stub — cut the PR branch where publish cuts it, push
        it, record it — then the draft PR publish opens once the branch is pushed, through
        the ``gh`` stub, which records it."""
        pushed = swc.SameWaveConflict._publish_bundle(self, cfg, d, **kw)
        iid = d.name.removeprefix("issue_")
        subprocess.run(["gh", "pr", "create", "--draft", "--repo", "org/repo", "--base", "main",
                        "--head", f"org:fix/{iid}", "--title", f"fix {iid}"],
                       capture_output=True, text=True)
        return pushed

    def _run(self, ids: list[str], *, max_passes: int | None = None,
             drive: list[str] | None = None, as_cli: bool = False) -> None:
        """One stack-mode run asked for ``ids``, driving all of them — or ``drive``, the ones
        ``flow_ids`` drives on a re-run, which skips the finished ids. ``as_cli``: through
        ``flow.flow_ids`` as ``pdca flow <ids>`` calls it, its Plan pre-pass included."""
        self.ids = list(ids)
        self.line = integrate.integration_branch(self.cfg, "main", ids)
        drive = [self.cfg.bundle(i) for i in (ids if drive is None else drive)]
        self._err, out = io.StringIO(), io.StringIO()
        self.holds: dict[str, str] = {}
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
            stack.enter_context(mock.patch.object(flow, "_build_all", self._build_all))
            stack.enter_context(mock.patch.object(leaves, "do_plan", self._plan_leaf))
            stack.enter_context(mock.patch.object(leaves, "do_plan_batch", self._plan_batch))
            stack.enter_context(mock.patch.object(leaves, "run_signoff_batch", self._sessions))
            stack.enter_context(mock.patch.object(flow, "_publish_bundle",
                                                  self._publish_bundle))
            stack.enter_context(mock.patch.object(publish, "draft_texts",
                                                  lambda *a, **k: True))
            for p in self.patches:
                stack.enter_context(p)
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(self._err))
            if as_cli:
                self.results = flow.flow_ids(self.cfg, ids, plan_missing=True,
                                             do_publish=True, do_act=False, by="T",
                                             today=TODAY, holds=self.holds,
                                             max_passes=max_passes)
            else:
                self.results = flow._drive_and_act(self.cfg, drive, do_publish=True,
                                                   do_act=False, by="T", today=TODAY,
                                                   batch=ids, holds=self.holds,
                                                   max_passes=max_passes)
        self.err = self._err.getvalue()
        self.rc = cli._results_rc(self.results, holds=self.holds)
        self.assertNotIn("Traceback", self.err)
        self.assertNotIn("skipping this bundle", self.err)   # no step of a bundle raised

    # -- what a session does -----------------------------------------------------------------

    @staticmethod
    def _writes_accept(d: Path) -> None:
        (d / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")

    def _ticks_and_accepts(self, d: Path) -> None:
        """The human clears every open §6 row and accepts: an override."""
        summary = d / "SUMMARY.md"
        summary.write_text(summary.read_text(encoding="utf-8").replace("- [ ]", "- [x]"),
                           encoding="utf-8")
        self._writes_accept(d)

    # -- helpers ---------------------------------------------------------------------------

    def _pair(self, *, b_line: str = "l2") -> list[str]:
        """Wave 0: 10 and 11 change line 2 of shared.txt — a textual conflict, with no
        `Conflicts with` between them (``b_line``: the line 11 changes) — and 12 a file of
        its own. Wave 1: 20, depending on 12 alone, so a fold runs after wave 0. Returns the
        ids."""
        self._on_base({"shared.txt": NINE})
        self._plan("10", {"shared.txt": _edit(NINE, l2="ten")})
        self._plan("11", {"shared.txt": _edit(NINE, **{b_line: "eleven"})})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        return ["10", "11", "12", "20"]

    def _summary(self, iid: str) -> Path:
        return self.cfg.bundle(iid) / "SUMMARY.md"

    def _open(self, iid: str, naming: str) -> list[str]:
        """``iid``'s open §6 rows that name ``issue_<naming>``."""
        return [r for r in signoff.open_needs_human(self._summary(iid))
                if f"issue_{naming}" in r]

    def _ticked(self, iid: str, naming: str) -> list[str]:
        """``iid``'s ticked §6 rows that name ``issue_<naming>``."""
        return [r for r in signoff.cleared_needs_human(self._summary(iid))
                if f"issue_{naming}" in r]

    def _created(self, iid: str) -> list[list[str]]:
        """The ``gh pr create`` calls for ``iid``'s branch."""
        return [c for c in self.gh_calls
                if c[:3] == ["gh", "pr", "create"] and f"org:fix/{iid}" in c]

    def _published(self, iid: str) -> None:
        self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        self.assertTrue(self.fx._has(f"fix/{iid}"), self.err)
        self.assertEqual(len(self._created(iid)), 1, self.gh_calls)

    def _not_published(self, iid: str) -> None:
        self.assertEqual(state.state(self.cfg.bundle(iid)), state.AWAITING_SIGNOFF, self.err)
        self.assertFalse(self.fx._has(f"fix/{iid}"), self.err)
        self.assertEqual(self._created(iid), [], self.gh_calls)
        self.assertNotIn(iid, self.holds)

    def _integration_tree(self) -> tuple[str, str, str]:
        """``(status, the branch checked out, HEAD)`` of the target's integration worktree,
        or empty strings when there is none yet."""
        wt = integrate._integ_worktree(self.fx.primary, "main")
        if not (wt / ".git").exists():
            return "", "", ""
        run = self._real_run
        return tuple(run(["git", "-C", str(wt), *args], capture_output=True,
                         text=True).stdout.strip()
                     for args in (("status", "--porcelain"), ("symbolic-ref", "-q", "HEAD"),
                                  ("rev-parse", "HEAD")))

    def _on_the_line_at_base(self, iid: str) -> None:
        """When ``iid``'s session opened, the integration tree was clean, on the run's line,
        at origin's main — where the wave found the line."""
        self.assertEqual(self.at_session.get(iid),
                         ("", f"refs/heads/{self.line}", self.fx._tip("main")), self.err)

    def _no_commit_builds(self) -> list:
        """Make every would-be commit fail to build in the run, so the trial cannot run
        (its `git apply` fails); returns the list each failed step is added to."""
        real, failed = integrate._git, []

        def no_commit_builds(repo: Path, *args: str) -> int:
            if args[:1] == ("apply",):
                failed.append(args)
                return 1
            return real(repo, *args)

        self.patches.append(mock.patch.object(integrate, "_git", no_commit_builds))
        return failed

    # -- (a) the later accept is refused, the earlier published ------------------------------

    def test_a_conflicting_accept_is_refused_and_its_sibling_published(self):
        ids = self._pair()
        self.recorded = {i: "accept\n" for i in ids}
        self._run(ids)

        self._published("10")
        self._not_published("11")
        rows = self._open("11", "10")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("shared.txt", rows[0])
        self.assertIn("`Conflicts with: 10`", rows[0])
        self.assertIn("iterate-plan", rows[0])
        self.assertIn(rows[0], signoff.open_needs_human(self._summary("11")))
        self.assertEqual(self.rc, 1, self.err)               # 11 did not finish
        self.assertIn("issue_20", self.built)                # wave 1 still builds…
        self._published("20")                                # …and completes
        self._published("12")
        # The trial ran in the integration tree and left it clean on the line.
        self._on_the_line_at_base("11")

    # -- (b) a shared file that merges cleanly changes nothing -------------------------------

    def test_a_shared_file_that_merges_cleanly_is_accepted(self):
        ids = self._pair(b_line="l8")
        self.recorded = {i: "accept\n" for i in ids}
        self._run(ids)

        for iid in ids:
            self._published(iid)
        for iid in ("10", "11"):
            self.assertEqual(signoff.open_needs_human(self._summary(iid)), [], iid)
            self.assertEqual(signoff.cleared_needs_human(self._summary(iid)), [], iid)
        self.assertEqual(self.holds, {}, self.err)
        self.assertEqual(self.rc, 0, self.err)
        self.assertEqual(self.sessions_had, {}, self.err)

    # -- (c) whichever is accepted first is kept --------------------------------------------

    def test_the_refusal_does_not_depend_on_which_accept_comes_first(self):
        # 11's accept is recorded, so the pre-apply takes it before 10's session opens; 10,
        # which sorts first, is then the one refused: the fold would have held 11 for it.
        ids = self._pair()
        self.recorded = {i: "accept\n" for i in ids if i != "10"}
        self.session = {"10": [self._writes_accept]}
        self._run(ids)

        self._published("11")
        self._not_published("10")
        rows = self._open("10", "11")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("shared.txt", rows[0])
        self.assertIn("`Conflicts with: 11`", rows[0])
        self.assertEqual([i for i in ("10", "11")
                          if self.results[i] == state.COMPLETE], ["11"], self.err)
        self.assertEqual(self.holds, {}, self.err)            # the fold holds nothing

    # -- (d) an override in the same run: accepted, published, held by the fold --------------

    def test_ticking_the_row_accepts_it_and_the_fold_holds_it(self):
        ids = self._pair()
        self.recorded = {i: "accept\n" for i in ids}
        self.session = {"11": [self._ticks_and_accepts]}
        self._run(ids)

        self.assertEqual(self.sessions_had.get("11"), 1, self.err)   # offered after refusal
        self._published("11")
        self.assertEqual(self.holds.get("11"), "conflict", self.err)  # #674, as on main
        self.assertEqual(len(self._ticked("11", "10")), 1, self.err)  # added once, kept
        self.assertEqual(self._open("11", "10"), [], self.err)
        self.assertEqual(self.rc, 3, self.err)

    # -- (e) the check cannot run: refuse only where a conflict is possible -----------------

    def test_a_trial_that_cannot_run_refuses_only_a_bundle_sharing_a_file(self):
        # 11 changes line 8 here, so it would merge cleanly: only the shared path refuses it.
        ids = self._pair(b_line="l8")
        self.recorded = {i: "accept\n" for i in ids}
        failed = self._no_commit_builds()
        self._run(ids)

        self.assertTrue(failed, self.err)
        self._published("10")
        self._not_published("11")
        rows = self._open("11", "10")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("could not run", rows[0])
        self.assertIn("shared.txt", rows[0])
        self._published("12")                   # no file shared with an accepted sibling
        self._on_the_line_at_base("11")         # a raising trial left the tree on the line

    def test_a_quoted_non_ascii_path_is_read_when_the_trial_cannot_run(self):
        # 10 and 11 change line 2 of café.txt, and git writes that path quoted in the patch
        # (`"a/caf\303\251.txt"`). The trial cannot run, so the shared path must be read
        # from the patches as git wrote them: 11 is refused, not taken to share nothing.
        self._on_base({"café.txt": NINE})
        self._plan("10", {"café.txt": _edit(NINE, l2="ten")})
        self._plan("11", {"café.txt": _edit(NINE, l2="eleven")})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        ids = ["10", "11", "12", "20"]
        self.git_made = {"10", "11", "12"}
        self.recorded = {i: "accept\n" for i in ids}
        failed = self._no_commit_builds()
        self._run(ids)

        self.assertTrue(failed, self.err)
        made = (self.cfg.bundle("11") / "patch.diff").read_text(encoding="utf-8")
        self.assertIn('diff --git "a/caf\\303\\251.txt" "b/caf\\303\\251.txt"', made)
        self._published("10")
        self._not_published("11")
        rows = self._open("11", "10")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("could not run", rows[0])
        self.assertIn("café.txt", rows[0])
        self._published("12")                   # its path is read too: shares nothing
        self._published("20")
        self.assertEqual(self.rc, 1, self.err)

    def test_a_patch_whose_paths_cannot_be_read_may_share_any(self):
        # 11 changes a file of its own, but its patch is a plain unified diff with no
        # `diff --git` header, whose paths `git apply` reads by a guess. The trial cannot
        # run, and what 11 touches is not known: it may share a file with 10, so it is
        # refused, never taken to share none. 12's patch is read: it shares nothing.
        self._on_base({"shared.txt": NINE, "other.txt": NINE})
        self._plan("10", {"shared.txt": _edit(NINE, l2="ten")})
        self._plan("11", {"other.txt": _edit(NINE, l2="eleven")})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        ids = ["10", "11", "12", "20"]
        self.plain = {"11"}
        self.recorded = {i: "accept\n" for i in ids}
        failed = self._no_commit_builds()
        self._run(ids)

        self.assertTrue(failed, self.err)
        made = (self.cfg.bundle("11") / "patch.diff").read_text(encoding="utf-8")
        self.assertTrue(made.startswith("--- a/other.txt\n+++ b/other.txt\n@@ "), made)
        self._published("10")
        self._not_published("11")
        rows = self._open("11", "10")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("could not run", rows[0])
        self.assertIn("could not all be read", rows[0])
        self._published("12")
        self._published("20")

    def test_a_check_that_breaks_the_tree_refuses_and_names_it(self):
        # 12 shares no file with 10, so a check that merely could not run would accept it.
        # Here building 12's would-be commit fails, and then the integration tree will not
        # go back on the line once: the shared tree's state is unknown, which the fold stops
        # on. 12 is refused, never accepted on the shared-path fallback, and the row names
        # that state, keeping what failed first.
        self._on_base({"shared.txt": NINE})
        self._plan("10", {"shared.txt": _edit(NINE, l2="ten")})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "10")    # a later wave: a fold follows
        ids = ["10", "12", "20"]
        self.recorded = {i: "accept\n" for i in ids}
        real, injected = integrate._git, []

        def breaks_once(repo: Path, *args: str) -> int:
            if args[:1] == ("apply",) and "issue_12" in args[1]:
                injected.append("apply")          # 12's would-be commit does not build…
                return 1
            if injected[-1:] == ["apply"] and args[:2] == ("checkout", "-q") and len(args) == 3:
                injected.append("checkout")       # …and the line will not come back, once
                return 1
            return real(repo, *args)

        # What the trial raised, through the real function (absent before the fix, where
        # nothing calls it: `create=True`, so that leg fails on an assertion, not here).
        real_clash, raised = getattr(integrate, "same_wave_clash", None), []

        def clash_spy(*a, **kw):
            try:
                return real_clash(*a, **kw)
            except Exception as exc:
                raised.append(exc)
                raise

        self.patches += [mock.patch.object(integrate, "_git", breaks_once),
                         mock.patch.object(integrate, "same_wave_clash", clash_spy,
                                           create=True)]
        self._run(ids)

        self.assertEqual(injected, ["apply", "checkout"], self.err)
        self._published("10")
        self._not_published("12")
        rows = self._open("12", "10")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("could not put back", rows[0])            # the tree's state, named…
        self.assertIn("does not apply", rows[0])                # …with what failed first
        self.assertIn("check that checkout", rows[0])
        self.assertNotIn("shares no file", self.err)            # no fallback accepted it
        # The error the trial raised is the fold's own, chained to the first one.
        self.assertEqual([type(e) for e in raised], [integrate._LineBroken], self.err)
        self.assertIsInstance(raised[0].__cause__, integrate.IntegrationError)
        self.assertIn("does not apply", str(raised[0].__cause__))
        self._on_the_line_at_base("12")         # put back on the line all the same
        self._published("20")
        self.assertEqual(self.rc, 1, self.err)                  # 12 did not finish

    # -- (f) the row lives only in SUMMARY §6 -----------------------------------------------

    def test_a_reassembled_summary_drops_the_row_and_the_next_accept_refuses_again(self):
        ids = self._pair()
        self.recorded = {i: "accept\n" for i in ids}
        dropped: list[list[str]] = []

        def reassembles_and_accepts(d: Path) -> None:
            # What an iterate-do or an auto-iterate rebuild ends in: the driver's own
            # assembly step writes §6 again from the Check artifacts. The tick goes with it.
            self._ticks_and_accepts(d)
            assemble.assemble_summary(d, self.cfg)
            dropped.append([*signoff.open_needs_human(d / "SUMMARY.md"),
                            *signoff.cleared_needs_human(d / "SUMMARY.md")])
            self._writes_accept(d)

        self.session = {"11": [reassembles_and_accepts]}
        self._run(ids)

        self.assertEqual(dropped, [[]], self.err)       # the reassembly dropped row and tick
        self._not_published("11")
        rows = self._open("11", "10")
        self.assertEqual(len(rows), 1, self.err)         # back, and unticked
        self.assertEqual(self._ticked("11", "10"), [], self.err)
        # Never a Check finding: nothing auto-iterate reads carries it.
        self.assertFalse([it for it in assemble.collect_needs_human(self.cfg.bundle("11"),
                                                                     self.cfg)
                          if "issue_10" in it.text], self.err)

    # -- (h) a refused bundle is offered one more session, not one every pass ----------------

    def test_a_refused_bundle_gets_one_more_session_then_the_wave_ends(self):
        ids = self._pair()
        self.session = {i: [self._writes_accept] for i in ids}   # 11: nothing after that
        self._run(ids, max_passes=20)

        offered = [c for c in self.session_calls if "issue_11" in c]
        self.assertLessEqual(len(offered), 2, self.session_calls)
        self._not_published("11")
        self._published("20")
        # What counted the session after the refusal is a file of the bundle, not the run.
        mark = json.loads((self.cfg.bundle("11") / "same-wave-refusal.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(mark["sessions"], 1, mark)
        about = [x for x in self.err.splitlines() if "issue_11" in x]
        end = [x for x in about if "not accepted" in x]
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("issue_10", end[0])
        self.assertIn("`Conflicts with: 10`", end[0])
        self.assertIn("iterate-plan", end[0])
        self.assertFalse([x for x in about if "max_passes" in x], self.err)
        self.assertNotIn("pass budget exhausted", self.err)

    def test_a_session_that_fails_is_not_the_one_more_session(self):
        # The session offered after the refusal raises: no session ran, so it is not the
        # one the bound allows. 11 is offered another, and parked only after that one.
        ids = self._pair()
        self.recorded = {i: "accept\n" for i in ids}

        def leaf_dies(d: Path) -> None:
            raise RuntimeError("the sign-off leaf died")

        self.session = {"11": [leaf_dies]}                  # then: nothing recorded
        self._run(ids, max_passes=20)

        self.assertEqual(self.err.count("sign-off session over ['issue_11'] failed"), 1,
                         self.err)
        self.assertEqual(self.sessions_had.get("11"), 2, self.err)   # the dropped one, then one
        self._not_published("11")
        mark = json.loads((self.cfg.bundle("11") / "same-wave-refusal.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(mark["sessions"], 1, mark)                   # only the one that ran
        end = [x for x in self.err.splitlines() if "issue_11" in x and "not accepted" in x]
        self.assertEqual(len(end), 1, self.err)
        self.assertNotIn("pass budget exhausted", self.err)
        self._published("20")

    def test_a_later_run_offers_the_refused_bundle_a_session_again(self):
        # The count is the wave's own: a re-run skips the finished ids, so 11 is driven
        # alone, with no accepted sibling, and is offered a session — where the human can
        # tick the row and accept it after all — not left with none.
        ids = self._pair()
        self.session = {i: [self._writes_accept] for i in ids}   # 11: nothing after that
        self._run(ids)
        self._not_published("11")

        self.session, self.sessions_had = {"11": [self._ticks_and_accepts]}, {}
        self._run(ids, drive=["11"])
        self.assertEqual(self.sessions_had.get("11"), 1, self.err)
        self._published("11")

    def test_a_later_run_parks_the_refused_bundle_after_one_session_too(self):
        # The re-run where the row stays open: 11's refused accept is still on disk, and
        # C6 refuses it every pass. One session, then the conflict step — never a spin to
        # the pass budget and its "raise [driver].max_passes".
        ids = self._pair()
        self.session = {i: [self._writes_accept] for i in ids}   # 11: nothing after that
        self._run(ids)
        self._not_published("11")

        self.session, self.sessions_had, self.session_calls = {}, {}, []
        self._run(ids, max_passes=20, drive=["11"])

        self.assertEqual(self.sessions_had.get("11"), 1, self.err)
        self.assertEqual(len(self.session_calls), 1, self.session_calls)
        self._not_published("11")
        self.assertEqual(len(self._open("11", "10")), 1, self.err)    # the row, still open
        end = [x for x in self.err.splitlines() if "issue_11" in x and "not accepted" in x]
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("issue_10", end[0])
        self.assertIn("`Conflicts with: 10`", end[0])
        self.assertIn("iterate-plan", end[0])
        self.assertNotIn("max_passes", self.err)
        self.assertNotIn("pass budget exhausted", self.err)
        self.assertEqual(self.rc, 1, self.err)

    def test_iterate_plan_from_the_cli_leaves_the_rebuilt_bundle_to_a_new_session(self):
        # The step the row and the wave-end line name, taken once the run is over:
        # `pdca signoff 11 --iterate-plan`, a re-plan that declares `Conflicts with: 10`, and
        # the same ids run again. The accept the check refused was about the attempt that
        # iterate archived, so the rebuilt 11 reaches AWAITING_SIGNOFF and is offered a
        # session of its own — never accepted, and published, on that old decision.
        ids = self._pair()
        self.session = {i: [self._writes_accept] for i in ids}   # 11: nothing after that
        self._run(ids)
        self._not_published("11")
        d = self.cfg.bundle("11")
        self.assertEqual(leaves.signoff_decision(d), "accept")   # the refused accept, kept

        said = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(said):
            rc = cli._signoff(self.cfg, SimpleNamespace(
                issue_id="11", accept=False, iterate_do=False, iterate_plan=True,
                discontinue=False, by="T", delta="declare Conflicts with: 10",
                no_publish=False))
        self.assertEqual(rc, 0, said.getvalue())
        self.assertEqual(state.state(d), state.UNPLANNED)        # archived with its brief
        self._plan("11", self.changes["11"], conflicts_with="10")        # the re-plan

        found: list[tuple[str, str]] = []

        def reads_it(b: Path) -> None:      # the human reads the new attempt, decides later
            found.append((state.state(b), leaves.signoff_decision(b)))

        self.session, self.sessions_had, self.built = {"11": [reads_it]}, {}, []
        self._run(ids, max_passes=1, drive=["11"])

        self.assertEqual(self.built, ["issue_11"], self.err)                 # rebuilt…
        self.assertEqual(found, [(state.AWAITING_SIGNOFF, "")], self.err)    # …and asked
        self.assertNotIn("applied the 'accept'", self.err)
        self._not_published("11")
        self.assertIn("'accept'", said.getvalue())       # the CLI said what it deleted

    def test_an_iterate_plan_after_the_refusal_is_re_planned_by_the_next_run(self):
        # 11 is refused, and the session it is offered then writes iterate-plan: the step
        # its row names. The run records it and re-opens 11 for Plan, but does not re-plan
        # or rebuild it: waves are set when a run starts, so this one would rebuild 11 on
        # the same base, beside 10, and refuse it again. The wave goes on for 12, which its
        # first session leaves undecided, so it builds again with 11 still unplanned. The
        # next run re-plans 11.
        ids = self._pair()
        self.recorded = {"10": "accept\n", "11": "accept\n", "20": "accept\n"}

        def iterate_plan(d: Path) -> None:
            (d / leaves.SIGNOFF_DECISION).write_text(
                "iterate-plan\ndeclare Conflicts with: 10\n", encoding="utf-8")

        self.session = {"11": [iterate_plan, self._writes_accept],
                        "12": [None, self._writes_accept]}
        self.replans = {"11": "10"}               # a re-plan would declare the conflict
        self._run(ids, max_passes=20)

        d = self.cfg.bundle("11")
        self.assertEqual(state.state(d), state.UNPLANNED, self.err)    # re-opened for Plan…
        self.assertEqual(self.planned, [], self.err)                    # …but not re-planned
        self.assertEqual(self.built.count("issue_11"), 1, self.err)     # nor rebuilt
        self.assertEqual(self.sessions_had.get("11"), 1, self.err)
        self.assertEqual(self.sessions_had.get("12"), 2, self.err)      # the wave went on
        self.assertEqual(self.err.count("issue_11 — cannot accept"), 1, self.err)
        self.assertFalse(self.fx._has("fix/11"), self.err)
        self.assertEqual(self._created("11"), [], self.gh_calls)
        self.assertNotIn("11", self.holds)
        self.assertEqual(self.results["11"], state.UNPLANNED)
        self.assertEqual(self.rc, 1, self.err)                          # 11 did not finish
        for iid in ("10", "12", "20"):
            self._published(iid)
        end = [x for x in self.err.splitlines() if "issue_11 [UNPLANNED]" in x]
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("issue_10", end[0])
        self.assertIn("next `pdca flow` run re-plans it (`pdca flow 11`", end[0])
        self.assertIn("issue_10's PR has merged", end[0])
        self.assertNotIn("max_passes", self.err)
        self.assertNotIn("pass budget exhausted", self.err)
        self.assertNotIn("made no progress", self.err)

        # The next run of the same ids re-plans it — its Plan pre-pass — and drives it to a
        # session of its own (the human reads the new attempt and decides later).
        self.planned, self.built, self.sessions_had = [], [], {}
        self.recorded, self.session = {}, {"11": [None]}
        self._run(ids, max_passes=1, as_cli=True)
        self.assertEqual(self.planned, ["issue_11"], self.err)
        self.assertEqual(self.built, ["issue_11"], self.err)
        self.assertEqual(self.sessions_had.get("11"), 1, self.err)
        self.assertEqual(brief.conflicts_with(d / "brief.md"), ["10"])
        self.assertFalse((d / state.SAME_WAVE_REFUSAL).exists(), self.err)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF, self.err)

    def test_the_step_never_asks_to_declare_a_conflict_the_brief_already_has(self):
        # 11's brief comes to declare `Conflicts with: 10` mid-run: an iterate-plan before
        # any refusal, re-planned in this run. The waves were set before, so 11 is still in
        # 10's wave, and its next accept is refused. The step names iterate-plan and the
        # next run, but does not ask to declare what the brief already declares.
        ids = self._pair()
        self.recorded = {i: "accept\n" for i in ids if i != "11"}

        def iterate_plan(d: Path) -> None:
            (d / leaves.SIGNOFF_DECISION).write_text("iterate-plan\n", encoding="utf-8")

        self.session = {"11": [iterate_plan, self._writes_accept]}
        self.replans = {"11": "10"}
        self._run(ids, max_passes=20)

        d = self.cfg.bundle("11")
        self.assertEqual(self.planned, ["issue_11"], self.err)        # re-planned in this run
        self.assertEqual(brief.conflicts_with(d / "brief.md"), ["10"])
        self._published("10")
        self._not_published("11")
        rows = self._open("11", "10")
        self.assertEqual(len(rows), 1, self.err)
        self.assertIn("shared.txt", rows[0])
        self.assertIn("iterate-plan", rows[0])
        self.assertIn("next `pdca flow` run re-plans it", rows[0])
        self.assertNotIn("declare", rows[0])
        self.assertNotIn("`Conflicts with", rows[0])
        end = [x for x in self.err.splitlines() if "issue_11" in x and "not accepted" in x]
        self.assertEqual(len(end), 1, self.err)
        self.assertNotIn("declare", end[0])

    def test_a_plain_c6_refusal_is_still_offered_a_session_every_pass(self):
        # An open §6 row from Check, no trial involved: today's behaviour, unchanged.
        ids = self._pair(b_line="l8")
        self.recorded = {i: "accept\n" for i in ids}
        self.check_rows = {"11": "confirm the change by hand (a Check finding)"}
        self._run(ids, max_passes=3)

        self.assertEqual(len([c for c in self.session_calls if "issue_11" in c]), 3,
                         self.session_calls)
        self.assertEqual(state.state(self.cfg.bundle("11")), state.AWAITING_SIGNOFF)
        self.assertIn("pass budget exhausted", self.err)

    # -- (g) the last wave has no fold to mirror ---------------------------------------------

    def test_on_the_last_wave_both_are_accepted_and_published(self):
        self._on_base({"shared.txt": NINE})
        self._plan("10", {"shared.txt": _edit(NINE, l2="ten")})
        self._plan("11", {"shared.txt": _edit(NINE, l2="eleven")})
        ids = ["10", "11"]
        self.recorded = {i: "accept\n" for i in ids}
        self._run(ids)

        self._published("10")
        self._published("11")
        self.assertEqual(self.holds, {}, self.err)
        self.assertEqual(self.rc, 0, self.err)               # as on main: no fold, no hold


class GitWrittenPaths(unittest.TestCase):
    """The paths the shared-path fallback reads from a patch (``waves.diff_footprint``, and
    ``waves.diff_files`` beside it) are the ones git wrote, in every shape a real ``git diff``
    writes them: quoted (a non-ASCII name, a tab, a quote mark), with a space, renamed,
    added, deleted, binary. A patch whose paths cannot all be read is not known — never
    "touches nothing"."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = repo = self.tmp / "repo"
        sb._git(self.tmp, "init", "-q", str(repo))
        sb._identity(repo)
        before = {"café.txt": "a\nb\n", "my file.txt": "1\n2\n", "old name.txt": "keep\n" * 9,
                  "gone.txt": "bye\n", "tab\there.txt": "t\n", 'q"uote.txt': "q\n",
                  "dir/sub.txt": "s\n"}
        for name, text in before.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
        (repo / "bin.dat").write_bytes(bytes(range(256)))
        sb._git(repo, "add", "--all")
        sb._git(repo, "commit", "-q", "-m", "base")
        for name in ("café.txt", "my file.txt", "tab\there.txt", 'q"uote.txt', "dir/sub.txt"):
            (repo / name).write_text("changed\n", encoding="utf-8")
        sb._git(repo, "mv", "old name.txt", "new näme.txt")
        (repo / "neu ü.txt").write_text("new\n", encoding="utf-8")
        (repo / "gone.txt").unlink()
        (repo / "bin.dat").write_bytes(bytes(range(255, -1, -1)))
        sb._git(repo, "add", "--all")
        self.touched = {"café.txt", "my file.txt", "old name.txt", "new näme.txt", "neu ü.txt",
                        "gone.txt", "tab\there.txt", 'q"uote.txt', "dir/sub.txt", "bin.dat"}

    def _patch(self, *config: str) -> Path:
        """The staged change as ``git diff`` writes it — its bytes, whatever the locale."""
        p = self.tmp / "patch.diff"
        p.write_bytes(subprocess.run(["git", "-C", str(self.repo), *config, "diff", "--cached",
                                      "-M"], capture_output=True, check=True).stdout)
        return p

    def _footprint(self, p: Path) -> set[str] | None:
        """``waves.diff_footprint(p)`` — absent before the fix, where this fails on an
        assertion rather than on the missing name."""
        read = getattr(waves, "diff_footprint", None)
        self.assertIsNotNone(read, "waves.diff_footprint is missing")
        return read(p)

    def test_every_path_git_wrote_quoted_is_read(self):
        p = self._patch("-c", "core.quotePath=true")
        text = p.read_text(encoding="utf-8")
        self.assertIn('diff --git "a/caf\\303\\251.txt" "b/caf\\303\\251.txt"', text)
        self.assertIn('diff --git a/old name.txt "b/new n\\303\\244me.txt"', text)
        self.assertIn('"a/tab\\there.txt"', text)
        self.assertEqual(waves.diff_files(p), self.touched)
        self.assertEqual(self._footprint(p), self.touched)

    def test_every_path_git_wrote_unquoted_is_read(self):
        p = self._patch("-c", "core.quotePath=false")
        self.assertIn("diff --git a/café.txt b/café.txt", p.read_text(encoding="utf-8"))
        self.assertEqual(waves.diff_files(p), self.touched)
        self.assertEqual(self._footprint(p), self.touched)

    def test_a_patch_whose_paths_cannot_all_be_read_is_not_known(self):
        p = self.tmp / "patch.diff"
        for text in ("--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n",                 # no git header
                     "@@ -1 +1 @@\n-a\n+b\n",                                   # no file at all
                     'diff --git "a/x\\9" "b/x\\9"\n--- "a/x\\9"\n+++ "b/x\\9"\n',  # bad quote
                     "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,3 +1,3 @@\n-a\n+b\n",  # cut
                     "From: someone\n\nno diff here\n"):
            p.write_text(text, encoding="utf-8")
            self.assertIsNone(self._footprint(p), text)
        p.write_text("", encoding="utf-8")
        self.assertEqual(self._footprint(p), set())          # an empty patch touches nothing


if __name__ == "__main__":
    unittest.main()
