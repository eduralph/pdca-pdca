# Result — issue 506 / a-transient-leaf-death-is-explained-and-retried

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A mid-response API failure inside a leaf burns the whole attempt and leaves a
  post-mortem artifact that explains nothing. Observed downstream (getwyrd/wyrd-pdca, bundle
  `results/issue_717/`): the escalated builder (opus, `--effort max`, the #135 ladder tier) ran
  ~18 minutes in auto-iterate, the API connection dropped mid-response, the CLI exited 1, and
  `build.error.log` recorded only
  `----- attempt 1 — exit 1 ----- (no output captured) LeafError: Command '['claude', '-p', …]'
  returned non-zero exit status 1.` The cause was visible only in the CLI's own session
  transcript under `~/.claude/projects/`:
  `2026-08-12T00:29:33 TEXT: API Error: Connection lost mid-response.` An identical re-run
  minutes later succeeded. Three weaknesses compound, all verified on the target base:
  * **The stream's own error text is discarded.** `progress.run_with_heartbeat` drains stdout
    for a session flag and a tool label only (`template/src/pdca_harness/progress.py:146-158`)
    and keeps a bounded **stderr** tail (`:143`, `:163-171`); with `capture` off, `output` is
    that stderr tail alone (`:255`). The API-error line arrives as a stream *text* event on
    stdout, so it is displayed and dropped, and `_format_leaf_attempt`
    (`template/src/pdca_harness/leaves.py:723-730`) falls back to `(no output captured)`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:154-155`, `_is_session_event`
    at `:365-377`; `leaves.py:664-670`). An 18-minute session that then dies mid-response
    produced plenty, so it is classified substantive — correctly by that rule, wrongly for this
    cause.
  * **The builder is not on the resilient path at all.** `_invoke_leaf_resilient`
    (`leaves.py:673-720`: bounded retry with backoff + a per-attempt error log) is used by the
    reviewer (`:2507`), the advisory (`:2840`) and the plan advisory (`:3142`). `do_build` calls
    plain `_invoke` (`leaves.py:1825`, via `_do_build_command`), so **no** builder failure is
    ever retried — and the builder is the leaf where an attempt is most expensive, and the
    escalation ladder's deep tiers (opus/max) are exactly where sessions run longest.
  On the current base the run itself no longer dies of a traceback on either CLI path —
  `flow._advance_one` wraps the beat in `_isolate` (`flow.py:459`) and the batch auto-iterate is
  wrapped at `:1333` — so what survives of the report's third symptom is the *message*: the
  operator gets `build/check failed (LeafError: Command '[…]' returned non-zero exit status 1)`,
  which names an argv and an exit status and nothing about why. (`flow_one`, the library-only
  route, still propagates — deliberately out of scope below.)
- Success criterion: With the patch:
  (i) a leaf whose stream carries a **terminal transient error event** — a lost/interrupted
  connection, an overload or 5xx, a mid-session rate-limit rejection — and then exits non-zero is
  classified **transient**, whether or not it produced substantive work first, while a leaf that
  fails for a substantive reason is still classified substantive and is **not** retried;
  (ii) that classification actually reaches Do: a transient builder death is retried, bounded,
  with backoff, instead of burning the attempt;
  (iii) `build.error.log` for such a death carries the leaf's **own terminal error text** rather
  than `(no output captured)`, so the post-mortem explains the failure without opening
  `~/.claude/projects/`;
  (iv) when the bounded retries are exhausted, what the operator reads names the transient
  classification and how to resume, rather than an argv and an exit status alone;
  (v) nothing else changes: a leaf that succeeds is spawned and reported exactly as today, the
  existing reviewer/advisory resilience contract (attempt count, backoff, per-attempt records,
  the `transient` attribute) still holds, a stream-less family still reports substantive
  (`leaves.py:664-669`), and the memory-telemetry post-mortem (#420) still rides `output` into
  the same log.
  Demonstrable by C4-verify: the offline suite spawns a stub "leaf" that is a Python interpreter
  emitting chosen stream events and exiting non-zero, so (i)-(iv) are assertions over an
  invocation counter and the error log's bytes.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Leaf-death classification and retention on the spawn path shared by every leaf, and
  putting the builder on the resilient path: read the terminal transient signal out of the stream
  the driver already parses, keep that text so it reaches the leaf's `*.error.log`, and let Do
  retry on it, bounded — with the exhausted-retry message naming the cause and the resume.
  **Out of scope:** resuming a long session via the CLI's own session-resume (a fresh re-invoke
  is an acceptable first cut, and for this incident nothing would have been lost either way — but
  say so in `build-notes.md` so the human can weigh it); the gate-side transient (issue #371 —
  one transient red on a *gating gate row* is the same argument in a different layer, and is its
  own slice); a leaf **signal-death** under the memory scope (issue #510 states explicitly that a
  SIGKILLed leaf "is neither #506's transient nor #421's preflight" — do not fold it in here);
  `flow._isolate`'s containment contract and the `flow_one` library route's propagation (a
  different, deliberate design point — `flow.py:302-306` documents why the single-issue path has
  no `_isolate` there); the memory-telemetry post-mortem (#420), which must keep working
  unchanged; any new `pdca.toml` knob (reuse the existing attempts/backoff defaults rather than
  adding configuration this slice has no evidence to tune).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Task under review: retain and classify a leaf's terminal transient API failure, retry a failed builder with bounded backoff, and give the operator an attributable recovery path.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary distinguishes terminal transient infrastructure deaths from substantive failures and keeps session-resume, signal death, and new configuration out of scope. |
| C2 Reproduction (red pre-fix) | PASS | Reverting only the three production files with the new tests/fixtures retained produced 13 focused failures, including retry count, diagnostic retention, and recovery-message assertions (`template/tests/test_leaf_resilience.py:268`). |
| C3 Change | PASS | The patch stays within stream classification/retention and the shared resilient invocation path, so the requested behavior changes without adding a configuration surface (`template/src/pdca_harness/progress.py:491`, `template/src/pdca_harness/leaves.py:1931`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Confirm a live Claude `--output-format stream-json` connection death carries the marked assistant event — the independent Python red→green is genuine (13 red, 32 green), but the stdout fixture is derived rather than captured, so the real vendor topology remains unexercised (`template/tests/fixtures/README.md:36`). |
| C5 Causal adequacy | PASS | The classifier keys on the CLI's explicit API-error mark and kind, while substantive prose and quoted incident text remain non-transient, so it replaces the faulty output proxy rather than guarding a capability side effect (`template/src/pdca_harness/progress.py:434`, `template/tests/test_leaf_resilience.py:307`). |
| T1 Structure | PASS | The terminal classifier is colocated with the stream parser, the builder reuses the existing resilience wrapper, and vendor bytes are isolated in a provenance-recorded fixture directory (`template/src/pdca_harness/progress.py:425`, `template/tests/fixtures/README.md:1`). |
| T2 Shape | PASS | Independent diff/compile checks and both frozen docs/site audits are clean; the fixture documentation explicitly separates observed transcript bytes from derived stream bytes (`template/tests/fixtures/README.md:7`, `template/tests/fixtures/README.md:36`). |
| T3 Runtime | PASS | The independent full offline test discovery exited 0, and focused subprocess-path cases prove transient retries, substantive non-retries, bounded attempt logs, and honest partial-patch recovery messaging (`template/tests/test_leaf_resilience.py:440`, `template/tests/test_leaf_resilience.py:470`). |
| T4 Contribution | N/A | Contribution artifacts do not exist during Check by design; the frozen row says the substantive PR-description audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Choose landing/rebase ownership with open PR #524 — upstream `main` exactly matches this patch's base and no affected-path closed PR was rejected, but #524 also inserts immediately after `_format_leaf_attempt`, so parallel integration can conflict despite separate semantics (`template/src/pdca_harness/leaves.py:758`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether fresh retries over a dirty worktree, governed by a prompt warning rather than cleanup or session resume, are operationally fit for long expensive builders — mistaken residue can otherwise be accepted as a completed attempt (`template/src/pdca_harness/leaves.py:1856`). |

### Advisory — adversary

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

### Advisory — code-review

# Advisory code review — issue #506 (iteration 2)

Second lens: correctness bugs the patch introduces, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (already carries the patch applied — `leaves.py` /
`progress.py` line numbers below are the post-patch target, matching `patch.diff`'s new
hunks).

The mechanism itself is sound on this reading: the retry-note / worktree-residue wiring
(`leaves.py:1855-1872`, `:1931-1934`), the `_has_content` guard so `do_build`'s outer
capture never clobbers the resilient wrapper's per-attempt log (`leaves.py:758-765`,
`:1812-1813`), the `capture`-exclusivity guard on the stream append
(`progress.py:409-415`), and the `memory_log=` kwarg drop (now derived, matching the
other three call sites) all read correctly against the iteration-1 carry-forward that
raised them. Two things worth a second look:

- NEEDS-HUMAN [impl] — `progress.py:529-535` (`_terminal_error`'s `result`-event branch).
  The iteration-1 review's "too broad" finding was fixed for the `assistant` branch by
  gating classification on a CLI-set marker (`is_api_error_message`/`isApiErrorMessage`,
  `progress.py:520-521`) before ever running `_TRANSIENT_CAUSE_RE` against free text — so
  a substantive failure whose text merely *reads like* an infra error (`_SUBSTANTIVE_LEAD`,
  `_QUOTES_THE_INCIDENT`) is correctly left un-marked and the regex never runs on it. The
  `result`-event branch has no equivalent CLI marker to gate on: any `result` event with
  `is_error` true and `subtype != "success"` — which covers non-infra endings too
  (`error_max_turns`, a permission/guardrail refusal, a tool's own execution error) — has
  its `result`/`error`/`errors` text run straight through the same broad
  `_TRANSIENT_CAUSE_RE` (`progress.py:533-534`), with only `is_error`/subtype as the gate.
  A tool failure whose own text happens to mention "timeout", echoes a "500"/"429" it
  received from *its own* subject matter, or reads "connection refused" from an unrelated
  log it was inspecting, would be reclassified transient and the builder retried 3× on a
  substantive death — reproducing the exact failure mode iteration 1 flagged, in the one
  shape iteration 1's fix didn't reach. Nothing in the appended suite exercises this
  branch at all: every stub script (`_TERMINAL_TRANSIENT`, `_INCIDENT_REPLAY`,
  `_UNCLASSIFIED_CAUSE`, `_PERMANENT_API_ERROR`, `_SUBSTANTIVE_LEAD_WORD`,
  `_QUOTES_THE_INCIDENT`, `_RECOVERED_THEN_FAILED` in
  `template/tests/test_leaf_resilience.py:34-40,834-887`) emits only `assistant` events
  via `event()`/`api_error()`; no test ever synthesises or replays a `result` event. The
  `assistant` shape now has two pinned-fixture tests plus two precision tests
  (`test_a_substantive_failure_opening_with_the_lead_word_is_not_retried`,
  `test_a_leaf_quoting_the_incident_line_is_not_retried`); the `result` shape has zero —
  so its precision is asserted nowhere, and per the brief's own falsifiability standard
  ("the classifier's contract with the real vendor stream is asserted, never observed")
  this half of it still isn't. Fixable by iterating: either add a precision test for a
  substantive `result`-event ending (and tighten the gate — e.g. restrict to the
  documented `error_during_execution` subtype plus `api_error_status`, rather than any
  non-success `is_error` result) or narrow the source of `texts` to a field the CLI itself
  marks as an infra cause.

- `progress.py:181-191` (the reader-thread loop) — `_is_session_event`, `_terminal_error`,
  `_is_work_event` and `_stream_tool_label` are four independent classifiers over the same
  `line`, and each does its own `json.loads(line)` (`progress.py:415`, `:515`, `:585`,
  `:595`). Pre-patch this loop already parsed each claude stream line twice (session +
  tool label); this patch adds a third unconditional parse (`_terminal_error`, called on
  every line regardless of family before its own `fmt` early-return) and, while a terminal
  report is pending, a fourth (`_is_work_event`). That's up to double the JSON-parsing
  work per line for the family (claude) this patch is actually about, in exactly the
  scenario the brief motivates the fix with — a long, event-heavy session (the incident
  ran ~18 minutes). Not a correctness bug (each function degrades safely and independently
  on a bad parse), but a straightforward reuse opportunity the "same shape as
  `_is_session_event`" composition cue (brief, Citations expected) invites: parse the line
  once per iteration and hand the same `ev` dict to all four classifiers, the way
  `_is_session_event`/`_terminal_error`/`_is_work_event`/`_stream_tool_label` already
  share the "best-effort JSON, degrade to today" *shape* but not the parse itself. Minor;
  flagging as an efficiency nit rather than NEEDS-HUMAN since it changes no observable
  behavior and nothing in the brief's scope requires closing it.

No other correctness issues found: the `_transient_do_death` branch selection
(`leaves.py:1841-1852`) is exercised by both the "no residue" and "partial patch.diff"
legs, the retry-note-from-attempt-2 wiring is asserted against the actual stdin the retried
child receives, and `_invoke_leaf_resilient`'s new `error_log.write_text` is wrapped in its
own `try/except OSError` (`leaves.py:740-744`) so a capture failure can't mask the leaf's
real exception — matching the "capture must never mask the failure" rule this bundle
otherwise reuses throughout.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Confirm a live Claude `--output-format stream-json` connection death carries the marked assistant event — the independent Python red→green is genuine (13 red, 32 green), but the stdout fixture is derived rather than captured, so the real vendor topology remains unexercised (`template/tests/fixtures/README.md:36`).
- [ ] T5 Judgment — Choose landing/rebase ownership with open PR #524 — upstream `main` exactly matches this patch's base and no affected-path closed PR was rejected, but #524 also inserts immediately after `_format_leaf_attempt`, so parallel integration can conflict despite separate semantics (`template/src/pdca_harness/leaves.py:758`).
- [ ] Validation — fitness-to-purpose — Decide whether fresh retries over a dirty worktree, governed by a prompt warning rather than cleanup or session resume, are operationally fit for long expensive builders — mistaken residue can otherwise be accepted as a completed attempt (`template/src/pdca_harness/leaves.py:1856`).
- [ ] `progress.py:529-535` (`_terminal_error`'s `result`-event branch).
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- Iteration delta (if iterating): Rejected on the findings — both advisory lenses converged independently on the same place. The core mechanism is SOUND and independently reproduced (13 red / 20 green through the real subprocess path, 1773 template tests OK, pinned real vendor transcript), and iteration 1's four defects are genuinely fixed: the matcher is re-anchored on the CLI's own `is_api_error_message` marker, the resume message is honest about a partial patch.diff, the retry note warns about residue, and the vendor contract is now observed rather than synthesised. KEEP ALL OF THAT — also the `_has_content` guard (leaves.py:758-765, :1812), the `capture`-exclusivity guard on the stream append (progress.py:409-415), and the derived `memory_log`. What must change is the `result`-event branch, `progress.py:529-535`. Three defects, all measured through the production path: 1. It silently overwrites the incident's own correct verdict. `terminal.update(...)` at progress.py:186 is last-writer-wins, so assistant(work) -> assistant{is_api_error_message, "Connection lost mid-response"} -> result{is_error, subtype:"error_during_execution", result:"Execution error"} yields transient=False and ONE invocation: the fix fails on the exact death it was built for, with the suite green. This contradicts the patch's own reasoning — progress.py:401-403 excludes `result` from `_WORK_EVENT_TYPES` because it is "the session's wrap-up", yet the same wrap-up is allowed to re-classify the death. Make a transient report STICKY unless real work follows it, rather than overwritable by the wrap-up. 2. The "too broad" arm iteration 1 was rejected for survives, relocated into this branch. It is gated only on `is_error` + `subtype != "success"` and then runs the wide `_TRANSIENT_CAUSE_RE` over free prose from `result`/`error`/`errors`. Measured through do_build: "Build failed: the integration test timed out waiting for the fixture server" -> 3 builder invocations; "2 tests failed: expected 500, got 404 in test_api.py" -> 3 invocations. Non-infra endings (error_max_turns, a guardrail refusal, a tool's own execution error, a log the leaf was merely reading) all reach it. Fix by keying on a field the CLI itself marks as an infra cause — e.g. restrict to the documented `error_during_execution` subtype plus `api_error_status` — or drop the branch; do not leave classification resting on prose in the one shape iteration 1's fix didn't reach. 3. The branch is entirely unpinned. `is_error` appears in no file under `template/tests/`, no stub emits a `result` event, and disabling progress.py:529 outright leaves 63 tests green. Whatever survives of this branch needs precision tests for a SUBSTANTIVE `result`-event ending, the mirror of the two assistant-branch precision tests. Two further items to close in the same rebuild: 4. The retry prompt points at a file that does not exist. `_BUILD_RETRY_NOTE` (leaves.py:1866) tells the retried builder its predecessor's account "is in build.error.log in the bundle directory", but `_invoke_leaf_resilient` unlinks it at leaves.py:712 and writes the records only after the loop at :741 — instrumented from inside the child, attempts 1/2/3 all see exists=False. Flush "".join(records) before each backoff sleep (which also survives a SIGKILLed run) or drop the sentence. Note the test at test_leaf_resilience.py:450 asserts only that the strings are present, so it passes over the false instruction. 5. The "read the vendor's verdict, not the prose" claim is not what the tests pin: both `_CLAUDE_TRANSIENT_ERROR_KINDS -> frozenset()` (progress.py:451) and `_transient_status -> return False` (:561-563) survive with 63 tests green — every transient case is rescued by the prose regex instead. Consequence: criterion (i)'s promised mid-session RATE-LIMIT rejection has no test at all. Pin the kind and `api_error_status` paths directly, with text the regex would not rescue. SCOPE — flagged, do NOT expand the slice to it. Widening the classification makes the reviewer/advisory leaves retryable after they have produced work, which they never were before, and their harvest is `if produced.exists()` (leaves.py:2629-2632) — unconditional on which attempt wrote it — so a truncated check-review.md from a dead attempt 1 can be copied into the bundle as the reviewer's verdict. Passing `retry_note` at leaves.py:2618/:2952/:3254 is necessary but not sufficient, since the harvest itself is attempt-blind. If the rebuild concludes this cannot be closed within the slice, say so in build-notes.md and leave it for a separate issue rather than growing this one. Not re-litigated: C4's derived stream fixture, the PR #524 rebase ownership, and the dirty-worktree fitness question remain open §6 items for the next sign-off; the disabled plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
