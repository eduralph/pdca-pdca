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
- **Depends on:** 472
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

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): rebuilding for the implementation-level findings — C5 Causal adequacy — Rebuild the budget rule around every live wave (while retaining the non-reset bound) — the named-only cause leaves adopted-tail starvation intact and therefore does not satisfy the stated causal contract at `template/src/pdca_harness/flow.py:1338`.; T2 Shape — Decide whether rendered documentation and link shape remain valid — the asserted `run-docs-check.sh` is absent from the target and the available render tests all skipped because `copier` is unavailable, so the recorded green cannot be independently affirmed.; T4 Contribution — Decide whether contribution metadata and novelty are acceptable — affected-path `git log --all` confirmed merged/local history including #468/#472, but the contribution validator/artifacts and closed/rejected-work history were unavailable, so prior art is not mechanically settled.; T5 Judgment — Rebuild the test evidence so stdout failure is exercised without contradicting the budget criterion — the current test turns a specified live-wave success case into its expected failure at `template/tests/test_flow_adopt_recovery.py:335`..
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): rebuilding for the implementation-level findings — T4 Contribution — Decide whether the contribution text is acceptable — affected-path history plus the sole closed-unmerged PR (which touched only README.md) found no duplicate, but `pr-description.md` and `commit-msg.txt` are outside reviewer inputs, so the substantive checker defined at `template/src/pdca_harness/cli.py:1081` could not be reproduced.. 1 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 3): rebuilding for the implementation-level findings — T3 Runtime — Decide whether runtime compatibility can be accepted without a real Copier render/update run — `copier` is unavailable, so all 7 root compatibility tests skipped even though the 1,672-test driver suite passed with 2 unrelated skips (`template/agents/planner.md.jinja:170`).; T4 Contribution — Decide whether the contribution text is acceptable — the PR-body and commit-message inputs required by the checker are withheld, so its recorded green cannot be rerun; affected-path merged history plus the sole closed-unmerged PR (#4, README-only) found no duplicate (`template/src/pdca_harness/cli.py:1083`).. 1 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
