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

Task under review: make `pdca split --accept` persist tolerant, mixed-role lineage records for every child and the parent without weakening split transactionality.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is falsifiable across child, parent, mixed-role, tolerant-read, retention, and rollback outcomes, with executable assertions beginning at `template/tests/test_split_lineage.py:66`. |
| C2 Reproduction (red pre-fix) | PASS | On target HEAD with only the new test retained, all 14 tests error on absent `split.LINEAGE`/`split.read_lineage`, establishing the pre-fix gap through the module import at `template/tests/test_split_lineage.py:25`. |
| C3 Change | FAIL | A snapshot-read failure after child moves escapes the rollback block and leaves both children materialised while the parent remains open; the unprotected snapshot is at `template/src/pdca_harness/split.py:511`. |
| C4 Verification (red→green) | PASS | The focused module independently changed from 14 errors on target HEAD to 14 passes with the patch, exercising the acceptance path from `template/tests/test_split_lineage.py:68`. |
| C5 Causal adequacy | PASS | The missing provenance is addressed at its creation boundary by staging child records and merging the parent record, with no capability probe or symptom guard (`template/src/pdca_harness/split.py:426`). |
| T1 Structure | PASS | The change stays within the declared split module, one focused test module, and the existing split documentation section (`docs/07-crosscutting.md:217`). |
| T2 Shape | PASS | Docs lint and a 22-page site render/link audit both pass, and the documented mixed-role schema is grounded at `docs/07-crosscutting.md:220`. |
| T3 Runtime | NEEDS-HUMAN | Require a real Copier render/update-compat run before sign-off — `copier` is absent on this host, so all seven root tests skipped under guards such as `tests/test_render_and_run.py:31`, although the 1,613-test template suite passed with two unrelated skips. |
| T4 Contribution | NEEDS-HUMAN | Confirm the PR description and commit message carry the issue id and a user-impact opener — those contribution artifacts were not among the reviewer inputs, so the recorded green gate could not be independently reproduced. |
| T5 Judgment | NEEDS-HUMAN | Decide whether closed/rejected work contains preferable or conflicting prior art — affected-path merged history was checked and contains no earlier lineage implementation, but closed/rejected refs are unavailable locally. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether this independent-edge schema is the right durable interface for children 2–4 and #449 — mechanical behavior passes, but the intentionally out-of-scope consumers have not yet demonstrated fitness (`docs/07-crosscutting.md:223`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T3 Runtime — Require a real Copier render/update-compat run before sign-off — `copier` is absent on this host, so all seven root tests skipped under guards such as `tests/test_render_and_run.py:31`, although the 1,613-test template suite passed with two unrelated skips.
- [ ] T4 Contribution — Confirm the PR description and commit message carry the issue id and a user-impact opener — those contribution artifacts were not among the reviewer inputs, so the recorded green gate could not be independently reproduced.
- [ ] T5 Judgment — Decide whether closed/rejected work contains preferable or conflicting prior art — affected-path merged history was checked and contains no earlier lineage implementation, but closed/rejected refs are unavailable locally.
- [ ] Validation — fitness-to-purpose — Decide whether this independent-edge schema is the right durable interface for children 2–4 and #449 — mechanical behavior passes, but the intentionally out-of-scope consumers have not yet demonstrated fitness (`docs/07-crosscutting.md:223`).

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
- Iteration delta (if iterating): C3 FAIL (verified): the parent-lineage snapshot read at template/src/pdca_harness/split.py:511 (`prior_lineage_bytes = lineage_path.read_bytes() if lineage_path.exists() else None`) sits in the gap between accept()'s two protected regions — after the children are moved into place, before the try block whose except performs _rollback(created) + prior-bytes restore + marker-unlink. If the path exists but read_bytes() raises (e.g. a directory at split-lineage.json — a case the patch's own tolerant-reader tests construct — or a permissions error), the exception escapes with children materialised and the parent left open, violating the brief's item 6 transactional guarantee. Fix: move the snapshot inside the protected try (the restore logic already handles None vs bytes) or otherwise ensure a snapshot-read failure triggers _rollback(created); add one test — a parent with a directory at the lineage path must fail accept() cleanly (no children left, no CLOSE_MARKER, no lineage record). Everything else stands: mixed-role merge, tolerant reader, staging discipline, DOWNSTREAM_OF_BRIEF exclusion, and the real copier T3 run (7/7 root tests passed) are good — keep the approach, harden only this one boundary.
- By / date: Eduard Ralph / 2026-08-08

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
