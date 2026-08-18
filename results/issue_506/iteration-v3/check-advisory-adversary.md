# Adversarial review — issue 506 (advisory, non-gating)

Re-ran the asserted red→green independently on `$PDCA_TARGET`: red leg (production reverted,
tests kept) **26 failures**, green leg **29 tests OK**, full template suite **1782 OK
(2 skipped)**. Then mutation-tested the load-bearing hunks — `_CLAUDE_TRANSIENT_ERROR_KINDS
→ frozenset()`, `_transient_status → False`, sticky-off, `_is_work_event → False`, the
result-subtype gate, the whole result branch, the cause regex, the `is_api_error_message`
gate, `produced and not terminal["transient"]`, the retention append, the `capture` guard,
`_write_attempt_records`, `retry_note`, `_has_content`, `_transient_do_death`,
success-unlink — **16/16 caught**. The tests are not tautological and the evidence is real.
What follows is what I could still break, grounded where possible in the shipped vendor
binary (claude-code 2.1.233, the build the fixtures README itself cites).

- NEEDS-HUMAN [impl] — **A real mid-response connection loss is classified SUBSTANTIVE and the
  builder is not retried when the CLI's error kind is `unknown`.** `progress.py:452` limits the
  machine-marked kinds to `{server_error, overloaded, rate_limit}` and everything else falls to
  `_TRANSIENT_CAUSE_RE` (`progress.py:468`). But claude-code's API-error mapper ends
  `if (e instanceof Error) return Yd({content: \`${Uw}: ${e.message}\`, error:"unknown"})` with
  `Uw="API Error"`, reached whenever `lj(e)` finds no cause code in `sie`/`gde` — and **neither
  set contains any `UND_ERR_*` code**, so Node/undici's canonical mid-response stream abort
  (`TypeError: terminated`, cause `SocketError{code:"UND_ERR_SOCKET"}`) surfaces as
  `{"type":"assistant","is_api_error_message":true,"error":"unknown", … "API Error: terminated"}`.
  Measured through the production path (`_invoke_leaf_resilient` → `_invoke` → `progress` →
  subprocess): `transient=False`, **1 invocation**, versus `transient=True`, 3 invocations for the
  pinned incident text. `other side closed` and `stream disconnected` fail the same way. That is
  criterion (i)'s "a lost/interrupted connection" left unretried. Fixing it is safe in the
  direction iteration 1 was rejected for — the regex only ever runs on text the CLI itself marked
  (`progress.py:537`), so adding `terminated` / `other side closed` / `stream (closed|disconnected)`
  cannot re-open the false-positive arm. Note the patch's own `UND_ERR_[A-Z_]+` alternative
  (`progress.py:493`) is unreachable for this shape: the code is in the `cause`, never in the text.

- NEEDS-HUMAN [impl] — **The `result`-branch `api_error_status` arm is dead code against the real
  stream, and both tests that "pin" it construct an event the CLI cannot emit.**
  `progress.py:546` guards with `subtype != "success"` and `progress.py:551` then requires
  `subtype in {"error_during_execution"}` (`progress.py:459`) **plus** an `api_error_status`. In
  claude-code 2.1.233 the only result carrying that field is
  `variant:{subtype:"success", api_error_status: gt, result: Ze?Dt:qe}` with `is_error: Ze` — the
  `error_during_execution` / `error_max_turns` variants carry `errors:[…]` and nothing else. The
  CLI asserts this itself in its own telemetry: `api_error_status: ol.subtype==="success" ? … :
  void 0`. So the guard excludes exactly the shape that carries the field, and the arm requires a
  combination that never occurs. `tests/test_leaf_resilience.py:461` (`error_during_execution` +
  `result="Execution error"` + `api_error_status: 503`) and `:473` (`error_max_turns` +
  `api_error_status`) are both impossible records — the "synthesised the shape it then parses"
  defect the round-2 sign-off rejected, relocated into the one branch the vendor fixture never
  covered. Either key the arm on the CLI's actual API-error ending (`subtype == "success" and
  is_error`, still machine-marked, still no prose matching) or delete it and say the wrap-up is
  retention-only — but do not leave a green test standing for an event that cannot exist.

- NEEDS-HUMAN [impl] — **The stickiness rationale cites an incident ending that was never
  observed.** `progress.py:558-560` states the incident's stream ends "work, the
  `is_api_error_message` report …, then the session's `result` wrap-up (`error_during_execution` /
  'Execution error')". Per the emitter, an api-error ending with no thrown/aborted turn produces
  the **success** variant with the API-error text in `result`; the `error_during_execution` variant
  is emitted only for a throw or an aborted turn and then carries
  `errors:["[ede_diagnostic] turn aborted (…) stop_reason=…"]` — "Execution error" appears
  nowhere, and the pinned transcript (`tests/fixtures/README.md`, line 345 = last event) contains
  no result record at all. The sticky rule itself survives my attack (the aborted-turn variant
  genuinely can follow the api-error message, and stickiness is what saves it), so this is the
  comment and `_WRAP_UP` (`tests/test_leaf_resilience.py:85`, used at `:208`) being asserted rather than
  observed — the exact standard the fixture was added to enforce.

- NEEDS-HUMAN — **Widening "transient" makes the reviewer/advisory leaves retryable after they
  have produced work, and only the builder got the residue mitigation.** `retry_note` is passed at
  `leaves.py:1957` and at no other call site (`:2641`, `:2975`, `:3277`); the reviewer's sandbox is
  one `TemporaryDirectory` for the whole call (`leaves.py:2597`-region), so attempts 2–3 run over
  attempt 1's files, and the harvest is attempt-blind — `leaves.py:2653-2655`
  (`if produced.exists(): copy`) and `leaves.py:2986-2987`. Concrete case: attempt 1 writes half a
  `check-review.md`, dies on a marked API error, attempt 2 exits 0 having decided the file is
  already there → the truncated verdict is copied into the bundle as the reviewer's answer. This
  is the scope item the previous sign-off flagged and deferred; the patch adds no mitigation and
  no in-code marker at those three sites, so the human decision (accept as a separate issue vs.
  close it here) is still open and now has a live path.

- The C5 row in `check-gates.json` is a **vacuous pass**: `result: "pass"` on the evidence
  "patch adds no new test file — nothing to assert", while the patch adds ~600 test lines and two
  fixtures. It corroborates nothing about the production path. (I checked the substance
  separately and it holds: the new cases drive a real `subprocess` through `_invoke` /
  `do_build`, with every asserted marker env-borne rather than argv-borne, so the
  `_format_leaf_attempt` argv-echo trap is genuinely avoided.)

**Attempted and could not refute.** (a) The "too broad" direction iteration 1 was rejected for —
I could not get substantive prose (`Error: … expected 500, got 404`, a verbatim quote of the
incident line, a blockquote, a result-event summary naming a timeout) to be read as infra: the
`is_api_error_message` mark gates it (`progress.py:537`). (b) The incident's own path — verified
the fixture derivation against the shipped emitters (`YEf` and the live `UXe` both emit
`error` and `is_api_error_message`, and the `Fje` content filter passes an api-error message), so
the assistant branch is grounded, not guessed. (c) `_memory_log_for` derives byte-identical
`build.memory.jsonl`; no other `run_with_heartbeat` caller reads the third return value
(`gates.py:559`, `publish.py:833`, `leaves.py:806` all discard it and pass `capture=True`);
leaves pass no `timeout`, so the retry cannot multiply a wall-clock bound. (d) `_has_content`
(`leaves.py:778`) genuinely stops `do_build` clobbering the wrapper's per-attempt records, and
`worktree.ensure` hard-resets a reused lane worktree (`worktree.py:377-384`), so
`_transient_do_death`'s "inputs are intact / re-drives Do from the top" is honest. (e) The
capture-exclusivity guard holds: every captured line still parses as JSON.
