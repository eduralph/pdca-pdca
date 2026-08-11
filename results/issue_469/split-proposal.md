<!-- pdca:split-proposal v1 -->
# Split proposal — issue_469

## Wave sketch

Two children. child-2 depends on child-1 (both edit `flow.py` / `cli.py`; the recovery +
reporting work builds on the adoption core). Both carry `Depends on (merged): 468` — the
unified drive path they build on is COMPLETE but its PR (#470) is unmerged, and the #186
out-of-batch merge-gate is the only mechanism that carries an out-of-batch prereq's diff
into their base: **merge PR #470 before driving the children.**

Origin: #469 v3 converged on correctness (C4 red→green reproduced independently, 23/26 red
pre-fix → 26/26 green; the adversary could not refute splice, recursion bound, wave
indices, path-escape guard, budget hand-down, or fold boundary) but hit the size backstop
(111 KB > 100 KB, 2 rounds spent). The split carves the converged v3 patch
(`results/issue_469/iteration-v3/patch.diff`, suite preserved at
`results/issue_469/test_flow_adopt_split.py`) into two shippable outcomes; the mechanics
carry over, they are not re-derived. Sign-off carry-forwards (1)–(3) are distributed:
(3) same-wave dedup test → child-1; (1) budget pre-emption and (2) single-id stdout
reporting → child-2. Carry-forward (4) — T4 has passed three consecutive iterations
without reviewer-reproducible evidence (`commit-msg.txt` / `pr-description.md` not in the
reviewer's inputs) — is a review-input-assembly gap orthogonal to adoption: **not a child;
file it as its own tracker issue.**

<!-- pdca:child child-1 -->
# flow: adopt split children mid-run — the adoption core on the unified drive path

- **Slug:** flow-adopt-core
- **Kind:** enhancement
- **Defect / goal:** a split that happens inside a driven flow strands its own children
  (tracker #449 → #469): the parent goes terminal (`close-disposition = split`), the
  children materialise fully briefed, and the run never drives them — the operator
  restarts by hand with `pdca flow <child-ids>`. #469 v3 built and converged the full
  adoption feature but was split on the size backstop; this child re-lands the **mid-run
  adoption core** — detect / validate / splice / report on the unified single drive path
  (#468) — by CARVING it out of the converged v3 patch
  (`results/issue_469/iteration-v3/patch.diff`; 26-test suite preserved at
  `results/issue_469/test_flow_adopt_split.py`), not re-deriving it. Terminal-parent
  recovery and the operator-facing reporting/budget refinements are the sibling child's.
- **Success criterion:** exercised **through `cli._flow`** on byte-identical disk state:
  a run whose Plan/re-plan beat splits a drive-set bundle drives that bundle's children
  to a terminal state within the same call — in a wave AFTER the parent's, honouring
  their `Depends on` / `Conflicts with`, counted against ONE run-wide `max_passes`
  budget across original AND adopted waves (pool sized off the pre-adoption schedule —
  the converged v3 mechanics; live re-sizing is the sibling child's), each adoption
  announced on stderr with the child's REAL wave index from the recomputed schedule. A
  child with an unresolvable dependency is held loudly in the existing held-report
  shape, excluded from the results map, and the run continues — never aborts. Adoption
  is lineage-scoped and transitive (only descendants of the ids given), never a disk
  sweep; an adopted child that itself splits is re-adopted within the same shared budget
  — bounded, no recursion reset. Guards proven by test, not just present: a split-marked
  but NON-terminal parent (e.g. sign-off recorded `iterate-do`) does NOT have its
  children adopted; a parent whose lineage record is unreadable is reported and skipped,
  never a crash; a lineage child id that escapes the bundle root (e.g. `"../../etc"`) is
  skipped with a report; an id already in the run's drive set is not adopted twice —
  dedup against the batch, against a duplicate id within one record, AND against a child
  already taken by another parent adopted in the SAME wave (two parents splitting in one
  wave, the second's record also naming the first's child — the #469-v3 adversary's
  unpinned-`taken` mutation; the docstring's test citation must name this test).
  Demonstrable by C4-verify on the patch alone.
- **Falsifiability:** RED on the offline driver suite — `cd template && PYTHONPATH=src
  python3 -m unittest tests.test_flow_adopt_split`, the invocation
  `engine/scripts/run-verify.sh` uses for a `template/tests/*.py` test. With all six
  leaves stubbed (fixture shape at `template/tests/test_flow_slice.py:33`,
  `_stub_config`), a leaf patched to split the parent mid-run, and the fixture built
  with the production `split.accept` (`split.py:525`): pre-fix (post-#470 `main`, no
  adoption) the children stay PLANNED after the call returns — `_drive_and_act` computes
  `wave_list` once (`flow.py:868` on the #468 branch) and the drive set is built once —
  so assertions that children reached COMPLETE fail; post-fix green. The guard tests are
  red pre-fix by the same route. No tracker, network, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on (merged):** 468
- **Ordering note:** builds on #468's unified results-map drive path — adoption is
  implemented once on the shared path so `flow_batch` and both `flow_ids` shapes inherit
  it from one implementation; landing it on forked entry points is what produced #449's
  five-iteration divergence chase. 468 is COMPLETE but out-of-batch and its PR #470 is
  unmerged; per the driver's #186 rule nothing carries an out-of-batch prereq's diff
  into the base, so the merged-gate is the correct field: merge PR #470, then drive.
- **Surfaces:** data
- **Difficulty:** high — the adoption splice lives inside `_drive_and_act`'s run-scoped
  wave/fold/integration state, the most load-bearing loop in the driver; a reviewer must
  hold the wave/fold/publish/budget interaction in view.
- **Scope:** adopt the children of a bundle that goes `close-disposition = split` while
  in the drive set — detect (read `split.read_lineage`; a parent with the marker but no
  readable record is reported and skipped, never a crash), validate
  (`waves.partition_schedulable` tolerance; held children reported in the existing
  "held this run — <reason>; left in-flight" shape and EXCLUDED from the results map),
  splice (children join after the current wave; pointed at the same per-target
  integration branch via the existing `_point_at_integration`; one run-wide `max_passes`
  pool across original AND adopted waves, sized as converged in v3; adopted children
  join the set `_warn_abandoned` / final sweep cover), report (stderr announcements
  with real wave indices) — on the unified drive path, so every CLI shape inherits it
  from one implementation. Includes the same-wave two-parents dedup test (v3 carry-
  forward 3) and the corrected docstring citation, and the ancillary
  `template/tests/test_verify_base.py` environment cleanup the v3 review accepted as
  discharging an iteration carry-forward, not scope expansion.
  / out of scope: **terminal-parent recovery** (a run handed an id ALREADY terminal on a
  split — the pre-run short-circuit stays for now; sibling child) and **shape-parity
  assertions against that recovery path**; **single-id stdout reporting of adopted
  dispositions** and **budget re-sizing on adoption** (sibling child); changing why
  recursive splits happen (#448's line — merely never enable an infinite one); a disk
  sweep in `flow_ids` (the distinction from the CSV sweep is deliberate and stays); the
  `--accept` hint printing `pdca flow <child-ids>` (still right for a split accepted
  outside a running flow); `waves.compute_waves` / `partition_schedulable` semantics
  (reused as-is); the split command, `split.accept`, or the lineage schema (#456 shipped
  it); publish/fold semantics beyond the existing reconciliation.
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; offline driver
  suite with stubbed leaves, no tracker, network or container.
- **Test file:** `template/tests/test_flow_adopt_split.py` (new module; the mid-run and
  guard subset of the preserved 26-test v3 suite — drive **through `cli._flow`**, build
  fixtures with the production `split.accept` — PLUS the same-wave two-parents dedup
  test the v3 adversary showed missing: mutation `known=batch_names | taken` →
  `known=batch_names` must fail it). The C4 gate reverts only the PRODUCTION hunks and
  keeps the test (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`).
  **Import modules, never new symbols** (`from pdca_harness import cli, flow, split,
  state, waves`; reach new names as attributes) — a named import of a new helper is
  ImportError on the red leg → PDCA-UNVERIFIABLE (exit 77), not red.
- **Citations expected:** Do must cite `path:line` on the merged base (post-#470 `main`;
  line numbers below verified on `origin/enhancement/468-flow-entrypoint-parity` and
  identical after a clean merge): `flow.py:845` (`_drive_and_act`; `wave_list` once at
  `:868`; `_point_at_integration` call at `:899`), `flow.py:630`
  (`_point_at_integration`), `flow.py:668` (`_TERMINAL`), `flow.py:731`
  (`_warn_abandoned`), `flow.py:1039` (the held-report shape to mirror), `flow.py:997`
  (`flow_batch`), `flow.py:1052` (`flow_ids`); `waves.py:104` (`conflict_map`), `:140`
  (`compute_waves`), `:240` (`partition_schedulable`); `state.py:44` (`CLOSE_MARKER`);
  `split.py:47` (`LINEAGE`), `:373` (`read_lineage`), `:525` (`accept`). **Peer
  callsites to mirror, not re-derive:** the held-report at `flow.py:1039`;
  `_point_at_integration` at `flow.py:630` (adopted children join the same `(repo,
  base)` integration branch through this call, not a second mechanism);
  `_warn_abandoned`'s not-terminal predicate at `flow.py:731`;
  `template/tests/test_flow_slice.py:33` for the offline fixture. **Reference
  implementation to carve from:** `results/issue_469/iteration-v3/patch.diff` and the
  preserved suite `results/issue_469/test_flow_adopt_split.py`.
- **Disposition hint:** new-feature
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
# flow: adopt stranded children of an already-terminal split, and report/budget adoption honestly

- **Slug:** flow-adopt-recovery-reporting
- **Kind:** enhancement
- **Defect / goal:** with the adoption core landed (child-1), two gaps remain from #469
  v3. **Recovery:** a run handed an id whose bundle is ALREADY terminal on a split does
  not adopt its stranded children — the pre-run short-circuit swallows it (#449
  iteration-1 RULING (b)), so a crashed or interrupted run's brood still needs a
  hand-typed restart. **Honesty:** two adversary-reproduced findings from v3 — (a) the
  run-wide pass pool is sized off the pre-adoption schedule, so an adopted child can
  starve an id the operator explicitly typed (reproduced: named `810` left PLANNED, rc 1,
  after adoption inserted `601` ahead of it); (b) the single-id CLI shape can print
  `COMPLETE` on stdout and exit 1 without ever naming on stdout the adopted bundle that
  caused the failure — the documented `state<TAB>path` machine contract reads success
  from a failed run. Carve recovery from the converged v3 patch
  (`results/issue_469/iteration-v3/patch.diff`); the budget and stdout refinements are
  new, decided at Plan (below).
- **Success criterion:** exercised **through `cli._flow`** on byte-identical disk state:
  (1) **recovery** — a run handed an id whose bundle is ALREADY terminal on a split
  adopts its stranded children (lineage-scoped, transitive, same guards as the core) —
  no pre-run short-circuit swallows it; the mid-run and recovery shapes produce the
  same child states, stderr announcements and exit code on equivalent disk state.
  (2) **budget** — the run-wide pool is RE-SIZED when adoption grows the schedule
  (per-wave allowance × live wave count, recomputed at splice), so the v3 adversary's
  starvation scenario now completes: bundles `500` (splits into `601`), `810` briefed
  `Depends on: 500` + `Conflicts with: 601`, `pdca flow 500 810 --max-passes 2`, `601`
  costing two passes → `810` reaches COMPLETE; the budget stays bounded because
  adoption itself is bounded (the recursion guard — no reset). (3) **stdout** — the
  single-id shape never reports success it did not deliver: when adopted children exist,
  their dispositions are printed as additional `state<TAB>path` lines (or one summary
  line naming what made the rc non-zero), so stdout and the exit code cannot disagree;
  a caller reading stdout of a failed run sees the bundle that failed. Demonstrable by
  C4-verify on the patch alone.
- **Falsifiability:** RED on the offline driver suite — `cd template && PYTHONPATH=src
  python3 -m unittest tests.test_flow_adopt_recovery` (same
  `engine/scripts/run-verify.sh` route as child-1). Pre-fix — child-1's accepted result
  as base (in-batch wave fold; or post-merge `main` once child-1's PR lands): the
  recovery tests fail because the pre-run short-circuit leaves an already-terminal
  parent's children PLANNED; the budget test fails exactly as the v3 adversary
  reproduced (`810` PLANNED, rc 1, "pass budget is spent"); the stdout test fails
  because the single-id shape prints exactly one `COMPLETE` line while exiting 1
  (adversary-reproduced on the v3 patch, whose mechanics child-1 carries). Post-fix
  green. No tracker, network, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** child-1
- **Depends on (merged):** 468
- **Ordering note:** builds on child-1's adoption core — recovery reuses its detect /
  validate / splice / report machinery, and both edit `flow.py` / `cli.py`, so the wave
  fold must give this bundle child-1's diff. 468's merge-gate is inherited for the same
  #186 reason as child-1 (merge PR #470 before driving).
- **Surfaces:** data
- **Difficulty:** medium — recovery, budget re-sizing and stdout reporting sit on the
  core child-1 lands; the touched surface is the entry gate (`cli._flow` pre-run path),
  the pool arithmetic, and `_report_single` — narrower blast radius than the splice
  itself, but still inside the drive loop's state.
- **Scope:** (1) remove the pre-run short-circuit for an id already terminal on a split:
  route it through the same lineage-scoped adoption the core uses, with identical
  guards, announcements and results-map semantics; (2) re-size the run-wide pass pool
  when adoption grows the schedule (allowance × live wave count at splice) — the Plan
  decision resolving v3 carry-forward (1) in favour of re-sizing over named-first
  service, which would fight the dependency scheduler's ordering; (3) make the
  single-id stdout shape name adopted children's dispositions (or a one-line summary of
  what made the rc non-zero) so the documented `state<TAB>path` contract and the exit
  code cannot disagree.
  / out of scope: the adoption core's detect/validate/splice/report mechanics (child-1,
  reused as-is); any change to the affirmed policy that held children are excluded from
  the results map and compatible with rc 0 (§6 Validation ticked at v3 sign-off); a disk
  sweep in `flow_ids`; `waves.compute_waves` / `partition_schedulable` semantics; the
  split command, `split.accept`, or the lineage schema; publish/fold semantics beyond
  the existing reconciliation; the T4 reviewer-evidence gap (v3 carry-forward 4 — its
  own tracker issue, not this bundle).
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; offline driver
  suite with stubbed leaves, no tracker, network or container.
- **Test file:** `template/tests/test_flow_adopt_recovery.py` (new module; drive
  **through `cli._flow`**, build fixtures with the production `split.accept`, reuse the
  child-1 fixture idiom. Must include: terminal-parent recovery red→green; mid-run vs
  recovery shape-parity on states/announcements/rc; the starvation scenario red→green;
  the single-id stdout/rc-agreement test). The C4 gate reverts only the PRODUCTION
  hunks and keeps the test. **Import modules, never new symbols** — a named import of a
  new helper is ImportError on the red leg → PDCA-UNVERIFIABLE (exit 77), not red.
- **Citations expected:** Do must cite `path:line` on the wave base (child-1's accepted
  result; anchors below verified on `origin/enhancement/468-flow-entrypoint-parity` and
  will shift under child-1's diff — cite the post-fold positions): the pre-run
  short-circuit in `cli._flow` / `flow_ids` (`flow.py:1052` region pre-child-1);
  `_report_single` in `cli.py` (the `state<TAB>path` contract — v3 located it at
  `cli.py:669-670` on the patched tree); the pool sizing and spend check child-1 lands
  (v3 positions `flow.py:1216` / `:1236` on the patched tree); `_TERMINAL`
  (`flow.py:668`); `split.read_lineage` (`split.py:373`). **Peer callsites to mirror,
  not re-derive:** child-1's adoption entry point (recovery routes through it, not a
  second mechanism); the held-report shape (`flow.py:1039` pre-child-1). **Reference
  implementation for the recovery leg:** the terminal-parent paths in
  `results/issue_469/iteration-v3/patch.diff` and the recovery tests in the preserved
  suite `results/issue_469/test_flow_adopt_split.py`.
- **Disposition hint:** new-feature
<!-- pdca:end child-2 -->
