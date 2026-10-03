## Summary
**User impact:** If one of the briefs in a `pdca flow` run says it depends on
work that isn't part of the run and isn't finished yet, or two briefs depend on
each other, the run stops before building anything — which is right — but the
user sees a Python traceback. A simple fix-your-input mistake (an outdated
"Depends on" line, or a prerequisite that was fixed some other way) looks like
the tool crashed.

This PR turns that crash into a short refusal: `pdca flow` says which bundle and
which dependency (or which cycle) is the problem, lists the ways out, and exits
with code 2. Nothing else about the run changes.

Reported in [#589](https://github.com/eduralph/pdca-harness/issues/589).

## What to look at
The change is a new, narrow error type for "the dependency graph can't be
scheduled", and one handler in the `flow` command that catches only that type.
Any other error still surfaces as before, so real bugs are not hidden.

To try it: create a bundle whose brief has `- **Depends on:** 773` with no
bundle 773 on disk, then run `pdca flow <that id>`. Before this PR you get a
traceback; with it you get:

```
flow: issue_A: declared dependency '773' is neither in this batch nor an existing COMPLETE bundle
  refusing to start — no bundle was built.
  Ways out: add 773 to this run's ids; or, if it landed outside the cycle, drop the edge from issue_A's brief; or finish 773 first.
```

and exit code 2. Two briefs that depend on each other give the same shape with
`dependency cycle: issue_A → issue_B → issue_A`.

## Root cause
`waves.check_dep_graph` correctly rejects an unresolved dependency or a cycle by
raising `ValueError`, but on the named-ids `flow` path nothing caught it:
`cli._flow_claimed` only caught `flow.PreflightError` around `flow.flow_ids`, and
`cli.main` only catches `worktree.WorktreeError`, so the exception escaped as a
traceback.

## Fix
- `template/src/pdca_harness/waves.py`: add `DependencyGraphError(ValueError)`
  with a `remedy` attribute. Both raise sites in `check_dep_graph` (unresolved
  dependency, cycle) now raise it, with the same message text as before and a
  remedy suited to each case (three ways out for a missing dependency, "drop one
  edge" for a cycle). Docstrings of `check_dep_graph` and `compute_waves` updated.
- `template/src/pdca_harness/cli.py`: in `_flow_claimed`, next to the existing
  `PreflightError` handler around `flow.flow_ids`, catch `waves.DependencyGraphError`,
  print the message, a "no bundle was built" line and the remedy to stderr, and
  return 2 — the same code as the bad-`pdca.toml` refusal. Claims are still
  released by the existing `with drive_claim.run(cfg)` scope in `_flow`.
- `docs/03-plan.md`: the "rejected up front" sentence now says what the operator
  sees (`pdca flow` exits 2 before building, naming the problem and the ways out).
- New test `template/tests/test_flow_dependency_refusal.py`.

Exit code 2 here vs. 1 for the preflight and claim refusals on the same path is
intended: this follows the config-error shape, and the existing codes are left
alone.

Not changed: when the graph is checked, the tolerant resume sweep and split
adoption (they already hold a bad-dependency bundle instead of refusing),
`pdca waves` output and exit code, and the zero-ids `--from-csv` path (which
cannot raise this error).

## Verification
- **Claim:** an unschedulable graph on `pdca flow <ids>` ends with rc 2, no
  traceback, the bundle/dependency (or cycle) on stderr plus the ways out, and no
  bundle built.
  - **Checked:** raise sites `template/src/pdca_harness/waves.py:78-80`
    (unresolved dependency) and `:93` (cycle) on `main` (`24c7f83`); the only
    caught type around the call was `PreflightError` at
    `template/src/pdca_harness/cli.py:654-660`; the strict call is
    `template/src/pdca_harness/flow.py:1694` (`waves.compute_waves`).
  - **Test:** `test_unresolved_dependency_single_id_refuses_rc2`,
    `test_unresolved_dependency_two_ids_refuses_rc2` and
    `test_dependency_cycle_refuses_rc2` in
    `template/tests/test_flow_dependency_refusal.py` drive `cli._flow` through the
    real `flow_ids` → `compute_waves` → `check_dep_graph` chain. They fail on
    `main` (the call raises `ValueError`) and pass with this change. They also
    check that no `patch.diff` was written, state stays PLANNED and
    `driver.run_issue` is never called.
- **Claim:** the new handling does not swallow other errors.
  - **Checked:** the handler names only `waves.DependencyGraphError`, mirroring
    the rc 2 config-error shape at `template/src/pdca_harness/cli.py:443-447`.
  - **Test:** `test_other_value_error_still_propagates` makes `flow.flow_ids`
    raise a plain `ValueError("something else")` and asserts it still escapes
    `cli._flow`. It passes before and after by design; it would fail if the fix
    caught all `ValueError`s.
- **Claim:** existing callers that expect `ValueError` are unaffected.
  - **Checked:** `DependencyGraphError` subclasses `ValueError`; `pdca waves`
    still catches `ValueError` and keeps its `unschedulable: …` line and rc 1.
  - **Test:** `tests.test_waves`, `tests.test_deps_completed`,
    `tests.test_flow_slice` plus the new file: 127 tests OK. Full suite
    (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`):
    2219 tests OK (2 skipped). Docs lint and site link check clean.

Fixes #589
