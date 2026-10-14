## Summary
**User impact:** When `pdca flow` rebuilds a patch on its own (auto-iterate), the final
sign-off checklist can still ask you to "confirm the review's independence by hand" for a
review of the *previous*, discarded attempt. That item blocks accept, even though the
current attempt's review came from a different vendor and needs no such check. You end up
ticking off a warning about work that no longer exists.

This PR stops that warning from being carried forward. It now appears only in the round
that actually raised it, and it still blocks accept there until you tick it.

Reported in [#605](https://github.com/eduralph/pdca-harness/issues/605).

## What to look at
- The change itself is a few lines in the sign-off checklist builder: findings that come
  from the "could not pick a different-vendor reviewer" note are now flagged as being about
  the Check's own run, like a review or gate that gave no result. Such rows are never held
  over for the final handover.
- The rest is wording: comments, docstrings, the auto-iterate message printed by
  `pdca flow`, and one sentence in the user docs.
- To try it: set `[leaves.advisory_selection] mode = "vendor-complement"` with one advisory
  reviewer from another vendor, and run a bundle whose first round has no
  `loop-telemetry.json` and an implementation-level finding. On `main`, the note from round
  1 lands in `deferred-findings.json` and comes back in round 2's checklist. With this PR it
  does not. The new test class `CheckDecorrelationNoteIsNotDeferred` runs the same
  scenario.

## Root cause
The decorrelation note is written as `check-advisory-decorrelation.md`, and
`collect_needs_human` reads it like any advisory finding: a plain HUMAN row with
`no_verdict=False`. Auto-iterate's `deferrable` only skips `no_verdict` rows, so the note
went into the deferral ledger, and `_deferred_needs_human` put it back into every later §6.

## Fix
- `template/src/pdca_harness/assemble.py`: in the advisory loop of `collect_needs_human`,
  items read from the artifact whose stem is `decorrelation` are marked
  `it._replace(no_verdict=True)`. This copies the existing missing-review placeholder
  handling a few lines above. The check is keyed on the artifact, not the note's text, and
  it is not placed in the `no_verdict=` callback, because that callback only runs for text
  with a leaf-status marker and the note has none.
- The `NeedsHumanItem.no_verdict` comment, the `autoiterate` module docstring and the
  `deferrable` docstring now describe the field as "a row about this Check's own run".
- `template/src/pdca_harness/flow.py`: the auto-iterate notice now reads "N row(s) about
  this Check's own run left for the next Check to re-check" instead of "review/gate row(s)
  with no verdict … re-run".
- `docs/07-crosscutting.md`: one sentence in the auto-iterate section covers the note.
- No new field, and the note's text and when it is written are unchanged. The plan-side
  note is out of scope (its carry-over was #603).

Known limit, not changed here: a user-configured advisory leaf with `id = "decorrelation"`
would share the note's file name. Its findings would then also skip the ledger (they still
show and block accept in their own round). That name collision already exists on `main`
(the selection step deletes that file), and reserving the id belongs to the advisory
selection policy.

## Verification
Line numbers are on `main` at `41210bc` unless marked "patched".

- **Claim:** the note's row was an ordinary HUMAN row and so was deferred.
  **Checked:** `template/src/pdca_harness/assemble.py:405-409` reads every
  `check-advisory-*.md` with only the placeholder callback; `leaves.py:3637-3642` writes the
  note with no leaf-status marker; `autoiterate.py:320-326` skips only `no_verdict` rows;
  `assemble.py:654` (`_deferred_needs_human`) adds every ledger entry back to §6.
- **Claim:** a note in the bundle always comes from the current Check, so not deferring it
  loses nothing.
  **Checked:** an iterate archives `check-advisory-*.md` (`state.py:155`), and every
  vendor-complement selection first deletes the old note (`leaves.py:3655`), then writes it
  again only if selection still fails (`leaves.py:3675`).
- **Claim:** a round 2 that writes no note shows no note in §6, and the ledger does not
  hold it; ordinary advisory findings are still deferred.
  **Test:** `template/tests/test_autoiterate.py`,
  `test_a_note_round_2_did_not_write_is_not_carried_into_its_section6` (patched
  `:2521-2536`). Round 1 runs the real advisory selection, the real auto-iterate decision
  and the real iterate; round 2 runs through `driver.run_issue`.
- **Claim:** a round 2 that writes the note again shows it once, as an open row that blocks
  accept until ticked.
  **Test:** `test_a_note_round_2_wrote_again_shows_once_and_blocks_accept` (patched
  `:2538-2558`).
- **Claim:** the flow notice no longer calls the note a row "with no verdict".
  **Test:** `test_the_flow_notice_does_not_call_the_note_a_row_with_no_verdict` (patched
  `:2560-2575`); the existing #409 notice assertion (patched `:766-767`) is updated to the
  new wording.
- **Red → green:** with the production hunks reverted and the tests kept,
  `tests.test_autoiterate` runs 148 tests with 7 failures (the 3 new tests plus 4 subcases
  of the notice assertion); round 2's §6 shows the round-1 note carried from the ledger.
  With the patch: 148 tests, OK, both via `python -m unittest` and run as a script.
  Placing the check in the `no_verdict=` callback instead leaves all 3 new tests red.
- **Full suites:** root suite 24 tests OK; template suite 2426 tests OK (2 skipped); docs
  lint and site render clean.

Fixes #605
