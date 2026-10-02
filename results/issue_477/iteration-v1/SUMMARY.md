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

Review issue #477: discount iteration rounds driven only by deferred-gate findings while retaining rounds with actionable or ambiguous evidence, including advisory implementation findings.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The discount and conservative counting boundary are testable through the existing API; Validation-only rounds remain charged as already decided in Plan (target/template/tests/test_size_signal.py:738; target/template/tests/test_size_signal.py:809). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes leaves five behavioral failures among 65 tests, including deferred attribution and advisory-driven environment rounds (reviewer-red.log:9; target/template/tests/test_size_signal.py:822). |
| C3 Change | FAIL | Malformed gating-row results can now suppress the size warning: missing, null, or unknown results beside a deferred T4 finding yield one charged round instead of two; evidence must be validated before granting the discount (target/template/src/pdca_harness/size_signal.py:202; reviewer-malformed.log:1). |
| C4 Verification (red→green) | PASS | The asserted regression suite independently changes from five failures to 65 passing tests after stash restoration; this verifies the supplied cases, which omit the malformed-row counterexample in C3 (reviewer-green.log:9; target/template/tests/test_size_signal.py:796). |
| C5 Causal adequacy | PASS | For the specified accounting problem, the shared attribution rule directly changes the measured quantity and preserves actionable advisory drivers; no capability probe or load-time symptom guard is introduced (target/template/src/pdca_harness/size_signal.py:151; target/template/src/pdca_harness/size_signal.py:216). |
| T1 Structure | PASS | Attribution retains the shared archive reader and canonical finding parser, so calibration and runtime do not acquire separate definitions (target/template/src/pdca_harness/size_signal.py:148; target/template/src/pdca_harness/size_signal.py:279; target/template/src/pdca_harness/size_signal.py:311). |
| T2 Shape | PASS | Independently rerun docs lint and 22-page site rendering/link audit pass, as does git diff --check; the frozen host-parity log also records both checks passing (gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent offline suite: 2,144 tests, two skips; frozen evidence additionally records 24 root tests passing, including actual Copier render/update cases; local root rerun exits 77 because this interpreter lacks Copier (reviewer-suite.log:1683; gate-logs/T3-suite.log:40; reviewer-root-suite.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred row explicitly owes its substantive audit to publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm the policy of charging advisory implementation findings on previously discounted environment rounds, and settle affected-file prior art against merged and closed/rejected work; the disposable target contains only one synthetic base commit and no remotes, so historical equivalence cannot be independently settled here (target/template/tests/test_size_signal.py:822; brief.md:89; brief.md:165). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the defensive discount and tighter advisory accounting justify changing the churn metric; the brief reports zero matching deferred-finding rounds among 39 recent eligible archives, so passing fixtures alone do not establish practical benefit (brief.md:112; target/template/src/pdca_harness/size_signal.py:188). |

Finding — P2: preserve the fail-safe for malformed gate rows. `_archived_gate_rows` checks that each row is a dictionary but does not validate its result (`target/template/src/pdca_harness/size_signal.py:232`). The new deferred path only rejects the literal `fail`, so a gating C4 row with a missing result, `null`, or an unknown string is ignored while a T4 finding supplies the discount. These are syntactically valid JSON records whose gate verdict is unavailable; they cannot establish that every driver was non-slice. Before this patch all three examples remain charged. After it all three shrink the two-round bundle from `(2, 0)` to `(1, 0)`, crossing the default warning threshold. Validate the archived gate verdicts before discounting and cover malformed row contents as well as malformed JSON. This concerns corrupted/invalid archive records, not ordinary gate output.

The independent probe is saved in `reviewer-malformed.py`; `reviewer-malformed.log:1` records the same inputs against pre-fix and patched production. From this review directory, rerun the patched leg with:

```bash
TMPDIR="$PWD/reviewer-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src:$PWD/target/template" python3 reviewer-malformed.py
```

Evidence limits: the production file was stashed and restored for both comparisons, and the complete tracked diff was verified identical afterward. No implementation edits were made. The C5 scanner's frozen log only says that no new test file was added; it does not itself prove production coverage. The independent executions above call the actual production API through the appended tests. The Copier limitation is local to this reviewer: the frozen T3 log records the actual render/update cases running successfully, so it is not an undischarged patch dependency or a verification failure. The brief declares no external dependencies.

Prior art: the brief records a path-based merged-history check and no closed-unmerged work for `template/src/pdca_harness/size_signal.py`; it provides no equivalent frozen history/search output for the changed test file. An independent path-filtered log for both affected files yields only synthetic base commit `a112791`, and `git remote -v` is empty. T5 therefore leaves the historical comparison to sign-off rather than claiming upstream absence. The only supplied INTEGRATION §4 is the unrendered template (`target/template/docs/INTEGRATION.md.jinja:81`), whose project-specific human-only list is TODO; it supplies no additional instantiated requirements.

The review is advisory. C3 identifies a reproducible patch defect; C4 reports the narrower supplied-suite result without treating that result as proof of the entire fail-safe promise.

### Advisory — code-review

# Advisory code review — issue 477 (size-signal: discount deferred-gate rounds)

Lens: bugs the patch introduces, plus reuse and simplification. Line numbers are from
the patched target tree (`target/template/...`).

The gate evidence holds up. `gate-logs/C4-verify.log` shows the suite at 65 tests, OK
with the fix and 5 failures without it. All the #446 tests and
`test_the_calibrator_uses_THIS_definition` still pass. The patch reuses the shared
parser as the brief asks: review and advisory findings both go through
`assemble._items_from_artifact`, and the element match uses `assemble._ELEMENT_RE`. Every
fail-safe path still returns False, so the round still counts. I found no resource,
ordering or exception-handling bugs.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/size_signal.py:204-210`: the deferred set is
  keyed by **element** only, and one element can have more than one gate row. T2 already
  has two on this project (`T2-docs` and `host-ci-docs`). Suppose one row of an element is
  `deferred` and a sibling row of the same element is a **non-gating** `fail`. The
  reviewer flags that failing sibling. The finding's leading id matches the deferred
  element, so the round is discounted, even though the finding is about a live, failing
  check. Check (a) only catches gating fails. This follows the brief as written ("equals
  the `element` of an archived gate row whose `result` is `deferred`"), so it is a scope
  choice, not a builder slip. A tighter rule would treat an element as deferred only if
  none of its rows is `fail` or `unverifiable`. No test covers an element whose rows
  disagree. On T4 today (one row) this cannot happen.
- `template/src/pdca_harness/size_signal.py:210` together with `:279`: on the primary
  review the patch ignores `kind` and matches by element only. A primary-review bullet
  `- NEEDS-HUMAN [impl] — T4 …` has its `[impl]` marker removed by
  `assemble._classify_finding` (`assemble.py:269-271`). After that, the text starts with
  `T4`, so the round is discounted, even though the reviewer explicitly tagged the item as
  something a rebuild can fix. The advisory path does the opposite (`:311` charges on
  IMPL). This is low stakes: reviewer table rows on gate elements already classify as
  IMPL without a marker, so `kind` cannot separate the two cases here, and the brief puts
  classification out of scope. I am noting it, not asking for a change.
- `template/src/pdca_harness/size_signal.py:283-288`: `_review_drove_the_iterate` no longer
  has a production caller. Only `tests/test_attempt_harvest.py:593` and `:684` use it. As
  a thin wrapper over `_review_findings` it is harmless, but it is now test-only API.
  Either say so in its docstring, or point those two tests at `_review_findings` and
  delete the wrapper. This is a cleanup, not a defect.
- `template/src/pdca_harness/size_signal.py:238-246`: `_element_of` re-imports `assemble`
  on every call (once per finding). That is cheap, since it hits the module cache after the
  first time. Moving the `_ELEMENT_RE` match inline, inside `_review_findings` or next to
  line 210, would also be fine. A minor style point.

Apart from the element-keying scope question above, the diff is clean on both lenses.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the policy of charging advisory implementation findings on previously discounted environment rounds, and settle affected-file prior art against merged and closed/rejected work; the disposable target contains only one synthetic base commit and no remotes, so historical equivalence cannot be independently settled here (target/template/tests/test_size_signal.py:822; brief.md:89; brief.md:165).
- [ ] Validation — fitness-to-purpose — Decide whether the defensive discount and tighter advisory accounting justify changing the churn metric; the brief reports zero matching deferred-finding rounds among 39 recent eligible archives, so passing fixtures alone do not establish practical benefit (brief.md:112; target/template/src/pdca_harness/size_signal.py:188).
- [ ] `template/src/pdca_harness/size_signal.py:204-210`: the deferred set is keyed by **element** only, and one element can have more than one gate row. T2 already has two on this project (`T2-docs` and `host-ci-docs`). Suppose one row of an element is `deferred` and a sibling row of the same element is a **non-gating** `fail`. The reviewer flags that failing sibling. The finding's leading id matches the deferred element, so the round is discounted, even though the finding is about a live, failing check. Check (a) only catches gating fails. This follows the brief as written ("equals the `element` of an archived gate row whose `result` is `deferred`"), so it is a scope choice, not a builder slip. A tighter rule would treat an element as deferred only if none of its rows is `fail` or `unverifiable`. No test covers an element whose rows disagree. On T4 today (one row) this cannot happen.
- [ ] **The brief keeps counting the exact class the issue asked to discount first.** The issue says: "discount a round whose only recorded drivers are findings of classes that no rebuild can change — **at minimum the always-human validation row**, and rows whose result is `deferred`". The brief does the opposite in clause (2): "a review whose ONLY NEEDS-HUMAN item is the standing Validation row … counts". Its reason ("V is a constant, not a driver") is defensible. But it means the brief implements the second half of the issue's suggestion and turns down the first half without listing that as an Alternative or an Open question. The human should decide this. It should not happen silently inside a success-criterion bullet.
- [ ] **After 07766ed the new discount path may almost never fire, so the fix may not reach the reported symptom.** The Motivation admits the four motivating archives (453/456/457/468) will not be re-classified. The reviewer prompt now says, for a `deferred` row: "Record it `N/A` … and do NOT escalate it to NEEDS-HUMAN" (`leaves.py:2735-2739`). So the new path only fires when the reviewer disobeys its prompt. Once T4 findings are gone, the noise left in those rounds is V (still counted, see above) and T3/missing `copier` (still counted, by design). The brief never shows that any real round from now on would be discounted. The success criterion is a synthetic fixture only, so it can go green while the backstop keeps firing at rounds=2 on pdca-pdca. Consider one of these: state the expected real-world effect (e.g. "the calibrator over the post-07766ed corpus changes by N"); re-scope to V-only rounds; or say plainly that this is a defensive rule for disobedient reviewers.
- [ ] **Clause (3)/(d) is a second behavioural change, and it may cancel both discounts in practice.** Reading `check-advisory-*.md` and charging any round where an advisory holds a NEEDS-HUMAN changes what #446 discounts. It is not needed for the deferred-gate fix; the brief itself lists it as an Open question. The advisory prompts tell leaves to use plain `- NEEDS-HUMAN — ` bullets for anything a human must adjudicate (`.claude/agents/adversary.md:66`, `code-review.md:47`, `pdca.toml.jinja:699`). On an instance with advisories configured, most rounds will have at least one such bullet. Rule (d) would then block the new discount and also turn off #446 in practice. Clause (4) ("every existing test passes unchanged") can't catch that, because the #446 fixtures have no advisory files. Two options: split (d)-for-#446 into its own slice; or narrow (d) to `[impl]`-tagged advisory items plus placeholders (the brief's own Alternatives bullet names only `[impl]` as the risk) and require a test for an advisory containing only a plain `- NEEDS-HUMAN —` bullet.
- [ ] **The deferred-row lookup only sees gating rows, so on instances where the T4 check is non-gating a deferred T4 row is silently invisible.** `_archived_gating_rows` filters to `r.get("gating")` (`size_signal.py:202`), and `row["element"]` comes from the check's `tier` (`gates.py:506,606`). The brief just asserts "T4-contribution is gating on this project" (Citations). The fail-safe direction holds (the round is still counted), so this is not unsafe. But the success criterion should say whether the deferred lookup reads all rows or only gating rows, and pin that choice with a test. Otherwise the builder has to guess.
- [ ] **Minor, for traceability: the element match depends on `_ELEMENT_RE` matching the §6 item text, not on a structured field.** `NeedsHumanItem` holds only `(text, kind)` (`assemble.py:39-43`). Matching by element means running `_ELEMENT_RE` (`assemble.py:54`) on `it.text`. That works only when the reviewer's Item cell starts with the id (e.g. `T4 — …`). Clause (1) should pin the fixture row format it relies on, and also a case where the Item cell has no id prefix, which must stay charged.

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
- Iteration delta (if iterating): Keep the design; fix the implementation so it honours its own fail-safe ("anything missing, unreadable or malformed counts the round"). These cases are most likely on a new machine where a dependency has not been captured yet, so gate records can come out incomplete or odd — exactly when the backstop must NOT go quiet. 1. Malformed gate-row results (reviewer C3 FAIL): `_environment_attributed` only rejects the literal `fail`, so a gating row whose `result` is missing, `null` or an unknown string is ignored, and a deferred-T4 finding then discounts the round (2,0) → (1,0). Validate every gating row's `result` against the known set (`pass` / `deferred` / `unverifiable`, or `fail` with truthy `flaky`); anything else counts the round. Add tests for missing, null and unknown-string results beside a deferred T4 finding. 2. Element keyed too loosely (code-review §6 item, `size_signal.py:204-210`): an element counts as deferred only if NONE of its rows (gating or not) is `fail` / `unverifiable` / malformed — a deferred row must not shelter a live failing sibling of the same element (e.g. T2-docs vs host-ci-docs). Add a test for an element whose rows disagree. Optional, low stakes: a primary-review `- NEEDS-HUMAN [impl] — T4 …` bullet should keep the round charged, as the advisory path does; `_review_drove_the_iterate` is now test-only — document or remove it.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
