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

Reviewing the attempt-accountability fix: resilient builder retries, durable per-attempt records, honest residue reporting, and attempt-owned reviewer/advisory artifacts.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance contract is explicit and falsifiable across retry classification, record durability, residue ownership, recovery advice, and unchanged behavior, with no external dependency required. |
| C2 Reproduction (red pre-fix) | PASS | With patched tests retained and production reverted, my offline run produced 12 failures and 4 errors, including the one-spawn builder behavior and dead-artifact adoption asserted at `template/tests/test_leaf_resilience.py:286` and `template/tests/test_leaf_resilience.py:523`. |
| C3 Change | FAIL | A retry is allowed before durable accountability is established: `_write_attempt_records` suppresses an `OSError` without reporting failure to the loop, which then sleeps and starts the next attempt; my forced write-error probe observed two invocations with no log (`template/src/pdca_harness/leaves.py:764`, `template/src/pdca_harness/leaves.py:788`). |
| C4 Verification (red→green) | PASS | Independent production-reverted tests were red, restoration made all 37 touched-module tests green, and the complete offline driver suite exited 0; the exercised contracts include pre-next-attempt visibility and interrupted-review recovery (`template/tests/test_leaf_resilience.py:329`, `template/tests/test_leaf_resilience.py:432`). |
| C5 Causal adequacy | PASS | The change addresses the eager causes directly by routing Do through the resilient wrapper and withdrawing failed-attempt artifacts before harvest; it adds no capability probe or symptom guard (`template/src/pdca_harness/leaves.py:762`, `template/src/pdca_harness/leaves.py:2108`). |
| T1 Structure | PASS | Scope remains in the leaf-invocation module and the two brief-mandated test modules; affected-path history confirms the existing #138/#369/#420 seams, and repository search surfaced no competing same-scope change. |
| T2 Shape | PASS | `git diff --check` is clean, while the frozen docs-lint, site-render/link-audit, and host-CI-parity logs all show successful patched-tree checks. |
| T3 Runtime | FAIL | The normal and interrupted paths pass, but under an attempt-log write failure the runtime continues a transient retry without the predecessor account that criterion (ii) requires, leaving a mid-retry kill with no post-mortem (`template/src/pdca_harness/leaves.py:797`, `template/src/pdca_harness/leaves.py:776`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted during Check; the frozen row is deferred and states that the substantive contribution audit reruns at publish. |
| T5 Judgment | FAIL | The sign-off decision should be iterate until starting attempt N+1 is contingent on attempt N's record being durably written, because otherwise the central accountability invariant still has a fail-open branch (`template/src/pdca_harness/leaves.py:780`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the operator-facing retry notice and exhausted-retry guidance are usable during a real interrupted provider session — offline stubs prove state transitions and wording, but not operational fitness under an actual connection drop (`template/src/pdca_harness/leaves.py:1975`, `template/src/pdca_harness/leaves.py:2025`). |

### Advisory — adversary

# Adversarial review — refuting the fix and its evidence (issue 532 / #506 child-1)

Re-ran the asserted red→green in a private copy of `$PDCA_TARGET` (never writing to it):
both patched test files green (37 tests), the whole offline suite green (1778 tests, 2
skipped), and the C4 red leg in `gate-logs/C4-verify.log` is a genuine red — 14 of the new
cases fail on the reverted production hunks for the reasons they claim, not on an import
error. The tests drive `leaves.do_build → _do_build_command → _invoke_leaf_resilient →
_invoke → progress → subprocess` with a real child; only `time.sleep` (and, in the capture
cases, the vendor spawn) stands in. **C4's verdict survives attack.** What follows is what
does not.

- **NEEDS-HUMAN [impl] — the exhausted-retry report asserts authorship it cannot know**
  (`template/src/pdca_harness/leaves.py:1993-1997`, fed by `_do_residue`
  `:1966-1972`, which only asks "does the file exist"). A *transient* death is by
  definition one that produced nothing, so bundle artifacts present at that moment are
  usually **not** the dead attempts'. Reproduced against the patched tree: a bundle at
  PLANNED holding a `build-notes.md` + brief-named test file written by an **earlier run**,
  with this Do's builder dying at spawn three times having written nothing, prints
  `issue_506 — the interrupted attempt left build-notes.md, test_x.py in the bundle …
  Read them as an unfinished attempt's residue`. That is false about both files, in the one
  sentence the brief's invariant governs ("nothing the harness tells the operator … about
  that residue may be false"). Carry-forward item 6 asked for these files to be named, not
  for their provenance to be invented; naming them ("the bundle holds …, which may predate
  this attempt") closes it.

- **NEEDS-HUMAN — the #510 signal-death exclusion is keyed on a premise the leaf's `argv`
  can break** (`leaves.py:1962-1963`, premise stated at `:1958-1960`: "`subprocess` reports
  a signal death as a NEGATIVE returncode"). That holds only when `argv[0]` *is* the process
  that dies. A wrapper argv — the documented `argv = ["local-build", …]` shape
  (`docs/04-do.md:47`), an `sh -c` launcher, `docker run` — reports an OOM SIGKILL of its
  child as **137**, a positive code. Reproduced on the patched tree with
  `argv=["/bin/sh","-c", …]` around a self-SIGKILLing leaf: `returncode 137`,
  `_builder_retryable → True`, **3 spawns**, and stderr reading `died of a TRANSIENT
  infrastructure failure (exit 137) — infra the harness absorbs` while `build.error.log`
  says `Killed`. That is verbatim the carry-forward item 3 defect, reached by a supported
  configuration instead of by the classifier. Whether to widen the exclusion (128+n) or
  leave the hole for #510 is a scope call the patch should not make silently.

- **NEEDS-HUMAN [impl] — a leaf that finished is left flagged "in flight"**
  (`leaves.py:753-756`). On the deliberately-retained-log path — a dead attempt's artifact
  was withdrawn and the successful attempt wrote none — the last write was
  `_write_attempt_records(..., in_flight=True)`, so the surviving log keeps
  `_LEAF_IN_FLIGHT` (`:785`). Reproduced: after `_run_review_sandboxed` completes,
  `check-review.error.log` ends with `<!-- pdca:leaf-attempt in-flight — the retry loop had
  not finished -->` and `leaves.leaf_run_incomplete(log)` returns **True** for a reviewer
  whose loop finished — contradicting that function's own contract (`:804-813`). The
  placeholder written a line later points the operator straight at that file. Blast radius
  today is the log's text (`_leaf_ran_and_failed` is only consulted where the placeholder
  already exists), but the fix is one line: re-flush with `in_flight=False` before returning
  success. Related fragility in the same predicate: it is a substring sniff, while the body
  now embeds up to 20 000 characters of the leaf's own artifact (`:825`, `:849-856`) — a
  verdict that *quotes* the marker (e.g. a review of this very patch) makes a completed log
  read as interrupted.

- **NEEDS-HUMAN [impl] — Do's failure path now has an unguarded stderr write, and it can
  replace the exception the criterion pins.** `do_build` keeps its capture inside
  `try/except OSError: pass` "never let error-capture mask the real failure"
  (`leaves.py:1925-1937`), but the newly-added `_report_exhausted_do_retries` prints
  (`:1988-1999`) sit outside it, and the builder is now also exposed to the wrapper's retry
  notice (`:773-775`), which raises out of `_invoke_leaf_resilient` entirely. Reproduced
  with a stderr that raises `BrokenPipeError` (`pdca run … | head`, a detached session, a
  full disk): patched tree → `do_build` raises **`BrokenPipeError`**, and the retries never
  run; pre-fix base, same probe → `LeafError`. Criterion (i) says "either way the final
  failure is still captured … and still re-raised".

- **NEEDS-HUMAN [impl] — the #369 discriminator's prose was updated in `leaves.py` but not
  where the driver states it**: `template/src/pdca_harness/driver.py:152-155` still
  documents the recovery rule as "`leaves.review_never_ran` — no artifact, no error log",
  which is exactly the reading the patch had to abandon. In a repo whose invariant is that
  what the harness says must be true, this is the one remaining sentence stating the old
  contract.

- **NEEDS-HUMAN — the C5 row is a green that asserts nothing, for the second round
  running.** `check-gates.json` records `C5 added test exercises production, not a copy →
  pass`, basis `patch adds no new test file — nothing to assert`
  (`gate-logs/C5-prod-path.log`) — the identical vacuous pass the sign-off carry-forward
  called out ("Make production-path coverage adjudicable next round"). It is unaddressed at
  the gate: the patch appends to existing files, so the oracle skips. The substance is
  mostly fine (I verified the builder and reviewer/advisory cases run production), but one
  of the three sites the fix exists for is proven only by **mocking the production wrapper**
  — `template/tests/test_leaf_resilience.py:573-595` patches `leaves._invoke_leaf_resilient`
  and then asserts `kw["artifact"] == cwd/"plan-advisory-lens.md"`, i.e. it re-states the
  call-site expression rather than exercising `_withdraw_residue` at that site. A human
  should decide whether that closes the carry-forward.

**Attempted and could not refute:** that the exhausted-retry advice is derived from
`state.state` rather than the residue's shape (`leaves.py:2011-2022` — PLANNED/BUILT/CHECKED
all verified true of the real waterfall); that fail-closed ownership stops the loop when the
withdrawal cannot be enforced (`:857-863`, no further spawn, no dead artifact adopted); that
`_memory_log_for` derivation yields the identical `build.memory.jsonl` and `_MemoryTelemetry`
still appends per spawn, so #420 is intact; that `progress.TIMEOUT_RC = -1001` is excluded
from the builder retry; that the shipped `systemd-run --user --scope` cap execs the leaf, so
the *shipped* OOM path really does surface as `-9`; that `_skip_backoff` does not busy-loop
the heartbeat (`progress.py` waits on `proc.wait(timeout=…)`, and its only `time.sleep` is
0.05 s); and that a dead attempt's artifact can be harvested at any of the three sites — the
harvest is unreachable while `err is not None`, and the withdrawal happens before the next
spawn. The residue-inheritance machinery is largely latent until sibling child-2 changes the
transient rule (a leaf that wrote an artifact has emitted a stream event, hence reads
substantive today) — which the brief's ordering note anticipates, so it is not a finding.

### Advisory — code-review

# Check — advisory code review (correctness + reuse/simplification lens)

Scope: this diff only (`template/src/pdca_harness/leaves.py` + the two appended test
files). Grounded on `$PDCA_TARGET`'s post-patch `leaves.py`, `state.py`, `progress.py`,
`config.py`, `brief.py`, `driver.py`.

## Verification of the six carry-forward findings from the prior iteration's sign-off

All six are addressed in this diff, and each is now backed by a genuinely red→green test
(confirmed in `gate-logs/C4-verify.log`: green leg 23/23, red leg with production hunks
reverted shows 11 failures + 3 errors across exactly the appended cases):

1. Fail-closed artifact ownership (`leaves.py:828-864`, `_withdraw_residue`) — `ok`
   is `False` when the unlink fails, and `_invoke_leaf_resilient:764`
   (`retry = retry_when(exc) and attempt < attempts and owned`) stops retrying on that
   `False`. `test_ownership_that_cannot_be_enforced_stops_the_retries` exercises it.
2. The #369 trap-door (`leaves.py:780-819`) — `_LEAF_IN_FLIGHT` + `leaf_run_incomplete` +
   `_leaf_ran_and_failed` correctly distinguish "interrupted mid-retry" from "ran and
   gave up" at all three sites that read it (`review_never_ran:2398`,
   `run_advisory_leaves:3106`, and the resume path via `driver._resume_interrupted_check`).
3. Signal-death scope leak (`leaves.py:1947-1963`, `_builder_retryable`) — filters
   `returncode < 0` (SIGKILL, and `progress.TIMEOUT_RC`) out of the retry class, one spawn,
   re-raised, exactly as before #506. #510 is not folded in.
4. Exhausted-retry next action (`leaves.py:2002-2022`) — now asks `state.state(d)`
   (a waterfall) instead of inferring from `patch.diff`'s presence; verified against real
   `state.state` in `test_the_exhausted_report_asks_the_state_machine_not_the_residues_shape`.
5. `_withdraw_residue` no longer renames into the doomed sandbox — the text is folded into
   the bundle-local `error_log`'s record (`leaves.py:836-856`), verified readable afterward
   by `test_the_withdrawn_verdict_is_readable_in_the_bundle_afterwards`.
6. The `residue` list is used, not dropped: `_report_exhausted_do_retries` (`leaves.py:1992-1999`)
   prints it and nothing deletes it; `test_the_exhausted_report_names_every_artifact_the_dead_attempt_left`
   asserts the files still exist afterward. C5 is still vacuous by construction (no *new*
   test file — the brief explicitly directs appending to existing files), but the C4 red/green
   log now makes production-path coverage of the appended cases adjudicable, closing that
   half of finding 6 as well.

## New findings from this pass

- The wiring at all three harvest sites (`_run_review_sandboxed:2798-2824`,
  `_run_advisory_sandboxed:3144-3159`, `run_plan_advisory`'s sandboxed helper
  `:3446-3461`) passes the *same* `Path` object as both `artifact=` to the wrapper and the
  post-call `if out.exists():` / `if produced.exists():` check, so there is no drift between
  what the wrapper owns and what the harvest reads — the shape a fresh reviewer of this
  pattern would specifically want to check for.
- `_do_build_command` (`leaves.py:2108-2119`) mirrors the three peer call sites' `err =
  _invoke_leaf_resilient(...); if err is not None: raise err` shape as directed by the brief,
  and correctly omits `memory_log=` so it's derived by `_memory_log_for(d / BUILD_ERROR_LOG)`
  → `d / "build.memory.jsonl"` (`BUILD_MEMORY_LOG`, `leaves.py:84`) — same file as before,
  confirmed by reading `_memory_log_for` (`leaves.py:363-373`).

- `_write_attempt_records` (`leaves.py:788-801`) swallows `OSError` on the write and just
  prints a warning, for *every* attempt including the final (exhausted) one. If that final
  write fails, the on-disk `error_log` is left holding whatever the *previous* attempt's
  flush wrote — which, if that previous flush happened while a retry was still pending,
  still carries the `_LEAF_IN_FLIGHT` trailer (`leaves.py:785`). `leaf_run_incomplete` /
  `_leaf_ran_and_failed` would then misclassify a leaf that actually *exhausted* its budget
  as merely "interrupted", and the #369 resume path (`review_never_ran`, `only_missing`)
  would re-invoke a leaf whose retries are already spent. This is a narrow edge (requires
  the write to fail specifically on the terminal flush, not an earlier one) and is strictly
  milder than the trap-door it replaces — pre-patch, the single end-of-loop
  `error_log.write_text(...)` had no `try/except` at all, so the same disk fault would have
  raised out of `_invoke_leaf_resilient` uncaught instead of leaving a stale marker. Not
  covered by any of the appended tests. Worth a look, not blocking.

- `_do_residue` (`leaves.py:1966-1972`) says in its docstring that the test file is
  "resolved as `_stub_build` resolves it", but `_stub_build` (`leaves.py:2177-2178`) falls
  back to `Path("test_stub.py")` when the brief names no test file, while `_do_residue` has
  no such fallback (it only lists names `brief.test_files` actually returns). Harmless in
  practice — `_do_residue` only fires on a command-backend retry exhaustion, where
  `_stub_build`'s stub-only fallback is never reached — but the docstring overclaims parity
  with a function whose fallback branch it doesn't share. Cosmetic.

## Reuse / simplification

- No duplicated logic against existing helpers: `_write_attempt_records`,
  `_withdraw_residue`, `leaf_run_incomplete` / `_leaf_ran_and_failed`, and `_has_content`
  are each new, single-purpose, and used at every site that needs the behavior (no
  copy-pasted variant left at the builder vs. the reviewer/advisory/plan-advisory sites).
- `_report_exhausted_do_retries`'s operator-facing prose duplicates some phrasing from
  `_unavailable_classification`'s `_FAIL_TRANSIENT` branch ("transient infra ... safe to
  re-run"). Not worth factoring out — one is a reviewer/advisory §6 placeholder sentence,
  the other an operator stderr narrative naming a state-machine consequence — but flagging
  in case a future edit wants a shared string.

## Overall

No correctness bug in this diff rises to blocking severity; the one item worth a look is
the stale in-flight marker on a failed terminal flush, noted above (not exercised by any
test in this patch, and strictly better than the pre-patch uncaught-write-failure behavior
it replaces).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether the operator-facing retry notice and exhausted-retry guidance are usable during a real interrupted provider session — offline stubs prove state transitions and wording, but not operational fitness under an actual connection drop (`template/src/pdca_harness/leaves.py:1975`, `template/src/pdca_harness/leaves.py:2025`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the implementation, not the slice. The shape is right and all six of the previous round's carry-forwards are genuinely closed with real red->green tests; what remains are local code defects, each confirmed by reading patch.diff directly. Do NOT re-cut this slice and do NOT re-attempt the previous approach unchanged. Must close before re-submission: 1. The retry starts even when the attempt record failed to write — criterion (ii) head-on. `_write_attempt_records` catches OSError, prints, and returns None; the loop computes `retry = retry_when(exc) and attempt < attempts and owned` BEFORE the write and never learns it failed, so attempt N+1 launches with attempt N's account absent from disk. Make starting attempt N+1 contingent on attempt N's record being durably written (return the write's success and fold it into `retry`, the same way `owned` already gates it). This is the patch's central invariant having a fail-open branch — it is the reviewer's C3/T3/T5 FAIL, which are one defect counted three times. Note `do_build`'s `if not _has_content(error_log)` guard does still capture the FINAL failure; what is lost is the per-attempt account during the retry window, and everything if the run is killed in that window. 2. An unguarded stderr write can replace the exception criterion (i) pins. `_report_exhausted_do_retries(d, exc)` sits OUTSIDE `do_build`'s `try: ... except OSError: pass` ("never let error-capture mask the real failure"), immediately before `raise`. BrokenPipeError is an OSError subclass, so a broken stderr turns the LeafError into a BrokenPipeError on the way out; the retry notice inside `_invoke_leaf_resilient` has the same shape. Criterion (i) requires the final failure to be captured and re-raised either way. Bring both prints under the guard. 3. The exhausted-retry message asserts authorship it cannot know. `_do_residue` is a pure existence check with no provenance, but the caller prints "the interrupted attempt left ...". A transient death by definition produced nothing, so those files are usually an EARLIER run's — making that sentence false in the one place the brief's invariant governs ("nothing the harness tells the operator about that residue may be false"). Name the files without claiming authorship, e.g. "the bundle holds ..., which may predate this attempt". Carry-forward item 6 asked for these files to be named, not for their provenance to be invented. 4. The signal-death carve-out is one wrapper deep — the previous round's item 3 reached through a different door. `_builder_retryable` excludes only `rc < 0`, but a wrapper argv (`sh -c`, `docker run`, the documented `local-build` shape) reports its child's OOM SIGKILL as 137 — positive. That is retried three times while stderr asserts "infra the harness absorbs" and build.error.log says `Killed`. The docstring's premise ("subprocess reports a signal death as a NEGATIVE returncode") holds only when argv[0] is the process that dies. Either widen the exclusion (128+n) or state explicitly why the hole is left to #510 — but do not leave it made silently. Worth a test either way. 5. A leaf that finished is left flagged "in flight" (one-line fix). On the deliberately-retained-log path — a dead attempt's artifact was withdrawn and the winning attempt wrote none — the last write was `in_flight=True` and the success path does not re-flush, so `leaf_run_incomplete()` returns True for a loop that finished, contradicting its own docstring. Re-flush with `in_flight=False` before returning success. Related fragility worth a look while you are there: that predicate is a substring sniff over a body that now embeds up to 20 000 characters of the leaf's own artifact, so a verdict that QUOTES the marker makes a completed log read as interrupted. SCOPE CONSTRAINT — LEAVE THE PROSE ALONE (decided at sign-off, binding on this rebuild): Do NOT touch the `_invoke_leaf_resilient` DOCSTRING or the retry-backoff PRINT line (`leaves.py:693-704` and `:728-730` on the base). Those two prose sites belong to sibling issue_533, which is landing its own rewrite of them, and which has been told at sign-off to keep them. This child owns the FUNCTION BODY, `do_build`, and the harvest sites — the mechanism, not the wording. Why this is binding and not a style note: verified mechanically at sign-off that the two patches collide. Both rewrite the same retry-print line, and the collision is SEMANTIC as well as textual — this round's version keeps "with no output (transient)", which is exactly the definition 533 exists to retire, so if this child lands second and wins that hunk the operator-facing prose silently regresses to the wrong contract. This round's patch also rewrites the docstring 533 rewrites, and deletes an `error_log.write_text(...)` line that sits in 533's trailing context. Keep the label-prefix improvement if it is still wanted (`kw.get('label') or workdir.name` — a real fix, since `workdir` names the sandbox or the harness root, not the bundle), but apply it WITHOUT restating the transient definition: take 533's wording for the classification clause and change only the name. Recommended merge order is unchanged (this child first, then 533), so expect 533's prose to land on top. Related, and worth settling with the sibling rather than alone: the signal-death boundary. This child's `_builder_retryable` excludes `rc < 0` but misses a positive 137; 533's `died_of_reported_infra` excludes neither. Same boundary, opposite holes, two children each inventing half of it. 533's carry-forward carries the mirror of this note. Non-blocking, close if cheap: `driver.py:152-155` still documents the old recovery rule ("no artifact, no error log") — the reading this patch had to abandon, and the last sentence in the codebase stating the old contract; `_do_residue`'s docstring overclaims parity with `_stub_build`'s `Path("test_stub.py")` fallback, which it does not share. C5 remains vacuously green ("patch adds no new test file") for the second round running, because the brief directs appending to existing files. Not a reason to reject, and the C4 red/green log does make the appended cases adjudicable — but it means C5 is carrying no weight on this bundle and should not be read as evidence. Section 6 (Validation — fitness-to-purpose) is deliberately left OPEN: no real interrupted provider session was induced. Findings 2, 3 and 4 above are each a case where the operator-facing wording is factually wrong, which is that item's substance and should be re-examined once they are closed.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
