# Adversarial review — issue 539 (what a transient leaf death is), iteration 2

**Bottom line:** I could not refute the red→green proof or the core mechanism, and found no
implementation defect to send back to Do. Two findings are policy calls for the human: both
are places where the patch's reading of the vendor's marks differs from what the vendor
itself does. Everything below was checked against the target at `$PDCA_TARGET` and against
the installed `claude-code 2.1.284`, the build the patch cites.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/progress.py:856` (with `:778`, `:784`): any typed
  cause the harness has not listed blocks a retry, including a free-form server
  `api_error_code` sitting on a `server_error` / `overloaded` report. Probe through
  `leaves._invoke_leaf_resilient`: work, then
  `{"error":"overloaded","is_api_error_message":true,"api_error_code":"capacity_exceeded"}`,
  exit 1 → **1 run, substantive**. The same happens for `server_error` +
  `api_error_code="overloaded_capacity"`. The CLI's own stream schema (2.1.284, the
  description of the `api_error` field) says *"new values are added over time, so treat an
  unknown value as absent"*. That means falling back to the kind, and here the kind says
  transient. `api_error_code` is whatever string the API puts in `error.details.error_code`;
  the CLI only checks that it matches `^[a-z][a-z0-9_]{0,63}$` (functions `H_n` / `oWo`). So
  the patch reads an unknown cause the opposite way from the vendor's documented contract.
  If the vendor types a new transient cause (it already typed one, `no_response`), or the
  API adds a detail code to a 529, the headline incident goes back to "not retried" and
  nothing warns anyone. The comment at `progress.py:779-784` ("for want of a reading, does
  one this harness has not seen") and the test at
  `tests/test_terminal_error_classification.py:368` treat this reading as settled. The
  iteration-1 carry-forward only asked that a typed cause outrank the kind. This fails
  safe (it withholds a retry and never adds one), so it is a policy choice, not a bug.

- NEEDS-HUMAN — `template/src/pdca_harness/progress.py:773` + `assemble.py:112`: when a
  subscription usage window runs out mid-session, the report rides `error:"rate_limit"`
  with **no** typed cause. In 2.1.284's 429 branch of `VHn` this is
  `Qo({content:cve(…),error:"rate_limit",quotaLimits:…})`, and `d0n` builds the text for
  the `five_hour` / `seven_day*` windows as "… · resets <time>". Probe: work, then
  `_report("rate_limit", "You've hit your 5-hour limit · resets 3pm")`, exit 1 → **3 runs,
  transient**, and §6 tells the operator "safe to re-run". That is false for hours, which
  is exactly the "false instruction" harm `assemble.py:95-99` warns about. Before this
  patch the same leaf was filed substantive. Carry-forward fix #1 only catches *typed*
  entitlement stops, so this untyped one gets through. The human kept `rate_limit`
  deliberately. The new information is that the stream carries a non-prose signal that
  tells a window stop apart from a passing 429: a
  `{"type":"rate_limit_event","rate_limit_info":{status, resetsAt, rateLimitType, …}}`
  event (2.1.284 functions `Qio` / `Zio`). So the two can be separated without reading
  prose. Decide whether to accept "safe to re-run" for window stops, or to scope a
  follow-up that keys on that event.

- Minor and informational (no action needed now): one guard is still not pinned by any
  test. Changing `all(` to `any(` at `progress.py:856` leaves the whole new test file green
  (mutation probe below). The input that would expose it is a report carrying both
  `api_error:"no_response"` and a gate `api_error_code`. 2.1.284 cannot produce that:
  `no_response` is set only when no response byte arrived, and `api_error_code` needs a
  response body. So for real inputs today the mutant behaves the same as the code.

## Attempted, could not refute

- **Red→green evidence.** I re-ran the green leg on the target:
  `tests.test_terminal_error_classification`, `test_leaf_status`,
  `test_terminal_error_retention`, `test_builder_retry` and `test_leaf_resilience` ran
  117 tests, all OK. The frozen red leg (`gate-logs/C4-verify.log`) fails on assertions,
  not on imports (`expected substantive; rc=-9`, `rc=137`, `expected transient; rc=1`, the
  stale §6 label). The fixture-replay reds use child-1's fixtures, which already exist on
  the base, so they are not reds from a missing file. The cases drive
  `_invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat` with a real
  subprocess, so they test the production path, not a copy of it.
- **Vendor grounding.** Checked against the 2.1.284 binary. Main-session stream events do
  carry `is_api_error_message`, `api_error` and `api_error_code` (the field copier `_o`).
  `APIConnectionError` (`Fu`, including its timeout subclass) is stamped `server_error`, so
  a lost connection is caught by the kind set and never reaches the prose reader. The
  vendor's main-session rule is `Akr` = `apiErrorIsTransient || overloaded ||
  server_error`, and the sub-agent set `["rate_limit","overloaded","server_error"]` exists
  as the patch comment says. An unclassified SDK error is reported as `API Error:
  <Pre(e)>`, so reading the status at the head of the text is correct. I found no event
  shape the patch reads that the CLI cannot emit.
- **Guards the brief required, killed by real mutation runs** on a scratch copy against the
  new test file: dropping `user` from `_WORK_EVENT_TYPES` (2 failures); emptying
  `_TRANSIENT_STATUSES` (3); dropping the `subtype == "success"` guard (1); ignoring
  `_note_terminal`'s return value (3); `rc != 0` instead of `rc not in (0, TIMEOUT_RC)` (1);
  `<=` at the 128 base (1); letting sub-agent traffic clear the verdict (1); letting a
  sub-agent report classify (2); never reading the leading status (5); treating any
  `unknown` prose as transient (3); ignoring typed causes (13). The only survivor is the
  `all`/`any` mutant above.
- **Signal predicate** (`progress.py:42`): 129 through 192 → True, 193 → False, 128 →
  False, `TIMEOUT_RC` → False. The memory cap is `systemd-run --scope`, which runs the leaf
  directly, so an OOM kill arrives as `-9`. The wrapper spelling is covered by a real
  `sh -c` test.
- **Restatement sites (criterion iv):** no stale "no output" / "did not run (transient" /
  "without emitting any work" definition is left in `src/`, `docs/` or
  `pdca.toml.jinja`. `test_leaf_resilience.py:7` still says "(no-output)", but the brief
  puts that file off-limits.
- **Not settled:** I could not establish from the minified binary whether the CLI can emit
  a synthetic main-session `tool_result` (a `user` event) *after* the API-error report,
  for example for a `tool_use` left pending when the connection dropped mid-response. If
  it can, `progress.py:271` would treat that as recovery and file the headline case as
  substantive. I have no concrete failing input for this, so it is not a finding. Only a
  real transcript of such a death would settle it.
