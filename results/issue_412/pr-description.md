# Add a `Merges with` brief field; refuse such groups in merge mode

## Summary
**User impact:** with `wave_mode = "merge"`, two bundles that must land together (for example a caller and the code it calls) can be merged onto the base one at a time, so the base can end up with only half of the pair, and nothing warns you. There was also no way to tell the driver that bundles belong together.

This PR adds an optional brief field, `- **Merges with:** <id>[, …]`, for declaring such a group. In stack mode (the default) nothing changes. In merge mode, which cannot yet merge a group as one unit, the driver now refuses to build any group member it can see and tells you the two ways out, instead of risking a half-landed pair.

This is a fail-safe, not the full "hold one member and merge the group together" the issue asks for. That work, chained pairs, and the two gaps listed below move to #778, so this PR refers to #412 rather than closing it.

Reported in [#412](https://github.com/eduralph/pdca-harness/issues/412).

## What to look at
- **The rule:** a bundle is a group member if its own brief declares `Merges with`, or another brief in the same run names it there. One side declaring is enough.
- **The behaviour in merge mode:** `pdca flow A B` (A's brief says `Merges with: B`) stops before building anything and prints the group plus `Ways out:` (switch to `wave_mode = "stack"`, or fold the group into one bundle). The `--from-csv` sweep holds the group and anything that depends on it, and builds the rest. Bare `pdca waves` reports the group as unschedulable.
- **To try it:** set `[driver] wave_mode = "merge"`, add `- **Merges with:** B` to bundle A's brief, and run `pdca flow A B`. On `main` it builds both. With this PR it exits 2 and builds nothing. Set `wave_mode = "stack"` and it runs as before.
- **Known gaps (documented, tracked in #778):** a group declared only by a bundle *outside* the run is not seen, and splitting a bundle does not carry `Merges with` to its children. The docs tell you to declare the field on every member.
- **Accepted difference:** bare `pdca waves` refuses where the sweep holds. That matches how it already treats an unresolved `Depends on`.

## Root cause
Briefs had no field for an atomic merge group, so the wave planner (`waves.check_dep_graph` / `waves.partition_schedulable`) could not know two bundles belong together. In merge mode the driver merges each non-final wave's PRs one by one (`template/src/pdca_harness/flow.py:3078-3081` on `main`), so a group member in a non-final wave can land on the base alone.

## Fix
- `brief.merges_with()` parses the field the same way as `conflicts_with` (ids only on the value line, trailing note ignored, `#12` / `12` / `issue_12` all accepted).
- `waves.merge_groups()` builds the groups from the briefs in the run, reading the field from both sides like `conflict_map` does. Unlike `conflict_map`, it keeps a partner outside the run, because a member merged without that partner is still half a group.
- `waves.check_dep_graph()` (the strict path behind `pdca flow <ids>` and `pdca waves`) raises `DependencyGraphError` with the two ways out when `wave_mode == "merge"` and any group exists. This check runs after the existing dependency and cycle checks, so those refusals keep their current messages.
- `waves.partition_schedulable()` (the tolerant path behind the `--from-csv` sweep and split-child adoption) holds every in-run member, with a reason naming `Merges with` and the same ways out. It does this before the existing hold propagation, so dependents are held with no new code.
- One template line in `template/templates/brief.md.tpl`, next to `Conflicts with`. Docs: a new optional-field bullet in `docs/03-plan.md`, and a paragraph at the end of the `"merge"` bullet in `docs/07-crosscutting.md`.
- No change to `merge.py`, `flow.py`, `cli.py`, `config.py` or `split.py`.

Single-wave groups are refused too, on purpose. The driver does not merge the final wave, but a later merge-mode run (a resume, or a batch where another bundle depends on one member) can pick the open PRs up and merge them one at a time. A brief cannot know which runs will follow.

## Verification
- **Claim:** the field parses like `Conflicts with`.
  **Checked:** `template/src/pdca_harness/brief.py:218-224` on `main` (`conflicts_with` → `field(...)` → `_id_list` at :347); the new parser reuses that path.
  **Test:** `MergesWithField.test_parses_like_conflicts_with` compares both parsers on the same values.
- **Claim:** in merge mode, a strict run with a group member is refused before any build, whichever side declares it, including a single member whose partner is outside the run.
  **Checked:** `template/src/pdca_harness/waves.py:65` (`check_dep_graph`) on `main`, which every strict caller reaches through `compute_waves`. `template/src/pdca_harness/cli.py:673-679` already turns `DependencyGraphError` into exit 2 plus `Ways out:`.
  **Test:** `MergeModeStrict` (4 tests, covering each id spelling); `FlowRefusesAGroup.test_flow_refuses_with_rc2_and_builds_nothing` drives `cli._flow` and checks exit 2, no traceback, `Ways out:` on stderr, no build, and both bundles still PLANNED.
- **Claim:** the tolerant sweep holds the group and its dependents and schedules the rest, without raising.
  **Checked:** `template/src/pdca_harness/waves.py:275-313` on `main` (`partition_schedulable`, the unresolved-dependency hold at :309, propagation at :313).
  **Test:** `MergeModeTolerant.test_holds_the_group_and_its_dependent_and_keeps_the_rest` (A `Merges with` B, C depends on A, D free: only D is scheduled). This path is tested with A declaring; the partner-only and outside-partner cases are tested on the strict path only, and a follow-up can add them here.
- **Claim:** stack mode is unchanged.
  **Test:** `StackModeUnchanged.test_same_result_as_without_the_field` gives the same waves and the same partition with and without the field, across all batches above.
- **Claim:** bare `pdca waves` in merge mode reports the group.
  **Checked:** `template/src/pdca_harness/cli.py:1095` on `main` (`compute_waves` → `unschedulable:`, exit 1).
  **Test:** `WavesPreviewRefusesAGroup.test_bare_waves_reports_the_group_unschedulable`, through `cli.main(["waves"])` with a real `pdca.toml`.
- **Regression test:** `template/tests/test_merge_group.py` (new, 9 tests). With the production changes reverted it fails 8 of 9 tests (11 assertion failures counting sub-tests; no import errors). The stack-mode test passes both ways, as intended. With the patch, all 9 pass.
- **Suites:** offline driver suite `Ran 2639 tests … OK (skipped=2)`; root render suite `Ran 24 tests … OK` (needed because the brief template changed); docs lint and link check OK.

Refs #412
