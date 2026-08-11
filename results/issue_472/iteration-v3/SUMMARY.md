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

Reviewing mid-run adoption of split children on the unified flow path, including dependency scheduling, shared pass budgeting, guard behavior, and operator reporting.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief makes the mid-run-only boundary, lineage scope, run-wide budget, held-child behavior, and exclusions falsifiable, so no planning decision remains unresolved. |
| C2 Reproduction (red pre-fix) | PASS | The isolated base-plus-test leg executed all 22 tests and failed 21, including the child-terminal assertions that capture the stranded-child symptom (`template/tests/test_flow_adopt_split.py:322`). |
| C3 Change | PASS | The requested adoption, scheduling, budgeting, guard, documentation, and fixture-cleanup surfaces stay within the declared slice, with the shared splice seam located at `template/src/pdca_harness/flow.py:929`. |
| C4 Verification (red→green) | PASS | Independent reruns produced 22 tests/21 failures before the production hunks and 22/22 passing after them; docs lint/link audit, 7 copier render/update tests, and all 1,655 driver tests also passed (`template/src/pdca_harness/flow.py:1265`). |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Rebuild decision: make lineage containment resolution-aware—the lexical `d.parent` check accepts an `issue_<id>` symlink resolving outside the bundle root, and my probe returned that external target as adoptable, so the escape guard is incomplete (`template/src/pdca_harness/flow.py:881`). |
| T1 Structure | PASS | Every CLI shape reaches one mutable wave loop and one adoption seam, avoiding a second entry-point implementation (`template/src/pdca_harness/flow.py:786`). |
| T2 Shape | PASS | Diff whitespace, documentation lint, and rendered-site link audit passed, and the operator-facing budget/adoption contract remains internally linked (`docs/07-crosscutting.md:243`). |
| T3 Runtime | PASS | The real Python and copier toolchains exercised the feature, full driver, render, and update-compat paths with no skips attributable to missing tools; the primary runtime behavior is asserted through `cli._flow` (`template/tests/test_flow_adopt_split.py:322`). |
| T4 Contribution | NEEDS-HUMAN | Release-text approval is still owed—`commit-msg.txt` and `pr-description.md` were not supplied, so the user-impact opener and #472 linkage required by the contribution rule cannot be independently audited (`template/pdca.toml.jinja:960`). |
| T5 Judgment | PASS | No conflicting prior art remains: affected-path history covers the merged lineage/flow work, and the complete closed-PR corpus has only one unmerged rejection, which touched `README.md` rather than any affected path. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Ship-or-iterate remains the human decision—automatic transitive adoption changes orchestration, pass-budget exhaustion, and stderr/results semantics, so maintainers must confirm that operational trade-off is desirable (`template/src/pdca_harness/flow.py:1171`). |

### Advisory — adversary

# Adversarial review — issue #472 (flow-adopt-core)

Advisory only; nothing here gates. Every `path:line` is on the target source at
`/home/eddie/pdca/pdca-harness.pdca-wt`. Toolchain was fully available (python3, git) —
no provisional verdicts.

## What I attacked and could not refute

- **The red→green is real, and it is the production path.** I reproduced C4 independently
  by rebuilding the base from `git show HEAD:` for the four production modules and keeping
  only the new test: **21 of 22 tests fail pre-fix, 22/22 pass post-fix** (the one that
  passes pre-fix, `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`
  `test_flow_adopt_split.py:503`, is by construction a no-regression guard). Every test
  drives through `cli._flow` (`test_flow_adopt_split.py:158`) and builds fixtures with the
  production `split.accept` (`split.py:525`) — no parallel re-implementation, no simulated
  split. Full offline driver suite: **1655 tests, OK**.
- **The suite is not over-broad.** I ran 24 targeted mutations of the production hunks;
  23 were killed. Notably: dropping the traversal guard (`flow.py:881`), the in-record
  dedup (`flow.py:873`), the terminal half of `_is_split_parent` (`flow.py:827`), the
  retraction block (`flow.py:1030`), `budget = allowance * len(wave_list)` →
  `allowance` (`flow.py:1216`), `min(allowance, budget - spent)` → `allowance`
  (`flow.py:1260`), `return used` → `return 0` on **both** un-finished `_drive_wave`
  exits (`flow.py:1105`, `flow.py:1144`), `k < len(wave_list) - 1` → a length cached
  before the loop (`flow.py:1312`), narrowing the marker catch to `OSError`
  (`flow.py:832`), and the brief's own required mutation `known=batch_names | taken` →
  `known=batch_names` (`flow.py:1001`), which fails exactly
  `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` — the test the
  docstring cites at `flow.py:976`, as the brief demands.
- **The only surviving mutation is provably unobservable**, not a hole: `return sorted(out,
  key=lambda p: p.name)` → `return out` at `flow.py:903` survives, because the wave levelling
  (`waves.compute_waves`) and the announcement (`', '.join(sorted(...))`, `flow.py:1045`)
  both re-sort. No finding.
- **I could not break the pool arithmetic.** `spent >= budget` (`flow.py:1226`) provably
  cannot fire on a non-adopting run (`spent ≤ allowance·k` after `k` waves, `budget =
  allowance·len(wave_list)`), `budget - spent ≥ 1` whenever `_drive_wave` is reached, and
  `spent` can never exceed `budget`. Probed a 10-deep recursive split chain at
  `--max-passes 20`: terminates at 10 waves / 20 passes, rc 1, correctly named.
- **I could not break the splice on hostile lineage records.** Probed absolute ids
  (`"/etc/shadow"`), a non-list `children` value, a dependency **cycle** between two adopted
  children, `flow_batch` (CSV shape) adoption, a child declaring `Depends on <the split
  parent>`, and a child conflicting with an un-driven named tail bundle. All degrade to a
  report and rc 0/1 as documented — no traceback, no double-drive, no bundle outside
  `cfg.bundle_root`, `bundles` and `batch_names` stay in sync across every splice and
  retraction.
- **I could not find a wrong citation.** I checked all ~30 `path:line` citations the patch
  adds or updates (`split.py:373/382-390/296-311/525/627-634/635`, `flow.py:675/678/758/
  1141/1255/1260`, `config.py:686`, `waves.py:243-246`, `gates.py:782`,
  `test_flow_slice.py:32-55/1122-1128/1137`, and both rewritten `cli.py:609-610` targets
  `flow.py:1450-1464` / `flow.py:1485-1491`). All resolve exactly, including the two
  `cli.py` line numbers the previous rounds churned on.

## Findings

- **NEEDS-HUMAN [human] — `check-gates.json:84-93` records the *gating* T4 row as `pass`, but
  it attests nothing.** `gate-logs/T4-contribution.log` shows `exit 0`, `duration 0s`,
  `(no output captured)`, and the bundle directory contains **neither `commit-msg.txt` nor
  `pr-description.md`**. The target's own checker says that is not a pass: `cli.py:1094-1100`
  prints `gates.DEFERRED_MARKER` when `pr-description.md` is absent, precisely so the matrix
  records `deferred — re-gated at publish` "instead of a vacuous green the reviewer cannot
  reproduce" (`cli.py:1075-1083`, issue #401). So either the checker that ran is not the one
  this repo ships, or the row was recorded as `pass` where the contract says `deferred`;
  either way the row's own claim ("user-impact opener + tracker id in **both artifacts**")
  has no subject and the recorded green is not reproducible. This is **not** caused by the
  diff — but it is the third consecutive round the carry-forward has raised it
  (`brief.md:112`, `brief.md:117`) and two auto-iterate rebuilds did not move it, so routing
  it back to Do a third time would be wasted. A human has to decide whether a gating T4
  `pass` may stand on absent artifacts.

- **NEEDS-HUMAN [impl] — `flow.py:1003` prints a claim that `flow.py:1019-1021` then makes
  false, producing exactly the "one situation, two report shapes" the patch's own docstring
  (`flow.py:956-960`) exists to prevent.** `taken` is grown from `_adoptable`'s return
  *before* `_reschedule` runs, so a child the reschedule then **holds** is still reported to a
  second parent as "already in this run's drive set" — while it is in neither the drive set
  nor the results map. Concrete, reproduced case: `pdca flow 500 700`, both split in wave 0,
  `700`'s lineage record also names `602` (hand-edit / re-plan), and `602`'s brief carries an
  unresolvable `Depends on: GHOST`. stderr then carries both
  `flow: issue_602 — child of issue_700 not adopted again: already in this run's drive set`
  (`flow.py:890-891`) and `flow: issue_602 held this run — unresolved dependency (GHOST)`
  (`flow.py:776-777`), with `results == {500, 700, 601, 801}` — `602` excluded. The end state is
  correct (one hold, no double adoption), so this is report-only, but the first line is a
  false statement about the run's drive set at exactly the moment an operator is reading the
  log to find out who owns `602`. Not covered by any test: the shared-child tests
  (`test_flow_adopt_split.py:880`, `:847`) only exercise the case where the shared child is
  schedulable. Builder-fixable (report the skip after the reschedule, or re-report the held
  child against the parent that was refused).

- **NEEDS-HUMAN [impl] — `flow.py:895-896` prints the raw lineage id, re-opening the
  "uncopyable hint" hazard that `_lineage_children`'s strip at `flow.py:693-694` was written
  to close.** `_lineage_children` only strips *outer* whitespace, and its docstring justifies
  that strip as stopping "an uncopyable `pdca flow \" 469 \"` hint". The new consumer builds a
  path from the same value and then interpolates it unquoted into a resume hint. Concrete,
  reproduced case: a hand-edited record `{"children": ["6\n01", "602"]}` passes the traversal
  guard (`cfg.bundle("6\n01").parent == cfg.bundle_root`) and emits a stderr line that breaks
  in two — `flow: issue_6` / `01 — child of issue_500 NOT adopted: no brief.md (brief it at
  Plan, then \`pdca flow 6` / `01\`)`. The sibling guard one branch up already does the right
  thing (`{cid!r}`, `flow.py:882`); this branch and the "already terminal" branch
  (`flow.py:899-900`) do not. Low severity — `split.validate` (`split.py:281`) only ever
  *writes* `[A-Za-z0-9._-]+`, so it needs a hand edit — but it is a one-token fix and the
  guard's stated rationale already covers it.

## Explicitly considered and NOT filed

- The run-wide pool means a `pdca flow <id>` whose parent burns most of its 20 passes before
  splitting can adopt children and then abandon them "budget spent". That is not a
  refutation: `brief.md:19-20` scopes budget re-sizing to the sibling child, the outcome is
  named with a resume hint (`flow.py:1230-1233`), and the pre-fix behaviour stranded the same
  children with no announcement at all.
- A run whose only unfinished work is a **held** adopted child exits 0 (documented at `flow.py:990-995`).
  Checked against the base: pre-fix the identical scenario also exits 0 with the children
  stranded PLANNED, so this is not a regression, and `brief.md:23` asks for the exclusion.
- `flow.flow()` does not adopt (`flow.py:389-394`). Verified it is not a CLI route post-#468
  (`cli.py:604-622`), so the planner/doc claim "every shape" holds for every operator-facing
  shape; the library caller is documented.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Rebuild decision: make lineage containment resolution-aware—the lexical `d.parent` check accepts an `issue_<id>` symlink resolving outside the bundle root, and my probe returned that external target as adoptable, so the escape guard is incomplete (`template/src/pdca_harness/flow.py:881`).
- [ ] T4 Contribution — Release-text approval is still owed—`commit-msg.txt` and `pr-description.md` were not supplied, so the user-impact opener and #472 linkage required by the contribution rule cannot be independently audited (`template/pdca.toml.jinja:960`).
- [ ] Validation — fitness-to-purpose — Ship-or-iterate remains the human decision—automatic transitive adoption changes orchestration, pass-budget exhaustion, and stderr/results semantics, so maintainers must confirm that operational trade-off is desirable (`template/src/pdca_harness/flow.py:1171`).
- [ ] `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
- [ ] `cli.py:794`: `pdca split <id> --accept` — the command the Plan /
- [ ] Fitness-to-purpose, for sign-off: a first-reschedule-held child is
- [ ] T4 in `check-gates.json` is the one gating row that carries an

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
- Iteration delta (if iterating): Auto-iterate (round 3): rebuilding for the implementation-level findings — C5 Causal adequacy — Rebuild decision: make lineage containment resolution-aware—the lexical `d.parent` check accepts an `issue_<id>` symlink resolving outside the bundle root, and my probe returned that external target as adoptable, so the escape guard is incomplete (`template/src/pdca_harness/flow.py:881`).; T4 Contribution — Release-text approval is still owed—`commit-msg.txt` and `pr-description.md` were not supplied, so the user-impact opener and #472 linkage required by the contribution rule cannot be independently audited (`template/pdca.toml.jinja:960`).. 4 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
