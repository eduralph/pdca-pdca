# Adversarial review — issue_646 (re-issued stack run continues its batch's line)

The red→green proof holds. I found two concrete cases where the kept line does something
a human should decide on. Both were reproduced against `$PDCA_TARGET` with a scratch test
that reuses the bundle's own `ResumedStackRun` fixture (real `_drive_and_act`, real fold,
real publish, real git; only `_drive_wave` and `gh` stubbed).

## Findings

- NEEDS-HUMAN — **The continued line keeps a rejected bundle's old commit, and its rebuild
  ships it.** `_carry_finished` checks only *finished* ids against origin's line
  (`template/src/pdca_harness/flow.py:798-800`, `:828`, `:836`;
  `template/src/pdca_harness/integrate.py:281`). It then continues the line exactly as
  origin has it (`flow.py:873`, `:886`). Failing case: batch `[P, X, D]`. The earlier run
  folded P and X. X was then rejected and iterated (iterate archives `patch.diff` /
  `SUMMARY.md` but keeps `publish.json`; its PR is CLOSED). Re-issue: the run drives
  `[D, X]`, and D has `Depends on: P`. Observed: X's stack base is the old line tip, and
  **the old X commit is an ancestor of the new X PR branch**. The rejected change rides
  into X's new PR, and nothing is printed. Before the fix, X was cut from `main`.
  Sign-off item 3 ("a closed PR's branch must not ride the shared line") is enforced only
  for finished ids, not for drive-set bundles the earlier run folded. The same gap applies
  to a finished P whose branch was force-pushed with a rebuilt commit after the earlier
  fold: `_holds` (`integrate.py:552-566`) looks only for the *current* head's commits, so
  an old P commit on the line goes unseen. The human needs to decide: extend the on-line
  check to every requested bundle that has a publish record, or accept and document it.

- NEEDS-HUMAN — **Following the harness's own advice after a failed `gh pr create` blocks
  the whole target, and the new advice does not get you out.** Earlier run: P's branch is
  pushed, `gh pr create` fails, and `publish.json` records `pr_url: ""`
  (`template/src/pdca_harness/publish.py:405-433`). The in-run fold still folds P
  (`flow.py:2236-2237`). The publish message says "Open it by hand"
  (`publish.py:416`). Re-issue `[P, D, U]`: `merged.pr_state` returns "no PR on record"
  (`template/src/pdca_harness/merged.py:112`). The line holds P, so the target is blocked:
  D **and the unrelated U** stay PLANNED, and nothing is built (reproduced). Before the
  fix, U built. The advice "fix what kept issue_P's PR state from being read (its
  publish.json / `gh`)" (`flow.py:864`) points at no command that works. `pdca publish P`
  takes the new-PR path, which has no existing-PR lookup (`_existing_pr` is used only by
  the `Onto branch` path, `publish.py:510`). So `gh pr create` fails again and writes
  `pr_url: ""` again. The only ways out are hand-editing JSON or deleting the line. The
  brief's (4d) counts "no `pr_url`" as unreadable, so this is a scope call. Options: look
  the PR up by its head branch when `pr_url` is empty, or tell the user to edit
  `publish.json` by name.

- (Brief-sanctioned, no action asked.) A finished P whose PR was **squash-merged** and its
  branch deleted now stops every re-issue before wave 0
  (`integrate.py:532-540`, via `flow.py:889-892`). Before the fix, D built correctly on
  `main`, which already had P's change. Brief (5) accepts this raise, the docs require
  merge commits, and the advice ("restore the branch") does work. I'm noting it so the
  sign-off knows a case that used to work is now a hard stop that also blocks unrelated
  bundles.

## Refutation attempts that failed

- **Red→green.** I re-ran the green leg at the target: `tests.test_flow_resume_stack_prereqs`,
  24/24 OK. Red leg, from `gate-logs/C4-verify.log`: 19/24 fail on the expected
  assertions (no line on origin before D's wave; a `--force` push over the earlier line;
  D built and its `p.txt` edit failed to apply on `main`). The 5 that pass on the red leg
  are the "unchanged" cases (5-empty/missing patch, 7-no-dependency, 7-`Stacks on` /
  `Depends on (merged)`, 7-`--no-publish` / merge). They should pass both ways.
- **Production path, not a copy.** D's patch edits `p.txt`, so the real `publish.publish`
  only succeeds if D's branch is cut from a line that holds P. That is not tautological.
  The lock test's depth counter would fail if the fold released its lock before
  `pushed_tip` (the iteration-1 bug), so sign-off item 1 really is pinned.
- **The gone-branch tests use the PR head.** `_fetch` prunes `origin`
  (`integrate.py:647-648`), so `test_4c_a_closed_pr_whose_branch_is_gone_…` resolves P
  through `headRefOid`, not a stale remote ref.
- **No-carry runs unchanged.** The widened `_runnable` hold (`flow.py:719`) can only fire
  for out-of-batch names that `_carry_finished` put in `held`. `integ.update`
  (`flow.py:2270`) cannot keep a stale target, because `accepted` is cumulative. A library
  call with `batch=None` makes `run_batch` the drive set, so `finished` is empty. The
  `flow_batch` sweep excludes COMPLETE bundles, so the child-2 scope stays untouched.
- **Concurrency.** The gap between `read_lines` and the fold is covered: the fold is given
  the checked tip and refuses a moved line (`integrate.py:431-439`). A line that appears
  in that gap gets replaced, which the docstring says openly.
