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

Review issue #693: make stack-mode `pdca flow` exit 3 when completed work was held out of an integration fold, while preserving failure precedence and existing output.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance rule distinguishes unfinished work (1), finished work with holds (3), and clean completion (0), with explicit single-id and last-wave boundaries; brief.md:12, brief.md:20, target/docs/07-crosscutting.md:711. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the two production changes reproduced five assertion failures returning 0 instead of 3, including both hold reasons and all CLI routes; review-red.log:1, target/template/tests/test_flow_hold_exit_code.py:234, target/template/tests/test_flow_hold_exit_code.py:245. |
| C3 Change | PASS | The patch stays within the specified exit-status contract, preserves result maps and stdout, and carries both hold reasons through the requested entry points; target/template/src/pdca_harness/cli.py:648, target/template/src/pdca_harness/cli.py:681, target/template/src/pdca_harness/flow.py:2583. |
| C4 Verification (red→green) | PASS | Restoring the production changes made all eight regression cases pass, including failure precedence, CSV, split-parent single-id, and sign-off success; the 23 single-driver tests also pass; review-green-test_flow_hold_exit_code.py.log:3, review-green-test_flow_single_driver.py.log:3. |
| C5 Causal adequacy | PASS | Real Git folds demonstrate the forbidden false-success result, and the exit rule now receives the previously lost hold information; no capability probe or symptom guard was introduced; target/template/tests/test_flow_hold_exit_code.py:161, target/template/tests/test_flow_hold_exit_code.py:231, target/template/src/pdca_harness/cli.py:717. |
| T1 Structure | PASS | Existing callers retain their result-map contract through optional keyword-only collectors, and both presentations share the same precedence rule; target/template/src/pdca_harness/flow.py:2602, target/template/src/pdca_harness/flow.py:2728, target/template/src/pdca_harness/cli.py:694. |
| T2 Shape | PASS | Independent whitespace checking, documentation lint, and rendering of 22 pages with internal-link audit passed; CLI help and user documentation state the new status; target/template/src/pdca_harness/cli.py:170, target/docs/07-crosscutting.md:715, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent offline suite passed 2,467 tests with two skips; frozen evidence separately shows all 24 root render/update tests passing, which this reviewer cannot rerun without Copier; review-suite.log:1817, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is required again at publish, so the deferred result is not a verification failure; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by every affected file path — the brief records searches for cli.py and flow.py only, and the supplied one-commit snapshot has no remote or historical PR evidence to verify those searches or coverage of the documentation/tests; brief.md:30. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept whether status 3 provides sufficient operational distinction while stdout still says COMPLETE and last-wave unpushed work remains outside scope — these are deliberate user-facing boundaries requiring sign-off; target/docs/07-crosscutting.md:711, target/docs/07-crosscutting.md:720. |

All source citations above refer to the supplied `$PDCA_TARGET` (`target/`), not another checkout. Its synthetic base identifies `d6057eb`, matching the brief, and `git apply --reverse --check patch.diff` succeeded against the patched tree. I stashed only `cli.py` and `flow.py`, retained the regression tests for the red run, restored the stash, and checked that the tracked diff was byte-for-byte unchanged. No target-state caveat was needed.

Independent execution used Python 3.14.4 and Git 2.53.0. From `target/template`, with `PYTHONPATH=src`, I ran `python3 -m unittest discover -s tests -p test_flow_hold_exit_code.py` before and after restoration, the corresponding command for `test_flow_single_driver.py` after restoration, and then `python3 -m unittest discover -s tests`. Temporary test files were confined under this review directory. The five red failures were exit-code assertions, not import errors or unavailable-tool failures. The other three regression cases passed before the fix. The prior iteration's broad stderr substring check is now restricted to the two actual hold phrases (`target/template/tests/test_flow_hold_exit_code.py:220`), and the single-id hold now runs through a real split-parent adoption (`target/template/tests/test_flow_hold_exit_code.py:298`).

The production-import scanner was independently rerun from `target/template/scripts/checks/test_exercises_production.py` with `PDCA_PROD_PACKAGE=pdca_harness` and this review directory as `PDCA_BUNDLE`; it confirmed the added test imports production. Code inspection and the red→green run establish more than that import heuristic: the tests call `cli._flow`, perform actual Git conflict folds, and check branch ancestry. Build/sign-off, publishing orchestration, and GitHub responses are stubbed, but the topology does exhibit the forbidden failure. The brief's Python/Git dependencies were exercised; this is not evidence of live GitHub publication, nor does the scoped fix require that service.

The instance-scoped gate wrappers were adjudicated from their captured logs where unavailable locally. `gate-logs/C4-verify.log` records the same five assertion failures and restored green tests; `gate-logs/C5-prod-path.log:10` records the import check; both documentation logs show clean lint and link audits. Independent documentation commands were `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-5o_zys1_/review-site`, run from `target/`. Copier is not installed in the reviewer interpreter, but the frozen root-suite log explicitly shows render and update-compat tests executing successfully (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`), so this local limitation is not an undischarged dependency of the recorded gate.

For prior art, `git log --all -- <all five affected paths>` returned only synthetic base commit `09f0c11`; `git remote -v` returned nothing, and `git show-ref` showed only the local master branch. The human should confirm the brief's history/closed-PR assessment for `template/src/pdca_harness/cli.py` and `template/src/pdca_harness/flow.py`, and cover `docs/07-crosscutting.md`, `template/tests/test_flow_hold_exit_code.py`, and `template/tests/test_flow_single_driver.py`. No additional concrete human-only rule can be extracted from the supplied integration template: its enumeration remains TODO (`target/template/docs/INTEGRATION.md.jinja:80`).

No builder-fixable defect was found. This report is advisory; the two human decisions above remain owed.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 693 (flow-run-with-holds-exits-3)

I found no correctness bugs and no reuse problems that need action. Nothing here needs a human decision.

## Correctness

- `template/src/pdca_harness/flow.py:2583-2585` — The hold collector uses the same keys as the results map. Both strip the prefix with `d.name.replace("issue_", "")` (`flow.py:2570`), so every held id is also a key of `results`. A bundle can't be in both sets: the fold skips `held_unpushed` bundles before it can mark one as a conflict (`flow.py:2543`). If one ever were in both, the second `update` would just overwrite the reason, and the exit code would not change.
- `template/src/pdca_harness/flow.py:2547-2552`, `:2563-2567` — Early `break`s (an integration error or a failed re-gate) still reach the end, where the collector is filled. Those breaks only happen when `k < len(wave_list) - 1`, so a later wave's bundles stay PLANNED and the run exits 1. That matches the brief's rule that a failure wins over 3. `PreflightError` skips the fill, but `cli.py:668-670` returns 1 in that case anyway.
- `template/src/pdca_harness/cli.py:694-719` — `_results_rc` checks for 1 first, then 3, then 0, which is the order the brief asks for. An empty results map can't come with a non-empty `holds`, so the early `return 0` in `_report_batch` (`cli.py:780-782`) doesn't hide a hold.
- `template/src/pdca_harness/cli.py:640-682` — The collector reaches all three paths: `flow_batch`, then `flow_ids` reported by `_report_single`, then `flow_ids` reported by `_report_batch`. The return types of `_drive_and_act`, `flow_ids` and `flow_batch` are unchanged, as the brief requires. Existing callers that don't pass `holds` get `None` and behave as before.
- `template/tests/test_flow_hold_exit_code.py` — The C4 gate log (`gate-logs/C4-verify.log:24-104`) shows all five hold cases fail with the fix reverted (`0 != 3`) and pass with it. The no-hold and failure-wins cases pass both ways, which is expected. The test imports only modules (`:316`). Iteration 2's point is addressed: `_assert_held_nothing` (`:489-492`) now checks for the two exact hold phrases, not the bare word "held". Iteration 1's point is addressed too: the single-id shape now gets a real hold through a split-parent recovery run (`:552-590`).
- `template/tests/test_flow_single_driver.py:803-812` — Changing the spy to `report(results, *rest)` passes `holds` through, so that test still runs `_report_batch` the same way.

## Reuse / simplification

- `template/src/pdca_harness/flow.py:2584` — Optional nit: the `sorted(...)` around `held_unpushed` has no effect, because it fills a dict whose order nothing reads. Leaving it is harmless.

The diff looks clean on both counts: no new correctness bugs, and no logic that an existing helper already covers.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by every affected file path — the brief records searches for cli.py and flow.py only, and the supplied one-commit snapshot has no remote or historical PR evidence to verify those searches or coverage of the documentation/tests; brief.md:30.
- [x] Validation — fitness-to-purpose — Accept whether status 3 provides sufficient operational distinction while stdout still says COMPLETE and last-wave unpushed work remains outside scope — these are deliberate user-facing boundaries requiring sign-off; target/docs/07-crosscutting.md:711, target/docs/07-crosscutting.md:720.
- [x] **The brief leaves the "carry" mechanism open, so a large API change can come in with it.** The Scope says only "Carry 'this run held bundle(s) X for reason R' from `_drive_and_act` to the CLI". It doesn't say how. `_drive_and_act`, `flow_ids` and `flow_batch` are all typed `-> dict[str, str]`, and their returns are combined as `skipped | _drive_and_act(...)` (`flow.py:2824`, `:2671`). That map is called in 71 places in 14 test files: 50 in `test_flow_slice.py`, plus the peer `test_flow_same_wave_conflict.py:158-160,177`, which indexes `self.results[iid]`. If Do changes the return type to a tuple or dataclass, it has to touch all of them. That is a second, much larger change, and the brief's claim that the test file "shares no lines with files other bundles in this batch edit" wouldn't hold. Fix: state in the brief that the `{id: state}` return type and contract stay unchanged, and that the hold signal travels separately (an optional out-parameter or collector passed from `cli._flow` through `flow_ids`/`flow_batch` into `_drive_and_act`). Or, if you want the return type to change, list every file that change touches as in scope.
- [x] **The test's fallback route contradicts the brief's own RED rule.** The Success criterion allows "drive `flow._drive_and_act` and pass its return through the same CLI function `cli._flow` uses to turn a run into an exit code". The Falsifiability line says the test must use "never a symbol the fix adds". On main, the functions that turn a run into an exit code are `_report_single`/`_report_batch`/`_results_rc`, and they take only `results`. If the fix adds a hold-aware helper or new parameter, the fallback test has to call it. Then, with the fix reverted, the test fails with an AttributeError or TypeError, not on its assertions, and the C4 revert gate's RED is not the RED the brief describes. Fix: require the `cli._flow` route, as in `test_flow_entrypoint_parity.py:125-130`. Or limit the fallback to calling only functions that already exist on `d6057eb`, with their current signatures.
- [x] **The "Invariant to restore" promises more than the criterion delivers.** It says "0 means … every accepted bundle's work is on the line the run says it built." But the #593 hold and the fold only run when `k < len(wave_list) - 1 and do_publish` (`flow.py:2503`, `:2518`). Two cases fall outside that. An accepted bundle in the last wave, or in a single-wave batch, whose publish pushed no branch (`flow.py:2490-2495`) is never put in `held_unpushed`, stays COMPLETE, and still exits 0 after this fix. And no last-wave bundle is ever folded. The criterion tests only `held_unpushed`/`held_conflict`, so a Check reviewer holding the patch to the invariant as written will find it unmet. Fix: either narrow the invariant to "work the run held out of a fold it performed (#593/#674)", or deliberately add "accepted but pushed no branch, in any wave" to scope with its own test case. The issue's "Done when" names only the #593 and #674 holds, so narrowing fits the thread.
- [x] **I couldn't verify the Ordering note's "no shared code regions".** The bundle has no `dependency-state.json`, and I have no brief for 671 or 672. The brief says 672 edits "the fold's skip handling". The only fold call in the run sits inside `_drive_and_act` at `flow.py:2531-2546`, where it reads and writes `held_conflict`. This slice must hook into that same `held_conflict`/`held_unpushed` state, either at `:2518-2546` or at the return at `:2562-2573`. If 672 changes which bundles the fold skips (`held_out=` at `:2537`), the two slices are in the same wave and depend on the same set. The human should confirm 672's hunks against `flow.py:2518-2573` before both run in wave 0. Also, 695's declared `Depends on: 693` means this slice's signal becomes an API that 695 relies on. That is one more reason to pin the mechanism (first finding) now.
- [x] T5 Judgment — Decide whether the recorded prior-art search sufficiently excludes duplicate or rejected work across the affected paths — the brief records merged/closed searches for CLI and flow, but this target has only a synthetic base commit and no remote, so independent historical confirmation is unavailable; `brief.md:30`, `review-prior-art.log:2`.
- [x] T5 Judgment — Confirm prior-art clearance across affected paths — the brief records merged and closed/unmerged work for the two production files, but this one-commit, no-remote snapshot cannot independently establish that clearance or coverage of the docs/test paths (`brief.md:30`; `review-evidence/prior-art.log:1`, `review-evidence/prior-art.log:20`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
