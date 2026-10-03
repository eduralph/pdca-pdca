# Build notes — issue 593, iteration 7 (stack-mode-append-only-fold-real-base-prs)

Target: `eduralph/pdca-harness @ main` (`24c7f83`), worktree `pdca-harness.pdca-wt-l0`.
Line numbers are on the patched tree unless marked "base".

## What I did this round

I applied round 6's `iteration-v6/patch.diff` (it applied cleanly to `24c7f83`) and changed
only what the carry-forward asks for. Compared with round 6, this round touches 4 files
(195 lines added, 49 removed): `integrate.py`, the stack-bases test file, and two docs. Of
the `integrate.py` lines, 14 are code; the rest are docstrings.

1. **The fold checks that the base has the merged head before taking it in.**
   `integrate._gone_branch`, new check at `template/src/pdca_harness/integrate.py:451-458`.
   It runs after the existing "already on the line?" check (`:437-441`) and the existing
   `Onto branch` / other-base refusal (`:442-450`), and before `_take_in_base` (`:459`).
   - It calls `_carries(wt, head, …, base_ref, of=base_ref)`. That runs
     `git cat-file -e <head>^{commit}`, then `git merge-base --is-ancestor <head> <base_ref>`.
   - Exit 0: the base has the head, so the base is merged in as before.
   - Exit 1, or the head commit is not in the clone: raise `IntegrationError`. The message
     names the bundle, the PR URL from `publish.json`, the full head SHA and the base, and
     says "it merged somewhere other than `<base_ref>`". It gives two ways out: restore the
     branch, or get the work into the base.
   - Any other exit code: `_in_line` raises its existing "a git step failed" error.
   - To do this, `_carries` (`:462-468`) and `_in_line` (`:492-503`) gained a keyword
     `of: str = "HEAD"` (the commit to test against). The default keeps every existing
     caller unchanged.
   - Squash and rebase merges now stop here too, as the carry-forward accepts. Their head
     commit is never an ancestor of the base.

2. **The base remote is fetched last.** In `_prepare_worktree` (`integrate.py:537-538`), the
   order is now: `origin`, then any `Onto branch` remotes, then the base remote.
   - The `--prune` rule is unchanged: the remotes that hold PR branches are pruned.
   - Own-repo (base remote = `origin`): still one fetch of `origin`, with `--prune`.
   - Why: a merged PR's branch is deleted after the merge. If a fetch shows the branch as
     gone, a base fetched after it already has the merge. Fetched first (round 6), a fork's
     base could be a snapshot from before a merge whose branch the next fetch then saw as
     deleted.
   - The docstring at `:527-534` says this.

3. **Docs that claimed the base "holds that work" without checking it.**
   - `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, as the carry-forward asks: the
     fold checks that the base has that commit and then merges it in; if the base does not
     have it (merged into another branch, or squashed / rebased), the fold STOPs the run.
   - `docs/07-crosscutting.md:664-668` said the same thing as the old 09 text, so I changed
     it to match.
   - In `integrate.py`, the module docstring (`:32-40`), the `fold` docstring (`:253-259`),
     `_gone_branch` (`:413-429`) and `_take_in_base` (`:472-475`) now say the base is checked.

4. **Tests** in `template/tests/test_integrate_stack_bases.py`:
   - **(a)** `test_a_fixup_merged_into_another_branch_stops_the_fold` (`:474`) is the
     adversary repro. A fixup is pushed to fix/A after the fold. fix/A is merged `--no-ff`
     into `release`, then deleted. `merged_head` returns the fixup SHA. The fold raises the
     merged-elsewhere error, and origin's line stays at T1 (nothing pushed).
   - **(b)** `test_a_branch_never_carried_and_merged_into_another_branch_stops_the_fold`
     (`:495`) is case 9's shape, merged into `release`. It raises, and nothing is pushed.
   - `test_a_failing_base_check_is_a_git_step_failure` (`:513`): only the new
     `merge-base --is-ancestor <head> origin/main` call is made to exit 128. The fold
     raises "exited 128 … git step failed", not the merged-elsewhere error.
   - `test_a_pr_merged_and_deleted_between_the_folds_fetches_is_still_carried` (`:541`) is
     the fetch-order race, on a real fork setup (a bare `upstream` as the base remote, PR
     branches on `origin`). A spy on `integrate._git` waits until the fold's first fetch has
     finished. Then, before the second fetch, a scratch clone merges fix/A into upstream's
     main and deletes fix/A on origin. The test asserts four things: the line has A's
     `a.txt`, the line was appended to, the last fetch was `upstream`, and `merged_head`
     was never asked.
   - Helper `_merge_pr(iid, *, into="main")` (`:178`) now takes the target branch. Existing
     callers are unchanged.
   - `_assert_merged_elsewhere` (`:467`) checks the four parts of the new message.

## Where this round departs from the brief's text (decided by the carry-forward)

- **Case 11 changed.** The brief's case list says "merged head SHA not present in the local
  clone → treated as not carried (base merged in), no exception". The carry-forward
  overrides that: "rc 1, or the head commit not in the clone → raise". The fold fetches the
  base before this check, so a head the clone lacks cannot be in the base.
  - `test_a_merged_head_missing_from_the_clone_is_not_carried` (`:447`) now asserts the
    merged-elsewhere error, and that nothing is pushed.
  - It still pins round 6's point that a missing commit is not a git failure: it asserts
    the message does not say "git step failed". Mutation M6 below shows this matters.
- **ii-b.4's "the base now holds that work" is now checked, not assumed.** This is the
  carry-forward's change. The brief's (ii-b.4) text predates it.

## Kept from round 6 (unchanged code, re-checked against the brief)

The full round-6 rationale is in `iteration-v6/build-notes.md`. In short:
- **Tip storage (i-a).** `stack-base-tip` (`publish.py:49`), written and removed by
  `write_stack_base` / `clear_stack_base` (`publish.py:638`, `:654`) and read by
  `read_stack_base_tip` (`publish.py:681`). `_read_stack_base` (`publish.py:664`) is
  byte-for-byte the base version. The recorded tip is the cut point and the host-CI pin.
- **Late-publish guard (i-b).** `_line_tip_refusal` (`publish.py:691`).
- **Head lookup (ii-b.1).** `merged.merged_head` (`merged.py:62`). `is_merged`
  (`merged.py:32`) is unchanged.
- **Append-only fold (iii).** `fold(…, folded_this_run=…)` (`integrate.py:219`).
- **Hold (iv).** `integrate.unpublished` (`integrate.py:145`) and the flow's `pushed` set
  (`flow.py:1713`, `:1890`). The pushed-this-run signal is `_publish_bundle` /
  `_record_mtime` (`flow.py:642`, `:668`).
- **Tips to the next wave.** `_point_at_integration(…, tips)` (`flow.py:722`) and the fold
  call (`flow.py:1906`).

Round 6's deviations still stand. The human may want to revisit two of them now:
1. **A deleted branch whose `publish.json` base is not this fold's base raises**
   (`integrate.py:442-450`). This is for a legacy `Stacks on:` PR. With the new base
   check, this rule no longer prevents a silent drop: a head that is not in the base is
   refused anyway. It now only adds a stop for one case: a `Stacks on:` PR merged into its
   parent's branch, after which the parent merged into main (the base has the head, so
   taking it in would be correct). The carry-forward said to keep everything else, so I
   kept it.
   - Cost to drop it: delete the `or rec.get("base") != base` term and its `what` branch
     (3 lines in `_gone_branch`), and change the expectation in
     `test_a_gone_branch_whose_pr_targeted_another_branch_is_not_taken_from_the_base`
     (`:606`). That test uses `ABSENT`, so without the rule it would hit the new
     merged-elsewhere error instead: a 1-line assertion change.
2. `merged_head` returns `None` when `gh` is not installed (`merged.py:78-79`).
3. The publish guard fetches with `--prune`.
4. The dry-run publish plan prints the guard.
5. The test helper `_merged_heads` patches `is_merged` consistently with `merged_head`.

**A check in `_take_in_base` can no longer be reached** (`integrate.py:476`, "a line that
already has the base needs nothing"). The caller has just shown that the head is in the
base and not in the line, so the base cannot be in the line. With several deleted branches
in one fold, the second one's head is already on the line once the first has merged the
base in, so it is skipped earlier, at `:437`. I kept the check because the brief's (ii-b.4)
asks for "skip if the base is already in the line", and it costs one `git merge-base` call
per base merge. Removing it is 1 `if` plus 10 re-indented lines (`:476-486`).

## Alternatives I ruled out

- **Checking ancestry after merging the base** (the adversary's other suggestion: "or of
  the line after the base merge"). This needs the same one git call. Checking before the
  merge answers the actual question (does the base have the head?) and leaves the worktree
  untouched when the fold refuses. Checking after would need a `git reset` to undo the merge
  commit before raising.
- **Fetching the missing head by `refs/pull/N/head`** to tell a squash from a wrong-branch
  merge. The brief puts this out of scope, and the carry-forward accepts that squash and
  rebase merges stop.
- **Moving the check into `_take_in_base`.** That function has no `publish.json` record,
  so naming the PR would mean reading the record a second time or adding a parameter.
  `_gone_branch` already has the record (`:442`) and is where the numbered decision steps
  live. Same size either way (one `if` and one `raise`).
- **Fetching the base first and then re-fetching it at the end.** This costs one extra
  network fetch per fold, for nothing that fetching it last does not already give.

## Red → green evidence

All runs used the project's own scripts, under `timeout`, with `PDCA_BUNDLE` and
`PDCA_WORKTREE` set and the final `patch.diff`.

**C4 gate** (`./engine/scripts/run-verify.sh`): `PDCA-EVIDENCE: C4 PASS — red without the
fix, green with it`.

| Module | Green leg | Red leg (production reverted to `24c7f83`) |
|---|---|---|
| `test_flow_adopt_split` | 29 OK | 29 OK (only its spy signatures changed) |
| `test_flow_slice` | 108 OK | FAILED (failures=9, errors=1) |
| `test_integrate` | 14 OK | FAILED (failures=1) |
| `test_integrate_stack_bases` | 44 OK | FAILED (failures=17, errors=30) |

There were 0 `unittest.loader._FailedTest` matches, so every module imported on both legs.
On `24c7f83` the five new or changed tests error with `TypeError: fold() got an unexpected
keyword argument 'folded_this_run'`: the whole round-6 API is missing there.

**Against round 6's code (the rejected attempt), with this round's tests.** This is the
red that matters for the carry-forward. I ran it before writing any production change:
- (a) `test_a_fixup_merged_into_another_branch_stops_the_fold`: FAIL, `IntegrationError
  not raised`. Round 6 merged main in and went on without the fixup.
- (b) `test_a_branch_never_carried_and_merged_into_another_branch_stops_the_fold`: FAIL,
  `IntegrationError not raised`.
- Case 11: FAIL, `IntegrationError not raised`. Round 6 printed "the merged work reaches
  pdca-integration/main through origin/main" for a commit it could not see.
- `test_a_failing_base_check_is_a_git_step_failure`: FAIL, `IntegrationError not raised`
  (round 6 never asked).
- The race test: FAIL, `'a.txt' not found in ['base.txt', 'z.txt'] : the line went on
  without A's work`. This is the fork-target silent drop the adversary described.

**Targeted mutations** (each applied alone to the final code; `integrate.py` was restored
and compared byte-for-byte after each one; run over `test_integrate_stack_bases` +
`test_integrate`):

| Mutation | Caught by |
|---|---|
| M5: no base check | (a), (b), case 11, git-failure test (4 failures) |
| M6: base check without the `cat-file` guard (missing commit read as a git failure) | case 11 only |
| M7: base remote fetched first again | the race test. It errors with a false stop: "merged somewhere other than upstream/main" |
| M8: base check against the line (`of="HEAD"`) instead of the base | case 8 (deleted branch) and case 9, the merged-into-main cases, plus the git-failure test |

M8 shows that the existing merged-into-main cases guard against refusing too often, and
they stay green with the real fix.

**Other gates**, all on the final patch:
- T3 `./engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`; driver suite
  `Ran 2269 tests … OK (skipped=2)`. The 2 skips existed before this patch.
- T2 `./engine/scripts/run-docs-check.sh`: docs lint clean, site render and link audit clean.
- C5 `run-prod-path.py`: the added test imports `pdca_harness`.
- `git diff --check`: clean. `patch.diff` applies to `24c7f83`, checked against a scratch
  index.
- After each C4 run, the worktree was byte-equal to `patch.diff`.

## Case map (brief numbering → test)

All cases are in `template/tests/test_integrate_stack_bases.py` unless marked
`test_flow_slice.py`.

| Case | Test (line) |
|---|---|
| 1 | `test_a_later_fold_appends_to_the_line_and_carries_the_pr_commits` (248) |
| 2 | `test_a_continuing_fold_pushes_without_force` (265); `test_a_listed_target_continues_this_runs_tip_without_force` (275) |
| 3 | `test_a_runs_first_fold_starts_fresh_over_an_earlier_runs_line` (291) |
| 4 | `test_a_line_another_run_moved_is_refused` (302) |
| 5 | `test_an_onto_branch_record_merges_that_remotes_branch_not_origins` (318) |
| 6 | `test_an_unpublished_bundle_stops_the_fold_before_any_git_step` (653) |
| 7 | `test_merged_prerequisites_already_on_the_line_are_skipped_by_commit` (394) |
| 8 | `test_a_fixup_pushed_onto_a_live_branch_is_merged_by_the_next_fold` (349); `test_a_fixup_merged_with_its_deleted_branch_reaches_the_line` (366) |
| 9 | `test_a_merged_branch_the_line_never_carried_comes_in_through_the_base` (424) |
| 10 | `test_a_gone_branch_not_known_merged_stops_naming_the_ref` (595); `test_a_gone_onto_branch_record_is_skipped_only_when_the_line_has_its_head` (621); deviation 1's test (606) |
| 11 | `test_a_merged_head_missing_from_the_clone_is_not_carried` (447), now a stop, per the carry-forward |
| 12 | `test_a_chain_dependents_diff_shrinks_once_its_prerequisite_merges` (727) |
| 13 | `test_a_dependent_on_two_siblings_shrinks_after_a_base_update` (736); `test_a_chain_on_a_moved_base_keeps_a_second_merge_base_until_updated` (752); `test_flow_slice.py:1621` |
| 14 | `StackPublishDryRun` (854-916); `test_a_wave_bundle_publishes_against_the_real_base` (774); `test_a_late_publish_is_cut_from_the_recorded_line_tip` (803); `test_flow_slice.py:1708` |
| 14b | `test_a_late_publish_through_host_ci_pins_the_recorded_line_tip` (816) |
| 14c | `StackBaseTip.test_write_read_and_clear` (930) |
| 15 | `test_a_late_publish_refuses_a_tip_the_line_no_longer_holds` (829) |
| 16 | `test_flow_slice.py:1363`; `test_flow_slice.py:1573` |
| 17 | `test_flow_slice.py:1380` |
| 18 | `test_flow_slice.py:1406`, `:1429`, `:1453`, `:1654`, `:1679` (stale record's mtime set back in `_earlier_attempt`, `:1520`) |
| 19 | `StackFoldDryRun` (948-998) |
| 20 | `MergedHead` (1051-1106) |
| Carry-forward (a) | `test_a_fixup_merged_into_another_branch_stops_the_fold` (474) |
| Carry-forward (b) | `test_a_branch_never_carried_and_merged_into_another_branch_stops_the_fold` (495) |
| Base check, other exit codes | `test_a_failing_base_check_is_a_git_step_failure` (513) |
| Base fetched last | `test_a_pr_merged_and_deleted_between_the_folds_fetches_is_still_carried` (541) |

## Refute-your-own-test answers

- **(a) Genuine red? Yes.**
  - All five new or changed tests fail on round 6's code, for the reasons the
    carry-forward names (a missing stop, and the line going on without A).
  - They also fail on `24c7f83` (C4 red leg, no import failures).
  - Each mutation M5-M8 is caught by the test meant for it.
- **(b) Production path? Yes.**
  - Every new case calls the real `integrate.fold`, against a real bare origin and a real
    primary checkout. Fetch, prune, `cat-file`, `merge-base`, `merge` and `push` are all
    real git.
  - The race test drives the real `_prepare_worktree` fetch loop. Its spy only adds the
    outside merge and delete between two real fetches, and passes every call through to
    the real `_git`.
  - The only stand-in is the host's answer about the PR (`merged.merged_head` and
    `is_merged`). The brief requires `gh` to be patched.
- **(c) Fixture includes the fault? Yes.**
  - fix/A is really merged `--no-ff` into a real `release` branch on origin and really
    deleted. The fixup is a real commit on the real PR branch.
  - In the race test, the merge really lands on a separate `upstream` bare repo and fix/A
    is really deleted on `origin`, at the point between the fold's two fetches.
  - The merged-into-main cases (8, 9) still use real merges into main, and they stay green.

## For the human at sign-off

- **Live-host check (owed at sign-off, not a Do dependency; deferred to a follow-up per the
  carry-forward, §10).** Round 6's steps still apply. One step to add: edit a merged-to-be
  PR's base to another branch, merge it, delete its branch, and confirm the next fold stops
  with "merged somewhere other than origin/<base>". I could not run this offline.
- **Squash or rebase merges of a prerequisite whose branch is deleted now stop the run,**
  when the line does not already have the PR's final head. The docs say so
  (`09-parallel-lanes.md:69`, `docs/07-crosscutting.md:666-668`). If the PR's head is
  already on the line (no fixup after the fold), the fold skips it at `:437` before this
  check, so a squash merge with no later fixup does not stop.
- **Vendored model spec edits.** `template/PCDA/quality-cycle/09-parallel-lanes.md` and
  `08-glossary.md` are edited. Per INTEGRATION §4 these need a human. The carry-forward
  says T5 was already approved this round; this round only changes the one sentence in 09
  that it asked for.
- **Patch size.** `patch.diff` is now 188 KB, up from round 6's 178 KB. Most of the growth
  is the four new tests (+124 lines). The brief says the human's no-split decision sets the
  125 KB size limit aside.
- **Commit hooks.** The target has no pre-commit config, no `core.hooksPath`, and no Python
  formatter or linter config. Its PR checks are `docs-check.yml` (T2, run above, clean),
  `render-check.yml` (the root suite, run above, OK) and the linked-issue check (a
  publisher artifact). New lines stay within the 100-column maximum the base
  `integrate.py` already uses. Publish's `commit -s` adds the DCO sign-off.
- **Scratch files.** These are under the worktree's git-ignored `.cache/`: gate logs
  (`c4-run.log`, `t2-run.log`, `t3-run.log`, `c5-run.log`), `mutate.py`,
  `integrate.py.keep`, `round7-integrate.diff`, and the scratch index files
  (`base-check.index`, `interdiff.index`). They are not in the patch. The new test file is
  left untracked in the worktree, as round 6 left it.
