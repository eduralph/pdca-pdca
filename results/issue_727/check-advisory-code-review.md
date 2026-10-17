# Advisory code review — issue_727 (flow-in-batch-dependency-scoped-bases)

Lens: bugs the patch adds, plus reuse / simplification / efficiency. I read the patched source at `$PDCA_TARGET` (it has the patch applied). Gates: C4 (red before the fix, green after) and T3 (2581 tests, OK) pass.

No correctness bug found that needs a human. These are the spots I checked and found sound:

- `_closure_members` (`template/src/pdca_harness/flow.py:913-957`): the walk only goes through bundles this run built. It checks for finished bundles before it checks `built`, so a carried edge always falls back to the line. The wave filter on `Conflicts with` partners matches what each member's own base held when it was pointed. A patchless node that was itself put on a seam is re-detected because the walk follows the same edges, so checking `seams` only against `members` is enough.
- `wave_of[d.name]` (`flow.py:2687`) cannot raise `KeyError`. `accepted` is only extended at `flow.py:2754`, and `wave_of` is updated right after.
- A dry run cannot push a base. `own_bases = hold_unmerged` (`flow.py:2616`) excludes the `stub` publisher, which is exactly when `dry` is true (`flow.py:2762`).
- When a base build stops the loop (`flow.py:2692-2697`), `line_stopped` is not set. The run still exits 1, because that wave's bundles stay non-terminal (`cli._results_rc`). The end-of-run check skips only the branch the `_Rewritten` stop already reported.

Minor, non-blocking notes:

- `template/src/pdca_harness/flow.py:998` changes `exc.args` on the caught error to add the bundle name. `str(exc)` changes, but `exc.cause` (set in `IntegrationError.__init__`, `integrate.py:98`) still holds the old, unprefixed text. Nothing on this path reads `cause` today, so nothing breaks. Raising a new error of the same type `from exc` (and keeping `_Rewritten.name`) would avoid the mismatch if anything reads `cause` later.
- `template/src/pdca_harness/integrate.py:1249-1255` repeats the "judge each head once" loop of `_lost` (`integrate.py:1077`). The only difference is that it keeps git errors per head instead of raising. One helper with a `collect_errors` switch would remove the copy. This is a cleanup, not a bug.
- `template/src/pdca_harness/integrate.py:1147` and `integrate.py:1286` both build the sentence "every PR this run cut from <line> after it took <head> (<owners>)". A shared helper would keep the fold stop and the end-of-run report from drifting apart.
- `template/src/pdca_harness/integrate.py:1264-1266`: the line report's PR list keeps a PR whose head git could not judge (`judged[h2]` is an `IntegrationError`, which is not `None`). Such a PR is named under "they hold commits <ref> no longer has", which is not proven. Erring toward listing it is the safe direction, so this is wording only.
- Efficiency: `_heads_taken` is rebuilt three times per wave (`flow.py:2691`, `:2790`, `:2840`). `_bundle_bases` recomputes `waves.conflict_map` and `_fold_candidates` over everything built so far, every wave. All of this is small next to the git work, so there is nothing to fix.

Neither lens found anything that needs a human decision.

<!-- pdca:leaf-complete -->
