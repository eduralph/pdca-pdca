# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

I found no problems with either lens (correctness, and reuse/simplification). The patch only changes `#` comment lines in one file, `template/src/pdca_harness/flow.py`. No code changed, so the patch cannot add a runtime bug. The T3 suite log shows `Ran 2423 tests ... OK (skipped=2)`, so the file still parses.

I checked the new wording against the code in the patched tree:

- `template/src/pdca_harness/flow.py:2141-2145`: the "exactly as before" and "adoption never relaxes it" claims are gone. The block now says there is "exactly one relaxation" since #590. That is accurate: `template/src/pdca_harness/waves.py:95-96` (`if dn in offered and dep not in stacks: continue`) is the only path that lets a dependency through without raising.
- The stale `waves.py:243-246` line number was replaced with a symbol-only reference. The quoted text "right for an explicit `flow <ids>`" does exist in the `partition_schedulable` docstring (`template/src/pdca_harness/waves.py:277-279`), so nothing is left that can go stale again.
- `template/src/pdca_harness/flow.py:2158-2163`: the comment keeps both facts the brief requires. The offered `Depends on` / `Depends on (merged)` edge is resolvable but "adds NO edge in `compute_waves`", and the `k=-1` splice is what orders it. This matches the `check_dep_graph` docstring at `template/src/pdca_harness/waves.py:74-80`. `compute_waves` passes `offered` straight through (`template/src/pdca_harness/waves.py:184`), and the splice call follows at `template/src/pdca_harness/flow.py:2173`.
- The `Stacks on` claim is correct. An offered child that is a `Stacks on` target fails the `dep not in stacks` test (`waves.py:95`), then gets checked with `cfg.bundle(dep)` for COMPLETE (`waves.py:102-103`). An in-flight child is not COMPLETE, so it raises.
- Minor, no action needed: the `k=-1` splice is now explained in two places, the reworded paragraph at `flow.py:2158-2163` and the existing recovery comment at `flow.py:2166-2170`. They agree, and the brief allowed rewording the #590 paragraph, so this is fine.

I saw no other stale strict-levelling text near the edit. The `_offered_by_seeds` docstring at `template/src/pdca_harness/flow.py:2003-2007` already describes the #590 behavior correctly.

C4 reports `unverifiable` (the patch ships no test). The brief expects that for a comment-only change, and the harness already sends that row to §6 for a human to read. I am not filing a separate finding for it.

<!-- pdca:leaf-complete -->
