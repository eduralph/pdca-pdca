# Build notes — issue 631 / fold-starts-from-a-clean-integration-tree (iteration 3)

Target: eduralph/pdca-harness @ main, `b5f5c29`. "Base" line numbers are on `b5f5c29`.
"Post-patch" line numbers are in the same file with `patch.diff` applied. Unless a path is
given, the file is `template/src/pdca_harness/integrate.py`.

## Iteration 3: what the carry-forward asked, and what changed

The round-2 finding: `test_failed_abort_and_failed_reset_stops_the_fold` only checked for
the base class `integrate.IntegrationError`. Any other `IntegrationError` on that path would
also have passed. It should pin the new `IntegrationTreeError` and show that `issue_X` is not
recorded as an ordinary skip.

Fix (`template/tests/test_integrate_clean_tree.py:217-229`):

```python
with self._abort_fails(reset_fails_after_merge=True), \
        self.assertRaises(integrate.IntegrationError) as caught:
    integrate.fold(self.cfg, [x, b], folded_this_run={TARGET: t1}, skipped=skipped)
self.assertIsInstance(caught.exception, integrate.IntegrationTreeError)
self.assertEqual(skipped, {})                      # neither issue_X nor issue_B
self.assertEqual(self._tip(LINE), t1)              # nothing pushed
```

Why two steps instead of `assertRaises(integrate.IntegrationTreeError)` directly: with the
fix reverted, the module has no `IntegrationTreeError`. The direct form would then error
with `AttributeError` while building the `assertRaises` argument. C4 counts that as red, but
the red would not name the defect. In the two-step form the red leg fails with
`AssertionError: IntegrationError not raised`. That is the real pre-fix behaviour: the
carry swallows the failure, records both X and B as skipped, and goes on. Post-fix, the
`assertIsInstance` pins the subclass. The name is still reached as a module attribute, so
the file's "only modules are imported" rule holds and the module loads on the red leg.

Mutation check: I removed the guard at post-patch `:453` (back to `if skipped is None:`)
and ran the C4 gate. Only this test failed, with `AssertionError: IntegrationError not
raised`. Restored afterwards.

### Also changed, from the round-2 advisory code review

These were not in the carry-forward. They are not among the five deferred findings in
`deferred-findings.json` either; those are older plan-review items plus the T5 prior-art
question, all left for the human. Each change below is small and has evidence attached.

1. **`git clean -fd` → `git clean -ffd`** (post-patch `:628`, docstring `:620-627`). The
   advisory review said a single `-f` skips an untracked directory that is a git repository
   of its own. I checked this with git 2.53.0 in a scratch repo:
   - `git clean -n -fd` lists nothing for an untracked `out/` that holds `.git`.
     `git clean -n -ffd` lists `Would remove out/`.
   - With that nested repo left in place, merging a branch that adds `out/build.txt`
     fails with `error: The following untracked working tree files would be overwritten
     by merge: out/build.txt` and exit 2. That is the same refusal as criterion (1).
   - `git clean -ffd` with no `-x` keeps ignored content, including an ignored nested
     repo. It removes only untracked, non-ignored plain directories and nested repos.
   The brief's Invariant excludes only ignored files. A leftover nested repo, from a gate
   that clones into the tree or runs `git init`, or from `pip install -e git+…` with its
   default `--src ./src`, is inside the Invariant. The brief's Scope says "Untracked files
   that are not ignored are removed (`git clean -fd`-equivalent, no `-x`)". I read the
   parenthetical as naming that meaning: remove untracked, keep ignored. A single `-f`
   does not fully deliver it. `-ffd` does, and it still has no `-x`.
   Risk of the second `-f`: it deletes an untracked nested repo inside the integration
   tree. The harness owns that tree. The default sweep removes it outright
   (`template/pdca.toml.jinja:214-218`, `template/src/pdca_harness/sweep.py:16-19`).
   Tracked submodules are not untracked, so `clean` never touches them. The lock sidecar
   is next to the tree, not inside it (base `:241`, post-patch `:250`).
   New test `test_untracked_nested_repo_does_not_block_the_next_fold`
   (`template/tests/test_integrate_clean_tree.py:171-180`). It is red with the fix
   reverted. It is also red with the fix applied but `-ffd` changed back to `-fd`: that
   mutation fails only this test, with `IntegrationError: could not merge issue_B's branch
   origin/fix/B onto pdca-integration/main — \`git merge\` exited 2 with no conflicting
   path …`. With `-ffd` it is green.
2. **Stale inline comment** (post-patch `:455`, base `:439`): "this bundle only; the merge
   was aborted" → "this bundle only; its merge was undone". The code no longer runs
   `merge --abort`, and the `skipped` docstring (post-patch `:346`) already says "undone".
   No behaviour change. The carry's contract that the brief quotes is unchanged in
   meaning: only this bundle is affected, and the tree is back where it was.
3. **`IntegrationTreeError` docstring** (post-patch `:70-76`): it now also names the third
   way it is raised. `_merge` cannot read the tip it would reset to (post-patch
   `:606-609`). No behaviour change.

Not taken from that review: the extra `rev-parse HEAD` per merge (post-patch `:606`). The
reviewer recorded it as checked, with no change needed.

## What the patch changes

All of it is in `template/src/pdca_harness/integrate.py`, plus the new test file.

1. **`IntegrationTreeError(IntegrationError)`**, post-patch `:70-76`, inserted after
   `IntegrationError` (base `:63-67`). It means the tree could not be put back to a known
   commit. It lets the carry's `skipped` handler tell "this bundle failed" from "the tree
   is broken". It subclasses `IntegrationError`, so the flow's existing handlers around
   the fold still catch it: `flow.py:934` for the #646 carry (its `_fold_lines` call at
   `:931`) and `flow.py:2298` for the in-run fold (`:2295`). No caller changes.
2. **Every fold resets the tree before `checkout -B`**: post-patch `:442-446`, just before
   the existing `checkout -B` (base `:431`, post-patch `:447`). It calls
   `_reset_tree(wt, "HEAD")`: `git reset -q --hard HEAD` drops `MERGE_HEAD` and restores
   tracked files, then `git clean -q -ffd` removes untracked, non-ignored files and
   directories, nested repos included. The call is inside the lifecycle lock (base
   `:406-415`, post-patch `:417-426`). It comes after the "continue" refusal (base
   `:419-428`), so a refused fold leaves the tree alone. It comes before any push (base
   `:447-456`, post-patch `:463-472`), so a fold that raises here pushes nothing. On a
   freshly created tree both commands do nothing.
3. **A failed merge resets to the pre-merge tip instead of `merge --abort`**: `_merge`,
   post-patch `:599-617` (base `:583-595`). It reads `HEAD` before merging (`:606`). When
   the merge exits non-zero, it calls `_reset_tree(wt, before)` (`:616`) in place of the
   unchecked `_git(wt, "merge", "--abort")` (base `:594`). If `HEAD` cannot be read, or
   either reset step fails, it raises `IntegrationTreeError`. `_take_in_base` also merges
   through `_merge` (base `:554`, post-patch `:570`), so it gets the same handling.
4. **The carry's `skipped` mode does not absorb `IntegrationTreeError`**: post-patch
   `:453` (base `:437`): `if skipped is None or isinstance(exc, IntegrationTreeError):
   raise`. This is criterion (3)'s "Only if that reset also fails does the fold raise".
5. **`_reset_tree` helper**: post-patch `:620-633`.
6. **Docstrings**: `fold`'s `skipped` paragraph (base `:334-341`, post-patch `:343-352`)
   and `_merge`'s (post-patch `:600-605`) now describe the reset, and the raise when the
   tree cannot be reset.

The docs needed no change. `template/pdca.toml.jinja:216` and
`template/src/pdca_harness/sweep.py:18` say "each fold resets its tree to a freshly fetched
ref — the base, or the run's pushed tip". Base `:218` (post-patch `:227`) says the tree is
"reused (reset) across folds". With the patch these are true as written: reset and clean,
then `checkout -B` onto `start_ref`. `start_ref` is `<base_remote>/<base>` or origin's line
as just fetched (base `:430`).

## Why always reset, rather than "abort, then reset if the abort fails"

Criterion (3) says the fold "puts the tree back to the line tip it had before X's merge
(e.g. `git reset --hard` to it)". The fold always resets and never calls `--abort`:

- `merge --abort` behaves like `reset --merge`. It differs from `reset --hard` only in
  keeping unrelated local edits. The fold has just reset the tree, and a successful merge
  leaves it clean, so there are no such edits. `reset --hard <before>` gives the same end
  state whenever the abort would have worked, and it also works when the abort fails.
- The alternative in `_merge` needs `before` as well:

  ```python
  if _git(wt, "merge", "--abort") != 0:
      _reset_tree(wt, before)
  ```

  That is 2 lines where the chosen fix has 1. Its "abort worked" branch would also skip
  the `clean`, so the two branches would leave different trees.
- A failed `git merge` makes no commit, so `HEAD` does not move. If it ever did, resetting
  to `before` still lands on the tip the fold had.

The (3) tests patch `integrate._git` so `merge --abort` fails, as the brief specifies. With
the fix, that call never happens. That is the point: the outcome (X skipped, B on the line,
no `MERGE_HEAD`) no longer depends on the abort working. On the reverted code, the failed
abort is what makes the test red.

## Ruled out

- **Reset only after the re-gate** (in `flow._fold_lines`, after `gates.run_integration`,
  `flow.py:816-819`). It does not cover a crashed fold or carry, or a failed abort, which
  leave the same state. The brief's Invariant rules it out by name, and it fails (3) and
  (4).
- **`git clean -fdx`.** It would delete the re-gate's ignored build caches for no gain:
  git overwrites ignored files on checkout and merge without refusing (the brief checked
  this). `test_ignored_build_cache_is_kept` pins that ignored files survive a fold.
- **`git clean -fd` (a single `-f`).** It leaves an untracked nested repo in place, and
  that repo blocks a later merge. See "Also changed" item 1 for the evidence.
- **`git checkout -f -B` instead of reset plus checkout.** `-f` discards tracked edits
  and overwrites untracked files in the checkout's way. It leaves untracked files that the
  start ref does not have. In (1), `out/build.txt` is not in `t1`, so it survives the
  checkout and B's merge still refuses. It would need the `clean` anyway, so it saves
  nothing.
- **Recreating the worktree on every fold** (`worktree remove --force`, then `worktree
  add` in `_prepare_worktree`, base `:618-628`). Sketch: about 4 lines (a remove with its
  error check, and an unconditional add). It also costs a full checkout per fold, loses
  the ignored caches, and does not fix the failed abort inside a fold (criterion (3)).
  That still needs the `_merge` change. So it is not smaller.
- **No new exception class.** The `skipped` handler must tell "this bundle failed" from
  "the tree cannot be reset". A subclass of `IntegrationError` does that without touching
  any caller: everything that catches `IntegrationError` still catches it.

## Test

`template/tests/test_integrate_clean_tree.py` is a new file, at the path the brief names.
It uses real git with a bare `origin` and a primary checkout. The fixture is copied from
`StackFoldGit` in `test_integrate_stack_bases.py`. It is not subclassed, because a subclass
would re-run all of that class's tests. The re-gate is the real `gates.run_integration`
with a repo-scoped gate.

| Test (file:line) | Criterion |
|---|---|
| `test_untracked_regate_output_does_not_block_the_next_fold` (`:148`) | (1) |
| `test_modified_tracked_file_does_not_block_the_next_fold` (`:161`) | (2) |
| `test_untracked_nested_repo_does_not_block_the_next_fold` (`:173`) | (1), with the leftover a nested repo; Invariant |
| `test_failed_abort_resets_the_tree_and_the_carry_goes_on` (`:202`) | (3) |
| `test_failed_abort_and_failed_reset_stops_the_fold` (`:217`) | (3), "only if that reset also fails"; raises `IntegrationTreeError`; no skip recorded |
| `test_fold_starts_clean_from_a_tree_left_mid_merge` (`:233`) | (4) |
| `test_ignored_build_cache_is_kept` (`:247`) | Invariant, no `-x`. A guard: green before and after the fix |

## Refuting my own test

- **(a) Genuine red? Yes.** I wrote `patch.diff` and ran the project's C4 gate on it from
  the instance root:
  `PDCA_BUNDLE=<abs>/results/issue_631 PDCA_WORKTREE=<lane> timeout 900
  ./engine/scripts/run-verify.sh`. The gate reverts only the production hunks and keeps
  the test. Red leg: `Ran 7 tests … FAILED (failures=2, errors=4)`. Six of seven fail,
  with the errors the brief predicts:
  - (1), (2) and the nested-repo case: `IntegrationError: could not merge issue_B's branch
    origin/fix/B onto pdca-integration/main — \`git merge\` exited 2 with no conflicting
    path …`
  - (4): `IntegrationError: could not start pdca-integration/main off <t1>`
  - (3): `'issue_B' unexpectedly found in` `skipped`, with "conflicts in a.txt", because
    the tree still holds X's conflicted merge.
  - (3), reset also fails: `AssertionError: IntegrationError not raised`.
  - `test_ignored_build_cache_is_kept` passes on both legs, as a guard should.
  Green leg: `Ran 7 tests … OK`. Gate verdict: `PDCA-EVIDENCE: C4 PASS — red without the
  fix, green with it`, exit 0. Same result on the final `patch.diff`, after the last
  docstring edit.
  Two mutation runs (each restored afterwards) show the new assertions do real work:
  `-ffd` → `-fd` fails only the nested-repo test, and removing the `isinstance` guard fails
  only the reset-fails test.
- **(b) Production path? Yes.** Every test calls the production `integrate.fold`. The
  re-gate cases call the production `gates.run_integration` with a repo-scoped gate that
  writes into the fold's worktree. The only patch is a wrapper around `integrate._git` in
  the two (3) tests. It calls the real function and fails only `merge --abort` (and, in
  one test, `reset` after the first merge). Every other git call is real.
- **(c) Fixture includes the fault? Yes.** The leftover state is really in the tree before
  the next fold runs, and the tests assert it is there. The gate really writes
  `out/build.txt`, really rewrites `a.txt`, and really runs `git init` in the fold's
  worktree (`assertEqual(... "gate\n")`, `assertTrue((wt / "out/.git").is_dir())`). Case
  (4) runs a real conflicting `git merge` in the worktree and asserts `MERGE_HEAD` exists.
  In (3), X's merge really conflicts and leaves `MERGE_HEAD`. One honest caveat on (3):
  with the fix, the fold no longer calls `merge --abort`, so the injected abort failure
  only matters on the reverted code. The post-fix run still really goes through a
  mid-merge tree (X's conflict) and really resets it. The reset-fails test drives the
  real new raise path.

## Other checks

- Full suites through the project's T3 runner (`./engine/scripts/run-suite.sh`, under
  `timeout 1800`), with the patch applied: root suite `Ran 24 tests … OK`, driver suite
  (`template/tests`) `Ran 2376 tests … OK (skipped=2)`, verdict `PDCA-EVIDENCE: root suite
  OK, driver suite OK`, exit 0. That is one test more than iteration 2's 2375: the new
  nested-repo case. It covers `test_integrate`, `test_integrate_stack_bases`,
  `test_regate`, and the flow tests that spy on `integrate._git`. (This run was on the
  final code except the `IntegrationTreeError` docstring reflow, which changes no code; C4
  was re-run after that edit.)
- Commit-readiness: the target has no pre-commit config, no `core.hooksPath`, and no
  active hooks (only `*.sample` files in the hooks directory). Its CI runs no formatter or
  Python linter (`.github/workflows/`: docs-check, docs, render-check,
  require-linked-issue). No `ruff`, `flake8` or `black` is configured or installed.
  `git diff --check` is clean, the test file ends with a newline, and every added line is
  under 100 characters. That matches the file: its only 100-character lines are the
  existing base `:103-104` (post-patch `:112-113`).
- Conflict note for 633 (same per-bundle loop in `fold`): in that loop, this patch adds
  one condition to the existing `raise` (post-patch `:453`) and rewords one comment
  (`:455`). Everything else is before the loop (`:442-446`) or in `_merge` /
  `_reset_tree` (`:599-633`).
- No external dependency beyond git and the stdlib, as the brief says. No NEEDS-HUMAN
  item from the build.
- Housekeeping, for the human. My git experiments ran in
  `<lane>/.cache/pdca-631-scratch/`, which the target's `.gitignore` (`/.cache/`) ignores,
  so it is not in `git status` or the patch. The T3 log is in the same place. One slip:
  a command of mine wrote a copy of the diff to `/tmp/.x`, outside the roots I was given.
  It holds only this patch's diff text and nothing reads it. I did not delete it, because
  cleanup is the harness's job; remove it if you want.
