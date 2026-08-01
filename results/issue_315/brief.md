# Design proposal — issue 315 / prepublish-review-stage

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** prepublish-review-stage
- **Kind:** enhancement (design proposal)
- **Goal:** a native pre-publish review stage in `publish.py` — N parallel review passes
  over the bundle's full diff, unioned/deduped, with BUG-class findings re-entering Do
  under the existing bounded iterate budgets — so the serialized-review-depth churn
  measured on external reviews (~1 new real finding per re-review round; extreme case 13
  rounds on one PR) is paid *before* the draft PR opens, not after.
- **Success criterion:** with the stage enabled: (a) publish runs N (configurable,
  default 3) review passes over the bundle's diff between the T4 gate passing and the
  first git step; (b) findings are unioned and deduped, and classes the instance rubric
  explicitly rejects are dropped; (c) BUG-class findings feed the brief's carry-forward
  block and trigger a bounded re-entry to Do (the `autoiterate.py` budget shape — never
  open-ended); (d) publish proceeds only when a pass completes with every finding fixed
  or recorded-rejected; (e) stage disabled (the default) ⇒ publish byte-identical to
  today. Demonstrable by C4-verify with stubbed review leaves
  (`PDCA_LEAVES_MODE=stub`-style stubbing as the existing leaf tests do).
- **Falsifiability:** the offline driver suite on this host. RED is producible now: a
  test enabling the stage with a stub reviewer that emits one BUG finding, asserting
  publish does not reach the git steps, fails on current `main` — `publish()` goes
  straight from `_t4_passes` (`publish.py:187-192`) to branch/apply/commit/push
  (`publish.py:254-266`) with no review seam in between.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 311, 317
- **Ordering note:** 311 and 317 also edit `publish.py` (311 adds a pre-push host-CI
  gate in the same seam; 317 hooks after `publish.json` is written) — different waves.
  No build-on dependency either way.
- **Difficulty:** high
- **Scope:** the pre-publish review stage in the engine: N parallel passes via the
  existing family machinery (`codex exec --sandbox read-only` for a codex reviewer —
  reuse `leaves.run_review`'s invocation path, do not build a second model-runner),
  union+dedup, rubric-rejected-class drop, bounded BUG re-entry via the
  carry-forward + auto-iterate budget shape, and the triaged-fixpoint proceed condition.
  Config-gated, off by default. / out of scope: the rubric *key/format* itself (the
  companion issue owns it — where no rubric is configured, skip the rubric-drop step);
  ingesting post-publish external PR reviews (#316); any change to the wyrd stopgap
  (`scripts/review-branch`).
- **External dependencies:** none — the unit tests stub the review leaves; live runs use
  the reviewer family the instance already configures.
- **Test file:** template/tests/test_prepublish_review.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the seam — after `_t4_passes` at `publish.py:187-192`, before the git
  steps at `publish.py:254-266`; the reviewer invocation to reuse —
  `leaves.run_review` (driver calls it at `driver.py:89`); the bounded-loop shape —
  `autoiterate.py:50-91` (`BUDGET_FILE`, `count`, `bump`) and
  `driver._carry_forward_into_brief`.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/publish.py` — no review-stage work; commit grep `#315`
  empty. The wyrd stopgap (instance-owned T4 gate row) exists downstream only and cannot
  reach the fix-loop half — confirming the engine gap. Not fixed, not in flight.
- **Disposition hint:** new-feature

## Motivation

158 external review findings across ~79 wyrd PRs show the dominant churn is serialized
review depth after the draft PR opens. The harness stops at the draft PR and never sees
it. Paying N parallel passes up front converts serial post-publish rounds into one
bounded pre-publish loop.

## Design

See Scope. Key decisions already made by the evidence: parallel passes (union grows
sublinearly but each pass surfaces distinct findings); a *triaged* fixpoint, not reviewer
silence, as the exit condition; re-entry strictly under the existing iterate budgets so a
noisy reviewer cannot spin the loop.

## Alternatives considered

- Instance-owned gating T4 row (wyrd's stopgap): works pre-push with zero engine change,
  but a gate row cannot reach the fix loop — findings can only block, not re-enter Do.
- Raising N of the *existing* Check reviewer: Check reviews `patch.diff` against the
  brief with build-notes withheld; this stage reviews the final full diff at the publish
  boundary. Different artifact, different moment.

## Impact & compatibility

Off by default ⇒ byte-identical for every existing instance. Enabled, publish latency
grows by N review passes plus any iterate rounds — bounded by config.

## Open questions

- Dedup key for findings across passes (file+line vs normalized text) — Do proposes,
  reviewer judges.
- Whether recorded-rejected findings should land in §6/SUMMARY or a stage-local artifact
  the sign-off reads.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.
