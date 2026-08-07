# Build notes — issue 370 / gate-output-evidence-log

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l0`, tip 710ec54).

## The defect, located on main

- `gates._run_one` captures the command's combined stdout+stderr
  (`template/src/pdca_harness/gates.py:459`, `capture=True`), then
- `_classify` keeps only the last line (`gates.py:502`, `last = output.strip().splitlines()[-1:]`),
- the row truncates that to 120 chars (`gates.py:475`, `path_line=evidence[0][:120]`),
- and nothing writes the rest anywhere — `_finalize` (`gates.py:516-522`) writes only
  the rows into `check-gates.json`/`check-gates.md`. The full basis of a verdict —
  including a gating red that parks the bundle — was one truncated line.

## The change (all cites: pre-patch main line numbers unless marked "new")

1. **`state.py` — the shared name + archive membership.**
   `GATE_LOGS_DIR = "gate-logs"` defined next to `CLOSE_MARKER`/`SESSION_CARRY`
   (new `state.py:53-57`) and appended to `DOWNSTREAM_OF_BRIEF` (was `state.py:60-88`,
   entry at new `state.py:94-97`). It lives in `state`, not `gates`, for the same
   reason the list itself does (`state.py:57-59` on main: `is_resolved` must read it and
   `driver` imports `state`; the other direction is an import cycle). Membership gives
   the criterion (c) archive behaviour through the existing single-sourced list, and
   `is_resolved` (`state.py:165`) correctly counts a `gate-logs/` dir as cycle evidence
   (`.exists()` is directory-safe) — only a bundle-scoped Check run can create it.

2. **`gates.py` — persist at the capture point.**
   - `run_gates` (`gates.py:136-139`) passes `log_dir=d / GATE_LOGS_DIR` into
     `_run_checks`; every other entry point (`run_working_tree` `:169`, `run_integration`
     `:175`, `run_gates_dry` `:206`) passes nothing → criterion (e), see "ruled out" #2.
   - `_run_checks` (`gates.py:277`) threads `log_dir` to both `_run_one` call sites
     (configured gates `:326-328`; host-CI parity rows `:353-355` — they are
     bundle-scoped verdict rows too, so their evidence is subject to the same invariant)
     and clears the previous run's `gate-logs/` first (new `:337-341`) so "one file per
     rule id, overwritten per Check run" also covers a check *removed* from config —
     no stale log masquerading as current evidence. The clear sits **after** worktree
     resolution, so the fail-closed path (`gates.py:307-314`, worktree mismatch — no gate
     runs) leaves the prior evidence intact.
   - `_run_one` (`gates.py:400-476`) now stamps start time + monotonic duration around
     the existing `run_with_heartbeat` call and, when `log_dir` is set, writes
     `gate-logs/<rule_id>.log` via the new `_write_gate_log` (new `gates.py:525-563`):
     header (cmd, cwd, `$PDCA_WORKTREE`, start, duration, exit/outcome) then the
     combined output **verbatim**. On timeout (`rc == progress.TIMEOUT_RC`, the #368
     outcome introduced at `gates.py:463-467`) the capture up to the kill is what
     `run_with_heartbeat` returns (`progress.py:116-135` drain thread → `:195`
     `"".join(chunks)`), so criterion (d) — *where it hung* — is the same write path,
     with the header naming the timeout. The exception path (`gates.py:470-471`) logs
     the exception string as the run's whole output. Write is best-effort
     (`except OSError → None`): evidence persistence must never turn into a gate crash.
   - The row gains `log` (bundle-relative, `gate-logs/<id>.log`) and `duration_secs`
     **additively** — `_row` (`gates.py:525-529`) and `render_md` (`gates.py:588`) are
     untouched, so every existing consumer of `check-gates.json` rows
     (`_check_result` `:93`, `driver._failing_gate_lines` `driver.py:333`, assemble,
     revalidate) sees the same keys as before. The 120-char `path_line` stays as the
     summary, per the brief.
   - Module docstring row-shape sentence updated (`gates.py:26`) so the documented
     schema doesn't lie.

3. **`driver.py` — archive the directory.** `_archive_iteration` moved only files
   (`driver.py:390-394`: `if src.is_file()`), so a directory in the archive list was
   silently skipped. Now `is_file() or is_dir()` with a comment (new
   `driver.py:390-396`, condition at `:394`); `Path.rename` moves the tree whole into
   `iteration-v<N>/`.
   This is the brief's cited peer pattern (the `DOWNSTREAM_OF_BRIEF` handling at
   `driver.py:359-394`) rather than a special case bolted next to it.

## Ruled out (with cost)

1. **Writing logs from `_finalize` (one write point next to `check-gates.json`).**
   `_finalize` sees only rows; the full output is already gone by then. Making it work
   means threading a `full_output` field through `_row` and every producer/consumer of
   rows — the five `_row` call sites (`gates.py:310, 343, 409, 472, 525`) plus
   `_assemble_matrix` stubs — and holding every gate's complete output (potentially MBs
   for a Docker-backed suite) in the result dict that gets JSON-dumped. Chosen shape:
   +1 helper at the capture point, 0 changes to row consumers, output never travels.
2. **Also logging from `run_gates_dry` (revalidate) / repo-scoped runs.** `run_gates_dry`
   documents "never mutates its frozen record" (`gates.py:206-213`); `gate-logs/` *is*
   the frozen evidence behind the frozen verdict, so a later dry re-gate overwriting it
   would destroy exactly the per-round reconstructability the brief's invariant demands
   ("a verdict's full basis is reconstructable from bundle files alone, per round").
   Not a cost call — the invariant decides it. Repo-scoped no-bundle runs are excluded
   by criterion (e) verbatim. Both are pinned by tests.
3. **Append-per-run instead of clear+overwrite.** The brief mandates "overwritten per
   Check run"; round history is the iterate archive's job (criterion (c)), not the log
   file's — appending would interleave rounds inside one file and still leave stale
   logs for de-configured checks.
4. **Not clearing stale logs at all** (pure per-file overwrite, −4 lines): a check
   removed from `pdca.toml` between runs would leave its old log sitting next to the
   fresh ones, indistinguishable from current evidence — a quieter version of the very
   defect (evidence that doesn't match the recorded verdict).

Deliberately untouched: `template/PCDA/quality-cycle/03-cycle-automation.md:327` shows
an illustrative `DOWNSTREAM_OF_BRIEF` snippet — it is the reference-model doc, already
elided (`# …`), and docs are out of the behavioral surface here.

## Test (`template/tests/test_gate_logs.py`, ships in patch.diff; copy in bundle)

Eight cases, mapped to the criterion: (a) header + verbatim multi-line body — the body
asserts `first-line\nmiddle-line\nlast-line\n` while `path_line` holds only
`last-line`, proving the log carries what the summary drops; (b) `log` +
`duration_secs` additive with all seven pre-existing keys still present; (a-cont.)
re-run clears a stale log; (d) a real hanging command (`echo before-the-hang; sleep 30`,
`timeout_secs = 1`) → `unverifiable` row **and** a log containing `before-the-hang`;
(e) `run_working_tree` rows carry no new keys and no `gate-logs/` appears;
frozen-evidence: `run_gates_dry` after a config change leaves the log byte-identical;
(c) `GATE_LOGS_DIR ∈ DOWNSTREAM_OF_BRIEF` + a behavioural `_archive_iteration` run
moving the dir into `iteration-v1/` and leaving the top level clean.

## Red→green, via the project's runner

Runner: the offline driver suite invocation the target documents (CONTRIBUTING /
`template/Makefile` `check`; the same invocation `engine/scripts/run-verify.sh` uses
for `template/tests/*`): `cd template && PYTHONPATH=src python3 -m unittest …`.

- **Green** (fix applied): `tests.test_gate_logs` — Ran 8, OK (1.0s).
- **Red** (production hunks reverted via `git checkout -- template/src`, test kept):
  Ran 8 — **FAILED (failures=2, errors=5)**. The one pass is
  `test_working_tree_run_keeps_todays_behaviour`, which asserts today's behaviour and
  must pass on both sides.
- **Regression**: `make check` from `template/` — Ran **1436** tests, OK (skipped=2).
  Root suite (render + update-compat, instance venv python for copier) — Ran 7, OK.

## Self-refutation (forced)

- **(a) Genuine red?** Yes — actually reverted (diff stashed to `/tmp/370-prod.diff`,
  `git checkout -- template/src`) and re-ran: 7/8 red, exactly the 7 that bind the new
  behaviour. Re-applied, re-ran: 8/8 green.
- **(b) Production path?** Yes — the tests call `gates.run_gates`,
  `gates.run_gates_dry`, `gates.run_working_tree`, and `driver._archive_iteration`
  directly: the very functions the patch edits. No stand-in, no re-implementation; the
  stub `Config` is the same fixture the existing `test_gates_unverifiable.py` uses to
  drive real gate subprocesses.
- **(c) Fixture includes the fault?** Yes — the timeout case runs a genuinely hanging
  command under a real 1s bound (the kill path executes); the stale-log case
  pre-plants the stale artifact and asserts its removal; the archive case runs the real
  archive step over a real directory. Nothing is curated out.

## Commit-readiness

The target repo has no active commit hooks (`.git/hooks` holds only samples, no
`core.hooksPath`) and no configured Python formatter/linter (no ruff/flake8/pre-commit
config); its CI is docs lint + render check + linked-issue. No docs touched; the render
suite (what `render-check.yml` runs) passed above with the working tree copied in.

## External dependencies

None beyond the brief's list (none). No NEEDS-HUMAN items.
