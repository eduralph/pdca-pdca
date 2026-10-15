# Build notes — issue 631 / fold-starts-from-a-clean-integration-tree (iteration 2)

Target: eduralph/pdca-harness @ main, `b5f5c29`. "post-patch" line numbers are in
`template/src/pdca_harness/integrate.py` with the patch applied; "base" means `b5f5c29`.

## Iteration 2 — what the carry-forward asked, and what changed

The round-1 finding: the new class was named `WorktreeError`, the same name as the unrelated
`worktree.WorktreeError` (`template/src/pdca_harness/worktree.py:62`), which `cli.py:459`,
`gates.py:377` and `publish.py:1028` catch. A reader could think those handlers catch the new
error too. They don't.

Fix: renamed it to **`IntegrationTreeError`** (post-patch `integrate.py:70-75`) everywhere it
is raised or tested for (post-patch `:452`, `:607`, `:624`, `:627`). Its docstring now also
says why the flow catches it: it subclasses `IntegrationError`, which the flow already
catches (`flow.py:915`, `:922`, `:934`). No behaviour change. `grep -rn WorktreeError
template/src/pdca_harness/integrate.py` is now empty.

Two wording fixes that go with it, also no behaviour change:

- `fold`'s `skipped` docstring (base `:334-341`, post-patch `:341-351`) said "a failed merge
  is aborted". It now says the merge is undone by resetting the tree to the line tip it had
  before it, and it lists a tree that cannot be reset (`IntegrationTreeError`) among the
  failures that still raise in `skipped` mode. The old text did not mention the new raise.
- The test helper `_abort_fails` docstring now says the failed abort leaves the tree
  mid-merge *for a fold that relies on `merge --abort`*. With the fix the fold no longer
  calls it, so the old wording ("the tree really is left mid-merge") was only true pre-fix.

Everything else is the round-1 design, re-verified below on the same base.

## What the patch changes

1. **`IntegrationTreeError(IntegrationError)`** — post-patch `integrate.py:70-75`. "The tree
   could not be put back to a known commit." It exists so the carry's per-bundle `skipped`
   handler can tell "this bundle failed" from "the tree is broken".

2. **Every fold resets the tree before `checkout -B`** — post-patch `integrate.py:441-445`,
   right before the existing `checkout -B` (base `:431`, post-patch `:446`). It calls
   `_reset_tree(wt, "HEAD")`: `git reset -q --hard HEAD` (drops `MERGE_HEAD`, restores
   tracked files), then `git clean -q -fd` (removes untracked files that are not ignored).
   No `-x`, per the brief's Invariant. It sits inside the lifecycle lock (base `:401-415`)
   and after the "continue" refusal (base `:419-428`), so the refusal order and the
   "nothing pushed when a fold raises" rule (base `:447-456`) are unchanged. On a freshly
   created tree both commands are no-ops.

3. **A failed merge resets to the pre-merge tip instead of `merge --abort`** — `_merge`,
   post-patch `integrate.py:598-616` (base `:583-595`). It reads `HEAD` before the merge
   (`:605`) and, when the merge exits non-zero, calls `_reset_tree(wt, before)` (`:615`)
   in place of the unchecked `_git(wt, "merge", "--abort")` (base `:594`). If `HEAD`
   cannot be read, or either reset step fails, it raises `IntegrationTreeError`.

4. **The carry's `skipped` mode lets `IntegrationTreeError` through** — post-patch
   `integrate.py:452` (base `:437`): `if skipped is None or isinstance(exc,
   IntegrationTreeError): raise`. That is criterion (3)'s "only if that reset also fails
   does the fold raise `IntegrationError`".

5. **`_reset_tree` helper** — post-patch `integrate.py:619-630`.

Docs: `template/pdca.toml.jinja:216` and `template/src/pdca_harness/sweep.py:18` say "each
fold resets its tree to a freshly fetched ref — the base, or the run's pushed tip", and
`integrate.py:218` says the tree is "reused (reset) across folds". With the patch these are
true as written (reset + clean, then `checkout -B` onto `start_ref`, which is
`<base_remote>/<base>` or origin's line as just fetched, base `:430`), so I left them alone.

## Why reset instead of "abort, then reset if abort fails"

Criterion (3) says "the fold puts the tree back to the line tip it had before X's merge (e.g.
`git reset --hard` to it)". I always reset and never call `--abort`:

- `merge --abort` is `reset --merge`. It differs from `reset --hard` only in keeping
  unrelated local edits. The fold has just reset the tree, and a successful merge leaves it
  clean, so there are none to keep. `reset --hard <before>` gives the same end state
  whenever abort works, and also works when abort fails.
- The alternative is longer and has two paths to test instead of one. Sketch, in `_merge`
  (it still needs `before`):

  ```python
  if _git(wt, "merge", "--abort") != 0:
      _reset_tree(wt, before)
  ```

  That is 2 lines where the chosen fix has 1, and the "abort worked" branch would skip the
  `clean` step, so the two branches would not leave the same tree.
- A failed `git merge` creates no commit, so `HEAD` should not move. If it ever did,
  resetting to `before` still lands on the tip the fold had.

The test for (3) patches `integrate._git` so `merge --abort` fails, as the brief specifies.
With the fix that call never happens, which is the point: the outcome (X skipped, B on the
line, no `MERGE_HEAD`) no longer depends on abort working. On the reverted code the failed
abort is what makes the test red.

## Ruled out

- **Reset only after the re-gate** (in `flow._fold_lines`, after `gates.run_integration`,
  `flow.py:816-819`). It does not cover a crashed fold or carry, or a failed abort, which
  leave the same state. The brief's Invariant rules this out explicitly. It also fails (3)
  and (4).
- **`git clean -fdx`.** Would delete the re-gate's ignored build caches for no gain: git
  overwrites ignored files on checkout and merge without refusing (the brief checked this).
  `test_ignored_build_cache_is_kept` pins that ignored files survive a fold.
- **`git checkout -f -B` instead of reset + checkout.** `-f` discards tracked edits and
  overwrites untracked files *in the way of the checkout*, but leaves untracked files the
  start ref does not have. In (1), `out/build.txt` is not in `t1`, so it survives the
  checkout and B's merge still refuses. It would need `clean` anyway, so it saves nothing.
- **Recreating the worktree every fold** (`worktree remove --force`, then `worktree add`
  in `_prepare_worktree`, base `:618-628`). Sketch: about 4 lines (a remove with its
  error check, an unconditional add). It also costs a full checkout per fold, loses the
  ignored caches, and does not fix the in-fold failed-abort path (criterion (3)), which
  still needs the `_merge` change. So it is not smaller.
- **No new exception class**: the `skipped` handler must tell "this bundle failed" from
  "the tree cannot be reset". A subclass of `IntegrationError` does that without touching
  any caller: everyone who catches `IntegrationError` still catches it.

Known limit, left as is: `git clean -fd` (no second `-f`) skips an untracked directory that
is itself a git repository. A re-gate that `git clone`s into the tree would leave that
directory. The brief asks for the `clean -fd` equivalent, and nothing in the harness puts a
nested repository in the integration tree, so I did not widen it.

## Test

`template/tests/test_integrate_clean_tree.py` (new file, as the brief names). Real git with a
bare `origin` and a primary checkout; the fixture is copied from
`test_integrate_stack_bases.py`'s `StackFoldGit` (not subclassed, because a subclass would
re-run all of that class's tests). The re-gate is the real `gates.run_integration` with a
repo-scoped gate. The module imports only modules (`gates`, `integrate`) and only uses
names that exist on the base (`integrate.IntegrationError`, `integrate._git`), so the red
leg loads and runs.

| Test | Criterion |
|---|---|
| `test_untracked_regate_output_does_not_block_the_next_fold` | (1) |
| `test_modified_tracked_file_does_not_block_the_next_fold` | (2) |
| `test_failed_abort_resets_the_tree_and_the_carry_goes_on` | (3) |
| `test_failed_abort_and_failed_reset_stops_the_fold` | (3), "only if that reset also fails" |
| `test_fold_starts_clean_from_a_tree_left_mid_merge` | (4) |
| `test_ignored_build_cache_is_kept` | Invariant, no `-x` (a guard: green before and after) |

## Refuting my own test

- **(a) Genuine red? Yes.** I ran the project's C4 gate on the final patch
  (`PDCA_BUNDLE=results/issue_631 PDCA_WORKTREE=<lane> ./engine/scripts/run-verify.sh`,
  from the instance root, under `timeout`). It reverts only the production hunks and keeps
  the test. Red leg: 5 of 6 tests fail, with the errors the brief predicts:
  - (1) and (2): `IntegrationError: could not merge issue_B's branch origin/fix/B onto
    pdca-integration/main — `git merge` exited 2 with no conflicting path …`
  - (4): `IntegrationError: could not start pdca-integration/main off <t1>`
  - (3): `'issue_B' unexpectedly found in` `skipped`, with "conflicts in a.txt", because the
    tree still holds X's conflicted merge
  - (3), reset-also-fails leg: `AssertionError: IntegrationError not raised`
  - `test_ignored_build_cache_is_kept` passes on both legs, as a guard should.

  Green leg: 6 of 6 pass. Gate output: `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it` (exit 0). Same result on two runs, before and after the test-docstring edit.
- **(b) Production path? Yes.** Every test calls the production `integrate.fold`, and the
  re-gate cases call the production `gates.run_integration` with a repo-scoped gate that
  writes into the fold's worktree. The only patch is a wrapper around `integrate._git` in
  the two (3) tests: it delegates to the real function and fails only `merge --abort` (and,
  in one test, `reset` after the first merge). Every other git call is real. C5 agrees:
  `PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package 'pdca_harness'`.
- **(c) Fixture includes the fault? Yes.** The leftover state is really in the tree before
  the next fold runs, and the tests assert it: the gate really writes `out/build.txt` /
  rewrites `a.txt` in the fold's worktree (`assertEqual(... "gate\n")`); (4) runs a real
  conflicting `git merge` in the worktree and asserts `MERGE_HEAD` exists. In (3), X's
  merge really conflicts and leaves `MERGE_HEAD`. One honest caveat on (3): after the fix
  the fold no longer calls `merge --abort`, so the patched abort failure only bites on the
  reverted code. The post-fix run still really goes through a mid-merge tree (X's conflict)
  and really resets it, and the reset-also-fails test drives the real new raise path.

## Other checks

- Full suites through the project's T3 runner (`./engine/scripts/run-suite.sh`, under
  `timeout`), with the patch applied: root suite `Ran 24 tests … OK`; driver suite
  (`template/tests`) `Ran 2375 tests … OK (skipped=2)`. That covers `test_integrate`,
  `test_integrate_stack_bases`, `test_regate`, and the flow tests that spy on
  `integrate._git` (e.g. `test_flow_slice.py:1591-1608`, which counts pushes only).
- Commit-readiness: the target has no pre-commit config, no `core.hooksPath`, no installed
  hooks (only `*.sample` in the hooks dir), and its CI runs no formatter or linter on Python
  (`.github/workflows/`: docs-check, docs, render-check, require-linked-issue). No `ruff`,
  `flake8` or `black` is installed here. `git diff --check` is clean, the test file ends
  with a newline, and every added line is under 100 characters, matching the file (the
  only 100-character lines in `integrate.py` are the existing `:111-112`).
- Conflict note for 633 (same per-bundle loop in `fold`): my change in that loop is one
  condition on the existing `raise` (post-patch `integrate.py:452`). The rest sits before
  the loop (`:441-445`) or in `_merge` / `_reset_tree` (`:598-630`).
- No external dependency beyond git and the stdlib, as the brief says. No NEEDS-HUMAN item.
