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

Review of the fix that makes failed reviewer/advisory attempts persist their own records and prevents dead-attempt artifacts from being harvested as successful output.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is bounded to per-attempt persistence, artifact ownership, and interrupted-versus-spent recovery at the resilient wrapper and its recovery discriminator (`template/src/pdca_harness/leaves.py:673`, `template/src/pdca_harness/leaves.py:2335`). |
| C2 Reproduction (red pre-fix) | PASS | With tracked production changes stashed and the behavioral test retained, the pre-fix tree produced 14 failures plus 1 error through existing entry points, including the missing predecessor record asserted at `template/tests/test_attempt_ownership.py:189`. |
| C3 Change | FAIL | Successful-retry cleanup must not be best-effort: suppressing an unlink failure can leave a settled `*.error.log` beside a successfully harvested live verdict, violating the required success-with-no-error-log contract and polluting archived evidence (`template/src/pdca_harness/leaves.py:740`). |
| C4 Verification (red→green) | PASS | Independent stash/pop execution reproduced red (14 failures, 1 error) then green (19/19), and the complete patched driver suite passed; the tests exercise the production wrapper directly at `template/tests/test_attempt_ownership.py:166`. |
| C5 Causal adequacy | PASS | The cause is addressed at the attempt-ownership boundary by withdrawing a failed attempt’s artifact before retry and making later harvests consume only the surviving attempt’s path; no capability-probe or symptom-guard smell applies (`template/src/pdca_harness/leaves.py:743`, `template/src/pdca_harness/leaves.py:2771`). |
| T1 Structure | PASS | The change remains one attempt-accountability slice across the wrapper, its three harvesters, and their shared discriminator; the out-of-scope builder and transient-classification paths are untouched (`template/src/pdca_harness/leaves.py:2759`, `template/src/pdca_harness/leaves.py:3119`, `template/src/pdca_harness/leaves.py:3423`). |
| T2 Shape | PASS | `git diff --check`, Python byte-compilation, both frozen documentation checks, and host-CI documentation parity are clean; the new test is isolated in `template/tests/test_attempt_ownership.py:1`. |
| T3 Runtime | FAIL | Injecting an `OSError` into successful error-log cleanup yielded a live `check-review.md` while `check-review.error.log` remained present and settled, so runtime evidence can falsely report a failure after success (`template/src/pdca_harness/leaves.py:740`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted during Check; the frozen row is deferred and its substantive contribution audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm no overlapping merged, closed, or rejected work for every affected source path before publish — the disposable target exposes only one synthetic base commit and no remote refs, so prior art cannot be mechanically settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether operational evidence remains trustworthy under real cleanup/permission failures after the residual-log defect is resolved — a successful leaf must not be archived as both success and failure (`template/src/pdca_harness/leaves.py:740`). |

### Advisory — adversary

# Adversarial review — attempt-owned leaf records and harvests (#506 / issue_536)

Task under review: give `_invoke_leaf_resilient` and the three artifact harvests a notion of
*which attempt* produced what — flush each attempt's record as it happens, withdraw a dead
attempt's artifact (text preserved), keep the #369 recovery discriminators honest about the
new "in flight" state, and stop a leaf's own text from impersonating the harness's trailer.

I re-ran the asserted proof rather than reading it. **Post-fix:** `PYTHONPATH=src python3 -m
unittest tests.test_attempt_ownership` → 19 tests, OK. **Red leg** (production hunks reverted
via `git checkout` on `assemble.py`/`driver.py`/`leaves.py`/`state.py`, the new test file
kept — the same shape `engine/scripts/run-verify.sh:214` uses) → **14 failures + 1 error**,
with module-level imports resolving cleanly (no `PDCA-UNVERIFIABLE` import trap). Full
suite with the patch: **1777 tests, OK (skipped=2)**. The C4/T3/C5 rows in `check-gates.json`
are warranted as written. What follows is what survived that.

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:871`: the whole-last-line
  match — the exact leg the brief singles out — is asserted in prose only; the suite cannot
  tell it from the defect round 3 shipped.** I mutated `return bool(tail) and tail[-1] ==
  _LEAF_IN_FLIGHT` into `return any(_LEAF_IN_FLIGHT in line for line in tail)` (a
  substring-anywhere sniff) and ran the whole suite: **1777 tests, OK**. Both impersonation
  cases (`test_attempt_ownership.py` `…ending_in_the_trailer_is_not_the_trailer`,
  `…stderr_quotes_the_trailer_is_still_read_as_spent`) stay green because `_defang_in_flight`
  neutralises the payload *before* the match ever runs, so only the belt is exercised and
  never the braces that `leaves.py:859-864` claims ("a substring sniff would let a leaf that
  MENTIONED the marker describe its own run… an impersonation has to defeat both"). The
  brief's Falsifiability §(iv) names this precisely — "the marker must be alone on its own
  final line — round 3 shipped this leg with the marker embedded mid-line". A one-line unit
  assertion closes it, no new fixture: hand-write a log whose *body* contains
  `"echo of the source: " + marker` on a non-final line and whose last non-blank line is
  ordinary text, and assert `leaves.leaf_run_incomplete(log)` is `False` — that goes red
  under the substring form and green under the shipped one. Severity is conformance, not a
  live exploit: I could not build a payload that defeats `_defang_in_flight` yet trips the
  match, so today the belt covers the braces — which is exactly why a regression that
  silently removed the braces would ship unnoticed.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:3135` and
  `template/src/pdca_harness/leaves.py:3439`: both advisory `_settle_leaf_record(error_log)`
  calls can be deleted and the suite stays green.** I removed both lines and re-ran: **1777
  tests, OK**. `BothAdvisoryHarvestsAreAttemptAwareToo` drives both twins but only asserts
  the *harvest* half (artifact contents + preserved residue); nothing reads back the
  advisory log's settled state, because `run_advisory_leaves(only_missing=True)`
  (`leaves.py:3079-3081`) short-circuits on `advisory_artifact(...).exists()` — the
  placeholder — before it ever reaches `_leaf_ran_and_failed`. The reviewer's twin *is*
  covered (`test_a_filed_outcome_settles_the_account`); its two copies are not. This is the
  same class the sign-off's finding 4 asked to close ("wiring either site … and the suite
  would stay green"), one call site over: parametrise the existing subTest to assert
  `leaves.leaf_run_incomplete(error_log)` is `False` after each advisory site returns.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/driver.py:178-179`: the operator-facing
  recovery message still says the leaf "never ran", which the patch has just made false.**
  `_resume_interrupted_check` prints `"Check — reviewer never ran (beat was interrupted
  after the gate write); recovering it…"` on every `review_never_ran(d)` — and since
  `leaves.py:2351-2352` that predicate is now *also* true for a reviewer that ran, died
  transiently, flushed `overloaded_error 529` to `check-review.error.log`, and was killed
  during the backoff. The operator is told the beat died *before* the leaf, over a bundle
  that visibly contains that leaf's error log. The diff reworded the paired text in
  `assemble.py:435-437` for exactly this reason ("the reviewer leaf never ran, **or the Check
  beat died while it was still running**") and states the rule at `assemble.py:419-422`
  ("they must not tell the operator three different stories about it") — the fourth reader,
  sixteen lines below the `driver.py:154-162` docstring the patch *did* update, was missed.
  Wording-only fix.

- **NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:737` + `leaves.py:2825`: the #278
  inversion the sign-off asked to close survives in the commoner shape — a transient death
  that wrote no artifact.** `_empty_run_class` can only classify what `withdrew` kept, and
  `leaves.py:737` keeps the log **only** when a dead attempt left a *file* behind. Driven
  end to end through `leaves._run_review_sandboxed` with a reviewer whose attempt 1 emits
  `overloaded_error 529` on stderr and exits 1 (i.e. `test_leaf_resilience.py:28-31`'s own
  `_TRANSIENT`, the canonical transient death — it writes nothing) and whose attempt 2 exits
  0 having written nothing, I get:

      attempts: 2 · error log exists: False · infra-empty: False · human-empty: True
      "Failure class: **substantive — needs a human.** The leaf ran but did not yield a
       usable verdict; do not assume an infra blip"

  — the exact sentence `leaves.py:2820-2823` says #278's marker exists to prevent, and attempt
  1's 529 is deleted outright by the `error_log.unlink()` at `leaves.py:740-741`, so §6 has
  no pointer to the infra death at all. This needs a human call, not a reflex: closing it
  means keeping the log whenever `records` is non-empty and the artifact is absent, which
  reads against criterion (vi)'s "a success still leaves no error log behind" and stretches
  criterion (iii)'s "still degrades to today's placeholder" — but leaving it means
  criterion (ii)'s "a dead attempt's text is preserved rather than merely deleted" holds
  only for attempts that happened to write a file, which is not what "an attempt is the unit
  of accountability" says. (No existing test blocks the change: `test_leaf_resilience.py`
  has no retry-then-succeed case.)

- **NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:2772` (twins `:3131`, `:3434`): the
  patch made the *discriminator's* file crash-atomic and left the *verdict's* file a
  non-atomic `shutil.copy2`, so a kill inside the harvest still files a truncated verdict —
  and blocks the recovery that would replace it.** Driving `_run_review_sandboxed` with a
  reviewer that succeeds and writes a full verdict, killed inside the bundle-side `copy2`:

      check-review.md exists : True
      content                : '# Review\n\n| Item | Verdi'
      review_never_ran       : False   ← the driver will NOT recover it

  A one-third-written `check-review.md` reaches sign-off as the review, and
  `leaves.py:2351` retires the leaf because the artifact "exists". The non-atomicity
  predates this diff, but the diff is what put attempt ownership on this line, and the
  invariant it restores ("no truncated verdict a dead attempt left may be adopted as the
  leaf's output") has an exact analogue here that the `_settle_leaf_record` docstring's
  absolute framing (`leaves.py:888-890`, "then no kill on either side of it leaves an
  interrupted Check looking spent") papers over. Whether hardening the harvest belongs to
  this slice or to a sibling is a scope call, not a builder reflex — the same `os.replace`
  helper the patch already added (`leaves.py:788`) would do it in one line per site.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:807-808`: the "inert" claim
  about a stranded temp sibling is slightly stronger than the code supports (minor).** The
  docstring argues the orphan is harmless *because* "no `state.DOWNSTREAM_GLOBS` pattern
  claims it" — but that is also why nothing ever removes it: `driver.py:431` archives by
  those same globs (`state.py:127` = `("check-advisory-*.md", "*.error.log",
  "*.memory.jsonl")`, none of which match `check-review.error.log.tmp.<pid>`), and
  `_invoke_leaf_resilient`'s staleness clear at `leaves.py:716-719` only unlinks the log and
  its memory twin. So each kill inside `_atomic_write_text` leaves one file that survives
  every subsequent iterate, inside a bundle directory that is committed in consumer repos.
  The repo's own precedent for an orphanable temp is to gitignore it (`leaves.py`'s #313
  seed spill: "a SIGKILLed session can still orphan one, which is why the name is
  gitignored"); this name is in no `.gitignore`. Either sweep `*.error.log.tmp.*` in the
  staleness clear, or soften the claim.

## Attempted and could not refute

- **The red→green is real, and it is the production path.** Reproduced independently in a
  copy of `$PDCA_TARGET`; the 14 failures + 1 error under reverted production are behavioural
  (`AssertionError: '1.1 Root cause | PA' unexpectedly found in …`, `'infra-empty' not found`,
  `2 != 1`), not symbol-existence, and the file imports only pre-existing API at module
  level. Mutation-testing confirmed the suite is not a mirror where it counts:
  dropping `_defang_in_flight` in `_withdraw_residue` (`leaves.py:947`) or in
  `_format_leaf_attempt` (`leaves.py:968`) each turns the suite red.
- **Impersonation via the stderr channel.** I ran 15 payloads through the production wrapper
  (exact marker; leading/trailing spaces; tab-, NBSP-, VT-, FF- and zero-width-padded; CR
  terminated; doubled internal space; repeated; trailing blank lines) — every one left
  `leaf_run_incomplete=False` / `_leaf_ran_and_failed=True` on the spent log. `str.strip()`
  and the substring-scoped defang cover the whitespace-variant space; a payload that dodges
  the defang necessarily dodges the equality test too.
- **The three harvests point at the right paths.** `produced = sandbox / "check-review.md"`
  (`leaves.py:2753`) and `out = sandbox / f"check-advisory-{leaf_id}.md"` (`leaves.py:3117`) /
  `sandbox / f"plan-advisory-{leaf_id}.md"` (`leaves.py:3421`) are all sandbox-local, so
  `artifact=` can never unlink a previously shipped bundle artifact; `REVIEWER_INPUTS` (`leaves.py:68`) seeds none of those three names into a
  sandbox, so no seeded input can be mistaken for a dead attempt's residue.
- **`_settle_leaf_record` cannot corrupt a log**: its pop loop (`leaves.py:903-908`) is
  gated by `leaf_run_incomplete`, so it only ever strips blank lines and the trailer.
- **No fourth reader drifted.** Repo-wide grep finds the discriminator read in exactly
  `leaves.review_never_ran`, `run_advisory_leaves(only_missing=True)` and
  `assemble._missing_review_text` — all three converted. `state.has_cycle_evidence` sees an
  in-flight log as *more* evidence, never less. Lanes cannot collide on the temp sibling
  (`.tmp.<pid>` is per-path, and `run_advisory_leaves` is a sequential loop).
- **`template/tests/test_leaf_resilience.py` is untouched** (clean in `git status`) **and
  green**, as criterion (vi) requires.
- The staleness clear at `leaves.py:716` still destroys a preserved dead-attempt verdict on a
  recovery re-run. I am **not** filing it: the sign-off adjudicated it as a deliberate
  deferral for Act, and criterion (vi) freezes that line.

### Advisory — code-review

# Check advisory — code review (correctness + reuse/simplification)

Scope: `template/src/pdca_harness/{leaves,driver,assemble,state}.py` and the new
`template/tests/test_attempt_ownership.py`, as touched by this patch (issue #506,
iteration 2). Grounded on `$PDCA_TARGET` (patch already applied there).

## Correctness

No bugs introduced by this patch were found. Specifically verified, against the target
source, not just the diff:

- **Retry/withdraw/flush interaction** (`leaves.py:723-764`): `may_retry` is
  `transient and attempt < attempts and owned`, and the loop only continues if
  `_write_attempt_records` also returned `True` (`:756-758`). Every path that can reach
  the success branch has therefore already durably flushed its predecessor's record, so
  the "kept in-flight" re-write on a silent success (`:737-738`) is provably writing
  content identical to the last mid-loop flush — redundant but harmless, not a
  correctness gap (traced by hand across the 1-of-3-attempts and 2-of-3-attempts cases;
  matches what `AttemptRecordsLandBeforeTheNextAttemptStarts` and
  `DeadAttemptOutputIsNeverHarvested` in the new test file exercise).
- **`_empty_run_class`** (`leaves.py:2812-2825`): only reachable with `error_log.exists()`
  actually true when a withdrawal happened in *this* invocation, because the wrapper
  clears any stale log before the loop starts (`:716`) and only a same-run withdrawal can
  leave one behind on a `None` return. So classifying "log survives a success ⇒ infra
  death" needs no extra state check — confirmed correct, not merely asserted by the
  tests.
- **`_settle_leaf_record` ordering** (`leaves.py:2780-2783`, `:3132-3135`,
  `:3436-3439`): called unconditionally after either harvest branch (copy or
  placeholder), and is a documented no-op on an absent/settled/unreadable log — verified
  that on the `produced.exists()` branch the log has already been unlinked by the wrapper
  by construction, so the call there is inert as designed, not accidentally so.
- **Whole-line, defanged marker match** (`leaf_run_incomplete`, `leaves.py:853-871`,
  `_defang_in_flight`, `:777-785`): every place that embeds leaf-controlled text into the
  log (`_format_leaf_attempt` tail, `_withdraw_residue` residue) routes through
  `_defang_in_flight` before it reaches `records`, so there is no path by which raw
  leaf-authored text can land in the log un-defanged.
- Three call sites of `_invoke_leaf_resilient` (`:2759`, `:3119`, `:3423`) all now pass
  `artifact=`; grepped for any other caller — there are none, so nothing was missed.
- The three places that used to read `REVIEW_ERROR_LOG`/advisory-error-log existence
  bluntly (`assemble.py:425`, `leaves.py:2352` `review_never_ran`, `leaves.py:3080`
  `run_advisory_leaves`) all now route through `_leaf_ran_and_failed`; grepped the rest of
  `template/src/pdca_harness` for other bare `.exists()` reads of these paths — none
  found, so the "three readers must agree" invariant is actually closed, not just
  claimed.
- `test_leaf_resilience.py` is untouched by the diff (only named in the new file's
  docstring) — confirmed via `grep -c` on the patch; C4's gate log
  (`gate-logs/C4-verify.log`) shows a genuine red→green on `test_attempt_ownership.py`
  alone (19 tests, 17 fail on the reverted production hunks, all for the reasons the
  brief predicts), and T3's 1777-test run is green.

One pre-existing, explicitly-deferred behavior worth restating for the record (not a new
finding — it's the carried-forward item the prior sign-off told this round to leave
alone): the staleness clear at `leaves.py:716` still unconditionally unlinks a prior
in-flight log — including one holding a preserved dead-attempt verdict — the moment a
recovery re-run of the same leaf starts. Correctly out of scope per criterion (vi) and
the carry-forward's item 1 note; flagging only so it isn't mistaken for something this
review missed.

## Reuse / simplification (minor, non-blocking)

- `_atomic_write_text` (`leaves.py:788-816`) reimplements the temp-sibling +
  `os.replace` idiom that `act.py` already inlines three times (`act.py:324-326`,
  `:367-369`, `:722-724`). The repo evidently prefers inlining this idiom per call site
  rather than factoring it, so this isn't a deviation from house style, but a fourth
  copy is a candidate for a shared one-line helper (e.g. in `state.py`, imported by both
  modules) next time either module touches this idiom again.
- `_leaf_ran_and_failed` (`leaves.py:874-877`) calls `error_log.exists()` and then
  `leaf_run_incomplete(error_log)`, which itself does a second `.read_text()` open. Since
  `leaf_run_incomplete` already treats an absent file as `False` (`:868-869`), the
  `.exists()` guard is redundant with the `try/except OSError` inside it — could be
  simplified to `not leaf_run_incomplete(error_log)`-only plus tracking "did it exist" if
  ever needed, dropping one syscall per call. Cold path (called once per bundle per
  discriminator check, not in a retry loop), so this is a nit, not a performance concern.

Neither item rises to a human-adjudication or builder-iteration finding; both are
optional polish for a future touch of this code.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm no overlapping merged, closed, or rejected work for every affected source path before publish — the disposable target exposes only one synthetic base commit and no remote refs, so prior art cannot be mechanically settled here.
- [ ] Validation — fitness-to-purpose — Decide whether operational evidence remains trustworthy under real cleanup/permission failures after the residual-log defect is resolved — a successful leaf must not be archived as both success and failure (`template/src/pdca_harness/leaves.py:740`).

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
- Iteration delta (if iterating): Rejected on unclosed carry-forward, not on approach or slicing. The slice is the right size and the design is sound — the atomic per-attempt flush, the defang + whole-last-line match, fail-closed withdrawal, and the three converted readers of "an error log means the leaf ran and FAILED" are all correct and independently reproduced (14 failures + 1 error red, 19/19 green, 1777-test suite green). Same slice, same design; close the items below. 1. Close round 1's carry-forward item 3 in the shape that actually occurs. `_empty_run_class` is keyed on `error_log.exists()`, but the log only survives a success when `withdrew` is True — and `withdrew` is set only when a dead attempt left a FILE. For the canonical transient death (attempt 1 exits non-zero with `overloaded_error 529` on stderr, writes nothing; attempt 2 exits 0 writing nothing) the `else` branch at leaves.py:739-741 unlinks the log, so `_empty_run_class` sees nothing and stamps `_FAIL_SUBSTANTIVE` — the operator is told "substantive — needs a human. The leaf ran but did not yield a usable verdict; do not assume an infra blip" one step after the harness deleted the 529 it was holding. That is #278's inversion and the parent invariant ("the evidence of a failure is kept; no evidence is never filed as a verdict") failing in the COMMON case. Adjudication you need, which the brief left ambiguous: keep the log whenever `records` is non-empty and the artifact is absent, not only after a file withdrawal. Criterion (vi)'s "a success still leaves no error log behind" governs a clean success that PRODUCED its artifact — not a success that produced nothing over a dead predecessor. Criterion (iii) still holds: a leaf that exits 0 having written nothing with NO dead predecessor degrades to today's placeholder, error-log-free, class unchanged. 2. Make the successful-retry cleanup not best-effort (the reviewer's C3/T3 FAIL, leaves.py:737-741). A swallowed `OSError` on `error_log.unlink()` leaves the log in flight; the harvest then succeeds and `_settle_leaf_record` STRIPS the trailer, converting the leftover into a settled "ran and failed" record beside a live check-review.md — one leaf archived as both success and failure, against criterion (vi). Confirmed narrow: no reader is driven to a wrong action (review_never_ran and the advisory short-circuit both see the artifact first), so this is archive pollution plus a contract breach, not a corrupted verdict. Fix at the source rather than papering over it downstream. 3. Close the two test-blindness holes the adversary demonstrated by mutation; both are one assertion and both would let a real regression ship green. - Mutating `leaf_run_incomplete`'s whole-line match into a substring sniff leaves all 1777 tests green, because both impersonation cases route their payload through `_defang_in_flight` before the match runs — the braces leaves.py:859-864 argues for are untested. Hand-write a log whose BODY contains the marker on a non-final line and whose last non-blank line is ordinary text; assert `leaf_run_incomplete(log)` is False. - Deleting BOTH advisory `_settle_leaf_record` calls (leaves.py:3135, :3439) leaves the suite green: `BothAdvisoryHarvestsAreAttemptAwareToo` asserts only the harvest half. Parametrise it to assert `leaf_run_incomplete(error_log)` is False after each site. 4. `driver.py:178-179` still prints "Check — reviewer never ran (beat was interrupted after the gate write)" on every `review_never_ran(d)`, which this patch has just made false for a reviewer that ran, died transiently and was killed during the backoff. The paired text in assemble.py:435-437 was reworded for exactly this reason; this fourth reader was missed. Wording only. Do NOT widen the slice: - Leave the staleness clear at leaves.py:716 alone — criterion (vi) freezes it and the prior sign-off adjudicated it as a deliberate Act deferral. - The non-atomic `shutil.copy2` of the VERDICT at the three harvests (leaves.py:2772, :3131, :3434) and the stranded `*.error.log.tmp.<pid>` (leaves.py:807-808) are noted as Act candidates, not this round's work. Do not harden them here. - Do not touch the retry set, `LeafError.transient`, `progress.py` (sibling #538 owns it) or the builder path. Keep `test_leaf_resilience.py` untouched.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
