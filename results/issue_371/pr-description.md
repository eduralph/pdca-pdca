## Summary
**User impact:** one unlucky failure of a test or check command, for example a test
runner that crashed once on a busy machine, was enough to mark a change as broken.
The round lost its verdict and the change went to a person for review, even when every
run before and after it passed. In the downstream case behind this issue, six earlier
rounds, a run seconds later, the reviewer's own run and a manual re-run were all green.

This PR re-runs a failed blocking check once at Check. If the second run passes, the
check counts as passed but is flagged as flaky, and a person still has to look at it
before the change can be accepted. Both runs are kept.

Reported in [#371](https://github.com/eduralph/pdca-harness/issues/371).

**Merge order:** this stacks on #598 (#409). The `assemble.py` hunk sits next to code that
#598 adds, so it does not apply to `main` alone. Please merge #598 first.

## What to look at
- **The rule.** A blocking check that fails with a real exit code is run a second time
  with the same command, environment and timeout. Fail then pass: recorded as a pass,
  marked flaky, and listed for the human to acknowledge. Fail then fail: recorded as a
  fail. Second run times out or can't run: the first failure stands.
- **Where it applies.** Only at Check. The check run right before a push, and the
  re-checks between integration waves and on the working tree, still run a failing
  command once. A second lucky run can never let a push through.
- **Switches.** On by default. Off for a whole project with
  `[gates] confirm_gating_fail = false`, or for one check with `confirm_fail = false`.
  The docs advise turning it off for checks backed by a model, where a second run is a
  new opinion rather than a re-check.
- **Evidence.** The check's log file holds both runs, each in its own block.

To try it: declare a gating check whose command fails on its first run and passes on its
second, for example one that creates a marker file and exits 1 when the file did not
exist yet. Run Check. Before this PR the row records `fail` and the bundle is parked.
After it, the row records `pass`, `flaky = true`, `attempts = ["fail", "pass"]`, and
SUMMARY §6 has one open item naming both outcomes. The tests in
`template/tests/test_gate_confirm.py` drive exactly this with real shell commands.

## Root cause
`gates._run_one` ran each gate command exactly once and recorded that single result as
the row's verdict. The harness already records "the check gave no answer" as
`unverifiable` rather than `fail` (#46, #368), but a red contradicted by an immediate
green had no such handling.

## Fix
- `template/src/pdca_harness/gates.py`
  - `_run_one` (`:505`) takes a new `confirm` keyword, default off. When it is set, the
    row is gating, the first run is a `fail` with a real exit code, and both switches are
    on (`_confirm_enabled`, `:676`), it runs the command once more.
  - A single run is now `_attempt` (`:637`), split out of `_run_one` with the same
    behaviour. `_combine_attempts` (`:686`) applies the combine rule.
  - The row gets `attempts` and `flaky` only when a second run happened, so every other
    row is unchanged.
  - Only `run_gates` (`:198`) and `run_gates_dry` (`:277`) pass `confirm=True`, through
    `_run_checks` (`:342`) to both the `[[gates.checks]]` rows and the `host_ci` rows.
    `run_working_tree`, `run_integration` and publish's host-CI gate
    (`publish.py:930`, not touched) keep the default.
  - `_write_gate_log` (`:706`) writes one block per run when there are two. The
    top-level `# outcome:` header shows the recorded result. Single-run logs are
    byte-identical to before.
- `template/src/pdca_harness/config.py`: new `gates_confirm_gating_fail` (`:280`, parsed
  at `:584-588`). Absent means on. A value that is not a boolean turns it off and prints a
  warning. `confirm_fail` on a `host_ci` entry already survives `_normalize_host_ci`; only
  its docstring changes.
- `template/src/pdca_harness/assemble.py`: `_flaky_items` (`:574`) turns each flaky row into
  one HUMAN §6 item, wired into `collect_needs_human` at `:341`. It is HUMAN whatever the
  check's tier, because a rebuild cannot fix an unreliable environment. It is not marked
  `no_verdict`, because both runs are real verdicts, so auto-iterate can defer it (#409).
  `overall` needs no change: `_finalize` only counts gating `fail` rows.
- Docs: `docs/05-check.md:451-465` and the `[gates]` comment in
  `template/pdca.toml.jinja:1005-1018`, which includes an upgrade note for model-backed
  rows.

## Verification
Line numbers are on this branch (on top of #598).

- **Claim:** fail then pass records `pass` + `flaky`, `attempts = ["fail", "pass"]`, after
  exactly two runs.
  **Checked:** `gates.py:505-620`, `:686-703`.
  **Test:** `CombinationRule.test_fail_then_pass_records_pass_flaky_after_two_runs`
  (`template/tests/test_gate_confirm.py:109`).
- **Claim:** fail then fail records `fail` with the second run's evidence. A second run
  that times out, is unverifiable, is deferred or raises leaves the first `fail` and its
  evidence.
  **Checked:** `gates.py:686-703`.
  **Test:** `CombinationRule`, `:117-156`.
- **Claim:** at most one extra run. Passing, non-gating, misconfigured-delegation and
  raised-before-exit rows run once. Both switches turn it off, on `[[gates.checks]]` and
  on `host_ci` entries.
  **Checked:** `gates.py:586-598`, `:676-683`; `config.py:584-588`.
  **Test:** `Bounds`, `:186-295`.
- **Claim:** only Check confirms. Publish refuses the push after one failed run.
  **Checked:** `gates.py:198`, `:277`; `publish.py:930` unchanged.
  **Test:** `PublishHostCiRunsOnce` (`:323-425`) runs the real `publish.publish`
  against a throwaway git origin with a fail-then-pass host-CI command. It asserts one
  run, exit 1, nothing pushed and the row recorded `fail`. A control test runs the same
  row through `run_gates` and gets the confirmed pass. `CheckTimeOnly` (`:297-320`)
  covers the working-tree and integration re-gates. Adding `confirm=True` at
  `publish.py:930` or to either re-gate turns these tests red; this was checked by making
  that change and running them.
- **Claim:** the log keeps both runs; single-run logs are unchanged.
  **Checked:** `gates.py:706-766`.
  **Test:** `Evidence`, `:430-455`. The existing `tests/test_gate_logs.py` still passes.
- **Claim:** a flaky row is one HUMAN item naming both outcomes, and `overall` counts it
  as a pass.
  **Checked:** `assemble.py:341`, `:574-598`; `gates.py:925`.
  **Test:** `Routing`, `:456-488`.
- **Red/green:** with the production changes reverted, 19 of the 27 tests in
  `test_gate_confirm.py` fail or error. With them applied, all 27 pass. The full offline
  suite passes (2162 driver tests), and so do the docs lint and render checks.

Run: `cd template && PYTHONPATH=src python3 -m unittest tests.test_gate_confirm`

## Not in this PR
- The docs advise `confirm_fail = false` only for model-backed checks. A check that
  changes shared state and doesn't clean up after a failure would also start its second
  run from a different state. A fail then pass there still goes to a human, so nothing
  slips through, but the docs could say so.
- A comment in `size_signal.py:166-168` says the flaky recorder "has not landed". It will
  be out of date once this merges. It is left alone here to keep this PR to one change.

Fixes #371
