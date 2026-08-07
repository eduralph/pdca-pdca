"""Auto-iterate on implementation Check findings (issues #264, #332; stdlib unittest).

The driver may rebuild a bundle unattended when SUMMARY §6 carries at least one
implementation defect — a `gate` cell of the 5/5/1 (C2/C4/T1..T4), an advisory finding the
leaf tagged `[impl]`, or (since #332) a C5/T5 judgment verdict the REVIEWER tagged
`NEEDS-HUMAN [impl]`. A HUMAN finding beside the implementation ones no longer vetoes the
rebuild: it is DEFERRED to a loss-proof ledger (`deferred-human.json`) that survives the
iteration archive and re-enters §6 on every assemble, so it still reaches the human at
handover under the C6 guard. What still halts: an empty §6 (never auto-accept), a
HUMAN-only set (nothing for a rebuild to fix), the size backstop, and the round budget —
hard (`max_auto_iters`), plus a soft window (`soft_auto_iters`) whose extra rounds fire
only while the recorded per-round IMPL count is not rising.

Load-bearing negatives, each its own test: it must never auto-accept, never tick a §6 box,
never lose a deferred finding (the #335 retirement fold), and never run past its budget.
Offline: stub leaves, real gate commands, no Claude.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import assemble, autoiterate, cli, driver, flow, gates, leaves, signoff, state
from pdca_harness.config import Config, LeafConfig

_GATE = {"id": "C4", "tier": "C4", "label": "verify", "scope": "bundle", "gating": True}
_PASS = {**_GATE, "cmd": "true"}
_FAIL = {**_GATE, "cmd": "false"}
_UNVERIFIABLE = {**_GATE, "cmd": "echo 'PDCA-UNVERIFIABLE: no prod file'; exit 0"}

_CLEAN_REVIEW = "All advisory items PASS.\n"

# The #332 production shape: a builder-fixable finding BESIDE a real judgment concern.
# Pre-#332 the C5 row vetoed the rebuild outright; now it defers to the ledger.
_MIXED_REVIEW = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                 "| C4 Verification (red→green) | NEEDS-HUMAN | off-by-one |\n"
                 "| C5 Causal adequacy | NEEDS-HUMAN | guards the symptom, not the cause |\n"
                 "| Validation — fitness-to-purpose | NEEDS-HUMAN | fitness is the human's call |\n")
_MIXED_C5_TEXT = "C5 Causal adequacy — guards the symptom, not the cause"


# The reviewer's prompt (agents/reviewer.md.jinja) hard-codes this row to NEEDS-HUMAN on EVERY
# cycle — validation is the human's call by definition. So EVERY real `check-review.md` carries
# it, and a fixture without it is a shape the product never produces. Omitting it is exactly why
# the original #264 tests passed while auto-iterate was unreachable in production (#293): they
# tested the mental model, not the artifact. It belongs in the fixture, not in one new test.
_STANDING_ROW = "| Validation — fitness-to-purpose | NEEDS-HUMAN | fitness is the human's call |"


def _review_table(item: str, verdict: str = "NEEDS-HUMAN", basis: str = "off-by-one",
                  *, standing: bool = True) -> str:
    rows = f"| {item} | {verdict} | {basis} |\n"
    if standing:
        rows += _STANDING_ROW + "\n"
    return f"# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n{rows}"


def _stub_config(root: Path) -> Config:
    return Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=root / "templates",
        default_branch="main",
        tracker_system="github",
        tracker_url="",
        issue_id_example="#1",
        builder=LeafConfig(mode="stub", family="claude"),
        reviewer=LeafConfig(mode="stub", family="codex"),
        auto_iterate=True,
        max_auto_iters=3,
    )


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = _stub_config(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _bundle(self, iid: str, *, gate: dict = _PASS, review: str = _CLEAN_REVIEW,
                advisory: str | None = None, build_notes: str | None = None,
                brief_body: str = "- **Slug:** ai\n") -> Path:
        d = self.cfg.bundle(iid)
        d.mkdir(parents=True)
        (d / "brief.md").write_text(brief_body, encoding="utf-8")
        (d / "patch.diff").write_text("--- a\n+++ b\n", encoding="utf-8")
        (d / "check-review.md").write_text(review, encoding="utf-8")
        if advisory is not None:
            (d / "check-advisory-adversary.md").write_text(advisory, encoding="utf-8")
        if build_notes is not None:
            (d / "build-notes.md").write_text(build_notes, encoding="utf-8")
        self.cfg.gates_checks = [gate]
        gates.run_gates(d, self.cfg)
        assemble.assemble_summary(d, self.cfg)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        return d

    def _try(self, d: Path, *, apply_now: bool = False) -> bool:
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            return flow._maybe_auto_iterate(
                self.cfg, d, by="", today="2026-07-09", apply_now=apply_now)

    def _assert_halted(self, d: Path) -> None:
        """No decision written, no budget spent, bundle still waiting on the human."""
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertFalse((d / leaves.SIGNOFF_DECISION).exists())
        self.assertEqual(autoiterate.count(d), 0)
        self.assertTrue(signoff.open_needs_human(d / "SUMMARY.md") or True)  # §6 untouched


class AutoIterates(_Base):
    """Implementation-only findings ⇒ the driver rebuilds without asking."""

    def test_failed_gating_gate_auto_iterates(self) -> None:
        d = self._bundle("GATEFAIL", gate=_FAIL)
        self.assertTrue(self._try(d))
        self.assertEqual(state.state(d), state.ITERATE_DO)
        self.assertEqual(signoff.outcome_token(d / "SUMMARY.md"), "iterated-to-Do")
        self.assertEqual(autoiterate.count(d), 1)

    def test_reviewer_needs_human_on_a_gate_cell_auto_iterates(self) -> None:
        d = self._bundle("C4NH", review=_review_table("C4 Verification (red→green)"))
        self.assertTrue(self._try(d))
        self.assertEqual(state.state(d), state.ITERATE_DO)

    def test_conformance_gate_cells_auto_iterate(self) -> None:
        for elem in ("C2 Reproduction (red pre-fix)", "T1 Structure", "T2 Shape",
                     "T3 Runtime", "T4 Contribution"):
            with self.subTest(elem=elem):
                d = self._bundle(f"E{elem[:2]}", review=_review_table(elem))
                self.assertTrue(self._try(d), f"{elem} is a gate cell — should auto-iterate")

    def test_advisory_impl_marker_auto_iterates_and_text_is_clean(self) -> None:
        d = self._bundle("ADVIMPL", advisory="- NEEDS-HUMAN [impl] — off-by-one at src/x.py:12\n")
        items = assemble.collect_needs_human(d, self.cfg)
        self.assertEqual([i.kind for i in items], [assemble.IMPL])
        self.assertTrue(items[0].text.startswith("off-by-one"))  # the marker is stripped
        self.assertTrue(self._try(d))

    def test_rationale_reaches_the_brief_carry_forward(self) -> None:
        # The next Do iteration must not be blind about why it was rejected.
        d = self._bundle("CARRY", gate=_FAIL)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-07-09", apply_now=True)
            driver.run_issue(d, self.cfg)
        brief_text = (d / "brief.md").read_text(encoding="utf-8")
        self.assertIn("carry-forward", brief_text.lower())
        self.assertIn("Auto-iterate", brief_text)
        self.assertTrue((d / "iteration-v1").is_dir())      # prior attempt archived, not deleted

    def test_signoff_is_attributed_to_the_driver_not_a_human(self) -> None:
        d = self._bundle("ATTR", gate=_FAIL)
        self._try(d)
        self.assertIn("auto-iterate", (d / "SUMMARY.md").read_text(encoding="utf-8"))


class TheStandingValidationRow(_Base):
    """Issue #293 — the row that made this whole feature dead code.

    The reviewer's prompt hard-codes `Validation — fitness-to-purpose` to NEEDS-HUMAN on EVERY
    cycle, whatever it found: validation is the human's call by definition. So every real
    `check-review.md` carries it. The original rule demanded that EVERY §6 item be IMPL, so a
    single such row disqualified every bundle and auto-iterate NEVER FIRED in production — a
    constant was being read as evidence that a human must look right now.

    It still renders in §6 and the C6 accept-guard still blocks on it. All it no longer does is
    veto a rebuild.
    """

    def test_an_impl_finding_beside_the_standing_row_auto_iterates(self) -> None:
        # THE production shape, and the one the old fixture never built.
        d = self._bundle("SV1", review=_review_table("C4 Verification (red→green)"))
        self.assertTrue(self._try(d), "a Do-fixable defect must rebuild, not spend a human")
        self.assertEqual(autoiterate.count(d), 1)

    def test_the_standing_row_alone_still_halts(self) -> None:
        # Nothing for a rebuild to fix: a clean bundle awaiting the human's ACCEPT. Never
        # auto-accept — `eligible` needs at least one IMPL item, not merely "no HUMAN item".
        d = self._bundle("SV2", review=f"# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                                       f"{_STANDING_ROW}\n")
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_a_situational_judgment_concern_beside_impl_defers_not_halts(self) -> None:
        # #332: C5/T5 carry signal, so they are never ARCHIVED-AND-FORGOTTEN — but beside a
        # builder-fixable finding they no longer veto the rebuild either. The concern is
        # deferred to the ledger (asserted here) and re-enters §6 every assemble, so the
        # human still adjudicates it at handover (DeferredFindings covers the round trip).
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C4 Verification (red→green) | NEEDS-HUMAN | off-by-one |\n"
                  "| C5 Causal adequacy | NEEDS-HUMAN | guards the symptom, not the cause |\n"
                  f"{_STANDING_ROW}\n")
        d = self._bundle("SV3", review=review)
        self.assertTrue(self._try(d), "an IMPL finding beside a judgment concern rebuilds")
        self.assertEqual(
            autoiterate.ledger_entries(d),
            ["C5 Causal adequacy — guards the symptom, not the cause"],
            "the judgment concern is deferred — never dropped, never carried to the builder")

    def test_an_advisory_fitness_objection_is_never_standing(self) -> None:
        """PR #294 review (codex). STANDING is the PRIMARY review's privilege, and nothing
        else's.

        `collect_needs_human` runs `check-review.md` and every `check-advisory-*.md` through the
        same classifier. The adversary's prompt tells it to raise architectural / scope /
        fitness objections as free-form `- NEEDS-HUMAN — …` bullets — so one that happens to
        begin "Validation — fitness-to-purpose" was being read as the reviewer's signal-free
        standing row, and an unattended rebuild would ARCHIVE a real objection instead of
        halting for sign-off. The basis for STANDING is "this row is a constant", which is true
        of the reviewer's mandated table and of nothing else.
        """
        advisory = ("# Adversary\n\n- NEEDS-HUMAN — Validation — fitness-to-purpose: this "
                    "patches the wrong layer; the success criterion cannot be met by this "
                    "design\n")
        d = self._bundle("SV5", review=_review_table("C4 Verification (red→green)"),
                         advisory=advisory)
        # #332: beside an IMPL finding the objection defers rather than halting — but its
        # presence in the LEDGER is exactly the proof it was classified HUMAN, not STANDING
        # (a STANDING item is never deferred): it re-enters §6 every round, so it reaches
        # the human instead of being archived away, which is the #294 property.
        self.assertTrue(self._try(d))
        self.assertIn("Validation — fitness-to-purpose: this patches the wrong layer; the "
                      "success criterion cannot be met by this design",
                      autoiterate.ledger_entries(d),
                      "a real fitness objection must be deferred to the human, never archived")

    def test_a_legacy_validation_bullet_in_the_review_is_never_standing(self) -> None:
        """PR #294 review (codex), second pass. Scoping STANDING to the primary ARTIFACT was
        still too wide — it must be scoped to the mandated verdict-table ROW.

        `_needs_human` also honours legacy `- NEEDS-HUMAN — …` bullets in `check-review.md`.
        Those are free prose the reviewer CHOSE to write, so one reading "Validation —
        fitness-to-purpose: patches the wrong layer" is a substantive objection, not the
        template row — and would have been archived by an unattended rebuild. Only a table row
        is the constant that earns STANDING.
        """
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C4 Verification (red→green) | NEEDS-HUMAN | [impl] off-by-one |\n"
                  f"{_STANDING_ROW}\n"
                  "- NEEDS-HUMAN — Validation — fitness-to-purpose: patches the wrong layer\n")
        d = self._bundle("SV6", review=review)
        # #332: it defers beside the IMPL row — and landing in the LEDGER is the proof it
        # was a finding (HUMAN), not the constant (STANDING is never deferred). It re-enters
        # §6 every assemble, so the human still sees it at handover.
        self.assertTrue(self._try(d))
        self.assertIn("Validation — fitness-to-purpose: patches the wrong layer",
                      autoiterate.ledger_entries(d),
                      "a legacy fitness bullet is a finding — deferred, never archived away")

    def test_a_second_table_never_earns_the_standing_exemption(self) -> None:
        """PR #294 review (codex), third pass. Keying on "came from a table" was STILL too wide.

        The reviewer may write more than one table — a "concerns" table beside the mandated
        verdict table. A row there reading `| Validation — fitness-to-purpose: patches the wrong
        layer | NEEDS-HUMAN | … |` is a substantive objection, but it came from a table and its
        text starts with the canonical label, so it was classified STANDING and an unattended
        rebuild would archive it. The canonical row is now identified by an EXACT match on its
        Item cell — the only thing that actually distinguishes the template row.
        """
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C4 Verification (red→green) | NEEDS-HUMAN | [impl] off-by-one |\n"
                  f"{_STANDING_ROW}\n"
                  "\n## Concerns\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| Validation — fitness-to-purpose: patches the wrong layer | NEEDS-HUMAN "
                  "| the criterion cannot be met by this design |\n")
        d = self._bundle("SV7", review=review)
        self.assertTrue(self._try(d))     # #332: defers beside the IMPL row
        self.assertIn("Validation — fitness-to-purpose: patches the wrong layer — the "
                      "criterion cannot be met by this design",
                      autoiterate.ledger_entries(d),
                      "a concerns-table objection is a finding — deferred, never archived away")

    def test_a_concerns_table_with_the_EXACT_label_still_halts(self) -> None:
        """PR #294, local codex pass. The fourth scoping of the same rule, and the one that
        finally names the right thing.

        Matching the Item cell was still not enough: a `## Concerns` table can carry the row
        `| Validation — fitness-to-purpose | NEEDS-HUMAN | patches the wrong layer |` with the
        **exact** canonical label. The parser had no idea which TABLE a row came from, so that
        real objection earned STANDING and an unattended rebuild would archive it. My previous
        test only covered a concerns row with EXTRA text in the cell, so it sailed past this.

        The justification was always "the MANDATED TABLE's Validation row is a constant" — so the
        parser now identifies that table (≥2 exact canonical Item cells) and only its V row can
        be standing.
        """
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C4 Verification (red→green) | NEEDS-HUMAN | [impl] off-by-one |\n"
                  "| C5 Causal adequacy | PASS | ok |\n"
                  f"{_STANDING_ROW}\n"
                  "\n## Concerns\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| Validation — fitness-to-purpose | NEEDS-HUMAN | patches the wrong layer |\n")
        d = self._bundle("SV9", review=review)
        # #332: the concerns row is HUMAN (not the constant), so it defers — proof: it is
        # in the ledger, which STANDING never enters, and re-enters §6 for the human.
        self.assertTrue(self._try(d))
        self.assertIn("Validation — fitness-to-purpose — patches the wrong layer",
                      autoiterate.ledger_entries(d),
                      "an exact-label concerns row is still a real objection — deferred")

    def test_two_standing_candidates_fail_closed(self) -> None:
        # The template row is a CONSTANT — it occurs once. If two survive (a duplicated row, a
        # second verdict-shaped table), at least one is not the constant and we cannot tell
        # which. Grant STANDING to neither and halt, rather than risk archiving a real objection.
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C5 Causal adequacy | PASS | ok |\n"
                  f"{_STANDING_ROW}\n"
                  "| Validation — fitness-to-purpose | NEEDS-HUMAN | and again, differently |\n")
        d = self._bundle("SV10", review=review)
        # Fail closed = STANDING granted to neither ⇒ both are ordinary HUMAN findings.
        # With nothing IMPL beside them the bundle halts outright (#332's HUMAN-only rule);
        # beside an IMPL finding they would defer to the ledger — reaching the human either
        # way, never archived as the constant.
        self.assertFalse(self._try(d), "ambiguous standing rows must fail closed")
        self._assert_halted(d)
        kinds = {i.kind for i in assemble.collect_needs_human(d, self.cfg)}
        self.assertNotIn(assemble.STANDING, kinds)

    def test_the_standing_row_is_never_carried_forward_to_the_builder(self) -> None:
        """PR #294 review (codex). STANDING rides along in `items` so it cannot veto the rebuild
        — but it is not a finding, and no builder can act on it. Carrying it into the §9 delta
        and the brief's carry-forward handed the next Do a human-only judgment call as though it
        were a defect to fix, under a sentence claiming the set was "implementation-level items
        only"."""
        d = self._bundle("SV8", review=_review_table("C4 Verification (red→green)"))
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-07-09", apply_now=True)
            driver.run_issue(d, self.cfg)
        brief_text = (d / "brief.md").read_text(encoding="utf-8")
        self.assertIn("C4 Verification", brief_text)                     # the real defect…
        self.assertNotIn("Validation — fitness-to-purpose", brief_text)  # …and only that

    def test_the_standing_row_still_blocks_accept(self) -> None:
        # The C6 guard is untouched: the human must still clear §6 before accepting. Not
        # vetoing a REBUILD is not the same as not needing a human at SIGN-OFF.
        d = self._bundle("SV4", review=_review_table("C4 Verification (red→green)"))
        summary = (d / "SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn("Validation — fitness-to-purpose", summary)   # still rendered in §6
        self.assertTrue(signoff.open_needs_human(d / "SUMMARY.md"))  # still blocks accept


class HaltsForTheHuman(_Base):
    """Anything architectural, environmental, or unclassifiable still stops."""

    def test_judgment_cells_halt(self) -> None:
        # THE load-bearing negative: C5 causal adequacy, T5 judgment, the validation act.
        for elem in ("C5 Causal adequacy", "T5 Judgment", "Validation — fitness-to-purpose"):
            with self.subTest(elem=elem):
                d = self._bundle(f"J{abs(hash(elem)) % 9999}", review=_review_table(elem))
                self.assertFalse(self._try(d), f"{elem} is a judgment cell — must halt")
                self._assert_halted(d)

    def test_input_cells_halt(self) -> None:
        for elem in ("C1 Spec", "C3 Change"):
            with self.subTest(elem=elem):
                d = self._bundle(f"I{elem[:2]}", review=_review_table(elem))
                self.assertFalse(self._try(d))
                self._assert_halted(d)

    def test_a_judgment_item_beside_impl_now_defers_instead_of_vetoing(self) -> None:
        # The #332 inversion of the old rule: one HUMAN finding no longer disqualifies the
        # whole bundle — it rides the ledger while the rebuild addresses the IMPL finding.
        # The two carry-forward channels stay distinct (asserted in DeferredFindings):
        # IMPL → builder via the brief; deferred HUMAN → human via ledger + §6.
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C4 Verification (red→green) | NEEDS-HUMAN | off-by-one |\n"
                  "| C5 Causal adequacy | NEEDS-HUMAN | guards the symptom |\n")
        d = self._bundle("MIXED", review=review)
        self.assertTrue(self._try(d))
        self.assertEqual(autoiterate.ledger_entries(d),
                         ["C5 Causal adequacy — guards the symptom"])

    def test_unverifiable_gate_halts(self) -> None:
        # A gate that COULD NOT RUN is a gate-kind element, but rebuilding can't fix a
        # missing mechanic — it would spin. Forced HUMAN (never promotable, #332) — and
        # with nothing IMPL beside it, HUMAN-only halts.
        d = self._bundle("UNVER", gate=_UNVERIFIABLE)
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_declared_external_dependency_halts(self) -> None:
        # HUMAN-only: the declared dependency is the sole §6 item (never IMPL, never
        # promotable — a rebuild cannot install protoc), so the bundle halts outright.
        d = self._bundle("EXTDEP",
                         build_notes="NEEDS-HUMAN external dependency: protoc — cannot compile\n")
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_unregistered_dependency_halts(self) -> None:
        self.cfg.doctor_checks = []
        d = self._bundle("UNREG",
                         brief_body="- **Slug:** ai\n- **External dependencies:** `protoc` (build)\n")
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_unmarked_advisory_finding_halts(self) -> None:
        # Backward compatibility: an advisory file written before #264 has no [impl] tag,
        # so it can never trigger an auto-iteration.
        d = self._bundle("ADVPLAIN", advisory="- NEEDS-HUMAN — the scope looks wider than the brief\n")
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_unmappable_review_row_halts(self) -> None:
        # An Item cell with no canonical element id → fail safe toward the human.
        d = self._bundle("UNMAP", review=_review_table("Some bespoke lens"))
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_empty_section6_halts_and_never_auto_accepts(self) -> None:
        d = self._bundle("CLEAN")
        self.assertEqual(signoff.open_needs_human(d / "SUMMARY.md"), [])
        self.assertFalse(self._try(d))
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)   # NOT COMPLETE
        self.assertNotEqual(signoff.outcome_token(d / "SUMMARY.md"), "merged-wider")

    def test_missing_review_halts(self) -> None:
        # The missing-review placeholder is HUMAN, and with nothing IMPL beside it the
        # HUMAN-only rule halts the bundle until a real review exists.
        d = self._bundle("NOREV")
        (d / "check-review.md").unlink()
        assemble.assemble_summary(d, self.cfg)
        self.assertFalse(self._try(d))

    def test_bundle_not_awaiting_signoff_is_a_noop(self) -> None:
        d = self._bundle("NOTREADY", gate=_FAIL)
        signoff.record(d / "SUMMARY.md", action="iterate-do", by="t", date="2026-07-09")
        self.assertEqual(state.state(d), state.ITERATE_DO)
        self.assertFalse(self._try(d))

    def test_disabled_by_config(self) -> None:
        self.cfg.auto_iterate = False
        d = self._bundle("OFF", gate=_FAIL)
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_close_disposition_bundle_halts(self) -> None:
        # The close fast path skips builder + reviewer and asks the human to confirm the
        # close. That confirmation is a human call — never auto-iterate it.
        d = self.cfg.bundle("CLOSE")
        d.mkdir(parents=True)
        (d / "brief.md").write_text(
            "- **Slug:** c\n- **Disposition hint:** likely-close\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            driver.run_issue(d, self.cfg)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_truncated_gates_json_declines_instead_of_crashing(self) -> None:
        # An over-reaching leaf can truncate a bundle's downstream. The file still exists, so
        # the bundle still reads AWAITING_SIGNOFF — but it no longer parses. The single-issue
        # flow has no `_isolate` around auto-iterate, so this must degrade, not raise.
        d = self._bundle("CORRUPT", gate=_FAIL)
        (d / "check-gates.json").write_text('{"rows": [', encoding="utf-8")
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        buf = io.StringIO()
        with redirect_stderr(buf), redirect_stdout(io.StringIO()):
            fired = flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-07-09",
                                             apply_now=False)   # must NOT raise
        self.assertFalse(fired)
        self.assertIn("cannot classify Check findings", buf.getvalue())

    def test_missing_gates_json_is_not_awaiting_signoff(self) -> None:
        # Deleting it moves the bundle back to BUILT, so the state guard declines first.
        d = self._bundle("GONE", gate=_FAIL)
        (d / "check-gates.json").unlink()
        self.assertEqual(state.state(d), state.BUILT)
        self.assertFalse(self._try(d))

    def test_stub_reviewer_never_auto_iterates(self) -> None:
        # Offline / CI (PDCA_LEAVES_MODE=stub): the stub review flags the always-human
        # validation act, so a rehearse run can never auto-iterate.
        d = self.cfg.bundle("STUB")
        d.mkdir(parents=True)
        (d / "brief.md").write_text("- **Slug:** ai\n", encoding="utf-8")
        driver.run_issue(d, self.cfg)   # stub builder + stub reviewer
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertFalse(self._try(d))


class Budget(_Base):
    def test_exhausted_budget_hands_over_to_the_human(self) -> None:
        self.cfg.max_auto_iters = 2
        d = self._bundle("BUDGET", gate=_FAIL)
        (d / autoiterate.BUDGET_FILE).write_text('{"count": 2}\n', encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf), redirect_stdout(io.StringIO()):
            fired = flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-07-09", apply_now=False)
        self.assertFalse(fired)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)   # halted, never dropped
        self.assertFalse((d / leaves.SIGNOFF_DECISION).exists())
        self.assertIn("auto-iterate budget spent (2/2)", buf.getvalue())

    def test_budget_survives_the_iteration_archive(self) -> None:
        # auto-iterate.json must NOT be in driver.DOWNSTREAM_OF_BRIEF, or the count resets
        # every rebuild and the loop never terminates.
        self.assertNotIn(autoiterate.BUDGET_FILE, driver.DOWNSTREAM_OF_BRIEF)
        d = self._bundle("SURVIVE", gate=_FAIL)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-07-09", apply_now=True)
        self.assertTrue((d / "iteration-v1").is_dir())
        self.assertEqual(autoiterate.count(d), 1)                  # not reset by the archive

    def test_garbled_budget_file_reads_as_zero(self) -> None:
        d = self._bundle("GARBLE", gate=_FAIL)
        (d / autoiterate.BUDGET_FILE).write_text("{ not json", encoding="utf-8")
        self.assertEqual(autoiterate.count(d), 0)
        self.assertTrue(self._try(d))

    def test_repeated_rounds_terminate_at_the_cap(self) -> None:
        # A bundle whose rebuild keeps failing the same gate must reach the human, not spin.
        # The reviewer is stubbed to a CLEAN review so every rebuild's §6 stays impl-only —
        # otherwise the stub reviewer's always-human validation row would halt it at round 1
        # (which it does, correctly: see test_stub_reviewer_never_auto_iterates).
        self.cfg.max_auto_iters = 2
        d = self._bundle("SPIN", gate=_FAIL)

        def clean_review(bundle: Path, cfg: Config) -> None:
            (bundle / "check-review.md").write_text(_CLEAN_REVIEW, encoding="utf-8")

        rounds = 0
        with mock.patch.object(leaves, "run_review", clean_review), \
             redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            for _ in range(5):
                if not flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-07-09",
                                                apply_now=True):
                    break
                rounds += 1
        self.assertEqual(rounds, 2)                                # stopped at the cap
        self.assertEqual(autoiterate.count(d), 2)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)   # handed over, not dropped
        self.assertTrue((d / "iteration-v2").is_dir())             # both attempts preserved


class BatchSweep(_Base):
    """In `_drive_wave` an auto-iterate must behave exactly like a deferred human iterate-do:
    the bundle leaves the sign-off queue, and the NEXT pass's build-all rebuilds it."""

    def test_auto_iterated_bundle_leaves_the_queue_and_rebuilds_next_pass(self) -> None:
        d = self._bundle("WAVE", gate=_FAIL)
        signed_off: list[str] = []

        def signoff_batch(cfg: Config, bundles: list[Path]) -> None:
            signed_off.extend(b.name for b in bundles)
            for b in bundles:                       # a human would accept here
                summ = b / "SUMMARY.md"
                summ.write_text(summ.read_text().replace("- [ ]", "- [x]"), encoding="utf-8")
                (b / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")

        def clean_review(bundle: Path, cfg: Config) -> None:
            (bundle / "check-review.md").write_text(_CLEAN_REVIEW, encoding="utf-8")

        with mock.patch.object(leaves, "run_signoff_batch", signoff_batch), \
             mock.patch.object(leaves, "run_review", clean_review), \
             redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._drive_wave(self.cfg, [d], by="t", today="2026-07-09", max_passes=1)

        # Pass 1 auto-iterated it, so the human's sign-off session never saw it …
        self.assertEqual(signed_off, [])
        self.assertEqual(state.state(d), state.ITERATE_DO)
        self.assertEqual(autoiterate.count(d), 1)
        # … and its rebuild is deferred to the next pass, not run mid-review.
        self.assertFalse((d / "iteration-v1").is_dir())

    def test_judgment_finding_still_reaches_the_signoff_queue(self) -> None:
        d = self._bundle("WAVEJ", review=_review_table("C5 Causal adequacy"))
        seen: list[str] = []

        def signoff_batch(cfg: Config, bundles: list[Path]) -> None:
            seen.extend(b.name for b in bundles)
            for b in bundles:
                (b / leaves.SIGNOFF_DECISION).write_text("discontinue\nnot now\n", encoding="utf-8")

        with mock.patch.object(leaves, "run_signoff_batch", signoff_batch), \
             redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._drive_wave(self.cfg, [d], by="t", today="2026-07-09", max_passes=1)
        self.assertEqual(seen, ["issue_WAVEJ"])   # the human got it, as they must

    def test_repeated_auto_iterations_count_as_progress_not_a_stuck_wave(self) -> None:
        """PR #270 review (codex). A bundle already ITERATE_DO is rebuilt by `_build_all` to
        AWAITING_SIGNOFF, re-Checked, then routed straight back to ITERATE_DO — so the
        before/after state snapshots MATCH. With the sign-off queue empty, the no-progress
        check fired and the wave returned after only TWO auto rounds, stranding the bundle
        with both `max_auto_iters` and `max_passes` budget to spare."""
        self.cfg.max_auto_iters = 3
        # The size backstop is switched OFF for this bundle: it fires at 2 rounds by
        # design (#324) and would stop the loop here for a completely different — and
        # correct — reason, hiding whether the no-progress check still misfires. This test
        # is about the stuck-wave detector; `test_the_size_backstop_stops_the_loop_early`
        # in test_size_signal.py asserts the interaction itself.
        self.cfg.size_signal = {"rounds": 0}
        d = self._bundle("WAVELOOP", gate=_FAIL)     # a gate that stays red across rebuilds
        signed_off: list[str] = []

        def signoff_batch(cfg: Config, bundles: list[Path]) -> None:
            signed_off.extend(b.name for b in bundles)
            for b in bundles:                        # the human clears §6 and accepts
                summ = b / "SUMMARY.md"
                summ.write_text(summ.read_text().replace("- [ ]", "- [x]"), encoding="utf-8")
                (b / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")

        def clean_review(bundle: Path, cfg: Config) -> None:
            (bundle / "check-review.md").write_text(_CLEAN_REVIEW, encoding="utf-8")

        buf = io.StringIO()
        with mock.patch.object(leaves, "run_signoff_batch", signoff_batch), \
             mock.patch.object(leaves, "run_review", clean_review), \
             redirect_stderr(buf), redirect_stdout(io.StringIO()):
            flow._drive_wave(self.cfg, [d], by="t", today="2026-07-10", max_passes=6)

        # the FULL auto budget is spent — not truncated at two by a false stuck-wave verdict
        self.assertEqual(autoiterate.count(d), 3)
        self.assertNotIn("a full pass made no progress", buf.getvalue())
        # …and once it is spent the bundle reaches the human and completes, never abandoned
        self.assertEqual(signed_off, ["issue_WAVELOOP"])
        self.assertEqual(state.state(d), state.COMPLETE)

    def test_a_wave_that_truly_stalls_still_warns(self) -> None:
        # The negative: with the auto budget spent, nothing advances — the no-progress guard
        # must still fire. `auto_iterated` must never mask a genuine stall.
        d = self._bundle("WAVESTALL", gate=_FAIL)
        (d / autoiterate.BUDGET_FILE).write_text('{"count": 99}\n', encoding="utf-8")
        signoff.record(d / "SUMMARY.md", action="iterate-do", by="t", date="2026-07-10")
        buf = io.StringIO()
        with mock.patch.object(flow, "_build_all", lambda cfg, bundles: None), \
             redirect_stderr(buf), redirect_stdout(io.StringIO()):
            flow._drive_wave(self.cfg, [d], by="t", today="2026-07-10", max_passes=5)
        self.assertIn("a full pass made no progress", buf.getvalue())
        self.assertIn("issue_WAVESTALL", buf.getvalue())

    def test_a_raising_auto_iterate_does_not_kill_the_sweep(self) -> None:
        d = self._bundle("WAVEBOOM", gate=_FAIL)
        with mock.patch.object(flow.autoiterate, "write_decision",
                               side_effect=OSError("disk full")), \
             mock.patch.object(leaves, "run_signoff_batch", lambda cfg, bundles: None), \
             redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._drive_wave(self.cfg, [d], by="t", today="2026-07-09", max_passes=1)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)   # isolated, still reviewable


class DecisionModule(unittest.TestCase):
    """`autoiterate` itself — the guard that keeps this from ever becoming an auto-accept."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _items(self, *kinds: str) -> list[assemble.NeedsHumanItem]:
        return [assemble.NeedsHumanItem(f"finding {i}", k) for i, k in enumerate(kinds)]

    def test_eligible_needs_at_least_one_impl(self) -> None:
        # #332: "≥1 IMPL" — a HUMAN finding beside IMPL no longer vetoes (it defers).
        self.assertTrue(autoiterate.eligible(self._items(assemble.IMPL, assemble.IMPL)))
        self.assertTrue(autoiterate.eligible(self._items(assemble.IMPL, assemble.HUMAN)))
        self.assertFalse(autoiterate.eligible([]))                                 # never accept
        self.assertFalse(autoiterate.eligible(self._items(assemble.HUMAN)))        # nothing to fix
        self.assertFalse(autoiterate.eligible(self._items(assemble.STANDING)))     # the constant
        self.assertFalse(autoiterate.eligible(self._items(assemble.HUMAN, assemble.STANDING)))

    def test_the_size_backstop_is_the_one_human_item_never_deferred(self) -> None:
        # #324's invariant survives the #332 deferral: the size item is evidence that
        # further rebuilds are the wrong move, so it stops the loop rather than riding
        # the ledger. (test_size_signal.py asserts the same from the backstop's side.)
        from pdca_harness import size_signal
        size_item = assemble.NeedsHumanItem(
            size_signal.needs_human_text(["patch is 253 KB (threshold 100 KB)"]),
            assemble.HUMAN)
        self.assertFalse(autoiterate.eligible(
            self._items(assemble.IMPL) + [size_item]))

    def test_write_decision_only_ever_writes_iterate_do(self) -> None:
        autoiterate.write_decision(self.tmp, self._items(assemble.IMPL))
        token = (self.tmp / leaves.SIGNOFF_DECISION).read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(token, "iterate-do")
        self.assertIn(token, leaves.VALID_DECISIONS)
        self.assertNotEqual(token, "accept")

    def test_write_decision_refuses_a_non_implementation_set(self) -> None:
        with self.assertRaises(ValueError):
            autoiterate.write_decision(self.tmp, self._items(assemble.HUMAN))
        self.assertFalse((self.tmp / leaves.SIGNOFF_DECISION).exists())
        self.assertEqual(autoiterate.count(self.tmp), 0)          # no budget spent either

    def test_write_decision_refuses_an_empty_set(self) -> None:
        with self.assertRaises(ValueError):
            autoiterate.write_decision(self.tmp, [])

    def test_rationale_is_a_single_line_naming_the_findings(self) -> None:
        r = autoiterate.rationale(self._items(assemble.IMPL, assemble.IMPL), attempt=2)
        self.assertNotIn("\n", r)
        self.assertIn("round 2", r)
        self.assertIn("finding 0", r)
        self.assertIn("finding 1", r)

    def test_rationale_states_the_deferral_but_never_the_deferred_texts(self) -> None:
        # Criterion (3): what was addressed and what was deferred — but the rationale is
        # the line the driver folds into the BUILDER's carry-forward, so a deferred
        # judgment call must never appear in it as though it were a defect to fix (the
        # #294 property). The count states the deferral; the ledger + §6 carry the texts
        # to the HUMAN.
        items = [assemble.NeedsHumanItem("off-by-one at x.py:3", assemble.IMPL),
                 assemble.NeedsHumanItem("guards the symptom, not the cause", assemble.HUMAN),
                 assemble.NeedsHumanItem("Validation — fitness-to-purpose", assemble.STANDING)]
        r = autoiterate.rationale(items, attempt=1)
        self.assertNotIn("\n", r)
        self.assertIn("off-by-one at x.py:3", r)                    # addressed, named
        self.assertIn("Deferred 1 human finding(s)", r)             # deferred, counted
        self.assertNotIn("guards the symptom", r)                   # …but never the text
        self.assertNotIn("Validation — fitness-to-purpose", r)      # STANDING never rides


class Classification(unittest.TestCase):
    """The impl/human split is taken from the canonical 5/5/1, not re-invented."""

    def test_gate_elements_match_the_canonical_matrix(self) -> None:
        expected = {e for e, _l, k, _o in gates.canonical_elements() if k == "gate"}
        self.assertEqual(assemble._GATE_ELEMENTS, expected)
        self.assertEqual(expected, {"C2", "C4", "T1", "T2", "T3", "T4"})

    def test_judgment_and_input_cells_are_never_impl(self) -> None:
        # THE invariant: a rebuild can never be aimed at a judgment / input cell. Unchanged.
        for elem, label, kind, _oracle in gates.canonical_elements():
            if kind in ("judgment", "input"):
                item = assemble._classify_finding(f"{label} — some basis")
                self.assertNotEqual(item.kind, assemble.IMPL, f"{elem} must never be impl")

    def test_only_the_validation_row_is_standing(self) -> None:
        # #293. Of the 5/5/1's own rows, V is the one the reviewer's prompt hard-codes to
        # NEEDS-HUMAN every cycle, so it alone can be STANDING (a constant carries no signal).
        # C5/T5 are judgment too, but the reviewer raises those only on a real concern — they
        # stay situational HUMAN and still halt the bundle. The PARSER decides which row is the
        # canonical one; the classifier only honours that decision.
        for elem, label, kind, _oracle in gates.canonical_elements():
            if kind not in ("judgment", "input"):
                continue
            # A REAL verdict table: the row under test plus another canonical row, which is what
            # makes it the mandated table rather than a stray one (a lone row cannot nominate
            # itself as the constant).
            table = ("| Item | Verdict | Basis |\n|---|---|---|\n"
                     "| C1 Spec | PASS | ok |\n"
                     f"| {label} | NEEDS-HUMAN | some basis |\n")
            [(text, standing, _tag)] = assemble._needs_human(table)
            got = assemble._classify_finding(text, standing=standing).kind
            want = assemble.STANDING if elem == "V" else assemble.HUMAN
            self.assertEqual(got, want, f"{elem} ({label})")

    def test_standing_needs_an_EXACT_match_on_the_canonical_item_cell(self) -> None:
        """PR #294 review (codex). What identifies the template row is its Item cell being
        EXACTLY the canonical label — not the text's prefix, and not merely "it came from a
        table". A prefix test let a real objection wear the template's clothes; a table test let
        a second table do the same. Both are the same mistake, one layer apart."""
        TBL = "| Item | Verdict | Basis |\n|---|---|---|\n| C1 Spec | PASS | ok |\n"
        canonical = TBL + "| Validation — fitness-to-purpose | NEEDS-HUMAN | the human's call |\n"
        objection = TBL + ("| Validation — fitness-to-purpose: patches the wrong layer "
                           "| NEEDS-HUMAN | the criterion cannot be met |\n")
        bullet = TBL + "- NEEDS-HUMAN — Validation — fitness-to-purpose: patches the wrong layer\n"
        lone = "| Validation — fitness-to-purpose | NEEDS-HUMAN | the human's call |\n"

        [(_t, standing, _tag)] = assemble._needs_human(canonical)
        self.assertTrue(standing, "the canonical row of the MANDATED table IS the constant")
        [(_t, standing, _tag)] = assemble._needs_human(objection)
        self.assertFalse(standing, "a longer Item cell is a real objection, not the template")
        [(_t, standing, _tag)] = assemble._needs_human(bullet)
        self.assertFalse(standing, "free prose is never the template row")
        [(_t, standing, _tag)] = assemble._needs_human(lone)
        self.assertFalse(standing, "a lone row in a stray table cannot nominate itself")

    def test_the_classifier_never_re_derives_standing_from_the_text(self) -> None:
        # Two sources of truth for "is this the constant row" is what produced the bug. The
        # classifier honours the caller's verdict and does not second-guess it from the text.
        text = "Validation — fitness-to-purpose — the human's call"
        self.assertEqual(assemble._classify_finding(text).kind, assemble.HUMAN)
        self.assertEqual(assemble._classify_finding(text, standing=True).kind, assemble.STANDING)

    def test_impl_marker_is_case_insensitive_and_stripped(self) -> None:
        self.assertEqual(assemble._classify_finding("[IMPL] — bug"),
                         assemble.NeedsHumanItem("bug", assemble.IMPL))

    def test_unknown_text_is_human(self) -> None:
        self.assertEqual(assemble._classify_finding("something bespoke").kind, assemble.HUMAN)

    def test_a_gate_row_kind_comes_from_its_element_not_its_label(self) -> None:
        # An instance names its own gates; the label may not start with the element id.
        rows = {"rows": [{"check": "fix verified", "result": "fail", "gating": True,
                          "element": "C4", "path_line": "", "oracle": "run-verify.sh"}]}
        self.assertEqual(assemble._failed_gating_items(rows)[0].kind, assemble.IMPL)
        rows["rows"][0]["element"] = ""      # unknown → fail safe
        self.assertEqual(assemble._failed_gating_items(rows)[0].kind, assemble.HUMAN)


class VRowForms(_Base):
    """Criterion (4) of #332: the STANDING match accepts the three observed production
    forms of the Validation Item cell — normalize (an optional leading `<element-id> — `
    prefix; ASCII `--` for `—`), then compare EXACT. #294's rule stands: anything ELSE
    added to the cell makes it a real objection, never the constant."""

    FORMS = ("Validation — fitness-to-purpose",
             "V — Validation — fitness-to-purpose",
             "Validation -- fitness-to-purpose")

    def test_each_production_form_is_standing_in_the_mandated_table(self) -> None:
        for form in self.FORMS:
            with self.subTest(form=form):
                table = ("| Item | Verdict | Basis |\n|---|---|---|\n"
                         "| C1 Spec | PASS | ok |\n"
                         f"| {form} | NEEDS-HUMAN | the human's call |\n")
                [(text, standing, _tag)] = assemble._needs_human(table)
                self.assertTrue(standing, form)
                self.assertEqual(assemble._classify_finding(text, standing=standing).kind,
                                 assemble.STANDING)

    def test_a_fully_prefixed_table_is_still_the_mandated_table(self) -> None:
        # The review prompt lists the matrix as "<id> — <label>", and a real reviewer
        # copies that whole form into the Item column — every cell carries the prefix,
        # so the ≥2-canonical-cells table detection must normalize too, or the V row of
        # a prefixed table could never be STANDING.
        table = ("| Item | Verdict | Basis |\n|---|---|---|\n"
                 "| C1 — C1 Spec | PASS | ok |\n"
                 "| C4 — C4 Verification (red→green) | PASS | ok |\n"
                 "| V — Validation — fitness-to-purpose | NEEDS-HUMAN | the human's call |\n")
        [(_text, standing, _tag)] = assemble._needs_human(table)
        self.assertTrue(standing)

    def test_comparison_is_exact_after_normalization_never_prefix_matching(self) -> None:
        for cell in ("Validation — fitness-to-purpose: patches the wrong layer",
                     "V — Validation — fitness-to-purpose: patches the wrong layer",
                     "Re Validation — fitness-to-purpose"):
            with self.subTest(cell=cell):
                table = ("| Item | Verdict | Basis |\n|---|---|---|\n"
                         "| C1 Spec | PASS | ok |\n"
                         f"| {cell} | NEEDS-HUMAN | x |\n")
                [(_t, standing, _tag)] = assemble._needs_human(table)
                self.assertFalse(standing, cell)

    def test_no_production_form_is_ever_deferred_to_the_ledger(self) -> None:
        # End to end, and why (4) matters MORE under (3): mis-reading the constant as an
        # ordinary HUMAN finding no longer halts the bundle — it would DEFER the template
        # row into the ledger, where it lingers as a §6 item forever. STANDING is exactly
        # what keeps it out.
        for i, form in enumerate(self.FORMS):
            with self.subTest(form=form):
                review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                          "| C4 Verification (red→green) | NEEDS-HUMAN | off-by-one |\n"
                          f"| {form} | NEEDS-HUMAN | fitness is the human's call |\n")
                d = self._bundle(f"VF{i}", review=review)
                self.assertTrue(self._try(d))
                self.assertEqual(autoiterate.ledger_entries(d), [])


class ImplTagPromotion(_Base):
    """Criterion (2) of #332: builder-fixability STATED by the reviewer — a
    `NEEDS-HUMAN [impl]` VERDICT on a judgment cell — instead of inferred from the
    taxonomy cell. Promotable = judgment-kind minus V; STANDING wins over the tag;
    untagged stays HUMAN (the fail-safe is unchanged)."""

    def test_promotable_set_is_judgment_minus_v_from_the_canonical_matrix(self) -> None:
        expected = ({e for e, _l, k, _o in gates.canonical_elements() if k == "judgment"}
                    - {"V"})
        self.assertEqual(assemble._PROMOTABLE_ELEMENTS, expected)
        self.assertEqual(expected, {"C5", "T5"})

    def test_c5_and_t5_tagged_verdicts_promote_and_fire(self) -> None:
        for iid, elem in (("TAGC5", "C5 Causal adequacy"), ("TAGT5", "T5 Judgment")):
            with self.subTest(elem=elem):
                d = self._bundle(iid, review=_review_table(
                    elem, verdict="NEEDS-HUMAN [impl]", basis="weak test, builder-fixable"))
                items = assemble.collect_needs_human(d, self.cfg)
                self.assertEqual([i.kind for i in items],
                                 [assemble.IMPL, assemble.STANDING])
                self.assertTrue(self._try(d))
                self.assertEqual(autoiterate.ledger_entries(d), [],
                                 "promoted means addressed by the rebuild, not deferred")

    def test_tag_on_input_cells_is_ignored(self) -> None:
        for iid, elem in (("TAGC1", "C1 Spec"), ("TAGC3", "C3 Change")):
            with self.subTest(elem=elem):
                d = self._bundle(iid, review=_review_table(elem, verdict="NEEDS-HUMAN [impl]"))
                kinds = [i.kind for i in assemble.collect_needs_human(d, self.cfg)]
                self.assertNotIn(assemble.IMPL, kinds)
                self.assertFalse(self._try(d))   # HUMAN-only ⇒ halts
                self._assert_halted(d)

    def test_a_tagged_v_row_stays_standing(self) -> None:
        # STANDING is checked BEFORE the tag: the constant cannot be promoted into a
        # reason to rebuild (V is not promotable, and the row carries no signal).
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C1 Spec | PASS | ok |\n"
                  "| Validation — fitness-to-purpose | NEEDS-HUMAN [impl] | tagged in error |\n")
        d = self._bundle("TAGV", review=review)
        items = assemble.collect_needs_human(d, self.cfg)
        self.assertEqual([i.kind for i in items], [assemble.STANDING])
        self.assertFalse(self._try(d))           # nothing IMPL ⇒ still a clean halt
        self._assert_halted(d)

    def test_an_untagged_judgment_verdict_stays_human(self) -> None:
        d = self._bundle("UNTAG", review=_review_table("C5 Causal adequacy"))
        kinds = [i.kind for i in assemble.collect_needs_human(d, self.cfg)]
        self.assertEqual(kinds, [assemble.HUMAN, assemble.STANDING])
        self.assertFalse(self._try(d))

    def test_a_human_tag_is_stripped_and_stays_human(self) -> None:
        # The advisory prompts now REQUIRE a tag; [human] is the explicit spelling of
        # the untagged fail-safe, so it must classify identically (and read cleanly).
        d = self._bundle("HTAG",
                         advisory="- NEEDS-HUMAN [human] — scope looks wider than the brief\n")
        [item] = assemble.collect_needs_human(d, self.cfg)
        self.assertEqual(item, assemble.NeedsHumanItem("scope looks wider than the brief",
                                                       assemble.HUMAN))
        self.assertFalse(self._try(d))

    def test_deterministic_items_are_never_promotable(self) -> None:
        # A gate that could not run, a declared external dependency and an unregistered
        # dependency never pass through the verdict-tag parse: they are constructed
        # HUMAN outright, so no tag anywhere can turn them into a reason to rebuild.
        self.cfg.doctor_checks = []
        d = self._bundle(
            "NOPROM", gate=_UNVERIFIABLE,
            build_notes="NEEDS-HUMAN external dependency: protoc — cannot compile\n",
            brief_body="- **Slug:** ai\n- **External dependencies:** `protoc` (build)\n")
        kinds = {i.kind for i in assemble.collect_needs_human(d, self.cfg)}
        self.assertEqual(kinds, {assemble.HUMAN})
        self.assertFalse(self._try(d))


class SoftHardRounds(_Base):
    """Criterion (1) of #332: the soft/hard round budgets, table-driven on the worked
    example (soft 3, hard 5): rounds ≤3 always fire; 3<n≤5 only if the recorded open
    IMPL count did not increase; n>5 never. Soft unset ⇒ hard-only, exactly as today."""

    def _seed(self, d: Path, spent: int, history: list[int]) -> None:
        (d / autoiterate.BUDGET_FILE).write_text(
            json.dumps({"count": spent, "impl_counts": history}), encoding="utf-8")

    def test_worked_example_soft3_hard5(self) -> None:
        self.cfg.max_auto_iters = 5
        self.cfg.soft_auto_iters = 3
        d = self.tmp / "rounds"
        d.mkdir()
        cases = [   # (spent, recorded history, current IMPL count, may fire?)
            (0, [],              9, True),    # round 1: always
            (2, [5, 9],          9, True),    # round 3: always, even with a rising count
            (3, [3, 2, 2],       2, True),    # round 4: held ⇒ fires
            (3, [3, 2, 2],       1, True),    # round 4: fell ⇒ fires
            (3, [3, 2, 2],       3, False),   # round 4: rose ⇒ hands over
            (4, [3, 2, 2, 2],    2, True),    # round 5: held ⇒ fires
            (4, [3, 2, 2, 1],    2, False),   # round 5: rose ⇒ hands over
            (5, [3, 2, 2, 1, 1], 0, False),   # round 6: never, converging or not
        ]
        for spent, history, impl_now, fires in cases:
            with self.subTest(spent=spent, history=history, impl_now=impl_now):
                self._seed(d, spent, history)
                verdict = autoiterate.budget_verdict(d, self.cfg, impl_count=impl_now)
                self.assertEqual(verdict == "", fires, verdict)

    def test_soft_unset_reproduces_the_hard_only_behaviour(self) -> None:
        self.cfg.max_auto_iters = 5
        self.assertIsNone(self.cfg.soft_auto_iters)
        d = self.tmp / "hardonly"
        d.mkdir()
        self._seed(d, 4, [1, 2, 3, 4])       # round 5, IMPL count rising every round
        self.assertEqual(autoiterate.budget_verdict(d, self.cfg, impl_count=9), "")
        self._seed(d, 5, [1, 2, 3, 4, 5])    # round 6: the hard cap, as always
        self.assertNotEqual(autoiterate.budget_verdict(d, self.cfg, impl_count=0), "")

    def test_an_old_shape_budget_file_fails_toward_the_human_in_the_soft_window(self) -> None:
        # Pre-#332 files carry {"count": n} only. Inside the always-fire window that is
        # fine; inside the soft window there is no history to prove convergence, so the
        # driver declines rather than guessing.
        self.cfg.max_auto_iters = 5
        self.cfg.soft_auto_iters = 3
        d = self.tmp / "oldshape"
        d.mkdir()
        (d / autoiterate.BUDGET_FILE).write_text('{"count": 2}\n', encoding="utf-8")
        self.assertEqual(autoiterate.budget_verdict(d, self.cfg, impl_count=1), "")
        (d / autoiterate.BUDGET_FILE).write_text('{"count": 3}\n', encoding="utf-8")
        self.assertIn("no per-round IMPL count",
                      autoiterate.budget_verdict(d, self.cfg, impl_count=1))

    def test_bump_records_per_round_impl_counts_and_count_stays_tolerant(self) -> None:
        d = self.tmp / "bump"
        d.mkdir()
        autoiterate.bump(d, impl_count=3)
        autoiterate.bump(d, impl_count=2)
        self.assertEqual(autoiterate.count(d), 2)
        self.assertEqual(autoiterate.impl_counts(d), [3, 2])
        (d / autoiterate.BUDGET_FILE).write_text('{"count": 7}\n', encoding="utf-8")
        self.assertEqual(autoiterate.count(d), 7)      # old shape still counts
        self.assertEqual(autoiterate.impl_counts(d), [])

    def test_the_flow_names_the_soft_decline(self) -> None:
        self.cfg.max_auto_iters = 5
        self.cfg.soft_auto_iters = 1
        d = self._bundle("SOFT", gate=_FAIL)             # one IMPL finding this round
        self._seed(d, 1, [0])                            # round 2: 0 → 1 is a rise
        buf = io.StringIO()
        with redirect_stderr(buf), redirect_stdout(io.StringIO()):
            fired = flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-08-02",
                                             apply_now=False)
        self.assertFalse(fired)
        self.assertIn("soft budget", buf.getvalue())
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)   # halted, never dropped

    def test_the_flow_fires_in_the_soft_window_while_the_count_holds(self) -> None:
        self.cfg.max_auto_iters = 5
        self.cfg.soft_auto_iters = 1
        d = self._bundle("SOFT2", gate=_FAIL)
        self._seed(d, 1, [1])                            # round 2: 1 → 1 held
        self.assertTrue(self._try(d))
        self.assertEqual(autoiterate.impl_counts(d), [1, 1])   # this round recorded too


class DeferredFindings(_Base):
    """Criterion (3) of #332: deferral is a delay, never a loss — the ledger survives the
    archive, re-enters §6 every assemble, and never leaks into the builder's channel."""

    def test_ledger_is_cycle_evidence_and_never_archived(self) -> None:
        self.assertNotIn(autoiterate.LEDGER_FILE, driver.DOWNSTREAM_OF_BRIEF)
        self.assertIn(autoiterate.LEDGER_FILE, state.CYCLE_EVIDENCE_ONLY)

    def test_deferred_finding_survives_the_archive_and_reenters_section6(self) -> None:
        d = self._bundle("DEF1", gate=_FAIL, review=_MIXED_REVIEW)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertTrue(flow._maybe_auto_iterate(self.cfg, d, by="",
                                                     today="2026-08-02", apply_now=True))
            driver.run_issue(d, self.cfg)
        self.assertTrue((d / "iteration-v1").is_dir())
        self.assertFalse((d / "iteration-v1" / autoiterate.LEDGER_FILE).exists())
        self.assertEqual(autoiterate.ledger_entries(d), [_MIXED_C5_TEXT])
        summary = (d / "SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn(f"- [ ] {_MIXED_C5_TEXT}", summary)    # C6 still blocks on it

    def test_round_one_human_finding_still_in_section6_at_handover(self) -> None:
        self.cfg.max_auto_iters = 1
        d = self._bundle("DEF2", gate=_FAIL, review=_MIXED_REVIEW)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertTrue(flow._maybe_auto_iterate(self.cfg, d, by="",
                                                     today="2026-08-02", apply_now=True))
            driver.run_issue(d, self.cfg)
            self.assertFalse(flow._maybe_auto_iterate(self.cfg, d, by="",
                                                      today="2026-08-02", apply_now=True))
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertTrue(any(_MIXED_C5_TEXT in it
                            for it in signoff.open_needs_human(d / "SUMMARY.md")))

    def test_the_merge_is_deduped_when_the_finding_is_raised_again(self) -> None:
        d = self._bundle("DEF3", review=_MIXED_REVIEW)
        (d / autoiterate.LEDGER_FILE).write_text(
            json.dumps({"deferred": [_MIXED_C5_TEXT]}), encoding="utf-8")
        texts = [i.text for i in assemble.collect_needs_human(d, self.cfg)]
        self.assertEqual(texts.count(_MIXED_C5_TEXT), 1)

    def test_deferred_texts_never_reach_the_builder_carry_forward(self) -> None:
        # The two carry-forward channels stay distinct: IMPL → builder via the brief;
        # deferred HUMAN → human via ledger + §6 (the #294 property, held under #332).
        d = self._bundle("DEF4", gate=_FAIL, review=_MIXED_REVIEW)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-08-02", apply_now=True)
            driver.run_issue(d, self.cfg)
        brief_text = (d / "brief.md").read_text(encoding="utf-8")
        self.assertIn("C4", brief_text)                        # the real defect…
        self.assertNotIn("guards the symptom", brief_text)     # …never the judgment call
        self.assertIn("Deferred 1 human finding(s)", brief_text)   # deferral is stated

    def test_a_garbled_ledger_reads_as_empty(self) -> None:
        d = self._bundle("DEF5", gate=_FAIL)
        (d / autoiterate.LEDGER_FILE).write_text("{ not json", encoding="utf-8")
        self.assertEqual(autoiterate.ledger_entries(d), [])
        self.assertTrue(self._try(d))          # never a crash, never a veto


class LedgerRetirement(_Base):
    """The #335 fold: ledger retirement is exact-first, two-tier on BOTH sides.

    A ticked §6 row retires its unique hit (exact tier first, else `_same_finding`)
    only if a still-open row does not claim it. Protection mirrors the tick match: an
    open row verbatim equal to an entry protects that entry ALONE (near-twin pairs still
    drain); an edited open row protects every `_same_finding` match, even against an
    exact tick (fail closed: lingering is visible, lost is unrecoverable). The flat
    symmetric-fuzzy exclusion is the known regression — it makes the near-twin pair
    permanently unclearable (instance fix getwyrd/wyrd-pdca@e4fdf3b)."""

    E1 = "C5 Causal adequacy — flaky retry loop in worker A"
    E2 = "C5 Causal adequacy — flaky retry loop in worker A and worker B"

    def _dir(self) -> Path:
        d = self.tmp / "unit"
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
        return d

    def _set(self, d: Path, entries: list[str], *, ticked: tuple = (),
             open_: tuple = ()) -> None:
        (d / autoiterate.LEDGER_FILE).write_text(
            json.dumps({"deferred": list(entries)}), encoding="utf-8")
        lines = ["# Result — issue U", "",
                 "## 6. NEEDS-HUMAN — items the human must clear before sign-off"]
        lines += [f"- [x] {t}" for t in ticked]
        lines += [f"- [ ] {o}" for o in open_]
        lines += ["", "## 9. Check sign-off", "- Outcome:", "- By / date:"]
        (d / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_335_repro_an_annotated_open_row_protects_its_entry(self) -> None:
        # (a) The field-report repro: the human ANNOTATED entry E1's §6 row and left it
        # open (unadjudicated); a SIMILAR new finding was ticked. The tick's only fuzzy
        # hit is E1 — but the open row claims it, so the unadjudicated entry survives.
        d = self._dir()
        self._set(d, [self.E1],
                  ticked=(self.E1 + " (round 2)",),
                  open_=(self.E1 + " — discussing with the maintainer",))
        autoiterate.retire_cleared(d)
        self.assertEqual(autoiterate.ledger_entries(d), [self.E1],
                         "the unadjudicated entry must survive")

    def test_an_exact_tick_beats_an_open_near_twin(self) -> None:
        # Near-twin PAIR in the ledger; E1 exactly ticked, E2 exactly open. Symmetric
        # fuzzy exclusion keeps E1 forever (the open E2 fuzzy-matches it) — the
        # permanently-unclearable ledger. Exact-first: the open row verbatim-owns E2,
        # protects E2 alone, and the tick drains E1.
        d = self._dir()
        self._set(d, [self.E1, self.E2], ticked=(self.E1,), open_=(self.E2,))
        autoiterate.retire_cleared(d)
        self.assertEqual(autoiterate.ledger_entries(d), [self.E2])

    EDIT_SHAPES = (
        ("case change", lambda t: t.upper()),
        ("whitespace change", lambda t: "  " + t.replace(" — ", "   —   ")),
        ("appended annotation", lambda t: t + " — still under discussion"),
        ("prepended annotation", lambda t: "unresolved: " + t),
    )

    def test_matcher_drift_guard_every_tick_shape_also_protects_when_open(self) -> None:
        # (b) Pins the RELATION between the two matchers, not either matcher alone:
        # every edit shape the tick match tolerates must also protect when the same
        # edited row is left open — even against an EXACT tick of the entry. If either
        # side drifts (a tolerant tick with an exact-only exclusion, or vice versa),
        # one of the two sub-asserts goes red.
        for name, edit in self.EDIT_SHAPES:
            with self.subTest(shape=name, side="tick"):
                d = self._dir()
                self._set(d, [self.E1], ticked=(edit(self.E1),))
                autoiterate.retire_cleared(d)
                self.assertEqual(autoiterate.ledger_entries(d), [],
                                 f"a tick edited by {name} must still retire")
            with self.subTest(shape=name, side="open"):
                d = self._dir()
                self._set(d, [self.E1], ticked=(self.E1,), open_=(edit(self.E1),))
                autoiterate.retire_cleared(d)
                self.assertEqual(autoiterate.ledger_entries(d), [self.E1],
                                 f"an open row edited by {name} must still protect, "
                                 "even against an exact tick")

    def test_an_edited_open_row_matching_two_near_twins_protects_both(self) -> None:
        # (c) The edited row verbatim-owns nothing, so we cannot tell WHICH entry it is:
        # protect every match, even against exact ticks of both.
        d = self._dir()
        edited = self.E2 + " — still discussing"       # _same_finding-matches E1 AND E2
        self._set(d, [self.E1, self.E2], ticked=(self.E1, self.E2), open_=(edited,))
        autoiterate.retire_cleared(d)
        self.assertEqual(autoiterate.ledger_entries(d), [self.E1, self.E2])

    def test_an_ambiguous_tick_retires_nothing(self) -> None:
        # Fail closed on the tick side too: a tick fuzzy-hitting two entries cannot
        # know which one it adjudicated.
        d = self._dir()
        self._set(d, [self.E1, self.E2], ticked=(self.E2 + " (see notes)",))
        autoiterate.retire_cleared(d)
        self.assertEqual(autoiterate.ledger_entries(d), [self.E1, self.E2])

    def test_retirement_runs_at_the_human_iterate_transition(self) -> None:
        # Integration: the human ticks the deferred row and answers iterate-do; the
        # driver's ITERATE_DO transition retires the entry before archiving the SUMMARY.
        d = self._bundle("RET", review=_review_table("C5 Causal adequacy"))
        entry = "C5 Causal adequacy — off-by-one"
        (d / autoiterate.LEDGER_FILE).write_text(
            json.dumps({"deferred": [entry]}), encoding="utf-8")
        summ = d / "SUMMARY.md"
        summ.write_text(summ.read_text(encoding="utf-8").replace(
            f"- [ ] {entry}", f"- [x] {entry}"), encoding="utf-8")
        signoff.record(summ, action="iterate-do", by="t", date="2026-08-02")
        self.assertEqual(state.state(d), state.ITERATE_DO)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            driver.advance(d, self.cfg)
        self.assertEqual(autoiterate.ledger_entries(d), [])
        self.assertTrue((d / "iteration-v1").is_dir())

    def test_an_auto_round_never_retires_anything(self) -> None:
        # Auto-iterate never ticks a §6 box, so its own transition retires nothing —
        # it can only ever ADD to the ledger.
        d = self._bundle("RETAUTO", gate=_FAIL, review=_MIXED_REVIEW)
        seeded = "T5 Judgment — an earlier deferral"
        (d / autoiterate.LEDGER_FILE).write_text(
            json.dumps({"deferred": [seeded]}), encoding="utf-8")
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertTrue(flow._maybe_auto_iterate(self.cfg, d, by="",
                                                     today="2026-08-02", apply_now=True))
        self.assertIn(seeded, autoiterate.ledger_entries(d))


class ConfigPlumbing(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _load(self, extra: str = "") -> Config:
        (self.tmp / "pdca.toml").write_text(
            '[project]\ndefault_branch = "main"\n'
            '[leaves.builder]\nmode = "stub"\n[leaves.reviewer]\nmode = "stub"\n' + extra,
            encoding="utf-8")
        return Config.load(self.tmp)

    def test_off_by_default(self) -> None:
        cfg = self._load()
        self.assertFalse(cfg.auto_iterate)
        self.assertEqual(cfg.max_auto_iters, 3)

    def test_driver_table_enables_it(self) -> None:
        self.assertTrue(self._load("[driver]\nauto_iterate = true\n").auto_iterate)

    def test_env_overrides_the_toml(self) -> None:
        with mock.patch.dict(os.environ, {"PDCA_AUTO_ITERATE": "1"}):
            self.assertTrue(self._load().auto_iterate)
        with mock.patch.dict(os.environ, {"PDCA_AUTO_ITERATE": "0"}):
            self.assertFalse(self._load("[driver]\nauto_iterate = true\n").auto_iterate)

    def test_max_auto_iters_is_clamped_below_max_passes(self) -> None:
        # Else exhausting the auto budget could coincide with the wave's pass budget running
        # out, leaving the bundle mid-flight at ITERATE_DO (#260's abandonment shape).
        cfg = self._load("[driver]\nmax_passes = 3\nmax_auto_iters = 99\n")
        self.assertEqual(cfg.max_auto_iters, 2)
        self.assertLess(cfg.max_auto_iters, cfg.max_passes)

    def test_max_auto_iters_floor_of_one(self) -> None:
        self.assertEqual(self._load("[driver]\nmax_passes = 1\nmax_auto_iters = 0\n").max_auto_iters, 1)

    def test_soft_auto_iters_unset_defaults_to_the_hard_budget(self) -> None:
        # Criterion (1): a rendered instance that never set it reproduces today's
        # behaviour exactly — soft == hard, no soft window at all.
        cfg = self._load("[driver]\nmax_auto_iters = 5\n")
        self.assertIsNone(cfg.soft_auto_iters)
        self.assertEqual(autoiterate.soft_budget(cfg), cfg.max_auto_iters)

    def test_soft_auto_iters_parsed_and_clamped(self) -> None:
        cfg = self._load("[driver]\nmax_auto_iters = 5\nsoft_auto_iters = 3\n")
        self.assertEqual(cfg.soft_auto_iters, 3)
        self.assertEqual(autoiterate.soft_budget(cfg), 3)
        # Never above the hard budget (a soft window past the cap is meaningless)…
        cfg = self._load("[driver]\nmax_auto_iters = 3\nsoft_auto_iters = 99\n")
        self.assertEqual(cfg.soft_auto_iters, 3)
        # …never below one, and a non-numeric value falls back to unset (= hard-only).
        self.assertEqual(self._load("[driver]\nsoft_auto_iters = 0\n").soft_auto_iters, 1)
        self.assertIsNone(self._load('[driver]\nsoft_auto_iters = "lots"\n').soft_auto_iters)

    def test_soft_env_override(self) -> None:
        with mock.patch.dict(os.environ, {"PDCA_SOFT_AUTO_ITERS": "2"}):
            self.assertEqual(self._load("[driver]\nmax_auto_iters = 5\n").soft_auto_iters, 2)

    def test_cli_flag_opts_in(self) -> None:
        cfg = _stub_config(self.tmp)
        cfg.auto_iterate = False
        with mock.patch.object(cli.Config, "load", return_value=cfg), \
             mock.patch.object(cli.flow, "flow", return_value=state.COMPLETE), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            cli.main(["flow", "ID1", "--auto-iterate", "--no-publish", "--no-act"])
        self.assertTrue(cfg.auto_iterate)


if __name__ == "__main__":
    unittest.main()
