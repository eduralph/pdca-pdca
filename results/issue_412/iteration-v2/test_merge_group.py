"""A `Merges with` group lands together in merge mode, or is refused up front (#412).

A brief may declare ``- **Merges with:** <id>[, <id>…]``: an atomic merge group, bundles that
must not reach the base separately. With ``[driver].wave_mode = "merge"`` the driver merges
every non-final wave's PRs at its boundary, so before #412 a pair split across waves landed
one PR at a time — or only half, if the run stopped between them. Now a COMPLETE member is
held (no ``gh pr ready``, no ``gh pr merge``, its PR stays a draft) while its group cannot
all merge — a member is not COMPLETE, or has a publish record merge mode would refuse — and
the whole group merges back to back at the boundary where nothing blocks it any more. A
bundle that depends on a held member is not built. A group left unmerged at the end of the
run, a group wholly in the final wave included, is named with what to do. A group the
schedule could never merge together — one member built after another, members that
``Conflicts with`` each other, a member outside the batch — is refused before any Do, with
rc 2 and a ``Ways out:`` line; the resume sweep holds it instead, and holds a group one of
whose members it holds. A split mid-run does not break a group. Stack mode ignores the field.

Offline: bundles on disk, the build / sign-off leaf stubbed (``flow._drive_wave`` writes a
patch, accepts the bundle and records its ``publish.json``, or splits it through the
production ``split.accept``), publishing stubbed, and ``gh`` answered by a stub in front of
``subprocess.run`` that records every call — the shape of
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

from pdca_harness import cli, flow, leaves, merge, publish, signoff, split, state, waves
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


def _fields(**fields: str) -> str:
    """``- **<Label>:** <value>`` lines, the label spelled with spaces for underscores
    (``merges_with="B"`` → ``Merges with: B``)."""
    return "".join(f"- **{k.replace('_', ' ').capitalize()}:** {v}\n"
                   for k, v in fields.items())


class MergeGroup(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = _cfg(self.tmp, "merge")
        self.discontinue: set[str] = set()    # ids the stub sign-off discontinues
        self.unpublished: set[str] = set()    # ids accepted with no PR recorded (publish failed)
        self.stacked: set[str] = set()        # ids whose record is an `Onto branch` commit
        self.merge_fails: set[str] = set()    # ids whose `gh pr merge` the host refuses
        # id → the children its build splits it into, through `split.accept`: (id, fields).
        self.splits: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.merged: set[str] = set()         # PR urls the host has merged
        self.gh_calls: list[list[str]] = []
        self.built: list[str] = []            # ids, in the order the build leaf ran
        self.calls_at: dict[str, int] = {}    # id → len(gh_calls) when it was built
        self._real_run = subprocess.run

    # -- fixture ---------------------------------------------------------------------------

    def _brief(self, iid: str, **fields: str) -> Path:
        """A PLANNED bundle; ``fields`` adds its ``- **<Label>:** <value>`` lines."""
        d = self.cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "brief.md").write_text(
            f"- **Slug:** {iid.lower()}\n- **Repo + branch target:** {REPO} @ main\n"
            f"{_fields(**fields)}", encoding="utf-8")
        return d

    def _split(self, d: Path, children: list[tuple[str, dict[str, str]]]) -> None:
        """Split ``d`` as `pdca split --accept` does — the PRODUCTION ``split.accept`` writes
        the children, their lineage and the parent's close marker. A proposal's ordering
        fields may only name sibling labels, so each child's ``fields`` are added to its
        brief afterwards, as a re-plan of the child would."""
        blocks = "".join(
            f"<!-- pdca:child child-{n} -->\n- **Slug:** {cid.lower()}\n"
            f"- **Repo + branch target:** {REPO} @ main\n<!-- pdca:end child-{n} -->\n\n"
            for n, (cid, _fields) in enumerate(children, 1))
        (d / split.PROPOSAL).write_text(
            f"<!-- pdca:split-proposal v1 -->\n# Split proposal\n\n{blocks}", encoding="utf-8")
        split.accept(d, [cid for cid, _fields in children], self.cfg)
        for cid, fields in children:
            with (self.cfg.bundle(cid) / "brief.md").open("a", encoding="utf-8") as f:
                f.write(_fields(**fields))

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
        """Build each bundle and sign it off (accept, discontinue, or split), recording a
        published PR for an accepted one, as publish would."""
        for d in wave:
            iid = d.name.removeprefix("issue_")
            self.built.append(iid)
            self.calls_at[iid] = len(self.gh_calls)
            if iid in self.splits:
                self._split(d, self.splits[iid])   # accepted below: terminal on a split
            else:
                (d / "patch.diff").write_text(
                    f"diff --git a/{iid}.txt b/{iid}.txt\nnew file mode 100644\n--- /dev/null\n"
                    f"+++ b/{iid}.txt\n@@ -0,0 +1 @@\n+{iid}\n", encoding="utf-8")
            (d / "check-gates.json").write_text("{}", encoding="utf-8")
            shutil.copyfile(TEMPLATES / "SUMMARY.md.tpl", d / "SUMMARY.md")
            action = "discontinue" if iid in self.discontinue else "accept"
            signoff.record(d / "SUMMARY.md", action=action, by="T", date=TODAY)
            if action == "accept" and iid not in self.splits and iid not in self.unpublished:
                (d / "publish.json").write_text(json.dumps({
                    "mode": "stacked" if iid in self.stacked else "new-pr",
                    "branch": f"fix/{iid}", "base": "main", "repo": REPO,
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

    def _sweep(self, *, do_publish: bool) -> None:
        """The resume sweep (`pdca flow --from-csv`): every in-flight bundle on disk."""
        err = io.StringIO()
        self.holds = {}
        with ExitStack() as stack:
            self._stubs(stack)
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(redirect_stderr(err))
            self.results = flow.flow_batch(self.cfg, do_publish=do_publish, do_act=False,
                                           by="T", today=TODAY, holds=self.holds)
        self.err = err.getvalue()
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

    def _assert_held_then_merged_together(self, merged: tuple[str, ...] = ("A", "B", "D")
                                          ) -> None:
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
        self.assertEqual({_url(i) for i in merged}, self.merged)
        for iid in "ABCD":
            self.assertEqual(self.results[iid], state.COMPLETE, self.err)
        self.assertEqual(self._lines("`Merges with` group", "not merged"), [], self.err)
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

    def test_a_split_before_the_last_member_does_not_break_the_group(self):
        # S splits in wave 0, so the run re-levels its un-driven tail — B and C, plus the
        # child S1 — after A was driven. A is not "outside the batch" for that: B and C are
        # still built, and A and B still merge together at wave 1's boundary.
        ids = self._group_across_waves() + ["S"]
        self._brief("S")
        self.splits = {"S": [("S1", {})]}
        self._run(ids)

        self.assertIn("S1", self.built, self.err)
        self.assertEqual(self._lines("not in this run's batch"), [], self.err)
        self.assertEqual(self._lines("held this run"), [], self.err)
        self._assert_held_then_merged_together(merged=("A", "B", "D", "S1"))
        self.assertEqual(self.results["S1"], state.COMPLETE)

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
        end = self._lines("`Merges with` group issue_A, issue_B was not merged",
                          "issue_B is DISCONTINUED")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("cannot land together in this run", end[0])
        self.assertIn("Not merged: issue_A.", end[0])
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

    # -- a member whose record merge mode refuses holds the whole group --------------------

    def _assert_whole_group_held(self, why: str) -> None:
        # Nothing of the group was readied or merged, so it did not land in part; the run
        # went on (no STOP) and held B's dependent C, naming the group.
        for iid in "AB":
            self.assertEqual(self._readied_or_merged(iid), [], self.err)
        self.assertEqual(self.merged, {_url("D")}, self.err)
        self.assertNotIn("STOPPING", self.err)
        self.assertNotIn("landed only in part", self.err)
        held = self._lines("issue_B held", "`Merges with` issue_A", why)
        self.assertEqual(len(held), 1, self.err)
        self.assertIn("No member is readied or merged", held[0])
        self.assertNotIn("C", self.built, self.err)
        self.assertEqual(len(self._lines("flow: issue_C held", "issue_B", "`Merges with`")), 1,
                         self.err)
        end = self._lines("`Merges with` group issue_A, issue_B was not merged", why)
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("cannot land together in this run", end[0])
        self.assertEqual(self.holds, {"A": "group", "B": "group"})

    def test_a_member_without_a_recorded_pr_holds_the_whole_group(self):
        # B's publish failed (no publish.json): `_merge_one` would refuse it, so A must not
        # be merged first — at wave 1's boundary neither is readied.
        self.unpublished = {"B"}
        self._run(self._group_across_waves())
        self._assert_whole_group_held("issue_B has no recorded PR")

    def test_a_member_with_an_onto_branch_record_holds_the_whole_group(self):
        self.stacked = {"B"}
        self._run(self._group_across_waves())
        self._assert_whole_group_held("issue_B is an `Onto branch` commit")

    def test_a_malformed_expected_checks_refuses_the_group_before_any_member_is_readied(self):
        # A guard, not a red→green case: a setting that refuses every PR alike is left to
        # `_merge_one`, which refuses it before readying the group's FIRST member — so the
        # release stops with nothing of the group landed.
        self.cfg.expected_checks_error = "[driver].expected_checks must be a list of names"
        self._brief("A", merges_with="B")
        self._brief("B")
        self._brief("C", depends_on="B")             # wave 0 = [A, B] is not the final one
        self._run(["A", "B", "C"])

        for iid in "AB":
            self.assertEqual(self._readied_or_merged(iid), [], self.err)
        self.assertIn("STOPPING", self.err)
        self.assertNotIn("landed only in part", self.err)
        self.assertNotIn("C", self.built, self.err)

    # -- the final wave, and a member that fails to merge after another landed -------------

    def test_a_group_wholly_in_the_final_wave_is_named_for_the_human(self):
        # One wave, so no boundary merges anything: every PR stays a draft as always, and
        # the run says the group's PRs must be merged together.
        self._brief("A", merges_with="B")
        self._brief("B")
        self._run(["A", "B"])

        for iid in "AB":
            self.assertEqual(self._readied_or_merged(iid), [], self.err)
        end = self._lines("`Merges with` group issue_A, issue_B was not merged")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("every member is COMPLETE", end[0])
        self.assertIn("Merge its PRs together, back to back, in this order: issue_A, issue_B.",
                      end[0])
        self.assertEqual(self.holds, {})                # nothing was held: final-wave drafts
        self.assertEqual(self.rc, 0, self.err)

    def test_a_group_whose_last_member_completes_in_the_final_wave_stays_all_draft(self):
        self._brief("A", merges_with="B")
        self._brief("B", depends_on="D")
        self._brief("D")
        self._run(["A", "B", "D"])                    # waves [A, D], [B]: B is final

        for iid in "AB":
            self.assertEqual(self._readied_or_merged(iid), [], self.err)
        self.assertIn(_url("D"), self.merged)
        end = self._lines("`Merges with` group issue_A, issue_B was not merged")
        self.assertEqual(len(end), 1, self.err)
        self.assertIn("every member is COMPLETE", end[0])
        self.assertIn("in this order: issue_A, issue_B.", end[0])
        self.assertEqual(self.holds, {"A": "group"})   # A was held at wave 0's boundary
        self.assertEqual(self.rc, 3, self.err)

    def test_a_member_refused_after_another_merged_names_what_landed(self):
        self.merge_fails = {"B"}
        self._run(self._group_across_waves())

        self.assertIn(_url("A"), self.merged)
        self.assertNotIn(_url("B"), self.merged)
        self.assertIn("STOPPING", self.err)
        self.assertNotIn("C", self.built, self.err)
        part = self._lines("!!! merge:", "landed only in part", "issue_A merged",
                           "issue_B did not")
        self.assertEqual(len(part), 1, self.err)
        end = self._lines("flow: `Merges with` group issue_A, issue_B landed only in part",
                          "issue_A merged, issue_B not")
        self.assertEqual(len(end), 1, self.err)

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

    # -- the resume sweep holds a group it cannot drive whole -------------------------------

    def test_the_sweep_holds_a_refused_group_and_drives_the_rest(self):
        self._chained_pair()
        self._brief("U")
        self._sweep(do_publish=False)
        self.assertEqual(self.built, ["U"], self.err)
        self.assertEqual(self.results.get("U"), state.COMPLETE)
        for iid in "AB":
            held = self._lines(f"flow: issue_{iid} held this run", "`Merges with`")
            self.assertEqual(len(held), 1, self.err)

    def test_the_sweep_holds_the_partner_of_a_held_bundle_that_declared_the_group(self):
        # X declares `Merges with: A` (A's brief is silent) and is held for an unresolvable
        # dependency. A must not then be driven and merged alone: the relation is read off
        # X's brief too, and A is held with it.
        self._brief("A")
        self._brief("X", merges_with="A", depends_on="Z")   # Z: no such bundle
        self._brief("D")
        self._brief("U", depends_on="D")                    # a boundary after wave 0
        self._sweep(do_publish=True)

        self.assertEqual(sorted(self.built), ["D", "U"], self.err)
        self.assertEqual(self._readied_or_merged("A"), [], self.err)
        self.assertIn(_url("D"), self.merged)
        held = self._lines("flow: issue_A held this run", "`Merges with` group",
                           "issue_X is held too")
        self.assertEqual(len(held), 1, self.err)
        self.assertEqual(len(self._lines("flow: issue_X held this run", "Z")), 1, self.err)

    # -- a split child a later reschedule drops still holds its partner --------------------

    def test_a_split_child_dropped_later_still_holds_the_member_it_declared(self):
        # T splits in wave 0 into T1, which declares `Merges with: A` (one-sided) and
        # `Depends on: P`. P is DISCONTINUED in wave 1, where U splits too, so that
        # re-levelling holds T1 and drops it from the drive set again. A must stay held:
        # T1's declaration is still the run's, though T1 has left the drive set.
        self._brief("A")
        self._brief("Q")
        self._brief("T")
        self._brief("P", depends_on="Q")
        self._brief("U", depends_on="Q")
        self.splits = {"T": [("T1", {"merges_with": "A", "depends_on": "P"})],
                       "U": [("U1", {})]}
        self.discontinue = {"P"}
        self._run(["A", "P", "Q", "T", "U"])

        self.assertNotIn("T1", self.built, self.err)
        self.assertEqual(len(self._lines("issue_T1 — adopted earlier this run, now held")),
                         1, self.err)
        self.assertNotIn("T1", self.results)
        self.assertEqual(self._readied_or_merged("A"), [], self.err)
        self.assertNotIn(_url("A"), self.merged)
        self.assertIn(_url("Q"), self.merged)
        end = self._lines("`Merges with` group issue_A, issue_T1 was not merged",
                          "issue_T1 is PLANNED")
        self.assertEqual(len(end), 1, self.err)
        self.assertEqual(self.holds, {"A": "group"})


if __name__ == "__main__":
    unittest.main()
