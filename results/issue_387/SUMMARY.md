# Result — issue 387 / single-source-the-brief-base-for-gate-scripts

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: the harness defines a base-resolution precedence ladder for bundle-scoped verify
  gates whose **last rung it never supplies**. `template/engine/scripts/run-verify.sh:25-27`
  tells every instance to "Resolve as: `$PDCA_BASE` > `$PDCA_VERIFY_BASE` > your own override >
  the brief's `Repo + branch target` > origin/<default>", but the driver exports only the first
  two (`template/src/pdca_harness/gates.py:468-476`) and ships no accessor a shell gate can
  call for the fourth. So every instance that fills in the C4 skeleton must re-implement
  `publish._clean_ref` **in bash**, from a comment that states the ladder but not the parsing
  rule. That parse has already been got wrong twice in Python and fixed twice — #235 (closed
  2026-07-04) and #262 (closed 2026-07-09) — and `publish._clean_ref`
  (`template/src/pdca_harness/publish.py:531-545`) now honours a backtick span **only** when it
  starts the field. The bash re-derivations carry the pre-#235 unanchored rule, so the two
  implementations of one parse disagree: for
  `- **Repo + branch target:** getwyrd/wyrd @ main (feature branch \`feat/x-slice\`)` Python
  resolves `main` while the shell resolves `feat/x-slice`. Publish then opens the PR against one
  base and C4-verify validates against another — for a bundle whose real base is not `main`
  (a stacked slice, a dependency-wave bundle, a standalone `pdca gates <id>`) the verifier
  either false-fails "patch does not apply — the bundle is stale" or proves red→green against a
  tree that lacks the prereq. One bug, two languages, is exactly what produced #235 → #262 →
  this. **Where the two halves live (verified, and it decides Scope):** the buggy `_brief_base()`
  named in the report is *not* in this repo — `template/engine/scripts/run-verify.sh` is a
  53-line skeleton that says "SKELETON. Fill this in for your project", `template/engine/`
  contains only that file plus `README.md.jinja` (no `engine/tests/` at all), and
  `git -C ../pdca-harness log --all -S "_brief_base"` finds nothing. It lives in the reporting
  instance, getwyrd/wyrd-pdca, as instance-authored code (`engine/scripts/run-verify.sh:166-178`
  and its parity test `engine/tests/test_run_verify.sh:140-145`). This bundle fixes **the
  harness's half**: the missing rung that forces the re-implementation.
- Success criterion: a bundle-scoped gate command can obtain the brief's own base
  **without reading `brief.md`**, and the three-rung ladder stays mutually exclusive:
  (a) for every bundle-scoped gate invocation, **exactly one** base variable is exported —
  `PDCA_BASE` when the brief names an `Onto branch`; else `PDCA_VERIFY_BASE` when a wave
  stack-base marker is present; else `PDCA_BRIEF_BASE` carrying the brief's own base;
  (b) `PDCA_BRIEF_BASE` is a remote-tracking ref of the same shape as the other two
  (`<remote>/<branch>`), so a gate script can use whichever is set interchangeably and can never
  produce the doubled `origin/origin/main` the report describes;
  (c) its value comes from the **same anchored parser publish uses** — not a copy — so
  `… @ main (feature branch \`feat/x-slice\`)` yields `origin/main`, `… @ \`feat/x\`` yields
  `origin/feat/x`, and a brief with no `Repo + branch target` field yields the default branch;
  (d) `publish`'s own resolved behaviour is unchanged (#235/#262 stay fixed, their tests stay
  green);
  (e) `template/engine/scripts/run-verify.sh:25-27` names the export as the last rung instead of
  instructing instances to parse the brief, so no future instance re-derives the parse.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: supply the ladder's missing last rung from the harness's single existing parse, so
  no gate script has to parse `brief.md` — the anchored parse becomes reachable as one accessor,
  the driver resolves the brief's base with it, the bundle-scoped base export is extended to
  cover that rung while staying mutually exclusive, and the C4 skeleton's guidance cites the
  export. / out of scope, explicitly: **getwyrd/wyrd-pdca's `engine/scripts/run-verify.sh` and
  `engine/tests/test_run_verify.sh`** — instance-owned files in a different repository; the
  report's fix items 1 and 2 are downstream work, filed as getwyrd/wyrd-pdca#204, and landing
  this change reduces that fix to deleting `_brief_base` and reading the exported ref. Also out
  of scope: changing `publish`'s resolved behaviour or `_clean_ref`'s rule (already correct);
  the mutual-exclusion contract between `PDCA_BASE` and `PDCA_VERIFY_BASE`; the fact that
  `gates.py:476` composes `origin/` inline rather than from `cfg.base_remote` (match the shape
  the existing exports use — do not go fix that inconsistency here); generating a shell case
  table from the Python tests; and filling in the C4 skeleton itself.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — <reason>` and exit 77\n# (-> SUMMARY §6 NEEDS-HUMAN, non-gating) instead of a red->green the bundle is guaranteed\n# to 
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp9n1xzuc2/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue 387: expose the brief's resolved base to bundle-scoped gate scripts as a single-source `PDCA_BRIEF_BASE` instead of forcing shell parsers to re-read `brief.md`.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The owed behavior is explicit: exactly one bundle base export, with `PDCA_BRIEF_BASE` using the publish parser and remote-tracking shape, so gate and publish bases cannot diverge (`brief.md:32`). |
| C2 Reproduction (red pre-fix) | PASS | With production hunks reverse-applied and the new tests retained, `PYTHONPATH=src python3 -m unittest tests.test_verify_base` failed 11 cases on `PDCA_BRIEF_BASE=UNSET`, grounding the missing-rung symptom exercised by `template/tests/test_verify_base.py:176`. |
| C3 Change | PASS | The patch puts the parser in the shared brief accessor and feeds the existing mutually-exclusive export chain, so the human decision is whether this is the intended harness-owned surface rather than instance shell code (`template/src/pdca_harness/brief.py:324`, `template/src/pdca_harness/gates.py:484`). |
| C4 Verification (red→green) | PASS | Focused red->green was reproduced independently: pre-fix production failed as above, and patched `PYTHONPATH=src python3 -m unittest tests.test_verify_base` ran 19 tests OK; full `PYTHONPATH=src python3 -m unittest discover -s tests` also exited 0 (`template/tests/test_verify_base.py:253`). |
| C5 Causal adequacy | PASS | The fix removes the duplicated-parser cause by moving the anchored parse into `brief` and making `publish` and `gates` share it; no capability-probe or runtime guard smell appears in `patch.diff` (`template/src/pdca_harness/publish.py:541`, `template/src/pdca_harness/gates.py:494`). |
| T1 Structure | PASS | The change stays inside the expected composition points: brief field accessors, gate export wiring, publish callsite, skeleton guidance, and the targeted unit module (`template/src/pdca_harness/gates.py:355`, `template/src/pdca_harness/publish.py:840`). |
| T2 Shape | NEEDS-HUMAN | The recorded docs/link gate claims green, but `./engine/scripts/run-docs-check.sh` is absent from the readable target checkout, so the human must decide whether the recorded external gate result is acceptable evidence (`check-gates.json:60`). |
| T3 Runtime | NEEDS-HUMAN | The exact recorded runtime gate cannot be reproduced here because `./engine/scripts/run-suite.sh` is absent, while the available full unittest suite passed; the human must clear whether the recorded `split-proposal.md` failure remains material (`check-gates.json:69`). |
| T4 Contribution | NEEDS-HUMAN | The recorded contribution gate is green, but no contribution artifacts or runnable `pdca-pdca contribcheck` context were provided, so the human must decide whether to trust that recorded PR-body/tracker evidence (`check-gates.json:78`). |
| T5 Judgment | PASS | Prior-art checks by affected path found no `_brief_base` history and no open PRs; GitHub issue search returned #262, #336, and this #387, so no duplicate or in-flight fix was mechanically found. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether this harness-side export is sufficient for the downstream instance workflow, because the real getwyrd shell change is explicitly out of scope and not exercised here (`brief.md:78`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The recorded docs/link gate claims green, but `./engine/scripts/run-docs-check.sh` is absent from the readable target checkout, so the human must decide whether the recorded external gate result is acceptable evidence (`check-gates.json:60`).
- [x] T3 Runtime — The exact recorded runtime gate cannot be reproduced here because `./engine/scripts/run-suite.sh` is absent, while the available full unittest suite passed; the human must clear whether the recorded `split-proposal.md` failure remains material (`check-gates.json:69`).
- [x] T4 Contribution — The recorded contribution gate is green, but no contribution artifacts or runnable `pdca-pdca contribcheck` context were provided, so the human must decide whether to trust that recorded PR-body/tracker evidence (`check-gates.json:78`).
- [x] Validation — fitness-to-purpose — Human sign-off must decide whether this harness-side export is sufficient for the downstream instance workflow, because the real getwyrd shell change is explicitly out of scope and not exercised here (`brief.md:78`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — <reason>` and exit 77\n# (-> SUMMARY §6 NEEDS-HUMAN, non-gating) instead of a red->green the bundle is guaranteed\n# to 

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
- By / date: Eduard Ralph / 2026-08-02

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Gate verdict: a `PDCA-UNVERIFIABLE:` substring in captured test output flips an exit-0 gate to unverifiable (this bundle's C4); #329 closed the non-zero-exit case only.
