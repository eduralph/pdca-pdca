# Brief — issue 529 / signoff-records-human-text-verbatim

- **Slug:** signoff-records-human-text-verbatim
- **Defect:** `signoff.record` writes the human's §9 decision with a nested `set_field`
  (`template/src/pdca_harness/signoff.py:180-185`) that passes the value to `re.subn` as a
  **replacement template**: `repl = rf"\g<1> {value}"`. `re.sub` parses backslash escapes in a
  template, and the values are unsanitised human text: the `Iteration delta` is the sign-off
  rationale (`flow.py:182-185`, flattened from `signoff-decision`), and `By / date` is
  `f"{by} / {date}"` (`signoff.py:203`), with `by` from `--by` / `[project].author`. Three
  failures follow:
  1. A rationale containing `\W`, `\d`, `\u` and so on raises `re.error` ("bad escape"; named
     `re.PatternError` from Python 3.13). Quoting the code under review is the normal shape of
     a rejection rationale. Observed on pdca-pdca `results/issue_506`: the rationale quoted
     `^\W*`.
  2. A rationale containing a **valid** reference such as `\g<1>` doesn't fail. It is
     silently expanded, so §9 records the field's own label in place of the human's words, and the
     next Do gets that via the carry-forward.
  3. `re.error` is not a `ValueError`, so it escapes both callers: `cli._signoff`
     (`cli.py:1400-1407`) tracebacks, and `flow._apply_decision` (`flow.py:183-192`) either
     tracebacks the single-issue run (no `_isolate` there) or, in the batch sweep, falls to
     `flow._isolate` (`flow.py:51-70`) as "skipping this bundle". `signoff-decision` is only
     unlinked after a successful `record`, so every later pass re-reads it and fails the same
     way. issue_506 burned all 20 passes stuck at AWAITING_SIGNOFF with §9 blank.
- **Success criterion:** offline, on the template driver suite, with the recordable SUMMARY
  shape used in `template/tests/test_handoff.py:72-80`:
  (a) `signoff.record(..., action="iterate-do", delta=<text>)` where the text contains a
      regex escape (e.g. ``_ERROR_LEAD_RE's `^\W*` lead``) succeeds, and the §9
      `- Iteration delta (if iterating):` line then ends with exactly that text,
      byte-for-byte;
  (b) a delta containing `\g<1>` is recorded **literally**: the line contains the characters
      `\g<1>` and does not contain a second copy of the field label;
  (c) a `by` value containing a backslash escape (e.g. `CORP\dev`) is recorded literally in
      `- By / date:` for every action, including `accept`;
  (d) end to end: `flow._apply_decision` over a bundle whose `signoff-decision` is
      `iterate-do` plus a rationale containing `^\W*` records §9, consumes (unlinks)
      `signoff-decision`, and returns `"iterate-do"`, so the bundle leaves AWAITING_SIGNOFF;
  (e) the existing sign-off suites (`test_signoff_authority.py`, `test_signoff_orphan.py`,
      `test_handoff.py`) pass unchanged: the Outcome/By/delta match-count guards
      (`signoff.py:188-215`) still raise `ValueError` on a §9 missing a field.
- **Falsifiability:** RED on the offline driver suite, Python ≥ 3.11 (CI runs 3.12). Pre-fix,
  (a), (c) and (d) raise `re.error` from `signoff.py:184` and (b) records the label twice, so
  each is a real test failure/error on existing API (`signoff.record`, `flow._apply_decision`),
  not an import failure. The test must not name `re.PatternError` (absent before 3.13): assert
  on the recorded text, not on an exception type.
- **Invariant to restore:** text a human supplies to the sign-off record is data, never
  interpreted. Whatever characters it contains, §9 carries it verbatim, and recording can
  only fail for the reasons `record` documents (`ValueError`, `signoff.py:165-169`). Source:
  Python `re.sub` documentation (a string `repl` has its backslash escapes processed; a
  callable `repl`'s return value is used as-is), and `record`'s own contract "records or
  raises `ValueError`" (`signoff.py:165-169`), which both callers rely on.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** none
- **Ordering note:** run 3 of plan-0.60-bug-order.md, one wave with 534, 467, 480 and 527.
  Only this bundle edits `signoff.py`. The test touches `flow._apply_decision` only by calling
  it, and nothing in this run edits `flow.py`.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** `signoff.record` writes each §9 field value verbatim, so no character in human
  text is read as regex template syntax. One site (`set_field`, `signoff.py:180-185`).
  / out of scope: `flow._isolate`'s "skipping this bundle" wording and a quarantine path for
  a decision that can never be recorded (the issue flags these as a separate consideration);
  multi-line values in §9 (flow already flattens the rationale, `flow.py:181-182`); the
  instance-side local patch in pdca-pdca (dropped at the next `copier update`); any other
  `re.sub` call in the package. Note in build-notes if Do sees the same pattern elsewhere,
  but don't fix it here.
- **Repro instruction:** on `main`, in `template/`: write the `_SUMMARY` text from
  `test_handoff.py:72-80` to a temp `SUMMARY.md`, then
  `PYTHONPATH=src python3 -c "from pathlib import Path; from pdca_harness import signoff; signoff.record(Path('SUMMARY.md'), action='iterate-do', by='T', date='2026-09-15', delta=r'the ^\W* lead')"`:
  it raises `re.error: bad escape \W`. With `delta=r'\g<1> literal'` it succeeds and §9 reads
  `- Iteration delta (if iterating): - Iteration delta (if iterating): literal`.
- **External dependencies:** none — offline; base toolchain only (python3 ≥ 3.11)
- **Test file:** template/tests/test_signoff_verbatim.py (new)
- **Citations expected:** Do cites path:line on `main` for every change. Peer callsites: the
  recordable SUMMARY fixture is `_SUMMARY` in `test_handoff.py:72-80`; the end-to-end shape of
  (d) mirrors `test_flow_captures_the_full_rationale_before_the_unlink`
  (`test_handoff.py:411-424`), which drives `flow._apply_decision` with a `signoff-decision`
  file and asserts the unlink.
- **Prior-art check (triage cycles):** by path on origin/main (fetched 2026-09-15):
  `git log -- template/src/pdca_harness/signoff.py` shows `15e7831`, `2407965`, `c6784ec`,
  `f1ee70b`, `e6ba305`, `6c4774c`; `git log -S` (re-run here) puts the template-string `repl` in
  the initial commit `3ca179a`, unchanged since. No open PR touches `signoff.py` (open: #542,
  #543). No closed/merged PR references #529 (the #470 search hit was a line number).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
