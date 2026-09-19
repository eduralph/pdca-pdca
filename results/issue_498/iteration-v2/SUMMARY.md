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

Review issue #498: prevent concurrent CLI flows from driving the same bundle and make split-accept instructions reflect whether a live flow will drive the children.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The refusal, implicit exclusion, lifetime, and hint requirements are falsifiable; the accepted scope explicitly leaves independent Plan writes unfenced (brief.md:17; brief.md:163; target/docs/07-crosscutting.md:484). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production changes produced 17 assertion failures in 22 tests, including a second process driving a held bundle and the incorrect in-flow instruction (target/template/tests/test_flow_single_driver.py:394; review-red.log). |
| C3 Change | FAIL | A split accepted after its parent's adoption read but before the wave is marked passed still promises automatic driving, leaving both children PLANNED; criterion (v) remains violated (target/template/src/pdca_harness/flow.py:1619; target/template/src/pdca_harness/drive_claim.py:328; review-hint-race.log:8). |
| C4 Verification (red→green) | PASS | The asserted regression suite independently changed from 17 failures to 22 passing tests after restoring the patch; this verifies the tested cases, but misses the additional C3 interleaving (review-green.log:3; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Exclusive OS locks address concurrent driving itself, fail closed, and release on scope exit; the real-process regressions exercise that cause. No capability probe masking a load-time side effect was added (target/template/src/pdca_harness/drive_claim.py:183; target/template/src/pdca_harness/drive_claim.py:245; target/template/tests/test_flow_single_driver.py:394). |
| T1 Structure | PASS | Ownership has a run-scoped lifecycle and stays outside bundle state; existing lock primitives are reused, with claims threaded through all CLI drive routes (target/template/src/pdca_harness/cli.py:574; target/template/src/pdca_harness/flow.py:1271; target/template/src/pdca_harness/flow.py:1766). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page site rendering/internal-link audit, and diff whitespace checks passed; frozen host-parity evidence agrees (target/.github/workflows/docs-check.yml:35; gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver suite: 1,943 tests, two skips, success. Frozen root-suite evidence shows 24 passing tests including render/update cases; local root rerun lacked importable Copier, a host limitation rather than evidence of a defect (review-suite.log:1656; review-root.log:6; gate-logs/T3-suite.log:38). |
| T4 Contribution | N/A | Contribution artifacts are deliberately absent at Check; the substantive contribution audit is deferred to its mandatory publish rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged/closed/rejected-work comparison remains sufficient — the brief records that search, but this target contains only one synthetic base commit and no remote, so its semantic prior-art conclusion cannot be independently settled here (brief.md:139; target/template/docs/INTEGRATION.md.jinja:83). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether protection limited to CLI driving meets the operational need despite unfenced Plan/single-step writes and the reproduced false assurance in C3 — passing regressions alone do not establish safe operator guidance (target/docs/07-crosscutting.md:484; target/template/src/pdca_harness/cli.py:886; review-hint-race.log:8). |

**Finding — P2: the adoption hint stays affirmative after the parent's last adoption read.**

`_adopt_split_children` reads each parent at `target/template/src/pdca_harness/flow.py:1268`, but `_past_adoption` only stamps the wave after the entire adoption pass returns (`target/template/src/pdca_harness/flow.py:1619`). During that interval, a separate shell can accept a split of a parent already examined. Its claim remains locked and unmarked, so `drives_children` returns true (`target/template/src/pdca_harness/drive_claim.py:328`). The caller tells the operator not to start another flow, although this run will never revisit that parent for adoption. Processing other parents or rescheduling their children can extend this interval.

I reproduced this with the patch applied: a real `cli._flow` reaches the adoption pass after an unanswered sign-off; a wrapper calls the real `_adoptable`, then runs a real split-accept subprocess before returning its already-read result. The split succeeds and prints “will drive the children (601 602) — do not start another flow for them”; the flow subsequently returns with both children `PLANNED`. The wrapper controls scheduling only: it does not replace the claim, hint, split, or adoption decision. This is an in-scope cross-shell hint failure, not a request to fence all Plan writes.

Reproduce from this review directory:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 review-hint-race.py
```

The runnable probe is `review-hint-race.py`; observed output is `review-hint-race.log:8` and `review-hint-race.log:10`. Coordinate the per-parent adoption boundary with the hint decision so a split accepted after that parent's last read cannot receive an automatic-driving promise; add this interleaving to the regression coverage.

Independent verification used the disposable target only. Production changes were stashed while the new tests remained, then restored successfully; reverse-apply validation confirms the supplied patch is still applied. There is no target-state caveat. The production-import scanner passed independently. The frozen C4 log reports the same 17-failure/22-pass result; the C5, T2, host-parity, T3, and deferred T4 logs were also inspected. The local missing-Copier result does not leave the dependency globally undischarged: the frozen T3 log explicitly records execution and success of those render/update tests.

The affected-path history investigation returned only `bdc913c pre-fix base 70ea12b0e60f6cea4c604a0c2777240760ba11f3`; `git remote -v` returned nothing. The brief documents path-based merged history and closed-unmerged PR checks, but supplies no independently inspectable closed/rejected-work record. The available INTEGRATION template leaves its project-specific human-only list as TODO (`target/template/docs/INTEGRATION.md.jinja:80`). No additional project-specific items can be inferred from that scaffold.

This review is advisory; it does not gate acceptance.

### Advisory — adversary

# Adversarial review — issue 498 (one live driver per bundle + a truthful split hint)

Advisory only. Inputs: patch.diff, brief.md, check-gates.json, gate-logs/. Every path:line
is on the patched target at `$PDCA_TARGET` (`template/` prefix omitted for `src/` and `tests/`).

## Evidence: re-run, holds up

I re-ran C4 in a scratch copy (Python 3.14.4). With the fix, all 22 tests in
`tests/test_flow_single_driver.py` pass. With the production hunks reverted and
`drive_claim.py` removed, the same 17 tests fail as in `gate-logs/C4-verify.log`. They fail
for real reasons: on the base, B drives 7 and the in-flow accept prints `run pdca flow …`.
Nothing fails on import. The tests go through `cli._flow` / `cli._split`, and the competing
driver is a real second process, so the C5 claim holds.

## Refutation attempts that landed

- NEEDS-HUMAN — **The hint promises children the run never drives.**
  `src/pdca_harness/cli.py:881-887` prints "the running `pdca flow` will drive the
  children … — do not start another flow for them" whenever `drives_children`
  (`src/pdca_harness/drive_claim.py:328`) sees a live claim on the parent that isn't yet
  stamped `passed`. But adoption only happens if the parent's wave actually runs it
  (`src/pdca_harness/flow.py:642-645`) and the parent ends that wave terminal on a split
  (`flow.py:902`, `_is_split_parent`). Probe case: `pdca flow 7 8`. The Plan pre-pass
  briefs 8 with `Depends on: 7` and accepts a split of 8 into 801/802, and 7's sign-off is
  never answered. The accept prints the "will drive … do not start another flow" line. The
  run exits 1 with 801/802 still PLANNED, and no later line names them; the only related
  line is `issue_8 skipped — prerequisite(s) not ready (7)`. A second variant: `pdca flow
  500`, where 500's own sign-off is never answered after the in-session accept. That run
  exits 0 with 601/602 PLANNED, and only its "resume with `pdca flow 500`" line leads back
  to them. Criterion (v) says the instruction should be printed when no live run will
  drive the children, and here none does. No check made at accept time can know this, and
  the brief set the wording. So a human needs to choose: soften the text (for example
  "will adopt them if issue_8 closes as split in this run"), or add an end-of-run line that
  names split children the run was expected to adopt but didn't.

- NEEDS-HUMAN [impl] — **Most of the new release and "passed" paths are untested.**
  I deleted each of these lines in turn: `src/pdca_harness/flow.py:1900-1901` (release a
  terminal named id or split seed), `:1291` (`dropped = children` when the reschedule
  fails), `:1314` (release children retracted by a later reschedule), `:1562` (mark a
  wave with no runnable bundles as passed), and `:1705` (mark everything passed before Act).
  After every deletion, all 63 tests in `test_flow_single_driver`, `test_flow_adopt_split`
  and `test_flow_adopt_recovery` still pass. Only deleting the no-brief skip release made a
  test fail. Carry-forward item 2 asked for tests on the release paths, including
  adoption's dropped children, but only the `children not in wave_of` branch is covered
  (`tests/test_flow_single_driver.py:634`). What goes unnoticed: with `:1314` gone, a child
  the run retracts with "adopted earlier this run, now held" stays claimed, so a
  `pdca flow <child>` from another shell is refused for the rest of the run. With `:1562` or
  `:1705` gone, an accept on a parent the run will never adopt from says "will drive".

- NEEDS-HUMAN — **The run prints a resume command and then refuses it.** Probe case:
  `pdca flow 7 8` with 8 `Conflicts with: 7`, and 7's sign-off never answered. After 7's
  wave, run A prints ``issue_7 [AWAITING_SIGNOFF] — resume with `pdca flow 7` ``
  (`src/pdca_harness/flow.py:777`) and moves on to 8. Running `pdca flow 7` while A is
  inside 8's build exits 1 with "issue_7 is held by another live `flow` run". The patch's
  own rule says the opposite (`src/pdca_harness/drive_claim.py:15-19`: "the resume command
  it prints for that bundle must not be refused by the run that printed it"), while the new
  test pins the refusal (`tests/test_flow_single_driver.py:684-712`). Keeping the claim is
  defensible, since A still sweeps 7's footprint at `flow.py:1706` and runs Act. It fails
  safe: there is no second driver, and the refusal message is clear. A human should pick
  one: keep the claim and make the resume line say "once this run ends", or release the
  claim and accept that the end-of-run sweep can hit a bundle another run is now driving.

- NEEDS-HUMAN [impl] — **A hint probe can cause a false refusal.** Low priority.
  `_held_now` (`src/pdca_harness/drive_claim.py:145-162`) briefly takes the real exclusive
  lock when nobody holds the claim. A `pdca flow 7` whose `take()` lands in that moment
  (`drive_claim.py:197-206`) does not retry. It is refused as "held by another live `flow`
  run (pid <old pid left in the file>)" even though no run holds 7. This needs
  `split --accept` on 7 and a `flow` start over 7 to land within microseconds of each
  other. `_hold_new` already retries for exactly this reason (`drive_claim.py:266-274`);
  `take()` should retry the same way.

## Attempted, could not refute

- **Refusal before any write.** Named ids are claimed at `cli.py:598-611`, before
  `--from-briefs`, the RESOLVED revalidation and the Plan pre-pass. `main` writes nothing
  before `_flow` (`cli.py:432-455`).
- **The re-exec can't lose the claim.** `os.execvpe` (`cli.py:148`) runs before `_flow`
  takes any claim.
- **SIGKILL leaves nothing behind.** The claim is an flock on a handle that is not passed to
  child processes (Python's default), and the package has no `fork` or `multiprocessing`.
  The SIGKILL test fails on the base and passes with the fix.
- **A run never refuses itself.** A `pdca split --accept` spawned by the run only probes and
  never waits on the lock. No agent prompt tells a leaf to run `pdca flow`; the only
  mention is `agents/signoff.md.jinja:93`, which is descriptive.
- **Aliases and lanes.** A symlinked alias of a bundle maps to the same claim (the name is
  a digest of the resolved path, `drive_claim.py:84-90`). All lanes use one `process_dir`
  (`config.py:781`), so they share one claims directory.
- **Sweep-mark lifetime.** The mark is a live lock and is removed when the batch raises
  (`drive_claim.py:282-305`). An accept after the batch has ended prints the old
  instruction, byte-identical.

### Advisory — code-review

# Advisory code review — issue #498

Second-lens pass on the patch: bugs the patch itself introduces, plus reuse/simplification
opportunities. Grounded on the patched target at `$PDCA_TARGET` (`template/src/pdca_harness/
drive_claim.py`, `flow.py`, `cli.py`, `leaves.py`, `docs/07-crosscutting.md`,
`template/tests/test_flow_single_driver.py`).

I did not find a blocking correctness bug. Two things worth a note, both minor:

- `template/src/pdca_harness/drive_claim.py:308-332` (`drives_children`) has a narrow
  TOCTOU (time-of-check/time-of-use — a gap between reading state and acting on it that
  another process can slip into) window: it calls `_held_now(claim)` and then, separately,
  `_stamp_of(claim)` to check for the `passed` marker. Between those two reads, the holding
  run could call `Run.passed()` (`:211-221`, invoked from `flow.py:1619`,
  `flow._past_adoption`) and rewrite the file. If that lands in the gap, `drives_children`
  can answer "yes, a live run will drive them" for a parent whose adoption splice for that
  wave has, in fact, just closed — so `cli._split` prints the truthful-sounding "the running
  flow will drive the children" line for children that will actually sit un-adopted. The
  window is two adjacent statements with no I/O between them (`flow.py:1617-1619`), so it's
  sub-millisecond and not what the brief's own repro windows (a paused builder, a paused Plan
  session) exercise or could reasonably be asked to close without a much bigger design
  change (holding a lock across the whole adoption decision). Not asking for a fix — noting
  it so it's a known, accepted gap in criterion (v)'s truthfulness rather than a silent one.

- `template/src/pdca_harness/drive_claim.py:39` — a claim `.lock` file is deliberately never
  deleted ("unlinking a lock file another process may already have open is how two holders
  of 'the same' lock happen," `:39`), so `process/.drive-claims/` accumulates one file per
  bundle ever driven, for the life of the checkout. Each file is a few bytes, and this
  mirrors the same trade-off `act.py`'s existing session lock already makes, so it isn't new
  risk this patch introduces — just flagging that it's unbounded growth, in case a future Act
  pass ever wants to sweep it (the `.sweep` mark files, by contrast, are unlinked on the
  normal exit path, `:301-305`; a SIGKILL mid-batch leaves a stray one, harmless since
  `_held_now` never finds it locked).

Everything else checks out under this lens:

- The claim/lock mechanism correctly reuses `act._lock_exclusive` / `act._unlock`
  (`act.py:36-62`) rather than re-implementing cross-platform advisory locking — good reuse,
  matches the brief's citation cue.
- Release bookkeeping in `flow.py` (`_adopt_split_children`'s `dropped` list at
  `:1285-1324`, `flow_batch`'s held-release loop at `:792-797`, `flow_ids`'s two
  `claims.release(d)` sites at `:1891` and `:1901`) is idempotent (`Run.release`,
  `drive_claim.py:232-237`, a plain `dict.pop(..., None)`) and I traced every path that
  claims a bundle back to a release or a hold-to-end-of-run — no leaked claim on any branch,
  including exception/raise paths (the `with drive_claim.run(cfg) as claims:` scope in
  `cli.py:573` unconditionally closes in `finally`, `drive_claim.py:452-455`).
- The previous iteration's rejected env-var (`SWEEP_ENV`/`RUN_ENV`) hint mechanism is fully
  gone (`grep` for it in `template/src` turns up nothing) — replaced with live-lock probing
  (`_held_now`, `drives_children`), which is the more defensible design and closes the
  carry-forward's item 3/5/6 together rather than patching around them.
- The new test file's concurrency shape matches the brief's falsifiability requirement: run
  B is a real subprocess (`_spawn`, `test_flow_single_driver.py:1191-1213`), not a same-
  process thread standing in for one, so an in-process-only claim would not pass these tests
  for the wrong reason.

If this needs to be pinned down as one line: clean patch, no NEEDS-HUMAN items from this
lens — the two notes above are observations, not blockers.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the affected-path merged/closed/rejected-work comparison remains sufficient — the brief records that search, but this target contains only one synthetic base commit and no remote, so its semantic prior-art conclusion cannot be independently settled here (brief.md:139; target/template/docs/INTEGRATION.md.jinja:83).
- [ ] Validation — fitness-to-purpose — Decide whether protection limited to CLI driving meets the operational need despite unfenced Plan/single-step writes and the reproduced false assurance in C3 — passing regressions alone do not establish safe operator guidance (target/docs/07-crosscutting.md:484; target/template/src/pdca_harness/cli.py:886; review-hint-race.log:8).
- [ ] **The hint promises children the run never drives.**
- [ ] **Most of the new release and "passed" paths are untested.**
- [ ] **The run prints a resume command and then refuses it.** Probe case:
- [ ] **A hint probe can cause a false refusal.** Low priority.

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
- Iteration delta (if iterating): The claim/lock half is sound (refused before any write, released on return/raise/SIGKILL, a run never refuses itself) — keep it. The split-hint half has failed two rounds because criterion (v) asks for something no check at accept time can know: whether this run will actually reach the split parent's children (its sign-off may go unanswered, it may sit behind an unready dependency, or its adoption read may already be past). Re-plan criterion (v) so it is decidable: 1. Make the in-flow hint conditional and honest, e.g. "the running `pdca flow` will adopt the children (…) if issue_N closes as split in this run", instead of an unconditional "will drive them — do not start another flow". 2. Add an end-of-run line naming split children the run was expected to adopt but did not, with the command to drive them. 3. Consider splitting the hint into its own issue so the drive-claim lock can ship on its own (pdca-pdca split <id> there, if the planner judges it two outcomes). Carry into the next brief too: 4. Tests for the release/"passed" paths the adversary showed are unpinned (flow.py:1900-1901, :1291, :1314, :1562, :1705 — each deletable with all 63 tests green). 5. The run prints "resume with `pdca flow 7`" and then refuses it while it still holds 7: either keep the claim and say "once this run ends", or release it — pick one and make the line and drive_claim.py:15-19 agree. 6. Run.take() should retry on the transient _held_now probe collision the way _hold_new already does (drive_claim.py:197-206 vs :266-274), so no false "held by another run" refusal.
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
