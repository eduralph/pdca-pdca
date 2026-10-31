"""`[driver].wave_mode = "none"`: every PR against its real base, nothing at a wave boundary (#464).

`"stack"` folds each wave onto a run-scoped integration line and `"merge"` readies and merges
the wave's PRs. `"none"` does neither: every accepted bundle publishes as a draft PR against
its real target base, as a one-bundle run does, and at a wave boundary nothing happens — no
`pdca-integration/*` branch is created or pushed, nothing is folded, readied or merged, and
the pre-wave carry of finished ids does not run. Waves still order the build, so a bundle
whose prerequisite (`Depends on`, `Depends on (merged)` or `Stacks on`, in the batch or not)
has not merged into its own target base is held, named on one line with the way out, and
recorded in the run's ``holds`` as ``"unmerged"`` (exit 3). Once the prerequisite's PR has
merged and the base as fetched has that merge, a re-run builds it on the base and opens its
PR against the base. A chain is held the same way, link by link, each told every step that
releases it, as that step stands: a merge to make, a PR to re-open, a fetch to fix. A
prerequisite whose PR can never count for the base (another base or repo, an `Onto branch`
commit) is named as such, never with "merge it". A prerequisite with no PR of its accepted
work on record — its texts failed, its PR was not opened, or an iterate left an older
attempt's PR on record, in this run and every later one — has nothing to merge: its dependent
is held with "publish it first", never as waiting for a merge, and the run fails (exit 1), as
the same failed publish does in stack mode. So it fails when a prerequisite's PR cannot be
read, or the fetched base cannot be checked, however far the reads got: that is a fault to
fix, not a merge to wait for. An iterated bundle whose PR is still open keeps that PR: `gh pr
create` refuses a second one, and the push has updated the first. A bundle left with no PR is
reported in every wave, the last one too, whether or not anything depends on it
(``"unpushed"`` or ``"no-pr"``, exit 3). A prerequisite no PR of which can exist (no patch, or
no usable target) has nothing to wait for. A dependent with no target of its own keeps #186's
"not ready", and a `Conflicts with` edge only orders the build. With ``--no-publish``, or in a
dry-run (the stub publisher), nothing waits and no host is asked, but for the gate on a
`Depends on (merged)` edge out of the run, the same in every mode.
An unknown `wave_mode` is reported at config load and falls back to `"stack"`.

These cases drive ``flow._drive_and_act`` the way tests/test_flow_same_wave_conflict.py
does, on the ``StackFoldGit`` fixture of tests/test_integrate_stack_bases.py (a bare
``origin`` and a primary checkout, real git), loaded by path. The build and sign-off leaves
are stubbed (the build records the base ``worktree._target`` gives its Do worktree, writes a
``patch.diff`` and the publish texts, and accepts), and so is the drafting of the publish
texts (``publish.draft_texts``: ready, or failed for the ids a case names). Publish is the
REAL one: the publisher is in ``command`` mode, ``flow._publish_bundle`` runs
``publish.publish``, which cuts, commits and pushes to the bare origin, and only ``gh`` is
answered by a stub in front of ``subprocess.run`` — so the ``gh pr create --base`` asserted
on is the one publish builds. The stub keeps the PRs it opened and refuses a second open PR
for one head and base, as the host does. An iterate is the real ``driver._archive_iteration``.
The exit code is ``cli._results_rc``'s, and the ``test_pdca_flow_*`` cases take it from
``cli._flow`` itself.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_wave_mode_none
"""

from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pdca_harness import cli, config, driver, flow, publish, state, worktree

_SPEC = importlib.util.spec_from_file_location(
    "stack_bases_fixture", Path(__file__).with_name("test_integrate_stack_bases.py"))
sb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sb)

TODAY = "2026-10-30"
PR_URL = "https://example.test/pr/"


class WaveModeNone(unittest.TestCase):

    def setUp(self) -> None:
        self.fx = sb.StackFoldGit()          # the fixture's real-git setUp/tearDown and helpers
        self.fx.setUp()
        self.addCleanup(self.fx.tearDown)
        self.cfg = self.fx.cfg
        self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
        self.cfg.wave_mode = "none"
        self.changes: dict[str, dict[str, str]] = {}     # id → the files its build adds
        self.merged_prs: dict[str, tuple[str, str]] = {}  # PR url → (head, merge commit)
        self.texts_fail: set[str] = set()     # ids whose publish texts fail draft/T4
        self.create_fails: set[str] = set()   # ids whose `gh pr create` fails after the push
        self.opened: dict[str, tuple[str, str, str]] = {}  # PR url → (owner, branch, its base)
        self.closed_prs: set[str] = set()     # PR urls `gh pr view` reads CLOSED
        self.view_fails = False               # every `gh pr view` fails (expired auth, say)
        self.view_reads_left: int | None = None  # … or all but this many, from now on
        self.list_fails = False               # `gh pr list` fails
        self.gh_missing = False               # `gh` itself cannot be run
        self.gh_calls: list[list[str]] = []
        # id → (the base its Do worktree is cut from, its recorded stack base) when built
        self.built: dict[str, tuple[str | None, str]] = {}
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _plan(self, iid: str, files: dict[str, str], *, depends_on: str = "",
              depends_on_merged: str = "", stacks_on: str = "", conflicts_with: str = "",
              onto_branch: str = "", target: bool = True, base: str = "main") -> Path:
        d = self.cfg.bundle(iid)
        extra = "".join(f"- **{name}:** {ids}\n" for name, ids in (
            ("Depends on", depends_on), ("Depends on (merged)", depends_on_merged),
            ("Stacks on", stacks_on), ("Conflicts with", conflicts_with),
            ("Onto branch", onto_branch)) if ids)
        if target and base == "main":
            sb._brief(d, extra=extra)
        else:   # no `Repo + branch target` (publish skips it: #186's answer), or another base
            d.mkdir(parents=True, exist_ok=True)
            where = f"- **Repo + branch target:** org/repo @ {base}\n" if target else ""
            (d / "brief.md").write_text(f"- **Slug:** {iid}\n{where}{extra}", encoding="utf-8")
        self.changes[iid] = files
        return d

    def _iterate(self, iid: str, files: dict[str, str]) -> None:
        """``signoff --iterate-do`` of an accepted bundle: the attempt moves to
        ``iteration-v<N>/`` and ``publish.json`` stays; the next build writes ``files``."""
        d = self.cfg.bundle(iid)
        driver._archive_iteration(d, driver._next_iteration_no(d), include_brief=False)
        self.assertEqual(state.state(d), state.PLANNED)
        self.assertTrue((d / "publish.json").is_file())
        self.changes[iid] = files

    def _record(self, iid: str) -> dict:
        return json.loads((self.cfg.bundle(iid) / "publish.json").read_text(encoding="utf-8"))

    def _publish(self, iid: str) -> int:
        """``pdca publish <id>``: the way out the hold lines name."""
        with self._stubbed():
            rc = publish.publish(self.cfg, iid, by="T", today=TODAY)
        self.err, self.out = self._err.getvalue(), self._out.getvalue()
        self.assertNotIn("Traceback", self.err)
        return rc

    def _merge_pr(self, iid: str, *, squash: bool = False, into: str = "main") -> None:
        """The maintainer merges ``iid``'s recorded PR into ``into``, with a merge commit or
        squashed; ``gh`` then reads it MERGED, with its head and the commit the merge put on
        that branch."""
        rec = self._record(iid)
        branch = rec["branch"]
        head = self.fx._tip(branch)
        h = self.fx.human
        sb._git(h, "fetch", "-q", "origin")
        sb._git(h, "checkout", "-q", "-B", into, f"origin/{into}")
        if squash:
            sb._git(h, "merge", "-q", "--squash", f"origin/{branch}")
            sb._git(h, "commit", "-q", "-m", f"fix {iid}, squashed")
        else:
            sb._git(h, "merge", "-q", "--no-ff", "--no-edit", f"origin/{branch}")
        sb._git(h, "push", "-q", "origin", into)
        self.merged_prs[rec["pr_url"]] = (head, sb._git(h, "rev-parse", "HEAD").strip())

    # -- stubs -----------------------------------------------------------------------------

    def _is_open(self, url: str) -> bool:
        return url not in self.merged_prs and url not in self.closed_prs

    def _gh_stub(self, args, *a, **kw):
        """Every ``gh`` call is recorded. ``gh pr create`` opens a PR (its URL names the id
        of the ``--head`` branch, then a count), refuses a head and base that already have an
        open PR, as the host does, and fails for an id in ``create_fails``; ``gh pr list``
        answers with the open PRs of ``--head`` (and ``--base``, if given), or fails with
        ``list_fails``; ``gh pr view`` reads a PR of ``merged_prs`` MERGED, of ``closed_prs``
        CLOSED, any other OPEN, or fails with ``view_fails`` or once ``view_reads_left`` runs
        out; any other ``gh`` call fails, and with ``gh_missing`` every one raises as a
        missing executable does. Everything else runs for real."""
        if not (isinstance(args, list) and args[:1] == ["gh"]):
            return self._real_run(args, *a, **kw)
        self.gh_calls.append(list(args))
        if self.gh_missing:
            raise FileNotFoundError(2, "No such file or directory", "gh")
        if self.view_fails and args[1:3] == ["pr", "view"]:
            return subprocess.CompletedProcess(args, 1, "", "gh: authentication expired")
        if self.view_reads_left is not None and args[1:3] == ["pr", "view"]:
            if self.view_reads_left == 0:
                return subprocess.CompletedProcess(args, 1, "", "gh: authentication expired")
            self.view_reads_left -= 1
        if args[1:3] == ["pr", "create"]:
            iid = self._pr_id(args)
            if iid in self.create_fails:
                return subprocess.CompletedProcess(args, 1, "", "gh: could not create the PR")
            owner, branch = args[args.index("--head") + 1].split(":", 1)
            base = args[args.index("--base") + 1]
            if any(pr == (owner, branch, base) and self._is_open(u)
                   for u, pr in self.opened.items()):
                return subprocess.CompletedProcess(
                    args, 1, "", f'a pull request for branch "{branch}" into branch "{base}" '
                                 f'already exists')
            count = sum(u.removeprefix(PR_URL).split("-")[0] == iid for u in self.opened)
            url = f"{PR_URL}{iid}{f'-{count + 1}' if count else ''}"
            self.opened[url] = (owner, branch, base)
            return subprocess.CompletedProcess(args, 0, f"{url}\n", "")
        if args[1:3] == ["pr", "list"]:
            if self.list_fails:
                return subprocess.CompletedProcess(args, 1, "", "gh: could not list the PRs")
            head = args[args.index("--head") + 1]
            base = args[args.index("--base") + 1] if "--base" in args else None
            open_only = "--state" not in args or args[args.index("--state") + 1] == "open"
            found = [{"url": u, "number": 1, "headRefName": br,
                      "headRepositoryOwner": {"login": owner}}
                     for u, (owner, br, on) in self.opened.items()
                     if br == head and base in (None, on) and (self._is_open(u) or not open_only)]
            return subprocess.CompletedProcess(args, 0, json.dumps(found), "")
        if args[1:3] == ["pr", "view"]:
            got = self.merged_prs.get(str(args[3]))
            other = "CLOSED" if str(args[3]) in self.closed_prs else "OPEN"
            info = ({"state": "MERGED", "headRefOid": got[0], "mergeCommit": {"oid": got[1]}}
                    if got else {"state": other, "headRefOid": ""})
            return subprocess.CompletedProcess(args, 0, json.dumps(info), "")
        return subprocess.CompletedProcess(args, 1, "", "gh: not stubbed")

    @staticmethod
    def _pr_id(create: list[str]) -> str:
        """The bundle id of a ``gh pr create`` call: from its ``--head OWNER:fix/<id>-<slug>``."""
        branch = create[create.index("--head") + 1].split(":", 1)[-1]
        return branch.removeprefix("fix/").split("-", 1)[0]

    def _drive_wave(self, cfg, wave: list[Path], **_kw) -> int:
        """Build and accept each bundle, recording what its Do worktree is cut from."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            target = worktree._target(d, cfg)
            self.built[iid] = (target[1] if target else None, publish.read_stack_base(d))
            (d / "patch.diff").write_text(
                "".join(sb._new_file_patch(n, t.rstrip("\n"))
                        for n, t in self.changes[iid].items()), encoding="utf-8")
            (d / publish.COMMIT_MSG).write_text(f"fix {iid}\n\nFixes #{iid}\n",
                                                encoding="utf-8")
            (d / publish.PR_BODY).write_text(f"**User impact:** {iid}\n\nFixes #{iid}\n",
                                             encoding="utf-8")
            sb._accept(d)
        return 1

    def _texts_ready(self, _cfg, d: Path, *_a, **_kw) -> bool:
        """``publish.draft_texts``: ready, except for an id in ``texts_fail``."""
        return d.name.removeprefix("issue_") not in self.texts_fail

    def _run(self, drive: list[str], batch: list[str], *, do_publish: bool = True) -> None:
        """One run asked for ``batch``, driving ``drive`` (a re-run drives what the earlier
        one left, as ``flow_ids`` does)."""
        bundles = [self.cfg.bundle(i) for i in drive]
        self.holds: dict[str, str] = {}
        with self._stubbed():
            self.results = flow._drive_and_act(self.cfg, bundles, do_publish=do_publish,
                                               do_act=False, by="T", today=TODAY,
                                               batch=batch, holds=self.holds)
        self.err, self.out = self._err.getvalue(), self._out.getvalue()
        self.rc = cli._results_rc(self.results, holds=self.holds)
        self.assertNotIn("Traceback", self.err)

    def _stubbed(self) -> ExitStack:
        """One run's stubs, with its stdout and stderr captured and its ``gh`` calls counted
        from here."""
        self._err, self._out = io.StringIO(), io.StringIO()
        self.calls_before = len(self.gh_calls)
        stack = ExitStack()
        stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
        stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
        stack.enter_context(mock.patch.object(publish, "draft_texts", self._texts_ready))
        stack.enter_context(redirect_stdout(self._out))
        stack.enter_context(redirect_stderr(self._err))
        return stack

    def _pdca_flow(self, *ids: str) -> int:
        """``pdca flow <ids…>`` through ``cli._flow``, which returns the process's exit code
        (publishing on, ``--no-act``)."""
        args = SimpleNamespace(issue_ids=list(ids), from_csv=None, from_briefs=None,
                               no_publish=False, no_act=True, by="T", lanes=None,
                               max_passes=None)
        with self._stubbed():
            rc = cli._flow(self.cfg, args)
        self.err, self.out = self._err.getvalue(), self._out.getvalue()
        self.assertNotIn("Traceback", self.err)
        return rc

    # -- assertions ------------------------------------------------------------------------

    def _gh(self, *sub: str) -> list[list[str]]:
        """The last run's ``gh <sub…>`` calls."""
        return [c for c in self.gh_calls[self.calls_before:] if c[1:1 + len(sub)] == list(sub)]

    def _pr_bases(self) -> dict[str, str]:
        """id → the ``--base`` of each ``gh pr create`` the last run made."""
        return {self._pr_id(c): c[c.index("--base") + 1] for c in self._gh("pr", "create")}

    def _integration_branches(self) -> list[str]:
        return sb._git(self.fx.origin, "for-each-ref", "--format=%(refname)",
                       "refs/heads/pdca-integration").split()

    def _nothing_at_the_boundary(self) -> None:
        """No integration line on origin; nothing readied or merged."""
        self.assertEqual(self._integration_branches(), [], self.err)
        self.assertEqual([c for c in self.gh_calls if c[1:3] in (["pr", "ready"],
                                                                 ["pr", "merge"])], [])

    def _held_lines(self, iid: str) -> list[str]:
        return [x for x in self.err.splitlines() if x.startswith(f"flow: issue_{iid} held")]

    def _held_line(self, iid: str) -> str:
        """The ONE line naming ``iid`` as held."""
        held = self._held_lines(iid)
        self.assertEqual(len(held), 1, self.err)
        return held[0]

    def _held_unmerged(self, iid: str, prereq: str) -> None:
        """``iid`` was not built, is PLANNED, and is named on ONE line as held for
        ``prereq``'s PR not merged into main — with no advice about a line."""
        self._held_unmerged_into("main", iid, prereq)

    def _held_unmerged_into(self, base: str, iid: str, prereq: str) -> None:
        self.assertNotIn(iid, self.built, self.err)
        self.assertEqual(self.results[iid], state.PLANNED, self.err)
        held = self._held_lines(iid)
        self.assertEqual(len(held), 1, self.err)
        self.assertIn(f"issue_{prereq}", held[0])
        self.assertIn(f"not merged into {base}", held[0])
        self.assertIn("merge", held[0].split("To build it,", 1)[-1])
        self.assertNotIn("line of this run", held[0])
        self.assertNotIn("carries them", held[0])

    def _held_for_no_pr(self, iid: str, prereq: str) -> None:
        """``iid`` was not built, is PLANNED, and is named on ONE line as held because
        ``prereq`` has no PR of its accepted work to merge, with the way out (publish it,
        then merge its PR) — never as waiting for a PR that exists; the run fails (1)."""
        self.assertNotIn(iid, self.built, self.err)
        self.assertEqual(self.results[iid], state.PLANNED, self.err)
        held = self._held_lines(iid)
        self.assertEqual(len(held), 1, self.err)
        self.assertIn(f"issue_{prereq}", held[0])
        self.assertIn("no PR of that work is on record", held[0])
        self.assertIn(f"publish them (`pdca publish <id>` for {prereq})", held[0])
        self.assertNotIn("not merged into", held[0])
        self.assertNotIn("line of this run", held[0])
        self.assertNotIn(iid, self.holds)
        self.assertEqual(self.rc, 1)

    def _held_for_no_landing(self, iid: str, prereq: str, why: str) -> None:
        """``iid`` was not built, is PLANNED, and is named on ONE line as held because no
        merge of ``prereq``'s PR can count for main, for reason ``why``, with a way out that
        can work: never told to merge it. An ``"unmerged"`` hold: nothing failed (3)."""
        self.assertNotIn(iid, self.built, self.err)
        self.assertEqual(self.results[iid], state.PLANNED, self.err)
        held = self._held_lines(iid)
        self.assertEqual(len(held), 1, self.err)
        self.assertIn(f"prerequisite(s) issue_{prereq} ({why}): no merge of their PR counts as "
                      f"landing on main (org/repo), so none will release issue_{iid}", held[0])
        self.assertIn(f"To build it, remove that edge from issue_{iid}'s brief, or rebuild them "
                      f"with their PR against org/repo @ main", held[0])
        self.assertNotIn("merge the PR", held[0])
        self.assertNotIn("merge their PR", held[0])
        self.assertEqual(self.holds.get(iid), "unmerged")
        self.assertEqual(self.rc, 3)

    def _published_on_the_base(self, iid: str) -> dict:
        """``iid`` was built from origin/main, and its PR branch cut from origin's main and
        published as a plain PR against main."""
        self.assertEqual(self.built.get(iid), ("origin/main", ""), self.err)
        rec = self._record(iid)
        self.assertEqual((rec["mode"], rec["base"]), ("new-pr", "main"))
        self.assertEqual(rec["cut_from"], self.fx._tip("main"))
        self.assertEqual(rec["pr_url"], PR_URL + iid)
        return rec

    # -- (a): independent bundles publish against the base; the dependent waits -----------

    def test_independent_bundles_publish_on_the_base_and_a_dependent_is_held(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("12", {"c.txt": "c\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11", "12"], ["10", "11", "12"])

        self.assertEqual(self._pr_bases(), {"10": "main", "12": "main"}, self.err)
        self._published_on_the_base("10")
        self._published_on_the_base("12")
        self.assertEqual((self.results["10"], self.results["12"]),
                         (state.COMPLETE, state.COMPLETE))
        self._nothing_at_the_boundary()
        self._held_unmerged("11", "10")
        self.assertEqual(self.holds, {"11": "unmerged"})
        self.assertEqual(self.rc, 3)

    # -- (b): once the prerequisite merged, a re-run builds it on the fetched base ----------

    def test_once_the_prerequisite_merged_a_rerun_builds_the_dependent_on_the_base(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_unmerged("11", "10")

        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        rec = self._published_on_the_base("11")
        # The base it was cut from has the prerequisite's merge.
        self.assertTrue(self.fx._ancestor(self.merged_prs[PR_URL + "10"][1], rec["cut_from"]))
        self.assertEqual(self._held_lines("11"), [], self.err)
        self._nothing_at_the_boundary()
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- (a2): a `Stacks on` edge is held the same way, and released onto the base ---------

    def test_a_stacks_on_dependent_waits_for_the_merge_and_publishes_against_the_base(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, stacks_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._pr_bases(), {"10": "main"}, self.err)
        self._nothing_at_the_boundary()
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        # Built from, cut from, and opened against the base — never 10's branch.
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        self._published_on_the_base("11")
        self._nothing_at_the_boundary()
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- every edge, in the batch or not: `Depends on (merged)`, and a prior run's prereq --

    def test_a_depends_on_merged_edge_in_the_batch_is_held_the_same_way(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on_merged="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._pr_bases(), {"10": "main"}, self.err)
        self._nothing_at_the_boundary()
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        self._published_on_the_base("11")
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_prerequisite_an_earlier_run_finished_holds_its_dependent_the_same_way(self):
        # 10 is neither driven nor asked for: the path stack mode's #647 hold takes, with
        # its "name it in the same command so the run's line carries it" advice.
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self.assertEqual(self._pr_bases(), {"10": "main"}, self.err)
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["11"], ["11"])
        self._held_unmerged("11", "10")
        self.assertNotIn("same `pdca flow <ids>` command", self.err)
        self._nothing_at_the_boundary()
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

        self._merge_pr("10")
        self._run(["11"], ["11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        self._published_on_the_base("11")
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_closed_pr_is_named_with_the_step_to_re_open_it(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self.assertNotIn("re-open", self._held_line("11"))

        self.closed_prs.add(PR_URL + "10")
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self.assertIn("To build it, re-open the PR of issue_10 and merge it into main, then "
                      "re-run.", self._held_line("11"))
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    def test_a_squash_merge_with_its_branch_deleted_releases_the_dependent(self):
        # Nothing here depends on the PR's own commits reaching the base: the commit the
        # merge put on it is what counts, and the fetched base has that one.
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        branch = json.loads((self.cfg.bundle("10") / "publish.json")
                            .read_text(encoding="utf-8"))["branch"]
        self._merge_pr("10", squash=True)
        self.fx._delete(branch)
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        rec = self._published_on_the_base("11")
        self.assertTrue(self.fx._ancestor(self.merged_prs[PR_URL + "10"][1], rec["cut_from"]))
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- a PR no merge of which can count for the base: named so, never "merge it" ------------

    def test_a_pr_for_another_base_can_never_release_the_dependent(self):
        # A real publish against `dev`. The state does not decide: open or merged, its merge
        # is not on 11's base.
        self.fx._push_from_human({"dev.txt": "dev\n"}, to="dev")
        self._plan("10", {"a.txt": "a\n"}, base="dev")
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._pr_bases(), {"10": "dev"}, self.err)
        self._held_for_no_landing("11", "10", "its PR goes to dev on org/repo")
        self.assertEqual(self._gh("pr", "view"), [])     # no state can change the answer
        self.assertEqual(self.holds, {"11": "unmerged"})

        self._merge_pr("10", into="dev")
        self._run(["11"], ["10", "11"])
        self._held_for_no_landing("11", "10", "its PR goes to dev on org/repo")
        self.assertEqual(self.holds, {"11": "unmerged"})

    def test_a_merge_into_the_bundles_own_base_counts_whichever_branch_that_is(self):
        self.fx._push_from_human({"dev.txt": "dev\n"}, to="dev")
        self._plan("10", {"a.txt": "a\n"}, base="dev")
        self._plan("11", {"b.txt": "b\n"}, depends_on="10", base="dev")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._pr_bases(), {"10": "dev"}, self.err)
        self._held_unmerged_into("dev", "11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

        self._merge_pr("10", into="dev")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"11": "dev"}, self.err)
        self.assertEqual(self._record("11")["cut_from"], self.fx._tip("dev"))
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_pr_on_record_for_another_repo_can_never_release_the_dependent(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        pj = self.cfg.bundle("10") / "publish.json"
        pj.write_text(json.dumps({**self._record("10"), "repo": "org/other"}), encoding="utf-8")
        self._run(["11"], ["10", "11"])
        self._held_for_no_landing("11", "10", "its PR goes to main on org/other")

    def test_an_onto_branch_prerequisite_can_never_release_the_dependent(self):
        # A real `Onto branch` publish: one commit on an existing PR's branch.
        self.fx._push_from_human({"f.txt": "f\n"}, to="feature")
        existing = f"{PR_URL}feature"
        self.opened[existing] = (publish._fork_owner(self.fx.primary), "feature", "main")
        self._plan("10", {"a.txt": "a\n"}, onto_branch="origin/feature")
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        rec = self._record("10")
        self.assertEqual((rec["mode"], rec["pr_url"]), ("stacked", existing))
        self.assertEqual(self._pr_bases(), {}, self.err)
        why = "an `Onto branch` commit on another PR"
        self._held_for_no_landing("11", "10", why)
        self.assertEqual(self.holds, {"11": "unmerged"})

        # That PR merges into 11's own base: the printed step cannot be "merge it" now.
        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self._held_for_no_landing("11", "10", why)
        self.assertEqual(self._gh("pr", "view"), [])

    def test_a_prerequisite_with_no_pr_yet_is_judged_by_where_its_brief_sends_it(self):
        # "Publish it, then merge its PR into main" could not work: its PR goes to dev.
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"}, base="dev")
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_for_no_landing("11", "10", "its PR goes to dev on org/repo")
        self.assertEqual(self.holds, {"10": "unpushed", "11": "unmerged"})

    def test_an_onto_branch_prerequisite_with_no_pr_yet_is_named_by_its_brief(self):
        # It targets main, as 11 does: only the `Onto branch` field says its PR cannot count.
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"}, onto_branch="origin/feature")
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_for_no_landing("11", "10", "an `Onto branch` commit on another PR")
        self.assertEqual(self.holds, {"10": "unpushed", "11": "unmerged"})

    def test_a_prerequisite_rebuilt_for_the_bundles_base_is_not_judged_by_its_old_record(self):
        # Published against dev, re-targeted to main and rebuilt, its texts failing: the record
        # is the rejected attempt's, so it no longer says where a PR of this work goes.
        self.fx._push_from_human({"dev.txt": "dev\n"}, to="dev")
        self._plan("10", {"a.txt": "a\n"}, base="dev")
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_for_no_landing("11", "10", "its PR goes to dev on org/repo")

        self._plan("10", {"a.txt": "a\n"})       # the brief now says main
        self._iterate("10", {"a.txt": "a, again\n"})
        self.texts_fail.add("10")
        self._run(["10", "11"], ["10", "11"])
        self._held_for_no_pr("11", "10")
        self.assertEqual(self.holds, {"10": "unpushed"})

        self.assertEqual(self._publish("10"), 0, self.err)
        self.assertEqual(self._record("10")["base"], "main")
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    def test_a_link_of_a_chain_bound_for_another_base_is_named_before_it_is_built(self):
        # 11 is on dev: held, for 10's PR goes to main. 12 is on main: 11's PR never will be.
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10", base="dev")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self.assertIn("no merge of their PR counts as landing on dev (org/repo)",
                      self._held_line("11"))
        self._held_for_no_landing("12", "11", "its PR goes to dev on org/repo")
        self.assertEqual(self.holds, {"11": "unmerged", "12": "unmerged"})

    # -- a dependent with no target of its own: #186's "not ready", not a hold ---------------

    def test_a_dependent_with_no_target_is_not_ready_until_its_prerequisite_merges(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10", target=False)
        self._run(["10", "11"], ["10", "11"])
        self.assertNotIn("11", self.built, self.err)
        self.assertEqual(self.results["11"], state.PLANNED)
        self.assertEqual(self._held_lines("11"), [], self.err)
        self.assertIn("flow: issue_11 skipped — prerequisite(s) not ready (10)", self.err)
        self.assertEqual((self.holds, self.rc), ({}, 1))

        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(self.built["11"], (None, ""), self.err)   # no target, no PR
        self.assertEqual(self._pr_bases(), {}, self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- a prerequisite with no PR of its accepted work: nothing to merge, a failure -------

    def test_a_prerequisite_whose_texts_failed_has_no_pr_and_its_dependent_fails(self):
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self.results["10"], state.COMPLETE)
        self.assertFalse((self.cfg.bundle("10") / "publish.json").exists())
        self.assertEqual(self._pr_bases(), {}, self.err)
        self.assertIn("flow: issue_10 pushed no branch this run — no PR holds its accepted "
                      "work; bundles that depend on it are held this run.", self.err)
        self._held_for_no_pr("11", "10")
        self.assertEqual(self.holds, {"10": "unpushed"})
        self.assertEqual(self._gh("pr", "view"), [])
        self._nothing_at_the_boundary()

    def test_a_prerequisite_whose_pr_was_not_opened_has_no_pr_and_its_dependent_fails(self):
        self.create_fails.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        rec = self._record("10")
        self.assertTrue(self.fx._has(rec["branch"]), self.err)   # its branch was pushed …
        self.assertEqual(rec["pr_url"], "")                       # … but no PR was opened
        self._held_for_no_pr("11", "10")
        self.assertEqual(self.holds, {"10": "no-pr"})
        self.assertEqual(self._gh("pr", "view"), [])
        self._nothing_at_the_boundary()

    def test_an_iterated_prerequisite_not_published_again_is_not_waited_on_by_its_old_pr(
            self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_unmerged("11", "10")
        # 10 is iterated, rebuilt and accepted, but its texts fail: PR 10 holds the old,
        # rejected work.
        self._iterate("10", {"a.txt": "a, again\n"})
        self.texts_fail.add("10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._record("10")["pr_url"], PR_URL + "10")   # still on record
        self._held_for_no_pr("11", "10")
        self.assertEqual(self.holds, {"10": "unpushed"})
        self.assertEqual(self._gh("pr", "view"), [])               # … and never asked about
        self._nothing_at_the_boundary()

        # A re-run does not drive 10 (it is COMPLETE) and has no memory of the last one: the
        # record itself says it is an earlier attempt's.
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.holds, {})
        self._held_for_no_pr("11", "10")
        self.assertEqual(self._gh("pr", "view"), [])

        # … so the old PR's merge does not release 11: what merged is not what was accepted.
        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.holds, {})
        self._held_for_no_pr("11", "10")
        self.assertNotIn("11", self.built, self.err)

    def test_publishing_an_iterated_prerequisite_again_makes_its_pr_the_one_to_merge(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._iterate("10", {"a.txt": "a, again\n"})
        self.texts_fail.add("10")
        self._run(["10", "11"], ["10", "11"])
        self._held_for_no_pr("11", "10")

        # The way out its line names: `pdca publish 10`. The open PR takes the rebuilt work.
        self.assertEqual(self._publish("10"), 0, self.err)
        rec = self._record("10")
        self.assertEqual(rec["pr_url"], PR_URL + "10")
        self.assertEqual(sb._git(self.fx.origin, "show", f"{rec['branch']}:a.txt"), "a, again\n")
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(sb._git(self.fx.origin, "show", "main:a.txt"), "a, again\n")
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_rebuild_with_the_same_patch_keeps_its_pr_on_later_runs(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._iterate("10", {"a.txt": "a\n"})
        self.texts_fail.add("10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self.holds, {"10": "unpushed"})   # this run pushed nothing of it …
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")                    # … but PR 10 does hold that patch
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    def test_a_record_written_before_the_patch_digest_counts_as_the_accepted_work(self):
        # An instance switching to "none": its bundles were published by an older harness.
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        rec = self._record("10")
        rec.pop("patch_sha256", None)
        (self.cfg.bundle("10") / "publish.json").write_text(json.dumps(rec), encoding="utf-8")
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- an iterated bundle whose PR is still open: the push updated it, and it counts --------

    def test_an_iterated_prerequisite_keeps_its_open_pr_and_its_merge_releases_the_dependent(
            self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._iterate("10", {"a.txt": "a, again\n"})
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(len(self._gh("pr", "create")), 1, self.err)   # refused, as the host does
        rec = self._record("10")
        self.assertEqual(rec["pr_url"], PR_URL + "10", self.err)
        self.assertEqual(sb._git(self.fx.origin, "show", f"{rec['branch']}:a.txt"), "a, again\n")
        self.assertNotIn("FAILED", self.err)
        self.assertIn("is already open for", self.out)
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual(sb._git(self.fx.origin, "show", "main:a.txt"), "a, again\n")
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_lone_iterated_bundle_whose_pr_is_still_open_is_a_clean_run(self):
        self._plan("10", {"a.txt": "a\n"})
        self.assertEqual(self._pdca_flow("10"), 0, self.err)
        self._iterate("10", {"a.txt": "a, again\n"})
        self.assertEqual(self._pdca_flow("10"), 0, self.err)
        self.assertEqual(self._record("10")["pr_url"], PR_URL + "10")

    def test_an_iterated_bundle_whose_old_pr_merged_gets_a_new_pr(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._merge_pr("10")
        # A follow-up on the same bundle: the merged PR must not be taken for it.
        self._iterate("10", {"z.txt": "z\n"})
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._record("10")["pr_url"], PR_URL + "10-2", self.err)
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    def test_an_old_pr_that_merged_is_not_taken_when_no_new_one_can_be_opened(self):
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self._merge_pr("10")
        self._iterate("10", {"z.txt": "z\n"})
        self.create_fails.add("10")
        self._run(["10"], ["10"])
        self.assertEqual(self._record("10")["pr_url"], "", self.err)
        self.assertEqual((self.holds, self.rc), ({"10": "no-pr"}, 3))

    def test_a_failed_lookup_leaves_no_pr_and_pdca_publish_is_the_way_out(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._iterate("10", {"a.txt": "a, again\n"})
        self.list_fails = True
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self._record("10")["pr_url"], "")
        self.assertIn("`gh pr create` FAILED", self.err)
        self._held_for_no_pr("11", "10")
        self.assertEqual(self.holds, {"10": "no-pr"})

        self.list_fails = False
        self.assertEqual(self._publish("10"), 0, self.err)
        self.assertEqual(self._record("10")["pr_url"], PR_URL + "10")
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    def test_a_pr_opened_by_hand_counts_once_pdca_publish_records_it(self):
        self.create_fails.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self.assertIn("A PR opened by hand counts only once that re-run records it", self.err)
        rec = self._record("10")
        self.assertEqual(rec["pr_url"], "")
        by_hand = f"{PR_URL}by-hand"
        self.opened[by_hand] = (publish._fork_owner(self.fx.primary), rec["branch"], "main")
        self.assertEqual(self._publish("10"), 0, self.err)
        self.assertEqual(self._record("10")["pr_url"], by_hand)

    def test_a_missing_gh_on_the_lookup_still_records_the_pushed_branch(self):
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self._iterate("10", {"a.txt": "a, again\n"})
        self.gh_missing = True
        self._run(["10"], ["10"])
        rec = self._record("10")
        self.assertEqual(rec["pr_url"], "")
        self.assertEqual(sb._git(self.fx.origin, "show", f"{rec['branch']}:a.txt"), "a, again\n")
        self.assertEqual((self.holds, self.rc), ({"10": "no-pr"}, 3))

    def test_an_open_pr_for_another_base_is_not_taken_for_the_bundles_own(self):
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        rec = self._record("10")
        self.opened[PR_URL + "10"] = (self.opened[PR_URL + "10"][0], rec["branch"], "dev")
        self.create_fails.add("10")
        self._iterate("10", {"a.txt": "a, again\n"})
        self._run(["10"], ["10"])
        self.assertEqual(self._record("10")["pr_url"], "", self.err)
        self.assertEqual(self.holds, {"10": "no-pr"})

    def test_an_open_pr_of_another_owner_is_not_taken_for_the_bundles_own(self):
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        rec = self._record("10")
        self.opened[PR_URL + "10"] = ("someone-else", rec["branch"], "main")
        self.create_fails.add("10")
        self._iterate("10", {"a.txt": "a, again\n"})
        self._run(["10"], ["10"])
        self.assertEqual(self._record("10")["pr_url"], "", self.err)
        self.assertEqual(self.holds, {"10": "no-pr"})

    def test_the_other_modes_keep_their_record_when_gh_pr_create_is_refused(self):
        # (d): the lookup is "none"'s own. There, the PR's URL decides what is released.
        for mode, iid in (("stack", "20"), ("merge", "30")):
            with self.subTest(mode=mode):
                self.cfg.wave_mode = mode
                self._plan(iid, {f"{iid}.txt": "a\n"})
                self._run([iid], [iid])
                self.assertEqual(self._record(iid)["pr_url"], PR_URL + iid)
                self._iterate(iid, {f"{iid}.txt": "a, again\n"})
                self._run([iid], [iid])
                self.assertEqual(self._record(iid)["pr_url"], "", self.err)
                self.assertEqual(self._gh("pr", "list"), [])
                self.assertIn("`gh pr create` FAILED", self.err)
                self.assertNotIn("A PR opened by hand counts", self.err)
                self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_conflicts_with_partner_of_a_bundle_that_pushed_no_branch_is_still_built(self):
        # A `Conflicts with` edge only orders the build here: no bundle is built on its
        # partner's work, so the partner of one that pushed no branch is not held for it
        # (stack mode's #629 hold, with its advice about a line), and is built on the base.
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("12", {"c.txt": "c\n"}, conflicts_with="10")
        self._run(["10", "12"], ["10", "12"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "12": state.COMPLETE}, self.err)
        self.assertEqual(self._held_lines("12"), [], self.err)
        self.assertEqual(self._pr_bases(), {"12": "main"}, self.err)
        self._published_on_the_base("12")
        self.assertEqual((self.holds, self.rc), ({"10": "unpushed"}, 3))
        self._nothing_at_the_boundary()

    # -- a bundle left with no PR is never a clean run, in any wave, the last one too ------

    def test_an_independent_bundle_whose_texts_failed_is_not_a_clean_run(self):
        # One wave, so that wave is the last, and nothing depends on 10.
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("12", {"c.txt": "c\n"})
        self._run(["10", "12"], ["10", "12"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "12": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"12": "main"}, self.err)
        self._published_on_the_base("12")
        self.assertEqual(self.err.count("flow: issue_10 pushed no branch this run"), 1, self.err)
        self.assertEqual((self.holds, self.rc), ({"10": "unpushed"}, 3))
        self._nothing_at_the_boundary()

    def test_an_independent_bundle_whose_pr_was_not_opened_is_not_a_clean_run(self):
        # The branch is pushed, so "pushed no branch" cannot see this one.
        self.create_fails.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("12", {"c.txt": "c\n"})
        self._run(["10", "12"], ["10", "12"])
        rec = self._record("10")
        self.assertTrue(self.fx._has(rec["branch"]), self.err)
        self.assertEqual(rec["pr_url"], "")
        self._published_on_the_base("12")
        self.assertEqual(self.err.count("flow: issue_10 pushed its branch this run"), 1, self.err)
        self.assertEqual((self.holds, self.rc), ({"10": "no-pr"}, 3))
        self._nothing_at_the_boundary()

    def test_a_one_bundle_run_whose_publish_failed_is_not_a_clean_run(self):
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self.assertEqual((self.results, self.holds, self.rc),
                         ({"10": state.COMPLETE}, {"10": "unpushed"}, 3), self.err)

    def test_a_failed_publish_in_the_last_wave_of_a_batch_is_not_a_clean_run(self):
        # 11 is released by 10's merge, in the batch's last wave, and its PR is not opened.
        self.create_fails.add("11")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._merge_pr("10")
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual((self.holds, self.rc), ({"11": "no-pr"}, 3))

    def test_a_bundle_publish_skips_is_not_reported_as_having_no_pr(self):
        # No target: publish skips it. No patch: a close/no-fix, nothing to contribute.
        self._plan("10", {"a.txt": "a\n"}, target=False)
        self._plan("12", {})
        self._run(["10", "12"], ["10", "12"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "12": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {}, self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_stack_mode_keeps_its_answer_for_a_failed_publish(self):
        # (d): the accounting above is "none"'s own. With no later wave stack mode reports
        # nothing (the fold it guards never runs); with one, its own line and hold stand.
        self.cfg.wave_mode = "stack"
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("12", {"c.txt": "c\n"})
        self._run(["10", "12"], ["10", "12"])
        self.assertEqual((self.holds, self.rc), ({}, 0))
        self.assertNotIn("pushed no branch", self.err)

        self._plan("20", {"d.txt": "d\n"})
        self._plan("21", {"e.txt": "e\n"}, depends_on="20")
        self.texts_fail.add("20")
        self._run(["20", "21"], ["20", "21"])
        self.assertIn("flow: issue_20 pushed no branch this run — left out of the integration "
                      "fold; bundles that depend on it or are its `Conflicts with` partners "
                      "are held this run.", self.err)
        self.assertEqual((self.holds, self.rc), ({"20": "unpushed"}, 1))

    # -- a prerequisite no PR of which can exist: nothing to wait for ------------------------

    def test_a_prerequisite_with_no_target_has_no_pr_to_wait_for(self):
        self._plan("10", {"a.txt": "a\n"}, target=False)
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "11": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        self._published_on_the_base("11")
        self.assertEqual(self._held_lines("11"), [], self.err)
        self.assertIn("flow: issue_11 — prerequisite issue_10 has no usable `Repo + branch "
                      "target`, so no PR of it can merge; not waiting for it, and built "
                      "without its work.", self.err)
        self.assertEqual(self._gh("pr", "view"), [])
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_prerequisite_with_no_patch_has_nothing_to_wait_for(self):
        self._plan("10", {})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "11": state.COMPLETE}, self.err)
        self._published_on_the_base("11")
        self.assertNotIn("no usable `Repo + branch target`", self.err)
        self.assertEqual(self._gh("pr", "view"), [])
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- a host that cannot be asked is a fault to fix, not a merge to wait for --------------

    def _held_for_a_fault(self, iid: str, *needles: str) -> None:
        """``iid`` was not built, is PLANNED, named on ONE line with ``needles``, and told
        nothing about merging: no hold of its own, so the run fails (1)."""
        self.assertNotIn(iid, self.built, self.err)
        self.assertEqual(self.results[iid], state.PLANNED, self.err)
        held = self._held_lines(iid)
        self.assertEqual(len(held), 1, self.err)
        for needle in needles:
            self.assertIn(needle, held[0])
        self.assertNotIn("merge the PR", held[0])
        self.assertNotIn(iid, self.holds)
        self.assertEqual(self.rc, 1)

    def test_a_host_fault_after_a_good_read_is_not_a_wait_for_a_merge(self):
        # The first read finds the PR MERGED; the host stops answering right after. What
        # the run does not know must not turn into "merge it", an ordinary hold (exit 3).
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._merge_pr("10")
        self.view_reads_left = 1
        self._run(["11"], ["10", "11"])
        self._held_for_a_fault("11", "issue_10", "is not known to have that merge")
        self.assertEqual(self.holds, {})

        # The host answers again: 11 is built.
        self.view_reads_left = None
        self._run(["11"], ["10", "11"])
        self.assertEqual(self.results, {"11": state.COMPLETE}, self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_pr_the_host_cannot_read_is_not_a_wait_for_a_merge(self):
        self.view_fails = True
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_for_a_fault("11", "issue_10", "could not be read",
                               "make sure `gh` can read their PR")
        self.assertEqual(self.holds, {})

        # `gh` works again: an ordinary wait for a merge.
        self.view_fails = False
        self._run(["11"], ["10", "11"])
        self._held_unmerged("11", "10")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    def test_a_missing_gh_is_not_a_wait_for_a_merge(self):
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self.gh_missing = True
        self._run(["11"], ["11"])
        self._held_for_a_fault("11", "issue_10", "could not be read")
        self.assertEqual(self.holds, {})

    def test_a_base_that_cannot_be_fetched_is_not_a_wait_for_a_merge(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._merge_pr("10")
        sb._git(self.fx.primary, "remote", "set-url", "origin", str(self.fx.tmp / "gone.git"))
        self._run(["11"], ["10", "11"])
        self._held_for_a_fault("11", "issue_10", "is not known to have that merge",
                               "can fetch origin")
        self.assertEqual(self.holds, {})

    # -- a chain: every link is held for a merge, and each merge releases the next -----------

    def test_a_chain_is_held_link_by_link_and_each_merge_releases_the_next(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self.assertEqual(self._pr_bases(), {"10": "main"}, self.err)
        self._held_unmerged("11", "10")
        self._held_unmerged("12", "11")
        held = self._held_line("12")
        self.assertIn("(issue_11 not built yet, held too)", held)
        self.assertIn("To build it, merge the PR of issue_10 into main, then merge the PR of "
                      "issue_11 into main, re-running after each step.", held)
        self.assertNotIn("skipped", self.err)
        self._nothing_at_the_boundary()
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged", "12": "unmerged"}, 3))

        self._merge_pr("10")
        self._run(["11", "12"], ["10", "11", "12"])
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        self._published_on_the_base("11")
        self._held_unmerged("12", "11")
        self.assertIn("To build it, merge the PR of issue_11 into main, then re-run.",
                      self._held_line("12"))
        self.assertEqual((self.holds, self.rc), ({"12": "unmerged"}, 3))

        self._merge_pr("11")
        self._run(["12"], ["10", "11", "12"])
        self.assertEqual(self.results, {"12": state.COMPLETE}, self.err)
        self.assertEqual(self._pr_bases(), {"12": "main"}, self.err)
        self._published_on_the_base("12")
        self._nothing_at_the_boundary()
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_longer_chain_names_every_merge_in_order(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._plan("13", {"d.txt": "d\n"}, depends_on="12")
        self._run(["10", "11", "12", "13"], ["10", "11", "12", "13"])
        held = self._held_lines("13")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("(issue_12 not built yet, held too)", held[0])
        self.assertIn("To build it, merge the PR of issue_10 into main, then merge the PR of "
                      "issue_11 into main, then merge the PR of issue_12 into main, re-running "
                      "after each step.", held[0])
        self.assertEqual((self.holds, self.rc),
                         ({"11": "unmerged", "12": "unmerged", "13": "unmerged"}, 3))

    def test_a_chain_above_a_closed_pr_says_to_re_open_it(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10"], ["10", "11", "12"])
        self.closed_prs.add(PR_URL + "10")
        self._run(["11", "12"], ["10", "11", "12"])
        self.assertIn("To build it, re-open the PR of issue_10 and merge it into main, then "
                      "merge the PR of issue_11 into main, re-running after each step.",
                      self._held_line("12"))
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged", "12": "unmerged"}, 3))

    def test_a_chain_above_a_merge_the_fetched_base_lacks_is_told_about_the_fetch(self):
        # 10's PR has merged: nobody can merge it again. The fault is the fetch, for 12 too.
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10"], ["10", "11", "12"])
        self.merged_prs[PR_URL + "10"] = (self.fx._tip(self._record("10")["branch"]), sb.ABSENT)
        self._run(["11", "12"], ["10", "11", "12"])
        self.assertIn("origin/main as fetched", self._held_line("11"))
        held = self._held_line("12")
        self.assertIn("(issue_11 not built yet, held too)", held)
        self.assertIn("To build it, make sure org/repo's checkout can fetch origin, so "
                      "origin/main has the merge of issue_10, then merge the PR of issue_11 "
                      "into main, re-running after each step.", held)
        self.assertNotIn("merge the PR of issue_10", held)
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged", "12": "unmerged"}, 3))

    def test_a_chain_above_a_pr_that_cannot_land_names_the_edge_to_change(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10"], ["10", "11", "12"])
        pj = self.cfg.bundle("10") / "publish.json"
        pj.write_text(json.dumps({**self._record("10"), "base": "dev"}), encoding="utf-8")
        self._run(["11", "12"], ["10", "11", "12"])
        self._held_for_no_landing("11", "10", "its PR goes to dev on org/repo")
        held = self._held_lines("12")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("To build it, remove the edge to issue_10 from issue_11's brief, or rebuild "
                      "issue_10 with its PR against org/repo @ main, then merge the PR of "
                      "issue_11 into main, re-running after each step.", held[0])
        self.assertNotIn("merge the PR of issue_10", held[0])
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged", "12": "unmerged"}, 3))

    def test_a_chain_is_held_through_every_edge_kind(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, stacks_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on_merged="11")
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self._held_unmerged("11", "10")
        self._held_unmerged("12", "11")
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged", "12": "unmerged"}, 3))

    def test_a_bundle_behind_two_paths_names_each_merge_once(self):
        # 13 depends on 11 and 12, each held for 10, and on 10 itself.
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="10")
        self._plan("13", {"d.txt": "d\n"}, depends_on="10, 11, 12")
        self._run(["10", "11", "12", "13"], ["10", "11", "12", "13"])
        held = self._held_lines("13")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("prerequisite(s) issue_10, issue_11, issue_12 not merged into main", held[0])
        self.assertIn("(issue_11, issue_12 not built yet, held too)", held[0])
        self.assertIn("To build it, merge the PR of issue_10 into main, then merge the PR of "
                      "issue_11 into main, then merge the PR of issue_12 into main, re-running "
                      "after each step.", held[0])
        self.assertEqual(held[0].count("merge the PR of issue_10"), 1)
        self.assertEqual(self.holds["13"], "unmerged")
        self.assertEqual(self.rc, 3)

    def test_a_chain_above_a_failed_publish_fails_the_run(self):
        # 11 cannot wait for a merge, so neither can 12: this run failed, it is not waiting.
        self.texts_fail.add("10")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self._held_for_no_pr("11", "10")
        self.assertNotIn("12", self.built, self.err)
        self.assertEqual(self._held_lines("12"), [], self.err)
        self.assertIn("flow: issue_12 skipped — prerequisite(s) not ready (11)", self.err)
        self.assertEqual((self.holds, self.rc), ({"10": "unpushed"}, 1))

    def test_a_chain_above_an_unreadable_pr_fails_the_run(self):
        self.view_fails = True
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self._held_for_a_fault("11", "could not be read")
        self.assertEqual(self._held_lines("12"), [], self.err)
        self.assertIn("flow: issue_12 skipped — prerequisite(s) not ready (11)", self.err)
        self.assertEqual((self.holds, self.rc), ({}, 1))

    def test_a_bundle_behind_a_wait_and_a_failure_is_not_counted_as_waiting(self):
        self.texts_fail.add("20")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")   # waits for 10's merge
        self._plan("20", {"e.txt": "e\n"})
        self._plan("21", {"f.txt": "f\n"}, depends_on="20")   # 20 has no PR: a failure
        self._plan("30", {"g.txt": "g\n"}, depends_on="11, 21")
        self._run(["10", "11", "20", "21", "30"], ["10", "11", "20", "21", "30"])
        self.assertNotIn("30", self.built, self.err)
        self.assertEqual(self.results["30"], state.PLANNED)
        self.assertIn("flow: issue_30 skipped — prerequisite(s) not ready (21)", self.err)
        self.assertEqual(self.holds, {"11": "unmerged", "20": "unpushed"})
        self.assertEqual(self.rc, 1)

    def test_a_dependent_with_no_target_behind_a_chain_is_not_ready(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11", target=False)
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self.assertEqual(self._held_lines("12"), [], self.err)
        self.assertIn("flow: issue_12 skipped — prerequisite(s) not ready (11)", self.err)
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 1))

    # -- the exit code `pdca flow` itself returns, through `cli._flow` -----------------------

    def test_pdca_flow_exits_3_while_a_chain_waits_and_0_once_it_has_merged(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, stacks_on="11")
        ids = ("10", "11", "12")
        self.assertEqual(self._pdca_flow(*ids), 3, self.err)
        self.assertEqual(self._pr_bases(), {"10": "main"}, self.err)
        self.assertEqual(self.out.splitlines()[-1], "flow: 1/3 complete")

        self._merge_pr("10")
        self.assertEqual(self._pdca_flow(*ids), 3, self.err)
        self.assertEqual(self._pr_bases(), {"11": "main"}, self.err)
        self.assertEqual(self.out.splitlines()[-1], "flow: 2/3 complete")

        self._merge_pr("11")
        self.assertEqual(self._pdca_flow(*ids), 0, self.err)
        self.assertEqual(self._pr_bases(), {"12": "main"}, self.err)
        self.assertEqual(self.out.splitlines()[-1], "flow: 3/3 complete")
        self._nothing_at_the_boundary()

    def test_pdca_flow_of_one_id_exits_3_when_held_and_when_left_with_no_pr(self):
        self._plan("10", {"a.txt": "a\n"})
        self.assertEqual(self._pdca_flow("10"), 0, self.err)
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self.assertEqual(self._pdca_flow("11"), 3, self.err)
        self.assertEqual(self.out.splitlines()[0].split("\t")[0], state.PLANNED)

        self._plan("20", {"e.txt": "e\n"})
        self.texts_fail.add("20")
        self.assertEqual(self._pdca_flow("20"), 3, self.err)
        self.assertEqual(self.out.splitlines()[-1].split("\t")[0], state.COMPLETE)

    def test_pdca_flow_exits_1_when_the_host_cannot_be_asked(self):
        self._plan("10", {"a.txt": "a\n"})
        self.assertEqual(self._pdca_flow("10"), 0, self.err)
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self.view_fails = True
        self.assertEqual(self._pdca_flow("11"), 1, self.err)

    def test_pdca_flow_exits_1_on_every_run_while_only_an_older_attempt_has_a_pr(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self.assertEqual(self._pdca_flow("10", "11"), 3, self.err)
        self._iterate("10", {"a.txt": "a, again\n"})
        self.texts_fail.add("10")
        self.assertEqual(self._pdca_flow("10", "11"), 1, self.err)
        self.assertEqual(self._pdca_flow("10", "11"), 1, self.err)   # 10 is not driven now
        self._merge_pr("10")
        self.assertEqual(self._pdca_flow("10", "11"), 1, self.err)   # … and the old PR merged
        self.assertEqual(self._gh("pr", "view"), [])

    # -- nothing waits, and no host is asked, with --no-publish or in a dry-run ------------

    def test_with_no_publish_a_dependent_builds_on_the_unchanged_base(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"], do_publish=False)
        self.assertEqual(self.results, {"10": state.COMPLETE, "11": state.COMPLETE}, self.err)
        self.assertEqual(self.built["11"], ("origin/main", ""), self.err)
        self.assertEqual(self.gh_calls, [], self.err)
        self.assertEqual(self._integration_branches(), [], self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_dry_run_asks_no_host_holds_nothing_and_plans_every_pr_on_the_base(self):
        self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="stub")
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, stacks_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "11": state.COMPLETE}, self.err)
        self.assertEqual(self.built["11"], ("origin/main", ""), self.err)
        self.assertEqual(self._held_lines("11"), [], self.err)
        self.assertEqual(self.gh_calls, [], self.err)
        self.assertFalse((self.cfg.bundle("10") / "publish.json").exists())
        plan = [x for x in self.out.splitlines()
                if x.startswith("publish --dry-run — issue_11 → ")]
        self.assertEqual(len(plan), 1, self.out)
        self.assertIn("draft PR on org/repo (", plan[0])
        self.assertTrue(plan[0].endswith(" → main):"), plan[0])
        self.assertEqual(self._integration_branches(), [], self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_rehearsal_does_not_wait_for_a_merged_edge_inside_the_run(self):
        for how, iid in (("no-publish", 20), ("stub", 30)):
            with self.subTest(how=how):
                self.cfg.publisher = dataclasses.replace(
                    self.cfg.publisher, mode="stub" if how == "stub" else "command")
                first, second = str(iid), str(iid + 1)
                self._plan(first, {f"{first}.txt": "a\n"})
                self._plan(second, {f"{second}.txt": "b\n"}, depends_on_merged=first)
                self._run([first, second], [first, second], do_publish=how != "no-publish")
                self.assertEqual(self.results, {first: state.COMPLETE, second: state.COMPLETE},
                                 self.err)
                self.assertEqual(self._gh("pr", "view"), [])
                self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_rehearsal_keeps_the_gate_on_a_merged_edge_out_of_the_run(self):
        # The exception to "nothing waits": #186's gate, the same in every mode. It asks the
        # host, holds until the merge, exits 1, and under "none" speaks of no line.
        for how, iid in (("no-publish", 20), ("stub", 30)):
            with self.subTest(how=how):
                do_publish = how != "no-publish"
                first, second = str(iid), str(iid + 1)
                self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
                self._plan(first, {f"{first}.txt": "a\n"})
                self._run([first], [first])                  # a real publish: its PR is open
                self._plan(second, {f"{second}.txt": "b\n"}, depends_on_merged=first)
                if how == "stub":
                    self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="stub")
                self._run([second], [second], do_publish=do_publish)
                self.assertEqual(self.results, {second: state.PLANNED}, self.err)
                self.assertNotIn(second, self.built, self.err)
                self.assertEqual(len(self._gh("pr", "view")), 1, self.err)
                held = self._held_lines(second)
                self.assertEqual(len(held), 1, self.err)
                self.assertIn(f"prerequisite(s) issue_{first} not merged into main (org/repo); "
                              f"not built on a base missing them. To build it, wait until their "
                              f"PR merges into main, then re-run.", held[0])
                self.assertNotIn("line of this run", held[0])
                self.assertEqual((self.holds, self.rc), ({}, 1))

                self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
                self._merge_pr(first)
                if how == "stub":
                    self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="stub")
                self._run([second], [second], do_publish=do_publish)
                self.assertEqual(self.results, {second: state.COMPLETE}, self.err)
                self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_rehearsal_does_not_wait_for_a_plain_edge_out_of_the_run(self):
        for how, iid in (("no-publish", 20), ("stub", 30)):
            with self.subTest(how=how):
                first, second = str(iid), str(iid + 1)
                self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="command")
                self._plan(first, {f"{first}.txt": "a\n"})
                self._run([first], [first])
                self._plan(second, {f"{second}.txt": "b\n"}, depends_on=first)
                if how == "stub":
                    self.cfg.publisher = dataclasses.replace(self.cfg.publisher, mode="stub")
                self._run([second], [second], do_publish=how != "no-publish")
                self.assertEqual(self.results, {second: state.COMPLETE}, self.err)
                self.assertEqual(self._gh("pr", "view"), [])
                self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_stack_mode_keeps_its_line_for_a_merged_edge_out_of_the_run(self):
        # (d): only "none" drops the words about a line.
        self.cfg.wave_mode = "stack"
        self._plan("10", {"a.txt": "a\n"})
        self._run(["10"], ["10"])
        self._plan("11", {"b.txt": "b\n"}, depends_on_merged="10")
        self._run(["11"], ["11"], do_publish=False)
        self.assertIn("prerequisite(s) issue_10 not merged into main (org/repo), and no line of "
                      "this run carries them;", self._held_line("11"))
        self.assertEqual((self.holds, self.rc), ({}, 1))

    # -- (b2): merged, but the base as fetched lacks the merge: still held -----------------

    def test_a_merged_prerequisite_the_fetched_base_lacks_still_holds_the_dependent(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self._held_unmerged("11", "10")

        # gh reads 10's PR MERGED, but origin's main has neither its merge commit nor head.
        branch = json.loads((self.cfg.bundle("10") / "publish.json")
                            .read_text(encoding="utf-8"))["branch"]
        self.merged_prs[PR_URL + "10"] = (self.fx._tip(branch), sb.ABSENT)
        self.assertFalse(self.fx._ancestor(self.fx._tip(branch), "main"))
        self._run(["11"], ["10", "11"])
        self.assertNotIn("11", self.built, self.err)
        self.assertEqual(self.results, {"11": state.PLANNED}, self.err)
        self.assertEqual(self._pr_bases(), {}, self.err)
        held = self._held_lines("11")
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("issue_10", held[0])
        self.assertIn("origin/main as fetched", held[0])
        self._nothing_at_the_boundary()
        self.assertEqual((self.holds, self.rc), ({"11": "unmerged"}, 3))

    # -- control: the same batch in stack mode still folds (the fixture can show a line) ---

    def test_the_same_batch_in_stack_mode_still_folds_a_line_and_builds_the_dependent(self):
        self.cfg.wave_mode = "stack"
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._plan("12", {"c.txt": "c\n"}, depends_on="11")
        self._run(["10", "11", "12"], ["10", "11", "12"])
        self.assertNotEqual(self._integration_branches(), [], self.err)   # a line, pushed
        self.assertEqual(self.results, {"10": state.COMPLETE, "11": state.COMPLETE,
                                        "12": state.COMPLETE}, self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    def test_a_prerequisite_with_no_target_builds_its_dependent_in_stack_mode_too(self):
        self.cfg.wave_mode = "stack"
        self._plan("10", {"a.txt": "a\n"}, target=False)
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        self._run(["10", "11"], ["10", "11"])
        self.assertEqual(self.results, {"10": state.COMPLETE, "11": state.COMPLETE}, self.err)
        self.assertNotIn("no usable `Repo + branch target`, so no PR", self.err)
        self.assertEqual((self.holds, self.rc), ({}, 0))

    # -- `pdca waves` says what "none" does, not what stack mode does -----------------------

    def test_the_waves_preview_does_not_claim_a_wave_builds_on_the_prior(self):
        self._plan("10", {"a.txt": "a\n"})
        self._plan("11", {"b.txt": "b\n"}, depends_on="10")
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = cli._waves(self.cfg, ["10", "11"])
        self.assertEqual(rc, 0)
        self.assertIn("(none mode", out.getvalue())
        self.assertNotIn("builds on the prior's accepted work", out.getvalue())


class WaveModeAtLoad(unittest.TestCase):
    """(c): `[driver].wave_mode` through the REAL loader."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def _load(self, value: str) -> tuple[config.Config, str]:
        (self.root / "pdca.toml").write_text(
            f'[paths]\nbundle_root = "results"\n\n[driver]\nwave_mode = "{value}"\n',
            encoding="utf-8")
        err = io.StringIO()
        with redirect_stderr(err):
            cfg = config.Config.load(self.root)
        return cfg, err.getvalue()

    def test_an_unknown_wave_mode_is_named_and_falls_back_to_stack(self):
        cfg, err = self._load("bogus")
        self.assertEqual(cfg.wave_mode, "stack")
        note = [x for x in err.splitlines() if "wave_mode" in x]
        self.assertEqual(len(note), 1, err)
        for part in ("'bogus'", "stack", "merge", "none"):
            self.assertIn(part, note[0])

    def test_each_known_wave_mode_loads_as_written_without_a_note(self):
        for value in ("stack", "merge", "none"):
            with self.subTest(value=value):
                cfg, err = self._load(value)
                self.assertEqual(cfg.wave_mode, value)
                self.assertNotIn("wave_mode", err)


if __name__ == "__main__":
    unittest.main()
