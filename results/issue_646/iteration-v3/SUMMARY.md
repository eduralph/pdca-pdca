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

Review re-issued stack-mode flows so finished prerequisites remain on the batch’s integration line, unsafe prior work is refused, and dependents resume on the correct base.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief and its two carry-forward amendments define observable resume, refusal, locking and recovery outcomes, with explicit no-carry and out-of-batch limits; target/template/tests/test_flow_resume_stack_prereqs.py:20 and target/docs/07-crosscutting.md:665 ground the intended behavior. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the regression tests produced 26 assertion failures in 31 tests, including the dependent missing its prerequisite; target/template/tests/test_flow_resume_stack_prereqs.py:360; reviewer-red.log:365 and reviewer-red.log:815. |
| C3 Change | FAIL | A recovered PR with an empty recorded URL stops the entire resumed run after merge and branch deletion, even when its head is already on both base and line: the new lookup’s MERGED result never reaches the fold’s URL-only lookup; target/template/src/pdca_harness/merged.py:144, target/template/src/pdca_harness/integrate.py:524; independently reproduced in reviewer-edge.log:7. |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the unexercised GitHub/gh dependency needs live confirmation before acceptance — independent offline red→green is established (26 failures → all 77 selected tests passing), but host responses are a Python table and PR creation is bypassed, so actual host lookup/recovery is not verified; target/template/tests/test_flow_resume_stack_prereqs.py:105 and target/template/tests/test_flow_resume_stack_prereqs.py:304; reviewer-green.log:211. |
| C5 Causal adequacy | PASS | Carrying finished requested prerequisites before wave 0 removes their omission from the build base; commit-accounting refuses unsafe continued history, and the shared fold helper preserves locking through tip capture and re-gating; target/template/src/pdca_harness/flow.py:770 and target/template/src/pdca_harness/flow.py:918; no capability probe conceals an eager/load-time cause. |
| T1 Structure | PASS | The pre-wave and in-run paths share the fold/lock/re-gate operation, while host lookup and commit accounting remain in their existing modules, limiting divergence between the two paths; target/template/src/pdca_harness/flow.py:754 and target/template/src/pdca_harness/flow.py:2352. |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, production-import scanner and diff whitespace check passed; the frozen docs and host-parity logs agree; target/docs/publishing/tools/lint_docs.py:1, gate-logs/T2-docs.log:10 and gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent driver suite: 2,356 tests, OK with two skips; root render/update coverage is supported by the frozen 24-test pass, because local Python cannot import copier (a reviewer-host caveat, not a patch failure); reviewer-suite.log:1984, gate-logs/T3-suite.log:54 and reviewer-root-suite.log:6. |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the recorded deferred row requires the substantive contribution audit at publish, so no contribution verdict is due now; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for all affected paths — the brief records a path-based search for flow/integrate/merged, but this target has only one synthetic base commit and no remotes, so the expanded surface and prior dispositions cannot be independently settled; brief.md:167 and target/template/src/pdca_harness/merged.py:98. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the resumed-flow behavior and recovery burden fit the intended workflow after addressing the reproduced defect — unsafe lines hold an entire target and may require deleting the line/rebuilding bundles, while no-carry runs still start fresh; target/template/src/pdca_harness/flow.py:993 and target/docs/07-crosscutting.md:679. |

**Finding — P2: preserve recovered PR identity through deleted-branch folding.**

A previous publish can push P’s branch but fail to record a PR URL. The user subsequently opens that PR, merges it, and deletes its branch. On a re-issued `[P, D]` run, `pr_state` successfully finds the MERGED PR by branch and returns its head (`target/template/src/pdca_harness/merged.py:135`). The carry accepts it (`target/template/src/pdca_harness/flow.py:890`). However, `_merge_published` sees the deleted branch and calls `_gone_branch`, which calls `merged_head`; that function returns `None` immediately when the recorded URL is empty (`target/template/src/pdca_harness/merged.py:75`). The run stops before wave 0 with the incorrect claim that the PR is not known to be merged.

The independent probe actually merges P into the local bare origin’s main and preserves the earlier integration line. Both contain P’s head, but D remains PLANNED. Recording only the URL already returned by the branch lookup makes the same run complete. This isolates the lost lookup result, rather than absent commits or a stale target, as the cause. The existing tests cover branch lookup and merged/deleted branches separately (`target/template/tests/test_flow_resume_stack_prereqs.py:602` and `target/template/tests/test_flow_resume_stack_prereqs.py:834`), leaving their combination uncovered. Carry the recovered identity/state into the deleted-branch decision, or make that decision use the same recovery lookup; cover the combination with a regression test.

Run `python3 reviewer-probe.py` from this review directory to reproduce. Its final assertion intentionally fails on the submitted patch; `reviewer-edge.log:7` records the original failure and `reviewer-edge.log:16` the successful URL-recorded control. All git operations in this probe use local fixture repositories, and host responses remain simulated.

**Evidence and limits.** The supplied target was readable and contained the required batch-scoping API; no stale-target substitution was necessary. Production changes were stashed only for the independent red leg and restored before green checks. Submitted source and tests were not edited.

The independent red command was `PYTHONPATH=src python3 -m unittest discover -s tests -p test_flow_resume_stack_prereqs.py` from `target/template`; green used `-p 'test_*stack*py'`, and the full driver run used `python3 -m unittest discover -s tests`. All used `TMPDIR` inside this review directory and disabled bytecode writes. Frozen C4 evidence also shows 31 new tests and 46 existing stack tests green, then 26 and two assertion failures respectively without production changes (`gate-logs/C4-verify.log:199`, `:226`, `:1044`, `:1091`).

The instance-scoped wrappers are not needed to establish their available underlying checks: docs lint/render and the production-import scanner were rerun directly. Local `python3 -m tests.run_root_suite` exited 77 because copier is not importable by this interpreter; the frozen log supplies actual render/update execution, so this local limitation does not invalidate T3. T4’s deferred result remains N/A. No additional configured human-only rules can be inferred from the template’s unfilled INTEGRATION §4 (`target/template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation was limited to the supplied target: path-filtered `git log --all` returns only `3cfb4ce pre-fix base 12405dc952a556b710993014cc55d374a74c60f8`, and `git remote -v` returns nothing. The brief’s recorded merged/closed/rejected searches are acknowledged, but are not independently confirmed for every changed path. No other checkout was inspected.

This review is advisory; the C3 finding and human decisions annotate acceptance rather than introducing a deterministic gate.

### Advisory — adversary

# Adversarial review — issue_646, attempt 3

I couldn't refute the main fix. The red→green proof holds, and the carry, the vouch check, the lock and the re-gate all did what they claim in every case I tried. I found two concrete inputs where the re-issued run now does worse than before, or gives advice that doesn't work. Scratch tests for each are in `scratch/` next to this file.

## Attempts that did not land

- **The red→green proof holds.** In `gate-logs/C4-verify.log`, the red leg has 26 FAILs in the new file and 2 in the updated wording tests, with no import errors. Each one fails on a real assertion: there is no line on origin before D's wave (`template/tests/test_flow_resume_stack_prereqs.py:368`), the earlier line gets force-pushed (`:438`), and bundles get built on a line that should be refused (`:461`). I re-ran both files at `$PDCA_TARGET`: 77 tests OK.
- **The tests use the production code, not a copy.** They call the real `flow._drive_and_act`, the real `integrate.fold` against a bare origin, and the real `publish.publish` with `open_pr=False`. Only three things are stubbed: `_drive_wave`, `draft_texts`, and the `gh` calls that `merged.py` makes (`test_flow_resume_stack_prereqs.py:271`, `:287-308`).
- **A wave-1 bundle on the earlier line is handled.** No test covers this case: the earlier run stopped after wave 1, so its line holds D, whose branch was cut from the line. I ran it in scratch (`scratch/attack_wave1.py`). `_own`'s cut logic (`template/src/pdca_harness/integrate.py:589-596`) vouched for D's commit, the line was continued without force, and E built on it. It works, but it is the most common real re-issue shape and only an in-run fold exercises that path. Consider adding a test for it.
- **Failure modes on the new paths are soft.** `publish._resolve_target`, `publish._fork_owner` and `integrate._rev` all return empty or None instead of raising, so the refusal and lookup paths can't throw a traceback. The owner match in `merged.pr_state` is the same exact compare that `publish._existing_pr` already uses (`template/src/pdca_harness/publish.py:580-583`), so it adds nothing new.
- **`check-gates.json` makes no claim it can't back.** C2 has no gate configured; the red evidence comes from C4 instead. T4 is deferred to publish.

## Findings

- NEEDS-HUMAN — **A squash-merged prerequisite now stops the whole run, where before it built fine.** `template/src/pdca_harness/flow.py:891` carries a MERGED P. If P's branch is gone and its PR was squash- or rebase-merged, the fold raises at `template/src/pdca_harness/integrate.py:548`, and `flow.py:932` stops the run before wave 0.
  - **Concrete case:** `flow P D U`, where P is COMPLETE and was squash-merged into `main` with its branch deleted, D has `Depends on: P`, and U is unrelated (`scratch/attack_squash.py`).
  - **Before the patch:** D and U both reach COMPLETE. D builds on `main`, which already has P's change.
  - **After the patch:** nothing is driven, and the advice says "get that work into origin/main", which by content is already true. Re-issuing the same command stops again every time. The only ways out are to restore P's branch, which puts the pre-squash commits on the line, or to drop P from the ids, which changes the batch and so the line.
  - **Why this is for a human, not the builder:** brief criteria (5) and (6) asked for exactly this ("otherwise raise", and a raise stops the run), and the docs already say never squash (`docs/07-crosscutting.md:647`). A human should decide whether such a P should stop everything, including the unrelated U, or count as "nothing to carry".
- NEEDS-HUMAN [impl] — **A closed PR that was replaced by a new one blocks the whole target, and the advice doesn't work.** `template/src/pdca_harness/merged.py:118-125` only asks about the `pr_url` recorded in `publish.json`. The lookup by branch only runs when that field is empty.
  - **Concrete case:** P's recorded PR is CLOSED, a newer OPEN PR exists for the same branch `fix/P`, and the earlier line holds P (`scratch/attack_superseded.py`).
  - **Result:** `gh pr list` is never called. P is treated as closed (`flow.py:894-898`), the target is blocked so D and the unrelated U are not built, and the advice is "re-open issue_P's PR". GitHub generally won't reopen a PR while another open PR has the same head and base, so the only advice that works is "delete the line", which strands any bundle recorded on that line. Iteration 2's sign-off said exactly this: advice must not be a dead end.
  - **Fix:** when the recorded PR is CLOSED, fall back to the same `gh pr list --head` lookup used for an empty `pr_url`, and add a test for it.
- **Two wording slips in the docs (minor).**
  - `docs/07-crosscutting.md:670-671` says the run "builds all of wave 0 on it". In fact only wave-0 bundles with the same (repo, base) target are pointed at the line (`flow.py:745-751`).
  - `docs/07-crosscutting.md:674` says a finished id that can't be carried "holds only the bundles that depend on it". Only plain `Depends on` dependents are held (`flow.py:719`); a `Stacks on` dependent is still built, as the brief intends.

### Advisory — code-review

# Advisory code review — issue #646 (stack-reissue-continues-batch-line)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.

I found no correctness bug that needs a human decision or a rebuild. I checked:

- The lock scope. `_fold_and_regate` holds the lock through fold, `pushed_tip` and re-gate.
- `LineRefused` is re-raised before the general `IntegrationError` handler, so the two are not mixed up.
- The `vouch` path in `fold`: it is only reached when `start == "auto"`, it skips a missing line, and a push of a vouched line with nothing to fold is unforced.
- The `integ.update` change. It is the same as the old rebinding, because every in-run fold is cumulative.
- The `_runnable` widening is limited to plain `Depends on`.
- A blocked target is kept out of later waves too, so no later fold can force-push over a refused line.

All gates pass (T3: 2356 tests OK). The findings below are small cleanups and one weak spot in a message.

- `template/src/pdca_harness/merged.py:152` — Reuse: the new `_gh` / `_json` / `_head` helpers repeat the `gh pr view … --json state,headRefOid` call, the `OSError` guard and the JSON parsing that `merged_head` already does (`merged.py:66-95`). `merged_head` could be rewritten on top of `_gh`/`_json`/`_head`, or on `pr_state` itself (MERGED ⇒ head), so the missing-`gh` guard lives in one place. Behaviour would not change. This is a cleanup, not a defect.
- `template/src/pdca_harness/flow.py:899-902` — Duplication: the `pr == "NONE"` branch re-reads `publish.json` and recomputes the repo fallback and `OWNER:BRANCH` (`publish._pr_head`). `merged.pr_state` just computed the same values (`merged.py:129-133`) and put them in `note`. The two repo fallbacks agree today (`rec["repo"] or` the brief's target), but they are written twice. Returning `head_spec` and the repo from `pr_state`, for example in a small record, would remove the second copy.
- `template/src/pdca_harness/flow.py:968-969` — Message weak spot, not a safety issue. A carried bundle whose branch was force-pushed with a rebuild leaves its old commits on the line. `integrate.holds` measures against the *current* head, so it returns an empty set for that bundle, and `_say_refused` skips it. The refusal line then names no bundle and offers only "delete the line". It is still correct to fail closed here, and the merge commit's subject (`pdca-integrate: issue_P`) in "brought in by …" points the reader to the bundle. A clause such as "it may hold an earlier version of P" would be clearer. Cosmetic: no NEEDS-HUMAN.
- `template/src/pdca_harness/integrate.py:583` — Efficiency, refusal path only: `entries` runs one `git rev-list` per first-parent commit of the line. That is fine at real line lengths (a handful of folds) and only runs when the line is refused. No action needed.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Decide whether the unexercised GitHub/gh dependency needs live confirmation before acceptance — independent offline red→green is established (26 failures → all 77 selected tests passing), but host responses are a Python table and PR creation is bypassed, so actual host lookup/recovery is not verified; target/template/tests/test_flow_resume_stack_prereqs.py:105 and target/template/tests/test_flow_resume_stack_prereqs.py:304; reviewer-green.log:211.
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art for all affected paths — the brief records a path-based search for flow/integrate/merged, but this target has only one synthetic base commit and no remotes, so the expanded surface and prior dispositions cannot be independently settled; brief.md:167 and target/template/src/pdca_harness/merged.py:98.
- [ ] Validation — fitness-to-purpose — Decide whether the resumed-flow behavior and recovery burden fit the intended workflow after addressing the reproduced defect — unsafe lines hold an entire target and may require deleting the line/rebuilding bundles, while no-carry runs still start fresh; target/template/src/pdca_harness/flow.py:993 and target/docs/07-crosscutting.md:679.
- [ ] **A squash-merged prerequisite now stops the whole run, where before it built fine.** `template/src/pdca_harness/flow.py:891` carries a MERGED P. If P's branch is gone and its PR was squash- or rebase-merged, the fold raises at `template/src/pdca_harness/integrate.py:548`, and `flow.py:932` stops the run before wave 0.
- [ ] **A closed PR that was replaced by a new one blocks the whole target, and the advice doesn't work.** `template/src/pdca_harness/merged.py:118-125` only asks about the `pr_url` recorded in `publish.json`. The lookup by branch only runs when that field is empty.
- [x] **The declared target is not the code the brief was written against, and the success criterion can't run there.** The brief says `Repo + branch target: eduralph/pdca-harness @ main` (brief:87), but it says its own line numbers come from `origin/pdca-integration/main @ f594d8e` and that "#591's batch-scoped line name is REQUIRED by this fix and exists only there until PR #639 merges" (brief:4-7). The target checkout I was given (`$PDCA_TARGET`) is the `main` shape, and it lacks everything the criterion calls:
- [x] **The rewording it plans breaks existing tests that the brief doesn't list.** The scope rewrites the "resuming across runs is #616" text at `publish.py:345`, `:696` and `:726` (brief:114-115). Existing tests check that text word for word:
- [x] **The problem statement can't be checked against the tracker.** The bundle has no `notes.json` and no `sources/` directory; the cwd holds only `brief.md`. I can't confirm that the #616 thread frames the defect as "re-issued `pdca flow <ids>` builds a dependent without its finished prerequisite". I also can't check the claim that iterations v1-v3 were rejected for "fresh line + carry of any out-of-batch prerequisite" (brief:158-159), or whether a maintainer constraint came with that rejection. The human should confirm the thread before sign-off. The code side does support the hazard: the `_runnable` docstring says so at `flow.py:692-698`, and the out-of-batch COMPLETE acceptance is at `flow.py:706-711`.
- [x] **Hidden second behaviour change: unrelated bundles get rebased onto the carried line.** The scope points "every same-target runnable wave-0 bundle — including an unrelated `U`" at the carried line, and accepts that "its PR shows the carried changes until they merge" (brief:103-106). That changes how bundles with no dependency on `P` are published. Today such a bundle's wave-0 stack base is cleared (`flow.py:736-742`). None of criteria (1)-(7) covers `U`'s PR diff, so it is unreviewed. Only (4) mentions `U`, and only to say it builds. Either justify it as part of the one fix or make it a criterion.
- [x] **New PR-state hold policy is close to a second change.** Criteria (4b)-(4d) add new gating logic:

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
- Iteration delta (if iterating): Rejected at sign-off (attempt 3): the approach is still right, and the round-1 and round-2 fixes are all in. Round 3 found three more gaps in the cross-run recovery logic. Fix each one and add a regression test for each: 1. Recovered PR identity is lost before the deleted-branch decision (review C3 FAIL, `reviewer-probe.py`). When `pr_url` is empty, `merged.pr_state` finds the MERGED PR by branch, but `integrate._gone_branch` -> `merged.merged_head` reads only the recorded URL and returns None, so the run stops before wave 0. Pass the recovered URL/state into the deleted-branch decision, or have that decision use the same branch lookup. Test the combination: empty pr_url + merged + branch deleted. 2. Squash- or rebase-merged prerequisite with its branch deleted (adversary, `scratch/attack_squash.py`). The fold raises at `integrate.py:~548` and the whole run stops, including unrelated bundles. Before the patch this case built fine. The re-issued command stops again every time, and the advice ("get that work into origin/main") is already true. A re-issue must not stop forever with advice that doesn't work. Criteria (5)/(6) asked for "otherwise raise", but no recovery policy was chosen at sign-off: pick one, state it in build-notes, and test it. 3. A closed PR that a newer open PR replaced (adversary, `scratch/attack_superseded.py`). `merged.pr_state` asks only about the recorded `pr_url`. When that PR is CLOSED, also run the same `gh pr list --head` branch lookup used for an empty `pr_url`, and use an OPEN/MERGED PR if one exists. Today the advice "re-open the PR" doesn't work, because GitHub won't reopen a PR while another open one uses the same head branch. Optional (adversary/code-review): fix the two doc wording slips at `docs/07-crosscutting.md:670-674` (only same-target wave-0 bundles are pointed at the line; only plain `Depends on` dependents are held), and build `merged_head` on the new `_gh`/`_json`/`_head` helpers.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
