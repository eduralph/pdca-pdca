# Build notes — issue 625 / stack-mode-live-github-check-tool

Target: eduralph/pdca-harness @ main (worktree at a6af7f3). New files only, plus one
CONTRIBUTING.md section. Nothing under `template/` changes. Line numbers below are in the
patched tree.

## What the patch adds

- `tools/live/stack_mode_live.py` (new, stdlib only; outside copier's `_subdirectory:
  template`, so it does not ship to rendered instances).
  - `setup` (`:93-147`): resolves the owner (`gh api user`), names the repo
    `pdca-live-stack-<UTC timestamp>` (`PREFIX`, `:48`). It refuses a name without the
    prefix and refuses an existing repo unless `--reuse` is passed. It runs
    `gh repo create --private`, then a PATCH to allow merge commits and squash and to keep
    branches on merge, so the tool deletes them itself. It inits a local checkout, sets a
    `gh auth git-credential` helper so the plain `git push` inside `publish.publish` can
    authenticate, pushes a `base.txt` commit, and writes the scenario briefs to
    `briefs/<id>.md` plus `state.json`.
  - `run` (`Live`, `:150-332`; `cmd_run`, `:335-351`): puts `template/src` on `sys.path`.
    It builds its own `Config` with the same field set as the fixture's `_cfg`
    (`template/tests/test_integrate_stack_bases.py:61-68`), except `publisher.mode=
    "command"` (so publish is not a dry run, as at
    `template/tests/test_flow_same_wave_conflict.py:60`) and `repo_checkouts` pointing at
    the live clone. Briefs carry the fields of the fixture's `_brief` (`:90-94`) plus
    `Depends on` (`_brief_text`, `:81-90`). The only stubs are:
    - `flow._drive_wave` → `Live._drive_wave` (`:211-218`), which writes the fixed patch
      and accepts, like the peer at `test_flow_same_wave_conflict.py:119-129`. It also
      writes `commit-msg.txt` and `pr-description.md` (`_accept`, `:200-209`).
    - `publish.draft_texts` → `lambda: True` (as at the peer's `:156`).

    `subprocess.run`, `flow._publish_bundle` and `publish.publish` stay real, so real
    pushes and real `gh pr create` happen. `flow._drive_and_act` is called exactly as the
    peer calls it at `:160-162` (`_drive`, `:254-279`). The tool does not import the
    `StackFoldGit` fixture.
  - The scenario order (`scenario`, `:308-332`):
    1. run1 = A, C, B.
    2. Merge A and C with merge commits, then delete their branches through the REST API.
    3. B's files; `gh pr update-branch`; B's files again.
    4. `gh pr view A --json state,headRefOid,mergeCommit`, plus on-base checks by real
       `git merge-base --is-ancestor` after a fetch.
    5. run2 = A, B, C, D, all named (brief §Design). Records D's recorded stack-base tip
       at build time and whether it holds A's and C's pushed heads.
    6. run3 = P, Q. Merge P, delete its branch, read Q's files with no update.
    7. Merge B, then check each of A/B/C's files on `origin/main`.
    8. run4 = S, squash-merged, branch deleted, view plus on-base checks.

    S runs on its own (run4), not in run1. If S sat in run1's wave 0, B's PR would carry
    S's file until S merged, so `E1` could not be "exactly B's own files".
  - `judge` (`judge`, `:359-434`; `cmd_judge`, `:453-473`): reads only the observations
    file. It emits checks E0, E1, E1b, E2, E3, E4, E5 (`CHECK_IDS`, `:60`) with id,
    PASS/FAIL, expected and observed, and an informational `E1-pre` (B's files before the
    update; brief says informational). It writes `report.json` and `report.md` and exits 0
    only if every check passes and `errors` is empty. A missing observation is a FAIL with
    "not observed", never a pass.
  - `teardown` (`:476-487`): `gh repo delete --yes`, only for a name with the prefix;
    `--keep` skips.
- `tests/test_stack_mode_live_tool.py` (new, root suite): six cases, one per numbered item
  of the Success criterion. Each writes `observations.json` to a temp dir and runs
  `sys.executable tools/live/stack_mode_live.py judge --workdir <tmp>` through
  `subprocess`. The tool is never imported. Every failure case also asserts that all
  OTHER checks stay PASS, so each FAIL is attributed to the right check.
- `CONTRIBUTING.md:39-75`: how to run it, what it needs (`repo` + `delete_repo` scopes),
  what it costs (one private repo, seven PRs, a few minutes, no model calls), the
  safety rules, and what each check means.

## How each check reads the observations

- E0: every recorded PR's `baseRefName` equals `base`.
- E1 / E1b: sorted file lists equal the id's own files.
- E2: `state == MERGED`, `headRefOid == prs.A.pushed_head` (read with `git ls-remote`
  right after the run that published it), `mergeCommit.oid` present, and that oid on the
  base.
- E3: for both A and C, a stderr line containing `<branch> is gone and its PR merged`.
  That is the wording of both `integrate._gone_branch` messages that do not raise
  (`template/src/pdca_harness/integrate.py:1440` area, the "skipped" one, and the
  take-in path). The check also needs no `STOPPING` and no `did not integrate`, and D's
  built-on tip holding both pushed heads. The brief names A's branch only. I check C too,
  because the brief's wording is "the deleted branches were taken through the base".
- E4: `mergeCommit` on the base is True and `headRefOid` on the base is False (False, not
  None: a missing oid is not evidence).
- E5: each of A, B, C has its file on `origin/main` with its content.

## Ruled out

- Importing the tool in the test: forbidden by the brief (the red leg would become an
  import error, which the gate reads as UNVERIFIABLE).
- `gh pr merge --delete-branch`: it also touches the local branch in the cwd. A REST
  `DELETE git/refs/heads/<branch>` deletes only the remote one.
- Waiting for PR diffs by polling until the list stops changing: a fixed `--settle`
  (default 15 s) is simpler and its cost is shown in the docs. If GitHub is slow, E1/E1b
  can read a stale list. A human who sees an E1/E1b FAIL should re-run with a larger
  `--settle` before filing a bug.

## Refuting my own test

- **(a) Genuine red? Yes.** I moved `tools/live/stack_mode_live.py` aside (`mv` to
  `.off`) and ran `python3 -m tests.run_root_suite tests.test_stack_mode_live_tool`:
  `FAILED (failures=6)`, `6 failure(s), 0 error(s)`, rc 1. These are assertion failures,
  not import errors. With the file restored: `root suite OK: 6 executed, 0 skipped`, rc 0
  (re-run after my last edit, same result).
- **(b) Production path? Yes, for `judge`.** The test runs the shipped script by path as
  a subprocess, the same way a human runs it. Nothing is copied or mocked. It does NOT
  cover `setup`, `run` or `teardown`. Per the brief, those are checked only by the live
  Validation run (below).
- **(c) Fixture includes the fault? Yes.** Each failure case starts from the all-pass
  document and injects exactly the fault the criterion names: no `headRefOid`; B listing
  `a.txt`; S's head on the base; D's PR based on `pdca-integration/main-r…`; Q listing
  `p.txt`. It then asserts that check FAILs with that observed value and that the rest
  still PASS.

## Other verification

- Full root suite with copier present (`/home/eddie/pdca/pdca-pdca/.venv/bin/python3 -m
  tests.run_root_suite`): `30 executed, 0 skipped`, OK. So the new `tools/` dir breaks
  no render or update case.
- In-process smoke check of `run`'s wiring with no network: the `Config` builds
  (`wave_mode` stack, publisher `command`), and `cli._results_rc`,
  `flow._drive_and_act`, `flow._drive_wave` and `publish.draft_texts` all exist. I did
  NOT drive `run` end to end offline. That would need a fake `gh`, which is the stand-in
  the brief rules out for this step.
- Formatter / hooks: the target configures none (no pre-commit config, no ruff/flake8/
  black config, no `core.hooksPath`; workflows are docs/render/triage only). Lines are
  kept to the house width (≤95, except one 96-column usage line in the docstring).
  `git diff --check` is clean.

## NEEDS-HUMAN — the live Validation run (hard sign-off condition per the brief)

`setup`, `run` and `teardown` have never been run. I did not create a GitHub repo from the
Do beat. That run is the brief's Validation step, and it is what closes #625. Steps:

```bash
gh auth refresh -s delete_repo          # token needs repo + delete_repo
W=$(mktemp -d)
python3 tools/live/stack_mode_live.py setup    --workdir "$W"
python3 tools/live/stack_mode_live.py run      --workdir "$W"     # rc 1 ⇒ could not drive: blocks accept
python3 tools/live/stack_mode_live.py judge    --workdir "$W"
python3 tools/live/stack_mode_live.py teardown --workdir "$W"     # or --keep to inspect
```

Attach `$W/report.md` to the bundle and post it on #625. A `run` that exits 1 (see
`errors` in `observations.json`) is a tool defect and blocks accept. A FAIL in the report
does not block accept: file each one as its own bug.

Things that could trip the first live run, which I could not check without GitHub:
- `gh pr update-branch` needs a recent `gh`.
- Run 2 drives finished, published A/B/C again. How the flow treats them is exactly what
  E3 observes. If the flow re-publishes B, that shows up in the stderr in
  `observations.json`.
- The 15 s settle may be short on a slow day.
