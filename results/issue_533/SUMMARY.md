# Result — issue 533 / a-leafs-own-terminal-error-is-kept-and-read

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `progress.run_with_heartbeat` already reads every event a leaf's stream emits
  and throws away the one line that explains a death; and what the harness calls a
  "transient" death is decided by a proxy that is wrong for exactly the sessions where an
  attempt is most expensive. Four facts, each re-verified against the target base
  (`eduralph/pdca-harness` @ `main`, `acb214a`) while this brief was written:
  * **The stream's own error text is discarded.** The drain parses stdout for a session flag
    and a tool label and keeps nothing else (`progress.py:150-159`); what it retains is a
    bounded **stderr** tail (`:143`, `:162-168`), and with `capture` off `output` is that
    stderr tail alone (`:255`, `:257`). The CLI's API-error line arrives as a stream *text*
    event on **stdout**, so it is displayed and dropped, and `_format_leaf_attempt`
    (`leaves.py:724-730`) falls back to `(no output captured)` at `:729` — verbatim what the
    reported incident's `build.error.log` contained. The cause was legible only in the CLI's
    own session transcript under `~/.claude/projects/`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:154-155`, `_is_session_event`
    at `:359`/`:365`; `LeafError.transient` is literally `return not self.produced`,
    `leaves.py:104-107`). "Produced anything?" is a *proxy* for "died at invocation", and the
    proxy fails for the long sessions: the incident's 18-minute builder did plenty of work and
    then died of an API connection drop, so it was classified substantive — correctly by that
    rule, wrongly for that cause. The module's own docstring (`progress.py:61`) already records
    that the CLI emits `system`/`api_retry` on a **retryable** API error; the **terminal**
    report is the case with no reader.
  * **The same proxy files a signal kill as transient infra.** `transient` is `not produced`
    with no notion of *how* the child died, so a leaf SIGKILLed **before** its first
    substantive event — the `leaf_memory_max` cap (#420), an OOM killer, a Ctrl-C — is
    classified transient and re-run for the full attempt budget. A capped leaf buys three more
    OOMs. Measured on the base by round 3's adversary through `_invoke_leaf_resilient`:
    `LeafError(returncode=-9).transient is True`, run 3 times; the wrapper spelling
    (`rc=137`, no stream events) likewise. This is the concrete instance of the #510 boundary,
    and it gets **worse** the moment sibling #537 puts the builder on the resilient path.
  * **The definition is restated in six places, and they do not agree.** `LeafError`'s
    docstring (`leaves.py:90-107`), the `_invoke` fallback comment (`:661-670`), the retry
    print (`:717`), `_FAIL_TRANSIENT` (`:2529`), `_failure_class` (`:2534-2549`),
    `_unavailable_classification` (`:2573-2600`), the reviewer call-site comment (`:2505`),
    plus `assemble.py:80` (`LEAF_STATUS_INFRA`, "ran, died with no output — a transient blip")
    and — the one the operator actually reads — `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` at
    `assemble.py:85`: **"leaf did not run (transient infra — safe to re-run)"**, the string
    `assemble.py:168` prefixes onto every §6 row for an infra-empty placeholder. Widening what
    "transient" means makes that string false for the headline case — an 18-minute leaf that
    ran, at length. `template/tests/test_leaf_status.py:135,188` pin the stale string, so the
    suite cannot catch the drift.
- Success criterion: With the patch:
  (i) **Retention, unconditionally.** A leaf whose stream carried the CLI's **own marked
  terminal error report** has that report's text in its `*.error.log`, by the same route the
  stderr tail takes — for **every** marked report, whatever its cause and whether or not the
  session recovered from it — and a report the CLI forwarded for a **sub-agent** is retained
  *labelled as such*, never passed off as the leaf's own death. A post-mortem explains the
  failure without opening `~/.claude/projects/`.
  (ii) **Classification by cause, not by silence.** Such a leaf is classified **transient**
  when the vendor marked its cause transient (a lost or interrupted connection, an overload
  or 5xx, a mid-session rate-limit rejection), however much work came first; and is **not**
  when the vendor marked it permanent (invalid request, authentication, billing) — no prose
  inside a marked report may promote it — nor when a leaf merely mentions or quotes an error,
  nor when the CLI **recovered** and real **main-session** work followed, nor when it failed
  substantively.
  (iii) **A signal kill is not transient infra.** A leaf a signal killed is not retried on the
  strength of having emitted nothing — in **both** returncode spellings (`-signum` from a
  direct child, the shell's `128+signum` from a wrapper argv).
  (iv) **One definition, stated truthfully everywhere.** Every site that restates what a
  transient leaf death is — including the operator-facing `_LEAF_STATUS_LABEL` string — says
  the same true thing, covering both shapes (produced nothing at all, **or** ended on its own
  marked transient report) and asserting neither "did not run" of a leaf that ran nor
  "no output" of a leaf that explained itself.
  (v) **Nothing else changes:** a stream-less family still reports substantive
  (`leaves.py:661-670`), `capture` still returns the child's raw stdout unmodified, the
  codex/gemini stream formats degrade to today's behaviour, a leaf that succeeds is spawned
  and reported exactly as today, and the memory-telemetry post-mortem (#420, `leaves.py:665`)
  still rides `output` into the same log.
  Demonstrable by C4-verify offline: a stub "leaf" that is a Python interpreter emitting
  chosen stream events and exiting non-zero, driven both through `progress.run_with_heartbeat`
  directly and through `leaves._invoke_leaf_resilient` (the reviewer/advisory path, resilient
  on **any** base), so every clause is an assertion over an invocation counter and the error
  log's bytes.
- Repo + branch target: eduralph/pdca-harness @ main (base `acb214a`)
- Scope (one logical fix) / out of scope: What a leaf's death *is*, and what survives it, on the spawn path every leaf
  shares: read the CLI's own marked terminal error report out of the stream the driver already
  parses; keep that text so it reaches the leaf's `*.error.log` by the route the stderr tail
  already takes; decide "transient" from the cause the **vendor** marked (and from how the
  child actually died) rather than from whether it happened to say anything; and make every
  site that restates that definition — the operator-facing label included — say the same true
  thing. **Out of scope:** who is retried and what a retry may inherit — the builder is **not**
  put on the resilient path here, and `_invoke_leaf_resilient`'s **body**, `do_build`,
  `_build_prompt` and the artifact harvests are #536/#537's; resuming a long session via the
  CLI's own session-resume (a fresh re-invoke is the accepted first cut — say so in
  `build-notes.md` so the human can weigh it); the gate-side transient (issue #371); issue
  #510's own remedy beyond the narrow "a signal kill is not transient infra" rule above; any
  new `pdca.toml` knob.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (split), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.

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
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
