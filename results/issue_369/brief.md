# Brief — issue 369 / checked-trapdoor-lost-review

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** checked-trapdoor-lost-review
- **Defect:** `check-gates.json` *is* the CHECKED marker (`state.py:171-176`, verified
  on main), but the BUILT branch runs gates → reviewer → advisory leaves as one
  indivisible step (`driver.py:75-92`) while CHECKED dispatches to `assemble` alone
  (`driver.py:93-95`). Any death in the window between the gate write and the reviewer
  leaf (Ctrl-C, OOM, killed session) lands the bundle in CHECKED with no review; on
  resume, `assemble_summary` fills `_missing_review_text()` and the reviewer can never
  run again for that round — no flag or subcommand reaches it; the only escape is
  hand-deleting `check-gates.json` and re-paying the entire gate run. Observed for real
  (wyrd `issue_635`, after the #368 19-hour hang was interrupted). Sharp edge: the
  record cannot distinguish a reviewer that *never ran* from one that *ran and failed*.
- **Success criterion:** (a) a bundle in CHECKED whose `check-review.md` is absent AND
  whose `check-review.error.log` is absent (the engine's existing failed-leaf
  discriminator, #138) gets the reviewer leaf run on the next `advance` before
  `assemble_summary` — the paid gate record is preserved, the missing leaf is
  recovered; same recovery for the configured advisory leaves' artifacts; (b) a
  reviewer that ran and failed (error log present) is NOT re-run — today's behaviour;
  (c) §6 distinguishes the two cases in its wording, so a skipped reviewer never reads
  like a failed one; (d) an uninterrupted cycle is byte-identical to today.
  Demonstrable by C4-verify: unit tests build the trap-door bundle state on disk
  (brief + patch + `check-gates.json`, no review artifacts) and assert `advance` runs
  the (stubbed) reviewer, and build the ran-and-failed state and assert it does not.
- **Falsifiability:** the offline driver suite on this host. RED now: on current
  `main`, `advance` on the trap-door state goes straight to `assemble.assemble_summary`
  (`driver.py:93-95`) — the assert-reviewer-ran test fails deterministically; the
  §6-wording assertion fails against `_missing_review_text()`'s single-case text.
- **Invariant to restore:** a state marker means what it says, and an interrupted beat
  is resumable: for every artifact the state machine derives a state from, reaching
  that state implies each of the beat's leaves either produced its artifact or failed
  *visibly* (error log) — a crash between two sub-steps must never silently convert
  "not yet run" into "unrecoverably skipped". Source: internal rule — the project's own
  state doctrine ("state is the files in `results/issue_<id>/`; nothing hidden",
  CLAUDE.md/docs 02), Tier C per docs/principles.md §5; this is a structural/lifecycle
  defect, so this invariant outranks diff-minimalism (principles §1.2).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 332, 341
- **Ordering note:** 332 also edits the §6 assembly paths in `assemble.py`; 341 also
  restructures the BUILT/CHECKED sequencing in `driver.advance` — shared files/regions,
  different waves. No build-on dependency any direction.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** the trap door: CHECKED must recover a never-ran reviewer/advisory leaf
  (the issue's Option A — resume the missing leaf, preserving the expensive gate
  artifact) and §6 must state skipped vs failed distinctly. / out of scope: Option B
  (moving the marker / re-running gates — rejected in the issue as the expensive
  half); the gate timeout itself (#368); any change to what a *failed* leaf does.
- **Repro instruction:** on the target checkout, create a bundle dir with a minimal
  `brief.md`, `patch.diff`, and a valid `check-gates.json`, no `check-review.md` and no
  `check-review.error.log`; confirm `state.state` says CHECKED; run `driver.advance`
  with a stub reviewer leaf and observe it is never invoked and `SUMMARY.md` appears
  with the missing-review text. The named test automates exactly this → red pre-fix.
- **External dependencies:** none
- **Test file:** template/tests/test_check_resume.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the marker derivation — `state.py:171-176`; the indivisible BUILT
  branch — `driver.py:75-92`; the CHECKED dispatch — `driver.py:93-95`; the error-log
  discriminator pattern — `leaves.py:290-323` (`error_log` write on failure, "leave no
  error log behind" on success) and the `check-*.error.log` naming (`leaves.py:70-72`);
  `_missing_review_text()` (`assemble.py:386`, consumed at `:185,:253`) for the §6
  wording split.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/driver.py template/src/pdca_harness/state.py
  template/src/pdca_harness/assemble.py` — #138 added the error logs, nothing resumes a
  missing leaf at CHECKED; commit grep `#369` empty. Not fixed, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
