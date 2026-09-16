# Check advisory — code-review lens (correctness + reuse/simplification)

Scope: `template/src/pdca_harness/{driver.py,leaves.py}` and the two test files this
patch touches. Grounded on the patched target at `$PDCA_TARGET`.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:789` (`records.append(_format_leaf_attempt(exc, attempt) + residue)`)
  vs `leaves.py:818-823` (`_defang_in_flight`). The in-flight trailer
  (`_LEAF_IN_FLIGHT`, `leaves.py:815`) is only neutralized inside the *withdrawn
  artifact* text (`_withdraw_residue`, `leaves.py:910`) before it is embedded in the
  error log. The captured **stderr tail** a failed attempt carries
  (`_format_leaf_attempt`, `leaves.py:922-928`, sourced from `exc.output`) is embedded
  raw, with no `_defang_in_flight` pass. `leaf_run_incomplete` (`leaves.py:853-867`)
  reads the log's *last non-blank line* for an exact match against the marker, so a
  leaf whose own stderr happens to end with a line that is byte-identical to
  `_LEAF_IN_FLIGHT` (a crash trace echoing this very source file, which the code's own
  comments concede is "an ordinary day" in this repo) would, on its *final* exhausted
  attempt, make a **spent** leaf read as merely *interrupted*. The regression is
  contained (`_leaf_ran_and_failed` would then treat the leaf as recoverable and
  #369's resume path re-runs it rather than leaving it un-reviewed), but it is the same
  hazard class the patch explicitly hardened for the artifact-residue path
  (`test_a_dead_attempts_artifact_ending_in_the_marker_is_not_the_trailer`,
  `test_leaf_resilience.py:1245-1258`) and left open on the sibling path
  (`test_a_leaf_whose_stderr_quotes_the_marker_is_still_read_as_spent`,
  `test_leaf_resilience.py:1260-1277`, only exercises a *prefixed* echo — `"echo of
  the source: " + marker` — never the marker alone on its own line, which is the
  actual failure mode). Applying `_defang_in_flight` to the `_format_leaf_attempt`
  output too (or to the joined `records` body just before the marker-equality check)
  would close the gap symmetrically.

- `leaves.py:900-919` (`_withdraw_residue`) reads a dead attempt's artifact with a
  single `artifact.read_text(...)` before truncating to `_RESIDUE_KEEP` (20 000
  chars). The docstring/comment anticipates "a runaway leaf could write an arbitrarily
  large file," but the truncation happens *after* the full file is materialized in
  memory rather than bounding the read itself. Minor — this only runs once per failed
  attempt, not a hot path, and typical verdict artifacts are KB-sized — so I'm not
  gating on it, just flagging as a cheap follow-up (`itertools.islice` over a stream,
  or `Path.open().read(_RESIDUE_KEEP + 1)`) should a leaf ever genuinely runaway-write.

## Not flagged (checked and clean)

- The `may_retry`/`recorded` gating in `_invoke_leaf_resilient` (`leaves.py:790-797`)
  correctly makes attempt N+1 contingent on attempt N's record having *landed*
  (`_write_attempt_records` return value folded into the break condition) — the
  fail-open this line's own prior iteration was rejected for (brief §Iteration 2 item 1)
  is closed.
- `_died_of_a_signal` (`leaves.py:2020-2033`) reads both the negative-`subprocess`
  and the 128+N wrapper-reported spellings, matching the carry-forward that flagged the
  single-spelling gap.
- `_next_action_after_a_dead_do` (`leaves.py:2076-2097`) asks `state.state(d)` rather
  than inferring from `patch.diff`'s presence, and the two round-3 tests
  (`test_the_exhausted_report_is_true_for_the_residue_actually_left`,
  `test_the_exhausted_report_asks_the_state_machine_not_the_residues_shape`) exercise
  the waterfall (patch.diff-only → BUILT vs patch.diff+check-gates.json → CHECKED)
  concretely, not just the happy path.
- `_report_transient_do_death` / the retry-notice print in `_invoke_leaf_resilient`
  are each wrapped in `contextlib.suppress(OSError)` at their call sites so a broken
  stderr (`BrokenPipeError`) can never replace the leaf's own exception on its way out
  to `flow._isolate` — verified against `test_a_broken_stderr_never_replaces_the_builders_own_failure`.
  `_do_residue` correctly makes no authorship claim about residue files (`"which may
  predate this attempt"`), addressing the earlier "the interrupted attempt left…" false
  statement.
- The scope constraint from the prior sign-off ("leave the `_invoke_leaf_resilient`
  docstring and the retry-backoff print line's wording alone, sibling #533 owns it") is
  honored: the print line's guarded but its literal text is byte-identical to the base,
  and the docstring is untouched (confirmed via `git diff` — no diff hunk touches those
  lines).
- `_memory_log_for` derivation is reused unchanged for the builder call site (no
  explicit `memory_log=` passed), and `"build.error.log"` derives to
  `"build.memory.jsonl"` (`BUILD_MEMORY_LOG`), preserving parity with the other three
  call sites per the brief's criterion (vi).
- No dead code left over from the two rejected prior iterations (`_disown_artifact`,
  `_report_exhausted_do_retries` are both absent from the current tree).
- The three harvest sites (`_run_review_sandboxed`, `_run_advisory_sandboxed`,
  `_run_plan_advisory_sandboxed`) apply the `artifact=` ownership mechanism
  identically; no copy/paste drift between them.

No other correctness bugs (off-by-one, leaks, concurrency, API misuse) or
reuse/duplication issues found in this diff.
