# Build notes — issue 673 / fold-stops-on-a-revert-brought-by-a-bundle-branch

Base: the worktree at `ebef78c` (`pdca-integrate: issue_693`, on top of `2be8a16` issue_672
and `d6057eb`), i.e. the wave-0 line with 672 already folded in, as the brief's ordering note
expects. Every `path:line` below is on the patched tree in `$PDCA_WORKTREE`; the brief's
`d6057eb` lines moved (672 added the `skipped` re-pass logic), so I re-located each one.

## What changed

- `template/src/pdca_harness/integrate.py:696` — `_merge_published`: on the `rc == 0`
  return of the bundle merge (the hook point the brief names), call the new `_keep_merge`.
  Docstring `:681-687` says what it does.
- `integrate.py:709-736` — new `_keep_merge`: mirrors `_take_in_base`'s base-merge judgment
  (`:827-843`). `before` is the merge commit's first parent (`HEAD^1`: `_merge` always uses
  `--no-ff`, `:1026`, so HEAD is a merge commit whose first parent is the tip before it). It
  calls `_undone_paths(..., head=head)`; on a git failure inside it, `_reset_line` then
  re-raise; on a hit, `_reset_line` and raise a plain `IntegrationError` with its own wording
  ("merging issue_B's branch … would remove issue_A's work … a.txt (issue_A) …"). Being a
  plain `IntegrationError` (not `_Conflict`, not `_LineBroken`) means: the in-run fold stops;
  under `skipped` only that bundle is recorded and dropped (`fold`, `:577-582`); `held_out`
  never absorbs it (it only takes `_Conflict`, `:570-571`). A failed reset is `_LineBroken`,
  so it stops even the carry, the same guarantee as #623.
- `integrate.py:849-858` — new `_removed`: the `whose/work/paths` text formerly inline in
  `_take_in_base`, pulled out so both refusals name paths the same way. `_take_in_base`'s
  message (`:837-843`) is byte-identical: same f-string, same inputs. The #623 tests asserting
  "taking origin/main in would remove" / "a.txt (issue_A) would go back" pass unchanged.
- `integrate.py:916-940` — new `_own_change`: which of the undone paths one of the branch's
  own commits changes itself.
- `integrate.py:943-976` — `_undone_paths` gets a keyword `head` (the merged branch tip).
  When given, after computing `undone` and `skip`, it removes every path that
  `_own_change(_own_commits(head, since, skip), undone)` reports. Base-merge callers pass
  nothing, so their behaviour is unchanged. The docstring states the gap-1 limit.
- Module docstring `integrate.py:50-56` and `fold` docstring `:358-362`: describe #673 and
  the accepted limit (gap 1).
- `docs/07-crosscutting.md:684-694` — user-facing text: the branch case, and the accepted
  limit (partial revert inside a file the line also changed; revert of work already on the
  base when the line started), next to the #623 paragraph.

## The "own commits" exemption — which rule (criterion 2b asks me to say)

**Rule: a commit changes a path of its own when its content there differs from what EVERY
one of its parents has** (root commit: from the empty tree). Not first-parent only.

Why not first-parent: I tried it (swapped `parents` for `parents[:1]` at `integrate.py:938`
and ran the new test). It fails
`test_a_branch_cut_from_the_line_then_updated_from_the_reverted_base_stops`. History: B is
cut from the line (so it has a.txt through A's commit), then main merges and reverts A, then
B gets "Update branch". That update merge's merge base is A's commit, so git takes main's
deletion. On B's first-parent chain the update merge *itself* deletes a.txt, so a
first-parent rule calls it B's own change, exempts it, and the fold silently pushes a line
without a.txt — the exact bug. With the every-parent rule, the update merge's a.txt equals its
second parent's (main, absent), so it is not B's own change and the fold stops. Criterion
(2b)'s own history (B cut from main before A) passes under either rule, because there the
update merge's first-parent diff does not touch a.txt; I added the second history to pin the
difference.

What still counts as own: a non-merge commit on the branch that edits/deletes the path
(criterion 3), a topic commit merged into the PR branch (it is in `_own_commits`, `:895-913`,
and is itself a non-merge commit), and a merge that resolves the path to content no parent
had (an "evil merge" / conflict resolution). A merge that simply takes the path from a base
parent does not count. Base commits are never visited at all: `_own_commits` stops at the
line's and the base's first-parent commits (`skip`).

## Cost of the check

Per bundle merge that succeeds: `_cut_point` (1-2 `git rev-list`) and two `git diff
--name-only`. When nothing on the line went back (the normal case) it returns there. Only
when some path went back does it run the extra `rev-list` for `skip`, one `rev-list
--no-walk --parents` for the own commits, and one path-limited `git diff` per own commit per
parent. A fresh line (`before` == base tip) returns after the first `rev-list`.

## What I ruled out

- **Checking only branches cut from the base / only file deletions**: the brief's
  invariant self-test rules these out. The check runs on every successful bundle merge and on
  any path whose content went back (edits back to old content included), via the shared
  `_undone_paths`.
- **A separate copy of the `_undone_paths` logic for branches**: would duplicate the cut
  point / owner attribution; the `head` keyword adds 6 lines (`:969-974`) instead.
- **Reading `before` via `_rev(wt, "HEAD")` before `_merge`**: works too, but `HEAD^1` after
  the merge is the same commit with no change to the `_merge` call site.
- **Original refusal advice "merge the line into fix/B"**: I first wrote that, then checked
  it is wrong — merging the line into B has merge base A's commit again, so git keeps the
  deletion. Replaced with "put the work back on fix/B (say, revert the revert there), or get
  it back into origin/main". I verified by script that after `git revert <R>` on fix/B the
  fold merges B and pushes a line with both a.txt and b.txt.

## Tests

`template/tests/test_integrate_revert_via_branch.py` (copy in the bundle dir). Loads
`test_integrate_stack_bases.py` by path and uses `StackFoldGit` as a helper object (setUp /
tearDown by hand, `addCleanup`), never subclassed. Imports only `pdca_harness.integrate`.

| Test | Criterion | Pre-fix | Post-fix |
|---|---|---|---|
| `test_a_branch_cut_from_a_base_that_reverted_line_work_stops_the_fold` | (1) | FAIL (no raise; line pushed without a.txt) | pass |
| `test_the_carry_skips_only_the_branch_that_brings_the_revert` | (2), with D | FAIL (`skipped == {}`) | pass |
| `test_a_branch_updated_from_a_base_that_reverted_line_work_stops_the_fold` | (2b) | FAIL | pass |
| `test_a_branch_cut_from_the_line_then_updated_from_the_reverted_base_stops` | (2b), first-parent trap | FAIL | pass |
| `test_a_dependent_that_deletes_the_file_itself_is_merged` | (3) delete | pass | pass |
| `test_a_dependent_that_edits_the_file_is_merged` | (3) edit | pass | pass |

The two (3) tests are guards against false stops: green before and after by design.
Criterion (4): full offline suite `cd template && PYTHONPATH=src python3 -m unittest discover
-s tests` → `Ran 2482 tests … OK (skipped=2)`, which includes
`test_integrate_stack_bases.py` (#623 / #633 cases), `test_flow_same_wave_conflict.py` and
`test_flow_resume_stack_prereqs.py`.

Runner: the project's own command from `CONTRIBUTING.md:26` (what `engine/scripts/run-suite.sh`
runs for the driver suite), wrapped in `timeout`.

## Refuting my own test

- **(a) Genuine red? Yes.** I reverted only `integrate.py` (`git checkout --`), kept the
  test, and ran it: `Ran 6 tests … FAILED (failures=4)` — the four refusal tests (1), (2),
  (2b), (2b-trap). Reapplied the fix: `OK`. Separately, the first-parent-only variant fails
  exactly the (2b-trap) test, so that test binds the rule choice.
- **(b) Production path? Yes.** Each test calls `integrate.fold` directly against real git
  (bare origin, primary checkout, human clone); nothing in `integrate` is mocked or patched.
  The new code runs from `fold` → `_merge_published` → `_keep_merge` → `_undone_paths`.
- **(c) Fixture includes the fault? Yes.** The revert really happens on origin's `main`
  (`_merge_pr("A")` + `_revert_on_main("-m", "1", "HEAD")`), B's branch really is cut from
  (or updated from, via `_update_branch`) that reverted main, and A's branch is kept, as the
  brief describes. Each refusal test also asserts origin's line still at T1 and still holding
  a.txt; the carry test asserts the revert commit is not an ancestor of the pushed tip.

## Commit-readiness

The target has no Python formatter/linter configured (no ruff/flake8/black config, no
pre-commit config, no installed git hooks in the common git dir). Checked: `git diff --check`
clean, no line over 100 chars in the touched Python (the file's existing width), `python3 -m
py_compile` clean, `docs/publishing/tools/lint_docs.py` → `lint_docs: OK` (the target's
docs-check workflow linter). I did not run `render_site.py --check`; the docs edit adds
prose only, no links.

## Housekeeping

I left a stray working file `results/issue_673/.prod-only.diff` (the production-only hunks,
used to re-apply the fix after the red run). It is not one of the three artifacts and can be
ignored; I did not delete it (cleanup is the harness's job).
