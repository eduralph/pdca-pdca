# flow: drive a split's children in the run that split them

## Summary
**User impact:** when a run decided a piece of work was too big and broke it into
smaller ones, it then abandoned them. You watched it plan the split, create the new
items — and stop, leaving you to start a second run by hand and type their ids to get
any of them done. Long unattended runs quietly did a fraction of the work you asked
for.

This PR makes the run that splits a piece of work also do the pieces: they join the
same run, in order, within the budget you already allowed.

Reported in [#472](https://github.com/eduralph/pdca-harness/issues/472).

## What to look at
The behaviour to try: give a run something big enough that the planning step decides to
decompose it (`pdca flow 500`, sign-off recorded as `iterate-plan`, the re-plan then
`pdca split 500 --accept`). Before this change the run ended with 500 closed and its
children untouched; now the same single command drives the children to completion too,
after their parent, in dependency order — and prints one line per adoption saying which
children joined which wave.

Three things worth a reviewer's attention, because they are deliberate limits rather
than omissions:

- **The budget does not grow.** `[driver].max_passes` now also sizes a pool for the
  whole run, so adopted work spends what the original schedule was allowed. A run that
  adopts nothing behaves exactly as before. A run that spends the pool stops and names
  what it walked away from.
- **A child that cannot be scheduled is held, not fatal.** It is named on stderr with
  the reason, left in flight, and left out of the run's results — a split can never
  abort the flow that caused it.
- **Only descendants of what you asked for.** Adoption follows the split's lineage
  record, transitively; it never turns into a sweep of `results/`. A run handed an id
  that was *already* closed on a split still prints today's `pdca flow <child-ids>`
  hint — recovering those is a separate change.

## Root cause
`_drive_and_act` computed its wave list once and drove exactly the bundles it was
handed, so a drive set could only shrink, never grow (`flow.py:845`, with the one-shot
`wave_list` at `flow.py:868`, on the merged base). Nothing read the
`split-lineage.json` record `pdca split --accept` writes (`split.py:47`,
`split.py:373`), so a parent that reached `close-disposition = split` mid-run took its
children out of reach of the run that had just created them.

## Fix
One adoption seam on the unified drive path, after each wave is driven
(`template/src/pdca_harness/flow.py:1434`), so both `pdca flow` shapes and `flow_batch`
inherit it from one implementation:

- **detect + validate** — `_adoptable` (`flow.py:896`) reads the parent's lineage record
  only when the parent is *terminal* on the split marker (`_is_split_parent`,
  `flow.py:870`), and filters each id exactly as `flow_ids` filters one the operator
  typed. The record is hand-editable, so it is also guarded: a duplicate entry yields one
  child, an id that is not a plain tracker token is refused (`_PLAIN_ID`, `flow.py:828` —
  the rule `split.validate` applies at write time, `split.py:297`), and containment is
  decided on the **resolved** path (`_inside_bundle_root`, `flow.py:844`), so an
  `issue_<id>` symlinked outside the instance is reported and skipped rather than driven
  and published. An unreadable marker or record is reported and skipped, never a crash.
  Two cases a reader of the log depends on: an entry that is not a usable id *at all* (a
  JSON number, an empty string — dropped before the filters above ever see it) is counted
  and echoed rather than lost in silence, and one bundle is adopted once even when two
  names reach it, so an `issue_<id>` symlinked to a bundle the run already drives cannot
  put one directory in a wave twice (which under `lanes > 1` is two lanes on one bundle).
- **splice** — `_adopt_split_children` (`flow.py:1082`) re-levels the un-driven tail
  together with the new children through the resume path's tolerance (`_reschedule`,
  `flow.py:1024`), replaces `wave_list[k+1:]`, and grows the drive set. Children reach
  their integration branch through the existing `_point_at_integration` call every wave
  goes through (`flow.py:1424`), not a second mechanism.
- **budget** — one run-wide pool, `max_passes × the waves the run set out to drive`
  (`flow.py:1385`), spent down by every wave including adopted ones (`flow.py:1429`); a
  run that adopts nothing cannot reach it.
- **report** — each adoption is announced with the child's real wave index read back
  from the recomputed schedule; a held child is reported in the existing
  "held this run — …; left in-flight" shape and excluded from the results map. A child
  refused because another parent already claimed it is reported *after* the splice
  (`_report_refused`, `flow.py:1047`), so the log can never claim a child is "already in
  this run's drive set" while the same run has just held it.

## Verification
- **Claim:** a run whose Plan/re-plan beat splits a bundle in its drive set drives that
  bundle's children to a terminal state within the same call — after the parent's wave,
  honouring their `Depends on` / `Conflicts with`, against one run-wide `max_passes`
  budget, with each adoption announced at its real wave index; an unschedulable child is
  held loudly and excluded, and the run continues.
- **Checked:** `template/src/pdca_harness/flow.py:790-1215` (the adoption unit) and
  `:1377-1434` (the drive loop that splices, budgets and reports) on `main`; the operator
  contract in `docs/07-crosscutting.md:243` and `:319`.
- **Test:** `template/tests/test_flow_adopt_split.py` — 27 tests, every one driving
  through `cli._flow` with all six leaves stubbed and fixtures built by the production
  `split.accept`. 26 of the 27 fail with the production hunks reverted and all 27 pass
  with them (the one that passes pre-fix asserts a *non*-adopting run is unchanged). Full
  offline driver suite: 1660 tests, green.

Fixes #472
