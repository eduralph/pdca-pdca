# Result — issue 332 / autoiterate-soft-hard-defer

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: auto-iterate fires on 13.5% of eligible-checked attempts (31/230 measured;
  199 vetoed) because builder-fixability is inferred from the taxonomy cell instead of
  stated by the reviewer, and because one HUMAN finding vetoes the rebuild outright.
  Deliver: soft/hard round budgets, a reviewer-stated `[impl]` tag honoured by the
  classifier, deferred (not blocking) human findings with a loss-proof ledger, and the
  Validation-row match fixed for its three observed forms.
- Success criterion: (1) with `soft_auto_iters`=3, `max_auto_iters`=5, the worked
  example holds: rounds ≤3 always fire; 3<n≤5 fire only if the IMPL count did not
  increase; n>5 never; `soft_auto_iters` unset defaults to `max_auto_iters` so a
  rendered instance reproduces today's behaviour exactly. (2) A judgment-cell (C5/T5)
  verdict `NEEDS-HUMAN [impl]` is promoted to IMPL only for promotable elements
  (judgment-kind minus V, derived from `gates.canonical_elements()` the way
  `_GATE_ELEMENTS` is at `assemble.py:50`), with STANDING checked before the tag so a
  tagged V row stays STANDING; an untagged bullet still classifies HUMAN (fail-safe
  unchanged); gates-that-could-not-run / declared / unregistered dependencies are never
  promotable. (3) `eligible()` (`autoiterate.py:56`) becomes "≥1 IMPL", with HUMAN
  findings deferred to a ledger kept out of `DOWNSTREAM_OF_BRIEF`, listed in
  `state.CYCLE_EVIDENCE_ONLY`, and merged deduped into §6 at assemble so every deferred
  finding reaches the human at handover under the C6 guard; empty §6 still halts
  (never auto-accept); HUMAN-only sets still halt immediately; `rationale()` states
  what was addressed and what was deferred, and still carries IMPL items only into the
  builder's carry-forward. (4) The STANDING match at `assemble.py:439` accepts all
  three production forms (`Validation — fitness-to-purpose`,
  `V — Validation — fitness-to-purpose`, `Validation -- fitness-to-purpose`) by
  normalizing an optional leading `<element-id> —` prefix and folding ASCII `--`,
  comparison exact *after* normalization; `_REVIEW_PROMPT` and the role prompts are
  aligned in the same pass. (5) **The #335 fold:** ledger retirement recognises a
  still-open §6 row with the SAME `_same_finding` relation the tick match uses, assigned
  **exact-first, two-tier** (mirroring the tick match): an open row *verbatim equal* to a
  ledger entry protects that entry ALONE (a still-open near-twin cannot shield its
  exactly-ticked neighbour, so near-twin pairs still drain); an *edited* open row
  (verbatim owner of nothing) protects EVERY entry it `_same_finding`-matches — fail
  closed: a lingering finding is visible, a lost one is unrecoverable. NOT the flat
  symmetric-fuzzy exclusion (`any(_same_finding(entry, o) for o in still_open)`): that
  re-creates the permanently-unclearable pair — an exactly-ticked entry whose near-twin
  stays open retires nothing, every round, forever. Shape proven in the instance
  (getwyrd/wyrd-pdca@e4fdf3b): a `protected: set[int]` computed once before the tick
  loop; the tick loop's guard becomes `hits[0] not in protected`. Three tests ship with
  it: (a) the #335 repro — an annotated-unticked row plus a similar ticked new finding →
  the unadjudicated entry survives; (b) a matcher-drift guard — every edit shape
  `_same_finding` tolerates in a *tick* must also protect when left *open*, even against
  an exact tick (pins the asymmetry itself so the two sides cannot drift apart again);
  (c) an edited open row matching two near-twin entries protects both. All demonstrable
  by C4-verify via the offline driver suite.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the five numbered items of the issue plus the #335 fold, exactly as in the
  success criterion; `auto-iterate.json` extended to carry per-round IMPL counts with
  `count()` tolerant of the old shape; `agents/reviewer.md`-family prompts updated in
  step with `_REVIEW_PROMPT` (`leaves.py:1395` — the issue's `:820` is stale) and
  `_advisory_prompt`'s
  "when in doubt, OMIT '[impl]'" (`leaves.py:2001`) replaced by a required
  `[impl]`/`[human]` tag with the untagged→HUMAN fail-safe; tests parameterized over
  the three V-row forms (the existing `test_autoiterate.py` hard-codes the exact form
  at its `_STANDING_ROW`), table-driven round gating, C5/T5-beside-IMPL defers vs
  C5/T5-alone halts, tag-on-C1/C3/V ignored, round-1 HUMAN finding still in §6 at
  handover, and `test_empty_section6_halts_and_never_auto_accepts` passing unchanged.
  / out of scope: routing input-cell defects to `iterate-plan` (the issue's declared
  follow-up — `autoiterate.DECISION` stays the single `iterate-do` token); #334 itself
  (already landed — `CYCLE_EVIDENCE_ONLY` exists in `state.py`; this change only adds
  the new ledger file to it).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
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
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
