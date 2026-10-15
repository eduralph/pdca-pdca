# Build notes — issue 673 / fold-stops-on-a-revert-brought-by-a-bundle-branch (iteration 2)

Base: the worktree at `ebef78c` (`pdca-integrate: issue_693`, on top of `2be8a16` issue_672
and `d6057eb`), the wave-0 line with 672 folded in, as the brief's ordering note expects.
Every `path:line` below is on the patched tree in `$PDCA_WORKTREE` unless it says "base".
The brief's `d6057eb` line numbers moved (672 added the `skipped` re-pass), so I re-located
each one: the bundle merge's `rc == 0` return is base `integrate.py:681-682`, `_take_in_base`
base `:755`, `_undone_paths` base `:860`, `_reset_line` base `:897-902`.

## What the carry-forward asked, and what changed

1. **C5: the own-change exemption was too wide.** Iteration 1 exempted a path when ANY of
   the branch's own commits had ever changed it (`_own_change`, iteration-1
   `integrate.py:916-940`). The reviewer's two histories (B cut from `fix/A`, and B that
   edits `a.txt` then puts it back, each then updated from the reverted `main`) still pushed
   a line without `a.txt`. Fixed by judging the commit that actually made the removal (below).
   Both histories are now tests, each covering the in-run stop AND the carry skip.
2. **`_reset_line` wording blamed the base for a bundle-branch refusal.** It now takes what
   is being undone (`merged_in`, `integrate.py:1000-1007`): "could not reset <line> … to
   undo the merge of origin/main" from `_take_in_base` (`:835`, `:838`), and "… to undo the
   merge of issue_B's branch origin/fix/B" from `_keep_merge` (`:729`, `:733`). The prefix
   "could not reset <line>" that `test_integrate_stack_bases.py:622` asserts is unchanged.
   Pinned by a new test (see the table).

## The own-change rule (criterion 2b asks me to say which)

**Rule: a removal is the branch's own change only when the commit that gave the branch tip
its content at that path is one of the branch's own commits that the merge brings.**
`_own_removals`, `integrate.py:919-944`:

- "The commit that gave the tip its content" = `git rev-list -n 1 <head> -- <path>`
  (`:940`), git's default history simplification. At a merge that took the path from one
  parent (the path is the same there), git follows that parent only. So an "Update branch"
  merge that took `main`'s deletion is never the answer; the walk goes past it to `main`'s
  revert commit. A merge that resolves the path to content no parent had is the answer
  itself. If no commit changed the path on the followed history, the answer is empty, and
  that is "not own".
- "The branch's own commits that the merge brings" = `_own_commits(head, --not before, skip)`
  (`:936`): commits reachable from the tip, not already on the line (`--not before`), walked
  without crossing the line's or the base's first-parent chain (`skip`, built at `:973-974`).
  Topic branches merged into the PR branch count as its own (that is how `_own_commits`
  already worked for #623).

This is "an equivalent rule" in the brief's words, not first-parent. I checked first-parent
by swapping in `git rev-list --first-parent -n 1` at runtime (no file edit): it fails 3 tests,
including `test_a_branch_cut_from_the_line_then_updated_from_the_reverted_base_stops`. There
the update merge's merge base is A's commit, so on fix/B's first-parent chain the update
merge itself deletes `a.txt` and passes for B's own deletion.

Probe of what git names for each history (run with the project's fixture before writing the
code; the fixture cleans up after itself):

| History | Commit git names for `a.txt` at B's tip | Own? | Result |
|---|---|---|---|
| (1) B cut from reverted main | main's revert | no (on main's first-parent chain) | stop |
| (2b) B cut before, then "Update branch" | none (B's first-parent side never had a.txt) | no | stop |
| B cut from line, then "Update branch" | main's revert (update merge took main's side) | no | stop |
| Reviewer 1: B cut from fix/A, updated | main's revert | no | stop |
| Reviewer 2: B edits + restores a.txt, updated | main's revert | no | stop |
| GitHub "Revert" button (revert PR merged into main), B cut from main | the revert commit on the side branch | no: B's walk stops at main's merge commit | stop |
| (3) C cut from line, deletes a.txt | C's deleting commit | yes | merged |
| C deletes a.txt, then updated from reverted main | C's deleting commit (both parents agree; git takes the first, C's side) | yes | merged |

### Rules I rejected, with the evidence

Each was swapped in for `_own_removals` at runtime and the new test module run against it:

| Rule | Failing tests |
|---|---|
| Iteration 1: any own commit that ever changed the path | `…cut_from_another_bundles_branch_then_updated_stops`, `…edited_the_file_and_put_it_back_still_brings_the_revert` (the reviewer's two histories) |
| First-parent introducer | the two above + `…cut_from_the_line_then_updated_from_the_reverted_base_stops` |
| Introducer counts as own when it is not on the line and not on main's first-parent chain | `…revert_merged_through_a_revert_pr_is_the_bases_not_the_branchs` (GitHub's Revert button puts the revert on a side branch) |

**Introducer counts as own only when not reachable from the base at all** (stricter than
mine). Not chosen. It passes every test, but it stops falsely in one history: C is cut from
`fix/A` (not the line), C's own commit deletes `a.txt`, and C's PR merges into `main` before
any fold carried C. C's deleting commit is then reachable from `main`, so it would count as
the base's. The code size is the same as mine: one `git merge-base --is-ancestor` per path
in place of the `_own_commits` walk, about 4 changed lines. The choice is about behaviour,
not cost. A false stop fails safe, so no test pins this. I did not add the history as a
test: it needs C cut from another bundle's branch and merged before its first fold, which
is rare.

**Net-change rule** (follow the branch's own changes back to where the branch picked the
content up, and exempt only when that content differs). Not chosen. The one case where it
differs from mine: B is cut from the reverted main (no `a.txt`), B's own commit re-adds
`a.txt`, and a later own commit deletes it again. My rule calls that B's change, because B's
own commit made the deletion. The net-change rule calls it the base's, because B's commits
cancel out. The invariant says "work a merged branch adds as its own commits is that
bundle's change", and a deletion by B's own commit fits that. Cost: a recursive walk with
one blob lookup per parent per commit visited, roughly 20-25 more lines than `_own_removals`
plus more git calls. I judged that not worth it for a history I could not motivate.

## Attribution: who the refusal names (`_undone_paths`, `integrate.py:980-990`)

With the rule fixed, the reviewer's first history (B cut from `fix/A`) stopped correctly,
but the message read "merging issue_B's branch … would remove issue_A, issue_B's work …
a.txt (issue_A, issue_B)": B's merge claimed to remove B's own work. The cause was in the
#623 attribution. `_own_commits` walked from B's tip through A's commit, because A's commit
is on neither the line's nor main's first-parent chain, so A's commit counted as B's too.
Fix: each bundle's walk also stops at every OTHER bundle's tip (`:988`, skipping a tip equal
to its own, so two records of one branch still both get named). A branch cut from another
bundle's branch holds that bundle's commits, which are not its work. This is the reason
`_own_commits` already gives for the line and the base (`:898-905`).

This also changes naming for the base merge, but only in histories where one bundle's branch
contains another bundle's branch tip. No existing test has that shape. The #623 assertions
(`test_integrate_stack_bases.py:523-524`, `:540`, `:555-556`, `:570`, `:583`, `:597`) all
pass. The base-merge message text is not reworded: `_take_in_base` (`:840-846`) uses the same
f-string with the same `work`/`paths`, now built by the shared `_removed` (`:852-861`, moved
verbatim from base `:789-792`).

## Other changes

- `_merge_published` (`integrate.py:692-700`): reads the line tip before the merge, as the
  peer `_take_in_base` does (`:819`), and calls `_keep_merge` on the `rc == 0` return.
  Iteration 1 read `HEAD^1` after the merge, which is right only while `_merge` uses
  `--no-ff` (`:1035`). Reading the tip first does not depend on that. Cost: one more
  `git rev-parse` per bundle merge. An unreadable tip raises `IntegrationTreeError`, the same
  type `_merge` raises in that case (`:1031-1034`), so `skipped` still never absorbs it.
- `_keep_merge` (`integrate.py:712-741`): the bundle-branch counterpart of `_take_in_base`'s
  check. It raises a plain `IntegrationError` with its own wording ("merging issue_B's
  branch origin/fix/B would remove issue_A's work …", never "taking origin/main in"). So the
  in-run fold stops; under `skipped` only that bundle is recorded and dropped (`fold`,
  `:577-582`); `held_out` never takes it, because it only takes `_Conflict` (`:570-571`). A
  failed reset is `_LineBroken`, which stops even the carry. The advice in the message ("revert
  the revert there, or update it from origin/main once origin/main has the work again") is
  right for all the refusal histories. Updating B from a main that reverted the revert gives
  a 3-way merge with base = the revert, so `a.txt` comes back.
- `_undone_paths` (`integrate.py:947-997`): keyword `head` (`:975-979`). Base-merge callers
  pass nothing, so their behaviour is unchanged apart from the attribution fix above. The
  docstring states the gap-1 limit.
- Docs: module docstring `integrate.py:51-57`, `fold` docstring `:360-363`, and
  `docs/07-crosscutting.md:684-694` (the user-facing text: the branch case, the carry, the
  own-change rule, and the accepted gap-1 limit, next to the #623 paragraph).

## Tests

`template/tests/test_integrate_revert_via_branch.py` (copy in the bundle dir). It loads
`test_integrate_stack_bases.py` by path and uses `StackFoldGit` as a helper object (setUp /
tearDown by hand, `addCleanup`), never subclassed. It imports only `pdca_harness.integrate`
(plus `unittest.mock` for the one fault-injection test).

| Test (line) | Covers | Pre-fix | Post-fix |
|---|---|---|---|
| `…cut_from_a_base_that_reverted_line_work_stops_the_fold` (`:156`) | (1) | FAIL: not raised | pass |
| `…carry_skips_only_the_branch_that_brings_the_revert` (`:167`) | (2) with D | FAIL: `skipped == {}` | pass |
| `…updated_from_a_base_that_reverted_line_work_stops_the_fold` (`:178`) | (2b) | FAIL | pass |
| `…cut_from_the_line_then_updated_from_the_reverted_base_stops` (`:189`) | (2b) first-parent trap; stop + carry | FAIL | pass |
| `…cut_from_another_bundles_branch_then_updated_stops` (`:203`) | reviewer history 1; stop + carry | FAIL | pass |
| `…edited_the_file_and_put_it_back_still_brings_the_revert` (`:214`) | reviewer history 2; stop + carry | FAIL | pass |
| `…revert_merged_through_a_revert_pr_is_the_bases_not_the_branchs` (`:228`) | GitHub Revert button; stop + carry | FAIL | pass |
| `…dependent_that_deletes_the_file_itself_is_merged` (`:240`) | (3) delete | pass | pass |
| `…dependent_that_edits_the_file_is_merged` (`:249`) | (3) edit; now also checks the push and that fix/C is on the line | pass | pass |
| `…dependent_deleting_the_file_then_updated_from_the_reverted_base_is_merged` (`:256`) | own deletion survives "Update branch" | pass | pass |
| `…line_that_will_not_go_back_after_refusing_a_branch_stops_even_the_carry` (`:272`) | `_LineBroken` for the new refusal + the reworded reset message | FAIL: not raised | pass |

The three "is merged" tests guard against false stops, so they pass before and after by
design. Every refusal assertion checks the line on origin is still at T1. Every carry
assertion checks `list(skipped) == ["issue_B"]`, `a.txt` and `d.txt` on the tip, `b.txt` not
on it, T1 an ancestor, and the revert not an ancestor.

Criterion (4): `test_integrate_stack_bases`, `test_flow_same_wave_conflict`,
`test_flow_resume_stack_prereqs` and the new module, run together: `Ran 108 tests … OK`.
Full suite through the project's T3 runner (`engine/scripts/run-suite.sh`): see "Runs" below.

## Runs (the project's runners)

- C4: `engine/scripts/run-verify.sh` with `PDCA_BUNDLE`/`PDCA_WORKTREE` set, wrapped in
  `timeout`, run on the final `patch.diff`. Green leg `Ran 11 tests … OK`; red leg
  (production hunks reverted, test kept) `Ran 11 tests … FAILED (failures=8)`;
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Afterwards the worktree
  matched `patch.diff` byte for byte.
- T3: `engine/scripts/run-suite.sh` (root render/update-compat suite with copier from the
  instance venv, then the offline driver suite), wrapped in `timeout`: root `Ran 24 tests …
  OK` (the copier cases ran, not skipped), driver `Ran 2487 tests … OK (skipped=2)`,
  `PDCA-EVIDENCE: root suite OK, driver suite OK`. 2487 = the base's 2476 + the 11 new.
  The only change after this run was the `_own_removals` docstring.

## Refuting my own test

- **(a) Genuine red? Yes.** `run-verify.sh` reverted only the production hunks
  (`integrate.py`; docs and tests excluded) and ran the module: 8 of 11 failed, all on
  assertions (`IntegrationError not raised`; `[] != ['issue_B']`). Separately, swapping each
  rejected rule into `_own_removals` makes specific tests fail (table above), so the tests
  pin the rule choice, not only "some check exists".
- **(b) Production path? Yes.** Each test calls `integrate.fold` against real git: a bare
  origin, the primary checkout and a `human` clone. Nothing in `integrate` is replaced,
  except in the one fault-injection test. That test wraps `integrate._git` so that only the
  `reset` back to the line's tip fails; every other git call runs for real. The new code runs
  `fold` → `_merge_published` → `_keep_merge` → `_undone_paths` → `_own_removals`.
- **(c) Fixture includes the fault? Yes.** The revert really happens on origin's `main`
  (`_merge_pr("A")` + `_revert_on_main("-m", "1", "HEAD")`, or the revert PR merged with a
  merge commit). B's branch really is cut from, or updated from (`_update_branch`), that
  reverted `main`, and A's branch is kept, as the brief describes. The reviewer's histories
  are built the way the review describes them: B cut from `origin/fix/A`, and B with two own
  commits that edit and restore `a.txt`.

## Commit-readiness

The target has no Python formatter or linter configured: no pre-commit config, no
ruff/flake8/black config, and no hooks in the common git dir. Its CI runs `docs-check.yml`
(`lint_docs.py`, `render_site.py --check`) and `render-check.yml` (the root suite). I ran:
`git diff --check` (clean, the new file included), `python3 -m py_compile` on both Python files
(OK), `docs/publishing/tools/lint_docs.py` (`lint_docs: OK`), and `render_site.py --check`
with the instance venv (`22 page(s)`, `link audit OK`). Line widths follow the file's own
(it already has lines up to 99 characters; the longest new line is 94). DCO sign-off is
added by publish when it commits.

## Housekeeping

Working files I left (cleanup is the harness's): `results/issue_673/.do-suite.log` (the T3
runner's output) and `.cache/site-check-673/` in the worktree (render output; `.cache/` is
git-ignored). The iteration-1 stray `results/issue_673/.prod-only.diff` is still there too.
None of them is an artifact.
