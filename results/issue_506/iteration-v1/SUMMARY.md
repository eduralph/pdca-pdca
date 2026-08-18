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

Review of issue #506: retain and classify terminal transient leaf errors, retry transient builder deaths, and give operators an attributable exhausted-retry message.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is observable and separates terminal infrastructure death from substantive work while preserving stream-less behavior, matching the target contract at `template/src/pdca_harness/leaves.py:90`. |
| C2 Reproduction (red pre-fix) | PASS | With only production hunks stashed, the retained tests failed 4/24 on retry count, transient classification, retained API text, and exhausted guidance; env-borne markers prevent argv-echo false positives at `template/tests/test_leaf_resilience.py:48`. |
| C3 Change | FAIL | Interrupted connections and 5xx failures outside the six enumerated codes remain outside the promised category: `_TRANSIENT_CAUSE_RE` accepts “interrupted” only before `mid-response` and only `429/500/502/503/504/529`, so `API Error: Connection interrupted.` returns no classification at `template/src/pdca_harness/progress.py:423`. |
| C4 Verification (red→green) | PASS | The same focused command changed from 4/24 failures without the two production files to 24/24 green with them, exercising classification/log retention at `template/tests/test_leaf_resilience.py:156` and builder retry/guidance at `template/tests/test_leaf_resilience.py:259`. |
| C5 Causal adequacy | PASS | The fix changes the causal signal from “produced anything” to the stream's terminal report and feeds that result through the existing retry path, without adding an optional-capability probe or guarding a capability-present-only path (`template/src/pdca_harness/progress.py:172`, `template/src/pdca_harness/leaves.py:717`). |
| T1 Structure | PASS | Classification stays beside the existing stream-format classifier and Do reuses the existing resilient wrapper rather than adding a second retry implementation (`template/src/pdca_harness/progress.py:398`, `template/src/pdca_harness/leaves.py:1875`). |
| T2 Shape | PASS | `git diff --check`, the repository's docs lint, and its render/link audit all passed independently using the CI commands declared at `.github/workflows/docs-check.yml:32`. |
| T3 Runtime | FAIL | The full offline suite exits 0, but a direct patched-target probe returns `''` for `API Error: Connection interrupted.` and `API Error: Connection timed out.`, leaving those promised terminal failures non-transient at `template/src/pdca_harness/progress.py:423`. |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; the frozen row is deferred and states that the substantive contribution audit reruns at publish. |
| T5 Judgment | FAIL | Affected-file GitHub queries found no open or closed-unmerged prior art (merged #140/#286 are complementary), but iteration is still owed because the narrow matcher leaves part of the stated transient category burning whole attempts (`template/src/pdca_harness/progress.py:423`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the repaired matcher and fresh bounded re-invoke are fit for representative live Claude terminal-event wording and long-session operator recovery — the offline stub proves harness mechanics, not the real vendor vocabulary or operational outcome (`template/tests/test_leaf_resilience.py:58`). |

### Advisory — adversary

# Adversarial review — issue 506 (advisory; never gates)

Grounded on `$PDCA_TARGET` (`fb28c6f` + the patch). I reproduced the red→green myself
(reverted `leaves.py`/`progress.py`, kept the test hunks: **4 failures** on the base —
`test_a_terminal_transient_error_after_real_work_is_retried`,
`test_the_error_log_carries_the_leafs_own_terminal_error`,
`test_a_transient_builder_death_is_retried_bounded_with_backoff`,
`test_the_exhausted_message_names_the_class_and_the_resume` — for the same reasons
`gate-logs/C4-verify.log` records; green with the patch), ran the whole suite (1765 tests,
28.6 s, OK — identical runtime to the base, so the new builder retries add no wall clock),
and mutation-tested the four load-bearing production hunks. What survived that:

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:420` (`_ERROR_LEAD_RE`, with
  its `^\W*` prefix) misclassifies a *substantive* builder failure as transient whenever the
  leaf's final message merely opens with an error-shaped clause that names an infra cause.**
  Driven through the real path (`_invoke_leaf_resilient` → `_invoke` → `progress` →
  subprocess) with the suite's own stub leaf, each of these substantive deaths came back
  `transient=True` and **re-ran the builder 3×**:
  `"Error: assertion failed - expected 500, got 404 in test_api.py"`,
  `"Error: the repro still fails - curl returns 503 from the stub server; needs a human."`,
  `"Connection refused while starting the fixture server; I could not finish the repro."`.
  `^\W*` also eats markdown, so a builder that *quotes* the incident line at the head of a
  message or bullet — `"- \`API Error: Connection lost mid-response.\` is the incident's
  verbatim line"`, `"> API Error: Connection lost mid-response.\n\nThat is what the stream
  carries."` — is read as the leaf dying of it. The blast radius is exactly the one the
  brief calls most expensive: three opus/max builder runs plus an operator told "nothing
  substantive failed. Safe to re-run." The precision guard the patch ships
  (`template/tests/test_leaf_resilience.py:75`, `:185`) only covers the **mid-sentence**
  mention (`"I reproduced the … defect and fixed it"`), so it passes without testing the
  case its own docstring claims — "a builder fixing this very defect says the string out
  loud" — which is precisely the *leading*-quote case. Tighten the lead (e.g. require the
  cause adjacent to the lead, or anchor on the CLI's literal `API Error:` prefix) and add a
  leading-quote case to that guard.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:1812-1817`: the new
  exhausted-retry message's "how to resume" is false in the incident's own scenario.** It
  says "re-driving Do on `issue_506` (`run` / `flow`) resumes the cycle". Measured: a stub
  builder that writes `patch.diff` and *then* emits the terminal API error leaves the bundle
  at `state.state(d) == BUILT` (`state.py:211` — "Do is done when there's a patch"), and
  `driver.py:76` runs **Check**, not Do, on the dead attempt's partial patch. The repo
  already states this ("a partial build lands there and never re-enters PLANNED",
  `driver.py:49-50`; `tests/test_build_error_log.py:96-101`). Criterion (iv) asks the
  operator message to name the resume, and this one points at a command that will not re-run
  Do. Minimum fix is message-local (name that a partial `patch.diff` must be cleared first);
  do **not** silently delete the builder's artifacts to make the sentence true — see the next
  item.

- **NEEDS-HUMAN — retrying the builder in place re-invokes it on the dead attempt's residue,
  and nothing in the patch or the prompt tells attempt 2 that.** `worktree.ensure` runs once,
  before the wrapper (`leaves.py:1833`), so attempts 2 and 3 start in a worktree already
  carrying attempt 1's edits and a bundle already holding its `patch.diff` / `build-notes.md`
  (`leaves.py:1875-1883`); `_build_prompt` (`leaves.py:1888`) says only "Produce, in the
  bundle directory …". For the reviewer/advisory leaves a retry is idempotent — they rewrite
  one file — but the builder mutates a tree, and the incident's leaf is exactly the one that
  had run 18 minutes before dying. The failure mode to weigh: attempt 2 reads a
  complete-looking `patch.diff` + `build-notes.md`, concludes the work is done, exits 0, and a
  half-finished patch is reported as a **successful** Do. The brief pre-accepted "a fresh
  re-invoke" only for *session* resume; whether a fresh re-invoke on a dirty lane is
  acceptable — or needs a reset / a carry-forward note in the prompt — is a scope call.

- **NEEDS-HUMAN — the classifier's contract with the *real* vendor stream is asserted, never
  observed (verdict provisional; no CLI, no network in this sandbox).** Every new test
  synthesises the event shape it then parses (`tests/test_leaf_resilience.py:63-73`), so it
  cannot distinguish "reads claude's terminal error" from "reads the stub's". If the CLI in
  fact emits that death as a `system` event, as a `result` with only `subtype:
  "error_during_execution"` and no string `result`/`error` key, or on **stderr**,
  `_terminal_error_text` (`progress.py:442`) and `_claude_event_texts` (`progress.py:466`)
  return `""`, the leaf stays substantive, and the whole suite is still green while the
  incident is unfixed. One real transcript from `~/.claude/projects/` (the brief cites it)
  pinned as a fixture would close this; a human should confirm the wire shape before this is
  taken as the incident's fix.

- `template/src/pdca_harness/progress.py:279-285` bends the documented `capture` contract:
  the docstring at `:113-114` says the stream parse is "mutually exclusive with `capture`
  (capture wins if both set)", but the terminal-error line is now appended to `output` on the
  `capture=True` branch too. No caller sets both today (`gates.py:559`, `publish.py:833`,
  `leaves.py:774` are all `capture=True, stream_json=False`), so this is latent — but the
  first caller that captures raw stream JSONL gets a trailing non-JSON line in its evidence.

- `template/src/pdca_harness/leaves.py:108-110` and `:2583` still describe the old rule
  ("A no-output non-zero exit", "ran, exited non-zero with no output; retries exhausted")
  after the patch widened it and rewrote the neighbouring prose at `:94-100` and `:2647`. In
  a codebase where the comment is the contract, that is a conformance nit worth one line each.

## Attempted and could not refute

- **Tautology / wrong-reason pass:** no. Four targeted mutations were each caught — dropping
  the exhausted-retry print (`leaves.py:1806`) → `test_the_exhausted_message…` fails;
  dropping the `_has_content` guard (`leaves.py:1800`) → the 3-record assertion fails;
  dropping `and not terminal["error"]` (`progress.py:287`) → 3 failures; dropping the
  recovery-clearing branch (`progress.py:178-179`) → the recovered-session test fails.
- **Vacuous markers:** no. `_API_ERROR` / `_LEAF_STDERR` reach the child through the env
  (`tests/test_leaf_resilience.py:50`), so `_format_leaf_attempt`'s argv echo cannot satisfy
  the assertions — the base-leg failure output confirms the echo carries the *script*, not
  the marker.
- **Parallel re-implementation:** no. `DoRetriesATransientBuilderDeath`
  (`tests/test_leaf_resilience.py:209`) drives the real `do_build` → `_do_build_command` →
  `_invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat` → `subprocess` chain.
  Note the C5 row's "pass" is *vacuous* here — its evidence line is "patch adds no new test
  file — nothing to assert" (`gate-logs/C5-prod-path.log`), so it supports nothing; the
  production-path claim rests on the manual check above, not on that green.
- **Collateral regressions:** none found. Full suite green, same runtime as base; the
  `_has_content` guard cannot resurrect a stale log (`do_build` still unlinks at
  `leaves.py:1774` before setup); a setup failure before the leaf still lands its own record
  (`tests/test_build_error_log.py:133`); stream-less families keep `produced=True`
  (`leaves.py:674`); codex/gemini degrade to today's classification (`progress.py:449`).

### Advisory — code-review

# Advisory code review — issue #506

Correctness lens: traced the new stream classifier (`progress.py`) and the retry
wiring (`leaves.py`) against the tests and the target source. The core mechanism —
`_terminal_error_text` / `_work_continued` setting `terminal["error"]`, folding it
into `produced`, and `_do_build_command` moving to `_invoke_leaf_resilient` with
`do_build`'s `_has_content` guard against clobbering the per-attempt log — is
internally consistent and the traced scenarios (fatal-then-exit, fatal-then-recover,
prose-mentioning-an-error, setup-vs-invocation failure) all resolve the way the
docstrings claim. No functional bug found that breaks the fix itself. Findings below
are all minor: a heuristic edge case worth a human's attention, and two cosmetic nits.

- NEEDS-HUMAN [impl] — `progress.py:420-422` (`_ERROR_LEAD_RE`) combined with
  `_TRANSIENT_CAUSE_RE` (`progress.py:423-...`) can misclassify a genuinely
  substantive assistant text block as a terminal transient death: the lead pattern
  matches the bare word `error` (not just `api error`), so any content block that
  *starts* with `"Error ..."` or `"Error: ..."` (a builder narrating a traceback it's
  fixing, or opening a paragraph with "Error handling: ...") and separately mentions
  any of the very common words in `_TRANSIENT_CAUSE_RE` elsewhere in the same block
  (`timeout`, `unavailable`, `network error`, or a bare `500`/`502`/`503`/`504` that
  could just as easily be an HTTP status code the builder is implementing) would be
  read as the CLI's own terminal report and forced `transient` — triggering a retry
  of what is actually a substantive failure. The docstring at `progress.py:411-419`
  frames the two-pattern design as "reads as an error report… not prose that mentions
  one," but the only test guarding that boundary
  (`test_prose_that_mentions_an_api_error_is_still_substantive`,
  `test_leaf_resilience.py:519-529`) deliberately opens with `"I reproduced the ..."`,
  i.e. it never exercises a block that *itself* opens with the bare lead word. Worth
  either tightening the lead regex (e.g. requiring the `api`/`fatal`/`connection`
  qualifiers rather than bare `error`) or adding a red case for a substantive block
  that opens with "Error" before this ships, since the failure mode this would
  produce — a builder failure silently retried and re-billed as transient — is exactly
  the class of misclassification the brief is trying to eliminate, just in the
  opposite direction.

- `leaves.py:108-109` (`LeafError.transient` property docstring), `leaves.py:2583`
  (the `_FAIL_TRANSIENT` inline comment) and `leaves.py:2588` (`_failure_class`
  docstring) still describe "transient" as "no output" / "ran, exited non-zero with
  no output" only. The class-level docstring just above (`leaves.py:97-105`) and the
  `_invoke_leaf_resilient` docstring (`leaves.py:686-689`) were updated for the new
  "worked, then reported its own terminal death" trigger, but these three secondary
  descriptions were not — cosmetic drift, not a behavior bug, but worth a follow-up
  touch so a future reader of `_failure_class` doesn't reason from the stale half of
  the definition.

- `leaves.py:1882` — `_do_build_command` passes `memory_log=d / BUILD_MEMORY_LOG`
  explicitly into `_invoke_leaf_resilient`, but `_invoke_leaf_resilient` already
  derives the identical path itself via `_memory_log_for(error_log)`
  (`leaves.py:704`, confirmed: `_memory_log_for(d / "build.error.log")` ==
  `d / "build.memory.jsonl"` == `BUILD_MEMORY_LOG`). The three other call sites
  (`leaves.py:2561`, `2894`, `3196`) all rely on the derivation and pass no
  `memory_log` kwarg. Harmless today (the explicit value and the derived one are
  byte-identical), but it's a needless carry-over from the pre-#506 `_invoke` call
  this replaced, and leaves the builder site as the one inconsistent caller of the
  four — dropping the kwarg would match the pattern this slice says it reuses "as it
  is" (`leaves.py:1866`).

No reuse/duplication or resource-leak/concurrency issues found beyond the above; the
new `_has_content` helper (`leaves.py:747-750`) has no existing equivalent to reuse,
and the shared-dict / single-drain-thread mutation pattern for `terminal["error"]`
follows the same (already-safe) shape as the pre-existing `produced` dict.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether the repaired matcher and fresh bounded re-invoke are fit for representative live Claude terminal-event wording and long-session operator recovery — the offline stub proves harness mechanics, not the real vendor vocabulary or operational outcome (`template/tests/test_leaf_resilience.py:58`).
- [ ] `progress.py:420-422` (`_ERROR_LEAD_RE`) combined with
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
- Iteration delta (if iterating): Rejected on the findings (reviewer C3/T3/T5 + the adversary lens). The core mechanism is sound and independently confirmed -- red->green reproduced, full suite green at base runtime, and all four mutations of the load-bearing hunks were caught, so the tests are not tautological. Keep that. Four defects sit on top of it: 1. The matcher is wrong in BOTH directions (progress.py:420-423). - Too narrow: `API Error: Connection interrupted.` and `API Error: Connection timed out.` yield no classification when probed against the patched target -- `_TRANSIENT_CAUSE_RE` accepts "interrupted" only before "mid-response", and only 429/500/502/503/504/529. Criterion (i) promises lost/interrupted connections. - Too broad: `_ERROR_LEAD_RE`'s `^\W*` lead plus a bare `error` word classifies substantive builder deaths as transient and re-runs the builder 3x -- measured through the real path with e.g. "Error: assertion failed - expected 500, got 404 in test_api.py". The `^\W*` also eats markdown, so a builder that QUOTES the incident line at the head of a bullet or blockquote is read as dying of it. Tighten the lead (require the api/fatal/connection qualifier, or anchor on the CLI's literal `API Error:` prefix) and widen the cause to the promised category. Add a red case for a substantive block that OPENS with the lead word, and one for a leading verbatim quote: the existing guard (test_leaf_resilience.py:75, :185, :519-529) only covers a mid-sentence mention, so it never tests the case its own docstring claims. 2. The exhausted-retry "how to resume" is false in this incident's own scenario (leaves.py:1812-1817). A builder that writes patch.diff and then dies leaves the bundle at BUILT (state.py:211), and driver.py:76 then runs Check, not Do, on the partial patch. Fix the message (name that a partial patch.diff must be cleared first). Do NOT silently delete the builder's artifacts to make the sentence true. 3. Retry re-invokes the builder on the dead attempt's residue: worktree.ensure runs once, before the wrapper (leaves.py:1833), so attempts 2-3 start in a worktree carrying attempt 1's edits and a bundle already holding patch.diff/build-notes.md. Risk: attempt 2 reads a complete-looking patch, exits 0, and a half-finished build is reported as successful. HANDLE THIS AT DO LEVEL, bounded -- make the retry prompt state that a previous attempt died mid-flight and that any patch.diff / build-notes.md present are its incomplete residue to be verified or replaced, not evidence the work is done. A lane reset or a new config knob is out of scope for this iteration; if the rebuild concludes a prompt-level note is insufficient, say so in build-notes.md rather than expanding the slice. 4. The classifier's contract with the real vendor stream is asserted, never observed -- every test synthesises the event shape it then parses (test_leaf_resilience.py:63-73). If the CLI emits that death as a `system` event, a `result` with no string result/error key, or on stderr, `_terminal_error_text` (progress.py:442) and `_claude_event_texts` (progress.py:466) return "" and the incident stays unfixed with the suite green. Pin one real transcript from ~/.claude/projects/ (the brief cites it) as a fixture. Also worth closing while in there: - progress.py:279-285 bends the documented `capture` contract (docstring :113-114 says the stream parse is mutually exclusive with capture) -- latent today, since no caller sets both, but the first raw-JSONL capturer gets a trailing non-JSON line. - leaves.py:108-110, :2583, :2588 still describe transient as "no output" only, after the patch widened the rule -- stale half of the definition. - leaves.py:1882 passes `memory_log=` explicitly where the other three call sites rely on `_memory_log_for` deriving the identical path; drop the kwarg to match. - Note the C5 green is vacuous here ("patch adds no new test file -- nothing to assert"), so it supports no production-path claim.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
- plan-reviewer produced no artifact in all 5 bundles of this sign-off batch (466/474/497/475/506) — systemic, not per-bundle: those briefs reached Do with no advisory pass, and each cost a human §6 adjudication. Act: find the leaf's failure mode, and decide whether a no-artifact plan advisory should hold Plan rather than pass through.
