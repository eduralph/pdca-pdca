# Build notes — issue 625 (stack-mode live GitHub check tool), iteration 6

Target: eduralph/pdca-harness @ main (a6af7f3, still `origin/main`), worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`. Line numbers are on the patched files (all four are
new files or carry new sections), or on driver code at main @ a6af7f3 where they name
`template/src/...`.

Started from `iteration-v5/patch.diff`, which applies cleanly to a6af7f3. The carry-forward asks
for one fix and says everything else stays as is, so everything outside the fix below is
iteration 5's code, unchanged.

## The carry-forward fix

**The bug (reviewer F1, §6 items 117/120).** `judge`'s `settled_files` used the list the last two
reads agreed on and ignored both the `synced` flag `run` records and the commit ids each read
carries. A poll that ran out of time on two identical stale reads (GitHub's answer from before
the merge or the update) was judged as if it were fresh: E1 / E1b came out PASS or FAIL where
INCOMPLETE is right.

**The fix, `tools/live/stack_mode_live.py:976-1013`.** After the existing "last two reads agree"
check (:993-996), the list is used only if all three hold, else E1 / E1b are INCOMPLETE with the
reason:

1. `expect` holds a non-empty `baseRefOid` and `headRefOid` (:997-1001). Reason: "`run` recorded
   no baseRefOid the PR should be on, so its reads cannot be checked".
2. Both of the last two reads show exactly those commits (:1002-1008). Reason names each read
   that is off, what it showed and what was expected, e.g. "the last two reads are not both on
   the commits `run` expected (read 2 of 3 shows headRefOid bbbbbbbbbbbb, not 777777777777), so
   the list may be GitHub's answer from before the merge or update". The human can read off the
   report which commit GitHub was still on.
3. `rec["synced"] is True` (:1009-1012). Reason: "`run` recorded the poll as not synced
   (synced: false) after N read(s) over S s".

The commit check runs before the flag check because its message says *why* a poll did not sync.
`seen` (shown on E1 / E1b and on the four recorded-not-judged lists) now also carries `expect`
(:988-990). E1 (:1099) and E1b (:1113) already turn a reason from `settled_files` into a "not
observed" entry, so they need no change; `judge` then exits 3 (`cmd_judge`, :1324) and so does
`run` (:901-907).

**`run` is unchanged** (`Live._files`, :709-750). Its early stop already needs the last two reads
to agree and both to be on `expect` (:743-745), so every poll that stopped early passes the new
rule; only a poll that ran out of time (or a hand-edited file) is now INCOMPLETE. `run` records
`synced` for the last read only (:749); the judge no longer relies on that and checks both reads
itself, as the carry-forward asks. One difference is deliberate: `run`'s `synced()` (:725-727)
treats an empty expected value as matching, so when the base tip or the pushed head could not be
read, the poll can still stop early and the judge then reports INCOMPLETE (nothing to check the
reads against). Making `run` strict there too would only make it wait the full `--settle-max`
(180 s) for the same INCOMPLETE, so I left it.

**Doc lines that described the old rule.** Tool docstring :40-41 (judge's exit codes: 1 on a
FAIL, 3 on an INCOMPLETE) and :46-47 ("a file list that never settled on the PR's current base
and head"); `CONTRIBUTING.md:80-81`, same wording (paragraph :77-85 re-wrapped, so the section
gains one line). The STOP-exception text (`AGENTS.md:14-18`, `CONTRIBUTING.md:87-90`) is
untouched.

## Test changes (`tests/test_stack_mode_live_tool.py`)

- `_reads` (:73-85) now takes the commits, as the carry-forward asks: `on=(base tip, head)` is
  written as `expect` and onto every read; `first_on` puts the first read on older commits
  (GitHub's answer from before the merge or update); `synced` is a parameter (it was hardcoded
  True, and the reads had no commit ids).
- `_good()` (:134-152) gives every polled list realistic commits: the run base tip starts at
  main's commit (`START`, :49) and then is each merge commit; B's head after Update branch is
  `B_UPDATED` (:50). B's and Q's judged lists open with one stale read and end on two fresh ones,
  so the PASS case (1) also proves a fresh list is still accepted after a stale first read.
- (3) :216 and (6) :239 build their FAIL lists on the expected commits, so they stay FAILs (a
  complete observation that disagrees), not INCOMPLETE.
- `_expect` (:181-197) asserts the exact exit code: 0 PASS, 1 FAIL, 3 INCOMPLETE (it was
  "non-zero" for both FAIL and INCOMPLETE).
- New method under criterion (7),
  `test_a_file_list_not_seen_settled_on_the_expected_commits_is_incomplete` (:303-361): six
  shapes, each with E1 or E1b INCOMPLETE, every other check PASS, exit 3, and a reason that
  names the cause.

| Shape | Old judge gave | Rule it holds |
|---|---|---|
| B: reads agree on the expected commits, `synced: false` | E1 PASS | the flag |
| B: last read fresh (so `run` recorded `synced: true`), the read before it still on B's head from before Update branch | E1 PASS | both reads, not only the last (the carry-forward's parenthetical) |
| B: `expect.baseRefOid` empty (`run` could not read the tip) | E1 PASS | the expected commits must be recorded |
| Q: poll ran out of time, three identical reads on the base from before P merged, `synced: false` (F1 as described) | E1b FAIL | commits + flag |
| Q: reads agree on the expected commits, `synced: false` | E1b PASS | the flag, on E1b |
| Q: last two reads on the old base, `synced: true` (as a hand-edited file may say) | E1b PASS | the base commit of both reads, without help from the flag |

## Red → green

- **This iteration's red** (iteration 5's tool with the new test), through the target's runner
  `python3 -m tests.run_root_suite tests.test_stack_mode_live_tool`: "Ran 21 tests … FAILED
  (failures=6)", exactly the six new sub-cases, with the old results in the table above. The
  other 20 methods passed, so the fixture change alone breaks nothing.
- **Green** (with the fix): "Ran 21 tests … OK", "root suite OK: 21 executed, 0 skipped".
- **C4 gate**, the configured command (`./engine/scripts/run-verify.sh` with `PDCA_BUNDLE` /
  `PDCA_WORKTREE`, under `timeout 900`): green leg "Ran 21 tests … OK"; red leg (tool and doc
  hunks reverted) "Ran 21 tests … FAILED (failures=40)", no `_FailedTest`; final line
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Every test method failed on the
  red leg. Afterwards the four files were byte-identical to copies taken before the gate.
- **Mutation checks**: one rule of the new `settled_files` broken at a time, the module re-run,
  the file restored and compared byte for byte. Flag ignored → 2 red (both "not synced" shapes);
  commit check ignored → 3 red; only the last read checked → 2 red; an empty expectation counted
  as a match (the rule `run` uses) → 1 red; head not checked → 1 red; base not checked → 3 red.
  Every rule is held by at least one case.
- **Whole root suite** (`python3 -m tests.run_root_suite`, with copier, `timeout 2400`): "Ran 45
  tests … OK", "root suite OK: 45 executed, 0 skipped". `template/` is not touched, so the
  offline driver suite is unaffected.
- I also read the fixed judge's messages off real `judge` runs on these shapes (see the example
  under the fix). They name the read, the commit it showed and the commit expected.

## Refute-your-own-test answers

- **(a) Genuine red?** Yes, twice. Against iteration 5's tool (the bug itself) the six new
  sub-cases fail and nothing else does. With the production hunks reverted (the C4 red leg) all
  21 methods fail on their assertions; the test never imports the tool, so this is a test that
  ran and failed, not an import error. The six mutations show that each new rule is held by a
  case, not only the file's existence.
- **(b) Production path?** Yes. Every case runs `tools/live/stack_mode_live.py judge` as a
  subprocess, by path: the real `settled_files`, `judge`, `report_md` and `cmd_judge`. No copy
  of the rule is in the test. The judge cases use no stand-in at all; the only stand-in in the
  file is `gh`, for the guard / preflight / teardown cases, as the brief prescribes.
- **(c) Fixture includes the fault?** Yes. The new fixtures are the faulty observations
  themselves: a poll `run` recorded as not synced, a stale read before the last one, a missing
  base tip, a timed-out poll stuck on the old base, and a file that says synced while its reads
  are on the old base.

## Success criterion → test

| Criterion | Test |
|---|---|
| (1) all match → exit 0, all PASS | `test_observations_matching_every_check_pass` :200 |
| (2) A no headRefOid → E2 FAIL with the observed value | `test_a_merged_pr_reporting_no_head_oid_fails_e2` :207 |
| (3) B after Update branch lists a.txt → E1 FAIL | `test_b_still_listing_a_file_of_a_after_update_branch_fails_e1` :216 |
| (4) S head on base → E4 FAIL | `test_a_squash_merge_whose_head_is_on_the_base_fails_e4` :223 |
| (5) base is the line or main → E0 FAIL | `test_a_pr_against_the_line_or_main_fails_e0` :230 |
| (6) Q lists p.txt → E1b FAIL | `test_q_listing_a_file_of_p_after_p_merged_fails_e1b` :239 |
| (7) preconditions missing → INCOMPLETE, not FAIL | `test_missing_preconditions_are_incomplete_not_fail` :246 (7 shapes) and, new, `test_a_file_list_not_seen_settled_on_the_expected_commits_is_incomplete` :308 (6 shapes) |
| (7b) run 2 non-zero / raised after its preconditions → E3 FAIL with rc / exception / stderr tail | `test_run_2_failing_after_its_preconditions_were_observed_fails_e3` :363 |
| (8) sandbox token reaches gh, not the ambient one; exit 0 | `test_preflight_passes_the_sandbox_token_to_gh_and_writes_nothing` :489 |
| (9) `private: false` → non-zero | `test_preflight_refuses_a_repo_that_is_not_private` :509 |
| (10) `--repo eduralph/pdca-harness` → non-zero, gh never called | `test_preflight_refuses_the_harness_repo_without_calling_gh` :517 |
| (11) missing / empty token file → non-zero, gh never called | `test_preflight_refuses_a_missing_or_empty_token_file_without_calling_gh` :525 |
| (12) squash / merge commits off → non-zero, naming the setting | `test_preflight_refuses_a_repo_without_squash_or_merge_commits` :538 |
| (13) setup / run / teardown + harness repo → non-zero, no gh | `test_writing_steps_refuse_the_harness_repo_without_calling_gh` :555 |
| (14) setup / run / teardown + missing token → non-zero, no gh | `test_writing_steps_refuse_a_missing_token_file_without_calling_gh` :564 |
| (15) teardown deletes exactly the recorded base + branches, closes the PR; no heads/main, repo delete or settings PATCH | `test_teardown_removes_the_runs_branches_and_pr_and_nothing_else` :610 |

Extra cases, all from iteration 5: E3 takes either `_gone_branch` success line and never the
opening it shares with the refusals (:393; integrate.py:1434-1436, :1509-1511); teardown deletes
an unrecorded branch under the run's prefix and not another run's (:628); `--keep` makes no gh
call (:636); preflight's draft warning (:502).

## The rest of the patch (iteration 5, unchanged)

- Tool, `tools/live/stack_mode_live.py` (1472 lines, standard library only): `guard()` :115 (no
  network: repo name rule, `eduralph/pdca-harness` by name, missing / empty / multi-word token
  file); `use_token()` :139 (drops ambient `GH_TOKEN` / `GITHUB_TOKEN` / enterprise tokens /
  `GH_HOST` / `GH_REPO`, sets `GH_TOKEN` from the token file, `GIT_CONFIG_GLOBAL=/dev/null`
  :150); `preflight()` :170 (private, push, `full_name`, both merge settings; draft warning
  :206); `cmd_setup` :323 (writes `state.json` before creating the branch :342, prints the
  `teardown` command if it stops part-way :359-362); `_clone` :377 (credential helper
  `!gh auth git-credential` in the clone only, :383-385); `Live` :433; `_drive` :551 (patches
  only `flow._drive_wave` and `publish.draft_texts`, :567-569; calls `flow.flow_ids` :573; exit
  code from `cli._results_rc` :579, cli.py:707); merges, deletes and Update branch :617-707;
  `judge` :1055, `_e3` :1192, `cmd_judge` :1302; `cmd_teardown` :1329 (`--keep` :1352, never
  `main` or the default branch :1359, branches under the run's prefix :1369, closes open run PRs
  :1391, removes only `checkout`, `checkout.pdca-*` and `project` locally :1412).
- `CONTRIBUTING.md:39-90`, section "Checking stack mode on real GitHub"; `AGENTS.md:14-18`, the
  STOP-exception bullet.

Design decisions from iteration 5 that still hold: `flow.flow_ids` (flow.py:3370) rather than a
direct `flow._drive_and_act` (:2709) call, so finished ids stay in the batch for
`_finished_named` (:1270) and `_carry_finished` (:1425); teardown keeps `state.json`,
`observations.json` and the report so the report can still be attached; teardown does not
refuse on merge settings; `--keep` changes nothing; a wrong base on any PR is an E0 FAIL even when
other PRs are missing; later phases still run after an independent failure; no `#625` in sandbox
commit messages or PR bodies (GitHub would cross-link every run's PRs); the driver is imported
only from this checkout. Iteration 5's decision 5 (the commit match as a soft condition) is the
one this iteration replaces.

## For the human at sign-off

1. **Hard sign-off condition (brief): the live run.** Nothing here touched GitHub. Run once:

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
   a disposable repo.

2. **Draft PRs on the sandbox (the question the carry-forward leaves to you).** Publish opens
   every PR with `gh pr create --draft` (template/src/pdca_harness/publish.py:330). As far as I
   know, GitHub offers draft PRs in private repositories only on organization plans (Team,
   Enterprise), not in a personal account's private repository. If `eduralph/pdca-stack-sandbox`
   belongs to the personal account, the first publish of the live run is likely refused and the
   run ends INCOMPLETE. `preflight` warns about it (:206-210). To settle it before the run:
   `gh api repos/eduralph/pdca-stack-sandbox --jq .owner.type` with the sandbox token, or one
   throwaway `gh pr create --draft` on the sandbox. I did not write this as a
   "NEEDS-HUMAN external dependency" line this time: this iteration's fix was built and verified
   offline without it, the live run is already its own §6 item, and with `dependency_halt = true`
   in pdca-pdca's `pdca.toml` a confirmed marker would send the bundle to sign-off with no gates
   and no review of the fix.

3. **A live-run risk that comes with the stricter rule (E1b).** E1b now needs Q's PR to report
   `baseRefOid` equal to the run base tip after P merged, while Q's head never moves (no Update
   branch, by design). I could not find out offline whether GitHub moves a PR's `baseRefOid`
   when only its base branch moves. If it does so only on a push to the head, every read of Q
   after P's merge keeps the old base, `run` waits the full 180 s and records `synced: false`,
   and E1b is INCOMPLETE on every run, so re-running will not help. You will recognize it in the
   report: the E1b reason lists the reads showing `baseRefOid` = the run base tip from before P
   merged (C's merge commit in this scenario). That would be the chosen rule meeting a GitHub
   behaviour, not a driver bug; what to accept as proof that Q's list is fresh would then be a
   re-plan decision. Iteration 5 kept the commit match soft for this reason; the sign-off chose
   the strict rule, which is what this iteration builds. E1 is less exposed: Update branch
   pushes to B's head. The four recorded-not-judged polls may also wait the full window; that
   costs time only.

4. **Second §6 item (brief): the STOP-exception wording**, `AGENTS.md:14-18` and
   `CONTRIBUTING.md:87-90`, unchanged in this iteration, to review and accept on its own.

## Commit-readiness

The target configures no formatter, linter or commit hook: no `.pre-commit-config.yaml`,
`pyproject.toml`, `setup.cfg`, `tox.ini`, ruff or flake8 config at the root; no active hooks in
the common git dir and no `core.hooksPath`. Its CI runs docs-check (`lint_docs.py` and
`render_site.py --check`, which read only `docs/*.md` and `template/PCDA/quality-cycle/*.md`:
docs/publishing/tools/lint_docs.py:73-77, render_site.py:249) and render-check (two root suite
modules), so none of it reads the touched root files except through the root suite, which
passes. Checked anyway: `git diff --check` clean with the new files included; no added line over
100 characters; both Python files parse and have no unused imports; every file ends with a
newline. Patch: 120,532 bytes, 4 files, applies cleanly to a6af7f3 (checked against a6af7f3's
tree in a scratch index); the DCO `Signed-off-by` comes from publish's `git commit -s`. The
bundle's copy of the test (`results/issue_625/test_stack_mode_live_tool.py`) matches the patch.

Nothing was pushed and no PR was opened. Do did not run `setup`, `run` or `teardown`. The only
`gh` call was local: `gh pr view 1 -R example/example --json nosuchfield` with a dummy token,
which gh rejects while parsing flags; it showed that gh 2.103.2 has the `baseRefOid`,
`headRefOid` and `files` fields the tool reads. Scratch files are in the worktree's git-ignored
`.cache/issue625/` and are not part of the patch.
