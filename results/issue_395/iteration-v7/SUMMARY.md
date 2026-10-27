# Result — issue 395 / same-wave-conflict-refused-at-accept

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In a `pdca flow` run in stack mode, a bundle is not accepted if its branch would textually conflict with a bundle of its own wave that is already accepted. This covers the waves the fold runs after: `k < len(wave_list) - 1`, `do_publish`, publisher not `stub` — the same condition as `flow.py:3078` plus the fold's non-dry `held_out` (flow.py:3115). "Would conflict" means the fold's own #674 rule, in the fold's order. When an accept (from a session, or a decision already recorded in the bundle) would add such a bundle, the driver refuses it the way C6 refuses an accept today. The bundle gets an open §6 NEEDS-HUMAN row naming the partner(s), the conflicting file(s) and the step (declare `Conflicts with: <partner>` in its brief, then `iterate-plan`). It stays AWAITING_SIGNOFF. Its siblings are accepted and published as before. So, in those waves, a run no longer accepts two same-wave bundles whose branches conflict, and it never opens two such PRs. A bundle the trial refuses is never COMPLETE without a PR. The last wave, a one-wave run, single-issue `flow`, `--no-publish`, merge mode, a dry run and the standalone `pdca signoff --accept` do not change. This is a partial fix of #395: the PR says `refs #395`, not `closes`.
- Success criterion: These run on the real-git `StackFoldGit` fixture with `gh` stubbed and the publisher in `command` mode. Every accept goes through the real `flow._drive_wave` → `flow._apply_decision` path: Do+Check are stubbed, the decision is written to the bundle (`leaves.SIGNOFF_DECISION`), and nothing calls `signoff.record(... "accept")` directly. A later wave exists in every case except (g), so the fold condition holds.
  - (a) A and B are in wave 0, with no `Conflicts with` between them. Their patches change the same lines of a shared file, and both carry `accept`. After the run: A is COMPLETE, its branch is pushed and `gh pr create` is called for it. B is AWAITING_SIGNOFF (`state.state`). B's SUMMARY §6 has an open row naming `issue_A` (or A's id) and the shared file. `signoff.open_needs_human` returns that row. B's branch is not on origin and no `gh pr create` names B. The run's `holds` has no entry for B. `cli._results_rc` is 1 (B did not finish). A wave-1 bundle that depends on neither still builds and completes.
  - (b) A and B change different lines of the same file (no textual conflict). Both are COMPLETE and both are published. Neither §6 gains a row.
  - (c) The refusal does not depend on which accept is applied first. With B's decision applied before A's (for example, B carries a recorded decision, which the pre-apply at flow.py:2516-2522 applies first, and A's is written by the stubbed session), A is the one refused, and the accepted one publishes. Either way, exactly one of the pair is COMPLETE and the fold holds nothing (`holds` empty).
  - (d) Override, in the SAME run (not a re-run — on a re-run A is finished and skipped, so B is no longer A's same-wave sibling and the #674 same-wave hold does not apply). Leg (a)'s setup, but the stubbed sign-off session offered to B after its refusal ticks B's new row and writes `accept` again. B is then accepted and published in that run. The fold, still running over wave 0 with A and B both accepted, holds B as `"conflict"` exactly as on `main` (#674): `holds` has B with reason `"conflict"`. The row is not added a second time (`signoff.ensure_needs_human_item` leaves a ticked row alone, `signoff.py:177-207`).
  - (e) The trial cannot run for the target: inject a failure of its git step (a fetch or a commit build). B, which shares a file path with the already-accepted A, is refused with a §6 row saying the check could not run and naming A and the file. C, accepted in the same wave with no file shared with an accepted sibling, is accepted and published.
  - (f) The row lives only in SUMMARY §6. It is NOT added to `assemble.collect_needs_human` (`assemble.py:389`) or to any Check artifact, so it has no IMPL/HUMAN kind and auto-iterate never sees it (do not add a new artifact source). A reassembly of B's SUMMARY (an iterate-do or auto-iterate rebuild) drops the row and any tick on it; that is intended, because the next accept runs the trial again. Test it: after B is refused as in (a), reassemble B's SUMMARY with the driver's own assembly step, write `accept` again, and drive another pass. B is refused again and the row is back, unticked. (Red on `main`: B is accepted.)
  - (h) A trial refusal does not spin the wave until the pass budget runs out. With `max_passes = 20` and the session stub for B writing nothing after the refusal, B is offered at most ONE sign-off session after the pass that refused it (`leaves.run_signoff_batch` calls naming B ≤ 2 in total). The wave then ends with B still AWAITING_SIGNOFF. The stderr line about B names the conflict, the partner and the step (`Conflicts with: <partner>` then `iterate-plan`). It does NOT say "raise [driver].max_passes". A plain C6 refusal (an open §6 row from Check, no trial involved) keeps today's behaviour; this leg does not change it.
  - (g) Last wave: the same conflicting A/B as the only wave of a run. Both are accepted and both are published, with the same exit code as on `main`.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: In a flow run's stack-mode non-final waves (the condition in Goal), an accept that would add a same-wave textual conflict, judged as the fold judges one, is refused. The bundle stays AWAITING_SIGNOFF with an open HUMAN §6 row. That covers every accept route inside `_drive_wave`. A trial-refused bundle is offered one more sign-off session, then the wave stops re-offering it and its wave-end message names the conflict step instead of the pass-budget hint (leg h). When the check cannot run for a target, refuse only a candidate whose patch shares a file path with an already-accepted sibling of the wave on that target. Every other candidate is accepted. The fold keeps its own #674 hold as the last line of defence (overrides, branches that move after the accept). Update `docs/07-crosscutting.md`: the same-wave paragraph (:719-731) gets the new behaviour, the override, and the fact that a line-plus-sibling conflict (#747 `_held_by_line`) is still caught only at the fold, after publish. The exit-code paragraph (:734-745) says a refused bundle is unfinished (exit 1). / out of scope: the last wave and one-wave runs (follow-up); re-sequencing a refused bundle into a later wave of the same run, and writing `Conflicts with` into its brief automatically (follow-up; the issue's layer-2 re-sequence half); a conflict that also involves work already on the line (#747) — the fold still catches it after publish (follow-up); the issue's layer 1, a Plan-exit advisory over briefs' predicted files (follow-up; briefs have no structured file list); the standalone `pdca signoff --accept` (no wave context); merge mode; documenting the assumption that every target repo has a PR setup and that accepted ⇒ PR, with its two existing exceptions (T4-failed texts, failed push) (follow-up, human-requested); the advisory `_audit_wave_overlap` warning (flow.py:1586), which stays as it is.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
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

Review accept-time refusal of same-wave textual conflicts before publication in non-final stack-mode flow waves (#395).

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The partial-fix boundary, acceptance order, override and recovery outcomes are explicit and falsifiable; the trial is enabled at the specified fold boundary (brief.md:19; template/src/pdca_harness/flow.py:3289). |
| C2 Reproduction (red pre-fix) | PASS | Independent tracked-change stash retained the new regression file: all 13 cases collected and 10 failed on assertions, including the forbidden COMPLETE/published conflicting sibling (review-red.log:212; template/tests/test_flow_same_wave_accept_trial.py:239). |
| C3 Change | PASS | Refusal precedes recording acceptance, so the conflicting bundle retains the existing sign-off state rather than creating accepted-but-unpublished work; both driver acceptance routes receive the trial (template/src/pdca_harness/flow.py:206; template/src/pdca_harness/flow.py:2768; template/src/pdca_harness/flow.py:2786). |
| C4 Verification (red→green) | PASS | After restoring the tracked patch, the identical independent command passed all 13 cases; red was 10 assertion failures, consistent with frozen C4 evidence (review-green.log:3; review-red.log:212; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | The real accept path and real git merges demonstrate prevention before publication, using the fold's own attribution rule and the publisher's base selection; no capability probe masks a load-time cause (template/src/pdca_harness/integrate.py:828; template/src/pdca_harness/integrate.py:947; template/src/pdca_harness/publish.py:796; gate-logs/C5-prod-path.log:10). |
| T1 Structure | PASS | Wave context stays explicit, git trial ownership stays in integration, and branch-base selection is shared with publication; trial failures restore the shared tree and refusal state follows the bundle lifecycle (template/src/pdca_harness/flow.py:136; template/src/pdca_harness/integrate.py:807; template/src/pdca_harness/integrate.py:832; template/src/pdca_harness/state.py:157). |
| T2 Shape | PASS | Independent docs lint, 22-page render and internal-link audit passed, as did git diff --check; frozen host-parity output confirms the same documentation checks (review-docs.log:2; review-docs.log:7; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver suite passed 2,643 tests with two skips; frozen evidence also shows 24 root render/update tests passing. Local root rerun could not exercise Copier and is a reviewer-host limitation, not a patch failure (review-suite.log:1819; gate-logs/T3-suite.log:54; review-root-suite.log:6). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish, so the deferred row is neither verified green nor a finding (gate-logs/T4-contribution.log:10). |
| T5 Judgment | PASS | Affected-path merged history and the seven named closed, unmerged PRs were independently checked; their existing scheduling/fold work does not replace accept-time refusal. Bounded sessions, override and unchanged plain C6 behavior are exercised (review-prior-art.txt:2; review-prior-art.txt:8; template/tests/test_flow_same_wave_accept_trial.py:418; template/tests/test_flow_same_wave_accept_trial.py:503). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this partial #395 fix and its tick-to-override recovery are suitable for operators — final/one-wave and line-plus-sibling conflicts can still produce conflicting PRs, while override deliberately restores publish-then-hold behavior (docs/07-crosscutting.md:750; docs/07-crosscutting.md:754). |

No implementation defect found. Production citations above are relative to `$PDCA_TARGET`; review evidence and supplied gate-log citations are relative to this sandbox. The target was readable and matched the supplied patch; the independent stash was popped successfully and no reviewer changes were made to target source.

Independent regression command, used both with tracked production changes stashed and after restoration: `cd target/template && PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_flow_same_wave_accept_trial`. Temporary test data was confined to `review-tmp/` in this sandbox. The tests exercise real local git conflicts, origin branch refs and the real driver acceptance path; GitHub and publisher mechanics are stubbed as explicitly required by the brief, so no live GitHub publication is claimed.

The instance-scoped oracle wrappers are unavailable here. Their frozen logs were inspected: C4 records assertion failures before the fix and a passing green leg; C5 records a production-package import scan; both documentation logs record successful lint/render/link checks; the suite log records successful root and driver suites; T4 records deferral until publish. Local root coverage is not claimed: the runner exited 77 because this interpreter cannot import `copier` (review-root-suite.log:6); the successful root verdict rests on the frozen gate execution (gate-logs/T3-suite.log:40).

Prior-art API evidence is preserved in `review-prior-art.json` and summarized by affected path in `review-prior-art.txt`. The local target intentionally has one synthetic base commit, so historical checks used the remote API pinned to the original base, rather than another checkout. Closed PRs #638, #639, #648, #649, #598, #599 and #600 were checked for state, description and changed paths. The new regression path has no prior history. This confirms the bounded prior-art check; it does not assert an exhaustive proof that no similar unpublished work exists.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review — issue 395 / same-wave-conflict-refused-at-accept

Verdict: **partly refuted.** The red→green proof holds, and the conflict rule matches the
fold's. But the refusal's own recovery step leads to a bundle being accepted and published
with no human sign-off. I reproduced that on the real fixture.

## Refutation that landed

- NEEDS-HUMAN [impl] — **Following the refusal row's own step leaves a stale `accept` that
  auto-accepts the rebuilt attempt on the next run, with no sign-off session.** A trial
  refusal returns `"blocked"` and keeps the `accept` in `signoff-decision`
  (`template/src/pdca_harness/flow.py:205-207`). The row and the wave-end line tell the human
  to run ``pdca signoff <id> --iterate-plan`` (`flow.py:379`). That CLI path records the
  decision but never deletes `signoff-decision` (`template/src/pdca_harness/cli.py:1504-1543`;
  only `flow._apply_decision` deletes it, `flow.py:235`). The iterate archive doesn't move the
  file either: `signoff-decision` is not in `DOWNSTREAM_OF_BRIEF`
  (`template/src/pdca_harness/state.py:125-159`, read by `driver._archive_iteration`,
  `driver.py:457`). On the next run the re-planned, rebuilt bundle reaches AWAITING_SIGNOFF.
  Auto-iterate then declines because a decision is on disk (`flow.py:561-565`), and the
  pre-apply applies the old `accept` to an attempt nobody has reviewed (`flow.py:507-510`).
  **Concrete case, run on `StackFoldGit`** (probe kept in my sandbox,
  `exp/probe_stale_accept.py`): run (h)'s setup, so 11 is refused and parked. Then
  `cli._signoff(iterate_plan=True)` for 11 (rc 0, state UNPLANNED; `signoff-decision` still
  reads `accept`). Re-plan 11 with `Conflicts with: 10`, then re-run `drive=["11"]`. Result:
  stderr says `issue_11 — applied the 'accept' sign-off decision already recorded in the
  bundle; no new session`, the session count for 11 is 0, and 11 is COMPLETE with
  `fix/11` pushed. `--iterate-do` goes the same way. The CLI gap already exists for C6
  refusals on `main`. This diff is what sends the same-wave case into it: it creates the
  refused accept, and its printed step names the CLI command. After parking, the CLI command
  is the only route the run leaves open. Possible fixes: have `cli._signoff` delete
  `signoff-decision` once it records a decision (as `flow.py:235` does), or have the row's
  step point to the in-session iterate-plan. Add a test leg for this.

## Attempted to refute, could not

- **Red→green evidence.** I re-ran green on the target (13/13 OK). I also re-ran red myself:
  `flow/integrate/publish/state.py` taken from `HEAD` (the pre-fix base) into a sandbox copy,
  test kept. Result: 10 FAIL, 0 ERROR, the same set as `gate-logs/C4-verify.log`. The 3 that
  pass on both sides are the "unchanged behaviour" legs: (b) clean merge, plain C6, (g) last
  wave. Each red failure is on the real symptom (`COMPLETE != AWAITING_SIGNOFF`, no trial
  `apply` ever called), not on an import. Accepts go through the real
  `_drive_wave` → `_apply_decision` path; the only stub is `leaves.run_signoff_batch`, and
  there is no `signoff.record(...accept)`.
- **Does the trial mirror the fold?** Merge order is the fold's: name-sorted within the wave
  (`integrate.py:755`; fold `accepted` order at `flow.py:3303`). The start point matches:
  `tip or <base_remote>/<base>` (`integrate.py:806`) versus fold `fresh`/`continue`
  (`integrate.py:563-611`). Each would-be commit is built with publish's own steps on
  publish's own cut point, for both new-PR and `Onto branch` bundles (`publish.py:262`,
  `:296-309`, `:490-498`). The `_held_by` rule is reused, not copied (`integrate.py:926`).
  The `publish._checkout_base` refactor gives the same result as the old inline rule.
- **Waves after the first.** Every shipped leg runs the check in wave 0 only
  (`tests/test_flow_same_wave_accept_trial.py:172`). That leaves the `folded_tips` start and
  the #727 own-base cut points untested. I probed a wave-1 pair (both depending on wave-0
  bundle 12, plus a wave 2): 21 was refused naming 20 and `shared.txt`, 20 and 30 published,
  `holds` empty. A clean wave-1 pair was all published. It works; a wave-1 leg in the suite
  would pin it.
- **Fallback, broken tree, the one-more-session limit, a failed session, re-runs.** The
  ordering of the `except` clauses (`flow.py:303-319`), the counting after the session
  (`flow.py:2778-2783`), and the reset at wave start (`flow.py:2713-2714`) all hold for the
  cases I traced. The lock is never held while the fold's locks are, so there is no
  deadlock.
- **Not filed, because the human already ruled on it:** the hold-count rule can be fooled
  after an override. Example: 10 and 11 are accepted via an override, so the fold holds 11.
  A new 09 that conflicts only with 10 is then accepted, and the fold holds 10 instead.
  That is the "override loophole" accepted in the carry-forward (`brief.md:111`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_395 / same-wave-conflict-refused-at-accept

Lens: correctness bugs the patch introduces, and reuse / simplification / efficiency. Advisory only.

**Result: I found no correctness bugs in this diff, and nothing that needs a human decision.** Two low-severity notes are below. Neither one blocks.

What I checked and found sound:

- The three iteration-6 carry-forward fixes are in place.
  1. A session is counted only once `run_signoff_batch` returns. The count is in the `else:` branch at `template/src/pdca_harness/flow.py:2783`.
  2. At wave start the count is reset, not deleted (`flow.py:419`, `_sessions_reset`).
  3. `IntegrationTreeError` / `_LineBroken` are caught before the generic `IntegrationError` fallback and refused as `"tree"` (`flow.py:306-308`). The errors are chained with `raise … from first` in `_back_on` (`integrate.py:953`).
- Each fix has its own test leg. The C4 log shows 10 of 13 tests red before the fix. The 3 that pass before the fix are legs (b), (g) and the plain-C6 leg, which are meant to pass on `main` too. T3 is green (2643 tests OK).
- The `publish._checkout_base` refactor (`publish.py:767`) gives the same result as the old inline `wave_stacked and bool(wave_tip)`. `wave_stacked` is `wave_mode != "merge" and bool(wave_base)`, as at `publish.py:251`. So the trial and publish now share one rule, and there is no second copy to drift.
- The trial condition at `flow.py:3289-3292` matches the fold's condition: not the last wave, publishing on, stack mode, and not a dry run (stub publisher, the same `dry` test as `flow.py:3351`).
- The order of guards in `_apply_decision` is correct: `unrecordable` → C6 → trial → record. C6 runs first, so when `_refuse` (`flow.py:329`) calls `open_needs_human`, the only open row it can see is the one just added. A ticked row then correctly means "override".
- The tree is put back on every exit path. `_merge` resets after a conflict, `_would_be` and the trial both call `_back_on` in `except BaseException` and again on success, and a non-`Exception` such as Ctrl-C is never replaced. The fold's own clash rule (`_held_by`) is reused, not reimplemented.

Notes (low severity, no tag needed):

- `integrate.py:812` — every accept that has an already-accepted sibling on the same target runs `_prepare_worktree`, which does a network fetch of origin with `--prune`, then the base remote. It then rebuilds the would-be commit of every accepted sibling, and runs the `alone` set of merges again (`integrate.py:829-831`). In a wave of N bundles that is up to N−1 fetches and O(N²) commit builds during sign-off. This is fine for today's wave sizes. If waves grow, the cheap fix is to cache each sibling's would-be commit and the `alone` result per wave, keyed on the sibling's `patch.diff` and the cut ref. Not worth doing in this slice.
- `flow.py:297-298` — any COMPLETE sibling counts as "accepted", including one whose publish later fails (T4 texts or push). In that case B is refused because of A, then A is held `"unpushed"`, and neither one gets a PR this run. This matches the brief: it says "already accepted", and the brief lists these two failure modes as known exceptions. B's row still gives the right next step (declare `Conflicts with`, then iterate-plan). I'm recording this so the reviewer knows about it, not as a defect.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether this partial #395 fix and its tick-to-override recovery are suitable for operators — final/one-wave and line-plus-sibling conflicts can still produce conflicting PRs, while override deliberately restores publish-then-hold behavior (docs/07-crosscutting.md:750; docs/07-crosscutting.md:754).
- [ ] **Following the refusal row's own step leaves a stale `accept` that auto-accepts the rebuilt attempt on the next run, with no sign-off session.** A trial refusal returns `"blocked"` and keeps the `accept` in `signoff-decision` (`template/src/pdca_harness/flow.py:205-207`). The row and the wave-end line tell the human to run ``pdca signoff <id> --iterate-plan`` (`flow.py:379`). That CLI path records the decision but never deletes `signoff-decision` (`template/src/pdca_harness/cli.py:1504-1543`; only `flow._apply_decision` deletes it, `flow.py:235`). The iterate archive doesn't move the file either: `signoff-decision` is not in `DOWNSTREAM_OF_BRIEF` (`template/src/pdca_harness/state.py:125-159`, read by `driver._archive_iteration`, `driver.py:457`). On the next run the re-planned, rebuilt bundle reaches AWAITING_SIGNOFF. Auto-iterate then declines because a decision is on disk (`flow.py:561-565`), and the pre-apply applies the old `accept` to an attempt nobody has reviewed (`flow.py:507-510`). **Concrete case, run on `StackFoldGit`** (probe kept in my sandbox, `exp/probe_stale_accept.py`): run (h)'s setup, so 11 is refused and parked. Then `cli._signoff(iterate_plan=True)` for 11 (rc 0, state UNPLANNED; `signoff-decision` still reads `accept`). Re-plan 11 with `Conflicts with: 10`, then re-run `drive=["11"]`. Result: stderr says `issue_11 — applied the 'accept' sign-off decision already recorded in the bundle; no new session`, the session count for 11 is 0, and 11 is COMPLETE with `fix/11` pushed. `--iterate-do` goes the same way. The CLI gap already exists for C6 refusals on `main`. This diff is what sends the same-wave case into it: it creates the refused accept, and its printed step names the CLI command. After parking, the CLI command is the only route the run leaves open. Possible fixes: have `cli._signoff` delete `signoff-decision` once it records a decision (as `flow.py:235` does), or have the row's step point to the in-session iterate-plan. Add a test leg for this.
- [x] **Leg (f) is vacuous, or it hides a second change.** The brief says: "The new row is a HUMAN-kind item (`assemble.HUMAN`). On its own it does not make `autoiterate.eligible` true." But the row is written with `signoff.ensure_needs_human_item`, which only splices a plain `- [ ] {item}` line into SUMMARY.md (`signoff.py:213`). It has no kind. Auto-iterate never reads SUMMARY §6. `_maybe_auto_iterate` classifies `assemble.collect_needs_human(d, cfg)` (`flow.py:340`), which rebuilds items from `check-gates.json`, `check-review.md` and `check-advisory-*.md` (`assemble.py:389-413`). So the row can never be "HUMAN-kind", and it cannot affect `eligible` at all. As written, (f) is green before and after the change: it cannot be falsified. A Do that tries to make it meaningful would have to add a new artifact source to `collect_needs_human`, which is a hidden second change. A related gap: if B also has an IMPL finding, an auto-iterate or iterate-do rebuild reassembles §6 from artifacts and drops the refusal row (and any tick on it). The brief does not say whether that is intended. Revise (f) to assert something observable, or drop it.
- [x] **Leg (d) "a re-run" does not reach the #674 same-wave hold it asserts.** Leg (a) leaves A COMPLETE. On a re-run, finished ids are skipped (`07-crosscutting.md:747-749`), so A is no longer a same-wave sibling of B. B is then judged against the line, not the wave. The docs say that case is either #747's line rule or "still stops the run" (`07-crosscutting.md:730`). The carry only starts from a plain `Depends on` (:716), so A may not be on the line at all. If no later wave follows, no fold runs. Then "The fold then holds B as `"conflict"` exactly as on `main` (#674)" is not what happens. Pin the override to the same run: the next pass's session ticks the row and re-accepts (`_drive_wave` re-offers C6-refused bundles, `flow.py:2521`). Or state the exact re-run topology and the expected fold outcome.
- [x] **The brief contradicts itself about Do's inputs.** Line 3 says "Do reads ONLY this file". Line 41 then tells Do to reuse mechanics from `/home/eddie/pdca/pdca-pdca/results/issue_395/iteration-v5/patch.diff`, an absolute path outside the target and the bundle, and to fix "two open findings on it". Line 36 tells Do to ignore a stray `test_flow_same_wave_prepublish.py` "in this bundle directory". Either Do may read the v5 patch, and the "ONLY" line is wrong, or it may not, and the two v5 findings (the discarded retry result, and the build loop outside `try/finally`) are guidance Do cannot act on. The stray rejected-design test should also be removed or named as excluded from the C4 gate. Otherwise a red/green run may pick it up. I could not check this: the bundle directory is not among my inputs.
- [x] **The cost of a refused bundle is understated: the wave drives B until its whole pass allowance is spent.** C6 refusal returns `"blocked"` before the decision file is unlinked (`flow.py:177-179` vs :205). So each later pass re-applies the stale accept, is refused again, and queues B for another sign-off session (`flow.py:2516-2532`). B is never terminal, so `_drive_wave` only exits on budget (`flow.py:2533-2543`; default `max_passes = 20`, `config.py:309`). Then it prints "raise [driver].max_passes", which is wrong advice for a conflict refusal. The brief's Design calls this "existing C6 behaviour … not changed here". But this change makes the state reachable without any human-visible finding: an undeclared conflict, two accepts. The criterion should pin how many sessions B is offered and what B's wave-end message says (it should name the conflict step, not the pass budget). Otherwise the human sees up to 20 re-prompts and a misleading hint, and no leg would catch it.
- [x] **Criterion (e) holds strictly more work than `main` when the partner's publish fails for a reason the trial cannot see.** The trial runs after T4 but before checks that live inside publish: the host-CI gate (publish.py:379-383), the line-tip refusal (publish.py:364-367), and commit hooks (publish.py:309; the trial commits with `--no-verify`, integrate.py:846). Example: A's host CI is red. A pushes nothing, B is held for A with no PR, and B's dependents and `Conflicts with` partners are held too. On `main`, B would have been published and folded cleanly, because the unpushed A is left out of the fold (flow.py:3169), and its dependents would have been built. The brief asks for this behaviour on purpose (criterion e: "A is still accepted work and will be re-published"), so it is a scope call for sign-off, not a bug.
- [x] **The brief does not say whether the change covers the final wave, and the success criterion never tests it.** The fold that "the #674 rule, same order" copies only runs when `k < len(wave_list) - 1 and do_publish` (`flow.py:3078`). So on the last wave, including a single-wave run, nothing holds a same-wave conflict today: both PRs publish. The Goal says "before a wave's accepted bundles are published", which reads as every wave. If that is the intent, the change adds a new hold (and a new exit-3 case per `docs/07-crosscutting.md:734-741`) on a path with no fold to mirror, and possibly no integration line to trial onto. If it is not the intent, the motivation ("a wave no longer ends with two open PRs that conflict") stays false for the last wave. Criterion (a) always includes "a bundle of a later wave", so it cannot tell the two readings apart. The brief should pick one and add a criterion leg for a one-wave run or the last wave.
- [x] **The trial set is undefined when a partner then fails to publish.** Design §1 runs the trial "after … drafted and T4-gated", over "the wave's accepted work". It does not say whether bundles with `ready[d.name]` False (`flow.py:3054-3058`) are in the trial. If they are, B can be held for clashing with an A that is never pushed (A becomes `held_unpushed` at `flow.py:3094-3100`). Then neither PR exists, and B is held for a partner that is not on the line. A push failure after the trial (`_publish_bundle` returns False, `flow.py:642-665`) has the same problem. The brief should limit the trial to `ready` bundles and say what happens to a conflict-held B when its partner A fails to push. Release B to publish, or keep the hold? Add a criterion leg for it.
- [x] **The main design decision is left to Do.** Design §2 says: "How to build it is Do's call; it must match what publish will push, or the trial and the fold can disagree." Whether the trial gives the same answer as the fold is the whole feature, and `_held_by` judges merges of commits onto `pre` (`integrate.py:1803-1808`). So "match" needs a precise meaning: same parent commit (the line commit the bundle was built on, or its own base under `#738`'s `own_bases`, `flow.py:2994-3016`) and the same tree as the branch publish cuts (`docs/07-crosscutting.md:712-713`: "its PR branch is cut from the line commit it was built on"). The brief should set that rule. As written, criterion (b) (no false hold) is only as strong as an implementation choice nobody has made. Also say which worktree is used: the fold's shared integration tree (`integrate.py:609-613`) is reset by every user and guarded by the `#297` lock scope (`flow.py:3101`). A pre-publish trial there needs the same lock, and the brief does not mention it.
- [x] **Criterion (c), "handled as today (this change does not move that case)", is not something a test can assert.** Today a branch that conflicts with the line is either held by `#747` (`_held_by_line`, `integrate.py:663-668`) or stops the run (`integrate.py:671-673`). The criterion should name the observable result: the bundle is pushed, `gh pr create` is called for it, and its hold kind or stop is the same as on `main`. Otherwise Check cannot prove the leg false.
- [x] **The issue asked for re-sequencing, and the brief defers it without saying so.** The thread's layer 2 says: "On failure, re-sequence: move the bundle to a later wave / record the discovered conflict in the brief, rather than publishing it as a sibling". The owner's comment puts the payoff as later bundles getting built. The brief scopes out both re-sequencing and writing the discovered `Conflicts with` into the brief. That is a reasonable cut, but it means this change does not close #395. Mark the brief as a partial fix (e.g. "refs #395", with a follow-up issue for re-sequence and the Plan-exit advisory) so publish does not auto-close the issue.
- [x] **The `Conflicts with: 464` declaration cannot be checked from this bundle.** There is no `dependency-state.json` and no `sources/` directory in the inputs, so I cannot confirm that a 464 bundle exists in this batch or what state it is in. The ordering note (464 "gates this same publish/fold block") is a real file overlap, so if 464 is in the same batch, the declaration is right. Confirm the id resolves before sign-off.
- [x] T5 Judgment — Approve withholding otherwise independent siblings when a target's trial remains unavailable — publishing only the first bundle protects against unknown conflicts but delays accepted work beyond the brief's normal sibling-publication behavior; docs/07-crosscutting.md:731 and template/src/pdca_harness/integrate.py:827.
- [x] **"the wave never opens two PRs that conflict with each other" is false for a bundle that conflicts with a sibling AND with the line.** `docs/07-crosscutting.md:728` and the comment at `template/src/pdca_harness/flow.py:3134` both claim it. The trial only asks `_held_by` (`template/src/pdca_harness/integrate.py:864-867`). The fold also asks `_held_by_line`, and passes it the same-wave bundles it already merged (`integrate.py:663-668`). Probe (`scratch/probes/probe_mixed.py`): wave 0 is 10 (line 2 of `shared.txt`) and 12; wave 1 is 20 (line 8, depends on 12) and 21 (lines 2 and 8, depends on 12); 30 depends on 20, so a fold follows wave 1. Result: `fix/20` and `fix/21` are both pushed and both get `gh pr create`. Then the fold holds 21, saying it "conflicts with issue_20's, merged before it in the same wave 1, and issue_10's". `main` does the same, so nothing regressed. But the patch leaves exactly the two-conflicting-PRs case the docs say can't happen. The brief limits the trial to the #674 rule, so this is a scope call: either widen the trial to the fold's `_held_by_line` when its partners include a same-wave bundle, or narrow the docs and comment to the #674 case.
- [x] **When the trial can't run, it also holds siblings that can't conflict, plus everything that depends on them.** `template/src/pdca_harness/integrate.py:827` marks every member after the first as "untried", whatever files it touches. Probe (`scratch/probes/probe_395.py`): the test's own `_pair` fixture (10 and 11 change the same line, 12 has a file of its own, 20 depends only on 12), with the trial's two fetches failing. Result: holds are `{11: unpushed, 12: unpushed}`, `fix/12` is never pushed, 20 is never built, exit code 1. On `main`, with the fold's fetch working, 12 publishes and folds, 20 builds, and the exit code is 3. So the brief's "Its siblings publish as before" fails on this path. There is a cheaper fallback that still never lets two conflicting PRs out: hold only the bundles whose patch shares a file with an earlier ready bundle. A textual conflict needs a shared path, and `waves.diff_files` already gives the file list (`flow.py:1614`). This failure policy came out of the round-1 iterate, so the human should pick it.
- [x] `template/src/pdca_harness/integrate.py:362-366` with `template/src/pdca_harness/flow.py:3152-3153`: when the trial can't run (lock not taken, or both tries fail at a git step), every ready bundle of that target except the first is held as `"unpushed"`. That happens whether or not they touch the same files. In a wave of N bundles on one repo, two fetch failures in a row leave N-1 accepted bundles unpublished, hold all their dependents, and make the run exit non-zero. This is a deliberate fail-closed choice made after round 1's finding, and it is documented (`docs/07-crosscutting.md:730-734`). Still, it is a large blast radius for a short-lived failure. The other option is fail-open (publish all, then let the fold's #674 check hold the loser), which round 1 rejected. Which trade-off to keep is a fitness call for the human.
- [x] **The fail-closed fallback holds back bundles that cannot conflict at all.** When the trial can't run for a target (two failed fetches, a lock it can't take, a git step outside one bundle's commit), `integrate.py:838-839` publishes only `members[0]` and holds every other ready bundle and its dependents. That happens even when their patches touch files no sibling touches, so a textual conflict is impossible. The behaviour is documented (`docs/07-crosscutting.md:736`) and tested. But it means one network blip during the trial now costs N-1 PRs and their later waves on any non-final wave with 2+ bundles. Before this change the same blip cost nothing at publish time, and the fold's own later fetch may well succeed. Whether to accept that, or to publish bundles with no shared path (the footprint `_audit_wave_overlap` already computes, `template/src/pdca_harness/flow.py:1629`) when the trial can't run, is a trade-off for a human.

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
- Iteration delta (if iterating): Keep the design; fix the stale-accept path (adversary finding, SUMMARY §6 item 2). A trial refusal leaves `accept` in signoff-decision, and the refusal row/wave-end line point to `pdca signoff <id> --iterate-plan`, which records the decision but never deletes signoff-decision (cli.py) — so the re-planned, rebuilt bundle is auto-accepted and published on the next run with no review. Fix: have cli._signoff delete signoff-decision once it records a decision (as flow._apply_decision does), and/or point the row's step at the in-session iterate-plan. Add a test leg: refuse B, `pdca signoff B --iterate-plan`, re-plan, re-run — B must reach AWAITING_SIGNOFF and get a fresh session, not be auto-accepted.
- By / date: Eduard Ralph / 2026-10-23

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
