## Summary

**User impact:** A check that passed could be recorded with a temporary file path from a
sandbox that no longer exists as its one line of stated evidence — instead of the "PASS"
summary the check itself printed. The saved record of a green run therefore read like a
failure trail: anyone reviewing it later could not tell why the check passed, and kept
stopping to investigate a check that had never failed (this happened on the majority of
recent runs here).

This PR lets a check state which line is its verdict — print `PDCA-EVIDENCE: <summary>` and
that summary is what gets recorded, whatever the command prints afterwards — and stops the
offline test suite from leaking the output of the code it drives, which was the noise being
recorded in the first place.

Reported in [#402](https://github.com/eduralph/pdca-harness/issues/402).

## What to look at

Two small, separable pieces:

- **The evidence rule** — `_classify` in `template/src/pdca_harness/gates.py` now takes the
  declared summary, and only falls back to "the command's last output line" when nothing was
  declared. The convention is written up for gate authors in
  `template/PCDA/quality-cycle/04-validation-tooling.md` (§Gate result vocabulary) — that
  section is the contract, and the piece most worth a second opinion.
- **The leak** — a handful of call sites in `template/tests/test_split.py` now apply the
  capture convention the rest of that file already uses.

Try it in ~30 seconds. Before this change, from a clean checkout:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_split 2>&1 | tail -3
```

prints `/tmp/…/results/issue_500/split-proposal.md` lines *after* the `OK` report — that is
exactly what a check running a suite would file as its result. With this change, that command
ends with the unittest report and nothing else. And a gate command such as

```
echo 'PDCA-EVIDENCE: C4 PASS: red without the fix, green with it'; echo /tmp/scratch/path
```

now records the `C4 PASS: …` line rather than the trailing path.

## Root cause

The evidence line came from `output.strip().splitlines()[-1:]` — the last line of the
command's capture — and that capture is one merged stdout+stderr stream
(`progress.run_with_heartbeat`, `stdout=PIPE, stderr=STDOUT`), so a wrapper that shells out
to a test suite files whatever that suite's *children* flushed last, never having said which
line was its own verdict. `unittest` writes its report to stderr while the driven code's
block-buffered stdout flushes last, so the leaked scratch paths from `tests/test_split.py`
landed after `OK` and became the recorded basis of a passing gate.

## Fix

- `template/src/pdca_harness/gates.py:77` adds `EVIDENCE_MARKER = "PDCA-EVIDENCE:"`;
  `gates.py:615` factors the existing declaration test (first text on a line, leading
  whitespace ignored — the form settled in #428) into `_declarations`, so both markers share
  one notion of "the gate said this"; `_declared_evidence` (`gates.py:644-652`) takes the
  **last** non-empty declaration, because a multi-leg wrapper's final word summarises the run
  (the unverifiable marker keeps *first*: a deferral reason cannot be retracted).
- `_classify` (`gates.py:702-707`) records that summary and falls back to the last output
  line only when nothing was declared. The marker never moves a verdict — the exit code alone
  decides pass/fail, and `PDCA-UNVERIFIABLE` stays the only marker that can change a
  `result`, so it cannot launder a red into a non-gating outcome.
- `template/PCDA/quality-cycle/04-validation-tooling.md:83` documents the convention where
  the gate contract lives, including the "purely additive" note: a gate that never prints the
  marker behaves exactly as before, and the full capture stays in `gate-logs/<rule_id>.log`.
- `template/tests/test_split.py:181,217,224,316,594` wrap the calls that drive
  `leaves.do_split` and `cli._split` in the `redirect_stdout(io.StringIO())` convention the
  file already uses at `:865`, `:897`, `:948`.

## Verification

- **Claim:** a gate that declares its summary has *that* summary recorded, even when the
  command relays further output afterwards.
  **Checked:** `template/src/pdca_harness/gates.py:644-652,702-707`.
  **Test:** `template/tests/test_gate_logs.py:256-265` — runs a real gate command through
  `run_gates` (no mocked classifier), using the shipped failing shape (`PDCA-EVIDENCE: C4
  PASS: …` followed by the `/tmp/…/issue_500/split-proposal.md` path); fails pre-fix, passes
  post-fix. `:267-273` pins that the last declaration wins.
- **Claim:** the evidence marker never changes a verdict.
  **Checked:** `template/src/pdca_harness/gates.py:698-707` — `result` still derives from the
  exit code; the unverifiable branch is untouched.
  **Test:** `template/tests/test_gate_logs.py:275-282` (declaring gate exiting non-zero still
  fails and still gates) and `:298-305` (`PDCA-UNVERIFIABLE` still wins the result).
- **Claim:** an undeclared gate keeps the documented last-line rule, and the full basis stays
  reachable.
  **Checked:** `template/src/pdca_harness/gates.py:703-704` (fallback) and `:553-563` (the
  full-output log recorded in `row["log"]`).
  **Test:** `template/tests/test_gate_logs.py:284-296` — a mid-line mention of the marker is
  relayed text, not a declaration, and a bare marker with no summary falls back too;
  `:105-107` shows the pre-existing last-line expectation is unchanged for undeclared gates.
- **Claim:** `tests.test_split` writes nothing to stdout — its whole output is the unittest
  report on stderr.
  **Checked:** `template/tests/test_split.py:181,217,224,316,594` on this branch.
  **Test:** `template/tests/test_suite_output_hygiene.py:37-51` — runs that module in a
  subprocess (`cwd=template`, `PYTHONPATH=src`) and asserts empty stdout; pre-fix it fails,
  printing the five leaked `/tmp/…/issue_50{0}|60{1,2}` paths verbatim. It is a separate
  module on purpose: a suite that shelled out to itself would recurse.
- **Suites:** the offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest
  discover -s tests`) and the render / `copier update` compatibility suites are green; the
  docs lint and site link audit pass.

Fixes #402
