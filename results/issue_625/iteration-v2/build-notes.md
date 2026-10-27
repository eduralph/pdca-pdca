# Build notes — issue 625 / stack-mode-live-github-check-tool (iteration 2)

Target: eduralph/pdca-harness @ main (worktree at a6af7f3). New files plus one
CONTRIBUTING.md section; nothing under `template/` changes. Line numbers below are in the
patched tree unless a line says "driver" (those are `template/src/pdca_harness/…` at
a6af7f3, unchanged).

Files in the patch:

- `tools/live/stack_mode_live.py` (new, 748 lines, stdlib only; repo root, outside
  copier's `_subdirectory: template`, so it never ships to rendered instances).
- `tests/test_stack_mode_live_tool.py` (new, 12 cases, root suite).
- `CONTRIBUTING.md:39-87` ("Checking stack mode on real GitHub").

## What the round-1 review asked for, and what changed

### 1. C5: a PASS needs successful runs, every required PR, and confirmed deletes

Round 1 computed each run's exit code and never used it (`:273` then), never checked run 1
(`:311`), passed E0 on whatever PRs happened to be recorded (`:368`), and ignored a failed
branch delete (`:240`). Now:

- **Run side.** `_drive` records every run of the flow: `rc` (`cli._results_rc`), the raise
  (traceback) if any, `holds`, per-id `results`, stderr and stdout
  (`tools/live/stack_mode_live.py:256-295`). After runs 1, 3 and 4 the scenario goes on only
  if `_require` passes (`:297-305`, called at `:414`, `:428`, `:436`): the run raised
  nothing, exited 0 with no holds, every id is COMPLETE, and every id has a PR. Otherwise it
  raises `Incomplete` (`:73-75`), `cmd_run` records it in `errors` and exits 1
  (`:442-466`). That is the brief's "a `run` that cannot drive the flow", which blocks
  accept. Run 2 is the exception: its outcome is what E3 judges, so it is recorded and never
  required (`:422-425`).
- **Judge side.** Each check lists the steps it depends on. A step that was not observed
  makes the check FAIL with `"not observed": [...]` naming the step, never PASS
  (`add`, `:556-561`):
  - `_run_problems` / `_run_ok` (`:478-499`): raised, rc ≠ 0, holds, or an id not COMPLETE.
    Used by E1 and E2 (run 1), E1b (run 3), E4 (run 4) and E5 (run 1). E3 uses it on run 2
    as part of the verdict itself (see 4).
  - E0 (`:563-568`) now needs all seven PRs (A B C D P Q S). A missing one is named with
    what its last run left it as (`_outcome`, `:515-521`), e.g. `D has no PR (run2:
    PLANNED)`.
  - `_merged_ok` (`:502-512`) needs the merge recorded with the right method, and for E2,
    E3 and E4 (the checks read "after the delete") the branch confirmed gone.
  - `finished` is set only at the end of the scenario (`:196`, `:439`). `_verdict`
    (`:652-656`) reports INCOMPLETE when `errors` is non-empty or `finished` is not true, so
    a run that stopped (or was interrupted; `cmd_run` writes the file in a `finally`) is
    never reported as a plain FAIL list. `report.json` has `result` / `passed` /
    `complete` (`:679-703`); `report.md` says what INCOMPLETE means (`:659-676`).

### 2. `_on_base` read exit 128 as "not on base"

`_is_ancestor` (`:206-213`): exit 0 → True, exit 1 → False, anything else → None ("not
observed"). `_on_base` (`:215-217`) and `_holds` (`:394-397`, D's base holding A's and C's
heads) both use it; round 1's `_holds` had the same flaw. `_files_on_base` (`:399-407`)
returns None for all ids when `origin/<base>` does not resolve. The judge already compared
`headRefOid on base` with `is False` for E4 (`:629-640`), so None FAILs. I checked
`_is_ancestor` against real git in the rehearsal clone (below): unknown commit → None,
squashed head → False, merge-committed head → True, ref that does not resolve → None.

### 3. Branch delete not checked

`_delete_branch` (`:344-366`): runs the REST delete; a non-zero exit is an error unless the
output says "Reference does not exist" (422; GitHub deleted it on merge). It then confirms
with `git ls-remote --exit-code origin refs/heads/<branch>` (exit 2 = no such ref, retried
up to 5 times) and raises `Incomplete` if the branch is still listed. `_merge` (`:323-342`)
records `merged[iid] = {method, branch, branch_gone: False}` as soon as the PR reads MERGED,
then updates it with the delete result. So a refused delete shows up in the report as "A's
branch was not confirmed deleted after its merge", not "merge not recorded". `_merge` also
checks the PR reads MERGED after `gh pr merge` (`:335-338`); round 1 trusted the exit code.

### 4. E3 ignored rc / holds / D, and matched the shared prefix

- `_gone_and_merged` (`:524-542`) full-matches only the two lines `integrate._gone_branch`
  prints when it goes on: driver `integrate.py:1434-1436` ("— <line> already carries that
  commit; skipped.") and `:1509-1511` ("…, which <line> did not have — the merged work
  reaches <line> through origin/main."). The refusals at `integrate.py:1443`, `:1449`,
  `:1491`, `:1503` begin with the same words but are raised, not printed; on the carry path
  `flow.py:1575-1578` (driver) names them in a "not carried" line. E3 also collects the
  finished ids named in such a line (`refused`, `:610-612`) and needs that list empty.
- E3 (`:606-627`) needs `_run_problems(run2)` empty: no raise, rc 0, no holds, A B C D all
  COMPLETE. A D held by a refused carry is not in `holds` (driver `flow.py:3173-3177` lists
  only unpushed / conflict / base / late-rewrite holds); it is PLANNED in `results`, which
  makes `_results_rc` return 1 (driver `cli.py:741-746`). Both are checked.
- Round 1's test fixture used made-up wording for the success line ("— taking origin/main
  in."). The new fixture uses the real text of both lines, one for A and one for C
  (`tests/test_stack_mode_live_tool.py:48-54`), and the refusal case uses the real shape of
  the carry's "not carried" line over the `integrate.py:1491` message (`:55-62`).

## A defect round 1 had that the review did not name: run 2 never reached the carry

Round 1's `_drive` handed `flow._drive_and_act` every id of the run as the drive set,
finished ones included. `flow._finished_named` (driver `flow.py:1270-1280`) takes as
"finished named ids" only ids in `batch` that are COMPLETE **and not in the drive set**. So
in run 2 it found none, `_carry_finished` (`flow.py:1425`) judged nothing, and the brief's
E3 path (carry → `_merge_published` → `_gone_branch`) was never reached. `pdca flow A B C D`
does not do that: `cli._flow` calls `flow.flow_ids` (driver `cli.py:667-669`), which skips
terminal ids and passes only the rest as the drive set, with every id as the batch
(`flow.py:3446-3501`).

I confirmed it by running round 1's tool through the same offline rehearsal (below): its
run 2 exited 3 with `holds {"A": "unpushed", "C": "unpushed"}` and printed no "gone" or
"carried" line at all, and round 1's own judge then reported `E3 FAIL` (`named gone and
merged: {A: false, C: false}`, `D built on: null`). On GitHub that would have been a false
finding, caused by the tool and filed against the driver.

Fix: `_drive` calls `flow.flow_ids(cfg, ids, do_publish=True, do_act=False, by=..., today=...,
holds=...)` (`:280-285`), the CLI's own call minus `claims` (a library call claims nothing)
and `plan_missing` (every bundle has a brief, so the plan pre-pass would do nothing).
`flow_ids` drives `flow._drive_and_act` itself, so the brief's peer pattern still holds:
same stubs (`flow._drive_wave` and `publish.draft_texts`, `:274-279`), same real parts
(`subprocess.run`, `flow._publish_bundle` → `publish.publish`). For runs 1, 3 and 4 (no
finished ids) the call into `_drive_and_act` is the same as the peer's at
`template/tests/test_flow_same_wave_conflict.py:144-162`. The rehearsal (below) shows run 2
now goes through the carry: "flow: issue_A — already terminal (COMPLETE), skipped", then
"integrate: issue_A's branch origin/fix/A-live-a is gone and its PR merged at … already
carries that commit; skipped.", then "flow: carried issue_A, issue_B, issue_C (finished in
an earlier run) onto pdca-integration/main-r… before wave 0".

Alternative I did not take: keep `_drive_and_act` and copy `flow_ids`' filter. Sketch:

```python
drive = [self.cfg.bundle(i) for i in ids
         if state.state(self.cfg.bundle(i)) not in self.flow._TERMINAL]
results = {i: state.state(self.cfg.bundle(i)) for i in ids
           if self.cfg.bundle(i) not in drive}
results |= self.flow._drive_and_act(self.cfg, drive, do_publish=True, do_act=False,
                                    by="live", today=self.today, batch=list(ids),
                                    holds=holds)
```

That is about 6 lines against 3, and it is a second copy of the driver's intake (it already
leaves out `_admit` and the split-seed path, `flow.py:3464-3490`). The tool exists to be
re-run when the driver changes, so a copy that can drift from `pdca flow` defeats it.

## Other changes from round 1

- `_update_branch` (`:368-383`): GitHub's update-branch can land after the call returns,
  so the tool waits (up to 60 s) for B's head to move, records before/after, and raises
  `Incomplete` if it never moves. E1 needs `moved: true` (`:575-582`).
- `setup` (`:108-164`) refuses a work directory that already holds a setup, and checks the
  name prefix before creating anything. `run` (`:442-448`) refuses a work directory that
  already holds bundles or observations (a second `run` would otherwise skip every bundle
  as finished and merge nothing).
- `_sh` has a 600 s timeout (`:80-86`), so a hung `gh` ends the run with an error instead
  of hanging it.
- `_obj` (`:471-475`): the judge reads a truncated or hand-edited observations file as "not
  observed", never as a crash.

## The test (`tests/test_stack_mode_live_tool.py`)

Runs `sys.executable tools/live/stack_mode_live.py judge --workdir <tmp>` as a subprocess
on observation files it writes; never imports the tool (brief). `_good()` (`:73-101`) is a
finished run meeting every expectation. `_fails` (`:121-135`) asserts the exit is non-zero,
exactly the named checks FAIL (each with its text in `observed`), and every other check
PASSes, so each FAIL is pinned to the right check.

- The brief's six cases: (1) `:138`, (2) E2 / no `headRefOid` `:150`, (3) E1 / `a.txt`
  `:156`, (4) E4 / head on base `:162`, (5) E0 / integration line `:168`, (6) E1b /
  `p.txt` `:174`.
- Round-1 findings: a PR never observed → E0 (`:182`); run 2 with D held / a hold / a raise
  → E3 (`:189`, three subtests); the refusal wording → E3 with `A: null` and `not carried:
  ["A"]` (`:207`); A's branch not confirmed deleted → E2 and E3 (`:214`); S's head on base
  unknown (None) → E4 (`:221`); a run that stopped after run 3 → INCOMPLETE, with E0, E1b,
  E4, E5 "not observed" and E1, E2, E3 still PASS (`:227`).

## Refuting my own test

- **(a) Genuine red? Yes.** The project's C4 gate, run as the driver runs it
  (`PDCA_BUNDLE=results/issue_625 PDCA_WORKTREE=<worktree> ./engine/scripts/run-verify.sh`
  from pdca-pdca): green leg `Ran 12 tests … OK`; red leg (production hunks reverted, so
  `tools/live/stack_mode_live.py` is gone) `Ran 12 tests … FAILED (failures=14)` (12 cases,
  3 subtests in one), each an assertion failure on python's "can't open file …
  stack_mode_live.py", no `_FailedTest`; `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`, rc 0. I also put round 1's tool back in place of the new one and ran the
  module: 8 failures, covering every round-1 finding case (missing PR, the three run-2
  subtests, refusal wording, unconfirmed delete, stopped run) plus case (1), which now also
  checks the new `result` field. The unknown-head E4 case passes on round 1's tool too:
  round 1's judge already compared `is False`; its bug was in `run`'s `_on_base`, which no
  offline `judge` test can reach (covered by the real-git check above).
- **(b) Production path? Yes, for `judge`.** The test runs the shipped script by path, the
  way a human runs it. Nothing is copied or mocked. It does NOT cover `setup`, `run` or
  `teardown`; per the brief only the live Validation run checks those (below).
- **(c) Fixture includes the fault? Yes.** Each failure case starts from the all-pass
  document and injects exactly the fault it names (list above). The run-2 stderr uses the
  driver's real success wording, and the refusal case the driver's real refusal shape, so
  the wording check is tested against text the driver prints, not text I made up.

## Wiring rehearsal (NOT evidence for any live check)

To find wiring faults in `run` before the human's live run, I drove `setup` → `run` →
`judge` → `teardown` offline with real git and the real driver, and a throwaway fake `gh`
(Python, answering only the calls listed below) over local bare repos. Git reached them
through a `url.<dir>.insteadOf = https://github.com/` rule in a scratch `GIT_CONFIG_GLOBAL`.
It lives in the untracked `.pdca-scratch-625/` in the worktree, is not in the patch, and
the driver's pre-gate reset (`git clean -ffdxq`, pdca-pdca `src/pdca_harness/worktree.py:260`)
removes it. The fake's answers (PR files, merge shapes) are NOT GitHub's, so this proves
only that the tool and the driver are wired together, not what GitHub does.

- Happy path: `run` rc 0; all four runs rc 0, every id COMPLETE, no holds; five merges, each
  with the delete confirmed; Update branch moved B's head; `judge` PASS; `teardown`
  deleted the repo.
- Refused delete (fake returns 403 for A's branch): `run` rc 1, "could not delete A's branch
  … (HTTP 403)"; `judge` INCOMPLETE; E2 "A's branch was not confirmed deleted after its
  merge".
- Misreported merged head for A (fake returns an unknown oid): the real driver refused to
  carry A ("its PR head … is not in …"), held B ("its `Depends on` names issue_A, whose
  work its branch carries — holding issue_D this run") and so D; run 2 rc 1,
  D PLANNED, `holds` empty. `judge` FAIL (not INCOMPLETE: `run` finished), E3 observed
  `not carried: [A, B]`, `not finished: [exit code 1, D is PLANNED]`; E0 "D has no PR
  (run2: PLANNED)"; E2 FAIL on the head; E1, E1b, E4, E5 PASS (the scenario went on after
  run 2).
- Guards: `setup` / `run` refuse a used work directory (rc 2); `setup` refuses a name
  without the prefix; `teardown` refuses `fakeuser/important-repo` (rc 2); `judge` with no
  observations file rc 2.

Every `gh` call a run makes (tool and driver together), from the rehearsal log:
`api user --jq .login`; `api -X PATCH repos/<repo> -F allow_merge_commit=true -F
allow_squash_merge=true -F delete_branch_on_merge=false`; `api -X DELETE
repos/<repo>/git/refs/heads/<branch>`; `repo create <repo> --private --description …`;
`repo view <repo> --json name`; `repo view <repo> --json
mergeCommitAllowed,squashMergeAllowed`; `repo delete <repo> --yes`; `pr create --draft
--repo <repo> --base main --head <owner>:<branch> --title … --body-file …`; `pr ready`;
`pr merge --merge` / `--squash`; `pr update-branch`; `pr view --json` with `files`,
`headRefOid`, `state`, `state,headRefOid`, `state,headRefOid,mergeCommit`,
`number,url,baseRefName,headRefName,headRefOid`.

## Other verification

- Full root suite on a clean clone of a6af7f3 + `patch.diff`, with copier
  (`/home/eddie/pdca/pdca-pdca/.venv/bin/python3 -m tests.run_root_suite`): `root suite OK:
  36 executed, 0 skipped`. (The first run inside the worktree errored in
  `test_update_compat` setUpClass because that test snapshots the working tree and picked up
  the rehearsal's nested git clones as broken submodules. That is my scratch folder, not the
  patch; the clean clone shows it, and the driver's reset removes the folder before Check.)
- T2 docs gate (`./engine/scripts/run-docs-check.sh` on the clean clone): `docs lint clean,
  site render + link audit clean`.
- Formatter / commit hooks: the target configures none (no pre-commit config, no ruff /
  black / flake8 config, no `core.hooksPath`; workflows are docs / render / triage only).
  `git diff --check` clean; `py_compile` clean; every line ≤ 95 characters (house width;
  `flow.py` keeps most lines under it). `patch.diff` applies with `git apply --check` to
  a6af7f3.

## Ruled out

- Importing the tool in the test: the brief forbids it (the red leg would be an import
  error, which the gate reads as UNVERIFIABLE).
- Adding a test-only subcommand to reach `_is_ancestor` offline: it would add CLI surface
  only for testing; the real-git check above covers it, and the live run exercises it.
- `gh pr merge --delete-branch`: it also touches the local branch in the cwd; the REST
  delete touches only the remote one, and its result can be checked.
- Polling PR files until they stop changing instead of a fixed `--settle`: not flagged; the
  docs state the cost. If E1/E1b FAIL on the live run, re-run with a larger `--settle`
  before filing a bug.
- Running the live check myself from the Do beat: it creates a real repository and marks
  ready / merges PRs, which is the human's Validation step (and STOP discipline).

## NEEDS-HUMAN — the live Validation run (hard sign-off condition per the brief)

`setup`, `run` and `teardown` have never run against GitHub; only the offline rehearsal
above. The brief makes this run the condition for accept and the thing that closes #625:

```bash
gh auth refresh -s delete_repo          # token needs repo + delete_repo
W=$(mktemp -d)
python3 tools/live/stack_mode_live.py setup    --workdir "$W"
python3 tools/live/stack_mode_live.py run      --workdir "$W"     # rc 1 ⇒ could not drive: blocks accept
python3 tools/live/stack_mode_live.py judge    --workdir "$W"     # PASS / FAIL / INCOMPLETE
python3 tools/live/stack_mode_live.py teardown --workdir "$W"     # or --keep to inspect
```

Attach `$W/report.md` to the bundle and post it on #625. INCOMPLETE (or `run` rc 1) means
the tool could not drive the scenario: see `errors` in `observations.json`; that blocks
accept. A FAIL on a finished run does not block accept: file each FAIL as its own bug.

What to expect, from reading the driver and the rehearsal:

- Run 2's line is a new one (its batch A B C D has a different key from run 1's A B C,
  driver `integrate.py:140-178`), so it starts at `origin/main`, which already holds A's and
  C's merge commits. The fold should therefore print the "already carries that commit;
  skipped." form for both, as in the rehearsal. E3 accepts that form and the "reaches …
  through origin/main" form.
- Run 2 happens after "Update branch" put a GitHub merge commit on B's branch (brief's
  order). If the carry treats that commit as a rewrite or a foreign commit and holds B,
  E3 FAILs with B in `not carried`: a finding to file, not a tool problem.
- Needs a `gh` with `pr update-branch` (this machine: gh 2.103.0). The default 15 s settle
  may be short on a slow day (see Ruled out).
