# Adversarial review — issue 593, iteration 7 (round-6 carry-forward)

Scope: this round's change. That is the base-ancestry check before `_take_in_base`
(`template/src/pdca_harness/integrate.py:451-459`), fetching the base remote last
(`integrate.py:537-542`), the doc line (`template/PCDA/quality-cycle/09-parallel-lanes.md:69`),
and regression tests (a)/(b). The rest of the patch passed review last round, and I did not
re-attack it.

## What I tried and could not break

- **Evidence is real, not a tautology.** C4's red leg only reverts to `main`, where every new
  test errors because `merged_head` is missing. That alone does not prove the new tests catch
  round 6's bug. So I removed only the new base check (`integrate.py:451-458`) in a scratch copy:
  `test_a_fixup_merged_into_another_branch_stops_the_fold` (a),
  `test_a_branch_never_carried_and_merged_into_another_branch_stops_the_fold` (b),
  `test_a_failing_base_check_is_a_git_step_failure` and
  `test_a_merged_head_missing_from_the_clone_is_not_carried` all go red. Next I put the base
  remote back first in the fetch loop (`integrate.py:538`):
  `test_a_pr_merged_and_deleted_between_the_folds_fetches_is_still_carried` goes red with
  "merged somewhere other than upstream/main". Both changes have tests that fail without them,
  and the tests run the production `integrate.fold` against a real bare origin.
- **Extra real-git cases (my own, not in the suite), all behave correctly:** a fixup merged into
  `release` that later reaches `main` folds and carries the fixup. A fork (`base_remote =
  upstream`) whose PR merged upstream takes `upstream/main` in. A fork PR merged into the fork's
  own `main` instead of upstream stops the fold and pushes nothing.
- **Error shape matches the carry-forward:** the message names the bundle, PR URL, full head SHA
  and `<base_remote>/<base>` (`integrate.py:452-458`). A non-0/1 exit from `--is-ancestor` is a
  git-step failure through `_in_line` (`integrate.py:497-503`).
- **Gates:** T3's log shows 2269 driver tests OK. I re-ran `test_integrate`, `test_flow_slice`,
  `test_flow_adopt_split`, `test_verify_base` and `test_integrate_stack_bases` here: all green.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/integrate.py:451-459` (and the docs at
  `template/PCDA/quality-cycle/09-parallel-lanes.md:69`, `integrate.py:36-37`): the check proves
  the base has the merged head **by ancestry**, not that the base still has the work. Concrete
  case, reproduced on real git: fold [A] → T1; push a fixup to fix/A; merge fix/A into `main`;
  delete fix/A; then `git revert -m 1` that merge on `main`; fold [A, B] with `{TARGET: T1}`. The
  fold passes the check, merges `main` in, and the pushed line ends up with
  `['b.txt', 'base.txt']`. **A's original change is gone too**, not only the fixup. B, which
  depends on A, then builds without A, and stderr says "the merged work reaches
  pdca-integration/main through origin/main", which is false. The builder did exactly what the
  carry-forward asked (`merge-base --is-ancestor`), so this is not an implementation slip. It is
  a scope question: is "the human reverted the prerequisite on the base" a case the fold should
  stop on (for example, by checking that the line before the base merge and the line after it
  agree on the bundle's own paths), or accepted and documented? The same thing happens when a
  base merge brings in a revert of any *other* bundle already on the line. Low likelihood, but
  it is the same failure class as round 6 §6 item 3 (a prerequisite silently dropped), and the
  stderr line misreports it.

- Not a defect, noted for the record — `integrate.py:443-450`: a gone branch whose record `base`
  is not the fold's base (a legacy `Stacks on:` PR, `base = fix/P-…`) stops the fold **before**
  the new base check runs. Now that the base check exists, this early stop only adds false stops.
  Example: L merged into fix/P, fix/P then merged into `main`, fix/L deleted. `main` has L's head,
  but the fold still raises "a PR against fix/P…, not main". It stops safely rather than losing
  work, and stack mode reaches it only for a wave-0 bundle stacked on an earlier run's parent. I
  can't tell from my inputs whether an earlier round settled this, so I am not routing it.

- Not a defect, noted for the record — `integrate.py:466-467`: `_carries` reads any non-zero
  `git cat-file -e` exit as "this clone does not have the commit". Git returns 128 both for a
  missing commit and for a broken repo or worktree (checked here). So a real git failure at that
  step is reported as "merged somewhere other than <base>" instead of "a git step failed". The
  fold still stops and pushes nothing, and earlier git steps in the same worktree would normally
  have failed first. Only the wording is wrong.

## Verdict

I tried to refute the round-6 fix three ways: tests that would pass without it, a fetch-order
race, and fork vs own-repo base mix-ups. I could not. The only concrete hole I found is the
revert-on-base case above, and that is a gap in the contract as written, not in how it was built.
