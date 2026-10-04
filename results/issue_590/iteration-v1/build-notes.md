# Build notes — issue 590 / flow-dep-on-seed-child-refused

Target: `eduralph/pdca-harness` @ `main` (`c67a14d`), worktree `pdca-harness.pdca-wt-l1`.
Line numbers below are in the patched tree unless marked "base".

## What changed

1. `template/src/pdca_harness/waves.py`
   - `check_dep_graph` (`waves.py:65-66`) takes a new keyword `offered: frozenset[str] =
     frozenset()` (bundle names). In the per-dependency loop, right after the in-batch test,
     `if dn in offered and dep not in stacks: continue` (`waves.py:95-96`): the edge is
     resolvable and adds no edge to the strict graph. A `Stacks on` edge to an offered name
     falls through to today's check and is still refused, as the brief asks.
   - `compute_waves` (`waves.py:172-173`) takes the same keyword and passes it to
     `check_dep_graph` (`waves.py:184`). Its own edge loop only adds in-batch edges, so an
     offered name adds nothing there either. With the default, both functions behave exactly
     as before.
2. `template/src/pdca_harness/flow.py`
   - New `_offered_by_seeds(cfg, seeds)` (`flow.py:1743-1793`): a silent breadth-first walk.
     For each seed it checks `_is_split_parent`, reads `split.read_lineage` +
     `_lineage_children` (the same reader adoption uses, `flow.py:770` / base
     `flow.py:1159-1160`), applies the same `_PLAIN_ID` and `_inside_bundle_root` guards, walks
     THROUGH a child that is terminal on a split, and keeps a child only if it is not terminal,
     not UNPLANNED, and has a `brief.md`. It prints nothing and appends to nothing. Each seed
     is wrapped in `try/except Exception`, so a broken read gives back no names, which leaves
     today's strict refusal in place for edges into it.
   - In `_drive_and_act` the strict call now passes those names (`flow.py:1887-1889`, base
     `flow.py:1830`). Only this call passes `offered`. `_reschedule` (`flow.py:1267`),
     `partition_schedulable` and `pdca waves` (`cli.py:1038`) are untouched.

Why it works: after the strict levelling, 810 sits in wave 0 with no edge. The existing `k=-1`
splice (`flow.py:1895-1898`) then re-levels `remaining + children` through `_reschedule`, so
601, 602 and 810 are levelled together and the `602 → 810` edge orders them. If adoption
takes nothing, `_reschedule` never runs and `_runnable` (`flow.py:705-716`) skips 810 at its
wave because its prerequisite is not COMPLETE. If adoption takes some children,
`partition_schedulable` holds 810 and `_report_held` names it. Neither path raises.

## Alternatives ruled out

- **Calling `_adoptable` / `_adopt_split_children` early to get the names.** They print
  operator lines and append to `refused`, so every line would print twice. The brief rules
  this out, and `test_a_lineage_cycle_is_examined_once_and_the_run_returns` counts one such
  line exactly.
- **Passing the offered children into `compute_waves` as extra bundles.** That would put
  real bundles and real edges into the strict levelling, before claims and adoption guards
  have run. The brief rules this out.
- **Running the seed splice before the strict check.** This would reorder the claim and
  adoption steps relative to validation, so adoption would claim children before a refusal
  that should leave everything untouched. It would also change the order of the k=-1
  report lines that existing tests pin. Not worth it when one keyword fixes the check.

## Tests (appended to `AdoptRecovery`, `template/tests/test_flow_adopt_recovery.py`)

- `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it` (`:769`): the brief's exact
  repro. `waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]`, all COMPLETE, rc 0.
- `test_a_seeds_grandchild_through_a_split_child_counts_as_offered` (`:788`): 500 → 601
  (itself split) → 701, 702; 810 depends on 702. Waves `[[602, 701], [702], [810]]`.
- `test_without_the_seed_or_off_its_lineage_the_edge_is_still_refused` (`:809`): `flow 810`
  alone, and `flow 500 810` with 810 depending on a PLANNED bundle 999 that is not a child.
  Both give rc 2 with today's message and drive nothing.
- `test_a_child_not_offered_is_still_refused_up_front` (`:844`): boundary (a). Three subtests
  where 602 is DISCONTINUED (driven there with the production wave driver plus a
  `discontinue` sign-off decision), RESOLVED (briefless with a `resolved` notes.json), or
  briefless (UNPLANNED). Each gives rc 2 with today's message and drives nothing.
- `test_an_offered_child_another_run_holds_is_held_never_a_raise` (`:874`): boundary (b).
  A real second process (`_hold_main`, `:122`, started by `_hold_claim`, `:739`) takes the
  production `drive_claim.Run.take` lock on 601 and keeps it until the test ends. Result:
  no traceback, rc ≠ 2, 601 and 810 not driven and still PLANNED, and stderr has a line that
  names issue_810 and 601 (here it is `_report_held`'s "held this run" line, because 602 was
  adopted and so a re-level ran).
  - Departure from the brief's wording: the brief says to copy `_hold` from
    `test_flow_single_driver.py:610-632`. That helper runs a full paused `cli._flow` in the
    child and needs that file's whole `_child_main` setup. I copied the technique (a real
    second process holding the real claim, a ready/go file handshake, a bounded wait, the
    process reaped at cleanup), but the child takes the claim directly with
    `drive_claim.run` / `Run.take`, the same API a live flow run uses to claim a bundle. That
    costs about 25 lines instead of about 120, and adoption sees the same contended lock.
    Nothing is imported from the other test file.

## Red → green (project runner, `engine/scripts/run-verify.sh`)

`PDCA_BUNDLE=results/issue_590 PDCA_BRIEF_BASE=c67a14d ./engine/scripts/run-verify.sh`:

- Green leg: `Ran 19 tests … OK`.
- Red leg (production hunks reverted, test kept): 3 failures — the repro, the grandchild
  case and boundary (b) — each with `issue_810: declared dependency '<id>' is neither in this
  batch nor an existing COMPLETE bundle` on stderr.
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

The two "still refused" tests pass on both legs. That is expected, because they pin the
contract the fix must not loosen. They are guard tests, not the red evidence.

Whole suite: `./engine/scripts/run-suite.sh` → `Ran 2303 tests … OK (skipped=2)`,
`PDCA-EVIDENCE: root suite OK, driver suite OK`.

## Self-refutation

- **(a) Genuine red?** Yes. On the run-verify red leg (fix reverted, test kept), the repro,
  the grandchild case and boundary (b) fail on `assertNotIn(self._REFUSED, err)`, and the
  captured stderr shows the exact up-front refusal from the issue.
- **(b) Production path?** Yes. Every case runs `cli._flow` (the operator surface). Splits
  come from the production `split.accept`. The stranded parent is carried to COMPLETE by the
  production `flow._drive_wave`. The wave and pass spies pass through to production code.
  The claim in (b) is the production `drive_claim` lock, held in a separate OS process.
- **(c) Fixture includes the fault?** Yes. The parent is really terminal on `split`, and its
  children are really PLANNED on disk (asserted in `_strand_a_split`) before the run starts.
  810's brief really declares the edge to the seed's child. In (b) the holder process is
  checked to be alive (`holder.poll() is None`) after the run, so the contention was in
  place for the whole run.

## Commit-readiness

The target has no formatter or pre-commit config (no ruff/black/flake8 config, no
`.pre-commit-config.yaml`; CI only runs the docs linter). No added line is longer than 96
characters, which fits the file's existing style. DCO sign-off is publish's job.

## Housekeeping

I sent the whole-suite output to `/tmp/issue590-suite.log`, which is outside the harness's
roots. That was a mistake on my part; the file is a plain text log and can be ignored or
removed by the harness.
