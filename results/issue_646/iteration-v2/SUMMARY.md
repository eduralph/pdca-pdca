# Result — issue 646 / stack-reissue-continues-batch-line

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds a dependent on a base missing its prerequisite, when the prerequisite finished
  in the earlier run:
  - the finished id is skipped as already terminal (`template/src/pdca_harness/flow.py:2320-2325`),
    so it is not in the drive set and never enters `accepted` or the fold
    (`flow.py:2031`, `:2067-2070`);
  - `_runnable` sees it as out-of-batch (`batch_names` is the drive set, `flow.py:706`) and
    accepts it as ready because it is COMPLETE (`flow.py:710`) — COMPLETE only means a draft
    PR was opened;
  - nothing has been folded yet, so `_point_at_integration` clears the dependent's stack base
    (`flow.py:736-742`) and it is cut from the plain target base.
  The dependent is built, C4-verified and published without its prerequisite. Nothing
  reports it. The earlier run's line is usually still on `origin` under the same name (#591:
  the batch key comes from the ids as asked for, skipped ones included, `flow.py:2357-2363`,
  `integrate.py:67-83`), holding the prerequisite — but the resumed run never uses it, and
  its first in-run fold force-replaces it (`integrate.py:344-345`, `:401`), which strands any
  accepted-but-unpublished bundle whose recorded line tip was on it
  (`publish._line_tip_refusal`, `publish.py:691-726`).
- Success criterion: With the patch, in stack mode with publishing on (non-stub publisher),
  real git against a bare `origin`, a run driven as `flow._drive_and_act(cfg, [D], …,
  batch=["P", "D"])` (the shape `flow_ids` produces when `P` is skipped as finished) where
  `P` is COMPLETE, has a non-empty `patch.diff`, a resolvable target, a `publish.json` naming
  a pushed branch and an OPEN PR, and `D` has `- **Depends on:** P`:
  (1) before `D`'s wave is driven, origin's line `integrate.integration_branch(cfg, "main",
  ["P", "D"])` contains `P`'s branch head, and `D`'s recorded stack base
  (`publish.read_stack_base`) names that line and its tip (`publish.read_stack_base_tip`)
  is the line's tip. Pre-fix `D`'s stack base is cleared and no such line holds `P` — RED.
  (2) **Continue, never replace:** when origin already has that line (the earlier run's,
  holding `P` and an accepted-but-unpublished `H` whose recorded `stack-base-tip` is a commit
  on it), the run continues it: the old tip stays an ancestor of the new tip, no force-push
  happens, and after the run `publish._line_tip_refusal` for `H` returns `""`.
  (3) **Append-only across waves:** with a second driven bundle `E` (`Depends on: D`), the
  fold after wave 0 continues the same line without force and without `IntegrationError`;
  it then holds `P` and `D`, and `E`'s stack base names it.
  (4) **Holds, per prerequisite, named on stderr, rest of the run goes on:** each case below
  leaves `P` out of the fold, holds exactly `P`'s dependents in the drive set (they stay
  PLANNED, are not built), prints one line naming `P`, the held dependents and the reason
  with advice that works under (2), and lets an unrelated bundle `U` build:
  (a) `P` has no branch on record; (c) `P`'s PR state is
  CLOSED (not merged); (d) `P`'s PR state cannot be read (no `pr_url`, a `gh` failure, or
  `gh` missing — an `OSError` — never a traceback).
  (5) **Nothing to carry:** `P` COMPLETE with an empty or missing `patch.diff` ⇒ nothing is
  folded, `D` is not held and builds on the base as today. `P`'s PR MERGED ⇒ `P` is handed to
  the fold like an open one; the fold already decides it (`integrate._gone_branch`,
  `integrate.py:442-490`: line has the merged head ⇒ skip; base has it ⇒ take base in;
  otherwise raise).
  (6) **Fail closed:** the pre-wave fold raising `IntegrationError` stops the run before
  wave 0: nothing is driven, stderr names the failure the way the in-run fold's
  "did not integrate; STOPPING" line does (`flow.py:2076-2079`), no traceback.
  (7) **Unchanged:** a run with no named-but-finished id that a drive-set bundle's plain
  `Depends on` names behaves exactly as today (no pre-wave fold, stale stack bases cleared);
  `Stacks on` and `Depends on (merged)` edges do not trigger the carry and keep their
  behaviour (#123, #186); a dry-run (stub publisher) asks no host, holds nothing, and only
  prints the plan; `--no-publish` and merge mode are untouched.
  (8) **Unrelated bundle on a carried line:** when the carry happens, an unrelated wave-0
  bundle `U` (no dependency on `P`) has its stack base pointed at the same line and tip as
  `D` (`publish.read_stack_base` / `read_stack_base_tip`), and its published PR still targets
  the real base `main` (#593) — the same outcome a later-wave `U` gets today. Pre-fix `U`'s
  stack base is cleared.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a re-issued stack-mode `pdca flow <ids>` carry the named ids that are
  already finished (COMPLETE, patched, targeted) onto its batch's integration line before
  wave 0, CONTINUING origin's line when it exists (append-only, no force) and starting it
  fresh only when it does not; then point the run's bundles at it exactly as later waves
  already are. The carry happens only when some bundle in the drive set names such an id in
  its plain `Depends on`; when it happens, every carryable finished named id is carried (the
  line is the batch's line, as the in-run fold carries every accepted bundle), and every
  same-target runnable wave-0 bundle — including an unrelated `U` — is pointed at it
  (`_point_at_integration`, `flow.py:722-742`; its PR shows the carried changes until they
  merge, as any later-wave PR does). A dependent held for some other reason (a
  `Depends on (merged)` wait, another held prerequisite) does not cancel the carry: the line
  is the batch's own, not that dependent's. A finished named id that cannot be carried
  (criterion 4a, 4c, 4d) holds only its own dependents — the same `held_unpushed` path the in-run
  fold uses (`flow.py:2052-2058`, `:712-713`) — and the hold message's advice must be one that
  works now the line is kept (e.g. "publish it with `pdca publish <id>`, then re-issue the
  same command"; for a closed PR, "re-open it or re-drive <id>"; for an unreadable state,
  say what could not be read). A failing pre-wave fold stops the run before wave 0. Update
  the stack-mode paragraph in `docs/07-crosscutting.md:658-677`, the "resuming across runs
  is #616" wording in `publish.py:345`, `:696`, `:726`, and the "known cross-run limit (#616)"
  docstring in `drift.py:58-61` so they describe the kept line. Existing tests pin the old
  wording — `template/tests/test_integrate_stack_bases.py:834-852` (asserts `"#616"` and
  `"re-drive it in a new run"`) and `:1012` (asserts `"#616"`): update those assertions to the
  new advice text in the same patch (they are in Do's review surface, and C4 keeps
  `tests/*.py`, so they must pass post-fix).
  / out of scope: a prerequisite that is NOT one of the requested ids, including the
  `flow_batch` sweep path (child-2); `merged.is_merged`'s "merged where" rule (child-2);
  `Depends on (merged)` semantics (#186, unchanged); `Stacks on` (unchanged); merge mode
  (#531); split children adopted mid-run by an earlier run (name the gap in a docstring);
  rebuilding the line from scratch; a line on origin that an outside party rewrote (the
  continued fold merges onto whatever origin has — say so in the docstring); pruning old
  integration branches (#454).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of #646: make a re-issued stack-mode flow carry finished prerequisites onto its batch’s existing integration line before wave 0, preserving prior build bases and refusing rejected work.

Source paths below are relative to `$PDCA_TARGET` (`target/`); evidence paths are relative to this review directory. This review is advisory and does not gate acceptance.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Recovery, append-only history, per-prerequisite holds and the prior review’s target-wide closed-PR refusal have explicit observable outcomes; the no-carry exception is documented (`brief.md:33`, `brief.md:201`; `docs/07-crosscutting.md:675`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the tests produced 21 assertion failures in 70 tests, including a dependent missing its prerequisite’s file and integration base (`review-red.log:298`, `review-red.log:630`). |
| C3 Change | FAIL | A closed PR’s unavailable head is treated as proof its work is absent, allowing same-target bundles to build on the rejected changes already on the line; reproduced below (`template/src/pdca_harness/integrate.py:560`; `review-closed-head.log:15`). |
| C4 Verification (red→green) | PASS | Restoring the production changes made all 70 focused tests pass, independently confirming the frozen C4 result; this establishes the shipped regressions, but they miss the C3 case (`review-green.log:178`; `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Carrying skipped finished prerequisites before wave 0 addresses their omission from the fold; the fold, tip read and re-gate share the lock. No capability probe masks a load-time cause; the remaining fail-closed defect is C3 (`template/src/pdca_harness/flow.py:798`, `template/src/pdca_harness/flow.py:883`). |
| T1 Structure | PASS | Existing flow, merge-state and integration modules retain their responsibilities, with shared fetch behavior and production-path regression coverage; no new dependency or parallel implementation (`template/src/pdca_harness/integrate.py:632`; `template/tests/test_flow_resume_stack_prereqs.py:44`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page rendering/link audit and production-import scanner passed; diff whitespace checks passed, consistent with both frozen docs gates (`review-scanners.log:1`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite: 2,349 tests, two skipped, no failures; frozen root-suite evidence reports 24 passing tests. Local root rerun lacks importable Copier, a reviewer-host limitation rather than a patch defect (`review-suite.log:1951`; `gate-logs/T3-suite.log:54`; `review-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate’s substantive audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art coverage across all affected paths and closed/rejected work — the brief records a path-based search for three modules, but the supplied target has only a synthetic base commit and no remotes, so broader history and rejected-PR conclusions cannot be independently settled (`brief.md:167`; `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the scoped recovery behavior and host coverage suffice after addressing C3 — real Git history, publishing and re-gating ran, but live GitHub/gh state retrieval was not exercised; its evidence rests on mocked host responses, and no-carry runs still replace the line (`template/tests/test_flow_resume_stack_prereqs.py:112`; `docs/07-crosscutting.md:681`). |

Confirmed finding — unavailable closed-PR head permits rejected work (high priority).

`template/src/pdca_harness/integrate.py:560` returns `False` when `git cat-file` cannot resolve the host-reported head. That answer reaches `flow.py:847` as “not on the line,” bypassing the target-wide refusal. An unavailable head cannot establish that earlier commits from the same PR are absent.

I exercised this sequence against the patched target using the shipped fixture and real Git:

1. Publish P and Q; fold both onto the batch’s line.
2. From another checkout, push a fixup to P, then close its PR and delete its branch before the harness fetches again. The host reports the fixup’s SHA, which the harness checkout does not have.
3. Resume the same batch with D depending on P, E depending on Q, and unrelated U; report P CLOSED and Q OPEN through the fixture’s host-response table.

Observed: the line still contains P’s original commit; D remains PLANNED, but E and U are driven and published COMPLETE. E’s recorded build base is the earlier line holding CLOSED P. Stderr incorrectly says P “is not carried.” This contradicts the explicit carry-forward requirement (`brief.md:201`) and the published refusal contract (`docs/07-crosscutting.md:675`). Evidence: `review-closed-head.log:15`. The existing deleted-branch test (`template/tests/test_flow_resume_stack_prereqs.py:513`) only checks a head already available from the earlier fold, so it misses this case.

Treat an unresolvable head as unknown and block that target, or obtain sufficient history to prove absence before continuing. Add this deleted-branch-after-fixup case to the regression suite. The standalone reproduction is preserved in `review-closed-head.py`; run from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/target/template/src:$PWD/target/template" \
python3 review-closed-head.py
```

The supplied target was readable and compatible with the patch; no stale-target caveat applies. Production changes were restored after the red leg, and no fix was made. The frozen root-suite log discharges the Copier coverage absent from this reviewer’s interpreter; it is not an unmet dependency of the submitted gate run. The project’s supplied `template/docs/INTEGRATION.md.jinja:80` leaves human-only items as a TODO and enumerates no additional project-specific decisions.

### Advisory — adversary

# Adversarial review — issue_646 (re-issued stack run continues its batch's line)

The red→green proof holds. I found two concrete cases where the kept line does something
a human should decide on. Both were reproduced against `$PDCA_TARGET` with a scratch test
that reuses the bundle's own `ResumedStackRun` fixture (real `_drive_and_act`, real fold,
real publish, real git; only `_drive_wave` and `gh` stubbed).

## Findings

- NEEDS-HUMAN — **The continued line keeps a rejected bundle's old commit, and its rebuild
  ships it.** `_carry_finished` checks only *finished* ids against origin's line
  (`template/src/pdca_harness/flow.py:798-800`, `:828`, `:836`;
  `template/src/pdca_harness/integrate.py:281`). It then continues the line exactly as
  origin has it (`flow.py:873`, `:886`). Failing case: batch `[P, X, D]`. The earlier run
  folded P and X. X was then rejected and iterated (iterate archives `patch.diff` /
  `SUMMARY.md` but keeps `publish.json`; its PR is CLOSED). Re-issue: the run drives
  `[D, X]`, and D has `Depends on: P`. Observed: X's stack base is the old line tip, and
  **the old X commit is an ancestor of the new X PR branch**. The rejected change rides
  into X's new PR, and nothing is printed. Before the fix, X was cut from `main`.
  Sign-off item 3 ("a closed PR's branch must not ride the shared line") is enforced only
  for finished ids, not for drive-set bundles the earlier run folded. The same gap applies
  to a finished P whose branch was force-pushed with a rebuilt commit after the earlier
  fold: `_holds` (`integrate.py:552-566`) looks only for the *current* head's commits, so
  an old P commit on the line goes unseen. The human needs to decide: extend the on-line
  check to every requested bundle that has a publish record, or accept and document it.

- NEEDS-HUMAN — **Following the harness's own advice after a failed `gh pr create` blocks
  the whole target, and the new advice does not get you out.** Earlier run: P's branch is
  pushed, `gh pr create` fails, and `publish.json` records `pr_url: ""`
  (`template/src/pdca_harness/publish.py:405-433`). The in-run fold still folds P
  (`flow.py:2236-2237`). The publish message says "Open it by hand"
  (`publish.py:416`). Re-issue `[P, D, U]`: `merged.pr_state` returns "no PR on record"
  (`template/src/pdca_harness/merged.py:112`). The line holds P, so the target is blocked:
  D **and the unrelated U** stay PLANNED, and nothing is built (reproduced). Before the
  fix, U built. The advice "fix what kept issue_P's PR state from being read (its
  publish.json / `gh`)" (`flow.py:864`) points at no command that works. `pdca publish P`
  takes the new-PR path, which has no existing-PR lookup (`_existing_pr` is used only by
  the `Onto branch` path, `publish.py:510`). So `gh pr create` fails again and writes
  `pr_url: ""` again. The only ways out are hand-editing JSON or deleting the line. The
  brief's (4d) counts "no `pr_url`" as unreadable, so this is a scope call. Options: look
  the PR up by its head branch when `pr_url` is empty, or tell the user to edit
  `publish.json` by name.

- (Brief-sanctioned, no action asked.) A finished P whose PR was **squash-merged** and its
  branch deleted now stops every re-issue before wave 0
  (`integrate.py:532-540`, via `flow.py:889-892`). Before the fix, D built correctly on
  `main`, which already had P's change. Brief (5) accepts this raise, the docs require
  merge commits, and the advice ("restore the branch") does work. I'm noting it so the
  sign-off knows a case that used to work is now a hard stop that also blocks unrelated
  bundles.

## Refutation attempts that failed

- **Red→green.** I re-ran the green leg at the target: `tests.test_flow_resume_stack_prereqs`,
  24/24 OK. Red leg, from `gate-logs/C4-verify.log`: 19/24 fail on the expected
  assertions (no line on origin before D's wave; a `--force` push over the earlier line;
  D built and its `p.txt` edit failed to apply on `main`). The 5 that pass on the red leg
  are the "unchanged" cases (5-empty/missing patch, 7-no-dependency, 7-`Stacks on` /
  `Depends on (merged)`, 7-`--no-publish` / merge). They should pass both ways.
- **Production path, not a copy.** D's patch edits `p.txt`, so the real `publish.publish`
  only succeeds if D's branch is cut from a line that holds P. That is not tautological.
  The lock test's depth counter would fail if the fold released its lock before
  `pushed_tip` (the iteration-1 bug), so sign-off item 1 really is pinned.
- **The gone-branch tests use the PR head.** `_fetch` prunes `origin`
  (`integrate.py:647-648`), so `test_4c_a_closed_pr_whose_branch_is_gone_…` resolves P
  through `headRefOid`, not a stale remote ref.
- **No-carry runs unchanged.** The widened `_runnable` hold (`flow.py:719`) can only fire
  for out-of-batch names that `_carry_finished` put in `held`. `integ.update`
  (`flow.py:2270`) cannot keep a stale target, because `accepted` is cumulative. A library
  call with `batch=None` makes `run_batch` the drive set, so `finished` is empty. The
  `flow_batch` sweep excludes COMPLETE bundles, so the child-2 scope stays untouched.
- **Concurrency.** The gap between `read_lines` and the fold is covered: the fold is given
  the checked tip and refuses a moved line (`integrate.py:431-439`). A line that appears
  in that gap gets replaced, which the docstring says openly.

### Advisory — code-review

# Advisory code review — issue_646 (stack-reissue-continues-batch-line)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.
All `path:line` refs are on the patched tree at `$PDCA_TARGET`.

I found no blocking correctness bug. The four sign-off items are handled:
- the lock now covers the fold, the tip read and the re-gate (`template/src/pdca_harness/flow.py:883-905`);
- a red re-gate stops the run before wave 0;
- a line that already holds a closed or unreadable id is blocked rather than continued (`flow.py:845-875`);
- the wording is qualified.

The gates agree. C4 is red pre-fix and green post-fix. T3 ran 2349 tests: OK.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:873-886`: once the carry triggers, the run continues the earlier run's line as it is. That line can hold the old branch of a bundle that is back in this run's drive set: it was folded last time, then re-opened or iterated, so it is no longer COMPLETE. Before this patch, the first fold started a fresh line, which dropped the stale copy. Now the wave-0 rebuild of that bundle is built on, and later folded onto, a line that already has its rejected branch. That can show up as a fold conflict, or as old commits riding along in its PR. The brief's "continue, never replace" rule makes this a design choice. A human should decide whether the carry should also check that no drive-set bundle is already on the line (`integrate.read_lines` already has the `_holds` machinery to look). No test covers this case.

- `template/src/pdca_harness/flow.py:2255`: the in-run fold after wave 0 folds only `accepted`. Ids carried by `_carry_finished` are not in it, so a fixup pushed to a carried id's PR branch during the run never reaches the line in this run. The new docs paragraph (`docs/07-crosscutting.md`, "Commits pushed onto a stack PR's branch after a fold carried it reach the line at the next fold") reads as if it applies to carried ids too. This is minor. Either pass the carried ids into later folds (`_merge_published` skips work already on the line, so this is cheap), or say in the docstring that carried ids are folded once.

- `template/src/pdca_harness/flow.py:883-905` vs `flow.py:2252-2283`: the carry's block (fold under an `ExitStack` of locks → record `pushed_tip` per target → `integ.update` → optional `gates.run_integration(..., hold_lock=False)` → STOP) is a near copy of the in-run fold block. The lock and re-gate rules are exactly what sign-off had to send back last round. Having two copies invites them to drift apart again. Suggested cleanup: one helper, e.g. `_fold_and_regate(cfg, bundles, folded_this_run, ...) -> str | None` (None means OK, otherwise the stop reason), used from both places.

- `template/src/pdca_harness/merged.py:99-130` vs `merged.py:67-96`: `pr_state` repeats `merged_head`'s whole `gh pr view --json state,headRefOid` call, including the `OSError` guard and the JSON parse. `merged_head` could become a thin wrapper: `st, head, why = pr_state(cfg.find_bundle(dep_id))`, keep its stderr line when `why` is set, and return `head if st == "MERGED" else None`. That leaves one place that reads PR state.

- `template/src/pdca_harness/integrate.py:271-276` vs `integrate.py:420-428`: `read_lines` copies `fold`'s "take the lock or raise IntegrationError with the permissions hint" block word for word. A small `_take_integ_lock(stack, repo, base)` helper would remove the duplicate. This is cosmetic.

- `template/src/pdca_harness/flow.py:858`, `flow.py:2117-2118`: `publish._resolve_target` (a brief parse) runs once per bundle in the `stuck` list and again for every bundle in every wave whenever `blocked` is non-empty. The cost is small, but the carry already resolves targets for its candidates. Caching `{d.name: target}` for the drive set once would remove the repeat parses. Low priority.

No test-quality problems found. The new file drives the real `_drive_and_act`, `fold`, `publish` and re-gate against real git. It imports modules only, so the red leg fails rather than erroring at import. The lock-order test checks nesting depth, which goes beyond checking that the calls happened.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm prior-art coverage across all affected paths and closed/rejected work — the brief records a path-based search for three modules, but the supplied target has only a synthetic base commit and no remotes, so broader history and rejected-PR conclusions cannot be independently settled (`brief.md:167`; `review-prior-art.log:1`).
- [ ] Validation — fitness-to-purpose — Decide whether the scoped recovery behavior and host coverage suffice after addressing C3 — real Git history, publishing and re-gating ran, but live GitHub/gh state retrieval was not exercised; its evidence rests on mocked host responses, and no-carry runs still replace the line (`template/tests/test_flow_resume_stack_prereqs.py:112`; `docs/07-crosscutting.md:681`).
- [ ] **The continued line keeps a rejected bundle's old commit, and its rebuild ships it.** `_carry_finished` checks only *finished* ids against origin's line (`template/src/pdca_harness/flow.py:798-800`, `:828`, `:836`; `template/src/pdca_harness/integrate.py:281`). It then continues the line exactly as origin has it (`flow.py:873`, `:886`). Failing case: batch `[P, X, D]`. The earlier run folded P and X. X was then rejected and iterated (iterate archives `patch.diff` / `SUMMARY.md` but keeps `publish.json`; its PR is CLOSED). Re-issue: the run drives `[D, X]`, and D has `Depends on: P`. Observed: X's stack base is the old line tip, and **the old X commit is an ancestor of the new X PR branch**. The rejected change rides into X's new PR, and nothing is printed. Before the fix, X was cut from `main`. Sign-off item 3 ("a closed PR's branch must not ride the shared line") is enforced only for finished ids, not for drive-set bundles the earlier run folded. The same gap applies to a finished P whose branch was force-pushed with a rebuilt commit after the earlier fold: `_holds` (`integrate.py:552-566`) looks only for the *current* head's commits, so an old P commit on the line goes unseen. The human needs to decide: extend the on-line check to every requested bundle that has a publish record, or accept and document it.
- [ ] **Following the harness's own advice after a failed `gh pr create` blocks the whole target, and the new advice does not get you out.** Earlier run: P's branch is pushed, `gh pr create` fails, and `publish.json` records `pr_url: ""` (`template/src/pdca_harness/publish.py:405-433`). The in-run fold still folds P (`flow.py:2236-2237`). The publish message says "Open it by hand" (`publish.py:416`). Re-issue `[P, D, U]`: `merged.pr_state` returns "no PR on record" (`template/src/pdca_harness/merged.py:112`). The line holds P, so the target is blocked: D **and the unrelated U** stay PLANNED, and nothing is built (reproduced). Before the fix, U built. The advice "fix what kept issue_P's PR state from being read (its publish.json / `gh`)" (`flow.py:864`) points at no command that works. `pdca publish P` takes the new-PR path, which has no existing-PR lookup (`_existing_pr` is used only by the `Onto branch` path, `publish.py:510`). So `gh pr create` fails again and writes `pr_url: ""` again. The only ways out are hand-editing JSON or deleting the line. The brief's (4d) counts "no `pr_url`" as unreadable, so this is a scope call. Options: look the PR up by its head branch when `pr_url` is empty, or tell the user to edit `publish.json` by name.
- [ ] `template/src/pdca_harness/flow.py:873-886`: once the carry triggers, the run continues the earlier run's line as it is. That line can hold the old branch of a bundle that is back in this run's drive set: it was folded last time, then re-opened or iterated, so it is no longer COMPLETE. Before this patch, the first fold started a fresh line, which dropped the stale copy. Now the wave-0 rebuild of that bundle is built on, and later folded onto, a line that already has its rejected branch. That can show up as a fold conflict, or as old commits riding along in its PR. The brief's "continue, never replace" rule makes this a design choice. A human should decide whether the carry should also check that no drive-set bundle is already on the line (`integrate.read_lines` already has the `_holds` machinery to look). No test covers this case.
- [ ] **The declared target is not the code the brief was written against, and the success criterion can't run there.** The brief says `Repo + branch target: eduralph/pdca-harness @ main` (brief:87), but it says its own line numbers come from `origin/pdca-integration/main @ f594d8e` and that "#591's batch-scoped line name is REQUIRED by this fix and exists only there until PR #639 merges" (brief:4-7). The target checkout I was given (`$PDCA_TARGET`) is the `main` shape, and it lacks everything the criterion calls:
- [ ] **The rewording it plans breaks existing tests that the brief doesn't list.** The scope rewrites the "resuming across runs is #616" text at `publish.py:345`, `:696` and `:726` (brief:114-115). Existing tests check that text word for word:
- [ ] **The problem statement can't be checked against the tracker.** The bundle has no `notes.json` and no `sources/` directory; the cwd holds only `brief.md`. I can't confirm that the #616 thread frames the defect as "re-issued `pdca flow <ids>` builds a dependent without its finished prerequisite". I also can't check the claim that iterations v1-v3 were rejected for "fresh line + carry of any out-of-batch prerequisite" (brief:158-159), or whether a maintainer constraint came with that rejection. The human should confirm the thread before sign-off. The code side does support the hazard: the `_runnable` docstring says so at `flow.py:692-698`, and the out-of-batch COMPLETE acceptance is at `flow.py:706-711`.
- [ ] **Hidden second behaviour change: unrelated bundles get rebased onto the carried line.** The scope points "every same-target runnable wave-0 bundle — including an unrelated `U`" at the carried line, and accepts that "its PR shows the carried changes until they merge" (brief:103-106). That changes how bundles with no dependency on `P` are published. Today such a bundle's wave-0 stack base is cleared (`flow.py:736-742`). None of criteria (1)-(7) covers `U`'s PR diff, so it is unreviewed. Only (4) mentions `U`, and only to say it builds. Either justify it as part of the one fix or make it a criterion.
- [ ] **New PR-state hold policy is close to a second change.** Criteria (4b)-(4d) add new gating logic:

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected at sign-off (attempt 2): the approach is still right, and last round's four fixes (lock, re-gate, closed PR already on the line, wording) are in. The remaining gaps share one cause: the continued line is trusted too much. Fix these in the rebuild, each with a regression test: 1. Unresolvable head = unknown, not absent. When a finished id's host-reported head cannot be resolved locally (e.g. a fixup was pushed, then the PR was closed and the branch deleted before we fetched), `integrate._holds` / the check at `integrate.py:~560` must not answer "not on the line". Treat it as unknown: block that target's wave-0 bundles and name it on stderr (do not print "is not carried"). Test: the reviewer's deleted-branch-after-fixup case (review C3 FAIL). 2. Check every requested id against the line, not only finished ones. Before continuing origin's line, check every requested id that has a publish record, including drive-set bundles the earlier run folded and that were since rejected/iterated (PR CLOSED, no longer COMPLETE). Their old commits must not ride into the rebuilt PR. Also catch an old commit of a finished id whose branch was force-pushed with a rebuild since the earlier fold (looking only at the current head misses it). If such commits are on the line, fail closed for that target, the same way as the closed-PR case. 3. Empty `pr_url` must not be a dead end. If the earlier run's `gh pr create` failed (`publish.json` has `pr_url: ""`) and the line holds that id, do not block the whole target with advice that doesn't work. Either look the PR up by its head branch when `pr_url` is empty, or make `pdca publish <id>` able to recover it, and print advice that actually gets the user unstuck. Optional cleanup from the code review: share one helper for the fold + lock + tip read + re-gate block between the carry and the in-run fold, so they cannot drift apart again.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
