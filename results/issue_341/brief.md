# Design proposal — issue 341 / do-halt-on-unmet-dependency

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** do-halt-on-unmet-dependency
- **Kind:** enhancement (design proposal)
- **Goal:** a builder that honestly declares an unmet external dependency
  (`NEEDS-HUMAN external dependency:` in `build-notes.md`, per the builder contract)
  currently changes nothing: BUILT unconditionally buys the full Check beat — gates,
  cross-vendor reviewer, adversary — to adjudicate a patch already stated to be
  unverifiable (`driver.py:75-92` consults nothing the builder wrote). Give Do a halt
  seam: a *confirmed* declaration routes through the existing close fast path to
  sign-off; a *refuted* one proceeds to Check unchanged, recorded.
- **Success criterion:** with the feature enabled: (a) marker present + claim
  **confirmed** (the named dependency resolves to a `[[doctor.checks]]` row — registered,
  or parsed from the fenced TOML block the builder contract already requires it to
  propose — AND that row's detect `cmd` exits non-zero) ⇒ the bundle takes the close
  fast path (N/A gate matrix via `gates.run_close_gates`, no reviewer, no adversary),
  §6 carries the `_declared_external_deps` item, and the bundle halts at
  AWAITING_SIGNOFF — **not** DISCONTINUED; (b) marker present + claim **refuted** (the
  detect `cmd` exits 0, or no row and no parseable proposed row) ⇒ byte-identical to
  today's full Check, with the refutation recorded where `pdca act index` can see it;
  (c) a malformed proposed-row TOML block ⇒ unconfirmed ⇒ full Check (fail toward
  review, never toward skipping it); (d) a test asserts a builder cannot skip the
  reviewer with a claim whose detect `cmd` exits 0; (e) terminal state is never set by
  a leaf — sign-off still owns COMPLETE/DISCONTINUED; (f) the behaviour is config-gated
  opt-in for one release, `off` byte-identical to today. Demonstrable by C4-verify via
  the offline driver suite (stub builders/leaves, `true`/`false` detect cmds).
- **Falsifiability:** the offline driver suite on this host. RED now: a test writing the
  marker with a failing detect cmd and asserting the reviewer leaf is NOT invoked fails
  on current `main` — the BUILT branch (`driver.py:75-92`) runs
  `gates.run_gates` → `leaves.run_review` → `run_advisory_leaves` unconditionally; the
  close fast path is reachable only from `brief.disposition_hint` pre-Do
  (`driver.py:50,71` → `_do_close` `:174-181`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 340
- **Conflicts with:** 369
- **Ordering note:** depends on 340 — the adjudication reuses its detect-cmd probe, one
  beat later (#340 prevents the burn Plan could foresee; this bounds the burn it could
  not). Conflicts with 369: both restructure the BUILT/CHECKED sequencing in
  `driver.advance` — different waves, whichever order the scheduler picks.
- **Difficulty:** high
- **Scope:** the marker-triggered routing in `driver.advance` at BUILT; deterministic
  adjudication (prefer the proposal-driven reading: parse the builder's fenced
  `[[doctor.checks]]` TOML block when no registered row matches — the builder supplies
  the detect command, the harness runs it, the exit code decides); reuse of the close
  fast path machinery (`CLOSE_MARKER` substitutes for `patch.diff` — `state.py:36`,
  `state.py:159`, `gates.run_close_gates` `gates.py:152`) or an equivalent
  blocked-marker that keeps the bundle resumable after the human installs the
  dependency; refutation recording for Act; the config gate. / out of scope: #340's
  Plan-exit probe itself (a prereq, landed in the prior wave); changes to the builder
  prompt contract (it already mandates the marker + proposed row); #250's §6 reporting
  (already landed — `assemble.py:482` — this change only makes the beat cheaper before
  it).
- **External dependencies:** none
- **Test file:** template/tests/test_builder_dependency_halt.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the close fast path to reuse — `driver.py:50,71` (`_close_class`
  guard + `_do_close` call), `_do_close` `driver.py:174-181`, `CLOSE_MARKER`
  `state.py:36` and its state substitution `state.py:159`, `gates.run_close_gates`
  `gates.py:152`; the declaration parser — `assemble._declared_external_deps`
  `assemble.py:482`; 340's probe helper for running a row's detect `cmd`.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/driver.py template/src/pdca_harness/state.py` — the
  close fast path and #250's §6 item exist; no commit routes on the builder's marker;
  DISCONTINUED still reachable only via sign-off (`state.py:27`). Not fixed, not in
  flight.
- **Disposition hint:** new-feature

## Motivation

Beyond wasted cost: the honest and dishonest builder paths proceed identically today,
and the dishonest bundle looks *better* at Check. Making the honest declaration halt the
beat is what structurally rewards it — while the deterministic probe keeps the
self-report from becoming a way to skip review (the inverse failure #332 documents:
a statement driving control flow with nothing checking it).

## Design

As in the criterion. The blocked bundle is *resumable* — the human installs the
dependency and iterates, or discontinues deliberately at sign-off; every terminal
decision stays at sign-off.

## Alternatives considered

- Strict reading (no registered row ⇒ always proceed): safe but leaves the common,
  unforeseen-dependency case uncovered; the proposal-driven reading turns an existing
  prompt requirement into a load-bearing artifact with the exit code deciding.
- Halting to DISCONTINUED: wrong semantics — blocked-resume-when-provided, not
  deliberately-abandoned.

## Impact & compatibility

Opt-in for one release; `off` byte-identical. Once on, only bundles whose builder emits
the marker AND whose claim survives the probe change path.

## Open questions

- Whether the blocked halt reuses `CLOSE_MARKER` verbatim or a sibling marker so a
  resumed bundle (dependency installed, human iterates) re-enters cleanly — Do
  proposes; the resumability property in the criterion is the constraint.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.
