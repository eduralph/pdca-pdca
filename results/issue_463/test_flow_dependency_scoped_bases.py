"""In stack mode a bundle is built on what it declares, not on when it was scheduled (#463).

Before #463 every bundle of a wave after the first was pointed at the run's one integration
line, which holds every bundle an earlier wave accepted: ``B`` (``Depends on: A``) was cut
from a line that also held ``Z``, a bundle of the same earlier wave it has nothing to do
with, so ``B``'s PR carried ``Z``'s commits, and merging it landed ``Z`` even if ``Z``'s own
PR was closed (#630). Now each bundle's base carries exactly the work of the bundles it was
ordered after by a declared edge — ``Depends on`` (transitively), an earlier-wave
``Conflicts with`` partner, a finished prerequisite the run carried (#646) — and a bundle
with none of those is built on the real base. The run's line is still folded after each
wave, as the run's check of the combined work.

These cases drive ``flow._drive_and_act`` through real folds on the ``StackFoldGit`` fixture
of tests/test_integrate_stack_bases.py (a bare ``origin``, a primary checkout and a scratch
clone), loaded by path and used as a helper object, as tests/test_flow_same_wave_conflict.py
does. The build and sign-off leaves are stubbed (the build writes a ``patch.diff`` and
accepts; a close disposition writes the close marker instead), ``flow._publish_bundle`` cuts
the PR branch from the recorded stack base tip (else the base), commits each of the
bundle's commits and pushes it, and ``gh`` is answered by a stub in front of
``subprocess.run``. The publisher is NOT a stub (a stub turns every fold into a dry-run).
Criterion (6) drives the carry fixture of tests/test_flow_resume_stack_prereqs.py, loaded the
same way.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_dependency_scoped_bases
"""

from __future__ import annotations

import dataclasses
import importlib.util
import inspect
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

TODAY = "2026-10-15"
TWO = "two commits"


class DependencyScopedBases(unittest.TestCase):

    def setUp(self) -> None:
        self.fx = sb.StackFoldGit()          # the fixture's real-git setUp/tearDown and helpers
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.cfg = self.fx.cfg
        self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
        self.commits: dict[str, list[dict[str, str]]] = {}   # id → its commits' new files
        self.close: set[str] = set()                         # ids closed with no patch
        # bundle → (stack base, recorded tip, origin's tip of that base, origin's main) when
        # its wave was driven
        self.seen: dict[str, tuple[str, str, str | None, str]] = {}
        self.order: list[str] = []                           # bundles, in the order built
        self.cut: dict[str, str] = {}                        # id → the commit its branch is cut from
        self.after_line_fold: Callable[[], None] | None = None   # run once, after a line fold
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _plan(self, iid: str, commits: list[dict[str, str]] | str | None = None, *,
              depends_on: str = "", merged: str = "", conflicts_with: str = "") -> Path:
        """Bundle ``iid``'s brief with the edges given, and what its build commits:
        ``commits`` a list of commits (each the new files it adds), ``TWO`` for two commits
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
        """Build and accept each bundle, recording what it was built on. A bundle in
        ``self.close`` is accepted with a close disposition: no patch."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            base = publish.read_stack_base(d)
            self.seen[d.name] = (base, publish.read_stack_base_tip(d),
                                 self.fx._tip(base) if base and self.fx._has(base) else None,
                                 self.fx._tip("main"))
            self.order.append(iid)
            if iid in self.close:
                (d / state.CLOSE_MARKER).write_text("likely-close\n", encoding="utf-8")
            else:
                (d / "patch.diff").write_text("".join(
                    sb._new_file_patch(n, t.rstrip("\n"))
                    for c in self.commits[iid] for n, t in c.items()), encoding="utf-8")
            sb._accept(d)
        return 1

    def _publish_bundle(self, cfg, d: Path, **_kw) -> bool:
        """What publish does: cut ``fix/<iid>`` from the recorded stack base tip (else the
        recorded base, else the base), make each of the bundle's commits on it, signed off,
        push it and record it. A closed bundle publishes nothing."""
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
            {"mode": "new-pr", "branch": branch, "base": "main", "repo": "org/repo",
             "pr_url": f"https://example.test/pr/{iid}"}), encoding="utf-8")
        return True

    def _run(self, ids: list[str]) -> None:
        """One stack-mode run asked for ``ids``, driving all of them."""
        self.line = integrate.integration_branch(self.cfg, "main", ids)
        real_fold = integrate.fold

        def fold(*a, **kw):
            out = real_fold(*a, **kw)
            if kw.get("into") is None and self.after_line_fold is not None:
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
            self.results = flow._drive_and_act(self.cfg, [self.cfg.bundle(i) for i in ids],
                                               do_publish=True, do_act=False, by="T",
                                               today=TODAY, batch=ids)
        self.err = err.getvalue()
        self.assertNotIn("Traceback", self.err)

    # -- helpers ---------------------------------------------------------------------------

    def _head(self, iid: str) -> str:
        return self.fx._tip(f"fix/{iid}")

    def _work(self, iid: str) -> list[str]:
        """Every commit of ``fix/<iid>`` that origin's ``main`` does not have."""
        return sb._git(self.fx.origin, "rev-list", f"main..fix/{iid}").split()

    def _reach(self, rev: str) -> set[str]:
        return set(sb._git(self.fx.origin, "rev-list", rev).split())

    def _all_of(self, rev: str, iid: str) -> None:
        """``rev`` holds every commit of ``iid``'s branch."""
        work = self._work(iid)
        self.assertTrue(work, iid)
        self.assertEqual([c for c in work if c not in self._reach(rev)], [], (rev, iid))

    def _none_of(self, rev: str, iid: str) -> None:
        """``rev`` holds no commit of ``iid``'s branch — not one, so a partial carry fails."""
        work = self._work(iid)
        self.assertTrue(work, iid)
        self.assertEqual([c for c in work if c in self._reach(rev)], [], (rev, iid))

    def _built_on(self, iid: str, *closure: str) -> str:
        """``iid`` was built on a base of its own holding the work of exactly ``closure``,
        and its PR branch was cut from that commit; returns it. Its recorded stack base is a
        branch on origin, and the recorded tip is that branch's tip when its wave was driven
        (the base it was built on); the tip holds each of their branches, and, beyond the
        base it started from and them, only its own fold's merge commits."""
        self.assertIn(f"issue_{iid}", self.seen, self.err)
        base, tip, at, main = self.seen[f"issue_{iid}"]
        self.assertTrue(base, self.err)
        self.assertIsNotNone(at, self.err)
        self.assertEqual(tip, at, self.err)
        heads = [self._head(c) for c in closure]
        for c, h in zip(closure, heads):
            self.assertTrue(self.fx._ancestor(h, tip), (iid, c, self.err))
        self.assertEqual(self.fx._beyond(tip, main, heads), [], (iid, self.err))
        self.assertEqual(self.cut[iid], tip)                  # its PR branch is cut from it
        self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        return tip

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

    # -- (3) a `Conflicts with` partner of an earlier wave counts as built on ---------------

    def test_an_earlier_wave_conflicts_with_partner_is_on_the_base(self):
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

    # -- (4) no in-run prerequisite with work → the real base --------------------------------

    def test_a_bundle_whose_only_prerequisite_has_no_patch_is_built_on_the_real_base(self):
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("N")
        self.close.add("N")                                  # closed: nothing of it is folded
        self._plan("H", depends_on="N")
        self._run(["A", "N", "Z", "H"])

        self.assertNotIn("STOPPING", self.err)
        self.assertLess(self.order.index("N"), self.order.index("H"))   # a later wave
        for iid in ("A", "N", "Z", "H"):
            self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        base, tip, _at, main = self.seen["issue_H"]
        self.assertEqual((base, tip), ("", ""), self.err)                # cleared
        self.assertEqual(publish.read_stack_base(self.cfg.bundle("H")), "")
        self.assertEqual(self.cut["H"], main)                # cut from the base it found
        self._none_of("fix/H", "A")
        self._none_of("fix/H", "Z")

    # -- an in-batch `Depends on (merged)` prerequisite is merged nowhere: carried ----------

    def test_an_in_batch_depends_on_merged_prerequisite_is_on_the_base(self):
        # In-batch, the field orders G after A like `Depends on`, and A's PR is merged
        # nowhere this run, so only G's base can bring A's work.
        self._plan("A", TWO)
        self._plan("Z", TWO)
        self._plan("G", merged="A")
        self._run(["A", "Z", "G"])

        self.assertNotIn("STOPPING", self.err)
        self._all_of("fix/G", "A")
        self._none_of("fix/G", "Z")
        self._built_on("G", "A")

    # -- (6) a carried finished prerequisite is in the closure (#646) -----------------------

    def test_a_carried_finished_prerequisite_is_on_its_dependents_base_alone(self):
        c = rs.ResumeStackPrereqs()          # the carry fixture, as a helper object
        c.setUp()
        self.addCleanup(c.doCleanups)
        c._finished("P", {"p.txt": "p\n"})
        c._finished("X", {"x.txt": "x\n"})
        d, e = c._planned("D", "P"), c._planned("E", "X")
        c._run([d, e], ["P", "X", "D", "E"])

        self.assertIn("flow: carried issue_P, issue_X", c.err)
        p, x = c.fx._tip("fix/P"), c.fx._tip("fix/X")
        for iid, has, lacks in (("D", p, x), ("E", x, p)):
            base, tip, _line = c.seen[f"issue_{iid}"]
            self.assertTrue(base, c.err)
            self.assertTrue(c.fx._ancestor(has, tip), (iid, c.err))
            self.assertFalse(c.fx._ancestor(lacks, tip), (iid, c.err))
            self.assertEqual(c.results[iid], state.COMPLETE, c.err)

    # -- the #633 check applies to a bundle's base ------------------------------------------

    def test_a_carried_branch_rewritten_before_a_dependents_base_is_built_stops_the_run(self):
        # After the line's fold after wave 0 carried fix/A, fix/A is rewritten (re-published
        # from the base). B's base is folded from fix/A next: the fold's #633 check stops
        # the run there, before B is built on commits the line does not hold.
        self._plan("A")
        self._plan("B", depends_on="A")
        took: list[str] = []

        def rewrite_a() -> None:
            took.append(self._head("A"))
            self.fx._push_from_human({"a-rebuilt.txt": "A, rebuilt\n"}, to="fix/A",
                                     force=True)

        self.after_line_fold = rewrite_a
        self._run(["A", "B"])

        self.assertEqual(len(took), 1, self.err)
        self.assertFalse(self.fx._ancestor(took[0], self._head("A")))     # a rewrite
        self.assertNotIn("issue_B", self.seen, self.err)                   # never built
        self.assertEqual(self.results["B"], state.PLANNED, self.err)
        stop = [x for x in self.err.splitlines() if "STOPPING" in x]
        self.assertEqual(len(stop), 1, self.err)
        for part in ("issue_B", "issue_A's branch origin/fix/A was rewritten", took[0][:12]):
            self.assertIn(part, stop[0])

    # -- integrate.fold(into=…): the push rule -----------------------------------------------

    def test_a_bundle_base_is_pushed_plain_when_new_and_forced_only_to_rebuild_it(self):
        self.assertIn("into", inspect.signature(integrate.fold).parameters,
                      "integrate.fold cannot fold onto a named branch")
        sb._git(self.fx.origin, "config", "receive.denyNonFastForwards", "true")
        a = self.fx._publish("A", {"a.txt": "a\n"})
        into = integrate.integration_branch(self.cfg, "main", ["A", "B"]) + "-dB"

        def fold() -> list[list[str]]:
            return self.fx._pushes(lambda: integrate.fold(
                self.cfg, [a], folded_this_run={}, batch=["A", "B"], into=into))

        pushes = fold()                                       # new on origin: a plain push
        self.assertEqual(pushes, [["push", "origin", into]])
        first = self.fx._tip(into)
        self.assertTrue(self.fx._ancestor(self._head("A"), first))
        self.assertEqual(sb._git(self.fx.origin, "rev-parse", f"{first}^1").strip(),
                         self.fx._tip("main"))                # started from the base
        self.assertFalse(self.fx._has(integrate.integration_branch(self.cfg, "main",
                                                                   ["A", "B"])))
        # Built again on a moved base: a forced push, refused here, naming the branch.
        self.fx._push_from_human({"m.txt": "m\n"}, to="main")
        with redirect_stderr(io.StringIO()), \
                self.assertRaises(integrate.IntegrationError) as refused:
            fold()
        for part in (into, "allow force-pushes on pdca-integration/*", f"delete the old {into}"):
            self.assertIn(part, str(refused.exception))
        self.assertEqual(self.fx._tip(into), first)           # nothing replaced
        # Allowed: it is rebuilt fresh from the base, the one push leased on the old tip.
        sb._git(self.fx.origin, "config", "receive.denyNonFastForwards", "false")
        pushes = fold()
        self.assertEqual(pushes, [["push", f"--force-with-lease={into}:{first}", "origin",
                                   into]])
        self.assertEqual(sb._git(self.fx.origin, "rev-parse", f"{into}^1").strip(),
                         self.fx._tip("main"))

    def test_a_bundle_base_name_is_scoped_to_the_batch_and_injective(self):
        self.assertTrue(hasattr(integrate, "bundle_base"), "no name for a bundle's base")
        name = integrate.bundle_base
        line = integrate.integration_branch(self.cfg, "main", ["A", "B"])
        b = name(self.cfg, "main", ["A", "B"], "issue_B")
        self.assertTrue(b.startswith(line + "-"), b)
        self.assertNotIn("/", b.removeprefix("pdca-integration/"))   # no path prefix clash
        names = [b, name(self.cfg, "main", ["A", "B"], "issue_A"),
                 name(self.cfg, "main", ["A"], "issue_B"),
                 name(self.cfg, "release/2.0", ["A", "B"], "issue_B"),
                 name(self.cfg, "release-2.0", ["A", "B"], "issue_B"),
                 name(self.cfg, "main", ["A", "B"], "issue_B-d1"),
                 name(self.cfg, "main", ["A", "B"], "issue_B/d1"),
                 name(self.cfg, "main", None, "issue_B"), line]
        self.assertEqual(len(set(names)), len(names), names)


if __name__ == "__main__":
    unittest.main()
