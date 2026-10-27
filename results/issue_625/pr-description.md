## Summary
**User impact:** If you use stack mode and merge your PRs on GitHub, you are relying on
behaviour that had never been checked against real GitHub. Nobody had seen what a
dependent PR shows once the PRs it depends on are merged, or whether the driver still finds
an already-merged PR after its branch is deleted. If either assumption is wrong, the docs
mislead you about what a PR's "Files changed" tab will show, or a follow-up run stops on
work that was already merged.

This PR adds a small tool that runs the stack-mode scenario on a private sandbox repo,
checks what GitHub shows against what the code and docs expect, and writes a report. It
can be re-run whenever GitHub or the driver changes.

Reported in [#625](https://github.com/eduralph/pdca-harness/issues/625).

## What to look at
- **The tool**, `tools/live/stack_mode_live.py`, has five steps: `preflight` (checks the
  token and repo and changes nothing), `setup`, `run`, `judge` (reads the saved results
  offline and writes `report.md`) and `teardown`. It lives at the repo root, so it is not
  shipped to projects made from the template.
- **The safety rails.** It runs only against a repo that passes its guard (private, named
  as a sandbox, never `eduralph/pdca-harness`). It uses only the sandbox token and never
  your normal `gh` login. Each run works on its own fresh `live-<stamp>` base branch, and
  teardown never touches the sandbox's `main`, the repo itself, or its settings.
- **A policy change, to review separately.** `AGENTS.md` and `CONTRIBUTING.md` get one
  narrow exception to the "never merge, never mark ready" rule: it covers only the merges
  and ready-marks this tool makes itself, started by a human, on a repo that passes the
  guard. It does not cover any other merge on the sandbox.
- **How to run it:** see the new "Checking stack mode on real GitHub" section in
  `CONTRIBUTING.md`. The offline part runs with
  `python3 -m tests.run_root_suite tests.test_stack_mode_live_tool` and needs no network.
- **Departure from the issue's wording:** #625 asks for a throwaway repo. The sandbox token
  cannot create repos, so the tool uses a persistent private repo,
  `eduralph/pdca-stack-sandbox`, with a fresh base branch per run. Merged and closed PRs
  stay in that repo's history.

## Root cause
The stack-mode rework (#593, PR #619) and the fixes after it were tested with real `git`
against a local bare origin and a stand-in `gh`. No test or run recorded the PR file lists
or the `gh pr view` answers that real GitHub gives after a merge and a branch delete.

## Fix
New files and two short doc sections. No driver code changes.

- `run` drives the real `flow` code with fixed patches in place of the model steps, and
  with real `git` and `gh`. It opens PRs against the run base, merges some with merge
  commits and one with a squash, deletes branches, and records every answer GitHub gives
  in `observations.json`.
- `judge` turns those observations into seven named checks, each PASS, FAIL or
  INCOMPLETE. INCOMPLETE means something the check needs was never seen, such as a merge
  GitHub refused or a file list that never settled. FAIL means the observation was complete
  and disagreed with what was expected. Only a FAIL is a bug to file.
- A PR's file list is read until two reads in a row agree on the expected commits. It is
  never polled until it matches the expected value, because that would hide a real FAIL.
  GitHub does not refresh a PR's base commit or file list when only the base branch moves,
  so for those reads the tool waits for GitHub's test merge of the PR to be rebuilt on the
  new base tip. It also records the compare view (`base...head`) next to the PR's own list.

## Verification
- **Claim:** `judge` gives the right verdict for each check and tells a real mismatch
  (FAIL) apart from missing evidence (INCOMPLETE).
  - **Checked:** `tools/live/stack_mode_live.py:1052` (`read_off`, the one settle rule
    shared by `run` and `judge`), `:1086` (`settled_files`), `:1175` (`judge`), `:1445`
    (exit code: 0 PASS, 1 FAIL, 3 INCOMPLETE).
  - **Test:** `tests/test_stack_mode_live_tool.py:220-504`. All checks pass (`:220`). Each
    check fails on its own fault (`:241`, `:250`, `:257`, `:264`, `:276`). Missing or stale
    evidence gives INCOMPLETE, not FAIL, in 18 shapes (`:289`, `:355`). A follow-up run
    that exits non-zero once its preconditions were seen gives FAIL (`:474`).
- **Claim:** nothing writes to any repo except the guarded sandbox, and only with the
  sandbox token.
  - **Checked:** `tools/live/stack_mode_live.py:90` (refused repos), `:134` (`guard`),
    `:189` (`preflight`: private, pushable, merge commits and squash merges both allowed).
  - **Test:** `:600` (the sandbox token reaches `gh` even when another `GH_TOKEN` is set),
    `:620`, `:628`, `:636`, `:649`, `:666`, `:675` (each refusal, and `gh` is never called
    for a refused repo or a missing token).
- **Claim:** teardown removes only the run's own branches and PRs.
  - **Test:** `:721` (deletes exactly the recorded branches and closes the recorded PR; no
    `heads/main`, no `repo delete`, no settings change), `:739`, `:747` (`--keep`).
- **Red → green:** the test runs the tool by path as a subprocess and never imports it.
  With the tool and doc changes reverted, all 22 test methods fail (46 failures, no import
  errors). With them applied, all 22 pass. The root suite (46 tests), the offline driver
  suite (2630 tests, 2 skipped) and the docs lint and site link check are all green.
- **Live run** (2026-10-26, sandbox run base `live-20261026-141700`): E0, E1, E2, E3, E4
  and E5 PASS. E1b FAIL: in a plain two-PR chain, after the first PR merged, real GitHub
  still listed its file on the second PR until that PR was pushed to or updated, while the
  compare view showed only the second PR's own file. That contradicts the plain-chain claim
  in `docs/07-crosscutting.md:646-664`. It will be filed as its own docs bug. The tool
  reported it correctly, so it is not a tool defect.
- **Known limit:** an observed but empty PR file list counts as INCOMPLETE rather than
  FAIL (`tools/live/stack_mode_live.py:1062`). No PR in this scenario can have an empty
  diff, so no check here is affected. A follow-up will treat it as a mismatch.

Fixes #625
