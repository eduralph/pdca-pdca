# Build notes — issue 632 / publish-raise-after-push-counts-as-pushed

Target: `eduralph/pdca-harness` @ `main` (`b5f5c29`), worktree `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l1`). Line numbers below are post-patch in that tree.

## The change (fix shape chosen at Plan)

`template/src/pdca_harness/publish.py:405-424`: the `gh pr create` call
(`subprocess.run(pr_cmd)`, was `publish.py:406` on main) is now wrapped in
`try/except Exception`. A raise becomes a synthetic
`subprocess.CompletedProcess(pr_cmd, 1, "", "<ExcType>: <msg>")`
(`publish.py:411-414`). It then goes down the existing rc-1 path: `pr_failed = True`,
the error goes to stderr, the record is written with an empty `pr_url`
(`publish.py:440`), and the call returns 1. A raise after the push now ends in the same
state as the rc-1 case that `test_publish_slice.py:359-381` already pins.

I also reworded the operator message (`publish.py:419-423`) for criterion (3). It now names
the branch and `origin`, says no draft PR was opened, and says how to finish: "Open the
draft PR by hand, or re-run `pdca publish <id>`. This is NOT done." The old text was
"branch pushed, but `gh pr create` FAILED — no draft PR was opened. Open it by hand, then
re-run if needed." That named neither the branch nor the command. Nothing in `tests/`,
`template/tests/` or `docs/` matched the old wording (checked with grep). The rc-1 path
gets the same, better message.

`flow.py` is unchanged, as the brief asks. `_publish_bundle` (`flow.py:642-665`) already
returns True when publish returns rc 1 after writing a fresh record. It also prints
"… is COMPLETE but publish did not complete (rc 1) — NOT published; run `pdca publish
<id>`" (`flow.py:661-663`). So the operator still sees that a step is left. Its docstring
("nor does a call that raised") stays true, because publish no longer raises here.

`except Exception`, not `except OSError`: the brief asks for any raise to be handled (a
`RuntimeError` case is tested). `KeyboardInterrupt` / `SystemExit` are not `Exception`
subclasses, so a ^C still stops the run. That matches `flow._isolate` (`flow.py:62`).

## Ruled out

- Changing `flow._publish_bundle` to detect the push itself (e.g. writing a marker before
  `gh pr create`). Rejected at Plan, and it would edit `flow.py`, which bundle 629 also
  touches. The publish-side catch restores the invariant at the one step that can fail
  between the push and the record write. The only code between them is the record build
  and `_normalize_tracker_refs`, which runs *before* the steps (`publish.py:329`).
- Writing `publish.json` before `gh pr create` and rewriting it after. That is two writes,
  and the mtime rule in flow would still work. But it changes when the record appears for
  every path, not just the failing one. It costs about +8 lines and a second
  `write_text`, against 6 lines for the catch. It also makes no difference to the
  invariant, so I kept the smaller change.
- `_publish_stacked`: out of scope per the brief (its push is its last step that can fail).

## Test

`template/tests/test_flow_publish_raise_after_push.py` (copy in the bundle):

- `test_gh_missing_after_push_counts_as_pushed` (`:146`): `gh pr create` raises
  `FileNotFoundError(2, …, "gh")`.
- `test_non_oserror_after_push_counts_as_pushed` (`:151`): it raises `RuntimeError`.
  Both go through `_assert_pushed_and_folded` (`:113`), which checks that exactly one
  `git push` was seen and that `gh pr create` ran. It then checks criteria (1), (2) and (3):
  `flow._publish_bundle(...) is True`; `integrate.unpublished([d], pushed={d.name}) == []`;
  `integrate._published_ref(d) == ("origin", "origin/fix/<id>-my-fix", False)`; stderr names
  the branch, `origin`, "no draft PR was opened", the exception type,
  `pdca publish <id>` and "did not complete"; stderr has no "Draft PR prepared".
- `test_push_failure_is_not_pushed` (`:156`) and `test_apply_raise_is_not_pushed` (`:173`)
  cover criterion (4): a failure before the push returns False, writes no `publish.json`,
  and leaves no branch on record.

Fixture, per the brief: the publisher is `LeafConfig(mode="command", interactive=True)`, so
`_publish_bundle` does not take the dry-run path. `commit-msg.txt` / `pr-description.md`
are pre-written and the call uses `texts_prevalidated=True`.
`publish.leaves.run_publish` is patched to raise if called, so no publisher leaf runs.
`publish._check_repo` is patched to 0 and `publish.subprocess.run` is stubbed. I copied
`_cfg` / `_bundle` / `_FIX_BRIEF` from `test_publish_slice.py:46-81` instead of importing
them. No test in the suite imports a sibling test module, and `from test_publish_slice
import …` failed with `ModuleNotFoundError` under `python -m unittest tests.<mod>`, which
is how the C4 script runs it.

## Red → green

- Pre-fix (test only): the two raise cases FAIL at `assertTrue(pushed, …)`. The asserts
  just before that one passed: exactly one push was seen, and `gh pr create` ran. Stderr
  shows `_isolate`'s "publish failed (FileNotFoundError …)". So the red comes from the
  defect (no record after a post-push raise), not from a dry-run. The two before-push
  cases pass pre-fix, as they should (criterion 4 is "unchanged").
- `engine/scripts/run-verify.sh` (the project's C4 gate, run with `PDCA_BUNDLE`,
  `PDCA_WORKTREE`, `PDCA_BRIEF_BASE=origin/main`):
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
- `engine/scripts/run-suite.sh` (T3): root suite 24 tests OK; driver suite 2373 tests OK
  (2 skipped). `PDCA-EVIDENCE: root suite OK, driver suite OK`.

## Self-refutation

- **(a) Genuine red?** Yes. With only the `publish.py` hunk reverted (my own run before
  writing the fix, and again in the C4 script's red leg), 2 of 4 tests fail with
  "push succeeded but _publish_bundle returned False".
- **(b) Production path?** Yes. The test calls the real `flow._publish_bundle`, which
  calls the real `publish.publish` new-PR path, and the real
  `integrate.unpublished` / `integrate._published_ref`. Only the outside world is stubbed:
  `subprocess.run` (git/gh), `_check_repo` (checkout presence) and the publisher leaf
  (as a guard that it is never called).
- **(c) Fixture includes the fault?** Yes. The `gh pr create` stub really raises
  (`FileNotFoundError` and `RuntimeError`) after a `git push` the stub records as
  successful. The test asserts the push and the `gh` call both happened, so the faulting
  step is exercised, not skipped.

## Commit-readiness

The target has no formatter, linter or pre-commit config (no `.pre-commit-config.yaml`;
`.github/workflows` only has docs/render/linked-issue checks). The new lines stay under the
file's existing width. No commit hook to run.

## Housekeeping

I sent the T3 suite output to `/tmp/suite632.log`, which is outside the harness roots. It
is a plain log file and nothing depends on it; the harness or a human can delete it.
