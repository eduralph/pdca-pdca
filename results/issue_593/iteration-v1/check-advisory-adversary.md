# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

Verdict: the core fix holds up. The red→green evidence is genuine. I found one concrete
regression the builder can fix, one doc/fitness claim that is false for a common batch
shape, one new concurrency behaviour for the human to weigh, and a test gap.

## Findings

- NEEDS-HUMAN [impl] — **`Onto branch:` bundles in a non-final wave now stop the run.**
  `template/src/pdca_harness/integrate.py:295-303` always looks up `origin/<publish.json branch>`.
  But `publish._publish_stacked` pushes to the brief's `<remote>` (`publish.py:452`,
  `git push <remote> HEAD:<branch>`) and records a bare `branch` plus `base: "<remote>/<branch>"`
  (`publish.py:507-511`). Failing case, reproduced against the patched `fold` with a scratch
  origin + upstream: a bundle with `- **Onto branch:** upstream/feat` (the documented shape,
  `brief.py:281-296`) whose commit sits on `upstream/feat` → `IntegrationError: issue_ON's
  published branch feat is gone from origin and its PR is not merged`. The message is wrong
  (the branch was never on origin), and before this patch the fold just applied `patch.diff`,
  so this case used to work. If `origin` happens to hold an unrelated branch with the same name,
  the fold merges the wrong branch without warning. Fix: for `mode == "stacked"` records, resolve
  the record's `base` ref (and fetch that remote in `_prepare_worktree`, `integrate.py:340-344`),
  and add a test. Heads-up for the human: once fixed, the fold merges the **whole** existing PR
  branch (other people's commits) onto the line. That follows from "carry the real commits", but
  the brief never mentions `Onto branch`.

- NEEDS-HUMAN — **"then shrinks to its own" is false when a wave has two or more siblings.**
  The fold fast-forwards to the first sibling and makes a merge commit M for each later one
  (`integrate.py:309-310`). A dependent cut from M, after the human merges both siblings into
  main with merge commits, has **two** merge bases with main (sibling A's tip and sibling C's
  tip). Reproduced with plain git: `git merge-base --all main fixB` → `A`, `C`, and
  `git diff main...fixB` prints `warning: multiple merge bases` and still lists `c.txt` next to
  `b.txt`. So the dependent's diff keeps showing a predecessor's change until the dependent itself
  merges, which is the #185 cost this patch claims to remove. I have not checked how GitHub
  handles more than one merge base, so treat this as a claim to verify on a real host.
  Unwarranted as written: `template/PCDA/quality-cycle/09-parallel-lanes.md:69`,
  `docs/07-crosscutting.md:644-646`, `integrate.py:13-14` / `:192`, `publish.py:250-252`, and
  brief success criterion (ii)'s rationale. Single-predecessor chains do shrink. The human
  decides: reword the docs ("shrinks for a single-predecessor chain; with several siblings a
  sibling's change can stay visible until the dependent merges"), or change how the fold
  combines siblings.

- NEEDS-HUMAN — **A continuing fold adopts whatever line origin has, not the tip this run
  pushed.** `integrate.py:285-293` checks out `origin/<line>` after a fetch with no check that it
  is the SHA this run's previous fold pushed. The flow passes only target keys, not SHAs
  (`flow.py:1848`, `:1854`). Failing case: run R1 folds T1; a concurrent run R2 on the same base
  does its first fold and force-pushes T1'; R1's next fold continues from T1', merges R1's wave-1
  branches (cut from T1) with a merge commit, and pushes a clean fast-forward. R1's later-wave PRs
  now silently carry R2's commits. Before this patch the per-fold rebuild kept each run's PRs to
  its own work (R2's PRs broke instead). The "it moved since this run's last fold" error at
  `integrate.py:322-324` only fires if origin moves between this fold's fetch and its push.
  Concurrent runs are #591 and out of scope, but this diff changes that failure from "overwrite"
  to "silent mixing". A cheap guard: have `fold` return the pushed SHA, have `flow` pass it back,
  and refuse when `origin/<line>` differs. Scope call for the human.

- NEEDS-HUMAN [impl] — **Two test gaps let a regression to "always rebuild and force" pass.**
  (a) The only flow-level check is `folded_before == [set()]` (`tests/test_flow_slice.py:1140`)
  in a stub-publisher run, where `integ` is never filled (`flow.py:1853`, `if folded and not dry`).
  Hard-coding `folded_this_run=set()` at `flow.py:1848` passes every test, yet makes every fold a
  fresh force-pushed rebuild. That rewrites T1's sibling merge commit, the exact defect this issue
  fixes. Add a test with three or more waves and a non-dry fold that asserts the second fold
  receives `{(repo, base)}`. (b) `test_later_folds_push_without_force`
  (`tests/test_integrate_stack_bases.py:147`) proves the push is a fast-forward, not that it is
  unforced: `receive.denyNonFastForwards` accepts a `--force` push that happens to be a
  fast-forward, so reverting `integrate.py:320-321` to always `--force` still passes. Spy on
  `_git` for the push arguments, or move origin's line between the two folds and assert the
  refusal.

## What I tried that did not break the fix

- **Evidence.** In `gate-logs/C4-verify.log` the red leg fails for the right reasons: the
  append-only test fails on its ancestry assertion, the no-force test on the refused force-push,
  and both publish tests on `--base pdca-integration/main`. Only
  `test_a_new_runs_first_fold_restarts_from_the_base` fails with a `TypeError` on the red leg,
  which the brief allows. The tests call the real `integrate.fold` / `publish.publish`; there is
  no copy of production code. I re-ran `tests.test_integrate_stack_bases` and
  `tests.test_integrate` on the patched target: 23 tests OK. The T3 log shows 2224 driver tests
  OK.
- **Merge-mode guard (#411).** The PR base is changed only after `_merge_base_refusal`
  (`publish.py:269-278`), so that guard behaves as before.
- **Fork path.** `pr_base` for a fork is unchanged (`publish.py:258`).
- **Overlap.** On a conflict the fold runs `merge --abort` and raises before any push
  (`integrate.py:309-315`); the test confirms origin's line is untouched.
- **Stale tracking ref after a host deletes a merged branch.** Handled by `fetch --prune`
  (`integrate.py:344`) and covered by a test.
- **Unpublished bundle.** It is caught before any git step runs (`integrate.py:233-235`).
- **Multi-target runs.** The `integ` keys and `fold`'s group keys are the same `(repo, base)`
  tuple, and `accepted` is cumulative, so a target folded once stays in every later fold
  (`flow.py:1822`, `:1854`).
