## Summary
**User impact:** When a model run dies partway through, the harness often makes the wrong
call about trying again. A builder that worked for eighteen minutes and then lost its
network connection was not retried, so a whole review round was wasted on a passing blip.
A run killed by the memory cap before it printed anything was retried three more times,
hitting the same cap each time. And the Check summary told the operator such a run "did not
run … safe to re-run", even directly above the error log proving it ran for eighteen minutes.

This PR decides whether to retry from *how* the run died — the cause the model CLI reported,
or the signal that killed it — instead of from whether it had printed anything yet, and makes
every message about that decision say the same true thing.

Reported in [#539](https://github.com/eduralph/pdca-harness/issues/539).

**Merge order:** this stacks on PR #587 (#537, the builder joins the retry path) and corrects
the retry message that PR adds. Merge #587 first, then this one.

## What to look at
- **The rule** lives in the stream reader in `progress.py`: it reads the CLI's own last error
  report and its usage-limit record, and decides "transient or not". `leaves.py` exposes that
  decision as the one property every caller already uses.
- **What changes for a user:** a run that dies of a lost connection, overload, server error or
  a passing rate-limit rejection is retried, however long it ran. A run killed by a signal,
  one refused by a spent subscription window, or one that failed for a permanent reason
  (bad request, auth, billing) runs once.
- **Try it offline** (no API key, no network), from `template/`:
  `PYTHONPATH=src python3 -m unittest tests.test_terminal_error_classification -v`.
  Each case spawns a small Python "leaf" that prints the recorded CLI events and exits,
  through the real retry path. The classes are named after the rules they check.

## Root cause
`LeafError.transient` was `return not self.produced`, where `produced` means "a substantive
stream event arrived". "Did it say anything?" stood in for "did it die of something a retry
fixes?", which is wrong both ways, and the definition was restated in about ten places
(docstrings, prints, the Check summary label) in single-shape "no output" wording.

## Fix
- `progress.run_with_heartbeat` keeps a verdict from the CLI's own main-session error report:
  transient when the report kind is `server_error`, `overloaded` or `rate_limit` (the last is
  a project choice, borrowed from the CLI's sub-agent retry set) and no typed cause
  (`api_error` / `apiError` / `api_error_code`) says otherwise. An `unknown` report is read
  only for a leading `API Error: NNN` with a retryable status or a failed-connection wording.
  A later main-session `assistant` or `user` tool-result event clears the verdict (the CLI
  recovered). Sub-agent reports never set it.
- A `rate_limit_event` with `status: "rejected"`, a named `rateLimitType` and no
  `isUsingOverage` marks a spent usage window; the newest such record wins, and it vetoes a
  retry in either shape.
- The verdict applies only to a non-zero exit that is not the harness's own timeout.
- `LeafError.transient` is now `not produced and not is_signal_death(rc)`;
  `is_signal_death` covers both `-signum` and the shell's `128+signum`.
- Every restatement — `LeafError` docstring, `_invoke` comment, retry print, builder retry
  print, `_failure_class`, the unavailable-review prose, `assemble.py`'s comment and
  `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]`, the `test_builder_retry.py` docstring — now states
  the two-shape definition. `test_leaf_status.py` is updated with the label.
- `test_terminal_error_retention.py`: three guards that asserted the old "work means not
  transient" rule are flipped/renamed. Retention itself is unchanged: the report text is still
  kept, including for a report the session recovered from.
- `tests/fixtures/README.md` records which vendor claims were observed in real
  claude-code 2.1.277 streams and which were derived from reading the 2.1.284 binary, with
  greps to re-check them.

## Verification
Line numbers are on `main` with PR #587 applied (the base this patch stacks on).
- **Claim:** a leaf that did work and then reported a transient API failure is retried.
  **Checked:** `template/src/pdca_harness/progress.py:277-285` (verdict set from the kept
  report, cleared on main-session recovery), `:404-414` (applied only to a non-zero,
  non-timeout exit). **Test:** `TransientCauseAfterWorkIsRetried`
  (`template/tests/test_terminal_error_classification.py:338`) — 1 run pre-fix, 3 post-fix.
- **Claim:** a permanent, unknown, sub-agent or recovered-from report is not retried.
  **Checked:** `progress.py:799` (kind set), `:843` (`_reports_transient_cause`), `:895`
  (`_typed_causes`, both spellings), `:905` (anchored reader for `unknown` reports), `:924`
  (main-session work, including `user` tool results). **Test:** `NotEveryReportIsTransient`
  (`:410`), including the typed-credits `rate_limit` case, the `apiError` spelling, and
  negative cases for an incidental number and a `timeout` field in a 400 body.
- **Claim:** a signal death is never retried for having said nothing, in either spelling;
  the harness timeout keeps its meaning.
  **Checked:** `progress.py:40-59` (`is_signal_death`), `template/src/pdca_harness/leaves.py:111-121`
  (`transient`). **Test:** `SignalDeathIsNotTransient` (`:557`) — SIGKILL/SIGTERM and the
  `137` wrapper case run 3 times pre-fix, 1 post-fix.
- **Claim:** a spent subscription window is not retried; a passing 429 still is.
  **Checked:** `progress.py:949-980` (`_usage_limit_refusal`), `:412-414`.
  **Test:** `SpentUsageWindowIsNotTransient` (`:606`), incl. the builder via `do_build` and the
  summary row reading "needs a human", never "safe to re-run".
- **Claim:** the operator is told the truth. **Checked:** `template/src/pdca_harness/assemble.py:112-113`
  (label). **Test:** `WhatTheOperatorIsTold` (`:735`) and `template/tests/test_leaf_status.py`,
  whose old-label assertions fail pre-fix.
- **Claim:** nothing else changes (retention, exit 0, stream-less families, codex, raw stdout).
  **Test:** `RetentionIsUnchanged` (`:775`), `NothingElseChanges` (`:794`).
- **Red → green:** with the production changes reverted and the tests kept, the new file fails
  54 of 66 cases on assertions (no import errors), `test_leaf_status` 2, the retention suite 3.
  With the patch, all touched suites pass, and the full offline suite passes (2047 tests,
  2 existing skips). An independent reviewer reproduced the same red → green.
- **Mutation check:** 20 targeted mutants of the new rule were each killed by the new file.

## Known limits
- No real spent-window stream has been captured. The `rejected` record in the tests is the
  observed `allowed` record with `status` flipped, per the vendor code. To confirm, run a leaf
  with `--output-format stream-json --verbose` on an exhausted subscription and replay the
  stream: expect one run and a "needs a human" row.
- The CLI can also mark a *near-limit* passing 429 `rejected` with a window name. That run
  would not be retried (a lost retry, on the safe side). The fixtures README states the vendor
  claim more broadly than that.
- Two anchors in the `unknown`-report reader (`_UNKNOWN_STATUS_RE.match` vs `.search`, and the
  exact `API Error: terminated` match) are correct but not yet pinned by a test.

Fixes #539
