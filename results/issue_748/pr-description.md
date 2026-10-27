## Summary
**User impact:** in a stack-mode `flow` run, a bundle whose change clashes with the
combined work of two earlier bundles (but with neither one alone) stops the whole run
with `STOPPING`. Every later bundle, even ones that have nothing to do with the clash, is
left unbuilt, and the user has to work out which bundles caused it.

This PR holds just that bundle instead, names exactly the bundles that cause the clash
together, and lets the rest of the run finish. Bundles the clash does not need are never
named. This builds on #747, which does the same for a clash with a single bundle.

Reported in [#748](https://github.com/eduralph/pdca-harness/issues/748).

## What to look at
The change is one new fallback in the integration fold: when no single bundle on the
line explains a conflict, it tries the bundles in pairs, and names a pair when the held
branch merges after each one alone but not after both. The same "the line without them
merges the branch" check that #747 applies to a single partner then decides whether to
hold or stop.

To see it: on a base with a ten-line `shared.txt`, plan P (renames it to `moved.txt`), R
(rewrites most of it) and H (edits its last line, in a later wave), plus an unrelated
chain. Before this change the run prints `STOPPING`. After it, H is held with
`its change conflicts with issue_P's, issue_R's …`, the proposed `Conflicts with: P, R`
is printed, the unrelated chain completes, and the run exits 3. Case (1) of the new test
file runs exactly this.

What still stops, on purpose: a clash only three or more bundles make together, and one
that needs a line bundle that was itself built on another line bundle.

## Root cause
`_held_by_line` (from #747) only accepted a clash that the partners `_clash` names one at a
time fully explain. When the rest of the clash came from two line bundles together, that
acceptance check failed and the fold raised, which stops the run.

## Fix
All in `template/src/pdca_harness/integrate.py`; `flow.py` is unchanged because #747's hold
wording already lists several partners.

- `_held_by_line`: if #747's single-partner answer is not accepted, call `_together` and
  run its set through the same acceptance check. An empty set, or the same set that
  already failed, still stops. A conflict with the base itself never reaches the new code.
- `_explains`: #747's acceptance check, moved out of `_held_by_line` unchanged so both
  paths use it.
- `_own_change`: for each line bundle, `git merge-base` of the held branch and that
  bundle's head, merged first in every trial. What the branch already holds of a bundle is
  then on both sides, so only the branch's own change is judged. No squash of the branch
  onto its start (squashing loses which tip of a prerequisite it holds).
- `_together`: the search. Size one: a bundle the branch's own change fails after alone.
  Size two: two bundles, each clean alone, failing together. Only bundles cut from the
  base go into pairs. Cost is up to n single and n(n-1)/2 pair trials, written in the
  docstring; it runs only after a fold merge has already conflicted.
- `_clash`, `_partners` and `_held_by` are not changed, so `_clash`'s contract for its
  other caller (the pre-wave carry) stays the same.

## Verification
Line numbers are on this branch with the patch applied.

- **Claim:** a clash two line bundles make only together holds the bundle and names both.
  - **Checked:** `template/src/pdca_harness/integrate.py:1842-1851` (fallback after #747's
    check), `:1916-1966` (`_together`), call site unchanged at `:661-666`.
  - **Test:** `template/tests/test_flow_cross_wave_joint_holds.py:270`, case (1).
- **Claim:** a bundle the clash does not need is never named.
  - **Test:** `:291` (case 2, unrelated X on the line), `:353` (case 4, two pairs in
    different files plus an unrelated X: exactly M, N, P, R named).
- **Claim:** a direct clash and a joint clash in the same file name all three bundles, and
  the proposed rebuild merges cleanly onto the line.
  - **Test:** `:314` (case 3, names A, P and R).
- **Claim:** a branch built on a line bundle is judged on its own change only.
  - **Checked:** `integrate.py:1887-1913` (`_own_change`) and its use at `:1939-1940`.
  - **Test:** `:408` (case 6). With `_own_change` forced to return `[]`, this case fails
    (X is wrongly named) and the other five still pass, so the case pins the helper.
- **Claim:** stated limits still stop the run.
  - **Test:** `:379` (case 5, a clash only three bundles make together prints
    `STOPPING`, rc 1). `test_flow_same_wave_conflict.py::test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`
    passes unchanged.
- **Claim:** the old guard flips as expected.
  - **Test:** `template/tests/test_flow_cross_wave_fold_holds.py:363`, renamed to
    `test_a_clash_two_line_bundles_cause_only_together_holds_naming_them`, now asserts the
    hold naming A, P and R, the whole chain complete, rc 3.
- **Red/green:** with the production hunks reverted, cases (1)-(4) and (6) fail on
  `did not integrate … STOPPING` and the flipped guard fails; with the patch, the new file
  (6 tests) and `test_flow_cross_wave_fold_holds` (9 tests) pass. The full offline suite
  passes (2625 tests, 2 skipped).

Known follow-up, not in this PR: #747's single-partner path tries the whole branch from
the base, without `_own_change`, so a branch built on a line bundle can still get an extra
name when the clash is direct only. Fixing it changes what #747 names, so it is left for
a separate change.

Fixes #748
