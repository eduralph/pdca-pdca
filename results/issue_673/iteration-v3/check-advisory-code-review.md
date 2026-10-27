# Advisory code review — issue 673 (correctness + reuse/simplification)

Both lenses come out mostly clean. The new check is wired in at the right place:
`_merge_published` reads the tip before the merge (`template/src/pdca_harness/integrate.py:693`)
and calls `_keep_merge` on a clean merge (`:698-700`). It reuses the #623 helpers
(`_undone_paths`, `_reset_line`) and does not copy them. The message builder that was
duplicated is now one helper, `_removed` (`:853-862`), so the base-merge wording stays
byte-identical (`:841-847`). The gates are green: C4 is red without the fix (11 of 14 new
tests fail) and green with it, and T3 ran 2490 tests OK. The "FAILED" lines in
`gate-logs/T3-suite.log` come from tests that simulate leaf failures, not from real failures.

I found no blocking correctness bug. Minor notes:

- `template/src/pdca_harness/integrate.py:727-731`: if `_undone_paths` hits a plain git
  read failure (`_out` at `:870`, or `_in_line` at `:1027`, both raise a plain
  `IntegrationError`), `_keep_merge` resets the line and re-raises. Under the carry's
  `skipped`, `fold` (`:578-583`) then records that bundle as skipped with a "could not
  read …" message instead of stopping the run. The line stays safe because the merge is
  undone. But a broken checkout can show up as a bundle quietly skipped, and every later
  bundle whose check fails the same way gets skipped too. `_take_in_base` (`:833-837`)
  already does this for the base merge. The patch extends it to every bundle merge, which
  makes it much more likely to come up. Raising `IntegrationTreeError` for these read
  failures would stop the carry instead. Low priority; leaving it as is matches the #623
  path.
- `template/src/pdca_harness/integrate.py:941-944`: `_own_removals` asks git which commit
  last set the path (`git rev-list -n 1 <head> -- <path>`, using git's default history
  simplification). An "evil" update merge (a conflict resolved to content neither parent
  had) or a merge that resolved a modify/delete conflict by hand to the deletion lands on
  the merge commit itself. That commit is in `own`, so the removal counts as the bundle's
  change. That is defensible (the branch's author made that choice), but no test pins it.
  If `last` comes back empty, the removal counts as not the bundle's own (fail-safe, a
  refusal). Not a defect; just noting the rule's edges.
- `template/src/pdca_harness/integrate.py:693-696`: `before` is read here, and `_merge`
  reads the same HEAD again (`:1040`). That costs one extra `rev-parse` per bundle. It
  could be folded in by having `_merge` return its `before`. Optional cleanup.
- Cost per bundle: every clean bundle merge now runs `_cut_point` plus two whole-tree
  `git diff --name-only` calls (`:969-974`) before it can return early. That is fine for
  normal batch sizes and runs only once per merge, so no change is needed.
- Tests (`template/tests/test_integrate_revert_via_branch.py`): they cover criteria (1),
  (2), (2b) and (3), plus the merge-from-base trap, a revert merged through a revert PR,
  the shared-commit naming, and a line that will not reset. They import only modules, so
  they fail on their assertions when the fix is removed (C4 confirms this). The
  `stuck` mock (test file `:633-636`) fails every `reset` except one whose last argument
  is `HEAD`. That is narrow but correct for today's `_reset_tree(wt, "HEAD")` at
  `integrate.py:529`. If that call ever changes, the test will fail and show it. No
  action needed.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->
