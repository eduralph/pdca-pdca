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

Task: make terminal transient leaf failures attributable and retryable, including the Do builder, without retrying substantive failures.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable classification, bounded retry, retained diagnostics, exhausted-retry guidance, and unchanged substantive-failure behavior against the shared invocation contract (`template/src/pdca_harness/progress.py:54`, `template/src/pdca_harness/leaves.py:680`). |
| C2 Reproduction (red pre-fix) | PASS | With patched tests retained and production reverted, the focused suite independently failed 26 cases spanning terminal classification and Do retry, then passed after restoration (`template/tests/test_leaf_resilience.py:361`, `template/tests/test_leaf_resilience.py:639`). |
| C3 Change | NEEDS-HUMAN | Decide whether the shared reviewer/advisory residue risk may remain follow-up scope — retries reuse one sandbox and success harvests any existing artifact, so an interrupted attempt's partial verdict can be promoted (`template/src/pdca_harness/leaves.py:2641`, `template/src/pdca_harness/leaves.py:2653`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the derived stdout-stream fixture is an adequate substitute for a live Claude CLI/API death — independent stub red→green is real, but the actual vendor transport/event mapping was not exercised (`template/tests/fixtures/README.md:36`). |
| C5 Causal adequacy | PASS | The change reads the CLI-marked terminal failure and its machine-set kind/status at the stream boundary, retains its text, and clears it only when later real work proves recovery; it does not merely guard the builder call site (`template/src/pdca_harness/progress.py:435`, `template/src/pdca_harness/progress.py:537`, `template/src/pdca_harness/progress.py:556`). |
| T1 Structure | PASS | Classification remains beside the existing per-family stream parser and bounded retry reuses the established resilient wrapper, keeping responsibilities localized (`template/src/pdca_harness/progress.py:501`, `template/src/pdca_harness/leaves.py:680`). |
| T2 Shape | PASS | Independent `git diff --check` was clean, and both frozen docs/site audit logs show clean renders and links; no documentation-shape defect was found. |
| T3 Runtime | PASS | The independently run focused suite passed all 41 tests and the full offline discovery suite exited 0; frozen T3 evidence also records 1,782 driver tests plus 7 root tests green (`template/tests/test_leaf_resilience.py:360`, `template/tests/test_build_error_log.py:58`). |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; the frozen deferred row says the substantive contribution audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Decide whether the brief's prior-art account is sufficient — this disposable target has one synthetic base commit and no remotes, so merged history plus closed/rejected work cannot be mechanically confirmed here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the stub/derived-stream evidence and the accepted shared-leaf residue tradeoff fit production use — a wrong live event shape misses the incident, while stale partial review artifacts can affect sign-off (`template/tests/fixtures/README.md:36`, `template/src/pdca_harness/leaves.py:2653`). |

### Advisory — adversary

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

### Advisory — code-review

# Advisory code review — correctness & reuse/efficiency lens (issue #506)

## Findings

- **NEEDS-HUMAN — reviewer/advisory/plan-advisory harvest is attempt-blind, and this
  patch widens the retry surface that can trigger it** (`template/src/pdca_harness/leaves.py:2653-2654`,
  `:2973/:2986`, `:3275/:3287`). All three sandboxed leaves run every attempt of
  `_invoke_leaf_resilient` in the *same* `sandbox` tempdir, then simply check
  `if produced.exists(): copy` / `if out.exists(): copy` after the wrapper returns
  `None` (success) — with no record of *which* attempt wrote the file. Before this
  patch, a reviewer/advisory retry only ever fired on a true no-output invocation
  death, so a stale `check-review.md` from a prior attempt could not exist to be
  mis-harvested. This patch's widened transient classification (`progress._terminal_error`
  / `_note_terminal`) now also retries a leaf that already did real work and wrote a
  *partial* artifact before its terminal transient death — so a retried attempt that
  exits 0 without re-writing the file (e.g. it half-completes, or misreads the leftover
  artifact as "already done") will have its predecessor's partial `check-review.md` /
  `check-advisory-*.md` / `plan-advisory-*.md` silently copied into the bundle as the
  final verdict. This exact risk is called out explicitly in the brief's iteration-2
  sign-off notes ("SCOPE — flagged, do NOT expand the slice to it... if the rebuild
  concludes this cannot be closed within the slice, say so in build-notes.md and leave
  it for a separate issue") — build-notes.md is withheld from this lens, so a human
  should confirm it was actually recorded/tracked rather than silently dropped, since
  the vulnerability is real and now more reachable than before the patch.

- Minor efficiency/reuse nit — **redundant per-line JSON parsing in the stream drain
  hot path** (`template/src/pdca_harness/progress.py:182-194`). The drain loop already
  called `json.loads` twice per stream line before this patch (`_is_session_event`,
  `_stream_tool_label`); this patch adds `_terminal_error` (parses every line
  unconditionally) and, conditionally, `_is_work_event` (parses again) — up to 4
  independent `json.loads` calls on the same line, each with its own try/except and
  `isinstance(ev, dict)` guard. For the long streaming sessions this very issue is
  about (the incident cited an ~18-minute run), this is needless repeated work in the
  one loop that runs on every emitted stream event. A single `json.loads` per line,
  passed as a parsed dict to each classifier, would keep the same dispatch-by-`fmt`
  shape at a fraction of the cost. Not a correctness bug (best-effort try/except means
  behavior is unaffected either way), so not gating — worth a follow-up cleanup.

## Not flagged

- The sticky-`terminal` design (`progress._note_terminal`, `progress.py:592-610` in the
  diff) — where a transient report survives a later non-transient marked report unless
  real work intervenes — looked overbroad at first glance (it defeats *any* subsequent
  report, not just the `result` wrap-up that motivated it), but this is exactly the
  fix iteration 2's sign-off mandated ("Make a transient report STICKY unless real work
  follows it"), so it's treated as intentional, not a defect.
- `_do_build_command` no longer passes `memory_log=` explicitly, relying on
  `_memory_log_for` to derive `build.memory.jsonl` from `build.error.log` — verified
  against `_memory_log_for` (`leaves.py:368-377`): the derivation is correct and matches
  the other three call sites, closing the iteration-1 review note cleanly.
- `_invoke_leaf_resilient`'s per-attempt flush (`_write_attempt_records`, called before
  the backoff `time.sleep`) and the `_BUILD_RETRY_NOTE` pointer at `BUILD_ERROR_LOG` were
  re-verified against the code: the file is genuinely readable by the next attempt (and
  by a run killed mid-backoff), closing the iteration-2 "false instruction" defect.
- Ran `template/tests/test_leaf_resilience.py` locally against the target tree (29
  tests) — all green, exercising the real `_invoke` → `progress.run_with_heartbeat` →
  `subprocess` path with a stub leaf, not a mock of the classifier.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C3 Change — Decide whether the shared reviewer/advisory residue risk may remain follow-up scope — retries reuse one sandbox and success harvests any existing artifact, so an interrupted attempt's partial verdict can be promoted (`template/src/pdca_harness/leaves.py:2641`, `template/src/pdca_harness/leaves.py:2653`).
- [ ] C4 Verification (red→green) — Decide whether the derived stdout-stream fixture is an adequate substitute for a live Claude CLI/API death — independent stub red→green is real, but the actual vendor transport/event mapping was not exercised (`template/tests/fixtures/README.md:36`).
- [ ] T5 Judgment — Decide whether the brief's prior-art account is sufficient — this disposable target has one synthetic base commit and no remotes, so merged history plus closed/rejected work cannot be mechanically confirmed here.
- [ ] Validation — fitness-to-purpose — Decide whether the stub/derived-stream evidence and the accepted shared-leaf residue tradeoff fit production use — a wrong live event shape misses the incident, while stale partial review artifacts can affect sign-off (`template/tests/fixtures/README.md:36`, `template/src/pdca_harness/leaves.py:2653`).
- [ ] **A real mid-response connection loss is classified SUBSTANTIVE and the
- [ ] **The `result`-branch `api_error_status` arm is dead code against the real
- [ ] **The stickiness rationale cites an incident ending that was never
- [ ] **Widening "transient" makes the reviewer/advisory leaves retryable after they
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.
- [ ] size backstop — this slice is behaving oversized: patch is 86 KB (threshold 80 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Rejected on the adversary's three implementation findings — the core mechanism is SOUND and independently confirmed (red 26 / green 29, 1782 template tests OK, 16/16 mutations of the load-bearing hunks caught, pinned vendor transcript). KEEP ALL OF IT: the marker-anchored matcher on `is_api_error_message`, the sticky-transient rule (it survived the adversary's attack — the aborted-turn variant genuinely can follow the api-error message, and stickiness is what saves it), the per-attempt `_write_attempt_records` flush before the backoff sleep, the `_has_content` guard, the `capture`-exclusivity guard, and the derived `memory_log`. Three defects sit on top of it, all grounded in the shipped vendor binary (claude-code 2.1.233) and measured through the production path: 1. A real mid-response connection loss is classified SUBSTANTIVE and the builder is NOT retried when the CLI's error kind is `unknown` (progress.py:452, :468). claude-code's API-error mapper ends `return Yd({content: "API Error: " + e.message, error: "unknown"})` whenever no cause code is found in its `sie`/`gde` sets — and neither set contains any `UND_ERR_*` code, so Node/undici's canonical mid-response stream abort (`TypeError: terminated`, cause `SocketError{code:"UND_ERR_SOCKET"}`) surfaces as `{"type":"assistant","is_api_error_message":true,"error":"unknown", … "API Error: terminated"}`. `_TRANSIENT_CAUSE_RE` matches none of `terminated` / `other side closed` / `stream disconnected`. Measured: transient=False, 1 invocation, vs transient=True and 3 invocations for the pinned incident text. That is criterion (i)'s "a lost/interrupted connection" left unretried — the exact category the slice promises. Add those shapes to the cause set. This is SAFE in the direction iteration 1 was rejected for: the regex only ever runs on text the CLI itself marked (progress.py:537), so it cannot re-open the false-positive arm. While in there: the patch's own `UND_ERR_[A-Z_]+` alternative (progress.py:493) is unreachable for this shape — the code lives in the event's `cause`, never in the text — so either read the nested cause code or drop that alternative rather than leave a branch that looks like coverage and is not. 2. The `result`-branch `api_error_status` arm is dead code against the real stream, and both tests that "pin" it construct an event the CLI cannot emit. progress.py:546 guards on `subtype != "success"` while :551 requires `error_during_execution` PLUS an `api_error_status` — but in 2.1.233 the only result carrying that field is the `subtype:"success"` variant with `is_error`; the `error_during_execution` / `error_max_turns` variants carry `errors:[…]` and nothing else. The CLI asserts this in its own telemetry (`api_error_status: ol.subtype === "success" ? … : void 0`). So the guard excludes exactly the shape that carries the field. Either re-key the arm on the CLI's actual API-error ending (`subtype == "success" and is_error` — still machine-marked, still no prose matching) or DELETE the arm and state that the wrap-up is retention-only. Either way, remove the two impossible records at test_leaf_resilience.py:461 and :473 — that is the "synthesised the shape it then parses" defect round 2 rejected, relocated into the one branch the vendor fixture never covered. Do not leave a green test standing for an event that cannot exist. 3. The stickiness rationale cites an incident ending that was never observed (progress.py:558-560) and `_WRAP_UP` (test_leaf_resilience.py:85, used at :208) encodes it. An api-error ending with no thrown/aborted turn produces the SUCCESS variant with the API-error text in `result`; the `error_during_execution` variant is emitted only for a throw or an aborted turn and then carries `errors:["[ede_diagnostic] turn aborted (…) stop_reason=…"]` — "Execution error" appears nowhere, and the pinned transcript (tests/fixtures/README.md, line 345 = last event) contains no result record at all. Keep the sticky RULE; restate the comment and the fixture over the aborted-turn variant that actually can follow, or drop the claim. Asserted-rather-than-observed is the exact standard the fixture was added to enforce. SCOPE — unchanged, do NOT expand. The reviewer/advisory attempt-blind harvest (leaves.py:2653, :2986, :3287) stays a follow-up issue; build-notes.md already records it honestly with a measured ≈28-line cost, which is what was asked for. Do not take it here. SIZE — the patch is 86 KB against the 80 KB backstop already (35 KB of it tests). These three fixes must not grow it: (2) deletes a dead arm and two tests, (1) and (3) are small. If the rebuild finds itself adding substantial new surface, say so in build-notes.md rather than widening the slice. Not re-litigated, still open §6 items for the next sign-off: C4's derived-stream fixture vs a live API death, the prior-art check on a disposable target, and fitness-to-purpose. The C5 gate row is a vacuous pass ("patch adds no new test file — nothing to assert") and supports no production-path claim; the adversary checked the substance separately and it holds. The plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure. Optional if free: the drain hot path now parses the same line up to 4× (progress.py:182-194) — non-gating, a single `json.loads` passed to each classifier would do.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
