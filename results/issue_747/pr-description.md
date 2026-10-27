## Summary
**User impact:** In a stacked run, if one fix's change overlapped with a fix that an
earlier wave had already put on the integration line, the whole run stopped. Every fix
still waiting was left unbuilt, even ones with nothing to do with the overlap. The user
had to untangle one fix's overlap and re-run before any other work could go ahead. The
same overlap between two fixes of the *same* wave was already handled by holding just the
one fix; an overlap across waves was not.

This PR holds back only the overlapping fix (plus the fixes that depend on it or are tied
to it by `Conflicts with`) when fixes already on the line clearly explain the overlap. The
rest of the run goes on. The hold line names every fix it overlaps with and gives a next
step that fits.

Reported in [#747](https://github.com/eduralph/pdca-harness/issues/747).

## What to look at
- **When a fix is held instead of stopping the run.** Only when the clash is clearly that
  fix's alone. Its own change merges onto the base by itself, specific fixes already on
  the line conflict with it, and the line *without* those fixes takes it cleanly. Those
  fixes can come from the same wave, an earlier wave, or an earlier run (a finished fix
  carried onto the line before wave 0).
- **The hold lines.** At fold time: "issue_Y held out of the integration fold — its
  change conflicts with issue_A's, already on the line from an earlier wave (conflicts in
  shared.txt) …". At the end of the run, the proposed fix:
  - partner is not a prerequisite → "declare `Conflicts with: A` in issue_Y's brief, then
    rebuild issue_Y on a base that holds issue_A" (as for same-wave holds today);
  - partner is the held fix's own prerequisite → "issue_10 is issue_21's own
    prerequisite: rebuild issue_21's branch on issue_10's, then re-run". It never proposes
    `Conflicts with` on a fix's own prerequisite.
  - Same-wave hold lines are byte-for-byte unchanged.
- **What still stops the run, on purpose.** A clash with the base itself; a clash that
  only shows when two line fixes are both present; a partner whose own change no longer
  fits the base; and a fix left on the line that was built on a partner (it would bring
  the partner back). Follow-ups #748 (clashes caused jointly) and #749 (partner stranded by
  a moved base) will turn the second and third into holds. The tests that pin them name
  the follow-up that flips them.
- **Exit codes.** Only holds left: 3. A dependent left PLANNED: 1.

To try it, run the new test module (real git, offline):

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_cross_wave_fold_holds tests.test_flow_same_wave_conflict
```

This builds on #738 (PR #746, hold a fix whose own base cannot be built). Both change the
held sets passed to `_runnable`, so this PR is stacked on that branch.

## Root cause
In `integrate.fold`, a merge conflict was turned into a hold only by `_held_by`, which
checks partners merged earlier in the same wave. Any other conflict raised, and the flow's
in-run fold block turned it into `STOPPING`. Finished fixes carried onto the line before
wave 0 were not even visible to the fold as possible partners.

## Fix
- `integrate.py`: new `_held_by_line`, tried in `fold`'s conflict branch when `_held_by`
  finds nothing. It reuses `_built_on`, `_clash` and `_partners` (no second classifier)
  and holds only for a `"batch"` clash whose named partners explain the whole conflict:
  one trial merge of the line minus the partners, with the held head merged **last**, as
  the fold does. A fix left on the line that was built on a removed partner means a stop.
- **Prerequisite partners.** A partner that is the held fix's own direct prerequisite
  (`Depends on` / `Stacks on`, new `_prerequisites`) stays on the line, and the trial
  uses the head rebuilt on it instead. Without this, a fix that clashes with its own
  prerequisite (the most common case) could never be held. Transitive prerequisites are
  not exempt; that stays a stop. Reviewers of #748 should know this exception exists.
- `_trial` gets a keyword-only `made` out-list that returns the commit a clean trial
  ended on. All other callers are unchanged.
- `fold` gets a keyword-only `finished_heads`: the heads the pre-wave carry folded. They
  are used **only** as partner candidates. They are never merged by the in-run fold and
  never enter `took` or `carried`, so the rewrite checks from #633/#695 are unchanged.
- `flow.py`: `_carry_finished` records the heads it carried; `_drive_and_act` passes them
  through `_fold_lines` to `fold`. The held fix lands in `held_conflict`, which `_runnable`
  already honours, so dependents and `Conflicts with` partners are held with no change to
  `_runnable`. `_announce_conflict_holds` / `_report_conflict_holds` word each partner by
  where it came from and give the rebuild step for a prerequisite partner.
- Tests: new `test_flow_cross_wave_fold_holds.py`; one existing test in
  `test_flow_same_wave_conflict.py` that pinned the old stop is renamed and now asserts
  the hold. No other existing test changes.

## Verification
Line numbers are on the branch this was built on (`main` plus #723, #727–#729 and #738,
at `9f7c446`), with this patch.

- **Claim:** a cross-wave clash explained by named partners holds only that fix; unrelated
  fixes complete.
  - **Checked:** `template/src/pdca_harness/integrate.py:655-668` (conflict branch tries
    `_held_by`, then `_held_by_line`, records into `held_out`);
    `integrate.py:1794-1857` (`_held_by_line`); `flow.py:3045-3067` (in-run fold block).
  - **Test:** `template/tests/test_flow_cross_wave_fold_holds.py:290`: Y held naming
    issue_A, unrelated chain W→V→U COMPLETE, no `STOPPING`, no "same wave", proposes
    `Conflicts with: A`, exit 3.
- **Claim:** a finished fix carried onto the line is named as a partner.
  - **Checked:** `flow.py:1367`, `:1500-1501` (carry records heads), `flow.py:2825-2830`,
    `:3056` (passed to the fold); `integrate.py:1829-1830` (used only as candidates
    still on the line).
  - **Test:** same file `:325`: Y held naming issue_F, Z COMPLETE, exit 3.
- **Claim:** a clash with the fix's own prerequisite is held with rebuild advice, never
  `Conflicts with`.
  - **Checked:** `integrate.py:1836-1852`, `:1860` (`_prerequisites`);
    `flow.py:1548-1567`, `:1569`, `:1593` (wording).
  - **Test:** `template/tests/test_flow_same_wave_conflict.py:367` (renamed from
    `test_a_conflict_with_earlier_wave_work_still_stops_the_run`): 21 held, stderr names
    issue_10 and `(conflicts in shared.txt)`, says to rebuild on issue_10's, no
    `Conflicts with: 10`, no "same wave", 30 not built, exit 1. Mixed partners
    (prerequisite + another): `test_flow_cross_wave_fold_holds.py:477`, exit 3.
- **Claim:** clashes the rule cannot pin still stop.
  - **Test:** `test_flow_cross_wave_fold_holds.py:363` (only together; #748 flips it),
    `:392` (partner no longer fits the base; #749 flips it), `:422`, `:448` (line fix
    built on a partner), `:518` (prerequisite does not explain it alone — also asserts
    with plain git that merge order matters here), `:555` (transitive prerequisite);
    `test_flow_same_wave_conflict.py:435` (clash with the base) unchanged.
- **Red/green:** with the production change reverted and the tests kept, the four hold
  tests (`:290`, `:325`, `:477`, and the renamed `:367`) fail with `wave N did not
  integrate … STOPPING`; the stop guards pass both ways by design. Each new piece of the
  rule was also broken one at a time (trial order, prerequisite exception, carried heads,
  built-on check), and each break turns at least one test red.
- **Full suite:** root suite 24 tests OK; driver suite 2619 tests OK (2 skipped). Docs
  lint and site render clean.

Fixes #747
