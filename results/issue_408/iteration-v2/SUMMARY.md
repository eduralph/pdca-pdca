# Result — issue 408 / review-impl-tag-v-row

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the reviewer, not a taxonomy proxy, states whether a judgment-cell finding is
  builder-fixable; the classifier honours that statement only where the taxonomy allows it;
  and the reviewer's always-human Validation row is recognised as the constant STANDING row
  in all three forms production actually writes it.
- Success criterion: all four hold in `template/tests/test_autoiterate.py`, run by the
  C4 gate:
  (1) **Tag honoured, bounded by the taxonomy.** A primary-review verdict row on C5 or T5
  whose Verdict cell is `NEEDS-HUMAN [impl]` classifies IMPL. The promotable set is derived
  from `gates.canonical_elements()` as `kind == "judgment"` minus `V` (so exactly
  `{C5, T5}` today), the way `_GATE_ELEMENTS` is derived at `assemble.py:50`, and a test
  pins that derivation. An `[impl]` tag on an input cell (C1, C3) or on the V row is
  ignored (C1/C3 → HUMAN; V → STANDING, because the STANDING check runs BEFORE the tag
  check). An untagged C5/T5 row still classifies HUMAN. Only the Verdict cell carries the
  tag: an `[impl]` in the Basis cell of a C5/T5 row is ignored (row stays HUMAN; pinned by a
  test — existing Basis-cell `[impl]` fixtures sit on C4, which is IMPL through the
  gate-element rule anyway, `test_autoiterate.py:224`).
  (1b) **The tag is bounded on every PRIMARY-review path, not just rows.** Today the
  leading-`[impl]` rule in `_classify_finding` (`assemble.py:228-230`) runs for every
  artifact, including the primary review's legacy `- NEEDS-HUMAN` bullets
  (`assemble.py:576-593`). After this slice a primary-review bullet carrying `[impl]` is
  promoted only if its leading element id is promotable (C5/T5); otherwise the tag is
  stripped and the item is HUMAN. Tested: `- NEEDS-HUMAN [impl] — C1 Spec …` and
  `- NEEDS-HUMAN [impl] — Validation — fitness-to-purpose …` in `review.md` → HUMAN.
  (1c) **Plan advisories are never promoted.** Today a `[impl]` in a `plan-advisory-*.md`
  bullet classifies IMPL (same `_items_from_artifact` path, `assemble.py:304-306`); it stays
  HUMAN only because the plan prompt never emits the tag. This slice makes that structural:
  plan advisories are parsed with the tag stripped and ignored. Tested (red today):
  `- NEEDS-HUMAN [impl] — …` in a plan advisory → HUMAN. The other rows the driver builds
  itself (unverifiable gates, declared / refuted / unregistered dependencies, the size item)
  are already constructed as HUMAN directly and are unchanged.
  (2) **V row in all three forms.** The STANDING match accepts
  `Validation — fitness-to-purpose`, `V — Validation — fitness-to-purpose`, and
  `Validation -- fitness-to-purpose`, by normalising the Item cell (drop a leading
  `<element-id> —` / `<element-id> --` prefix ONLY when that id is the element whose
  canonical label follows — so `V —` before the Validation label, `C1 —` before `C1 Spec`;
  fold ASCII `--` to `—`, collapse whitespace) before an EXACT comparison. A mismatched
  prefix is kept, so the cell never equals a canonical label: `| C5 — Validation —
  fitness-to-purpose | NEEDS-HUMAN | … |` and the same with `T5 —` stay HUMAN (negative
  tests). The same normalisation is used by `_verdict_table_lines`
  (`assemble.py:615`, label compare `:640-641`), so a table written entirely in the prefixed form (`C1 — C1 Spec`, …)
  is still recognised as the verdict table. No prefix-matching of free text (the #294 rule):
  `Validation — fitness-to-purpose: patches the wrong layer` stays HUMAN. The
  `i in verdict_table` guard and the fail-closed "two STANDING rows → neither"
  guard (`assemble.py:610-611`) are unchanged and still pass their existing tests.
  (3) **Prompts carry the contract.** `_REVIEW_PROMPT` (`leaves.py:2723`) lists the element
  labels bare (not `{elem} — {label}`, `leaves.py:2743`, which is the source of the prefix
  form), says to write the Item cell exactly as listed, and instructs `NEEDS-HUMAN [impl]`
  on the C5/T5 rows only, for implementation defects. `_advisory_prompt`
  (`leaves.py:3583`) drops "when in doubt, OMIT '[impl]'" (`leaves.py:3601`) and requires
  every NEEDS-HUMAN bullet to carry `[impl]` or `[human]`; an untagged bullet still reads as
  HUMAN. `template/agents/reviewer.md.jinja` and `template/agents/adversary.md.jinja` state
  the same contract (they are the role bodies inlined for codex leaves).
  (4) A `[human]` tag on an advisory bullet is stripped from the §6 text the same way
  `[impl]` is, and classifies HUMAN.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: issue #332 items 2, 3, 5 — the reviewer/advisory/role-prompt tag contract;
  tag honouring in `assemble.py` for C5/T5 only (rows and primary-review bullets);
  plan-advisory parsing that ignores `[impl]` (`assemble.py:304-306`); V-row normalisation in both the STANDING
  match and the verdict-table detector; prompt/role-prompt alignment; tests as in the
  success criterion. / out of scope: `eligible()`, round budgets, deferral, the ledger,
  `rationale()` (all #409); routing input-cell defects to `iterate-plan` (#332 follow-up);
  whether a NEEDS-HUMAN on a *gate* cell whose gate row is `deferred` should stay IMPL
  (see Open questions); any change to `autoiterate.py`, `config.py`, `state.py`,
  `driver.py`, `flow.py`, `size_signal.py`.

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

Review issue #408: honor reviewer implementation tags within the taxonomy, recognize the three Validation-row forms, and prevent Basis quotes or duplicate Validation rows from misrouting work.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable routing outcomes and both carry-forward regressions; scope and external dependencies are explicit (`brief.md:13`, `brief.md:96`, `brief.md:192`). |
| C2 Reproduction (red pre-fix) | PASS | Independently retaining the new tests while stashing production changes produced 22 failures and 2 errors across 127 tests, including behavioral assertion failures (`review-red.log:478`). |
| C3 Change | FAIL | Newly promoted findings from reordered tables lose their actionable Basis: Verdict is located by header but Basis still means the following cell, so Do receives only “T5 Judgment” (`template/src/pdca_harness/assemble.py:818`, `template/src/pdca_harness/assemble.py:833`; reproduction below). |
| C4 Verification (red→green) | PASS | Restoring the exact production diff made all 127 focused tests pass; both requested carry-forward regressions are covered, although the additional reordered-Basis case remains uncovered (`review-green.log:111`, `template/tests/test_autoiterate.py:1927`, `template/tests/test_autoiterate.py:2045`). |
| C5 Causal adequacy | PASS | The fix changes classification and label matching at their cause, and counts duplicate standing rows before deduplication; it introduces no capability probe masking a load-time problem (`template/src/pdca_harness/assemble.py:324`, `template/src/pdca_harness/assemble.py:835`). |
| T1 Structure | PASS | Taxonomy-derived promotion and one shared label normalizer avoid independent routing definitions; changes remain within the five authorized files (`template/src/pdca_harness/assemble.py:69`, `template/src/pdca_harness/assemble.py:128`). |
| T2 Shape | PASS | Independent diff whitespace check, docs lint, and 22-page render/link audit passed; frozen T2 and host-parity logs agree (`review-docs.log:2`, `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver run passed 2,202 tests with 2 skips; frozen evidence records 24 root tests including real render/update cases, which local missing Copier prevented repeating (`review-suite.log:1763`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Establish that merged and closed/rejected work across all five affected paths does not supersede this change — the supplied target has only a synthetic base commit and no remote, while the brief's recorded path searches cover only part of the changed set (`brief.md:111`; investigation below). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting routing behavior serves the intended review workflow after the lost-Basis defect is resolved — deterministic parser tests cannot establish the quality of real reviewers' builder-fixability judgments (`template/agents/reviewer.md.jinja:114`, `template/agents/adversary.md.jinja:60`). |

Source citations beginning `template/` refer to the supplied `$PDCA_TARGET`; brief and log citations refer to this review sandbox. The target was readable and carried the patch; no stale-target caveat was needed. This review is advisory and does not gate acceptance.

**Finding — preserve the Basis when honoring reordered Verdict columns (P2).** At `template/src/pdca_harness/assemble.py:833`, Basis extraction still uses `cells[vi + 1]`. With the newly supported header `Item / Basis / Verdict`, `vi` points to the final column, so the explanation becomes empty. The newly enabled promotion then yields `NeedsHumanItem(text='T5 Judgment', kind='impl', ...)`, sending implementation work back without the actual defect description. Different findings on that element can also collapse to the same text. The added reordered-column test checks only the label and kind (`template/tests/test_autoiterate.py:1952`), so it misses this loss.

I exercised `_items_from_artifact(..., allow_standing=True)` with this input:

```text
| Item | Basis | Verdict |
|---|---|---|
| C1 Spec | ok | PASS |
| T5 Judgment | Handle empty input | NEEDS-HUMAN [impl] |
| Validation — fitness-to-purpose | human decision | NEEDS-HUMAN |
```

Actual promoted text: `T5 Judgment`. Expected: `T5 Judgment — Handle empty input`. Locate Basis through the header as well, and assert the entire resulting finding text in the regression test. The reproduction was executed directly against production code; `review-reordered.log` records the result.

Independent verification retained the patched test module, stashed only the four production/prompt files, ran the red leg, popped the stash, checked byte-identical restoration of the original diff, and ran the green leg. The production-import scanner also completed; its frozen wrapper reported no newly added test file, so that wrapper's pass alone was not treated as proof of production coverage. The behavioral tests import and exercise the production classifier and auto-iteration path.

The local root-suite attempt exited 77 because `/usr/bin/python3` cannot import Copier (`review-root-suite.log:6`). This is a reviewer-host limitation: the frozen T3 log explicitly shows render and update cases running successfully, rather than merely skipping. No unmet external dependency was inferred from that local limitation. All six frozen gate logs were inspected; the host-CI evidence demonstrates local command parity, not a hosted CI run.

The prior-art investigation ran `git log --all --oneline --` with all five changed paths and `git remote -v` inside the supplied target. It returned only `81bd363 pre-fix base 4b329e4d82319f6dcb2667da12f1f309b6ef636c` and no remote. The brief records merged-history searches for `assemble.py` and `leaves.py`, but its closed-unmerged path list omits the modified role files, test file, and `leaves.py`; complete merged/closed/rejected coverage cannot be confirmed from this artifact-only bundle. No other checkout was consulted.

The brief records explicit prior sign-off acceptance of mandatory advisory tags and approval of the other role changes (`brief.md:206`, `brief.md:208`). That decision is carried forward; this review does not reopen the accepted advisory-tag policy or request approval for it again.

### Advisory — code-review

# Advisory code review — issue_408 (review-impl-tag-v-row)

Both fixes from the sign-off carry-forward are in and tested: the tag is read only from the
Verdict column (`assemble.py:816-839`), and STANDING rows are counted before dedup
(`assemble.py:834-835`, guard at `:847`). Gates pass: C4 is red without the fix and green with
it, and the T3 suite ran 2202 tests OK. I found no bug that makes the patch wrong. The points
below are edge cases and small cleanups.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/assemble.py:822-823`: when the verdict table
  has a Verdict column and that cell says PASS / FAIL / N/A, the row is now **dropped from §6
  entirely**, even if another cell says NEEDS-HUMAN. Before the patch, that row reached the
  human as a HUMAN item. The carry-forward only asked for "no IMPL item". Dropping the row
  goes further and gives up the old fail-safe for a self-contradicting row (for example
  `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`). `test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding`
  pins the drop on purpose. The human should confirm that "the Verdict cell wins outright" is
  the policy they want, rather than "no IMPL, but still HUMAN".
- `template/src/pdca_harness/size_signal.py:330` (file not touched by the patch; out of scope
  per the brief): `_review_findings` spots a reviewer `[impl]` only as a tag at the start of
  the text (`_IMPL_MARKER_RE`). It cannot see the new Verdict-cell `NEEDS-HUMAN [impl]` on
  C5/T5, because those items start with the label. The only effect is that a C5 `[impl]` row
  on a C5 element whose gate row is `deferred` could be discounted as "not slice churn".
  The impact is small, but the docstring at `size_signal.py:302-303` ("a finding tagged
  `[impl]` … counts the round") is no longer fully true. This is worth a follow-up issue.
  It is not a blocker.
- `template/src/pdca_harness/assemble.py:77` vs `:80`: `_IMPL_MARKER_RE` is now used only by
  `size_signal.py:330`, and `_TAG_MARKER_RE` covers the same prefix. A comment on
  `_IMPL_MARKER_RE` saying it is kept for `size_signal` would stop someone deleting it as dead
  code, or "fixing" one regex and not the other.
- `template/src/pdca_harness/assemble.py:124` (`_ITEM_PREFIX_RE`): the element-id match is
  case-sensitive (`v — Validation — fitness-to-purpose` keeps its prefix), but the label
  compare after it is casefolded. This fails safe (the row stays HUMAN), so it is only a
  consistency nit.
- `template/src/pdca_harness/assemble.py:885-897` (`_verdict_column`): it walks back up to the
  table header once for every NEEDS-HUMAN row, which costs O(rows²) per table. Verdict tables
  have about 11 rows, so this doesn't matter in practice. It would be simpler to find the
  column once per block inside `_verdict_table_lines`, but that is not needed.

Nothing else: the classifier order (STANDING, then `[human]`/ignored, then the Verdict-cell
tag bounded to C5/T5, then the text tag, then the gate element) matches the brief, and
`_PROMOTABLE_ELEMENTS` is derived the same way `_GATE_ELEMENTS` is.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Establish that merged and closed/rejected work across all five affected paths does not supersede this change — the supplied target has only a synthetic base commit and no remote, while the brief's recorded path searches cover only part of the changed set (`brief.md:111`; investigation below).
- [ ] Validation — fitness-to-purpose — Decide whether the resulting routing behavior serves the intended review workflow after the lost-Basis defect is resolved — deterministic parser tests cannot establish the quality of real reviewers' builder-fixability judgments (`template/agents/reviewer.md.jinja:114`, `template/agents/adversary.md.jinja:60`).
- [ ] T5 Judgment
- [ ] Validation — fitness-to-purpose
- [ ] [human] — `template/src/pdca_harness/assemble.py:822-823`: when the verdict table has a Verdict column and that cell says PASS / FAIL / N/A, the row is now **dropped from §6 entirely**, even if another cell says NEEDS-HUMAN. Before the patch, that row reached the human as a HUMAN item. The carry-forward only asked for "no IMPL item". Dropping the row goes further and gives up the old fail-safe for a self-contradicting row (for example `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`). `test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding` pins the drop on purpose. The human should confirm that "the Verdict cell wins outright" is the policy they want, rather than "no IMPL, but still HUMAN".
- [ ] **The "bounded by the taxonomy" guarantee has a hole: `[impl]` on a primary-review *bullet*.** The brief says "The existing leading-`[impl]` rule for advisory bullets stays" (Design). That rule is not advisory-scoped. `_classify_finding` strips `[impl]` and returns IMPL before anything else (`assemble.py:228-230`). The primary review goes through that same path (`assemble.py:275` → `_items_from_artifact` → `_needs_human`, which still honours legacy `- NEEDS-HUMAN` bullets at `assemble.py:576-593`). So once the reviewer prompt teaches `[impl]`, a reviewer bullet like `- NEEDS-HUMAN [impl] — C1 Spec …` or `- NEEDS-HUMAN [impl] — Validation …` classifies IMPL, with no C5/T5 bound and no STANDING-first ordering. Criterion (1) only covers "a primary-review verdict **row**", so no test catches this. The brief should either state that the leading-`[impl]` rule applies only to advisory artifacts (and test a tagged reviewer bullet → HUMAN), or accept the hole explicitly.
- [ ] **Criterion (1) promises something the code does not do, and the scope does not cover the fix.** The brief says "Rows the driver adds itself (… plan advisories …) are never promoted by any tag". Plan advisories are parsed by the same classifier (`assemble.py:304-306`: `items += _items_from_artifact(ptext)`), so `- NEEDS-HUMAN [impl] — …` in a `plan-advisory-*.md` classifies IMPL today. They stay HUMAN only because the prompt never emits the tag ("HUMAN-kind by construction (the plan prompt emits no [impl] markers)", `assemble.py:302-303`). A red→green test for this clause would need a code change at `assemble.py:304-306`, which the Scope and Design sections never mention. That is a hidden second change. If the clause only means "unchanged by this slice", it is not a new behaviour to test and should be reworded. Pick one of those two readings.
- [ ] **The V-row normaliser, as specified, gives STANDING to rows that are not V.** The rule is "drop an optional leading `<element-id> —` / `<element-id> --` prefix" before the exact compare. It takes *any* element id. So `| C5 — Validation — fitness-to-purpose | NEEDS-HUMAN | … |` (or T5, C1, …) normalises to `_V_LABEL` and becomes STANDING. That is the kind of "real objection wearing the template's clothes" the #294 rule exists to block (`assemble.py:549-556`). The dual-STANDING guard (`:610-611`) only helps if the real V row is also present. The fix is small: strip the prefix only when it names the element whose label follows (for STANDING, only `V`), and add a negative test for a C5- or T5-prefixed Validation label.
- [ ] **Advisory `[impl]` is still not bounded by the taxonomy, and this slice makes it more common.** The Goal says "the classifier honours that statement only where the taxonomy allows it". For advisory bullets, though, `[impl]` still promotes whatever the finding is about (`assemble.py:228-230`; no element check). Clause (3) removes "when in doubt, OMIT '[impl]'" (`leaves.py:3601`, `adversary.md.jinja:66`) and forces a binary `[impl]`/`[human]` on every bullet. Today's conservative default ("an unmarked finding always reaches" the human, `adversary.md.jinja:66`) becomes a forced choice. More advisory findings about scope or fitness-to-purpose may be self-labelled `[impl]` and auto-iterated. #332 asks for this, but the Impact section ("Untagged findings stay HUMAN (fail-safe)") presents it as risk-free. It is a policy change and the human should explicitly accept it at sign-off.
- [ ] **The ordering note uses an id the brief never declares.** The note says the computed batch order is "`pdca-pdca waves 408 409 371 477`: [409] → [371, 477] → [408]". But **Conflicts with** lists only `409, 371`, and 477 appears nowhere else in the brief or the thread. No `dependency-state.json` was provided, so I could not resolve 409, 371 or 477. Either declare 477 with a reason, or drop it from the wave command. (The thread's "in-flight #369" was correctly replaced: #369's wording is already on main at `assemble.py:505-533`.)
- [ ] **(minor) The tag's position is under-specified against existing fixtures.** Criterion (1) only defines `NEEDS-HUMAN [impl]` *in the Verdict cell*. The existing suite already puts `[impl]` in the **Basis** cell (`test_autoiterate.py:224`, `:242`, `:266`, `:280`: `| C4 … | NEEDS-HUMAN | [impl] off-by-one |`). A C5/T5 row written that way would silently stay HUMAN. The brief should say whether a Basis-cell `[impl]` on C5/T5 is ignored (and pin that with a test) or also honoured. That way the prompt wording in clause (3) and the parser agree.

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
- Iteration delta (if iterating): Rebuild to fix one regression the reviewer found (reproduced at sign-off): assemble.py (_needs_human_rows, ~:833): the Verdict column is now found by its header (_verdict_column), but the Basis is still read as cells[vi + 1]. With a header ordered `| Item | Basis | Verdict |` the Basis is lost, so a promoted finding reads only `T5 Judgment` instead of `T5 Judgment — Handle empty input`, and the rebuild gets nothing to act on. Find the Basis column by its header too (fall back to the cell after the Verdict only when no Basis header exists), and make the reordered-column test assert the FULL finding text, not just the label and kind. Second change (human decision at sign-off): a verdict-table row whose Verdict cell says PASS / FAIL / N/A but whose other cells mention NEEDS-HUMAN must NOT be dropped from §6 (assemble.py ~:822-823). It must never become IMPL (no auto-rebuild), but it should still reach the human as a HUMAN item, which keeps the old fail-safe for self-contradicting rows like `| T5 Judgment | PASS | still NEEDS-HUMAN on scope |`. Update test_a_basis_quoting_an_impl_verdict_under_pass_is_no_finding: assert no IMPL item, and assert the row appears as a HUMAN item. The STANDING guards are unchanged. Keep everything else as is: the iteration-1 fixes (tag read from the Verdict column only; STANDING rows counted before dedup), the V-row normalisation, the C5/T5 bounding, the plan-advisory/primary-review bounding, and the prompt/role changes were all found fine. The advisory-tag policy change stays accepted.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
