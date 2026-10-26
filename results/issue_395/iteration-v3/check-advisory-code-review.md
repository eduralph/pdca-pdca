# Advisory code review — issue_395 (same-wave conflict caught before publish)

Lens: correctness bugs the patch adds, plus reuse / simplification / efficiency. Line
numbers are from the patched target tree at `$PDCA_TARGET`.

Summary: I found no blocking correctness bug. The trial runs on the same waves as the fold
(`flow.py:3166-3170` uses the same `k < len(wave_list) - 1`, not-merge, not-stub condition
as the fold at `flow.py:3202-3204`). It uses the same bundle order (`complete` sorted by
name, `flow.py:3127`) and the fold's own clash rule (`integrate._held_by`,
`integrate.py:893`). The `publish._checkout_base` refactor (`publish.py:797-806`) gives the
same result as the inline code it replaced: `wave_stacked and bool(wave_tip)` is the same
test as `wave_mode != "merge" and wave_base and wave_tip`. All six brief legs (a–f) have a
real-git test, and so do the retry, fail-closed and re-issue paths from iterations 1–2.
The points below are small.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:3173-3175`: the flow writes `conflict-hold.json` when the trial holds a bundle, but only publish removes it (`publish.py:446`, `:563`). Take a bundle held in run 1 that, in a later run, is not held again but is still not published: its texts fail T4, the trial cannot try it (`untried`), or its push fails. Run 1's record is never replaced or cleared. The next re-issue's carry (`flow.py:1538-1539`) then reports run 1's partners and files as if they were current. It only goes away when the attempt is archived (an iterate) or when it is published. Fix: in the trial block, clear the record for every bundle in `to_publish` that this trial did not hold. Add a test where run 2 is untried or fails T4 for the bundle run 1 held.
- `template/src/pdca_harness/integrate.py:825-839`: with `_TRIAL_ATTEMPTS = 2`, suppose the first try works but leaves one bundle unbuilt, and the retry then fails at a fetch. `found` is reset to `None`, so the whole target falls back to "publish only the first bundle". That throws away a usable answer from the first try. This is the safe side and the docstring says it on purpose ("Holds and failures of a try before the last are dropped"), so it is not a bug. It just holds more bundles than needed in a rare case. No action needed.
- `template/src/pdca_harness/integrate.py:880-898`: `_same_wave_trial` copies only the fold's first pass. It does not do the #672 restart (`integrate.py:692-705`: when a bundle is skipped, the merged bundles that hold its work come off too and the line starts again). So in a wave where one bundle conflicts with the line and another bundle carries its work, the trial's set of merged bundles (`kept`) can differ from the fold's. The fold's own check still covers this (`integrate.py:668`), and the brief allows for that, so it costs at worst a late hold at the fold. I am noting it, not asking for a change.
- `template/src/pdca_harness/publish.py:819-820`: the `Onto branch` (#54) path of `cut_base` builds the trial commit on `<remote>/<branch>`. No test covers it. Two other paths have no test either: the lock that cannot be taken (`integrate.py:821-824`, the default `cause` text) and the multi-target grouping in `same_wave_holds` (`integrate.py:809-813`). Each is a small branch. A unit case for the `Onto branch` ref would catch drift from `_publish_stacked`'s cut point, which uses `apply --check` on that branch (`publish.py:494-498`). Optional.
- Reuse: the new code reuses existing helpers and adds no second copy of the clash rule. It calls `_merge`, `_held_by`, `_reset_tree`, `_prepare_worktree` and `integ_lock`, plus the shared `_checkout_base` taken out of `publish`. `_would_be` (`integrate.py:901-938`) repeats publish's apply / add / commit steps (`publish.py:298-308`) instead of sharing them. That is fair, since publish's steps are argv lists built for a different checkout and they push. Keep the two in step if publish's commit steps change (for example, if publish switches to `apply --3way`).
- Efficiency: the trial adds one fetch and one build-and-merge per bundle to each non-final wave, plus `_held_by`'s pairwise trial merges, but only for a bundle that conflicts. This matches the fold's cost and is skipped for targets with fewer than two bundles (`integrate.py:815-816`). `_held_before` makes one `gh pr view` per partner per re-issue (`flow.py:1370-1376`), and only for bundles that have a hold record. Neither is on a hot path.

<!-- pdca:leaf-complete -->
