## Summary
**User impact:** when a review finding that needs a human decision runs longer than one
line, the sign-off checklist in `SUMMARY.md` shows only its first line. The person signing
off sees a question that stops mid-sentence (for example just ``src/x.py:12 (`f`):``) and has
to open the review file to find out what they are being asked to decide. This hits anyone
clearing that checklist; reviews in real cycles have produced several such cut-off items.

This PR keeps the whole finding: its wrapped lines are joined into the same single checklist
line.

Reported in [#527](https://github.com/eduralph/pdca-harness/issues/527).

## What to look at
The change is in one function, the parser that turns review files into checklist items in
`SUMMARY.md`. A finding's wrapped lines (indented under it) now join onto it. A blank line,
a line back at the same indent, another list item, a heading, a table row, or a code fence
ends the finding. So two findings in a row stay two checklist items.

To try it: write a review file in a bundle whose finding wraps, e.g.

```
- NEEDS-HUMAN [impl] — src/x.py:12 (`f`):
  the bound counts sleep seconds, not
  wall-clock time, so it overshoots.
```

then build the summary. Before this change the checklist item ends at ``(`f`):``. After it,
the item reads the whole sentence through "so it overshoots." on one `- [ ]` line, and
sign-off counts it as one open item.

## Root cause
`_needs_human` walked the review text one line at a time and, for a `- NEEDS-HUMAN` bullet,
kept only the stripped current line; the indented lines below it were never joined. Every
file that feeds the checklist goes through this parser (`check-review.md`,
`check-advisory-*.md`, `plan-advisory-*.md`), so all of them were affected.

## Fix
- The `for` loop becomes a `while` loop, so a bullet can consume its continuation lines
  before the index moves on (`template/src/pdca_harness/assemble.py:489-522`).
- On a bullet, it records the bullet's indent and absorbs each following line that is
  indented deeper, stopping at a blank line, a line no deeper than the bullet, or a line
  that `_ends_needs_human_continuation` flags: a list item at any indent (`-`, `*`, `+`,
  `1.`), a heading, a table row, or a code fence (`assemble.py:60-77`).
- The parts are stripped and joined with single spaces, never a newline. Each item renders
  as one `- [ ] …` line (`assemble.py:603`, unchanged), and `signoff.open_needs_human`
  counts open items per line, so a second physical line would drop out of the open-item
  check.
- The table-row branch is unchanged in behavior. It is re-indented into the new loop, its
  early `continue` becomes `if vi is not None:`, and its inner index is renamed `j`→`k` so it
  does not clash with the new scan index.

The indent rule follows the one `brief._block_for` already uses for wrapped brief fields
(`template/src/pdca_harness/brief.py:70-104`, #336). That helper is not reused directly: it
keeps a multi-line block and treats blank lines as inside it, while a checklist item must be
one line.

Out of scope: findings split into several paragraphs (a blank line still ends the item), and
the table-row path.

## Verification
- **Claim:** a wrapped `- NEEDS-HUMAN` bullet becomes one checklist item holding its full
  text, on one line, counted once at sign-off.
  - **Checked:** `template/src/pdca_harness/assemble.py:494-512` (continuation scan and
    space join); rendering at `assemble.py:603`; line-based count at
    `template/src/pdca_harness/signoff.py:102-122` on `main`.
  - **Test:** `template/tests/test_needs_human_multiline.py:76-100` — the item text, the
    rendered `SUMMARY.md` checkbox line, and the `open_needs_human` count.
- **Claim:** the item ends at the right place — consecutive bullets stay separate, an
  indented sub-bullet stays its own item, and a blank line, heading, or dedent ends it.
  - **Checked:** `assemble.py:60-77` and `:501-507` (stop conditions).
  - **Test:** `test_needs_human_multiline.py:103-156` (`ContinuationBoundaries`). The other
    list markers (`*`, `+`, numbered), table rows, and both fence styles were also checked
    directly against the parser during review.
- **Claim:** classification is unchanged — a wrapped `[impl]` bullet is still one IMPL item
  with the marker stripped, and single-line bullets give the same text as before.
  - **Checked:** `_IMPL_MARKER_RE` and `_classify_finding` are untouched; the table branch
    at `assemble.py:513-521` keeps the same STANDING check against the precomputed
    verdict-table rows.
  - **Test:** `test_needs_human_multiline.py:164-175` (`ClassificationUnchanged`).
- **Red → green:** with the `assemble.py` change removed, 9 of the 10 new tests fail with
  real assertion errors (e.g. ``'overshoots' not found in 'src/x.py:12 (`f`):'``); only the
  single-line case passes, as expected. With the change, all 10 pass.
- **No regressions:** the full offline driver suite (`template/`,
  `PYTHONPATH=src python3 -m unittest discover -s tests`) passes — 1798 tests, 2 skipped
  (existing skips), including `test_autoiterate.py`, `test_plan_advisory.py`,
  `test_external_dependency_section6.py` and `test_leaf_status.py`. Docs lint and site
  render also pass.

Fixes #527
