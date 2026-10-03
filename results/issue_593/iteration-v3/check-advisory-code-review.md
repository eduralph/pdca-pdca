# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Advisory only; none of these gate.

**Bottom line:** I found no correctness bug that blocks the fix. The fold logic (fresh vs
continue vs auto, the tip-mismatch refusal, the unforced push on continue, the gone-branch
skip, the rc-128 split) matches the brief. The flow's hold (`publish_failed` +
`integrate.unpublished`, `_runnable`'s new `unpublished` check) also closes iteration 2's
regression, where an old `publish.json` stood in for a failed re-publish. The tests run the
real fold against real git, on an origin that refuses non-fast-forwards. They include the
failed re-publish case (`template/tests/test_flow_slice.py`, `StackModeFlow`), and they
check the push flags directly. All gates passed; T4 is deferred to publish. The items below
are small.

## Correctness

- `template/src/pdca_harness/integrate.py:402-407`: every non-zero `git merge` is reported
  as "an undeclared cross-wave overlap". The same patch takes care to keep a failed
  `merge-base --is-ancestor` (rc 128) from being reported as an overlap (`:392-398`), but
  `merge` gets no such check. One way this can happen: the optional re-gate runs in this
  same worktree (`flow.py:1905`, `gates.run_integration`) and nothing cleans the tree
  afterwards. The next continuing fold then does `checkout -B` (`:353`) with that build
  output still present. An untracked file in the way makes `git merge` refuse, and the
  operator is told to "declare the conflict / re-order", which is the wrong fix. The run
  stops either way, so the risk is a misleading message, not wrong state. Possible fix:
  tell a real conflict apart (unmerged paths present, e.g.
  `git diff --name-only --diff-filter=U`) from any other failure. Or reset/clean the
  integration tree before `checkout -B`. Also, the `merge --abort` return code at `:404` is
  ignored. If the abort fails, the next fold fails later at "could not start …", which is
  still fail-closed.
- `template/src/pdca_harness/integrate.py:120-122`: the `"stacked"` record fallback
  `ref.partition("/")[0]` cannot trigger with today's writer. `publish.py:437`/`:511`
  always record `base` as `f"{remote}/{branch}"`. If a record ever disagreed, the fallback
  would quietly merge `base`, a ref other than the recorded `branch`. Returning `None`
  instead fails closed (the bundle is then treated as unpublished) and is simpler.

## Simplification / efficiency / nits

- `template/src/pdca_harness/integrate.py:422-425`: `fetch --prune origin` runs in the
  human's **primary** checkout (`publish._checkout_path`). It prunes every stale `origin/*`
  tracking ref there, not just the published branches the fold needs. This is harmless in
  practice and is what the brief asks for (iv). A narrower option is to prune only the
  `refs/remotes/origin/<branch>` refs the fold merges. Separately, a failing fetch of
  `base_remote` now stops the fold; before, its exit code was ignored (`_git(repo, "fetch",
  base_remote)` with no check). This is intended and documented, but it is a behaviour
  change for flaky networks.
- `template/src/pdca_harness/integrate.py:273-276`: the dry-run fallback calls
  `publish._resolve_target(d)` a second time for the slug. `_targeted` (`:203-211`) already
  resolved it and threw the slug away. This is trivial; carrying the slug through
  `_fold_candidates` would avoid the second brief parse.
- `template/src/pdca_harness/integrate.py:308`: the dry-run header still says
  `fold N patch(es)`, but the plan now merges published branches (`:316`). Cosmetic.
- Test gap (minor), `template/tests/test_integrate_stack_bases.py:243-254`: the
  concurrent-mismatch test covers a line *moved* by another run. No test covers a listed
  target whose origin line was *deleted* mid-run (`line is None`,
  `integrate.py:344`, message "(absent)"). The same condition guards both, so the risk is
  low.

No item here needs a human decision. Nothing is tagged NEEDS-HUMAN.
