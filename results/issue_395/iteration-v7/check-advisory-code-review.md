# Advisory code review — issue_395 / same-wave-conflict-refused-at-accept

Lens: correctness bugs the patch introduces, and reuse / simplification / efficiency. Advisory only.

**Result: I found no correctness bugs in this diff, and nothing that needs a human decision.** Two low-severity notes are below. Neither one blocks.

What I checked and found sound:

- The three iteration-6 carry-forward fixes are in place.
  1. A session is counted only once `run_signoff_batch` returns. The count is in the `else:` branch at `template/src/pdca_harness/flow.py:2783`.
  2. At wave start the count is reset, not deleted (`flow.py:419`, `_sessions_reset`).
  3. `IntegrationTreeError` / `_LineBroken` are caught before the generic `IntegrationError` fallback and refused as `"tree"` (`flow.py:306-308`). The errors are chained with `raise … from first` in `_back_on` (`integrate.py:953`).
- Each fix has its own test leg. The C4 log shows 10 of 13 tests red before the fix. The 3 that pass before the fix are legs (b), (g) and the plain-C6 leg, which are meant to pass on `main` too. T3 is green (2643 tests OK).
- The `publish._checkout_base` refactor (`publish.py:767`) gives the same result as the old inline `wave_stacked and bool(wave_tip)`. `wave_stacked` is `wave_mode != "merge" and bool(wave_base)`, as at `publish.py:251`. So the trial and publish now share one rule, and there is no second copy to drift.
- The trial condition at `flow.py:3289-3292` matches the fold's condition: not the last wave, publishing on, stack mode, and not a dry run (stub publisher, the same `dry` test as `flow.py:3351`).
- The order of guards in `_apply_decision` is correct: `unrecordable` → C6 → trial → record. C6 runs first, so when `_refuse` (`flow.py:329`) calls `open_needs_human`, the only open row it can see is the one just added. A ticked row then correctly means "override".
- The tree is put back on every exit path. `_merge` resets after a conflict, `_would_be` and the trial both call `_back_on` in `except BaseException` and again on success, and a non-`Exception` such as Ctrl-C is never replaced. The fold's own clash rule (`_held_by`) is reused, not reimplemented.

Notes (low severity, no tag needed):

- `integrate.py:812` — every accept that has an already-accepted sibling on the same target runs `_prepare_worktree`, which does a network fetch of origin with `--prune`, then the base remote. It then rebuilds the would-be commit of every accepted sibling, and runs the `alone` set of merges again (`integrate.py:829-831`). In a wave of N bundles that is up to N−1 fetches and O(N²) commit builds during sign-off. This is fine for today's wave sizes. If waves grow, the cheap fix is to cache each sibling's would-be commit and the `alone` result per wave, keyed on the sibling's `patch.diff` and the cut ref. Not worth doing in this slice.
- `flow.py:297-298` — any COMPLETE sibling counts as "accepted", including one whose publish later fails (T4 texts or push). In that case B is refused because of A, then A is held `"unpushed"`, and neither one gets a PR this run. This matches the brief: it says "already accepted", and the brief lists these two failure modes as known exceptions. B's row still gives the right next step (declare `Conflicts with`, then iterate-plan). I'm recording this so the reviewer knows about it, not as a defect.

<!-- pdca:leaf-complete -->
