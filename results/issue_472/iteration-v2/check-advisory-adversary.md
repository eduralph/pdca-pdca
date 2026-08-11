# Check - adversarial review (advisory, non-gating)

Lens: refute the red-green evidence and the reviewer's verdict; find the input that breaks
the fix. Everything below is grounded on the target source at
`/home/eddie/pdca/pdca-harness.pdca-wt` and on runs I performed against a copy of it.

## What I could not refute

- **The red leg is real.** Reverting only the production hunks (`flow.py`, `config.py`,
  `leaves.py`) and keeping the new module: **20 of 21 tests fail**; the single pre-fix pass
  is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`, which is deliberately a
  no-regression control. Post-fix 21/21 green, and the whole driver suite is green
  (1654 tests, OK, skipped=2).
- **The tests exercise production, not a parallel copy.** Every drive goes through
  `cli._flow` (`test_flow_adopt_split.py:158`), and the spies at
  `test_flow_adopt_split.py:258-273` are pass-throughs that call the real `_drive_wave` /
  `_build_all` / `_point_at_integration` and return the production value, so the budget
  accounting under assertion is the real one. `_capture_results`
  (`test_flow_adopt_split.py:284`) wraps the real `flow.flow_ids`.
- **Mutation battery: 18 of 20 mutants killed.** Dropping `taken` from `known`
  (`flow.py:985`), either `_adoptable` guard (`flow.py:894`, `flow.py:898` - the two the
  previous round reported unpinned), the bundle-root escape check (`flow.py:881`), the
  `seen` dedup (`flow.py:873`), the run-pool break (`flow.py:1187`), the `min(allowance,
  budget - spent)` hand-down (`flow.py:1221`), charging the pool at all (`flow.py:1220`),
  either un-finished `return used` (`flow.py:1073`, `flow.py:1112`), the live
  `len(wave_list) - 1` fold test (`flow.py:1273`), the terminal half of `_is_split_parent`
  (`flow.py:827`), the total `except` (`flow.py:832`), the real-wave read-back
  (`flow.py:1002`), `scheduled`-only growth of `bundles` (`flow.py:1003`) and of
  `batch_names` (`flow.py:1005`), and `partition_schedulable` tolerance (`flow.py:917`) are
  each caught by a named test. The only surviving mutant is cosmetic (`sorted(...)` at
  `flow.py:903`).
- **Attacked and failed:** `flow_batch`/CSV parity (adoption does fire there:
  `{'500': 'COMPLETE', '601': 'COMPLETE', '602': 'COMPLETE'}`); a Plan **pre-pass** split
  under `cli._flow`'s unconditional `plan_missing=True` (`cli.py:614`) - I expected the
  parent to go terminal before the drive set is built and strand the children, but
  `split.accept` leaves a *pending* disposition, so the parent is still non-terminal at the
  filter and is adopted normally; `Conflicts with` between adopted children (honoured -
  601 and 602 land in separate waves, though no test pins it); a dependent of the split
  parent (`Depends on 500`) - it re-levels into the children's wave exactly as
  `flow.py:970-974` discloses; traversal / odd child ids (`../../etc`, `..`, `a b`, `/`) -
  all reported and skipped, no crash; `max_passes=0` - unreachable from the CLI, which
  treats the falsy value as unset; a recursion cycle (a child record naming its own
  grandparent) - bounded by `batch_names`, run finished rc 0. `integrate.fold` filters on
  `_has_patch` (`integrate.py:160`), so the patchless split parent whose wave now folds
  cannot raise `IntegrationError` and stall the adopted waves.

## Findings

- NEEDS-HUMAN [impl] - `flow.py:975` (and the same claim at `flow.py:948-950`) states an
  invariant the run does not keep: "A child the reschedule HELD is excluded from the results
  map, so a run whose only unfinished work is a held child still exits 0" / "never joins the
  results map". That holds only for a child held by the reschedule that **first** sees it.
  A child adopted by an earlier call joins `bundles` and `batch_names` at
  `flow.py:1003-1005` and is never removed when a **later** call holds it. Concrete,
  reproduced case: `pdca flow 500 700` with `700` declaring `Depends on 500`; `500` splits
  in wave 0 into `601`/`602`, `602`'s brief names `Depends on 700`; `700` halts
  AWAITING_SIGNOFF while `601` completes and itself splits in wave 1. The second
  `_reschedule` (`flow.py:917`) sees `700` outside its set and not COMPLETE, so it holds
  `602`. Observed: stderr carries BOTH `issue_500 split -> adopted children issue_602 into
  wave 2` AND `issue_602 held this run - unresolved dependency (700)`, and the results map
  comes back `{'500': COMPLETE, '700': AWAITING_SIGNOFF, '601': COMPLETE, '602': PLANNED,
  '801': COMPLETE, '802': COMPLETE}` - `602` is announced as adopted, is in the map, and
  is never driven. So the same situation ("a child this run created and could not
  schedule") produces two different report shapes and potentially two different exit codes
  depending only on *when* the hold happens. Either drop a late-held child from
  `bundles`/`batch_names` (and retract the announcement), or narrow the two docstring
  claims to "the reschedule that first schedules it".

- NEEDS-HUMAN [impl] - `config.py:312` cites `config.py:671` for the clamp
  ("Clamped below ``max_passes`` (``config.py:671``)"), but line 671 is
  `max_passes = int(driver_cfg.get("max_passes", 20))` - the *read*. The clamp is
  `max_auto_iters = min(max_auto_iters, max(1, max_passes - 1))` at `config.py:685`. This
  comment is the exact site iteration 1's carry-forward flagged ("`config.py:312-314` now
  states an invariant the patch breaks"); the invariant text was rewritten but the new
  citation a reader is asked to follow lands on the wrong statement. The peer citations in
  the same block (`flow.py:1221`, `flow.py:1109`) and elsewhere in the patch
  (`flow.py:758`, `split.py:635`, `split.py:373`, `cli.py:622`, `test_flow_slice.py:1137`,
  the three new docs anchors) all resolve correctly, so this is the one outlier.

- NEEDS-HUMAN [human] - Fitness-to-purpose, for sign-off: a first-reschedule-held child is
  excluded from the results map on purpose, so the run **exits 0** while leaving a bundle it
  created PLANNED and undriven - pinned as intended behaviour at
  `test_flow_adopt_split.py:731` and reasoned at `flow.py:975-979`. The brief does ask for
  exactly this ("excluded from the results map ... the run continues"), so this is not a
  build defect; but the outcome is a milder form of the defect the issue exists to fix (a
  split's child stranded, with the only signal on stderr). Unattended automation reading the
  exit code sees a clean success. The human should confirm that "this run created work it
  could not schedule" belongs on stderr rather than in the exit code, since a driver that
  auto-iterates on rc will never come back for it.

- NEEDS-HUMAN [human] - T4 in `check-gates.json` is the one gating row that carries an
  empty `path_line` (no quotable oracle line), and the contribution artifacts
  (`commit-msg.txt`, `pr-description.md`) are bundle files, so they are neither in
  `patch.diff` nor in this station's inputs. I therefore could not re-run or audit the
  release-facing impact text - the same carry-forward iteration 1 raised. Per issue #236
  this inability is **not** scored as a refutation; the T4 verdict is simply provisional
  from here and needs the human's eye at sign-off.

## Verdict

The core mechanism holds up under attack: the evidence is a genuine red-to-green on the
production path, the guards the brief names are pinned by mutation-resistant tests, and I
could not find an input that makes a run crash, lose a bundle, drive one twice, or exceed
the operator's pass budget. The two `[impl]` items are a false docstring invariant with a
reproduced counter-example and a mis-aimed citation; neither touches the drive mechanics.
