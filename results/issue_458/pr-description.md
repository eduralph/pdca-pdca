## Summary
**User impact:** When `pdca split` breaks an oversized work item into smaller children, each child can still score oversized — its brief inherits the parent's difficulty, its dependency tokens, and the "conflicts with" entries naming its own siblings, which the split itself wrote. The size advisory answered every such child with the same "consider `pdca split` first" its parent got, so an operator following the driver's advice would keep re-splitting slices that are already as narrow as they can get — the same advice at every depth, and the planning prompts pointed at `pdca split` again too.

This PR makes the advisory read where a child's size came from: a score carried by conflicts with the child's own split siblings is named as inherited ("prefer building over re-splitting"), while a child oversized on its own evidence keeps the ordinary split advice unchanged.

Reported in [#458](https://github.com/eduralph/pdca-harness/issues/458).

## What to look at
Three small surfaces, one decision. The advisory now asks a single new question before its existing forks — does the size estimate report conflicts that name this child's own split siblings? If yes, the message names the split the child came from and says the size is inherited; if no (even for a split child), nothing changes. The same one-sentence note travels with the planner and splitter prompts, since the next planning session reads the brief before the advisory runs again. The process flowchart in the docs gains the matching fork.

To see the defect: give a bundle a split-lineage record and a brief whose only conflicts are the siblings that record lists — before this change the advisory prints the parent's own "consider `pdca split` first"; after it, the provenance line. Deleting the stale sibling entries brings the ordinary advice back, with no model sizer involved.

## Root cause
`size_reasons` chose the split remedy off its `splittable` predicate, whose churn readout is true whenever structural churn alone fired — exactly the readout a split inflates, because every materialised child declares its siblings under `Conflicts with:` (`template/src/pdca_harness/plan_policy.py:134-141` pre-fix). Nothing in the remedy path consulted the provenance signal sizing already publishes for this case — `SizeEstimate.sibling_conflicts` (`template/src/pdca_harness/sizing.py:215`, computed at `:324-325`, added by b4c924d6832bba0450ff39e4c7bf2d8c2d96a112 / #457) — so every level of a split recursion saw the same inputs and gave the same advice.

## Fix
- `template/src/pdca_harness/plan_policy.py` — the provenance question is asked **before** the readout fork: `if before_do and est.sibling_conflicts:` (`:189` post-fix) emits "scores large for a split child (child N of a split of #X, depth D) — driven by inherited/sibling fields; prefer building over re-splitting" plus an explicit "; N sibling conflict(s) not counted" beside the scored reasons. The new `_split_child_provenance` helper (`:88` post-fix) only formats ids — the decision is the count sizing exposes, never the presence of a lineage record (presence would assert inheritance over a child whose conflicts are all organic). All other branches are untouched; with no sibling conflicts the added `extra` stays empty, so output is byte-identical.
- `template/src/pdca_harness/leaves.py` — shared `_split_provenance_note` (`:524` post-fix), injected into `_plan_prompt` (`:610`) and `_split_prompt` (`:1294`). The prompt note gates on presence of the child edge — "your `Conflicts with` may be inherited — check" is true of every child — unlike the advisory, whose claim about the score needs the count.
- `docs/07-crosscutting.md`, `### The process` only — Entry A's flowchart gains the sibling fork and its remedy node, Entry B's node states it does not fork (a built bundle routes through iterate-plan either way), plus one prose paragraph.

## Verification
All checks below ran against `pdca-integration/main` at ef00e6ed2020c7f84a67b8df91cf0504f294418e (which carries #457's signal via PR #483).

- **Claim:** a child whose oversized score is carried by sibling conflicts gets the provenance line, never "consider `pdca split` first".
  **Checked:** `template/src/pdca_harness/plan_policy.py:189-201` post-fix — the branch fires on the count and precedes every other fork, so it is reachable both when churn is oversized and in the `churn=watch`/`patch=oversized` shape #457 leaves behind.
  **Test:** `test_i_*` (3 tests), including a mixed fixture asserting both the scored organic count and the uncounted sibling count appear.
- **Claim:** zero sibling conflicts (even with lineage) keeps the ordinary split remedy and never the inherited-fields line.
  **Test:** `test_ii_organic_conflicts_keep_the_ordinary_split_remedy`.
- **Claim:** the recovery works on the sizer this project ships, not only a paid one.
  **Checked:** `template/src/pdca_harness/leaves.py:1252` — `_stub_sizer` returns `{"band": "ok"}` unconditionally, so a recovery gated on the sizer's verdict would be dead config offline. **Test:** `test_iii…` runs the real stub through `plan_policy.evaluate`, re-reads `sizing.json` (`stub: True`, `band: "ok"`) on both legs, then drops the sibling entries and asserts the ordinary remedy returns.
- **Claim:** a bundle that already has a patch keeps its iterate-plan wording; a bundle with no lineage is byte-identical.
  **Test:** `test_iv…` and `test_vi…` (full-string equality).
- **Claim:** both prompts gain exactly the one note and nothing else.
  **Test:** `test_v…` — full-prompt equality after removing the note, built twice off one bundle differing only in the lineage record.
- **Regression test:** `template/tests/test_plan_policy_split_child.py` (9 tests, one module so the invariance halves can only go green together with the fix). With the production hunks reverted on ef00e6e: 4 failures + 2 errors, all 9 executed; with the patch applied: 9/9 OK.
- **Suites on the same base:** docs lint + full site render/link audit (22 pages) green; root render and `copier update` compatibility suites green with copier 9.17.0 importable (7 tests, 0 skips); offline driver suite green (1700 tests).

Fixes #458
