"""A fold clash a moved base explains holds the bundle, with the fix for whoever can act (#749).

When ``main`` moves mid-run, a bundle built on its own base (#727) after the move carries
that move, and a line bundle cut from the old ``main`` may no longer merge onto it. The
fold then cannot merge the new bundle onto the line, and no trial on the base as it is now
can name the line bundle (#747's rule (d): each partner's head must merge onto the base
alone first), so before #749 the run stopped: ``STOPPING``, and bundles that had nothing to
do with the clash were never built. Now the fold judges the clash on the base the branch
actually holds (``git merge-base <head> <remote>/main``, ``integrate._held_by_move``):

* every line bundle merges onto that base: an ordinary overlap, worded as #747 words it —
  a ``main`` commit the branch does not hold is never blamed (cases (3a), (3c));
* a line bundle does not merge onto it, nor onto ``main`` now, and the move is what makes
  the branch clash with it — what of the branch's own files is at stake in its clash with
  that bundle as it is on the line (the lines it changed there, and the base lines it
  dropped, counted at each place) loses some, and gains none, once it is rebuilt on that
  base (one frame, the branch's own lines, so positions compare): it is stranded.
  The branch is held, the line bundle and ``<remote>/main`` are named, and the fix goes
  to that bundle's owner — rebuild its branch on the new ``<remote>/main`` — never to the
  held bundle's (case (1)); its ``Conflicts with`` partners wait for that rebuild, not for
  the held bundle's (case (3d)). Whatever else the held bundle's own change clashes with
  is found by #747's and #748's rules, run again on that base with the stranded bundle
  rebuilt, and held to their check that it explains the rest (the joint case here; #747's
  flipped case, in tests/test_flow_cross_wave_fold_holds.py); then its partners wait for
  both steps, the held bundle's rebuild on a base that holds those too (that case here,
  with a partner). One rule for one file and several: the move and the branch's own
  change in one file are held as when they are in two (cases (5), (6)), in one conflict
  block too (case (7)), and so are a deletion of the branch's own, or a move that deletes,
  in a hunk with the other (the three deletion cases, each beside its two-file twin);
  repeated lines change nothing (case (10)), as positions come from git's own hunks, nor
  a line dropped twice, one drop merged cleanly (placed where the other side changed it),
  nor a longer conflict marker (the marker-size case); a file one side deleted is the
  whole clash (the deleted-file case). Stakes that do not shrink so are not the move's: a
  line at stake only once the bundle is rebuilt stops the run (cases (8), (8b)), so does
  the same stake both times (the equal-stake case), and an unrelated move leaves the same
  lines at stake, with a bundle that still fits ``main``, which #747 names as an
  ordinary overlap (case (9));
* a line bundle does not merge onto it but does onto ``main`` now: ``main`` has moved on
  past the clash, and the step is the held bundle's — update its branch from
  ``<remote>/main`` (case (3b)) — which is what its ``Conflicts with`` partners wait for;
* anything else still stops the run: a branch that takes the move back out, so the move
  is not what it clashes with, in another file or in the file it clashes in (case (3c),
  its second and third tests), a rest of the clash no rule names (the three-bundle case),
  and a conflict the fold cannot place on the branch's lines, which the stop line names
  (the binary case). A line bundle the branch holds an older tip of is never named for
  that (case (2), a guard of #748's own-change rule).

These cases drive ``flow._drive_and_act`` through real folds and real base builds on the
``StackFoldGit`` fixture of tests/test_integrate_stack_bases.py (a bare ``origin`` and a
primary checkout), loaded by path exactly as tests/test_flow_same_wave_conflict.py does,
with the stubs of tests/test_flow_cross_wave_fold_holds.py: the build and sign-off leaves
are stubbed (``flow._drive_wave`` writes a ``patch.diff`` and accepts),
``flow._publish_bundle`` cuts and pushes each PR branch from the recorded stack-base tip,
and ``gh`` is answered OPEN with the branch's tip as the PR head. ``main`` is moved by a
scratch clone between steps of the run: after the run's n-th fold, or once a bundle has
published. The publisher is NOT a stub (a stub turns every fold into a dry-run). The exit
code is the one ``cli._flow`` gives the same run: ``cli._results_rc`` over the results and
holds.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run, and the hold cases fail on their assertions:
they end in ``wave N did not integrate … STOPPING`` with later bundles never built. Cases
(2), the second and third (3c), the three-bundle case, (8), (8b), (9) and the
equal-stake case are guards, green either way; (8b) is the one a rule that held on any
line leaving the set fails, and the equal-stake case the one a rule that held on equal
stakes fails.
Each ``_merges`` call states a fact of the fixture, tried by plain git in the scratch clone
after the run; what the run did is read from its results, holds and stderr.

The stakes are read in one frame for both trials (``integrate._stakes``): three line diffs,
each run once, with the diff algorithm the merge uses. So a shape git lines up one way from
the old base and another way from the new one is held as its two-file twin is (case (11)),
a line that looks like a conflict marker is text (case (12)), and the frame follows the
repository's ``diff.algorithm`` (cases (13a), (13b)); a trial with two merge bases is not
judged, and its stop names the file (case (15)). ``StakeFrame`` calls the stake function on
commits made with git's plumbing: case (13b), (15)'s criss-cross, and (14), a random probe of
shapes on repeated lines against their reading twins.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_cross_wave_stranded_holds
"""

from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import random
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Callable, Iterable
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import cli, flow, integrate, publish, state

_SPEC = importlib.util.spec_from_file_location(
    "stack_bases_fixture", Path(__file__).with_name("test_integrate_stack_bases.py"))
sb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sb)

TODAY = "2026-10-21"
NINE = "".join(f"line {i}\n" for i in range(1, 10))
# A ten-line file, each line long enough that rewriting six or seven of them takes it below
# git's rename-similarity threshold (the joint clash of tests/test_flow_cross_wave_joint_holds.py).
TEN = "".join(f"line {i} of the shared file, as the base has it\n" for i in range(1, 11))


def _edit(text: str, **lines: str | None) -> str:
    """``text`` with line ``n`` (``l<n>=...``) replaced, or dropped where it says None."""
    out = text.splitlines(keepends=True)
    for key, new in lines.items():
        out[int(key.removeprefix("l")) - 1] = "" if new is None else new + "\n"
    return "".join(out)


def _rewrite(text: str, who: str, lines: Iterable[int] = range(1, 8)) -> str:
    """``text`` (``TEN``) with ``lines`` (by default its first seven) rewritten by ``who``."""
    return _edit(text, **{f"l{i}": f"{who} rewrote line {i} entirely: something else altogether"
                          for i in lines})


class CrossWaveStrandedHolds(unittest.TestCase):

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
        self.moves: list[str] = []                       # each commit `main` moved by, in order
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
        """What `publish` does for an accepted bundle: cut ``fix/<iid>`` off ``cut_from``,
        make its change (deleting a file where it says None), commit it signed off, push
        it, and record it in publish.json and patch.diff."""
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

    def _move_main(self, files: dict[str, str]) -> Callable[[], None]:
        """A step that commits ``files`` on origin's ``main`` from the scratch clone (someone
        else's change landing mid-run), recording the commit in ``self.moves``."""
        return lambda: self.moves.append(self.fx._push_from_human(files, to="main"))

    def _drop_from_main(self, name: str) -> Callable[[], None]:
        """A step that deletes ``name`` on origin's ``main`` (``StackFoldGit._push_from_human``
        cannot delete a file), recording the commit in ``self.moves``."""
        def step() -> None:
            human = self.fx.human
            sb._git(human, "fetch", "-q", "origin")
            sb._git(human, "checkout", "-q", "-B", "scratch", "origin/main")
            sb._git(human, "rm", "-q", name)
            sb._git(human, "commit", "-q", "-s", "-m", f"drop {name} on main")
            sb._git(human, "push", "-q", "origin", "HEAD:refs/heads/main")
            self.moves.append(sb._git(human, "rev-parse", "HEAD").strip())
        return step

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

    def _run(self, ids: list[str]) -> None:
        """One stack-mode run asked for ``ids``, driving all of them."""
        self.line = integrate.integration_branch(self.cfg, "main", ids)
        self.holds: dict[str, str] = {}
        # What the in-run folds held, as the flow passes it in (#674 ``held_out``: name →
        # (partners, files); #749 ``moved``: name → who can act) — absent before the fix.
        self.held_out: dict = {}
        self.moved: dict = {}
        real_fold = integrate.fold
        folds = [0]

        def fold(*a, **kw):
            if kw.get("held_out") is not None:     # filled in place: keep the flow's dicts
                self.held_out = kw["held_out"]
                self.moved = kw["moved"] if kw.get("moved") is not None else {}
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
                self.cfg, [self.cfg.bundle(i) for i in ids], do_publish=True, do_act=False,
                by="T", today=TODAY, batch=ids, holds=self.holds)
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

    def _report(self, iid: str, *parts: str) -> str:
        """ONE end-of-run stderr line says ``issue_<iid>`` was held out of the line, with each
        of ``parts``. Returns that line."""
        lines = [x for x in self.err.splitlines()
                 if x.startswith(f"flow: issue_{iid} was held out of this run's integration "
                                 f"line — ")]
        self.assertEqual(len(lines), 1, self.err)
        for part in parts:
            self.assertIn(part, lines[0])
        return lines[0]

    def _none_of(self, text: str, *wrong: str) -> None:
        for w in wrong:
            self.assertNotIn(w, text)

    def _not_stopped(self) -> None:
        self.assertNotIn("did not integrate", self.err)
        self.assertNotIn("STOPPING", self.err)

    def _stopped(self, k: int, iid: str) -> None:
        """The wave-``k`` fold stopped the run on ``issue_<iid>``'s branch, holding nothing,
        and named no stranded bundle nor any step for one."""
        self.assertIn(f"wave {k} did not integrate (issue_{iid}'s branch", self.err)
        self.assertIn("STOPPING", self.err)
        self._none_of(self.err, f"issue_{iid} held out of the integration fold",
                      f"issue_{iid} was held", "rebuild issue_A's branch", "branch holds")
        self.assertEqual(self.holds, {})
        self.assertEqual(self.rc, 1, self.err)

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

    def _on_main(self, iid: str, *, mains: bool = False) -> str:
        """``iid``'s branch rebuilt on origin's ``main`` as it is now — main with the branch
        merged in, the branch's side winning every clash, or with ``mains`` main's side: two
        of the ways its owner's rebuild could go. A file one side deleted, which no hunk
        settles, is settled the same way: that side's file, or none. Pushed, once the run is
        over, as ``fix/<name>`` so :func:`_merges` can try it; returns that name."""
        human = self.fx.human
        name = f"{iid}-on-main" + ("-mains" if mains else "")
        side = "ours" if mains else "theirs"
        sb._git(human, "fetch", "-q", "origin")
        sb._git(human, "checkout", "-q", "-B", "rebuilt", "origin/main")
        if sb._run(human, "merge", "-q", "--no-ff", "--no-edit", "-X", side,
                   f"origin/fix/{iid}").returncode != 0:
            for path in sb._git(human, "diff", "--name-only", "--diff-filter=U").split():
                if sb._run(human, "checkout", f"--{side}", "--", path).returncode == 0:
                    sb._git(human, "add", "--", path)
                else:
                    sb._git(human, "rm", "-q", "--", path)
            sb._git(human, "commit", "-q", "--no-edit")
        sb._git(human, "push", "-q", "origin", f"HEAD:refs/heads/fix/{name}")
        sb._git(human, "checkout", "-q", "--detach", "origin/main")
        return name

    def _rebuilt(self, iid: str, *, on: str) -> str:
        """``iid``'s branch rebuilt on ``fix/<on>``, as its owner is told to: that branch with
        ``iid``'s merged in, ``iid``'s side winning every clash. Pushed, once the run is
        over, as ``fix/<iid>-on-<on>`` so :func:`_merges` can try it; returns that name."""
        human, name = self.fx.human, f"{iid}-on-{on}"
        sb._git(human, "fetch", "-q", "origin")
        sb._git(human, "checkout", "-q", "-B", "rebuilt", f"origin/fix/{on}")
        sb._git(human, "merge", "-q", "--no-ff", "--no-edit", "-X", "theirs",
                f"origin/fix/{iid}")
        sb._git(human, "push", "-q", "origin", f"HEAD:refs/heads/fix/{name}")
        sb._git(human, "checkout", "-q", "--detach", "origin/main")
        return name

    def _diff3(self, onto: str, iid: str, path: str = "shared.txt") -> str:
        """``path`` as git leaves it, in its diff3 conflict style, merging ``iid``'s branch
        onto ``onto`` — a fact of the fixture, tried in the scratch clone."""
        human = self.fx.human
        sb._git(human, "fetch", "-q", "origin")
        sb._git(human, "checkout", "-q", "--detach", onto)
        try:
            sb._run(human, "-c", "merge.conflictStyle=diff3", "merge", "-q", "--no-ff",
                    "--no-edit", "-m", "trial", f"origin/fix/{iid}")
            return (human / path).read_text(encoding="utf-8")
        finally:
            sb._run(human, "reset", "-q", "--hard")
            sb._git(human, "checkout", "-q", "--detach", "origin/main")

    # -- (1) a line bundle a moved base strands -----------------------------------------------

    def _stranded_run(self, *, with_x: bool) -> None:
        """A adds a.txt (wave 0). After wave 0's fold, main gets an a.txt of its own, so A's
        branch, on the line, no longer merges onto main. W depends on Z, so its own base is
        built in wave 1 on the moved main: W's branch carries main's a.txt and clashes with A
        on the line, though W's own change (w.txt) has nothing to do with A. V depends on W,
        so a fold runs after wave 1. S is `Stacks on: R` — cut from the line, it holds no
        part of the move — and T, after it, is built after that fold. With ``with_x``, X
        depends on T and declares `Conflicts with: W`."""
        self._plan("A", {"a.txt": "a\n"})
        self._plan("R", {"r.txt": "r\n"})
        self._plan("Z", {"z.txt": "z\n"})
        self._plan("S", {"s.txt": "s\n"}, stacks_on="R")
        self._plan("W", {"w.txt": "w\n"}, depends_on="Z")
        self._plan("T", {"t.txt": "t\n"}, depends_on="S")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        ids = ["A", "R", "Z", "S", "W", "T", "V"]
        if with_x:
            self._plan("X", {"x.txt": "x\n"}, depends_on="T", conflicts_with="W")
            ids.append("X")
        self.after_fold[1] = self._move_main({"a.txt": "main's own\n"})
        self._run(ids)

        # W's base holds the moved main (bases are not pinned to the run's start); A's
        # branch does not merge onto main now, W's does, and W merges after A rebuilt there,
        # whichever side of a.txt A's owner keeps.
        self.assertTrue(self.fx._ancestor(self.moves[0], self.seen["issue_W"][1]))
        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("W")))
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "W"))
        self.assertIsNone(self._merges("origin/main", self._on_main("A"), "W"))
        self.assertIsNone(self._merges("origin/main", self._on_main("A", mains=True), "W"))

    def test_a_line_bundle_a_moved_base_strands_gets_the_fix_not_the_held_bundle(self):
        # Before: wave 1's fold stopped the run on W (`STOPPING`), and T was never built.
        self._stranded_run(with_x=False)

        self._not_stopped()
        line = self._held("W", "issue_A's branch, already on the line from an earlier wave, "
                               "does not merge cleanly onto the origin/main issue_W's branch "
                               "holds: origin/main moved since it was cut, and issue_W's own "
                               "change does not clash with it", "(conflicts in a.txt)",
                          "rebuild issue_A's branch on the new origin/main",
                          "bundles that depend on issue_W or are its `Conflicts with` partners "
                          "are held this run")
        end = self._report("W", "To fold issue_W, rebuild issue_A's branch on the new "
                                "origin/main, then re-run.")
        self._none_of(line + end, "its change", "rebuild issue_W", "update issue_W",
                      "Conflicts with: A", "issue_R", "issue_Z", "issue_S", "issue_T",
                      "depend on it", "To fold it")
        self.assertEqual(len([x for x in self.err.splitlines()
                              if x.startswith("flow: issue_V skipped — prerequisite(s) not "
                                              "ready (W)")]), 1, self.err)
        self.assertNotIn("issue_V", self.seen, self.err)
        self.assertEqual(self.results["V"], state.PLANNED, self.err)
        self._complete("A", "R", "Z", "S", "W", "T")              # T is built after the fold
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)            # V is left PLANNED, with no hold

    # -- (2) a prerequisite whose branch moved on is not named --------------------------------

    def test_a_prerequisite_whose_branch_moved_on_is_not_named(self):
        # A guard (green before #749 too): K is Y's prerequisite, so Y's base holds K's
        # branch. After Y publishes, K's owner pushes a fixup that changes only k.txt — a
        # fast-forward the next fold takes (#633). Y's clash is with N alone, on line 2;
        # what Y holds of K, an older tip of it, is no clash. So Y is held naming N only,
        # and no K rebuild is proposed.
        self._on_base({"shared.txt": NINE})
        self._plan("K", {"k.txt": "k\n"})
        self._plan("N", {"shared.txt": _edit(NINE, l2="n")})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(NINE, l2="y")}, depends_on="K")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        fixup: list[str] = []
        self.after_publish["Y"] = lambda: fixup.append(self.fx._push_from_human(
            {"k.txt": "k's fixup\n"}, to="fix/K", off="origin/fix/K"))
        self._run(["K", "N", "W", "Y", "V", "U"])

        self.assertEqual(self._head("K"), fixup[0])                    # the fixture's facts
        self.assertTrue(self.fx._ancestor(f"{fixup[0]}~1", self._head("Y")))
        self.assertFalse(self.fx._ancestor(fixup[0], self._head("Y")))
        self.assertTrue(self.fx._ancestor(fixup[0], self.fx._tip(self.line)))
        self.assertIsNone(self._merges("origin/main", "K", "Y"))
        self.assertEqual(self._merges("origin/main", "N", "Y"), 1)
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_N's, already on the line from "
                               "an earlier wave (conflicts in shared.txt)")
        end = self._report("Y", "Proposed, for you to confirm: declare `Conflicts with: N` in "
                                "issue_Y's brief, then rebuild issue_Y on a base that holds "
                                "issue_N.")
        self._none_of(line + end, "issue_K", "conflicts with issue_K's",
                      "rebuild issue_Y's branch on issue_K's")
        self.assertNotIn("Conflicts with: K", self.err)
        self._complete("K", "N", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    # -- (3) the stranded check runs on the base the branch holds -----------------------------

    def test_main_moved_twice_a_partner_that_fits_the_base_the_branch_holds_is_an_overlap(self):
        # A changes lines 2 and 8 of shared.txt; Y, built on Q only, changes line 2. After
        # wave 0's fold an unrelated m.txt lands on main, so Y's base holds it. Once Y has
        # published, main changes line 8, so A's branch no longer merges onto main — in the
        # very file Y clashes with A in. But A merges onto the main Y holds: Y's clash with A
        # is its own change, on line 2. Before: STOPPING, U never built.
        self._on_base({"shared.txt": NINE})
        self._plan("A", {"shared.txt": _edit(NINE, l2="a", l8="a")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(NINE, l2="y")}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self.after_fold[1] = self._move_main({"m.txt": "main's own\n"})
        self.after_publish["Y"] = self._move_main({"shared.txt": _edit(NINE, l8="main's own")})
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("Y")))   # the facts
        self.assertFalse(self.fx._ancestor(self.moves[1], self._head("Y")))
        self.assertIsNone(self._merges(self.moves[0], "A"))    # onto the main Y holds: clean
        self.assertEqual(self._merges("origin/main", "A"), 0)  # onto main now: not
        self.assertIsNone(self._merges("origin/main", "Y"))
        self.assertEqual(self._merges(self.moves[0], "A", "Y"), 1)
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line from "
                               "an earlier wave (conflicts in shared.txt)")
        end = self._report("Y", "Proposed, for you to confirm: declare `Conflicts with: A` in "
                                "issue_Y's brief, then rebuild issue_Y on a base that holds "
                                "issue_A.")
        self._none_of(line + end, "rebuild issue_A's branch on the new origin/main",
                      "does not merge cleanly", "branch holds")
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def _undone_run(self, *, with_x: bool) -> None:
        """A adds a.txt. After wave 0's fold, main gets an a.txt of its own; V and Y, built on
        bases of their own in wave 1, hold that main, and neither touches a.txt. Once both
        have published, main deletes its a.txt again: A's branch merges onto main as it is
        now, but V's and Y's still carry the a.txt main dropped. S is `Stacks on: R` — cut
        from the line — and T, after it, is built after the fold that meets V and Y; U
        depends on V. With ``with_x``, X declares `Conflicts with: V`, so it builds after V
        and is reached after that fold."""
        self._plan("A", {"a.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("R", {"r.txt": "r\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("S", {"s.txt": "s\n"}, stacks_on="R")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("Y", {"y.txt": "y\n"}, depends_on="Q")
        self._plan("T", {"t.txt": "t\n"}, depends_on="S")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        ids = ["A", "Q", "R", "W", "S", "V", "Y", "T", "U"]
        if with_x:
            self._plan("X", {"x.txt": "x\n"}, conflicts_with="V")
            ids.append("X")
        self.after_fold[1] = self._move_main({"a.txt": "main's own\n"})
        self.after_publish["Y"] = self._drop_from_main("a.txt")
        self._run(ids)

        for iid in ("V", "Y"):                                          # the fixture's facts
            self.assertTrue(self.fx._ancestor(self.moves[0], self._head(iid)), iid)
            self.assertFalse(self.fx._ancestor(self.moves[1], self._head(iid)), iid)
            self.assertIsNone(self._merges("origin/main", iid), iid)
        self.assertEqual(self._merges(self.moves[0], "A"), 0)   # not onto the main they hold
        self.assertIsNone(self._merges("origin/main", "A"))     # onto main as it is now: clean

    def test_main_undid_the_commit_the_branches_clash_on_so_each_updates_from_main(self):
        # V's and Y's branches carry the a.txt main dropped again (`_undone_run`). That clash
        # is neither their own change nor A's owner's to fix: each is told to update its
        # branch from origin/main, and none to declare `Conflicts with: A`. Before:
        # STOPPING on V.
        self._undone_run(with_x=False)

        self._not_stopped()
        for iid in ("V", "Y"):
            line = self._held(iid, "issue_A's branch, already on the line from an earlier "
                                   "wave, does not merge cleanly onto the origin/main "
                                   f"issue_{iid}'s branch holds, but does onto origin/main as "
                                   "it is now", "(conflicts in a.txt)",
                              f"update issue_{iid}'s branch from origin/main")
            end = self._report(iid, f"To fold issue_{iid}, update issue_{iid}'s branch from "
                                    "origin/main, then re-run.")
            self._none_of(line + end, "its change", "rebuild issue_A's branch")
        self.assertNotIn("Conflicts with: A", self.err)
        self.fx._update_branch("Y")                       # the step works: Y then merges
        self.assertIsNone(self._merges(f"origin/{self.line}", "Y"))
        self.assertNotIn("issue_U", self.seen, self.err)
        self._complete("A", "Q", "R", "W", "S", "V", "Y", "T")
        self.assertEqual(self.holds, {"V": "conflict", "Y": "conflict"})
        self.assertEqual(self.rc, 1, self.err)               # U is left PLANNED, with no hold

    def test_a_partner_a_main_commit_the_branch_does_not_hold_strands_is_an_overlap(self):
        # A adds a.txt and changes shared.txt; Y, built on Q only, changes shared.txt too.
        # Once Y has published, main gets an a.txt of its own, so A's branch no longer merges
        # onto main. Y's branch holds no part of that move: its clash with A is their two
        # changes to shared.txt, which A's rebuild on the new main leaves standing. So Y's
        # owner gets the `Conflicts with: A` proposal, and A's owner is not told to rebuild
        # for Y. Before: STOPPING, U never built.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"a.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self.after_publish["Y"] = self._move_main({"a.txt": "main's own\n"})
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertFalse(self.fx._ancestor(self.moves[0], self._head("Y")))  # the facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self.assertEqual(self._merges("origin/main", self._on_main("A"), "Y"), 1)
        self._not_stopped()
        line = self._held("Y", "its change conflicts with issue_A's, already on the line from "
                               "an earlier wave (conflicts in shared.txt)")
        end = self._report("Y", "Proposed, for you to confirm: declare `Conflicts with: A` in "
                                "issue_Y's brief, then rebuild issue_Y on a base that holds "
                                "issue_A.")
        self._none_of(line + end, "rebuild issue_A's branch", "does not merge cleanly",
                      "branch holds")
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_branch_that_takes_the_move_back_out_still_stops_and_strands_no_one(self):
        # A guard (green before #749 too). A adds x.txt and changes shared.txt. After wave 0's
        # fold, main gets an x.txt of its own, so A's branch no longer merges onto main. Y,
        # built in wave 1 on that main, deletes the x.txt main added and changes shared.txt,
        # as A did: it holds the move but takes it back out, so it clashes with A only in
        # shared.txt, not in the x.txt A fails on main in. The move strands A, but not in
        # this clash: A is not called stranded for Y, and the run stops on Y, as before. V
        # is `Stacks on: W` (cut from the line), so Y's is the only branch holding the move.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"x.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"x.txt": None, "shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self.after_fold[1] = self._move_main({"x.txt": "main's own\n"})
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("Y")))   # the facts
        self.assertFalse(self.fx._ancestor(self.moves[0], self._head("V")))
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self._stopped(1, "Y")
        self.assertIn("(conflicts in shared.txt)", self.err)
        self.assertEqual(self.results["U"], state.PLANNED, self.err)

    def test_a_branch_that_takes_the_move_back_out_in_the_file_it_clashes_in_still_stops(self):
        # A guard (green before #749 too), the same as the last case in one file: A changes
        # lines 2 and 8 of shared.txt. After wave 0's fold, main changes line 8, so A's branch
        # no longer merges onto main. Y, built in wave 1 on that main, changes line 2 and puts
        # line 8 back as it was: it holds the move but takes it back out, so its clash with A
        # is line 2 alone, its own change, which A's rebuild on main leaves standing however
        # A's owner settles line 8. That A does not fit main is not what Y clashes with: A is
        # not called stranded for Y, and the run stops on Y, as before (Y's clash is with a
        # bundle that does not fit the base Y holds, so not the ordinary overlap of (3a)).
        self._on_base({"shared.txt": NINE})
        self._plan("A", {"shared.txt": _edit(NINE, l2="a", l8="a")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": _edit(NINE, l2="y")}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self.after_fold[1] = self._move_main({"shared.txt": _edit(NINE, l8="main's own")})
        self._run(["A", "Q", "W", "Y", "V", "U"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("Y")))   # the facts
        self.assertFalse(self.fx._ancestor(self.moves[0], self._head("V")))
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        self.assertEqual(self._merges("origin/main", self._on_main("A"), "Y"), 1)
        self.assertEqual(self._merges("origin/main", self._on_main("A", mains=True), "Y"), 1)
        self._stopped(1, "Y")
        self.assertIn("(conflicts in shared.txt)", self.err)
        self.assertEqual(self.results["U"], state.PLANNED, self.err)

    def test_a_conflicts_with_partner_of_a_stranded_hold_waits_for_the_partner_rebuild(self):
        # Case (1) plus X, which depends on T and declares `Conflicts with: W`, so it is
        # reached after the fold that holds W. X is held with W's reason and the fix for A's
        # owner: not told that W's change clashes, nor to wait for W to be rebuilt. Before:
        # STOPPING, and X was never reached.
        self._stranded_run(with_x=True)

        self._not_stopped()
        self._held("W", "rebuild issue_A's branch on the new origin/main")
        why = [x for x in self.err.splitlines() if x.startswith("flow: issue_X held — ")]
        self.assertEqual(len(why), 1, self.err)
        for part in ("it `Conflicts with` issue_W, which this run's fold held out of the line "
                     "(issue_A's branch, already on the line, does not merge cleanly onto the "
                     "origin/main issue_W's branch holds",
                     "To build it, wait until issue_A's branch is rebuilt on the new "
                     "origin/main, and issue_W's PR merges into main (org/repo), then re-run."):
            self.assertIn(part, why[0])
        self._none_of(why[0], "its change", "issue_W is rebuilt", "a base that holds issue_A",
                      "update issue_W")
        self.assertNotIn("issue_X", self.seen, self.err)
        self.assertEqual(self.results["X"], state.PLANNED, self.err)
        self._complete("A", "R", "Z", "S", "W", "T")
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)          # V and X are left PLANNED, with no hold

    def test_a_conflicts_with_partner_of_a_past_hold_waits_for_the_branch_update(self):
        # Case (3b) plus X, which declares `Conflicts with: V`, so it is reached after the
        # fold that holds V. X is held with V's reason and V's own step: it waits until V's
        # branch is updated from origin/main — not for A's rebuild, nor for V to be rebuilt
        # on a base that holds A — and it is not told that V's change clashes. Before:
        # STOPPING on V, and X was never reached.
        self._undone_run(with_x=True)

        self._not_stopped()
        self._held("V", "update issue_V's branch from origin/main")
        why = [x for x in self.err.splitlines() if x.startswith("flow: issue_X held — ")]
        self.assertEqual(len(why), 1, self.err)
        for part in ("it `Conflicts with` issue_V, which this run's fold held out of the line "
                     "(issue_A's branch, already on the line, does not merge cleanly onto the "
                     "origin/main issue_V's branch holds, but does onto origin/main as it is "
                     "now: origin/main has moved on since issue_V's branch was built), so no "
                     "line of this run holds that work",
                     "To build it, wait until issue_V's branch is updated from origin/main, "
                     "and issue_V's PR merges into main (org/repo), then re-run."):
            self.assertIn(part, why[0])
        self._none_of(why[0], "its change", "rebuild issue_A's branch", "issue_V is rebuilt",
                      "a base that holds", "Conflicts with: A", "issue_Y")
        self.fx._update_branch("V")                 # what X waits for works: V then merges
        self.assertIsNone(self._merges(f"origin/{self.line}", "V"))
        self.assertNotIn("issue_X", self.seen, self.err)
        self.assertEqual(self.results["X"], state.PLANNED, self.err)
        self._complete("A", "Q", "R", "W", "S", "V", "Y", "T")
        self.assertEqual(self.holds, {"V": "conflict", "Y": "conflict"})
        self.assertEqual(self.rc, 1, self.err)          # U and X are left PLANNED, with no hold

    def test_a_conflicts_with_partner_of_a_stranded_hold_with_an_own_clash_waits_for_both(self):
        # #747's flipped case (tests/test_flow_cross_wave_fold_holds.py) plus Z, which
        # declares `Conflicts with: Y`, so it is reached after the fold that holds Y. A adds
        # a.txt and changes shared.txt. After wave 0's fold, main gets an a.txt of its own; Y,
        # built in wave 1 on that main, changes shared.txt too: the move strands A (a.txt),
        # and Y's own change also clashes with A's (shared.txt), so A's rebuild alone does
        # not fold Y. Z waits for both steps — A's branch rebuilt on the new main, and Y on a
        # base that holds A — and then for Y's PR. V is `Stacks on: W` (cut from the line, so
        # it holds A), and U, after it, is built. Before: STOPPING, and Z was never reached.
        self._on_base({"shared.txt": "x\n"})
        self._plan("A", {"a.txt": "a\n", "shared.txt": "a\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("W", {"w.txt": "w\n"})
        self._plan("Y", {"shared.txt": "y\n"}, depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, stacks_on="W")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self._plan("Z", {"z.txt": "z\n"}, conflicts_with="Y")
        self.after_fold[1] = self._move_main({"a.txt": "main's own\n"})
        self._run(["A", "Q", "W", "Y", "V", "U", "Z"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("Y")))   # the facts
        self.assertTrue(self.fx._ancestor(self._head("A"), self._head("V")))
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "Y"))
        rebuilt = self._on_main("A")
        self.assertEqual(self._merges("origin/main", rebuilt, "Y"), 1)   # one step is not enough
        both = self._rebuilt("Y", on=rebuilt)                            # both steps taken
        self.assertIsNone(self._merges("origin/main", rebuilt, "Q", "W", "V", both))
        self._not_stopped()
        self._held("Y", "rebuild issue_A's branch on the new origin/main",
                   "; and issue_Y's own change also conflicts with issue_A's")
        why = [x for x in self.err.splitlines() if x.startswith("flow: issue_Z held — ")]
        self.assertEqual(len(why), 1, self.err)
        for part in ("it `Conflicts with` issue_Y, which this run's fold held out of the line "
                     "(issue_A's branch, already on the line, does not merge cleanly onto the "
                     "origin/main issue_Y's branch holds: origin/main moved since it was cut; "
                     "and issue_Y's own change also conflicts with issue_A's, already on the "
                     "line), so no line of this run holds that work",
                     "To build it, wait until issue_A's branch is rebuilt on the new "
                     "origin/main, issue_Y is rebuilt on a base that holds issue_A, and "
                     "issue_Y's PR merges into main (org/repo), then re-run."):
            self.assertIn(part, why[0])
        self._none_of(why[0], "its change", "update issue_Y")
        self.assertNotIn("issue_Z", self.seen, self.err)
        self.assertEqual(self.results["Z"], state.PLANNED, self.err)
        self._complete("A", "Q", "W", "Y", "V", "U")
        self.assertEqual(self.holds, {"Y": "conflict"})
        self.assertEqual(self.rc, 1, self.err)                 # Z is left PLANNED, with no hold

    # -- a stranded partner beside clashes of the branch's own change -------------------------

    def _beside_run(self, joint: dict[str, dict[str, str | None]]) -> None:
        """A adds a.txt; B sets b.txt; the bundles of ``joint`` (wave 0, before Z) make a
        clash with W's last line of shared.txt only together; X adds x.txt. After wave 0's
        fold, main gets an a.txt of its own. W depends on Z, so its own base is built in wave
        1 on that main: W carries main's a.txt (a clash with A that is the move's), and its
        own change sets b.txt (a clash with B) and changes shared.txt's last line. V depends
        on W. Y is `Stacks on: X` — cut from the line, after W in the fold — and T, after it,
        is built after the fold that meets W."""
        self._on_base({"shared.txt": TEN, "b.txt": "b0\n"})
        self._plan("A", {"a.txt": "a\n"})
        self._plan("B", {"b.txt": "B's\n"})
        for iid, files in joint.items():
            self._plan(iid, files)
        self._plan("X", {"x.txt": "x\n"})
        self._plan("Z", {"z.txt": "z\n"})
        self._plan("W", {"w.txt": "w\n", "b.txt": "W's\n",
                         "shared.txt": _edit(TEN, l10="line 10, as W has it")}, depends_on="Z")
        self._plan("Y", {"y.txt": "y\n"}, stacks_on="X")
        self._plan("T", {"t.txt": "t\n"}, depends_on="Y")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self.after_fold[1] = self._move_main({"a.txt": "main's own\n"})
        self._run(["A", "B", *joint, "X", "Z", "W", "Y", "T", "V"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("W")))   # the facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        self.assertIsNone(self._merges("origin/main", "W"))
        self.assertEqual(self._merges("origin/main", "B", "W"), 1)
        for iid in joint:
            self.assertIsNone(self._merges("origin/main", "Z", iid, "W"), iid)
        self.assertEqual(self._merges("origin/main", "Z", *joint, "W"), len(joint) + 1)

    def test_a_stranded_partner_beside_a_clash_two_line_bundles_make_together_names_all(self):
        # The move strands A (a.txt), W's own change clashes with B (b.txt), and with P and R
        # only together (shared.txt: P renames it, R rewrites most of it). A's rebuild alone
        # does not settle W's clash, so the hold names all four — A for its owner to rebuild,
        # and B, P and R for W's `Conflicts with` — and once A is rebuilt on main, the line
        # without B, P and R merges W, whichever side of a.txt A's owner keeps. Before:
        # STOPPING (A fails #747's rule (d)), T never built.
        self._beside_run({"P": {"shared.txt": None, "moved.txt": TEN},
                          "R": {"shared.txt": _rewrite(TEN, "R")}})

        for mains in (False, True):                                      # the fixture's facts
            rebuilt = self._on_main("A", mains=mains)
            self.assertIsNone(self._merges("origin/main", rebuilt, "X", "Z", "W"), mains)
            self.assertEqual(
                self._merges("origin/main", rebuilt, "B", "P", "R", "X", "Z", "W"), 6, mains)
        self._not_stopped()
        line = self._held("W", "issue_A's branch, already on the line from an earlier wave, "
                               "does not merge cleanly onto the origin/main issue_W's branch "
                               "holds: origin/main moved since it was cut; and issue_W's own "
                               "change also conflicts with issue_B's, issue_P's, issue_R's, "
                               "already on the line from an earlier wave",
                          "(conflicts in a.txt, b.txt, shared.txt)",
                          "rebuild issue_A's branch on the new origin/main")
        end = self._report("W", "To fold issue_W, rebuild issue_A's branch on the new "
                                "origin/main. Proposed, for you to confirm: declare "
                                "`Conflicts with: B, P, R` in issue_W's brief, then rebuild "
                                "issue_W on a base that holds issue_B, issue_P, issue_R.")
        self._none_of(line + end, "Conflicts with: A", "issue_X", "issue_Z", "issue_Y",
                      "update issue_W", "its change")
        self.assertEqual(self.results["V"], state.PLANNED, self.err)
        self._complete("A", "B", "P", "R", "X", "Z", "W", "Y", "T")      # T: after the fold
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)            # V is left PLANNED, with no hold

    def test_a_stranded_partner_beside_a_clash_three_line_bundles_make_still_stops(self):
        # A guard (green before #749 too): the last case, but the clash in shared.txt needs
        # three line bundles together (P renames it; R and S each rewrite three of its
        # lines, apart). #748 names no set of three, so nothing explains the rest of W's
        # clash once A is rebuilt and B taken off: W is not held naming A and B, whose steps
        # would not fold it. The run stops on W, as before.
        self._beside_run({"P": {"shared.txt": None, "moved.txt": TEN},
                          "R": {"shared.txt": _rewrite(TEN, "R", range(1, 4))},
                          "S": {"shared.txt": _rewrite(TEN, "S", range(5, 8))}})

        for pair in (("P", "R"), ("P", "S"), ("R", "S")):                # the fixture's facts
            self.assertIsNone(self._merges("origin/main", "Z", *pair, "W"), pair)
        self._stopped(1, "W")
        self.assertIn("(conflicts in a.txt, b.txt, shared.txt)", self.err)
        self.assertNotIn("Conflicts with: B", self.err)
        self.assertEqual(self.results["T"], state.PLANNED, self.err)

    # -- (5)-(10): one rule for a clash in one file and in several ----------------------------

    def _moved_run(self, base: dict[str, str], a: dict[str, str | None],
                   main: Callable[[], None], w: dict[str, str | None]) -> None:
        """Case (1)'s run on other files: A makes change ``a`` (wave 0), and after wave 0's
        fold ``main`` moves origin's ``main``. W depends on Z, so its own base is built in
        wave 1 on that main, and its branch makes change ``w`` on it. V depends on W, so a
        fold runs after wave 1. S is `Stacks on: R` — cut from the line, it holds no part of
        the move — and T, after it, is built after that fold."""
        self._on_base(base)
        self._plan("A", a)
        self._plan("R", {"r.txt": "r\n"})
        self._plan("Z", {"z.txt": "z\n"})
        self._plan("S", {"s.txt": "s\n"}, stacks_on="R")
        self._plan("W", w, depends_on="Z")
        self._plan("T", {"t.txt": "t\n"}, depends_on="S")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self.after_fold[1] = main
        self._run(["A", "R", "Z", "S", "W", "T", "V"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("W")))   # the facts
        self.assertIsNone(self._merges("origin/main", "W"))

    def _one_file_run(self, own: int, move: int) -> None:
        """A changes lines ``own`` and ``move`` of shared.txt (``NINE``); after wave 0's fold
        main changes line ``move``, so A's branch no longer merges onto main; W, built on
        that main, keeps main's line ``move`` and changes line ``own``."""
        self._moved_run(
            {"shared.txt": NINE},
            {"shared.txt": _edit(NINE, **{f"l{own}": f"A's line {own}",
                                          f"l{move}": f"A's line {move}"})},
            self._move_main({"shared.txt": _edit(NINE, **{f"l{move}": f"main's line {move}"})}),
            {"shared.txt": _edit(NINE, **{f"l{own}": f"W's line {own}",
                                          f"l{move}": f"main's line {move}"})})
        self.assertEqual(self._merges("origin/main", "A"), 0)

    def _two_file_run(self) -> None:
        """Case (5)'s two-file twin, the shape of #747's flipped case: A adds a.txt and
        changes line 2 of shared.txt; after wave 0's fold main adds an a.txt of its own; W,
        built on that main (so holding main's a.txt), changes line 2."""
        self._moved_run({"shared.txt": NINE},
                        {"a.txt": "a\n", "shared.txt": _edit(NINE, l2="A's line 2")},
                        self._move_main({"a.txt": "main's own\n"}),
                        {"shared.txt": _edit(NINE, l2="W's line 2")})
        self.assertEqual(self._merges("origin/main", "A"), 0)

    def _stranded_and_own(self, files: str) -> tuple[str, str]:
        """W was held for the move, which strands A, and for its own clash with A: the fix
        for A's owner, then the `Conflicts with: A` step for W's (``files``: what W's fold
        merge left conflicting). T was built after the fold; V, after W, was not. Returns
        W's hold line and end-of-run line."""
        self._not_stopped()
        line = self._held("W", "issue_A's branch, already on the line from an earlier wave, "
                               "does not merge cleanly onto the origin/main issue_W's branch "
                               "holds: origin/main moved since it was cut; and issue_W's own "
                               "change also conflicts with issue_A's, already on the line "
                               f"from an earlier wave (conflicts in {files}); rebuild "
                               "issue_A's branch on the new origin/main; bundles that depend "
                               "on issue_W or are its `Conflicts with` partners are held this "
                               "run.")
        end = self._report("W", "issue_W's own change also conflicts with issue_A's, already "
                                f"on the line ({files}). To fold issue_W, rebuild issue_A's "
                                "branch on the new origin/main. Proposed, for you to confirm: "
                                "declare `Conflicts with: A` in issue_W's brief, then rebuild "
                                "issue_W on a base that holds issue_A.")
        self._none_of(line + end, "issue_R", "issue_Z", "issue_S", "issue_T", "issue_V",
                      "update issue_W", "its change")
        self.assertNotIn("issue_V", self.seen, self.err)
        self.assertEqual(self.results["V"], state.PLANNED, self.err)
        self._complete("A", "R", "Z", "S", "W", "T")              # T is built after the fold
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 1, self.err)            # V is left PLANNED, with no hold
        return line, end

    def _steps_fold_w(self) -> str:
        """The hold's two steps, taken with plain git: A rebuilt on main, its side winning,
        does not fold W alone; with W rebuilt on that too, the line takes every bundle.
        Returns the name A's rebuild was pushed as (:func:`_on_main`)."""
        rebuilt = self._on_main("A")
        self.assertEqual(self._merges("origin/main", rebuilt, "W"), 1)
        both = self._rebuilt("W", on=rebuilt)
        self.assertIsNone(self._merges("origin/main", rebuilt, "R", "Z", "S", both))
        return rebuilt

    def test_a_one_file_clash_with_a_stranded_partner_holds_it_with_both_steps(self):
        # (5), the shape iteration 4 stopped on: A changes lines 2 and 8 of shared.txt; main
        # then changes line 8, so A's branch no longer merges onto main; W, built on that
        # main, keeps main's line 8 and changes line 2. As A is on the line, W's lines 2 and
        # 8 are at stake; once A is rebuilt on the main W holds, line 2 alone. The move's
        # line leaves, so A is stranded, and line 2 is W's own clash with A — the same hold
        # as its two-file twin (case (6)). Before: STOPPING, and T was never built.
        self._one_file_run(2, 8)

        self._stranded_and_own("shared.txt")
        self._steps_fold_w()

    def test_one_file_and_two_files_give_the_same_hold(self):
        # (6): case (5) beside its two-file twin, where the move is main's a.txt and W's own
        # clash is line 2 of shared.txt. The runs hold the same bundle, for the same
        # partners and who can act, with the same exit code and the same words, but for the
        # files named.
        seen = []
        for run, files in ((lambda: self._one_file_run(2, 8), "shared.txt"),
                           (self._two_file_run, "a.txt, shared.txt")):
            if seen:
                self.setUp()                              # a fresh repo and bundles each run
            run()
            line, end = self._stranded_and_own(files)
            seen.append((dict(self.holds), self.held_out.get("issue_W", ([], []))[0],
                         self.moved.get("issue_W"), self.rc,
                         line.replace(files, "…"), end.replace(files, "…")))
        self.assertEqual(seen[0], seen[1])
        # W's partner, and who can act: A's owner (stranded), and W's for its own clash.
        self.assertEqual(seen[0][1], ["issue_A"])
        self.assertEqual(tuple(seen[0][2]), ("origin/main", ["issue_A"], [], ["issue_A"]))

    def test_the_move_and_the_branch_s_own_change_in_one_conflict_block_hold_it(self):
        # (7): A changes lines 7 and 8; main then changes line 8; W keeps main's line 8 and
        # changes line 7. Git leaves one conflict block over lines 7-8 both as A is on the
        # line and once A is rebuilt on the main W holds: no file and no block drops out,
        # but the block shrinks — line 8 leaves the lines at stake — so A is stranded, and
        # line 7 is W's own clash. Before: STOPPING.
        self._one_file_run(7, 8)

        self._stranded_and_own("shared.txt")
        rebuilt = self._on_main("A")                                     # the fixture's facts
        for onto, base in (("origin/fix/A", "line 8"), (f"origin/fix/{rebuilt}", "main's line 8")):
            text = self._diff3(onto, "W")
            self.assertEqual(len([x for x in text.splitlines() if x.startswith("<<<<<<< ")]),
                             1, text)
            self.assertIn(f"\nline 7\n{base}\n=======\nW's line 7\nmain's line 8\n>>>>>>> ", text)
        both = self._rebuilt("W", on=rebuilt)
        self.assertIsNone(self._merges("origin/main", rebuilt, "R", "Z", "S", both))

    def test_a_rebuild_that_puts_a_new_line_at_stake_is_not_judged(self):
        # (8), a guard: A changes lines 2 and 5; main then changes line 5; W, built on that
        # main, puts line 5 back as the old main had it and changes line 2. As A is on the
        # line, only line 2 is at stake (W's line 5 is the old base's); once A is rebuilt on
        # the main W holds, line 5 is too (W changed it from main's, the rebuilt A has its
        # own). A rebuild that adds a line at stake does not show the move to be A's: the
        # run stops, as before.
        self._moved_run({"shared.txt": NINE},
                        {"shared.txt": _edit(NINE, l2="A's line 2", l5="A's line 5")},
                        self._move_main({"shared.txt": _edit(NINE, l5="main's line 5")}),
                        {"shared.txt": _edit(NINE, l2="W's line 2")})

        self.assertEqual(self._merges("origin/main", "A"), 0)            # the fixture's facts
        self.assertEqual(self._merges("origin/main", self._on_main("A"), "W"), 1)
        self._stopped(1, "W")
        self.assertIn("(conflicts in shared.txt)", self.err)
        self.assertEqual(self.results["T"], state.PLANNED, self.err)

    def test_a_line_that_leaves_while_another_joins_is_not_judged(self):
        # (8b), the guard a weaker rule fails: A changes lines 2, 5 and 8; main then changes
        # lines 5 and 8; W, built on that main, keeps main's line 8, puts line 5 back as the
        # old main had it, and changes line 2. As A is on the line, lines 2 and 8 are at
        # stake; once A is rebuilt, lines 2 and 5. Line 8 leaves but line 5 joins: not a
        # strict subset, so not judged, and the run stops with no fix for A's owner. A rule
        # that held whenever some line left would hold W here.
        self._moved_run(
            {"shared.txt": NINE},
            {"shared.txt": _edit(NINE, l2="A's line 2", l5="A's line 5", l8="A's line 8")},
            self._move_main({"shared.txt": _edit(NINE, l5="main's line 5",
                                                 l8="main's line 8")}),
            {"shared.txt": _edit(NINE, l2="W's line 2", l8="main's line 8")})

        self.assertEqual(self._merges("origin/main", "A"), 0)            # the fixture's facts
        self.assertEqual(self._merges("origin/main", self._on_main("A"), "W"), 1)
        self._stopped(1, "W")
        self.assertIn("(conflicts in shared.txt)", self.err)
        self.assertEqual(self.results["T"], state.PLANNED, self.err)

    def test_an_unrelated_move_that_leaves_the_same_lines_at_stake_strands_no_one(self):
        # (9), iteration 1's counterexample under the line rule: A changes line 2; main then
        # changes line 8, which nobody else touches; W, built on Q and that main, changes
        # line 2. Line 2 alone would be at stake as A is on the line and once A is rebuilt:
        # the move is no part of the clash. A still merges onto main, so no move is looked
        # for at all: #747's rule names A on the base as it is, an ordinary overlap — what
        # iteration 4 gave too — with W's own `Conflicts with: A` step, no fix for A's owner
        # and no BaseMove. V, after X, is built in W's wave, and U after the fold. No bundle
        # is cut from the line here (the other cases' S is), so none brings A back when
        # #747's check takes A off it.
        self._on_base({"shared.txt": NINE})
        self._plan("A", {"shared.txt": _edit(NINE, l2="A's line 2")})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("X", {"x.txt": "x\n"})
        self._plan("W", {"shared.txt": _edit(NINE, l2="W's line 2", l8="main's line 8")},
                   depends_on="Q")
        self._plan("V", {"v.txt": "v\n"}, depends_on="X")
        self._plan("U", {"u.txt": "u\n"}, depends_on="V")
        self.after_fold[1] = self._move_main({"shared.txt": _edit(NINE, l8="main's line 8")})
        self._run(["A", "Q", "X", "W", "V", "U"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("W")))   # the facts
        self.assertIsNone(self._merges("origin/main", "A"))
        self.assertIsNone(self._merges("origin/main", "W"))
        self.assertEqual(self._merges("origin/main", "A", "W"), 1)
        self.assertEqual(self._merges("origin/main", self._on_main("A"), "W"), 1)
        self._not_stopped()
        line = self._held("W", "its change conflicts with issue_A's, already on the line from "
                               "an earlier wave (conflicts in shared.txt)")
        end = self._report("W", "Proposed, for you to confirm: declare `Conflicts with: A` in "
                                "issue_W's brief, then rebuild issue_W on a base that holds "
                                "issue_A.")
        self._none_of(line + end, "rebuild issue_A's branch", "does not merge cleanly",
                      "branch holds", "origin/main")
        self.assertEqual(self.held_out.get("issue_W", ([], []))[0], ["issue_A"])
        self.assertEqual(self.moved, {})
        self._complete("A", "Q", "X", "W", "V", "U")
        self.assertEqual(self.holds, {"W": "conflict"})
        self.assertEqual(self.rc, 3, self.err)

    def test_repeated_lines_do_not_change_the_hold(self):
        # (10): case (5) on a file in which every changed line's text is elsewhere too: `}`
        # and blank lines between the edited lines 5 and 11, the old text and A's new text
        # in unchanged lines, and W's new line 5 is main's new line 11 and the file's line 1,
        # so W's version has it three times. Searching that version for a block's text would
        # put both blocks of the clash as A is on the line at line 1, and see no line leave;
        # positions taken from git's own hunks put them at lines 5 and 11. Same hold as (5).
        base = "".join(x + "\n" for x in ("    x = 3;", "}", "", "}", "    x = 1;", "}",
                                          "    x = 2;", "", "}", "", "    x = 1;", "}",
                                          "    x = 1;"))
        self._moved_run({"shared.txt": base},
                        {"shared.txt": _edit(base, l5="    x = 2;", l11="    x = 2;")},
                        self._move_main({"shared.txt": _edit(base, l11="    x = 3;")}),
                        {"shared.txt": _edit(base, l5="    x = 3;", l11="    x = 3;")})
        self.assertEqual(self._merges("origin/main", "A"), 0)

        self._stranded_and_own("shared.txt")
        self._steps_fold_w()

    def test_a_clash_with_a_file_one_side_deleted_is_placed_whole_and_held(self):
        # A file one side deleted has no conflict blocks, but it is no conflict the fold
        # cannot place: the whole file is the clash — the place W's deletion left, or every
        # line W changed. Main deletes f.txt, which A changed, and W, built on that main,
        # holds the deletion; then the other way round, A deletes f.txt and main changes
        # it. Either way f.txt leaves the clash once A is rebuilt: A is stranded, W's own
        # change (w.txt) clashes with nothing, as iteration 4 held it.
        moves = (("A changes it, main deletes it", {"f.txt": "A's f\n"},
                  lambda: self._drop_from_main("f.txt")),
                 ("A deletes it, main changes it", {"f.txt": None},
                  lambda: self._move_main({"f.txt": "main's f\n"})))
        for i, (how, a, move) in enumerate(moves):
            with self.subTest(how):
                if i:
                    self.setUp()                          # a fresh repo and bundles each run
                self._moved_run({"f.txt": "f\n"}, a, move(), {"w.txt": "w\n"})
                self.assertEqual(self._merges("origin/main", "A"), 0)

                self._not_stopped()
                line = self._held("W", "issue_A's branch, already on the line from an earlier "
                                       "wave, does not merge cleanly onto the origin/main "
                                       "issue_W's branch holds: origin/main moved since it was "
                                       "cut, and issue_W's own change does not clash with it "
                                       "(conflicts in f.txt); rebuild issue_A's branch on the "
                                       "new origin/main;")
                end = self._report("W", "To fold issue_W, rebuild issue_A's branch on the new "
                                        "origin/main, then re-run.")
                self._none_of(line + end, "its change", "Conflicts with: A", "update issue_W",
                              "could not be judged line by line")
                self.assertEqual(self.results["V"], state.PLANNED, self.err)
                self._complete("A", "R", "Z", "S", "W", "T")
                self.assertEqual(self.holds, {"W": "conflict"})
                self.assertEqual(self.rc, 1, self.err)

    def test_a_conflict_the_fold_cannot_place_stops_the_run_and_names_the_file(self):
        # Case (1) with a binary file: A adds logo.bin; after wave 0's fold main gets a
        # logo.bin of its own, which W, built on that main, holds. Git merges no lines of a
        # binary file, so the fold cannot judge W's clash with A line by line and does not
        # judge whether the move is part of it: the run stops, as before the fix, and the
        # stop line names the file and says its conflict could not be judged line by line.
        self._moved_run({"shared.txt": NINE}, {"logo.bin": "\0A's logo\n"},
                        self._move_main({"logo.bin": "\0main's logo\n"}), {"w.txt": "w\n"})
        self.assertEqual(self._merges("origin/main", "A"), 0)            # the fixture's facts

        self._stopped(1, "W")
        stop = [x for x in self.err.splitlines() if "STOPPING" in x]
        self.assertEqual(len(stop), 1, self.err)
        for part in ("wave 1 did not integrate (issue_W's branch", "(conflicts in logo.bin)",
                     "; the conflict in logo.bin could not be judged line by line (it is a "
                     "binary file), so the fold did not judge whether the moved base is "
                     "part of the clash); STOPPING"):
            self.assertIn(part, stop[0])
        self.assertEqual(self.results["T"], state.PLANNED, self.err)

    # -- deletions, equal stakes, a line dropped twice, longer conflict markers ---------------

    def _twins_hold_alike(self, one: Callable[[], None], two: Callable[[], None], *,
                          facts: Callable[[str], None]) -> None:
        """``one`` (a run whose clash is in shared.txt) and its two-file twin ``two`` (in
        a.txt and shared.txt) each hold W for the move, which strands A, and for its own
        clash with A (:func:`_stranded_and_own`), and the hold's two steps fold W
        (:func:`_steps_fold_w`); ``facts`` checks the one-file run's fixture, given the name
        A's rebuild was pushed as. The runs hold the same bundle, for the same partners and
        who can act, with the same exit code and the same words, but for the files named."""
        seen = []
        for run, files in ((one, "shared.txt"), (two, "a.txt, shared.txt")):
            if seen:
                self.setUp()                              # a fresh repo and bundles each run
            run()
            self.assertEqual(self._merges("origin/main", "A"), 0)       # the fixture's facts
            line, end = self._stranded_and_own(files)
            rebuilt = self._steps_fold_w()
            if not seen:
                facts(rebuilt)
            seen.append((dict(self.holds), self.held_out.get("issue_W", ([], []))[0],
                         self.moved.get("issue_W"), self.rc,
                         line.replace(files, "…"), end.replace(files, "…")))
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(seen[0][1], ["issue_A"])
        self.assertEqual(tuple(seen[0][2]), ("origin/main", ["issue_A"], [], ["issue_A"]))

    def _one_block(self, onto: str, base: list[str], head: list[str]) -> None:
        """Git leaves exactly one conflict block in shared.txt merging W's branch onto
        ``onto``, its base side ``base`` and W's side ``head`` — a fixture fact."""
        lines = self._diff3(onto, "W").splitlines()
        marks = [i for i, x in enumerate(lines) if x[:8] in ("<<<<<<< ", "||||||| ", "=======",
                                                             ">>>>>>> ")]
        self.assertEqual(len(marks), 4, lines)
        _start, mid, sep, end = marks
        self.assertEqual((lines[mid + 1:sep], lines[sep + 1:end]), (base, head), lines)

    def test_the_branch_s_own_deletion_beside_the_move_holds_as_it_does_in_two_files(self):
        # Case (7) with W's own change a deletion: A changes line 7; main then changes line
        # 7, so A's branch no longer merges onto main; W, built on that main, keeps main's
        # line 7 and deletes line 8. Git leaves one block over lines 7-8 as A is on the line,
        # and over main's line 7 and line 8 once A is rebuilt: W's diff from the old base is
        # one hunk, main's line 7 for lines 7-8, and from the main it holds only the drop of
        # line 8. That drop is at stake both times, counted at the same place (a hunk holds
        # each line it drops at every place from before its first line to after its last),
        # and main's line 7 only the first time: the move leaves the clash, and W's own drop
        # still clashes with A. Beside it, its two-file twin (main adds a.txt; A adds one and
        # changes line 7; W deletes line 8) is held the same way. Before: STOPPING, both runs
        # — and a stake that kept the drop apart from the line it shares a hunk with would
        # stop the one-file run alone, its stakes never comparing.
        def facts(rebuilt: str) -> None:
            self._one_block("origin/fix/A", ["line 7", "line 8"], ["main's line 7"])
            self._one_block(f"origin/fix/{rebuilt}", ["main's line 7", "line 8"],
                            ["main's line 7"])

        self._twins_hold_alike(
            lambda: self._moved_run(
                {"shared.txt": NINE}, {"shared.txt": _edit(NINE, l7="A's line 7")},
                self._move_main({"shared.txt": _edit(NINE, l7="main's line 7")}),
                {"shared.txt": _edit(NINE, l7="main's line 7", l8=None)}),
            lambda: self._moved_run(
                {"shared.txt": NINE},
                {"a.txt": "a\n", "shared.txt": _edit(NINE, l7="A's line 7")},
                self._move_main({"a.txt": "main's own\n"}),
                {"shared.txt": _edit(NINE, l8=None)}),
            facts=facts)

    def test_a_move_that_deletes_a_line_holds_as_it_does_in_two_files(self):
        # The move is a deletion: A changes line 7; main then deletes line 7, so A's branch no
        # longer merges onto main; W, built on that main, changes line 8. W's diff from the
        # old base is one hunk, its line 8 for lines 7-8, so two lines dropped; from the main
        # it holds a hunk of one line for one. W's line 8 is at stake both times, and the drop
        # of line 7 (main's, which W holds) only as A is on the line: the move leaves the
        # clash, and W's own line 8 still clashes with A's line 7, right before it. Its
        # two-file twin (main
        # deletes a.txt, which A changes, with line 7) is held the same way. Before:
        # STOPPING, both runs — and a stake that did not count the lines a hunk drops would
        # be the same both times in the one-file run, and stop it alone.
        def facts(rebuilt: str) -> None:
            self._one_block("origin/fix/A", ["line 7", "line 8"], ["W's line 8"])
            self._one_block(f"origin/fix/{rebuilt}", ["line 8"], ["W's line 8"])

        self._twins_hold_alike(
            lambda: self._moved_run(
                {"shared.txt": NINE}, {"shared.txt": _edit(NINE, l7="A's line 7")},
                self._move_main({"shared.txt": _edit(NINE, l7=None)}),
                {"shared.txt": _edit(NINE, l7=None, l8="W's line 8")}),
            lambda: self._moved_run(
                {"shared.txt": NINE, "a.txt": "a\n"},
                {"a.txt": "A's a\n", "shared.txt": _edit(NINE, l7="A's line 7")},
                self._drop_from_main("a.txt"),
                {"shared.txt": _edit(NINE, l8="W's line 8")}),
            facts=facts)

    def test_a_drop_beside_a_line_the_move_added_holds_as_it_does_in_two_files(self):
        # A hunk of one line for one drops a line too: A changes line 7; main then adds a
        # line after it, so A's branch no longer merges onto main; W, built on that main,
        # deletes line 7. W's diff from the old base is one hunk, main's new line for line 7
        # — the line it drops sits before that line or after it, which the hunk does not say
        # — and from the main it holds the drop of line 7 alone, before main's line. Counted
        # in the first hunk too, at each place it spans, the drop is at stake both times, and
        # main's line only the first time. Its two-file twin (main adds a.txt; A adds one and
        # changes line 7; W deletes line 7) is held the same way. Before: STOPPING, both
        # runs — and a stake that took a hunk of one line for one as dropping nothing, or
        # counted a drop only after a hunk's last line, would stop the one-file run alone.
        def facts(rebuilt: str) -> None:
            self._one_block("origin/fix/A", ["line 7"], ["main's line"])
            self._one_block(f"origin/fix/{rebuilt}", ["line 7", "main's line"], ["main's line"])

        self._twins_hold_alike(
            lambda: self._moved_run(
                {"shared.txt": NINE}, {"shared.txt": _edit(NINE, l7="A's line 7")},
                self._move_main({"shared.txt": _edit(NINE, l7="line 7\nmain's line")}),
                {"shared.txt": _edit(NINE, l7="main's line")}),
            lambda: self._moved_run(
                {"shared.txt": NINE},
                {"a.txt": "a\n", "shared.txt": _edit(NINE, l7="A's line 7")},
                self._move_main({"a.txt": "main's own\n"}),
                {"shared.txt": _edit(NINE, l7=None)}),
            facts=facts)

    def test_the_same_stake_before_and_after_the_rebuild_still_stops(self):
        # The stakes are equal, so not judged: A changes lines 2 and 8; main then changes line
        # 8, so A's branch no longer merges onto main; W, built on that main, changes line 2
        # and takes A's line 8. Line 8 is the same change on both sides as A is on the line
        # and once it is rebuilt, so git merges it cleanly both times, and line 2 alone is at
        # stake both times: the move is no part of W's clash with A. The run stops, with no
        # fix for A's owner. Unlike case (9), the fold gets this far: A does not merge onto
        # main, so the tie is tried. A rule that held on equal stakes would hold W here.
        self._moved_run(
            {"shared.txt": NINE},
            {"shared.txt": _edit(NINE, l2="A's line 2", l8="A's line 8")},
            self._move_main({"shared.txt": _edit(NINE, l8="main's line 8")}),
            {"shared.txt": _edit(NINE, l2="W's line 2", l8="A's line 8")})

        self.assertEqual(self._merges("origin/main", "A"), 0)            # the fixture's facts
        rebuilt = self._on_main("A")
        for onto in ("origin/fix/A", f"origin/fix/{rebuilt}"):
            self._one_block(onto, ["line 2"], ["W's line 2"])
        self._stopped(1, "W")
        self.assertIn("(conflicts in shared.txt)", self.err)
        self.assertEqual(self.results["T"], state.PLANNED, self.err)

    def test_a_line_the_branch_drops_twice_is_placed_where_the_other_side_changed_it(self):
        # Two drops alike: shared.txt is `a1 } a3 } a5 } a7 a8 a9`. A changes line 4 to
        # `} // A` and changes line 8; main then changes line 8, so A's branch no longer
        # merges onto main; W, built on that main, deletes both `}` of lines 4 and 6 and keeps
        # main's line 8. Git puts the drop of line 4 in a block (A changed that line) and
        # merges the drop of line 6 cleanly, and W's side cannot tell the two apart: both
        # drop a `}` after an `a` line. The side W is merged onto can: A changed line 4, not
        # line 6. So the clash is placed — the drop of line 4 and main's line 8 as A is on
        # the line, the drop alone once A is rebuilt — and held as case (5) is. Before:
        # STOPPING — and a placement that read W's side alone could not tell the two drops
        # apart, and stopped on a conflict it could not place.
        base = "".join(x + "\n" for x in ("a1", "}", "a3", "}", "a5", "}", "a7", "a8", "a9"))
        self._moved_run({"shared.txt": base},
                        {"shared.txt": _edit(base, l4="} // A", l8="A's a8")},
                        self._move_main({"shared.txt": _edit(base, l8="main's a8")}),
                        {"shared.txt": _edit(base, l4=None, l6=None, l8="main's a8")})
        self.assertEqual(self._merges("origin/main", "A"), 0)            # the fixture's facts
        text = self._diff3("origin/fix/A", "W")
        self.assertEqual(len([x for x in text.splitlines() if x.startswith("<<<<<<< ")]), 2,
                         text)
        self.assertIn("\na3\n<<<<<<< HEAD\n} // A\n||||||| ", text)
        self.assertIn("\n}\n=======\n>>>>>>> ", text)
        self.assertIn("\n>>>>>>> origin/fix/W\na5\na7\n", text)    # line 6's drop: merged

        self._stranded_and_own("shared.txt")
        self.assertNotIn("could not be judged line by line", self.err)
        self._steps_fold_w()

    def test_a_longer_conflict_marker_is_read_as_git_writes_it(self):
        # Case (5) with `shared.txt conflict-marker-size=9` in the base's .gitattributes: git
        # writes the file's conflict blocks with nine-character markers, and the fold reads
        # them so, as it reads seven by default. Held as case (5) is. Before: STOPPING — and
        # a reader of seven-character markers alone found no blocks, and stopped on a
        # conflict it could not place.
        self._moved_run(
            {"shared.txt": NINE, ".gitattributes": "shared.txt conflict-marker-size=9\n"},
            {"shared.txt": _edit(NINE, l2="A's line 2", l8="A's line 8")},
            self._move_main({"shared.txt": _edit(NINE, l8="main's line 8")}),
            {"shared.txt": _edit(NINE, l2="W's line 2", l8="main's line 8")})
        self.assertEqual(self._merges("origin/main", "A"), 0)            # the fixture's facts
        text = self._diff3("origin/fix/A", "W")
        self.assertEqual(len([x for x in text.splitlines() if x.startswith("<<<<<<<<< ")]), 2,
                         text)
        self.assertNotIn("\n<<<<<<< ", text)

        self._stranded_and_own("shared.txt")
        self.assertNotIn("could not be judged line by line", self.err)
        self._steps_fold_w()

    # -- (11)-(13a), (15): one reading of the branch's lines serves both trials ---------------

    def _heads(self, old: str, new: str, path: str = "shared.txt") -> list[str]:
        """The hunk headers of git's diff of ``path`` from ``old`` to ``new``, read as ``git
        merge`` reads it (histogram, no indent heuristic, no context) — a fixture fact,
        tried in the scratch clone."""
        sb._git(self.fx.human, "fetch", "-q", "origin")
        out = sb._git(self.fx.human, "diff", "-U0", "--no-color", "--no-indent-heuristic",
                      "--diff-algorithm=histogram", old, new, "--", path)
        return [x[:x.index(" @@") + 3] for x in out.splitlines() if x.startswith("@@ ")]

    def _repeated_run(self, *, unique: bool = False) -> None:
        """(11)'s shape, iteration 6's adversary's: shared.txt is `}`, `}`, `line 3` …
        `line 7` (with ``unique``: `line 1` … `line 7`); A changes line 2; after wave 0's
        fold main changes line 3, so A's branch no longer merges onto main; W, built on that
        main, keeps main's line 3 and changes line 1."""
        base = ("line 1\nline 2\n" if unique else "}\n}\n") + "".join(
            f"line {i}\n" for i in range(3, 8))
        self._moved_run({"shared.txt": base}, {"shared.txt": _edit(base, l2="A's line 2")},
                        self._move_main({"shared.txt": _edit(base, l3="main's line 3")}),
                        {"shared.txt": _edit(base, l1="W's line 1", l3="main's line 3")})

    def _repeated_twin(self) -> None:
        """(11)'s two-file twin: main adds a.txt; A adds one of its own and changes line 2 of
        the same shared.txt; W, built on that main, changes line 1."""
        base = "}\n}\n" + "".join(f"line {i}\n" for i in range(3, 8))
        self._moved_run({"shared.txt": base},
                        {"a.txt": "a\n", "shared.txt": _edit(base, l2="A's line 2")},
                        self._move_main({"a.txt": "main's own\n"}),
                        {"shared.txt": _edit(base, l1="W's line 1")})

    def _w_held(self, files: str) -> tuple:
        """What the run did with W (:func:`_stranded_and_own`, held with both steps, which
        fold it: :func:`_steps_fold_w`): holds, W's partners, who can act, exit code, and its
        hold and end-of-run lines."""
        line, end = self._stranded_and_own(files)
        self._steps_fold_w()
        return (dict(self.holds), self.held_out.get("issue_W", ([], []))[0],
                self.moved.get("issue_W"), self.rc, line, end)

    def test_repeated_lines_read_one_way_for_both_trials_hold_as_two_files_do(self):
        # (11), the shape iteration 6 stopped on. From the old base, git's diff reads W's
        # change as a new line before the two `}` and takes main's line 3 for the second `}`
        # and line 3; from the main W holds, as a one-line edit of line 1. A diff of its own
        # per trial put W's line 1 at stake only once A is rebuilt, so "after" gained a line
        # and the run stopped. The frame reads W's lines once, for both trials: W's line 1 is
        # at stake both times, main's line 3 only as A is on the line. Held as its two-file
        # twin is, and as the same shape with unique lines is, with both steps, which fold W.
        def facts(_rebuilt: str) -> None:
            old = f"{self.moves[0]}~1"                    # the main A was cut from
            self.assertEqual(self._heads(old, "origin/fix/W"),
                             ["@@ -0,0 +1 @@", "@@ -2,2 +3 @@"])
            self.assertEqual(self._heads(self.moves[0], "origin/fix/W"), ["@@ -1 +1 @@"])

        self._twins_hold_alike(self._repeated_run, self._repeated_twin, facts=facts)
        self.setUp()                                      # and its unique-lines version
        self._twins_hold_alike(lambda: self._repeated_run(unique=True), self._repeated_twin,
                               facts=lambda _rebuilt: None)

    def test_a_seven_character_underline_holds_as_an_eight_character_one_does(self):
        # (12): README.md has a Markdown heading `Install` underlined `=======`, seven
        # characters, as long as git's own conflict separator. A retitles it `Setup` /
        # `=====` and changes line 8; main then changes line 8, so A's branch no longer
        # merges onto main; W, built on that main, keeps main's line 8 and changes `Install`
        # to `Installing`. Git writes the underline into its conflict block's base side, just
        # before its separator, where a reader of git's conflict markers took it for the
        # separator and stopped (iteration 6: "could not be placed"). The frame reads no
        # markers: held as the same shape with an eight-character underline is.
        seen = []
        for rule in ("=======", "========"):
            if seen:
                self.setUp()                              # a fresh repo and bundles each run
            base = f"# Tool\n\nInstall\n{rule}\n\nRun it.\n\nline 8\nline 9\n"
            self._moved_run(
                {"README.md": base},
                {"README.md": _edit(base, l3="Setup", l4="=====", l8="A's line 8")},
                self._move_main({"README.md": _edit(base, l8="main's line 8")}),
                {"README.md": _edit(base, l3="Installing", l8="main's line 8")})
            self.assertEqual(self._merges("origin/main", "A"), 0)        # the fixture's facts
            self.assertIn(f"\nInstall\n{rule}\n=======\nInstalling\n{rule}\n>>>>>>> ",
                          self._diff3("origin/fix/A", "W", "README.md"))
            seen.append(self._w_held("README.md"))
            self.assertNotIn("could not be judged line by line", self.err)
        self.assertEqual(seen[0], seen[1])

    def test_the_frame_reads_lines_with_the_diff_algorithm_the_merge_uses(self):
        # (13a): case (5) and case (11), each run with diff.algorithm unset, then set to
        # myers, then to patience, in the config of the repository the fold runs in. Git's
        # merge honours it, and the frame diffs with the algorithm the merge uses, so each
        # clash is read as the merge reads it: the same hold, the same words, every time.
        fresh = False
        for case, run in (("(5)", lambda: self._one_file_run(2, 8)),
                          ("(11)", self._repeated_run)):
            seen = []
            for algo in ("", "myers", "patience"):
                if fresh:
                    self.setUp()                          # a fresh repo and bundles each run
                fresh = True
                if algo:
                    sb._git(self.fx.primary, "config", "diff.algorithm", algo)
                run()
                self.assertEqual(sb._run(self.fx.primary, "config", "--get",
                                         "diff.algorithm").stdout.strip(), algo)
                seen.append(self._w_held("shared.txt"))
            self.assertEqual(seen[1:], seen[:1] * 2, case)

    def test_a_trial_with_two_merge_bases_is_not_judged_and_the_stop_names_the_file(self):
        # (15), through the flow: case (5), but W depends on Z and on Q, both of wave 0, so
        # its own base holds both branches. Its trial with A — A's head, what W holds of the
        # line (Z's and Q's heads) merged in first — then has two merge bases, Z's head and
        # Q's, which git merges into one base of its own; no diff of the frame is from it.
        # Not judged: the run stops, as before the fix, and the stop line names the file and
        # says its conflict could not be judged line by line.
        self._on_base({"shared.txt": NINE})
        self._plan("A", {"shared.txt": _edit(NINE, l2="A's line 2", l8="A's line 8")})
        self._plan("R", {"r.txt": "r\n"})
        self._plan("Z", {"z.txt": "z\n"})
        self._plan("Q", {"q.txt": "q\n"})
        self._plan("S", {"s.txt": "s\n"}, stacks_on="R")
        self._plan("W", {"shared.txt": _edit(NINE, l2="W's line 2", l8="main's line 8")},
                   depends_on="Z, Q")
        self._plan("T", {"t.txt": "t\n"}, depends_on="S")
        self._plan("V", {"v.txt": "v\n"}, depends_on="W")
        self.after_fold[1] = self._move_main({"shared.txt": _edit(NINE, l8="main's line 8")})
        self._run(["A", "R", "Z", "Q", "S", "W", "T", "V"])

        self.assertTrue(self.fx._ancestor(self.moves[0], self._head("W")))   # the facts
        self.assertEqual(self._merges("origin/main", "A"), 0)
        tips = [self._head(i) for i in ("W", "A", "Z", "Q")]
        self.assertEqual(sorted(sb._git(self.fx.origin, "merge-base", "--all", *tips).split()),
                         sorted(tips[2:]))
        self._stopped(1, "W")
        stop = [x for x in self.err.splitlines() if "STOPPING" in x]
        self.assertEqual(len(stop), 1, self.err)
        for part in ("wave 1 did not integrate (issue_W's branch", "(conflicts in shared.txt)",
                     "; the conflict in shared.txt could not be judged line by line (its trial "
                     "merge has more than one merge base), so the fold did not judge whether "
                     "the moved base is part of the clash); STOPPING"):
            self.assertIn(part, stop[0])
        self.assertEqual(self.results["T"], state.PLANNED, self.err)


# -- (13b), (14), (15) at the call boundary: the stake function ------------------------------

def _text(lines: Iterable[str]) -> str:
    return "".join(x + "\n" for x in lines)


Edits = dict[int, str | None]       # line index → its new text, or None: deleted


def _edits(rng: random.Random, n: int, tag: str) -> Edits:
    """1-3 edits of ``n`` lines, each a replacement (new text unique to ``tag``'s side) or
    a deletion."""
    lines = sorted(rng.sample(range(n), min(rng.randint(1, 3), n)))
    return {i: None if rng.random() < 0.5 else f"{tag}{k}" for k, i in enumerate(lines)}


def _edited(lines: list[str], edits: Edits) -> list[str]:
    return [edits.get(i, x) for i, x in enumerate(lines) if edits.get(i, x) is not None]


def _shape(rng: random.Random) -> tuple[list[str], Edits, Edits, Edits]:
    """A random shape for (14): a base of 4-12 lines drawn from `}`, blank, `x` and unique
    lines, and the edits of the move, of A's change and of W's own change (on the move's
    side)."""
    n = rng.randint(4, 12)
    base = [rng.choice(["}", "", "x", f"u{i}"]) for i in range(n)]
    move = _edits(rng, n, "M")
    return base, move, _edits(rng, n, "A"), _edits(rng, len(_edited(base, move)), "W")


def _reading(repo: Path, old: str, new: str, a: list[str], b: list[str]
             ) -> list[tuple[int, int, int, int]]:
    """Git's own reading of a frame diff, from blob ``old`` (lines ``a``) to ``new`` (``b``):
    each hunk ``(a, b, c, d)`` of ``git diff -U0`` with the frame's settings (histogram, no
    indent heuristic, no inter-hunk context), counted from 0, less the equal lines at its
    ends — the trim the frame makes on every diff."""
    out = []
    for line in sb._git(repo, "diff", "-U0", "--no-color", "--no-indent-heuristic",
                        "--inter-hunk-context=0", "--diff-algorithm=histogram",
                        old, new).splitlines():
        if line.startswith("@@ -"):
            span: list[int] = []
            for part in line.split(" ")[1:3]:
                start, comma, count = part[1:].partition(",")
                k = int(count) if comma else 1
                span += [int(start) - 1 if k else int(start), k]
            i, m, j, n = span
            while m and n and a[i] == b[j]:
                i, m, j, n = i + 1, m - 1, j + 1, n - 1
            while m and n and a[i + m - 1] == b[j + n - 1]:
                m, n = m - 1, n - 1
            if m or n:
                out.append((i, m, j, n))
    return out


def _relabelled(old: list[str], hunks: list[tuple[int, int, int, int]], tag: str
                ) -> list[str]:
    """The new side of a diff with ``hunks`` from lines ``old``: each line the diff keeps
    keeps its label, each one it adds gets a new one, ``tag`` and a number."""
    out: list[str] = []
    done = 0
    for a, b, _c, d in hunks:
        out += old[done:a] + [f"{tag}{len(out) + i}" for i in range(d)]
        done = a + b
    return out + old[done:]


def _meet(a: int, b: int, c: int, d: int) -> bool:
    """Lines ``a`` to ``a+b`` and ``c`` to ``c+d`` overlap or touch, ends included."""
    return a <= c + d and c <= a + b


class StakeFrame(unittest.TestCase):
    """The stake function ``_held_by_move`` calls (``integrate._stakes``), called directly on
    commits made with git's plumbing in a scratch repository, and judged against git's own
    merges. It is reached by attribute at call time, so with the fix reverted the module
    still loads, and these fail for want of it (no behaviour red is claimed for them)."""

    SEEDS = (749, 750, 751)          # (14): fixed seeds, one repository each
    SHAPES = 250                     # per seed

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _repo(self, name: str) -> Path:
        repo = self.tmp / name
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        sb._identity(repo)
        return repo

    def _commit(self, repo: Path, files: dict[str, str], *parents: str) -> str:
        """A commit of ``files`` (name → text) on ``parents``, made with git's plumbing."""
        rows = "".join(
            f"100644 blob {self._out(repo, 'hash-object', '-w', '--stdin', stdin=text)}\t{name}\n"
            for name, text in files.items())
        return self._out(repo, "commit-tree", self._out(repo, "mktree", stdin=rows),
                         *(x for p in parents for x in ("-p", p)), "-m", "c")

    def _out(self, repo: Path, *args: str, stdin: str | None = None) -> str:
        r = subprocess.run(["git", "-C", str(repo), *args], input=stdin, capture_output=True,
                           text=True)
        self.assertEqual(r.returncode, 0, (args, r.stderr))
        return r.stdout.strip()

    def test_the_frame_takes_the_diff_algorithm_the_merge_runs_with(self):
        # (13b): on this shape the algorithms disagree: git's merge conflicts under histogram
        # (ort's own default, diff.algorithm unset) and merges cleanly under myers. Given the
        # algorithm read from the repository's config, the frame finds a conflict in the
        # file exactly when a real `git merge` there conflicts, each way. One that forced
        # histogram, or took `git diff`'s own default (myers), would get one of them wrong.
        def tokens(s: str) -> str:
            return _text("" if t == "_" else t for t in s.split())

        repo = self._repo("algorithm")
        base = self._commit(repo, {"f.txt": tokens("{ y _ { } y } x } x { _")})
        one = self._commit(repo, {"f.txt": tokens("{ y _ { } { } x } x } _")}, base)
        two = self._commit(repo, {"f.txt": tokens("{ y _ { } y } } x { _")}, base)
        seen = {}
        for setting in ("", "myers"):
            if setting:
                self._out(repo, "config", "diff.algorithm", setting)
            self._out(repo, "checkout", "-q", "--detach", one)
            clean = sb._run(repo, "merge", "-q", "--no-ff", "--no-edit", two).returncode == 0
            sb._run(repo, "merge", "--abort")
            self._out(repo, "reset", "-q", "--hard", one)
            try:
                integrate._stakes(repo, base, one, two, (["f.txt"], []),
                                  integrate._diff_algorithm(repo))
                found = True
            except integrate._NotJudged:
                found = False
            seen[setting] = (clean, found)
        self.assertEqual(seen, {"": (False, True), "myers": (True, False)})

    def test_a_trial_with_more_than_one_merge_base_is_not_judged(self):
        # (15): a criss-cross history — two commits that each merge the other's parent — so
        # `git merge-base --all` gives two, and git merges against a base it makes of them.
        # The frame diffs from one merge base, so it judges nothing here, and says so,
        # naming the file.
        repo = self._repo("criss-cross")
        base = self._commit(repo, {"f.txt": NINE})
        x1 = self._commit(repo, {"f.txt": _edit(NINE, l2="x's line 2")}, base)
        y1 = self._commit(repo, {"f.txt": _edit(NINE, l8="y's line 8")}, base)
        both = _edit(NINE, l2="x's line 2", l8="y's line 8")
        x2 = self._commit(repo, {"f.txt": both}, x1, y1)
        y2 = self._commit(repo, {"f.txt": both}, y1, x1)
        head = self._commit(repo, {"f.txt": _edit(both, l5="the head's line 5")}, x2)
        there = self._commit(repo, {"f.txt": _edit(both, l5="its line 5")}, y2)
        self.assertEqual(sorted(self._out(repo, "merge-base", "--all", head, there).split()),
                         sorted([x1, y1]))                               # the fixture's facts
        self.assertEqual(sb._run(repo, "merge-tree", "--write-tree", head, there).returncode,
                         1)
        with self.assertRaises(integrate._NotJudged) as raised:
            integrate._stakes(repo, x2, head, there, (["f.txt"], []),
                              integrate._diff_algorithm(repo))
        self.assertEqual(raised.exception.path, "f.txt")
        self.assertEqual(str(raised.exception), "the conflict in f.txt could not be judged "
                         "line by line (its trial merge has more than one merge base)")

    def _variant(self, repo: Path, algo: str, base: list[str], s: list[str], t: list[str],
                 h: list[str]) -> tuple[tuple[bool, bool], bool, list[str]]:
        """One variant of a shape, judged as ``_held_by_move`` judges a stranded partner:
        ``O`` holds ``base``, the move's side ``s`` and the partner ``t`` are on ``O``, the
        head ``h`` on ``s`` — blobs, trees and commits made with git's plumbing. The partner
        is rebuilt on ``s``, its side winning (``git merge-tree -X theirs``), and the two
        trials' outcomes come from ``git merge-tree --write-tree`` (no config set, so it
        merges as porcelain ort does): the head onto the partner, then onto it rebuilt. Then
        the stake function decides, with ``algo``: tied when the head's stake after is a
        strict subset of its stake before. Returns ``(outcomes, tied, blobs)``: each trial
        conflicted or not, the verdict, and the blobs of ``O``, ``s``, ``t``, ``h``."""
        blobs = [self._out(repo, "hash-object", "-w", "--stdin", stdin=_text(x))
                 for x in (base, s, t, h)]
        trees = self._out(repo, "mktree", "--batch", stdin="".join(
            f"100644 blob {b}\tf.txt\n\n" for b in blobs)).split()
        o = self._out(repo, "commit-tree", trees[0], "-m", "O")
        moved = self._out(repo, "commit-tree", trees[1], "-p", o, "-m", "the move")
        there = self._out(repo, "commit-tree", trees[2], "-p", o, "-m", "the partner")
        head = self._out(repo, "commit-tree", trees[3], "-p", moved, "-m", "the head")
        rebuilt = sb._run(repo, "merge-tree", "--write-tree", "-X", "theirs", moved,
                          there).stdout.split()[0]
        first = sb._run(repo, "merge-tree", "--write-tree", head, there).returncode
        second = sb._run(repo, "merge-tree", "--write-tree", f"--merge-base={moved}", head,
                         rebuilt).returncode
        self.assertIn((first, second), {(0, 0), (0, 1), (1, 0), (1, 1)})
        tied = False
        if first:
            try:
                before, after = integrate._stakes(repo, moved, head, there,
                                                  (["f.txt"], ["f.txt"] if second else []),
                                                  algo)
                tied = after < before
            except integrate._NotJudged:
                pass
        return (bool(first), bool(second)), tied, blobs

    def _with_twin(self, repo: Path, algo: str, base: list[str], s: list[str], t: list[str],
                   h: list[str]) -> tuple:
        """A shape (:meth:`_variant`) and its reading twin: every line relabelled by git's
        own reading of the frame's three diffs (:func:`_reading`; a line a diff keeps keeps
        its label, one it adds gets a new one) — and the fact that git reads the twin as it
        reads the shape. Returns ``((outcomes, tied), (the twin's outcomes, tied), (move,
        own, theirs))``, the last the shape's three readings."""
        pairs = ((0, 1), (1, 3), (0, 2))          # the move, the own change, the partner's
        outcome, tied, blobs = self._variant(repo, algo, base, s, t, h)
        lines = (base, s, t, h)
        move, own, theirs = hunks = [_reading(repo, blobs[x], blobs[y], lines[x], lines[y])
                                     for x, y in pairs]
        o2 = [f"o{i}" for i in range(len(base))]
        s2 = _relabelled(o2, move, "m")
        twin_lines = (o2, s2, _relabelled(o2, theirs, "a"), _relabelled(s2, own, "w"))
        twin, twin_tied, twin_blobs = self._variant(repo, algo, *twin_lines)
        self.assertEqual([_reading(repo, twin_blobs[x], twin_blobs[y], twin_lines[x],
                                   twin_lines[y]) for x, y in pairs], hunks)
        return (outcome, tied), (twin, twin_tied), (move, own, theirs)

    def test_lines_that_line_up_on_their_own_never_settle_a_conflict_the_rebuild_makes(self):
        # The three shapes runs of 14,000 found (seeds 102, 109 and 203 of the build notes):
        # the move replaces a line, W removes the move's line, and A removes the line beside
        # it, equal to the one the move replaced, so W's text and A's agree there. Git's
        # text test takes W's removal out of the stake once A is rebuilt (A's rebuild makes
        # a hunk over the move's), but not before, where the region holds the move's hunk:
        # W would be held where its reading twin (the same reading, every line its own) is
        # not judged. Made over a move hunk, the rebuild's hunk agrees with W's only as the
        # same hunk, so no shape is tied, as no twin is.
        repo = self._repo("lined-up")
        algo = integrate._diff_algorithm(repo)
        for base, s, t, h in (
                (["", "x", "u2", "x", "u4", "u5", "x", "x"], ["", "x", "u4", "u5", "M2", "x"],
                 ["", "u2", "u4", "u5", "x"], ["x", "u5", "x"]),
                (["x", "", "}", "}", "", "", "x", "x", "}", "", "u10", "u11"],
                 ["x", "", "M0", "}", "", "", "x", "x", "", "M2", "u11"],
                 ["x", "", "}", "", "", "x", "x", "A1", "", "u10", "u11"],
                 ["x", "", "}", "", "", "x", "W1", "", "M2", "u11"]),
                (["}", "u1", "", "}", "}", "}", "", "", "}", "}", "}"],
                 ["}", "M0", "", "}", "M1", "}", "", "", "M2", "}", "}"],
                 ["u1", "", "}", "}", "", "", "}", "}", "A2"],
                 ["M0", "", "}", "}", "", "", "W2", "}", "}"])):
            shape, twin, _hunks = self._with_twin(repo, algo, base, s, t, h)
            self.assertEqual((shape, twin), (((True, True), False), ((True, True), False)), base)

    def test_a_random_probe_decides_each_shape_as_its_reading_twin(self):
        # (14): random shapes on repeated lines, each beside its reading twin — every line
        # relabelled by git's own reading of the frame's three diffs, a line a diff keeps
        # keeping its label and one it adds getting a new one — so the twin is the same clash
        # with nothing left for repeated lines to decide. Wherever git's two trials end the
        # same way for both, the stake function decides them alike (tied or not), but for
        # two kinds of shape, each an exact test over the frame's hunks: R, the head's own
        # change touches a move hunk and puts back what it replaced; I, the partner's change
        # touches a move hunk and makes the same change. There, a mismatch must leave the
        # shape not tied and its twin tied — never a hold the twin would not get — and is
        # rare. The positional twin (the same edits at the same line numbers on a base of
        # unique lines) is counted only (`probe["positional"]`, for the build notes).
        probe = self._probe()
        self.assertGreaterEqual(probe["shapes"], 600)
        self.assertGreater(probe["compared"], probe["shapes"] * 9 // 10)
        self.assertEqual(probe["outside"], [], probe["outside"][:3])
        self.assertEqual([m for m in probe["exempt"] if m["tied"] != (False, True)], [])
        self.assertLessEqual(len(probe["exempt"]), probe["shapes"] // 100)

    def _probe(self) -> dict:
        """(14) over :attr:`SEEDS`: the shapes, the ones compared (git's trials end alike for
        the shape and its reading twin), the mismatches outside R ∪ I and inside it, and the
        positional twin's mismatches (counted only)."""
        probe: dict = {"shapes": 0, "compared": 0, "outside": [], "exempt": [],
                       "positional": 0, "positional_compared": 0}
        for seed in self.SEEDS:
            repo = self._repo(f"probe-{seed}")
            algo = integrate._diff_algorithm(repo)
            rng = random.Random(seed)
            for _ in range(self.SHAPES):
                base, edits_move, edits_theirs, edits_own = _shape(rng)
                s = _edited(base, edits_move)
                t, h = _edited(base, edits_theirs), _edited(s, edits_own)
                (outcome, tied), (twin, twin_tied), (move, own, theirs) = self._with_twin(
                    repo, algo, base, s, t, h)
                probe["shapes"] += 1
                if outcome == twin:
                    probe["compared"] += 1
                    if tied != twin_tied:
                        r = any(_meet(a, b, mc, md) and h[c:c + d] == base[ma:ma + mb]
                                for a, b, c, d in own for ma, mb, mc, md in move)
                        i = any(_meet(a, b, ma, mb) and t[c:c + d] == s[mc:mc + md]
                                for a, b, c, d in theirs for ma, mb, mc, md in move)
                        probe["exempt" if r or i else "outside"].append(
                            {"seed": seed, "base": base, "move": s, "theirs": t, "own": h,
                             "tied": (tied, twin_tied), "R": r, "I": i})
                u = [f"u{i}" for i in range(len(base))]
                su = _edited(u, edits_move)
                positional, positional_tied, _blobs = self._variant(
                    repo, algo, u, su, _edited(u, edits_theirs), _edited(su, edits_own))
                if outcome == positional:
                    probe["positional_compared"] += 1
                    probe["positional"] += tied != positional_tied
        return probe


if __name__ == "__main__":
    unittest.main()
