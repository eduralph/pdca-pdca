# Design proposal — issue 317 / pdca-record

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** pdca-record
- **Kind:** enhancement (design proposal)
- **Goal:** a `pdca record [<ids>…]` verb that commits terminal result bundles to the
  instance repo (and, opt-in, opens one PR for the batch) — so a bundle's state stops
  living on one machine only. Observed: four wyrd bundles uncommitted for five days,
  including a DISCONTINUED one whose §9 was the sole provenance for an open upstream PR.
- **Success criterion:** (a) `pdca record` with no ids selects exactly the bundles whose
  `state.state` is terminal-finished — COMPLETE, DISCONTINUED, RESOLVED — and excludes
  UNPLANNED and AWAITING_SIGNOFF (halted-for-a-human) and every in-motion state;
  (b) the selected batch is staged and committed as one commit with the configured
  conventional subject; (c) `[records] mode = "pr"` additionally branches, pushes and
  opens one PR for the whole batch (git/gh stubbed in tests); (d) `mode = "off"` — the
  default — is byte-identical to today (no new behaviour anywhere, including for
  instances that do not version `results/`); (e) classification is `state.state`, not a
  re-implementation (asserted: the selection changes when the state files change,
  with no duplicated state-enumeration in the new module). Demonstrable by C4-verify;
  red on current `main` — no `record` subparser exists (verified against `cli.py`) and
  `HALTED` (`state.py:31`) has no consumer that commits bundles.
- **Falsifiability:** the offline driver suite on this host. RED now: the subcommand is
  rejected by the parser; the selection/commit assertions have no code to satisfy them.
  git/gh calls are stubbed as `template/tests/` already does for publish.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 311, 315, 316
- **Ordering note:** 316 also adds a `cli.py` subparser in the same block. 311/315 edit
  `publish.py`, which this change touches only at the "after `publish.json` is written"
  call-in point — still a shared file, so different waves. No build-on dependency.
- **Difficulty:** medium
- **Scope:** the `record` verb (new engine module + `cli.py` wiring + `[records]` config:
  `mode = off|commit|pr` (default off), `branch`, `subject`, `issue = ask|<N>`);
  selection via `state.state` ∈ {COMPLETE, DISCONTINUED, RESOLVED}; batch-by-default
  (one commit / one PR per invocation); deterministic git/gh subprocesses in the
  `publish.py` shape, no model in the loop. If publish triggers recording, the call runs
  strictly *after* `publish()` writes `publish.json` — never mid-publish. / out of
  scope: any auto-commit of non-terminal bundles; changing what publish itself does;
  retiring wyrd's interim script.
- **External dependencies:** none — tests stub git and the gh CLI; live pr-mode uses the
  gh binary the instance already requires (no backticked token on purpose: nothing new
  to register).
- **Test file:** template/tests/test_record.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the state classification to consume, not copy — `state.HALTED`
  (`state.py:31`) and the UNPLANNED/AWAITING_SIGNOFF definitions (`state.py:17-31`); the
  deterministic git-step shape to mirror — `publish.py:254-266`; the `publish.json`
  closing write that any publish-triggered call must follow; the config-table pattern —
  `[publisher]` parsing in `config.py`.
- **Prior-art check (triage cycles):** no `record` subparser in `cli.py`; `git -C
  ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/cli.py
  template/src/pdca_harness/state.py` shows no recording work; commit grep `#317` empty.
  Not fixed, not in flight.
- **Disposition hint:** new-feature

## Motivation

The driver's state *is* the files; an uncommitted terminal bundle is provenance that
exists on one machine. Manual recording is forgettable and the forgetting is silent. The
selection predicate (`state.state`) already exists and is exactly the safety property —
bundles in motion are excluded by construction, which is the argument for the engine
owning this rather than a script re-enumerating states and drifting.

## Design

Per the issue's three learned-by-hand points: trigger on *terminal* (COMPLETE,
DISCONTINUED, RESOLVED), not "published"; if hooked to publish, run after the
`publish.json` write; batch by default (wyrd's own history records 4–6 bundles per PR).

## Alternatives considered

- Instance script: reimplements `state.state` and drifts (the RESOLVED-guard defect in
  wyrd was exactly two such enumerations drifting).
- Per-bundle PRs: noise, and collides with one-issue-per-PR instance rules.

## Impact & compatibility

`mode = "off"` default keeps every existing instance unaffected. Same engine/instance
split as `[publisher]`.

## Open questions

- `issue = "ask"` interaction in headless contexts (flow) — presumably skip PR mode and
  report; Do proposes.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.
