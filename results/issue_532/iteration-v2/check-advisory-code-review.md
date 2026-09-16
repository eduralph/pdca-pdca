# Check — advisory code review (correctness + reuse/simplification lens)

Scope: this diff only (`template/src/pdca_harness/leaves.py` + the two appended test
files). Grounded on `$PDCA_TARGET`'s post-patch `leaves.py`, `state.py`, `progress.py`,
`config.py`, `brief.py`, `driver.py`.

## Verification of the six carry-forward findings from the prior iteration's sign-off

All six are addressed in this diff, and each is now backed by a genuinely red→green test
(confirmed in `gate-logs/C4-verify.log`: green leg 23/23, red leg with production hunks
reverted shows 11 failures + 3 errors across exactly the appended cases):

1. Fail-closed artifact ownership (`leaves.py:828-864`, `_withdraw_residue`) — `ok`
   is `False` when the unlink fails, and `_invoke_leaf_resilient:764`
   (`retry = retry_when(exc) and attempt < attempts and owned`) stops retrying on that
   `False`. `test_ownership_that_cannot_be_enforced_stops_the_retries` exercises it.
2. The #369 trap-door (`leaves.py:780-819`) — `_LEAF_IN_FLIGHT` + `leaf_run_incomplete` +
   `_leaf_ran_and_failed` correctly distinguish "interrupted mid-retry" from "ran and
   gave up" at all three sites that read it (`review_never_ran:2398`,
   `run_advisory_leaves:3106`, and the resume path via `driver._resume_interrupted_check`).
3. Signal-death scope leak (`leaves.py:1947-1963`, `_builder_retryable`) — filters
   `returncode < 0` (SIGKILL, and `progress.TIMEOUT_RC`) out of the retry class, one spawn,
   re-raised, exactly as before #506. #510 is not folded in.
4. Exhausted-retry next action (`leaves.py:2002-2022`) — now asks `state.state(d)`
   (a waterfall) instead of inferring from `patch.diff`'s presence; verified against real
   `state.state` in `test_the_exhausted_report_asks_the_state_machine_not_the_residues_shape`.
5. `_withdraw_residue` no longer renames into the doomed sandbox — the text is folded into
   the bundle-local `error_log`'s record (`leaves.py:836-856`), verified readable afterward
   by `test_the_withdrawn_verdict_is_readable_in_the_bundle_afterwards`.
6. The `residue` list is used, not dropped: `_report_exhausted_do_retries` (`leaves.py:1992-1999`)
   prints it and nothing deletes it; `test_the_exhausted_report_names_every_artifact_the_dead_attempt_left`
   asserts the files still exist afterward. C5 is still vacuous by construction (no *new*
   test file — the brief explicitly directs appending to existing files), but the C4 red/green
   log now makes production-path coverage of the appended cases adjudicable, closing that
   half of finding 6 as well.

## New findings from this pass

- The wiring at all three harvest sites (`_run_review_sandboxed:2798-2824`,
  `_run_advisory_sandboxed:3144-3159`, `run_plan_advisory`'s sandboxed helper
  `:3446-3461`) passes the *same* `Path` object as both `artifact=` to the wrapper and the
  post-call `if out.exists():` / `if produced.exists():` check, so there is no drift between
  what the wrapper owns and what the harvest reads — the shape a fresh reviewer of this
  pattern would specifically want to check for.
- `_do_build_command` (`leaves.py:2108-2119`) mirrors the three peer call sites' `err =
  _invoke_leaf_resilient(...); if err is not None: raise err` shape as directed by the brief,
  and correctly omits `memory_log=` so it's derived by `_memory_log_for(d / BUILD_ERROR_LOG)`
  → `d / "build.memory.jsonl"` (`BUILD_MEMORY_LOG`, `leaves.py:84`) — same file as before,
  confirmed by reading `_memory_log_for` (`leaves.py:363-373`).

- `_write_attempt_records` (`leaves.py:788-801`) swallows `OSError` on the write and just
  prints a warning, for *every* attempt including the final (exhausted) one. If that final
  write fails, the on-disk `error_log` is left holding whatever the *previous* attempt's
  flush wrote — which, if that previous flush happened while a retry was still pending,
  still carries the `_LEAF_IN_FLIGHT` trailer (`leaves.py:785`). `leaf_run_incomplete` /
  `_leaf_ran_and_failed` would then misclassify a leaf that actually *exhausted* its budget
  as merely "interrupted", and the #369 resume path (`review_never_ran`, `only_missing`)
  would re-invoke a leaf whose retries are already spent. This is a narrow edge (requires
  the write to fail specifically on the terminal flush, not an earlier one) and is strictly
  milder than the trap-door it replaces — pre-patch, the single end-of-loop
  `error_log.write_text(...)` had no `try/except` at all, so the same disk fault would have
  raised out of `_invoke_leaf_resilient` uncaught instead of leaving a stale marker. Not
  covered by any of the appended tests. Worth a look, not blocking.

- `_do_residue` (`leaves.py:1966-1972`) says in its docstring that the test file is
  "resolved as `_stub_build` resolves it", but `_stub_build` (`leaves.py:2177-2178`) falls
  back to `Path("test_stub.py")` when the brief names no test file, while `_do_residue` has
  no such fallback (it only lists names `brief.test_files` actually returns). Harmless in
  practice — `_do_residue` only fires on a command-backend retry exhaustion, where
  `_stub_build`'s stub-only fallback is never reached — but the docstring overclaims parity
  with a function whose fallback branch it doesn't share. Cosmetic.

## Reuse / simplification

- No duplicated logic against existing helpers: `_write_attempt_records`,
  `_withdraw_residue`, `leaf_run_incomplete` / `_leaf_ran_and_failed`, and `_has_content`
  are each new, single-purpose, and used at every site that needs the behavior (no
  copy-pasted variant left at the builder vs. the reviewer/advisory/plan-advisory sites).
- `_report_exhausted_do_retries`'s operator-facing prose duplicates some phrasing from
  `_unavailable_classification`'s `_FAIL_TRANSIENT` branch ("transient infra ... safe to
  re-run"). Not worth factoring out — one is a reviewer/advisory §6 placeholder sentence,
  the other an operator stderr narrative naming a state-machine consequence — but flagging
  in case a future edit wants a shared string.

## Overall

No correctness bug in this diff rises to blocking severity; the one item worth a look is
the stale in-flight marker on a failed terminal flush, noted above (not exercised by any
test in this patch, and strictly better than the pre-patch uncaught-write-failure behavior
it replaces).
