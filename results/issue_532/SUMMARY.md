# Result — issue 532 / an-attempt-is-the-unit-of-accountability

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The harness spawns leaves in bounded-retry loops, but nothing ties an
  artifact, an error record, or an operator sentence to the *attempt that produced it*.
  Three consequences, all live on the base:
  * **Do is never retried.** `_do_build_command` calls plain `_invoke`
    (`leaves.py:1824`), while the reviewer (`:2507`), the advisory (`:2840`) and the plan
    advisory (`:3142`) all run under `_invoke_leaf_resilient` (`:673-721`). So no builder
    failure is ever retried — on the leaf where an attempt is most expensive. The reported
    incident burned ~18 minutes and a cycle round to a dropped connection.
  * **A retried leaf inherits a dead attempt's work.** `_invoke_leaf_resilient` writes its
    attempt records only *after* the loop (`:720`), so while attempt 2 runs there is nothing
    on disk explaining attempt 1, and a killed run loses them all. The three harvest sites
    copy their artifact on a bare existence test — `:2520` (`check-review.md`), `:2851`,
    `:3152` — with no notion of *which* attempt wrote it, so a truncated verdict from a dead
    attempt is adopted as the leaf's own. This is live **today**, without any builder
    retry: those three leaves already retry.
  * **The exhausted death explains nothing.** `do_build` captures one record and re-raises
    (`:1765-1778`); the operator reads an argv and an exit status. What the honest next
    action *is* depends on residue: a bundle holding `patch.diff` reads BUILT
    (`state.py:224`), so `driver.advance` (`driver.py:76`) runs **Check** on that partial
    patch, not Do.
- Success criterion: With the patch:
  (i) a **transient** builder death is retried, bounded, with backoff, under the same
  `_invoke_leaf_resilient` contract the other three leaves use, while a **substantive**
  builder failure is still not retried; either way the final failure is still captured to
  `build.error.log` and still re-raised, so `flow._isolate` drops just this bundle as today;
  (ii) each attempt's error record is on disk **before** the next attempt starts, so a
  retried leaf — and a post-mortem of a run killed mid-retry — can read the predecessor's
  account instead of a file that does not exist yet;
  (iii) a retried **builder** is told in its prompt that a previous attempt died mid-flight
  and that any `patch.diff` / `build-notes.md` / test file present is that attempt's
  incomplete residue to verify or replace — never evidence the work is done;
  (iv) **every** failed Do — transient or substantive — prints the residue actually on disk
  and the next action true for it (naming, when a `patch.diff` was left, that the bundle now
  reads BUILT and a plain re-run runs Check on it); only the *"transient — absorbed after N
  attempts"* sentence is conditioned on the failure having been classified transient.
  Nothing deletes the builder's artifacts to make that sentence true. **(Settled at this
  re-plan — see Ordering note §2; round 3's gating of the whole report on retryability made
  the residue branch unreachable in production.)**
  (v) no artifact written by a **dead** attempt is harvested as a **successful** attempt's
  output at the reviewer / advisory / plan-advisory sites, and no dead attempt's captured
  stderr can impersonate the harness's own in-flight trailer: whatever marker distinguishes
  an interrupted log from a spent one must be neutralised in **both** the withdrawn-artifact
  text and the `_format_leaf_attempt` stderr tail (`:724-730`), which today embeds
  `exc.output` raw;
  (vi) nothing else changes: the shipped resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, the `_memory_log_for` derivation — derive it,
  do not pass `memory_log=` where the other three call sites do not; the builder's current
  explicit `memory_log=d / BUILD_MEMORY_LOG` at `:1830` derives to the identical file), the
  #420 memory-telemetry post-mortem still rides `output` into the same log, a successful
  build is spawned and reported exactly as today, `_stub_build` (`:1889`) behaves exactly as
  today, and both offline suites stay green **and fast** (see Falsifiability).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Who gets retried, what a retry may inherit, and what the operator is told when
  the retries run out — the leaf-invocation layer of #506. Put the builder on the existing
  resilient path; flush each attempt's record as it happens; tell a retried builder that a
  predecessor died mid-flight and that any artifacts present are its residue; make the failed
  Do report name the residue actually on disk and a next action true for it; and give the
  three artifact harvests a notion of which attempt produced what, including the stderr tail
  that today can impersonate the harness's own trailer.
  **Out of scope:** the stream-side question of *what counts as* a transient death and the
  retention of the leaf's own error text — that is sibling #533, and this work must not touch
  `progress.py`, redefine `LeafError.transient`, or add a signal-death predicate (Ordering
  note §3 — the retry set is reused exactly as shipped); a lane/worktree reset between attempts, and any new `pdca.toml` knob (reuse
  the shipped attempts/backoff defaults — a prompt-level statement of the residue is the
  bounded fix; if the rebuild concludes that is insufficient, say so in `build-notes.md`
  rather than expanding the slice); the gate-side transient (issue #371); issue #510's own
  remedy; `flow._isolate`'s containment contract and the `flow_one` library route's
  propagation (`flow.py:302-306` documents why the single-issue path differs); the #420
  memory-telemetry post-mortem, which must keep working unchanged; and the nine other leaves
  still on plain `_invoke` (planner, sizer, splitter, plan-revision, sign-off, act, publisher)
  — the invariant is stated over every leaf, but this slice's four sites are the ones the
  reported incident runs through.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (split), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
