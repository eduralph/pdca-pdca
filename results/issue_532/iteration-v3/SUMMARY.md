# Result — issue 532 / an-attempt-is-the-unit-of-accountability

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The builder is the only leaf the harness never retries, and the retry path it
  is missing has two attempt-ownership holes of its own. All verified on the target base
  (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **Do is never retried.** `_do_build_command` calls plain `_invoke`
    (`template/src/pdca_harness/leaves.py:1824`), while the reviewer (`:2507`), the advisory
    (`:2840`) and the plan advisory (`:3142`) all run under `_invoke_leaf_resilient`
    (`:673-721` — bounded retry with backoff plus a per-attempt error log, #138). So **no**
    builder failure is ever retried — on the leaf where an attempt is most expensive, and
    where the #135 escalation ladder's deep tiers (opus/`--effort max`) run longest. The
    reported incident burned ~18 minutes and a whole cycle round to a dropped connection.
  * **The exhausted death explains nothing and its "next step" would be false.** `do_build`
    captures one record and re-raises (`:1765-1778`); what the operator reads is
    `build/check failed (LeafError: Command '[…]' returned non-zero exit status 1)` — an
    argv and an exit status. And the honest next action depends on what the dead attempt
    left behind: a bundle holding `patch.diff` reads **BUILT** (`state.py:211`), so
    `driver.advance` (`driver.py:76`) runs **Check** on that partial patch, not Do.
  * **A retry would inherit the dead attempt's work.** Two holes, both live the moment any
    leaf is retried after producing output: `_invoke_leaf_resilient` writes its attempt
    records only *after* the loop (`:720`), so while attempt 2 runs there is nothing on disk
    explaining attempt 1 (and a killed run loses them all); and the three harvest sites
    copy their artifact `if produced.exists()` — `:2519-2523` (`check-review.md`),
    `:2851-2854`, `:3152-3155` — with no notion of *which* attempt wrote it, so a truncated
    verdict from a dead attempt can be adopted as the leaf's own. `worktree.ensure` likewise
    runs once, before the wrapper (`:1791`), so a retried builder opens a worktree still
    carrying the dead attempt's edits and a bundle that may already hold `patch.diff` /
    `build-notes.md`.
- Success criterion: With the patch:
  (i) a **transient** builder death is retried, bounded, with backoff, under the same
  `_invoke_leaf_resilient` contract the reviewer/advisory leaves use, while a **substantive**
  builder failure is still not retried; either way the final failure is still captured to
  `build.error.log` and still re-raised, so `flow._isolate` drops just this bundle exactly as
  today;
  (ii) each attempt's error record is on disk **before** the next attempt starts, so a
  retried leaf — and a post-mortem of a run that was killed mid-retry — can read the
  predecessor's account instead of a file that does not exist yet;
  (iii) a retried **builder** is told in its prompt that a previous attempt died mid-flight
  and that any `patch.diff` / `build-notes.md` / test file present is that attempt's
  incomplete residue to verify or replace — never evidence the work is done;
  (iv) when the bounded retries are exhausted, what the operator reads names the transient
  classification, points at the on-disk account, and states a next action that is **true for
  the residue actually present** (naming, when a partial `patch.diff` was left, that the
  bundle now reads BUILT and a plain re-run would run Check on it); nothing deletes the
  builder's artifacts to make that sentence true;
  (v) no artifact written by a **dead** attempt is harvested as a **successful** attempt's
  output at the reviewer / advisory / plan-advisory sites;
  (vi) nothing else changes: the existing resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, the `_memory_log_for` pairing — derive it, do
  not pass `memory_log=` explicitly where the other three call sites do not), the
  memory-telemetry post-mortem (#420) still rides `output` into the same log, a successful
  build is spawned and reported exactly as today, and both offline suites stay green **and
  fast** (see Falsifiability).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Who gets retried, what a retry may inherit, and what the operator is told when
  the retries run out — the leaf-invocation layer of #506. Put the builder on the existing
  resilient path; flush each attempt's record as it happens; tell a retried builder that a
  predecessor died mid-flight and that any artifacts present are its residue; make the
  exhausted-retry report name the class of failure, where its account is, and a next action
  that matches the residue actually on disk; and give the three artifact harvests a notion of
  which attempt produced what.
  **Out of scope:** the stream-side question of *what counts as* a transient death and the
  retention of the leaf's own error text — that is sibling child-2, and this child must not
  touch `progress.py` or change the transient rule; a lane/worktree reset between attempts,
  and any new `pdca.toml` knob (reuse the shipped attempts/backoff defaults — a prompt-level
  statement of the residue is the bounded fix; if the rebuild concludes that is insufficient,
  say so in `build-notes.md` rather than expanding the slice); the gate-side transient
  (issue #371 — the same argument one layer down, its own slice); a leaf **signal-death**
  under the memory cap (issue #510 states it "is neither #506's transient nor #421's
  preflight" — do not fold it in); `flow._isolate`'s containment contract and the `flow_one`
  library route's propagation (`flow.py:302-306` documents why the single-issue path differs);
  the memory-telemetry post-mortem (#420), which must keep working unchanged.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing the fix that makes every spawned leaf attempt accountable by retrying transient Do failures, persisting predecessor evidence, preventing dead-attempt artifact harvest, and reporting truthful recovery actions.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines bounded retry, pre-retry evidence, residue ownership, truthful next-action reporting, compatibility constraints, and an offline oracle with no external dependency. |
| C2 Reproduction (red pre-fix) | PASS | With only the production hunks stashed and the new tests retained, the two touched modules ran 43 tests with 14 failures and 8 errors, including the one-attempt builder and dead-verdict harvest gaps exercised at `template/tests/test_leaf_resilience.py:305` and `template/tests/test_leaf_resilience.py:663`. |
| C3 Change | FAIL | A completed exhausted leaf is misclassified as interrupted when its captured stderr ends with the exact in-flight marker: the formatter preserves that payload verbatim and the discriminator treats the last matching line as its own trailer (`template/src/pdca_harness/leaves.py:815`, `template/src/pdca_harness/leaves.py:853`, `template/src/pdca_harness/leaves.py:922`). |
| C4 Verification (red→green) | PASS | Restoring the production patch changed the independently reproduced 14-failure/8-error red to 43/43 green, and the full offline driver suite plus compile check completed green; the focused assertions traverse the production entry points at `template/tests/test_leaf_resilience.py:305` and `template/tests/test_build_error_log.py:101`. |
| C5 Causal adequacy | PASS | The change acts at the shared retry, record-flush, and artifact-ownership boundaries rather than adding a capability probe or downstream symptom guard (`template/src/pdca_harness/leaves.py:722`, `template/src/pdca_harness/leaves.py:787`, `template/src/pdca_harness/leaves.py:2880`). |
| T1 Structure | NEEDS-HUMAN | Decide whether this child may own transient-classification prose and the retry-print site reserved for sibling #533 — the new description and edited print recreate a known semantic/textual overlap that can affect merge order (`template/src/pdca_harness/leaves.py:674`, `template/src/pdca_harness/leaves.py:802`). |
| T2 Shape | PASS | `git diff --check`, Python compilation, the frozen docs lint/render audit, and its host-CI parity run are clean; the patch remains confined to the four brief-owned source/test files. |
| T3 Runtime | FAIL | A direct production-function probe formats an exhausted attempt whose stderr is exactly the marker and returns `leaf_run_incomplete=True`, allowing CHECKED-resume recovery to exceed the bounded attempt budget (`template/src/pdca_harness/leaves.py:838`, `template/src/pdca_harness/leaves.py:866`, `template/src/pdca_harness/driver.py:176`). |
| T4 Contribution | N/A | The contribution gate is deferred by design because `pr-description.md` is drafted after Check; publish reruns the substantive audit and no human clearance is owed now. |
| T5 Judgment | FAIL | The affected-path merged/open/rejected prior-art check is present, but the exact stderr-marker collision escaped judgment because the regression test prefixes the marker with other text and therefore cannot exercise a marker-only final line (`template/tests/test_leaf_resilience.py:588`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the corrected bounded-retry and residue-accountability behavior is fit for real provider interruptions — automated evidence uses faithful Python leaf processes, but operational provider recovery and operator messaging remain a sign-off judgment. |

### Advisory — adversary

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

### Advisory — code-review

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

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T1 Structure — Decide whether this child may own transient-classification prose and the retry-print site reserved for sibling #533 — the new description and edited print recreate a known semantic/textual overlap that can affect merge order (`template/src/pdca_harness/leaves.py:674`, `template/src/pdca_harness/leaves.py:802`).
- [ ] Validation — fitness-to-purpose — Decide whether the corrected bounded-retry and residue-accountability behavior is fit for real provider interruptions — automated evidence uses faithful Python leaf processes, but operational provider recovery and operator messaging remain a sign-off judgment.
- [ ] `template/src/pdca_harness/leaves.py:789` (`records.append(_format_leaf_attempt(exc, attempt) + residue)`)
- [ ] size backstop — this slice is behaving oversized: patch is 82 KB (threshold 80 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Human rationale (sign-off, issue_532): iterate-plan to settle the C5 item. What the re-plan must author: - C5 ("added test exercises production, not a copy") has been vacuously green three rounds running — "patch adds no new test file — nothing to assert" — because the brief directs appending to existing test files. Round 1's sign-off carry-forward already asked for this and it is still unclosed. The next brief must make production-path coverage adjudicable instead of leaving C5 carrying no weight; hand-reading in its place is how the two unfaithful-stub findings below survived. - Slice size: 82 KB against the 80 KB backstop, and round 3 of implementation-shaped findings every round. Author the split at Plan (`pdca-pdca split 532`, then `pdca-pdca split 532 --accept`) rather than re-cutting it in Do. - Criterion (iv) is not implementable as written. The exhausted-retry report is gated on `_builder_retryable`, but transient means the attempt produced nothing, so the BUILT / "partial patch.diff" branch is unreachable in production — while the half-written-patch shape the brief's own defect bullet names is classified substantive and gets no report at all. The brief must settle whether the residue + next-action lines print for every failed Do, or drop the claim. - Carry into whichever child keeps the mechanism: `_format_leaf_attempt` does not run `_defang_in_flight` over the captured stderr tail, so a leaf that spent its whole budget but whose stderr ends on a line equal to the marker reads as merely interrupted and buys extra spawns (reviewer C3/T3/T5, both advisory lenses, verified end-to-end on the production path). The fix is small; the test must place the marker alone on its own final line, not mid-line. - The T1 scope constraint versus sibling #533 (leave the `_invoke_leaf_resilient` docstring and the retry-backoff print wording to 533) was honored this round — keep it binding through the re-slice. §6 NEEDS-HUMAN items were left open — none were cleared.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
