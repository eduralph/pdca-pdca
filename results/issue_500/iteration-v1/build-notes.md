# Build notes — issue 500 / merge-mode-retarget-wrong-based-pr

Target: eduralph/pdca-harness @ main (worktree base `a6af7f3`). All line numbers are in the
patched worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`.

## What changed

1. **`template/src/pdca_harness/merge.py:463-511` — new `_target_base_refusal(cfg, d, pr_url)`.**
   Returns `""` when the merge may go on, or the reason it may not. Steps, in order:
   - no `brief.md` → refuse (`:474-477`). Without this guard `brief.field` raises
     `FileNotFoundError` and `merge_wave` crashes, which is fail-closed but ugly.
   - resolve the target with `publish._resolve_target(d)[:2]` (`:478`), the same parser
     `flow._runnable` uses (`flow.py:778-779`), as the brief asks. Empty repo or base → refuse
     (`:479-482`). Publish refuses the same case (`publish.py:182-189`), so a published PR
     always had one.
   - #411 route 2 first: `publish._batch_branch_producer(cfg, d, repo_spec, target)`
     (`:487-490`), called the way `publish._merge_base_refusal` calls it (`publish.py:800`).
     This runs before any `gh` call, so criterion (e) holds whatever base the host reports.
     The `fix` advice text is copied from `_merge_base_refusal` (`publish.py:792-796`).
   - read the host base via `_pr_head` (`:491`). Unreadable → refuse.
   - equal → `""` (criterion d: no `gh pr edit`).
   - different → `gh pr edit <pr> --base <target>` (`:496-503`); failure → refuse naming
     both branches. Then `_pr_head` again (`:504-509`); anything but the target → refuse
     naming both. Otherwise print "retargeted … from X to Y" (`:510`) and go on.
2. **`merge.py:563-572` — call site in `_merge_one`.** Placed after the
   `expected_checks_error` refusal (`:558-562`) and before `gh pr ready` (`:580-581`), outside the
   `if cfg.merge_requires != "required":` block, so it covers both settings (criterion c) and
   runs after the malformed-setting refusal (criterion f). It prints a plain STOP and returns 1,
   the way the `expected_checks_error` refusal does, not through `_refuse` (`:453`), which
   would send a spurious `gh pr ready --undo`. So in (b)/(e) there is no `gh pr ready` and no
   `--undo` at all.
3. **`template/src/pdca_harness/publish.py:288-294`** — the #411 comment no longer says the
   check happens only at publish; it points at `merge._target_base_refusal`.
4. **`docs/07-crosscutting.md:887-894`** (merge-mode bullet) describes the merge-time check and
   the retarget. **`:905-910`** replaces "the harness never retargets a PR for you" with what
   now happens, and states the driver only retargets a PR it is about to merge, never a brief.
5. **Existing tests changed** (the change makes them wrong, not flaky):
   - Every merge test fixture now writes a one-line `brief.md` with
     `org/repo @ main` (`test_merge.py` `_bundle`, `MergeAgainstCurrentBase._run`,
     `MergeConfirmRequiresCompleteRollup._merge`; `test_merge_third_remote.py` `_bundle`;
     `test_merge_onto_branch.py` `_bundle`). Without it the new check refuses every bundle
     (no target).
   - Tests that pin exact call order now expect one extra `gh pr view` before
     `gh pr ready` (`test_readies_before_merging`, `test_all_green_readies_then_checks_then_merges`,
     `test_partial_green_then_pending_merges_only_after_the_fourth_read`,
     `test_merge_requires_required_call_log_is_unchanged`,
     `test_update_that_lands_late_still_merges_pinned_to_the_updated_head`,
     `test_new_pr_and_modeless_records_still_merge`). The brief's Impact section names this
     extra read.
   - `test_ready_failure_stops_before_merge`'s stub returned empty stdout for every call, so
     the new `gh pr view` could not be parsed; it now answers `gh pr view` through the
     existing `_up_to_date` helper and still fails `gh pr ready` as before.

**Maintainer decision needed at sign-off (from the brief):** this reverses #411's "refuse at
publish, not at merge time" and the docs promise "the harness never retargets a PR for you".
If the maintainer does not want an unattended retarget, the fallback is refuse-only: delete
`merge.py:494-510` (the edit + re-read) and return the "PR targets X, not Y" refusal in their
place, about 15 lines; test (a) would then need to flip to expect a refusal.

## Choices and what I ruled out

- **Reusing `_base_read`'s `gh pr view` instead of a separate read.** Ruled out: `_base_read`
  runs after `gh pr ready` and only under `"all"` (`merge.py:597` onward). The brief requires
  the check before the ready-mark and under both settings, so a read before the ready-mark is
  needed anyway. Cost: one extra `gh pr view` per merged PR, as the brief's Impact predicts.
- **Falling back to `cfg.default_branch` when the brief names no target.** Ruled out: the
  invariant says merge only into the *resolved* target; publish already refuses an unresolved
  target, so guessing here would only widen what can merge.
- **Route-2 check repo:** I pass the brief's repo from `_resolve_target`, the same value
  publish passed (`publish.py:182`, `:296`), not the record's `repo` field, so both checks ask
  the same question.
- **Residual risk accepted per the brief's open question:** after a retarget, `pull_request`
  checks that ran against the old base are not re-run. No code for this, as the brief
  recommends.

## Test — `template/tests/test_merge_retarget.py` (copy also in the bundle)

Imports only `merge, merged, publish, state` and `config.Config/LeafConfig`, none of them a
symbol this patch adds, so the red leg imports and fails on assertions. A stateful `_Host`
stub stands in front of `subprocess.run`, as `test_merge.py` does; `gh pr edit` moves the
reported base unless told to fail or be ignored.

| Criterion | Test |
|---|---|
| (a) retarget succeeds → merged, edit before ready before merge, base re-read | `test_wrong_base_is_retargeted_then_merged` (both `merge_requires`) |
| (b) edit fails / re-read still wrong → rc 1, no ready/undo/merge, stderr names both | `test_retarget_that_fails_or_does_not_take_refuses` (2 × 2 subtests) |
| (c) both settings | each of a/b/d/e loops over `("all", "required")` |
| (d) right base → no edit | `test_right_base_makes_no_edit` |
| (e) sibling-produced target → no edit/ready/merge, stderr names `issue_499` | `test_batch_produced_target_is_refused_before_any_edit` (host base = target and ≠ target) |
| (f) malformed `expected_checks` + wrong base → no edit | `test_expected_checks_error_is_refused_before_the_retarget` |

### Runs (through the project's runners)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… PDCA_BRIEF_BASE=origin/main ./engine/scripts/run-verify.sh`
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Red leg: 10 subtest
  failures; e.g. under `"required"` the call log was
  `[gh pr ready, gh pr merge … --merge, git fetch]` — the wrong-based PR merged with no edit.
- T3: `./engine/scripts/run-suite.sh` → rc 0 (root suite and offline driver suite).
- T2: `./engine/scripts/run-docs-check.sh` → `docs lint clean, site render + link audit clean`.

### Refuting my own test

- **(a) Genuine red? Yes.** `run-verify.sh` reverts the production hunks (merge.py,
  publish.py) and re-runs: 10 failures in (a), (b) and (e) — `gh pr merge` was called on a
  wrong-based PR and on a sibling-targeted PR, and no `gh pr edit` was made. (d) and (f) pass
  pre-fix by design: they guard against the fix over-reaching (an edit when none is needed,
  or one before the malformed-setting refusal).
- **(b) Production path? Yes.** The test calls `merge.merge_wave` → `_merge_one` →
  `_target_base_refusal`, `_pr_head`, `publish._resolve_target`,
  `publish._batch_branch_producer` — all real. Only `subprocess.run`, `merge._sleep`,
  `state.state` and `merged.is_merged` are patched; the bundle's real `brief.md` and sibling
  `publish.json` are read from disk.
- **(c) Fixture includes the fault? Yes.** The host reports a wrong base (`fix/old-parent`);
  the route-2 case has a real sibling bundle (`issue_499`) whose `publish.json` records
  branch `feat/sibling`, the same branch the bundle's brief targets; the failure cases make
  the host actually reject or ignore the edit.

## Commit-readiness

The target has no formatter config, pre-commit config, or `core.hooksPath`
(checked `ls -a`, `.github/workflows`, `git config core.hooksPath`). The only checkers are
the docs lint + site render (T2, clean). Lines I added are ≤ 92 characters, matching the
surrounding code; `git diff --check` is clean.

## Housekeeping

`results/issue_500/.suite-err.log` is stderr from the T3 run I redirected there. It is not
an artifact; the harness can drop it.
