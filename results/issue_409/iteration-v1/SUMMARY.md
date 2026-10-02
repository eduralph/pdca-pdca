# Result — issue 409 / autoiterate-budgets-defer-ledger

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: one HUMAN finding no longer vetoes an unattended rebuild. While Check still
  finds implementation work, the driver rebuilds — stopped only by the existing hard cap
  (`max_auto_iters`) or the size backstop — and HUMAN findings are held in a loss-proof
  ledger that re-enters §6 at handover, so every one still reaches the human under the C6
  guard.
- Success criterion: all four hold in `template/tests/test_autoiterate.py` (plus the
  `template/tests/test_size_signal.py` fixture adaptations), run by the C4 gate:
  (1) **Two stops, no new budget.** The loop's stopping rules are exactly: `max_auto_iters`
  (unchanged: field, default 3, clamp below `max_passes`, `auto-iterate.json` `{"count": n}`
  shape all as today) and the size backstop (clause 4). No new config key is added: a test
  asserts `Config` has no `soft_auto_iters` attribute and that rendering
  `template/pdca.toml.jinja` yields no `soft_auto_iters` key. With the defer rule of
  clause 2 in place, a bundle whose Checks keep returning `[IMPL, ordinary HUMAN]` fires
  until `count == max_auto_iters` and then halts with the budget-spent message
  (`flow.py:331-335`), when `[size_signal].rounds = 0`; with the default
  `[size_signal].rounds = 2` the same bundle stops at 2 rounds on the size item and says so
  on stderr (the existing `flow.py:318-330` path).
  (2) **Defer, don't veto.** `eligible()` is true iff ≥ 1 IMPL item and no size-backstop
  item (clause 4). HUMAN items next to IMPL items are written to a
  `deferred-findings.json` ledger. The ledger is NOT in `state.DOWNSTREAM_OF_BRIEF`
  (so an iterate does not archive it), IS in `state.CYCLE_EVIDENCE_ONLY` (a test pins
  membership against the module constant), and its entries are merged, deduplicated, into
  §6 by `assemble_summary`, so every deferred finding is an open `- [ ]` item at handover.
  An empty §6 still halts and never auto-accepts
  (`test_empty_section6_halts_and_never_auto_accepts` passes unchanged). A HUMAN-only set
  still halts at once. `rationale()` names what was addressed AND what was deferred, and
  still carries only IMPL items into the builder's carry-forward (the #294 property). A
  ledger that exists but cannot be read is written into §6 and blocks an accept, on the
  shared decision path every sign-off uses (`flow._apply_decision`), not only when
  auto-iterate is on.
  (3) **The #335 fold — retirement.** Before an iterate archives `SUMMARY.md`, ledger
  entries the human positively ticked (`- [x]`) in §6 are retired. A still-open §6 row
  protects ledger entries using the same `_same_finding` relation the tick match uses,
  assigned exact-first in two tiers: an open row verbatim-equal to a ledger entry protects
  that entry ONLY (a near-twin cannot shield its exactly-ticked neighbour); an edited open
  row that verbatim-owns nothing protects EVERY entry it `_same_finding`-matches (fail
  closed). NOT the flat symmetric-fuzzy exclusion
  (`any(_same_finding(entry, o) for o in still_open)`), which re-creates the
  permanently-unclearable pair. Shape: a `protected: set[int]` computed once before the
  tick loop, whose guard becomes `hits[0] not in protected`. The two §6 readers take
  OPPOSITE fail-safe directions, per `signoff._section`'s own contract (`signoff.py:231`):
  the open-row reader (protection) uses `whole_on_missing=True` — scanning the whole
  document finds more open rows and protects more; the NEW ticked-rows reader uses
  `whole_on_missing=False` — with no §6 heading it finds no ticks and retires nothing (a
  `- [x]` quoted in §5 review text, pasted verbatim at `assemble.py:395`, must never retire a
  ledger entry). This reverses the thread's `True` for the tick side (confirmed by the human at Plan).
  Four tests: (a) the #335 repro — an annotated but unticked row plus
  a similar ticked new finding → the unadjudicated entry survives; (b) matcher drift —
  every edit shape `_same_finding` tolerates in a tick also protects when left open, even
  against an exact tick; (c) an edited open row matching two near-twin entries protects
  both; (d) a SUMMARY with no §6 heading and a `- [x]` row elsewhere retires nothing.
  (4) **The #324 composition.** The size backstop stops the loop by KIND of item, not by
  disqualifying every HUMAN item: a HUMAN item for which `size_signal.is_size_item(text)`
  is true makes `eligible()` false; otherwise ordinary HUMAN items defer. The same size text
  tagged IMPL still rebuilds. Both directions of `test_the_tag_is_the_mechanism`
  (`test_size_signal.py:280`) keep passing (they pass today too — they guard against
  regression, not the red leg). One NEW test discriminates the size-by-kind rule from a
  naive `any(item.kind == IMPL)`: `[IMPL, ordinary HUMAN] → True` AND
  `[IMPL, ordinary HUMAN, size HUMAN] → False` in the same test. The flow tests at
  `test_size_signal.py:215` and `:237` get this change's fixture updates: an IMPL +
  ordinary-HUMAN set now FIRES, so the "declines silently" case becomes HUMAN-only.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: issue #332 item 4, plus the #335 fold, the #324 composition, and the
  stopping-rule consolidation, as in the success criterion. Files: `autoiterate.py`
  (`eligible()`, `rationale()`, the ledger, retirement), `state.py`
  (`CYCLE_EVIDENCE_ONLY`), `driver.py` (retire before the archive, in both iterate
  branches), `assemble.py` (merge deferred findings into §6; update the #324 comment at
  `:307-311`, which states the old `eligible()` rule), `signoff.py` (the ticked-rows
  reader), `flow.py` (`_maybe_auto_iterate` defer messages; the ledger-readability check in
  `_apply_decision`; the comment at `:319-324` states the stop rule — keep it accurate),
  `cli.py` (`--auto-iterate` help text). **Consolidated docs:** the stopping rules are
  described ONCE, in `docs/07-crosscutting.md`'s auto-iterate section ("It's bounded",
  `:456`): the hard cap plus the size backstop, which stops the loop early (default 2 rounds)
  and why. The `auto_iterate` comment in `template/pdca.toml.jinja` (`:53-72`) is updated for
  the defer rule (today it lists "an unmarked advisory finding" and a C5/T5 concern as things
  that halt the bundle — after this change they defer to handover) and points to the size
  backstop instead of restating it; the `[size_signal]` `rounds` comment (`:292-295`) stays
  the single place that states the round threshold. `docs/05-check.md` (`:405-407`, `:773-779`)
  links to step 07 rather than repeating the mechanics. /
  out of scope: any new round budget or convergence test (`soft_auto_iters` — dropped, see
  the note at top); changing `max_auto_iters`'s default or clamp; changing the size
  backstop's threshold or how it counts rounds (#477); the `[impl]` tag, prompt changes,
  `_PROMOTABLE_ELEMENTS`, V-row normalisation (#408); routing input-cell defects to
  `iterate-plan` (`autoiterate.DECISION` stays the single `iterate-do` token, its guard
  unchanged); #334 (landed — this only adds the ledger to the existing
  `CYCLE_EVIDENCE_ONLY`); `config.py`.

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

Review issue #409: allow bounded unattended rebuilds alongside HUMAN findings while preserving those findings for human sign-off and retiring only positively cleared entries.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The approved scope gives falsifiable outcomes for mixed findings, both stop rules, ledger retention, and safe retirement; the no-new-budget constraint is covered by executable checks (target/template/tests/test_autoiterate.py:851; brief.md:28). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the changed tests produces 21 failures and 14 errors across 141 tests, including the mixed-finding veto and premature stopping (red-rerun.log:213; red-rerun.log:453). |
| C3 Change | PASS | The patch addresses the specified lifecycle without adding a budget or changing defaults; deferred findings survive archives and return to the handover checklist (target/template/src/pdca_harness/state.py:174; target/template/src/pdca_harness/assemble.py:359). |
| C4 Verification (red→green) | PASS | Restoring the production patch makes all 141 focused tests pass; this independently reproduces the frozen C4 evidence and covers handover accept refusal and both iterate transitions (green-rerun.log:73; target/template/tests/test_autoiterate.py:708; target/template/tests/test_autoiterate.py:1033). |
| C5 Causal adequacy | PASS | Removing the eligibility veto directly addresses the stalled rebuild, while exact-first protection prevents both lost open findings and permanently protected near-twins; no optional-capability/load-time workaround was introduced (target/template/src/pdca_harness/autoiterate.py:159; target/template/src/pdca_harness/autoiterate.py:306; target/template/tests/test_autoiterate.py:944). |
| T1 Structure | PASS | Persistence, assembly, retirement, and accept checking use the existing lifecycle boundaries; strict tick parsing prevents unrelated review text from authorizing retirement (target/template/src/pdca_harness/driver.py:135; target/template/src/pdca_harness/signoff.py:135; target/template/src/pdca_harness/flow.py:176). |
| T2 Shape | PASS | Independent docs lint and 22-page render/link audit pass, as does git diff --check; the host-parity log reports the same underlying checks (docs-lint-rerun.log:1; docs-render-rerun.log:2; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent offline suite passes 2,119 tests with two skips; frozen evidence additionally shows 24 passing root tests including actual render/update cases, although this review host lacks importable Copier (suite-rerun.log:1670; gate-logs/T3-suite.log:38; root-rerun.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred gate explicitly requires the substantive audit at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path merged and closed/rejected prior-art coverage before adopting the port — the brief records a partial path search, but the supplied one-commit target has no remotes or PR evidence to independently rule out duplicate or rejected work (brief.md:151; prior-art-rerun.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether rebuilding before adjudicating ordinary judgment, scope, and environment findings is acceptable for opted-in instances — tests establish preservation and stopping behavior, but the value of delaying those decisions remains the maintainer's call (target/docs/07-crosscutting.md:442; target/docs/07-crosscutting.md:464). |

No grounded patch defect found. This review is advisory; acceptance remains the human's decision.

Independent reproduction used the disposable target at base 940565897e0df93e11c20c0d7ea76ac5ffa803ca. I stashed only `template/src`, retained the regression tests, and ran `PYTHONPATH=src python3 -m unittest tests.test_autoiterate tests.test_size_signal` from `target/template`, then restored the stash and reran the same command. Red failures include ordinary assertion failures, not merely missing new symbols. The final target diff is byte-for-byte identical to the supplied `patch.diff`. Temporary test files and output artifacts were confined beneath this review sandbox.

I also ran the offline suite, docs validators, whitespace check, and reference production-import scanner. The latter only checks newly added test files, so its success is vacuous here, consistent with `gate-logs/C5-prod-path.log:10`; inspection and the red→green run establish that the edited tests exercise production. The retirement cases explicitly distinguish the original open-row matching bug from symmetric fuzzy overprotection (target/template/tests/test_autoiterate.py:944; target/template/tests/test_autoiterate.py:960).

The root-suite rerun exited 77 because Copier is not importable in this interpreter (root-rerun.log:6). This is a reviewer-host limitation, not a patch failure or an unmet build dependency: the frozen gate actually exercised render and update compatibility and passed (gate-logs/T3-suite.log:38; gate-logs/T3-suite.log:54). Wrapper paths belong to the gate's instance root; their absence here is not a finding. No additional concrete human-only requirements are enumerated in the supplied integration template (target/template/docs/INTEGRATION.md.jinja:80).

For prior art I searched every affected path in the supplied target's available history. The only result is its synthetic pre-fix commit, and `git remote -v` is empty (prior-art-rerun.log:1). The brief names a merged-history search for autoiterate/config/state and asserts no closed-unmerged matches; the underlying closed/rejected search results and coverage for the remaining affected paths are unavailable. The T5 decision is to confirm that coverage against the canonical repository, not to treat the synthetic history as proof that no prior work exists.

### Advisory — adversary

# Adversarial review — issue 409 / autoiterate-budgets-defer-ledger

The red→green evidence holds. The fix has one real fail-open path in the new retirement code, plus one untested rule. Every case below was run against the production modules at `$PDCA_TARGET` (scratch copies in this sandbox, not the target).

## Refutations

- NEEDS-HUMAN — **A §6 heading quoted in §5 retires a ledger entry the human never ticked.** The brief picked `whole_on_missing=False` for the tick reader so that "a `- [x]` quoted in §5 review text … must never retire a ledger entry". The patch covers only the case where the SUMMARY has no §6 heading at all. `signoff.cleared_needs_human` (template/src/pdca_harness/signoff.py:123-136) and `open_needs_human` both go through `_section`, which takes the FIRST `## 6. NEEDS-HUMAN` heading (signoff.py:310-313). `assemble` pastes review and advisory text verbatim into §5, above the real §6 (template/src/pdca_harness/assemble.py:399-400).
  - **Repro:** the ledger holds `[E]`. An advisory writes a fenced example block containing `## 6. NEEDS-HUMAN — items the human must clear before sign-off` and `- [x] E`. The real §6 renders `- [ ] E`. The human records `iterate-do` with nothing ticked, then `driver.advance` runs.
  - **Result:** the ledger becomes `[]`. `retire_cleared` (template/src/pdca_harness/autoiterate.py:303-316) reads the tick from the fake section and cannot see the real open row that would protect E.
  - **Existing hole, not from this diff:** the same bundle's C6 read (the check that blocks accept while §6 rows are open) returned `[]` open rows even with a red gate. The fix belongs in the shared `_section` reader, for example skipping headings inside code fences, or requiring the §6 heading to come after §5. That is a scope call, because C6 uses the same reader.

- NEEDS-HUMAN — **A fresh near-twin row shields an exactly-ticked ledger entry.** The brief says a verbatim open row protects only its own entry, "a near-twin cannot shield its exactly-ticked neighbour". The code at template/src/pdca_harness/autoiterate.py:306-309 treats ANY open row that matches no ledger entry verbatim as an "edited" row. That includes an unedited finding this Check raised fresh.
  - **Repro:** the ledger holds `[P = "C5 Causal adequacy — guards the symptom in the parser"]`. This round's reviewer raises `R = "…in the renderer"`. §6 shows `- [x] P` and `- [ ] R`. The human records `iterate-do`.
  - **Result:** after `driver.advance` the ledger is still `[P]`, so P comes back unticked next round.
  - **Severity:** this fails closed. Nothing is lost; the human just re-ticks P.
  - **Test gap:** the tests only pair twins that are both in the ledger (template/tests/test_autoiterate.py:956-958, :981-986).
  - **Decision needed:** should a verbatim fresh row count as owning itself (protecting nothing), or stay fail-closed as now?

- NEEDS-HUMAN [impl] — **The "more than one fuzzy hit fails closed" rule is untested.** Changing `len(hits) == 1` to `hits` at template/src/pdca_harness/autoiterate.py:316 (retire the first hit) passes all 141 tests in `test_autoiterate` + `test_size_signal`. The rule does matter:
  - **Case:** the ledger holds `[P, R]` as above. The human deletes P's row and edits R's row to `…in the UI layer`, then ticks it.
  - **Current code:** keeps both, which is correct.
  - **Mutated code:** retires P, the one the human did not tick.
  - **Fix:** add this case to `RetiresOnlyWhatTheHumanTicked`.

- NEEDS-HUMAN — **"Loss-proof" does not hold against a leaf, and the patch now tells the builder the file name.** The builder can write the bundle directory (template/src/pdca_harness/leaves.py:2517 grants `d`). The new carry-forward line in the brief the builder reads says the findings are "held in deferred-findings.json" (template/src/pdca_harness/autoiterate.py:339-342).
  - **Effect:** deleting the file reads as "nothing deferred" (autoiterate.py:204), and so does emptying it to `{"items": []}`. Either way every deferred finding silently drops out of the handover §6, and C6 passes. The only remaining copies are in the archived `iteration-v*/SUMMARY.md` files.
  - `auto-iterate.json` has the same exposure (pre-existing). The ledger differs because it is now the only live copy of those findings.
  - **Options:** a cheap partial fix is to stop naming the file in builder-facing text. The real decision is whether bundle files the driver trusts need protection from leaves.

## Tried to refute, could not

- **C4 red→green.** Re-ran the green leg: 141 tests OK. The frozen red leg (gate-logs/C4-verify.log) fails for the right reasons; for example, `TwoStops` fails with "0 != 3" because today's veto declines the round.
  - Many retirement tests go red only through `AttributeError` on a precondition line, so I mutation-tested the discriminating assertions instead. Each of these variants turns at least one test red:
    - the two wrong protection shapes the brief names (symmetric-fuzzy and exact-only);
    - a lenient tick reader;
    - a naive `any(IMPL)` eligibility check;
    - dropping the retire call in the iterate-plan branch, or moving it after the archive;
    - removing `_hold_unreadable_ledger`;
    - deferring after `bump`;
    - no dedup when rendering;
    - filtering out non-string ledger entries;
    - recording STANDING items in the ledger.
  - So tests (a)–(d) and clause 4 discriminate as the brief requires.
- **The C5 row "pass" is vacuous.** The gate log says "patch adds no new test file — nothing to assert", so it proves nothing on its own. It is not a real problem: the tests drive `flow._maybe_auto_iterate`, `driver.advance` and `assemble.assemble_summary`, and mutating production code turns them red.
- **Also tried, could not break:**
  - the size-by-kind stop;
  - the hard cap with `rounds = 0`;
  - an unreadable ledger at accept on the shared `_apply_decision` path;
  - a ledger write failure (it happens before `bump`, so no round is spent);
  - render dedup between ledger entries and fresh findings.
- **Sandbox note:** `test_the_calibrator_uses_THIS_definition` errors in my copies only because `scripts/size-calibrate` was not copied into the sandbox. It is an environment artifact, not a finding.

### Advisory — code-review

# Advisory code review — issue 409 (autoiterate-budgets-defer-ledger)

Lens: bugs the patch introduces, plus reuse/simplification. Advisory only. The gates pass (C4 red→green, T3 suite green). I found no blocking correctness bug. The tests for clauses 1–4 are present and are built to tell the wrong designs apart (`template/tests/test_autoiterate.py:944`, `:960`, `:988`, `:997`, `:1065`).

## Correctness

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/autoiterate.py:126`: in `_same_finding`, the containment test (`a in b or b in a`) skips `_MATCH_FLOOR`. A short ticked row can therefore match any ledger entry that contains it as a substring. Example: a human trims a row to a few words, or ticks a short unrelated row such as a gate line. In `retire_cleared` (`autoiterate.py:~310-316`), a single such hit retires the entry unless an open row protects it. That only happens when the entry's own row is no longer open verbatim (the human deleted or ticked it). So the risk is small, but it fails open, and the brief says "absence is not consent". Fix: apply the floor to containment too (require `min(len(a), len(b)) >= _MATCH_FLOOR` before the substring test). Then add one test with a short ticked row that is a substring of a deleted entry.
- `template/src/pdca_harness/autoiterate.py:233-235`: if `write_text` or `os.replace` fails, `_write_ledger` leaves `.deferred-findings.json.<pid>.tmp` in the bundle. The file is harmless (no reader globs it), but it is never cleaned up and is not archived. Low priority: a `try/finally` that unlinks the tmp file on failure would handle it.
- `template/src/pdca_harness/autoiterate.py:238-260` (`defer`): deduplication uses exact normalised text only, so a reviewer who rewords the same HUMAN concern each round adds one ledger entry per round. The handover §6 then has near-duplicate rows (at most `max_auto_iters` of them), and the human must tick each one. The brief chose this on purpose ("never deduplicated fuzzily"), so this is a note, not a defect.

## Reuse / simplification

- `template/src/pdca_harness/assemble.py:446` (`_deferred_needs_human`) rewrites `autoiterate._norm` inline (`" ".join(t.split()).casefold()`), even though the function already imports `autoiterate` locally. Calling `autoiterate._norm` keeps defer-time and assembly-time dedup on one definition, so they cannot drift.
- `template/src/pdca_harness/signoff.py:159-166` (`ensure_needs_human_item`) repeats the checkbox list and normalisation from `autoiterate._BOXES` / `_row_text`. `signoff` cannot import `autoiterate` (that would be an import cycle). The cleaner direction is to move `_norm`/`_row_text` into `signoff` and have `autoiterate` import them from there. Cosmetic.
- `template/src/pdca_harness/flow.py:216-230`: `_hold_unreadable_ledger` parses the ledger on every accept, even when auto-iterate never ran. `deferred()` returns early when the file is absent, so the cost is one `exists()` call. No action needed.

Nothing else found on either lens. Two things I checked and found correct: retirement runs in both iterate branches in `driver.py`, and `_hold_unreadable_ledger` runs before the C6 check in `_apply_decision`.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm affected-path merged and closed/rejected prior-art coverage before adopting the port — the brief records a partial path search, but the supplied one-commit target has no remotes or PR evidence to independently rule out duplicate or rejected work (brief.md:151; prior-art-rerun.log:1).
- [ ] Validation — fitness-to-purpose — Decide whether rebuilding before adjudicating ordinary judgment, scope, and environment findings is acceptable for opted-in instances — tests establish preservation and stopping behavior, but the value of delaying those decisions remains the maintainer's call (target/docs/07-crosscutting.md:442; target/docs/07-crosscutting.md:464).
- [ ] **A §6 heading quoted in §5 retires a ledger entry the human never ticked.** The brief picked `whole_on_missing=False` for the tick reader so that "a `- [x]` quoted in §5 review text … must never retire a ledger entry". The patch covers only the case where the SUMMARY has no §6 heading at all. `signoff.cleared_needs_human` (template/src/pdca_harness/signoff.py:123-136) and `open_needs_human` both go through `_section`, which takes the FIRST `## 6. NEEDS-HUMAN` heading (signoff.py:310-313). `assemble` pastes review and advisory text verbatim into §5, above the real §6 (template/src/pdca_harness/assemble.py:399-400).
- [ ] **A fresh near-twin row shields an exactly-ticked ledger entry.** The brief says a verbatim open row protects only its own entry, "a near-twin cannot shield its exactly-ticked neighbour". The code at template/src/pdca_harness/autoiterate.py:306-309 treats ANY open row that matches no ledger entry verbatim as an "edited" row. That includes an unedited finding this Check raised fresh.
- [ ] **The "more than one fuzzy hit fails closed" rule is untested.** Changing `len(hits) == 1` to `hits` at template/src/pdca_harness/autoiterate.py:316 (retire the first hit) passes all 141 tests in `test_autoiterate` + `test_size_signal`. The rule does matter:
- [ ] **"Loss-proof" does not hold against a leaf, and the patch now tells the builder the file name.** The builder can write the bundle directory (template/src/pdca_harness/leaves.py:2517 grants `d`). The new carry-forward line in the brief the builder reads says the findings are "held in deferred-findings.json" (template/src/pdca_harness/autoiterate.py:339-342).
- [ ] `template/src/pdca_harness/autoiterate.py:126`: in `_same_finding`, the containment test (`a in b or b in a`) skips `_MATCH_FLOOR`. A short ticked row can therefore match any ledger entry that contains it as a substring. Example: a human trims a row to a few words, or ticks a short unrelated row such as a gate line. In `retire_cleared` (`autoiterate.py:~310-316`), a single such hit retires the entry unless an open row protects it. That only happens when the entry's own row is no longer open verbatim (the human deleted or ticked it). So the risk is small, but it fails open, and the brief says "absence is not consent". Fix: apply the floor to containment too (require `min(len(a), len(b)) >= _MATCH_FLOOR` before the substring test). Then add one test with a short ticked row that is a substring of a deleted entry.
- [ ] **The default size backstop means the Goal's budget can never be the binding limit, and the brief does not say so.** The Motivation says the problem is that "the round budget … is never the constraint that binds", and clause (1)'s worked example depends on rounds 4–5 happening. But `size_signal.DEFAULT_THRESHOLDS["rounds"] = 2` (`size_signal.py:73`). Clause (4) keeps "a size-backstop item makes `eligible()` false". So on a default instance the third Check (2 archives) raises the size item and the loop stops at 2 rounds, whatever `soft_auto_iters` or `max_auto_iters` is set to. `test_size_signal.py:179-187` pins this ordering, and `pdca.toml.jinja:292` documents it. The brief puts "how size-signal counts rounds (#477)" out of scope, so after this change `soft_auto_iters`/`max_auto_iters` above 2 still do nothing unless `[size_signal].rounds` is raised or set to 0. That applies to the default of 3 too, and to the 3/5 example. The unit criterion can pass while the stated Goal is not delivered. The brief should do three things: say this plainly, document in `pdca.toml.jinja` next to `soft_auto_iters` that the key only matters once `size_signal.rounds` is raised, and add `pdca.toml.jinja:289-293` (whose comment states the old rule) to the edit list. Otherwise it should explain why #477 is not a prerequisite.
- [ ] **The ticked-rows reader's `whole_on_missing=True` points the safe direction the wrong way.** Clause (3) requires the new reader to call `signoff._section(..., whole_on_missing=True)` "the lenient §6 side, matching `open_needs_human`". That leniency is safe for `open_needs_human` only because scanning the whole document finds more `- [ ]` rows and so blocks accept harder (`signoff.py:108-111`, `:237-238`). A reader that looks for `- [x]` rows gets the opposite effect: with no §6 heading, every ticked checkbox anywhere in SUMMARY is treated as a tick. That includes checkboxes quoted in §5 review text, which is pasted in verbatim at `assemble.py:395`. Each such tick retires a ledger entry, so an unreviewed deferred finding can be lost. That is exactly the kind of loss the ledger is meant to prevent. The open-row side (protection) should stay lenient. The tick side should be `whole_on_missing=False`, so a missing §6 retires nothing. `unrecordable()` (`signoff.py:154-156`) makes this path hard to reach today. But the brief makes `True` a binding contract, and the reasoning it gives for it is wrong. The thread imposed this constraint, so a human should decide rather than the planner quietly changing it.
- [ ] **Clause (4)'s named test cannot go red first.** The criterion says "Both directions of `test_the_tag_is_the_mechanism` (`test_size_signal.py:280`) pass", and Falsifiability (4) calls the "ordinary HUMAN beside IMPL fires" case a direction of that test. It is not one. The test's two directions are size-text HUMAN → False and size-text IMPL → True (`test_size_signal.py:285-290`), and both already pass on `main`. The only failing leg in clause (4) is the new "[IMPL, ordinary HUMAN] → True" case, which is clause (2)'s change. Nothing in clause (4) fails today, so the check cannot tell apart a size-by-kind composition from the naive `any(IMPL)` that would drop the backstop entirely. The brief should require one new test that fails against a plain `any(item.kind == IMPL)`, for example `[IMPL, ordinary HUMAN, size HUMAN] → False` next to `[IMPL, ordinary HUMAN] → True`. It should also stop claiming that `:280` provides the failing leg.
- [ ] **The convergence baseline ("every Check that reaches the auto-iterate decision, including declines") has no definition, so clause (1) can't be checked at its edges.** `_maybe_auto_iterate` can decline in five places before or at the budget check: auto-iterate off or not at AWAITING_SIGNOFF (`flow.py:296`), a decision already recorded (`:303-307`), `collect_needs_human` raised (`:308-317`), ineligible (`:318-330`), and budget spent (`:331-335`). The brief doesn't say which of these record an IMPL count. One case changes the result. A HUMAN-only decline records IMPL=0 and the human then iterates by hand. Above soft, any later Check with IMPL ≥ 1 is then an "increase", so auto-iterate never fires again even though the budget is left. The brief should list which decline paths observe a count, and say whether a human-driven iterate resets the baseline. A test should pin both.
- [ ] **The scope is two independent changes plus a bug fix, and the brief admits it.** The Open questions say "the natural cut is budgets (clause 1) vs defer+ledger (clauses 2–4)". Clause (1) (`config.py`, the `auto-iterate.json` shape, `flow.py:331-335`) shares no mechanism with the ledger, retirement or `_apply_decision` work. The thread does scope both under #409, so this is not smuggled in. But leaving the split to "the sizing prompt" means the review load is already set. The change touches 9 source files, the jinja template, 2 docs and 2 test modules, and it adds a gate at `_apply_decision` that runs on every sign-off, not only with auto-iterate on. The finding above also makes clause (1) almost unobservable on default settings. So the split should be decided at Plan: ship defer+ledger (which fixes the 13.5% veto the Motivation measures) and hold the budgets until #477 settles how size-signal counts rounds.

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
- Iteration delta (if iterating): Rebuild to close two gaps in the retirement code; keep everything else as-is. - §6 item 5 (adversary): the "more than one fuzzy hit fails closed" rule in retire_cleared (template/src/pdca_harness/autoiterate.py:~316, `len(hits) == 1`) is untested — mutating it to retire the first hit passes all 141 tests. Add the case to RetiresOnlyWhatTheHumanTicked: ledger [P, R] near-twins; human deletes P's row, edits R's row and ticks it → both entries must survive. - §6 item 7 (code review): in _same_finding (autoiterate.py:126) the containment test (`a in b or b in a`) skips _MATCH_FLOOR, so a short ticked row can retire any ledger entry that contains it — fails open, against "absence is not consent". Apply the floor to containment too (require min(len(a), len(b)) >= _MATCH_FLOOR before the substring test) and add a test: a short ticked row that is a substring of a deleted entry retires nothing. Out of scope for this rebuild: items 3 (shared signoff._section heading reader), 4 (fresh near-twin fails closed — acceptable), 6 (leaf write access to the bundle dir).
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
