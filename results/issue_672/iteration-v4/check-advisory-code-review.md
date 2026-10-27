# Advisory code review — issue 672 (carry keeps a fold-time skip off the line)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Grounded on the
patched target at `$PDCA_TARGET`. Gates: C4 is red before the fix and green after
(14 of 36 fail pre-fix, `gate-logs/C4-verify.log`). The T3 suite passes, 2477 tests
(`gate-logs/T3-suite.log`). I found no leak of skipped work onto the line. The findings
below are about wrong holds, misleading messages, and some dead or duplicated code.

- NEEDS-HUMAN [impl] — **A restart can hold both bundles, each naming the other as the
  cause, and the real conflict is never reported.** `template/src/pdca_harness/integrate.py:557`
  builds `excl` for the next pass from every `out` bundle's full work. `:570` then checks
  each bundle against it, including the bundle whose skip caused the restart. If Q was cut
  by hand from P's first commit `p1`, `out[Q]`'s work (`:618`, `_work` at `:971`) includes
  `p1`. So on pass 2, P is held for "holding a commit of Q's branch", and that commit is
  P's own `p1`. I reproduced this with a real-git probe on the carry fixture
  (`probe/test_probe_circular.py` in this sandbox): P adds `p-first.txt`; Q is
  `_finished_on("Q", "P")`; P then adds `q.txt` (which conflicts with Q's file, not with
  the base); order `Q, P`. Result: no push, D and E both PLANNED, and stderr says
  "issue_Q's branch … holds 63aebcc…, a commit of issue_P's branch … get issue_P carried"
  and "issue_P's branch … holds 63aebcc…, a commit of issue_Q's branch … get issue_Q
  carried". The advice loops, and neither line says the two conflict. P would merge alone
  on pass 2. Nothing leaks (the invariant holds), and `docs/07-crosscutting.md:750-753`
  does call "cut by hand, both held" a known limit. Still, this case is P failing *because
  of* Q, which is the case the restart exists to fix
  (`test_one_holding_a_later_ones_commit_is_held_when_they_conflict` covers only the
  stack-base form). Suggested fix: when judging bundle `d` on a later pass, leave out every
  `out` entry whose recorded cause is `d` (`out[n][0] == d.name`). Then P merges, and Q
  gets the existing "without {n} it is [carried]" message (`:645-649`). Add the probe as a
  regression test.

- NEEDS-HUMAN [impl] — **When a branch holds skipped work and also conflicts, the conflict
  message wins, and the "holds" cause and hint are lost.** `integrate.py:570-589`: `hit` is
  known before the merge, but the merge runs anyway. If the merge fails, the bundle goes
  into `left` with the conflict text, and `held` is never set. So `flow.py:1133-1134` gives
  it the `open` hint ("get issue_Q's PR open … re-open it"), which is wrong because its PR
  is open, and `causes` does not name the skipped id. The brief (`brief.md:9`) calls this
  the usual shape when P conflicts ("Q contains P's change, so it conflicts the same
  way"). It is simpler and cheaper to skip the merge when `hit` is set: record
  `_holds_why(...)` and `held[d.name]` directly, which also removes the merge-then-reset at
  `:571-574` and `:599`. No test covers a holder that also conflicts.

- **Dead code: the `held_out` re-judging on restart can never run.** `integrate.py:619-621`
  only runs when `skipped is not None` (restarts break out at `:607-608` otherwise).
  `held_out` is only passed by the in-run folds (`flow.py:2555-2560`), and those always
  pass `skipped=None`. The carry (`flow.py:1121-1123`) passes `skipped` and no `held_out`.
  Either delete the block and the `aside` list (`:554`, `:584`), or add an assertion that
  the two modes never combine.

- **Duplicate host call for a gone branch.** `integrate.py:990-998` (`_gone_work`) calls
  `merged.merged_head` again for a bundle whose `_merge_published` → `_gone_branch`
  (`integrate.py:767`) just asked the host the same question, which costs one more `gh pr
  view` round trip per gone, skipped bundle. Small cost, since it happens only on the
  gone-branch path. You could have `_gone_branch` return or record the head it read.

- **Minor efficiency: `_holding` scans in nested loops.** `integrate.py:1001-1012`:
  `next(... for name, work in excl.items() for c in work if c in adds[tip])` is called for
  every bundle, every pass, and once more for each `took` entry (`:609-610`) and each `out`
  entry (`:640`). The membership test uses a set, so each call is linear in the total
  excluded work, which is fine for realistic batch sizes. I note it only; no change needed.

Nothing else found. The restart terminates (each pass adds at least one name from `took`
to `out`). The skipped and `skip_causes` dicts are filled only after the
`SkippedWorkOnLine` and gone-branch raises, so the carry's `except` branch
(`flow.py:1124-1130`) never sees a half-filled `within`. The in-run folds (`skipped=None`)
keep their old single-pass behaviour.

<!-- pdca:leaf-complete -->
