# Advisory review — adversary (issue #541, iteration 5)

Lens: refute the red→green evidence and the reviewer's verdict; find the input that breaks the
fix. Scope: the three carry-forward items from the v4 sign-off, plus the delta as a whole.

**Bottom line:** I could not refute any of the three carry-forward fixes. One wording finding
remains in the same class as carry-forward item 3 (an overstated claim), this time in the prompt
text the leaf reads. One exotic edge is noted below the bar.

## Evidence I re-ran myself

- Re-ran `PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest` at `$PDCA_TARGET/template`:
  24/24 OK. `tests.test_leaf_status` is unmodified by the patch and passes 15/15, so 4d holds.
  The full offline suite (`discover -s tests`) passes: 1990 tests OK, 2 skipped. This matches
  `gate-logs/C4-verify.log` (green 24 OK; red FAILED, failures=13, errors=5) and
  `gate-logs/T3-suite.log`.
- **Mutation, carry-forward item 1 (prompt order).** In a copy of the target, I moved
  `_COMPLETION_INSTRUCTION` back in front of the rubric at the review site
  (`template/src/pdca_harness/leaves.py:3170-3171`). The extended 4e leg went red with
  `review: the prompt does not END with the closing instruction — its last line is
  '- RUBRIC-RULE-5e1: no bare unwrap()'`. I did the same at the advisory site
  (`leaves.py:3423-3424`) and it went red on `prompt='advisory'`. So the new assertions at
  `template/tests/test_attempt_harvest.py:733-742` catch the v4 bug, and they check the prompt
  actually fed on stdin, not a copy of the constant.
- Caveat for whoever cites C4 as proof of item 1: in the C4 red leg the 4e test dies with an
  `AttributeError` on `assemble.LEAF_COMPLETE_TRAILER` (`test_attempt_harvest.py:718`) before it
  reaches the prompt-order assertions. C4 therefore does **not** show that those assertions would
  catch the v4 ordering. The mutation runs above do. This is not a defect, just a limit on what
  the C4 row proves.
- I tried to find text added to the prompt after it is composed. `_invoke` only *prepends* the
  role-injection prefix (`leaves.py:618`, `:630`) and nothing is appended, so the instruction
  stays last for every family, not only the claude-family stub the test drives.
- I tried to make a harness placeholder end with the trailer, which would break #278. Every
  placeholder's last line is fixed prose that ends after the interpolated `reason`
  (`leaves.py:3236-3237`, `:3585-3586`, `:4072-4073`). Even a multi-line `reason` cannot make
  the last line equal the trailer. Could not refute.
- Carry-forward items 2 and 3 (wording): the half-deleted "neither…" sentence is gone
  (`leaves.py:3258-3263` now says plainly that "leaf did not run" would be false and the default
  `human-empty` applies). "cannot have closed itself" is softened in `assemble.py:162-165` and in
  the test module docstring. Grepping the patch finds no remaining "cannot have closed",
  `unowned-empty` or `LEAF_STATUS_UNOWNED`. Could not refute.
- Not a refutation, recorded so nobody re-raises it: the brief says the status set is exactly
  three tokens, but `test_the_recognised_status_set_does_not_grow` pins four, including
  `sandbox-empty`. The base already has `LEAF_STATUS_SANDBOX` (#526; unchanged context at
  `assemble.py:119`). The builder read the base correctly and the brief's count was out of date.

## Findings

- NEEDS-HUMAN — **The trailer instruction tells every reviewer leaf two things this patch makes
  false** (`template/src/pdca_harness/leaves.py:2538-2540`): "it is how the harness tells your
  finished report from a half-written one left behind by an attempt that died, and an artifact
  it cannot tell apart is not read as your verdict." (a) Dead attempts' leftovers are separated
  by `_LeafHarvest.withdraw` (`leaves.py:907`), whether or not they carry a trailer. The trailer
  only changes how a *quoted* status marker is read. (b) By criterion 4b, an artifact *without*
  the trailer **is** read as the verdict. The patch's own leg shows this:
  `test_the_live_attempts_own_artifact_is_harvested_at_every_site`
  (`test_attempt_harvest.py:350`) files `_LIVE_TEXT` (`:116`), which has no trailer, as the live
  verdict, and `leaf_status` returns `""` for it. The block comment above has the same problem
  (`leaves.py:2524-2526`: "a question no amount of reading the report's TEXT can answer", when
  the trailer is itself read from the text). This is the same class as carry-forward item 3,
  except that here it is in model-facing text, not a docstring. A leaf that believes a report
  without the trailer "is not read as your verdict" could leave the trailer off a partial report
  on purpose to hold it back, and the harness would file it anyway. It is wording only, with no
  code change. Not tagged `[impl]` because the sign-off limited this round to exactly three
  fixes. The human decides whether to fold it in now or defer it. Suggested wording: "…it tells
  the harness this file is your finished report; nothing may follow it."
- (Below the bar for a round on its own; recorded, not escalated.) `_note_bash_unavailable`
  re-implements the "is the last non-blank line the trailer?" test with
  `text.rstrip().rpartition("\n")` (`leaves.py:4043-4044`). `assemble.leaf_status` uses
  `splitlines()` (`assemble.py:169`). The two split lines differently. Measured: a closed plan
  review whose trailer follows a U+2028 line separator classifies `""` before the Bash note is
  added and `infra-empty` after, so the note un-closes it. LF, CRLF and bare CR all behave
  correctly, because `read_text` normalises CR. The input is exotic. A shared "last non-blank
  line" helper would remove this second copy of the trailer test, which scope item 2 warns
  against in spirit.

Attempted to refute: the prompt-order fix at both sites, the stale-docstring and overstated-claim
fixes, #278 placeholder safety, the non-growth guard, and the full-suite regression. Could not
refute any of them. The only substantive finding is the prompt wording above.
