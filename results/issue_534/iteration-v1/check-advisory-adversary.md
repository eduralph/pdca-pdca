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
