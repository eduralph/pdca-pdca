# Check — advisory code review (issue #528)

Scope: `template/process/act-log.md.jinja`, `template/src/pdca_harness/handoff.py`,
`template/tests/test_handoff.py` (this diff only).

## Correctness

No bugs found in the patch.

- `_is_pure_insertion` (`handoff.py:183-207`) — checked the math directly: bounding
  `lcs` to `remaining = len(baseline) - lcp` means `lcp + lcs` can never exceed
  `len(baseline)`, so hitting `lcp + lcs == len(baseline)` is not a heuristic — it
  proves `baseline[:lcp]` and `baseline[lcp:]` tile the whole of `baseline` with no
  gap or overlap, which means `text` really is `baseline` with one contiguous block
  spliced in at position `lcp`. Ran it against prepend / mid-splice / append /
  no-common-content / an edit-plus-append case by hand (`_is_pure_insertion("ab",
  "aXbY")` correctly returns `False` — two separate insertion points, not one
  contiguous block) — all matched the documented contract.
- `prev_text = baseline.get("act_log_text")` is checked with `is None`
  (`handoff.py:235`), not truthiness, so a session that starts from an empty
  act-log (`act_log_text == ""`) still takes the new full-text branch instead of
  silently falling back to the legacy len/sha path. Easy off-by-one to get wrong
  here; it wasn't.
- Branch order in `check_act` (`handoff.py:248-262`: unchanged → pure-append →
  pure-insertion-elsewhere → edited/removed) matches the four cases in the brief,
  and the case-(d) test (`test_handoff.py:365-378`, edit an existing entry's text
  *and* append a correct new one at the end) lands on the "append-only" message,
  not the "appended at the end" message, confirming the branches don't collide.
  C4's red leg (`gate-logs/C4-verify.log`) shows this test and the two
  insertion-shape tests genuinely failing pre-fix and passing post-fix — the new
  tests exercise the change, not a tautology.
- Backward compatibility: the legacy len/sha-only baseline path
  (`handoff.py:235-247`) is kept and still exercised by the pre-existing
  `ActContract` tests (`test_handoff.py:283-296` etc., built with hand-rolled
  `{"act_log_len", "act_log_sha"}` dicts, no `act_log_text` key) — C4's green leg
  reports all 41 tests passing, so the brief's "existing tests stay green without
  edits" criterion holds.
- Full suite (`gate-logs/T3-suite.log`): 1900 tests, OK. Docs/host-CI gates clean.

## Reuse / simplification / efficiency

Nothing to flag. `_is_pure_insertion` is new logic with no existing helper in the
codebase it duplicates (checked for `difflib`/`SequenceMatcher` use elsewhere — none).
The hand-rolled prefix/suffix scan is also the cheaper choice here versus
`difflib.SequenceMatcher` (linear vs. worst-case quadratic) for a file that can grow
to four-figure line counts per the brief's own account of a real instance's log — a
reasonable, not premature, efficiency choice for this hot(ish) content size, even
though `check_act` itself runs once per `/handoff`, not in a loop.

The one thing worth naming without treating it as a defect: `session()`
(`handoff.py:433-434`) now writes the *entire* act-log text into the session's JSON
scratch file on disk at session start (previously just length + a sha). This is
the smallest baseline that can satisfy the fix's correctness requirement — checking
"was old text preserved intact" cannot be done from a hash alone — and the file is
transient (state-prefixed, `unlink`ed on reap), so the cost is one extra text-sized
disk write per interactive Act session, not a hot path. Not flagging as a finding.

## Verdict

Diff is clean on both lenses. No NEEDS-HUMAN items from this leaf.
