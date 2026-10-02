# Advisory code review — issue 545 (split-parent-closes-with-children-bound-depth)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Advisory only; nothing here gates.

Overall the diff is clean. The split-parent rule sits ahead of the recorded-PR checks
(`template/src/pdca_harness/cleanup.py:398-403`). It reuses `_close_issue`, `_issue_state`,
`split.read_lineage`, `flow._lineage_children` and `flow._is_split_parent` instead of copying
them. The "whole list or nothing" guard (`cleanup.py:255`) correctly closes the
`["601", null]` hole from iteration 1. The depth check is one named constant
(`split.py:298` `MAX_SPLIT_DEPTH`), and it runs in `preflight` before anything is filed. Gate logs:
C4 red→green, T3 suite `Ran 2092 tests … OK`.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/cli.py:877-879` (and the partial-filing hint
  at `template/src/pdca_harness/split.py:1329-1333`): these are the resume commands printed after
  child issues were **already filed** and the accept step failed. They are
  `split <id> --accept --ids …` with no `--force`. The patch adds a depth refusal to `preflight`
  (`split.py:349`), and `preflight` also runs on the `--ids` path (`cli.py:814`). So on a
  forced depth-≥2 split, copying the printed command exactly gets refused. That happens on the
  one path whose comment says the hint "is the whole guarantee" against orphaned issues. The
  refusal message does name `--force`, so nothing is lost for good. Still, the printed command is
  wrong. Fix: append ` --force` to the hint when `args.force` was set (the split.py hint would
  need the flag passed in). Also add a test for the forced-then-failed-accept hint.
- `template/src/pdca_harness/cleanup.py:255` — the guard compares
  `len(flow._lineage_children(record))` to `len(record["children"])`. So it depends on the
  private reader's filtering rules (drop only; never merge or coerce). If `_lineage_children`
  ever starts coercing `602 → "602"` or de-duplicating, this guard's meaning changes without
  anyone noticing. A direct check here is simpler and doesn't depend on that:
  `raw = record.get("children"); if not isinstance(raw, list) or not raw or not all(isinstance(c, str) and c.strip() for c in raw): …`.
  Minor, and the comment at `:249-254` explains the current coupling.
- `template/src/pdca_harness/cleanup.py:57` — `cleanup` now imports all of `flow` (which pulls in
  most of the package) just to use two private helpers. There's no import cycle (T3 is green),
  but `pdca cleanup` now loads the flow's import graph. The brief asked for this reuse
  (citation (d)), so this is only a note. Moving `_lineage_children` / `_is_split_parent` into
  `split.py` (next to `read_lineage`) would be the cleaner home. That's out of scope here.
- `template/src/pdca_harness/cli.py:197-200` — `--force` without `--accept` is accepted and
  silently ignored on the draft `pdca split <id>` step. That's harmless, and the brief puts
  draft-step behaviour out of scope. It's listed only so a reviewer isn't surprised by it.

No resource leaks, off-by-one errors or concurrency problems found. The `lambda` at
`cleanup.py:306-308` binds per call (it's created inside `_split_parent_row`), so there's no
late-binding bug across bundles. The new tests go through the production entry points
(`cleanup.run`, `cli._split`, `cli.main`). The P5 mixed cases, P8's hand-written note check and
the upper-case `stateReason` fixtures all exercise the fix itself, not a copy of it.
