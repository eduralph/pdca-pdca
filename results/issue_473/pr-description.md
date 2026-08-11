# PR description

## Summary
**User impact:** If the run that split a piece of work into children ends before those
children are driven — a crash, a Ctrl-C, a split accepted in another session — re-running
`pdca flow <parent-id>` does nothing but print a hint: the children stay untouched and the
operator has to hand-type every child id to resume. Two related honesty problems bite the
runs that *do* pick up split children: the run can abandon work the operator explicitly
asked for with "the run's pass budget is spent", and `pdca flow <id>` can print `COMPLETE`
while exiting 1 — so automation reading its output sees success on a failed run.

This PR makes naming the parent recover its stranded children through the same adoption
path a mid-run split already uses, funds every wave the run acquires (no wave starved, none
funded twice), and makes the single-id output report every bundle the run answered for.

Reported in [#473](https://github.com/eduralph/pdca-harness/issues/473).

**Landing order:** builds directly on the split-adoption core from #472, currently open as
draft PR #478 — that PR must merge first; this one extends its machinery rather than
duplicating it.

## What to look at
Three narrow surfaces, all on the existing drive path: the pre-run filter that used to
swallow an already-split parent (it now hands the id on as an adoption seed), the pass-pool
arithmetic (now read off the live schedule instead of sized once up front), and the
single-id stdout report (now one line per bundle in the results map, named id first).

To try it: accept a split, interrupt the run before the children are driven, then run
`pdca flow <parent-id>` — the children are adopted, scheduled by their own edges, and each
gets its own `state<TAB>path` line on stdout. The starvation case is
`pdca flow 500 810 --max-passes 2` where 500 splits into a child that costs two passes and
810 conflicts with it: 810 now completes instead of being left behind.

Note for review: this also touches `template/agents/planner.md.jinja` (and
`docs/07-crosscutting.md`) — the planner guidance and operator docs stated the old pool
rule and the old "a later run does not pick them up" limitation, which would be false
statements about the shipped behaviour if left alone. The prompt hunk is the two bullets
that became false plus one new bullet for recovery.

## Root cause
Adoption (#469/#472) only fired for a bundle that split *while this run was driving it*;
`flow_ids`' pre-run terminal filter skipped an id already terminal on a split before
adoption could see it. Independently, the run's pass pool was computed once, before the
loop (`allowance × len(wave_list)`), while every splice grows `wave_list` — arithmetic done
before the waves it must fund exist — and `_report_single` printed one line for the named
id while deriving the exit code from the whole results map.

## Fix
- **Recovery** — `flow_ids` still skips a terminal split parent (nothing to build; the
  non-destructive hint still prints) but appends it to an `adopt_seeds` list threaded into
  `_drive_and_act`, which calls the core's own `_adopt_split_children` once at `k=-1` so
  the children are levelled in front of the whole schedule — same detect, guards,
  announcements and results-map semantics; recovery is a use of the adoption path, not a
  second mechanism. `_adoptable` now also returns walk-through candidates (a child that is
  itself terminal on a split), drained breadth-first with an `examined` set, so a chain
  abandoned part-way down (500 → 601 → 701, with 601 already split) hands over the
  descendants actually stranded.
- **Budget** — `_pass_pool(allowance, wave_list)` names the rule and is read off the live
  `wave_list` at each wave, which is exactly "recomputed at splice" since a splice is the
  only thing that changes that list. The per-wave cap, the never-reset `spent`, and the
  admission rule all stay; what bounds a chain of splits is that adoption is finite.
- **Stdout** — `_report_entry` prints the documented `state<TAB>path` line (plus the
  open-items listing for a bundle awaiting sign-off) and `_report_single` calls it for the
  named id first, then every other entry, sorted — unconditionally, because a child left
  waiting for the human keeps the run at exit 0 and a failure-gated report would stay
  silent about it. A run that adopts nothing still prints exactly one line.

## Verification
All positions cited on the tree this PR produces (the #472 adoption core plus this change).

- **Claim:** naming an already-split parent adopts its stranded children, transitively,
  with the same guards and announcements as a mid-run split.
  **Checked:** `template/src/pdca_harness/flow.py:1773-1786` (seed hand-off in `flow_ids`),
  `flow.py:1471-1481` (the `k=-1` splice in `_drive_and_act`), `flow.py:1205-1218` (the
  walk-through queue).
  **Test:** `template/tests/test_flow_adopt_recovery.py` — recovery cases red pre-fix
  (children left PLANNED), green post-fix; includes mid-run vs recovery shape parity on
  equivalent disk state.
- **Claim:** the pass pool funds every wave the schedule holds, re-sized when adoption
  grows it, without resetting spend or funding a wave twice.
  **Checked:** `flow.py:1268-1291` (`_pass_pool`), `flow.py:1492` (live read),
  `flow.py:1535-1536` (per-wave cap retained).
  **Test:** `…not_starved_by_a_wave_adoption_added` — the exact
  `flow 500 810 --max-passes 2` starvation scenario, red pre-fix (`810` PLANNED, exit 1),
  green post-fix; bound pinned by `…no_more_than_the_operators_allowance`.
- **Claim:** single-id stdout and the exit code cannot disagree — every bundle in the
  results map gets its `state<TAB>path` line, named id first.
  **Checked:** `template/src/pdca_harness/cli.py:644-655` (`_report_entry`),
  `cli.py:688-691` (`_report_single`).
  **Test:** `…names_the_adopted_bundle_that_failed_the_run`,
  `…names_an_adopted_child_left_waiting_for_the_human`, and the one-line no-adoption pin —
  red pre-fix (one `COMPLETE` line, exit 1), green post-fix.
- **Red→green, independently established:** with the production hunks reverted and the
  tests kept, 12 of 14 new cases fail (the two survivors are deliberate no-op pins) and 5
  rewritten adoption cases fail; with the patch, 14/14 and 27/27 pass. Full offline driver
  suite: 1,674 tests OK (2 pre-existing unrelated skips). Docs lint + 22-page rendered-site
  link audit OK; the 7 Copier render/update-compat tests (which exercise the
  `planner.md.jinja` hunk) all pass.

Fixes #473
