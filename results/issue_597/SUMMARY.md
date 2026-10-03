# Result — issue 597 / flow-never-drives-a-briefless-bundle

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `pdca flow <ids>` crashes with `FileNotFoundError: …/issue_N/brief.md` when one
  of the ids is a split parent whose split was accepted **before #481**. How the disk gets
  there: an iterate-to-Plan archived the parent's brief to `iteration-vN/brief.md`; the split
  was accepted afterwards; before #481 `split --accept` wrote no replacement brief. So the
  parent has `close-disposition` = `split` and no `brief.md`. `state.state` checks the close
  marker before the brief (`template/src/pdca_harness/state.py:351`), finds no
  `check-gates.json`, and returns BUILT (`state.py:367-368`). BUILT is neither UNPLANNED nor
  terminal, so `flow.flow_ids` puts it in the drive set (`flow.py:2064-2104`); the same goes
  for the `--from-csv` sweep (`flow.py:1925-1930`) and for split adoption, which filters a
  child the same way (`flow.py:1105-1108`). The first brief read then crashes the whole run
  before any bundle is driven: `_drive_and_act` → `_point_at_integration` (`flow.py:1768`,
  `:694-706`) → `publish._resolve_target` (`publish.py:548`) → `brief.repo_target`
  (`brief.py:324`) → `brief.parse_fields` (`brief.py:23`) → `FileNotFoundError`. Found on
  getwyrd/wyrd-pdca (bundle issue_654).
- Success criterion: With the patch:
  (i) **A pre-#481 split parent is repaired at intake, then driven.** Given a split parent
  with `close-disposition` = `split`, no `brief.md`, and an authored iterate-to-Plan archive
  (`iteration-vN/brief.md`), `pdca flow <parent-id>` (through `cli._flow`) does not raise. Before
  the bundle enters the run — and only **after this run holds its claim** (see (iii)) —
  `<parent>/brief.md` is written, **byte-identical** to what
  `split --accept` writes for the same parent since #481 (`split._split_parent_brief`
  applied to `split._parent_plan`'s result, `split.py:937-939`; the child list is
  `[cfg.bundle(c).name for c in <lineage children>]` — bundle NAMES such as `issue_701`, in
  lineage record order, read with `flow._lineage_children` (`flow.py:736-752`); the lineage
  stores bare ids, `split.py:707`, so passing them unconverted breaks byte-identity), and one
  stderr line names the bundle and says its brief was rebuilt from `iteration-vN/brief.md`.
  **Observable end point:** the same test builds a control parent with the post-#481 disk
  (`split.accept`, brief left in place) and drives it the same way; the repaired parent's
  entry in the `cli._flow` results map and the call's exit code equal the control's. Do
  records the actual state reached (expected AWAITING_SIGNOFF or a terminal state with stub
  leaves and `no_publish=True`) in build-notes. Only **non-terminal** bundles (ones that
  would enter the drive set) are repaired: a briefless split parent that is already
  terminal (handed on as an adoption seed, `flow.py:2075-2102`, or walked by `_adoptable`,
  `flow.py:1109-1117`) is never written to.
  (ii) **No usable source → skipped, not crashed.** With no archive, an archive
  `_parent_plan` refuses (unfilled required field, unreadable), **or a lineage record that
  is missing, unreadable, or yields no children** (`flow._lineage_children` returns `[]`,
  `flow.py:747-752`), no `brief.md` is written, the
  bundle is NOT driven, one stderr line names it and says why and what to do (the
  `SplitError` text already carries the remedy, `split.py:806-833`), its claim is released
  (as the other intake skips do, `flow.py:2072-2073`), and every other bundle in the batch is
  still driven. Through `flow_ids` it still gets an entry in the results map (#468: every
  named id is answered for), so the run's exit code is non-zero.
  (iii) **Every intake path.** (i) and (ii) hold for a named id (`flow_ids`), for the
  `--from-csv` sweep (`flow_batch`), and for a split child reached through adoption
  (`_adoptable`). **The repair runs only after the claim succeeds** (#565): for named ids
  the claim is already taken before `flow_ids` (`cli.py:602-615`); in the sweep the repair
  must come after `_claim_swept` (`flow.py:1939-1940`), not in the state filter before it
  (`:1929-1934`); in adoption, after the adopted child is claimed. A bundle this run cannot
  claim (another live run holds it) is excluded as today and **never written to** — a test
  holds the bundle with another claim on the sweep path and asserts no `brief.md` appears. Any other bundle with no `brief.md` that is past Do (a close marker or
  `patch.diff`, but not a split parent) is skipped as in (ii) — never driven.
  (iv) **Nothing else changes.** A bundle that has its own `brief.md` is never rewritten
  (byte-identical before/after). A briefless split parent that is already terminal is not
  written to (tested). `state.state` is unchanged. The whole `template/tests`
  suite stays green.
  Shown by the named test going red on `main` (`FileNotFoundError` out of `cli._flow`) and
  green with the fix.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Close the gap at intake: a bundle with no `brief.md` never reaches the drive set;
  a split parent left briefless by a pre-#481 accept gets the brief `split --accept` would
  have written, from the same source and by the same code (reuse — do not re-implement —
  `split._parent_plan` / `split._split_parent_brief`); everything else briefless is skipped
  with a message. All three intake paths, one shared rule. / out of scope: changing
  `state.state` (it correctly reads such a bundle as past Do, #481); changing
  `split --accept` itself; making `_point_at_integration` / `publish` tolerate a missing brief
  (that would drive a briefless bundle further, not stop it); repairing other kinds of damaged
  bundles (corrupt briefs) beyond the skip in (ii); writing a brief into a terminal bundle.

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

Review issue #597: prevent `pdca flow` from driving briefless bundles, rebuilding legacy split-parent briefs after claim acquisition and skipping unrecoverable bundles without aborting the batch.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The repair/skip boundary, byte identity, claim ownership and terminal exclusions are observable and covered by the production CLI/control comparison (`target/template/tests/test_flow_briefless_split_parent.py:198`, `brief.md:19`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production change reproduces the missing-brief crash: 16 tests run, 13 errors; the production-created legacy disk reaches the original failing read (`target/template/tests/test_flow_briefless_split_parent.py:150`, `reviewer-red.log:102`). |
| C3 Change | PASS | All three admission paths enforce the Plan artifact before driving; repair follows claims and excludes terminal bundles, while failed admission releases ownership (`target/template/src/pdca_harness/flow.py:1406`, `target/template/src/pdca_harness/flow.py:2037`, `target/template/src/pdca_harness/flow.py:2203`). |
| C4 Verification (red→green) | PASS | Restoring the patch passes all 16 regression tests, including control-equivalent results and live-run claim-release probes; the independent CLI probe reaches COMPLETE for parent and children with exit 0 (`reviewer-green.log:3`, `reviewer-probes.log:1`, `target/template/tests/test_flow_briefless_split_parent.py:182`). |
| C5 Causal adequacy | PASS | Legacy invalid disk state is repaired or excluded at admission before downstream readers; the test fixture demonstrably exhibits the original crash, and no optional-capability/load-time symptom guard is added (`target/template/src/pdca_harness/flow.py:1014`, `target/template/tests/test_flow_briefless_split_parent.py:129`). |
| T1 Structure | PASS | One admission rule and the existing split renderer preserve consistent behavior across named, swept and adopted bundles; state classification and publishing semantics stay outside this change (`target/template/src/pdca_harness/flow.py:1037`, `target/template/src/pdca_harness/flow.py:1057`). |
| T2 Shape | PASS | Independent whitespace check, documentation lint and 22-page site/link audit pass; frozen logs corroborate both documentation gate rows (`gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver suite passes 2,231 tests with two skips; frozen evidence shows all 24 root render/update tests passed, although this review host cannot independently repeat copier-dependent tests (`reviewer-suite.log`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`, `reviewer-root-suite.log:7`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred gate requires its substantive PR/commit audit at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm that the affected-path merged-history and closed/rejected-work search still rules out an upstream equivalent — the brief records that search, but this snapshot contains only one synthetic base commit and no remote, so independent settlement is unavailable (`brief.md:119`, `reviewer-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether archive-derived recovery and explicit skips meet operators' needs for legacy split parents — executable evidence establishes byte-identical recovery and control-equivalent outcomes, while operational suitability remains the sign-off decision (`target/template/tests/test_flow_briefless_split_parent.py:198`, `target/template/tests/test_flow_briefless_split_parent.py:302`, `reviewer-probes.log:1`). |

No grounded patch defect found. Source citations above refer to the supplied disposable `$PDCA_TARGET` under `target/`; evidence citations refer to this review directory. The target was readable and matched the patch, with no observed target-state caveat. The production change was restored after the red leg; no implementation was edited.

Independent checks used `PYTHONDONTWRITEBYTECODE=1` and a `TMPDIR` inside this review directory. From `target/template`, the red and green command was `PYTHONPATH=src python3 -m unittest tests.test_flow_briefless_split_parent`; only the production file was stashed, preserving the added tests. The full driver command was `PYTHONPATH=src python3 -m unittest discover -s tests`. From `target`, documentation checks were `python3 docs/publishing/tools/lint_docs.py` and `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-q0s8zant/reviewer-site`; both succeeded. AST inspection confirmed production-package imports, and fixture/entry-point inspection confirmed calls to `driver._archive_iteration`, `split.accept` and `cli._flow`, consistent with `gate-logs/C5-prod-path.log:10`.

Additional executable probes supplied invalid UTF-8 separately in the archive and lineage record. Both produced a single actionable skip, wrote no replacement brief, preserved the named result and allowed the sibling to run (`reviewer-probes.log:2`, `reviewer-probes.log:3`). The fixture uses real filesystem state and real claims; stub leaves do not prevent the forbidden failure, as the independent red leg demonstrates.

The root-suite rerun exited 77 because this interpreter cannot import `copier`; 19 tests were collected with three skips. This is a reviewer-host limitation, not a patch failure or an undischarged dependency of the fix: the frozen T3 log explicitly shows the render and update cases executing successfully. The brief declares no external dependency. No rendered project-specific INTEGRATION.md was supplied; the target contains only the template's unfilled human-only-items field (`target/template/docs/INTEGRATION.md.jinja:80`).

The iteration's four concerns are addressed: lineage failure no longer includes `plan is None`; refusal messages have a flow-specific remedy; the sweep compares its result map and exit status with a control; and sweep/adoption claim-release tests probe from a second run while the first still owns driven work (`target/template/src/pdca_harness/flow.py:1019`, `target/template/tests/test_flow_briefless_split_parent.py:270`, `target/template/tests/test_flow_briefless_split_parent.py:280`, `target/template/tests/test_flow_briefless_split_parent.py:315`). The separate `plan is None` return handles a brief appearing between the two existence checks, consistent with the documented limits of claim coverage (`target/template/src/pdca_harness/flow.py:1025`, `target/template/src/pdca_harness/drive_claim.py:42`).

### Advisory — code-review

# Advisory code review — issue 597 (flow-never-drives-a-briefless-bundle)

Lens: bugs the patch introduces, plus reuse / simplification. Grounded on the patched tree at `$PDCA_TARGET`.

**Verdict: no correctness bugs found.** The four carry-forward points from iteration 1 are all cleared:

- The dead `plan is None or` check is gone. `plan is None` now only returns True (`template/src/pdca_harness/flow.py:1025-1028`), and the lineage message fires only for an empty or missing lineage (`flow.py:1029-1036`).
- The SplitError text is cut down to its reason, with one flow-side remedy (`flow.py:1019-1024`).
- The sweep test now compares rc against a control (`template/tests/test_flow_briefless_split_parent.py:302-317`).
- Claim release is now tested on all three intake paths (`test_flow_briefless_split_parent.py:258-291`).

Reuse is right. The rebuild calls `split._parent_plan`, `split._split_parent_brief` and `flow._lineage_children` and copies none of their logic. The write uses the same `write_text(..., encoding="utf-8")` as `split.py:1007`, so the bytes match (and the test checks it). Every `_admit` call runs after the claim: `flow.py:1407` comes after `_refused_child`, `flow.py:2040` comes after `_claim_swept`, and named ids are claimed in `cli._flow`. `release` is safe to call twice (`drive_claim.py:229`), so the later `dropped` and `held` releases do not conflict with it.

Minor notes (none blocks; none needs a human):

- `template/src/pdca_harness/flow.py:1019` — the trim splits on the literal `" — refusing to split"`, which ties it to the wording in `split.py:813,829,833`. If that wording changes, the full `split --accept` text and its "re-run" remedy come back into flow output. `_assert_skipped` would catch this (`assertNotIn("refusing to split")`, `test_flow_briefless_split_parent.py:177-180`), so this is a coupling note, not a bug.
- `template/src/pdca_harness/flow.py:2040-2045` — when every swept bundle is skipped as briefless, `flow_batch` returns `{}`, so `pdca flow --from-csv` exits 0 even though it named bundles it would not drive. This matches the existing "could not claim" return just above it, and the brief only asks for a non-zero exit on the named-id path (`flow_ids`, #468). It is a known gap, not a regression.
- `template/src/pdca_harness/flow.py:1407` vs `:1422` — in adoption, the brief is rebuilt before `_reschedule`. If the reschedule then fails, the child keeps a newly written brief but is not driven this run. The write is the correct brief and happens under this run's claim, so it does no harm. The next run simply takes the "has brief.md" path.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm that the affected-path merged-history and closed/rejected-work search still rules out an upstream equivalent — the brief records that search, but this snapshot contains only one synthetic base commit and no remote, so independent settlement is unavailable (`brief.md:119`, `reviewer-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether archive-derived recovery and explicit skips meet operators' needs for legacy split parents — executable evidence establishes byte-identical recovery and control-equivalent outcomes, while operational suitability remains the sign-off decision (`target/template/tests/test_flow_briefless_split_parent.py:198`, `target/template/tests/test_flow_briefless_split_parent.py:302`, `reviewer-probes.log:1`).
- [x] **Writing the brief before the bundle is claimed breaks the #565 claim rule on two of the three intake paths.** The brief says the repair happens "Before the bundle enters the run" but never says it must come after the bundle is claimed.
- [x] **The child list as written cannot produce a byte-identical brief.** Success criterion (i) says "the child list is the parent's lineage `children`". But `split.accept` passes bundle names: `[cfg.bundle(i).name for i in ids]` (`split.py:939`), e.g. `issue_701`. The lineage record stores bare ids: `record["children"] = list(children_ids)` (`split.py:707`), e.g. `701`, which `flow._lineage_children` (`flow.py:747-752`) returns unchanged. Read literally, the brief makes Do pass `701, 702` and miss byte-identity. Say "`cfg.bundle(c).name` for each lineage child, in record order".
- [x] **No outcome is given when the archive is usable but the lineage is not.** (i) needs the lineage `children`. (ii) covers only "no archive, or an archive `_parent_plan` refuses". "Missing lineage" is listed as out of scope, but the brief never says what happens to a briefless split parent whose `split-lineage.json` is missing, unreadable, or has an empty or garbage `children` list (`flow.py:741-752` shows hand-edited records are an expected case). Do will have to choose between writing a brief that names no children (not what any accept wrote), skipping, or crashing. Fold this case into (ii) explicitly — skip with a message and no write — and test it.
- [x] **(i)'s "drives that bundle as it drives a post-#481 split parent" is a comparison, not an observable result.** As written, a reviewer can only verify it by running a second, post-#481 control parent. State the end point the test asserts instead. With stub leaves and `no_publish=True`, that would be the parent's final state in the `cli._flow` results (presumably AWAITING_SIGNOFF via the close fast path) plus exit code 0 for the single-id shape (`cli.py:678-683`). Otherwise the "then driven" half of (i) cannot be checked, and only "does not raise" and the brief bytes can be.
- [x] **(i) does not say whether terminal or signed-off split parents are rebuilt.** It covers "a split parent with `close-disposition` = `split`, no `brief.md`", with no state limit. A briefless split parent already terminal (SPLIT, signed off) is never driven: `flow_ids` hands it on as an adoption seed (`flow.py:2075-2102`) and `_adoptable` walks it (`flow.py:1109-1117`). Writing a new `brief.md` into a frozen bundle there would be a second behaviour change the thread does not ask for, since the crash is only on the drive path. Either limit the repair to non-terminal bundles (the ones that would enter the drive set, matching the stated invariant) or say explicitly that terminal ones are rebuilt too, and add (iv) coverage either way.

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
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
