# Build notes — issue 593, iteration 6 (stack-mode-append-only-fold-real-base-prs)

Target: `eduralph/pdca-harness @ main` (`24c7f83`), worktree `pdca-harness.pdca-wt-l0`.
Line numbers below are on the patched tree unless marked "base".

## What I did

The brief says to start from `iteration-v5/patch.diff`, which it calls correct apart from
the deleted-branch path (replaced by ii-b) and the late-publish guard (new, i-b). I applied
that patch (it applied cleanly to `24c7f83`) and then changed five things on top of it:

1. **Tip storage (i-a).** Round 5 put the tip on a second line of `stack-base`. Now it is a
   sibling file, `stack-base-tip`:
   - `STACK_BASE_TIP_FILE` at `template/src/pdca_harness/publish.py:49`.
   - `write_stack_base(d, branch, tip=None)` at `publish.py:638` writes `stack-base`
     exactly as base did, and writes the tip file when `tip` is given or removes it when
     not.
   - `clear_stack_base` (`publish.py:654`) removes both files.
   - New reader `read_stack_base_tip` at `publish.py:681`; it returns `""` when there is
     no `stack-base`.
   - `_read_stack_base` (`publish.py:664`) is back to the base code byte for byte, so
     `gates.py:568`, `drift._resolve_base` and `tests/test_verify_base.py` see no change.
     Round 5's `_stack_marker` is gone.
   - `publish()` reads the branch and the tip separately (`publish.py:236-238`). It cuts
     from the tip when one is recorded (`:261-265`), and `checkout_base` is the tip itself.
     So the host-CI path pins the same commit and `host_ci_base` equals it. The existing
     pin code is unchanged (`_host_ci_passes` and `_pin_checkout`, called at
     `publish.py:381-387`).

2. **Late-publish guard (i-b, new).** `_line_tip_refusal` at `publish.py:691-726` is
   called at `publish.py:362-370`, after `_check_repo` and before anything is pushed. Its
   steps:
   - Fetch origin.
   - `cat-file -e <tip>^{commit}`: a missing commit means "not on the line".
   - `rev-parse origin/<line>`: a missing line means "not on the line".
   - `merge-base --is-ancestor <tip> origin/<line>`: rc 0 means on the line, rc 1 means
     not on it, and any other rc is a git failure.

   When the tip is not on the line, publish refuses with rc 1 and a message naming the
   bundle, the full tip SHA, the branch, "Re-drive it in a new run (#616)", and that
   nothing was pushed. A failed fetch or a git failure also refuses, with its own message.
   The dry-run plan prints a comment line for the guard (`publish.py:342-345`).

3. **Deleted published branch (ii-b), decided by commit.**
   - New `merged.merged_head(cfg, id)` at `template/src/pdca_harness/merged.py:62-91`
     runs `gh pr view <pr_url> --json state,headRefOid` and returns `headRefOid` only when
     `state == "MERGED"`. Everything else returns `None`. `is_merged` (`merged.py:32`) is
     unchanged.
   - `integrate._gone_branch` at `integrate.py:409-445` replaces round 5's version and its
     `_merges_past` subject scan, which I deleted. No `<base>..HEAD` range and no commit
     subject is read anywhere now. Its logic:
     - `merged_head` is `None`: raise, naming the bundle and the ref.
     - The merged head is on the line being built (`_carries`, `integrate.py:448-454`: a
       commit the clone does not have counts as "not on the line", never as an error):
       skip it with one stderr line, and do not merge the base in.
     - Otherwise, for a record whose PR targeted this fold's base: merge
       `<base_remote>/<base>` in (`_take_in_base`, `integrate.py:457-475`). It is signed
       off, unforced, skipped when the base is already in the line, and raises naming the
       conflicting paths.
     - An `Onto branch` record raises.
   - `this_runs_line` is gone from `_merge_published` (`integrate.py:382`) and from the
     fold loop (`integrate.py:363`).

4. **"Pushed this run" signal (iv).** `flow._publish_bundle` (`flow.py:642-665`) now
   returns `rc is not None and after is not None and after != before`, where both values
   are `publish.json`'s `st_mtime_ns` (`_record_mtime`, `flow.py:668-674`).
   - An exception logged by `_isolate` gives `None`, so the result is `False`.
   - Round 5 used `rc == 0 or (mtime, content) changed`. The brief asks for mtime only and
     no rc shortcut.
   - The flow keeps a positive set, `pushed` (`flow.py:1713`), filled at `flow.py:1861-1862`
     only when the signal is True. A bundle whose texts were not ready is never added.
   - The hold is `integrate.unpublished(accepted, pushed=pushed)` (`flow.py:1890`,
     definition `integrate.py:144-154`). It returns every targeted, patched bundle with no
     branch on record or not in `pushed`. It is the same helper (`_fold_candidates`) the
     fold uses to refuse.
   - `_runnable`'s keyword is now `held` (`flow.py:682`, check at `:712`).

5. **Docs and comments (viii).**
   - Round 5's docs edits are kept.
   - Added to `docs/07-crosscutting.md` (the stack bullet near line 642) and to
     `template/PCDA/quality-cycle/09-parallel-lanes.md:69`: commits pushed onto a PR branch
     after a fold reach the line; a deleted branch is judged by the commit its PR merged
     with; a late publish refuses once a later run replaced the line.
   - The `drift._resolve_base` docstring (`drift.py:50-61`) no longer says "exactly as
     publish does". It says publish cuts from the recorded tip while drift checks the line
     as it is now, a known cross-run limit (#616).
   - The `cli._publish_flag` comment (`cli.py:1058-1060`) now says plainly that the cue
     means "part of a stack, merge bottom-up".
   - Module and function docstrings in `integrate.py` (`:1-40`, the `fold` docstring) and
     `merged.py:1-19` describe the commit-based rule.

Unchanged from round 5 and re-checked against the brief:
- `folded_this_run` and its fresh / continue / auto behaviour (`integrate.py:218-379`).
- The mismatch refusal naming both SHAs and #591 (`:349-357`).
- An unforced push when continuing (`:368`), and the force-push remedy text (`:369-377`).
- The pruning fetch of the remotes that hold PR branches (`_prepare_worktree`,
  `:506-529`).
- The dry-run plan text (`:314-329`).
- `_point_at_integration` gaining `tips` (`flow.py:722-742`). I kept `tips` optional,
  defaulting to `None`, because `tests/test_integrate.py:323-342` calls it with two
  arguments and the brief says those tests must keep passing.
- The flow reads the tip right after `fold` returns (`flow.py:1904-1911`).
- The real base for wave>0 PRs (`publish.py:282`).

## Where I went past the brief's literal wording (all fail-closed or cosmetic)

1. **A deleted branch whose PR did not target this base raises** (`integrate.py:436-444`).
   - The brief says: for `"new-pr"` / `"stacked-pr"`, merge the base in; for `"stacked"`,
     raise. I raise whenever the record's `base` differs from the fold's base. For every
     record the wave flow writes, this gives the same result as the brief's rule
     (`new-pr` and wave `stacked-pr` both record the real base).
   - It differs only for a legacy `Stacks on:` PR, which targets its parent's branch.
     Merging main in would not carry that work, and the line would silently lack it.
   - Cost: 3 lines plus one test (`test_a_gone_branch_whose_pr_targeted_another_branch_
     is_not_taken_from_the_base`, `test_integrate_stack_bases.py:481`).
   - If the human wants the literal rule, drop the `or rec.get("base") != base` term and
     that test.

2. **`merged_head` also returns `None` when `gh` is not installed** (`OSError`,
   `merged.py:78-79`). `is_merged` lets that raise. Inside a fold, a raw
   `FileNotFoundError` would escape the flow's `except IntegrationError` and crash the
   run. The brief's ii-b.1 says "any gh failure ... returns None", so I read a missing
   `gh` as a gh failure.

3. **The guard fetches with `--prune`** (`publish.py:706`). Without it, a deleted
   `pdca-integration/main` stays as a stale remote-tracking ref and the guard judges a
   line that no longer exists. Case 15's second half (`test_integrate_stack_bases.py:721-
   726`) passes either way, but only for the right reason with `--prune`. The fold already
   prunes origin in the same clone, so this is not new behaviour for that repo.

4. **The dry-run plan prints the guard** (`publish.py:342-345`). It is cosmetic and only
   appears when a tip is recorded, which a dry-run flow never records.

5. **The test helper `_merged_heads` also patches `merged.is_merged` the same way**
   (`test_integrate_stack_bases.py:97-108`). Without that, a fold that only asks "is it
   merged?" (round 5) would hit `is_merged`'s COMPLETE-state check and fail for an
   unrelated reason. With it, cases 7 and 8 fail against round 5 for the exact reasons the
   brief names (shown below). The final code never calls `is_merged` in the fold.

## Red → green evidence

All runs used the project's own scripts or the CONTRIBUTING command, under `timeout`.

**C4 gate** (`./engine/scripts/run-verify.sh` with `PDCA_BUNDLE` and `PDCA_WORKTREE` set,
final patch). Output: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

| Module | Green leg | Red leg (production reverted) |
|---|---|---|
| `test_flow_adopt_split` | 29 OK | 29 OK (only its spy signatures changed) |
| `test_flow_slice` | 108 OK | FAILED (failures=9, errors=1) |
| `test_integrate` | 14 OK | FAILED (failures=1: `test_overlap_raises_integration_error`) |
| `test_integrate_stack_bases` | 40 OK | FAILED (failures=17, errors=26) |

No `unittest.loader._FailedTest` appeared on the red leg (0 matches), so every module
imported. The tests import modules only, and the new functions are reached as attributes
at test time.

**Against round 5's production code with my tests** (I swapped the production hunks,
kept my tests, then restored; the worktree was re-checked byte-equal to `patch.diff`):
- Case 7 (`test_merged_prerequisites_already_on_the_line_are_skipped_by_commit`): ERROR,
  `IntegrationError: issue_A's branch origin/fix/A is gone and its PR is merged, but
  origin/main ... does not merge onto pdca-integration/main (conflicts in c.txt ...)`.
  This is the needless stop from round 5 §6 item 3.
- Case 8, deleted branch (`test_a_fixup_merged_with_its_deleted_branch_reaches_the_line`):
  FAIL, `'a\n' != 'a, after review\n'`. The fixup is lost (round 5 §6 item 4).
- Case 15 (`test_a_late_publish_refuses_a_tip_the_line_no_longer_holds`): FAIL, rc 0.
  Round 5 published from the orphaned tip.
- Cases 8 (live branch), 9, 11, 14 and 14b pass on round 5. That is expected: round 5
  already merged live tips, took the base in, and cut from a recorded tip.

**Targeted mutations** (each applied alone, then restored and re-verified against
`patch.diff`):
- M1: signal = "the record exists", mtime ignored. Caught: the stale-record re-publish
  test fails (the old branch would be folded).
- M2: signal = `rc == 0`. Caught: the "pushed, then `gh pr create` failed" test fails
  (the branch would be held).
- M3: the merged head is never treated as carried. Caught: case 7 and the Onto-branch
  skip error out.
- M4: a merged branch is always treated as carried. Caught: case 8 (deleted), case 9 and
  case 11 fail.

**Wider suites:**
- `template/tests`: `Ran 2264 tests ... OK (skipped=2)`. Both skips are pre-existing
  template-checkout skips (role-prompt sync, Jinja counts).
- `./engine/scripts/run-suite.sh`: root suite 24 OK, driver suite OK.
- `./engine/scripts/run-docs-check.sh`: docs lint clean, site render and link audit clean.
- `run-prod-path.py` (C5): the added test imports `pdca_harness`.

## Case map (brief numbering → test)

All cases are in `template/tests/test_integrate_stack_bases.py` unless marked
`test_flow_slice.py`.

| Case | Test (line) |
|---|---|
| 1 | `test_a_later_fold_appends_to_the_line_and_carries_the_pr_commits` (246) |
| 2 | `test_a_continuing_fold_pushes_without_force` (263); `test_a_listed_target_continues_this_runs_tip_without_force` (273) |
| 3 | `test_a_runs_first_fold_starts_fresh_over_an_earlier_runs_line` (289) |
| 4 | `test_a_line_another_run_moved_is_refused` (300) |
| 5 | `test_an_onto_branch_record_merges_that_remotes_branch_not_origins` (316) |
| 6 | `test_an_unpublished_bundle_stops_the_fold_before_any_git_step` (528) |
| 7 | `test_merged_prerequisites_already_on_the_line_are_skipped_by_commit` (392) |
| 8 | `test_a_fixup_pushed_onto_a_live_branch_is_merged_by_the_next_fold` (347); `test_a_fixup_merged_with_its_deleted_branch_reaches_the_line` (364) |
| 9 | `test_a_merged_branch_the_line_never_carried_comes_in_through_the_base` (422) |
| 10 | `test_a_gone_branch_not_known_merged_stops_naming_the_ref` (470); `test_a_gone_onto_branch_record_is_skipped_only_when_the_line_has_its_head` (496); plus deviation 1's test (481) |
| 11 | `test_a_merged_head_missing_from_the_clone_is_not_carried` (445) |
| 12 | `test_a_chain_dependents_diff_shrinks_once_its_prerequisite_merges` (602) |
| 13 | `test_a_dependent_on_two_siblings_shrinks_after_a_base_update` (611); `test_a_chain_on_a_moved_base_keeps_a_second_merge_base_until_updated` (627); flow-level `test_a_dependent_carries_every_earlier_wave_branch_not_only_its_prerequisite` (`test_flow_slice.py:1621`) |
| 14 | `StackPublishDryRun` (729-790); `test_a_wave_bundle_publishes_against_the_real_base` (649); `test_a_late_publish_is_cut_from_the_recorded_line_tip` (678); flow-level `test_a_held_bundle_published_later_is_cut_from_the_line_it_was_built_on` (`test_flow_slice.py:1708`) |
| 14b | `test_a_late_publish_through_host_ci_pins_the_recorded_line_tip` (691) |
| 14c | `StackBaseTip.test_write_read_and_clear` (805) |
| 15 | `test_a_late_publish_refuses_a_tip_the_line_no_longer_holds` (704) |
| 16 | `test_each_later_fold_continues_the_tip_the_runs_last_fold_pushed` (`test_flow_slice.py:1363`); `test_a_three_wave_run_folds_append_only_onto_a_real_origin` (`:1573`) |
| 17 | `test_a_dry_run_lists_the_folded_target_and_plans_start_then_continue` (`test_flow_slice.py:1380`) |
| 18 | `test_an_unpublished_bundle_holds_only_its_dependents` (`:1406`); `test_texts_not_ready_hold_the_bundle_though_an_earlier_record_survives` (`:1429`); `test_a_patched_bundle_with_no_target_does_not_hold_its_dependents` (`:1453`); `test_a_failed_re_publish_is_held_though_an_earlier_record_survives` (`:1654`); `test_a_re_publish_whose_pr_create_failed_is_folded_and_its_dependents_build` (`:1679`) |
| 19 | `StackFoldDryRun` (823-873) |
| 20 | `MergedHead` (926-981) |

For case 18, both stale-record variants now run with `today="2026-10-03"`. The stale
record's mtime is set back an hour with `os.utime` in `_earlier_attempt`
(`test_flow_slice.py:1520-1538`), as the brief asks.

## Refute-your-own-test answers

- **(a) Genuine red? Yes.**
  - With the production hunks reverted (C4 red leg), three of the four touched modules
    fail: 9+1, 1 and 17+26 failures and errors, with no import failures.
  - Against round 5's code, the three cases round 5 got wrong fail for the named reasons.
  - Each of the four mutations M1-M4 is caught by exactly the test meant for it.
- **(b) Production path? Yes.**
  - Every fold case calls the real `integrate.fold` against a real bare origin plus a
    primary checkout, with real `git merge`, `push` and `fetch --prune`.
  - The publish cases call the real `publish.publish`: real fetch, guard, host-CI pin,
    ephemeral worktree and push. Only `_warn_if_squash_only` (`gh repo view`) is patched.
  - The flow cases drive the real `flow.flow_ids` → `_drive_and_act` with the real fold.
    Do, Check and sign-off are replaced by `_accept_wave`, and publish by a function that
    pushes the branch the way publish does.
  - The only stand-in is the host's answer about PR state (`merged.merged_head` /
    `is_merged`). The brief requires `gh` to be patched.
- **(c) Fixture includes the fault? Yes.**
  - Branches are really merged into origin's main with `--no-ff` and really deleted on
    origin, while the primary checkout still holds stale tracking refs, so pruning is
    exercised.
  - The clashing `c.txt` really lands on main (case 7).
  - The fixup is a real commit pushed to the real PR branch (case 8).
  - A fresh line is really force-pushed over the recorded tip, and the line is really
    deleted (case 15).
  - Origin really refuses non-fast-forward pushes in the append-only cases.
  - The stale `publish.json` really has an old mtime (case 18).

## For the human at sign-off

- **Live-host check (the brief lists it as owed at sign-off, not a Do dependency).** On a
  disposable GitHub repo:
  1. Put A and C in wave 0 and B on both.
  2. Merge A and C with merge commits.
  3. Look at B's "Files changed", then use "Update branch", then merge B.
  4. Delete a merged prerequisite's branch and confirm the next fold recognises it through
     the real `gh pr view --json state,headRefOid` path. Expect the stderr line
     `... is gone and its PR merged at <sha> — pdca-integration/<base> already carries
     that commit; skipped.`

  I could not run this offline.
- **Vendored model spec edits.** `template/PCDA/quality-cycle/09-parallel-lanes.md` and
  `08-glossary.md` are edited, which needs a human per INTEGRATION §4 (the brief notes
  this).
- **Patch size.** `patch.diff` is 178 KB against the brief's ~148 KB. The extra comes
  mostly from the test file: 985 lines, up from round 5's 691, for the new cases 7, 8 (two
  tests), 9, 10 (three tests), 11, 14 (late publish), 14b, 14c, 15 and 20. The brief says
  the 125 KB size backstop is set aside by the human's no-split decision.
- **Commit hooks.** The target has no pre-commit config, no `core.hooksPath` and no Python
  formatter. Its PR checks are `docs-check.yml` (run above, clean), `render-check.yml`
  (the root suite, run above, OK) and the linked-issue check (a publisher artifact). DCO
  sign-off is added by publish's `commit -s`.
- **Scratch files.** Under the worktree's git-ignored `.cache/`: `c4-run.log`,
  `t3-run.log`, `mine.diff`, `flow.py.keep`, `integrate.py.keep`. They are not in the
  patch, and the harness reclaims the worktree.
