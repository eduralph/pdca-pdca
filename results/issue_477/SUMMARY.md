# Result — issue 477 / size-signal-discount-human-class-rounds

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the size backstop's rounds rule stops charging a slice for a round whose only
  recorded drivers are things no rebuild can change: an environment fault (already handled
  by #446) or a reviewer finding on a gate the harness deliberately deferred. Any
  builder-actionable or ambiguous evidence still counts the round, so the backstop can only
  warn less on noise, never go quiet on real churn.
- Success criterion: all hold in `template/tests/test_size_signal.py` (appended to the
  #446 class `RoundsAreAttributedToTheSliceNotTheEnvironment`, `:540`), run by the C4 gate,
  through `size_signal.iteration_rounds`:
  (1) **Deferred-gate finding is not slice churn.** An archive whose gating rows are all
  `pass` except a `deferred` row for element T4, and whose primary review
  (`check-review.md`) raises NEEDS-HUMAN only on the T4 row and the standing Validation row,
  is NOT charged (the two-round bundle reads `(1, 0)`, not `(2, 0)`). The match is by
  element: the §6 item text's leading element id, read with `assemble._ELEMENT_RE`
  (`assemble.py:54`, `^(C[1-5]|T[1-5]|V)\b` on `NeedsHumanItem.text`), equals the
  `element` of an archived gate row whose `result` is `deferred`. Fixture rows use the
  Item-cell form the reviewer writes, starting with the id (`| T4 Contribution … |
  NEEDS-HUMAN | … |`); a NEEDS-HUMAN row whose Item cell has no leading id keeps the round
  charged (tested). The deferred-element set is read from ALL archived gate rows, gating or
  not (a withheld row is withheld either way); the `fail` / `unverifiable` / `flaky` checks
  stay on gating rows only, as today (`size_signal.py:202`). Tested: a non-gating
  `deferred` T4 row still discounts.
  (2) **Still counted — every one of these keeps the round charged:** a plain gating
  `fail`; a review NEEDS-HUMAN on any element whose gate row is not `deferred` (e.g. T3,
  C5, T5); a FAIL verdict cell; a review placeholder or missing/unreadable review; missing
  or malformed `check-gates.json`; a review whose ONLY NEEDS-HUMAN item is the standing
  Validation row with no environment row and no deferred-gate finding (nothing recorded
  explains the round, so it counts — V is a constant, not a driver; see Open questions, this
  is a choice the human must confirm); and any archived advisory artifact
  (`check-advisory-*.md`) that carries an IMPL-kind item (as classified by
  `assemble._items_from_artifact`, so it follows the tag contract whatever #408 lands) or is
  a leaf-status placeholder. A plain `- NEEDS-HUMAN — …` advisory bullet (HUMAN kind) does
  NOT charge the round (tested on both the new path and a #446 round).
  (3) **One rule, applied to #446 rounds too.** The advisory check in (2) applies to
  environment-attributed rounds as well: an archive with a solely-`unverifiable` gating red
  and a clean review, but an advisory `- NEEDS-HUMAN [impl] — …` finding, is now CHARGED;
  the same archive with only a plain `- NEEDS-HUMAN — …` advisory bullet is still
  discounted (so #446 keeps working on instances that configure advisories).
  This is a deliberate tightening in the safe direction (today it is discounted because
  `_review_drove_the_iterate`, `size_signal.py:205`, reads only `check-review.md`).
  (4) Every existing test in `test_size_signal.py` passes unchanged, including the #446
  class (`:540-700`) and `test_the_calibrator_uses_THIS_definition` (`:524`) — the
  calibrator keeps sharing `iteration_rounds`.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the round-attribution rule in `size_signal.py` (`_environment_attributed` /
  `_review_drove_the_iterate` or their replacement: one function that decides whether an
  archived round's recorded drivers were all non-slice), its module/function docstrings,
  and the `[driver.size_signal]` comment in `template/pdca.toml.jinja` if it describes what
  is discounted. / out of scope: how `assemble` classifies a NEEDS-HUMAN on a deferred gate
  cell for auto-iterate (today IMPL via `_ELEMENT_RE`; see Open questions); treating a T3
  NEEDS-HUMAN about a missing host tool as environmental (not decidable from the archive —
  it keeps counting); threshold defaults; the calibrator script (it shares the function).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
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

Review issue #477: discount rounds driven solely by deferred-gate review findings while keeping actionable, conflicting, or malformed evidence charged to the size backstop.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The accounting boundary and carry-forward corrections are explicit and testable; Validation-only rounds remain charged by the recorded human decision (`brief.md:163`; `target/template/tests/test_size_signal.py:815`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the added tests produced 12 assertion failures, including deferred-round overcounting and advisory-driven undercounting; no import failure substituted for reproduction (`reviewer-red.log:9`, `reviewer-red.log:208`, `reviewer-red.log:262`). |
| C3 Change | PASS | The reviewed cases preserve the backstop when gating results are malformed or a deferred element has a live sibling; both carry-forward defects have executable coverage (`target/template/src/pdca_harness/size_signal.py:217`, `target/template/src/pdca_harness/size_signal.py:254`; `target/template/tests/test_size_signal.py:849`, `target/template/tests/test_size_signal.py:880`). |
| C4 Verification (red→green) | PASS | Restoring the production patch made the same 70-test suite pass, independently reproducing the frozen gate's transition; the target diff was subsequently confirmed byte-for-byte equal to the supplied patch (`reviewer-red.log:262`; `reviewer-green.log:9`; `gate-logs/C4-verify.log:1`). |
| C5 Causal adequacy | PASS | The accounting tests exercise production `iteration_rounds` and the resulting warning threshold; archive validation addresses the specified attribution error and adds no optional-capability probe or load-time workaround (`target/template/tests/test_size_signal.py:744`, `target/template/tests/test_size_signal.py:751`). |
| T1 Structure | PASS | Attribution continues to share the canonical review parser and calibrator definition, avoiding divergent interpretations of archived findings or round counts (`target/template/src/pdca_harness/size_signal.py:332`, `target/template/src/pdca_harness/size_signal.py:370`; `target/template/scripts/size-calibrate:88`). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and `git diff --check` succeeded; the underlying docs commands match host CI, and both frozen T2 logs also show clean audits (`target/.github/workflows/docs-check.yml:32`; `gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver run passed 2,149 tests with two skips; frozen evidence additionally shows 24 root tests passing, including real render/update cases, although this review interpreter cannot import copier (`reviewer-suite.log:1683`; `gate-logs/T3-suite.log:36`; `reviewer-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the gate explicitly defers their substantive audit to the required publish-time rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for both affected paths — the brief records a production-file search, but the supplied target has only a synthetic base commit and no remote, so the test-file history and rejected-work coverage cannot be independently established (`brief.md:89`; `reviewer-history.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Judge whether the demonstrated accounting behavior meets the operational need — tests establish the defensive rule, but the brief's measured cohort has zero eligible deferred-finding rounds out of 39 and cannot demonstrate fewer unnecessary holds (`brief.md:112`; `target/template/tests/test_size_signal.py:751`). |

No grounded patch defect found. Source citations above resolve in the supplied `$PDCA_TARGET` (`target/`); brief and log citations identify the supplied evidence or independent reviewer output. The target was current and applicable, and the original production and test modifications were restored after the red leg.

Independent reproduction used `git stash push -- template/src/pdca_harness/size_signal.py`, then `cd template && PYTHONPATH=src python3 -m unittest tests.test_size_signal`, followed by `git stash pop` and the same test command. Both runs used the appended tests. All temporary test artifacts were directed into this review sandbox. The full driver rerun used `PYTHONPATH=src python3 -m unittest discover -s tests`.

The instance-scoped gate wrappers are not part of this target. Their frozen logs were read rather than treating their absence as a defect. The C5 scanner only reports that no new test file was added (`gate-logs/C5-prod-path.log:10`); the C5 verdict instead rests on reading the appended tests and independently running their production path. Local root-suite exit 77 is a reviewer-host limitation, not a patch failure or an undischarged project dependency: the frozen T3 log explicitly shows the copier-dependent render/update cases executing successfully and the root suite passing (`gate-logs/T3-suite.log:36`, `gate-logs/T3-suite.log:54`).

Prior-art investigation actually ran the affected-path git log and remote listing; `reviewer-history.log` records the single synthetic commit and empty remote list. No other checkout was consulted. The supplied target contains only the generic integration template, whose project-specific human-only list remains TODO (`target/template/docs/INTEGRATION.md.jinja:80`); no additional project-specific items could be derived from it. The prior human decision to retain the design and charge Validation-only rounds is respected.

### Advisory — code-review

# Advisory code review — issue 477 (size-signal: discount deferred-gate rounds)

No correctness bugs found in this diff. I traced the new round rule in
`_environment_attributed` against the gate writer (`gates.py:813-830`, `:866-887`) and the
review parser (`assemble.py:248-304`, `:626`), and re-ran `tests.test_size_signal` and
`tests.test_attempt_harvest` on the patched target: 94 tests, all pass. The gate logs
agree: C4 is red without the fix and green with it, and T3 (2149 tests) is OK. Both
carry-forward items are fixed and tested: malformed `result` values count the round, and a
deferred row no longer covers for a failing row of the same element. The optional `[impl]`
item is fixed too. The notes below are small and none of them blocks.

- `template/src/pdca_harness/size_signal.py:272` — `_deferred_elements` treats only a
  non-string `element` as "could be anyone's". An empty string `""` (what `gates.py:514`
  and `:606` write for a check with no `tier`) goes into `live` as the element `""`, so a
  failing row like that does not stop the T4 deferral. This can't happen today:
  `_assemble_matrix` (`gates.py:873-878`) drops element-less rows before writing
  `check-gates.json`. It only matters for a hand-edited or future archive. If you want it
  closed, change the check to `if not isinstance(element, str) or not element:` and the
  fail-safe also covers that case.
- `template/src/pdca_harness/size_signal.py:330` — the `[impl]` check runs
  `assemble._needs_human(text)` a second time, because `_items_from_artifact` on the next
  line runs it again internally. That costs nothing at these input sizes, and the docstring
  explains why the raw text is needed (classifying strips the tag). It does create a second
  reader of `assemble` private names (`_IMPL_MARKER_RE`, `_needs_human`). If #408 changes
  how the tag is written, this line has to change with it. A small public helper in
  `assemble` (for example "items with their raw-tag flag") would keep it to one parser,
  which is the rule the docstring itself cites.
- `template/src/pdca_harness/size_signal.py:336` — `_review_drove_the_iterate` is no longer
  called by production code. It stays only because `tests/test_attempt_harvest.py:593` and
  `:684` call it. The docstring says this, as the carry-forward asked. A simpler option is to
  point those two tests at `_review_findings` (asserting `== []` / `is None`) and delete the
  wrapper. Optional.
- `template/src/pdca_harness/size_signal.py:370` — an advisory bullet that is not tagged
  but starts with a gate element id (for example `- NEEDS-HUMAN — T4 PR body lacks the
  tracker id`) is classified IMPL by `assemble._classify_finding` (`assemble.py:274-276`),
  so it charges the round. The same text in the primary review, on a deferred T4, is
  discounted. The brief asks for exactly this ("IMPL-kind as classified by
  `_items_from_artifact`"), and it errs toward counting, so this is a note, not a defect. No
  test covers this case.

Nothing here needs a human decision. The design questions about scope (the #446
tightening, Validation-only rounds) are in the brief's Open questions, and they belong to
the reviewer leaf, not this lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for both affected paths — the brief records a production-file search, but the supplied target has only a synthetic base commit and no remote, so the test-file history and rejected-work coverage cannot be independently established (`brief.md:89`; `reviewer-history.log:1`).
- [x] Validation — fitness-to-purpose — Judge whether the demonstrated accounting behavior meets the operational need — tests establish the defensive rule, but the brief's measured cohort has zero eligible deferred-finding rounds out of 39 and cannot demonstrate fewer unnecessary holds (`brief.md:112`; `target/template/tests/test_size_signal.py:751`).
- [x] **The brief keeps counting the exact class the issue asked to discount first.** The issue says: "discount a round whose only recorded drivers are findings of classes that no rebuild can change — **at minimum the always-human validation row**, and rows whose result is `deferred`". The brief does the opposite in clause (2): "a review whose ONLY NEEDS-HUMAN item is the standing Validation row … counts". Its reason ("V is a constant, not a driver") is defensible. But it means the brief implements the second half of the issue's suggestion and turns down the first half without listing that as an Alternative or an Open question. The human should decide this. It should not happen silently inside a success-criterion bullet.
- [x] **After 07766ed the new discount path may almost never fire, so the fix may not reach the reported symptom.** The Motivation admits the four motivating archives (453/456/457/468) will not be re-classified. The reviewer prompt now says, for a `deferred` row: "Record it `N/A` … and do NOT escalate it to NEEDS-HUMAN" (`leaves.py:2735-2739`). So the new path only fires when the reviewer disobeys its prompt. Once T4 findings are gone, the noise left in those rounds is V (still counted, see above) and T3/missing `copier` (still counted, by design). The brief never shows that any real round from now on would be discounted. The success criterion is a synthetic fixture only, so it can go green while the backstop keeps firing at rounds=2 on pdca-pdca. Consider one of these: state the expected real-world effect (e.g. "the calibrator over the post-07766ed corpus changes by N"); re-scope to V-only rounds; or say plainly that this is a defensive rule for disobedient reviewers.
- [x] **Clause (3)/(d) is a second behavioural change, and it may cancel both discounts in practice.** Reading `check-advisory-*.md` and charging any round where an advisory holds a NEEDS-HUMAN changes what #446 discounts. It is not needed for the deferred-gate fix; the brief itself lists it as an Open question. The advisory prompts tell leaves to use plain `- NEEDS-HUMAN — ` bullets for anything a human must adjudicate (`.claude/agents/adversary.md:66`, `code-review.md:47`, `pdca.toml.jinja:699`). On an instance with advisories configured, most rounds will have at least one such bullet. Rule (d) would then block the new discount and also turn off #446 in practice. Clause (4) ("every existing test passes unchanged") can't catch that, because the #446 fixtures have no advisory files. Two options: split (d)-for-#446 into its own slice; or narrow (d) to `[impl]`-tagged advisory items plus placeholders (the brief's own Alternatives bullet names only `[impl]` as the risk) and require a test for an advisory containing only a plain `- NEEDS-HUMAN —` bullet.
- [x] **The deferred-row lookup only sees gating rows, so on instances where the T4 check is non-gating a deferred T4 row is silently invisible.** `_archived_gating_rows` filters to `r.get("gating")` (`size_signal.py:202`), and `row["element"]` comes from the check's `tier` (`gates.py:506,606`). The brief just asserts "T4-contribution is gating on this project" (Citations). The fail-safe direction holds (the round is still counted), so this is not unsafe. But the success criterion should say whether the deferred lookup reads all rows or only gating rows, and pin that choice with a test. Otherwise the builder has to guess.
- [x] **Minor, for traceability: the element match depends on `_ELEMENT_RE` matching the §6 item text, not on a structured field.** `NeedsHumanItem` holds only `(text, kind)` (`assemble.py:39-43`). Matching by element means running `_ELEMENT_RE` (`assemble.py:54`) on `it.text`. That works only when the reviewer's Item cell starts with the id (e.g. `T4 — …`). Clause (1) should pin the fixture row format it relies on, and also a case where the Item cell has no id prefix, which must stay charged.

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
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
