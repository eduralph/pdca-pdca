# Adversarial review — #738 (iteration 3)

The red→green proof holds, and I could not break the fix itself. One gap is real: a line the patch adds does work but no test pins it.

## Evidence, re-run

- I re-ran C4 myself. `template/tests/test_flow_bundle_base_holds.py`: 15/15 fail with the production files reverted (`git checkout -- template/src`, test file kept) and 15/15 pass with the patch. Every red-leg failure is the `assertNotIn("STOPPING", …)` at `test_flow_bundle_base_holds.py:303`, so each case goes red because the run stops, which is the defect. The eight suites the brief names, plus `test_integrate_carried_rewrite_late`, pass on the patched tree (161 tests).
- The tests run the production path. They call `flow._drive_and_act` and stub only git calls and the model leaves. The fetch failure runs the real `integrate._prepare_worktree` with only `git fetch` returning 1 (`test_flow_bundle_base_holds.py:223-233`), so the real `_FetchFailed` (`integrate.py:2111`) is what the wrapper at `integrate.py:862-874` sees. The push refusal fires the real raise at `integrate.py:921`. No stub replaces the `except` the fix adds (`flow.py:1041-1045`).
- Because every red leg fails at that first assertion, the red leg proves nothing about the later logic: the stale-PR check and the end-of-run re-read. I mutation-tested that logic instead. Five of seven mutations are caught. The two that survive are below.

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:3018` (`base_rewrites.clear()`) is not pinned by any test. Replacing it with `pass` leaves all 94 tests green across `test_flow_bundle_base_holds`, `test_flow_dependency_scoped_bases`, `test_integrate_carried_rewrite_late`, `test_flow_carried_prereq_bases`, `test_flow_merged_prereq_dependency_base` and `test_integrate_bundle_base`. The one test meant to cover it, `test_a_rewrite_mended_before_the_next_fold_fails_nothing` (`test_flow_bundle_base_holds.py:580-602`), ends the same with or without the line. The line matters, and here is the failing case (probe P1): `A`,`Z` / `B` dep `A`, `W` dep `Z` / `V` dep `W`.
  1. `fix/A` is force-pushed after fold 0, so `B` is held.
  2. `fix/A` is restored before fold 1, so fold 1 passes.
  3. `fix/A` is force-pushed again after fold 1, and wave 2 is the last wave.

  With the patch as written, the end-of-run check names A's rewrite: `holds={'B':'base','A':'rewritten'}`, exit **1**. With the line removed, A stays excluded from `_report_late_rewrites` (`flow.py:3056`), the second rewrite is reported nowhere, and the run exits **3**. Add P1 as a test.

  In the same function, `if not on: continue` (`flow.py:1122-1123`) is also unpinned. Probe P3: only `A` carried with a PR-less lost head, `B` held for its rewrite, every fetch failing at the end. Without the guard, the run adds `'A': 'unchecked'` and prints `flow: could not read issue_A's branch … these PRs may hold commits it no longer has: .` with an empty PR list. With it, neither appears. One assertion on `holds` in such a case would pin it. Both are test-only changes. The production code is correct.

## Notes (checked, not filed)

- Known limit, not new in this diff: a rewrite hold in a wave that is not the last still loses later waves. Probe P2 is case (2) plus `V` dep `W` in wave 2. `B` is held, `W` is COMPLETE, then the fold after wave 1 refuses `fix/A` (#633, `integrate.py:549`), prints `STOPPING`, and leaves `V` PLANNED. Brief case (2) is still met (the unrelated bundle in B's wave is COMPLETE). The test docstring says this plainly (`test_flow_bundle_base_holds.py:13-20`), and earlier rounds likely deferred it.
- An existing #695 assertion was flipped: `test_integrate_carried_rewrite_late.py` (1d) now expects exit 3, not 1. So "the line carries commits fix/A lost, no PR holds them" exits 3 when a base build saw the rewrite first, and 1 when only the end-of-run check sees it. The brief chose this ("cases (1)-(4) … exit 3"), and `cli.py:714-727` documents it. It is a deliberate choice, not a slip.
- Refutation attempts that failed:
  - A `KeyError` in `_report_stale_prs` on `dirs[m]` or `dirs[o]`: members come only from `built` = `accepted` (`flow.py:998`), and PR owners from `pushed` ⊆ `accepted` (`flow.py:1163`).
  - A dirty shared integration worktree after a base fails mid-merge: every base build and fold resets first (`integrate.py:891`, `:614`), and case (1) builds W's base right after B's clash.
  - A lock leak: `integ_lock` is a `with` block (`integrate.py:853`).
  - A `Conflicts with` partner in the held bundle's own wave: `compute_waves` never puts two partners in one wave.
  - `Stacks on` a held bundle: `declared_deps` includes it, so that bundle is skipped.
  - The `clear()` firing without fix/A being re-read on a multi-target run: `fold` checks every carried branch across all target groups before any merge (`integrate.py:549`).
  - Mismatched fix messages: each of the three raises in `_prepare_worktree`/`_fetch` now maps to its own fix (`integrate.py:863-871`).

<!-- pdca:leaf-complete -->
