# Result — issue 536 / per-attempt-record-and-one-error-log-meaning

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A retried leaf's `*.error.log` is written only **after** the retry loop ends
  (`leaves.py:720`), so two things are broken at once and neither can be fixed without the
  other. (a) While attempt 2 runs there is nothing on disk explaining attempt 1, and a run
  killed mid-retry loses every attempt's account — the file never existed. (b) The reason
  (a) cannot simply be flushed earlier: the **presence** of that file is hard-coded at four
  sites to mean *"the leaf ran and FAILED"*, so flushing it early makes that sentence false
  at every one of them. Two of the four are executable recovery discriminators
  (`leaves.review_never_ran` `:2103-2104`; `run_advisory_leaves(only_missing=True)`
  `:2800-2801`), so a reviewer that the death window merely **interrupted** would be
  retired instead of re-run, and the bundle would reach sign-off **with no review of the
  diff at all**. Separately, `_format_leaf_attempt` (`:724-730`) embeds `exc.output` raw at
  `:727`, so a leaf's own captured text can impersonate whatever the harness uses to
  describe its own run — which matters only once that description exists.
  **(c) — the second child.** The same root has an artifact face: the three harvest sites
  copy their artifact on a bare existence test (`:2519-2523`, `:2851-2854`, `:3152-3155`)
  with no notion of *which* attempt wrote it, so a truncated verdict a **dead** attempt left
  in the sandbox is adopted as the leaf's own output — exactly what `engine/README.md:44-68`
  forbids ("no evidence must never be filed as a verdict"). Its own reader, the leaf-status
  label at `assemble.py:84-85` (`"leaf did not run (transient infra — safe to re-run)"`),
  becomes false once a run whose last attempt exited 0 can be routed there.
- Success criterion: With the patch applied to the target base, all of:
  1. **Each failed attempt's record is on disk before the next attempt starts.** A leaf
     observing the bundle during attempt 2 finds attempt 1's account already there; today
     it finds no file. A run killed mid-retry therefore leaves a post-mortem.
  2. **An unsettled account does not read as "ran and FAILED" to any reader.** All four
     readers enumerated under `Citations expected` agree, because they consult **one**
     point of truth rather than each testing the file's existence: an error log left by a
     leaf whose attempts are not yet spent recovers the leaf exactly as an absent one does
     (`review_never_ran` → True; `only_missing` does not skip it), and the operator-facing
     wording in `assemble._missing_review_text` / `driver._resume_interrupted_check` names
     both shapes instead of asserting only one.
  3. **A leaf's own text cannot impersonate that distinction.** Whatever distinguishes an
     unsettled account from a spent one is neutralised in the captured stderr tail
     `_format_leaf_attempt` embeds, and is recognised only as the log's **last non-blank
     line, alone** — never as a substring, and never mid-line. (Round 3 shipped this leg
     with the token embedded mid-line, which is not the failure mode.)
  4. **The shipped resilience contract is unchanged.** Attempt count, the transient rule,
     the backoff schedule, the staleness clear (`:698-702`) and the `_memory_log_for`
     derivation are exactly as shipped; a **successful** leaf still leaves no error log
     behind; the #420 memory-telemetry post-mortem still rides `output` into the same log
     and survives the neutralisation intact; and `template/tests/test_leaf_resilience.py`
     stays green **untouched** — verified at Plan, not assumed: its error-log *content*
     assertions are `assertIn` (`:64`, `:74`) and its *existence* assertions read the FINAL
     state only (`:63` after a spent retry, `:83`/`:91` after success), so a per-attempt
     flush and a trailer do not disturb any of them.
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed.** A record flush
     that fails (a read-only bundle dir, ENOSPC) **must not end the run**: the shipped stop
     rule is the only stop rule, and the un-flushed records stay in hand so the loop's final
     write still persists them. This is strictly no worse than the base, which persists
     nothing until the end. v5 measured the opposite choice at 3 attempts → 1 and it was
     the finding that could not be closed, because criterion (4) and a fail-closed
     withdrawal cannot both hold. Do not re-introduce it. **This has a mechanical check:**
     `test_leaf_resilience.py:62` asserts `self._runs() == 3` for a transient leaf, and a
     Plan-time run of the base measured exactly 3 attempts — any narrowing turns that
     shipped test red, which criterion (4) forbids.
- Repo + branch target: eduralph/pdca-harness @ main   (base `acb214a`; every
  `path:line` in this brief was re-verified against it while the brief was written)
- Scope (one logical fix) / out of scope: Make each failed attempt's account exist on disk from the moment that attempt
  fails rather than only once the retry loop ends; and make the distinction this creates —
  an account whose leaf has not yet settled versus one whose leaf has spent its attempts —
  carry **a single point of truth that every reader consults**, so that no reader can be
  left speaking the old meaning. A leaf's own captured text must not be able to impersonate
  that distinction. (The single-point-of-truth constraint is a *design constraint carried
  from five rounds of measured evidence*, not a mechanism chosen here: which form it takes —
  predicate, enum, dataclass — stays Do's call.) The unsettled state's whole lifetime is
  **inside `_invoke_leaf_resilient`**: the loop ends either by failing, which settles the
  records, or by succeeding, which discards them as today. No caller changes.
  / **out of scope:** the artifact/harvest half in every part — do **not** pass an artifact
  path into the wrapper, do **not** touch the three harvest sites (`:2519-2523`,
  `:2851-2854`, `:3152-3155`), do **not** add a residue quote/withdrawal, a settle-at-harvest
  hook, or an empty-run classification, and do **not** extend the unsettled state past the
  wrapper's return. Do **not** touch `assemble.py:80-89` (the leaf-status labels) — that
  reader belongs to the carried-out half and is false only under it. The builder path is
  `#537`: do not move `_do_build_command` (`:1824`) onto the resilient path, do not touch
  `do_build`'s capture (`:1765-1778`), `_build_prompt` (`:1834`) or `_stub_build` (`:1889`).
  What counts *as* a transient death is `#539`: do not touch `progress.py`, do not redefine
  `LeafError.transient` (`:103-108`), do not add a signal-death predicate; the retry set is
  reused exactly as shipped. Also out: a lane/worktree reset between attempts; any new
  `pdca.toml` knob; the gate-side transient (#371); #510's remedy; the nine other leaves
  still on plain `_invoke`. Do **not** create `template/tests/fixtures/` and do **not** add
  `template/tests/test_terminal_error_classification.py` — those are #538/#539's.

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
