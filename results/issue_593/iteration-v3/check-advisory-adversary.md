# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

**Evidence.** The red→green proof holds. In `gate-logs/C4-verify.log` the red leg fails the key cases on
assertions, not import errors: the line not carrying `fix/A` / `fix/B`, the pushes passing `--force`, `--base
pdca-integration/main`, and `main...B` showing `a.txt`. The `TypeError` reds are the new-keyword cases the brief
accepted (test 3). The integrate cases call the real `integrate.fold` against real git. The publish case calls
the real `publish.publish`. I re-ran `tests.test_integrate_stack_bases` and `tests.test_integrate` on the patched
tree: 36 OK.

**Attacks that did not land:** the no-`--force` push on a continuing fold; the tip-mismatch refusal; rc 128 from
`--is-ancestor` treated as a git failure; gone branch → `is_merged` → skip or raise; `--prune` on every fetch;
the DCO trailer on merge commits; dry-run shelling nothing; resolving an `Onto branch` record to its own remote;
the hold cascading through `_runnable`; sorted per-target lock order (unchanged).

Findings:

- NEEDS-HUMAN [impl] — **The diff-shrink docs still overclaim, the same way last round's carry-forward #2 did.**
  The fold merges *every* accepted bundle of a target onto the line, not just a dependent's declared
  prerequisites. So the "two merge bases" case hits every later-wave PR whenever an earlier wave of that target
  had two or more bundles. That is the common case, not an edge case. I reproduced it with the real `fold`
  (`scratch/exp_unrelated_sibling.py`): wave 0 = {A, Z} with Z unrelated, and B `Depends on` A only. After A
  merges with a merge commit, `main...B` shows `['b.txt', 'z.txt']`. After Z merges too, `git merge-base --all`
  gives **2** bases and `main...B` shows `['a.txt', 'b.txt']`: B's *only* prerequisite, already merged. Neither
  documented exception covers this (B is not on two siblings, and the base did not move). Wrong text, which
  should say "every earlier-wave branch on the line":
  - `template/PCDA/quality-cycle/09-parallel-lanes.md:69` ("Once its only prerequisite merges … its own change —
    with two exceptions … a dependent that sits on two or more same-wave siblings")
  - `docs/07-crosscutting.md:648-651` ("shows its prerequisites' changes … usually its own change")
  - `template/src/pdca_harness/integrate.py:18-21`
  - `template/src/pdca_harness/publish.py:252-254`
  - `template/PCDA/quality-cycle/08-glossary.md:293`

  A case like the experiment above would pin it.

- NEEDS-HUMAN — **Merging any wave>0 PR now lands every earlier-wave PR of that target on the real base, including
  unrelated ones the human never approved or has closed.** This follows from the experiment above: B's PR
  (`--base main`, `publish.py:265`) carries Z's commits. Merge B and Z lands on `main` even if Z's own PR was
  rejected. Before this patch an own-repo wave>0 PR targeted the line, so this could not happen. Only the fork path
  carried the cumulative diff (#185). The docs say "merge the stack bottom-up" but never say that a PR carries
  non-prerequisite siblings, or that closing a lower PR does not keep it off the target. This is the #463 scope
  line. The human should confirm it is acceptable at sign-off, and the docs should say it.

- NEEDS-HUMAN — **The new publish-failed hold catches the sign-off's own iterate scenario even when only PR
  creation "failed".** The new-PR path always runs `gh pr create` (`publish.py:375-388`). `gh` exits non-zero when
  an open PR for that head branch already exists, which is the usual state of an iterated, still-draft bundle.
  By then the rebuilt branch has been force-pushed (`publish.py:295-302`), and `publish.json` is rewritten naming
  it with `pr_url: ""` (`publish.py:390-408`, rc 1). `flow.py:1838-1840` then marks the bundle failed, it is
  held, and every dependent is skipped. So a rebuilt bundle with an open PR always holds its dependents. The
  milestone needs another run, and that run then hits #616 (the dependent builds on a base missing the
  prerequisite). The new test models a different shape: its fake publish returns 1 with nothing pushed
  (`tests/test_flow_slice.py:1341`, used by `:1544`). Whether "branch pushed, PR already exists" counts as
  unpublished for the hold is a policy call. (Provisional: I could not run `gh` here.)

- NEEDS-HUMAN — **The tip-mismatch guard protects the line but not the PRs, and the PRs are what reach `main`
  now.** Publish cuts a wave>0 branch from `origin/<integration branch>` (`publish.py:246`) without checking it
  against the run's recorded tip. The final wave never folds (`flow.py:1853`, `k < len(wave_list) - 1`), so
  nothing checks it there. Concrete case: run 2 starts on the same base while run 1 is in its final wave, and
  run 2's first fold force-pushes a fresh line (`integrate.py:361`). Run 1's final-wave PRs then open against
  `main` carrying run 2's unmerged bundles, with no refusal. The same happens to a later manual `pdca publish
  <id>`, which the flow's own message suggests (`flow.py:1843`), because the `stack-base` marker persists after the
  run. Before this patch such a PR targeted the line and could not reach `main`. #591 is out of scope, but the
  invariant "every PR … reaches the real target" now means "reaches it with whatever is on the line when
  publish ran".

- NEEDS-HUMAN [impl] — **The end-to-end flow test `test_a_three_wave_run_folds_append_only_onto_a_real_origin`
  (`tests/test_flow_slice.py:1523-1542`) cannot tell "continue unforced" from "start fresh and `--force` every
  fold".** I re-ran it with `integrate.fold` wrapped to pass `folded_this_run={}` on every call (fresh +
  `--force` each time; `scratch/exp_e2e_weak.py`) and it still **passes**. `denyNonFastForwards` accepts a forced
  push that happens to fast-forward, and a fresh fold that merges EB still has T1 as an ancestor. Line 1542
  (`fix/issue_EB~1` in the line) is already implied by line 1540. The behaviour is still pinned elsewhere (the
  kwargs spy at `:1358-1372` and the push-argument spy at `tests/test_integrate_stack_bases.py:207-231`), so this
  is a weak test, not a coverage gap. To make it go red on that bug, assert exactly one `pdca-integrate:
  issue_EA` merge commit is in the line: an always-fresh fold makes two.
