# Result — issue 540 / per-attempt-record-and-one-error-log-meaning

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch applied to the target base, all of:
  1. **Each failed attempt's record is on disk before the next attempt starts.** A leaf
     observing the bundle during attempt 2 finds attempt 1's account already there; today it
     finds no file. A run killed mid-retry therefore leaves a post-mortem.
  2. **An unsettled account does not read as "ran and FAILED" to any reader.** All four
     readers under `Citations expected` agree because they consult **one** point of truth
     rather than each testing the file's existence: an error log left by a leaf whose
     attempts are not yet spent recovers the leaf exactly as an absent one does
     (`review_never_ran` → True; `only_missing` does not skip it), and the operator-facing
     wording in `assemble._missing_review_text` / `driver._resume_interrupted_check` names
     both shapes instead of asserting only one.
  3. **A leaf's own text cannot impersonate that distinction.** Whatever distinguishes an
     unsettled account from a spent one is neutralised in the captured stderr tail
     `_format_leaf_attempt` embeds, and is recognised only as the log's **last non-blank
     line, alone** — never as a substring, never mid-line. (Round 3 shipped this leg with the
     token embedded mid-line, which is not the failure mode.)
  4. **The shipped resilience contract is unchanged.** Attempt count, the transient rule, the
     backoff schedule, the staleness clear (`:698-702`) and the `_memory_log_for` derivation
     exactly as shipped; a **successful** leaf still leaves no error log behind; the #420
     memory-telemetry post-mortem still rides `output` into the same log and survives the
     neutralisation intact; and `template/tests/test_leaf_resilience.py` stays green
     **untouched** — verified at Plan, not assumed: its error-log *content* assertions are
     `assertIn` (`:64`, `:74`) and its *existence* assertions read the FINAL state only
     (`:63` after a spent retry, `:83`/`:91` after success).
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed.** A record flush
     that fails (read-only bundle dir, ENOSPC) **must not end the run**: the shipped stop rule
     is the only stop rule, and the un-flushed records stay in hand so the loop's final write
     still persists them — strictly no worse than the base, which persists nothing until the
     end. v5 measured the opposite choice at 3 attempts → 1 and it was the finding that could
     not be closed, because criterion (4) and a fail-closed withdrawal cannot both hold.
     Mechanical check: `test_leaf_resilience.py:62` asserts `_runs() == 3`, and a Plan-time
     run of the base measured exactly 3.
- Repo + branch target: eduralph/pdca-harness @ main   (base `acb214a`; every
  `path:line` re-verified against it at Plan)
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing #540: persist every failed reviewer/advisory attempt before retry while keeping unfinished accounts recoverable and impossible for leaf output to impersonate.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required persistence, settlement, impersonation, and unchanged-retry outcomes are concrete and independently exercisable in the behavior tests at `template/tests/test_attempt_ownership.py:129`. |
| C2 Reproduction (red pre-fix) | PASS | With production hunks stashed and the new test retained, the independent base run failed 5/8 because attempt 2 found no attempt-1 snapshot, directly reproducing the defect asserted at `template/tests/test_attempt_ownership.py:133`. |
| C3 Change | FAIL | The change does not preserve unfinished state across a late write failure: `_flush_attempt_records` catches an `OSError` after `write_text` may already have truncated the log, while the classifier treats the resulting empty/torn readable log as settled and can suppress recovery (`template/src/pdca_harness/leaves.py:755`, `template/src/pdca_harness/state.py:181`). |
| C4 Verification (red→green) | PASS | The independent stash/restore run was red 5/8 on the base and green 8/8 patched, matching the frozen gate's red→green result for the production-driving test (`template/tests/test_attempt_ownership.py:104`). |
| C5 Causal adequacy | FAIL | The last-line marker addresses the ordinary retry window but not the brief's ENOSPC/process-death category: a failed or interrupted truncating marker write can leave no marker and is then misread as attempts spent, recreating sign-off without review (`template/src/pdca_harness/leaves.py:756`, `template/src/pdca_harness/state.py:185`). |
| T1 Structure | PASS | One shared settlement predicate owns the meaning and the reviewer/advisory recovery readers consume it, avoiding the prior four-way existence-test drift (`template/src/pdca_harness/state.py:169`, `template/src/pdca_harness/leaves.py:2150`, `template/src/pdca_harness/leaves.py:2850`). |
| T2 Shape | PASS | Direct docs lint and 22-page render/link audit were clean, agreeing with the frozen shape evidence at `gate-logs/T2-docs.log:16`. |
| T3 Runtime | PASS | The patched driver suite independently passed 1,800 tests with 2 skips; the frozen gate also records 7/7 root render/update tests and 1,800 driver tests passing (`gate-logs/T3-suite.log:27`, `gate-logs/T3-suite.log:1653`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check, and the frozen row says the mandatory substantive audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Contribution disposition is owed after the crash-consistency defect is corrected or explicitly rejected—accepting the current ordinary truncating write risks retiring an interrupted reviewer; affected-path history found relevant merged PR #417 and no rejected-PR overlap (`template/src/pdca_harness/leaves.py:755`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Exercise a real transient reviewer, terminate the harness after attempt 1, rerun `pdca advance`, and confirm the prior account remains readable and the reviewer is recovered—the stub suite does not establish real interruption/ENOSPC fitness (`template/src/pdca_harness/driver.py:176`). |

### Advisory — adversary

# Advisory review — adversary (issue #540)

Lens: refute the red→green evidence and the reviewer's verdict; find the input that breaks
the fix. Re-ran everything below against `$PDCA_TARGET` (a copy of the target tree in this
leaf's own sandbox — the target itself was only read).

## Findings

- NEEDS-HUMAN [impl] — **The record the patch writes to survive a death is itself not
  death-safe, and it fails towards the unsafe verdict.** `template/src/pdca_harness/leaves.py:756`
  writes the unsettled record with `Path.write_text`, which is `open(…, "w")` (O_TRUNC) →
  write → close: the file passes through a **0-byte** state and, for a record larger than the
  text buffer, through **prefix** states — and the settlement marker is the LAST thing
  written. Any such partial state reads as *settled*, i.e. "the leaf ran and FAILED"
  (`state.py:185` → `leaves.py:2151` → `assemble.py:420`). Two concrete cases, both measured
  on the target tree:
  1. **Partial write, no race at all.** Under `RLIMIT_FSIZE` (the faithful ENOSPC/quota
     analogue — the exact failure `_flush_attempt_records`' docstring, `leaves.py:748-752`,
     says it is best-effort for) the shipped `leaves._flush_attempt_records` left 2048 bytes
     of attempt 1 on disk with no marker; `state.leaf_ran_and_failed` → `True`,
     `leaves.review_never_ran` → `False`, `assemble._missing_review_text` → "# Advisory
     review MISSING — the reviewer RAN AND FAILED".
  2. **0-byte file** (a SIGKILL/OOM landing between the truncate and the data) — same three
     answers.
  In both, the reviewer that still had 2 attempts left is **retired instead of re-run**, and
  the bundle reaches sign-off with no review of the diff — the precise catastrophe the brief
  names. On the base the same scenario leaves *no* file and `review_never_ran` → `True`
  (recovered), so `leaves.py:753`'s claim "strictly no worse than before" is false for the
  torn-write case, and `state.py:178`'s stated fail-direction ("Unreadable errs the same way,
  towards re-running") does not hold for *truncated* — truncated errs towards retiring.
  Fixable inside the function the patch added: write a sibling temp file and `os.replace()`
  it into place (still best-effort, still `except OSError`), so the record is all-or-nothing.

- NEEDS-HUMAN — **The post-mortem criterion 1 creates is deleted by the recovery criterion 2
  mandates, before any reader sees it.** `leaves.py:705` (`error_log.unlink(missing_ok=True)`,
  frozen by criterion 4) is the first statement of `_invoke_leaf_resilient`, and
  `driver.py:129-131` runs `_resume_interrupted_check` **before** `assemble.assemble_summary`.
  So on the engine's own path the sequence is: unsettled log → recovery re-runs the reviewer →
  the unsettled account is unlinked. The new §6 sentence at `assemble.py:433-434` ("the
  `check-review.error.log` in this bundle is the unfinished account of the attempts it had
  made by then — read it for the post-mortem") therefore names a file the same `advance` has
  just deleted; and since a leaf that runs and spends its attempts always writes a
  `check-review.md` placeholder (`leaves.py:2610`), that branch is in practice reachable
  only when a human calls assemble by hand on a bundle nobody advanced. The mid-retry
  post-mortem is real on disk, but only for a human who inspects the killed bundle *before*
  the next advance — narrower than "a run killed mid-retry therefore leaves a post-mortem"
  reads. Whether that is enough (or whether the staleness clear should preserve/rename the
  unsettled record) is a scope call the brief pre-decided under criterion 4, so it needs a
  human, not a rebuild.

- `template/src/pdca_harness/leaves.py:762-772` — noted, not blocking: `_format_leaf_attempt`
  is shared with the **builder** path (`leaves.py:1817`, inside the `do_build` capture the
  brief fenced off), so `build.error.log` now also gets marker-shaped lines rewritten with the
  quoted suffix. Harmless (nothing reads `build.error.log`'s settlement) and arguably more
  consistent, but it is a behaviour change inside a fenced region, reached indirectly.

## Refutations attempted and failed

- **The red→green evidence is genuine and reproduced independently.** Green: 8/8 in the target
  tree. Red: reverse-applied only the four production hunks (`git diff -- template/src`),
  kept the test — 5 failures, matching `gate-logs/C4-verify.log`. The test drives the shipped
  `leaves._invoke_leaf_resilient` / `review_never_ran` / `run_advisory_leaves` /
  `assemble._missing_review_text`; nothing is re-implemented (C5's claim holds).
- **The tests are not green for the wrong reason.** Four mutants, each caught: marker dropped
  from `unsettled_record` (3 failures); `neutralize_leaf_text` made identity (1 failure —
  `test_a_leaf_emitting_that_line_last_does_not_read_as_unsettled`); `_unsettled` made a
  substring test (2 failures); success-path `unlink` removed (1 failure). The suite pins each
  leg it claims.
- **Could not break the writer/reader pair.** `state.neutralize_leaf_text:209` and
  `state._unsettled:188` split with the same `str.splitlines()` and compare with the same
  `.strip()`, and the neutralizer rejoins on `"\n"`, so no line the reader would call a marker
  escapes the writer: probed trailing `\r`/`\x0b`/`\x1c` separators, NBSP-for-space variants,
  NUL suffixes, marker + trailing blank lines, marker mid-line, and the record's own framing
  — all symmetric. The one body that skips neutralization, the `(no output captured)
  {type}: {exc}` fallback (`leaves.py:772-773`), is single-line and prefixed, and its text
  derives from argv/OS, not from the leaf.
- **Could not narrow the retry contract.** With the flush failing on every attempt the loop
  still ran 3 attempts (measured), attempt count/transient rule/backoff untouched; the flush
  catches only `OSError`, but the captured text cannot carry surrogates (`progress.py:170`
  spawns with `text=True`, strict decoding), so no `UnicodeEncodeError` escapes it.
- **No fifth reader left speaking the old meaning.** Repo-wide grep finds no other consumer of
  `check-review.error.log` / `check-advisory-*.error.log` (the remaining `.exists()` at
  `leaves.py:2655` only decorates a placeholder written after the wrapper returned, i.e.
  always settled). Neighbouring suites re-run green here: `test_leaf_resilience`,
  `test_check_resume`, `test_terminal_error_retention`, `test_build_error_log`,
  `test_leaf_memory_log`, `test_cycle_evidence` — 90 tests, OK, with `test_leaf_resilience.py`
  untouched as criterion 4 requires.

### Advisory — code-review

# Advisory code review — correctness & reuse lens (issue #540 patch)

Reviewed `template/src/pdca_harness/{state,leaves,driver,assemble}.py` and the new
`template/tests/test_attempt_ownership.py`, grounded on the patched target tree.

## Correctness

- No bugs found that the patch introduces. Specifically verified and clean:
  - All four readers named in the brief consistently switched from `.exists()` to
    `state.leaf_ran_and_failed(...)`: `leaves.py:2150-2151` (`review_never_ran`),
    `leaves.py:2850-2851` (`run_advisory_leaves(only_missing=True)`),
    `assemble.py:420` (`_missing_review_text`), and `driver.py:176`/`:182`
    (`_resume_interrupted_check`, via the two functions above). No fifth reader was
    missed — `leaves.py:2655` (`_unavailable_classification`'s `error_log.exists()`)
    is called only after `_invoke_leaf_resilient` has already returned (`leaves.py:2562-2564`,
    `:2889-2899`), i.e. after the log is always settled, so the raw existence check there
    is correctly out of the single-point-of-truth requirement's scope.
  - `state._unsettled` (`state.py:188-200`) and `state.neutralize_leaf_text`
    (`state.py:209-222`) are consistent and idempotent: neutralization runs once per
    attempt at format time (`leaves.py:772` inside `_format_leaf_attempt`), before a
    record ever reaches `unsettled_record` (`state.py:203-206`) or the final settled
    write (`leaves.py:742`), so a neutralized line can never be mistaken for the raw
    marker on a later read.
  - The success-path cleanup (`leaves.py:721-722`, new) correctly restores "no error
    log on success" now that a failed-then-recovered attempt may have left an unsettled
    file behind; the pre-existing pre-loop `error_log.unlink(missing_ok=True)`
    (`leaves.py:705`, untouched) still needs no such guard since nothing was written by
    that point in the old or new code.
  - `_flush_attempt_records` (`leaves.py:746-759`) and the test at
    `test_attempt_ownership.py:540-549` correctly demonstrate criterion 5: a flush
    failure is swallowed and does not shorten the attempt budget, while the final
    unguarded `write_text` (`leaves.py:742`) still raises on the same failure exactly as
    the pre-patch code did — confirmed by `gate-logs/C4-verify.log` showing the retry
    count reaching 3 before the propagated `OSError`.

## Reuse / simplification

- `state._unsettled`'s "last non-blank line" scan (`state.py:197-199`) has no existing
  sibling to reuse — the closest precedent in the codebase (e.g. `drift.py:37,43,91`'s
  `.splitlines()[-1:]`) takes the literal last line rather than skipping trailing blanks,
  which is a different (and here, required) semantic, so writing it fresh is justified,
  not a missed-reuse opportunity.
- No duplicated logic, no needless work in a hot path, no resource leaks or concurrency
  issues spotted; the extra `write_text` per transient attempt is bounded by `attempts`
  (≤2 extra writes for the shipped default of 3) and is the mechanism the brief asked for.

Nothing else stood out. The diff is clean on both lenses — no NEEDS-HUMAN items.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Contribution disposition is owed after the crash-consistency defect is corrected or explicitly rejected—accepting the current ordinary truncating write risks retiring an interrupted reviewer; affected-path history found relevant merged PR #417 and no rejected-PR overlap (`template/src/pdca_harness/leaves.py:755`).
- [ ] Validation — fitness-to-purpose — Exercise a real transient reviewer, terminate the harness after attempt 1, rerun `pdca advance`, and confirm the prior account remains readable and the reviewer is recovered—the stub suite does not establish real interruption/ENOSPC fitness (`template/src/pdca_harness/driver.py:176`).
- [ ] **The record the patch writes to survive a death is itself not
- [ ] **The post-mortem criterion 1 creates is deleted by the recovery criterion 2

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the advisory findings, not on the design: the slice is right-sized, the single-point-of-truth predicate is the right shape, and the red->green evidence held up under independent reproduction and four mutants. One local defect blocks it. 1. BLOCKING — make the unsettled-record write crash-safe. `_flush_attempt_records` (leaves.py) uses `Path.write_text`, i.e. open(O_TRUNC) -> write -> close, and the UNSETTLED marker is the LAST thing written. So the file passes through a 0-byte state and, for records larger than the buffer, prefix states — and any such partial state has no trailing marker, so `state.leaf_ran_and_failed` returns True and a reviewer that still had attempts left is RETIRED instead of re-run. Measured on the target tree under RLIMIT_FSIZE (2048 bytes, no marker) and as a 0-byte file. On the base the same scenario leaves no file and the leaf is recovered, so the docstring's "strictly no worse than before" is false for the torn-write case, and state.py's "unreadable errs towards re-running" does not hold for TRUNCATED — truncated errs towards retiring. That is the exact catastrophe the slice exists to prevent, reintroduced by the write it added. Fix inside the function the patch already added: write a sibling temp file and `os.replace()` it into place, so the record is all-or-nothing. Keep it best-effort — still `except OSError`, still no narrowing of the retry contract (criterion 5). Add a leg pinning it: a torn/0-byte error log must recover its leaf, not retire it. 2. SECONDARY — the settled/unsettled asymmetry that made (1) dangerous is worth removing at the source: an EMPTY or contentless log currently reads as settled by default. Consider making `_unsettled`/`leaf_ran_and_failed` fail towards re-running for a log with no recognisable attempt record at all, consistent with the stated fail-direction. Not in scope for this rebuild: the observation that the mid-retry post-mortem is unlinked by `_invoke_leaf_resilient`'s staleness clear before `assemble` runs. The brief pre-decided that under criterion 4, and the adversary flagged it as a human scope call, not a rebuild item. Leave criterion 4 honoured and `test_leaf_resilience.py` untouched; carried to Act.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
