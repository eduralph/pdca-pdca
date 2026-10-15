# Advisory code review — issue 673 (round 4)

Overall: no correctness bug found in this round's change. It was scoped to the refusal wording (`_branch_removed`) and the `_reset_line` message. Detection and the keep/refuse decisions match what the earlier rounds signed off on. Gate evidence agrees: C4 shows 12 of the 15 new tests red without the fix (the 3 that pass pre-fix are the criterion (3) "own change is merged" cases, which should pass either way), and T3 ran 2491 tests OK. The notes below are minor. None of them blocks.

## Correctness

- `template/src/pdca_harness/integrate.py:876-887` — `_branch_removed` checked by hand against each kind of `groups`. Only single-bundle groups other than `incoming` go through `_removed`, so `incoming` can never be named as `"<incoming>'s work"`. A shared group is worded as "work from X or Y — git cannot tell…", and a group that is only `incoming` is worded as "earlier work, which its branch no longer has". A path with no owner groups falls back to `note on branch`, because `whose == [""]` filters to empty. A 3-way share reads "work from A, B or C". Tests `test_integrate_revert_via_branch.py:785-819` pin the two new wordings. No bug.
- `template/src/pdca_harness/integrate.py:1039-1046` — `_reset_line` now names what it was undoing (`merged_in`). Both callers pass it: `:730`/`:734` for a bundle branch, `:836`/`:839` for the base. The round-1 finding (the message blamed the base for a bundle-branch reset) is fixed, and `test_integrate_revert_via_branch.py:874-898` covers it, including that `skipped` stays empty because `_LineBroken` is re-raised at `:578-580`.
- `template/src/pdca_harness/integrate.py:962-969` — `_own_removals` only treats the base given by `base_ref` (`{cfg.base_remote}/{base}`, `:700`) as "not the branch's own". The `skip` set (`:1005-1006`) is the line's chain plus that base's first-parent chain. Suppose a branch picked up a revert from somewhere else, for example a different upstream branch it was updated from, or an `Onto branch` parent PR. Then the revert commit looks like the branch's own, and the removal is merged without a word. This fails open, but it is narrower than the case the brief targets, and the brief limits the scope to "cut from, or updated from, the base". Recorded for awareness only, no action asked.

## Reuse / simplification

- `template/src/pdca_harness/integrate.py:1008` and `:1024` — the name `mine` is bound twice in `_undone_paths` with different types: first a set of paths (from `_own_removals`), then a set of commit ids inside the owners loop. Nothing breaks, because the first binding is not used after `:1009`, but it reads as if they were the same thing. Renaming the first one (e.g. `own_paths`) would make it clearer. Cosmetic.
- `template/src/pdca_harness/integrate.py:881` — `whose = [", ".join(...)]` builds a one-item list holding a possibly empty string, and `:886` then filters it out again with `if w`. A plain `solo = [...]` list joined once at the end would say the same thing more directly. Cosmetic.
- `template/src/pdca_harness/integrate.py:833-847` / `:727-742` — `_take_in_base` and `_keep_merge` now run the same "try `_undone_paths`; on error reset and re-raise; on a hit reset and raise" steps. The shared message pieces already moved into `_removed`. The rest is about eight lines repeated twice, with different messages each time. A shared helper would not save much, so leaving it as is seems fine.

## Efficiency

- `template/src/pdca_harness/integrate.py:693-700` — every clean bundle merge now also costs one `rev-parse`, one `rev-list` (`_cut_point`), two `git diff --name-only` calls and, with no cut point, one `hash-object`. The extra walks (`_own_removals`, the owner walks, and the pairwise `_in_line` at `:1025-1026`, which grows with the square of the number of owners) run only when a path was actually undone. That is reasonable for a fold of a few bundles.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
