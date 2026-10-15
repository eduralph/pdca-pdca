# Build notes — issue 694 / reissue-after-conflict-hold-names-the-partner (iteration 4)

Target: `eduralph/pdca-harness` @ main, built on the wave-2 stack base
`pdca-integration/main-r547f8028520f` at `a2e38fe` (672, 693 and 673 folded in), in
`$PDCA_WORKTREE`. Every `path:line` below is on that tree with this patch applied. The RED was
taken on this base: with the production hunks reverted, all 22 cases fail on their
assertions, each showing the defect line ("… does not merge cleanly onto … — an undeclared
cross-wave overlap … get issue_11's PR open … `pdca publish 11` …").

I started from the round-3 patch (`iteration-v3/patch.diff`), which applied cleanly to the
same base. Round 3 passed C1–C4 and T1–T3 and had one implementation finding (C5). This
round fixes that finding, takes one of the advisory review's small points, and adds tests that
pin the fix.

## The round-3 finding and the fix

**Finding:** 10 deletes `a.txt`; 12, built on 10, changes `b.txt`; 11 changes both. The carry
named only `issue_10`. To judge a stacked partner (12) for its own change only, round 3 merged
11 onto "base + what 12 was built on" with `-X theirs`, then merged 12. `-X theirs` settles
clashing hunks but not a clash over a whole file (one side deleted it, or both renamed it), so
the trial stopped at 11's merge and 12 was never judged.

I reproduced it first, as a test, on the round-3 code: it printed exactly the review's line
("… conflicts with issue_10's (a.txt), finished in this batch … `Conflicts with: 10` …").

**Fix:** the merge of the held branch in that trial now always completes, with the held
branch's side winning every clash, so the trial always gets to the partner's own head.

- `_merge_over` (`template/src/pdca_harness/integrate.py:1132-1169`), new. It runs `git merge
  --no-ff -X theirs` (`:1146-1147`). If that stops, it reads what is still conflicting with
  `git ls-files -u -z` (`:1150`). For each such path it removes every stage and puts back
  stage 3, the held branch's version, when there is one (`:1152-1157`). With no stage 3 (the
  held branch deleted the file, or renamed it elsewhere), the path stays gone. That goes in
  through `git update-index -z --index-info` (`:1159`) and is committed with `git commit
  --no-verify` (`:1162`): a trial commit, never pushed, so no commit hook runs on it. Then
  `_reset_tree(wt, "HEAD")` (`:1169`) makes the tree match the commit. If the merge fails
  with nothing conflicting, or a settle step fails, the tree goes back to where it was and
  this raises `IntegrationError` (`:1163-1168`). `_clash` turns that into `"line"`, which
  names no bundle (`:1240-1243`), the same as any failed trial step in round 3.
- `_trial` calls it at the `wins` index (`integrate.py:1329-1332`) and goes on. Round 3's
  `theirs=` keyword on `_merge` is gone, so `_merge` (`:1111-1129`) is back to the base's
  text.
- `_partners` (`integrate.py:1246-1271`) keeps round 3's rule. A stacked partner is named
  when its own head conflicts in that trial (`at == len(below) + 1`, `:1268`), with that
  merge's files. Its docstring now says what it does.

Before the fix, on the round-3 code, the new cases fail; after it, they pass. A probe in a
throwaway repo (`-X theirs` merge with a modify/delete both ways and a rename/rename) left
exactly the stages the settle rule expects, and the settled commit's tree was the held
branch's side for every path.

**Why the held branch's side, and why it is not new false blame:** the trial asks whether the
partner's own change (what it was built on → its head) clashes with the held branch's change.
In the trial's last merge, git's merge base is, in the usual case, what the partner was built
on. A path the partner's own commits never touched is the same on that side as in the merge
base, so it merges cleanly whatever the settle put there: a clash the held branch has only
with what the partner was built on can never name the partner. The
round-2 case (`test_a_partner_built_on_a_deletion_is_not_named_for_it`,
`template/tests/test_flow_reissue_after_conflict_hold.py:367`) still passes, now because the
trial reaches 12 and finds no clash.

## Tests added (all real git, through `flow._drive_and_act`)

In `template/tests/test_flow_reissue_after_conflict_hold.py`:

- `:385` `test_a_partner_built_on_a_deletion_is_named_for_its_own_file`: the review's case,
  as written. It asserts 12's branch really has no `a.txt`, and that the line names
  `issue_10's (a.txt), issue_12's (b.txt)` with `Conflicts with: 10, 12`.
- `:401` `test_a_partner_two_deep_on_a_deletion_is_named_for_its_own_file`: the same with a
  three-deep stack (10 deletes `a.txt`, 12 on 10 adds a file, 13 on 12 changes `b.txt`).
  Names 10 and 13, not 12.
- `:429` `…_named_when_it_changes_a_file_the_branch_deletes`: 11 deletes `a.txt`; 10 and 12
  (on 10) change it on different lines. The settle drops the file, so 12's own change to it
  conflicts. Both are named.
- `:442` `test_a_partner_that_puts_back_a_file_its_base_deleted_is_named`: 10 deletes
  `shared.txt`; 12 (on 10) writes it again its own way; 11 changes it. The settle keeps 11's
  file, so 12's copy clashes with it. Both are named. This was a known gap in round 3's notes;
  it is closed now.
- The comment on `:367` is updated (it described the old stop).

Each settle direction is pinned. I ran wrong versions of `_merge_over` in memory, with no file
changed, against all 22 cases:

| Version | Red cases |
|---|---|
| round-3 code (stop at the clash; run from an extracted copy of the round-3 tree) | `:385`, `:401`, `:429`, `:442` |
| settle keeps "ours" (stage 2) | `:429`, `:442` |
| settle keeps the merge base (stage 1) | `:429` |
| the same rule re-implemented (to check the harness) | none |

## Advisory point taken

`_built_on` now works out "built on" only for the bundles a partner is looked for among: the
ones the fold carries and the ones a later pass took back off (`integrate.py:646-649`;
`names`, `:1274-1306`). Round 3 did it for every bundle with a head in the clone, with a
`git merge-base` per pair. Every bundle's own-commit walk is still computed (`:1294-1295`),
because "less the own commits of each bundle whose head it holds" needs them. That keeps the
result for the bundles looked up the same.

Not taken, both left as the advisory review called them (cosmetic or "no action needed"):
- With a red re-gate, a `"batch"` line still names a partner that the run then does not
  carry. The step is still right for the conflict.
- A partner that does not merge onto the current base by itself (`at == 0`, `:1263`) is
  not named. The id falls back to `"line"`. It is safe, but the advice is weaker.

## Other shapes probed (not shipped)

These were run through the same flow and fixture, as throwaway cases:
- 10 renames `shared.txt` to `moved.txt` and changes line 2; 12 (on 10) changes `moved.txt`
  line 8; 11 changes `shared.txt` lines 2 and 8. Output: `issue_10's (moved.txt),
  issue_12's (moved.txt)`. With 12 adding only a file of its own: `issue_10's (moved.txt)`
  only. Both are right. Round-3 code gives the same here (no whole-file clash), so this does
  not pin the fix, and I did not add it.

## How the partner is found (the brief asks for this; unchanged from round 3 but the settle)

In `integrate.fold`, in `skipped` mode, and only when the caller passes `clashes` (only the
carry does, `flow.py:1180-1185`), a bundle whose merge raises `_Conflict` is recorded: its
head, the files (`_Conflict.paths`, `integrate.py:99-107`), and what was on the line then
(`:605`). After the last pass, each such id not held for another's work (`:641`) is judged
by `_clash` (`integrate.py:1199-1243`) on the line the fold pushes:

1. **Base first** (the brief's pinned rule): its head onto `<base_remote>/<base>` alone. A
   conflict gives `"base"`: no bundle named, that trial's files (criterion 2).
2. **Carried partners**: each bundle the line carries (`took`, merge order: merged by this
   fold before it or after, or already on origin's line) for which its head does not merge
   onto base + that bundle's head. A bundle built on more than the base must also clash in
   its own change: base + what it was built on, then the held branch with its side winning
   every clash (`_merge_over`), then its head. Any named gives `"batch"`, each with its files.
3. **The pushed line**: its head onto that line. A conflict gives `"line"`: no bundle named.
4. **Taken back off**: if it merges there, `"off"` with the bundles that were on the line
   then and a later pass took off, each named only by the step-2 rule. If none was taken off,
   the result is `"moved"`: a plain re-issue.

The flow words each one and picks the hint (`_clash_why`, `flow.py:1029-1058`; hints
`flow.py:1007-1026`). The `"batch"` step is `_CONFLICT_STEP` (`flow.py:1004`). It is the one
string the end-of-run line uses too (`_report_conflict_holds`, `flow.py:1263-1272`), so run 2
gives run 1's step word for word. Criterion (1)'s test takes the step from run 1's stderr
and asserts it in run 2's line (`test_flow_reissue_after_conflict_hold.py:210`).

## Ruled out, with costs

- **Settling with porcelain per path** (`git checkout --theirs` + `git add`, or `git rm
  --cached`, as round 3's notes sketched). `checkout --theirs` fails on a path with no stage
  3, so it needs one branch per kind of path, and it writes the tree before the commit. With
  `update-index --index-info` it is one call for every kind of entry (file, symlink,
  submodule), and the tree is touched only by the reset after. It is about the same size
  (the settle is 13 code lines, `integrate.py:1150-1162`).
- **A "keep" mode on `_merge`** (round 3's sketch: skip `_reset_tree` on failure, about +3
  lines in `_merge` plus about +11 in `_trial`). That spreads trial-only behaviour through
  the merge every real fold uses. `_merge_over` is a separate function that only `_trial`
  calls: `_merge` ends up byte-identical to the base.
- **`git merge-tree --write-tree -X theirs`** (no tree touched). For a modify/delete it keeps
  the modified side whichever side that is, so "the held branch deleted it" would still need a
  temporary index (`read-tree`, `update-index`, `write-tree`, `commit-tree`: four more git
  steps). The brief also pins a trial merge in the carry's worktree.
- **Per-file attribution** (name a partner when its own commits touched a conflicting file).
  It names a stacked partner that changed other lines of the same file. That would turn
  `test_a_partner_built_on_another_is_not_named_when_its_own_lines_merge` (`:355`) red.
- **Leave one out** (take one partner's merge off the line and retry). When two partners clash
  in one file, taking either off still leaves a conflict, so neither is named.
- **Keeping round 3's "not named when the trial cannot reach it"**. That is the rejected
  approach: it drops a real partner, as the review showed.

## Known gaps (documented, not fixed here)

- Base first, as the brief pins it: a branch that clashes with the base and with a partner is
  reported as a base conflict only. Once it is updated from the base, the next re-issue names
  the partner.
- When no single partner reproduces the conflict but several together do, the carry says
  `"line"` (no id named). In the same case, #674's in-run hold names all bundles merged before
  it (`_held_by`, `integrate.py:1172-1196`). That is rare (it takes git's hunk grouping),
  and the carry's line is still true ("no other finished bundle … was found to account for").
- In the `"batch"` kind, a conflicting file that no named partner accounts for (say, hand-made
  work on the line as well) is not listed.
- A partner whose own trial cannot run (what it was built on does not merge onto the base, or
  a settle step fails as a git step) is not named, or the id falls back to `"line"`. Neither
  blames a wrong bundle.
- A trial merge in a clone with `rerere` set to stage its resolutions would report no
  conflicting path. That is true of the existing `_merge` too.
- Carried from round 3: a carried partner hides a taken-off one; `"off"` counts every bundle
  taken off that was on the line then; a commit two bundles share while neither holds the
  other's tip counts for both (same accepted limit as #673); which of two conflicting ids is
  carried is unchanged (out of scope).
- Cost: per conflicting id, one base trial, then one or two trials per carried bundle (each
  stacked one's trial now always runs to its end), maybe one on the line, and one or two per
  taken-off bundle. All of it runs only on the carry's conflict path.

## Test runs (project runners, each under `timeout`)

- C4, `engine/scripts/run-verify.sh` (`PDCA_BUNDLE`, `PDCA_WORKTREE`): green leg `Ran 22
  tests … OK`; red leg (production hunks reverted, test kept) `Ran 22 tests … FAILED
  (failures=22)`. All 22 are `AssertionError`s carrying the base's "cross-wave overlap"
  line; none is a load or import error. `PDCA-EVIDENCE: C4 PASS`. After the gate, `git diff
  HEAD` of the worktree is byte-identical to `patch.diff`.
- T2, `engine/scripts/run-docs-check.sh`: `lint_docs: OK`, 22 pages rendered, `link audit
  OK`.
- T3, `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`; driver suite `Ran 2513
  tests … OK (skipped=2)` (round 3 had 2509; the four new cases make 2513). So every case of
  `test_flow_resume_stack_prereqs.py` and `test_flow_same_wave_conflict.py` is green
  (criterion 3). `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- C5, `engine/scripts/run-prod-path.py`: the added test imports `pdca_harness`.

## Self-refutation

- **(a) Genuine red? Yes.** C4's red leg reverts the production hunks and keeps the test: 22
  of 22 fail on assertions, none fails to load. Against the round-3 production code, the four
  new or changed cases fail (`:385`, `:401`, `:429`, `:442`) and the other 18 pass. The
  review's case fails there with the review's exact wording. Each wrong settle direction
  turns at least one case red (table above).
- **(b) Production path? Yes.** Every case drives `flow._drive_and_act` → `_carry_finished` →
  `_fold_lines` → `integrate.fold` → `_merge_published` / `_clash` / `_partners` /
  `_built_on` / `_trial` / `_merge_over`, with real git: a bare origin, a primary checkout,
  and a scratch clone. The stubs are the `SameWaveConflict` ones (build leaf, publish leaf
  that cuts and pushes real branches, `publish.draft_texts`) plus the `gh` stub answering
  OPEN with the branch's real tip. The test imports modules only.
- **(c) Fixture includes the fault? Yes.** The review's case asserts 12's pushed branch has no
  `a.txt`, so the deletion it inherits is really there. The re-add case asserts the line 12
  was built on has no `shared.txt`. The three-deep case asserts 10 ⊂ 12 ⊂ 13 by ancestry.
  Every stacked case asserts 20 stays PLANNED and unbuilt, and each finished id is COMPLETE
  with an OPEN PR at its real head before run 2.

## Commit-ready

The target has no pre-commit config, no `core.hooksPath`, no installed hooks (only git's
samples) and no formatter or linter config. Its CI workflows are docs-check, docs,
render-check, require-linked-issue and triage-new-issue. `CONTRIBUTING.md` asks for DCO
sign-off (publish adds it) and green suites (T3). `git diff HEAD --check` is clean, and no
added line is over 100 columns. `patch.diff` is `git diff HEAD` of the worktree (the new test
is marked intent-to-add) and reverse-applies cleanly.

## Process notes

- I wrote one file outside the allowed roots: `/tmp/pdca-694-c4.out`, the output of the C4
  run, kept so I could count the red leg's assertion errors. It holds gate output only. I did
  not delete it; cleanup is the harness's job. Every other run piped its output directly.
- Throwaway repos for the git probes and the round-3 comparison were Python
  `TemporaryDirectory`s inside the worktree, removed by Python when each probe ended. The
  worktree's `git status` shows only the four patched files.
- A first try at the round-3 comparison ran the base code by mistake: `git apply` inside a
  folder of the worktree skips paths outside that folder without a word. I re-ran it with
  `GIT_CEILING_DIRECTORIES` and checked that the copy really held round-3's `_partners`.
