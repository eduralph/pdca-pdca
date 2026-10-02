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

Review issue #408: honor taxonomy-bounded implementation tags, recognize the three Validation-row forms, and preserve human findings through parsing and deduplication.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable routing outcomes, explicit exclusions, and accepted carry-forward decisions; the regression tests cover those specified cases (`brief.md:14`, `target/template/tests/test_autoiterate.py:1842`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production/prompt changes while retaining tests produced 84 failures and 2 errors across 140 tests; failures include behavioral assertions, not merely missing symbols (`reviewer-red.log:1617`). |
| C3 Change | FAIL | A contradictory prefixed Validation row becomes STANDING and loses its human handover finding because Verdict recognition still uses a substring; reproduced against base and patched production code (`target/template/src/pdca_harness/assemble.py:874`, `reviewer-probes.log:1`). |
| C4 Verification (red→green) | PASS | Restoring the production/prompt changes makes all 140 tests pass, independently confirming the gate's red→green claim; that coverage does not include the C3 counterexample (`reviewer-green.log:115`, `gate-logs/C4-verify.log:1748`). |
| C5 Causal adequacy | PASS | Tests exercise the production classifier and iteration path; taxonomy derivation and label normalization address the routing causes directly, with no capability-probe/load-time symptom guard (`target/template/tests/test_autoiterate.py:1867`, `target/template/src/pdca_harness/assemble.py:70`). |
| T1 Structure | PASS | Changes remain within parsing, prompt contracts, and their regression tests; the taxonomy remains the source for promotable elements (`target/template/src/pdca_harness/assemble.py:70`, `target/template/src/pdca_harness/leaves.py:2757`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and `git diff --check` passed; frozen docs and host-CI logs agree (`gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver run passed 2,215 tests with 2 skips; frozen evidence records 24 successful root render/update tests, which the local interpreter could not repeat because Copier is not importable (`reviewer-suite.log:1767`, `gate-logs/T3-suite.log:54`, `reviewer-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Complete the designated human review of the final role wording and settle affected-path prior art: the brief records searches but this one-commit/no-remote target cannot corroborate merged or closed/rejected history, and the recorded searches omit changed role/test paths (`target/template/agents/reviewer.md.jinja:114`, `target/template/agents/adversary.md.jinja:60`, `brief.md:111`, `brief.md:166`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resulting routing preserves human authority while returning actionable defects to Do, accounting for the reproduced loss of a scope finding; the advisory-tag policy itself was already accepted in carry-forward (`target/template/src/pdca_harness/assemble.py:883`, `brief.md:237`). |

**P2 — Preserve contradictory Validation verdicts as HUMAN.** At `target/template/src/pdca_harness/assemble.py:874`, `other` becomes false whenever the Verdict cell contains `needs-human` anywhere. This correctly rejects tag promotion through the whole-cell `[impl]` matcher, but does not reject STANDING at line 883. In an otherwise complete verdict table, this row demonstrates the regression:

```markdown
| V — Validation — fitness-to-purpose | PASS (was NEEDS-HUMAN [impl]) | still NEEDS-HUMAN: confirm the chosen scope |
```

Independent execution of the pre-fix source from the target's `HEAD` returns HUMAN, and production `autoiterate.deferrable()` retains the finding. The patched source returns STANDING and `deferrable()` returns `[]`. `N/A — not NEEDS-HUMAN [impl]` has the same result. The exact outputs are in `reviewer-probes.log:1`. Beside real implementation work, this scope objection therefore disappears from the deferred handover. Determine whether the Verdict actually states NEEDS-HUMAN before granting STANDING, and extend the quoted-verdict tests to the prefixed Validation forms. This is a parser correction within the existing scope, not a request for the deferred structured-format redesign.

The three recorded carry-forward regressions pass their added tests, including same-text Concerns/bullet copies withdrawing STANDING in either order (`target/template/tests/test_autoiterate.py:2218`). The production-path scanner's frozen log only says that no new test file was added (`gate-logs/C5-prod-path.log:10`); it does not independently establish production coverage. The inspected tests and independent red→green execution supply that evidence.

The target was readable and its production changes were restored after the stash-based experiment. No stale-target caveat applies. The root-suite limitation is local: frozen evidence explicitly shows Copier render/update cases running successfully (`gate-logs/T3-suite.log:38`), so it is not an undischarged external dependency or a patch defect. The available integration template leaves human-only enumeration as TODO; the role-review requirement above comes from the brief's explicit project-specific statement. The already accepted mandatory advisory-tag policy is not reopened.

### Advisory — code-review

# Check advisory — code review (issue #408)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. I found no
correctness bug in the new classifier, normaliser or prompts. The four brief clauses are
each covered by a test. C4 shows a real red leg (84 failures pre-fix) and T3 runs the full
suite green (2215 tests). Findings, most important first:

- NEEDS-HUMAN — template/src/pdca_harness/assemble.py:339 (with :874) — `verdict_other`
  goes beyond the brief. A verdict-table row whose Verdict cell is PASS / FAIL / N/A while
  another cell mentions NEEDS-HUMAN is now HUMAN on **every** element, gate cells included.
  For example, `| C4 … | FAIL | … NEEDS-HUMAN … |` used to be IMPL through the gate-element
  rule and auto-iterated. Now it halts for the human. None of the four success-criterion
  clauses names this change, and the brief's scope covers only C5/T5 tag honouring and V-row
  normalisation. The code comments cite a "#408 sign-off", and the change is tested
  (`test_a_gate_row_contradicting_its_verdict_does_not_auto_iterate`), so this looks
  deliberate. The human should confirm the gate-cell behaviour change is wanted in this
  slice and not in #409 or a follow-up. It reduces auto-iteration on gate rows.
- template/src/pdca_harness/size_signal.py:313-318, :330 — the docstring is now stale (a
  file this patch did not edit). It says the `[impl]` read uses "the pattern
  `assemble._classify_finding` strips". `_classify_finding` now strips `_TAG_MARKER_RE`
  (assemble.py:80), not `_IMPL_MARKER_RE` (assemble.py:77). The check at :330 also no longer
  matches what §6 does: a primary-review bullet `[impl] — C1 …` is HUMAN in §6 after this
  patch, but size_signal still reads it as "the reviewer saying a rebuild can fix it". The
  verdict-cell `NEEDS-HUMAN [impl]` form is invisible to :330. That form still counts the
  round, because the C5/T5 item is non-STANDING and so the returned list is non-empty. Both
  gaps only make the code count a round, never skip one, so behaviour is safe. Only the
  comment is wrong. A one-line docstring fix, or a note in the PR, would do. The brief puts
  `size_signal.py` out of scope, so this is not tagged for rebuild.
- template/src/pdca_harness/assemble.py:77 vs :80 — `_IMPL_MARKER_RE` is now used only by
  size_signal.py:330. `_TAG_MARKER_RE` covers it (`m.group(1) == "impl"`). Keeping both is
  fine, but a comment on :77 saying it stays only for size_signal would stop a later reader
  from treating the two as duplicates or editing just one.
- template/src/pdca_harness/assemble.py:855 / :932 — `_table_header` walks back to the top
  of the table for every NEEDS-HUMAN row, so the cost grows with the square of the table's
  row count. With about 11 rows this costs nothing. If you want it simpler, find the header
  once per block in `_verdict_table_lines` (which already finds the block bounds). That is
  optional, not a defect.
- Tests (template/tests/test_autoiterate.py, new `ReviewerImplTag` / `ValidationRowForms` /
  `TagContractPrompts`) — no weak test found. They go through production entry points
  (`_items_from_artifact`, `collect_needs_human`, `_try`), reach new symbols through the
  module (`assemble._PROMOTABLE_ELEMENTS`) as the brief requires, and include the negative
  cases (mismatched `C5 —` / `T5 —` prefix, free text after the label, Basis-cell `[impl]`,
  plan-advisory `[impl]`). The C5-prod-path gate passed with "patch adds no new test file —
  nothing to assert". That is expected, because the tests were appended to an existing
  module. It means that gate checked nothing here; it is not a fault in the patch.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Complete the designated human review of the final role wording and settle affected-path prior art: the brief records searches but this one-commit/no-remote target cannot corroborate merged or closed/rejected history, and the recorded searches omit changed role/test paths (`target/template/agents/reviewer.md.jinja:114`, `target/template/agents/adversary.md.jinja:60`, `brief.md:111`, `brief.md:166`).
- [x] Validation — fitness-to-purpose — Decide whether the resulting routing preserves human authority while returning actionable defects to Do, accounting for the reproduced loss of a scope finding; the advisory-tag policy itself was already accepted in carry-forward (`target/template/src/pdca_harness/assemble.py:883`, `brief.md:237`).
- [x] V — Validation — fitness-to-purpose — still NEEDS-HUMAN: confirm the chosen scope
- [x] template/src/pdca_harness/assemble.py:339 (with :874) — `verdict_other` goes beyond the brief. A verdict-table row whose Verdict cell is PASS / FAIL / N/A while another cell mentions NEEDS-HUMAN is now HUMAN on **every** element, gate cells included. For example, `| C4 … | FAIL | … NEEDS-HUMAN … |` used to be IMPL through the gate-element rule and auto-iterated. Now it halts for the human. None of the four success-criterion clauses names this change, and the brief's scope covers only C5/T5 tag honouring and V-row normalisation. The code comments cite a "#408 sign-off", and the change is tested (`test_a_gate_row_contradicting_its_verdict_does_not_auto_iterate`), so this looks deliberate. The human should confirm the gate-cell behaviour change is wanted in this slice and not in #409 or a follow-up. It reduces auto-iteration on gate rows.
- [x] **The "bounded by the taxonomy" guarantee has a hole: `[impl]` on a primary-review *bullet*.** The brief says "The existing leading-`[impl]` rule for advisory bullets stays" (Design). That rule is not advisory-scoped. `_classify_finding` strips `[impl]` and returns IMPL before anything else (`assemble.py:228-230`). The primary review goes through that same path (`assemble.py:275` → `_items_from_artifact` → `_needs_human`, which still honours legacy `- NEEDS-HUMAN` bullets at `assemble.py:576-593`). So once the reviewer prompt teaches `[impl]`, a reviewer bullet like `- NEEDS-HUMAN [impl] — C1 Spec …` or `- NEEDS-HUMAN [impl] — Validation …` classifies IMPL, with no C5/T5 bound and no STANDING-first ordering. Criterion (1) only covers "a primary-review verdict **row**", so no test catches this. The brief should either state that the leading-`[impl]` rule applies only to advisory artifacts (and test a tagged reviewer bullet → HUMAN), or accept the hole explicitly.
- [x] **Criterion (1) promises something the code does not do, and the scope does not cover the fix.** The brief says "Rows the driver adds itself (… plan advisories …) are never promoted by any tag". Plan advisories are parsed by the same classifier (`assemble.py:304-306`: `items += _items_from_artifact(ptext)`), so `- NEEDS-HUMAN [impl] — …` in a `plan-advisory-*.md` classifies IMPL today. They stay HUMAN only because the prompt never emits the tag ("HUMAN-kind by construction (the plan prompt emits no [impl] markers)", `assemble.py:302-303`). A red→green test for this clause would need a code change at `assemble.py:304-306`, which the Scope and Design sections never mention. That is a hidden second change. If the clause only means "unchanged by this slice", it is not a new behaviour to test and should be reworded. Pick one of those two readings.
- [x] **The V-row normaliser, as specified, gives STANDING to rows that are not V.** The rule is "drop an optional leading `<element-id> —` / `<element-id> --` prefix" before the exact compare. It takes *any* element id. So `| C5 — Validation — fitness-to-purpose | NEEDS-HUMAN | … |` (or T5, C1, …) normalises to `_V_LABEL` and becomes STANDING. That is the kind of "real objection wearing the template's clothes" the #294 rule exists to block (`assemble.py:549-556`). The dual-STANDING guard (`:610-611`) only helps if the real V row is also present. The fix is small: strip the prefix only when it names the element whose label follows (for STANDING, only `V`), and add a negative test for a C5- or T5-prefixed Validation label.
- [x] **Advisory `[impl]` is still not bounded by the taxonomy, and this slice makes it more common.** The Goal says "the classifier honours that statement only where the taxonomy allows it". For advisory bullets, though, `[impl]` still promotes whatever the finding is about (`assemble.py:228-230`; no element check). Clause (3) removes "when in doubt, OMIT '[impl]'" (`leaves.py:3601`, `adversary.md.jinja:66`) and forces a binary `[impl]`/`[human]` on every bullet. Today's conservative default ("an unmarked finding always reaches" the human, `adversary.md.jinja:66`) becomes a forced choice. More advisory findings about scope or fitness-to-purpose may be self-labelled `[impl]` and auto-iterated. #332 asks for this, but the Impact section ("Untagged findings stay HUMAN (fail-safe)") presents it as risk-free. It is a policy change and the human should explicitly accept it at sign-off.
- [x] **The ordering note uses an id the brief never declares.** The note says the computed batch order is "`pdca-pdca waves 408 409 371 477`: [409] → [371, 477] → [408]". But **Conflicts with** lists only `409, 371`, and 477 appears nowhere else in the brief or the thread. No `dependency-state.json` was provided, so I could not resolve 409, 371 or 477. Either declare 477 with a reason, or drop it from the wave command. (The thread's "in-flight #369" was correctly replaced: #369's wording is already on main at `assemble.py:505-533`.)
- [x] **(minor) The tag's position is under-specified against existing fixtures.** Criterion (1) only defines `NEEDS-HUMAN [impl]` *in the Verdict cell*. The existing suite already puts `[impl]` in the **Basis** cell (`test_autoiterate.py:224`, `:242`, `:266`, `:280`: `| C4 … | NEEDS-HUMAN | [impl] off-by-one |`). A C5/T5 row written that way would silently stay HUMAN. The brief should say whether a Basis-cell `[impl]` on C5/T5 is ignored (and pin that with a test) or also honoured. That way the prompt wording in clause (3) and the parser agree.
- [x] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
