# Build notes — issue 597 / flow-never-drives-a-briefless-bundle (iteration 2)

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l0`, base `24c7f83`,
the same base as iteration 1). Line numbers are on the patched tree unless marked "base".

## What this iteration did

The sign-off kept the fix and asked for four review points only. So I re-applied the
iteration-1 patch unchanged and then made just these edits:

| # | Review point | Change |
|---|---|---|
| 1 | `flow.py:1020` — dead `plan is None or` in the lineage check | Dropped. The lineage message now fires only on `if not children:` (`flow.py:1030`). See "Point 1" below for the separate 2-line `plan is None` guard. |
| 2 | `flow.py:1017` — skip line pasted `SplitError` text ("refusing to split", "then re-run: …") and added a second remedy | New line at `flow.py:1015-1024`: a flow lead-in, the `SplitError`'s reason only, and one remedy. |
| 3 | test `:266` — `assertIsInstance(rc, int)` can never fail | Replaced with a control sweep over the post-#481 disk: results map and rc must equal the control's (`test_the_sweep_repairs_then_drives_like_the_control`, test:302). |
| 4 | test `:237` — claim release only tested through `flow_ids` | Added `test_the_sweep_lets_go_of_a_bundle_it_skips` (test:270) and `test_adoption_lets_go_of_a_child_it_skips` (test:280). The `flow_ids` test (now `test_a_named_id_it_skips_is_let_go`, test:258) uses the same probe. |

Nothing else changed in `flow.py`: `_has_plan_artifact`, `_admit` and the three call sites are
as accepted.

## The change (whole patch, for reference)

All in `template/src/pdca_harness/flow.py`. Four hunks, inserted after base lines 977, 1315,
1944 and 2102:

- `flow.py:978-1054` `_has_plan_artifact(cfg, d)`. It decides whether a bundle may enter the
  drive set. Never raises.
  - `brief.md` exists → True. The brief is never opened (`flow.py:1000-1001`).
  - Close marker is not `split` → one "past Do … NOT driven" line, False (`flow.py:1003-1012`).
  - `split._parent_plan(d, cfg)` raises → one skip line, False (`flow.py:1013-1024`, point 2).
  - `plan is None` → True (`flow.py:1025-1028`, point 1).
  - No children in the lineage record (`_lineage_children(split.read_lineage(d) or {})`) →
    one lineage skip line, False (`flow.py:1029-1036`).
  - Otherwise: `split._split_parent_brief(d, plan, [cfg.bundle(c).name for c in children])`
    (`flow.py:1037`, the same call as `split.py:937-939`). It is written through a temp file
    and `replace` (`flow.py:1038-1050`), followed by one "rebuilt it from iteration-vN/brief.md"
    line (`flow.py:1051-1054`).
- `flow.py:1057-1065` `_admit(cfg, d, claims)`: calls `_has_plan_artifact` and releases the
  claim on a bundle it keeps out. This mirrors `flow_ids`' no-brief skip (base `flow.py:2068-2074`).
- Call sites, each after the claim is held:
  - adoption, `flow.py:1406-1407`, after `_refused_child` claims the child;
  - sweep, `flow.py:2037-2044`, after `_claim_swept`;
  - named ids, `flow.py:2203-2207`, after the UNPLANNED and terminal filters, so a terminal
    briefless split parent (a seed) never reaches it. The skipped id stays in the results map.

`split.py`, `state.py`, `_point_at_integration` and `publish.py` are untouched.

## Point 1 — why a separate `plan is None` guard is still there (2 lines + 2 comment lines)

The flagged condition is gone, so the lineage line can only fire for a missing, unreadable or
empty lineage record. I did not drop `plan is None` with nothing in its place, though.
`_parent_plan` returns None iff `brief.md` exists (`split.py:805-806`). With no guard, a None
would reach `_split_parent_brief`, whose `rel, slug, target = plan` (`split.py:857`) raises
`TypeError`. Nothing between the intake and `cli._flow` catches that, so it would end the run:
the same failure class this issue fixes.

When can it happen? Only if a `brief.md` is written between the check at `flow.py:1000` and the
one at `split.py:805`. The claim does not fence such writers: a CSV batch's planner,
`pdca split --accept`, and the single-step verbs all take no claim (`drive_claim.py:42-46`).
So the window is tiny but documented as possible. The guard answers exactly what the top
check would have answered (it has a brief → admit), and its comment cites both places.

- Cost of the guard: 4 lines (`flow.py:1025-1028`).
- Cost of dropping it: 0 lines, plus a reachable uncaught `TypeError`.

If the human prefers it gone, deleting `flow.py:1025-1028` is the whole change. No test
depends on it, because the race cannot be produced deterministically.

## Point 2 — the skip line, and why it cuts the `SplitError` text

New wording (observed, no-archive case):

```
flow: issue_654 — split parent NOT driven: issue_654 has no brief.md and no iterate-to-Plan
archive (iteration-v<N>/brief.md) to rebuild one from. Write issue_654/brief.md (slug,
success criterion, repo + branch target), then `pdca flow 654`
```

Refused archive:

```
flow: issue_654 — split parent NOT driven: issue_654 has no brief.md, and
iteration-v1/brief.md, the brief it would be rebuilt from, is incomplete: brief.md field
'repo + branch target' is empty or an unfilled placeholder — it is required by every brief
template. Write issue_654/brief.md (slug, success criterion, repo + branch target), then
`pdca flow 654`
```

How: `why = str(exc).partition(" — refusing to split")[0]` (`flow.py:1019-1020`). All three of
`_parent_plan`'s raise sites put the reason first and then " — refusing to split. <split's own
remedy>" (`split.py:811-814`, `:827-829`, `:831-833`). A non-`SplitError` is shown as
`Type: text`.

Alternatives I ruled out:

- **Give `SplitError` a structured reason field.** It is a bare `Exception` subclass
  (`split.py:94-95`). This needs a `reason` attribute plus 3 raise-site edits in `split.py`
  (about 8 lines). The brief puts changes to `split --accept` out of scope, and its ordering
  note has 597 editing only `flow.py`'s intake.
- **Write the reason on the flow side from `state.replan_archives(d)`** ("no archive" vs
  "archive unusable"). About 6 lines. It drops the detail the operator needs (which field is
  unfilled, or the `OSError`), and it re-derives part of `_parent_plan`'s decision, which the
  brief says not to do.
- **Keep the whole text and only add a lead-in.** That keeps "refusing to split" and the
  second remedy, which is exactly what the review flagged.

Failure mode of the cut: if `split.py` ever rewords " — refusing to split", the `partition`
cuts nothing and the line falls back to the full `SplitError` text. The information is still
correct; only the wording gets worse. `_assert_skipped` (test:169-180) then fails on
"refusing to split", which points back here.

Pinned by tests: `_assert_skipped` now also asserts that no "refusing to split" and no
"re-run" appear, and that "`pdca flow <id>`" appears exactly once.

## Point 3 — sweep compared against a control

`test_the_sweep_repairs_then_drives_like_the_control` (test:302) runs `pdca flow --from-csv`
over the repaired disk, then over a fresh post-#481 disk (brief left in place). It asserts that
the maps are equal, the rcs are equal, and 654 is not left BUILT. Observed (both runs):
`{'654': 'COMPLETE', '701': 'COMPLETE', '702': 'COMPLETE', 'BATCH1': 'COMPLETE',
'BATCH2': 'COMPLETE'}`, rc 0.

## Point 4 — claim release on all three intake paths

All three tests share one probe, `_assert_let_go(skipped, driven=…)` (test:182-194). It runs
INSIDE the first run's still-open `drive_claim.run` scope. From a second `drive_claim.Run` it
checks two things:

- the probe can NOT take a bundle the live run drives (`Refusal.held`), so the run's claims
  are still alive;
- the probe CAN take the skipped bundle.

So a pass means "this bundle was let go", not "the run already dropped everything".

- named ids: `flow.flow_ids(["654", "800"])` → probe 654 against driven 800 (test:258);
- sweep: `flow.flow_batch(csv=…)` → probe 654 against driven `BATCH1` (test:270);
- adoption: `flow.flow_ids(["500"])` with 500 terminal on a split into 654 + 656 → probe
  654 against adopted, driven 656 (test:280).

## (i) Observable end point

`pdca flow 654` (through `cli._flow`, stub leaves, `no_publish=True`, `no_act=True`):

- Repaired pre-#481 parent: `{'654': 'COMPLETE', '701': 'COMPLETE', '702': 'COMPLETE'}`, rc 0.
- Control (post-#481 disk): `{'654': 'COMPLETE', '701': 'COMPLETE', '702': 'COMPLETE'}`, rc 0.

The rebuilt `brief.md` is byte-identical to the one `split.accept` wrote for the same parent.
The parent goes down the close fast path to COMPLETE, and its children are adopted and driven.
For (ii), with no archive: `{'654': 'BUILT', '800': 'COMPLETE'}`, rc 1. The sibling is driven
and 654 is answered for.

## Refuting my own test

- **(a) Real red? Yes.** The project's C4 gate, run as
  `PDCA_BUNDLE=… PDCA_WORKTREE=… PDCA_BRIEF_BASE=origin/main ./engine/scripts/run-verify.sh`,
  gives: green leg `Ran 16 … OK`; red leg (production hunks reverted) `Ran 16 … FAILED
  (errors=13)`; then `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
  - All 13 errors are `FileNotFoundError: …/results/issue_654/brief.md`, the reported crash.
    That includes both new let-go tests and the control sweep test.
  - The 3 that pass on base are guards a careless fix could break: held claim not written,
    terminal parent not written, own brief byte-identical. The base never writes a brief, so
    they pass there.
  - Mutations, each run on the fixed tree and then restored:
    - **M1:** `_admit` without `claims.release(d)` → the 3 let-go tests FAIL.
    - **M2:** `_admit` calling `claims.close()` (drops every claim) → the same 3 FAIL, on the
      "driven bundle still held" probe. So the probe tells the two apart.
    - **M3:** iteration-1 wording (whole `SplitError` text plus a second remedy) → 4 FAIL:
      no-archive, refused-archive, sweep skip, adoption skip.
- **(b) Production path? Yes.** Every leg runs the real `cli._flow`, `flow.flow_ids`,
  `flow.flow_batch` and `_adopt_split_children`. The spies only record return values. The
  expected bytes come from the real `split.accept`. Claims are real flock claims through
  `drive_claim.run` / `drive_claim.Run`.
- **(c) Fixture includes the fault? Yes.** It is the real pre-#481 disk, built by production
  code: close marker `split`, lineage record, `iteration-v1/brief.md` from
  `driver._archive_iteration`, and the `brief.md` deleted. The test asserts it reads BUILT
  before the run. The held-claim leg takes a real claim from a second `drive_claim.Run`.

## Runs

- New module with the fix: 16/16 OK.
- T3 through `./engine/scripts/run-suite.sh`: root suite `Ran 24 … OK`; driver suite
  `Ran 2231 … OK (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- Commit-readiness: the target has no pre-commit config, formatter or linter config, and no
  installed hooks. `git diff --check` is clean, and no added line is over 100 columns (the
  file's style). DCO sign-off (`git commit -s`, AGENTS.md) is applied at publish.

## Housekeeping (for the human)

- **My mistake:** I sent the C4 gate's output to `/tmp/c4-597.log`, which is outside the roots
  I was given. It is a plain log of the run above and nothing reads it. It is safe to delete;
  the harness will not reclaim it.
- `results/issue_597/.fix-only.diff` is iteration 1's helper (its `flow.py` hunks). It is now
  stale and differs from this patch at points 1 and 2. Ignore it; `patch.diff` is canonical.
- `results/issue_597/test_flow_briefless_split_parent.py` has been updated to this
  iteration's test. It is byte-identical to the copy inside `patch.diff`.
- The worktree is left as base plus the patch: `flow.py` modified and the test untracked.
  The index is as I found it.
