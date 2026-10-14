# Advisory code review — issue 674 (same-wave conflict holds one bundle, not the run)

Lens: correctness bugs the patch adds, plus reuse / simplification / efficiency. Grounded on `$PDCA_TARGET` (patched tree on the pre-fix base). Gate logs read: C4 (red leg fails 4 cases and errors 1 — the direct `fold(..., held_out=)` call; none are import failures), T3 (2450 tests OK), C5 (production package imported).

No correctness bug found in the diff. The iteration-2 guard is in place and works as described. The rest is minor.

## Checked and found sound

- `template/src/pdca_harness/integrate.py:516-544` — `pre` is read just before the wave's first merge. `accepted` is in wave order, and `_fold_candidates` keeps that order (`integrate.py:430-433`), so every earlier-wave bundle (including new fast-forward commits on a carried branch) is already in `pre`. `kept` gets only wave bundles that actually merged (or were already on the line), so a held bundle is never used to judge a later one. Case (4) depends on this, and the test covers it.
- `template/src/pdca_harness/integrate.py:900-906` — `_held_by` returns None, so the fold stops as before, when `head` conflicts with `pre` itself (earlier-wave work), and also when `head` merges cleanly onto `pre` plus `kept` (the conflict comes from something else the line took in, such as `_take_in_base` for a gone branch). That is the round-2 fix. Both paths have a test (`test_a_conflict_with_earlier_wave_work_still_stops_the_run`, `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`).
- `template/src/pdca_harness/integrate.py:628` — `_Conflict` is raised only by `_merge_published`'s conflicting-path branch. The no-path git failure (`:632`) and `_take_in_base`'s base-merge conflict (`:716-725`) stay plain `IntegrationError`, so the hold can never swallow them.
- `template/src/pdca_harness/integrate.py:911-941` — `_trial` works on a detached HEAD. `_merge` resets a failed merge (`:880`), and the `finally` puts the tree back on `branch` at its old tip, clean, or raises `_LineBroken`. The integration tree stays as `fold` expects, and `test_a_hold_leaves_the_integration_tree_clean_on_the_line` checks this.
- `template/src/pdca_harness/flow.py:2446-2462` — `held_conflict` is filled in place by the fold. The new holds (`had` diff) are announced on both the success path and the stop path, before the next wave's `_runnable`. Held bundles are left out of every later fold (`:2448-2449`), and dry-run passes `held_out=None`.
- `template/src/pdca_harness/flow.py:740-742`, `:2304-2311` — `Conflicts with` partners of a conflict-held bundle are now held, with their own wording. That was the round-1 fix, covered by `test_a_conflicts_with_partner_of_a_held_bundle_is_held_too`.

## Minor notes (no action needed)

- `template/src/pdca_harness/integrate.py:531-532` — `head is not None` and `pre is not None` are always true here. A `None` head goes to `_gone_branch`, which never raises `_Conflict`, and `pre` was already checked at `:524-526`. They help the type checker only. Harmless.
- `template/src/pdca_harness/integrate.py:937-941` — if a trial raises inside the `try` and the checkout back to `branch` then fails too, the `_LineBroken` from `finally` replaces the first error. Python keeps the first error as `__context__`, and both mean "stop, check the checkout", so no information that matters is lost.
- `template/src/pdca_harness/integrate.py:900-907` — efficiency: each held bundle costs `2 + len(kept)` trial merges, and each one checks out the whole tree. This runs only when a merge has already failed, so it is fine for real wave sizes. `git merge-tree --write-tree` (a git command that tests a merge without touching the worktree) would avoid the checkouts, but it needs git 2.38+. The harness states no minimum git version, so keeping plain merges is the right call.
- `template/src/pdca_harness/flow.py:740-742` — a bundle that both `Depends on` and `Conflicts with` a conflict-held bundle prints two hold lines: the generic prerequisite skip and the new partner line. The #629 `partners` path already does the same, so this is consistent and not worth changing.
- Re-issued runs, outside this diff's code: a conflict-held bundle is COMPLETE, so a re-issued run sends it through `_carry_finished` (`flow.py:1025-1034`). There it is skipped with the fold's old "undeclared cross-wave overlap" text, and `held_finished` holds only its plain `Depends on` dependents, not its `Conflicts with` partners. The docs the patch adds (`docs/07-crosscutting.md:705-706`) tell the user to re-run a held partner only after the rebuilt bundle's PR merges, which matches #646's existing contract. Noted for awareness, not as a defect of this diff.

No NEEDS-HUMAN findings.

<!-- pdca:leaf-complete -->
