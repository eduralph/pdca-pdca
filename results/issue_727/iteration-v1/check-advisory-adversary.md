# Adversarial review — issue_727 (dependency-scoped bases)

I re-ran the red→green proof myself. On a copy of the target with `template/src` reverted to `fcae4aa`, 11 of the 15 new tests fail. On the patched tree all 15 pass. The 4 that pass both ways are the seam tests, (6), which by design pin today's behaviour. The tests drive the real `flow._drive_and_act` and the real fold and base build. Only the build, the sign-off and publish are stubbed, as the brief allows. So the evidence is real, and the closure walk was right in every case I built. I found two report gaps the builder can fix, one test gap, and one design question. All probes ran in scratch copies inside this sandbox and nothing was written to the target.

## Findings

- NEEDS-HUMAN [impl] — The line's report names too few PRs, and claims none are affected when some are. The filter `had.get(name) == took` at `template/src/pdca_harness/flow.py:1042` keeps only bundles cut from the line after it took the branch's **latest** head. When nothing passes that filter, the end-of-run text at `template/src/pdca_harness/integrate.py:1278-1281` says "no PR this run cut from <line> after it took <head> holds them".
  - **Failing case (run on the patched tree):** `A`; `S` (`Stacks on: A`, a seam, cut from the line while it held a1); `B` (`Depends on: A`); `C` (`Depends on: B`). While `S` builds, `fix/A` fast-forwards to a2, and the fold after wave 1 takes a2. While `C` builds, `fix/A` is force-pushed to a commit that holds neither a1 nor a2.
  - **Result:** `fix/S` still holds a1, which `fix/A` no longer has. The report says no line PR holds the old commits and never names `issue_S`. Only `issue_B` and `issue_C` are named.
  - **Why it matters:** brief (7) asks for the line's report to name the PRs cut from the line. The same filter feeds the fold's stop message (`_rewrite_stop`) and the "(none)" text in the `unchecked` report (`flow.py:2926`).
  - **Untested:** with the `had.get(name) == took` condition deleted, all 100 tests in the bundle's eight suites still pass. One fix is to name every line-cut PR whose recorded head the branch's current tip no longer contains.

- NEEDS-HUMAN [impl] — When a later bundle's base build catches a rewrite, the run stops with the line-only remedy, and the end-of-run check is skipped. The `_bundle_bases` error sets `line_stopped = True` (`template/src/pdca_harness/flow.py:2714`), which turns off the #695 check (`flow.py:2864`). The refusal text comes from `build_bundle_base` (`template/src/pdca_harness/integrate.py:833-841`). It names only the line's head and says "Restore … then re-run".
  - **Failing case:** `A`; `B` (`Depends on: A`, on its own base); `S` (`Stacks on: A`, on the line); `C` (`Depends on: B`). `fix/A` is force-pushed after the fold that follows wave 1.
  - **Patched result:** the run stops at `C`'s base. Neither `issue_B`'s PR (its base took the old head) nor `issue_S`'s PR is named as holding lost commits, and `holds == {}`.
  - **On `fcae4aa`, same case:** `C` is built, and the end check reports `A` rewritten with "rebuild those PRs", setting `holds == {"A": "rewritten"}`.
  - The fold's own stop (`_rewrite_stop`) names each base and PR. This third stop point does not.

- NEEDS-HUMAN [impl] — A guard in the closure walk has no test. At `template/src/pdca_harness/flow.py:965`, `if not prereq and wave is not None and built[n][1] >= wave: continue` keeps out a member's `Conflicts with` partner that was built after that member. With the guard deleted, all 100 tests in the bundle's suites still pass.
  - **A case that catches it:** `A`; `E` (`Conflicts with: A`); `Y` (`Depends on: A`); `D` (`Depends on: Y`). On the patched code `fix/D` correctly lacks `fix/E`'s own commit. With the guard removed, `fix/D` holds it — the #630 bug in another shape.
  - Add this as a test.

- NEEDS-HUMAN [human] — Per-bundle bases start from a freshly fetched `origin/main`, so each dependent's branch brings mid-run main commits into the line. Before this change, the line never took those in (flow.py:738 states that the line does not follow the base). `build_bundle_base` fetches the base fresh (`integrate.py:829`) and starts the branch from it (`integrate.py:849`).
  - **Failing case:** `A`, `Z` (wave 0); `B` (`Depends on: A`); `C` (`Depends on: B`). After the wave-0 fold, `main` gets a `z.txt` that differs from `Z`'s.
  - **Patched result:** `B` is built, and the fold after wave 1 stops: "issue_B's branch … does not merge cleanly … (conflicts in z.txt) — an undeclared cross-wave overlap; declare the conflict" (`integrate.py:1322`). That blames `B` for a clash between `main` and `Z`; `B` and `Z` share nothing.
  - **On `fcae4aa`:** all four bundles finish.
  - Without any conflict, I confirmed the line now picks up `main`'s new commit through `B`. On `fcae4aa` it does not.
  - A related case: if `main` changes `A`'s file mid-run, the run stops at `B`'s base build. On `fcae4aa` it continues. That part falls under #725 ("holds for base-build failures"). The misattributed line stop above does not.
  - **Decision needed:** should per-bundle bases start from the commit the line started from, which means changing #723's `build_bundle_base`, or is this accepted?

- NEEDS-HUMAN [human] — Several restated tests change test inputs or test setup, not just assertions. The brief lists exactly this as a reason v1/v2 were rejected, and (8) requires each change to be in `build-notes.md`, which I cannot see.
  - `template/tests/test_flow_reissue_after_conflict_hold.py:246` gives `21` a new declared edge (`on="12, 10"`). The old scenario relied on `21` picking up `10` from the line, which is the bug being fixed.
  - `template/tests/test_integrate_carried_rewrite_late.py:283` moves case (1c)'s rewrite from the line's push to `B`'s base push. The old timing is kept as a new test with a new expected outcome: the run now stops.
  - `template/tests/test_flow_slice.py:1638` narrows the "EA merged once" count to `--first-parent`, because the line's history now holds `B`'s base merge of `EA` too.
  - Each change looks justified to me. Please confirm all three are listed with before and after.

## Attempts that did not refute the fix

- Diamond (`D` depends on `B` and `C`, both of which depend on `A`): `D`'s base builds cleanly and holds `A`, `B` and `C` but not `Z`.
- (6b), and the transitive walk through a bundle with no patch: both behave as the brief says.
- `Onto branch` and `Stacks on` seams: each is guarded twice, by the brief check (`flow.py:951-954`) and the member check. Deleting the member-on-the-line seam (`flow.py:974`) is caught by an existing resume test.
- Publish: real `publish.publish` never runs against a per-bundle base, because every test stubs it. The brief allows this, and production treats any `stack-base` the same way (`publish.py:236-366`), so I don't count it as a refutation.

<!-- pdca:leaf-complete -->
