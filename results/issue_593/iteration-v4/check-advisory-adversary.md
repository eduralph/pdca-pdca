# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

Bottom line: the red→green proof holds, and the core design (append-only fold of the real PR
commits, unforced pushes after a run's first fold, PRs opened against the real base) held up
against every attack below. I found one concrete case where the run stops when it doesn't
need to (reproduced with real git), two design consequences a human should rule on, and some
stale comments.

## Evidence (C4 / C5): attempted to refute, could not

- `gate-logs/C4-verify.log`: on the red leg the core cases fail for the right reasons, not
  because of an import error. On `main`, the second fold's force-push is refused by a
  `denyNonFastForwards` origin, so the flow prints "STOPPING"
  (`test_a_three_wave_run_folds_append_only_onto_a_real_origin`). The publish record base is
  `pdca-integration/main`, not `main` (`test_a_wave_bundle_publishes_against_the_real_base`).
  No dependent is held (`test_an_unpublished_bundle_holds_only_its_dependents`). Seven new
  cases error with a `TypeError` on the new keyword, which the brief accepts. Two red
  failures are about message wording only (`test_overlap_raises_integration_error`,
  `test_a_conflict_names_the_conflicting_paths`), but neither is the case that proves the
  fix. I re-ran `tests.test_integrate_stack_bases` and `tests.test_integrate` on the patched
  target: 40 OK.
- The e2e flow test (`template/tests/test_flow_slice.py`, `test_a_three_wave_run_…`) uses
  the real `integrate.fold` and a real origin. It now pins exactly one
  `pdca-integrate: issue_EA` merge and checks that only the first push is forced, so the old
  rebuild-and-force-push code cannot pass it. I found no case where a test passes against a
  copy of the production code instead of the code itself.
- Also tried and could not break: the "another run moved the line" check
  (`template/src/pdca_harness/integrate.py:338`), the unforced push for a continuing fold
  (`:355`), the `Onto branch` record resolving to the other remote's branch, and dry-run
  touching nothing.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:376-377` and `:398-413`:
  when a branch is gone and its PR is merged, the fold merges the base into the line. It
  does this even when that bundle's commits are **already on the line** from an earlier fold
  in this run. The flow passes the cumulative `accepted` list to every fold
  (`flow.py:1844`, `:1879`), so every wave-0 bundle is checked again at every later fold.
  If GitHub's "delete branch on merge" is on, this path runs as soon as a wave-0 PR merges
  mid-run. Concrete failing case, reproduced with real git on the `StackFoldGit` fixture
  (`scratch/exp_gone_in_line.py`):
  1. Fold `[A, C]` with `folded_this_run={}`. Call the pushed tip T1.
  2. The maintainer merges `fix/A` into `main` with a merge commit and deletes `fix/A`.
  3. A teammate lands an unrelated change to `c.txt` on `main`. C's PR is still open.
  4. Fold `[A, C]` with `folded_this_run={TARGET: T1}`.

  Result: `IntegrationError … origin/main, which carries its work, does not merge onto
  pdca-integration/main (conflicts in c.txt …)`, so the run STOPs. A's tip was an ancestor
  of T1, so nothing needed to be taken in. The control (`scratch/exp_not_deleted.py`) is
  identical except `fix/A` is kept: the fold succeeds. Whether the run stops therefore
  depends only on a host branch-deletion setting. This is not one of the three stop
  conditions the brief allows (iv). Fix idea: take in the base only when the gone bundle is
  not already on the line, for example by looking for its `pdca-integrate: <name>` merge in
  the line's first-parent history, or by having the flow pass the names it has already
  folded. Add this case as a test.
- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:1835-1837` holds a bundle on **any**
  non-zero publish return code. The iteration-2 case this exists for ("published earlier,
  iterated, rebuilt, re-publish …") may in practice never get a zero return code. The
  re-publish's `--force-with-lease` push succeeds, and publish writes a fresh `publish.json`
  naming the new branch (`publish.py:391`). But `gh pr create` then fails because an open
  draft PR for the same head and `main` already exists, so publish returns 1
  (`publish.py:375-381`, `:407`). The result: every iterated bundle whose old PR is still
  open is held, and all its dependents are skipped for the run, even though a correct new
  branch was pushed this run. Before this patch, that return code was only reported and the
  dependents still built. I could not check this offline (it needs the real `gh`), so treat
  it as provisional. A human should decide whether the hold should key on "no branch pushed
  this run" rather than on the return code.
- NEEDS-HUMAN — a later `pdca publish` of a held wave>0 bundle now ships later waves' work
  into the real base. The flow tells the human to run `pdca publish <id>`
  (`flow.py:1840`). The bundle keeps its `stack-base`, so publish cuts it from the
  integration line **as it is now** (`publish.py:246`) and opens it `--base main`
  (`publish.py:264-265`). By then the line holds every bundle folded after the held one's
  wave. Concrete case: waves {A} → {U, J} → {K} → {L}, and U's publish fails. After the run,
  `pdca publish U` cuts from a line holding A, J and K. U's PR, opened against `main`, then
  carries J and K, and merging it (it is a wave-1 PR) lands K before K's own PR is
  reviewed. Before this patch, the same publish opened against the integration branch.
  Decide what base a late publish of a held bundle should use, for example the line commit
  it was built and verified on.
- NEEDS-HUMAN [impl] — some text still says wave PRs open against the integration branch,
  which (viii) says should now agree with the code. These are `gates.py:536-537` ("publish
  opens its PR against that branch") and, in `publish.py`, a file this diff already edits:
  `:43`, `:611` ("stacked PR base off the prior waves' folded work"), `:618` ("open its PR
  against an old integration branch") and `:644` ("builds + opens its PR on the prior waves'
  folded work"). These are comment and docstring fixes only.

## Where the verdict may have been too generous

- `check-gates.json` reports overall `pass`, with C4/C5 green. Those gates do not cover the
  "branch gone, PR merged" path when the bundle is already on the line (finding 1). The only
  test for that path (`test_a_merged_prerequisite_whose_branch_is_gone_still_reaches_the_line`)
  covers a bundle that was never folded. So the iteration-3 fix closed one gap and opened the
  needless stop above.
