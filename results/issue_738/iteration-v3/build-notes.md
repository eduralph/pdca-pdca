# Build notes — #738 (iteration 3): hold a bundle whose own base cannot be built

Base: `pdca-integration/main-r547f8028520f` at `75a886e` (the worktree's HEAD). "base:N" is a
line on `75a886e`; "now:N" is the same file with `patch.diff` applied. All paths are under
`template/`.

## Starting point

I applied iteration 2's `patch.diff` (`results/issue_738/iteration-v2/patch.diff`; it applies
cleanly to `75a886e`) and changed only what the round-2 carry-forward asks for. Kept from
iteration 2, unchanged: the catch-and-hold in `_bundle_bases` (flow.py now:1040-1044, base:1019-1022
re-raised), the wave loop's hold instead of `STOPPING` (now:2891-2902, base:2759-2770),
`_runnable`'s `unbuilt` partner check and its #674-style partner line, `_announce_base_holds`
(now:1061), `_note_base_rewrites` (now:1080), `base_rewrites.clear()` after a fold that did
not stop (now:3018), `_results_rc`'s exemption for the `"base"` reason (cli.py now:742-743),
the extra fields on `_Rewritten`, the `checkout -B` wording, and the edits to the two older
test files.

Size of this round, production only, against iteration 2's tree: cli.py +6 -4, flow.py +61
-37, integrate.py +57 -10.

## The three carry-forward findings

**1. A rewrite restored mid-run was still reported stale, and the run failed (probe P1).**
Iteration 2's `_report_stale_prs` took a head as lost because the refusal had judged it so,
and never read the branch again. The member also stays out of `_report_late_rewrites` (the
brief requires that; flow.py now:3056, base:2914), so nothing else re-read it.

- New `integrate.lost_now` (integrate.py now:1317-1340): which of the given heads the
  member's published branch does not hold *now*. It reads the branch the same way the #695
  end-of-run check does (`rewritten_carried`, base:1199): `_fetch(..., attempts=2)`
  (base:1238), `_rev`, then `_carried_rewrite` per head (base:1172). A branch that no longer
  resolves is left alone, as `rewritten_carried` leaves it (base:1247). If it cannot judge,
  it raises `IntegrationError` with `cause`.
- `_report_stale_prs` (flow.py now:1092-1148) first collects the PRs that hold a lost head,
  as before. If there are none (only the line holds the old commits, as in case (2)), it does
  no fetch and returns nothing. Otherwise it calls `lost_now` (now:1127) and keeps only the
  heads still lost. Only those PRs make the member `"rewritten"` (now:1140) and get a line.
  The line now says "...as the hold line of issue_B above says, and still lacks it, so...".
- If the re-read fails, the member gets `"unchecked"` (now:1129). One line names every PR on a
  lost head, with the cause, and asks for a check by hand: "could not read issue_A's branch
  origin/fix/A again (could not fetch origin in …) to see whether it was restored after the
  hold line of issue_B above named it rewritten, so these PRs may hold commits it no longer
  has: issue_S, which is cut from <line> at <tip>, holding <head>. Check by hand …". It never
  claims the PR holds old commits. `"unchecked"` is already in `_FAILED_REASONS` (cli.py
  now:699, base:698), so the exit is 1, as for the #695 check.
- Return type is now `{member: reason}`, merged into `holds` at flow.py now:3069 (iteration
  2 wrote a fixed `"rewritten"`). Call site: now:3053-3055.
- Tests: `test_a_rewrite_restored_while_the_last_wave_builds_fails_nothing` is the P1 probe.
  fix/A is put back at the line's head right after S publishes, in the last wave, so no fold
  comes after. It asserts no line names S, `holds == {"B": "base"}`, exit 3.
  `test_a_rewritten_branch_that_cannot_be_read_again_names_each_pr_to_check` covers the
  failed re-read: `holds == {"B": "base", "A": "unchecked", "Z": "unchecked"}`, exit 1. Z is
  `"unchecked"` from the existing end-of-run check, whose fetch fails too.

**2. The test file's docstring over-claimed.** Rewritten (test file :1-50). It now says that
the rest of the wave goes on; that later waves and folds go on only for a failure only that
base meets (the fetch, in the four-wave case); and that a rewrite not restored, or a moved
`main`, can still stop the run at the next fold. I checked both of those claims with
throwaway probes (not committed). Rewrite held in wave 1 of 3: `wave 1 did not integrate
(issue_A's branch origin/fix/A was rewritten …); STOPPING`, V PLANNED, rc 1. Moved `main` in
wave 1 of 3: `wave 1 did not integrate (issue_W's branch origin/fix/W does not merge cleanly
… (conflicts in a.txt))`, rc 1. The second one is the #739 clash at the line fold (out of
scope). The `NOT_DONE` comment no longer names "iteration 1" (PDCA-internal wording).

**3. One fix for three different causes in the base build's fetch wrapper.**
`_prepare_worktree` can raise for a missing checkout (base:2032), a failed fetch (base:2043)
or a worktree it cannot create (base:2056). Iteration 2 told all three to "Check that remote
… and that checkout".

- Two small subclasses, raised where the cause is: `_NoCheckout` and `_FetchFailed`
  (integrate.py now:146-153), raised by `_fetch` (now:2100, now:2111). Message text and
  `cause` are unchanged, so the fold's wording, pinned at
  `test_integrate_carried_rewrite_late.py:549-550`, is unchanged.
- The wrapper in `build_bundle_base` (now:862-874, base:835) picks the step by class:
  - fetch: "Check that remote (its URL, the network, credentials), then re-run"
  - missing checkout: "Create or clone the checkout for org/repo there, or set
    [publisher.checkouts] in pdca.toml if it lives elsewhere, then re-run" (the same hint
    publish gives, publish.py base:1067)
  - anything else, i.e. the worktree: "Check that origin/main resolves in <repo> and that the
    worktree's path can be created (a directory left there that is not a git worktree blocks
    it), then re-run"
- Tests: case (3) now asserts the remote step and the absence of "Create or clone". Two new
  real-git cases make the cause happen on disk for B's base only, and undo it right after:
  `test_a_checkout_missing_while_one_base_is_built_holds_only_that_bundle` moves the
  checkout away; `test_a_worktree_that_cannot_be_made_for_one_base_holds_only_that_bundle`
  removes the integration worktree and leaves a plain directory at its path, so the real
  `git worktree add` fails. W's base, built next, works in both.

## How the brief's cases map to tests (template/tests/test_flow_bundle_base_holds.py)

| Brief case | Test (line) | Holds / exit |
|---|---|---|
| (1) moved base | `test_a_base_that_moved_under_a_prerequisite_holds_only_its_dependent` (:341) | `{B: base}` / 3 |
| (2) rewritten prereq | `test_a_prerequisite_rewritten_after_the_fold_holds_only_its_dependent` (:356) | `{B: base}` / 3 |
| (3) failed fetch | `test_a_fetch_that_fails_for_one_base_holds_only_that_bundle` (:374) | `{B: base}` / 3 |
| (3), missing checkout | `test_a_checkout_missing_while_one_base_is_built_holds_only_that_bundle` (:387) | `{B: base}` / 3 |
| (3), worktree | `test_a_worktree_that_cannot_be_made_for_one_base_holds_only_that_bundle` (:401) | `{B: base}` / 3 |
| (4) refused push | `test_a_push_origin_refuses_holds_only_that_bundle` (:421) | `{B: base}` / 3 |
| (5) partner | `test_a_conflicts_with_partner_of_a_held_bundle_is_held` (:435) | `{B: base}` / 1 |
| (6) stale line | `test_a_pr_cut_from_the_stale_line_after_a_rewrite_hold_is_named` (:457) | `{B: base, A: rewritten}` / 1 |
| (6), restored before the end (P1) | `test_a_rewrite_restored_while_the_last_wave_builds_fails_nothing` (:484) | `{B: base}` / 3 |
| (6), cannot read again | `test_a_rewritten_branch_that_cannot_be_read_again_names_each_pr_to_check` (:506) | `{B: base, A: unchecked, Z: unchecked}` / 1 |
| (6), no-patch bundle | `test_a_bundle_closed_with_no_patch_on_the_stale_line_is_no_pr` (:531) | `{B: base}` / 3 |
| (6), own base built earlier | `test_a_base_built_before_the_rewrite_in_the_same_wave_is_named` (:551) | `{E: base, A: rewritten}` / 1 |
| restored before the next fold | `test_a_rewrite_mended_before_the_next_fold_fails_nothing` (:580) | `{B: base}` / 3 |
| (7) dependent | `test_a_dependent_of_a_held_bundle_is_skipped_and_fails_the_run` (:606) | `{B: base}` / 1 |
| hold before the last wave | `test_a_hold_before_the_last_wave_carries_over_two_folds` (:619) | `{B: base}` / 1 |

The fixture patches `integrate._FETCH_RETRY_PAUSE` to 0 (test :257; the symbol is on the base,
integrate.py base:2012) so the failed re-read does not sleep.

## Judgment calls the human should check

1. **A branch deleted after the refusal is left alone at the end of the run.** `lost_now`
   returns no lost head when the branch no longer resolves (integrate.py now:1336-1337). That
   matches the #695 end-of-run check (base:1247: "in a fold, `_gone_branch` judges it; at the
   end of the run nothing does"). The cost: if fix/A is deleted while the last wave builds,
   for example because A's PR merged its rewritten head, S's PR is not named and the run exits
   3. B's hold line still names the rewrite. The other choice, keeping the refusal's judgment,
   is a one-line change (`return set(heads)` at now:1337). I did not pin either choice with a
   test, so the human can choose.
2. **A failed re-read names every PR on a lost head, including those the refusal already
   named.** The question changed from "holds old commits" to "may hold them; check by hand", so
   repeating them gives new facts, not a duplicate claim. Exit 1, as `"unchecked"` is for #695.
3. **The re-read fetches only when a PR holds a lost head.** Case (2) (only the line holds
   them) does no extra fetch and stays exit 3, as the brief asks.
4. Carried over from iteration 2, unchanged: exit 3 for case (2) (per the brief); `held_base`
   in `_runnable`'s `held=` set changes nothing today (iteration 2's mutant M7); and
   `base_rewrites.clear()` after a fold that went on relies on that fold having re-checked
   every refused member, which holds today (the round-2 code review's note).

## Deferred human findings — not changed

- A rewrite hold before the last wave: the next fold re-reads fix/A and stops the run
  (`deferred-findings.json` items 2, 4 and 12). I re-confirmed it above (probe P2). I did not
  change this behaviour; only the test docstring now says it.
- Exit 1 vs 3 for the same rewrite, depending on whether a dependent's base reads it (item
  3): exit 3 is kept, per the brief.
- Items 1, 5-11 and 13 are about the plan, the review setup or prior-art search, not this
  code.

## Alternatives ruled out

- **Drop the late-check exclusion and let `_report_late_rewrites` re-read A** (1 line, at
  flow.py now:3056). The brief rules it out: it names the rewrite a second time, and turns
  case (2) into exit 1, because the late check fails a line that alone holds the old commits.
- **Teach `integrate.rewritten_carried` to skip what a hold already named.** It would need a
  new parameter, a filter in both report branches, and a new report for line-cut PRs whose
  line report is skipped, since today those PRs are only named inside the line's report
  (`_late_line_rewrite`, base:1276). That is about 25-35 lines inside a function whose output
  the #695 and #727 suites pin line by line. `lost_now` is 24 lines, including its
  docstring, and reuses the same three helpers without touching that contract.
- **Tell the three fetch-wrapper causes apart without subclasses.** Matching the message
  text is fragile, and the codebase decides by what was raised, never by message.
  Re-checking `(repo / ".git").exists()` in the wrapper is about 2 lines, but it decides by
  reading the disk again after the fact. The subclasses are 8 lines, docstrings included, and
  the decision is made where the cause is raised, which is what the brief asks ("error
  wording in `integrate.py` where the cause is raised").

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** I ran the project's C4 gate (`engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout`) on the final `patch.diff`. Green leg:
  15 + 25 + 15 tests OK. Red leg (production hunks reverted, tests kept): 15/15 new tests
  FAIL, plus the 2 + 2 updated older tests. All 19 fail with `AssertionError: 'STOPPING'
  unexpectedly found` (no import errors). Result: `PDCA-EVIDENCE: C4 PASS`. Red against
  iteration 2: with iteration 2's production code and this round's tests, exactly the 6 tests
  tied to this round fail, each on its own assertion. That covers P1 (a line names S), the
  failed re-read (no "could not read" line), the missing checkout and worktree cases (no
  matching step), case (3) (no separate remote step) and case (6) ("and still lacks it").
  Mutants, one at a time, each run on all three modules with the file restored after:

  | Mutant | Test that goes red |
  |---|---|
  | M1 `lost_now` returns every head (no re-read) | P1 restored case |
  | M2 `_report_stale_prs` ignores the re-read | P1 restored case |
  | M3 a failed re-read is not caught | cannot-read-again case (ERROR) |
  | M4 a failed fetch gets another cause's step | case (3) |
  | M5 a missing checkout gets the worktree step | missing-checkout case |

- **(b) Production path? Yes.** The tests call `flow._drive_and_act` and `cli._results_rc`.
  The real `_bundle_bases`, `_runnable`, `integrate.build_bundle_base`, `_prepare_worktree`,
  `_fetch`, `integrate.fold`, `_report_stale_prs`, `integrate.lost_now` and
  `_report_late_rewrites` all run against a bare origin. Stubbed: the build and sign-off
  leaves, publish's mechanics (a real cut and push with git), and `gh`. For one bundle only:
  the fetch (the real `_prepare_worktree` runs with `git fetch` failing) and the push of one
  base branch. At the end of one case, every integrate fetch. No stub touches the `except`
  blocks the fix adds.
- **(c) Fixture includes the fault? Yes.** All of these are real: a clashing `a.txt` pushed
  to `main`; a force-push of fix/A; fix/A put back on origin (`git branch -f` in the bare
  origin) after S published; the checkout moved away while B's base is built; a plain
  directory at the worktree path, so `git worktree add` fails for real; failing fetches; a
  refused push. Git confirms S's published head holds the lost commit. The unrelated bundles
  (W, V, U) are in the same runs and must reach COMPLETE.

## Commit-readiness

The target configures no formatter, linter or commit hook: no `.pre-commit-config.yaml`, no
ruff/black/flake8 config, no `core.hooksPath`, only `*.sample` hooks, and no linter in
`.github/workflows`. CONTRIBUTING.md asks for the DCO sign-off (publish adds it) and a green
offline suite. `git diff --check` is clean with the new file included. No added line is over
100 columns. Every touched file compiles. ruff and pyflakes are not installed.

## Suite runs (final tree)

- C4 (`engine/scripts/run-verify.sh`): PASS, as above.
- T3 (`engine/scripts/run-suite.sh`): root suite 24 tests OK; driver suite 2609 tests OK (2
  skipped). That is 4 more than iteration 2's 2605: the four new cases.
- T2 (`engine/scripts/run-docs-check.sh`): docs lint clean, 22 pages rendered, link audit OK.
  The patch touches no docs.

## Housekeeping

- My first C4 run's output went to `results/issue_738/.c4-local.log`. That is inside the
  bundle directory, but it is not one of the three artifacts. It holds only test output. I did
  not delete it (no `rm`). The final C4 run printed straight to the terminal.
- To make `git diff` include the new test file I marked it intent-to-add (`git add -N`), then
  cleared the mark (`git reset -- <file>`) each time. The worktree index is as I found it, and
  the test file is untracked, as before. To compare against iteration 2 I swapped the
  production hunks in place with `git apply -R` / `git apply`, and checked afterwards that the
  tree matches `patch.diff` byte for byte. `git hash-object -w` left a few loose blobs in the
  repo's object store for the size count above; git's gc removes them.
