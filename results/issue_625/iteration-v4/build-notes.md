# Build notes — issue 625 / stack-mode-live-github-check-tool (iteration 4)

Target: eduralph/pdca-harness @ main, worktree at a6af7f3. Same three files as round 3:

- `tools/live/stack_mode_live.py` (new, stdlib only, repo root, outside copier's
  `_subdirectory: template`, `copier.yml:13`, so it never reaches rendered instances).
- `tests/test_stack_mode_live_tool.py` (new, root suite, 21 cases).
- `CONTRIBUTING.md:39-104` ("Checking stack mode on real GitHub").

Line numbers below are in the patched tree (base + `patch.diff`; I checked with `cmp` that
the worktree and a clean clone of a6af7f3 with `patch.diff` applied are byte-identical). I
started from round 3's `patch.diff` and changed what the round-3 carry-forward asks for.
The round-1 and round-2 fixes are kept as they were.

## Finding 1 — an undrivable run 2 must be INCOMPLETE, with `run` exiting non-zero

### What was wrong (reproduced on round 3's tool, kept as a scratch copy)

Round 3 recorded run 2's outcome and never required anything of it ("Run 2's outcome is
what E3 judges, so it is recorded, never required"). A run 2 that raised therefore went on
through runs 3 and 4, set `finished: true`, `run` exited 0, and `judge` reported an ordinary
FAIL on E3. That FAIL takes the "file a bug, accept" route, although the brief says "A `run`
that cannot drive the flow blocks accept".

Evidence, on round 3's tool:

- Its own `judge`, fed round 3's own `_good()` fixture with run 2 raised
  (`RuntimeError: boom`): `rc 1 result FAIL {'E0': 'FAIL', ..., 'E3': 'FAIL', ...}`, not
  INCOMPLETE.
- A scratch probe that drives round 3's real `Live.scenario()` and `cmd_run()` with the
  GitHub-facing methods of `Live` stubbed and run 2 raising: `run rc=0 finished=True
  errors=[]`, and the steps went on to `drive run3, merge P, merge B, drive run4, merge S`.

### The invariant, and the fix

The invariant: a FAIL is a stack-mode finding, so `judge` may report one only on a complete
observation. Anything the run did not observe makes the report INCOMPLETE, and `run` exits
1 on exactly the same rule.

- `_incomplete` (`tools/live/stack_mode_live.py:895-907`) is that rule: an error `run`
  recorded, a scenario it did not finish, or any check's `not observed` item. `_verdict`
  (`:910-914`) uses it, `report.json` lists its reasons (`:953`), `report.md` prints them
  (`:922-925`).
- `cmd_run` (`:578-608`) now takes its exit code from `_incomplete(obs, judge(obs))`
  (`:601`), so `run` and the report can never disagree. It prints each reason.
- Run 2 in the scenario: after recording run 2 and D's base, `_require_driven("run2")`
  (`:560`, defined `:413-429`) stops the scenario with `Incomplete` when run 2 raised, or
  when D finished but has no PR (its publish did not complete, so `E0` has nothing to
  read). A hold, a stop or an unfinished D is the flow's own answer: recorded, and the
  scenario goes on, as before.
- `judge`, E3 (`:837-867`): a raise is `not observed` ("run2 raised …: `flow_ids` did not
  return, so the flow was not driven", `:854-855`), so even an observations file that says
  `finished: true` reads INCOMPLETE. A hold, a non-zero rc or an unfinished D stays a
  finding (FAIL). E3 now also requires D COMPLETE and a recorded base (`:858`), and a D
  base git could not place is `not observed` (`:851-852`).
- `judge`, E0 (`:771-780`): with the new rule, a D that run 2 held would have made E0
  `not observed` (no PR) and turned a real E3 finding into INCOMPLETE, blocking the accept
  the brief allows. `_needs_pr` (`:721-727`) excuses D's PR only when run 2 returned and D
  is not COMPLETE; the excused id is shown as `not published` in E0's observed value.
- The other `not observed` cases the new rule now sends to INCOMPLETE rather than FAIL: a
  commit git could not place (`_placed`, `:712-718`, used by E2 `:828` and E4 `:874-875`),
  an E5 value not read (`:886-888`), a branch not confirmed deleted, a PR never recorded.

### Alternatives I did not take

- **Only stop the scenario on a run-2 raise** (keep round 3's verdict rule, which looks
  only at `errors` and `finished`). About 6 lines in `scenario()`. It fixes the live run but
  not the judge: a saved file with `finished: true` and run 2 raised (the shape the
  reviewer probed) still reads FAIL, and the same class stays open for every other
  `not observed` value (a missing PR, an unplaced commit, an unsettled file list). The
  general rule costs `_incomplete` (13 lines) + 2 lines in `_verdict` + 8 lines in
  `cmd_run`, and closes the class. I did both: the stop (so the scenario does not go on
  merging PRs after a crash) and the rule.
- **Treat every unfinished run 2 as INCOMPLETE.** Simpler in E3 and E0 (no `_needs_pr`,
  −7 lines), but a hold or stop of D is exactly what E3 exists to catch (brief, E3: "no
  stop"); making it INCOMPLETE would block accept on the finding #625 is meant to file.

## Finding 2 — PR file lists read once after a fixed sleep

### The fix

`Live._files` (`:340-358`) now polls. It waits `--settle` seconds (default 15), then reads
every `POLL` = 5 s (`:87`) until `_settled` (`:686-691`): the last two reads agree on a
non-empty list (`_stable`, `:679-683`) and that list differs from `before`, the list read
before the merge or update. Otherwise it stops at `--settle-max` (default 180, `:1008-1010`;
the window always fits two reads, `:257-258`). It records every read, `before`, the window
and the elapsed seconds. A failed `gh` read is one more read, not the end of the scenario
(`_read_files`, `:329-338`).

The stop rule never looks at the expected list, as the reviewer asked: a list that stays
wrong is read to the end of the window and recorded as it is (a FAIL, with `changed: false`
and the seconds in the report). `judge` takes the last read only if the last two agree
(`_settled_files`, `:694-709`); otherwise the check is `not observed` (→ INCOMPLETE).

Each `before` must itself be a settled list, or the early stop could take a stale list
that merely differs from a stale `before`. So the scenario now reads B at every step
(`:537-553`): when its PR opens, after A's merge, after C's merge (the informational
`E1-pre`), after "Update branch"; and Q when its PR opens and after P's merge (`:564-566`).
The read between A's and C's merges is the one that matters. Without it, the read after
both merges could settle on GitHub's after-A-only list ([b, c]). If GitHub then caught up
on C's merge (merge base C → [a, b]) during the read after "Update branch", that list
differs from `before` and could be taken: a false E1 FAIL. E1 and E1b require every read
in their chain to have settled (`:793-809`, `:811-819`).

### Alternatives I did not take

- **A longer fixed sleep** (1 line: `--settle 60`). Still one read, so a slow GitHub still
  gives a false FAIL, and every read pays the full wait (6 reads × 60 s).
- **Poll until the list matches the expected one.** Rejected by the reviewer: it hides a
  real FAIL.
- **Use GitHub's compare API (`base...head`) as the freshness check.** About 10 lines and
  one more call per read. But with two merge bases (run 1's line, docs/07-crosscutting.md:
  658-661) the compare endpoint and the PR diff may not pick the same base, and then the
  read would never settle. It also is not what "Files changed" shows.
- **Wait until the PR's `baseRefOid` equals the fetched base tip.** I cannot check offline
  whether GitHub updates that field when the base moves; a wrong guess makes every read run
  to the end of the window.

Residual risk: if GitHub shows an in-between list for longer than one poll interval, and
the previous step's list was already right, the early stop can take the in-between list.
The settled chain of `before` lists narrows this; the report shows the reads behind every
list, so the human can see it.

## The test (`tests/test_stack_mode_live_tool.py`)

Runs the tool by path through `subprocess`; never imports it (brief).

- The brief's six binding cases: (1) `:172`, (2) E2 `:185`, (3) E1 `:191`, (4) E4 `:197`,
  (5) E0 `:203`, (6) E1b `:209`. (3) and (6) now use read records that stay wrong to the
  end of the window: still FAIL (a finding), not INCOMPLETE. `_fails` (`:149-169`) also
  checks the report's `result`, `complete` and `incomplete` fields.
- Round 3's findings:
  - `:228` run 2 raised → INCOMPLETE, E3 `not observed`. Two shapes: a file that says
    `finished: true` (judged off run 2's own record), and the file `run` now writes (stopped
    at run 2).
  - `:266` run 2 held D (carry hold, rc 1; base hold, rc 3), D never built and with no PR →
    E3 FAIL, E0 PASS with D listed `not published`, result FAIL. This guards against the
    new rule over-reaching.
  - `:283` a held carried branch with D finished → FAIL.
  - `:289` D finished with no PR → INCOMPLETE.
  - `:343` a stale first read after P's merge is judged on the settled list → PASS.
  - `:354` a list that never settled (flips to the end; every read failed; B before
    "Update branch" unsettled; Q never read at open) → INCOMPLETE.
- Round 1 cases moved to INCOMPLETE under the new rule: `:220` (PR never recorded),
  `:311` (branch not confirmed deleted), `:319` (commit git could not place: S's head,
  A's merge commit, B's change on the base, D's base vs C's head). `:380` (run stopped
  early) also checks the reason list.
- `SetupLeavesItsRepositoryToTeardown` (`:438-555`): unchanged from round 3.

What the shipped test does not drive: `run` itself (it needs GitHub). The two run-side
changes (`_require_driven`, the poll loop) are checked by the scratch probe below and by
the live run. `cmd_run`'s exit code comes from `_incomplete`, which the shipped test does
drive through `judge`.

## Refuting my own test

- **(a) Genuine red? Yes.**
  - The project's C4 gate as the driver runs it (from pdca-pdca:
    `PDCA_BUNDLE=…/results/issue_625 PDCA_WORKTREE=<worktree> ./engine/scripts/run-verify.sh`):
    green leg `Ran 21 tests … OK`; red leg (production hunks reverted, so the tool is gone)
    `Ran 21 tests … FAILED (failures=30)`, every one a FAIL on "can't open file
    …stack_mode_live.py", no ERROR, no `_FailedTest`; `PDCA-EVIDENCE: C4 PASS — red
    without the fix, green with it`, rc 0. An earlier run had one ERROR (a `KeyError` in
    `:343` before its first assertion); I made that case assert first.
  - Against the rejected approach: the round-3 tool with run 2 raised gives result FAIL
    (above). With the new test file, round 3's tool fails 26 cases, most because the file
    list records changed shape, so I also re-broke each fix on top of the final patch (in a
    scratch clone) and ran the test:
    - verdict back to round 3's rule → 6 tests fail (raise, D without PR, unsettled list,
      unplaced commit, unconfirmed delete, PR never recorded);
    - E3 ignores a raise → `test_a_run_2_that_raised_is_incomplete_not_a_finding` fails;
    - judge takes one read without the settle check →
      `test_a_file_list_that_never_settled_is_incomplete` fails;
    - D excused from E0 even when it finished → the D-without-PR and raise tests fail.
- **(b) Production path? Yes for `judge`, `setup` and `teardown`; no for `run`.** The test
  runs the shipped script by path; nothing of the tool is copied or mocked. `setup` /
  `teardown` get a stand-in `gh` and a local git remote (the outside world). `run` needs
  GitHub, so no shipped test drives it. My scratch probe (`.pdca-scratch-625/probe/
  run_side_probe.py` in the worktree, not in the patch) drives the real `scenario()`,
  `_require_driven`, `cmd_run` and `_files` with `Live`'s GitHub-facing methods (or the
  clock and `_read_files`) stubbed:
  - run 2 raises → `run rc=1 finished=False`, stops after `drive run2`, judge INCOMPLETE;
  - run 2 holds D → `run rc=0 finished=True`, goes to the end, judge FAIL (E3 only);
  - D finished with no PR → `run rc=1`, stops after run 2, INCOMPLETE;
  - poll: stale twice then moves → 4 reads, 30 s; never moves → 34 reads, 180 s, recorded
    as read; a failed read then moves → 3 reads; first read of a new PR → 2 reads; flips to
    the end → 34 reads, not stable (judge: not observed).
- **(c) Fixture includes the fault? Yes.** The raise case carries a real traceback in
  `runs.run2.raised` with `finished: true`, the exact shape the reviewer probed, plus the
  shape `run` now writes. The held-D cases have D unbuilt: no PR, no base, base checks
  `None`. The unsettled cases carry a list that flips at the end and reads that all failed.
  Nothing is curated out.

## Other verification

- Root suite, clean clone of a6af7f3 + `patch.diff`, with copier
  (`.venv/bin/python3 -m tests.run_root_suite`): `root suite OK: 45 executed, 0 skipped`.
- T2 docs gate (`./engine/scripts/run-docs-check.sh` on that clone): `docs lint clean,
  site render + link audit clean`.
- Driver suite under `template/`: not run this round; the patch touches nothing there.
  T3 runs it.
- Formatter / commit hooks: the target configures none (no `.pre-commit-config.yaml`,
  `pyproject.toml`, `setup.cfg`, `ruff.toml` or `tox.ini`, no `core.hooksPath`, no
  non-sample hooks; CI lints only docs and runs the root suites). `git diff --check` clean,
  `py_compile` clean, every Python line ≤ 95 characters, `patch.diff` applies with
  `git apply --check` to a6af7f3. No linter is installed here; I checked imports by hand.
- Scratch: `.pdca-scratch-625/` in the worktree (clones, logs, probe), untracked; the
  driver's pre-gate `git clean -ffdxq` (pdca-pdca `src/pdca_harness/worktree.py:260`)
  removes it. I removed two of my own temp files with `rm -f` while assembling the test
  file; that should have been left to the harness.

## Not addressed here

The round-1 to round-3 items marked for human judgment stay in `deferred-findings.json`.

## NEEDS-HUMAN — the live Validation run (hard sign-off condition per the brief)

`setup`, `run` and `teardown` have still never run against GitHub. The brief makes the live
run the condition for accept and the thing that closes #625. `gh` and the token scopes are
declared in the brief's `External dependencies`, so there is no undeclared dependency.

```bash
gh auth refresh -s delete_repo          # token needs repo + delete_repo
W=$(mktemp -d)
python3 tools/live/stack_mode_live.py setup    --workdir "$W"   # rc 1 ⇒ read stderr; teardown still deletes the repo
python3 tools/live/stack_mode_live.py run      --workdir "$W"   # rc 1 ⇒ INCOMPLETE: blocks accept
python3 tools/live/stack_mode_live.py judge    --workdir "$W"   # PASS / FAIL / INCOMPLETE
python3 tools/live/stack_mode_live.py teardown --workdir "$W"   # or --keep to inspect
```

Attach `$W/report.md` to the bundle and post it on #625. INCOMPLETE (and `run` rc 1) lists
its reasons at the top of `report.md` and blocks accept. A FAIL does not: file each FAIL as
its own bug. Expect `run` to take several minutes: six polled file-list reads, usually
20-30 s each. The read of B after C's merge can take the full 180 s if GitHub keeps
showing the after-A list, which is expected when it picks A as the merge base. What to
expect from the driver is unchanged from round 2 (`iteration-v2/build-notes.md`, last
section).
