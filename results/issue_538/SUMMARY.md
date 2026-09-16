# Result — issue 538 / a-leafs-own-account-of-its-death-is-kept

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch: (i) when a leaf's stream carried the CLI's **own marked
  terminal error report** — the message the vendor itself flags as its API-error report — that
  text is in the leaf's `*.error.log`, reaching it by the same route the stderr tail takes
  (appended to what `run_with_heartbeat` returns as `output`), so a post-mortem explains the
  failure without opening `~/.claude/projects/`; (ii) retention is **unconditional** — every
  marked report is kept whatever its cause, *including* one the session then recovered from,
  because a harness holding the text must never file `(no output captured)`; (iii) a report the
  CLI forwarded for a **sub-agent** (the Task's `parent_tool_use_id`, or `isSidechain` in the
  persisted-transcript spelling) is kept **labelled as such**, never presented as the leaf's own
  death — a log that confidently names the wrong death is worse than the silence it replaces;
  (iv) where a stream carries several candidate records, the one nearest the leaf's own death
  wins and a farther one (a `result` wrap-up naming only the effect, a sub-agent's report) cannot
  bury it, in either arrival order; (v) **nothing is classified** — `produced`,
  `LeafError.transient` and the retry counts are byte-identical to today for every input: a leaf
  retried 3 times today is retried 3 times after this, and one retried 0 times still is;
  (vi) nothing else changes — `capture` still returns the child's raw stdout unmodified (confirm
  the appended text cannot leak into a gate's evidence line: the leaf spawn at `leaves.py:657` is
  the only caller that does not pass `capture=True` — the other three, `gates.py:559`,
  `publish.py:833` and `leaves.py:752`, all do), the
  codex/gemini stream formats degrade to today's behaviour, a stream-less family is untouched, a
  leaf that exits 0 is spawned and reported exactly as today, and the #420 memory-telemetry
  post-mortem (`leaves.py:663-666`) still rides `output` into the same log.
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

Task under review: retain a Claude leaf's marked terminal-error account in its post-mortem output without changing retry classification, raw capture, or ownership attribution.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is explicit and falsifiable: preserve marked evidence with correct ownership and precedence while leaving retry and capture semantics unchanged (`template/tests/test_terminal_error_retention.py:218`). |
| C2 Reproduction (red pre-fix) | PASS | Reverting only the production hunk independently produced 23 behavioral failures, including the missing-report artifact assertion at `template/tests/test_terminal_error_retention.py:221`. |
| C3 Change | PASS | Scope stays within the stipulated stream reader plus its new tests/fixtures, so the diagnostic reaches the existing failure-output contract without altering downstream classification (`template/src/pdca_harness/progress.py:302`). |
| C4 Verification (red→green) | PASS | Independent execution was red with 23 failures before the production change and green with all 34 focused tests after restoration; the broader offline suite also passed 1,792 tests (`template/tests/test_terminal_error_retention.py:221`). |
| C5 Causal adequacy | PASS | The drain now retains the already-read marked event directly, with no capability probe, fallback guard, or retry-policy change that could mask an eager upstream cause (`template/src/pdca_harness/progress.py:197`). |
| T1 Structure | PASS | Decode, extraction, precedence, ownership, and bounded formatting are separated into focused helpers, keeping the hot-loop state transition auditable (`template/src/pdca_harness/progress.py:423`). |
| T2 Shape | PASS | `git diff --check`, docs lint, rendered-site link audit, and host-CI parity are clean, so the patch introduces no formatting or repository-shape defect (`template/src/pdca_harness/progress.py:530`). |
| T3 Runtime | PASS | Focused red→green, the complete offline suite, retry-count guards, raw-capture checks, and alternate-family degradation all pass (`template/tests/test_terminal_error_retention.py:368`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is explicitly deferred to the mandatory publish-time rerun. |
| T5 Judgment | PASS | The affected-file prior-art record covers merged `progress.py` history and the closed/rejected #533/#506 attempts, with no unresolved overlap or semantic upstream lead for this isolated slice (`template/src/pdca_harness/progress.py:35`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether a real failed Claude leaf's retained main/sub-agent wording is truthful and operationally useful in `*.error.log` — offline red→green and binary-field confirmation establish mechanics, not post-mortem fitness (`template/tests/fixtures/README.md:48`). |

### Advisory — code-review

# Advisory code review — issue #538 (progress.py terminal-report retention)

Scope: correctness bugs introduced by this diff, and reuse/simplification/efficiency
opportunities. Grounded on `target/template/src/pdca_harness/progress.py` (patched) and
`target/template/tests/test_terminal_error_retention.py`.

## Correctness

No bugs found. Traced the mechanics the brief's five success-criterion clauses depend on
against the patched source, not just the tests:

- `_note_terminal` / `_TERMINAL_PRECEDENCE` (progress.py:580-603): the "nearest wins, in
  either arrival order" rule is `if precedence[new] < precedence.get(current, 0): return`
  — correctly lets same-or-nearer-shape records overwrite (including a second `_REPORT`
  replacing an older one, per the "newest wins within a shape" clause) while a farther
  shape arriving after OR before a nearer one never displaces it. Hand-traced against all
  the `NearestRecordWins` cases (progress.py:580-603, test file :319-364); matches.
- The `if shape:` guard at progress.py:201 correctly keeps an empty-text wrap-up
  (`_MUTE_WRAPUP`) from ever reaching `_note_terminal`, so it cannot displace an
  already-retained nearer/equal record by masquerading as "a record with nothing to say"
  — `_terminal_error` returns `("", "")` for that case (progress.py:572-576), not
  `("", _WRAPUP)`, so the guard is watertight rather than incidentally correct.
- `_stream_event`'s single-decode-per-line sharing (progress.py:423-447, 197-203) is
  transparent to the three callers: each still calls `_stream_event(ev)` on the
  already-decoded dict and short-circuits on `isinstance(line, dict)` — verified this
  doesn't reintroduce a second `json.loads` for the JSON-string path, consistent with the
  `OneDecodePerStreamLine` test's counted-`json.loads` assertions.
- `capture=True` short-circuits the whole retention path only at the append step
  (`terminal["text"] and not capture`, progress.py:303), but the drain still evaluates
  `_terminal_error` unconditionally whenever `stream_json` is set — dead work when both
  `capture` and `stream_json` are true together, but no caller in the tree currently
  passes both (confirmed against all four `run_with_heartbeat` call sites:
  gates.py:559-562, publish.py:833-836, leaves.py:752-754 pass `capture=True` alone;
  leaves.py:657-660 passes `stream_json=True` alone), so this is inert today, not a bug.
- The append block (progress.py:303-311) runs regardless of `rc`, so on a clean `rc == 0`
  exit it still formats and appends `terminal["text"]` into `output` — wasted string work
  the caller (`leaves._invoke`, which only inspects `output` inside `if rc != 0:`,
  leaves.py:661-670) discards immediately. Cosmetic only, not worth a fix.

## Reuse / simplification

Nothing to flag. The whitespace-flattening idiom in `_report_line` (progress.py:654,
`" ".join(text.split())`) duplicates the same one-liner already used independently in
`assemble.py:106`, `driver.py:349`/`:182`, `leaves.py:514` — but each of those is a
private local idiom already, not a shared helper this patch bypassed; not worth
introducing a cross-module dependency for a one-line built-in composition, and it doesn't
fall inside this patch's declared single-file scope (progress.py only) anyway.

The patch adds no other production file (fixtures + one new test file only, as scoped),
and the new helpers (`_stream_event`, `_terminal_error`, `_note_terminal`,
`_is_subagent_event`, `_claude_message_texts`, `_claude_result_texts`, `_report_line`)
are each single-purpose with no overlap with pre-existing `progress.py` code — the one
piece of duplication this patch explicitly *removes* (three independent `json.loads` +
"is it a dict" guards collapsing into one `_stream_event`) is itself the efficiency win
called out in the diff.

## Verdict

Diff is clean on both lenses. No NEEDS-HUMAN items.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Decide whether a real failed Claude leaf's retained main/sub-agent wording is truthful and operationally useful in `*.error.log` — offline red→green and binary-field confirmation establish mechanics, not post-mortem fitness (`template/tests/fixtures/README.md:48`).

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
