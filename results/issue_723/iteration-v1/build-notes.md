# Build notes — issue 723 (`build_bundle_base`)

Base: the run's line `pdca-integration/main-r547f8028520f` at `489e5fb` (worktree
`/home/eddie/pdca/pdca-harness.pdca-wt`). Line numbers below are in the patched file; the
`fold` / helper anchors the brief cites (`:126`, `:154`, `:280`, `:327`, `:538`, `:810`,
`:842`) are on `489e5fb` before the patch.

## What changed

All in `template/src/pdca_harness/integrate.py`, plus the new test file.

- `bundle_base_branch(cfg, base, batch, name)` (`integrate.py:145`): the name,
  `integration_branch(cfg, base, batch) + "-b" + _flatten_base(<id without issue_>)`.
  `integration_branch` (`:126` on base) and `_flatten_base` (`:154` on base) are unchanged.
  I made the name a public helper so (a) the injectivity oracle for ids `12`, `1-2`, `1/2`
  can be tested (a bundle dir cannot be named `issue_1/2`), and (b) #724 can compute a
  bundle's base name without building it.
- `_owners(cfg, bundles, batch)` (`integrate.py:703`): the 4-line "who owns a path" block
  factored out of `fold` (base `integrate.py:568-575`), now called at `integrate.py:581`.
  Same behaviour; this is the only change inside `fold`'s body.
- `build_bundle_base(cfg, d, members, *, batch, carried, excluded) -> (branch, tip)`
  (`integrate.py:717`), the sibling the brief specifies. In order:
  1. Resolves `d`'s target; resolves every member with `_fold_candidates` (same as fold);
     a member on another target, or with no published branch, raises before any git step.
  2. #633: `_carried_tips` (unchanged) on the members `carried` names, before the lock,
     exactly as `fold` calls it (base `integrate.py:501`). A rewritten member raises; no
     merge, no push. The tip it checked is the one merged.
  3. Takes `integ_lock(_integ_worktree(repo, base))` (base `:280`, `:538`), runs
     `_prepare_worktree` (fetch + worktree), reads origin's copy of the branch, runs
     `_reset_tree(wt, "HEAD")`, then `checkout -B <branch> <base_remote>/<base>`: always
     fresh from the base as fetched.
  4. Each member goes through `_merge_published` (base `:810`), so gone branches
     (`_gone_branch`), base take-in (`_take_in_base`) and the #673 revert check
     (`_keep_merge`) are the fold's own code, not copies.
  5. A `_Conflict` goes to `_member_clash` (`integrate.py:824`): if the head does not merge
     onto the fetched base alone (`_trial`), the message names `<remote>/<base>` and says to
     rebuild the member's branch on it, and has no "declare the conflict / re-order". Else
     it names the earlier members it clashes with (each tried on its own after the base,
     as `_held_by` does) and keeps the "declare the conflict / re-order" wording, which
     `_merge_published`'s own message (base `:842`) also keeps, unchanged.
  6. Foreign ancestry check, `_foreign_work` (`integrate.py:855`), before the push.
  7. Push: no origin copy → `git push origin <branch>`; origin copy → `git push
     --force-with-lease=<branch>:<fetched tip> origin <branch>`. A refused push raises,
     naming the branch and the remedy (delete it on origin, or allow force-pushes on
     `pdca-integration/*`).
  8. Returns `(branch, pushed_tip(wt))`. It never reads or writes the run's line or any
     `carried` / `folded_this_run` record.

## Criterion (6): why the rule is not `foreign_commit`'s argv taken literally

The brief's shape is `rev-list --no-merges <excluded head> --not <base> <member heads…>`.
Taken literally, that list is **empty** in the brief's own red case: `P` was cut from an
old line holding `X`, so `P`'s head reaches `X`'s commit, and `--not <P's head>` subtracts
it. A literal port would never raise there. Every non-merge commit of the result comes from
the base or a member head, so "reachable from neither the base nor any member's head" is
empty for every result.

What I implemented keeps the rule's shape (non-merges, `--not <base> <heads…>`) but changes
which heads are subtracted. An excluded bundle `E`'s work is
`rev-list --no-merges <E> --not <base> <every other bundle head that E's head holds>`.
Members and excluded bundles both count. This is the same ownership rule `_undone_paths`
already uses (#673, base `integrate.py:1159-1164`): a branch that holds another bundle's
tip does not own that bundle's commits. The check refuses when any of that work is in the
built tip (`rev-list --no-merges <tip> --not <base>`), and names the first member whose
head reaches the commit.

- Red case: `X` does not hold `P`, so nothing is subtracted, `X`'s commit is in the result
  through `P`, and the build raises naming `issue_X` and `issue_P`.
- Must-not-raise case: `C` (cut from the line after wave 0) holds `A`'s head, so `A`'s
  commits are subtracted from `C`'s work. `C`'s remaining work (its own commit, plus `Z`'s,
  which `C` also holds) is not in `B`'s base, so no raise.
- Partial hold (`P` cut from `X` at X1, `X` later at X2; neither holds the other): X1
  counts as `X`'s work and is refused. That is the conservative side, matching "refused,
  never silently widened".

Mutation check: with the `*under` subtraction removed (`integrate.py:881`), the
must-not-raise test errors with `IntegrationError`. So that test does depend on the
subtraction.

## Criterion (4), revert leg: honest limit

`_merge_published` runs the #623/#673 checks on every member merge, so they are wired in.
But on a branch that **starts fresh from the base as fetched**, those checks cannot fire
through the base:

- `_cut_point` gives cut = the fetched base tip, so the base's first-parent `skip` set is
  empty and any revert already on the base is below the cut point. That is the accepted
  limit `_undone_paths`' docstring states (base `integrate.py:1131-1133`).
- A revert reached only through a member's branch (not on the base) counts as that
  member's own change under #673's rule (`_own_removals`), so it is merged.
- `_take_in_base` for a gone member is a no-op, because the branch already has the base.

The run's fold behaves the same on a fresh start (`folded_this_run={}`). Every #673
refusal test in `test_integrate_revert_via_branch.py` continues from an older tip. So the
test for this leg (`test_a_revert_on_the_base_is_judged_as_the_runs_fresh_fold_judges_it`)
is a parity test. On the #673 history (A merged into main then reverted there, B cut from
the reverted main), the bundle base and the run's fresh fold agree on content for `a.txt`
and `b.txt`. It does not show a raise, because neither path raises there. **For the human
at sign-off:** if the brief meant a history where a fresh build should refuse, I could not
construct one. The gone-member leg does raise (`test_a_gone_member_not_known_merged_…`).

## Test file and which red each case shows

`template/tests/test_integrate_bundle_base.py`, 11 cases. It loads `StackFoldGit` by path
and uses it as a helper object (as `test_integrate_revert_via_branch.py:47-60` does), and
imports only `pdca_harness.integrate`. With the production hunks reverted, each case
reaches `integrate.build_bundle_base` (or `integrate.bundle_base_branch`) inside its body
and fails with `AttributeError` (an ERROR the runner counts; the module still loads, 11
tests ran). `run-verify.sh` output: green leg `Ran 11 … OK`; red leg `Ran 11 … FAILED
(errors=11)`; `PDCA-EVIDENCE: C4 PASS`.

| case | criterion | post-fix assertion |
|---|---|---|
| `test_a_bundle_base_holds_its_members_and_nothing_else` | (1) | both A commits in, both Z commits out, `tip^1 == origin/main`, line tip unchanged, branch on origin |
| `test_the_name_is_the_line_plus_b_and_the_flattened_id` | (2) | exact `pdca-integration/main-r<key>-b12`, no `/`, 3 distinct names |
| `test_creating_pushes_without_force_and_rebuilding_forces` | (3) | `_pushes` argv: create has no `--force*`/`+`; rebuild has `--force…` |
| `test_a_refused_force_push_names_the_branch_and_the_remedy` | (3) | denyNonFastForwards + non-ancestor on origin → raises, names branch / delete / `pdca-integration/*`; origin unchanged |
| `test_two_members_that_clash_are_both_named` | (4) | names `issue_Y`, `issue_A`, `c.txt`; nothing pushed |
| `test_a_clash_with_the_base_says_rebuild_not_reorder` | (4) | names `origin/main`, `Rebuild`; no "declare the conflict"/"re-order" |
| `test_a_gone_member_not_known_merged_stops_the_build` | (4) | `_gone_branch`'s message |
| `test_a_revert_on_the_base_is_judged_as_the_runs_fresh_fold_judges_it` | (4) | parity with the run's fresh fold (see the limit above) |
| `test_a_rewritten_carried_member_stops_the_build_before_any_push` | (5) | raises "rewritten" + `issue_A`; zero pushes |
| `test_a_member_cut_from_an_old_line_cannot_bring_an_excluded_bundle_in` | (6) red | names `issue_X`, `issue_P`; nothing pushed |
| `test_an_excluded_bundle_cut_from_the_line_does_not_claim_a_members_work` | (6) must-not-raise | builds; A in, C and Z out |

Criterion (7): `cd template && PYTHONPATH=src python3 -m unittest` over all 21
`tests/test_integrate_*.py` + `tests/test_flow_*.py` modules → `Ran 453 tests … OK`, with
no existing test edited.

## Refute-your-own-test

- **(a) Genuine red?** Yes. `engine/scripts/run-verify.sh` reverted the production hunks
  in place and re-ran: 11 tests ran, 11 errors (the entry point is gone). With the fix:
  11/11 pass. Beyond that whole-function red, the mutation above shows the (6)
  must-not-raise case binds the ownership rule.
- **(b) Production path?** Yes. Every case calls `integrate.build_bundle_base` /
  `bundle_base_branch` from the shipped module, against real git (bare origin, primary
  checkout, real fetch/merge/push). The only patch is `merged.merged_head` through the
  fixture's `_merged_heads` (the host's PR state; no `gh` offline), which the existing
  stack-base tests patch too. `_pushes` spies on `integrate._git` but calls through to it.
- **(c) Fixture includes the fault?** Yes. The clash cases commit real conflicting files.
  The base-clash case moves origin's `main`. The gone case deletes the branch on origin.
  The rewrite case force-pushes a rewritten `fix/A`. The refusal case sets
  `receive.denyNonFastForwards` and puts a non-ancestor at the branch name. The (6) red
  case cuts `P` from a real line holding `X`.

## Alternatives ruled out

- **A `fold(into=…)` keyword** (the v1 approach, `results/issue_463/iteration-v1/patch.diff`
  integrate hunks). The brief fixes the design as a sibling. The v1 keyword threaded `into`
  through `fold`, `_carried_tips` and `_merge_published`, about 70 changed lines inside
  fold's paths, and gave `folded_this_run`, `held_out`, `wave` and `skipped` no meaning
  under it. The sibling changes `fold` by 2 lines (the `_owners` call).
- **Reworking `_carried_tips`'s message for bundle bases.** It names "this run folded it
  onto <line>", which is still true: the carried head was recorded by a line fold. I left
  it unchanged to keep `fold`'s callees untouched.
- **A `locks=` keyword like `fold`'s.** Not in scope. #724 may add it if its re-gate needs
  the lock held after the build.

## Commit-readiness

The target has no formatter config or pre-commit hooks (no `.pre-commit-config.yaml`; the
CI workflows are docs/render/issue-linking only). The new code keeps the file's ≤100-column
convention (the only lines at 100 are pre-existing, `integrate.py:172-173`). Both files
pass `py_compile`. No unused imports.

## Housekeeping

I left two untracked scratch files in the worktree root: `.integ.bak` (a copy of
`integrate.py` used to restore after the mutation check) and `.suite.log` (the 453-test run
log). They are not in `patch.diff`. Per the harness rules, I did not delete them.
