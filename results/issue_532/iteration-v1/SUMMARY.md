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

Task under review: make transient builder and review-leaf retries bounded, diagnosable, residue-aware, and accountable per attempt without retrying substantive failures.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief gives an explicit retry/accountability invariant, separates transient-classification work into its sibling slice, and supplies offline falsifiability with no external dependency. |
| C2 Reproduction (red pre-fix) | PASS | With only production reverted and the new tests retained, the affected modules produced 7 failures and 2 errors, including the builder-budget and dead-verdict cases at `template/tests/test_leaf_resilience.py:240` and `template/tests/test_leaf_resilience.py:346`. |
| C3 Change | FAIL | Artifact ownership is not actually fail-closed: when both rename and fallback unlink raise, the unlink error is suppressed and control continues, leaving a dead attempt's file eligible for harvest despite the opposite diagnostic (`template/src/pdca_harness/leaves.py:783`). |
| C4 Verification (red→green) | PASS | Restoring production changed the independently observed 7-failure/2-error red leg to 28/28 affected tests green, and the complete offline driver suite exited 0; the exercised contracts are pinned at `template/tests/test_leaf_resilience.py:240` and `template/tests/test_build_error_log.py:94`. |
| C5 Causal adequacy | PASS | The normal-path fix assigns records, prompts, and artifacts at the retry wrapper/call sites rather than adding a capability probe or guarding an eager side effect (`template/src/pdca_harness/leaves.py:726`, `template/src/pdca_harness/leaves.py:1984`). |
| T1 Structure | PASS | The change stays within the shared retry wrapper, builder invocation, three harvest sites, and their two existing test modules; no sibling transient-classification surface is changed (`template/src/pdca_harness/leaves.py:673`, `template/src/pdca_harness/leaves.py:2668`). |
| T2 Shape | PASS | `git diff --check` and the local docs lint passed; the frozen T2 and host-CI logs also show clean site rendering and link audits. |
| T3 Runtime | FAIL | Despite the green standard suites, injected rename+unlink failures made the wrapper return success after two attempts with `dead_artifact_still_harvestable=True`, which the later existence-only harvest would adopt (`template/src/pdca_harness/leaves.py:783`, `template/src/pdca_harness/leaves.py:2686`). |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; the frozen deferred row states that the substantive contribution audit re-runs at publish. |
| T5 Judgment | NEEDS-HUMAN | Maintainer must compare the archived rejected issue-506 iteration by affected path against this patch — merged PRs #140/#286 and current open overlaps were mechanically checked, but the rejected artifact is outside the allowed review inputs, so reuse-versus-rejected-design cannot be settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Maintainer must decide whether fresh-session retry plus residue instructions is operationally fit for a real long-running vendor failure — the Python leaf stubs exercise the mechanics (`template/tests/test_leaf_resilience.py:134`) but cannot establish recovery quality after an actual mid-response drop. |

### Advisory — adversary

# Adversarial review — issue_532 (advisory; never gates)

Re-ran the red→green myself on `$PDCA_TARGET` (Python 3.14, offline):
`PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience tests.test_build_error_log`
→ 28 tests, OK, 0.73 s; the frozen `gate-logs/C4-verify.log` red leg shows 6 failures + 1
error on the reverted production hunks, each on the assertion the hunk exists for. The
red→green is real and the new cases drive the production path (`do_build` →
`_invoke_leaf_resilient` → `progress.run_with_heartbeat` → a real `subprocess` child), not a
re-implementation. The refutations below are about the fix and about what the evidence does
*not* cover.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:1888-1894`: the
  exhausted-retry "next action" decides BUILT/CHECK from `(d / "patch.diff").exists()`
  instead of from the state machine it cites, so it is false exactly on the bundle its own
  advice creates. Repro (ran it): a bundle that already holds `check-gates.json` (the
  operator followed this message's own "Move it aside to re-run Do" last round) + a builder
  that dies transiently after writing a partial `patch.diff` → the operator is told *"a
  bundle holding patch.diff reads BUILT — so `pdca run 506` would run CHECK on that PARTIAL
  patch"*, while `state.state(d)` returns **CHECKED** (`template/src/pdca_harness/state.py:222-226`)
  and `driver.advance` runs `_resume_interrupted_check` + `assemble_summary`
  (`template/src/pdca_harness/driver.py:116-130`) — i.e. it assembles a SUMMARY over the
  partial patch and a stale gate record, not a Check. Success criterion (iv) asks for a next
  action "true for the residue actually present"; asking `state.state(d)` would make it true
  in all cases. The new test only exercises a bundle with no `check-gates.json`
  (`template/tests/test_leaf_resilience.py:294-311`), so it cannot see this.

- **NEEDS-HUMAN** — `template/src/pdca_harness/leaves.py:742` (the per-attempt flush,
  criterion (ii)) silently disarms the #369 trap-door recovery for a run **killed mid-retry**
  — the very scenario (ii) advertises. `review_never_ran` is "no artifact **and** no error
  log" (`leaves.py:2266-2267`, consumed at `driver.py:170-175`), and the advisory resume uses
  the same discriminator (`leaves.py:2966-2968`). Ran both legs of the same probe (reviewer
  fails transiently, then the run is Ctrl-C'd during the retry): on the **pre-fix base**
  `check-review.error.log` is absent → `review_never_ran → True` → the reviewer is recovered
  on the next `pdca run`; **with the patch** attempt 1's record is already on disk →
  `review_never_ran → False` → the reviewer is never re-run, assembly fills the
  missing-review placeholder and the bundle can reach sign-off with no review of the diff.
  That contradicts criterion (vi) ("nothing else changes") and needs a human call on which
  contract yields (e.g. flush under an in-flight suffix, or teach the discriminator that a
  record short of the attempt budget is not "ran and failed").

- **NEEDS-HUMAN** — `template/src/pdca_harness/leaves.py:1883-1886`: a builder **signal
  death** — the case the brief puts out of scope ("issue #510 … do not fold it in") — is now
  retried and mis-reported as absorbed infra. Ran it: a builder SIGKILLed before its first
  substantive stream event (an OOM under the #420 cap, a scope that dies at spawn) exits
  `-9` with `produced=False`, so `LeafError.transient` is True (`leaves.py:106-108`) → **3
  spawns instead of 1** (each repeating whatever exhausted the memory bound), and stderr
  reads *"the builder leaf died of a TRANSIENT infrastructure failure (exit -9) — infra the
  harness absorbs, not a build that failed on the merits"* while `build.error.log` carries
  the #420 memory post-mortem saying otherwise. The classifier is child-2's, but this patch
  is what extends it to the leaf where the memory cap exists and what adds the assertive
  prose.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:775-777`: `_disown_artifact`
  justifies itself with "Renamed, not deleted: the dead attempt's text stays readable beside
  it for the run's post-mortem" — false at **all three** call sites, which are temp sandboxes
  destroyed on exit (`leaves.py:2627`, `:2979`, `:3276`; the rename target is
  `artifact.with_name(...)`, i.e. inside the doomed dir). Ran it: attempt 1 writes a
  full-looking verdict table and dies transiently, attempt 2 returns alive without writing →
  bundle ends with `check-review.md` = "NOT COMPLETED … (reviewer produced no
  check-review.md)" (`leaves.py:2689`) and **no** `*.before-attempt*` anywhere. Criterion (v)
  is met (nothing dead is adopted), but the harness now tells the operator no verdict was
  produced when one was produced and discarded — the second half of the invariant. Copying
  the disowned file into the bundle (`check-review.md.dead-attempt1`) would make both claims
  true.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:1887,1895-1898`: the `residue`
  list is computed and then dropped on the floor in the no-patch branch. Ran it: a builder
  that wrote `build-notes.md` and then died transiently leaves it in the bundle, and the
  operator is told *"no patch.diff was left behind … its inputs are intact — `pdca run 506`
  re-drives Do from the top"* — silent about the half-written `build-notes.md` (and any
  brief-named test file) actually on disk, which the re-driven Do inherits with **attempt 1's
  prompt**, i.e. without `_BUILD_RETRY_NOTE`. That is the exact mis-read (iii) exists to
  prevent, one level up. `test_the_exhausted_report_sends_a_bundle_with_no_patch_back_to_do`
  (`template/tests/test_leaf_resilience.py:313-320`) only covers the nothing-left-behind case.

- Evidence note (no rebuild implied): the criterion (v) leg is red only against a state
  production cannot currently produce. `transient` means `produced is False`
  (`leaves.py:106-108`), and `produced` is "the child emitted a **substantive** stream event"
  (`template/src/pdca_harness/progress.py:59-63`, set at `leaves.py:670`) — a leaf that wrote
  `check-review.md` necessarily emitted one, so today it is classified substantive, not
  retried, and the harvest is skipped anyway. The test manufactures the combination by
  stubbing `_invoke` with a hand-built `LeafError(produced=False)` that also writes the file
  (`template/tests/test_leaf_resilience.py:346-364`). The brief asked for (v) and calls it
  pre-emptive, so this is not a defect — but "genuine red on the current base" is true only
  in the stubbed sense; the hunk earns its keep once sibling child-2 lands.

- Verdict note: the `C5-prod-path` row's pass is **vacuous** — "patch adds no new test file —
  nothing to assert" (`check-gates.json:44-53`, `gate-logs/C5-prod-path.log`). Nothing
  adjudicated that the ~10 appended cases hit production; I checked that by hand instead (they
  do). A review that cites C5 as evidence of production coverage would be over-reading it.

- Minor, unprefixed: `template/src/pdca_harness/leaves.py:1858-1859` — when
  `_write_attempt_records` loses its write (OSError), the outer capture re-labels the *final*
  attempt's exception as `----- attempt 1 -----`. Cosmetic, but it is the fallback whose whole
  job is the post-mortem's honesty.

- Attempted and could **not** refute: the `memory_log` derivation (`_memory_log_for("build.error.log")`
  is byte-identically `d / BUILD_MEMORY_LOG`, `leaves.py:362-372,83`, and `test_leaf_memory_log.py:272`
  still passes, #420 intact); telemetry across retries (`_MemoryTelemetry` appends with a
  `spawn` boundary, `leaves.py:421-439`); the `_has_content` guard against the outer capture
  clobbering the per-attempt records (`leaves.py:1858`); attempt 1's prompt byte-identity and
  the note landing from attempt 2 on (`leaves.py:729-731`, verified from inside the child);
  the substantive-failure leg (1 spawn, no "retry", no "TRANSIENT"); re-raise into
  `flow._isolate` unchanged (`leaves.py:1993-1994`); the success-path unlink not turning a
  working leaf into a failure (`leaves.py:732-737`); and the wall clock — both touched files
  run in 0.73 s with only `time.sleep` patched, the shipped attempts/backoff defaults intact.

### Advisory — code-review

# Check advisory — code review (2nd lens: correctness bugs + reuse/simplification)

Reviewed `patch.diff` against the target source under `$PDCA_TARGET`
(`template/src/pdca_harness/leaves.py:673-812, 1820-1994, 2620-2690, 2976-3020,
3280-3321`) and the two test files it touches. Traced every new code path by hand
(attempt-numbering, transient-vs-substantive classification, the artifact
disown/harvest sequencing, the Do exhausted-retry report vs. `state.state`/
`driver.advance`) and cross-checked against the frozen gate evidence
(`gate-logs/C4-verify.log`: red leg genuinely fails — 6 failures + 1 error, all in
the newly-appended assertions, no import error; green leg is clean, 14/14 in both
touched test files; `gate-logs/T3-suite.log`: full 1769-test driver+root suite green).

## Correctness

No bug introduced by this patch. Specifically checked and found sound:

- `_invoke_leaf_resilient` (`leaves.py:673-755`): the per-attempt flush
  (`_write_attempt_records`, `:742`) happens strictly before `time.sleep(delay)`
  (`:754`), so the "on disk before the next attempt" claim holds even for a run
  killed mid-backoff. The success path's `error_log.unlink` (`:732-737`) only ever
  removes a file the *failure* branch wrote, so a first-attempt success still does
  zero I/O on the error log, as documented.
- `_disown_artifact` (`:770-790`) is called once per attempt for every call site
  that passes `artifact=`, and only for those (the builder passes none, so its
  residue is correctly left untouched at `:1984-1992`/`:3979` region). The fail-closed
  branch (unlink when rename fails) prevents a residue that can't be set aside from
  staying harvestable, matching the stated invariant.
- `_report_exhausted_do_retries` (`leaves.py:1869-1898`) is only reached via
  `getattr(exc, "transient", False)` (`:1864`), and `LeafError.transient` is `True`
  only when `produced is False`; a setup failure (`worktree.ensure` → `WorktreeError`,
  no `.transient` attribute) correctly falls through to `False` and is never
  misreported as a transient/exhausted builder death. Its `"patch.diff" in residue`
  branch (`:1888`) matches `state.state`'s own BUILT test (`state.py:207-211`:
  keyed on `patch.diff`/`CLOSE_MARKER`, not `build-notes.md`), so the BUILT-vs-Check
  claim it prints is true of the real state machine (also asserted end-to-end by
  `test_leaf_resilience.py:657-680` against `state.state(d)`).
- `_memory_log_for(BUILD_ERROR_LOG)` (`:362-372`) derives `"build.memory.jsonl"`,
  identical to the `BUILD_MEMORY_LOG` constant the call site used to pass
  explicitly — dropping the explicit `memory_log=` kwarg at `:1984-1992` is a
  no-op behavior change, not a regression.
- All three harvest sites (`_run_review_sandboxed:2674-2687`,
  `_run_advisory_sandboxed:3006-3018`, plan-advisory `:3308-3319`) apply the
  `artifact=`/harvest-after-`err`-check pattern identically; none can adopt a dead
  attempt's file because the early `return` on `err is not None` happens before the
  `out.exists()` check.

## Reuse / simplification

- `_skip_backoff`/`_REAL_SLEEP` (`template/tests/test_build_error_log.py:34-45` and
  `template/tests/test_leaf_resilience.py:472-482`) are byte-for-byte duplicated
  across the two test files rather than factored into one shared test helper. Minor,
  test-only, no behavioral risk — not worth a round on its own, flagging only because
  the patch is what introduced the duplicate (it existed in neither file before).

No other duplication, needless hot-path work, or simpler-equivalent-available found;
the new helpers (`_write_attempt_records`, `_disown_artifact`, `_has_content`) are each
used at more than one call site or guard a genuinely new invariant, not a copy of
existing logic.

## Scope

Both findings are localized to lines this diff touches; nothing pre-existing outside
the diff's regions is cited.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Maintainer must compare the archived rejected issue-506 iteration by affected path against this patch — merged PRs #140/#286 and current open overlaps were mechanically checked, but the rejected artifact is outside the allowed review inputs, so reuse-versus-rejected-design cannot be settled here.
- [ ] Validation — fitness-to-purpose — Maintainer must decide whether fresh-session retry plus residue instructions is operationally fit for a real long-running vendor failure — the Python leaf stubs exercise the mechanics (`template/tests/test_leaf_resilience.py:134`) but cannot establish recovery quality after an actual mid-response drop.

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
- Iteration delta (if iterating): Rejected on the open findings in this bundle's own Check record, not on the approach: the slice's shape is right, the implementation is not yet correct. Must close before re-submission: 1. Fail-closed artifact ownership (`leaves.py:783`) — the reviewer's C3/T3 FAIL. When the rename AND the fallback unlink both raise, the error is suppressed and control continues, leaving a dead attempt's artifact harvestable — the opposite of the invariant the code's own diagnostic claims. 2. The #369 trap-door regression (`leaves.py:742`) — the per-attempt flush, which is criterion (ii) itself, disarms recovery for a run killed mid-retry. `review_never_ran` is "no artifact AND no error log"; attempt 1's record now exists, so the reviewer is never re-run and the bundle can reach sign-off with NO review of the diff. This violates criterion (vi). Decide which contract yields (an in-flight suffix, or teach the discriminator that a record short of the attempt budget is not "ran and failed"). 3. Signal-death scope leak (`leaves.py:1883-1886`) — a builder SIGKILLed under the #420 memory cap exits -9 with produced=False, so it is classified transient: 3 spawns instead of 1, each repeating whatever exhausted the bound, while stderr asserts it was absorbed infra and build.error.log says otherwise. #510 is out of scope per the brief; this patch must not extend the classifier to it. 4. Exhausted-retry next action (`leaves.py:1888-1894`) — ask `state.state(d)`, do not infer from `patch.diff` existence. Confirmed at sign-off by reading `state.py`: state() is a waterfall, so a bundle holding patch.diff AND check-gates.json returns CHECKED, not BUILT, and the printed advice is false exactly on the bundle its own previous advice creates. (The code-review lens cleared this by reading only the first rung; the adversary is correct.) 5. `_disown_artifact` (`leaves.py:775-777`) — the rename target is inside the temp sandbox that is destroyed on exit, so "stays readable beside it" is false at all three call sites: a real verdict is discarded while the operator is told none was produced. Copy the disowned file into the bundle. 6. The `residue` list is computed and dropped on the floor in the no-patch branch (`leaves.py:1887,1895-1898`) — the operator is told inputs are intact while a half-written build-notes.md (and any brief-named test file) is on disk, inherited by a re-driven Do without the retry note. Also: the C5-prod-path green is vacuous ("patch adds no new test file"). The appended cases were only hand-checked. Make production-path coverage adjudicable next round. Not iterate-plan: the four concerns (retry the builder, per-attempt accountability, residue awareness, operator reporting) were weighed as one outcome and kept in one slice.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
