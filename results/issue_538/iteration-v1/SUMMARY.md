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

Task under review: retain a Claude leaf's marked terminal error report in its preserved failure log without changing retry classification or other callers' output.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is falsifiable across retention, ownership, precedence, and unchanged retry semantics, matching the existing failure-output contract at `template/src/pdca_harness/leaves.py:657`. |
| C2 Reproduction (red pre-fix) | PASS | The pre-fix behavior is established: stashing only the production change produced 19 retention failures, including the direct error-log assertion at `template/tests/test_terminal_error_retention.py:187`. |
| C3 Change | PASS | The scope boundary is satisfied—one permitted production file plus the specified new tests and fixtures—so sibling work in `leaves.py` and `assemble.py` is not put at collision risk; the production seam is `template/src/pdca_harness/progress.py:175`. |
| C4 Verification (red→green) | PASS | Independent red→green was reproduced (19 of 29 assertions failed pre-fix; all 29 passed patched), and the patched full driver suite passed 1,787 tests; the production-path assertion is at `template/tests/test_terminal_error_retention.py:194`. |
| C5 Causal adequacy | PASS | The missing retention is corrected where stdout is already drained and where failure output is assembled, with no capability probe or retry-classification guard; see `template/src/pdca_harness/progress.py:186` and `template/src/pdca_harness/progress.py:296`. |
| T1 Structure | PASS | File ownership remains coherent: parsing and bounded retention stay in the shared progress module while end-to-end expectations stay in the new test module at `template/tests/test_terminal_error_retention.py:1`. |
| T2 Shape | PASS | The shape is reviewable and mechanically clean: `git diff --check`, docs lint, site render/link audit, and host-CI parity all passed; the public output contract is documented at `template/src/pdca_harness/progress.py:52`. |
| T3 Runtime | PASS | Runtime regression risk is discharged by the targeted 29-test run and the full 1,787-test offline driver run, including raw-capture and other-family guards at `template/tests/test_terminal_error_retention.py:336`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the frozen row is deferred and the substantive PR-description/tracker audit is owed to the mandatory publish re-gate. |
| T5 Judgment | PASS | Overall risk is acceptable: retention is bounded, unknown formats degrade to prior behavior, and an affected-path scan of the complete closed/merged PR corpus found six merged precedents and no closed-unmerged duplicate; see `template/src/pdca_harness/progress.py:491`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide whether a whitespace-flattened, 500-character diagnostic line is sufficient for real post-mortems—truncation can omit decisive context even though retention mechanics pass; see `template/src/pdca_harness/progress.py:615`. |

### Advisory — code-review

# Check advisory — code review (correctness + reuse/efficiency lens)

Scope: only the hunks in `patch.diff` (progress.py + new tests/fixtures), grounded
against `template/src/pdca_harness/progress.py` and `leaves.py` at `$PDCA_TARGET`.

## Correctness

Traced the new retention path end-to-end (`_terminal_error` → `_note_terminal` →
the `terminal["text"]` append in `run_with_heartbeat`, `progress.py:192-199,
296-305,469-622`) against all four `run_with_heartbeat` call sites
(`leaves.py:657`, `leaves.py:752`, `gates.py:559`, `publish.py:833`) and the
precedence table (`_TERMINAL_PRECEDENCE`, `progress.py:482`). No bug found:

- The only caller that sets `stream_json=True` (`leaves.py:657-660`) never also sets
  `capture=True`, and the three `capture=True` callers never set `stream_json=True`,
  so the "skip the append under `capture`" branch (`progress.py:297`) is dead in
  production exactly as the docstring claims — and the patch's own test
  (`test_capture_returns_the_childs_raw_stdout_unmodified`, exercising that
  otherwise-impossible `capture=True, stream_json=True` combination directly
  against `run_with_heartbeat`) is the only place that combination is checked, which
  is the right way to cover an invariant no caller currently triggers.
- `_note_terminal`'s `<` comparison (`progress.py:571`) correctly lets an equal
  (same-shape) precedence overwrite — "newest wins within a shape" — while a
  strictly lower one is rejected in either arrival order; verified against all six
  `NearestRecordWins` cases and the precedence table by hand, no off-by-one.
- `terminal["shape"]` is only ever mutated from the single drain thread
  (`progress.py:194-196`), read from the main thread only after
  `reader.join(timeout=5)` (`:292`) — the same join-then-read pattern the
  pre-existing `produced` dict already uses, so this doesn't introduce a new race,
  just extends an existing one.
- `use_stream` / family-profile gating (`leaves.py:648-649`) confirms `_terminal_error`
  only ever sees `stream_format="claude-stream-json"` in production, matching its
  `fmt != "claude-stream-json"` degrade-to-`("", "")` guard (`progress.py:525`).

## Reuse / efficiency

- **Minor** — `progress.py:192-199`: the drain loop now calls `json.loads` on every
  stream line **three** times (`_is_session_event`, the new `_terminal_error`, then
  `_stream_tool_label`), each independently parsing and independently swallowing
  `(ValueError, TypeError)`. This was already 2x before the patch; the patch adds a
  third pass rather than parsing once and dispatching the parsed `dict` to the three
  classifiers. Given `_terminal_error` is explicitly written "in the same shape" as
  `_is_session_event" for symmetry, a shared one-parse-then-dispatch would have been
  a natural simplification here, and the stream drain is a genuine hot loop for a
  long session (thousands of lines). Not a correctness issue — each function
  degrades safely on a bad parse — just wasted repeated work.
  - NEEDS-HUMAN [impl] — worth asking the builder to parse once per line and pass
    the decoded event to all three classifiers, since the three now duplicate the
    exact same `json.loads` + `isinstance(ev, dict)` guard
    (`progress.py:194-199,528-532,629-633`).

## Tests

- `_run_leaf` / `_heartbeat` correctly drive the production path
  (`leaves._invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat`) with
  a `family="claude"` stub leaf, so `use_stream` is true and the new code actually
  executes (verified against `families.resolve("claude")`,
  `stream_argv`/`stream_format` at `families.py:91-92`). The C4 gate log confirms a
  genuine (non-vacuous) red: 10/29 cases fail on revert, not an import-time
  `PDCA-UNVERIFIABLE`, and fixtures are present so `PinnedVendorRecords` isn't
  trivially skipped.
- One small gap: `_terminal_error`'s "an error record with nothing to say is not
  evidence" branch (`progress.py:544-546`, a `result`/`is_error` event whose
  `_report_line` comes back empty) has no direct test — only the non-empty wrap-up
  path (`_WRAPUP`) is exercised. Low risk since the branch is a straightforward
  early-return, but it's the one line in the new retention logic without a red/green
  witness of its own.

## Summary

Clean on the correctness lens — no bugs found in the traced retention/precedence
path, and it degrades safely everywhere it's supposed to. One efficiency nit (the
now-3x per-line JSON parse) worth a quick builder pass, and one minor untested
branch (empty-text wrap-up). Neither blocks; both are cheap follow-ups.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — The maintainer must decide whether a whitespace-flattened, 500-character diagnostic line is sufficient for real post-mortems—truncation can omit decisive context even though retention mechanics pass; see `template/src/pdca_harness/progress.py:615`.
- [ ] worth asking the builder to parse once per line and pass

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — worth asking the builder to parse once per line and pass
- By / date: auto-iterate / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
