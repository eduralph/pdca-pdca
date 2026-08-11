"""An honest split-child advisory, with an escape hatch that actually works (#458).

`plan_policy.size_reasons` used to answer EVERY oversized split child with the same
`consider `pdca split` first` its parent got — the exact readout a split inflates. The
fix keys the "driven by inherited/sibling fields" line on the one thing that is actually
evidence of it: a `Conflicts with:` id the bundle DECLARES that also names one of its own
split SIBLINGS (`split-lineage.json`'s `siblings` edge). Two failures a first attempt at
this fix produced, both reproduced here so they cannot recur silently:

1. Keying on mere lineage PRESENCE is false for a split child whose conflicts are all
   organic (declared against bundles outside the split) — every split child carries a
   lineage record forever, so that predicate fires on children that should still be told
   to split.
2. The escape hatch has to work on the sizer this project actually SHIPS: `mode = "stub"`,
   `leaves._stub_sizer` returning `{"band": "ok"}` unconditionally. A hatch tested only
   through a mocked sizer proves nothing about the offline default every fresh instance
   runs.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pdca_harness import leaves, plan_policy, sizing, split
from pdca_harness.config import Config, LeafConfig

# Difficulty=high (3) + Conflicts with (3, regardless of how many ids) + an oversized
# brief (3, the padded Scope) = 9 >= the oversized cutoff of 7 — the same shape
# test_size_guard.py's _OVERSIZED fixture uses. patch_band also lands on `oversized`
# (difficulty=high AND over-size both fire), so `splittable` is True via churn_band
# regardless — no dependence on the patch_band branch this bundle doesn't need.
_SIBLING = "602"
_SIBLINGS = ["602", "603"]
_PARENT = "500"
_DEPTH = 1


def _child_brief(conflicts: str) -> str:
    return (
        "- **Slug:** split-child\n"
        "- **Difficulty:** high\n"
        f"- **Conflicts with:** {conflicts}\n"
        "- **Scope:** " + ("pad " * 4000) + "\n"
    )


def _cfg(root: Path, guard: str = "warn") -> Config:
    cfg = Config(
        root=root, bundle_root=root / "results", process_dir=root / "process",
        templates_dir=root / "templates", default_branch="main",
        tracker_system="github", tracker_url="", issue_id_example="#1",
        builder=LeafConfig(mode="stub"), reviewer=LeafConfig(mode="stub"),
    )
    cfg.size_guard = guard
    # sizer defaults to LeafConfig(mode="stub") — the shipped offline default, left
    # UNTOUCHED here so `leaves.run_sizer` really runs `leaves._stub_sizer` (#458 iii):
    # the previous attempt's hatch test mocked this away and passed on the red leg too.
    return cfg


class SplitChildAdvisory(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.d = self.tmp / "results" / "issue_601"
        self.d.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _lineage(self, **over) -> None:
        record = {"version": split.LINEAGE_VERSION, "id": "601", "parent": _PARENT,
                  "siblings": list(_SIBLINGS), "depth": _DEPTH, **over}
        (self.d / split.LINEAGE).write_text(json.dumps(record, indent=2, sort_keys=True)
                                            + "\n", encoding="utf-8")

    # -- (i) the load-bearing red: a sibling-conflict-carried score names the provenance --

    def test_i_sibling_conflict_gets_the_honest_provenance_line(self) -> None:
        """Child 601's own declared conflict names SIBLING 602 — the score is carried by
        what it inherited from the split, and the message must say so, not recommend
        splitting a bundle whose entire evidence is that it was already split."""
        (self.d / "brief.md").write_text(_child_brief(_SIBLING), encoding="utf-8")
        self._lineage()
        cfg = _cfg(self.tmp, "warn")

        reasons = plan_policy.size_reasons(self.d, cfg, before_do=True)

        self.assertEqual([r.code for r in reasons], ["oversized"])
        detail = reasons[0].detail
        self.assertIn(
            "scores large for a split child (child 601 of a split of #500, depth 1) — "
            "driven by inherited/sibling fields; prefer building over re-splitting",
            detail)
        self.assertNotIn("consider `pdca split` first", detail)
        # The exact failure mode reproduced: the honest line must NOT sit beside an
        # uncounted "N conflict(s) declared" with no clarifying clause.
        self.assertIn("1 sibling conflict(s) not counted", detail)

    # -- (ii) zero sibling conflicts: the ordinary remedy, unchanged --------------------

    def test_ii_organic_only_conflicts_get_the_ordinary_remedy(self) -> None:
        """Four ORGANIC conflicts (none of them a sibling) must still recommend a split —
        this child's oversized score is not inherited from anything. The rejected attempt
        keyed on lineage presence alone and printed the inherited-fields line here too,
        contradicting its own '4 conflict(s) declared' evidence."""
        (self.d / "brief.md").write_text(_child_brief("811, 812, 813, 814"),
                                         encoding="utf-8")
        self._lineage()
        cfg = _cfg(self.tmp, "warn")

        reasons = plan_policy.size_reasons(self.d, cfg, before_do=True)

        self.assertEqual([r.code for r in reasons], ["oversized"])
        detail = reasons[0].detail
        self.assertIn("consider `pdca split` first", detail)
        self.assertIn("4 conflict(s) declared", detail)
        self.assertNotIn("driven by inherited/sibling fields", detail,
                         "an organic-only split child was told it scored large because "
                         "of inherited fields")
        self.assertNotIn("scores large for a split child", detail)

    # -- (iii) same as (ii), but proving it against the REAL shipped stub sizer ---------

    def test_iii_the_ordinary_remedy_survives_the_real_stub_sizer(self) -> None:
        """Not a mock: `plan_policy.evaluate` drives `leaves.run_sizer` for real, which —
        with the shipped `[leaves.sizer] mode = "stub"` default — writes `sizing.json`
        via `leaves._stub_sizer` and returns `{"band": "ok", ...}` unconditionally. The
        suppression in test (ii) must not depend on the operator having bought a
        `mode = "command"` sizer, and this proves the real offline path was exercised —
        not merely a mocked-out stand-in that could pass on the red leg too."""
        (self.d / "brief.md").write_text(_child_brief("811, 812, 813, 814"),
                                         encoding="utf-8")
        self._lineage()
        cfg = _cfg(self.tmp, "warn")
        self.assertEqual(cfg.sizer.mode, "stub", "test no longer exercises the shipped "
                         "default — the whole point of (iii)")

        reasons = plan_policy.evaluate(self.d, cfg, before_do=True)

        # The real `_stub_sizer` ran and left its artifact — not a mock.
        verdict = json.loads((self.d / "sizing.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict.get("band"), "ok")
        self.assertTrue(verdict.get("stub"), "sizing.json was not written by the real "
                        "_stub_sizer — the hatch was proven against a mock")

        self.assertEqual([r.code for r in reasons], ["oversized"])
        detail = reasons[0].detail
        self.assertIn("consider `pdca split` first", detail)
        self.assertNotIn("driven by inherited/sibling fields", detail)

    # -- (iv) before_do=False keeps the iterate-plan wording, provenance or not ---------

    def test_iv_after_do_still_routes_through_iterate_plan(self) -> None:
        """A bundle that already has a patch is told to re-plan, not to `pdca split` —
        and that holds even when the score IS sibling-carried: splitting only ever
        happens in Plan, so the provenance fork must not leak into this branch."""
        (self.d / "brief.md").write_text(_child_brief(_SIBLING), encoding="utf-8")
        self._lineage()
        cfg = _cfg(self.tmp, "warn")

        reasons = plan_policy.size_reasons(self.d, cfg, before_do=False)

        detail = reasons[0].detail
        self.assertIn("iterate-plan", detail)
        self.assertNotIn("pdca split` first", detail)
        self.assertNotIn("driven by inherited/sibling fields", detail)

    # -- (vi) no lineage at all: byte-identical to today ---------------------------------

    def test_vi_no_lineage_is_byte_identical_to_today(self) -> None:
        """A bundle that was never split must get exactly the pre-existing message —
        the sibling-conflict check must never fire without a lineage record to check
        against, even when the declared conflict happens to equal what would be a
        sibling id in some OTHER split."""
        (self.d / "brief.md").write_text(_child_brief(_SIBLING), encoding="utf-8")
        self.assertIsNone(split.read_lineage(self.d))
        cfg = _cfg(self.tmp, "warn")

        reasons = plan_policy.size_reasons(self.d, cfg, before_do=True)

        est = sizing.combine(sizing.estimate(self.d / "brief.md", cfg),
                             leaves.run_sizer(self.d, cfg), cfg)
        expected = f"oversized — consider `pdca split` first ({'; '.join(est.reasons)})"
        self.assertEqual(reasons[0].detail, expected)


if __name__ == "__main__":
    unittest.main()
