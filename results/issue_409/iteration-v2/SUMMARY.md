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

Review issue #409: allow bounded automatic rebuilds alongside human findings, preserving those findings through handover and retiring only positively cleared entries, including the #335 retirement fix.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The approved scope gives falsifiable outcomes for mixed findings, both existing stops, persistence and conservative retirement; the iteration adds two specific regression obligations without reopening the dropped soft budget (brief.md:26; brief.md:226). |
| C2 Reproduction (red pre-fix) | PASS | Keeping the changed tests while stashing production changes reproduced 21 failures and 20 errors across 143 tests, including the mixed-findings veto and missing ledger behavior; these are executed test failures, not collection failures (review-red.log:523; template/tests/test_autoiterate.py:670). |
| C3 Change | PASS | Deferred findings remain visible at handover and require human clearance, while retirement precedes either archive transition; the change stays within the approved mechanism and supporting documentation (template/src/pdca_harness/assemble.py:359; template/src/pdca_harness/driver.py:135; template/src/pdca_harness/flow.py:176). |
| C4 Verification (red→green) | PASS | Restoring the production changes made the same 143 tests pass; both iteration-specific tests also reject their intended faulty mutations, substantiating the added retirement safeguards (review-green.log:73; review-mutations.log:91; review-mutations.log:125; template/src/pdca_harness/autoiterate.py:135; template/src/pdca_harness/autoiterate.py:326). |
| C5 Causal adequacy | PASS | The blanket HUMAN veto is removed at the eligibility decision, and ledger persistence addresses loss across archival; no optional-capability probe or load-time symptom guard is introduced (template/src/pdca_harness/autoiterate.py:170; template/src/pdca_harness/autoiterate.py:369; template/src/pdca_harness/state.py:174). |
| T1 Structure | PASS | The existing assembly, decision and archive boundaries own the lifecycle, with one matching relation for retirement and open-row protection; strict tick extraction avoids treating a missing §6 as clearance (template/src/pdca_harness/autoiterate.py:315; template/src/pdca_harness/signoff.py:123; template/src/pdca_harness/driver.py:317). |
| T2 Shape | PASS | Independent whitespace checks, docs lint and a 22-page render/link audit passed, confirming the changed explanations and links satisfy the repository checks (docs/07-crosscutting.md:434; gate-logs/T2-docs.log:11; gate-logs/host-ci-docs.log:11). |
| T3 Runtime | PASS | The independent driver suite passed 2,121 tests with two skips; frozen evidence additionally records 24 passing root render/update tests, while local root reproduction lacks importable Copier (review-suite.log:1670; gate-logs/T3-suite.log:39; gate-logs/T3-suite.log:54; review-root-suite.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; the deferred gate explicitly assigns the substantive audit to publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior art across merged and closed/rejected work before accepting a duplicate or previously rejected approach — the brief records a partial path-based search, but this copy has only one synthetic base commit, no remotes and no independent closed-PR evidence (brief.md:151). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether deferring architectural, scope and environmental objections until bounded handover is acceptable for unattended operation — the lifecycle tests establish preservation and accept blocking, but cannot establish that rebuilding before those judgments is useful for operators (docs/07-crosscutting.md:447; template/tests/test_autoiterate.py:700). |

Source paths above are relative to `$PDCA_TARGET` (`target/`); brief and evidence paths are relative to this review directory. The target is readable and matches the supplied patch. Its restored `git diff --binary` is byte-for-byte identical to `patch.diff`; there is no target-state mismatch.

Independent verification:

- Stashed only `template/src/pdca_harness`, leaving the new tests and configuration documentation present, then ran `PYTHONPATH=src python3 -m unittest tests.test_autoiterate tests.test_size_signal` from `target/template`. The red run failed as detailed above. Popped the stash and repeated the identical command: all 143 tests passed. Temporary test files were directed inside this review directory.
- Ran `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`: 2,121 tests passed, two skipped. Full output is in `review-suite.log`.
- Applied two faulty variants only to imported functions in memory, without editing target source: allowing short containment matches made `test_a_short_row_matches_only_exactly` fail four subcases; allowing ambiguous ticks to retire the first match made `test_a_tick_matching_two_entries_retires_neither` fail. Both produced assertion failures, no errors (`review-mutations.log`).
- Ran `git diff --check`, `python3 docs/publishing/tools/lint_docs.py`, and `python3 docs/publishing/tools/render_site.py --check --out ../review-site` from `target`: all passed. This independently reproduces the checks shown by both frozen docs gates.
- Re-ran the shipped production-import scanner. Its scope covers newly added test files; this patch only modifies existing tests, so its successful exit is not substantive production-path evidence. The frozen C5 log explicitly says the same (`gate-logs/C5-prod-path.log:10`). The red→green run and mutation checks provide that evidence here.
- Attempted `python3 -m tests.run_root_suite`: exit 77, because this interpreter cannot import Copier. This is a reviewer-host limitation, not a patch failure or an unmet dependency in the frozen run: `gate-logs/T3-suite.log` explicitly records successful real render and update cases followed by 24 passing root tests. The brief declares no external dependencies. No additional project human-only criteria are enumerated in the supplied integration template (`template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation: path-filtered `git log --all` returned only `0474a5e pre-fix base 940565897e0df93e11c20c0d7ea76ac5ffa803ca`; `git remote -v` returned nothing. The brief's recorded history search names autoiterate/config/state, but does not provide independently inspectable merged and closed/rejected evidence for the remaining affected paths. This limitation belongs to T5, not C4.

No confirmed patch defect found. This review is advisory; the two human decisions above remain owed.

### Advisory — adversary

# Adversarial review — issue 409 / autoiterate-budgets-defer-ledger

The red→green evidence holds up, and the tests drive production code. I did break the fix in
two places: the shipped matcher treats two unrelated findings as the same one, and one
sign-off path skips the new unreadable-ledger guard. There are also stale comments and one
design question for the human.

## Refutations that landed

- NEEDS-HUMAN [impl] — `_same_finding` counts two **unrelated** findings as the same one when all they share is the canonical 5/5/1 label and the shorter one is short (template/src/pdca_harness/autoiterate.py:144; the reasoning at :91-100 assumes the label is "a small fraction of a full §6 row"). The floor (20) is shorter than the labels themselves: `"C5 Causal adequacy — "` is 21 chars and `"Validation — fitness-to-purpose — "` is 34. `int(shorter * 0.6)` only gets past the label once the shorter row is longer than about 35 / 57 chars. Checked on the patched tree: `_same_finding("C5 Causal adequacy — symptom only", "C5 Causal adequacy — patches the wrong layer entirely")` → True, and `"Validation — fitness-to-purpose — wrong layer"` vs `"Validation — fitness-to-purpose — the docs overclaim the guarantee"` → True. End to end through `retire_cleared`: ledger `[V1]`, the human deletes V1's row and ticks the unrelated fresh V2 → **V1 is retired**. That fails open, the same "absence is not consent" class as iteration-1 item 7. The other direction: V1 ticked exactly, unrelated V2 left open → V1 is kept and comes back unticked next round. The ratio rule is also untested: replacing line 144 with `return shared >= _MATCH_FLOOR` still passes all 143 tests in test_autoiterate + test_size_signal. Fix idea: measure the shared opening only past a common canonical `Item —` prefix, and add a test with two different findings on one element where one of them is short.

- NEEDS-HUMAN [impl] — `pdca signoff <id> --accept` skips the unreadable-ledger hold. template/src/pdca_harness/cli.py:1446-1451 runs its own C6 check (`signoff.open_needs_human`) and never calls `flow._hold_unreadable_ledger` (flow.py:216). So brief clause 2 ("blocks an accept, on the shared decision path every sign-off uses") is false on this path. Repro on the patched tree: clean bundle, auto_iterate off, write `{"items": ["a held finding", 7]}` to deferred-findings.json after assembly, call `cli._signoff(cfg, Namespace(accept=True, …))` → exit 0, state COMPLETE, no §6 row added. This contradicts flow.py:221 ("the one decision path every sign-off takes") and docs/07-crosscutting.md:462 ("an accept is refused until you clear it"). Fix: run the same hold before the C6 check in `cli._signoff` (or share one helper), and add a test on the CLI path.

- NEEDS-HUMAN [impl] — three comments near `collect_needs_human` still describe the old veto and contradict the new rule and the builder's own tests. assemble.py:246-248 says "an infra-empty must never be auto-iterated (#264)", but `test_a_missing_review_beside_a_red_gate_is_deferred` (test_autoiterate.py:696) pins the opposite. assemble.py:278-279 says "rebuilding would spin against the same missing mechanic", but an unverifiable gate beside a red gate now rebuilds. assemble.py:302-303 says plan-advisory findings make "auto-iterate correctly decline(s)", but they now defer. The patch updated only the :307-311 comment that the brief named.

- NEEDS-HUMAN — short-lived infra rows get deferred and shown again at handover as if they were current. The missing-review placeholder (assemble.py:545-551: "no check-review.md was produced … see `review.error.log` in this bundle … re-run the Check reviewer before accepting") goes into the ledger when a reviewer failure sits beside a red gate. It comes back word for word in the handover §6 even after a later round produced a real review and the error log was archived with its round. Gate-could-not-run rows behave the same way. Deferred rows don't say which round raised them, so the human can't tell a stale infra row from a live one. This also drops the #264 rule that an infra-empty review never auto-iterates: a reviewer that fails every round now uses up rounds on gate feedback alone, until the size backstop or the cap stops it. The brief's "HUMAN items defer" covers this if read literally, but it is a design call: should placeholder / unverifiable items be deferred, left out like STANDING, or still veto?

## Tried and could not refute

- **C4 red→green:** reproduced on a scratch copy. Base production files + patched tests → test_autoiterate: 87 tests, 21 failures + 20 errors (the same as gate-logs/C4-verify.log). Patched tree → 143 OK. test_size_signal is green on both legs, which the brief expects (fixture changes only, not a red leg). T3 log: 2121 driver tests OK.
- **Production path:** the tests call `flow._maybe_auto_iterate`, `flow._apply_decision`, `driver.advance`, `assemble.assemble_summary` and `autoiterate.retire_cleared` directly, not a copy. C5's "pass" in check-gates.json proves nothing on its own ("patch adds no new test file — nothing to assert"), so I checked this by hand.
- **Mutation testing, 16 of 17 caught:** symmetric-fuzzy protection, exact-only protection (#335), retiring the first fuzzy hit (`len(hits) == 1`), containment below the floor, naive `any(IMPL)`, a lenient tick reader (`whole_on_missing=True`), no dedup at assembly, retirement removed from either iterate branch, the accept hold removed, bump before defer, tier-2 protecting only one match, ticks always matched fuzzily, non-string ledger entries filtered out, STANDING deferred, the `- (none` placeholder kept. Only removing the ratio survived (first bullet).
- **Split parents:** split.py:978 archives the parent without retiring anything. The parent still goes CHECKED → `assemble_summary` (driver.py:130), though, so its ledger entries show in its §6 and block accept. Nothing is lost.

### Advisory — code-review

# Code review — issue 409 (advisory)

Lens: bugs the patch introduces, plus reuse and simplification. No blocking defect found. The two carry-forward gaps from iteration 1 are closed and tested: the floor now bounds containment (`template/src/pdca_harness/autoiterate.py:134-138`, test at `template/tests/test_autoiterate.py:1014`), and the "more than one fuzzy hit retires nothing" rule is pinned (`template/tests/test_autoiterate.py:999`). The gate logs agree: C4 is red before the fix and green after, and T3 ran 2121 tests OK.

- NEEDS-HUMAN — `template/src/pdca_harness/autoiterate.py:249-271` (`defer`) records every HUMAN item a round passes, including items the harness re-derives from scratch each round: "gate could not run" rows (`assemble.py:280`), refuted-dependency rows, and reviewer rows whose wording changes between rounds. A round-1 "gate X unverifiable" that a later round fixes still reaches the handover §6 as an open box. Each rewording of the same objection becomes its own ledger entry, because dedup is exact-only on purpose (`assemble.py:429-453`). The count is bounded by `max_auto_iters`, so this is noise, not loss. The brief asks for exactly this ("every deferred finding is an open `- [ ]` item"). The human should still decide whether mechanically re-derived HUMAN rows should be deferred at all, or only reviewer/advisory judgment rows.
- `template/src/pdca_harness/assemble.py:446` and `:449` repeat the whitespace-collapse + casefold normalisation that `autoiterate._norm` (`autoiterate.py:105`) already provides, and the function already imports `autoiterate` locally (`assemble.py:440`). `signoff.ensure_needs_human_item` repeats the same normalisation and the checkbox list (`signoff.py:159`, `:163-164`; compare `autoiterate._BOXES` / `_row_text` at `autoiterate.py:102-117`). Today all three copies behave the same, but the exact-dedup, exact-retire and no-duplicate-row checks only line up while they stay identical. A simple fix: move `_norm`/`_row_text` into `signoff`, which `autoiterate` already imports, and call them from all three places. Cleanup only, not a bug.
- `template/src/pdca_harness/autoiterate.py:243-246` (`_write_ledger`): if `tmp.write_text` fails partway (for example, disk full), the `.deferred-findings.json.<pid>.tmp` sibling stays in the bundle directory. Nothing reads it, so the only cost is a stray file. A `try/except` that unlinks the temp file before re-raising would close it. Low severity.

Also checked, no problem found: `retire_cleared`'s exact-first `protected` set and its tick loop (`autoiterate.py:317-333`, the ticked-rows read at `:315`); the strict tick reader against the lenient open reader (`signoff.py:124-141` vs `:102-120`); retirement placed between the carry-forward and the archive in both iterate branches (`driver.py:135`, `:141`); an unreadable ledger raising before any budget is spent (`defer` first at `autoiterate.py:369`), with the flow catching it (`flow.py:359-367`); and the accept-path ledger check running before C6 (`flow.py:176-177`). `STANDING` items are never written to the ledger (`kind != HUMAN` at `autoiterate.py:264`).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm affected-path prior art across merged and closed/rejected work before accepting a duplicate or previously rejected approach — the brief records a partial path-based search, but this copy has only one synthetic base commit, no remotes and no independent closed-PR evidence (brief.md:151).
- [ ] Validation — fitness-to-purpose — Decide whether deferring architectural, scope and environmental objections until bounded handover is acceptable for unattended operation — the lifecycle tests establish preservation and accept blocking, but cannot establish that rebuilding before those judgments is useful for operators (docs/07-crosscutting.md:447; template/tests/test_autoiterate.py:700).
- [ ] `_same_finding` counts two **unrelated** findings as the same one when all they share is the canonical 5/5/1 label and the shorter one is short (template/src/pdca_harness/autoiterate.py:144; the reasoning at :91-100 assumes the label is "a small fraction of a full §6 row"). The floor (20) is shorter than the labels themselves: `"C5 Causal adequacy — "` is 21 chars and `"Validation — fitness-to-purpose — "` is 34. `int(shorter * 0.6)` only gets past the label once the shorter row is longer than about 35 / 57 chars. Checked on the patched tree: `_same_finding("C5 Causal adequacy — symptom only", "C5 Causal adequacy — patches the wrong layer entirely")` → True, and `"Validation — fitness-to-purpose — wrong layer"` vs `"Validation — fitness-to-purpose — the docs overclaim the guarantee"` → True. End to end through `retire_cleared`: ledger `[V1]`, the human deletes V1's row and ticks the unrelated fresh V2 → **V1 is retired**. That fails open, the same "absence is not consent" class as iteration-1 item 7. The other direction: V1 ticked exactly, unrelated V2 left open → V1 is kept and comes back unticked next round. The ratio rule is also untested: replacing line 144 with `return shared >= _MATCH_FLOOR` still passes all 143 tests in test_autoiterate + test_size_signal. Fix idea: measure the shared opening only past a common canonical `Item —` prefix, and add a test with two different findings on one element where one of them is short.
- [ ] `pdca signoff <id> --accept` skips the unreadable-ledger hold. template/src/pdca_harness/cli.py:1446-1451 runs its own C6 check (`signoff.open_needs_human`) and never calls `flow._hold_unreadable_ledger` (flow.py:216). So brief clause 2 ("blocks an accept, on the shared decision path every sign-off uses") is false on this path. Repro on the patched tree: clean bundle, auto_iterate off, write `{"items": ["a held finding", 7]}` to deferred-findings.json after assembly, call `cli._signoff(cfg, Namespace(accept=True, …))` → exit 0, state COMPLETE, no §6 row added. This contradicts flow.py:221 ("the one decision path every sign-off takes") and docs/07-crosscutting.md:462 ("an accept is refused until you clear it"). Fix: run the same hold before the C6 check in `cli._signoff` (or share one helper), and add a test on the CLI path.
- [ ] three comments near `collect_needs_human` still describe the old veto and contradict the new rule and the builder's own tests. assemble.py:246-248 says "an infra-empty must never be auto-iterated (#264)", but `test_a_missing_review_beside_a_red_gate_is_deferred` (test_autoiterate.py:696) pins the opposite. assemble.py:278-279 says "rebuilding would spin against the same missing mechanic", but an unverifiable gate beside a red gate now rebuilds. assemble.py:302-303 says plan-advisory findings make "auto-iterate correctly decline(s)", but they now defer. The patch updated only the :307-311 comment that the brief named.
- [ ] short-lived infra rows get deferred and shown again at handover as if they were current. The missing-review placeholder (assemble.py:545-551: "no check-review.md was produced … see `review.error.log` in this bundle … re-run the Check reviewer before accepting") goes into the ledger when a reviewer failure sits beside a red gate. It comes back word for word in the handover §6 even after a later round produced a real review and the error log was archived with its round. Gate-could-not-run rows behave the same way. Deferred rows don't say which round raised them, so the human can't tell a stale infra row from a live one. This also drops the #264 rule that an infra-empty review never auto-iterates: a reviewer that fails every round now uses up rounds on gate feedback alone, until the size backstop or the cap stops it. The brief's "HUMAN items defer" covers this if read literally, but it is a design call: should placeholder / unverifiable items be deferred, left out like STANDING, or still veto?
- [ ] `template/src/pdca_harness/autoiterate.py:249-271` (`defer`) records every HUMAN item a round passes, including items the harness re-derives from scratch each round: "gate could not run" rows (`assemble.py:280`), refuted-dependency rows, and reviewer rows whose wording changes between rounds. A round-1 "gate X unverifiable" that a later round fixes still reaches the handover §6 as an open box. Each rewording of the same objection becomes its own ledger entry, because dedup is exact-only on purpose (`assemble.py:429-453`). The count is bounded by `max_auto_iters`, so this is noise, not loss. The brief asks for exactly this ("every deferred finding is an open `- [ ]` item"). The human should still decide whether mechanically re-derived HUMAN rows should be deferred at all, or only reviewer/advisory judgment rows.
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
- Iteration delta (if iterating): Design is right; fix three implementation defects the adversary review confirmed: 1. `_same_finding` (autoiterate.py:144) treats unrelated findings on the same element as one: the canonical 5/5/1 label ("C5 Causal adequacy — " = 21 chars) alone clears _MATCH_FLOOR (20). A tick on one can retire an unrelated, never-adjudicated ledger entry (fails open). Measure the shared opening only past a common canonical `Item —` prefix, and add a test with two different findings on one element where one is short. The ratio rule is untested today (`return shared >= _MATCH_FLOOR` passes all 143 tests) — pin it. 2. `pdca signoff <id> --accept` (cli._signoff, cli.py:1446-1451) runs its own C6 check and never calls `flow._hold_unreadable_ledger`, so an unreadable ledger does not block accept on that path — violates brief clause 2. Share one helper with `_apply_decision` and add a CLI-path test. 3. Stale comments in assemble.py (:246-248, :278-279, :302-303) still describe the old veto; update them to the defer rule. Open design question the human did not rule on (do not change behaviour for it this round): whether re-derived infra rows (missing-review placeholder, gate-could-not-run) should be deferred.
- By / date: Eduard Ralph / 2026-09-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
