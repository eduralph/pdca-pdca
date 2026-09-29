# Build notes — issue 539, iteration 2 (what a transient leaf death is, decided once)

Base: the lane worktree at `41c19e9` ("pdca-integrate: issue_537"). It carries #538
(merged, `b920752`), #540 (merged, `4050da2`) and #537 (folded). The patch applies cleanly
to it (`git apply --cached --check` against a scratch index of `HEAD`). Line numbers below
are **post-patch** in the worktree unless marked "base". The brief's own line numbers are on
its older base `acb214a`; on this base they moved (for example `leaves.py:104-107` is now
base `:105-109`, `assemble.py:80/:85` are base `:103/:109`).

This rebuild starts from iteration 1's patch (the sign-off said the approach and slice are
sound) and fixes the six carry-forward items. Everything else from iteration 1 was
re-read and kept only where it still holds.

## The carry-forward, item by item

1. **A typed cause is checked before the kind** (`progress.py:854-856`). A `rate_limit`
   report the CLI typed as `long_context_credits_required` or
   `model_requires_usage_credits` is no longer retried. I made the rule general instead of
   special-casing `rate_limit`: whenever the report carries a typed cause, the typed cause
   decides, and only `no_response` (`_CLAUDE_TRANSIENT_CAUSES`, `:784`) counts as
   transient. Reason: 2.1.284 also puts typed causes on `server_error`
   (`tls_untrusted_ca`, `gateway_content_type`), and those are configuration stops a
   fresh attempt meets again. Iteration 1 retried them; the base never did (on the base a
   marked report is an `assistant` event, so any death with a report was substantive).
   Tests: `test_a_rate_limit_the_vendor_typed_as_a_usage_credit_stop`,
   `test_a_server_error_the_vendor_typed_as_a_stop_a_retry_meets_again`,
   `test_a_typed_cause_this_harness_has_not_read`,
   `test_a_typed_cause_that_names_a_response_that_never_came`.
2. **Both spellings of the typed cause** (`_CLAUDE_CAUSE_FIELDS`, `:778`): `api_error`
   (stream) and `apiError` (transcript). I also added the second typed field the CLI
   ships, `api_error_code` / `apiErrorCode`. The vendor's schema calls it the channel for
   "server gate codes this build has no api_error value for, so a host can key on a new
   gate". That is exactly the case item 1 is about, for a gate the CLI has not typed yet.
   Example from 2.1.284: a 429 whose body carries `credits_required` but misses the
   mapper's typed branch (it is guarded by a condition, `K=M&&…`) falls through to an
   untyped `rate_limit`, and the wrapper then attaches `apiErrorCode:"credits_required"`.
   The `success` wrap-up repeats that code, so the wrap-up rule honours it too (`:864`). Tests: `test_the_transcript_spelling_of_a_typed_cause`
   (all three: `apiError` gateway sign-in, `apiError` usage-credit stop, `apiErrorCode`),
   `test_a_server_gate_code_outranks_the_kind`, `test_a_wrapup_carrying_a_server_gate_code`.
3. **The `unknown` text reader is narrow now** (`_unclassified_text_is_transient`,
   `:879-890`). Two steps:
   - A leading `API Error: <status>` decides on its own (`_UNKNOWN_STATUS_RE`, `:794`,
     anchored with `re.match`). Nothing after it is read, so a 400 body is never promoted
     by a number or a word inside it.
   - With no leading status, only the wording of a connection that failed counts
     (`_CONNECTION_FAILED_RE`, `:801-814`): the phrases the SDK, the CLI, Node and undici
     use, and the CLI's own `JF`/`J0` connection codes. No bare `timeout`, no bare number,
     no "overloaded"/"rate limit"/"internal server error" prose (in 2.1.284 those always
     arrive with a status or with their own kind).

   Why this is grounded, not just narrower: in 2.1.284 an `unknown` report is either
   `API Error: ${Pre(e)}` for an `APIError` with a status (the SDK's `makeMessage` puts the
   status first; an `APIError` with no status is turned into `APIConnectionError` and
   stamped `server_error` earlier), or `API Error: ${e.message}` for a failure that got no
   HTTP answer. 5xx and 429 are stamped earlier, so the statuses that reach `unknown` are
   4xx; 408 and 409 are the only ones the API client retries. Negative tests:
   `test_an_unclassified_report_is_decided_by_its_leading_status_alone` (the adversary's
   `messages.536…` body, the `…input.timeout` field-name body, and a 400 body quoting every
   connection phrase) and `test_an_unclassified_report_without_a_status_names_no_failed_connection`
   (an incidental `536` and a `timeout` field with no status). The mutant the sign-off named
   ("any text not containing `Unexpected`") is now killed (M17 below).
4. **`assemble.py:95` comment** now says both INFRA shapes mean "no review came back", and
   notes a transient one may have worked for minutes first. It agrees with `leaves.py:3023`.
5. **`rate_limit` is stated as project policy.** `progress.py:764-773` and the README
   (`template/tests/fixtures/README.md`, "`rate_limit` is this project's policy") now say:
   `server_error` and `overloaded` are the vendor's main-session rule (`Akr`); `rate_limit`
   is this project's choice, made at sign-off; the three-kind set is borrowed from the CLI's
   handling of a sub-agent an API error cut off. I also corrected what that sub-agent set
   does: iteration 1 called it the set the CLI "retries" a sub-agent on. It is not a retry.
   `il()` keeps the cut-off Task's partial output ("Everything below is PARTIAL output
   recovered from the agent before it was cut off") instead of failing the Task. The README
   also drops iteration 1's claim that "a TLS failure dies before any work, which #138
   already retried" — that was wrong on this base (see item 1).
6. **Scope, as decided at sign-off.** Kept: the flipped/renamed guards in child-1's
   `test_terminal_error_retention.py` (`:21-23`, `:368-402`) and the string in
   `_do_build_command` (`leaves.py:2201-2205`). Added, docstring only:
   `test_builder_retry.py:3-9` now states the two-shape definition. No test in that file
   changed. The `_do_build_command` string sits on #537's PR 587, so 587 must merge first.

## What the patch does, by file

**`progress.py` — the verdict, computed where the stream is read.**
- `is_signal_death(rc)` (`:34-59`): both spellings of a signal death, `-signum` (direct
  child) and the shell's `128+signum` (wrapper argv), signals 1-64. `TIMEOUT_RC` (-1001)
  is outside both ranges.
- The drain asks one more question of the record child-1 already keeps
  (`:240-246`, `:265-272`): does it name a cause the vendor marks transient? The verdict
  follows the record `_note_terminal` keeps (it now returns whether it kept the record,
  `:663-691`), so a farther record cannot overrule a nearer one. Main-session `assistant`
  or `user` work after the report clears the verdict only; the kept text stays, which is
  criterion (v).
- The verdict is folded into `produced` only for a non-zero exit that was not the
  harness's own timeout (`:388-394`). Exit 0 and a timeout keep `produced` as it was.
- The classifier (`_reports_transient_cause`, `:817-866`) sits beside `_is_session_event`
  and `_terminal_error` in their shape: dispatch on `stream_format`, shared decode, `False`
  for anything it does not know. It never raises on odd field types (it runs in the drain
  thread; a raise there would stop every later line being read). It runs only when a
  record is kept, and `_is_main_session_work` (`:898-911`) only while a transient verdict
  stands, so the hot loop pays nothing extra on ordinary lines.
- Prose that said "nothing is classified" or "`produced` is byte-identical" is rewritten
  (base `:61-66`, `:78-79`, `:328-329`, `:467-468`, `:488-489`, `:573`).

**`leaves.py` — the property plus strings and comments only.**
- `LeafError.transient` (`:108-116`): `not produced and not progress.is_signal_death(rc)`.
  This is the code fix for round 3's defect (a), not a narrowed sentence.
- Rewritten to the same two-shape definition: the `LeafError` docstring (`:93-102`), the
  `_invoke` fallback comment (`:681-685`, code untouched), the `_invoke_leaf_resilient`
  docstring (`:711-719`, which now also says a retry is a fresh re-invoke, not a session
  resume), the retry print (`:767-770`, string only; the folded `for attempt` loop is
  otherwise untouched), the builder's failure line (`:2201-2205`), the reviewer call-site
  comment (`:2932-2934`), the `_FAIL_*` comments (`:2954-2963`), `_failure_class`
  (`:2975-2978`) and `_unavailable_classification` (`:3023`, `:3035-3040`).

**`assemble.py`.** The comment at `:95-99`, the `infra-empty` comment (`:104-106`), and the
operator-facing label (`:112-113`): "leaf died of transient infra (before emitting any
work, or on its own report of a transient API error — safe to re-run)". It no longer says
"did not run". "Safe to re-run" stays true for both shapes.

**Tests.** `test_leaf_status.py` `:84` comment, `:135-140` (the full label, plus "did not
run" must be absent) and `:229` (the §6 filter). The brief said `:188` would go red; it
does not — `:188` checks the *startup* label, which is still true and unchanged. The new
`test_terminal_error_classification.py` holds criteria (i)-(vi) (52 tests).

**Provenance.** `template/tests/fixtures/README.md`, section "Classifying the report
(issue #539)": which claims are observed, which derived from 2.1.284, and eight greps that
re-verify them. I ran all eight against the installed binary; each matches and each takes
about a second.

## Vendor grounding (claude-code 2.1.284, the installed binary)

Observed (real bytes, already pinned by #538): the 2.1.228 incident record is
`error:"server_error"` and that leaf exited 1; the 2.1.222 permanent record is
`error:"model_not_found"`. Neither carries a typed cause.

Derived (read out of the binary; the README quotes each expression):
- the kind enum; the vendor's main-session rule `Akr` (`overloaded`/`server_error` or the
  `apiErrorIsTransient` flag, which never reaches the stream);
- the sub-agent set `rl` and what `il()` does with it;
- the typed-cause enum (25 values) and which kinds carry which typed cause;
- `api_error_code` and where it is set;
- how an `unknown` report's text is built, and which statuses can reach it;
- the lost-connection codes `JF`/`J0`; the status on the `success` wrap-up only;
- what a main-session vs sub-agent `user` event looks like.

Not observed: a real 2.1.284 stream of an API-error death, or any real record carrying a
typed cause. If a human wants to close that gap, the cheapest real check is to run a
`claude -p --output-format stream-json --verbose` session through a proxy that drops the
connection mid-response, and confirm the last `assistant` line carries
`"is_api_error_message":true,"error":"server_error"` with no `api_error`.

## Decisions a reviewer may question

- **Typed cause outranks kind for every kind, not only `rate_limit`.** Cost: a
  `server_error` typed `tls_untrusted_ca` / `gateway_content_type` is not retried. That is
  the base behaviour, and those are configuration problems a retry repeats.
- **An unrecognised typed cause withholds the retry.** The schema says to "treat an
  unknown value as absent"; the harness deliberately does not, matching criterion (ii) for
  unknown kinds. Cost: if a future CLI adds a typed cause for a genuinely transient failure
  on `server_error`, it will not be retried until `_CLAUDE_TRANSIENT_CAUSES` learns it. It
  can only ever withhold a retry.
- **`api_error_code` counts as a typed cause.** Risk: the CLI copies any identifier the
  server puts in `error.details.error_code`, on any API error. If the API ever sends one on
  a 5xx or 529, those stop being retried. I cannot see from the binary whether it does; the
  vendor documents the field as the channel for gate codes, and the only code the binary
  itself names is `credits_required`. The failure mode is a withheld retry (a §6 row the
  human re-runs), never a promoted one. The alternative (ignore the field) keeps retrying
  a usage-credit gate on an untyped `rate_limit`, and the long-context one re-does up to
  200K tokens of work per retry. If the human prefers the other trade, drop the two
  `…_code` names from `_CLAUDE_CAUSE_FIELDS` (`progress.py:778`) and the three tests that
  pin them.
- **`no_response` is retried.** The vendor stamps it `server_error` and its own rules retry
  that kind; its text names a proxy only conditionally ("If a proxy … holds responses").
- **An unstamped report is not transient even with a typed cause.** No `error` kind means
  the record did not come through the vendor's mapper the normal way; criterion (ii).
- **A direct child that exits 129-192 reads as a signal death.** Only withholds a retry.
  I know of no CLI that uses that range for a transient startup failure.

## Consequences to state (not widened)

- **#537 makes the builder spend this retry set.** An 18-minute builder that ends on its
  own `server_error` report is now re-invoked up to twice more, each time with #537's
  residue notice. On a real outage that can triple the cost of the most expensive leaf.
  Resuming the CLI session instead of a fresh re-invoke is out of scope; a fresh re-invoke
  is the accepted first cut.
- **A signal death gets one attempt**, whether the leaf emitted anything or not, so a
  memory-capped leaf is not re-run into the same cap. What to do with it beyond that is
  still #510's question.
- **`rate_limit` covers usage-quota stops too** (the untyped "resets 5pm" kind). A retry
  hits the limit on its first request, so each extra attempt is cheap.

## Alternatives ruled out, with cost

- **Carry the verdict on a new `LeafError` field or a fourth return value** instead of
  folding it into `produced`. That needs `_invoke`'s `raise` and `LeafError.__init__`
  changed, which is outside "leaves.py strings, comments and the `transient` property
  only". A 4-tuple return would also change every 3-tuple unpack of `run_with_heartbeat`:
  21 call sites across `src/` and `tests/` (`grep -c "run_with_heartbeat("` minus the def).
- **Keep the signal rule in `progress`** (report `produced=True` on a signal death). Then
  `produced` would say "did work" for a leaf that emitted nothing, and the manner-of-kill
  rule would live beside the stream verdict instead of on the returncode the property
  already holds. The property-side check is one line and covers both shapes.
- **Special-case only `rate_limit` + typed cause** (the literal reading of item 1). About
  the same code, but it keeps retrying `server_error` + `tls_untrusted_ca`, which fails the
  same way every time.
- **Keep iteration 1's broad regex and add a deny-list** (for example "not if
  `invalid_request_error` appears"). A deny-list keeps the false positives it does not
  list; anchoring on the leading status removes the whole class.
- **Read the `LeafError.output` text to classify.** That is prose the leaf's stderr can
  forge. Ruled out by the invariant.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** The project's C4 script (`engine/scripts/run-verify.sh`) reverts
  only the production hunks and re-runs every touched test file. Red leg on the final
  patch: new file 40 failures (subtests counted) out of 52 tests, `test_leaf_status` 2 of
  15, `test_terminal_error_retention` 3 of 34, `test_builder_retry` 11/11 green (docstring
  only). Zero `ERROR:` lines — every red is an assertion, none an import or crash. The new
  file imports only API that existed before the patch. Verdict: `PDCA-EVIDENCE: C4 PASS —
  red without the fix, green with it`.
- **(b) Production path? Yes.** Every case runs a real child process (a Python stub) through
  `leaves._invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat`; the builder
  case goes through `leaves.do_build`; the §6 case through `_failure_class`,
  `_review_unavailable` and `assemble._items_from_artifact`. No mock of the classifier, no
  copy of it. C5 (`run-prod-path.py`) confirms the new file imports `pdca_harness`.
- **(c) Fixture includes the fault? Yes, with one caveat.** The stub really emits the
  marked report and exits 1. SIGKILL and SIGTERM are really delivered (`os.kill`; rc -9 /
  -15). The 137 case runs behind a real `sh -c` wrapper that outlives the killed child.
  Both observed death records (stream and transcript spelling) are replayed after inline
  work. Caveat: no real `claude` CLI and no real cgroup OOM kill. `--scope` execs the leaf
  as a direct child, so a real OOM kill surfaces as the same -9 the stub produces.

**Mutation check.** 49 mutants, each run against the new test file alone; all 49 killed,
on the final code. They include the three round-3 survivors the brief names (M01 `user`
out of the work set, M02 empty status set, M03 the `subtype == "success"` guard), the
sign-off's regex mutant (M17 "any text not containing `Unexpected`"), each typed-cause
field, each regex arm, each status in the set, the 5xx range, both signal spellings, the
128 boundary, the exit-0 and timeout folds, the precedence gate, the clearing rule, both
sub-agent checks, the unstamped check, both `isinstance` guards (they keep the drain alive
on malformed input), and reverting each of the three operator-facing strings. The runner
and its log are in the worktree's ignored `.cache/pdca-539-scratch/` (`mutants.py`,
`mutants-final.log`).

## Runs

- The four touched test files: 112 tests OK (with `test_leaf_resilience.py`: 117 OK).
- C4 gate script on the final patch: PASS (above).
- T3 runner (`engine/scripts/run-suite.sh`): root suite 24 OK, driver suite 2033 OK with 2
  skips, both pre-existing and unrelated.
- T2 runner (`engine/scripts/run-docs-check.sh`): docs lint clean, site render + link
  audit clean.
- C5 runner (`engine/scripts/run-prod-path.py`): the added test imports `pdca_harness`.
- `git diff --check`: clean. The target has no formatter, linter or pre-commit hook
  configured (no `.pre-commit-config.yaml`, no ruff/black/flake8 config; CI runs the test
  suites and the docs check). Only the DCO sign-off applies, at commit time.
- `patch.diff` is 95,974 bytes, 8 files. Under the instance's size signal (`patch_kb =
  125`). The new test file is 677 lines of that.

## Housekeeping

I wrote one gate log outside the harness roots by mistake: `/tmp/claude-1000/c4-539.log`
(the first C4 run). Nothing reads it. I cannot delete files, so it is left in place. Every
later log went into the worktree's ignored `.cache/pdca-539-scratch/`.
