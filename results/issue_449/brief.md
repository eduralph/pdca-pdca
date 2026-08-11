# Design proposal — issue 449 / flow-adopt-split-children (re-plan, to be split)

> The Plan artifact for this slice, re-authored after five build iterations. The v5
> sign-off (§9, 2026-08-08) RULED: **split, not rebuild** — the adoption mechanics are
> proven (C4 red→green reproduced, 10/14 mutations caught, splice/recursion/budget could
> not be refuted), but the "both entry points agree" contract broke by three distinct
> structural routes across the iterations, so per-divergence patching will not converge.
> This brief restates the full scope on CURRENT main (`f7876f2` — the former dependencies
> 453 and 456 are now merged) and is the input to `pdca split 449`; the children carry the
> work. Keep the `- **Label:** value` lines — the driver parses them.

- **Slug:** flow-adopt-split-children
- **Kind:** enhancement (design proposal)
- **Goal:** a split that happens *inside* a driven flow no longer strands its own
  children. When a bundle in the drive set reaches `close-disposition = split`, the run
  enumerates that bundle's children from its lineage record, validates them with the
  tolerance the resume path already uses, splices them into the remaining waves, and says
  so — instead of ending with the parent terminal, the children sitting PLANNED, and the
  operator restarting by hand with `pdca flow <child-ids>`. Both CLI shapes (`pdca flow
  <parent>` and `pdca flow <parent> <other>`) do the same thing to the same disk and
  report it the same way — **by construction**, not by per-divergence patching.
- **Success criterion:** on byte-identical disk state (a parent terminal on
  `close-disposition = split` with PLANNED children carrying a valid
  `split-lineage.json`, or a parent whose Plan/re-plan beat splits it mid-run),
  `pdca flow <parent>` and `pdca flow <parent> <other-id>` — exercised **through
  `cli._flow`**, not hand-picked `flow.*` calls — drive the children to a terminal state
  within the same call, in a wave AFTER the parent's, honouring their `Depends on` /
  `Conflicts with`, counted against one run-wide `max_passes` budget, each adoption
  announced on stderr with the child's REAL wave index; and both invocations produce the
  same child states, the same adoption announcements, and the same exit code. A child
  with an unresolvable dependency is held loudly (excluded from the results map) and the
  run continues. An explicit-id flow adopts only lineage descendants of the ids it was
  given (transitively, bounded by the run budget) and never widens into a disk sweep.
- **Falsifiability:** RED is producible on the ordinary offline driver suite — `cd
  template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split` — which is
  what `engine/scripts/run-verify.sh` runs for a `template/tests/*.py` test. With all six
  leaves stubbed (fixture shape at `template/tests/test_flow_slice.py:31-56`) and the
  fixture built with the **production** `split.accept` (`split.py:525`), pre-fix:
  (1) `pdca flow <parent>` via `cli._flow` on a terminal split parent short-circuits at
  `cli.py:604-608` — rc 0, `rm -rf` hint printed, children still PLANNED; (2) a mid-run
  split is adopted by no entry point (`_drive_and_act` computes `wave_list` once at
  `flow.py:799`; `flow_ids` builds its drive set once at `flow.py:1035-1046`; `flow.flow`'s
  loop exits when the parent derives terminal, `flow.py:389-410`). Post-fix both go green.
  No tracker, network, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none — the former prerequisites are merged: 453 (PR #460, `6668172`)
  restructured the pass loop this touches; 456 (PR #465, `f7876f2`) shipped
  `split-lineage.json` and its one tolerant reader `split.read_lineage`
  (`split.py:373-404`).
- **Conflicts with:** none in flight — 458 scopes `plan_policy.py`, 459 scopes
  `split.py`; this slice edits `flow.py` / `cli.py` and only *reads* `split.py` via
  `read_lineage`. Re-check at child-brief time.
- **Ordering note:** this parent is to be **split** (v5 sign-off ruling). Intended shape —
  two children, dependent: (a) a structural **entry-point-unification** slice: route the
  single-id CLI path through the same results-map machinery as the batch path (or make
  `flow.flow` a thin wrapper over `flow_ids`), remove/route the pre-run disk-state gate at
  `cli.py:604-608` so recovery semantics are decided in ONE place, and make report + exit
  code derive from one results map — parity holds by construction, tested THROUGH
  `cli._flow`; then (b) the **adoption re-land**: the proven detect/validate/splice/report
  mechanics on top of (a), implemented once because there is now only one drive path, with
  the four surviving untested guards from the v5 adversary folded into its test surface
  (terminal-state-in-predicate, lineage path-escape, held-child exclusion from the results
  map, drive-set dedup). (b) `Depends on:` (a).
- **Surfaces:** data
- **Difficulty:** high — it changes the drive-set lifecycle at all three entry points and
  the CLI routing above them (`cli._flow`), inside `_drive_and_act`'s run-scoped
  wave/fold/integration state, the most load-bearing loop in the driver. (This rating is
  itself the evidence for splitting: 5 iterations, size backstop tripped at round 4,
  threshold 2, overridden twice.)
- **Scope:** adopt the children of a bundle that goes (or is found) `close-disposition =
  split` while it is in the drive set — detect via `split.read_lineage`, validate via
  `waves.partition_schedulable`, splice after the current wave, report with real wave
  indices — with entry-point parity restructured to hold by construction (single results-map
  path through `cli._flow`).
  / out of scope: changing *why* recursive splits happen (448's line — this slice must
  merely not enable an infinite one; adoption shares the run's iteration budget); a disk
  sweep in `flow_ids` (the distinction from the CSV sweep is deliberate and stays); the
  `--accept` hint printing `pdca flow <child-ids>` (still right for a split accepted
  outside a running flow); `waves.compute_waves` / `partition_schedulable` semantics
  (reused as-is); the split command, `split.accept`, or the lineage schema (456 shipped
  it; note it has **independent optional edges and no `role` field** — detection is
  `read_lineage(d)` returning a dict with a `children` key, `split.py:392-395`);
  publish/fold semantics beyond pointing an adopted child at the same per-target
  integration branch through the existing `_point_at_integration` (`flow.py:621`); the
  pre-existing T3 red (11 failures in `template/tests/test_verify_base.py` under an
  inherited `PDCA_VERIFY_BASE` — a verified harness test-isolation fault, non-gating,
  expect it again, do not chase it).
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; the test runs in the
  offline driver suite with stubbed leaves and gates, no tracker, network or container.
- **Test file:** `template/tests/test_flow_adopt_split.py` (new module in the offline
  driver suite; the v5 version, 17 tests, is preserved at this bundle's root for reuse —
  its C4 red→green was reproduced by the adversary). The C4 gate reverts only the
  PRODUCTION hunks and keeps the test (`engine/scripts/run-verify.sh`,
  `--exclude=template/tests/*`), so a new test file earns its red correctly. **Import
  modules, never new symbols** (`from pdca_harness import flow, split, state, waves, cli`;
  reach new names as `flow.<name>`) — a `from pdca_harness.flow import <new helper>`
  raises ImportError on the red leg, which run-verify.sh classifies PDCA-UNVERIFIABLE
  (exit 77), not red. **Exercise through `cli._flow`**, the surface where iterations 4 and
  5 both found parity breaks; the v5 suite's direct `flow.flow` / `flow.flow_ids` calls
  are exactly the hand-picked-call gap that let the CLI short-circuit through.
- **Citations expected:** Do must cite `path:line` on `origin/main` for every change.
  Verified at `f7876f2`: `cli.py:604-608` (single-id COMPLETE short-circuit + `rm -rf`
  hint — actively destructive for a split parent, it would delete the lineage record),
  `cli.py:638-648` (single-id report/exit derived from one state string),
  `cli.py:651-656` + `_report_batch` (batch report/exit derived from a results map);
  `flow.py:367` (`flow`, returns a state string; loop at `:389-410`), `flow.py:776`
  (`_drive_and_act`; `wave_list` once at `:799`, `_point_at_integration` call at `:830`),
  `flow.py:928` (`flow_batch`; re-enumerates only BETWEEN Plan and drive; held-report
  shape at `:968-970`), `flow.py:983` (`flow_ids`; drive set built once at `:1035-1046`,
  terminal filter at `:1041-1043`), `flow.py:659` (`_TERMINAL`), `flow.py:662`
  (`_warn_abandoned`); `waves.py:104` (`conflict_map`), `:140` (`compute_waves`), `:240`
  (`partition_schedulable`); `state.py:44` (`CLOSE_MARKER`); `split.py:47` (`LINEAGE`),
  `:373` (`read_lineage`, the one tolerant reader), `:525` (`accept`).
  **Peer callsites to mirror, not re-derive:** the held-report at `flow.py:968-970`;
  `_point_at_integration` at `flow.py:621` (an adopted child joins the same `(repo,
  base)` integration branch through this call, not a second mechanism);
  `_warn_abandoned`'s not-terminal predicate at `flow.py:662`; the offline fixture at
  `template/tests/test_flow_slice.py:31-56`.
- **Disposition hint:** new-feature

## Motivation

Unchanged from the filing (tracker #449): a split inside a driven flow strands its own
children — the parent goes terminal, the children materialise fully briefed, and the run
never drives them; the planner's runtime prompt documents the limitation instead of the
harness fixing it. Both backstop entries of the size-and-split design (docs 07) end in a
manual restart.

What five iterations added: the adoption mechanics converged and were adversarially
verified, but the **entry-point parity contract** — "`pdca flow 500` and `pdca flow 500
501` do the same thing to the same disk" — broke by a new route each round:

1. iter 1 — `flow_ids` filtered the terminal split parent out of the drive set before
   adoption could see it (fixed);
2. iter 4 — the single-id adoption tail swallowed `PreflightError` inside `_isolate`,
   diverging exit codes (fixed);
3. iter 5 — two more: the CLI short-circuits a single already-COMPLETE split parent
   before `flow.flow` runs (`cli.py:604-608`, printing an `rm -rf` hint that would
   destroy the lineage record), and `flow.flow` discards the adoption tail's results map
   so the entry points return rc 0 vs rc 1 for the same run.

The cause is structural: `flow.flow` returns a *state string*, `flow_ids` returns a
*results map*, and `cli._flow` gates the single-id route on pre-run disk state the batch
route never consults. Parity must hold **by construction** — one drive path, one results
map, one report/exit derivation — before adoption is re-landed on top of it.

## Design

Split into two children (see `Ordering note:`); the v5 design — detect via
`read_lineage`, validate via `partition_schedulable`, splice after the current wave,
report real wave indices, run-wide budget pool, bounded recursion, transitive
lineage-only scope, stale-split recovery per iteration-1 RULING (b) — is carried into the
adoption child unchanged in substance; the v5 patch and test suite are preserved in
`iteration-v5/` and at the bundle root as reference material the child briefs may cite.

## Alternatives considered

- **Sixth iterate-do on the monolith** — rejected by the v5 sign-off: three distinct
  parity-break routes show per-divergence patching does not converge; the size backstop
  (4 rounds vs threshold 2) concurs.
- **Scale the documented parity claim back to what the code guarantees** — the sign-off's
  fallback; rejected as primary: the claim is the operator contract the docs and planner
  prompt already make, so prefer making it true.
- Earlier alternatives (disk re-enumeration between waves; parsing `build-notes.md`
  prose; keeping the restart; adopting into the current wave) — rejected in v1–v5 for the
  reasons recorded in `iteration-v5/brief.md`; unchanged.

## Impact & compatibility

- Recovery semantics per iteration-1 RULING (b): a run handed an id whose bundle is
  **already** terminal on a split adopts its stranded children — deliberate recovery, and
  both CLI shapes do it identically.
- A run can do more work than its id list literally named — only along the parent→child
  lineage edge, announced per adoption; the results map gains entries for adopted
  children (and for the single-id shape, the report/exit now derive from that map).
- The `--accept` hint stays, correct for a split accepted outside any running flow.
- Rendered instances pick this up on their next `copier update`; no config key changes.

## Open questions

1. Child (a)'s exact mechanism — thin-wrapper `flow.flow` over `flow_ids` vs routing in
   `cli._flow` — is Do's call within (a)'s brief, provided parity is by construction and
   tested through `cli._flow`.
2. Whether `flow_batch`'s drive phase also adopts (v5 said yes; least valuable of the
   three) — keep, unless it complicates (b)'s splice.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be marked ready
before sign-off accepts.
