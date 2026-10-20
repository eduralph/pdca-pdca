# Advisory code review — issue_739 (hold a cross-wave clash at the line fold)

Scope: `patch.diff` against `$PDCA_TARGET` (patch applied there). Gates: C4 pass (red pre-fix, green post-fix), C5 pass, T2 pass, T3 pass (2631 tests OK, `gate-logs/T3-suite.log`). I found no correctness bug I could confirm. The fold change, the new `_held_on_line` / `_together` / `_rebuilt` helpers and the `_runnable` / announce wording look right for the cases the brief and the three earlier rounds name. Tests exist for each probe from rounds 1-3 (main moved twice, a base commit main later undid, an older tip of a prerequisite, the `Conflicts with` partner X of a stranded hold). What is left is small cleanup and one unconfirmed edge case. None of it blocks.

## Correctness

- `template/src/pdca_harness/integrate.py:1896-1897` — the stranded-vs-past split is not symmetric. A partner counts for either one only if it fails on `held` *in a file `head` clashes with it in* (`set(fails_on(held, n)) & set(files)`). It then counts as `stranded` if `fails_on(base_ref, n)` is non-empty in *any* file. So a partner that merges onto the current base in the clash file, and fails there only in some unrelated file (main moved again elsewhere), would be called `stranded`. The held bundle's line would then tell the partner's owner to rebuild, when the clash-file fix is "update the held branch from the base" (`past`). I did not run this case, so it may not be reachable in practice. A one-line fix is to intersect with `files` on the second trial too: `set(fails_on(base_ref, n)) & set(files)`. No NEEDS-HUMAN tag, because I have not shown that it happens.
- `template/src/pdca_harness/integrate.py:663-671` — the cross-wave hold records `held_out[d.name]` from partners found against `took`. If a later pass of the same `fold` loop took one of those partners back off the line (`_hold_work`, `:695-699`), the record would go stale. Today this cannot happen: the in-run fold that passes `held_out` passes no `skipped` (`flow.py:3120-3126`), so the restart loop never runs together with a hold. #674's same-wave hold has the same pattern, so I am noting it, not filing it.

## Reuse / simplification / efficiency

- `template/src/pdca_harness/integrate.py:2120-2155` — `_rebuilt` copies `_trial`'s setup and teardown almost line for line (`:2080-2117`): read the tip, `checkout --detach`, then in `finally` call `_reset_tree`, check out `branch` again, and raise `_LineBroken` if the tip moved. A small context manager (e.g. `_detached(wt, branch, onto)`) shared by both would remove about 15 duplicated lines and keep the two error messages from drifting apart. Optional.
- `template/src/pdca_harness/integrate.py:1952-1967` — `_together` costs O(n) trials per round, each merging up to n revisions, plus one `_rebuilt` per round. With n bundles on the line that is roughly cubic in the worst case. It runs only after a fold merge has already conflicted, so this is not a hot path, and the round-1/round-2 findings asked for this minimal-set search. Worth a short comment saying the cost is accepted, in case lines get long.
- `template/src/pdca_harness/integrate.py:1904-1910` — `holds_some` runs `git rev-list` twice and compares list lengths. `rev-list --count` (or one `rev-list heads[n] ^head …` checked for being shorter than the full count) would avoid building both lists. Very minor.

No NEEDS-HUMAN items: the findings above are advisory cleanups or unconfirmed edge cases, and none needs a scope or architecture decision.

<!-- pdca:leaf-complete -->
