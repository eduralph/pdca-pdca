# Build notes — issue 436 / size-signal-attributable-rounds — iteration 3

Target: eduralph/pdca-harness @ main (`0fbfa26` — still origin/main tip, re-fetched
2026-08-06), built in `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt-l0`).
All `path:line` cites are against that tree with the patch applied.

## Carry-forward (iterations 1 AND 2) — the T3 red is root-caused this time

Both prior rejections recorded the same failing gate: `T3 runtime … == T3: root suite
OK, driver suite FAILED (rc 1)`, and both reviews could only say "not reproducible,
runner absent". Iteration 2 reproduced the gate's command five ways and got green each
time but could not explain the recorded red. New, decisive evidence this round:

**The identical T3 red is recorded in EVERY frozen bundle of this instance since
issue_384** — issues 384, 396, 401, 402, 403, 411, 420, 428, 434, 436 (both rounds),
442; survey of every `results/*/check-gates.json` + `iteration-v*/check-gates.json`,
rows with `element == "T3"`. Eleven different bundles, eleven unrelated patches
(memory caps, publish slices, merge-mode bases, …), one byte-identical evidence line.
A red that fires regardless of patch content is not caused by any of those patches —
including this one. It is a standing fault of the Check-run environment on this host,
and reviewers in issue_411 and issue_420 likewise failed to reproduce it
(issue_420's final review even marked T3 PASS on an independent 1,563-test green run).

Reproduction attempts this round, all green, all through the project's own runners:

- clean base `0fbfa26`: driver suite `cd template && PYTHONPATH=src python3 -m
  unittest discover -s tests` → OK, 1563 tests (both system and instance-venv
  python 3.14.4);
- patched: OK, 1576 tests (2 skipped);
- the configured T3 gate itself (`engine/scripts/run-suite.sh`) from the instance
  root: `== T3: root suite OK, driver suite OK`, rc 0;
- the same script executed through the driver's own gate executor
  (`progress.run_with_heartbeat(cmd, shell=True, capture=True, env={PDCA_BUNDLE,
  PDCA_WORKTREE,…})` — the exact call `gates._run_one` makes,
  pdca-pdca `src/pdca_harness/gates.py:406-412`): rc 0.

Why the failing output was never seen: the instance's engine predates #370 — the
target at `0fbfa26` archives per-round gate logs (`state.py:110-113`,
`GATE_LOGS_DIR`), but pdca-pdca's engine has no `GATE_LOGS_DIR` and no
`gate-logs/` exists in any bundle, so only the last output line survived. Once this
instance updates onto a main containing #370, the next T3 red will carry its full
log and can be diagnosed instead of guessed at.

Disposition for the human at sign-off: the T3 row is **advisory by configuration**
(`pdca.toml:839`, `gating = false`, comment: "a whole-suite run is red on any
pre-existing failure regardless of the patch") and demonstrably not patch-caused.
Recommend clearing the §6 T3 item on this evidence, and (outside this brief's scope)
filing an instance issue for the standing driver-suite red in Check runs since
issue_384. The irony is the brief's own point: two rounds of this bundle were burned
on a host-side fault charged to the slice — the defect class #436 exists to stop.
(Under the shipped attribution those rounds still count, correctly: the faulting T3
row is recorded non-gating and green-gating elsewhere, and only a *gating*
unverifiable/flaky row can attribute — `size_signal.py:195-209`, pinned at
`template/tests/test_size_signal.py:669`.)

### T2 (docs runner "absent, provisional")

`engine/scripts/run-docs-check.sh` run this round from the instance root against the
patched worktree: docs lint OK, `render_site: link audit OK` (22 pages), rc 0. The
script renders to a mktemp dir, so the worktree stays clean. The runner is
instance-side (`pdca-pdca/engine/scripts/`), which is why a reviewer confined to the
target tree cannot find it — that is the reviewer's vantage, not a defect of the patch.

### T4 (closed/rejected-work duplication oracle)

Refreshed via `gh` against eduralph/pdca-harness on 2026-08-06:

- closed PRs matching `size_signal`: only **#361** (MERGED 2026-07-28 — the original
  #324 backstop this brief extends);
- closed PRs matching "rounds attribution": only **#330** (merged, signoff/gates
  fail-open reads — unrelated);
- open PRs: **zero**.

No closed/rejected work duplicates this change; merged history on the affected paths
still shows only `f616bc9` (#355), the re-plan boundary.

### Premise update the publisher must carry

The brief (and iteration 2) said #359 is OPEN and the cross-instance re-derivation is
"deferred to #359's calibration loop". **#359 is now CLOSED (COMPLETED, 2026-08-01)**
— its Act calibration loop landed via PR #394 (`abd6f1e`, in main). The deferral
survives with corrected wording: re-deriving the published 76% rounds-rule precision
over the 86-bundle getwyrd/wyrd-pdca corpus (not reachable from this checkout) is left
to the **landed** #359 Act calibration loop, which retunes `[driver.size_signal]` as
each instance's own corpus accumulates post-fix. The PR description must say so.

## What changed vs iteration 2 (the non-repeat)

Production code is semantically identical to the twice-reviewed attempt — every
review verdict on the change itself PASSed in both rounds (C1–C5, T1, T5); both
iterates were driven by the advisory T3 environment red plus evidence questions, not
by any finding against the code. Rewriting accepted production would be churn for its
own sake — the very failure mode this signal measures. The carry-forward is addressed
with what it actually asked for: the failing gate is now root-caused with
cross-bundle evidence (above). The patch itself is NOT unchanged — two new bindings:

1. `test_a_flaky_flagged_pass_is_environment_attributed`
   (`template/tests/test_size_signal.py:614-621`) — the **likelier** shape #371's
   recorder will write: a confirm-once re-run ending fail→PASS records final result
   `pass` with the flaky marker. Iteration 2 only pinned flaky-on-`fail`; attribution
   must key on the marker, not the result the re-run settled on. Production already
   satisfies it (`size_signal.py:203-207` tests the key independent of result) — the
   contract is now bound instead of incidental.
2. `test_the_miner_inherits_environment_attribution`
   (`template/tests/test_size_calibrate.py:253-270`) — the Success criterion's
   "the miner inherits the attribution with no second implementation" sentence, bound
   end-to-end through the loaded `scripts/size-calibrate` module (`sc.iteration_rounds`,
   the import at `template/scripts/size-calibrate:71-74`, call site `:268`), with real
   archived evidence files. The brief's Test-file field invites exactly this
   ("if the miner needs its own guard, extend test_size_calibrate.py alongside");
   both changed modules ride the instance C4 contract.

## The change (production summary, cites on the patched tree)

`iteration_rounds` counted every `iteration-v*` archive past the last re-plan boundary
(main `size_signal.py:121-146`) without opening the archive's evidence, so a round lost
to an environment fault fired the rounds rule (`rounds: 2` default,
`size_signal.py:78`). The fix teaches the ONE shared counter attribution:

- `size_signal.py:121-156` — `iteration_rounds` filters counted archives through
  `_environment_attributed`; the re-plan boundary (#355) applies FIRST, so attribution
  only refines rounds already charged to the current brief (pinned at tests:693).
- `size_signal.py:158-192` — `_environment_attributed`: excludes a round iff
  (a) no plain gating `fail` (a `fail` with truthy `flaky` is a confirm-once record —
  the #371 contract consumer side, per the brief's premise correction that #371 has
  NOT landed; dormant until its recorder ships), (b) ≥1 gating row `unverifiable` or
  flaky, (c) the archived review drove nothing of its own. Plain-fail, all-green
  (reviewer-driven), and mixed-cause rounds all count.
- `size_signal.py:195-209` — `_archived_gating_rows`: reads the archive's own
  `check-gates.json` (archived per round via `state.DOWNSTREAM_OF_BRIEF`,
  `state.py:83-114`); returns `None` (≠ `[]`) on missing/unreadable/malformed so "no
  evidence" never reads as "no gating rows"; scoped to GATING rows (only a gating row
  can have mechanically driven the iterate — `gates.py` vocabulary `result` ∈
  pass/fail/unverifiable, rc-77 channel).
- `size_signal.py:212-245` — `_review_drove_the_iterate`: counts the round unless the
  file is a REAL review artifact whose only finding is the standing Validation row
  (#293). Findings are read through `assemble._items_from_artifact(…,
  allow_standing=True)` (`assemble.py:158`) — the same parser feeding §6 and
  auto-iterate; a second parser for the same artifact is the #294 defect class. Any
  other NEEDS-HUMAN finding, a whole-cell FAIL verdict
  (`_has_fail_verdict_cell`, `size_signal.py:248-256`), a leaf-status placeholder
  (`assemble.leaf_status`, `assemble.py:92`), or a missing/unreadable file counts the
  round. Lazy `assemble` import — the same cycle-avoidance `measure` documents.
- `size_signal.py:270-290` — `measure()`'s `rounds` comment names the second boundary.
- Failure direction throughout is the brief's: ambiguous/missing/unreadable evidence
  COUNTS the round; over-counting keeps the backstop, silent shrinkage is the failure
  mode `size_signal.current` already refuses.

## Ruled out (with costs)

1. **Attribution at Check time** (driver writes an attributed figure into
   `size-signal.json`): leaves the miner counting the contaminated quantity — the
   issue's "measurement bug". Cost: a second counter in `driver.py` (~40 lines) + a
   mirrored one in `size-calibrate` (~40 lines) + a new recorded key every consumer
   must learn, vs one function-set in the module both readers already share. The
   Invariant to restore is "the signal measures the quantity its calibration defined"
   (`size_signal.py:135-137` doctrine) — only the shared counter restores it for both.
2. **Copying instead of reusing `assemble._items_from_artifact`** (it is
   module-private): duplicates ~90 lines of parsing (`assemble.py:435-518` on main)
   and creates the two-parsers-for-one-artifact drift #294 already demonstrated;
   promoting it public touches `assemble` + its tests for zero behaviour change.
   In-package private use, one call site, is the smallest invariant-preserving option.
3. **Looser review test** (only *implementation-shaped* findings count the round):
   telling an echo of the gate row from an independent finding is textual guesswork;
   the brief's asymmetry ("ambiguous … COUNTS the round") mandates the strict
   direction. Consequence, recorded for the human: a review that merely mirrors an
   unverifiable gate as its own NEEDS-HUMAN row keeps the round counted.

## Miner before/after (the brief's mandated ask-2 report)

`PYTHONPATH=src python3 scripts/size-calibrate --root /home/eddie/pdca/pdca-pdca
--csv …` before (all three changed files stashed) and after (patch applied), instance
venv. Corpus: **30 settled bundles, 31 CSV rows, 0 churned** (issue_436 itself
excluded as in-flight). **Every number is unchanged — the per-bundle CSV is
byte-identical; stdout differs only in the output path line.** Verified why: a scan of
every `results/*/iteration-v*/check-gates.json` (10 archived rounds) found **zero**
gating rows recorded `unverifiable` or bearing `flaky` — no environment-lost rounds
exist in this corpus, so the exclusion is inert here: direct evidence it is as narrow
as specified. The cross-instance 86-bundle corpus behind the published 76% is not
reachable from this checkout; re-derivation is left to the landed #359 calibration
loop (see premise update above) — **the PR description must say so.**

## Refutation record (forced self-check)

- **(a) Genuine red?** Yes — twice over. The instance's configured C4 gate
  (`engine/scripts/run-verify.sh`, the `C4-verify` cmd) ran the red leg with only the
  production hunks reverted: test_size_signal **5 failures**
  (`…solely_unverifiable…`:590, `…excluded_round_keeps_the_rounds_rule…`:596,
  `…flaky_flagged_fail…`:607, `…flaky_flagged_pass…`:614,
  `…replan_boundary_still_wins…`:693) — and a targeted stash-revert run confirmed the
  miner-side pin also red (`test_the_miner_inherits_environment_attribution`), **6
  red pre-fix total, 0 post-fix**; gate verdict `C4 PASS: red without the fix, green
  with it`, rc 0. The inclusion/fail-safe tests are green on both sides *by design* —
  they pin behaviour the fix must preserve.
- **(b) Production path?** Yes — the tests call `size_signal.iteration_rounds` /
  `measure` / `oversize_reasons` from `template/src/pdca_harness` (the module the
  patch edits), and the miner test goes through the real `template/scripts/
  size-calibrate` loaded by path (`test_size_calibrate.py:52-57`). No copy, no mock.
- **(c) Fixture includes the fault?** Yes — every fixture bundle carries the
  environment-faulted round itself (`iteration-v1` with the unverifiable/flaky gating
  row and its archived review) **alongside** a plainly-failing `iteration-v2`, so the
  assertions discriminate the excluded round from the counted one inside one bundle.
  The brief's exact Repro shape reads `(2, 0)` on main → `(1, 0)` patched.

## Runner + commit-readiness

- C4: `engine/scripts/run-verify.sh` (PDCA_BUNDLE=results/issue_436) → rc 0,
  red→green as above.
- T3: `engine/scripts/run-suite.sh` → `== T3: root suite OK, driver suite OK`, rc 0;
  full driver suite 1576 tests, OK (2 skipped).
- T2: `engine/scripts/run-docs-check.sh` → lint OK, link audit OK, rc 0.
- The target configures no pre-commit hooks or formatter (no `.pre-commit-config*`,
  no root `pyproject`; CI is docs-check/render-check/require-linked-issue).
  `git diff --check` clean; `py_compile` clean on all three files; the only >100-col
  lines flagged in touched files predate the patch (`size_signal.py:36` module
  docstring, `test_size_calibrate.py:438`) — the patch adds none.
- Nothing pushed, no PR opened; STOP discipline observed.
