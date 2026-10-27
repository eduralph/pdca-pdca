# Build notes — issue 500 (merge-mode retarget), iteration 2

Target: eduralph/pdca-harness @ main, base commit `a6af7f3` (origin/main). Worktree:
`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l0`. "base L" = line on
`a6af7f3`; "new L" = line after the patch.

## What changed and why

**`template/src/pdca_harness/merge.py`**

- New `_target_base(cfg, d, pr_url)` (new L485-532). It runs before the ready-mark and returns
  `(target, "")` or `("", why)`:
  - It resolves the target with `publish._resolve_target(d)[:2]` (new L502), the one parser
    publish uses, the same call as `flow._runnable` (`flow.py:779`). A missing brief, or one
    with no usable target, refuses (new L499-505). Publish never opens a PR for such a
    bundle, so this case can't happen in practice; it fails closed anyway.
  - It checks #411 route 2 with `publish._batch_branch_producer` (new L506-509), the same call
    `publish._merge_base_refusal` makes (base `publish.py:798`). This runs before any `gh`
    call, so (e) makes no `gh pr view`, `edit`, `ready` or `merge` call.
  - It reads the host base with `_pr_head` (new L510). If it equals the target, it returns
    (d). If not, it runs `gh pr edit <pr> --base <target>` (new L520), reads the base again
    (new L526), and goes on only if the host now reports the target (a). An edit that
    fails, or a base that doesn't change, refuses and names both branches (b).
- `_merge_one` calls it right after the `expected_checks_error` refusal (base L507-511) and
  before `gh pr ready` (base L519), at new L584-594. That covers (f) and both
  `merge_requires` values (c). A refusal prints to stderr and does `return 1`, like the
  `expected_checks` refusal, and does not go through `_refuse` (base L453), which always
  sends `gh pr ready --undo`. So in (b) and (e) there is no `gh pr ready` call of either
  kind.
- **Carry-forward 1 (the base-change gap):** `_base_read` now takes a required keyword-only
  `target` (new L379-380). A read that finds the PR on any other base refuses (new
  L399-402) before it fetches, checks behind-ness or updates anything. Both `_base_read`
  calls in `_merge_one` pass `target=target`: the first read after the ready-mark (base L552,
  new L637), and the final read after the rollup wait (base L607, new L694). That final read
  is what the reviewer saw ignore a changed base (`reviewer-base-race.log:2`). It and the
  first read are the only base reads on the "all" path that a merge or `update-branch` decision
  depends on. Both refuse through `_refuse`, so the ready-mark is undone. I chose to refuse
  rather than retarget a second time. A base that changes after the driver just set it means
  someone or something is editing the PR while the run works on it, and an unattended
  driver should not fight that. The next run's pre-ready check retargets it again anyway.
- **Carry-forward 3 (wrong hint after a failed or ignored edit):** after an edit fails or does
  not take, the brief's target is right and the PR is what's wrong. The hint now says
  "Retarget the PR to `<target>` on the host, or check that this `gh` login may edit it"
  (new L515-517). The refusal's closing line (new L591-593) adds "Re-run once that is
  resolved". The route-2 refusal keeps the brief-pointing hint, which is correct there.
- Module docstring: the line that said `"required"` does "no base read" (base L73) would now
  be false. It now says "no behind check" and that the target-base check still runs (new
  L73-74). A new paragraph describes the #500 rule (new L93-104), including that a base
  edited after the last read is the same gap no client can close as a base tip that moves
  after it (base L70-72).

**`template/src/pdca_harness/publish.py`**

- **Carry-forward 2 (duplicated hint):** the hint is now one module-level constant,
  `MERGE_BASE_FIX` (new L771-779), with no closing period. `_merge_base_refusal` uses
  `MERGE_BASE_FIX + "."` (new L803), so publish's output is byte-identical to before (base
  L790-793). The merge-time route-2 refusal uses `publish.MERGE_BASE_FIX` (merge.py new
  L509). I made it a public name because another module reads it.
- The #411 comment (base L288-292) said "Refuse here rather than at merge time". It now says
  publish refuses first and merge time checks again and retargets (new L288-294), as the
  brief's scope asks.

**Docs**

- `docs/07-crosscutting.md`: the merge-mode bullet (base L858-886) gets the target-base
  check, retarget, refusal and late-edit rule (new L887-896). The #411 paragraph's "the
  harness never retargets a PR for you" (base L897) is replaced (new L907-913). Both are
  named in the brief's scope.
- `template/docs/fork-discipline.md.jinja` (base L59, L64-65, L71-73): **not named in the
  brief.** I changed it because it lists merge mode's per-PR sequence as starting with the
  ready-mark, and says `"required"` "skips all of this". Both statements became false, in
  the doc an operator reads to learn what the driver does to their PRs unattended. The edit
  touches 6 lines and adds 9 (new L59-60, L65-68, L74-76), and keeps every other line of the
  paragraph unchanged. Drop it if you want the patch held strictly to the brief's file list.
- I left `template/pdca.toml.jinja` and `docs/05-check.md` alone: nothing they say becomes
  false.

**Tests**

- New `template/tests/test_merge_retarget.py` (the file the brief names). It imports only
  modules (`merge, merged, publish, state`) plus `Config`/`LeafConfig`, and never imports a
  symbol this patch adds. Its fake `_Host` (L71-117) records the base every `gh pr merge`
  landed on (`merged_into`), so the tests assert the invariant directly: nothing merges
  anywhere but the target.
  - (a)+(c) `test_wrong_base_is_retargeted_then_merged_into_the_target` (L150)
  - (b)+(c) `test_retarget_that_fails_or_does_not_take_refuses_with_the_pr_untouched` (L176).
    Also asserts the host-side hint and the absence of "Repo + branch target" (carry-forward 3).
  - (d)+(c) `test_pr_on_its_target_base_makes_no_edit` (L197)
  - (e)+(c) `test_batch_produced_target_is_refused_before_any_gh_call` (L210). Also asserts
    that the hint matches `publish._merge_base_refusal`'s own output word for word
    (carry-forward 2, checked through production code, without importing the new constant).
  - (f)+(c) `test_malformed_expected_checks_is_refused_before_any_edit` (L233)
  - carry-forward 1: `test_base_edited_on_the_host_after_the_check_is_never_merged_into`
    (L249). Three cases: retargeted then moved during the rollup wait, retargeted then moved
    right after the ready-mark, and on-target then moved during the wait. Each must refuse,
    never call `merge` or `update-branch`, undo the ready-mark, and name both branches.
  - `test_bundle_with_no_target_base_is_refused_untouched` (L269) pins the fail-closed
    no-target behaviour.
- Existing tests, updated because the check needs a brief and adds one `gh pr view` before the
  ready-mark:
  - `test_merge.py`: new `_brief()` helper (L59), used by the three bundle builders (L128,
    L922, L1219); three call-log assertions get the leading view; `fail_ready` answers the
    view (L237); the views list (L1036-1039).
  - `test_merge_onto_branch.py` (L74, L170) and `test_merge_third_remote.py` (L115, and
    `_read` passes `target="main"`, the base its fake host reports).
  - No assertion was loosened. Each change adds exactly the one new read.

## Alternatives ruled out (with cost)

- **`_base_read` returns the base (a 5-tuple) and `_merge_one` compares it.** Every unpack of
  `_base_read` would change: 2 in merge.py and 5 in `test_merge_third_remote.py` (L194, 203,
  221, 249, 266). Each `_merge_one` site would also need its own ~3-line comparison and
  refusal, about 15 changed lines in all. The chosen fix changes the signature, adds a 4-line
  check, edits the 2 call sites and 1 test line, about 8 lines. It also keeps the rule inside
  the one function every post-ready read goes through, so a future third read can't skip it.
- **`target: str = ""` defaulting to "skip the check".** This would save the 1-line test
  change in `test_merge_third_remote.py`, but a forgotten argument would silently drop a
  safety check. With the keyword required, a forgotten argument is a TypeError, and an empty
  target refuses.
- **Also checking the base inside `_wait_for_update`.** About 4 lines plus a parameter. Not
  needed for the invariant: `update-branch` is decided only after the first `_base_read`
  (now checked), and `gh pr merge` is reached on "all" only through the final `_base_read`
  (now checked).
- **A post-ready base re-read under `"required"`.** It can't close the gap (there is always
  a window between the last read and `gh pr merge`, and `gh pr merge` has no base pin). The
  window under "required" is one `gh pr ready` call. The brief keeps "required" as "skip the
  rollup/base-update gate".
- **Reusing `_base_read`'s view instead of the extra pre-ready `gh pr view`.** The brief
  allowed it. It would mean moving the #531 read before the ready-mark, which changes the
  documented order (merge.py docstring, base L58-60) and the call logs `test_merge.py` pins.
  The cost of not doing it is one `gh pr view` per merge-mode PR.

## Red→green evidence

C4, run through the project's gate script (`./engine/scripts/run-verify.sh`, under
`timeout 900`, with `PDCA_BUNDLE` and `PDCA_WORKTREE` set). Exit 0:

```
== C4 green leg: … test_merge.py test_merge_onto_branch.py test_merge_retarget.py test_merge_third_remote.py
Ran 59 OK · Ran 5 OK · Ran 7 OK · Ran 9 OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 59 FAILED (failures=5) · Ran 5 FAILED (failures=2) · Ran 7 FAILED (failures=15) · Ran 9 FAILED (errors=6)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

On the red leg, `test_merge_retarget` failed in (a)×2, (b)×4, (e)×4, the late-edit race ×3
and no-target ×2. (d) and (f) pass on both legs, as they should: the old code already makes
no edit for a right-based PR and already refuses a malformed `expected_checks` first.

Targeted mutation checks, each reverted afterwards:

- Disabling only the new `_base_read` check (`if False and base != target`) while keeping the
  retarget, i.e. the first attempt's behaviour: exactly the 3 late-edit cases fail
  (`AssertionError: 0 != 1`, the PR merged). This test binds carry-forward 1.
- Putting the first attempt's brief-pointing hint back on a failed or ignored edit: exactly
  the 4 (b) cases fail. This binds carry-forward 3.

Other gates run locally: T2 docs (`run-docs-check.sh`: lint clean, render and link audit
clean). T3 (`run-suite.sh`: root render/update suite, 24 tests OK, which covers the edited
`.jinja` doc; driver suite, 2637 tests OK, 2 skipped as before). C5
(`run-prod-path.py`: the added test imports `pdca_harness`). `git diff --check` is clean.
Commit readiness: the target has no formatter, linter or pre-commit config and no active
git hooks; its only commit rule is the DCO sign-off, which publish adds with `commit -s`. New
lines stay within each file's existing width.

## Refuting my own test

- **(a) Genuine red? Yes.** C4's red leg reverts the production hunks (merge.py, publish.py)
  and the new module fails 15 subtests. The two targeted mutations above make exactly the
  carry-forward tests fail. Every red is an assertion failure on a run that executed, not an
  import error: the module imports only pre-existing names.
- **(b) Production path? Yes.** Every case runs the real `merge.merge_wave` → `_merge_one` →
  `_target_base` / `_base_read`, plus the real `publish._resolve_target`,
  `_batch_branch_producer` and `_merge_base_refusal`. Only the process boundary is faked
  (`merge.subprocess.run`), with `state.state`, `merged.is_merged` and `merge._sleep` patched
  as `test_merge.py` does.
- **(c) Fixture includes the fault? Yes.** The fake host really carries the wrong base (`fix/old-parent`), really
  fails or ignores the edit, has a real sibling `publish.json` producing `feat/sibling`, and
  really moves the base mid-run (after the first `gh pr checks`, or right after the
  ready-mark). The assertion that catches a wrong merge (`merged_into`) records the base at
  the moment `gh pr merge` runs, so a merge into the wrong branch can't pass.

## For sign-off

- The brief's Motivation asks the maintainer to confirm the reversal of #411's "refuse at
  publish, never retarget" decision (old `publish.py:288-290` comment, old
  `07-crosscutting.md:897`). This patch makes that reversal. The refuse-only fallback would
  remove `_target_base`'s edit and re-read (new L515-531) and make a different base refuse
  instead.
- Residual risk, as the brief's open question states it: after a retarget, a head that
  already contains the new base's tip is not updated, so the rollup used is the existing
  one for that SHA. `pull_request`-triggered checks that ran against the old base are not
  re-run by a base edit.
- A base edited after the final read and before `gh pr merge` still merges into that base.
  No client can close this gap (`gh pr merge` has no base pin). The merge.py docstring now
  says so next to the existing base-tip gap.
- No `NEEDS-HUMAN external dependency`: everything ran offline with stubbed `gh`.
- Housekeeping slip: I wrote one scratch log of the C4 run to `/tmp/issue500-c4.log`,
  outside the roots I'm meant to write to. It holds only that run's output; later runs piped
  output directly. I didn't remove it (cleanup belongs to the harness).
- The worktree index has an intent-to-add entry I created only to put the new test file into
  `git diff`. I dropped it afterwards, so the new test is an ordinary untracked file again.
