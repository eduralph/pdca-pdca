# Result — issue 456 / split-lineage-record

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: after `split.accept(parent, ids, cfg)` —
  1. each created child bundle contains `split-lineage.json` naming its `parent`, its
     `siblings` (the *other* children of the same split, by tracker id) and its `depth`
     (parent's depth + 1, so recursion depth is recorded without anyone counting);
  2. the parent bundle contains `split-lineage.json` naming its `children`;
  3. **the mixed-role case is preserved**: for a parent that *itself* already carried a
     child record, the post-accept record still carries its own `parent` and `siblings`
     **and** gains `children`. This is the specific defect the previous attempt shipped —
     it overwrote the child record with a parent one, keeping only `depth`, so a depth-1
     bundle silently lost its sibling set and the whole ratchet returned at depth ≥ 1
     (reproduced: bundle 601 scored `6 / watch` with no advisories; after
     `split.accept(601, [701,702])` it was back to `9 / oversized`). A test must accept a
     split whose parent is itself a child and assert both edges survive — asserting only
     that `depth` survives blesses the loss rather than catching it;
  4. one tolerant module-level reader returns the parsed record, or `None` for an absent,
     unreadable, malformed or wrong-`version` file. It never raises: a provenance reader
     that can throw into a beat is worse than one that abstains, and every consumer must
     behave exactly as today when it returns `None`;
  5. the record is **not** added to `state.DOWNSTREAM_OF_BRIEF` (`state.py:82-110`), so it
     survives `iterate-plan` and the archiving of a rejected attempt — it is provenance,
     not attempt output. Assert this by name in a test, not in a comment;
  6. the existing transactional discipline is preserved: child records are written into
     `staging` and moved with the rest (`split.py:348-362`, moved by `accept` at
     `:406-427`), and the parent's record is written **before** `CLOSE_MARKER`
     (`split.py:453-461` region) so a failed write leaves the parent un-marked and
     `_rollback` still correct. A failed accept restores the parent's prior record bytes.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
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
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of the change that records durable split lineage in child and parent bundles while preserving mixed-role and rollback semantics.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief settles the schema, mixed-role merge, tolerant-reader behavior, archive persistence, transaction ordering, scope, and an executable falsifier, so the required outcome is unambiguous. |
| C2 Reproduction (red pre-fix) | PASS | The decision was whether the retained test genuinely detects the missing capability: a clean `main` tree collected all 18 tests and all 18 errored on absent lineage symbols, beginning with the functional case at `template/tests/test_split_lineage.py:78`. |
| C3 Change | FAIL | The reader must abstain for every unreadable or malformed record, but invalid UTF-8 bytes raise `UnicodeDecodeError` because the decode at `template/src/pdca_harness/split.py:387` is outside the `ValueError` handler; a consumer can still be crashed by the provenance file. |
| C4 Verification (red→green) | FAIL | The nominal leg is real (18 red errors, then 18/18 green), but a direct invalid-byte probe still raises at `template/src/pdca_harness/split.py:387`, so the green suite does not verify the stated never-raises contract. |
| C5 Causal adequacy | PASS | The change creates provenance where the split is materialised and records the inverse parent edge before close (`template/src/pdca_harness/split.py:469`, `template/src/pdca_harness/split.py:595`); no capability probe or symptom-only runtime guard was introduced. |
| T1 Structure | PASS | The patch applies cleanly to the exact current `main` SHA, touches only the three scoped paths, and leaves lineage outside the attempt-output registry at `template/src/pdca_harness/state.py:82`. |
| T2 Shape | PASS | The independent docs rerun rendered 22 pages with a clean link audit, and the documented one-file mixed-role contract is grounded at `docs/07-crosscutting.md:217`. |
| T3 Runtime | PASS | Copier 9.17.1 was actually exercised: all 7 render/update-compat tests passed, the full offline suite passed 1,617 tests with 2 unrelated skips, and the carried-forward unreadable-prior transaction case passes at `template/tests/test_split_lineage.py:279`. |
| T4 Contribution | NEEDS-HUMAN | Re-run the contribution lint against the actual commit and PR artifacts before publish — those artifacts are absent from the reviewer inputs, so the checker correctly returned deferred at `template/src/pdca_harness/cli.py:1089` and the recorded PASS cannot be independently confirmed. |
| T5 Judgment | PASS | The change remains one lineage-contract fix with no downstream consumers, and an exact affected-path scan covered merged history plus closed/rejected PRs: no prior `split-lineage.json` implementation or rejected overlapping change exists. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | After the tolerant-reader defect is corrected, decide whether this one-file independent-edge contract is the right prerequisite for the downstream sizing and flow work — mechanical checks cannot determine that product-level fitness. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Re-run the contribution lint against the actual commit and PR artifacts before publish — those artifacts are absent from the reviewer inputs, so the checker correctly returned deferred at `template/src/pdca_harness/cli.py:1089` and the recorded PASS cannot be independently confirmed.
- [ ] Validation — fitness-to-purpose — After the tolerant-reader defect is corrected, decide whether this one-file independent-edge contract is the right prerequisite for the downstream sizing and flow work — mechanical checks cannot determine that product-level fitness.

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Re-run the contribution lint against the actual commit and PR artifacts before publish — those artifacts are absent from the reviewer inputs, so the checker correctly returned deferred at `template/src/pdca_harness/cli.py:1089` and the recorded PASS cannot be independently confirmed.
- By / date: auto-iterate / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
