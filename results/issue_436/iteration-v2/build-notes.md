# Build notes — issue 436 / size-signal-attributable-rounds — iteration 2

Target: eduralph/pdca-harness @ main (`0fbfa26`), built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`). All `path:line` cites are against that
tree with the patch applied.

## Iteration-1 carry-forward — both items resolved with new evidence

### T3 — "is the recorded driver-suite failure a real integration regression?" → NO

The frozen record kept only the gate's last line (`== T3: root suite OK, driver suite
FAILED (rc 1)`); no failing test name survives (no gate-logs in `iteration-v1/`).
I reproduced the gate's exact conditions instead — same interpreter
(`/home/eddie/pdca/pdca-pdca/.venv/bin/python3`, 3.14.4), same commands, same worktree,
iteration-1's patch applied byte-for-byte:

- **Baseline** (clean `0fbfa26`): driver suite `cd template && PYTHONPATH=src python3 -m
  unittest discover -s tests` → **OK, 1563 tests**.
- **Patched, exact gate command**: OK, 1573 tests — then **4 more repeat runs, all OK**
  (no flake surfaced in 5 runs).
- **The gate script itself** (`pdca-pdca/engine/scripts/run-suite.sh`, run from the
  instance root as T3 does): `== T3: root suite OK, driver suite OK`, rc 0 — twice
  (once with iteration-1's patch, once with this iteration's).
- **The C4→T3 sequence**: ran `engine/scripts/run-verify.sh` end-to-end, then inspected
  the tree — it restores exactly base + full patch (`git diff --stat` identical), and
  the driver suite is green after it.
- **No gate race**: the harness runs configured gates **sequentially**
  (`template/src/pdca_harness/gates.py:388-399` — a plain `for chk in
  cfg.gates_checks` loop), so T3 cannot have sampled the tree mid-C4.

Conclusion: the rc 1 is not reproducible under identical command/interpreter/tree and
is **not patch-caused**. The one mechanism I found that *could* produce exactly the
recorded shape is instance-side: `run-verify.sh:73`'s `restore() { git apply …
2>/dev/null || true; }` **discards a re-apply failure**, and a restore that failed on
that run would leave the tree production-reverted with the tests present — the driver
suite then fails with precisely the 4 deliberately-red tests while the root suite
(render/update-compat, which copies the tree) stays OK. The round-trip is clean for
this patch on every attempt here, so whatever interfered was transient host state. That
is an instance-infrastructure concern (pdca-pdca `engine/`, not the target repo) and
out of this brief's scope — worth an instance issue if it recurs. Noting the irony for
the human: a round of this very bundle was burned on a host-side fault charged against
the slice — the defect class #436 exists to stop. (Under the shipped attribution that
round still counts, correctly: T3 is non-gating (`pdca.toml:839`, `gating = false`),
and its archived gating rows are all green — condition (b) refuses non-gating evidence,
`size_signal.py:203-207` and the pin at `template/tests/test_size_signal.py:661`.)

### T4 — "does closed/rejected prior work duplicate this change?" → NO

The reviewer lacked a closed-work oracle; supplied it via `gh` against
eduralph/pdca-harness:

- Closed PRs mentioning `size_signal`: only **#361** (MERGED 2026-07-28 — the original
  #324 backstop this brief extends).
- Closed-**unmerged** (rejected) PRs, whole repo: only **#4** ("PROBE: no linked
  issue"), a harness self-test, unrelated.
- Closed issues around size/rounds: #324/#321/#318/#320/#325 — the calibration lineage
  the brief already cites; none touches environment-fault attribution.
- Merged history on the affected paths (`git log -- …/size_signal.py
  …/size-calibrate`): `f616bc9` (#355) landed the **re-plan** boundary only.

No duplication; this change is the first attribution of rounds to environment faults.

## What changed vs iteration 1

Production code is **identical** to the reviewed attempt — C1–C5 all PASSed there, and
the iterate was driven solely by the two evidence questions above, both now answered;
rewriting accepted production code would be churn for its own sake. The test module
gains **one test** binding the success criterion's second half end-to-end:
`test_the_mixed_cause_round_still_fires_the_rounds_rule`
(`template/tests/test_size_signal.py:637-651`) — the mixed-cause bundle (unverifiable
gating row + implementation finding) must still report `rounds: 2` through `measure`
and fire the rounds rule in `oversize_reasons`, so the exclusion provably cannot eat
genuine slice churn. Previously only the `iteration_rounds` tuple was pinned for that
case (tests:626); the brief's criterion sentence names the *rule firing*.

## The change itself (unchanged from iteration 1; cites refreshed)

`iteration_rounds` counted every `iteration-v*` archive past the last re-plan boundary
(`size_signal.py:121-146` on main) without opening the archive's evidence, so a round
lost to an environment fault fired the rounds rule (`rounds: 2`, threshold at
`size_signal.py:78`). The fix teaches the ONE shared counter the attribution; the miner
inherits it through its existing import (`template/scripts/size-calibrate:71-74,268` —
unchanged, no second implementation).

- `size_signal.py:121-156` — `iteration_rounds` filters counted archives through
  `_environment_attributed`; the re-plan boundary (#355, `f616bc9`) applies FIRST, so
  attribution only refines rounds already charged to the current brief (pinned at
  tests:685).
- `size_signal.py:158-192` — `_environment_attributed`: excludes a round iff (a) no
  plain gating `fail` (a `fail` bearing truthy `flaky` is a confirm-once fail→pass
  record — the #371 contract, consumer side per the brief's premise correction that
  #371 has NOT landed; the key is dormant until its recorder ships), (b) ≥1 gating row
  `unverifiable` or flaky, (c) the archived review drove nothing of its own. Plain
  fail, all-green (reviewer-driven), and mixed-cause rounds all count.
- `size_signal.py:195-209` — `_archived_gating_rows`: reads the archive's
  `check-gates.json` (archived per round by `state.DOWNSTREAM_OF_BRIEF`,
  `state.py:83-114`); returns `None` (≠ `[]`) on missing/unreadable/malformed so "no
  evidence" never reads as "no gating rows". Scoped to GATING rows — only a gating row
  can have mechanically driven the iterate (pinned, tests:661).
- `size_signal.py:212-245` — `_review_drove_the_iterate`: True (count) unless the file
  is a REAL review artifact whose only finding is the standing Validation row. Findings
  are read through `assemble._items_from_artifact(…, allow_standing=True)` — the same
  parser feeding §6 and auto-iterate. STANDING is the one non-driver kind; any other
  NEEDS-HUMAN finding, a whole-cell FAIL verdict (`_has_fail_verdict_cell`,
  `size_signal.py:248-256`), a leaf-status placeholder, or a missing/unreadable file
  counts the round. Lazy `assemble` import — the cycle-avoidance pattern `measure`
  documents (`size_signal.py:222-224`).
- `size_signal.py:288-289` — `measure()`'s `rounds` comment names the second boundary.
- `template/tests/test_size_signal.py:540-692` — the class covering every case the
  brief's Test-file field lists, plus FAIL-cell, non-gating-row, and replan-boundary
  edges, and BOTH end-to-end assertions (excluded round keeps `oversize_reasons` quiet,
  tests:596; mixed-cause round still fires it, tests:637).

`test_size_calibrate.py` untouched: the miner calls the same `iteration_rounds`
(single-definition invariant already locked at tests:524), and its own
`iteration_rounds` cases use bare archives — missing evidence — whose behaviour the
fail-safe direction preserves byte-for-byte.

## Design decisions / ruled out (held from iteration 1 — still valid)

1. **Attribution at Check time instead** (driver writes an "attributed rounds" figure
   into `size-signal.json`): leaves the miner counting the contaminated quantity —
   the issue's "measurement bug". Cost: a second counter in `driver.py` (~40 lines) +
   a mirrored one in `size-calibrate` (~40 lines) + a new recorded key every signal
   consumer must learn, vs one function-set in the module both already share. The
   Invariant to restore is "the signal measures the quantity its calibration defined"
   (`size_signal.py:135-137`), and only the shared counter restores it for both readers.
2. **Review-test strictness**: any finding other than the STANDING row counts the round
   — stricter than the brief's minimum. The brief's failure direction is asymmetric
   ("over-counting keeps the backstop; silent shrinkage is the failure mode `current`
   already refuses"). Consequence for the human: a review that merely MIRRORS the
   unverifiable gate as its own NEEDS-HUMAN row keeps the round counted; telling echo
   from finding is textual guesswork, and ambiguity counts per the brief.
3. **Reusing `assemble._items_from_artifact` (module-private)**: copying its parsing
   into size_signal duplicates ~90 lines (`assemble.py:435-518`), and a second parser
   for the same artifact is the #294 defect class; promoting it public touches assemble
   + its tests for zero behaviour change. In-package private use, one call site.
4. **`flaky` semantics**: truthy `flaky` on a gating row is environment-attributed AND
   exempts that row from "plain fail" — both halves from the brief's Scope and Success
   criterion. No writer emits the key at `0fbfa26` (`gates.py` `_row`), so the branch
   is dormant until #371's recorder lands.

## Miner before/after (the brief's ask-2 report half)

Ran `template/scripts/size-calibrate --root /home/eddie/pdca/pdca-pdca --csv …` before
(stashed) and after the patch. Corpus: 28 settled bundles, 31 CSV rows, 0 churned.
**Every number is identical — the per-bundle CSV is byte-identical** (`diff`: only the
output-path line differs). Verified why: a scan of every
`results/*/iteration-v*/check-gates.json` in the corpus found **zero** archives whose
gating rows contain `unverifiable` or a `flaky` key — no environment-lost rounds exist
here, so the exclusion is inert, direct evidence it is as narrow as specified.

The published 76% rounds-rule precision rests on the 86-bundle getwyrd/wyrd-pdca corpus
(with the contaminated issue_652 round), NOT reachable from this checkout; its
re-derivation is deferred to **#359**'s calibration loop and **the PR description must
say so** (brief Scope — please carry this into publish).

## Refutation record (forced self-check)

- **(a) Genuine red?** Yes — the instance's own C4 gate (`engine/scripts/run-verify.sh`,
  the configured `C4-verify` cmd) ran the red leg with only the production hunks
  reverted: **4 failures**, exactly the exclusion-side tests
  (`…solely_unverifiable…`:590, `…excluded_round_keeps_the_rounds_rule…`:596,
  `…flaky_flagged_fail…`:607, `…replan_boundary_still_wins…`:685); green leg with the
  fix applied passed → `C4 PASS: red without the fix, green with it`, rc 0. The
  inclusion/fail-safe tests (incl. the new tests:637) are green on both sides *by
  design* — they pin behaviour the fix must preserve; the four red ones bind the
  objective.
- **(b) Production path?** Yes — the tests call `size_signal.iteration_rounds` /
  `measure` / `oversize_reasons` from `template/src/pdca_harness` (the module the patch
  edits); no copy, no mock. The miner leg is bound by the existing single-definition
  assertion (tests:524) against the real `template/scripts/size-calibrate`.
- **(c) Fixture includes the fault?** Yes — every fixture bundle carries the
  environment-faulted round itself (`iteration-v1` with the unverifiable/flaky gating
  row) **plus** a plainly-failing `iteration-v2`, so assertions discriminate the
  excluded round from the counted one inside the same bundle. The brief's exact Repro
  (v1 unverifiable-only + clean review, v2 plain fail) reads `(2, 0)` on main →
  `(1, 0)` patched.

## Runner + commit-readiness

- T3 gate script (`engine/scripts/run-suite.sh`, the configured runner):
  `== T3: root suite OK, driver suite OK`, rc 0 — root render/update-compat suite under
  the instance venv (copier importable) AND the offline driver suite (1574 tests, 2
  skipped) both green with the final patch.
- C4 gate script (`engine/scripts/run-verify.sh` with `PDCA_BUNDLE=results/issue_436`):
  rc 0, red→green as above.
- The target repo configures no pre-commit hooks or formatter (no
  `.pre-commit-config*`, no root `pyproject` — only `.jinja` templates rendered into
  instances); `git diff --check` clean, no >100-col lines introduced.
- No external dependencies hit; none declared by the brief. Nothing pushed, no PR.
