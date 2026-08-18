# Advisory code review — correctness & reuse lens (issue #540 patch)

Reviewed `template/src/pdca_harness/{state,leaves,driver,assemble}.py` and the new
`template/tests/test_attempt_ownership.py`, grounded on the patched target tree.

## Correctness

- No bugs found that the patch introduces. Specifically verified and clean:
  - All four readers named in the brief consistently switched from `.exists()` to
    `state.leaf_ran_and_failed(...)`: `leaves.py:2150-2151` (`review_never_ran`),
    `leaves.py:2850-2851` (`run_advisory_leaves(only_missing=True)`),
    `assemble.py:420` (`_missing_review_text`), and `driver.py:176`/`:182`
    (`_resume_interrupted_check`, via the two functions above). No fifth reader was
    missed — `leaves.py:2655` (`_unavailable_classification`'s `error_log.exists()`)
    is called only after `_invoke_leaf_resilient` has already returned (`leaves.py:2562-2564`,
    `:2889-2899`), i.e. after the log is always settled, so the raw existence check there
    is correctly out of the single-point-of-truth requirement's scope.
  - `state._unsettled` (`state.py:188-200`) and `state.neutralize_leaf_text`
    (`state.py:209-222`) are consistent and idempotent: neutralization runs once per
    attempt at format time (`leaves.py:772` inside `_format_leaf_attempt`), before a
    record ever reaches `unsettled_record` (`state.py:203-206`) or the final settled
    write (`leaves.py:742`), so a neutralized line can never be mistaken for the raw
    marker on a later read.
  - The success-path cleanup (`leaves.py:721-722`, new) correctly restores "no error
    log on success" now that a failed-then-recovered attempt may have left an unsettled
    file behind; the pre-existing pre-loop `error_log.unlink(missing_ok=True)`
    (`leaves.py:705`, untouched) still needs no such guard since nothing was written by
    that point in the old or new code.
  - `_flush_attempt_records` (`leaves.py:746-759`) and the test at
    `test_attempt_ownership.py:540-549` correctly demonstrate criterion 5: a flush
    failure is swallowed and does not shorten the attempt budget, while the final
    unguarded `write_text` (`leaves.py:742`) still raises on the same failure exactly as
    the pre-patch code did — confirmed by `gate-logs/C4-verify.log` showing the retry
    count reaching 3 before the propagated `OSError`.

## Reuse / simplification

- `state._unsettled`'s "last non-blank line" scan (`state.py:197-199`) has no existing
  sibling to reuse — the closest precedent in the codebase (e.g. `drift.py:37,43,91`'s
  `.splitlines()[-1:]`) takes the literal last line rather than skipping trailing blanks,
  which is a different (and here, required) semantic, so writing it fresh is justified,
  not a missed-reuse opportunity.
- No duplicated logic, no needless work in a hot path, no resource leaks or concurrency
  issues spotted; the extra `write_text` per transient attempt is bounded by `attempts`
  (≤2 extra writes for the shipped default of 3) and is the mechanism the brief asked for.

Nothing else stood out. The diff is clean on both lenses — no NEEDS-HUMAN items.
