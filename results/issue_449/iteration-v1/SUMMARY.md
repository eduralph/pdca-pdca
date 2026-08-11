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

Review of issue #449: adopt children created by a split during an active flow into later waves of that same call without widening the explicit drive set.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | NEEDS-HUMAN | Confirm the behavior is not semantically superseded by prior flow/split work — the affected-path merged-history and closed-unmerged-PR scans found no competing implementation, but equivalence remains a product judgment (`docs/07-crosscutting.md:243`). |
| C2 Reproduction (red pre-fix) | PASS | The production-hunks-reversed run executed all five focused tests and failed all five on stranded children/missing reports, grounding the pre-fix symptom through the real entry points (`template/tests/test_flow_adopt_split.py:161`). |
| C3 Change | FAIL | A run-wide pass cap must bound transitive adoption, but `_drive_and_act` reuses the full `max_passes` for every wave; independently, `max_passes=2` completed the parent plus two child waves, permitting more work than the same-run budget promises (`template/src/pdca_harness/flow.py:1045`; contract at `docs/07-crosscutting.md:251`). |
| C4 Verification (red→green) | PASS | The focused module independently ran 5 failing tests with production hunks reversed and the same 5 passing after restoration, so the tested frozen-drive-set defect has genuine red→green evidence (`template/tests/test_flow_adopt_split.py:168`). |
| C5 Causal adequacy | PASS | The frozen drive set is changed at the shared post-wave scheduling point, rather than masked by a capability probe or runtime guard, so the tested stranding cause is directly addressed (`template/src/pdca_harness/flow.py:1050`). |
| T1 Structure | PASS | Shared detect/validate/reschedule helpers feed the common wave driver while the single-id adapter delegates back into that driver, keeping entry-point behavior structurally aligned (`template/src/pdca_harness/flow.py:789`; `template/src/pdca_harness/flow.py:896`). |
| T2 Shape | PASS | Documentation lint and a fresh 22-page render/link audit both passed, so the added operator contract is structurally renderable (`docs/07-crosscutting.md:243`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the unavailable rendered-suite evidence is acceptable — the focused tests and all 1,627 offline driver tests pass now, but the recorded T3 runner failed earlier and its exact `run-suite.sh` plus `copier` toolchain were unavailable (root render/update tests therefore skipped). |
| T4 Contribution | NEEDS-HUMAN | Confirm the contribution artifacts still satisfy policy — the recorded gate is green, but its `./scripts/pdca contribcheck` command and the commit/PR artifacts were not supplied and could not be independently rerun. |
| T5 Judgment | FAIL | The test set proves adoption, ordering, scoping, and holding but omits the load-bearing run-budget boundary, allowing the per-wave reset above to pass review (`template/tests/test_flow_adopt_split.py:159`; `template/src/pdca_harness/flow.py:917`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether same-call descendant adoption is the right operator behavior after the run-wide budget defect is corrected — it deliberately expands the work performed beyond the ids literally named (`template/agents/planner.md.jinja:164`). |

### Advisory — adversary

# Adversarial review — issue_449 (flow adopts split children mid-run)

Advisory only; nothing here gates. Every citation is `$PDCA_TARGET` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:414-421` — **the single-id path adopts a
  split that did *not* happen in this run, spending unrequested cycles.** `flow()` tests only
  `_is_split_parent(d)` (terminal + `close-disposition == split`, `flow.py:723-736`); nothing
  records whether the split occurred during *this* call. Concrete case, reproduced against the
  target: bundle 500 was split and closed in an *earlier* run, its children 601/602 left
  stranded PLANNED. A fresh `pdca flow 500` — which the CLI routes to `flow.flow`
  (`cli.py:639`) — breaks out of the loop on beat 1 (500 is COMPLETE, nothing to plan) and then
  drives **601 and 602 to COMPLETE**, emitting `flow: issue_500 split → adopted children
  issue_601, issue_602 into wave 1`. Pre-patch the identical call drove *zero* waves and just
  printed `COMPLETE`. Because `do_publish` is forwarded (`flow.py:421`), on a live instance
  those two cycles also publish draft PRs. This directly contradicts `brief.md` §Impact &
  compatibility — *"Behaviour changes only when a split happens during a run"* — and the docs
  hunk the patch adds (`docs/07-crosscutting.md:9-12`: *"When a bundle **in the drive set**
  reaches `close-disposition = split`"* — here it never was). It also splits the two entry
  points apart: the same stale parent through `flow.flow_ids(cfg, ["500"])` adopts **nothing**
  (the terminal-id filter at `flow.py:1258-1260` removes 500 before `_drive_and_act` ever
  runs), so `pdca flow 500` and `pdca flow 500 501` now disagree on identical on-disk state —
  while the patch's own planner prompt asserts the opposite (`template/agents/planner.md.jinja:58-60`:
  *"That holds for every shape"*). The scope call is the human's: either restrict adoption in
  `flow()` to a parent that was non-terminal at loop entry, or accept re-driving stranded
  children as intended and correct the brief/docs claim. Note brief §Design step 5 ("on exit,
  if the bundle is terminal with `close-disposition = split`") *does* read literally as
  implemented — the brief is internally inconsistent, which is why this needs adjudication
  rather than a rebuild.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:864-865` and `flow.py:894` — **the
  adoption announcement names a wave the child is not in.** Both report sites hardcode the
  parent's index + 1 (`into wave {k + 1}` / the literal `into wave 1`), but the children are
  placed by `_reschedule`'s recomputed `tail` (`flow.py:860`), which levels them by their own
  `Depends on`. The patch's own test proves the mismatch: it asserts the waves actually driven
  are `[["issue_500"], ["issue_601"], ["issue_602"]]` (`template/tests/test_flow_adopt_split.py:176-177`)
  while asserting the message says `into wave 1` for **both** children
  (`test_flow_adopt_split.py:178-179`) — 602 is driven in wave 2. I reproduced the same skew on
  a mixed drive set (`{500, 700}`, 700 depending on 500): waves driven
  `[[500], [601, 700], [602]]`, message still `into wave 1`. The brief's success criterion does
  spell the format as `into wave <k+1>`, so flag it to the builder rather than treat it as a
  spec change: report each child's real index from `tail`, and update the two assertions.

- NEEDS-HUMAN — `check-gates.json` row **T3** (`"result": "fail"`, evidence `== T3: root suite
  OK, driver suite FAILED (rc 1)`) — **the red is an environment fault, not this patch, and the
  frozen record does not say so.** The 11 failures are all in `template/tests/test_verify_base.py`
  (e.g. `:184`, `:111`, `:269`), asserting `PDCA_VERIFY_BASE == "UNSET"` and getting
  `origin/pdca-integration/main`. Cause: issue_449 is a wave>0 bundle carrying a `stack-base`
  marker, so `gates.py:533` exports `PDCA_VERIFY_BASE` into the T3 gate process itself, and
  that var leaks into the subprocesses `test_verify_base` spawns. I reproduced it exactly —
  `PDCA_VERIFY_BASE=origin/pdca-integration/main python3 -m unittest tests.test_verify_base`
  → `FAILED (failures=11)`, same count — and the whole suite is **green** without it (`Ran 1627
  tests … OK (skipped=2)`) with the patch applied. Nothing in `patch.diff` touches
  `test_verify_base.py`, `gates.py` or `publish.read_stack_base`. Human call only on whether a
  non-gating red left unexplained in the frozen record is acceptable at sign-off; **this is not
  a refutation of the fix** (issue #236) and is pre-existing test-isolation debt.

## Refutations attempted that failed

The red→green evidence held up under direct re-execution, and the fix survived every input I
could aim at it:

- **Is the red leg real?** Reverted only the production hunks (`flow.py`, `leaves.py`) to
  `HEAD` in a scratch copy, kept the test: `FAILED (failures=5)`, all on substantive assertions
  (`'PLANNED' != 'COMPLETE'`), **not** an ImportError — so it is not a PDCA-UNVERIFIABLE
  masquerading as red. Post-fix: `Ran 5 tests … OK`. The test drives the real `flow.flow_ids` /
  `flow.flow` entry points and the real `split.accept`, not a re-implementation.
- **Does adoption evict already-scheduled work?** `_reschedule` replaces `wave_list[k+1:]`
  wholesale (`flow.py:860`) from `partition_schedulable`, which is stricter than the
  `compute_waves` validation the run started with. Built the case — drive set `{500, 700}`,
  700 `Depends on: 500`, 500 splits — expecting 700 to be held out as "unresolved". It is not:
  the split parent is COMPLETE by the time `_adopt_split_children` runs, so the disk resolution
  at `waves.py:269-271` satisfies it. All four bundles reached COMPLETE.
- **Is the "transitive, bounded" claim (`flow.py:741-745`) real?** Chained a second split
  (500 → 601, 602; then 601 → 701, 702). Grandchildren were adopted and completed
  (`[[500], [601], [602, 701, 702]]`), and the `known`/`examined` guards stopped re-adoption.
- **Can the patch-less split parent crash the newly-reachable fold?** Changing `k < last` to
  `k < len(wave_list) - 1` (`flow.py:1097`) makes the parent's wave fold where it previously
  would not. `integrate.fold` filters on `_has_patch` (`integrate.py:160`), so a close-
  disposition parent with no `patch.diff` drops out — no raise.
- **Can a hand-edited lineage record break it?** `split.read_lineage` is total by construction
  (`split.py:373-391`), the traversal guard at `flow.py:762-766` rejects a child id resolving
  outside `cfg.bundle_root`, and both adoption sites sit inside `_isolate`.
- Also probed and could not break: adoption vs. the `flow_ids` Plan pre-pass (a just-accepted
  split leaves the parent BUILT, not terminal, so it survives the drive-set filter); duplicate
  adoption of a child already in the batch; held children still reaching the results map.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C1 Spec — Confirm the behavior is not semantically superseded by prior flow/split work — the affected-path merged-history and closed-unmerged-PR scans found no competing implementation, but equivalence remains a product judgment (`docs/07-crosscutting.md:243`).
- [ ] T3 Runtime — Decide whether the unavailable rendered-suite evidence is acceptable — the focused tests and all 1,627 offline driver tests pass now, but the recorded T3 runner failed earlier and its exact `run-suite.sh` plus `copier` toolchain were unavailable (root render/update tests therefore skipped).
- [ ] T4 Contribution — Confirm the contribution artifacts still satisfy policy — the recorded gate is green, but its `./scripts/pdca contribcheck` command and the commit/PR artifacts were not supplied and could not be independently rerun.
- [ ] Validation — fitness-to-purpose — Decide whether same-call descendant adoption is the right operator behavior after the run-wide budget defect is corrected — it deliberately expands the work performed beyond the ids literally named (`template/agents/planner.md.jinja:164`).
- [ ] `template/src/pdca_harness/flow.py:414-421` — **the single-id path adopts a
- [ ] `template/src/pdca_harness/flow.py:864-865` and `flow.py:894` — **the
- [ ] `check-gates.json` row **T3** (`"result": "fail"`, evidence `== T3: root suite

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
- Iteration delta (if iterating): Rejected on two implementation defects; the adoption mechanism itself (detect/validate/splice/report, transitive + bounded traversal) is sound — keep it. 1) Run budget: `max_passes` must be a RUN-WIDE cap, but `_drive_and_act` hands the full budget to every wave (`template/src/pdca_harness/flow.py:1045`) — `max_passes=2` completed the parent plus two child waves. Enforce the cap across all waves including adopted ones, and add the missing run-budget boundary test to `template/tests/test_flow_adopt_split.py` (the T5 gap that let this through). 2) Adoption announcement: report each child's REAL wave index from the recomputed schedule, not the hardcoded parent-index+1 (`flow.py:864-865`, `:894`) — the existing test asserts "into wave 1" for a child actually driven in wave 2; fix both report sites and the assertions. 3) RULING (b) on stale-split adoption: adopting stranded children of a parent split in an EARLIER run is accepted as intended recovery behavior — do NOT restrict adoption to this-run splits. Instead make both entry points consistent (`flow.flow` single-id and `flow.flow_ids` must both adopt on identical disk state; today `flow_ids` filters the terminal parent out before adoption runs, `flow.py:1258-1260`) and correct the brief/docs claim "behaviour changes only when a split happens during a run" to state the recovery semantics honestly. 4) The T3 gate red (11 failures in `template/tests/test_verify_base.py` — `PDCA_VERIFY_BASE` leaking into its subprocesses) is a pre-existing harness test-isolation fault hitting every stacked bundle; NOT this patch's defect, out of scope. Do not chase it; expect the same non-gating red on the rebuild.
- By / date: Eduard Ralph / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
