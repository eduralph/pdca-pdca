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

Review issue #409: allow bounded unattended rebuilds alongside HUMAN findings while preserving those findings through a deferred ledger and retiring only findings the human cleared.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The approved scope gives falsifiable requirements for both existing stops, preservation, retirement, and sign-off; the latest carry-forward explicitly resolves the three retirement corrections without reopening the dropped soft budget (`brief.md:27`, `brief.md:251`; `template/tests/test_autoiterate.py:1052`, `template/tests/test_autoiterate.py:1304`). |
| C2 Reproduction (red pre-fix) | PASS | With patched tests retained and production changes stashed, the old HUMAN veto and absent ledger reproduce 25 assertion failures and 36 errors across 152 tests; behavioral failures include zero rounds instead of the required three (`review-red.log:755`; `template/tests/test_autoiterate.py:899`). |
| C3 Change | PASS | The change meets the authorized defer/retirement scope, including fresh-finding ownership and quoted-tick isolation; no new confirmed defect found, and affected-path history plus closed-PR inspection found no competing implementation (`template/src/pdca_harness/autoiterate.py:394`, `template/src/pdca_harness/signoff.py:149`; `review-prior-art.log:1`). |
| C4 Verification (red→green) | PASS | Restoring the production patch makes all 152 focused tests pass, including handover loss prevention and both sign-off paths; the restored target diff is byte-identical to the input patch (`review-green.log:77`; `template/tests/test_autoiterate.py:705`, `template/tests/test_autoiterate.py:815`; `gate-logs/C4-verify.log:858`). |
| C5 Causal adequacy | PASS | The original HUMAN veto is removed directly, and retirement distinguishes rendered findings before fuzzy matching; no optional-capability probe or load-time symptom guard is introduced (`template/src/pdca_harness/autoiterate.py:218`, `template/src/pdca_harness/autoiterate.py:394`; `template/tests/test_autoiterate.py:1326`). |
| T1 Structure | PASS | Preservation and retirement belong to the ledger module, archive transitions retire before moving evidence, and both accept entry points share the unreadable-ledger check; the exercised boundaries support the required lifecycle (`template/src/pdca_harness/driver.py:135`, `template/src/pdca_harness/driver.py:317`, `template/src/pdca_harness/flow.py:214`, `template/src/pdca_harness/cli.py:1450`). |
| T2 Shape | PASS | Independent docs lint, 22-page site render/link audit, and diff whitespace check pass; the frozen host-parity log also records the same docs checks succeeding (`review-lint.log:1`, `review-render.log:1`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline execution passes 2,130 tests with two skips; render/update coverage rests on the frozen gate's 24 passing root tests because this sandbox's Python cannot import Copier (`review-suite.log:1674`, `review-root.log:6`; `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; the deferred row owes its substantive PR/commit audit to the mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether recovered infrastructure findings should still require explicit clearance at handover — the independent probe shows a missing-review finding remains an accept blocker after fresh review/gate findings become empty, adding historical recovery work to sign-off (`template/src/pdca_harness/assemble.py:260`, `template/src/pdca_harness/autoiterate.py:310`; `review-infra-policy.log:4`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Judge whether deferring human concerns until bounded handover provides sufficient oversight in real operation — the exercised preservation rules cannot establish the quality or workload of that human review (`docs/07-crosscutting.md:445`, `docs/07-crosscutting.md:465`). |

Source citations beginning `template/` or `docs/` are grounded in this round's patched `$PDCA_TARGET` (`target/`). Brief and evidence-log citations are relative to the review sandbox. The target was readable, matched the supplied patch, and required no stale-base caveat.

Independent verification used `git stash push -- template/src/pdca_harness` to retain the new tests while restoring pre-fix production, then `git stash pop` to restore the fix. Both legs ran `PYTHONPATH=src python3 -m unittest tests.test_autoiterate tests.test_size_signal` from `target/template`. The red failures include actual assertions, not merely missing new symbols. The green leg exercises the latest quoted-section, fresh-row, short-label, ambiguity, CLI-accept, and stopping-rule cases. Full-suite verification ran `PYTHONPATH=src python3 -m unittest discover -s tests`; all temporary test data was directed inside this sandbox with `TMPDIR`.

The independent shape commands were `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out ../review-site`, from `target`. The root command `python3 -m tests.run_root_suite` returned 77 because Copier is not importable here (`review-root.log:6`). That is a reviewer-host limitation, not a patch defect or an undischarged gate dependency: the frozen T3 log explicitly shows both render cases and all five update-compatibility cases executing successfully (`gate-logs/T3-suite.log:38`). The brief declares no external dependencies. No shim or substitute was used to manufacture a green rerun.

The instance-scoped wrapper commands are not available in the target. Their frozen logs were inspected: C4 contains both legs, T2 and host parity contain successful lint/render audits, and T3 contains executed root and offline suites. The C5 scanner's result is narrower than its title: it only says no new test file was added (`gate-logs/C5-prod-path.log:10`). C5 above therefore relies on inspection and execution of the modified tests against production, not on that scanner as proof of coverage. T4 remains deferred, not verified.

The prior-art investigation queried GitHub's `main` commit history by every one of the 14 affected paths and enumerated all 254 closed PRs. The only closed-unmerged PR was #4, which overlaps README solely by adding an enforcement-probe comment; its patch is captured in `review-prior-art.log:145`. PR #410 has no changed files, consistent with the brief's scaffold-only account (`review-prior-art.log:144`). The complete history of `autoiterate.py` returned three pre-ledger changes. This investigation found no semantic upstream-ahead conflict requiring a human disposition.

For T5, the independent probe deferred a real missing-review item beside a failing gate, then supplied a successful review and passing gate results and reassembled the summary. Fresh findings were empty; the original deferred row still appeared in `accept_blockers` (`review-infra-policy.log:2`). This is the behavior the carry-forward expressly leaves for human policy judgment, not a newly asserted implementation defect. The available template `INTEGRATION.md` §4 contains only a TODO for additional project-specific human-only items (`template/docs/INTEGRATION.md.jinja:80`).

### Advisory — adversary

# Adversarial review — issue 409 (iteration 4)

I re-ran the tests and tried to break this round's three retirement fixes. All three hold. I found two gaps next to them, both of which fail safe. Both need a human decision, not a rebuild.

## Findings

- NEEDS-HUMAN — **The accept guard (C6) still reads the FIRST §6 heading, which the patch itself says can belong to a leaf.** See `template/src/pdca_harness/flow.py:233` (`accept_blockers` → `signoff.open_needs_human` with no `last`) and `template/src/pdca_harness/signoff.py:170` (`ensure_needs_human_item`, first heading). The patch's own docstring at `signoff.py:138-145` says the first `## 6. NEEDS-HUMAN` heading can be a block a leaf quoted into §5. It switched only the two retirement readers to the last heading.
  - Concrete case, run against the patched code: a SUMMARY whose §5 holds a quoted `## 6. NEEDS-HUMAN` block with only `- [x] something old`, and whose real §6 holds `- [ ] <deferred finding>`. `flow.accept_blockers(d)` returns `[]`, so the accept goes through. `open_needs_human(..., last=True)` on the same file correctly returns the open row.
  - Second case: with the ledger unreadable, `ensure_needs_human_item` writes the unreadable-ledger row into the quoted block inside §5, not the real §6. C6 still blocks, because it reads the same wrong block. But the human is refused over a row that isn't in the §6 they are looking at.
  - The first-heading C6 read was already there on `main` (base `_section` breaks on the first match). This diff makes it matter more: the brief's goal is that every deferred finding "still reaches the human under the C6 guard", and deferred findings no longer halt the loop before handover.
  - Both readers have to move together. Moving only `ensure_needs_human_item` to the last heading would make C6 miss the row, so it would fail open.
  - Changing which §6 C6 reads touches every accept, so the human should decide on scope.

- NEEDS-HUMAN — **An open fresh near-twin blocks the retirement of a deferred finding the human ticked exactly, and no test pins this either way.** See `template/src/pdca_harness/autoiterate.py:386-390`. The docstring at `:357-358` treats a fresh row left open as a possible edit, so it protects every ledger entry it fuzzy-matches.
  - Concrete case, run against the patched code: ledger `["the fix does not cover the retry path"]`, §6 `- [x] the fix does not cover the retry path` plus the fresh `- [ ] the fix does not cover the CLI path`, `fresh=[that CLI row]`. `retire_cleared` keeps the entry, so it comes back unticked next round.
  - This is the #335 symptom (an entry the human cleared keeps coming back), now across the ledger/fresh boundary. It contradicts the module's own rule at `autoiterate.py:107-110` ("A row equal to one assembly rendered is that row — never an edit of another"). It also contradicts the brief's clause 3: "a near-twin cannot shield its exactly-ticked neighbour".
  - `docs/07-crosscutting.md:458-465` lists when an entry survives a tick, but not this case.
  - It fails safe: the entry is shown again, never lost. Whether that nuisance is acceptable is a design call.
  - Either way the choice is not pinned. I changed the code so that an open row exactly equal to a fresh rendered row protects nothing in the ledger, and all 152 tests still pass. Whichever direction the human picks needs a test.

## Notes (no action needed)

- `test_a_quoted_tick_retires_nothing_on_an_auto_iterate_round` (`template/tests/test_autoiterate.py:1304`) still passes when the tick reader goes back to the first heading. The open-row protection saves the entry, so the test fails only if both readers go back. The unit test at `:1101` catches each reader going back on its own, so the fix is still covered.
- The C5 gate row in `check-gates.json` says `pass`, but its log says "patch adds no new test file — nothing to assert". The gate checked nothing. I confirmed the substance separately: the tests call `autoiterate.retire_cleared`, `driver.advance`, `flow._maybe_auto_iterate` and `cli`/`flow` accept paths directly, and the mutations below prove they exercise production code.

## Refutation attempts that failed

- **Red→green evidence:**
  - I re-ran `tests.test_autoiterate` and `tests.test_size_signal` on a copy of the patched tree: 152 tests, OK.
  - The C4 red leg (`gate-logs/C4-verify.log`) shows 25 failures and 36 errors. 34 of the errors are `AttributeError` on new symbols, which the brief allows. The assertion failures are on the old veto behaviour (`0 != 3` fired rounds, `False is not true` for defer).
  - `test_size_signal` passes on both legs. As the brief says, those are fixture updates, not a red leg.
- **Tests that would pass for the wrong reason:** I tried 17 separate changes to production code (mutations), and every one broke at least one test:
  - reverting the tick reader or the open-row reader to the first heading;
  - dropping the label-equality check before the length floor;
  - ignoring `fresh`;
  - letting a hit on a fresh row retire an entry;
  - fuzzy-matching only against the ledger;
  - removing the exact-first step;
  - making protection flat;
  - removing the ratio or the floor;
  - removing label stripping;
  - removing retirement from `driver.advance`;
  - putting back the CLI's own C6 check;
  - removing `ensure_needs_human_item` from `accept_blockers`;
  - turning off assembly dedup;
  - deferring STANDING rows.
- **Is the last §6 heading really the assembled one?** Yes:
  - The only thing after §6 is fixed text, the §9 fields, and §10 lines built by the harness (`assemble.py:419-440`).
  - §6 rows are single lines (`assemble.py:730-733`).
  - The flow flattens the §9 delta (`flow.py:181-182`). `pdca signoff --delta` is not flattened (`cli.py:1465`), but that text is the human's own.
- **Can `fresh` drift from what assembly rendered?** Both come from `collect_needs_human`, and nothing it reads changes between assembly and the iterate beat in normal use. Any failure while working out `fresh` is caught at `driver.py:336-340` and leaves the ledger as it was, so it fails closed.
- **Size-by-kind stop, hard cap, both accept paths sharing one guard, the unreadable ledger blocking auto-iterate before any budget is spent:** I could not break any of these.

### Advisory — code-review

# Code review (advisory) — issue 409 / autoiterate-budgets-defer-ledger, round 4

Scope: correctness bugs this patch introduces, plus reuse/simplification. All gates in
check-gates.json pass (C4 is red before the fix and green after, per gate-logs/C4-verify.log;
T4 is deferred to publish). The three iteration-3 carry-forward fixes are in and tested: the
tick reader uses the last §6 heading (`test_a_section6_quoted_by_a_leaf_is_not_the_humans`,
`test_a_quoted_tick_retires_nothing_on_an_auto_iterate_round`); a tick equal to a fresh
rendered row never retires a ledger entry (`test_a_tick_on_a_fresh_finding_never_retires_a_deferred_one`,
three repro pairs plus the driver wiring test); and `_same_finding` checks equality after
stripping shared labels, before the floor (template/src/pdca_harness/autoiterate.py:177-181).
I found no new correctness bug in the retirement logic, the ledger read/write, or the
`eligible()` / `write_decision` ordering.

## Findings

- NEEDS-HUMAN — template/src/pdca_harness/signoff.py:102 (`open_needs_human`, default `last=False`)
  and template/src/pdca_harness/flow.py:262 (`accept_blockers`). The patch finds and
  documents a problem: a leaf can quote a `## 6. NEEDS-HUMAN` heading into §5, above the
  real §6 (signoff.py `cleared_needs_human` docstring, :128). The patch fixes only the
  retirement readers. The C6 accept guard still reads the FIRST §6 heading. So an artifact
  that quotes an empty or all-ticked §6 block makes `accept_blockers` report no open rows,
  while the real §6 below still has open ones. That is fail-open on accept. Your own test
  `test_a_section6_quoted_by_a_leaf_is_not_the_humans` (template/tests/test_autoiterate.py:1116-1118)
  builds exactly this SUMMARY shape. The first-heading read existed before this patch.
  But the patch now routes every accept path through `accept_blockers` (cli.py:1450,
  flow.py:176), and it states in code that the first heading can belong to a leaf. The
  human should decide whether to fix C6 here or in a follow-up issue. The fix is not just
  `last=True` in one place: `ensure_needs_human_item` (next bullet) must read the same
  section as the C6 check, or an added row becomes invisible to it.
- template/src/pdca_harness/signoff.py:170 (`ensure_needs_human_item`) writes the
  unreadable-ledger row into the FIRST §6 heading. When a leaf quoted a §6 block, the row
  lands inside the quoted adversary text in §5, not in the real §6. It still blocks accept,
  because C6 reads the same first block. So this is consistent, but the human will find
  the row in the wrong place. The dedup check at :174-178 also misses the copy assembly
  already put in the real §6 (assemble.py `_deferred_needs_human`), so the row shows up
  twice. This should be fixed together with the item above, not alone.
- template/src/pdca_harness/assemble.py:463,466 (`_deferred_needs_human`) re-implements
  `autoiterate._norm` inline (`" ".join(t.split()).casefold()`), even though it already
  imports `autoiterate` locally two lines earlier. signoff.py:174-178 does the same with
  `autoiterate._row_text` / `_BOXES`. Assembly's dedup and `retire_cleared`'s `rnorm` dedup
  (autoiterate.py:376-381) must agree, or a fresh copy of an entry renders twice and its
  tick becomes a two-hit, fail-closed match. Calling `autoiterate._norm` in assemble keeps
  the two in step. signoff cannot import autoiterate (that would create an import cycle),
  so there the inline copy is acceptable. Low priority; no behaviour change today.
- template/src/pdca_harness/autoiterate.py:291-294 (`_write_ledger`): if `tmp.write_text`
  raises partway through (for example, a full disk), the `.deferred-findings.json.<pid>.tmp`
  file stays in the bundle. It is harmless: nothing globs it, and `DOWNSTREAM_GLOBS` does
  not match it. A `try/finally` that unlinks the temp file on failure would tidy this up.
  Cosmetic.

No other findings. The CLI accept path is safe on a SUMMARY with no §6. `accept_blockers`
cannot add the row there, but `signoff.record` then refuses the SUMMARY (signoff.py:223,
:241-246), so an accept is never recorded.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Decide whether recovered infrastructure findings should still require explicit clearance at handover — the independent probe shows a missing-review finding remains an accept blocker after fresh review/gate findings become empty, adding historical recovery work to sign-off (`template/src/pdca_harness/assemble.py:260`, `template/src/pdca_harness/autoiterate.py:310`; `review-infra-policy.log:4`).
- [x] Validation — fitness-to-purpose — Judge whether deferring human concerns until bounded handover provides sufficient oversight in real operation — the exercised preservation rules cannot establish the quality or workload of that human review (`docs/07-crosscutting.md:445`, `docs/07-crosscutting.md:465`).
- [ ] **The accept guard (C6) still reads the FIRST §6 heading, which the patch itself says can belong to a leaf.** See `template/src/pdca_harness/flow.py:233` (`accept_blockers` → `signoff.open_needs_human` with no `last`) and `template/src/pdca_harness/signoff.py:170` (`ensure_needs_human_item`, first heading). The patch's own docstring at `signoff.py:138-145` says the first `## 6. NEEDS-HUMAN` heading can be a block a leaf quoted into §5. It switched only the two retirement readers to the last heading.
- [ ] **An open fresh near-twin blocks the retirement of a deferred finding the human ticked exactly, and no test pins this either way.** See `template/src/pdca_harness/autoiterate.py:386-390`. The docstring at `:357-358` treats a fresh row left open as a possible edit, so it protects every ledger entry it fuzzy-matches.
- [ ] template/src/pdca_harness/signoff.py:102 (`open_needs_human`, default `last=False`) and template/src/pdca_harness/flow.py:262 (`accept_blockers`). The patch finds and documents a problem: a leaf can quote a `## 6. NEEDS-HUMAN` heading into §5, above the real §6 (signoff.py `cleared_needs_human` docstring, :128). The patch fixes only the retirement readers. The C6 accept guard still reads the FIRST §6 heading. So an artifact that quotes an empty or all-ticked §6 block makes `accept_blockers` report no open rows, while the real §6 below still has open ones. That is fail-open on accept. Your own test `test_a_section6_quoted_by_a_leaf_is_not_the_humans` (template/tests/test_autoiterate.py:1116-1118) builds exactly this SUMMARY shape. The first-heading read existed before this patch. But the patch now routes every accept path through `accept_blockers` (cli.py:1450, flow.py:176), and it states in code that the first heading can belong to a leaf. The human should decide whether to fix C6 here or in a follow-up issue. The fix is not just `last=True` in one place: `ensure_needs_human_item` (next bullet) must read the same section as the C6 check, or an added row becomes invisible to it.
- [x] **The default size backstop means the Goal's budget can never be the binding limit, and the brief does not say so.** The Motivation says the problem is that "the round budget … is never the constraint that binds", and clause (1)'s worked example depends on rounds 4–5 happening. But `size_signal.DEFAULT_THRESHOLDS["rounds"] = 2` (`size_signal.py:73`). Clause (4) keeps "a size-backstop item makes `eligible()` false". So on a default instance the third Check (2 archives) raises the size item and the loop stops at 2 rounds, whatever `soft_auto_iters` or `max_auto_iters` is set to. `test_size_signal.py:179-187` pins this ordering, and `pdca.toml.jinja:292` documents it. The brief puts "how size-signal counts rounds (#477)" out of scope, so after this change `soft_auto_iters`/`max_auto_iters` above 2 still do nothing unless `[size_signal].rounds` is raised or set to 0. That applies to the default of 3 too, and to the 3/5 example. The unit criterion can pass while the stated Goal is not delivered. The brief should do three things: say this plainly, document in `pdca.toml.jinja` next to `soft_auto_iters` that the key only matters once `size_signal.rounds` is raised, and add `pdca.toml.jinja:289-293` (whose comment states the old rule) to the edit list. Otherwise it should explain why #477 is not a prerequisite.
- [x] **The ticked-rows reader's `whole_on_missing=True` points the safe direction the wrong way.** Clause (3) requires the new reader to call `signoff._section(..., whole_on_missing=True)` "the lenient §6 side, matching `open_needs_human`". That leniency is safe for `open_needs_human` only because scanning the whole document finds more `- [ ]` rows and so blocks accept harder (`signoff.py:108-111`, `:237-238`). A reader that looks for `- [x]` rows gets the opposite effect: with no §6 heading, every ticked checkbox anywhere in SUMMARY is treated as a tick. That includes checkboxes quoted in §5 review text, which is pasted in verbatim at `assemble.py:395`. Each such tick retires a ledger entry, so an unreviewed deferred finding can be lost. That is exactly the kind of loss the ledger is meant to prevent. The open-row side (protection) should stay lenient. The tick side should be `whole_on_missing=False`, so a missing §6 retires nothing. `unrecordable()` (`signoff.py:154-156`) makes this path hard to reach today. But the brief makes `True` a binding contract, and the reasoning it gives for it is wrong. The thread imposed this constraint, so a human should decide rather than the planner quietly changing it.
- [x] **Clause (4)'s named test cannot go red first.** The criterion says "Both directions of `test_the_tag_is_the_mechanism` (`test_size_signal.py:280`) pass", and Falsifiability (4) calls the "ordinary HUMAN beside IMPL fires" case a direction of that test. It is not one. The test's two directions are size-text HUMAN → False and size-text IMPL → True (`test_size_signal.py:285-290`), and both already pass on `main`. The only failing leg in clause (4) is the new "[IMPL, ordinary HUMAN] → True" case, which is clause (2)'s change. Nothing in clause (4) fails today, so the check cannot tell apart a size-by-kind composition from the naive `any(IMPL)` that would drop the backstop entirely. The brief should require one new test that fails against a plain `any(item.kind == IMPL)`, for example `[IMPL, ordinary HUMAN, size HUMAN] → False` next to `[IMPL, ordinary HUMAN] → True`. It should also stop claiming that `:280` provides the failing leg.
- [x] **The convergence baseline ("every Check that reaches the auto-iterate decision, including declines") has no definition, so clause (1) can't be checked at its edges.** `_maybe_auto_iterate` can decline in five places before or at the budget check: auto-iterate off or not at AWAITING_SIGNOFF (`flow.py:296`), a decision already recorded (`:303-307`), `collect_needs_human` raised (`:308-317`), ineligible (`:318-330`), and budget spent (`:331-335`). The brief doesn't say which of these record an IMPL count. One case changes the result. A HUMAN-only decline records IMPL=0 and the human then iterates by hand. Above soft, any later Check with IMPL ≥ 1 is then an "increase", so auto-iterate never fires again even though the budget is left. The brief should list which decline paths observe a count, and say whether a human-driven iterate resets the baseline. A test should pin both.
- [x] **The scope is two independent changes plus a bug fix, and the brief admits it.** The Open questions say "the natural cut is budgets (clause 1) vs defer+ledger (clauses 2–4)". Clause (1) (`config.py`, the `auto-iterate.json` shape, `flow.py:331-335`) shares no mechanism with the ledger, retirement or `_apply_decision` work. The thread does scope both under #409, so this is not smuggled in. But leaving the split to "the sizing prompt" means the review load is already set. The change touches 9 source files, the jinja template, 2 docs and 2 test modules, and it adds a gate at `_apply_decision` that runs on every sign-off, not only with auto-iterate on. The finding above also makes clause (1) almost unobservable on default settings. So the split should be decided at Plan: ship defer+ledger (which fixes the 13.5% veto the Motivation measures) and hold the budgets until #477 settles how size-signal counts rounds.
- [ ] size backstop — this slice is behaving oversized: patch is 138 KB (threshold 125 KB); 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Iteration delta (if iterating): Design stays as-is. Rebuild to fix two gaps from the iteration-4 review (§6 rows 3/5 and 4) and apply one policy ruling (row 1): 1. C6 accept guard reads the FIRST `## 6. NEEDS-HUMAN` heading (fails open). `flow.accept_blockers` -> `signoff.open_needs_human` (signoff.py:102, default `last=False`; flow.py:233/:262) and `signoff.ensure_needs_human_item` (signoff.py:170) still read the first heading, which a leaf can quote into §5. Move BOTH to the last (real, assembled) §6 heading together — moving only one makes the unreadable-ledger row invisible to C6. Fix the ensure_needs_human_item dedup (:174-178) so it sees the copy assembly already put in the real §6 (no duplicate row). Tests: a SUMMARY whose §5 quotes an all-ticked §6 block while the real §6 has an open row -> accept_blockers is non-empty on both the flow and `pdca signoff --accept` paths; with an unreadable ledger, the row lands in the real §6, once. 2. Fresh near-twin shields an exactly-ticked ledger entry (autoiterate.py:386-390). Rule (matches brief clause 3 "a near-twin cannot shield its exactly-ticked neighbour" and autoiterate.py:107-110): an open row exactly equal to a row assembly rendered from a FRESH finding is that fresh finding, not an edit of a ledger entry, so it protects nothing in the ledger. Pin it with a test: ledger ["the fix does not cover the retry path"], §6 `- [x]` that row + fresh open `- [ ] the fix does not cover the CLI path` -> entry is retired. Keep the fail-closed protection for genuinely edited open rows. 3. Policy ruling (human, sign-off): stale/recovered infrastructure findings (missing-review placeholder, gate-could-not-run) must NOT need hand clearance at handover. Once a later round's review/gates have recovered (the fresh finding is gone), drop that infra entry from the ledger instead of re-entering it in §6. Ordinary HUMAN findings still defer and still need a tick. Test: a deferred missing-review row, then a successful review + passing gates -> it no longer appears in §6 or accept_blockers. Ruled, do not reopen: deferring human concerns to bounded handover is enough oversight (fitness-to-purpose). Size backstop (138 KB / 3 rounds) was weighed and overridden by the human: one mechanism converging, not an oversized slice — do not split. Cosmetic, optional: use autoiterate._norm in assemble._deferred_needs_human instead of the inline copy.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
