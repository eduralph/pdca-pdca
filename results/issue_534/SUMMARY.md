# Result — issue 534 / handoff-contract-reported-at-reap-not-turn-end

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `template/.claude/settings.json:60-70` registers `handoff_guard.py` as a Claude
  Code **Stop** hook. Stop fires every time the main agent finishes a turn, not when the
  session ends. `_stop_verdict()` (`template/.claude/hooks/handoff_guard.py:48-73`) exits 2
  while the leaf's contract is undischarged, and on exit 2 Claude Code sends the hook's
  stderr back to the model instead of handing the turn to the human (the hook's own
  docstring says so at `handoff_guard.py:13-15`). An interactive leaf that asks the human a
  question therefore never reaches them: the model gets the guard's text, answers it, ends
  another turn, and is blocked again. Nothing bounds the repeat — the Stop envelope, which
  carries `stop_hook_active` for exactly this purpose, is parsed and thrown away
  (`handoff_guard.py:53`). Observed: a sign-off session blocked twelve turns in a row, and
  this re-plan session was blocked on every turn it asked the human a question. The pressure
  on the model is to write the artifact the guard demands, and for sign-off that artifact is
  `signoff-decision` — the human's own decision. Live for every interactive leaf with a
  contract: planner, signoff, publisher, act (`handoff.py:70-78`).
- Success criterion: all of the following, shown by the named tests at C4. Items (a)–(c)
  are the fix; (d)–(g) are the rules the report itself must obey — they are part of the
  criterion, not polish.
  (a) **No turn end is intercepted.** The rendered template registers no hook on the Stop
      event, and `handoff_guard.py` run the way the old registration ran it (no arguments, a
      Stop-event JSON envelope on stdin, `PDCA_HANDOFF_ROLE` and `PDCA_HANDOFF_STATE` set,
      and the registered bundle's contract **undischarged**) exits 0 and writes nothing to
      stderr. An instance whose `settings.json` still carries the old registration (a
      `copier update` merge that kept it) therefore cannot deadlock either.
  (b) **The contract is reported at reap.** When the `handoff.session(...)` context the
      driver wraps around an interactive leaf exits with the contract undischarged, the
      problems `stop_problems()` finds are printed to **stderr**, naming the role and each
      bundle (a sign-off bundle with no `signoff-decision`; a signoff `iterate-do` with no
      rationale; a planner brief with an empty Success criterion). A discharged contract
      prints nothing.
  (c) **Report only.** The reap writes nothing into any bundle, deletes or moves no artifact,
      raises nothing, and does not reopen the session. A failure inside the check degrades to
      a printed line, never an exception out of the context manager (the existing rule at
      `handoff.py:273`: a checked exit contract must never break the leaf it checks).
  (d) **The report hides nothing.** Four cases, each with its own test:
      1. **An abandon never hides the list.** A recorded `--abandon` reason is printed
         first, and then every problem `stop_problems()` finds. `stop_problems()` does not
         read `abandoned` at all. (This deliberately reverses the pre-2026-09-15 rule
         "reason instead of the list": under report-only nothing is blocked, so hiding the
         list only keeps information from the human.)
      2. **One "was it abandoned?" test.** A blank or whitespace-only `abandoned` value —
         which a session can write straight into its own scratch file — is no reason: no
         abandon line is printed and the problem list still is. The reap and
         `stop_problems()` must not disagree about what counts as abandoned.
      3. **One bundle's failure never hides another's.** A bundle whose check raises (a
         `signoff-decision` that is not UTF-8, a directory where a file belongs) is listed
         as `<bundle>: could not check (<error>)` and every other registered bundle is still
         checked and reported.
      4. **A broken `[[doctor.checks]]` table is reported, and hides nothing.** Planner
         bundle checks read that table from `pdca.toml` as it is at reap time (the session
         may have edited it). If it cannot be read, the reap says so at **every planner
         session's reap** — whether the bundles were registered or not, and whether any of
         them carries a `brief.md` or not. A broken table is a real problem, and a batch
         that rightly left every issue UNPLANNED must still hear about it. The message names the
         cause and its actual effect: the file and table that failed, the error, and that
         the dependency clause was not checked. It must not claim the exit contract was not
         checked when the rest of it was. The checks that do not need the table — `Slug`,
         `Success criterion`, `Repo + branch target` for every authored brief — still run
         and are still reported next to it. One line for the table, however many bundles are
         registered.
  (e) **Nothing the session wrote is printed raw.** Every line the reap prints — the abandon
      reason and each problem item — has its non-printable characters escaped, so text a
      session controls (a `--abandon` reason, a dependency token quoted out of a brief)
      cannot use a terminal escape such as `ESC[8m` to conceal the lines that follow it.
  (f) **The suite stays quiet.** No test in the driver suite prints the reap report to the
      real stderr. Every test that drives `handoff.session` (or a function that does) over
      an undischarged contract captures it, as `test_handoff.py:323-328` already does with
      `redirect_stderr`. Confirmed today on the round-4 tree: the only remaining leaks are
      `template/tests/test_state_resolved.py:191` and `:217`. Check this by rule, not by the
      two names: run the whole driver suite and grep its stderr for `handoff:` — that is how
      those two were found, and how rounds 3 and 4 each missed the next pair.
  (g) **The prose is true.** No text promises Stop-hook enforcement to the model or the
      operator. Where the driver could not register a bundle set (the CSV/default batch
      planner, Act), `docs/01-render-and-integrate.md` and the `report_at_reap` /
      `stop_problems` docstrings say what the code does — the session must have named its
      work through a passing `/handoff`, and the re-read covers **every bundle the driver
      registered** — with no wider promise. Re-reading the briefs a CSV session authored is
      issue #549 and is not done here. **One exclusion, deliberate and not a finding:** the
      stale comment at `leaves.py:916-917` stays untouched for the ordering reason above. It
      is a developer comment, not text the model or the operator reads, and its twin at
      `leaves.py:1104-1108` IS corrected here. At least one test pins the part a reader cannot be
      trusted to re-check: the shipped text the MODEL reads — the rendered `/handoff` command
      body and the planner / sign-off leaf prompts — no longer tells it that a hook enforces
      the contract when a turn or session ends. (Round 4 satisfied this item but left it to
      review; with no test it can silently come back.)
  (h) `/handoff <id>` (`handoff_guard.py --check`) and `--abandon` keep working exactly as
      today: the model's self-check and the typed-abandon channel, verdict by exit status,
      nothing written into any bundle.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: remove turn-end enforcement of the interactive leaves' exit contract, judge it at
  the session boundary, and make that report obey the rules in the criterion. Files in reach:
  `template/.claude/settings.json` (the Stop registration),
  `template/.claude/hooks/handoff_guard.py` (the no-argument path; docstring),
  `template/src/pdca_harness/handoff.py` (the `session()` reap and the reporting it drives;
  module and function docstrings that describe a Stop hook), and the text that promises
  Stop-hook enforcement to the model or the operator: the `leaves.py` prompt strings in
  `_plan_prompt` (`:1035`), `_plan_batch_prompt` (`:1293`, `:1310`) and `_signoff_prompt`
  (`:3438`), the comments in `run_signoff` (`:3414`), `run_publish` (`:3628`) and
  `do_plan_batch` (`:1104-1108` only — see Ordering note),
  `template/.claude/commands/handoff.md.jinja:17-19`, and
  `docs/01-render-and-integrate.md:174-181`. Those prompts should say `/handoff` is the
  session's self-check and the driver reports an unmet contract to the human when the session
  ends. Criterion (d)(4) may change how `check_planner`'s dependency clause is invoked or
  reported from the reap — that is **in scope**, provided `/handoff`'s own behaviour and
  output are unchanged. Updating the driver suite to match is in scope and expected:
  `test_handoff.py::test_stop_hook_ships_and_is_registered` (`:133-141`) asserts the
  registration this fix removes and must be inverted; the module docstring's item (b)
  (`:10-11`) needs rewriting; `test_abandon_is_the_escape_hatch` (`:341-344`) asserts
  `stop_problems(...) == []` for an abandoned session, which criterion (d)(1) reverses, so it
  changes too; the other `StopVerdict` tests (`:331-362`) exercise `stop_problems()`, which
  stays, and must keep passing.
  / out of scope: `do_plan` and `run_plan_advisory_batch` in `leaves.py`, and everything inside
  480's two `do_plan_batch` hunk ranges — the single exception is the stale comment at
  `leaves.py:1104-1108`, which is in scope (see Ordering note and criterion (g)); **#549** — re-reading the briefs a CSV/default batch session authored
  (that needs a session-start snapshot, and is a separate slice); reopening a session,
  blocking, or changing any flow/state transition on an unmet contract; renaming
  `stop_problems`; the contents of the per-role checks `check_signoff` / `check_publisher` /
  `check_act`, and of `check_planner` beyond what (d)(4) requires; #508 (`/handoff` cannot run
  in a rendered instance) and #528 (Act vs `/handoff`); #492 `/interview`; #404 (a rendered
  `/abandon` command); this instance's own copy of the hook, which changes at its next
  `copier update`.

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

Review issue #534: let interactive leaves return each turn to the human and report unmet handoff contracts only when the driver reaps the session.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable contract distinguishes free turn completion from advisory session-exit reporting and explicitly bounds CSV/Act coverage; `brief.md:36`, `target/docs/01-render-and-integrate.md:175`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix reproduces the blocked legacy hook and missing reap reports: 2 failures in the existing handoff module and 46 failures plus 2 errors in the new module; `target/template/tests/test_handoff_reap.py:263`, `review-evidence/red-tests.test_handoff_reap.log:1`. |
| C3 Change | PASS | Registered bundles remain attributable, abandon reasons cannot suppress unmet items, and failures stay advisory without changing bundle contents; exercised at `target/template/tests/test_handoff_reap.py:385` and `target/template/tests/test_handoff_reap.py:518`, grounded in `target/template/src/pdca_harness/handoff.py:403` and `target/template/src/pdca_harness/handoff.py:556`. |
| C4 Verification (red→green) | PASS | After stash restoration all 158 tests across the four changed modules pass, including a real hook subprocess whose live `--check` fails before its no-argument invocation succeeds silently; `target/template/tests/test_handoff_reap.py:281`, `review-evidence/green-tests.test_handoff_reap.log:3`, corroborated by `gate-logs/C4-verify.log:732`. |
| C5 Causal adequacy | PASS | Removing the turn-end interception eliminates the feedback-loop cause, including retained legacy registrations; no capability probe masks a load-time cause, and new tests exercise production; `target/template/.claude/hooks/handoff_guard.py:77`, `target/template/.claude/settings.json:59`, `review-evidence/production-scanner.log:1`. |
| T1 Structure | PASS | The existing session boundary and per-role checks keep one contract source; a broken doctor table suppresses only the dependency clause while every bundle retains its other checks; `target/template/src/pdca_harness/handoff.py:113`, `target/template/src/pdca_harness/handoff.py:547`. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, and whitespace checks pass; shipped model text has regression coverage against enforcement claims; `review-evidence/docs-lint.log:1`, `review-evidence/docs-render.log:3`, `target/template/tests/test_handoff_reap.py:757`; host-CI parity is also recorded at `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independent driver suite: 1,817 tests, two skips, zero stderr lines containing `handoff:`; actual render/update coverage is supported by the frozen 24-test successful run, with local rerun limits noted below; `review-evidence/driver.stderr:1080`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; their substantive audit is deferred to the mandatory publish gate, not waived; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | PASS | Path-based merged history and closed/rejected PR inspection found no competing fix; protected ordering regions remain unchanged and CSV artifact rereading stays outside this slice; `review-evidence/prior-art.json:1`, `target/template/src/pdca_harness/leaves.py:1107`, `target/template/src/pdca_harness/handoff.py:527`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether advisory terminal reports give operators sufficient information when leaving a contract unmet, accepting the documented CSV/Act coverage boundary; automation proves reporting and noninterference but cannot establish operator usefulness; `target/docs/01-render-and-integrate.md:178`, `target/template/src/pdca_harness/handoff.py:424`. |

No grounded patch defects found. This review is advisory; acceptance remains the human's decision.

Independent verification used the disposable `$PDCA_TARGET` in this directory. I stashed only the five changed production/model-command paths, retained all changed tests, ran each of the four affected test modules, popped the stash, and reran them. The red results matched the frozen C4 log: the two handoff modules failed on behavior, while the publish/state capture-wrapper modules passed on both legs. No test-module import failure substituted for reproduction. Green counts were 35 + 29 + 66 + 28. The new module exercises malformed artifacts, broken doctor tables across planner session shapes, blank and nonblank abandon reasons, escaped terminal controls, scratch corruption, and preservation of the leaf's own exception. The production-import scanner was rerun from `target/template/scripts/checks/test_exercises_production.py` with this bundle and `PDCA_PROD_PACKAGE=pdca_harness`.

The subsequent complete driver-suite rerun passed and its captured stderr contained no `handoff:` substring. Logs are retained under `review-evidence/`; all test temporary roots were directed inside this reviewer sandbox. `git diff --check` and `git apply --reverse --check ../patch.diff` passed after restoration, confirming the reviewed patch still matches the target. The protected `do_plan` and `run_plan_advisory_batch` function bodies are byte-for-byte unchanged; the sole `do_plan_batch` edit is the sanctioned comment.

The local root-suite attempt exited 77: `/usr/bin/python3` cannot import Copier, and the disposable one-commit checkout has no release tags (`review-evidence/root.stderr:36`). This is a reviewer-host/evidence limitation, not a patch failure or an undischarged dependency in the original verification: `gate-logs/T3-suite.log:38` shows the actual render cases and five update-compatibility cases executing successfully, followed by 24 tests and `OK`. The wrappers are instance-scoped, so I used direct target test/scanner commands and the complete frozen logs. No log was missing. No Claude Code session was launched; the protocol is exercised by the real hook subprocess, as the brief specifies.

Prior-art investigation queried GitHub commit history by every one of the ten affected paths. The handoff implementation, hook, command, and existing tests have only their introducing commit `900d638` (PR #398); the new reap test has no upstream history. Of 233 closed PRs, the only unmerged one is #4, touching only `README.md`, with no affected-path overlap. A broad closed-PR search for `534` returned #521 because its text contains that line number; its actual four paths are verifier/gates files and its issue is #474. It is not a competing fix. Results are retained in `review-evidence/prior-art.json` and `review-evidence/prior-art-pr521.json`. The available `target/template/docs/INTEGRATION.md.jinja:80` leaves project-specific human-only items as an unfilled template placeholder; it supplies no additional concrete obligation.

For the fitness decision, use the ordinary interactive sign-off session for a disposable bundle in an updated instance. Leave `signoff-decision` absent, ask the agent a question, and confirm its turn reaches you. End the session with Ctrl-D or `/quit`: the terminal should name the signoff role and missing bundle decision while the driver continues its normal flow. Repeat with `iterate-do` and no rationale to assess whether that report makes the corrective action clear. These are operator-validation steps; the corresponding automated hook and reap behavior has already passed.

### Advisory — adversary

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

### Advisory — code-review

# Advisory code review — issue #534

Second-lens pass (bugs the patch introduces; reuse/simplification/efficiency). Traced
the reap path end to end against the target tree: `session()`'s `finally` block, the
`registered`/`state` merge, `report_at_reap`, `stop_problems`, `_doctor_table_problem`,
`_printable`/`_emit`, and `handoff_guard.py`'s new no-argument/`--abandon`/`--check`
dispatch. No correctness bug found in this diff — the exception handling around each
new failure mode (deeply-nested JSON on the scratch file, a directory in an artifact's
place, a non-UTF-8 artifact, a structurally-broken `pdca.toml`, an unparseable
`pdca.toml`) is exercised by `test_handoff_reap.py` and matches what the target source
actually does; I did not find a case the tests miss. Two minor, non-blocking
observations, neither rising to something a human needs to decide:

- `template/src/pdca_harness/handoff.py:340-349` (`_doctor_table_problem`) parses
  `pdca.toml` twice on a planner reap when the table *is* readable: the explicit
  `tomllib.loads` call, then again inside `_doctor.registered_ids(cfg)` →
  `Config.current_doctor_checks()` (`template/src/pdca_harness/config.py:547-551`),
  which re-reads and re-parses the same file. This isn't redundant by accident —
  `current_doctor_checks()` swallows `TOMLDecodeError` and falls back to the run's
  snapshot, so the explicit parse is what lets the reap catch that case (confirmed by
  `test_a_pdca_toml_that_does_not_parse_is_a_broken_table_too`,
  `test_handoff_reap.py:1373-1389`) — but it is a double read+parse of the same small
  file, once per planner-role reap. Cheap in absolute terms (reap runs once per
  session, not in a loop), so not worth a round on its own; worth folding into one
  parse if this function gets touched again.
- `template/.claude/hooks/handoff_guard.py:73-76` adds a new "unknown mode" branch
  (any argv other than `--check`/`--abandon`, e.g. a typo, now exits 2 with a message
  instead of silently falling through to the old `_stop_verdict()`, which returned 0
  when `PDCA_HANDOFF_ROLE` was unset). This is a reasonable tightening — it only
  matters for a human/session invoking the script directly with a bad flag, not the
  retired Stop path, which always invokes with empty argv — but it has no direct test
  in either `test_handoff.py` or `test_handoff_reap.py`. Not required by the brief's
  criteria, so not a gap in this bundle's success criterion.

Scope check: the `leaves.py` edit at criterion (g)'s named exception (the stale "Stop
hook" comment at `leaves.py:916-917`) is confirmed still untouched in the target tree,
and the comment fix at the old `:1104-1108` location (now `leaves.py:1105-1109`) sits
between, not inside, the two `do_plan_batch` ranges the brief reserves for #480
(`:1070-1078`/`:1126-1136` old numbering) — no encroachment found.

No reuse/duplication issue found: `_printable` (`handoff.py:303-314`) is genuinely new
logic with no existing escaping helper elsewhere in `template/src` it should have
called instead.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Decide whether advisory terminal reports give operators sufficient information when leaving a contract unmet, accepting the documented CSV/Act coverage boundary; automation proves reporting and noninterference but cannot establish operator usefulness; `target/docs/01-render-and-integrate.md:178`, `target/template/src/pdca_harness/handoff.py:424`.
- [x] size backstop — this slice is behaving oversized: patch is 89 KB (threshold 80 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
