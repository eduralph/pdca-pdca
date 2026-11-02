# Adversarial review: issue 626

I could not refute the red→green evidence or criteria (a)–(e). I did find one false message in the new code, a second narrow revert problem, and two places where the result falls short of the brief's wording.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:853` says "so {base} has the PR's work", but the check behind it (`integrate._squash_merged`) only shows that the merge commit is an ancestor of the base. Failing case, which I ran: P has an `Onto branch` record, is squash-merged, and the squash commit is then reverted on main. `main` holds only `base.txt`, yet D's line reads "so main has the PR's work ... To build it, drop issue_P from issue_D's brief". A user who follows that would have D built on a base without P's work. Before the patch this D stayed held with no such advice. Fix: say the PR was merged into the base, not that the base has its work, and add this revert case as a test.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:1370` and `template/src/pdca_harness/integrate.py:1480`: after a squash merge that was later reverted, the "Update branch" step keeps the reverted change. Failing case, which I ran: P is squash-merged and reverted on main, and Q is updated from main as its line says. `fix/Q` still holds `p.txt`, so Q's PR would land P again. `pdca flow Q D` then carries Q with no warning, and D reaches COMPLETE. With a merge commit, the same steps remove `p.txt` from `fix/Q`. The shape is narrow, and the ancestry check cannot see a revert. A human should decide whether to document this limit or handle it.

- NEEDS-HUMAN [human] — `brief.md:40` says a squash-merged prerequisite "**holds** its dependents until they are updated from the base", but the update has no effect on the hold. Only naming P in the command does. I ran both directions:
  - Update Q and re-issue `P, Q, D`: Q and D are still held.
  - Never update Q and run `Q, D`: Q is carried and D reaches COMPLETE, with no read of P's merge commit and no mention of the squash merge. `fix/Q` lacks the squash commit, and its PR keeps showing P's change.

  So someone who leaves an already merged P out of the command, which seems the likely thing to do, never sees the new recognition. `template/tests/test_stack_squash_merge.py:1187` pins this and `docs/07-crosscutting.md:824` states it, so it is deliberate and criterion (c) still passes as written. It does differ from the brief's design text. A human should choose: accept and correct that wording, or make a run check that a dependent holds the merge commit.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/publish.py:848` warns only when a brief names the bundle, but `brief.md:9` (Goal 1) and `brief.md:37` (Design 1) also promise a warning for a PR that "a later wave" builds on. `docs/07-crosscutting.md:698-700` says the fold puts every published branch on the line, so a later wave's PR carries branches it never named. Failing case, from reading the code and not run end to end: in batch `X, P, D`, D `Depends on` P and nothing names X. X's publish gives no warning, although D's PR carries X's commits. If X is squash-merged and its branch deleted, the fold stops on X. `template/tests/test_stack_squash_merge.py:338` shows a stop like this on a bundle no brief names. Criterion (d) and the test at `template/tests/test_stack_squash_merge.py:200` require this silence, so the brief contradicts itself here. A human should decide which wording wins.

## Attempts that did not refute the fix

- **Red→green evidence:** the proof holds. On a copy of the unpatched tree with the new test files added, `tests.test_stack_squash_merge` gave 44 failures out of 77, the same count as `gate-logs/C4-verify.log`, and all of them were assertion failures. On the patched tree, all 77 pass. The tests run real git through `flow._drive_and_act`, `integrate.fold` and `publish.publish`. Only `gh` and the build and publish leaves are stubbed.
- **Test strength:** I made 16 small breaking changes to the patch, covering the head guard, drop steps, `_hold_all`, cause naming, mode checks, the `Onto branch` warning, `counts_into` and the `OSError` handling. The new tests caught 15. The 16th (the self-edge check) was not a valid run, because my edit broke the file's indentation, but `test_a_brief_naming_itself_is_no_dependent` covers that check.
- **Full suite:** 2774 tests pass on the patched tree, with 2 skipped. With a logging stand-in for `gh`, the patched and unpatched suites made the same calls, and neither made a `mergeCommit` read, so no other test reaches `gh` through the new path.
- **Logic attacks with no failure:**
  - A real merge commit cannot look like a squash, because its head is on the base.
  - The fold and carry only run this path outside merge mode.
  - `counts_into` matches the old `merged_into` condition.
  - The chain order in `_cascade_not_clean` holds up.
  - The `except` path in `_carry_finished` cannot leave a held line with an empty cause.
- **Messages that are incomplete but not wrong:** when Q depends on two squash-merged prerequisites, its line names only the first, so it takes two re-issues. Each prerequisite's own line still names it in the same output. With a line older than the squash, D gets the existing line telling the user to delete it, which is accurate.
- **Verified only by stub:** the rebase half has no live check. `tools/live/stack_mode_live.py:945` exercises squash only, and `template/tests/test_stack_squash_merge.py:775` says the rebase answer comes from a stub. If GitHub reported no merge commit for a rebase, the code would fall back to the old message, so I do not count this as a defect.
- **Gates:** T4 is `deferred` while `overall` reads `pass`, so the PR text has not been audited yet. That audit runs at publish, so this is not a finding against the fix.

<!-- pdca:leaf-complete -->
