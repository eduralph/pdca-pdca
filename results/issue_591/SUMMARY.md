# Result — issue 591 / stack-integration-line-per-run

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In `[driver].wave_mode = "stack"`, every run that targets the same base folds
  onto ONE shared branch: `integrate.integration_branch(cfg, base)` depends only on the base
  (`template/src/pdca_harness/integrate.py:62-68`, `"pdca-integration/" + _flatten_base(base)`).
  So two `pdca flow` runs going at once on `main` (two independent milestone tracks) share
  `pdca-integration/main`, and each run's first fold force-pushes that branch fresh from the
  base (`integrate.py:362-371`, `fresh` ⇒ `push --force`), replacing the other run's line.
  From wave 1 on, a run's Do worktree and its C4 verify base both read that shared, moving
  branch by NAME, not the commit the run pushed: the Do worktree bases off
  `origin/<stack-base>` (`template/src/pdca_harness/worktree.py:96-98`), and the C4 gate gets
  `PDCA_VERIFY_BASE=origin/<stack-base>` (`template/src/pdca_harness/gates.py:568-570`).
  So run A's wave k+1 can be built and verified on run B's line, which lacks A's waves 0..k.
  **What #593 already changed (so Do does not re-fix it):** wave PRs now target the real
  base (`publish.py:266-283`), so open PRs no longer change base under the run; publish cuts
  from the recorded tip `stack-base-tip` and refuses a tip the line no longer holds; and a
  continuing fold refuses a line another run moved (`integrate.py:351-360`, the message cites
  #591). What is left: (a) Do and C4 still read the moving branch, so the wrong-base build
  happens before anything notices; (b) the refusal only fires at the NEXT fold, and a run's
  final wave has none; (c) even when it fires, the result is that two concurrent runs on one
  base cannot both finish — one always stops. Single-wave runs are unaffected (no fold).
- Success criterion: With the patch, two runs that drive DIFFERENT batches against the
  same `(repo, base)` never share an integration branch, and a run that is re-issued with the
  same requested ids gets the same branch name back. Demonstrated in the offline driver suite
  with real git against a bare `origin` (the `StackFoldGit` fixture): run A folds wave 0
  (bundle a1); run B (a different batch) then makes its first fold on the same base (bundle
  b1); run A then makes its continuing fold (a1 + a2). All three folds succeed; A's line on
  `origin` contains a1 and a2 and not b1; B's line contains b1 and not a1 or a2; and the
  stack base the flow records for A's wave-1 bundle (`publish.read_stack_base`, which Do's
  worktree and `PDCA_VERIFY_BASE` both read) names A's line, not B's. Pre-fix the third fold
  raises `IntegrationError` ("another run on the same base has likely moved it (#591)")
  because B's fresh fold force-pushed over the shared branch. The branch name stays a valid,
  injective single ref segment under `pdca-integration/` (two different bases, or a base and a
  batch key, can never produce the same name — the existing `_flatten_base` injectivity tests
  keep passing).
  **Flow-level case (the batch identity is threaded from the request, not the drive set).** A
  second test drives `flow.flow_ids` (stubbed leaves, `integrate.fold` patched to record the
  branch name it would use, or a real fold) and asserts: `flow_ids([a1, a2])` and a re-issued
  `flow_ids([a1, a2])` in which `a1` is already COMPLETE (so skipped as terminal and absent from
  the drive set) fold onto the SAME branch name; `flow_ids([a2])` alone, or `flow_ids([a1, b1])`,
  folds onto a DIFFERENT name. Pre-fix all of them use `pdca-integration/main`, so the
  "different" assertions fail. Importing `flow` in the test file is allowed (modules only).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the integration branch belong to one batch: two different batches on the
  same base get different branches; the same requested batch (re-issued with the same ids,
  including ids the run skips as already terminal) gets the same branch, so the module's
  "a resumed run rebuilds the same branch" contract holds. Derive the batch identity from the
  ids the run was ASKED to drive — for `flow_ids`, the `pdca flow <ids>` list as given
  (normalised to bundle names, de-duplicated and sorted, so order and `500` vs `issue_500` do not
  matter), including ids skipped as terminal or briefless — not from the post-filter drive set,
  so a resumed run whose finished bundles are skipped still lands on the same name. Today only
  the post-filter set reaches `_drive_and_act` (`flow.py:1793-1801`); the requested list lives
  in `flow_ids` (`flow.py:2233-2275`) and must be passed down.
  **`flow_batch` (the CSV sweep):** it has no requested id list — it sweeps every in-flight
  bundle under `bundle_root` (`flow.py:2088-2093`). Key it on the sorted names of that sweep as
  taken at run start (before the claim / `_admit` / `partition_schedulable` trims). No resume
  stability is promised for `flow_batch` (finished bundles drop out of the sweep, so a re-run
  gets a new name); that is acceptable because it only ever means a fresh line, never a shared
  one. Do not key on the CSV path or contents. The issue's suggested shape is
  `pdca-integration/<flattened base>-r<short hash of the batch>`; `-r` cannot appear in
  `_flatten_base`'s output (every `-` it emits is `-h` or `-s`), so that keeps the name
  injective — Do may use it or an equivalent that keeps injectivity. Everything that reads the
  branch must read the run's name: the `stack-base` marker already carries the exact branch to
  Do, C4 and publish, so those need no change beyond receiving the new name.
  **Worktree and lock stay keyed on the base** (`_integ_worktree`, `integrate.py:163-168`, and
  `integ_lock`): two runs on one base keep sharing one integration worktree and one lock, held
  across fold and re-gate (`flow.py:1994-2023`). That is correct — folds are serialised, and
  each fold does `checkout -B` of its own branch in that tree — at the cost that run B waits
  out run A's re-gate. Do not re-key them; `sweep.py:90` / `doctor.py:83` therefore need no
  change. Update the docs text that
  names `pdca-integration/<base>`. Keep the existing in-run refusal of a moved line (it still
  guards the same batch run twice at once, which drive claims #565 should already refuse).
  / out of scope: re-keying the integration worktree or lock per batch; resume overwriting its
  own earlier line (#616); deleting old integration branches on `origin` (one branch per batch now
  accumulates; a sweep of branches whose PRs are all merged/closed is follow-up work, see
  #454); re-folding an earlier run's unmerged branches on resume (#616); merge mode (#531);
  changing how Do/C4 resolve the base (they keep reading the branch by name — once the name is
  per-batch that is correct).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review issue #591: isolate stack integration branches by requested batch so concurrent different batches on the same base cannot overwrite each other's build and verification line.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Different-batch isolation and same-request identity are falsifiable, including skipped terminal IDs; both acceptance cases execute against production entry points (`target/template/tests/test_integrate_stack_bases.py:865`, `target/template/tests/test_integrate_stack_bases.py:935`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the two production changes reproduced A's continuing-fold IntegrationError after B overwrote its line, plus equal branch names for different requests (`reviewer-red.log:25`, `reviewer-red.log:43`; regression at `target/template/tests/test_integrate_stack_bases.py:885`). |
| C3 Change | PASS | Request identity survives drive-set filtering and is passed to every fold; the CSV path captures its sweep before admission, preserving the brief's intended ownership boundary (`target/template/src/pdca_harness/flow.py:2363`, `target/template/src/pdca_harness/flow.py:2169`, `target/template/src/pdca_harness/flow.py:2070`). |
| C4 Verification (red→green) | PASS | After stash restoration, all 169 affected tests passed, including real-git isolation and terminal-ID stability; the red was the reported failure, not an unavailable API (`reviewer-green.log:495`, `reviewer-red.log:40`; `target/template/tests/test_integrate_stack_bases.py:893`). |
| C5 Causal adequacy | PASS | Giving different requests different refs removes the shared-write cause; real git demonstrates the forbidden overwrite before the fix and independent ancestry afterward, with no production capability probe or symptom guard added (`target/template/src/pdca_harness/integrate.py:83`, `target/template/tests/test_integrate_stack_bases.py:895`). |
| T1 Structure | PASS | One batch identity reaches the existing fold call while base-scoped locking still covers fold and re-gate; existing stack-base readers consume the resulting exact ref (`target/template/src/pdca_harness/flow.py:2065`, `target/template/src/pdca_harness/worktree.py:96`, `target/template/src/pdca_harness/gates.py:568`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page site render/internal-link audit, and diff whitespace checks passed; frozen host-CI evidence agrees (`target/.github/workflows/docs-check.yml:34`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite: 2,325 tests, two skips, no failures; frozen root evidence shows all 24 render/update tests passing, while this interpreter's root rerun could not import Copier (`reviewer-suite.log:1798`, `gate-logs/T3-suite.log:36`, `gate-logs/T3-suite.log:54`, `reviewer-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the frozen gate explicitly defers their substantive audit to publish, where it must rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged-history and closed/rejected-work search remains adequate — the brief records it, but this isolated target has only a synthetic base commit and no remotes, so independent upstream equivalence cannot be settled here (`brief.md:149`; affected code `target/template/src/pdca_harness/integrate.py:67`, `target/template/src/pdca_harness/flow.py:2070`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether different-batch isolation is sufficient to ship with same-batch resume replacement (#616) and branch accumulation explicitly deferred — those operational limits remain despite the reproduced isolation success (`brief.md:60`, `brief.md:121`; `target/template/src/pdca_harness/integrate.py:390`). |

Independent evidence: production-only `git stash push` retained the regression tests for the red leg; `git stash pop` restored the fix before the green leg. The resulting target diff matches `patch.diff` byte-for-byte. No judged source was edited. Test temporary files stayed under this review sandbox via `TMPDIR`.

The green command was `cd target/template && PYTHONPATH=src python3 -m unittest tests.test_integrate_stack_bases tests.test_integrate tests.test_flow_slice`; the full driver command was `PYTHONPATH=src python3 -m unittest discover -s tests`. Captured results are in `reviewer-red.log`, `reviewer-green.log`, and `reviewer-suite.log`.

The production-path scanner was rerun. Its applicability is limited to newly added test files; this patch modifies existing tests, so the frozen scanner's “nothing to assert” is not itself proof of causal coverage (`gate-logs/C5-prod-path.log:10`). The real-git red→green run supplies that proof. Its fixture can exhibit the forbidden failure and actually did; mocked GitHub calls do not substitute for the git operation under review.

The root rerun exited 77 because Copier is unavailable as a library to `/usr/bin/python3` (`reviewer-root.log:6`). This is a local host limitation, not a patch defect or an unexercised dependency in the frozen evidence: `gate-logs/T3-suite.log:36` explicitly records successful render and update cases. No additional human-only items are enumerated in the supplied integration template (`target/template/docs/INTEGRATION.md.jinja:80`).

### Advisory — code-review

# Advisory code review — issue 591 (stack-integration-line-per-run)

Overall: the change is small and correct for the success criterion. The name stays injective (`-r` cannot come out of `_flatten_base`), every fold in a run gets the same batch-scoped name, and the marker carries that name to Do, C4 and publish without other changes. No other production code builds `pdca-integration/<base>` by name (grep over `template/src` and `template/engine`), so nothing still points at the old shared name. Gates pass (C4 red→green, T3 suite OK). Two small points:

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:91` — `batch_key` strips one `issue_` before adding it back, so `"issue_500"` and `"500"` give the same key. The flow does not treat those as the same bundle. `pdca flow` passes ids through raw (`template/src/pdca_harness/cli.py:591` `ids = list(args.issue_ids)`; only the split `--ids` path at `cli.py:800-803` strips `issue_`), and `flow_ids` resolves each with `cfg.bundle(iid)` = `issue_<iid>` (`template/src/pdca_harness/config.py:512`). So `issue_500` drives `issue_issue_500`, a different bundle from `500`, but both get the same key. In practice the risk is low (nobody types an `issue_issue_…` bundle), but the key should match how the flow resolves names. A simpler fix that is also correct: have the callers pass bundle names (`[cfg.bundle(i).name for i in ids]` at `flow.py:2363`; `flow_batch` already passes `d.name` at `flow.py:2170`), and let `batch_key` just de-duplicate and sort. Then the `issue_` handling lives in one place (`Config.bundle`) and is not copied into `integrate.py`. The test at `template/tests/test_integrate.py` (the `"issue_500"` case in `test_integration_branch_name_is_scoped_to_the_batch`) pins the current folding together and would need to change with it.
- `template/src/pdca_harness/flow.py:1866` — `run_batch = sorted(batch)` is extra work: `batch_key` already sorts and de-duplicates, so `list(batch)` (or passing `batch` straight through) is enough. Cosmetic, no fix needed.

Checked and found fine: the flow-level test (`template/tests/test_integrate_stack_bases.py`, `_flow_fold_names`) runs the real `fold` as a dry run through the real `flow_ids`, so it really tests that the key comes from the request and not the drive set. The `inspect.signature` switch at `test_integrate_stack_bases.py:861` exists only so the red leg fails on the shared line and not with a TypeError, and it is dead once the fix lands. That is acceptable under the file's modules-only import rule. The `swept` snapshot in `flow_batch` (`flow.py:2170`) is taken before the claim / `_admit` trims, as the brief asks.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work search remains adequate — the brief records it, but this isolated target has only a synthetic base commit and no remotes, so independent upstream equivalence cannot be settled here (`brief.md:149`; affected code `target/template/src/pdca_harness/integrate.py:67`, `target/template/src/pdca_harness/flow.py:2070`).
- [x] Validation — fitness-to-purpose — Decide whether different-batch isolation is sufficient to ship with same-batch resume replacement (#616) and branch accumulation explicitly deferred — those operational limits remain despite the reproduced isolation success (`brief.md:60`, `brief.md:121`; `target/template/src/pdca_harness/integrate.py:390`).
- [x] `template/src/pdca_harness/integrate.py:91` — `batch_key` strips one `issue_` before adding it back, so `"issue_500"` and `"500"` give the same key. The flow does not treat those as the same bundle. `pdca flow` passes ids through raw (`template/src/pdca_harness/cli.py:591` `ids = list(args.issue_ids)`; only the split `--ids` path at `cli.py:800-803` strips `issue_`), and `flow_ids` resolves each with `cfg.bundle(iid)` = `issue_<iid>` (`template/src/pdca_harness/config.py:512`). So `issue_500` drives `issue_issue_500`, a different bundle from `500`, but both get the same key. In practice the risk is low (nobody types an `issue_issue_…` bundle), but the key should match how the flow resolves names. A simpler fix that is also correct: have the callers pass bundle names (`[cfg.bundle(i).name for i in ids]` at `flow.py:2363`; `flow_batch` already passes `d.name` at `flow.py:2170`), and let `batch_key` just de-duplicate and sort. Then the `issue_` handling lives in one place (`Config.bundle`) and is not copied into `integrate.py`. The test at `template/tests/test_integrate.py` (the `"issue_500"` case in `test_integration_branch_name_is_scoped_to_the_batch`) pins the current folding together and would need to change with it.
- [x] **The success criterion does not test the part most likely to go wrong: passing the batch identity in from the flow.** The scenario (brief "Success criterion", "Repro instruction") calls `integrate.fold` directly three times, and each call "carr[ies] each run's batch identity (however Do threads it)". So the test passes once `fold` accepts a key, even if `_drive_and_act` never passes one, or passes the wrong one. Today `_drive_and_act` only receives the post-filter drive set (`flow.py:1793-1801`, `named = frozenset(batch_names)`). The requested ids, including skipped-terminal ids, exist only in `flow_ids` (`flow.py:2233-2275`) and are never passed down. The brief's main rule ("derive from the ids the run was ASKED to drive … not the post-filter drive set") has no red→green test. The check "`read_stack_base` names A's line" adds nothing either: `_point_at_integration` writes whatever branch string `fold` returned (`flow.py:736-742`). Ask for a flow-level test of `flow_ids([a1, a2])` vs `flow_ids([a1-terminal, a2])` (same name), and vs a different id list (different name), with the fold patched or a dry-run. Note that `test_integrate_stack_bases.py:41` imports no `flow`; importing the module is allowed.
- [x] **"The CSV batch for `flow_batch`" is not a defined id set.** `flow_batch` does not drive the CSV's ids. It sweeps "EVERY in-flight bundle" under `bundle_root` (`flow.py:2088-2093`), then trims that set by claims (`:2099`), `_admit` (`:2107`) and `partition_schedulable` (`:2116`). `csv` is only a path handed to the Plan session (`cli.py:638-640`, `leaves.py:1550`). The obvious keys all go wrong. Hashing the swept set changes on every resume, because finished bundles drop out of the sweep. Hashing the CSV path ties the name to a filename. Hashing the CSV content changes when the export is refreshed. And two concurrent `--from-csv` runs sweep the same global pool. The brief should state the `flow_batch` key exactly, or put `flow_batch` out of scope and give it a stated fallback.
- [x] **The "same ids ⇒ same branch" rule makes a resumed run overwrite its own earlier line, and the brief does not say so.** A resumed run starts with `folded_tips = {}` (`flow.py:1813`), so its first fold is `fresh` and force-pushes (`integrate.py:314-315, :370`). `flow_ids` skips the bundles that are already COMPLETE (`flow.py:2242-2269`), so they are not in `accepted`. The resumed run therefore rebuilds the same-named line without the earlier run's waves. The earlier waves' recorded `stack-base-tip` then falls off the line, and a late publish refuses it (`test_integrate_stack_bases.py:829`). This happens today too, but the brief presents the same name as what makes "a resumed run rebuilds the same branch" hold (Scope; `integrate.py:63`). Until #616 lands, that same name is what lets the overwrite happen. Either say this explicitly in the Invariant/Scope as an accepted gap pending #616, or reconsider. Also, a resume run with a subset of ids (a common way to resume) gets a different name anyway.
- [x] **Worktree and lock keying is left as "possibly", which is an open design decision.** The brief's Difficulty line says "possibly `_integ_worktree`/`integ_lock` keying". `_integ_worktree` keys on base only (`integrate.py:163-168`), and the flow holds that lock over fold **and** re-gate (`flow.py:1994-2023`). With per-batch branches, two runs on one base keep sharing one worktree and one lock. That is correct, but run B blocks for the whole of run A's re-gate, and the next fold of each run does `checkout -B` of a different branch in the same tree. Re-keying the worktree per batch changes what `sweep.py:90` / `doctor.py:83` find, and the brief only says to keep them "working". Decide it in the brief: keep base-keyed (and say so), or re-key. Don't leave it for Do to choose with no criterion.
- [x] **The docs-update list misses two places that name the shared branch.** Scope says "Update the docs text that names `pdca-integration/<base>`", but Difficulty only lists `docs/07-crosscutting.md:660`, `pdca.toml.jinja:120-121` (actually 120-122) and the `integrate.py` docstrings. These also name it: `template/engine/scripts/run-verify.sh:25` (`origin/pdca-integration/<base>`) and `template/PCDA/quality-cycle/09-parallel-lanes.md:69`. Separately, the brief puts #531 in wave 0 with "no declared conflict" while it edits the same `[driver]` comment block (`pdca.toml.jinja:111-129`, the wave_mode stanza this fix rewrites). Adjacent hunks there are a likely textual conflict, so consider declaring `Conflicts with: 531`.

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
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
