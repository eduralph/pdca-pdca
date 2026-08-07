# PR description

## Summary
**User impact:** Anyone who switches on the documented Remote Control option in their own
generated project immediately gets a red test suite. The shipped tests insist that the
option stays commented out — even though switching it on is exactly what the documentation
invites people to do. The only escape is to hand-edit a test file the template owns, and to
re-apply that edit after every template update; one downstream project is already carrying
such a patch.

This PR changes the check to assert what is true in *every* configuration the template
sanctions — the option may only be turned on for the steps that hand the terminal to a
human — instead of pinning the template's own factory default. Reported in
[#386](https://github.com/eduralph/pdca-harness/issues/386).

## What to look at
One file changes, `template/tests/test_remote_control_docs.py`; nothing outside the tests is
touched, and the Remote Control guidance in `pdca.toml.jinja` is deliberately left alone.

To try it: run `cd template && PYTHONPATH=src python3 -m unittest
tests.test_remote_control_docs`. On `main` today, a generated project whose config has
`--remote-control` appended to the planner's command line fails with
`--remote-control is active, not commented: …`; with this change it passes, while the same
flag on the headless builder or reviewer — the configuration the docs warn against, because
it opens an interactive session nobody is there to answer — now fails and names the
offending entry.

## Root cause
`test_it_stays_off_by_default` walked every line of the config and required each mention of
`--remote-control` to be commented out. That is the *template's* default, not an invariant:
the same test module is shipped into rendered instances (it resolves `pdca.toml.jinja` or
`pdca.toml` and already scopes one case with `skipUnless(RENDERED, …)`), and an instance
enabling the seam is a sanctioned configuration. The property that does hold everywhere —
the flag may only ride an `interactive = true` leaf — was never asserted on its own; the
blanket comment check caught a headless leaf only incidentally, so scoping it would have
removed the real protection along with the false failure.

## Fix
- `remote_control_offenders()` (plus a small `_sections()` splitter reusing the module's
  existing line-anchored `re.split` idiom, widened from `[leaves.` to every table so an
  active flag parked outside a leaf block cannot slip past) returns every *uncommented*
  `--remote-control` line that is not inside a leaf declaring `interactive = true`.
- `test_the_flag_rides_only_an_interactive_leaf` asserts that in **both** postures.
- `test_it_stays_off_by_default` is kept, now `skipIf(RENDERED, …)` with a docstring saying
  which posture it binds — mirroring the module's own precedent for posture-bound cases.
- A `RemoteControlPostures` class builds rendered-shaped configs in a temp directory and
  both calls the helper directly and copies this very test file into that temp checkout to
  run it under `unittest discover`, so each posture is exercised end to end.

## Verification
- **Claim:** the suite passes on the unrendered template, where the flag ships commented.
  **Checked:** `template/tests/test_remote_control_docs.py:130-146` scopes the
  off-by-default case to that posture; `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_remote_control_docs -v` → `Ran 10 tests … OK (skipped=1)`, the skip being the
  pre-existing rendered-only duplicate-`argv` count.
- **Claim:** the suite passes on an instance that enabled the flag on its interactive leaves
  (planner / signoff / publisher / act) — the case that is red on `main`.
  **Checked:** `template/tests/test_remote_control_docs.py:53-73` (the offender rule) and
  `:194-198` / `:225-229`, which assert it for all four leaves and then run the whole module
  inside a temp checkout whose config carries the uncommented flag.
- **Claim:** the suite still fails on an instance carrying the flag on a headless leaf.
  **Checked:** `template/tests/test_remote_control_docs.py:117-128` and `:200-207` /
  `:232-238` — the end-to-end case asserts a non-zero exit *and* that the output names
  `leaves.builder`, so the failure comes from the protection rather than from a generic
  complaint.
- **Claim:** the existing assertions are unaffected in both postures.
  **Checked:** the doc-phrase cases (`APPEND`, "do not add a second", `CLAUDE-ONLY`,
  "headless builder/reviewer must NOT carry it") and the duplicate-`argv` count at
  `template/tests/test_remote_control_docs.py:79-115` are unchanged from
  `main` (`5e655c2`, where they sit at `:31-67`); the synthetic configs include the doc
  block so those cases really run in the rendered posture too.
- **Test:** `template/tests/test_remote_control_docs.py` — the defect is this module, so the
  regressions ship in it. Against the module as it stands on `main`, both new end-to-end
  cases fail (the enrolled-instance run exits 1 on the old blanket assertion; the
  headless-leaf run fails without ever naming `leaves.builder`); with this change all pass.
  A minimal one-line alternative — merely skipping the old case on rendered configs —
  was tried and rejected: it turns a headless leaf carrying the flag fully green, which the
  new protective case correctly refuses.
- **Wider suites:** `./engine/scripts/run-suite.sh` → render + update-compat `Ran 7 tests …
  OK` (these copy the working tree, so this module ran in its *rendered* posture as well)
  and the offline driver suite `Ran 1473 tests … OK (skipped=2)`.

Fixes #386
