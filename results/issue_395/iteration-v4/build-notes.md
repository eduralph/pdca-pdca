# Build notes — issue 395, iteration 4 (same-wave conflict caught before publish)

Target: `eduralph/pdca-harness @ main`, base `a6af7f3` (= `origin/main` when built).
Line numbers are in the patched tree (base + `patch.diff`) unless marked otherwise.
Partial fix: the PR should say `refs #395`, not `closes` (see §9).

I started from the iteration-3 patch (`iteration-v3/patch.diff`). The round-3 reviewers
found its main path sound, so I changed only the three parts the round-3 carry-forward
asked for. Everything else from iteration 3 is kept as it was.

## 1. C5 — once some partners' PRs close, the step names only the others

**The defect.** Take a bundle held for two partners (13, held for 10 and 12). After
10's PR closed without merging, the re-issue kept the hold (correct) but still advised
"declare `Conflicts with: 10, 12` … rebuild issue_13 on a base that holds issue_10,
issue_12". No base will ever hold 10, so nobody could follow that step
(review-mixed-closed.log).

**The fix.** `_held_before` (`template/src/pdca_harness/flow.py:1380`) now also returns
the partners still standing: every partner except those whose PR reads CLOSED
(`flow.py:1393-1394`). The carry passes only those to the step (`flow.py:1549-1551`,
`:1580`). When the hold stands is unchanged from round 3: it stands while any partner may
still land. Only the step and the reason text change. The output from the test below:

> an earlier run held it before publishing it, as its change conflicts with issue_10's,
> issue_12's, of its own wave (shared.txt); issue_10's PR is closed unmerged now, but
> issue_12's may still land, so it has no PR — holding issue_20 this run; proposed, for
> you to confirm: declare `Conflicts with: 12` in issue_13's brief, then rebuild issue_13
> on a base that holds issue_12, then re-issue.

The reason still names 10, because it explains why the bundle was held. Only the step
drops it.

**Test.** I rewrote `test_a_reissue_keeps_the_hold_while_one_of_its_partners_may_land`
(`template/tests/test_flow_same_wave_prepublish.py:692`) to follow the reviewer's probe:
10's PR closed, the old integration line deleted (the step the carry gives for a line that
holds a closed PR's work), 12's PR still open. It asserts that the step names 12 only,
that "Conflicts with: 10", "holds issue_10" and "pdca publish 13" do not appear, and that
the carry puts 12 on the line. On iteration-3 code it fails with the exact advice the
reviewer quoted.

## 2. Adversary — one bundle's `Onto branch` remote no longer fails the whole trial

**The defect.** Iteration 3 fetched every member's remote in one `_prepare_worktree` call
(iteration-3 tree, `integrate.py:859-860`). If one bundle had an `Onto branch` (#54) on a
remote that could not be fetched (`nosuch/pr-12`), that fetch failed and the whole
target failed closed: only the first bundle was published, the rest were held as
unpushed, and their dependents were never built.

**The fix.** `_same_wave_trial` now fetches only `origin` and the base remote for the
whole target (`template/src/pdca_harness/integrate.py:864`). Those are the remotes every
cut point and the line live on. A remote that belongs to one bundle (an `Onto branch`
remote that is neither of those) is fetched by `_would_be` as the first step of building
that bundle's commit (`integrate.py:877-879`, `:929`). That matches publish, whose
`_publish_stacked` fetches the same remote as its first step (`publish.py:492`). If that
fetch fails, it counts as an `_Unbuilt` for that one bundle, which the round-3 path
already handles: one retry, then the bundle is held as unpushed (named with "could not
fetch nosuch"), and its siblings are tried without it. The fold already worked this way:
it fetches only the remotes of branches that were pushed (`integrate.py:602`).

**Alternatives I ruled out, with the cost.**

- *Keep one batched fetch, but map a failed remote back to the bundles that use it.*
  `_fetch` (`integrate.py:2432`) is shared with the fold and the carry. It raises on the
  first failure and does not report which remote failed. This option needs a new return
  shape for `_fetch`, or a loop of one-remote `_fetch` calls plus a remote → bundles map:
  about 12-15 lines, against about 6 here. It also would not match publish, which fetches
  the `Onto branch` remote itself.
- *Do not fetch a bundle's own remote at all.* About 2 lines. The trial would then build
  on whatever remote-tracking ref the checkout last had, or on none if it never fetched
  that remote, so the trial commit could differ from what publish pushes. The mutation
  run in §6 shows the cost: without the per-bundle fetch,
  `test_a_bundle_onto_a_branch_of_another_remote_is_tried_there_and_held` fails (12 is
  held as unpushed instead of for its real conflict with 10).

**Tests.** All three use real git. The bad remote is a real `git fetch` of a remote the
checkout does not have.

- `test_a_bundle_whose_own_remote_cannot_be_fetched_is_held_alone` (`:574`): the
  reviewer's probe. 10 and 11 publish, 20 is built, and 12 is held as unpushed with
  "could not fetch nosuch". Publish never runs for 12: its own refusal ("has no 'nosuch'
  remote") is absent from stderr. On iteration 3, 11 is held as well and 20 is never
  built.
- `test_a_first_bundle_whose_own_remote_cannot_be_fetched_still_lets_the_rest_be_tried`
  (`:602`): the bad bundle sorts first (09), and 10/11 really conflict. 09 is held alone,
  10 publishes, and 11 is still held for its conflict with 10. On iteration 3, only 09 is
  published (and publish then refuses it), so nothing reaches origin.
- `test_a_bundle_onto_a_branch_of_another_remote_is_tried_there_and_held` (`:543`): the
  working path. The round-3 code review noted the `Onto branch` path of the trial had no
  test. A second bare repository is the checkout's `fork` remote, with an open PR branch
  `pr-12` the checkout has never fetched. 12 (`Onto branch: fork/pr-12`) changes the line
  10 changes. The trial fetches `fork`, builds 12's commit on `pr-12`, and holds it for
  10, and `pr-12` on the fork is unchanged. On `main`, publish pushes 12's commit onto
  `pr-12` before the fold holds it. For this the test's `gh` stub now answers `gh pr list`
  (the lookup `_publish_stacked` makes, `publish.py:522`, owner `ONTO_OWNER`, `:68`), so
  on the red leg publish really pushes there instead of crashing in the stub.

## 3. Code review — a later run that gets to the held bundle's publish replaces its record

**The defect.** The flow wrote `conflict-hold.json` when the trial held a bundle, and only
a push removed it (`publish.py:446`, `:563`). Say a later run drove that bundle again and
neither held it nor published it (its texts failed T4, it could not be tried, or its push
failed). Then run 1's record stayed, and the next re-issue gave run 1's partners and step.

**The fix.** In each wave's publish step, the record of every bundle in `to_publish` that
the trial did not hold is cleared (`flow.py:3185-3194`); a held bundle's record is written,
as before. So the record always says what the last run that got to publishing the bundle
decided. A dry run (stub publisher) clears nothing, because it pushes nothing and decides
nothing.

**Why clear, rather than keep the record when no later trial judged the bundle.** I
considered keeping the record when run 2 could not judge the bundle (texts failed T4, or
it could not be tried), since nothing new was learned about its conflict. I chose to
clear, as the reviewer asked, for two reasons:

- In each of those cases, run 2's own message already tells the human to publish the
  bundle: "fix and run `pdca publish 11`" (`flow.py:3210`), or "check that its change
  merges with … and publish it" (`_announce_untried`, `flow.py:1735`). Keeping the record
  would make the next re-issue contradict the run just before it.
- The case the round-1 finding was about is not affected: a plain re-issue right after the
  trial hold. A finished bundle is never in a later run's `to_publish`, because both entry
  points skip finished bundles (`flow_ids`, `flow.py:3603`; `flow_batch`, `flow.py:3441`).
  So its record is never cleared, and the carry still gives the conflict step
  (`test_a_reissue_after_a_trial_hold_names_the_partner_and_opens_no_pr`, `:632`, still
  passes). An iterate archives the record anyway (`state.py:159`). In practice, the
  cleared case needs a sign-off cleared by hand and given again.

**Tests.** Each case drives 11 again in run 2 after deleting its `SUMMARY.md`, i.e. its
sign-off cleared by hand (`_redrive_11`, `:752`). That is the only way a held attempt
reaches a later publish step without an iterate.

- `test_a_later_run_whose_texts_fail_t4_drops_the_hold` (`:758`): 11's texts fail T4 in
  run 2. Run 3 gives the plain "no PR with a pushed branch on record … `pdca publish 11`"
  line, not run 1's hold.
- `test_a_later_run_whose_push_fails_drops_the_hold` (`:780`): run 2 publishes 11 (alone
  in its wave, held for nothing) and origin refuses the push. Run 3 does not bring run
  1's hold back.
- `test_a_dry_run_keeps_the_hold` (`:799`): a stub-publisher run 2 leaves the record, so
  run 3 still gives the conflict step. It passes on iteration 3 too (which never cleared);
  it pins the dry-run guard.

## 4. Docs and comments

`docs/07-crosscutting.md:731-746` now:

- lists "the remote of its `Onto branch` cannot be fetched" among the reasons a single
  bundle is held alone;
- says the whole-target fallback happens when "a fetch of `origin` or the base remote, or
  another git step there, fails";
- says the re-issue step names only partners whose PR is not closed;
- adds "A later run that drives the held bundle again and does not hold it drops that
  hold."

The test module's docstring, the `write_conflict_hold` / `clear_conflict_hold` docstrings
(`publish.py:707`, `:732`) and the `CONFLICT_HOLD` comment (`state.py:62-69`) say the
same.

## 5. The new test — `template/tests/test_flow_same_wave_prepublish.py`, 23 cases

Real git (`StackFoldGit`, bare `origin`), real `publish.publish`, `gh` stubbed, driven
through `flow._drive_and_act`. It imports modules only. "main" is the C4 red leg
(production hunks reverted). "iteration 3" is this file run against iteration-3 production
code (a scratch copy built from `git archive HEAD` plus `iteration-v3/patch.diff`).

| case (line) | what | main | iteration 3 | now |
|---|---|---|---|---|
| `…is_held_before_it_is_published` (:275) | (a) | FAIL | pass | pass |
| `…in_a_later_wave_is_held…` (:303) | (a), bases of their own | FAIL | pass | pass |
| `…shared_file_on_different_lines…` (:333) | (b) | pass | pass | pass |
| `…conflict_with_work_on_the_line…` (:347) | (c) | pass | pass | pass |
| `…partner_whose_texts_failed_t4…` (:373) | (d) | pass | pass | pass |
| `…hold_stands_when_the_partners_push_fails` (:386) | (e) | FAIL | pass | pass |
| `…in_the_last_wave…` (:405), `…one_wave_run…` (:420) | (f) | pass | pass | pass |
| `…fetch_fails_once…` (:434) | retry | FAIL | pass | pass |
| `…cannot_run_publishes_only_the_first…` (:457) | whole-target fallback | FAIL | pass | pass |
| `…staging_fails_once…` (:486) | retry of one commit | FAIL | pass | pass |
| `…trial_commit_cannot_be_built…` (:511) | one commit never built | FAIL | pass | pass |
| **`…onto_a_branch_of_another_remote…` (:543)** | **`Onto branch`, fetched** | FAIL | pass | pass |
| **`…own_remote_cannot_be_fetched_is_held_alone` (:574)** | **bad remote, last** | FAIL | **FAIL** | pass |
| **`…first_bundle_whose_own_remote…` (:602)** | **bad remote, first** | FAIL | **FAIL** | pass |
| `…reissue_after_a_trial_hold…` (:632) | re-issue, partner open | FAIL | pass | pass |
| `…published_by_hand…` (:653) | record cleared on push | FAIL | pass | pass |
| `…reissue_once_the_partners_pr_closed…` (:670) | every partner closed | FAIL | pass | pass |
| **`…keeps_the_hold_while_one_of_its_partners_may_land` (:692)** | **some partners closed** | FAIL | **FAIL** | pass |
| `…while_the_partner_has_no_pr…` (:731) | partner unpushed (e) | FAIL | pass | pass |
| **`…later_run_whose_texts_fail_t4…` (:758)** | **record replaced** | FAIL | **FAIL** | pass |
| **`…later_run_whose_push_fails…` (:780)** | **record replaced** | FAIL | **FAIL** | pass |
| **`…dry_run_keeps_the_hold` (:799)** | **dry-run guard** | FAIL | pass | pass |

Bold rows are new or rewritten this round. On iteration 3 the file has exactly 5
failures, one group per finding: `Ran 23 … FAILED (failures=5)`.

## 6. Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner
  (`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`, from the instance root)
  reverted the production hunks and re-ran all seven touched test files. New file:
  `Ran 23 … FAILED (failures=18)`. All 18 are assertion failures (`FAIL`, not `ERROR`),
  and there is no `_FailedTest` load failure. The 5 that pass are the guards (b), (c),
  (d) and both (f) cases, as they should on `main`. `test_flow_same_wave_conflict`: 3
  failures. The re-issue file: 24 `AttributeError` errors from its unguarded
  `_held_before_publish` mock (kept on purpose, per round 1's review). The other four
  files pass on the reverted tree, as on `main`. With the fix, all seven pass. Final
  line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Against iteration-3
  production code the file fails exactly the 5 bold-FAIL rows above, which reproduces the
  three findings.
  Single-piece mutations (`.pdca-scratch/mutate.py`, each in a scratch copy of
  `template/`), each caught by at least one case:
  - fetch every remote for the whole target again: 2 failures;
  - never fetch a bundle's own remote: 3 failures, including the working-remote case;
  - the step names every partner again: 1;
  - never clear the record: 2;
  - clear in a dry run too: 1;
  - clear only ready bundles: 1;
  - clear only bundles that were not ready: 1.
- **(b) Production path? Yes.** The trial, the per-bundle fetch, `_would_be`, the retry,
  the untried and hold bookkeeping, writing and clearing the record, and the carry's
  `_held_before` all run unpatched inside `flow._drive_and_act`. Publish is the real
  `publish.publish` pushing to bare repositories (origin, and the fork for the `Onto
  branch` case). The stubs are the build and sign-off leaves, drafting / T4 (`draft_texts`
  returning False is how a case fails T4), the `gh` binary, and, in some older cases,
  injected failures of `integrate._fetch` / selected `integrate._git` calls. Outcomes are
  read from the bare repositories' refs and the recorded `gh` argv.
- **(c) Fixture includes the fault? Yes.** The bad remote is a real failing `git fetch`.
  The `Onto branch` remote is a real second bare repository with a real PR branch. The
  closed partner is the `gh` state that publish and the carry read in production. The
  refused push is a real `pre-receive` hook. The pairs really conflict (one line of
  `shared.txt` changed two ways; two lines for the two-partner case).

## 7. Other evidence (final tree, `patch.diff` sha256 `d16ad525…44dbc`)

- T3 (`./engine/scripts/run-suite.sh`): root render/update-compat suite `Ran 24 … OK`;
  driver suite `Ran 2653 … OK (skipped=2)` (2630 on the base, plus the 23 new cases).
  `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- T2 (`./engine/scripts/run-docs-check.sh`): `docs lint clean, site render + link audit
  clean` (22 pages).
- C5 prod-path (`run-prod-path.py`): "1 added driver-suite test(s) import the production
  package 'pdca_harness'".
- `git apply --cached --check patch.diff` on `a6af7f3` (a temporary index, so the
  worktree was not touched): clean. The worktree diff equals `patch.diff` byte for byte
  after the C4 and T3 runs. `git diff --check`: clean.

## 8. Commit-readiness

The target has no formatter, linter, pre-commit config or active git hooks (no
`.pre-commit-config.yaml`, no ruff / flake8 / black config, no `core.hooksPath`, only
`*.sample` files in `.git/hooks`). Its rules (`AGENTS.md`, `CONTRIBUTING.md`) are DCO
sign-off and a conventional subject, which publish handles. Every added line is at most
96 characters wide (the touched files already have lines up to 106). All touched Python
files byte-compile.

## 9. For the human at sign-off

- **Refs vs Closes** (unchanged since iteration 2). The brief wants `refs #395`. The
  target's required check (`.github/workflows/require-linked-issue.yml`) passes only with
  a closing keyword or an issue linked in the PR's Development sidebar, and this
  instance's `[tracker].issue_trailer` is `Fixes #{id}`. Decide before publish.
- **New behaviour this round.**
  - A bundle whose `Onto branch` remote cannot be fetched is held alone, as unpushed,
    named with the failed fetch. Publish would refuse it anyway (`publish.py:517`), so
    only the reason given changes. Its siblings publish.
  - With some partners' PRs closed, the re-issue step names only the others.
  - A later run that gets to the held bundle's publish and does not hold it drops the
    record (§3, where I explain why I cleared rather than kept it when that run could not
    judge the bundle). If you would rather keep the hold in that case, it is a one-line
    change at `flow.py:3193`: clear only when `ready.get(d.name) and d.name not in
    untried`. The T4 case (`:758`) would then have to assert the opposite; the mutation
    run shows it catches that change today.
- **Still deferred to you** (not build work; see `deferred-findings.json`): the
  whole-target fallback's blast radius; criterion (e) holding more than `main` when the
  partner's push fails for a reason the trial cannot see; the last wave; and a bundle
  that conflicts with a sibling and with the line at once.

## 10. Known limits (by design)

- The trial starts from the tip this run last pushed. The fold's own check stays and has
  the last word for a branch that changed after the trial.
- The trial does not apply the fold's #623/#673 "would undo work" refusals or its #747/#748
  line holds; those stay at the fold.
- `_would_be` repeats publish's fetch → checkout → apply → add → commit steps. Drift
  between them fails closed (the bundle is withheld), not open.
- `Conflicts with: 464`: 464 edits the same publish/fold block (`flow.py:3142-3286`).
  Expect a textual conflict there if both land.

## Scratch

`.pdca-scratch/` in the worktree holds the C4 and T3 logs, the mutation script and its
copies, the iteration-3 production copy used for the "iteration 3" column, and a small
script that prints a case's stderr. It is untracked and not in `patch.diff`.

No external dependency was missing. No NEEDS-HUMAN external-dependency item.
