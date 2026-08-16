# Advisory code review — issue #475 (no-new-session-notice-waits-for-the-guard)

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:252-256`. The new gate
  `if outcome != "blocked":` is broader than "the decision was actually applied." It also
  admits the two other non-`"blocked"` failure outcomes of `_apply_decision`:
  - `None` from the "no SUMMARY.md" drop (`flow.py:161-165`, which already prints
    `"... skipping record, will re-drive"` on the line immediately before),
  - `REASSEMBLE`/`None` from `_repair_unsignable` (`flow.py:114-130`, reached via
    `unrecordable()` at `:173-175` or the `ValueError` repair at `:186-192`, which already
    prints `"decision '<action>' not recorded (...); ... bundle returned to ... to reassemble"`).
  In both cases the decision was explicitly **not** recorded — the code just printed a message
  saying so — yet `_apply_recorded_decision` now prints, on the very next line,
  `"flow: <bundle> — applied the '<action>' sign-off decision already recorded in the bundle;
  no new session"`. That is a definite, past-tense claim ("applied") of a result that the
  preceding line just said did not happen; it is the same "notice claims a result a downstream
  step can still withdraw" defect the brief is fixing, reappearing one guard downstream of the
  one this patch targeted (C6). The old wording ("applying …", printed before the call) was at
  least ambiguous about success; the new wording is unambiguous and, for these two outcomes,
  false. The condition should gate on genuine success — e.g. `if outcome == action:` — not
  merely `!= "blocked"`. This path is reachable in exactly the scenario the fix is about: an
  orphaned decision already on disk (issue #453) whose bundle also lost/mangled its
  `SUMMARY.md` between the session and the driver's next pass — plausible, and structurally
  identical to `test_signoff_survives_a_leaf_that_reset_the_bundle`
  (`template/tests/test_flow_slice.py:316-336`), except reached via
  `_apply_recorded_decision` rather than a live session, which no test in this diff or the
  existing suite exercises. C4's red/green pair only covers the `"blocked"` case and the
  ordinary successful applies (`test_signoff_orphan.py:168,241,121,219`), so this gap passes
  every gate in `check-gates.json` undetected.

- `template/src/pdca_harness/flow.py:245-247` (docstring). "`'blocked'` is the one outcome
  where a session follows … so it is the one outcome that must not get this notice" restates
  the same over-generalization as the code bug above — it conflates "not blocked" with
  "successfully applied." Worth correcting alongside the code fix so the docstring doesn't
  keep asserting the same false dichotomy once the condition above is narrowed.

- `template/tests/test_signoff_orphan.py:186-189` and `:262-265` — minor reuse nit, not a
  defect. Both new assertions re-derive, inline, exactly what `_Base._announced`
  (`test_signoff_orphan.py:111-115`) already computes (lines matching both `d.name` and a
  substring); `self.assertFalse(self._announced(d, "no new session"), ...)` would say the same
  thing without duplicating the list comprehension across two test classes.

## Scope note

Both C6-guard-adjacent behaviours the brief targets — the announce-before-decide reordering
and the C6-refused case staying silent on "no new session" — are correctly fixed and covered
by `C4-verify` (log confirms red pre-fix on both drive paths, green post-fix). The first
finding above is the only correctness concern found in this diff; it sits just past the
brief's stated out-of-scope boundary (`_apply_decision`'s repair paths, `:161-192`) but is
introduced by the same edited condition/wording, so it is flagged as an implementation
narrowing rather than a new scope item.
