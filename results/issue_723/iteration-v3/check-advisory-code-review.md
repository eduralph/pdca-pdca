# Advisory code review — issue_723 (build_bundle_base)

Gates: C4 red→green (23 errors pre-fix, all pass post-fix), T3 suite OK (2549 tests). No gate disagreement found in gate-logs/.

## Correctness

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:930-932` (`_foreign_work` docstring) admits a case where excluded work gets through with no error. If an excluded branch X is fast-forwarded onto the head of a branch P that was cut from X, X's first-parent chain now runs through P's head. So X's earlier commits (for example `x1`) count as P's work, and building a base from `[P]` with X excluded pushes `x1` without refusing. The brief's invariant says a build is "refused, never silently widened". This attribution rule (first-parent chains, at `:940-949`) is not the rule the brief asked for. That rule was `foreign_commit`'s: `rev-list --no-merges <excluded> --not <base> <member heads…>`. The builder moved to chains to fix the round-1/2 false refusals. A human should decide whether this known false negative is acceptable, or whether the fast-forward case must fail closed (for example: refuse when an excluded head's chain contains a member's head that the member's branch no longer holds). No test covers it either way.
- `template/src/pdca_harness/integrate.py:820-829`: an excluded entry with an empty or missing head (`'(none given)'`) is a hard refusal, so a caller can never pass a run bundle that has no published branch (patchless or unpublished). That is consistent with the docstring, but #724's caller must filter those out first. Noting it for the caller; this is not a defect in the diff.
- `template/src/pdca_harness/integrate.py:830` and `:859-860`: the lease is pinned to the tip read right after the fetch, so a concurrent writer is caught (`--force-with-lease=<branch>:<existing>`), and creating the branch uses a plain push. Correct as written. The refused-push message at `:862-869` merges two causes, a protected branch and a moved branch, into one sentence. That is fine, since the remedy covers both.
- Refusals after the merge loop (foreign work at `:850-858`, a refused push at `:861`) leave the local `pdca-integration/…-b<id>` ref pointing at the unpushed build. The next build's `checkout -B … <base_ref>` (`:832`) and `_reset_tree` (`:831`) overwrite it, so nothing stale is reused. Same pattern as `fold`. No action needed.

## Tests

- `template/tests/test_integrate_bundle_base.py:195-211`: the create-without-force check reads the push argv only. No case runs a *create* against an origin with `receive.denyNonFastForwards = true` to show it succeeds. The argv check is what the brief asked for in (3), so this is fine. Mentioned only because the docstring at `integrate.py:763-765` claims the denyNonFastForwards behavior.
- The revert-check case (`test_integrate_bundle_base.py`, `test_a_member_that_brings_a_revert_of_an_earlier_members_work_stops_the_build`) now actually triggers the #623/#673 check and asserts the same refusal from `fold`. This fixes the round-1 finding.

## Reuse / simplification

- `template/src/pdca_harness/integrate.py:703-714` (`_owners`) is a clean extraction from `fold` (old body at `fold`'s `owners` loop). `fold`'s behavior is unchanged.
- `template/src/pdca_harness/integrate.py:873-904` (`_member_clash`): the `head is None` branch (`:886-887`) can't be reached, because `_Conflict` is only raised when a real head is merged (`_merge_published`, `:1101`). It's harmless, so leave it or drop it.
- `template/src/pdca_harness/integrate.py:946`: `theirs` rebuilds a union of every other chain once per excluded bundle (quadratic in the number of heads). Batches are small, so this costs nothing in practice. No change suggested.

Nothing else found: the shared merge path (`_merge_published` → `_gone_branch` / `_take_in_base` / revert check), the lock (`integ_lock`, `:802`), the worktree (`_prepare_worktree`, `:808`) and the name (`bundle_base_branch`, `:145`, which leaves `integration_branch` and `_flatten_base` untouched) are reused as the brief requires.

<!-- pdca:leaf-complete -->
