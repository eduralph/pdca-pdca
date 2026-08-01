# Design proposal — issue 311 / host-ci-gate

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** host-ci-gate
- **Kind:** enhancement (design proposal)
- **Goal:** the harness can express "host CI jobs the delegated gate runner does not
  cover" — an instance declares host-only CI commands and the cycle runs them against
  the tree with `patch.diff` applied, before publish pushes anything, so a bundle can
  no longer pass Check green and open a PR that immediately fails a required status
  (observed four times in the wyrd instance, always the `typos` job: getwyrd/wyrd#595,
  #564, #569, #394).
- **Success criterion:** with a declared host-CI command configured, (a) a command that
  exits non-zero against the patched tree blocks publish — no branch is pushed, no PR is
  opened — and the failure is recorded with the command named; (b) a command that exits 0
  leaves publish behaviour unchanged; (c) an instance that declares nothing is
  byte-identical to today. Demonstrable by C4-verify: the shipped unit test asserts all
  three against a stub command, red on current `main` (publish today consults only
  `_t4_passes`, which runs with `cwd=cfg.root` *before* the patch is applied — verified at
  `template/src/pdca_harness/publish.py:101` and `:187-192`).
- **Falsifiability:** the offline driver suite on this host
  (`cd template && PYTHONPATH=src python3 -m unittest template/tests/...`). RED is
  producible now: a test that configures a failing declared host-CI command and asserts
  publish refuses fails on current `main` because no such configuration key exists and
  publish pushes regardless. No live CI or GitHub needed — publish's git/gh subprocesses
  are stubbed the way `template/tests/` already stubs them.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 315, 317, 368
- **Ordering note:** 315 and 317 also modify `publish.py` (315 inserts a pre-publish
  review stage in the same seam; 317 hooks after `publish.json` is written) — schedule in
  different waves. 368 modifies `gates.py`'s run machinery (`_run_one` / timeout), which
  this change is likely to reuse for the host-CI run — different waves, no build-on
  dependency.
- **Difficulty:** medium
- **Scope:** proposal 1 of the issue only — a declared list of host-only CI commands
  (instance config, e.g. a `[gates.host_ci]`-shaped table; exact key naming is Do's call)
  that the harness runs as a pre-publish gate against a tree with `patch.diff` applied
  (isolated worktree, the same machinery the verify leg / bundle-scoped gates already
  use), closing the T4 slot's pre-apply blindness. / out of scope: proposal 2 (the
  composition audit that parses the host's workflow files and warns about uncovered
  always-on jobs) — file it as its own follow-up if wanted; also out of scope: any change
  to the wyrd instance itself (already worked around host-side via getwyrd/wyrd#599).
- **External dependencies:** none
- **Test file:** template/tests/test_host_ci.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the pre-push T4 gate seam this composes with — `publish.py:187-192`
  ("the artifacts MUST pass before anything is pushed", `_t4_passes` at `:101`); the
  bundle-scoped gate execution to mirror for "run a command against the patched tree" —
  `gates.py:409` (`_run_one` → `progress.run_with_heartbeat`).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/publish.py template/src/pdca_harness/gates.py` — no
  host-CI/pre-publish-gate work; commit-message grep for `#311` empty; `plan_policy.py`
  (#321/#333) is pre-dispatch policy, not pre-publish. Not fixed, not in flight.
- **Disposition hint:** new-feature

## Motivation

The instance's only CI-parity gate delegates wholesale to the host's single-sourced
runner. A host that keeps *any* always-on CI job outside that runner (spell-check, docs
lint) has a structural blind spot: the T4 gate runs before the patch is applied so it
cannot see prose that arrives in the patch, and the C4 re-gate covers exactly what the
delegated runner covers. Result: Check green, PR opens red. wyrd fixed it host-side only
because the host was willing to change its runner; the harness still cannot express the
gap for any other instance.

## Design

An instance-config list of host-only CI commands. The driver runs them as a gate against
a worktree with `patch.diff` applied (reusing the existing bundle-scoped worktree/apply
machinery), at a point where a failure still blocks the push — either as a new
bundle-scoped gate class at Check or as a publish-time pre-push step; Do decides the
seam, with the constraint that the *record* of a failure must land where sign-off/§6 can
see it, and that publish must not have pushed anything when it fires. Empty list ⇒ no
behavioural change anywhere.

## Alternatives considered

- Extending the host's runner (what wyrd did): fixes one host, not the harness's
  expressiveness gap; requires host cooperation.
- Running the commands inside T4 as-is: T4 runs `cwd=cfg.root` pre-apply; the failing
  content is in the patch, so it structurally cannot catch this.

## Impact & compatibility

Additive config; no key declared ⇒ byte-identical behaviour. New gate results appear only
for instances that opt in.

## Open questions

- Whether the run belongs in Check (visible to the reviewer/§6) or immediately pre-push
  in publish (freshest tree). Default to Check-visible if both are cheap.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the advisory findings (brief unchanged): 1. C5 — stale-base certification (the substantive defect): the publish-leg host-CI run reuses a warm gate worktree that deliberately does not fetch (worktree.py:238) while the push path fetches afterward (publish.py:270); reviewer reproduced host CI green on the stale base but red on fetched base + patch, so the gate can certify a tree other than the one pushed. Fix: the pre-push host-CI reconstruction must fetch/pin the same base commit the push will use, with a test covering the base-advanced-since-Check case. 2. C3 — non-zero bypasses: the brief's criterion (a) says a non-zero command blocks publish, but exit 77 and gating=false rows publish anyway (publish.py:780). The human did not bless these carve-outs this round; the rebuild should either make every non-zero declared command block publish per the brief's letter, or surface the carve-out question explicitly for sign-off rather than shipping it as a default. Note: the reviewer's C4 FAIL appears to be an oracle-path artifact (it ran the target's template skeleton run-verify.sh, not the instance's configured gate, and itself confirms the test module is red->green); the deterministic C4 gate passed.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — /tmp/tmpo3p54blm/results/issue_500/split-proposal.md
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
