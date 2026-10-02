# Design proposal — issue 409 / autoiterate-budgets-defer-ledger

> Child slice of #332 (items 1, 4), split during Plan. Reopened 2026-08-11: PR #410 merged
> only a scaffold commit, so none of this reached `main`. The working shape is proven
> downstream in getwyrd/wyrd-pdca#168 (merged 2026-07-26; #335 fix at
> getwyrd/wyrd-pdca@e4fdf3b); this cycle ports the child-2 part to the template. #335 is
> fixed INSIDE this change (maintainer triage: its defective code exists only downstream).
> Sibling slice: #408.
>
> **Re-scoped at Plan (human, 2026-09-30):** #332 item 1 (a new `soft_auto_iters` budget with
> a convergence test) is DROPPED, not deferred. The loop already has an early stop below the
> hard cap — the size backstop's rounds rule (`[size_signal].rounds`, default 2, below
> `max_auto_iters` = 3) — and a second soft limit on top of it would add a setting that never
> binds on a default instance. Instead this slice CONSOLIDATES the stopping rules: exactly two
> stops, the hard cap and the size backstop, described in one place. The slug keeps its
> original name for bundle continuity.

- **Slug:** autoiterate-budgets-defer-ledger
- **Kind:** enhancement (design proposal)
- **Goal:** one HUMAN finding no longer vetoes an unattended rebuild. While Check still
  finds implementation work, the driver rebuilds — stopped only by the existing hard cap
  (`max_auto_iters`) or the size backstop — and HUMAN findings are held in a loss-proof
  ledger that re-enters §6 at handover, so every one still reaches the human under the C6
  guard.
- **Success criterion:** all four hold in `template/tests/test_autoiterate.py` (plus the
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
- **Falsifiability:** RED today on this host via
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_autoiterate tests.test_size_signal`,
  as run by `./engine/scripts/run-verify.sh` (gating C4; keeps test files, reverts
  production hunks, runs every changed test module). Per clause: (1) the flow test that
  drives `[IMPL, ordinary HUMAN]` Checks to the hard cap is red today, because today's veto
  (`autoiterate.py:73-74`) declines on the first Check (the "no `soft_auto_iters`" assertions
  pass today and guard against it being re-added — they are not a red leg); (2)
  `[IMPL, HUMAN]` → `eligible()` is False today (`autoiterate.py:73-74`), and
  `state.CYCLE_EVIDENCE_ONLY` (`state.py:170`) holds exactly two names; (3) no ledger or
  `retire_cleared` exists upstream, so tests (a)–(d) fail; (a) and (b) must ALSO fail
  against the symmetric-fuzzy variant (write them to discriminate); (4) the new discriminating
  test is red today on its `[IMPL, ordinary HUMAN] → True` leg (today's veto), and its
  `[IMPL, ordinary HUMAN, size HUMAN] → False` leg fails against a naive `any(IMPL)`
  implementation; `test_the_tag_is_the_mechanism` is not a red leg. Tests must reach new
  symbols as module attributes (`autoiterate.retire_cleared`), never via a module-top
  `from … import`: on the red leg an import error reads as PDCA-UNVERIFIABLE, not red.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 408, 477
- **Ordering note:** 408 edits `assemble.py` + `test_autoiterate.py`; 477 edits
  `size_signal.py` + `test_size_signal.py` (this slice adapts that test file's fixtures).
  Shared files, no build-on dependency, so different waves. 371 declares `Depends on: 409`
  for ordering only (shared `assemble.py` and `template/pdca.toml.jinja`; this slice no
  longer touches `config.py`). This slice builds first, on plain `main`; 408 builds last,
  so Do here sees today's `_classify_finding`. Computed batch order
  (`pdca-pdca waves 408 409 371 477`): [409] → [371, 477] → [408].
- **Scope:** issue #332 item 4, plus the #335 fold, the #324 composition, and the
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
- **Difficulty:** high
- **External dependencies:** none
- **Test file:** template/tests/test_autoiterate.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites on `main` @ 9405658: `autoiterate.py` — `BUDGET_FILE` `:50`, `DECISION`
  `:53`, `eligible` `:56` (veto `:73-74`), `count` `:77`, `bump` `:86`, `rationale` `:93`,
  `write_decision` `:107` (keep its refuse-if-ineligible guard); `state.py` —
  `DOWNSTREAM_OF_BRIEF` `:116`, `CYCLE_EVIDENCE_ONLY` `:170`, its use in `is_resolved`
  `:295`; `driver.py` — `advance` iterate branches `:131-140` (retire between
  `_carry_forward_into_brief` and `_archive_iteration`, as `_carry_forward_into_brief` is
  best-effort there); `flow.py` — `_apply_decision` `:133` (C6 guard `:176`),
  `_maybe_auto_iterate` `:276` (eligible `:318`, size-item stderr `:319-330`, budget
  `:331-335`); `size_signal.is_size_item` `size_signal.py:374`;
  `assemble.collect_needs_human` `:259`, `assemble_summary` `:333`;
  `signoff.open_needs_human` `:102`, `_section` `:231`; `cli.py:180`;
  `template/pdca.toml.jinja:53-74`, `:286-295`; `docs/07-crosscutting.md:434-462`;
  `docs/05-check.md:405-407`, `:773-779`. Downstream reference: getwyrd/wyrd-pdca#168
  (`deferred`, `DeferredLedgerUnreadable`, `ensure_section6_item`, `cleared_needs_human` —
  NOT its `observe` / `should_iterate` budget code, which is out of scope) and
  getwyrd/wyrd-pdca@e4fdf3b (the exact-first `protected` set). The #168 prototype still has
  the #335 bug; the fold above is binding.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -n 8 -- template/src/pdca_harness/autoiterate.py template/src/pdca_harness/config.py
  template/src/pdca_harness/state.py` → 5ced9bd, 4050da2, 7ab824f, 87c7352, 0881af9,
  2261b53, 96c9704, e7a88b0 — none add a ledger. `soft_auto_iters`, `retire_cleared`,
  `_same_finding`, `deferred-findings.json` are absent from `template/src/` (grep,
  2026-09-30). PR #410 (merged) carried only a scaffold. Closed-unmerged PRs touching these
  paths: none. No open PRs.
- **Disposition hint:** new-feature

## Motivation

`eligible()` requires every non-IMPL item to be STANDING, so one HUMAN finding vetoes the
rebuild. Auto-iterate fired on 31 of 230 eligible-checked attempts (13.5%); two bundles the
maintainer reported as broken spent zero rounds. The veto, not the round limit, is what
stops the loop. Removing the veto lets the limits that already exist — the hard cap and
the size backstop — do the stopping, which is their job.

## Design

- **Stops:** unchanged mechanisms, consolidated description. `max_auto_iters` is the hard
  cap; the size backstop is the early stop (it fires at 2 rounds by default, below the cap
  of 3, on purpose). No third limit.
- **Ledger:** `deferred-findings.json` in the bundle, holding HUMAN-item texts; written when
  a round fires with HUMAN items present; merged into §6 at assembly (dedup against the
  fresh items); retired only by a positive tick, using the exact-first protected set.
  Unreadable ledger → a §6 item that blocks accept.
- **Size item:** `eligible()` stops on a size-backstop HUMAN item specifically. Every other
  HUMAN item defers.

## Alternatives considered

- Keep the veto and only add the tag (#408): measured as not enough on its own, because
  HUMAN findings beside IMPL items remain the common case.
- Symmetric-fuzzy retirement exclusion: re-creates the unclearable near-twin pair (#335
  second comment; regressed round 5 in the instance).
- A `soft_auto_iters` budget with a convergence test (#332 item 1, the downstream #168
  shape): dropped by the human at Plan. It duplicates the size backstop's early stop, and on
  a default instance the backstop always fires first, so the new key would never bind.

## Impact & compatibility

No config change: instances keep `max_auto_iters` and `[size_signal].rounds` as they are.
With auto-iterate on, HUMAN findings now reach the human at handover, not before the
rebuild. That is the intended trade, and C6 still makes the human clear every one before
accept. New bundle file: `deferred-findings.json`. The PR should close #409 and #335
(`Closes #335` in the body as well). #332 item 1 should be noted on the tracker as dropped
(not done) so #332 can close without it.

## Open questions

- DECIDED (human, Plan, 2026-09-30): the tick-side reader uses `whole_on_missing=False`,
  reversing the thread's stated `True`. The thread's reason ("matching `open_needs_human`")
  holds only for the open-row side, where leniency blocks harder; on the tick side it would
  retire ledger entries on stray ticks.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: findings 2–4 addressed in the brief — tick-side reader switched to
`whole_on_missing=False` with a test, flagged for the human (clause 3, Open questions); a
new discriminating test for the size-by-kind rule and the false red-leg claim removed
(clause 4, Falsifiability). Findings 1, 4 (baseline) and 5 (split) are resolved by the
human's re-scope: the `soft_auto_iters` budget and its convergence baseline are dropped, so
the size backstop and hard cap are the only stops (clause 1), their description is
consolidated into one place (Scope), and what remains is one mechanism (defer + ledger +
retirement) with no split needed.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild to close two gaps in the retirement code; keep everything else as-is. - §6 item 5 (adversary): the "more than one fuzzy hit fails closed" rule in retire_cleared (template/src/pdca_harness/autoiterate.py:~316, `len(hits) == 1`) is untested — mutating it to retire the first hit passes all 141 tests. Add the case to RetiresOnlyWhatTheHumanTicked: ledger [P, R] near-twins; human deletes P's row, edits R's row and ticks it → both entries must survive. - §6 item 7 (code review): in _same_finding (autoiterate.py:126) the containment test (`a in b or b in a`) skips _MATCH_FLOOR, so a short ticked row can retire any ledger entry that contains it — fails open, against "absence is not consent". Apply the floor to containment too (require min(len(a), len(b)) >= _MATCH_FLOOR before the substring test) and add a test: a short ticked row that is a substring of a deleted entry retires nothing. Out of scope for this rebuild: items 3 (shared signoff._section heading reader), 4 (fresh near-twin fails closed — acceptable), 6 (leaf write access to the bundle dir).
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild to close two gaps in the retirement code; keep everything else as-is.
  - §6 item 5 (adversary): the "more than one fuzzy hit fails closed" rule in retire_cleared (template/src/pdca_harness/autoiterate.py:~316, `len(hits) == 1`) is untested — mutating it to retire the first hit passes all 141 tests. Add the case to RetiresOnlyWhatTheHumanTicked: ledger [P, R] near-twins; human deletes P's row, edits R's row and ticks it → both entries must survive.
  - §6 item 7 (code review): in _same_finding (autoiterate.py:126) the containment test (`a in b or b in a`) skips _MATCH_FLOOR, so a short ticked row can retire any ledger entry that contains it — fails open, against "absence is not consent". Apply the floor to containment too (require min(len(a), len(b)) >= _MATCH_FLOOR before the substring test) and add a test: a short ticked row that is a substring of a deleted entry retires nothing.
  Out of scope for this rebuild: items 3 (shared signoff._section heading reader), 4 (fresh near-twin fails closed — acceptable), 6 (leaf write access to the bundle dir).
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Design is right; fix three implementation defects the adversary review confirmed: 1. `_same_finding` (autoiterate.py:144) treats unrelated findings on the same element as one: the canonical 5/5/1 label ("C5 Causal adequacy — " = 21 chars) alone clears _MATCH_FLOOR (20). A tick on one can retire an unrelated, never-adjudicated ledger entry (fails open). Measure the shared opening only past a common canonical `Item —` prefix, and add a test with two different findings on one element where one is short. The ratio rule is untested today (`return shared >= _MATCH_FLOOR` passes all 143 tests) — pin it. 2. `pdca signoff <id> --accept` (cli._signoff, cli.py:1446-1451) runs its own C6 check and never calls `flow._hold_unreadable_ledger`, so an unreadable ledger does not block accept on that path — violates brief clause 2. Share one helper with `_apply_decision` and add a CLI-path test. 3. Stale comments in assemble.py (:246-248, :278-279, :302-303) still describe the old veto; update them to the defer rule. Open design question the human did not rule on (do not change behaviour for it this round): whether re-derived infra rows (missing-review placeholder, gate-could-not-run) should be deferred.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Design is right; fix three implementation defects the adversary review confirmed:
  1. `_same_finding` (autoiterate.py:144) treats unrelated findings on the same element as one:
     the canonical 5/5/1 label ("C5 Causal adequacy — " = 21 chars) alone clears _MATCH_FLOOR (20).
     A tick on one can retire an unrelated, never-adjudicated ledger entry (fails open). Measure
     the shared opening only past a common canonical `Item —` prefix, and add a test with two
     different findings on one element where one is short. The ratio rule is untested today
     (`return shared >= _MATCH_FLOOR` passes all 143 tests) — pin it.
  2. `pdca signoff <id> --accept` (cli._signoff, cli.py:1446-1451) runs its own C6 check and never
     calls `flow._hold_unreadable_ledger`, so an unreadable ledger does not block accept on that
     path — violates brief clause 2. Share one helper with `_apply_decision` and add a CLI-path test.
  3. Stale comments in assemble.py (:246-248, :278-279, :302-303) still describe the old veto;
     update them to the defer rule.
  Open design question the human did not rule on (do not change behaviour for it this round):
  whether re-derived infra rows (missing-review placeholder, gate-could-not-run) should be deferred.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Design stays as-is; fix three retirement defects from the iteration-3 review (§6 items 3–5): 1. Unattended retirement via a quoted §6 heading (adversary). `signoff._section` returns the FIRST `## 6. NEEDS-HUMAN` heading (signoff.py:308-313); §5 pastes leaf text verbatim ahead of the real §6 (assemble.py:380-383), so `cleared_needs_human` can read ticks a leaf quoted, and `_retire_cleared_deferrals` (driver.py:135, :141) empties the ledger on an automatic round with no human involved. Fix: make the tick-side reader use the LAST matching §6 heading (or the real, assembled §6), AND/OR skip retirement when §9 was written by auto-iterate. Add a test: ledger entry + an advisory artifact quoting a §6 heading with that row ticked + one [impl] bullet → after an auto-iterate round the entry is still in the ledger. 2. Fuzzy fail-open beyond labels (adversary). Any shared opening ≥ 20 chars (or ≥ 60% ratio) lets a tick on one finding retire a different one whose own row was deleted (autoiterate.py:181), e.g. "the fix does not cover the retry path" retired by a tick on "...the CLI path", and shared path:line openings. Do not tune thresholds. Rule: a ticked row that exactly equals a row assembly rendered from a FRESH finding is that finding's clearance, never an edit of a ledger entry; fuzzy matching applies only to rows the human actually edited (needs the rendered row list at retire time). Tests for the three repro pairs. 3. `_same_finding` (autoiterate.py:170-173) applies `_MATCH_FLOOR` before checking equality after `_past_shared_labels`, so a separator-only edit of a short finding doesn't match itself. Add `if a == b: return True` before the floor check; add the case to `test_a_short_row_matches_only_exactly`. Stale plan-review items were cleared by the human (resolved by the Plan re-scope). Items 1–2 (T5 infra-row deferral policy, fitness-to-purpose) were not ruled on — do not change behaviour for them.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Design stays as-is; fix three retirement defects from the iteration-3 review (§6 items 3–5):
  1. Unattended retirement via a quoted §6 heading (adversary). `signoff._section` returns the FIRST
     `## 6. NEEDS-HUMAN` heading (signoff.py:308-313); §5 pastes leaf text verbatim ahead of the real
     §6 (assemble.py:380-383), so `cleared_needs_human` can read ticks a leaf quoted, and
     `_retire_cleared_deferrals` (driver.py:135, :141) empties the ledger on an automatic round with
     no human involved. Fix: make the tick-side reader use the LAST matching §6 heading (or the real,
     assembled §6), AND/OR skip retirement when §9 was written by auto-iterate. Add a test: ledger entry
     + an advisory artifact quoting a §6 heading with that row ticked + one [impl] bullet → after an
     auto-iterate round the entry is still in the ledger.
  2. Fuzzy fail-open beyond labels (adversary). Any shared opening ≥ 20 chars (or ≥ 60% ratio) lets a
     tick on one finding retire a different one whose own row was deleted (autoiterate.py:181), e.g.
     "the fix does not cover the retry path" retired by a tick on "...the CLI path", and shared
     path:line openings. Do not tune thresholds. Rule: a ticked row that exactly equals a row assembly
     rendered from a FRESH finding is that finding's clearance, never an edit of a ledger entry; fuzzy
     matching applies only to rows the human actually edited (needs the rendered row list at retire
     time). Tests for the three repro pairs.
  3. `_same_finding` (autoiterate.py:170-173) applies `_MATCH_FLOOR` before checking equality after
     `_past_shared_labels`, so a separator-only edit of a short finding doesn't match itself. Add
     `if a == b: return True` before the floor check; add the case to
     `test_a_short_row_matches_only_exactly`.
  Stale plan-review items were cleared by the human (resolved by the Plan re-scope). Items 1–2 (T5
  infra-row deferral policy, fitness-to-purpose) were not ruled on — do not change behaviour for them.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Design stays as-is. Rebuild to fix two gaps from the iteration-4 review (§6 rows 3/5 and 4) and apply one policy ruling (row 1): 1. C6 accept guard reads the FIRST `## 6. NEEDS-HUMAN` heading (fails open). `flow.accept_blockers` -> `signoff.open_needs_human` (signoff.py:102, default `last=False`; flow.py:233/:262) and `signoff.ensure_needs_human_item` (signoff.py:170) still read the first heading, which a leaf can quote into §5. Move BOTH to the last (real, assembled) §6 heading together — moving only one makes the unreadable-ledger row invisible to C6. Fix the ensure_needs_human_item dedup (:174-178) so it sees the copy assembly already put in the real §6 (no duplicate row). Tests: a SUMMARY whose §5 quotes an all-ticked §6 block while the real §6 has an open row -> accept_blockers is non-empty on both the flow and `pdca signoff --accept` paths; with an unreadable ledger, the row lands in the real §6, once. 2. Fresh near-twin shields an exactly-ticked ledger entry (autoiterate.py:386-390). Rule (matches brief clause 3 "a near-twin cannot shield its exactly-ticked neighbour" and autoiterate.py:107-110): an open row exactly equal to a row assembly rendered from a FRESH finding is that fresh finding, not an edit of a ledger entry, so it protects nothing in the ledger. Pin it with a test: ledger ["the fix does not cover the retry path"], §6 `- [x]` that row + fresh open `- [ ] the fix does not cover the CLI path` -> entry is retired. Keep the fail-closed protection for genuinely edited open rows. 3. Policy ruling (human, sign-off): stale/recovered infrastructure findings (missing-review placeholder, gate-could-not-run) must NOT need hand clearance at handover. Once a later round's review/gates have recovered (the fresh finding is gone), drop that infra entry from the ledger instead of re-entering it in §6. Ordinary HUMAN findings still defer and still need a tick. Test: a deferred missing-review row, then a successful review + passing gates -> it no longer appears in §6 or accept_blockers. Ruled, do not reopen: deferring human concerns to bounded handover is enough oversight (fitness-to-purpose). Size backstop (138 KB / 3 rounds) was weighed and overridden by the human: one mechanism converging, not an oversized slice — do not split. Cosmetic, optional: use autoiterate._norm in assemble._deferred_needs_human instead of the inline copy.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Design stays as-is. Rebuild to fix two gaps from the iteration-4 review (§6 rows 3/5 and 4) and apply one policy ruling (row 1):
  1. C6 accept guard reads the FIRST `## 6. NEEDS-HUMAN` heading (fails open). `flow.accept_blockers` -> `signoff.open_needs_human` (signoff.py:102, default `last=False`; flow.py:233/:262) and `signoff.ensure_needs_human_item` (signoff.py:170) still read the first heading, which a leaf can quote into §5. Move BOTH to the last (real, assembled) §6 heading together — moving only one makes the unreadable-ledger row invisible to C6. Fix the ensure_needs_human_item dedup (:174-178) so it sees the copy assembly already put in the real §6 (no duplicate row). Tests: a SUMMARY whose §5 quotes an all-ticked §6 block while the real §6 has an open row -> accept_blockers is non-empty on both the flow and `pdca signoff --accept` paths; with an unreadable ledger, the row lands in the real §6, once.
  2. Fresh near-twin shields an exactly-ticked ledger entry (autoiterate.py:386-390). Rule (matches brief clause 3 "a near-twin cannot shield its exactly-ticked neighbour" and autoiterate.py:107-110): an open row exactly equal to a row assembly rendered from a FRESH finding is that fresh finding, not an edit of a ledger entry, so it protects nothing in the ledger. Pin it with a test: ledger ["the fix does not cover the retry path"], §6 `- [x]` that row + fresh open `- [ ] the fix does not cover the CLI path` -> entry is retired. Keep the fail-closed protection for genuinely edited open rows.
  3. Policy ruling (human, sign-off): stale/recovered infrastructure findings (missing-review placeholder, gate-could-not-run) must NOT need hand clearance at handover. Once a later round's review/gates have recovered (the fresh finding is gone), drop that infra entry from the ledger instead of re-entering it in §6. Ordinary HUMAN findings still defer and still need a tick. Test: a deferred missing-review row, then a successful review + passing gates -> it no longer appears in §6 or accept_blockers.
  Ruled, do not reopen: deferring human concerns to bounded handover is enough oversight (fitness-to-purpose). Size backstop (138 KB / 3 rounds) was weighed and overridden by the human: one mechanism converging, not an oversized slice — do not split.
  Cosmetic, optional: use autoiterate._norm in assemble._deferred_needs_human instead of the inline copy.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
