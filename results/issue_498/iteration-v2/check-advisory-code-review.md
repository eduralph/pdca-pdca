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
