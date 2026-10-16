# Advisory code review — issue 723 / fold-builds-a-per-bundle-base

Lens: bugs the patch introduces, plus reuse and simplification. I read `patch.diff`, `brief.md`, `check-gates.json` and `gate-logs/C4-verify.log`. Every `path:line` below is in `$PDCA_TARGET`, which already has the patch applied.

**Result: no correctness bug found in the diff.** What I checked:

- `_member_clash` reads `_trial` the right way round (`template/src/pdca_harness/integrate.py:1726`: `(i, paths)` means a conflict and `(None, [])` means clean), so `on_base = at is not None` is correct. A head of `None` can't reach `_member_clash`, because a gone branch raises a plain `IntegrationError` from `_gone_branch`, never `_Conflict`.
- `cuts[n]` in `own` can't raise `KeyError`. `cuts` covers every member whose head is not `None`, and `merged_in` only adds those members.
- The lease push `--force-with-lease=<branch>:<existing>` only runs when `existing` is set. The `existing[:12]` in the error text sits only in the branch of the conditional that needs it (`integrate.py:847-859`).
- The new tests really exercise the fix. Each fail-closed test, (6)(e)(i) through (iv-b), would let the build succeed (so the test goes red) if its check were skipped, because the member's cut point would fall back to `None` and X's commit would count as the member's own. The revert test (`template/tests/test_integrate_bundle_base.py:313`) fires on a fresh base: A is merged first, then B's branch brings in the revert. Without the check, the ownership rule would accept that revert as B's own work and the build would push. The `_git` spy in `_refused` also sees merges, because `_merge` goes through `_git` (`integrate.py:1539`). That makes the "no merge before refusal" assertion in test (5) meaningful.
- The C4 log shows all 26 tests failing in the test body with `AttributeError` before the fix, as the brief asks.

Findings:

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:803`: a contract hazard for #724, the caller. `build_bundle_base` opens a new `integ_lock` on the same worktree that `fold` locks. When the flow passes `locks=` to keep that lock held through the re-gate (`flow.py:948` → `integrate.py:550`), a call to `build_bundle_base` from the same process inside that window deadlocks. `fcntl.flock` (the OS file lock, `worktree.py:56`) locks per open file, so a second `open()` plus a blocking `LOCK_EX` in the same process waits forever. Separately, the build leaves the shared worktree checked out on the bundle-base branch (`integrate.py:828-829`). A re-gate that assumes the worktree still holds the run's line would then test the wrong tree. Nothing calls this yet, so this diff is not broken. #724 needs to either call it outside the fold/re-gate lock window or get a way to reuse the held lock. At least the docstring should say so.
- `template/src/pdca_harness/integrate.py:710`: a small reuse nit. The new `_bundle_name` repeats the expression `batch_key` already uses inline (`integrate.py:163`), and `bundle_base_branch` strips the prefix by hand again (`integrate.py:154`). Calling one helper from all three would keep the "`500` and `issue_500` are one bundle" rule in one place. This is cosmetic and not worth a round on its own.
- `template/src/pdca_harness/integrate.py:963` (`_unowned_work`): runs one `rev-list` per member. That's fine at the expected member counts. A single call isn't possible because each member has its own cut point, so this needs no change.

<!-- pdca:leaf-complete -->
