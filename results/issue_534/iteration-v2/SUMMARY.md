# Result — issue 534 / handoff-contract-checked-at-reap-not-turn-end

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `template/.claude/settings.json:60-71` registers `handoff_guard.py` as a Claude
  Code **Stop** hook. Stop fires every time the main agent finishes a turn, not when the
  session ends. `_stop_verdict()` (`template/.claude/hooks/handoff_guard.py:48-73`) exits 2
  while the leaf's contract is undischarged, and on exit 2 Claude Code sends the hook's stderr
  back to the model instead of handing the turn to the human (the hook's own docstring says
  so at `handoff_guard.py:14-15`). An interactive leaf that asks the human a question therefore
  never reaches the human. The model gets the guard's text, answers it, ends another turn, and
  is blocked again. Nothing bounds the repeat: the envelope is parsed and thrown away
  (`handoff_guard.py:53`). Observed: a sign-off session blocked twelve turns in a row. The
  pressure on the model is to write the artifact the guard demands, and for sign-off that
  artifact is `signoff-decision`, the human's own decision. The hook is live for every
  interactive leaf with a contract (planner, signoff, publisher, act: `handoff.py:70-78`).
- Success criterion: all of the following, shown by the named test at C4:
  (a) **No turn end is intercepted.** The rendered template registers no hook on the Stop
      event, and `handoff_guard.py` run the way the old registration ran it (no arguments, a
      Stop-event JSON envelope on stdin, `PDCA_HANDOFF_ROLE` and `PDCA_HANDOFF_STATE` set, and
      the registered bundle's contract **undischarged**) exits 0 and writes nothing to stderr.
      So an instance whose `settings.json` still carries the old registration (e.g. a
      `copier update` merge that kept it) cannot deadlock either.
  (b) **The contract is reported at reap.** When the `handoff.session(...)` context the driver
      wraps around an interactive leaf exits with the contract undischarged, the problems
      `stop_problems()` finds are printed to **stderr**, naming the role and each bundle
      (e.g. a sign-off bundle with no `signoff-decision`; a signoff `iterate-do` with no
      rationale; a planner brief with an empty Success criterion). A discharged contract
      prints nothing. A recorded `--abandon` reason is still reported as it is today
      (`handoff.py:307-310`), in place of the problem list.
  (c) **Report only.** The reap check writes nothing into any bundle, deletes or moves no
      artifact, raises nothing, and a failure inside the check (e.g. an unreadable config)
      degrades to a one-line stderr note, never an exception out of the context manager
      (the existing rule at `handoff.py:273`: the contract must never break the leaf it checks).
  (d) `/handoff <id>` (`handoff_guard.py --check`) and `--abandon` keep working unchanged as
      the model's self-check and the typed-abandon channel.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: remove turn-end enforcement of the interactive leaves' exit contract and move
  the check to the session boundary, as stated in the criterion. Files in reach:
  `template/.claude/settings.json` (the Stop registration),
  `template/.claude/hooks/handoff_guard.py` (Stop mode; docstring),
  `template/src/pdca_harness/handoff.py` (`session()` reap; module/function docstrings that
  describe a Stop hook), and the text that promises Stop-hook enforcement to the model or the
  operator: `leaves.py` prompt strings in `_plan_prompt` (`:1035`), `_plan_batch_prompt`
  (`:1293`, `:1310`) and `_signoff_prompt` (`:3438`), the comments in `run_signoff` (`:3414`)
  and `run_publish` (`:3628`), `template/.claude/commands/handoff.md.jinja:17-19`, and
  `docs/01-render-and-integrate.md:178-181`. Prompts should now say `/handoff` is the
  self-check and the driver reports an unmet contract when the session ends. Updating
  `template/tests/test_handoff.py` to match is **in scope and expected**:
  `test_stop_hook_ships_and_is_registered` (`:133-141`) asserts the registration this fix
  removes and must be inverted, and the module docstring's item (b) (`:10-11`) rewritten. The
  `StopVerdict` tests (`:331-362`) test `stop_problems()`, which stays, and must keep passing.
  / out of scope: `do_plan`, `do_plan_batch`, `run_plan_advisory_batch` in `leaves.py` (see
  Ordering note); reopening a session or changing any flow/state transition on an unmet
  contract; renaming `stop_problems`; the per-role contract checks themselves
  (`check_planner` / `check_signoff` / `check_publisher` / `check_act`); #508 (`/handoff`
  cannot run in a rendered instance) and #528 (Act vs `/handoff`); #492 `/interview`; this
  instance's own copy of the hook (it changes at the next `copier update`).

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

Fix issue #534: let interactive leaves return each turn to the human, and report unmet handoff contracts only when their process exits, including whitespace-only abandonment handling.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Human turn handoff, session-end reporting, failure tolerance and unchanged self-check channels have explicit, falsifiable outcomes; `brief.md:28`, `target/template/tests/test_handoff_reap.py:143`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes produced 21 failures across 53 tests, including the live old hook returning 2 and missing reap notices; `review-work/red.log:22`, `target/template/tests/test_handoff_reap.py:196`. |
| C3 Change | PASS | The changes satisfy the stated boundary and both iteration corrections; blank abandonment can no longer suppress a missing-decision notice, and the excluded planner functions are unchanged; `target/template/src/pdca_harness/handoff.py:269`, `target/template/src/pdca_harness/handoff.py:103`. |
| C4 Verification (red→green) | PASS | After stash restoration, all 53 targeted tests passed, covering subprocess hook invocation, all contract roles, malformed artifacts, no bundle mutation and check failure recovery; `review-work/green.log:7`, `target/template/tests/test_handoff_reap.py:328`. |
| C5 Causal adequacy | PASS | Removing turn-end enforcement eliminates the feedback loop itself; no optional-capability probe conceals a load-time cause, and tests call production logic with a demonstrably live contract; `target/template/.claude/hooks/handoff_guard.py:76`, `target/template/tests/test_handoff_reap.py:162`. |
| T1 Structure | PASS | Existing driver session boundaries and contract checks remain the single source of judgment, with the registered bundle set preserved for reporting; `target/template/src/pdca_harness/handoff.py:306`, `target/template/src/pdca_harness/leaves.py:3419`. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering and internal-link audit passed, as did diff whitespace checking; frozen host-workflow parity evidence agrees; `review-work/lint.log:3`, `review-work/render.log:4`, `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independent driver suite: 1,806 tests, two skips; fresh rendering passed with Copier, while release-update coverage rests on the frozen five passing update tests because this target has no release tags; `review-work/driver-rerun.log:1119`, `gate-logs/T3-suite.log:43`. |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the deferred gate explicitly assigns substantive auditing to publish, which must rerun it; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | PASS | Scope remains consistent with the maintainer’s chosen reporting boundary; complete affected-path main history and 233 closed PR file lists show no competing correction or rejected same-path work; `brief.md:15`, `review-work/prior-art.txt:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm that terminal notices provide sufficient operator feedback for malformed-but-present artifacts while the driver continues — automated checks establish the protocol, but operational sufficiency remains the sign-off decision; `target/template/src/pdca_harness/handoff.py:345`, `target/template/src/pdca_harness/handoff.py:362`. |

## Evidence and limits

No patch defect found. This review is advisory; acceptance remains with the human and deterministic gates.

- **Independent red→green:** retained the patched tests and stashed all six changed production/documentation files, ran `PYTHONPATH=src python3 -m unittest tests.test_handoff tests.test_handoff_reap` from `target/template`, restored the stash, and reran. Red exited 1; green exited 0. File hashes matched before and after restoration. The red subprocess hook returned 2 with the missing-decision message, excluding the false-green bootstrap failure described in the brief. Evidence: `review-work/red.log:42`, `review-work/green.log:7`; frozen counterpart: `gate-logs/C4-verify.log:10`.
- **Production and scope:** the tests import `pdca_harness` directly (`target/template/tests/test_handoff_reap.py:46`), consistent with `gate-logs/C5-prod-path.log:10`. Source comparison confirmed `do_plan`, `do_plan_batch` and `run_plan_advisory_batch` unchanged, including their comments. The patch reverse-application check passed against the restored target; no target staleness was observed.
- **Runtime:** `PYTHONPATH=src python3 -m unittest discover -s tests` passed independently. The default Python could not import Copier (`review-work/root.log:8`); running `python3 -m tests.run_root_suite` through the installed Copier environment passed 19 tests with one skipped update class (`review-work/root-copier.log:5`). The disposable target has no release tags (`target/tests/test_update_compat.py:243`). Consequently, this review does not claim an independent update-compatibility rerun: the frozen log explicitly shows all five update cases passing and 24 root tests passing (`gate-logs/T3-suite.log:43`, `gate-logs/T3-suite.log:54`). This is a local target-history limitation, not an unmet dependency in the gate evidence.
- **Docs:** independently ran `docs/publishing/tools/lint_docs.py` and `docs/publishing/tools/render_site.py --check --out <review workspace>/site`. Both passed. The frozen T2 and host-parity logs show the same checks succeeding (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`); they establish workflow-command parity, not a separate live hosted-CI run.
- **Prior art:** GitHub API queries covered all eight affected paths on main and changed-file lists for all 233 closed PRs, with pagination. The original contract implementation is [PR #398](https://github.com/eduralph/pdca-harness/pull/398), commit `900d638`; it remains the only main-history change to the hook and handoff module. The only unmerged closed PR, #4, affects none of these paths. Records: `review-work/prior-art.txt:1` and `review-work/prior-art.json:1`.
- **Human-only policy:** the supplied target contains an unrendered integration template whose additional human-only list is still TODO (`target/template/docs/INTEGRATION.md.jinja:80`); no concrete additional project item is enumerated there. No live Claude UI outcome is claimed; the brief explicitly defines the hook protocol test as sufficient technical verification without that binary (`brief.md:105`).

### Advisory — adversary

# Adversarial review — issue 534, iteration 2

**Verdict:** I could not refute the core fix. The red→green proof reproduces, the new tests catch every deliberate break I tried, and the no-argument hook path does nothing. One concrete failing case remains in the reap report for batch sessions, plus one upgrade-path gap in the evidence.

## Evidence re-run

- Re-ran C4 on copies inside my sandbox (Python 3.14.4). Post-fix, `tests.test_handoff` + `tests.test_handoff_reap`: 53 OK. With the five production files reverted to `HEAD`: 21 failures, the same set as `gate-logs/C4-verify.log:27-239`. The (a) red is real, not the "contract check unavailable" false green the brief warns about. Each (a) test first proves the check is live with `--check` (`template/tests/test_handoff_reap.py:175`, `:214`), and pre-fix the hook returns 2 with the actual problem list (`C4-verify.log:52`, `:72`).
- Mutation checks, each applied alone to a copy, all caught: report on stdout instead of stderr (15 fail); drop the `registered` override at `template/src/pdca_harness/handoff.py:331` (1 fail); restore the old unstripped abandon test in `stop_problems` at `handoff.py:431` (3 fail); narrow the `except` at `handoff.py:353` (1 error); make the no-argument hook print (3 fail); print the problems alongside an abandon reason (1 fail); skip the scratch-file unlink at `handoff.py:333` (6 fail). So the tests run the production code (`pdca_harness.handoff` and the real hook file), and none of them is a tautology.
- Both iteration-1 carry-forward items are done. One abandon test, `_abandon_reason` (`handoff.py:269-278`), is used at `handoff.py:351` and `:431`, with whitespace-only cases (`test_handoff_reap.py:300`). The `check_planner` docstring is reworded (`handoff.py:103-106`).

## Findings

- NEEDS-HUMAN [impl] — **One bundle whose check raises hides the whole batch report.** `stop_problems` checks every registered bundle in one loop (`template/src/pdca_harness/handoff.py:445-447`), and `report_at_reap` wraps the whole call in one `try` (`handoff.py:350-357`). So any exception from one bundle replaces every other bundle's result with the single "could not check … — nothing reported" line. Concrete case, run against the patched code: a batch sign-off over `issue_7` + `issue_8`, where `issue_7/signoff-decision` contains a non-UTF-8 byte (`iterate-do\ncaf\xe9 …` saved as cp1252, read with `encoding="utf-8"` at `template/src/pdca_harness/leaves.py:3512`) and `issue_8/signoff-decision` is `iterate-do` with no rationale. The reap prints only `handoff: could not check the signoff session's exit contract (UnicodeDecodeError: …) — nothing reported`. `issue_8`'s missing rationale is never shown, even though that is one of the two cases the brief keeps the report for (brief (b); `handoff.py:345-348`). The note also doesn't say which bundle broke. You get the same result when `issue_7/signoff-decision` is a directory (IsADirectoryError). Run on its own, `issue_8` is reported correctly. Fix: catch errors per bundle in the loop (report `issue_7: could not check (…)` and carry on), and add a two-bundle test where one bundle raises. Keep config-wide failures as the single line that `test_handoff_reap.py:358` expects. This is unlikely to happen (the model writes these files), but it is the same kind of edge case the iteration-1 sign-off sent back.
- NEEDS-HUMAN — **The T3 "copier update still applies" evidence doesn't cover an instance that edited `.claude/settings.json`.** `tests/test_update_compat.py` only edits `pdca.toml` (`:141`), so the green T3 row says nothing about merging `settings.json`. I ran a three-way `git merge-file` from the old template to the patched one (`template/.claude/settings.json:54-60`) onto edited instances. An instance that added an entry to `permissions.ask` merges cleanly. One that added its own hook next to the shipped `Stop` entry, or a new top-level key after `"hooks"`, gets conflict markers, so `settings.json` stays invalid JSON until someone resolves it. Keeping `"hooks": {}` or `"Stop": []` in the template conflicts the same way, so this is not a defect in how the patch removes the block. Either resolution is safe, because the no-argument hook now does nothing (`template/.claude/hooks/handoff_guard.py:72-78`). Decide whether the PR body or release note should warn instance owners about this conflict and say that keeping or dropping the old `Stop` block are both fine.
- Not filed (known, and the brief defers it): for Act, and for a CSV-batch planner that registers no bundles, `stop_problems` only asks whether a `/handoff` passed (`handoff.py:435-440`, `:449-452`). The Act role prompt still tells the model its job is done once the entry is written, and never mentions `/handoff` (`template/agents/act.md.jinja:58-61`). #508 says `/handoff` cannot run in a rendered instance. So expect "the act session has not verified its exit contract" to print after most Act sessions, even when the entry was written. That is a false report, not a block, so it is still better than before the fix. It belongs with #508/#528 in run 4.

## Attempted and could not refute

- **(a) No turn-end hook.** `template/.claude/settings.json:1-60` has no `hooks` key. The agent frontmatter registers only `PreToolUse` (`template/.claude/agents/builder.md.jinja:11-14`, `publisher.md.jinja:12-20`). No code path builds a `Stop`/`SubagentStop` registration at spawn. The no-argument path returns 0 before it imports anything or reads stdin (`handoff_guard.py:72-78`), so a kept old registration, a broken `src/`, or a missing config can't make it print or block.
- **(b)/(c) Scratch-file tampering.** If the leaf rewrites, empties, or deletes the scratch file, `registered` still wins (`handoff.py:306-311`, `:331`), and bad or missing JSON reads as `{}` (`handoff.py:226-233`). Odd `abandoned` values (`true`, `0`, lists) are now judged the same way in both places. The leaf's own exception passes through unchanged (`test_handoff_reap.py:362`).
- **Unknown-mode exit 2** (`handoff_guard.py:72-75`). This would block a turn only if something registered the script as a Stop hook *with* an argument. Nothing ever did, so I found no concrete failing case.
- **Leftover wording.** No text still promises Stop-hook enforcement, except the `do_plan`/`do_plan_batch` comments (`leaves.py:917`, `:1104-1108`), which the brief deliberately leaves out of scope for #480.
- **check-gates.json.** C4 and C5 hold up when re-run. I had no reviewer verdict to check beyond the gate rows.

### Advisory — code-review

# Check — advisory code review (issue #534)

Reviewed `patch.diff` against target source at `$PDCA_TARGET`, focused on correctness
bugs the patch introduces and reuse/simplification opportunities.

## Correctness

- No bugs found. Both carry-forward findings from iteration 1 are actually fixed:
  - `handoff.py:269-278` (`_abandon_reason`) is now the single "was this abandoned"
    test, used by both `stop_problems` (`handoff.py:431`) and `report_at_reap`
    (`handoff.py:351`), so a whitespace-only `abandoned` value can no longer clear the
    problem list while also printing no reason. `test_a_blank_abandon_value_does_not_hide_the_report`
    (`template/tests/test_handoff_reap.py:301-323`) exercises exactly that case for
    `""`, `" "`, `"\n"`, `" \t\n"`.
  - `check_planner`'s docstring (`handoff.py:103-106`) no longer mentions the Stop
    boundary; it now describes the session-end check.
- `session()`'s merge at reap (`handoff.py:331`,
  `report_at_reap(cfg, role, {**_read_json(path), **registered})`) correctly protects
  `role`/`bundles`/`require_artifact`/`baseline` from being clobbered by a rewritten or
  lost scratch file, while still picking up `passed`/`abandoned` from the file — checked
  this against `test_the_report_names_the_bundles_the_driver_registered`
  (`test_handoff_reap.py:271-280`) and it holds.
- `report_at_reap` (`handoff.py:336-364`) only wraps the `_abandon_reason` /
  `stop_problems` call in `try/except`; the two `print(...)` calls after it are
  unguarded. That's fine in practice (they're plain string formatting to `sys.stderr`),
  but it means the docstring's "never raises" claim is not literally enforced end to
  end — a future edit that adds anything fallible to those print branches would not be
  caught by the existing exception net. Not a bug today, just a latent gap; not
  something this patch needs to fix.
- Verified the two intentionally-untouched "Stop hook" comments
  (`leaves.py:917`, `leaves.py:1107`) are both inside `do_plan` / `do_plan_batch`,
  exactly the functions the brief's Ordering note carves out for issue #480. No stray
  edits leaked into those functions or into `run_plan_advisory_batch`.
- `settings.json` diff is a clean removal of the `hooks.Stop` block; valid JSON, no
  other permission entries touched.
- `handoff_guard.py`'s new "unknown mode" branch (`handoff_guard.py:72-75`, returns 2
  for any argv it doesn't recognize) is a behavior change from the old fallthrough to
  `_stop_verdict()`, but it's consistent with the brief's scope (only `--check`,
  `--abandon`, and no-args are meaningful now) and is exercised by the no-args tests in
  `test_handoff_reap.py`.

## Reuse / simplification

- `_abandon_reason` (`handoff.py:269-278`) is exactly the kind of single-source helper
  that should have existed before iteration 1's fix; good factoring, no duplicate logic
  left behind.
- `report_at_reap` reasonably reuses `stop_problems` rather than re-implementing the
  per-role dispatch; no duplicated contract logic introduced.

## Gate evidence cross-check

- C4 log (`gate-logs/C4-verify.log`) shows the red leg failing for the right reasons
  pre-fix (Stop hook still registered, `_stop_verdict` returns 2 on an undischarged
  contract) and green post-fix, matching the brief's stated falsifiability trap.
- No other gate log surfaced anything relevant to this lens.

Nothing else stood out. The diff is clean on both lenses.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Confirm that terminal notices provide sufficient operator feedback for malformed-but-present artifacts while the driver continues — automated checks establish the protocol, but operational sufficiency remains the sign-off decision; `target/template/src/pdca_harness/handoff.py:345`, `target/template/src/pdca_harness/handoff.py:362`.
- [ ] **One bundle whose check raises hides the whole batch report.** `stop_problems` checks every registered bundle in one loop (`template/src/pdca_harness/handoff.py:445-447`), and `report_at_reap` wraps the whole call in one `try` (`handoff.py:350-357`). So any exception from one bundle replaces every other bundle's result with the single "could not check … — nothing reported" line. Concrete case, run against the patched code: a batch sign-off over `issue_7` + `issue_8`, where `issue_7/signoff-decision` contains a non-UTF-8 byte (`iterate-do\ncaf\xe9 …` saved as cp1252, read with `encoding="utf-8"` at `template/src/pdca_harness/leaves.py:3512`) and `issue_8/signoff-decision` is `iterate-do` with no rationale. The reap prints only `handoff: could not check the signoff session's exit contract (UnicodeDecodeError: …) — nothing reported`. `issue_8`'s missing rationale is never shown, even though that is one of the two cases the brief keeps the report for (brief (b); `handoff.py:345-348`). The note also doesn't say which bundle broke. You get the same result when `issue_7/signoff-decision` is a directory (IsADirectoryError). Run on its own, `issue_8` is reported correctly. Fix: catch errors per bundle in the loop (report `issue_7: could not check (…)` and carry on), and add a two-bundle test where one bundle raises. Keep config-wide failures as the single line that `test_handoff_reap.py:358` expects. This is unlikely to happen (the model writes these files), but it is the same kind of edge case the iteration-1 sign-off sent back.
- [x] **The T3 "copier update still applies" evidence doesn't cover an instance that edited `.claude/settings.json`.** `tests/test_update_compat.py` only edits `pdca.toml` (`:141`), so the green T3 row says nothing about merging `settings.json`. I ran a three-way `git merge-file` from the old template to the patched one (`template/.claude/settings.json:54-60`) onto edited instances. An instance that added an entry to `permissions.ask` merges cleanly. One that added its own hook next to the shipped `Stop` entry, or a new top-level key after `"hooks"`, gets conflict markers, so `settings.json` stays invalid JSON until someone resolves it. Keeping `"hooks": {}` or `"Stop": []` in the template conflicts the same way, so this is not a defect in how the patch removes the block. Either resolution is safe, because the no-argument hook now does nothing (`template/.claude/hooks/handoff_guard.py:72-78`). Decide whether the PR body or release note should warn instance owners about this conflict and say that keeping or dropping the old `Stop` block are both fine.
- [ ] external dependency: write permission for `template/.claude/**` in the Do worktree — the Edit tool was refused again this iteration (tried on `template/.claude/settings.json`; the session is non-interactive, so the prompt could not be approved), so the three `.claude/` hunks were never applied at their real paths in Do. The 4 tests that read those files (5 failures: `test_handoff_reap.NoTurnEndIsIntercepted` x3, one with two subtests, plus `test_handoff::test_hook_ships_and_is_not_registered_on_stop`) and the root render slice were green in Do only against copies. C4 and T3 at Check, where the driver applies `patch.diff` itself, are the real-path run. In iteration 1 both passed with byte-identical `.claude/` hunks.

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
- Iteration delta (if iterating): The approach is right and should be kept as is (no Stop registration, the no-argument hook path inert, report-only check at reap, one shared `_abandon_reason` test). Iterate only on §6.2, the adversarial finding: one bundle whose check raises hides the whole batch report. `stop_problems` checks every registered bundle in one loop (`handoff.py:445-447`) and `report_at_reap` wraps the whole call in one `try` (`handoff.py:350-357`), so e.g. a non-UTF-8 or directory `signoff-decision` in `issue_7` replaces `issue_8`'s real problem (iterate-do with no rationale) with a single "could not check … — nothing reported" line that does not even name the broken bundle. Fix: catch errors per bundle inside the loop, report `issue_7: could not check (<error>)` and carry on with the rest. Keep config-wide failures as the one line `test_handoff_reap.py:358` expects. Add a two-bundle test where one bundle raises and the other's problem is still reported. No change needed for the settings.json copier-update conflict (§6.3): leave it as is, no PR/release-note warning required. Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py (issue 480).
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
