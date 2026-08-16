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

Task under review: correct the lineage-reader documentation so its abstention and non-numeric-depth behavior match the existing reader, arithmetic, and merge paths.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required contract is unambiguous and internally consistent: reader rejection, depth fallback, and verbatim merge behavior are distinct decisions grounded at `template/src/pdca_harness/split.py:606`, `template/src/pdca_harness/split.py:628`, and `template/src/pdca_harness/split.py:652`. |
| C2 Reproduction (red pre-fix) | PASS | With the patch stashed, `docs/07-crosscutting.md:278` falsely included non-numeric `depth` among `None` outcomes, while the unchanged regression at `template/tests/test_split_lineage.py:236` passed and demonstrated record return plus depth-1 fallback. |
| C3 Change | PASS | The corrected paragraph now covers read/parse, object shape, version, arithmetic fallback, and separate merge preservation without changing any other file (`docs/07-crosscutting.md:278`). |
| C4 Verification (red→green) | NEEDS-HUMAN | The human must decide whether the semantic prose red→green accurately states the runtime contract — this docs-only patch has no executable failing leg, and C4 correctly reported `PDCA-UNVERIFIABLE` while the relevant lineage tests passed (`docs/07-crosscutting.md:278`). |
| C5 Causal adequacy | PASS | Correcting the normative statement removes the source of false implementation findings directly; no capability probe or runtime guard masks the cause (`docs/07-crosscutting.md:278`). |
| T1 Structure | PASS | Keeping the correction in the existing lineage paragraph preserves the document hierarchy and the intended separation from production code (`docs/07-crosscutting.md:277`). |
| T2 Shape | PASS | Independent patched-tree reruns of the Obsidian lint and site-render/internal-link audit were clean, so the expanded prose retains publishable document shape (`docs/07-crosscutting.md:278`). |
| T3 Runtime | PASS | The 23-test lineage module passed before and after reapplication, including non-object rejection and non-numeric-depth behavior, and the frozen full-suite log reports both suites clean (`template/tests/test_split_lineage.py:236`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted during Check; the deferred gate records that their substantive audit is mandatory at publish. |
| T5 Judgment | PASS | Affected-path history and all PR states were queried: prior edits were merged and no open or closed-unmerged attempt touched this file, while the final wording agrees with the implementation (`docs/07-crosscutting.md:278`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether this normative wording is sufficiently clear to prevent future false review findings — automated checks establish syntax, links, and existing behavior, not reader interpretation (`docs/07-crosscutting.md:278`). |

### Advisory — code-review

# Advisory code review — issue #476 (lineage-reader-doc-matches-the-reader)

## Scope of this diff
Single-file, prose-only change: `docs/07-crosscutting.md:277-289` (12 insertions, 4
deletions). No production code, no test file, no other doc paragraph touched — matches
`brief.md`'s declared scope exactly.

## Correctness (fact-checked against target source, not just against the brief)

Verified every factual claim in the rewritten paragraph directly against
`template/src/pdca_harness/split.py` on `$PDCA_TARGET`:

- "absent, unreadable, malformed JSON, a non-object payload and an unrecognised `version`
  all return `None`" — matches `read_lineage`'s `try/except Exception: return None`
  (`split.py:606-609`) plus `if not isinstance(data, dict) or data.get("version") !=
  LINEAGE_VERSION: return None` (`split.py:610-611`). All five failure modes are present
  and none are invented.
- "The first three cover *any* way of failing to parse the file at all... the last two
  parse cleanly and are turned away on shape and version" — correctly distinguishes the
  blanket `except Exception` (parse-time) from the `isinstance`/`version` checks
  (post-parse, shape/version). This is the exact distinction the iteration-1 sign-off
  demanded (carry-forward point 2) and it is drawn correctly.
- "the depth arithmetic one layer down absorbs the value it can't compute with, counting
  it as unknown (`0`) so the child lands at depth 1" — matches `_recorded_depth`
  (`split.py:615-631`): non-int, bool, or negative `depth` values fall through to `return
  0`, and the caller adds 1 for the child.
- "The parent's own record keeps `"one"` verbatim by a separate route: the merge copies an
  existing `depth` through rather than recomputing it" — matches
  `_merge_parent_lineage` (`split.py:643-657`), which calls `read_lineage(parent)` and
  copies `existing["depth"]` through the `for key in ("parent", "siblings", "depth")` loop
  without ever calling `_recorded_depth`. This correctly resolves the false causal link
  the iteration-1 sign-off flagged (carry-forward point 4: parent-record survival and
  child-depth fallback are stated as two independent mechanisms, not one).
- Cross-checked against the pinned test,
  `template/tests/test_split_lineage.py:236-251`
  (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number`): child depth is
  asserted `== 1`, parent's `depth` is asserted `== "one"` verbatim. The corrected prose
  states exactly this outcome and no more.

No factual claim in the diff is unsupported by the code it describes, and no residual
gap from the iteration-1 rejection (missing "non-object" enumeration, the parse/shape
conflation, the implied causal link) is still present.

## Gate evidence sanity-check
- `C4-verify` → exit 77 `PDCA-UNVERIFIABLE` is the classification `run-verify.sh` gives
  any docs-only patch with no test; consistent with the brief's declared Falsifiability
  and not a false red.
- `T2-docs` and `host-ci-docs` both pass (`lint_docs: OK`, `render_site` link audit OK),
  confirming the rewritten paragraph doesn't break Obsidian syntax or internal links —
  the two mechanical checks this class of change can actually fail.

## Reuse / simplification / efficiency
Not applicable in the usual sense — this is a one-file prose edit with no code, no new
helper, and no hot path. The prose itself reuses the wording already present in
`read_lineage`'s own docstring (`split.py:586-587`, "absent, unreadable, malformed JSON,
a non-object payload and an unrecognised `version` all return `None`") rather than
re-deriving new phrasing, which is exactly what the iteration-1 sign-off asked for
(carry-forward point 3). No duplicated logic, no simpler equivalent, nothing to flag.

## Findings
None. The diff is clean on both lenses: no correctness bug is introduced (every claim
in the corrected paragraph checks out against the source it documents and against the
pinned test), and there is no reuse/simplification/efficiency opportunity being missed
(the patch already reuses the existing docstring wording rather than duplicating it).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — The human must decide whether the semantic prose red→green accurately states the runtime contract — this docs-only patch has no executable failing leg, and C4 correctly reported `PDCA-UNVERIFIABLE` while the relevant lineage tests passed (`docs/07-crosscutting.md:278`).
- [x] Validation — fitness-to-purpose — The human must decide whether this normative wording is sufficiently clear to prevent future false review findings — automated checks establish syntax, links, and existing behavior, not reader interpretation (`docs/07-crosscutting.md:278`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — patch ships no test (changed: docs/07-crosscutting.md)
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
