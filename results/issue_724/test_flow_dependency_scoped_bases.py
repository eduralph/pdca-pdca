"""In stack mode a bundle is built on what it declares, not on when it was scheduled (#463).

Before #463 every runnable bundle of a run was pointed at the run's one integration line,
which holds every bundle an earlier wave accepted: ``B`` (``Depends on: A``) was cut from a
line that also held ``Z``, a bundle of the same earlier wave it has nothing to do with, so
``B``'s PR carried ``Z``'s commits, and merging it landed ``Z`` even after ``Z``'s own PR
was closed (#630). Now each bundle's base carries exactly the accepted work of the bundles
it is ordered after by a declared edge — ``Depends on`` and an in-batch ``Depends on
(merged)``, transitively; an earlier-wave ``Conflicts with`` partner; a finished
prerequisite the run carried (#646) — built by ``integrate.build_bundle_base`` (#723), and a
bundle with none of those is built on the real base. The run's line is still folded after
each wave, as the run's check of the combined work. A base that cannot be built stops the
run before the wave, with #723's error: a carried prerequisite whose branch holds work of a
bundle the dependent does not build on, and a carried branch rewritten since the run took
it. And an out-of-batch prerequisite merged into the base is judged by that merge alone: the
dependent is no longer cut from a line that does not follow the base (#655).

Beside the brief's cases, these pin what a member's own edges bring: a carried prerequisite
built on a ``Conflicts with`` or ``Depends on (merged)`` partner brings that partner along
(the partner it was built on is read off its branch), a bundle that ``Conflicts with`` a
carried bundle is built on it (the carry comes before every wave), a ``Conflicts with``
partner that never completed brings nothing of what it was to be built on, and ``Depends
on`` stays transitive through a prerequisite with no patch. And the head a bundle's base
took from a branch, a carried one's too, is the one the next fold and the run's end hold
that branch to (#633, #695).

These cases drive ``flow._drive_and_act`` through real folds on the ``StackFoldGit`` fixture
of tests/test_integrate_stack_bases.py (a bare ``origin``, a primary checkout and a scratch
clone), loaded by path and used as a helper object, as tests/test_flow_same_wave_conflict.py
does. The build and sign-off leaves are stubbed (the build writes a ``patch.diff`` and
accepts, or fails and leaves the bundle PLANNED; a close disposition writes the close marker
instead), ``flow._publish_bundle`` cuts the PR branch from the recorded stack-base tip (else
the base), makes each of the bundle's commits and pushes it, and ``gh`` is answered by a stub
in front of ``subprocess.run``. The publisher is NOT a stub (a stub turns every fold into a
dry-run). A re-issued run is driven the way ``pdca flow <ids>`` drives one: the batch asked
for, with only the bundles not yet finished in the drive set. The carried cases of the brief
drive the carry fixture of tests/test_flow_resume_stack_prereqs.py, and the #655 case the
fixture of tests/test_flow_merged_prereq_on_line.py, loaded the same way.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_dependency_scoped_bases
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

from pdca_harness import flow, integrate, publish, state


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sb = _load("stack_bases_fixture", "test_integrate_stack_bases.py")
rs = _load("resume_stack_prereqs_fixture", "test_flow_resume_stack_prereqs.py")
mp = _load("merged_prereq_fixture", "test_flow_merged_prereq_on_line.py")

TODAY = "2026-10-17"
TWO = "two commits"


def _helper(case: unittest.TestCase, cls: type) -> unittest.TestCase:
    """A fixture TestCase used as a helper object: set up, and torn down with ``case``."""
    helper = cls()
    helper.setUp()
    case.addCleanup(helper.doCleanups)
    return helper


class DependencyScopedBases(unittest.TestCase):

    def setUp(self) -> None:
        self.fx = sb.StackFoldGit()          # the fixture's real-git setUp/tearDown and helpers
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.cfg = self.fx.cfg
        self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
        self.commits: dict[str, list[dict[str, str]]] = {}   # id → its commits' new files
        self.close: set[str] = set()                         # ids closed with no patch
        self.failing: set[str] = set()                       # ids whose build fails
        self.during: dict[str, Callable[[], None]] = {}      # id → run as it is built
        # bundle → (stack base, recorded tip, origin's tip of that base, origin's main) when
        # its wave was driven, this run
        self.seen: dict[str, tuple[str, str, str | None, str]] = {}
        self.order: list[str] = []                           # ids, in the order built
        self.cut: dict[str, str] = {}                        # id → where its branch was cut
        self.after_line_fold: Callable[[], None] | None = None   # run once, after a fold
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _plan(self, iid: str, commits: list[dict[str, str]] | str | None = None, *,
              depends_on: str = "", merged: str = "", conflicts_with: str = "") -> Path:
        """Bundle ``iid``'s brief with the edges given, and what its build commits:
        ``commits`` a list of commits (each the files it writes), ``TWO`` for two commits
        of files of its own, None for one. A bundle in ``self.close`` commits nothing."""
        d = self.cfg.bundle(iid)
        sb._brief(d, extra=(f"- **Depends on:** {depends_on}\n" if depends_on else "")
                  + (f"- **Depends on (merged):** {merged}\n" if merged else "")
                  + (f"- **Conflicts with:** {conflicts_with}\n" if conflicts_with else ""))
        low = iid.lower()
        self.commits[iid] = ([{f"{low}1.txt": f"{iid} one\n"}, {f"{low}2.txt": f"{iid} two\n"}]
                             if commits == TWO else commits or [{f"{low}.txt": f"{iid}\n"}])
        return d

    # -- stubs -----------------------------------------------------------------------------

    def _gh_stub(self, args, *a, **kw):
        """Any ``gh`` call is answered OPEN with the PR's head, its branch's tip on origin;
        everything else runs for real."""
        if not (isinstance(args, list) and args[:1] == ["gh"]):
            return self._real_run(args, *a, **kw)
        iid = str(args[3]).rsplit("/", 1)[-1]
        head = self.fx._tip(f"fix/{iid}") if self.fx._has(f"fix/{iid}") else ""
        return subprocess.CompletedProcess(args, 0, json.dumps(
            {"state": "OPEN", "headRefOid": head}), "")

    def _drive_wave(self, cfg, wave: list[Path], **_kw) -> int:
        """Build and accept each bundle, recording what it was built on, after running its
        ``during`` hook. A bundle in ``self.failing`` fails its build: it stays PLANNED. One
        in ``self.close`` is accepted with a close disposition: no patch."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            base = publish.read_stack_base(d)
            self.seen[d.name] = (base, publish.read_stack_base_tip(d),
                                 self.fx._tip(base) if base and self.fx._has(base) else None,
                                 self.fx._tip("main"))
            self.order.append(iid)
            if iid in self.during:
                self.during[iid]()
            if iid in self.failing:
                continue
            if iid in self.close:
                (d / state.CLOSE_MARKER).write_text("likely-close\n", encoding="utf-8")
            else:
                (d / "patch.diff").write_text("".join(
                    sb._new_file_patch(n, t.rstrip("\n"))
                    for c in self.commits[iid] for n, t in c.items()), encoding="utf-8")
            sb._accept(d)
        return 1

    def _publish_bundle(self, cfg, d: Path, **_kw) -> bool:
        """What publish does: cut ``fix/<iid>`` from the recorded stack-base tip (else the
        recorded base, else the base), make each of the bundle's commits on it, signed off,
        push it and record it — ``stacked-pr`` when cut from a stack base. The brief is not
        touched. A closed bundle publishes nothing."""
        iid = d.name.removeprefix("issue_")
        if iid in self.close:
            return False
        tip, base = publish.read_stack_base_tip(d), publish.read_stack_base(d)
        cut = tip or (f"origin/{base}" if base else "origin/main")
        repo, branch = self.fx.primary, f"fix/{iid}"
        sb._git(repo, "fetch", "-q", "origin")
        sb._git(repo, "checkout", "-q", "-B", branch, cut)
        self.cut[iid] = sb._git(repo, "rev-parse", "HEAD").strip()
        for i, files in enumerate(self.commits[iid], 1):
            for name, text in files.items():
                (repo / name).write_text(text, encoding="utf-8")
            sb._git(repo, "add", "--all")
            sb._git(repo, "commit", "-q", "-s", "-m", f"fix {iid} ({i})")
        sb._git(repo, "push", "-q", "origin", branch)
        sb._git(repo, "checkout", "-q", "main")
        (d / "publish.json").write_text(json.dumps(
            {"mode": "stacked-pr" if base else "new-pr", "branch": branch, "base": "main",
             "repo": "org/repo", "pr_url": f"https://example.test/pr/{iid}"}),
            encoding="utf-8")
        return True

    def _run(self, ids: list[str], *, drive: list[str] | None = None) -> None:
        """One stack-mode run asked for ``ids``, driving ``drive`` (default: all of them;
        a re-issue drives only the ones not finished, as ``pdca flow <ids>`` does). The
        holds it reports are in ``self.holds``."""
        self.ids = list(ids)
        self.line = integrate.integration_branch(self.cfg, "main", ids)
        self.seen, self.order, self.holds = {}, [], {}
        real_fold = integrate.fold

        def fold(*a, **kw):
            out = real_fold(*a, **kw)
            if self.after_line_fold is not None:
                hook, self.after_line_fold = self.after_line_fold, None
                hook()
            return out

        err, out = io.StringIO(), io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
            stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
            stack.enter_context(mock.patch.object(flow, "_publish_bundle",
                                                  self._publish_bundle))
            stack.enter_context(mock.patch.object(publish, "draft_texts",
                                                  lambda *a, **k: True))
            stack.enter_context(mock.patch.object(integrate, "fold", fold))
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(err))
            self.results = flow._drive_and_act(
                self.cfg, [self.cfg.bundle(i) for i in (drive or ids)], do_publish=True,
                do_act=False, by="T", today=TODAY, batch=ids, holds=self.holds)
        self.err = err.getvalue()
        self.assertNotIn("Traceback", self.err)

    # -- helpers ---------------------------------------------------------------------------

    def _head(self, iid: str) -> str:
        return self.fx._tip(f"fix/{iid}")

    def _work(self, iid: str) -> list[str]:
        """Every commit of ``origin/main..fix/<iid>``."""
        return sb._git(self.fx.origin, "rev-list", f"main..fix/{iid}").split()

    def _reach(self, rev: str) -> set[str]:
        return set(sb._git(self.fx.origin, "rev-list", rev).split())

    def _all_of(self, rev: str, iid: str) -> None:
        """``rev`` holds every commit of ``origin/main..fix/<iid>``."""
        work = self._work(iid)
        self.assertTrue(work, iid)
        self.assertEqual([c for c in work if c not in self._reach(rev)], [], (rev, iid))

    def _none_of(self, rev: str, iid: str) -> None:
        """``rev`` holds no commit of ``origin/main..fix/<iid>`` — not one, so a partial
        carry fails too."""
        work = self._work(iid)
        self.assertTrue(work, iid)
        self.assertEqual([c for c in work if c in self._reach(rev)], [], (rev, iid))

    def _built_on(self, iid: str, *closure: str) -> str:
        """``iid`` was built on a base of its own holding exactly the work of ``closure``,
        and its PR branch was cut from that commit; returns it. Its recorded stack base is a
        branch on origin and its recorded tip is that branch's tip when its wave was driven
        (the commit it was built on). The tip holds each of their branches; no commit of
        another bundle of the run's own work; and, beyond the base it started from and
        them, only the merge commits made building it."""
        self.assertIn(f"issue_{iid}", self.seen, self.err)
        base, tip, at, main = self.seen[f"issue_{iid}"]
        self.assertTrue(base, self.err)
        heads = [self._head(c) for c in closure]
        for c, h in zip(closure, heads):
            self.assertTrue(self.fx._ancestor(h, tip), (iid, c, self.err))
        for other in self.ids:
            if other != iid and other not in closure:
                own = self.fx._own(other, base=main, beside=heads)
                self.assertEqual([c for c in own if self.fx._ancestor(c, tip)], [],
                                 (iid, other, self.err))
        self.assertEqual(self.fx._beyond(tip, main, heads), [], (iid, self.err))
        self.assertIsNotNone(at, self.err)
        self.assertEqual(tip, at, self.err)
        self.assertNotEqual(base, self.line, self.err)        # never the run's line
        self.assertEqual(self.cut[iid], tip)                  # its PR branch is cut from it
        self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        return tip

    def _on_real_base(self, iid: str) -> None:
        """``iid`` was built on the real base: no stack base recorded, and its PR branch cut
        from origin's main as its wave found it."""
        base, tip, _at, main = self.seen[f"issue_{iid}"]
        self.assertEqual((base, tip), ("", ""), self.err)
        self.assertEqual(publish.read_stack_base(self.cfg.bundle(iid)), "")
        self.assertEqual(self.cut[iid], main)
        self.assertEqual(self.results[iid], state.COMPLETE, self.err)

    def _stop(self) -> str:
        """The ONE stderr line that stops the run."""
        stop = [x for x in self.err.splitlines() if "STOPPING" in x]
        self.assertEqual(len(stop), 1, self.err)
        return stop[0]

    # -- (1) the #630 case: B carries A, and nothing of Z -----------------------------------

    def test_a_dependent_carries_its_prerequisite_and_nothing_of_an_unrelated_bundle(self):
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("B", depends_on="A")
        self._run(["A", "Z", "B"])

        self.assertNotIn("STOPPING", self.err)
        for iid in ("A", "Z", "B"):
            self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        self.assertEqual(len(self._work("A")), 2)
        self.assertEqual(len(self._work("Z")), 2)
        self._all_of("fix/B", "A")
        self._none_of("fix/B", "Z")
        # B's recorded stack base: a branch on origin holding fix/A's tip and not fix/Z's,
        # the commit B was built on and its PR branch cut from.
        base, tip, _at, _main = self.seen["issue_B"]
        self.assertTrue(self.fx._has(base), self.err)
        self.assertTrue(self.fx._ancestor(self._head("A"), base))
        self.assertFalse(self.fx._ancestor(self._head("Z"), base))
        self.assertEqual(self._built_on("B", "A"), tip)
        # The run's line still folds every accepted bundle: the check of the combined work.
        for iid in ("A", "Z"):
            self._all_of(self.line, iid)

    # -- (2) transitive: C carries B and A, and nothing of Z --------------------------------

    def test_the_base_carries_every_prerequisite_reached_through_another(self):
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("B", depends_on="A")
        self._plan("C", depends_on="B")
        self._run(["A", "Z", "B", "C"])

        self.assertNotIn("STOPPING", self.err)
        self.assertEqual(self.order.index("C"), 3, self.order)         # wave 2
        for iid in ("A", "B"):
            self._all_of("fix/C", iid)
        self._none_of("fix/C", "Z")
        self._built_on("C", "B", "A")
        self._built_on("B", "A")

    def test_a_prerequisite_reached_through_one_with_no_patch_is_on_the_base(self):
        # H `Depends on: N`, and N, closed with no patch, `Depends on: A`. N has nothing to
        # carry, but `Depends on` is transitive: H is ordered after A, so A is on H's base.
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("N", depends_on="A")
        self.close.add("N")
        self._plan("H", depends_on="N")
        self._run(["A", "Z", "N", "H"])

        self.assertNotIn("STOPPING", self.err)
        self.assertEqual(self.order.index("H"), 3, self.order)         # wave 2
        self._built_on("H", "A")
        self._none_of("fix/H", "Z")

    # -- (3) an earlier-wave `Conflicts with` partner is on the base ------------------------

    def test_an_earlier_wave_conflicts_with_partner_is_on_the_base(self):
        # The scheduler puts the name-higher id of a conflicting pair in the later wave.
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("E", conflicts_with="A")
        self._run(["A", "Z", "E"])

        self.assertNotIn("STOPPING", self.err)
        self.assertLess(self.order.index("A"), self.order.index("E"))   # a later wave
        self.assertLess(self.order.index("Z"), self.order.index("E"))
        self._all_of("fix/E", "A")
        self._none_of("fix/E", "Z")
        self._built_on("E", "A")

    def test_a_conflicts_with_partner_that_never_completed_brings_nothing_along(self):
        # Q (wave 0), A `Depends on: Q` (wave 1), E `Conflicts with: A` (wave 2, the
        # name-higher id). A's build fails, so A is on no base, and nothing of what A was to
        # be built on reaches E's: E declared nothing about Q. A partner that never
        # completed does not hold E, so E is built — on the real base.
        self._plan("Q", TWO)
        self._plan("Z", TWO)
        self._plan("A", depends_on="Q")
        self._plan("E", conflicts_with="A")
        self.failing.add("A")
        self._run(["Q", "Z", "A", "E"])

        self.assertNotIn("STOPPING", self.err)
        self.assertEqual(self.results["A"], state.PLANNED, self.err)
        self.assertLess(self.order.index("A"), self.order.index("E"))   # a later wave
        self._on_real_base("E")
        self._none_of("fix/E", "Q")
        self._none_of("fix/E", "Z")
        self._all_of(self.line, "Q")                        # the line has Q all the same

    # -- (4) an in-batch `Depends on (merged)` prerequisite is merged nowhere: carried ------

    def test_an_in_batch_depends_on_merged_prerequisite_is_on_the_base(self):
        # In batch, the field orders G after A like `Depends on`, and A's PR is merged
        # nowhere this run, so only G's base can bring A's work.
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("G", merged="A")
        self._run(["A", "Z", "G"])

        self.assertNotIn("STOPPING", self.err)
        self._all_of("fix/G", "A")
        self._none_of("fix/G", "Z")
        self._built_on("G", "A")

    # -- (5) no prerequisite with work to carry → the real base -----------------------------

    def test_a_bundle_whose_only_prerequisite_has_no_patch_is_built_on_the_real_base(self):
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("N")
        self.close.add("N")                                  # closed: nothing of it to carry
        self._plan("H", depends_on="N")
        self._run(["A", "N", "Z", "H"])

        self.assertNotIn("STOPPING", self.err)
        self.assertLess(self.order.index("N"), self.order.index("H"))   # a later wave
        for iid in ("A", "N", "Z", "H"):
            self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        self._on_real_base("H")                              # record cleared, cut from main
        self._none_of("fix/H", "A")
        self._none_of("fix/H", "Z")
        self._all_of(self.line, "A")                         # the line still has both
        self._all_of(self.line, "Z")

    # -- a re-issue: what a carried bundle was built on comes along -------------------------

    def _carried_on_partner(self, **edge: str) -> None:
        """Run 1 of ``[K, P, D]`` builds ``P`` on ``K`` through ``edge`` (``conflicts_with``
        or ``merged``: ``K`` is earlier, by name or as ``P``'s prerequisite), and ``D``
        (``Depends on: P``) fails, so it stays PLANNED. Run 2 re-issues the batch for ``D``:
        the carry puts the finished ``K`` and ``P`` on the line. ``P``'s branch was cut from
        a base holding ``K``, so ``D``'s base holds both — of ``P`` alone, ``P``'s branch
        would bring ``K``'s commits from below its cut point, which #723 refuses."""
        ids = ["K", "P", "D"]
        self._plan("K", TWO)
        self._plan("P", **edge)
        self._plan("D", depends_on="P")
        self.failing.add("D")
        self._run(ids)
        self.assertEqual(self.results["D"], state.PLANNED, self.err)
        self._built_on("P", "K")                             # run 1 built P on K

        self.failing.clear()
        self._run(ids, drive=["D"])
        self.assertIn("flow: carried issue_K, issue_P (finished", self.err)
        self.assertNotIn("STOPPING", self.err)
        self._built_on("D", "P", "K")
        self._all_of("fix/D", "K")

    def test_a_carried_bundle_built_on_its_conflicts_with_partner_brings_it_along(self):
        self._carried_on_partner(conflicts_with="K")

    def test_a_carried_bundle_built_on_its_depends_on_merged_partner_brings_it_along(self):
        self._carried_on_partner(merged="K")

    def test_a_bundle_that_conflicts_with_a_carried_bundle_is_built_on_it(self):
        # Run 1 of [K, P, D, W] finishes only K. P `Conflicts with: K`, and both write
        # shared.txt; D `Depends on: K`, which makes the re-issue carry K; W `Depends on: D`.
        # The re-issue drives P, D and W. The carry comes before every wave, so P is built
        # on a base holding K, and its change merges onto the line that holds K.
        ids = ["K", "P", "D", "W"]
        self._plan("K", [{"shared.txt": "k\n"}])
        self._plan("P", [{"shared.txt": "p\n"}], conflicts_with="K")
        self._plan("D", depends_on="K")
        self._plan("W", depends_on="D")
        self.failing.update({"P", "D"})
        self._run(ids)
        self.assertEqual(self.results["K"], state.COMPLETE, self.err)
        for iid in ("P", "D", "W"):
            self.assertEqual(self.results[iid], state.PLANNED, self.err)

        self.failing.clear()
        self._run(ids, drive=["P", "D", "W"])
        self.assertIn("flow: carried issue_K (finished", self.err)
        self.assertNotIn("STOPPING", self.err)
        self._built_on("P", "K")
        self._built_on("D", "K")
        self._built_on("W", "D", "K")
        self.assertEqual(self.fx._show(self.line, "shared.txt"), "p\n")  # P's, on top of K

    # -- the head a base took: the next fold, and the run's end, hold the branch to it ------

    def _base_takes_a_newer_head(self, ids: list[str]) -> tuple[str, str]:
        """``A``, then ``B`` (``Depends on: A``), and ``ids`` beyond them. After the fold
        after wave 0 puts ``fix/A`` on the line at ``h1``, a reviewer pushes ``h2`` onto it
        (a fast-forward), so B's base takes ``h2``. While B builds, ``fix/A`` is
        force-pushed back to ``h1``: B's branch holds ``h2``, which A's PR no longer has.
        Returns ``(h1, h2)``."""
        self._plan("A")
        self._plan("B", depends_on="A")
        heads: list[str] = []

        def push_h2() -> None:
            heads.append(self._head("A"))
            heads.append(self.fx._push_from_human({"a2.txt": "A, after review\n"},
                                                  to="fix/A", off="origin/fix/A"))

        def back_to_h1() -> None:
            sb._git(self.fx.origin, "branch", "-f", "fix/A", heads[0])

        self.after_line_fold = push_h2
        self.during["B"] = back_to_h1
        self._run(["A", "B", *ids])
        h1, h2 = heads
        self.assertTrue(self.fx._ancestor(h1, h2))                     # a fast-forward
        self.assertTrue(self.fx._ancestor(h2, self._head("B")))        # B's base took h2
        self.assertEqual(self._head("A"), h1)                          # A's PR lacks it
        return h1, h2

    def test_a_head_a_base_took_is_checked_at_the_end_of_the_run(self):
        _h1, h2 = self._base_takes_a_newer_head([])
        self.assertNotIn("STOPPING", self.err)
        self.assertEqual(self.results["B"], state.COMPLETE, self.err)
        named = [x for x in self.err.splitlines()
                 if "issue_A's branch origin/fix/A was rewritten" in x]
        self.assertEqual(len(named), 1, self.err)
        self.assertIn(h2[:12], named[0])
        self.assertEqual(self.holds, {"A": "rewritten"})

    def test_a_carried_head_a_base_took_is_checked_at_the_end_of_the_run(self):
        # Run 1 of [P, D] finishes P; D fails. The re-issue carries P, and D's base takes
        # P's head. While D builds, fix/P is rewritten: D's PR holds commits P's PR no longer
        # has. P is no bundle this run accepted, but its head is one a base of the run took,
        # so the run's end checks it, names the rewrite and fails the run.
        ids = ["P", "D"]
        self._plan("P")
        self._plan("D", depends_on="P")
        self.failing.add("D")
        self._run(ids)
        self.assertEqual(self.results["P"], state.COMPLETE, self.err)
        took = self._head("P")

        self.failing.clear()
        self.during["D"] = lambda: self.fx._push_from_human({"p2.txt": "P, rebuilt\n"},
                                                           to="fix/P", force=True)
        self._run(ids, drive=["D"])
        self.assertIn("flow: carried issue_P (finished", self.err)
        self.assertNotIn("STOPPING", self.err)
        self.assertTrue(self.fx._ancestor(took, self._head("D")))      # D's base took it
        self.assertFalse(self.fx._ancestor(took, self._head("P")))     # P's PR lacks it
        named = [x for x in self.err.splitlines()
                 if "issue_P's branch origin/fix/P was rewritten" in x]
        self.assertEqual(len(named), 1, self.err)
        self.assertIn(took[:12], named[0])
        self.assertEqual(self.holds, {"P": "rewritten"})

    def test_a_head_a_base_took_is_checked_by_the_next_fold(self):
        # C (`Depends on: B`) comes after B, so a fold runs after B's wave: it stops the
        # run, before C is built on a base holding a commit A's PR no longer has.
        self._plan("C", depends_on="B")
        _h1, h2 = self._base_takes_a_newer_head(["C"])
        stop = self._stop()
        for part in ("wave 1 did not integrate", "issue_A's branch origin/fix/A was "
                     "rewritten", h2[:12]):
            self.assertIn(part, stop)
        self.assertNotIn("issue_C", self.seen, self.err)
        self.assertEqual(self.results["C"], state.PLANNED, self.err)

    # -- a branch the line carried, rewritten before a dependent's base is built (#633) -----

    def test_a_branch_the_line_carried_rewritten_before_a_dependents_base_stops_the_run(self):
        # After the line's fold after wave 0 took fix/A, fix/A is rewritten (re-published
        # from the base). B's base is built from fix/A next: the head the fold took reaches
        # its #633 check, so the run stops there, before B is built on commits the line
        # does not hold.
        self._plan("A")
        self._plan("B", depends_on="A")
        took: list[str] = []
        rebuilt: list[str] = []

        def rewrite_a() -> None:
            took.append(self._head("A"))
            rebuilt.append(self.fx._push_from_human({"a-rebuilt.txt": "A, rebuilt\n"},
                                                    to="fix/A", force=True))

        self.after_line_fold = rewrite_a
        self._run(["A", "B"])

        self.assertEqual(len(took), 1, self.err)
        self.assertFalse(self.fx._ancestor(took[0], rebuilt[0]))         # a rewrite
        self.assertNotIn("issue_B", self.seen, self.err)                  # never built
        self.assertEqual(self.results["B"], state.PLANNED, self.err)
        self.assertEqual(publish.read_stack_base(self.cfg.bundle("B")), "")
        facts = integrate._carried_rewrite(self.fx.origin, "issue_A", "origin/fix/A",
                                           took[0], rebuilt[0], self.line)
        self.assertIsNotNone(facts)
        stop = self._stop()
        for part in ("issue_B", facts):
            self.assertIn(part, stop)


class CarriedPrerequisiteBases(unittest.TestCase):
    """The carried cases (#646): the carry fixture of tests/test_flow_resume_stack_prereqs.py,
    whose run is a re-issue that finds finished ids to carry before wave 0."""

    def setUp(self) -> None:
        self.c = _helper(self, rs.ResumeStackPrereqs)
        self.fx, self.cfg = self.c.fx, self.c.cfg

    def _work(self, iid: str) -> list[str]:
        return sb._git(self.fx.origin, "rev-list", f"main..fix/{iid}").split()

    def _holds_none_of(self, tip: str, iid: str) -> None:
        work = self._work(iid)
        self.assertTrue(work, iid)
        self.assertEqual([c for c in work if self.fx._ancestor(c, tip)], [], (tip, iid))

    def _built_on_carried(self, iid: str, has: str, lacks: str) -> str:
        """``iid`` was built on its recorded base — origin's tip of it when its wave was
        driven — which holds ``fix/<has>``'s tip and no commit of ``fix/<lacks>``, and is
        COMPLETE. Returns that commit."""
        c = self.c
        base, tip, _line = c._built(iid)
        at, _main = c.base_at[f"issue_{iid}"]
        self.assertTrue(base, c.err)
        self.assertTrue(self.fx._ancestor(self.fx._tip(f"fix/{has}"), tip), (iid, c.err))
        self._holds_none_of(tip, lacks)
        self.assertEqual(tip, at, c.err)
        self.assertNotEqual(base, c.line, c.err)             # never the run's line
        self.assertEqual(c.results[iid], state.COMPLETE, c.err)
        return tip

    def _stop(self) -> str:
        stop = [x for x in self.c.err.splitlines() if "STOPPING" in x]
        self.assertEqual(len(stop), 1, self.c.err)
        return stop[0]

    def _never_built(self, iid: str) -> None:
        """``iid`` was never built: PLANNED, and no stack base recorded for it."""
        c = self.c
        self.assertNotIn(f"issue_{iid}", c.seen, c.err)
        self.assertEqual(c.results[iid], state.PLANNED, c.err)
        self.assertEqual(publish.read_stack_base(self.cfg.bundle(iid)), "")
        self.assertEqual(publish.read_stack_base_tip(self.cfg.bundle(iid)), "")

    # -- (6) each carried prerequisite is on its own dependents' bases alone ----------------

    def test_a_carried_finished_prerequisite_is_on_its_dependents_base_alone(self):
        c = self.c
        c._finished("P", {"p.txt": "p\n"})
        c._finished("X", {"x.txt": "x\n"})
        d, e = c._planned("D", "P"), c._planned("E", "X")
        c._run([d, e], ["P", "X", "D", "E"])

        self.assertIn("flow: carried issue_P, issue_X", c.err)
        self.assertNotIn("STOPPING", c.err)
        self._built_on_carried("D", has="P", lacks="X")
        self._built_on_carried("E", has="X", lacks="P")
        for iid in ("P", "X"):                       # the line still carries both
            self.assertTrue(self.fx._ancestor(self.fx._tip(f"fix/{iid}"), c.line), iid)

    # -- (7) a carried prerequisite whose branch holds another carried bundle's work --------

    def test_a_carried_prerequisite_cut_from_a_line_holding_another_stops_the_run(self):
        # An earlier run's line held X, and P was cut from it, recording it as its stack
        # base — but P's brief names no edge to X. Both finish, both are carried; D depends
        # on P alone, so a base of P without X cannot be built: P's branch brings X's
        # commit from below the cut point P recorded.
        c = self.c
        x = c._finished("X", {"x.txt": "x\n"})
        old = integrate.integration_branch(self.cfg, "main", ["X", "P"])   # the earlier run
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            integrate.fold(self.cfg, [x], folded_this_run={}, batch=["X", "P"])
        old_tip = self.fx._tip(old)
        p = self.fx._publish("P", {"p.txt": "p\n"}, cut_from=f"origin/{old}")
        sb._accept(p)
        publish.write_stack_base(p, old, old_tip)
        c.gh["P"] = "OPEN"
        self.assertEqual(state.state(p), state.COMPLETE)
        self.assertTrue(self.fx._ancestor(self.fx._tip("fix/X"), self.fx._tip("fix/P")))
        d = c._planned("D", "P")
        batch = ["X", "P", "D"]
        c._run([d], batch)

        self.assertIn("flow: carried issue_X, issue_P", c.err)          # both carried
        self._never_built("D")
        stop = self._stop()
        for part in ("issue_D", "issue_P", "issue_X"):
            self.assertIn(part, stop)
        # Nothing was pushed for D, and no branch holding X's commits is recorded as the
        # stack base of any bundle of this run; P's record is the earlier run's, untouched.
        self.assertFalse(self.fx._has(
            integrate.bundle_base_branch(self.cfg, "main", batch, "issue_D")))
        self.assertEqual((publish.read_stack_base(p), publish.read_stack_base_tip(p)),
                         (old, old_tip))
        for iid in ("X", "D"):
            b = self.cfg.bundle(iid)
            tip = publish.read_stack_base_tip(b)
            self.assertEqual((publish.read_stack_base(b), tip), ("", ""), iid)

    # -- (8) a carried prerequisite rewritten after the carry (#633) ------------------------

    def test_a_carried_prerequisite_rewritten_after_the_carry_stops_the_run(self):
        c = self.c
        c._finished("P", {"p.txt": "p\n"})
        d = c._planned("D", "P")
        took = self.fx._tip("fix/P")
        rebuilt: list[str] = []
        given: list[dict] = []                     # what each base build was handed
        real_carry, real_build = flow._carry_finished, integrate.build_bundle_base

        def carry_then_rewrite(*a, **kw):
            out = real_carry(*a, **kw)
            rebuilt.append(self.fx._push_from_human({"p2.txt": "p, rebuilt\n"}, to="fix/P",
                                                    force=True))
            return out

        def build(*a, **kw):
            given.append(dict(kw))
            return real_build(*a, **kw)

        with mock.patch.object(flow, "_carry_finished", carry_then_rewrite), \
                mock.patch.object(integrate, "build_bundle_base", build):
            c._run([d], ["P", "D"])

        self.assertIn("flow: carried issue_P", c.err)
        self.assertEqual(len(rebuilt), 1, c.err)
        self.assertFalse(self.fx._ancestor(took, rebuilt[0]))           # a rewrite
        self._never_built("D")
        # The carry's head for P reached the base build's `carried`, and it refused there.
        self.assertEqual(len(given), 1, c.err)
        self.assertEqual(given[0]["carried"].get("issue_P"), took, given)
        facts = integrate._carried_rewrite(self.fx.origin, "issue_P", "origin/fix/P", took,
                                           rebuilt[0], c.line)
        self.assertIsNotNone(facts)
        stop = self._stop()
        for part in ("issue_D", "issue_P", facts):
            self.assertIn(part, stop)


class MergedPrerequisiteJudgedOnTheBase(unittest.TestCase):
    """(9) #655 judged on the base the dependent gets: the fixture of
    tests/test_flow_merged_prereq_on_line.py, where out-of-batch P's PR merges into main
    after the run's first fold, so the line lacks the merge but main has it."""

    def _merged_after_the_first_fold(self, edge: str) -> None:
        m = _helper(self, mp.MergedPrereqOnTheLine)
        m._prereq()
        m.after_first_fold = m._merge
        m._run(m._wd(edge), ["W", "D"])
        fx = m.fx
        self.assertFalse(fx._ancestor(m.merge_oid["P"], m.line))      # the line lacks it
        self.assertEqual([x for x in m.err.splitlines() if "issue_D held" in x], [], m.err)
        self.assertNotIn("STOPPING", m.err)
        self.assertIn("issue_D", m.seen, m.err)
        base, tip = m.seen["issue_D"]
        self.assertTrue(base, m.err)
        self.assertEqual(m.results["D"], state.COMPLETE, m.err)
        self.assertTrue(fx._ancestor(m.merge_oid["P"], tip))          # its base has it
        self.assertTrue(fx._ancestor(fx._tip("fix/W"), tip))
        self.assertTrue(fx._ancestor(m.merge_oid["P"], fx._tip("fix/D")))

    def test_a_plain_depends_on_dependent_is_built_on_a_base_with_the_merge(self):
        self._merged_after_the_first_fold(mp.PLAIN_EDGE)

    def test_a_depends_on_merged_dependent_is_built_on_a_base_with_the_merge(self):
        self._merged_after_the_first_fold(mp.MERGED_EDGE)


if __name__ == "__main__":
    unittest.main()
