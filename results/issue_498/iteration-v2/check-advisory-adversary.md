# Adversarial review — issue 498 (one live driver per bundle + a truthful split hint)

Advisory only. Inputs: patch.diff, brief.md, check-gates.json, gate-logs/. Every path:line
is on the patched target at `$PDCA_TARGET` (`template/` prefix omitted for `src/` and `tests/`).

## Evidence: re-run, holds up

I re-ran C4 in a scratch copy (Python 3.14.4). With the fix, all 22 tests in
`tests/test_flow_single_driver.py` pass. With the production hunks reverted and
`drive_claim.py` removed, the same 17 tests fail as in `gate-logs/C4-verify.log`. They fail
for real reasons: on the base, B drives 7 and the in-flow accept prints `run pdca flow …`.
Nothing fails on import. The tests go through `cli._flow` / `cli._split`, and the competing
driver is a real second process, so the C5 claim holds.

## Refutation attempts that landed

- NEEDS-HUMAN — **The hint promises children the run never drives.**
  `src/pdca_harness/cli.py:881-887` prints "the running `pdca flow` will drive the
  children … — do not start another flow for them" whenever `drives_children`
  (`src/pdca_harness/drive_claim.py:328`) sees a live claim on the parent that isn't yet
  stamped `passed`. But adoption only happens if the parent's wave actually runs it
  (`src/pdca_harness/flow.py:642-645`) and the parent ends that wave terminal on a split
  (`flow.py:902`, `_is_split_parent`). Probe case: `pdca flow 7 8`. The Plan pre-pass
  briefs 8 with `Depends on: 7` and accepts a split of 8 into 801/802, and 7's sign-off is
  never answered. The accept prints the "will drive … do not start another flow" line. The
  run exits 1 with 801/802 still PLANNED, and no later line names them; the only related
  line is `issue_8 skipped — prerequisite(s) not ready (7)`. A second variant: `pdca flow
  500`, where 500's own sign-off is never answered after the in-session accept. That run
  exits 0 with 601/602 PLANNED, and only its "resume with `pdca flow 500`" line leads back
  to them. Criterion (v) says the instruction should be printed when no live run will
  drive the children, and here none does. No check made at accept time can know this, and
  the brief set the wording. So a human needs to choose: soften the text (for example
  "will adopt them if issue_8 closes as split in this run"), or add an end-of-run line that
  names split children the run was expected to adopt but didn't.

- NEEDS-HUMAN [impl] — **Most of the new release and "passed" paths are untested.**
  I deleted each of these lines in turn: `src/pdca_harness/flow.py:1900-1901` (release a
  terminal named id or split seed), `:1291` (`dropped = children` when the reschedule
  fails), `:1314` (release children retracted by a later reschedule), `:1562` (mark a
  wave with no runnable bundles as passed), and `:1705` (mark everything passed before Act).
  After every deletion, all 63 tests in `test_flow_single_driver`, `test_flow_adopt_split`
  and `test_flow_adopt_recovery` still pass. Only deleting the no-brief skip release made a
  test fail. Carry-forward item 2 asked for tests on the release paths, including
  adoption's dropped children, but only the `children not in wave_of` branch is covered
  (`tests/test_flow_single_driver.py:634`). What goes unnoticed: with `:1314` gone, a child
  the run retracts with "adopted earlier this run, now held" stays claimed, so a
  `pdca flow <child>` from another shell is refused for the rest of the run. With `:1562` or
  `:1705` gone, an accept on a parent the run will never adopt from says "will drive".

- NEEDS-HUMAN — **The run prints a resume command and then refuses it.** Probe case:
  `pdca flow 7 8` with 8 `Conflicts with: 7`, and 7's sign-off never answered. After 7's
  wave, run A prints ``issue_7 [AWAITING_SIGNOFF] — resume with `pdca flow 7` ``
  (`src/pdca_harness/flow.py:777`) and moves on to 8. Running `pdca flow 7` while A is
  inside 8's build exits 1 with "issue_7 is held by another live `flow` run". The patch's
  own rule says the opposite (`src/pdca_harness/drive_claim.py:15-19`: "the resume command
  it prints for that bundle must not be refused by the run that printed it"), while the new
  test pins the refusal (`tests/test_flow_single_driver.py:684-712`). Keeping the claim is
  defensible, since A still sweeps 7's footprint at `flow.py:1706` and runs Act. It fails
  safe: there is no second driver, and the refusal message is clear. A human should pick
  one: keep the claim and make the resume line say "once this run ends", or release the
  claim and accept that the end-of-run sweep can hit a bundle another run is now driving.

- NEEDS-HUMAN [impl] — **A hint probe can cause a false refusal.** Low priority.
  `_held_now` (`src/pdca_harness/drive_claim.py:145-162`) briefly takes the real exclusive
  lock when nobody holds the claim. A `pdca flow 7` whose `take()` lands in that moment
  (`drive_claim.py:197-206`) does not retry. It is refused as "held by another live `flow`
  run (pid <old pid left in the file>)" even though no run holds 7. This needs
  `split --accept` on 7 and a `flow` start over 7 to land within microseconds of each
  other. `_hold_new` already retries for exactly this reason (`drive_claim.py:266-274`);
  `take()` should retry the same way.

## Attempted, could not refute

- **Refusal before any write.** Named ids are claimed at `cli.py:598-611`, before
  `--from-briefs`, the RESOLVED revalidation and the Plan pre-pass. `main` writes nothing
  before `_flow` (`cli.py:432-455`).
- **The re-exec can't lose the claim.** `os.execvpe` (`cli.py:148`) runs before `_flow`
  takes any claim.
- **SIGKILL leaves nothing behind.** The claim is an flock on a handle that is not passed to
  child processes (Python's default), and the package has no `fork` or `multiprocessing`.
  The SIGKILL test fails on the base and passes with the fix.
- **A run never refuses itself.** A `pdca split --accept` spawned by the run only probes and
  never waits on the lock. No agent prompt tells a leaf to run `pdca flow`; the only
  mention is `agents/signoff.md.jinja:93`, which is descriptive.
- **Aliases and lanes.** A symlinked alias of a bundle maps to the same claim (the name is
  a digest of the resolved path, `drive_claim.py:84-90`). All lanes use one `process_dir`
  (`config.py:781`), so they share one claims directory.
- **Sweep-mark lifetime.** The mark is a live lock and is removed when the batch raises
  (`drive_claim.py:282-305`). An accept after the batch has ended prints the old
  instruction, byte-identical.
