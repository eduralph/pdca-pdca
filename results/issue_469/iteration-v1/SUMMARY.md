# Result — issue 469 / flow-adopt-split-children

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** on byte-identical disk state,
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes (or is found) `close-disposition =
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

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #469: make every unified `pdca flow` drive path adopt lineage-scoped split children in the same bounded run, including recovery from an already-terminal split parent.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is precise and falsifiable across mid-run adoption, terminal-parent recovery, CLI parity, scheduling, one shared budget, lineage scope, and loud holds; no unresolved scope choice remains. |
| C2 Reproduction (red pre-fix) | PASS | Against the target's exact pre-fix `HEAD` plus only the new test, 16/19 tests failed and the principal child-terminal assertion stayed PLANNED, directly reproducing the stranded-child defect at `template/tests/test_flow_adopt_split.py:345`. |
| C3 Change | PASS | The patch stays within the declared flow, configuration, operator-documentation, prompt, and focused-test surfaces, with adoption centralized on the shared driver at `template/src/pdca_harness/flow.py:939` and `template/src/pdca_harness/flow.py:1115`. |
| C4 Verification (red→green) | PASS | The same focused module changed from 16 failures pre-fix to 19/19 passing post-fix, covering mid-run/recovery behavior at `template/tests/test_flow_adopt_split.py:333` and held-child exclusion at `template/tests/test_flow_adopt_split.py:685`. |
| C5 Causal adequacy | PASS | The fix removes the frozen-drive-set cause by recomputing and splicing the remaining schedule at `template/src/pdca_harness/flow.py:997`; it adds no optional-capability probe or guard around an eager/load-time side effect. |
| T1 Structure | PASS | The architectural choice is coherent: one adoption helper mutates the one shared wave list, and adopted work re-enters the ordinary loop and integration reconciliation at `template/src/pdca_harness/flow.py:1006` and `template/src/pdca_harness/flow.py:1197`. |
| T2 Shape | PASS | `git diff --check`, docs lint, and a 22-page render/link audit all pass; the operator contract is consistently stated at `docs/07-crosscutting.md:243`. |
| T3 Runtime | NEEDS-HUMAN | Decide whether to waive the recorded non-gating runtime red — the full driver suite passes with a clean environment, but an inherited `PDCA_VERIFY_BASE` reproducibly causes 11 pre-existing isolation failures where wave-0 expects it unset at `template/tests/test_verify_base.py:104`, so the frozen gate run was not hermetic. |
| T4 Contribution | NEEDS-HUMAN | Decide whether the asserted contribution-text PASS is sufficient — `commit-msg.txt`, `pr-description.md`, and the recorded `scripts/pdca contribcheck` runner were not supplied, so the required user-impact opener and tracker linkage could not be independently reproduced. |
| T5 Judgment | PASS | Affected-path history confirms the declared #468 unified-path and #456 lineage prerequisites are present, and the sole closed-unmerged PR changes only `README.md`; no overlapping rejected implementation or unaccounted upstream fix remains. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether automatic transitive adoption and the recovery run's one-wave-sized pass pool match operator expectations — this controls surprise work expansion and where a broad split stops for an explicit resume despite the verified mechanics documented at `docs/07-crosscutting.md:320`. |

### Advisory — adversary

# Adversarial review — issue_469 (flow: adopt split children mid-run)

Advisory only; gates are elsewhere. Everything below was re-run against
`$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt`) on faithful copies, never in the
target tree.

## The evidence — re-run, and it holds

- Red leg reproduced: production hunks (`flow.py`, `config.py`, `leaves.py`) reverted to
  `e955b79`, test kept ⇒ **16 of 19 fail**; post-fix **19/19 pass** (0.19 s). The three that
  are green pre-fix are no-regression guards
  (`test_a_named_id_list_keeps_its_strict_scheduling_contract`,
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
  `test_an_unreadable_close_marker_never_kills_the_run`), so the brief's "the guard tests
  are red pre-fix by the same route" is loose — but the **four guards the brief actually
  names** are all in the red set. C4's `pass` row is earned.
- The suite drives the production path: `cli._flow → flow.flow_ids → _drive_and_act`, with
  `flow._drive_wave` / `_build_all` / `_point_at_integration` wrapped as pass-through spies
  (`test_flow_adopt_split.py:243-255`) and the split produced by the real `split.accept`. No
  parallel re-implementation.
- 15-mutation battery on `flow.py`: **14 caught** (narrowed `except`, dropped path-escape
  guard, dropped record dedup, dropped drive-set dedup, hardcoded `k+1` wave index, per-wave
  budget, held-child-in-results-map, dropped terminal predicate, dropped chain walk, strict
  reschedule, append-instead-of-splice, dropped run-budget break, seeds never examined,
  dropped no-record report). One survived — see below.
- T3's recorded red is **not** this patch: the full driver suite is **1652/1652 green** with
  the patch applied in a faithful repo copy, and `tests.test_verify_base` fails (11/19) only
  when `PDCA_VERIFY_BASE` is inherited — exactly the pre-existing isolation fault the brief
  pre-declared. Not a refutation.

## Refutations

- **NEEDS-HUMAN — `template/src/pdca_harness/cli.py:661` + `flow.py:1009`: adoption breaks
  the CLI-shape exit-code parity the brief makes success criterion (3).** `_report_single`
  applies its `AWAITING_SIGNOFF`-is-OK leniency to the **whole** results map, and #469 has
  now put bundles the operator never typed into that map (`bundles += scheduled`).
  Reproduced on byte-identical disk (500 splits into 601/602; the sign-off session answers
  601 and walks away from 602 — the ordinary end of an interactive run):
  `pdca flow 500` → stdout `COMPLETE<TAB>…/issue_500`, **rc 0**;
  `pdca flow 500 999` (999 already COMPLETE, arity-only change — the exact fixture
  `test_both_cli_shapes_adopt_identically_on_the_same_bytes:427` uses) → stdout lists
  `AWAITING_SIGNOFF 602`, **rc 1**. Pre-patch both shapes returned 0 on that same disk, so
  the divergence is introduced here. The single-id run therefore reports total success on
  stdout *and* in rc while an adopted child sits un-terminal. The suite misses it because the
  only non-finishing parity test, `test_a_refused_adopted_wave_exits_1_at_either_arity:446`,
  picks the one failure path (`PreflightError`) that returns **before** the results map.
  Human call because the remedy touches #468's documented rc rule (restrict the leniency to
  the ids named, or ratify the widening) rather than being a local slip.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1287` (`if k < len(wave_list) - 1
  and do_publish:`) is a load-bearing production hunk with zero test coverage.** Every test in
  `test_flow_adopt_split.py` runs with `no_publish=True` (`:158`), so the publish/fold branch
  is dead under the whole new suite. Verified: restoring the pre-patch cached
  `last = len(wave_list) - 1` **survives all 1652 driver tests**, yet on the canonical
  `pdca flow 500` split-and-adopt run with publishing on it takes `integrate.fold` calls from
  `[['issue_500'], ['issue_500','issue_601']]` down to `[]` — i.e. no wave ever folds, `integ`
  stays empty, and every adopted child builds off the unfolded base instead of the run's
  per-target integration branch. Add one adoption test with `no_publish=False` asserting the
  wave-0 fold happens (and, with a non-stub publisher, that adopted children are pointed at
  the integration branch — the present
  `test_adopted_children_go_through_the_same_integration_reconciliation:359` only asserts the
  *call list* under `dry=True`, where `_point_at_integration` can only ever clear a stale base).

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:984` (`if parent.name in
  examined: continue`): the termination bound the docstring claims ("Adoption is bounded — a
  parent is examined once … the queue drains") is the one mutation the suite does not catch.**
  Deleting the `continue` keeps all 1652 tests green, and `cli._flow` then **hangs forever**
  (killed at 45 s) on a lineage record whose `children` edge names an ancestor — 500 split →
  601, 601's hand-edited `split-lineage.json` naming `500` back, driven as `pdca flow 500`.
  The shipped code is correct (the same scenario finishes in <1 s, rc 0, 602 COMPLETE); it is
  the *test* that is missing, and the hand-edited-record threat model is precisely the one the
  patch cites to justify the dedup (`flow.py:870`) and path-escape guards, both of which *are*
  pinned. A cyclic-lineage regression test costs ~10 lines.

- **NEEDS-HUMAN — `template/src/pdca_harness/flow.py:1181`
  (`budget = allowance * max(1, len(wave_list))`): adoption is strictly weaker than the manual
  restart it replaces, which is a fitness call, not a bug.** `pdca flow 500` sets out to drive
  one wave, so the whole run — parent plus however many adopted generations — gets
  `max_passes` passes total, while the operator's current remedy (`pdca flow 601 602 …`) gets
  `max_passes` **per wave**. At the default 20 a parent wave (~2 passes) plus a six-child brood
  levelled into six waves has ~3 passes each; a wider or deeper brood stops mid-run. It is
  loud, resumable and documented in the diff (`docs/07-crosscutting.md`, "One consequence
  worth knowing before you type it"), and `test_the_pass_budget_is_one_cap_for_the_whole_run`
  pins the behaviour — so this is for the human to ratify at sign-off, not for the builder to
  re-decide.

## Attempted and could not refute

- Mid-run re-scheduling (`_reschedule`, `flow.py:916`) dropping or re-ordering *original*
  batch members: dependency edges point backwards, so any dep path between two still-pending
  bundles runs entirely through still-pending bundles — order is preserved, and a conflict
  naming an already-driven bundle is correctly moot. Every case I could build where the
  tolerant path holds an original (prereq left non-COMPLETE) is a case `_runnable` already
  skipped loudly pre-patch; disposition unchanged.
- The strict-contract claim ("only what adoption ADDS goes through the tolerant path"): the
  seed splice at `k=-1` does re-level the *whole* remainder tolerantly, but
  `waves.compute_waves` still raises first (`flow.py:1175`), and I could not construct an id
  list that `check_dep_graph` admits and `partition_schedulable` then holds — the two resolve
  `Stacks on` / archived / out-of-batch prereqs identically (`waves.py:76`, `waves.py:262`).
- Path traversal: `../../etc`, `x/../600`, absolute ids and empty ids all fail the
  `d.parent != cfg.bundle_root` lexical check or land inside the root harmlessly.
- Budget non-regression for runs that adopt nothing: `spent ≤ allowance × k` before wave `k`,
  so `spent >= budget` provably cannot fire — verified by construction and by
  `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`.
- `_drive_wave`'s new `int` return: every exit path returns `used`; no other production caller
  exists (`flow.flow` keeps its own loop and, per `cli.py:614`, is no longer on any CLI path).
- Recursion/dedup across waves, `examined` being pre-seeded with every driven bundle, held
  children staying out of `bundles` / `batch_names`, and the announcement being read back from
  the recomputed tail: all behave as documented under direct scenario runs.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether to waive the recorded non-gating runtime red — the full driver suite passes with a clean environment, but an inherited `PDCA_VERIFY_BASE` reproducibly causes 11 pre-existing isolation failures where wave-0 expects it unset at `template/tests/test_verify_base.py:104`, so the frozen gate run was not hermetic.
- [ ] T4 Contribution — Decide whether the asserted contribution-text PASS is sufficient — `commit-msg.txt`, `pr-description.md`, and the recorded `scripts/pdca contribcheck` runner were not supplied, so the required user-impact opener and tracker linkage could not be independently reproduced.
- [ ] Validation — fitness-to-purpose — Decide whether automatic transitive adoption and the recovery run's one-wave-sized pass pool match operator expectations — this controls surprise work expansion and where a broad split stops for an explicit resume despite the verified mechanics documented at `docs/07-crosscutting.md:320`.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether to waive the recorded non-gating runtime red — the full driver suite passes with a clean environment, but an inherited `PDCA_VERIFY_BASE` reproducibly causes 11 pre-existing isolation failures where wave-0 expects it unset at `template/tests/test_verify_base.py:104`, so the frozen gate run was not hermetic.; T4 Contribution — Decide whether the asserted contribution-text PASS is sufficient — `commit-msg.txt`, `pr-description.md`, and the recorded `scripts/pdca contribcheck` runner were not supplied, so the required user-impact opener and tracker linkage could not be independently reproduced.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
