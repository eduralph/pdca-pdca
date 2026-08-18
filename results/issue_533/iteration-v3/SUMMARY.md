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

Task under review: retain a leaf CLI's marked terminal API-error report and classify its failure by the vendor-marked cause, including after substantive work.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decidable: only a terminal main-session transient cause may alter retry classification, while permanent, recovered, sub-agent, and unmarked reports remain distinguishable and diagnostics survive (`template/src/pdca_harness/progress.py:100`). |
| C2 Reproduction (red pre-fix) | PASS | My independent pre-fix run failed 30 of 34 focused cases on retry and retention, matching the frozen red leg's 30 failures (`gate-logs/C4-verify.log:320`). |
| C3 Change | PASS | The resolved slice boundary is honored: classification and retention stay in the shared stream reader, while downstream retry-policy edits are explanatory prose only (`template/src/pdca_harness/progress.py:231`, `template/src/pdca_harness/leaves.py:693`). |
| C4 Verification (red→green) | PASS | Restoring the patch changed the independently rerun focused suite from 30 failures to 34/34 green; the frozen oracle records the same red→green and a non-vacuous red (`gate-logs/C4-verify.log:31`, `gate-logs/C4-verify.log:323`). |
| C5 Causal adequacy | PASS | The fix reads and retains the actual marked stream record at the production drain, with closed defaults for unsupported formats and unknown vendor kinds; the production-path audit confirms the tests import `pdca_harness` (`template/src/pdca_harness/progress.py:611`, `gate-logs/C5-prod-path.log:10`). |
| T1 Structure | PASS | The terminal classifier is colocated with the existing per-family stream classifier and shares one sub-agent predicate for report and recovery decisions, avoiding divergent ownership rules (`template/src/pdca_harness/progress.py:471`, `template/src/pdca_harness/progress.py:755`). |
| T2 Shape | PASS | Both documentation shape checks and host-CI parity completed with clean lint, render, and link audit results (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The focused suite and my full offline driver rerun are green; frozen evidence also records 1,792 driver tests plus the render/update-compat suite passing (`gate-logs/T3-suite.log:1627`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check, and the deferred row states their substantive audit will run at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Affected-path inspection found no competing terminal-error change on current upstream `acb214a`; open overlaps are distant, and regression cases directly cover the rejected prior-art precedence failures (`template/tests/test_terminal_error_classification.py:396`, `template/tests/test_terminal_error_classification.py:481`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Approve the vendor-event boundary and fresh-reinvoke policy together with sibling issue #532 — the live long-running builder path is not exercised by this slice alone, so a mismatch could retry permanent failures or discard costly work; compare the deployed CLI's emitters/transcripts with the recorded provenance before sign-off (`template/tests/fixtures/README.md:121`). |

### Advisory — adversary

# Adversarial pass — issue_533 (a leaf's own terminal error is kept and read)

Re-ran the asserted red→green independently on a copy of `$PDCA_TARGET`: **green 34/34**
with the patch, **red 30/34** with the three production files reverted (`git checkout --`
on `progress.py` / `leaves.py` / `assemble.py`, test + fixtures kept). The four that pass on
red are the (iv) "nothing else changes" invariants, by design. The suite drives the real
spawn path — a real `subprocess`, `progress.run_with_heartbeat` and
`leaves._invoke_leaf_resilient` — with no mock, no stub classifier and no re-implementation
of the production logic, so C4/C5 are honest. I also re-derived the load-bearing vendor
claims from the shipped `claude-code 2.1.233` binary rather than from `fixtures/README.md`:
the stream emitter's `is_api_error_message:!0` + top-level `error:r.error`, the main loop's
hard-coded `parent_tool_use_id:null` vs the `agent_progress` branch's `e.parentToolUseID`,
`new Set(["rate_limit","overloaded","server_error"])`, the `Yd({content:…,error:"unknown"})`
last resorts, and `api_error_status` only on the `variant:{subtype:"success"}` result — all
confirmed. Findings below are what survived that.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/leaves.py:102` and `:700-702` state a rule
  the code does not implement: a signal-killed leaf *is* still classified transient and
  retried when it died before its first substantive stream event.** `LeafError`'s new
  docstring says "A child a SIGNAL killed (the memory cap, an OOM, a Ctrl-C) is neither
  shape", and `_invoke_leaf_resilient`'s says "Any other failure of a leaf that ran —
  including one a **signal** killed, whatever its stream last said (#510) — … is
  substantive: do not retry." Measured through the production path
  (`_invoke_leaf_resilient`, claude family, stream on): a stub leaf that emits **no** stream
  event and dies of `SIGKILL` returns `LeafError(returncode=-9).transient is True` and is run
  **3 times**; the wrapper spelling (`rc=137`, no stream events) likewise. `is_signal_death`
  is consulted only in the new branch (`progress.py:358-359`), while `LeafError.transient`
  (`leaves.py:110-115`) is still `not produced`. That is exactly the `_memory_cap_prefix`
  (#420) shape the sentence names — a capped leaf OOM-killed before its first `assistant`
  event buys three more OOMs — and it is the half of last round's item 2 that was left open
  while the prose claims both halves. Minimal in-scope fix is to narrow the two sentences to
  the reported-infra branch; extending `is_signal_death` into `transient` itself changes
  #138's base behaviour and is the #510 boundary decision, so that variant is a human call.
  Suite gap: both signal cases (`tests/test_terminal_error_classification.py:599`, `:612`)
  emit a work event first, so neither reaches this shape.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/progress.py:465`: the `"user"` member of
  `_WORK_EVENT_TYPES` is load-bearing and unasserted — deleting it flips a real
  classification with all 34 tests still green.** Mutation-measured: with
  `_WORK_EVENT_TYPES = {"assistant"}` the suite is `OK`, yet the stream
  `[assistant work, marked server_error report, main-session user tool_result, exit 1]`
  goes from `produced=True` / 1 attempt to `produced=False` / 3 attempts — i.e. a leaf that
  recovered through a tool cycle and then failed on its own merits becomes retryable, the
  criterion-(ii) inversion. Every clearing case in the suite (`:369`, `:245`) clears with an
  `assistant` event; the vendor emits main-session tool results as `type:"user"`,
  `parent_tool_use_id:null` (confirmed in 2.1.233), which is the only reason the member is
  there. This is the exact twin of last round's item 4 (the `result` *exclusion*, now
  properly pinned by `:245`'s `success-with-no-text` case) — one case with a `user`
  tool_result after the report closes it.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/progress.py:687-688` and `:567`: the
  `result` branch's two discriminators are both unasserted.** Emptying
  `_TRANSIENT_STATUSES = frozenset({408, 409, 425, 429})`, or dropping the
  `ev.get("subtype") == "success"` guard, each leaves all 34 tests green. The only
  status-carrying case (`tests/test_terminal_error_classification.py:271`) uses 503, which is
  decided by the `500 <= status <= 599` range, and `wrapup_execution_error` (`:123`) never
  sets `api_error_status`, so the `error_during_execution` case at `:497` cannot exercise the
  subtype guard. The guard is vendor-*correct* (2.1.233 attaches `api_error_status` only to
  the `success` variant), so this is coverage, not behaviour: add `api_error_status: 503` to
  the execution-error event (must stay substantive) and one 429 wrap-up.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/assemble.py:80` and
  `template/src/pdca_harness/leaves.py:2544` replace one half-true restatement with the other
  half, so the codebase still carries two statements of the definition.** Both were narrowed
  to "ran, died of infra it reported", dropping #138's original shape — a leaf that emitted
  nothing at all and exited non-zero — which still routes to the same `_FAIL_TRANSIENT` /
  `LEAF_STATUS_INFRA` pair (the suite's own case at
  `tests/test_terminal_error_classification.py:628` produces exactly that leaf). Their
  siblings at `leaves.py:2552-2554` and `:2611-2616` get it right ("produced no substantive
  output, **or** …"). Since "the definition is restated in N places and goes stale the moment
  it widens" is the invariant this slice exists to serve, a newly-wrong restatement is the
  same defect in the other direction. (`template/tests/test_leaf_status.py:84`'s "ran, no
  output → retryable blip" comment is stale for the same reason and is not fenced off by the
  brief.)

- NEEDS-HUMAN — **`template/src/pdca_harness/progress.py:237-240`: the clearing rule discards
  the retained *text* along with the verdict, so `(no output captured)` can still be the
  post-mortem for a leaf whose CLI did explain itself.** Measured on the resilient path:
  `[work, marked server_error report, main-session work]` + exit 1 with empty stderr writes
  `----- attempt 1 — exit 1 -----\n(no output captured) LeafError: …` — the artifact the
  brief calls "a post-mortem artifact that explains nothing" — even though the harness had
  the report text in hand. Criterion (iii) says the text is retained "for every marked
  terminal report, transient or not"; the patch's reading is that a recovered report is not
  *terminal*, which is defensible, so this is a fitness call rather than a bug. Cheap
  alternative if the human wants (iii) read literally: clear `transient`/`shape` but keep the
  text under a "recovered" label, which changes no classification.

## Attempted and could not refute

- **The evidence.** Red→green reproduced independently; no tautology, no over-broad
  assertion, no mocked-away defect; the C4 red leg fails on the *assertions* (30 of them),
  not on an import or a missing fixture: no symbol this patch adds is imported at module
  level, and the two fixture-replaying cases carry the `skipTest` guard the brief demanded
  (`tests/test_terminal_error_classification.py:281`, `:509`) — in this round's gate log the
  untracked fixtures survived the revert, so both went red on their retention assertions
  rather than skipping. Both gate traps avoided.
- **Prose-promotion.** Tried to promote a permanent cause through the text path: the
  permanent kinds, an unrecognised (post-2.1.233) kind, an *unstamped* marked report and the
  cloud-runner tail all stay substantive — last round's item 1 is genuinely closed, not
  re-worded. Likewise the transcript spelling (item 3: `isSidechain` honoured on both sides
  of the scope rule) and the main-session scoping.
- **Mutation battery (12).** Killed: `isSidechain` in `_is_subagent_event`, the shell
  `128+signum` spelling of `is_signal_death`, the `_note_terminal` precedence guard,
  `result`-as-work, the 5xx range, a subagent report classifying, and the retention append
  leaking under `capture`. Survivors are the three coverage items above plus two nits I do
  **not** file as findings: `_report_line`'s 500-char bound and `_MAX_SIGNUM`'s exact value
  are unasserted.
- **One precedence hole I could not ground.** A retained `_SUBAGENT_REPORT` is overwritten by
  a later `_WRAPUP` (`_TERMINAL_PRECEDENCE`, `progress.py:543`), which drops the
  `[sub-agent report, not the leaf's own death]` label and can classify transient off the
  wrap-up's status. I could not derive a 2.1.233 emission sequence that produces it (the
  vendor builds the `success` wrap-up out of the *main* transcript's last message), so I am
  not filing it — noted only so the next reader does not have to re-derive it.
- **Neighbour behaviour.** Checked every `run_with_heartbeat` caller: all but the leaf spawn
  pass `capture=True`, so the appended report cannot corrupt a gate's evidence line
  (`gates.py:559`, `publish.py:833`, `leaves.py:767`), and `_invoke` discards `output` on
  `rc == 0`.

### Advisory — code-review

# Advisory code review — issue #533 (terminal-error classification), round 3

Second lens: correctness bugs the patch introduces, plus reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET` (target/), not build-notes.md.

## Findings

- NEEDS-HUMAN [impl] — `target/template/src/pdca_harness/assemble.py:85` (`_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]`)
  still reads `"leaf did not run (transient infra — safe to re-run)"`. This is the exact
  string prefixed onto every §6 item for a placeholder carrying the `infra-empty` marker
  (`_items_from_artifact`, `assemble.py:168-173`) — it is what the human actually reads at
  sign-off. The patch widens `LEAF_STATUS_INFRA` (via `_failure_class`/`LeafError.transient`,
  `leaves.py:106-108`, `2549-…`) to also cover a leaf that *did* run substantively — the
  brief's own headline case, an 18-minute builder whose stream ended on the CLI's own marked
  transient report (`progress.died_of_reported_infra`, `progress.py:358-360`). For that exact
  leaf the §6 row will now read "leaf did not run (transient infra — safe to re-run) — …",
  which is false: the leaf ran, at length, and the death is legible in the retained report a
  few lines below it. The patch already rewrote the *comment* directly above this dict
  (`assemble.py:80`, "ran, died of infra it reported") and the in-body prose
  `_unavailable_classification` builds for the placeholder itself (`leaves.py:2611-2616`,
  "having produced nothing, or ending on its own report…") — but missed this dict two lines
  further down, which is the fifth downstream restatement of the definition the brief's own
  invariant warns will "go stale the moment it widens" (only four were enumerated in
  Citations expected, plus this dict). `template/tests/test_leaf_status.py:135,188` pins the
  stale string, so nothing in the suite would catch the mismatch — it is silent, not
  gate-visible. One-line fix (e.g. `"leaf failed on transient infra — safe to re-run"`),
  but it needs a human/builder decision on the exact wording since it's user-facing prose,
  not a logic change.

- `target/template/src/pdca_harness/leaves.py:2520` — the comment above the reviewer's
  `_invoke_leaf_resilient` call, `"A transient (no-output) reviewer failure is retried with
  backoff…"`, is the same stale, narrower definition (developer-facing only, not
  operator-facing like the finding above, so lower stakes — no `[impl]` tag warranted on its
  own, noting it here since it's the same class of drift the invariant calls out and it sits
  right next to the fifth-site item above).

## Everything else checked and found sound

- `progress._note_terminal`'s precedence table (`_TERMINAL_PRECEDENCE`, `progress.py:...`)
  correctly lets a same-shape record overwrite newest-wins while blocking a farther-shape
  record (wrap-up, sub-agent) from burying a nearer one; traced through all the ordering
  permutations the test suite exercises (report→wrapup, report→subagent→wrapup,
  subagent→report) and the logic matches.
- `is_signal_death`'s dual-spelling boundary (`rc < 0` vs. shell `128+signum`) correctly
  excludes `TIMEOUT_RC` (-1001) without a special case, and `died_of_reported_infra`
  correctly gates on `rc not in (0, TIMEOUT_RC)` — the success-path (`rc == 0`) restoration
  of `produced`'s documented contract (iteration-1's defect #2) holds: `terminal` state can
  be left set at `rc == 0` and it is provably inert there.
  - `_kind_is_transient` now matches its own docstring: an absent `error` key is
    distinguished from the literal `"unknown"` (`kind = raw_kind if isinstance(raw_kind, str)
    and raw_kind.strip() else None`), and the free-text regex only ever runs for
    `kind == "unknown"` — iteration-2's defect #1 is closed, confirmed by reading the branch,
    not just the tests.
- `_is_subagent_event` is the single predicate used on both sides (classify / clear), so the
  stream spelling (`parent_tool_use_id`) and the persisted-transcript spelling
  (`isSidechain`) can't drift apart — iteration-1's main-session-scoping defect and
  iteration-2's transcript-spelling defect both check out against the current source.
- `_WORK_EVENT_TYPES` excludes `result` (`progress.py:465`), so a wordless `is_error` result
  can't silently clear a report via the "main session carried on" branch — iteration-2's
  defect #4 — and the drain's `if shape: ... elif ...:` structure keeps a report-bearing line
  from also being read as a clearing line.
- No new resource leak or concurrency bug: `terminal` is mutated only by the single drain
  thread and read by the caller after `reader.join()`, the same pattern the pre-existing
  `produced` / `latest_tool` dicts already use. The test helper `_fd1_parked`
  (`test_terminal_error_classification.py`) opens then closes the sink file *after*
  `dup2`-ing it onto fd 1 — correct idiom (the duplicate keeps the description alive), not a
  leak, despite looking suspicious at a glance.
- Re-parsing the same stream line's JSON across `_is_session_event` / `_terminal_error` /
  `_is_main_session_work` / `_stream_tool_label` is redundant, but it is the pre-existing
  shape of this module (`_is_session_event` and `_stream_tool_label` already each re-parse
  independently) and the brief explicitly directs the new reader to sit "beside it, in the
  same shape" — not a new inefficiency this patch introduces, and not hot enough (one leaf's
  own stdout) to be worth a refactor here.
- C4's red/green legs (`gate-logs/C4-verify.log`) are genuine: the red leg fails on the
  production assertions (`self.assertFalse(produced)`, retained-text `assertIn`s), not on an
  import/collection error, so the new test file is exercising the real code path, not a copy.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Approve the vendor-event boundary and fresh-reinvoke policy together with sibling issue #532 — the live long-running builder path is not exercised by this slice alone, so a mismatch could retry permanent failures or discard costly work; compare the deployed CLI's emitters/transcripts with the recorded provenance before sign-off (`template/tests/fixtures/README.md:121`).
- [ ] **`template/src/pdca_harness/leaves.py:102` and `:700-702` state a rule
- [ ] **`template/src/pdca_harness/progress.py:465`: the `"user"` member of
- [ ] **`template/src/pdca_harness/progress.py:687-688` and `:567`: the
- [ ] **`template/src/pdca_harness/assemble.py:80` and
- [ ] **`template/src/pdca_harness/progress.py:237-240`: the clearing rule discards
- [ ] `target/template/src/pdca_harness/assemble.py:85` (`_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]`)
- [ ] size backstop — this slice is behaving oversized: patch is 99 KB (threshold 80 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Human rationale (sign-off, issue_533): iterate-plan concerning the replanning of its sibling. Not rejected on the implementation. This round is strong — the reviewer returned PASS on all ten cells, the adversary reproduced red->green independently (30/34 red, 34/34 green) on the real spawn path with no mocked classifier, re-derived the vendor claims from the shipped `claude-code 2.1.233` binary, and killed 6 of 12 mutations. C5 is a GENUINE pass here (a real new test file importing `pdca_harness`) — the C5 vacuity that decided sibling issue_532 does NOT apply to this bundle and must not be carried across. Why it returns to Plan anyway: - The Validation fitness item is not free-standing: it asks to approve the vendor-event boundary and the fresh-reinvoke policy "together with sibling issue #532". #532 was sent to iterate-plan in this same session, so that boundary is being re-cut. Clearing this item now would approve one half of a boundary whose other half is being redrawn. The re-plan must settle the two children against each other, not separately. - Signal-death is the concrete instance of that shared boundary, and each child owns the opposite half: #532's `_builder_retryable` excludes `rc < 0` but misses a positive 137; this child's `died_of_reported_infra` excludes neither. Decide it ONCE across both, and state where the #510 line falls, rather than letting each child invent half of it. - Slice size: 99 KB against the 80 KB backstop, and it is not fixture bloat — 44 KB is production source (`progress.py` 32.6 KB, `leaves.py` 10.5 KB), 34 KB test, 19 KB fixtures + README. Round 3 of implementation-shaped findings each round. Author the split at Plan (`pdca-pdca split 533`, then `pdca-pdca split 533 --accept`). Carry into whichever child keeps the mechanism (all confirmed by measurement, not reading): - Prose/code mismatch with a live cost: `leaves.py:102` and `:700-702` state that a signal-killed leaf is not transient, but `LeafError.transient` is still `not produced`, so a leaf emitting no stream event and dying of SIGKILL (or the wrapper's rc=137) is classified transient and run 3 times — a memory-capped leaf buys three more OOMs. Both signal tests emit a work event first, so neither reaches the shape. - Operator-facing falsehood: `assemble.py:85` `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` still reads "leaf did not run (transient infra — safe to re-run)", and that string is prefixed onto the §6 items the human reads. The patch widens that class to cover a leaf that DID run substantively — the brief's own 18-minute-builder headline case — so §6 will assert "did not run" directly above the retained report proving it ran. It is the fifth restatement site (four were enumerated), and `test_leaf_status.py:135,188` pin the stale string, so the suite cannot catch it. - Definition still restated two contradictory ways: `assemble.py:80` and `leaves.py:2544` were narrowed to "ran, died of infra it reported", dropping #138's original emitted-nothing shape, which still routes to the same `_FAIL_TRANSIENT` / `LEAF_STATUS_INFRA` pair. Their siblings at `leaves.py:2552-2554` and `:2611-2616` get it right. A newly-wrong restatement is the same defect this slice exists to prevent. (`test_leaf_status.py:84`'s comment is stale for the same reason.) - Two surviving mutations = unpinned guards: the `"user"` member of `_WORK_EVENT_TYPES` (`progress.py:465`) is load-bearing — deleting it flips a recovered-then-substantively- failed leaf to retryable, the criterion-(ii) inversion, with all 34 tests still green; and both `result`-branch discriminators (`_TRANSIENT_STATUSES`, the `subtype == "success"` guard, `progress.py:687-688` and `:567`) are unasserted. - Fitness call to settle in the brief, not in Do: the clearing rule (`progress.py:237-240`) discards the retained text along with the verdict, so `(no output captured)` can still be the post-mortem for a leaf whose CLI did explain itself. Criterion (iii) says the text is retained for every marked terminal report; the patch reads a recovered report as not terminal. Decide which reading is wanted. §6 NEEDS-HUMAN items were left open — none were cleared.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
