<!-- pdca:split-proposal v1 -->
# Split proposal — issue_449

Per the v5 sign-off ruling (2026-08-08): the adoption mechanics are proven, but the
"both entry points agree" contract broke by three distinct structural routes across five
iterations — `flow.flow` returns a state string, `flow_ids` returns a results map, and
`cli._flow` gates the single-id route on pre-run disk state the batch route never
consults. Split into two dependent children: first make entry-point parity hold **by
construction** (one drive path, one results map, one report/exit derivation), then
re-land the proven adoption mechanics once, on that unified path, folding in the four
surviving untested guards from the v5 adversary.

## Wave sketch

child-2 (adoption re-land) depends on child-1 (entry-point unification): wave 0 =
child-1, wave 1 = child-2 building on its accepted result. Neither conflicts with
in-flight 458 (`plan_policy.py`) or 459 (`split.py` — child-2 only *reads* it via
`split.read_lineage`).

<!-- pdca:child child-1 -->
# flow: unify the CLI entry points on one results-map drive path (parity by construction)

- **Slug:** flow-entrypoint-parity
- **Kind:** enhancement
- **Defect / goal:** `cli._flow` routes a single id and an id list through structurally
  different machinery — `flow.flow` returns a bare state string and the CLI derives its
  report and exit code from that one value (`cli.py:638-648`), while the batch route
  returns a results map through `_report_batch` (`cli.py:651-656`); and the single-id
  route is gated on pre-run disk state the batch route never consults (`cli.py:604-608`,
  the COMPLETE short-circuit). Five iterations of issue #449 broke the documented
  "both shapes do the same thing to the same disk" contract by a new route each round
  (terminal-parent filter; swallowed PreflightError; CLI short-circuit; discarded
  results map) — the asymmetry, not any one divergence, is the defect. Unify: ONE
  routing path and ONE results-map return that both CLI shapes drive through, with the
  single-id presentation (its stderr shape, its exit-code contract) DERIVED from that
  map, not a separate drive path. Concrete defect red today: for a terminal split
  parent (a bundle with a `children` edge in `split-lineage.json`, shipped by #456) the
  single-id short-circuit prints `already complete — nothing to run. To redo it: rm -rf
  <bundle>` — destructive advice, since deleting the bundle destroys the lineage record
  — where the batch shape prints a terminal skip.
- **Success criterion:** exercised **through `cli._flow`** (never hand-picked `flow.*`
  calls) on byte-identical disk state, the single-id and multi-id shapes agree by
  construction: for every bundle state in {in-flight, COMPLETE, DISCONTINUED, RESOLVED,
  terminal-with-`close-disposition = split`}, both shapes report the same per-bundle
  disposition for the shared id and derive their exit code from the same results-map
  rule, and an error meant to abort a run (e.g. `flow.PreflightError`) produces the same
  rc on both shapes. A terminal split parent (lineage record with a `children` key) is
  never told `rm -rf`; its message names the recovery (`pdca flow <child-ids>`).
  Preserved single-id presentation, derived from the map: the AWAITING_SIGNOFF listing
  of open §6 items and its rc-0 stop-for-the-human semantics. Demonstrable by C4-verify
  on the patch alone.
- **Falsifiability:** RED on the offline driver suite — `cd template && PYTHONPATH=src
  python3 -m unittest tests.test_flow_entrypoint_parity`, the invocation
  `engine/scripts/run-verify.sh` uses for a `template/tests/*.py` test. With all six
  leaves stubbed (fixture shape at `template/tests/test_flow_slice.py:31-56`) and a
  terminal split parent built with the production `split.accept` (`split.py:525`):
  pre-fix, `cli._flow(["<parent>"])` short-circuits at `cli.py:604-608` and prints the
  `rm -rf` hint (assertion on stderr fails), and the two shapes derive report/exit from
  different code (state-string vs results-map divergence assertions fail); post-fix
  green. No tracker, network, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** medium — one structural change concentrated in `cli._flow` and the
  `flow.flow` return/routing seam; blast radius is the CLI contract plus `flow.py`'s
  single-id entry, not the wave machinery.
- **Scope:** route both CLI shapes through one drive path returning one results map
  (e.g. `flow.flow` becomes a thin wrapper over `flow_ids`, or `cli._flow` routes
  `len(ids) == 1` through the batch machinery — Do's call, provided the parity is
  by construction); move the pre-run terminal checks (`cli.py:604-637`, COMPLETE
  short-circuit + RESOLVED revalidation) so the DECISION lives once on the shared path
  (RESOLVED revalidation already exists in `flow_ids` at `flow.py:1005-1016` — do not
  duplicate it); make the terminal-split-parent message lineage-aware (`rm -rf` advice
  is destructive there); keep the single-id presentation (needs-human listing, rc 0 at
  AWAITING_SIGNOFF, `state<TAB>path` line) as a presentation of the shared map.
  / out of scope: split-child ADOPTION (child-2 — this slice makes the ground safe for
  it; children of a split parent stay PLANNED here); any change to `_drive_and_act`'s
  wave/fold/budget semantics, `waves.py`, `split.py`, publish or Act; the batch shapes'
  `_report_batch` exit rule for multi-id sets (rc 0 iff all COMPLETE/RESOLVED — stays);
  the pre-existing T3 red (11 failures in `template/tests/test_verify_base.py` under an
  inherited `PDCA_VERIFY_BASE` — verified pre-existing isolation fault, non-gating,
  expect it, do not chase it).
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; offline driver
  suite with stubbed leaves, no tracker, network or container.
- **Test file:** `template/tests/test_flow_entrypoint_parity.py` (new module in the
  offline driver suite). The C4 gate reverts only the PRODUCTION hunks and keeps the
  test (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`), so a new test
  file earns its red. **Import modules, never new symbols** (`from pdca_harness import
  cli, flow, split, state`; reach new names as attributes) — a `from pdca_harness.flow
  import <new helper>` raises ImportError on the red leg, which run-verify.sh
  classifies PDCA-UNVERIFIABLE (exit 77), not red. Drive **through `cli._flow`** —
  the surface where iterations 4 and 5 of #449 both found parity breaks.
- **Citations expected:** Do must cite `path:line` on `origin/main` for every change.
  Verified at `f7876f2`: `cli.py:604-608` (COMPLETE short-circuit + `rm -rf` hint),
  `cli.py:608-637` (RESOLVED revalidation, single-id), `cli.py:638-648` (single-id
  report/exit from one state string), `cli.py:651-656` + `_report_batch` (batch
  report/exit from a results map); `flow.py:367` (`flow`, returns a state string),
  `flow.py:983` (`flow_ids`, returns a results map; RESOLVED revalidation at
  `:1005-1016`; drive-set build at `:1035-1046`); `split.py:47` (`LINEAGE`),
  `split.py:373` (`read_lineage` — the one tolerant reader; the record has independent
  optional edges and NO `role` field, `children` iff split, `split.py:392-395`).
  **Peer callsites to mirror, not re-derive:** `_report_batch` (`cli.py`) for the
  single derivation of report + exit code; `flow_ids`'s terminal filter at
  `flow.py:1041-1043` for how the batch shape already skips terminal bundles;
  `template/tests/test_flow_slice.py:31-56` for the offline fixture.
- **Disposition hint:** new-feature
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
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
- **Depends on:** child-1
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
<!-- pdca:end child-2 -->
