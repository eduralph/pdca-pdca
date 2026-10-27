"""A clash at the line fold that is one bundle's holds that bundle, not the run (#739).

A bundle built on its own base (#727) holds only what it declares, so its branch can clash
at the line fold with a bundle already on the line from an earlier wave. Before #739 the
fold held only a clash with bundles of the bundle's own wave (#674, ``integrate._held_by``);
anything else raised, the flow printed ``STOPPING``, and bundles that had nothing to do with
the clash were never built. Now a clash that trial merges pin on bundles of the line — the
branch merges cleanly onto the base alone, and conflicts with bundles already on the line,
one at a time or only several together — holds that bundle, names every partner (a
finished id the carry put on the line included, #646), whatever files their clashes share,
and no bundle the clash does not need. Each partner gets the fix of whoever can act on it,
judged on the base the held branch actually holds: the partner's owner rebuilds on the new
base when that base, which the held branch carries, strands the partner's own change and
the base as it is now still does — never the owner of a branch only built on a stranded
one; the held bundle's owner updates its branch from the base when the base has since
moved past that clash; and for a clash the held bundle's own change has, its owner
rebuilds on the partner's branch when it is ordered after it already (a prerequisite, or a
branch it holds an older tip of), else is proposed a ``Conflicts with``. A bundle that
declared ``Depends on`` it is skipped, one that declared ``Conflicts with`` it is held with
the same reason and what to wait for, and the run goes on.

These cases drive ``flow._drive_and_act`` through real folds and real base builds on the
``StackFoldGit`` fixture of tests/test_integrate_stack_bases.py (a bare ``origin`` and a
primary checkout), loaded by path exactly as tests/test_flow_same_wave_conflict.py does,
with that file's stubs: the build and sign-off leaves stubbed (``flow._drive_wave`` writes a
``patch.diff`` and accepts), ``flow._publish_bundle`` cutting and pushing each PR branch from
the recorded stack-base tip, and ``gh`` answered by a stub in front of ``subprocess.run``
(every PR OPEN, with its branch's tip as its head). The publisher is NOT a stub (a stub
turns every fold into a dry-run). The exit code is the one ``cli._flow`` gives the same run:
``cli._results_rc`` over the results and holds.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions: each ends in
``wave N did not integrate … STOPPING``, its later waves never built. All but the last,
which pins a stop the fix keeps: a branch that clashes with the base itself.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_cross_wave_fold_holds
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

TODAY = "2026-10-19"


def _ten(what: str) -> str:
    """A ten-line file for the base, each line long enough that rewriting seven of them takes
    the file below git's rename-similarity threshold (:func:`_rewrite`)."""
    return "".join(f"line {i} of the {what} file, as the base has it\n" for i in range(1, 11))


TEN = _ten("shared")


def _edit(text: str, **lines: str) -> str:
    """``text`` with line ``n`` (``l<n>=...``) replaced."""
    out = text.splitlines(keepends=True)
    for key, new in lines.items():
        out[int(key.removeprefix("l")) - 1] = new + "\n"
    return "".join(out)


def _rewrite(text: str, who: str) -> str:
    """``text`` (from :func:`_ten`) with its first seven lines rewritten by ``who``."""
    return _edit(text, **{f"l{i}": f"{who} rewrote line {i} entirely: something else altogether"
                          for i in range(1, 8)})


class CrossWaveFoldHolds(unittest.TestCase):

    def setUp(self) -> None:
        self.fx = sb.StackFoldGit()          # the fixture's real-git setUp/tearDown and helpers
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.cfg = self.fx.cfg
        self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
        # id → path → its text on the bundle's branch (None: the branch deletes it)
        self.changes: dict[str, dict[str, str | None]] = {}
        # n → run once, after the run's n-th fold (1: its first)
        self.after_fold: dict[int, Callable[[], None]] = {}
        self.after_publish: dict[str, Callable[[], None]] = {}  # id → run once it published
        self.seen: dict[str, tuple[str, str]] = {}       # bundle → (stack base, tip) when built
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _on_base(self, files: dict[str, str]) -> None:
        """Commit ``files`` on origin's ``main`` (the base every bundle targets)."""
        for name, text in files.items():
            (self.fx.primary / name).write_text(text, encoding="utf-8")
        sb._git(self.fx.primary, "add", "--all")
        sb._git(self.fx.primary, "commit", "-q", "-m", "base files")
        sb._git(self.fx.primary, "push", "-q", "origin", "main")

    def _plan(self, iid: str, files: dict[str, str | None], *, depends_on: str = "",
              stacks_on: str = "", conflicts_with: str = "") -> None:
        sb._brief(self.cfg.bundle(iid),
                  extra=(f"- **Depends on:** {depends_on}\n" if depends_on else "")
                  + (f"- **Stacks on:** {stacks_on}\n" if stacks_on else "")
                  + (f"- **Conflicts with:** {conflicts_with}\n" if conflicts_with else ""))
        self.changes[iid] = files

    def _push_branch(self, iid: str, cut_from: str) -> None:
        """What `publish` does for an accepted bundle (``StackFoldGit._publish``, which
        cannot delete a file): cut ``fix/<iid>`` off ``cut_from``, make its change, commit
        it signed off, push it, and record it in publish.json and patch.diff."""
        d, primary, branch = self.cfg.bundle(iid), self.fx.primary, f"fix/{iid}"
        sb._git(primary, "fetch", "-q", "origin")
        sb._git(primary, "checkout", "-q", "-B", branch, cut_from)
        for name, text in self.changes[iid].items():
            if text is None:
                (primary / name).unlink()
            else:
                (primary / name).write_text(text, encoding="utf-8")
        sb._git(primary, "add", "--all")
        sb._git(primary, "commit", "-q", "-s", "-m", f"fix {iid}")
        (d / "patch.diff").write_text(sb._git(primary, "diff", "HEAD~1", "HEAD"),
                                      encoding="utf-8")
        sb._git(primary, "push", "-q", "origin", branch)
        sb._git(primary, "checkout", "-q", "main")
        mode = "new-pr" if cut_from == "origin/main" else "stacked-pr"
        (d / "publish.json").write_text(json.dumps(
            {"mode": mode, "branch": branch, "base": "main", "repo": "org/repo",
             "pr_url": f"https://example.test/pr/{iid}"}), encoding="utf-8")

    def _finished(self, iid: str, files: dict[str, str]) -> None:
        """``iid`` finished in an earlier run of the batch: published off main, accepted."""
        self._plan(iid, files)
        self._push_branch(iid, "origin/main")
        sb._accept(self.cfg.bundle(iid))

    def _drop_from_main(self, name: str) -> str:
        """Someone deletes ``name`` on origin's ``main`` (``StackFoldGit._push_from_human``
        cannot delete a file); returns the pushed commit."""
        human = self.fx.human
        sb._git(human, "fetch", "-q", "origin")
        sb._git(human, "checkout", "-q", "-B", "scratch", "origin/main")
        sb._git(human, "rm", "-q", name)
        sb._git(human, "commit", "-q", "-s", "-m", f"drop {name} on main")
        sb._git(human, "push", "-q", "origin", "HEAD:refs/heads/main")
        return sb._git(human, "rev-parse", "HEAD").strip()

    def _rebuilt(self, iid: str, *, on: str, as_: str) -> None:
        """``iid``'s branch rebuilt on ``on`` with its side winning every clash — one way its
        owner's rebuild could go — pushed as ``fix/<as_>``, for :func:`_merges` to try."""
        human = self.fx.human
        sb._git(human, "fetch", "-q", "origin")
        sb._git(human, "checkout", "-q", "-B", "scratch", on)
        sb._git(human, "merge", "-q", "--no-edit", "-X", "theirs", f"origin/fix/{iid}")
        sb._git(human, "push", "-q", "origin", f"HEAD:refs/heads/fix/{as_}")

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
        """Build and accept each bundle, recording what it was built on. Its patch.diff
        names the files it changes (publish records the real diff)."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            self.seen[d.name] = (publish.read_stack_base(d), publish.read_stack_base_tip(d))
            (d / "patch.diff").write_text("".join(
                sb._new_file_patch(n, "changed") for n in self.changes[iid]), encoding="utf-8")
            sb._accept(d)
        return 1

    def _publish_bundle(self, cfg, d: Path, **_kw) -> bool:
        """What publish does: cut the PR branch from the recorded stack-base tip (else that
        branch, else the base), push it, record it. The run's brief is kept as it was. Then
        what ``after_publish`` names for it happens (the world moving before the fold)."""
        iid = d.name.removeprefix("issue_")
        tip, base = publish.read_stack_base_tip(d), publish.read_stack_base(d)
        brief = (d / "brief.md").read_text(encoding="utf-8")
        self._push_branch(iid, tip or (f"origin/{base}" if base else "origin/main"))
        (d / "brief.md").write_text(brief, encoding="utf-8")
        self.after_publish.pop(iid, lambda: None)()
        return True

    def _run(self, ids: list[str], *, finished: tuple[str, ...] = ()) -> None:
        """One stack-mode run asked for ``ids``, driving all of them but ``finished``."""
        self.ids = list(ids)
        self.line = integrate.integration_branch(self.cfg, "main", ids)
        self.holds: dict[str, str] = {}
        real_fold = integrate.fold
        folds = [0]

        def fold(*a, **kw):
            out = real_fold(*a, **kw)
            folds[0] += 1
            self.after_fold.pop(folds[0], lambda: None)()
            return out

        self._err = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
            stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
            stack.enter_context(mock.patch.object(flow, "_publish_bundle",
                                                  self._publish_bundle))
            stack.enter_context(mock.patch.object(publish, "draft_texts",
                                                  lambda *a, **k: True))
            stack.enter_context(mock.patch.object(integrate, "fold", fold))
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(self._err))
            self.results = flow._drive_and_act(
                self.cfg, [self.cfg.bundle(i) for i in ids if i not in finished],
                do_publish=True, do_act=False, by="T", today=TODAY, batch=ids,
                holds=self.holds)
        self.err = self._err.getvalue()
        self.rc = cli._results_rc(self.results, holds=self.holds)
        self.assertNotIn("Traceback", self.err)

    # -- helpers ---------------------------------------------------------------------------

    def _head(self, iid: str) -> str:
        return self.fx._tip(f"fix/{iid}")

    def _held(self, iid: str, *parts: str) -> str:
        """ONE stderr line says ``issue_<iid>`` was held out of the fold, with each of
        ``parts``; its branch is on no line the run pushed. Returns that line."""
        lines = [x for x in self.err.splitlines()
                 if x.startswith(f"flow: issue_{iid} held out of the integration fold — ")]
        self.assertEqual(len(lines), 1, self.err)
        for part in parts:
            self.assertIn(part, lines[0])
        self.assertFalse(self.fx._ancestor(self._head(iid), self.fx._tip(self.line)))
        return lines[0]

    def _not_stopped(self) -> None:
        self.assertNotIn("did not integrate", self.err)
        self.assertNotIn("STOPPING", self.err)

    def _complete(self, *ids: str) -> None:
        """Each of ``ids`` was built and is COMPLETE."""
        for iid in ids:
            self.assertIn(f"issue_{iid}", self.seen, self.err)
            self.assertEqual(self.results[iid], state.COMPLETE, self.err)

    def _merges(self, onto: str, *iids: str) -> int | None:
        """Where merging the branches of ``iids`` one after another onto ``onto`` first
        conflicts (its index), or None — the fixture's facts, tried in the scratch clone."""
        human = self.fx.human
        sb._git(human, "fetch", "-q", "origin")
        sb._git(human, "checkout", "-q", "--detach", onto)
        try:
            for i, iid in enumerate(iids):
                if sb._run(human, "merge", "-q", "--no-ff", "--no-edit", "-m", "trial",
                           f"origin/fix/{iid}").returncode != 0:
                    return i
            return None
        finally:
            sb._run(human, "reset", "-q", "--hard")
            sb._git(human, "checkout", "-q", "--detach", "origin/main")

    # -- (1) a partner of an earlier wave, in the batch --------------------------------------

    def test_a_clash_with_an_earlier_wave_bundle_holds_only_that_bundle(self):
        # Y is built on a base of its own holding only Q, its prerequisite, so not A, whose
        # shared.txt the line took in wave 0: the fold after wave 1 cannot merge Y. Before:
        # STOPPING, and U, at the end of an unrelated chain, stayed PLANNED.
        self._plan("A", {"shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        ids = ["A", "Q", "W", "Y", "V", "U"]
        self._run(ids)

        self._not_stopped()
        base, tip = self.seen["issue_Y"]
        self.assertEqual(base, integrate.bundle_base_branch(self.cfg, "main", ids, "issue_Y"))
        self.assertTrue(self.fx._ancestor(self._head("Q"), tip))
        self.assertFalse(self.fx._ancestor(self._head("A"), tip))
        line = self._held("Y", "its change conflicts with issue_A's, already on the line",
                          "(conflicts in shared.txt)", "`Conflicts with` partners are held",
                          "Proposed, for you to confirm: declare `Conflicts with: A` in "
                          "issue_Y's brief, then rebuild issue_Y on a base that holds issue_A")
        for other in ("issue_Q", "issue_W", "issue_V"):
            self.assertNotIn(other, line)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertTrue(self.fx._ancestor(self._head("V"), self.seen["issue_U"][1]))
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    # -- (2) a finished bundle the carry put on the line ------------------------------------

    def test_a_clash_with_a_finished_bundle_carried_onto_the_line_names_it(self):
        # F finished in an earlier run; G depends on it, so the carry puts F on the line
        # before wave 0 (#646). Y, built on Q only, clashes with F there. The fold carries
        # no record of F, so the partner must come from the carry.
        self._finished("F", {"shared.txt": "f\n"})
        self._plan("G", {"g.txt": "g\n"}, depends_on="F")
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        ids = ["F", "G", "Q", "W", "Y", "V", "U"]
        self._run(ids, finished=("F",))

        self.assertIn("flow: carried issue_F (finished in an earlier run) onto", self.err)
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_F's, already on the line",
                          "(conflicts in shared.txt)", "`Conflicts with: F`")
        self.assertNotIn("no bundle", line)
        for other in ("issue_G", "issue_Q", "issue_W", "issue_V"):
            self.assertNotIn(other, line)
        self._complete("G", "Q", "W", "Y", "V", "U")
        self.assertNotIn("F", self.results)                  # finished: not driven this run
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    # -- (3) a line bundle a moved base strands ----------------------------------------------

    def test_a_line_bundle_a_moved_base_strands_is_named_with_the_fix_for_its_owner(self):
        # After wave 0's fold, main gets an a.txt of its own: A's branch, on the line, no
        # longer merges onto main. B's base (A) cannot be built: B is held (#738). W's base
        # (Z) is built on the moved main, so W's branch carries main's a.txt and clashes with
        # A on the line — W's own change has nothing to do with it, and only A's owner can
        # fix it. S (`Stacks on: R`) is cut from the line, so T after it is built after the
        # fold. V depends on W. X declares `Conflicts with: W` (and depends on T, so it is
        # built after the fold that holds W): it is held with W's reason and fix, not told
        # that W's change clashes or that W is to be rebuilt.
        self._plan("A", {"a.txt": "a\n"})
        self._plan("R", {"r.txt": "r\n"})
        self._plan("Z", {"z.txt": "z\n"})
        self._plan("B", {"b.txt": "b\n"}, depends_on="A")
        self._plan("S", {"s.txt": "s\n"}, stacks_on="R")
        self._plan("W", {"w.txt": "w\n"}, depends_on="Z")
        self._plan("T", {"t.txt": "t\n"}, depends_on="S")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("X", {"x.txt": "x\n"}, depends_on="T", conflicts_with="W")
        moved: list[str] = []
        self.after_fold[1] = lambda: moved.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["A", "R", "Z", "B", "S", "W", "T", "V", "X"])

        self._not_stopped()
        # Bases are not pinned to the run's start: W's holds the moved main.
        self.assertTrue(self.fx._ancestor(moved[0], self.seen["issue_W"][1]))
        line = self._held("W", "issue_A's branch, already on the line, does not merge cleanly "
                               "onto origin/main itself: origin/main moved since it was cut, "
                               "and issue_W's branch holds that move", "(conflicts in a.txt)",
                          "To fold it, rebuild issue_A's branch on the new origin/main")
        for blame in ("its change", "rebuild issue_W", "update issue_W", "Conflicts with: A"):
            self.assertNotIn(blame, line)
        self.assertEqual(len([x for x in self.err.splitlines()
                              if x.startswith("flow: issue_B held — could not build issue_B's "
                                              "own base from issue_A")]), 1, self.err)
        self.assertNotIn("issue_V", self.seen, self.err)
        self.assertEqual(self.results["V"], state.PLANNED, self.err)
        self.assertEqual(len([x for x in self.err.splitlines()
                              if x.startswith("flow: issue_V skipped — prerequisite(s) not "
                                              "ready (W)")]), 1, self.err)
        # X, W's `Conflicts with` partner: held with W's reason and the fix for A's owner.
        why = [x for x in self.err.splitlines() if x.startswith("flow: issue_X held — ")]
        self.assertEqual(len(why), 1, self.err)
        for part in ("it `Conflicts with` issue_W, which this run's fold held out of the line "
                     "(issue_A's branch, already on the line, does not merge cleanly onto "
                     "origin/main itself", "wait until issue_A's branch is rebuilt on the new "
                     "origin/main, and issue_W's PR merges into main (org/repo)"):
            self.assertIn(part, why[0])
        for blame in ("its change", "issue_W is rebuilt", "a base that holds issue_A"):
            self.assertNotIn(blame, why[0])
        self.assertNotIn("issue_X", self.seen, self.err)
        self.assertEqual(self.results["X"], state.PLANNED, self.err)
        self._complete("A", "R", "Z", "S", "W", "T")
        self.assertEqual(self.holds, {"B": "base", "W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)          # V and X are left PLANNED, with no hold

    def test_a_partner_built_on_a_stranded_branch_is_not_told_to_rebuild_on_the_base(self):
        # P1 adds a.txt; P2, built on P1 (its own base holds P1), adds s.txt. Both are on the
        # line after wave 1's fold; then main gets an a.txt of its own. P1's branch no longer
        # merges onto main, and neither does P2's — but only for the P1 it holds, not for
        # its own change. W, built on the moved main in wave 2, carries main's a.txt (a clash
        # with P1 on the line) and adds an s.txt of its own (an overlap with P2's own
        # change). So P1's owner is told to rebuild on the new main, and W gets the
        # `Conflicts with: P2` proposal; P2's owner is not told to rebuild on main.
        self._plan("P1", {"a.txt": "p1\n"})
        self._plan("Z0", {"z0.txt": "z0\n"})
        self._plan("P2", {"s.txt": "p2\n"}, depends_on="P1")
        self._plan("Z1", {"z1.txt": "z1\n"}, depends_on="Z0")
        self._plan("W", {"s.txt": "w\n"}, depends_on="Z1")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        moved: list[str] = []
        self.after_fold[2] = lambda: moved.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["P1", "Z0", "P2", "Z1", "W", "V"])

        self._not_stopped()
        self.assertTrue(self.fx._ancestor(moved[0], self.seen["issue_W"][1]))
        self.assertFalse(self.fx._ancestor(moved[0], self.seen["issue_P2"][1]))
        self.assertTrue(self.fx._ancestor(self._head("P1"), self._head("P2")))  # the facts
        self.assertEqual(self._merges("origin/main", "P1"), 0)
        self.assertEqual(self._merges("origin/main", "P2"), 0)
        line = self._held("W", "issue_P1's branch, already on the line, does not merge cleanly "
                               "onto origin/main itself",
                          "its change also conflicts with issue_P2's, already on the line",
                          "(conflicts in a.txt, s.txt)",
                          "rebuild issue_P1's branch on the new origin/main",
                          "`Conflicts with: P2` in issue_W's brief")
        for wrong in ("issue_P2's branch", "Conflicts with: P1"):
            self.assertNotIn(wrong, line)
        self.assertNotIn("issue_V", self.seen, self.err)
        self._complete("P1", "Z0", "P2", "Z1", "W")
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)               # V is left PLANNED, with no hold

    def test_a_partner_whose_own_base_does_not_merge_is_not_called_stranded(self):
        # As above, but P2 also changes the a.txt P1 added. So P2's branch clashes with the
        # moved main in a.txt, the file W clashes with it in — and P2's own change cannot be
        # tried on main at all, since P1, what it was built on, does not merge there first.
        # Its owner is still not told to rebuild on main: that is P1's step, and P2 is
        # rebuilt on P1 once P1 is. W gets the `Conflicts with: P2` proposal.
        self._plan("P1", {"a.txt": "p1\n"})
        self._plan("Z0", {"z0.txt": "z0\n"})
        self._plan("P2", {"a.txt": "p2\n", "s.txt": "p2\n"}, depends_on="P1")
        self._plan("Z1", {"z1.txt": "z1\n"}, depends_on="Z0")
        self._plan("W", {"s.txt": "w\n"}, depends_on="Z1")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        moved: list[str] = []
        self.after_fold[2] = lambda: moved.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["P1", "Z0", "P2", "Z1", "W", "V"])

        self.assertTrue(self.fx._ancestor(moved[0], self.seen["issue_W"][1]))  # the facts
        self.assertTrue(self.fx._ancestor(self._head("P1"), self._head("P2")))
        self.assertEqual(self._merges("origin/main", "P1"), 0)
        self.assertEqual(self._merges("origin/main", "P2"), 0)
        self._not_stopped()
        line = self._held("W", "issue_P1's branch, already on the line, does not merge cleanly "
                               "onto origin/main itself",
                          "its change also conflicts with issue_P2's, already on the line",
                          "(conflicts in a.txt, s.txt)",
                          "rebuild issue_P1's branch on the new origin/main",
                          "`Conflicts with: P2` in issue_W's brief")
        for wrong in ("issue_P2's branch", "Conflicts with: P1"):
            self.assertNotIn(wrong, line)
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)               # V is left PLANNED, with no hold

    def test_a_bundle_built_before_the_base_moved_is_told_its_own_fix(self):
        # A adds a.txt and changes shared.txt; Y, built on Q only, changes shared.txt too.
        # Once Y has published — after its base was built — main gets an a.txt of its own,
        # so A's branch no longer merges onto main. But Y's branch holds no part of that
        # move: its clash with A is their two changes to shared.txt, which A's rebuild on the
        # new main would leave standing. So Y's owner gets the `Conflicts with: A` proposal,
        # and A's owner is not told to rebuild for Y.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"a.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moved: list[str] = []
        self.after_publish["Y"] = lambda: moved.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertFalse(self.fx._ancestor(moved[0], self._head("Y")))   # the fixture's facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line",
                          "(conflicts in shared.txt)",
                          "Proposed, for you to confirm: declare `Conflicts with: A` in "
                          "issue_Y's brief, then rebuild issue_Y on a base that holds issue_A")
        for wrong in ("merge cleanly onto origin/main itself", "holds that move",
                      "rebuild issue_A's branch", "update issue_Y's branch"):
            self.assertNotIn(wrong, line)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_bundle_built_before_the_base_moved_is_never_said_to_hold_the_move(self):
        # A changes lines 2 and 8 of a nine-line shared.txt; Y, built on Q only, changes line
        # 2. Once Y has published, main changes line 8, so A's branch no longer merges onto
        # main — in shared.txt, the very file Y clashes with A in. Y still merges onto main
        # (line 8 is not Y's), and its branch holds no part of the move: its clash with A is
        # its own change, on line 2. So A is not called stranded for Y, and Y is not said to
        # hold the move.
        nine = "".join(f"line {i}\n" for i in range(1, 10))
        self._on_base({"shared.txt": nine})
        self._plan("A", {"shared.txt": _edit(nine, l2="a", l8="a")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(nine, l2="y")}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moved: list[str] = []
        self.after_publish["Y"] = lambda: moved.append(self.fx._push_from_human(
            {"shared.txt": _edit(nine, l8="main's own")}, to="main"))
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertFalse(self.fx._ancestor(moved[0], self._head("Y")))   # the fixture's facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line",
                          "(conflicts in shared.txt)", "`Conflicts with: A` in issue_Y's brief")
        for wrong in ("merge cleanly onto origin/main itself", "holds that move",
                      "rebuild issue_A's branch", "update issue_Y's branch"):
            self.assertNotIn(wrong, line)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_base_move_the_clash_is_not_in_is_not_blamed_for_it(self):
        # Main moves twice. After wave 0's fold it gets an m.txt no bundle touches, so Y,
        # built in wave 1, holds a newer main than the line. Once Y has published, main also
        # gets an a.txt of its own, so A's branch no longer merges onto main. Y's clash with
        # A is still only their two changes to shared.txt: not a file A clashes with main
        # in, so A's rebuild on the new main would not settle it. Y's owner gets the
        # `Conflicts with: A` proposal; A's owner is not told to rebuild for Y.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"a.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moves: list[str] = []
        self.after_fold[1] = lambda: moves.append(self.fx._push_from_human(
            {"m.txt": "main's own\n"}, to="main"))
        self.after_publish["Y"] = lambda: moves.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(moves[0], self._head("Y")))    # the fixture's facts
        self.assertFalse(self.fx._ancestor(moves[1], self._head("Y")))
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line",
                          "(conflicts in shared.txt)",
                          "Proposed, for you to confirm: declare `Conflicts with: A` in "
                          "issue_Y's brief, then rebuild issue_Y on a base that holds issue_A")
        for wrong in ("merge cleanly onto origin/main itself", "holds that move",
                      "rebuild issue_A's branch", "update issue_Y's branch"):
            self.assertNotIn(wrong, line)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_base_move_the_branch_does_not_hold_is_not_blamed_in_the_file_it_moved(self):
        # Main moves twice. After wave 0's fold it gets an m.txt no bundle touches, so Y,
        # built in wave 1, holds a newer main than the line. Once Y has published, main also
        # changes line 8 of shared.txt, which A changed too: A's branch no longer merges onto
        # main, in shared.txt, the very file Y clashes with A in. But Y's branch holds only
        # the first move, and A merges cleanly onto the main Y holds: Y's clash with A is its
        # own change, on line 2. So Y's owner gets the `Conflicts with: A` proposal; A is
        # not called stranded for Y, and Y is not said to hold the move. V is `Stacks on:
        # W` (cut from the line), so no branch merged before Y brings the first move onto the
        # line: Y's is the only one holding it.
        nine = "".join(f"line {i}\n" for i in range(1, 10))
        self._on_base({"shared.txt": nine})
        self._plan("A", {"shared.txt": _edit(nine, l2="a", l8="a")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(nine, l2="y")}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moves: list[str] = []
        self.after_fold[1] = lambda: moves.append(self.fx._push_from_human(
            {"m.txt": "main's own\n"}, to="main"))
        self.after_publish["Y"] = lambda: moves.append(self.fx._push_from_human(
            {"shared.txt": _edit(nine, l8="main's own")}, to="main"))
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(moves[0], self._head("Y")))    # the fixture's facts
        self.assertFalse(self.fx._ancestor(moves[1], self._head("Y")))
        self.assertFalse(self.fx._ancestor(moves[0], self._head("V")))
        self.assertIsNone(self._merges(moves[0], "A"))          # onto the main Y holds: clean
        self.assertEqual(self._merges("origin/main", "A"), 0)   # onto main now: not
        self.assertIsNone(self._merges("origin/main", "Y"))
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line",
                          "(conflicts in shared.txt)",
                          "Proposed, for you to confirm: declare `Conflicts with: A` in "
                          "issue_Y's brief, then rebuild issue_Y on a base that holds issue_A")
        for wrong in ("merge cleanly onto origin/main", "holds that move",
                      "rebuild issue_A's branch", "update issue_Y's branch"):
            self.assertNotIn(wrong, line)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_base_move_the_branch_takes_back_is_not_blamed_for_its_clash(self):
        # A adds x.txt and changes shared.txt. After wave 0's fold, main gets an x.txt of its
        # own, so A's branch no longer merges onto main. Y, built in wave 1 on that main,
        # deletes the x.txt main added and changes shared.txt, as A did. So Y holds the
        # move but takes its x.txt back out: Y clashes with A only in shared.txt, its own
        # change, not in the x.txt A fails on main in. Y's owner gets the `Conflicts with:
        # A` proposal; A is not called stranded for Y. V is `Stacks on: W` (cut from the
        # line), so Y's is the only branch holding the move.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"x.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"x.txt": None, "shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moved: list[str] = []
        self.after_fold[1] = lambda: moved.append(self.fx._push_from_human(
            {"x.txt": "main's own\n"}, to="main"))
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(moved[0], self._head("Y")))    # the fixture's facts
        self.assertFalse(self.fx._ancestor(moved[0], self._head("V")))
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line",
                          "(conflicts in shared.txt)",
                          "Proposed, for you to confirm: declare `Conflicts with: A` in "
                          "issue_Y's brief, then rebuild issue_Y on a base that holds issue_A")
        for wrong in ("merge cleanly onto origin/main", "holds that move",
                      "rebuild issue_A's branch", "update issue_Y's branch"):
            self.assertNotIn(wrong, line)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_stranded_partner_whose_change_the_bundle_also_overlaps_gets_both_steps(self):
        # A adds a.txt and changes shared.txt. After wave 0's fold, main gets an a.txt of its
        # own. Y, built in wave 1 on the moved main, carries main's a.txt — the base's clash
        # with A — and changes shared.txt itself, as A did. A's rebuild on the new main
        # settles the first, not the second: Y still conflicts with A's change after it. So
        # both steps are given — A's owner rebuilds on main, and Y's owner gets the
        # `Conflicts with: A` proposal. V, of the unrelated chain, is `Stacks on: W`: cut
        # from the line, it holds no part of main's move.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"a.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moved: list[str] = []
        self.after_fold[1] = lambda: moved.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(moved[0], self.seen["issue_Y"][1]))  # the facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self._not_stopped()
        line = self._held("Y", "issue_A's branch, already on the line, does not merge cleanly "
                               "onto origin/main itself: origin/main moved since it was cut, "
                               "and issue_Y's branch holds that move",
                          "its change also conflicts with issue_A's, already on the line",
                          "(conflicts in a.txt, shared.txt)",
                          "To fold it, rebuild issue_A's branch on the new origin/main",
                          "Proposed, for you to confirm: declare `Conflicts with: A` in "
                          "issue_Y's brief, then rebuild issue_Y on a base that holds issue_A")
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_stranded_partner_needed_for_a_clash_together_gets_both_steps(self):
        # A renames shared.txt to moved.txt and adds a.txt; R rewrites most of shared.txt.
        # After wave 0's fold, main gets an a.txt of its own. Y, built in wave 1 on the moved
        # main, carries main's a.txt — the base's clash with A — and changes the last line of
        # shared.txt, which clashes with A's rename and R's rewrite together, though with
        # neither alone. Rebuilding A on the new main settles the first only: Y then still
        # clashes with A and R together. So A's owner is told to rebuild on main, and Y's
        # owner gets the `Conflicts with: A, R` proposal. V is `Stacks on: W`: cut from the
        # line, it holds no part of main's move.
        self._on_base({"shared.txt": TEN})
        self._plan("A", {"shared.txt": None, "moved.txt": TEN, "a.txt": "a\n"})
        self._plan("R", {"shared.txt": _rewrite(TEN, "R")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(TEN, l10="line 10, as Y has it")},
                   depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moved: list[str] = []
        self.after_fold[1] = lambda: moved.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self._run(["A", "R", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(moved[0], self.seen["issue_Y"][1]))  # the facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "R", "Y"))
        self._rebuilt("A", on="origin/main", as_="AB")   # A rebuilt on main, its side winning
        self.assertIsNone(self._merges("origin/main", "AB", "Y"))
        self.assertEqual(self._merges("origin/main", "AB", "R", "Y"), 2)
        self._not_stopped()
        line = self._held("Y", "issue_A's branch, already on the line, does not merge cleanly "
                               "onto origin/main itself: origin/main moved since it was cut, "
                               "and issue_Y's branch holds that move",
                          "its change also conflicts with issue_A's, issue_R's, already on the "
                          "line", "(conflicts in a.txt, shared.txt)",
                          "To fold it, rebuild issue_A's branch on the new origin/main",
                          "Proposed, for you to confirm: declare `Conflicts with: A, R` in "
                          "issue_Y's brief")
        for other in ("issue_Q", "issue_W", "issue_V"):
            self.assertNotIn(other, line)
        self._complete("A", "R", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_clash_with_a_base_commit_main_has_since_undone_is_for_the_branch_to_update(self):
        # A adds a.txt. After wave 0's fold, main gets an a.txt of its own; V and Y, built on
        # bases of their own in wave 1, hold that main, and neither touches a.txt. Once both
        # have published, main deletes its a.txt again: A's branch merges onto main as it is
        # now, but V's and Y's branches still carry the a.txt main has dropped. That is their
        # clash with A — neither their own change nor A's owner's to fix. Each is told to
        # update its branch from origin/main, after which it merges onto the line, and is
        # given no `Conflicts with: A` proposal. U depends on V and is skipped; S, `Stacks on:
        # R` (cut from the line, which never had main's a.txt), and T after it carry on.
        self._plan("A", {"a.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("R", {"r.txt": "r\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("S", {"s.txt": "s\n"}, stacks_on="R")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("Y", {"y.txt": "y\n"}, depends_on="Q")
        self._plan("T", {"t.txt": "t\n"}, depends_on="S")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        moves: list[str] = []
        self.after_fold[1] = lambda: moves.append(self.fx._push_from_human(
            {"a.txt": "main's own\n"}, to="main"))
        self.after_publish["Y"] = lambda: moves.append(self._drop_from_main("a.txt"))
        self._run(["A", "Q", "R", "W", "S", "V", "Y", "T", "U"])

        for iid in ("V", "Y"):                                          # the fixture's facts
            self.assertTrue(self.fx._ancestor(moves[0], self._head(iid)), iid)
            self.assertFalse(self.fx._ancestor(moves[1], self._head(iid)), iid)
            self.assertIsNone(self._merges("origin/main", iid), iid)
        self.assertEqual(self._merges(moves[0], "A"), 0)    # not onto the main they hold
        self.assertIsNone(self._merges("origin/main", "A"))  # onto main as it is now: clean
        self._not_stopped()
        for iid in ("V", "Y"):
            line = self._held(iid, "issue_A's branch, already on the line, does not merge "
                                   f"cleanly onto the origin/main issue_{iid}'s branch holds, "
                                   "but does onto origin/main as it is now: origin/main moved "
                                   f"on since issue_{iid}'s branch was built",
                              "(conflicts in a.txt)",
                              f"To fold it, update issue_{iid}'s branch from origin/main, then "
                              "re-run.")
            for wrong in ("its change", "Conflicts with: A", "rebuild issue_A's branch"):
                self.assertNotIn(wrong, line)
        self.fx._update_branch("Y")                       # the step works: Y then merges
        self.assertIsNone(self._merges(f"origin/{self.line}", "Y"))
        self.assertNotIn("issue_U", self.seen, self.err)
        self._complete("A", "Q", "R", "W", "S", "V", "Y", "T")
        self.assertEqual(self.holds, {"V": "conflict", "Y": "conflict"})
        self.assertEqual(self.rc, 1, self.err)               # U is left PLANNED, with no hold

    # -- a partner the held branch is ordered after already -----------------------------------

    def test_a_branch_holding_an_older_tip_of_its_prerequisite_is_told_so(self):
        # Y depends on A, so its base holds A's branch. Once Y has published, A's owner pushes
        # a fixup onto A's branch — a fast-forward, which the next fold takes (#633) — that
        # changes the line of shared.txt Y changes. Y's branch holds A's earlier tip, not the
        # fixup: it is held, told that it holds an older tip of issue_A's branch and to
        # rebuild on issue_A's — not that it lacks A, and with no `Conflicts with: A`
        # proposal (A is its prerequisite already).
        nine = "".join(f"line {i}\n" for i in range(1, 10))
        self._on_base({"shared.txt": nine})
        self._plan("A", {"a.txt": "a\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(nine, l5="y")}, depends_on="A")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        fixup: list[str] = []
        self.after_publish["Y"] = lambda: fixup.append(self.fx._push_from_human(
            {"shared.txt": _edit(nine, l5="a's fixup")}, to="fix/A", off="origin/fix/A"))
        self._run(["A", "W", "Y", "V", "U"])

        self.assertEqual(self._head("A"), fixup[0])                    # the fixture's facts
        self.assertTrue(self.fx._ancestor(f"{fixup[0]}~1", self._head("Y")))
        self.assertFalse(self.fx._ancestor(fixup[0], self._head("Y")))
        self.assertTrue(self.fx._ancestor(fixup[0], self.fx._tip(self.line)))
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line: its "
                               "branch holds an older tip of issue_A's branch",
                          "(conflicts in shared.txt)",
                          "To fold it, rebuild issue_Y's branch on issue_A's, then re-run.")
        for wrong in ("does not hold", "Conflicts with: A", "rebuild issue_A's branch",
                      "update issue_Y's branch"):
            self.assertNotIn(wrong, line)
        self._complete("A", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    # -- (4) a clash only with several partners together -------------------------------------

    def test_a_clash_only_with_two_line_bundles_together_names_both(self):
        # P renames shared.txt to moved.txt; R rewrites most of shared.txt; H changes its
        # last line. H merges onto main plus either one alone (git follows P's rename, and
        # R's lines are not H's), but after both, the line's moved.txt is no longer like
        # main's shared.txt, so H's edit has nowhere to go. K, H's prerequisite, is on the
        # line too, but H is built on it: K is not what H clashes with, so it is not named.
        # X, of the same earlier wave, adds a file of its own: H merges after the line
        # without it no better, so it is not named either. J (after H in the fold) and L
        # carry on.
        self._on_base({"shared.txt": TEN})
        self._plan("P", {"shared.txt": None, "moved.txt": TEN})
        self._plan("R", {"shared.txt": _rewrite(TEN, "R")})
        self._plan("K", {"k.txt": "k\n"})
        self._plan("X", {"x.txt": "x\n"})
        self._plan("H", {"shared.txt": _edit(TEN, l10="line 10, as H has it")},
                   depends_on="K")
        self._plan("J", {"j.txt": "j\n"}, depends_on="K")
        self._plan("L", {"l.txt": "l\n"}, depends_on="J")
        self._run(["P", "R", "K", "X", "H", "J", "L"])

        self.assertIsNone(self._merges("origin/main", "P", "H"))       # the fixture's facts
        self.assertIsNone(self._merges("origin/main", "R", "H"))
        self.assertEqual(self._merges("origin/main", "K", "P", "R", "X", "H"), 4)
        self.assertEqual(self._merges("origin/main", "K", "P", "R", "H"), 3)   # X or not
        self.assertTrue(self.fx._ancestor(self._head("K"), self._head("H")))
        self._not_stopped()
        line = self._held("H", "its change conflicts with issue_P's, issue_R's, already on "
                               "the line", "(conflicts in shared.txt)", "`Conflicts with: P, R`",
                          "rebuild issue_H on a base that holds issue_P, issue_R")
        for other in ("issue_K", "issue_X", "issue_J"):
            self.assertNotIn(other, line)
        self._complete("P", "R", "K", "X", "H", "J", "L")
        self.assertEqual(self.holds, {"H": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_clash_together_names_whose_change_it_needs_not_who_carries_it(self):
        # Case (4)'s clash, with the line of a third wave: P renames shared.txt, and P2,
        # built on P, adds a file of its own; V, built on W, rewrites most of shared.txt, and
        # W adds a file of its own. H (wave 2) conflicts after P's rename and V's rewrite
        # together. Leaving P out alone changes nothing — P2 carries it — so P is named for
        # the change P2 carries; P2 is not, for its own adds nothing to the clash. V is named
        # for its own change; W, only under it, is not. K0 and K1 are H's own prerequisites.
        self._on_base({"shared.txt": TEN})
        self._plan("P", {"shared.txt": None, "moved.txt": TEN})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("K0", {"k0.txt": "k0\n"})
        self._plan("P2", {"p2.txt": "p2\n"}, depends_on="P")
        self._plan("V", {"shared.txt": _rewrite(TEN, "V")}, depends_on="W")
        self._plan("K1", {"k1.txt": "k1\n"}, depends_on="K0")
        self._plan("H", {"shared.txt": _edit(TEN, l10="line 10, as H has it")},
                   depends_on="K1")
        self._plan("J", {"j.txt": "j\n"}, depends_on="K1")
        self._plan("L", {"l.txt": "l\n"}, depends_on="J")
        self._run(["P", "W", "K0", "P2", "V", "K1", "H", "J", "L"])

        self.assertIsNone(self._merges("origin/main", "P2", "H"))      # the fixture's facts
        self.assertIsNone(self._merges("origin/main", "V", "H"))
        self.assertEqual(self._merges("origin/main", "P2", "V", "H"), 2)
        self.assertTrue(self.fx._ancestor(self._head("P"), self._head("P2")))
        self.assertTrue(self.fx._ancestor(self._head("W"), self._head("V")))
        self._not_stopped()
        line = self._held("H", "its change conflicts with issue_P's, issue_V's, already on "
                               "the line", "(conflicts in shared.txt)", "`Conflicts with: P, V`")
        for other in ("issue_P2", "issue_W", "issue_K0", "issue_K1", "issue_J"):
            self.assertNotIn(other, line)
        self._complete("P", "W", "K0", "P2", "V", "K1", "H", "J", "L")
        self.assertEqual(self.holds, {"H": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_two_clashes_only_together_in_two_files_name_all_four(self):
        # Case (4)'s clash twice, one in each of two files: P1 renames first.txt and R1
        # rewrites most of it; P2 and R2 do the same to second.txt. H changes the last line
        # of both. H merges after any one of the four, but not after P1 and R1 (its first.txt
        # change has nowhere to go), nor after P2 and R2. Leaving any one of the four out
        # leaves the other file's clash standing, so no one of them is needed for the whole
        # clash: each file is judged on its own, and H is held naming all four. K, H's
        # prerequisite, and X, which adds a file of its own, are not named; J and L carry on.
        first, second = _ten("first"), _ten("second")
        self._on_base({"first.txt": first, "second.txt": second})
        self._plan("P1", {"first.txt": None, "moved1.txt": first})
        self._plan("R1", {"first.txt": _rewrite(first, "R1")})
        self._plan("P2", {"second.txt": None, "moved2.txt": second})
        self._plan("R2", {"second.txt": _rewrite(second, "R2")})
        self._plan("K", {"k.txt": "k\n"})
        self._plan("X", {"x.txt": "x\n"})
        self._plan("H", {"first.txt": _edit(first, l10="line 10, as H has it"),
                         "second.txt": _edit(second, l10="line 10, as H has it")},
                   depends_on="K")
        self._plan("J", {"j.txt": "j\n"}, depends_on="K")
        self._plan("L", {"l.txt": "l\n"}, depends_on="J")
        self._run(["P1", "R1", "P2", "R2", "K", "X", "H", "J", "L"])

        line_up = ["K", "P1", "P2", "R1", "R2", "X"]               # the fixture's facts
        for one in ("P1", "R1", "P2", "R2"):
            self.assertIsNone(self._merges("origin/main", one, "H"), one)
            self.assertEqual(self._merges("origin/main", *(n for n in line_up if n != one), "H"),
                             5, one)
        self.assertEqual(self._merges("origin/main", "P1", "R1", "H"), 2)
        self.assertEqual(self._merges("origin/main", "P2", "R2", "H"), 2)
        self._not_stopped()
        line = self._held("H", "its change conflicts with issue_P1's, issue_P2's, issue_R1's, "
                               "issue_R2's, already on the line",
                          "(conflicts in first.txt, second.txt)",
                          "`Conflicts with: P1, P2, R1, R2`")
        for other in ("issue_K", "issue_X", "issue_J"):
            self.assertNotIn(other, line)
        self._complete("P1", "R1", "P2", "R2", "K", "X", "H", "J", "L")
        self.assertEqual(self.holds, {"H": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_clash_with_one_bundle_beside_one_only_together_names_all_three(self):
        # A adds a shared.txt, as H does: a clash A alone accounts for. In first.txt, H's
        # change clashes only with P's rename and R's rewrite together, which no one bundle
        # accounts for. A's clash does not hide theirs: H is held naming A, P and R, not A
        # alone. K, H's prerequisite, is not named.
        first = _ten("first")
        self._on_base({"first.txt": first})
        self._plan("A", {"shared.txt": "a\n"})
        self._plan("P", {"first.txt": None, "moved.txt": first})
        self._plan("R", {"first.txt": _rewrite(first, "R")})
        self._plan("K", {"k.txt": "k\n"})
        self._plan("H", {"shared.txt": "h\n",
                         "first.txt": _edit(first, l10="line 10, as H has it")},
                   depends_on="K")
        self._plan("J", {"j.txt": "j\n"}, depends_on="K")
        self._plan("L", {"l.txt": "l\n"}, depends_on="J")
        self._run(["A", "P", "R", "K", "H", "J", "L"])

        self.assertEqual(self._merges("origin/main", "A", "H"), 1)      # the fixture's facts
        self.assertIsNone(self._merges("origin/main", "P", "H"))
        self.assertIsNone(self._merges("origin/main", "R", "H"))
        self.assertEqual(self._merges("origin/main", "P", "R", "H"), 2)
        self._not_stopped()
        line = self._held("H", "its change conflicts with issue_A's, issue_P's, issue_R's, "
                               "already on the line", "(conflicts in first.txt, shared.txt)",
                          "`Conflicts with: A, P, R`")
        for other in ("issue_K", "issue_J"):
            self.assertNotIn(other, line)
        self._complete("A", "P", "R", "K", "H", "J", "L")
        self.assertEqual(self.holds, {"H": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_clash_with_one_bundle_and_with_two_together_in_one_file_names_all_three(self):
        # All in shared.txt: A changes its last line, as H does — a clash A alone accounts
        # for. P renames the file and R rewrites most of it, which clashes with H's edit too,
        # with the two together though with neither alone. A's clash, in the same file, must
        # not hide theirs: H rebuilt on A alone still clashes with P and R. So H is held
        # naming all three. K, H's prerequisite, is not named; J and L carry on.
        self._on_base({"shared.txt": TEN})
        self._plan("A", {"shared.txt": _edit(TEN, l10="line 10, as A has it")})
        self._plan("P", {"shared.txt": None, "moved.txt": TEN})
        self._plan("R", {"shared.txt": _rewrite(TEN, "R")})
        self._plan("K", {"k.txt": "k\n"})
        self._plan("H", {"shared.txt": _edit(TEN, l10="line 10, as H has it")},
                   depends_on="K")
        self._plan("J", {"j.txt": "j\n"}, depends_on="K")
        self._plan("L", {"l.txt": "l\n"}, depends_on="J")
        self._run(["A", "P", "R", "K", "H", "J", "L"])

        self.assertEqual(self._merges("origin/main", "A", "H"), 1)      # the fixture's facts
        self.assertIsNone(self._merges("origin/main", "P", "H"))
        self.assertIsNone(self._merges("origin/main", "R", "H"))
        self.assertEqual(self._merges("origin/main", "K", "P", "R", "H"), 3)
        self._rebuilt("H", on="origin/fix/A", as_="HA")  # H rebuilt on A, its side winning
        self.assertIsNone(self._merges("origin/main", "A", "HA"))
        self.assertEqual(self._merges("origin/main", "A", "P", "R", "HA"), 3)
        self._not_stopped()
        line = self._held("H", "its change conflicts with issue_A's, issue_P's, issue_R's, "
                               "already on the line", "(conflicts in shared.txt)",
                          "`Conflicts with: A, P, R`",
                          "rebuild issue_H on a base that holds issue_A, issue_P, issue_R")
        for other in ("issue_K", "issue_J"):
            self.assertNotIn(other, line)
        self._complete("A", "P", "R", "K", "H", "J", "L")
        self.assertEqual(self.holds, {"H": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_the_own_change_of_a_bundle_built_on_a_partner_is_judged_too(self):
        # A changes the last line of shared.txt, as H does: a clash A alone accounts for. B,
        # built on A, renames the file; P rewrites most of it. B's own change, the rename,
        # clashes with H's edit together with P's rewrite, though neither alone does. B
        # carries A's change, but that is not all it brings: H rebuilt on A alone still
        # clashes with B and P. So H is held naming A, P and B. K0 and K1, H's prerequisites,
        # are not named; J and L carry on.
        self._on_base({"shared.txt": TEN})
        self._plan("A", {"shared.txt": _edit(TEN, l10="line 10, as A has it")})
        self._plan("K0", {"k0.txt": "k0\n"})
        self._plan("P", {"shared.txt": _rewrite(TEN, "P")})
        self._plan("B", {"shared.txt": None,
                         "moved.txt": _edit(TEN, l10="line 10, as A has it")}, depends_on="A")
        self._plan("K1", {"k1.txt": "k1\n"}, depends_on="K0")
        self._plan("H", {"shared.txt": _edit(TEN, l10="line 10, as H has it")},
                   depends_on="K1")
        self._plan("J", {"j.txt": "j\n"}, depends_on="K1")
        self._plan("L", {"l.txt": "l\n"}, depends_on="J")
        self._run(["A", "K0", "P", "B", "K1", "H", "J", "L"])

        self.assertTrue(self.fx._ancestor(self._head("A"), self._head("B")))  # the facts
        self.assertEqual(self._merges("origin/main", "A", "H"), 1)
        self.assertIsNone(self._merges("origin/main", "P", "H"))
        self._rebuilt("H", on="origin/fix/A", as_="HA")  # H rebuilt on A, its side winning
        self.assertIsNone(self._merges("origin/main", "A", "B", "HA"))
        self.assertIsNone(self._merges("origin/main", "A", "P", "HA"))
        self.assertEqual(self._merges("origin/main", "A", "P", "B", "HA"), 3)
        self._not_stopped()
        line = self._held("H", "its change conflicts with issue_A's, issue_P's, issue_B's, "
                               "already on the line", "(conflicts in shared.txt)",
                          "`Conflicts with: A, P, B`")
        for other in ("issue_K0", "issue_K1", "issue_J"):
            self.assertNotIn(other, line)
        self._complete("A", "K0", "P", "B", "K1", "H", "J", "L")
        self.assertEqual(self.holds, {"H": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    # -- a branch that clashes with the base itself still stops the run ---------------------

    def test_a_branch_that_also_clashes_with_the_base_itself_still_stops_the_run(self):
        # Case (1)'s shape on a nine-line shared.txt: A changes line 2 and Y lines 2 and 8.
        # Once Y has published, main changes line 8 too. So Y clashes with A on the line, but
        # also with main itself, which no bundle's rebuild can settle: that is the line's
        # failure, and the fold stops the run as before. Pins the rule's first condition —
        # judged on the base as fetched, not on the commit the line was cut from, where Y
        # merges.
        nine = "".join(f"line {i}\n" for i in range(1, 10))
        self._on_base({"shared.txt": nine})
        self._plan("A", {"shared.txt": _edit(nine, l2="a")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(nine, l2="y", l8="y")}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self.after_publish["Y"] = lambda: self.fx._push_from_human(
            {"shared.txt": _edit(nine, l8="main's own")}, to="main")
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertIsNotNone(self._merges("origin/main", "Y"))         # the fixture's fact
        stop = [x for x in self.err.splitlines() if "STOPPING" in x]
        self.assertEqual(len(stop), 1, self.err)
        self.assertIn("flow: wave 1 did not integrate (issue_Y's branch origin/fix/Y does not "
                      "merge cleanly", stop[0])
        self.assertEqual([x for x in self.err.splitlines() if "held out of" in x], [], self.err)
        self.assertNotIn("Conflicts with: A", self.err)
        self.assertNotIn("issue_U", self.seen, self.err)
        self.assertEqual(self.results["U"], state.PLANNED, self.err)
        self.assertEqual(self.holds, {})
        self.assertEqual(self.rc, 1, self.err)


if __name__ == "__main__":
    unittest.main()
