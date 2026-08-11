# Result — issue 449 / flow-adopt-split-children

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a split that happens *inside* a driven flow no longer strands its own
  children. When a bundle in the drive set reaches `close-disposition = split`, the run
  enumerates that bundle's children, validates them with the tolerance the resume path
  already uses, splices them into the remaining waves, and says so — instead of ending
  with the parent terminal, the children sitting PLANNED, and the operator restarting by
  hand with `pdca flow <child-ids>`.
- Success criterion: a `flow.flow_ids(cfg, ["<parent>"])` (and a single-id
  `flow.flow`) whose Plan/re-plan beat splits the parent drives that parent's children to
  a terminal state **within the same call** — in a wave AFTER the one the parent was in,
  honouring their own `Depends on` / `Conflicts with`, counted against the same run's
  `max_passes` budget, each adoption announced on stderr as `issue_<parent> split →
  adopted children issue_<a>, issue_<b> into wave <k+1>`. A child whose dependency cannot
  be resolved is **held loudly and the run continues**, never aborts. An explicit-id flow
  adopts only children of the ids it was given (transitively) and never widens into a disk
  sweep. Demonstrable by C4-verify on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes `close-disposition = split` while it
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

Reviewing issue 449’s enhancement so a flow adopts and drives split descendants in later waves during the same bounded run instead of stranding them PLANNED.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is decidable across entry points, lineage-only scope, scheduling tolerance, reporting, and budget behavior, so no implementation-critical product choice remains unstated (`docs/07-crosscutting.md:243`). |
| C2 Reproduction (red pre-fix) | PASS | With only production hunks reversed and the regression module retained, all 15 tests executed and the suite produced 18 assertion failures, including both entry points leaving child 601 PLANNED (`template/tests/test_flow_adopt_split.py:254`). |
| C3 Change | PASS | The change reads the lineage edge, tolerantly re-levels only the remaining schedule plus descendants, and adds only scheduled children to run state, preserving explicit-id scope (`template/src/pdca_harness/flow.py:824`). |
| C4 Verification (red→green) | PASS | After restoring the exact patch, the same 15 tests all passed; the target also passes `git diff --check` and the complete offline driver suite (`template/tests/test_flow_adopt_split.py:254`). |
| C5 Causal adequacy | PASS | The frozen-drive-set cause is removed by recomputing and splicing the remaining waves after each driven split, rather than hidden behind a capability probe or symptom guard (`template/src/pdca_harness/flow.py:968`). |
| T1 Structure | PASS | Shared detect/validate/splice/report helpers live behind `_drive_and_act`, while the single-id path delegates to that same mechanism with carried accounting instead of duplicating the scheduler (`template/src/pdca_harness/flow.py:451`). |
| T2 Shape | PASS | Docs lint and the 22-page render/link audit passed, and the operator contract states later-wave placement, lineage-only scope, recovery, and held-child behavior consistently (`docs/07-crosscutting.md:243`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether to waive the recorded T3 red as gate-runner state leakage — the full driver suite and all seven Copier 9.17.1-backed render/update tests pass independently, but the recorded run inherited `PDCA_VERIFY_BASE` where wave-0 tests require it absent (`template/tests/test_verify_base.py:100`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether to accept the reported contribution-metadata green without an independent audit — `commit-msg.txt` and `pr-description.md` were not supplied, so their user-impact opener and tracker reference could not be rerun. |
| T5 Judgment | PASS | Affected-path merged history and all closed-unmerged PRs were checked mechanically; #354/#362/#460/#465 are complementary antecedents and no rejected affected-path work duplicates this adoption change. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether transitive recovery adoption and the one-wave pass pool for a parent-only recovery match the intended operator experience — automation proves the mechanics but cannot own that product-policy judgment (`docs/07-crosscutting.md:331`). |

### Advisory — adversary

# Adversarial review — issue 449 / flow-adopts-split-children-mid-run

Advisory only; never gates. Everything below is grounded on the target source at
`$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, working tree = patch applied).

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:451`: the single-id adoption
  tail is wrapped in `_isolate`, which swallows `PreflightError`, so `pdca flow 500` exits
  **0** where `pdca flow 500 601` exits **1** on byte-identical disk state.** `_isolate`
  contains every `Exception` (`flow.py:~640`, "only `Exception` is contained"), and the
  adopted children's drive raises `PreflightError` at `flow.py:1209` when a pooling wave
  fails lane preflight. Concrete reproduction (run against the target, `lanes=2`, parent
  500 stranded terminal-on-split with two *independent* children 601/602 so the adopted
  wave pools, `preflight.lane_preflight` returning `(False, [...])`):
  - `flow.flow_ids(cfg, ["500"])` → raises `PreflightError: lane preflight failed for a
    lanes=2 batch — not fanning out`; `cli.py:652-656` catches it and returns **1**.
  - `flow.flow(cfg, "500")` → returns `COMPLETE`, printing only `flow: issue_500 — split
    adoption failed (PreflightError: …); skipping this bundle (left COMPLETE)`; `cli.py:639`
    then returns **0** because the *parent* is COMPLETE. The children are still `PLANNED`.
  This contradicts three claims the patch itself adds: `docs/07-crosscutting.md:259-260`
  ("`pdca flow 500` and `pdca flow 500 501` do the same thing to the same disk"),
  `flow.py:1113-1115` ("behave the same on the same disk state"), and the Iteration-1
  sign-off RULING (b) that required the two entry points to be consistent. The abort is
  deliberately loud by design ("aborts the run … rather than produce false-red bundles",
  `flow.py:1197-1200`) — downgrading it to a contained per-bundle skip means automation
  reading the exit code sees a successful flow. Fix is narrow (re-raise `PreflightError`
  — and anything else meant to stop a run — out of the tail, or scope the `_isolate` to the
  detect/validate step rather than the whole `_drive_and_act`), plus a test asserting both
  entry points behave identically here; the suite currently has no case where the tail
  raises at all.

- **NEEDS-HUMAN — `check-gates.json:78-85`: the gating T4 pass is not verifiable from the
  supplied inputs (verdict provisional).** T4's oracle is `./scripts/pdca contribcheck`,
  which is not present in the target worktree, and `patch.diff` contains no
  `commit-msg.txt` / `pr-description.md` — the artifacts T4 judges. Iteration 2's
  carry-forward raised exactly this and it is still unresolved from where Check sits. Not a
  refutation of the fix; a human must confirm the contribution artifacts independently.

## Attempted and could not refute

- **The red→green is real and exercises production.** Reverse-applied the production hunks
  only (`git apply -R --include='template/src/*'`, test file kept) into a scratch copy:
  **18 failures**; with the hunks restored, **15 tests OK**. The tests drive
  `flow.flow_ids` / `flow.flow` / `flow.flow_batch` — the real entry points — and build the
  split with the production `split.accept`, not a simulation.
- **The assertions bind — no tautology, nothing mocked away.** Seven targeted mutations of
  the exact behaviours prior iterations demanded, each caught: dropping the duplicate-child
  `seen` dedup (`flow.py:838`) → 1 fail; ignoring `wave_offset` in the announcement
  (`flow.py:990`) → 3 fails; un-capping the run pool (`flow.py:1160`) → 4 fails; handing the
  single-id tail a fresh budget instead of `max_iters - spent` (`flow.py:453`) → 1 fail;
  narrowing `_is_split_parent`'s catch to `OSError` (`flow.py:794`) → 1 error; dropping the
  terminal parent instead of seeding it (`flow.py:1445`) → 5 fails; splicing into the
  current wave `k` instead of `k+1` (`flow.py:969,978`) → 6 fails.
- **The T3 red is genuinely pre-existing, not this patch.** With a clean environment the
  entire driver suite is green: **1637 tests, OK (skipped=2)**. Re-running
  `tests.test_verify_base` with `PDCA_VERIFY_BASE` inherited reproduces exactly 11 failures
  **both** on the patched tree and on a pristine `git archive HEAD` export — identical
  counts. The carry-forward's "test-isolation fault, out of scope" is verified, not assumed.
- **Hostile lineage records do not break it** (`flow.py:824-873`). Probed on the target: a
  record naming the parent as its own child terminates (`examined` guard); `["601", None,
  42, "../evil", "  ", "602"]` drives 601/602 and rejects `../evil` with *"it resolves
  outside …/results"*; two children in a dependency cycle are both held (`dependency cycle`)
  and the run continues; conflicting siblings land in separate waves.
- **Recursion is bounded and does not multiply the budget.** An adopted child that splits
  again mid-run drove 4 waves (500 → 601 → {701,702}) on a pool sized for 1 wave, spending
  exactly 6 of 6 allowed passes, with each announcement naming the child's real wave
  (601→1, 602→2, 701→2, 702→3). Two split parents in one wave both had their broods adopted.
- **The pool is provably non-binding without adoption**, so no ordinary batch is newly
  truncated: each wave spends `min(allowance, budget - spent)` and `budget = allowance ×
  len(wave_list)` (`flow.py:1160,1220`), so `spent` cannot reach `budget` before the last
  wave. `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` covers it.
- **`_drive_wave`'s new `int` return is total** — all three exit paths return `used`
  (`flow.py:1046,1076,1085`); no caller in `template/tests` depends on the old `None`.
- **Entry-point agreement holds at a *binding* budget for a mid-run split too** (a case the
  suite only covers at a non-binding budget): both entry points ended
  `601=COMPLETE, 602=PLANNED` and printed the identical *"the run's pass budget is spent
  (3 pass(es) over 2 wave(s))"* line at `max_passes/max_iters=3`.
- **Adoption really does reach `flow_batch`'s drive phase**, as `docs/07-crosscutting.md`
  and `template/agents/planner.md.jinja` now claim: a mid-run split under `flow.flow_batch`
  adopted 601/602 into waves 1 and 2.
- **The operator-facing caveat the previous round asked for is documented** — the
  recovery-run pool ("names only a parent already terminal on a split … its pool is one
  wave's worth") is in `docs/07-crosscutting.md`, not only in a module docstring.
- Tried and could not reach: an announced wave index going stale after a *later* adoption
  re-levels the remainder (constructed a name-lower conflicting grandchild; the schedule did
  not move an already-announced child). No concrete failing case, so not filed.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether to waive the recorded T3 red as gate-runner state leakage — the full driver suite and all seven Copier 9.17.1-backed render/update tests pass independently, but the recorded run inherited `PDCA_VERIFY_BASE` where wave-0 tests require it absent (`template/tests/test_verify_base.py:100`).
- [ ] T4 Contribution — Decide whether to accept the reported contribution-metadata green without an independent audit — `commit-msg.txt` and `pr-description.md` were not supplied, so their user-impact opener and tracker reference could not be rerun.
- [ ] Validation — fitness-to-purpose — Decide whether transitive recovery adoption and the one-wave pass pool for a parent-only recovery match the intended operator experience — automation proves the mechanics but cannot own that product-policy judgment (`docs/07-crosscutting.md:331`).
- [ ] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 2). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Human chose iterate-do (second conscious override of the size backstop's iterate-plan recommendation). The adoption mechanism is proven — C4 red→green reproduced and mutation-tested (7/7 mutations caught) — keep it unchanged. Fix ONE narrow defect, do not re-architect: the single-id adoption tail is wrapped in `_isolate`, which swallows `PreflightError` (`template/src/pdca_harness/flow.py:451`; `_isolate` contains every Exception at `flow.py:~640`), so on byte-identical disk state `pdca flow 500` exits 0 with children still PLANNED where `pdca flow 500 601` exits 1 on a lane-preflight failure (`flow.py:1209`, caught by `cli.py:652-656`). This contradicts the entry-point-consistency contract the patch itself documents (`docs/07-crosscutting.md:259-260`, `flow.py:1113-1115`) and Iteration 1's RULING (b). Fix: re-raise `PreflightError` (and anything else meant to abort a run) out of the tail — or scope `_isolate` to the detect/validate step rather than the whole `_drive_and_act` — and add a test in `template/tests/test_flow_adopt_split.py` where the tail raises, asserting both entry points produce identical exit behavior on identical disk; the suite currently has no case where the tail raises at all. T3 red (11 failures in test_verify_base.py under inherited PDCA_VERIFY_BASE) remains the verified pre-existing isolation fault, out of scope — expect the same non-gating red on the rebuild.
- By / date: Eduard Ralph / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
