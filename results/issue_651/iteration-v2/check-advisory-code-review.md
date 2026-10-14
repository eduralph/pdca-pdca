# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

The diff is clean on both lenses. It changes `#` comment lines only, in one file (`template/src/pdca_harness/flow.py`). There is no code change, so it cannot introduce a runtime bug, and the T3 suite passes (`gate-logs/T3-suite.log`: 2423 tests, OK). I checked each claim in the new wording against the patched tree:

- `template/src/pdca_harness/flow.py:2141-2145` — the "exactly as before" and "adoption never relaxes it" wording is gone. The new text names the single #590 relaxation and points ahead to the `offered` paragraph. The stale `waves.py:243-246` line reference is replaced by a symbol reference (`waves.partition_schedulable`'s docstring). The brief allows that, and the quoted text does exist at `template/src/pdca_harness/waves.py:277-279`. Correct.
- `template/src/pdca_harness/flow.py:2158-2166` — "resolvable here instead of raising, but adds NO edge in `compute_waves`" matches the `continue` at `template/src/pdca_harness/waves.py:95-96`. "The splice orders it" matches the `check_dep_graph` docstring at `waves.py:74-79`. "A `Stacks on` edge still refuses" matches the `dep not in stacks` guard at `waves.py:95`. Both facts the brief requires are present.
- `template/src/pdca_harness/flow.py:2163` — "a loop through the child is found and held — never a raise" is true. The splice re-levels through `_reschedule` → `waves.partition_schedulable` (`flow.py:1521`), which holds cycle members (`waves.py:319-323`) instead of raising.
- `template/src/pdca_harness/flow.py:2164` — "if adoption does not take the child, its dependent is held or skipped" matches the `_offered_by_seeds` docstring (`flow.py:2018-2020`).
- Minor wording point, not worth a change: `flow.py:2144` says "one relaxation", and `flow.py:2158` then calls it "That relaxation". The two paragraphs are split by the unrelated RE-levelling paragraph (`flow.py:2147-2156`), so a reader has to scroll back to find what "That" refers to. The paragraph names the relaxation again right away ("A `Depends on` / `Depends on (merged)` edge to such a child..."), so this does no real harm.

Reuse / simplification: nothing to flag. The new paragraph repeats some of the `check_dep_graph` docstring (`waves.py:74-79`), but the brief asks for both facts to be stated at this call site, so the repetition is intended.

No NEEDS-HUMAN findings from this lens. The C4 `unverifiable` result (exit 77, no test shipped) is the expected outcome for a comment-only change, as the brief explains. I'm not raising it again here.

<!-- pdca:leaf-complete -->
