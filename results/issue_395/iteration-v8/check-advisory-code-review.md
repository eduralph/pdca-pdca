# Advisory code review — issue 395 (same-wave conflict refused at accept)

Lenses: correctness bugs the patch introduces, and reuse / simplification / efficiency.
Grounded on the patched target at `$PDCA_TARGET`.

**Correctness: no blocking defect found.** I traced the accept paths and the session bound
by hand, and they behave as the brief asks:

- Pre-apply refusal, then a session, then a C6 block: 2 sessions, then parked.
- Post-session refusal: one more session, then parked.
- A session that raises is not counted (`flow.py:2790-2798`).
- The count goes back to 0 at wave start (`flow.py:2729`).
- The override needs the row ticked. The `open_needs_human` test in `_refuse` is only
  right because C6 passed just before it, and it did.
- The CLI now deletes the decision file (`cli.py:1546`).
- Tree errors are caught before the general `IntegrationError` fallback
  (`flow.py:321-323`).
- The `_back_on` reset runs on every exit of `same_wave_clash`, raising exits included.
  Errors are chained with `raise … from`.
- The `publish._checkout_base` refactor gives the same result as the old inline
  `wave_stacked and bool(wave_tip)` rule.
- The trial condition at `flow.py:3304-3307` matches the fold's own condition (`dry` is
  `publisher.mode == "stub"`, `flow.py:3366`).

The new test file drives the real `_drive_wave` → `_apply_decision` path and covers every
leg in the brief, plus the three iteration-6 legs and the iteration-7 CLI leg. C4 shows
11 of 14 red before the fix. The 3 green ones are the controls that should be green on
`main`: (b), (g), and the plain C6 case.

Findings (all minor, none gating):

- `template/src/pdca_harness/integrate.py:812` / `:829-831` — efficiency. Every accept on
  a non-final wave runs a full `_fetch` of origin and the base remote. It rebuilds every
  accepted sibling's would-be commit and runs the merge chain twice (`alone` and `held`),
  with `_held_by` trials on top. For a wave of N bundles accepted one by one, that is N
  fetches and about N² commit builds. This is fine for today's wave sizes. If waves grow,
  two things could be cached per wave: `alone` (it only changes on an override) and the
  built commits keyed by bundle. Not worth doing in this slice.
- `template/src/pdca_harness/flow.py:317` with `integrate.py:793` — small duplication.
  `_refused_for_wave` resolves the target only to look up `folded_tips`, and
  `same_wave_clash` resolves it again. Passing `folded_tips` (or the resolved tip) down
  once would drop the second call. Cosmetic.
- `template/src/pdca_harness/integrate.py:807` — simplification. An `ExitStack` that holds
  one lock adds nothing over `with integ_lock(wt) as got:`. The brief asked to follow
  `_fold_lines`, which needs the stack because it holds one lock per target. Here there is
  only one target. Cosmetic.
- `template/src/pdca_harness/state.py:159` — adding `SAME_WAVE_REFUSAL` to
  `DOWNSTREAM_OF_BRIEF` almost never does anything. Both decision routes call
  `consume_decision` (`flow.py:233`, `cli.py:1546`), and that deletes the record before an
  iterate archives the attempt. So it is archived only on an iterate that records no
  decision (a reassemble or an auto-iterate). That is harmless and arguably correct. I note
  it only so no one relies on the archive copy existing.
- `template/src/pdca_harness/flow.py:474` — wording. The wave-end line says the session
  "recorded nothing new". It also prints when the session wrote `accept` again without
  ticking the row (C6 then blocks it). "recorded nothing that settled it" would be
  accurate in both cases. Cosmetic.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
