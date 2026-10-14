# Build notes — issue 633 / fold-refuses-a-rewritten-carried-branch

Target: `eduralph/pdca-harness` `main` @ `b5f5c29`, worktree `pdca-harness.pdca-wt-l0`.
Line numbers below are post-patch in that worktree unless marked "base".

## What changed

### `template/src/pdca_harness/integrate.py`

- **New `carried` parameter on `fold`** (`integrate.py:281`), a `dict[str, str] | None`
  filled in place, the same pattern as `skipped` (base `:275`, `:433-439`). Docstring
  paragraph at `:349-357`.
- **Up-front check before any merge or push** (`:388-402`). After the `refs` resolution
  and grouping (base `:347-369`), when `carried` is non-empty and this is not a dry-run:
  for each target group that has a bundle with a recorded head, fetch the checkout once
  (`_fetch`, the same fetch a fold already does) and call `_refuse_rewritten` for each such
  bundle. It runs before the group loop, so with several targets no target pushes before a
  rewrite on any target is caught. It sits outside the per-bundle `skipped` try/except
  (`:466-473`), as the brief asks.
- **No second fetch.** A target fetched by that pass is not fetched again:
  `_prepare_worktree(..., fetch=(repo_spec, base) not in fetched)` (`:447-449`). New
  keyword `fetch: bool = True` on `_prepare_worktree` (`:680-689`). A fold with no carried
  heads still fetches exactly where it did before, inside the lock.
- **`_refuse_rewritten`** (`:498-518`): resolves the branch tip with `_rev`; returns when the
  branch is gone (left to `_gone_branch`, criterion 3), when the tip is the recorded head, or
  when the recorded head is an ancestor of the tip, via `_in_line(..., of=tip)`. That keeps
  the fail-closed rule of base `:569-580`: exit code 128 raises and is never read as "no".
  Otherwise it raises `IntegrationError`. The message names the bundle, the ref, the word
  "rewritten", the likely causes (re-publish / force-push / "Update with rebase"), says
  only fast-forward updates are carried, says nothing was merged or pushed, and gives two
  fixes: restore the branch to a descendant of the head, or let the run stop and re-issue
  it. Nothing reads a commit message.
- **Recording.** `_merge_published` now returns the head it merged or found already in the
  line, or `None` for a gone branch (`:520-537`). The fold collects these per target in
  `took` (`:465-470`) and copies them into `carried` only **after the push succeeds**
  (`:492-493`). So a failed fold records nothing, and a bundle the carry skipped is never
  recorded.
- Docstrings: the module paragraph at base `:39-40` now says fixups reach the line only
  when they extend the branch, and that a rewrite is refused (`:39-45`). The `fold`
  docstring sentence at base `:310-311` says the same (`:316-318`).

### `template/src/pdca_harness/flow.py`

- `_fold_lines` takes `carried` and passes it on to `integrate.fold` (`flow.py:796`,
  docstring `:805-808`, call `:815-816`).
- `_drive_and_act` creates one `carried_heads: dict[str, str] = {}` per run, next to
  `folded_tips` (`flow.py:2101-2103`), and passes it to the in-run fold (`:2304-2307`).
- The #646 pre-wave carry call (`flow.py:937-939`, base `:931-933`) is **not** touched, so
  it passes no mapping and never checks (criterion 2b). I did not touch `_runnable`, the
  announcement near base `:2289-2291`, or `_carry_finished`, per the ordering note.

### `docs/07-crosscutting.md:666-671`

The sentence at base `:665-666` now says only fast-forward commits reach the line, a
rewrite stops the run, and what to do about it. `lint_docs.py` reports OK.

## Tests (`template/tests/test_integrate_stack_bases.py`, appended to `StackFoldGit`)

- `_carried_kw` (`:371-376`) passes `carried=` only when `fold` accepts it. This is the
  same `inspect.signature` approach the file already uses for `batch` (`:860-866`). So the
  red leg fails the way the bug does, not on a `TypeError`.
- `test_a_carried_branch_rewritten_mid_run_stops_the_fold` (`:390`): criterion (1). A
  non-conflicting rewrite (`a2.txt`) using the brief's exact sequence. Asserts
  `IntegrationError` with `issue_A`, `fix/A`, `rewritten`, `Restore`, `re-issue`; no
  `git merge` / `git push` ran (spy on `integrate._git`); origin's line still at `t1`.
  Both folds share one `carried` dict.
- `test_a_conflicting_rewrite_is_named_a_rewrite_not_an_overlap` (`:412`): criterion (1b).
  The rewrite edits `a.txt`. The message has `rewritten` and not `cross-wave overlap`.
- `test_a_fast_forward_of_a_carried_branch_is_still_merged` (`:423`): criterion (2) with
  the mapping on. The fixup is merged, the recorded heads move to the new tips, and a third
  no-op fold passes the check.
- `test_a_carry_fold_with_no_carried_mapping_is_unchanged` (`:444`): criterion (2b).
  `skipped={}`, no `carried`, a rewritten branch: the fold merges as before and `skipped`
  stays empty.
- `test_a_carried_branch_gone_after_its_merge_is_left_to_the_gone_branch_rule` (`:454`):
  criterion (3) with the mapping on. A merged and deleted branch still goes through
  `_gone_branch`.
- `test_the_flow_passes_one_carried_mapping_to_every_in_run_fold` (`:470`): the flow
  plumbing. A 3-wave dry-run flow (Z1 ← Z2 ← Z3) gives two in-run folds. Each must get a
  dict, and it must be the same object both times.

## Red → green (project runner: `engine/scripts/run-verify.sh`, the C4 gate)

Run from the instance root with `PDCA_BUNDLE` set and `PDCA_WORKTREE` = this worktree:

- Green leg: `Ran 52 tests … OK`.
- Red leg (production hunks reverted, test kept): `Ran 52 tests … FAILED (failures=3)`.
  The failures are exactly the three new tests that pin the defect:
  - rewritten → `AssertionError: IntegrationError not raised` (the silent merge);
  - conflicting rewrite → the message was the old "…conflicts in a.txt) — an undeclared
    cross-wave overlap…", the misattribution the brief describes;
  - flow plumbing → `None is not an instance of dict`.
- Script result: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
- Also ran every `template/tests/test_{flow,integrate,carry,stack,wave}*` module with the
  patch applied: `Ran 370 tests … OK`.

The other three new tests (fast-forward, 2b, gone-branch) pass pre-fix too. That is
correct: they pin behaviour that must not change.

## Self-refutation

- **(a) Genuine red? Yes.** The C4 script reverted the production hunks (integrate.py,
  flow.py) and re-ran the file. The three defect tests failed on assertions, with no
  `_FailedTest` load error and no `TypeError`. That is the bug's own behaviour: a silent
  merge, and a rewrite blamed on an overlap.
- **(b) Production path? Yes.** The tests call the real `integrate.fold` and the real
  `flow.flow_ids`. Only `merged.merged_head` (the host lookup, as in the existing
  gone-branch tests) is patched, and `_git` is wrapped by a spy that calls the real
  function.
- **(c) Fixture includes the fault? Yes.** `fix/A` is really force-pushed on the bare
  origin, from a commit cut off `origin/main` that does not contain the folded head
  (asserted: `assertFalse(self._ancestor(t1, rebuilt))`). That is what `publish`'s
  `--force-with-lease` re-publish does (base `publish.py:312-319`). Both the
  non-conflicting and the conflicting rewrite are covered.

## Choices and what I ruled out

- **Where the check runs.** I could have put it only inside the group loop, after
  `_prepare_worktree`, with no extra fetch. That works for one target. With two targets,
  an earlier target would already have merged and pushed before a later target's rewrite
  was seen, which breaks "stops the fold before anything is pushed". The up-front pass
  costs one `_fetch` per target that has carried heads. With `fetch=False` that fetch
  replaces the one `_prepare_worktree` would have done, so there is no extra network
  traffic. Cost: 15 lines (`:388-402`) plus 3 in `_prepare_worktree`.
- **The fetch now runs before the integ lock** for targets with carried heads. The lock
  guards the worktree's lifecycle (`integ_lock` docstring), not the primary checkout's
  refs, and `carry_view` (base `:185-193`) already fetches without the lock. The
  base-fetched-last order inside `_fetch`, which `_gone_branch` relies on, is unchanged.
- **Recording inside `_merge_published`** instead of returning the head: rejected. It would
  record before the push, so a fold that failed at push would leave heads the line never
  got.
- **Re-checking inside the loop** to close the gap between the up-front fetch and the
  merge: not needed. The loop no longer re-fetches for those targets, so it merges the same
  ref snapshot that was checked.
- **A carried head missing from the clone** makes `merge-base --is-ancestor` exit 128,
  which raises "could not tell whether …". That is fail-closed, as the brief asks. It
  cannot really happen, because the head is on the fetched `origin/<line>`.

## Commit-readiness

The target has no formatter or pre-commit hooks configured: no `.pre-commit-config.yaml`,
and no ruff/black config in `pyproject.toml`. CI lints only docs
(`.github/workflows/docs-check.yml:33`), and `python3 docs/publishing/tools/lint_docs.py`
reports `lint_docs: OK`. New lines stay within the file's existing width (no new line over
99 characters).

## Conflicts to expect

The brief lists 623 and 631. My hunks are in `fold`'s pre-loop section, the merge loop,
`_merge_published`'s returns, `_prepare_worktree`, and the docs paragraph at
`07-crosscutting.md:666`. These will need a textual rebase onto whatever 623 and 631 land.
No logic depends on them.
