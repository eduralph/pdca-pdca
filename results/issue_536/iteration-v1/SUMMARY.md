# Result — issue 536 / attempt-owned-leaf-records-and-harvests

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch: (i) each failed attempt's record is on disk
  **before** the next attempt starts, so a retried leaf — and a post-mortem of a run killed
  mid-retry — can read the predecessor's account instead of a file that does not exist yet;
  (ii) at all three harvest sites, no artifact written by a **dead** attempt is copied out as
  a **successful** attempt's output, and a dead attempt's text is *preserved* in the bundle's
  `*.error.log` rather than merely deleted — a real verdict must not be destroyed while the
  operator is told none was produced; (iii) the **live** attempt's own artifact is still
  harvested exactly as today, and a leaf that exits 0 having written nothing still degrades
  to today's placeholder; (iv) no dead attempt's captured stderr and no quoted artifact text
  can impersonate the harness's own in-flight trailer: whatever marker distinguishes an
  interrupted log from a spent one is neutralised in **both** the quoted-artifact text and
  the `_format_leaf_attempt` stderr tail, and is matched as the log's **last non-blank line,
  alone** — never as a substring; (v) an in-flight log does not read as "the leaf ran and
  FAILED" to the #369 recovery discriminators (`review_never_ran` at `:2094`, its test at
  `:2103-2104`; `run_advisory_leaves(only_missing=True)` at `:2800-2801`), so a reviewer the
  death window merely interrupted is still re-run and a bundle cannot reach sign-off with no
  review of the diff; (vi) nothing else changes: the shipped resilience contract holds
  unchanged (attempt count, backoff, the staleness clear at `:698-702`, the `_memory_log_for`
  derivation), a success still leaves no error log behind, the #420 memory-telemetry
  post-mortem still rides `output` into the same log **and survives the neutralisation
  intact**, and `template/tests/test_leaf_resilience.py` stays green **untouched** (its five
  tests assert with `assertIn`, so a per-attempt flush and a trailer do not disturb them —
  verify that rather than editing the file).
- Repo + branch target: eduralph/pdca-harness @ main (base `acb214a`; every `path:line`
  above was re-verified against it while this proposal was written)
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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

Reviewing the fix that makes failed leaf-attempt records durable, prevents dead-attempt artifacts from being harvested, and preserves interrupted-leaf recovery.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | `brief.md` defines the ownership invariant, offline falsification, all three harvest sites, recovery semantics, and explicit sibling exclusions. |
| C2 Reproduction (red pre-fix) | PASS | Independent pre-fix execution produced 6 assertion failures and 1 error in the behavioral cases that observe retry-time logging and dead-artifact harvesting (`template/tests/test_attempt_ownership.py:176`, `template/tests/test_attempt_ownership.py:260`). |
| C3 Change | PASS | The change stays within the specified wrapper, recovery discriminators, three retried harvests, explanatory driver prose, and one new behavioral test file (`template/src/pdca_harness/leaves.py:745`, `template/src/pdca_harness/leaves.py:2685`). |
| C4 Verification (red→green) | PASS | Independent stash/reapply verification reproduced red on the base and 10/10 green with the fix; the untouched resilience suite was also 5/5 green (`template/tests/test_attempt_ownership.py:176`, `template/tests/test_leaf_resilience.py:56`). |
| C5 Causal adequacy | FAIL | A silent successful retry after residue withdrawal rewrites the log without the in-flight marker, so a kill before placeholder creation makes the recovery discriminator classify an artifact-less interrupted Check as spent and leaves the no-review window open (`template/src/pdca_harness/leaves.py:734`, `template/src/pdca_harness/leaves.py:832`). |
| T1 Structure | PASS | Attempt-record persistence, marker interpretation, and residue withdrawal are separated into bounded helpers and composed by the intended wrapper (`template/src/pdca_harness/leaves.py:784`, `template/src/pdca_harness/leaves.py:813`, `template/src/pdca_harness/leaves.py:844`). |
| T2 Shape | FAIL | The shared error-log contract still says a log exists only when retries are exhausted, but the patch intentionally creates it mid-retry and can retain it after a successful no-artifact retry; this stale contract can mislead every consumer of the shared constant (`template/src/pdca_harness/state.py:61`). |
| T3 Runtime | FAIL | A production-path simulation of fail-with-artifact → silent success → death-before-placeholder observed `artifact_exists=False`, `error_log_incomplete=False`, and `review_never_ran=False`, so crash recovery does not satisfy the stated runtime invariant (`template/src/pdca_harness/leaves.py:734`, `template/src/pdca_harness/leaves.py:2277`). |
| T4 Contribution | N/A | The contribution artifact is absent by design at Check; the frozen gate says the substantive PR-description audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Determine overlap risk for the affected `driver.py` recovery path — the supplied prior-art section audits `leaves.py` by path but not this second modified production file, and the self-contained target has no merged/closed PR history to settle it mechanically (`template/src/pdca_harness/driver.py:117`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the change is operationally fit for crash recovery — the configured suites are green, but the independently exercised post-success/pre-placeholder death window can still reach sign-off without a review artifact. |

### Advisory — adversary

# Adversarial review — attempt-owned leaf records and harvests (#536 / parent #506)

Evidence re-run here, offline, on the target at `$PDCA_TARGET` (python3 3.14, stdlib only):
red leg = production hunks reverted, `template/tests/*` kept → **6 failures + 1 error**
(3 of the 10 are guards that legitimately pass on the base); green leg = patched tree →
**10 OK**; `tests/test_leaf_resilience.py` untouched → **5 OK**. C4's `red without the fix,
green with it` reproduces. The two impersonation legs are load-bearing (remove
`_defang_in_flight` and both go red), so the added tests are not tautologies. Findings
below are what survived an attempt to break the fix.

- **NEEDS-HUMAN [impl] — the per-attempt flush is not crash-atomic, which re-opens the very
  window criterion (v) exists to close.** `template/src/pdca_harness/leaves.py:800`
  (`error_log.write_text(body, …)`) truncates first and appends the `_LEAF_IN_FLIGHT`
  trailer **last**. A kill between the truncate and the trailer bytes — SIGKILL, the OOM
  kill the #420 telemetry exists to explain — leaves a log with **no trailer** (0 bytes in
  the common case). Concrete failing case, verified against the target: with
  `check-review.error.log` containing `""` **or** `"----- attempt 1 — exit 1 -----\nboom\n"`,
  `leaves.leaf_run_incomplete()` → `False` and `leaves._leaf_ran_and_failed()`
  (`leaves.py:835`) → `True`, so `review_never_ran` (`leaves.py:2277`) → `False` and
  `driver.py:176` never recovers the reviewer — the bundle reaches sign-off with **no review
  of the diff**. On the base the same kill left *no* log at all and the leaf **was**
  recovered, so this is a new (narrow) failure mode introduced by the flush, not pre-existing
  debt. The repo already ships the crash-atomic idiom this needs — temp sibling +
  `os.replace` (`src/pdca_harness/act.py:326`) — and `_write_attempt_records` does not use it.

- **NEEDS-HUMAN — the patch's own recovery path destroys the dead-attempt text criterion (ii)
  went to the trouble of preserving.** An in-flight log is precisely the log that makes
  `review_never_ran` say "recover me" (`leaves.py:2277` → `driver.py:176` →
  `leaves.run_review`), and the first statement of the re-run is the staleness clear
  `error_log.unlink(missing_ok=True)` at `leaves.py:714`. Verified end to end on the target:
  attempt 1 writes a complete verdict and dies transiently → the mid-retry log is in-flight
  and holds that verdict → `review_never_ran` is `True` → after the recovery run the verdict
  is **gone** (`"the real verdict" in log` → `False`). The sandbox that held the original
  died with the run, so if the recovery run then fails the operator is told "the reviewer
  produced no verdict" while the only surviving copy of a real one has been deleted — the
  exact harm the brief's criterion (ii) rationale names. Not marked `[impl]` because closing
  it means either archiving the log before the clear or changing the staleness clear, and
  criterion (vi) freezes that clear: a scope call, not an iteration.

- **NEEDS-HUMAN [impl] — the new "successful attempt wrote nothing after a withdrawal" branch
  files an infra death as a substantive one.** `leaves.py:2704` (and its twins `:3039`,
  `:3340`) passes `error_log=` but leaves `failure=` at the default `_FAIL_SUBSTANTIVE`, so
  `_unavailable_classification` (`leaves.py:2769-2792`) stamps
  `<!-- pdca:leaf-status human-empty -->` and prints *"**substantive — needs a human.** The
  leaf ran but did not yield a usable verdict; do not assume an infra blip"* — one sentence
  before pointing at a log that reads `overloaded_error 529` plus a withdrawn partial verdict
  (reproduced verbatim on the target). `assemble` keys the §6 row off that marker, so a
  transient blip now presents to the operator as a reviewer that reviewed and failed — the
  inversion #278's marker exists to prevent. The wrapper only ever retries *transient*
  failures, so a log that survives a **successful** return is by construction an infra death:
  the branch can classify it without new information.

- **NEEDS-HUMAN [impl] — the third reader of "an error log means the leaf ran and FAILED" was
  left un-#506-aware.** `src/pdca_harness/assemble.py:417` still splits on a bare
  `(d / state.REVIEW_ERROR_LOG).exists()`, so an in-flight log renders *"the reviewer RAN AND
  FAILED … Fix the cause, then re-run"* for a leaf the death window merely interrupted, while
  `leaves.py:2277` and `leaves.py:2986` now say the opposite about the same file. Honest
  caveat: I could **not** construct a live failure — `driver.py:130` recovers before
  `driver.py:132` assembles, and every `run_review` path leaves a `check-review.md` behind,
  so the branch is currently shadowed. Filed as the one reader the semantic change missed,
  cheap to align (`leaves._leaf_ran_and_failed`), not as a reachable bug.

- **NEEDS-HUMAN [impl] — two of the three harvest sites the brief names are asserted by
  inspection only.** `template/tests/test_attempt_ownership.py:255,301` drive only
  `_run_review_sandboxed`; nothing exercises `leaves.py:3028` (advisory) or `leaves.py:3329`
  (plan-advisory). I drove both myself through the production functions and they behave
  correctly (dead text withdrawn, preserved in the log, placeholder written) — so this is
  test blindness, not a live defect. Its cost is concrete: had either site been wired to the
  **bundle** path (`advisory_artifact(d, leaf_id)`) instead of the sandbox `out`, a dead
  attempt would `unlink()` the previous round's shipped artifact and the suite would stay
  green. One parametrized case over `_run_advisory_sandboxed` closes it.

**Attempted to refute and could not:** (a) the criterion-(iv) impersonation leg — I ran 30
payloads through the production path (dead-attempt artifact **and** captured stderr): bare
marker, space/tab-padded, `\r`-, form-feed-, vertical-tab-, U+2028- and U+0085-separated,
marker + ZWSP / BOM / NUL, BOM + marker, no trailing newline, trailing blank lines, and a
21 000-char artifact past the `_RESIDUE_KEEP` truncation. `review_never_ran` stayed `False`
in every one — `_defang_in_flight` (`leaves.py:781`) plus the whole-line last-non-blank match
(`leaves.py:829`) hold, and the #420 post-mortem survives verbatim. (b) The fail-closed
`owned` stop: a leaf that `mkdir`s its artifact path costs itself two of three attempts
(`leaves.py:752`), but the wrapper stays fail-closed, prints why, and leaves a non-in-flight
log — and the brief explicitly blesses this mechanism. (c) The success path: I could not
construct a case reaching `leaves.py:734` with a dead attempt's file still standing (an
un-withdrawable artifact breaks the loop first). (d) `_format_leaf_attempt`'s
`(no output captured) …` fallback is not leaf-controllable, so it is no second door.

### Advisory — code-review

# Check advisory — code review (correctness bugs + reuse/simplification)

Read against target `template/src/pdca_harness/leaves.py` / `driver.py` (issue #536,
attempt-owned leaf records and harvests). Traced the wrapper (`_invoke_leaf_resilient`,
`leaves.py:673-761`), the new helpers (`_write_attempt_records`, `leaf_run_incomplete`,
`_leaf_ran_and_failed`, `_withdraw_residue`, `_defang_in_flight`, `:764-898`), all three
harvest sites (`:2678-2705`, `:3023-3039`, `:3325-3341`) and the two recovery
discriminators (`review_never_ran` `:2261-2278`, `run_advisory_leaves` `:2965-2986`), plus
`driver.py`'s comment-only changes at `:112-119` / `:150-163`. Cross-checked against
`gate-logs/C4-verify.log` (genuine 7/10-fail red → 10/10-pass green) and
`gate-logs/T3-suite.log` (1768 tests OK, `test_leaf_resilience.py` unmodified and still
green in the full run). No correctness bug in the shipped logic was found; two are
advisory-only nits below.

- The `owned=False` fail-closed branch of `_withdraw_residue` (`leaves.py:875-883` —
  `artifact.unlink()` raising `OSError`, which forces `may_retry = False` and stops the
  retry loop at `leaves.py:752`) is never exercised by
  `template/tests/test_attempt_ownership.py`. The symmetric OSError-on-write branch of
  `_write_attempt_records` *is* covered
  (`test_a_retry_never_starts_without_its_predecessors_account_on_disk`, mocking
  `Path.write_text`), but nothing mocks `Path.unlink` to drive the artifact-can't-be-
  withdrawn path, so the fail-closed guarantee the docstring claims at
  `leaves.py:860-862` ("the caller stops retrying rather than run another attempt over a
  path it no longer owns") is asserted in prose only. A test mirroring the existing
  `refuse_the_log` pattern against `Path.unlink` would close this.
  NEEDS-HUMAN [impl] — add a test that exercises `_withdraw_residue`'s unlink-failure
  branch, the one asymmetric leg of the two documented "fail closed" contingencies.

- Minor duplication: the "report to stderr, but never let a broken pipe mask the
  leaf's own failure" guard (`with contextlib.suppress(OSError): print(...)`) is
  written out twice, structurally identically, in `_write_attempt_records`
  (`leaves.py:806-808`) and `_withdraw_residue` (`leaves.py:878-881`) — both new in
  this patch. A tiny `_report(msg: str) -> None` helper would collapse both call sites
  to one line each; not worth blocking on, since the two messages differ enough that
  inlining is defensible, but it's a straightforward simplification if this file is
  touched again.

- Minor observational nit, not a bug: when retries stop because `_withdraw_residue`
  could not remove a dead attempt's artifact (`owned=False`, `leaves.py:752`), the
  exception returned to the caller is still the underlying `LeafError` with its
  original `.transient` flag intact. `_failure_class` (`leaves.py:2716-2731`) reads
  that flag and classifies the placeholder as `_FAIL_TRANSIENT` ("safe to re-run"),
  even though the actual reason this attempt was the last one is an unwithdrawable
  file on disk — a condition a plain re-run over the same sandbox lane would likely hit
  again. Narrow (requires an OS-level `unlink` failure on the sandbox artifact) and not
  worth gating on, but worth a human's awareness since it's a slightly misleading
  operator-facing message in that corner.

No dead code, resource leak, off-by-one, or API misuse found; the per-attempt flush,
withdrawal, defang, and the two discriminator updates are consistent with each other
and with the brief's six success-criterion legs, and `test_leaf_resilience.py` is
untouched and stays green per the full-suite gate log.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Determine overlap risk for the affected `driver.py` recovery path — the supplied prior-art section audits `leaves.py` by path but not this second modified production file, and the self-contained target has no merged/closed PR history to settle it mechanically (`template/src/pdca_harness/driver.py:117`).
- [ ] Validation — fitness-to-purpose — Decide whether the change is operationally fit for crash recovery — the configured suites are green, but the independently exercised post-success/pre-placeholder death window can still reach sign-off without a review artifact.

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
- Iteration delta (if iterating): Rejected on the crash-recovery findings, not on approach or slicing. The mechanism is right — C4 red→green was independently reproduced, the defang + whole-last-line match survived 30 impersonation payloads, and test_leaf_resilience.py stayed untouched and green. Same slice, same design; close the findings below. What to change: 1. Make the per-attempt flush crash-atomic. `_write_attempt_records` (`leaves.py:800`) truncates first and appends the `_LEAF_IN_FLIGHT` trailer last, so a kill between the two writes leaves an unmarked (commonly 0-byte) log. That reads as "ran and failed" to `_leaf_ran_and_failed` (`:835`), `review_never_ran` (`:2277`) returns False, `driver.py:176` never recovers the reviewer, and the bundle can reach sign-off with no review of the diff. The base left no log at all in that window and DID recover, so this is a new failure mode the patch introduces. Use the crash-atomic idiom the repo already ships: temp sibling + `os.replace` (`act.py:326`). 2. Close the same window on the success path. The reviewer's C5/T3 FAILs (`leaves.py:734`, `:832`) are the post-success/pre-placeholder leg of (1): a silent successful retry after a withdrawal re-flushes the log without the marker, and a kill before the placeholder is written yields artifact absent + non-in-flight log + `review_never_ran` False. Sequence the re-flush and the placeholder so no ordering of the kill leaves an interrupted Check looking spent. 3. Classify an infra death as one. The new "succeeded having written nothing after a withdrawal" branch (`leaves.py:2704`, twins `:3039`, `:3340`) passes `error_log=` but leaves `failure=` at the `_FAIL_SUBSTANTIVE` default, so `_unavailable_classification` stamps `human-empty` and tells the operator "substantive — needs a human" over a log reading `overloaded_error 529`. That is the inversion #278's marker exists to prevent. The wrapper only retries transient failures, so a log surviving a successful return is by construction an infra death — the branch can classify it without new information. 4. Close the two test-blindness gaps the adversary and the code review named; both are cheap and both are the kind of gap that would let a real regression stay green: - one parametrized case over `_run_advisory_sandboxed` covering the advisory (`leaves.py:3028`) and plan-advisory (`:3329`) harvest sites — today only `_run_review_sandboxed` is driven, so wiring either site to the bundle path instead of the sandbox `out` would unlink a shipped artifact and the suite would stay green; - a `Path.unlink`-failure test for `_withdraw_residue`'s fail-closed branch (`leaves.py:875-883`), mirroring the existing `refuse_the_log` pattern — the symmetric write-failure leg is covered, this one is asserted in prose only. 5. Align the third reader of "an error log means the leaf ran and FAILED": `assemble.py:417` still splits on a bare `.exists()`. Currently shadowed, not a reachable bug — but it now contradicts `leaves.py:2277` and `:2986` about the same file. Use `leaves._leaf_ran_and_failed`. Do NOT widen the slice: - Leave the staleness clear at `leaves.py:714` alone. The adversary is right that a recovery re-run deletes the dead attempt's preserved verdict, but criterion (vi) freezes that clear and fixing it is a scope change, not this iteration. Note it in build-notes as a known limitation and let Act decide. - Do not touch the retry set, `LeafError.transient`, `progress.py`, or the builder path — the sibling exclusions in the brief still hold. - Keep `test_leaf_resilience.py` untouched.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
