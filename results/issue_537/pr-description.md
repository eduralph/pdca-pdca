## Summary
**User impact:** When the building step of a cycle hit a brief outage — a dropped
connection, an overloaded API — the whole build failed at once, with no retry, even though
the review steps already retry the same kind of hiccup. Users lost the time the build had
spent (about 18 minutes and a full round in the reported case) and had to re-run by hand,
where the identical build then succeeded. When a build did fail, the message showed only a
command line and an exit code. It did not say what was left behind, or that a re-run could
go straight to review on a half-written patch.

This PR makes the builder retry these outages the same way the other steps do. It also
makes a failed build say what it left and what a re-run will do next.

Reported in [#537](https://github.com/eduralph/pdca-harness/issues/537).

## What to look at
- The builder now goes through the same retry helper as the reviewer and advisories. A
  failure after the builder did real work is still not retried.
- A retry's prompt carries a short notice: the previous attempt died, and any files it
  finds are unfinished leftovers, not a finished build. The first attempt's prompt is
  unchanged.
- A failed build now prints the files left in the bundle and the true next step, e.g.
  "the bundle now reads BUILT, so a plain re-run runs CHECK on that unfinished patch.diff,
  not Do".
- To try it offline, from `template/`:
  `PYTHONPATH=src python3 -m unittest tests.test_builder_retry -v`. The stub "builder" is a
  Python one-liner that dies the way a dropped connection does, so no vendor CLI, key or
  network is needed.

## Root cause
`_do_build_command` spawned the builder with plain `_invoke`, while the reviewer, the
advisory and the plan advisory all use `_invoke_leaf_resilient` (added in #138 and never
extended to the builder). On failure, `do_build` wrote one record and re-raised, with no
word on the residue. A bundle holding `patch.diff` reads BUILT, so the driver's next run
goes to Check, not Do.

## Fix
All in `template/src/pdca_harness/leaves.py`. Line numbers are post-patch; the file is
the same on `main` (`59a836d`) as on the base this was built on.
- **Builder on the retry path** (`:2168-2175`): `err = _invoke_leaf_resilient(...)`, the
  same shape as the peer call sites (`:2920`, `:3272`, `:3706`). The shipped defaults are
  used as they are (3 attempts, 4 s / 8 s backoff, the existing transient rule), with no
  new config knob. `memory_log=` is no longer passed. The wrapper derives the same
  `build.memory.jsonl` from `build.error.log`, as it does for the other three callers.
- **Prompt per attempt** (`:733`): the wrapper's `prompt` may now be a callable of the
  attempt number. A plain string is sent unchanged on every attempt, so the other three
  callers are byte-identical. The builder's `prompt_for` returns today's prompt for
  attempt 1 and `_build_prompt(..., dead_attempts=N-1)` after that. It also counts the
  attempts actually spawned.
- **Retry notice** (`_retry_notice`, `:2253-2281`): added between the task text and the
  rubric only when `dead_attempts > 0`. It points at `build.error.log` only if that file
  exists, and names the worktree only when one is in use.
- **Keeping the per-attempt record** (`:2042-2050`): the log is cleared at the start of
  each Do, so one that exists at failure was written by the retries. `do_build` now leaves
  it alone and only writes its own record for a Do that died outside the leaf (worktree
  setup, the lane lock).
- **Failed-Do report** (`_do_residue` `:2056`, `_report_failed_do` `:2064`, called at
  `:2052`): runs for every failure and lists the residue. It asks `state.state(d)` and
  prints the next action for BUILT, PLANNED or anything else. It deletes nothing. The
  "transient … not absorbed after N attempt(s)" line (`:2187-2191`) prints only for a
  failure classified transient, and N is the attempts actually spawned.
- **Unwritable log** (`:763-766`, `:2176-2182`): the wrapper still raises the same
  `OSError` when it cannot write the settled record, now chained `from` the leaf's own
  failure. The builder unwraps it, so the builder's failure still reaches the flow, as
  `test_capture_never_masks_the_real_failure` requires. Other callers see the same
  exception as before.

This builds on #540 (per-attempt record flush), already on `main`. It does not need #541's
code. A trial merge with #541's commit is clean, and the full suite passes with both
applied.

## Verification
- **Claim:** a transient builder death is retried with the shipped budget and backoff. A
  substantive failure is not.
  **Checked:** `leaves.py:2168-2175` against the peer sites `:2920` / `:3272` / `:3706`,
  and the unchanged stop rule in the wrapper.
  **Test:** `test_a_transient_builder_death_is_retried_with_the_shipped_backoff` (3 runs,
  sleeps `[4.0, 8.0]`), `test_a_transient_death_the_retry_absorbs_is_a_successful_build`,
  and `test_a_substantive_builder_failure_is_still_not_retried` (1 run, no sleep).
- **Claim:** attempt 1's prompt is today's; each retry is told its predecessor died and
  what it finds is residue, and the record it is pointed at is on disk when it starts.
  **Checked:** `:733`, `:2156-2164`, `:2253-2281`.
  **Test:** `test_attempt_one_is_unchanged_and_each_retry_carries_the_notice`,
  `test_the_record_a_retry_is_pointed_at_is_on_disk_when_it_starts`.
- **Claim:** every failed Do (transient, substantive or setup) names the residue and the
  true next step. A left `patch.diff` is reported as BUILT → Check.
  **Checked:** `:2052-2095`. The state comes from `state.py:347-364` (no `patch.diff` →
  PLANNED, `patch.diff` without gates → BUILT). `driver.py:69-76` runs Do only from
  PLANNED.
  **Test:** `test_a_patch_left_behind_reads_built_and_a_rerun_runs_check`,
  `test_a_transient_failure_names_the_attempts_it_actually_spent`,
  `test_a_substantive_failure_after_a_transient_one_gets_no_transient_sentence`,
  `test_a_do_that_died_in_setup_reports_too`.
- **Claim:** the retries' per-attempt record survives the final failure.
  **Checked:** `:2042-2050`.
  **Test:** `test_both_attempts_are_still_in_the_log`.
- **Claim:** a successful build is spawned as today: one spawn, same prompt, label,
  stream flag and memory log.
  **Test:** `test_one_spawn_with_todays_arguments`.
- **Red → green:** with only the production hunks reverted, 9 of the 11 new tests fail on
  their assertions, not on import. The other 2 are guards meant to pass either way (the
  substantive no-retry case and the spawn-arguments case). All 11 pass with the patch.
  `template/tests/test_build_error_log.py` stays green on both sides. Its three tests that
  now hit the retry path record the backoff instead of sleeping it, and no assertion there
  changed.
- **Full offline suite:** root suite OK, driver suite 1977 tests OK. Driver suite time
  went from 34.4 s to 34.7 s.

Fixes #537
