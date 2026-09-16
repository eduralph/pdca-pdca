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

Review of issue #506: retain and classify a leaf's terminal infrastructure error, retry transient builder deaths, and provide an actionable exhausted-retry message.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief makes the terminal-event categories, bounded builder retry, retained diagnostic, honest resume path, unchanged substantive behavior, and offline falsifier explicit; no external dependency is declared (`template/tests/test_leaf_resilience.py:323`). |
| C2 Reproduction (red pre-fix) | PASS | With only production stashed and patched tests/fixtures retained, the independent run executed 39 tests and failed 30 assertions, including classification, retention, builder retry, retry residue, and resume behavior (`template/tests/test_leaf_resilience.py:371`). |
| C3 Change | FAIL | A vendor-declared permanent kind must remain non-retryable, but the unconditional `kind in transient_set OR prose-regex` makes `invalid_request`/`authentication_failed` transient whenever their text says “timed out” or “temporarily unavailable,” contradicting the permanent-kind contract and spending three attempts on a permanent failure (`template/src/pdca_harness/progress.py:547`). |
| C4 Verification (red→green) | PASS | Restoring the production patch changed the same independent run from 30 failures to 39/39 green; the frozen gate independently records the same meaningful red→green posture, and the complete patched offline suite also exited 0 (`template/tests/test_leaf_resilience.py:650`). |
| C5 Causal adequacy | PASS | The change replaces the “produced work” proxy at the stream classifier, carries the terminal account over the existing error-output route, and puts Do on the existing bounded resilience wrapper; it is not a capability probe or downstream symptom guard (`template/src/pdca_harness/progress.py:509`, `template/src/pdca_harness/leaves.py:1954`). |
| T1 Structure | NEEDS-HUMAN | The maintainer must accept the follow-up boundary: the shared retry now reaches reviewer/advisory leaves after real work, but successful retry still harvests any pre-existing artifact without attempt ownership, so an interrupted attempt's partial verdict can survive; closing that risk would expand an already 92,086-byte slice (`template/src/pdca_harness/leaves.py:2641`, `template/src/pdca_harness/leaves.py:2653`). |
| T2 Shape | PASS | Python compilation and `git diff --check` are clean, while both frozen docs checks show lint, render, and link-audit success; the pinned fixture is documented with explicit observed-versus-derived provenance (`template/tests/fixtures/README.md:7`). |
| T3 Runtime | FAIL | Although the patched 1,780-test offline suite passes, an additional production-path probe with `error="invalid_request"` and “request timed out” returned `transient=True` and invoked the leaf three times, exposing a missing precision case (`template/src/pdca_harness/progress.py:548`). |
| T4 Contribution | N/A | The Check-time row is deferred because `pr-description.md` is intentionally drafted later; the mandatory publish-time contribution gate owes the substantive verdict. |
| T5 Judgment | NEEDS-HUMAN | The maintainer must choose ownership/rebase order with open PR #524: it is based on the same `main` SHA and inserts at the same post-`_format_leaf_attempt` boundary, so publishing either first can create conflict or duplicate rationale even though upstream `main` itself is not ahead (`template/src/pdca_harness/leaves.py:768`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether the derived stdout fixture represents the current live CLI: run Do through a proxy that severs an established Claude response after work begins, then confirm three bounded attempts, the leaf's exact error in `build.error.log`, and the partial-patch resume warning; the stream fixture is derived rather than observed (`template/tests/fixtures/README.md:36`). |

### Advisory — adversary

# Adversarial review — issue 506 (iteration 4)

Ground: `$PDCA_TARGET` (patched working tree, base `bc16d55`). Evidence re-run independently:
red leg (production files restored from `HEAD`, all test hunks kept) → **30 failures / 39 tests**;
green leg → **39 OK**; full template suite → 1780 tests, only `test_settings_permissions` red and
only because my scratch copy re-roots `REPO_SETTINGS` (`tests/test_settings_permissions.py:40`) —
unrelated to the patch. So C4's red→green is real, and it is real *through the production path*
(each case spawns a python "leaf" whose bytes go through `progress.run_with_heartbeat`).

## Findings

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:188-191` (with `:405`, `:625-636`):
  the "the CLI recovered, so that report was not the end" rule is **scope-blind**, and one trailing
  **sub-agent** line restores the pre-fix outcome exactly. Measured through
  `_invoke_leaf_resilient` → `_invoke` → `progress` → a real subprocess, replaying the pinned
  incident fixture and then a single
  `{"type":"assistant","parent_tool_use_id":"toolu_01SUB", …"subagent: still summarising"}`:
  `transient=False`, **1** invocation, error log back to
  `(no output captured) LeafError: Command '[…]'` — the incident's verbatim artifact, i.e. criteria
  (i) *and* (iii) both fail with the suite green. A trailing sub-agent `user` tool_result gives the
  same result. This is not an invented event shape: claude-code 2.1.233 emits sub-agent messages on
  *this* stream through the same emitter, as `type:"assistant"`/`"user"` with `parent_tool_use_id`
  set (`case "progress"` → `UXe`, binary offsets ~300270907/300271692, `yield {type:"assistant", …,
  parent_tool_use_id: e.parentToolUseID, …i.isApiErrorMessage===!0&&{is_api_error_message:!0}}`),
  while `_is_work_event` dispatches on `ev["type"]` alone. An orphaned sub-agent still streaming is
  not the main session carrying on. Cheap containment: require the clearing event to be main-session
  (`parent_tool_use_id` null/absent) and pin it with the existing stub harness. **What I could not
  establish:** an ordering where a sub-agent line lands *after* the main session's terminal report
  and the process then exits non-zero — the natural candidate is two parallel `Task` sub-agents, one
  of which dies of the API error. The gap is concrete and cheap to close; its field frequency is not.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:580`: stickiness is stated over the
  `result` wrap-up (docstring `:563-577`) but implemented over *any* later report, so a **second
  marked api-error report** is swallowed. Measured: work → `api_error(server_error, "…Connection
  lost mid-response…")` → `api_error(invalid_request, "API Error: 400 duplicate tool_use ID in
  conversation history.")` → exit 1 yields `transient=True`, **3** builder invocations, and a
  `build.error.log` that keeps only the first line — the permanent 400 that will fail identically on
  every retry is neither retained nor read. Two marked reports with no work event between them is
  what two parallel sub-agents (or a sub-agent plus the main session) produce; the CLI's own loop
  does not stop after emitting one (`case "assistant": if(_t.isApiErrorMessage) yield*tt("stream_error")`
  continues the message loop, 2.1.233). Keeping the sign-off's endorsed rule while closing this is a
  one-line narrowing: stick only against a `result` event, let a later *marked report* overwrite.

- `template/src/pdca_harness/leaves.py:1861` + `:1870`: `residue` is computed over
  `("patch.diff", "build-notes.md")` but only printed on the `patch.diff` branch. Measured with
  `_transient_do_death` on a bundle holding a half-written `build-notes.md` and no patch: the
  operator is told "no patch.diff was left behind … its inputs are intact — `pdca run 506` …
  re-drives Do from the top", and the residue is never named. Accurate about *state* (the bundle does
  read PLANNED, and `worktree.ensure` resets the tree on the next run), so this is an honesty nit in
  a message whose whole point is honesty, not a functional break.

- `template/src/pdca_harness/progress.py:603`: `_claude_result_texts` reads a top-level `error` key
  "as a fallback for a shape neither of those covers" — but the CLI's `result` schema attaches
  `errors: string[]` to the `error_*` variants and `result` to the `success` one (verified in the
  binary at ~306393322, the same quote the fixture README uses), so that key is unreachable, and
  mutation-testing confirms it is unpinned (deleting it leaves 39 tests green). That is the identical
  "a branch that looks like coverage and is not" the previous sign-off had removed for
  `UND_ERR_[A-Z_]+`. Two smaller mutants also survive: dropping `ev.get("subtype") == "success"`
  at `:555` (defensible — the excluded shape cannot exist) and dropping the `stream disconnected`
  alternative at `:495`.

- Verdict caveat (not a refutation): `check-gates.json` C5 records `pass` with
  `"patch adds no new test file — nothing to assert"`. That row supports **no** production-path
  claim — as prior sign-offs already noted. I checked the substance separately and it holds: every
  new case drives a real subprocess and asserts on an invocation counter and the error log's bytes,
  and each marker reaches the child through the env or a fixture file, so the argv echo in
  `_format_leaf_attempt` cannot satisfy an assertion (`tests/test_leaf_resilience.py:64-66`).

## Attempted and could not refute

- **The vendor contract**, which is where rounds 2-3 found the rot. I re-derived the fixture README's
  claims from the shipped binary myself: the stream's assistant emitter writes `error` and
  `is_api_error_message` and **no** `api_error_status` (~300266437); `Yd` always normalises the
  api-error content to one text block, `isApiErrorMessage:!0` (~302956461), so `_claude_message_texts`
  cannot miss it; the `result` emitter is byte-for-byte what the README quotes (~306393322); `sie`/`gde`
  hold no `UND_ERR_*` code (~296572269), so the mapper's `error:"unknown"` + `API Error: terminated`
  fallback is real — and this round's cause set now matches it.
- **The "too broad" arm** iterations 1-2 were rejected for. The regex only ever runs on text the CLI
  itself marked, and I walked the mapper's permanent branches (`invalid_request` 400 duplicate
  tool_use / tool-use concurrency, `authentication_failed`, `model_not_found`, `billing_error`,
  request_too_large): none of their texts match `_TRANSIENT_CAUSE_RE`. The two precision legs
  (leading "Error: … 500 …", a leaf quoting the incident line verbatim) hold.
- **Tautology / mutation cover**: 13 mutants of the load-bearing hunks; 9 caught, including
  `\bterminated\b`, `other side closed`, the 5xx range in `_transient_status`, the
  `isApiErrorMessage` spelling, the per-attempt flush (`leaves.py:741`), `do_build`'s `_has_content`
  guard, `_transient_do_death`, the retention of a `result` ending's text, and the
  attempt-1-prompt-unchanged rule. The 4th survivor is cosmetic (`leaves.py:749` names the leaf by
  `label`, unpinned).
- **The builder's newly inherited legacy arm**: a builder that dies before any stream event (a bad
  `effort_argv`, a memory-scope kill at startup) is now retried 3× and told "nothing substantive
  failed" (`leaves.py:1859`). That is #138's pre-existing rule reaching a new caller, `#510` is
  explicitly out of scope in the brief, and the cost is bounded (3 spawns, 12s) — noted, not filed.

### Advisory — code-review

# Advisory code review — correctness + reuse/simplification lens (issue #506)

Scope: only the hunks in `patch.diff`, grounded on `$PDCA_TARGET`. The core mechanism
(sticky terminal-report classification, the `is_api_error_message`/`result` split, the
attempt-by-attempt error-log flush, the builder's `_BUILD_RETRY_NOTE`, `_has_content`) is
sound and matches what C4 (`gate-logs/C4-verify.log`: 30 failures pre-fix, `OK` on both
touched test files post-fix) and the full suite (`gate-logs/T3-suite.log`: 1780 tests OK)
actually exercised. Iteration-1/2's four carried-forward defects (narrow/broad matcher,
false resume message, unwarned retry-into-residue, unpinned vendor contract) are genuinely
fixed and tested against real fixture bytes (`tests/fixtures/`), not a synthesised shape.

## Findings

- NEEDS-HUMAN — The widened transient signal now makes the **reviewer/advisory** leaves
  retryable after they have already produced partial work (they share
  `_invoke_leaf_resilient` with the builder, `leaves.py:680-754`), but unlike the builder
  they get no `retry_note` (`leaves.py:2641-2648`, `leaves.py:2975-2981` — no `retry_note=`
  kwarg), and the sandbox `tempfile.TemporaryDirectory` that holds the leaf's own output
  is opened ONCE and reused across all internal retry attempts
  (`_run_review_sandboxed`/`_run_advisory_sandboxed`, `leaves.py:2597-2648` and
  `:2948-2981`). A dying attempt 1 can leave a partial `check-review.md` /
  `check-advisory-<id>.md` on disk in that sandbox (`REVIEWER_INPUTS`, `leaves.py:68`,
  never includes those output names, so nothing clears them between attempts); harvest is
  attempt-blind — `if produced.exists(): shutil.copy2(...)` (`leaves.py:2653-2657`,
  `:2986-2989`) — with no check that the copied file is from the attempt that actually
  succeeded. This is exactly item 5 the previous sign-off's carry-forward flagged as SCOPE
  ("necessary but not sufficient… a truncated check-review.md from a dead attempt 1 can be
  copied into the bundle as the reviewer's verdict") and explicitly deferred, asking that
  any non-closure be recorded in `build-notes.md`. That file is withheld from this lens, so
  a human should confirm at sign-off that the deferral is actually documented there (or
  that this round closed it in a way not visible from the diff alone).

- The stream drain (`progress.py:182-194`) now runs up to four independent
  `json.loads(line)` calls per stream line inside the hot per-leaf drain thread:
  `_is_session_event` (`:183`), `_terminal_error` (`:185`), conditionally `_is_work_event`
  (`:188`), and `_stream_tool_label` (`:192`) each re-parse the same JSON. This follows the
  codebase's pre-existing per-classifier-reparse convention (`_is_session_event` +
  `_stream_tool_label` already did this before the patch), so it's not a new pattern, but
  the patch does add two more re-parses per line to what was already redundant work. Not
  perf-material at typical CLI line rates, but a follow-on could parse once and pass the
  dict to each classifier rather than widening the existing duplication further.

- `_record_loop_attempt` (`leaves.py:1906`, called once per `do_build`) still records one
  `loop-telemetry.json` entry per iterate-do attempt, unaware that `_invoke_leaf_resilient`
  may now spawn the builder up to 3 times underneath it for a single recorded attempt
  (`leaves.py:1953-1962`). Not a defect against this brief's scope (telemetry wasn't in
  scope, and the brief explicitly says not to add new knobs), but worth surfacing: anyone
  reading `loop-telemetry.json` for cost/attempt accounting will now undercount actual
  builder invocations on a bundle that hit a transient retry.

## Not re-flagged (already closed this round, verified against target source)

- The matcher precision fix (`_terminal_error` gating `_TRANSIENT_CAUSE_RE` only on
  CLI-marked `is_api_error_message` text, `progress.py:580-586`) and the `result`-branch
  narrowing to `subtype == "success"` + `api_error_status` (`progress.py:587-593`) both
  match the "kind/status, not prose" requirement and are pinned by
  `test_the_cli_error_kind_classifies_a_report_whose_text_says_nothing` and
  `test_a_result_ending_the_cli_did_not_mark_is_explained_but_not_retried`.
- Sticky terminal-report semantics (`_note_terminal`, `progress.py:597-618`) correctly
  survive a same-shape `result` wrap-up and are cleared only by a real work event
  (`_is_work_event`, `progress.py:661-672`), verified by
  `test_the_wrap_up_result_does_not_overturn_the_report_that_named_the_cause`.
- `_write_attempt_records` flushing after every attempt (`leaves.py:757-765`), making
  `_BUILD_RETRY_NOTE`'s pointer at `BUILD_ERROR_LOG` true for every retried attempt, is
  exercised end-to-end from inside the child by
  `test_a_retried_builder_can_actually_read_that_account`.
- `capture` vs `stream_json` classification stays mutually exclusive on OUTPUT bytes while
  the classification itself still runs under `capture=True` (`progress.py:141-151`,
  `:292-298`), verified by `test_a_capturing_caller_still_gets_verbatim_stream_bytes`.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T1 Structure — The maintainer must accept the follow-up boundary: the shared retry now reaches reviewer/advisory leaves after real work, but successful retry still harvests any pre-existing artifact without attempt ownership, so an interrupted attempt's partial verdict can survive; closing that risk would expand an already 92,086-byte slice (`template/src/pdca_harness/leaves.py:2641`, `template/src/pdca_harness/leaves.py:2653`).
- [ ] T5 Judgment — The maintainer must choose ownership/rebase order with open PR #524: it is based on the same `main` SHA and inserts at the same post-`_format_leaf_attempt` boundary, so publishing either first can create conflict or duplicate rationale even though upstream `main` itself is not ahead (`template/src/pdca_harness/leaves.py:768`).
- [ ] Validation — fitness-to-purpose — The human must decide whether the derived stdout fixture represents the current live CLI: run Do through a proxy that severs an established Claude response after work begins, then confirm three bounded attempts, the leaf's exact error in `build.error.log`, and the partial-patch resume warning; the stream fixture is derived rather than observed (`template/tests/fixtures/README.md:36`).
- [ ] The widened transient signal now makes the **reviewer/advisory** leaves
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.
- [ ] size backstop — this slice is behaving oversized: patch is 90 KB (threshold 80 KB); 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Rejected on SLICING, not on the mechanism. The core is sound and has survived four rounds of independent attack — red->green reproduced every round through the real subprocess path, 1780 template tests green, 9/13 and 16/16 mutations of the load-bearing hunks caught, the vendor contract re-derived from the shipped binary. KEEP ALL OF IT. Each round also genuinely closed the previous round's defects. The problem is that the findings have been implementation-shaped in all four rounds, which is what an oversized slice produces: 92 KB against the 80 KB backstop, round 4 against a 3-round threshold. Do not rebuild this as one slice again — split it in Plan. Proposed seams (author the briefs at the split; the sizing.json currently claims one indivisible outcome, which is the judgement being overridden here): 1. STREAM-SIDE classification + retention, in progress.py: read the CLI's own terminal error event, classify transient by the marker/kind/status the vendor sets, keep the text so it reaches the leaf's *.error.log. This is criteria (i) and (iii). Self-contained and independently testable against the pinned fixture. 2. DO-SIDE resilience, in leaves.py: put do_build on _invoke_leaf_resilient with the retry note, the _has_content guard, the per-attempt _write_attempt_records flush, and the _transient_do_death exhausted-retry message. This is criteria (ii) and (iv). Depends on 1 but is a distinct outcome. 3. Optional third: the reviewer/advisory attempt-blind harvest, already deferred twice and measured at ~34 lines across two files in build-notes.md:197-206. File it as its own issue rather than deferring it a third time. Carry into the child briefs, unresolved this round: - Adversary finding A (progress.py:188-191, :405, :625-636): the "the CLI recovered" clearing rule is scope-blind — one trailing SUB-AGENT line restores the pre-fix outcome exactly (transient=False, 1 invocation, "(no output captured)"), so criteria (i) and (iii) both fail with the suite green. Containment is one line: require the clearing event to be main-session (parent_tool_use_id null/absent). The adversary could not establish the ordering in the wild; the gap is cheap to close regardless. - Adversary finding B (progress.py:580): stickiness is documented over the `result` wrap-up but implemented over any later report, so a SECOND marked api-error report is swallowed — a permanent 400 following a dropped connection is neither retained nor read, and costs 3 spawns. Containment is one line: stick only against a `result` event, let a later marked report overwrite. Already self-disclosed as a known trade-off in build-notes.md; close it rather than re-disclose it. - The reviewer's C3/T3 FAIL needs adjudication, not compliance. It rests on an `invalid_request` event whose text says "request timed out"; the adversary walked every permanent branch the vendor actually emits and found no text that matches _TRANSIENT_CAUSE_RE, i.e. the probe may be a synthesised shape the CLI cannot produce — the exact defect rounds 2 and 3 rejected the build for. Settle this against the binary before treating it as a defect to fix. - Nits, non-gating: residue is computed over both artifacts but printed only on the patch.diff branch (leaves.py:1861, :1870); the top-level `error` key in _claude_result_texts is unreachable against the real result schema and survives mutation (progress.py:603) — same "a branch that looks like coverage and is not" already removed once; the drain hot path now parses each line up to 4x (progress.py:182-194). Open §6 items carry forward UNCLEARED — none was ticked at this sign-off: - T1 / code-review: the attempt-blind harvest boundary (see seam 3). - T5: rebase/ownership order against open PR #524 (same base SHA, same post-_format_leaf_attempt boundary). Still to be decided at publish time. - Validation: the stream fixture is derived from the shipped binary and a pinned incident record, not observed from a live mid-response connection death. Standing since round 2; a limit of the environment, not an untried option. - The plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure. Note the C5 gate row is a vacuous pass ("patch adds no new test file — nothing to assert") and supports no production-path claim; both advisory lenses checked the substance separately and it holds.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
