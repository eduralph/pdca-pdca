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

Review of issue 449: make every flow entry point adopt split descendants into later waves within one run, under one pass budget and lineage-scoped scheduling.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is explicit: adoption must agree across entry points, follow lineage transitively, and spend one run-wide budget (`docs/07-crosscutting.md:243`, `docs/07-crosscutting.md:256`, `docs/07-crosscutting.md:309`). |
| C2 Reproduction (red pre-fix) | PASS | With only production hunks reverted, all 8 focused tests executed and produced 9 assertion failures because split children stayed PLANNED; the entry-point assertions ground at `template/tests/test_flow_adopt_split.py:214` and `template/tests/test_flow_adopt_split.py:236`. |
| C3 Change | FAIL | Do not accept until stale-parent recovery has entry-point budget parity and traverses terminal split children: `flow()` charges an observation-only pass at `template/src/pdca_harness/flow.py:390`, while `_adoptable` drops a terminal split child before examining its descendants at `template/src/pdca_harness/flow.py:792`. |
| C4 Verification (red→green) | PASS | The same 8-test module changed from 9 assertion failures without production hunks to 8/8 passing with them restored, exercising real `flow_ids` and `flow` calls at `template/tests/test_flow_adopt_split.py:222` and `template/tests/test_flow_adopt_split.py:242`. |
| C5 Causal adequacy | PASS | The approach removes the frozen-drive-set cause by lineage-seeding and post-wave rescheduling, not by a capability probe or load-time guard (`template/src/pdca_harness/flow.py:1044`, `template/src/pdca_harness/flow.py:1094`). |
| T1 Structure | PASS | Scheduling remains centralized in `_drive_and_act`, while held-item reporting is shared with the resume path rather than duplicated (`template/src/pdca_harness/flow.py:706`, `template/src/pdca_harness/flow.py:996`). |
| T2 Shape | PASS | Independent docs lint and site rendering completed with 22 pages and a clean link audit; the rendered contract is grounded at `docs/07-crosscutting.md:243` and `docs/07-crosscutting.md:307`. |
| T3 Runtime | FAIL | Clean driver runtime passed 1,630 tests, and the supplied 11-failure gate pattern reproduced only under leaked `PDCA_VERIFY_BASE`; nevertheless, patched probes confirmed real divergence and stranded descendants caused by `template/src/pdca_harness/flow.py:390` and `template/src/pdca_harness/flow.py:792`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether to accept the contribution metadata without an independent rerun — `commit-msg.txt` and `pr-description.md` were not supplied, so the reported T4 green is provisional; affected-path merged-history plus closed/rejected-PR checks found antecedents #354/#362/#460 but no duplicate adoption patch. |
| T5 Judgment | FAIL | Require regression cases for a two-pass stale-parent comparison and a stale 500→601→701 split chain before sign-off; the current parity test uses only the default budget at `template/tests/test_flow_adopt_split.py:252`, and no nested stale lineage case follows it. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide fitness after the C3/T3 defects are repaired and rerun the render/update suite with `copier` installed — this reviewer observed 7/7 root tests skipped without that tool, while current tight-budget and nested-stale exercises still strand children. |

### Advisory — adversary

# Adversarial review — issue_449 (flow adopts split children mid-run)

Re-ran the asserted red→green at `$PDCA_TARGET` before attacking. It holds: with only the
production hunks reverted (`flow.py`, `config.py`, `leaves.py` restored from `HEAD`,
`template/tests/test_flow_adopt_split.py` kept) the suite is **red on 9 assertions**
(`'PLANNED' != 'COMPLETE'`, `None != 'COMPLETE'`), and green 8/8 with the patch. The test
drives the real `flow.flow_ids` / `flow.flow` and builds the fixture with the production
`split.accept`, so it is not a parallel re-implementation. The findings below are what
survived that.

## Refutations

- **NEEDS-HUMAN [impl] —** `template/src/pdca_harness/flow.py:1304` calls `_is_split_parent(d)`
  **outside any `_isolate`**, and `_is_split_parent` (`flow.py:744-748`) catches only
  `OSError`. A `close-disposition` file whose bytes are not UTF-8 raises `UnicodeDecodeError`
  (a `ValueError`), which escapes `flow_ids` and kills the **whole** explicit-id run.
  Reproduced: with `results/issue_500/close-disposition` = `b"split\xff\n"`,
  `flow.flow_ids(cfg, ["500", "601"])` dies with
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 5` at `flow.py:745`
  — and `601`, a perfectly drivable named id, is never driven. `flow.flow` survives the
  same disk only because it wraps adoption in `_isolate` (`flow.py:433`). This is exactly
  the trap the sibling reader this patch builds on documents at
  `template/src/pdca_harness/split.py:382-390` ("bytes that are not UTF-8 raise
  `UnicodeDecodeError` out of the *read*, where only `OSError` was expected") — the patch
  cites `split.read_lineage` as its model and then repeats the failure it was written to
  avoid. Pre-fix `flow_ids` read no file on that branch, so the crash is new.

- **NEEDS-HUMAN [impl] —** The patch's own headline claim — "`pdca flow 500` and
  `pdca flow 500 501` behave the same on the same disk state" (`flow.py:1015-1016`,
  `docs/07-crosscutting.md` new §"Naming a parent that is already terminal…", and
  iteration-1 sign-off RULING (b), which asked for exactly this) — is **false whenever the
  budget binds**. `flow.py:388-390` charges `spent += 1` *before* the loop body, and on a
  recovery run (`pdca flow 500`, 500 already terminal on a split) the body immediately
  `break`s at `flow.py:393` having done no work; `flow.py:435` then hands adoption only
  `max_iters - spent`. `flow_ids` charges the seed parent nothing (`flow.py:1303-1315`).
  Concrete failing case, identical disk state (500 split into 601 → 602, chained,
  `max_passes=2`): `flow.flow_ids` → `('COMPLETE', 'COMPLETE')`; `flow.flow` →
  `('COMPLETE', 'PLANNED')` with "the run's pass budget is spent (1 pass(es) over 1
  wave(s))". The CLI routes one id to `flow.flow` and several to `flow_ids`
  (`cli.py:639` / `cli.py:652`), so this is user-visible exactly as the claim words it.
  Compounding it: the regression test for this axis,
  `template/tests/test_flow_adopt_split.py:252-275`, runs both entry points on the
  **default** budget (20) against children needing 2 passes — the budget can never bind, so
  it passes for the wrong reason on precisely the property RULING (b) asked to fix. A
  binding-budget case belongs in that test.

- **NEEDS-HUMAN —** Making `[driver].max_passes` a run-wide cap (`flow.py:1027-1028`,
  `:1059-1067`, `:1089`; `config.py:293-299`) changes behaviour for **every** multi-wave
  batch, including ones with no split anywhere — not only adopting runs, which is all
  RULING (1) needed. Concrete: six bundles in a linear `Depends on` chain (six waves, one
  pass each) with `max_passes=5` — pre-fix all six reach COMPLETE; post-fix the run stops
  with "the run's pass budget is spent (5 pass(es) over 5 wave(s))" and `705` is abandoned
  PLANNED. At the shipped default of 20 this truncates any CSV sweep or id list whose waves
  × passes exceed 20 (a deep chain, or ~10 waves at 2 passes each) — runs that completed
  before. `brief.md:225` still asserts "no config key is added and none changes meaning";
  that claim is now false and was not corrected, and no default was raised. Human call:
  raise the default, or scope the run-wide cap to runs that actually adopted. (Related, if
  the cap stays: `flow.py:985-986` now reports the *remaining* allowance — "pass budget
  exhausted after 1 pass(es); raise `[driver].max_passes`" while `max_passes` is 20 —
  which reads as a contradiction to the operator it is addressed to.)

- **NEEDS-HUMAN —** `flow.py:1043-1047` swaps the **strict** levelling for the tolerant one
  whenever a seed adopts, so an explicit id list gets two different failure contracts
  depending on unrelated disk state. `waves.partition_schedulable`'s own docstring
  (`waves.py:243-246`) says raising is "right for an explicit `flow <ids>` / `pdca waves`
  request". Demonstrated: with `800`/`801` in a mutual `Depends on` cycle,
  `pdca flow 800 801` raises `ValueError: dependency cycle: issue_800 → issue_801 →
  issue_800`; adding one *unrelated* stranded split parent — `pdca flow 500 800 801` —
  returns normally, holds both (loudly, to be fair) and drives 500's children. Whether an
  explicit request should silently degrade to resume-sweep tolerance because some other
  named id happens to carry a readable lineage record is a contract decision, not a detail;
  the comment at `flow.py:1035-1042` rationalises it without acknowledging that the same
  id list now behaves two ways.

- **NEEDS-HUMAN [impl] —** `flow.py:763` documents the third `_adoptable` filter as "one
  already in this run's drive set (`known`) is named and dropped", but `flow.py:785-786`
  drops it with a bare `continue` and no message — so `pdca flow 500 601` (parent + one of
  its own children) silently says nothing about 601 while naming every other skip. Minor,
  but this repo treats a docstring claim as load-bearing.

## Attempted and could not refute

- **The evidence.** Red→green reproduces on the production path (above); the test exercises
  the real entry points, never a helper, and the split is produced by production
  `split.accept`, so the fixture is not a mirror of the fix.
- **Transitive adoption.** Built a two-level split (500 → 601,602; 601 → 701,702) driven
  through `flow_ids`: waves `[500] [601,602] [701,702]`, all five COMPLETE, both adoptions
  announced with their real wave index. The brief's "transitively, bounded" claim holds.
- **The splice vs. existing later waves.** `flow 500 501 502` with `502 → 501 → 500` and a
  mid-run split of 500 yields `[500] [501,601,602] [502]` — nothing dropped, nothing driven
  twice, `501`'s ordering preserved. I could not construct an input where the reschedule
  loses a listed bundle without also reporting it via `_report_held`.
- **Scope.** Could not get an explicit-id flow to widen into a `results/` sweep; the
  `known` / `examined` sets do bound re-adoption.
- **T3's red is not this patch.** The full offline driver suite runs **1630 tests, OK** at
  `$PDCA_TARGET` with the patch applied. The gate red reproduces only with the env var set:
  `PDCA_VERIFY_BASE=HEAD python3 -m unittest tests.test_verify_base` → 11 failures. That
  matches the carry-forward's "pre-existing harness test-isolation fault" and is not
  attributable to this diff.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Decide whether to accept the contribution metadata without an independent rerun — `commit-msg.txt` and `pr-description.md` were not supplied, so the reported T4 green is provisional; affected-path merged-history plus closed/rejected-PR checks found antecedents #354/#362/#460 but no duplicate adoption patch.
- [ ] Validation — fitness-to-purpose — The maintainer must decide fitness after the C3/T3 defects are repaired and rerun the render/update suite with `copier` installed — this reviewer observed 7/7 root tests skipped without that tool, while current tight-budget and nested-stale exercises still strand children.

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Decide whether to accept the contribution metadata without an independent rerun — `commit-msg.txt` and `pr-description.md` were not supplied, so the reported T4 green is provisional; affected-path merged-history plus closed/rejected-PR checks found antecedents #354/#362/#460 but no duplicate adoption patch.
- By / date: auto-iterate / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
