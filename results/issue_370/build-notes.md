# Build notes — issue 370 / gate-output-evidence-log (iteration 2)

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l1`, tip 9612792).

## Iteration 1 carry-forward — what changed and why

The human upheld the advisory C5 FAIL: in v1, `_write_gate_log` returned `None` on
`OSError` and the row was emitted with **no** `log`/`duration_secs` and **no other
signal** — the feature's own promise ("full basis reconstructable from bundle files
alone") could silently not happen, echoing the original #370 defect. Directed remedy:
keep the invariant that evidence persistence never breaks the gate run or alters a
verdict, but surface a write failure visibly — an additive row key (`log_error` with the
reason) plus a stderr line — and cover the reproduced collision (a file squatting on the
`gate-logs` path) with a test. Everything else stood up (C4 red→green, C1/C2/C3/T1
advisory PASS), so this is the v1 patch rebuilt with that one behaviour changed. The
rejected approach (silent `None` → keys simply absent) is NOT re-submitted:

- `_write_gate_log` now returns `(rel_path, None)` on success or `(None, reason)` on a
  write failure — the failure is **returned, not swallowed**
  (`gates.py:538-574` new; the `except OSError as exc` → reason at `:572-573`).
- `_run_one` records it: on success `row["log"]` (`gates.py:524-525` new); on failure
  `row["log_error"] = reason` **and** a stderr line naming the gate and the reason
  (`gates.py:526-534` new). `duration_secs` is set in both branches (`:523`) — the
  measurement happened regardless of whether the log write did, and criterion (b) ties
  it to the row, not to the file.
- The verdict is untouched in both branches: the row's `result` and `_finalize`'s
  `overall` are computed before/independently of the persistence step (`gates.py:509-514`
  new) — pinned by the new test.
- The pre-run clear's comment now states the collision behaviour explicitly
  (`gates.py:339-345` new): a non-directory squatting on the path survives the
  `rmtree(ignore_errors=True)` and is surfaced per row as `log_error`. I deliberately do
  **not** auto-delete a squatting *file*: it is not a file the harness wrote (the harness
  only ever creates `gate-logs` as a directory), and silently destroying unknown user
  data to make room for a log would be a worse failure mode than a loudly-reported
  unwritten log. The human sees `log_error` in `check-gates.json` + stderr and removes
  the squatter. (Cost of the alternative: ~3 lines — `if log_dir.is_file():
  log_dir.unlink()` — so this is not a cost call; it is a data-safety call.)
- New test `test_write_failure_surfaces_log_error_and_stderr`
  (`template/tests/test_gate_logs.py:126-149`): plants a **file** at
  `d/gate-logs` (the reproduced collision), runs the real `run_gates`, asserts
  result/overall stay `pass`, `path_line` unchanged, no `log` key, `log_error` contains
  the target path + reason, `duration_secs` present, the stderr line names the gate and
  "not written", and the recorded `check-gates.json` carries `log_error` too
  (state-is-files: the signal survives the live run).
- Docstring row-shape sentence documents `log_error` (`gates.py:26-31` new).

## The defect, located on main (unchanged from v1)

- `gates._run_one` captures the command's combined stdout+stderr
  (`template/src/pdca_harness/gates.py:459` pre-patch, `capture=True`), then
- `_classify` keeps only the last line (`gates.py:502` pre-patch), the row truncates it
  to 120 chars (`gates.py:475` pre-patch, `path_line=evidence[0][:120]`),
- and nothing writes the rest anywhere — `_finalize` (`gates.py:516-522` pre-patch)
  writes only the rows into `check-gates.json`/`check-gates.md`.

## The change (cites: NEW line numbers on the patched worktree unless marked pre-patch)

1. **`state.py` — the shared name + archive membership.**
   `GATE_LOGS_DIR = "gate-logs"` next to `CLOSE_MARKER`/`SESSION_CARRY`
   (`state.py:53-57` new) and appended to `DOWNSTREAM_OF_BRIEF` (`state.py:93-97` new).
   It lives in `state`, not `gates`, for the same reason the list does (`state.py:57-59`
   pre-patch: `is_resolved` must read it and `driver` imports `state` — the other
   direction is an import cycle). Membership gives criterion (c) through the existing
   single-sourced list.

2. **`gates.py` — persist at the capture point.**
   - `run_gates` (`gates.py:145-157` new) passes `log_dir=d / GATE_LOGS_DIR` into
     `_run_checks`; every other entry point (`run_working_tree`, `run_integration`,
     `run_gates_dry`) passes nothing → criterion (e); `run_gates_dry`'s docstring
     records why (`gates.py:229-233` new): `gate-logs/` is the frozen evidence behind
     the frozen verdict, a dry re-gate must not overwrite it.
   - `_run_checks` (`gates.py:298-300` new) threads `log_dir` to both `_run_one` call
     sites (configured gates `:355-358`; host-CI parity rows `:383-386` — they are
     bundle-scoped verdict rows too) and clears the previous run's `gate-logs/` first
     (`:339-345` new) so "overwritten per Check run" also covers a check *removed* from
     config. The clear sits after worktree resolution, so the fail-closed path (worktree
     mismatch — no gate runs) leaves prior evidence intact.
   - `_run_one` (`gates.py:431-434, 486-489, 506-535` new) stamps start time + monotonic
     duration around the existing `run_with_heartbeat` call and, when `log_dir` is set,
     writes `gate-logs/<rule_id>.log` via `_write_gate_log` (`gates.py:538-574` new):
     header (cmd, cwd, `$PDCA_WORKTREE`, start, duration, exit/outcome) then the
     combined output **verbatim**. On timeout (`rc == progress.TIMEOUT_RC`, the #368
     outcome) the capture up to the kill is what `run_with_heartbeat` returns, so
     criterion (d) is the same write path with the header naming the timeout
     (`gates.py:556-559` new). The exception path logs the exception string as the run's
     whole output (`gates.py:508` new).
   - Row keys `log` + `duration_secs` (+ `log_error` on failure) are **additive** —
     `_row` and `render_md` untouched, so every existing consumer of `check-gates.json`
     rows (`_check_result`, `driver._failing_gate_lines`, assemble, revalidate) sees the
     same keys as before. The 120-char `path_line` stays as the summary, per the brief.

3. **`driver.py` — archive the directory.** `_archive_iteration` moved only files
   (`driver.py:390-394` pre-patch: `if src.is_file()`); now `is_file() or is_dir()`
   (`driver.py:390-396` new) — `Path.rename` moves the tree whole into
   `iteration-v<N>/`. This is the brief's cited peer pattern (the `DOWNSTREAM_OF_BRIEF`
   handling, `driver.py:359+`), not a special case bolted next to it.

## Ruled out (with cost) — carried from v1, still valid

1. **Writing logs from `_finalize`.** `_finalize` sees only rows; the output is gone by
   then. Making it work means threading a `full_output` field through the five `_row`
   call sites plus `_assemble_matrix` stubs and holding every gate's complete output
   (potentially MBs for a Docker-backed suite) in the JSON-dumped result dict. Chosen
   shape: +1 helper at the capture point, 0 changes to row consumers.
2. **Also logging from `run_gates_dry` / repo-scoped runs.** Excluded by the invariant
   ("per round" reconstructability — a dry re-gate overwriting frozen evidence destroys
   it) and by criterion (e) verbatim. Both pinned by tests.
3. **Append-per-run instead of clear+overwrite.** The brief mandates "overwritten per
   Check run"; round history is the iterate archive's job (criterion (c)).
4. **Not clearing stale logs** (−6 lines): a check removed from `pdca.toml` would leave
   its old log indistinguishable from current evidence — a quieter version of the defect.
5. **(new) Auto-deleting a file squatting on `gate-logs`** (~3 lines cheaper than
   nothing, see carry-forward section): rejected on data-safety, not cost — the harness
   never creates that path as a file, so the squatter is someone else's data; the loud
   `log_error` + stderr is the honest behaviour the human asked for.

## Test (`template/tests/test_gate_logs.py`, in patch.diff; copy in bundle)

Nine cases mapped to the criterion: (a) header + verbatim multi-line body (`path_line`
holds only `last-line`, the log holds all three lines); (b) `log` + `duration_secs`
additive, no `log_error` on success, all seven pre-existing keys present; (a-cont.)
re-run clears a stale log; **(iteration 2)** write failure → `log_error` + stderr,
verdict unchanged, recorded in `check-gates.json`; (d) a real hanging command
(`sleep 30`, `timeout_secs=1`) → `unverifiable` row and a log containing
`before-the-hang`; (e) `run_working_tree` rows carry none of the three new keys and no
`gate-logs/` appears; frozen-evidence: `run_gates_dry` leaves the log byte-identical;
(c) `GATE_LOGS_DIR ∈ DOWNSTREAM_OF_BRIEF` + a behavioural `_archive_iteration` run.

## Red→green, via the project's runner

- **Green** (fix applied): `template/`: `PYTHONPATH=src python3 -m unittest
  tests.test_gate_logs` — Ran 9, OK (1.0s).
- **Red** (production hunks reverted via `git checkout -- template/src`, test kept):
  Ran 9 — **FAILED (failures=2, errors=6)**. The one pass is
  `test_working_tree_run_keeps_todays_behaviour` (asserts today's behaviour, must pass
  on both sides). The new collision test errors red (KeyError `log_error`).
- **Regression**: `make check` from `template/` (the target's documented runner,
  `template/Makefile:73-74`) — Ran **1438** tests, OK (skipped=2).
- **The gate that was red last round** (T3 runtime): the instance's own gate script
  `engine/scripts/run-suite.sh` run over this worktree — root suite (render +
  update-compat, instance venv python for copier) Ran 7 OK; offline driver suite
  Ran 1438 OK (skipped=2).

## Self-refutation (forced)

- **(a) Genuine red?** Yes — actually reverted (prod diff stashed to
  `/tmp/370v2-prod.diff`, `git checkout -- template/src`) and re-ran: 8/9 red, exactly
  the 8 that bind the new behaviour, including the new collision case. Re-applied,
  re-ran: 9/9 green.
- **(b) Production path?** Yes — the tests call `gates.run_gates`, `gates.run_gates_dry`,
  `gates.run_working_tree`, and `driver._archive_iteration` directly: the very functions
  the patch edits. No stand-in; the stub `Config` is the same fixture the existing
  `test_gates_unverifiable.py` uses to drive real gate subprocesses.
- **(c) Fixture includes the fault?** Yes — the timeout case runs a genuinely hanging
  command under a real 1s bound (the kill path executes); the collision case plants the
  actual squatting file the human's rationale reproduced and the write really fails
  (`FileExistsError` from `mkdir`); the stale-log case pre-plants the stale artifact;
  the archive case runs the real archive step over a real directory.

## Commit-readiness

The target repo has no active commit hooks (`.git/hooks` holds only samples, no
`core.hooksPath`) and no configured Python formatter/linter (no ruff/black/flake8/
pre-commit config anywhere in the tree or `template/pyproject.toml`). No docs touched;
the render suite (what `render-check.yml` runs) passed above with the working tree
copied in.

## External dependencies

None beyond the brief's list (none). No NEEDS-HUMAN items.
