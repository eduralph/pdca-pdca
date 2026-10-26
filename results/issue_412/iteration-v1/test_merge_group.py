"""A `Merges with` group lands together in merge mode, or is refused up front (#412).

A brief may declare ``- **Merges with:** <id>[, <id>…]``: an atomic merge group, bundles that
must not reach the base separately. With ``[driver].wave_mode = "merge"`` the driver merges
every non-final wave's PRs at its boundary, so before #412 a pair split across waves landed
one PR at a time — or only half, if the run stopped between them. Now a COMPLETE member is
held (no ``gh pr ready``, no ``gh pr merge``, its PR stays a draft) while any member of its
group is not COMPLETE, and the whole group merges back to back at the boundary where the
last member completes. A bundle that depends on a held member is not built. A group the
schedule could never merge together — one member built after another, members that
``Conflicts with`` each other, a member outside the batch — is refused before any Do, with
rc 2 and a ``Ways out:`` line. Stack mode ignores the field.

Offline: bundles on disk, the build / sign-off leaf stubbed (``flow._drive_wave`` writes a
patch, accepts the bundle and records its ``publish.json``), publishing stubbed, and ``gh``
answered by a stub in front of ``subprocess.run`` that records every call — the shape of
tests/test_flow_out_of_batch_prereq_hold.py. The publisher is NOT a stub (a stub publisher
is a dry-run, which merges nothing). ``[driver].merge_requires = "required"`` keeps the
merge itself to ``gh pr ready`` + ``gh pr merge`` (tests/test_merge.py covers the rollup).

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_merge_group
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

from pdca_harness import cli, flow, leaves, merge, publish, signoff, state, waves
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
TODAY = "2026-10-23"
REPO = "org/repo"


def _cfg(root: Path, wave_mode: str) -> Config:
    return Config(
        root=root, bundle_root=root / "results", process_dir=root / "process",
        templates_dir=TEMPLATES, default_branch="main", tracker_system="github",
        tracker_url="", issue_id_example="#1",
        builder=LeafConfig(mode="stub"), reviewer=LeafConfig(mode="stub"),
        planner=LeafConfig(mode="stub", interactive=True),
        signoff=LeafConfig(mode="stub", interactive=True),
        publisher=LeafConfig(mode="command", interactive=True),
        act=LeafConfig(mode="stub", interactive=True), gates_checks=[],
        # Inside the temp dir and never a git checkout: nothing outside it is looked at.
        repo_checkouts={REPO: str(root / "repo")},
        wave_mode=wave_mode, merge_requires="required")


def _url(iid: str) -> str:
    return f"https://github.com/{REPO}/pull/{iid}"


class MergeGroup(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = _cfg(self.tmp, "merge")
        self.discontinue: set[str] = set()    # ids the stub sign-off discontinues
        self.merge_fails: set[str] = set()    # ids whose `gh pr merge` the host refuses
        self.merged: set[str] = set()         # PR urls the host has merged
        self.gh_calls: list[list[str]] = []
        self.built: list[str] = []            # ids, in the order the build leaf ran
        self.calls_at: dict[str, int] = {}    # id → len(gh_calls) when it was built
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _brief(self, iid: str, **fields: str) -> Path:
        """A PLANNED bundle; ``fields`` adds ``- **<Label>:** <value>`` lines, the label
        spelled with spaces for underscores (``merges_with="B"`` → ``Merges with: B``)."""
        d = self.cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        extra = "".join(f"- **{k.replace('_', ' ').capitalize()}:** {v}\n"
                        for k, v in fields.items())
        (d / "brief.md").write_text(
            f"- **Slug:** {iid.lower()}\n- **Repo + branch target:** {REPO} @ main\n{extra}",
            encoding="utf-8")
        return d

    # -- stubs -----------------------------------------------------------------------------

    def _gh_stub(self, args, *a, **kw):
        if not (isinstance(args, list) and args[:1] == ["gh"]):
            return self._real_run(args, *a, **kw)
        self.gh_calls.append(list(args))
        url = next((str(x) for x in args if str(x).startswith("https://")), "")
        if args[:3] == ["gh", "pr", "merge"]:
            if url.rsplit("/", 1)[-1] in self.merge_fails:
                return subprocess.CompletedProcess(args, 1, "", "merge refused by host")
            self.merged.add(url)
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["gh", "pr", "view"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(
                {"state": "MERGED" if url in self.merged else "OPEN"}), "")
        return subprocess.CompletedProcess(args, 0, "", "")

    def _drive_wave(self, cfg, wave: list[Path], **_kw) -> int:
        """Build each bundle and sign it off (accept, or discontinue), recording a published
        PR for an accepted one, as publish would."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            self.built.append(iid)
            self.calls_at[iid] = len(self.gh_calls)
            (d / "patch.diff").write_text(
                f"diff --git a/{iid}.txt b/{iid}.txt\nnew file mode 100644\n--- /dev/null\n"
                f"+++ b/{iid}.txt\n@@ -0,0 +1 @@\n+{iid}\n", encoding="utf-8")
            (d / "check-gates.json").write_text("{}", encoding="utf-8")
            shutil.copyfile(TEMPLATES / "SUMMARY.md.tpl", d / "SUMMARY.md")
            action = "discontinue" if iid in self.discontinue else "accept"
            signoff.record(d / "SUMMARY.md", action=action, by="T", date=TODAY)
            if action == "accept":
                (d / "publish.json").write_text(json.dumps({
                    "mode": "new-pr", "branch": f"fix/{iid}", "base": "main", "repo": REPO,
                    "pr_url": _url(iid), "by": "T", "date": TODAY}), encoding="utf-8")
        return 1

    def _stubs(self, stack: ExitStack) -> None:
        stack.enter_context(mock.patch.object(subprocess, "run", self._gh_stub))
        stack.enter_context(mock.patch.object(flow, "_drive_wave", self._drive_wave))
        stack.enter_context(mock.patch.object(flow, "_publish_bundle", lambda *a, **k: True))
        stack.enter_context(mock.patch.object(publish, "draft_texts", lambda *a, **k: True))
        stack.enter_context(mock.patch.object(leaves, "do_plan_batch", lambda *a, **k: None))
        stack.enter_context(mock.patch.object(merge, "_sleep", lambda *_a: None))

    def _run(self, ids: list[str]) -> None:
        """One merge-mode run driving ``ids`` (publishing on, Act off)."""
        err, out = io.StringIO(), io.StringIO()
        self.holds: dict[str, str] = {}
        with ExitStack() as stack:
            self._stubs(stack)
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(err))
            self.results = flow._drive_and_act(
                self.cfg, [self.cfg.bundle(i) for i in ids], do_publish=True, do_act=False,
                by="T", today=TODAY, batch=ids, holds=self.holds)
        self.err = err.getvalue()
        self.rc = cli._results_rc(self.results, holds=self.holds)
        self.assertNotIn("Traceback", self.err)

    def _cli(self, *argv: str) -> int:
        """``pdca flow <argv>`` through ``cli.main`` on this config."""
        err, out = io.StringIO(), io.StringIO()
        with ExitStack() as stack:
            self._stubs(stack)
            stack.enter_context(mock.patch.object(cli.Config, "load", return_value=self.cfg))
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(err))
            rc = cli.main(["flow", *argv])
        self.err = err.getvalue()
        self.assertNotIn("Traceback", self.err)
        return rc

    # -- reading the gh log ----------------------------------------------------------------

    def _readied_or_merged(self, iid: str, calls: list[list[str]] | None = None
                           ) -> list[list[str]]:
        """Each ``gh pr ready`` (not ``--undo``) / ``gh pr merge`` call on ``iid``'s PR."""
        return [c for c in (self.gh_calls if calls is None else calls)
                if c[:3] in (["gh", "pr", "ready"], ["gh", "pr", "merge"])
                and _url(iid) in c and "--undo" not in c]

    def _merge_index(self, iid: str) -> int:
        at = [n for n, c in enumerate(self.gh_calls)
              if c[:3] == ["gh", "pr", "merge"] and _url(iid) in c]
        self.assertEqual(len(at), 1, (iid, self.gh_calls, self.err))
        return at[0]

    def _lines(self, *needles: str) -> list[str]:
        return [x for x in self.err.splitlines() if all(n in x for n in needles)]

    # -- fixture (a): A + B one group across waves 0 and 1 ----------------------------------

    def _group_across_waves(self, **a_fields: str) -> list[str]:
        """``A`` and ``B`` one group with no edge between them; ``D`` (no group) in wave 0;
        ``B`` `Depends on: D`, so ``A`` is wave 0 and ``B`` wave 1; ``C`` `Depends on: B`,
        wave 2. ``a_fields`` defaults to ``A`` declaring the group too."""
        self._brief("A", **(a_fields or {"merges_with": "B"}))
        self._brief("B", merges_with="A", depends_on="D")
        self._brief("C", depends_on="B")
        self._brief("D")
        return ["A", "B", "C", "D"]

    def _assert_held_then_merged_together(self) -> None:
        # Wave 0's boundary has passed by the time B builds: D merged, A neither readied
        # nor merged — and the run went on.
        self.assertIn("B", self.built, self.err)
        at_b = self.gh_calls[:self.calls_at["B"]]
        self.assertEqual(self._readied_or_merged("A", at_b), [], self.err)
        self.assertNotEqual(self._readied_or_merged("D", at_b), [], self.err)
        self.assertEqual(len(self._lines("issue_A held", "issue_B", "`Merges with`")), 1,
                         self.err)
        self.assertNotIn("STOPPING", self.err)
        # Wave 1's boundary: A and B both merged, A first, before C builds.
        self.assertIn("C", self.built, self.err)
        at_c = self.calls_at["C"]
        self.assertLess(self._merge_index("A"), self._merge_index("B"))
        self.assertLess(self._merge_index("B"), at_c)
        self.assertEqual({_url(i) for i in "ABD"}, self.merged)
        for iid in "ABCD":
            self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        self.assertEqual(self.holds, {})
        self.assertEqual(self.rc, 0, self.err)

    def test_a_group_member_is_held_until_the_group_completes_then_merged_with_it(self):
        # (a)
        self._run(self._group_across_waves())
        self._assert_held_then_merged_together()

    def test_merges_with_declared_on_one_side_binds_both(self):
        # (f) only B declares it; A's brief says nothing — the group is the same.
        self._run(self._group_across_waves(ordering_note="none"))
        self.assertNotIn("Merges with",
                         (self.cfg.bundle("A") / "brief.md").read_text(encoding="utf-8"))
        self._assert_held_then_merged_together()

    # -- (b): a member that ends not COMPLETE leaves the rest held -------------------------

    def test_a_member_that_ends_discontinued_leaves_the_rest_unmerged(self):
        self.discontinue = {"B"}
        self._run(self._group_across_waves())

        self.assertEqual(self.results["B"], state.DISCONTINUED)
        self.assertEqual(self._readied_or_merged("A"), [], self.err)   # never, by the run
        self.assertNotIn(_url("A"), self.merged)
        self.assertNotEqual(self._readied_or_merged("D"), [], self.err)
        held = self._lines("issue_A held", "`Merges with` issue_B")
        self.assertEqual(len(held), 1, self.err)
        end = self._lines("issue_A was not merged", "issue_B is DISCONTINUED")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("can no longer land together", end[0])
        self.assertEqual(self.holds, {"A": "group"})
        self.assertEqual(self.rc, 1, self.err)          # B did not finish

    # -- (c): a dependent of a held member is held -----------------------------------------

    def test_a_bundle_depending_on_a_held_member_is_not_built(self):
        ids = self._group_across_waves() + ["E"]
        self._brief("E", depends_on="A")              # wave 1, beside B
        self._run(ids)

        self.assertNotIn("E", self.built, self.err)
        self.assertEqual(self.results["E"], state.PLANNED)
        why = self._lines("flow: issue_E held", "issue_A")
        self.assertEqual(len(why), 1, self.err)
        self.assertIn("`Merges with` group with issue_B", why[0])
        self.assertNotIn("pushed no branch", why[0])
        # The group itself still lands together at wave 1's boundary.
        self.assertLess(self._merge_index("A"), self._merge_index("B"))

    # -- the final wave, and a member that fails to merge after another landed -------------

    def test_a_group_whose_last_member_completes_in_the_final_wave_stays_all_draft(self):
        self._brief("A", merges_with="B")
        self._brief("B", depends_on="D")
        self._brief("D")
        self._run(["A", "B", "D"])                    # waves [A, D], [B]: B is final

        for iid in "AB":
            self.assertEqual(self._readied_or_merged(iid), [], self.err)
        self.assertIn(_url("D"), self.merged)
        end = self._lines("issue_A was not merged", "issue_B")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("is all COMPLETE", end[0])
        self.assertIn("merge the group's PRs together", end[0])
        self.assertEqual(self.holds, {"A": "group"})
        self.assertEqual(self.rc, 3, self.err)

    def test_a_member_refused_after_another_merged_names_what_landed(self):
        self.merge_fails = {"B"}
        self._run(self._group_across_waves())

        self.assertIn(_url("A"), self.merged)
        self.assertNotIn(_url("B"), self.merged)
        self.assertIn("STOPPING", self.err)
        self.assertNotIn("C", self.built, self.err)
        part = self._lines("landed only in part", "issue_A merged", "issue_B did not")
        self.assertEqual(len(part), 1, self.err)

    # -- (d), (g): refused before any Do in merge mode ------------------------------------

    def _assert_refused(self, rc: int, *ids: str) -> str:
        self.assertEqual(rc, 2, self.err)
        self.assertEqual(self.built, [], self.err)
        self.assertEqual(self.gh_calls, [], self.err)
        self.assertIn("refusing to start — no bundle was built", self.err)
        ways = self._lines("Ways out:")
        self.assertEqual(len(ways), 1, self.err)
        self.assertIn("one bundle", ways[0])
        self.assertIn('wave_mode = "stack"', ways[0])
        head = self._lines("flow: ", "`Merges with`")
        self.assertEqual(len(head), 1, self.err)
        for iid in ids:
            self.assertIn(f"issue_{iid}", head[0])
            self.assertEqual(state.state(self.cfg.bundle(iid)), state.PLANNED)
        return head[0]

    def _chained_pair(self) -> None:
        self._brief("A", merges_with="B")
        self._brief("B", merges_with="A", depends_on="A")

    def test_a_chained_group_is_refused_before_any_do(self):
        # (d)
        self._chained_pair()
        head = self._assert_refused(self._cli("A", "B", "--no-act"), "A", "B")
        self.assertIn("`Depends on` issue_A", head)

    def test_the_chained_group_runs_as_today_in_stack_mode(self):
        # (e) the same batch, wave_mode = "stack": the field is ignored.
        self.cfg.wave_mode = "stack"
        self._chained_pair()
        plan = waves.compute_waves(self.cfg, [self.cfg.bundle("A"), self.cfg.bundle("B")])
        self.assertEqual([[d.name for d in w] for w in plan], [["issue_A"], ["issue_B"]])
        rc = self._cli("A", "B", "--no-publish", "--no-act")
        self.assertEqual(rc, 0, self.err)
        self.assertEqual(self.built, ["A", "B"], self.err)
        self.assertNotIn("Merges with", self.err)

    def test_a_group_whose_members_conflict_is_refused_before_any_do(self):
        # (g) the members `Conflicts with` each other (declared on one side).
        self._brief("A", merges_with="B", conflicts_with="B")
        self._brief("B")
        head = self._assert_refused(self._cli("A", "B", "--no-act"), "A", "B")
        self.assertIn("`Conflicts with` each other", head)

    def test_a_group_naming_an_id_outside_the_batch_is_refused_before_any_do(self):
        # (g) X is an in-flight bundle the run was not asked for.
        self._brief("A", merges_with="X")
        self._brief("X")
        head = self._assert_refused(self._cli("A", "--no-act"), "A", "X")
        self.assertIn("not in this run's batch", head)
        self.assertIn("add X to this run's ids", self._lines("Ways out:")[0])

    # -- the resume sweep holds a refused group instead of crashing -------------------------

    def test_the_sweep_holds_a_refused_group_and_drives_the_rest(self):
        self._chained_pair()
        self._brief("U")
        err = io.StringIO()
        with ExitStack() as stack:
            self._stubs(stack)
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(err))
            results = flow.flow_batch(self.cfg, do_publish=False, do_act=False, by="T",
                                      today=TODAY)
        self.err = err.getvalue()
        self.assertNotIn("Traceback", self.err)
        self.assertEqual(self.built, ["U"], self.err)
        self.assertEqual(results.get("U"), state.COMPLETE)
        for iid in "AB":
            held = self._lines(f"flow: issue_{iid} held this run", "`Merges with`")
            self.assertEqual(len(held), 1, self.err)


if __name__ == "__main__":
    unittest.main()
