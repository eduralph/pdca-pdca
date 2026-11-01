# Advisory code review: issue 626

I found one small correctness bug, one cosmetic message conflict and one simplification question. I read the code and gate logs and did not run anything; line numbers refer to the patched tree at `$PDCA_TARGET`.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1701` and `:1712`: in a batch spanning two targets, the carry can name the wrong line to delete. `gone` is built inside the per-target loop (`flow.py:1623`), so it lists only this target's squash- or rebase-merged ids. The line name hashes the whole batch (`integrate.py:141`, `integrate.py:173`). If a second target also has such an id, the operator is told to re-issue without both, but each message names the line for a batch without only one. The line that re-issue really continues is never named, so it may survive. With the edge dropped, nothing checks that line for the merge, which is the silent build `integrate.DROP_PREREQ` exists to prevent. It takes a multi-target batch, a record that never counts as merged, and an existing line on origin, so it is narrow. Fix: collect `gone` across all targets before printing any of these lines. `template/tests/test_stack_squash_merge.py` has no two-target carry case; add one.

- `template/src/pdca_harness/merged.py:113` and `template/src/pdca_harness/flow.py:895`: for a held dependent, two stderr lines now disagree about where the PR merged. `merged_into` prints "merged, but into <record base> ...; treating as not merged" (for an `Onto branch` record the base is `origin/fix/...`). `_runnable` then prints that the same PR was squash- or rebase-merged into `main`. The second line is the accurate one, and the operator sees both. This is cosmetic and I found no wrong behaviour. Fix, if wanted: have the `flow.py` line say that the record names another base.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:840` and `:870`: is the third reporting path worth its size? The brief's Scope covers recognising these merges "at the fold and at the re-issue carry", and its criteria (a) to (e) do not mention `_runnable`. The patch also adds `_uncounted_squash`, about 30 lines that build the step text across the `stale`, `unjudged` and `carryable` cases, `DROP_PREREQ`, `reissue_line`, and matching conditional prose in `docs/07-crosscutting.md`. The extra path does fix a real problem: without it, a dependent told to wait would wait forever. A simpler option is one hold line saying "drop the edge and delete this batch's line on origin if it is there", which gives up the per-case detail. Decide whether to keep the full version, simplify it, or split it into a follow-up issue.

## Checked, no finding

- **Merge mode:** the carry and `hold_unmerged` are gated at `flow.py:3026` and `:3039`, and `_uncounted_squash` and `_others_build_on` check `wave_mode` themselves.
- **Line name in `_runnable`:** `asked` matches `run_batch` for both `flow_ids` and `flow_batch`, so `flow.py:885` and `:892` hash the right batch.
- **`_finished_head` reordering:** a merged PR whose head is empty or missing from the checkout keeps its old reason when it is not a squash.
- **`_gone_branch` reordering:** moving the `_carries` call above the `onto` check does not change any outcome.
- **Cascade cause:** `_cascade_not_clean` passes the merged id down a chain through `causes.get`.
- **`_others_build_on`:** an unreadable brief is skipped, because `UnicodeDecodeError` is a `ValueError`. The bundle's own brief is also skipped.
- **Gates:** all ran as expected. The `FAILED (failures=82)` at the end of `C4-verify.log` is the expected red run without the fix, and T3 passed. T4 is deferred to publish.

<!-- pdca:leaf-complete -->
