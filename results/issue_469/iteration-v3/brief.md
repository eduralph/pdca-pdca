# flow: adopt split children mid-run on the unified drive path

- **Slug:** flow-adopt-split-children
- **Kind:** enhancement
- **Defect / goal:** a split that happens inside a driven flow strands its own children
  (tracker #449): the parent goes terminal (`close-disposition = split`), the children
  materialise fully briefed, and the run never drives them — the operator restarts by
  hand with `pdca flow <child-ids>`. Re-land the adoption mechanics proven across #449's
  five iterations (C4 red→green reproduced, 10/14 mutations caught; splice, recursion
  bound and budget pool could not be refuted) ON TOP of the unified single drive path
  (child-1), so they are implemented ONCE and entry-point parity cannot re-break:
  detect via `split.read_lineage`, validate via `waves.partition_schedulable`, splice
  after the current wave, report with real wave indices. The v5 patch and its 17-test
  suite are preserved in `results/issue_449/iteration-v5/` and at the #449 bundle root
  as reference; the mechanics carry over, the entry-point plumbing does not.
- **Success criterion:** exercised **through `cli._flow`** on byte-identical disk state,
  both CLI shapes: (1) a run whose Plan/re-plan beat splits a drive-set bundle drives
  that bundle's children to a terminal state within the same call — in a wave AFTER the
  parent's, honouring their `Depends on` / `Conflicts with`, counted against ONE
  run-wide `max_passes` budget, each adoption announced on stderr with the child's REAL
  wave index from the recomputed schedule; (2) a run handed an id whose bundle is
  ALREADY terminal on a split adopts its stranded children (recovery, #449 iteration-1
  RULING (b)) — no pre-run short-circuit swallows it; (3) both shapes produce the same
  child states, announcements and exit code. A child with an unresolvable dependency is
  held loudly, excluded from the results map, and the run continues — never aborts.
  Adoption is lineage-scoped and transitive (only descendants of the ids given), never a
  disk sweep; an adopted child that itself splits is re-adopted within the same shared
  budget — bounded, no recursion reset. Guards proven by test, not just present: a
  split-marked but NON-terminal parent (e.g. sign-off recorded `iterate-do`) does NOT
  have its children adopted; a lineage child id that escapes the bundle root (e.g.
  `"../../etc"`) is skipped with a report; an id already in the run's drive set is not
  adopted twice (dedup against the batch AND a duplicate id within one record).
  Demonstrable by C4-verify on the patch alone.
- **Falsifiability:** RED on the offline driver suite — `cd template && PYTHONPATH=src
  python3 -m unittest tests.test_flow_adopt_split`, the invocation
  `engine/scripts/run-verify.sh` uses for a `template/tests/*.py` test. With all six
  leaves stubbed (fixture shape at `template/tests/test_flow_slice.py:31-56`), a leaf
  patched to split the parent mid-run, and the fixture built with the production
  `split.accept` (`split.py:525`): pre-fix (child-1's base, no adoption) the children
  stay PLANNED after either CLI shape returns — `_drive_and_act` computes `wave_list`
  once (`flow.py:799` at `f7876f2`) and the drive set is built once — so assertions
  that children reached COMPLETE fail; post-fix green. The guard tests are red pre-fix
  by the same route. No tracker, network, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 468
- **Ordering note:** builds on child-1's unified results-map drive path — adoption is
  implemented once on the shared path, which is the whole point of the split; landing it
  on today's forked entry points would reproduce #449's five-iteration divergence chase.
  Wave fold gives this bundle child-1's accepted diff; both edit `cli.py` / `flow.py`.
- **Surfaces:** data
- **Difficulty:** high — the adoption splice lives inside `_drive_and_act`'s run-scoped
  wave/fold/integration state, the most load-bearing loop in the driver; a reviewer must
  hold the wave/fold/publish/budget interaction in view.
- **Scope:** adopt the children of a bundle that goes (or is found) `close-disposition =
  split` while in the drive set — detect (read `split.read_lineage`; a parent with the
  marker but no readable record is reported and skipped, never a crash), validate
  (`waves.partition_schedulable` tolerance; held children reported in the existing
  "held this run — <reason>; left in-flight" shape and EXCLUDED from the results map),
  splice (children join after the current wave; pointed at the same per-target
  integration branch via the existing `_point_at_integration`; one run-wide `max_passes`
  pool across original AND adopted waves; adopted children join the set
  `_warn_abandoned` / final sweep cover), report (real wave indices, identical on both
  CLI shapes) — on the unified drive path from child-1, so `flow`, `flow_ids` and
  `flow_batch`'s drive phase inherit it from one implementation.
  / out of scope: changing why recursive splits happen (#448's line — merely never
  enable an infinite one); a disk sweep in `flow_ids` (the distinction from the CSV
  sweep is deliberate and stays); the `--accept` hint printing `pdca flow <child-ids>`
  (still right for a split accepted outside a running flow); `waves.compute_waves` /
  `partition_schedulable` semantics (reused as-is); the split command, `split.accept`,
  or the lineage schema (#456 shipped it — independent optional edges, NO `role` field,
  `children` iff split); publish/fold semantics beyond the existing reconciliation; the
  pre-existing T3 red (`template/tests/test_verify_base.py` under inherited
  `PDCA_VERIFY_BASE` — verified pre-existing isolation fault, non-gating, expect it, do
  not chase it).
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; offline driver
  suite with stubbed leaves, no tracker, network or container.
- **Test file:** `template/tests/test_flow_adopt_split.py` (new module; rework the
  preserved v5 suite — 17 tests at `results/issue_449/test_flow_adopt_split.py` — to
  drive **through `cli._flow`**, the gap that let the CLI short-circuit through in v5,
  and ADD the four guards the v5 adversary showed survive mutation: non-terminal
  split-marked parent → children stay PLANNED; lineage path-escape skipped; held child
  absent from the results map (`assertNotIn`); drive-set dedup when a child id is also
  named in the batch). The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`). **Import modules,
  never new symbols** (`from pdca_harness import cli, flow, split, state, waves`; reach
  new names as attributes) — a named import of a new helper is ImportError on the red
  leg → PDCA-UNVERIFIABLE (exit 77), not red.
- **Citations expected:** Do must cite `path:line` on the wave base (child-1's accepted
  result; line numbers below verified on `origin/main` at `f7876f2` and may shift under
  child-1's diff): `flow.py:776` (`_drive_and_act`; `wave_list` once at `:799`;
  `_point_at_integration` call at `:830`), `flow.py:621` (`_point_at_integration`),
  `flow.py:659` (`_TERMINAL`), `flow.py:662` (`_warn_abandoned`), `flow.py:968-970`
  (the held-report shape to mirror), `flow.py:983` (`flow_ids`), `flow.py:928`
  (`flow_batch`); `waves.py:104` (`conflict_map`), `:140` (`compute_waves`), `:240`
  (`partition_schedulable`); `state.py:44` (`CLOSE_MARKER`); `split.py:47` (`LINEAGE`),
  `:373` (`read_lineage`), `:525` (`accept`).
  **Peer callsites to mirror, not re-derive:** the held-report at `flow.py:968-970`;
  `_point_at_integration` at `flow.py:621` (adopted children join the same `(repo,
  base)` integration branch through this call, not a second mechanism);
  `_warn_abandoned`'s not-terminal predicate at `flow.py:662`;
  `template/tests/test_flow_slice.py:31-56` for the offline fixture.
- **Disposition hint:** new-feature

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether to waive the recorded non-gating runtime red — the full driver suite passes with a clean environment, but an inherited `PDCA_VERIFY_BASE` reproducibly causes 11 pre-existing isolation failures where wave-0 expects it unset at `template/tests/test_verify_base.py:104`, so the frozen gate run was not hermetic.; T4 Contribution — Decide whether the asserted contribution-text PASS is sufficient — `commit-msg.txt`, `pr-description.md`, and the recorded `scripts/pdca contribcheck` runner were not supplied, so the required user-impact opener and tracker linkage could not be independently reproduced.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether to accept incomplete render/update compatibility evidence — the 1,655-test driver suite and 19-test inherited-`PDCA_VERIFY_BASE` regression passed, but `copier` was absent so all 7 repository render/update tests skipped (`tests/test_update_compat.py:32`).; T4 Contribution — Decide whether the frozen T4 PASS is sufficient — `commit-msg.txt` and `pr-description.md` were not supplied, so the required user-impact opener and tracker id in both artifacts could not be independently audited against `template/src/pdca_harness/cli.py:1075`.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Size backstop: patch is 111 KB (threshold 100 KB) with 2 iterate rounds already spent — the slice is oversized; author the split in the re-plan (`pdca split`), do not rebuild it whole. The core mechanics are CONVERGED and should be preserved across the split, not re-derived: C4 red→green reproduced independently (23/26 red pre-fix, 26/26 green post-fix), and the adversary could not refute the splice, recursion bound, wave indices, path-escape guard, budget hand-down, or fold boundary. Human affirmed the fitness-to-purpose policy at sign-off: transitive/recursive adoption (children that split are re-adopted) under one bounded run-wide budget is intended (§6 Validation ticked). Carry into the children the four open adversary findings: (1) budget pre-emption — the run-wide pool is sized off the pre-adoption schedule, so an adopted child can starve an id the operator typed (flow.py:1216/:1236); decide re-sizing vs named-first service; (2) single-id shape can print COMPLETE on stdout yet exit 1 without naming the adopted bundle that caused it (cli.py:669-670); print adopted dispositions or a summary line; (3) the `taken` half of the dedup key (flow.py:1009) is load-bearing but unpinned — add a same-wave two-parents test and fix the docstring citation; (4) T4 has passed three consecutive iterations without reviewer-reproducible evidence — supply commit-msg.txt / pr-description.md to the reviewer's inputs (the artifacts exist in the bundle and check out on manual read).
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
