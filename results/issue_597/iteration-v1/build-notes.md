# Build notes — issue 597 / flow-never-drives-a-briefless-bundle

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l1`, base `24c7f83`).
Line numbers below are on the patched tree.

## The change

One shared gate in `template/src/pdca_harness/flow.py`, called by all three intake paths
after the run holds the bundle's claim.

- `flow.py:978-1044` `_has_plan_artifact(cfg, d)`. It decides whether a bundle may enter the
  drive set. In order:
  1. `brief.md` exists → True, and the brief is never opened (criterion iv).
  2. The close marker is not `split` → name the bundle on stderr ("past Do … no Plan
     artifact … Restore … then `pdca flow <id>`"), return False. This covers "any other
     bundle with no brief.md that is past Do" (iii).
  3. `split._parent_plan(d, cfg)` (the same call `split.accept` makes, `split.py:937`). A
     `SplitError` (no archive, or an archive that is unreadable or incomplete) → one stderr line
     carrying the `SplitError` text, which already holds the remedy, plus
     "then `pdca flow <id>`". Return False.
  4. Children = `_lineage_children(split.read_lineage(d) or {})` (`flow.py:736-752` on the base).
     Empty (record missing, unreadable, or naming no children) → one stderr line, return False.
  5. `split._split_parent_brief(d, plan, [cfg.bundle(c).name for c in children])`. This
     mirrors `split.py:938-939` exactly, using bundle NAMES in lineage order. The result is
     written to a temp file and then `replace`d into `brief.md`, so the write is all or nothing.
     A failed write → stderr line, return False. On success: one stderr line saying the brief
     was "rebuilt it from iteration-vN/brief.md". Return True.
  Never raises.
- `flow.py:1047-1055` `_admit(cfg, d, claims)`: calls `_has_plan_artifact` and releases the claim
  when the bundle is kept out. This mirrors the no-brief skip in `flow_ids` (`flow.py:2068-2074` on base).
- Call sites:
  - `flow_ids`, `flow.py:2193-2197`: after the UNPLANNED and terminal filters, so a terminal
    briefless split parent (an adoption seed) never reaches the gate. A skipped id goes into
    `skipped[iid] = s` (BUILT), so it stays in the results map (#468) and `_results_rc` gives
    a non-zero exit.
  - `flow_batch`, `flow.py:2027-2035`: after `_claim_swept`, not in the state filter before it
    (#565). If nothing is left, it prints "nothing to drive" and returns `{}`, like the
    claim-exclusion branch right above it.
  - `_adopt_split_children`, `flow.py:1396-1397`: right after `_refused_child` claims each child.
    `_adoptable` has already routed terminal children to `walk`, so they are never gated or written.

`state.state`, `split.accept`, `_point_at_integration` and `publish` are untouched (out of scope).

## Observed end point (criterion i)

With stub leaves, `no_publish=True`, `no_act=True`, `pdca flow 654` on the repaired parent:
results map `{'654': 'COMPLETE', '701': 'COMPLETE', '702': 'COMPLETE'}`, rc 0. The control
parent (post-#481 disk, brief left in place) gives the same map and the same rc. The repaired
parent goes down the close-disposition fast path to COMPLETE, then its children are adopted
and driven. Its rebuilt `brief.md` is byte-identical to the one `split.accept` wrote for the
same parent before the test deleted it.

## Alternatives ruled out

- **Guarding the crashing read (`_point_at_integration` / `publish._resolve_target`).** The
  brief's self-test already rules this out: the bundle would still be driven into Check,
  sign-off and publish with no brief. The fix keeps it out of the drive set instead.
- **Repairing inside the state filter, before the claim (e.g. in the `flow_batch` list
  comprehension at `:1929-1934` on base).** Smaller, but it would write into a bundle another
  live run holds (#565). The gate runs after the claim on every path.
- **Re-implementing the brief text in `flow.py`.** Rejected: it would drift from
  `split._split_parent_brief`. Reusing the two private split functions keeps byte identity by
  construction. The cost is a cross-module call to private names; `flow.py` already calls
  `split.read_lineage` and reads split's constants.
- **Changing `state.state` to return UNPLANNED for a briefless split parent.** Out of scope
  per the brief; #481 deliberately made it read past Do.

## Test — `template/tests/test_flow_briefless_split_parent.py` (14 tests)

Every pre-#481 disk is built with production code: `driver._archive_iteration(include_brief=True)`,
then `split.accept`, then the test deletes the `brief.md` accept wrote. Runs go through
`cli._flow` with pass-through spies on `flow.flow_ids` / `flow.flow_batch` that record the
real results map. The test imports modules only, never a new symbol.

| Criterion | Test(s) |
|---|---|
| (i) repaired byte-identical + same map/rc as control | `test_a_pre_481_split_parent_is_repaired_then_driven_like_the_control` |
| (ii) no archive / refused archive / missing lineage / empty lineage; sibling driven; map entry; rc≠0 | `test_no_archive_is_skipped`, `test_an_archive_split_refuses_is_skipped`, `test_a_missing_lineage_record_is_skipped`, `test_a_lineage_record_naming_no_children_is_skipped` |
| (ii) claim released | `test_a_skipped_bundle_s_claim_is_released` (a second `drive_claim.Run` can take it while the first run is still open) |
| (iii) non-split briefless past-Do skipped | `test_a_briefless_bundle_past_do_that_is_not_a_split_parent_is_skipped` |
| (iii) sweep repair / skip / held by another claim | `test_the_sweep_repairs_then_drives`, `test_the_sweep_skips_a_parent_with_no_source_and_drives_the_rest`, `test_the_sweep_never_writes_a_bundle_another_run_holds` |
| (iii) adoption repair / skip | `test_an_adopted_child_is_repaired_then_driven`, `test_an_adopted_child_with_no_source_is_skipped` |
| (iv) terminal briefless parent untouched; own brief byte-identical | `test_a_terminal_briefless_split_parent_is_never_written`, `test_a_bundle_with_its_own_brief_is_left_byte_identical` (the control leg in (i) also checks a post-#481 parent's brief is unchanged) |

## Refuting my own test

- **(a) Real red?** Yes. I reverted the `flow.py` hunks with `git apply -R` and re-ran:
  11 of 14 tests error with `FileNotFoundError: …/results/issue_654/brief.md`, the reported
  crash, from `cli._flow` / `flow.flow_ids`. That includes the adoption-path test. The 3 that
  stay green on the base are guards that a careless fix could break: held claim not written,
  terminal parent not written, own brief untouched. They pass on the base because the base
  never writes a brief. The project's C4 gate agrees:
  `PDCA_BUNDLE=… PDCA_WORKTREE=… PDCA_BRIEF_BASE=origin/main ./engine/scripts/run-verify.sh`
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
- **(b) Production path?** Yes. Every leg goes through `cli._flow` (or `flow.flow_ids`
  directly for the claim-release check) into the real `flow_ids` / `flow_batch` /
  `_adopt_split_children`. The spies only record return values. The expected bytes come from
  the real `split.accept`, not from a copy of the template.
- **(c) Does the fixture include the fault?** Yes. The fixture is the real pre-#481 disk:
  close marker `split`, lineage record, `iteration-v1/brief.md` from the driver's own archive
  call, and no `brief.md`. The test asserts it reads BUILT before the run. The held-claim leg
  takes a real flock claim through a second `drive_claim.Run`.

## Runs

- New module with the fix: 14/14 OK.
- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`,
  under `timeout`): `Ran 2229 tests … OK (skipped=2)`.
- Commit-readiness: the target has no pre-commit config, no ruff/flake8 config, and no
  formatter in CONTRIBUTING/AGENTS. `git diff --check` is clean and no added line is over 100
  columns, which matches the file's style.

## Housekeeping

To do the red leg I wrote a helper file, `results/issue_597/.fix-only.diff` (the `flow.py`
hunks only), into the bundle dir. I could not delete it under the no-`rm` rule. It is a
subset of `patch.diff` and can be ignored. A copy of the test is also in the bundle dir;
the canonical copy is in `patch.diff`.
