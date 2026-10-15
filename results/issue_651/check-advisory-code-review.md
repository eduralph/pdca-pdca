# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

The diff is clean on both lenses: no correctness bug and no reuse/simplification finding. No NEEDS-HUMAN items from this lens.

- Comment-only change. Every added and removed line in `patch.diff` is a `#` line in `template/src/pdca_harness/flow.py` (`flow.py:2141-2145`, `flow.py:2158-2167`), and no other file changes. T3 passes (`gate-logs/T3-suite.log`: root suite OK, driver suite OK), so the file still parses.
- The claims in the new text match the code:
  - An offered `Depends on` / `Depends on (merged)` edge is skipped without adding a graph edge, and a `Stacks on` edge to an offered child still falls through to the refusal. See `template/src/pdca_harness/waves.py:95-96` (`if dn in offered and dep not in stacks: continue`) and `waves.py:102-109`.
  - `offered` comes from `_offered_by_seeds` and is passed into `compute_waves`; the child is spliced in later at `k=-1`. See `flow.py:2168-2170` and `flow.py:2176-2178`.
  - "A loop through the child is not seen here … it holds such a loop instead of raising" matches `template/tests/test_flow_adopt_recovery.py:948-972`.
  - The cited test `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it` exists at `test_flow_adopt_recovery.py:769`.
- The stale `waves.py:243-246` line reference was dropped rather than renumbered (`flow.py:2143-2144`). The brief allows a symbol reference with no line number, and the quoted text is still at `waves.py:278-279`. Dropping the number avoids the same drift happening again.
- Minor wording point, no action needed: the first paragraph (`flow.py:2141-2145`) says the strict check "raises on a cycle", then names only the edge as the one relaxation. A cycle through an offered child also goes unraised as a result. That is stated 15 lines later (`flow.py:2160-2163`), and the first paragraph points the reader there, so the block does not contradict itself.

<!-- pdca:leaf-complete -->
