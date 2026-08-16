## Summary
**User impact:** Checks that have nothing to do with verifying a fix — the full
offline test suite, a docs lint, the contribution audit — were run with a
base-branch setting in their environment that only the fix-verification step is
supposed to receive. Any test suite that reads that setting then behaved as if it
had been aimed at a different branch, so checks failed for reasons unrelated to
the change being reviewed. Worse, the failures could not be reproduced by hand:
running the same command yourself sets nothing, so the check passes, and the red
looks like a flake. On this project it showed up as eleven failures in one run
while the same suite was green everywhere else.

This PR delivers the base setting to the one check that actually needs it — the
per-fix verifier — and to no other, so every other check runs in a clean
environment again. Reported in
[#474](https://github.com/eduralph/pdca-harness/issues/474).

## What to look at
A check row can now say `verifies_base = true` in its `[[gates.checks]]` entry to
declare itself the row that rebuilds the base branch before applying a patch. If
it says nothing, the answer defaults to "is this the `C4` row?" — which every
verifier row shipped by this project already is, so **no existing configuration
needs an edit to keep working**. That default is the part worth a second opinion:
if a project has wired a non-`C4` row to read the base branch out of the
environment, it must now add `verifies_base = true` to that row. Rows on the
host-CI path are affected in the same way — they also stop receiving the base;
they never reset to it, but it is a real change beyond the reported symptom and
is called out here on purpose rather than buried.

To try it: configure two checks that print the three base variables — one tagged
`tier = "C4"`, one anything else — and run the checks over a fix. Before this
change both print the resolved base; after it, only the `C4` one does. That is
exactly what `template/tests/test_verify_base.py` does, so running that module is
the quickest way to see the behaviour.

## Root cause
`template/src/pdca_harness/gates.py:524-536` exported one of `PDCA_BASE` /
`PDCA_VERIFY_BASE` / `PDCA_BRIEF_BASE` whenever a fix directory was attached to
the run (`if bundle is not None:`), and `gates.py:197` attaches it for
`scopes=("repo", "bundle")` — i.e. for *every* configured row of a run. The
condition therefore described the run, not the row, so a repo-wide suite row, a
docs-lint row and a host-CI row all inherited a setting addressed to the
verifier. Scope could not be used to tell them apart either: a project's own
suite row is legitimately `scope = "bundle"` as well.

## Fix
One declared row-level key and one predicate. `_verifies_base(chk)` returns
`chk.get("verifies_base", chk.get("tier") == "C4")`, and the export is gated on
it: `if bundle is not None and _verifies_base(chk):`. The shape mirrors the
`at_publish` key this codebase already uses for a row-level decision — an
explicit boolean that wins in either direction, over a derived default
(`template/src/pdca_harness/publish.py:767,778`). The ladder's resolution order
and its fully-qualified `<remote>/<branch>` values are untouched; only who
receives the value changed. The row-level contract is documented where
`[[gates.checks]]` keys are documented (`template/pdca.toml.jinja:908-917`) and in
the verifier skeleton's own header comment
(`template/engine/scripts/run-verify.sh:13-19`), whose ladder-resolution sentence
is left verbatim because other tests assert on its wording.

## Verification
- **Claim:** a row that is not the per-fix verifier observes none of the three
  variables — `scope = "repo"` and `scope = "bundle"` rows alike.
  **Checked:** `template/src/pdca_harness/gates.py:524-536` and `gates.py:197` on
  `main` — the export keys on the run, and the run covers every configured row.
  **Test:** `template/tests/test_verify_base.py`,
  `test_only_the_verifier_row_receives_the_ladder` — two extra rows (one
  `scope = "repo"`, one `scope = "bundle"`) echo what their subprocess really saw;
  fails pre-fix with `['UNSET', 'UNSET', 'origin/main'] != ['UNSET', 'UNSET',
  'UNSET']`, passes post-fix.
- **Claim:** this is not only the stacked-run symptom — the third rung
  (`PDCA_BRIEF_BASE`) is exported on every ordinary run and must stay off
  non-verifier rows too.
  **Checked:** `template/src/pdca_harness/gates.py:509-520` on `main` — rung 3 is
  documented as exported unconditionally, and `gates.py:534-536` exports it in the
  `else` branch every run without an `Onto branch` or a stack marker reaches.
  **Test:** `test_the_unconditional_brief_base_rung_also_stays_off_non_verifier_rows`
  — an ordinary run with no `Onto branch` and no stack marker; fails pre-fix,
  passes post-fix.
- **Claim:** the verifier still gets exactly one variable, resolved by the same
  unchanged ladder and with the same value as today.
  **Checked:** `template/src/pdca_harness/gates.py:495-524` on `main` — resolution
  block unedited by this PR.
  **Test:** the pre-existing cases in the same module
  (`test_onto_branch_wins_over_the_wave_base` at
  `template/tests/test_verify_base.py:151`, the brief-base cases at `:214-289`, and
  `test_exactly_one_base_is_exported_for_every_bundle` at `:291-307`) all pass
  unmodified.
- **Claim:** a project whose verifier row predates this change does not silently
  lose its base.
  **Checked:** `template/pdca.toml.jinja:908-917` and
  `template/tests/test_verify_base.py:47-51` on `main` — every shipped verifier
  row already carries `tier = "C4"` and no `verifies_base` key.
  **Test:** `test_a_predating_c4_row_keeps_its_base_with_no_config_edit` — asserts
  the untouched row still receives the base; passes on both sides of the change by
  design (it guards the compatibility half, not the defect).
- **Claim:** the declaration overrides the default in both directions.
  **Test:** `test_an_explicitly_declared_non_c4_verifier_still_receives_the_base`
  and `test_a_c4_row_can_opt_out_explicitly`.
- **Claim:** nothing else about a check's environment changes.
  **Checked:** `template/src/pdca_harness/gates.py:491-494` (`PDCA_BUNDLE`,
  `PDCA_WORKTREE`) and `gates.py:537-541` (`PDCA_LANE`) on `main` — all outside
  the changed condition and unedited.
  **Test:** whole offline suite, `1763` tests, green (`cd template && PYTHONPATH=src
  python3 -m unittest discover -s tests`).
- **Red-leg method:** the production file alone (`template/src/pdca_harness/gates.py`)
  was reverted while every test hunk stayed in place; three of the new cases failed
  on the leaked base and no others, then all 27 passed with the fix restored — so
  the new tests fail for the defect, not for an import error.

Fixes #474
