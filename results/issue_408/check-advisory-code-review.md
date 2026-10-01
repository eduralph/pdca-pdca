# Check advisory — code review (issue #408)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. I found no
correctness bug in the new classifier, normaliser or prompts. The four brief clauses are
each covered by a test. C4 shows a real red leg (84 failures pre-fix) and T3 runs the full
suite green (2215 tests). Findings, most important first:

- NEEDS-HUMAN — template/src/pdca_harness/assemble.py:339 (with :874) — `verdict_other`
  goes beyond the brief. A verdict-table row whose Verdict cell is PASS / FAIL / N/A while
  another cell mentions NEEDS-HUMAN is now HUMAN on **every** element, gate cells included.
  For example, `| C4 … | FAIL | … NEEDS-HUMAN … |` used to be IMPL through the gate-element
  rule and auto-iterated. Now it halts for the human. None of the four success-criterion
  clauses names this change, and the brief's scope covers only C5/T5 tag honouring and V-row
  normalisation. The code comments cite a "#408 sign-off", and the change is tested
  (`test_a_gate_row_contradicting_its_verdict_does_not_auto_iterate`), so this looks
  deliberate. The human should confirm the gate-cell behaviour change is wanted in this
  slice and not in #409 or a follow-up. It reduces auto-iteration on gate rows.
- template/src/pdca_harness/size_signal.py:313-318, :330 — the docstring is now stale (a
  file this patch did not edit). It says the `[impl]` read uses "the pattern
  `assemble._classify_finding` strips". `_classify_finding` now strips `_TAG_MARKER_RE`
  (assemble.py:80), not `_IMPL_MARKER_RE` (assemble.py:77). The check at :330 also no longer
  matches what §6 does: a primary-review bullet `[impl] — C1 …` is HUMAN in §6 after this
  patch, but size_signal still reads it as "the reviewer saying a rebuild can fix it". The
  verdict-cell `NEEDS-HUMAN [impl]` form is invisible to :330. That form still counts the
  round, because the C5/T5 item is non-STANDING and so the returned list is non-empty. Both
  gaps only make the code count a round, never skip one, so behaviour is safe. Only the
  comment is wrong. A one-line docstring fix, or a note in the PR, would do. The brief puts
  `size_signal.py` out of scope, so this is not tagged for rebuild.
- template/src/pdca_harness/assemble.py:77 vs :80 — `_IMPL_MARKER_RE` is now used only by
  size_signal.py:330. `_TAG_MARKER_RE` covers it (`m.group(1) == "impl"`). Keeping both is
  fine, but a comment on :77 saying it stays only for size_signal would stop a later reader
  from treating the two as duplicates or editing just one.
- template/src/pdca_harness/assemble.py:855 / :932 — `_table_header` walks back to the top
  of the table for every NEEDS-HUMAN row, so the cost grows with the square of the table's
  row count. With about 11 rows this costs nothing. If you want it simpler, find the header
  once per block in `_verdict_table_lines` (which already finds the block bounds). That is
  optional, not a defect.
- Tests (template/tests/test_autoiterate.py, new `ReviewerImplTag` / `ValidationRowForms` /
  `TagContractPrompts`) — no weak test found. They go through production entry points
  (`_items_from_artifact`, `collect_needs_human`, `_try`), reach new symbols through the
  module (`assemble._PROMOTABLE_ELEMENTS`) as the brief requires, and include the negative
  cases (mismatched `C5 —` / `T5 —` prefix, free text after the label, Basis-cell `[impl]`,
  plan-advisory `[impl]`). The C5-prod-path gate passed with "patch adds no new test file —
  nothing to assert". That is expected, because the tests were appended to an existing
  module. It means that gate checked nothing here; it is not a fault in the patch.
