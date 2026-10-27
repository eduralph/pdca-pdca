# Build notes — issue 672 / carry-keeps-a-fold-time-skip-off-the-line (iteration 2)

Target: `eduralph/pdca-harness` `main` @ `d6057eb`. Worktree: `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l1`). Every `path:line` below is post-patch in that worktree
unless it says "base".

## What the previous attempt got wrong, and what this one does instead

Iteration 1 checked each bundle *before* merging it against the bundles already skipped,
and called a shared merge base "the skipped one's work" when the line lacked it. The
review found two holes:

1. **Earlier partial carriers (C5).** A branch merged *before* the skip (Q, cut from P's
   first commit, asked for first) was never looked at again, so P's first commit stayed
   on the pushed line.
2. **False hold from base history (advisory).** In continue mode the line can be behind
   the base. Two branches both updated from the newer base share a base commit the line
   lacks, so an unrelated Y was held "for holding P's work".

This attempt does not re-submit that check. It changes two things:

- **Work is measured against the base, not the line.** A skipped bundle's work is each
  commit its branch adds over `origin/<base>` (merge commits left out), less the commits
  of the bundles of the fold it was built on (`integrate.py:932-951`, `_own_work`;
  `integrate.py:923-929`, `_commits`). Base commits never count. That removes finding 2.
- **Earlier carriers are handled before the push.** After each pass, if any bundle merged
  in it holds a skipped bundle's work, the fold resets the line to where it started and
  folds again; the check before each merge leaves that bundle out this time
  (`integrate.py:592-604`). Nothing has been pushed at that point, so the line is still
  pushed once. That removes finding 1.

## What changed

1. `template/src/pdca_harness/integrate.py`
   - `:68` imports `brief` (a leaf module: only `re` and `pathlib`; no import cycle).
   - `:99-103` new `SkippedWorkOnLine(IntegrationError)`.
   - `:315` new keyword `skip_causes` on `fold`.
   - `:377-399` the `skipped` paragraph of `fold`'s docstring, rewritten as the brief asks.
   - `:536-604` the merge loop:
     - `:538-539` every branch tip is read once, before any merge, so each pass merges and
       judges the same commit (`checked` tips from #633 are still the ones used). Within a
       target's loop no fetch happens, so this reads exactly what the old per-bundle read
       read.
     - `:544` `while True:` around the existing per-bundle loop: one pass normally; another
       only when a bundle merged in it holds skipped work. The loop body is the old body,
       indented one level, plus the #672 lines.
     - `:559-565` before merging, a bundle whose tip holds a skipped bundle's work is
       skipped (raised as a plain `IntegrationError` inside the `try`, so it goes through
       the one existing skip path at `:576-584`).
     - `:574`, `:580` names left out are not tried again in a later pass (monotone).
     - `:582-584` the cause goes into `skip_causes`; each newly skipped bundle's own work is
       computed (`own`).
     - `:592-597` continue mode: if origin's line (the start) already holds skipped work,
       raise `SkippedWorkOnLine` before any push.
     - `:598-604` the earlier-carrier check and the line reset.
   - `:923-962` helpers `_commits`, `_own_work`, `_skipped_work`.
2. `template/src/pdca_harness/flow.py`
   - `_fold_lines`: `:919` parameter, `:934-936` docstring, `:946` pass-through.
   - `_carry_finished`: `:1056-1068` docstring (the "does not spread" residual replaced);
     `:1115-1132` pass `skip_causes`; a bundle held for holding skipped work gets the
     existing `built_on` hint (`_CARRY_HINTS`, `flow.py:991-999`) and its cause in
     `causes`, exactly as `_cascade_not_clean` records a pre-fold cause
     (`flow.py:1002-1029`, untouched). `SkippedWorkOnLine` gets the existing `line` hint,
     like the pre-fold untrusted-line path (`flow.py:1098-1101` on base). Any other error
     keeps today's behaviour (all ids held, `open` hint).
3. `docs/07-crosscutting.md:728-749`: the residual sentence (base `:728-730`) replaced; the
   untrusted-line sentence now also covers a line that already holds skipped work; one
   new entry in "Known limits" (see below).
4. Test: `template/tests/test_flow_resume_stack_prereqs.py:474-666`, ten cases plus four
   helpers, using only the file's existing helpers and module imports.

`_cascade_not_clean` and its hint text are unchanged, as the brief requires. The red
re-gate path, the in-run folds (`skipped=None`, they never take a second pass:
`integrate.py:590-591`), fold order, and "the one asked for first wins" are unchanged.

## Why inside `integrate.fold`, not in the carry before the push

The brief left this to Do. I chose `fold`'s `skipped` mode because the deciding cost is
correctness, not line count:

- **Carry-side alternative:** give `fold` a `push=False` mode, call it once to learn the
  skips, compute containment in `flow.py`, then call `fold` again with the survivors and
  push. Concretely: a push flag through the push block (`integrate.py:607-621`, about 5
  lines), a way to hand back the tips it read (about 5 lines), the same containment
  helpers moved to `flow.py` (about 25 lines), and a second `_fold_lines` call (about 6
  lines). That is about the same size as this patch's ~40 lines of loop change plus ~40
  lines of helpers.
- **What it costs that this does not:** the second call runs `_prepare_worktree` again,
  which re-fetches origin and the base remote (`integrate.py:_fetch`, two fetches per
  target). A branch can move between the judgement and the merge. That is the window
  #633 closed by reading each tip once. Inside `fold`, each tip is read once and the
  commit judged is the commit merged.
- **Rejected outright:** push, then repair with a force-push. The brief forbids it, and
  the tests pin `len(pushes) == 1`.

## The rule for "whose work is a commit", and why it is not the literal invariant

The brief's precise invariant says "no commit that id's branch adds over the base". Taken
literally, that includes the commits of the bundles the skipped id was *built on*. Example:
X is clean, P was cut from `fix/X`, P conflicts with the base. P's branch adds X's commit
over the base, so the literal reading would hold X, and every bundle that depends on X.
In stack mode it is worse: a wave-1 branch is cut from the line, so it holds every
wave-0 branch's commits; one failing wave-1 id would hold all of wave 0. Today X is
carried in that case, so the literal reading would be a regression and a false hold with
a wrong cause. That is the same kind of false hold the review flagged for base commits.

So the rule (`_own_work`, `integrate.py:932-951`) is: a skipped bundle S's work is the
non-merge commits S's tip adds over the base, minus the commits of every other bundle T of
the fold that S was built on, where "built on" means:

- (a) S's branch holds T's whole tip (pure ancestry), or
- (b) S's plain `Depends on` names T. This covers T's branch moving on after S was cut
  from it, for example a review fixup. (b) is ignored when T's branch holds S's tip,
  because then T was built on S whatever the brief says.

Any other bundle whose tip holds any of that work is skipped, whatever its own brief
declares (criterion 2). Merge commits are left out because two branches cut from the same
fold line share that line's merges, which are nobody's work. A branch that holds a
bundle's own merge commit also holds the commits under it.

This matches the invariant's first sentence ("never puts onto the line work its own fold
skipped, directly or through another finished bundle's branch"). X's commit reaches the
line through X's own clean merge, not through the skipped merge. If the reviewer reads the
"Precisely" sentence literally, case (a) will look like a violation. The tests
`test_the_prerequisite_a_skipped_id_was_cut_from_is_still_carried` and
`test_a_declared_prerequisite_that_moved_on_since_is_still_carried` pin this choice, and the
docstrings and docs state it. The human should confirm it at sign-off.

## What I ruled out, and why

- **Literal "anything the skipped branch adds over the base"**: false holds of
  prerequisites (above).
- **Re-trying merge-failure skips on a second pass**: it can flip which of two
  conflicting ids is carried (out of scope) and can oscillate (A excluded, so S merges, so
  A's exclusion is moot, so A is retried, so S fails...). Skips stay monotone, which
  guarantees termination: each extra pass leaves out at least one more bundle, so there
  are at most n+1 passes.
- **Restricting "work" to the first-parent chain** instead of rule (b): it would also
  cover stack-mode line-mates that moved on, but it misses work merged into a PR branch
  from a topic branch, and that miss is a leak. I kept the fail-closed choice.
- **Subtracting each bundle's recorded `stack-base-tip`**: precise for stack mode, but
  it trusts publish metadata that an iterate can rewrite. That is a second source of
  truth I could not fully bound, so I left it out.
- **Printing a "folding again" line on the second pass**: not added; see limits.

## Known limits (all fail closed unless noted)

- **Over-hold:** a finished prerequisite whose branch moved on after another id was cut
  from it, when that other id's merge fails and its `Depends on` does not name it. Rule
  (a) fails because the tip moved, and rule (b) fails because there is no edge, so the
  shared commit counts as the skipped id's and the prerequisite is held too. In stack
  mode this also covers a wave-0 line-mate that got a fixup and is not named by the
  failing wave-1 id. It is listed in the docs' "Known limits".
- **Over-hold:** a bundle that conflicted only with an earlier holder (which is later
  removed by the second pass) stays skipped, because skips are monotone.
- **Not covered (possible leak):** a skipped id whose branch is gone (`head is None`).
  The fold has no tip, so it cannot compute that id's work. This needs an OPEN PR whose
  branch was deleted; its hold message already says to restore the branch.
- **Not covered (possible leak, pathological):** a skipped branch whose only change lives
  in merge commits (no non-merge commit over the base), and a `Depends on` that the
  branches contradict only partly. The guard in (b) catches only the whole-tip case.
- **Cosmetic:** on a second pass, `_gone_branch` / `_take_in_base` run again for a
  merged-and-deleted branch, so their `integrate:` line prints twice and `gh` is asked
  twice. This only happens when an earlier holder forces the second pass.
- `SkippedWorkOnLine` overwrites every held id's reason with the line message (the skipped
  id's own conflict reason is not shown), the same way the pre-fold untrusted-line path
  overwrites reasons. Hold wording is 694's area.

## Red → green (project runner)

C4 gate, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE`/`PDCA_WORKTREE` set, run from
the instance root under `timeout`, on the final patch:

- Green leg: `Ran 28 tests ... OK`.
- Red leg (production hunks reverted, tests kept): `Ran 28 tests ... FAILED (failures=5)`:
  criterion 1, criterion 2, the contradicted `Depends on`, the earlier partial carrier,
  and the old line holding skipped work.
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

The other five new cases pass on `main` on purpose. They guard what the fix must not
break: base history is not work (the advisory case), a prerequisite stays carried (two
variants), a sibling cut from the same line stays carried, and Q folded before P carries
both (the brief's "not changed" fold-order case).

**Mutation checks**: each mechanism was broken on purpose, one at a time, and its pinning
test run, then the file was restored and confirmed byte-identical. All seven went red:

| Mutation | Test that failed |
|---|---|
| ignore `Depends on` in rule (b) | `test_a_declared_prerequisite_that_moved_on_since_is_still_carried` |
| drop the ancestry rule (a) | `test_the_prerequisite_a_skipped_id_was_cut_from_is_still_carried` |
| measure work from the line start, not the base (the iteration-1 bug) | `test_base_history_two_branches_share_is_no_skipped_ids_work` |
| no second pass | `test_a_branch_merged_before_the_skip_with_part_of_its_work_is_left_out` |
| no check of origin's line | `test_a_line_already_holding_a_skipped_ids_work_is_not_carried_onto` |
| count merge commits as work | `test_a_sibling_cut_from_the_same_line_is_still_carried` |
| trust a contradicted `Depends on` | `test_a_depends_on_the_branches_contradict_does_not_carry_the_work` |

Other gates I ran through their wrapper scripts:

- T2 `run-docs-check.sh`: `lint_docs: OK`, render 22 pages, link audit OK.
- T3 `run-suite.sh`: root suite `Ran 24 tests ... OK`; offline driver suite
  `Ran 2469 tests ... OK (skipped=2)`.
- C5 `run-prod-path.py`: "patch adds no new test file", as expected for appended cases.
- The brief's three named modules: `Ran 98 tests ... OK`.

## Refutation (forced)

- **(a) Genuine red? Yes.** The C4 gate reverts the production hunks with
  `git apply -R --exclude=tests/* --exclude=template/tests/*` and keeps the test. Five
  cases failed on their assertions (not import errors), for example D built and in
  `self.seen`, or a push where none is allowed. Restoring the hunks makes all 28 pass.
- **(b) Production path? Yes.** Every case drives `flow._drive_and_act` →
  `_carry_finished` → `_fold_lines` → the real `integrate.fold` against a real bare origin
  and a real primary checkout. Only `gh`, the build leaf and publish are stubbed, as in
  the file's existing cases. The push count is the fixture's spy wrapped around the real
  `integrate._git`.
- **(c) Fixture includes the fault? Yes.** The failing merges really fail: base and P
  change the same file, and `-X ours` really resolves it on `fix/Q`. Each case asserts
  the shape before the run: `fix/P` is an ancestor of `fix/Q`, and main is an ancestor of
  `fix/Q`. The partial carrier has a real two-commit P with Q cut from the first commit.
  The continue-mode cases fold a real earlier line onto origin (and, for the advisory
  case, move main ahead of it and "Update branch" both P and Y). Criterion 2 rewrites
  Q's brief with no edge, so the declared edge cannot be what catches it.

## Commit-readiness

The target has no formatter or pre-commit hook: no `.pre-commit-config.yaml`, no
ruff/black config, and its `.claude/settings.json` has no hooks. Its CI runs
`docs/publishing/tools/lint_docs.py` and `render_site.py --check`; both pass (T2 above).
`git diff --check` is clean. Every added line is 100 columns or less; the three longer
lines in `flow.py` were there before. `patch.diff` applies cleanly to `d6057eb` (checked
with `git apply --cached --check` on a scratch index).

## Interactions

- **673** (edits `fold`'s per-bundle merge loop) will conflict textually: this patch
  re-indents that loop by one level inside `while True:`. 673 needs a rebase onto this
  patch. That is the order the brief already gives (672 first).
- **694** (hold wording in `_carry_finished`) touches the lines at `flow.py:1115-1132`.

## Housekeeping

- My mistake: I wrote one gate log to `/tmp/pdca-672-c4.log`, outside the roots I was
  given. It is a plain text log of a C4 run, safe to delete. I did not delete it myself
  (no `rm`, per the harness rules).
- Inside the worktree, the git-ignored `.cache/pdca-672/` holds the mutation-check backup
  of `integrate.py` and a scratch git index. The backup predates one later docstring-only
  edit (the "a git step that fails while the fold judges..." clause, `integrate.py:396`),
  so it is not the shipped file. Neither file appears in `git status`.
- No external dependency beyond git and Python 3.11+ was needed (none undeclared).
