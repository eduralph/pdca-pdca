# PR description

## Summary
**User impact:** If a Check run is interrupted at the wrong moment — Ctrl-C, an
out-of-memory kill, a dropped session — the bundle comes back in a state it can never
repair on its own: the expensive gate results are saved, but the review silently never
happens. The summary just says the review is missing, no command will run the reviewer
again for that round, and the only workaround is deleting the saved gate results and
re-paying the whole gate run (hours, in the incident that surfaced this). The record
also reads exactly like a reviewer that ran and crashed, so you cannot even tell which
of the two happened.

This PR makes the driver notice a review that never ran and simply run it on the next
advance, keeping the already-paid gate results untouched.

Reported in [#369](https://github.com/eduralph/pdca-harness/issues/369).

## What to look at
`_resume_interrupted_check` in `template/src/pdca_harness/driver.py` — the recovery
step the CHECKED dispatch now runs before assembling — and the new `only_missing` mode
of `run_advisory_leaves` in `template/src/pdca_harness/leaves.py`. To reproduce the
trap: create a bundle directory with a `brief.md`, a `patch.diff`, and a valid
`check-gates.json`, but no `check-review.md` and no `check-review.error.log` (exactly
the state an interrupted run leaves behind). Advancing it on `main` never invokes the
reviewer and produces a `SUMMARY.md` with the missing-review placeholder; with this
change the reviewer runs first and the gate record is preserved.
`template/tests/test_check_resume.py` automates exactly this.

## Root cause
`check-gates.json` is itself the CHECKED marker
(`template/src/pdca_harness/state.py:213-216`), but the BUILT branch runs gates →
reviewer → advisory leaves as one indivisible step
(`template/src/pdca_harness/driver.py:104-115`) while the CHECKED dispatch went
straight to `assemble.assemble_summary` (`driver.py:116-118`). Any death in the window
between the gate write and a model leaf therefore landed the bundle in CHECKED with
that leaf never run — and no code path could ever reach it again for that round.

## Fix
Before assembling, the CHECKED dispatch calls `_resume_interrupted_check`. It tells
"never ran" from "ran and failed" with the engine's existing failed-leaf discriminator
(#138): a leaf that ran and failed wrote its error log
(`template/src/pdca_harness/leaves.py:306-324` — cleared at the start of a run,
written when retries exhaust), so artifact and error log both absent means the leaf
never ran and is safe to run now. A never-ran reviewer is re-run
(`leaves.review_never_ran`), advisory leaves via `run_advisory_leaves(...,
only_missing=True)` — with the advisory-selection policy (#200) re-applied first, so
an unselected vendor-complement leaf's absent artifact is never read as "missing". The
two no-model branches (close disposition, dependency halt) get their deterministic
review stand-in note rewritten instead; a model reviewer is never invoked there. A
leaf that ran and failed is left alone — today's behaviour. Finally,
`_missing_review_text` (`template/src/pdca_harness/assemble.py:394-401`) splits into
distinct NEVER-RAN and RAN-AND-FAILED wordings, and the error-log filename becomes the
shared constant `state.REVIEW_ERROR_LOG` so the writer, the resume check, and the
wording stay on one spelling.

## Verification
- **Claim:** a never-ran reviewer/advisory leaf is recovered on the next advance,
  before summary assembly, with the paid gate record preserved byte-for-byte.
  **Checked:** `template/src/pdca_harness/driver.py:116-118` on `main` — the CHECKED
  dispatch reached only `assemble_summary`, never a leaf.
  **Test:** `template/tests/test_check_resume.py` — `NeverRanReviewerIsRecovered`
  asserts the recovered review is consumed by `SUMMARY.md` and `check-gates.json` is
  byte-identical.
- **Claim:** a leaf that ran and failed is NOT re-run.
  **Checked:** `template/src/pdca_harness/leaves.py:306-324` on `main` — the error log
  is written on failure and cleared on success, so its presence proves the leaf ran.
  **Test:** `RanAndFailedIsNotRerun` (reviewer and advisory; fixtures carry the real
  error-log artifact).
- **Claim:** §6 distinguishes a skipped reviewer from a failed one.
  **Checked:** `template/src/pdca_harness/assemble.py:394-401` on `main` — one wording
  covered both cases.
  **Test:** `Section6DistinguishesSkippedFromFailed`.
- **Claim:** an uninterrupted cycle is unchanged, including under vendor-complement
  advisory selection.
  **Test:** `UninterruptedCycleIsUntouched` — sentinel artifacts survive advance
  byte-identical, and an unselected leaf is never promoted by the resume.
- **Red→green:** with the production hunks reverted, all 10 tests in
  `template/tests/test_check_resume.py` fail deterministically; with the patch, 10/10
  pass. Full offline driver suite: 1463 tests OK (2 skipped); root template-repo suite
  (render + update-compat): 7 tests OK.

Fixes #369
