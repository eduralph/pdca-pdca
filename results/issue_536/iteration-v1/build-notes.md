# Build notes — issue 536 (attempt-owned leaf records and harvests)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All edits made in the cycle
worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`; every `path:line` below is that tree
**after** the patch unless it says "base".

## What the patch does, region by region

Seven regions in one module plus two prose blocks in `driver.py`. Base line numbers are the
brief's; post-patch line numbers are this tree's.

1. **`_invoke_leaf_resilient` gains `artifact=`** — `leaves.py:681` (base `:673-682`).
   One new keyword, defaulting to `None`; a caller that passes nothing gets today's
   behaviour byte for byte.
2. **The loop body flushes per attempt and withdraws a dead attempt's residue** —
   `leaves.py:721` (`withdrew`), `:745` (`_withdraw_residue`), `:752-753` (`may_retry` +
   `recorded`), replacing the post-loop `error_log.write_text` at base `:720`.
   `may_retry = transient and attempt < attempts and owned` is the shipped rule
   (`not transient or attempt == attempts ⇒ stop`, base `:713`) with two **narrowing**
   conditions; the attempt budget, the backoff schedule, the retry notice, the staleness
   clear (base `:698-702`) and the `_memory_log_for` derivation are untouched.
3. **Success path** — `leaves.py:725-740`. Normally the log is removed (it may now exist,
   because attempt 1's record was already flushed), so "a success leaves no error log
   behind" still holds. The one exception is the case the criterion (ii) names: this
   attempt exited 0 having written **no** artifact while a dead predecessor's artifact was
   withdrawn, so the log is the only surviving copy of that text and the caller is about to
   report "produced no artifact" — the records are re-flushed **without** the in-flight
   marker (the loop finished; a log still claiming otherwise would read as interrupted).
4. **The in-flight trailer and its two defences** — `leaves.py:770` (`_LEAF_IN_FLIGHT`),
   `:773` (`_defang_in_flight`), `:784` (`_write_attempt_records`), `:813`
   (`leaf_run_incomplete`, matched as the **last non-blank line, whole**), `:832`
   (`_leaf_ran_and_failed`).
5. **`_format_leaf_attempt` is defanged** — `leaves.py:895` (base `:727`). This is the
   defect round 3 shipped: the stderr tail was embedded raw, so a leaf's own text could
   write the harness's trailer for it. `_defang_in_flight` replaces only the marker
   substring, so the #420 memory post-mortem that rides in on `output`
   (`leaves.py:663-665`) survives byte for byte.
6. **`_withdraw_residue`** — `leaves.py:841` (`_RESIDUE_KEEP`), `:844`. Preserves the dead
   attempt's text in that attempt's record, then unlinks; **fails closed** (`ok=False` ⇒ no
   further attempt over a path the wrapper no longer owns).
7. **The three harvest sites** — reviewer `leaves.py:2679, 2687, 2701-2706` (base
   `:2507, :2519-2523`); advisory `:3028, :3037-3039` (base `:2840, :2851-2854`);
   plan-advisory `:3329, :3338-3341` (base `:3142, :3152-3155`). Each passes `artifact=`
   and each "produced no artifact" branch now passes `error_log=` to the
   `*_unavailable(...)` placeholder it already paired with — the shape the failure branch
   already used (`:2695`, `:3034`, `:3335`), not a second one.
   `_unavailable_classification` only names the log **if it exists**
   (`leaves.py:2790-2791`), so a run with no dead attempt writes the byte-identical
   placeholder of today.
8. **The two recovery discriminators** — `review_never_ran` `leaves.py:2278` (base
   `:2103-2104`) and `run_advisory_leaves(only_missing=True)` `leaves.py:2986` (base
   `:2800-2801`). Both now ask `_leaf_ran_and_failed`, so an in-flight log recovers exactly
   like a missing one.
9. **`driver.py` prose** — `:123-129` (`advance`'s CHECKED comment) and `:152-160`
   (`_resume_interrupted_check`'s docstring). Comment-only: they are where the meaning of
   "an error log exists" is documented, and that meaning changed.

## What I deliberately did not touch

* **The builder** (`do_build`, `_do_build_command`, `_build_prompt`, `_stub_build`) —
  sibling child-2. No `retry_note` / `retry_when` / attempts-stamping from the round-3
  prior art was carried over; those exist only to serve the builder retry and the honest
  failed-Do report.
* **`progress.py`, `LeafError.transient`, any signal-death predicate** — #533/#510. The
  retry set is reused exactly as shipped (`getattr(exc, "transient", False)`,
  `leaves.py:748`), and I did not adopt #533's `"on transient infra"` wording anywhere.
* **`test_leaf_resilience.py`** — untouched, as the criterion requires. Verified green
  rather than edited (its five cases use `assertIn`, so a per-attempt flush and a trailer
  line do not disturb them): `PDCA-EVIDENCE: root suite OK, driver suite OK` from
  `engine/scripts/run-suite.sh`.
* **`assemble._missing_review_text`** (`assemble.py:406-432`) — it splits its wording on a
  bare `.exists()` too, so an in-flight log would read "RAN AND FAILED" there. Left alone
  on purpose: (a) on every driver path `_resume_interrupted_check` recovers the interrupted
  leaf *before* `assemble_summary` runs (`driver.py:128-130`), so this text is only
  reachable by assembling an interrupted bundle by hand; (b) **both** wordings are
  NEEDS-HUMAN and both block accept under C6, so the invariant the criterion protects — a
  bundle cannot reach sign-off with no review of the diff — holds either way; (c) the
  criterion names exactly two discriminators, and widening to a third reader would be
  scope, not the invariant. Flagged here so the human can call it if they disagree; the
  delta would be one line plus a docstring sentence.

## Alternatives considered, with their cost

* **Timestamp/PID ownership instead of withdrawal** (stat the artifact's mtime, compare
  against the attempt's start): rejected on correctness, not size. A dead attempt that
  wrote its file 200 ms before dying and a live attempt that rewrote it are separated by
  milliseconds on a fast leaf, and a leaf whose clock or filesystem lies (a sandbox on a
  tmpfs with coarse mtime granularity) silently misclassifies. Withdrawal needs no clock:
  after a failed attempt the file is *by construction* that attempt's, because the wrapper
  removed anything earlier.
* **Delete the residue without preserving it** (`artifact.unlink()`, no record): 6 lines
  shorter than `_withdraw_residue` (`leaves.py:844-878` would collapse to the `unlink` and
  the fail-closed return). Rejected: the sandbox is a `TemporaryDirectory` that dies with
  the run, so deleting is the one action that makes a real verdict unrecoverable while the
  placeholder tells the operator none was produced — the exact failure the invariant names.
* **Marker as a substring test only** (no `_defang_in_flight`): saves 4 lines
  (`leaves.py:773-781`) plus one call at `:895` and one at `:874`. Rejected: it is the
  hole round 3 shipped. With a substring test *or* an undefanged tail, a reviewer of this
  very file whose stderr or verdict quotes the marker makes a spent log read as
  interrupted, and #369 re-runs (and re-pays for) a leaf that already gave up. Both
  defences are kept and the test drives both doors.
* **Flush best-effort and retry regardless** (drop the `recorded` gate, `leaves.py:753`):
  saves 1 line of control flow and the `bool` return of `_write_attempt_records`.
  Rejected: it re-opens the precise window the slice exists to close — attempt N+1 running
  while nothing on disk explains attempt N. The gate is what makes (i) a guarantee rather
  than an intention.
* **A `pdca.toml` knob for the residue cap / attempts**: out of scope per the brief; the
  shipped defaults are reused and `_RESIDUE_KEEP` is a module constant.

## Refuting my own test (forced questions)

Runner used throughout: the project's own gate scripts —
`engine/scripts/run-verify.sh` (C4 red→green) and `engine/scripts/run-suite.sh` (T3), both
with `$PDCA_BUNDLE` / `$PDCA_WORKTREE` set. No hand-rolled invocation.

**(a) Genuine red?** Yes — proven by the gate itself, which reverts the production hunks
and keeps every `template/tests/*` hunk (`run-verify.sh:214-217`):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_attempt_ownership.py
Ran 10 tests in 0.660s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 10 tests in 0.539s
FAILED (failures=6, errors=1)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

7 of the 10 cases are red on the base, one per criterion leg:
`test_each_attempts_account_is_on_disk_before_the_next_one_starts`
(`'attempt 1' not found in '(absent)'` — read from inside attempt 2),
`test_a_retry_never_starts_without_its_predecessors_account_on_disk` (the base's post-loop
`write_text` raises the refused `OSError` straight out of the wrapper),
`test_a_dead_attempts_half_written_verdict_is_not_adopted_as_the_review`
(`'1.1 Root cause | PA' unexpectedly found` — the base harvests the dead attempt's file as
the review), `test_the_withdrawn_verdict_is_readable_in_the_bundle_afterwards`,
`test_a_leaf_interrupted_mid_retry_is_recovered_not_retired`,
`test_a_dead_attempts_artifact_ending_in_the_trailer_is_not_the_trailer` and
`test_a_leaf_whose_stderr_quotes_the_trailer_is_still_read_as_spent`.
No `unittest.loader._FailedTest` appeared, i.e. the module imported on the red leg (it
imports only pre-existing API: `pdca_harness.leaves`, `pdca_harness.state`,
`pdca_harness.config`) and names **no** symbol this patch adds, anywhere — the trailer
string itself is read back off a log the harness wrote (`_harness_trailer`), never typed
into the test.
The other three cases are deliberate no-regression guards for criterion (iii)/(vi) and are
green on both legs: the live attempt's artifact is still harvested, a leaf that exits 0
writing nothing still degrades to today's placeholder with no error log, and a leaf that
spent its attempts is still not re-run.

**(b) Production path?** Yes. Nothing is re-implemented and no production function is
replaced by a stub of itself:
`leaves._invoke_leaf_resilient → leaves._invoke → progress.run_with_heartbeat → subprocess`
with a **real** `python3` child as the leaf, and
`leaves._run_review_sandboxed` (the real harvest site, real `tempfile` sandbox, real
`shutil.copy2` harvest, real `_review_unavailable` placeholder) for the ownership legs, and
the real `leaves.review_never_ran` for the recovery legs. The only stand-ins are
`time.sleep` (the backoff's wall clock, skipped only for waits ≥ 1s so `progress`' own
0.05s poll still really sleeps) and, in one case, `Path.write_text` refusing exactly one
filename to model a bundle that cannot be written.

**(c) Fixture includes the fault?** Yes. The dead attempt is a real child process that
writes a real truncated `check-review.md` **into the real sandbox** and then dies
transiently (stderr only, no stream event — the shipped transient signal), and the retry
that follows is a real second spawn; nothing curates the residue out of the fixture. The
in-flight log asserted on is the actual bytes on disk at the moment attempt 2 ran, read by
the leaf itself from inside the retry loop — the only vantage point from which "flushed as
it happened" is distinguishable from "written once the loop ended". The impersonation legs
feed back the harness's own trailer string, taken from a log the harness produced in the
same run, so they cannot pass by drifting from the production constant.

## Commit-readiness

* No formatter/linter config ships in the target (`CONTRIBUTING.md` names only "keep the
  offline suite green"); no `.pre-commit-config.yaml`. Longest added line is 95 chars,
  inside the file's existing envelope (`leaves.py` already has lines to 110).
* T3 (`run-suite.sh`): `PDCA-EVIDENCE: root suite OK, driver suite OK`.
* C5 (`run-prod-path.py`): `PDCA-EVIDENCE: 1 added driver-suite test(s) import the
  production package 'pdca_harness'` — the new file is a **new** test file, so C5 has
  something to assert this round.
* Suite output hygiene (`test_suite_output_hygiene.py`'s rule): the new module writes **0
  bytes** to stdout (every driven print is redirected in-test).
* No PR pushed, opened, or marked ready.

## External dependencies

None beyond the base toolchain (stdlib Python + git), as the brief predicted: every leaf in
the test is a `python3` child, so the whole file runs offline, headless, with no vendor CLI,
no API key, no network and no container. Nothing to declare.
