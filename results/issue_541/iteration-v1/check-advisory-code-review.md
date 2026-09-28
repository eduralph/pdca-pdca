# Advisory code review — issue #541 (dead-attempt harvest)

Reviewed `patch.diff` against the target source (`leaves.py`, `assemble.py`, `state.py`),
traced every branch of `_LeafHarvest` (`leaves.py:781-907`) and its three call sites
(`leaves.py:2744-2754`, `:3099-3110`, `:3402-3412`), and cross-checked against
`gate-logs/C4-verify.log` (confirms a genuine red pre-fix / green post-fix leg — 9
failures + 2 errors without the fix, 9/9 with it — driven through the real entry points).

**No correctness bugs introduced by this patch, and no reuse/duplication left on the
table.** Specifics I checked and found sound:

- `_LeafHarvest.withdraw` (`leaves.py:843-866`) is called for every dying attempt
  unconditionally, before the transient/stop-rule check
  (`leaves.py:750-754`), so the *last* attempt's residue is preserved exactly like every
  earlier one's — matches brief criterion 5 and is exercised by
  `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract`.
- `_disown`'s un-owned message (`leaves.py:899-903`, worded "the leaf exited 0, but…") is
  only ever read back in `run()` after `err is None` is confirmed
  (`leaves.py:830-837`) — i.e. only once the leaf really has exited 0 — so the message is
  never stale/misleading despite being written at disown-time, before that outcome is known.
- On a leaf that exhausts all attempts without ever exiting 0, `self._unowned`/`_account` are
  set but never read (`run()`'s `err is not None` branch bypasses them); the same residue
  text still reaches the bundle because `_invoke_leaf_resilient`'s own settled-record write
  (`leaves.py:769`) already includes every `withdraw()` return value. No double-write, no
  lost residue.
- `_preserve()` (`leaves.py:878-897`) deliberately does not use
  `state.settled_record`/`unfinished_record` but its own `_WITHDRAWN_TRAILER`
  (`leaves.py:773-778`), which is a distinct string from `state.ATTEMPTS_SPENT_MARKER`, so
  `state.leaf_ran_and_failed` correctly reads `False` on a preserved-but-unsettled log —
  verified against `state.py:182-196` and matches
  `test_the_preserved_account_never_reads_as_a_leaf_that_spent_its_attempts`.
- All three call sites pass `empty_reason`/`failed_reason` strings identical to what the
  three hand-written branches used to say (`"reviewer produced no check-review.md"`,
  `"produced no artifact"` ×2, `"leaf failed"` default vs `"reviewer leaf failed"`
  override), so the refactor is behavior-preserving on the non-#541 paths, not just on the
  new one.
- `assemble._items_from_artifact`'s fallback to `_UNKNOWN_LEAF_STATUS_LABEL`
  (`assemble.py:190-191`) closes the same hole the brief's C4 red leg exercised
  (`test_an_unrecognised_status_is_still_a_placeholder_never_a_verdict`) without weakening
  the existing recognised-status paths — `if not label: return items` is unchanged for the
  real "no marker at all" case.
- The de-duplication itself (brief criterion 6) is real, not cosmetic: all three call sites
  now route through the one `_LeafHarvest` class, and `test_all_three_sites_go_through_the_one_owner`
  drives that by substituting a recording subclass at the module attribute the call sites
  resolve dynamically (`leaves._LeafHarvest`), which is a valid patch point since Python
  resolves a bare name against module globals at call time.

If the diff is clean on both lenses, say so explicitly: **it is clean.** No findings to
route to a human or back to Do.
