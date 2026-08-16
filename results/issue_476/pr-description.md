## Summary
**User impact:** The published documentation describes the split-lineage reader doing
something it has never done, so anyone who checks the code against the docs concludes that
correct code is broken. That is not hypothetical — a review of this area raised failures
against an implementation that was right, and every later reader of that page walks into
the same trap.

This corrects the one paragraph that makes the false claim, so the page describes the
reader that actually ships. Reported in
[#476](https://github.com/eduralph/pdca-harness/issues/476).

## What to look at
One paragraph in the split-lineage section of the crosscutting-concerns page. Nothing
else changes — no production code, no tests, no other paragraph.

To see the mismatch for yourself: read the paragraph's sentence about when the lineage
reader gives up and returns nothing, then run the lineage tests offline from `template/`
with `PYTHONPATH=src python3 -m unittest tests.test_split_lineage -v`. The test named
`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` passes today and
asserts the opposite of what the old sentence claimed: a hand-edited record whose depth is
the word `"one"` is handed back rather than rejected, the child is written at depth 1, and
the parent's own value is left untouched.

## Root cause
The paragraph listed "a `depth` that isn't a number" among the conditions under which
`split.read_lineage` returns `None`, but the reader only refuses a file it cannot turn
into a version-1 record; `{"depth": "one"}` clears every one of those checks and is
returned intact. The unusable value is handled a layer down by the depth arithmetic, and
the parent's record survives by a third route — the merge — so the single sentence
conflated three mechanisms and got the first one wrong.

## Fix
The sentence is replaced by wording taken from the reader's own docstring: it abstains on
anything it cannot turn into a version-1 record — absent, unreadable, malformed JSON, a
non-object payload, an unrecognised `version` — with the first three covering any failure
to parse the file at all (down to bytes that aren't valid UTF-8) and the last two parsing
cleanly but being turned away on shape and version. A non-numeric `depth` is then placed
in neither group: the reader returns the record, the depth arithmetic counts the value as
unknown (`0`) so the child lands at depth 1, and a separate sentence attributes the
parent's surviving `"one"` to the merge copying an existing `depth` through rather than
recomputing it. The closing rationale sentence is untouched, and no other paragraph is
edited.

## Verification
- **Claim:** the paragraph's list of cases that return `None` is exactly the reader's.
  **Checked:** `template/src/pdca_harness/split.py:606-612` on `main` — the only two
  `return None` sites are the total `except Exception` around the read and parse
  (`:606-609`) and the shape/version test on already-parsed data (`:610-611`); anything
  passing both is returned at `:612`. The new wording is lifted verbatim from the reader's
  own docstring at `:586-587`, so prose and contract are single-sourced.
- **Claim:** a non-numeric `depth` is not one of those cases, and the child still lands at
  depth 1. **Checked:** `template/src/pdca_harness/split.py:615-631` — `_recorded_depth`
  answers `0` for anything that is not a non-negative, non-boolean `int`, and the caller
  adds 1.
- **Claim:** the parent keeping `"one"` is a different mechanism, not a consequence of that
  arithmetic. **Checked:** `template/src/pdca_harness/split.py:643-657` — the merge copies
  `parent` / `siblings` / `depth` from the existing record (`:654-656`) and never calls
  `_recorded_depth`, so the value survives regardless.
- **Test:** `template/tests/test_split_lineage.py:236-253`
  (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number`) already pins this
  behaviour — child depth `1`, parent's depth still `"one"`. This change is prose only and
  adds no test; to confirm the new sentence is falsifiable rather than merely plausible, I
  temporarily made the reader do what the old sentence claimed (return `None` on a
  non-numeric `depth`) and that test failed immediately; reverting restored green. The
  individual `None` cases are pinned at `:133`, `:136`, `:141`, `:145`, `:149`, `:155`, and
  "never raises" at `:174`.
- **Checks run on the patched tree:** the repository's own documentation checks —
  `docs/publishing/tools/lint_docs.py` and `docs/publishing/tools/render_site.py --check`,
  the two that `.github/workflows/docs-check.yml` runs — are clean (syntax lint, site
  render, internal-link audit), and the offline suite from `template/`
  (`PYTHONPATH=src python3 -m unittest discover -s tests`) reports 1758 tests OK
  (2 skipped), with `tests/test_split_lineage.py` green at 23 tests.

Fixes #476
