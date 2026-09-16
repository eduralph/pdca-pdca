## Summary
**User impact:** if your sign-off reason or your `--by` name contains a backslash, the
decision cannot be recorded. Quoting a pattern such as `^\W*` in a rejection reason makes
`pdca signoff` crash with a traceback, and `pdca flow` skips the bundle on every pass, so it
stays stuck waiting for sign-off with an empty decision (one real bundle used up all 20
passes this way). A reason that happens to contain `\g<1>` is worse: it is saved without any
error, but with the wrong words, and those wrong words are what the next build is told.

This PR makes sign-off save the text exactly as you typed it, whatever characters it contains.

Reported in [#529](https://github.com/eduralph/pdca-harness/issues/529).

## What to look at
The change is two lines in the helper that writes each sign-off field into `SUMMARY.md`,
plus a new test file.

To see the bug on `main`, from `template/`: put the recordable SUMMARY text from
`tests/test_handoff.py` (the `_SUMMARY` fixture) into a temp `SUMMARY.md`, then run

```
PYTHONPATH=src python3 -c "from pathlib import Path; from pdca_harness import signoff; signoff.record(Path('SUMMARY.md'), action='iterate-do', by='T', date='2026-09-15', delta=r'the ^\W* lead')"
```

It fails with `re.error: bad escape \W`. With `delta=r'\g<1> literal'` it succeeds, but the
line reads `- Iteration delta (if iterating): - Iteration delta (if iterating): literal`.
With this branch, both are saved as typed.

## Root cause
`record`'s inner `set_field` built the replacement for `re.subn` as the string
`rf"\g<1> {value}"`, and Python treats a string replacement as a template with its own
backslash escapes, so the human's text was parsed instead of copied. An unknown escape
raises `re.error`, which is not a `ValueError`, so it got past both callers' error
handling. A valid reference like `\g<1>` was quietly expanded.

## Fix
The replacement is now a small function that returns the captured label plus `value`.
`re.sub` uses a function's return value as-is, with no escape processing, so every character
of the human's text reaches the file unchanged. Field matching, the match-count checks, and
the refuse-before-writing behaviour are unchanged. The docstring explains why the
replacement has to be a function, so it doesn't get turned back into a string later.

I also checked the other `re.sub`/`re.subn` calls in the package: none of them builds its
replacement from user-supplied text, so this was the only affected spot.

## Verification
- **Claim:** a rationale containing a regex escape (`^\W*`) is recorded, and the line
  ends with exactly that text.
  - **Checked:** `template/src/pdca_harness/signoff.py:180-185` on `main`: the string
    template at line 183 is where the escape was parsed. The helper feeds both
    `By / date` (line 203) and `Iteration delta` (line 209).
  - **Test:** `RationaleWithARegexEscapeIsRecordedVerbatim` in
    `template/tests/test_signoff_verbatim.py`: errors before the fix, passes after.
- **Claim:** text that spells a valid group reference (`\g<1>`) is kept as typed, not
  expanded into a second copy of the label.
  - **Test:** `RationaleWithAValidGroupReferenceIsNotExpanded`: fails before the fix
    (label recorded twice), passes after.
- **Claim:** a `--by` value with a backslash (`CORP\dev`) is recorded as typed for every
  outcome, including `accept`.
  - **Checked:** `signoff.py:203` builds `f"{by} / {date}"` and passes it through the same
    helper.
  - **Test:** `ByWithABackslashEscapeIsRecordedVerbatim`, looping over all four actions:
    errors on each before the fix, passes after.
- **Claim:** through the real flow, a decision whose reason quotes `^\W*` is recorded, the
  decision file is used up, and the bundle moves on.
  - **Checked:** `template/src/pdca_harness/flow.py:183-192`: `_apply_decision` catches only
    `ValueError` around `signoff.record`, and the decision file is deleted only after a
    successful record, which is why the old error left the bundle stuck.
    `template/src/pdca_harness/cli.py:1400-1407` has the same `except ValueError` for
    `pdca signoff`.
  - **Test:** `EndToEndThroughApplyDecision` calls `flow._apply_decision` with a
    `signoff-decision` file. It checks that the call returns `"iterate-do"`, that the file is
    deleted, and that the reason is saved as typed. Errors before the fix, passes after.
- **Claim:** the existing sign-off behaviour is unchanged, including the refusal when a
  field is missing.
  - **Test:** `test_signoff_authority.py`, `test_signoff_orphan.py` and `test_handoff.py`
    pass unmodified. Full driver suite, `cd template && PYTHONPATH=src python3 -m unittest
    discover -s tests`: 1792 tests OK (2 skipped).

The new test checks the saved text, not the exception type, so it gives the same result
on Python 3.11 and 3.12 (`re.PatternError` only exists from 3.13).

Fixes #529
