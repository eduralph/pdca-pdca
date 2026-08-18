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

Review of the fix that makes retrying reviewer/advisory leaves account for artifacts and errors by attempt, preserving dead-attempt evidence without harvesting it as a live verdict.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is falsifiable and scoped to the existing resilient wrapper plus its three harvest callers; those production entry points are identifiable at `template/src/pdca_harness/leaves.py:673`, `template/src/pdca_harness/leaves.py:2837`, `template/src/pdca_harness/leaves.py:3215`, and `template/src/pdca_harness/leaves.py:3520`. |
| C2 Reproduction (red pre-fix) | PASS | With only the four production hunks stashed and the behavioral test retained, the target produced 19 failures and 4 errors across the attempt-flush, dead-residue, and interrupted-recovery cases rooted at `template/tests/test_attempt_ownership.py:204`, `template/tests/test_attempt_ownership.py:334`, and `template/tests/test_attempt_ownership.py:677`. |
| C3 Change | PASS | The patch closes the required state transitions in order—persist the failed attempt, withdraw its artifact, and settle only after filing the outcome—at `template/src/pdca_harness/leaves.py:759`, `template/src/pdca_harness/leaves.py:763`, `template/src/pdca_harness/leaves.py:767`, and `template/src/pdca_harness/leaves.py:925`. |
| C4 Verification (red→green) | PASS | Independent target reruns gave 23 red assertions/errors without the production fix, then 26/26 ownership tests, 5/5 untouched resilience tests, and the full driver suite green after restoration; the executable test command is documented at `template/tests/test_attempt_ownership.py:43`. |
| C5 Causal adequacy | PASS | The change removes attempt-blind ownership at the wrapper and all three harvests rather than adding a capability probe or downstream symptom guard; the ownership handoff is enforced at `template/src/pdca_harness/leaves.py:752` and consumed at `template/src/pdca_harness/leaves.py:2856`, `template/src/pdca_harness/leaves.py:3227`, and `template/src/pdca_harness/leaves.py:3531`. |
| T1 Structure | PASS | Despite the large explanatory diff, each helper owns one retry-state concern—atomic record replacement, in-flight detection, settlement, residue capture, or withdrawal—at `template/src/pdca_harness/leaves.py:804`, `template/src/pdca_harness/leaves.py:898`, `template/src/pdca_harness/leaves.py:925`, `template/src/pdca_harness/leaves.py:981`, and `template/src/pdca_harness/leaves.py:1014`. |
| T2 Shape | PASS | `git diff --check`, docs lint, the 22-page site render/link audit, and the frozen host-CI parity evidence are clean; the new test remains a standalone production-path suite rather than modifying the frozen resilience test (`template/tests/test_attempt_ownership.py:25`). |
| T3 Runtime | PASS | The patched full offline driver suite exits 0, while focused tests exercise actual Python child processes through the production wrapper and all three harvest sites (`template/tests/test_attempt_ownership.py:32`); the frozen T3 log also records both root and driver suites green. |
| T4 Contribution | N/A | `pr-description.md` is absent by design during Check, and the frozen deferred row states that the substantive contribution-artifact audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged-history and closed/rejected-work overlap for every affected path—this disposable target has one commit and no remote refs, and the brief's path audit explicitly covers `leaves.py` but not all four other changed paths, so incomplete prior-art coverage could conceal conflicting work. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether marker-bearing error logs should operationally favor re-running an interrupted reviewer over retiring it—this determines whether avoiding a review-less sign-off justifies possible duplicate reviewer cost (`template/src/pdca_harness/leaves.py:919`, `template/src/pdca_harness/driver.py:177`). |

### Advisory — adversary

# Adversarial review — attempt-owned leaf records and harvests (#536, iteration 4)

Evidence re-run independently in a scratch copy of `$PDCA_TARGET` (python 3.14, offline):
green leg `26/26 OK`; red leg (production hunks reverted, test hunk kept) `19 failures + 4
errors` — the red→green in `check-gates.json` C4 is real, the five tests green on both legs
are the declared "nothing else changes" regressions (criterion iii/vi), not padding. The
tests drive real subprocesses through `leaves._invoke_leaf_resilient`,
`leaves._run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`,
`leaves.review_never_ran` and `assemble._missing_review_text` — production, not a copy. I
then ran 20 targeted mutations of the new logic against the full 1784-test driver suite and
9 impersonation payloads through the real wrapper. Three findings.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:912`: `leaf_run_incomplete`
  reads the log with `read_text(encoding="utf-8")` and guards only `except OSError`
  (`:913`), but its own docstring promises "Absent or **unreadable** ⇒ False" (`:909-910`).
  A log whose bytes are not valid UTF-8 raises `UnicodeDecodeError` (a `ValueError`) straight
  out of the discriminator. Reproduced: `log.write_bytes(b"----- attempt 1 - exit 1 -----\n\xff\xfe tail\n")`
  then `leaves.review_never_ran(d)` → `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff`.
  This is a **new** crash surface: `review_never_ran` (`:2430`) and
  `assemble._missing_review_text` (`assemble.py:425`) previously only `.exists()`-tested this
  file, and both now sit on `driver.advance`'s critical path — an undecodable log aborts the
  whole cycle instead of degrading. The reachable route is the patch's own premise: a log the
  **pre-patch** non-atomic `write_text` (base `leaves.py:720`) left truncated mid-multibyte by
  a kill, read after a harness upgrade. Note the inconsistency inside the same patch —
  `_residue_record` reads defensively (`:1004`, `errors="replace"`), this reader does not.
  One-line fix: `errors="replace"`, or `except (OSError, ValueError)`.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:1004`: `_residue_record` reads the
  **entire** dead attempt's artifact into the driver process and only then applies the
  `_RESIDUE_KEEP` bound (`:1007`), whose constant docstring (`:978`) justifies itself by "a
  runaway leaf could write an arbitrarily large file". Measured: a 200 MB `check-review.md`
  costs 420 MB peak allocation in the driver to produce a 20 161-char record. Worse, the read
  is called from *inside* the `except Exception` handler (`:758`, under the
  `# a failed leaf must never crash the cycle` guard at `:750`), and only `OSError` is caught
  (`:1005`) — so a `MemoryError` escapes the guard entirely. Demonstrated end-to-end with a
  stub reviewer that writes an artifact then dies transiently, with the artifact read raising
  `MemoryError`: `_run_review_sandboxed` propagates it and leaves **no `check-review.md`
  placeholder and no `check-review.error.log`** — precisely the "no artifact and no account"
  state this slice exists to eliminate, and it would abort `driver.advance`. The same escape
  applies at the two advisory sites, under the `# advisory must never crash the cycle`
  comment (`:3222`). The base never read this file at all (bare `.exists()` + streamed
  `shutil.copy2`), so both the allocation and the escape are patch-introduced. Fix: bounded
  read (`open(...).read(_RESIDUE_KEEP + 1)`) and widen the guard to `Exception`.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:3176`: the second of the two #369
  recovery discriminators the brief's criterion (v) names explicitly —
  `run_advisory_leaves(only_missing=True)` — is **not exercised by any test**. Reverting that
  line to the base's bare `advisory_error_log(d, leaf_id).exists()` leaves the whole driver
  suite green: `Ran 1784 tests ... OK (skipped=2)`. `test_attempt_ownership.py` calls
  `review_never_ran` nine times and `only_missing` never (no occurrence in the file). The
  regression that would ship green: an advisory leaf that ran, died transiently and was killed
  mid-retry leaves an in-flight log and no artifact, `_resume_interrupted_check` skips it, and
  the bundle reaches sign-off with that advisory leaf silently absent — the exact criterion-(v)
  failure, on the twin the round-1 carry-forward already asked to be covered (item 4). One test:
  seed a bundle with an in-flight advisory error log and no artifact, assert the leaf is re-run.

## Attempted and could not refute

- **The red leg is not a symbol-existence trap.** Every assertion is behavioural and the file
  imports only pre-existing API; the C4 red leg fails on `AssertionError` / the base's own
  `error_log.write_text` at `:720`, not on `ImportError` — no `PDCA-UNVERIFIABLE`.
- **20 mutations of the new production logic, 19 caught** by the 1784-test suite: whole-line →
  substring match in `leaf_run_incomplete`; dropping `_defang_in_flight` in `_format_leaf_attempt`
  and in `_residue_record`; `_atomic_write_text` → plain `write_text`; withdrawing before
  persisting; dropping the `recorded` gate on the retry; dropping the `records` conjunct on the
  keep-the-log condition; dropping the re-flush on a refused withdrawal; `_empty_run_class` →
  always substantive; reverting `assemble.py:425` and `review_never_ran` to `.exists()`; deleting
  `_settle_leaf_record` at each of the five call sites; settling *before* the outcome is filed.
  Only the `only_missing` revert above survived (plus the untested `_RESIDUE_KEEP` bound, folded
  into finding 2).
- **Impersonation.** Nine payloads through the real wrapper — bare marker, whitespace/NBSP
  padded, doubled, CRLF, marker + trailing blanks, marker mid-line, defanged-then-real, and a
  payload long enough to exercise `progress`' 200-line stderr tail cap — none flipped
  `leaf_run_incomplete` on a spent run. The defang cannot synthesise the marker (`pdca:` →
  `pdca-quoted:` is one-way), and truncation at `_RESIDUE_KEEP` can only break it.
- **Kill-ordering.** I walked every ordering of the loop (`:750-775`) and the three harvests: I
  could not construct a kill point that leaves an interrupted leaf looking spent. The
  `recorded`/`owned` fail-closed stops hold; a failed non-first flush leaves a stale marker only
  until the harvest's `_settle_leaf_record`, which is covered.
- **Scope.** No touch to `progress.py`, `LeafError.transient`, the retry set, the builder path,
  the staleness clear (`:718`), or `test_leaf_resilience.py`; no `tests/fixtures/`; all three
  `_invoke_leaf_resilient` call sites pass `artifact=`. `has_cycle_evidence` (`state.py:203`) is
  the only other consumer of the log's existence and the change only makes it *less* likely to
  mis-settle a live bundle.
- **Examined and accepted, not filed:** a success that *did* produce its artifact discards the
  log and with it the dead predecessor's quoted verdict (`:748`) — the round-2 sign-off
  adjudicated exactly this reading of criterion (vi), so it is settled scope, not a defect.

### Advisory — code-review

# Advisory code review — correctness & reuse lens (issue #64 / #536, iteration 4)

Read the full diff against target `leaves.py`/`assemble.py`/`driver.py`/`state.py` plus
`template/tests/test_attempt_ownership.py`, ran that new file and the untouched
`test_leaf_resilience.py` directly against the checked-out patched tree (both green,
26/26 and 5/5), and re-read `gate-logs/C4-verify.log` (26 green with the fix, 19 fail +
4 error red with it reverted) and `gate-logs/T3-suite.log` (full driver suite green).

## Correctness

No new correctness bugs found in this iteration's mechanism. Specifically checked and
confirmed sound:

- `_invoke_leaf_resilient` (`leaves.py:673-780`): the ordering of quote-then-persist-
  then-withdraw (`:759-767`) closes the round-3 withdraw-before-persist window; the
  fail-closed re-flush on a refused withdrawal (`:768-769`) and the unconditional break
  on the last attempt (`:773`) are correct for every combination of `may_retry`/
  `recorded`/`owned` I traced by hand, including the terminal-attempt case where
  `_write_attempt_records` itself fails (the harvest sites' own `_settle_leaf_record`
  call after the placeholder acts as a backstop against a stale in-flight trailer in
  that case — verified by `test_a_failed_flush_leaves_no_stale_marker_beside_a_filed_failure`
  and its advisory/plan-advisory twin).
- `leaf_run_incomplete` / `_settle_leaf_record` (`leaves.py:898-972`): the whole-last-
  non-blank-line match is safe against a truncated `_residue_record` quote or a
  `_format_leaf_attempt` tail accidentally producing the exact marker text, because
  both quoting sites run through `_defang_in_flight` *before* truncation/embedding
  (`:1004-1011`, `:1046`) — I traced the truncation-boundary case (marker cut mid-string
  by `_RESIDUE_KEEP`) and it cannot reassemble into an exact match either.
- The three harvest sites (`:2837-2871`, `:3215-3232`, `:3520-3537`) are structurally
  identical in the ordering that matters (settle only after the placeholder that
  supersedes the log is filed) and match what the tests in
  `BothAdvisoryHarvestsAreAttemptAwareToo` actually drive.

One low-value, low-risk gap, not worth gating on: `_format_leaf_attempt`'s
"`(no output captured)`" fallback body (`leaves.py:1046` area, the `body = tail if tail
else f"(no output captured) {type(exc).__name__}: {exc}"` line) is **not** passed
through `_defang_in_flight` — only `tail` is. In practice this fallback fires for
harness-level plumbing exceptions (e.g. a `FileNotFoundError` from a misconfigured
`argv`), not leaf-controlled text, so it's outside the two channels criterion (iv)
actually names ("captured stderr" / "quoted artifact text") and I could not construct a
realistic path where `str(exc)` contains the literal marker. Noting it rather than
gating on it.

## Reuse / simplification

- The three harvest sites remain close to verbatim copies of each other (`err is not
  None` branch, `out.exists()` branch, the `_settle_leaf_record` calls) — a natural
  `_harvest_leaf(d, error_log, artifact, dest, unavailable_fn, ...)` extraction. This is
  already surfaced and explicitly deferred by iteration 3's carry-forward as an Act
  candidate ("prefer the minimal edit at each site over a refactor" — the diff is
  already large), so I'm not re-opening it as a fresh finding here, just confirming the
  duplication is still there and still intentional.
- The success-path re-flush in `_invoke_leaf_resilient` (`:745-746`) writes the exact
  same bytes (`records`, `in_flight=True`) that the immediately-preceding per-attempt
  flush already landed on disk — it's a no-op write on the happy/common path (harmless,
  and arguably a deliberate belt-and-suspenders against a torn read, but worth a
  one-line comment if Act ever revisits this function, since a future reader may assume
  it's load-bearing when the actual safety net is the earlier flush).

## Verdict

Diff is clean on both lenses to the depth I could check without vendor tooling. No
NEEDS-HUMAN findings.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm merged-history and closed/rejected-work overlap for every affected path—this disposable target has one commit and no remote refs, and the brief's path audit explicitly covers `leaves.py` but not all four other changed paths, so incomplete prior-art coverage could conceal conflicting work.
- [ ] Validation — fitness-to-purpose — Decide whether marker-bearing error logs should operationally favor re-running an interrupted reviewer over retiring it—this determines whether avoiding a review-less sign-off justifies possible duplicate reviewer cost (`template/src/pdca_harness/leaves.py:919`, `template/src/pdca_harness/driver.py:177`).
- [ ] `template/src/pdca_harness/leaves.py:912`: `leaf_run_incomplete`
- [ ] `template/src/pdca_harness/leaves.py:1004`: `_residue_record` reads the
- [ ] `template/src/pdca_harness/leaves.py:3176`: the second of the two #369
- [ ] size backstop — this slice is behaving oversized: patch is 91 KB (threshold 80 KB); 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Not a slicing problem — reading A. The slice and the design are right and have been stable for four rounds: C4 red->green reproduced independently, 19 of 20 mutations of the new logic caught, no impersonation payload flipped either discriminator, and test_leaf_resilience.py untouched and green. Same slice, same mechanism. Do NOT re-scope, do not split, do not refactor. On the size flag: it is largely the test. 857 of the 1312 added lines (49 KB of 91 KB) are template/tests/test_attempt_ownership.py; the production change is ~450 lines across four files. Keep the diff from growing — prefer the minimal edit at each site. Close these three findings, all in code this patch introduced: 1. template/src/pdca_harness/leaves.py:912 — leaf_run_incomplete reads the log with read_text(encoding="utf-8") and guards only OSError (:913), while its own docstring promises "absent or unreadable => False" (:909-910). A non-UTF-8 log raises UnicodeDecodeError straight out of a discriminator that now sits on driver.advance's critical path, so the cycle aborts instead of degrading; the reachable route is the patch's own premise (a log the pre-patch non-atomic write left truncated mid-multibyte, read after upgrade). Fix: errors="replace" — matching _residue_record's own defensive read at :1004 — or except (OSError, ValueError). 2. template/src/pdca_harness/leaves.py:1004 — _residue_record reads the entire dead artifact into the driver before applying the _RESIDUE_KEEP bound (:1007), and is called from inside the "a failed leaf must never crash the cycle" handler (:758, guard at :750) which catches only OSError (:1005). A MemoryError therefore escapes the guard and leaves no placeholder and no error log — precisely the no-artifact/ no-account state this slice exists to eliminate. Same escape at the two advisory sites (:3222). Fix: bounded read, open(...).read(_RESIDUE_KEEP + 1), and widen the guard to Exception. 3. template/src/pdca_harness/leaves.py:3176 — run_advisory_leaves(only_missing=True), the second of the two #369 recovery discriminators criterion (v) names explicitly, is exercised by no test: reverting it to the base's bare advisory_error_log(...).exists() leaves the whole 1784-test driver suite green. This is the twin round 1's carry-forward already asked to be covered (item 4). Add one test: seed a bundle with an in-flight advisory error log and no artifact, assert the leaf is re-run. Do not widen the slice: keep test_leaf_resilience.py untouched; do not touch progress.py, LeafError.transient, the retry set, the builder path, or the staleness clear. The near-verbatim duplication across the three harvest sites stays an Act candidate, not this round's refactor. Optional, non-gating if it is free while in that function: _format_leaf_attempt's "(no output captured)" fallback body (leaves.py:1046 area) does not pass through _defang_in_flight — only tail does. The code-review lens judged it outside the two channels criterion (iv) names and declined to gate on it. The two routine NEEDS-HUMAN items (T5 prior-art overlap across the four non-leaves.py paths; fitness-to-purpose on re-running an interrupted reviewer) were NOT cleared and remain open for the next sign-off.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
