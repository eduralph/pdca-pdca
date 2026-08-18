# Advisory code review — correctness + reuse/simplification (issue #64 lens)

Scope: this patch only (attempt-owned leaf records/harvests, #506), grounded on
`$PDCA_TARGET/template/src/pdca_harness/{leaves,driver,assemble,state}.py` and the new
`template/tests/test_attempt_ownership.py`. This is round 5; four prior sign-off rounds
already found and closed real defects (non-atomic flush, withdraw-before-persist kill
window, unsettled error logs left beside filed placeholders, unbounded-residue reads,
undecodable-log crashes, false "retries did not recover" prose, an untested second
recovery discriminator). I re-walked the mechanism fresh rather than trusting that
history, and traced every kill window, the defang/whole-last-line match, and all three
harvest sites end to end against the current target source.

## Findings

- `leaves.py:745-746` — minor redundant write, not a bug. On a successful attempt that
  produced no artifact over a run with a dead predecessor (`records and artifact is not
  None and not artifact.exists()`), the wrapper calls `_write_attempt_records(error_log,
  records, in_flight=True)` again. To reach this branch the loop must have already
  continued past a failed attempt whose own flush used the *same* `records` list and the
  *same* `in_flight=True` and whose `recorded` return value was `True` (required for the
  retry to have been allowed at all, `leaves.py:773`) — so this second write reproduces
  byte-identical content already durably on disk. It's correctness-safe (the call's
  return value is intentionally unchecked, and if this redundant write fails the
  already-landed state from the prior flush stands unchanged), just a needless
  temp-file + `os.replace` round trip on the "retried, came back alive, wrote nothing"
  path. Worth a comment noting it's deliberate belt-and-suspenders (or dropping it), but
  not worth gating on.

- No new correctness bugs found in the crash-atomic flush (`_atomic_write_text`,
  `leaves.py:804`), the persist-before-unlink ordering in the failed-attempt branch
  (`leaves.py:759-773`, closing round 3's withdraw-before-persist window), the
  `_defang_in_flight` neutralisation applied to both quoted channels (the residue text at
  `leaves.py:1035` and the stderr tail *and* its no-output fallback at `leaves.py:1074`,
  closing round 4's optional finding), the bounded/degrading residue read
  (`_residue_record`, `leaves.py:1024-1035`), or the three harvest sites' settle/no-settle
  symmetry (`leaves.py:2871-2897`, `:3248-3258`, `:3552-3563`) — all three now settle on
  both the `err is not None` branch and the empty-success branch, never on the
  artifact-harvested branch, matching the documented contract.

- Reuse note, not new to this round: the three harvest sites remain near-verbatim
  duplicates of each other (settle ordering, `_empty_run_class`/`error_log=` wiring, the
  `# see the reviewer` cross-references acknowledging the copy). This was already named
  by the iteration-3 carry-forward as a legitimate `_harvest_leaf`-helper Act candidate
  and deliberately deferred ("closing item 2 at three sites by hand is smaller than the
  refactor, and this patch is already oversized") — re-flagging only for completeness,
  not as a fresh finding.

- Test coverage: the new file drives all three harvest sites (`BothAdvisoryHarvestsAre
  AttemptAwareToo` parametrizes over `_run_advisory_sandboxed` and
  `_run_plan_advisory_sandboxed`, closing round 1/4's twin-blindness gap) and both #369
  recovery discriminators (`AnInterruptedLeafIsRecoveredNotRetired` for
  `review_never_ran`, `AnInterruptedAdvisoryLeafIsRecoveredToo` for
  `run_advisory_leaves(only_missing=True)`, closing round 4's untested-twin finding). I
  did not find a case that exercises production without also asserting something
  meaningful — no "test that doesn't actually exercise the fix" gap.

- C4 evidence (`gate-logs/C4-verify.log`) independently confirms the red leg is a real
  regression on the base (23 failures + 4 errors reverting only the production hunks) and
  the green leg is 31/31; `gate-logs/T3-suite.log` shows the full 1789-test driver suite
  green. No gate-adjudication concerns.

## Verdict

Clean on both lenses at this round. The one item above is a harmless, non-blocking
efficiency nit — not a correctness defect and not something requiring human
adjudication.
