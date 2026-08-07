# Build notes — issue 369 / checked-trapdoor-lost-review

Target: eduralph/pdca-harness, built in `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt-l0`,
HEAD 881f988 on the resolved stack base `pdca-integration/main`). All `path:line`
citations below are against that tree; "pre-fix" lines are the tree before the patch.

## The defect, verified on the target

- `check-gates.json` *is* the CHECKED marker: `state.py:213-216` pre-fix (patch present →
  no `check-gates.json` ⇒ BUILT; present + no `SUMMARY.md` ⇒ CHECKED). (The brief's
  `state.py:171-176` cite has drifted a few lines on the current base; same code.)
- The BUILT branch runs gates → reviewer → advisory leaves as one indivisible step:
  `driver.py:104-115` pre-fix. The CHECKED dispatch was `assemble` alone:
  `driver.py:116-118` pre-fix.
- The failed-leaf discriminator (#138) is the error log: `leaves.py:306` clears it at the
  start of a run, `leaves.py:312` "success — leave no error log behind", `leaves.py:324`
  writes it after retries exhaust; the reviewer's is `check-review.error.log`
  (`leaves.py:1843` pre-fix), each advisory's `check-advisory-<id>.error.log`
  (`leaves.py:2132` pre-fix). So **artifact absent AND error log absent ⇔ the leaf never
  ran** — the beat died in the window — while a ran-and-failed leaf leaves the log (and a
  §6 placeholder via `_review_unavailable`, `leaves.py:1891` pre-fix).
- `_missing_review_text()` (`assemble.py:394-401` pre-fix, consumed at `:184-185` and
  `:258-262`) had one wording for both cases — the sharp edge the brief names.

## The change (Option A: resume the missing leaf, preserve the paid gates)

1. **`state.py:61-67`** — `REVIEW_ERROR_LOG = "check-review.error.log"`, named beside
   `CLOSE_MARKER`/`SESSION_CARRY` so the writer (`leaves`), the resume check (`driver`)
   and the §6 wording (`assemble`) share one spelling. (`state` imports neither module —
   no cycle; it is already the artifact-naming module by convention, `state.py:44-65`.)
2. **`driver.py:116-129`** — the CHECKED dispatch now calls
   `_resume_interrupted_check(d, cfg, close)` (`driver.py:169-199`) before
   `assemble.assemble_summary`. Three shapes, matching the three BUILT branches:
   - close-class bundle (`close` truthy): the reviewer stand-in is the deterministic
     `_close_review_note` — if the note is missing it is rewritten; **never** a model
     reviewer (a close bundle has no patch to review, `driver.py:220-243`).
   - dependency-halted bundle (`dependency_halt.load(d)` with `halted: true` — the record
     `record()` writes *before* the N/A gates, `driver.py:86-87`): the deterministic
     `blocked_review_note` is rewritten from `dependency_halt.recorded_verdicts(d)` (new,
     `dependency_halt.py:217-225` — a tolerant reconstruction of the recorded rows).
   - normal bundle: `leaves.review_never_ran(d)` (new, `leaves.py:1496-1507`) → rerun
     `leaves.run_review`; then `leaves.run_advisory_leaves(d, cfg, only_missing=True)`.
3. **`leaves.py:2110-2135`** — `run_advisory_leaves` gains `only_missing` (the
   CHECKED-resume mode): a spec whose artifact **or** error log exists is skipped. The
   `_select_advisory` policy (#200) is re-applied **first** — under `vendor-complement`
   exactly one of the pool runs, so an unselected leaf's absent artifact is legitimate,
   not "missing"; filtering the pool by absence before selecting would promote an
   excluded leaf on every uninterrupted advance (violating criterion (d)). A new
   `advisory_error_log()` helper (`leaves.py:2018-2022`) keeps the writer
   (`leaves.py:2152`) and the discriminator on one spelling.
4. **`assemble.py:394-421`** — `_missing_review_text(d)` splits on
   `state.REVIEW_ERROR_LOG`: "the reviewer **RAN AND FAILED** (see
   `check-review.error.log` …)" vs "the reviewer **NEVER RAN** (the Check beat was
   interrupted before it), it did not run-and-fail". Both wordings keep the phrase
   "no check-review.md was produced" (the pre-existing
   `test_assemble_survives_missing_review`, `template/tests/test_driver_slice.py:315`,
   asserts on it). Kept even though `advance` now recovers first: `assemble_summary` is
   also called directly (regate paths, API), and it is the record's honest fallback.

## Success criteria → where each is proven (`template/tests/test_check_resume.py`)

- (a) never-ran reviewer/advisory recovered before assemble, gates preserved
  byte-for-byte — `NeverRanReviewerIsRecovered` (both tests assert the gate JSON is
  unchanged and SUMMARY consumed the *real* review).
- (b) ran-and-failed NOT re-run — `RanAndFailedIsNotRerun` (reviewer and advisory; the
  fixture is the error log the real failure path writes).
- (c) §6 wording split — `Section6DistinguishesSkippedFromFailed` (asserted via direct
  `assemble_summary`, since that wording must hold on any path that still reaches
  assemble with the review absent).
- (d) uninterrupted cycle untouched — `UninterruptedCycleIsUntouched`: sentinel artifacts
  survive `advance` byte-identical, and the vendor-complement test pins that an
  unselected leaf is never promoted by resume. One honestly-noted corner: under
  vendor-complement with **no** complement configured, resume re-derives the
  decorrelation note (unlink + rewrite inside `_select_advisory`, `leaves.py:2088`) —
  the content is byte-identical (same chosen spec, same reason strings), only the mtime
  moves; avoiding even that would mean duplicating the selection logic outside
  `_select_advisory`, a second implementation of #200 that could drift.
- The close / dependency-halt note recovery (`DeterministicStandInNotesAreRecovered`) is
  not named by the criteria but is *forced* by them: without branching on those paths,
  resume would run a **model reviewer** over a bundle both paths deliberately keep away
  from one (no patch / declared-unverifiable patch) — and the branch's rewrite of the
  deterministic note is 3 lines each, restoring the brief's invariant uniformly.

## Alternatives ruled out (with cost)

- **Option B — move the marker / re-run gates**: rejected in the issue and out of scope
  per the brief ("the expensive half"). Concretely: the observed incident followed the
  #368 19-hour gate hang; hand-deleting `check-gates.json` re-pays the entire gate run
  to recover a leaf that costs minutes.
- **A new state between gates and review** (e.g. GATED, derived from a new marker):
  `grep -l 'state.CHECKED'` hits 5 src modules + 9 test files, and every state consumer
  (`state.HALTED`, `queue`, `flow`, `regate`, docs 03's state table) would need the new
  name; the marker file itself would need archiving rules (`DOWNSTREAM_OF_BRIEF`). That
  is a ~15-file change to express what two existing artifacts already encode — the #138
  error log plus the artifact make "never ran" derivable with zero new state, in ~46
  driver lines + ~30 leaves lines.
- **Recovering inside `assemble_summary`**: assemble is "pure code, no model"
  (`assemble.py:1-7`); invoking a model leaf from it breaks that doctrine and every
  direct assemble caller would silently start spawning reviewers.
- **Naive per-leaf absence recovery (no selection re-apply)**: cheaper to write (skip the
  `_select_advisory` pass) but wrong — under vendor-complement it re-runs the excluded
  same-vendor leaf on *every* advance of a normal bundle, breaking criterion (d); the
  test `test_vendor_complement_unselected_leaf_is_not_promoted` exists to keep this from
  regressing.

The brief names an **Invariant to restore** (a state marker means what it says; an
interrupted beat is resumable), so per principles §1.2 the target was the smallest change
restoring the invariant across *all three* BUILT branches — hence the close/dep-halt note
recovery is in, not shaved off for diff size.

## Verification (project runner)

Runner per `pdca.toml` [gates] / `engine/scripts/run-verify.sh` for `template/tests/*`:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_check_resume` (the exact
per-module invocation the C4 gate uses; offline, stub leaves, no display needed —
the test module imports only stdlib + `pdca_harness`).

- **Green leg** (fix applied): 10/10 OK (0.010s).
- **Red leg** (production hunks reverted via `git stash push -- template/src/pdca_harness`,
  test left in place): 10/10 fail deterministically — the recovery tests fail on the
  missing behaviour (`check-review.md` never created → assertion/`FileNotFoundError`),
  the wording tests on the single-case `_missing_review_text`, and the tests referencing
  `state.REVIEW_ERROR_LOG` error on the absent constant. Restored with `git stash pop`.
- **Full offline driver suite**: `Ran 1463 tests … OK (skipped=2)` — no regressions
  (including the pre-existing missing-review test).
- **Root template-repo suite** (render + update-compat, instance venv python):
  `Ran 7 tests … OK`.

## Forced self-refutation (recorded)

- **(a) Genuine red?** Yes — actually reverted and re-run (above): 10/10 red without the
  fix, 10/10 green with it.
- **(b) Production path?** Yes — the tests drive `driver.advance`, `gates.run_gates` /
  `run_close_gates`, `dependency_halt.record`, and `assemble.assemble_summary` — the
  production modules, not copies. Leaf `mode="stub"` is itself a production branch of
  `run_review`/`run_advisory_leaves` (the offline mode CI uses), not a test-local mock;
  the recovery code under test is identical for stub and command modes (the discriminator
  reads artifacts, not the leaf mode).
- **(c) Fixture includes the fault?** Yes — the trap-door fixture is the *real* paid gate
  artifact (`gates.run_gates` output) with the review artifacts genuinely absent, exactly
  the on-disk state the wyrd issue_635 incident left; the ran-and-failed fixtures include
  the real error-log artifact rather than curating the failure out. `_trapdoor()` also
  asserts `state.state(d) == CHECKED` first, so the fixture provably *is* the defect's
  premise.

## Commit-readiness

The target repo configures no pre-commit hooks or formatter (no `.pre-commit-config`,
no ruff/flake8 config, no `core.hooksPath`; checked at the worktree root). CONTRIBUTING.md
requires DCO sign-off (`git commit -s`, added at publish per the target's flow) and a
green offline suite — which is green above. No AI-attribution trailers are to be added to
the eventual commit/PR.

## STOP discipline

Nothing pushed; no PR opened. `patch.diff` + test + these notes only.
