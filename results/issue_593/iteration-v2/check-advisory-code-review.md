# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lenses: correctness bugs the patch adds; reuse / simplification / efficiency.
Grounded on the patched tree at `$PDCA_TARGET`. Gates: C4 and T3 pass (gate-logs). I found
no blocking correctness bug. The new code does what the brief's (i)–(vii) ask: the
fresh/continue/auto start choice, the tip-mismatch refusal, no `--force` on a continuing
push, the pruning fetch of every remote a record names, merge-abort on conflict, and the
`_runnable` hold that cascades. Findings, most important first:

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:120-126` (`unpublished`) and
  `integrate.py:99-117` (`_published_ref`) decide "published" from whether a `publish.json`
  with a `branch` is on disk, not from whether publish worked **this run**. If a bundle was
  published in an earlier run and is driven again (re-opened / iterated), and this run's
  publish fails (`flow.py:651-653`) or its texts fail draft/T4 (`flow.py:1817-1822`), the old
  `publish.json` stays. The bundle is then not held. The fold merges the old PR branch (old
  content) and its dependents build on it. The brief's (iv) means "publish failed this run",
  so this is a missed case. A simple fix: have the flow add a bundle to `unpublished` when
  its publish rc is non-zero or its texts were not ready, on top of the `publish.json` check.
- `template/src/pdca_harness/integrate.py:244-259` (the `refs` / `missing` loop in `fold`)
  does the same work as `unpublished()` at `integrate.py:120-126`, plus a dry-run fallback.
  Both call `_published_ref` for each targeted bundle. Small cleanup, not a bug: have
  `unpublished()` drive the outside-dry-run error, or move the ref resolution (with the
  `_branch_name` fallback) into one helper that both use, so the definition of
  "unpublished" can't drift between flow and fold.
- `template/src/pdca_harness/integrate.py:364` — `git merge-base --is-ancestor` returns 1
  for "not an ancestor" and 128 for an error. The code treats both as "go ahead and merge".
  An error then shows up as a misleading "does not merge cleanly … undeclared cross-wave
  overlap" message (`integrate.py:372-374`) instead of a git-step failure. The result is
  still safe (fail-closed, nothing pushed); only the message is wrong. Low priority.
- `template/src/pdca_harness/integrate.py:355-362` — when a published branch is gone, the
  fold calls `merged.is_merged`, which runs `gh pr view` (`merged.py:46`) while the
  integration lock is held. A `gh` failure counts as "not merged" (`merged.py:48-51`), so a
  flaky network turns a merged, deleted branch into a run-stopping `IntegrationError`. That
  is fail-closed and matches the brief. The brief already owes a live-host check of this
  path at sign-off. Noted, no change asked.
- Test coverage, `template/tests/test_integrate.py:292-300`
  (`test_overlap_raises_integration_error`): it checks the error and that nothing was
  pushed. It does not check that `_merge_published`'s `merge --abort`
  (`integrate.py:371`) leaves the reused integration worktree clean. A dirty tree would make
  the next `checkout -B` fail on a re-run. A one-line `git status --porcelain` check on the
  worktree would pin this. Optional.
- `template/tests/test_integrate.py:194-202` (`test_fold_commits_carry_a_dco_signoff`) checks
  the trailer on the tip commit only. With a single bundle the tip is the `--no-ff` merge
  commit, so it does cover the new merge-commit signoff. No action needed; noted because the
  test's subject changed from a re-applied commit to a merge commit without a rename.

Nothing in the publish change (`publish.py:261-262`) looks wrong: `wave_stacked` only flips
`pr_base` for a recorded stack-base outside merge mode, and the legacy `Stacks on:` and fork
paths are untouched, which the new tests pin.
