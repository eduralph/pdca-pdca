"""A same-wave conflict is found before the wave publishes (#395).

Since #674 the fold holds the later of two bundles of one wave whose branches conflict, and
the run goes on — but only after both were published, so the wave ends with two draft PRs
that conflict with each other, and the held one's PR is work the human must close or redo.
On a wave the fold runs after (stack mode, not the last wave), the driver now tries the
wave's ready bundles against each other before anything is pushed, with the fold's own
rule, and publishes none it would hold: no branch, no PR. The last wave (and so a one-wave
run) is unchanged. A trial that fails is tried again. A bundle whose would-be commit still
cannot be built is not published, and the rest are tried without it — a bundle whose own
remote (an ``Onto branch``) cannot be fetched among them; where the trial still cannot run
at all, only the first bundle of the wave is published. A later run that finds a bundle held
this way finished — a re-issue's carry, or a re-run that skips it — names the bundles it
conflicts with, never asks for the PR it does not have or tells you to delete it, and gives
the step for those whose PR is not closed — until each of them has its PR closed unmerged;
a re-run exits 3 for it. A held bundle whose earlier publish opened a PR (an iterate keeps
that record) is never said to have none: each such line names that PR, which still shows
the earlier work. A later run that drives the held bundle again and does not hold it drops
that hold.

These cases drive ``flow._drive_and_act`` through real folds — the ``StackFoldGit`` fixture
of tests/test_integrate_stack_bases.py (a bare ``origin`` and a primary checkout), with the
fixture loading and helpers of tests/test_flow_same_wave_conflict.py, loaded by path as
tests/test_flow_reissue_after_conflict_hold.py does. The build and sign-off leaves are
stubbed (the build writes a ``patch.diff`` and the two publish texts, then accepts), and so
is drafting the texts. Publishing is NOT stubbed: the production ``publish.publish`` cuts,
commits and pushes each branch to the bare origin, and its ``gh pr create`` is answered by a
stub in front of ``subprocess.run`` that records every ``gh`` call. The publisher is in
``command`` mode (a stub turns every fold into a dry-run). A push that fails is a real
refusal: a ``pre-receive`` hook on the bare origin. A fetch that fails is
``integrate._fetch`` raising as it does when ``git fetch`` fails, for the first calls of a
run only, or a real ``git fetch`` of a remote the checkout does not have. A git step that
fails in the integration checkout is ``integrate._git`` returning 1 for the calls a case
picks; publish's own git steps never go through it. An ``Onto branch`` on another remote is
a second bare repository the checkout has as a remote. A re-run goes through ``cli._flow``,
the CLI's own route and exit code; an iterate is the production ``driver._archive_iteration``.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_same_wave_prepublish
"""

from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import subprocess
import unittest
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pdca_harness import cli, driver, flow, integrate, publish, state

_SPEC = importlib.util.spec_from_file_location(
    "same_wave_conflict_fixture", Path(__file__).with_name("test_flow_same_wave_conflict.py"))
swc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(swc)
sb = swc.sb                     # the StackFoldGit fixture module, loaded by path there

TODAY = "2026-10-24"
NINE = swc.NINE                 # a nine-line file
_edit = swc._edit
# The step a same-wave conflict between 10 and 11 gets, at the end of a run and on a re-issue.
STEP_11 = ("declare `Conflicts with: 10` in issue_11's brief, then rebuild issue_11 on a base "
           "that holds issue_10")
# The owner of a remote whose bare repository is ``<tmp>/someone/repo.git``, as publish reads
# it from the remote's url (``publish._fork_owner``).
ONTO_OWNER = "someone"


class SameWavePrepublish(unittest.TestCase):
    # The SameWaveConflict fixture and helpers, borrowed method by method: subclassing it
    # would collect and run its own cases again here.
    setUp = swc.SameWaveConflict.setUp
    _on_base = swc.SameWaveConflict._on_base
    _plan = swc.SameWaveConflict._plan
    _patch = swc.SameWaveConflict._patch

    # -- stubs -----------------------------------------------------------------------------

    def _gh_stub(self, args, *a, **kw):
        """Any ``gh`` call is recorded and answered: ``gh pr create`` with a PR url naming
        the branch, ``gh pr list --head <branch>`` (an ``Onto branch`` publish looking up
        the PR it commits onto) with one open PR of that branch, owned by ``ONTO_OWNER``,
        ``gh pr view`` OPEN with that branch's tip on origin as its head (no PR here ever
        merges) — CLOSED for a branch of ``closed_prs``; everything else runs for real —
        what a call does not capture (publish's git steps) goes to /dev/null, not the test
        log."""
        if not (isinstance(args, list) and args[:1] == ["gh"]):
            if not {"capture_output", "stdout", "stderr"} & kw.keys():
                kw = {**kw, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            return self._real_run(args, *a, **kw)
        self.gh_calls.append(list(args))
        if args[:3] == ["gh", "pr", "create"]:
            head = args[args.index("--head") + 1]
            return subprocess.CompletedProcess(
                args, 0, f"https://example.test/pr/{head.split(':', 1)[-1]}\n", "")
        if args[:3] == ["gh", "pr", "list"]:
            head = args[args.index("--head") + 1]
            return subprocess.CompletedProcess(args, 0, json.dumps([{
                "url": f"https://example.test/pr/{head}", "number": 1, "headRefName": head,
                "headRepositoryOwner": {"login": ONTO_OWNER}}]), "")
        branch = str(args[3]).partition("/pr/")[2] if args[:3] == ["gh", "pr", "view"] else ""
        tip = self.fx._tip(branch) if branch and self.fx._has(branch) else ""
        pr = "CLOSED" if branch in self.closed_prs else "OPEN"
        return subprocess.CompletedProcess(
            args, 0, json.dumps({"state": pr, "headRefOid": tip}), "")

    def _drive_wave(self, cfg, wave: list[Path], **_kw) -> int:
        """Build and accept each bundle: its ``patch.diff`` and both publish texts."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            self.built.append(iid)
            (d / "patch.diff").write_text(self._patch(self.changes[iid]), encoding="utf-8")
            (d / publish.COMMIT_MSG).write_text(f"Fix {iid}\n\nRefs #{iid}\n",
                                                encoding="utf-8")
            (d / publish.PR_BODY).write_text(f"**User impact:** fixes {iid}.\n\nRefs #{iid}\n",
                                             encoding="utf-8")
            sb._accept(d)
        return 1

    def _draft_texts(self, cfg, d: Path, **_kw) -> bool:
        """Drafting and T4: they pass, except for an id in ``t4_fails``."""
        return d.name.removeprefix("issue_") not in self.t4_fails

    @contextmanager
    def _stubbed(self) -> Iterator[None]:
        """The stubs of one run, with its stdout and stderr captured (``self.err`` once it
        ends). The first ``fetch_fails`` calls of ``integrate._fetch`` fail, the rest run for
        real. With ``git_fails`` = ``(match, n)``, the first ``n`` calls of ``integrate._git``
        whose args ``match`` accepts (each one, for ``n`` None) exit 1 without running, each
        recorded in ``git_failed``; the rest run for real."""
        self.built: list[str] = []
        self._err, out = io.StringIO(), io.StringIO()
        self.holds: dict[str, str] = {}
        self.git_failed: list[tuple[str, ...]] = []
        real_fetch, real_git = integrate._fetch, integrate._git

        def fetch(*a, **kw):
            if self.fetch_fails:
                self.fetch_fails -= 1
                raise integrate.IntegrationError(
                    "could not fetch origin in the test's checkout (failure injected by the "
                    "test) — the fold cannot see the branches it merges",
                    cause="could not fetch origin (failure injected by the test)")
            return real_fetch(*a, **kw)

        def git(repo, *args):
            if self.git_fails and self.git_fails[1] != 0 and self.git_fails[0](args):
                match, left = self.git_fails
                self.git_fails = (match, None if left is None else left - 1)
                self.git_failed.append(args)
                return 1
            return real_git(repo, *args)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
            stack.enter_context(mock.patch.object(integrate, "_fetch", fetch))
            stack.enter_context(mock.patch.object(integrate, "_git", git))
            stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
            stack.enter_context(mock.patch.object(publish, "draft_texts", self._draft_texts))
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(self._err))
            yield
        self.err = self._err.getvalue()
        self.assertNotIn("Traceback", self.err)

    def _run(self, ids: list[str], drive: list[str] | None = None) -> None:
        """One stack-mode run asked for ``ids``, driving ``drive`` (all of them by default:
        a re-issue drives only the ids it does not skip as finished); publish is real."""
        with self._stubbed():
            self.results = flow._drive_and_act(
                self.cfg, [self.cfg.bundle(i) for i in (ids if drive is None else drive)],
                do_publish=True, do_act=False, by="T", today=TODAY, batch=ids,
                holds=self.holds)
        self.rc = cli._results_rc(self.results, holds=self.holds)

    def _cli(self, ids: list[str]) -> int:
        """``pdca flow <ids…>`` (publishing on, Act off) through ``cli._flow``, with
        :meth:`_stubbed`'s stubs: the CLI's own route, for one id or several (#468), which
        skips each finished id with its hint and prints its exit code's results. ``holds`` is
        the collector ``cli._flow`` hands ``flow.flow_ids``, read off that call (the real one
        runs). Returns the exit code."""
        real_ids = flow.flow_ids

        def flow_ids(*a, **kw):
            self.holds = kw["holds"]
            return real_ids(*a, **kw)

        args = SimpleNamespace(issue_ids=list(ids), from_csv=None, from_briefs=None,
                               no_publish=False, no_act=True, by="T", lanes=None,
                               max_passes=None)
        with self._stubbed(), mock.patch.object(flow, "flow_ids", flow_ids):
            self.rc = cli._flow(self.cfg, args)
        return self.rc

    def _publish_by_hand(self, iid: str) -> None:
        """``pdca publish <iid>``, run by hand between two runs: the production publish,
        drafting and T4 included (no T4 gate is configured here), its PR opened."""
        err = io.StringIO()
        with mock.patch.object(subprocess, "run", self._gh_stub), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = publish.publish(self.cfg, iid, by="T", today=TODAY)
        self.assertEqual(rc, 0, err.getvalue())

    # -- helpers ---------------------------------------------------------------------------

    t4_fails: frozenset[str] = frozenset()
    fetch_fails = 0
    git_fails: tuple[Callable[[tuple[str, ...]], bool], int | None] | None = None
    closed_prs: frozenset[str] = frozenset()     # branches whose PR reads CLOSED

    def _branch(self, iid: str) -> str:
        """The PR branch publish pushes for ``issue_<iid>``."""
        d = self.cfg.bundle(iid)
        return publish._branch_name(self.cfg, d, publish._resolve_target(d)[2])

    def _pr_created(self, iid: str) -> bool:
        """``gh pr create`` was called for ``issue_<iid>``'s branch."""
        return any(c[:3] == ["gh", "pr", "create"]
                   and c[c.index("--head") + 1].endswith(":" + self._branch(iid))
                   for c in self.gh_calls)

    def _published(self, iid: str) -> None:
        """``issue_<iid>``'s branch is on origin and its PR was opened."""
        self.assertTrue(self.fx._has(self._branch(iid)), (iid, self.err))
        self.assertTrue(self._pr_created(iid), (iid, self.gh_calls))

    def _not_published(self, iid: str) -> None:
        """No branch of ``issue_<iid>`` reached origin and no PR was opened for it."""
        self.assertFalse(self.fx._has(self._branch(iid)), (iid, self.err))
        self.assertFalse(self._pr_created(iid), (iid, self.gh_calls))

    def _held_lines(self, iid: str) -> list[str]:
        """The stderr lines saying ``issue_<iid>`` was held for a conflict."""
        return [x for x in self.err.splitlines()
                if x.startswith(f"flow: issue_{iid} held out of the integration fold")]

    def _lines(self, start: str) -> list[str]:
        """The stderr lines of the last run that start with ``start``."""
        return [x for x in self.err.splitlines() if x.startswith(start)]

    def _refuse_pushes(self, branch: str) -> None:
        """Origin refuses every push to ``branch`` (a ``pre-receive`` hook)."""
        hook = self.fx.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nwhile read old new ref; do\n"
                        f'  [ "$ref" = "refs/heads/{branch}" ] && '
                        '{ echo "refused by the test" >&2; exit 1; }\n'
                        "done\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)

    def _onto(self, iid: str, onto: str) -> None:
        """``issue_<iid>``'s brief names ``- **Onto branch:** <onto>`` (#54): publish commits
        onto that PR branch, on the remote ``onto`` names, and the trial builds it there."""
        bp = self.cfg.bundle(iid) / "brief.md"
        bp.write_text(bp.read_text(encoding="utf-8") + f"- **Onto branch:** {onto}\n",
                      encoding="utf-8")

    def _pair(self, ten: dict[str, str], eleven: dict[str, str]) -> list[str]:
        """``10`` and ``11`` (``ten`` / ``eleven``: their files) and ``12`` (a file of its
        own) in wave 0, with no ``Conflicts with`` between them; ``20`` depends on ``12``
        alone, so it is wave 1 and the fold runs after wave 0. Returns the ids."""
        self._plan("10", ten)
        self._plan("11", eleven)
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        return ["10", "11", "12", "20"]

    def _held_11_with_20_on_it(self, *, refuse: str | None = None) -> list[str]:
        """Run 1: 10 and 11 change the same line of ``shared.txt`` in wave 0, beside 12;
        20 depends on 11, so wave 1 waits on it. 11 is held before it is published, and 20
        is never built. ``refuse``: an id whose pushes origin refuses in this run. Returns
        the ids."""
        self._on_base({"shared.txt": "x\n"})
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("11", {"shared.txt": "eleven\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "11")
        ids = ["10", "11", "12", "20"]
        if refuse:
            self._refuse_pushes(self._branch(refuse))
        self._run(ids)
        self._not_published("11")
        self.assertEqual(self.results["20"], state.PLANNED, self.err)
        end = self._lines("flow: issue_11 was held out of this run's integration line")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn(STEP_11, end[0])
        return ids

    def _not_carried(self, iid: str) -> str:
        """The ONE stderr line of the last run saying finished ``issue_<iid>`` is not
        carried."""
        said = [x for x in self.err.splitlines()
                if f"issue_{iid} (finished in an earlier run) is not carried" in x]
        self.assertEqual(len(said), 1, self.err)
        return said[0]

    def _hint(self, iid: str) -> str:
        """The hint the last run printed under its ONE skip of finished ``issue_<iid>``."""
        lines = self.err.splitlines()
        at = [n for n, x in enumerate(lines)
              if x == f"flow: issue_{iid} — already terminal (COMPLETE), skipped"]
        self.assertEqual(len(at), 1, self.err)
        self.assertLess(at[0] + 1, len(lines), self.err)
        return lines[at[0] + 1].strip()

    # -- (a) a same-wave conflict holds the later bundle BEFORE it is published -------------

    def test_a_same_wave_conflict_is_held_before_it_is_published(self):
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self._run(ids)

        self._published("10")
        self._not_published("11")
        self._published("12")
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        # Named with its partner and the file, and the step at the end of the run.
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's, ahead of it in the same wave 0", held[0])
        self.assertIn("shared.txt", held[0])
        self.assertIn("no branch pushed, no PR opened", held[0])
        end = self._lines("flow: issue_11 was held out of this run's integration line")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("`Conflicts with: 10`", end[0])
        self.assertIn("rebuild issue_11 on a base that holds issue_10", end[0])
        self.assertNotIn("issue_11 pushed no branch", self.err)    # a conflict hold only
        line = integrate.integration_branch(self.cfg, "main", ids)   # 10's change, not 11's
        self.assertEqual(self.fx._show(self.fx._tip(line), "shared.txt"), "ten\n")
        # A later bundle that depends on neither still builds, and publishes.
        self.assertIn("20", self.built)
        self.assertEqual(self.results["20"], state.COMPLETE, self.err)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_same_wave_conflict_in_a_later_wave_is_held_before_it_is_published(self):
        # 20 and 21 both depend on 10, so wave 1 builds each on a base of its own holding 10
        # (#727), and publish cuts each branch from that base's tip — so does the trial; 30
        # depends on 20, so a fold follows wave 1. 20 and 21 change the same line: 21 is
        # held before it is published, as in wave 0, and 30 is built.
        self._on_base({"shared.txt": "x\n"})
        self._plan("10", {"ten.txt": "ten\n"})
        self._plan("20", {"shared.txt": "twenty\n"}, "10")
        self._plan("21", {"shared.txt": "twenty-one\n"}, "10")
        self._plan("30", {"thirty.txt": "thirty\n"}, "20")
        ids = ["10", "20", "21", "30"]
        self._run(ids)

        d20 = self.cfg.bundle("20")
        self.assertEqual(publish.read_stack_base(d20),
                         integrate.bundle_base_branch(self.cfg, "main", ids, "issue_20"))
        self.assertEqual(json.loads((d20 / "publish.json").read_text(encoding="utf-8"))
                         ["cut_from"], publish.read_stack_base_tip(d20))
        for iid in ("10", "20", "30"):
            self._published(iid)
        self._not_published("21")
        self.assertEqual(self.holds, {"21": "conflict"}, self.err)
        held = self._held_lines("21")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_20's, ahead of it in the same wave 1", held[0])
        self.assertIn("shared.txt", held[0])
        self.assertEqual(self.rc, 3, self.err)

    # -- (b) a shared file that merges cleanly holds nothing --------------------------------

    def test_a_shared_file_on_different_lines_publishes_both(self):
        self._on_base({"shared.txt": NINE})
        ids = self._pair({"shared.txt": _edit(NINE, l2="ten")},
                         {"shared.txt": _edit(NINE, l8="eleven")})
        self._run(ids)

        for iid in ids:
            self._published(iid)
        self.assertEqual(self.holds, {}, self.err)
        self.assertEqual(self._held_lines("10") + self._held_lines("11"), [])
        self.assertEqual(self.rc, 0, self.err)

    # -- (c) a conflict only with work already on the line is the fold's (#747) ------------

    def test_a_conflict_with_work_on_the_line_still_publishes_and_the_fold_holds_it(self):
        # 21 depends on 12 only, so it is built on a base without 10 (#727), but 10 is on the
        # line from wave 0: its clash is with 10, not with 22, its wave's other bundle. The
        # trial leaves it to the fold, which holds it (#747), as it did before #395.
        self._on_base({"shared.txt": "x\n"})
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("21", {"shared.txt": "twenty-one\n"}, "12")
        self._plan("22", {"twenty-two.txt": "twenty-two\n"}, "12")
        self._plan("30", {"thirty.txt": "thirty\n"}, "22")
        ids = ["10", "12", "21", "22", "30"]
        self._run(ids)

        self._published("21")
        self.assertEqual(self.holds, {"21": "conflict"}, self.err)
        held = self._held_lines("21")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("issue_10's, already on the line from an earlier wave", held[0])
        self.assertNotIn("Found before publishing", held[0])
        for iid in ("10", "12", "22", "30"):
            self._published(iid)
        self.assertNotIn("STOPPING", self.err)
        self.assertEqual(self.rc, 3, self.err)

    # -- (d) only bundles whose texts passed draft + T4 are tried --------------------------

    def test_a_partner_whose_texts_failed_t4_holds_nothing(self):
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self.t4_fails = frozenset({"10"})
        self._run(ids)

        self._not_published("10")
        self._published("11")
        self.assertEqual(self.holds, {"10": "unpushed"}, self.err)
        self.assertEqual(self._held_lines("11"), [])

    # -- (e) a hold stands when its partner's push then fails -------------------------------

    def test_a_hold_stands_when_the_partners_push_fails(self):
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self._refuse_pushes(self._branch("10"))
        self._run(ids)

        self.assertFalse(self.fx._has(self._branch("10")), self.err)   # the push failed
        self._not_published("11")
        self.assertEqual(self.holds, {"10": "unpushed", "11": "conflict"}, self.err)
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's", held[0])
        self.assertNotIn("issue_11 pushed no branch", self.err)
        self.assertIn("issue_10 pushed no branch", self.err)
        self._published("12")
        self._published("20")

    # -- (f) the last wave is unchanged -----------------------------------------------------

    def test_a_same_wave_conflict_in_the_last_wave_publishes_both(self):
        # 20 and 21 are wave 1, the run's last: no fold runs after it, so no trial either.
        self._on_base({"shared.txt": "x\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"shared.txt": "twenty\n"}, "12")
        self._plan("21", {"shared.txt": "twenty-one\n"}, "12")
        ids = ["12", "20", "21"]
        self._run(ids)

        for iid in ids:
            self._published(iid)
        self.assertEqual(self.holds, {}, self.err)
        self.assertEqual(self._held_lines("21"), [])
        self.assertEqual(self.rc, 0, self.err)

    def test_a_same_wave_conflict_in_a_one_wave_run_publishes_both(self):
        self._on_base({"shared.txt": "x\n"})
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("11", {"shared.txt": "eleven\n"})
        self._run(["10", "11"])

        self._published("10")
        self._published("11")
        self.assertEqual(self.holds, {}, self.err)
        self.assertEqual(self._held_lines("11"), [])
        self.assertEqual(self.rc, 0, self.err)

    # -- a trial that fails is tried again; a bundle it still cannot try is not published --

    def test_a_trial_whose_fetch_fails_once_tries_again_and_still_holds(self):
        # The run's first fetch — the trial's — fails, as a fetch racing another git
        # process in the same checkout can (#695). The trial tries again and gets past it,
        # so 11 is still held before it is published. Every later fetch runs for real, the
        # fold's included.
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self.fetch_fails = 1
        self._run(ids)

        self._published("10")
        self._not_published("11")
        self._published("12")
        self.assertEqual(self.fetch_fails, 0)        # the failure was injected
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's", held[0])
        self.assertNotIn("STOPPING", self.err)
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_trial_that_cannot_run_publishes_only_the_first_bundle_of_the_wave(self):
        # Both of the trial's fetches fail; the fold's, after the wave publishes, does not.
        # The run cannot tell whether 11 conflicts with 10, so it publishes 10 alone — no
        # sibling can hold the first of a wave — and holds 11 as unpushed (no branch, no
        # PR), naming what failed. The fold then folds 10, and 20, built on it, runs.
        self._on_base({"shared.txt": "x\n"})
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("11", {"shared.txt": "eleven\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "10")
        ids = ["10", "11", "20"]
        self.fetch_fails = 2
        self._run(ids)

        self._published("10")
        self._not_published("11")
        self.assertEqual(self.fetch_fails, 0)        # both failures were injected
        self.assertEqual(self.holds, {"11": "unpushed"}, self.err)
        why = self._lines("flow: issue_11 is not published this run")
        self.assertEqual(len(why), 1, self.err)
        self.assertIn("could not be tried against issue_10's, of wave 0", why[0])
        self.assertIn("failure injected by the test", why[0])
        self.assertIn("`pdca publish 11`", why[0])
        self.assertNotIn("issue_11 pushed no branch", self.err)    # named once, not twice
        self.assertEqual(self._held_lines("11"), [])               # no conflict was found
        self.assertNotIn("STOPPING", self.err)
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_trial_commit_whose_staging_fails_once_is_built_again_and_still_holds(self):
        # The trial's first `git add --all` — staging 10's would-be commit in the
        # integration checkout — fails once. 10 must not drop out of the trial: 11 would
        # then be tried without it, and published beside it. The trial tries again, builds
        # 10's commit, and holds 11. Publish's own `git add` never goes through this hook.
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self.git_fails = (lambda args: args[:2] == ("add", "--all"), 1)
        self._run(ids)

        self._published("10")
        self._not_published("11")
        self._published("12")
        self.assertEqual(len(self.git_failed), 1, self.err)       # the failure was injected
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's, ahead of it in the same wave 0", held[0])
        self.assertIn("shared.txt", held[0])
        self.assertNotIn("is not published this run", self.err)
        self.assertNotIn("STOPPING", self.err)
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_bundle_whose_trial_commit_cannot_be_built_is_not_published_beside_the_rest(self):
        # Each trial commit of 11 fails, on both tries. The run cannot tell whether 11
        # conflicts with 10 or 12, so it publishes 11 beside neither: no branch, no PR, held
        # as unpushed and named with what failed. 10 and 12 are tried without it, and both
        # are published — the rest of the wave is not held for one bundle's commit — and 20,
        # built on 12, runs.
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self.git_fails = (lambda args: args[:1] == ("commit",)
                          and "pdca-integrate: trial commit of issue_11" in args, None)
        self._run(ids)

        self._published("10")
        self._not_published("11")
        self._published("12")
        self.assertEqual(len(self.git_failed), 2, self.err)       # injected, once on each try
        self.assertEqual(self.holds, {"11": "unpushed"}, self.err)
        why = self._lines("flow: issue_11 is not published this run")
        self.assertEqual(len(why), 1, self.err)
        self.assertIn("could not be tried against issue_10's, issue_12's, of wave 0", why[0])
        self.assertIn("issue_11's would-be commit could not be built", why[0])
        self.assertIn("`git commit` failed", why[0])
        self.assertIn("`pdca publish 11`", why[0])
        self.assertNotIn("issue_11 pushed no branch", self.err)    # named once, not twice
        self.assertEqual(self._lines("flow: issue_10 is not published")
                         + self._lines("flow: issue_12 is not published"), [], self.err)
        self.assertEqual(self._held_lines("11"), [])               # no conflict was found
        self.assertNotIn("STOPPING", self.err)
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_bundle_onto_a_branch_of_another_remote_is_tried_there_and_held(self):
        # 12 commits onto `pr-12`, an open PR's branch on another remote (`Onto branch:
        # fork/pr-12`, #54), and changes the line of `shared.txt` that 10 changes. The trial
        # fetches that remote for 12, as publish does — this checkout never fetched it
        # before — builds 12's commit on pr-12, and holds it for 10: nothing is pushed onto
        # pr-12. 20, depending on 10, is built.
        self._on_base({"shared.txt": "x\n"})
        fork = self.fx.tmp / ONTO_OWNER / "repo.git"
        fork.parent.mkdir()
        subprocess.run(["git", "clone", "-q", "--bare", str(self.fx.origin), str(fork)],
                       check=True, capture_output=True)
        pr12 = self.fx._push_from_human({"pr-12.txt": "pr 12\n"}, to="pr-12", url=str(fork))
        sb._git(self.fx.primary, "remote", "add", "fork", str(fork))
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("12", {"shared.txt": "twelve\n"})
        self._onto("12", "fork/pr-12")
        self._plan("20", {"twenty.txt": "twenty\n"}, "10")
        self._run(["10", "12", "20"])

        self._published("10")
        self.assertEqual(sb._git(fork, "rev-parse", "refs/heads/pr-12").strip(), pr12,
                         self.err)                         # no commit pushed onto pr-12
        self.assertEqual(self.holds, {"12": "conflict"}, self.err)
        held = self._held_lines("12")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's, ahead of it in the same wave 0", held[0])
        self.assertIn("shared.txt", held[0])
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_bundle_whose_own_remote_cannot_be_fetched_is_held_alone(self):
        # 12 commits onto a PR branch of a remote this checkout does not have (`Onto branch:
        # nosuch/pr-12`, #54); 10 and 11 beside it have files of their own, and 20 depends on
        # 11. The trial fetches that remote for 12 alone, as publish does: it cannot, so 12's
        # commit cannot be built and 12 is not published (publish would refuse it too). 10
        # and 11 are tried without it, both are published, and 20 is built on 11.
        self._on_base({"shared.txt": "x\n"})
        self._plan("10", {"ten.txt": "ten\n"})
        self._plan("11", {"eleven.txt": "eleven\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._onto("12", "nosuch/pr-12")
        self._plan("20", {"twenty.txt": "twenty\n"}, "11")
        self._run(["10", "11", "12", "20"])

        self._published("10")
        self._published("11")
        self.assertEqual(self.holds, {"12": "unpushed"}, self.err)
        why = self._lines("flow: issue_12 is not published this run")
        self.assertEqual(len(why), 1, self.err)
        self.assertIn("could not be tried against issue_10's, issue_11's, of wave 0", why[0])
        self.assertIn("could not fetch nosuch", why[0])
        self.assertNotIn("has no 'nosuch' remote", self.err)      # publish never ran for it
        self.assertEqual(self._lines("flow: issue_10 is not published")
                         + self._lines("flow: issue_11 is not published"), [], self.err)
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    def test_a_first_bundle_whose_own_remote_cannot_be_fetched_still_lets_the_rest_be_tried(
            self):
        # As above, but the bundle onto a remote this checkout lacks sorts first (09), and 10
        # and 11 change the same line. 09 is held alone; 10 and 11 are tried without it, so
        # 10 is published and 11 is held for its conflict with 10, as with no 09. 20,
        # depending on 10, is built.
        self._on_base({"shared.txt": "x\n"})
        self._plan("09", {"nine.txt": "nine\n"})
        self._onto("09", "nosuch/pr-9")
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("11", {"shared.txt": "eleven\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "10")
        self._run(["09", "10", "11", "20"])

        self._published("10")
        self._not_published("11")
        self.assertEqual(self.holds, {"09": "unpushed", "11": "conflict"}, self.err)
        why = self._lines("flow: issue_09 is not published this run")
        self.assertEqual(len(why), 1, self.err)
        self.assertIn("could not be tried against issue_10's, of wave 0", why[0])
        self.assertIn("could not fetch nosuch", why[0])
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's, ahead of it in the same wave 0", held[0])
        self.assertIn("20", self.built)
        self._published("20")
        self.assertEqual(self.rc, 3, self.err)

    # -- a re-issue after a trial hold names the partners while one of them may land -------

    def test_a_reissue_after_a_trial_hold_names_the_partner_and_opens_no_pr(self):
        # Re-issued, the run skips the finished ids and its carry judges them for 20. 11
        # has no PR, and asking for one (`pdca publish 11`) would open the PR that
        # conflicts with 10's: it is named with 10, the file and run 1's step instead.
        ids = self._held_11_with_20_on_it()
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn("an earlier run held it before publishing it, as its change conflicts "
                      "with issue_10's, of its own wave (shared.txt), so it has no PR", said)
        self.assertIn(f"proposed, for you to confirm: {STEP_11}, then re-issue", said)
        self.assertIn("holding issue_20 this run", said)
        for wrong in ("get issue_11's PR open", "pdca publish 11", "issue_12"):
            self.assertNotIn(wrong, said)
        self._not_published("11")             # neither run pushed it or opened its PR
        self.assertNotIn("20", self.built)
        self.assertEqual(self.results["20"], state.PLANNED, self.err)
        carried = self._lines("flow: carried ")
        self.assertEqual(len(carried), 1, self.err)
        self.assertIn("issue_10, issue_12 (finished", carried[0])

    def test_a_trial_hold_published_by_hand_is_judged_by_its_pr(self):
        # After run 1, 11 is published by hand anyway. Its branch is pushed, so the hold no
        # longer stands: the re-issue's carry judges its PR as for any finished id, and its
        # fold finds the conflict with 10 (#694) — no word of a hold before publishing.
        ids = self._held_11_with_20_on_it()
        self._publish_by_hand("11")
        self._published("11")
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn(f"its branch origin/{self._branch('11')} does not merge cleanly onto the "
                      f"line — its change conflicts with issue_10's (shared.txt), finished "
                      f"in this batch", said)
        self.assertIn(f"proposed, for you to confirm: {STEP_11}, then re-issue", said)
        self.assertNotIn("before publishing", said)
        self.assertEqual(self.results["20"], state.PLANNED, self.err)

    def test_a_reissue_once_the_partners_pr_closed_asks_to_publish_the_held_bundle(self):
        # After run 1, 10's PR is closed without merging, so 10 does not land and 11's hold
        # keeps no two PRs apart any more. The re-issue's carry says so and asks for 11's PR
        # (`pdca publish 11`), the step that unblocks 20 — not a rebuild on a base that
        # holds 10, which no base will.
        ids = self._held_11_with_20_on_it()
        self.closed_prs = frozenset({self._branch("10")})
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn("an earlier run held it before publishing it, as its change conflicts "
                      "with issue_10's, of its own wave (shared.txt), but that PR is closed "
                      "unmerged now, so that hold no longer stands; it has no PR", said)
        self.assertIn("get issue_11's PR open with its branch on origin (re-open it, `pdca "
                      "publish 11`, or re-drive issue_11), then re-issue", said)
        self.assertIn("holding issue_20 this run", said)
        self.assertNotIn(STEP_11, said)
        self._not_carried("10")      # its PR is closed (the line it is on is named there)
        self._not_published("11")             # the carry publishes nothing itself
        self.assertNotIn("20", self.built)
        self.assertEqual(self.results["20"], state.PLANNED, self.err)

    def test_a_reissue_keeps_the_hold_while_one_of_its_partners_may_land(self):
        # 13 changes line 2, as 10 does, and line 8, as 12 does: it is held for both, ahead
        # of it in wave 0. 10's PR then closes unmerged, and the line, which holds 10's work,
        # is deleted, as the carry asks for a line holding work no PR of the batch lands.
        # 12's PR is still open, and 13's PR would conflict with it: the re-issue keeps the
        # hold, for 12 alone. Its step names 12 only — no base will hold 10, and a
        # `Conflicts with` edge to it orders nothing — and the carry puts 12 on the line.
        self._on_base({"shared.txt": NINE})
        self._plan("10", {"shared.txt": _edit(NINE, l2="ten")})
        self._plan("12", {"shared.txt": _edit(NINE, l8="twelve")})
        self._plan("13", {"shared.txt": _edit(NINE, l2="thirteen", l8="thirteen")})
        self._plan("20", {"twenty.txt": "twenty\n"}, "13")
        ids = ["10", "12", "13", "20"]
        self._run(ids)
        self._not_published("13")
        held = self._held_lines("13")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("conflicts with issue_10's, issue_12's, ahead of it in the same wave 0",
                      held[0])
        self.closed_prs = frozenset({self._branch("10")})
        self.fx._delete(integrate.integration_branch(self.cfg, "main", ids))
        self._run(ids, drive=["20"])

        said = self._not_carried("13")
        self.assertIn("an earlier run held it before publishing it, as its change conflicts "
                      "with issue_10's, issue_12's, of its own wave (shared.txt); issue_10's "
                      "PR is closed unmerged now, but issue_12's may still land, so it has no "
                      "PR", said)
        self.assertIn("proposed, for you to confirm: declare `Conflicts with: 12` in "
                      "issue_13's brief, then rebuild issue_13 on a base that holds issue_12, "
                      "then re-issue", said)
        for wrong in ("Conflicts with: 10", "holds issue_10", "pdca publish 13"):
            self.assertNotIn(wrong, said)
        carried = self._lines("flow: carried ")
        self.assertEqual(len(carried), 1, self.err)
        self.assertIn("carried issue_12 (finished", carried[0])
        self._not_published("13")
        self.assertEqual(self.results["20"], state.PLANNED, self.err)

    def test_a_reissue_while_the_partner_has_no_pr_keeps_the_hold(self):
        # 10's push failed in run 1, so it has no PR — but it is still accepted work, to be
        # published, and 11's PR would conflict with its. The re-issue keeps 11's hold and
        # its step, and asks for 10's PR, never for 11's.
        ids = self._held_11_with_20_on_it(refuse="10")
        self.assertEqual(self.holds, {"10": "unpushed", "11": "conflict"}, self.err)
        (self.fx.origin / "hooks" / "pre-receive").unlink()        # origin takes pushes again
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn("an earlier run held it before publishing it, as its change conflicts "
                      "with issue_10's, of its own wave (shared.txt), so it has no PR", said)
        self.assertIn(f"proposed, for you to confirm: {STEP_11}, then re-issue", said)
        self.assertNotIn("pdca publish 11", said)
        self.assertIn("`pdca publish 10`", self._not_carried("10"))
        self._not_published("10")
        self._not_published("11")
        self.assertEqual(self.results["20"], state.PLANNED, self.err)

    # -- a later run that reaches the held bundle's publish and does not hold it -----------

    def _redrive_11(self) -> None:
        """Between runs, 11's sign-off is cleared by hand (it is to be given again), so the
        next run drives 11 again: the one way an attempt held before publishing reaches a
        later run's publish — an iterate archives its hold with the attempt."""
        (self.cfg.bundle("11") / "SUMMARY.md").unlink()

    def test_a_later_run_whose_texts_fail_t4_drops_the_hold(self):
        # Run 1 holds 11 before publishing it. Run 2 drives 11 again, alone, and its texts
        # fail T4 there: it is not published, and run 2 holds it for no conflict — it asks
        # for `pdca publish 11`. That is 11's latest word, so run 3, a re-issue, asks for
        # 11's PR, as for any finished id with no PR, and no longer gives run 1's hold.
        ids = self._held_11_with_20_on_it()
        self._redrive_11()
        self.t4_fails = frozenset({"11"})
        self._run(ids, drive=["11", "20"])
        self._not_published("11")
        self.assertEqual(len(self._lines("flow: issue_11 — publish texts not ready")), 1,
                         self.err)
        self.t4_fails = frozenset()
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn("no PR with a pushed branch on record (publish.json)", said)
        self.assertIn("`pdca publish 11`", said)
        self.assertNotIn("before publishing", said)
        self.assertNotIn(STEP_11, said)
        self.assertEqual(self.results["20"], state.PLANNED, self.err)

    def test_a_later_run_whose_push_fails_drops_the_hold(self):
        # As above, but in run 2 11 is ready: alone in its wave, it is held for nothing, and
        # publish pushes it — origin refuses the push. Run 3 does not bring run 1's hold back.
        ids = self._held_11_with_20_on_it()
        self._redrive_11()
        self._refuse_pushes(self._branch("11"))
        self._run(ids, drive=["11", "20"])
        self._not_published("11")
        self.assertEqual(self.holds, {"11": "unpushed"}, self.err)
        self.assertEqual(len(self._lines("flow: issue_11 pushed no branch this run")), 1,
                         self.err)
        (self.fx.origin / "hooks" / "pre-receive").unlink()        # origin takes pushes again
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn("no PR with a pushed branch on record (publish.json)", said)
        self.assertNotIn("before publishing", said)
        self.assertNotIn(STEP_11, said)

    def test_a_dry_run_keeps_the_hold(self):
        # A rehearsal (the stub publisher) that drives 11 again pushes and decides nothing:
        # the re-issue after it still gives run 1's hold.
        ids = self._held_11_with_20_on_it()
        self._redrive_11()
        real = self.cfg.publisher
        self.cfg.publisher = dataclasses.replace(real, mode="stub")
        self._run(ids, drive=["11", "20"])
        self.cfg.publisher = real
        self._run(ids, drive=["20"])

        said = self._not_carried("11")
        self.assertIn("an earlier run held it before publishing it, as its change conflicts "
                      "with issue_10's, of its own wave (shared.txt), so it has no PR", said)
        self.assertIn(f"proposed, for you to confirm: {STEP_11}, then re-issue", said)

    # -- a re-run that finds the held bundle finished gives its hold, never `rm -rf` -------

    def test_a_rerun_after_a_trial_hold_gives_the_holds_step_and_exits_3(self):
        # Run 1 holds 11 before publishing it; 20 depends on 12, so every other id finishes.
        # The same ids are asked for again (`pdca flow 10 11 12 20`), then 11 alone (`pdca
        # flow 11`): each id is finished, so skipped. 11 is accepted work with no PR, so it
        # is not "already complete — nothing to run", and `rm -rf` would throw that work
        # away: it gets its hold's step instead, both ways (#468), and the run exits 3, as
        # run 1 did. The other ids keep the plain hint. Once 11 is published by hand it is
        # held no more, and a re-run is clean.
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self._run(ids)
        self._not_published("11")
        self.assertEqual(self.results["20"], state.COMPLETE, self.err)
        self.assertEqual(self.rc, 3, self.err)
        held = ("An earlier run held it before publishing it, as its change conflicts with "
                "issue_10's, of its own wave (shared.txt), so it has no PR. Proposed, for you "
                f"to confirm: {STEP_11}, then re-issue.")

        self.assertEqual(self._cli(ids), 3, self.err)
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        self.assertEqual(self._hint("11"), held)
        for iid in ("10", "12", "20"):
            self.assertEqual(self._hint(iid), "already complete — nothing to run. To redo "
                                              f"it: rm -rf {self.cfg.bundle(iid)}")
        self.assertNotIn(f"rm -rf {self.cfg.bundle('11')}", self.err)
        self.assertEqual(self._cli(["11"]), 3, self.err)
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        self.assertEqual(self._hint("11"), held)
        self.assertNotIn("rm -rf", self.err)
        self._not_published("11")             # neither re-run pushed it or opened its PR

        self._publish_by_hand("11")
        self.assertEqual(self._cli(ids), 0, self.err)
        self.assertEqual(self.holds, {}, self.err)
        self.assertEqual(self._hint("11"), "already complete — nothing to run. To redo it: "
                                           f"rm -rf {self.cfg.bundle('11')}")

    def test_a_rerun_once_the_partners_pr_closed_asks_to_publish_the_held_bundle(self):
        # After run 1, 10's PR is closed unmerged: 11's hold keeps no two PRs apart any more,
        # but 11 still has no PR. A re-run says so and asks for that PR — not a rebuild on a
        # base that holds 10, which no base will, and never `rm -rf` — and still exits 3,
        # 11 held as a bundle that pushed no branch.
        self._on_base({"shared.txt": "x\n"})
        ids = self._pair({"shared.txt": "ten\n"}, {"shared.txt": "eleven\n"})
        self._run(ids)
        self._not_published("11")
        self.closed_prs = frozenset({self._branch("10")})

        self.assertEqual(self._cli(ids), 3, self.err)
        self.assertEqual(self.holds, {"11": "unpushed"}, self.err)
        self.assertEqual(self._hint("11"), (
            "An earlier run held it before publishing it, as its change conflicts with "
            "issue_10's, of its own wave (shared.txt), but that PR is closed unmerged now, so "
            "that hold no longer stands; it has no PR. Get issue_11's PR open with its branch "
            "on origin (re-open it, `pdca publish 11`, or re-drive issue_11), then re-issue."))
        self.assertNotIn(f"rm -rf {self.cfg.bundle('11')}", self.err)
        self._not_published("11")

    # -- a held bundle that an earlier publish gave a PR names that PR ----------------------

    def _published_then_iterated_11(self) -> tuple[str, str]:
        """Run 1 publishes 11 alone (``eleven-v1``), its PR open. 11 is then iterated: its
        attempt archived as ``pdca signoff 11 --iterate-do`` archives it — ``publish.json``
        outlives that, so it still names the PR — and rebuilt as ``eleven-v2``. Returns (its
        PR, v1's commit on that PR's branch)."""
        self._on_base({"shared.txt": "x\n"})
        self._plan("11", {"shared.txt": "eleven-v1\n"})
        self._run(["11"])
        self._published("11")
        d11 = self.cfg.bundle("11")
        pr = json.loads((d11 / "publish.json").read_text(encoding="utf-8"))["pr_url"]
        v1 = self.fx._tip(self._branch("11"))
        driver._archive_iteration(d11, 1, include_brief=False)
        self.assertEqual(state.state(d11), state.PLANNED)
        self.changes["11"] = {"shared.txt": "eleven-v2\n"}
        self.gh_calls.clear()
        return pr, v1

    def test_a_held_bundle_whose_earlier_publish_opened_a_pr_names_that_pr(self):
        # Run 2 drives the rebuilt 11 beside 10, which changes the same line: held before it
        # is published, 11 pushes nothing onto its PR, which still shows v1. Each line that
        # says the run published nothing for it names that PR, and so does run 3, which asks
        # for the same ids again — its skip of 11 and its carry for 20, which depends on 11:
        # never "no PR".
        pr, v1 = self._published_then_iterated_11()
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "11")
        ids = ["10", "11", "12", "20"]
        self._run(ids)

        self.assertEqual(self.fx._tip(self._branch("11")), v1, self.err)   # nothing pushed
        self.assertFalse(self._pr_created("11"), self.gh_calls)
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        earlier = (f"its PR on record, {pr}, still shows what an earlier publish of it pushed "
                   f"(close it if it is open, or leave it until issue_11 is published again)")
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn(f"Found before publishing: no branch pushed, no PR opened; {earlier}.",
                      held[0])
        end = self._lines("flow: issue_11 was held out of this run's integration line")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn(f"this run pushed no branch and opened no PR for it; {earlier}.", end[0])

        self.assertEqual(self._cli(ids), 1, self.err)          # 20 is left unbuilt
        for line in (self._hint("11"), self._not_carried("11")):
            self.assertIn(f"of its own wave (shared.txt), so {earlier}", line)
            self.assertIn(STEP_11, line)
            self.assertNotIn("no PR", line)
            self.assertNotIn("rm -rf", line)
        self.assertNotIn("20", self.built)
        self.assertEqual(self.fx._tip(self._branch("11")), v1, self.err)

    def test_a_bundle_the_trial_could_not_try_names_its_earlier_pr(self):
        # The same rebuilt 11, but each of its trial commits fails, so it could not be tried
        # against 10 and 12: not published, and its line names the PR v1 is still on. Its
        # step is to publish 11, which updates that PR, so no more is said about it.
        pr, v1 = self._published_then_iterated_11()
        self._plan("10", {"ten.txt": "ten\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        self.git_fails = (lambda args: args[:1] == ("commit",)
                          and "pdca-integrate: trial commit of issue_11" in args, None)
        self._run(["10", "11", "12", "20"])

        self.assertEqual(self.fx._tip(self._branch("11")), v1, self.err)
        self.assertEqual(self.holds, {"11": "unpushed"}, self.err)
        why = self._lines("flow: issue_11 is not published this run")
        self.assertEqual(len(why), 1, self.err)
        self.assertIn("publish it (`pdca publish 11`). Until then, its PR on record, "
                      f"{pr}, still shows what an earlier publish of it pushed.", why[0])

    def test_a_held_bundle_whose_branch_was_renamed_is_not_told_its_pr_will_update(self):
        # The rebuilt 11 is held for 10, but its brief was revised too (an iterate-plan) and
        # that renamed its branch: publishing it again opens a new PR, so the one on record
        # is not said to be updated then — only to be closed, and why.
        pr, _v1 = self._published_then_iterated_11()
        bp = self.cfg.bundle("11") / "brief.md"
        bp.write_text(bp.read_text(encoding="utf-8").replace("- **Slug:** 11",
                                                             "- **Slug:** eleven"),
                      encoding="utf-8")
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        self._run(["10", "11", "12", "20"])

        self.assertNotIn(self._branch("11"), pr)        # publish would push another branch
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn(f"its PR on record, {pr}, still shows what an earlier publish of it "
                      f"pushed (close it if it is open: publishing issue_11 again opens a new "
                      f"PR).", held[0])
        self.assertNotIn("leave it", held[0])

    def test_a_held_bundle_whose_partners_pr_closed_is_asked_to_publish_onto_its_pr(self):
        # The rebuilt 11 is held for 10 (20 depends on 12, so every other id finishes). 10's
        # PR then closes unmerged, so the hold no longer stands, and the step is to publish
        # 11 — which pushes the new work onto its PR: a re-run names that PR, without the
        # advice to close it.
        pr, v1 = self._published_then_iterated_11()
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("12", {"twelve.txt": "twelve\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "12")
        ids = ["10", "11", "12", "20"]
        self._run(ids)
        self.assertEqual(self.holds, {"11": "conflict"}, self.err)
        self.closed_prs = frozenset({self._branch("10")})

        self.assertEqual(self._cli(ids), 3, self.err)
        self.assertEqual(self.holds, {"11": "unpushed"}, self.err)
        hint = self._hint("11")
        self.assertIn(f"so that hold no longer stands; its PR on record, {pr}, still shows "
                      f"what an earlier publish of it pushed. Get issue_11's PR open", hint)
        self.assertIn("`pdca publish 11`", hint)
        self.assertNotIn("close it", hint)
        self.assertEqual(self.fx._tip(self._branch("11")), v1, self.err)

    def test_a_held_bundle_onto_a_branch_names_the_pr_it_commits_onto(self):
        # 12 commits onto `pr-12`, another remote's open PR branch (`Onto branch: fork/pr-12`,
        # #54). Run 1 publishes it alone: its commit (a file of its own) is on pr-12. Iterated
        # and rebuilt to change the line of `shared.txt` that 10 changes, it is held in run 2,
        # so pr-12 still has run 1's commit. That PR is someone else's: the line names it and
        # does not say to close it.
        self._on_base({"shared.txt": "x\n"})
        fork = self.fx.tmp / ONTO_OWNER / "repo.git"
        fork.parent.mkdir()
        subprocess.run(["git", "clone", "-q", "--bare", str(self.fx.origin), str(fork)],
                       check=True, capture_output=True)
        self.fx._push_from_human({"pr-12.txt": "pr 12\n"}, to="pr-12", url=str(fork))
        sb._git(self.fx.primary, "remote", "add", "fork", str(fork))
        self._plan("12", {"twelve-v1.txt": "twelve\n"})
        self._onto("12", "fork/pr-12")
        self._run(["12"])
        d12 = self.cfg.bundle("12")
        rec = json.loads((d12 / "publish.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["mode"], "stacked", self.err)
        v1 = sb._git(fork, "rev-parse", "refs/heads/pr-12").strip()
        driver._archive_iteration(d12, 1, include_brief=False)
        self.changes["12"] = {"shared.txt": "twelve\n"}
        self._plan("10", {"shared.txt": "ten\n"})
        self._plan("20", {"twenty.txt": "twenty\n"}, "10")
        self._run(["10", "12", "20"])

        self.assertEqual(sb._git(fork, "rev-parse", "refs/heads/pr-12").strip(), v1, self.err)
        self.assertEqual(self.holds, {"12": "conflict"}, self.err)
        held = self._held_lines("12")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn(f"no PR opened; the PR it commits onto, {rec['pr_url']}, still has the "
                      f"commit an earlier publish of it pushed.", held[0])
        self.assertNotIn("close it", held[0])


if __name__ == "__main__":
    unittest.main()
