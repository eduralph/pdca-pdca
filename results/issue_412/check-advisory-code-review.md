# Advisory code review — issue 412 / merges-with-field-refused-in-merge-mode

I found no correctness bug on either lens. The items below are small, and none should block.

## Correctness

- `template/src/pdca_harness/waves.py:170-196` (`merge_groups`): the union-find (grouping members by a shared root) is correct. `root()` creates missing nodes through `setdefault`, so a partner outside the run (`X`) becomes a node and stays in the group, as the docstring says. A self-reference (`A` declares `Merges with: A`) makes a one-member group, and merge mode refuses it. That matches the brief's "declares a non-empty `Merges with`" rule, so it is fine.
- `template/src/pdca_harness/waves.py:377-386`: the holds are added before the first `_propagate_holds`, so dependents are held too. Every in-run member of every group is held, so the set left over has no group the strict `compute_waves` call could still refuse. That means the `compute_waves(schedulable)` calls after the tolerant path (`flow.py:2180` and the sweep) cannot start raising because of this change. The split re-levelling at `flow.py:2175` is safe for the same reason. Split children do not carry the field, and the brief already names that gap.
- `template/src/pdca_harness/waves.py:149-157`: the group check runs after the cycle and unresolved-dependency checks. A batch with both problems reports the dependency error first, and the group error only once that is fixed. This is fine, but the operator may need two tries to see both.
- Low priority (not marked NEEDS-HUMAN because `flow.py` is out of scope): the sweep's "nothing to schedule" message at `template/src/pdca_harness/flow.py:3338-3339` still says every bundle is "held on an unresolved dependency or a cycle". A run held only by a merge group now shows that wrong reason. Each bundle's real reason is still printed above it by `_report_held` (`flow.py:1793`), so nothing is lost. A follow-up (or #778) could fix the wording.

## Tests

- NEEDS-HUMAN [impl] — `template/tests/test_merge_group.py:158-172`: the tolerant path is only tested on batch (d), where `A` declares the group. Nothing tests `partition_schedulable` in merge mode when only the partner declares the group (`BATCH_B`), or when the partner is outside the run (`BATCH_B_OUT`, :44). The strict path tests both. Two short subtests that reuse the existing batches would pin the "either side binds both" rule on the sweep path too. (d) passes today, and the code handles both cases, so this only adds coverage.
- `template/tests/test_merge_group.py` (`WavesPreviewRefusesAGroup`): it changes the process cwd (`os.chdir`) and restores it in `finally`. That is safe in serial runs, but it would break if the suite ever ran in parallel threads. The existing tests do the same, so this is not new risk.

## Reuse / simplification

- The patch reuses `_id_list`/`field` for parsing (`brief.py`), `DependencyGraphError(…, remedy=…)` for the refusal, and `_propagate_holds` for dependents. It also shares one `_GROUP_WAYS_OUT` string between the strict and tolerant paths. I see no duplicated logic and nothing slow: `merge_groups` reads each brief once per call, the same cost as `conflict_map`.

<!-- pdca:leaf-complete -->
