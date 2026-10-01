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

Review issue #409: allow bounded automatic rebuilds alongside human findings, preserve those findings until handover, and retire only findings the human cleared.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The final contract distinguishes rebuild work, human clearance, recovered infrastructure, and the two existing stop rules; the iteration-4 rulings settle the earlier policy and scope questions (`brief.md:28`, `brief.md:283`, `brief.md:286`; `template/tests/test_autoiterate.py:707`, `template/tests/test_autoiterate.py:1087`). |
| C2 Reproduction (red pre-fix) | PASS | Independently retaining the changed tests while stashing production changes reproduces the ordinary-HUMAN veto and premature halt: 157 tests run, 30 failures and 41 missing-feature errors; actual assertions fail, not merely imports (`review-red.log:534`, `review-red.log:850`; `template/tests/test_autoiterate.py:1087`). |
| C3 Change | PASS | The final patch addresses the approved retention and clearance boundaries, including both accept entry points and fresh-versus-deferred near-twins; no new budget or unapproved policy change was found (`template/src/pdca_harness/flow.py:211`, `template/src/pdca_harness/cli.py:1448`, `template/src/pdca_harness/autoiterate.py:407`; `brief.md:283`). |
| C4 Verification (red→green) | PASS | Restoring the stashed production changes makes all 157 tests pass, including quoted-section accept guards, ledger retention, and both stop rules; the patch was byte-identical before and after stash restoration (`review-green.log:86`; `template/tests/test_autoiterate.py:986`, `template/tests/test_autoiterate.py:1020`, `template/tests/test_autoiterate.py:1296`). |
| C5 Causal adequacy | PASS | The demonstrated veto is removed at the eligibility decision, while retention and clearance run through production assembly/driver/sign-off paths; no optional-capability probe or load-time symptom guard was added (`template/src/pdca_harness/autoiterate.py:221`, `template/src/pdca_harness/driver.py:314`, `template/tests/test_autoiterate.py:804`, `template/tests/test_autoiterate.py:1521`). |
| T1 Structure | PASS | Ledger lifetime remains separate from archived attempts, and shared acceptance/section readers keep CLI and flow clearance consistent; the new no-verdict flag retains existing constructor defaults (`template/src/pdca_harness/state.py:174`, `template/src/pdca_harness/assemble.py:42`, `template/src/pdca_harness/signoff.py:103`, `template/src/pdca_harness/flow.py:211`). |
| T2 Shape | PASS | Independent documentation lint, 22-page rendering/link audit, and diff whitespace checks pass; the documented handover behavior reflects the final policy (`review-docs-lint.log:1`, `review-docs-render.log:3`; `docs/07-crosscutting.md:448`). |
| T3 Runtime | PASS | Independent offline suite: 2,135 tests, OK with two skips; frozen root-suite evidence additionally shows actual render and update-compatibility cases passing, not skipped coverage (`review-suite.log:1683`; `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the captured deferred row assigns the substantive commit/PR audit to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior-art coverage for all 15 affected paths — the brief records a narrower three-path search, while this target has only a synthetic base commit and no remote, so duplicate or previously rejected work cannot be independently excluded (`brief.md:151`; `review-prior-art.log:3`, `review-prior-art.log:18`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Give final fitness sign-off for this implementation against the already accepted bounded-handover policy — the automated evidence verifies retention and clearance behavior, while the final suitability judgment remains human; this does not reopen the settled oversight or size ruling (`brief.md:286`; `template/tests/test_autoiterate.py:804`, `template/tests/test_autoiterate.py:1101`). |

Source citations beginning `template/`, `docs/`, or `README.md` are relative to `$PDCA_TARGET` (`/tmp/pdca-review-4243vs72/target`); brief, gate, and independent-run evidence paths are relative to this review directory. The target is readable and its applied patch supports the citations; no stale-target caveat was needed. No confirmed patch defect was found.

Independent verification used `PYTHONPATH=src python3 -m unittest tests.test_autoiterate tests.test_size_signal` in the target's `template/` directory, stashing all changed non-test paths for red and restoring them for green. `TMPDIR` pointed to the review scratch root; bytecode generation was disabled. The red run includes missing-symbol errors because the new ledger API does not exist on the base, but also 30 assertion failures demonstrating the behavioral mismatch. The full offline suite subsequently passed without further production changes.

The production-import scanner was rerun. Its added-file heuristic has no new test file to inspect here, as the frozen log explicitly states (`gate-logs/C5-prod-path.log:10`); its success alone is not causal evidence. The changed tests directly import and invoke production modules (`template/tests/test_autoiterate.py:38`), and the red→green rerun supplies the stronger evidence.

The instance-scoped gate wrappers were adjudicated using their captured commands and output, with available target checks rerun directly. Root render/update compatibility relies on the frozen log: this disposable target has no release tags for an independent prior-release update rerun (`review-prior-art.log:24`). The log explicitly records all five update cases and both render cases passing (`gate-logs/T3-suite.log:38`). This is a reviewer-copy limitation, not an unmet dependency in the recorded gate run. The brief declares no external dependencies (`brief.md:131`), and no shim or substituted toolchain was needed for the independently exercised change. The available integration template enumerates no additional human-only items beyond its TODO (`template/docs/INTEGRATION.md.jinja:80`).

The iteration-4 infrastructure policy is exercised through real collection, assembly, and flow transitions with controlled leaf outputs: recovered missing-review, reviewer-placeholder, advisory-placeholder, and unverifiable-gate rows disappear while ordinary human findings survive (`template/tests/test_autoiterate.py:707`). The prior human approval of bounded deferral and this slice's size is preserved.

### Advisory — adversary

# Adversarial review — issue 409 (iteration 5)

**Evidence re-run.** I rebuilt the red leg in a scratch copy: the test files kept, the 10
production files under `template/src/` reset to `HEAD`. `tests.test_autoiterate` +
`tests.test_size_signal` gave 30 failures + 41 errors. On the patched tree all 157 pass. That
matches `gate-logs/C4-verify.log`. The red failures are real assertion and attribute failures
(no `retire_cleared`, the veto still declining), not import noise.

**Mutation pass (my own, 27 single-line breaks of the fix).** 26 were caught by the new
tests. These include: the first vs last §6 heading in `_needs_human_section`
(`signoff.py:119`) and in `ensure_needs_human_item` (`signoff.py:187`); symmetric-fuzzy
protection; dropping the exact tier (`autoiterate.py:421`); ignoring `protected`; taking the
first of several hits; dropping the ratio or the floor; dropping label stripping; deferring
`no_verdict` rows (`autoiterate.py:322`); the CLI accept path's own C6 check; no retire on
iterate-plan; and `defer` after `bump`. The one survivor (`unrecordable` reading the first
vs the last §6) behaves the same either way. The tests reach production code, not a copy.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/signoff.py:112-115` claims nothing after the
  assembled §6 can hold a second `## 6. NEEDS-HUMAN` heading, because "the flow flattens"
  the §9 iteration delta. The CLI path does not flatten it: `cli.py:1466` passes
  `args.delta` raw to `signoff.record`, which writes it verbatim (`signoff.py:308`). Only
  `flow.py:181-182` flattens. **Reproduced:** a ledger holds `[E1, E2]`, and both rows are
  left OPEN (`- [ ]`) in the real §6. Then
  `pdca signoff X --iterate-do --delta "$(printf 'notes\n## 6. NEEDS-HUMAN (from v1)\n- [x] E1\n- [x] E2')"`
  makes the §9 copy the "last" §6. At the iterate, `autoiterate.retire_cleared`
  (`autoiterate.py:409-410`) reads its ticks, ignores the real §6, and retires BOTH entries
  (`kept: []`). The trigger is narrow: a human has to paste a §6 heading line into
  `--delta`, for example a §6 block copied from an older iteration's SUMMARY. The fix is
  small and the builder can make it: flatten `--delta` in `cli._signoff`, or in
  `signoff.record` itself. The test helper `_section6` (`tests/test_autoiterate.py:95-98`)
  copies the same "last heading" rule, so the suite cannot see this. Left unmarked because
  whether a low-severity hole is worth a sixth rebuild is the human's call.

- NEEDS-HUMAN — The sign-off ruling (stale or recovered infrastructure rows must not need
  hand clearance) is applied only to the two placeholder texts and to gates that could not
  run (`assemble.py:320-337`). The harness-written **decorrelation note** is not covered:
  `leaves.py:3626-3631`, written from `_select_advisory` at `leaves.py:3664-3667`. It is
  re-derived on every Check: `leaves.py:3644` deletes the previous note first. It talks about
  that Check's own run ("confirm the review's independence by hand"), not about the patch.
  Yet it has no leaf-status marker, so it gets `no_verdict=False` and is deferred.
  Confirmed: `autoiterate.deferrable` returns it. Concrete case: round 1 has no
  `loop-telemetry.json`, so the note reads "builder family … unknown" and is deferred. In
  round 2 the family is known and a complement leaf exists, so no note is written. The
  handover §6 still asks the human to confirm the independence of a review of a patch that
  was thrown away. Whether this note belongs to the ruled class is a scope call. Note that
  the plan-advisory placeholder is NOT in that class: it is never re-run on iterate-do, so
  deferring it is correct.

- `check-gates.json` row "C5 added test exercises production, not a copy" reports `pass`,
  but its log (`gate-logs/C5-prod-path.log`) says "patch adds no new test file — nothing to
  assert". The tests went into existing files, so the gate checked nothing. That pass is not
  evidence. The mutation pass above independently shows the tests do run production code,
  so the conclusion holds. Only the gate row's evidence is empty.

## Attempted, could not refute

- The fresh vs rendered drift at retire time. `driver._retire_cleared_deferrals`
  (`driver.py:334-335`) re-derives `fresh` after `_carry_forward_into_brief`. The only
  input that could change is the `[[doctor.checks]]` dependency rows. Their texts share a
  long tail, not a long opening, so `_same_finding` keeps them apart.
- Any leaf text landing after the real §6. §7, §8 and §10 are fixed text written by the
  harness. Gate `path_line` values are single lines. Flow-written §9 deltas are flattened.
  The only hole is the CLI delta above.
- An edited tick retiring a neighbour. An edit of a rendered row still matches its own
  origin, so any near-twin makes two hits and fails closed. An edit that matches only a
  fresh row retires nothing.
- An unreadable ledger on every accept path. Both `_apply_decision` and `cli._signoff` go
  through `flow.accept_blockers`. If §6 is missing, `ensure_needs_human_item` adds nothing,
  but `record` then refuses on `unrecordable`. A ledger entry that is not a string, or a
  dangling symlink, raises `DeferredLedgerUnreadable`.
- `no_verdict` spoofing. A real (closed) artifact never gets a leaf-status label, so its
  rows can never be marked no-verdict. Placeholder reasons are single-line in practice
  (`str(CalledProcessError)` quotes argv with `repr`).
- Clause 1 / clause 4 flow behaviour (the cap at 3 with `rounds = 0`, the backstop at 2 by
  default, `[IMPL, HUMAN, size HUMAN] → False`). These are driven through the real
  `flow._maybe_auto_iterate` and pass for the right reason.

### Advisory — code-review

# Advisory code review — issue 409 (iteration 5)

Scope: correctness bugs this patch introduces, plus reuse / simplification. Gates are green
(C4 red→green, 101 tests failing pre-fix and passing post-fix; T3 suite OK). I found no
blocking correctness defect. The three carry-forward items from iteration 4 are in place:
C6 and the row writer both read the last §6 heading, a fresh row protects nothing, and
no-verdict rows are not deferred. Each item has a test that drives production code. Below
are the smaller things worth knowing; none of them needs to stop an accept.

- template/src/pdca_harness/driver.py:334 — `_retire_cleared_deferrals` rebuilds the "fresh"
  row list by re-running `assemble.collect_needs_human` at the iterate transition, not by
  reading what assembly rendered. Anything that `collect_needs_human` reads and that can
  change between assembly and sign-off will shift that list. The clearest case is the
  unregistered-dependency row: `pdca.toml` is re-read live and can change mid-cycle
  (assemble.py:765-767 says so). If the human fixes `pdca.toml` and ticks that row, the
  tick then matches no rendered row exactly, so `retire_cleared` (autoiterate.py:419-423)
  treats it as an edit and fuzzy-matches it against the ledger. A wrong retirement needs a
  ledger entry that `_same_finding` accepts, so this is unlikely. Still, it fails in the
  open direction. A sturdier fix would record the rendered row list at assembly, for
  example in a sidecar next to the ledger, and read that back at retire time. Low priority.
- template/src/pdca_harness/signoff.py:191-197 — `ensure_needs_human_item`
  hand-copies the checkbox-strip and normalise logic that `autoiterate._row_text` / `_norm`
  (autoiterate.py:120-131) already define. Separately, `assemble._deferred_needs_human`
  (assemble.py:505-508) calls the private `autoiterate._norm` through a local import. Both
  copies must stay identical: the `_deferred_needs_human` docstring says that if the dedup
  and retire normalisation differ, a tick matches two rows and retires nothing. Moving
  `_norm` / `_row_text` into `signoff` would leave one definition and drop the cross-module
  private access. `autoiterate` already imports `signoff`, and `assemble` can import it
  without a cycle. This is a cleanup only; today the behaviour matches.
- template/src/pdca_harness/autoiterate.py:290 — `_write_ledger` leaves a stray
  `.deferred-findings.json.<pid>.tmp` in the bundle when `write_text` fails partway (disk
  full, permissions). The live ledger stays intact, so this is only litter. A
  `try/except: tmp.unlink(missing_ok=True); raise` around the write would tidy it.
- template/src/pdca_harness/flow.py:378 (`_maybe_auto_iterate`) — the
  stderr notice counts `rerun` over the raw `items`, while `held` uses the deduplicated
  `deferrable(items)`. The same no-verdict row raised twice is counted twice. This only
  affects the message.

No NEEDS-HUMAN items from this lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior-art coverage for all 15 affected paths — the brief records a narrower three-path search, while this target has only a synthetic base commit and no remote, so duplicate or previously rejected work cannot be independently excluded (`brief.md:151`; `review-prior-art.log:3`, `review-prior-art.log:18`).
- [x] Validation — fitness-to-purpose — Give final fitness sign-off for this implementation against the already accepted bounded-handover policy — the automated evidence verifies retention and clearance behavior, while the final suitability judgment remains human; this does not reopen the settled oversight or size ruling (`brief.md:286`; `template/tests/test_autoiterate.py:804`, `template/tests/test_autoiterate.py:1101`).
- [x] `template/src/pdca_harness/signoff.py:112-115` claims nothing after the assembled §6 can hold a second `## 6. NEEDS-HUMAN` heading, because "the flow flattens" the §9 iteration delta. The CLI path does not flatten it: `cli.py:1466` passes `args.delta` raw to `signoff.record`, which writes it verbatim (`signoff.py:308`). Only `flow.py:181-182` flattens. **Reproduced:** a ledger holds `[E1, E2]`, and both rows are left OPEN (`- [ ]`) in the real §6. Then `pdca signoff X --iterate-do --delta "$(printf 'notes\n## 6. NEEDS-HUMAN (from v1)\n- [x] E1\n- [x] E2')"` makes the §9 copy the "last" §6. At the iterate, `autoiterate.retire_cleared` (`autoiterate.py:409-410`) reads its ticks, ignores the real §6, and retires BOTH entries (`kept: []`). The trigger is narrow: a human has to paste a §6 heading line into `--delta`, for example a §6 block copied from an older iteration's SUMMARY. The fix is small and the builder can make it: flatten `--delta` in `cli._signoff`, or in `signoff.record` itself. The test helper `_section6` (`tests/test_autoiterate.py:95-98`) copies the same "last heading" rule, so the suite cannot see this. Left unmarked because whether a low-severity hole is worth a sixth rebuild is the human's call.
- [x] The sign-off ruling (stale or recovered infrastructure rows must not need hand clearance) is applied only to the two placeholder texts and to gates that could not run (`assemble.py:320-337`). The harness-written **decorrelation note** is not covered: `leaves.py:3626-3631`, written from `_select_advisory` at `leaves.py:3664-3667`. It is re-derived on every Check: `leaves.py:3644` deletes the previous note first. It talks about that Check's own run ("confirm the review's independence by hand"), not about the patch. Yet it has no leaf-status marker, so it gets `no_verdict=False` and is deferred. Confirmed: `autoiterate.deferrable` returns it. Concrete case: round 1 has no `loop-telemetry.json`, so the note reads "builder family … unknown" and is deferred. In round 2 the family is known and a complement leaf exists, so no note is written. The handover §6 still asks the human to confirm the independence of a review of a patch that was thrown away. Whether this note belongs to the ruled class is a scope call. Note that the plan-advisory placeholder is NOT in that class: it is never re-run on iterate-do, so deferring it is correct.
- [x] **The default size backstop means the Goal's budget can never be the binding limit, and the brief does not say so.** The Motivation says the problem is that "the round budget … is never the constraint that binds", and clause (1)'s worked example depends on rounds 4–5 happening. But `size_signal.DEFAULT_THRESHOLDS["rounds"] = 2` (`size_signal.py:73`). Clause (4) keeps "a size-backstop item makes `eligible()` false". So on a default instance the third Check (2 archives) raises the size item and the loop stops at 2 rounds, whatever `soft_auto_iters` or `max_auto_iters` is set to. `test_size_signal.py:179-187` pins this ordering, and `pdca.toml.jinja:292` documents it. The brief puts "how size-signal counts rounds (#477)" out of scope, so after this change `soft_auto_iters`/`max_auto_iters` above 2 still do nothing unless `[size_signal].rounds` is raised or set to 0. That applies to the default of 3 too, and to the 3/5 example. The unit criterion can pass while the stated Goal is not delivered. The brief should do three things: say this plainly, document in `pdca.toml.jinja` next to `soft_auto_iters` that the key only matters once `size_signal.rounds` is raised, and add `pdca.toml.jinja:289-293` (whose comment states the old rule) to the edit list. Otherwise it should explain why #477 is not a prerequisite.
- [x] **The ticked-rows reader's `whole_on_missing=True` points the safe direction the wrong way.** Clause (3) requires the new reader to call `signoff._section(..., whole_on_missing=True)` "the lenient §6 side, matching `open_needs_human`". That leniency is safe for `open_needs_human` only because scanning the whole document finds more `- [ ]` rows and so blocks accept harder (`signoff.py:108-111`, `:237-238`). A reader that looks for `- [x]` rows gets the opposite effect: with no §6 heading, every ticked checkbox anywhere in SUMMARY is treated as a tick. That includes checkboxes quoted in §5 review text, which is pasted in verbatim at `assemble.py:395`. Each such tick retires a ledger entry, so an unreviewed deferred finding can be lost. That is exactly the kind of loss the ledger is meant to prevent. The open-row side (protection) should stay lenient. The tick side should be `whole_on_missing=False`, so a missing §6 retires nothing. `unrecordable()` (`signoff.py:154-156`) makes this path hard to reach today. But the brief makes `True` a binding contract, and the reasoning it gives for it is wrong. The thread imposed this constraint, so a human should decide rather than the planner quietly changing it.
- [x] **Clause (4)'s named test cannot go red first.** The criterion says "Both directions of `test_the_tag_is_the_mechanism` (`test_size_signal.py:280`) pass", and Falsifiability (4) calls the "ordinary HUMAN beside IMPL fires" case a direction of that test. It is not one. The test's two directions are size-text HUMAN → False and size-text IMPL → True (`test_size_signal.py:285-290`), and both already pass on `main`. The only failing leg in clause (4) is the new "[IMPL, ordinary HUMAN] → True" case, which is clause (2)'s change. Nothing in clause (4) fails today, so the check cannot tell apart a size-by-kind composition from the naive `any(IMPL)` that would drop the backstop entirely. The brief should require one new test that fails against a plain `any(item.kind == IMPL)`, for example `[IMPL, ordinary HUMAN, size HUMAN] → False` next to `[IMPL, ordinary HUMAN] → True`. It should also stop claiming that `:280` provides the failing leg.
- [x] **The convergence baseline ("every Check that reaches the auto-iterate decision, including declines") has no definition, so clause (1) can't be checked at its edges.** `_maybe_auto_iterate` can decline in five places before or at the budget check: auto-iterate off or not at AWAITING_SIGNOFF (`flow.py:296`), a decision already recorded (`:303-307`), `collect_needs_human` raised (`:308-317`), ineligible (`:318-330`), and budget spent (`:331-335`). The brief doesn't say which of these record an IMPL count. One case changes the result. A HUMAN-only decline records IMPL=0 and the human then iterates by hand. Above soft, any later Check with IMPL ≥ 1 is then an "increase", so auto-iterate never fires again even though the budget is left. The brief should list which decline paths observe a count, and say whether a human-driven iterate resets the baseline. A test should pin both.
- [x] **The scope is two independent changes plus a bug fix, and the brief admits it.** The Open questions say "the natural cut is budgets (clause 1) vs defer+ledger (clauses 2–4)". Clause (1) (`config.py`, the `auto-iterate.json` shape, `flow.py:331-335`) shares no mechanism with the ledger, retirement or `_apply_decision` work. The thread does scope both under #409, so this is not smuggled in. But leaving the split to "the sizing prompt" means the review load is already set. The change touches 9 source files, the jinja template, 2 docs and 2 test modules, and it adds a gate at `_apply_decision` that runs on every sign-off, not only with auto-iterate on. The finding above also makes clause (1) almost unobservable on default settings. So the split should be decided at Plan: ship defer+ledger (which fixes the 13.5% veto the Motivation measures) and hold the budgets until #477 settles how size-signal counts rounds.
- [x] size backstop — this slice is behaving oversized: patch is 166 KB (threshold 125 KB); 4 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

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
- Follow-up (#409 §6 row 3): `pdca signoff --delta` is written raw into §9; a pasted `## 6. NEEDS-HUMAN` block becomes the "last" §6 and `retire_cleared` retires uncleared ledger entries — flatten `--delta` in `cli._signoff` or `signoff.record`, as `flow.py:181-182` already does.
- Follow-up (#409 §6 row 4): the harness-written decorrelation note (`leaves.py:3626-3631`) is re-derived each Check but is deferred like an ordinary HUMAN finding — treat it as a stale/recovered infra row and drop it once a later round no longer emits it.
- Process: stale Plan-advisory rows (soft_auto_iters, convergence baseline, whole_on_missing, clause-4 red leg, split) re-entered §6 after the Plan re-scope resolved them and the human had already cleared them at iteration 3 — plan-advisory findings should not re-surface once the brief is revised past them.
