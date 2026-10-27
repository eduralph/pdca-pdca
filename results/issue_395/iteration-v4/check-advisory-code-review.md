# Advisory code review — issue 395 (same-wave conflict caught before publish)

Lens: bugs this patch adds, plus reuse / simplification / efficiency. Grounded on the patched tree at `$PDCA_TARGET`.

**Result: no correctness bugs found.** I traced the trial (`integrate.same_wave_holds` → `_same_wave_trial` → `_would_be`), how its result feeds the publish loop and the fold in `flow._drive_and_act`, the hold-record lifecycle (`publish.write/read/clear_conflict_hold`, `state.CONFLICT_HOLD`), and the carry's handling of a held id (`flow._held_before`). Things I checked that hold up:
- `publish._checkout_base` (publish.py:799-808) returns the same thing as the old inline `wave_stacked and bool(wave_tip)` rule, so the refactor keeps publish's behavior.
- The trial merges in the fold's order (name-sorted `to_publish` → `_targeted`, which keeps order), starts the line from the same `folded_tips` the fold uses, and judges a conflict with the fold's own `_held_by`. It does not add a second clash rule.
- `_would_be` (integrate.py:905-946) always puts the tree back on `branch` at its old tip, and raises `_LineBroken` if it can't. That error is an `IntegrationError`, so it fails closed through the retry loop in `same_wave_holds`.
- Targets take their locks in sorted order on one `ExitStack`, so two targets can't deadlock. The fold's `had = set(held_conflict)` is taken after the trial's holds go in, so a trial hold is not announced twice.
- Criterion (e) holds: a trial-held bundle is excluded from `held_unpushed` (flow.py:3239), and a partner whose push fails still becomes `"unpushed"` through `integrate.unpublished`.

Minor cleanups (advisory, no human decision needed):

- `template/src/pdca_harness/flow.py:1556-1558` — inside the `try`, `why[d.name] = unpublished[d.name]` is redundant, because `why.update(unpublished)` at flow.py:1579 sets the same entries again on every path (including after the `bad` branch replaces `why`). Only the `continue` matters. You could keep `if d.name in unpublished: continue` and drop the assignment.
- `template/src/pdca_harness/integrate.py:922-927` copies publish's own step list (`publish.py:296-304`, and `:492-496` for `Onto branch`): checkout, `git apply`, `git add --all`, commit. The brief says the trial must build the same tree publish pushes. If publish's apply flags ever change (say, to `--3way` or `--whitespace=fix`), the trial will quietly stop matching it. This is acceptable for now. A shared tuple of apply/stage arguments, or a comment in publish pointing at `_would_be`, would make that drift visible.
- `template/src/pdca_harness/publish.py:822-827` (`cut_base`) repeats publish's stack-branch steps and its "`Stacks on` with no branch" refusal (`publish.py:236-242`). `_checkout_base` already shares the last step. Pulling the `wave_base / stack_branch` lookup into the same helper would leave one copy instead of two.
- `template/tests/test_flow_same_wave_conflict.py:155` — `hasattr(publish, "cut_base")` has the same weakness iteration 1 flagged for `create=True`. If `cut_base` is renamed, the `cut_from` override is silently skipped and the case at :394 runs the trial against the real cut. `test_flow_slice.py:1370` has the same guard, but the new `assertIn("HU", self.publish_calls)` at :1433 catches a rename there. Since the symbol now exists on the target branch, the guard in `test_flow_same_wave_conflict.py` could be dropped.
- Efficiency: when the first try builds every bundle except one whose patch really doesn't apply, `same_wave_holds` (integrate.py:829-834) sleeps one second and redoes the whole target: fetch, rebuild every would-be commit, merge. That only costs time, on a path that should almost never run. Not worth changing.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->
