# Build notes — issue 672 / carry-keeps-a-fold-time-skip-off-the-line

Target: `eduralph/pdca-harness` `main` @ `d6057eb`. Worktree: `$PDCA_WORKTREE`
(`pdca-harness.pdca-wt-l1`). Line numbers below are post-patch, in that worktree.

## What changed

1. `template/src/pdca_harness/integrate.py`
   - `:99-106` new `_HoldsSkipped(IntegrationError)` carrying `cause` (the skipped bundle).
   - `:318` new keyword `skip_causes` on `fold`; docstring for `skipped` extended at
     `:390-399` (the brief asked for this when the behaviour changes).
   - `:537` `dropped` list: every bundle this fold skipped that had a head.
   - `:548-554` under `skipped` only, before merging a bundle, check each dropped head
     with `_holds_work_of`; if this branch holds any of it, raise `_HoldsSkipped`. It is
     inside the existing `try`, so the existing skip path (`:557-566`) records it in
     `skipped` and the merge is never attempted.
   - `:567-570` after a skip: push its head onto `dropped` (so chains work: R cut from a
     contained Q is caught by Q's head too) and fill `skip_causes`.
   - `:894-913` `_holds_work_of(wt, head, other, branch)`: `git merge-base --all head other`;
     true iff some merge base is not in the line (`_in_line`, `:849` on base). Reason: every
     commit both tips share is an ancestor of some merge base, and the line holding a merge
     base holds all its ancestors. So this is exactly "head holds a commit of the skipped
     branch that the line does not". rc 1 with no output = no common history → false. Any
     other git failure raises `IntegrationError`, which under `skipped` skips the bundle
     (fail closed for that bundle, not the whole fold).
2. `template/src/pdca_harness/flow.py`
   - `_fold_lines` `:919`, docstring `:934-936`, pass-through `:946`.
   - `_carry_finished` `:1112-1126`: pass `skip_causes=within`; a contained id gets
     reason "its branch holds work of <cause>, whose merge the fold skipped" with the
     existing `built_on` hint (`_CARRY_HINTS`, `flow.py:997-998`) and its cause in
     `causes`, so its hold line names both the id, its dependents and the cause, exactly as
     `_cascade_not_clean` (`flow.py:1002-1029`) does for pre-fold causes. Plain skips keep
     the `open` hint as before.
   - Docstring of `_carry_finished`: the "does not spread" residual sentence replaced.
3. `docs/07-crosscutting.md:728-733` (was `:728-730`): the residual sentence replaced with the new behaviour.
   `lint_docs.py`: OK.
4. Test: `template/tests/test_flow_resume_stack_prereqs.py:476-524` — helper
   `_skipped_in_the_fold(declared=...)` and two cases for criteria (1) and (2). Uses only
   the file's existing helpers/imports and `sb._git` / `self.fx.human`.

## Why inside `fold` and not in the carry before the push

The brief left this to Do. The carry cannot do it before the push without changing the
fold anyway: `fold` merges and pushes in one call (`integrate.py` push after the loop),
and the carry only learns of the skip from the `skipped` dict after the push. Options:

- (A, chosen) check inside the per-bundle loop, before the merge. One push, no rewrite;
  ~35 production lines across both files. Order-faithful: a bundle folded *before* the
  failing one is not re-judged (its merge put the work on the line, so the later one is a
  no-op, which the brief says is correct and stays).
- (B, rejected) a dry pre-fold in the carry (trial-merge everything, compute skips, then
  fold the survivors). It would need a second worktree pass or a new `push=False` mode on
  `fold` plus a second call: at least the same `fold` change (a flag through the push
  block at `integrate.py:583-593`) plus a re-fold in `flow.py`, and it doubles the merge
  work. It also can't be simpler than (A) since it still needs the ancestry check.
- (C, rejected outright) push then repair with a force-push: forbidden by the brief
  (criterion (1) pins `len(pushes) == 1`).

`skip_causes` is a separate out-dict rather than parsing the message, so the hint is not
tied to wording. It is only filled under `skipped`, so the in-run folds (`skipped=None`)
are unchanged.

Out-of-scope items left alone, per the brief: `_cascade_not_clean` stays edge-only, hint
text unchanged; re-gate handling unchanged; Q-before-P order unchanged.

## Red → green (project runner: `cd template && PYTHONPATH=src python3 -m unittest ...`, run under `timeout`)

- Pre-fix: both new tests FAIL — `issue_D` built; stderr showed
  `flow: carried issue_Q, issue_X ...` and P skipped for a conflict in `base.txt`.
- Post-fix: `tests.test_flow_resume_stack_prereqs`, `tests.test_integrate_stack_bases`,
  `tests.test_flow_same_wave_conflict`: 90 tests OK. Full offline driver suite
  (`unittest discover -s tests` in `template/`): 2461 tests OK (2 skipped).
- Root suite (`python3 -m unittest discover -s tests` at repo root) not run by me; T3 runs it.

## Refutation (forced)

- **(a) Genuine red?** Yes. I reverted only the production hunks (`git apply -R` of the
  `template/src` diff), kept the test and docs, re-ran the two new tests: both FAILED
  (`failures=2`), then re-applied and they pass. The scratch hunk file used for this was
  moved out of the worktree to `results/issue_672/prod-hunks.scratch.diff` (not part of
  the patch).
- **(b) Production path?** Yes. The tests drive `flow._drive_and_act` → `_carry_finished`
  → `_fold_lines` → the real `integrate.fold` against a real bare origin; only `gh`, the
  build leaf and publish are stubbed (as in the file's existing cases). The push count is
  the fixture's spy around the real `integrate._git`.
- **(c) Fixture includes the fault?** Yes. P's merge really conflicts (base got
  `base.txt = r`), Q's branch really resolved it with `git merge -X ours origin/main`
  (the test asserts `fix/P` and `main` are both ancestors of `fix/Q`), and pre-fix the
  leak is observed (D built on a line holding P). Criterion (2) rewrites Q's brief with no
  `Depends on`, so the declared edge is not what catches it.

## Commit-readiness

No formatter or pre-commit hook is configured in the target (no `.pre-commit-config.yaml`;
CI runs `docs/publishing/tools/lint_docs.py`, which passes). `git diff --check` clean.
New lines stay within the file's existing 100-column style.
