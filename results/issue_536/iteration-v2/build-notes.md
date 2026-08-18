# Build notes — issue 536, iteration 2 (attempt-owned leaf records and harvests)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All edits in the cycle worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`; every `path:line` below is that tree **after**
the patch unless it says "base" or "v1".

Same slice, same mechanism as iteration 1 — the sign-off rejected it on five crash-recovery
/ test-blindness findings, not on approach. This iteration starts from v1's patch and closes
those five. Everything v1 shipped that the reviewer and the adversary confirmed (the
per-attempt flush, the withdrawal, the defang + whole-last-line match, the two discriminators)
is unchanged.

## The five carry-forward findings, and what closes each

**1. The per-attempt flush is now crash-atomic.** `_atomic_write_text`
(`leaves.py:788-816`) writes a temp sibling and `os.replace`s it — the idiom the repo
already ships for its other kill-sensitive record (`act.py:325-326`, the review frontier).
`_write_attempt_records` (`leaves.py:819-850`) routes through it, so no kill can catch the
log truncated-and-unmarked. v1's plain `write_text` truncated first and appended the trailer
last: a kill in between left a 0-byte log, which reads "ran and gave up"
(`_leaf_ran_and_failed`, `:874`) → `review_never_ran` False (`:2352`) → `driver.py:176` never
recovers the reviewer. The base left *no* log in that window and did recover, so v1 really
did introduce it. Bound honestly in the docstring: this covers a killed **process** (the OOM
kill, Ctrl-C, a killed session); surviving a power loss would need fsync, which the repo's
idiom does not do either.

**2. The post-success/pre-placeholder window is closed by sequencing.** The wrapper's
"succeeded having written nothing after a withdrawal" branch now re-flushes the kept log
**in flight** (`leaves.py:737-738`, was `in_flight=False` in v1), and each harvest site
drops the marker *after* it has filed the outcome: `_settle_leaf_record`
(`leaves.py:880-908`) called at `:2783` (reviewer), `:3135` (advisory), `:3439`
(plan-advisory). Every ordering of a kill now leaves an honest state:

| kill lands | on disk | reads as |
|---|---|---|
| during the flush | previous or new complete in-flight log (atomic) | interrupted → recovered |
| after the wrapper returns, before the placeholder | in-flight log, no review | interrupted → recovered |
| after the placeholder, before the settle | placeholder + in-flight log | outcome filed; marker inert |
| during the settle | in-flight or settled (atomic) | either is honest |

The settle sits *outside* the harvest `if/else` on purpose: the artifact-copied branch needs
it too, in the corner where the wrapper's own `unlink` of the log was refused (suppressed
`OSError`, `:740-741`) and the log would otherwise keep a marker forever.

**3. An infra death is filed as infra.** `_empty_run_class` (`leaves.py:2812-2825`), used by
all three "produced no artifact" branches (`:2779`, `:3134`, `:3437`). A log that survives a
*successful* return exists only because the wrapper withdrew a dead attempt's artifact, and
the wrapper retries none but transient failures — so it is by construction an infra death and
needs no new information. Left at `_FAIL_SUBSTANTIVE` (v1) the placeholder stamped
`human-empty` and said "substantive — needs a human … do not assume an infra blip" one
sentence above a log reading `overloaded_error 529`: the inversion #278's marker exists to
prevent. With no log the class is the shipped default, byte for byte. `_FAIL_TRANSIENT`'s
inline comment (`:2789`) lost the words "retries exhausted", which is no longer the only
shape that reaches it.

**4. The two test-blindness gaps are closed by tests, not prose.**
`BothAdvisoryHarvestsAreAttemptAwareToo` (`test_attempt_ownership.py:403-466`) drives
`_run_advisory_sandboxed` **and** `_run_plan_advisory_sandboxed` through one parametrized
case (`subTest(site=…)`), so the reviewer's two near-identical twins are exercised rather
than read; and `test_an_artifact_that_cannot_be_withdrawn_stops_the_retries` (`:377-401`)
mocks `Path.unlink` — mirroring the existing `refuse_the_log` write-failure pattern — to
drive `_withdraw_residue`'s fail-closed branch (`leaves.py:949-955`), which v1 asserted only
in prose.

**5. The third reader is aligned.** `assemble._missing_review_text` (`assemble.py:424-425`)
now asks `leaves._leaf_ran_and_failed` instead of a bare `.exists()`, and its "NEVER RAN"
wording (`:434-440`) no longer claims "no `check-review.error.log` exists" — an interrupted
leaf's log does. Deferred module-level import (`from . import leaves`) because `leaves`
imports `assemble` at top level; the idiom and the cross-module private call both have
precedent (`handoff.py:132`, `dependency_halt.py:87`, `publish.py:807`). Kept private per the
sign-off's literal instruction.

Also closed, though not in the numbered list: the reviewer's **T2 FAIL** on the shared
constant's contract — `state.REVIEW_ERROR_LOG`'s comment (`state.py:67-72`) said the file
exists only when retries are exhausted, which this slice makes false for every consumer that
reads it.

## The rest of the patch (unchanged from v1, re-verified against this base)

`artifact=` on the wrapper (`leaves.py:681`); the loop-body withdrawal + per-attempt flush
(`:723`, `:748-757`); `_LEAF_IN_FLIGHT` (`:774`) and `_defang_in_flight` (`:777-785`);
`leaf_run_incomplete` matched as the **last non-blank line, whole** (`:853-872`);
`_leaf_ran_and_failed` (`:874-878`); `_withdraw_residue` (`:917-957`); the defanged
`_format_leaf_attempt` (`:959-971`); the three harvest sites passing `artifact=`
(`:2761`, `:3122`, `:3425`); the two recovery discriminators (`:2352`, `:3080`); and the
`driver.py` prose (`:124-130`, `:154-162`) where the meaning of "an error log exists" is
documented. The marker string itself changed (`:774`) — "the retry loop had not finished" is
no longer the only reason it is there, and it is operator-facing text in the log.

Unchanged on purpose, per the brief and the sign-off: the retry set / `LeafError.transient` /
`progress.py`, the builder path, the attempt budget and backoff, the staleness clear
(`:716`), the `_memory_log_for` derivation, and `template/tests/test_leaf_resilience.py`
(untouched, 5/5 green — verified, not edited).

## Known limitations (deliberately not fixed here)

* **The staleness clear still deletes a preserved verdict on recovery.** `leaves.py:716`
  unlinks the log at the start of every run, so the recovery run that an in-flight log
  triggers destroys the dead attempt's withdrawn text before it can be read. The adversary
  found this in v1; criterion (vi) freezes that clear, and the sign-off explicitly ruled the
  fix a scope change. Flagged for Act.
* **Artifact writes are still not atomic.** `_review_unavailable`'s `write_text`
  (`leaves.py:2839`) and the harvests' `shutil.copy2` can be caught mid-write by a kill, so a
  torn placeholder/review is possible. Pre-existing on the base for every artifact the
  harness writes, unchanged by this patch, and a different (much wider) slice: the invariant
  here is about the *error-log discriminator*, which is the file this patch made a kill
  window in.

## Alternatives considered, with their cost

* **`fsync` the log + its directory instead of / on top of `os.replace`** (finding 1): +3
  lines and an `O_DIRECTORY` open in `_atomic_write_text`. Rejected: it buys durability
  against a power loss, not against the kill this harness actually sees (the leaf scope's OOM
  kill, `leaf_memory_max`), and the repo's own kill-sensitive record (`act.py:325-326`) sets
  the same bar. Documented rather than silently scoped.
* **A separate `*.error.log.in-flight` marker file** instead of a trailer (finding 1): ~10
  lines, plus a new `state.DOWNSTREAM_GLOBS` pattern (`state.py:121`) or the marker leaks
  across rounds, plus all three discriminators reading two files instead of one. Rejected:
  keeping two files consistent under a kill is a *harder* version of the problem being
  solved, and the trailer needs no archive vocabulary at all.
* **Settle inside the three `*_unavailable` writers** rather than at the harvest sites
  (finding 2): identical line count (3 calls either way). Rejected on correctness, not style:
  the artifact-copied branch also needs a settle (the `unlink`-refused corner above) and
  never calls `*_unavailable`; and those helpers are also called on the `err is not None`
  path where the log is already settled, so the call would read as if it did something there.
* **A fourth failure class** (`empty-after-infra`) instead of reusing `_FAIL_TRANSIENT`
  (finding 3): a 4th constant, a 4th branch in `_unavailable_classification`
  (`leaves.py:2849-2877`), a 4th `assemble.LEAF_STATUS_*` (`assemble.py:80-82`) and every §6
  reader taught the new marker — ~20 lines across two modules. Rejected: #278 splits by the
  operator's next **action**, and the action here is exactly `transient`'s ("safe to
  re-run").
* **Timestamp/PID ownership instead of withdrawal** (stat the artifact's mtime against the
  attempt's start): rejected on correctness. A dead attempt that wrote 200 ms before dying
  and a live attempt that rewrote are milliseconds apart on a fast leaf, and a tmpfs with
  coarse mtime granularity misclassifies silently. Withdrawal needs no clock.
* **Delete the residue without preserving it**: `_withdraw_residue`'s body collapses from 8
  lines (`leaves.py:940-947` — the read, the `_RESIDUE_KEEP` truncation, the record) to the
  `unlink` alone. Rejected: the sandbox is a `TemporaryDirectory` that dies with the run, so
  deleting is the one action that makes a real verdict unrecoverable while the placeholder
  tells the operator none was produced.
* **Marker as a substring test only** (no `_defang_in_flight`): saves 9 lines
  (`leaves.py:777-785`) plus two call sites (`:947`, `:968`). Rejected: it is the hole round 3
  shipped; a reviewer of *this* file quoting the marker would then declare the harness's own
  run unfinished. The adversary put 30 payloads through both doors in v1 and could not break
  the pair.
* **Flush best-effort and retry regardless** (drop the `recorded` gate, `leaves.py:756-757`):
  saves 1 line of control flow and the `bool` return. Rejected: it re-opens the precise
  window the slice exists to close.
* **Make `_leaf_ran_and_failed` public** for the `assemble` caller (finding 5): 0 lines
  either way. Kept private — the sign-off named it with the underscore, and cross-module
  private calls have precedent here (`dependency_halt.py:87`, `publish.py:807`).

## Refuting my own test (forced questions)

Runner: the project's own gate scripts only — `engine/scripts/run-verify.sh` (C4),
`run-suite.sh` (T3), `run-prod-path.py` (C5), `run-docs-check.sh` (T2), each with
`$PDCA_BUNDLE` / `$PDCA_WORKTREE` set. The single non-gate invocation (the v1 differential
below) is the exact command `run-verify.sh:183` runs, wrapped in `timeout 300`.

**(a) Genuine red?** Yes, twice over.

*Against the base* — the gate reverts the production hunks and keeps every `template/tests/*`
hunk (`run-verify.sh:214-217`):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_attempt_ownership.py
Ran 19 tests in 1.167s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 19 tests in 1.104s
FAILED (failures=14, errors=1)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

No `unittest.loader._FailedTest` on the red leg, i.e. the module imported: it names no symbol
this patch adds anywhere (module-level imports are `pdca_harness.leaves`, `.assemble`,
`.state`, `.config`; the trailer string is read back off a log the harness wrote,
`_harness_trailer`, never typed in). The 4 cases green on both legs are the deliberate
no-regression guards (live artifact still harvested at all three sites; a leaf that exits 0
writing nothing still degrades to today's placeholder *and today's class*; a spent leaf is
still not re-run; a spent log still reads "RAN AND FAILED" to `assemble`).

*Against iteration v1* — the real question this round. I reverted the production hunks to
v1's patch, kept **this** test file, and ran the module: 6 failures, and they are exactly the
five findings.

```
FAIL test_a_kill_during_a_flush_destroys_neither_the_marker_nor_the_predecessor   → finding 1
FAIL test_a_kill_before_the_outcome_is_filed_is_recovered_not_retired             → finding 2
FAIL test_the_preserved_death_is_filed_as_the_infra_death_it_was                  → finding 3
FAIL test_a_dead_attempts_artifact_is_not_harvested_at_either_site (advisory)     → finding 3/4
FAIL test_a_dead_attempts_artifact_is_not_harvested_at_either_site (plan-advisory)→ finding 3/4
FAIL test_the_missing_review_note_calls_an_interrupted_leaf_not_yet_run           → finding 5
```

(Finding 4's other half, the unlink-failure case, is green on v1 by construction — v1 had the
fail-closed branch and no test for it — and red on the base, which is what a blindness gap
looks like when it is closed.)

**(b) Production path?** Yes. Nothing is re-implemented and no production function is replaced
by a stub of itself: `leaves._invoke_leaf_resilient → _invoke → progress.run_with_heartbeat →
subprocess` with a **real** `python3` child as the leaf; `leaves._run_review_sandboxed`,
`leaves._run_advisory_sandboxed` and `leaves._run_plan_advisory_sandboxed` (real `tempfile`
sandboxes, real `shutil.copy2` harvests, real `*_unavailable` placeholders) for the ownership
legs; the real `leaves.review_never_ran` and the real `assemble._missing_review_text` for the
recovery legs. The stand-ins are only the retry backoff's wall clock (`time.sleep`, skipped
only for waits ≥ 1 s so `progress`' own 0.05 s poll still really sleeps) and **fault
injection at the syscall boundary** — `Path.write_text` / `Path.unlink` refusing or dying on
one named file. That injects the fault; it does not stand in for any logic under test (the
production write path, including which file it writes and in what order, is what decides the
outcome — which is why v1 fails these cases and this patch passes them).

**(c) Fixture includes the fault?** Yes. The dead attempt is a real child process that writes
a real truncated artifact **into the real sandbox** and then dies transiently (stderr only,
no stream event — the shipped transient signal); the retry is a real second spawn; nothing
curates the residue out. The in-flight log asserted on is the actual bytes on disk while
attempt 2 ran, read by the leaf itself from *inside* the retry loop. The two kill cases put
the process's death **inside** the write that the criterion is about — the flush is caught
after its truncate (`_Kill`, a `BaseException`, so no `except Exception` in the harness gets
to soften it), and the harvest is caught before the placeholder lands — rather than asserting
on a hand-built "what a kill would have left" file. The impersonation legs feed back the
harness's own trailer, taken from a log it produced in the same run, so they cannot pass by
drifting from the production constant.

## Commit-readiness

* No formatter/linter config ships in the target (`CONTRIBUTING.md:21-29` asks only "keep the
  offline suite green"); no `.pre-commit-config.yaml`, no ruff/black/flake8 config anywhere in
  the tree. Longest added line is 96 chars, inside the file's existing envelope (`leaves.py`
  already has lines to 110).
* T3 (`run-suite.sh`): `PDCA-EVIDENCE: root suite OK, driver suite OK` — root 7/7, driver
  1777/1777, `test_leaf_resilience.py` untouched and green inside that run.
* C5 (`run-prod-path.py`): `PDCA-EVIDENCE: 1 added driver-suite test(s) import the production
  package 'pdca_harness'` — a genuinely **new** test file, so C5 has something to assert.
* T2 (`run-docs-check.sh`): `docs lint clean, site render + link audit clean`.
* Suite output hygiene: the new module writes **0 bytes** to stdout (measured:
  `python -m unittest tests.test_attempt_ownership 2>/dev/null | wc -c` → 0).
* One untracked scratch file remains in the worktree root,
  `.mine_test_attempt_ownership.py` — the copy of the test used to hold it constant
  while the production hunks were swapped to v1's for the differential above. It is
  untracked, so it is in neither `patch.diff` nor any commit; the harness's own sweep
  reclaims it with the worktree.
* No PR pushed, opened, or marked ready.

## External dependencies

None beyond the base toolchain (stdlib Python + git), as the brief predicted: every leaf in
the test is a `python3` child, so the whole file runs offline, headless, with no vendor CLI,
no API key, no network and no container. Nothing to declare.
