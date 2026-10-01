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

Review issue #408: route builder-fixable reviewer findings through bounded `[impl]` tags, recognize the supported Validation-row spellings, and align reviewer/advisory prompts.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The scope defines testable routing boundaries and exact label matching, with the advisory-policy trade explicitly reserved for sign-off; the taxonomy boundary is grounded at `target/template/src/pdca_harness/assemble.py:69`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production/prompt changes while retaining the new tests produced 15 failures and 2 errors across 119 tests; substantive routing and label assertions fail, not merely imports (`review-red.log`; `target/template/tests/test_autoiterate.py:1855`). |
| C3 Change | FAIL | Two reproduced regressions violate the requested safety boundaries: normalized duplicate V rows evade ambiguity handling, and Basis-only tags can promote PASS rows; findings below (`target/template/src/pdca_harness/assemble.py:807`, `target/template/src/pdca_harness/assemble.py:814`). |
| C4 Verification (red→green) | PASS | Restoring the stashed fix made all 119 focused tests pass, independently confirming the frozen C4 result; this verifies the supplied cases, which omit both regressions below (`review-green.log`; `gate-logs/C4-verify.log:119`). |
| C5 Causal adequacy | PASS | The change addresses classification and label interpretation directly, without a capability probe or load-time symptom guard; tests call production classification and iteration paths (`target/template/tests/test_autoiterate.py:1848`, `target/template/tests/test_autoiterate.py:1865`). |
| T1 Structure | PASS | Promotion membership follows the canonical taxonomy, with explicit artifact-specific routing and one shared label normalizer; no unrelated subsystem change is required (`target/template/src/pdca_harness/assemble.py:69`, `target/template/src/pdca_harness/assemble.py:364`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/internal-link audit, and `git diff --check` passed, consistent with both frozen docs gates (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite: 2,194 tests, OK with 2 skips; frozen evidence additionally shows all 24 root render/update tests passing, although local Python lacks Copier (`review-suite.log:1761`; `gate-logs/T3-suite.log:56`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Accept or reject mandatory advisory routing choices and the role-prompt changes, and confirm affected-path merged/closed-work coverage — unbounded advisory tags can spend rebuild rounds, while this snapshot cannot independently establish prior art (`target/template/agents/adversary.md.jinja:60`; `target/template/agents/reviewer.md.jinja:114`; `brief.md:111`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the routing policy improves real reviewer handoffs without misrouting architectural concerns — deterministic parser/prompt tests do not establish the quality of model tagging (`target/template/agents/adversary.md.jinja:64`; `target/template/src/pdca_harness/assemble.py:337`). |

**Finding 1 — preserve duplicate detection before normalizing/deduplicating V rows (P2).** At `target/template/src/pdca_harness/assemble.py:807`, a bare Validation label and a `V —`-prefixed label become identical. If their Basis cells also match, `add()` drops the second row at line 772 before the ambiguity check at line 821. I appended a prefixed V row with the same Basis to a complete verdict table: the base preserved a HUMAN item alongside STANDING; the patch returns only STANDING. The brief expressly requires ambiguous duplicate V rows to lose their exemption. Count row occurrences before text deduplication and add coverage using identical Basis cells; the added test currently uses different Basis text.

**Finding 2 — read the tag from the actual Verdict column (P2).** At `target/template/src/pdca_harness/assemble.py:814`, `cells[vi]` is assumed to be the Verdict cell, but `vi` is the first cell anywhere containing `needs-human` (line 802). In a complete verdict table, `| C5 Causal adequacy | PASS | Quoted NEEDS-HUMAN [impl] from an old review |` therefore becomes IMPL, despite no routing instruction in its Verdict. The base already misread this as HUMAN; this patch newly promotes it to implementation work, potentially triggering unnecessary rebuilds. Use the Verdict column for both verdict recognition and tag extraction, and test this Basis-only quotation with a PASS verdict.

Both findings were executed against patched production code and the pre-fix source obtained only from this target's `HEAD`. Exact comparison output is in `review-edge-cases.log`. To reproduce the patched cases from this sandbox:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=target/template/src:target/template python3 - <<'PY'
from pdca_harness import assemble
from tests.test_autoiterate import _full_review
reviews = [
    _full_review() + "| V — Validation — fitness-to-purpose | NEEDS-HUMAN | fitness is the human's call |\n",
    _full_review({'C5': ('PASS', 'Quoted NEEDS-HUMAN [impl] from an old review')}),
]
for review in reviews:
    print(assemble._items_from_artifact(review, allow_standing=True))
PY
```

Evidence limits: the C5 scanner's frozen output says only “patch adds no new test file”; rerunning the available reference scanner likewise provides no substantive coverage of edits to existing tests. C5 above instead rests on production calls and the actual red→green run. The instance-scoped gate wrappers were not assumed to exist in the target; their frozen logs were read. Local root-suite execution exited 77 because Copier is not importable, but the frozen root log explicitly records successful render and update cases, so this is a reviewer-host caveat, not an unmet gate dependency or patch defect.

Prior art: the brief records merged-history queries by `assemble.py`/`leaves.py` and a closed-unmerged search covering several engine paths. It does not record equivalent coverage for both changed role bodies and the changed test file. My affected-path `git log --all` query finds only synthetic base commit `c0b3d98`; the disposable target has no remotes or closed-PR data. Consequently full prior-art coverage remains a human decision under T5. The available INTEGRATION file is an unfilled template, so the role-prompt human-only requirement is taken from the brief's explicit project-specific statement.

The target was readable and matched the patch. Production changes were restored after the red leg; no source fixes were made. This review is advisory and does not gate acceptance.

### Advisory — code-review

# Advisory code review — issue 408 (review-impl-tag-v-row)

No correctness bugs found in the patch. I traced the classifier order in
`_classify_finding` (`template/src/pdca_harness/assemble.py:318-339`): STANDING first, then
`[human]` / plan-advisory → HUMAN, then the Verdict-cell tag bounded to C5/T5, then the
leading-text tag (free for Check advisories, bounded for the primary review), then the
gate-element rule. This matches clauses 1, 1b, 1c and 4 of the brief. The fail-closed
"two STANDING rows → neither" guard keeps the impl bit and still grants STANDING to
neither row. A V row tagged `[impl]` and caught by that guard falls through to HUMAN,
because "Validation …" never matches `_ELEMENT_RE`. The other readers of these helpers in
`size_signal.py` (`:330`, `:332`, `:370`) still behave safely: a C5/T5 Verdict-cell
`[impl]` row is now a non-STANDING IMPL item, so `_review_findings` still counts the round
through its returned list. The C4 log shows the new tests red before the fix
(15 failures, 2 errors) and green after. The C5 prod-path gate asserted nothing ("patch
adds no new test file"), but the new tests do call production code directly
(`assemble._items_from_artifact`, `collect_needs_human`, `leaves._REVIEW_PROMPT`,
`leaves._advisory_prompt`).

Minor cleanups. None needs a human decision or a rebuild:

- `template/src/pdca_harness/size_signal.py:313-317,330` — the patch makes this docstring
  stale. It says the `[impl]` read uses "the pattern `assemble._classify_finding` strips"
  (`_IMPL_MARKER_RE`). `_classify_finding` now strips `_TAG_MARKER_RE`
  (`assemble.py:83`), and the reviewer's main `[impl]` statement now sits in the Verdict
  cell, where line 330 cannot see it. Behaviour is still right, since the item list catches
  it. Still, the comment and the now nearly unused `_IMPL_MARKER_RE`
  (`assemble.py:77`, which duplicates half of `_TAG_MARKER_RE`) are worth tidying: use
  `_needs_human_rows`' impl bit or `_TAG_MARKER_RE`, and update the docstring.
- `template/src/pdca_harness/assemble.py:124` — `_ITEM_PREFIX_RE` matches the element id
  case-sensitively, but the label compare after it is casefolded. So
  `validation — fitness-to-purpose` counts as STANDING, while `v — validation —
  fitness-to-purpose` does not. This fails safe (the row stays HUMAN), and production has
  not been seen writing a lowercase id. Adding `re.IGNORECASE` and upper-casing
  `group(1)` before the `_ELEMENT_OF_LABEL` lookup would close the gap if you want it fully
  symmetric.
- `template/src/pdca_harness/assemble.py:805-808` — the comment says a canonical label "is
  rendered in the matrix's own spelling". `_normalized_item_label` only folds `--` to `—`,
  collapses whitespace and drops the prefix; it keeps the reviewer's casing. Either reword
  the comment or map `norm` to the canonical label (for example, by keeping the original
  label in a casefold→label dict) so §6 text really is uniform.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Accept or reject mandatory advisory routing choices and the role-prompt changes, and confirm affected-path merged/closed-work coverage — unbounded advisory tags can spend rebuild rounds, while this snapshot cannot independently establish prior art (`target/template/agents/adversary.md.jinja:60`; `target/template/agents/reviewer.md.jinja:114`; `brief.md:111`).
- [x] Validation — fitness-to-purpose — Decide whether the routing policy improves real reviewer handoffs without misrouting architectural concerns — deterministic parser/prompt tests do not establish the quality of model tagging (`target/template/agents/adversary.md.jinja:64`; `target/template/src/pdca_harness/assemble.py:337`).
- [ ] **The "bounded by the taxonomy" guarantee has a hole: `[impl]` on a primary-review *bullet*.** The brief says "The existing leading-`[impl]` rule for advisory bullets stays" (Design). That rule is not advisory-scoped. `_classify_finding` strips `[impl]` and returns IMPL before anything else (`assemble.py:228-230`). The primary review goes through that same path (`assemble.py:275` → `_items_from_artifact` → `_needs_human`, which still honours legacy `- NEEDS-HUMAN` bullets at `assemble.py:576-593`). So once the reviewer prompt teaches `[impl]`, a reviewer bullet like `- NEEDS-HUMAN [impl] — C1 Spec …` or `- NEEDS-HUMAN [impl] — Validation …` classifies IMPL, with no C5/T5 bound and no STANDING-first ordering. Criterion (1) only covers "a primary-review verdict **row**", so no test catches this. The brief should either state that the leading-`[impl]` rule applies only to advisory artifacts (and test a tagged reviewer bullet → HUMAN), or accept the hole explicitly.
- [ ] **Criterion (1) promises something the code does not do, and the scope does not cover the fix.** The brief says "Rows the driver adds itself (… plan advisories …) are never promoted by any tag". Plan advisories are parsed by the same classifier (`assemble.py:304-306`: `items += _items_from_artifact(ptext)`), so `- NEEDS-HUMAN [impl] — …` in a `plan-advisory-*.md` classifies IMPL today. They stay HUMAN only because the prompt never emits the tag ("HUMAN-kind by construction (the plan prompt emits no [impl] markers)", `assemble.py:302-303`). A red→green test for this clause would need a code change at `assemble.py:304-306`, which the Scope and Design sections never mention. That is a hidden second change. If the clause only means "unchanged by this slice", it is not a new behaviour to test and should be reworded. Pick one of those two readings.
- [ ] **The V-row normaliser, as specified, gives STANDING to rows that are not V.** The rule is "drop an optional leading `<element-id> —` / `<element-id> --` prefix" before the exact compare. It takes *any* element id. So `| C5 — Validation — fitness-to-purpose | NEEDS-HUMAN | … |` (or T5, C1, …) normalises to `_V_LABEL` and becomes STANDING. That is the kind of "real objection wearing the template's clothes" the #294 rule exists to block (`assemble.py:549-556`). The dual-STANDING guard (`:610-611`) only helps if the real V row is also present. The fix is small: strip the prefix only when it names the element whose label follows (for STANDING, only `V`), and add a negative test for a C5- or T5-prefixed Validation label.
- [x] **Advisory `[impl]` is still not bounded by the taxonomy, and this slice makes it more common.** The Goal says "the classifier honours that statement only where the taxonomy allows it". For advisory bullets, though, `[impl]` still promotes whatever the finding is about (`assemble.py:228-230`; no element check). Clause (3) removes "when in doubt, OMIT '[impl]'" (`leaves.py:3601`, `adversary.md.jinja:66`) and forces a binary `[impl]`/`[human]` on every bullet. Today's conservative default ("an unmarked finding always reaches" the human, `adversary.md.jinja:66`) becomes a forced choice. More advisory findings about scope or fitness-to-purpose may be self-labelled `[impl]` and auto-iterated. #332 asks for this, but the Impact section ("Untagged findings stay HUMAN (fail-safe)") presents it as risk-free. It is a policy change and the human should explicitly accept it at sign-off.
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
- Iteration delta (if iterating): Rebuild to fix the two regressions the reviewer found (both reproduced at sign-off): 1. assemble.py (_needs_human_rows, ~:814): the [impl] tag is read from cells[vi], where vi is the first cell containing "needs-human" anywhere in the row, not the Verdict column. So `| C5 Causal adequacy | PASS | Quoted NEEDS-HUMAN [impl] from an old review |` in the verdict table becomes an IMPL item and would trigger a needless auto-rebuild. Use the Verdict column for both NEEDS-HUMAN recognition and tag extraction; add a test (PASS verdict + Basis-only quote -> no IMPL item). 2. assemble.py (~:807 with add() dedup ~:772): a bare and a `V —`-prefixed Validation row with identical Basis now normalise to the same text, so add() drops the second before the "two STANDING rows -> neither" fail-closed guard (~:821) can count it. Count STANDING rows before text dedup; add a test with IDENTICAL Basis cells (the existing test uses different Basis). Keep everything else; the rest of the patch (T5 prompt/role changes, V-row normalisation, plan-advisory/primary-review bounding) was found fine at sign-off. Advisory-tag policy change (mandatory [impl]/[human] on every advisory bullet, "when in doubt, omit" removed) was explicitly ACCEPTED at sign-off — keep it as is.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
