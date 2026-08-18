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
