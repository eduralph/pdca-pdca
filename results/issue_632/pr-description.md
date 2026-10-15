## Summary
**User impact:** when `pdca flow` publishes a fix and opening the draft PR crashes
after the branch has already been pushed (most often because the GitHub CLI `gh` is
not installed), the run acts as if nothing was pushed. That fix is left out of the
integration branch, every fix that depends on it is held back for the run, and the
operator only sees a generic "publish failed", with no hint that the branch is
already on origin and only the PR is missing.

This PR makes that crash behave like an ordinary "could not open the PR" failure.
The pushed branch is recorded and folded in, and the message says the branch is on
origin, that no PR was opened, and how to finish.

Reported in [#632](https://github.com/eduralph/pdca-harness/issues/632).

## What to look at
- The one change is in `publish.py`, around the `gh pr create` call: it now catches
  an exception there and handles it like the existing "gh returned an error" case.
- The operator message for that case is reworded (it now names the branch and the
  `pdca publish <id>` command). It applies to both the error and the crash.
- To try it: run the new test file, or set up a bundle as
  `test_open_pr_failure_exits_nonzero` does, but make the `gh pr create` stub raise
  `FileNotFoundError` instead of returning 1. Before this change the flow reports
  the bundle as unpushed; after it, the branch is recorded and folded.

## Root cause
`flow._publish_bundle` decides "this call pushed the branch" from whether
`publish.json` was freshly written, and `publish.publish` writes that record only
after `gh pr create` returns. If that call raised, the exception skipped the record
write, so a branch that was already on origin looked unpushed.

## Fix
In `publish.publish`, the `gh pr create` call is wrapped in `try/except Exception`.
An exception becomes a synthetic rc-1 result carrying `"<ExcType>: <msg>"`, and from
there the existing rc-1 path runs unchanged: the error is printed, the record is
written with an empty `pr_url`, and publish returns 1. `flow.py` is not changed: it
already folds an rc-1 publish that wrote a fresh record, and still prints "publish
did not complete", so the operator knows a step is left. `KeyboardInterrupt` and
`SystemExit` are not `Exception` subclasses, so Ctrl-C still stops the run.

Out of scope: the stacked-PR path (`_publish_stacked`), where the push is already
the last step that can fail, so there is nothing after it to catch.

## Verification
- **Claim:** once the push succeeds, a `gh pr create` that raises still leaves the
  branch on record and counted as pushed this run.
  **Checked:** `template/src/pdca_harness/publish.py:404-414` and `:431` on `main`.
  The raise skipped the rc-1 handling and the record write. `flow.py:642-665`
  reads that record to decide "pushed".
- **Claim:** the fold and the flow agree on the branch.
  **Checked:** `integrate.py:139-182`. `_published_ref` / `unpublished` read the
  branch from the same `publish.json`, which is now written.
- **Claim:** this matches the flow's own stated rule.
  **Checked:** `flow.py:2282-2283` ("A branch pushed this run is folded even if
  `gh pr create` failed after it"), and the rc-1 case already pinned by
  `test_publish_slice.py:359-381`.
- **Claim:** a failure *before* the push is unchanged and still counts as unpushed.
  **Checked:** covered by two new tests (failed `git push`, raising `git apply`).
  `test_publish_slice.py` still passes.
- **Test:** `template/tests/test_flow_publish_raise_after_push.py`. The two
  raise-after-push cases (`FileNotFoundError` and `RuntimeError`) fail without the
  fix ("push succeeded but _publish_bundle returned False") and pass with it. The
  tests first check that the push and the `gh pr create` call both really ran, so
  the failure is caused by this bug and not by a dry run. Full offline suite: 2373
  tests OK (2 skipped).

Fixes #632
