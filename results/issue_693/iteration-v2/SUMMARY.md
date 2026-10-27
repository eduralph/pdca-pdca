# Result — issue 693 / flow-run-with-holds-exits-3

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A stack-mode `pdca flow` run that holds an accepted bundle out of its integration line, and finishes everything else, exits 0. The held bundle's work is on no line of the run, and the only signal is stderr. A script or CI job cannot tell that run from a clean one. The exit code comes from `cli._results_rc` (`template/src/pdca_harness/cli.py:679-690`): 0 iff every bundle in the results map is COMPLETE/RESOLVED. A held bundle IS COMPLETE (built, signed off, published; only the fold left it out). Two holds produce this when the held bundle has no in-batch dependent (a held dependent stays PLANNED, which already makes rc 1):
  - the #593 hold: an accepted bundle that pushed no branch this run (`held_unpushed`, `template/src/pdca_harness/flow.py:2295`, filled at `:2518-2525`);
  - the #674 hold: an accepted bundle whose branch conflicts with a same-wave bundle merged before it (`held_conflict`, `flow.py:2300`, filled by the fold at `:2529-2546`, reported again at the end of the run, `:2572`).
  `_drive_and_act` returns only `{id: state}` (`flow.py:2560`, `:2573`), so nothing about either hold reaches `cli`.
- Success criterion: A `pdca flow` run that held at least one bundle for the #593 or the #674 reason, and in which every bundle in its results map otherwise reached COMPLETE/RESOLVED, exits **3** ("finished with holds"). The precedence is: any bundle not at a successful terminal → 1 (as today, it wins over 3); else any hold → 3; else 0. It holds for both CLI shapes (the single-id shape keeps its rule that AWAITING_SIGNOFF counts as success, `cli.py:741`). The rule is written next to `_results_rc` (its docstring) and in `docs/07-crosscutting.md` where the stack-mode holds are described (`:684-711`). Pinned by real-git tests on the `SameWaveConflict` setup of `template/tests/test_flow_same_wave_conflict.py:53-163`:
  (1) **#674 hold → 3.** Batch `10`, `11`, `12` (wave 0) and `21` with `Depends on: 12` (wave 1). `10` and `11` change the same line of `shared.txt` (on the base) to different text; `12` and `21` add their own files. `11` is held by the wave-0 fold and has no dependent. Every result is COMPLETE. The run's exit code is 3.
  (2) **#593 hold → 3.** Same batch with no conflict (`11` adds its own file), but publishing `11` pushes no branch (the stubbed `_publish_bundle` returns False for it without pushing). `11` is held as unpushed. Every result is COMPLETE. The exit code is 3.
  (3) **No hold → 0.** Same batch, no conflict, every publish pushes. The exit code is 0.
  (4) **Failure wins.** Case (1) plus a bundle `20` with `Depends on: 11`: `20` is held PLANNED, so the exit code is 1, not 3.
  The exit code is read ONLY from what `cli._flow` returns (as `template/tests/test_flow_entrypoint_parity.py:125-130` does, with `issue_ids` = the batch, publishing on, Act off); `cli._flow` exists on `d6057eb` with this signature, so with the fix reverted the test runs and fails on its exit-code assertion. There is no fallback route: the test must not call a helper or parameter the fix adds, nor copy the rule into the test. If `flow_ids`' set-up cannot be satisfied offline through `cli._flow`, Do stops and reports that in `build-notes.md` rather than switching route.
  Pre-fix, (1) and (2) return 0. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Carry "this run held bundle(s) X for reason R" from `_drive_and_act` to the CLI's exit-code decision, for `held_unpushed` and `held_conflict`. Mechanism, pinned (695 builds on it): the `{id: state}` return type and contract of `_drive_and_act`, `flow_ids` and `flow_batch` stay UNCHANGED (they are combined as `skipped | _drive_and_act(...)`, `flow.py:2824`, `:2671`, and indexed by ~70 test call sites). The hold signal travels separately, as an optional keyword-only collector `holds: dict[str, str] | None = None` that `cli._flow` creates and passes through `flow_ids` / `flow_batch` into `_drive_and_act`, which fills it with `{bundle id: reason}` (`"unpushed"` / `"conflict"`); `None` means no caller listens, so every existing call site is untouched. The CLI's exit-code decision reads it and return 3 per the criterion's precedence in both CLI shapes. Document exit code 3 in `_results_rc`'s docstring and in `docs/07-crosscutting.md`'s stack-mode hold paragraphs, and mention it in the `flow` subcommand's help or epilog (`cli.py:170`). The stdout result lines stay as they are (`state<TAB>…`); a held bundle still reads COMPLETE. / out of scope: the #646 carry's `held_finished` (its holds only ever hold a PLANNED dependent, which already makes rc 1); merge mode; dry-run (stub publisher) runs, which hold nothing; a last-wave or single-wave accepted bundle that pushed no branch (no fold runs after it, so it is never in `held_unpushed`; a separate gap if wanted); any change to the return type of `_drive_and_act` / `flow_ids` / `flow_batch`; `pdca status` output; any new state value; changing which bundles are held or the stderr wording.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #693: make `pdca flow` exit 3 when an otherwise successful run holds accepted work out of an integration fold, preserving failure precedence and both CLI shapes.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance rule distinguishes unfinished work (1), successful terminals with holds (3), and clean completion (0), with explicit last-wave exclusions and single-id sign-off semantics (`brief.md:12`, `brief.md:20`, `brief.md:25`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes produces five exit-code assertion failures (`0 != 3`), including both hold reasons, CSV entry, and single-id adoption; all 31 tests load and run (`review-evidence/red.log:82`; `template/tests/test_flow_hold_exit_code.py:220`). |
| C3 Change | PASS | The patch stays within the specified reporting contract: terminal-state maps and hold decisions remain intact, and all CLI routes receive the run's hold signal (`template/src/pdca_harness/cli.py:648`, `template/src/pdca_harness/cli.py:681`, `template/src/pdca_harness/flow.py:2583`). |
| C4 Verification (red→green) | PASS | Restoring the production changes makes all 31 focused tests pass, including clean-run 0 and failure-over-hold 1; the independent result agrees with the frozen gate (`review-evidence/green.log:4`; `template/tests/test_flow_hold_exit_code.py:235`, `template/tests/test_flow_hold_exit_code.py:246`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Real Git folds reproduce the lost hold information through `cli._flow`, with branch-ancestry assertions; carrying that information fixes the exit decision without a capability probe or symptom guard (`template/tests/test_flow_hold_exit_code.py:152`, `template/tests/test_flow_hold_exit_code.py:217`; `template/src/pdca_harness/cli.py:717`). |
| T1 Structure | PASS | Existing library callers retain the dictionary return contract and optional collector defaults; both reporting shapes share one precedence rule (`template/src/pdca_harness/flow.py:2592`, `template/src/pdca_harness/cli.py:694`, `template/src/pdca_harness/cli.py:771`, `template/src/pdca_harness/cli.py:789`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and whitespace check pass; the documentation explains the operator-visible distinction and its boundary (`review-evidence/docs-lint.log:2`, `review-evidence/docs-render.log:3`, `review-evidence/diff-check.log:3`; `docs/07-crosscutting.md:711`). |
| T3 Runtime | PASS | Independent driver run passes 2,467 tests with two skips; root render/update coverage rests on the frozen 24-test passing run because this review interpreter lacks importable Copier (`review-evidence/driver-suite.log:1817`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`, `review-evidence/root-suite.log:7`). |
| T4 Contribution | N/A | Contribution artifacts are deliberately not drafted at Check; the deferred gate explicitly requires its substantive audit at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art clearance across affected paths — the brief records merged and closed/unmerged work for the two production files, but this one-commit, no-remote snapshot cannot independently establish that clearance or coverage of the docs/test paths (`brief.md:30`; `review-evidence/prior-art.log:1`, `review-evidence/prior-art.log:20`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the documented automation contract and limited coverage — exit 3 distinguishes these two fold holds, while last-wave unpushed work remains outside scope and single-id sign-off stops still count as successful terminals (`docs/07-crosscutting.md:711`; `template/tests/test_flow_hold_exit_code.py:296`). |

Source citations beginning `template/` or `docs/` were checked against `$PDCA_TARGET` (`target/`); other citations refer to this review bundle. The disposable target identifies its base as `d6057ebc8c9b31987a2e145f487e9cec76181768`, matching the brief. After the stash/restore experiment, `git apply --reverse --check ../patch.diff` succeeds and no stash remains. No source patch was authored during review.

The independent red/green command was `PYTHONPATH=src python3 -m unittest tests.test_flow_hold_exit_code tests.test_flow_single_driver`, run in `target/template` with temporary files confined to this review root. Five hold cases fail before the fix; all eight new cases and 23 existing single-driver cases pass afterward. The added single-id split-parent tests now exercise real holds, including AWAITING_SIGNOFF, so the iteration concern in `brief.md:42` is discharged. The production-import scanner also passes (`review-evidence/prod-path.log:2`).

The root-suite rerun exits 77 because `/usr/bin/python3` cannot import Copier; it is not independent root-suite verification. The frozen log explicitly shows rendering and update-compatibility cases passing, so this is a reviewer-host limitation, not a patch defect or an unmet dependency in the captured gate run. Python and real Git exercised the scoped failure; stubbed leaves, publisher orchestration, and `gh` responses do not prevent this topology from producing it. No live-host publishing claim is inferred.

Prior-art investigation was performed by all five affected file paths; the available history contains only the synthetic base and no remote. The brief's five previously deferred human findings (`brief.md:42`) are not included in this input bundle and are not discharged by this review. The only supplied INTEGRATION file leaves its project-specific human-only list as a template TODO (`template/docs/INTEGRATION.md.jinja:80`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 693 (flow-run-with-holds-exits-3)

Lens: correctness bugs the patch introduces, plus reuse, simplification and efficiency.

I found no correctness bug. The two items below are small, and neither needs a human.

## What I checked

- **Every path still fills the hold signal.** In `_drive_and_act`, every early stop in the wave loop is a `break` (`template/src/pdca_harness/flow.py:2517`, `:2552`, `:2567`). A `break` still reaches the new fill at `flow.py:2583-2585`. The only early `return` is `return {}` at `flow.py:2371`, and that happens before any fold, so nothing has been held yet. A raised `PreflightError` (`flow.py:2442`) leaves `holds` empty, but `cli._flow` returns 1 on that path anyway.
- **The keys match the results map.** `holds` is keyed with the same `n.replace("issue_", "")` step that builds `results` (`flow.py:2570` and `:2584-2585`). Every held id is also a key of the returned map.
- **The two hold kinds never overlap.** The fold only looks at bundles that are not already unpushed (`flow.py:2543`), so the two `update` calls can't overwrite each other.
- **The precedence matches the brief.** `cli._results_rc` (`template/src/pdca_harness/cli.py:716-719`) returns 1 first. It returns 3 only when everything else succeeded and `holds` is not empty. The single-id shape still counts AWAITING_SIGNOFF as success, and that case is now tested (`test_a_single_id_run_stopped_for_sign_off_still_exits_3_for_its_hold`).
- **The return types are unchanged.** `_drive_and_act`, `flow_ids` and `flow_batch` still return `{id: state}`. `holds` is an optional keyword argument, so existing call sites are untouched.
- **The tests were red before the fix.** The C4 gate log (`gate-logs/C4-verify.log`) shows 5 of the 8 new tests failing without the fix and all passing with it. The 5 are the two hold cases, the CSV case, and both single-id hold cases. Last round's finding was that the single-id test could not fail. Real single-id cases over a split parent now cover it, including the 3-over-0 check (`template/tests/test_flow_hold_exit_code.py` around `:285-306`).
- **The test fixture edit is minimal.** The `*rest` pass-through in `template/tests/test_flow_single_driver.py:806-813` is the smallest change that keeps that existing probe working with the new `_report_batch` argument.

## Findings

- NEEDS-HUMAN [impl] — `template/tests/test_flow_hold_exit_code.py:238` and `:292`: `self.assertNotIn("held", self.err)` is a broad substring check over all of stderr. Any unrelated stderr line that happens to contain "held" (for example a future #646 carry note) would fail the no-hold cases for the wrong reason. The positive tests already match the exact phrases `"held out of the integration fold"` and `"pushed no branch this run"`. Asserting those two exact phrases are absent would be more precise and would match the other tests. This is a robustness nit; the tests pass today.
- `template/src/pdca_harness/flow.py:2584-2585` (minor, no action needed): the `sorted(...)` on `held_unpushed` only fixes the order keys go into a dict that callers only check for emptiness. It is harmless and cheap. Dropping it would be a little simpler, but keeping it makes the order predictable for #695, which plans to build on this signal.

Nothing found on the reuse or efficiency lens. The patch reuses the existing `held_unpushed` / `held_conflict` records and the existing id-key step instead of tracking holds a second time. The added work runs once per run, at the end.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm prior-art clearance across affected paths — the brief records merged and closed/unmerged work for the two production files, but this one-commit, no-remote snapshot cannot independently establish that clearance or coverage of the docs/test paths (`brief.md:30`; `review-evidence/prior-art.log:1`, `review-evidence/prior-art.log:20`).
- [ ] Validation — fitness-to-purpose — Accept the documented automation contract and limited coverage — exit 3 distinguishes these two fold holds, while last-wave unpushed work remains outside scope and single-id sign-off stops still count as successful terminals (`docs/07-crosscutting.md:711`; `template/tests/test_flow_hold_exit_code.py:296`).
- [ ] `template/tests/test_flow_hold_exit_code.py:238` and `:292`: `self.assertNotIn("held", self.err)` is a broad substring check over all of stderr. Any unrelated stderr line that happens to contain "held" (for example a future #646 carry note) would fail the no-hold cases for the wrong reason. The positive tests already match the exact phrases `"held out of the integration fold"` and `"pushed no branch this run"`. Asserting those two exact phrases are absent would be more precise and would match the other tests. This is a robustness nit; the tests pass today.
- [ ] **The brief leaves the "carry" mechanism open, so a large API change can come in with it.** The Scope says only "Carry 'this run held bundle(s) X for reason R' from `_drive_and_act` to the CLI". It doesn't say how. `_drive_and_act`, `flow_ids` and `flow_batch` are all typed `-> dict[str, str]`, and their returns are combined as `skipped | _drive_and_act(...)` (`flow.py:2824`, `:2671`). That map is called in 71 places in 14 test files: 50 in `test_flow_slice.py`, plus the peer `test_flow_same_wave_conflict.py:158-160,177`, which indexes `self.results[iid]`. If Do changes the return type to a tuple or dataclass, it has to touch all of them. That is a second, much larger change, and the brief's claim that the test file "shares no lines with files other bundles in this batch edit" wouldn't hold. Fix: state in the brief that the `{id: state}` return type and contract stay unchanged, and that the hold signal travels separately (an optional out-parameter or collector passed from `cli._flow` through `flow_ids`/`flow_batch` into `_drive_and_act`). Or, if you want the return type to change, list every file that change touches as in scope.
- [ ] **The test's fallback route contradicts the brief's own RED rule.** The Success criterion allows "drive `flow._drive_and_act` and pass its return through the same CLI function `cli._flow` uses to turn a run into an exit code". The Falsifiability line says the test must use "never a symbol the fix adds". On main, the functions that turn a run into an exit code are `_report_single`/`_report_batch`/`_results_rc`, and they take only `results`. If the fix adds a hold-aware helper or new parameter, the fallback test has to call it. Then, with the fix reverted, the test fails with an AttributeError or TypeError, not on its assertions, and the C4 revert gate's RED is not the RED the brief describes. Fix: require the `cli._flow` route, as in `test_flow_entrypoint_parity.py:125-130`. Or limit the fallback to calling only functions that already exist on `d6057eb`, with their current signatures.
- [ ] **The "Invariant to restore" promises more than the criterion delivers.** It says "0 means … every accepted bundle's work is on the line the run says it built." But the #593 hold and the fold only run when `k < len(wave_list) - 1 and do_publish` (`flow.py:2503`, `:2518`). Two cases fall outside that. An accepted bundle in the last wave, or in a single-wave batch, whose publish pushed no branch (`flow.py:2490-2495`) is never put in `held_unpushed`, stays COMPLETE, and still exits 0 after this fix. And no last-wave bundle is ever folded. The criterion tests only `held_unpushed`/`held_conflict`, so a Check reviewer holding the patch to the invariant as written will find it unmet. Fix: either narrow the invariant to "work the run held out of a fold it performed (#593/#674)", or deliberately add "accepted but pushed no branch, in any wave" to scope with its own test case. The issue's "Done when" names only the #593 and #674 holds, so narrowing fits the thread.
- [ ] **I couldn't verify the Ordering note's "no shared code regions".** The bundle has no `dependency-state.json`, and I have no brief for 671 or 672. The brief says 672 edits "the fold's skip handling". The only fold call in the run sits inside `_drive_and_act` at `flow.py:2531-2546`, where it reads and writes `held_conflict`. This slice must hook into that same `held_conflict`/`held_unpushed` state, either at `:2518-2546` or at the return at `:2562-2573`. If 672 changes which bundles the fold skips (`held_out=` at `:2537`), the two slices are in the same wave and depend on the same set. The human should confirm 672's hunks against `flow.py:2518-2573` before both run in wave 0. Also, 695's declared `Depends on: 693` means this slice's signal becomes an API that 695 relies on. That is one more reason to pin the mechanism (first finding) now.
- [ ] T5 Judgment — Decide whether the recorded prior-art search sufficiently excludes duplicate or rejected work across the affected paths — the brief records merged/closed searches for CLI and flow, but this target has only a synthetic base commit and no remote, so independent historical confirmation is unavailable; `brief.md:30`, `review-prior-art.log:2`.

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — `template/tests/test_flow_hold_exit_code.py:238` and `:292`: `self.assertNotIn("held", self.err)` is a broad substring check over all of stderr. Any unrelated stderr line that happens to contain "held" (for example a future #646 carry note) would fail the no-hold cases for the wrong reason. The positive tests already match the exact phrases `"held out of the integration fold"` and `"pushed no branch this run"`. Asserting those two exact phrases are absent would be more precise and would match the other tests. This is a robustness nit; the tests pass today.. Deferred, not addressed here: 5 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
