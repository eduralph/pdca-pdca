# Design proposal — issue 449 / flow-adopts-split-children-mid-run

> The Plan artifact for this slice. Do reads ONLY this file and implements it; Check runs
> the regular gated check on the code. The `- **Label:** value` lines are parsed by the
> driver; the prose `##` sections are the design rationale.

- **Slug:** flow-adopt-split-children
- **Kind:** enhancement (design proposal)
- **Goal:** a split that happens *inside* a driven flow no longer strands its own
  children. When a bundle in the drive set reaches `close-disposition = split`, the run
  enumerates that bundle's children, validates them with the tolerance the resume path
  already uses, splices them into the remaining waves, and says so — instead of ending
  with the parent terminal, the children sitting PLANNED, and the operator restarting by
  hand with `pdca flow <child-ids>`.
- **Success criterion:** a `flow.flow_ids(cfg, ["<parent>"])` (and a single-id
  `flow.flow`) whose Plan/re-plan beat splits the parent drives that parent's children to
  a terminal state **within the same call** — in a wave AFTER the one the parent was in,
  honouring their own `Depends on` / `Conflicts with`, counted against the same run's
  `max_passes` budget, each adoption announced on stderr as `issue_<parent> split →
  adopted children issue_<a>, issue_<b> into wave <k+1>`. A child whose dependency cannot
  be resolved is **held loudly and the run continues**, never aborts. An explicit-id flow
  adopts only children of the ids it was given (transitively) and never widens into a disk
  sweep. Demonstrable by C4-verify on the patch alone.
- **Falsifiability:** RED is producible on the ordinary offline driver suite — `cd
  template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split`, which is
  what `engine/scripts/run-verify.sh` runs for a `template/tests/*.py` test. With all six
  leaves stubbed (fixture shape at `template/tests/test_flow_slice.py:31-56`) and a leaf
  patched to perform the split mid-run — write the parent's `close-disposition`,
  `build-notes.md` and lineage record, and materialise two child bundles with briefs —
  pre-fix the call returns with the children still PLANNED and never driven (`flow_ids`
  builds its bundle list once at `flow.py:961-974`; `_drive_and_act` computes
  `wave_list = waves.compute_waves(cfg, bundles)` once at `flow.py:727`), so an assertion
  that both children reached COMPLETE fails. Post-fix it passes. No tracker, network, `gh`
  or container: the split is simulated on disk exactly as `pdca split --accept` leaves it.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 456, 453
- **Ordering note:** **Re-pointed from 448 to 456 at Plan (2026-08-08).** The build-on is
  the machine-readable **children record** (`split-lineage.json`, `role: "parent"`) that
  step 1 below reads instead of parsing child ids out of the parent's prose
  `build-notes.md`; the two filings were made together and name each other for exactly
  this. That record was 448's deliverable when this brief was written, but 448 has since
  been **split** into 456/457/458/459 (`results/issue_448/split-proposal.md`, accepted —
  `close-disposition = split`). 448 now lands NO patch and reaches COMPLETE with an empty
  wave fold, so depending on it would hand this bundle nothing and build step 1 against a
  record that does not exist. **456** (`split-lineage-record`) is the child that owns the
  record *and its schema*, so the dependency moves there; 457/458/459 are consumers of the
  same record and are not prerequisites of this slice. 453 is the sequencing decision: it
  restructures the same `_drive_wave` pass loop and the same `flow_ids` / `flow` entry
  points this slice rewrites, and it is the smaller, purely-corrective change, so it lands
  in an earlier wave and this bundle builds on its accepted result rather
  than colliding with it on `flow.py`. **Human to confirm:** to land this first instead,
  drop 453 from `Depends on` — issue 453's own brief declares `Conflicts with: 449` and
  `waves.conflict_map` is symmetric (`waves.py:104-121`), so the pair still lands in
  separate waves, ordered name-lower-first (449 before 453). The conflict is deliberately
  declared on 453's side only: repeating it here would add a third structural churn point
  to this brief's size estimate for an edge the scheduler already has.
- **Surfaces:** data
- **Difficulty:** high — it changes the drive-set lifecycle at all three entry points
  (`flow.flow`, `flow.flow_ids`, `flow.flow_batch`'s drive phase) and inside
  `_drive_and_act`'s run-scoped wave/integration state, the most load-bearing loop in the
  driver; a reviewer must hold the wave/fold/publish interaction in view.
- **Scope:** adopt the children of a bundle that goes `close-disposition = split` while it
  is in the drive set — detect, validate, splice, report (see *Design*) — implemented in
  `_drive_and_act` so all three entry points inherit it.
  / out of scope: changing *why* recursive splits happen (that is 448 — this slice must
  merely not enable an infinite one); a disk sweep in `flow_ids` (the distinction from the
  CSV sweep at `flow.py:882-896` is deliberate and stays); the `--accept` hint that prints
  `pdca flow <child-ids>` (still right for a split accepted outside a running flow — it
  stays); `waves.compute_waves` / `partition_schedulable` semantics (reused as-is); the
  split command, `split.accept`, or the lineage schema (448 owns it); publish/fold
  semantics beyond pointing an adopted child at the same per-target integration branch
  through the existing reconciliation.
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; the test runs in the
  offline driver suite with stubbed leaves and gates, and needs no tracker, network or
  container.
- **Test file:** `template/tests/test_flow_adopt_split.py` (new module in the offline
  driver suite). The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`), so a new test file earns
  its red correctly. **Import modules, never new symbols:** write `from pdca_harness
  import flow, split, state, waves` and reach anything this patch adds as `flow.<new_name>`.
  A `from pdca_harness.flow import <new helper>` raises ImportError on the red leg, which
  run-verify.sh classifies as PDCA-UNVERIFIABLE (exit 77) rather than a red — the test
  would then prove nothing. Exercise adoption through the real `flow.flow_ids` /
  `flow.flow` entry points, never by calling an internal helper directly: the defect is
  that the *entry points* freeze their drive set.
- **Citations expected:** Do must cite `path:line` on `origin/main` for every change.
  Verified at `b95aa58`: `flow.py:704-850` (`_drive_and_act` — `wave_list` computed once at
  `:727`, `_point_at_integration` at `:758`, the fold at `:805-843`); `flow.py:911-976`
  (`flow_ids`, drive set built once at `:961-974`); `flow.py:314-372` (single-id `flow`,
  whose loop exits when the parent derives terminal); `flow.py:856-905` (`flow_batch`,
  which re-enumerates only BETWEEN Plan and drive, `:877-896`); `flow.py:602-636`
  (`_TERMINAL`, `_warn_abandoned`); `waves.py:240-296` (`partition_schedulable`),
  `waves.py:140-196` (`compute_waves`); `state.py:44` (`CLOSE_MARKER`); `split.py:429-472`
  (where `accept` marks the parent and writes the breadcrumb); `driver.py:213`
  (`_close_class`).
  **Peer callsites to mirror, not re-derive:**
  * `flow.py:892-899` — the resume path's `waves.partition_schedulable` + per-name "held
    this run — <reason>; left in-flight" report. Adopted children go through **this exact
    tolerance and this exact reporting shape**; an unresolvable dependency holds, never
    aborts;
  * `flow.py:754-759` — `_point_at_integration(integ, runnable)`, the existing per-target
    reconciliation. An adopted child joins a later wave and is pointed at the same
    `(repo, base)` integration branch through this call, not a second mechanism;
  * `flow.py:609-636` — `_warn_abandoned`'s "not terminal" predicate and resume hint: an
    adopted child left un-terminal must be reported by the same code, so a batch stays
    explainable as one unit;
  * `template/tests/test_flow_slice.py:31-56` — `_stub_config`, the offline fixture the new
    test mirrors (all six leaves stubbed, hermetic repo checkout inside the tmp root).
- **Disposition hint:** new-feature

## Motivation

A split inside a driven flow strands its own children: the parent goes terminal
(`close-disposition = split`, `split.py:461`), the children materialise on disk fully
briefed — and the run that caused all of this never drives them. The planner's own runtime
prompt documents the limitation instead of the harness fixing it (`leaves.py:581-586`):

> "A CSV-DRIVEN batch run re-enumerates every in-flight bundle from disk after the Plan
> beat, so it picks the children up […] EVERY OTHER SHAPE, including an explicit id list
> like `pdca flow 500 501`, drives exactly the ids it was given and never looks for new
> ones; `--accept` prints the `pdca flow <child-ids>` command that drives them."

Where the drive set freezes, verified at `b95aa58`:

* `flow.flow_ids` builds `bundles` from exactly the listed ids, once (`flow.py:961-974`),
  then hands the fixed list to `_drive_and_act`.
* `flow.flow` (single id) loops on the one bundle (`flow.py:335-354`); when the Plan
  session splits it, the parent derives terminal and the loop exits. The children sit
  PLANNED, undriven.
* `_drive_and_act` computes `wave_list` once, up front (`flow.py:727`). Even the CSV batch
  — the one shape that picks children up — only re-enumerates *between* Plan and drive
  (`flow.py:877-896`). A split arriving during the drive phase (the documented Entry-B
  path: `iterate-plan` at sign-off → re-plan → split) is adopted by **no** mode.

So both backstop entries of the size-and-split design (docs 07, "Size & split") end in a
restart: the mechanism that decomposes work mid-flight cannot hand the pieces back to the
flight it is part of.

## Design

All four steps live in `_drive_and_act` (`flow.py:704-850`), the shared body of both batch
entry points, so `flow_ids` and `flow_batch`'s drive phase inherit them; the single-id
`flow` gets the same behaviour via step 5.

**1. Detect.** After a wave is driven (`flow.py:759`) — and after the serial Plan pre-pass
inside `_build_all`, where a re-plan can split a bundle — examine the just-terminal bundles
for `close-disposition == "split"` (`state.py:44`, `split.py:461`) and read their children
from the parent's `split-lineage.json` (`role: "parent"`, `children: [...]`, written by
448). A read, not a prose parse: the child ids live in `build-notes.md` prose today
(`split.py:453-456`), which is not a contract. A parent with the marker but no readable
children record is reported and skipped — never a crash, never a guess.

**2. Validate.** Resolve each child id to its bundle, drop those that do not exist or are
already terminal / UNPLANNED (the filters `flow_ids` applies at `flow.py:965-970`), then
run the survivors together with the run's remaining bundles through
`waves.partition_schedulable` (`waves.py:240`) — the tolerance the batch resume path
already uses. A child with an unresolvable dependency or in a cycle is **held**, reported
in the existing "held this run — <reason>; left in-flight" form (`flow.py:897-899`), and
the run continues.

**3. Splice.** Recompute the remaining waves with the adopted children included, honouring
their `Depends on` / `Conflicts with`. Constraints that make this safe inside
`_drive_and_act`'s run-scoped state:

* children join **after the current wave** — never the wave being driven, never an earlier
  one that has already folded;
* they are pointed at the same per-target integration branch through the existing
  `_point_at_integration(integ, runnable)` (`flow.py:754-758`), not a new mechanism, so a
  child builds on the base its siblings' accepted work folded onto;
* they count against the **same run's** `max_passes` budget rather than resetting it, and
  they join the `bundles` set the final `_sweep_quietly`, results map and `_warn_abandoned`
  already cover (`flow.py:845-850`), so an adopted child left un-terminal is named with a
  resume hint like any other;
* adoption is **bounded**: an adopted child can itself split, so re-adoption shares the
  run's existing iteration budget — no unbounded recursion. (448 addresses *why* recursive
  splits happen; this slice must merely not enable an infinite one.)

**4. Report.** Loudly, on stderr, one line per adoption: `flow: issue_500 split → adopted
children issue_501, issue_502 into wave 2`. A batch must remain explainable as one unit.

**5. The single-id path.** `flow.flow` (`flow.py:314-372`) loops on one bundle and exits
when it derives terminal. A split there is the same event: on exit, if the bundle is
terminal with `close-disposition = split` and has a readable children record, drive its
children through the same adoption path (a fresh drive set for the remainder of this run)
before the publish/Act tail. `--no-publish` and `do_act` semantics are unchanged.

**Scope boundary that must hold by construction:** an explicit-id flow adopts only children
**of the ids it was given**, transitively. It never globs `results/`. The difference
between `flow_ids` and the CSV sweep (`flow.py:979-983`) is deliberate and stays.

## Alternatives considered

* **Re-enumerate the bundle root between waves.** One line, and wrong: it silently turns
  every explicit-id flow into a disk sweep, adopting unrelated in-flight bundles nobody
  asked for. The lineage edge keeps adoption scoped to the run's own descendants.
* **Parse child ids out of the parent's `build-notes.md`.** Works today, but that
  breadcrumb is prose written for a human (`split.py:453-456`) and would become a de-facto
  format with no version. 448 ships the machine-readable record for this consumer.
* **Keep the restart and improve the message.** The status quo (`--accept` already prints
  the command). It fails the Entry-B path — `iterate-plan` at sign-off → re-plan → split —
  where the operator did not initiate the split beat and the batch silently drops to a
  partial result.
* **Adopt into the CURRENT wave.** Cheaper, but a wave's members must be mutually
  independent and its fold happens once at its end (`flow.py:800-843`); a child arriving
  mid-wave would build on a base about to move.

## Impact & compatibility

* **Behaviour changes when a split is adoptable** — corrected at Iteration 1 by the
  sign-off RULING (b) below, which supersedes this bullet's original "only when a split
  happens during a run". With no split anywhere in the drive set (nor among the ids named),
  `_drive_and_act` computes the same waves and drives the same bundles as today. But a run
  handed an id whose bundle is **already** terminal on a `split` adopts its stranded
  children — deliberate recovery for a run that stopped before its children were driven —
  and both entry points do it, so `pdca flow 500` and `pdca flow 500 501` behave identically
  on identical disk state.
* **A run can now do more work than its id list literally named** — deliberately, only
  along the parent→child edge, announced per adoption. The results map returned by
  `flow_ids` / `flow_batch` gains entries for adopted children.
* **The `--accept` hint stays**, correct for a split accepted outside any running flow.
* **Depends on 448's artifact.** Without a readable children record a parent is reported
  and skipped, so this degrades to today's behaviour rather than failing — but the feature
  is only useful once 448 has landed, which is why it is scheduled behind it.
* **Rendered instances** pick this up on their next `copier update`; no config key is added
  and none changes meaning.

## Open questions

1. **Adopt in `flow_batch`'s drive phase too?** This brief says yes — one run, one
   explanation — though it is the least valuable of the three entry points (its next
   invocation's glob would pick the children up) and could be dropped if it complicates the
   splice.
2. **Should an adopted child be publishable in the same run?** It will be, by falling out
   of the ordinary per-wave publish. This brief keeps that: the human still signs it off,
   and a draft PR is not a merge.
3. **Ordering against 453** — see `Ordering note:`; confirm or swap at Plan.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on two implementation defects; the adoption mechanism itself (detect/validate/splice/report, transitive + bounded traversal) is sound — keep it. 1) Run budget: `max_passes` must be a RUN-WIDE cap, but `_drive_and_act` hands the full budget to every wave (`template/src/pdca_harness/flow.py:1045`) — `max_passes=2` completed the parent plus two child waves. Enforce the cap across all waves including adopted ones, and add the missing run-budget boundary test to `template/tests/test_flow_adopt_split.py` (the T5 gap that let this through). 2) Adoption announcement: report each child's REAL wave index from the recomputed schedule, not the hardcoded parent-index+1 (`flow.py:864-865`, `:894`) — the existing test asserts "into wave 1" for a child actually driven in wave 2; fix both report sites and the assertions. 3) RULING (b) on stale-split adoption: adopting stranded children of a parent split in an EARLIER run is accepted as intended recovery behavior — do NOT restrict adoption to this-run splits. Instead make both entry points consistent (`flow.flow` single-id and `flow.flow_ids` must both adopt on identical disk state; today `flow_ids` filters the terminal parent out before adoption runs, `flow.py:1258-1260`) and correct the brief/docs claim "behaviour changes only when a split happens during a run" to state the recovery semantics honestly. 4) The T3 gate red (11 failures in `template/tests/test_verify_base.py` — `PDCA_VERIFY_BASE` leaking into its subprocesses) is a pre-existing harness test-isolation fault hitting every stacked bundle; NOT this patch's defect, out of scope. Do not chase it; expect the same non-gating red on the rebuild.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Decide whether to accept the contribution metadata without an independent rerun — `commit-msg.txt` and `pr-description.md` were not supplied, so the reported T4 green is provisional; affected-path merged-history plus closed/rejected-PR checks found antecedents #354/#362/#460 but no duplicate adoption patch.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Human chose one more iterate-do (consciously overriding the size backstop's iterate-plan recommendation) to see if the slice converges. The adoption mechanism is sound — C4 red→green reproduced and mutation-tested by the adversary; keep it. Fix the adversary's implementation findings, do not re-architect: 1) Budget-exhaustion message on the single-id path: `flow.flow` prints the adoption tail's remainder/local wave index ("0 pass(es) over 0 wave(s)") instead of the run's real totals (`template/src/pdca_harness/flow.py:1133-1136`, remainder handed at `flow.py:450`); `flow_ids` is correct. Add a test asserting the message on the single-id path. 2) Adoption-announcement wave numbering diverges between entry points on identical disk (`flow.py:936` builds `wave_of` from the local `wave_list`): `flow.flow` logs waves 0/1 where `flow_ids` logs 1/2, while docs claim the entry points do the same thing (`docs/07-crosscutting.md:259-260`). Make the numbering consistent (or document the index as within-the-adopted-schedule) and fix the test, which currently enshrines both schemes (`template/tests/test_flow_adopt_split.py:244-245` vs `:260-261`). 3) Duplicate child id in a hand-edited lineage record is adopted twice (`flow.py:809-837`, no dedup at `:837`): add a `seen` set in the id loop and a test. 4) Close the Entry-B coverage gap on the single-id path (iterate-plan at sign-off → re-plan → split): stub `leaves.run_signoff` (not only `run_signoff_batch`) so the brief's motivating case is exercised through `flow.flow` — the exact path findings 1 and 2 live on. Also surfaced but a fitness call, not a required code change: a recovery run naming only a terminal split parent sizes its pass pool as one wave (`flow.py:1109`), so the parent-id route buys less budget than naming the children — at minimum document it for the operator. T3 red (11 failures in test_verify_base.py under inherited PDCA_VERIFY_BASE) remains the pre-existing isolation fault, out of scope — expect the same non-gating red on the rebuild.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Human chose iterate-do (second conscious override of the size backstop's iterate-plan recommendation). The adoption mechanism is proven — C4 red→green reproduced and mutation-tested (7/7 mutations caught) — keep it unchanged. Fix ONE narrow defect, do not re-architect: the single-id adoption tail is wrapped in `_isolate`, which swallows `PreflightError` (`template/src/pdca_harness/flow.py:451`; `_isolate` contains every Exception at `flow.py:~640`), so on byte-identical disk state `pdca flow 500` exits 0 with children still PLANNED where `pdca flow 500 601` exits 1 on a lane-preflight failure (`flow.py:1209`, caught by `cli.py:652-656`). This contradicts the entry-point-consistency contract the patch itself documents (`docs/07-crosscutting.md:259-260`, `flow.py:1113-1115`) and Iteration 1's RULING (b). Fix: re-raise `PreflightError` (and anything else meant to abort a run) out of the tail — or scope `_isolate` to the detect/validate step rather than the whole `_drive_and_act` — and add a test in `template/tests/test_flow_adopt_split.py` where the tail raises, asserting both entry points produce identical exit behavior on identical disk; the suite currently has no case where the tail raises at all. T3 red (11 failures in test_verify_base.py under inherited PDCA_VERIFY_BASE) remains the verified pre-existing isolation fault, out of scope — expect the same non-gating red on the rebuild.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 5 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the adversary's two behavioral refutations: (1) the CLI short-circuits a single already-COMPLETE split parent before flow.flow runs (`cli.py:605-608`), so `pdca flow 500` does nothing — no adoption, children stay PLANNED, and it prints an `rm -rf` hint that would destroy the lineage record — while `pdca flow 500 999` on the same disk adopts; (2) the entry points still report the same run differently (rc 0 vs rc 1) because flow.flow discards the adoption tail's results map (`flow.py:473-476`). This is the THIRD distinct route by which the "both entry points agree" contract has broken (iter 1: terminal-parent filter; iter 4: swallowed PreflightError; now: CLI short-circuit + exit-code divergence). The cause is structural — flow.flow returns a state, flow_ids returns a results map, and cli._flow gates the single-id route on pre-run disk state the batch route never consults — so per-divergence patching will not converge; the size backstop (4 rounds vs threshold 2, overridden twice) confirms the slice is oversized. Re-plan should SPLIT, not rebuild: the adoption mechanics (detect/validate/splice/report, budget pool, recursion bound) are proven — C4 red→green reproduced, 10/14 mutations caught, splice/recursion/budget could not be refuted — keep them. Candidate split: (a) a structural entry-point-unification slice (route the single-id CLI path through flow_ids / a single results-map return, so parity holds by construction, tested THROUGH cli._flow, not hand-picked flow calls); (b) a small slice for the surviving untested guards (terminal-in-predicate, lineage path-escape, held-child exclusion from results, drive-set dedup) — or fold them into (a)'s test surface. Alternatively scale the documented parity claim back to what the code guarantees, but prefer making the claim true. T3 red remains the pre-existing PDCA_VERIFY_BASE isolation fault (clean-env suites green for reviewer and adversary) — non-gating, out of scope, expect it again.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v5/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
