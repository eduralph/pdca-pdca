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
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpz1sjfvpe/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: implement issue #332 auto-iterate soft/hard budgets, reviewer `[impl]` promotion, deferred HUMAN ledger, Validation-row normalization, and the folded #335 ledger-retirement fix.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the five required behaviours and folded #335 retirement invariant, with no blocking external dependency declared in `brief.md:10`. |
| C2 Reproduction (red pre-fix) | PASS | Reversed implementation plus patched tests failed 17 failures / 43 errors, including missing `soft_auto_iters`, `LEDGER_FILE`, and `budget_verdict`; patched regression coverage is grounded in `template/tests/test_autoiterate.py:947`. |
| C3 Change | PASS | The change covers the decision path from classification through budget gating and ledger persistence, so the human decision is whether this feature scope matches #332 rather than whether a named component is absent; see `template/src/pdca_harness/flow.py:270`. |
| C4 Verification (red->green) | PASS | Red was reproduced in `/tmp/pdca-review-red`; green was reproduced with `PYTHONPATH=src python3 -m unittest tests.test_autoiterate` and `tests.test_size_signal`, plus full `unittest discover`, with core checks at `template/tests/test_autoiterate.py:1033`. |
| C5 Causal adequacy | PASS | The fix removes the taxonomy-proxy veto and persists deferred human findings instead of guarding around a present capability, so the root-cause decision is covered by `template/src/pdca_harness/autoiterate.py:75`. |
| T1 Structure | PASS | The implementation keeps separate builder and human carry-forward channels, which is the structural decision that prevents deferred judgments from being handed to Do; see `template/src/pdca_harness/autoiterate.py:181`. |
| T2 Shape | NEEDS-HUMAN | The exact `./engine/scripts/run-docs-check.sh` wrapper is absent from `$PDCA_TARGET`, so the docs-render/link-audit PASS in `check-gates.json` is provisional despite `git diff --check` passing. |
| T3 Runtime | PASS | The frozen T3 non-gating failure was not reproduced: full `PYTHONPATH=src python3 -m unittest discover -s tests` passed against `$PDCA_TARGET`, with the #335 drain/protection cases at `template/tests/test_autoiterate.py:1116`. |
| T4 Contribution | NEEDS-HUMAN | The exact `pdca-pdca contribcheck` tool is absent from `$PDCA_TARGET`, so the tracker/PR-body PASS in `check-gates.json` needs human confirmation before relying on it. |
| T5 Judgment | PASS | Prior-art search by affected paths plus GitHub issue search found #332/#335 as the live requested work and older #293/#324/#334 as related prerequisites, not an already-landed duplicate; see `template/src/pdca_harness/state.py:113`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether auto-deferring human findings is operationally acceptable, because even with green runtime tests this changes when reviewers are interrupted; see `template/src/pdca_harness/autoiterate.py:237`. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T2 Shape — The exact `./engine/scripts/run-docs-check.sh` wrapper is absent from `$PDCA_TARGET`, so the docs-render/link-audit PASS in `check-gates.json` is provisional despite `git diff --check` passing.
- [ ] T4 Contribution — The exact `pdca-pdca contribcheck` tool is absent from `$PDCA_TARGET`, so the tracker/PR-body PASS in `check-gates.json` needs human confirmation before relying on it.
- [ ] Validation — fitness-to-purpose — Human sign-off must decide whether auto-deferring human findings is operationally acceptable, because even with green runtime tests this changes when reviewers are interrupted; see `template/src/pdca_harness/autoiterate.py:237`.
- [ ] size backstop — this slice is behaving oversized: patch is 112 KB (threshold 100 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Size backstop (§6 item 4): patch is 112 KB / 16 files against the 100 KB threshold — the slice is oversized, not wrong. The brief bundles five numbered behaviours plus the #335 fold; re-plan should author the split via `pdca split` (e.g. budgets + `[impl]` promotion vs. deferred-HUMAN ledger + #335 retirement vs. Validation-row normalization) rather than rebuilding the single slice. Work quality itself was strong (C4 green, 9/12 advisory PASS), so carry the implementation shape forward into the child briefs.
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
