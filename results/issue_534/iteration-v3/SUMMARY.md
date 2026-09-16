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

Review issue #534: prevent interactive turn-end deadlocks and report unmet handoff contracts when the driver reaps the session, including blank-abandon and broken-bundle cases.

Source citations beginning `template/` or `docs/` are grounded on the restored, patched `$PDCA_TARGET`; evidence and brief citations are relative to this review directory. This review is advisory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The agreed boundary and observable outcomes are explicit: turns reach the human; session-end checks only report; self-check and typed abandonment remain available (`brief.md:28`; `template/tests/test_handoff_reap.py:164`). |
| C2 Reproduction (red pre-fix) | PASS | Independent stash/run reproduced the actual blocked turn: the live old hook returned 2, including as a subprocess; the 20 regression tests produced 24 assertion failures, with missing reap reports (`reviewer-red.log:3`; `template/tests/test_handoff_reap.py:198`). |
| C3 Change | PASS | The patch satisfies the agreed boundary and both carry-forward corrections; blank abandonment cannot suppress problems and a broken bundle cannot hide its peers (`template/src/pdca_harness/handoff.py:445`; `template/src/pdca_harness/handoff.py:468`; `template/tests/test_handoff_reap.py:302`; `template/tests/test_handoff_reap.py:364`). |
| C4 Verification (red→green) | PASS | Restoring the patch changed the regression outcome to green: all 55 handoff tests pass, covering real hook subprocesses, unchanged bundle contents, error reporting, and preserved leaf exceptions (`reviewer-green.log:7`; `template/tests/test_handoff_reap.py:330`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Removing the turn-end hook and making its legacy invocation unconditionally silent removes the feedback-loop cause; the reporting exception boundaries isolate failures and are not capability probes masking that cause (`template/.claude/hooks/handoff_guard.py:76`; `template/src/pdca_harness/handoff.py:338`; `template/tests/test_handoff_reap.py:145`). |
| T1 Structure | PASS | The existing contract module and session boundary remain the owners of the check; the three functions excluded for concurrent work are unchanged, including comments (`template/src/pdca_harness/handoff.py:343`; `reviewer-checks.log:1`). |
| T2 Shape | PASS | Independently rerun docs lint and 22-page render/link audit pass, as does whitespace checking; frozen docs and host-CI-parity logs agree (`docs/01-render-and-integrate.md:176`; `gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver run passes 1,808 tests with two skips; frozen evidence shows all 24 root render/update tests passed; the local root rerun is unavailable because this interpreter cannot import Copier (`reviewer-suite.log:1119`; `gate-logs/T3-suite.log:37`; `reviewer-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred row owes its substantive audit to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art coverage by affected file path across merged and closed/rejected work — the brief records path-based history but closed-work searches by issue/text, and this synthetic one-commit target has no remote or history with which to settle supersession (`brief.md:115`; `reviewer-checks.log:5`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether reporting malformed or missing artifacts at process exit gives operators sufficient visibility while preserving human control of each turn — protocol and report behavior pass automated tests, but operational adequacy remains the human sign-off decision (`docs/01-render-and-integrate.md:176`; `template/src/pdca_harness/handoff.py:354`). |

## Independent verification

- Stashed tracked changes in the disposable target, leaving the new regression test available; ran `python3 -m unittest discover -s "$PDCA_TARGET/template/tests" -p test_handoff_reap.py` with the target's `template/src` on `PYTHONPATH`. The old hook's contract check was live: both in-process and subprocess invocations returned 2, rather than taking a missing-config fallback. Result: 20 tests, 24 assertion failures (`reviewer-red.log`).
- Popped that stash and ran the same discovery with `-p 'test_handoff*.py'`: 55 tests passed (`reviewer-green.log`). The patch reverse-apply check succeeds on the restored target (`reviewer-checks.log:4`). No production source was edited by the reviewer.
- Ran the full offline driver suite from `target/template`: 1,808 tests passed, two skipped (`reviewer-suite.log`). Ran the production-import scanner against this bundle: its added test imports `pdca_harness`. Inspected the tests' calls into the actual hook and `handoff.session`, beyond the scanner's import heuristic.
- Ran the target's docs lint and renderer with `--check`, writing output inside this sandbox: lint clean, 22 pages rendered, internal links clean. `git diff --check` passed.
- All test temporary directories were directed inside this review directory with `TMPDIR`; evidence logs are retained here for the harness.

## Evidence limits and human decisions

**Root-suite host caveat:** `python3 -m tests.run_root_suite` returned 77 locally: Copier exists as a CLI but is not importable by `/usr/bin/python3` (`reviewer-root.log:6`). This does not establish a patch failure or an undischarged dependency in the frozen round: `gate-logs/T3-suite.log:37` explicitly shows the render and update-compat cases executing successfully, followed by 24 tests and `OK` at lines 54–56. No alias or shim was substituted for Copier. The unavailable instance-root wrappers were adjudicated from their supplied logs and, where available, their underlying target commands were rerun.

**Prior art:** the local investigation returned only synthetic base commit `c4597c7` and no remotes. The supplied brief names historical commits for three affected paths, but its closed/merged search is by `#534` and `stop_hook_active`, not the affected paths. Before clearing T5, establish whether prior merged or closed/rejected changes touching the files listed in `patch.diff` already address or reject this approach. No superseding change is established by the supplied evidence.

**Fitness:** the maintainer has already chosen report-only behavior; this review does not reopen that scope decision. Sign-off must judge whether the observed messages are sufficient for the intended workflow, especially malformed-but-present decisions and briefs that downstream processing does not reject. The relevant independently passing cases are `template/tests/test_handoff_reap.py:237`, `:245`, and `:364`.

No grounded patch defect found. The target was usable and the patch was restored; there is no stale-target caveat. The available integration document is the template with a TODO for project-specific human-only items (`template/docs/INTEGRATION.md.jinja:80`), so it supplies no additional enumerated decision.

### Advisory — adversary

# Adversarial review — issue 534 (handoff contract checked at reap, not turn end), iteration 3

Verdict: I could not refute the fix. The red→green evidence holds up when re-run, and every
break attempt against criteria (a)–(d) failed. One design point for the human (the abandon
reason still hides the problem list), two low-value notes, and the attempts that failed.

## Finding for the human

- NEEDS-HUMAN — **An `--abandon` still hides the whole problem list, including the one case the
  reap report exists to catch.** `report_at_reap` skips `stop_problems` when a reason is recorded
  (`template/src/pdca_harness/handoff.py:360-361`), and `stop_problems` returns `[]` for it too
  (`handoff.py:445-446`). That matches the brief's (b) ("in place of the problem list"), and it
  made sense when abandoning was the only way past the Stop hook's block. Under report-only
  nothing is blocked, so hiding the list now only keeps information from the human. Concrete
  case, reproduced on the patched tree: a batch sign-off over issue_7 + issue_8; the session
  writes `iterate-do` with no rationale into issue_7, then runs
  `--abandon "out of time, issue_8 next week"`. The prompt this diff adds invites exactly that
  (`leaves.py:3498-3499`), and so does the `/handoff` FAIL text (`handoff.py:416-417`). The reap
  prints only `the signoff session was deliberately abandoned — out of time, issue_8 next week`.
  `stop_problems` would have listed `issue_7: decision 'iterate-do' has no rationale…`, which is
  the malformed-but-present case the brief keeps the reap for. `signoff.py:208-209` then records
  an empty Iteration delta. The code does what the brief says, so this isn't an `[impl]` item. The
  question is whether (b) should say "print the reason, then the list".

## Notes (no action needed to accept)

- **The broken-config note is opaque, and it hides field problems.** The new one-time
  `[[doctor.checks]]` read (`handoff.py:458-464`) turns a malformed table into the one-line note at
  `handoff.py:362-364`. Reproduced: the planner session writes `[doctor.checks]` (single brackets,
  an easy typo for the `[[doctor.checks]]` rows its prompt tells it to register). The reap prints
  only `could not check the planner session's exit contract (AttributeError: 'str' object has no
  attribute 'get') — nothing reported`. It doesn't name `pdca.toml`, and the bundle's empty
  Success criterion goes unreported. That second part isn't new this round: `check_planner`
  reads the table at `handoff.py:128` after it has built its field problems, so they were lost
  before the hoist too. It also meets (c) as written. One small side effect of the hoist: an
  id-seeded batch where every id was left UNPLANNED (no brief, so `handoff.py:111-113` returns
  `[]`) now prints the same "could not check" line when the table is broken, where before it
  printed nothing. An optional polish would be to wrap the hoisted call so the note says
  "pdca.toml [[doctor.checks]] is unreadable". That alone doesn't justify another rebuild.
- **The report prints even when the leaf never started.** `session()`'s `finally`
  (`handoff.py:333-340`) runs the check however the body exited, including an `_invoke` that
  raised before any session existed (`claude` not on PATH → `FileNotFoundError` from
  `leaves.py:635`). Reproduced: `the signoff session ended with its exit contract not
  discharged … issue_7: signoff-decision is missing`, followed by the traceback, or by
  `flow.py:1386`'s "sign-off session … failed" in the batch path. This matches (b)'s wording and
  does no harm (report only), but the line describes a session that never ran.

## Evidence re-run

- Green: `cd template && PYTHONPATH=src python3 -m unittest tests.test_handoff
  tests.test_handoff_reap` on `$PDCA_TARGET` → 55 tests OK.
- Red: I copied the target into this sandbox, reverted the six production files with
  `git checkout HEAD --`, and re-ran → 25 failures, the same set as `gate-logs/C4-verify.log`.
  Both (a) hook tests fail before the fix with the live text `This signoff leaf session may not
  end yet`, from the in-process test and from the real subprocess. So the brief's false-green
  trap (the "contract check unavailable — allowing the stop" branch) was avoided.
- Production path: the tests drive the real `handoff.session` / `stop_problems` and the real hook
  file. They don't use a copy, so C5's claim holds. The T3 root suite really ran render and
  update-compat (copier was present, and `test_merge_leaves_no_conflict_markers` passed); these
  were not skips. I found no claim in `check-gates.json` that the logs don't support.

## Attempted, could not break

- **Another turn-end hook:** none left. `template/.claude/settings.json` has no `hooks` key. Agent
  frontmatter registers only `PreToolUse` (`builder.md.jinja`, `publisher.md.jinja`). Nothing in
  `copier.yml`, the repo-root `.claude/settings.json` or the family profiles adds one.
- **The old registration still firing:** the no-argument path (`handoff_guard.py:76-78`) returns 0
  before `_bootstrap`, with empty stdout and stderr. So neither an exit 2 nor a JSON
  `"decision": "block"` can reach the model, whatever `stop_hook_active` is.
- **A silent false green at reap:** the bundle set comes from the driver's `registered` dict
  (`handoff.py:338`), so a leaf that rewrites its scratch file can't shrink it. `abandoned` values
  of `0`, `false`, `[]` or blank count as "not abandoned" in both places. Deleting the scratch
  file still re-checks the artifacts.
- **Report only:** the publisher lint (`cli.contribution_problems`) only reads. The reap wrote
  nothing in any role.
- **Exceptions:** a raise in one bundle's check is caught per bundle, and a config-wide raise is
  caught once. The only escape I found is a print to a broken stderr pipe (the prints at
  `handoff.py:366-372` sit outside the `try`), which lets `BrokenPipeError` out. Every other stderr
  print in the driver has the same exposure, and an interactive leaf needs a live terminal anyway,
  so I don't count it.
- **Scope:** `do_plan`, `do_plan_batch` and `run_plan_advisory_batch` are untouched. The stale
  "Stop hook" comments at `leaves.py:917` and `:1104-1108` remain, as the brief requires.

### Advisory — code-review

# Check — advisory code review (issue #534)

Scope: correctness bugs the patch introduces, plus reuse/simplification/efficiency. Ground
truth is `$PDCA_TARGET` (post-patch tree). Both prior sign-off iteration findings (blank
abandon value, per-bundle error isolation) are fixed correctly and covered by new tests
(`_abandon_reason` in `handoff.py:269-278`, used by both `stop_problems` and
`report_at_reap`; the per-bundle `try/except` at `handoff.py:468-471`). Verified the new
test file passes standalone (`test_handoff_reap.py`, 20 tests) and together with the
updated `test_handoff.py` (55 tests, all green), matching the C4 gate log.

## Findings

- NEEDS-HUMAN [impl] — `template/tests/test_handoff.py:304-313` (`test_session_registers_env_and_cleans_up`)
  and `:320-326` (`test_act_session_carries_the_baseline`) open a `handoff.session(...)`
  whose contract is deliberately left undischarged (no `signoff-decision`, no act-log
  entry) and exit it without `redirect_stderr`. Before this patch `session()`'s `finally`
  only printed on a recorded abandon reason, so these two tests were silent. Now every
  exit runs `report_at_reap` (`handoff.py:295, 343-372`), which prints the full unmet-
  contract report to real stderr whenever the contract isn't discharged — confirmed by
  running the file directly (`-v` shows the "ended with its exit contract not
  discharged..." block printed mid-test for both). Both tests still pass — unittest
  doesn't fail on stray output — so this doesn't affect T3/C4, but it's noise the brief's
  own scope note ("Updating test_handoff.py to match is in scope") should have caught:
  every other test in the file that drives an undischarged session already wraps it in
  `redirect_stderr` (e.g. `:328-333`). A one-line fix: wrap those two `with` blocks in
  `redirect_stderr(io.StringIO())` the same way.

- No other findings. The `_abandon_reason` / `_error_text` helpers in `handoff.py:269-285`
  are new, single-purpose, and not duplicates of anything already in the module or of the
  `f"{type(exc).__name__}: {exc}"` pattern used elsewhere in the codebase (that pattern
  doesn't collapse embedded newlines the way `_error_text` does, which is what the "one
  line" contract in `report_at_reap`/`stop_problems` actually needs). The added
  `_doctor.registered_ids(cfg)` pre-check in `stop_problems` (`handoff.py:458-464`)
  duplicates a config read that `check_planner`'s own dependency checks also do per
  bundle, but that's a deliberate, tested tradeoff (one aggregate failure line instead of
  N per-bundle "could not check" lines for a shared input) — not a hot path, not worth
  changing. Scope carve-outs (`leaves.py:917`, `do_plan`/`do_plan_batch`/
  `run_plan_advisory_batch` left untouched) match the brief's explicit ordering note
  against issue #480 and don't leak into the diff.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm prior-art coverage by affected file path across merged and closed/rejected work — the brief records path-based history but closed-work searches by issue/text, and this synthetic one-commit target has no remote or history with which to settle supersession (`brief.md:115`; `reviewer-checks.log:5`).
- [ ] Validation — fitness-to-purpose — Decide whether reporting malformed or missing artifacts at process exit gives operators sufficient visibility while preserving human control of each turn — protocol and report behavior pass automated tests, but operational adequacy remains the human sign-off decision (`docs/01-render-and-integrate.md:176`; `template/src/pdca_harness/handoff.py:354`).
- [ ] **An `--abandon` still hides the whole problem list, including the one case the
- [ ] `template/tests/test_handoff.py:304-313` (`test_session_registers_env_and_cleans_up`)
- [ ] external dependency: write permission for `template/.claude/**` in the Do worktree — the Edit tool was refused again this iteration (tried on `template/.claude/settings.json`; the session is non-interactive, so the prompt could not be approved), so the three `.claude/` hunks were never applied at their real paths in Do. The 4 tests that read those files (5 failures: `test_handoff_reap.NoTurnEndIsIntercepted` x3, one with two subtests, plus `test_handoff::test_hook_ships_and_is_not_registered_on_stop`) and the root render slice were green in Do only against copies. C4 and T3 at Check, where the driver applies `patch.diff` itself, are the real-path run. Iterations 1 and 2 both passed C4 and T3 with byte-identical `.claude/` hunks.

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
- Iteration delta (if iterating): The approach is right and should be kept as is (no Stop registration, the no-argument hook path inert, report-only check at reap, one shared `_abandon_reason` test, per-bundle error isolation). Iterate only on these two findings: 1. An abandon must not hide the problem list. This deliberately changes criterion (b)'s "in place of the problem list": under report-only nothing is blocked, so hiding the list only keeps information from the human. When an abandon reason is recorded, the reap prints the reason AND then every problem `stop_problems` finds. Today `report_at_reap` skips `stop_problems` when a reason is recorded (handoff.py:360-361), and `stop_problems` itself returns [] on an abandon (handoff.py:445-446); change both so the list is still computed and printed after the reason. Update the text that says "instead of / in place of the list" (docs/01-render-and-integrate.md, the handoff_guard.py docstring, the `record_abandon` / `stop_problems` / `report_at_reap` docstrings). Add a test: batch sign-off over issue_7 + issue_8, issue_7 gets `iterate-do` with no rationale, then `--abandon "out of time"` → the reap prints the reason AND `issue_7: decision 'iterate-do' has no rationale…`. 2. Silence the two tests that now print the reap report to real stderr: `test_session_registers_env_and_cleans_up` (test_handoff.py:304-313) and `test_act_session_carries_the_baseline` (:320-326). Wrap their `handoff.session(...)` blocks in `redirect_stderr(io.StringIO())`, as the other undischarged-session tests in that file already do. Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py, including their stale "Stop hook" comments (issue 480).
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
