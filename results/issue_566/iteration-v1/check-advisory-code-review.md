# Advisory code review — issue #566

Scope: correctness bugs introduced by this patch, plus reuse/simplification/efficiency.
Grounded on the patched target tree (`$PDCA_TARGET`), not build-notes.

## Findings

- `template/src/pdca_harness/flow.py:1461-1482` (`_split_marked`) duplicates the three-line
  close-marker read in `_is_split_parent` (`flow.py:907-930`) verbatim, differing only in the
  terminal-state gate. The docstring on `_split_marked` explains *why* the two predicates must
  answer differently (one must see a split before sign-off confirms it, the other must not),
  which is a real reason not to merge them into one predicate — but `_is_split_parent` could
  still be rewritten as `state.state(d) in _TERMINAL and _split_marked(d)` to drop the second
  copy of the try/except read without changing either's behavior. Cosmetic; not a defect.

- `template/src/pdca_harness/flow.py:1634-1652`: when `_drive_and_act` is entered with an
  empty `bundles` and only `adopt_seeds` (the "named id is itself an already-terminal split
  parent, nothing else to drive" shape from `flow_ids`), and the seed's pre-pass adopts no
  child at all, the function returns `{}` right there — before the tail that now calls
  `_warn_stranded_split_children` (`flow.py:1811`). I checked every branch that can leave
  `bundles` empty after that pre-pass (no brief, held by a sibling parent, claim refused by
  another live run, reschedule failure) and each already prints its own explicit stderr line
  (`_adoptable`'s prints, `_report_held`, `_report_refused`, the "could not be scheduled"
  message) — so in practice nothing is left silently orphaned on this path today. But it does
  mean the new end-of-run report is not literally reached on every return from
  `_drive_and_act`, which is narrower than the brief's "just before `_drive_and_act` returns"
  wording. Worth a second look if a future change adds a way to leave `bundles` empty on this
  path *without* its own report — right now it's redundant-safe, not silent.

## Everything else checked and clean

- `drive_claim.held()` / the `Run.take()` retry loop (`drive_claim.py:170-297`): retry count,
  wait scheduling, handle lifecycle (no leaked file descriptors on any exit branch), and the
  fail-open-the-opposite-way contract between `take()` (fail closed) and `held()` (fail open)
  all check out. The forced-collision test (`test_take_retries_past_a_forced_peek_collision...`)
  correctly pins the retry against a real OS lock via a deterministic hook rather than
  wall-clock timing.
- `flow_batch`'s new `try/finally` around the sweep marker (`flow.py:1854-1990ish`): the two
  existing "nothing to drive" messages were re-wrapped across two string literals when the
  block gained a level of indentation, but the concatenated text is byte-identical to before
  — confirmed by diffing the two literal halves. No message text actually changed.
- `_warn_stranded_split_children`'s walk mirrors `_adopt_split_children`'s lineage walk
  (`_lineage_children`, `_PLAIN_ID`, `_real`, `_inside_bundle_root`) faithfully; it correctly
  reuses those helpers rather than re-implementing bundle-name validation.
- C4's red leg (`gate-logs/C4-verify.log`) fails 4 of 8 new tests plus 1 `AttributeError` on
  the reverted production code and the green leg passes all 8 — the new test file does
  exercise the fix, not a copy of it (confirmed independently of C5's prod-path check, which
  also passes).
- T3's full offline suite is green (1963 tests, 2 skipped) with the patch applied; the
  "FAILED" lines inside `T3-suite.log` belong to an unrelated nested-harness fixture printing
  its own log, not this patch's tests.
- Docs/planner/leaves.py wording updates (`docs/07-crosscutting.md:339-352`,
  `template/agents/planner.md.jinja:152-192`, `template/src/pdca_harness/leaves.py:1116-1477`)
  match what `cli._split` and `flow._warn_stranded_split_children` actually print — no drift
  between the model-facing text and the code.

No NEEDS-HUMAN items — nothing here rises to an architectural or scope question; the one open
item above is a defensive-depth note, not a bug to route back to Do.
