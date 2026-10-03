# Build notes — issue 593, iteration 4 (stack-mode-append-only-fold-real-base-prs)

Target: eduralph/pdca-harness @ main, base commit `24c7f83`. Worktree:
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`. Line numbers are in the patched tree unless
marked "base".

## Starting point

The iteration-3 sign-off keeps the design (real-base PRs, append-only fold of the real PR
commits, hold dependents of an unpublished bundle) and says "rebuild only to fix these".
So I applied `iteration-v3/patch.diff` (it applies cleanly to `24c7f83`) as the starting
point and changed only what the carry-forward names. That patch is the one thing past
`brief.md` I read, because the carry-forward points at it and asks for fixes to it. I did
not read the v3 SUMMARY, review or check files. Before changing anything I ran the four
touched test modules on the v3 code: 170 tests, all green.

## Item 1 — a merged prerequisite whose branch is gone dropped off a continued line

Reproduced first, on the v3 code, with the new regression test
(`template/tests/test_integrate_stack_bases.py:309-330`): fold A, publish B from the tip,
merge A and B into origin's `main` with merge commits, delete `fix/B`, fold `[A, B]` with
`folded_this_run={TARGET: t1}`. Result on v3: `fatal: path 'b.txt' does not exist in
'<new tip>'` — B's work never reached the line, so the next wave would build without it.

Fix: `_merge_published` (`template/src/pdca_harness/integrate.py:369-395`) now calls
`_take_in_base` (`integrate.py:398-415`) when the branch is gone and `merged.is_merged`
says the PR merged. Its work is in the base, so if `<base_remote>/<base>` is not already
an ancestor of the line, the base is merged in with a signed-off merge commit
(`pdca-integrate: origin/main (carries merged issue_B)`). The merge sits on top of the
line, so the push is a fast-forward: unforced, accepted by a `denyNonFastForwards`
origin, and no commit an open PR depends on is rewritten. On a line that started fresh
from the base (the common case: the run's first fold) the base is already an ancestor,
so nothing changes there.

The regression asserts `b.txt` is on the new tip, `t1` and origin's `main` are ancestors
of it, and no push carried `--force`, against an origin with
`receive.denyNonFastForwards true`. With the call put back to v3's skip-only behaviour
(probe at `integrate.py:377`, since undone) it fails with the same "b.txt does not exist".

Options weighed:

- (A, chosen) merge the fetched base into the line: `_take_in_base` is 18 lines.
- (B) record each pushed branch tip's SHA in `publish.json` and merge that SHA when the
  branch is gone. It needs a new field in both publish records (base `publish.py:382-388`
  and `:502-507`), a fallback for records written before the field existed, and the
  objects are only fetchable through some other ref anyway. After a merge-commit merge
  that ref is the base, so (B) ends up fetching the same base for more code (~15 lines
  in publish.py plus the fallback path in integrate.py).
- (C) stop the run: brief (iv) says a gone branch whose PR merged is skipped, not a stop.
- (D) merge the base at the start of every continued fold: it would join every later
  wave's line to a newer base even when nothing needs it, which makes the several-merge-
  bases case of (v) the normal case for all later PRs. Rejected for a rare event.

On the invariant ("within one run only that run's work enters its integration line"):
the base merge brings target-base commits onto the line. They are not another run's
integration-line commits (the #591 tip guard at `integrate.py:336-344` is unchanged), and
the run's first fold already starts from that same base. I flag it so sign-off can judge
it.

## Item 2 — the diff-shrink docs overclaimed

Rewrote (v) in the five places named: `template/PCDA/quality-cycle/09-parallel-lanes.md:69`,
`docs/07-crosscutting.md:648-657` (base `:642-647`), `integrate.py:15-27`,
`publish.py:247-258`, `template/PCDA/quality-cycle/08-glossary.md:290-298` (base
`:289-295`). The rule now says: the fold puts every published branch of a target on its
line, so a later wave's PR carries **every earlier-wave branch on the line**, not only its
prerequisites', and shows their changes until they merge (09 adds: merging it first
would land their commits with it). Once they have all merged with merge commits, its
diff is its own change when the line is a plain chain — one branch per earlier wave, and
no base newer than a branch on it taken in (the base did not move between the wave-0
publishes and the first fold, and no fold merged the base in, which item 1's path does).
Otherwise a fold merge commit joined histories the base got separately, the PR has
several merge bases with the base, and "Update branch" leaves only its own change.

How I checked the rule (commit graphs, B0 = base):

- Chain A→B→C→D, base unmoved, merged in order: the best common ancestor of `main` and D
  is C's tip alone, and the fold's merge onto C's tip has C's tree, so `main...D` is D's
  change only. (This is what `:406-412` pins for two waves.)
- One wave with two branches A, Z: after both merge, A's and Z's tips are both best
  common ancestors (neither contains the other). Two merge bases.
- Base moved to B1 before the first fold: B1 and A's tip. Two merge bases (`:429-449`).
- Item 1's base merge, chain A→B→C→D, A merged and its branch deleted before fold 3: D's
  line holds the base merge M(L2, MA'); after B and C merge, C's tip and MA' are both
  best common ancestors. Two merge bases — hence "no fold merged the base in" in the
  plain-chain condition.

Pin for the sign-off's case: `template/tests/test_flow_slice.py:1596-1627`, flow-level
with the real fold and a real origin. Wave 0 = {ZA, ZZ}; ZB's brief says `Depends on: ZA`
only. Asserts ZZ's own commit is in ZB's branch, `main...ZB` shows ZZ's file until ZZ
merges (still shown after only ZA merged), `merge-base --all main ZB` is ZA's and ZZ's
tips once both merge, and after "Update branch" only ZB's file. I kept it at flow level
(not as an extra assertion on the integrate-level sibling test, which would save ~3 KB)
because only there is "ZB depends on ZA alone" real: `fold` itself never sees
`Depends on`. On the base code it fails (ZZ's commit is not in ZB's branch: the old fold
re-applied patches); on v3 it passes, as expected for a pin of docs about v3 behaviour.

The test module docstring (`test_integrate_stack_bases.py:1-19`) was updated to match.

## Item 3 — the end-to-end test passed with "fresh + --force" every fold

Why v3's version passed: a fold that rebuilt the line from the base merges
`fix/issue_EA` again as a new merge commit, then merges `fix/issue_EB`, which descends
from the old tip. So the old tip is an ancestor of the new one and even the forced push
is a fast-forward that `denyNonFastForwards` accepts; every v3 assertion still holds. And
if both folds run in the same second, the re-made merge commit is byte-identical to the
first, so a merge-count check alone could also pass by chance.

Now (`test_flow_slice.py:1548-1594`): each fold runs under its own
`GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` (a `dated_fold` wrapper around the real fold), and
the test asserts exactly one `pdca-integrate: issue_EA` merge commit on origin's line,
exactly two pushes, `--force` on the first only. Mutation check: with `integrate.py:299`
changed to `start = "fresh"` (every fold rebuilt and forced; undone since), it fails with
`AssertionError: 2 != 1 : ['pdca-integrate: issue_EB', 'pdca-integrate: issue_EA',
'pdca-integrate: issue_EA']`.

## Optional code-review items (both done)

- Conflict vs other merge failure: `_merge` (`integrate.py:431-444`) returns the paths
  left unmerged (`git diff --name-only --diff-filter=U`) when a merge fails, and aborts
  it. `_merge_published` reports "does not merge cleanly onto … (conflicts in …) — an
  undeclared cross-wave overlap" only when paths conflict; otherwise "`git merge` exited
  N with no conflicting path … a git step failed (not an overlap)" (`integrate.py:387-395`).
  Tests: `:368-392` (a real "refusing to merge unrelated histories", exit 128) and
  `:394-404` (a real conflict names `base.txt`). With every failure forced back to the
  overlap message (probe, undone) the first test fails. Both ancestry checks (bundle
  branch, and item 1's base) go through `_in_line` (`integrate.py:418-428`), which keeps
  v3's rule that exit 128 is a failed git step.
- `"stacked"`-record fallback: `_published_ref` (`integrate.py:105-123`) returns None for
  a `"stacked"` record whose `base` is not `<remote>/<branch>`, instead of guessing the
  remote from the first path segment. The flow then holds it and the fold refuses it.
  `publish._publish_stacked` always writes `base = f"{remote}/{branch}"` (base
  `publish.py:429`, `:502-507`), so only a hand-edited or corrupt record gets here. Test:
  `:624-633`; with v3's guess put back (probe, undone) it fails `[] != ['issue_BAD']`.

## Size

Final `patch.diff`: 126,677 bytes = 123.7 KiB, under this instance's
`[driver.size_signal] patch_kb = 125` (computed as bytes/1024). My first cut was 126.6 KiB.
I got under by shortening docstrings and comments — mine from this round, plus some long
v3 ones in `integrate.py`, `flow.py` (`:1686-1691`, `:1858-1862`) and the test module
docstring — not by dropping any test. Rounds should count 2 (v2, v3 since the v1 re-plan),
under `rounds = 3`.

## Gates run with the project's runners

- C4 `engine/scripts/run-verify.sh` (PDCA_BUNDLE + PDCA_WORKTREE set): `PDCA-EVIDENCE: C4
  PASS — red without the fix, green with it`. Green leg: 29 / 106 / 14 / 26 tests OK
  (test_flow_adopt_split, test_flow_slice, test_integrate, test_integrate_stack_bases).
  Red leg: test_flow_slice 7 failures, test_integrate 1 failure,
  test_integrate_stack_bases 17 failures + 7 errors. The 2 cases that pass on both legs do
  so by design (`test_the_fork_path_is_unchanged`, `test_a_legacy_stacks_on_parent_keeps_its_branch_base`).
  The worktree was restored afterwards (its diff equals `patch.diff` byte for byte).
- T2 `run-docs-check.sh`: docs lint clean, site render + link audit clean. The host-CI
  row (`run-host-ci.sh`) runs the same two checkers.
- C5 `run-prod-path.py`: "1 added driver-suite test(s) import the production package
  'pdca_harness'".
- T3 `run-suite.sh`: root suite 24 tests OK (copier cases ran, none skipped); driver suite
  2249 tests OK (2 skipped, pre-existing). `PDCA-EVIDENCE: root suite OK, driver suite OK`.

## Refuting my own tests

(a) Genuine red? Yes. The C4 gate reverted the production hunks and the touched modules
went red (counts above), with no import failure (the new module imports only
`integrate, publish, signoff`, which exist on the base). For this round's items I also
reverted each fix alone on top of the final code: item 1 (skip-only) → the regression
fails on the missing `b.txt`; item 3 (fresh + force every fold) → the e2e test fails
`2 != 1`; optional (a) → the unrelated-histories test fails; optional (b) → the malformed
record test fails. The item-2 pin fails on the base and passes on v3, as a docs pin should.

(b) Production path? Yes. Every case calls the real `integrate.fold` (or the real
`flow.flow_ids` driving the real fold) against real git: a bare origin with
`receive.denyNonFastForwards true`, a primary checkout, real merges by a second clone.
What is replaced: `merged.is_merged` (it shells `gh`, no network here), the Do/Check drive
(`_drive_wave` accepts each bundle with a real patch) and the publish step (a stand-in
that cuts, commits signed off and pushes the branch the way publish does and writes the
same `publish.json` shape). Those are inputs to the code under test, not the code under
test.

(c) Fixture includes the fault? Yes. Item 1's fixture really merges A and B into origin's
`main` and really deletes `fix/B` on origin before the continued fold, and the primary
keeps a stale tracking ref (`fetch.prune false`), so the fold's own `--prune` is what makes
the branch disappear. Item 3's fixture has origin refusing non-fast-forwards, and distinct
commit clocks so a rebuilt line cannot hide behind an identical commit. The item-2 fixture
has a real unrelated wave-0 sibling (ZZ) on the line.

## Commit-ready

The target configures no formatter or linter (no pre-commit config, no ruff/black config;
CONTRIBUTING.md asks for DCO sign-off and green suites). Its PR CI is docs-check.yml (the
T2 / host-CI checkers, green), render-check.yml (the T3 root suite, green) and
require-linked-issue.yml (the publisher's PR body). No added Python line is over 100
columns, the width the surrounding code uses.

## Known limits, for sign-off

- A gone branch whose PR merged somewhere other than the target base (an `Onto branch`
  PR merged into its own base, or a PR an older version opened against an integration
  branch): merging the target base cannot bring that work, yet the fold prints that it
  reaches the line through the base. Brief (iv) defines gone + merged as "its work is in
  the base", and retargeting older PRs is out of scope.
- `merged.is_merged` shells `gh` without a guard, as `merge.py:200` does; a host without
  `gh` would raise FileNotFoundError out of the fold. `gh` is a required doctor row here.
- Carried from the brief, still owed at sign-off: the live-host check on a disposable
  GitHub repo (External dependencies), the vendored-spec edits to 09 and 08 (NEEDS-HUMAN
  by INTEGRATION §4), and confirming (iv)'s hold policy.
