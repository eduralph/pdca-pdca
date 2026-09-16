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
