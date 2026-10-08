# Advisory code review — issue #646 (stack-reissue-continues-batch-line)

Lens: correctness bugs the patch adds, plus reuse/simplification. Advisory only; nothing here gates.

Gate evidence checked: in `gate-logs/C4-verify.log` the green leg is OK for both suites (17 + 46 tests). The red leg fails 12 of the new tests plus the 2 updated wording tests in `test_integrate_stack_bases.py`. The `FAILED (failures=2)` at the end of the log is the red leg, not a regression.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:839-848` (`_carry_finished`): the carry fold skips the opt-in `[driver].regate_between_waves` check that the in-run fold runs on every folded tip before the next wave builds on it (`flow.py:2213-2221`). With re-gate on, wave 0 of a re-issued run builds on a line combination nobody re-gated: the earlier run's line plus the newly merged finished ids. That breaks the "validate each folded combination before the next wave builds on it" promise. The fix is to run `gates.run_integration` over each carried `wt` (holding the integ lock through it, as the in-run fold does with its `locks` stack) and stop before wave 0 when it is red. The fix is small, and no test covers it.

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:801-803` (the trigger) together with `integrate.py:344-345`: when a re-issued run has finished ids but no driven bundle plainly `Depends on` one, nothing is carried. The first in-run fold then runs in `"fresh"` mode and force-pushes over the earlier run's line. An accepted-but-unpublished bundle whose `stack-base-tip` was on that line is stranded (`publish._line_tip_refusal`). That matches brief criterion (7) ("behaves exactly as today"). It does not match the brief's stated invariant ("no run replaces commits an earlier run of the same batch recorded as a build base"). The patch is honest about it: the docs and messages now say "started fresh by a run that carried nothing" (`docs/07-crosscutting.md:685-687`, `publish.py:728-732`). A human should decide whether that gap is acceptable for this child, or whether a re-issued run (any finished id in `run_batch`) should always start its first fold in `"auto"` mode (continue if origin has the line).

- `template/src/pdca_harness/merged.py:98-127` (`pr_state`): this repeats the `gh pr view <pr_url> --json …` call, the `OSError` guard and the JSON parsing from `merged_head` (`merged.py:66-95`) and `is_merged`. A small shared helper that returns `(info_dict | None, why)` would let all three use one code path, so the missing-`gh` guard cannot drift between them. This is a cleanup, not a bug.

- `template/src/pdca_harness/flow.py:719-722` (`_runnable`): the widened held check `cfg.bundle(dep).name in held and (not out_of_batch or dep in plain_deps)` compares the raw `dep` string with raw `brief.depends_on` strings. Both come from the same brief parser (`waves.declared_deps` is `depends_on + …`, `waves.py:48`), so this is correct today. A comment saying that `held` can now hold out-of-batch names only through `_carry_finished` would make the rule easier to read. Minor; no action needed.

## Checked and found clean

- `integ.update(...)` replacing `integ = {...}` (`flow.py:2207`) does not change in-run behaviour. `fold` returns every target in the cumulative `accepted`, so the only difference is that a target only the carry folded keeps its line.
- The carried ids stay out of `accepted`, so `integrate.unpublished(accepted, pushed=pushed)` never reports them as unpushed in later waves. The fold after wave 0 runs in `"continue"` mode from the carry's recorded tip, without force. Test 3 pins this.
- `pushed_tip` raising `IntegrationError` falls inside the `try`, so the run stops before wave 0 with no traceback (`flow.py:839-847`).
- In a dry run (stub publisher) the carry calls no `gh`, holds nothing, leaves `integ` alone and records `None` tips, the same as the in-run dry fold.
- The tests match criteria (1)–(8) one-to-one. They drive the production `_drive_and_act` and `integrate.fold` against a real bare origin, and they spy on pushes to prove that no force-push happens.
