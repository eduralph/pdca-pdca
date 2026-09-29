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

Review whether leaf retries follow terminal API causes and signal deaths, excluding spent subscription windows while preserving retained reports and truthful operator messages.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The retry/non-retry outcomes are falsifiable offline; carry-forward decisions explicitly authorize the additional edits and distinguish passing 429s from spent windows (`brief.md:219`, `brief.md:227`; `target/template/tests/test_terminal_error_classification.py:612`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the three production changes while retaining the tests produced 54 assertion failures across 66 tests, including retry counts and operator labels; no import-error substitute for reproduction (`reviewer-red.log:646`; `target/template/tests/test_terminal_error_classification.py:341`). |
| C3 Change | PASS | The inspected patch stays within the amended classification scope; the retry loop and retention behavior remain intact, including the explicitly authorized test/message updates (`target/template/src/pdca_harness/progress.py:277`; `brief.md:219`). |
| C4 Verification (red→green) | PASS | Restoring the stash makes all 66 classification tests pass; the frozen C4 log additionally shows all four touched test modules green and behavioral failures on its red leg (`reviewer-green.log:3`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | The decision now follows terminal cause, recovery, usage state and signal exit rather than output alone; tests invoke production subprocess/retry paths, and no capability-probe or load-time symptom guard was introduced (`target/template/src/pdca_harness/progress.py:277`, `target/template/src/pdca_harness/leaves.py:121`, `target/template/tests/test_terminal_error_classification.py:260`). |
| T1 Structure | PASS | Classification remains in the existing stream reader and leaf error boundary; it adds no configuration, scheduling responsibility or retry-loop restructuring (`target/template/src/pdca_harness/progress.py:949`, `target/template/src/pdca_harness/leaves.py:121`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit and whitespace check pass; both frozen docs gates agree (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite passes 2,047 tests with two skips; the frozen root suite passes 24 tests, supplying render/update evidence unavailable locally because Copier is absent (`reviewer-suite.log:1656`; `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive audit remains due at publish, as the deferred gate records (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-file prior art across merged history and closed/rejected work — this disposable copy has one synthetic commit and no remotes; the brief records selected history and rejected rounds, but complete closed-work coverage cannot be independently established (`brief.md:198`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether derived protocol evidence adequately supports the real subscription-stop distinction — no live rejected-window or typed-cause session was exercised; those outcomes rest on constructed events and vendor code reading, so green offline tests do not discharge that external behavior (`target/template/tests/fixtures/README.md:259`; `target/template/tests/test_terminal_error_classification.py:186`). |

No confirmed patch defect was found. These judgments are advisory; they do not gate acceptance.

Independent verification used the disposable target supplied by the harness. I stashed only `progress.py`, `leaves.py` and `assemble.py`, ran the new behavioral tests against the pre-fix production tree, restored the stash, and repeated the tests. The restored target passes `git apply --reverse --check ../patch.diff`. The complete offline suite then passed, including the updated retention, builder and leaf-status tests. All temporary test roots were directed inside this review workspace. The added test's AST imports the actual production package at `target/template/tests/test_terminal_error_classification.py:60`, corroborating `gate-logs/C5-prod-path.log:10`.

The instance-scoped gate wrappers are not target tools. Their frozen logs were read, and their underlying checks were rerun where available. The root render/update suite was adjudicated from its captured 24-test passing run; local Copier absence is a reviewer-host limitation, not a patch failure or a missing gate verdict. The target is usable and contains the prerequisite changes; no stale-target caveat was needed. The available integration template enumerates no additional concrete human-only checks (`target/template/docs/INTEGRATION.md.jinja:80`).

For the external-behavior decision, I also inspected the installed Claude 2.1.284 binary's usage-state extraction and stream emitter. Its error reader rebuilds state from response headers before marking a 429 rejected, and its stream emitter carries the resulting usage state, supporting the documented derivation at `target/template/tests/fixtures/README.md:242`. This is independent code reading, not an observed subscription rejection. To discharge the remaining uncertainty, capture an actual spent-window session with `claude -p --output-format stream-json --verbose "Reply OK"` under an already exhausted subscription, retain its exit status and stream, and replay those bytes through the production-path harness at `target/template/tests/test_terminal_error_classification.py:260`: expect one invocation, a non-transient error, retained report text, and no “safe to re-run” label. Compare a genuine passing 429 capture: expect three attempts. The current passing inline cases prove those outcomes for the constructed inputs only.

### Advisory — adversary

# Adversarial review — issue #539 (iteration 3)

**Verdict: I could not break the core fix.** I found two unpinned guards in the tests and one vendor claim in the README that goes too far. None of them blocks the headline behaviour.

## Evidence, re-run independently

- `template/tests/test_terminal_error_classification.py:341` and `:561-579`: I re-ran red→green myself on a scratch copy of `$PDCA_TARGET`. With the patch, 131 tests pass across the five touched or neighbouring suites. With `template/src` reverted (tests kept), the headline cases fail on **assertions**, not imports. Those cases are: work then a lost-connection report (1 run, needs 3), a silent SIGKILL (`-9`) and SIGTERM (`-15`) (3 runs, needs 1), and the wrapper spelling (`sh -c` giving `137`). The C4 log shows the same failures and no `PDCA-UNVERIFIABLE`. Every case goes through `leaves._invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat` with a real child process, so this is the production path, not a copy of it.
- `template/tests/test_terminal_error_classification.py:612-616`: the sign-off's spent-window case (work, then a spent-window event, then a `rate_limit` report, then exit 1 → 1 run) is **green on the base as well**, because the base never retried a leaf that did work. It is still a real guard: when I deleted `or refused_by_usage_limit` (`progress.py:414`), 16 subtests went red, including this one, `:674` (the silent-leaf veto, which *is* red on the base), the builder case and the §6 row. So the evidence holds, even though this particular red→green pair proves nothing on its own.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:913` and `:835`: two anchors in the text reader for `unknown` reports are not pinned by any test. I swapped `_UNKNOWN_STATUS_RE.match` for `.search`, and separately replaced `\AAPI\s+Error:\s*terminated\W*\Z` with a bare `\bterminated\b`. **Both mutants pass all 131 tests.** Here is the concrete input each one breaks. Production correctly returns `False` for both (I checked by calling `_reports_transient_cause` directly); each mutant would retry them and tell §6 "safe to re-run":
  - `error:"unknown"`, text `"API Error: upstream replied: API Error: 503 from the gateway, not ours"`
  - `error:"unknown"`, text `"API Error: Your session was terminated by the organization admin"`

  Iteration-1 sign-off item 3 asked specifically that mutants of this reader be killed. Add these two negative cases next to `test_an_unclassified_report_without_a_status_names_no_failed_connection` (`tests/test_terminal_error_classification.py:490`).
- NEEDS-HUMAN — `template/tests/fixtures/README.md:244-245` (and the `DERIVED` note on `_PASSING_REJECTION`, `tests/test_terminal_error_classification.py:188-191`): the claim "only the usage-limit 429 names a window there" is broader than the 2.1.284 binary supports. `extractQuotaStatusFromError` uses `fve(...).own`, which is `b0n(base, readings)`. When the 429's own status header is absent or `allowed`/`allowed_warning`, `b0n` calls `wdt`/`S0n`/`k0n`, and those fill in `rateLimitType` from the per-window usage headers. That happens when the 5-hour window is ≥0.9 used with ≤72% of it gone, when the weekly window crosses 0.75/0.5/0.25 early, or when a `…-surpassed-threshold` header is present. `Ddt` then forces `status:"rejected"`. The result is `{status:"rejected", rateLimitType:"five_hour", isUsingOverage:false}`, and `_usage_limit_refusal` (`progress.py:979`) reads that as a spent window. It does this even though the CLI's own test for a usage-limit 429 (`_sn`: the claim header or the overage-status header) calls it "not your usage limit" and retries it itself. The CLI's own mock server does send usage readings without a claim header (`setEarlyWarning`). The failure is on the safe side: a subscriber near their limit loses a retry, and §6 says "needs a human" instead of "safe to re-run". Nobody has observed a real 429 with that header mix. A human should decide whether to correct the README claim only, or also tell the two states apart. The warning-derived state carries `utilization` and `surpassedThreshold`, which a claim-derived state does not. That difference is unverified and may not hold.

## Attempted, could not refute

- **Synthetic tool results after the report clearing the verdict** (`progress.py:284-285`). In 2.1.284, both places that emit synthetic tool results (`yield*Ja(B,…)`) do so *before* the error report. When a `user` tool result does follow a report, that comes from the tool-drain path after a mid-response drop, and there the CLI really does continue into a new turn. So the clearing rule matches what the vendor does.
- **Signal spellings** (`progress.py:40-57`, `leaves.py:121`). `-9`/`-15`/`137`/`143` count as signal deaths. `128`, `255`, `193` and `TIMEOUT_RC` do not, and the `128` boundary is pinned. The memory cap uses `systemd-run --user --scope`, which execs the leaf, so an OOM kill arrives as `-9`.
- **`isUsingOverage` exclusion.** The vendor's `fve` sets it to exactly `status==="rejected" && overage allowed`, which matches the patch.
- **Other consumers of `produced`.** Nothing reads `produced` except `LeafError.transient`. `gates.py:588`, `leaves.py:1001` and `publish.py:833` all discard it, so changing what it means has no side effects elsewhere.
- **Criterion (vi) cases.** Exit 0, a stream-less family, the codex format and raw stdout under `capture` all behave as before, and each has a test that would catch a change.
- **Mutation spot-checks.** Letting sub-agent work clear the verdict, allowing an empty window name, reading any rc≠0 as a death, letting sub-agent reports classify, dropping the transcript spelling of the error flag, and dropping the leading-status read: each mutant is killed.

### Advisory — code-review

# Advisory code review — issue #539 (transient leaf death, decided once)

Lens: bugs the patch introduces, plus reuse/simplification/efficiency. Gates: C4 is a real red→green (the red leg fails 54 new cases and the 3 flipped retention guards, `gate-logs/C4-verify.log`); C5, T2, host-CI and T3 pass.

No correctness bug found that needs to go back to Do. The classification logic, the signal predicate and the drain-loop wiring hold up when I read them and when I probed them directly. The items below are low-severity notes. None is marked NEEDS-HUMAN.

## Correctness — checked, holds

- `template/src/pdca_harness/progress.py:278-285` — the verdict follows `_note_terminal`'s new bool return (`:711-712`), so a sub-agent report or a `result` wrap-up that arrives after a main-session report cannot overwrite its verdict (precedence `{subagent:1, wrapup:2, report:3}`, `:612`). The recovery clear only runs in the `elif` branch, so the report line itself (also an `assistant` event) never clears its own verdict. This is correct.
- `template/src/pdca_harness/progress.py:408-414` — the verdict applies only when `rc not in (0, TIMEOUT_RC)`. Exit 0 and the harness's own timeout keep today's `produced`. The signal check stays with the caller (`leaves.py:121`), so "work, then transient report, then SIGKILL" is correctly not retried (pinned by `test_terminal_error_classification.py:581`).
- `template/src/pdca_harness/progress.py:42-59` `is_signal_death` — probed: `-9`, `137`, `129`, `192` → True; `-1001` (TIMEOUT_RC), `128`, `193`, `255`, `1` → False. Both spellings are covered, and the timeout keeps its meaning.
- `template/src/pdca_harness/leaves.py:692` — the stream-less fallback `produced or not use_stream` is unchanged, so codex/gemini/generic still report substantive.
- Hot loop (`progress.py:266-291`): the added per-line work is one dict lookup in `_usage_limit_refusal` plus two branches that only run on report lines or after a transient verdict. The single JSON decode per line is kept. No efficiency problem.

## Low-severity notes (advisory, no action required)

- `template/src/pdca_harness/progress.py:895-897` (`_typed_causes`) — the test is `ev.get(key) is not None`, so an empty string (`api_error: ""`) counts as a typed cause, and the report is never transient. Probe: `error:"server_error", api_error:""` → `False`. The vendor schema says to "treat an unknown value as absent". The fixtures README says the patch deliberately does not do that for *unknown values*, but an *empty* value is arguably absence, not an unknown cause. This only withholds a retry, never grants one, so it fails safe. If you want it tightened, the fix is one word: `if ev.get(key) not in (None, "")`.
- `template/src/pdca_harness/progress.py:804` (`api_error_code` / `apiErrorCode` in `_CLAUDE_CAUSE_FIELDS`) — any server gate code outranks the kind. Probe: `error:"overloaded", api_error_code:"overloaded_error"` → not transient. That matches the iteration-1 sign-off rule ("typed cause outranks the kind"), and the README records it as derived, not observed. If the API ever attaches `error.details.error_code` to ordinary 529/5xx responses, the headline overloaded/server_error retry would silently stop. Nothing in the patch observes whether it does, so this is worth re-checking against a real 529 transcript when one turns up. It is not a defect in this diff.
- `template/src/pdca_harness/progress.py:905-915` (`_unclassified_text_is_transient`) — for an `unknown` report with no leading status, any `Error.message` containing connection-failure wording is retried. Probe: `"API Error: tool said connection refused by user"` → True. A local misconfiguration such as a bad `ANTHROPIC_BASE_URL` (`ENOTFOUND`) also gets retried, when it is really permanent. The cost is bounded (two extra invocation-time attempts) and the brief allows it ("only the wording of a connection that failed"), so I'm noting it, not flagging it.
- Reuse: the two-shape phrase "before emitting any work, or on its own report of a transient API error" is now hand-copied into at least six runtime strings: `assemble.py:112-113`, `leaves.py:776-777` (retry print), `leaves.py:2210-2211` (builder print), `leaves.py:3044-3049` (§6 placeholder prose), plus several comments and docstrings. The brief's whole defect was that the definition drifted across copies. One module constant (for example in `assemble`, reused by `leaves` for the prints and the placeholder) would stop the next drift at compile time rather than by test. The tests pin each string separately (`test_leaf_status.py:137-140`, `test_terminal_error_classification.py:738-775`), so today's copies agree. This is optional cleanup, not a bug.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm affected-file prior art across merged history and closed/rejected work — this disposable copy has one synthetic commit and no remotes; the brief records selected history and rejected rounds, but complete closed-work coverage cannot be independently established (`brief.md:198`).
- [x] Validation — fitness-to-purpose — Decide whether derived protocol evidence adequately supports the real subscription-stop distinction — no live rejected-window or typed-cause session was exercised; those outcomes rest on constructed events and vendor code reading, so green offline tests do not discharge that external behavior (`target/template/tests/fixtures/README.md:259`; `target/template/tests/test_terminal_error_classification.py:186`).
- [x] `template/src/pdca_harness/progress.py:913` and `:835`: two anchors in the text reader for `unknown` reports are not pinned by any test. I swapped `_UNKNOWN_STATUS_RE.match` for `.search`, and separately replaced `\AAPI\s+Error:\s*terminated\W*\Z` with a bare `\bterminated\b`. **Both mutants pass all 131 tests.** Here is the concrete input each one breaks. Production correctly returns `False` for both (I checked by calling `_reports_transient_cause` directly); each mutant would retry them and tell §6 "safe to re-run":
- [x] `template/tests/fixtures/README.md:244-245` (and the `DERIVED` note on `_PASSING_REJECTION`, `tests/test_terminal_error_classification.py:188-191`): the claim "only the usage-limit 429 names a window there" is broader than the 2.1.284 binary supports. `extractQuotaStatusFromError` uses `fve(...).own`, which is `b0n(base, readings)`. When the 429's own status header is absent or `allowed`/`allowed_warning`, `b0n` calls `wdt`/`S0n`/`k0n`, and those fill in `rateLimitType` from the per-window usage headers. That happens when the 5-hour window is ≥0.9 used with ≤72% of it gone, when the weekly window crosses 0.75/0.5/0.25 early, or when a `…-surpassed-threshold` header is present. `Ddt` then forces `status:"rejected"`. The result is `{status:"rejected", rateLimitType:"five_hour", isUsingOverage:false}`, and `_usage_limit_refusal` (`progress.py:979`) reads that as a spent window. It does this even though the CLI's own test for a usage-limit 429 (`_sn`: the claim header or the overage-status header) calls it "not your usage limit" and retries it itself. The CLI's own mock server does send usage readings without a claim header (`setEarlyWarning`). The failure is on the safe side: a subscriber near their limit loses a retry, and §6 says "needs a human" instead of "safe to re-run". Nobody has observed a real 429 with that header mix. A human should decide whether to correct the README claim only, or also tell the two states apart. The warning-derived state carries `utilization` and `surpassedThreshold`, which a claim-derived state does not. That difference is unverified and may not hold.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
