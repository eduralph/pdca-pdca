# Build notes — issue 631 / fold-starts-from-a-clean-integration-tree

Target: eduralph/pdca-harness @ main, `b5f5c29`. Line numbers below are post-patch in
`template/src/pdca_harness/integrate.py` unless they say "base" (= `b5f5c29`).

## What changed

1. **`WorktreeError(IntegrationError)`** — `integrate.py:70-74`. A new subclass for "the
   tree could not be put back to a known commit". Existing callers that catch
   `IntegrationError` (flow, carry) still catch it; it only exists so the carry's
   per-bundle `skipped` handler can tell "this bundle failed" from "the tree is broken".

2. **Every fold resets the tree before `checkout -B`** — `integrate.py:438-442`, calling
   `_reset_tree(wt, "HEAD")` right before the existing `checkout -B` (base `:431`). That
   is `git reset -q --hard HEAD` (drops `MERGE_HEAD` and restores tracked files) then
   `git clean -q -fd` (removes untracked, non-ignored files). No `-x`, per the brief's
   Invariant. It sits inside the lifecycle lock (base `:406-415`) and after the
   "continue" refusal (base `:419-428`), so nothing about the refusal order or the
   "nothing pushed on raise" rule (base `:447-456`) changes. A fresh worktree is already
   clean, so the reset is a no-op there.

3. **A failed merge resets to the pre-merge tip instead of `merge --abort`** —
   `_merge`, `integrate.py:602-613` (base `:583-595`). It records `HEAD` before the merge
   and, on a non-zero merge exit, calls `_reset_tree(wt, before)`. If either git step
   fails, `WorktreeError` is raised.

4. **The carry's `skipped` mode lets `WorktreeError` through** — `integrate.py:449`
   (base `:437`): `if skipped is None or isinstance(exc, WorktreeError): raise`. This
   matches criterion (3): only when the reset also fails does the fold raise.

5. **`_reset_tree` helper** — `integrate.py:616-627`.

The docs that claim "each fold resets its tree to a freshly fetched ref"
(`template/pdca.toml.jinja:216`, `template/src/pdca_harness/sweep.py:18`) are now true
as written, so I left them alone.

## Why reset instead of "abort, then reset if abort fails"

The brief's wording in (3) is "if `git merge --abort` fails, reset". I went one step
simpler: always reset to the pre-merge tip, never call `--abort`. Reasons:

- `merge --abort` is `reset --merge`. Its only difference from `reset --hard` is that it
  keeps unrelated local edits, and the fold has just reset the tree, so there are none
  to keep. `reset --hard <before>` gives the same end state in every case where abort
  works, and also works where abort fails.
- One call, with its return code checked, is easier to reason about than two, one of
  them a fallback. The rejected version is roughly 3 more lines in `_merge`
  (`if _git(wt, "merge", "--abort") != 0: _reset_tree(wt, before)`) plus an untidy
  case: abort succeeds but leaves untracked leftovers (e.g. `file~HEAD` from a rename
  conflict), which `--abort` does not remove and the next bundle's merge in the same
  fold could trip on. The reset path also runs `clean -fd`, which covers that.
- If HEAD moved during a failed merge (it should not: a non-zero `git merge` creates no
  commit), resetting to `before` still lands on the line tip the fold had.

The test for (3) patches `integrate._git` so `merge --abort` fails. With the fix it is
never called, which is fine: the test checks the outcome (X skipped, B on the line, no
`MERGE_HEAD`), and on the reverted code the failed abort is what makes it red.

## Ruled out

- **Reset only after the re-gate** (in `flow._fold_lines` after `gates.run_integration`,
  base `flow.py:816-819`). Does not cover a crashed fold/carry or a failed abort, which
  leave the same state. The brief's Invariant says this explicitly.
- **`git clean -fdx`.** Would remove the re-gate's ignored build caches for no gain:
  git overwrites ignored files on checkout/merge without refusing. The test
  `test_ignored_build_cache_is_kept` pins that ignored files survive.
- **`git checkout -f -B`** instead of reset + checkout. `-f` throws away tracked edits but
  does not remove untracked files that the next merge would overwrite, so (1) would still
  fail; it would need `clean` anyway.
- **Recreating the worktree each fold** (`worktree remove` + `add`). Also clean, but costs
  a full checkout per fold and loses the ignored caches. ~6 lines in `_prepare_worktree`
  vs. the 2-command reset.

## Test

`template/tests/test_integrate_clean_tree.py` (new). Real git with a bare `origin` and a
primary checkout; fixture copied from `test_integrate_stack_bases.py`'s `StackFoldGit`
(not imported/subclassed, because subclassing would re-run all of that class's tests
here). The re-gate is the real `gates.run_integration` with a repo-scoped gate.

| Test | Criterion |
|---|---|
| `test_untracked_regate_output_does_not_block_the_next_fold` | (1) |
| `test_modified_tracked_file_does_not_block_the_next_fold` | (2) |
| `test_failed_abort_resets_the_tree_and_the_carry_goes_on` | (3) |
| `test_failed_abort_and_failed_reset_stops_the_fold` | (3), "only if that reset also fails" |
| `test_fold_starts_clean_from_a_tree_left_mid_merge` | (4) |
| `test_ignored_build_cache_is_kept` | Invariant: no `-x` (guard; green before and after) |

## Refuting my own test

- **(a) Genuine red?** Yes. I ran the project's C4 gate
  (`PDCA_BUNDLE=results/issue_631 ./engine/scripts/run-verify.sh`, which reverts the
  production hunks and keeps the test). Red leg: 5 of 6 fail, with the exact errors the
  brief predicts — (1)/(2) "could not merge issue_B's branch … `git merge` exited 2 with
  no conflicting path", (4) "could not start …", (3) `issue_B` lands in `skipped`
  ("conflicts in a.txt", because the tree still holds X's conflicted merge), and the
  reset-failure leg gets "IntegrationError not raised". The ignored-cache guard passes
  on both sides, as intended. Green leg: 6/6. Gate output:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- **(b) Production path?** Yes. Every test calls the production `integrate.fold` and the
  production `gates.run_integration`. The only patch is `integrate._git` in the (3)
  tests, wrapping the real function and failing just `merge --abort` (and, in one test,
  `reset` after the first merge) — every other git call is real.
- **(c) Fixture includes the fault?** Yes. The leftover state is really in the tree: the
  gate really writes `out/build.txt` / rewrites `a.txt` in the fold's worktree (asserted
  before the next fold); (4) runs a real conflicting `git merge` in the worktree and
  asserts `MERGE_HEAD` exists; (3) really leaves the tree mid-merge because the abort
  fails.

## Other checks

- `PYTHONPATH=src python3 -m unittest discover -s tests` in `template/`: 2375 tests OK
  (2 skipped), including `test_integrate`, `test_integrate_stack_bases`, `test_regate`.
- Commit-readiness: the target has no pre-commit config, no `core.hooksPath`, no
  installed hooks, and no formatter/linter in its CI beyond docs lint (which this patch
  does not touch). `ruff` is not installed here; lines are kept under 100 chars to match
  the file's style.
- Conflict note: 633 also edits the per-bundle loop in `fold`; my change there is one
  condition on the existing `raise` (`integrate.py:449`) plus the reset before
  `checkout -B` (`:438-442`).
