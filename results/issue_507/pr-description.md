## Summary
**User impact:** A project generated from this template inherits permanently red
tests the moment it follows the template's own instructions. Enable the sandbox
opt-in and the offline test suite goes red with no green option — deleting the
commented example fails one test, keeping it fails another. Replace the skeleton
verify script with a real one, as the script itself instructs, and eight wording
tests fail on updating to v0.57.0. Nothing is actually wrong with such a
project.

This PR scopes each of those assertions to the posture where it actually holds,
so the shipped suites stay green in every configuration the template sanctions —
while the protections that really do bind every instance keep biting everywhere.

Reported in [#507](https://github.com/eduralph/pdca-harness/issues/507).

## What to look at
The whole change is three shipped test modules — `template/tests/test_families.py`,
`template/tests/test_verify_red_leg.py`, `template/tests/test_verify_base.py`.
No production, template-config, or documentation file changes; this is the same
treatment #386 (merged as PR #426) gave the remote-control docs suite, applied
to the three remaining offenders.

To see the defect on `main`: render an instance, uncomment its `[leaves.sandbox]`
example (keeping or deleting the commented block — either way), and run the
shipped suite: one test fails in every layout. Or replace the verify-script
skeleton with a real gate and run the two verify-wording modules: 8 failures.
With this patch, one offline run covers all of those configurations
synthetically:

    cd template && PYTHONPATH=src python3 -m unittest \
        tests.test_families tests.test_verify_red_leg tests.test_verify_base

## Root cause
Two of the sandbox assertions encode the template's own default rather than an
invariant: `test_leaves_sandbox_is_declared_exactly_once`
(`template/tests/test_families.py:353` on `main`) counts commented and active
`[leaves.sandbox]` headers together (`^#?\s*\[leaves\.sandbox\]\s*$`) and
requires exactly one, while `test_the_commented_example_parses_when_uncommented`
(`:359`) requires a commented example to exist — so an instance with an active
table fails one or the other in every layout. Likewise the seven
`C4RedLegVerdictRule` cases (`template/tests/test_verify_red_leg.py:65-141`) and
the base-ladder case (`template/tests/test_verify_base.py:293-301`) string-match
`engine/scripts/run-verify.sh`, whose own line 2 says "SKELETON. Fill this in
for your project." (`engine/README.md.jinja:31,84` repeat the instruction) —
properties of what the template *publishes*, asserted against the one file every
instance is told to overwrite.

## Fix
Applies the rule 75294d17190177f720d5989b1f65a79561f5d54e (PR #426) established:
a suite shipped into renders asserts only what holds in every posture the
template sanctions; template-default-only properties bind the template checkout.

- `test_families.py`: the old pair becomes three tests — at most one ACTIVE
  `[leaves.sandbox]` header (every posture; two is the PR #292
  unparseable-file defect), a commented example that is still present must
  round-trip to valid TOML under one table with an unquoted boolean (every
  posture; absence is not a defect), and "the commented example is still
  present" (template checkout only, skipped once rendered). `_source()` now
  returns `(text, rendered)` so the posture is visible at the assertion site.
- `test_verify_red_leg.py` / `test_verify_base.py`: the skeleton-wording cases
  skip once rendered, with the posture read off the project root's
  `pdca.toml(.jinja)` — the same signal `test_remote_control_docs.py` uses,
  since `run-verify.sh` carries no `.jinja` suffix of its own.
  `run-verify.sh` and the engine README are not touched, and
  `EngineReadmeExplainsTheRule` — the instance-binding half of the two-facts
  rule, asserted against `engine/README.md`, which ships to every render and
  is not a fill-in file — is unchanged.
- New posture-regression classes (`ShippedPdcaTomlExamplePostures`,
  `C4SkeletonWordingPostures`, `C4BaseLadderPostures`) drive the *real*
  TestCases in-process against synthetic text for each sanctioned posture — via
  overridable source attributes, never a reimplementation and never a
  subprocess — with negative controls proving the skips do the work.

## Verification
- **Claim:** an instance with an active sandbox table had no green option.
  **Checked:** `template/tests/test_families.py:353-362` on `main` — evaluating
  the two pre-fix assertions over the three layouts yields PASS/PASS (default),
  PASS/FAIL (active, example deleted), FAIL/PASS (active, example kept); also
  observed live in a real enrolled instance.
  **Test:** `ShippedPdcaTomlExamplePostures.test_active_table_without_the_example_is_loadable`
  and `…test_active_table_with_the_kept_example_is_loadable` — each layout fails
  the pre-fix assertions (one failure each) and passes post-fix.
- **Claim:** a filled-in verify gate fails exactly 8 wording cases pre-fix.
  **Checked:** `template/tests/test_verify_red_leg.py:65-141` (7 cases) and
  `template/tests/test_verify_base.py:293-301` on `main` string-match
  `engine/scripts/run-verify.sh`; running the pre-fix modules against a
  synthetic filled-in gate reproduces `FAILED (failures=8)`.
  **Test:** `C4SkeletonWordingPostures.test_a_filled_in_gate_missing_the_wording_is_not_flagged_once_rendered`
  and `C4BaseLadderPostures.test_a_filled_in_gate_missing_the_ladder_is_not_flagged_once_rendered`
  — green post-fix, each with a negative control
  (`…would_fail_if_it_were_still_bound`) showing the identical fixture still
  fails the 7/1 cases when the posture scope is off.
- **Claim:** the PR #292 protection (two active tables ⇒ unparseable
  `pdca.toml`) still bites in every posture.
  **Test:** `ShippedPdcaTomlExamplePostures.test_two_active_headers_still_fails`
  — asserts the loosened suite still fails on two active headers AND that
  `tomllib` itself refuses the file (the real defect, not a suite artefact).
- **Claim:** the template checkout keeps every guarantee it has today.
  **Checked:** the run above → `Ran 71 tests … OK` (60 pre-fix); the posture-(i)
  cases drive the real checkout text and stay green;
  `EngineReadmeExplainsTheRule` (`template/tests/test_verify_red_leg.py:144-173`)
  and every other case in the three modules are untouched.

Fixes #507
