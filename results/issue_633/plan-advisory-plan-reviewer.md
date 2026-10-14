Bash was unavailable in this run (every command failed with `apply-seccomp: write /proc/self/setgroups … Permission denied`). This review was done with Read, Grep and Glob only.

# Plan review — issue 633 / fold-refuses-a-rewritten-carried-branch

I checked every `path:line` the brief cites against the target (`integrate.py:461-485, :472-473, :477-481, :349-357, :569-580, :196-207, :18-21, :30-34`, `flow.py:2298-2301`, `test_integrate_stack_bases.py:166-178, :351-366`). They all hold. The defect matches the thread. The issue's second "Done when" option is the fold detecting the rewrite and stopping, and the human chose that option at Plan. The RED is reachable with the fixture as written: `_push_from_human(..., off="origin/main", force=True)` rewrites `fix/A` on the bare origin. In the (1b) variant, both sides add `a.txt` with different content, which gives an add/add conflict, as the brief claims. The findings below are gaps in the design and the scope, not a wrong root cause.

- NEEDS-HUMAN — **The brief never says where "the commit the line took from it" comes from, and nothing records it today.** The Scope and Invariant depend on comparing a branch's current tip with "the commit the line took from it". The issue goes further: "its **recorded** head is no longer an ancestor of the branch". No per-bundle head is recorded anywhere:
  - `folded_this_run` maps a target to one line tip (`integrate.py:273, :294-296`).
  - The flow only stores per-target tips (`flow.py:812-813, :2297, :2304`).
  - `_merge_published` keeps nothing about the head it merged (`integrate.py:468-474`).

  Yet the Citations section says "The fold already has what it needs in one place … `refs[d.name]` … `_in_line`". Neither of those gives the old head. Do is left to invent one of three designs:
  - (a) Thread a per-bundle head record through `fold`'s signature and `flow.py`'s `folded_tips`. That is a hidden second surface in `flow.py`, and `Surfaces: data` does not cover it.
  - (b) Recover the old head from the line's `pdca-integrate: <name>` merge commits. That is judgment by commit message, which this module explicitly avoids ("never by a commit message", `integrate.py:41`, `:312`).
  - (c) Derive it by ancestry, e.g. `foreign_commit(wt, line, base_ref, current heads)` (`integrate.py:196-207`), then attribute the orphaned commit to a bundle.

  The brief should pick one design and name the files it touches. Otherwise Check cannot tell a sound fix from (b).

- NEEDS-HUMAN — **It is unspecified whether the new refusal goes inside `_merge_published`, and that decides whether the #646 pre-wave carry stops or quietly skips.**
  - With `skipped` passed, any `IntegrationError` raised while merging one bundle is recorded and the fold moves on to the next bundle (`integrate.py:433-439`). The carry passes `skipped` and `folded_this_run={tgt: tip}` (`flow.py:932`, `:811`).
  - If the check lives in `_merge_published` (the natural spot, next to `:472`), a rewrite found during a carry turns into a skip, not a stop.
  - If the check is done "in-run only" from a record, the carry never sees it.

  The brief puts the carry's judgment of an earlier run's line out of scope. It does not say what happens when the new check fires inside a carry that continues a line. The brief should state the intended behaviour, or require that the check runs outside the per-bundle `skipped` net. It should also add a criterion that pins that behaviour.

- NEEDS-HUMAN — **The brief does not mention a behaviour change that hits legitimate use: a rebase-style "Update branch" on a carried PR will now stop the run.**
  - The module docstring promises that commits pushed onto a stack PR branch after a fold reach the line (`integrate.py:39-40`). The fixture models only GitHub's merge-style update (`_update_branch`, `test_integrate_stack_bases.py:191-196`).
  - A reviewer who uses "Update with rebase", or a contributor who force-pushes a cleanup onto a carried PR mid-run, rewrites the branch exactly as a re-publish does. The new code will STOP the run.
  - That may be the right call, but the issue frames the problem only as "re-publishing a folded bundle". The brief should acknowledge this wider effect. The refusal message's "what to do" should cover it, and the docstring at `:39-40` and `docs/07-crosscutting.md:665-666` should be updated to say "fast-forward only". Otherwise the doc contract and the code disagree after the patch.

- NEEDS-HUMAN — **The ordering is declared without a resolvable dependency.**
  - The Ordering note says this bundle "goes in wave 1 and builds on both" 623 and 631, and that 631 rewrites the very loop this fix edits (`integrate.py:416-441`).
  - The brief declares only `Conflicts with: 623, 631`. There is no `Depends on` / `Stacks on`, and no `dependency-state.json` was supplied, so I cannot confirm that bundles 623 and 631 exist or what state they are in.
  - If the driver treats `Conflicts with` as serialization only, without a base ordering, Do may build on bare `main @ b5f5c29`. Its cited line numbers would then drift under 631's edit.
  - The brief should declare the prerequisite edges it relies on, or drop "builds on both" and state that line refs are on `b5f5c29`.

- NEEDS-HUMAN — **Criterion (1)'s message check is loose.** "says its branch was rewritten since this run folded it, with what to do" can only be verified by a reviewer, not by the test. Assert concrete substrings: `issue_A`, `fix/A`, and the word "rewritten". Also assert that the text does *not* contain "cross-wave overlap" in (1b). The test then fails on a regression in wording, not only on a missing raise.

I also tried to fault the root cause, the RED and the out-of-scope list (#573, #108, #646, #653, `_gone_branch`). I could not: the framing matches both the thread and the source.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
