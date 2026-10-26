# Build notes — issue 625 / stack-mode-live-github-check-tool (iteration 3)

Target: eduralph/pdca-harness @ main, worktree at a6af7f3. Same three files as round 2:

- `tools/live/stack_mode_live.py` (new, stdlib only, repo root, outside copier's
  `_subdirectory: template`, so it never reaches rendered instances).
- `tests/test_stack_mode_live_tool.py` (new, root suite, 16 cases).
- `CONTRIBUTING.md:39-93` ("Checking stack mode on real GitHub").

Line numbers below are in the patched tree (worktree = base + `patch.diff`, checked with
`cmp`). I started from round 2's `patch.diff` (`iteration-v2/`) and changed only what the
round-2 carry-forward asks for, plus three small items from round 2's code review. Round 1
and round 2 fixes are unchanged.

## What the round-2 carry-forward asked for

`setup` created the GitHub repository first and wrote `state.json` last, after the
repository settings call, the local git steps and the push. A failure in between left a
private repository that no `state.json` named, so `teardown` stopped at "state.json not
found", a second `setup` in that work directory was refused, and a fresh work directory
made a new repository. The first one was orphaned.

I reproduced that on round 2's tool before changing anything (evidence under "Refuting my
own test", (a)).

### The fix

The invariant: every repository `setup` creates is either recorded in `state.json`, where
`teardown` deletes it, or named on stderr with the command that deletes it.

- `cmd_setup` (`tools/live/stack_mode_live.py:141-192`) now writes `state.json` with the
  repository right after `gh repo create` returns, before any step that can fail
  (`:181`), with `ready: false`. Everything after the create moved into `_prepare`
  (`:195-227`): the settings PATCH (`:199`), the checkout and the push (`:218`), the
  briefs and the bundle root. Only when `_prepare` returns does `setup` rewrite the state
  with the paths and `ready: true` (`:189`).
- If anything in that block fails (`:183-188`), `setup` exits 1 and prints the error, the
  repository name and the command that deletes it: `teardown --workdir <dir>` when
  `state.json` was written, `gh repo delete <repo> --yes` in the one case where the state
  write itself failed. This is the reviewer's second option on top of the first.
- `_write_state` (`:102-107`) writes a temp file and renames it over `state.json`, so a
  write cut short never leaves a half file that loses the repository name.
- `_state(..., ready=True)` (`:110-126`) refuses a setup that did not finish (or a
  repository `teardown` already deleted). `cmd_run` (`:509`) and `Live.__init__` (`:244`)
  use it, so `run` stops before importing the driver and writes nothing.
- A second `setup` in a work directory whose setup did not finish is still refused, but
  now names the repository it left and says `teardown` deletes it (`:143-151`).
- `cmd_teardown` (`:771-796`) works from a partial state (it only needs `repo`). A failed
  `gh repo delete` is reported with the usual cause (no `delete_repo` scope) and exits 1,
  keeping `state.json` so teardown can run again (`:787-793`); before it was a traceback.
  After a delete it marks the state `deleted` (`:794`), so a second teardown says "already
  deleted" and makes no second delete call (`:780-782`).
- A failed `gh repo create` (`:166-177`): GitHub can make the repository and still lose the
  answer. `setup` cannot tell its own repository from one another run made under the same
  name at that moment, so it does not record it for `teardown`; it prints `gh repo view` /
  `gh repo delete <repo> --yes` and exits 1. That puts the call with the human instead of
  letting `teardown` delete a repository this setup cannot show it made.

Docs: the module docstring (`:14-25`) and `CONTRIBUTING.md:64-68` say what a part-way
setup leaves and how to remove it; `CONTRIBUTING.md:92-93` says the test now also covers
`setup` / `teardown`.

Residual, not closed: a Ctrl-C in the instant between `gh repo create` returning and the
state write (`:168` → `:181`, no I/O but building a dict and one small file write) is
neither recorded nor named. A Ctrl-C anywhere after `:181` leaves the repository recorded.

### Alternatives I did not take

- **Delete the repository on failure (roll back).** About 3 lines in the `except` at
  `:183`:
  ```python
  if not exists:
      _sh(["gh", "repo", "delete", repo, "--yes"], check=False)
  ```
  The delete needs the `delete_repo` scope, which is the scope people most often lack (it
  takes its own `gh auth refresh -s delete_repo`), so the rollback fails in the likeliest
  case and the state record is needed anyway. It also moves a destructive call out of the
  one place that guards it (`teardown`'s prefix check, `:783-786`) and removes the
  half-made repository the human may want to look at. So it is not a cheaper fix, only an
  extra path.
- **Record the repository before `gh repo create`.** It would close the lost-answer case,
  but `state.json` would then name a repository that may not exist, or one another setup
  made under the same `--repo` name a moment earlier, and `teardown` would delete that
  one. `teardown` would also need a "does not exist" branch that parses `gh`'s error text
  (about 5 lines, and the wording differs between `gh` versions). I print the delete
  command for that case instead.
- **Only print the name and the delete command** (the reviewer's second option alone).
  About 4 lines, but `teardown`, the documented cleanup step, would still fail with "state
  file not found". I did both.

## Three small items from round 2's code review (untagged, done because they were cheap)

- `_merge` no longer sleeps 30 s after the last refused merge attempt
  (`tools/live/stack_mode_live.py:393-399`).
- `_fails` now also checks the report's `result`: FAIL for a run that went to its end,
  INCOMPLETE for the stopped-run case (`tests/test_stack_mode_live_tool.py:125-142`,
  `:256`). Before, a bug that sent every failing run to INCOMPLETE would have passed.
- New case: run 2's stderr holds neither "gone and merged" line → E3 FAIL with
  `"gone and merged": {"A": null, "C": null}` (`:222-226`). That is the plain path where
  `_gone_and_merged` returns None.

I did not act on the round-2 items marked for the human (for example, whether the tool's
`gh pr ready` / `gh pr merge` on the disposable repository fits `AGENTS.md`). The
carry-forward holds those in `deferred-findings.json` for sign-off.

## The test

`tests/test_stack_mode_live_tool.py` runs the tool by path through `subprocess` and never
imports it (brief).

- `JudgeLiveObservations` (`:108-259`): the brief's six binding cases (1) `:145`, (2) E2
  `:157`, (3) E1 `:163`, (4) E4 `:169`, (5) E0 `:175`, (6) E1b `:181`; round 1's cases
  (`:189-259`) and the new no-gone-line case (`:222`).
- `SetupLeavesItsRepositoryToTeardown` (`:298-415`), new. A stand-in `gh` (`FAKE_GH`,
  `:268-295`) is put first on PATH. It answers only the calls `setup` and `teardown` make,
  logs each call, and keeps the repositories it "created" in a JSON file. `git` is real;
  a scratch `GIT_CONFIG_GLOBAL` rewrites `https://github.com/` to local paths, so a push
  goes to `remote/<owner>/<name>.git`, which exists only if the case makes it. The real
  `gh` can never answer: the test checks `shutil.which("gh")` is the stand-in (`:326`),
  and strips `GH_*` / `GITHUB_*` tokens and points `GH_CONFIG_DIR` at an empty directory.
  - `:352` — two subtests: GitHub refuses the settings PATCH, and the push fails. Each:
    `setup` exits 1 with the repository created; stderr names it and
    `teardown --workdir <dir>`; `run` exits non-zero with "did not finish" and writes no
    `observations.json`; a second `setup` exits 2 naming the left repository; `teardown`
    twice exits 0, the stand-in holds no repository afterwards, and exactly one
    `repo delete <repo> --yes` call was made.
  - `:386` — a setup that finishes: exit 0, the base commit is on the local remote,
    nothing about a left repository; a second `setup` is refused without the "did not
    finish" text; `teardown` deletes the repository. A guard for the normal path (it
    passes on round 2's tool too).
  - `:406` — `repo create` makes the repository and still fails: `setup` exits 1, names
    `gh repo delete <repo> --yes`, and writes no `state.json`.

What these cases do not show: anything about GitHub's own answers. The stand-in answers
what I wrote; only the live run (below) checks `setup` / `run` / `teardown` against GitHub.

## Refuting my own test

- **(a) Genuine red? Yes.**
  - The project's C4 gate as the driver runs it (from pdca-pdca:
    `PDCA_BUNDLE=<abs>/results/issue_625 PDCA_WORKTREE=<worktree> ./engine/scripts/run-verify.sh`):
    green leg `Ran 16 tests … OK`; red leg (production hunks reverted, so the tool is
    gone) `Ran 16 tests … FAILED (failures=19)` — 16 cases, 19 counting subtests, every one
    a FAIL on python's "can't open file … stack_mode_live.py", no ERROR, no
    `_FailedTest`; `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
    The worktree matched `patch.diff` again afterwards (`cmp`).
  - Against round 2's tool (the specific regression): in a scratch clone with
    `iteration-v2/patch.diff` applied and this round's test copied in, the root runner
    gave `FAILED (failures=3)`: the two "stops after creating" subtests and the failed
    create case. The happy-path case passes there, as it should. The first assertion to
    fail was the message check, so I also ran the "stops after creating" case with the
    message checks removed: it then failed at `teardown`, with round 2's own words
    `stack_mode_live: …/work/state.json not found — run \`setup\` first` (rc 1) for both
    subtests. That is the orphan from the finding, observed, not inferred.
- **(b) Production path? Yes.** The test runs the shipped script by path, the way a human
  runs it; `cmd_setup`, `_prepare`, `cmd_run`'s state check and `cmd_teardown` are the
  real code. What is replaced is the outside world: the `gh` CLI (a stand-in) and GitHub's
  git host (a local path). Nothing of the tool is copied or mocked.
- **(c) Fixture includes the fault? Yes.** The repository is really "created" in the
  stand-in's store before the failure, and `teardown` must really remove it from there.
  The faults are injected, not curated out: the PATCH call returns 502 from the stand-in;
  the push really fails in real git (`fatal: '…/remote/fake-owner/pdca-live-stack-offline.git'
  does not appear to be a git repository`); the create really makes the repository and
  exits 1.

## Other verification

- Root suite, clean clone of a6af7f3 + `patch.diff`, with copier
  (`.venv/bin/python3 -m tests.run_root_suite`): `root suite OK: 40 executed, 0 skipped`
  (36 in round 2, plus the four new cases).
- T2 docs gate (`./engine/scripts/run-docs-check.sh` on the worktree): `docs lint clean,
  site render + link audit clean`.
- Driver suite (`template/`, `PYTHONPATH=src python3 -m unittest discover -s tests`) on the
  same clean clone: `Ran 2630 tests … OK (skipped=2)`. The patch touches nothing under
  `template/`.
- Formatter / commit hooks: the target configures none (no `.pre-commit-config.yaml`,
  `pyproject.toml`, `setup.cfg`, `ruff.toml` or `tox.ini` at the root, no
  `core.hooksPath`, no non-sample hooks). `git diff --check` clean; `py_compile` clean;
  every changed Python line ≤ 95 characters (house width). `patch.diff` applies with
  `git apply --check` to a6af7f3.
- Scratch: the clones and logs are in the untracked `.pdca-scratch-625/` inside the
  worktree, not in the patch; the driver's pre-gate reset removes it. The full root suite
  ran in a clean clone, not the worktree, because `test_update_compat` copies the working
  tree and the worktree also holds another session's `.pdca-scratch/` with nested repos.

## NEEDS-HUMAN — the live Validation run (hard sign-off condition per the brief)

`setup`, `run` and `teardown` have never run against GitHub. The offline cases above
check `setup` / `teardown`'s failure handling against a stand-in, nothing more. The brief
makes the live run the condition for accept and the thing that closes #625:

```bash
gh auth refresh -s delete_repo          # token needs repo + delete_repo
W=$(mktemp -d)
python3 tools/live/stack_mode_live.py setup    --workdir "$W"   # rc 1 ⇒ read stderr; teardown still deletes the repo
python3 tools/live/stack_mode_live.py run      --workdir "$W"   # rc 1 ⇒ could not drive: blocks accept
python3 tools/live/stack_mode_live.py judge    --workdir "$W"   # PASS / FAIL / INCOMPLETE
python3 tools/live/stack_mode_live.py teardown --workdir "$W"   # or --keep to inspect
```

Attach `$W/report.md` to the bundle and post it on #625. INCOMPLETE (or `run` rc 1) means
the tool could not drive the scenario (see `errors` in `observations.json`) and blocks
accept. A FAIL on a finished run does not block accept: file each FAIL as its own bug.
What to expect from reading the driver is unchanged from round 2 (`iteration-v2/
build-notes.md`, last section): run 2 should print the "already carries that commit;
skipped." form for A and C, and a GitHub merge commit on B's branch from "Update branch"
could make the carry hold B, which would be an E3 finding to file, not a tool problem.
