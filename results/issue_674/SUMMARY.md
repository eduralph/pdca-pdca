# Result — issue 674 / same-wave-conflict-holds-one-bundle-not-the-run

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode, when two bundles in the same wave both pass Check but their branches conflict textually, nothing finds that until the fold, and then the whole run stops. `_audit_wave_overlap` (`template/src/pdca_harness/flow.py:1004-1019`, called at `flow.py:2271`) only prints a file-level warning for any two bundles that touch the same file, whether or not they actually conflict. The fold that follows (`flow.py:2339-2346` → `_fold_lines` → `integrate.fold`) merges each accepted bundle's published branch onto the line in name order. The second branch of the pair fails in `integrate._merge_published` (`template/src/pdca_harness/integrate.py:508-515`) with "does not merge cleanly … an undeclared cross-wave overlap", and `flow` prints "wave k did not integrate … STOPPING — later waves not run" and `break`s (`flow.py:2343-2346`). Every later wave is dropped, including bundles that have nothing to do with the pair. The message names only the branch that failed, not the bundle it conflicts with, and calls a same-wave clash "cross-wave". Seen for real: #623 and #631 in one wave, both adding an `IntegrationError` subclass at the same spot in `integrate.py` and editing the same `if skipped is None …` line in `fold`.
- Success criterion: On a real-git stack-mode run (the `StackFoldGit` fixture of `template/tests/test_integrate_stack_bases.py`, driven through `flow._drive_and_act(cfg, drive, do_publish=True, do_act=False, by=…, today=…, batch=…)` with the publisher NOT stubbed, exactly as `template/tests/test_flow_resume_stack_prereqs.py:123-147` does), with the batch: `10`, `11`, `12` with no dependencies (wave 0); `20` with `Depends on: 11` and `21` with `Depends on: 12` (wave 1); `30` with `Depends on: 21` (wave 2). The third wave is there so wave 1 also folds (a fold runs only when `k < len(wave_list) - 1`, `flow.py:2315`), and every fold re-passes all of `accepted` (`flow.py:2135`, `:2341`), so a hold that lasts only one fold would show up here. The stubbed build for `10` and `11` both change the same line of one file (`shared.txt`, present on the base) to different text; `12` adds an unrelated file; `20`, `21` and `30` add their own files. Each bundle's `patch.diff` names the files it changes.
  (1) **Held, not stopped.** The run does not print "did not integrate" and does not stop. `11` (the later of the pair in the wave's name order, which is the fold's merge order) is left out of the fold; `10` and `12` are on the integration line (their branch tips are ancestors of the line's tip). `21` is built on that line (its recorded stack base is the run's line, and the line it was built on contains `10` and `12` but not `11`) and ends COMPLETE. `20` is never built and is left PLANNED, because its prerequisite `11` is held. The wave-1 fold also leaves `11` out (the hold lasts for the whole run, not one fold), and `30` is built on the line after that fold and ends COMPLETE. `20`'s skip line may be `_runnable`'s existing generic "skipped — prerequisite(s) not ready (11)" (`flow.py:762-764`); that wording is accepted on purpose here (confirmed by the human at plan sign-off, 2026-10-14), because the end-of-run line in (2) names the conflict, and rewording `_runnable`'s message would edit the code in-flight bundle 629 also edits.
  (2) **Named by pair and file, before the next wave.** A stderr line, printed during or right before the wave's fold and before the next wave starts building, names both `issue_10` and `issue_11` and `shared.txt`, and says `issue_11` was held out of the integration fold because its change conflicts with `issue_10`'s. A line at the end of the run (after the last wave, alongside the existing end-of-run reports) repeats the pair, the file, and the step to take: declare `Conflicts with: 10` in `issue_11`'s brief (a proposal for the human to confirm), then rebuild `issue_11` on a base that holds `issue_10`. No `brief.md` in the batch gains a `Conflicts with:` line from the run.
  (3) **A shared file that merges cleanly changes nothing.** Same batch, but `10` and `11` change different, non-adjacent lines of `shared.txt` (they merge cleanly). Both are folded, `20` and `21` are built and COMPLETE, nothing is held, and stderr has no new line beyond today's `_audit_wave_overlap` warning for the pair.
  (4) **Three-way chain: only the bundle that really conflicts is held.** A separate batch, one wave plus a dependent wave so it folds: `40`, `41`, `42` with no dependencies, and `50` with `Depends on: 42`. `chain.txt` on the base has nine lines. `40` changes line 2; `41` changes lines 2 and 8 (other text); `42` changes line 8 (other text again). So `40`–`41` and `41`–`42` conflict, `40`–`42` merge cleanly. Result: `40` and `42` are folded, only `41` is held (with a line naming `issue_40` as the partner), and `50` is built and COMPLETE. A pair-by-pair rule that holds `42` because of the already-held `41` fails this.
  Pre-fix, (1), (2) and (4) fail: the run stops with "wave 0 did not integrate (issue_11's branch … does not merge cleanly …)", and `21` is never built; in (4) the run stops at `41` and `50` is never built. (3) passes before and after (it guards against holding on file overlap alone). That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: In the stack-mode wave loop, after the wave publishes and before its fold (only where a fold runs: not the final wave, publishing on, not a dry-run), find which same-wave accepted bundles' published branches really conflict with each other, and hold per the Invariant's rule (in the fold's merge order, against the bundles already kept, not pair by pair), holding its dependents through `_runnable`; the hold lasts for every later fold in the run, report it per criterion (2), and let the run continue. Held bundles are reported in the end-of-run output. Keep `_audit_wave_overlap`'s existing warning as it is. Prior mechanism to reuse: `integrate.fold` already has a per-bundle skip-on-conflict mode, the `skipped=` dict from #646 (`integrate.py:351-360`, `:465-474`; passed through `_fold_lines`, `flow.py:790-811`). It merges in order, undoes a failed merge and goes on to the next bundle, which is the sequential check the Invariant needs. Do should use it (or say in `build-notes.md` why not) rather than build a second merge path beside the fold. Used as-is it would also swallow a conflict with earlier-wave work, which must still stop; Do must tell the two apart (the Invariant's "merges cleanly onto the line without them" test) and name the kept partner(s) a held bundle conflicts with. Tie-break: the bundle kept is the one earlier in the fold's merge order, which is a name sort (`flow.py:2269`, `integrate.py:295-296`). This departs from the issue's "keep the lower-id bundle" only when ids have different digit counts (`issue_100` sorts before `issue_99`); changing the fold's order is out of scope. Confirmed by the human at plan sign-off (2026-10-14). / out of scope: changing any brief automatically; a conflict between a bundle and work already on the line from an earlier wave (the fold still stops on it, as today); improving the fold's own "did not integrate" message (the issue's "optionally" item); merge mode (`wave_mode = "merge"`); dry-run / stubbed-publisher runs; Plan-time or pre-publish detection and re-sequencing (#395 layers 1-2); closing or editing the held bundle's draft PR (it stays as published).

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

Review issue #674: hold conflicting same-wave bundles and their dependents/declared conflict partners while allowing unrelated stack-mode waves to continue.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable continuation, ordering, reporting, persistence, and clean-overlap outcomes, with earlier-wave conflicts remaining stops; `brief.md:11`, `brief.md:18`, `target/template/tests/test_flow_same_wave_conflict.py:200`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix reproduced four behavioral assertion failures, including the unwanted run stop; the additional new-API TypeError is not the basis for this verdict; `review-red.log:30`, `review-red.log:39`. |
| C3 Change | PASS | The changes stay within stack-fold conflict isolation, downstream holds, recovery messages, documentation, and regression coverage; final-wave and merge-mode scope boundaries remain intact; `target/template/src/pdca_harness/flow.py:2421`, `target/template/src/pdca_harness/flow.py:2451`. |
| C4 Verification (red→green) | PASS | Restoring the patch makes all eight regression tests pass after the independently observed behavioral red, including both outcomes when the base changes mid-wave; `review-green.log:1`, `review-green.log:11`, `target/template/tests/test_flow_same_wave_conflict.py:401`. |
| C5 Causal adequacy | PASS | Real sequential Git merges distinguish a same-wave clash from clean overlap and earlier-wave/base-only conflicts; both carry-forward defects are covered, and no optional-capability probe masks a load-time cause; `target/template/src/pdca_harness/integrate.py:902`, `target/template/tests/test_flow_same_wave_conflict.py:292`, `target/template/tests/test_flow_same_wave_conflict.py:401`. |
| T1 Structure | PASS | Conflict classification stays inside the existing locked fold; trial merges restore the original line, and run-level holds remain excluded from subsequent folds; `target/template/src/pdca_harness/integrate.py:475`, `target/template/src/pdca_harness/integrate.py:937`, `target/template/src/pdca_harness/flow.py:2452`. |
| T2 Shape | PASS | Independently rerun docs lint, 22-page rendering/internal-link audit, production-import scanner, and diff whitespace check pass; these match the frozen docs and host-parity evidence; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`, `target/.github/workflows/docs-check.yml:33`. |
| T3 Runtime | PASS | Independent driver run passes 2,450 tests with two skips; frozen evidence also shows 24 root-suite tests passing, while this reviewer host cannot rerun Copier-dependent cases; `review-suite.log:1817`, `gate-logs/T3-suite.log:54`, `review-root-suite.log:6`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; the substantive contribution audit must rerun at publish, as the deferred gate records; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm the prior-art disposition for affected paths — the brief records merged-history and closed/unmerged-PR checks for flow/integrate, but this one-commit snapshot has no remote or PR records to independently exclude superseding or rejected work; `brief.md:29`, `target/template/src/pdca_harness/integrate.py:884`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the run-local hold and proposed manual rebuild workflow as sufficient for #674 — automated tests demonstrate continued unrelated work and truthful conflict reports, but operational adequacy remains a maintainer decision; `target/docs/07-crosscutting.md:696`, `target/template/src/pdca_harness/flow.py:1092`. |

Evidence and limits:

- Grounding used only the supplied `$PDCA_TARGET` (`target/`) and review artifacts. The target is readable and contains the patch; `git apply --reverse --check ../patch.diff` succeeds after restoration. No stale-target defect was inferred, and no implementation files were edited.
- Independent red→green command: from `target/template`, `PYTHONPATH=src python3 -m unittest tests.test_flow_same_wave_conflict`, first with tracked changes stashed and then restored. The untracked regression test remained present. Red: four assertion failures, one expected incompatibility error from the new `held_out` argument, three passing tests. Green: eight passing tests. The behavioral assertions, not that argument error, establish reproduction.
- Independent runtime command: from `target/template`, `PYTHONPATH=src python3 -m unittest discover -s tests`. Result: 2,450 tests, exit 0, two skips. Regression tests exercise actual Git commits, pushes to a local bare origin, merge conflicts, ancestry, and worktree restoration. Build/sign-off and host responses use the explicitly planned fixture boundaries; this is not live GitHub validation. Python 3.14.4 and Git 2.53.0 were available; no new Git feature/version dependency was introduced by the patch.
- The root-suite rerun (`python3 -m tests.run_root_suite`) exited 77 because Copier is not importable by the local interpreter. Its skipped cases are not claimed as local verification. The frozen gate log records 24 root-suite tests actually executed successfully (`gate-logs/T3-suite.log:54`), followed by 2,450 driver tests (`gate-logs/T3-suite.log:1874`); this local toolchain limitation is not a patch defect or an undischarged dependency in that frozen run.
- Docs checks ran directly from the target using the commands in its CI workflow; site output and temporary test data were confined to this review cwd. The production-import scanner was rerun with `PDCA_PROD_PACKAGE=pdca_harness` and this bundle's patch. All six supplied gate logs were read; the instance-scoped wrapper paths were not treated as missing target tools.
- Prior-art investigation: `git log --all -- template/src/pdca_harness/flow.py template/src/pdca_harness/integrate.py` exposes only synthetic base commit `eff6948`; `git remote -v` returns nothing. The path-based history and closed-work check is documented in the brief, but its disposition cannot be independently settled here. The supplied target has only the generic `template/docs/INTEGRATION.md.jinja:80` placeholder for additional project-defined human-only items, not a populated instance ruleset.

No grounded builder-fixable defect was found. This review is advisory; the two NEEDS-HUMAN decisions above remain for sign-off, and the deferred contribution audit remains owed at publish.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Adversarial review — issue 674 (same-wave conflict holds one bundle, not the run)

Verdict: I could not refute the fix on the paths the brief names. The red→green proof
holds, the test drives production code, and every attack scenario I ran came out right,
except one rare same-wave case that the patch deliberately stops on. Two items below are
for the human to decide. None is a defect the builder should rebuild for.

## Evidence I re-ran

- Green: `tests.test_flow_same_wave_conflict` on the patched tree at `$PDCA_TARGET`, with
  8/8 passing. Red: on a copy with `template/src`, `docs` and `template/PCDA` reverted,
  4 tests fail and 1 errors (the same result as `gate-logs/C4-verify.log`). The 3 that
  pass before the fix are the guard cases (criterion 3, the earlier-wave stop, and the
  stop on a base taken in mid-wave), which is what they should do.
- Production path: the test calls the real `flow._drive_and_act` and the real
  `integrate.fold` against real git (a bare origin). Only the build leaf, `_publish_bundle`,
  `draft_texts` and `gh` are stubbed, the same way the peer
  `test_flow_resume_stack_prereqs.py` does it. It is not a copy of the production code.

## Findings

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:541-544` (a gone branch,
  `head is None`, is never added to `kept`) together with the `kept` guard at `:531-532`:
  a real same-wave textual conflict still stops the run when the earlier bundle of the
  pair had its PR merged and its branch deleted between publish and fold. Concrete case
  (I ran it): wave 1 is `20` and `22`, which both change line 2 of `shared.txt`, plus `23`,
  with `30` depending on `23`. Right after the wave publishes, 20's PR merges and
  `fix/20` is deleted. The fold takes main in for 20, `kept` is empty, and 22 raises:
  "wave 1 did not integrate (issue_22's branch … — an undeclared cross-wave overlap)
  … STOPPING", and `30` is never built. The brief's Invariant says a same-wave conflict
  costs "never the run". The patch documents this as a deliberate stop
  (`docs/07-crosscutting.md:706-709`), following the round-2 guidance. A possible
  extension: add `(name, merged_head)` to `kept` for a gone bundle of the wave, so
  `_held_by` can name it as the partner. It needs a human to merge a just-opened draft PR
  within minutes, so it is rare. Decide whether the documented exception is acceptable.
- NEEDS-HUMAN [human] — `template/src/pdca_harness/cli.py:690` together with
  `flow.py:2490`: a run whose only problem is a held bundle with no dependents now exits 0.
  Concrete case (I ran it): batch `10`, `11`, `12`, `21` (`Depends on: 12`), where 10 and
  11 change the same line. Results are all COMPLETE, so `_results_rc` returns 0. The only
  signal is two stderr lines, while 11's open draft PR is known to conflict with 10's.
  Before the fix the same batch exited 1 (the fold stopped and 21 stayed PLANNED). This
  matches the existing #593 `held_unpushed` behaviour, so it is a policy choice, not a
  bug. Decide whether a conflict hold should fail the run's exit code.
- Out of this diff's scope, noted for context: re-issuing the same `pdca flow <ids>` after a
  hold (the recovery the docs recommend) keeps `20` held through the existing #646 carry,
  which is correct. But that carry's line (`flow.py:913`) calls the clash "an undeclared
  cross-wave overlap" (`integrate.py:630`). It also tells the user to "get issue_11's PR
  open … (re-open it, `pdca publish 11`, …)", though the PR is already open, and the #674
  end-of-run proposal is not repeated. The brief puts the fold's message out of scope, so
  this is not filed for rebuild.
- Minor test nit, not filed: `template/tests/test_flow_same_wave_conflict.py:329-339`
  calls `integrate.fold(..., held_out=..., wave=...)`, keywords the fix adds. With the fix
  reverted it fails with `TypeError` rather than on an assertion, so this one case cannot
  go red for the right reason. The other four red cases carry the proof, so C4's verdict
  stands.

## Refutation attempts that failed (the fix held)

- Three-way chain (40/41/42): only 41 is held, and 42 is judged against the bundles kept,
  not the held one. Covered by the test, and I confirmed the logic at `integrate.py:902-908`.
- Holds in two successive waves (11 in wave 0, 21 in wave 1): both stay off the final
  line, only 31 (which depends on 21) is skipped, and both appear in the end-of-run report.
- The hold lasts the whole run: later folds leave `held_conflict` out at `flow.py:2452-2453`.
  `carried` never records a held bundle, because `took` is only written in the `else` branch.
- A conflict with earlier-wave work, or only with a base taken in mid-wave, still stops
  the run (`_held_by`'s two `return None` paths). Both are tested.
- The "name every kept bundle" fallback at `integrate.py:908` rarely fires. Git treats
  edits on adjacent lines as a conflict (I checked: K1 line 3, K2 line 5, H line 4 conflicts
  pairwise with each), so the pairwise check finds the real partner.
- The tie-break between ids of different lengths: `waves.compute_waves` orients a
  `Conflicts with` pair by name (`waves.py:200-212`), the same order the fold uses. So the
  proposed `Conflicts with: 100` in issue_99's brief really does build 99 after 100.
- Integration tree state: `_trial` restores the branch tip or raises `_LineBroken`, and
  the test checks that the tree is clean and on the branch afterwards. No new git feature
  is used (`checkout --detach`, `merge`, `reset --hard` and `clean` are already relied on).
- The gate rows in `check-gates.json` (C4, C5, T2, T3) match their logs. I found no claim
  there that the evidence does not support.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 674 (same-wave conflict holds one bundle, not the run)

Lens: correctness bugs the patch adds, plus reuse / simplification / efficiency. Grounded on `$PDCA_TARGET` (patched tree on the pre-fix base). Gate logs read: C4 (red leg fails 4 cases and errors 1 — the direct `fold(..., held_out=)` call; none are import failures), T3 (2450 tests OK), C5 (production package imported).

No correctness bug found in the diff. The iteration-2 guard is in place and works as described. The rest is minor.

## Checked and found sound

- `template/src/pdca_harness/integrate.py:516-544` — `pre` is read just before the wave's first merge. `accepted` is in wave order, and `_fold_candidates` keeps that order (`integrate.py:430-433`), so every earlier-wave bundle (including new fast-forward commits on a carried branch) is already in `pre`. `kept` gets only wave bundles that actually merged (or were already on the line), so a held bundle is never used to judge a later one. Case (4) depends on this, and the test covers it.
- `template/src/pdca_harness/integrate.py:900-906` — `_held_by` returns None, so the fold stops as before, when `head` conflicts with `pre` itself (earlier-wave work), and also when `head` merges cleanly onto `pre` plus `kept` (the conflict comes from something else the line took in, such as `_take_in_base` for a gone branch). That is the round-2 fix. Both paths have a test (`test_a_conflict_with_earlier_wave_work_still_stops_the_run`, `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`).
- `template/src/pdca_harness/integrate.py:628` — `_Conflict` is raised only by `_merge_published`'s conflicting-path branch. The no-path git failure (`:632`) and `_take_in_base`'s base-merge conflict (`:716-725`) stay plain `IntegrationError`, so the hold can never swallow them.
- `template/src/pdca_harness/integrate.py:911-941` — `_trial` works on a detached HEAD. `_merge` resets a failed merge (`:880`), and the `finally` puts the tree back on `branch` at its old tip, clean, or raises `_LineBroken`. The integration tree stays as `fold` expects, and `test_a_hold_leaves_the_integration_tree_clean_on_the_line` checks this.
- `template/src/pdca_harness/flow.py:2446-2462` — `held_conflict` is filled in place by the fold. The new holds (`had` diff) are announced on both the success path and the stop path, before the next wave's `_runnable`. Held bundles are left out of every later fold (`:2448-2449`), and dry-run passes `held_out=None`.
- `template/src/pdca_harness/flow.py:740-742`, `:2304-2311` — `Conflicts with` partners of a conflict-held bundle are now held, with their own wording. That was the round-1 fix, covered by `test_a_conflicts_with_partner_of_a_held_bundle_is_held_too`.

## Minor notes (no action needed)

- `template/src/pdca_harness/integrate.py:531-532` — `head is not None` and `pre is not None` are always true here. A `None` head goes to `_gone_branch`, which never raises `_Conflict`, and `pre` was already checked at `:524-526`. They help the type checker only. Harmless.
- `template/src/pdca_harness/integrate.py:937-941` — if a trial raises inside the `try` and the checkout back to `branch` then fails too, the `_LineBroken` from `finally` replaces the first error. Python keeps the first error as `__context__`, and both mean "stop, check the checkout", so no information that matters is lost.
- `template/src/pdca_harness/integrate.py:900-907` — efficiency: each held bundle costs `2 + len(kept)` trial merges, and each one checks out the whole tree. This runs only when a merge has already failed, so it is fine for real wave sizes. `git merge-tree --write-tree` (a git command that tests a merge without touching the worktree) would avoid the checkouts, but it needs git 2.38+. The harness states no minimum git version, so keeping plain merges is the right call.
- `template/src/pdca_harness/flow.py:740-742` — a bundle that both `Depends on` and `Conflicts with` a conflict-held bundle prints two hold lines: the generic prerequisite skip and the new partner line. The #629 `partners` path already does the same, so this is consistent and not worth changing.
- Re-issued runs, outside this diff's code: a conflict-held bundle is COMPLETE, so a re-issued run sends it through `_carry_finished` (`flow.py:1025-1034`). There it is skipped with the fold's old "undeclared cross-wave overlap" text, and `held_finished` holds only its plain `Depends on` dependents, not its `Conflicts with` partners. The docs the patch adds (`docs/07-crosscutting.md:705-706`) tell the user to re-run a held partner only after the rebuilt bundle's PR merges, which matches #646's existing contract. Noted for awareness, not as a defect of this diff.

No NEEDS-HUMAN findings.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the prior-art disposition for affected paths — the brief records merged-history and closed/unmerged-PR checks for flow/integrate, but this one-commit snapshot has no remote or PR records to independently exclude superseding or rejected work; `brief.md:29`, `target/template/src/pdca_harness/integrate.py:884`.
- [x] Validation — fitness-to-purpose — Accept the run-local hold and proposed manual rebuild workflow as sufficient for #674 — automated tests demonstrate continued unrelated work and truthful conflict reports, but operational adequacy remains a maintainer decision; `target/docs/07-crosscutting.md:696`, `target/template/src/pdca_harness/flow.py:1092`.
- [x] `template/src/pdca_harness/integrate.py:541-544` (a gone branch, `head is None`, is never added to `kept`) together with the `kept` guard at `:531-532`: a real same-wave textual conflict still stops the run when the earlier bundle of the pair had its PR merged and its branch deleted between publish and fold. Concrete case (I ran it): wave 1 is `20` and `22`, which both change line 2 of `shared.txt`, plus `23`, with `30` depending on `23`. Right after the wave publishes, 20's PR merges and `fix/20` is deleted. The fold takes main in for 20, `kept` is empty, and 22 raises: "wave 1 did not integrate (issue_22's branch … — an undeclared cross-wave overlap) … STOPPING", and `30` is never built. The brief's Invariant says a same-wave conflict costs "never the run". The patch documents this as a deliberate stop (`docs/07-crosscutting.md:706-709`), following the round-2 guidance. A possible extension: add `(name, merged_head)` to `kept` for a gone bundle of the wave, so `_held_by` can name it as the partner. It needs a human to merge a just-opened draft PR within minutes, so it is rare. Decide whether the documented exception is acceptable.
- [x] `template/src/pdca_harness/cli.py:690` together with `flow.py:2490`: a run whose only problem is a held bundle with no dependents now exits 0. Concrete case (I ran it): batch `10`, `11`, `12`, `21` (`Depends on: 12`), where 10 and 11 change the same line. Results are all COMPLETE, so `_results_rc` returns 0. The only signal is two stderr lines, while 11's open draft PR is known to conflict with 10's. Before the fix the same batch exited 1 (the fold stopped and 21 stayed PLANNED). This matches the existing #593 `held_unpushed` behaviour, so it is a policy choice, not a bug. Decide whether a conflict hold should fail the run's exit code.
- [x] **The RED test never checks that the hold lasts past one fold.** `accepted` grows over the run ("cumulative COMPLETE bundles", `flow.py:2135`), and every fold re-passes all of it, filtered only by `held_unpushed` (`flow.py:2341`). If the new hold set is not added to that filter, or is reset each wave, the *next* wave's fold tries to merge `issue_11` again and the run stops anyway. The criterion's batch has two waves. The fold runs only when `k < len(wave_list) - 1` (`flow.py:2315`), so wave 1 never folds and this regression would pass. Fix: add a third wave, e.g. `30` with `Depends on: 21`. Then require that the wave-1 fold leaves `11` out and the run reaches `30` COMPLETE.
- [x] **"Keep the first of each conflicting pair" is under-specified when three or more bundles conflict, and the invariant overclaims.** Take A–B conflicting, B–C conflicting, A–C clean. A per-pair rule holds B because of A, then holds C because of B, even though B is already out. C is held for nothing, which breaks "Bundles that merge cleanly are never held" (brief line 17). Pairwise merges from a shared base also miss the case where each pair merges cleanly but merging them one after another onto the line conflicts. The fold would then still stop, which breaks "never the run". Fix: test each bundle against the bundles already *kept* (greedy, in fold order), not against every pair. Or narrow the invariant to what pairwise detection can actually guarantee. Add a 3-bundle chain case to the criterion either way.
- [x] **The brief does not mention that `integrate.fold` already has a per-bundle skip-on-conflict mode.** That mode is the `skipped=` parameter added in #646 (`integrate.py:351-360`, `465-474`; `_fold_lines` passes it through, `flow.py:795`/`811`). It undoes a failed merge and goes on to the next bundle. It is the sequential, line-based check, so it covers the multi-bundle cases above. The brief's own prior-art section cites #646 but not this mechanism, so Do may build a second conflict-detection path next to it. The planner should say whether Do reuses it (for example, the pre-fold check names the partner, and `skipped` is the backstop that keeps the run going). If not, say why not. One reason could be that `skipped` would also swallow conflicts with earlier-wave work on the line, which the Scope explicitly keeps as a stop.
- [x] **The tie-break rule differs from the issue's.** The thread says "Keep the **lower-id** bundle in the fold". The brief keeps "the first … in the fold's merge order", and that order is a name sort (`flow.py:2269`, `integrate.py:295-296`). Names sort as strings, so `issue_100` comes before `issue_99`, and the brief would keep the higher id. The test's `10`/`11` cannot tell the two rules apart. Pick one rule in the brief and, if it is merge order, say that this departs from the issue.
- [x] **The `Conflicts with: 651` declaration cannot be checked from here.** There is no `dependency-state.json` in the bundle, so whether bundle 651 exists, and what state it is in, cannot be confirmed. The cited comment at `flow.py:2141-2144` does exist and is next to `held_unpushed` (`flow.py:2134`), so the stated reason is plausible. The human should confirm 651 is in this batch. If it is not, the declaration has no effect on wave ordering.
- [x] **The skip message for `20` will not explain why.** `_runnable` reports a held in-batch prerequisite with the generic line "skipped — prerequisite(s) not ready (11)" (`flow.py:762-764`). But `11` is COMPLETE, so "not ready" is misleading. The brief relies on this path ("through `_runnable`") but criterion (2) only asks for the pair/file lines. Either accept this wording on purpose, or say whether the dependent's line should point to the conflict.
- [x] T5 Judgment — Confirm the recorded file-scoped merged-history and closed/unmerged-PR conclusions — the supplied single-commit, remote-free snapshot cannot independently establish whether prior rejected work changes this decision; `brief.md:29`, `review-inspection.log:2`.
- [x] `template/src/pdca_harness/cli.py:690` (`_results_rc`) with `flow.py:2441`: when the held bundle has no in-batch dependents, the run now exits 0. I ran `10`/`11` (conflicting on `shared.txt`), `12`, and `22` (`Depends on: 12`). Every result is COMPLETE and `_results_rc` returns 0. Before the fix the same batch stopped and exited 1. Now the only signal that 11's work is on no line, and that its draft PR conflicts with 10's, is two stderr lines. This matches the #593 `held_unpushed` precedent (also COMPLETE, so also rc 0), and the brief does not ask for a non-zero exit. So this is a fitness-to-purpose question, not a defect: should a run that held a bundle for a conflict the human must resolve exit non-zero (or mark the bundle) so that a script or CI caller notices?
- [x] `template/src/pdca_harness/flow.py:2289-2295`: a bundle in `held_conflict` holds its `Depends on` dependents (via `held=`), but not its `Conflicts with` partners. Only `held_unpushed` goes to `unpushed=`, and `conflicts=` is only computed when `held_unpushed` is non-empty. #629's reasoning applies here too: a later-wave bundle that declares `Conflicts with: 11` was scheduled after 11 so it would build on 11's work, but 11 is now on no line of this run. That partner is still built, on a base without 11. The brief only asks for dependents to be held, and #629 (in flight) owns this code, so whether to extend the hold to `Conflicts with` partners now or leave it to #629 is a scope call.
- [x] T5 Judgment — Confirm that the affected-path merged-history and closed/rejected-work checks cover the current proposal — brief.md:29 records those searches, but this isolated target has only one synthetic commit and no remote, so their conclusions cannot be independently settled here; review-grounding.log:1.
- [x] `template/src/pdca_harness/flow.py:1092-1101`: the end-of-run step "rebuild issue_11 on a base that holds issue_10" names no command, and 11 is COMPLETE, which `docs/00-introduction.md:162` draws as a terminal state. The natural next move, re-issuing the batch (`docs/07-crosscutting.md:704`), reaches the existing carry. I ran it: the carry prints "issue_11 … is not carried … an undeclared cross-wave overlap … get issue_11's PR open with its branch on origin (re-open it, `pdca publish 11`, or re-drive issue_11), then re-issue" (`flow.py:1050`, hint text at `flow.py:913`). For a #674 hold that advice is wrong: 11's PR is already open, and re-publishing changes nothing. This diff doesn't touch that code, and the brief fixed the end-of-run wording on purpose. A human should decide whether the two messages need to agree, here or in a follow-up issue.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- issue_674 follow-up: a run whose only problem is a conflict-held bundle with no dependents exits 0 (`cli.py:690` `_results_rc`); consider a non-zero exit or marker so scripts/CI notice (same question for #593 `held_unpushed`).
- issue_674 follow-up: re-issuing a batch after a #674 hold hits the #646 carry message (`flow.py:913`, `integrate.py:630`), which calls the clash "cross-wave" and says to get the already-open PR open; align it with the #674 end-of-run advice.
