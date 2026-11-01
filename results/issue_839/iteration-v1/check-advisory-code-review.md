# Advisory code review: issue 839

I found four correctness defects and one small cleanup. None of them affects the tested legs (1) to (5) of the brief. I confirmed the first three with a small probe that calls `flow._merge_prereqs` and `flow._merge_way_out` directly, with `state`, `merged_into` and `_merge_one` stubbed. The probe does not do a full `flow_ids` run. The fourth comes from reading the code.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1481`: a COMPLETE prerequisite with no `brief.md` crashes the whole run before wave 0. `visit` calls `publish._resolve_target(p)` and `waves.declared_deps(p / "brief.md")` outside `_isolate`, and both raise `FileNotFoundError` on a missing brief (the probe confirmed this). `state.state` can still report such a bundle as past Do (`state.py:354-360`), and `_isolate`'s docstring says any bundle file may be absent. The new step guards the root bundle (`bp.exists()`) but not the prerequisites it walks to. The same exception can come from `_merge_way_out` (`flow.py:1435`) and from `_runnable`'s `_fold_candidates` call (`flow.py:800`), which merge mode now reaches because `hold_unmerged` is on. Fix: treat a missing brief as "not taken" and hold only that dependent, and add a test. I did not check whether an earlier scheduling step would stop this case first.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1477-1487`: the walk can ready and merge a PR that nothing is waiting for. `visit` goes through a prerequisite without checking whether it is already merged, and the merge loop handles the deepest bundle first. With D → P → Q, where P is already merged into the base and Q is marked and open, the probe called `_merge_one` on Q. `_runnable` only looks at D's direct edges, so D never needed Q. This is an unattended merge that `docs/07-crosscutting.md:909` does not describe ("the marked prerequisites the bundles it drives wait for"). Fix: don't descend past a prerequisite that is already `merged_into` the base, and add a test.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1449`: `_merge_way_out` gives advice that cannot work for two kinds of record, because it checks only the brief's target and the marker. It does not check the record's `mode` or `base`. The probe returned "merge the PR by hand, then re-run" for both:
  - A `"stacked"` record: `merged_into` never counts one as merged (`merged.py:110`), so the dependent stays held after the human follows the advice. Merge mode used to build this dependent, so this dead end is new here.
  - A PR already merged into another base: there is nothing left to merge by hand.
  Fix: give each case its own text, using the wording already on `flow.py:1446` ("get its work onto {base}"), and add a test for each.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:817` and `template/src/pdca_harness/flow.py:1519`: on the pre-wave path, a refusal that has nothing to do with the PR is reported as a PR problem. With a malformed `expected_checks`, the message ends "resolve at the PR" where the wave text says to fix `pdca.toml`, and the hold line says "its PR did not pass the merge gates". Nothing at the PR can clear this. `_isolate` returning `None` after an internal error gets the same hold line. The brief fixes this trailing text for PR refusals, but this case needs its own. The rollup refusal (`merge.py:930`) also drops the hints about `merge_wait_secs` and `merge_requires`, so a PR refused only because its checks were slow gets no hint about that setting.
- `template/src/pdca_harness/flow.py:1517`: cleanup. The `p=p, held=held` lambda defaults do nothing, because `_isolate` calls the lambda straight away inside the same loop pass. `lambda: merge._merge_one(...)` is enough.

No problems found in these areas:
- **Marker:** it is written before the first `gh pr ready`, and the later `base` rewrite (`merge.py:842`) keeps it.
- **Re-publish:** `publish.py:450` and `:566` write fresh records without the marker.
- **Merge order:** it stays deepest-first across several roots.
- **Base refresh:** `fetched` skips the later fetches in a chain, but `worktree.ensure` fetches again (`worktree.py:249`, `:319`, `:364`), so the dependent is cut from the merged base.
- **Wave-boundary text:** the refusal messages are unchanged, and the new tests pin the three main ones.

Gate logs: C4 shows the tests red without the fix and green with it. T3-suite passed.

<!-- pdca:leaf-complete -->
