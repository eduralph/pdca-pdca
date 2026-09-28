# Build notes — #537 the builder retries like every other leaf

## Base actually used (read first)

- Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt` at **5daab65**
  (`origin/main`). It contains #540 (merge 4050da2) but **not #541**: #541 is the single
  commit fcc21a7 on `fix/541-no-dead-attempts-artifact-harvested-as-a-live-ones`, an open
  draft PR (#585) based on 5daab65. The brief expected the wave fold to give me both; it
  gave me #540 only. This bundle has no `stack-base` marker, so C4 resolves
  `$PDCA_BRIEF_BASE` = `origin/main` (`engine/scripts/run-verify.sh:31-50`), the same base
  the worktree was made from. I therefore built on 5daab65.
- Nothing in this slice needs #541's code: `_LeafHarvest` (fcc21a7) owns the reviewer /
  advisory artifact paths; the builder is not a harvest site and passes no `harvest=`.
- Checked the other direction too: `git merge-tree --write-tree <this patch> fcc21a7` is
  **clean**, and with #541's diff applied on top of this patch the whole T3 suite passes
  (driver suite 2001 tests OK, root suite OK). A first cut using
  `from collections.abc import Callable` conflicted with #541's import hunk (it adds
  `from collections import deque` + the same line at the same spot), so the patch uses
  `import collections.abc` at `leaves.py:37` instead; after both land that is one redundant
  import, not a conflict.
- The brief's line numbers are for acb214a. On 5daab65 (pre-patch) the same regions are:
  `_invoke_leaf_resilient` 680-753 (loop `_invoke` call 722, settled write 752),
  `do_build` 1991-2028 (stale clear 2001-2003, capture 2021-2028), `_do_build_command`
  2031-2081 (plain `_invoke` 2074-2081, explicit `memory_log=` 2080), `_build_prompt` 2084,
  `_stub_build` 2139, `select_builder` 1884, peer call sites 2775 / 3127 / 3561,
  `LeafError.transient` 104-108. `state.py:347` / `:363-364`, `driver.py:69-76`.

## What changed (post-patch line numbers, `template/src/pdca_harness/leaves.py`)

1. **Builder on the resilient path** — `_do_build_command` `:2098-2192`. The plain
   `_invoke` became `err = _invoke_leaf_resilient(...)` (`:2168-2175`) with
   `error_log=d / BUILD_ERROR_LOG`, the same label / status / stream_json / env /
   extra_argv / cfg as before, and **no** `memory_log=` (the wrapper derives
   `build.memory.jsonl` from `build.error.log` via `_memory_log_for`, `:728`). No
   `attempts=` / `backoff=`: the shipped defaults (3, 4.0 s) apply. `if err is None:
   return` / `raise err` (`:2183-2192`) keeps `do_build`'s capture + re-raise contract.
2. **Prompt per attempt** — the wrapper's `prompt` may now be a callable of the attempt
   number (`:691-697` signature, `:733` the one changed loop line). A plain string is sent
   unchanged on every attempt, so the reviewer and both advisories are byte-identical. The
   builder passes `prompt_for` (`:2159-2164`): attempt 1 returns `first`, built eagerly at
   `:2156` exactly as the old call built it; attempt N≥2 returns
   `_build_prompt(..., dead_attempts=N-1)`. `prompt_for` also records `spent` — the wrapper
   asks for attempt N's prompt immediately before spawning it, so `spent` is the number of
   attempts actually spawned.
3. **Retry notice** — `_build_prompt(..., dead_attempts=0)` (`:2195-2250`) appends
   `_retry_notice(...)` (`:2253-2281`) between the task text and the rubric only when
   `dead_attempts > 0`; 0 appends `""`, so every other caller's prompt is byte-identical.
4. **Unwritable settled record** — the wrapper's final write is now
   `try: _replace_record(...) except OSError as exc: raise exc from last` (`:763-766`).
   Same OSError, same moment; only `__cause__` is set. `_do_build_command` catches that
   OSError (`:2176-2182`) and raises the builder's own failure instead.
5. **`do_build`'s capture** (`:2036-2053`): if `build.error.log` exists (it was cleared at
   `:2016`, so only the wrapper can have written it during this Do) it is left alone and the
   print says so; otherwise the old single-record capture runs. Then `_report_failed_do(d)`
   runs for **every** failure, inside `contextlib.suppress(Exception)`, then `raise`.
6. **Report helpers** — `_do_residue` (`:2056-2061`: patch.diff, build-notes.md and the
   brief's test files, those that exist, read-only) and `_report_failed_do`
   (`:2064-2095`: residue line, then `state.state(d)` asked, next action per state).
7. The transient sentence is printed in `_do_build_command` (`:2187-2191`), the one place
   that knows `spent`; condition is `getattr(err, "transient", False)` — the shipped
   classification, untouched.

Tests: new `template/tests/test_builder_retry.py` (11 tests), and
`template/tests/test_build_error_log.py` gets `_no_backoff()` (`:36-42`) used at `:72`,
`:168`, `:209`. No assertion in that file changed.

## Why this shape, and what I ruled out

### The #286 vs #540 conflict (the non-obvious part)

Putting the builder on the wrapper collides with two pinned contracts:

- #540: the wrapper **raises** OSError when the settled record cannot be written
  (`leaves.py` comment above `:763`; pinned by `test_attempt_ownership.py:290-299`
  `assertRaises(OSError)` and the torn-write driver's `final_write == "OSError"`, `:195`).
- #286: a builder failure reaches the flow even when the log cannot be written (pinned by
  `test_build_error_log.py:163-170` `test_capture_never_masks_the_real_failure`, which
  patches `Path.write_text` to raise and asserts `LeafError`).

Moving the builder onto the wrapper unchanged turns that test's `LeafError` into
`OSError("read-only fs")` — I confirmed this by removing the unwrap (mutation 5 below):
the test goes red with `OSError: read-only fs` raised from the wrapper's final write.

Options considered:
- **Make the wrapper swallow the write failure** — changes #540's contract for the other
  three leaves and breaks `test_attempt_ownership.py:296`. Rejected (brief (v)).
- **Relax `test_capture_never_masks_the_real_failure` to accept OSError** — weakens a pinned
  contract; the brief only allows updating that file for wall-clock / call counts / (iv).
  Rejected.
- **A builder-only kwarg on the wrapper ("don't raise on write failure")** — a second new
  wrapper parameter plus a second code path in the wrapper; more surface than needed.
- **Chosen:** `raise exc from last` (1 statement → 4 lines in the wrapper) + a 7-line
  `except OSError` in `_do_build_command` that re-raises `__cause__` and prints
  `could not write build.error.log (…)`. The other three call sites see the same OSError
  as before; the extra `__cause__` only adds the leaf's failure to their traceback. The
  re-raise is done after the `except` block (not inside it) so no `__context__` cycle is
  created.

### Why a callable prompt rather than a `retry_note=` kwarg

One changed loop line (`:733`) and no new parameter to thread through; attempt 1's prompt
is produced by exactly the old expression. It also gives the attempts-spent count for
free, without stamping attributes on exceptions (round 3's `_stamp_attempts`) or adding a
line inside the wrapper's `except` block — that block is where #541 inserts its
`harvest.withdraw` call, so staying out of it is also what keeps the merge with #541 clean.

### "N is the attempts actually spent, not the budget"

Measured (`spent`), not assumed. Honest caveat: on this base a transient *final* failure
can only happen on the last attempt (the stop rule `if not transient or attempt ==
attempts: break`, `leaves.py:747-748`), so N always equals the budget in every reachable
case today. The test compares N with the stub's own invocation count, which is correct but
cannot distinguish "measured" from "hard-coded budget" on this base. Measuring keeps the
sentence true if #533 / #510 change the stop rule.

### Wording of the transient sentence

The brief names it *"transient — absorbed after N attempts"*. On a failed Do the death was
*not* absorbed, so the printed sentence is:
`transient: the builder leaf exited 1 without emitting any work, the class of failure the
harness retries to absorb; not absorbed after 3 attempt(s).` I avoided #533's
`"on transient infra"` wording and did not touch any string inside
`_invoke_leaf_resilient` (its retry print still says `leaves: <workdir.name> — …`, which
for a claude builder is the harness root's name — a #533 string, left alone).

### Retry notice honesty

- It does not say *which* attempt left the residue: Do only starts from PLANNED
  (`driver.py:69-75`, the only `do_build` caller), i.e. with no patch.diff
  (`state.py:347`), so nothing there is a finished build; but a build-notes.md or test file
  may predate this Do (an earlier failed Do), so "that dead attempt's" could be false.
  Wording used: "INCOMPLETE RESIDUE of an attempt that did not finish".
- The pointer at `build.error.log` is included only if the file is there when the retry's
  prompt is built (the #540 flush is best-effort, `leaves.py:770-783`).
- The worktree clause is only emitted when `worktree_root` is set (`$PDCA_WORKTREE`, "NOT
  reset between attempts" — true: `worktree.ensure` runs once, `:2110`, before the
  wrapper); in-place runs get "any source edit already made in place".
- Is a prompt-level statement sufficient (brief asks)? I think yes for this slice. A retry
  only follows a transient death, i.e. no substantive stream event arrived
  (`progress.py:187`, `:466`), so in practice the dead attempt rarely did tool work; the notice
  covers the remaining case (work done but events lost). A lane reset between attempts
  would be stronger but is out of scope, and it would destroy possible evidence.

### Report for every failed Do

Round 3 gated the report on retryability, which made the BUILT branch unreachable. Here
`_report_failed_do` runs for every failure, including setup failures (tested:
`test_a_do_that_died_in_setup_reports_too`). The state is asked via `state.state(d)`;
BUILT → "a plain re-run (`pdca run <id>`) runs CHECK on that unfinished patch.diff, not
Do. To rebuild instead, move patch.diff out of the bundle first." PLANNED → "starts Do
again", plus a warning when other residue exists that the re-driven builder is not told it
is residue (true: a fresh Do's attempt 1 prompt has no notice). Anything else → "`pdca
status` shows what a re-run does next". Nothing deletes anything.

### Wall-clock trap

Chose "patch the sleep" over exposing a budget: no new module constant or parameter, and
the shipped defaults are untouched. Both test files replace `leaves.time` (the module
object `leaves` imported) with a stand-in whose `sleep` does not wait; everything else is
the real `time` module. It is narrower than patching `time.sleep` globally: `progress.py`'s
own `time.sleep` (straggler sweep, `progress.py:386`) is unaffected. In the new file the
stand-in records the delays, so the test asserts the builder's backoff is exactly the
shipped `[4.0, 8.0]`. The brief named only `test_build_error_log.py:63-71`; two more tests
there also hit the retry path — `test_capture_never_masks_the_real_failure` (mocked
transient LeafError) and `_build_with_a_dying_child` for the `claude` family (stderr-only
child ⇒ transient) — so all three get `_no_backoff()`. Driver suite time: 34.4 s baseline
→ 34.7 s with the patch (+11 tests).

## Test runs (all through the project's runners)

- **C4** `engine/scripts/run-verify.sh` (PDCA_BUNDLE=this bundle, PDCA_WORKTREE=the
  worktree), final patch: green leg `test_build_error_log` 12 OK + `test_builder_retry`
  11 OK; red leg `test_build_error_log` 12 OK, `test_builder_retry` **9 failures, 0
  errors, 0 load failures** → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  The 2 tests that pass on the red leg are guards meant to hold on both:
  `test_a_substantive_builder_failure_is_still_not_retried` and
  `test_one_spawn_with_todays_arguments`.
- **T3** `engine/scripts/run-suite.sh`: baseline (untouched base) driver suite 1966 OK;
  root suite had 1 error, `test_update_compat.UpdateCompat.setUpClass` (a `git commit` in a
  temp repo failed) — pre-existing and environmental, it passed on both later runs. With
  the patch: root OK, driver 1977 OK. With the patch + #541's diff on top: root OK, driver
  2001 OK.

## Refuting my own test

- **(a) Genuine red?** Yes. C4's red leg reverts only the production hunks
  (`run-verify.sh:214`) and 9 of the 11 new tests fail on assertions — e.g.
  `1 != 3 : a transient builder death must be retried…`, `'— transient:' not found in
  'overloaded_error 529\nleaves: issue_RETRY — Do failed; captured the error tail…'`,
  `'attempt 2' not found in '----- attempt 1 — exit 1 -----\nfirst-death'`. The module
  imports only pre-existing API (`leaves`, `state`, `worktree`, `Config`, `LeafConfig`),
  so there is no load failure. Mutations, each run through C4 and then reverted (worktree
  re-verified byte-identical to patch.diff afterwards):
  1. `do_build` overwrites unconditionally (guard removed) → red:
     `test_both_attempts_are_still_in_the_log` (`'first-death' not found`) and
     `test_a_transient_builder_death_is_retried_with_the_shipped_backoff`.
  2. Retry notice dropped (`prompt_for` always returns `first`) → red:
     `test_attempt_one_is_unchanged_and_each_retry_carries_the_notice`.
  3. Residue report gated on `exc.transient` (round 3's defect) → red: the BUILT test, the
     transient-then-substantive test and the setup-failure test.
  4. Unwrap removed (`_do_build_command` re-raises the OSError) → red:
     `test_build_error_log.test_capture_never_masks_the_real_failure` (`OSError: read-only
     fs`).
  Not bindable on this base: "N = spent vs N = budget" (see above).
- **(b) Production path?** Yes. Every test except the (v) spawn-arguments guard drives the
  real `leaves.do_build` → `_do_build_command` → `_invoke_leaf_resilient` → `_invoke` →
  `progress.run_with_heartbeat` → a real subprocess. The only stand-in is `leaves.time`,
  whose `sleep` records instead of waiting. The (v) guard mocks `_invoke` on purpose, to
  read the exact spawn arguments (prompt, `memory_log`, label, stream_json).
- **(c) Fixture includes the fault?** Yes. The transient stub dies exactly the way the
  shipped rule classifies as transient (stderr only, exit 1, no stream event — copied from
  `test_leaf_resilience.py:28-35`); the substantive stubs emit `{"type":"assistant"}`
  first. The BUILT case really writes `patch.diff` into the bundle and dies; the (iv) case
  really has attempt 1's record flushed by the wrapper (the stub copies the log it finds at
  attempt 2, and the test asserts that copy holds attempt 1) before attempt 2 fails.

## Commit-readiness

The target configures no Python formatter or linter (no pre-commit config; `.github/
workflows` only lint docs; INTEGRATION.md §8 asks for conventional-commit subject, DCO
`Signed-off-by`, `Fixes #537`). `git diff --check` is clean and every added line is
≤ 100 columns. None of ruff / pyflakes / flake8 is installed here, so no lint run.

## Housekeeping to report

- By mistake I wrote one log outside the harness roots: `/tmp/claude-baseline-suite.log`
  (the baseline T3 output). Not removed — cleanup is the harness's.
- The merge check with #541 created two unreferenced commit objects in the shared object
  store (`git commit-tree`, no ref updated); `git gc` reaps them.
- The worktree index carries an intent-to-add entry for the new test file so that
  `git diff` (and so patch.diff) includes it.
- Bundle copy of the test: `results/issue_537/template/tests/test_builder_retry.py`
  (identical to the file in patch.diff).
