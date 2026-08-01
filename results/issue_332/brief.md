# Design proposal — issue 332 / autoiterate-soft-hard-defer

> Plan artifact (design-proposal form). Do reads ONLY this file.
> **Folds in #335** (per the maintainer's triage on both issues: the retirement defect
> must be fixed *inside this change*, not after it — the instance implementation shipped
> with it, and a faithful port reproduces it).

- **Slug:** autoiterate-soft-hard-defer
- **Kind:** enhancement (design proposal)
- **Goal:** auto-iterate fires on 13.5% of eligible-checked attempts (31/230 measured;
  199 vetoed) because builder-fixability is inferred from the taxonomy cell instead of
  stated by the reviewer, and because one HUMAN finding vetoes the rebuild outright.
  Deliver: soft/hard round budgets, a reviewer-stated `[impl]` tag honoured by the
  classifier, deferred (not blocking) human findings with a loss-proof ledger, and the
  Validation-row match fixed for its three observed forms.
- **Success criterion:** (1) with `soft_auto_iters`=3, `max_auto_iters`=5, the worked
  example holds: rounds ≤3 always fire; 3<n≤5 fire only if the IMPL count did not
  increase; n>5 never; `soft_auto_iters` unset defaults to `max_auto_iters` so a
  rendered instance reproduces today's behaviour exactly. (2) A judgment-cell (C5/T5)
  verdict `NEEDS-HUMAN [impl]` is promoted to IMPL only for promotable elements
  (judgment-kind minus V, derived from `gates.canonical_elements()` the way
  `_GATE_ELEMENTS` is at `assemble.py:50`), with STANDING checked before the tag so a
  tagged V row stays STANDING; an untagged bullet still classifies HUMAN (fail-safe
  unchanged); gates-that-could-not-run / declared / unregistered dependencies are never
  promotable. (3) `eligible()` (`autoiterate.py:56`) becomes "≥1 IMPL", with HUMAN
  findings deferred to a ledger kept out of `DOWNSTREAM_OF_BRIEF`, listed in
  `state.CYCLE_EVIDENCE_ONLY`, and merged deduped into §6 at assemble so every deferred
  finding reaches the human at handover under the C6 guard; empty §6 still halts
  (never auto-accept); HUMAN-only sets still halt immediately; `rationale()` states
  what was addressed and what was deferred, and still carries IMPL items only into the
  builder's carry-forward. (4) The STANDING match at `assemble.py:439` accepts all
  three production forms (`Validation — fitness-to-purpose`,
  `V — Validation — fitness-to-purpose`, `Validation -- fitness-to-purpose`) by
  normalizing an optional leading `<element-id> —` prefix and folding ASCII `--`,
  comparison exact *after* normalization; `_REVIEW_PROMPT` and the role prompts are
  aligned in the same pass. (5) **The #335 fold:** ledger retirement uses ONE matching
  predicate on both the selection side and the still-open-in-§6 exclusion side; when a
  ticked row and an open row both match one entry the open row wins; a test asserts the
  two sides cannot drift (both routed through one predicate). All demonstrable by
  C4-verify via the offline driver suite.
- **Falsifiability:** the offline driver suite on this host
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_autoiterate`). RED now,
  per clause: (1) `soft_auto_iters` is unparsed (`config.py:259` has only
  `max_auto_iters`); (2) `[impl]` on a C5/T5 verdict cell is ignored by
  `_classify_finding`/`_needs_human`; (3) a HUMAN item beside IMPL items vetoes in
  `eligible()` (`autoiterate.py:73-74`); (4) the prefix form fails the exact casefolded
  match at `assemble.py:438-439`; (5) `retire_cleared` does not exist upstream — the
  ledger ships with the single-predicate shape from day one.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 331, 369
- **Ordering note:** 331 also reworks the carry-forward channel around
  `driver._carry_forward_into_brief`; 369 also edits the §6 assembly in `assemble.py`
  and the driver's Check sequencing — shared files, different waves. #335 is NOT a
  separate bundle: it is folded here (its defective code exists only downstream).
- **Difficulty:** high
- **Scope:** the five numbered items of the issue plus the #335 fold, exactly as in the
  success criterion; `auto-iterate.json` extended to carry per-round IMPL counts with
  `count()` tolerant of the old shape; `agents/reviewer.md`-family prompts updated in
  step with `_REVIEW_PROMPT` (`leaves.py:1395` — the issue's `:820` is stale) and
  `_advisory_prompt`'s
  "when in doubt, OMIT '[impl]'" (`leaves.py:2001`) replaced by a required
  `[impl]`/`[human]` tag with the untagged→HUMAN fail-safe; tests parameterized over
  the three V-row forms (the existing `test_autoiterate.py` hard-codes the exact form
  at its `_STANDING_ROW`), table-driven round gating, C5/T5-beside-IMPL defers vs
  C5/T5-alone halts, tag-on-C1/C3/V ignored, round-1 HUMAN finding still in §6 at
  handover, and `test_empty_section6_halts_and_never_auto_accepts` passing unchanged.
  / out of scope: routing input-cell defects to `iterate-plan` (the issue's declared
  follow-up — `autoiterate.DECISION` stays the single `iterate-do` token); #334 itself
  (already landed — `CYCLE_EVIDENCE_ONLY` exists in `state.py`; this change only adds
  the new ledger file to it).
- **External dependencies:** none
- **Test file:** template/tests/test_autoiterate.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites verified on main: `autoiterate.eligible` `autoiterate.py:56`,
  `rationale` `:93`, budget file handling `:50,77-91`; `_advisory_prompt` OMIT at
  `leaves.py:2001`; `_GATE_ELEMENTS` `assemble.py:50`, `_V_LABEL` `:64`,
  `_classify_finding` `:128`, `_needs_human` `:396` with the casefolded exact match at
  `:438-439` and the fail-closed dual-STANDING guard at `:445-447`;
  `CYCLE_EVIDENCE_ONLY` in `state.py` (#334, landed).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/autoiterate.py template/src/pdca_harness/assemble.py` —
  #293/#294 history present, none of items 1–5 landed; `soft_auto_iters` absent from
  `config.py`; no `retire_cleared`/`_same_finding` anywhere upstream (confirming #335
  has no upstream code to fix separately). Instance prototype getwyrd/wyrd-pdca#167
  exists downstream only — and carries the #335 bug, which is why the fold is binding.
- **Disposition hint:** new-feature

## Motivation

Two maintainer-reported broken bundles spent zero auto-rounds — vetoed at eligibility,
never bounded by the budget. The measured blockers (untagged advisory bullets 91%,
T5 146/230, C5 66/230) are a taxonomy proxy standing in for a statement the reviewer
could simply make. Deferral + budgets turn the round budget into the actual bound.

## Design

As specified in the issue and criterion. Two carry-forward channels stay distinct: IMPL
→ builder via `_carry_forward_into_brief`; deferred HUMAN → human via ledger + §6. The
#294 property (a human-only judgment call is never handed to Do as a defect) must hold
in `rationale()`'s output.

## Alternatives considered

- Raising `max_auto_iters` alone: does nothing — eligibility, not the budget, is the
  binding constraint (13.5% measured).
- Prefix-matching the V row: rejected by #294 — lets a real objection wear the
  template's clothes; normalize-then-exact instead.

## Impact & compatibility

Defaults reproduce today's behaviour byte-for-byte (`soft_auto_iters` unset ⇒ hard-only;
untagged ⇒ HUMAN). The ledger is additive and archive-exempt by design.

## Open questions

- None blocking; the issue + comments fully specify the shape.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.
