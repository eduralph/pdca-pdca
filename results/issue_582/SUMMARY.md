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

Review issue #582: require two green rollup reads a full 15-second poll interval apart before merge, refusing confirmation when the positive wait budget is insufficient.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded confirmation contract is falsifiable, including the revised 1s/20s boundaries and the unchanged nonpositive-budget exception; `target/template/tests/test_merge.py:558`, `target/template/src/pdca_harness/merge.py:165`. |
| C2 Reproduction (red pre-fix) | PASS | Independently retaining the new tests while stashing production changes reproduced premature merging, including green→failing and both rejected budget boundaries: 33 tests, 92 assertion failures; `reviewer-red.log:775`, `reviewer-red.log:802`, `reviewer-red.log:811`, grounded in `target/template/tests/test_merge.py:478`. |
| C3 Change | PASS | Insufficient confirmation time now refuses instead of merging after a shortened interval; budgets 1 and 20 also preserve ready-undo and explanatory refusal text; `target/template/src/pdca_harness/merge.py:185`, `target/template/tests/test_merge.py:558`, `target/template/tests/test_merge.py:573`. |
| C4 Verification (red→green) | PASS | Restoring the production patch independently turned the same 33 tests green, including the 90-case sequence/budget sweep; `reviewer-green.log:3`, `target/template/tests/test_merge.py:591`; frozen evidence agrees at `gate-logs/C4-verify.log:10`. |
| C5 Causal adequacy | PASS | The premature single-read decision is directly corrected for the scoped invariant, and tests call production `merge_wave`; no optional-capability probe or load-time symptom guard was added; `target/template/tests/test_merge.py:465`, `target/template/src/pdca_harness/merge.py:170`. |
| T1 Structure | PASS | The existing wait helper retains its interface and caller/refusal handling, keeping the change within the four planned files; `target/template/src/pdca_harness/merge.py:148`, `target/template/src/pdca_harness/merge.py:264`. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and diff whitespace check passed; operator guidance states that positive budgets below 15s refuse every PR; `reviewer-docs-lint.log:1`, `reviewer-docs-render.log:2`, `target/template/pdca.toml.jinja:151`. |
| T3 Runtime | PASS | Independent driver run passed 2,224 tests with two skips; frozen evidence also shows 24 root render/update tests passing, while this review host lacks importable Copier; `reviewer-driver.log:1767`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`, `reviewer-root.log:6`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive audit is deferred to the required publish rerun, not discharged here; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm no equivalent or rejected upstream work exists across all four affected paths — the supplied prior-art account names only merge.py, and this snapshot has one synthetic commit and no remotes or closed-PR evidence to independently settle that decision; `brief.md:113`, `reviewer-prior-art.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the 15s confirmation heuristic and its small-budget refusal behavior as sufficient for this increment — jobs registering later, or different green check sets, can still pass, so this does not fully close the underlying missing-check risk; `target/template/src/pdca_harness/merge.py:162`, `target/template/pdca.toml.jinja:153`, `brief.md:67`. |

Independent verification used the disposable target supplied by the harness. I stashed only the three production/comment files, kept the patched test module, ran `PYTHONPATH=src python3 -m unittest discover -s tests -p test_merge.py`, restored the stash, and reran the identical command. Red exited 1; green exited 0. Both the 1s immediate-green refusal and the 20s pending→green refusal fail without the fix and pass with it. The sequence sweep includes empty confirmation, flickering green, and exact interval boundaries. The restored target diff matches `patch.diff` byte-for-byte. All source citations above refer to the supplied target; no stale-target caveat applies.

Additional independent checks were `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`, docs lint and `render_site.py --check`, `git diff --check`, and the production-path scanner. Temporary outputs stayed inside this review sandbox. The scanner's successful result is not substantive proof here: the patch edits an existing test file, so its added-file heuristic has nothing to inspect (`gate-logs/C5-prod-path.log:10`). Production coverage is instead established by the direct `merge_wave` call and the independent red→green result.

The root-suite rerun exited 77 because this interpreter cannot import Copier (`reviewer-root.log:6`). This is a review-host limitation, not a patch defect or an unmet dependency in the frozen verification: `gate-logs/T3-suite.log:38` through its root-suite result at line 56 show actual render and update-compatibility cases passing. The instance-scoped gate wrappers were adjudicated from their supplied logs; the docs commands were also rerun directly. The host-CI-parity log shows local lint/render/link-audit success, not an assertion that a live GitHub workflow ran (`gate-logs/host-ci-docs.log:10`). The available integration template has only a TODO for project-defined human-only items (`target/template/docs/INTEGRATION.md.jinja:80`), so it supplies no further enumerated decisions.

No patch defects found within the agreed scope. The two NEEDS-HUMAN decisions above remain advisory sign-off items; this review does not authorize ready-marking or merging.

### Advisory — code-review

# Advisory code review — issue 582 / merge-wait-confirms-green

No correctness bugs found in this diff. The new `_wait_for_green` loop
(`template/src/pdca_harness/merge.py:171-193`) does what the brief asks:

- It always ends. Each pass through the outer `while True` either returns or sleeps a
  full `poll_interval` and adds it to `waited`, and a confirm is only taken when
  `wait_secs - waited >= poll_interval` (`merge.py:185-187`). So the sum of sleeps never
  goes over `wait_secs`.
- The confirm is never shortened. This was the iteration-1 rejection, and it is fixed:
  `_sleep(poll_interval)` at `merge.py:189` replaces the old `min(...)` step.
- A `pending`/`empty` confirm goes back into the inner wait. A `failing`/`unreadable`
  confirm comes back out through `if verdict != "green": return` (`merge.py:180-181`) with
  no extra read.
- `wait_secs <= 0` still does one read and returns it as-is (`merge.py:172-173`).
- `_merge_one` is unchanged. The new `pending` detail shows up in the existing "has not
  finished within Ns — …" refusal (`merge.py:268-269`), and the ready-undo still runs
  (`merge.py:282`).

The gate log `gate-logs/C4-verify.log` shows the new tests red without the fix and green
with it. The class-wide `_sleep` patch in `setUp` (`template/tests/test_merge.py:84-86`)
keeps the four green-path tests from sleeping for real. The suite ran in 0.079 s.

Findings (all minor):

- NEEDS-HUMAN — `template/src/pdca_harness/config.py:743-746`: any `merge_wait_secs` from
  1 to 14 now quietly refuses every PR under `merge_requires = "all"`. The patch only
  documents this in comments (`config.py:383`, `template/pdca.toml.jinja:153-155`).
  `Config.load` already warns about and corrects bad values (negative, non-integer), so
  a one-line warning for `0 < merge_wait_secs < 15` would match how it handles those.
  Whether to add it is a scope call: the brief lists only the comment edits for
  `config.py`, and the 15 s poll interval is a default argument in `merge.py:148`, not
  something `config.py` knows about.
- `template/src/pdca_harness/merge.py:176`: when the budget is not a multiple of 15
  (say 20 or 299), the inner wait still takes a short last step (`min(poll_interval,
  wait_secs - waited)`). A `green` read after that short step is then always refused as
  unconfirmed, because less than 15 s is left. This is fail-closed, so it is safe. The
  short step only changes which refusal message you get: it can catch a late `failing`
  instead of reporting `pending`. No change needed; mentioning it so nobody reads that
  short step as a path that can lead to a merge.
- `template/tests/test_merge.py:530-531` and `:584-585` assert the full refusal detail
  word for word ("green first seen with 0s of wait budget left, too little to confirm it
  15s later (2 checks)"). That is stricter than the brief, which only asks for
  `unconfirmed`/`confirm` in stderr, so any later rewording will break both tests.
  `test_green_with_no_budget_left_to_confirm_is_not_believed` already checks for
  `"confirm"` on its own (`:528`). This is a style choice, not a defect.

No reuse or efficiency problems: the change sits entirely inside the one function that
owned the wait, and there is no existing helper it should have used. The new
`_drive_reads` test helper (`test_merge.py:439-472`, with `_checks` at `:475`) is close to the inline fake in
`test_pending_then_green_merges` (`:296-310`). The brief only asks for that test's read
count to change, so leaving the old fake alone is the right call.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm no equivalent or rejected upstream work exists across all four affected paths — the supplied prior-art account names only merge.py, and this snapshot has one synthetic commit and no remotes or closed-PR evidence to independently settle that decision; `brief.md:113`, `reviewer-prior-art.log:1`.
- [x] Validation — fitness-to-purpose — Accept the 15s confirmation heuristic and its small-budget refusal behavior as sufficient for this increment — jobs registering later, or different green check sets, can still pass, so this does not fully close the underlying missing-check risk; `target/template/src/pdca_harness/merge.py:162`, `target/template/pdca.toml.jinja:153`, `brief.md:67`.
- [x] `template/src/pdca_harness/config.py:743-746`: any `merge_wait_secs` from 1 to 14 now quietly refuses every PR under `merge_requires = "all"`. The patch only documents this in comments (`config.py:383`, `template/pdca.toml.jinja:153-155`). `Config.load` already warns about and corrects bad values (negative, non-integer), so a one-line warning for `0 < merge_wait_secs < 15` would match how it handles those. Whether to add it is a scope call: the brief lists only the comment edits for `config.py`, and the 15 s poll interval is a default argument in `merge.py:148`, not something `config.py` knows about.
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
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- Publish could not check line numbers on the patched code. Its attempt to apply
  `patch.diff` in a scratch worktree (`git -C ../pdca-harness worktree add --detach
  <scratchpad>/wt origin/main` + `git apply`) was denied by the permission check, with no
  reason given. The `path:line` citations in pr-description.md were instead worked out from
  the patch's hunk headers and matched against build-notes.md. That worked here, but it is
  manual and easy to get wrong on larger patches. Possible deltas: have the driver hand the
  publisher an already-patched, read-only worktree (or the patched files), or allow
  `git worktree add/remove` under the session scratch directory for the publisher leaf.
- (empty is the common case)
