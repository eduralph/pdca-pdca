# Advisory code review — issue 496 / pin-split-never-aborts-flow

**Verdict: the diff is clean on both lenses.** I found no correctness bugs. The only cleanups are two optional nits. The patch changes tests only (`template/tests/test_flow_adopt_split.py`), and nothing under `template/src/` changes, which matches the brief.

## Mutants replayed (scratch copy of `$PDCA_TARGET/template`, Python 3.14.4)

Command: `PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split`

- Unmutated: `Ran 29 tests … OK`. Run 3 more times together with `test_flow_adopt_recovery` and `test_flow_single_driver`: OK each time, so no flakiness and no leaked monkeypatch was seen.
- M1 (`template/src/pdca_harness/flow.py:1286` `if tail is None:` → `if False:`): `test_a_failed_reschedule_after_a_split_never_aborts_the_run` ERROR, `TypeError: must assign iterable to extended slice`.
- M2 (`template/src/pdca_harness/flow.py:1098` → `except ZeroDivisionError`): same test ERROR, `RuntimeError: levelling blew up`.
- M3 (`template/src/pdca_harness/flow.py:878` `return None` → `raise`): `test_a_child_whose_path_will_not_resolve_never_aborts_the_run` ERROR, `OSError: cannot resolve …/issue_601`.
- Plan review's 4th mutant (`wave_list[k + 1:] = []` added inside the `if tail is None:` branch): the reschedule test FAILs. It fails at `template/tests/test_flow_adopt_split.py:1279` (`1 != 0` on rc), which is earlier than the `'PLANNED' != 'COMPLETE'` the brief predicted. Either way the mutant is caught.

All three required mutants are killed, each by a new test, when only that module runs. That meets the success criterion.

## Findings

- `template/tests/test_flow_adopt_split.py:1321-1322` — correctness looks fine. `Path.resolve` is patched on the class for the whole process. The cleanup is registered right after the patch, inside `after_split`, so it runs even if `_cli` raises. The wrapper only raises for `.name == "issue_601"` and passes every other call to the real method, so other tests and the fixture's `shutil.rmtree` cleanup are not affected. Injecting at `pathlib.Path.resolve` rather than at `flow._real` is what lets M3 be seen, and the replay confirms it. No action.
- `template/tests/test_flow_adopt_split.py:32` (nit, optional) — the new `import pathlib` is redundant, because `Path` is already imported and is the same class object. `real_resolve = Path.resolve` / `setattr(Path, "resolve", …)` would do the same thing. Keeping `pathlib.Path.resolve` does make the patch site match the brief's wording word for word, so leaving it is also fine.
- `template/tests/test_flow_adopt_split.py:1225-1238` (nit, optional) — the new comment block and docstrings cite `flow.py` line numbers (`:1087-1088`, `:1092`, `:1098`, `:1286`, `:876-878`, `:1649`). The brief asks for this so the mutants can be replayed, but these numbers will drift with any edit to `flow.py`. Naming the function next to each line number (it mostly does already) makes the replay notes easier to maintain. No action needed for this cycle.

No NEEDS-HUMAN items from this lens. The C4 `unverifiable` result (`gate-logs/C4-verify.log`) is the expected outcome for a test-only patch, as the brief says. The mutant replay above is the evidence that stands in for it.
