# Build notes — issue 534, iteration 2 / handoff-contract-checked-at-reap-not-turn-end

Target: `eduralph/pdca-harness @ main` (`6ba00ba`, same base as iteration 1). Cites are on
that commit unless marked "post-patch" (the worktree after the patch).

NEEDS-HUMAN external dependency: write permission for `template/.claude/**` in the Do worktree — the Edit tool was refused again this iteration (tried on `template/.claude/settings.json`; the session is non-interactive, so the prompt could not be approved), so the three `.claude/` hunks were never applied at their real paths in Do. The 4 tests that read those files (5 failures: `test_handoff_reap.NoTurnEndIsIntercepted` x3, one with two subtests, plus `test_handoff::test_hook_ships_and_is_not_registered_on_stop`) and the root render slice were green in Do only against copies. C4 and T3 at Check, where the driver applies `patch.diff` itself, are the real-path run. In iteration 1 both passed with byte-identical `.claude/` hunks.

No `[[doctor.checks]]` row is proposed, on purpose. This instance has
`dependency_halt = true`: a row whose cmd exits non-zero would CONFIRM the claim and send
the bundle down the close fast path with N/A gates, which skips C4, the one run that
applies the `.claude/` hunks at their real paths. A shell probe also cannot see a Claude
Code permission prompt. The fix belongs on the harness side (let the builder write
`.claude/` paths for bundles whose Scope names them, or have Plan flag such bundles).

I did not write the `.claude/` files through the shell to get around the refusal. The
hunks are copied unchanged from iteration 1's `patch.diff` (the sign-off asked to keep
the approach as is), and the new patch reproduces them byte for byte (checked below).

## What changed in this iteration

Both items from the sign-off carry-forward, and nothing else.

1. **A blank abandon value no longer hides the reap report.**
   - The bug in iteration 1: `report_at_reap` stripped `abandoned` and, finding it empty,
     called `stop_problems`. `stop_problems` tested the unstripped value (`handoff.py:374`
     on main, unchanged in iteration 1), counted `" "` as an abandonment and returned
     `[]`. So neither the reason nor the problem list was printed.
   - The fix: one function decides "was the session abandoned":
     `_abandon_reason(state)` (post-patch `handoff.py:269-278`) returns
     `str(state.get("abandoned") or "").strip()`. `report_at_reap` uses it for the reason
     (post-patch `:351`) and `stop_problems` uses it for its early return (post-patch
     `:431`, was `if state.get("abandoned"):` at main `:374`). The `stop_problems`
     docstring says a blank value is no abandonment (post-patch `:429`).
   - The expression is the same one main already used to read the reason at reap
     (`handoff.py:307`), so a recorded `--abandon` reason is reported exactly as today
     (criterion b). The only behaviour change inside `stop_problems` is that a
     whitespace-only string no longer counts as abandoned. Every other value is judged
     as before: `""`, `None`, `0`, `False`, `[]` are not abandoned; any non-blank string,
     `True`, or a non-empty list is. The existing `StopVerdict` test
     (`test_handoff.py:341-344`, `"abandoned": "deliberate"`) still passes.
   - How a blank value can get there: `record_abandon` never writes one (main `:261`
     turns a blank into `"(no reason given)"`) and `handoff_guard.py --abandon` refuses
     one (main `handoff_guard.py:93-96`). But the scratch file sits in the project root
     and the leaf has Write, so the session can write `{"abandoned": " "}` itself.
2. **`check_planner`'s docstring** (main `handoff.py:98-101`, post-patch `:103-106`) no
   longer says "at the Stop boundary". It now says the session-end check
   (`stop_problems`, reported when the driver reaps the session) passes a wholly-absent
   brief. `allow_absent` is only passed from `stop_problems` (main `:386-389`), so that is
   the accurate place to name. I left the `# local: keep this module import-light for
   the hook` comment (main `:103`, post-patch `:108`). It refers to the hook script that
   still imports this module for `--check` / `--abandon`, and it describes no Stop hook.
3. **Test:** `ReportedAtReap.test_a_blank_abandon_value_does_not_hide_the_report`
   (post-patch `test_handoff_reap.py:300-321`).
   - For `""`, `" "`, `"\n"`, `" \t\n"` (subtests), the session writes the blank value
     into its own scratch file during a real `handoff.session("signoff", [bundle])` whose
     bundle has no `signoff-decision`.
   - It asserts that the reap prints `issue_7: signoff-decision is missing`, that it
     prints no "deliberately abandoned" line, and that `stop_problems()` given the same
     blank value returns a non-empty list.
   - The module docstring's item (b) gained one clause (post-patch `:20`).

## Carried over unchanged from iteration 1

These are the same hunks, byte for byte. Short list with cites on main:

- `template/.claude/settings.json:60-71`: the `"hooks"` key with the Stop registration
  is removed. `permissions` and `sandbox` are identical (compared with `json.load`).
- `template/.claude/hooks/handoff_guard.py`: `_stop_verdict()` (`:48-73`) and
  `import json` (`:30`) are removed. The fallthrough (`:101`) becomes: no arguments
  returns 0 silently without reading stdin, an unknown argument exits 2. The docstring
  (`:1-26`) and the `--abandon` success message (`:98-99`) are reworded.
- `template/src/pdca_harness/handoff.py`:
  - `session()`'s `finally` (`:306-311`) now calls `report_at_reap(cfg, role, {**file,
    **registered})` inside a nested `try/finally`, so the scratch file is always removed.
  - The driver's registration is kept in memory (`registered`), so a leaf that rewrites
    the scratch file cannot change which bundles get named.
  - `:301` "unenforced" becomes "unchecked".
  - Docstrings `:13-15`, `:258-260`, `:267-274`, section comment `:315`, `:366-373`.
- `template/src/pdca_harness/leaves.py`: prompt text and comments at `:1035`,
  `:1293-1294`, `:1310`, `:3414-3415`, `:3437-3438`, `:3464-3465`, `:3492-3494`,
  `:3628-3629`, `:3693-3694`. I re-checked with an AST range check on main that no hunk
  falls inside `do_plan` (`:904-927`), `do_plan_batch` (`:1055-1133`) or
  `run_plan_advisory_batch` (`:3354-3401`). The stale comments at `:916-917` and
  `:1104-1108` stay for issue 480, as the Ordering note asks.
- `template/.claude/commands/handoff.md.jinja:17-19`, `docs/01-render-and-integrate.md:177-182`.
- `template/tests/test_handoff.py`: docstring `:1-2` and `:10-11`; `:133-141` is inverted
  to `test_hook_ships_and_is_not_registered_on_stop`.
- A search of the patched tree for "Stop hook", "stop boundary" and similar wording finds
  only historical mentions (post-patch `handoff.py:18`, `:422`, the tests, and the
  staged hook's docstring) plus the reserved `leaves.py:917`.

## Evidence

The runs used the instance venv's Python (3.14.4, copier 9.17.0). Targeted runs used the
same per-module command `engine/scripts/run-verify.sh` uses (`cd template &&
PYTHONPATH=src python3 -m unittest tests.<module>`), bounded by `timeout`.

- **Patch integrity:** 8 files, 51,010 bytes. It applies cleanly to `6ba00ba` (checked
  with a throwaway index). Every post-image blob is byte-identical to what I tested: the
  worktree files, and the `.cache/534/stage/` copies for the three `.claude/` files. The
  hook keeps mode `100755`. `git apply --whitespace=error` is clean.
- **C4-shaped red leg** (production hunks reverted, tests kept, `.claude/` at main): 53
  tests ran, 21 failures (subtests counted), no `_FailedTest`, so the module loads on the
  red leg. All four blank-abandon subtests are red: main's reap prints nothing at all.
  The tree was restored and re-checked against the patch post-image.
- **Red for finding 1 specifically:** the new test against iteration 1's `handoff.py`
  (rebuilt in a scratch `src` copy, differing from post-patch only by the two fixes):
  the `" "`, `"\n"`, `" \t\n"` subtests FAIL with `'issue_7: signoff-decision is missing'
  not found in ''`, which is the adversary's finding exactly. `""` passes there, as
  expected (it is the control). With the fix, all four pass.
- **Green at real paths** (worktree = full patch except the three `.claude/` files): 53
  ran, 5 failures from 4 tests (one fails in two subtests). Those are exactly the
  `.claude/`-reading tests named in the NEEDS-HUMAN line, failing because the worktree's
  `settings.json` and hook are still at main. Everything else passes, including the new
  blank-abandon test and all of `ReportedAtReap` / `ReportOnly`.
- **Sanity pass against the copies** (not a substitute for C4): both test modules,
  unmodified, with their `HOOK` / `SETTINGS` / `COMMAND` constants pointed at
  `.cache/534/stage/` (`.cache/534/sanity_run.py`): 53/53 OK.
- **T3 runner** (`engine/scripts/run-suite.sh`, `PDCA_WORKTREE` = this worktree):
  - Driver suite: 1806 tests (iteration 1's 1805 plus the new one), 5 failures (the same
    five), 2 skipped.
  - Root suite: 24 tests, 1 failure, `test_render_then_slice`. That is the same five
    seen through the rendered instance (its slice: 1806 tests, 5 failures, 10 skipped;
    the traceback is the Stop-registration assertion).
  - `test_update_compat` passed, but with `settings.json` at main it did not exercise
    the settings change. Iteration 1's Check T3 did, and passed.
- **T2 runner** (`engine/scripts/run-docs-check.sh`): docs lint clean, site render +
  link audit clean.
- **Commit-readiness:** the target has no formatter, linter or pre-commit config (no
  `pyproject.toml` / ruff / pre-commit at the root; CI is docs lint + render + render
  check + linked-issue). All changed Python compiles, including the staged hook. No new
  imports were added this iteration. New lines are 88 columns or fewer; the files'
  existing maximum is 93. The one commit requirement is the DCO sign-off
  (`git commit -s`, CONTRIBUTING.md), which publish applies.

## Refuting my own test

- **(a) Genuine red?** Yes. With the production hunks reverted, 21 failures across the
  53 tests, including all four blank-abandon subtests. Against iteration 1's code, which
  is the more pointed red for this iteration, the three whitespace-only subtests fail
  with an empty stderr, which is the reported defect itself.
- **(b) Production path?** Yes. The new test drives the real `handoff.session` context
  manager that `leaves.py` wraps around every contract leaf, the real `report_at_reap`
  and the real `stop_problems`. The only thing it does "as the leaf" is write the
  scratch file the session registered, which a real leaf with Write can do. No mocks. The
  iteration-1 tests are unchanged (the `_bootstrap` patch in the in-process hook test is
  the brief's sanctioned approach; the subprocess test has no mocks). Caveat: for the
  `.claude/`-reading tests, Do's green ran against copies. C4 closes that.
- **(c) Fixture includes the fault?** Yes. The bundle has no `signoff-decision`, so the
  contract is really undischarged, and the blank value sits in the real scratch file the
  real reap reads. The red against iteration 1 shows this fixture triggers the defect
  (empty output), not a neighbour of it.

## Alternatives ruled out

- **Strip inline in `stop_problems` only** (`if str(state.get("abandoned") or
  "").strip():`). That is 1 changed line against my 10-line helper plus 2 changed call
  lines. It fixes the symptom but keeps two separately written copies of "is it
  abandoned", and that duplication is what let the two drift apart. The helper removes
  the duplication, and the sign-off asked for "one test in both places".
- **Drop a blank `abandoned` in `report_at_reap` before calling `stop_problems`** (about
  2 lines). This fixes one caller only. `stop_problems` would still count `" "` as an
  abandonment for any other caller.
- **Count a blank value as an abandonment with "(no reason given)"**, the way
  `record_abandon` treats a blank argument (main `:261`). Rejected. The hook refuses a
  blank reason (`handoff_guard.py:93-96`) so that walking away needs a typed reason. If a
  blank value written straight into the scratch file counted, a leaf could hide the
  problem list without typing one. The sign-off also named blank = not abandoned.
- The iteration-1 alternatives (keeping Stop with `stop_hook_active`, a usage error on
  the no-argument call, draining stdin, reporting from each `leaves.py` callsite) still
  stand as recorded in `iteration-v1/build-notes.md`. Nothing here reopens them.

## Housekeeping

- Working files are in the worktree's gitignored `.cache/534/`: `claude-hunks.diff`,
  `stage/` (post-patch `.claude/` copies), `v1src/` (iteration 1's src for the targeted
  red), `sanity_run.py`, `patch.diff`, logs (`red-leg.log`, `suite.log`,
  `docs-check.log`) and throwaway index files. They are left for the harness to reclaim.
- One slip: while building `.cache/534/v1src/` I ran an `rm -rf` on that copy's own
  `__pycache__`. Cleanup is the harness's job. It touched nothing outside my scratch copy.
- I used `git add -N` on the new test so `git diff` would include it, then `git reset`
  it back out. The worktree's index is at HEAD again, and the test file is untracked as
  before. `py_compile` left `__pycache__` dirs, which are gitignored.
- No commit (the worktree's checked-out branch name is the harness's), no push, no PR.
