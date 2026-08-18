# Adversarial review — issue_532 (`an-attempt-is-the-unit-of-accountability`)

Evidence re-run at `$PDCA_TARGET` (the patched tree, base `acb214a`): `PYTHONPATH=src
python3 -m unittest tests.test_leaf_resilience tests.test_build_error_log` → 43 tests OK;
the full `tests/` suite → 1784 tests OK in 29s (no wall-clock regression from the new
retry — `test_leaf_memory_log` at 2.4s is the slowest `do_build` module). The C4 red leg in
`gate-logs/C4-verify.log` is a genuine red (13 assertion failures + 7 `AttributeError`s on
symbols this patch adds), not a manufactured one. Findings below.

- **NEEDS-HUMAN [impl]** — `leaves.py:927` (`_format_leaf_attempt`) does **not** run
  `_defang_in_flight` over the captured stderr tail, although `_withdraw_residue` does over
  the withdrawn artifact (`leaves.py:910`). `leaf_run_incomplete` compares the log's last
  non-empty line for **equality** with the marker (`leaves.py:867`), and a leaf's own stderr
  tail is the last thing in the final record — so a leaf whose stderr ends on a line that
  *is* `_LEAF_IN_FLIGHT` (an ordinary day in this repo: a leaf quoting the diff hunk or the
  source line it is reviewing) makes a log written by a loop that **spent its whole budget**
  read as interrupted. Verified end-to-end on the production path — a reviewer driven through
  the real `leaves._run_review_sandboxed` with
  `output=f"traceback while quoting the diff hunk:\n{leaves._LEAF_IN_FLIGHT}"`: 3 attempts
  recorded, `leaf_run_incomplete → True`, `_leaf_ran_and_failed → False`,
  `review_never_ran → True`, and `driver._resume_interrupted_check` (`driver.py:176`) then
  paid **3 more reviewer spawns** for a leaf that had already given up — the #138/#369
  regression the patch's own docstring says the equality check exists to prevent. The test
  that claims this door (`tests/test_leaf_resilience.py:588`,
  `test_a_leaf_whose_stderr_quotes_the_marker_is_still_read_as_spent`) only exercises the
  marker embedded **mid-line** (`"echo of the source: <marker>"`), so it would not have gone
  red on this. Fix: defang in `_format_leaf_attempt` too, and widen the test to put the
  marker on its own final line. Same exposure via `run_advisory_leaves(only_missing=True)`
  (`leaves.py:3180`).

- **NEEDS-HUMAN** — criterion (iv)'s headline sentence is gated onto a shape that, by the
  harness's own classifier, cannot carry the residue it describes. `_report_transient_do_death`
  fires only when `_builder_retryable(exc)` (`leaves.py:1993`), i.e. only when the **final**
  attempt was transient — and transient means `produced is False`, i.e. no `assistant` /
  `item.started` stream event (`progress.py:359`, `progress.py:155`), i.e. the attempt did no
  tool work and wrote nothing. So the `state.BUILT` branch of `_next_action_after_a_dead_do`
  (`leaves.py:2089`, "runs CHECK on the residue patch.diff") and the "partial patch.diff"
  clause of `_BUILD_RETRY_NOTE` (`leaves.py:2114`) are unreachable in production: `do_build`
  is dispatched only at PLANNED (`driver.py:69-75`) and a bundle holding `patch.diff` reads
  BUILT (`state.py:211`). Conversely, the shape the brief's own Defect bullet names *does*
  happen and gets **nothing**. Verified with a real child builder: attempt 1 transient
  (retried), attempt 2 emits an `assistant` event, half-writes `patch.diff`, then the
  connection drops → substantive → the entire report is skipped; all the operator saw was
  `leaves: issue_506 — Do failed; captured the error tail in build.error.log`, while the
  bundle now reads **BUILT** and a plain re-run will run Check on a truncated patch. The
  bounded remedy is to gate only the "TRANSIENT … absorbed … after N attempts" sentence on
  `_builder_retryable` and print the residue + next-action lines for **every** failed Do —
  but that is a scope call the human should make, since the builder gated it deliberately and
  argued the gating in-code.

- **NEEDS-HUMAN [impl]** — following from the above, the only test covering criterion (iv)'s
  BUILT sentence (`tests/test_leaf_resilience.py:420`,
  `test_the_exhausted_report_is_true_for_the_residue_actually_left`) reaches it with
  `_DYING_BUILDER` (`tests/test_leaf_resilience.py:174`), a stub that writes `$RESIDUE` and
  then dies **without emitting a single stream event**. That combination — wrote a
  `patch.diff`, yet reads `transient` — is exactly what `progress._is_session_event` rules
  out, so the assertion `state.state(self.d) == state.BUILT` is earned by a leaf production
  cannot produce. It is red-worthy and green, but it is green for a reason the production
  classifier forbids; it does not evidence the criterion.

- `assemble.py:417` still uses the pre-#506 discriminator — bare
  `(d / state.REVIEW_ERROR_LOG).exists()` → "the reviewer RAN AND FAILED" — while the patch
  taught the other two readers (`leaves.review_never_ran`, `run_advisory_leaves`) that an
  in-flight log means *interrupted*. I tried to make the drift bite and could **not**:
  `_resume_interrupted_check` runs immediately before `assemble_summary` (`driver.py:130-132`),
  it is the only caller, and every path through `run_review` leaves a `check-review.md`
  (verdict or `_review_unavailable` placeholder), so `_missing_review_text` is not reachable
  with an in-flight log. Noted as latent inconsistency, not a defect.

- `check-gates.json` records **C5 "added test exercises production, not a copy" = pass** on
  the basis `"patch adds no new test file — nothing to assert"` (`gate-logs/C5-prod-path.log`
  asserts literally nothing). Iteration 1's sign-off carry-forward (`brief.md:197`) closed
  with "the C5-prod-path green is vacuous … Make production-path coverage adjudicable next
  round." The patch again appends to two existing files, so the gate is byte-identically
  vacuous and that carry-forward item is **unclosed**. The prod-path claim in this round rests
  on hand-reading again — which is how the two unfaithful-stub findings above survived.

- Attempted and could **not** refute: the `memory_log` derivation (`_memory_log_for` yields
  the identical `build.memory.jsonl`, #420 unchanged); `do_build`'s `_has_content` guard
  (`leaves.py:1987`) clobbering the per-attempt records; the fail-closed withdrawal
  (`_withdraw_residue` returns `ok=False` and the loop stops — the iteration-1 finding is
  genuinely closed); `_unavailable_classification` pointing at a log the success path just
  unlinked (it guards on `.exists()`, `leaves.py:2985`); a fourth un-owned harvest site
  (there are exactly three); the `_died_of_a_signal` 128+N widening (`progress.TIMEOUT_RC =
  -1001` is caught by the negative arm); and the wall-clock trap the brief warned about
  (`test_leaf_memory_log` and the seven other `do_build` modules pay no backoff).

- I did **not** treat as a refutation, but flag for the record: the invariant is stated over
  "**every** leaf it spawns", and nine leaves remain on plain `_invoke` after this patch
  (`leaves.py:990`, `:1179`, `:1717`, `:1803`, `:3613`, `:3642`, `:3689`, `:3781`, `:3846` —
  planner, sizer, splitter, plan-revision, sign-off, act, publisher). The brief's own
  self-test enumerates four sites (builder call site, wrapper flush, three harvests, operator
  message) and the patch covers all four, so this is the brief's scoping, not the patch's gap.
