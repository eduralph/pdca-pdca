# Brief — issue 474 / base-export-reaches-only-the-per-fix-verifier

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** base-export-reaches-only-the-per-fix-verifier
- **Defect:** The per-fix base export is broadcast to **every** gate row of a Check run, not
  only to the row that consumes it. `gates._run_one` sets exactly one of `PDCA_BASE` /
  `PDCA_VERIFY_BASE` / `PDCA_BRIEF_BASE` whenever `bundle is not None`
  (`template/src/pdca_harness/gates.py:525-536`), and `gates.run_gates` passes `bundle=d` for
  **both** scopes (`:197` — `scopes=("repo", "bundle")`). So a repo-scoped whole-suite row, a
  docs-lint row, the T4 contribution row and a C5 lens all run with a bundle-scoped base in
  their environment; `_merged_env` then merges it into the subprocess, and any env-sensitive
  suite in the target reads it as though the driver had set it for *them*.
  Observed on this instance: T3 went red **exactly and only** on the two stacked bundles of a
  37-cycle corpus (issue_419, issue_457) — `results/issue_457/gate-logs/T3-suite.log`, 11
  failures, all `test_verify_base.VerifyBaseExport`, all
  `AssertionError: 'origin/pdca-integration/main' != 'UNSET'`, with the root suite green in the
  same run; the reviewer reproduced it only with `PDCA_VERIFY_BASE` in the ambient environment
  (`results/issue_457/SUMMARY.md` §5). It is very likely also (part of) the recurring
  "unclassifiable T3 driver-suite red" that instance chased across the 2026-08-05/06 Act
  reviews — unreproducible by hand, because a hand rerun exports nothing.
  **Correction to the issue text, verified on the target base:** the issue names two layers.
  Layer 2 (`VerifyBaseExport` was not hermetic against an ambient base) **has since landed** —
  `setUp` now snapshots the environment and pops all three vars
  (`template/tests/test_verify_base.py:91-103`, `_BASE_VARS` at `:42`), in commit `96c9704`.
  So the *observed* red no longer reproduces through that particular suite. Layer 1 — the
  driver broadcasting a bundle-scoped base to rows that never asked for it — is untouched, is
  the half the issue says must be fixed regardless ("fixing only (2) still leaves repo-scoped
  gates of any instance running with a bundle-scoped base in their environment"), and is this
  slice. Note also that the leak is **not** specific to stacked bundles: rung 3
  (`PDCA_BRIEF_BASE`, `:534-536`) is exported on *every* ordinary cycle, so a fix that only
  suppressed the stacked export would guard the symptom that happened to be observed.
- **Success criterion:** With the patch, in a bundle-scoped gate run (`gates.run_gates`) for a
  bundle in **any** of the three base postures — an `Onto branch` brief, a stacked bundle with a
  stack-base marker, and an ordinary wave-0 bundle:
  (i) the gate command of a row that is **not** the per-fix verifier observes **none** of
  `PDCA_BASE` / `PDCA_VERIFY_BASE` / `PDCA_BRIEF_BASE` — repo-scoped rows and bundle-scoped
  non-verifier rows alike;
  (ii) the per-fix verifier row still receives **exactly one**, resolved by today's unchanged
  ladder (`Onto branch` > wave integration base > brief base), with the same fully-qualified
  `<remote>/<branch>` value it gets today;
  (iii) an instance whose C4 row predates this change does **not** silently lose its base — the
  compatibility rule is explicit, documented, and asserted by a case of its own;
  (iv) nothing else about the gate environment changes: `PDCA_BUNDLE`, `PDCA_WORKTREE` and
  `PDCA_LANE` are still exported to every row, and `host_ci` rows keep the environment they have
  today.
  Demonstrable by C4-verify: `template/tests/test_verify_base.py` already runs `gates.run_gates`
  against a stub config whose gate row echoes all three variables into a file
  (`_ECHO_BASES`, `:45-51`; `_recorded_bases`, `:115-121`), so (i)-(iv) are assertions over
  what the subprocess actually saw.
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  network, no services — in the target checkout Do is given. Add a **second** row to the stub
  config (the same echo command, declared as a non-verifier — one repo-scoped, one
  bundle-scoped) and assert it records `UNSET/UNSET/UNSET`: today it records the bundle's base,
  so the case fails, and that failure is the red. The existing hermetic `setUp` (`:91-103`)
  guarantees the ambient environment cannot mask either leg. C4's red leg reverts `gates.py`
  and keeps every `template/tests/*.py` hunk (`engine/scripts/run-verify.sh:214-217`), so cases
  appended to this module earn a genuine red.
  **One gate-evaluability trap to respect:** since #507 (`1d6df79`), `test_verify_base.py:293-…`
  and `test_verify_red_leg.py` string-match the wording of the **skeleton**
  `template/engine/scripts/run-verify.sh` — including "Resolve as: $PDCA_BASE >
  $PDCA_VERIFY_BASE > your own override > $PDCA_BRIEF_BASE" — in the template-checkout posture.
  If this slice edits that skeleton's ladder prose, those cases must be updated in the same
  patch, or the T3 row goes red for a reason that has nothing to do with the fix.
- **Invariant to restore:** A gate row's environment carries only the context of **its own
  scope**: the per-fix base contract — the ladder `PDCA_BASE` / `PDCA_VERIFY_BASE` /
  `PDCA_BRIEF_BASE`, whose whole purpose is telling a per-fix verifier which base to reconstruct
  before applying `patch.diff` — belongs to the row that performs that verification, and no
  other row may observe it. Quantified over the category, not the observed failure: it covers
  all three variables, all three postures (including the unconditional `PDCA_BRIEF_BASE` every
  ordinary cycle exports) and every non-verifier row, so a patch that merely stopped exporting
  `PDCA_VERIFY_BASE` to repo-scoped rows visibly fails it. Self-test: it cannot be satisfied by
  guarding one module — the suites of *any* target are downstream, which is why the fix is
  driver-side. Source: internal project invariant (Tier C) — the target's own written contract
  at `gates.py:495-524` ("the base a **per-fix verifier** must reset to… exactly one is set for
  every bundle-scoped gate invocation", #54/#273/#387) and the C4 skeleton the harness publishes
  to every instance, `template/engine/scripts/run-verify.sh:29-34`, which introduces all three
  variables as "the base to reset to before applying patch.diff" and nothing else.
  `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6 category gate
  applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves — and a
  wave > 0 bundle in this very instance is what **this** bug false-reds, so the fix must not be
  scheduled behind the defect it removes. Ordering lives in the run boundaries. Issue 507, which
  also edits `template/tests/test_verify_base.py`, is already **merged** on the target base
  (`1d6df79`, PR #518) — the run-1 prerequisite the plan names is satisfied, and its
  posture-skipping additions are what the Falsifiability trap above refers to. If this slice
  documents a new `[[gates.checks]]` row key in `template/pdca.toml.jinja`, that hunk lands in
  the `[gates]` block, far from the `[driver]` hunk issue 462 adds in the same run — a
  distant-hunk same-file pair the human merges in number order.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** `gates._run_one`'s base export: deliver the ladder's one resolved value to the
  per-fix verifier row and to nothing else, and make how a row is recognised as that verifier
  **explicit and declared** rather than inferred from scope (this instance's own T3 row is
  bundle-scoped, so scope alone does not separate them). Ship the compatibility rule with it:
  a rendered instance that has not re-declared its C4 row must not silently lose the base — a
  silent loss would reverse the guarantee of #54/#273/#387 (the test base and the deploy base
  must not diverge) and would be far worse than the leak. Document the row-level contract where
  `[[gates.checks]]` keys are documented (`template/pdca.toml.jinja`'s `[gates]` block) and in
  the C4 skeleton's ladder comment if that file's asserted wording permits (see Falsifiability).
  Do decides the declaration's shape and states the compatibility rule in `build-notes.md`; it
  is the human's call at sign-off. **Out of scope:** `template/tests/test_verify_base.py`'s
  hermeticity (already fixed, `:91-103`) and any other suite's env handling; `PDCA_BUNDLE` /
  `PDCA_WORKTREE` / `PDCA_LANE`, which every row legitimately needs; the worktree
  reconstruction (`worktree.for_gate`, `gates.py:369`) — it already resolves the base itself and
  must keep doing so; `host_ci` rows; the publish-time gate re-run; this instance's own
  `pdca.toml` and `engine/scripts/*` (a different repo — `docs/INTEGRATION.md` §2 keeps instance
  changes outside the cycle).
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. Read `gates.py:525-536` beside `gates.py:189-197`: the export is keyed on
     `bundle is not None`, and `run_gates` passes the bundle for `scopes=("repo", "bundle")` —
     so every configured row of a Check run receives one of the three variables.
  2. Make it visible: add a second row to `_ECHO_BASES`-style stub config in
     `tests/test_verify_base.py` (one repo-scoped, one bundle-scoped) and print
     `_recorded_bases` for a bundle with a stack-base marker — both rows report
     `origin/pdca-integration/main`, though only one of them is a per-fix verifier.
  3. Historical evidence of the consequence: this instance's
     `results/issue_457/gate-logs/T3-suite.log` (11 `VerifyBaseExport` failures,
     `'origin/pdca-integration/main' != 'UNSET'`) and `results/issue_457/SUMMARY.md` §5.
- **External dependencies:** none — the gate runner is driven in-process against a stub config
  whose row is a shell echo, so the slice builds and goes red→green on the base toolchain.
- **Test file:** `template/tests/test_verify_base.py` — append to the existing suite. It already
  owns this contract ("a bundle-scoped gate is told exactly one base"), its `setUp` is hermetic
  against the ambient environment, and its `_ECHO_BASES` row records what the subprocess really
  saw. C4's red leg keeps all `template/tests/*.py` hunks and reverts only `gates.py`, so
  appended cases earn their red.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * the ladder and its mutual exclusivity live at `gates.py:495-536`; keep the resolution order
    and the fully-qualified `<remote>/<branch>` shape exactly as they are — only *who* receives
    the value changes;
  * a per-row declared behaviour already exists to mirror: `at_publish` (`gates._deferrable` /
    `template/pdca.toml.jinja`'s T4 row comment) is a row-level key whose default is *derived
    from `scope`* and can be set explicitly in either direction — the same shape solves the
    compatibility half here;
  * `_run_checks` (`gates.py:388-400`) is where per-row decisions are made with both the row and
    the config in hand.
  A regression test must not import a symbol this patch introduces at module level: C4's red leg
  reverts production first, and a module that then fails to import is recorded
  `PDCA-UNVERIFIABLE`, not red (`engine/scripts/run-verify.sh:231-234`) — declare any new row
  key as data in the stub config's dict, not as an imported constant.

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/gates.py` — `e79d109` (#387, the `PDCA_BRIEF_BASE` rung),
  `2ef3e28` (#273 review, `Onto branch` wins), `8e9b5fb` (#273, the original
  `PDCA_VERIFY_BASE`), plus `5c7d010`/`07766ed`/`56250bb`/`1ed6868` (verdict recording). Every
  one *adds* to the ladder; none narrows who receives it.
  `template/tests/test_verify_base.py` — `1d6df79` (#507, posture skips) and `96c9704` (the
  hermetic `setUp`, layer 2 of this issue). `gh pr list -R eduralph/pdca-harness --state open` →
  **no open PRs**. Open issues searched: #441 (nothing checks that every configured gate has a
  runner) and #371 (a transient red on a gating row) touch the gate layer but neither is this;
  #507 is closed/merged. Not previously attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
