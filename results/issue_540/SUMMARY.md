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

Review of the fix that persists each failed leaf attempt before retry while keeping unfinished, settled, and leaf-authored error-log states unambiguous and crash-safe.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is observable and bounded: retain each attempt before retry, recover every unfinished account, preserve retry/success behavior, and require no external service; the production boundary is explicit at `template/src/pdca_harness/leaves.py:683`. |
| C2 Reproduction (red pre-fix) | PASS | With the tracked production changes stashed and the new behavioral test retained, the base imported successfully but failed 15 assertions, including the missing attempt-1 snapshot at `template/tests/test_attempt_ownership.py:232` and interrupted-leaf recovery at `template/tests/test_attempt_ownership.py:320`. |
| C3 Change | PASS | The patch flushes before backoff at `template/src/pdca_harness/leaves.py:735`, atomically replaces records at `template/src/pdca_harness/leaves.py:765`, and gives all readers the one settlement predicate at `template/src/pdca_harness/state.py:182`. |
| C4 Verification (red→green) | PASS | Restoring the patch changed the reproduced 15-failure red to 26/26 focused tests green, and the independent full driver suite passed 1,803 tests (2 skipped); the torn-write assertion exercises a real `RLIMIT_FSIZE` failure at `template/tests/test_attempt_ownership.py:254`. |
| C5 Causal adequacy | PASS | This removes the delayed/in-place write cause through pre-retry atomic replacement and positive settlement, rather than adding a capability probe or optional-path guard; ambiguous records deliberately fail toward recovery at `template/src/pdca_harness/state.py:182`. |
| T1 Structure | PASS | Ownership is separated coherently: record construction/classification lives in `state`, atomic persistence in `leaves`, and the reviewer and advisory recovery paths both delegate to the shared predicate at `template/src/pdca_harness/leaves.py:2176` and `template/src/pdca_harness/leaves.py:2875`. |
| T2 Shape | PASS | `git diff --check`, docs lint, static-site render, and internal-link audit passed locally; the frozen host-CI parity log independently reports the same clean shape. |
| T3 Runtime | PASS | The full offline driver suite passed locally, and the frozen T3 log shows the 7 root render/update-compat tests and driver suite passed with the required gate toolchain; local absence of `copier` did not substitute for that evidence. |
| T4 Contribution | N/A | `pr-description.md` is intentionally not drafted during Check, and the deferred gate states that the substantive contribution audit reruns at publish. |
| T5 Judgment | PASS | The affected-path prior-art scan covered all 226 closed/merged and 8 open PRs, found the relevant merged lineage (#140 and #417), no closed-unmerged competing patch, and no upstream equivalent; the current change remains within the four-reader/error-record slice shown at `template/src/pdca_harness/assemble.py:406`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Maintainer must accept the operational trade-off that any ambiguous or older markerless account is re-run rather than retired—this protects review completeness but may spend one extra leaf run after an upgrade; that bias is explicit at `template/src/pdca_harness/state.py:187`. |

### Advisory — adversary

# Adversarial review — #540 (per-attempt record + one error-log meaning)

Method: re-ran the C4 green leg on the target (`tests.test_attempt_ownership` 11/11 OK),
re-read the frozen red leg in `gate-logs/C4-verify.log`, ran seven mutants against the new
suite (all killed), re-ran the six neighbouring suites (90 tests, OK), then went hunting for
the input that breaks the fix. One landed.

- NEEDS-HUMAN [impl] — **The impersonation defence is defeated by a truncation at the one
  offset it names.** `state.neutralize_leaf_text` defuses a leaf-emitted marker line by
  APPENDING the quote note *after* the marker on the same line
  (`template/src/pdca_harness/state.py:242`, suffix at `:100`), so the bytes
  `…ran and FAILED -----` are still a complete prefix of that line. Its own docstring
  (`state.py:231-234`) says the exposure it exists to close is "a record cut short right
  after such a line … would read as spent and retire a leaf that was only interrupted" —
  and that is exactly what still happens. Measured end-to-end on the target through the
  **production** writer and all four production readers: drive `leaves._invoke_leaf_resilient`
  with a stub whose stderr's last line is the settlement line, take the mid-retry record the
  production flush wrote, cut it at the end of the marker text (offset 88 or 89 of the
  neutralised line — a bare `-----` or `----- ` both strip to the marker):
  `state.leaf_ran_and_failed` → **True**, `leaves.review_never_ran` (`leaves.py:2176-2177`)
  → **False**, `assemble._missing_review_text` (`assemble.py:420`) → "RAN AND FAILED",
  `run_advisory_leaves(only_missing=True)` (`leaves.py:2874-2877`) → **skips the leaf**. A
  reviewer the death window merely interrupted is retired and the bundle reaches sign-off
  with no review of the diff — the precise catastrophe this slice exists to prevent, and a
  direct counterexample to the unconditional fail-direction claim at `state.py:186-189`
  ("torn off part-way by a dead write … fail towards RE-RUNNING") and to brief criterion 3.
  Fix is one expression: put the note BEFORE the line (`f"{_QUOTED_SUFFIX} {line}"`) or
  rewrite the marker text itself — measured, both leave **zero** dangerous cut offsets
  (shipped form: 2). Reachability, stated honestly: `_replace_record` (`leaves.py:778-781`)
  makes the harness's own writes rename-atomic, so a SIGKILL can no longer tear the file;
  what remains is a crash/power-loss with unflushed data (`_replace_record` does **not**
  fsync the temp before `os.replace`, so its "all-or-nothing" docstring at `leaves.py:765-776`
  is a rename claim, not a durability one), an externally truncated log, or any future writer
  of these records. Narrow — but the code, the brief and the test all assert the property
  unconditionally.
- NEEDS-HUMAN [impl] — **The test that claims to pin that property only pins the adjacent
  cut.** `template/tests/test_attempt_ownership.py:381-391` builds its torn record with
  `_before_last_line` (`:222-225`), which cuts at the *start* of the last line — i.e. it
  removes the harness's own closing line and leaves the neutralised leaf line **whole**, the
  one shape the append does defuse. The sibling leg at `:330-339` walks several cuts
  (`settled[:head]`, `settled[:head + len//2]`) but drives the *non*-impostor stub, so no cut
  can land inside a neutralised marker line. The missing leg is the intersection of the two:
  impostor stub + a cut at `mid.index(line) + len(line)`. It fails today.
- NEEDS-HUMAN [impl] — **The new sibling temp is orphanable inside the bundle and matches no
  ignore rule.** `leaves.py:778` writes `.{error_log.name}.partial`; the OSError path unlinks
  it, a killed run does not. `template/.gitignore.jinja:17` ignores `*.log` (so the error logs
  themselves are never committed) but nothing matches `.check-review.error.log.partial`, so
  `record.py:111` (`git add -A -- <bundle>`) would sweep an orphan into a records commit/PR.
  The file's own convention is explicit about this class — `.pdca-prompt-*.md` (`:25`),
  `.pdca-handoff-*.json` (`:32`), `.act-reviewed.tmp.*` (`:37`) each exist because "a killed
  session can orphan one", two of them with a test asserting the pattern tracks the code
  constant. `state.DOWNSTREAM_GLOBS` (`state.py:154`) and `driver._archive_iteration`
  (`driver.py:430`) also won't archive or clear it.
- Evidence-quality note (not a defect, no adjudication needed): three of the C4 red-leg
  failures are `AttributeError: module 'pdca_harness.state' has no attribute 'settled_record'`
  from the *modified* `test_check_resume.py` (`gate-logs/C4-verify.log:398`, `:407`, `:416`) — symbol
  absence, the same class of non-evidence `run-verify.sh:229-232` rejects at import time,
  just surfacing at attribute access instead. The verdict stands on
  `test_attempt_ownership.py` alone, which went genuinely red (15 behavioural failures,
  `C4-verify.log:378-380`) and which I re-ran green on the target; those three should not be
  counted as independent red evidence for the check-resume readers.

## Attempted and could not refute

- **Seven mutants, all killed** by the new suite: neutralisation → identity; last-line test →
  substring; drop the success-path unlink (`leaves.py:722-723`); `_replace_record` → plain
  `write_text`; `_flush_attempt_records` no longer best-effort (`leaves.py:758-762`);
  `unfinished_record` emitting the settled marker; empty log reading as settled.
- **Criterion 5 (the retry contract) holds under a non-OSError.** I looked for an exception
  the flush's `except OSError` would not catch and that would cut the loop from 3 attempts to
  1 — the obvious candidate is `UnicodeEncodeError` on a surrogate-bearing tail, but
  `progress.py:169-171` spawns with `text=True` and strict decoding, so a leaf's output can
  never carry a lone surrogate. Attempts stay 3 on the unwritable-dir path (re-ran).
- **No fifth reader speaking the old meaning.** Repo-wide grep for `*.error.log` /
  `REVIEW_ERROR_LOG` finds only the four converted readers plus non-discriminating uses
  (`leaves.py:2681` log_ref, `driver.py:430` archiving, `state.py:296` cycle evidence — which
  now flips True slightly earlier, in the safe direction). Plan-advisory logs
  (`leaves.py:3216`) have no existence reader; `build.error.log` is off this path.
- **Criterion 4 intact.** `test_leaf_resilience.py` is untouched by the diff and green
  (re-ran); the success path still leaves no error log; the #420 memory post-mortem still
  rides `output` through the neutralisation (`leaves.py:664-666`).
- **The staleness clear (`leaves.py:706`) deleting the mid-retry post-mortem when the
  recovery re-runs the leaf** is real, but the brief pre-decided it under criterion 4 and the
  previous round already routed it to Act — not re-filed here.

### Advisory — code-review

# Advisory code review — issue #540 (per-attempt record + one error-log meaning)

Scope: correctness bugs introduced by this diff, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (base `acb214a` + patch). C4 gate log confirms a genuine
red→green (production hunks reverted: 15 failures + 3 errors; applied: 11+10 tests OK).

Traced all four named readers (`leaves.review_never_ran`,
`leaves.run_advisory_leaves(only_missing=True)`, `assemble._missing_review_text`,
`driver._resume_interrupted_check`) plus the two other, unnamed callers of
`_invoke_leaf_resilient` (`_run_advisory_sandboxed` for plan-advisory leaves, and the
`_unavailable_classification` display helper) — none was left speaking the old
"presence == ran-and-failed" sentence, and no fifth semantic reader was missed. The
carried-forward round-1 BLOCKING/SECONDARY findings (torn-write safety, fail-towards-
re-running default) are both present and each has a pinning test
(`test_a_record_a_dying_write_cut_off_leaves_the_last_whole_one`,
`test_a_torn_or_empty_record_recovers_its_leaf`) that fails on the reverted tree per the
C4 log.

No blocking correctness bug found. Two small, non-blocking observations:

- `leaves.py:778` (`_replace_record`) names its sibling temp file
  `.{error_log.name}.partial` with no per-writer discriminator (pid, etc.). The repo's
  existing atomic-write idiom for exactly this shape — `act.py:266-268,324` (`mark_reviewed`)
  and its `.tmp.{os.getpid()}` siblings at `act.py:324,369,724` — deliberately pid-suffixes
  the temp name "so one writer's `os.replace` can never consume another's" when two
  processes can overlap. `_invoke_leaf_resilient` has no equivalent exclusivity guard of
  its own (nothing in `leaves.py`/`driver.py` locks a bundle against a second concurrent
  invocation), so if the same `error_log` is ever targeted by two processes at once (e.g.
  an operator re-running Check while a prior session is still alive, not merely killed),
  one process's in-flight `tmp.write_text` could be truncated by the other's, and the
  `os.replace` that follows could publish a mixed/short record — the exact failure mode
  `_replace_record`'s docstring says it exists to prevent. Whether concurrent invocation
  of the same leaf/bundle is actually reachable (vs. already excluded by driver/worktree
  exclusivity elsewhere) isn't answerable from this diff alone.
  - NEEDS-HUMAN — confirm whether two live processes can ever target the same bundle's
    error log concurrently; if so, `_replace_record` should pid-suffix its temp name like
    `act.py` already does, for the same reason.

- `leaves.py:706` clears only `error_log` at the top of `_invoke_leaf_resilient`
  ("clear any stale tail from a prior cycle run"); it doesn't clear a stray
  `.{name}.partial` sibling. `_replace_record`'s own except-block cleans up the temp file
  when the *process is alive* to catch the failure (verified by the torn-write test's
  `stray == []` assertion), but a process killed in the narrow window between
  `tmp.write_text` succeeding and `os.replace` running — the same "killed mid-retry"
  class of event this whole slice defends against — would leave that `.partial` file
  behind, and nothing ever unlinks it on the next invocation. It's inert litter (no reader
  consults `.partial`, so `state.leaf_ran_and_failed` and friends are unaffected), so this
  is not a correctness bug in the fix's tracked contract, just a minor gap against the
  "a partial sibling is never left in the bundle" claim in `_replace_record`'s own
  docstring (`leaves.py:775`).
  - NEEDS-HUMAN [impl] — optionally have `_invoke_leaf_resilient` also unlink
    `error_log.with_name(f".{error_log.name}.partial")` alongside its existing
    `error_log.unlink(missing_ok=True)` at `leaves.py:706`, so a stray temp from an
    earlier kill doesn't linger indefinitely.

Everything else checked out: `_replace_record`'s all-or-nothing write directly satisfies
the round-1 BLOCKING finding (sibling temp + `os.replace`, same-directory so no EXDEV
risk); `state.leaf_ran_and_failed`/`_last_nonblank` fail towards re-running for every
ambiguous shape (absent, unreadable, empty, torn, unfinished) per the round-1 SECONDARY
finding; `neutralize_leaf_text` only rewrites a line that IS the marker (whitespace
aside), never a substring, so the #420 memory-telemetry text riding `output` survives
untouched unless it happens to equal the marker outright; the unsettled state's lifetime
is correctly scoped inside `_invoke_leaf_resilient` (settled on failure, discarded via
`error_log.unlink` on a recovering success at `leaves.py:722-723`) with no caller change;
and the retry contract (attempt count, transient rule, backoff schedule) is unchanged —
`_flush_attempt_records` is `except OSError`-only and best-effort, matching criterion 5.
No reuse/duplication or efficiency concern beyond the temp-naming point above.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Maintainer must accept the operational trade-off that any ambiguous or older markerless account is re-run rather than retired—this protects review completeness but may spend one extra leaf run after an upgrade; that bias is explicit at `template/src/pdca_harness/state.py:187`.
- [x] **The impersonation defence is defeated by a truncation at the one
- [x] **The test that claims to pin that property only pins the adjacent
- [x] **The new sibling temp is orphanable inside the bundle and matches no
- [x] confirm whether two live processes can ever target the same bundle's
- [x] optionally have `_invoke_leaf_resilient` also unlink

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Accepted with a follow-up bug to file on the tracker: the adversary's truncation-impersonation residue — `state.neutralize_leaf_text` appends the quote note AFTER the marker, so a cut at the marker offset still reads as settled; plus the missing test leg (impostor stub + cut at end of the neutralised line), the orphanable `.{name}.partial` temp with no ignore rule, and the open concurrency question on pid-suffixing the temp.
