# Result — issue 550 / plan-revision-pass-admits-the-bundles-checkouts

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The plan-advisory revision pass spawns the planner with no workspace grant.
  `run_plan_advisory_batch` re-enters the planner at
  `template/src/pdca_harness/leaves.py:3710` —
  `_invoke(cfg.planner, cfg.root, _plan_revision_prompt(cfg, with_findings), cfg=cfg)` — with
  no `extra_argv`. Every other interactive spawn carries the #494 grant: `do_plan`
  (`leaves.py:1008-1010`, `_plan_grant`), `do_plan_batch` (`:1203-1205`, `_plan_grant`), and
  the sign-off / batch sign-off / Act / publish spawns (`:3751`, `:3803`, `:3901`, `:3971`,
  all `_bundle_grant`). So the one session whose whole job is to weigh findings written against
  the target source (`plan-advisory-*.md`, path:line citations) and re-check the brief's
  root-cause citation opens with the target checkout outside its workspace: the human gets the
  per-file approval prompts #494 removed everywhere else, and a hand-granted approval cannot
  stick (it lands in the untracked `settings.local.json`, which `--setting-sources project`
  drops). Opt-in path only: it runs when `[[leaves.plan_advisory]]` is configured, the
  reviews raised findings, and `cfg.planner.mode == "command"` (`leaves.py:3704`).
- Success criterion: With the patch, when `run_plan_advisory_batch` runs the revision pass
  on a planner leaf whose family has a grounding flag (claude → `--add-dir`), the planner spawn
  (i) admits, through that flag, exactly the deduplicated primary checkouts that the bundles
  in `with_findings` resolve to (one flag/value pair per distinct directory); (ii) admits
  **nothing** when none of those bundles' checkouts resolve on this host, even if the
  instance has other known targets (`[publisher.checkouts]` or other briefs' targets). A
  session that already has bundles never widens to the instance's other targets; that is
  the `_bundle_grant` rule at `leaves.py:830-841`. (iii) Nothing else about the spawn changes:
  cwd stays `cfg.root`, the prompt is byte-identical, a `generic`-family planner (no
  grounding flag) is spawned with no admission argv, and a revision that raises is still
  contained (the `try/except` at `:3709-3715`). Shown by the named test going red on the
  base (the spawn's `extra_argv` is `None`) and green with the fix.
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it)
- Scope (one logical fix) / out of scope: The revision-pass planner spawn in `run_plan_advisory_batch` is admitted to the
  checkouts of the bundles it revises, by the same rule as the other bundle-scoped sessions.
  Update the `test_leaf_workspace_admission.py` module docstring, which says "six" interactive
  spawns, so it names the seventh. / out of scope: the revision pass's lack of a
  `handoff.session` exit contract (a separate question); any change to `_bundle_grant`,
  `_plan_grant`, `_known_targets` or `_primary_checkout`; the plan-advisory reviewer's own
  sandbox and grounding (`_run_plan_advisory_sandboxed`); OS-level sandboxing of interactive
  leaves (#551); the revision prompt text.

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

Review issue #550: admit the plan-advisory revision planner to exactly the primary checkouts of bundles with findings, without widening its workspace.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The admission boundary is falsifiable, including an absent checkout despite other known targets; the negative fixture proves those other targets exist (`target/template/tests/test_leaf_workspace_admission.py:246`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix leaves 17 tests runnable and produces exactly the missing-admission failure (`target/template/tests/test_leaf_workspace_admission.py:241`; `review-red.log:4`). |
| C3 Change | PASS | The revision session receives only its finding bundles’ grant, preserving its cwd, prompt and exception boundary; no unrelated production behavior changes (`target/template/src/pdca_harness/leaves.py:3703`). |
| C4 Verification (red→green) | PASS | Restoring the production fix turns the same 17 tests green; 32 advisory tests and a separate mixed-bundle probe also pass, covering failure containment, deduplication and exclusion (`target/template/tests/test_plan_advisory.py:199`; `review-green.log:3`; `review-batch.log:1`). |
| C5 Causal adequacy | PASS | The missing spawn admission is directly repaired; no new capability probe or runtime guard masks a load-time cause, and the test executes the real revision path (`target/template/src/pdca_harness/leaves.py:3710`; `target/template/tests/test_leaf_workspace_admission.py:239`). |
| T1 Structure | PASS | Reusing the existing strict bundle resolver preserves one admission policy and avoids the broader pre-brief Plan fallback (`target/template/src/pdca_harness/leaves.py:923`). |
| T2 Shape | PASS | Independent whitespace, docs lint and site/link checks pass; frozen host-CI evidence corroborates the same docs commands (`review-docs-lint.log:1`; `review-docs-render.log:3`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver run passes 1,924 tests with two skips; frozen root-suite evidence shows 24 tests passing, including render/update compatibility, which local missing Copier prevents rerunning (`gate-logs/T3-suite.log:10`; `gate-logs/T3-suite.log:54`; `review-suite.log`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally undrafted at Check; the substantive audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged and closed/rejected prior-art check before contribution — the brief reports it, but this supplied repository has only one synthetic base commit and no remotes or PR-history evidence (`review-prior-art.log:1`; affected call: `target/template/src/pdca_harness/leaves.py:3710`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether demonstrated argv admission sufficiently resolves the operator’s repeated-approval problem — real vendor CLI permission behavior was not exercised; the recorder establishes only the harness boundary (`target/template/tests/test_leaf_workspace_admission.py:89`). |

Independent evidence and limits:

- The target is the supplied disposable copy of base `70ea12b`, with the patch applied. Production-only `git stash` preserved the added regression tests for the red leg; `git stash pop` restored the fix for green. The final target diff matches `patch.diff` exactly. No stale-target caveat applies.
- `review-red.log` shows one assertion failure because `extra_argv` is `None`; `review-green.log` shows all 17 passing. `review-advisory.log` shows 32 passing, including the planner-failure containment case. The extra probe used real checkout fixtures and production admission code, with a controlled no-findings result for one bundle; it observed one spawn, two distinct admitted checkouts, no duplicate and no admission for the clean bundle.
- `review-suite.log` records the successful full driver rerun. Copier is not importable locally, so root-suite adjudication rests on the frozen log’s actual 24-test successful run, not an inferred local success. All six supplied gate logs were inspected. The instance-scoped wrappers are not required to exist in this target copy.
- The C5 scanner explicitly did no substantive scan because no new test file was added (`gate-logs/C5-prod-path.log:10`). C5 above instead rests on the production call and the independently reproduced regression, not that scanner’s nominal pass.
- The declared Python/git dependencies were exercised. The fixtures can expose the forbidden missing-admission behavior, as the red leg demonstrates; they do not establish real CLI permission UX. No additional project-specific human-only items are enumerated in the supplied integration template (`target/template/docs/INTEGRATION.md.jinja:80`).
- Prior-art investigation by both affected paths returned only `bd8754f pre-fix base 70ea12b...`; `git remote -v` returned no entries (`review-prior-art.log`). The brief’s claimed #494/PR #524 precedent and absence of closed-unmerged work therefore remain unconfirmed from the supplied evidence.

No grounded patch defect found. This review is advisory; the two NEEDS-HUMAN decisions remain for sign-off.

### Advisory — code-review

# Check advisory — code review (correctness + reuse/simplification)

## Production change (leaves.py:3710-3711)

Clean. The new `extra_argv=_bundle_grant(with_findings, cfg, cfg.profile(cfg.planner))`
is a byte-for-byte mirror of every other bundle-scoped grant call site (`leaves.py:3752`
for sign-off, `:3902` for Act, `:3972` for publish) — same three-argument shape, same
`cfg.profile(<the leaf being spawned>)` pattern. No new helper, no duplicated logic: it
reuses `_bundle_grant`/`_grant_argv` exactly as the brief's composition cue specified.
The grant computation sits inside the existing `try/except` (the whole call is one
expression), so a `_bundle_grant` failure is contained the same way an `_invoke` failure
already was — no change to the exception's blast radius. No resource leak, no
off-by-one, no altered control flow. One line, correctly scoped.

## Test additions (test_leaf_workspace_admission.py)

- NEEDS-HUMAN [impl] — `test_leaf_workspace_admission.py:26-27`: bullet (i) of the module
  docstring still reads "each of the **six** admits the primary checkout...", but the
  paragraph just above it (lines 20-27) now says the revision pass is "a seventh
  interactive spawn... covered below by the bundle-scoped rule (i)" — i.e. rule (i) now
  governs seven spawns, not six. The brief's own scope line asked to "update the ...
  module docstring, which says 'six' interactive spawns, so it names the seventh" — the
  new paragraph does that, but the itemized criterion (i) a few lines down was missed and
  is now internally inconsistent with the paragraph above it. One-word fix.

Two of the three new tests are weaker than they look, though this isn't something the
patch invented — it inherits an existing test-helper convention rather than misusing it:

- `_admits_nothing` (`test_leaf_workspace_admission.py:169-175`) treats "extra_argv key
  never passed" (`None`) and "extra_argv passed but empty" (`[]`) as the same outcome —
  by design, per its own docstring ("Empty and absent are the same spawn... The contract
  is 'no grant', not a representation"). That means
  `test_plan_revision_admits_nothing_when_its_bundles_checkout_is_absent`
  (`:246-264`) and `test_plan_revision_generic_family_planner_spawns_with_no_admission`
  (`:266-273`) both pass identically whether or not the production fix at
  `leaves.py:3710-3711` is present, because pre-fix `extra_argv` is `None` (the kwarg was
  never passed) and post-fix it's `[]` (an empty grant) — both falsy. The C4 gate log
  confirms this directly: reverting the one production line fails exactly one of the
  three new tests (`test_plan_revision_admits_the_bundles_checkouts`), not three. This
  matches the pre-existing sibling test `test_a_bundle_scoped_session_never_widens_to_the_known_targets`
  (`:335-366`), which the brief explicitly asked the new negative test to mirror, and
  which has the identical property — so this is established convention in this file, not
  a defect this diff introduced. Flagging for visibility only, not as something this
  patch needs to fix: the gate's own bar ("the named test going red on the base") was met
  by the one test that actually flips, and that's consistent with how the file already
  verifies the six original spawns.

No other issues found — no leaks, no concurrency concerns, no missed edge case in the
call site itself, nothing duplicated that an existing helper doesn't already cover.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path merged and closed/rejected prior-art check before contribution — the brief reports it, but this supplied repository has only one synthetic base commit and no remotes or PR-history evidence (`review-prior-art.log:1`; affected call: `target/template/src/pdca_harness/leaves.py:3710`).
- [x] Validation — fitness-to-purpose — Decide whether demonstrated argv admission sufficiently resolves the operator’s repeated-approval problem — real vendor CLI permission behavior was not exercised; the recorder establishes only the harness boundary (`target/template/tests/test_leaf_workspace_admission.py:89`).
- [x] `test_leaf_workspace_admission.py:26-27`: bullet (i) of the module

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
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
