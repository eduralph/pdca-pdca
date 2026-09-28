# Advisory review — adversary (issue 541, round 5)

Lens: refute the red→green, find the input that breaks the fix, name the unwarranted claim.
I reproduced both legs myself in a scratch copy of `$PDCA_TARGET` (post-fix: 23 tests OK; the
same module with `assemble.py`/`leaves.py` reverted to HEAD: 12 failures + 5 errors), so the
C4 row is not taken on trust. The three part-B legs go red for the right reason
(`test_the_trailer_counts_only_as_the_artifacts_last_non_blank_line`,
`test_a_closed_artifact_is_real_at_every_reader_whatever_it_quotes`,
`test_a_closed_advisory_keeps_its_impl_routing_into_section_6`) and they drive the three
production readers, not copies.

## Findings

- NEEDS-HUMAN [impl] — **The completion instruction is not the leaf's last word at two of the
  three write sites, and the 4e leg cannot see it.** `_COMPLETION_INSTRUCTION` is appended to
  the *constant* (`leaves.py:2400`, `leaves.py:3181`), but the prompt actually handed to the
  leaf is `_REVIEW_PROMPT + rubric_mod.for_reviewer(d, cfg)` (`leaves.py:2952`) and
  `(… + instruction) + rubric` (`leaves.py:3182`). Concrete case: any project with a standing
  rubric configured (`rubric.for_reviewer` returns non-empty, `rubric.py:270-283`) — I composed
  it and the review/advisory prompts then end with the host's rubric text, with "…as the very
  last line of the file … Nothing may follow it" buried mid-prompt. The 4e leg
  (`tests/test_attempt_harvest.py:684`) asserts `assertIn(_TRAILER, prompt)` against
  `leaves._REVIEW_PROMPT` / `leaves._advisory_prompt(_SPEC, _ADVERSARY)` with **no rubric**, so
  it passes either way and would not catch the instruction being pushed further from the end.
  Cheap fix: assert on the composed prompt (pass a non-empty rubric in the leg), and/or append
  the instruction at the composition site. Only the plan-advisory site (`leaves.py:3389`) has
  it genuinely last.

- NEEDS-HUMAN — **The mechanism's load-bearing claim is false for exactly the artifact class
  this issue is about.** `assemble.py:132` (and the brief, Scope §4/§"Why absence is inert")
  states "a dying attempt's half-written report cannot have [closed itself]". It can: an
  advisory that *quotes* the trailer — which every advisory reviewing #541 must — and is cut
  off at that line ends with the trailer as its last non-blank line. I ran it: a report
  containing a `pdca:leaf-status` marker in its body and truncated immediately after a quoted
  trailer inside an unclosed fence returns `leaf_status(...) == ""`, i.e. **read as a real
  closed verdict**. I could not find a *reachable* production path for it on its own — the
  harvest withdraws such a residue, and the sandbox is a fresh `TemporaryDirectory`
  (`leaves.py:2899`) — but it composes with the explicitly-accepted metadata-only-touch hole in
  `_residue_identity`: in that scenario a dead attempt's truncated text is both filed *and*
  read as a closed verdict, i.e. one accepted hole upgrades the other. This needs no code
  change if the human accepts the claim as approximate; what I am asking for is that the
  sentence in the docstring (and the brief's rationale) not be left asserting an impossibility
  that is merely improbable, since that sentence is what a sixth round would rely on.

- NEEDS-HUMAN [impl] — **A stale-edit leftover in a comment the brief made a binding scope
  item.** Scope §3 required every comment justifying the struck fourth token to be replaced
  with the actual rule. `leaves.py:3032` reads "so neither \"leaf did not run\" would be true
  of it" — a half-deleted "neither … nor …" from the rejected design (the second arm, "nor
  'produced no usable verdict'", is what B-simple gave up). As written it is ungrammatical and
  its remaining meaning is the opposite of what the paragraph then concludes (`human-empty`
  *is* taken). One-line reword; the same paragraph is otherwise correct.

- (Not a defect, an observation on the brief.) The brief's honesty note classes "the 4e
  write-site legs" as **green pre-fix by construction**. They are not: pre-fix the symbols do
  not exist and `test_every_instructable_leaf_closes_its_artifact_and_no_placeholder_does`
  errors on `assemble.LEAF_COMPLETE_TRAILER` (`tests/test_attempt_harvest.py:677`) — visible in
  the frozen `gate-logs/C4-verify.log`. The patch is stronger than the brief credited it,
  and `check-gates.json`'s C4 wording claims nothing beyond what I verified.

## Attempted and could not refute

- **A forged "closed" artifact.** 13 probes against `assemble.leaf_status` (`assemble.py:138`):
  quoted trailer followed by a closing fence, blockquoted, inline in prose, with a trailing
  period, followed by a footer comment, CRLF, indented, trailing blank/NBSP lines, empty input.
  Every one falls through to today's behaviour; only a genuine last-line trailer returns real.
- **A new false-placeholder.** The guard is strictly a widening of "real", so 4b holds by
  construction: for any artifact whose last non-blank line is not the trailer the function is
  byte-identical to HEAD. The three hard-excluded suites are untouched (`git diff --stat HEAD
  -- template/tests/` is empty) and `test_leaf_status.py` + `test_leaf_resilience.py` +
  `test_attempt_ownership.py` pass unmodified (31 tests).
- **A fourth, unconverted reader.** Repo-wide search for `leaf_status` / `LEAF_STATUS` /
  `pdca:leaf-status` finds exactly the three readers the brief names (`assemble.py:216`,
  `size_signal.py:240`, `leaves.py:3452`) and no shell/script/doc reader; no second classifier
  (`NOT COMPLETED` appears only at the three write sites).
- **A fourth harvest site / a narrowed retry contract.** `_LeafHarvest.run` (`leaves.py:868`) is
  the only caller of `_invoke_leaf_resilient` in `src/`; the surviving direct callers are tests.
- **Two harvest scenarios the suite does not cover**, driven through the real entry points:
  two consecutive deaths then a live write (filed, `_runs == 3`, no error log), and a dead
  attempt leaving a *complete, closed* artifact (refused, preserved unsettled in the error log,
  placeholder `human-empty`) — both behave as the design says.
- **Import-time breakage on the supported floor (≥3.11).** The forward reference
  `harvest: _LeafHarvest | None` at `leaves.py:684` precedes the class, but
  `from __future__ import annotations` is present (`leaves.py:35`), so this is not a
  3.14-only pass.
- **Un-owned prose that lies.** `_FAIL_UNOWNED` can only be reached after a withdrawal, so the
  account the prose points at (`leaves.py:3062`) always exists except on a best-effort write
  failure; and `review_never_ran` (`leaves.py:2538`) is not tripped by the preserved unsettled
  log, because the placeholder artifact exists.

<!-- pdca:leaf-complete -->
