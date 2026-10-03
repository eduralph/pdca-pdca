# Adversarial review — issue 593 (iteration 5)

I went after the red→green evidence, the iteration-4 carry-forward fixes, and the new
"was a branch pushed this run?" signal. Two real-git probes broke the merged-and-gone path
in `_gone_branch`. Everything else held up. The probes ran on `$PDCA_TARGET` with the
`StackFoldGit` fixture (python3 + git were available, so nothing here is provisional).

- NEEDS-HUMAN [impl] — **The fix for the needless STOP (iteration-4 item 3) misses the normal bottom-up merge.**
  `template/src/pdca_harness/integrate.py:414` decides "this line already carries it" by
  looking for `pdca-integrate: <bundle>` in `_merges_past`, and `integrate.py:427-431` limits
  that scan to `<base_remote>/<base>..HEAD`. Every wave≥1 PR is cut from the line, so it
  carries the earlier fold merge commits. Once one of those PRs merges into the base, those
  merge commits can be reached from the base and drop out of the scan. The check then misses
  a bundle that *is* on the line and falls through to `_take_in_base` (`integrate.py:424`,
  `:439-451`), which merges the base in and STOPs on any unrelated conflict.
  **Failing case (reproduced):** waves {A} → {B (Depends on A), C}. Fold [A] → T1. Publish B
  and C off the line. Fold [A,B,C] with `{TARGET: T1}` → T2. The maintainer merges fix/A and
  then fix/B into main and deletes both branches. Someone lands an unrelated `c.txt` change on
  main. Fold [A,B,C] with `{TARGET: T2}` (is_merged true) → `IntegrationError: issue_A's
  branch origin/fix/A is gone and its PR is merged, but origin/main … conflicts in c.txt`.
  A's merge commit is an ancestor of T2. An `Onto branch` record hits the same miss and
  raises at `integrate.py:418-423` instead. The pinning test
  (`template/tests/test_integrate_stack_bases.py:305-324`) merges only fix/A, never a
  wave-1 PR, so it cannot see this. Fix direction: limit the scan by where this run's line
  started (or have the flow pass in the bundle names it already folded), not by the base.
  Add the case above as a regression test.

- NEEDS-HUMAN — **"Already on the line" trusts a commit subject, not the merged head, so it can drop a merged PR's later commits.**
  `integrate.py:414-417` skips a gone, merged bundle once *any* `pdca-integrate: <bundle>`
  merge is on the line. If the PR got more commits after the fold carried it (say a reviewer
  pushes a fixup to fix/A), and it then merged with its branch deleted, the skip leaves those
  commits off the line, and the next wave builds and verifies without them.
  **Failing case (reproduced):** fold [A] → T1. Push a fixup to fix/A (`a.txt` → "a, after
  review"). Merge fix/A into main and delete it. Fold [A,B] with `{TARGET: T1}`. The line has
  `a.txt` = "a", main has "a, after review". With "delete branch on merge" off, the same fold
  would merge fix/A's new head. So the result depends on a repo setting. This partly reopens
  iteration-3 item 1. A tight fix needs the merged PR's head SHA (`merged.py:46` asks `gh` only
  for `state`), and it pulls against the finding above. A human should decide whether
  commits pushed straight onto a stack PR branch are in scope. The subject-match approach
  came from sign-off's own suggestion.

- NEEDS-HUMAN — **Only publish reads the recorded line tip. Do, the verify gate and drift still read the moving branch.**
  `publish.py:254-255` cuts the PR branch from the recorded tip. `worktree.py:96-98` (Do
  worktree), `gates.py:568-570` (`PDCA_VERIFY_BASE`) and `drift.py:49-64` still use
  `origin/pdca-integration/<base>` as it is *now*. `drift._resolve_base` even says it
  resolves "exactly as publish does", which is no longer true. Within one run the two agree.
  But a held bundle that is re-driven by hand (iterate-do, then drive, not a new flow) gets
  rebuilt and verified on the grown line, which now holds later waves, and then published
  from the old tip. Either the tested tree is not the pushed tree, or `git apply` fails with
  a misleading "rebase against origin/main" hint (`publish.py:375`). `pdca drift` on a
  late-published PR checks it against the grown line and can falsely report needs-rebase.
  This is a scope call (manual re-drive of a held bundle, close to #616), not a bug inside
  the flow.

- Tried and failed to refute:
  - **C4 red→green.** Confirmed in `gate-logs/C4-verify.log`. On the red leg,
    test_integrate_stack_bases had 17 failures + 9 errors, and test_flow_slice had 9 + 1.
    `test_a_held_bundle_published_later_…` goes red at a setup assertion
    (`test_flow_slice.py:1721`), not at its key check. So I re-ran it with publish ignoring
    the recorded tip (patched `publish._stack_marker`). It then fails at `:1731` ("LU's PR
    branch carries LK"), so it does guard the recorded-SHA part.
  - **The `_record_stamp` push signal** (`flow.py:655-675`). I checked every return path in
    `publish.py:157-429` and `:432-538`. `publish.json` is written only after the push, so an
    earlier run's record cannot pass as fresh. The one gap I found errs toward holding: an
    exception from `gh pr create` after the push (e.g. `gh` missing) holds a bundle that was
    pushed. That is the safe direction.
  - **Within-run behaviour:** the append-only unforced push, the refusal when another run
    moved the line, the hold cascade through `_runnable` (`flow.py:712-713`), the fork and
    dry-run plans, and `Onto branch` remote resolution. I found no input that breaks them.
