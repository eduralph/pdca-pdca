# Result — issue 341 / do-halt-on-unmet-dependency

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a builder that honestly declares an unmet external dependency
  (`NEEDS-HUMAN external dependency:` in `build-notes.md`, per the builder contract)
  currently changes nothing: BUILT unconditionally buys the full Check beat — gates,
  cross-vendor reviewer, adversary — to adjudicate a patch already stated to be
  unverifiable (`driver.py:75-92` consults nothing the builder wrote). Give Do a halt
  seam: a *confirmed* declaration routes through the existing close fast path to
  sign-off; a *refuted* one proceeds to Check unchanged, recorded.
- Success criterion: with the feature enabled: (a) marker present + claim
  **confirmed** (the named dependency resolves to a `[[doctor.checks]]` row — registered,
  or parsed from the fenced TOML block the builder contract already requires it to
  propose — AND that row's detect `cmd` exits non-zero) ⇒ the bundle takes the close
  fast path (N/A gate matrix via `gates.run_close_gates`, no reviewer, no adversary),
  §6 carries the `_declared_external_deps` item, and the bundle halts at
  AWAITING_SIGNOFF — **not** DISCONTINUED; (b) marker present + claim **refuted** (the
  detect `cmd` exits 0, or no row and no parseable proposed row) ⇒ byte-identical to
  today's full Check, with the refutation recorded where `pdca act index` can see it;
  (c) a malformed proposed-row TOML block ⇒ unconfirmed ⇒ full Check (fail toward
  review, never toward skipping it); (d) a test asserts a builder cannot skip the
  reviewer with a claim whose detect `cmd` exits 0; (e) terminal state is never set by
  a leaf — sign-off still owns COMPLETE/DISCONTINUED; (f) the behaviour is config-gated
  opt-in for one release, `off` byte-identical to today. Demonstrable by C4-verify via
  the offline driver suite (stub builders/leaves, `true`/`false` detect cmds).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the marker-triggered routing in `driver.advance` at BUILT; deterministic
  adjudication (prefer the proposal-driven reading: parse the builder's fenced
  `[[doctor.checks]]` TOML block when no registered row matches — the builder supplies
  the detect command, the harness runs it, the exit code decides); reuse of the close
  fast path machinery (`CLOSE_MARKER` substitutes for `patch.diff` — `state.py:36`,
  `state.py:159`, `gates.run_close_gates` `gates.py:152`) or an equivalent
  blocked-marker that keeps the bundle resumable after the human installs the
  dependency; refutation recording for Act; the config gate. / out of scope: #340's
  Plan-exit probe itself (a prereq, landed in the prior wave); changes to the builder
  prompt contract (it already mandates the marker + proposed row); #250's §6 reporting
  (already landed — `assemble.py:482` — this change only makes the beat cheaper before
  it).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmp945yyzgh/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: add an opt-in Do-exit halt for builder-declared unmet external dependencies, confirmed by a doctor detect command, while preserving full Check for refuted or unconfirmed claims.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief requires confirmed declarations to skip reviewer/adversary via N/A gates and refuted or malformed claims to run full Check; those are explicit in `brief.md:8` and `brief.md:14`. |
| C2 Reproduction (red pre-fix) | PASS | In a throwaway target copy with the source changes reversed but the new test retained, `PYTHONPATH=src python3 -m unittest tests.test_builder_dependency_halt` fails before the fix because `pdca_harness.dependency_halt` is absent, exercising the pre-fix gap named by `template/tests/test_builder_dependency_halt.py:97`. |
| C3 Change | PASS | The routing decision is confined to BUILT and only calls the N/A close matrix after deterministic adjudication confirms an absent dependency, so the human decision is whether this opt-in control-flow change matches the brief's halted-but-resumable semantics at `template/src/pdca_harness/driver.py:85`. |
| C4 Verification (red→green) | PASS | Focused green rerun: `PYTHONPATH=src python3 -m unittest tests.test_builder_dependency_halt` passed 13 tests on the patched target, covering confirmed halt, refuted full Check, malformed full Check, resumability, and opt-in-off at `template/tests/test_builder_dependency_halt.py:97`. |
| C5 Causal adequacy | PASS | The patch removes the unconditional Check spend by making the dependency detect exit code load-bearing rather than adding a symptom guard around a capability that should already exist; the refuted path still runs real gates and reviewer at `template/src/pdca_harness/driver.py:103`. |
| T1 Structure | PASS | The new behavior is isolated in `dependency_halt` with shared constants in state and one driver callsite, so the structural decision is localized and archivable via `template/src/pdca_harness/state.py:70`. |
| T2 Shape | NEEDS-HUMAN | The declared docs/link audit oracle `./engine/scripts/run-docs-check.sh` is absent in this review directory, so the human must decide whether the gate-runner artifact, not my local whitespace check, is sufficient for T2. |
| T3 Runtime | NEEDS-HUMAN | The declared suite oracle `./engine/scripts/run-suite.sh` is absent here and `check-gates.json` records a non-gating T3 fail at `/tmp/tmp945yyzgh/results/issue_500/split-proposal.md`; local `make check` passed, but the recorded T3 failure needs human disposition. |
| T4 Contribution | NEEDS-HUMAN | The declared `pdca-pdca contribcheck` artifact inputs are not present in this review directory, so the human must decide whether the contribution wrapper evidence is acceptable despite the reviewer being unable to rerun it. |
| T5 Judgment | PASS | Affected-path prior-art check over merged history found #340 and #250 dependency work but no prior Do-exit halt implementation, so the contribution appears scoped to the new issue rather than duplicating landed work. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Always-human validation: decide whether halting honest unverifiable builder output before reviewer/adversary is the desired product workflow, especially because accepted halted bundles would require an explicit sign-off choice to provide the dependency and iterate or discontinue. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The declared docs/link audit oracle `./engine/scripts/run-docs-check.sh` is absent in this review directory, so the human must decide whether the gate-runner artifact, not my local whitespace check, is sufficient for T2.
- [x] T3 Runtime — The declared suite oracle `./engine/scripts/run-suite.sh` is absent here and `check-gates.json` records a non-gating T3 fail at `/tmp/tmp945yyzgh/results/issue_500/split-proposal.md`; local `make check` passed, but the recorded T3 failure needs human disposition.
- [x] T4 Contribution — The declared `pdca-pdca contribcheck` artifact inputs are not present in this review directory, so the human must decide whether the contribution wrapper evidence is acceptable despite the reviewer being unable to rerun it.
- [x] Validation — fitness-to-purpose — Always-human validation: decide whether halting honest unverifiable builder output before reviewer/adversary is the desired product workflow, especially because accepted halted bundles would require an explicit sign-off choice to provide the dependency and iterate or discontinue.

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
- By / date: Eduard Ralph / 2026-08-01

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- T3 suite fail at `/tmp/.../results/issue_500/split-proposal.md` is a harness bug (suite trips over the synthetic issue_500 fixture), not caused by this patch — file/fix upstream.
- T4 contribcheck runs too early at Check (vacuous default-open pass before the publish artifacts exist) — reconsider when/how T4 is reported in the Check matrix.
