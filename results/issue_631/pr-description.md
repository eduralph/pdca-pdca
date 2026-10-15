## Summary
**User impact:** A multi-wave run could stop with "did not integrate" even though
every accepted fix merged cleanly. This happened when the between-waves re-gate
left build output behind in the shared integration checkout, or when an earlier
merge was left half-finished. A later fix that touched the same file was then
refused, and the run halted until someone cleaned the checkout by hand. In the
pre-wave carry, a later fix could also be wrongly reported as conflicting
because it was merged into a checkout that was still mid-merge.

This PR makes every fold start from a clean checkout of its starting point, and
makes a failed merge put the checkout back where it was. Ignored files, such as
build caches, are kept.

Reported in [#631](https://github.com/eduralph/pdca-harness/issues/631).

## What to look at
The change is small and lives in `template/src/pdca_harness/integrate.py`:
a new `_reset_tree` helper, one call to it at the start of each fold, and
`_merge` now resetting instead of running `git merge --abort`.

To reproduce: run the new test file against `main` with the production change
reverted, and six of its seven cases fail. A manual version (in `template/`,
`PYTHONPATH=src`): fold branch A, write an untracked `out/build.txt` into the
integration worktree, then fold A plus a branch B that adds `out/build.txt`. On
`main` the second fold raises `IntegrationError` ("could not merge issue_B's
branch … `git merge` exited … with no conflicting path"). With this PR it
succeeds and the line holds B's file.

## Root cause
`_prepare_worktree` only creates the integration worktree when it is missing and
otherwise reuses it as is, and nothing resets it between users (folds, the
carry, the re-gate). So any leftover untracked file, modified tracked file or
`MERGE_HEAD` makes the next `checkout -B` or `git merge` refuse. `_merge` also
ignored the return code of `git merge --abort`, so a failed abort left a
mid-merge tree for the next bundle in the carry's per-bundle `skipped` mode.

## Fix
- **Reset before every fold.** Just before `checkout -B`, the fold runs
  `git reset -q --hard HEAD` then `git clean -q -ffd`. It runs inside the
  existing lifecycle lock, after the up-front refusal checks and before any
  push. `-ff` also removes an untracked nested repository (for example a gate
  that clones or `git init`s into the tree), which a single `-f` skips and which
  blocks a later merge the same way. There is no `-x`: git overwrites ignored
  files on checkout and merge without refusing, so they cannot change a fold's
  result, and keeping them lets the re-gate reuse its caches.
- **A failed merge resets to the pre-merge tip.** `_merge` reads `HEAD` before
  merging and, on failure, resets the tree to it instead of calling
  `merge --abort`. That gives the same end state whenever the abort would have
  worked, and also works when it doesn't.
- **`IntegrationTreeError`** (a subclass of `IntegrationError`) is raised when
  the tree cannot be reset or its tip cannot be read. Existing handlers in the
  flow still catch it, so no caller changes. The carry's `skipped` mode does not
  absorb it, because every later merge would run in an unknown tree.
- Docstrings updated. The template docs already say "each fold resets its tree
  to a freshly fetched ref". With this change that is true as written.

Not changed: the re-gate's verdict and which gates it runs, the Do/Check lane
worktrees, the sweep policy, and the lock scope.

## Verification
Line numbers are on `main` @ `b5f5c29` unless marked post-patch.

- **Claim:** a fold's result depends only on its start ref and the branches it
  merges. Nothing an earlier user left in the shared tree can make it refuse.
  - **Checked:** `template/src/pdca_harness/integrate.py:618-628`: the tree is
    reused when it exists. `:431`: `checkout -B` runs on it with no reset
    before it. The reset now sits just before it (post-patch `:442-446`).
  - **Checked:** `template/src/pdca_harness/flow.py:816-819`: the re-gate runs
    the repo-scoped gates with that tree as cwd. It is the source of the
    leftover build output.
  - **Checked:** `integrate.py:401-415` / `:447-456`: the reset is inside the
    lifecycle lock and before any push, so a fold that raises pushes nothing.
- **Claim:** a failed merge never leaves a mid-merge tree. The carry skips only
  that bundle and goes on, and stops only if the tree cannot be reset.
  - **Checked:** `integrate.py:594`: the unchecked `merge --abort` is replaced
    by a checked reset (post-patch `:603-617`). `:437`: the `skipped` handler
    re-raises `IntegrationTreeError` (post-patch `:453`).
- **Claim:** ignored files are kept.
  - **Checked:** `_reset_tree` runs `clean -ffd` with no `-x` (post-patch
    `:620-633`).
- **Claim:** the docs' "each fold resets its tree" is now accurate.
  - **Checked:** `template/pdca.toml.jinja:216` and
    `template/src/pdca_harness/sweep.py:18`. No doc change needed.
- **Test:** `template/tests/test_integrate_clean_tree.py` (new). It uses real
  git against a bare `origin`, and the real `gates.run_integration` as the
  re-gate:
  - untracked re-gate output blocks the next fold;
  - a rewritten tracked file blocks the next fold;
  - an untracked nested repository blocks the next fold;
  - a failed abort: the carry skips X, then merges B, with no `MERGE_HEAD` left;
  - a failed abort and a failed reset: raises `IntegrationTreeError`, records
    no skip, and pushes nothing;
  - a tree left mid-merge by an earlier user: the next fold succeeds;
  - ignored build caches survive a fold. This one guards behaviour, so it
    passes before and after the fix.

  With the production change reverted, 6 of 7 fail with the errors above.
  With it, all 7 pass. Two mutation checks confirm the new assertions do real
  work: `-ffd` → `-fd` fails only the nested-repo case, and dropping the
  `IntegrationTreeError` re-raise fails only the reset-fails case. Full offline
  suite: `template/tests` 2376 tests OK (2 skipped), root suite 24 OK.

This touches the same per-bundle loop in `fold` as the fix for #633: one added
condition on the existing `raise` and one reworded comment.

Fixes #631
