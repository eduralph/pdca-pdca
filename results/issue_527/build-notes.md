# Build notes — issue 527 / section6-keeps-whole-needs-human-bullet

## What changed and why

`_needs_human` (`template/src/pdca_harness/assemble.py:454-525` on the target base
`6ba00ba`) parsed `review_text.splitlines()` line by line and, for a `- NEEDS-HUMAN`
bullet, took only the stripped current line
(pre-fix `assemble.py:465-468`). Any continuation lines — the bullet's objection
wrapped onto indented lines below it — were silently dropped. That is the exact
defect the brief describes and the two real cases it cites (`results/issue_462` and
`results/issue_472` in pdca-pdca).

The fix turns the `for i, line in enumerate(lines)` loop into a `while i < n` loop so
a bullet match can consume more than one line before advancing `i`
(`assemble.py:484-517` post-fix). When a line strips to `- NEEDS-HUMAN…`, the fix
records the bullet's own indentation, then walks forward absorbing every following
line that is indented deeper than the bullet, stopping at the first line that is
blank, no deeper than the bullet, or matches
`_ends_needs_human_continuation` — a new list item at any indent (`-`, `*`, `+`,
`1.`), a heading (`#`), a table row (`|`), or a code fence (`` ``` ``/`~~~`)
(`assemble.py:60-73`, the new `_LIST_ITEM_RE` / `_CODE_FENCE_RE` /
`_ends_needs_human_continuation`). The absorbed lines are stripped individually and
joined with single spaces — never a newline, because `collect_needs_human`'s caller
renders each item as `f"- [ ] {it}"` (`assemble.py:559` unchanged) and a second
physical line would drop off the checkbox and out of
`signoff.open_needs_human`'s line-based count (`signoff.py:116-120`, cited in the
brief).

The table branch (`elif s.startswith("|") and "needs-human" in s.lower(): …`) is
untouched in substance — only re-indented one level to live inside the `while` and
renamed its loop variable `j`→`k` to avoid colliding with the new continuation-scan
index `j`. Every other line (`_verdict_table_lines`, `_classify_finding`,
`_items_from_artifact`, `collect_needs_human`) is unchanged.

## Peer callsite followed

The brief names `brief._block_for` / `whole_field` (`brief.py:37-106`, #336) as the
pattern to mirror for "membership by indentation deeper than the field's own
bullet." I read only that cited callsite (`brief.py:70-104`) — its rule is: a
continuation line is one indented deeper than the field's bullet; a sibling field,
a heading, or an unindented line ends the block. I reused that indentation test
(`cont_indent <= bullet_indent` ⇒ stop) but did NOT reuse `_block_for`'s
dedent-and-keep-as-block output: `whole_field` returns a multi-line block (a brief
field can span the SUMMARY §1 rendering as several lines, via `_item`'s two-space
continuation indent, `assemble.py:109-125`), but a §6 item is always one
`- [ ] …` Markdown line, so the brief explicitly calls for flattening
("the result is flattened to one line rather than kept as a block"). I did not
import or call anything from `brief.py` — the two parsers solve the same shaped
problem over differently-shaped outputs, so copying the pattern (indentation
membership) and not the code was the right amount of reuse.

## Alternatives ruled out

- **Regex-based multi-line match** (e.g. a single regex over the whole text with
  `re.MULTILINE` and a lookahead for the next boundary) — rejected: the boundary
  rule has five distinct stop conditions (blank, dedent, new-list-item-at-any-indent,
  heading, table-row, code-fence) that are easiest to express and to read as
  sequential line-by-line checks, exactly as `_block_for` does. A single regex
  encoding all five would be far harder to verify by inspection and diverge further
  from the peer pattern the brief points at.
- **Recursive-descent over a real Markdown parser** — rejected on cost: this repo
  has no Markdown-parsing dependency anywhere in `assemble.py` or its imports
  (`assemble.py:9-19`), and pulling one in for a single-function fix is a new
  dependency for a five-line boundary rule already solved locally by `_block_for`
  without one.
- **Keep dropping continuation lines but WARN in §6 that the bullet was
  truncated** — rejected: this is a guard on the symptom (acknowledging the
  truncation) rather than removing the cause (the truncation itself), and it does
  not satisfy the brief's success criterion (a), which requires the item's *text*
  to be the full joined sentence, not a truncated one plus a warning.

## Test

New file `template/tests/test_needs_human_multiline.py`, 10 cases across three
classes:

- `WrappedBulletBecomesOneItem` — the brief's own repro shape (a),
  end-to-end through `assemble.collect_needs_human`, the rendered `SUMMARY.md` §6
  checkbox line, and `signoff.open_needs_human`'s count.
- `ContinuationBoundaries` — each of criterion (b)'s five boundary conditions
  (two consecutive bullets, an indented sub-bullet, a blank line, a heading, a
  plain dedent).
- `ClassificationUnchanged` — criterion (c): a
  multi-line `[impl]` bullet is still one IMPL item with the marker stripped
  (mirrors `test_autoiterate.py:130-135`'s
  `test_advisory_impl_marker_auto_iterates_and_text_is_clean`), plus a
  single-line-bullet regression case.

Fixture mirrors `test_autoiterate.py:77-95`'s `_bundle` and
`test_external_dependency_section6.py`'s `_bundle` (a PASS-gate bundle with a clean
primary review, so §6 is fed only by the one advisory artifact under test).

Criterion (d) — the existing suites — verified by running the FULL offline suite
(`template/tests`), not just the four named files, via
`PYTHONPATH=src python3 -m unittest discover -s tests`: 1798 tests, 2 skipped
(pre-existing, unrelated to this change), 0 failures, exit 0. `make check` (the
project's own runner, `template/Makefile:73-74`) gives the identical result.

## Refute-your-own-test checklist

**(a) Genuine red?** Yes. I set the source change aside with
`git stash push -u -m issue527-wip -- template/src/pdca_harness/assemble.py` (the
new test file was untouched/untracked, so it stayed in place) and re-ran
`python -m unittest tests.test_needs_human_multiline -v`: 9 of 10 cases failed with
real assertion failures (e.g. `AssertionError: 'overshoots' not found in
'src/x.py:12 (\`f\`):'`, `AssertionError: 0 != 1` for the SUMMARY checkbox line and
the signoff count). Only `test_single_line_bullet_is_unaffected` stayed green,
exactly as expected — it exercises the untouched single-line path. I then
`git stash apply <sha>` + `git stash drop stash@{0}` to restore the fix (never a
bare `stash pop`, per the worktree's shared-stash warning) and re-ran: all 10 green.

**(b) Production path?** Yes. The test calls `assemble.collect_needs_human`,
`assemble.assemble_summary`, and `signoff.open_needs_human` directly — the exact
three functions the brief names as pre-existing API — against real `Config` /
`gates.run_gates` bundle plumbing, not a mock or a re-implementation of the parser.

**(c) Fixture includes the fault?** Yes. The advisory artifact text
(`_WRAPPED_IMPL_BULLET`) is the brief's own repro shape verbatim — a real multi-line
`- NEEDS-HUMAN [impl] — …` bullet, the 462/472 shape — written to
`check-advisory-adversary.md` in a bundle whose gate passes and whose primary
review is clean, so the wrapped bullet is the ONLY thing that can produce a §6 item.
No node/backend was curated out here (this is a pure-function defect, not a
distributed-systems one), but the fixture is the real defect shape, not a
simplification of it.

## External dependencies

None. Offline, stdlib `unittest`, no Docker/network — matches the brief's
`External dependencies: none`.

## Formatter / commit-hook check

No `.pre-commit-config.yaml`, `pyproject.toml` (only a Jinja template,
`template/pyproject.toml.jinja`, with no `[tool.black]` / `[tool.ruff]` section),
`.flake8`, or `ruff.toml` exists anywhere in this repo, and neither
`.github/workflows/*.yml` runs a Python formatter or linter (only
`docs/publishing/tools/lint_docs.py`, a Markdown doc linter, unrelated to
`template/src` or `template/tests`). There is no configured formatter/lint hook for
this repo's Python source to run before commit. I matched the surrounding file's
existing style by hand (double-quoted strings, ~95-char lines, module-level
docstrings, the existing regex-constant naming convention).
