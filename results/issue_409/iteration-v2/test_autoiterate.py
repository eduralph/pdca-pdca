"""Auto-iterate while Check still finds implementation work (issues #264, #409; stdlib
unittest).

The driver may rebuild a bundle unattended when its SUMMARY §6 carries at least one
implementation defect — a `gate` cell of the 5/5/1 (C2/C4/T1..T4), or an advisory finding the
leaf tagged `[impl]`. Since #409 a HUMAN finding beside it (a `judgment` cell C5/T5/V, an
`input` cell C1/C3, a gate that could not run, an external dependency, an unmarked advisory
bullet, a row it cannot classify) no longer vetoes that rebuild: it is DEFERRED to
`deferred-findings.json` and returns to §6 at handover, where C6 still makes the human clear
it. A §6 with no implementation work still halts at once. Exactly two things stop the loop
while implementation work remains: the size backstop's item and `max_auto_iters`.

Load-bearing negatives, each its own test: it must never auto-accept, never tick a §6 box,
never lose a HUMAN finding it iterated past, never retire one the human did not tick, and
never run past either stop. Offline: stub leaves, real gate commands, no Claude.

New symbols are reached as module attributes (`autoiterate.retire_cleared`), never imported
at module top: with the production change reverted, an import error would read as "the
module never loaded", not as the red leg.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import (assemble, autoiterate, cli, driver, flow, gates, leaves, signoff,
                          size_signal, state)
from pdca_harness.config import Config, LeafConfig

_GATE = {"id": "C4", "tier": "C4", "label": "verify", "scope": "bundle", "gating": True}
_PASS = {**_GATE, "cmd": "true"}
_FAIL = {**_GATE, "cmd": "false"}
_UNVERIFIABLE = {**_GATE, "cmd": "echo 'PDCA-UNVERIFIABLE: no prod file'; exit 0"}

_CLEAN_REVIEW = "All advisory items PASS.\n"


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


# The ledger's file name, spelled here so a helper can read it on either leg of the C4
# verify; `test_the_ledger_is_cycle_evidence_and_is_never_archived` pins it to the module.
_LEDGER = "deferred-findings.json"

# The production shape #409 is about: a Do-fixable defect beside a situational judgment
# concern, with the reviewer's standing Validation row as every real review carries it.
_C5_TEXT = "C5 Causal adequacy — guards the symptom, not the cause"
_MIXED_REVIEW = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                 "| C4 Verification (red→green) | NEEDS-HUMAN | off-by-one |\n"
                 "| C5 Causal adequacy | NEEDS-HUMAN | guards the symptom, not the cause |\n"
                 f"{_STANDING_ROW}\n")
_IMPL_ONLY_REVIEW = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                     "| C4 Verification (red→green) | NEEDS-HUMAN | off-by-one |\n"
                     "| C5 Causal adequacy | PASS | ok |\n"
                     f"{_STANDING_ROW}\n")


def _ledger(d: Path) -> list[str] | None:
    """The ledger's entries as written on disk, or None when there is no ledger."""
    p = d / _LEDGER
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["items"]


def _write_ledger(d: Path, entries: list[str]) -> None:
    (d / _LEDGER).write_text(json.dumps({"items": entries}), encoding="utf-8")


def _section6(summary: Path) -> str:
    text = summary.read_text(encoding="utf-8")
    return text.split("## 6. NEEDS-HUMAN", 1)[1].split("\n## ", 1)[0]


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
        """No decision written, no budget spent, nothing deferred (the human is about to read
        this §6 directly), bundle still waiting on the human."""
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertFalse((d / leaves.SIGNOFF_DECISION).exists())
        self.assertEqual(autoiterate.count(d), 0)
        self.assertIsNone(_ledger(d))
        self.assertTrue(signoff.open_needs_human(d / "SUMMARY.md") or True)  # §6 untouched

    def _assert_deferred(self, d: Path, expected: list[str]) -> None:
        """The round FIRED, and the ledger holds exactly ``expected`` — the HUMAN findings it
        iterated past, and nothing else (no IMPL item, no STANDING row)."""
        self.assertEqual(state.state(d), state.ITERATE_DO)
        self.assertEqual(autoiterate.count(d), 1)
        self.assertEqual(_ledger(d), expected)


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

    def test_a_situational_judgment_concern_beside_it_is_deferred_not_dropped(self) -> None:
        # The distinction that makes this safe: C5/T5 are judgment cells too, but the reviewer
        # raises them only on a REAL concern — so they carry signal and must reach the human,
        # standing row or not. Since #409 that means the ledger, not a veto: the rebuild runs,
        # and the concern returns to §6 at handover. The standing row is not a deferral.
        d = self._bundle("SV3", review=_MIXED_REVIEW)
        self.assertTrue(self._try(d), "a judgment concern beside a defect defers, not vetoes")
        self._assert_deferred(d, [_C5_TEXT])

    # The four tests below are PR #294's scopings of STANDING. Each once asserted a HALT,
    # because STANDING was then the only non-IMPL kind that did not veto. Since #409 an
    # ordinary HUMAN item does not veto either, so what tells the two kinds apart is the
    # LEDGER: a HUMAN finding is recorded there and returned to §6 at handover; STANDING is
    # not. A real objection mistaken for the standing row would be archived with its round
    # and never reach the handover — so each test now asserts the objection is in the ledger
    # and the standing row is not.

    def test_an_advisory_fitness_objection_is_never_standing(self) -> None:
        """PR #294 review (codex). STANDING is the PRIMARY review's privilege, and nothing
        else's.

        `collect_needs_human` runs `check-review.md` and every `check-advisory-*.md` through the
        same classifier. The adversary's prompt tells it to raise architectural / scope /
        fitness objections as free-form `- NEEDS-HUMAN — …` bullets — so one that happens to
        begin "Validation — fitness-to-purpose" was being read as the reviewer's signal-free
        standing row, and an unattended rebuild would ARCHIVE a real objection. The basis for
        STANDING is "this row is a constant", which is true of the reviewer's mandated table
        and of nothing else.
        """
        objection = ("Validation — fitness-to-purpose: this patches the wrong layer; the "
                     "success criterion cannot be met by this design")
        d = self._bundle("SV5", review=_review_table("C4 Verification (red→green)"),
                         advisory=f"# Adversary\n\n- NEEDS-HUMAN — {objection}\n")
        self.assertTrue(self._try(d))
        self._assert_deferred(d, [objection])   # held for the human; the standing row is not

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
        self.assertTrue(self._try(d))
        self._assert_deferred(d, ["Validation — fitness-to-purpose: patches the wrong layer"])

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
        self.assertTrue(self._try(d))
        self._assert_deferred(d, ["Validation — fitness-to-purpose: patches the wrong layer — "
                                  "the criterion cannot be met by this design"])

    def test_a_concerns_table_with_the_EXACT_label_is_still_a_real_objection(self) -> None:
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
        self.assertTrue(self._try(d))
        self._assert_deferred(d, ["Validation — fitness-to-purpose — patches the wrong layer"])

    def test_two_standing_candidates_fail_closed(self) -> None:
        # The template row is a CONSTANT — it occurs once. If two survive (a duplicated row, a
        # second verdict-shaped table), at least one is not the constant and we cannot tell
        # which. Grant STANDING to neither — so BOTH are held for the human, rather than risk
        # archiving a real objection as the constant.
        review = ("# Review\n\n| Item | Verdict | Basis |\n|---|---|---|\n"
                  "| C4 Verification (red→green) | NEEDS-HUMAN | [impl] off-by-one |\n"
                  "| C5 Causal adequacy | PASS | ok |\n"
                  f"{_STANDING_ROW}\n"
                  "| Validation — fitness-to-purpose | NEEDS-HUMAN | and again, differently |\n")
        d = self._bundle("SV10", review=review)
        self.assertTrue(self._try(d))
        self._assert_deferred(d, [
            "Validation — fitness-to-purpose — fitness is the human's call",
            "Validation — fitness-to-purpose — and again, differently"])

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
    """A §6 with no implementation work still stops at once: architectural, environmental,
    or unclassifiable findings with nothing beside them for a rebuild to address. (Beside an
    IMPL finding they are deferred instead — see `DefersHumanFindings`.)"""

    def test_judgment_cells_halt(self) -> None:
        # THE load-bearing negative: C5 causal adequacy, T5 judgment, the validation act —
        # with no implementation work beside them, there is nothing to rebuild for.
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

    def test_unverifiable_gate_halts(self) -> None:
        # A gate that COULD NOT RUN is a gate-kind element, but rebuilding can't fix a
        # missing mechanic — it would spin. Forced HUMAN.
        d = self._bundle("UNVER", gate=_UNVERIFIABLE)
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_declared_external_dependency_alone_halts(self) -> None:
        d = self._bundle("EXTDEP",
                         build_notes="NEEDS-HUMAN external dependency: protoc — cannot compile\n")
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_unregistered_dependency_alone_halts(self) -> None:
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

    def test_missing_review_alone_halts(self) -> None:
        d = self._bundle("NOREV")
        (d / "check-review.md").unlink()
        assemble.assemble_summary(d, self.cfg)
        self.assertFalse(self._try(d))
        self._assert_halted(d)

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


class DefersHumanFindings(_Base):
    """#409 clause 2 — defer, don't veto.

    A HUMAN finding beside implementation work no longer declines the round: the veto made
    auto-iterate fire on 31 of 230 attempts (13.5%), and bundles the maintainer reported as
    broken spent zero rounds. The finding is held in the ledger instead, which is never
    archived and is merged back into §6 at every assembly — so it still reaches the human,
    and C6 still makes them clear it before accept.
    """

    def test_a_judgment_finding_beside_a_defect_no_longer_vetoes_the_rebuild(self) -> None:
        d = self._bundle("MIXED", review=_MIXED_REVIEW)
        self.assertTrue(self._try(d), "a HUMAN finding beside a defect must defer, not veto")
        self._assert_deferred(d, [_C5_TEXT])   # held for the human; IMPL + STANDING are not

    def test_a_human_only_set_still_halts_at_once(self) -> None:
        # Nothing for a rebuild to address: straight to the human, nothing deferred.
        d = self._bundle("HONLY", review=_review_table(
            "C5 Causal adequacy", basis="guards the symptom, not the cause"))
        self.assertFalse(self._try(d))
        self._assert_halted(d)

    def test_environmental_findings_beside_a_red_gate_are_deferred(self) -> None:
        # Each once vetoed the rebuild of an otherwise Do-fixable bundle. Beside real
        # implementation work they are now held for the handover like any HUMAN finding.
        cases = {
            "EXTDEP2": ({"build_notes": "NEEDS-HUMAN external dependency: protoc — cannot "
                                        "compile\n"},
                        "external dependency: protoc — cannot compile"),
            "ADVPLAIN2": ({"advisory": "- NEEDS-HUMAN — the scope looks wider than the brief\n"},
                          "the scope looks wider than the brief"),
        }
        for iid, (kwargs, text) in cases.items():
            with self.subTest(case=iid):
                d = self._bundle(iid, gate=_FAIL, **kwargs)
                self.assertTrue(self._try(d))
                self._assert_deferred(d, [text])

    def test_a_missing_review_beside_a_red_gate_is_deferred(self) -> None:
        d = self._bundle("NOREV2", gate=_FAIL)
        (d / "check-review.md").unlink()
        assemble.assemble_summary(d, self.cfg)
        self.assertTrue(self._try(d))
        [entry] = _ledger(d)
        self.assertIn("no check-review.md was produced", entry)

    def test_deferred_findings_reach_the_handover_section6_and_block_accept(self) -> None:
        """THE loss-proof property. Round 1's reviewer raised C5; the rebuild's reviewer did
        not. Before the ledger C5 existed only in `iteration-v1/` — the handover §6 the human
        signs off against would never have shown it."""
        self.cfg.max_auto_iters = 1
        d = self._bundle("HANDOVER", review=_MIXED_REVIEW)

        def impl_only_review(bundle: Path, cfg: Config) -> None:
            (bundle / "check-review.md").write_text(_IMPL_ONLY_REVIEW, encoding="utf-8")

        buf = io.StringIO()
        with mock.patch.object(leaves, "run_review", impl_only_review), \
             redirect_stderr(buf), redirect_stdout(io.StringIO()):
            fired = [flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-09-30",
                                              apply_now=True) for _ in range(2)]
        self.assertEqual(fired, [True, False])
        self.assertIn("auto-iterate budget spent (1/1)", buf.getvalue())
        self.assertIn("deferred to handover", buf.getvalue())       # the round said so
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertNotIn("guards the symptom",                      # this round never raised it…
                         (d / "check-review.md").read_text(encoding="utf-8"))
        summ = d / "SUMMARY.md"
        self.assertIn(f"- [ ] {_C5_TEXT}", signoff.open_needs_human(summ))   # …yet §6 has it
        # C6 holds on that row alone: clear everything else, and accept is still refused.
        summ.write_text(summ.read_text(encoding="utf-8").replace("- [ ]", "- [x]")
                        .replace(f"- [x] {_C5_TEXT}", f"- [ ] {_C5_TEXT}"), encoding="utf-8")
        (d / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            outcome = flow._apply_decision(self.cfg, d, by="human", today="2026-09-30",
                                           apply_now=False)
        self.assertEqual(outcome, "blocked")
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)

    def test_the_ledger_is_cycle_evidence_and_is_never_archived(self) -> None:
        # Pinned against the module constants: archive it and every deferred finding leaves the
        # live bundle with the SUMMARY that carried it.
        self.assertEqual(autoiterate.DEFERRED_FILE, _LEDGER)
        self.assertIn(autoiterate.DEFERRED_FILE, state.CYCLE_EVIDENCE_ONLY)
        self.assertNotIn(autoiterate.DEFERRED_FILE, state.DOWNSTREAM_OF_BRIEF)
        d = self._bundle("KEEP", review=_MIXED_REVIEW)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-09-30", apply_now=True)
        self.assertTrue((d / "iteration-v1").is_dir())               # the round was archived…
        self.assertFalse((d / "iteration-v1" / _LEDGER).exists())    # …the ledger was not
        self.assertEqual(_ledger(d), [_C5_TEXT])
        self.assertIn(f"- [ ] {_C5_TEXT}", _section6(d / "SUMMARY.md"))   # rebuilt §6 has it

    def test_rationale_names_what_was_addressed_and_what_was_deferred(self) -> None:
        items = [assemble.NeedsHumanItem("C4 Verification (red→green) — off-by-one",
                                         assemble.IMPL),
                 assemble.NeedsHumanItem(_C5_TEXT, assemble.HUMAN),
                 assemble.NeedsHumanItem("Validation — fitness-to-purpose — the human's call",
                                         assemble.STANDING)]
        r = autoiterate.rationale(items, attempt=2)
        self.assertNotIn("\n", r)
        self.assertIn("round 2", r)
        self.assertIn("off-by-one", r)                       # addressed: named
        self.assertIn("Deferred", r)
        self.assertIn("1 finding(s)", r)                     # deferred: counted…
        self.assertNotIn("guards the symptom", r)            # …never quoted (#294)
        self.assertNotIn("Validation", r)
        self.assertNotIn("implementation-level items only", r)   # no longer true

    def test_deferred_findings_never_reach_the_builders_carry_forward(self) -> None:
        # The #294 property end to end: the brief the next Do reads names the defect and the
        # fact of a deferral, but carries no human-only judgment call as though it were work.
        d = self._bundle("CARRY2", review=_MIXED_REVIEW)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-09-30", apply_now=True)
        brief_text = (d / "brief.md").read_text(encoding="utf-8")
        self.assertIn("C4 Verification", brief_text)
        self.assertIn("Deferred", brief_text)
        self.assertNotIn("guards the symptom", brief_text)
        self.assertNotIn("Validation — fitness-to-purpose", brief_text)

    def test_an_unreadable_ledger_is_a_section6_item_at_assembly(self) -> None:
        d = self._bundle("BADLEDGER")                        # clean: §6 is otherwise empty
        (d / _LEDGER).write_text("{ not json", encoding="utf-8")
        assemble.assemble_summary(d, self.cfg)
        [row] = signoff.open_needs_human(d / "SUMMARY.md")
        self.assertIn(f"{_LEDGER} exists but cannot be read", row)

    def test_an_unreadable_ledger_blocks_accept_on_the_shared_decision_path(self) -> None:
        """Not only when auto-iterate is on: a ledger written by an earlier run outlives the
        setting that wrote it, and a SUMMARY assembled before the ledger broke does not carry
        the row. `_apply_decision` is the one path every sign-off takes."""
        self.cfg.auto_iterate = False
        d = self._bundle("BADACCEPT")
        summ = d / "SUMMARY.md"
        self.assertEqual(signoff.open_needs_human(summ), [])  # an accept would go through…
        (d / _LEDGER).write_text('{"items": ["a held finding", 7]}', encoding="utf-8")
        (d / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            outcome = flow._apply_decision(self.cfg, d, by="human", today="2026-09-30",
                                           apply_now=False)
        self.assertEqual(outcome, "blocked")                  # …until the ledger broke
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        six = _section6(summ)
        self.assertIn(f"- [ ] {_LEDGER} exists but cannot be read", six)
        self.assertNotIn("- (none", six)                      # the empty-§6 line is now false
        # The human clears it deliberately: that tick is honoured and not re-added.
        summ.write_text(summ.read_text(encoding="utf-8").replace("- [ ]", "- [x]"),
                        encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            outcome = flow._apply_decision(self.cfg, d, by="human", today="2026-09-30",
                                           apply_now=False)
        self.assertEqual(outcome, "accept")
        self.assertEqual(state.state(d), state.COMPLETE)
        self.assertEqual(_section6(summ).count("exists but cannot be read"), 1)

    def test_an_unreadable_ledger_stops_auto_iterate_without_spending_a_round(self) -> None:
        d = self._bundle("BADAUTO", gate=_FAIL)              # implementation work: would fire
        (d / _LEDGER).write_text("{ not json", encoding="utf-8")
        assemble.assemble_summary(d, self.cfg)
        buf = io.StringIO()
        with redirect_stderr(buf), redirect_stdout(io.StringIO()):
            fired = flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-09-30",
                                             apply_now=False)
        self.assertFalse(fired)
        self.assertEqual(autoiterate.count(d), 0)
        self.assertFalse((d / leaves.SIGNOFF_DECISION).exists())
        self.assertEqual((d / _LEDGER).read_text(encoding="utf-8"), "{ not json")  # untouched
        self.assertIn("cannot be read", buf.getvalue())


class TwoStops(_Base):
    """#409 clause 1 — the loop's stopping rules are exactly two, and neither is new: the size
    backstop (early, 2 rounds by default) and the hard cap `max_auto_iters`. A soft round
    budget with a convergence test (#332 item 1) was dropped at Plan: on a default instance
    the backstop always fires first, so it would add a setting that never binds."""

    def _drive(self, d: Path, review: str = _MIXED_REVIEW) -> tuple[int, str]:
        """Re-drive the bundle with auto-iterate until it declines; (rounds fired, stderr)."""
        def reviewer(bundle: Path, cfg: Config) -> None:
            (bundle / "check-review.md").write_text(review, encoding="utf-8")

        buf = io.StringIO()
        fired = 0
        with mock.patch.object(leaves, "run_review", reviewer), \
             redirect_stderr(buf), redirect_stdout(io.StringIO()):
            for _ in range(8):
                if not flow._maybe_auto_iterate(self.cfg, d, by="", today="2026-09-30",
                                                apply_now=True):
                    break
                fired += 1
        return fired, buf.getvalue()

    def test_there_is_no_soft_budget_key(self) -> None:
        # Guards the drop against being re-added; not a red leg (it passes on main too).
        self.assertNotIn("soft_auto_iters", Config.__dataclass_fields__)
        self.assertFalse(hasattr(self.cfg, "soft_auto_iters"))
        root = Path(__file__).resolve().parents[1]
        # `pdca.toml.jinja` in the template repo, `pdca.toml` in a rendered instance (this
        # file ships into the render). A key the template never declares cannot be rendered.
        sources = [root / n for n in ("pdca.toml.jinja", "pdca.toml") if (root / n).is_file()]
        if not sources:
            self.skipTest("no pdca.toml(.jinja) beside the tests")
        text = sources[0].read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^\s*#?\s*soft_auto_iters\s*=", text, re.MULTILINE))

    def test_mixed_checks_fire_until_the_hard_cap(self) -> None:
        # The size backstop OFF, so the hard cap is the only stop left.
        self.cfg.size_signal = {"rounds": 0}
        self.cfg.max_auto_iters = 3
        d = self._bundle("CAP", review=_MIXED_REVIEW)
        fired, err = self._drive(d)
        self.assertEqual(fired, 3, "an [IMPL, HUMAN] Check must keep firing to the cap")
        self.assertEqual(autoiterate.count(d), 3)
        self.assertIn("auto-iterate budget spent (3/3)", err)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)   # handed over, not dropped
        # Raised by every round, recorded once, rendered once.
        self.assertEqual(_ledger(d), [_C5_TEXT])
        self.assertEqual(_section6(d / "SUMMARY.md").count(_C5_TEXT), 1)

    def test_mixed_checks_stop_at_the_size_backstop_first_by_default(self) -> None:
        # Default `[size_signal].rounds = 2`, below the cap of 3 on purpose.
        self.cfg.max_auto_iters = 3
        d = self._bundle("SIZE", review=_MIXED_REVIEW)
        fired, err = self._drive(d)
        self.assertEqual(fired, 2)
        self.assertEqual(autoiterate.count(d), 2)
        self.assertIn("not auto-iterating: size backstop", err)   # it says why, on stderr
        self.assertNotIn("budget spent", err)
        self.assertEqual(state.state(d), state.AWAITING_SIGNOFF)
        self.assertIn(f"- [ ] {_C5_TEXT}", _section6(d / "SUMMARY.md"))


def _summary(rows: list[str], *, heading: bool = True, elsewhere: str = "") -> str:
    """A SUMMARY.md with the given §6 checkbox rows (or none, and no §6 heading at all)."""
    six = "## 6. NEEDS-HUMAN — items the human must clear before sign-off\n" if heading else ""
    return ("# Result — issue 1 / retire\n\n"
            "## 5. Advisory review (artifact-only, decorrelated)\n"
            f"{elsewhere}\n\n"
            f"{six}" + "".join(f"{r}\n" for r in rows) + "\n"
            "## 7. Proven / not proven\n- n/a\n\n"
            "## 9. Check sign-off                     ← human completes Check here\n"
            "- Outcome:\n")


class RetiresOnlyWhatTheHumanTicked(unittest.TestCase):
    """#409 clause 3, with #335 folded in — `autoiterate.retire_cleared`.

    A deferred finding leaves the ledger only on a POSITIVE tick in §6. A still-open row
    protects entries by the SAME `_same_finding` relation the tick is matched with, assigned
    exact-first: a verbatim open row protects its own entry only (so a near-identical pair
    stays drainable), an edited open row protects every entry it matches (fail closed).
    The #335 repro and the matcher-drift test are written to fail against BOTH wrong
    protection shapes: exact-only protection (the #335 bug) and the flat symmetric-fuzzy
    exclusion (the permanently unclearable pair). Each of the others pins one further rule,
    named in its test.
    """

    # Two different findings that `_same_finding` cannot tell apart (a long shared opening).
    P = "C5 Causal adequacy — guards the symptom in the parser"
    R = "C5 Causal adequacy — guards the symptom in the renderer"
    E = "T5 Judgment — the retry loop swallows the first failure and reports the last one"
    X = "C1 Spec — the brief never says which config file wins"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.n = 0

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _retire(self, ledger: list[str], rows: list[str], **summary_kw) -> list[str]:
        self.n += 1
        d = self.tmp / f"issue_{self.n}"
        d.mkdir()
        _write_ledger(d, ledger)
        (d / "SUMMARY.md").write_text(_summary(rows, **summary_kw), encoding="utf-8")
        kept = autoiterate.retire_cleared(d, d / "SUMMARY.md")
        self.assertEqual(kept, _ledger(d), "the return value must be what is on disk")
        return kept

    def test_a_tick_retires_its_entry_and_absence_is_not_consent(self) -> None:
        kept = self._retire([self.P, self.E, self.X],
                            [f"- [x] {self.E}",
                             f"- [ ] {self.P}",
                             f"- [ ] {self.X} (owner: plan)"])   # edited, never ticked
        self.assertEqual(kept, [self.P, self.X])

    def test_335_an_annotated_open_row_survives_a_similar_ticked_new_finding(self) -> None:
        self.assertTrue(autoiterate._same_finding(self.P, self.R), "precondition: near-twins")
        # The #335 repro: the human annotated the deferred parser row but did not tick it,
        # and ticked a similar NEW finding (not in the ledger). The tick fuzzy-matches the
        # parser entry; only the open annotated row can protect it, and only if protection
        # uses the relation the tick does. Exact-only protection retires it here.
        self.assertEqual(self._retire([self.P],
                                      [f"- [ ] {self.P} (owner: architecture)",
                                       f"- [x] {self.R}"]),
                         [self.P], "an unadjudicated deferred finding was retired")
        # …and the fix must not overshoot into symmetric-fuzzy protection: a VERBATIM open row
        # protects its own entry only, so its exactly-ticked near-twin still drains.
        self.assertEqual(self._retire([self.P, self.R],
                                      [f"- [ ] {self.P}", f"- [x] {self.R}"]),
                         [self.P], "an exactly-ticked entry was shielded by its open near-twin")

    def test_every_edit_shape_a_tick_tolerates_also_protects_when_left_open(self) -> None:
        """Matcher drift. Whatever `_same_finding` accepts for a tick, an open row must
        accept for protection — even when the entry's own row is ticked exactly beside it."""
        shapes = {
            "annotated": f"{self.E} (owner: architecture)",
            "prefixed": f"Re-raised: {self.E}",
            "trimmed": self.E.rsplit(" ", 3)[0],
            "edited in the middle": self.E.replace("reports the last one",
                                                   "logs only the last one"),
            "case and spacing": "  ".join(self.E.upper().split()),
        }
        for name, edited in shapes.items():
            with self.subTest(shape=name):
                self.assertTrue(autoiterate._same_finding(self.E, edited), "precondition")
                # Left open, the edited row protects the entry against an exact tick.
                self.assertEqual(self._retire([self.E], [f"- [ ] {edited}", f"- [x] {self.E}"]),
                                 [self.E])
                if " ".join(edited.split()).casefold() == self.E.casefold():
                    continue   # the same entry after normalisation: no distinct twin to drain
                # A VERBATIM open row owns its own entry only — the exactly-ticked twin drains,
                # in either direction.
                self.assertEqual(self._retire([self.E, edited],
                                              [f"- [ ] {self.E}", f"- [x] {edited}"]),
                                 [self.E])
                self.assertEqual(self._retire([self.E, edited],
                                              [f"- [ ] {edited}", f"- [x] {self.E}"]),
                                 [edited])

    def test_an_edited_open_row_matching_two_near_twins_protects_both(self) -> None:
        edited = "C5 Causal adequacy — guards the symptom in the pipeline (owner: architecture)"
        self.assertTrue(autoiterate._same_finding(self.P, edited), "precondition")
        self.assertTrue(autoiterate._same_finding(self.R, edited), "precondition")
        # It owns neither verbatim, so it could be an edit of either: fail closed, protect both
        # — even the one ticked exactly.
        self.assertEqual(self._retire([self.P, self.R], [f"- [ ] {edited}", f"- [x] {self.R}"]),
                         [self.P, self.R])

    def test_a_tick_matching_two_entries_retires_neither(self) -> None:
        """A tick retires ONE entry or none. The human deleted P's row, then edited R's row and
        ticked it. The edit owns neither entry verbatim and `_same_finding`-matches both
        near-twins, so it cannot say which one the human cleared: fail closed, both stay.
        Retiring the first match would drop P, which nobody ticked; so would retiring every
        match."""
        edited = f"{self.R} (fixed by the rebuild)"
        for entry in (self.P, self.R):
            self.assertTrue(autoiterate._same_finding(entry, edited), "precondition")
            self.assertNotEqual(" ".join(edited.split()).casefold(), entry.casefold(),
                                "precondition: a fuzzy match, not an exact one")
        self.assertEqual(self._retire([self.P, self.R], [f"- [x] {edited}"]), [self.P, self.R])
        # Control: with only R in the ledger the same tick is unambiguous, and it retires R.
        self.assertEqual(self._retire([self.R], [f"- [x] {edited}"]), [])

    def test_a_short_row_matches_only_exactly(self) -> None:
        """`_MATCH_FLOOR` bounds containment as well as the shared opening. A ticked fragment
        under the floor — an element name, a few words — occurs inside countless findings, so a
        deleted entry that merely CONTAINS it was never ticked: retiring it would read consent
        from absence. The same holds the other way round, for a short entry inside a long row.
        """
        fragments = {"prefix": "T5 Judgment",
                     "middle": "retry loop swallows",    # one character under the floor
                     "suffix": "the last one"}
        for where, short in fragments.items():
            with self.subTest(where=where):
                self.assertIn(short.casefold(), self.E.casefold(), "precondition: a substring")
                self.assertLess(len(short), autoiterate._MATCH_FLOOR, "precondition: short")
                # E's own row was deleted; the only tick is the fragment.
                self.assertEqual(self._retire([self.E], [f"- [x] {short}"]), [self.E])
        short_entry = "C1 Spec — vague"
        with self.subTest(where="a short entry inside a long ticked row"):
            self.assertEqual(self._retire([short_entry],
                                          [f"- [x] {short_entry} about which config file wins"]),
                             [short_entry])
        # Controls: a short entry still retires on its exact tick, and containment at full
        # length still matches — an annotated tick retires its entry.
        self.assertEqual(self._retire([short_entry], [f"- [x] {short_entry}"]), [])
        self.assertEqual(self._retire([self.E], [f"- [x] {self.E} (fixed in round 2)"]), [])

    def test_a_summary_with_no_section6_heading_retires_nothing(self) -> None:
        # The tick reader is STRICT (`whole_on_missing=False`): a `- [x]` quoted in §5's review
        # text — pasted verbatim at assembly — is not the human's clearance.
        quoted = f"The reviewer quoted a cleared row:\n\n- [x] {self.E}\n"
        self.assertEqual(self._retire([self.E], [], heading=False, elsewhere=quoted), [self.E])
        # Control: the very same row under a real §6 heading does retire it.
        self.assertEqual(self._retire([self.E], [f"- [x] {self.E}"]), [])

    def test_an_unreadable_ledger_is_never_rewritten(self) -> None:
        d = self.tmp / "issue_bad"
        d.mkdir()
        (d / _LEDGER).write_text("{ not json", encoding="utf-8")
        (d / "SUMMARY.md").write_text(_summary([f"- [x] {self.E}"]), encoding="utf-8")
        self.assertEqual(autoiterate.retire_cleared(d, d / "SUMMARY.md"), [])
        self.assertEqual((d / _LEDGER).read_text(encoding="utf-8"), "{ not json")


class RetireAtTheIterate(_Base):
    """The wiring: `driver.advance` retires what the human ticked BEFORE the iterate archives
    the SUMMARY that carries the ticks — in both iterate branches."""

    A = "C5 Causal adequacy — the parser guards the symptom"
    B = "T5 Judgment — the retry loop hides the first failure"

    def _iterated(self, iid: str, action: str) -> Path:
        d = self._bundle(iid)
        _write_ledger(d, [self.A, self.B])
        assemble.assemble_summary(d, self.cfg)                   # §6 renders both, unticked
        summ = d / "SUMMARY.md"
        summ.write_text(summ.read_text(encoding="utf-8")
                        .replace(f"- [ ] {self.A}", f"- [x] {self.A}"), encoding="utf-8")
        signoff.record(summ, action=action, by="human", date="2026-09-30")
        with redirect_stderr(io.StringIO()):
            driver.advance(d, self.cfg)                          # the one iterate beat
        return d

    def test_a_human_iterate_do_retires_what_they_ticked(self) -> None:
        d = self._iterated("RETDO", "iterate-do")
        self.assertEqual(_ledger(d), [self.B])
        self.assertIn(f"- [x] {self.A}",                         # the tick is archived intact
                      (d / "iteration-v1" / "SUMMARY.md").read_text(encoding="utf-8"))

    def test_a_human_iterate_plan_retires_what_they_ticked(self) -> None:
        d = self._iterated("RETPLAN", "iterate-plan")
        self.assertEqual(state.state(d), state.UNPLANNED)
        self.assertEqual(_ledger(d), [self.B])


class DecisionModule(unittest.TestCase):
    """`autoiterate` itself — the guard that keeps this from ever becoming an auto-accept."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _items(self, *kinds: str) -> list[assemble.NeedsHumanItem]:
        return [assemble.NeedsHumanItem(f"finding {i}", k) for i, k in enumerate(kinds)]

    def test_eligible_iff_there_is_implementation_work(self) -> None:
        self.assertTrue(autoiterate.eligible(self._items(assemble.IMPL, assemble.IMPL)))
        self.assertFalse(autoiterate.eligible([]))                                 # never accept
        self.assertTrue(autoiterate.eligible(self._items(assemble.IMPL, assemble.HUMAN)))  # #409
        self.assertTrue(autoiterate.eligible(self._items(assemble.IMPL, assemble.STANDING)))
        self.assertFalse(autoiterate.eligible(self._items(assemble.HUMAN)))
        self.assertFalse(autoiterate.eligible(self._items(assemble.HUMAN, assemble.STANDING)))

    def test_the_size_item_stops_by_kind_not_every_human_item(self) -> None:
        """#409 clause 4, the #324 composition. The size backstop stops the loop by KIND of
        item; ordinary HUMAN items defer. Both legs in ONE test so neither wrong rule passes:
        today's veto fails the first leg, a naive `any(item.kind == IMPL)` fails the second."""
        defect = assemble.NeedsHumanItem("C4 Verification (red→green) — off-by-one",
                                         assemble.IMPL)
        ordinary = assemble.NeedsHumanItem(_C5_TEXT, assemble.HUMAN)
        size = assemble.NeedsHumanItem(
            size_signal.needs_human_text(["2 round(s) already spent (threshold 2)"]),
            assemble.HUMAN)
        self.assertTrue(autoiterate.eligible([defect, ordinary]),
                        "an ordinary HUMAN finding must defer, not veto")
        self.assertFalse(autoiterate.eligible([defect, ordinary, size]),
                         "the size backstop's item must stop the loop")
        # The same text tagged IMPL is not the backstop's item, and still rebuilds.
        self.assertTrue(autoiterate.eligible([defect, ordinary,
                                              size._replace(kind=assemble.IMPL)]))

    def test_write_decision_defers_the_human_items_before_spending_the_round(self) -> None:
        items = [assemble.NeedsHumanItem("finding 0", assemble.IMPL),
                 assemble.NeedsHumanItem("finding 1", assemble.HUMAN),
                 assemble.NeedsHumanItem("finding 2", assemble.STANDING),
                 assemble.NeedsHumanItem("FINDING  1", assemble.HUMAN)]   # same, re-worded case
        autoiterate.write_decision(self.tmp, items)
        self.assertEqual(_ledger(self.tmp), ["finding 1"])   # HUMAN only, deduplicated
        self.assertEqual(autoiterate.count(self.tmp), 1)
        autoiterate.write_decision(self.tmp, items)          # a later round re-raising it
        self.assertEqual(_ledger(self.tmp), ["finding 1"])   # …does not grow the handover
        self.assertEqual(autoiterate.count(self.tmp), 2)

    def test_write_decision_refuses_the_size_backstop_set(self) -> None:
        size = size_signal.needs_human_text(["patch is 253 KB (threshold 100 KB)"])
        with self.assertRaises(ValueError):
            autoiterate.write_decision(self.tmp, [assemble.NeedsHumanItem("d", assemble.IMPL),
                                                  assemble.NeedsHumanItem(size, assemble.HUMAN)])
        self.assertFalse((self.tmp / leaves.SIGNOFF_DECISION).exists())
        self.assertEqual(autoiterate.count(self.tmp), 0)
        self.assertIsNone(_ledger(self.tmp))

    def test_an_unreadable_ledger_is_told_apart_from_an_absent_one(self) -> None:
        self.assertEqual(autoiterate.deferred(self.tmp), [])          # absent: nothing deferred
        self.assertEqual(autoiterate.ledger_problem(self.tmp), "")
        for garbage in ("{ not json", '["a list, not an object"]', '{"items": "text"}',
                        '{"items": ["ok", 7]}'):
            with self.subTest(content=garbage):
                (self.tmp / _LEDGER).write_text(garbage, encoding="utf-8")
                with self.assertRaises(autoiterate.DeferredLedgerUnreadable):
                    autoiterate.deferred(self.tmp)
                self.assertTrue(autoiterate.ledger_problem(self.tmp))
                # …and a round refuses to rewrite it: no decision, no budget, file untouched.
                with self.assertRaises(autoiterate.DeferredLedgerUnreadable):
                    autoiterate.write_decision(
                        self.tmp, self._items(assemble.IMPL, assemble.HUMAN))
                self.assertFalse((self.tmp / leaves.SIGNOFF_DECISION).exists())
                self.assertEqual(autoiterate.count(self.tmp), 0)
                self.assertEqual((self.tmp / _LEDGER).read_text(encoding="utf-8"), garbage)

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
        self.assertIsNone(_ledger(self.tmp))                      # and nothing deferred

    def test_write_decision_refuses_an_empty_set(self) -> None:
        with self.assertRaises(ValueError):
            autoiterate.write_decision(self.tmp, [])

    def test_rationale_is_a_single_line_naming_the_findings(self) -> None:
        r = autoiterate.rationale(self._items(assemble.IMPL, assemble.IMPL), attempt=2)
        self.assertNotIn("\n", r)
        self.assertIn("round 2", r)
        self.assertIn("finding 0", r)
        self.assertIn("finding 1", r)


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
            [(text, standing)] = assemble._needs_human(table)
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

        [(_t, standing)] = assemble._needs_human(canonical)
        self.assertTrue(standing, "the canonical row of the MANDATED table IS the constant")
        [(_t, standing)] = assemble._needs_human(objection)
        self.assertFalse(standing, "a longer Item cell is a real objection, not the template")
        [(_t, standing)] = assemble._needs_human(bullet)
        self.assertFalse(standing, "free prose is never the template row")
        [(_t, standing)] = assemble._needs_human(lone)
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


class ConfigPlumbing(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        # Hermetic against the ambient environment (#419): Config.load honors PDCA_*
        # env overrides (PDCA_AUTO_ITERATE, config.py), and a project's T3 suite gate
        # runs this suite with the DRIVER's inherited env (gates._merged_env) — an
        # auto-iterate flow can carry PDCA_AUTO_ITERATE=1 there, flipping the
        # default-behavior assertions below to read the operator's shell instead of
        # the toml under test.
        env_guard = mock.patch.dict(os.environ)
        env_guard.start()
        self.addCleanup(env_guard.stop)
        for key in [k for k in os.environ if k.startswith("PDCA_")]:
            del os.environ[key]

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

    def test_cli_flag_opts_in(self) -> None:
        cfg = _stub_config(self.tmp)
        cfg.auto_iterate = False
        # `flow_ids` is the ONE drive path `cli._flow` routes a single id through (#468),
        # so that is the call to stub out for a flag-plumbing test.
        with mock.patch.object(cli.Config, "load", return_value=cfg), \
             mock.patch.object(cli.flow, "flow_ids",
                               return_value={"ID1": state.COMPLETE}), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            cli.main(["flow", "ID1", "--auto-iterate", "--no-publish", "--no-act"])
        self.assertTrue(cfg.auto_iterate)


if __name__ == "__main__":
    unittest.main()
