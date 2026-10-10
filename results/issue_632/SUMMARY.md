# Result — issue 632 / publish-raise-after-push-counts-as-pushed

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `flow._publish_bundle` (`template/src/pdca_harness/flow.py:642-665`) decides "this call pushed the branch" from `publish.json`'s mtime: True only if the record exists after the call and is new or changed (`flow.py:656-665`), and never when the call raised (`_isolate` returns None, `flow.py:661`). The new-PR path of `publish.publish` runs every git step, the push included (`git push --force-with-lease -u origin <branch>`, `template/src/pdca_harness/publish.py:319`, run at `:390-398`), then `gh pr create` (`publish.py:404-406`), and only then writes `publish.json` (`publish.py:431`). If `subprocess.run(pr_cmd)` RAISES after the push (e.g. `gh` is not installed: `FileNotFoundError`), no record is written. The bundle is treated as unpushed and goes into `held_unpushed`, and its dependents are skipped (`flow.py:2285-2291`), although its branch is on origin. That contradicts the stated rule: "A branch pushed this run is folded even if `gh pr create` failed after it" (`flow.py:2282-2283`). The rc-1 failure of `gh pr create` is already handled that way (`publish.py:407-414`, the record is still written with an empty `pr_url`, pinned by `test_publish_slice.py:359-381`). The raise is not, and the operator is not told the branch was pushed.
- Success criterion: With the patch, with `publish._check_repo` patched to 0 and `subprocess.run` stubbed so every `git` step succeeds and `gh pr create` raises `FileNotFoundError` (the setup of `template/tests/test_publish_slice.py:359-381`, with a raise instead of rc 1):
  Fixture for the `_publish_bundle` call: the module's `_bundle` config has a stub publisher (`test_publish_slice.py:63`), and `_publish_bundle` passes `dry_run=cfg.publisher.mode == "stub"` (`flow.py:659`), which returns before any git step and writes no record (`publish.py:334-353`). So set a non-stub publisher on the test's config (e.g. `LeafConfig(mode="command", interactive=True)`), write `commit-msg.txt` and `pr-description.md` into the bundle first, and call with `texts_prevalidated=True`, so no publisher leaf is spawned and no T4 runs (`publish.py:198-199`, `_ensure_texts` at `:56-66`).
  (1) `flow._publish_bundle(cfg, d, by=…, today=…, texts_prevalidated=True)` on that accepted bundle returns True (its branch was pushed this run). A second case, with `gh pr create` raising a non-`OSError` (e.g. `RuntimeError`), also returns True.
  (2) The fold has that branch on record, using (1)'s answer: with `pushed = {d.name} if rc else set()` from (1)'s return, `integrate.unpublished([d], pushed=pushed)` is `[]`, and `integrate._published_ref(d)` names the branch publish pushed (`fix/<id>-<slug>`, on `origin`).
  (3) Stderr says the branch is on origin, but no PR was opened, and how to finish (open the PR / re-run `pdca publish <id>`). The bundle is not reported as fully published: stderr still says publish failed or did not complete (today `_isolate` prints "publish failed (…)" for a raise, `flow.py:62-71`), so the operator knows a step is left.
  (4) **Unchanged.** When a step BEFORE the push fails or raises (stub `git push` returning rc 1, or `git apply` raising), `_publish_bundle` returns False and no branch is on record. `test_open_pr_failure_exits_nonzero` and the rest of `test_publish_slice.py` still pass.
  Pre-fix, (1) returns False and (2) finds no branch. That is the RED. Before writing the fix, the test author checks that the new test is red for THAT reason (no `publish.json`, and the git stub saw the push), not because of a dry-run.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a publish whose push succeeded count as pushed, for the flow and the fold, even when `gh pr create` raises, and make the run say the branch is on origin with no PR opened. Fix shape (chosen, so Check judges one design): in `publish.publish`, catch any `Exception` raised by the `gh pr create` call (`subprocess.run(pr_cmd)`, `publish.py:406`) and send it down the existing rc-1 path (`pr_failed = True`, the "branch pushed, but `gh pr create` FAILED" message, the record with an empty `pr_url`, return 1; `publish.py:407-436`). That is the only step between the push and the record write that can fail. `flow.py` is NOT changed: `_publish_bundle` already returns True for an rc-1 publish that wrote a record (`flow.py:649-653`, `:665`), and its docstring ("nor does a call that raised") stays true, because the call no longer raises. / out of scope: `_publish_stacked` (`publish.py:452-560`): its push is its last fallible step (`publish.py:484`); after it come only the best-effort `_restore_worktree` (`publish.py:1095-1101`, `capture_output`, no raise) and the record write (`:539-547`), so there is no post-push raise to handle; docs changes (the docs already state the rule this restores, `docs/07-crosscutting.md:672-673`, which 623 and 629 edit); retrying `gh pr create`; checking that `gh` exists before publishing (a doctor/preflight concern); the stub/dry-run publisher (pushes nothing, `flow.py:2285`); the #593 rule that an earlier run's record never counts (`flow.py:654`).

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

Review issue #632: preserve pushed-branch accounting and fold eligibility when `gh pr create` raises after a successful push, while reporting that publication remains incomplete.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The chosen scope has falsifiable outcomes for post-push exceptions, fold eligibility, operator guidance, and pre-push failures; it matches the existing partial-publish contract (`brief.md:13`, `target/template/src/pdca_harness/flow.py:649`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix made both exception cases fail at the pushed-result assertion after the push and PR-call checks passed; both pre-push controls remained green (`review-red.log:1`, `target/template/tests/test_flow_publish_raise_after_push.py:120`). |
| C3 Change | PASS | The diff stays within the selected PR-creation failure boundary and its regression tests; it preserves the record format and nonzero partial-publish result (`target/template/src/pdca_harness/publish.py:410`, `target/template/src/pdca_harness/publish.py:440`). |
| C4 Verification (red→green) | PASS | Restoring the fix passed all four regression cases, including both exception types and pre-push controls; the existing 66 publish tests also passed (`review-green.log:1`, `review-publish.log:52`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Both exceptions now reach the same durable branch record consumed by flow and fold, and tests derive fold eligibility from the actual flow result; this repairs interrupted accounting rather than masking an eager capability side effect (`target/template/src/pdca_harness/publish.py:440`, `target/template/tests/test_flow_publish_raise_after_push.py:128`, `target/template/src/pdca_harness/integrate.py:181`). |
| T1 Structure | PASS | Exception handling is confined to the external PR command, with no new dependency, public interface, or record schema; earlier git failures retain their existing behavior (`target/template/src/pdca_harness/publish.py:410`, `target/template/tests/test_flow_publish_raise_after_push.py:156`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, production-import scanner, and diff whitespace checks passed; frozen host-CI evidence also records clean lint and link checks (`review-docs.log:1`, `review-render.log:2`, `review-prod-path.log:1`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 2,373 tests with two skips; local Copier coverage was unavailable, so root render/update coverage rests on the frozen log showing 24 passing tests (`review-suite.log`, `review-root-suite.log:6`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the brief's affected-path merged-history and closed/rejected-work conclusions — the supplied snapshot has only one synthetic base commit and no remote, so those conclusions cannot be independently established here (`brief.md:31`, `review-grounding.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept whether continuing the fold while requiring the operator to finish PR creation meets the intended workflow — offline evidence establishes accounting and diagnostics, but does not demonstrate a live hosted PR recovery (`target/template/tests/test_flow_publish_raise_after_push.py:128`, `target/template/src/pdca_harness/publish.py:419`). |

No implementation defect found within the chosen scope. Source citations were checked against the supplied target, whose synthetic base identifies the brief's `b5f5c29` revision. The production change was stashed for the red leg and restored for the green leg; the original patch and new test remain intact.

Independent commands: in `target/template`, `PYTHONPATH=src python3 -m unittest discover -s tests -p test_flow_publish_raise_after_push.py -v` (red and green), the same discovery command selecting `test_publish_slice.py`, and full `PYTHONPATH=src python3 -m unittest discover -s tests`. Temporary test files were confined through `TMPDIR` to this review workspace. In `target`, reran `docs/publishing/tools/lint_docs.py`, `docs/publishing/tools/render_site.py --check` with output inside this workspace, the production-import scanner, and `git diff --check`.

The local root-suite command exited 77 because Copier is not importable by `/usr/bin/python3`; it executed 19 cases with three skips and explicitly reported no Copier-dependent coverage. This is a reviewer-host limitation, not a patch defect or a claim of independent root-suite verification. The frozen T3 log separately shows the render/update tests executing successfully (`gate-logs/T3-suite.log:38`). All supplied gate logs were inspected; the instance-scoped wrappers were not assumed to exist in the target. The brief explicitly defines an offline subprocess-exception regression, and its fixture can exhibit the forbidden failure, as the red rerun demonstrated.

The only supplied INTEGRATION §4 is the template, whose project-defined human-only list remains a placeholder (`target/template/docs/INTEGRATION.md.jinja:80`); no additional concrete project-specific human-only item is available in the inputs. The brief documents prior-art searches by affected production path, including merged commits and closed PRs, but supplies no independently checkable history beyond the snapshot; T5 records the outstanding confirmation.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 632 (publish-raise-after-push-counts-as-pushed)

Verdict: no correctness bugs found on either lens. Nothing here needs a human decision. The notes below are small, optional cleanups.

## Correctness

- `template/src/pdca_harness/publish.py:410-414` — The `try/except Exception` wraps only the `gh pr create` call, which is the one step between the push (`publish.py:318`, run in the loop at `:391-397`) and the record write (`publish.py:440`). A failure before the push still returns 1 from `:397` (or raises out to `_isolate`) without writing a record, so case (4) is unchanged. Catching `Exception`, not `BaseException`, lets ^C / `SystemExit` through, which matches `flow._isolate` (`flow.py:62-71`). The fake `CompletedProcess(pr_cmd, 1, "", "<Type>: <msg>")` sends the raise down the existing rc-1 path: `pr_failed=True`, the exception text goes to stderr, the record is written with `pr_url=""`, and the call returns 1 (`publish.py:445-446`). `flow._publish_bundle` then returns True from the record's new mtime (`flow.py:665`). No bug found.
- `template/src/pdca_harness/publish.py:419-422` — The new hint "re-run `pdca publish <id>`" is safe to follow. A re-run does `checkout -B` (`:300`) and `push --force-with-lease` (`:318`), so the branch that is already local and on origin does not make it fail.
- C4 log (`gate-logs/C4-verify.log`): the new test fails without the fix for the right reason. `_isolate` logs "publish failed (RuntimeError: gh exploded)" and `_publish_bundle` returns False after the push stub ran. It passes with the fix. T3 suite is green.

## Test quality / simplification (optional, not blocking)

- `template/tests/test_flow_publish_raise_after_push.py:139` — `assertIn("origin", err)` proves almost nothing, because "origin" can show up in any stderr line. Asserting the new phrase (for example `f"{branch} is pushed to origin"`) would pin criterion (3) to the new message from `publish.py:419`. Small strengthening only. The branch-name and "no draft PR was opened" asserts on the lines around it already cover most of it.
- `template/tests/test_flow_publish_raise_after_push.py:45-79` — `_cfg` / `_bundle` are copied from `tests/test_publish_slice.py:48-81`, with the publisher changed and the texts pre-written. The brief allowed copying them, and the suite has no shared helper module, so this is fine. If the copies drift apart they could be merged later.
- `template/src/pdca_harness/flow.py:662` (not changed by this diff) — When this path runs, the operator now sees publish's "branch … is pushed to origin" line, then flow's "publish did not complete (rc 1) — NOT published". The two lines read a bit inconsistently. This flow message came before this patch, and criterion (3) asks for the "did not complete" wording to stay, so it is not a defect in this diff. It is only a wording note for a later change.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the brief's affected-path merged-history and closed/rejected-work conclusions — the supplied snapshot has only one synthetic base commit and no remote, so those conclusions cannot be independently established here (`brief.md:31`, `review-grounding.log:1`).
- [x] Validation — fitness-to-purpose — Accept whether continuing the fold while requiring the operator to finish PR creation meets the intended workflow — offline evidence establishes accounting and diagnostics, but does not demonstrate a live hosted PR recovery (`target/template/tests/test_flow_publish_raise_after_push.py:128`, `target/template/src/pdca_harness/publish.py:419`).
- [x] **The repro and criterion (1) cannot go green with the fixture the brief names.** The test fixture's config sets `publisher=LeafConfig(mode="stub", …)` (`template/tests/test_publish_slice.py:63`), and `_publish_bundle` passes `dry_run=cfg.publisher.mode == "stub"` (`flow.py:659`). The dry-run branch returns 0 before any git or `gh` step (`publish.py:334-353`) and writes no `publish.json`. Following the Repro instruction literally (`_bundle(self.cfg, …)`, then `flow._publish_bundle(self.cfg, d, …)`) gives `False`, with no record and `unpublished == [d]`, **both before and after a correct fix**. The "RED" in the brief is therefore real for the wrong reason, and the test can never turn green. That invites a "fix" that games the test, or a C4 red→green leg that fails. The existing test only escapes this because it calls `publish.publish(...)` directly, so `dry_run` defaults to False (`test_publish_slice.py:375`). The brief must tell Do to (i) set `cfg.publisher.mode` to a non-stub value for the `_publish_bundle` call, and (ii) keep `_ensure_texts` from spawning a real publisher leaf under that mode (`publish.py:59-62` calls `leaves.run_publish` when texts are missing). For example: draft the texts first under stub, or pass `texts_prevalidated=True` with `commit-msg.txt` / `pr-description.md` already present.
- [x] **`_publish_stacked` is in scope but no criterion verifies it, and it has no step after the push that is likely to raise.** The Scope says the fix "Applies to both publish paths that push (… and `_publish_stacked`, `publish.py:452-560`)". In that path the push is the last step (`publish.py:484`). After it there is only `_restore_worktree`, which uses `subprocess.run(..., capture_output=True)` and is best-effort (`publish.py:1095-1101`), and then the record write (`publish.py:539-547`). There is no `gh pr create` or similar call that could raise in between. Criteria (1)–(4) test only the new-PR path. Do will either change `_publish_stacked` with nothing to verify it (unverified review surface) or leave it alone (scope not met). Either drop `_publish_stacked` from Scope, or name the raise it must survive and add a criterion and test for it.
- [x] **The brief does not pick a fix shape, and the two candidates touch different files.** Criterion (1) requires `_publish_bundle` to return True when `publish.publish` raised after the push. On main, that is blocked twice: no record is written (`publish.py:431`), and `rc is not None` (`flow.py:665`) zeroes out any raise. Two implementations satisfy the criteria:
- [x] **Criterion (2) is close to a tautology as written.** `integrate.unpublished([d], pushed={d.name})` passes `pushed` by hand, so it only proves that `publish.json` names a branch (`integrate.py:181-182`). The flow's real fold set comes from `_publish_bundle`'s return value. To close the loop, criterion (2) should derive `pushed` from criterion (1)'s return (`pushed = {d.name} if rc else set()`), or the test should drive the wave fold path at `flow.py:2286`. Otherwise (1) and (2) can pass separately through code that never connects them.

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
- By / date: Eduard Ralph / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
