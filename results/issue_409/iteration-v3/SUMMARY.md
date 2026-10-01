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

Review issue #409: allow bounded rebuilds alongside human findings while preserving deferred findings for sign-off and retiring only positively cleared entries.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The four success criteria and iteration-2 corrections give executable acceptance conditions; the hard cap, size backstop, and no-new-budget constraint are pinned in `target/template/tests/test_autoiterate.py:880`, with the remaining infrastructure-policy decision recorded under T5. |
| C2 Reproduction (red pre-fix) | PASS | Keeping the changed tests while stashing production changes reproduced the old veto and missing ledger behavior: 147 tests, 22 failures and 29 errors (`reviewer-red.log:628`); mixed findings are exercised at `target/template/tests/test_autoiterate.py:1221`. |
| C3 Change | PASS | The change stays within the approved deferral/retirement mechanism and iteration-2 repairs; both acceptance entry points now consult the same blocker check (`target/template/src/pdca_harness/flow.py:214`, `target/template/src/pdca_harness/cli.py:1450`), without adding a budget. |
| C4 Verification (red→green) | PASS | Restoring the production patch turned the same 147 tests green (`reviewer-green.log:74`), including CLI acceptance, label matching, ambiguity, and stopping limits; the restored git diff equals the supplied patch byte-for-byte (`target/template/tests/test_autoiterate.py:815`, `target/template/tests/test_autoiterate.py:1028`). |
| C5 Causal adequacy | PASS | The unwanted veto is removed at the eligibility decision, while persistence covers the archive boundary that would lose findings; exercised production paths establish causality, and no optional-capability probe masks a load-time cause (`target/template/src/pdca_harness/autoiterate.py:207`, `target/template/src/pdca_harness/driver.py:135`). |
| T1 Structure | PASS | Shared acceptance checks and retirement before both archive transitions preserve the existing decision boundary; ledger writes replace atomically and ambiguous retirement matches retain evidence (`target/template/src/pdca_harness/flow.py:214`, `target/template/src/pdca_harness/autoiterate.py:364`). |
| T2 Shape | PASS | Independent docs lint, rendering of 22 pages, internal-link audit, and git diff whitespace checks passed; the stopping-rule explanation agrees with the exercised defaults (`reviewer-docs.log:2`, `target/docs/07-crosscutting.md:464`). |
| T3 Runtime | PASS | Independent offline suite: 2,125 tests, two skips (`reviewer-suite.log:1671`); frozen render/update evidence shows 24 passing tests including actual Copier operations (`gate-logs/T3-suite.log:37`); local Copier-library absence limits only that rerun. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate explicitly owes its substantive PR/commit audit to publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether missing-review and could-not-run infrastructure findings should remain deferred after later recovery — the brief leaves this policy open, and these historical rows still require clearance even when fresh checks recover (`brief.md:246`, `target/template/src/pdca_harness/assemble.py:289`, `target/template/tests/test_autoiterate.py:697`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether delaying human objections until bounded handover provides the intended operator benefit and acceptable review burden — tests establish retention and refusal of uncleared acceptance, but cannot settle that workflow tradeoff (`target/docs/07-crosscutting.md:458`, `target/template/tests/test_autoiterate.py:705`). |

Independent verification used the disposable target's production-only stash, retaining the proposed tests for the red leg, then restored the stash before the green leg. The red result includes behavioral assertion failures, not merely missing-symbol errors. The complete patch was restored unchanged. Source citations above resolve in the supplied target; no stale-target caveat was needed.

The production-path scanner's frozen PASS is narrow: it says there is no newly added test file to inspect (`gate-logs/C5-prod-path.log:10`). C5 above instead relies on reading and running the modified tests against the actual production modules, including the handover/acceptance and retirement paths. The proposed regression cases cover the iteration-2 label-prefix, proportional-match, and CLI-acceptance corrections.

The root-suite rerun returned 77 because this interpreter cannot import Copier (`reviewer-root-suite.log:6`). This is a reviewer-host limitation, not a patch failure or an undischarged dependency of the recorded gate: its frozen log explicitly shows render, CLI-name, and five update-compatibility cases executing successfully (`gate-logs/T3-suite.log:37`). The brief declares no external dependencies. The supplied integration template has no additional enumerated human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).

Prior art was checked by all 14 affected file paths against main's recent merged history, and against all 254 returned closed PRs using their file lists. The eligibility module's complete three-commit history covers the original auto-iterate and standing-row fixes; none implements this ledger. PR #410 has no changed files in the returned record, consistent with the brief's scaffold-only account. The only closed-unmerged overlap is the unrelated README probe #4. Evidence: `reviewer-prior-art-summary.txt:1`, `reviewer-path-history.log:1`, and `reviewer-closed-prs.json:1`. No competing implementation or prior rejection of this mechanism was identified.

No new implementation defect was established. The two NEEDS-HUMAN rows are advisory decisions for sign-off; the contribution audit remains due at publish.

### Advisory — adversary

# Adversary review — issue 409, iteration 3

Evidence re-run: `tests.test_autoiterate` + `tests.test_size_signal` on the patched target give 147 OK, matching `gate-logs/C4-verify.log`. That log's red leg (22 failures, 29 errors) falls only on new or changed tests, and `test_size_signal` is green on both legs, which the brief says it should be. I also ran 17 targeted mutations on a sandbox copy. 16 are caught, including every rule the iteration-2 sign-off asked for: labels stripped, the ratio, the floor applied before containment, one hit or none, the CLI accept path, the strict tick reader, exact-first protection against both wrong shapes, and size-by-kind against a naive `any(IMPL)`. The one mutation that survives drops the separator check in `_split_label` (template/src/pdca_harness/autoiterate.py:139), and I found no input where that matters. Two refutations landed:

- NEEDS-HUMAN — An unattended auto-iterate round can retire a deferred finding that nobody ticked, so the finding is lost with no human involved. How: `signoff._section` takes the FIRST matching §6 heading (template/src/pdca_harness/signoff.py:308-313). Advisory text is pasted into §5 verbatim (template/src/pdca_harness/assemble.py:380-383), ahead of the real §6 (assemble.py:419). So the new tick reader `cleared_needs_human` (signoff.py:123-136) reads a §6 block that a leaf quoted. `_retire_cleared_deferrals` runs on every iterate transition, including automatic ones (template/src/pdca_harness/driver.py:135, :141). Repro, run on the production code path in a sandbox: the ledger holds `T5 Judgment — the retry loop hides the first failure`. The adversary artifact quotes a `## 6. NEEDS-HUMAN` heading with that row ticked beneath it, plus one `[impl]` bullet. After assembly the real §6 carries the entry unticked. `flow._maybe_auto_iterate` fires, and the ledger is then `[]`. The finding now survives only unticked in `iteration-v1/SUMMARY.md`, which is the exact loss the ledger exists to prevent. This contradicts docs/07-crosscutting.md:458 ("The ledger is only emptied by you") and autoiterate.py:44. Clause 3(d)'s test covers only a SUMMARY with NO §6 heading, so it cannot see this. It is related to the shared heading-reader item scoped out in iteration 2, but unattended retirement is a new consequence of this diff. Two narrow fixes are possible: read the LAST matching §6 heading on the tick side, or skip retirement when §9 was written by `auto-iterate` (an automatic round has no human ticks by construction). The human decides whether to fix it now.
- NEEDS-HUMAN — The iteration-2 fail-open (a tick on one finding retires a different finding nobody ticked) is closed only when the shared text is a label. Any other shared opening of 20+ characters still triggers it once the shorter finding is short enough for the 0.6 ratio to allow it: below about 34 characters the 20-character floor alone decides, and longer findings pass whenever the shared opening reaches 60% (template/src/pdca_harness/autoiterate.py:181). I checked this with `retire_cleared` on the patched code, deleting the entry's own row and ticking a different fresh finding. `the fix does not cover the retry path` is retired by a tick on `the fix does not cover the CLI path`. `C5 Causal adequacy — the patch does not handle the empty-list case` is retired by `…concurrent writers`. `C5 Causal adequacy — template/src/pdca_harness/autoiterate.py:316 — first hit wins` is retired by `…autoiterate.py:126 — floor skipped`, a shared path:line opening, which is the citation form the brief asks findings to use. To any text matcher, a one-word edit looks the same as a different finding, so tuning the numbers will not settle this. A rule that would: treat a ticked row that exactly equals a row assembly rendered from a FRESH finding as that finding's clearance, never as an edit of a ledger entry, so fuzzy matching only applies to rows the human actually edited. That is a design call, because it needs the rendered row list at retire time. The precondition is that the human deleted the entry's own row.
- (Fail-closed, no action needed.) Labels no longer count toward the match, so a ledger entry with fewer than 20 characters after its label retires only on an unedited tick. Example: the ledger holds `T5 Judgment — naming is unclear`, the human ticks it with `(renamed in round 2)` appended, and the entry is kept and returns unticked next round. Nothing is lost, but docs/07-crosscutting.md:458-461 ("If you tick a deferred finding … that entry leaves the ledger") promises a little more than the code does.

Attempted to refute, could not:

- The CLI accept path now takes its C6 check (the rule that every §6 item must be cleared before accept) from `flow.accept_blockers` (template/src/pdca_harness/cli.py:1450). The other `open_needs_human` callers (cli.py:554, :697, :983; queue.py:43) are display-only.
- The tests reach production symbols directly (`autoiterate.retire_cleared`, `flow._maybe_auto_iterate`, `cli._signoff`, `driver.advance`), not copies. That matters because the C5 gate row passed with nothing to check ("patch adds no new test file").
- The ledger is not archived by either iterate branch.
- An empty or HUMAN-only §6 halts with no ledger written.
- An unreadable ledger stops auto-iterate before any budget is spent or decision written.
- STANDING rows are never deferred, and the rationale never quotes HUMAN text.

### Advisory — code-review

# Code review (advisory) — issue 409 / autoiterate-budgets-defer-ledger

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency.
Grounded on the patched tree at `$PDCA_TARGET`. Gates: C4 red→green holds (gate-logs/C4-verify.log: 22 failures + 29 errors without the fix, green with it); T3 suite green.

Overall: no fail-open bug found. The retirement logic (exact-first `protected` set, tick reader on `whole_on_missing=False`, open reader on `True`), the ledger write order in `write_decision`, and the shared `accept_blockers` path on both accept routes (flow and CLI) all match the brief. `signoff.record` still refuses a SUMMARY with no §6 (`signoff.py:227`), so the CLI path calling `accept_blockers` without `unrecordable` first leaves no gap. §6 items are always one line (`assemble.py:590-592`), so matching the first line of an open/ticked row against a ledger entry is sound. What's left is small:

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/autoiterate.py:170-173`: `_same_finding` applies `_MATCH_FLOOR` before it checks whether the two texts are EQUAL once their shared label is stripped. So a short finding whose only edit is the separator does not match itself: `_same_finding("C5 Causal adequacy — weak test for X", "C5 Causal adequacy: weak test for X")` returns False (checked on the patched tree). This fails safe (the entry stays in the ledger), but a human who ticks such a row sees the entry come back unticked every round. The fix is one line: `if a == b: return True` straight after `_past_shared_labels`, before the floor check. Add a matching case to `test_a_short_row_matches_only_exactly`.
- `template/src/pdca_harness/autoiterate.py:107-120`, `template/src/pdca_harness/signoff.py:159-164`, `template/src/pdca_harness/assemble.py:463-466` (reuse): the patch writes the same "strip the checkbox, collapse whitespace, casefold" rule three times. The `UNREADABLE_LEDGER_ITEM` promise ("never add a second copy", `autoiterate.py` constant comment) only holds while `assemble._deferred_needs_human` and `signoff.ensure_needs_human_item` normalise the same way. Move `_norm` / `_row_text` into `signoff` (autoiterate already imports it, and assemble can call it lazily) so all three share one helper. It's a cleanup, not a bug today.
- `template/src/pdca_harness/autoiterate.py:280-283` (minor): `_write_ledger` leaves `.deferred-findings.json.<pid>.tmp` in the bundle if `write_text` or `os.replace` raises. That's harmless to state detection, but nothing ever removes it. A `try/finally` that unlinks the temp file when `os.replace` did not run would tidy it up. Optional.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Decide whether missing-review and could-not-run infrastructure findings should remain deferred after later recovery — the brief leaves this policy open, and these historical rows still require clearance even when fresh checks recover (`brief.md:246`, `target/template/src/pdca_harness/assemble.py:289`, `target/template/tests/test_autoiterate.py:697`).
- [ ] Validation — fitness-to-purpose — Decide whether delaying human objections until bounded handover provides the intended operator benefit and acceptable review burden — tests establish retention and refusal of uncleared acceptance, but cannot settle that workflow tradeoff (`target/docs/07-crosscutting.md:458`, `target/template/tests/test_autoiterate.py:705`).
- [ ] An unattended auto-iterate round can retire a deferred finding that nobody ticked, so the finding is lost with no human involved. How: `signoff._section` takes the FIRST matching §6 heading (template/src/pdca_harness/signoff.py:308-313). Advisory text is pasted into §5 verbatim (template/src/pdca_harness/assemble.py:380-383), ahead of the real §6 (assemble.py:419). So the new tick reader `cleared_needs_human` (signoff.py:123-136) reads a §6 block that a leaf quoted. `_retire_cleared_deferrals` runs on every iterate transition, including automatic ones (template/src/pdca_harness/driver.py:135, :141). Repro, run on the production code path in a sandbox: the ledger holds `T5 Judgment — the retry loop hides the first failure`. The adversary artifact quotes a `## 6. NEEDS-HUMAN` heading with that row ticked beneath it, plus one `[impl]` bullet. After assembly the real §6 carries the entry unticked. `flow._maybe_auto_iterate` fires, and the ledger is then `[]`. The finding now survives only unticked in `iteration-v1/SUMMARY.md`, which is the exact loss the ledger exists to prevent. This contradicts docs/07-crosscutting.md:458 ("The ledger is only emptied by you") and autoiterate.py:44. Clause 3(d)'s test covers only a SUMMARY with NO §6 heading, so it cannot see this. It is related to the shared heading-reader item scoped out in iteration 2, but unattended retirement is a new consequence of this diff. Two narrow fixes are possible: read the LAST matching §6 heading on the tick side, or skip retirement when §9 was written by `auto-iterate` (an automatic round has no human ticks by construction). The human decides whether to fix it now.
- [ ] The iteration-2 fail-open (a tick on one finding retires a different finding nobody ticked) is closed only when the shared text is a label. Any other shared opening of 20+ characters still triggers it once the shorter finding is short enough for the 0.6 ratio to allow it: below about 34 characters the 20-character floor alone decides, and longer findings pass whenever the shared opening reaches 60% (template/src/pdca_harness/autoiterate.py:181). I checked this with `retire_cleared` on the patched code, deleting the entry's own row and ticking a different fresh finding. `the fix does not cover the retry path` is retired by a tick on `the fix does not cover the CLI path`. `C5 Causal adequacy — the patch does not handle the empty-list case` is retired by `…concurrent writers`. `C5 Causal adequacy — template/src/pdca_harness/autoiterate.py:316 — first hit wins` is retired by `…autoiterate.py:126 — floor skipped`, a shared path:line opening, which is the citation form the brief asks findings to use. To any text matcher, a one-word edit looks the same as a different finding, so tuning the numbers will not settle this. A rule that would: treat a ticked row that exactly equals a row assembly rendered from a FRESH finding as that finding's clearance, never as an edit of a ledger entry, so fuzzy matching only applies to rows the human actually edited. That is a design call, because it needs the rendered row list at retire time. The precondition is that the human deleted the entry's own row.
- [ ] `template/src/pdca_harness/autoiterate.py:170-173`: `_same_finding` applies `_MATCH_FLOOR` before it checks whether the two texts are EQUAL once their shared label is stripped. So a short finding whose only edit is the separator does not match itself: `_same_finding("C5 Causal adequacy — weak test for X", "C5 Causal adequacy: weak test for X")` returns False (checked on the patched tree). This fails safe (the entry stays in the ledger), but a human who ticks such a row sees the entry come back unticked every round. The fix is one line: `if a == b: return True` straight after `_past_shared_labels`, before the floor check. Add a matching case to `test_a_short_row_matches_only_exactly`.
- [x] **The default size backstop means the Goal's budget can never be the binding limit, and the brief does not say so.** The Motivation says the problem is that "the round budget … is never the constraint that binds", and clause (1)'s worked example depends on rounds 4–5 happening. But `size_signal.DEFAULT_THRESHOLDS["rounds"] = 2` (`size_signal.py:73`). Clause (4) keeps "a size-backstop item makes `eligible()` false". So on a default instance the third Check (2 archives) raises the size item and the loop stops at 2 rounds, whatever `soft_auto_iters` or `max_auto_iters` is set to. `test_size_signal.py:179-187` pins this ordering, and `pdca.toml.jinja:292` documents it. The brief puts "how size-signal counts rounds (#477)" out of scope, so after this change `soft_auto_iters`/`max_auto_iters` above 2 still do nothing unless `[size_signal].rounds` is raised or set to 0. That applies to the default of 3 too, and to the 3/5 example. The unit criterion can pass while the stated Goal is not delivered. The brief should do three things: say this plainly, document in `pdca.toml.jinja` next to `soft_auto_iters` that the key only matters once `size_signal.rounds` is raised, and add `pdca.toml.jinja:289-293` (whose comment states the old rule) to the edit list. Otherwise it should explain why #477 is not a prerequisite.
- [x] **The ticked-rows reader's `whole_on_missing=True` points the safe direction the wrong way.** Clause (3) requires the new reader to call `signoff._section(..., whole_on_missing=True)` "the lenient §6 side, matching `open_needs_human`". That leniency is safe for `open_needs_human` only because scanning the whole document finds more `- [ ]` rows and so blocks accept harder (`signoff.py:108-111`, `:237-238`). A reader that looks for `- [x]` rows gets the opposite effect: with no §6 heading, every ticked checkbox anywhere in SUMMARY is treated as a tick. That includes checkboxes quoted in §5 review text, which is pasted in verbatim at `assemble.py:395`. Each such tick retires a ledger entry, so an unreviewed deferred finding can be lost. That is exactly the kind of loss the ledger is meant to prevent. The open-row side (protection) should stay lenient. The tick side should be `whole_on_missing=False`, so a missing §6 retires nothing. `unrecordable()` (`signoff.py:154-156`) makes this path hard to reach today. But the brief makes `True` a binding contract, and the reasoning it gives for it is wrong. The thread imposed this constraint, so a human should decide rather than the planner quietly changing it.
- [x] **Clause (4)'s named test cannot go red first.** The criterion says "Both directions of `test_the_tag_is_the_mechanism` (`test_size_signal.py:280`) pass", and Falsifiability (4) calls the "ordinary HUMAN beside IMPL fires" case a direction of that test. It is not one. The test's two directions are size-text HUMAN → False and size-text IMPL → True (`test_size_signal.py:285-290`), and both already pass on `main`. The only failing leg in clause (4) is the new "[IMPL, ordinary HUMAN] → True" case, which is clause (2)'s change. Nothing in clause (4) fails today, so the check cannot tell apart a size-by-kind composition from the naive `any(IMPL)` that would drop the backstop entirely. The brief should require one new test that fails against a plain `any(item.kind == IMPL)`, for example `[IMPL, ordinary HUMAN, size HUMAN] → False` next to `[IMPL, ordinary HUMAN] → True`. It should also stop claiming that `:280` provides the failing leg.
- [x] **The convergence baseline ("every Check that reaches the auto-iterate decision, including declines") has no definition, so clause (1) can't be checked at its edges.** `_maybe_auto_iterate` can decline in five places before or at the budget check: auto-iterate off or not at AWAITING_SIGNOFF (`flow.py:296`), a decision already recorded (`:303-307`), `collect_needs_human` raised (`:308-317`), ineligible (`:318-330`), and budget spent (`:331-335`). The brief doesn't say which of these record an IMPL count. One case changes the result. A HUMAN-only decline records IMPL=0 and the human then iterates by hand. Above soft, any later Check with IMPL ≥ 1 is then an "increase", so auto-iterate never fires again even though the budget is left. The brief should list which decline paths observe a count, and say whether a human-driven iterate resets the baseline. A test should pin both.
- [x] **The scope is two independent changes plus a bug fix, and the brief admits it.** The Open questions say "the natural cut is budgets (clause 1) vs defer+ledger (clauses 2–4)". Clause (1) (`config.py`, the `auto-iterate.json` shape, `flow.py:331-335`) shares no mechanism with the ledger, retirement or `_apply_decision` work. The thread does scope both under #409, so this is not smuggled in. But leaving the split to "the sizing prompt" means the review load is already set. The change touches 9 source files, the jinja template, 2 docs and 2 test modules, and it adds a gate at `_apply_decision` that runs on every sign-off, not only with auto-iterate on. The finding above also makes clause (1) almost unobservable on default settings. So the split should be decided at Plan: ship defer+ledger (which fixes the 13.5% veto the Motivation measures) and hold the budgets until #477 settles how size-signal counts rounds.

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
- Iteration delta (if iterating): Design stays as-is; fix three retirement defects from the iteration-3 review (§6 items 3–5): 1. Unattended retirement via a quoted §6 heading (adversary). `signoff._section` returns the FIRST `## 6. NEEDS-HUMAN` heading (signoff.py:308-313); §5 pastes leaf text verbatim ahead of the real §6 (assemble.py:380-383), so `cleared_needs_human` can read ticks a leaf quoted, and `_retire_cleared_deferrals` (driver.py:135, :141) empties the ledger on an automatic round with no human involved. Fix: make the tick-side reader use the LAST matching §6 heading (or the real, assembled §6), AND/OR skip retirement when §9 was written by auto-iterate. Add a test: ledger entry + an advisory artifact quoting a §6 heading with that row ticked + one [impl] bullet → after an auto-iterate round the entry is still in the ledger. 2. Fuzzy fail-open beyond labels (adversary). Any shared opening ≥ 20 chars (or ≥ 60% ratio) lets a tick on one finding retire a different one whose own row was deleted (autoiterate.py:181), e.g. "the fix does not cover the retry path" retired by a tick on "...the CLI path", and shared path:line openings. Do not tune thresholds. Rule: a ticked row that exactly equals a row assembly rendered from a FRESH finding is that finding's clearance, never an edit of a ledger entry; fuzzy matching applies only to rows the human actually edited (needs the rendered row list at retire time). Tests for the three repro pairs. 3. `_same_finding` (autoiterate.py:170-173) applies `_MATCH_FLOOR` before checking equality after `_past_shared_labels`, so a separator-only edit of a short finding doesn't match itself. Add `if a == b: return True` before the floor check; add the case to `test_a_short_row_matches_only_exactly`. Stale plan-review items were cleared by the human (resolved by the Plan re-scope). Items 1–2 (T5 infra-row deferral policy, fitness-to-purpose) were not ruled on — do not change behaviour for them.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
