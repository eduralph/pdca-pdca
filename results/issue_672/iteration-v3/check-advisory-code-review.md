# Advisory code review — issue 672 (carry keeps a fold-time skip off the line)

Scope: correctness bugs the patch adds, plus reuse/simplification. Line numbers are on the patched tree at `$PDCA_TARGET`. I read the code and did not run anything; the gate logs report C4 and T3 green.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:573-579`, `:598-603`: when the fold starts over (`_reset_tree(wt, start_ref)`), every id in `left` stays left out, including ids skipped in the first pass for a plain merge conflict. That conflict may only have happened because of a bundle the second pass now leaves out. Example, in order `Q, Y, P`: Q (cut from P's first commit) merges, Y conflicts with Q's change and is skipped, P conflicts and is skipped. The second pass drops Q but never retries Y. Y would now merge cleanly, but it is still held with the "open" hint ("get its PR open"), which is wrong advice. Its `own` work (`:582-583`) can also hold more ids by ancestry. This is a false hold, not a leak, so the invariant still holds. Possible fix: on a restart, clear the conflict-only skips (the ones with no `holds` cause) from `left`, `skipped` and `own`, and merge them again. The loop still ends, because every restart adds at least one held-for-work id. No test covers a conflict skip that a restart makes stale.

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:591-596` with `template/src/pdca_harness/flow.py:1125-1126`: on a re-issued run, origin's line usually already holds a finished id's earlier head, because the earlier run folded it there. If that id's branch later gets a commit that conflicts, `_own_work` (`integrate.py:930-958`) counts the earlier head, which is already on the line, as the skipped id's work. The fold then raises `SkippedWorkOnLine`, and the carry holds **every** finished id of the target with the "delete the line" hint. Before the patch, only the conflicting id was held and the rest were carried. This is deliberate: it is pinned by `test_a_line_already_holding_a_skipped_ids_work_is_not_carried_onto` and documented in `docs/07-crosscutting.md:737-741`. It also fits the brief's "append-only" rule. But that work is on the line already, so holding the whole target does not keep it off. The only effect is a larger hold on a common re-issue shape. A human should decide whether a commit the line already got from that id's own earlier head should count as "accounted for" here.

- `template/tests/test_flow_resume_stack_prereqs.py:528` (non-blocking, [impl]-grade nit): `test_base_history_two_branches_share_is_no_skipped_ids_work` checks only that no push was forced. The other new carry tests assert `len(pushes) == 1`. Adding that check here would also catch a re-fold that pushes twice on a continued line.

## Clean on the rest

- The one-push rule holds. The restart happens before any push (`integrate.py:598-603` comes before `:611`). `_reset_tree` runs `reset --hard` on the checked-out line branch, so the second pass starts from `start_ref`. The loop ends: each restart puts at least one merged id into `left`, through the check before its merge at `:558`.
- Base history is never counted as an id's work: `_commits` (`integrate.py:922-927`) uses `rev-list --not base_ref`. That covers the round-1 finding. Merge commits are counted, which covers the round-2 finding.
- Gone branches (`head is None`) only ever take in the base (`integrate.py:697-742`). The base holds no skipped work, so leaving them out of `took` at `:585-586` is safe.
- In `flow.py:1121-1132`, `within.clear()` on any fold error, plus the `SkippedWorkOnLine` → `"line"` hint, keeps the hold reasons consistent. `causes.update(within)` feeds the existing `built_on` hint (`flow.py:1001-1002`), so it reuses the #652 wording instead of adding a new path.
- Reuse is fine: `_own_work` builds on the existing `_in_line` / `_carries` / `publish.read_stack_base_tip` helpers, and `adds` caches each tip's `rev-list`. The extra git calls grow with (skipped ids × bundles in the target). That is small, and it costs nothing when nothing is skipped: `own` is empty, so `:558` skips the check.

<!-- pdca:leaf-complete -->
