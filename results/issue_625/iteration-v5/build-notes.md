# Build notes — issue 625 (stack-mode live GitHub check tool), iteration 5

Target: eduralph/pdca-harness @ main (a6af7f3), worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`.
Line numbers below are on the patched files (new files) or on main @ a6af7f3 (driver code).

## What the patch does

Four files, all new code or new doc text; no driver change (`template/src` untouched).

- `tools/live/stack_mode_live.py` (new, 1448 lines, stdlib only). Five subcommands:
  - guard, no network: `guard()` :113 refuses a `--repo` not named `pdca-stack-sandbox` and
    without `sandbox` in its name, `eduralph/pdca-harness` by name, and a missing, empty or
    multi-word token file.
  - `use_token()` :137 drops `GH_TOKEN`, `GITHUB_TOKEN`, `GH_ENTERPRISE_TOKEN`,
    `GITHUB_ENTERPRISE_TOKEN`, `GH_HOST`, `GH_REPO` from the process environment, sets
    `GH_TOKEN` to the token file's token and `GIT_CONFIG_GLOBAL=/dev/null` (:148). Every `gh`
    and `git` child, the driver's included, inherits that.
  - `preflight()` :168 reads `gh api repos/<repo>`: refuses an answer for another repo
    (rename/redirect), not private, no push, and (when the step merges) `allow_merge_commit`
    or `allow_squash_merge` false; warns when a merge setting is absent, and (:204) when the
    repo is a personal account's private repo (draft PRs, see NEEDS-HUMAN below).
  - `cmd_setup` :321: guard, empty-workdir check, preflight, then writes `state.json` BEFORE
    creating the branch (:340), creates `live-<UTC stamp>` from `main` with
    `POST repos/<repo>/git/refs`, records again (:348), clones (`_clone` :375, credential
    helper `!gh auth git-credential` set in the clone only, :381-382), writes every scenario
    bundle's brief and records the PR branch the driver will use for each
    (`publish._branch_name`, publish.py:622-630) and the integration prefix
    (`integrate.integration_branch(cfg, base)`, integrate.py:140-157). On any later failure it
    prints the exact `teardown` command (:356-360).
  - `cmd_run` :874 + class `Live` :431: the scenario. Each run is `flow.flow_ids(...)` (:571)
    with only `flow._drive_wave` and `publish.draft_texts` patched (:565-567); real
    `subprocess.run`, real `flow._publish_bundle` → `publish.publish`, real folds. Exit code is
    `cli._results_rc` (:577; cli.py:707). Records PRs, merges (ready → merge pinned with
    `--match-head-commit` → confirm MERGED → delete branch → confirm with
    `git ls-remote --exit-code`, :615-687), Update branch (:689), polled file lists (:707),
    after-merge views and ancestry (:750), base contents (:765), what D was built on (:784).
    Phases (:801-872) each check their own preconditions, so one refused step does not stop
    the independent ones (run 3, run 4). Exits 3 when any check would be INCOMPLETE.
  - `judge()` :1031 / `_e3()` :1168 / `cmd_judge` :1278: one row per check with PASS / FAIL /
    INCOMPLETE, `report.json` + `report.md`; exit 0 PASS, 1 FAIL, 3 INCOMPLETE.
  - `cmd_teardown` :1305: guard, `--keep` (:1328) changes nothing, preflight without the merge
    settings, then closes open PRs whose head is a run branch (:1367), deletes the run base +
    recorded branches + every remote branch under the run's prefix (:1345, :1374), never
    `main` / the default branch (:1335), then removes only `checkout`, `checkout.pdca-*` and
    `project` from the work dir (:1388) and keeps the record files.
- `tests/test_stack_mode_live_tool.py` (new, 572 lines). Runs the tool by path, never imports it.
- `CONTRIBUTING.md:39-89` new section "Checking stack mode on real GitHub": how to run,
  what it needs, what it costs, how to read the report, and the STOP-exception paragraph (:86-89).
- `AGENTS.md:14-18` one bullet under "STOP discipline": the rules cover this project's own
  PRs; the one exception is the tool's own ready-marks and merges, started by a human, on a
  repo that passes its guard; it covers no other merge on the sandbox.

## Success criterion → test (tests/test_stack_mode_live_tool.py)

| Criterion | Test |
|---|---|
| (1) all match → exit 0, all PASS | `test_observations_matching_every_check_pass` :184 |
| (2) A no headRefOid → E2 FAIL with observed value | `test_a_merged_pr_reporting_no_head_oid_fails_e2` :191 |
| (3) B after Update branch lists a.txt → E1 FAIL | `test_b_still_listing_a_file_of_a_after_update_branch_fails_e1` :200 |
| (4) S head on base → E4 FAIL | `test_a_squash_merge_whose_head_is_on_the_base_fails_e4` :207 |
| (5) base = line or main → E0 FAIL | `test_a_pr_against_the_line_or_main_fails_e0` :214 (both) |
| (6) Q lists p.txt → E1b FAIL | `test_q_listing_a_file_of_p_after_p_merged_fails_e1b` :223 |
| (7) preconditions missing → INCOMPLETE, not FAIL | `test_missing_preconditions_are_incomplete_not_fail` :230 (7 shapes: A delete, C delete, A merge refused, Update branch refused, P merge refused, list never settled, ancestry exit 128) |
| (7b) run 2 non-zero / raised after preconditions → E3 FAIL with rc / exception / stderr tail | `test_run_2_failing_after_its_preconditions_were_observed_fails_e3` :288 |
| (8) sandbox token reaches gh, not ambient; exit 0 | `test_preflight_passes_the_sandbox_token_to_gh_and_writes_nothing` :414 (also: cwd stays empty) |
| (9) private false → non-zero | `test_preflight_refuses_a_repo_that_is_not_private` :434 |
| (10) `--repo eduralph/pdca-harness` → non-zero, gh never called | `test_preflight_refuses_the_harness_repo_without_calling_gh` :442 |
| (11) missing / empty token file → non-zero, gh never called | `test_preflight_refuses_a_missing_or_empty_token_file_without_calling_gh` :450 |
| (12) squash / merge commits off → non-zero naming the setting | `test_preflight_refuses_a_repo_without_squash_or_merge_commits` :463 |
| (13) setup/run/teardown + harness repo → non-zero, no gh | `test_writing_steps_refuse_the_harness_repo_without_calling_gh` :480 |
| (14) setup/run/teardown + missing token → non-zero, no gh | `test_writing_steps_refuse_a_missing_token_file_without_calling_gh` :489 |
| (15) teardown deletes exactly the recorded base + branches, closes the PR, no heads/main / repo delete / PATCH | `test_teardown_removes_the_runs_branches_and_pr_and_nothing_else` :535 |

Extra cases: E3 accepts either `_gone_branch` success line and never the shared opening
(:318, integrate.py:1434-1436 / :1509-1511 vs the refusal printed through flow.py:1575-1578);
teardown deletes an unrecorded branch under the run's prefix and not another run's (:553);
`--keep` makes no gh call (:561); preflight's draft warning (:427).

For (13)/(14), `run` and `teardown` get a `state.json` that would otherwise let them proceed,
so only the guard can stop them, and each case asserts the guard's own message, not only the
exit code.

## Design decisions (and what I ruled out)

1. **`flow.flow_ids`, not a direct `flow._drive_and_act` call.** The brief names the peer at
   template/tests/test_flow_same_wave_conflict.py:144-162, which calls `_drive_and_act`
   directly. `flow_ids` (flow.py:3370-3501) is the call `pdca flow <ids>` makes
   (cli.py:667-669); it skips finished ids and hands `_drive_and_act` the rest with every
   named id as `batch` (:3498-3501). Run 2 needs exactly that: A, B, C finished and still in
   the batch, so `_finished_named` (flow.py:1270-1280) and `_carry_finished` (:1425) see
   them. Calling `_drive_and_act` directly would mean copying flow_ids' drive-set loop
   (flow.py:3449-3491, 43 lines, about 20 of them code; the terminal skip is :3458) and its
   results merge (:3498) into the tool, a parallel copy of driver logic. The stubs are the
   peer's minus `subprocess.run` and `_publish_bundle`, which the brief asks to keep real.
2. **Teardown keeps `state.json`, `observations.json`, `report.md`, `report.json`.** The brief
   says "remove the local work dir unless --keep". Following the documented order
   (setup, run, judge, teardown) that would delete `report.md` before the human attaches it
   to the bundle. Teardown removes the clone, its `checkout.pdca-*` worktrees and locks, and
   the bundle root (`project/`), and never anything else in the directory the user named
   (so `--workdir ~` by mistake cannot wipe a home directory). Deviation, flagged here and
   stated in CONTRIBUTING.md:73-74.
3. **Teardown does not refuse on merge settings** (`need_merge=False`). Refusing to clean up
   because squash merges were switched off would strand the run's branches. It still
   requires the guard, private and push.
4. **`--keep` changes nothing** (no PR closed, no branch deleted, no local removal), reading
   the Goal ("--keep skips this") and the Teardown paragraph together.
5. **File-list polling.** Every read takes `files,baseRefOid,headRefOid` in one call. Stop
   when two reads in a row agree on the files AND both show the PR on the base tip just
   fetched and on the expected head; else stop at `--settle-max` (180 s). Never looks at the
   expected files. `judge` takes the list the last two reads agree on and records `synced`.
   I did not make the OID match a hard condition in `judge`: if GitHub's `baseRefOid` lags in
   a way I have not seen, a hard gate would turn every list into INCOMPLETE and block accept
   with no driver bug; as a soft condition it only makes the poll wait longer.
6. **E0 and D.** A, B, C, P, Q, S always need a PR; D only when run 2 left it COMPLETE (run 2's
   own outcome is E3's). A wrong base on any PR read is a FAIL even if other PRs are missing:
   that observation is complete.
7. **Phases continue past an independent failure.** A refused A merge skips run 2 and B's
   merge, but run 3 and run 4 still run, so one live run reports as much as it can.
8. **`GIT_CONFIG_GLOBAL=/dev/null`.** A global `url.*.insteadOf` to ssh would otherwise make
   pushes go out over the user's ssh key instead of the sandbox token. The clone gets its own
   identity (`pdca stack-mode live check <pdca-live-check@example.invalid>`, :86-87) so a
   private-email push block on the user's account cannot refuse the push.
9. **No `#625` in commit messages or PR bodies on the sandbox**: GitHub would add a
   cross-reference to eduralph/pdca-harness#625 for every PR of every run.
10. **`full_name` check in preflight**: GitHub follows renames; `repos/<x>-sandbox` answering
    for another repository is refused.
11. **Driver imported from this checkout only** (`_driver()` :258 refuses an installed
    `pdca_harness`), with `sys.dont_write_bytecode` so it leaves no `.pyc` in `template/src`.

Started from `iteration-v4/patch.diff` as the brief allows: kept the judge's shape, the
`_gone_branch` line matching, the stubbed `_drive_wave` / `_accept`, and the merge / delete /
update-branch helpers; replaced repo create/delete with the sandbox, run base, token and guard
design; added `preflight` and the new `teardown`; moved INCOMPLETE from a report-level flag to
a per-check result; made a run-2 raise or non-zero exit an E3 FAIL once its preconditions are
observed (v4 made a raise INCOMPLETE).

## Verification

- **C4 gate, the project's runner** (`engine/scripts/run-verify.sh` with `PDCA_BUNDLE` /
  `PDCA_WORKTREE`, under `timeout 900`): green leg "Ran 20 tests … OK"; red leg (tool and doc
  hunks reverted) "Ran 20 tests … FAILED (failures=34)", no `_FailedTest`; final line
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. All 20 test methods failed
  on the red leg. The worktree was restored by the script's trap (git status unchanged).
- **Whole root suite** (`python3 -m tests.run_root_suite`, the target's own entry point, with
  copier, under `timeout 2400`): "Ran 44 tests … OK", "root suite OK: 44 executed, 0
  skipped". `template/` is untouched, so the offline driver suite is not affected.
- **Mutation checks** (one rule broken at a time in the tool, matching test run, file
  restored and re-compared byte for byte): each went red — run-2 raise read as INCOMPLETE
  (the v4 rule) → (7b) red; ambient token kept → (8) red; both repo-name guards off →
  (10)/(13) red; teardown deleting `main` → (15) red; a missing precondition read as FAIL →
  (7) red (6 failures); merge settings only warned → (12) red; a gh call before `--keep` →
  keep test red; E0 accepting `main` → (5) red. One mutation stayed green on its own: turning
  off only the explicit `eduralph/pdca-harness` refusal, because the name rule refuses it
  with the same "refusing eduralph/pdca-harness" message; turning off both goes red.
- **Local end-to-end simulation, not shipped** (`$PDCA_WORKTREE/.cache/live-sim/`, git-ignored):
  a stand-in `gh` backed by a local bare repo (PR store, merge / squash / update-branch via
  `git merge-tree`, refs API), `https://github.com/` rewritten to the bare repo through
  `GIT_CONFIG_SYSTEM`, a dummy token and the repo name `fake-owner/pdca-stack-sandbox`. It
  drives the real tool → real driver → real git end to end:
  - clean: all seven checks PASS; run 2's fold printed both "already carries that commit;
    skipped." lines; teardown closed D's and Q's PRs and went through 13 branches (8 deleted,
    5 already gone after their merges), leaving only `main`; the stand-in saw only the
    sandbox token although `GH_TOKEN` was set to another value in the environment; the work
    dir kept only the four record files.
  - Update branch refused: only E1 INCOMPLETE, `run` and `judge` exit 3.
  - merged PRs reporting no head (the case the brief names: `merged.merged_head` getting no
    usable `headRefOid`): E2, E3, E4 FAIL, E3 carrying the carry's "is not carried" lines and
    run 2's rc 1; `run` exits 0 (complete), `judge` exits 1. So a driver/host mismatch is
    filed as a FAIL, not a blocked accept.
  This shows the plumbing works against the real driver. It says nothing about what GitHub
  answers; only the live run does.

## Refute-your-own-test answers

- **(a) Genuine red?** Yes. The C4 red leg reverts the production hunks (the tool file and
  the doc text) and all 20 test methods fail on their assertions (34 failures counting
  sub-cases), not on an import (the test never imports the tool). Beyond "file missing", the
  eight mutations above each turn the matching test red, so the cases bind the rules, not
  just the file's existence.
- **(b) Production path?** Yes. Every case runs `tools/live/stack_mode_live.py` itself as a
  subprocess, by path: the real `judge`, `preflight`, guard and `teardown` code, which also
  imports the real driver (`integrate.integration_branch`) for the prefix. No copy of any of
  it is in the test. The stand-in is `gh` only, which the brief prescribes for C4.
- **(c) Fixture includes the fault?** Yes. The judge fixtures write the failing observation
  itself (no headRefOid, a.txt still listed, head on base, wrong base, p.txt listed, a delete
  not confirmed, a refused merge, a run 2 that exited 1 or raised). The guard cases set an
  ambient `GH_TOKEN` / `GITHUB_TOKEN` the tool must not pass on, and give `run` / `teardown`
  a ready `state.json` so only the guard can stop them. The teardown world holds `main`,
  another run's base, line and open PR, so "deletes exactly" and "never main" are tested
  against the things that must survive.

## For the human at sign-off

**Hard sign-off condition (brief).** Run once, on this machine (gh 2.103.2 here; the tool uses
`gh pr view --json baseRefOid`, `gh pr merge --match-head-commit` and `gh pr update-branch`):

```bash
cd ../pdca-harness   # the patched checkout
python3 tools/live/stack_mode_live.py preflight
W=$(mktemp -d)
python3 tools/live/stack_mode_live.py setup    --workdir "$W"
python3 tools/live/stack_mode_live.py run      --workdir "$W"
python3 tools/live/stack_mode_live.py judge    --workdir "$W"
cp "$W/report.md" <pdca-pdca>/results/issue_625/live-report.md
python3 tools/live/stack_mode_live.py teardown --workdir "$W"
```

INCOMPLETE blocks accept; each FAIL is its own bug. The #625 closing comment must say the
check used the persistent private sandbox with a fresh `live-<stamp>` base per run instead of
a disposable repo (the brief's stated departure).

NEEDS-HUMAN external dependency: draft pull requests on the private sandbox — `publish.publish` opens every PR with `gh pr create --draft` (template/src/pdca_harness/publish.py:330), and as far as I know GitHub offers draft PRs in private repositories only on organization plans (Team, Enterprise), not in a personal account's private repository (Free or Pro). If `eduralph/pdca-stack-sandbox` is owned by the personal account `eduralph`, the first publish of the live run is likely refused, no PR opens, and the run ends INCOMPLETE, which blocks accept. I could not check this: Do may not touch GitHub. `preflight` now warns about it. Check before the live run (for example `gh api repos/eduralph/pdca-stack-sandbox --jq .owner.type`; one throwaway `gh pr create --draft` on the sandbox settles it). If drafts are refused, the fix is a sandbox owned by an organization whose plan allows drafts (or a re-plan); not a change in this tool.

```toml
[[doctor.checks]]
group = "engine"
id    = "sandbox-draft-prs"   # publish opens drafts; the live check needs them on the sandbox
cmd   = "test \"$(GH_TOKEN=\"$(cat \"$HOME/.config/pdca/sandbox-gh-token\")\" gh api repos/eduralph/pdca-stack-sandbox --jq .owner.type)\" = Organization"
hint  = "publish opens every PR as a draft; GitHub lists draft PRs in private repos for Team/Enterprise organization plans. Confirm with one throwaway `gh pr create --draft` on the sandbox, or move the sandbox to an organization whose plan allows drafts"
level = "WARN"
```

(The row is a proxy: it checks the owner type, not draft support itself, which GitHub's API
does not expose. WARN, so a personal sandbox that does allow drafts only costs a warning.)

Other live-run risks, all reported as INCOMPLETE (never a false FAIL) if they bite: the token's
pull-request permissions (ready, merge, update-branch) are not checked by the doctor row;
`allow_update_branch = false` on the sandbox may make GitHub refuse "Update branch" (E1
INCOMPLETE); if GitHub's `baseRefOid` does not move with the base, each file-list read waits
the full `--settle-max` (about 3 minutes each, 6 reads) and records `synced: false`.

**Second §6 item (brief):** the STOP-exception wording, `AGENTS.md:14-18` and
`CONTRIBUTING.md:86-89`, to review and accept on its own.

## Commit-readiness

The target repo configures no formatter, linter or commit hook (no `.pre-commit-config.yaml`,
no ruff/flake8 config, no hooks installed in `.git/hooks`; CI runs render-check and
docs-check only, neither touching these files). Checked anyway: `git diff --check` clean
(new files included), no new line over 100 characters (the one 102-character line in
CONTRIBUTING.md:26 is pre-existing), both Python files compile, no unused imports (ast
check), files end with a newline. The DCO `Signed-off-by` is added by publish's
`git commit -s`. Patch: 113,989 bytes, 4 files (size signal threshold 125 KB). Nothing was
pushed and no PR was opened.
