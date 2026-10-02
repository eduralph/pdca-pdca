## Summary
**User impact:** When you split an issue into child issues, the parent issue gets
closed as "not planned" (with a comment saying the review chose not to fix it) the
first time you run `pdca cleanup --apply` after the parent is signed off, even while
its children are still being built. Anyone reading the tracker sees work marked as
dropped when it was only moved. Separately, nothing stops a slice from being split
again and again (one instance went three levels deep), which opens issues faster
than the cycle can close them.

This PR keeps a split parent's issue open until all of its child issues are closed,
then closes it with a comment listing every child. It also makes
`pdca split <id> --accept` refuse, by default, to split a bundle that is already two
splits deep; `--force` overrides the refusal.

Reported in [#545](https://github.com/eduralph/pdca-harness/issues/545).

**This does not do what the issue's first acceptance line asks.** The issue proposes
closing the parent right away at `split --accept`. This PR keeps it open on purpose:
a parent closed before its children land looks finished or dropped when it is
neither. So an open parent still counts as open work in the milestone until its
children are done. A `split` label that milestone views could filter out would
address that; it is not part of this PR.

## What to look at
- **Parent close:** `pdca cleanup` has one new rule for a finished split parent
  whose issue is still open. It looks up each child issue on the tracker. If any
  child is still open, or its state can't be read, it reports "waiting on #…" and
  changes nothing. Once all children are closed it closes the parent: as
  "completed" if at least one child was completed, otherwise as "not planned". The
  closing comment always names every child. If the children list can't be read in
  full, it says so and leaves the close to a human.
- **Depth bound:** `pdca split <id> --accept` checks the depth recorded when the
  bundle was created by an earlier split. An issue and its children can be split;
  a grandchild cannot, unless you pass `--force`. The refusal happens before
  anything is filed on the tracker.
- **Wording:** the planner prompt says `--force` is the human's decision, so the
  planner agent does not add it on its own when it hits the refusal. Please read
  that paragraph.
- **To try it:** run `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_split_parent_lifecycle`. The tests fake only `gh` and go through the
  real `cleanup.run`, `cli._split` and `cli.main` entry points.

## Root cause
A split parent has no patch of its own, so `cleanup` put it in the generic "finished
with an empty patch → close as not planned" case (`cleanup.py:329-335` on `main`) and
never looked at its children. If the parent had been published before it was split,
the recorded-PR check could also close it as "Fixed by …" while its children were
open. `split --accept` recorded each child's depth but never checked it.

## Fix
- `template/src/pdca_harness/cleanup.py:398-403`: in the COMPLETE + issue-OPEN
  branch, a split parent (`flow._is_split_parent`) is decided **first**, ahead of the
  recorded-PR checks and the empty-patch close. It goes to the new
  `_split_parent_row` (`cleanup.py:235-307`), which reads the children with the
  existing `split.read_lineage` / `flow._lineage_children`. It closes only when the
  reader kept every entry of the list: `["601", null]` with #601 closed does not
  close the parent. A child id that is not a number (a non-GitHub tracker id) is
  report-only, "close by hand". The close reason is read from `stateReason`
  regardless of case, because the real `gh` prints `COMPLETED` / `NOT_PLANNED`.
- `cleanup.py:169-191`: `_close_issue` gains `prefer_bundle_comment` (default
  `True`, so ordinary bundles behave as before). The split parent passes `False`
  and builds its own body: any hand-written `tracker-comment.md` text, then the
  child list. The child list is never dropped.
- `template/src/pdca_harness/split.py:298-316`: `MAX_SPLIT_DEPTH = 2` and
  `check_depth`, called from `preflight` (`split.py:349`) before any `gh issue
  create`. A damaged lineage record reads as depth 0 through the existing
  `_recorded_depth` and is never refused.
- `template/src/pdca_harness/cli.py:197-200`: new `--force` flag on `split`.
  `cli.py:814` reads it with `getattr(..., False)` so existing callers that build
  a namespace without it keep working unchanged.
- Docs and prompts: the cleanup table (`docs/07-crosscutting.md:673`), `cleanup`'s
  module docstring, `template/agents/planner.md.jinja:164-175` and the splitter
  comment in `template/pdca.toml.jinja:513-518`.

**Known gap:** if a forced split files the child issues and then the accept step
fails, the retry command it prints (`cli.py:877-879`, `split.py:1329-1333`) leaves
out `--force`, so pasting it as-is gets refused. The refusal message names
`--force`, so nothing is lost. The hint fix is left for a follow-up.

## Verification
- **Claim:** a split parent is never closed while a child issue is open or
  unreadable, including when it carries a merged PR from before the split.
  **Checked:** `cleanup.py:398-403` (runs before the PR checks) and
  `cleanup.py:235-307`. **Test:** `test_p1_…`, `test_p4_…`, `test_p9_…`
  (`template/tests/test_split_parent_lifecycle.py:129`, `:178`, `:281`). They fail
  on `main`, where the P1 case issued `gh issue close 500 --reason "not planned"`
  with child #601 still open, and pass with this change.
- **Claim:** once all children are closed, the parent closes as completed (or
  not planned if no child was completed), and the comment names every child even
  when `tracker-comment.md` exists. **Test:** `test_p2_…`, `test_p3_…`,
  `test_completed_is_read_without_regard_to_case`, `test_p8_…` (`:139`, `:157`,
  `:171`, `:269`).
- **Claim:** a missing, empty or partly damaged children list, or a non-numeric
  child id, never closes the parent. **Test:** `test_p5_…` ×2 and
  `test_a_child_id_that_is_not_a_tracker_number_is_closed_by_hand` (`:188`, `:210`,
  `:237`).
- **Claim:** unchanged behaviour elsewhere: a dry run makes no calls, and an
  unsplit empty-patch bundle still closes as not planned. **Test:** `test_p6_…`,
  `test_p7_…` (`:251`, `:259`). The existing
  `test_complete_close_disposition_closes_not_planned` and
  `test_bundle_tracker_comment_file_is_preferred` (`template/tests/test_cleanup.py`)
  pass unchanged.
- **Claim:** `split --accept` refuses depth ≥ 2 without `--force`, files nothing,
  and accepts with `--force`. Depth 0/1 and damaged records are accepted as before.
  **Checked:** `split.py:298-316`, `:349`; `cli.py:197-200`, `:814`. **Test:**
  `test_d1_…` ×3, `test_d2_…` ×2 (two of them through the real argparse
  `cli.main`), `test_d3_…`, `test_d4_…` (`:345-404`).
- **Claim:** the planner prompt says the parent stays open, does not promise a
  "completed" close, and says `--force` is the human's decision. The cleanup
  docstring names the new rule. **Test:** `:424`, `:433`, `:443`.
- **Red/green:** with every non-test change reverted, the new module runs and fails
  (23 assertion failures, no import errors). With the change, all 21 tests pass.
- **No regressions:** `tests.test_split` passes (109 tests) with its prompt-wording
  suites unchanged. The full offline driver suite passes (2092 tests, 2 skipped),
  as do the root render suite (24 tests) and the docs lint, site render and link
  audit.

Fixes #545
