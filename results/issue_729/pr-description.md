## Summary
**User impact:** In a stacked run, when a fix's prerequisite gets merged into `main`
partway through the run, the fix is held back with "does not have that merge" and is
not built, even though the base it would be built on already contains that merge. The
only way forward today is to delete the run's integration branch on origin and re-run,
for a hold that guards nothing.

This PR checks the integration branch only for fixes that are actually built on it.
Every other fix is judged on the base it really gets, so it is no longer held for no
reason.

Reported in [#729](https://github.com/eduralph/pdca-harness/issues/729).

## What to look at
The decision of whether a fix may run now uses the same "what will this be built on"
answer that later picks its base. Fixes that still sit on the run's integration branch
(because of a `Stacks on` / `Onto branch` edge, or a prerequisite the run carried) keep
today's check and today's message. All others are judged only by whether the
prerequisite merged into their target base.

To try it: run the two test modules below. The new one shows a dependent built (not
held) after its prerequisite merges mid-run; the existing one shows a line-based
dependent still held.

```
cd template && PYTHONPATH=src python3 -m unittest \
    tests.test_flow_merged_prereq_dependency_base \
    tests.test_flow_merged_prereq_on_line
```

This builds on #727 (fixes get a base of their own, built from `main` as fetched when
their wave starts) and only makes sense with it in place.

## Root cause
`_runnable` asked `_line_lacks_merge` about the run's integration branch for every
dependent of an out-of-batch merged prerequisite. Since #727 most dependents are no
longer cut from that branch but from a base of their own (or the real base), fetched
after this check, so the question was about a tree they don't use.

## Fix
- `_runnable` takes `on_line`, the names of the wave's bundles built on the line. The
  line lookup runs only for those; `None` (the default) keeps the old rule for every
  bundle, so existing direct callers are unchanged.
- The per-bundle plan loop that was inline in `_bundle_bases` moves into a new
  `_base_plans`, which calls #727's `_closure_members` (a bundle is on the line exactly
  when that returns a seam). The wave loop calls it once per wave, derives `on_line`
  from it, and passes the same plans to `_bundle_bases`. The bundles judged on the line
  are therefore the bundles pointed at the line, by construction.
- `_line_lacks_merge` and `merged.merge_and_head` are unchanged. Docstrings in
  `_runnable`, `merged.py` and `_pr_view` now say the line check applies only to a
  bundle built on the line.

## Verification
Line numbers are on `main` with #727 applied (the base this PR is built on), with this
patch.

- **Claim:** a dependent on its own base is not held when its prerequisite merges into
  `main` after the first fold, and that base contains the merge.
  - **Checked:** `template/src/pdca_harness/flow.py:795-796`: the line is looked up only
    when `on_line is None or d.name in on_line`; otherwise `merged.merged_into` alone
    decides. The own base is built fresh from the fetched base on every call
    (`template/src/pdca_harness/integrate.py:745-748`, fetch at `:2052`), per bundle per
    wave, after `_runnable` has judged the merge.
  - **Test:** `template/tests/test_flow_merged_prereq_dependency_base.py`: both edge types
    (`Depends on (merged): P` and a plain `Depends on: P` with P not in the batch), plus
    a dependent on the real base. All three fail without the fix (held with the
    "does not have that merge" message) and pass with it. Each asserts the line exists,
    holds W, and lacks P's merge before asserting D is built on a base that has it.
- **Claim:** a prerequisite not merged into `main` still holds its dependent.
  - **Test:** same file, two "still holds" cases. They pass before and after.
- **Claim:** a dependent that a seam keeps on the line is still held, with today's
  message.
  - **Checked:** `flow.py:2690-2698` (plan once per wave, `on_line` = bundles whose plan
    is a seam), `flow.py:2713` (passed to `_runnable`), `flow.py:970-989` (`_base_plans`
    calls `_closure_members`, `flow.py:922`).
  - **Test:** `template/tests/test_flow_merged_prereq_on_line.py`: the five held cases
    now use a D with `Stacks on: W` beside `Depends on: W`; their assertions are
    unchanged. Passing `on_line=set()` (dropping the line check for everyone) makes
    exactly those five fail.
- **Full suite:** root suite 24 tests OK; driver suite 2594 tests OK (2 skipped).

Fixes #729
