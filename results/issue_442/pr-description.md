# PR description

## Summary
**User impact:** Anyone reading the gates module's documentation to learn how a
gate's result can change is told there is exactly one declaration that can do
it. There are two — the same document introduces the second one a few
paragraphs later — so a reader is left believing a deferral cannot change a
gate's result, when it can.

This PR corrects that one sentence so the documentation names both
declarations, and adds a regression test that keeps the claim honest.

Reported in [#442](https://github.com/eduralph/pdca-harness/issues/442).

## What to look at
One sentence in the module docstring at the top of the gates module, plus the
small test that pins it. To see the original contradiction, read the docstring
top to bottom on `main`: the evidence-marker paragraph claims a single
result-changing marker, and the deferral paragraph below it introduces a
second one.

## Root cause
The exclusivity sentence at `template/src/pdca_harness/gates.py:38` (on `main`,
`0fbfa26`) predates 07766ed3a235e623c0ecdaea7b9b90358bdb810d (#401), which
added the ``PDCA-DEFERRED`` declaration twenty lines below in the same
docstring (`gates.py:55-68`, constant at `gates.py:98`) — a second marker that
changes a `result` (to `deferred`). The #401 change never touched the older
sentence, so the docstring has contradicted itself since.

## Fix
Replaces the one false sentence with "…only the
``PDCA-UNVERIFIABLE``/``PDCA-DEFERRED`` declarations can change a ``result``"
(rewrapped across two lines to stay inside the file's prose width; nothing
else in the docstring touched, no behavioral change). Appends
`ModuleDocNamesEveryResultChangingMarker` to the #401 suite
(`template/tests/test_gate_deferred.py`): one assertion that the exclusivity
wording is gone, one that the corrected claim names both declarations. The
marker names in the expected claim are composed from the production constants
(`UNVERIFIABLE_MARKER` / `DEFERRED_MARKER`), so the test carries no second
spelling that can drift from the module, and the assertions run over a
whitespace-collapsed `gates.__doc__` so they span the docstring's wrap points
instead of pinning the current line layout.

## Verification
- **Claim:** the module doc's evidence-marker paragraph no longer claims
  exclusivity for ``PDCA-UNVERIFIABLE``; it names both ``PDCA-UNVERIFIABLE``
  and ``PDCA-DEFERRED`` as the declarations that can change a ``result``.
- **Checked:** `template/src/pdca_harness/gates.py:38` on `main` (`0fbfa26`) —
  the stale sentence this PR removes; `gates.py:55-68` and `gates.py:98` — the
  ``PDCA-DEFERRED`` paragraph and constant that the sentence denied.
- **Test:** `template/tests/test_gate_deferred.py:281-305` — both new
  assertions fail with the docstring fix reverted and pass with it applied
  (`tests.test_gate_deferred`: `Ran 19 tests … OK` patched, `FAILED
  (failures=2)` — exactly the two new tests — reverted); the full offline
  suite stays green (`Ran 1565 tests … OK, skipped=2`).

Fixes #442
