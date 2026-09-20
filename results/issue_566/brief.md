# split --accept tells the operator to run `pdca flow <child-ids>` even when a live run may drive them — and no run names the split children it did not drive

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file. Split out of #498 at its
> third Plan; builds on the sibling child's drive claim (one live driver per bundle).

- **Slug:** split-hint-honest-about-a-live-run
- **Defect / goal:** `pdca split <id> --accept` always ends with
  `"<parent> marked split; run `pdca flow <child-ids>` to drive the children"`
  (`template/src/pdca_harness/cli.py:843-844`). Since #469/#473 a live run adopts the
  children of a split parent it is driving (`flow.py:1554`) or was handed as a seed
  (`flow.py:1784-1797`), and a CSV batch sweeps every in-flight bundle after its Plan
  session (`flow.py:1673-1692`), so the bare instruction tells the operator to start a
  second driver over bundles a live run may be about to drive. The model-facing text says
  the same (`template/agents/planner.md.jinja:155`, `:182-183`; `leaves.py:1119-1120`;
  `docs/07-crosscutting.md:340-343`). And when a live run does NOT reach a split parent's
  children (its sign-off goes unanswered, the parent sits behind an unready prerequisite,
  or the split lands after the parent's adoption point), nothing at the end of the run
  names them: they sit PLANNED with no line pointing at them.
  Two earlier rounds (#498 v1/v2) tried to make the line **promise** the run would drive
  the children; nothing at accept time can know that, so this brief asks for an honest
  conditional line plus an end-of-run report instead.
- **Success criterion:** Through `cli._split` and `cli._flow`, with the patch:
  (i) **In reach of a live run, the line is conditional.** When `split --accept` completes
  while (a) a live `pdca flow` run holds the parent (the sibling child's claim) — whether
  the accept runs from that run's own Plan or sign-off session or from another shell — or
  (b) a live CSV batch run (`pdca flow --from-csv`) has not yet swept its in-flight bundles
  (`flow.py:1678`), then today's line is **not** printed. In its place one line that: starts
  `<parent> marked split;`, names every child id, says that run drives them only if it
  reaches them and lists any it did not drive when it ends, and gives `pdca flow
  <child-ids>` (via `_prog()`, as today) for use after that run has ended. It never
  promises ("will drive") and never says "do not start another flow". Suggested wording:
  `issue_500 marked split; a running \`pdca flow\` holds issue_500 and drives its children
  (601 602) if it reaches them — it lists any it did not drive when it ends. After that
  run ends, drive any left with \`pdca flow 601 602\``.
  (ii) **Otherwise, today's line byte-identical.** A standalone accept, an accept after the
  run has ended (returned, raised or was killed), and an accept on a parent the live run
  has let go (e.g. a named id it skipped) print exactly
  `<parent> marked split; run \`<prog> flow <ids>\` to drive the children`.
  (iii) **End-of-run report.** Just before `_drive_and_act` returns (`flow.py:1641-1646`,
  so both CLI shapes and the CSV batch get it), for every split parent in the run's drive
  set or its adoption seeds, the run names on stderr every lineage child that is not
  terminal and not in the run's final drive set — one line per parent, with a
  `pdca flow <ids>` command. It walks through a child that is itself terminal on a split,
  as adoption does (`flow.py:1216-1231`). No such children → no line. The exit code is
  unchanged. Probe: `pdca flow 7 8` with 8 `Conflicts with: 7`, nobody answers 7's
  sign-off; while A drives 8, a split of 7 is accepted from another shell (the line is
  (i)'s conditional one, since A still holds 7); when A ends it names 7's children with
  `pdca flow 701 702`.
  (iv) **Checking never causes a false refusal.** Whatever the accept does to learn whether
  a live run holds the parent must never make a concurrent `pdca flow` over that bundle
  refuse it as "held by another run" when no run holds it. If the check can collide with a
  claim attempt, the claim side retries past it, pinned by a test that forces the
  collision deterministically.
  (v) **The text agrees.** `template/agents/planner.md.jinja:155` and `:182-183`, the
  planner seed prompt at `leaves.py:1119-1120`, and `docs/07-crosscutting.md:340-343` say
  what `--accept` now prints and when, and mention the end-of-run report.
  (vi) **Nothing else changes.** Every other line of `cli._split` and the existing
  adoption reports (`flow.py:980-985`, `:1041-1056`, `:1115`, `:1245`) are byte-identical;
  the whole `template/tests` suite stays green. Every branch that changes which line
  `--accept` prints, or whether the end-of-run report fires, has a test that fails if that
  branch is deleted.
  Shown by the named test going red on this child's base (the in-flow accept prints
  today's instruction; no end-of-run line) and green with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11
  + git), stub leaves, empty gates, on the base this child builds on (the sibling child's
  accepted result: the drive claim exists, the line is still unconditional, no end-of-run
  report). `template/tests/test_flow_adopt_split.py:43-63` drives real `cli._flow` runs;
  `:190-216` swaps a stub leaf for a stand-in that acts mid-run — for the in-run case the
  stand-in calls `cli._split(cfg, SimpleNamespace(issue_id=…, accept=True, ids="601,602"))`
  and the test captures stderr. For "another shell" cases run A as a **real subprocess**
  paused inside a stand-in leaf, and call `cli._split` from the test process. Bound every
  wait with a timeout so the red leg fails instead of hanging C4. For (iii), the probe in
  the criterion is the red case: on the base A ends with 701/702 PLANNED and no line naming
  them.
- **Invariant to restore:** The driver never tells the operator something about a live run
  that the run cannot guarantee, and every child a split produced is either driven by the
  run that could reach it or named, with the command that drives it, by the time that run
  ends. Source: internal project invariant (Tier C) — the flow's own "never silent" rule
  for work it walks away from (#260, `_warn_abandoned` `flow.py:750-777`) and for held
  children (`_report_held` `flow.py:780-797`), applied to split children. Scope names no
  mechanism; guarding `cli.py`'s line alone cannot satisfy the second half.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b` plus the sibling
  child's accepted change; line numbers here are on `70ea12b`, verified 2026-09-19 —
  re-locate them on the stacked base)
- **Depends on:** 565
- **Ordering note:** Depends on the drive-claim child: it reads that claim to decide what to
  print, and both edit `cli.py` and `flow.py`. On this v0.57.0 instance a stacked
  second-wave bundle may show a false advisory T3 red (#474, fixed upstream only).
- **Surfaces:** data
- **Difficulty:** medium — the tail of `cli._split`, the end of `_drive_and_act`, a
  live-holder check built on the sibling's claim, and model-facing text in three places.
- **Scope (one logical fix) / out of scope:** Make `split --accept`'s closing line depend
  on whether a live run can reach the children, word it as a condition rather than a
  promise, add the end-of-run report of split children the run did not drive, and update
  the text that describes `--accept`'s output. / out of scope: the claim mechanism itself
  and its refusal / release rules (the sibling child's); the adoption algorithm (what is
  adopted, wave levelling, budget); `_terminal_hint` (`flow.py:710-747`); the `--ids` /
  filing / error branches of `cli._split` (`cli.py:721-842`); the other adoption report
  lines listed in (vi); single-step verbs; cross-host coordination.
- **Reproduction:** On the sibling child's accepted result, from `template/`: with
  `tests/test_flow_adopt_split.py`'s stub fixture, make 500's stand-in Plan leaf call
  `cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))` inside a
  `cli._flow` run over 500 — stderr carries `issue_500 marked split; run \`… flow 601
  602\` to drive the children` while the same run drives 601/602 itself. Then run the
  (iii) probe: A ends with 701/702 PLANNED and no line naming them.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11, git) suffices; stub
  leaves, no vendor CLI, no network.
- **Test file:** `template/tests/test_split_hint_live_run.py` (**new**). **C4 red-leg import
  trap:** the red leg reverts this child's production hunks and keeps the test; a
  module-level import of a symbol THIS child adds fails to load and records
  `PDCA-UNVERIFIABLE`, not red. Import only modules on the base
  (`from pdca_harness import cli, flow, split, state`) and drive the behaviour through
  `cli._flow` / `cli._split`. Do not import helpers from `test_flow_single_driver.py` or
  any other test module; copy what you need. A subprocess leg must set `PYTHONPATH` to the
  checkout's `template/src` and must not inherit `PDCA_*` from the gate's environment.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  The line to replace: `cli.py:843-844`. The end-of-run point: `_drive_and_act`'s tail
  (`flow.py:1641-1646`); mirror the walk of `_adopt_split_children` (`flow.py:1216-1231`,
  via `_adoptable` `flow.py:913`) and the lineage read of `_lineage_children`
  (`flow.py:690-707`); keep the report shape of `_warn_abandoned` (`flow.py:773-777`). The
  live-holder check builds on the sibling child's claim — reuse it, do not add a second
  lock. From #498 v2 (`results/issue_498/iteration-v2/patch.diff`): its hint half answered
  "will drive" and was rejected for that; do not re-attempt it unchanged. Its CSV-batch
  "not swept yet" mark (`sweeping`) and its probe collision (`_held_now` vs `take()`
  without retry) are the known pitfalls for (i)(b) and (iv).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 6
  -- template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py` → `6ddfca4` /
  `51a65a2` (#475), `9a19cb5` (#466), `a2eefe1` (#459), `389bf1a` / `96c9704` (#469/#473) —
  none conditions the closing instruction or reports un-driven split children. Open PRs
  touching `cli.py` / `flow.py` / `split.py`: none. Closed-unmerged: none. Prior attempts:
  #498 `iteration-v1/`, `iteration-v2/` (hint half sent back to Plan both times).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on finding 2 — the end-of-run stranded-child report names finished children as unfinished work. `flow._warn_stranded_split_children`'s lineage walk (patch.diff:319-328) implements only half of brief (iii). It skips a child that is in the run's final drive set, and walks through a child that is itself split-marked, but it never checks the child's own state. So a COMPLETE / DISCONTINUED / RESOLVED child gets appended to `stranded` and printed as "left in-flight" with a `pdca flow <ids>` command pointing at work that is already done. Reviewer probe: parent 500 with COMPLETE children 601/602 under a real `flow 500 8` run prints `601, 602 left in-flight` (check-review.md finding 2; reviewer-probes.log:1). The only `state.state` calls in the new flow code are in the unrelated batch sweep — there is no terminal check anywhere in the walk. What to change: - Skip a lineage child whose state is terminal, per brief (iii) "not terminal and not in the run's final drive set". Both conditions, not just the second. - Keep walking THROUGH a terminal split child. That traversal is deliberate and correct — a split parent is terminal by design, and its grandchildren must still be reached. Do not fix this by gating the whole walk on non-terminal. - Pin the missing branch with a test. Brief (iii) says "No such children → no line" and (vi) requires a test for every branch that changes whether the report fires; none of the 8 submitted tests covers a split parent whose children are all finished. Scope of this iterate: finding 2 only. Change nothing else. The human reviewed the other two reviewer findings at sign-off and accepted the current behaviour on both — do not "also fix" them: - Finding 1 (flow_batch holds the CSV sweep marker for the whole drive, because `return _drive_and_act(...)` is evaluated inside the `try` before the `finally` releases it): accepted as-is, no fix wanted. - Finding 3 (`Run.take`'s bounded 5-retry past a `held()` peek vs brief (iv)'s absolute "never cause a false refusal"): no work wanted now. The conditional-line half of the change was not rejected.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on finding 2 — the end-of-run stranded-child report names finished
  children as unfinished work.

  `flow._warn_stranded_split_children`'s lineage walk (patch.diff:319-328)
  implements only half of brief (iii). It skips a child that is in the run's final
  drive set, and walks through a child that is itself split-marked, but it never
  checks the child's own state. So a COMPLETE / DISCONTINUED / RESOLVED child gets
  appended to `stranded` and printed as "left in-flight" with a `pdca flow <ids>`
  command pointing at work that is already done. Reviewer probe: parent 500 with
  COMPLETE children 601/602 under a real `flow 500 8` run prints
  `601, 602 left in-flight` (check-review.md finding 2; reviewer-probes.log:1).
  The only `state.state` calls in the new flow code are in the unrelated batch
  sweep — there is no terminal check anywhere in the walk.

  What to change:

  - Skip a lineage child whose state is terminal, per brief (iii) "not terminal
    and not in the run's final drive set". Both conditions, not just the second.
  - Keep walking THROUGH a terminal split child. That traversal is deliberate and
    correct — a split parent is terminal by design, and its grandchildren must
    still be reached. Do not fix this by gating the whole walk on non-terminal.
  - Pin the missing branch with a test. Brief (iii) says "No such children → no
    line" and (vi) requires a test for every branch that changes whether the
    report fires; none of the 8 submitted tests covers a split parent whose
    children are all finished.

  Scope of this iterate: finding 2 only. Change nothing else.

  The human reviewed the other two reviewer findings at sign-off and accepted the
  current behaviour on both — do not "also fix" them:

  - Finding 1 (flow_batch holds the CSV sweep marker for the whole drive, because
    `return _drive_and_act(...)` is evaluated inside the `try` before the
    `finally` releases it): accepted as-is, no fix wanted.
  - Finding 3 (`Run.take`'s bounded 5-retry past a `held()` peek vs brief (iv)'s
    absolute "never cause a false refusal"): no work wanted now.

  The conditional-line half of the change was not rejected.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
