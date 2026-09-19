# Result — issue 498 / one-live-driver-per-bundle-and-a-truthful-split-hint

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two linked problems.
  (a) **The hint is wrong inside a flow.** `pdca split <id> --accept` always ends with
  `"<parent> marked split; run `pdca flow <child-ids>` to drive the children"`
  (`template/src/pdca_harness/cli.py:843-844`). That was true before #469/#472. Now every CLI
  `pdca flow` shape drives the children of a split accepted during its own run. An id run
  hands a split parent to `_drive_and_act` as an adoption seed (`flow.py:1784-1803`) or adopts
  a mid-run split (`_adopt_split_children`, `flow.py:1119`). A CSV batch sweeps every
  in-flight bundle after its Plan session (`flow.py:1673-1698`). The planner role prompt
  says the same (`template/agents/planner.md.jinja:164-169`). So an operator who follows the
  printed instruction starts a second driver over bundles the first run is about to drive.
  (b) **Nothing stops two drivers from holding the same bundle.** No drive-path code takes any
  ownership of a bundle. The only cross-process claim in the driver is Act's
  (`act.py:125-159`), so the race is reachable by any two `pdca flow` runs over overlapping
  ids, with or without the hint. State is plain files in `results/issue_<id>/`, so two
  interleaved drivers write the same bundle's artifacts with no ordering.
- Success criterion: With the patch, through the CLI entry points (`cli._flow`,
  `cli._split`):
  (i) **A second driver over a bundle a live run holds is refused.** While run A (`pdca flow`
  naming id 7) is mid-drive, run B, a `pdca flow` whose named ids include 7, exits non-zero
  **before it changes any bundle's state**. That includes `flow_ids`' RESOLVED revalidation
  and its Plan pre-pass. It prints a line naming `issue_7` as held by another run. Nothing
  under `results/` changes because of B.
  (ii) **Implicit reach is excluded, not refused.** A CSV batch's in-flight sweep, and split
  adoption, both skip a bundle a different live run holds. Each prints a line naming it, and
  the rest of that run continues.
  (iii) **The claim ends with the run.** After A returns, normally or by raising, a new run
  over 7 proceeds. A run whose process dies (SIGKILL, host crash) leaves nothing that stops
  a later run.
  (iv) **A run never refuses itself.** A's own in-process steps, and every leaf or command
  spawned inside A (including `pdca split --accept` run from A's Plan session), are not
  refused or blocked by A's claim. Bundles A adopts become A's, so the same rules cover them.
  (v) **The hint is truthful.** When `split --accept` runs while a live run will drive that
  parent's children, it does not print the `run pdca flow <child-ids>` instruction. It says
  instead that the running flow will drive them. This covers the parent being in the run's
  drive set on an id run, and the Plan session of a CSV batch run. When no live run will
  drive them (a standalone accept from a shell, or an accept inside a run that is not
  driving that parent), the instruction is printed **byte-identical to today's**.
  (vi) Nothing else changes: a single run with no second driver behaves and prints exactly
  as today, apart from (v)'s line, and the whole `template/tests` suite stays green.
  Shown by the named test going red on the base (B proceeds and drives 7; the in-flow accept
  prints the instruction) and green with the fix.
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it. #481's accept-path change is already merged as PR #561.)
- Scope (one logical fix) / out of scope: One logical fix: make bundle ownership by a live run exclusive for the life of
  the run, and make `split --accept`'s closing instruction depend on whether a live run will
  drive the children. Update the text that says `--accept` always prints the instruction:
  `template/agents/planner.md.jinja:155` and `:182-183`, the planner seed prompt at
  `leaves.py:1119-1120`, and `docs/07-crosscutting.md:340-343`. / out of scope:
  `pdca run`, `pdca signoff`, `pdca publish` and other single-step verbs (note the gap in
  `build-notes.md`; it is not fixed here); the library-only `flow.flow()` (`flow.py:379`, not
  a CLI route, does not adopt, `:401-406`); lane-level locking and worktree locks (`lane.py`,
  `worktree.py`); the adoption algorithm itself (what is adopted, wave levelling, budget);
  the `--ids`/filing branches of `split --accept` other than the final instruction; the
  "already marked split by another run" message (`cli.py:822-831`); `--from-briefs`
  seeding of *missing* bundles in `cli._flow` (`:577-588`); cross-host coordination (one
  host is assumed); Windows behavior beyond not breaking import (see Citations).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

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

Review issue #498: enforce one live CLI flow driver per bundle and make split-accept instructions reflect whether a live flow will drive the children.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable refusal, exclusion, lifetime, self-use and hint outcomes, with explicit single-host and CLI scope; `brief.md:21`, `brief.md:95`. |
| C2 Reproduction (red pre-fix) | PASS | Independent production-only stash reproduced eight behavioral failures in 11 tests, including a competing process modifying the held bundle; `review-red.log:121`, `target/template/tests/test_flow_single_driver.py:267`. |
| C3 Change | FAIL | Exclusivity is lost when a claim cannot be recorded: a second real process returned 0 and changed results while A remained paused; `target/template/src/pdca_harness/drive_claim.py:128`, `review-edge.log:1`. |
| C4 Verification (red→green) | PASS | After restoring production, the same 11 tests all passed; this confirms the asserted regression cases, with the additional failures recorded separately; `review-green.log:3`, `target/template/tests/test_flow_single_driver.py:296`. |
| C5 Causal adequacy | PASS | Run-scoped ownership addresses concurrent writers directly; tests exercise real CLI entry points and competing processes, and no load-time capability workaround was added; `target/template/src/pdca_harness/cli.py:573`, `target/template/tests/test_flow_single_driver.py:296`. |
| T1 Structure | PASS | Claims stay outside bundle state, use the existing OS-lock primitive and release through the run scope; the failure policy is assessed in C3; `target/template/src/pdca_harness/drive_claim.py:123`, `target/template/src/pdca_harness/drive_claim.py:185`, `target/template/.gitignore.jinja:43`. |
| T2 Shape | PASS | Independent docs lint, site rendering/link audit and diff whitespace check passed; frozen docs and host-CI parity logs agree; `review-lint.log:1`, `review-render.log:3`, `gate-logs/host-ci-docs.log:11`. |
| T3 Runtime | FAIL | A delayed child split after its CSV flow ended still promised automatic driving, leaving both children PLANNED; all 1,932 suite tests passed but miss this lifetime case; `target/template/src/pdca_harness/drive_claim.py:249`, `review-ended-sweep.log:8`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive audit must run at publish; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior-art coverage across merged and closed/rejected work — the brief records triage searches, but the synthetic target history cannot corroborate their coverage; `brief.md:139`, `review-prior-art.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether CLI-flow-only, single-host ownership meets operator needs — single-step writers remain outside the guarantee, and the two reproduced exceptions need disposition; `brief.md:95`, `target/docs/07-crosscutting.md:479`. |

Two independently reproduced findings:

1. **[P1] Refuse or skip driving when acquiring ownership fails.** At `target/template/src/pdca_harness/drive_claim.py:128` and `:136`, open failures and non-contention lock failures return the same empty string as successful acquisition. The CLI consequently proceeds into bundle writes. I made `process/.drive-claims` a regular file, paused real flow A inside its builder, and started real flow B over the same issue. B returned 0 and changed `results/` while A was still alive (`review-edge.log:1`). This is a controlled test of the error policy, not an unavailable-tool gate failure. The brief's invariant requires exclusive ownership; reporting an error can preserve that invariant by refusing named work or skipping implicit work. The referenced Act precedent already yields failure when its lock cannot be opened (`target/template/src/pdca_harness/act.py:140`).

2. **[P2] Check live CSV-run ownership before suppressing the resume instruction.** At `target/template/src/pdca_harness/drive_claim.py:249`, equal inherited environment tokens suffice to return true; no live run is checked. I started a real delayed split subprocess during the CSV Plan callback, ended the enclosing flow with `KeyboardInterrupt`, then released that subprocess. Its accept returned 0 and printed “the running `pdca flow` will drive the children” although the flow had ended before its sweep; both children remained PLANNED (`review-ended-sweep.log:1`). Ending the parent scope cannot revoke environment variables already inherited by a child. Require a live run signal for the CSV branch, with the standalone instruction when the run has ended.

Verification and evidence limits:

- The target was readable and consistent with the supplied patch. Production changes were stashed while keeping the regression test, then restored. `git apply --reverse --check ../patch.diff` passed afterward; no source fixes were made.
- Independently ran `PYTHONPATH=src python3 -m unittest tests.test_flow_single_driver` on both trees and `PYTHONPATH=src python3 -m unittest discover -s tests` on the patched tree. The full suite passed 1,932 tests with two skips (`review-suite.log`). Reviewer temporary files stayed within this sandbox.
- Independently ran `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out <sandbox>/review-site`; both passed. The instance-specific C5 scanner was adjudicated from its full frozen log, which shows only a production-package import check (`gate-logs/C5-prod-path.log:10`); the independent behavior tests provide stronger evidence.
- The local root-suite attempt exited 77 because this interpreter cannot import Copier (`review-root.log`). This is a reviewer-host limitation, not a patch failure or an unmet frozen-gate dependency: the frozen log explicitly shows actual render and update cases executing successfully, 24 tests total (`gate-logs/T3-suite.log:38`, `:54`). No vendor CLI, service or substituted lock implementation was needed for the fix's process tests.
- The supplied brief records affected-path merged-history and closed-unmerged checks. The independent affected-path history query returned only the harness's synthetic base commit (`review-prior-art.log:2`), so historical coverage remains a human judgment. The target contains only an unfilled integration template at `target/template/docs/INTEGRATION.md.jinja:49`; no additional populated project-specific human-only rules were available in the bundle.

These verdicts are advisory; deterministic gate results remain unchanged.

### Advisory — adversary

# Adversarial review — issue 498 (one live driver per bundle + a truthful split hint)

The red→green proof holds up. I re-ran `template/tests/test_flow_single_driver.py` against the
patched target: 11/11 green. The frozen C4 red leg (`gate-logs/C4-verify.log`) shows 8 failures
for real reasons: B drove 7 to COMPLETE, the in-flow accept printed the instruction, and adoption
took the held child. None of them are import errors. The 3 tests that pass on the base
(raise-releases, standalone accept, accept for a parent the run is not driving) are
regression pins, and by design they cannot go red there. The production path is exercised
for real: run B and the spawned `split --accept` are real subprocesses, and only the six
leaves are stubbed, as the brief allows. What I could break is below.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1729` vs `:1738`: a CSV batch
  claims every swept bundle (`_claim_swept`) *before* `waves.partition_schedulable` holds the
  unschedulable ones. The held ones keep their claim for the whole batch even though the run
  never drives them. I reproduced it (my scratch probe: stub leaves, batch paused in 7's
  build, 8's brief has `Depends on: 999`). The batch prints `issue_8 held this run —
  unresolved dependency (999); left in-flight (resolve it, then re-run)`. The operator then
  fixes 8's brief and runs `pdca flow 8` from another shell, which gets `rc 1 — issue_8 is held
  by another live flow run … refusing to start a second driver`. The batch ends with 8 still
  PLANNED. The adoption path releases its claim in this exact situation (`flow.py:1257-1296`,
  `dropped` → `claims.release`, and its docstring says "a claim lasts as long as the run DRIVES
  the bundle"), so the two implicit-reach paths disagree. A parallel CSV batch will also report
  8 as "NOT driven: held by another live `flow` run" when no run is driving it. Fix: release
  every name in `held` right after `partition_schedulable` (and after the "nothing
  schedulable" early return). Also add a test: nothing in the new file covers any
  `release()` path, so neither this case nor adoption's `dropped` logic is pinned.

- NEEDS-HUMAN — `flow.py:1712-1713`: a CSV batch's Plan session runs *before* the run claims
  anything. That session is allowed to rewrite existing briefs (`leaves.py:1160-1161`, "briefed
  or REWROTE"), and `pdca split --accept` takes no claim. So run B (`pdca flow --from-csv`) can
  still rewrite `brief.md` of, or mark as split, a bundle that live run A is mid-drive on. The
  brief's (ii) asks only for the *sweep* to exclude, so the patch meets the letter. But the new
  docs line `docs/07-crosscutting.md:469` ("Those processes never share a *bundle*") and the
  brief's invariant ("every CLI drive path") claim more than the code enforces. A human should
  decide: soften the docs to name the Plan-session / `split` gap, or widen scope. This needs
  design work (claims for a model-driven session that can touch any bundle), not an iteration.

- NEEDS-HUMAN — `template/src/pdca_harness/drive_claim.py:246-248`: `drives_children` returns
  False whenever `PDCA_FLOW_RUN` is unset. It never checks whether the parent's claim is live.
  Concrete case: run A = `pdca flow 500` sits in its Plan pre-pass. The operator, reading the
  proposal "with the human" as the planner prompt describes, runs `pdca split 500 --accept
  --ids 601,602` from a second terminal. That accept prints `run pdca flow 601 602`, yet A then
  adopts both through its seed path (`flow.py:1851-1864`). Nothing unsafe happens, because the
  claims serialize: whoever claims first drives, and A reports the other as "NOT adopted".
  But the hint is untrue in a case the first sentence of the brief's (v) covers ("while a
  live run will drive that parent's children"). The second sentence of (v) calls every shell
  accept "no live run", so the brief contradicts itself here, and a human must pick which
  sentence wins. If the first wins, checking the parent's live lock regardless of token
  (`_held_now`) would make the line true.

- Not flagged for a decision, context only: `docs/07-crosscutting.md:471-472` says the claim is
  dropped "however it ends (… `SIGKILL`)". That is true of the lock. But headless leaves run in
  their own session (`progress.py:178-182`), so a SIGKILLed driver's builder or reviewer can
  outlive it and keep writing the bundle after a new run over 7 has already claimed and started
  it. The brief asked for SIGKILL to free the claim, and the base had no protection at all, so
  this is not a regression.

- Not flagged for a decision, context only (Windows, out of scope per the brief):
  `drive_claim.py:143-145` writes the stamp into byte 0, which is the byte
  `act._lock_exclusive` locks on Windows (`act.py:38-39`, `LK_NBLCK, 1` at offset 0). Windows
  byte locks block reads from other handles, so `_stamp` (`drive_claim.py:93`) reads `("", "")`
  for any held file. `drives_children` is then always False on Windows, and refusal lines lose
  the pid. The fallback is today's instruction, so nothing regresses.

Refutations I tried that did not land:
- **Per-process lock:** the Unix `_lock_exclusive` is `flock`, which belongs to the open file
  handle, not the process. So a second handle in the same process is refused, and the
  in-process `_held_now` check in `drives_children` works.
- **Lock leaking to children or across the re-exec:** Python opens files non-inheritable by
  default, and the claim is taken after the keep-awake re-exec (`cli.py:433` runs before
  `cli.py:573`).
- **Self-refusal from a lane race on `Run._held`:** adoption runs on the main thread after each
  wave (`flow.py:1586`).
- **A swept dependent driven early because its prerequisite was excluded:** it gets held
  instead (`waves.py:269-274`).
- **Id spelling mismatch between claim and drive:** both go through `cfg.bundle(iid)`.
- **The in-flow hint promising a child the sweep then holds:** `split` refuses a child whose
  `Depends on` names a non-sibling id (I probed it), so this cannot be reached.

I found no unwarranted claim in `check-gates.json`. C4 is red→green for real reasons, C5 is
true (the new test imports `pdca_harness`), T3 is 1932 tests OK, and T4 is honestly deferred.

### Advisory — code-review

# Advisory code review — issue #498

Lens: correctness bugs this patch introduces, plus reuse/simplification/efficiency. Grounded
on the patched tree at `$PDCA_TARGET` (`template/src/pdca_harness/{cli,flow,leaves,drive_claim}.py`,
`template/tests/test_flow_single_driver.py`).

## Correctness

- The claim/lock half of `drive_claim.py` is solid: `Run.take()` opens the claim file `"a+"`
  (never `"w"`, so a contended open cannot truncate another run's stamp — `drive_claim.py:127`),
  takes a non-blocking `flock`/`LK_NBLCK` reusing `act._lock_exclusive`/`_unlock`
  (`drive_claim.py:49,132`), and is released only by the OS when the holding handle closes —
  correct for return, raise, and `SIGKILL`. Traced every call site (`cli.py:572-583` named-id
  claim before any write, `flow.py:1063-1068` child adoption, `flow.py:1750-1763`
  `_claim_swept`, `flow.py:1294-1296` release of dropped/retracted children) and the
  claim/release bookkeeping is consistent: a child dropped by a failed or partial reschedule
  is released exactly once (`flow.py:1257-1296`), and a bundle already in `known`/`batch_names`
  is refused via the owner check before ever reaching `claims.take()`, so no redundant
  claim-then-release churn.

- NEEDS-HUMAN [impl] — `drive_claim.py:57-61,179-208,246-252`: the "truthful hint" state
  (`RUN_ENV`, `SWEEP_ENV`) is process-global `os.environ`, not thread-scoped, while the
  module's own docstring (`drive_claim.py:18-22`) explicitly describes "two runs in one
  process — a test driving two flows on two threads" as a scenario the mechanism must not
  tell apart from two processes. That claim is true for the *lock* (per-open-handle
  `flock`, thread- and process-safe) but not for `drives_children()`'s inputs: if two
  distinct `drive_claim.run()` scopes were ever active concurrently on two threads of one
  process, each entry/exit does `prev = os.environ.get(RUN_ENV); os.environ[RUN_ENV] = token`
  and restores `prev` on exit (`:180-190`) — a second scope's exit can stomp the first
  scope's still-live token, or a leaf spawned from one run can read the other run's token.
  Worst case this only corrupts the *hint* (wrongly suppresses or wrongly prints the
  `pdca flow <child-ids>` instruction), never the actual exclusion, and it isn't reachable
  through the shipped CLI (one `cli._flow` call per process; lane fan-out inside one run is
  threads sharing one token, not two runs) or exercised by any test in this patch — every
  test uses at most one thread-based run at a time. Narrow and not exercised, but it is a
  real gap between what the docstring asserts and what the env-var-based hint actually
  guarantees; worth a follow-up (e.g. a `contextvars.ContextVar` as the primary token, with
  the environment variable kept only for subprocess inheritance) or a narrowed docstring
  claim.

- Test coverage for the SIGKILL half of (iii) (`test_flow_single_driver.py`, the
  `test_a_killed_run_holds_nothing_and_blocks_nothing` case) is real and runs on this gate
  host (`hasattr(signal, "SIGKILL")` is true on Linux), and `C4-verify.log` confirms 11/11
  green with the fix and 8/11 red without it, driven through `cli._flow`/`cli._split` as the
  brief requires (not a copy — `C5-prod-path.log` confirms the new test imports
  `pdca_harness`). No issue found in the test's mechanics: the "ready" handshake file is
  written only after the holder process has already taken its claim (claiming happens before
  Do runs), so there's no window where the competing run could win a race the test doesn't
  intend to test.

## Reuse / simplification / efficiency

- No duplicated locking logic: `drive_claim.py` reuses `act._lock_exclusive`/`_unlock`
  directly (`drive_claim.py:49`) rather than re-implementing the Windows/Unix branch, exactly
  as the brief's composition cue asks. The per-bundle keying (`_key`, resolved path + digest)
  and run-lifetime bookkeeping are new because nothing in the codebase already does per-bundle
  ownership — not a case of skipped reuse.
- The claiming loops in `cli._flow_claimed` (whole-run refusal) and `flow._claim_swept`
  (per-bundle exclusion) share the same `claims.take(d)` / `why` shape but differ in exit
  behavior (return-whole vs. continue-and-exclude) and in message wording tied to their own
  context; collapsing them into one helper would save a few lines at the cost of the
  context-specific messages the brief's success criteria (i) vs (ii) both call for
  separately. Not worth flagging as duplication.
- No hot-path concern: every claim/lock check is a non-blocking `flock` attempt on a tiny
  file, at most once per bundle per run; no busy-waiting in production code (the busy-wait
  loops — `_pausing_build`'s `time.sleep(0.02)` polling — are test-only, bounded by `_WAIT`).

## Summary

Clean on the whole. One narrow, unexercised gap in the new module's thread-safety story for
the advisory hint (not the exclusion itself) — flagged above as an implementation follow-up,
not a blocker.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm affected-path prior-art coverage across merged and closed/rejected work — the brief records triage searches, but the synthetic target history cannot corroborate their coverage; `brief.md:139`, `review-prior-art.log:1`.
- [ ] Validation — fitness-to-purpose — Decide whether CLI-flow-only, single-host ownership meets operator needs — single-step writers remain outside the guarantee, and the two reproduced exceptions need disposition; `brief.md:95`, `target/docs/07-crosscutting.md:479`.
- [ ] `template/src/pdca_harness/flow.py:1729` vs `:1738`: a CSV batch
- [ ] `flow.py:1712-1713`: a CSV batch's Plan session runs *before* the run claims
- [ ] `template/src/pdca_harness/drive_claim.py:246-248`: `drives_children` returns
- [ ] `drive_claim.py:57-61,179-208,246-252`: the "truthful hint" state

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
- Iteration delta (if iterating): Core claim mechanism is sound (OS lock, released on return/raise/SIGKILL, taken after the keep-awake re-exec). Rebuild to close these gaps from the Check review: 1. Fail closed when a claim cannot be recorded. Run.take() (drive_claim.py:128, :136) returns "" on an open failure or a non-contention lock failure, so the run proceeds without exclusivity (reviewer reproduced a second run writing a held bundle). Refuse named ids (cli._flow, exit non-zero, before any write) and skip implicit ones (CSV sweep, adoption), each with a report line — as act_session does when its lock cannot be opened (act.py:140). 2. Release swept claims the batch does not drive. flow.py ~:1729 claims every swept bundle before waves.partition_schedulable holds the unschedulable ones (~:1738); release every held name right after the partition (and on the "nothing schedulable" early return), matching adoption's dropped -> claims.release. Add tests for release paths (this case and adoption's dropped children) — none exist today. 3. The CSV-sweep hint needs a live run. drives_children (drive_claim.py:249) trusts an inherited SWEEP_ENV token; also check that the run holding that token is still live, and print today's instruction when it has ended. 4. Soften docs/07-crosscutting.md (~:469 "Those processes never share a bundle") to name the known gap: a CSV batch's Plan session runs before any claim and can rewrite briefs / split a bundle another run holds. Widening claims to the Plan session is out of scope (separate issue). 5. Criterion (v): the first sentence wins — when a live run will drive the parent's children, the hint must say so even if the accept runs from another shell. Check the parent's live claim regardless of RUN_ENV (the _held_now path); print today's instruction only when no live run holds the parent. 6. Narrow the drive_claim.py module docstring (:18-22): the two-runs-on-two-threads guarantee holds for the lock, not for the env-var hint state.
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
