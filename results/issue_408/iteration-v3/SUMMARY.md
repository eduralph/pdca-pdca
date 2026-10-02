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

Review issue #408: bound implementation tags to eligible reviewer judgments, align role prompts, and recognize Validation-row variants without losing human objections.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable routing boundaries and incorporates both prior sign-off corrections; reordered Basis text and contradictory verdicts have direct regressions (`brief.md:213`; `target/template/tests/test_autoiterate.py:1949`, `:1996`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production/prompt changes while retaining the new tests produced 61 failures and 2 errors across 135 tests; failures include real classification assertions, not merely missing symbols (`review-red.log:1205`; `target/template/tests/test_autoiterate.py:1855`). |
| C3 Change | FAIL | A supported prefixed Validation row now absorbs an identical, separate concerns-table objection, removing its HUMAN classification; preserve non-standing provenance when deduplicating (`target/template/src/pdca_harness/assemble.py:811`, `:856`; `review-probes.log:21`). |
| C4 Verification (red→green) | PASS | Restoring the exact patch made all 135 tests pass, independently confirming the supplied red→green evidence; this verifies the asserted suite, which misses the counterexample below (`review-green.log:113`; `gate-logs/C4-verify.log:1331`). |
| C5 Causal adequacy | FAIL | Label normalization addresses the parsing cause directly, but its interaction with deduplication violates the required separation between the standing row and actual objections; no capability-probe smell was found (`target/template/src/pdca_harness/assemble.py:799`, `:864`; `target/template/tests/test_autoiterate.py:2161`). |
| T1 Structure | PASS | The five changed files keep classification in the assembler, derive eligibility from the canonical taxonomy, and align callers/prompts without changing iteration budgets or state machinery (`target/template/src/pdca_harness/assemble.py:69`, `:349`; `target/template/src/pdca_harness/leaves.py:2759`). |
| T2 Shape | PASS | Independent diff whitespace check, docs lint, and 22-page render/link audit passed; frozen host-parity evidence agrees (`review-docs.log:1`; `review-site.log:2`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver run passed 2,210 tests with 2 skips; frozen evidence additionally shows actual Copier render/update cases passing, although this reviewer interpreter could not rerun them (`review-suite.log`; `gate-logs/T3-suite.log:38`, `:54`; `review-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the human-only role wording and complete affected-path prior-art coverage — prompt changes control rebuild routing, while the supplied history check omits some changed paths and cannot be independently completed from this one-commit, remote-free target (`target/template/agents/reviewer.md.jinja:114`; `target/template/agents/adversary.md.jinja:60`; `brief.md:112`, `:166`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the final behavior preserves every substantive objection while reducing unnecessary handoffs — the reproduced loss below must inform sign-off; the mandatory advisory-tag policy was already accepted and is not reopened (`target/template/src/pdca_harness/assemble.py:329`; `review-probes.log:23`; `brief.md:233`). |

**Finding: a separate human objection disappears after Validation normalization.**

In a complete verdict table, write the Validation Item as `V — Validation — fitness-to-purpose`, with Verdict `NEEDS-HUMAN` and Basis `Confirm operator workflow`. Follow it with a separate `## Concerns` table containing the bare Item `Validation — fitness-to-purpose`, the same Verdict, and the same Basis. The concerns table does not meet the verdict-table detector's two-label threshold, so its row must remain an actual HUMAN finding.

The patched parser normalizes the first row's text to match the second. `add()` then merges them at `target/template/src/pdca_harness/assemble.py:811`, retaining the first row's `standing=True`; it merges only `impl` and `other`, not standing provenance. Only one row counted toward `standing_rows`, so the duplicate-standing guard cannot recover the objection. Classification returns one STANDING item and zero HUMAN items. Before the patch, this same input retained both HUMAN items. Recognizing the first as STANDING is intended; losing the second is not.

Reproduce from this bundle with `PYTHONDONTWRITEBYTECODE=1 python3 review-probe.py`. The script compares the target's actual pre-fix source from `git show HEAD:…` with its patched production module. Captured results are in `review-probes.log:21`. Preserve a HUMAN item whenever deduplication encounters non-standing provenance, and test both table orders. The existing regression at `target/template/tests/test_autoiterate.py:2161` covers the opposite spelling arrangement (bare primary row, prefixed concerns row), which does not collide.

Independent verification used the disposable target only. Production/prompt hunks were stashed and restored; the resulting tracked diff was byte-for-byte identical. All generated evidence and temporary work stayed inside this bundle. No target-state staleness was observed. The root-suite rerun exited 77 because Copier is not importable by `/usr/bin/python3`; this is a reviewer-host limitation, not a patch defect or an undischarged build dependency: `gate-logs/T3-suite.log:38` records real render tests and `:42` records update-compatibility tests. The production-path scanner's log reports only “patch adds no new test file”; direct inspection and execution of the extended production-calling tests supplied the substantive evidence instead (`gate-logs/C5-prod-path.log:10`; `target/template/tests/test_autoiterate.py:1865`).

Prior-art investigation: affected-path `git log --all` returns only the synthetic base commit `2bac641`; `git remote -v` returns nothing. The brief records merged-history checks for `assemble.py` and `leaves.py`, but its closed-work path list excludes `leaves.py`, both role files, and the changed test file (`brief.md:112`). No supplied frozen log establishes those missing searches. The project-specific integration document is not in the supplied target; its generic template leaves human-only items as TODO (`target/template/docs/INTEGRATION.md.jinja:80`). The brief explicitly identifies role-file changes as human-only, so that obligation is retained in T5.

### Advisory — code-review

# Advisory code review — issue 408 (round 3)

No correctness bug found that needs a rebuild. Both sign-off fixes are in place and tested:
the Basis column is now found by its header, and a row whose Verdict says PASS / FAIL / N/A
but mentions NEEDS-HUMAN elsewhere is now a HUMAN item instead of being dropped. The earlier
fixes are still there too: the tag is read only from the Verdict column, and STANDING rows
are counted before dedup. What I checked and found sound:

- `template/src/pdca_harness/assemble.py:841-866` — the header lookup only runs for
  verdict-table rows. A row with an empty or missing Verdict cell falls back to the old
  "first cell mentioning NEEDS-HUMAN" read, and no tag is read on that path
  (`impl=col is not None and …`). So a malformed row can reach §6 but can never become IMPL.
- `assemble.py:800-809` — when the same text shows up twice, the dedup merge fails safe:
  `impl` is AND-ed and `other` is OR-ed, so if either copy is untagged or contradicts
  itself, the item drops to HUMAN. The fail-closed guard counts raw V rows
  (`standing_rows`), not deduped items.
- `assemble.py:293-341` (`_classify_finding`) — STANDING is checked before any tag, `[human]` / plan-advisory /
  `verdict_other` are checked before the gate-element rule, and an unhonoured `[impl]` on
  the primary review falls through to the untagged classification. This matches the brief
  (1)/(1b)/(1c)/(4).

Small, non-blocking notes (none needs a human decision):

- `template/src/pdca_harness/size_signal.py:330` (not touched by this diff; the brief puts
  `size_signal.py` out of scope) still finds `[impl]` with `assemble._IMPL_MARKER_RE` on the
  `_needs_human` text. A reviewer's new Verdict-cell `NEEDS-HUMAN [impl]` never shows up in
  that text, and its docstring (`size_signal.py:315-318`, "the pattern
  `assemble._classify_finding` strips") is now out of date, because `_classify_finding` uses
  `_TAG_MARKER_RE` (`assemble.py:80`). As far as I can tell this has no effect on behaviour:
  a C5/T5 `[impl]` row comes back as a non-STANDING IMPL item from
  `_items_from_artifact`, so the round is still counted. It is worth a follow-up note on
  #409 / #477 so the two readers don't drift apart.
- `assemble.py:77` — `_IMPL_MARKER_RE` is now used only by `size_signal.py`, and
  `_TAG_MARKER_RE` (`assemble.py:80`) covers what it matches. Its comment ("An advisory leaf
  tags…") reads as if it still drives classification. A one-line comment saying it is kept
  for `size_signal` would prevent confusion. Optional.
- `assemble.py:841` / `assemble.py:914-926` — `_table_header` walks back to the top of the
  table again for every NEEDS-HUMAN row, so the cost grows with the square of the number of
  rows. Verdict tables have about 11 rows, so this costs nothing in practice. Working out the
  header once per block in `_verdict_table_lines` would be the simpler version if this code
  is touched again. Optional.
- Gate note: `gate-logs/C5-prod-path.log` passes with "patch adds no new test file —
  nothing to assert", so the prod-path gate checked nothing this round. By reading the
  tests instead: the new tests in `template/tests/test_autoiterate.py:1816-2212` call
  production code through the module (`assemble._items_from_artifact`,
  `assemble.collect_needs_human`, `leaves._REVIEW_PROMPT`, `leaves._advisory_prompt`) and
  copy none of its logic, so they do test the real code.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the human-only role wording and complete affected-path prior-art coverage — prompt changes control rebuild routing, while the supplied history check omits some changed paths and cannot be independently completed from this one-commit, remote-free target (`target/template/agents/reviewer.md.jinja:114`; `target/template/agents/adversary.md.jinja:60`; `brief.md:112`, `:166`).
- [ ] Validation — fitness-to-purpose — Decide whether the final behavior preserves every substantive objection while reducing unnecessary handoffs — the reproduced loss below must inform sign-off; the mandatory advisory-tag policy was already accepted and is not reopened (`target/template/src/pdca_harness/assemble.py:329`; `review-probes.log:23`; `brief.md:233`).
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
- Iteration delta (if iterating): Rebuild to fix one regression the reviewer found (reproduced at sign-off): assemble.py (_needs_human_rows, add() ~:799-812): when two rows dedup to the same text, the merge AND-s `impl` and OR-s `other` but keeps the FIRST row's `standing`. So a verdict-table V row written `V — Validation — fitness-to-purpose` followed by a separate `## Concerns` table row `Validation — fitness-to-purpose` with the IDENTICAL Verdict and Basis collapses into one STANDING row, and the real objection disappears (pre-fix both reached §6 as HUMAN). Fix: merge standing fail-safe too (`standing = existing.standing and new.standing`), so any non-standing copy keeps the item a HUMAN finding. Add a test for this order (prefixed V row in the verdict table, bare-label copy with identical Basis in a Concerns table -> one HUMAN item, not STANDING) and keep the existing opposite-order test (test_a_concerns_table_copy_of_the_v_row_is_not_folded_into_it). Keep everything else as is: tag read from the Verdict column only, Verdict/Basis found by header, PASS rows mentioning NEEDS-HUMAN reach §6 as HUMAN, STANDING rows counted before dedup, V-row normalisation, C5/T5 bounding, plan-advisory/primary-review bounding, prompt/role changes, and the accepted advisory-tag policy. Do NOT restructure the review output format: replacing keyword parsing of free markdown with a structured verdict format is deliberately deferred to milestone 0.70 as its own issue.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Review output format: keyword parsing of free-markdown review output caused 4 parser-edge iterate rounds on #408 — replace with a structured, delimited verdict format (milestone 0.70, own issue).
