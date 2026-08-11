# Result — issue 472 / flow-adopt-core

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** on byte-identical disk state:
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes `close-disposition = split` while
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

Review of the mid-run split-adoption core: drive lineage children in later waves through the unified flow path under one pre-adoption pass budget.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The decision boundary is explicit: adopt only terminal split descendants created during this run, while terminal-parent recovery and reporting refinements remain separate (`docs/07-crosscutting.md:243`). |
| C2 Reproduction (red pre-fix) | PASS | In a target-derived copy with production hunks reversed, all 21 focused tests executed and 20 failed by leaving children undriven; the principal assertion is at `template/tests/test_flow_adopt_split.py:322`. |
| C3 Change | PASS | The patch stays within the adoption core and its accepted hermetic-test cleanup: scheduling, shared-budget accounting, operator guidance, docs, and tests are the surfaces needed for the stated contract (`template/src/pdca_harness/flow.py:929`). |
| C4 Verification (red→green) | PASS | Independent red→green ran 21 tests on both legs (20 failures before, all 21 passing after), and removing same-wave `taken` dedup separately failed the adversarial test at `template/tests/test_flow_adopt_split.py:823`. |
| C5 Causal adequacy | PASS | The change removes the frozen-schedule cause by recomputing and splicing the live tail, then charges adopted waves through the existing drive loop; it does not add an optional-capability probe around a load-time symptom (`template/src/pdca_harness/flow.py:1172`). |
| T1 Structure | PASS | Adoption is composed once into `_drive_and_act`, while held reporting is shared with the resume path, preserving one implementation for every CLI shape (`template/src/pdca_harness/flow.py:1226`). |
| T2 Shape | PASS | Docs lint and site rendering/link audit both pass, and the published semantics align adoption, lineage scope, holds, and budget behavior (`docs/07-crosscutting.md:243`). |
| T3 Runtime | PASS | The full offline driver suite passes 1,654 tests (2 skipped), compileall succeeds, and the ambient-base cleanup passes 19 tests even with all three outer base variables set (`template/tests/test_verify_base.py:74`). |
| T4 Contribution | NEEDS-HUMAN | The release-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be independently rerun and the user-impact opener plus #472 linkage remain unaudited. |
| T5 Judgment | PASS | The affected-path audit across merged history and all closed/unmerged GitHub work found no conflicting prior art; the only rejected PR touches `README.md`, outside this patch's seven affected paths (`template/src/pdca_harness/flow.py:929`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The operator-semantics decision is owed — confirm that stderr-only held-child reporting and a pool fixed from the original schedule are acceptable, because those choices determine whether same-run adoption communicates unfinished work honestly (`docs/07-crosscutting.md:257`). |

### Advisory — adversary

# Check - adversarial review (advisory, non-gating)

Lens: refute the red-green evidence and the reviewer's verdict; find the input that breaks
the fix. Everything below is grounded on the target source at
`/home/eddie/pdca/pdca-harness.pdca-wt` and on runs I performed against a copy of it.

## What I could not refute

- **The red leg is real.** Reverting only the production hunks (`flow.py`, `config.py`,
  `leaves.py`) and keeping the new module: **20 of 21 tests fail**; the single pre-fix pass
  is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`, which is deliberately a
  no-regression control. Post-fix 21/21 green, and the whole driver suite is green
  (1654 tests, OK, skipped=2).
- **The tests exercise production, not a parallel copy.** Every drive goes through
  `cli._flow` (`test_flow_adopt_split.py:158`), and the spies at
  `test_flow_adopt_split.py:258-273` are pass-throughs that call the real `_drive_wave` /
  `_build_all` / `_point_at_integration` and return the production value, so the budget
  accounting under assertion is the real one. `_capture_results`
  (`test_flow_adopt_split.py:284`) wraps the real `flow.flow_ids`.
- **Mutation battery: 18 of 20 mutants killed.** Dropping `taken` from `known`
  (`flow.py:985`), either `_adoptable` guard (`flow.py:894`, `flow.py:898` - the two the
  previous round reported unpinned), the bundle-root escape check (`flow.py:881`), the
  `seen` dedup (`flow.py:873`), the run-pool break (`flow.py:1187`), the `min(allowance,
  budget - spent)` hand-down (`flow.py:1221`), charging the pool at all (`flow.py:1220`),
  either un-finished `return used` (`flow.py:1073`, `flow.py:1112`), the live
  `len(wave_list) - 1` fold test (`flow.py:1273`), the terminal half of `_is_split_parent`
  (`flow.py:827`), the total `except` (`flow.py:832`), the real-wave read-back
  (`flow.py:1002`), `scheduled`-only growth of `bundles` (`flow.py:1003`) and of
  `batch_names` (`flow.py:1005`), and `partition_schedulable` tolerance (`flow.py:917`) are
  each caught by a named test. The only surviving mutant is cosmetic (`sorted(...)` at
  `flow.py:903`).
- **Attacked and failed:** `flow_batch`/CSV parity (adoption does fire there:
  `{'500': 'COMPLETE', '601': 'COMPLETE', '602': 'COMPLETE'}`); a Plan **pre-pass** split
  under `cli._flow`'s unconditional `plan_missing=True` (`cli.py:614`) - I expected the
  parent to go terminal before the drive set is built and strand the children, but
  `split.accept` leaves a *pending* disposition, so the parent is still non-terminal at the
  filter and is adopted normally; `Conflicts with` between adopted children (honoured -
  601 and 602 land in separate waves, though no test pins it); a dependent of the split
  parent (`Depends on 500`) - it re-levels into the children's wave exactly as
  `flow.py:970-974` discloses; traversal / odd child ids (`../../etc`, `..`, `a b`, `/`) -
  all reported and skipped, no crash; `max_passes=0` - unreachable from the CLI, which
  treats the falsy value as unset; a recursion cycle (a child record naming its own
  grandparent) - bounded by `batch_names`, run finished rc 0. `integrate.fold` filters on
  `_has_patch` (`integrate.py:160`), so the patchless split parent whose wave now folds
  cannot raise `IntegrationError` and stall the adopted waves.

## Findings

- NEEDS-HUMAN [impl] - `flow.py:975` (and the same claim at `flow.py:948-950`) states an
  invariant the run does not keep: "A child the reschedule HELD is excluded from the results
  map, so a run whose only unfinished work is a held child still exits 0" / "never joins the
  results map". That holds only for a child held by the reschedule that **first** sees it.
  A child adopted by an earlier call joins `bundles` and `batch_names` at
  `flow.py:1003-1005` and is never removed when a **later** call holds it. Concrete,
  reproduced case: `pdca flow 500 700` with `700` declaring `Depends on 500`; `500` splits
  in wave 0 into `601`/`602`, `602`'s brief names `Depends on 700`; `700` halts
  AWAITING_SIGNOFF while `601` completes and itself splits in wave 1. The second
  `_reschedule` (`flow.py:917`) sees `700` outside its set and not COMPLETE, so it holds
  `602`. Observed: stderr carries BOTH `issue_500 split -> adopted children issue_602 into
  wave 2` AND `issue_602 held this run - unresolved dependency (700)`, and the results map
  comes back `{'500': COMPLETE, '700': AWAITING_SIGNOFF, '601': COMPLETE, '602': PLANNED,
  '801': COMPLETE, '802': COMPLETE}` - `602` is announced as adopted, is in the map, and
  is never driven. So the same situation ("a child this run created and could not
  schedule") produces two different report shapes and potentially two different exit codes
  depending only on *when* the hold happens. Either drop a late-held child from
  `bundles`/`batch_names` (and retract the announcement), or narrow the two docstring
  claims to "the reschedule that first schedules it".

- NEEDS-HUMAN [impl] - `config.py:312` cites `config.py:671` for the clamp
  ("Clamped below ``max_passes`` (``config.py:671``)"), but line 671 is
  `max_passes = int(driver_cfg.get("max_passes", 20))` - the *read*. The clamp is
  `max_auto_iters = min(max_auto_iters, max(1, max_passes - 1))` at `config.py:685`. This
  comment is the exact site iteration 1's carry-forward flagged ("`config.py:312-314` now
  states an invariant the patch breaks"); the invariant text was rewritten but the new
  citation a reader is asked to follow lands on the wrong statement. The peer citations in
  the same block (`flow.py:1221`, `flow.py:1109`) and elsewhere in the patch
  (`flow.py:758`, `split.py:635`, `split.py:373`, `cli.py:622`, `test_flow_slice.py:1137`,
  the three new docs anchors) all resolve correctly, so this is the one outlier.

- NEEDS-HUMAN [human] - Fitness-to-purpose, for sign-off: a first-reschedule-held child is
  excluded from the results map on purpose, so the run **exits 0** while leaving a bundle it
  created PLANNED and undriven - pinned as intended behaviour at
  `test_flow_adopt_split.py:731` and reasoned at `flow.py:975-979`. The brief does ask for
  exactly this ("excluded from the results map ... the run continues"), so this is not a
  build defect; but the outcome is a milder form of the defect the issue exists to fix (a
  split's child stranded, with the only signal on stderr). Unattended automation reading the
  exit code sees a clean success. The human should confirm that "this run created work it
  could not schedule" belongs on stderr rather than in the exit code, since a driver that
  auto-iterates on rc will never come back for it.

- NEEDS-HUMAN [human] - T4 in `check-gates.json` is the one gating row that carries an
  empty `path_line` (no quotable oracle line), and the contribution artifacts
  (`commit-msg.txt`, `pr-description.md`) are bundle files, so they are neither in
  `patch.diff` nor in this station's inputs. I therefore could not re-run or audit the
  release-facing impact text - the same carry-forward iteration 1 raised. Per issue #236
  this inability is **not** scored as a refutation; the T4 verdict is simply provisional
  from here and needs the human's eye at sign-off.

## Verdict

The core mechanism holds up under attack: the evidence is a genuine red-to-green on the
production path, the guards the brief names are pinned by mutation-resistant tests, and I
could not find an input that makes a run crash, lose a bundle, drive one twice, or exceed
the operator's pass budget. The two `[impl]` items are a false docstring invariant with a
reproduced counter-example and a mis-aimed citation; neither touches the drive mechanics.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — The release-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be independently rerun and the user-impact opener plus #472 linkage remain unaudited.
- [ ] Validation — fitness-to-purpose — The operator-semantics decision is owed — confirm that stderr-only held-child reporting and a pool fixed from the original schedule are acceptable, because those choices determine whether same-run adoption communicates unfinished work honestly (`docs/07-crosscutting.md:257`).
- [ ] `flow.py:975` (and the same claim at `flow.py:948-950`) states an
- [ ] `config.py:312` cites `config.py:671` for the clamp
- [ ] Fitness-to-purpose, for sign-off: a first-reschedule-held child is
- [ ] T4 in `check-gates.json` is the one gating row that carries an
- [ ] `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
- [ ] `cli.py:794`: `pdca split <id> --accept` — the command the Plan /

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — T4 Contribution — The release-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be independently rerun and the user-impact opener plus #472 linkage remain unaudited.; `flow.py:975` (and the same claim at `flow.py:948-950`) states an; `config.py:312` cites `config.py:671` for the clamp. 4 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
