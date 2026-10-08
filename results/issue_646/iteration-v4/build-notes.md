# Build notes — issue #646 (stack-reissue-continues-batch-line), attempt 4

Withheld from the reviewer. For the human at sign-off.

## Base I built on

Same as attempts 1-3. The worktree (`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`)
is at `origin/pdca-integration/main` @ `12405dc` (`origin/main` @ `c67a14d` plus the folds of
#531, #590, #591); the bundle's `stack-base` file says `pdca-integration/main`. I started from
attempt 3's `patch.diff` (it applied cleanly), kept its approach and its round-1/round-2 fixes,
and changed only what round 3 asked for. All `path:line` below are on the patched worktree
(`12405dc` + `patch.diff`).

For the human (unchanged): the brief says not to build until #639 (#591) is merged into
`main`. Locally `origin/main` is still `c67a14d`, so it is not; the worktree has #591 through
the integration line, so the `TypeError` concern behind that rule does not apply. The PR is a
stacked PR off the integration line.

## What changed since attempt 3, by sign-off item

### 1. The deleted-branch check now uses the same PR look-up as the carry

`merged.merged_head` (`template/src/pdca_harness/merged.py:71-84`) is now built on
`merged.pr_state` (`merged.py:109-142`). So when `publish.json` has no `pr_url`, the fold's
deleted-branch check (`integrate._gone_branch`, `integrate.py:527`) finds the PR by its
branch, exactly as the carry did. This is the sign-off's second option ("have that decision
use the same branch lookup"). It also covers carried bundles in every later in-run fold, and
the code review's optional cleanup: `merged_head` lost its own copy of the `gh` call, the
`OSError` guard and the JSON parsing (30 lines down to 14).

Regression test (the review's C3 case): empty `pr_url` + PR merged + branch deleted, with the
earlier line holding P —
`test_5_a_pr_found_by_its_branch_merged_and_deleted_is_judged_by_that_pr`
(`template/tests/test_flow_resume_stack_prereqs.py:928`). It also asserts both host calls were
branch look-ups (the carry's, then the fold's).

Two existing unit tests pinned the old URL-only behaviour and are updated in the same patch:
`MergedHead.test_a_merged_pr_gives_its_head_commit` (`test_integrate_stack_bases.py:1184`, the
`--json` fields now include `mergeCommit`) and `test_no_recorded_pr_asks_nothing`, now
`test_no_recorded_pr_is_looked_up_by_its_branch` (`:1201`). The `_merged_heads` helper
(`:102-114`) also stubs the new `merged.merge_commit` (no merge commit known), so the existing
fold tests keep their meaning; one test comment that said a squash always stops is corrected
(`:453-456`).

### 2. Squash- or rebase-merged prerequisite with its branch gone — the policy I chose

**Policy:** when a merged PR's branch is gone and neither the line nor the base has the head
the PR merged with, the fold asks the host for the commit the merge made (`mergeCommit`: the
squash commit, the last rebased commit, or the merge commit). If the base has that commit,
the base carries the PR's work, and the line takes the base in — the same step the fold
already takes for a merge-commit merge whose head the line lacks. If the base does not have
it either (the PR merged into another branch), the fold still stops, as before. The decision
is by commit, on the host's record, never by message — the same rule #593 uses for the head.

Code: `merged.merge_commit` (`merged.py:87-94`) and the check in `integrate._gone_branch`
(`integrate.py:547-559`). Docstrings updated at `integrate.py:45-49`, `:336-341`,
`:505-525`; docs at `docs/07-crosscutting.md:694-699` and
`template/PCDA/quality-cycle/09-parallel-lanes.md:72`.

The residual case, and its advice: if the line already holds an older commit of the PR
(folded before a fixup) and the squash includes that fixup, taking the base in can conflict
(the two versions of the same lines). The stop message now says what works there: "restore
<id>'s branch" (`integrate.py:659-666`, GitHub's "Restore branch" button). With the branch
back, the fold merges the PR's own head, which sits on top of the older commit, so it merges
cleanly.

Tests:

- `test_5_a_squash_merged_prerequisite_whose_branch_is_gone_comes_in_through_the_base`
  (`:948`). The adversary's case: `flow P D U`, P squash-merged into main, branch deleted.
  D and U now build on the line, and the line has the squash commit.
- `test_6_a_merged_prerequisite_whose_merge_the_base_lacks_stops_before_wave_0` (`:1023`).
  The fail-closed half: P merged into `release`, so the run still stops and names the merge
  commit.
- `test_5_a_squash_clashing_with_the_lines_older_commit_says_restore_and_that_works`
  (`:974`). It follows the printed advice (restores the branch), re-issues, and D builds.

**Behaviour change beyond the re-issue path, on purpose:** `_gone_branch` is the fold's one
rule, so a squash-merged *in-run* bundle whose branch is deleted mid-run now also comes in
through the base instead of stopping the run. I did not limit it to the carry. A stop there
leads straight into the same re-issue, where the bundle is now finished and carried, so a
carry-only rule would just move the dead end one run later.

### 3. A closed PR that a newer one replaced

`merged.pr_state` now also looks the branch up when the recorded PR is CLOSED
(`merged.py:136-142`). An open PR found there wins. A newer merged one wins too. Otherwise the
closed one stands. If that look-up fails, the state is "could not be read", never a guess.

While doing this I found a hole in attempt 3's branch look-up and closed it. Attempt 3
preferred open, then merged, then closed, whatever their age. So a branch whose old PR #1
merged and whose newer PR #2 (the recorded one) was closed would count as MERGED. The fold
merges the branch's current tip, so #2's rejected commits would have ridden the line. Now an
open PR wins, and otherwise the newest PR by number decides (`merged.py:145-179`; `number` is
added to the `gh pr list` fields).

Tests:

- `test_4c_a_closed_pr_a_newer_open_pr_replaced_is_carried` (`:699`). The adversary's case:
  P is carried and D and U build on the kept line, with no "re-open" advice.
- `test_4c_an_older_merged_pr_of_its_branch_does_not_replace_the_closed_one` (`:720`).
  Mutation check: with attempt 3's open-then-merged-then-closed order put back, this is the
  one test that fails.
- `test_4d_a_closed_pr_whose_branch_look_up_fails_is_unread_not_closed` (`:729`).

The CLOSED hold message now names the PR and says no PR replaced it (`flow.py:897-902`).

### Optional items

- **Doc wording slips:** fixed in `docs/07-crosscutting.md:670-675`. Only the same-target
  wave-0 bundles are pointed at the line, and only plain `Depends on` dependents are held. The
  same slip in attempt 3's sentence in `09-parallel-lanes.md:72` is fixed too.
- **`merged_head` on the shared helpers:** done (see item 1).
- **Adversary's suggested wave-1 test:** added as
  `test_2_a_line_holding_an_earlier_waves_bundle_is_continued` (`:469`). The earlier run
  folded P, then D (cut from the line), then stopped. The re-issue vouches for both and
  continues the line. It passes on attempt 3's code too, as the adversary found. It now pins
  that shape.

## Alternatives ruled out (with cost)

- **Item 1, pass the carry's PR facts into the fold.** This needs a new `fold` parameter
  threaded through `_fold_and_regate`, `fold`, `_merge_published` and `_gone_branch`, plus the
  in-run call: about +12 lines. It would still be stale for a PR that merges mid-run, so
  `_gone_branch` would need the look-up anyway. The shared look-up costs nothing extra and
  removed 16 lines.
- **Item 2, "a merged prerequisite is nothing to carry" (carry-only).** If the earlier line
  holds P's commits, the vouch check then refuses the line, because no carried bundle accounts
  for them. That is a new dead end. Avoiding it needs P as a vouch member without being folded
  (about +10 lines), and the carry cannot know "branch gone, head not on base" before the
  fold's own fetch (a second copy of `_gone_branch`'s checks, about +20 lines). That is about
  +30 lines and a second rule.
- **Item 2, a content check** (`git merge-tree --write-tree <base> <head>` gives the base's
  tree). No host call, about +10 lines. But it needs git ≥ 2.38 and the head in this clone; a
  squash after a fixup this clone never fetched has neither, so it would still stop. And it
  decides by content, where #593 deliberately decides by commit.
- **Item 2, hold P's dependents instead of stopping the run.** U would go on, but D would be
  held on every re-issue with the same advice. Still a dead end for D.
- **Item 3, accept any open or merged PR on the branch (the literal ask).** That is the hole
  described in item 3. "Newest decides" costs 3 lines.
- **Not done (cosmetic, from the round-3 code review):** the `pr.state == "NONE"` branch in
  `_carry_finished` still re-derives the repo and `OWNER:BRANCH` (`flow.py:903-911`). Moving
  them into `PR` would add two fields used only there. The refusal line still names no bundle
  for a carried bundle re-pushed with a rebuild; the "brought in by … pdca-integrate: issue_P"
  subject already points at it, and deciding on that subject would break the by-commit rule.

## Known limits (named, not fixed)

- Criterion (7) stands. A re-issued run where no driven bundle plainly `Depends on` a finished
  id carries nothing, and its first fold starts the line fresh. The docs and messages say so.
- The squash policy trusts that the base still has the PR's work once it has the commit the
  merge made. A later revert on the base undoes that. The existing merge-commit path (head on
  base) has the same property, and so did the pre-patch "build on main".
- "Newest decides" errs toward holding. If the newest PR of a branch is a closed duplicate of
  an older merged one, P is held as CLOSED; re-opening it, or re-driving P, clears it.
- Behaviour change, unchanged from attempt 3: a carried PR closed with its branch deleted
  during the run stops the run at the next in-run fold, as for an accepted in-run bundle.
- `merged.is_merged` (`Depends on (merged)`) is still URL-only, with no `OSError` guard. That
  is pre-existing and child-2's area.
- The adopted split child limit and the "trusts first-parent merge commits" limit from
  attempt 3 still apply. Both are named in docstrings.

## Self-refutation (forced)

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh`, which
  reverts only the production hunks) on the final `patch.diff`:
  - Green leg: 39/39 new tests and 46/46 in `test_integrate_stack_bases`.
  - Red leg: `FAILED (failures=34)` of the 39 new tests, all assertion failures and 0 errors.
    Plus 4 in the other file: the 2 wording tests the brief named, and the 2 `MergedHead`
    tests updated for item 1.
  - The 5 tests green on both legs are the "unchanged" guards, which must pass either way:
    the two `test_5` nothing-to-carry cases and the three `test_7` cases.
  - Verdict: `PDCA-EVIDENCE: C4 PASS`.

  Against **attempt 3's production code** (swapped with `git apply`, restored, checked with
  `cmp`), 9 tests fail:
  - On behaviour: items 1, 2 (squash) and 3 (newer open PR; failed look-up), plus the 2
    `MergedHead` tests.
  - On wording only: three tests where attempt 3 did the same thing but its message lacked
    what the test reads (the PR URL, the merge commit, "restore issue_P's branch").

  The look-up order also has the mutation check described in item 3.
- **(b) Production path? Yes.**
  - Real: `flow._drive_and_act` with `batch=[…]`, as `flow_ids` calls it, and inside it
    `_runnable`, `_carry_finished`, `_fold_and_regate` and `_point_at_integration`;
    `integrate.fold` with `_vouch`, `_merge_published`, `_gone_branch` and `_take_in_base`
    against real git with a bare `origin`; `merged.pr_state`, `merged_head` and
    `merge_commit`; `publish.publish` (`open_pr=False`).
  - Stubbed: `flow._drive_wave` (build and sign-off), `publish.draft_texts`,
    `publish._warn_if_squash_only`, and `gh` itself, answered at `merged.subprocess` for
    `gh pr view` and `gh pr list`.
- **(c) Fixture includes the fault? Yes.**
  - The squash is a real `git merge --squash` pushed to main, with the branch deleted.
  - The "merged elsewhere" case really merges into `release`.
  - The clash case's line really holds P's first commit while main holds the squashed fixup,
    and the test really restores the branch.
  - The empty-`pr_url` case's earlier line is made by the real fold, then the PR is merged
    and the branch deleted.
  - The replaced-PR cases list both PRs for the branch, with numbers.
- **Live host shape, checked (read-only).** `gh pr list --json
  number,url,state,headRefOid,mergeCommit,headRefName,headRepositoryOwner` and `gh pr view
  --json state,headRefOid,mergeCommit` against `eduralph/pdca-harness` return
  `"mergeCommit":{"oid":"…"}` for a merged PR, `null` for an open one, and an integer
  `number`. That is what `merged._pr` parses. The test table uses the same shapes.

## Commands run (the project's runners, each under `timeout`)

- C4: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `C4 PASS`, run twice,
  the second time on the final `patch.diff`.
- T3: `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh` → root suite OK (24), driver suite OK
  (2364, 2 skipped; attempt 3 had 2356, and the 8 extra are my new tests).
- T2: `./engine/scripts/run-docs-check.sh` → docs lint clean, site render and link audit clean.
  `run-host-ci.sh` from the worktree → clean.
- C5: `run-prod-path.py` → the added test imports `pdca_harness`.
- Commit-readiness: the target has no formatter, linter config or hooks (no
  `.pre-commit-config.yaml`, no `core.hooksPath`, no non-sample hooks, no ruff/black/flake8
  config). Its CI runs only the docs checks and the root render suite, and both pass above.
  Every touched `.py` parses with `ast.parse(feature_version=(3, 11))` and has no unused
  imports. No added line is over 96 columns. `git diff --check` is clean, and the patch
  applies cleanly to `12405dc`. The DCO sign-off is added by publish (`git commit -s`).

## Size signal — expect it to fire

`patch.diff` is 153,028 bytes (149.4 KiB), over this instance's advisory `patch_kb = 125`.
This is also round 4, so the `rounds = 3` leg fires regardless. Both are advisory (§6, never
blocking). The new test file is 67 KB of it, and `09-parallel-lanes.md` costs 8.6 KB because
each bullet is one long line that any edit re-emits twice. Getting under 125 KiB would mean
dropping about 24 KB, which means real tests, so I did not.

## Housekeeping

- Scratch files are under the worktree's git-ignored `.cache/646/` (gate logs, a saved
  production diff used for the swaps, a temporary index, a message-printing helper). They are
  not in `patch.diff`, and I did not delete them (no `rm`).
- The new test file is marked intent-to-add (`git add -N`) in the worktree's index, so
  `git diff` includes it.
- The bundle copy of the test is at
  `results/issue_646/template/tests/test_flow_resume_stack_prereqs.py`, identical to the
  worktree file (checked with `cmp`).

No external dependency was missing.
