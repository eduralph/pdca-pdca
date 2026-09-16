# Build notes — issue 534 / handoff-contract-checked-at-reap-not-turn-end

Target: `eduralph/pdca-harness @ main` (`6ba00ba`). All `path:line` cites below are on
that commit unless marked "post-patch".

NEEDS-HUMAN external dependency: write permission for `template/.claude/**` in the Do worktree — Claude Code refused every builder edit under `template/.claude/` as a "sensitive file" (`settings.json`, `hooks/handoff_guard.py`, `commands/handoff.md.jinja`; all three tried with the Edit tool, all refused, and the session is non-interactive so the prompt could not be approved). I did not route around the refusal with a shell write. Those three hunks are in `patch.diff`, built with `git diff --no-index` from working copies in the worktree's gitignored `.cache/534/`, and `git apply --check --cached patch.diff` passes against `main`. But they were never applied at their real paths during Do, so the green leg of the 5 tests that read those files (4 in `test_handoff_reap.py` class `NoTurnEndIsIntercepted`, plus `test_handoff.py::test_hook_ships_and_is_not_registered_on_stop`) was shown only against the copies (see "Evidence" below). The C4 gate at Check, where the driver applies `patch.diff` itself, is the first run at the real paths. The root render/update suite (T3) could not be run meaningfully in Do for the same reason.

No `[[doctor.checks]]` row is proposed. A shell probe cannot see a Claude Code permission prompt, and a row that pretended to would be a fake probe. The fix is on the harness side: either the human approves the builder's `.claude/` edits for bundles whose Scope names `.claude/` files, or Plan flags such bundles so the human knows Do cannot write them.

## What changed and why

The maintainer picked fix shape 3 (brief, "Decision"): drop turn-end enforcement and judge the
contract when the driver reaps the leaf's process, report only.

1. **Stop registration removed**: `template/.claude/settings.json:60-71`. The whole
   `"hooks"` key goes, since Stop was its only entry. `permissions` and `sandbox` are
   byte-identical (checked with `json.loads` before and after).
2. **Hook's Stop mode removed, no-argument call made inert**:
   `template/.claude/hooks/handoff_guard.py`.
   - `_stop_verdict()` (`:48-73`) is deleted, and so is `import json` (`:30`), which only
     it used.
   - `main()`'s fallthrough (`:101`, `return _stop_verdict()`) becomes: an unknown
     argument is a usage error (exit 2, stderr), and **no arguments returns 0 with no
     output and stdin unread** (post-patch `:72-78`). That is criterion (a)'s "an
     instance whose `settings.json` still carries the old registration cannot deadlock".
   - Docstring (`:1-26`) rewritten: the script is the session's CLI (`--check`,
     `--abandon`), and the no-argument path exists only so a leftover registration is
     harmless. It explains why (Stop fires every turn end; exit 2 feeds the model).
   - The `--abandon` success message (`:98-99`) said "the session may now end", which
     only made sense under the block. It now says the driver reports the reason when the
     session ends. Exit codes and what gets recorded are unchanged (criterion d).
3. **Reap report**: `template/src/pdca_harness/handoff.py`.
   - `session()`'s `finally` (`:306-311`) used to report only an abandon reason. It now
     calls the new `report_at_reap(cfg, role, state)` (post-patch `:324-352`) inside a
     nested `try/finally`, so the scratch file is still removed whatever the report does
     (post-patch `:314-321`).
   - `report_at_reap` prints the abandon reason if one was recorded (same text as
     `:309-310`), else each `stop_problems()` item under a header naming the role (items
     are already `issue_<id>:`-prefixed by `stop_problems`, `:390`), else nothing.
   - Any exception inside the check becomes one stderr line (whitespace collapsed so a
     multi-line message stays one line) and nothing is raised. That is the `:273` rule,
     criterion (c).
   - The state handed to `stop_problems` is the scratch file merged under the driver's
     **in-memory** registration (`registered`, post-patch `:294-299`). The session can
     write that file (it lives in the project root and the leaf has Write), so if the
     report read the file alone, a leaf that rewrote or deleted it would change which
     bundles get named. `passed` / `abandoned` still come from the file, because the
     session legitimately writes those (`record_pass` `:247-254`, `record_abandon`
     `:257-261`). Cost: the `registered` dict (6 lines) plus the merge expression. The
     old `json.dump` literal (`:290-296`) now dumps `{**registered, "passed": []}`, so
     the file content is unchanged. Test:
     `test_the_report_names_the_bundles_the_driver_registered`.
   - Docstrings describing a Stop hook: module `:13-15`, `record_abandon` `:258-260`,
     `session` `:267-274`, the section comment `:315`, `stop_problems` `:366-373`. The
     name `stop_problems` is kept (Scope: renaming is out of scope); its docstring says
     the name is historical.
   - `:301` "the exit contract is unenforced" → "unchecked", since nothing enforces it
     anymore.
4. **Text that promised Stop-hook enforcement** now says `/handoff` is the self-check and
   the driver reports an unmet contract at session end:
   - `leaves.py`: `_plan_prompt` `:1035`, `_plan_batch_prompt` `:1293-1294` and `:1310`,
     the `run_signoff` comment `:3414-3415`, `_signoff_prompt` `:3437-3438`, the
     `run_publish` comment `:3628-3629`. All of these are named in the brief.
   - **Also** `run_signoff_batch` comment `:3464-3465`, `_signoff_batch_prompt`
     `:3492-3494` and `_publish_prompt` `:3693-3694`. The brief's list missed these,
     probably because "the Stop" / "hook" wrap across a line there, so a single-line grep
     for "Stop hook" never matches them. They fall under the Scope's own category ("the
     text that promises Stop-hook enforcement to the model") and are outside the three
     functions the Ordering note reserves for #480. Leaving them would keep telling the
     sign-off-batch and publish models that a Stop hook blocks them.
     `_signoff_batch_prompt` also referred to "the --abandon escape hatch it names" (the
     Stop hook's message); it now spells out the command.
   - Not touched: `do_plan` (`:904-929`), `do_plan_batch` (`:1055-1135`),
     `run_plan_advisory_batch` (`:3354-3403`), including the stale comments at
     `:916-917` and `:1104-1108`, as the Ordering note requires. Hunk ranges were checked
     against the function ranges on `main`.
   - `template/.claude/commands/handoff.md.jinja:17-19` and
     `docs/01-render-and-integrate.md:177-182`. The doc paragraph ends with one short
     line ("prompt lives in a canonical,") so the following, unrelated lines don't need
     reflowing.
5. **Tests**: `template/tests/test_handoff.py:133-141`
   (`test_stop_hook_ships_and_is_registered`) is inverted to
   `test_hook_ships_and_is_not_registered_on_stop`, and the module docstring item (b)
   (`:10-11`) is rewritten. The `StopVerdict` tests (`:331-362`) are unchanged and pass.
   New: `template/tests/test_handoff_reap.py` (also copied into the bundle).

## The test: `template/tests/test_handoff_reap.py` (17 tests, 4 classes = criteria a-d)

- (a) `NoTurnEndIsIntercepted`:
  - The settings file registers nothing on `Stop` or `SubagentStop`. SubagentStop is
    included because it is the other turn-end event, which is what the Invariant is
    about.
  - The hook, loaded in-process the way `test_handoff.py:143-147` does, with `_bootstrap`
    pointed at the test's `Config` (the brief's sanctioned approach), gets argv
    `["handoff_guard.py"]` and a Stop envelope on stdin (both `stop_hook_active` values)
    inside a real `handoff.session` with no `signoff-decision`. It must return 0 with
    empty stderr and stdout.
  - **Trap guard:** before the Stop call, the same patched hook runs `--check issue_7` in
    the same environment and must return 1 with `FAIL` + `signoff-decision`. That proves
    its contract check is live, so the pre-fix red can't come from the "contract check
    unavailable" branch (`handoff_guard.py:59-62`).
  - A second test does the same as a **real subprocess**:
    `python3 <hook>` with `CLAUDE_PROJECT_DIR` set to a temp root holding a minimal
    `pdca.toml` that makes sign-off interactive, `PYTHONPATH` pointing at the template's
    `src`, and `PDCA_*` / `CLAUDE_*` scrubbed from the inherited environment. It has the
    same `--check` liveness step first and no mocks at all.
- (b) `ReportedAtReap`: signoff with no decision, `iterate-do` with no rationale, a
  planner brief with an empty Success criterion, publisher with no artifacts, act with
  no named entry, a two-bundle batch where only the undischarged bundle is named, the
  driver-registration test above, a discharged contract printing nothing, and an abandon
  reason replacing the list. All go through the real `handoff.session(...)` with
  `redirect_stderr`, as `test_handoff.py:323-328` does.
- (c) `ReportOnly`:
  - Every file under the temp project root (bundles, process dir, pdca.toml) is snapshot
    as bytes before and after a reap for each of the four roles; the snapshots must be
    equal.
  - A **real** failure inside the check: the brief names a dependency and `pdca.toml` has
    `doctor = 1`, so `Config.current_doctor_checks` (`config.py:547-551`) raises
    `AttributeError`. The test first asserts `check_planner` really raises. Then the
    session must exit without raising, with exactly one stderr line, and the scratch file
    must be gone.
  - A leaf's own exception passes through the context manager as the same object.
- (d) `SelfCheckAndAbandonUnchanged`: `--check` gives 1 → 0 after the decision is written,
  and 2 with no id. `--abandon ""` gives 2, `--abandon "<why>"` gives 0, and the reap
  reports the reason.

## Evidence

- **Baseline** (`main`, nothing changed): the instance T3 runner
  (`engine/scripts/run-suite.sh`) reported root suite OK (24 tests) and driver suite OK
  (1788 tests, 2 skipped).
- **Pre-fix red** (`main` + only the new test file): 16 of 17 fail. Each fails for the
  intended reason: the hook returns 2 with "This signoff leaf session may not end yet"
  (in-process and subprocess), settings registers the Stop hook, and the reap prints
  nothing. The one that passes pre-fix is the exception pass-through guard, which is
  correct.
- **C4-shaped red leg** (every production hunk reverted, tests kept; the `.claude/` files
  were already at `main`): `test_handoff_reap` + `test_handoff` ran 52 tests, 17 failed,
  no `_FailedTest` (the module loads on the red leg; only pre-existing API is imported at
  module level).
- **Green**:
  - Worktree (all changes except the three `.claude/` files): 47/52 pass. The 5 failures
    are exactly the tests that read those files.
  - The same 52 tests with the modules' `HOOK` / `SETTINGS` constants pointed at the
    `.cache/534` copies (the exact post-patch content): 52/52 OK. This is a sanity pass
    of the unmodified test code against the new file contents, not a substitute for C4.
  - Full offline suite on the worktree: 1805 tests (1788 + 17 new), same 2 skips, 5
    failures (the same five).
- **Docs** (the two T2 checkers, run directly with the render output inside the
  worktree): `lint_docs: OK`, `render_site: link audit OK`.
- **Commit-readiness**: the target has no formatter, linter or pre-commit config
  (`CONTRIBUTING.md`, `.github/workflows/*`: docs lint + render only). All changed Python
  compiles. `pyflakes` isn't installed, so unused imports were checked by hand (the hook's
  `json` import was removed with `_stop_verdict`). The only commit hook-like requirement
  is DCO sign-off (`git commit -s`), which publish applies.

## Refuting my own test

- **(a) Genuine red?** Yes. With every production hunk reverted, 17 of 52 tests fail and
  the module still loads. On pure `main` plus the new test, 16 of 17 fail, with the
  pre-fix hook's own blocking message in the failure output.
- **(b) Production path?** Yes. The tests drive the real `handoff.session` context
  manager that `leaves.py` wraps around every contract leaf (`:918`, `:1110`, `:3416`,
  `:3466`, `:3562`, `:3630`), the real `stop_problems` / `check_*` functions, and the
  real hook file. The only stand-in is the in-process test's `_bootstrap` patch, which
  points the config lookup at the test's `Config` as the brief directs; the subprocess
  test has none. Caveat: for the 5 `.claude/`-reading tests, the green leg in Do ran
  against copies of the post-patch files (permission refusal above). C4 closes that.
- **(c) Fixture includes the fault?** Yes. The registered session's contract is
  undischarged (no `signoff-decision`), and that is proven by the hook's own `--check`
  returning FAIL in the same environment before the Stop call. The Stop envelope is
  sent with `stop_hook_active` both false and true. The check-failure fixture is a real
  broken config read, proven to raise before the reap runs.

## Alternatives ruled out

- **Keep the Stop hook but block only once (`stop_hook_active`) or answer in JSON.** Any
  exit 2 or `"decision": "block"` on Stop still turns a turn end into text for the model.
  That breaks the Invariant, and the maintainer already chose shape 3.
- **Make the no-argument call a usage error.** A stale registration would then exit 2
  (fed to the model, the same defect) or 1 (a hook error shown to the user on every
  turn). Inert exit 0 is the only safe answer to criterion (a).
- **Drain stdin on the no-argument path.** A stdin that never closes would stall every
  turn end until Claude Code's hook timeout. The Stop envelope is a few hundred bytes,
  well under a pipe buffer, so leaving it unread causes no write error for the caller.
  `subprocess.run(input=...)` in the test covers the case.
- **Report from each `leaves.py` callsite instead of inside `session()`.** That means 6
  callsites, two of them in `do_plan` / `do_plan_batch`, which this bundle may not touch.
  `session()` is the single reap point for all four roles, so one change covers them all.
- **Skip the report when the leaf raised.** The contract is just as unmet, and the leaf's
  exception still propagates unchanged (tested). Reporting on every exit also matches how
  the abandon reason was already reported at `:306-311`.
- **Silence the reap output in pre-existing tests.** Two `test_handoff.py` session tests
  and one `do_plan_batch` test now print a report during the suite. It's harmless stderr,
  and quieting it would add unrelated test edits.

## Housekeeping

- Working files are left in the worktree's gitignored `.cache/534/` for the harness to
  reclaim: the three `.claude/` copies, `prod.diff` (used for the red leg), suite logs,
  and the docs render.
- One slip: the baseline suite log was written to `/tmp/issue534-baseline-suite.log`,
  outside the harness roots. I left it for the harness rather than deleting it.
- No push, no PR.
