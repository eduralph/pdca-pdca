# Build notes — issue 694 / reissue-after-conflict-hold-names-the-partner (iteration 2)

Target: `eduralph/pdca-harness` @ main, built on the wave-2 stack base
`pdca-integration/main-r547f8028520f` at `a2e38fe` (672, 693 and 673 folded in), in
`$PDCA_WORKTREE`. Every `path:line` below is on that tree with this patch applied. The RED
was re-taken on this base, not on `d6057eb`: the C4 red leg prints exactly the defect line
("… does not merge cleanly onto pdca-integration/main-r… (conflicts in shared.txt) — an
undeclared cross-wave overlap … get issue_11's PR open … `pdca publish 11` …"), so #672's
`skipped` → `why` change does not touch `issue_11` here, as the brief predicted.

## What the run now prints (run 2 of each case, real git)

```
(1)  … is not carried onto pdca-integration/main-r…: its branch origin/fix/11 does not merge cleanly onto the line — its change conflicts with issue_10's (shared.txt), finished in this batch — holding issue_20 this run; proposed, for you to confirm: declare `Conflicts with: 10` in issue_11's brief, then rebuild issue_11 on a base that holds issue_10, then re-issue.
(2)  … — its change conflicts with origin/main itself (shared.txt) — holding issue_20 this run; update issue_11's branch from origin/main, resolving the conflict (or re-drive issue_11), then re-issue.
line … — its change conflicts with work already on the line (shared.txt) that no other finished bundle of this batch was found to account for — holding issue_20 this run; rebuild issue_11 on a base that holds the work it conflicts with, then re-issue.
stacked … — its change conflicts with issue_10's (a.txt), issue_12's (b.txt), finished in this batch — …; proposed, for you to confirm: declare `Conflicts with: 10, 12` in issue_11's brief, then rebuild issue_11 on a base that holds issue_10, issue_12, then re-issue.
```

The step in (1) is byte-for-byte the step run 1's end-of-run line gives (the test takes it
from run 1's stderr and asserts it in run 2's line).

## Iteration 1 carry-forward — how each finding is addressed

1. **Later-listed partners already on the line were never tried** (`took` only). Now the
   candidates are every other bundle of the fold with a known head
   (`integrate.py:613-617`), kept when one of its own commits, not a merge, is on the line
   (`integrate.py:1176-1181`). Order no longer matters. Test:
   `test_a_partner_already_on_the_line_is_named_when_asked_for_after`
   (`test_flow_reissue_after_conflict_hold.py:180`), the reviewer's re-issue as `11 10 …`.
   Run against iteration 1's production code it fails with "no bundle of this batch accounts
   for" (run below).
2. **Ancestry pruning hid a stacked partner's own edit.** Pruning is gone. A partner built
   on more than the base is judged by its own change only: trial merge of base + what it was
   built on, then the held branch with `-X theirs` (its side wins every hunk that clashes
   with that), then the partner's head; it is named when that last merge conflicts, with
   that merge's files (`integrate.py:1185-1191`, `wins` at `:1231-1252`, `theirs` at
   `:1092-1105`). Tests: `…_named_for_its_own_file` (`:283`, the reviewer's two-file case),
   `…_named_for_its_own_lines_of_a_shared_file` (`:306`, same file, different lines),
   `…_not_named_when_its_own_lines_merge` (`:317`), and
   `test_one_built_on_the_partner_is_not_named_for_the_partners_change` (`:244`).
   Iteration 1's code fails the first two.
3. **Criterion (2)'s test passed without the fix.** It now asserts text only the fix prints
   ("its change conflicts with origin/main itself (shared.txt)" and "update issue_11's
   branch from origin/main, resolving the conflict"), plus no "cross-wave" / "PR open" /
   "pdca publish 11" (`:331-360`). C4's red leg now fails it.

The advisory review's smaller items: the `Conflicts with` step is one shared string now,
`_CONFLICT_STEP` (`flow.py:1004`), used by both `_report_conflict_holds`
(`flow.py:1246-1250`, output byte-identical, its tests unchanged and green) and the carry's
`"conflict"` hint (`flow.py:1017`); `cands[name][2][1]` without the dead fallback
(`flow.py:1175`); the double `_not_carried` call is gone.

## How the partner is found (the brief asks for this)

In `integrate.fold`, under `skipped` and only when the caller passes `clashes` (only the
carry does, `flow.py:1159-1164`), a bundle whose merge raises `_Conflict` is remembered with
its head and the files (`integrate.py:598-600`; `_Conflict` now carries `paths`,
`integrate.py:99-107`, filled at `:735`). At the end of that pass, before #672 may restart
the line, `_clash` (`integrate.py:1142-1196`) is called for each, with the line checked out
as the pass left it:

1. **Base first.** Trial-merge its head onto `<base_remote>/<base>` alone. A conflict there →
   `"base"`, no bundle named, the trial's files (criterion 2, the pinned rule).
2. **Partners.** For every other bundle of the fold with a head (branch tip read once, else
   its PR head), work out its own commits (`_own_work`, `integrate.py:1199-1228`): what its
   head reaches without passing through the first-parent chain of the line or of the base —
   the same walk #673 uses (`_own_commits`, `integrate.py:953`; `_cut_point`, `:930`) — less
   the own commits of any other bundle whose head it holds. It is a candidate only if one of
   those (not a merge) is on the line. So a bundle merged by this pass (before or after the
   held one), or already on origin's line, counts; one only built on the line, or one held
   too, does not.
3. **Trial.** Its change conflicts when the held head does not merge onto base + its head
   (index 1 of the trial). If it was built on more than the base (`under`: the parents of
   its own commits that the base lacks — the line commit it was cut from, or the branch it
   was cut from), the isolation trial above decides, so only its own change counts.
4. **Else `"line"`**: files from the real merge, no bundle, no `Conflicts with`. A trial git
   step that fails with no conflicting path also lands here (never a stop); a tree that
   will not go back (`IntegrationTreeError`, `_LineBroken`) still stops the fold.

The brief's "trial `_merge` … undone with `_reset_line`" is met by reusing #674's
`_trial` (`integrate.py:1231`): `_merge` on a detached HEAD, then `_reset_tree` and a
check that the branch is back at its tip (`_LineBroken` if not). Same mechanics, no second
copy. The flow side maps the result to a reason and hint (`_clash_why`, `flow.py:1025-1040`;
hints `flow.py:1015-1021`), applied for each clashed id not held for a skipped id's work —
the #672 `built_on` reason still wins for those (`flow.py:1172-1180`) — and fills
`partners` / `ids` / `base` into the hint (`flow.py:1194-1198`).

Docs: the carry paragraph of `docs/07-crosscutting.md` gets the new behaviour (`:767-783`)
and the known-limits entry now says the pair is named with the step (`:791-792`); the rest
of that paragraph is only re-wrapped.

## Decisions and what I ruled out (with costs)

- **Judge at the end of the pass, not at the failed merge.** The brief says partners are
  ids "merged in this fold, or already on origin's line"; it does not say "before it". At
  the end of the pass the line also holds bundles merged after the held one, and the next
  re-issue meets exactly that line, so naming them saves a round trip. Same code size as
  judging at the merge (the call moved from the `except` to after the loop, plus one dict).
  Test `test_one_the_fold_merges_after_it_is_named_too` (`:202`) pins it; it fails if the
  call is moved back (mutation M7 below). This differs from #674's in-run hold, which only
  judges bundles merged before it; on a re-issue the line from run 1 holds those later
  bundles anyway, so the carry names them in either design.
- **`-X theirs` isolation instead of comparing file lists.** The file-list version (files
  of base+held+X subtracted from base+partner+X) is about the same size but misses a partner
  whose own change is in a file the held branch also conflicts in. Mutation M3 turns
  `…_own_lines_of_a_shared_file` red. Cost of the chosen way: a `theirs` keyword on
  `_merge` (+2 lines) and a `wins` index on `_trial` (+2 lines).
- **Ownership by the line's first-parent chain, not by current tips.** My first rewrite
  judged "what it was built on" from the other bundles' current tips. A fixup pushed to
  `fix/10` after run 1 then made `issue_21` (cut from the run-1 line, which holds the old
  `issue_10` commit) look like it owned `issue_10`'s change, and it was named. The new test
  `test_a_partner_whose_branch_moved_on_since_is_named` (`:188`) caught it; mutation M4
  pins it. Reusing #673's `_own_commits` walk fixed it with no new walk code.
- **Finding partners in `flow.py` after the fold** (ruled out): the line as the pass left
  it, the worktree and the lock exist only inside `fold`. After `_fold_lines` returns the
  lock is released and the tree holds the pushed tip (after any #672 restart). Doing it
  there would need a second `integ_lock` acquisition and checkout (about 15 lines) and calls
  into `integrate`'s private `_trial` / `_own_work` from `flow`, and it would judge the wrong
  line. Inside the fold it is one keyword, one dict and a 5-line loop.
- **Reusing `held_out` / `_held_by` unchanged**: ruled out by the brief (it judges against
  the line "as the wave found it", which on a re-issue already holds `issue_10`).

## Mutation checks (each part of `_clash` pinned by a test)

Each mutant patched in memory (no files touched), the 12 cases run against it:

| Mutant | Red |
|---|---|
| M1 every other bundle is a candidate (no "own commit on the line" test) | `test_a_finished_id_held_as_well_is_never_named` |
| M2 no isolation (name on the plain base+partner trial) | 7 cases, incl. criterion (1) and both "not named" cases |
| M3 file-list isolation instead of `-X theirs` | `…_own_lines_of_a_shared_file`, `…_merges_after_it_is_named_too` |
| M4 ownership by current tips (my first rewrite) | `…_whose_branch_moved_on_since_is_named` |
| M5 no subtraction of a held bundle's own commits | `…_cut_from_anothers_branch_is_named_for_its_own_file` |
| M6 no base-alone trial first | `test_a_conflict_with_the_base_names_no_partner` |
| M7 judged at the failed merge, not at the end of the pass | `…_merges_after_it_is_named_too` |

And iteration 1's production code with this test file: 5 red, including the reversed-order
case ("…that no bundle of this batch accounts for", `issue_10` not named) and the two stacked
cases (`issue_12` dropped). Its other 2 reds are wording only.

## Known gaps (documented, not fixed here)

- Base first, as pinned: a branch that conflicts with the base and also with a partner on
  a continued line is reported as a base conflict only. After updating it from the base,
  the next re-issue names the partner.
- A commit two bundles share while neither holds the other's current tip counts for both
  (say Q was cut from `fix/P` itself and P got a fixup later): Q can be named for P's old
  change. Same accepted limit as #673 (`_undone_paths`). A bundle cut from the line (what
  publish does) is not affected.
- A conflict only several partners produce together, none alone, falls to `"line"`. Git
  judges each hunk on its own, so I could not build such a case with line edits.
- A partner named at the end of one pass can be taken off the line by a later #672 pass
  (it holds a skipped id's work). The reason still names it (its change does conflict) and
  says "finished in this batch", not "on the line"; its own line says why it is not carried.
- Which of two conflicting ids is carried is unchanged (out of scope): one already on the
  line stays, else the one asked for first.
- Cost: per conflicting id, one base trial, then per other finished bundle a few rev-lists
  and one trial (two when built on more than the base). Only on the carry's conflict path.

## Test runs (project runners, with `timeout`)

- C4, `engine/scripts/run-verify.sh` (`PDCA_BUNDLE`, `PDCA_WORKTREE`): green leg `Ran 12
  tests … OK`; red leg (production hunks reverted, test kept) `Ran 12 tests … FAILED
  (failures=12)`, all assertion failures, module loaded; `PDCA-EVIDENCE: C4 PASS`.
- T3, `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`; driver suite
  `Ran 2503 tests … OK (skipped=2)`, so every case of `test_flow_resume_stack_prereqs.py` and
  `test_flow_same_wave_conflict.py` is green (criterion 3).
- T2, `engine/scripts/run-docs-check.sh`: lint clean, render + link audit clean.
- Commit-ready: the target has no pre-commit config, hooksPath, formatter or linter config;
  CONTRIBUTING.md asks for the green offline suite and DCO sign-off (publish adds it).
  `git diff --check` is clean and no added line is over 100 columns (the 106-column line in
  `flow.py` is pre-existing). `patch.diff` is `git diff HEAD` of the worktree, reverse-applies
  cleanly, and the worktree matched it after every gate run.

## Self-refutation

- **(a) Genuine red? Yes.** C4's red leg reverts the production hunks and keeps the test:
  all 12 cases fail on their assertions, each showing the old "undeclared cross-wave overlap
  … get issue_11's PR open … `pdca publish 11`" line. Criterion (2) now fails too (it did
  not in iteration 1). Beyond the full revert, each part of the new logic was broken on its
  own (M1–M7) and each break turned at least one case red.
- **(b) Production path? Yes.** Every case drives `flow._drive_and_act` twice →
  `_carry_finished` → `_fold_lines` → `integrate.fold` → `_merge_published` / `_clash` /
  `_own_work` / `_trial`, with real git (a bare origin, a primary checkout, a scratch clone
  for the people outside the harness). Stubbed, as in the `SameWaveConflict` suite: the
  build leaf, the publish leaf (which still cuts and pushes real branches), `draft_texts`
  and `gh` (answered OPEN with the branch's real tip). The test imports modules only.
- **(c) Fixture includes the fault? Yes.** Run 1 really holds `issue_11` (asserted: the
  "held out of the integration fold" line and the end-of-run step), and before run 2 the
  test asserts `10`, `11`, `12`, `21` are COMPLETE and that `merged.pr_state` through the
  stub reports each PR OPEN with its real head, and that `21` is on no line. So the carry
  reaches the fold and the fold really fails `issue_11` on origin's continued line, which
  holds `issue_10`. Criterion (2) really moves the base and deletes every
  `pdca-integration/*` branch, then asserts the line is gone. The stacked cases assert
  `issue_12` holds `issue_10`'s commit (and, cut from `fix/10`, does not hold the line
  commit); the fixup case asserts the fixup is a fast-forward off the line; the
  other-work case pushes a real hand-made merge commit onto the line.
