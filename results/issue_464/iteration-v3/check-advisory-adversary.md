# Adversarial review: issue 464, `wave_mode = "none"`

The red→green proof holds, and the brief's named legs pass. But I found two concrete inputs that break the fix, both when a prerequisite is iterated. There are also two smaller cases where the printed way out is wrong.

I ran every case below on a scratch copy of the patched tree at `$PDCA_TARGET`, using real git and a stubbed `gh`.

## Findings

- NEEDS-HUMAN [impl] — **Iterating a prerequisite whose draft PR is still open blocks its dependent for good.** The way out it prints cannot work. Cause: `template/src/pdca_harness/flow.py:868` makes `publish.json`'s `pr_url` the only sign that a PR exists, but on a re-publish `gh pr create` refuses a head that already has an open PR, and `template/src/pdca_harness/publish.py:412` and `:440` then overwrite the good URL with `""`. The repo already documents this `gh` failure at `flow.py:651-652` ("an iterated bundle whose old draft PR is still open"). Case: run 10 and 11 (11 `Depends on: 10`), iterate 10, run again.
  - The new commit reaches the open PR, but the run gives `holds={'10': 'no-pr'}`, rc 1, and says "no PR of that work is on record".
  - `pdca publish 10`, the advice printed, returns 1 and leaves `pr_url` as `""`.
  - After the PR merges on the host, 11 is still held with rc 1. `pdca publish 10` still returns 1 and `pr_url` stays `""`, so 11 stays held. I found no way out through the harness; hand-editing `publish.json` or dropping the edge looks like the only one left.
  - A lone iterated bundle with no dependents gets `no-pr` and rc 3, though its PR is open and up to date. The same iterate in `"stack"` gives rc 0, so iterating is a normal path that only this mode turns into a failure.
  - Fix: when `gh pr create` fails, look up the open PR (`_existing_pr`, `publish.py:582`) or keep the earlier URL, without changing stack mode's result.
  - Why the tests missed it: the stub at `template/tests/test_flow_wave_mode_none.py:139` lets a second `gh pr create` for the same head succeed, and the iterate test (`:466`) only fails the texts. Add a case where the stub refuses the second create.

- NEEDS-HUMAN [impl] — **One run after a failed re-publish, the dependent is released on the old, rejected PR.** `template/src/pdca_harness/flow.py:868` only catches a stale record through `unpushed_set`, which lasts one run. Case: 10 has an open PR, is iterated and rebuilt, and its texts fail. That run correctly gives `holds={'10': 'unpushed'}`, rc 1, and tells the user to publish first. The next `pdca flow 10 11` does not drive 10 (it is COMPLETE), so the stale `pr_url` counts again:
  - That run gives `holds={'11': 'unmerged'}`, rc 3, and "merge their PR into main", which points at the rejected attempt.
  - Following that advice gives `results={'11': 'COMPLETE'}`, rc 0, and `a.txt` on `main` has the old text, not the rebuilt `a, again`.
  - The new test `test_an_iterated_prerequisite_not_published_again_is_not_waited_on_by_its_old_pr` stops after the first run, so it never sees this.
  - Fix: tell a record from an earlier attempt without relying on this run's `pushed` set, for example by comparing `publish.json` with the current `patch.diff`, and treat a stale record as having no PR.

- NEEDS-HUMAN [impl] — **The hold can tell the user to do something that cannot help.** `template/src/pdca_harness/flow.py:876-879` sends every "not merged into d's base" answer to the same message, "merge their PR into main, then re-run".
  - Case 1: prerequisite 10 has an `Onto branch` record (mode `stacked`) and its PR has already merged into `main`. `merged_into` (`template/src/pdca_harness/merged.py:109`) never counts that record, so the run gives `holds={'11': 'unmerged'}`, rc 3, on every run. The docs say this kind of commit does not count (`docs/07-crosscutting.md:925`), but the printed step is already done and nothing else is offered.
  - Case 2: 10's PR targets `dev`, is open, and 11 targets `main`. It prints the same advice, but merging that PR puts it on `dev`, so 11 stays held.
  - I hand-wrote the `publish.json` records for both cases, using the fields `publish.py:440` and `:562` write. I did not run a real `Onto branch` publish.
  - `test_a_merge_into_another_base_does_not_release_the_dependent` (`template/tests/test_flow_wave_mode_none.py:403`) pins the hold but not the advice.
  - Fix: use a separate line when the PR is already merged, or when its recorded base is not d's base. That line should say merging this PR will not release the bundle.

- NEEDS-HUMAN [impl] — **A chain above a merged PR that the fetched base lacks gets the wrong advice, and no test covers it.** At `template/src/pdca_harness/flow.py:892`, a prerequisite already merged on the host still goes into `to_merge`. Case: 10 ← 11 ← 12, 10's PR is MERGED, and `origin/main` as fetched lacks the merge. 11 is correctly told to fix the fetch. 12 is told "merge the PRs of issue_10, issue_11 in that order", but 10 is already merged and the real fault is the fetch. Deleting line 892 leaves all 43 tests green, so nothing pins that line. This is low severity, but it is the only mutant of the seven I tried that survived.

## What I tried and could not refute

- **Red→green.** Reproduced at `$PDCA_TARGET`: 35 of 43 tests fail with the production changes reverted, all 43 pass with them, and the failures are assertions, not import errors. This matches `gate-logs/C4-verify.log`. The 8 tests that pass on red are controls and `"stack"` pins, so they prove nothing about the fix, but they do not inflate the 35.
- **Production path.** The C5 row only checks imports, so I checked this by hand. The tests drive the real `flow._drive_and_act`, `cli._flow` and `publish.publish` against a bare origin. Only the build leaf, text drafting and `gh` are stubbed. It is not a copy of production. The stub's weakness is the first finding.
- **Test strength.** Six of seven mutants were caught: the stub-publisher gate, `_hold_without_pr`, `_base_lacks_merge`, the `merged_into` call, the `_stacks_on_branch` gate and the `unpushed_set` check.
- **Stale stack base in a flow run.** `_point_at_integration` clears it for every bundle a `"none"` flow run builds (`template/src/pdca_harness/flow.py:1113`).
- **Non-string `wave_mode`.** From reading the check at `template/src/pdca_harness/config.py:744`, it falls back to `"stack"` with a note. I did not run this case.

## The verdict

This pass received `check-gates.json`, not the reviewer's written verdict, so I cannot quote a claim from it. The one claim I question is `"overall": "pass"` being read as "`none` is ready to use". The gates show the brief's legs hold on a `gh` stub more forgiving than real `gh`. They say nothing about iterating a prerequisite, which is a normal path in this harness. I did not call real `gh`: the refusal in the first finding comes from the repo's own note at `flow.py:651-652` and my stub of it.

<!-- pdca:leaf-complete -->
