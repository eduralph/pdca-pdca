# Advisory code review — issue 631 (fold starts from a clean integration tree)

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency.
Paths are under `$PDCA_TARGET` (patched tree).

**Result: no blocking findings on either lens.** The fix does what the brief asks. The previous rounds' two items are handled: the class is now `IntegrationTreeError` (`template/src/pdca_harness/integrate.py:70`), and the test asserts that subclass and an empty `skipped` (`template/tests/test_integrate_clean_tree.py:223-230`). The C4 log shows 6 of 7 tests red before the fix and all green after. The one test that passes before the fix, `test_ignored_build_cache_is_kept` (`template/tests/test_integrate_clean_tree.py:247`), is meant to: it guards the "no `-x`" choice and is not a repro.

What I checked and found correct:

- `template/src/pdca_harness/integrate.py:446` — the reset before the fold runs inside the lifecycle lock and before `checkout -B`. A failure raises before any push, so the "nothing is pushed when a fold raises" order still holds.
- `template/src/pdca_harness/integrate.py:605-616` — `before` is read before the merge. Conflict paths are collected (`diff --diff-filter=U`) *before* `_reset_tree` wipes them, so the conflict message is unchanged. Both callers of `_merge` (`_merge_published` at `:490` and `_take_in_base` at `:570`) get the reset-on-failure behaviour, so the gone-branch path no longer leaves a mid-merge tree either.
- `template/src/pdca_harness/integrate.py:453` — `IntegrationTreeError` bypasses `skipped`. Since it subclasses `IntegrationError`, the flow's existing handlers still catch it. That matches criterion (3)'s "raise only if the reset fails".
- `template/src/pdca_harness/integrate.py:628` — `clean -ffd` with no `-x` matches the brief's invariant: ignored files are kept, and nested repos are removed (the extra test at `tests/test_integrate_clean_tree.py` covers the nested-repo case).
- Cost: each fold adds two git calls, and each merge adds one `rev-parse` (plus two calls on a failed merge). That is negligible next to the fetch and merge.

Minor, non-blocking notes (no action needed):

- `template/tests/test_integrate_clean_tree.py:192` — after the fix, production never calls `git merge --abort`, so the spy's abort branch only matters for the pre-fix (red) leg. That is intended: it makes the pre-fix code really leave a mid-merge tree. Post-fix, criterion (3)'s green leg is really testing "a failed merge is undone by reset", not "a failed abort is caught". It meets the brief, but a reader may find the test name `test_failed_abort_resets_the_tree_and_the_carry_goes_on` misleading against the new code path. Optional rename or comment.
- `template/src/pdca_harness/integrate.py:446` — the reset before the fold passes the literal `"HEAD"`, so if it fails the error says "could not reset … to HEAD", not a SHA. That is fine for an operator, just less specific than the in-merge case, which passes a SHA (`:616`). Optional.
- `template/src/pdca_harness/integrate.py:616` — the comment "a no-op when the merge never started" holds only because the tree was cleaned at fold start and every merge since then committed. `clean -ffd` is not a no-op in general. This is accurate in context, so no change is needed.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
