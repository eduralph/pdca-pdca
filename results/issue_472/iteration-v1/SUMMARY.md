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

Task under review: adopt the children of a bundle that splits during `pdca flow`, scheduling and driving them in later waves under the original run-wide pass budget.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decision-complete: lineage-scoped, transitive adoption, tolerant holds, deduplication, real wave reporting, and the original-schedule budget are all observable through the CLI fixture at `template/tests/test_flow_adopt_split.py:322`. |
| C2 Reproduction (red pre-fix) | PASS | The production-reverted leg executed all 20 focused tests and failed 18 because split children remained undriven, directly reproducing the operator restart at `template/tests/test_flow_adopt_split.py:333`. |
| C3 Change | PASS | The change stays within the adoption core and its documented/test support; adopted children enter the shared drive path and ordinary later-wave handling at `template/src/pdca_harness/flow.py:1220`. |
| C4 Verification (red→green) | PASS | Independent red→green rerun executed 20 tests on each leg (18 failures without production hunks; 20 passes with them), grounding the criterion at `template/tests/test_flow_adopt_split.py:322`. |
| C5 Causal adequacy | PASS | The frozen drive set is removed as the cause by extending and re-waving the shared run state, rather than guarded by a capability probe or alternate entrypoint, at `template/src/pdca_harness/flow.py:1151`. |
| T1 Structure | PASS | Adoption is decomposed into detection, validation, rescheduling, and one splice while `_drive_and_act` remains the sole execution path, limiting parity risk at `template/src/pdca_harness/flow.py:929`. |
| T2 Shape | PASS | Diff whitespace validation, documentation lint, and the 22-page rendered-site link audit all pass; the public contract covers wave, lineage, hold, and budget semantics at `docs/07-crosscutting.md:243`. |
| T3 Runtime | PASS | The focused suite, full offline driver discovery, and all seven Copier render/update-compat tests pass with the patched target; pass accounting is exercised at `template/tests/test_flow_adopt_split.py:397`. |
| T4 Contribution | NEEDS-HUMAN | The contribution-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the asserted checker pass cannot be independently rerun and release-facing impact text remains unaudited. |
| T5 Judgment | PASS | Shared-path placement preserves the merged #468 architecture, and affected-path searches found the relevant merged lineage/flow prior art but no closed-unmerged PR collision; the remaining boundary is explicitly documented at `template/src/pdca_harness/flow.py:967`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide whether automatic transitive adoption, stderr-only holds, and a pool fixed to the original wave count match operator expectations — these choices change run duration and unfinished-work visibility despite green automation at `docs/07-crosscutting.md:257`. |

### Advisory — adversary

# Adversarial review — issue_472 (flow: adopt split children mid-run)

Ground: `$PDCA_TARGET` = `/home/eddie/pdca/pdca-harness.pdca-wt` (HEAD `3e3b829`, patch applied
in the worktree). Red leg reproduced in a copy with the production hunks reverted
(`git checkout -- flow.py config.py leaves.py docs/ planner.md.jinja test_verify_base.py`,
new test kept).

## Findings

- NEEDS-HUMAN [human] — `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
  self-declared carve-out at `flow.py:969-973`: a bundle that declared `Depends on <the id
  that splits>` is re-levelled by its **own** edges and lands in the **same wave as the
  children that parent decomposed into**. Concrete, run at the target: `pdca flow 500 811
  812` where `811` declares `Depends on: 500` and `812` declares `Depends on: 811`, and
  `500` splits mid-run into `601`/`602`, drives
  `[['issue_500'], ['issue_601','issue_602','issue_811'], ['issue_812']]` and folds wave 1 as
  `['issue_500','issue_601','issue_602','issue_811']`. `811` declared it must build *after*
  `500`'s work; that work now lives in `601`/`602`, which build concurrently with it (in
  parallel under `lanes>1`) and are then folded together — so a patch conflict between `811`
  and a child now hits `integrate.fold` and stops the run ("wave 1 did not integrate;
  STOPPING — later waves not run", `flow.py:1290-1293`) in a configuration that pre-fix could
  not produce one. The docstring calls re-pointing a dependent "a `waves` semantics change,
  deliberately out of this scope"; the brief never mentions the case and no test pins it.
  Human call: accept the degraded edge, or scope a follow-up.

- NEEDS-HUMAN [impl] — `config.py:312-314` now states an invariant the patch breaks:
  "`max_auto_iters` … Clamped below `max_passes` so a wave's pass budget can't run out
  mid-auto-iteration (which #260 would then report as abandoned)". `flow.py:1221` hands a
  wave `min(allowance, budget - spent)`, which for an **adopted** wave can be far below
  `max_passes`. Concrete: `[driver].auto_iterate = true`, `max_passes = 20` (so
  `max_auto_iters` clamps to ≤ 19, default 3), `pdca flow 500` → `budget = 20 × 1`; the
  parent's wave spends 18, the adopted child's wave gets 2, and a child with 3 automatic
  rounds available exhausts its allowance mid-auto-iteration and is reported abandoned —
  exactly what the clamp exists to prevent. The patch rewrote the comment block immediately
  above this one (`config.py:294-301`) and left this neighbour stale; either the clamp text
  must acknowledge the pool or the adopted wave's allowance needs a floor.

- NEEDS-HUMAN [impl] — `template/tests/test_flow_adopt_split.py:821`
  (`test_an_unreadable_close_marker_never_kills_the_run`) is **green on the red leg**.
  Measured: reverting the production hunks leaves 18/20 failing; the two survivors are this
  guard and the deliberate no-adoption regression test at `:503`. Every assertion it makes
  (`601` PLANNED, `_adoptions() == []`, no `Traceback`, no `split adoption failed`, rc 0) is
  satisfied trivially by a build that has no adoption at all, so it cannot distinguish "the
  probe swallows `UnicodeDecodeError`" from "there is no probe". The brief's falsifiability
  says "The guard tests are red pre-fix by the same route" — this one is not. It is not
  worthless (narrowing `flow.py:832` to `except OSError` does fail it), but the cheap fix is a
  second, *readable* split parent in the same run whose children **are** adopted, so the test
  asserts a difference adoption makes.

- NEEDS-HUMAN [human] — `cli.py:794`: `pdca split <id> --accept` — the command the Plan /
  re-plan leaf runs *inside* the flow — still prints "`issue_500` marked split; run `pdca flow
  601 602` to drive the children". Post-fix that instruction, followed while the run is still
  going, starts a **second driver over the same child bundles**; the drive path takes no
  per-bundle lock (the only `flock`s reachable from `_drive_and_act` are `integrate`'s,
  `flow.py:1287`/`flow.py:1300`). The brief rules the hint out of scope because it is "still right for a
  split accepted outside a running flow" — but the case this feature creates is a split
  accepted *inside* one, which is precisely where the hint is now wrong. Human call: leave it
  (and the double-drive window) or make the hint conditional.

- NEEDS-HUMAN [impl] — `flow.py:894` and `flow.py:898`: both `_adoptable` guards are unpinned.
  Mutating away `if not d.exists() or s == state.UNPLANNED` and `if s in _TERMINAL` leaves all
  20 tests green (verified). Minor — neither is on the brief's enumerated "proven by test"
  list — but the fixture already has the hand-edited-record hook, and I confirmed by probe
  that `_record(iid, ["601", "999"])` prints `issue_999 — child of issue_500 NOT adopted: no
  brief.md`; one `assertIn` in an existing test closes both.

## Refutations attempted and failed

- **The red→green claim is honest.** With the patch: `cd template && PYTHONPATH=src python3 -m
  unittest tests.test_flow_adopt_split` → 20/20 OK. With production reverted and the test kept
  → 18 failures. The suite drives through `cli._flow` (`test_flow_adopt_split.py:158`) and
  builds fixtures with the production `split.accept`, not a re-implementation. The full driver
  suite at the target is green (1653 tests, OK, skipped=2), so T3's row holds too.
- **The brief's mandated mutation behaves exactly as specified**: `known=batch_names | taken`
  → `known=batch_names` (`flow.py:985`) fails exactly
  `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` and nothing else, and the
  docstring at `flow.py:959-961` cites that test by name.
- **13 further mutations, all killed**: hardcoded `k + 1` announcement index (4 fails);
  `budget = allowance * (len(wave_list) + 1)` (5); fold boundary from a cached wave count (1);
  `except OSError` in `_is_split_parent` (1); dropping its terminal predicate (1); the stall
  exit returning 0 passes (1); removing the run-level `spent >= budget` break (3); handing each
  wave the full `allowance` (2); dropping `_report_held` from `_reschedule` (2); `bundles +=
  children` instead of `scheduled` (1); dropping the `seen` dedup (1); dropping the
  bundle-root traversal guard (1); not growing `batch_names` (1); narrowing the budget-break
  abandonment report to `wave_list[k+1:]` (3).
- **Budget/termination could not be broken.** Before wave *i*, `spent ≤ i·allowance` and
  `budget = n·allowance` (`flow.py:1177`), so the pool is provably non-binding for a run that
  adopts nothing, and `min(allowance, budget - spent) = allowance` there; every *driven* wave
  costs ≥ 1 pass, so a chain of splits terminates. `budget = 0` (which would break the run at
  wave 0 before publishing anything) needs `max_passes ≤ 0`, and both entry points clamp to ≥ 1
  (`config.py:660`, `cli.py:572`) — unreachable from the CLI.
- **Traversal guard holds**: `cfg.bundle()` on `"../../etc"`, `"/etc"`, `"a/b"` all fail
  `d.parent != cfg.bundle_root` (`flow.py:881`); `".."` / `"."` pass that check but resolve to
  non-existent `issue_..` / `issue_.` and are dropped by the brief guard.
- **The CSV shape the shipped docs advertise works**, though no test covers it: I drove
  `cli._flow` with `--from-csv` and no ids (→ `flow_batch` → the same `_drive_and_act`,
  `flow.py:1370`); the children were adopted, driven and reported (`flow: 5/5 complete`).
- **A cycle among adopted children does not crash and does not abort**: both children are held
  ("dependency cycle"), the run continues and exits **0** — i.e. a `pdca flow 500` that creates
  two bundles it cannot schedule still reports success. That is the contract the brief asked
  for ("held … excluded from the results map … never aborts") and `flow.py:975-979` states it
  outright, so I record it as a conforming trade-off rather than a refutation — but it is the
  one place the reviewer's "the run answers for what it did" framing is weakest.

Toolchain note (issue #236, not a refutation): the target checkout has no `engine/scripts/` or
`scripts/pdca`, so T2 (`run-docs-check.sh`) and the gating T4 (`contribcheck`) could not be
re-run here; C4 and T3 were reproduced directly and both hold.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — The contribution-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the asserted checker pass cannot be independently rerun and release-facing impact text remains unaudited.
- [ ] Validation — fitness-to-purpose — The maintainer must decide whether automatic transitive adoption, stderr-only holds, and a pool fixed to the original wave count match operator expectations — these choices change run duration and unfinished-work visibility despite green automation at `docs/07-crosscutting.md:257`.
- [ ] `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
- [ ] `config.py:312-314` now states an invariant the patch breaks:
- [ ] `template/tests/test_flow_adopt_split.py:821`
- [ ] `cli.py:794`: `pdca split <id> --accept` — the command the Plan /
- [ ] `flow.py:894` and `flow.py:898`: both `_adoptable` guards are unpinned.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — T4 Contribution — The contribution-text decision remains owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the asserted checker pass cannot be independently rerun and release-facing impact text remains unaudited.; `config.py:312-314` now states an invariant the patch breaks:; `template/tests/test_flow_adopt_split.py:821`; `flow.py:894` and `flow.py:898`: both `_adoptable` guards are unpinned.. 2 finding(s) needing human judgment were deferred to sign-off, not addressed here.
- By / date: auto-iterate / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
