# Advisory code review — issue 633 (fold refuses a rewritten carried branch)

No correctness bugs found in the patch. The notes below are small cleanups and one wording nit. None of them blocks.

What I checked and found sound:
- The check runs before any target takes its lock or merges (`template/src/pdca_harness/integrate.py:414`), and it is skipped when `carried` is empty or this is a dry run. So the run's first fold and the #646 carry (`template/src/pdca_harness/flow.py:981`, which passes no mapping) behave as before.
- The commit that gets merged is the one that was checked (`integrate.py:491-493`). The fetch under the lock still runs (`_prepare_worktree`, `integrate.py:449`), so the earlier round's finding is fixed. The "origin's line moved" (#591) refusal reads a fresh fetch again, and a test pins this.
- The record is updated only after that target's push succeeds (`integrate.py:520-521`). Gone branches (tip `None`) keep their old record and fall through to `_gone_branch` unchanged (`integrate.py:549-550`, `:577-579`).
- The ancestry test keeps `_in_line`'s fail-closed reading: a git error raises, it is never read as "rewritten" (`integrate.py:550-551`, `:807-818`).
- The flow creates one mapping per run and passes it only to the in-run fold (`flow.py:2148`, `:2349-2352`).
- C4 log: the new tests fail without the fix (4 failures, including the 1b "cross-wave overlap" message) and pass with it.

Findings:

- `template/src/pdca_harness/integrate.py:540-545` — `_carried_tips` calls `_fetch` once per target group. When several bases share one checkout (the multi-base case the new race test sets up), it fetches the same checkout once per group, and each group then fetches again under its lock (`:449`). That makes 2N full fetches of origin for N targets in one checkout. Fetching once per distinct checkout here would give the same result with fewer network round trips. This is efficiency only, so no tag needed.
- `template/src/pdca_harness/integrate.py:543` — that up-front fetch runs outside any integration lock, in a checkout another flow's fold may be fetching into at the same time. Two git fetches in one repo can fail on ref locks. `_fetch` would then raise and stop the run with a misleading "fetch failed". Folds of different bases in one checkout could already overlap like this before the patch, so the risk is not new. But the patch adds one more unlocked fetch per fold that has carried bundles. Low likelihood. Mentioned so the human knows it exists; no change requested.
- `template/src/pdca_harness/integrate.py:560-561` — the refusal says "Restore {ref} to …", and `ref` is the remote-tracking name (`origin/fix/A`). The operator restores the branch `fix/A` on the remote, not `origin/fix/A`. Saying "restore branch fix/A on origin" would be clearer. This is a wording nit; the test only checks for "Restore" and "fix/A", so it would still pass.
- `template/tests/test_integrate_stack_bases.py:1279-1299` (`test_a_rewrite_between_two_targets_fetches_never_reaches_the_line`) — the rewrite fires before the 2nd `fetch`. With both groups carried, that 2nd fetch is `_carried_tips`'s own fetch for `zbase` (`integrate.py:543`), not the lock-time fetch the comment describes. The test still proves the point: fix/A is rewritten after its tip was checked, and the 3rd fetch (under main's lock) makes the stale tip visible before the merge. But the comment "the fetch for zbase also refreshes fix/A" does not match which fetch it is. The test depends on fetch order (`len(fetches) == 2`), so a future change to the fetch count would quietly move the race point. Clarifying the comment or matching on the call site would make it sturdier. Test clarity only; no tag needed.

<!-- pdca:leaf-complete -->
