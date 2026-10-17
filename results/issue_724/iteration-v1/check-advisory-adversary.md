# Adversarial review — issue_724 (dependency-scoped bases, #463)

The red→green evidence holds. I re-ran `tests.test_flow_dependency_scoped_bases` on the patched tree: 11/11 green. The frozen C4 red leg (`gate-logs/C4-verify.log:2229-2474`) shows all 11 failing on the unpatched source for the right reasons (Z's commits on `fix/B`, D built when it should stop, D held for #655). The tests drive the real `flow._drive_and_act` and the real `integrate.build_bundle_base`; only build, sign-off, publish and `gh` are stubbed.

The fix still breaks on three concrete inputs the tests don't cover. I reproduced each with real git, using the patch's own fixtures, against both the patched source and the unpatched source (`git archive HEAD`).

- NEEDS-HUMAN [impl] — **A re-issued run stops when a carried prerequisite was itself built on a `Conflicts with` or in-batch `Depends on (merged)` partner.** `template/src/pdca_harness/flow.py:876-880`: `_closure` follows `Depends on (merged)` edges only to bundles in `waves_of`, and `Conflicts with` edges only from and to bundles in `waves_of`. A carried (finished) bundle is never in `waves_of`. Failing case, with a history built entirely by the patched code:
  - Run 1, `[K, P, D]`: K has two commits; P declares `Conflicts with: K` (or `Depends on (merged): K`); D declares `Depends on: P`. P is correctly built on a base holding K. D's build fails, so D stays PLANNED.
  - Run 2 re-issues `[K, P, D]` to finish D. The carry carries K and P, but D's closure is just `{P}`. `build_bundle_base` then refuses, and the run prints `flow: wave 0 — could not build issue_D's base from issue_P: … It is in the published head of issue_K, which issue_D does not build on … STOPPING`. D stays PLANNED.
  - On the unpatched source, the same two runs end with D COMPLETE.
  - By the brief's Invariant, K belongs in D's base (D → P → K), and `_closure`'s own docstring (`flow.py:862-865`) says each member's edges must be followed for exactly this reason. This is not the "foreign ancestry" stop the brief accepts in (7): there, X is outside D's closure. Fix: follow a carried member's `Depends on (merged)` edges to `paths`, and its `Conflicts with` edges to carried partners (in the direction the scheduler used, or by checking the partner's head is below the member's recorded cut point). Add the case to `test_flow_dependency_scoped_bases.py`.

- NEEDS-HUMAN [impl] — **A drive-set bundle that declares `Conflicts with` a carried bundle is built without that bundle's work, and the next fold stops the run.** `template/src/pdca_harness/flow.py:910` builds `conflicts` from `waves.conflict_map(cfg, bundles)`, which keeps only drive-set names (`template/src/pdca_harness/waves.py:136-153`). `flow.py:878-880` then needs both ends in `waves_of`. Failing case:
  - Run 1, `[K, P, D, W]`: only K finishes.
  - Run 2 re-issues the batch, driving P (`Conflicts with: K`; both K and P add `shared.txt`), D (`Depends on: K`, which triggers the carry) and W (`Depends on: D`).
  - Patched: P is built on plain `main` (record cleared, `fix/P` lacks K). The wave-0 fold then fails with `issue_P's branch … does not merge cleanly … (conflicts in shared.txt) — an undeclared cross-wave overlap; declare the conflict` (it *was* declared), prints `STOPPING`, and W is never run.
  - Unpatched: P is built on the line holding K, and all three complete.
  - A carried partner comes before every wave, so it is an "earlier-wave `Conflicts with` partner … that this run … carried" in the brief's Invariant. Fix: treat carried bundles as wave −1 for conflict edges, with a conflict map that covers `bundles` plus `carried`.

- NEEDS-HUMAN [impl] — **The end-of-run rewrite check (#695) cannot see what a bundle's own base took.** `template/src/pdca_harness/flow.py:2595` passes `carried_heads` (what the *line's* folds took) to `build_bundle_base`. That function accepts a member head that fast-forwards past it (`template/src/pdca_harness/integrate.py:811-822`), returns only `(branch, tip)` (`integrate.py:860`), and nothing records the head it merged. `_report_late_rewrites` (`flow.py:2741`) only checks `carried_heads`. Failing case:
  - Batch `[A, B]`, with B declaring `Depends on: A`.
  - After the line's fold takes `fix/A` at h1, a human pushes h2 on top of it (a fast-forward, which is allowed).
  - B's base merges h2, then `fix/A` is force-pushed back to h1.
  - Result: A and B both COMPLETE, `holds == {}` (exit 0), `fix/B` holds h2, and `fix/A` no longer does. Merging B's PR lands a commit A's PR dropped, which is the #630/#633 harm this issue exists to stop.
  - Unpatched: B is cut from the line tip and never takes h2.
  - Fix: record the member heads each base build merged (say, have `build_bundle_base` return them or fill a `took` mapping like `fold` does), and include them in the end-of-run check. This touches #723's signature, so the builder may need to coordinate it.

- Test input change to confirm: `template/tests/test_flow_reissue_after_conflict_hold.py` (`test_one_the_fold_merges_after_it_is_named_too`) changes 21's `Depends on` from `12` to `12, 10`. Brief criterion (10) allows that only if `build-notes.md` names it with before and after. I can't see `build-notes.md`, so the human should check. The other restated assertions read as fair restatements to me, not weaker ones: `test_flow_slice.py` `_built_on` / `--first-parent` merge count, the moved race point in `test_integrate_carried_rewrite_late.py`, and `_built_on` in the resume and same-wave suites. Each follows the new cut point.

- Tried and could not break:
  - Removing #655's `_line_lacks_merge`. Every base, own or real, starts from a fresh fetch of the base (`integrate.py:810,830`), so a prerequisite judged by `merged_into` is on it.
  - Stub-publisher, merge and `--no-publish` modes. `bases` stays `{}`, which matches the unpatched source, where `integ` was never seeded in those modes.
  - Patchless and held members (`flow.py:911-923`).
  - The `_point_at_integration` key lookup (`flow.py:818-842`).

- Note: my first test run, before I set `PYTHONDONTWRITEBYTECODE`, left gitignored `__pycache__/` directories under `$PDCA_TARGET/template/{src/pdca_harness,tests}`. Nothing tracked was changed. My repro scripts and scratch git repos are in this leaf's sandbox (`repro/`, `base/`, `tmp/`).

<!-- pdca:leaf-complete -->
