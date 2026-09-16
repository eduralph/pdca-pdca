# Build notes — issue #536 (iteration 3): attempt-owned leaf records and harvests

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All edits made in
`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l0`; every `path:line` below is
**post-patch** in that tree unless it says "base".

## 0. What this iteration is

Round 2 was rejected on **unclosed carry-forward**, not on approach or slicing ("the slice
is the right size and the design is sound… Same slice, same design; close the items
below"). So this iteration *starts from* `iteration-v2/patch.diff` (re-applied to the clean
base, `git apply --check` first) and changes only what the four carry-forward items name.
The production delta against v2 is small and local:

| item | region | statement-level change |
|---|---|---|
| 1 | `leaves.py:723,743` | drop the `withdrew` flag; keep-rule becomes `records and artifact is not None and not artifact.exists()` |
| 2 | `leaves.py:746`, `:857-883`, `:2823`, `:3176`, `:3480` | `contextlib.suppress(OSError) + unlink` → `_discard_attempt_records()` (6 statements); the three `_settle_leaf_record` calls move **inside** the placeholder branch |
| 3 | test only | 2 new assertions / cases that kill the two mutants the adversary demonstrated |
| 4 | `driver.py:178-184` | the recovery line no longer says "reviewer never ran" |

Everything else in the patch is v2's, re-verified against the base.

## 1. Item 1 — keep the account for the death that actually happens

**Was:** `if withdrew and artifact is not None and not artifact.exists():` — the log
survived a success only when a dead attempt had left a **file**. The canonical transient
death leaves no file: attempt 1 dies at invocation with `overloaded_error 529` on stderr
and nothing else; attempt 2 comes back alive and produces nothing. v2 unlinked the log in
that case, so `_empty_run_class` (`leaves.py:2852`) saw nothing, stamped `_FAIL_SUBSTANTIVE`
and the placeholder told the operator "**substantive — needs a human.** … do not assume an
infra blip" one step after the harness deleted the 529 it was holding.

**Now:** `leaves.py:743` keeps the log whenever **this run recorded a failed attempt**
(`records` non-empty) and the leaf produced no artifact — the adjudication the sign-off
supplied. The classification then follows for free: the wrapper retries none but
*transient* failures (`leaves.py:759`), so any log surviving a successful return is by
construction an infra death, which is exactly what `_empty_run_class` says (`leaves.py:2852-2864`).

Criterion (iii) is untouched and asserted: a leaf that exits 0 having written nothing with
**no** dead predecessor has `records == []` → the log is discarded → the placeholder is
byte-identical to today, class included
(`test_a_leaf_that_exits_zero_writing_nothing_still_degrades_as_today`). Criterion (vi)'s
"a success still leaves no error log behind" governs a success that **produced its
artifact**: `test_the_live_attempts_own_artifact_is_still_harvested` asserts exactly that,
and `test_leaf_resilience.py`'s `test_success_leaves_no_error_log` /
`test_stale_error_log_cleared_on_success` still pass untouched (they pass no `artifact=`,
so the `artifact is not None` clause keeps their behaviour identical).

New red→green case: `test_a_death_that_left_no_file_is_kept_and_classified_just_the_same`
(red on the base **and** red on v2 — see §5).

## 2. Item 2 — the cleanup is a discard, not a best-effort unlink

**Was:** `with contextlib.suppress(OSError): error_log.unlink(missing_ok=True)`. A refused
removal left the log standing **with its in-flight trailer**, and the harvest then called
`_settle_leaf_record` unconditionally, which stripped the trailer — converting the leftover
into a settled "the leaf ran and FAILED" record (`_leaf_ran_and_failed`) sitting beside the
`check-review.md` the same leaf had just produced. One leaf archived as both success and
failure, against criterion (vi).

**Fixed at the source, in two halves:**

1. `_discard_attempt_records` (`leaves.py:857-883`) — the removal is *reported* when the
   filesystem refuses it (`leaves: could not remove … it stays marked unsettled rather than
   be filed as a failure this leaf did not have`), instead of silently swallowed. It still
   never raises: a log that cannot be removed must not turn a leaf that worked into a
   failure (that is why the removal is attempted at all, #138).
2. The three harvests now settle **only the log they filed** — the call moves inside the
   `else:` (placeholder) branch at `leaves.py:2823`, `:3176`, `:3480`. On the branch that
   harvests a real artifact there is nothing to settle by construction (the wrapper keeps a
   log only when the artifact is **absent**), so the only log that can be standing there is
   one the filesystem refused to remove — and settling *that* is precisely the false
   verdict. It now stays in flight: an account the operator was warned is unsettled is at
   worst noise; a settled one is a verdict the leaf never gave. No reader is affected either
   way (`review_never_ran` and the advisory `only_missing` short-circuit both see the
   artifact first) — this is the archive-honesty half of the invariant.

New red→green case: `test_a_log_that_cannot_be_removed_is_never_filed_as_a_failure` (red on
v2 for both assertions: no warning printed, and the leftover settled).

**Why not the alternatives** (concrete costs, not adjectives):

* *Give `_settle_leaf_record` a "did we file an artifact" parameter and keep the call where
  it was.* +1 parameter, the same 3 call sites edited, and a branch whose entire purpose is
  to do nothing. Moving the call is 3 lines re-indented and 0 new parameters, and it makes
  the rule readable at the call site.
* *Make a refused removal fail the leaf (raise / return the exception).* Forbidden by the
  shipped contract: `_invoke_leaf_resilient` must not convert a leaf that worked into a
  failure. It would also fire on the one filesystem state where the operator can least
  afford to lose the review.
* *Re-assert the in-flight marker after a refused removal
  (`_write_attempt_records(error_log, records, in_flight=True)`, +2 lines).* Unreachable
  belt-and-braces: the only way a log survives to that point is a flush that expected a
  retry, and that flush always writes the marker (`leaves.py:760` with `in_flight=may_retry`
  — a final-attempt flush writes `in_flight=False` but then `break`s, so the success path is
  never reached with an unmarked log). It would be code no test can distinguish, and in the
  read-only case that motivates it, the write fails too and prints a second warning. The
  reasoning is recorded in the docstring instead (`leaves.py:864-873`).

## 3. Item 3 — the two mutants the adversary demonstrated are now killed

Both were verified by *applying the mutation to this patch* and re-running the module
(details in §5):

* **Substring sniff instead of a whole-last-line match** in `leaf_run_incomplete`
  (`leaves.py:886-904`). New case
  `test_a_marker_quoted_in_the_body_does_not_speak_for_the_run` hand-writes two complete
  logs — one with the marker on a **non-final** line, one where the final line **contains**
  the marker mid-line — and asserts through `leaves.review_never_ran` that a leaf which gave
  up stays retired. Hand-written on purpose: the two impersonation cases already in the file
  route their payload through `_defang_in_flight` first, so they pass a sniffing mutant.
* **Deleting both advisory `_settle_leaf_record` calls.**
  `BothAdvisoryHarvestsAreAttemptAwareToo.test_a_dead_attempts_artifact_is_not_harvested_at_either_site`
  now also asserts `leaves.leaf_run_incomplete(error_log)` is False after each site, i.e.
  the account stops claiming the run is unfinished once the outcome is filed.

A third mutation I ran unprompted — deleting the **reviewer's** settle call — is killed by
the pre-existing `test_a_filed_outcome_settles_the_account`, so all three settle sites are
now guarded.

## 4. Item 4 — the fourth reader's wording

`driver.py:177-184`. `review_never_ran(d)` now also fires for a reviewer that ran, died
transiently and was killed before its retry or its harvest landed, so the line no longer
claims "reviewer never ran (beat was interrupted after the gate write)". It reads
"Check — no completed review (the reviewer never ran, or the beat was interrupted while it
did); recovering it…", matching the §6 text `assemble._missing_review_text` already carries
(`assemble.py:433-440`). Wording only — no control flow.

## 5. Verification (project runners only)

Run through the instance's own gate scripts, with `$PDCA_BUNDLE` / `$PDCA_WORKTREE` set as
the driver sets them:

| gate | command | result |
|---|---|---|
| C4 | `./engine/scripts/run-verify.sh` | **PASS** — green leg `Ran 22 tests … OK`; red leg `Ran 22 tests … FAILED (failures=17, errors=1)` |
| T3 | `./engine/scripts/run-suite.sh` | OK — 7 render/update-compat + **1780** offline driver tests (`skipped=2`) |
| T2 | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`, `render_site: link audit OK` |
| C5 | `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` | `1 added driver-suite test(s) import the production package 'pdca_harness'` |

Two extra checks that are not gates, run as `timeout 300 env PYTHONPATH=src python3 -m
unittest tests.test_attempt_ownership` from `template/` (the command `CONTRIBUTING.md`
names; bounded by an explicit `timeout`, and the module runs in ~1.2 s):

* **Delta refutation vs iteration v2.** With v2's production hunks applied and *this*
  iteration's test file: `FAILED (failures=2)` —
  `test_a_death_that_left_no_file_is_kept_and_classified_just_the_same` and
  `test_a_log_that_cannot_be_removed_is_never_filed_as_a_failure`. So the two new
  behavioural cases bind the two behavioural carry-forward items, not just the base defect.
* **Mutation testing of the new guards**, each applied to *this* patch:
  * `leaf_run_incomplete` → substring sniff: `FAILED (failures=2)` (both subtests of the new
    case).
  * both advisory `_settle_leaf_record` calls deleted: `FAILED (failures=2)` (both sites).
  * the reviewer `_settle_leaf_record` call deleted: `FAILED (failures=2)`.

  The tree was restored from `patch.diff` after each mutation and the final C4 + T3 runs
  were made on the shipped state.

Style/commit-readiness: the target ships no formatter or pre-commit hook (no
`.pre-commit-config.yaml`, no linter config; CI is docs-check / render-check /
require-linked-issue). Longest **added** line is 93 chars (repo norm: existing lines run to
110), no tabs, no trailing whitespace, file ends with a newline. `test_leaf_resilience.py`
is not in the patch.

## 6. Forced self-refutation (recorded for sign-off)

* **(a) Genuine red?** **Yes.** `run-verify.sh` reverts the production hunks and keeps every
  `template/tests/*` hunk: 17 failures + 1 error across 22 tests, including every new case.
  The module still **imports** on the red leg (no module-level import of anything this patch
  adds), so the red is measured, not a load failure — `LOAD_FAILED` stayed 0 and the gate
  printed `PDCA-EVIDENCE: C4 PASS`, not `PDCA-UNVERIFIABLE`.
* **(b) Production path?** **Yes.** Every case drives shipped entry points —
  `leaves._invoke_leaf_resilient`, `leaves._run_review_sandboxed`,
  `leaves._run_advisory_sandboxed`, `leaves._run_plan_advisory_sandboxed`,
  `leaves.review_never_ran`, `assemble._missing_review_text` — with a real `python3`
  subprocess as the "leaf" (`_invoke` → `progress.run_with_heartbeat` → `subprocess`).
  Nothing is re-implemented in the test; the C5 gate independently confirms the added test
  imports the production package.
* **(c) Fixture includes the fault?** **Yes.** The dead attempt is a real child process that
  exits non-zero with stderr and no stream event (the shipped transient signal); its residue
  is a real file in the real sandbox; the kill windows are modelled by raising a
  `BaseException` from **inside** the production write (`Path.write_text`), and the
  filesystem refusals by making the real `Path.unlink` raise for exactly the file under
  test. Nothing curates the failing element out — the case that matters most for item 1
  (`first_writes=""`) deliberately removes the *file* while keeping the *death*.

## 7. Known limitations — deliberately not fixed here (Act candidates)

* **The staleness clear at `leaves.py:718`** still deletes a preserved dead-attempt verdict
  when the #369 recovery re-runs the leaf. Criterion (vi) freezes that clear, and both prior
  sign-offs adjudicated it as an Act deferral. Unchanged.
* **`shutil.copy2` of the verdict at the three harvests** (`leaves.py:2809`, `:3172`,
  `:3475`) is not atomic; a kill mid-copy can leave a truncated artifact. Noted by round 2
  as an Act candidate, not this round's work.
* **A stranded `*.error.log.tmp.<pid>`** from `_atomic_write_text` (`leaves.py:813-820`) if
  the process dies between the temp write and `os.replace`. Inert (it is not the log, and no
  `state.DOWNSTREAM_GLOBS` pattern claims it); same Act note.
* **`_invoke_leaf_resilient`'s entry unlink (`leaves.py:718`) is unguarded** on the base and
  stays unguarded: an unwritable bundle raises out of the wrapper. Pre-existing, out of
  slice.
* **One imprecise stderr note, carried over from v2 unchanged.**
  `_write_attempt_records`' failure message (`leaves.py:846-852`) is worded for the retry
  caller ("not starting another attempt…; the leaf's own failure is returned unchanged"). It
  is also reachable from the *success*-path keep at `leaves.py:744`, where there is no next
  attempt and no failure to return. Not fixed here because making it exact needs a new
  parameter on the helper (+1 param, +1 branch, 3 call sites) for a line that can only print
  if the filesystem turns read-only **between** attempt 1's successful flush and the
  successful retry's — and because the retry wording is the observable
  `test_a_retry_never_starts_without_its_predecessors_account_on_disk` asserts. Flagging it
  so it is a known choice rather than an oversight.

No external dependency was needed: pure-stdlib Python 3.14 + git, offline, no vendor CLI, no
API key, no container.
