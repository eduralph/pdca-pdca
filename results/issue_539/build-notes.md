# Build notes — issue 539, iteration 3 (what a transient leaf death is, decided once)

Base: the lane worktree at `41c19e9` ("pdca-integrate: issue_537"), which carries #538
(merged, `b920752`), #540 (merged, `4050da2`) and #537 (folded). Line numbers below are
**post-patch** in that worktree unless marked otherwise.

This rebuild starts from iteration 2's patch, applied unchanged (`git apply --check` clean on
this base), because the sign-off said the approach, slice and the rest of the patch are
sound. It adds the one thing the sign-off asked for: a spent subscription usage window is
not a transient death.

## The carry-forward: a spent usage window must not be retried

### What the vendor actually emits (claude-code 2.1.284, the installed binary)

I read this out of the binary before writing any code, because two of #506's rejected
rounds asserted event shapes the CLI cannot emit.

- **The record exists and is on stdout.** The SDK stream schema declares
  `iK = {type:"rate_limit_event", rate_limit_info: ajr(), uuid, session_id}`, described as
  "Rate limit event emitted when rate limit info changes". `ajr` has
  `status: z(["allowed","allowed_warning","rejected"])`,
  `rateLimitType: z(["five_hour","seven_day","seven_day_opus","seven_day_sonnet","seven_day_overage_included","overage"]).optional()`,
  `resetsAt`, `isUsingOverage`, and is described as "Rate limit information for claude.ai
  subscription users" (so API-key sessions never get one). It is built by `Qio`
  (`return{type:"rate_limit_event",rate_limit_info:r,uuid:to(),session_id:s}`) and emitted by
  the headless session's status-change listener (`Zf` → `c9(s)` → `WJe(E)` → `emit`).
- **Observed, not just derived:** real 2.1.277 `-p --output-format stream-json` streams from
  this operator's own subscription login (the #526 live probes) contain it, mid-stream right
  after the first response:
  `{"status":"allowed","resetsAt":1789761600,"rateLimitType":"five_hour","overageStatus":"rejected","overageDisabledReason":"out_of_credits","isUsingOverage":false,...}`.
  This matters: the **allowed** state names a window too, so `rateLimitType` alone is no
  refusal. The rule needs `status == "rejected"`.
- **What a 429 does to it.** `extractQuotaStatusFromError` runs in the request's catch block
  before the report is yielded, and for any 429 on a subscription login sets
  `K = Ddt(K, e)` = `{...K, status:"rejected", ...}`, then `emitStatusChange(K)`. The window
  comes from the 429's own `anthropic-ratelimit-unified-representative-claim` header
  (`fve`: `...S&&{rateLimitType:S}`). So **every** final 429 leaves `status:"rejected"`, but
  only a usage-limit 429 names a window.
- **The vendor draws the same line.** Its own test for a usage-limit 429 is
  `_sn(e)` = the claim header or the overage-status header. For a subscriber the CLI does
  not retry that one (`if(e.status===429)return!ut()||Sde()||qMt(e)`,
  `qMt(e)=e.status===429&&!_sn(e)&&…`). Its reports differ only in text and in fields that
  never reach the stream: `Qo({content:cve(F,n),error:"rate_limit",quotaLimits:…})` →
  "You've hit your session limit · resets 3pm", versus
  `Qo({content:"API Error: Server is temporarily limiting requests (not your usage limit) · …",error:"rate_limit",apiErrorIsTransient:M})`.
  The stream converter `_o` carries neither `quotaLimits` nor `apiErrorIsTransient`.
- **Extra usage.** `isUsingOverage = status rejected && overage allowed` means the window is
  spent but paid extra usage is serving requests. The vendor's own UI shows no error for it
  (`gdt`: `if(e.isUsingOverage){…return null}`). Its mock server names a window on every
  overage state (`setOverageScenarioHeaders` defaults `exceededLimits` to `five_hour`), so the
  overage arm of `_sn` needs no separate rule.

Not observed: a `rate_limit_event` in the `rejected` state. I would have to exhaust a real
usage window to capture one. The refused record in the tests is the observed allowed record
with the one field the CLI changes (`status`) flipped.

### The rule (progress.py)

- `_usage_limit_refusal(line, fmt)` (`progress.py:949-980`), beside `_is_main_session_work`
  and in the same shape as the other stream classifiers (dispatch on `stream_format`, shared
  decode, never raises). A refusal is `status == "rejected"`, a named `rateLimitType` (any
  non-empty string — a window this harness has not read still withholds the retry), and not
  `isUsingOverage`. It returns `None` for any line that is not a readable rate-limit record,
  so the drain keeps the newest state; a `rate_limit_info` that is not a mapping is ignored,
  as the vendor's own readers drop it. Codex and stream-less families answer `None`.
- The drain keeps the newest state (`progress.py:259`, `:286-288`). The record is
  account-wide (no `parent_tool_use_id`), so there is no scope to check.
- The fold at the end (`progress.py:408-414`): for a non-zero exit that is not the harness's
  own timeout, a refusal makes `produced` `True` in **either** transient shape, so
  `LeafError.transient` (unchanged, `leaves.py:121`) is `False`. Exit 0 and `TIMEOUT_RC` keep
  today's meaning.
- `rate_limit` stays in `_CLAUDE_TRANSIENT_KINDS` (iteration-1 decision). Its comment now says
  the policy covers a **passing** rejection, and the stream's record vetoes a spent window
  (`progress.py:791-795`).

### The tests the sign-off asked for, and the rest of the class

`SpentUsageWindowIsNotTransient` (`test_terminal_error_classification.py:606-731`), all
inline, all through `leaves._invoke_leaf_resilient` → `_invoke` → `run_with_heartbeat`:

- work + refused event + `rate_limit` report + exit 1 → **1 run**, not transient, no retry
  line (`:612`) — the sign-off's first case;
- work + plain `rate_limit` report + exit 1 → **still retried** (`:619`), with no event, after
  the observed allowed event, and after the `rejected`-with-no-window state a subscriber's
  passing 429 leaves — the sign-off's second case;
- each window in the schema plus an unknown one; `allowed` / `allowed_warning` with a window
  name; `isUsingOverage`; four spellings of "no window"; newest state wins both ways; the
  refusal vetoes the no-work shape, a 429 wrap-up and another transient report; a malformed
  record is ignored and the drain reads on; codex degrades; exit 0 and the harness timeout
  keep today's meaning;
- the builder is not re-run into a spent window (through `leaves.do_build`, `:713`);
- the §6 row is `human-empty`, never "safe to re-run" (`:719`) — the harm the sign-off named;
- the report text is still kept in the error log (criterion v).

I moved the builder and §6 plumbing into two shared helpers (`_build`, `_section6`,
`:278-306`) so the old headline tests and the new ones drive the same production path.

## Prose (criterion iv)

Every site that lists what is not transient now includes a spent usage limit next to a
signal death, and the places that listed "a usage/rate limit" as a transient cause say "a
rate limit": `LeafError` docstring (`leaves.py:93-104`), `transient` property
(`:111-121`), `_invoke` comment (`:686-691`), `_invoke_leaf_resilient` docstring
(`:717-727`), `_FAIL_*` comment (`:2966-2969`), `_failure_class` (`:2984-2987`), the
transient placeholder prose (`:3044-3049`: "a passing rate-limit rejection", "a rate
limit"), `run_with_heartbeat` docstring (`progress.py:88-103`, `:105-123`),
`_is_session_event` (`:550-554`), the section header (`:778-785`). The retry print, the builder's transient
line, the reviewer call-site comment and the §6 label are unchanged from iteration 2 and
still true: a spent window never reaches them. `test_leaf_resilience.py:5` still says
"usage/rate limit", but the brief puts that file off-limits.

The fixtures README (`template/tests/fixtures/README.md:89-279`) records the observed
record, the derived claims with each expression quoted, and five new greps. I ran all
thirteen greps against the installed 2.1.284; each matches.

## Decisions a reviewer may question

- **The veto covers both shapes, not only `rate_limit` reports.** While the account is
  refused, a fresh attempt is refused on its first request, however the leaf died. So a
  no-work death and a `server_error` report after a refusal are not retried either. Cost:
  if the newest refusal were stale, a retry that would have worked is withheld. The CLI
  emits a new event on every state change, so a stale refusal needs the server to report
  `rejected` on requests it served, which `isUsingOverage` already covers.
- **No `resetsAt` check.** The vendor's own UI treats a `rejected` state past its `resetsAt`
  as cleared. I left that out: retries happen seconds after the death, the newest-state rule
  already clears a refusal once the CLI sees an allowed response, and a wall-clock check
  would add a time dependency to the classifier for no case I can construct. About 4 lines
  and 2 tests if the human wants it.
- **A 429 that carries the window claim is a stop, whatever the server meant.** If the
  server ever sends the claim on a capacity 429, the harness withholds the retry, exactly as
  the CLI itself does ("You've hit your … limit", no CLI retry). This only withholds.
- **What the operator sees for a spent window:** the §6 row is `human-empty` ("leaf produced
  no usable verdict (needs a human)"), and the error log carries the vendor's own text
  ("You've hit your session limit · resets 3pm"). Skipping the leaf loudly and blocking its
  dependents is the §10 follow-up, out of scope here.

## Alternatives ruled out, with cost

- **Veto only a death whose kept record is a rate limit** (report kind `rate_limit` or a
  429 wrap-up). About +15 lines against the chosen rule (a second drain flag set beside
  `_note_terminal`, an 8-line helper, one more condition in the fold), and it leaves the
  no-work refused death retried three times with "safe to re-run" — the harm itself.
- **`status == "rejected"` alone** (one line shorter). 2.1.284 sets `rejected` on every final
  429 in a subscription session, so every passing 429 would stop being retried, against the
  sign-off's "a passing mid-session 429 stays transient".
- **Read the report text** ("You've hit your … limit" vs "not your usage limit"). The
  sign-off said not by prose, and the vendor calls its text the fallback that may change.
- **Carry the refusal on a new `LeafError` field** instead of `produced`. Changes `_invoke`'s
  raise and `LeafError.__init__`, outside "leaves.py strings, comments and the transient
  property only"; `produced` is read nowhere else (`grep -rn "\.produced\b"` finds only
  `leaves.py:106,121`).

## Consequences to state (not widened)

- **#537's builder** now stops at one attempt on a spent window instead of three, each of
  which would have been refused on its first request.
- **API-key sessions** get no `rate_limit_event`, so their `rate_limit` reports are retried
  as in iteration 2 (project policy).
- Unchanged from iteration 2: a retry is a fresh re-invoke, not a session resume; a signal
  death gets one attempt (#510's question beyond that).

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** The instance's C4 script (`engine/scripts/run-verify.sh`) on the
  final patch: green leg all four touched test modules OK (126 tests); red leg with the
  production hunks reverted: new file 54 failures (subtests counted) of 66 tests,
  `test_leaf_status` 2 of 15, `test_terminal_error_retention` 3 of 34, `test_builder_retry`
  11/11 green (docstring only). Zero `ERROR:` lines; the new file imports only pre-existing
  API. `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  One honest caveat about the carry-forward item: on the **base**, the sign-off's first case
  (work + refusal + `rate_limit` report → 1 run) already passes, for the wrong reason — the
  base never retried any death after work. Its red is against iteration 2's rule: mutant W01
  below (no refusal rule at all) fails 16 tests, all in the new class, that case and the §6
  "safe to re-run" case included. On the base itself the no-work refused shape is red (the
  base retries it three times).
- **(b) Production path? Yes.** Every case spawns a real child (a Python stub printing the
  events) through `leaves._invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat`;
  the builder case through `leaves.do_build`; the §6 case through `_failure_class`,
  `_review_unavailable` and `assemble._items_from_artifact`. Nothing is mocked except
  `time.sleep` in the builder case. C5 (`run-prod-path.py`): the added test imports
  `pdca_harness`.
- **(c) Fixture includes the fault? Yes, with the one caveat above.** The stub really emits
  the refused `rate_limit_event` and the `rate_limit` report and exits 1; the allowed record is
  verbatim from a real 2.1.277 stream. No real refused event (see "Not observed").

## Mutation check

`.cache/pdca-539-scratch/mutants.py` (git-ignored) copies `template/src`, applies one
mutation, and runs the new test file against the copy. 20 mutants, all killed: W01 no
refusal rule (16 failures), W02 no format dispatch, W03 no record-type check, W04 malformed
record clears instead of being ignored, W05 no status check (4), W06 no `isinstance`, W07 no
empty-name check, W08 no `isUsingOverage` check, W09 sticky refusal, W10 drain updates only
on a refusal, W11 veto applied to exit 0 / timeout, W12 veto only over the reported shape,
W13 veto skips the no-work shape; and the iteration-2 guards re-checked on this code: R01
`user` out of the work set (2), R02 empty status set (3), R03 no `subtype == "success"` guard,
R04 timeout re-labelled (2), R05 no signal rule (5), R06 typed cause ignored (13), R07
verdict not gated on the kept record (3). Log: `mutants.log` beside it.

## Runs

- C4 (`run-verify.sh`) on the final patch: PASS (above).
- T3 (`run-suite.sh`) on the final tree: root suite 24 OK, driver suite 2047 OK with 2
  pre-existing skips.
- C5 (`run-prod-path.py`): 1 added driver-suite test imports `pdca_harness`.
- T2 (`run-docs-check.sh`) not run by me: its checkers read only `docs/*.md` and
  `template/PCDA/quality-cycle/*.md` (`docs/publishing/tools/lint_docs.py:73-77`), and this
  patch touches neither; it also renders into a `mktemp -d` outside the worktree. Check
  re-runs it.
- `git diff --check`: clean. The target configures no formatter, linter or pre-commit hook
  (no ruff/black/flake8 config, no `.pre-commit-config.yaml`; CI runs the suites and the docs
  check). Only the DCO sign-off applies, at commit time.
- `patch.diff`: 116,747 bytes, 8 files, under the instance's size signal (`patch_kb = 125`,
  `patch_files = 25`). The worktree diff is byte-identical to it.

## How a human could observe the one derived record

Run any claude leaf on the subscription login when its 5-hour window is spent (or wait for a
real stop), with `--output-format stream-json --verbose`, and keep stdout. Expect a
`rate_limit_event` with `"status":"rejected"` and a `rateLimitType` before the
`"error":"rate_limit"` report, and exit 1. Replayed through `_invoke_leaf_resilient` it
should run once.
