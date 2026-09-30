# Build notes — issue 496 / pin-split-never-aborts-flow

Target: `eduralph/pdca-harness @ main`, worktree at `f33a23f`. Test-only patch — no change
under `template/src/` (the brief rules it out, and I found nothing wrong with the production
code).

## What changed (all in `template/tests/test_flow_adopt_split.py`)

- `:32` — `import pathlib` (the seam for scenario B is `pathlib.Path.resolve`).
- `:40` — `waves` added to the module import (`from pdca_harness import …, waves`), module
  only, per the file's own docstring (`:21-23`).
- `:1225-1239` — section comment with one line per mutant (site, edit, which test dies with
  what), so the reviewer can replay them without these notes.
- `:1241` — `test_a_failed_reschedule_after_a_split_never_aborts_the_run` (scenario A).
- `:1298` — `test_a_child_whose_path_will_not_resolve_never_aborts_the_run` (scenario B).

Both are methods on the existing `AdoptSplitChildren` class, drive the run through
`self._cli([...])` → `cli._flow`, and use the existing `_briefed`, `_arm`,
`_capture_results`, `_state` helpers. No new shared helper.

### Scenario A (`:1241`)
`pdca flow 500 7 8`, 8 has `Depends on: 7`. 500 splits into 601/602 (default bodies).
`waves.partition_schedulable` is swapped for a wrapper that raises `RuntimeError` only when
its list contains `issue_601`, and records the list plus bundle 8's state at that moment;
restored with `addCleanup`. Production calls it as `waves.partition_schedulable(...)`
(`template/src/pdca_harness/flow.py:1092`), so patching the module attribute reaches it.
Asserts: raised exactly once, list contained `issue_8`, 8 was `PLANNED` then; rc 0; the
`could not re-wave … (RuntimeError: ` line (`flow.py:1099`) and the `children of issue_500
could not be scheduled; they are left in-flight` line (`flow.py:1291`); no `Traceback`;
601/602 `PLANNED` and absent from the results map; waves driven = `{500,7}` then `[8]`
(wave 0 compared sorted, since order inside a wave is not what is being pinned); 500, 7, 8
`COMPLETE` in the results map.

### Scenario B (`:1298`)
`pdca flow 500`, 500 splits into 601 and an independent 602 (`_SIBLING_TWO`, so 602 is not
held on a missing 601). The `after_split` hook swaps `pathlib.Path.resolve` for a wrapper
that raises `OSError` for `.name == "issue_601"` and calls the real method otherwise;
restored via `addCleanup`. Injected below `flow._real` (`flow.py:868-878`), not at it, as
the brief requires. Asserts: wrapper reached; rc 0; `ignoring child id '601'` (`flow.py:1037`);
no `Traceback`, no `split adoption failed`; 602 `COMPLETE`; 601 `PLANNED`, no `patch.diff`,
not in the results map.

## Red → green (mutation, not revert)

Interpreter: `/home/eddie/pdca/pdca-pdca/.venv/bin/python3` (Python 3.14.4). Each mutant was
applied in place in the worktree with `sed`, the module run, then `git checkout --
src/pdca_harness/flow.py` to restore (confirmed by `git status` showing only the test file
modified afterwards).

Command every time (from `template/`):
`PYTHONPATH=src timeout 300 .venv/bin/python3 -m unittest tests.test_flow_adopt_split`

- **Unmutated:** `Ran 29 tests … OK`.
- **M1** — `flow.py:1286` `if tail is None:` → `if False:`.
  `ERROR: test_a_failed_reschedule_after_a_split_never_aborts_the_run` —
  `TypeError: must assign iterable to extended slice`. 1 error, 28 pass.
- **M2** — `flow.py:1098` `except Exception as exc:` → `except ZeroDivisionError as exc:`.
  `ERROR: test_a_failed_reschedule_after_a_split_never_aborts_the_run` —
  `RuntimeError: levelling blew up` (the injected fault escaping `_reschedule`). 1 error.
- **M3** — `flow.py:878` (the `return None` in `_real`'s handler, `:876-878`) → `raise`.
  `ERROR: test_a_child_whose_path_will_not_resolve_never_aborts_the_run` —
  `OSError: cannot resolve …/results/issue_601`. Frames: `flow_ids` (`flow.py:2062`) →
  `_drive_and_act` (`:1832`) → `_warn_stranded_split_children` (`:1542`) → `_real` (`:875`).
  Matches the brief's prediction. 1 error.
- **Extra, M4 (plan reviewer's mutant)** — add `wave_list[k + 1:] = []` after the `print`
  in the `if tail is None:` branch (after `flow.py:1294`).
  `FAIL: test_a_failed_reschedule_after_a_split_never_aborts_the_run` —
  `AssertionError: 1 != 0` (rc: bundle 8 was never driven, so the run fails). The three-bundle
  form does catch it, as Plan found.

Full offline suite with the patch, unmutated:
`PYTHONPATH=src timeout 600 …/python3 -m unittest discover -s tests` → `Ran 2073 tests …
OK (skipped=2)` (2071 before + the 2 new ones). So the `Path.resolve` / `partition_schedulable`
swaps do not leak into other tests.

Runner note: the instance's runner (`engine/scripts/run-suite.sh`) runs the root suite and
the full driver suite with no per-module option; the brief's criterion is stated per-module,
so I used exactly the brief's module command wrapped in `timeout`, plus one full driver-suite
run the same way the script does it (`cd template && PYTHONPATH=src python3 -m unittest
discover -s tests`).

## Refute-your-own-test

- **(a) Genuine red?** There is no production hunk to revert (test-only by design). The red
  comes from the three mutants above: each, applied alone, turns one new test red (M1, M2 →
  scenario A; M3 → scenario B), and M4 also turns A red. Unmutated, both are green. As the
  brief says, C4 will report `PDCA-UNVERIFIABLE` (exit 77) for a test-only patch; that is
  expected and the mutant replay above is the evidence instead.
- **(b) Production path?** Yes. Both tests go through `cli._flow` → `flow.flow_ids` →
  `_drive_and_act` → the real `_adopt_split_children`, `_reschedule`, `_real`,
  `_warn_stranded_split_children`. The split itself is the production `split.accept`. The
  only replaced things are the two fault seams (`waves.partition_schedulable` for A, and
  `pathlib.Path.resolve` for one path in B) — both *below* the code being pinned, and both
  pass through to the real function otherwise. `flow._real` is not replaced (the M3 run
  proves the handler under test is the one being exercised).
- **(c) Fixture includes the fault?** Yes. A: the wrapper records that it actually raised,
  once, on a list that included `issue_8` while 8 was still `PLANNED` — so the fault fired
  while the run still had a wave ahead. B: `reached` must be non-empty, so the `OSError`
  was actually thrown for `issue_601`.

## Formatter / hooks

The target has no formatter config, no `.pre-commit-config.yaml`, and its CI workflows only
run docs checks and render/update suites (`.github/workflows/*.yml`). Nothing to run. New
lines follow the file's existing style (≤ ~92 visible columns, em-dash comments).

## Ruled out

- Injecting at `flow._real` for B — the brief forbids it and it would make M3 invisible.
- A real symlink loop for B — does not raise under Python ≥ 3.13 (brief note b).
- A new test file — the brief names appending to `AdoptSplitChildren`.
- Asserting the exact wave-0 order — not what the rule is about; compared sorted.
