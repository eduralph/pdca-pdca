# Adversarial review — issue 506 (advisory, non-gating)

**Evidence re-run, independently.** I reverted `progress.py` / `leaves.py` / `assemble.py` to
the base in a scratch copy, kept every `template/tests/*` hunk, and got **13 failures / 20**;
with the fix, **20/20 green**, and the whole template suite is **1773 tests OK**. The red is
genuine, it runs the real `_invoke_leaf_resilient → _invoke → progress.run_with_heartbeat →
subprocess` path (no mock between the child's bytes and the assertion), and the pinned
`tests/fixtures/claude_api_error_death.*.jsonl` is a real vendor record, not a synthesised
shape. C4's `pass` is warranted. What follows is what the red→green does **not** cover.

- **NEEDS-HUMAN — the widened classification newly exposes the reviewer/advisory leaves to
  the very residue hazard the carry-forward called out for the builder, and a prompt note
  cannot close it.** `_BUILD_RETRY_NOTE` is passed only at `template/src/pdca_harness/leaves.py:1934`;
  the three pre-existing call sites — `leaves.py:2618` (reviewer), `:2952` (advisory),
  `:3254` (plan advisory) — pass no `retry_note`, and their sandbox is not reset between
  attempts (`leaves.py:712-741` clears only the error log). Before this patch those leaves
  were retried **only when they produced nothing**, so there was never residue; the patch
  makes "worked for minutes, then died" retryable, which is exactly the case that leaves a
  half-written artifact behind. Measured through the real wrapper: a reviewer that writes a
  truncated `check-review.md` and then emits the pinned API-error event, whose attempt 2
  sees the file and exits 0, makes `_invoke_leaf_resilient` return `None` — and
  `leaves.py:2629-2632` then `shutil.copy2`s `'# Check review\n\n## 1. C1 Spec -- PASS\n(truncated mid-'`
  into the bundle as the reviewer's verdict. Note the harvest is `if produced.exists()`,
  unconditional on *which* attempt wrote it, so even a retry that writes nothing at all
  harvests attempt 1's fragment: a `retry_note` at those three sites is necessary but not
  sufficient, which is why this is a scope call rather than a straight rebuild.

- **NEEDS-HUMAN [impl] — the `result`-event branch silently overwrites the incident's own
  transient verdict, so the fix can fail on the very death it was built for.**
  `progress.py:186` is last-writer-wins (`terminal.update(text=text, transient=transient)`),
  and `progress.py:529` lets a terminal `result` event re-write it. Measured through the
  production path: `assistant(work)` → `assistant{is_api_error_message, error:"server_error",
  "API Error: Connection lost mid-response…"}` → `result{subtype:"error_during_execution",
  is_error:true, result:"Execution error"}` → **`transient=False`, 1 invocation** — not
  retried, and the incident stays unfixed with the suite green (precisely carry-forward
  defect #4's shape). This contradicts the patch's own reasoning: `progress.py:401-403`
  excludes `result` from `_WORK_EVENT_TYPES` *because* "a `result` event is the session's
  wrap-up", yet the same wrap-up event is allowed to re-classify the death. `result` is
  already modelled as a normal claude terminal event elsewhere (`_SESSION_EVENT_TYPES`,
  `progress.py:401`; `tests/test_progress.py:109`), and no fixture pins what stdout emits
  *after* the assistant record — `tests/fixtures/README.md` itself says the transcript's next
  line is CLI bookkeeping, not a stream event. Suggested: make a transient report sticky
  unless real work follows, rather than overwritable by the wrap-up.

- **NEEDS-HUMAN [impl] — the rejected "too broad" arm survives, relocated into the
  `result` branch.** The assistant branch was correctly re-anchored on the vendor's
  `is_api_error_message` mark (`progress.py:520`), but `progress.py:529-535` is gated only on
  `is_error` + `subtype != "success"` and then runs the same wide `_TRANSIENT_CAUSE_RE` over
  free prose from `result` / `error` / `errors`. Measured through `do_build`'s real path: a
  builder whose terminal result reads `"Build failed: the integration test timed out waiting
  for the fixture server"` → `transient=True`, **3 builder invocations**; likewise
  `"2 tests failed: expected 500, got 404 in test_api.py"` → `transient=True`, 3 invocations.
  That is the same class of defect the previous iteration was rejected for ("re-runs the
  builder 3x on a genuine test failure"), and the two new precision tests
  (`tests/test_leaf_resilience.py:308`, `:318`) only exercise the *assistant* branch, so
  neither would ever catch it.

- **NEEDS-HUMAN [impl] — the entire `result` branch is unpinned production code.** `is_error`
  appears in no file under `template/tests/`; no added stub emits a `result` event. Mutation:
  disabling `progress.py:529` outright leaves `test_leaf_resilience` + `test_progress` +
  `test_build_error_log` (63 tests) **green**. So the loosest classifier in the patch — and
  the one that can reverse the correct verdict (finding above) — carries no test at all, and
  `_claude_result_texts`' claim (`progress.py:548-550`) that an `errors` list is "the shape an
  `error_during_execution` result uses" is asserted, never observed.

- **NEEDS-HUMAN [impl] — the retry prompt points the builder at a file that does not exist
  yet.** `_BUILD_RETRY_NOTE` (`leaves.py:1866`) tells the retried builder its predecessor's
  "own account of the death is in `build.error.log` in the bundle directory", but
  `_invoke_leaf_resilient` unlinks that file at `leaves.py:712` and writes the accumulated
  records only *after* the loop (`leaves.py:741`). Instrumented the stub leaf to stat the path
  from inside the child: `attempt 1: build.error.log-exists=False / attempt 2: False /
  attempt 3: False`. `tests/test_leaf_resilience.py:450` asserts only that the strings "retry
  notice" and "incomplete residue" are in the prompt, so it passes over the false instruction.
  Fix by flushing `"".join(records)` before each backoff sleep (which also survives a
  SIGKILLed run) or by dropping the sentence.

- **NEEDS-HUMAN [impl] — the "read the vendor's verdict, not the prose" claim is not what the
  tests pin.** Mutations that survive with all 63 tests green: `_CLAUDE_TRANSIENT_ERROR_KINDS`
  → `frozenset()` (`progress.py:451`), and `_transient_status` → `return False`
  (`progress.py:561-563`). Every transient case in the suite is rescued by the prose regex
  instead, so the vendor-kind and `api_error_status` paths the fixture README presents as the
  design's core are unexercised. Consequence: criterion (i)'s "a mid-session **rate-limit**
  rejection" has no test — an `is_api_error_message` event with `error:"rate_limit"` and text
  like "Claude is unable to respond to this request." is classified only by the untested
  `kinds` path, and a future edit that drops `rate_limit` or `overloaded` goes unnoticed.

**Attempted and could not refute:** the red→green itself (reproduced independently, 13 red /
20 green); "the test exercises a copy, not production" (it does not — real subprocess, real
`do_build`); the `capture` contract regression (skipping the append under `capture` is correct
and pinned, and `gates.py:559` / `publish.py:833` / `leaves.py:786` all use `capture=True`
without `stream_json`, so no gate evidence line can pick up the appended prose); the stale-log
regression I expected from `_has_content` (`leaves.py:1812`) — `do_build` already unlinks at
`leaves.py:1786`, so a setup failure still writes; the dropped `memory_log=` kwarg
(`_memory_log_for` derives the identical `build.memory.jsonl`); the drain-thread race on
`terminal` (readers are joined at `progress.py:283` before it is read, and `dict.update` is
atomic); a stream-less family still reporting substantive (`leaves.py:678`); and
`_transient_do_death`'s "still reads PLANNED" branch, which `state.py:203-211` confirms is
true even when only `build-notes.md` is left behind.
