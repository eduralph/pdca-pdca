"""A split child stops being indistinguishable from a fresh oversized brief (issue #448).

Three of the five weighted `sizing` features are fields the split itself installs into
every child: `conflicts_with` (sibling ordering entries — correct scheduling metadata),
`difficulty_high` (inherited from the parent) and `ext_deps` (the parent's tokens, copied).
3 + 3 + 3 = 9 against a cutoff of 7, whatever the child's actual scope, and the one
de-escalating term (`is_plan_pointer`) a split child never has. Nothing downstream knew a
split had happened, so every consumer read a child as a fresh oversized brief and pointed
at `pdca split` again — the ratchet these tests close.

What is asserted here is the WHOLE chain on the production path: `--accept` writes the
lineage, the estimator reads it and stops counting the split's own artifacts, the remedy
stops recommending a further split on structural score alone, and the convergence report
reaches the operator BEFORE the irreversible filing it is supposed to inform.

Modules are imported, never new symbols: on the C4 red leg the production hunks are
reverted while this file stays, and a `from pdca_harness.split import <new helper>` would
raise ImportError — which run-verify.sh classifies PDCA-UNVERIFIABLE, not red, so the test
would prove nothing.
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pdca_harness import cli, leaves, plan_policy, sizing, split, state
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"

# A child as a split actually materialises one: `Difficulty` and `External dependencies`
# inherited from the parent, `Conflicts with` naming its siblings. 3 + 3 + 3 = 9 today.
_INHERITED = ("- **Difficulty:** high\n"
              "- **External dependencies:** `protoc`\n")


def _child(slug: str, conflicts: str) -> str:
    return (f"- **Slug:** {slug}\n- **Defect / goal:** {slug}\n"
            + _INHERITED + f"- **Conflicts with:** {conflicts}\n")


def _proposal(*children: str) -> str:
    body = "<!-- pdca:split-proposal v1 -->\n# Split proposal\n\n"
    for i, child in enumerate(children, 1):
        body += (f"<!-- pdca:child child-{i} -->\n{child}\n"
                 f"<!-- pdca:end child-{i} -->\n\n")
    return body


class _Bundles(unittest.TestCase):
    """A real instance root, a real parent bundle, real `--accept` runs."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = Config(
            root=self.tmp, bundle_root=self.tmp / "results",
            process_dir=self.tmp / "process", templates_dir=TEMPLATES,
            default_branch="main", tracker_system="github", tracker_url="",
            issue_id_example="#1",
            builder=LeafConfig(mode="stub"), reviewer=LeafConfig(mode="stub"),
        )
        self.cfg.size_guard = "warn"
        self.parent = self.cfg.bundle("500")
        self.parent.mkdir(parents=True)
        (self.parent / "brief.md").write_text(
            "- **Slug:** parent\n" + _INHERITED, encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _propose(self, text: str, parent: Path | None = None) -> None:
        (parent or self.parent).joinpath(split.PROPOSAL).write_text(
            text, encoding="utf-8")

    def _accept_two(self) -> list[Path]:
        """The ordinary case: two children that conflict with each other."""
        self._propose(_proposal(_child("first", "child-2"),
                                _child("second", "child-1")))
        with redirect_stderr(io.StringIO()):
            return split.accept(self.parent, ["601", "602"], self.cfg)


class LineageIsWrittenAtMaterialisation(_Bundles):
    """Item 1. Before this, `materialise` wrote only the child body and "Child slice of
    #N" went solely into the tracker issue — so a child was locally indistinguishable from
    a fresh brief to every consumer that matters."""

    def test_each_child_records_its_parent_siblings_and_depth(self) -> None:
        created = self._accept_two()
        record = split.lineage(created[0])
        self.assertEqual(record["role"], "child")
        self.assertEqual(record["id"], "601")
        self.assertEqual(record["parent"], "500")
        self.assertEqual(record["siblings"], ["602"])
        self.assertEqual(record["depth"], 1)
        self.assertEqual(split.lineage(created[1])["siblings"], ["601"])

    def test_the_parent_records_the_inverse_edge(self) -> None:
        """One filename in BOTH directions, distinguished by `role`: the child edge is what
        stops the ratchet, the parent edge is what a consumer needs to find the slices a
        bundle became. Two files would drift."""
        self._accept_two()
        record = split.lineage(self.parent)
        self.assertEqual(record["role"], "parent")
        self.assertEqual(record["id"], "500")
        self.assertEqual(record["children"], ["601", "602"], "not the ORDERED id list")
        self.assertEqual(record["depth"], 0)

    def test_depth_counts_recursion_without_anyone_counting(self) -> None:
        """A split of a split child: the grandchildren record depth 2, and the middle
        bundle's parent record keeps the depth its own child record carried."""
        created = self._accept_two()
        child = created[0]
        self._propose(_proposal(_child("a", "child-2"), _child("b", "child-1")), child)
        with redirect_stderr(io.StringIO()):
            grandchildren = split.accept(child, ["701", "702"], self.cfg)
        self.assertEqual(split.lineage(grandchildren[0])["depth"], 2)
        self.assertEqual(split.lineage(child)["depth"], 1,
                         "the parent record lost the depth its child record carried")

    def test_the_record_is_staged_like_every_other_per_child_write(self) -> None:
        """`split.py:406-427` — anything written per child goes into `staging` and is moved
        with the rest, never in place: a failure half-way must not leave a bundle whose
        provenance disagrees with its content."""
        children = split.parse(_proposal(_child("first", "child-2"),
                                         _child("second", "child-1")))
        staging = self.parent / ".split-staging"
        staged = split.materialise(children, ["601", "602"], self.cfg, staging,
                                   parent=self.parent)
        self.assertTrue((staged[0] / split.LINEAGE).is_file())
        self.assertEqual(list(self.cfg.bundle_root.glob("issue_60*")), [],
                         "a child bundle was written outside staging")

    def test_lineage_is_provenance_not_attempt_output(self) -> None:
        """It must NOT join `DOWNSTREAM_OF_BRIEF`: a bundle does not stop being a split
        child because its brief was re-planned or a rejected attempt was archived."""
        self.assertNotIn(split.LINEAGE, state.DOWNSTREAM_OF_BRIEF)

    def test_an_unreadable_record_reads_as_absent_and_never_raises(self) -> None:
        """Nothing here may raise into a beat: an abstention loses one advisory, an
        exception loses the beat."""
        created = self._accept_two()
        for bad in ("not json at all", json.dumps({"version": 99, "role": "child"}),
                    json.dumps({"version": 1, "role": "not-a-role"}),
                    json.dumps(["not", "a", "dict"])):
            with self.subTest(record=bad[:24]):
                (created[0] / split.LINEAGE).write_text(bad, encoding="utf-8")
                self.assertIsNone(split.lineage(created[0]))
        (created[0] / split.LINEAGE).unlink()
        self.assertIsNone(split.lineage(created[0]))
        self.assertIsNone(split.lineage(self.tmp / "no-such-bundle"))


class TheEstimatorStopsScoringTheSplitsOwnArtifacts(_Bundles):
    """Item 2 — success criterion (a). Sibling `Conflicts with` entries are scheduling
    metadata this process installed, not churn evidence."""

    def test_a_child_scores_below_the_cutoff_where_it_scores_9_today(self) -> None:
        created = self._accept_two()
        child = created[0]
        est = sizing.estimate(child / "brief.md", self.cfg)

        # The control is the SAME brief text with no lineage beside it — every bundle
        # written before #448, and what this child was until the record existed.
        plain = self.tmp / "plain"
        plain.mkdir()
        shutil.copyfile(child / "brief.md", plain / "brief.md")
        without = sizing.estimate(plain / "brief.md", self.cfg)
        self.assertGreaterEqual(without.score, sizing.DEFAULT_OVERSIZED)
        self.assertEqual(without.band, sizing.OVERSIZED)

        self.assertLess(est.score, sizing.DEFAULT_OVERSIZED,
                        f"the split's own artifacts are still scored: {est.reasons}")
        self.assertNotEqual(est.band, sizing.OVERSIZED)
        self.assertTrue(any("sibling conflict" in r for r in est.reasons),
                        f"the exclusion is not visible in the reasons: {est.reasons}")

    def test_an_organic_conflict_still_counts_at_full_weight(self) -> None:
        """The strongest measured churn signal on organic bundles — weakening it beyond
        the split's own siblings would trade a real signal for a special case."""
        created = self._accept_two()
        child = created[0]
        text = (child / "brief.md").read_text(encoding="utf-8")
        (child / "brief.md").write_text(
            text.replace("- **Conflicts with:** 602", "- **Conflicts with:** 602, 903"),
            encoding="utf-8")
        est = sizing.estimate(child / "brief.md", self.cfg)
        self.assertIn("1 conflict(s) declared", est.reasons)
        self.assertEqual(est.band, sizing.OVERSIZED)

    def test_the_weight_is_registered_and_ships_at_zero(self) -> None:
        """Registered so `[driver.sizing]` retunes it without patching the engine — the
        same shape as every other weight; 0 because no corpus has measured it."""
        self.assertEqual(sizing.DEFAULT_WEIGHTS["split_child"], 0)
        created = self._accept_two()
        cfg = SimpleNamespace(sizing={"split_child": -2})
        self.assertEqual(sizing.estimate(created[0] / "brief.md", cfg).score,
                         sizing.estimate(created[0] / "brief.md", self.cfg).score - 2)

    def test_a_bundle_with_no_lineage_is_scored_exactly_as_today(self) -> None:
        p = self.tmp / "organic"
        p.mkdir()
        (p / "brief.md").write_text("- **Slug:** s\n" + _INHERITED
                                    + "- **Conflicts with:** 12, 13\n", encoding="utf-8")
        est = sizing.estimate(p / "brief.md", self.cfg)
        self.assertEqual(est.score, 9)
        self.assertEqual(est.band, sizing.OVERSIZED)


class TheRemedyIsDepthAndEvidenceAware(_Bundles):
    """Item 3 — success criterion (b). Structural score alone cannot see decomposability;
    the sizer leaf can, and it is the only evidence that justifies splitting a child."""

    def _oversized_child(self) -> Path:
        """A split child that is oversized even AFTER the sibling exclusion: high
        difficulty + external dependencies + a brief over the size cutoff = 9."""
        self._propose(_proposal(
            _child("first", "child-2") + "- **Scope:** " + ("pad " * 4000) + "\n",
            _child("second", "child-1")))
        with redirect_stderr(io.StringIO()):
            created = split.accept(self.parent, ["601", "602"], self.cfg)
        est = sizing.estimate(created[0] / "brief.md", self.cfg)
        self.assertEqual(est.band, sizing.OVERSIZED, "the fixture is not oversized")
        return created[0]

    def test_a_split_child_is_not_told_to_split_again_on_structure_alone(self) -> None:
        child = self._oversized_child()
        with redirect_stderr(io.StringIO()):
            reasons = plan_policy.size_reasons(child, self.cfg, before_do=True)
        self.assertTrue(reasons, "the advisory stopped firing altogether")
        detail = reasons[0].detail
        self.assertIn("scores large for a split child", detail)
        self.assertIn("driven by inherited/sibling fields", detail)
        self.assertIn("depth 1", detail)
        self.assertNotIn("consider `pdca split` first", detail)

    def test_the_sizers_verdict_still_earns_the_split_remedy(self) -> None:
        """≥ 2 independently shippable outcomes is the one signal that can see
        decomposability — a child that really is two slices must still be splittable."""
        child = self._oversized_child()
        with mock.patch("pdca_harness.leaves.run_sizer",
                        return_value={"band": "oversized",
                                      "independent_outcomes": ["a", "b"]}), \
                redirect_stderr(io.StringIO()):
            reasons = plan_policy.size_reasons(child, self.cfg, before_do=True)
        self.assertIn("consider `pdca split` first", reasons[0].detail)

    def test_a_bundle_without_lineage_keeps_todays_remedy(self) -> None:
        child = self._oversized_child()
        (child / split.LINEAGE).unlink()
        with redirect_stderr(io.StringIO()):
            reasons = plan_policy.size_reasons(child, self.cfg, before_do=True)
        self.assertIn("consider `pdca split` first", reasons[0].detail)

    def test_the_iterate_plan_wording_is_unchanged_after_do(self) -> None:
        child = self._oversized_child()
        with redirect_stderr(io.StringIO()):
            reasons = plan_policy.size_reasons(child, self.cfg, before_do=False)
        self.assertIn("iterate-plan", reasons[0].detail)

    def test_the_planner_and_splitter_prompts_carry_the_same_context(self) -> None:
        """The loop is not only numeric: a planner or splitter that cannot see where the
        inherited fields came from proposes the remedy that produced them."""
        child = self._oversized_child()
        plan_prompt = leaves._plan_prompt(self.cfg, None, child)
        split_prompt = leaves._split_prompt(child, self.cfg)
        for name, prompt in (("planner", plan_prompt), ("splitter", split_prompt)):
            with self.subTest(prompt=name):
                self.assertIn("split child", prompt)
                self.assertIn("child 1 of a split of #500, depth 1", prompt)
        parent_plan = leaves._plan_prompt(self.cfg, None, self.parent)
        self.assertNotIn("split child", parent_plan,
                         "a bundle with no lineage had its prompt changed")


class ConvergenceIsCheckedBeforeIrreversibleFiling(_Bundles):
    """Item 4 — success criterion (c). `preflight` runs before `file_children`, which is
    the only point at which the answer can still change a decision: after it the tracker
    issues exist and cannot be withdrawn."""

    def test_preflight_reports_each_staged_childs_band_against_the_parent(self) -> None:
        children = split.parse(_proposal(_child("first", "child-2"),
                                         _child("second", "child-1")))
        err = io.StringIO()
        self._propose(_proposal(_child("first", "child-2"), _child("second", "child-1")))
        with redirect_stderr(err):
            split.preflight(self.parent, children, self.cfg)
        report = err.getvalue()
        self.assertIn("convergence check", report)
        for label in ("child-1", "child-2"):
            self.assertIn(label, report)
        self.assertIn(self.parent.name, report)

    def test_the_staged_estimate_treats_ordering_refs_as_siblings(self) -> None:
        """Inside a proposal every ordering ref is a sibling LABEL by construction, so the
        staged estimate must exclude them exactly as the materialised child will —
        otherwise it reports a band no child will ever have."""
        children = split.parse(_proposal(_child("first", "child-2"),
                                         _child("second", "child-1")))
        report = "\n".join(split.convergence_report(self.parent, children, self.cfg))
        self.assertIn("sibling conflict", report)
        self.assertNotIn("2 conflict(s) declared", report)

    def test_the_report_reaches_the_operator_BEFORE_the_issues_are_filed(self) -> None:
        """The whole point of running it in `preflight`: a convergence verdict that
        arrived after filing could not inform the decision it exists to inform."""
        self._propose(_proposal(_child("first", "child-2"), _child("second", "child-1")))
        err = io.StringIO()
        seen: list[str] = []

        def filer(parent, children, cfg, **kw):
            seen.append(err.getvalue())
            return ["601", "602"]

        with mock.patch("pdca_harness.split.file_children", filer), \
                redirect_stderr(err), redirect_stdout(io.StringIO()):
            rc = cli._split(self.cfg, SimpleNamespace(issue_id="500", accept=True, ids=""))
        self.assertEqual(rc, 0)
        self.assertIn("convergence check", seen[0],
                      "the children were filed before the convergence report was printed")

    def test_the_report_never_blocks_an_acceptance(self) -> None:
        """Advisory, matching the size guard's warn-only stance — and an estimate that
        fails must not be the reason a valid split cannot be accepted."""
        children = split.parse(_proposal(_child("first", "child-2"),
                                         _child("second", "child-1")))
        self._propose(_proposal(_child("first", "child-2"), _child("second", "child-1")))
        with mock.patch("pdca_harness.sizing.estimate", side_effect=RuntimeError("boom")), \
                redirect_stderr(io.StringIO()):
            split.preflight(self.parent, children, self.cfg)   # must not raise
        with redirect_stderr(io.StringIO()):
            created = split.accept(self.parent, ["601", "602"], self.cfg)
        self.assertEqual(len(created), 2)


if __name__ == "__main__":
    unittest.main()
