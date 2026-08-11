# Brief — issue 413 / merge-mode-full-check-rollup

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> The field labels below are parsed by the driver — keep the `- **Label:** value`
> shape. The success criterion is the load-bearing field: it is the sentence
> Check tests "did this work" against.

- **Slug:** merge-mode-full-check-rollup
- **Defect:** Two-part, one discipline. (Code) `merge._merge_one`
  (`template/src/pdca_harness/merge.py:42-96`) relies on `gh pr merge` to fail closed on
  "a failing required check" (`merge.py:86-88`) — which only covers checks the HOST repo
  marks required in branch protection. A host with thin protection lets a non-final wave
  PR ready+merge (`merge.py:73-82`) while its real gates are red or still running: a red
  non-required CI job or an unfinished run does not stop the merge, so the next wave
  builds on a base that never went green. (Docs) `template/docs/fork-discipline.md.jinja:46-47`
  states flatly that the automation "never marks a PR ready and never merges" — false
  under the harness's own `wave_mode = "merge"` (#279, `merge.py:73` and `merge.py:82`
  do both for non-final waves), so instances that enable merge mode inherit a discipline
  doc that no longer describes their system.
- **Success criterion:** `_merge_one` merges only a PR whose FULL check rollup is green
  at merge time: the rollup is read (also) AFTER `gh pr ready` and immediately before
  `gh pr merge` — marking a draft ready can itself trigger `ready_for_review` CI, so a
  rollup observed only pre-ready cannot guarantee green-at-merge. The gate refuses
  (non-zero return, STOP, `gh pr merge` never invoked) on any failing check and on any
  pending/queued check (wait-or-STOP, never merging past an in-flight run); refusing
  after ready is safe because a re-run resumes idempotently (`merge.py:63-65`). Rollup
  edge semantics are defined, not left to chance: an EMPTY rollup (no checks reported)
  refuses under the default — absence of evidence is not green — while skipped/neutral
  checks count as completed non-failures and do not block. A config knob
  (`merge_requires = "all" | "required"`, default `"all"`, parsed from `[driver]`)
  restores host-config semantics — including merging with an empty rollup — only on
  explicit opt-in. The fork-discipline template scopes the never-ready/never-merge
  claim: it binds the model leaves unconditionally and every final-wave PR; under
  `wave_mode = "merge"` the deterministic driver readies+merges non-final waves at the
  wave boundary, guarded by per-bundle human sign-off before publish and the check-rollup
  gate. Shipped tests assert the refusal paths.
- **Falsifiability:** RED is producible offline in the driver suite: `test_merge.py`
  exercises `_merge_one` with a stubbed `gh`; a stub whose check rollup reports a failing
  (or pending) check while `gh pr merge` would succeed makes the new test fail on current
  `main` — today nothing between the COMPLETE-state check and `gh pr ready` consults the
  rollup (`merge.py:59-82`, verified at `0fbfa26`). Environment: plain python3 + unittest,
  no network (gh is stubbed).
- **Invariant to restore:** A later wave must never build on a base whose verification is
  not green — the fail-closed rule `merge.py:11-13` already states ("the next wave must
  never build on an unmerged base") extended to its actual intent: not merely merged, but
  merged with every check passed, independent of how tightly the host operator configured
  branch protection. The harness's correctness must not hinge on per-instance host
  config. Source: merge.py's own fail-closed doctrine (`merge.py:11-17`) and the
  ready-mark gate in the discipline doc it contradicts.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 396
- **Ordering note:** conflicts-with 396 because both touch `template/pdca.toml.jinja`
  (this bundle documents the `merge_requires` knob in the `[driver]` block; 396 rewrites
  the REMOTE CONTROL comment) — schedule into different waves rather than build blind on
  the same base.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** the rollup gate in `_merge_one` (+ the `merge_requires` knob in config.py
  and its `[driver]` documentation in pdca.toml.jinja) and the scoped §2 claim in
  fork-discipline.md.jinja / out of scope: any change to the final-wave path (drafts stay
  the human's to ready), the instance-side INTEGRATION.md wording (already fixed
  downstream, getwyrd/wyrd-pdca#198), watching/polling for pending checks to clear
  (refusing is enough; re-run resumes idempotently per `merge.py:63-65`).
- **Repro instruction:** On the target checkout: `git -C ../pdca-harness show
  origin/main:template/src/pdca_harness/merge.py | sed -n '59,89p'` — the only guards
  between "bundle is COMPLETE" and `gh pr merge` are a recorded PR and `gh`'s own exit;
  no rollup read exists. For the docs half: `grep -n "never marks" ../pdca-harness/template/docs/fork-discipline.md.jinja`.
- **External dependencies:** none (`gh` is already the harness's base toolchain; tests
  stub it. Do should verify which `gh pr checks` invocation shape to use — `--json
  bucket` fields or its documented exit codes 0/1/8 — against the CLI the target's CI
  ships, and note the minimum gh version in build-notes if one applies.)
- **Test file:** template/tests/test_merge.py (append: red-rollup → refuse + no merge
  invoked; pending-rollup → refuse; all-green → ready+merge proceed; EMPTY rollup →
  refuse under `"all"`; skipped/neutral-only alongside greens → proceed; a check that
  appears pending only AFTER the ready call (the stub flips its rollup on `gh pr ready`)
  → refuse before merge; `merge_requires = "required"` → legacy behavior; and
  `merge_requires` parsed from `[driver]` in a rendered pdca.toml via the real config
  loader, not only a directly constructed Config. The instance C4 contract reverts
  production hunks and keeps appended tests, so the red leg is earned.)
- **Citations expected:** Do must cite path:line on the target branch for every change —
  `merge.py:59` (merge cmd), `merge.py:67-82` (ready+merge block), `merge.py:86-88`
  (the required-check assumption in the error text), `fork-discipline.md.jinja:46-47`
  (the flat claim), `config.py:332-336` (where wave_mode config lives, peer for the new
  knob).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/merge.py template/docs/fork-discipline.md.jinja` — #279
  (ready-before-merge, `126db1f`) and #411 (wrong-base fail-closed, `6518908`) landed;
  neither consults the check rollup, and the fork-discipline claim is unchanged since the
  doc was added (`25674df`). No open PRs; `gh search issues` finds no other rollup issue.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Confirm the commit and PR artifacts contain a user-impact opener and tracker reference for #413 — those artifacts and the rendered `contribcheck` entry point were not supplied, so the asserted gate result cannot be independently reproduced.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Confirm `commit-msg.txt` and `pr-description.md` contain a user-impact opener and tracker reference `#413` — neither artifact was supplied, so the asserted contribution-gate PASS cannot be independently reproduced and release traceability depends on that check.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
