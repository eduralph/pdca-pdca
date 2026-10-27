# Build notes — issue 694 / reissue-after-conflict-hold-names-the-partner (iteration 3)

Target: `eduralph/pdca-harness` @ main, built on the wave-2 stack base
`pdca-integration/main-r547f8028520f` at `a2e38fe` (672, 693 and 673 folded in), in
`$PDCA_WORKTREE`. Every `path:line` below is on that tree with this patch applied. The RED
was taken on this base, not on `d6057eb`. The C4 red leg prints exactly the defect line:

```
flow: issue_11 (finished in an earlier run) is not carried onto pdca-integration/main-r…: issue_11's
branch origin/fix/11 does not merge cleanly onto pdca-integration/main-r… (conflicts in shared.txt) —
an undeclared cross-wave overlap; declare the conflict / re-order, then re-run — holding issue_20 this
run; get issue_11's PR open with its branch on origin (re-open it, `pdca publish 11`, or re-drive
issue_11), then re-issue.
```

I started from the round-2 patch (`iteration-v2/patch.diff`). The round-2 review passed C1–C4
and T1–T3 and raised two C5 findings, both about who gets named. This round fixes those two,
picks up the advisory review's smaller items, and closes two more corners found while fixing
the second finding.

## What run 2 prints now (real git, from the test cases)

```
batch    … its branch origin/fix/11 does not merge cleanly onto the line — its change conflicts with
         issue_10's (shared.txt), finished in this batch — holding issue_20 this run; proposed, for you
         to confirm: declare `Conflicts with: 10` in issue_11's brief, then rebuild issue_11 on a base
         that holds issue_10, then re-issue.
base     … its change conflicts with origin/main itself (shared.txt) — …; update issue_11's branch from
         origin/main, resolving the conflict (or re-drive issue_11), then re-issue.
line     … its change conflicts with work already on the line (shared.txt) that no other finished bundle
         of this batch was found to account for — …; rebuild issue_11 on a base that holds the work it
         conflicts with, then re-issue.
off      … its branch origin/fix/13 did not merge cleanly onto the line as the fold had it then — its
         change conflicts with issue_12's (b.txt), finished in this batch, which this run does not carry
         (see its line) — …; proposed, for you to confirm, once a line carries issue_12: declare
         `Conflicts with: 12` in issue_13's brief, then rebuild issue_13 on a base that holds issue_12,
         then re-issue.
off, no  … did not merge cleanly onto the line as the fold had it then (d.txt), but merges onto the line
name       it pushes: its change conflicts with work that bundles the fold then took back off the line
           brought onto it (see their lines) — …; re-issue once those bundles are carried, or out of
           the batch.
moved    … did not merge cleanly onto the line as the fold had it then (shared.txt), but merges onto the
         line it pushes — …; re-issue: the carry tries it again on that line.
```

The `batch` step is byte-for-byte the step run 1's end-of-run line gives. Both come from one
string, `_CONFLICT_STEP` (`template/src/pdca_harness/flow.py:1004`), used by
`_report_conflict_holds` (`flow.py:1268`) and the `conflict` / `conflict_off` hints
(`flow.py:1017-1019`). The test takes the step from run 1's stderr and asserts it in run 2's
line.

## Iteration 2 carry-forward: how each finding is addressed

1. **A deleted file wrongly blamed an unrelated stacked partner** (`integrate.py:1186`/`:1191`
   in round 2). Round 2 tried a stacked partner P on "base + what P was built on + the held
   branch (`-X theirs`) + P". `-X theirs` cannot settle a modify/delete conflict, so that
   trial stopped at the held branch, and round 2 then named P on the plain trial's files.
   Now P is named only when that trial reaches P's own head and that merge conflicts
   (`_partners`, `template/src/pdca_harness/integrate.py:1208-1231`; the rule is
   `if at != len(below) + 1: continue` at `:1228`). A trial that stops earlier proves nothing
   against P, so P is not named.
   - Regression: `test_a_partner_built_on_a_deletion_is_not_named_for_it`
     (`template/tests/test_flow_reissue_after_conflict_hold.py:366`). This is the reviewer's
     case: 10 deletes `shared.txt`, 12 (built on the line holding 10) only adds a file, and 11
     changes `shared.txt`. Before the change, on round-2 code, it failed with "conflicts with
     issue_10's (shared.txt), issue_12's (shared.txt) … `Conflicts with: 10, 12`".
   - Guard against over-correcting: `test_a_partner_built_on_another_is_named_when_its_own_change_deletes_the_file`
     (`:384`). When P's *own* change deletes the file, the trial reaches P and P is named.

2. **A partner that #672 later took off the line stayed in the advice** (`integrate.py:615`
   vs `:627` in round 2). Round 2 judged each skipped id at the end of the pass that skipped
   it, before `_hold_work` could take merged bundles back off and restart the line. Now every
   skipped id is judged once, after all passes and after `_built_on_skipped`, on the line the
   fold actually pushes (`integrate.py:635-657`). Partners can only be bundles that line
   carries: the final pass's `took` (`:657`). If none fits, the branch is tried on the pushed
   line itself (`:1196`). If it conflicts there, the result is `"line"`. If it merges there,
   its merge failed on work the fold then took back off. That is `"off"`: the bundles that were
   on the line when it was tried and that a later pass took off (`:653-654`; the snapshot is
   taken at `:605`), each one named only if its own change conflicts. Those names are always
   reported as not carried, and the step is conditional ("once a line carries issue_12: …").
   It never advises a rebuild on a base that no line is.
   - Regression: `test_a_partner_the_fold_takes_off_the_line_is_named_as_not_carried`
     (`:399`). This is the reviewer's case: 10/11 clash on `a.txt`, 12 is cut from fix/11 and
     resolves `a.txt` as 10 does and changes `b.txt`, 13 changes `b.txt`, and only 10 is
     carried. Before the change, on round-2 code, it failed: 13's line read "conflicts with
     issue_12's (b.txt), finished in this batch … rebuild issue_13 on a base that holds
     issue_12", with no word that issue_12 is not carried.
   - The reviewer's two suggestions, and why I went further:
     - "Drop partners in `holds`" alone leaves 13 with no partner. Round-2 code then prints
       `"line"`: "conflicts with work already on the line (b.txt) … rebuild issue_13 on a base
       that holds the work it conflicts with". That is false, because 13 merges onto the
       pushed line.
     - So a judgment on the final line also needs an outcome for "merges there". `"off"` and
       `"moved"` (below) are that outcome.

Advisory-review items:

- `partners` is now never filled for a held id. The fold no longer judges ids in `holds`
  (`integrate.py:641`), so the flow's `if name not in holds` filter is gone
  (`flow.py:1197-1199`). The `built_on` update after it still wins (`flow.py:1202`).
- The O(n²)-per-conflict cost of round 2's `_own_work` is gone. `_built_on`
  (`integrate.py:1234`) runs once per fold, only when there is an id to judge.
- The dead `if clashes is not None` inside the loop is gone. The loop that used it moved out
  of the pass (`integrate.py:641-642`).

## Two more corners, found while fixing finding 2

- **`"moved"`**: the branch merges onto the pushed line, but none of the bundles that were on
  the line when it was tried was taken off. A merge after it in the same pass changed the line.
  "Re-issue once those bundles are carried" would be wrong here, because there are none. The
  correct step is a plain re-issue. `test_one_a_later_merge_lets_onto_the_line_is_carried_by_a_plain_reissue`
  (`:577`) shows it: 12 puts back a file that hand-made work on the line had changed. A third
  run, re-issued as the line says, really carries 11 and builds 20.
- **Only bundles on the line when it was tried count for `"off"`** (`integrate.py:653-654`).
  A bundle merged and taken off *after* the skipped one was tried cannot be what its merge
  failed on. `test_a_bundle_taken_back_off_after_it_was_tried_changes_nothing` (`:580`)
  adds such a bundle (31, held for 30's work, asked for after 11). A merge spy asserts 31 really
  merged after 11 failed. The advice is still the plain re-issue, and run 3 carries 11.
- **`"off"` with no name** (`:587`): 32 clashes with work that 31 (held) brought from 30
  (skipped for a base conflict). The trial on what 31 was built on stops at 30's commit, so
  31 is not named. The line says to re-issue once the bundles taken back off are carried or
  out of the batch.

## How the partner is found (the brief asks for this)

In `integrate.fold`, under `skipped`, and only when the caller passes `clashes` (only the carry
does, `flow.py:1180-1185`), a bundle whose merge raises `_Conflict` is remembered. The record
holds its head, the files (`_Conflict.paths`, `integrate.py:99-107`, filled at `:754`), and the
names merged so far in that pass (`integrate.py:603-605`). After the last pass, for each such
id not in `holds` (`:641`), `_clash` (`integrate.py:1161-1205`) runs with the pushed line
checked out:

1. **Base first** (the brief's pinned rule). Trial-merge its head onto `<base_remote>/<base>`
   alone. A conflict gives `"base"`: no bundle named, the trial's files (criterion 2).
2. **Carried partners.** For each bundle the line carries (`took`, merge order), check that the
   head does not merge cleanly onto base + that bundle's head (`_partners`, `:1208`). If the
   bundle was built on more than the base, it must also pass the own-change trial above. Any
   named gives `"batch"`, each with its files.
3. **The pushed line.** Trial the head on the pushed line (`:1196`). A conflict gives
   `"line"`: no bundle named, that trial's files.
4. **Bundles taken back off.** If the head merges there: with no bundle from step 2's
   snapshot taken off, the result is `"moved"`. Otherwise it is `"off"`, with the taken-off
   bundles whose own change it conflicts with (the step-2 rule), possibly none.

"What a bundle was built on" (`_built_on`, `integrate.py:1234-1262`) works as follows. Take
the parents of its own commits that are neither its own nor on the base. Its own commits come
from #673's walk (`_own_commits`, `:972`; the first-parent chains of the pushed line and the
base, `_cut_point`, `:949`), minus the own commits of any other bundle of the fold whose head
it holds. It is computed once, for every bundle with a head in the clone. If a git read there
fails, the tree is untouched and every judged id gets `"line"`: no bundle named, never a stop
(`:646-650`). A trial git step that fails inside `_clash` does the same (`:1202-1205`). A tree
that will not go back (`IntegrationTreeError`, `_LineBroken`) still stops the fold.

The brief's "trial `_merge` … undone with `_reset_line`" is met by reusing #674's `_trial`
(`integrate.py:1265`). It runs `_merge` on a detached HEAD, then `_reset_tree`, then checks
the branch is back at its tip (`_LineBroken` if not). Same mechanics, no second copy. The
`-X theirs` is a keyword on `_merge` (`:1111`, `:1124`), used only by the `wins` index of a
trial (`:1286`).

The flow maps each result to a reason and a hint (`_clash_why`, `flow.py:1029-1058`; hints
`flow.py:1015-1025`). The #652 `built_on` hint (`flow.py:1013`) was the model for a hint that
names another id. The carry's hold line and its format call are at `flow.py:1214-1224`.

## Decisions and what I ruled out (with costs)

- **Judge after all passes, not after each pass.** Round 2's per-pass block was 9 lines inside
  the loop. The new block is 23 lines after it (`integrate.py:635-657`). The extra lines pay
  for one `_built_on` per fold instead of one per conflicting id, the git-read fallback, and
  the per-id `off` list. Judging per pass is the cause of finding 2. Patching its output
  afterwards ("drop partners in `holds`", +2 lines) still prints a false `"line"` for the
  reviewer's 13, as shown above.
- **Not naming on an incomplete own-change trial, instead of completing it.** Completing it
  would mean settling each non-content conflict on the held branch's side: `git checkout <rev>
  -- <p>`, or `git rm` when `<rev>` lacks `<p>`, then commit. But `_merge` resets the tree on
  any failure (`integrate.py:1130`), so it would need a "keep" mode. Sketch: `_merge(...,
  keep=True)` skips `_reset_tree` (+3 lines). `_trial` at the `wins` index loops the unmerged
  paths and commits (+8). Error handling for a failed checkout/rm/commit (+3). That is about
  +14 production lines plus a test. It would only change the result when the branch changes
  a file that what P was built on deleted *and* P's own change touches that file again. The
  reviewer asked to "attribute only demonstrated own changes", which the cheaper rule does.
- **`"moved"` as its own outcome** (+2 lines in `_clash`, +2 in `_clash_why`, +1 hint).
  Without it, that case gets the `"off"` advice "re-issue once those bundles are carried", but
  there are none. The plain re-issue the test runs proves the right step. Mutant M-g shows the
  difference.
- **Retrying a skipped id on the final line**, which would carry the reviewer's 13 this run,
  is out of scope. The brief says "carrying the held bundle" is out, and the review says
  "Retrying the held merge itself remains outside this slice's scope". The docs keep this as
  a known limit, now "(named, as above)".
- **Reusing `held_out` / `_held_by` unchanged** is ruled out by the brief. It judges against
  the line "as the wave found it", which on a re-issue already holds `issue_10`.

## Mutation checks (each part pinned by a test)

M-a to M-h were patched in memory, with no file touched, and the 18 cases run against each.
M-i is inline in `fold`, so I swapped the file text in a subprocess run and restored it; the
`sha256sum` was identical before and after.

| Mutant | Red |
|---|---|
| M-a round 2's rule: an incomplete own-change trial still names P | `…_built_on_a_deletion_is_not_named_for_it`, `…_taken_back_off_brought_names_no_partner` |
| M-b bundles taken back off count as on the line (round 2's effect) | `…_takes_off_the_line_is_named_as_not_carried`, `…_taken_back_off_brought_names_no_partner` |
| M-c no trial on the pushed line | `…_other_work_on_the_line_names_no_partner` |
| M-d no `"off"` / `"moved"` (report `"line"`) | 4 cases, incl. both finding-2 cases |
| M-e no own-change trial for a stacked partner | 10 cases, incl. criterion (1) |
| M-f no base-alone trial first | `…_conflict_with_the_base_names_no_partner`, `…_names_no_partner` (30) |
| M-g no `"moved"` (always `"off"`) | `…_carried_by_a_plain_reissue`, `…_after_it_was_tried_changes_nothing` |
| M-h no own-change trial for bundles taken back off | `…_taken_back_off_brought_names_no_partner` |
| M-i every bundle taken back off counts, not only those on the line then | `…_after_it_was_tried_changes_nothing` |

Round-2 production code, against the two finding regressions (run before I changed any code):
both red, each with the exact wording the review quotes.

## Known gaps (documented, not fixed here)

- Base first, as the brief pins it. A branch that conflicts with the base and also with a
  partner is reported as a base conflict only. After it is updated from the base, the next
  re-issue names the partner.
- A carried partner hides a taken-off one. If the branch conflicts with both, only the carried
  one is named. The other is named on a later re-issue, once a line carries it.
- An incomplete own-change trial names nothing (finding 1's rule). In the rare case where P's
  own change also re-touches the file its base deleted, P is not named (see the cost note).
- `"off"` counts every bundle that was on the line when the branch was tried and was taken off
  later. One that was there but unrelated still makes the advice "wait for those bundles"
  rather than "re-issue". The advice is still safe: a re-issue after they are dealt with
  carries it.
- A commit two bundles share while neither holds the other's current tip counts for both
  (same accepted limit as #673's `_undone_paths`).
- Which of two conflicting ids is carried is unchanged (out of scope).
- Cost: per conflicting id, one base trial, then one or two trials per carried bundle, then
  possibly one trial on the line and one or two per taken-off bundle. `_built_on` runs once
  per fold. All of this is only on the carry's conflict path.

## Test runs (project runners, each under `timeout`)

- C4, `engine/scripts/run-verify.sh` (`PDCA_BUNDLE`, `PDCA_WORKTREE`), on the final patch:
  green leg `Ran 18 tests … OK`. Red leg (production hunks reverted, test kept)
  `Ran 18 tests … FAILED (failures=18)`, every one an `AssertionError`, none a load or type
  error. `PDCA-EVIDENCE: C4 PASS`. After the gate, `git diff HEAD` of the worktree is
  byte-identical to `patch.diff`.
- T3, `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`; driver suite
  `Ran 2509 tests … OK (skipped=2)`. So every case of `test_flow_resume_stack_prereqs.py` and
  `test_flow_same_wave_conflict.py` is green (criterion 3).
- T2, `engine/scripts/run-docs-check.sh`: docs lint clean, site render + link audit clean.
- C5, `engine/scripts/run-prod-path.py`: the added test imports `pdca_harness`.

## Self-refutation

- **(a) Genuine red? Yes.** C4's red leg reverts the production hunks and keeps the test. All
  18 cases fail on their assertions, each showing the base's "an undeclared cross-wave
  overlap … get issue_11's PR open … `pdca publish 11`" line (or 30's). Against round-2 code,
  the two finding regressions fail as the review describes. Each part of the new logic, broken
  on its own (M-a … M-i), turns at least one case red.
- **(b) Production path? Yes.** Every case drives `flow._drive_and_act` →
  `_carry_finished` → `_fold_lines` → `integrate.fold` → `_merge_published` / `_clash` /
  `_partners` / `_built_on` / `_trial`, with real git: a bare origin, a primary checkout, and
  a scratch clone for the people outside the harness. The stubs are the same ones the
  `SameWaveConflict` suite uses: the build leaf, the publish leaf (which still cuts and pushes
  real branches, and now can delete a file), `publish.draft_texts`, and `gh` (answered OPEN
  with the branch's real tip). The test imports modules only.
- **(c) Fixture includes the fault? Yes.**
  - Deletion case: 10's branch really deletes `shared.txt`, and the test asserts 12's branch
    has no `shared.txt` (it carries the deletion).
  - Taken-off case: the test asserts 12's head holds 11's, no line is on origin before run 2,
    12's line says it was built on 11, and only 10 is carried.
  - "Moved" cases: a merge spy asserts the fold tried 10 (merged), then 11 (refused), and 31
    merged after that and was never refused. A third run really carries 11 and builds 20.
  - Criterion (1): before run 2, the test asserts 10, 11, 12 and 21 are COMPLETE, the `gh` stub
    reports each PR OPEN with its real head, and 21 is on no line.

## Commit-ready

The target has no pre-commit config, no `core.hooksPath`, and no formatter or linter config
(no ruff/flake8/black settings). `CONTRIBUTING.md` asks for DCO sign-off, which publish adds,
and green suites (T3 above). `git diff HEAD --check` is clean, and no added line is over 100
columns. `patch.diff` is `git diff HEAD` of the worktree (the new test is marked intent-to-add
in the worktree's index) and reverse-applies cleanly.

## Process notes

- I wrote one log file outside the allowed roots: `/tmp/c4-694.log`, the output of my first
  C4 run, kept so I could inspect the red leg. It holds gate output only. I did not delete it,
  since cleanup is the harness's job. Every later run piped its output directly.
- The reviewer's repro scripts (`review-deletion.py`, `review-dropped-partner.py`) were not
  kept in the bundle. I rebuilt both cases from the review text as flow-level tests.
