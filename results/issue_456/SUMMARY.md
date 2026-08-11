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

Review of the change that records transactional split lineage in child and parent bundles and provides a tolerant reader.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | No specification decision is missing: the contract fixes independent optional edges, mixed-role preservation, tolerance, persistence, and transaction ordering (`docs/07-crosscutting.md:217`). |
| C2 Reproduction (red pre-fix) | PASS | The test must fail through executed assertions rather than import collection; with production hunks stashed, all 23 tests ran and failed, including the child-edge check at `template/tests/test_split_lineage.py:80`. |
| C3 Change | FAIL | Decide whether a schema-invalid `depth` is malformed and make the public contract consistent: an independent probe returned the record with `"depth": "one"`, because the reader returns every version-1 object at `template/src/pdca_harness/split.py:397`, while the declared reader contract requires abstention. |
| C4 Verification (red→green) | PASS | The isolated rerun executed 23 failing tests without the production hunks and the same 23 passing tests with them restored; the mixed-role regression is exercised at `template/tests/test_split_lineage.py:104`. |
| C5 Causal adequacy | PASS | No symptom-guard decision is owed: the absent on-disk provenance is addressed at the writer/reader and rollback boundary, including pre-write snapshot validation at `template/src/pdca_harness/split.py:550`. |
| T1 Structure | PASS | No scope expansion needs approval: the patch stays within the declared docs, split module, and test module, and lineage remains absent from the archival list at `template/src/pdca_harness/state.py:82`. |
| T2 Shape | FAIL | Choose one externally documented reader shape before downstream consumers rely on it: the docs promise `None` for a nonnumeric depth at `docs/07-crosscutting.md:229`, but the implementation and test preserve that invalid value at `template/tests/test_split_lineage.py:236`. |
| T3 Runtime | PASS | The external Copier dependency was genuinely exercised, not skipped: 7/7 render/update tests passed with Copier 9.17.1, the offline suite passed 1622 tests, and the transactional rollback path is covered at `template/tests/test_split_lineage.py:348`. |
| T4 Contribution | NEEDS-HUMAN | Re-run contribution lint after the commit and PR body are drafted and confirm both carry issue #456 plus the required user-impact opener — those artifacts do not yet exist, so the checker is substantively deferred by design at `template/src/pdca_harness/cli.py:1089`; merged history and the sole rejected PR were checked by affected path with no rejected overlap. |
| T5 Judgment | PASS | No further architecture choice is owed for the core model: independent child and parent edges preserve recursive mixed-role bundles, directly exercised at `template/tests/test_split_lineage.py:104`, and the affected-path prior-art sweep found no rejected duplicate. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the lineage contract is fit for the planned downstream consumers before sign-off — this slice intentionally ships no consumer, so the writer/reader behavior at `template/src/pdca_harness/split.py:373` has no end-to-end sizing or flow validation yet. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T4 Contribution — Re-run contribution lint after the commit and PR body are drafted and confirm both carry issue #456 plus the required user-impact opener — those artifacts do not yet exist, so the checker is substantively deferred by design at `template/src/pdca_harness/cli.py:1089`; merged history and the sole rejected PR were checked by affected path with no rejected overlap.
- [x] Validation — fitness-to-purpose — Decide whether the lineage contract is fit for the planned downstream consumers before sign-off — this slice intentionally ships no consumer, so the writer/reader behavior at `template/src/pdca_harness/split.py:373` has no end-to-end sizing or flow validation yet.
- [x] size backstop — this slice is behaving oversized: 2 round(s) already spent (threshold 2). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- By / date: Eduard Ralph / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- File a bug: `docs/07-crosscutting.md` claims `split.read_lineage` returns `None` for a nonnumeric `depth`, but it does not (reader is permissive; `_recorded_depth` absorbs the value) — delete the clause. Source of reviewer C3/T2 FAIL on issue_456.
