# Brief — issue 370 / gate-output-evidence-log

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** gate-output-evidence-log
- **Defect:** a gate's full output is discarded: `_run_one` captures the command's
  stdout+stderr (`gates.py:409`), `_classify` keeps only the last line
  (`gates.py:423,446`), the row truncates it to 120 characters (`gates.py:419` /
  `:365`), and nothing writes the rest anywhere. `check-gates.json` / `check-gates.md`
  are the only record a gate run leaves, so the entire evidence for a verdict —
  including a *gating* red that parks the bundle — is one truncated line. Measured
  (wyrd `issue_648`): a transient gating `C4-ci` red recorded only
  `xtask: … failed with exit status: 101`; which test failed is unrecoverable — the
  post-mortem had to be reconstructed from reflog stamps and target-dir mtimes and
  still could not name the test.
- **Success criterion:** (a) a bundle-scoped gate run writes `gate-logs/<rule_id>.log`
  into the bundle: a small header (command, cwd, `$PDCA_WORKTREE`, start time,
  duration, exit code / outcome) then the combined output verbatim; one file per rule
  id, overwritten per Check run; (b) the row gains `log` (bundle-relative path) and
  `duration_secs`, additively — existing keys and consumers unchanged; (c) the iterate
  archive moves `gate-logs/` alongside the round's other downstream artifacts, so each
  round keeps its own evidence; (d) on timeout (the #368 bound, prior wave), the
  partial capture is attached so a hung gate's log shows *where* it hung instead of
  nothing; (e) a repo-scoped run with no bundle (`pdca gates --working-tree`, the CI
  re-gate) keeps today's behaviour. The 120-char evidence line stays — it is the right
  summary; the defect is that it was also the entire record. Demonstrable by
  C4-verify: unit tests run a stub gate row bundle-scoped and assert the log file's
  header + verbatim body + row keys; an archive-step test asserts per-round retention.
- **Falsifiability:** the offline driver suite on this host. RED now: after a
  bundle-scoped `run_gates` with a stub row on current `main`, `gate-logs/` does not
  exist and the row carries no `log`/`duration_secs` keys — the assertions fail
  deterministically.
- **Invariant to restore:** evidence sufficiency for verdicts: any output that decides
  or explains a recorded gate verdict must itself be recorded in the bundle — a
  verdict's full basis is reconstructable from bundle files alone, per round. Source:
  internal rule — the state-is-files doctrine (CLAUDE.md/docs 02: "State is the files
  in `results/issue_<id>/`; nothing is hidden"), Tier C per docs/principles.md §5.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 368
- **Conflicts with:** 372
- **Ordering note:** depends on 368 — criterion (d) attaches the partial capture to the
  timeout outcome 368 introduces, and both edit `gates._run_one`; building on its
  accepted result avoids a blind collision. Conflicts with 372 (both touch
  `progress.py` capture handling) — different waves.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** persist the evidence a bundle-scoped gate run already produces, as in the
  criterion. / out of scope: changing any verdict/classification logic; the timeout
  mechanism itself (#368, prior wave); straggler sweeping (#372); repo-scoped/CI runs.
- **Repro instruction:** on the target checkout, read `gates.py:409-423` — the capture
  is consumed by `_classify` and dropped; run any bundle-scoped gate and observe the
  bundle contains only `check-gates.json`/`check-gates.md` with the truncated
  `path_line`. The named test automates the missing-log assertion → red pre-fix.
- **External dependencies:** none
- **Test file:** template/tests/test_gate_logs.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the capture-and-drop — `gates.py:409-419`; `_classify` keeping the
  last line — `gates.py:423,442-446`; the row-shape writers (`:365,:419`) for the
  additive keys; the iterate-archive step that moves per-round artifacts
  (`driver.py:316`-region, `DOWNSTREAM_OF_BRIEF` handling) as the pattern for
  archiving `gate-logs/`; 368's timeout outcome for where the partial capture attaches.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/gates.py` — evidence-line truncation history only,
  nothing persists gate output; commit grep `#370` empty. The staging exists only in
  the wyrd instance. Not fixed, not in flight upstream.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
