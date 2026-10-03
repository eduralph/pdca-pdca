# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.
All gates in check-gates.json pass (T4 deferred to publish). I found no blocking bug. The
core paths hold up on reading: resolve every ref before any git step, the tip-mismatch
refusal, unforced continue pushes, `_in_line` treating rc 128 as a git failure, and
conflict vs non-conflict merge errors. The new tests cover each brief case against real git.
The points below are small.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:376-377`: when a published
  branch is gone and `merged.is_merged` is true, `_take_in_base` assumes the work is now in
  `<base_remote>/<base>`. For a `"stacked"` (`Onto branch`) record, `is_merged` reads the
  *other* PR's `pr_url` (`merged.py:42-53`), and that PR may have targeted a branch other
  than this fold's base. In that case the fold prints "its work reaches … through
  <base_remote>/<base>" (`integrate.py:414-415`) when it does not, and later waves build
  without it. Rare, but it is a silent miss. A simple guard: only take the merged-and-gone
  path for `"new-pr"` / `"stacked-pr"` records, or check the merged PR's `baseRefName`.
  Otherwise raise.
- `template/src/pdca_harness/integrate.py:458-461`: the fold now runs `fetch --prune` in the
  user's **primary** checkout for every remote it touches, including `base_remote`. Before,
  it ran a plain fetch. Gone-branch detection only needs pruning on `origin` and the
  `"stacked"` record remotes. Pruning the base remote too is harmless in practice (it only
  drops stale tracking refs), but it is a side effect the brief does not ask for. Optional:
  prune only the remotes that hold PR branches.
- `template/src/pdca_harness/integrate.py:268-270`: the dry-run fallback calls
  `publish._resolve_target(d)` again, though `_fold_candidates` already resolved it (and
  dropped the slug). Simplification, not a bug: carry the slug in the candidate tuple, or
  build the fallback ref inside `_fold_candidates`/`_published_ref` behind a `dry_run` flag.
- `template/src/pdca_harness/publish.py:264`: `wave_stacked` reads the `stack-base` file a
  second time, though `_stack_base_branch` (`publish.py:231`, `:648-650`) already read it to
  pick `stack_branch`. Correct as written. A small cleanup would be to read
  `_read_stack_base(d)` once and use it for both, so the "stack-base wins" rule lives in one
  place.
- `template/tests/test_integrate_stack_bases.py:292-298`: the "gone branch whose PR merged
  is skipped" case only asserts that `G.txt` is absent. That would also hold if the fold had
  skipped the bundle without the merged check, or pushed nothing at all. It is weak on its
  own, but `:309-330` covers the real behaviour (merged work reaches a continued line), so
  this is a nit. Asserting the "is gone and its PR is merged" stderr line and that `LINE`
  was pushed would make it pull its weight.

Nothing else found: the flow changes (`flow.py:1855-1885`, `_runnable` `flow.py:694-695`,
`_publish_bundle` return `flow.py:656`) are consistent with each other. `folded_tips` is
filled only from targets `fold` actually returned, and a `pushed_tip` failure is caught as
an `IntegrationError` and stops the run as the brief requires.
