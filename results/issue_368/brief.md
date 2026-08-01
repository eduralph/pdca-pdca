# Brief — issue 368 / gate-timeout

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** gate-timeout
- **Defect:** a gate command has no bound anywhere in the chain: `gates._run_one`
  invokes the command through `progress.run_with_heartbeat` (`gates.py:409`) and
  `run_with_heartbeat` has no `timeout` parameter in its signature
  (`progress.py:25-37`, verified on main — `interval` is only the heartbeat tick), and
  the `[[gates.checks]]` schema has no per-gate timeout field. A hung gate stalls the
  Check beat indefinitely — measured: an advisory (`gating = false`) `C5-mutants` row
  held a wyrd Check beat for 19h 16m until a human interrupted it, while the heartbeat
  printed `… still working` — the mechanism built so a slow gate would not look hung is
  what stopped a genuinely hung gate from looking hung.
- **Success criterion:** (a) `run_with_heartbeat` accepts `timeout: int | None = None`;
  on expiry the child process **group** is terminated (gates run under `shell=True` —
  killing only the shell orphans the real work) and a distinguishable timed-out outcome
  is returned; `timeout=None` is byte-identical to today. (b) A `[[gates.checks]]` row
  may carry `timeout_secs`, with a `[gates] default_timeout_secs` fallback; a row that
  times out is recorded **`unverifiable`**, not `fail` — kept out of the gating verdict,
  surfaced at sign-off — with an evidence line naming the bound (e.g. "gate exceeded its
  3600s timeout"). (c) No timeout configured anywhere ⇒ gate behaviour unchanged.
  Demonstrable by C4-verify: unit tests drive `run_with_heartbeat` with a
  sleep-and-spawn command and a 1–2s bound, and drive a stub gate row through
  `run_gates` asserting the `unverifiable` outcome + evidence line.
- **Falsifiability:** the offline driver suite on this host
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_progress`). RED is
  deterministic on current `main`: calling `run_with_heartbeat(..., timeout=2)` raises
  `TypeError` (unexpected keyword), and a `timeout_secs` row assertion fails because the
  schema key is ignored — no hang is needed to make the test go red.
- **Invariant to restore:** no gate may consume unbounded wall-clock: an advisory row
  must not hold a veto over the cycle expressed as latency. Every gate invocation is
  bounded when a bound is configured, and an expired bound is recorded as "the oracle
  did not answer" (`unverifiable`, the #46 outcome), never as a pass/fail verdict.
  Source: internal rule — the instance gating policy (`pdca.toml` GATING POLICY comment)
  reasons about which rows may *block*; a row that can stop time blocks by other means
  (docs/principles.md §5 Tier C shape; no external canon claimed).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 311
- **Ordering note:** 311 also edits `gates.py`'s run machinery (host-CI command
  execution) — different waves, no dependency. 370 and 372 `Depends on` THIS bundle
  (370 attaches the partial capture to the timeout it introduces; 372 reuses its
  process-group kill + sessionization) — expressed in their briefs.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** the missing bound: `run_with_heartbeat` timeout + group termination on
  expiry, the `timeout_secs` / `default_timeout_secs` schema keys, and the
  `unverifiable` recording with the bound named in the evidence line. The escalating
  heartbeat wording (proposal item 4) MAY ship if trivial, else is explicitly dropped.
  / out of scope: sweeping stragglers of a *normally exiting* child (#372); persisting
  full gate output (#370); the target project's deadlocked test suite (filed there).
- **Repro instruction:** on the target checkout, `grep -n "def run_with_heartbeat" -A 12
  template/src/pdca_harness/progress.py` — no timeout in the signature; `gates.py:409`
  passes none. Write the named test: `run_with_heartbeat(["sleep", "60"], timeout=1)`
  (and a `shell=True` variant that spawns a child) asserting a timed-out outcome within
  ~2s and no surviving group member → red (TypeError) pre-fix, green post-fix.
- **External dependencies:** none
- **Test file:** template/tests/test_progress.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the invocation to bound — `gates.py:409-419` (`_run_one` →
  `run_with_heartbeat`, evidence truncation at `:419`); the signature —
  `progress.py:25-37`; the wait loop the expiry check joins — `progress.py:133`
  (`proc.wait(timeout=interval)`); the `unverifiable` outcome's existing handling in
  `gates.py`/`assemble.py` (#46/#165 discipline) so the timed-out row routes to §6 the
  same way.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/progress.py template/src/pdca_harness/gates.py` — no
  timeout work; `grep -rn "start_new_session\|killpg" progress.py` empty (the #368
  staging exists only in the wyrd instance). Commit grep `#368` empty. Not fixed, not
  in flight upstream.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
