# Result — issue 539 / what-a-transient-leaf-death-is-decided-once

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch: (i) a leaf whose stream carried a marked terminal error
  report and then exited non-zero is classified **transient** when the vendor marked the cause
  transient — a lost or interrupted connection, an overload or 5xx, a mid-session rate-limit
  rejection — **however much work came first**; (ii) it is **not** so classified when the vendor
  marked the cause **permanent** (invalid request, authentication, billing), nor for a kind this
  harness does not recognise, nor for a report the vendor left **unstamped** — no prose inside a
  marked report may promote a permanent cause, and a leaf that merely mentions or quotes an error
  is untouched; a report the CLI **recovered** from, with real **main-session** work following, is
  not the leaf's death; and a **sub-agent's** report never classifies (the CLI has its own
  recovery for those); (iii) a leaf a **signal** killed is never classified transient on the
  strength of having emitted nothing — in **both** returncode spellings, `-signum` from a direct
  child and the shell's `128+signum` from a wrapper argv — so a memory-capped leaf is not re-run
  into the same cap, while the harness's own wall-clock kill (`progress.TIMEOUT_RC`) keeps today's
  meaning; (iv) **every** site that restates the definition states the same true thing, covering
  **both** shapes — a leaf that produced nothing at all, **or** one that ended on its own marked
  transient report — and the operator-facing `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` no longer
  asserts "did not run" of a leaf that ran; `template/tests/test_leaf_status.py` is updated with
  it rather than left pinning the stale string; (v) child-1's retention is **unchanged** — in
  particular the report text is still retained for a report the session recovered from, even
  though this child's clearing rule removes the *verdict*; (vi) nothing else changes: a
  stream-less family still reports substantive (`leaves.py:666-670`), `capture` still returns the
  child's raw stdout unmodified, codex/gemini degrade to today's behaviour, a leaf that succeeds
  is spawned and reported exactly as today, and the #420 post-mortem still rides `output` into the
  same log.
- Repo + branch target: eduralph/pdca-harness @ main (base `acb214a`; every `path:line` here
  was re-verified against it while this proposal was written)
- Scope (one logical fix) / out of scope: 

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

Review transient leaf-death classification so reported API failures can retry after work, signal deaths do not retry, and operator messages accurately describe both cases.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Six criteria distinguish retryable causes, permanent errors, recovery, signals, retention, and unchanged callers; scope exceptions require reconciliation below (`brief.md:29`, `brief.md:110`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the three production changes leaves 40 classification tests runnable and produces 21 assertion failures, including connection-loss and signal cases (`review-red.log:1`; `template/tests/test_terminal_error_classification.py:221`). |
| C3 Change | FAIL | A typed permanent gateway failure in the supported transcript spelling is retried three times because `apiError` is overlooked; its `api_error` stream equivalent correctly gets one attempt (`template/src/pdca_harness/progress.py:838`; `review-typed-error.log:1`). |
| C4 Verification (red→green) | PASS | Restoring the patch makes all 74 classification/retention tests pass; the frozen C4 log verifies all three changed test modules, but they omit the C3 transcript case (`review-green.log:1`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Cause classification and signal exclusion directly address the proxy defect; recovered work clears the verdict while preserving evidence, with no added capability probe masking a load-time cause (`template/src/pdca_harness/progress.py:259`; `template/src/pdca_harness/leaves.py:109`). |
| T1 Structure | PASS | Stream interpretation remains in progress and the retry decision remains in LeafError; the shared retry loop receives wording changes without structural edits (`template/src/pdca_harness/progress.py:803`; `template/src/pdca_harness/leaves.py:109`). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and diff whitespace check pass; frozen docs and host-CI evidence agrees (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite passes 2,021 tests with two skips; local root tests lack importable Copier, but the frozen gate actually passed all 24 root tests, including update compatibility (`gate-logs/T3-suite.log:38`; `review-suite.log:1656`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design; the substantive audit is deferred to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether to approve excluded retention-test and builder-message edits, and discharge the incomplete prior-art audit — the brief forbids those edits and this snapshot cannot establish merged plus closed/rejected history for every affected path (`brief.md:123`, `brief.md:139`, `brief.md:198`; `template/tests/test_terminal_error_retention.py:368`; `template/src/pdca_harness/leaves.py:2201`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether stub-driven evidence and derived vendor records suffice for real CLI failures — no live vendor API-error session was exercised, and the current-version stream contract rests on binary reading rather than an observed run (`template/tests/fixtures/README.md:106`, `template/tests/fixtures/README.md:158`). |

C3 finding (medium): preserve typed permanent causes in both accepted spellings. The classifier accepts `isApiErrorMessage` alongside `is_api_error_message` (`template/src/pdca_harness/progress.py:829`), but its unknown-kind exclusion checks only `api_error`. A transcript record carrying `apiError="gateway_session_expired"` falls through to prose matching. With the same “gateway session timed out; connection lost” text used by the existing stream test, it incorrectly spends the complete retry budget on a credential/session failure. The provenance note identifies that typed cause as a sign-in stop (`template/tests/fixtures/README.md:134`). This is a reproduced parser defect in an accepted input spelling, not a claim that a live CLI emitted this exact constructed record during review.

Observed through `_invoke_leaf_resilient`, with real Python child processes:

```text
stream: typed gateway_session_expired; transient=False; attempts=1
transcript: typed gateway_session_expired; transient=True; attempts=3
```

Reproduce from `$PDCA_TARGET/template`, with `TMPDIR` set to a scratch directory inside the harness cwd:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 - <<'PY'
import test_terminal_error_classification as t
case = t._StubLeafCase()
case.setUp()
event = t._report('unknown', 'API Error: gateway session timed out; connection lost')
event['isApiErrorMessage'] = event.pop('is_api_error_message')
event['apiError'] = 'gateway_session_expired'
event.pop('parent_tool_use_id')
err = case._run(t._stream(t._WORK, event))
print('transient:', err.transient, 'attempts:', case._runs())
assert not err.transient and case._runs() == 1
PY
```

Independent verification: `git stash push` was scoped to `assemble.py`, `leaves.py`, and `progress.py`, preserving the new tests; `git stash pop` restored the patch before the green leg. No source fix was made. The target includes prerequisite retention code and was usable, so there is no stale-target caveat. C4 passes for its asserted regression suite; it does not negate the additional C3 counterexample.

The local root runner reported `PDCA-UNVERIFIABLE` because `/usr/bin/python3` cannot import Copier (`review-root.log:6`). This is a local host limitation, not a patch failure or an undischarged Copier dependency: the frozen log shows the render/update cases actually ran. The vendor-contract dependency differs: the provenance note expressly says no real 2.1.284 API-error stream was observed. Sign-off should accept that evidence limitation explicitly or validate the kinds, typed causes, recovery traffic, and exit status against an actual CLI session.

For T5, the retention edits update assertions whose old values conflict with the intended classification, and the builder edit changes only diagnostic wording. They appear motivated by this task, but both cross explicit brief exclusions and require a scope decision. The brief records affected-path history for leaves/assemble and names rejected parent rounds; it does not supply a reproducible closed/rejected audit for every affected path. Investigation found exactly one synthetic base commit (`8ea9cca`) and no remotes; broader history cannot be established from this artifact-only target. The available `template/docs/INTEGRATION.md.jinja:80` leaves project-specific human-only items as TODO, adding no concrete items beyond this review contract.

### Advisory — adversary

# Adversarial review — issue #539 (what a transient leaf death is)

Lens: refute the red→green proof and find inputs that break the fix. Grounded on the patched
target at `$PDCA_TARGET`. Probes and mutants were run from this sandbox against a copy of the
source. The installed `claude` CLI (2.1.284) was greppable, so the vendor claims below were
checked against the binary, not taken on trust.

## The evidence holds

- C4's red is real, not vacuous. `gate-logs/C4-verify.log` shows the red leg failing on
  assertions: 21 of 40 in the new file, 2 in `test_leaf_status.py`, 3 in the retention file.
  None of them are import errors. The two replayed fixtures (`claude_api_error_death.stream.jsonl`,
  `…permanent…`) are child-1's and already on the base, so they are present on the red leg:
  `test_the_observed_incident_record_after_work_is_retried` goes red with "expected transient;
  rc=1", not with a skip. Every case drives `leaves._invoke_leaf_resilient` → `_invoke` →
  `progress.run_with_heartbeat` with a real subprocess stub, and the `sh -c` wrapper case
  really produces rc 137. I re-ran the four affected test files on the patched tree: 94 OK.
- The three guards the brief named as round-3 survivors are now pinned. With a mutant for
  each: dropping `"user"` from `_WORK_EVENT_TYPES` fails 2 tests, emptying
  `_TRANSIENT_STATUSES` fails 1, and dropping the `subtype == "success"` guard fails 1. So do
  mutants for the `_note_terminal` gate, both sub-agent checks, the `api_error` check on
  `unknown`, the `rc not in (0, TIMEOUT_RC)` guard, and each signal spelling.
- The drain logic survives the CLI's own recovery. In `-p` mode the binary's `Nd(...)` resumes
  a main session after a `truncatedAfterOutput` report ("Connection lost mid-response").
  Main-session work that follows clears the verdict (`progress.py:266-267`), and a later
  report sets it again. I found no event order that clears or keeps the verdict wrongly.

## Refutations

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:836`: every `rate_limit` report
  is treated as transient without looking at the typed `api_error` the vendor puts on it. The
  code reads `api_error` only for `unknown` (`:838`). But claude-code 2.1.284 stamps two
  entitlement stops as `error:"rate_limit"` with a typed cause:
  `apiError:"long_context_credits_required"` ("Usage credits required for 1M context") and
  `apiError:"model_requires_usage_credits"`. The wire converter `_o` puts `api_error` on the
  stream event, so the harness can see it. Probe through `_invoke_leaf_resilient`, with work
  followed by `{"error":"rate_limit","api_error":"long_context_credits_required",…}` and
  exit 1: the leaf runs **3 times** and is classed `transient`. The long-context case is the
  expensive one. Each fresh attempt runs until its context passes the limit again, so a long
  builder spends the whole budget re-doing the same work. That goes against criterion (ii): a
  billing/entitlement cause the vendor typed as permanent must not be retried. Fix: treat a
  `rate_limit` that carries any typed `api_error` as not transient (the plain 429 and the quota
  limit carry none), and add a test for it.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:799` and `:789`: the prose check
  for `unknown` reports matches a 5xx-looking number or the word `timeout` anywhere in the
  text. In this CLI a 5xx `APIError` is already stamped `server_error` and a 429 `rate_limit`.
  What falls through to `unknown` (`if(e instanceof Pt)return Qo({…error:"unknown"})`) is
  mostly a generic 4xx, with the JSON body in the text. Concrete cases the probe retries 3×:
  `API Error: 400 {…"invalid_request_error","message":"messages.536.content.0.text: cache_control
  cannot be set for empty text blocks"}` (matched by `\b5\d\d\b` on a message index, which
  long sessions like the headline one pass 500), and `API Error: 400 {…"messages.40.content.1.
  tool_use.input.timeout: Input should be a valid integer"}` (the Bash tool's `timeout` field,
  matched by `\btimeout\b`). A body that literally says `invalid_request_error` gets promoted by
  a stray token. The test side is weak too: `tests/test_terminal_error_classification.py:285`
  is the only negative case, and a mutant that replaces the whole regex with "any text not
  containing 'Unexpected'" passes every test. Fix: tie the status arm to the leading
  `API Error: NNN`, drop or narrow bare `timeout`, and add negative cases with an incidental
  number and field name.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/assemble.py:95` still says both INFRA shapes
  mean "nothing reviewed the diff". The patch rewrote the same phrase in
  `leaves.py:3023` to "no review came back", because it is false for a reviewer that worked
  for minutes and then lost the API. This is the `assemble.py:76-79` "why" block the brief
  cites, and it now disagrees with the code next to it. It's a comment, not operator-facing,
  so low impact, but criterion (iv) asks for every restatement to agree.

## Scope calls for a human

- NEEDS-HUMAN — The patch edits two things the brief put out of bounds. First,
  `template/tests/test_terminal_error_retention.py:368-401`: child-1's `NothingIsClassified`
  guards are renamed and flipped (a transient report after work is now asserted retried 3×,
  and `produced` is now asserted `False`). Second, the print string inside `_do_build_command`
  at `template/src/pdca_harness/leaves.py:2201-2205`, which is #537's function. Both edits
  follow from the brief's own criteria: child-1's guard pinned exactly the behaviour this
  child changes, and the old builder string ("without emitting any work") would be false for
  the headline case. Only strings and assertions changed, and the `for attempt` loop is
  untouched. Still, the brief said "do not touch" both, so a human should accept the
  deviation and check it against #537's and #538's branches at fold time.
- NEEDS-HUMAN — `template/src/pdca_harness/progress.py:765`: `rate_limit` is in the transient
  set because the brief asks for it, but the vendor's own main-session rule (`Akr`: only
  `overloaded`/`server_error`, or the `apiErrorIsTransient` flag) leaves it out. The vendor
  sets that flag on a plain 429 only in some conditions (`apiErrorIsTransient:M`). A
  mid-session quota stop ("resets 5pm") now buys a full fresh re-invoke of a long leaf. The
  retries fail fast at startup, so the cost is small, but the fixtures README
  (`tests/fixtures/README.md`, "Hence `_CLAUDE_TRANSIENT_KINDS`") presents the set as the
  vendor's rule when `rate_limit` actually comes from the vendor's *sub-agent* retry set. This
  is a policy choice, not a bug.

## Tried and could not break

The signal predicate (both spellings; 128 and 255 are correctly outside it; `TIMEOUT_RC`
answers False). A sub-agent report arriving before or after the main one. A wrap-up status
overruling a permanent report. Exit 0 and the harness timeout keeping `produced`. The codex
and stream-less fallbacks. `capture` staying raw. The only other readers of
`run_with_heartbeat` (`gates.py:588`, `publish.py:833`, `leaves.py:993`) ignore `produced`, so
the new meaning cannot leak there.

### Advisory — code-review

# Advisory code review — issue #539 (what a transient leaf death is)

Lenses: bugs the patch introduces, and reuse / simplification / efficiency. Line numbers are
on the patched target at `$PDCA_TARGET`. I found no correctness bug that breaks a stated
criterion. The classifier follows the shape of `_is_session_event`, runs once per decoded line
(no extra JSON parse in the hot loop), and degrades to `False` for codex and stream-less
families. C4 went red for real on the pre-fix leg: assertion failures, not import errors or
missing fixtures. The `PinnedVendorRecords` cases ran rather than skipped, since both
`*.stream.jsonl` fixtures already exist on the base. The findings below are the edges worth a look.

- NEEDS-HUMAN — `template/tests/test_terminal_error_retention.py:368-401`: the brief says not
  to touch child-1's `test_terminal_error_retention.py`. The patch edits it anyway: it renames
  `NothingIsClassified` to `RetryCountsArePinned` and flips three assertions from "1 run /
  produced True" to "3 runs / produced False". The flip can't be avoided, because those
  guards pinned exactly the old behaviour that criterion (i) changes. They would go red under
  any correct fix, and C4's red leg shows the three failures. A human should confirm this
  counts as the necessary edit and not a scope breach. The other options were to delete the
  guards or move them into the new file.
- NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:2202-2204`: the patch rewrites the
  "transient" message inside `_do_build_command`, and the brief puts that function out of
  scope (it belongs to #537). The edit is only a string, and without it this restatement
  would still say "without emitting any work", which is false. So it is arguably required by
  criterion (iv). But it is a hunk in #537's function, which means a merge conflict with that
  sibling is likely. A human should decide whether to keep it or hand it to #537.
- `template/src/pdca_harness/progress.py:776-800` (`_TRANSIENT_CAUSE_RE`): the fallback for
  the `unknown` kind is broad. Bare `\btimeout\b`, `\bterminated\b`, `409`, and any
  standalone `5\d\d` all count as transient. The vendor builds `unknown` text as
  `API Error: ${e.message}` for *any* thrown `Error`, so an unrelated message that happens to
  contain a number like 512 or the word "timeout" will be retried. The damage is bounded:
  only `unknown` reports with no typed `api_error` reach this regex, and the cost is at most
  `attempts-1` extra runs. Tightening it would help, for example by anchoring the status
  alternative to `status|HTTP|code` context or dropping `\b5\d\d\b` and relying on the
  worded 5xx phrases. Advisory, not a blocker.
- `template/src/pdca_harness/progress.py:59` (`is_signal_death`): for a *direct* child, any
  real exit code from 129 to 192 is now read as a signal death and never retried. The test
  `test_a_bare_exit_137_is_read_as_the_same_death` (`tests/test_terminal_error_classification.py:361`)
  pins this on purpose. This only ever holds back a retry and never adds one, so it's the
  safe direction. Still, a CLI that uses a code in that range for a transient startup failure
  would lose #138's retry. I know of none today. Recording it so the trade-off is visible,
  not as a defect.
- `template/src/pdca_harness/progress.py:261-267`: after main-session work clears the verdict,
  the kept record still has the `_REPORT` shape. A later `result` wrap-up that carries a
  transient `api_error_status` therefore can't be kept (lower precedence) and can't set the
  verdict again. In practice a fresh API-error death emits its own `_REPORT`, which is kept
  and re-sets the verdict, so I don't see this misfire on real CLI output. It's a quiet
  coupling between `_note_terminal` precedence and the verdict, and one comment line would
  save a future reader from rediscovering it.

Reuse and simplification: nothing to flag. `_reports_transient_cause` reuses
`_stream_event`, `_is_subagent_event` and `_claude_message_texts` instead of duplicating them.
`_note_terminal` returning `bool` is the smallest change that keeps the verdict tied to the
kept record.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Decide whether to approve excluded retention-test and builder-message edits, and discharge the incomplete prior-art audit — the brief forbids those edits and this snapshot cannot establish merged plus closed/rejected history for every affected path (`brief.md:123`, `brief.md:139`, `brief.md:198`; `template/tests/test_terminal_error_retention.py:368`; `template/src/pdca_harness/leaves.py:2201`).
- [ ] Validation — fitness-to-purpose — Decide whether stub-driven evidence and derived vendor records suffice for real CLI failures — no live vendor API-error session was exercised, and the current-version stream contract rests on binary reading rather than an observed run (`template/tests/fixtures/README.md:106`, `template/tests/fixtures/README.md:158`).
- [ ] `template/src/pdca_harness/progress.py:836`: every `rate_limit` report is treated as transient without looking at the typed `api_error` the vendor puts on it. The code reads `api_error` only for `unknown` (`:838`). But claude-code 2.1.284 stamps two entitlement stops as `error:"rate_limit"` with a typed cause: `apiError:"long_context_credits_required"` ("Usage credits required for 1M context") and `apiError:"model_requires_usage_credits"`. The wire converter `_o` puts `api_error` on the stream event, so the harness can see it. Probe through `_invoke_leaf_resilient`, with work followed by `{"error":"rate_limit","api_error":"long_context_credits_required",…}` and exit 1: the leaf runs **3 times** and is classed `transient`. The long-context case is the expensive one. Each fresh attempt runs until its context passes the limit again, so a long builder spends the whole budget re-doing the same work. That goes against criterion (ii): a billing/entitlement cause the vendor typed as permanent must not be retried. Fix: treat a `rate_limit` that carries any typed `api_error` as not transient (the plain 429 and the quota limit carry none), and add a test for it.
- [ ] `template/src/pdca_harness/progress.py:799` and `:789`: the prose check for `unknown` reports matches a 5xx-looking number or the word `timeout` anywhere in the text. In this CLI a 5xx `APIError` is already stamped `server_error` and a 429 `rate_limit`. What falls through to `unknown` (`if(e instanceof Pt)return Qo({…error:"unknown"})`) is mostly a generic 4xx, with the JSON body in the text. Concrete cases the probe retries 3×: `API Error: 400 {…"invalid_request_error","message":"messages.536.content.0.text: cache_control cannot be set for empty text blocks"}` (matched by `\b5\d\d\b` on a message index, which long sessions like the headline one pass 500), and `API Error: 400 {…"messages.40.content.1. tool_use.input.timeout: Input should be a valid integer"}` (the Bash tool's `timeout` field, matched by `\btimeout\b`). A body that literally says `invalid_request_error` gets promoted by a stray token. The test side is weak too: `tests/test_terminal_error_classification.py:285` is the only negative case, and a mutant that replaces the whole regex with "any text not containing 'Unexpected'" passes every test. Fix: tie the status arm to the leading `API Error: NNN`, drop or narrow bare `timeout`, and add negative cases with an incidental number and field name.
- [ ] `template/src/pdca_harness/assemble.py:95` still says both INFRA shapes mean "nothing reviewed the diff". The patch rewrote the same phrase in `leaves.py:3023` to "no review came back", because it is false for a reviewer that worked for minutes and then lost the API. This is the `assemble.py:76-79` "why" block the brief cites, and it now disagrees with the code next to it. It's a comment, not operator-facing, so low impact, but criterion (iv) asks for every restatement to agree.
- [x] The patch edits two things the brief put out of bounds. First, `template/tests/test_terminal_error_retention.py:368-401`: child-1's `NothingIsClassified` guards are renamed and flipped (a transient report after work is now asserted retried 3×, and `produced` is now asserted `False`). Second, the print string inside `_do_build_command` at `template/src/pdca_harness/leaves.py:2201-2205`, which is #537's function. Both edits follow from the brief's own criteria: child-1's guard pinned exactly the behaviour this child changes, and the old builder string ("without emitting any work") would be false for the headline case. Only strings and assertions changed, and the `for attempt` loop is untouched. Still, the brief said "do not touch" both, so a human should accept the deviation and check it against #537's and #538's branches at fold time.
- [x] `template/src/pdca_harness/progress.py:765`: `rate_limit` is in the transient set because the brief asks for it, but the vendor's own main-session rule (`Akr`: only `overloaded`/`server_error`, or the `apiErrorIsTransient` flag) leaves it out. The vendor sets that flag on a plain 429 only in some conditions (`apiErrorIsTransient:M`). A mid-session quota stop ("resets 5pm") now buys a full fresh re-invoke of a long leaf. The retries fail fast at startup, so the cost is small, but the fixtures README (`tests/fixtures/README.md`, "Hence `_CLAUDE_TRANSIENT_KINDS`") presents the set as the vendor's rule when `rate_limit` actually comes from the vendor's *sub-agent* retry set. This is a policy choice, not a bug.
- [x] `template/tests/test_terminal_error_retention.py:368-401`: the brief says not to touch child-1's `test_terminal_error_retention.py`. The patch edits it anyway: it renames `NothingIsClassified` to `RetryCountsArePinned` and flips three assertions from "1 run / produced True" to "3 runs / produced False". The flip can't be avoided, because those guards pinned exactly the old behaviour that criterion (i) changes. They would go red under any correct fix, and C4's red leg shows the three failures. A human should confirm this counts as the necessary edit and not a scope breach. The other options were to delete the guards or move them into the new file.
- [x] `template/src/pdca_harness/leaves.py:2202-2204`: the patch rewrites the "transient" message inside `_do_build_command`, and the brief puts that function out of scope (it belongs to #537). The edit is only a string, and without it this restatement would still say "without emitting any work", which is false. So it is arguably required by criterion (iv). But it is a hunk in #537's function, which means a merge conflict with that sibling is likely. A human should decide whether to keep it or hand it to #537.

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
- Iteration delta (if iterating): Rejected on implementation issues; the approach and slice are sound. Fix in the rebuild: 1. progress.py (_reports_transient_cause, kind in _CLAUDE_TRANSIENT_KINDS branch): a `rate_limit` report carrying a typed api_error (e.g. long_context_credits_required, model_requires_usage_credits) is a permanent entitlement stop and must NOT be transient — criterion (ii). Check the typed cause before the kind-set shortcut; add a test. 2. progress.py (`kind != _CLAUDE_UNKNOWN_KIND or ev.get("api_error")`): also honour the transcript spelling `apiError` (the classifier already accepts `isApiErrorMessage`). A typed `apiError="gateway_session_expired"` currently falls through to prose and is retried 3x. Add a test in that spelling. 3. _TRANSIENT_CAUSE_RE is too broad for `unknown` reports: bare `\b5\d\d\b` matches message indices (`messages.536…`) and bare `\btimeout\b` matches field names in 400 invalid_request_error bodies. Anchor the status arm to the leading `API Error: NNN`, drop/narrow bare `timeout`, and add negative cases with an incidental number and a `timeout` field name (a mutant replacing the whole regex currently passes every test). 4. assemble.py:95 comment still says both INFRA shapes mean "nothing reviewed the diff" — reword to agree with leaves.py ("no review came back"), per criterion (iv). 5. Keep `rate_limit` in _CLAUDE_TRANSIENT_KINDS — that is a deliberate project choice (human, at sign-off). But fix the fixtures README ("Hence `_CLAUDE_TRANSIENT_KINDS`") and the progress.py comment so they state it as the project's policy, borrowed from the vendor's sub-agent retry set — not as the vendor's main-session rule (which covers only overloaded/server_error). 6. Scope, decided by the human at sign-off: KEEP both out-of-bounds edits — the flipped/renamed guards in child-1's test_terminal_error_retention.py (unavoidable under criterion (i)) and the transient message rewrite in _do_build_command. That print was introduced by #537's PR 587 (open), which this bundle stacks on; the edit is a string correction on top of 587, not a collision — merge 587 first, then 539. ALSO ALLOWED (exception to the brief's do-not-touch list): update the module docstring of template/tests/test_builder_retry.py (added by PR 587), which defines a transient death as "the child exits non-zero before emitting any work" — restate it in the two-shape form per criterion (iv). Docstring only; no test changes in that file.
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
