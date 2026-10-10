# Build notes — issue 621 / merge-confirm-requires-complete-rollup

Target: `eduralph/pdca-harness` `main` @ `b5f5c29`, worktree `pdca-harness.pdca-wt-l0`.
Line numbers below are on the patched tree unless marked "base".

## What changed

**`template/src/pdca_harness/merge.py`**
- `_check_rollup` (`merge.py:114`, base `:111`) now returns `(verdict, detail, names)`.
  `names` is the sorted tuple of every reported check's name, one entry per check, so two
  `build` rows stay two entries. Sorting a tuple gives a multiset compare with `==` and no
  `Counter` import. Unreadable / empty reads return `()`. Its only caller is
  `_wait_for_green`; no test patched it (checked with grep).
- New `_name` (`merge.py:173`) factored out of `_names` so both use one name rule (`"?"` for
  a nameless check).
- New `_read_rollup(pr_url, expected)` (`merge.py:181`): runs `_check_rollup`; if the read
  is green and a declared name is missing, it returns `pending` with a detail like
  `expected check e2e not reported yet (1 check reported)`. A declared check counts as
  present on a green read, and a green read only has `_ROLLUP_OK` buckets (`pass`,
  `skipping`), so a skipped / neutral declared check does not block (criterion 1).
- `_wait_for_green` (`merge.py:196`) gains `expected=()`. Every read goes through
  `_read_rollup`, including the single read of `wait_secs <= 0` (`merge.py:231-233`), which
  covers criterion 1b. The confirm (`merge.py:253-258`) now succeeds only if the confirm read
  is green **and** `names == first`. A green confirm over a different set falls back into
  the `while True` loop as a new first green: the pending inner loop is skipped (verdict is
  green), and the existing budget rule (`left < poll_interval` → pending) decides whether a
  second confirm fits. So the budget rules from base `merge.py:213-219` are unchanged: a
  confirm is a full poll interval later or not at all.
- `_merge_one`: refuses before the ready-mark when `cfg.expected_checks_error` is set
  (`merge.py:423-432`), and passes `expected=cfg.expected_checks` to the wait
  (`merge.py:494-497`). A missing declared check ends as `pending`, so the existing refusal
  branch prints "a check has not finished within Ns — expected check e2e not reported yet…"
  and calls `_undo_ready` (base `merge.py:452-469`).
- Docstrings: module docstring (`merge.py:39-46`) and `_wait_for_green` docstring
  (`merge.py:213-227`) replace the old "compares verdicts only" sentence (base `:192-194`)
  and state the residual for the undeclared case.

**`template/src/pdca_harness/config.py`**
- Fields `expected_checks: tuple[str, ...] = ()` and `expected_checks_error: str = ""`
  (`config.py:387-396`), next to `merge_wait_secs`.
- Parsed in `Config.load` right after `merge_wait_secs` (`config.py:757-763`) via the new
  `_expected_checks` (`config.py:897-906`). A bare string → one-item tuple. A list of
  non-blank strings → stripped and de-duplicated in order. Anything else (int, bool, table,
  list with a non-string, blank name, `""`) → warning on stderr and an error string. The
  tuple stays empty, but `_merge_one` refuses every PR on the error, so it fails closed,
  following `merge_requires` (base `config.py:728-732`).
- Passed to the constructor at `config.py:872-873`.

**`template/pdca.toml.jinja:195-204`** — commented block after `merge_wait_secs` (left
commented out so the rendered default stays empty and the render suite stays unchanged).

**`docs/07-crosscutting.md:731-737`** — a short paragraph in the merge-mode bullet on the
same-set confirm, `expected_checks`, and the residual.

**`template/docs/fork-discipline.md.jinja:63`** — not touched. That line describes the
bounded wait and the update-branch sequence, not the confirm, and the brief scoped it with
"if that line describes the confirm".

## Design choices and what I ruled out

- **Where to apply the declared list.** I put it in a wrapper (`_read_rollup`) rather than
  inside `_check_rollup`, so `_check_rollup` stays a pure classifier of what gh reported, and
  the "pending because e2e is missing" rule applies the same on every read (first, loop,
  confirm, single). Turning a missing declared check into `pending` rather than a new
  verdict means `_merge_one`'s refusal table (base `merge.py:453-460`) needs no new key, and
  the existing wait logic keeps polling until it registers.
- **Refusing a malformed setting before the ready-mark vs. after.** Before. Nothing about
  the PR is read yet, so readying it only to undo it adds two `gh` calls and a window where
  the PR shows ready. The brief's "PR returned to draft as on every refusal" is about
  criterion 1 (the missing-check case), and that path does go through `_undo_ready`. The
  refusal applies under `merge_requires = "required"` too: the brief says "every PR is
  refused", and a typo'd setting is better surfaced than silently ignored.
- **A changed-set confirm.** Options: (a) restart the whole wait, (b) treat the new green as
  the new first green and confirm it one interval later. I chose (b): it is what criterion 2
  asks ("a later read with the same names as that one confirms it"), and it reuses the
  existing budget check unchanged (one line: `first = names` plus the extra `and names ==
  first`).
- **Comparing names on the non-green intermediate reads.** Not needed: a pending read between
  greens just resumes the wait, and the next green is confirmed against its own successor.

## Tests — `template/tests/test_merge.py`, class `MergeConfirmRequiresCompleteRollup` (`:1162`)

Ten tests, each mapped to a criterion:
- (1) `test_declared_check_that_never_registers_never_reads_green` (`:1225`) — `_wait_for_green`
  over `green(dco)` forever with `expected=("dco","e2e")` → `pending`, detail names `e2e`.
- (1) `test_declared_check_missing_refuses_the_merge_and_undoes_ready` (`:1232`) — through
  `merge_wave`: rc 1, no `gh pr merge`, `gh pr ready --undo` called.
- (1) `test_declared_check_that_registers_and_passes_merges_after_two_same_reads` (`:1240`).
- (1) `test_declared_check_that_is_skipped_does_not_block` (`:1249`) — `e2e` = `skipping`.
- (1b) `test_declared_check_applies_to_the_single_read_of_wait_zero` (`:1257`).
- (2) `test_confirm_read_over_a_different_set_is_not_a_confirmation` (`:1270`) — with 29 s of
  budget, `green(dco)` → `green(dco,e2e)` is `pending`; with 300 s it takes three reads.
- (2) `test_names_are_compared_as_a_multiset` (`:1284`) — `build` vs `build, build`.
- (3) `test_same_set_with_nothing_declared_still_confirms` (`:1294`) — unchanged behaviour.
- (4) `test_expected_checks_comes_from_the_driver_table` (`:1303`) — real `Config.load`:
  default empty, list, bare string, five malformed shapes warn on stderr and set the error.
- (4) `test_malformed_expected_checks_fails_closed_in_merge_mode` (`:1330`) — a fully green
  rollup is still refused, naming `expected_checks`.

## Runs (project runners only)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
  green leg `Ran 59 tests … OK`; red leg `Ran 59 tests … FAILED (failures=2, errors=7)`;
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The worktree diff matched
  `patch.diff` byte-for-byte after the runner's restore (`cmp`).
- T3: `./engine/scripts/run-suite.sh` → root suite (render + update-compat) `Ran 24 tests …
  OK`; driver suite `Ran 2379 tests … OK (skipped=2)`.
- T2: `./engine/scripts/run-docs-check.sh` → lint clean, render + link audit clean.
- Formatter / hooks: the target has no pre-commit config, no `.git/hooks/pre-commit`, and no
  ruff/black config. I kept every added line within the file's existing 100-column width
  (checked: 0 added lines over 100 chars). `pyflakes` is not installed, so no lint beyond
  the suites importing every module.

## Refuting my own test

- **(a) Genuine red? Yes.** The C4 runner reverted the production hunks (merge.py,
  config.py, pdca.toml.jinja) and kept the test: 2 failures + 7 errors out of 59. The two
  FAILs are the name-compare tests (criterion 2), and they fail on behaviour:
  `('green', 2) != ('pending', 2)`, so base `main` confirms `green(dco)` → `green(dco,e2e)`
  and `green(build)` → `green(build,build)`. The 7 errors are the tests that use the new
  setting / parameter (`TypeError: unexpected keyword argument 'expected'`,
  `AttributeError: … 'expected_checks'`). Those are honest reds in the sense that base has no
  way to declare a check at all, but they are missing-API reds, not behaviour reds; the
  brief's repro (base returns `("green", "1 check")` for `green(dco)` → `green(dco)`) is the
  behaviour they stand for, and `test_same_set_with_nothing_declared_still_confirms` pins
  that base behaviour as still true when nothing is declared. The module imported fine on
  the red leg (no `_FailedTest`), so the runner counted real test runs.
- **(b) Production path? Yes.** Tests call the real `merge._wait_for_green` and
  `merge.merge_wave` → `_merge_one` → `_read_rollup` → `_check_rollup`, and the real
  `Config.load` parsing a real `pdca.toml`. Only `subprocess.run` (the `gh`/`git` boundary),
  `merge._sleep`, `state.state` and `merged.is_merged` are patched, the same seams the
  existing #582 tests use (`test_merge.py:473-506`).
- **(c) Fixture includes the fault? Yes.** The scripted rollups are exactly the defect
  shapes: `e2e` absent from every read while declared; the check set changing between the
  green and its confirm; a duplicated name. The malformed-setting test feeds an otherwise
  fully green rollup, so only the bad setting can cause the refusal.

## Residual (for the PR description)

With nothing declared (the default), `green(dco)` → `green(dco)` still merges when a slow
`e2e` registers more than one poll interval later. The issue's "Done when" refusal holds
only for an operator who sets `[driver].expected_checks`. The PR must say "narrows #621",
not "fixes #621". Deriving the expected set automatically is out of scope per the brief.
