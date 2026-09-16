# Brief — issue 534 / handoff-contract-checked-at-reap-not-turn-end

- **Slug:** handoff-contract-checked-at-reap-not-turn-end
- **Defect:** `template/.claude/settings.json:60-71` registers `handoff_guard.py` as a Claude
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
- **Decision (maintainer, Plan session 2026-09-15):** of the issue's three fix shapes, take
  shape 3. Drop turn-end enforcement entirely and check the contract when the driver reaps the
  leaf's process. The reap check **only reports**: it prints what is unmet and changes no
  bundle state, and it does not reopen the session. This is safe because the Stop hook never
  covered the absent-artifact case anyway (Ctrl-D / `/quit` ends the process whatever the hook
  says), and the driver already handles each absent artifact after the session:
  `flow.py:369-372` (no brief), `flow.py:152-155` / `:1378-1392` (no decision),
  `publish.py:55-60` (no publish artifacts). The reap report is kept because two
  malformed-but-present cases are caught by nothing downstream: a brief whose Success
  criterion / Repo + branch target is empty (`handoff.py:116-119`), and an `iterate-*` /
  `discontinue` decision with no rationale (`handoff.py:143-146`; `signoff.py:208` then
  records an empty Iteration delta, so the next Do is not told why the attempt was rejected).
- **Success criterion:** all of the following, shown by the named test at C4:
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
- **Falsifiability:** RED is reachable offline on the template driver suite. Pre-fix,
  (a) fails because `template/.claude/settings.json` registers the Stop hook and `_stop_verdict`
  returns 2 for an undischarged contract. (b) fails because `handoff.session()`'s `finally`
  (`handoff.py:306-311`) reports only an abandon reason. **Trap for Do:** if the hook fixture
  cannot load a config, the pre-fix hook takes its "contract check unavailable — allowing the
  stop" branch (`handoff_guard.py:59-62`) and exits 0, so the red leg would be a false green
  (C4 FAIL). The (a) test must give the hook a working contract check (a loadable instance
  config, or the hook module loaded in-process as `test_handoff.py:143-147` does, with its
  config lookup pointed at the test's `Config`) and show that pre-fix it really returns 2.
  (b) needs only existing API (`handoff.session`, `handoff.record_abandon`) and is the most
  reliable red.
- **Invariant to restore:** an interactive leaf's turn end always hands control to the human.
  No harness mechanism may turn a turn end into feedback to the model. The exit contract is
  judged at the session boundary (the leaf's process exit, where the driver reaps it), and
  its verdict goes to the human, not the model. Source: Claude Code hooks reference (Stop runs
  "when the main agent has finished responding"; exit 2 feeds stderr back to the model), and
  #331's own framing that the question is "did the leaf discharge its contract when the
  session ended" (`handoff.py:3-7`). This holds across all four contract roles, not one
  module.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** none
- **Ordering note:** runs in one wave with 467, 480, 527 and 529 (run 3 of
  plan-0.60-bug-order.md; the instance driver is v0.57.0, so each run is one wave). 480 also
  edits `template/src/pdca_harness/leaves.py`, in the bodies of `do_plan` (`:904-927`) and
  `do_plan_batch` (`:1055-1133`) and in `run_plan_advisory_batch`. To keep the two diffs apart,
  this bundle **does not touch those three functions**, not even their comments (the stale
  "Stop hook" comments at `leaves.py:916-917` and `:1104-1108` are left for a follow-up).
  #508 and #528 (same hook/handoff family) go in run 4, after this lands.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** remove turn-end enforcement of the interactive leaves' exit contract and move
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
- **Repro instruction:** on `main`, `cd template && PYTHONPATH=src python3 -c` a snippet that
  sets `PDCA_HANDOFF_ROLE=signoff` and a state file registering an empty bundle dir, loads
  `.claude/hooks/handoff_guard.py`, points `_bootstrap` at a test `Config` with an interactive
  signoff leaf, feeds `{}` on stdin and calls `main()` with no args: it returns 2 and prints
  "This signoff leaf session may not end yet". Separately, enter and exit
  `handoff.session(cfg, "signoff", [bundle])` with no `signoff-decision`: nothing is printed.
- **External dependencies:** none — base toolchain only (python3 ≥ 3.11, git); no Claude Code binary is needed, the hook protocol is exercised by calling the script the way Claude Code does
- **Test file:** template/tests/test_handoff_reap.py (new), plus the sanctioned update to
  template/tests/test_handoff.py described in Scope. Supplementary, advisory T3: the root
  render/update suites (`tests/test_render_and_run.py`, `tests/test_update_compat.py`), since
  `settings.json` is a rendered template file and `copier update` must still apply cleanly.
- **Citations expected:** Do cites path:line on `main` for every change. Peer callsites:
  load the hook module in-process as `template/tests/test_handoff.py:143-147` does; build the
  contract `Config` with `_cfg()` at `test_handoff.py:83-104`; capture the reap report as
  `test_abandon_reason_is_reported_when_the_driver_reaps` does (`test_handoff.py:323-328`,
  `redirect_stderr` around `handoff.session`).
- **Prior-art check (triage cycles):** by path on origin/main (fetched 2026-09-15):
  `handoff_guard.py` and `handoff.py` have one commit, `900d638` (#331, which introduced
  them); `settings.json`'s last change is `a7df381` (permission rules, unrelated). No open PR
  touches these files (open: #542, #543, both `progress.py`/`leaves.py` error logs). No closed
  or merged PR references #534 (search hits #521 were line numbers). `gh search issues
  stop_hook_active` finds only #534. Related open issues: #508, #528, #492.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The approach is right (drop the Stop registration, report the unmet contract at reap, report only) and should be kept as is; iterate only on the two implementation findings from the adversarial review: 1. A blank abandon value hides the reap report completely. `handoff.session`'s reap (handoff.py:339-340) strips `abandoned`, finds it empty and calls `stop_problems`, but `stop_problems` (handoff.py:419-420) tests the UNSTRIPPED value, treats " " as abandoned and returns [] — so neither the reason nor the problem list is printed. Use one "is it abandoned" test in both places (strip in `stop_problems`, or drop a blank `abandoned` before calling it) and add a whitespace-only abandon case to the `ReportedAtReap` tests. 2. `check_planner`'s docstring (handoff.py:103-106) still describes the retired hook ("at the Stop boundary a wholly-absent brief passes there"); reword it to the session-end check, as the brief's Scope already covers handoff.py docstrings that describe a Stop hook. Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py, including their stale "Stop hook" comments (issue 480 edits those functions).
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The approach is right (drop the Stop registration, report the unmet contract at reap, report only) and should be kept as is; iterate only on the two implementation findings from the adversarial review:
  1. A blank abandon value hides the reap report completely. `handoff.session`'s reap (handoff.py:339-340) strips `abandoned`, finds it empty and calls `stop_problems`, but `stop_problems` (handoff.py:419-420) tests the UNSTRIPPED value, treats " " as abandoned and returns [] — so neither the reason nor the problem list is printed. Use one "is it abandoned" test in both places (strip in `stop_problems`, or drop a blank `abandoned` before calling it) and add a whitespace-only abandon case to the `ReportedAtReap` tests.
  2. `check_planner`'s docstring (handoff.py:103-106) still describes the retired hook ("at the Stop boundary a wholly-absent brief passes there"); reword it to the session-end check, as the brief's Scope already covers handoff.py docstrings that describe a Stop hook.
  Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py, including their stale "Stop hook" comments (issue 480 edits those functions).
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: The approach is right and should be kept as is (no Stop registration, the no-argument hook path inert, report-only check at reap, one shared `_abandon_reason` test). Iterate only on §6.2, the adversarial finding: one bundle whose check raises hides the whole batch report. `stop_problems` checks every registered bundle in one loop (`handoff.py:445-447`) and `report_at_reap` wraps the whole call in one `try` (`handoff.py:350-357`), so e.g. a non-UTF-8 or directory `signoff-decision` in `issue_7` replaces `issue_8`'s real problem (iterate-do with no rationale) with a single "could not check … — nothing reported" line that does not even name the broken bundle. Fix: catch errors per bundle inside the loop, report `issue_7: could not check (<error>)` and carry on with the rest. Keep config-wide failures as the one line `test_handoff_reap.py:358` expects. Add a two-bundle test where one bundle raises and the other's problem is still reported. No change needed for the settings.json copier-update conflict (§6.3): leave it as is, no PR/release-note warning required. Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py (issue 480).
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: The approach is right and should be kept as is (no Stop registration, the no-argument hook path inert, report-only check at reap, one shared `_abandon_reason` test, per-bundle error isolation). Iterate only on these two findings: 1. An abandon must not hide the problem list. This deliberately changes criterion (b)'s "in place of the problem list": under report-only nothing is blocked, so hiding the list only keeps information from the human. When an abandon reason is recorded, the reap prints the reason AND then every problem `stop_problems` finds. Today `report_at_reap` skips `stop_problems` when a reason is recorded (handoff.py:360-361), and `stop_problems` itself returns [] on an abandon (handoff.py:445-446); change both so the list is still computed and printed after the reason. Update the text that says "instead of / in place of the list" (docs/01-render-and-integrate.md, the handoff_guard.py docstring, the `record_abandon` / `stop_problems` / `report_at_reap` docstrings). Add a test: batch sign-off over issue_7 + issue_8, issue_7 gets `iterate-do` with no rationale, then `--abandon "out of time"` → the reap prints the reason AND `issue_7: decision 'iterate-do' has no rationale…`. 2. Silence the two tests that now print the reap report to real stderr: `test_session_registers_env_and_cleans_up` (test_handoff.py:304-313) and `test_act_session_carries_the_baseline` (:320-326). Wrap their `handoff.session(...)` blocks in `redirect_stderr(io.StringIO())`, as the other undischarged-session tests in that file already do. Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py, including their stale "Stop hook" comments (issue 480).
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The approach is right and should be kept as is (no Stop registration, the no-argument hook path inert, report-only check at reap, one shared `_abandon_reason` test, per-bundle error isolation). Iterate only on these two findings:
  1. An abandon must not hide the problem list. This deliberately changes criterion (b)'s "in place of the problem list": under report-only nothing is blocked, so hiding the list only keeps information from the human. When an abandon reason is recorded, the reap prints the reason AND then every problem `stop_problems` finds. Today `report_at_reap` skips `stop_problems` when a reason is recorded (handoff.py:360-361), and `stop_problems` itself returns [] on an abandon (handoff.py:445-446); change both so the list is still computed and printed after the reason. Update the text that says "instead of / in place of the list" (docs/01-render-and-integrate.md, the handoff_guard.py docstring, the `record_abandon` / `stop_problems` / `report_at_reap` docstrings). Add a test: batch sign-off over issue_7 + issue_8, issue_7 gets `iterate-do` with no rationale, then `--abandon "out of time"` → the reap prints the reason AND `issue_7: decision 'iterate-do' has no rationale…`.
  2. Silence the two tests that now print the reap report to real stderr: `test_session_registers_env_and_cleans_up` (test_handoff.py:304-313) and `test_act_session_carries_the_baseline` (:320-326). Wrap their `handoff.session(...)` blocks in `redirect_stderr(io.StringIO())`, as the other undischarged-session tests in that file already do.
  Still out of scope, unchanged: `do_plan` / `do_plan_batch` / `run_plan_advisory_batch` in leaves.py, including their stale "Stop hook" comments (issue 480).
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: The size backstop tripped: three rounds already spent (threshold 3), so this goes back to Plan instead of another rebuild. Keep the approach as is: no Stop registration, the no-argument hook path inert, a report-only check at reap, one shared `_abandon_reason` test, per-bundle error isolation, and the abandon reason printed before (not instead of) the problem list. In the re-plan, decide for each remaining round-4 finding whether it becomes its own issue or a small fold-in to this slice: 1. `handoff.py:462-468`: the shared `[[doctor.checks]]` pre-read in `stop_problems` gives a "could not check" false alarm on a planner batch where every issue was correctly left UNPLANNED. Either read it only when some bundle has a `brief.md`, or move it inside the per-bundle `try`. Add a test. 2. `handoff.py:368-369`: escape non-printable characters in the abandon reason before printing it, so a terminal escape code cannot hide the problem list that follows. 3. `docs/01-render-and-integrate.md:177-180` and the `report_at_reap` docstring (`handoff.py:360-363`) promise more than the code does on the CSV-batch planner path: `stop_problems` returns [] once any `/handoff` has passed (`handoff.py:478-479`). Reword to "every bundle the driver registered". Re-checking the briefs the session added belongs in `do_plan_batch` (issue 480). 4. `test_state_resolved.py:191` and `:217` print the reap report to the real stderr. Wrap each in `redirect_stderr(io.StringIO())`.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The size backstop tripped: three rounds already spent (threshold 3), so this goes back to Plan instead of another rebuild. Keep the approach as is: no Stop registration, the no-argument hook path inert, a report-only check at reap, one shared `_abandon_reason` test, per-bundle error isolation, and the abandon reason printed before (not instead of) the problem list. In the re-plan, decide for each remaining round-4 finding whether it becomes its own issue or a small fold-in to this slice:
  1. `handoff.py:462-468`: the shared `[[doctor.checks]]` pre-read in `stop_problems` gives a "could not check" false alarm on a planner batch where every issue was correctly left UNPLANNED. Either read it only when some bundle has a `brief.md`, or move it inside the per-bundle `try`. Add a test.
  2. `handoff.py:368-369`: escape non-printable characters in the abandon reason before printing it, so a terminal escape code cannot hide the problem list that follows.
  3. `docs/01-render-and-integrate.md:177-180` and the `report_at_reap` docstring (`handoff.py:360-363`) promise more than the code does on the CSV-batch planner path: `stop_problems` returns [] once any `/handoff` has passed (`handoff.py:478-479`). Reword to "every bundle the driver registered". Re-checking the briefs the session added belongs in `do_plan_batch` (issue 480).
  4. `test_state_resolved.py:191` and `:217` print the reap report to the real stderr. Wrap each in `redirect_stderr(io.StringIO())`.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
