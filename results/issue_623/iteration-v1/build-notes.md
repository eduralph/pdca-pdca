# Build notes — issue 623 / fold-refuses-base-that-reverts-line-work

Target: eduralph/pdca-harness @ main (`b5f5c29`), worktree `pdca-harness.pdca-wt-l1`.
Line numbers below are on the patched tree unless marked "base".

## What changed

- `template/src/pdca_harness/integrate.py`
  - `:563-611` `_take_in_base` — records the line tip (`before`) before the base merge.
    After a clean merge it calls `_undone_paths`. If any path was undone, it resets the
    worktree to `before` (`_reset_line`) and raises `IntegrationError` naming the bundles,
    the paths, `origin/main` and the line. The "reaches … through" line is printed only
    when no refusal happened, so it is true whenever it is printed. The reset lives here,
    not in `_merge` (base `:583-595`), as the brief asked (631 edits `_merge`).
  - `:624-631` `_cut_point` — `git rev-list --first-parent --topo-order <before> --not
    <base_ref>`; the cut point is the first parent of the last commit listed (or `before`
    itself if the list is empty). This is "the first first-parent commit the base already
    has", decided by commit. A chain that never meets the base gives None → the empty tree.
  - `:633-638` `_changed` — `git diff --no-renames --name-only -z`.
  - `:640-672` `_undone_paths` — the detection rule from the brief: paths that differ
    between cut and `before` but no longer differ between cut and `HEAD` (after the merge).
    New content (criterion 5) still differs from the cut, so it is not flagged.
  - `:675-680` `_reset_line` + `:71-73` `_LineBroken` — if the reset itself fails, the
    error is a subclass that `fold` re-raises even under `skipped` (`:450`). Without this,
    a failed reset in carry mode would leave the revert in the worktree and the fold would
    merge the next bundle on it and push. Cost: 3-line class + one `isinstance` check.
  - `:441-447` `fold` builds `owners` (this fold's bundles, then `cfg.bundle(n)` for each
    batch name, `issue_` prefix stripped as `batch_key` does at base `:94`) and passes it
    through `_merge_published` (`:475`, `:484`) and `_gone_branch` (`:503`, `:551`). All
    new params default to `()`, so no other caller changes (none exist outside the module).
  - Docstrings: module (`:45-46`), `fold` (`:324-326`), `_gone_branch` (`:517-518`).
- `docs/07-crosscutting.md:671-674` — one added sentence after "the run stops rather than
  build the next wave without that work". Touches only the lines between 633's
  (`:665-666`) and 629's (base `:672-673`) sentences; 629's line shifts down by 3.

## Attribution: one refinement of the brief's rule (flag for the human)

The brief says: name a bundle "whose commits in `C..<its head>` touched the path". Taken
literally this over-names: in the repro, B is cut from `origin/main`, which contains A's
merge, so A's commit `a1` is in `C..B`. I narrowed it to the bundle's **first-parent
chain** since the cut point (`rev-list --first-parent <head> --not <cut>`), intersected
with the line's own commits that touched the path (`rev-list <before> --not <cut> --
<path>`). A fixup or "Update branch" merge on a PR branch keeps the branch on the first
parent, so a bundle's own commits stay on that chain; another bundle's work arrives through
a second parent and is not counted. Still decided by commit, never by message. The bundle
head is its published branch tip, or `merged.merged_head` when the branch is gone (only
called in the refusal path, so no extra host calls on a normal fold). When no bundle
matches, the message names the path and the last line commit that changed it, as the
brief asks.

## Test change I had to make (and why it is not a weakening)

Criterion (4) failed at first with B published off `origin/main` (the default of
`_publish`). Cause: B's branch was cut from main *after* the revert, so B's own branch
carries the revert, and merging B brings it to the line. That is a different defect (a
bundle's own branch undoing another bundle — out of this brief's scope; close to #633's
territory). In the flow a later-wave bundle is cut from the line, so the test publishes B
with `cut_from=f"origin/{LINE}"` (`test_integrate_stack_bases.py:521-523`, with a comment).
Criteria (1) and (2) keep the brief's default publish; the fold refuses at A before B is
merged, so it does not matter there.

Worth a human look: a bundle whose own PR branch carries a base revert still drops the
other bundle's work on merge. This patch does not cover that path (`_merge_published`
merging a live branch never takes the base in, so it is not "the base merge").

## Tests (appended to `StackFoldGit`, `template/tests/test_integrate_stack_bases.py`)

- `:451` `_revert_on_main`, `:460` `_fixup_merged_then_reverted` (the brief's repro).
- `:473` criterion (1), `:489` criterion (2) (batch `["Z","A","B"]`, line from
  `integration_branch`), `:516` criterion (4) (`skipped={}`), `:535` criterion (5).
- Criterion (3): the existing `test_a_merged_branch_the_line_never_carried_comes_in_through_the_base`
  and every other case in the file still pass.

## Runs (project runner, not hand-rolled)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `C4 PASS`.
  Green leg: 50 tests OK. Red leg (production hunks reverted, tests kept): exactly 3
  failures — (1) and (2) `IntegrationError not raised`, (4) `Lists differ: [] !=
  ['issue_A']`. (5) and all old cases stay green on both legs.
- T3: `./engine/scripts/run-suite.sh` → root suite 24 OK, driver suite 2373 OK (2 skipped).
- T2: `./engine/scripts/run-docs-check.sh` → lint_docs OK, render + link audit OK.
- Commit hooks: the target has no `.pre-commit-config.yaml` and no ruff/flake8 config, and
  no tool installed here; I checked no changed line exceeds 100 columns (the file's
  existing width). Nothing else to run.

## Self-refutation

- **(a) Genuine red?** Yes. The C4 script reverted the production hunks of `patch.diff`
  in the worktree and re-ran the file: (1), (2), (4) failed on their assertions (not on
  import — the test imports only modules, no new symbols). Output above.
- **(b) Production path?** Yes. Every test calls the real `integrate.fold` against real
  git (bare origin, real merges, real `git revert -m 1` / `git revert`, real branch
  deletion). The only patch is the host answer (`merged.merged_head` via the existing
  `_merged_heads` helper), which is the GitHub API, not the code under change.
- **(c) Fixture includes the fault?** Yes. The revert commit is actually pushed to
  origin's `main`, and the fold actually fetches and merges that `main`. (4) asserts the
  revert commit is not an ancestor of the pushed tip; (1)/(2) assert origin's line is still
  at `t1`.

## Ruled out

- Checking only the merged head's files (`git diff <cut> <head>`) instead of the whole
  line: would miss criterion (2) (Z's revert while A is the gone bundle). The brief defines
  "A's work" as everything the line has from A, so the check spans all line paths.
- Detecting reverts by commit message ("Revert …"): forbidden by the brief and easy to
  dodge (a hand-written undo).
- Putting the reset in `_merge`: conflicts with 631 in the same wave (brief).
