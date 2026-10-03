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

Review issue #597: prevent `pdca flow` from driving briefless bundles, repairing recoverable legacy split parents after claim acquisition and safely skipping the rest.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Recovery, refusal, ownership, terminal preservation, and control-parent equivalence have observable acceptance criteria; the regression exercises the public CLI boundary (`brief.md:19`; `target/template/tests/test_flow_briefless_split_parent.py:179`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes reproduced the missing-brief `FileNotFoundError`, with 11 errors among 14 tests; imports and fixture construction succeeded (`review-red.log:1`; `target/template/tests/test_flow_briefless_split_parent.py:181`). |
| C3 Change | PASS | Named, swept, and adopted bundles satisfy the Plan-artifact admission rule after ownership is acquired; skipped claims are released and terminal bundles bypass repair (`target/template/src/pdca_harness/flow.py:1053`, `:1395`, `:2022`, `:2193`; `target/template/src/pdca_harness/cli.py:602`). |
| C4 Verification (red→green) | PASS | Restoring the production stash made all 14 tests pass; repaired and control parents independently reached COMPLETE with exit 0 and the expected brief bytes (`review-green.log:1`; `review-extra.log:1`; `target/template/tests/test_flow_briefless_split_parent.py:182`). |
| C5 Causal adequacy | PASS | The defect is admission of legacy state lacking a required artifact; repair restores that artifact through the same producer as split acceptance, while unrecoverable state never reaches downstream readers. This transforms the invalid input, without an optional-capability or load-time workaround (`target/template/src/pdca_harness/flow.py:1014`, `:1027`; `target/template/src/pdca_harness/split.py:937`). |
| T1 Structure | PASS | One shared admission rule serves all three intake paths, preserves state classification, and reuses the canonical archive reader and brief renderer (`target/template/src/pdca_harness/flow.py:1047`, `:1397`, `:2030`, `:2193`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, production-import scanner, and diff whitespace check passed; frozen docs and host-parity logs agree (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`; `gate-logs/C5-prod-path.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 2,229 tests with two skips; frozen evidence shows all 24 root render/update tests passing. Local root rerun exited 77 because Copier is not importable, so that portion is log-supported rather than independently reproduced (`review-suite.log:1767`; `review-root-suite.log:6`; `gate-logs/T3-suite.log:38`, `:54`). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the deferred gate explicitly owes its substantive PR-description/commit-message audit to publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the recorded path-based merged and closed/rejected prior-art conclusions still establish that this recovery is needed upstream — the brief records that investigation, but the supplied target has only a synthetic base commit and no remote or PR evidence to independently settle it (`brief.md:119`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether automatic recovery from the latest authored archive and recorded child order, with explicit skips when recovery is impossible, is the desired operator policy for existing legacy instances — offline CLI behavior and control equivalence are demonstrated, but fitness for the reported deployment remains a sign-off judgment (`brief.md:19`; `target/template/src/pdca_harness/flow.py:1014`; `review-extra.log:1`). |

Source citations beginning `target/` were checked against the supplied `$PDCA_TARGET`; other citations identify supplied evidence or independent rerun logs in this review directory. The target was readable and supported the red→green experiment; no stale-target caveat was needed. The production stash was restored, and no source or test changes were made by this review.

Independent regression command, run once with the production change stashed and again after restoring it: from `target/template`, `TMPDIR=/tmp/pdca-review-o_gmubu2/review-tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_flow_briefless_split_parent`. Full driver verification used the same environment with `python3 -m unittest discover -s tests`. Outputs are preserved in `review-red.log`, `review-green.log`, and `review-suite.log`.

Additional production-path exercises confirmed invalid-UTF-8 archives and lineage records are skipped without aborting the batch, an adoption child held by another claim receives no brief, and a terminal briefless descendant remains untouched. Both repaired and post-#481 control parents reached COMPLETE with exit 0 (`review-extra.log:1`). The stub leaves do not hide the forbidden failure: the same fixture reproduced it on the pre-fix source.

The instance-scoped gate wrappers are not part of this target. Their frozen logs were inspected, and available underlying checks were rerun directly. The local Copier import failure is a reviewer-host limitation, not a patch defect or an undischarged dependency of this fix: the frozen root log explicitly records successful render and update cases (`gate-logs/T3-suite.log:38`). The brief declares no external dependencies (`brief.md:104`). The only supplied INTEGRATION document is the unrendered template; its human-only-items entry is TODO, with no additional concrete obligations enumerated (`target/template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation in this sandbox: `git log --oneline --all -- template/src/pdca_harness/flow.py template/src/pdca_harness/split.py` returned only `1d6edcd pre-fix base 24c7f83cca82764c279e75d0103f51ca33b97b18`; `git remote -v` returned no entries. The brief names affected-path merged history and closed-unmerged PRs #598–600, but no independently inspectable history or PR records accompany that assertion. This is the T5 decision above, not a verification failure.

No patch defect was found. These verdicts are advisory; human validation and prior-art judgment remain owed.

### Advisory — code-review

# Advisory code review — issue 597 (flow-never-drives-a-briefless-bundle)

Lens: bugs the patch introduces, plus reuse/simplification. I found no correctness bug. The
three intake paths call one shared helper (`_admit` → `_has_plan_artifact`), each one only
after the claim is taken. The helper reuses `split._parent_plan`, `split._split_parent_brief`,
`split.read_lineage` and `flow._lineage_children` rather than copying them, writes the brief
atomically (temp file + `replace`), and releases the claim on every skip. I checked that the
rebuilt parent stays BUILT, the same as the post-#481 control (brief + close marker, no
`check-gates.json` → `state.py:367-368`), so sending it into the drive set matches what the
control does. C4 log: 11 of 14 tests error with the reported `FileNotFoundError` before the
fix. The 3 that pass are the "nothing changes" / held-claim invariance tests, which is
expected. The points below are minor.

- NEEDS-HUMAN [impl] — template/src/pdca_harness/flow.py:1020 — `plan is None` can never be
  true here. `split._parent_plan` returns `None` only when `brief.md` exists
  (`split.py:805-806`), and `_has_plan_artifact` already returned `True` for that case at the
  top of the function. The dead condition shares a branch whose message blames the lineage
  record, so if it ever did fire, it would point the operator at the wrong file. Drop the
  `plan is None or` part.
- NEEDS-HUMAN [impl] — template/src/pdca_harness/flow.py:1017 — the skip message pastes the
  `SplitError` text in as-is. That text says "— refusing to split" and ends "…then re-run: a
  parent with its own brief.md keeps it as it is" (`split.py:807-814`, `:828-833`). In a
  `pdca flow` run nothing is being split, and the line then adds a second remedy (". Then
  `pdca flow N`"). The remedy is correct, but the message is confusing. Consider a short
  flow-side lead-in, or accept it as is.
- NEEDS-HUMAN [impl] — template/tests/test_flow_briefless_split_parent.py:266 —
  `test_the_sweep_repairs_then_drives` checks only `assertIsInstance(rc, int)` for the exit
  code, which every outcome passes. The named-id test compares against a control. The sweep
  test checks the brief bytes and that 654 left BUILT, which covers the fix, but the
  `rc` assertion adds nothing. Remove it or compare it against a control.
- NEEDS-HUMAN [impl] — template/tests/test_flow_briefless_split_parent.py:237 — claim release
  on a skipped bundle is tested only through `flow_ids`. The sweep (`flow.py:2030`) and
  adoption (`flow.py:1397`) paths rely on the same `_admit` release, but no test checks that
  another run can take the bundle after either path skips it. This is a small coverage gap
  against brief (ii)/(iii), not a defect: the code path is shared.
- template/tests/test_flow_briefless_split_parent.py:105 — `flow._drive_wave` is saved and
  restored but never replaced. It is only read through `self._orig[2]`. This is harmless, but
  the restore suggests a patch that does not exist. Cosmetic, no action needed.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the recorded path-based merged and closed/rejected prior-art conclusions still establish that this recovery is needed upstream — the brief records that investigation, but the supplied target has only a synthetic base commit and no remote or PR evidence to independently settle it (`brief.md:119`).
- [ ] Validation — fitness-to-purpose — Decide whether automatic recovery from the latest authored archive and recorded child order, with explicit skips when recovery is impossible, is the desired operator policy for existing legacy instances — offline CLI behavior and control equivalence are demonstrated, but fitness for the reported deployment remains a sign-off judgment (`brief.md:19`; `target/template/src/pdca_harness/flow.py:1014`; `review-extra.log:1`).
- [ ] template/src/pdca_harness/flow.py:1020 — `plan is None` can never be true here. `split._parent_plan` returns `None` only when `brief.md` exists (`split.py:805-806`), and `_has_plan_artifact` already returned `True` for that case at the top of the function. The dead condition shares a branch whose message blames the lineage record, so if it ever did fire, it would point the operator at the wrong file. Drop the `plan is None or` part.
- [ ] template/src/pdca_harness/flow.py:1017 — the skip message pastes the `SplitError` text in as-is. That text says "— refusing to split" and ends "…then re-run: a parent with its own brief.md keeps it as it is" (`split.py:807-814`, `:828-833`). In a `pdca flow` run nothing is being split, and the line then adds a second remedy (". Then `pdca flow N`"). The remedy is correct, but the message is confusing. Consider a short flow-side lead-in, or accept it as is.
- [ ] template/tests/test_flow_briefless_split_parent.py:266 — `test_the_sweep_repairs_then_drives` checks only `assertIsInstance(rc, int)` for the exit code, which every outcome passes. The named-id test compares against a control. The sweep test checks the brief bytes and that 654 left BUILT, which covers the fix, but the `rc` assertion adds nothing. Remove it or compare it against a control.
- [ ] template/tests/test_flow_briefless_split_parent.py:237 — claim release on a skipped bundle is tested only through `flow_ids`. The sweep (`flow.py:2030`) and adoption (`flow.py:1397`) paths rely on the same `_admit` release, but no test checks that another run can take the bundle after either path skips it. This is a small coverage gap against brief (ii)/(iii), not a defect: the code path is shared.
- [ ] **Writing the brief before the bundle is claimed breaks the #565 claim rule on two of the three intake paths.** The brief says the repair happens "Before the bundle enters the run" but never says it must come after the bundle is claimed.
- [ ] **The child list as written cannot produce a byte-identical brief.** Success criterion (i) says "the child list is the parent's lineage `children`". But `split.accept` passes bundle names: `[cfg.bundle(i).name for i in ids]` (`split.py:939`), e.g. `issue_701`. The lineage record stores bare ids: `record["children"] = list(children_ids)` (`split.py:707`), e.g. `701`, which `flow._lineage_children` (`flow.py:747-752`) returns unchanged. Read literally, the brief makes Do pass `701, 702` and miss byte-identity. Say "`cfg.bundle(c).name` for each lineage child, in record order".
- [ ] **No outcome is given when the archive is usable but the lineage is not.** (i) needs the lineage `children`. (ii) covers only "no archive, or an archive `_parent_plan` refuses". "Missing lineage" is listed as out of scope, but the brief never says what happens to a briefless split parent whose `split-lineage.json` is missing, unreadable, or has an empty or garbage `children` list (`flow.py:741-752` shows hand-edited records are an expected case). Do will have to choose between writing a brief that names no children (not what any accept wrote), skipping, or crashing. Fold this case into (ii) explicitly — skip with a message and no write — and test it.
- [ ] **(i)'s "drives that bundle as it drives a post-#481 split parent" is a comparison, not an observable result.** As written, a reviewer can only verify it by running a second, post-#481 control parent. State the end point the test asserts instead. With stub leaves and `no_publish=True`, that would be the parent's final state in the `cli._flow` results (presumably AWAITING_SIGNOFF via the close fast path) plus exit code 0 for the single-id shape (`cli.py:678-683`). Otherwise the "then driven" half of (i) cannot be checked, and only "does not raise" and the brief bytes can be.
- [ ] **(i) does not say whether terminal or signed-off split parents are rebuilt.** It covers "a split parent with `close-disposition` = `split`, no `brief.md`", with no state limit. A briefless split parent already terminal (SPLIT, signed off) is never driven: `flow_ids` hands it on as an adoption seed (`flow.py:2075-2102`) and `_adoptable` walks it (`flow.py:1109-1117`). Writing a new `brief.md` into a frozen bundle there would be a second behaviour change the thread does not ask for, since the crash is only on the drive path. Either limit the repair to non-terminal bundles (the ones that would enter the drive set, matching the stated invariant) or say explicitly that terminal ones are rebuilt too, and add (iv) coverage either way.

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
- Iteration delta (if iterating): The fix itself (intake admission after claim, rebuild via split._parent_plan / _split_parent_brief, skip-with-message otherwise) was accepted — keep it. Rebuild only to clear the four code-review points: 1. flow.py:1020 — drop the dead `plan is None or` condition (_parent_plan returns None only when brief.md exists, already handled at the top), so the lineage-blaming message can only fire for a missing/empty lineage. 2. flow.py:1017 — the skip message pastes SplitError text ("refusing to split", "then re-run: a parent with its own brief.md keeps it") into a flow run, then adds a second remedy. Give it a flow-side lead-in / one clear remedy so it reads right in `pdca flow`. 3. test_flow_briefless_split_parent.py:266 — `assertIsInstance(rc, int)` can never fail; compare the sweep's rc against a control (as the named-id test does) or remove it. 4. test_flow_briefless_split_parent.py:237 — claim release on a skipped bundle is tested only via flow_ids; add tests that another run can claim the bundle after the sweep (flow_batch, flow.py:2030) and adoption (flow.py:1397) paths skip it.
- By / date: Eduard Ralph / 2026-10-02

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
