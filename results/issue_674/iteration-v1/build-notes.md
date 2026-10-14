# Build notes — issue 674 / same-wave-conflict-holds-one-bundle-not-the-run

## Base

The worktree (`$PDCA_WORKTREE`) is the stack base `pdca-integration/main-r8bf6d15b2de3` at
`420f8b4`, which already holds #605, #629, #633, #651 and #658 on top of the brief's
`41210bc`. So line numbers move from the brief's: `held_unpushed` is `flow.py:2162` here (the
brief says `:2134`), the fold call is `flow.py:2382-2392` (`:2339-2346`), the `_runnable`
call is `flow.py:2250` (`:2209`), `_warn_stranded_split_children` is called at `flow.py:2416`
(`:2370`), and the fold's merge loop is `integrate.py:489-502`. Every "base" line below is on
`420f8b4`; every "after" line is in the patched worktree. `patch.diff` applies to that base
(it does not apply to plain `origin/main`, since #633's `carried=` lines are part of its
context).

## What changed

**`template/src/pdca_harness/integrate.py`**

- `_Conflict(IntegrationError)` (after: `:92-99`): carries the conflicting `paths`. Raised by
  `_merge_published` in place of the plain `IntegrationError` for a textual conflict (base
  `:585-589`, after `:630`). Same message, same base class, so every existing catch and
  `assertRaises(IntegrationError)` still matches.
- `fold(..., held_out=None, wave=())` (after `:309-310`, docstring `:395-407`). In the merge
  loop (base `:489-502`, after `:517-546`):
  - `pre` = the line tip just before the first bundle of `wave` is merged (after `:523-528`).
  - `kept` = the bundles of `wave` merged so far, with their heads (after `:519`, `:545-546`).
  - When a bundle of `wave` fails with `_Conflict`, at least one bundle of `wave` is already
    kept, and `_held_by` names partner(s), the bundle is recorded in
    `held_out[name] = (partners, paths)` and the loop goes on (after `:532-538`). Any other
    failure takes the existing path: raise, or `skipped` for the carry.
- `_held_by` (after `:886-898`): first a trial merge of the failed head onto `pre`. If that
  conflicts too, the bundle clashes with earlier-wave work → returns `[]` → the fold raises
  as before. Otherwise it tries `pre` + each kept bundle + the head, one kept bundle at a
  time, and returns those that conflict. If none conflicts alone (the clash is only with
  several of them together), it returns all kept bundles.
- `_trial` (after `:901-929`): merges on a **detached HEAD** at `onto`, so the line's branch
  ref never moves. It reuses `_merge` (base `:821-839`), which already resets a failed merge
  with `_reset_tree`. In `finally` it runs `_reset_tree(wt, "HEAD")`, checks the branch out
  again and checks HEAD is back at the tip it had. If not, it raises `_LineBroken`, which
  stops even under `skipped`. A merge that fails with no conflicting path raises (a failed
  git step, never read as "conflicts"). It runs inside `fold`'s `integ_lock` scope (base
  `:449-458`), which the brief requires.
- Module docstring (base `:51-53`, after `:51-55`) now names the held case.

**`template/src/pdca_harness/flow.py`**

- `_fold_lines` passes `held_out` / `wave` through (base `:815-839`, after `:820-821`,
  `:834-837`, `:845`).
- `_drive_and_act`: a new run-wide `held_conflict` dict (after `:2199-2202`), next to
  `held_unpushed`, following the peer pattern the brief cites.
  - It is added to `_runnable(held=…)` (base `:2250`, after `:2290-2291`), so `20` gets
    `_runnable`'s existing "skipped — prerequisite(s) not ready (11)". The brief accepts that
    wording.
  - It is left out of every fold's bundle list (base `:2385-2388`, after `:2430-2434`), so
    the hold lasts the whole run.
  - The fold gets `held_out=None if dry else held_conflict` and
    `wave=[d.name for d in complete]` (this wave's accepted bundles).
- `_announce_conflict_holds` (after `:1061-1071`) prints one line per new hold right after
  the fold, before the next wave's `_runnable` / `_drive_wave`. It also prints on the
  `IntegrationError` path, before "STOPPING", so a hold found before a later stop is not lost
  (after `:2435-2442`).
- `_report_conflict_holds` (after `:1074-1083`) is called right after
  `_warn_stranded_split_children` (base `:2416`, after `:2467-2468`). It repeats the pair and
  the files, and proposes "declare `Conflicts with: <ids>` in <name>'s brief, then rebuild
  <name> on a base that holds <partners>". It writes no brief.
- `_runnable` docstring: the `held` sentence now covers a conflict-held prerequisite (base
  `:693-696`, after `:693-697`). The message text is unchanged, per the brief.

**Docs** (the reference model and the user doc both said any branch that does not merge
cleanly stops the run, which is no longer true):

- `template/PCDA/quality-cycle/09-parallel-lanes.md:69`: one inserted clause.
- `docs/07-crosscutting.md:696-705` (after): a new paragraph after the held-bundle text.

**Test** `template/tests/test_flow_same_wave_conflict.py` (new; a copy is in this bundle
under `template/tests/`). It imports only modules and loads `StackFoldGit` by path, as the
peer does (`test_flow_resume_stack_prereqs.py:34-39`).

| Test (line) | Criterion |
|---|---|
| `:180` same wave conflict holds the later bundle, run goes on | (1) + (2), the exact batch of the brief (10, 11, 12 / 20→11, 21→12 / 30→21) |
| `:227` shared file that merges cleanly holds nothing | (3) |
| `:251` three-way chain: only 41 is held, partner 40 | (4) |
| `:276` a hold leaves the integration tree clean on the line | the brief's `_reset_tree` / lock requirement |
| `:298` a conflict with earlier-wave work still stops the run | the Invariant's "the fold still stops on it, as today" |

For (2), "before the next wave builds" is checked by snapshotting stderr inside the build stub
when `21` starts building (`err_at`). "At the end of the run" is checked on the stderr after
`30`'s build started.

## Why this shape (and what I ruled out)

**Reuse of the fold, not a second merge path.** The brief points at #646's `skipped=` mode. I
reused the loop it lives in (the same sequential, merge-in-order, undo-and-go-on pass), but
not `skipped` itself:

- `skipped` swallows *every* per-bundle `IntegrationError` except tree/line errors. That
  includes a gone branch whose PR is not merged, and "git merge exited N with no
  conflicting path". Those must still stop.
- `fold` pushes before it returns. If the flow classified `skipped` afterwards, an
  earlier-wave conflict would be found only after the line was pushed without that bundle.
  That is not "the fold still stops on it, as today" (today it raises before any push,
  `integrate.py:496-498` base).
- The "merges onto the line without them" test needs `pre`, the line tip before the wave's
  first merge. Only the fold's loop knows it.

Sketch of the rejected `skipped`-as-is route: in `flow.py` ~25 lines (pass `skipped`, then,
per skipped name of this wave, re-open the integration worktree under `integ_lock`, find
`pre` by walking the line's first-parent chain back past this wave's merge commits, trial-
merge, and on an earlier-wave conflict print STOPPING), and it still pushes before the stop.
What I did instead: +20 lines in the fold loop (`integrate.py:517-546` after) plus +45 for
`_held_by` / `_trial` (`:886-929`). It raises before any push in the stop case, and keeps
`skipped` exactly as the carry uses it.

**`git merge-tree --write-tree` (git ≥ 2.38) rejected.** It would test merges without touching
a worktree. But the harness states no minimum git version, and the brief makes adding one a
sign-off question. `_trial` uses only `checkout --detach`, `merge`, `reset --hard`,
`clean -ffd` and `checkout`, all of which the fold already runs. **No new git feature or
version is required.** (Local git here is 2.53.)

**Naming the partner by trial merges, not by shared files.** The cheaper rule ("kept bundles
whose change touches a conflicting path") costs no extra merges. But it names the wrong
partner when two kept bundles touch the same file in different places. Example: 10 edits
line 1, 11 edits line 9 (clean with 10), 12 edits line 1. File overlap names 10 *and* 11 for
12, and the end-of-run line would then propose `Conflicts with: 10, 11`. That is wrong for 11.
Cost of the exact rule: per held bundle, 1 + |kept| trial merges (each about 6 git calls). A
wave of n bundles is at most O(n²) trials, and they only happen on a conflict, which used to
stop the run.

**Hold entries are recorded as soon as they are found,** not after the target's push (as
`carried` is). If a later bundle then stops the fold, the flow still names the hold it found
before "STOPPING", and the end-of-run line repeats it. The conflict is real either way.

**Tie-break** = the fold's merge order = name sort (`flow.py:2313` base, `integrate.py:301-302`
base). As the brief says, this departs from "lower id" only across digit counts
(`issue_100` < `issue_99`). The human confirmed this at plan sign-off.

## Not done / possible follow-ups

- A bundle that declares `Conflicts with: <held bundle>` is not held. #629 holds such
  partners of a *pushed-no-branch* bundle (`_runnable(unpushed=…, conflicts=…)`, base
  `flow.py:2252-2254`), but its stderr line says the bundle "pushed no branch this run",
  which would be false here. The brief scopes the hold to dependents through `_runnable`. If
  wanted, it is one more set passed to `unpushed=` plus a message branch in `_runnable`, the
  code 629 owns.
- Final wave: no fold runs, so a same-wave conflict in the last wave is still not detected.
  That is unchanged and in scope only "where a fold runs".
- The stop message for an earlier-wave conflict still says "an undeclared cross-wave overlap".
  That is now accurate for the only case that reaches it. Rewording it is out of scope.

## Red → green (project runner)

Run through the C4 gate, `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`
(from the pdca-pdca root, under `timeout`):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_flow_same_wave_conflict.py
Ran 5 tests in 0.954s
OK
== C4 red leg: bundle test(s) with the production change reverted
ERROR: test_a_hold_leaves_the_integration_tree_clean_on_the_line … TypeError: fold() got an unexpected keyword argument 'held_out'
FAIL: test_a_same_wave_conflict_holds_the_later_bundle_and_the_run_goes_on … 'did not integrate' unexpectedly found … "flow: wave 0 did not integrate (issue_11's branch origin/fix/11 does not merge cleanly onto pdca-integration/main-r8d76d16d53ea (conflicts in shared.txt) …); STOPPING — later waves not run."
FAIL: test_of_a_three_way_chain_only_the_bundle_that_conflicts_is_held … "flow: wave 0 did not integrate (issue_41's branch origin/fix/41 does not merge cleanly … (conflicts in chain.txt) …); STOPPING"
Ran 5 tests in 0.671s
FAILED (failures=2, errors=1)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The (3) and earlier-wave-stop cases pass on both legs. The brief expects that: they guard
against holding on file overlap alone and against swallowing an earlier-wave conflict.

Full suites through the T3 runner (`./engine/scripts/run-suite.sh`): root 24 tests OK,
driver 2447 tests OK (2 skipped). Docs through the T2 runner (`run-docs-check.sh`):
`lint_docs: OK`, `render_site: link audit OK`.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** The C4 red leg reverts only the production hunks (`git apply -R
  --exclude=tests/*`) and keeps the test. Two cases fail on assertions, with the real pre-fix
  stop text from git ("wave 0 did not integrate … conflicts in shared.txt … STOPPING"). The
  fold-level case errors (`fold()` has no `held_out` before the fix). It still ran (5 tests
  counted), so it is not a load failure.
- **(b) Production path? Yes.** The flow cases call `flow._drive_and_act` with the publisher
  in `command` mode, so `integrate.fold` → `_merge_published` → `_held_by` / `_trial` run
  against real git: a bare `origin`, the primary checkout, and the real integration
  worktree, pushed for real. Stubbed: the build and sign-off leaves (`flow._drive_wave`),
  `publish.draft_texts`, `flow._publish_bundle` (replaced by a real git cut-commit-push from
  the recorded line tip, the fixture's `_publish`), and `gh`. None of those is code this fix
  changes. The fold-level case calls `integrate.fold` directly.
- **(c) Fixture includes the fault? Yes.** `10` and `11` are real branches, cut from the same
  base commit, that set the same line of `shared.txt` (committed on `main` first) to
  different text. Git itself refuses the merge: the red-leg output above is git's own
  conflict list. Case (4) uses a real nine-line `chain.txt` with the 40/41/42 line edits from
  the brief. Nothing is curated out: all six (or four) bundles are in the batch and driven.

## Commit-readiness

The target repo has no formatter, linter config or installed git hooks (`git rev-parse
--git-common-dir`/hooks has only samples; no `.pre-commit-config.yaml`; CONTRIBUTING.md
names only DCO sign-off and the offline suite). Every added line is ≤ 100 columns (the
existing files' width). Docs lint is clean. The DCO `Signed-off-by` belongs to the publish
commit, not the patch.

## Process slip (for the human)

I sent one full-suite log to `/tmp/claude-674-suite.log`, which is outside the worktree and
bundle roots. It holds only test-runner output. I did not delete it, because cleanup is the
harness's job. All later runs printed to the console only.
