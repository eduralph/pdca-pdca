# Build notes — issue 371 / gate-confirm-failed-gating-row (iteration 2)

Target: eduralph/pdca-harness, built in `$PDCA_WORKTREE` on `00dc958` ("pdca-integrate:
issue_409", stack-base `pdca-integration/main`), i.e. on 409's folded result as the brief's
ordering note asks. Line numbers below are on that tree with this patch applied.

## What this iteration changed (the carry-forward)

Sign-off accepted the implementation and rejected one test: `test_publish_host_ci_rows_run_once`
hand-copied publish's `_run_one(...)` call, so adding `confirm=True` at
`template/src/pdca_harness/publish.py:930` would have left it green.

1. **Removed** that test. **Added** `PublishHostCiRunsOnce`
   (`template/tests/test_gate_confirm.py:323-425`), which drives the real publish path with
   nothing mocked: `publish.publish(cfg, "RG", open_pr=False, …)` → `publish._host_ci_passes`
   (`publish.py:880`) → real `_pinned_base` (git fetch + pin) → real `worktree.for_publish`
   → `gates._run_one` at `publish.py:930`. The fixture is a toy bare origin + clone, the same
   shape as `tests/test_host_ci.py` `HostCiPatchedTree` (`test_host_ci.py:338-373`), and the
   config mirrors `test_host_ci.py:_cfg` (`:48-70`). The declared host-CI row is the
   fail→pass marker-file command, normalized by the real `_normalize_host_ci`
   (`config.py:874`).
   - `test_fail_then_pass_command_refuses_the_push_after_one_run` (`:392`): precondition
     that the row is one Check WOULD confirm (gating, project switch on, no `confirm_fail`).
     Then it asserts: the command ran exactly once, `publish` returned 1, origin has only
     `refs/heads/main` (nothing pushed), no `publish.json`, and `host-ci.json` records the
     row `fail` with the first run's evidence and no `flaky`/`attempts`.
   - `test_control_the_same_row_is_confirmed_at_check` (`:416`): same fixture and command
     through `gates.run_gates` (the lane tree). It IS confirmed: two runs, `pass` + `flaky`,
     `attempts == ["fail", "pass"]`. This shows the publish test passes because publish
     doesn't confirm, not because the row or the command can't be confirmed.
   - `test_run_one_without_the_switch_runs_once` (`:298`) stays, now commented as what it
     is: the `_run_one` default. It no longer claims to stand in for publish.
2. **Optional clean-ups the sign-off listed**, both done:
   - `_write_gate_log` (`gates.py:706-766`) now takes `attempts` alone (always a list) and
     derives the single-run case from `attempts[0]` (`:732-739`). The `started` / `rc` /
     `output` parameters are gone, so nothing is passed and then ignored. The caller is
     `gates.py:618-621`. Single-run logs are byte-identical to before: same header lines, same
     order, `start` = the one run's start, `duration` = that run's rounded duration.
     `tests/test_gate_logs.py` still passes in T3.
   - `_flaky_items` (`assemble.py:574-598`) reads `attempts[0]` / `attempts[-1]` from the
     list instead of joining and re-splitting on `' → '`. It also drops the
     `or ["fail", "pass"]` fallback: a `flaky` row without `attempts` now says
     "attempts not recorded" instead of inventing a history (`:587-592`). The normal-case §6
     text is unchanged.
3. Tests for the clean-ups: `test_flaky_row_without_attempts_invents_no_history` (`:470`,
   new), and `test_flaky_row_is_one_human_section6_item` (`:457`) now asserts the exact phrase
   `first run fail, confirm re-run pass` instead of the loose `"fail" in` / `"pass" in`.

Everything else is the iteration-1 patch, unchanged.

## The whole patch (for reference)

**`template/src/pdca_harness/gates.py`**
- `_run_one` (`:505-508`) gets the keyword `confirm: bool = False`. After the first run, it
  runs the command once more (`:586-598`) only if all of these hold: `confirm` is set, the
  row is gating, the first run classified `fail` with a real exit code (`rc is not None`),
  and `_confirm_enabled(chk, cfg)` is true. The `cmd_error` early return (`:515-522`) is
  unchanged, so a misconfigured delegation is never confirmed.
- One run = `_attempt` (`:637-667`), moved out of `_run_one` with the same behaviour: same
  heartbeat call, timeout → `unverifiable`, `_classify`, exception → `fail` with the
  exception as output.
- `_attempt_outcome` (`:670`): the per-sample label; `rc is None` → `"error"`.
- `_confirm_enabled` (`:676`): `cfg.gates_confirm_gating_fail is True and
  chk.get("confirm_fail", True) is True`. A malformed value falls back to one run (today's
  behaviour).
- `_combine_attempts` (`:686`): one sample → itself; fail→pass → `pass` + flaky with the
  confirm run's evidence; fail→fail → `fail` with the confirm run's evidence; anything else
  → the first `fail` with the first run's evidence.
- `attempts` / `flaky` row keys are added only when a confirm ran (`:606-612`), so every
  other row is unchanged (keeps `test_gate_logs`' "no new keys" contract).
- Two-run log: top-level `# outcome: <combined>`, `# flaky:`, `# attempts:`, then one
  `# ==== attempt N of 2 ====` block per run with its own `# start:`, `# duration_secs:`,
  `# exit:`, `# outcome:` and verbatim output (`:740-760`). `_exit_line` (`:769`) is shared
  by both formats. Still one file per row.
- Callers: `_run_checks` gets `confirm=False` (`:344`) and passes it to the
  `[[gates.checks]]` loop (`:407`) and the host-CI loop (`:435`). Only `run_gates` (`:198`)
  and `run_gates_dry` (`:277`) pass `confirm=True`. `run_working_tree` (`:231`),
  `run_integration` (`:261`) and publish (`publish.py:930`, not touched) keep the default.

**`template/src/pdca_harness/config.py`**: field `gates_confirm_gating_fail: bool = True`
(`:275-280`, beside `gates_default_timeout_secs`). Parsed at `:582-588`: absent ⇒ True; a
non-boolean ⇒ False with a stderr line, the same pattern as `dependency_halt`. Passed to the
constructor at `:839`. `_normalize_host_ci` already copies every key of a table entry, so
`confirm_fail` survives it with no code change; only its docstring says so now (`:882-883`).

**`template/src/pdca_harness/assemble.py`**: `_flaky_items` (`:574`) next to
`_unverifiable_items`, wired into `collect_needs_human` at `:341` as
`NeedsHumanItem(t, HUMAN)`. It is HUMAN whatever the element (a C4 row would be IMPL in
`_failed_gating_items`). `no_verdict` is left at False on purpose: both samples are real
verdicts on this round's tree, and the issue's promise is that auto-iterate *defers* the
item (#409), which `no_verdict=True` would block. `overall` needs no change: `_finalize`
(`gates.py:925`) counts only gating `fail`, and the row records `pass`.

**Docs**: `template/pdca.toml.jinja:1005-1018` (comment block before `[gates]`, including
the upgrade note for model-backed rows) and `docs/05-check.md:451-465`.

Not touched (out of scope per the brief): `size_signal.py`, `publish.py`, auto-iterate.

## Runs (the instance's own gate scripts, with `PDCA_BUNDLE` / `PDCA_WORKTREE` set)

- **C4** `engine/scripts/run-verify.sh`: green leg `Ran 27 tests … OK`; red leg (production
  hunks reverted) `Ran 27 tests … FAILED (failures=11, errors=8)`; verdict
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. No load failure.
- **T3** `engine/scripts/run-suite.sh`: root suite 24 OK; driver suite 2162 OK (2 skipped).
- **T2** `run-docs-check.sh`: lint OK, render + link audit OK. **host-ci-docs**
  `run-host-ci.sh` on the patched tree: OK. **C5** `run-prod-path.py`: 1 added driver-suite
  test imports `pdca_harness`.
- **Formatter / hooks**: the target has no pre-commit config, no `core.hooksPath`, no
  ruff/black/flake8 config, and no lint step in its workflows (`docs-check`, `docs`,
  `render-check`, `require-linked-issue`). CONTRIBUTING only asks for a DCO `Signed-off-by`
  trailer, which belongs in the commit message at publish. I ran `git diff --check` (clean)
  and `py_compile` on every touched `.py` (OK). No added line is wider than 100 columns; the
  touched files already have lines up to 106.

## Refute-your-own-test

- **(a) Genuine red?** Yes, at two levels.
  - Whole file: the C4 red leg reverts the production hunks and 19 of 27 tests fail or
    error. The core failures are `AssertionError: 1 != 2` (one run, not two), no
    per-attempt log block, and `'fail' != 'pass'` for `overall`. Errors are
    `_run_checks() got an unexpected keyword argument 'confirm'` and `'Config' object has
    no attribute 'gates_confirm_gating_fail'`. No import failure, so it doesn't read as
    UNVERIFIABLE.
  - Clause-4b guards, by mutation (the gap the sign-off found). With `confirm=True` added at
    `publish.py:930`, the C4 green leg failed:
    `FAIL: test_fail_then_pass_command_refuses_the_push_after_one_run … AssertionError: 2 != 1 : publish's host-CI gate re-ran a failing command`
    → `C4 FAIL — bundle test red WITH the fix applied`. With `confirm=True` added to the
    `_run_checks` calls in `run_working_tree` (`gates.py:231`) and `run_integration`
    (`:261`), both `test_working_tree_regate_runs_once` and
    `test_integration_regate_runs_once` failed with `2 != 1`. I reverted both mutations
    and checked that the worktree diff equals `patch.diff` byte for byte.
- **(b) Production path?** Yes. The publish test calls `publish.publish` itself. Fetch, pin,
  ephemeral tree, `_run_one` and the `host-ci.json` refusal record are all production code.
  Nothing is patched in that class. The other tests call `gates.run_gates`,
  `run_gates_dry`, `run_working_tree`, `run_integration`, `_run_checks`, `_run_one`,
  `Config.load` and `assemble.collect_needs_human`. The commands are real subprocesses
  through `progress.run_with_heartbeat`. Only the two "raised before an exit code" tests
  wrap `run_with_heartbeat` to raise on a chosen call, because a shell command can't make
  the subprocess layer raise. The real function runs on the other calls.
- **(c) Fixture includes the fault?** Yes. The fault is a gating command that fails once and
  then passes. The marker-file command really does that (the control test shows it
  confirm-passes on the same fixture). The publish fixture is a real git origin, so the
  refusal and "nothing pushed" are real. The timeout case really sleeps past a real
  `timeout_secs = 1`.

## Alternatives ruled out

- **Static check that `publish.py:930` passes no `confirm`** (the sign-off's minimum):
  rejected as the only guard. It reads source text, so it binds the spelling, not the
  behaviour: a wrapper or `**kwargs` would get past it. The real-publish test costs about
  60 lines of fixture (`:330-390`), adds about 0.2 s, and binds the behaviour itself.
- **Publish with `_pinned_base` / `for_publish` mocked** (the `HostCiPublishGate` style,
  `test_host_ci.py:165-186`): it would still exercise `publish.py:930`. But the real-git
  fixture is barely longer (one bare init, one clone, one commit, one push) and also proves
  nothing reached origin.
- From iteration 1, still valid: confirming in `_run_checks` instead of `_run_one` (would
  duplicate the ~40 lines of row and log building, and both runs couldn't share one log
  without passing raw outputs out); always emitting `attempts` (changes every row and
  breaks `test_gate_logs`' "no new keys" contract); `no_verdict=True` on the flaky item
  (blocks #409 deferral).

## Left alone, worth a follow-up

- Review finding 4 (advisory): the docs advise `confirm_fail = false` only for
  model-backed rows. A gate that changes shared state and doesn't clean up after a failure
  would also start its second run from a different tree. A fail→pass still lands in §6 as
  HUMAN, so nothing slips through silently. I didn't add the doc sentence because sign-off
  said to keep the rest of the patch as is.
- `size_signal.py:166-168` still says "the recorder has not landed". That's stale once this
  merges, but the brief rules out any change to `size_signal.py`.

## Housekeeping

- For the re-gate mutation check, I copied `gates.py` to `gates.py.premutation` inside the
  worktree and then moved it back over the mutated file. No stray file is left;
  `git status` shows only the patch's six paths.
- To generate `patch.diff` I marked the new test intent-to-add (`git add -N`) and later
  unstaged it (`git reset -- <file>`). The worktree index matches HEAD again, and the new
  test is a plain untracked file, as after `git apply`.
- The docs gates render into `mktemp` dirs under `/tmp`, and the tests use
  `tempfile.mkdtemp` with `addCleanup`. Both come from the project's own scripts and tests.
  I wrote nothing outside the worktree and the bundle.
