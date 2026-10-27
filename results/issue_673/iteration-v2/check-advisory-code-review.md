# Advisory code review — issue 673

Lens: bugs the patch adds, plus reuse / simplification / efficiency. Line numbers are on the
patched target (`$PDCA_TARGET`). The gates I can see all pass: C4 shows red before the fix
(8 of 11 fail) and green after, and the full suite runs green (T3: 2487 tests OK).

I found no blocking correctness bug. The own-removal rule (`git rev-list -n 1 <head> -- <path>`,
which follows the parent a merge took the path from, checked against `_own_commits`) handles
every history in the brief. That includes the case iteration 1 got wrong: a branch that touched
a.txt earlier but whose current a.txt came from the base. The `_reset_line` wording finding
from iteration 1 is fixed (`integrate.py:1000-1007`), and a test covers it
(`test_integrate_revert_via_branch.py`, the "will not go back" case).

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:988`: a bundle's walk now stops
  only at a commit that *equals* another owner's current tip (`skip | {t for t in tips.values() if t != tip}`).
  Suppose B was cut from `fix/A`, and A later got another commit pushed. Then A's current tip
  is not in B's history. B's walk goes past it into A's commits, and B gets named as an owner
  of a.txt too. The bundle-branch refusal would then say "a.txt (issue_A, issue_B)" and
  "issue_A, issue_B's work", which wrongly blames B for removing its own work. This only
  affects the error message: the refuse/keep decision does not change. The same change also
  affects the #623 base-merge message, because `_undone_paths` is shared. Possible fix:
  stop the walk at any commit reachable from another owner's tip (the
  `merge-base --is-ancestor` check, or one `rev-list` per other tip), or accept this and add
  a test that pins the current behavior. No test covers an advanced `fix/A`.
- `template/src/pdca_harness/integrate.py:726-730`: if a git read inside the new check fails,
  `_out` raises a plain `IntegrationError` (`:864-872`). Under the carry's `skipped`, `fold`
  then records that bundle as skipped (`:577-582`) instead of stopping, the same as a real
  refusal. `_take_in_base` (`:832-836`) already behaves this way, but it only runs for a gone
  branch. This check runs on every clean bundle merge, so a passing git glitch is now more
  likely to drop a good bundle quietly. The fix would be to wrap the failure in
  `IntegrationTreeError`, which `fold` re-raises even under `skipped`. Low risk, so I left it
  advisory and did not tag it.
- `template/src/pdca_harness/integrate.py:965-970` (efficiency): every clean bundle merge now
  pays for `_cut_point` plus two full diffs from the cut point (`old`→`before`,
  `old`→`HEAD`). Within one fold the cut point never changes. Only paths the merge itself
  changed can have been undone, so checking `_changed(wt, before, "HEAD")` first (usually
  small) would skip most of the work. This is cheap for today's line sizes, and the suite
  time did not get worse. It's an optional cleanup.
- Reuse: pulling the message builder out into `_removed` (`integrate.py:852-861`) and making
  `_reset_line` name what it undid (`:1000`) removes the duplication between `_take_in_base`
  and `_keep_merge`. The base-merge wording ("taking … in would remove", `:842`) is unchanged,
  as criterion (4) requires. Nothing more to merge here.

<!-- pdca:leaf-complete -->
