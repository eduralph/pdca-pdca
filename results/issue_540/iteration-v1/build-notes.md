# Build notes — issue 540 (per-attempt record + one error-log meaning)

Target: `eduralph/pdca-harness`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`, base `pdca-integration/main` @ `d2938ef`, which
carries `acb214a` + issue_538). Every `leaves.py` line the brief cites resolved identically
on this base (`:720` the post-loop write, `:724-730` `_format_leaf_attempt`, `:698-702` the
staleness clear, `:2103-2104`, `:2800-2801`).

## What I changed and why (path:line = post-patch, in the worktree)

The two halves of the defect are one change, exactly as the brief frames it: flushing the
record early is only safe once "this file exists" stops meaning "the leaf ran and FAILED".

**1. The point of truth — `state.py`.** `state` is the only module `leaves`, `assemble` and
`driver` all import (`leaves` imports `assemble`, so the predicate could not live in
`leaves` without a cycle), and it already owns the *spelling* of `REVIEW_ERROR_LOG`
(`state.py:61-67`) "so the writer, the CHECKED-resume check and the §6 wording split share
one spelling". This slice puts the file's *meaning* in the same place:

- `state.py:83` `UNSETTLED_MARKER` — the line an unfinished record carries **last**.
- `state.py:169` `leaf_ran_and_failed(error_log)` — the single predicate all four readers
  consult. False for absent, unreadable, or still-marked. Unreadable errs toward re-running:
  a needless re-run costs a leaf, a wrong "ran and failed" costs the review of the diff.
- `state.py:188` `_unsettled(text)` — recognition: the **last non-blank line, whole**
  (`.strip()`-equal), never a substring, never mid-line. Round 3's mid-line token was not
  the failure mode; the failure mode is a leaf ending its stderr with that line.
- `state.py:203` `unsettled_record()` / `state.py:209` `neutralize_leaf_text()` — the writer
  and the defusal, beside the marker because they are one decision.

**2. The writer — `leaves._invoke_leaf_resilient`.** `leaves.py:734` flushes the records
**before the backoff sleep**, i.e. before the next attempt spawns. The post-loop write
(`leaves.py:742`) is byte-identical to the shipped line — the loop still settles by writing
the records *without* the marker, so the attempt budget, the transient rule, the backoff
schedule, the `:698-702` staleness clear and `_memory_log_for` are untouched.

`leaves.py:746` `_flush_attempt_records` swallows `OSError` (criterion 5): the shipped stop
rule stays the only stop rule, the un-flushed records stay in hand, and the final write
still persists them — strictly no worse than the base, which persisted nothing until then.
v5's opposite choice measured 3 attempts → 1.

**3. One thing the brief did not enumerate, which the flush forces —
`leaves.py:715-722`.** Once a failed attempt writes its record, a *later* attempt that
**succeeds** would leave that record behind, and criterion 4 says a successful leaf leaves
no error log. The base could not have this bug (nothing was written until the loop ended)
and the shipped suite cannot catch it (`test_leaf_resilience.py:83`/`:91` succeed on
attempt **1**, so no flush ever happened). So success now restores "no error log", under
`contextlib.suppress(OSError)` — a leaf that worked must not be failed by the cleanup of its
own post-mortem. Covered by `test_a_leaf_that_recovers_on_retry_leaves_no_record_behind`.

**4. Impersonation — `leaves.py:772`.** `_format_leaf_attempt` embeds the tail through
`state.neutralize_leaf_text`. Only a line that *is* the marker is rewritten (suffixed
`(quoted from the leaf's own output …)`); everything else is byte-identical, so the #420
memory post-mortem still rides `output` into the same log intact. Rewritten, never dropped:
the leaf's account survives, it just cannot be the log's marker line.
Note `leaves.py:1817` (the builder's single-record write, #537's territory) also calls
`_format_leaf_attempt` — I did not touch it; it inherits the same defusal, which is a no-op
for any text that does not contain the marker line.

**5. The four readers.** `leaves.review_never_ran` `:2151`; `run_advisory_leaves`
`only_missing` `:2851`; `assemble._missing_review_text` `:420` (+ the never-ran wording at
`:428-438`, which now names **both** shapes: no log at all, and an unsettled log left by a
death inside the retry loop); `driver._resume_interrupted_check` `:153-161` docstring and
`:177-179` the operator line, plus the CHECKED-dispatch comment `driver.py:123-128`. No
caller signature changed; the unsettled state's whole lifetime is inside the wrapper.

## Alternatives ruled out (with the cost, not an adjective)

- **A sidecar marker file** (`check-review.attempts-pending`). Rejected on the brief's own
  design constraint *and* on cost: it is a second file whose absence/presence is a second
  discriminator — the readers would then test two paths instead of one, exactly the drift
  the "single point of truth" constraint exists to prevent. It also needs its own cleanup on
  success and its own entry in `state.DOWNSTREAM_GLOBS` (`state.py:141`) or it survives an
  iterate. Concretely ~4 extra call sites (2 unlinks, 1 glob, 1 predicate) versus 0 here.
- **A leading marker (first line) instead of a trailing one.** Cheaper to *write* but not to
  *trust*: the records are appended, so a leading marker must be re-stripped and re-written
  on every flush, and the settled write would have to rewrite the head. The trailing form
  makes settling a pure removal of the tail line, which is what keeps `leaves.py:742`
  byte-identical to the shipped line.
- **Making the flush fail-closed** (abort the run when the record cannot be written).
  Rejected by the brief's DECIDED-HERE item and confirmed mechanically: it narrows the
  retry contract (`test_leaf_resilience.py:62` asserts `_runs() == 3`), and criterion 4 and
  a fail-closed withdrawal cannot both hold. `test_an_unwritable_record_does_not_narrow_the_retry_contract`
  now pins this: with the record path unwritable the leaf still runs 3 attempts.
- **Recognising the marker as a substring / anywhere in the file.** One line cheaper, and
  exactly the hole criterion 3 names: a leaf that prints the marker anywhere in its stderr
  would then be re-run forever as "interrupted". Recognition is last-line-whole; the
  neutraliser closes the remaining path.

Deliberately untouched (brief's out-of-scope): the artifact/harvest half (`:2519-2523`,
`:2851-2854`, `:3152-3155` — child-2), `assemble.py:80-89` leaf-status labels, the builder
path (`_do_build_command`, `do_build`'s capture, `_build_prompt`, `_stub_build`),
`progress.py` / `LeafError.transient` (#539), and #539's `"on transient infra"` wording —
the strings at `leaves.py:736-739` are left exactly as shipped, since #539 owns them.
No `template/tests/fixtures/` was created; `test_leaf_resilience.py` is not in the diff.

## Refuting my own test

- **(a) Genuine red?** Yes — proven by the project's own C4 gate, not by reasoning:
  `./engine/scripts/run-verify.sh` reverts the production hunks and keeps the test.
  Green leg `Ran 8 tests … OK`; red leg `Ran 8 tests … FAILED (failures=5)`, no
  `unittest.loader._FailedTest` (module-level imports are all pre-existing API:
  `assemble`, `leaves`, `state`, `Config`, `LeafConfig`) →
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The five that go red are
  `test_attempt_two_finds_attempt_ones_account`,
  `test_reviewer_with_an_unsettled_record_is_recovered`,
  `test_advisory_with_an_unsettled_record_is_not_skipped`,
  `test_a_leaf_emitting_that_line_last_does_not_read_as_unsettled`,
  `test_the_line_is_recognised_only_whole_and_last`. The other three are
  contract-preservation guards that pass on the base **by design** (settled record still
  retires the leaf; a recovered leaf leaves no record; an unwritable record does not cost
  attempts) — they exist to catch *my* change breaking the shipped contract.
  I also refuted each production hunk **individually** (revert one, re-run):
  drop the flush → 5 red; drop `state.leaf_ran_and_failed` in `review_never_ran` → 2 red;
  drop it in `only_missing` → 1 red; drop `neutralize_leaf_text` → 1 red (the impersonation
  leg specifically); drop the success-unlink → 1 red. No hunk is unbound.
- **(b) Production path?** Yes. Every leg drives the shipped functions —
  `leaves._invoke_leaf_resilient` (the real retry loop, spawning real subprocesses through
  `progress.run_with_heartbeat`), `leaves.review_never_ran`, `leaves.run_advisory_leaves`,
  `assemble._missing_review_text`. Nothing is re-implemented or mocked; the test names no
  symbol this patch adds (it derives the marker from the bytes production wrote).
- **(c) Fixture includes the fault?** Yes, and it is *taken from* the fault rather than
  hand-built: the mid-retry fixture is produced by the stub leaf copying the real error-log
  path aside **on its second invocation** — byte-for-byte the state a mid-retry kill leaves,
  so it cannot drift from the production shape. The impersonation leg reads the marker off
  those same bytes and has the leaf emit exactly that line, alone, last on stderr; the
  settled log it produces is then handed to the real reader.

## Evidence run through the project's runners (never hand-rolled)

- `./engine/scripts/run-verify.sh` (C4, gating) → `PDCA-EVIDENCE: C4 PASS`.
- `./engine/scripts/run-suite.sh` (T3) → `root suite OK, driver suite OK`
  (7 template-repo tests + 1800 driver tests, `test_leaf_resilience.py` and
  `test_check_resume.py` green **untouched**).
- `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` (C5) →
  `PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package 'pdca_harness'`
  — the new-file requirement the brief flagged (three rounds of appends printed "patch adds
  no new test file") is satisfied.
- `./engine/scripts/run-docs-check.sh` (T2) → `docs lint clean, site render + link audit clean`.

Commit-readiness: the target repo defines no formatter/linter hook (no
`.pre-commit-config.yaml`, no `.git/hooks/*`, no ruff/black config; its CI workflows are
docs-render/lint + linked-issue only, all run above). Added lines stay within the file's
existing wrap (max added line 94 cols, checked mechanically).

No external dependency was needed: every leg is a `sys.executable -c` stub leaf — no vendor
CLI, no API key, no network, no container.
