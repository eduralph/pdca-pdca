# Adversarial review: issue 626, attempt 5

One real refutation: the wrong build that attempt 4 was rejected for can still happen, through advice this patch prints. Everything else held up. I had no reviewer verdict text, only `check-gates.json`, so I attacked the gate claims and the brief.

## Findings

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:1486` (`DROP_PREREQ`, used at `template/src/pdca_harness/flow.py:1412` and `:1414`): following P's own printed advice still builds D without P's work, with no warning. Attempt 4 was rejected for exactly this kind of failure, but the fix reached only D's hold line (`flow.py:863`). I ran this sequence with the test fixture. The record is an `Onto branch` one.
  1. Run `R, D`, with D naming `R, P` and P's PR still open. R is carried onto the line, and D is told to "name issue_P in the same `pdca flow <ids>` command".
  2. P is squash-merged and its branch deleted.
  3. Run `P, R, D`, as step 1 advised. This run has a different line. P's line says to re-issue without P "after dropping issue_P from the brief of any bundle that names it", and says nothing about the older line.
  4. Drop the edge and run `R, D`. This continues the line from step 1, and D reaches COMPLETE at `52a53282edb4`. That tip lacks the merge commit and `p.txt`, and the output has no "on origin" warning.

  D's own hold line, which gives the delete step, never prints in this sequence, because D no longer names P by the time the older line is back in use. Q's hold line and the fold's stop use the same step and have the same gap.

  The builder knows about this: `docs/07-crosscutting.md:925-927` says "look for such a line yourself", and `template/tests/test_stack_squash_merge.py:1261` pins the behaviour as expected. So the docs are honest, but the printed advice can still produce a wrong build.

  You decide because your sign-off told the builder to fix D's line and the docs and "change nothing else". The choice is to accept this as a documented limit, or to have P's line, Q's line and the fold's stop also name the line of the re-issued batch. `integration_branch` can work out that name from the batch minus P.

- `template/src/pdca_harness/flow.py:863` and `template/src/pdca_harness/merged.py:114-116`: for an `Onto branch` record, the same run prints two lines that disagree. Run output: "merged: P's PR … merged, but into org/repo @ origin/fix/P … treating as not merged into org/repo @ main", then "issue_D held — … squash- or rebase-merged into main". The first line's wording is older, but this patch puts the two side by side. No wrong build follows, because the second line gives the right step, so I am not asking for a change.

- `template/src/pdca_harness/flow.py:868`: a small test gap. Changing `all(known …)` to `any(known …)` passes all 95 tests, so nothing pins the wording when the line is known to lack one merge and cannot be checked for another. The step printed is the same either way, so this is not a behaviour bug.

## Attempted and could not refute

- **Red→green proof:** it reproduces. On the base with the new test file, 62 of 95 tests fail, all on assertions. With the patch, all 95 pass. `patch.diff` matches the target tree. I did not re-run the full suite; `gate-logs/T3-suite.log` shows 2792 tests OK, 2 skipped.
- **Whether the tests exercise production code:** they do. I broke the patched code in 20 places on scratch copies, and the new tests caught 19; the only one missed is the wording gap above. Removing either attempt-4 fix also fails tests: 9 fail without the delete step, and 23 fail with "so main has the PR's work" put back. C5 only checks imports, so this is the stronger evidence.
- **Other inputs I tried by reading the code:**
  - **Line checks:** a dependent not on the line, and a target with no recorded tip.
  - **Merge shapes:** a line that has the head but not the merge commit, and a merge commit on the base with the head there too (for example, a dependent merged later with a merge commit).
  - **Read failures:** fetch or `gh` failures at each read.
  - **Records and modes:** merge mode, dry-run, an archived prerequisite and an `Onto branch` publish.
  - **Advice in a chain:** the hints a chain of dependents gets.

  Each failed closed or gave correct advice. I did not re-open anything your attempt-4 rulings settled.
- **`check-gates.json`:** the `overall: pass` is fair, with two limits. T4 is deferred to publish, so the contribution check has not run on this attempt. C2 has no gate of its own, so C4 is the only red-before-fix proof, and I re-ran that result above. Real GitHub behaviour remains unproven offline, which you accepted as #625's job.

<!-- pdca:leaf-complete -->
