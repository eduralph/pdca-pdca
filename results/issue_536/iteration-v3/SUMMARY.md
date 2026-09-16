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

Task under review: make retrying reviewer and advisory leaves persist attempt-owned records and harvest only the successful attempt's artifact while preserving interrupted-run recovery.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The retry, dead-artifact, impersonation, and recovery outcomes are falsifiable offline against the resilient wrapper at `template/src/pdca_harness/leaves.py:673`. |
| C2 Reproduction (red pre-fix) | PASS | With the four production files stashed and the new behavioral test retained, the independent base run produced 17 failures and 1 error, including the missing pre-retry record assertion at `template/tests/test_attempt_ownership.py:204`. |
| C3 Change | FAIL | A dead attempt's text must survive interruption, but withdrawal unlinks it at `template/src/pdca_harness/leaves.py:986` before the caller first persists that record at `template/src/pdca_harness/leaves.py:760`, leaving an avoidable evidence-loss window. |
| C4 Verification (red→green) | PASS | Independent stash/restore reproduced red (17 failures, 1 error) then green (22/22), and the restored patch also passed its unchanged resilience and memory-log suites (44/44 total) plus reverse-apply checking. |
| C5 Causal adequacy | FAIL | Attempt accountability remains incomplete when the harness dies between destructive residue withdrawal and record persistence at `template/src/pdca_harness/leaves.py:753`; that ordering can recreate the exact no-artifact/no-account state the fix is meant to eliminate. |
| T1 Structure | PASS | The work remains one accountability slice centered on the retry wrapper and its three harvest/recovery consumers, with the production boundary anchored at `template/src/pdca_harness/leaves.py:673`. |
| T2 Shape | PASS | `git diff --check` and reverse-apply checking pass, and the frozen docs lint, site link audit, and host-CI parity logs all show green. |
| T3 Runtime | FAIL | Although the independent full offline suite passed 1,780 tests, a forced kill immediately after `artifact.unlink()` at `template/src/pdca_harness/leaves.py:986` observed `runs=1 bundle_artifact=False error_log=False`, losing both the dead verdict and its account. |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; `gate-logs/T4-contribution.log` records that the substantive contribution audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm no overlapping merged or closed/rejected work for every affected path — the disposable target contains one synthetic base commit and no remotes, so the brief's prior-art claim cannot be mechanically re-derived here and overlap would affect contribution safety. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the operational post-mortem guarantee is acceptable only after the withdrawal-before-persistence kill window is resolved — the normal suite is green but misses a core process-death boundary. |

### Advisory — adversary

# Adversarial review — issue_536 (attempt-owned leaf records and harvests)

Verdict up front: **I could not break the mechanism.** The red→green was reproduced
independently, twelve targeted mutations of the new production logic were all caught by the
new test file, and the 1780-test driver suite is green. The two findings below are
claim-accuracy defects in what the patch *tells the operator and the next maintainer*, in a
slice whose whole invariant is "never file a false account of a run" — both are cheap
builder edits, neither is a behavioural break.

## Findings

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:2910` — the §6 text the new
  `_empty_run_class` path (`leaves.py:2866`, used at `:2819`, `:3175`, `:3478`) routes into
  states something that did not happen. Concrete case, run against the patched target: a
  reviewer whose attempt 1 exits 1 with `overloaded_error 529` and whose attempt 2 exits 0
  having written nothing yields a placeholder reading *"**transient infra — safe to
  re-run.** The leaf exited non-zero with no output **and retries did not recover**…"* — but
  the retries *did* recover; the recovered attempt produced no verdict. `_FAIL_TRANSIENT`'s
  prose was written for the retries-exhausted shape only, and the builder updated the
  adjacent internal comment for exactly this reason (`leaves.py:2829`, now "retries didn't
  recover") while leaving the operator-facing sentence untouched. The class (`infra-empty`)
  and the action ("safe to re-run") are right; only the account of what happened is wrong.
  The new test cannot catch it: `template/tests/test_attempt_ownership.py:363-365` asserts
  only `LEAF_STATUS_INFRA`, `not LEAF_STATUS_HUMAN` and the substring `"safe to re-run"` —
  an assertion that is true of the wrong sentence too. Either widen the prose to cover "the
  run contained a transient death; the attempt that came back produced nothing", or give
  the empty-run shape its own wording.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:919-921` and
  `template/tests/test_attempt_ownership.py:607-609`, `:523-525` — the stated consequence of
  `_settle_leaf_record` is unwarranted. Both the docstring and the two tests justify the
  settle with "otherwise a leaf that gave up looks recoverable forever and is re-run (and
  re-paid for) on every `advance`". That cannot happen: at every one of the three sites the
  settle runs *after* the `*_unavailable(...)` placeholder has been written, and every reader
  of the marker short-circuits on that artifact first — `review_never_ran` requires
  `check-review.md` absent (`leaves.py:2388-2389`), `run_advisory_leaves(only_missing=True)`
  checks `advisory_artifact(...).exists()` first (`leaves.py:3120-3122`), and
  `assemble._missing_review_text` is only reached when the review is absent
  (`assemble.py:185`, `:261`). Demonstrated: with `leaves.py:2823`'s settle deleted, the same
  end-to-end reviewer run leaves the log carrying `_LEAF_IN_FLIGHT` and
  `review_never_ran(d)` is **still `False`** — nothing is recovered or re-paid for. The
  settle is archive hygiene (a bundle must not archive a finished leaf as unfinished), and
  `test_a_filed_outcome_settles_the_account` only bites because it transplants the log into a
  synthetic bundle that has no `check-review.md` — a state that cannot arise once the outcome
  is filed. The genuinely load-bearing half — settle *after* the placeholder, never before —
  is correct and is separately proven (I mutated the order and
  `test_a_kill_before_the_outcome_is_filed_is_recovered_not_retired` went red). Fix the
  rationale, not the code, so a later maintainer does not read the settle as a recovery guard.

## Attempted refutations that failed

- **The evidence.** Reproduced from the frozen inputs, not taken on trust: patched target →
  `Ran 22 tests … OK`; production hunks reverted with the test kept (the `run-verify.sh` red
  leg) → `FAILED (failures=17, errors=1)`; full driver suite on the patched tree →
  `Ran 1780 tests … OK (skipped=2)`. The five tests green pre-fix are exactly the
  unchanged-behaviour guards for criteria (iii)/(vi), which is what they should be. The suite
  drives real `python3` child leaves through `_invoke_leaf_resilient`,
  `_run_review_sandboxed`, `_run_advisory_sandboxed` and `_run_plan_advisory_sandboxed` —
  no parallel re-implementation, and nothing under test is mocked away (the only patches are
  the backoff sleep, `os.environ`, and the two deliberate `Path.write_text`/`Path.unlink`
  failure injections). 8 consecutive runs, no flake.
- **Test blindness (mutation testing, full suite each time).** All twelve were caught, with
  the failing test naming the exact property: drop `_defang_in_flight` from the stderr tail
  (`leaves.py:1005`) or from the withdrawn residue (`:984`); relax `leaf_run_incomplete`
  (`:904`) to a last-line substring or a whole-file sniff; keep the log even when the
  artifact was produced (`:743`); make the flush non-atomic (`:815`); settle before the
  placeholder (`:2818`); make `_empty_run_class` always substantive (`:2866`); delete both
  advisory settles (`:3176`, `:3480`); retry without ownership of the artifact (`:759`);
  retry over an unrecorded predecessor (`:761`); revert `assemble.py:425` to a bare
  `.exists()`. Round 2's two demonstrated blind spots are closed.
- **Impersonation.** I could not construct a leaf-controlled payload that flips either
  discriminator: the marker is defanged in both quoted bodies and matched as the whole last
  non-blank line, and trailing whitespace, a defanged copy, a marker straddling the
  `_RESIDUE_KEEP` truncation and a marker mid-body all fail. The one body that is *not*
  defanged — the `(no output captured) {type(exc).__name__}: {exc}` fallback at
  `leaves.py:1007` — carries `CalledProcessError`'s own text (argv + exit code), which is
  operator config rather than leaf output, and its worst case is a wasted re-run, not a
  missing review; criterion (iv) names only the two quoted bodies, so I am not filing it.
- **Paths the tests do not drive.** A 3-attempt run mixing a residue-less death, a
  residue-leaving death and a silent success files all three records in order, withdraws only
  the dead attempt's file, keeps the account, classifies it infra and leaves no stray
  `*.tmp.<pid>`. On the give-up path a flush that fails to land can leave a log still marked
  in flight (no settle runs there), but it is inert for the same reason as finding 2 — the
  placeholder exists, so every reader short-circuits.
- **Already adjudicated, deliberately not re-filed:** a `#369` recovery re-run destroys the
  dead attempt's preserved text via the frozen staleness clear at `leaves.py:718`. That is
  the round-1 adversary finding the human explicitly deferred to Act under criterion (vi);
  the composition (preserve at `:753` → destroy at `:718`) is unchanged by this round.

### Advisory — code-review

# Advisory code review — correctness + reuse/simplification (issue #64 lens)

Scope: `template/src/pdca_harness/{leaves,driver,assemble,state}.py` and
`template/tests/test_attempt_ownership.py`, as changed by patch.diff (issue #506:
attempt-as-unit-of-accountability for the reviewer/advisory/plan-advisory retry
wrapper). Grounded on `$PDCA_TARGET/template/src/pdca_harness/leaves.py`.

## Findings

- NEEDS-HUMAN [impl] — `leaves.py:2804-2807` (mirrored at `leaves.py:3167-3170` and
  `leaves.py:3470-3473`): the `err is not None` branch of all three harvest sites
  (`_run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`)
  files the "leaf failed" placeholder via `_review_unavailable`/`_advisory_unavailable`/
  `_plan_advisory_unavailable` but never calls `_settle_leaf_record`. This relies on the
  invariant that the retry loop's own last `_write_attempt_records(..., in_flight=False)`
  call (`leaves.py:760`) already settled the log before breaking. That invariant holds
  only when that final write *succeeds*. If it fails (`_atomic_write_text` raises
  `OSError`, e.g. a transient disk error) while a *prior* attempt's write already landed
  with `in_flight=True` (`leaves.py:744`/`760` when `may_retry` was still `True` on an
  earlier iteration), `_write_attempt_records` reports the failure and returns `False`
  (`leaves.py:845-853`) but leaves the on-disk file exactly as the prior successful write
  left it — still carrying `_LEAF_IN_FLIGHT`. The loop then breaks (`leaves.py:761-762`,
  `not (may_retry and recorded)`), `err is not None` at the call site, and the "leaf
  failed" placeholder is written to the bundle — while the error log itself is still
  read by `leaf_run_incomplete`/`_leaf_ran_and_failed` as *in flight*. The next `advance`
  will then treat this leaf as never-run (`review_never_ran` / `only_missing`) and
  re-run and re-pay it, even though a "reviewer leaf failed: …" verdict was already filed
  for it — the same "leaf recorded as two contradictory things" conflation issue #506
  otherwise sets out to remove. This is a narrow window (requires a disk write failure on
  a *non-first* attempt specifically), and it is a strict improvement over the pre-patch
  code's unguarded final `write_text` — but nothing in `test_attempt_ownership.py` drives
  a write failure on a middle/last attempt after an earlier one already landed (the one
  write-failure case that's tested, `test_a_retry_never_starts_without_its_predecessors_
  account_on_disk`, refuses *every* write from attempt 1, so no stale in-flight marker is
  ever created). Consider settling (or re-checking) the log in the `err is not None`
  branches too, or making `_write_attempt_records`'s failure path itself strip a stale
  in-flight trailer it can no longer trust.

- Reuse/simplification (non-blocking) — `leaves.py:2789-2823`, `3158-3176`,
  `3462-3480`: the three harvest sites are near-identical, and the patch (by its own
  in-code admission at `leaves.py` comments "the reviewer's two near-identical twins")
  threads the same five-line attempt-aware harvest sequence (`artifact=…`, the
  `err is not None` branch, `out.exists()`/`produced.exists()`, the `_empty_run_class`
  call, the `_settle_leaf_record` call) through all three copies by hand. That's exactly
  the shape that let the gap above land identically in all three places rather than
  once. A small shared helper (e.g. `_harvest_leaf(d, out, dest, error_log, err, ...)`)
  encapsulating "copy on success / `_*_unavailable` + settle on empty / `_*_unavailable`
  on `err`" would remove the duplication and make the settle-call omission structurally
  impossible to repeat at a fourth site later.

Everything else in the diff — the `_LEAF_IN_FLIGHT` marker/defang scheme, the atomic
write, `_withdraw_residue`'s fail-closed ownership handshake, the `#369` discriminator
updates in `driver.py`/`assemble.py`/`review_never_ran`, and the new
`test_attempt_ownership.py` coverage — reads correctly against the target source and is
exercised by a real production-path test suite (confirmed against
`gate-logs/T3-suite.log`: 1780 driver-suite tests green, `gate-logs/C4-verify.log`
red→green). No other correctness bugs or reuse gaps found.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm no overlapping merged or closed/rejected work for every affected path — the disposable target contains one synthetic base commit and no remotes, so the brief's prior-art claim cannot be mechanically re-derived here and overlap would affect contribution safety.
- [ ] Validation — fitness-to-purpose — Decide whether the operational post-mortem guarantee is acceptable only after the withdrawal-before-persistence kill window is resolved — the normal suite is green but misses a core process-death boundary.
- [ ] `leaves.py:2804-2807` (mirrored at `leaves.py:3167-3170` and

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
- Iteration delta (if iterating): Rejected on the findings, not on approach or slicing — for the third time, and the mechanism is holding up: C4 red→green reproduced independently, twelve targeted mutations of the new production logic all caught, 1780-test driver suite green, no impersonation payload flipped either discriminator, `test_leaf_resilience.py` untouched and green. Same slice, same design. Close the items below and keep the diff from growing — it is already flagged oversized, so prefer the minimal edit at each site over a refactor. 1. Close the withdraw-before-persist kill window (the reviewer's C3/C5/T3 FAIL, `leaves.py:986` / `:760`). `_withdraw_residue` reads the dead attempt's text into memory and `unlink()`s the artifact, and only afterwards does the caller persist the record — a kill in that gap loses BOTH the dead attempt's text and its account (`runs=1 bundle_artifact=False error_log=False`). It is narrower than the base's window, not a regression, but it is the exact no-artifact/no-account state this slice exists to eliminate, and it is cheaply closable: persist the record (residue text included) BEFORE the unlink, then unlink. The ordering knot is that `in_flight` depends on `owned`, which depends on the unlink having succeeded — resolve it by flushing first with `in_flight = transient and attempt < attempts`, then withdrawing, then re-flushing with `in_flight=False` if the unlink was refused. The fail-closed stop on a refused withdrawal stays exactly as it is. 2. Settle (or distrust) the log in the three `err is not None` harvest branches (`leaves.py:2804-2807`, mirrored `:3167-3170`, `:3470-3473`). All three file the `*_unavailable` placeholder but never call `_settle_leaf_record`, relying on the loop's final `_write_attempt_records(..., in_flight=False)` having landed. When that write fails on a NON-first attempt after an earlier one already landed in flight, the file keeps its in-flight trailer while a "leaf failed" verdict sits in the bundle — `review_never_ran` / `only_missing` then re-run and re-pay for a leaf whose outcome is already filed, which is the same "one leaf recorded as two contradictory things" this change removes. Fix at either end (settle in the `err` branches, or have `_write_attempt_records`'s failure path strip a trailer it can no longer trust). Add the test that is missing: a write failure on a middle/last attempt AFTER an earlier attempt's in-flight write landed — the existing write-failure test refuses every write from attempt 1, so it never creates the stale marker. 3. Fix the two claim-accuracy defects — prose and rationale only, no behaviour change. In a slice whose whole invariant is "never file a false account of a run", what the harness tells the operator has to be true too. - `leaves.py:2910`: for a run whose attempt 1 died transiently (`overloaded_error 529`) and whose attempt 2 exited 0 having written nothing, `_FAIL_TRANSIENT`'s prose says "retries did not recover" — but they did; the recovered attempt produced no verdict. The class (`infra-empty`) and the action ("safe to re-run") are right; only the account is wrong. Widen the wording, or give the empty-run shape its own. Also strengthen `test_attempt_ownership.py:363-365`, which asserts only the class and the substring "safe to re-run" and is therefore true of the wrong sentence too. - `leaves.py:919-921` and the tests at `test_attempt_ownership.py:607-609`, `:523-525`: the settle's stated justification ("otherwise a leaf that gave up looks recoverable forever and is re-run and re-paid for on every advance") is unwarranted — every reader short-circuits on the placeholder first, and deleting the settle leaves `review_never_ran` False regardless. Restate it as what it is: archive hygiene, plus the genuinely load-bearing half — settle AFTER the outcome is filed, never before — which is already correct and separately proven. Fix the rationale, not the code, so a later maintainer does not read the settle as a recovery guard. Do NOT widen the slice: - The shared `_harvest_leaf` helper the code review suggests for the three near-identical harvest sites is a good idea and an Act candidate, NOT this round's work. Closing item 2 at three sites by hand is smaller than the refactor, and this patch is already oversized. - Leave the staleness clear at `leaves.py:718` alone — criterion (vi) freezes it and two prior sign-offs adjudicated the recovery-re-run/preserved-text interaction as a deliberate Act deferral. - The non-atomic `shutil.copy2` of the verdict at the three harvests and the strandable `*.error.log.tmp.<pid>` remain noted, not hardened here. - Do not touch the retry set, `LeafError.transient`, `progress.py` (sibling #538 owns it) or the builder path. Keep `test_leaf_resilience.py` untouched.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
