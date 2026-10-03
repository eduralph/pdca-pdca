# Build notes — issue 582 / merge-wait-confirms-green (iteration 2)

Target: eduralph/pdca-harness @ main. Worktree base `24c7f83` = `origin/main`. Line numbers
are in the patched worktree unless marked "main" or "iteration 1".

## What the carry-forward asked, and what this attempt does

Iteration 1 was rejected for one gap. The confirm sleep was `min(poll_interval, wait_secs -
waited)` (iteration-1 `merge.py:182`), so with less than 15 s of budget left the confirm read
came 1–14 s after the first green. Budget 1 with green, green merged after 1 s. Budget 20 with
pending, green, green merged after a 5 s confirm. The carry-forward asked for three things:
take the confirm read only when a FULL poll interval of budget is left; otherwise return the
green as `pending` with the "unconfirmed" detail, through the same path as the no-budget case;
and add tests through `merge.merge_wave` for both boundaries. Everything else was to be kept.

Changed from iteration 1 (all in `template/src/pdca_harness/merge.py`, `_wait_for_green`):

- `:185-188`: `left = wait_secs - waited`; `if left < poll_interval:` return `"pending"` with
  the unconfirmed detail. Iteration 1 had `if waited >= wait_secs:`, so it refused only at
  exactly 0 s left.
- `:189-190`: the confirm sleeps `poll_interval` and charges `poll_interval`. It can no longer
  be shortened. Iteration 1 had `step = min(poll_interval, wait_secs - waited)`.
- `:182-184`: a three-line comment saying why the confirm is a full interval or nothing.
- Detail text (`:187-188`): `green first seen with {left}s of wait budget left, too little to
  confirm it {poll_interval}s later ({detail})`. Iteration 1's `green first seen with no wait
  budget left to confirm it (2 checks)` would now be false on the new path: at budget 20 the
  refusal happens with 5 s left. With 0 s left the new text reads `... with 0s of wait budget
  left, too little to confirm it 15s later (2 checks)`. It still names the green as
  unconfirmed and contains `confirm` (brief (iii)). The brief's wording was an "e.g.". Through
  `_merge_one`'s existing message (`merge.py:268-269`) the refusal reads: `a check has not
  finished within 20s — green first seen with 5s of wait budget left, too little to confirm it
  15s later (2 checks)`.
- Docstrings: `_wait_for_green` (`:153-163`) and the module docstring (`:39-43`) now say "one
  full poll interval later" and "never shortened". They also say that a `wait_secs` below
  `poll_interval` never returns green.
- Operator comments now say "a full poll interval (15 s)" and "a value from 1 to 14 refuses
  every PR": `template/src/pdca_harness/config.py:380-385` and
  `template/pdca.toml.jinja:151-155`.

Kept unchanged from iteration 1: the outer loop shape (`merge.py:174-193`), the `wait_secs <= 0`
early return (`:171-172`, criterion iv), failing/unreadable returning at once (`:180-181`),
pending/empty confirm reads re-entering the bounded loop (`:175-179`), the class-wide `_sleep`
patch in `setUp` (`template/tests/test_merge.py:80-86`), the two on-purpose test updates
(`:318-320` 4 reads, `:342-344` `[ready, checks, checks, merge]`), and the six iteration-1
tests (`:478-556`). The only edit to those six is one exact-text assertion (`:530-531`), which
follows the new detail wording.

## Full change list vs main

- `template/src/pdca_harness/merge.py:148-193`: `_wait_for_green` (main `:143-160`). It is
  still the only callee of the gate in `_merge_one` (`:264`, main `:231`). `_merge_one`,
  `_check_rollup`, `_undo_ready`, and the `merge_requires = "required"` skip are untouched
  (criterion v).
- `template/src/pdca_harness/merge.py:39-43`: module docstring (main `:33-42`).
- `template/src/pdca_harness/config.py:380-385`: `merge_wait_secs` comment (main `:375-381`).
- `template/pdca.toml.jinja:151-155`: 5 added comment lines, all above `merge_wait_secs = 300`
  (`:161`). The hunk's trailing context ends near main `:153`, so #593's edit near main `:176`
  stays a separate hunk.
- `template/tests/test_merge.py`: setUp patch, two updated tests, a `_drive_reads` helper
  (`:439-472`, now also records an ordered read/sleep/merge timeline when given one), and nine
  #582 tests (`:478-628`).

## Behaviour, traced

| merge_wait_secs | rollup reads | what happens |
|---|---|---|
| 300 (default) | green(dco), pending(e2e), green, green | read at t=0, 15, 30, 45; merges after read 4; sleeps [15, 15, 15] |
| 300 | green(dco), failing(e2e) | 2 reads, refused FAILING naming `e2e (fail)`, ready undone |
| 1 | green, green | 1 s left < 15: refused unconfirmed, 1 read, no sleep |
| 20 | pending, green, green | green at t=15, 5 s left: refused unconfirmed, 2 reads, sleeps [15] |
| 15 | pending, green | green at t=15, 0 s left: refused (the brief's stated small-budget change) |
| 15 | green, green | 15 s left at t=0: confirmed at t=15, merges |
| 30 | pending, green, green | green at t=15, 15 s left: confirmed at t=30, merges |
| 0 | green | one read, no sleep, merges as-is (criterion iv) |

One consequence: with `merge_requires = "all"`, any `merge_wait_secs` from 1 to 14 now refuses
every PR, because no green can ever get its full-interval confirm. The carry-forward asked for
exactly that (budget 1, green, green → refused). The docstring and both operator comments say
so. A `Config.load` warning for that range would be a sensible follow-up. I did not add one:
the brief limits the `config.py` change to the comment.

## Bound, termination, invariant

- Bound (criterion iii): the pending/empty loop sleeps `min(poll_interval, wait_secs - waited)`
  only while `waited < wait_secs`. The confirm sleeps `poll_interval` only when
  `wait_secs - waited >= poll_interval`. Each sleep is added to `waited`, so `waited` never
  goes past `wait_secs` and the sum of sleeps is at most `merge_wait_secs`.
- Termination: every pass of the outer loop either returns or sleeps a positive amount
  (`poll_interval` is 15, the only value any caller passes). `waited` grows toward the bound,
  so the loop ends. A `poll_interval` of 0 would spin, but it already spins on main for a
  pending rollup, and nothing passes 0.
- Invariant: for `wait_secs > 0`, the only `return "green"` (`:192-193`) comes right after
  `_sleep(poll_interval)` (`:189`), and the read before that sleep was green (`:180-181`). So a
  returned green always means two green reads exactly one poll interval apart. The exception
  is `wait_secs <= 0`, which the brief keeps on purpose (criterion iv).
- Known residual, per the brief: only the verdict is compared, not the check names. A slow
  job that has not registered within 15 s still gets through (`green(dco)` → `green(dco)`
  merges), and so does `green(dco)` → `green(dco, e2e)`. Check should not count #582 as fully
  closed.

## Tests

The tests named after the carry-forward:

- `test_budget_under_one_poll_interval_never_confirms_a_green` (`:558`): budget 1, green,
  green. Asserts rc 1, no merge, `not finished within 1s`, `confirm` in stderr, ready undone,
  1 read, no sleep.
- `test_green_with_under_a_poll_interval_of_budget_left_is_not_believed` (`:573`): budget 20,
  pending, green, green. Asserts rc 1, no merge, `not finished within 20s`, the exact 5 s
  detail text, ready undone, 2 reads, sleeps `[15]`.

`test_a_merge_always_follows_two_greens_one_poll_interval_apart` (`:590`) is a sweep that
states the invariant directly. It covers budgets 1, 14, 15, 16, 20, 29, 30, 31, 44, 45, 46,
59, 60, 61 and 300 (both sides of every 15 s boundary up to 60), against six rollup
sequences: green; pending→green; empty→green; three pendings then green; green→empty→green
(a confirm read that is EMPTY, covering the `empty` half of criterion ii); and a green/pending
flicker that never holds. That is 90 sub-cases. Every case checks three things. First, the
total slept is at most the budget. Second, the run merges exactly when the budget is at least
the sequence's `merges_from` (15, 30, 30, 60, 45, never). Third, for every merge, the last two
reads before `gh pr merge` were both green with exactly 15 s slept between them. Otherwise it
checks rc 1 and the ready-undo. The timeline comes from the patched `subprocess.run` and
`_sleep`, so the check does not assume how the code orders its sleeps and reads.

## Red → green (project runners, under `timeout`)

- **New tests against iteration 1's production code.** The worktree held iteration 1's
  production hunks plus these tests, and I ran `engine/scripts/run-verify.sh` (the C4 script)
  with an interim `patch.diff`. Its green leg failed with `FAILED (failures=15)`: both
  carry-forward boundary tests; 12 sweep sub-cases (budget 1/14 green; 16/20/29 pending-green
  and empty-green; 31/44 green-empty-green; 46/59 pending3-green); and the 15 s detail-text
  test. That last one fails on wording only, since iteration 1 refused that case too. Log:
  `results/issue_582/.c4-vs-iteration-v1.log`.
- **C4 script on the final patch:** green leg `Ran 33 tests … OK`; red leg (production hunks
  reverted to main) `FAILED (failures=92)`; result `PDCA-EVIDENCE: C4 PASS — red without the
  fix, green with it`. The 92 are 83 sweep sub-cases plus 9 tests, including the brief's repro
  `test_partial_green_then_failing_does_not_merge` (`AssertionError: 0 != 1`: main merged
  after one read). Log: `results/issue_582/.c4-final.log`.
- **T3 suite on the final patch** (`engine/scripts/run-suite.sh`, under `timeout 1500`):
  `PDCA-EVIDENCE: root suite OK, driver suite OK`. Root: 24 tests in 42.1 s. Driver: 2224
  tests in 47.4 s, `OK (skipped=2)`. Wall time 90 s. Log:
  `results/issue_582/.suite-green.log`. An earlier run, the same patch minus the
  green-empty-green sweep case, was also all OK, with the driver suite at 46.4 s. Iteration 1
  measured the driver suite at 46.1 s on main and 47.2 s with its patch, so the suite is no
  slower: nothing in it sleeps for real.

## Refutation

- **(a) Genuine red?** Yes. The C4 red leg is "fix reverted": tests in place, `merge.py`,
  `config.py` and `pdca.toml.jinja` at main. It gave 92 failures across 9 tests and 83 sweep
  sub-cases, including the brief's repro, where main returns 0 and calls `gh pr merge` after a
  single read. Against iteration 1's code (the rejected approach), the new boundary tests also
  go red (15 failures above). So the tests bind the carry-forward defect, not just the original
  one.
- **(b) Production path?** Yes. Every new test calls the public `merge.merge_wave`, which runs
  the real `_merge_one` → `_wait_for_green` → `_check_rollup` (real JSON parsing and bucket
  classification) → `_undo_ready`. Only the same boundaries the existing tests patch are
  patched: `subprocess.run`, `merge._sleep`, `state.state`, and `merged.is_merged`.
- **(c) Fixture includes the fault?** Yes. The original fault is a partial green: fixtures feed
  `green(dco)` followed by the slow job's real outcome (`e2e fail`, `e2e pending`). The
  carry-forward fault is a green seen with less than one poll interval of budget left:
  fixtures use budgets 1 and 20, and the sweep covers 14, 16, 29, 31, 44, 46 and 59, where
  iteration 1 merged on a shortened confirm.

## Alternatives ruled out

- **Sleep a full 15 s for the confirm even past the budget.** This removes the 2-line guard
  (`:186-188`), but it overruns `merge_wait_secs` by up to 14 s and breaks criterion (iii),
  "sum of the `_sleep` arguments ≤ the bound". The carry-forward also chose refusing.
- **Reserve one interval for the confirm** by ending the pending loop at `wait_secs -
  poll_interval`. Diff: change the condition and step on `:175-176`. But a still-pending
  rollup would then be refused 15 s before `merge_wait_secs`, so "not finished within 300s"
  would be untrue (it gave up at 285 s). That changes the pending/empty wait, which criterion
  (v) keeps as is. It also does nothing for budget 1.
- **Two detail texts** (the brief's exact "no wait budget left" at 0 s, a second text for
  1–14 s): about 2 more lines, a conditional around the return. One format that prints the
  real seconds left is true in both cases and tells the operator by how much to raise the
  bound.
- **Comparing check names or counts between reads, or a configured expected-check list:**
  out of scope per the brief. The residual above stays.

## Commit-readiness

The target configures no formatter, linter or commit hook. There is no
`.pre-commit-config.yaml`; no ruff/black/flake8 config in `template/pyproject.toml.jinja`,
`template/Makefile` or `.github/workflows/` (`.gitignore:4` lists `.ruff_cache/` only); and
`/home/eddie/pdca/pdca-harness/.git/hooks` holds only `*.sample`. Neither ruff nor pyflakes is
installed here. `git diff --check` is clean, and no added line is longer than 100 columns.

## Housekeeping

- Logs in the bundle dir: `.c4-vs-iteration-v1.log`, `.c4-final.log`, `.suite-green.log`, and
  `.patch-final.diff` (a byte-identical copy of `patch.diff`, kept to restore the worktree
  after the iteration-1 comparison). `patch.diff` was briefly overwritten with the interim
  iteration-1-production patch for that comparison, then restored. `cmp` confirmed it matches
  the worktree diff.
- My mistake: one command wrote a throwaway `git diff` to `/tmp/.unused`, which is outside the
  given roots. It holds only a copy of this patch. I left it for the harness, per the
  no-cleanup rule.
