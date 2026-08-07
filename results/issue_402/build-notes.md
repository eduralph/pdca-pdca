# Build notes — issue 402 / gate-evidence-not-leaked-stdout

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) at `0a43cc8` (`pdca-integrate: issue_428`) —
the brief's declared base (`Depends on: 428`, `stack-base` = `pdca-integration/main`).
All `path:line` citations below are against that tree **with the patch applied**.

## What the patch does — the two halves

### Half (2), the load-bearing one: evidence is what the gate DECLARED

- `template/src/pdca_harness/gates.py:77` — new `EVIDENCE_MARKER = "PDCA-EVIDENCE:"`.
- `gates.py:615` — `_declarations(output, marker)`: the #428 declaration test (first text on
  a line, leading whitespace ignored), factored out so **one** notion of "the gate said this"
  serves both markers. This is the brief's constraint "do not invent a second, different
  notion" taken literally: `_declared_unverifiable` (`gates.py:635`) is now a thin caller of
  it and its behaviour is byte-identical (first declaration wins).
- `gates.py:644` — `_declared_evidence`: the **last** non-empty declaration. Last, not first,
  because a wrapper with several legs declares per leg and its final word summarises the run;
  the unverifiable marker keeps *first* because a deferral reason cannot be retracted by later
  output. Both are documented in place.
- `gates.py:702-707` — `_classify` now takes the declared summary as the evidence, and only
  falls back to `output.strip().splitlines()[-1:]` when the gate declared nothing. The
  fallback is deliberately kept (Success criterion 2's second sentence: "a gate that declares
  nothing keeps a defined, documented evidence rule").
- **The marker never changes a verdict.** `result` still comes from the exit code alone;
  `PDCA-UNVERIFIABLE` remains the one marker that can move a `result`, under #329/#428's
  rules. That is what keeps the #329 hazard (a marker laundering a red into a
  non-gating outcome) from reappearing through a second marker — pinned by
  `test_a_declaring_gate_that_exits_non_zero_still_fails` (`test_gate_logs.py:275`) and
  `test_unverifiable_declaration_still_wins_the_result` (`:298`).
- `template/PCDA/quality-cycle/04-validation-tooling.md:83` — the convention stated where the
  gate contract is written (§Gate result vocabulary), so a wrapper can be written against it,
  including the "purely additive, nothing else changes" note for existing instances.

### Half (1): `test_split.py` stops leaking the driven code's stdout

Mirrors the peer callsite the brief cites, `template/tests/test_split.py:865`
(`redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO())`) — the file's own
convention — onto the paths that had not applied it: `:181`, `:217`, `:224`, `:316`,
`:594-597`. Those drive `leaves.do_split` (`leaves.py:1157`, `print(f"{d / split.PROPOSAL}")`)
and `cli._split` (`cli.py:786-787`, `print(child)`), which produced the five leaked
`/tmp/…/results/issue_50{0}|60{1,2}` lines. No fixture-level capture was invented.

## Why this shape, and what was ruled out

- **Rejected: strip `/tmp`-looking lines / heuristically skip "noise" when picking the last
  line.** It cannot be right in general (a real gate verdict may legitimately name a path)
  and it is the "guard the symptom" move: it leaves the cause — nobody ever said which line
  was the verdict — in place. The declaration rule removes the cause for any gate that adopts
  it, in ~20 lines.
- **Rejected: record the last *N* lines / the whole output as `path_line`.** `path_line` is a
  120-char summary consumed as one line by `assemble.py:356,365,386`, `driver.py:391`,
  `publish.py:849` and the rendered matrix (`gates.py:811`, a Markdown table cell where a
  newline breaks the row). Making it multi-line is a **5-callsite** change plus a table-format
  change, versus 6 changed lines in `_classify` — and it would not fix the defect anyway: the
  leaked `/tmp` line would still be in the recorded summary, just with company. The full basis
  is already reachable, by design, through `row["log"]` (`gates.py:553-563`, #370/#415).
- **Rejected: separate the streams (capture stdout and stderr apart, take the last *stderr*
  line).** That is not the invariant — a gate is free to declare on stdout — and it is a real
  change to `progress.run_with_heartbeat` (`progress.py:111-112`, `stdout, stderr = subprocess.PIPE, subprocess.STDOUT`) whose merged
  capture is what `gate-logs/` persists verbatim (`_write_gate_log`, `gates.py:604`); the
  interleaved log is a feature (#370). Two captures also reintroduce ordering ambiguity in the
  log, i.e. a new defect of the same family.
- **Rejected: fix only half (1).** Measured at Plan and re-measured here: the whole offline
  suite leaks ~500 stdout lines from other modules, so half (1) alone just changes *which*
  line gets misfiled; and a test-only patch is `PDCA-UNVERIFIABLE` under this project's C4
  (`engine/scripts/run-verify.sh:51-53`), so it could not earn a red→green at all.
- **Not done deliberately (scope):** the suite-wide stdout-hygiene sweep (the other ~500
  lines — the brief says do NOT start it here); the pdca-pdca-side follow-up that should
  replace its `run-suite.sh` stopgap (Act 2026-08-02, `a100098`) with a `PDCA-EVIDENCE:`
  declaration — a change to **this instance**, not to the target; and adding the marker to the
  target's shipped skeleton wrappers (`template/engine/scripts/run-verify.sh` is an
  unimplemented skeleton; the contract doc is where the brief asked for the statement).

## Refuting my own test (forced, recorded)

- **(a) Genuine red?** Yes, both halves, each reverted independently and re-run:
  - production hunk reverted (`git stash push -- template/src/pdca_harness/gates.py`),
    `cd template && PYTHONPATH=src python3 -m unittest tests.test_gate_logs` →
    `Ran 15 tests … FAILED (errors=6)` (the 6 new cases; `AttributeError: module
    'pdca_harness.gates' has no attribute 'EVIDENCE_MARKER'` on the ones that name the
    marker, and the declared-summary case would file the trailing `/tmp` line).
  - the `test_split.py` capture hunk reverted, `python3 -m unittest
    tests.test_suite_output_hygiene` → `FAILED (failures=1)`, printing the five leaked
    `/tmp/tmp…/results/issue_500/split-proposal.md` / `issue_60{1,2}` lines verbatim.
  - End-to-end through the project's own C4 runner (`PDCA_BUNDLE=… PDCA_WORKTREE=…
    ./engine/scripts/run-verify.sh`, which reverts the *production* hunks and keeps the
    tests): `C4 PASS: red without the fix, green with it`.
- **(b) Production path?** Yes. `test_gate_logs.GateEvidenceIsTheGatesOwnVerdict` calls
  `gates.run_gates(bundle, cfg)` — the real entry point — with real shell gate commands, so
  the assertions run through `_run_one` → `progress.run_with_heartbeat` → `_classify` → `_row`
  → `check-gates.json`, exactly the path a live Check uses. No mock of the classifier, no
  re-implementation; it reads `gates.EVIDENCE_MARKER` from production rather than a literal.
  `test_suite_output_hygiene` runs the real `tests.test_split` module in a subprocess
  (`cwd=template`, `PYTHONPATH=src`) and inspects its real stdout — the production printers
  in `leaves.py`/`cli.py` are the things being silenced.
- **(c) Fixture includes the fault?** Yes. The gate command in the binding test *is* the
  failing shape, not a sanitised one: `echo 'PDCA-EVIDENCE: C4 PASS: red without the fix,
  green with it'; echo /tmp/tmpy_ulekwf/results/issue_500/split-proposal.md` — the shipped
  string from `results/issue_387`'s T3 row, with the leaked path still last in the capture and
  still present in the persisted `gate-logs/` body (asserted, `test_gate_logs.py:265`). The
  hygiene test runs the whole `test_split` module, including the tests that leaked; it does
  not select the quiet ones. Both would be trivially green if I had curated the fault out —
  and (a) shows they are not.

## Runs (all through the project's own runners, never hand-rolled)

- `./engine/scripts/run-verify.sh` (C4, gating) → `C4 PASS: red without the fix, green with it`.
- `./engine/scripts/run-suite.sh` (T3) → `== T3: root suite OK, driver suite OK`
  (root render/update-compat suite + the 1509-test offline driver suite).
- `./engine/scripts/run-docs-check.sh` (T2) → `lint_docs: OK`, `render_site: link audit OK`.
- Commit-readiness: the target repo defines no formatter / pre-commit hook (`git config
  core.hooksPath` empty, no `.pre-commit-config.yaml`, no lint config; CI is render-check +
  docs-check, both run above). Longest added Python line is 96 chars, inside the file's
  existing envelope (`gates.py` already carries 96–106-char lines).

No external dependency beyond the brief's `none` was needed.
