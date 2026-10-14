## Summary
**User impact:** Anyone reading or changing the `flow` driver's scheduling code is told,
in the comment right above it, that the ids you name on the command line are checked
"exactly as before" and that picking up a recovery seed's children "never relaxes" that
check. Since #590 that is wrong: such a run now accepts a dependency on one of those
children instead of refusing it. Someone trusting the comment would expect a refusal that
no longer happens, and the comment block contradicts its own later paragraph.

This PR rewrites the comment so it describes what the code does today. No code changes.

Reported in [#651](https://github.com/eduralph/pdca-harness/issues/651).

## What to look at
One comment block in `template/src/pdca_harness/flow.py`, inside `_drive_and_act`, just
above the line that builds `offered` and calls `waves.compute_waves`. Read the new wording
next to `waves.check_dep_graph` (the `offered` handling) and decide whether it says the
same thing the code does. Nothing runs differently, so there is nothing to reproduce; the
existing #590 tests in `template/tests/test_flow_adopt_recovery.py` exercise the
behaviour the comment describes.

## Root cause
#590 (29a79433456b01521e3c59fb2103223bfb2e6cdc) added the `offered` path, which lets a
`Depends on` edge to a recovery seed's in-flight child pass the up-front check, and added
a paragraph saying so at the bottom of the block. The opening paragraph, which still says
"exactly as before … adoption never relaxes it", was left unchanged. It also cited
`waves.py:243-246` for a docstring that has since moved.

## Fix
- **Opening paragraph:** drops "exactly as before" and "never relaxes it". It still says
  the named batch is levelled strictly (`compute_waves` raises on a cycle or an
  unresolvable dependency), and adds that since #590 there is one relaxation: a
  `Depends on` / `Depends on (merged)` edge to a child a recovery seed offers. The
  drifted `waves.py:243-246` line reference becomes a symbol reference
  (`waves.partition_schedulable`'s docstring), so it can't drift again.
- **The #590 paragraph:** spelled out so it keeps both facts. The edge is resolvable at
  the up-front check but adds **no** edge in `compute_waves`. The child joins the schedule
  only at the seed's `k=-1` splice, which re-levels with it in place, so that splice is
  what orders the edge (and holds a loop through the child instead of raising). A
  `Stacks on` edge to such a child, or any other unresolvable dependency, still refuses.
  The paragraph names the test that pins this.
- The middle paragraph (about re-levelling at splices) is unchanged.

## Verification
Line numbers are on `main` @ 41210bcd18e0b6d1b77fd5fe6e29c2bbebb6fa57 (base) unless marked
patched.

- **Claim:** the old wording is false on `main`.
  **Checked:** `template/src/pdca_harness/flow.py:2160-2162` passes
  `offered=_offered_by_seeds(...)` to `waves.compute_waves`;
  `template/src/pdca_harness/waves.py:95-96` skips (`continue`) instead of raising for a
  non-`Stacks on` edge to an offered child. Docstring at `waves.py:74-80` says the same.
  Setting `offered = frozenset()` (the world the old comment describes) makes 6 of the 8
  #590 tests in `test_flow_adopt_recovery.py` fail.
- **Claim:** the edge adds no ordering edge in `compute_waves`; the splice orders it.
  **Checked:** `waves.py:95-96` appends no edge; patched `flow.py:2176-2179` runs the
  `k=-1` splice, which re-waves with the child in place. Disabling the splice makes 4 of
  the 8 #590 tests fail, including `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it`.
- **Claim:** a loop through the child is held at the splice, not raised.
  **Checked:** `flow.py:1521-1522` (tolerant `partition_schedulable` at the splice).
  Making that re-level strict fails `test_a_loop_through_an_offered_child_is_held_never_a_raise`.
- **Claim:** `Stacks on` to an offered child still refuses.
  **Checked:** `waves.py:95` (`and dep not in stacks`) falls through to the raise at
  `waves.py:102-109`. Dropping that condition fails all three sub-cases of
  `test_stacks_on_an_offered_child_is_still_refused_up_front`.
- **Claim:** the quoted docstring text is real.
  **Checked:** `waves.py:277-279` ("right for an explicit ``flow <ids>``").
- **Claim:** comment lines only.
  **Checked:** every changed line in the diff starts with `#`; the token stream (minus
  comments) and the AST of `flow.py` are identical before and after.
- **Test:** none ships, by design — a comment can't fail a test, and a test that greps the
  comment text would only test wording. The claims above are each tied to an existing
  test that goes red when the behaviour it describes is broken. The full offline driver
  suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`) passes:
  2423 tests, OK (2 skipped).

Out of scope, noted only: the docstring of
`test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost`
(`template/tests/test_flow_adopt_split.py:598-599`) calls the splice "the one place the id
list stops being levelled strictly", which #590 also made slightly out of date.

Fixes #651
