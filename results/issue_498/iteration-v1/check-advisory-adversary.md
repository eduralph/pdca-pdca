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
