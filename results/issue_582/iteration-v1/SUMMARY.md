# Result — issue 582 / merge-wait-confirms-green

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Under `[driver].wave_mode = "merge"`, `merge._wait_for_green`
  (`template/src/pdca_harness/merge.py:143-160`) re-reads a PR's check rollup only while it
  is `pending` or `empty` (`merge.py:155`) and returns the first `green` it sees. In the
  seconds after a PR is opened/readied, the rollup reports only the checks that have
  registered SO FAR: one fast workflow that already passed (a DCO or issue-link check)
  reads as a clean `green` (`_check_rollup`, `merge.py:126-130`) while a slow job has not
  created its check run yet. `_merge_one` then merges on that partial green
  (`merge.py:229-231`). If the slow job is host-required, `gh pr merge` refuses and the wave
  stops; if it is not required — the thin-branch-protection case `merge_requires = "all"`
  exists for — the PR merges and the check fails afterwards on the base. The same applies to
  a green reached through the loop (`empty → green` or `pending → green`): that read can be
  just as partial.
- Success criterion: Through `merge.merge_wave` (the public entry `flow` calls,
  `merge.py:70-79`), with `subprocess.run` and `merge._sleep` patched as in
  `tests/test_merge.py:289-314`:
  (i) **A green is believed only once it has held.** When a rollup read says `green`, the
  wait re-reads once more, one poll interval later (charged to the `merge_wait_secs`
  budget), and treats the PR as green only if that second read is also `green`. Probe:
  reads `green(dco)`, then `pending(dco pass, e2e pending)`, then `green(dco, e2e)`,
  `green(dco, e2e)` → **merges, and only after the 4th read**; reads `green(dco)`, then
  `failing(e2e fail)` → **does not merge**, returns non-zero, names the failing check, and
  undoes the ready-mark (`gh pr ready --undo`) exactly as a failing rollup does today
  (`tests/test_merge.py:258-269`).
  (ii) **A confirm that does not hold re-enters the wait** — a `pending`/`empty` second read
  goes back into the bounded loop; `failing`/`unreadable` returns at once (no further reads).
  (iii) **The bound holds.** Total slept time never exceeds `merge_wait_secs` (sum of the
  `_sleep` arguments ≤ the bound). A green that first appears when no budget is left for
  its confirm is **not** believed: it is returned as `pending` (the module's fail-closed
  direction, `merge.py:59-63`), so the existing "not finished within Ns" refusal message
  applies, with a detail that says why: the `detail` returned with that `pending` must name
  the green as unconfirmed (e.g. `green first seen with no wait budget left to confirm it
  (2 checks)`), so the refusal reads "a check has not finished within Ns — green first seen
  with no wait budget left to confirm it (2 checks)" rather than a bare count; a test asserts
  `unconfirmed`/`confirm` appears in stderr. This is an intended behaviour change for small
  budgets: with `merge_wait_secs = 15`, `pending → green` merges today and is refused after
  the fix (no budget left to confirm). Operators with slow checks raise `merge_wait_secs`.
  (iv) **`merge_wait_secs <= 0` is unchanged:** exactly one rollup read, no sleep, its
  verdict returned as-is (`tests/test_merge.py:316-328` keeps passing).
  (v) **Nothing else changes.** `_check_rollup`'s classification, `merge_requires =
  "required"` skipping the gate (`tests/test_merge.py:417-425`), the order ready → rollup
  read(s) → merge, and the ready-undo on every decline stay as they are. Two existing tests
  change on purpose, and only these two: `test_pending_then_green_merges`
  (`tests/test_merge.py:289-314`) expects **4** reads (pending, pending, green, green), and
  `test_all_green_readies_then_checks_then_merges` (`:329-334`) expects the gh sequence
  `[ready, checks, checks, merge]` (the confirm read). The whole `template/tests` suite
  stays green **and does not get slower**: four tests reach a green rollup without patching
  `merge._sleep` (`test_merges_then_fetches_base` `:105-121`, `test_merge_failure_stops`
  `:139-160`, `test_readies_before_merging` `:162-182`, `test_first_failure_stops_the_wave`
  `:218-228`) and would each sleep a real 15 s after the fix — patch `merge._sleep` once in
  `MergeWave.setUp` (`mock.patch.object(merge, "_sleep")` + `addCleanup(...stop)`) so no
  test in the class sleeps for real. Tests that already patch it in their own `with` keep
  working (a nested patch).
  Shown by the named test going red on `main` (it merges on the first green read) and green
  with the fix.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make `_wait_for_green` confirm a green before returning it, per (i)–(iv) above,
  and update its docstring and the module docstring's description of the wait
  (`merge.py:33-42`) to say a green is confirmed once, and the two operator-facing comments
  that describe the wait rule ("re-reads the rollup until it clears pending/empty"):
  `template/pdca.toml.jinja:144-151` and `template/src/pdca_harness/config.py:375-381`. / out
  of scope: comparing check NAMES
  or counts between reads, or waiting for a configured list of expected checks (a richer
  design — file separately if wanted); changing `poll_interval` (15 s) or the
  `merge_wait_secs` default (300); stack mode (`integrate.fold`), which never merges.

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

Review issue #582: require a second green check-rollup read before merge-mode waves merge a PR, within the configured wait budget.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines an offline-falsifiable, bounded confirmation contract and explicitly excludes check-set completeness; the target documents the same interval and residual risk (`brief.md:21`, `brief.md:65`, `target/template/src/pdca_harness/merge.py:155`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the regression tests reproduced seven assertion failures, including merging after the initial partial green (`target/template/tests/test_merge.py:468`, `review-red.log:102`). |
| C3 Change | FAIL | A positive budget shorter than one poll interval permits premature confirmation: budgets 1 and 20 merge after confirmation delays of 1 and 5 seconds, violating the required 15-second separation (`target/template/src/pdca_harness/merge.py:182`, `review-boundary.log:1`). |
| C4 Verification (red→green) | PASS | The supplied regression suite independently changed from seven failures to all 30 tests passing after production changes were restored; this establishes the tested cases, not the omitted short-interval boundary in C3 (`review-red.log:102`, `review-green.log:3`, `target/template/tests/test_merge.py:468`). |
| C5 Causal adequacy | PASS | For the scoped partial-green race, tests drive the real merge entry point and demonstrate refusal when the next read fails; no capability probe or load-time symptom guard was introduced, while completeness remains explicitly unproved (`target/template/tests/test_merge.py:460`, `target/template/src/pdca_harness/merge.py:159`). |
| T1 Structure | PASS | The change stays within the existing wait helper, its test class, and the two planned configuration comments, preserving the merge caller and rollup classifier (`target/template/src/pdca_harness/merge.py:147`, `target/template/src/pdca_harness/config.py:380`, `target/template/pdca.toml.jinja:151`). |
| T2 Shape | PASS | Independent diff whitespace checking, docs lint, and the 22-page site render/link audit passed; frozen host-parity output confirms the same checks (`gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent offline driver run passed 2,221 tests with two skips in 43.056 seconds; frozen evidence also shows all 24 root render/update tests passing, which cannot be fully rerun with this copy's missing release history (`review-suite.log:1767`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is deferred to the mandatory publish-time rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm upstream novelty across all affected paths and closed/rejected work — the brief records a path-based merge.py search, but this copy has only a synthetic base commit and no remotes, so independent history/PR confirmation and the other affected paths remain unsettled (`brief.md:113`, `target/template/docs/INTEGRATION.md.jinja:83`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether one full interval of verdict stability is sufficient for deployment after C3 is addressed — checks registering later, or a changed all-green check set, can still allow an unsafe merge, so this does not fully close the underlying issue (`target/template/src/pdca_harness/merge.py:159`, `brief.md:68`). |

**Advisory finding — P2: require enough budget for a full confirmation interval.** At `target/template/src/pdca_harness/merge.py:179`, only an entirely exhausted budget is rejected. The `min(...)` at line 182 then shortens the confirmation sleep to whatever remains. Through the existing `_drive_reads` helper calling the production `merge_wave` entry point, I observed:

| Budget | Rollup sequence | Sleep arguments | Observed outcome |
|---|---|---|---|
| 1 second | green → green | `[1]` | Returns 0 and calls merge after a 1-second confirmation. |
| 20 seconds | pending → green → green | `[15, 5]` | Returns 0 and calls merge after a 5-second confirmation. |

Both configurations are accepted integer budgets (`target/template/src/pdca_harness/config.py:736`). They shorten the window in which a slow job can register below the 15 seconds promised by the brief and operator comment (`brief.md:22`, `target/template/pdca.toml.jinja:151`). Refuse as unconfirmed when the remaining budget cannot fund a full poll interval, and cover both boundaries through `merge_wave`. This is separate from the explicitly accepted residual risk of jobs registering after a full interval. Evidence: `review-boundary.log:1` and `review-boundary.log:2`.

Independent verification used the disposable target only: stash the three production/comment files, run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_merge.py` from `target/template`, restore the stash, and rerun. Temporary test artifacts were directed inside this review workspace. The restored target diff exactly matches `patch.diff`. The same interpreter ran the full offline suite. Additional probes confirmed that an empty confirmation resumes waiting (four reads, sleeps `[15, 15, 15]`) and a negative direct wait budget preserves the single-read/no-sleep behavior (`review-boundary.log:3`). No real PR was readied or merged; subprocess calls in these probes were mocked.

All six frozen gate logs were inspected. Instance-scoped wrappers were not treated as target files. The production-path scanner reported only “patch adds no new test file”, so its green is not treated as proof of production coverage; that coverage was established by the public-entry-point reruns (`gate-logs/C5-prod-path.log:10`, `target/template/tests/test_merge.py:460`). Root update-compatibility evidence comes from the frozen run because the disposable target has no release tags; this is a target-history limitation, not a patch defect or an unsatisfied dependency in the recorded gate run. The brief declares no external dependencies, and the offline fixture can exhibit the forbidden partial-green merge. No additional project-specific human-only items are enumerated in the supplied integration template (`target/template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation ran `git log --all --oneline --` with all four affected paths and inspected remotes: only synthetic commit `8158ec5` was available and no remote was configured. The brief's historical claims therefore remain attributed to the brief rather than independently confirmed. No other checkout was consulted. The verdicts above are advisory and do not gate acceptance.

### Advisory — code-review

# Advisory code review — issue 582 / merge-wait-confirms-green

No correctness bugs found. I traced the new wait loop at `template/src/pdca_harness/merge.py:168-187` through every case in brief (i)–(iv):

- green → green merges; green → failing or unreadable returns after 2 reads; green → pending/empty goes back into the wait.
- A green that shows up with `waited >= wait_secs` comes back as `pending` with the "unconfirmed" detail, and `_merge_one` (`merge.py:261-262`) shows it as "a check has not finished within Ns — green first seen with no wait budget left to confirm it (N checks)".
- A confirm read that is pending/empty after the budget is gone skips the inner loop and returns that verdict as-is, so the existing refusal messages still fit.
- `wait_secs <= 0` returns early (`merge.py:168-169`) with a single read.
- Every sleep is `min(poll_interval, wait_secs - waited)`, so the total sleep never goes over the budget. Each pass of the outer loop sleeps at least once while budget is left, so the loop always ends (for the only caller's `poll_interval=15`).

Gate logs agree: C4 is red before the fix and green after (`gate-logs/C4-verify.log`), and T3 ran 2221 tests OK in about 44 s, so the `setUp` sleep patch did its job (`gate-logs/T3-suite.log`).

Minor findings, none blocking:

- `template/src/pdca_harness/merge.py:173-176` and `merge.py:182-185`: the same four lines (step, sleep, add to `waited`, re-read) appear twice. A small inner helper, or folding the confirm into one loop with a `seen_green` flag, would remove the copy. Optional; the current form is easy to read.
- `template/tests/test_merge.py:439-462`: `_drive_reads` mostly repeats `_drive` (`test_merge.py:240-260`). The only differences are a list of rollup reads instead of one fixed result, and returning the sleep arguments. `_drive` could take an optional `reads=` instead. It also patches `_sleep` again on top of the new class-wide patch in `setUp`; that works because the patches nest, and it is needed to read the sleep arguments. Cosmetic only.
- The known gap (the confirm compares only the verdict, so `green(dco)` → `green(dco)` still merges) is stated in the brief, the docstring (`merge.py:157-159`) and the operator comments. It is not a defect in this patch, but the issue should not be closed as fully fixed. The brief already says Check must not count it closed.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm upstream novelty across all affected paths and closed/rejected work — the brief records a path-based merge.py search, but this copy has only a synthetic base commit and no remotes, so independent history/PR confirmation and the other affected paths remain unsettled (`brief.md:113`, `target/template/docs/INTEGRATION.md.jinja:83`).
- [x] Validation — fitness-to-purpose — Decide whether one full interval of verdict stability is sufficient for deployment after C3 is addressed — checks registering later, or a changed all-green check set, can still allow an unsafe merge, so this does not fully close the underlying issue (`target/template/src/pdca_harness/merge.py:159`, `brief.md:68`).
- [x] **(v) "the whole suite stays green" cannot hold if only one test is updated.** The brief allows updating just `test_pending_then_green_merges` (brief "Test file" line; (v)). But `test_all_green_readies_then_checks_then_merges` (`template/tests/test_merge.py:329-334`) asserts the exact `gh pr` sequence `[ready, checks, merge]`. Once a first-read green is confirmed, that sequence becomes `[ready, checks, checks, merge]` and the test fails. The brief also says "the ready→read→merge order … stay as they are", which directly contradicts the confirm. The brief needs to name this second test update and say what the new expected sequence is. Otherwise Do faces a choice between breaking (v) and quietly editing a test the brief didn't authorize.
- [x] **Tests that don't patch `merge._sleep` will start sleeping for real.** Today a first-read green never sleeps. After the fix it always sleeps one `poll_interval` (15 s) before the confirm read. Four tests reach a green rollup without patching `_sleep`: `test_merges_then_fetches_base` (`test_merge.py:114-118`), `test_merge_failure_stops` (`:150-154`), `test_readies_before_merging` (`:172-176`), and the `ok` bundle in `test_first_failure_stops_the_wave` (`:224-228`). That adds about 60 s of real `time.sleep` to the suite (`merge.py:58`). The brief doesn't mention it. It should either require patching `_sleep` in those tests (more test changes outside the one named) or accept the slowdown explicitly.
- [x] **The "Invariant to restore" claims more than the fix delivers, and the success criterion never tests the case that's still open.** The invariant reads "merges a PR only on evidence that the PR's whole check rollup is complete". But the fix compares verdicts only, and the brief puts "comparing check NAMES or counts between reads" out of scope. If a slow job takes longer than one poll interval (15 s) to register, the sequence `green(dco)`, `green(dco)` still merges on a partial rollup. So does `green(dco)` → `green(dco, e2e)`, where the confirm "holds" on a different set of checks. The probe in (i) is picked so the slow check shows up inside the window. The brief should restate the invariant as what this fix actually narrows (partial greens that change within one poll interval). It should also list the `green(dco)` ×2 case as a known residual, so a reviewer doesn't count the bug as fully closed.
- [x] **(iii)'s refusal message will read wrong, and the brief doesn't say how to fix it.** (iii) returns a late, unconfirmed green as `pending`. The detail carried with a green verdict is a count, `"N checks"` (`merge.py:130`). `_merge_one` would then print "a check has not finished within 300s — 2 checks" (`merge.py:235-236`), which names no pending check. The brief's own "Citations expected" line says these messages "must still read right" but doesn't say what the detail should become. It should state the expected detail text and add a test assertion for it. (iii) is also a real behaviour change for small budgets: with `merge_wait_secs = 15`, the sequence pending → green merges today but will be refused after the fix. The brief should say that's intended, not just "the bound holds".
- [x] **Operator-facing docs describing the wait are outside the scope.** The scope covers only the docstrings in `merge.py`. But the rendered config template describes the old rule to operators: "re-reads the rollup until it clears pending/empty" (`template/pdca.toml.jinja:148-150`). The `Config.merge_wait_secs` comment says the same (`template/src/pdca_harness/config.py:378-381`). Both will be out of date once the fix lands. Either add them to scope (which breaks the brief's claim that "582 touches only `merge.py` + `tests/test_merge.py`", and that claim is what supports the no-conflict argument in the Ordering note) or leave them stale on purpose and say so.
- [x] **I couldn't verify the Ordering note's claims about the batch.** "No other bundle in the batch (589, 593, 597) touches `merge.py`/`test_merge.py`" has no `dependency-state.json` and no evidence in the bundle behind it. The only check left is the human's at sign-off, especially since the batch is forced into a single wave to avoid #593's stacking bug.

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
- Iteration delta (if iterating): Rejected for the C3 boundary gap found in review: when the remaining merge_wait_secs budget is less than one poll_interval, the confirm sleep is shortened via min(poll_interval, wait_secs - waited) (merge.py:182), so the confirm read lands 1-14 s after the first green (e.g. budget 1: green->green merges after 1 s; budget 20: pending->green->green merges after a 5 s confirm). That breaks the brief's "re-read one poll interval later" promise. Next attempt: only take the confirm read when a FULL poll interval of budget remains; if it does not, return the green as `pending` with the "unconfirmed" detail (same path as the no-budget-left case). Add tests through merge.merge_wave for both boundaries (budget 1 with green,green and budget 20 with pending,green,green -> both refused, no merge, ready undone). Everything else in the patch was accepted as-is; keep it.
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
