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

Task under review: retain and classify a leaf's own terminal API-error report so transient main-session deaths are retried and explained without promoting permanent, recovered, quoted, or sub-agent failures.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is falsifiable across transient, permanent, recovered, timeout, non-Claude, and retention outcomes, so a regression has an observable consequence (`template/tests/test_terminal_error_classification.py:177`). |
| C2 Reproduction (red pre-fix) | PASS | With production hunks stashed but the inline tests retained, the independent pre-fix run failed 23 of 28 cases at the intended classification/retention assertions, reproducing the discarded-report defect (`template/tests/test_terminal_error_classification.py:181`; `gate-logs/C4-verify.log:254`). |
| C3 Change | NEEDS-HUMAN | Confirm this child owns the `_invoke_leaf_resilient` documentation/status-string edits and sibling issue 532 has dropped them — the original scope assigns that body to the sibling while carry-forward requires ownership to be settled, so dual ownership risks a stacked-patch conflict (`template/src/pdca_harness/leaves.py:681`; `brief.md:101`; `brief.md:234`). |
| C4 Verification (red→green) | PASS | Independent execution produced 23/28 failures pre-fix and 28/28 passes post-fix, matching the frozen gate's meaningful red→green evidence (`template/tests/test_terminal_error_classification.py:181`; `gate-logs/C4-verify.log:257`). |
| C5 Causal adequacy | PASS | The change consumes the vendor-marked cause and main-session provenance in the existing stream drain, replacing the discarded evidence/proxy classification rather than adding a capability probe or symptom guard (`template/src/pdca_harness/progress.py:197`; `template/src/pdca_harness/progress.py:616`). |
| T1 Structure | PASS | Parsing, cause classification, record precedence, and main-session recovery are separated into bounded helpers, keeping the retry decision auditable (`template/src/pdca_harness/progress.py:565`; `template/src/pdca_harness/progress.py:649`). |
| T2 Shape | PASS | Independent documentation lint and rendered-site link audit passed, agreeing with both frozen shape checks (`gate-logs/T2-docs.log:11`; `gate-logs/host-ci-docs.log:14`). |
| T3 Runtime | PASS | The independent patched target suite passed all 1,786 tests with 2 skips; the frozen suite also records clean root and driver runs (`gate-logs/T3-suite.log:1625`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check, and the frozen row says the substantive audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Approve the overall idiom and maintainability of the vendor-specific retry classifier — an affected-path PR query found only non-overlapping open hunks (#524/#520) and no closed-unmerged match, but retry-policy mistakes can multiply expensive sessions or suppress valid recovery (`template/docs/INTEGRATION.md.jinja:55`; `brief.md:175`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether observed transcript records plus stream shapes derived from Claude Code 2.1.233 are representative enough of live terminal failures — the real outage was not induced, so production fitness still turns on that vendor-grounding assumption (`template/tests/fixtures/README.md:13`; `template/tests/fixtures/README.md:51`). |

### Advisory — adversary

# Adversarial pass — issue_533 (a leaf's own terminal error is kept and read)

Evidence re-run independently, not taken on trust: red leg (production reverted to
`acb214a`, new test file kept) → **23 of 28 fail**; green leg → **28/28 OK**, matching
`gate-logs/C4-verify.log:29,254-256`. The suite drives the real spawn path (a real
subprocess through `leaves._invoke_leaf_resilient` / `progress.run_with_heartbeat`), not a
re-implementation. I also re-derived the vendor grounding from the shipped binary
(`~/.local/share/claude/versions/2.1.233`) rather than from `fixtures/README.md`: the
main-session emitters really do hard-code `parent_tool_use_id:null` (both the `assistant`
and the `user` case), the `agent_progress` branch really does forward
`is_api_error_message` with `parent_tool_use_id:e.parentToolUseID`, and the kind enum is
exactly the ten the patch splits. Both pinned fixtures are byte-verifiable against the
only two `isApiErrorMessage` records in the local transcripts, and both are main-session
and terminal. That part of the round holds. Five findings landed anyway — the first two are
substantive misclassifications reachable from the vendor's own emitters; the rest are a
scope call for the human and two conformance gaps.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:619` + `:646`: a marked
  message with **no `error` key** is not "the vendor's unknown API error", and routing it
  to `_TRANSIENT_CAUSE_RE` promotes leaf-side failures to transient. `kind = str(ev.get("error")
  or "unknown")` collapses *absent* into *"unknown"*, and `_kind_is_transient` then falls
  through to prose for **any** kind outside the two frozensets. 2.1.233's queryLoop
  catch-all emits exactly that shape for *any* exception that escapes the loop —
  `let wn = tr instanceof Error ? tr.message : String(tr); … let ii = Yd({content:wn,now:m.now,uuid:m.uuid})`
  — and `Yd` sets `isApiErrorMessage:!0` unconditionally while leaving `error` undefined
  (so the stream line carries the mark and no kind). Verified through the production path
  on the patched tree: a main-session marked message whose text is `connect ECONNREFUSED
  127.0.0.1:8931` (a dead MCP server), `fetch failed`, `Command timed out after 120000ms`,
  `socket hang up` or `terminated` all return `produced=False` → `.transient` → **retried
  to the attempt budget**, and the §6 row then tells the operator "transient infra — safe
  to re-run" (`leaves.py:2608-2613`) for a config failure that fails identically every
  time — the very conflation PR #285's review is cited for at `leaves.py:2541-2543`. The
  same line is the drift hole: any kind the vendor adds after 2.1.233 (the CLI
  auto-updates; the harness pins nothing) is unlisted, so its prose decides. The patch's
  own docstring already states the correct rule — "The text is read **only** for the kind
  the CLI leaves ``unknown``" (`:638-639`) — and the code does not implement it. Nothing
  asserts the looser behaviour: replacing the fallthrough with `if kind != "unknown":
  return False` leaves all 28 tests green, so the over-broad branch is both unnecessary
  and untested.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:321`: the exclusion list
  stops one death short. `died_of_reported_infra = terminal["transient"] and rc not in (0,
  TIMEOUT_RC)` deliberately spares the run *the harness killed* on its wall-clock bound,
  but not the run the harness killed on its **memory** bound (#420) or one a signal took.
  Measured on the patched tree: a stub leaf that emits a work event, then the incident's
  own `server_error` report, then dies of `SIGKILL` returns `(-9, …, produced=False)` →
  `.transient` → three attempts, each of which will hit the same cap. `_memory_cap_prefix`
  (`leaves.py:309-322`) puts every capped leaf one OOM away from this, and the brief
  explicitly fences signal-death out as #510's ("neither #506's transient nor #421's
  preflight"), so this patch is silently reclassifying an excluded case from substantive
  to transient. One predicate (`rc > 0`, or the same `TIMEOUT_RC`-style exclusion for a
  negative/128+n status) closes it; the missing case is worth a test either way.

- **NEEDS-HUMAN** — `template/src/pdca_harness/leaves.py:693-704` and `:728-730` are inside
  `_invoke_leaf_resilient`'s **body**, which the brief reserves for sibling child-1
  ("`_invoke_leaf_resilient`'s body, `do_build`, and the artifact harvests are sibling
  child-1's … this child changes only `progress.py`, the four prose sites in `leaves.py`,
  one comment in `assemble.py`") and which the last sign-off flagged as an *unresolved*
  ownership question to settle "before either lands" (carry-forward item 3). The builder
  resolved it unilaterally: the docstring is rewritten and the retry line now prints "on
  transient infra". The prose is now true — but this is the one region the split exists to
  keep disjoint, and 532 is still movable, so the merge-order collision is a human call,
  not a builder's.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:617-621`: the mark is read
  in two spellings, the scope in one. `_terminal_error` deliberately accepts the persisted
  **transcript** spelling `isApiErrorMessage` alongside the stream's `is_api_error_message`
  ("keying on one of them would leave the incident unfixed"), but decides whose death it
  was from `parent_tool_use_id` only — a field the transcript shape does not have (it
  carries `isSidechain`; see the pinned `claude_api_error_death.transcript.jsonl`). Since
  `.get()` returns `None` for an absent key, a transcript-shaped **sidechain** record —
  `{"type":"assistant","isSidechain":true,"isApiErrorMessage":true,"error":"overloaded",…}`
  — is classified `_REPORT`, returns `produced=False`, is retried, and the retained
  diagnostic names a sub-agent's blip as the leaf's own death. Verified on the patched
  tree: `(1, 'API Error: 529 the API is at capacity\n', False)`. No 2.1.233 emitter puts
  that shape on stdout, so this is not reachable today — but that is an argument for
  deleting the transcript-spelling branch, not for keeping half of it: either the shape can
  appear (then honour `isSidechain` / treat a missing `parent_tool_use_id` as unknown
  scope) or it cannot (then the branch and its test assert a record no vendor emits). It is
  the same scope family this round was rebuilt to close.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:425-427` (and
  `_note_terminal`'s docstring at `:663-666`): the claim that excluding `result` from
  `_WORK_EVENT_TYPES` is load-bearing ("Let it win and the death this fix exists for is
  retried zero times again, with the suite green") is unasserted. Mutation-tested: adding
  `"result"` to `_WORK_EVENT_TYPES` leaves all 28 tests **green**, because every wrap-up the
  suite emits carries `is_error` and therefore takes the `_note_terminal` branch, never the
  clearing `elif`. The exclusion only bites for a text-less `is_error` result
  (`{"type":"result","subtype":"success","is_error":true,"result":""}` → `_terminal_error`
  returns `("",False,"")` at `:626-627` → falls to the clearing branch), and no case covers
  it. One event appended to `test_report_survives_the_wrapups_that_name_no_cause` fixes the
  gap. (For contrast, eight other mutations I planted — dropping the sub-agent scope check,
  making `_note_terminal` newest-wins, unscoping `_is_main_session_work`, letting prose
  promote a permanent kind, classifying on `TIMEOUT_RC`, dropping the `[sub-agent report…]`
  label, appending under `capture`, reading the wrap-up's prose — were each caught by a
  named test. The suite is strong; this is its one blind spot.)

Attempted and could **not** refute: the red leg is not vacuous (23 real assertion failures,
no import/collection error, fixtures present on both legs); the two fixture-replaying cases
skip rather than error when `fixtures/` is absent; `capture=True` returns the child's stdout
byte-identical with the append suppressed (`:307`); the codex format degrades silently
(`:608-609`); a stream-less family still reports `produced=True` (`leaves.py:678`); the
`TIMEOUT_RC` path is not reclassified; `rc == 0` keeps `produced`'s documented meaning
(carry-forward item 2 closed); the retained report rides `LeafError.output` into
`build.error.log` via `_format_leaf_attempt` (`leaves.py:1785`), so criterion (iii) reaches
the builder's log without touching child-1's harvest; #420's post-mortem still appends after
it; and `tests.test_progress test_leaf_resilience test_build_error_log test_leaf_status
test_leaf_memory_log` (80 tests) are green on the patched tree.

### Advisory — code-review

# Advisory code review — issue #533 (a leaf's own terminal error is kept and read)

Scope: correctness bugs the patch introduces, and reuse/simplification/efficiency. Grounded
on `$PDCA_TARGET` (patch applied, working tree). Both blocking defects from the prior
sign-off appear genuinely fixed in this round, not just re-worded:

- **Main-session scoping (prior item 1)** is real: `_terminal_error` (`progress.py:455-462`)
  routes a marked report to `_REPORT` only when `parent_tool_use_id is None`, else to
  `_SUBAGENT_REPORT`; `_note_terminal` (`progress.py:518-520`) enforces
  `_TERMINAL_PRECEDENCE = {subagent:1, wrapup:2, report:3}` so neither a sub-agent report nor
  a wrap-up can overwrite a main-session `_REPORT`, while a **second** main-session report
  (same precedence) still wins — matches `test_a_trailing_subagent_report_does_not_overwrite_the_main_sessions`
  and `test_a_second_marked_report_wins_outright`, both of which I traced by hand against
  `_note_terminal`'s precedence table and confirm are correct.
- **`produced`'s contract on the success path (prior item 2)** is restored:
  `died_of_reported_infra = terminal["transient"] and rc not in (0, TIMEOUT_RC)`
  (`progress.py:268-269`) means `produced` is only forced False on a non-zero, non-timeout
  exit — `test_a_recovered_run_that_exits_zero_still_reports_produced` and
  `test_a_timed_out_run_is_not_reclassified_by_its_stream` both exercise this and pass.
- **Prior item 3** (the two extra restatement sites, `leaves.py:693` /
  `:724-726`-ish — `_invoke_leaf_resilient`'s docstring and its retry-backoff print) is no
  longer left contradictory: this patch updates both (`leaves.py:693-704`, `:728-730`) so the
  operator-facing "with no output (transient)" message and docstring no longer contradict the
  widened definition.

## Findings

- NEEDS-HUMAN — `leaves.py:693-704` and `:728-730` (the `_invoke_leaf_resilient` docstring
  and its retry-backoff print line) are two of the "fifth and sixth restatement" sites the
  prior sign-off flagged as an **unresolved scope question between this child and sibling
  child-1** (issue_532, which owns `_invoke_leaf_resilient`'s *body*, `do_build`, and the
  harvest sites per the brief's Ordering note). This patch has unilaterally taken prose
  ownership of those two lines without any visible coordination artifact in this bundle
  (build-notes.md is withheld from this leaf, so I can't confirm it was settled there
  either). The brief's own recommended merge order is child-1 first, then this one — if
  child-1's patch also touches these same lines (plausible, since they sit inside the
  function child-1 owns the body of), that is a foreseeable merge conflict at publish, not a
  bug in this diff standalone. This is exactly the item the prior sign-off said must be
  "settle[d]…before either lands"; nothing here demonstrates that settlement happened. Human
  call, not something Do can resolve by re-iterating this slice alone.

- Minor / non-blocking — `_kind_is_transient` (`progress.py:473-485`) falls back to the
  `_TRANSIENT_CAUSE_RE` regex for **any** kind that is in neither
  `_CLAUDE_TRANSIENT_ERROR_KINDS` nor `_CLAUDE_PERMANENT_ERROR_KINDS`, but its own docstring
  and the module's `# ----` banner comment (`progress.py:296-301`, `:478-480`) describe this
  path as reserved for kind `"unknown"` specifically. Today the two enums plus `"unknown"`
  exhaust the vendor's documented kind enum quoted in `fixtures/README.md`, so the two
  descriptions coincide in practice — but the code is written more permissively (silently
  regex-classifies any *future*, currently-unlisted kind) than the prose promises. No test
  exercises an unlisted-and-not-`"unknown"` kind. Worth a one-line docstring correction
  ("or any kind not yet in either set") the next time this file is touched; not worth
  reopening the slice for.

- Minor / non-blocking (efficiency) — the per-line stream drain (`progress.py:236-248`) now
  runs up to four independent `json.loads` calls on the same line
  (`_is_session_event`, `_terminal_error`, optionally `_is_main_session_work`, then
  `_stream_tool_label`), where two (`_is_session_event` + `_stream_tool_label`) already
  existed pre-patch. This is the shape the brief explicitly asked for ("beside
  `_is_session_event`, in the same shape") and stream lines are small/I-O bound rather than
  CPU-bound, so it's not a real hot-path concern — noting only because the lens asks for it,
  not as something to fix.

No other correctness issues found: `_note_terminal`'s precedence table, the `capture`
short-circuit (`progress.py:253`, verified `tee_err` is always true whenever `stream_json`
is true and terminal state could be populated, so no output is silently dropped), the
`_WORK_EVENT_TYPES` exclusion of `result`, and the `TIMEOUT_RC` carve-out all check out
against the new test suite and against the C4 gate's red leg (`gate-logs/C4-verify.log`),
which fails for the right reasons pre-fix (wrong/absent retention text, wrong transient
verdict) — not a vacuous red.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C3 Change — Confirm this child owns the `_invoke_leaf_resilient` documentation/status-string edits and sibling issue 532 has dropped them — the original scope assigns that body to the sibling while carry-forward requires ownership to be settled, so dual ownership risks a stacked-patch conflict (`template/src/pdca_harness/leaves.py:681`; `brief.md:101`; `brief.md:234`).
- [ ] T5 Judgment — Approve the overall idiom and maintainability of the vendor-specific retry classifier — an affected-path PR query found only non-overlapping open hunks (#524/#520) and no closed-unmerged match, but retry-policy mistakes can multiply expensive sessions or suppress valid recovery (`template/docs/INTEGRATION.md.jinja:55`; `brief.md:175`).
- [ ] Validation — fitness-to-purpose — Decide whether observed transcript records plus stream shapes derived from Claude Code 2.1.233 are representative enough of live terminal failures — the real outage was not induced, so production fitness still turns on that vendor-grounding assumption (`template/tests/fixtures/README.md:13`; `template/tests/fixtures/README.md:51`).
- [ ] `leaves.py:693-704` and `:728-730` (the `_invoke_leaf_resilient` docstring

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
- Iteration delta (if iterating): Rejected on the implementation, not the slice or the evidence. This round is well evidenced — C5 is a genuine pass (unlike the sibling's), the vendor grounding was re-derived from the shipped 2.1.233 binary rather than trusted from fixtures/README.md, and the suite caught eight of nine planted mutations. Both blocking defects from the previous round (main-session scoping, `produced`'s contract on the success path) are genuinely fixed, not re-worded. Do NOT re-cut this slice. What follows are local defects in the classifier, each confirmed by reading patch.diff directly. Must close before re-submission: 1. The classifier reads prose for ANY unrecognised kind, and its own docstring says it must not. Two defects in three lines of `_kind_is_transient` / `_terminal_error`: (a) `kind = str(ev.get("error") or "unknown")` collapses an ABSENT `error` key into the string "unknown" — but 2.1.233's queryLoop catch-all marks a message (`isApiErrorMessage:!0`) while leaving `error` undefined, which is the shape ANY exception escaping the loop takes; (b) the final `return any(_TRANSIENT_CAUSE_RE .search(t) for t in texts)` fires for every kind outside the two frozensets, while the docstring immediately above states "The text is read **only** for the kind the CLI leaves ``unknown``". Consequence, verified through the production path: a dead MCP server (`connect ECONNREFUSED`), `fetch failed`, `socket hang up`, `terminated` are all retried to the attempt budget and the operator is told "transient infra — safe to re-run" for a config failure that fails identically every time — the exact conflation PR #285's review is cited against. It is also the drift hole: the CLI auto-updates and the harness pins nothing, so any kind the vendor adds after 2.1.233 gets classified by regex. Make the code match its docstring (`if kind != "unknown": return False` keeps all 28 tests green, so the loose branch is both unnecessary and untested), and distinguish an absent `error` key from a literal "unknown". 2. Signal deaths are not excluded from the transient class, and the brief fences them out. `died_of_reported_infra = terminal["transient"] and rc not in (0, TIMEOUT_RC)` spares the run the harness killed on its WALL-CLOCK bound but not the one it killed on its MEMORY bound (#420), nor one a signal took. Measured: a stub leaf that emits a work event, then the incident's own `server_error` report, then dies of SIGKILL returns `(-9, ..., produced=False)` -> transient -> three attempts, each of which will hit the same cap. `_memory_cap_prefix` puts every capped leaf one OOM away from this. The brief states a signal death "is neither #506's transient nor #421's preflight" (#510's own question), so this patch must not silently reclassify it. Add the exclusion and a test. COORDINATE WITH SIBLING issue_532 (also iterate-do this round): the two children have OPPOSITE holes at the same boundary. 532's `_builder_retryable` excludes `rc < 0` but misses a positive 137 (a wrapper argv — `sh -c`, `docker run`, the documented `local-build` shape — reports its child's OOM SIGKILL as 137). 533 excludes neither. The signal-death boundary wants deciding ONCE and spelled the same way in both, rather than each child inventing half of it. 3. The transcript spelling is half-supported. `_terminal_error` deliberately accepts the persisted transcript spelling `isApiErrorMessage` alongside the stream's `is_api_error_message`, but decides WHOSE death it was from `parent_tool_use_id` only — a field the transcript shape does not carry (it carries `isSidechain`). Since `.get()` returns None for an absent key, a transcript-shaped SIDECHAIN record is classified as the main session's own death, retried, and the retained diagnostic names a sub-agent's blip as the leaf's death. Not reachable from any 2.1.233 emitter today — which is an argument for resolving the branch, not for keeping half of it: either the shape can appear (then honour `isSidechain`, or treat an absent `parent_tool_use_id` as unknown scope) or it cannot (then delete the transcript-spelling branch and the test asserting a record no vendor emits). 4. The `result` exclusion from `_WORK_EVENT_TYPES` is load-bearing but unasserted. The comment claims that letting `result` count as work means "the death this fix exists for is retried zero times again, with the suite green" — and mutation testing confirms exactly that: adding `"result"` leaves all 28 tests green, because every wrap-up the suite emits carries `is_error` and so takes the `_note_terminal` branch, never the clearing `elif`. The exclusion only bites for a text-less `is_error` result (`{"type":"result","subtype":"success","is_error":true,"result":""}`), which no case covers. One event appended to `test_report_survives_the_wrapups_that_name_no_cause` closes it. OWNERSHIP QUESTION — RESOLVED AT SIGN-OFF, this child KEEPS the prose: The `_invoke_leaf_resilient` docstring and retry-print edits (`leaves.py:693-704`, `:728-730`) stay with THIS child. Sibling issue_532 has been instructed in its own iterate-do carry-forward to leave those two prose sites alone. Rationale: 533 is the child that changes what "transient" MEANS, so it is the child that must restate it; 532's version of that print keeps the old "with no output (transient)" wording, which this child's whole purpose is to retire. Verified mechanically at sign-off that the two patches DO collide — both rewrite the same retry-print line and the same docstring, and 533's hunk carries as trailing context an `error_log.write_text(...)` line that 532 deletes. Keep these edits; do not hand them back. Section 6's fourth bullet is a truncated duplicate of its first ("`leaves.py:693-704` and `:728-730` (the `_invoke_leaf_resilient` docstring" — cut off mid-sentence). An assembly artifact, not a finding; noted so the next round does not chase it as a separate item. Section 6 items are left OPEN (an iterate does not require them cleared). Item 1's substance — the ownership question — is settled above; items T5 and Validation remain genuinely open and should be re-examined once 1-4 are closed.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
