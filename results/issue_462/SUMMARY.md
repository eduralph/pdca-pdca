# Result — issue 462 / merge-wave-waits-for-its-evidence

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In `wave_mode = "merge"`, a non-final wave's PRs are opened by `_publish_bundle`
  and merged **seconds later** by `merge.merge_wave`, before their required checks have had
  any chance to report. `_merge_one` (`template/src/pdca_harness/merge.py:127-204`) does three
  things back to back with no wait anywhere: `gh pr ready` (`:158-165`), then the full
  check-rollup gate (`:175-194`), then `gh pr merge` (`:196-204`). A PR created seconds ago has
  checks that are queued or not yet registered, so `_check_rollup` returns `pending` (a job
  still running/queued) or `empty` (no check reported yet) and `_merge_one` returns 1 — the run
  STOPs. **Nothing was wrong**: the evidence had simply not arrived. And the STOP is not clean —
  `gh pr ready` already succeeded, so that PR is left **non-draft**, advertising a readiness no
  human granted, while every later bundle in the wave keeps its draft, is never touched, and no
  later wave runs.
  Observed at getwyrd/wyrd-pdca 2026-08-08, wave 691/695/696/697: `getwyrd/wyrd#703` created
  `15:57:37Z`, `ready_for_review` `15:57:43Z` — six seconds later — merge refused; #704/#705/#706
  untouched; the repo's required `gate` context depends on `rust` + `tikv`, both still running.
  **Correction to the issue text, verified on the target base:** the report predates #413
  (PR #484, `2261b53`, merged 2026-08-11), which added the rollup gate at `:175-194`. The
  failure now lands one line earlier and with a precise message ("a check has not finished"),
  but the two defects the issue names are untouched: **the run still treats "the evidence has
  not arrived yet" as a terminal verdict**, and **it still leaves a readied PR behind when it
  declines**. `merge_requires = "required"` does not help either — it skips the rollup gate and
  hands the same race to `gh pr merge`, which refuses a `BLOCKED` PR just as immediately.
- Success criterion: With the patch, `merge.merge_wave` at a non-final wave boundary:
  (i) **waits** while the rollup verdict is `pending` or `empty`, re-reading it until it
  resolves or a **bounded, configurable** wall-clock limit expires — a rollup that turns green
  after the checks report is merged, and the run continues into the next wave;
  (ii) still **refuses and STOPs** — no merge, non-zero, later waves not run — on `failing`,
  on `unreadable`, and on a `pending`/`empty` rollup that is still unresolved when the bound
  expires, with a message that distinguishes "the checks never reported within Ns" from "a
  check is red";
  (iii) on **every** path where it declines to merge a PR it readied — the rollup refusal, the
  bound expiring, and a failing `gh pr merge` — that PR is returned to **draft** before
  `_merge_one` returns non-zero, so a stopped wave leaves no PR advertising a readiness no
  human granted; an already-merged or dry-run path readies nothing and undoes nothing;
  (iv) the existing contract is unchanged otherwise: dry-run shells nothing, a close/no-fix or
  already-merged bundle is skipped, a COMPLETE bundle with no recorded PR still fails closed,
  and `merge_requires = "required"` still skips the rollup gate.
  Demonstrable by C4-verify: `template/tests/test_merge.py` drives `merge.merge_wave` with
  every `gh`/`git` call mocked (`_gh(checks=…, ready=…, merge=…)`, `:50-60`) and asserts the
  exact verb sequence, so (i)-(iv) are assertions over recorded argv, offline and instant.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The non-final-wave merge boundary in `template/src/pdca_harness/merge.py`: make
  the boundary wait for the rollup to resolve within a bounded, configurable limit, and make
  every decline restore the draft state it changed. The bound is new configuration — plumb it
  through `Config` the way `merge_requires` is plumbed (`config.py:361-368`, `:703-707`,
  `:813`) and document it in the `[driver]` block of `template/pdca.toml.jinja` beside
  `merge_requires`, including what a sensible default is and that `0` means "do not wait"
  (today's behaviour). **Out of scope:** `gh pr merge --auto` (the issue's option A) — the
  driver must know the base has actually moved before the next wave's Do worktree resets to
  it, so `--auto` would need a second wait bolted on anyway, and it would relax the STOP
  discipline to PRs the run never confirmed merged; `docs/07-crosscutting.md` and
  `docs/05-check.md` (476 owns the former in this run; the `[driver]` block is this knob's
  documentation home, as it is for `merge_requires`); `wave_mode = "stack"` and the
  integration-fold path; publish, the reviewer, and any change to what `_check_rollup`
  classifies; retrying a *failing* check (a red check is a genuine stop).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Task under review: make merge-mode wave boundaries wait for pending or absent PR-check evidence within a configurable bound and restore draft state whenever a readied PR is not merged.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable contract is explicit about pending/empty resolution, timeout refusal, draft restoration, and the zero-wait escape hatch (`template/pdca.toml.jinja:142`). |
| C2 Reproduction (red pre-fix) | PASS | Independently retaining the patched tests against pre-fix production produced 7 failures/errors, including pending-to-green and ready-undo expectations (`template/tests/test_merge.py:271`). |
| C3 Change | FAIL | The configured safety bound must limit actual elapsed time, but the loop increments only requested sleep seconds and excludes every rollup-call duration, so it is not the promised wall-clock bound (`template/src/pdca_harness/merge.py:153`). |
| C4 Verification (red→green) | PASS | Independent re-run was red with pre-fix production and green 24/24 with the patch; the exercised production import and pending-to-green case are at `template/tests/test_merge.py:37` and `template/tests/test_merge.py:289`. |
| C5 Causal adequacy | PASS | The change removes the immediate-verdict behavior by re-reading pending/empty evidence and restores state on both refusal exits; it adds no capability probe or symptom guard (`template/src/pdca_harness/merge.py:153`, `template/src/pdca_harness/merge.py:248`). |
| T1 Structure | PASS | Waiting and ready-state rollback are isolated helpers with configuration passed through the existing merge boundary (`template/src/pdca_harness/merge.py:143`, `template/src/pdca_harness/merge.py:163`). |
| T2 Shape | PASS | Both frozen docs/host-CI lint-and-render logs are green, and the new scalar remains in the documented `[driver]` block (`template/pdca.toml.jinja:142`). |
| T3 Runtime | FAIL | A direct exercise with a 1s configured bound and 0.6s rollup latency measured 2.20s, confirming that slow `gh pr checks` calls can overrun the advertised limit (`template/src/pdca_harness/merge.py:153`). |
| T4 Contribution | N/A | The contribution gate was deferred because `pr-description.md` is intentionally drafted later; its substantive audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm no merged, closed, or rejected prior work already covers these four affected paths — the disposable target has one synthetic base commit and no remote, so the brief's affected-path prior-art claim cannot be mechanically settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the 300s default and 15s polling cadence fit the repository's real CI-registration latency and draft-governance expectations — that choice determines whether merge waves progress without premature STOPs (`template/src/pdca_harness/config.py:369`). |

### Advisory — code-review

# Advisory code review — issue #462 (merge-wave-waits-for-its-evidence)

Second lens: bugs the patch itself introduces, and reuse/simplification/efficiency.
Grounded on `target/template/src/pdca_harness/{merge.py,config.py}`,
`target/template/tests/test_merge.py`, `target/template/pdca.toml.jinja` (post-patch).

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:143-160` (`_wait_for_green`):
  the bound is tracked as a count of *sleep* seconds (`waited += step`), not elapsed
  wall-clock time. Each `_check_rollup` call is a real `gh pr checks` subprocess (network
  round-trip); its latency is never added to `waited`, so the loop's actual wall-clock
  duration is `merge_wait_secs` plus the cumulative latency of up to
  `merge_wait_secs / 15` `gh` calls. For a slow `gh`/host this can meaningfully overshoot
  the configured bound the success criterion calls "bounded, configurable" (brief §Success
  criterion (i)/(ii)). A `time.monotonic()`-based deadline (`deadline = _now() + wait_secs;
  while verdict in (...) and _now() < deadline: ...`) would be both tighter and no harder
  to keep patchable for tests (the mocked `_sleep` already costs zero real time, and the
  mocked `_check_rollup`/`subprocess.run` calls are instant in the suite, so a real clock
  read would not slow `test_merge.py` down). Low severity — bounded overshoot, never
  unbounded — but worth tightening since "bounded" is the literal invariant being restored.

- NEEDS-HUMAN [impl] — `template/tests/test_merge.py`: every new/updated case that
  exercises the `_undo_ready` path uses a `failing`, `pending`-timeout, or `gh pr merge`
  failure verdict (`test_merge_failure_stops:157-159`,
  `test_failing_check_refuses_and_never_merges:268-269`,
  `test_pending_check_refuses:285-287`,
  `test_wait_bound_zero_performs_no_wait:414-420` in the patched file). None drives an
  `unreadable` rollup (`merge.py:239`, `_check_rollup`'s fifth verdict, unchanged by this
  patch) through `_merge_one` and asserts the `gh pr ready --undo` call. The code path is
  the same `if verdict != "green": ... _undo_ready(pr_url)` branch used for the other three
  verdicts (`merge.py:232-248`), so this is very likely a correct-by-construction case, not
  a live bug — but the brief's own success criterion (ii) names `unreadable` explicitly
  alongside `failing`/timeout as a path that must both STOP *and* restore draft (iii), and
  right now nothing in the suite would catch a future edit that special-cased `unreadable`
  differently (e.g. someone "optimizing" the dict-branch dispatch). A `_drive(...,
  checks=SimpleNamespace(returncode=1, stdout="", stderr="boom"))` case mirroring
  `test_failing_check_refuses_and_never_merges` would close the gap cheaply.

## Not flagged (checked, found clean)

- `_wait_for_green`'s loop always makes forward progress (`step >= 1` whenever the loop
  guard is true, since `wait_secs - waited >= 1` there) — no infinite-loop or zero-sleep
  risk; `merge_wait_secs = 0` is a genuine single-read no-op (`merge.py:148-152`,
  confirmed against `test_wait_bound_zero_performs_no_wait`).
- `config.py:719-729` mirrors the existing `merge_requires` fail-closed pattern exactly
  (bad type → default, out-of-range → default, both warn on stderr) — no new validation
  gap, no crash on a malformed `pdca.toml`.
- `merge_wait_secs` is inserted in `pdca.toml.jinja` before the next `[install]` header
  (`:153`), so it lands in `[driver]` as intended — the file's own "silently joins the
  next table" trap (cited in the brief) is avoided.
- Every decline path that follows the ready-mark (`rollup != green`, and a failing
  `gh pr merge`) now calls `_undo_ready` (`merge.py:248`, `:261`); the `gh pr ready`
  failure path (`:211-216`) correctly does *not* call it, since that call never marked
  the PR ready in the first place.
- No duplicated rollup-classification logic — `_wait_for_green` calls `_check_rollup`
  rather than re-deriving the bucket rules, as the brief's citation directs.
- Scope matches the brief: only `merge.py`, `config.py`, `pdca.toml.jinja`, and
  `test_merge.py` are touched; `docs/07-crosscutting.md` and `docs/05-check.md` are
  untouched, as declared out of scope.
- C4-verify's logged red leg (`gate-logs/C4-verify.log`) genuinely fails on production
  reverted (`AttributeError: 'Config' object has no attribute 'merge_wait_secs'` plus the
  old-behaviour assertion failures) and genuinely passes with the fix — the regression
  test exercises the real defect, not a copy.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm no merged, closed, or rejected prior work already covers these four affected paths — the disposable target has one synthetic base commit and no remote, so the brief's affected-path prior-art claim cannot be mechanically settled here.
- [x] Validation — fitness-to-purpose — Decide whether the 300s default and 15s polling cadence fit the repository's real CI-registration latency and draft-governance expectations — that choice determines whether merge waves progress without premature STOPs (`template/src/pdca_harness/config.py:369`).
- [x] `template/src/pdca_harness/merge.py:143-160` (`_wait_for_green`):
- [x] `template/tests/test_merge.py`: every new/updated case that
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
