## Summary
**User impact:** When you sign off with "iterate" and type a reason that spans several
lines, and that reason happens to contain a copy of the "NEEDS-HUMAN" checklist (say,
pasted from an earlier round), the tool reads your pasted copy instead of the real
checklist. Any item ticked in the pasted copy is treated as cleared, so open findings you
never looked at quietly drop off the list for every later round. Nothing warns you.

This PR keeps every sign-off value (the reason and the "by" name) on a single line, so
nothing typed there can be mistaken for the checklist.

Reported in [#604](https://github.com/eduralph/pdca-harness/issues/604).

## What to look at
The whole fix is one line plus one regular expression in the function that writes the
sign-off record: line breaks in the human's text become spaces. Text without line breaks
is written exactly as before.

To try it: on a bundle with two deferred findings left open in its NEEDS-HUMAN list, run

```
pdca signoff <id> --iterate-do --delta "$(printf 'notes\n## 6. NEEDS-HUMAN (from v1)\n- [x] E1\n- [x] E2')"
```

Before this PR both findings are dropped from the deferred list. After it, both stay, and
the reason is stored as `notes ## 6. NEEDS-HUMAN (from v1) - [x] E1 - [x] E2` on one line.

## Root cause
`cli._signoff` passes `--delta` and `--by` straight to `signoff.record`, which wrote them
with their line breaks, and only the flow's sign-off path flattened the text first. Every
reader of the NEEDS-HUMAN section takes the one under the last `## 6. NEEDS-HUMAN` heading,
on the assumption that nothing after it spans lines, so a heading inside a multi-line
reason won.

## Fix
- `signoff.py` adds `_LINE_BREAKS_RE`, a character class matching exactly what
  `str.splitlines` splits on (not only `\n`: also `\r`, `\v`, `\f`, `\x1c`-`\x1e`, `\x85`,
  ` `, ` `).
- `record`'s `set_field` helper replaces each run of those characters with one space before
  writing the field. Because the fix is inside `record`, all three callers are covered (the
  CLI, the flow, `cleanup`), and so is any future caller.
- Values with no line break are recorded byte-for-byte, and backslash handling from #529 is
  unchanged. Tabs and repeated spaces are kept, unlike the flow's `" ".join(x.split())`.
- Docstrings updated: `set_field` now says "literally … except line breaks, which become
  spaces", and `_needs_human_section` now credits `record` (not the flow) with keeping the
  sign-off section single-line.
- Known side effect: a multi-line reason was cut to its first line when carried into the
  next round's brief (`_DELTA_RE` matches one line). It is now carried whole, flattened.

Out of scope: the wider redesign of how the SUMMARY.md format is parsed (#607), and changing
the "last heading wins" rule.

## Verification
- **Claim:** nothing typed into the sign-off reason or name can change which NEEDS-HUMAN
  list the driver reads, so no deferred finding is retired unless the human ticked it in
  the real list.
- **Checked** (on `main` @ `b5f5c29`):
  - `template/src/pdca_harness/cli.py:1473-1474`: `--delta` passed through unchanged.
  - `template/src/pdca_harness/signoff.py:247`, `:267-284`: `record` / `set_field` wrote
    the value as given.
  - `template/src/pdca_harness/signoff.py:103-118`: the last-heading rule and the docstring
    that assumed the sign-off section is single-line.
  - `template/src/pdca_harness/signoff.py:345`, `:359`: headings count only at the start of
    a line from `splitlines`, so the heading text left inline after flattening is harmless.
  - `template/src/pdca_harness/driver.py:135`, `:317-340` →
    `template/src/pdca_harness/autoiterate.py:348`: on iterate, ticks from that section
    retire ledger entries.
  - `template/src/pdca_harness/flow.py:183` and `template/src/pdca_harness/cleanup.py:154`:
    the other two callers of `record`, both now covered by the single fix.
- **Test:** `template/tests/test_signoff_verbatim.py`, new class
  `ForgedSection6InSignoffTextRetiresNothing`. It builds a real bundle with two open
  deferred findings and signs off through `cli._signoff`, so the real retire step runs.
  Nothing is mocked.
  - multi-line `--delta`: pre-fix the ledger empties (`[]`); post-fix it stays `[E1, E2]`.
  - multi-line `--by` ending in a line break: pre-fix `E1` is retired (`[E2]`); post-fix
    both stay.
  - multi-line `--by` from the issue: pre-fix it creates a second `## 6. NEEDS-HUMAN`
    heading; post-fix there is one.
  - every `splitlines` boundary (computed over all code points, plus `\r\n` and mixed runs)
    is flattened in both values, and plain text with tabs, double spaces and `\W` is stored
    byte-for-byte.
  - a positive control (a real tick on `E1` in the real list retires `E1` only) passes
    before and after, which shows the failures above are not a broken fixture.

  Pre-fix (production change reverted, test kept): 15 failures, all in the cases above. The
  positive control and the four existing #529 tests pass. Post-fix: the module passes
  (9 tests), and the full `make check` suite passes (2374 tests, 2 skipped).

Fixes #604
