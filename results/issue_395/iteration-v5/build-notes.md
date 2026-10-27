# Build notes — issue 395, iteration 5 (same-wave conflict caught before publish)

Target: `eduralph/pdca-harness @ main`, base `a6af7f3` (= `origin/main` when built).
Line numbers are in the patched tree (base + `patch.diff`) unless marked otherwise.
Partial fix: the PR should say `refs #395`, not `closes` (see §8).

I started from the iteration-4 patch (`iteration-v4/patch.diff`). The round-4 sign-off said
the trial itself is sound and asked for two fixes in the new "held, no PR" state, each with
a test. Those two fixes are the only behaviour change this round. I left alone what that
sign-off left undecided: the fail-closed fallback when the trial cannot run, and the docs
claim for the sibling-plus-line case.

## 1. A held bundle with a PR from an earlier publish: that PR is named, never "no PR"

**The defect.** `publish.json` outlives an iterate (`state.DOWNSTREAM_OF_BRIEF`,
`template/src/pdca_harness/state.py:126-161`, does not list it). So a bundle published
once, then iterated and rebuilt, still has its old PR on record. If the trial then holds
the rebuilt bundle, nothing is pushed onto that PR, which keeps showing the old work. But
iteration 4's lines said "no branch pushed, no PR opened", "opened no PR for it", and the
carry said "so it has no PR". The open PR was hidden.

**The fix.** One helper, `_earlier_pr` (`template/src/pdca_harness/flow.py:1380`), reads
the bundle's `publish.json` and returns a clause naming the PR, or "" when none is
recorded. Every line that says a run did not publish the bundle uses it:

- the trial's hold line, `_announce_conflict_holds` (`flow.py:1714`, clause at `:1729-1733`);
- the end-of-run line, `_report_conflict_holds` (`flow.py:1790`, clause at `:1811-1815`);
- the carry's reason, `_held_before` (`flow.py:1405`, clause at `:1423`), which the
  re-issue's carry (`flow.py:1578`) and the new re-run hint (§2) both use;
- the "could not be tried" line, `_announce_untried` (`flow.py:1769`, clause at `:1787`).
  The sign-off did not name this one. It is a line this change added, and it hid an
  earlier PR the same way, so I gave it the same clause.

The clause depends on what kind of record it is:

| record | text |
|---|---|
| own PR, same branch as now | "its PR on record, URL, still shows what an earlier publish of it pushed (close it if it is open, or leave it until issue_N is published again)" |
| own PR, branch renamed since | "… (close it if it is open: publishing issue_N again opens a new PR)" |
| own PR, the line's step is to publish it | the fact only: publishing it updates that PR |
| `Onto branch` (mode `stacked`) | "the PR it commits onto, URL, still has the commit an earlier publish of it pushed" (no advice) |

Why each branch exists:

- **Renamed branch** (`flow.py:1398`). The branch name comes from the brief's slug and
  Kind (`publish._branch_name`, `template/src/pdca_harness/publish.py:621-629`). An
  iterate-plan can change both. Then publish pushes a different branch and opens a new PR,
  so "leave it until published again" would leave the old PR open forever. I compare the
  recorded branch with the one publish would push now.
- **`publishing`** (`flow.py:1400`). Where the line's own step is to publish the bundle
  (the carry's "open" verdict once every partner's PR closed, `flow.py:1423` with
  `publishing=not standing`; the untried line, `flow.py:1779-1780`), "close it" would
  contradict the step. On the same branch, publishing updates that PR, so only the fact is
  given.
- **`Onto branch`** (`flow.py:1394`). There `pr_url` is someone else's PR that the bundle
  commits onto (`publish._publish_stacked`, `publish.py:554-562`). Telling the human to
  close it would be wrong.

**Alternative I ruled out, with the cost.** Reading the PR's state (`merged.pr_state`) to
say "open" or "closed" for sure. That is one `gh pr view` per held bundle with a record,
per line: two in the run that holds it (the hold line and the end line), one more for each
later carry or re-run. It also adds a failure path (state unreadable) to lines that today
read only local files. The plain "close it if it is open" needs neither, and stays true in
every state.

## 2. A re-run that finds a held bundle finished gives the hold's step and exits 3

**The defect.** `pdca flow 10 11 12 20` again after run 1 held 11: every id is COMPLETE,
so `flow_ids` skips each (`flow.py:3670`). The skip's hint, `_terminal_hint`, knew nothing
about the hold. It printed "already complete — nothing to run. To redo it: rm -rf
…/issue_11", and the run exited 0. Following that advice deletes accepted work that has no
PR. Iteration 4's hold step only ran in the carry, which runs only when a driven bundle
depends on the held one.

**The fix.**

- `_terminal_hint` (`flow.py:1848`) now takes `cfg` and returns `(hint, hold)`. For a
  COMPLETE bundle whose conflict hold is on record (`publish.read_conflict_hold`,
  `flow.py:1895`), the hint is what the carry gives it, from the same `_held_before`
  (`flow.py:1897-1902`): the partners, the files, and the step for the partners that may
  still land. Once every partner's PR is closed unmerged, it is the step to publish it.
  It never prints `rm -rf` for such a bundle. Every other bundle gets the same hint as
  before. The function is still the one place the skip's advice comes from, for both CLI
  shapes (#468).
- `flow_ids` records the hold in the run's `holds` collector (`flow.py:3672-3677`), so the
  re-run exits 3 (`cli._results_rc`, `template/src/pdca_harness/cli.py:708`), as the run
  that held it did. The kind is `"conflict"` while the hold stands, and `"unpushed"` once
  it no longer does: then the bundle is simply accepted work that pushed no branch. Both
  exit 3. A run that also leaves a driven bundle unbuilt still exits 1, which wins.

Output of the new case (`test_a_rerun_after_a_trial_hold_gives_the_holds_step_and_exits_3`):

> flow: issue_11 — already terminal (COMPLETE), skipped
>   An earlier run held it before publishing it, as its change conflicts with issue_10's,
>   of its own wave (shared.txt), so it has no PR. Proposed, for you to confirm: declare
>   `Conflicts with: 10` in issue_11's brief, then rebuild issue_11 on a base that holds
>   issue_10, then re-issue.

**Why exit 3, not 0.** The sign-off said to consider a non-zero exit. Exit 0 tells a script
the batch is clean while one bundle's work has no PR. Exit 3 already means "every bundle
finished, but one is held" (`cli.py:721-733`). The hold is a fact on disk, so I record it
in every mode, a dry-run included.

**Alternatives I ruled out.**

- *Check the hold in `flow_ids` before calling `_terminal_hint`.* The same few lines, but
  the skip's advice would then come from two places, which is how the CLI shapes drifted
  apart before (#468). I kept it in `_terminal_hint`.
- *Record `"conflict"` for both verdicts.* Once every partner's PR is closed unmerged, the
  carry already says the hold "no longer stands" (`flow.py:1432`). Calling it a conflict
  hold in `holds` would contradict that. `"unpushed"` matches what the bundle is.

**Not covered: `pdca flow --from-csv` (`flow_batch`).** Its sweep leaves out every
COMPLETE bundle silently (`flow.py:3499-3508`), with no hint and no `rm -rf`. So it gives
no wrong advice, but it does not name the held bundle either, and it exits 0 when nothing
else is in flight. Changing that means scanning every finished bundle on every sweep. That
is a change of its own, and the sign-off asked only about the id route.

## 3. Docs and comments

- `docs/07-crosscutting.md:728-730`: a held bundle with a PR from an earlier publish is
  named with that PR, which still shows the earlier work.
- `docs/07-crosscutting.md:743-750`: "a later run that finds such a held bundle finished
  (a re-run of the same ids, or a re-issue for a bundle that depends on it)", never asks
  you to delete the bundle, and a re-run in which every bundle is finished exits 3. This
  fixes the round-4 adversary's point that the old line (then `:741`) was true only for a
  re-issue with a dependent.
- `docs/07-crosscutting.md:769-772`, the exit-code paragraph: a bundle held before it was
  published keeps a later re-run from exiting 0.
- `cli.py:638-642` and `cli.py:721-733`: the `holds` collector comment and the
  `_results_rc` docstring now list the pre-publish hold, in this run or a standing one
  from an earlier run. Docstring only; `cli.py` has no code change.
- `state.py:62-70` (the `CONFLICT_HOLD` comment), the `flow_ids` docstring
  (`flow.py:3624-3628`), and the two trial-block comments (`flow.py:3231-3236`,
  `:3250-3251`) now say "a later run" (carry or re-run), not just "a re-issue's carry".

## 4. Tests — `template/tests/test_flow_same_wave_prepublish.py`, now 30 cases

Real git (`StackFoldGit`, bare `origin`), real `publish.publish`, `gh` stubbed. The
re-run cases go through `cli._flow` (new helper `_cli`, `:183`), so the skip, the hint and
the exit code are the CLI's own. The iterate is the production
`driver._archive_iteration`. The stubs of `_run` moved into a shared `_stubbed` context
(`:132`), with no change in what they stub. The file still imports modules only.

"main" is the C4 red leg (every production hunk reverted). "iteration 4" is this file run
against iteration-4 production code: a scratch copy built from `git archive HEAD` plus
`iteration-v4/patch.diff`.

| case (line) | what | main | iteration 4 | now |
|---|---|---|---|---|
| `…rerun_after_a_trial_hold_gives_the_holds_step_and_exits_3` (:856) | re-run, several ids and one; hint, exit 3; clean again once published | FAIL | FAIL | pass |
| `…rerun_once_the_partners_pr_closed_asks_to_publish…` (:893) | re-run, hold no longer stands: publish step, exit 3 | FAIL | FAIL | pass |
| `…held_bundle_whose_earlier_publish_opened_a_pr_names_that_pr` (:934) | earlier PR named on the hold line, the end line, the re-run hint and the carry | FAIL | FAIL | pass |
| `…bundle_the_trial_could_not_try_names_its_earlier_pr` (:969) | earlier PR on the untried line | FAIL | FAIL | pass |
| `…branch_was_renamed_is_not_told_its_pr_will_update` (:988) | renamed branch: "opens a new PR" | FAIL | FAIL | pass |
| `…partners_pr_closed_is_asked_to_publish_onto_its_pr` (:1010) | earlier PR, publish step: no "close it" | FAIL | FAIL | pass |
| `…onto_a_branch_names_the_pr_it_commits_onto` (:1033) | `Onto branch` record: no "close it" | FAIL | FAIL | pass |

The 23 cases from iteration 4 are unchanged: 18 fail on main, 5 pass there (b, c, d, f
twice), all pass on iteration 4 and now. Against iteration-4 production code the file
gives `Ran 30 … FAILED (failures=7)`, exactly the seven rows above.

## 5. Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner
  (`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`, from the instance root)
  reverted every production hunk and re-ran all seven touched test files. New file:
  `Ran 30 … FAILED (failures=25)`, all `FAIL` (assertions), no `_FailedTest` load failure.
  The 5 that pass are the guard cases above. `test_flow_same_wave_conflict`: 3 failures.
  The re-issue file: 24 `AttributeError` errors from its unguarded `_held_before_publish`
  mock (kept on purpose since round 1). The other four files pass on the reverted tree, as
  on main. With the fix, all seven pass. Final line: `PDCA-EVIDENCE: C4 PASS — red without
  the fix, green with it`. The red that matters for this round is the iteration-4 column:
  the 7 new cases fail there, and only they. Their failure messages show the two bugs: the
  hold line ends "no PR opened." with no PR named, and the re-run exits 0 with
  `rm -rf …/issue_11`.
  Single-piece mutations of this round's code (`.pdca-scratch/mutate5.py`, each in a
  scratch copy of `template/`). Every one is caught:
  - hint without the hold: 3 failures; hint back to `rm -rf`: 4; hold kind always
    `"conflict"`: 2; `flow_ids` never records the hold: 3;
  - `_earlier_pr` always "": 5; ignores a renamed branch: 1; ignores `Onto branch`: 1;
    ignores `publishing`: 2;
  - the carry, the hold line, the end line or the untried line without the clause: 2, 3,
    1 and 1.
- **(b) Production path? Yes.** `_terminal_hint`, `flow_ids`, `_held_before`,
  `_earlier_pr`, the announce and report lines, the carry and `cli._flow` /
  `_results_rc` all run unpatched. `flow.flow_ids` is wrapped only to read the `holds`
  dict `cli._flow` hands it; the real function runs. Publish is the real `publish.publish`
  pushing to bare repositories (origin, and the fork for the `Onto branch` case). The
  stubs are the build and sign-off leaves, drafting / T4, the `gh` binary, and, in the
  untried case, the trial's own `git commit` (`integrate._git` returning 1). Outcomes are
  read from the bare repositories' refs, the recorded `gh` argv, stderr and the exit code.
- **(c) Fixture includes the fault? Yes.** The earlier PR is a real earlier publish:
  run 1 pushes v1 and records its PR, then the production iterate archives the attempt and
  leaves `publish.json`. The `Onto branch` record is a real `_publish_stacked` onto a
  second bare repository. The renamed branch is a real slug change in the brief. The
  re-run is a real `cli._flow` over finished bundles with a hold on disk. A closed
  partner is the `gh` state the carry and the hint read in production.

## 6. Other evidence (final tree, `patch.diff` sha256 `700381e5…e691ea`)

- T3 (`./engine/scripts/run-suite.sh`): root render/update-compat suite `Ran 24 … OK`;
  driver suite `Ran 2660 … OK (skipped=2)` (2653 last round plus the 7 new cases).
  `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- T2 (`./engine/scripts/run-docs-check.sh`): `docs lint clean, site render + link audit
  clean` (22 pages). `run-host-ci.sh` runs the same two checks.
- C5 prod-path (`run-prod-path.py`): "1 added driver-suite test(s) import the production
  package 'pdca_harness'".
- `git apply --cached --check patch.diff` on `a6af7f3` (a temporary index, so the worktree
  was not touched): clean. After the C4 and T3 runs the worktree diff still equals
  `patch.diff` byte for byte. `git diff --check`: clean.

## 7. Commit-readiness

Checked again this round: the target has no formatter, linter, pre-commit config or active
git hooks (no `.pre-commit-config.yaml`, no ruff / flake8 / black config, no
`core.hooksPath`, only `*.sample` hooks). Its workflows are docs-check, docs, render-check
and issue-triage ones; T2 and T3 cover the first three. Its rules (`AGENTS.md`,
`CONTRIBUTING.md`) are DCO sign-off and a conventional subject, which publish handles.
Every added line is at most 96 characters wide. All touched Python files byte-compile.

## 8. For the human at sign-off

- **Refs vs Closes** (unchanged since iteration 2). The brief wants `refs #395`. The
  target's required check (`.github/workflows/require-linked-issue.yml`) passes only with
  a closing keyword or an issue linked in the PR's Development sidebar, and this
  instance's `[tracker].issue_trailer` is `Fixes #{id}`. Decide before publish.
- **New behaviour this round.**
  - A re-run (`pdca flow <ids>`) that skips a held bundle as finished gives its hold's
    step instead of `rm -rf`, and exits 3 while that hold is on record. Once the bundle is
    published (by hand or by a later run), the re-run is clean again (exit 0). If you
    would rather keep exit 0 there and only fix the hint, drop `flow.py:3676-3677`; the
    two re-run cases would then have to assert 0.
  - Each line that says a run did not publish a bundle names the PR an earlier publish of
    it recorded. This includes the untried line, which the sign-off did not name.
  - `cli.py` has docstring and comment changes only.
- **Still deferred to you** (not build work; see `deferred-findings.json`): the
  whole-target fallback's blast radius; criterion (e) holding more than `main` when the
  partner's push fails for a reason the trial cannot see; the last wave; and a bundle that
  conflicts with a sibling and with the line at once.

## 9. Known limits

- `pdca flow --from-csv` does not name a held bundle (§2).
- A re-issue prints the hold's step twice: once on the skip line, once on the carry line.
  They are different stages of the run, and the old skip line printed `rm -rf` there.
- The earlier-PR clause does not ask the host whether that PR is still open (§1).
- The pre-existing "pushed no branch this run" line (texts failed T4, or a failed push)
  can also leave an earlier PR showing old work. That line predates #395 and does not say
  "no PR", so I left it.
- From iteration 4, unchanged: the trial starts from the tip this run last pushed, and the
  fold keeps the last word; the trial does not apply the fold's #623/#673/#747/#748
  checks; `_would_be` repeats publish's steps, and drift fails closed; `Conflicts with:
  464` edits the same publish/fold block, so expect a textual conflict there.

## Scratch

`.pdca-scratch/` in the worktree holds the C4 and T3 logs, the iteration-4 production copy
used for the "iteration 4" column, the mutation script and its copies, and the temporary
git index files used to build and check `patch.diff`. It is untracked and not in
`patch.diff`. One command used `rm -f` on a temporary index path there before creating it;
the file did not exist, so it removed nothing.

No external dependency was missing. No NEEDS-HUMAN external-dependency item.
