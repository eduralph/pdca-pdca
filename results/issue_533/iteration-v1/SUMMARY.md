# Result — issue 533 / a-leafs-own-terminal-error-is-kept-and-read

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `progress.run_with_heartbeat` already reads every event a leaf's stream emits,
  and throws away the one line that explains a death. Two rules, both verified on the target
  base (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **The stream's own error text is discarded.** The drain parses stdout for a session flag
    and a tool label and keeps nothing else (`template/src/pdca_harness/progress.py:147-158`);
    what it retains is a bounded **stderr** tail (`:143`, `:162-171`), and with `capture` off
    `output` is that stderr tail alone (`:255`). The CLI's API-error line arrives as a stream
    *text* event on **stdout**, so it is displayed and dropped, and `_format_leaf_attempt`
    (`leaves.py:724-730`) falls back to `(no output captured)` — verbatim what the reported
    incident's `build.error.log` contained. The cause was legible only in the CLI's own
    session transcript under `~/.claude/projects/`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:144`, `:154-155`,
    `_is_session_event` at `:365-377`; `LeafError.transient` at `leaves.py:103-107`).
    "Produced anything?" is a *proxy* for "died at invocation", and the proxy fails for
    exactly the long sessions where an attempt is most expensive: the incident's 18-minute
    builder did plenty of work and then died of an API connection drop, so it was classified
    substantive — correctly by that rule, wrongly for that cause. The module's own docstring
    (`:55-64`) already records that the CLI emits `system`/`api_retry` on a **retryable** API
    error; the **terminal** report is the case with no reader.
- Success criterion: With the patch:
  (i) a leaf whose stream carries the CLI's **own terminal error report** — the report the
  vendor itself marks as an API error — and then exits non-zero is classified **transient**
  when that report's cause is transient (a lost or interrupted connection, an overload or
  5xx, a mid-session rate-limit rejection), however much work came first;
  (ii) it is **not** classified transient when the vendor marks the cause **permanent** (an
  invalid request, an authentication or billing failure) — no prose inside a marked report
  may promote it — nor when a leaf merely mentions or quotes an error, nor when it fails
  substantively; and a report the CLI then **recovers** from, with real **main-session** work
  following it, is not the leaf's death;
  (iii) the report's text is **retained for every marked terminal report, transient or not**,
  so it reaches the leaf's `*.error.log` by the same route the stderr tail takes, and the
  post-mortem explains the failure without opening `~/.claude/projects/`;
  (iv) nothing else changes: a stream-less family still reports substantive
  (`leaves.py:661-670`), `capture` still returns the child's raw stdout unmodified, the
  codex/gemini stream formats degrade to today's behaviour, a leaf that succeeds is spawned
  and reported exactly as today, and the memory-telemetry post-mortem (#420) still rides
  `output` into the same log.
  Demonstrable by C4-verify offline: a stub "leaf" that is a Python interpreter emitting
  chosen stream events and exiting non-zero, driven both through
  `progress.run_with_heartbeat` directly and through `leaves._invoke_leaf_resilient` (the
  reviewer/advisory path, which is resilient on **any** base), so (i)-(iv) are assertions
  over an invocation counter and the error log's bytes.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: What a leaf's death *is*, on the spawn path every leaf shares — read the CLI's
  own terminal error report out of the stream the driver already parses, classify transient
  by what the **vendor** marked (not by prose the harness guesses at), and keep that text so
  it reaches the leaf's `*.error.log` by the route the stderr tail already takes. Update the
  four downstream prose sites that restate the old definition so the codebase does not carry
  two contradictory statements of it.
  **Out of scope:** who is retried and what a retry may inherit — the builder is **not** put
  on the resilient path here, `_invoke_leaf_resilient`'s body, `do_build`, and the artifact
  harvests are sibling child-1's (this child changes only `progress.py`, the four prose sites
  in `leaves.py`, one comment in `assemble.py`, and its own tests/fixtures); resuming a long
  session via the CLI's own session-resume (a fresh re-invoke is the accepted first cut — say
  so in `build-notes.md` so the human can weigh it); the gate-side transient (issue #371); a
  leaf **signal-death** under the memory cap (issue #510: "neither #506's transient nor
  #421's preflight"); the memory-telemetry post-mortem (#420), which must keep working
  unchanged; any new `pdca.toml` knob.

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

Task under review: retain a Claude leaf's vendor-marked terminal API-error report and classify only terminal transient causes as retryable, even after substantive work.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required decision boundary is falsifiable across transient, permanent, recovered, quoted, fixture-absent, and streamless outcomes, with the focused cases beginning at `template/tests/test_terminal_error_classification.py:161`. |
| C2 Reproduction (red pre-fix) | PASS | With only the tracked production hunks stashed, 20 of 23 focused tests failed on classification or retention assertions while the compatibility controls remained green; the incident-shaped retry assertion is at `template/tests/test_terminal_error_classification.py:165`. |
| C3 Change | PASS | The shared stream drain now derives retry state from marked terminal events and retains their diagnostic through the existing output route, so all leaf callers receive the same corrected evidence at `template/src/pdca_harness/progress.py:185` and `template/src/pdca_harness/progress.py:295`. |
| C4 Verification (red→green) | PASS | Independent execution produced 20 focused failures before the source fix and 23/23 passes after restoration; the patched tree also passed 1,781 offline driver tests, consistent with the frozen C4/T3 logs and the end-to-end retry assertion at `template/tests/test_terminal_error_classification.py:168`. |
| C5 Causal adequacy | PASS | The fix reads the previously discarded vendor-marked death in the common stream reader and clears it only when later main-session work proves recovery, removing the dropped-evidence/proxy cause rather than adding an optional-capability fallback (`template/src/pdca_harness/progress.py:188`, `template/src/pdca_harness/progress.py:660`). |
| T1 Structure | PASS | Classification, retention, and recovery state stay localized in `progress`, downstream changes are definition-only, and the dedicated end-to-end suite drives the existing public spawn path (`template/tests/test_terminal_error_classification.py:13`). |
| T2 Shape | PASS | `git diff --check`, docs lint, and the 22-page render/link audit passed independently; the frozen host-CI parity log is also green, and fixture provenance explicitly separates observed from derived records at `template/tests/fixtures/README.md:13` and `template/tests/fixtures/README.md:51`. |
| T3 Runtime | PASS | The focused suite passed 23/23 and the full offline driver suite passed 1,781 tests with two expected skips; the frozen gate additionally shows all seven render/update-compat tests executed and passed, covering neighboring behavior documented at `template/tests/test_terminal_error_classification.py:370`. |
| T4 Contribution | N/A | Contribution artifacts do not exist at Check by design; `gate-logs/T4-contribution.log` records deferral and the substantive contribution audit is mandatory at publish. |
| T5 Judgment | PASS | The target base exactly matches current upstream `main`; affected-file history found the closest merged precedent in PR #286, the complete closed-PR scan found no unmerged closed duplicate, and open PRs #520/#524 touch disjoint `leaves.py` regions, so no prior-art or ordering conflict remains to adjudicate. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide whether the vendor marker/kind/status boundary is fit for automatic retry in production—a wrong classification can replay an expensive long-running leaf or hide a substantive failure behind an infra label (`template/src/pdca_harness/progress.py:461`). |

### Advisory — adversary

# Adversarial pass — issue_533 (a leaf's own terminal error is kept and read)

Re-ran the asserted red→green at `$PDCA_TARGET` (23 tests green with the patch; the frozen
`gate-logs/C4-verify.log` red leg fails 20 of them, including the two headline assertions —
`err.transient` and `"Connection lost mid-response" in error_log` — so the red is real, not a
missing-file artifact: the fixture-replaying cases *failed on their assertions* rather than
skipping). The suite drives the production symbols (`progress.run_with_heartbeat`,
`leaves._invoke_leaf_resilient`), not a copy — I re-drove the same two entry points from my own
scratch probes and reproduced every asserted behaviour. Vendor grounding re-derived
independently from `~/.local/share/claude/versions/2.1.233`. One refutation landed.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:560-562`: the `_REPORT` branch
  matches a marked api-error message **without checking `parent_tool_use_id`**, while
  `_is_main_session_work` (`progress.py:660-681`) is deliberately main-session-scoped. So a
  **sub-agent's** report is credited as the leaf's own account of its death, and because
  `_note_terminal` (`:615`) only protects a `_REPORT` from a *wrap-up*, a later sub-agent report
  overwrites the main session's. Concrete failing case, run against the patched target:
  `assistant(work)` → main-session report `{"is_api_error_message":true,"error":"invalid_request"}`
  → trailing sub-agent report `{"parent_tool_use_id":"toolu_…","subagent_type":"general-purpose",
  "is_api_error_message":true,"error":"overloaded"}` → `result/error_during_execution`, exit 1 ⇒
  `produced=False` (leaf retried to the attempt budget) and the retained diagnostic is
  `"API Error: 529 the API is at capacity"`. That is brief criterion (ii) inverted — a cause the
  vendor marked **permanent** is promoted, and the `*.error.log` names the wrong death — and it is
  the same family as the defect the brief said must not be rebuilt (a second marked report
  swallowing the first). The input is vendor-emittable, not hypothetical: 2.1.233's
  `agent_progress` branch yields `{type:"assistant", …, parent_tool_use_id: e.parentToolUseID,
  error: i.error, ...(i.isApiErrorMessage===!0 && {is_api_error_message:!0}), …}` — and
  `template/tests/fixtures/README.md:115-117` quotes exactly that branch with `error:` and the
  flag **elided behind "…"**, which is why the shape reads like harmless chatter. The gap was
  contemplated and left unasserted: the test helper's `parent=` parameter
  (`template/tests/test_terminal_error_classification.py:71-77`) is passed by **no** test, while
  `test_a_trailing_subagent_line_does_not_clear_the_report` (`:294`) establishes that trailing
  sub-agent lines are exactly the interleaving to expect. Fix is one predicate (scope the
  `_REPORT` branch, or make `_note_terminal` prefer a main-session report) plus the missing case.

- **NEEDS-HUMAN** — `template/src/pdca_harness/leaves.py:693` and `:724-726` are a **fifth**
  restatement of the definition this patch widens, and the patch leaves both false: the operator
  now sees `leaves: <bundle> — leaf exited 1 with no output (transient); retry 1/2 in 0s` for a
  leaf that produced 18 minutes of work and a report — printed verbatim in this round's own green
  leg (`gate-logs/C4-verify.log`, lines 12-13). The brief lists only four prose sites and scopes
  `_invoke_leaf_resilient`'s body to sibling child-1, so this needs a human scope call: either
  child-1 owns these two lines (confirm it does) or the codebase ships the contradiction the
  invariant exists to prevent. Not marked `[impl]` because touching them crosses the split.

- `template/src/pdca_harness/progress.py:303` bends the documented contract of the third return
  value on the **success** path: a leaf whose stream carried a transient marked report and then
  exited **0** now returns `produced=False`, and `:295-301` appends the report to `output` (was
  `""`). I checked every call site — `leaves.py:663-678` (guarded by `rc != 0`), `leaves.py:760`,
  `gates.py:559`, `publish.py:833` (all `capture=True` and/or discard the flag) — so nothing today
  misreads it; but the docstring at `:60-62` still defines `produced` as "did the child emit a
  substantive stream event", which is now false for a *successful* run, and #510's signal-death
  work is the next reader of that flag.

- Attempted and **could not** refute: (a) that the red is vacuous — it is not, the inline cases
  carry it; (b) that the regex could promote a permanent cause — `_kind_is_transient`
  (`progress.py:576-585`) answers from the vendor kind first in both directions, and I confirmed
  `_CLAUDE_PERMANENT_ERROR_KINDS` is exactly 2.1.233's enum minus its own transient set minus
  `unknown`, so only `unknown` reaches `_TRANSIENT_CAUSE_RE` (the false positives I could build —
  `"cannot read /var/log/429/config.json"` — are not shapes the CLI's `"API Error: "+e.message`
  mapper emits); (c) that the clearing rule wipes the death via a trailing main-session
  `user` tool_result — plausible on paper (`_WORK_EVENT_TYPES` at `:408` includes `user`, and
  `_is_main_session_work` does not exclude the CLI's `isSynthetic` echoes, so such a line would
  drop **both** the classification and the retained text), but I found no evidence for it: every
  `isApiErrorMessage` record in the local `~/.claude/projects` corpus (2 of them) was its
  session's last event, so this stays a residual risk, not a refutation; (d) that `capture`
  changed — the raw stdout is byte-identical (`:295`); (e) that the vendor citations were
  asserted rather than observed — the assistant emitter (no `api_error_status` on `assistant`),
  the three `result` variants with `api_error_status` only on `success`, and the transient
  predicate `apiErrorIsTransient===!0 || error==="overloaded" || error==="server_error"` all
  re-derived from the binary and all as the fixture README describes them.

### Advisory — code-review

# Check — advisory code review (issue #506 slice)

Scope: `template/src/pdca_harness/progress.py` (new terminal-error reader/classifier),
the four prose sites in `template/src/pdca_harness/leaves.py`, one comment in
`assemble.py`, and the new test/fixture files. Grounded against
`$PDCA_TARGET/template/src/pdca_harness/{progress,leaves}.py` (post-patch) and the
C4 gate log (genuine red→green: 20 failures pre-fix, `Ran 23 tests … OK` post-fix).

## Correctness

Traced the state machine end to end (`_terminal_error`, `_kind_is_transient`,
`_note_terminal`, `_is_main_session_work`, and the `produced["session"] and not
terminal["transient"]` fold at `progress.py:303`) against every case in
`test_terminal_error_classification.py`, plus several combinations the suite does
not exercise (WRAPUP-before-REPORT ordering, a REPORT/WRAPUP pair with `is_error`
False, a `kind=None` report, an interrupted `reader.join(timeout=5)`). No bug found:
the `if shape: … elif …` branch order at `progress.py:188-194` correctly prevents a
REPORT line from being read as its own "recovery" via `_is_main_session_work`, the
`_note_terminal` stickiness (`progress.py:412-414`) is scoped to the wrap-up shape
only (not "any later record"), and the newline/`capture` handling at `:295-301`
matches the pre-existing stderr-tail convention exactly (no double-newline, no
corruption of raw JSONL under `capture`). The two defects the brief calls out as
open against the rejected prior attempt (scope-blind clearing, wrap-up swallowing a
second report) are both closed and each has a dedicated regression test
(`test_a_trailing_subagent_line_does_not_clear_the_report`,
`test_a_second_marked_report_wins_outright`).

- No correctness bugs found in the new classification/retention logic.

## Reuse / simplification / efficiency

- `progress.py:186-197` (the claude-format branch of `_drain`): for every stream line
  of a `claude-stream-json` leaf, the drain thread now does up to **three** independent
  `json.loads` + dict-walks of the same line unconditionally (`_is_session_event`
  at `:419`, `_terminal_error` at `:555`ish, `_stream_tool_label` at `:688`), plus a
  fourth (`_is_main_session_work`) once a terminal report is pending. This was already
  a 2x-parse pattern before this patch (`_is_session_event` + `_stream_tool_label`);
  the patch's `_terminal_error` call adds a third unconditional parse per line, in
  the same shape as the existing classifiers (matches the brief's own composition
  cue to sit "beside `_is_session_event`, in the same shape"), so it is consistent
  with established style rather than a new anti-pattern. For an 18-minute session
  emitting thousands of lines (the incident this fix targets) the redundant
  re-parsing is measurable but not correctness-affecting — a `json.loads(line)` once
  per line, threaded through to each classifier, would avoid the repeat work. Not
  blocking; a straightforward follow-up if `_drain`'s per-line cost ever becomes
  the bottleneck.

No other duplicated logic, unreachable branches, or resource-leak concerns found in
the diff. The regex `_TRANSIENT_CAUSE_RE` (`progress.py` "unknown"-kind fallback)
is exercised only on text the CLI itself marked as its own API-error message, so its
breadth (bare `\btimeout\b`, `\b(?:…|500|502|503|504|…)\b`, etc.) is scoped tightly
enough that a false-positive match on unrelated leaf prose is not reachable — no
finding there.

## Summary

Diff is clean on both lenses I was asked to apply: no correctness bugs introduced,
and the one efficiency observation above (redundant per-line JSON parsing in the
stream drain) is minor, pre-existing in kind, and non-blocking.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — The maintainer must decide whether the vendor marker/kind/status boundary is fit for automatic retry in production—a wrong classification can replay an expensive long-running leaf or hide a substantive failure behind an infra label (`template/src/pdca_harness/progress.py:461`).

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
- Iteration delta (if iterating): The approach is sound and the evidence is strong — gates green, all reviewer rows PASS, the adversary independently re-ran the red→green and re-derived the vendor grounding from the shipped binary. Rejected on one landed refutation, not on the design. Must close before re-submission: 1. Scope the terminal-report reader to the main session (`progress.py:560-562`). The `_REPORT` branch matches a marked api-error message without checking `parent_tool_use_id`, while its sibling `_is_main_session_work` (`:660-681`) is deliberately main-session-scoped. Because `_note_terminal` is newest-wins and only protects a `_REPORT` from a *wrap-up*, a trailing SUB-AGENT report overwrites the main session's. Confirmed by reading the patch at sign-off. Consequence, and why it blocks: a main-session `invalid_request` followed by a sub-agent `overloaded` classifies transient — a cause the vendor marked PERMANENT is promoted and retried to the attempt budget — and the retained diagnostic names the wrong death ("API Error: 529 the API is at capacity"). That is criterion (ii) inverted, and it is the same family as the defect the brief said must not be rebuilt (a second marked report swallowing the first). Retention is the point of criterion (iii); a log that confidently names the wrong cause is worse than the "(no output captured)" it replaces. Fix is one predicate — scope the `_REPORT` branch to `parent_tool_use_id is None`, or make `_note_terminal` prefer a main-session report — plus the missing case. The test helper's `parent=` parameter (`test_terminal_error_classification.py:71-77`) already exists and is passed by no test; the gap was contemplated and left unasserted. Note the commoner variant, which needs no conjunction: a sub-agent blip in a leaf that then fails on its own merits is now labelled transient. Fixing the scope closes both. 2. `produced`'s documented contract is bent on the SUCCESS path. A leaf whose stream carried a transient marked report and then exited 0 returns `produced=False`, while the docstring (`progress.py:60-62`) still defines it as "did the child emit a substantive stream event". No current call site misreads it, but #510's signal-death work is the next reader of that flag. Either restore the flag on rc == 0 or restate the contract. 3. UNRESOLVED SCOPE QUESTION, not adjudicated at this sign-off: `leaves.py:693` and `:724-726` are a fifth and sixth restatement of the definition this patch widens, and both are left false — the operator sees "leaf exited 1 with no output (transient)" for a leaf that produced 18 minutes of work and a report (printed verbatim in this round's own green leg, gate-logs/C4-verify.log lines 12-13). The brief lists only four prose sites and scopes `_invoke_leaf_resilient`'s body to sibling child-1 (issue_532). Since 532 also went back for rebuild this round, its scope is still movable: settle which child owns these two lines before either lands, so the codebase does not ship the contradiction the invariant exists to prevent. §6 fitness-to-purpose was NOT cleared and remains open for the next round. The main-session scoping in item 1 is what the boundary's fitness turns on. Note also that the expensive case in that item — replaying a long-running builder — is not reachable from this patch alone (the builder is not on the resilient path here); it becomes live when 532 lands, which is a further reason to settle the two together.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
