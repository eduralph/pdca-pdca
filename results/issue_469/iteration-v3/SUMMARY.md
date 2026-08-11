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
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of the enhancement that makes every unified `pdca flow` shape adopt and drive lineage-scoped children from terminal splits within the same bounded run.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is executable and unambiguous across mid-run adoption, terminal-parent recovery, scheduling, budgeting, and malformed-lineage cases at `template/tests/test_flow_adopt_split.py:434` and `template/tests/test_flow_adopt_split.py:511`. |
| C2 Reproduction (red pre-fix) | PASS | In an isolated copy, retaining all tests while reversing only production hunks executed 26 tests and failed 23, including the children remaining PLANNED assertion at `template/tests/test_flow_adopt_split.py:446`. |
| C3 Change | PASS | The change stays on the requested unified drive path, with adoption extending the live wave tail at `template/src/pdca_harness/flow.py:1271`; the ancillary environment cleanup at `template/tests/test_verify_base.py:80` discharges the iteration carry-forward rather than expanding product scope. |
| C4 Verification (red→green) | PASS | Restoring the same production hunks made all 26 focused tests green; independent broader reruns also passed 1,659 driver tests, 7 Copier render/update tests, and 19 inherited-base tests grounded at `template/tests/test_flow_adopt_split.py:434`. |
| C5 Causal adequacy | PASS | The fixed-wave cause is removed where the shared list iterator consumes a recomputed tail at `template/src/pdca_harness/flow.py:1227` and `template/src/pdca_harness/flow.py:1275`; no optional-capability probe or load-time symptom guard was introduced. |
| T1 Structure | PASS | The patch reverse-checks exactly against the target, `git diff --check` and `compileall` pass, and the single shared drive implementation begins at `template/src/pdca_harness/flow.py:1141`. |
| T2 Shape | PASS | Documentation lint and the 22-page rendered-site link audit pass, and the documented scheduling/budget contract matches the exercised behavior at `docs/07-crosscutting.md:243` and `docs/07-crosscutting.md:320`. |
| T3 Runtime | PASS | Clean-environment execution passed all 1,659 driver tests; Copier's own Python passed all 7 render/update tests, and an inherited `PDCA_VERIFY_BASE` passed all 19 isolation regressions using the cleanup at `template/tests/test_verify_base.py:80`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether to trust the frozen T4 PASS — `commit-msg.txt` and `pr-description.md` were not supplied, so the required user-impact opener and issue id in both artifacts at `template/src/pdca_harness/cli.py:1075` could not be independently audited. |
| T5 Judgment | PASS | Exact affected-path screening covered merged history and every closed/rejected PR exposed by the repository API; related lineage/flow work was merged, while the sole rejected PR touched none of the nine affected paths, so no conflicting prior art remains. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether terminal-parent transitive adoption under one run-wide budget, with held children excluded from results and therefore compatible with rc 0, is acceptable operator policy — it changes what naming a parent may execute and how automation interprets an incomplete brood (`docs/07-crosscutting.md:257`, `template/tests/test_flow_adopt_split.py:980`). |

### Advisory — adversary

# Adversarial review — issue_469 (flow: adopt split children mid-run)

Advisory only; nothing here gates. Evidence re-run at `$PDCA_TARGET`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) with python3 3.14.4, offline.

## Evidence check (red→green) — attempted refutation, could not

Reproduced independently: the whole `template/` copied to a scratch dir with **only** the
four production files reverted to `HEAD` (`flow.py`, `cli.py`, `config.py`, `leaves.py`)
and the new test kept — **23 of 26 fail** pre-fix, **26/26 pass** post-fix. The three that
stay green pre-fix (`test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
`test_a_named_id_list_keeps_its_strict_scheduling_contract`,
`test_an_unreadable_close_marker_never_kills_the_run`) are *don't-break* regression guards,
which is the correct shape for them. The suite drives through `cli._flow` and builds its
fixtures with the production `split.accept` — not a parallel re-implementation. Full driver
suite at the target: `Ran 1659 tests … OK (skipped=2)`, so the T3 row reproduces.

## Findings

- **NEEDS-HUMAN — `template/src/pdca_harness/flow.py:1216` (`budget = allowance * max(1, len(wave_list))`) with `flow.py:1236` (`if spent >= budget: break`): an adopted child can now starve an id the operator explicitly NAMED, in a run that drove it before the patch.** The pool is sized off the *pre-adoption* schedule, but adoption both adds waves to it and can insert a child **ahead** of a named id in the re-levelled tail (`_reschedule` re-runs `conflict_map`, and a conflict naming a not-yet-existing child is dropped pre-adoption and becomes real post-adoption — `waves.py:104-118`). Concrete, reproduced both legs: bundles `500` (splits into `601`), `810` briefed `Depends on: 500` + `Conflicts with: 601`, run `pdca flow 500 810 --max-passes 2`, `601` costing two passes. Pre-fix: waves `[[500],[810]]`, `810` → **COMPLETE**, rc 0. Post-fix: waves `[[500],[601]]`, pool spent (`"the run's pass budget is spent (4 pass(es) over 2 wave(s))"`), `810` left **PLANNED**, rc 1. It is loud, not silent — but the policy question is a human one: the brief asked for "ONE run-wide `max_passes` budget" and says nothing about adopted work pre-empting the ids the operator typed. Either the pool should be re-sized when the schedule grows, or named waves should be served before adopted ones; both are scope decisions, not a slip.

- **NEEDS-HUMAN — `template/src/pdca_harness/flow.py:1029` (`scheduled = [c for c in children if c.name in wave_of]`) and the assertion at `template/tests/test_flow_adopt_split.py:980` (`assertEqual(rc, 0)`): a run whose split stranded its only child still reports total success to automation.** Reproduced: `500` splits into a single child `601` whose brief names an unresolvable `Depends on: GHOST`. Result — results map `{'500': 'COMPLETE'}`, stdout `COMPLETE\t…/issue_500`, **rc 0**, `601` left PLANNED on disk. Only stderr carries `issue_601 held this run`. That is precisely the #449 symptom the brief set out to remove (a split whose children never get driven), now invisible to any caller that reads the exit code or stdout. The brief *did* ask for held children to be excluded from the results map, and the builder flags the consequence in the `_adopt_split_children` docstring (`flow.py:1000` region) — so this is a fitness-to-purpose call for the human at sign-off, not a coding error.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/cli.py:669-670` (`_report_single`): the single-id shape can print `COMPLETE` on stdout and exit 1, never naming on stdout the bundle that caused it.** Reproduced with the suite's own walk-away fixture (`pdca flow 500`, child `602` left AWAITING_SIGNOFF): stdout is exactly one line, `COMPLETE\t…/issue_500`, and rc is 1. The rc now depends on map entries the presentation never prints, which is new — pre-patch the single-id map only ever held the typed id, so stdout and rc could not disagree. The `state<TAB>path` line is the documented machine-readable contract of this shape (`cli.py:665`); automation that trusts it reads success from a failed run. Cheap fix while iterating: print the adopted children's dispositions (or one summary line naming what made the rc non-zero) alongside the typed id.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1009` (`known=batch_names | taken`): the `taken` half of the dedup key is load-bearing but unpinned — deleting it passes all 26 tests.** Mutation `known=batch_names | taken` → `known=batch_names` leaves `python3 -m unittest tests.test_flow_adopt_split` fully green. It is not dead code: with two parents splitting in the **same** wave and the second's record also naming the first's child (`500`→`601,602`, `700`→`601,801`, `pdca flow 500 700`), the mutant announces `issue_700 split → adopted children issue_601, issue_801 into wave 1` — one bundle adopted under two parents, entered twice into `bundles` (hence the results map's source list and the closing `_sweep_quietly`). The docstring at `flow.py:979-984` asserts both halves are needed and cites `test_a_child_adopted_earlier_is_not_re_adopted_by_a_later_parent` — but that test's two adoptions happen in **separate** calls (`k=-1` seed, then wave 0), so it exercises only the `batch_names` half. One test with both parents in one wave closes the gap and corrects the citation.

- **NEEDS-HUMAN — `check-gates.json` row "T4 PR body has a user-impact opener + tracker id in both artifacts": `result: pass`, `gating: true`, and `path_line: ""` — the only gating row with no recorded oracle output.** C4/T2/T3 each carry an evidence string; T4 carries none, and no `commit-msg.txt` / `pr-description.md` exists in the target worktree (`git status` shows only the seven patched files plus the new test), so the required opener and tracker linkage cannot be reproduced from the supplied inputs. This is the **third consecutive iteration** in which T4's PASS has been recorded without reproducible evidence (see the iteration-1 and iteration-2 carry-forwards in `brief.md:105,111`). Verdict on T4 is provisional at best.

## Attempted and could not refute

- **Real wave indices** — mutating `flow.py:1028` to a hardcoded `k + 1` fails 10 tests.
- **Lineage-cycle bound** (`examined`, `flow.py:1005-1007`) — the SIGALRM deadline test is a genuine termination assertion, and `_watch_examined` spies the production `_children_of_split` rather than inferring from the run returning.
- **Path escape** (`flow.py:878-880`) — I could not construct a child id that keeps `d.parent == cfg.bundle_root` while resolving outside it; `cfg.bundle` is `bundle_root / f"issue_{id}"` (`config.py:469-471`), so any separator or `..` moves the parent.
- **Total catches** — `_is_split_parent`'s bare `except` (`flow.py:827`) matches `split.read_lineage`'s own documented total catch (`split.py:397-399`); `BaseException` still propagates, and the watchdog in the test suite correctly uses a `BaseException` so `_isolate` cannot swallow the hang it proves.
- **"One drive path / every shape"** in `docs/07-crosscutting.md` and `template/agents/planner.md.jinja` — `flow.flow` has **no** production callers (only `tests/test_flow_slice.py`, `tests/test_sweep.py`), so its deliberate non-adoption cannot be reached from any CLI shape; `flow_batch` and both `flow_ids` shapes all land on `_drive_and_act`.
- **Fold boundary** — `k < len(wave_list) - 1` read live (`flow.py:1322`); reverting to a cached `last` is caught.
- **Pool hand-down** — `min(allowance, budget - spent)` (`flow.py:1270`) and `_drive_wave` returning `used` on *both* un-finished exits (`flow.py:1099`, `flow.py:1138`) are each pinned.
- **Strict admission for named ids** — `compute_waves` still runs before any adoption (`flow.py:1210`), so a cycle in the id list is refused regardless of on-disk lineage.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Decide whether to trust the frozen T4 PASS — `commit-msg.txt` and `pr-description.md` were not supplied, so the required user-impact opener and issue id in both artifacts at `template/src/pdca_harness/cli.py:1075` could not be independently audited.
- [x] Validation — fitness-to-purpose — Decide whether terminal-parent transitive adoption under one run-wide budget, with held children excluded from results and therefore compatible with rc 0, is acceptable operator policy — it changes what naming a parent may execute and how automation interprets an incomplete brood (`docs/07-crosscutting.md:257`, `template/tests/test_flow_adopt_split.py:980`).
- [ ] size backstop — this slice is behaving oversized: patch is 111 KB (threshold 100 KB); 2 round(s) already spent (threshold 2). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Size backstop: patch is 111 KB (threshold 100 KB) with 2 iterate rounds already spent — the slice is oversized; author the split in the re-plan (`pdca split`), do not rebuild it whole. The core mechanics are CONVERGED and should be preserved across the split, not re-derived: C4 red→green reproduced independently (23/26 red pre-fix, 26/26 green post-fix), and the adversary could not refute the splice, recursion bound, wave indices, path-escape guard, budget hand-down, or fold boundary. Human affirmed the fitness-to-purpose policy at sign-off: transitive/recursive adoption (children that split are re-adopted) under one bounded run-wide budget is intended (§6 Validation ticked). Carry into the children the four open adversary findings: (1) budget pre-emption — the run-wide pool is sized off the pre-adoption schedule, so an adopted child can starve an id the operator typed (flow.py:1216/:1236); decide re-sizing vs named-first service; (2) single-id shape can print COMPLETE on stdout yet exit 1 without naming the adopted bundle that caused it (cli.py:669-670); print adopted dispositions or a summary line; (3) the `taken` half of the dedup key (flow.py:1009) is load-bearing but unpinned — add a same-wave two-parents test and fix the docstring citation; (4) T4 has passed three consecutive iterations without reviewer-reproducible evidence — supply commit-msg.txt / pr-description.md to the reviewer's inputs (the artifacts exist in the bundle and check out on manual read).
- By / date: Eduard Ralph / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
