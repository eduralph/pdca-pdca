## Summary
**User impact:** A check that really passed could be reported as "couldn't be verified",
and a check that really failed could be reported the same way instead of blocking — because
a check was judged by a phrase found *anywhere* in what it printed, even when that phrase
came from something the check merely ran and echoed (a log line, a test's output, a quoted
sentence from these docs). The result is a verification report that misleads in both
directions: real green results stop counting as verified, and real red results are
downgraded to "someone should look at this".

This PR makes the "cannot verify" verdict belong to the check that *declares* it, so text a
check only passed along no longer overrides its real result. Reported in
[#428](https://github.com/eduralph/pdca-harness/issues/428).

## What to look at
The whole behavioural change is in how a gate's captured output is read in
`template/src/pdca_harness/gates.py`: one small new helper that recognises a *declaration*,
plus the few lines in `_classify` that call it. Everything else in the diff is the written
contract (the vocabulary section, the C5a rule, the glossary) saying the same thing, and
new tests.

To try it, configure a gate whose command relays the marker without declaring it and exits
successfully:

```
echo '# ... Emit `PDCA-UNVERIFIABLE: <reason>` and exit 77'; exit 0
```

Before this change the gate row records `unverifiable`; after it, the row records `pass` —
the gate's real verdict. The whole area runs offline in a second:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_gates_unverifiable`.

## Root cause
`_classify` accepted the `PDCA-UNVERIFIABLE:` marker as a bare substring on any output line
(`template/src/pdca_harness/gates.py:614-618` on `main`), so it could not tell a gate's own
declaration from text the gate relayed from a child process. Because an `unverifiable` row
counts toward neither `pass` nor `fail` in `overall`, that mistake silently removed a
genuine green from the verified set and would just as readily launder a genuine red into a
deferral — and it fires structurally in any project whose tests exercise this machinery,
including this one.

## Fix
Recognising a declaration is now its own function, `_declared_unverifiable`: a declaration
is a line whose *first* text is the marker (leading whitespace ignored), and the reason is
what follows it. `_classify` consults it instead of substring-scanning, so an occurrence
mid-line falls through to the gate's real exit-code verdict. Both documented deferral
channels are untouched — exit 77, and an exit-0 line that starts with the marker — and every
marker emitter shipped in the tree already writes it that way
(`template/scripts/checks/test_exercises_production.py:76,85` on `main`). The normative
statements are aligned (`04-validation-tooling.md` vocabulary section and its upgrade note,
`06-quality-cycle-guidelines.md` §C5a, `08-glossary.md`) so gate authors can write to the
rule, including the one behaviour change worth calling out: a gate that *prefixed* its
declaration (`echo "C4: PDCA-UNVERIFIABLE: …"`) now records its real pass/fail and should
move the marker to the front of the line.

## Verification
- **Claim:** A gate that exits 0 and only *relays* the marker inside a line records its real
  verdict (`pass`) and counts toward `overall`.
  **Checked:** `template/src/pdca_harness/gates.py:614-618` on `main` — the substring scan
  that produced the old verdict, reproduced from a one-line shell gate: the exact sentence at
  `template/engine/scripts/run-verify.sh:49` on `main` (a comment quoting the contract) was
  enough to flip a green gate to `unverifiable`.
  **Test:** `template/tests/test_gates_unverifiable.py` —
  `test_a_relayed_marker_does_not_override_a_green_gate` and
  `test_a_relayed_marker_on_the_only_output_line_still_passes` fail pre-fix
  (`AssertionError: 'unverifiable' != 'pass'`), pass post-fix. The second case pins the rule
  to *position in the line*, not "the last line", so a last-line shortcut cannot satisfy it.

- **Claim:** A gate that genuinely declares `unverifiable` itself still records it, on both
  channels, even when relayed noise precedes the declaration.
  **Checked:** the pre-existing declaration cases at
  `template/tests/test_gates_unverifiable.py:74-116` on `main` (marker line with exit 0, exit
  77, and the shipped advisory production-path check) are unmodified and still green.
  **Test:** `test_a_declaration_after_relayed_text_is_still_honoured` — relayed text first,
  then an indented declaration; the row is `unverifiable` with the declared reason.

- **Claim:** The earlier narrowing that ignores the marker on a failing exit
  (c6784ec14ae0836360f01b8d3ad5dc5261ae2792) is not regressed.
  **Checked:** `template/tests/test_gates_unverifiable.py:91-98` on `main` —
  `test_the_marker_does_not_launder_a_non_zero_exit`, unchanged and passing.

- **Whole-module run:** 12 tests green with the patch; with only the production hunks
  reverted (test files kept), 3 failures — the three new cases. Docs lint and the site link
  audit are green over the edited specification pages.

Fixes #428
