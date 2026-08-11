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

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Whether render/update compatibility remains intact must be decided after installing Copier and rerunning those checks — Copier is absent and all 7 root render/update tests skipped, so that portion of the recorded T3 green is provisional; the independently reproduced lineage crash is recorded under C3/T5.; T4 Contribution — Whether the contribution has the required impact opener and tracker references must be decided from the actual commit message and PR body — neither artifact nor the instance-level `contribcheck` wrapper is among the supplied review inputs, so the recorded green cannot be rerun.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Maintainer must verify the final commit sign-off/conventional subject and PR user-impact opener plus `Closes #468` — neither contribution artifact is supplied and the independent `contribcheck` therefore deferred; these rules affect publishability (`AGENTS.md:21`).
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
