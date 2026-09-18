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

Review issue #534: remove interactive-leaf turn-end blocking and report unmet exit contracts to the human when the driver reaps the session.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable turn handover, reap reporting, failure containment, and preserved self-check behavior; tests exercise those boundaries, including a live undischarged contract (`brief.md:27`, `target/template/tests/test_handoff_reap.py:163`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes produced 17 failures across 52 tests, including actual hook exit 2 and absent malformed-artifact reports; the fixture does not evade the defect through failed config loading (`review-red.log:42`, `target/template/tests/test_handoff_reap.py:213`). |
| C3 Change | PASS | Turn completion can return control to the human while the existing session boundary supplies role/bundle diagnostics without changing bundle outcomes; protected planner functions remain unchanged (`target/template/.claude/hooks/handoff_guard.py:76`, `target/template/src/pdca_harness/handoff.py:319`, `target/template/src/pdca_harness/leaves.py:3419`). |
| C4 Verification (red→green) | PASS | Restoring the same production changes passes all 52 tests, including real-process hook invocation, unchanged bundle contents, and a real malformed-config failure reduced to one stderr line (`review-green.log:7`, `target/template/tests/test_handoff_reap.py:196`, `target/template/tests/test_handoff_reap.py:320`). |
| C5 Causal adequacy | PASS | Removing the blocking Stop path eliminates the repeated model-feedback cause; no capability probe substitutes for correcting it, and regression tests invoke production code (`target/template/.claude/hooks/handoff_guard.py:76`, `target/template/tests/test_handoff_reap.py:46`, `target/template/tests/test_handoff_reap.py:190`). |
| T1 Structure | PASS | Reusing the existing session context and contract checks keeps role semantics centralized and avoids new flow transitions or vendor-specific driver paths (`target/template/src/pdca_harness/handoff.py:319`, `target/template/src/pdca_harness/handoff.py:340`, `target/template/src/pdca_harness/handoff.py:406`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/internal-link audit, and diff whitespace check pass; host-parity evidence agrees (`target/.github/workflows/docs-check.yml:35`, `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver suite passes 1,805 tests with two skips; frozen evidence separately shows all 24 root tests passing, including actual render/update cases (`review-suite.log:1119`, `gate-logs/T3-suite.log:37`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is deferred to its required publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Establish that affected paths have no superseding merged or closed/rejected solution — the brief records path-based history but issue-reference-based closed-work searches, and the supplied one-commit target cannot independently settle that question (`brief.md:115`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm that terminal warnings at process exit sufficiently support human sign-off, particularly when a malformed-but-present artifact can still reach downstream processing — automated protocol tests establish behavior, but this operational adequacy remains a human decision (`target/docs/01-render-and-integrate.md:178`, `target/template/src/pdca_harness/handoff.py:333`). |

## Independent verification and evidence limits

- Grounding used only the supplied target and review inputs. The target contains one synthetic base commit, no tags, and no remotes; the applied patch is readable and coherent. No stale-target defect was inferred.
- Red/green procedure: `git stash push` restricted to the six production/documentation paths, retaining both regression test files; run `PYTHONPATH=src python3 -m unittest tests.test_handoff tests.test_handoff_reap` from `target/template`; restore with `git stash pop`; rerun. Results: exit 1 / 17 failures, then exit 0 / 52 passing tests. The patch was restored. Full outputs: `review-red.log` and `review-green.log`.
- Independently ran `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`: exit 0, 1,805 tests, two skips (`review-suite.log`). Temporary test data was directed into this review sandbox.
- Independently ran the host workflow's docs lint and site render with `--check`, writing the site into this sandbox; both passed. Rechecked production imports with Python AST and inspected actual production invocations. Compared the three excluded planner functions against the base: all unchanged.
- The instance-scoped oracle wrappers are not supplied here. Their frozen logs were consulted. Copier is not importable in this reviewer environment, and the synthetic target has no release tags, so the root render/update suite was adjudicated from `gate-logs/T3-suite.log`: named render and update cases actually ran and passed. This is a local rerun limitation, not an unmet dependency in the round's evidence. The Python/git hook regression was independently executable, including the real subprocess invocation.
- The available integration template lists project-specific human-only items as TODO (`target/template/docs/INTEGRATION.md.jinja:80`); it supplies no additional concrete item. Prior-art confirmation remains limited as recorded in T5: no path-based closed/rejected-work evidence is supplied for the affected files.

No grounded patch defect found. This review is advisory; fitness-to-purpose and the prior-art evidence gap remain for human adjudication.

### Advisory — adversary

# Adversarial review: issue 534 (exit contract checked at reap, not at turn end)

**Verdict: I could not refute the fix.** The red→green is real, and the patch removes the
cause (the Stop registration) rather than hiding it. I found one small logic slip in the new
reap code, one stale docstring the brief put in scope, and some notes.

## Findings

- NEEDS-HUMAN [impl] — **A blank abandon value hides the reap report completely.**
  `template/src/pdca_harness/handoff.py:339-340` strips `abandoned`, finds it empty, and calls
  `stop_problems`. But `stop_problems` tests the *unstripped* value at `handoff.py:419-420`,
  treats `" "` as truthy, and returns `[]`. So neither the reason nor the problem list is
  printed. Probe (sign-off bundle with no `signoff-decision`): no abandon → the missing-decision
  line prints; `{"abandoned": "x"}` → "deliberately abandoned — x"; `{"abandoned": " "}` →
  stderr is `''`. The `--abandon` CLI can't produce a blank value (`handoff.py:266`
  normalizes it), but the leaf can: its scratch-file path is in its env and it has Write. Fix:
  use the same "is it abandoned" test in both places (strip in `stop_problems`, or drop a
  blank `abandoned` before calling it), and add the case to `ReportedAtReap`. Low severity.

- NEEDS-HUMAN [impl] — **`check_planner`'s docstring still describes the retired hook.**
  `handoff.py:103-106` says "at the Stop boundary a wholly-absent brief passes there". The
  brief's Scope lists "module/function docstrings that describe a Stop hook" in `handoff.py`.
  A one-line fix ("at the session-end check").

- **The report's wording is false when the leaf never ran.** If the spawn raises (for example
  `FileNotFoundError` from `subprocess.run` at `template/src/pdca_harness/leaves.py:635` when
  the CLI is missing), the `finally` at `handoff.py:319` still prints "the signoff session
  ended with its exit contract not discharged (a report only; the driver carries on as
  usual)", and then the exception propagates. Probe confirmed. Neither half of that sentence
  is true on this path. Cosmetic, since the real error follows. Not marked [impl]: not worth
  a round on its own, but could be folded into the round above.

- **Test (a) only guards `settings.json`** (`template/tests/test_handoff_reap.py:143-150`).
  Agent frontmatter is a second place a turn-end hook can be registered.
  `template/.claude/agents/publisher.md.jinja:12-20` already uses `hooks:` for PreToolUse,
  and the contract leaves are launched with `--agent`. I checked: none of the `signoff`,
  `planner`, `publisher` or `act` wrappers registers Stop/SubagentStop today, so this is a
  coverage gap, not a bug. Scanning those four frontmatters too would enforce the brief's
  invariant ("no harness mechanism") rather than a single file.

- **For the case the brief kept the report for (iterate with no rationale), the report is
  the only notice, and it isn't saved anywhere.** In the single-issue flow,
  `template/src/pdca_harness/flow.py:182-185` records the empty Iteration delta and
  `flow.py:209` applies the transition at once, so the next beat's output follows the report
  immediately. The maintainer chose this trade-off (report only, no flow change), so I'm not
  reopening it. I'm only noting that "so a session can't close silently with a bad artifact"
  (`docs/01-render-and-integrate.md:178-180`) relies on the human watching the terminal at
  that moment.

- **Interaction with #508 (out of scope here).** The Act and CSV-batch planner verdicts rest
  only on `passed` (`handoff.py:423-428`, `:437-440`), and only a passing `/handoff` writes it
  (`handoff.py:400-402`). If `/handoff` really can't run in a rendered instance (#508 as the
  brief describes it), every Act session will end with this report even when the entry was
  written. That is not a regression, since before the fix the same condition caused the
  endless turn-end block. But the Act report will be noise until #508 lands.

## What I tried and could not break

- **Red→green.** Re-ran on the patched tree: 52/52 pass (`tests.test_handoff` +
  `tests.test_handoff_reap`). Copied the template into my sandbox, restored the four
  production files from `HEAD`, and re-ran: 12 of the 17 new tests fail (16 failures counting subtests). The 5 that pass on both sides are the "unchanged behaviour" guards: a discharged contract prints nothing, an abandon is reported instead of the list, the leaf's own exception passes through, and `--check`/`--abandon` still work. The (a) failures
  carry the old guard's real "This signoff leaf session may not end yet" text, from both the
  in-process leg and the subprocess leg. So the red comes from a live contract check, not the
  "contract check unavailable — allowing the stop" false green the brief warned about. The
  (b)/(c) failures are the old `finally` printing nothing. This matches
  `gate-logs/C4-verify.log`.
- **Production path.** The tests drive the real `handoff.session` (the function called at
  `leaves.py:918`, `:1111`, `:3419`, `:3470`, `:3567`, `:3636`) and the real hook file, not a
  copy. The one-line-note test breaks the check with a real `AttributeError` (`doctor = 1` in
  `pdca.toml`), not a mock.
- **The reap never raises out of the context manager.** I looked for `SystemExit` or other
  non-`Exception` raises in the reap's call tree (`brief`, `doctor`,
  `config.current_doctor_checks`, `cli.contribution_problems`,
  `leaves.signoff_decision`/`signoff_rationale`) and found none. The leaf's own exception
  passes through untouched (tested).
- **Other turn-end hooks.** None in `settings.json`, the agent frontmatter, or any other
  vendor config in the template. No leftover "the Stop hook enforces…" promises in prompts,
  `docs/` or `PCDA/`, apart from the two `leaves.py` comments the brief left for a follow-up
  (`:917`, `:1107`).
- **Scope.** The `leaves.py` hunks stay out of `do_plan` (`:904`), `do_plan_batch` (`:1056`)
  and `run_plan_advisory_batch` (`:3356`).
- **Gate claims.** The claims in `check-gates.json` (C4 pass, C5 production import, T2/T3
  pass, T4 deferred to publish) match the frozen logs. T3 really ran the copier render/update
  suites (24 tests, none skipped) and the 1805-test driver suite.

### Advisory — code-review

# Advisory code review — issue #534

Went through `patch.diff` against the target source (`handoff.py`, `handoff_guard.py`,
`settings.json`, `leaves.py`, and both test files), plus the frozen C4/C5/T2/T3/T4 gate
logs. No correctness bug introduced by this patch, and no reuse/duplication or
efficiency issue worth flagging.

Specific things checked, for the record:

- `handoff.session()`'s new `finally` (`template/src/pdca_harness/handoff.py:314-321`)
  nests `report_at_reap(...)` inside its own `try/finally` so `path.unlink` still runs
  even if the report step misbehaves — an improvement over the pre-patch single-level
  finally, not a regression.
- The state merge `{**_read_json(path), **registered}` (`handoff.py:319`) correctly
  lets `registered` (the driver's own spawn-time `role`/`bundles`/`baseline`) win over
  whatever the scratch file holds, while preserving `passed`/`abandoned` written during
  the session — verified against `_read_json`'s dict-or-`{}` guard
  (`handoff.py:226-233`) and exercised by
  `test_the_report_names_the_bundles_the_driver_registered`
  (`template/tests/test_handoff_reap.py:262-269`), which passed in the C4 green leg.
- `handoff_guard.py`'s no-argument branch (`template/.claude/hooks/handoff_guard.py:76-78`)
  is unconditional — it never reads stdin or checks env — so it can't regress into
  blocking a turn end even if some future edit adds env-sensitive logic above it. Matches
  criterion (a).
- `settings.json` after the hook removal (`template/.claude/settings.json`) is still
  valid JSON with no dangling comma or empty `hooks` husk.
- The stale comment "the Stop hook can verify the brief" at
  `template/src/pdca_harness/leaves.py:916-917` is now inaccurate post-patch, but the
  brief explicitly puts `do_plan`'s body out of scope for this bundle (to keep the diff
  clear of #480, same wave) and names this exact comment as deferred to a follow-up. Not
  a defect this patch introduced — flagging only so it isn't mistaken for one.
- C4's red leg (`gate-logs/C4-verify.log`) shows all 16 new/changed assertions failing
  pre-fix for the reasons the brief predicts (Stop hook still registered, `_stop_verdict`
  returns 2, reap reports nothing), and C4 green shows them passing with no `stop_problems`
  logic change hidden in the diff — the red/green pair genuinely exercises this fix rather
  than a coincidental one.

If a human wants a second opinion on anything here, the only candidate is the stale
`leaves.py:916-917` comment above, but it's already accounted for by the brief's Ordering
note, so I'm not raising it as NEEDS-HUMAN.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Establish that affected paths have no superseding merged or closed/rejected solution — the brief records path-based history but issue-reference-based closed-work searches, and the supplied one-commit target cannot independently settle that question (`brief.md:115`).
- [ ] Validation — fitness-to-purpose — Confirm that terminal warnings at process exit sufficiently support human sign-off, particularly when a malformed-but-present artifact can still reach downstream processing — automated protocol tests establish behavior, but this operational adequacy remains a human decision (`target/docs/01-render-and-integrate.md:178`, `target/template/src/pdca_harness/handoff.py:333`).
- [ ] **A blank abandon value hides the reap report completely.**
- [ ] **`check_planner`'s docstring still describes the retired hook.**
- [ ] external dependency: write permission for `template/.claude/**` in the Do worktree — Claude Code refused every builder edit under `template/.claude/` as a "sensitive file" (`settings.json`, `hooks/handoff_guard.py`, `commands/handoff.md.jinja`; all three tried with the Edit tool, all refused, and the session is non-interactive so the prompt could not be approved). I did not route around the refusal with a shell write. Those three hunks are in `patch.diff`, built with `git diff --no-index` from working copies in the worktree's gitignored `.cache/534/`, and `git apply --check --cached patch.diff` passes against `main`. But they were never applied at their real paths during Do, so the green leg of the 5 tests that read those files (4 in `test_handoff_reap.py` class `NoTurnEndIsIntercepted`, plus `test_handoff.py::test_hook_ships_and_is_not_registered_on_stop`) was shown only against the copies (see "Evidence" below). The C4 gate at Check, where the driver applies `patch.diff` itself, is the first run at the real paths. The root render/update suite (T3) could not be run meaningfully in Do for the same reason.

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
- Iteration delta (if iterating): The approach is right (drop the Stop registration, report the unmet contract at reap, report only) and should be kept as is; iterate only on the two implementation findings from the adversarial review: 1. A blank abandon value hides the reap report completely. `handoff.session`'s reap (handoff.py:339-340) strips `abandoned`, finds it empty and calls `stop_problems`, but `stop_problems` (handoff.py:419-420) tests the UNSTRIPPED value, treats " " as abandoned and returns [] — so neither the reason nor the problem list is printed. Use one "is it abandoned" test in both places (strip in `stop_problems`, or drop a blank `abandoned` before calling it) and add a whitespace-only abandon case to the `ReportedAtReap` tests. 2. `check_planner`'s docstring (handoff.py:103-106) still describes the retired hook ("at the Stop boundary a wholly-absent brief passes there"); reword it to the session-end check, as the brief's Scope already covers handoff.py docstrings that describe a Stop hook. Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py, including their stale "Stop hook" comments (issue 480 edits those functions).
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
