# PR description

## Summary
**User impact:** Declaring an external dependency in a brief — and registering a
detect command for it, as required — gives no real protection today. On a machine
that doesn't have the tool, planning still completes and the build is still
dispatched: nothing ever runs the detect command, so the gap surfaces late as a
confusing build failure — or not at all, when the build quietly works around the
missing tool and the result looks verified without being so.

This PR makes the dependency guard actually execute the detect commands for
exactly the dependencies a brief declares, and hold the bundle — quoting the
row's own install hint — before a build is dispatched.

Reported in [#340](https://github.com/eduralph/pdca-harness/issues/340).

## What to look at
One new function in `template/src/pdca_harness/doctor.py` (the probe) and its
call from the existing guard in `template/src/pdca_harness/plan_policy.py`;
everything else is tests, docs and config comments. To try it: register a
`[[doctor.checks]]` row whose `cmd` is `false`, name its id as a backticked
token in a brief's `External dependencies`, and `pdca run` the bundle — it holds
before the build, quoting the row's hint. Flip the cmd to `true` (or install the
real tool) and the next run proceeds; no re-plan needed. Detect commands now run
on every policy evaluation, so they must stay cheap and side-effect-free — the
config comment and docs carry that expectation.

## Root cause
Since b0bc575f818ebb8f3050b8c91f25e6c335d21282 (#333) the guard reconciles brief
tokens against registered `[[doctor.checks]]` rows, but registration only
requires a non-empty `cmd` (`registered_ids`,
`template/src/pdca_harness/doctor.py:306` on `main`) and `plan_policy.py`
contains no subprocess call — the registered detect command is never executed.
A dependency could therefore be discharged by registration alone on a host
where it is absent, leaving the builder's own mid-build self-report as the sole
detector.

## Fix
- New `doctor.failing_dependencies` (`template/src/pdca_harness/doctor.py:356-400`)
  executes the detect `cmd` of exactly the rows the brief's backticked tokens
  name. Tokens come from `brief.external_dependency_tokens`
  (`template/src/pdca_harness/brief.py:250`), so `(no-check: …)` and plain-prose
  dependencies yield no token and are never probed; rows come from
  `Config.current_doctor_checks` (`template/src/pdca_harness/config.py:391`) —
  `pdca.toml` as it is on disk, so a row registered during the Plan beat counts
  in the same pass. Each cmd runs with the same subprocess shape doctor's own
  row runner uses (shell, project root, exit 0 ⇒ present). A registered row the
  brief does not name is never spawned, so an instance's wider doctor inventory
  is not a tax on every bundle.
- `plan_policy.dependency_reasons` appends the probe's reasons **after** the
  #333 registration reasons (`template/src/pdca_harness/plan_policy.py:209-212`;
  an unregistered token has no row to run, so it holds for that reason first),
  and `_BLOCKING` gains `failed-dependency` (`plan_policy.py:63`). Mode handling
  is untouched: `off` returns before any probe (byte-identical to today), and
  `warn` maps to `failed-dependency-warn`, which `blocking()` ignores, so the
  driver reports it and proceeds.
- Docs and config carry the new operational contract — named detect cmds run
  every beat the policy is consulted and must stay cheap and side-effect-free;
  provisioning stays with `[install].extra_bootstrap`
  (`template/pdca.toml.jinja:713-719`, `docs/03-plan.md:244-250`, matching
  comments in `config.py`).

## Verification
All cites are on this branch (base `main` @
`dfd0427e9149674fefacba5ca28c27e4404e3b28` plus this patch); the regression
tests are the new `DependencyProbe` class in the guard's existing test module.

- **Claim:** a brief-named registered row whose detect cmd exits non-zero holds
  the bundle before the build, quoting that row's own `hint`.
  **Checked:** `template/src/pdca_harness/doctor.py:356-400` (the probe reports
  each non-zero exit with the row's hint), `template/src/pdca_harness/plan_policy.py:63`
  (`failed-dependency` blocks).
  **Test:** `template/tests/test_dependency_guard.py:315` — hold raised, no
  `patch.diff` produced, state stays PLANNED; asserts `lanes = 1`, the path that
  previously had no preflight at all.
- **Claim:** a passing detect changes nothing — no reasons, build dispatches.
  **Test:** `template/tests/test_dependency_guard.py:334`.
- **Claim:** ONLY the rows the brief names are executed; exempt and prose
  dependencies are never probed.
  **Checked:** the `rid.lower() not in wanted` filter,
  `template/src/pdca_harness/doctor.py:396`.
  **Test:** `template/tests/test_dependency_guard.py:342` and `:366` — the
  unnamed/exempt row's cmd would both fail *and* create a marker file, so
  non-execution is observable: no hold AND no marker.
- **Claim:** the probe runs after the registration check — an unregistered token
  holds as `unregistered-dependency` first, and its reasons list first.
  **Test:** `template/tests/test_dependency_guard.py:354`.
- **Claim:** rows are read from disk, not the run's snapshot — a row added or
  edited during planning counts in the same pass.
  **Test:** `template/tests/test_dependency_guard.py:378`.
- **Claim:** the hold self-clears — fix the row or install the tool and the next
  attempt proceeds, no re-plan.
  **Test:** `template/tests/test_dependency_guard.py:387`.
- **Claim:** `off` is byte-identical (the detect cmd is not even spawned) and
  `warn` reports the failure without holding.
  **Test:** `template/tests/test_dependency_guard.py:399` (marker-proven) and
  `:406`.
- **Red→green:** with the production hunks reverted and the tests kept, the
  module fails (5 failures); with the patch, 27/27. Full offline driver suite:
  1,323 tests OK. Template render + `copier update` compatibility suite: 7 tests
  OK. Docs lint: OK.

Fixes #340
