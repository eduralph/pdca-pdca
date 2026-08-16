# Result — issue 476 / lineage-reader-doc-matches-the-reader

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `docs/07-crosscutting.md:277-282` states that the lineage reader returns `None`
  "for a `depth` that isn't a number". It does not. Verified on the target base:
  `split.read_lineage` (`template/src/pdca_harness/split.py:583-612`) returns `None` for an
  absent, unreadable, malformed, non-object or wrong-version file — and for **nothing else**:
  `{"depth": "one"}` is valid JSON of the right version, so the reader hands the record straight
  back. The unusable value is absorbed one layer down by `split._recorded_depth` (`:615-631`),
  which answers `0` for anything that is not a non-negative non-boolean `int`, so a child of
  such a parent is written at depth 1 and the parent's own record keeps `"one"` verbatim. That
  behaviour is deliberate and already pinned:
  `template/tests/test_split_lineage.py:236-251`
  (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` — the child's depth is 1,
  and the parent's record still reads `"one"`).
  This is not cosmetic. The documented-but-untrue clause was the source of the reviewer's C3/T2
  FAIL findings on this instance's issue_456 cycle: the reviewer held a correct implementation
  against the doc's claim and filed findings against code that was right. Every later cycle
  that reads this paragraph is exposed to the same false negative. Surfaced as a §10 Act
  candidate on issue_456 and routed upstream at the 2026-08-09 Act review
  (`process/act-log.md`).
- Success criterion: With the patch, `docs/07-crosscutting.md`'s lineage paragraph states
  what the code does: `split.read_lineage` abstains (`None`) on a file it cannot **parse** —
  absent, unreadable including non-UTF-8 bytes, malformed, non-object, wrong version — and a
  `depth` it cannot **compute with** is absorbed by the depth arithmetic instead (treated as
  unknown, i.e. `0`, so the child lands at depth 1), with the tolerance rationale intact. No
  sentence in the file claims a `None` the reader never returns, and no other paragraph is
  edited. The two mechanical checks the target's own CI runs on every PR stay clean on the
  patched tree: `docs/publishing/tools/lint_docs.py` (Obsidian-syntax lint) and
  `docs/publishing/tools/render_site.py --check` (site render + internal-link audit) — this
  instance runs both as the advisory `T2-docs` row **and** as the forced-gating `host-ci-docs`
  parity row, which is re-run at publish against the exact base the push builds on.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The lineage paragraph of `docs/07-crosscutting.md` (`:277-282`) — correct the
  return-contract clause so the doc describes the reader that exists, keeping the two-layer
  tolerance story (the reader abstains on what it cannot parse; the depth arithmetic absorbs a
  value it cannot compute with) and the rationale sentence that follows it. **Out of scope:**
  `split.py` — the permissive reader and `_recorded_depth` are correct and stay untouched (the
  issue routes this to the doc deliberately); every other paragraph of `07-crosscutting.md`,
  including the merge-mode section 462 was kept out of; `template/docs/`; the split lineage
  suites, which already pin the behaviour; adding a docs-versus-behaviour consistency test (the
  behaviour is pinned at `test_split_lineage.py:236-251`; a prose-matching test would be new
  machinery this slice does not need).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — patch ships no test (changed: docs/07-crosscutting.md)
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review of the docs-only correction aligning the split-lineage reader contract with its actual handling of unusable `depth` values.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required reader-versus-arithmetic contract and one-paragraph scope are decidable against `template/src/pdca_harness/split.py:583` and `template/src/pdca_harness/split.py:615`. |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, the base prose claimed a non-numeric depth returns `None` while an executable probe returned the parsed record, matching `template/src/pdca_harness/split.py:612` and the regression at `template/tests/test_split_lineage.py:236`. |
| C3 Change | FAIL | The required abstention contract includes valid-JSON non-object payloads, but the patched enumeration omits that case even though the reader rejects it, leaving the contract incomplete at `docs/07-crosscutting.md:278` versus `template/src/pdca_harness/split.py:610`. |
| C4 Verification (red→green) | NEEDS-HUMAN | The maintainer must decide whether the reproduced prose contradiction, corrected semantic probe, and existing regression are sufficient for this docs-only change — the configured verifier produced no mechanical bundle red→green and exited 77 (`gate-logs/C4-verify.log:7`; `template/tests/test_split_lineage.py:247`). |
| C5 Causal adequacy | PASS | Correcting the normative sentence removes the source of false review findings directly, with no capability probe or runtime guard introduced at `docs/07-crosscutting.md:278`. |
| T1 Structure | PASS | The change remains confined to the lineage paragraph and preserves its surrounding split and transaction narrative at `docs/07-crosscutting.md:270`. |
| T2 Shape | PASS | Independently rerun docs lint and site/link rendering passed, corroborating both frozen docs checks (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | All 23 lineage tests passed independently, including the non-numeric-depth behavior at `template/tests/test_split_lineage.py:236`, and the frozen full runtime suite also passed (`gate-logs/T3-suite.log:7`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred row says their substantive audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Affected-path commit history plus all closed/merged PR file lists found only merged predecessors (latest #504), no closed-unmerged attempt, and the current open-PR query was empty, so no prior-art collision requires judgment. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The maintainer must decide whether the reader-facing explanation is complete and clear after resolving C3 — lint, rendering, and runtime tests cannot judge documentation fitness at `docs/07-crosscutting.md:278`. |

### Advisory — code-review

# Check — advisory code review (issue #476, lineage-reader-doc-matches-the-reader)

Docs-only patch (`docs/07-crosscutting.md`, one hunk, ~5 lines). No production code
touched (`split.py` is out of scope and untouched, per brief). Both lenses below,
scoped strictly to this diff.

## Correctness (of the claim the patch makes)

Cross-checked the corrected paragraph against the actual implementation:

- `docs/07-crosscutting.md:282-283` ("returns `None` … for *any* way of failing to
  **parse** it") matches `read_lineage` (`target/template/src/pdca_harness/split.py:583-612`):
  the only `return None` paths are the total `except` around read/parse and the
  `isinstance`/`version` check.
- `docs/07-crosscutting.md:284-286` ("A `depth` it parses fine but can't compute with …
  is absorbed one layer down instead, by the depth arithmetic, which treats it as unknown
  (`0`) so the child lands at depth 1") matches `_recorded_depth`
  (`target/template/src/pdca_harness/split.py:615-631`) and is pinned by
  `target/template/tests/test_split_lineage.py:236-251`.
- The false clause named in the brief ("and for a `depth` that isn't a number") is gone;
  no other sentence in the paragraph or file was touched, matching the brief's scope.

This is a well-grounded, narrowly-scoped correction — no bug introduced, nothing to
reuse/simplify (no code changed, no hot path involved).

## Minor prose-precision nit

- NEEDS-HUMAN [impl] — `docs/07-crosscutting.md:284-286`: the sentence "…absorbed one
  layer down instead, by the depth arithmetic, which treats it as unknown (`0`) so the
  child lands at depth 1 **and the parent's own record is left untouched**" grammatically
  attributes *both* consequences to "the depth arithmetic … treats it as unknown (0)".
  The child-depth-1 outcome is indeed produced by `_recorded_depth` (`split.py:615-631`,
  called from `materialise`, `split.py:~625`). But the parent's record being left
  untouched is a *different* mechanism: `_merge_parent_lineage` (`split.py:642-657`)
  copies `depth` (and `parent`/`siblings`) through **verbatim** from the existing record
  without ever calling `_recorded_depth` on it — it would be left untouched regardless of
  what the depth arithmetic does. As written, a careful reader could infer a causal link
  between "depth arithmetic treats it as unknown" and "parent's record is untouched" that
  doesn't exist in the code; the two facts are correct individually but not connected the
  way the sentence implies. Given this brief exists specifically because doc precision on
  this exact reader/arithmetic split previously produced false review findings (issue
  #456), this is worth a wording pass (e.g., splitting into two independent clauses) even
  though it doesn't misstate any individual fact — a human/builder call on whether the
  ambiguity clears the bar to fix now or is accepted as close enough.

No other findings. Nothing in this diff duplicates existing logic, adds needless work, or
introduces a resource/concurrency/API-misuse risk — it's a text-only doc edit with no code
or test surface.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — The maintainer must decide whether the reproduced prose contradiction, corrected semantic probe, and existing regression are sufficient for this docs-only change — the configured verifier produced no mechanical bundle red→green and exited 77 (`gate-logs/C4-verify.log:7`; `template/tests/test_split_lineage.py:247`).
- [ ] Validation — fitness-to-purpose — The maintainer must decide whether the reader-facing explanation is complete and clear after resolving C3 — lint, rendering, and runtime tests cannot judge documentation fitness at `docs/07-crosscutting.md:278`.
- [ ] `docs/07-crosscutting.md:284-286`: the sentence "…absorbed one
- [ ] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — patch ships no test (changed: docs/07-crosscutting.md)
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- Iteration delta (if iterating): Rejected because the corrected paragraph still does not match the reader it documents — the precise failure this bundle exists to end. Three concrete changes for the rebuild: 1. The enumeration omits the NON-OBJECT case. `read_lineage` returns `None` on three grounds (`template/src/pdca_harness/split.py:606-611`): any exception during read/parse; `not isinstance(data, dict)`; and a wrong `version`. The patched sentence lists only "absent, unreadable, malformed or wrong-version file". The brief's own success criterion names "non-object" explicitly — the patch misses its stated criterion, and the omission was inherited from the pre-patch text rather than fixed. 2. The organising idea does not cover that case either. The patch says `None` comes back "for *any* way of failing to **parse** it" — but a valid-JSON non-object such as `[1,2,3]` parses fine and is rejected on SHAPE, not on parse. Reword so the framing spans both "could not parse it" and "parsed, but is not the right shape/version", otherwise adding "non-object" to the list contradicts the sentence around it. 3. Reuse the wording that is already correct: `read_lineage`'s own docstring (`split.py:586-587`) already reads "absent, unreadable, malformed JSON, a non-object payload and an unrecognised `version` all return `None`". The correct sentence exists in the file being documented — align the prose to it rather than re-deriving it. Also fix the prose-precision nit while in there: the patch attributes both consequences to the depth arithmetic ("treats it as unknown (`0`) so the child lands at depth 1 and the parent's own record is left untouched"). The parent's record surviving is a DIFFERENT mechanism — `_merge_parent_lineage` (`split.py:643-657`) copies `depth` through verbatim and never calls `_recorded_depth`; it would survive regardless of the arithmetic. Split into two independent clauses so no causal link is implied. Given this brief exists because imprecision in this exact paragraph produced false reviewer findings on issue_456, an implied-but-untrue causal link is the same class of defect being fixed. Scope is unchanged: still docs-only, still the one lineage paragraph of `docs/07-crosscutting.md`; `split.py` stays untouched and correct. C4 remaining "unverifiable" for a docs-only patch is accepted and is not a reason for this iterate.
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
