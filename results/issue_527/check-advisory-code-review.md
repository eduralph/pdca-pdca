# Check advisory — code review (correctness / reuse lens), issue #527

Traced the new loop in `_needs_human` (`template/src/pdca_harness/assemble.py:489-522`)
line by line against the test cases and the gate evidence. No correctness bug found and
no reuse/simplification opportunity worth flagging.

- Loop control is sound: the bullet branch sets `i = j; continue`, so the bottom-of-loop
  `i += 1` never double-advances, and the table branch (now wrapped in
  `if vi is not None:` instead of an early `continue`) still falls through to that same
  `i += 1` — equivalent to the pre-patch control flow (`assemble.py:513-522`).
- `verdict_table` (line indices of the mandated 5/5/1 table) is computed once from the
  original `lines` before the loop and never re-derived, so skipping ahead over a
  bullet's continuation lines can't shift which index the STANDING check
  (`i in verdict_table`, `:520`) tests — table rows and NEEDS-HUMAN bullets are
  mutually exclusive branches, and `_ends_needs_human_continuation` breaks continuation
  scanning the moment it hits a `|` line, so a bullet can never swallow a table row.
- The "one line, never a newline" invariant the brief calls load-bearing for
  `signoff.open_needs_human` (`signoff.py:102-120`, which matches `- [ ] ` per physical
  line) holds end to end: continuation text is `" ".join`-ed (`:510`), never
  `"\n".join`-ed, and the only place §6 items get rendered back to text
  (`assemble.py:603`, `f"- [ ] {it}"`) does no further splitting.
- Dedup (`add()`, `:483-487`) now keys on the full joined text rather than just the
  first line — strictly finer-grained than before, so it can't newly collide two
  distinct multi-line bullets that happened to share a first line; it's a side benefit,
  not a regression.
- Checked the existing bullets in `test_autoiterate.py`, `test_plan_advisory.py`,
  `test_leaf_status.py`, `test_external_dependency_section6.py` that this patch must
  leave byte-identical: all are genuinely single physical lines (the ones assembled from
  multiple Python string literals join into one line with no embedded `\n` before the
  final one), so none exercises the new continuation path — consistent with the T3 gate
  log (1798 tests, OK) and with the C4 gate log showing the new suite's red leg fails
  9/10 and green leg passes 10/10, i.e. a real causal test, not a vacuous one.
- Reuse: the brief's peer callsite `brief._block_for` (`brief.py:70-104`) does something
  visibly similar (indentation-based continuation membership), but its semantics differ
  in two ways that matter here — it *preserves* a block's relative indentation instead of
  flattening to one line, and it treats a blank line as *inside* the block rather than
  ending it. The new code doesn't call it, and the docstring at `assemble.py:459-464`
  and the brief's Scope section both call this out explicitly, so this isn't
  unacknowledged duplication — it's a considered decision not to reuse a helper whose
  contract doesn't fit.

No findings requiring a human or a builder iteration.
