# Advisory code review — issue_749 (aim the fix at a line bundle stranded by a moved base)

Lens: bugs the patch adds, and reuse / simpler / cheaper code. Grounded on the patched
tree at `$PDCA_TARGET` (`target/`). Gates: C4 shows 6 of the 10 new tests red without the
fix and all green with it; T3 suite green.

No correctness bug found in the production change. I checked these and they hold:

- `_trial(..., wins=0, made=made)` in the rebuild loop (`template/src/pdca_harness/integrate.py:1985-1990`) always fills `made`, because the `wins` rev never stops the trial (`integrate.py:2292-2304`). So `made[0]` cannot raise `IndexError`.
- `moved[d.name]` is written only when `_held_by_line` returns a hold, and `fold` then always records it in `held_out` (`integrate.py:672-679`). So `held_moved` in `flow.py` never names a bundle that was not held. Dry runs pass `moved=None` (`flow.py`, the `_fold_lines` call in `_drive_and_act`), the same way `held_out` is handled.
- When `held == base_ref`, `lost` reuses `now` (`integrate.py:1978`), so `past` is empty there, as it should be.
- The `past` acceptance check (`integrate.py:2008-2011`) puts the updated head onto the real line with every bundle on it. A `past` hold therefore covers the whole clash, not just part of it.
- The `_where` / `_overlap_step` extraction (`flow.py`, before `_announce_conflict_holds`) is a plain lift of the old inline code, with no change in behaviour for ordinary holds. It also removes the duplicated step text that `_report_conflict_holds` had.

Findings (all minor):

- NEEDS-HUMAN [impl] — Two wordings in `_moved_hold` that a `Conflicts with` partner sees are never tested. (1) The `past` wait text, `"{name}'s branch is updated from {base}"` (`template/src/pdca_harness/flow.py:1632`), reaches `_runnable`'s partner line (`flow.py:863-868`), but no test puts a `Conflicts with` partner on a `past` hold. (2) The stranded-plus-own wait text (`flow.py:1642`) has no partner test either. Case (3d) (`template/tests/test_flow_cross_wave_stranded_holds.py:586`) only covers a stranded hold with an empty `own`. The brief's (3d) only asks for the stranded case, so this is a coverage gap, not a miss of the success criterion. One more partner test (case 3b plus an X that declares `Conflicts with: V`) would pin (1).
- Wording nit, `flow.py:1642`: with `own` set, the partner line reads "wait until issue_A's branch is rebuilt on the new origin/main, and issue_W is rebuilt on a base that holds issue_A, and issue_W's PR merges…". That is two "and"s in a row. It also joins the raw ids with `', '.join(move.own)`, which matches the ordinary-hold line at `flow.py:874`, so it is consistent, just clumsy. Not worth a round on its own.
- Minor efficiency, `integrate.py:1991`: `lead = _own_change(wt, head, held, on)` repeats work that `_unfit(wt, branch, head, held, on, tips)` already did on line 1978 (same arguments, `integrate.py:2037` inside `_unfit`). It costs one `git merge-base` per line bundle, and only on a path that runs after a fold conflict. That is cheap, so leave it unless `_unfit` is changed to also return its `lead`.

Nothing else to report on the reuse lens. The patch reuses child-2's `_own_change` and the one `_trial` helper, as the brief asks. It adds no second trial-worktree helper and no squash.

<!-- pdca:leaf-complete -->
