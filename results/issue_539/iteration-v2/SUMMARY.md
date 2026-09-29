# Result — issue 539 / what-a-transient-leaf-death-is-decided-once

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch: (i) a leaf whose stream carried a marked terminal error
  report and then exited non-zero is classified **transient** when the vendor marked the cause
  transient — a lost or interrupted connection, an overload or 5xx, a mid-session rate-limit
  rejection — **however much work came first**; (ii) it is **not** so classified when the vendor
  marked the cause **permanent** (invalid request, authentication, billing), nor for a kind this
  harness does not recognise, nor for a report the vendor left **unstamped** — no prose inside a
  marked report may promote a permanent cause, and a leaf that merely mentions or quotes an error
  is untouched; a report the CLI **recovered** from, with real **main-session** work following, is
  not the leaf's death; and a **sub-agent's** report never classifies (the CLI has its own
  recovery for those); (iii) a leaf a **signal** killed is never classified transient on the
  strength of having emitted nothing — in **both** returncode spellings, `-signum` from a direct
  child and the shell's `128+signum` from a wrapper argv — so a memory-capped leaf is not re-run
  into the same cap, while the harness's own wall-clock kill (`progress.TIMEOUT_RC`) keeps today's
  meaning; (iv) **every** site that restates the definition states the same true thing, covering
  **both** shapes — a leaf that produced nothing at all, **or** one that ended on its own marked
  transient report — and the operator-facing `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` no longer
  asserts "did not run" of a leaf that ran; `template/tests/test_leaf_status.py` is updated with
  it rather than left pinning the stale string; (v) child-1's retention is **unchanged** — in
  particular the report text is still retained for a report the session recovered from, even
  though this child's clearing rule removes the *verdict*; (vi) nothing else changes: a
  stream-less family still reports substantive (`leaves.py:666-670`), `capture` still returns the
  child's raw stdout unmodified, codex/gemini degrade to today's behaviour, a leaf that succeeds
  is spawned and reported exactly as today, and the #420 post-mortem still rides `output` into the
  same log.
- Repo + branch target: eduralph/pdca-harness @ main (base `acb214a`; every `path:line` here
  was re-verified against it while this proposal was written)
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review the transient-leaf classification fix: retry reported transient API deaths after work, exclude signal deaths and permanent causes, and keep operator messages and retained evidence consistent.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six success criteria define observable retry, recovery, signal, retention and compatibility outcomes; the carry-forward explicitly resolves the apparent scope exceptions (`brief.md:28`, `brief.md:211`). |
| C2 Reproduction (red pre-fix) | PASS | With only the three production modules stashed, the same 112 tests produced 45 assertion failures, including post-work retry counts and signal exclusions, rather than missing imports or fixtures (`reviewer-red.log:534`; `target/template/tests/test_terminal_error_classification.py:259`). |
| C3 Change | PASS | Permanent typed causes take precedence, recovery clears the verdict without deleting evidence, and signal deaths cannot consume retries; the additional message/test edits are already authorized (`target/template/src/pdca_harness/progress.py:854`, `target/template/src/pdca_harness/progress.py:271`, `target/template/src/pdca_harness/leaves.py:116`; `brief.md:211`). |
| C4 Verification (red→green) | PASS | Restoring the production fix made all 112 tests pass; this independently reproduces the frozen gate’s behavioral red→green evidence (`reviewer-green.log:14`; `gate-logs/C4-verify.log:594`). |
| C5 Causal adequacy | PASS | Tests exercise the actual subprocess/retry path; removing user-event recovery, transient HTTP statuses, or the success-subtype guard independently causes assertion failures; no new optional-capability probe masks a load-time cause (`target/template/src/pdca_harness/progress.py:864`, `target/template/src/pdca_harness/progress.py:895`; `reviewer-mutations.log:19`, `reviewer-mutations.log:38`, `reviewer-mutations.log:57`). |
| T1 Structure | PASS | Classification stays beside the existing stream readers, uses the existing event decode, and leaves retry scheduling and retention precedence intact; the stream-less fallback remains substantive (`target/template/src/pdca_harness/progress.py:261`, `target/template/src/pdca_harness/progress.py:688`, `target/template/src/pdca_harness/leaves.py:684`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page site rendering/link audit, and diff whitespace checks passed; frozen docs and host-CI parity logs also show successful audits (`gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent offline driver run passed 2,033 tests with two skips; frozen evidence also shows 24 root tests passing, including render/update coverage unavailable to this interpreter (`reviewer-suite.log:1656`; `gate-logs/T3-suite.log:54`; local host caveat: `reviewer-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the substantive audit is deferred to its required publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior art across merged and closed/rejected work before publication — the brief reports merged-path checks and rejected rounds, but the supplied one-commit snapshot has no remote/history to independently establish completeness (`brief.md:198`, `brief.md:206`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the operational tradeoff of restarting a previously productive leaf and the vendor-schema evidence boundary — real 2.1.284 typed-error streams were not exercised, so that mapping rests on documented code-derived records plus executable offline cases (`target/template/src/pdca_harness/leaves.py:718`, `target/template/tests/fixtures/README.md:208`). |

No confirmed patch defect was found. All source citations above ground on the supplied patched target. Its base supports the independent reproduction; no stale-target caveat was needed. The scope exceptions and project policy to retry untyped rate-limit reports were already approved in the brief’s carry-forward and are not reopened here.

Independent verification used the disposable target only. Production changes were stashed while all patched tests remained available, then restored with `git stash pop`. From `target/template`, both legs ran `PYTHONPATH=src python3 -m unittest tests.test_terminal_error_classification tests.test_leaf_status tests.test_terminal_error_retention tests.test_builder_retry`; the full green suite ran `PYTHONPATH=src python3 -m unittest discover -s tests`. `TMPDIR` stayed inside this review workspace, and bytecode writes were disabled. Mutation checks changed module objects in a separate Python process, not source files. Afterward, `git apply --reverse --check ../patch.diff` confirmed the supplied patch remained applied.

The root-suite rerun explicitly reported `PDCA-UNVERIFIABLE`: Copier is not importable by `/usr/bin/python3`; 19 tests ran with three skips. This is a local toolchain caveat, not a patch failure. The frozen T3 log records the substantive root coverage (24 tests, no skips) and the same successful 2,033-test driver suite. Instance-scoped gate wrappers were adjudicated from their supplied logs; their absence from the target is expected. The target’s integration template contains no additional enumerated human-only checks (`target/template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation: `git log --oneline -- template/src/pdca_harness/progress.py template/src/pdca_harness/leaves.py template/src/pdca_harness/assemble.py` returned only synthetic base commit `3748606`; `git remote -v` returned no entries. Thus the brief’s history account is available, but independent merged/closed/rejected history verification is not. The T5 decision concerns that evidence gap, not a demonstrated duplicate or ordering defect.

### Advisory — adversary

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

### Advisory — code-review

# Advisory code review — issue #539 (transient leaf death, decided once)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Grounded on the patched target at `$PDCA_TARGET`.

**Summary: no blocking correctness bug found.** The classification logic, the drain wiring
and the signal predicate do what the brief asks. The three guards the brief names (main-session
`user` work, the `_TRANSIENT_STATUSES` set, the `subtype == "success"` wrap-up guard) each have a
test that fails if the guard is removed. The iteration-1 carry-forward items (typed cause before
the kind shortcut, the `apiError` spelling, the anchored status regex with no bare `timeout`,
the `assemble.py:95` comment) are all in. What follows are low-severity notes, none gating.

## Correctness

- `template/src/pdca_harness/progress.py:265-272` — the verdict follows only the record
  `_note_terminal` *keeps*, and clearing only happens on non-report main-session work. I walked
  through the orderings: sub-agent report then main report; main report then wrap-up; main
  report, then work, then a wrap-up with a 5xx; main report, then work, then a new main report.
  Each gives the intended verdict. The one-way "cleared stays cleared until a nearer-or-equal
  record" rule is correct because `_TERMINAL_PRECEDENCE` (`progress.py:592`) puts `_REPORT`
  highest. No bug.
- `template/src/pdca_harness/progress.py:393` — `rc not in (0, TIMEOUT_RC)` keeps exit 0 and the
  harness's own timeout unchanged, as criteria (iii) and (vi) require. A signal-killed leaf that
  had reported a transient cause still comes back `produced=False` here, but
  `LeafError.transient` (`leaves.py:116`) rejects it on `is_signal_death`, and
  `test_the_kill_outranks_a_transient_report` pins that. The split is correct but spread across
  two modules. The docstring at `progress.py:98` says so; no action needed.
- `template/src/pdca_harness/progress.py:42-59` (`is_signal_death`) — any exit code 129–192 is
  treated as a signal death, even from a direct child that chose that code itself.
  `test_a_bare_exit_137_is_read_as_the_same_death` pins this on purpose, and the only cost is
  "not retried". That is acceptable, but the price is that a CLI which ever exits 129–192 for
  its own reasons (not a signal) loses its retry. Noted, not a defect.
- `template/src/pdca_harness/progress.py:871` (`_typed_causes`: `ev.get(key) is not None`) —
  an empty-string typed cause (`"api_error": ""`) counts as "typed" and so turns a stamped
  `server_error` / `overloaded` report into not-transient. This fails safe (no retry), and the
  CLI is not known to emit an empty string, so it is only a nit. A truthiness check
  (`if ev.get(key)`) would treat `""` as untyped and let the kind decide.
- `template/src/pdca_harness/progress.py:372-373` — `died_of` is read after
  `reader.join(timeout=5)`, so if a drain thread is still running after 5 s the verdict could be
  stale. This is the same existing limit child-1's `terminal` state already has, not a new
  hazard. Mentioned only because the patch adds a second reader of that state.

## Reuse / simplification / efficiency

- Hot-loop cost is fine. `_reports_transient_cause` runs only when a marked record is kept
  (rare), and `_is_main_session_work` only while a transient verdict is pending. Both reuse the
  drain's single decode through `_stream_event`'s dict pass-through (`progress.py:502-514`). No
  duplicated helper: `_is_main_session_work` is different from `_is_session_event` on purpose
  (it leaves out `result`), and it reuses `_is_subagent_event`.
- The two-shape wording ("before emitting any work, or on its own report of a transient API
  error") is now copied into about eight prose sites (`leaves.py:97-102`, `:110-115`,
  `:711-719`, `:768`, `:2202`, `:2932`, `:2958`, `:3036-3040`; `assemble.py:104`, `:112`). Each
  site agrees today, which is what criterion (iv) asks for. The copies can still drift apart the
  same way the old single-shape wording did, and only the operator-facing strings (the label,
  the retry line, the builder line) are pinned by tests. A shared constant for the runtime
  strings would stop that drift. This is optional and lies outside the brief's "strings only"
  limit for `leaves.py`, so it is not filed as a finding.

## Consequence to confirm (not a code defect)

- NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:758-770` together with the builder path
  (`leaves.py:2158`, #537): a leaf that worked for minutes and then lost the API is now re-run
  **from scratch** up to `attempts - 1` more times, each with its full timeout. For the reviewer
  this is the goal (criterion i). For the builder, stacked on #537, it means a fresh builder
  starts on a worktree still holding the dead attempt's partial edits, and worst-case wall-clock
  for one Do grows to about `attempts × leaf timeout`. The brief calls this a consequence to
  record, not a reason to widen the slice. Confirm at sign-off that the retry budget and the
  dirty-worktree restart are acceptable for the builder, or track it as a follow-up.

## Gate evidence

C4 is red→green: `gate-logs/C4-verify.log` shows 40 of 52 failing on the red leg and green with
the fix. The red failures are behavioural assertions (for example `human-empty != infra-empty`,
`retry 1/2` missing), not import errors. T3 passes: 2033 tests, 2 skips, both in unrelated
modules. The pinned vendor fixtures are present, so the fixture-replay cases actually ran
rather than skipping.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm affected-path prior art across merged and closed/rejected work before publication — the brief reports merged-path checks and rejected rounds, but the supplied one-commit snapshot has no remote/history to independently establish completeness (`brief.md:198`, `brief.md:206`).
- [ ] Validation — fitness-to-purpose — Accept the operational tradeoff of restarting a previously productive leaf and the vendor-schema evidence boundary — real 2.1.284 typed-error streams were not exercised, so that mapping rests on documented code-derived records plus executable offline cases (`target/template/src/pdca_harness/leaves.py:718`, `target/template/tests/fixtures/README.md:208`).
- [ ] `template/src/pdca_harness/progress.py:856` (with `:778`, `:784`): any typed cause the harness has not listed blocks a retry, including a free-form server `api_error_code` sitting on a `server_error` / `overloaded` report. Probe through `leaves._invoke_leaf_resilient`: work, then `{"error":"overloaded","is_api_error_message":true,"api_error_code":"capacity_exceeded"}`, exit 1 → **1 run, substantive**. The same happens for `server_error` + `api_error_code="overloaded_capacity"`. The CLI's own stream schema (2.1.284, the description of the `api_error` field) says *"new values are added over time, so treat an unknown value as absent"*. That means falling back to the kind, and here the kind says transient. `api_error_code` is whatever string the API puts in `error.details.error_code`; the CLI only checks that it matches `^[a-z][a-z0-9_]{0,63}$` (functions `H_n` / `oWo`). So the patch reads an unknown cause the opposite way from the vendor's documented contract. If the vendor types a new transient cause (it already typed one, `no_response`), or the API adds a detail code to a 529, the headline incident goes back to "not retried" and nothing warns anyone. The comment at `progress.py:779-784` ("for want of a reading, does one this harness has not seen") and the test at `tests/test_terminal_error_classification.py:368` treat this reading as settled. The iteration-1 carry-forward only asked that a typed cause outrank the kind. This fails safe (it withholds a retry and never adds one), so it is a policy choice, not a bug.
- [ ] `template/src/pdca_harness/progress.py:773` + `assemble.py:112`: when a subscription usage window runs out mid-session, the report rides `error:"rate_limit"` with **no** typed cause. In 2.1.284's 429 branch of `VHn` this is `Qo({content:cve(…),error:"rate_limit",quotaLimits:…})`, and `d0n` builds the text for the `five_hour` / `seven_day*` windows as "… · resets <time>". Probe: work, then `_report("rate_limit", "You've hit your 5-hour limit · resets 3pm")`, exit 1 → **3 runs, transient**, and §6 tells the operator "safe to re-run". That is false for hours, which is exactly the "false instruction" harm `assemble.py:95-99` warns about. Before this patch the same leaf was filed substantive. Carry-forward fix #1 only catches *typed* entitlement stops, so this untyped one gets through. The human kept `rate_limit` deliberately. The new information is that the stream carries a non-prose signal that tells a window stop apart from a passing 429: a `{"type":"rate_limit_event","rate_limit_info":{status, resetsAt, rateLimitType, …}}` event (2.1.284 functions `Qio` / `Zio`). So the two can be separated without reading prose. Decide whether to accept "safe to re-run" for window stops, or to scope a follow-up that keys on that event.
- [x] `template/src/pdca_harness/leaves.py:758-770` together with the builder path (`leaves.py:2158`, #537): a leaf that worked for minutes and then lost the API is now re-run **from scratch** up to `attempts - 1` more times, each with its full timeout. For the reviewer this is the goal (criterion i). For the builder, stacked on #537, it means a fresh builder starts on a worktree still holding the dead attempt's partial edits, and worst-case wall-clock for one Do grows to about `attempts × leaf timeout`. The brief calls this a consequence to record, not a reason to widen the slice. Confirm at sign-off that the retry budget and the dirty-worktree restart are acceptable for the builder, or track it as a follow-up.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on one policy gap; the approach, slice and the rest of the patch are sound — keep them. Fix in the rebuild: a subscription usage-window stop (5-hour / weekly limit) must NOT be classified transient. Today it arrives as an untyped `error:"rate_limit"` report, is retried 3x, and §6 tells the operator "safe to re-run" — false for hours (the assemble.py:95-99 "false instruction" harm). Distinguish it from a passing 429 using the stream's non-prose signal, the `{"type":"rate_limit_event","rate_limit_info":{status, resetsAt, rateLimitType, ...}}` event (claude-code 2.1.284, functions Qio / Zio) — not by reading prose. A passing mid-session 429 stays transient (rate_limit stays in _CLAUDE_TRANSIENT_KINDS, per iteration-1 decision). Add inline tests: work + window-exhausted rate_limit_event + rate_limit report + exit 1 → 1 run, not transient; work + plain rate_limit report (no window event) + exit 1 → still retried. Out of scope for this bundle (tracked separately in §10): skipping the leaf loudly so the flow continues, and blocking its dependents — that is flow-scheduling work, not classification.
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Follow-up issue: a leaf that hits a subscription usage-window stop should be skipped loudly so the flow keeps going, with every bundle that depends on it (or is blocked by it) also blocked — flow-level, out of #539's scope.
- Follow-up issue: builder retry after a transient death (with #537) restarts from scratch on a worktree holding the dead attempt's partial edits, at up to ~3× leaf timeout — consider resetting the worktree before a retry, resuming the CLI session, or a lower builder retry budget.
