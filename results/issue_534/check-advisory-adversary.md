# Adversarial review — issue 534 (handoff contract reported at reap, not at turn end)

Verdict: **could not refute the fix.** I attacked the red→green proof, the claim that no
turn end is blocked, the report rules (d)–(g), and the gate verdicts. The evidence holds up.
Two small gaps are listed at the end. Neither breaks a criterion item, so by the brief's own
rule ("a finding that does not break one of the criterion items is a follow-up issue") they
are follow-up candidates, not reasons for another Do round.

## Refutation attempts that failed

- **Red leg is real and fails for the right reason.** I copied the four changed test modules
  onto a clean clone of the pre-fix tree and ran them the gate's way (`template/`,
  `PYTHONPATH=src`). `test_handoff_reap` failed 46 times with 2 errors; `test_handoff` failed
  twice. The (a) tests fail with `2 != 0` and the old "This signoff leaf session may not end
  yet" text, *after* the liveness step (`--check` → 1) passed
  (`template/tests/test_handoff_reap.py:228`, `:263`). So the round-1 trap (the hook falling
  back to "contract check unavailable — allowing the stop" and exiting 0) is not what makes
  these tests pass. The frozen log `gate-logs/C4-verify.log` matches what I got.
- **Tests exercise production, not a copy.** They load the real hook file and call
  `handoff.session` / `stop_problems` / `leaves._*_prompt` from `pdca_harness`. The subprocess
  test runs the real `template/.claude/hooks/handoff_guard.py` with no arguments, the way the
  old registration did.
- **(f) quiet suite, checked by rule rather than by test name.** On the patched tree the
  whole driver suite ran 1817 tests, OK (2 skipped). stdout and stderr together contain
  **zero** `handoff` lines. `gate-logs/T3-suite.log` also has zero `handoff:` lines.
- **(a) no other turn-end hook.** No `Stop` / `SubagentStop` is registered anywhere else. The
  only agent frontmatter `hooks:` blocks are PreToolUse ones for builder and publisher
  (`template/.claude/agents/publisher.md.jinja:12-20`). Nothing in `template/src` passes
  hooks through `--settings`.
- **(b)/(c) false report from driver-side work inside the `with` block.** Every
  `handoff.session` call site wraps only `_invoke`
  (`template/src/pdca_harness/leaves.py:918`, `:1111`, `:3419`, `:3470`, `:3567`, `:3636`).
  The driver does not move or read artifacts before the reap, so a discharged session cannot
  be misreported as undischarged.
- **(e) escaping.** Every session-controlled string goes through `_printable`
  (`handoff.py:303-314`): the reason, dependency tokens, and detect `cmd`/`hint` quoted from
  `pdca.toml`. `contribution_problems` (`cli.py:1162-1193`) prints nothing itself. A zero-width
  space as the abandon reason is printed as a visible escape sequence, so it is not hidden.
- **(g) prose.** Searching `template/` and `docs/` finds no remaining text that promises
  hook enforcement, apart from the deliberately excluded comment at `leaves.py:917`.
- **Gate verdicts.** None of the `check-gates.json` claims look overstated. C5 names the one
  added test module. T4 being `deferred` is correct, since the PR body is not drafted until
  publish.

## Gaps found (follow-up candidates, not criterion breaks)

- `template/src/pdca_harness/handoff.py:342` — `_doctor_table_problem` treats a **missing**
  `pdca.toml` as readable. `Config.current_doctor_checks` (`config.py:547-550`) then quietly
  falls back to the rows loaded at startup. That is exactly the fallback its own docstring
  (`handoff.py:334-337`) says the reap must not pass off as "a check of the table the session
  left behind." Reproduced: a Config whose startup rows register `frobnicator` (cmd `true`),
  a brief naming `` `frobnicator` ``, `pdca.toml` deleted → the planner reap prints nothing.
  With a `pdca.toml` that lacks the row, it reports it. The trigger is contrived (the session
  has to delete the instance's `pdca.toml`), and exempting a missing file is what keeps the
  synthetic test Configs quiet. Worth a one-line docstring fix or a follow-up, not a round.
- `template/src/pdca_harness/handoff.py:128-141` with `:557-560` — the per-bundle failure
  handling covers the whole bundle. If the dependency clause raises *after* the field checks
  found problems, the field problems are dropped. Reproduced with a readable table whose row
  has a TOML-escaped NUL byte at the end of its `cmd`, and a brief with an empty Success
  criterion. The report says only `issue_7: could not check (ValueError: embedded null byte)`,
  and the empty-criterion item (one of the two cases the brief says only this report catches)
  is lost. This matches (d)(3) word for word, and the trigger is contrived (a NUL in a cmd,
  or the fork failing), so it is a follow-up at most.
- Regression-guard gap, not a defect: `test_the_template_registers_no_turn_end_hook`
  (`template/tests/test_handoff_reap.py:209`) checks only `settings.json`. A future `Stop:`
  entry in an agent wrapper's frontmatter (`template/.claude/agents/*.md.jinja`) would bring
  the deadlock back without failing any test. Nothing registers one today.
