## Summary
**User impact:** `pdca flow` can crash with `FileNotFoundError: …/brief.md` before it drives
a single bundle. This happens when the run includes a split parent from an older version
whose brief went missing (its split was accepted before #481). One old bundle stops the
whole batch, including all the healthy bundles, and the error does not tell you which
bundle is at fault or how to fix it.

This PR makes `pdca flow` check that each bundle has a brief before driving it. A split
parent with a missing brief gets the brief it would have had (rebuilt the same way
`pdca split --accept` builds it today). Any other bundle without a brief is skipped and
named, and the rest of the batch still runs.

Reported in [#597](https://github.com/eduralph/pdca-harness/issues/597) (first seen on a
downstream instance).

## What to look at
- One file changes: `template/src/pdca_harness/flow.py`. A new helper decides whether a
  bundle may enter the run. It is called from the three places a run picks up bundles:
  ids named on the command line, the `--from-csv` sweep, and adopting a split's children.
- To reproduce: take a split parent whose brief was archived by a re-plan, run
  `pdca split --accept` on it, delete the `brief.md` that accept wrote (this is what an
  accept from before #481 left behind), then run `pdca flow <parent-id>`. On `main` this
  crashes. With this PR it prints one line saying the brief was rebuilt from
  `iteration-v1/brief.md`, and the parent and its children run to the same result as a
  parent that never lost its brief.
- What gets printed when a bundle is skipped, e.g. with no archive to rebuild from:

  ```
  flow: issue_654 — split parent NOT driven: issue_654 has no brief.md and no iterate-to-Plan
  archive (iteration-v<N>/brief.md) to rebuild one from. Write issue_654/brief.md (slug,
  success criterion, repo + branch target), then `pdca flow 654`
  ```

## Root cause
Before #481 (5ced9bd94826fe4dbf409214614311ebbef3110e), `split --accept` on a parent whose
brief had been archived by an iterate-to-Plan wrote the close marker but no new brief.
`state.state` reads a bundle with a close marker and no `check-gates.json` as BUILT. The
intake filters only skip UNPLANNED and terminal bundles, so this one was driven, and the
first brief read (`_point_at_integration` → `publish._resolve_target` →
`brief.parse_fields`) raised out of the whole run.

## Fix
- `_has_plan_artifact(cfg, d)` (new, `flow.py`). It never raises.
  - If `brief.md` exists, the bundle is admitted and the file is never opened.
  - If the close marker is not `split`, the bundle is past Do with no brief: it is named on
    stderr and kept out.
  - Otherwise it calls `split._parent_plan` on the iterate-to-Plan archive. Then it renders
    the brief with `split._split_parent_brief`, using the lineage record's children as
    bundle names in record order. This is the same call `split.accept` makes, so the
    result is byte-identical. The file is written through a temp file and `replace`, so a
    failed write never leaves a half-written brief behind.
  - If the archive is missing or refused, or the lineage record is missing or names no
    children, the bundle is skipped with one stderr line: the reason, then one remedy
    (write `brief.md`, then `pdca flow <id>`). Text written for `split --accept` (such as
    "refusing to split") is cut, so the line reads correctly in a flow run.
- `_admit(cfg, d, claims)` (new) wraps the helper and releases the run's claim on any
  bundle it keeps out. This matches the existing no-brief skip in `flow_ids`.
- Call sites, each placed **after** the run holds the bundle's claim, so a bundle another
  live run is driving is never written to:
  - adoption, right after `_refused_child` claims the children;
  - the `--from-csv` sweep, right after `_claim_swept`;
  - named ids, after the UNPLANNED and terminal filters. This means a terminal split
    parent (used only to find its children) is never given a brief. A skipped named id
    stays in the results map, so the run exits non-zero.
- `state.py`, `split.py` and `publish.py` are not changed.

## Verification
- **Claim:** a split parent left without a brief by an old accept gets its brief rebuilt
  and is then driven exactly like a parent that kept its brief.
  - **Checked:** `template/src/pdca_harness/split.py:935-939` on `main`: the rebuild reuses
    `_parent_plan` + `_split_parent_brief` with bundle names, the same as `accept`.
  - **Test:** `test_a_pre_481_split_parent_is_repaired_then_driven_like_the_control`. The
    rebuilt brief is byte-identical to the one `split.accept` wrote. The results map and
    exit code match a control parent that kept its brief (both
    `{'654': 'COMPLETE', '701': 'COMPLETE', '702': 'COMPLETE'}`, rc 0).
- **Claim:** if there is nothing to rebuild from, the bundle is skipped, not driven, and
  not a crash. Its claim is released and the rest of the batch still runs.
  - **Checked:** `template/src/pdca_harness/flow.py:2068-2074` on `main`: the existing
    no-brief skip (message + `claims.release`) that the new skip mirrors.
    `split.py:784-806`: the cases where `_parent_plan` refuses.
  - **Test:** no archive, a refused archive, a missing lineage record, and a lineage record
    with no children each give one named line, no `brief.md`, a driven sibling and a
    non-zero exit. Claim release is checked on all three intake paths
    (`test_a_named_id_it_skips_is_let_go`, `test_the_sweep_lets_go_of_a_bundle_it_skips`,
    `test_adoption_lets_go_of_a_child_it_skips`). While the run is still live, a second
    claimant can take the skipped bundle but not the one being driven.
- **Claim:** all three intake paths are covered, and none of them writes before holding
  the claim.
  - **Checked:** `flow.py:1925-1940` (sweep: state filter, then `_claim_swept`),
    `flow.py:1104-1108` (adoption filter), `flow.py:2064-2104` (named ids) on `main`: these
    are the paths that let the BUILT, briefless parent through.
  - **Test:** `test_the_sweep_repairs_then_drives_like_the_control` (same map and rc as a
    control sweep), `test_an_adopted_child_is_repaired_then_driven`,
    `test_the_sweep_never_writes_a_bundle_another_run_holds`.
- **Claim:** nothing else changes.
  - **Checked:** `template/src/pdca_harness/state.py:351` and `:367-368` on `main`: the state
    rule that reads this bundle as BUILT is left as is.
  - **Test:** `test_a_bundle_with_its_own_brief_is_left_byte_identical`,
    `test_a_terminal_briefless_split_parent_is_never_written`.
- **Red → green:** `template/tests/test_flow_briefless_split_parent.py` (new, 16 tests).
  With the `flow.py` changes reverted, 13 tests error with the reported
  `FileNotFoundError: …/issue_654/brief.md`. The other 3 are guards that a careless fix
  could break, and they pass both ways. With the fix, all 16 pass. The full offline suite
  stays green (root 24 OK, driver 2231 OK, 2 skipped).

Fixes #597
