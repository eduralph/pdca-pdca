# Advisory code review — issue 621 (merge-confirm-requires-complete-rollup)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Grounded on
`$PDCA_TARGET` (patch applied on `b5f5c29`).

**Overall: no correctness bugs found.** The wait loop, the multiset compare and the
fail-closed config path do what the brief asks. The gate logs agree: T3 ran 2379 tests OK,
and C4 shows red before the fix and green after. The notes below are minor and none needs
a human.

## Correctness

- `template/src/pdca_harness/merge.py:253-258`: the confirm logic is right. `first = names`
  is taken from the green that passed the budget check. When the confirm read is green over
  a different set, the outer `while True` goes round again: the inner pending loop is
  skipped, because the verdict is green, and the budget check at `:247-250` either confirms
  it a full poll interval later or refuses. So the existing budget rules stay as they were.
  Multiset compare holds because `_check_rollup` returns `tuple(sorted(...))` (`:153` in the
  diff), with duplicates kept. No bug.
- `template/src/pdca_harness/merge.py:181-193` (`_read_rollup`): the declared list is only
  checked on a `green` verdict, so a `failing`/`pending` read keeps its own detail. That is
  correct. The `wait_secs <= 0` path (`:232-234`) goes through `_read_rollup` too, so
  criterion (1b) is met.
- `template/src/pdca_harness/merge.py:427-431`: the malformed-setting refusal comes before
  the `merge_requires != "required"` branch (`:456`). So it also refuses every PR when
  `merge_requires = "required"`, where `expected_checks` is never read. That matches the
  brief's wording ("in merge mode every PR is refused") and errs toward refusing, so it is
  not a defect. It is just stricter than it has to be for that mode.
- Every `_check_rollup` caller is updated. The return went from a 2-tuple to a 3-tuple,
  and `grep` finds no other caller in `template/src` or `template/tests`.

## Small cleanups (optional, not blocking)

- `template/src/pdca_harness/config.py:902` strips declared names, but `merge.py:170-171`
  (`_name`) does not strip the names it reads back from the rollup. If a check name had
  stray whitespace it would never match, and every PR would wait out the budget and refuse.
  That fails closed and is unlikely in practice. Stripping in `_name` too, or not stripping
  in the config, would keep the two sides the same.
- `template/src/pdca_harness/merge.py:248-250`: if the budget runs out right after a
  changed-set confirm, the refusal says "green first seen with Ns of wait budget left". It
  does not say the check set changed between reads, so an operator reading the log gets less
  help. This is a wording nit only.
- `template/src/pdca_harness/merge.py:174-178`: `_names` now uses the new `_name` helper,
  so nothing is duplicated. Reuse is good.

## Tests

- `template/tests/test_merge.py` (new class `MergeConfirmRequiresCompleteRollup`) covers
  criteria (1), (1b), (2), (3) and (4) through both `_wait_for_green` and the real
  `merge_wave` → `_merge_one` path. The test for a changed set with the budget exhausted
  (29 s, two reads) pins the "no second confirm" edge. I found no test that checks a value
  without exercising the fix.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
