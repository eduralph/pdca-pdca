# Result — issue 526 / plan-advisory-truthful-when-sandbox-cannot-start

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: On a host that denies unprivileged user namespaces (Ubuntu's default
  `kernel.apparmor_restrict_unprivileged_userns = 1`), the `[[leaves.plan_advisory]]` leaf
  produces nothing, and its empty result is reported as a substantive failure. Three facts
  combine. (1) It is the only leaf the harness runs with the vendor sandbox turned ON and
  fail-closed: `_seed_plan_sandbox_settings`
  (`template/src/pdca_harness/leaves.py:2656-2688`) writes
  `{"sandbox": {"enabled": true, "allowUnsandboxedCommands": false, "failIfUnavailable": true}}`
  and the runner adds `--setting-sources project` (`leaves.py:3373-3378`). (2) On such a host the
  sandbox (bubblewrap) cannot start, so every Bash call fails, even `echo hello`. (3) Bash is the
  leaf's only way to write its file: the template argv grants `Read,Bash,Grep,Glob`
  (`template/pdca.toml.jinja:750`), the agent's frontmatter says `tools: Read, Bash, Grep, Glob`
  (`template/.claude/agents/plan-reviewer.md.jinja:8`), and the prompt requires writing
  `plan-advisory-<id>.md` (`leaves.py:3139-3160`). The leaf then exits 0 with no file, so the runner
  files "produced no artifact" (`leaves.py:3394`) at the default `_FAIL_SUBSTANTIVE`
  (`leaves.py:2768`, `:3407-3408`). `_unavailable_classification` (`leaves.py:2810-2840`) marks
  that as the needs-a-human class, and the §6 text tells the human it is "not an infra blip",
  which is the opposite of the truth. On top of that, `plan-advisory-benefit.json`
  (`leaves.py:3514-3520`) records only `findings`/`revised`, so an unavailable run is written as
  `findings: 0, revised: false`, the same record as a review that ran and found nothing. The
  issue counts nine such records in pdca-pdca, which would wrongly convict the feature at an
  Act review.
- Success criterion: With the plan-advisory runner driven through `leaves.run_plan_advisory`,
  on a leaf run where the vendor sandbox cannot start (the leaf exits 0, no Bash command ran):
  (a) the bundle's `plan-advisory-<id>.md` is not classified as the needs-a-human class. It carries
  an infra `pdca:leaf-status` marker, and its text names the unavailable vendor sandbox as the
  cause, so the operator can act on it; (b) `plan-advisory-benefit.json` records that this leaf's
  review did not complete, in a way `act` / an Act reader can tell apart from "ran, 0 findings";
  (c) the reviewer's findings still reach the bundle on such a host, by a delivery route that does
  not depend on Bash. When that works, the artifact is the leaf's real review, and it still states
  that Bash was unavailable. (d) The fail-closed boundary is unchanged: the seeded policy still
  has `enabled: true`, `allowUnsandboxedCommands: false`, `failIfUnavailable: true` and no Check
  grants, so `test_claude_plan_reviewer_gets_a_minimal_failclosed_sandbox`
  (`template/tests/test_plan_advisory.py:110-138`) stays green. The leaf still cannot modify the
  bundle's real `brief.md` or the pinned target. (e) A leaf that ran with a working sandbox and
  wrote nothing is still classified as it is today. The fix narrows the substantive class; it
  does not relabel every empty result as infra.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make the plan-advisory leaf's outcome truthful on a host where the vendor sandbox
  cannot start: the review is delivered when the model can still produce it, and when it cannot,
  the placeholder and the benefit record say "environment", not "substantive". The mechanism is
  Do's call; the issue lists options without choosing one. The only rule on the fix shape: the
  boundary in (d) stays. / out of scope: relaxing or dropping the fail-closed seed
  (`failIfUnavailable`, `allowUnsandboxedCommands`); Check-side leaves and their
  `_seed_sandbox_settings` path; the `doctor` preflight (#452); making `unshare` work on the host;
  back-filling the nine existing pdca-pdca placeholders.

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

Review issue #526: preserve truthful Plan advisory outcomes and deliver reviews when the vendor sandbox cannot start, without weakening confinement.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable failure classification, completion telemetry, delivery, confinement, and working-sandbox behavior; these distinguish a successful review from unavailable execution (`brief.md:23`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes and driving the existing subprocess boundary reproduced `human-empty` and absent completion telemetry for sandbox startup failure (`review-tmp/base-observation.log:1`; fixture at `template/tests/test_plan_advisory.py:52`). |
| C3 Change | FAIL | Healthy runs are instructed to claim Bash was unavailable because the intended conditional and Write-tool instruction are Python comments, not prompt text (`template/src/pdca_harness/leaves.py:3194`). |
| C4 Verification (red→green) | FAIL | The supplied sandbox regression errors on a new constant before testing the old status, contrary to the required behavioral red; independent observations confirm the narrow fix but do not repair the submitted regression (`template/tests/test_plan_advisory.py:185`; `gate-logs/C4-verify.log:48`). |
| C5 Causal adequacy | FAIL | A healthy sandbox explicitly reported as working is still classified as unavailable; merely mentioning the capability does not establish failure and violates criterion (e) (`template/src/pdca_harness/leaves.py:3428`; `review-tmp/probes.log:21`). |
| T1 Structure | PASS | Output retention is opt-in and the existing classification/artifact path remains shared; no unrelated subsystem or dependency was added (`template/src/pdca_harness/leaves.py:575`; `template/src/pdca_harness/progress.py:48`). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page render/link audit, and diff whitespace checks passed; frozen host-parity evidence also reports successful lint and link audit (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 1,896 tests with two skips; frozen root-suite evidence shows 24 tests passed, while this reviewer interpreter lacks importable Copier (`review-tmp/driver-suite.log:1660`; `gate-logs/T3-suite.log:54`; `review-tmp/root-suite.log:7`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the substantive audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for all six affected paths — the brief reports a narrower path search, and this disposable target has one synthetic commit and no remotes, so independent history adjudication is unavailable (`brief.md:103`; `template/src/pdca_harness/progress.py:48`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether authenticated live evidence establishes usable Write delivery and unchanged confinement — the required real vendor session was not exercised beyond authentication, so current delivery/boundary evidence rests on code inspection and offline fixtures (`brief.md:95`; `template/pdca.toml.jinja:752`; `review-tmp/tmp18010wkp/results/issue_LIVE/plan-advisory-live.error.log:3`). |

Source citations beginning `template/` refer to the applied tree at `$PDCA_TARGET` (`/tmp/pdca-review-l5l8bypt/target`). The target was readable and consistent with the patch. All stashed changes were restored; no implementation edits were made. Verdicts are advisory and do not change deterministic gate results.

Confirmed findings:

1. **Incorrect prompt on healthy hosts.** At `template/src/pdca_harness/leaves.py:3194`, “If Bash is not working, use the Write tool instead” exists only in comments. The generated prompt instead ends with an unconditional instruction to say Bash was unavailable. I called the production prompt generator and recorded its actual output in `review-tmp/probes.log`. Put both the condition and delivery instruction into the prompt string, and check the healthy-host wording.
2. **False sandbox-failure attribution.** At `template/src/pdca_harness/leaves.py:3428`, any occurrence of “sandbox”, “unprivileged”, etc. is sufficient. I ran `run_plan_advisory` with a real subprocess emitting “The sandbox is working normally. I reviewed the brief and found no issues.” and no artifact. It produced `sandbox-empty` and told the operator the host denied every Bash call. This should retain the existing substantive classification under criterion (e). Use evidence of actual startup failure and cover explicit success/negation, rather than matching the topic alone.
3. **Regression red depends on the new implementation symbol.** At `template/tests/test_plan_advisory.py:185`, the pre-fix run raises `AttributeError` for `LEAF_STATUS_SANDBOX`; it never compares the old marker or reaches the benefit assertion. The other new test raises `KeyError` on `completed`. I reproduced both errors independently (`review-tmp/red.log`), matching the frozen C4 log. Assert observable status/telemetry without relying on new production symbols, so the submitted test demonstrates the specified behavioral failure. Separately, my boundary observation confirmed the real pre-fix defect and its narrow post-fix correction: `human-empty` with no completion key became `sandbox-empty` with `completed: false`.

Evidence limits and human follow-through:

- The full offline driver suite passed after restoration. Docs validators passed independently. The root suite could not exercise Copier under this interpreter; its frozen gate log explicitly shows render/update tests passing. This is a reviewer-host caveat, not a patch defect. The C5 scanner log says “patch adds no new test file”; it did not assess the appended tests. Inspection and the independent subprocess probes establish that those tests call production code.
- `claude --version` reported 2.1.276 and `unshare -Ur true` failed with `Operation not permitted`. I attempted the production runner with the patched tool allowlist and an isolated Claude configuration inside this scratch directory. The CLI exited 1 with “Not logged in”; it did not exercise sandbox startup or Write delivery. None of the supplied gate logs contains an authenticated live delivery/confinement test. References to withheld builder notes are not evidence available to this review.
- To discharge live validation, use an authenticated disposable rendered instance on the restricted host. Seed the exact policy from `template/src/pdca_harness/leaves.py:2700`, then run `claude -p --agent plan-reviewer --permission-mode acceptEdits --allowedTools Read,Bash,Grep,Glob,Write --setting-sources project --add-dir "$PDCA_TARGET"` from its scratch review directory, with a prompt to attempt `echo hello` through Bash and deliver `plan-advisory-plan-reviewer.md` through Write. Capture the tool results and real review. Confirm Bash denial, successful review delivery, and accurate disclosure. Exercise the configured leaf through `leaves.run_plan_advisory` as well to verify the bundled artifact and benefit JSON.
- Use disposable sentinel files to verify that Write cannot alter the real bundle brief or pinned grounding target. This specifically needs evidence because `template/pdca.toml.jinja:752` describes Write as allowed in `--add-dir` paths, and `template/src/pdca_harness/leaves.py:3462` supplies the target through that flag. The unchanged fail-closed seed test alone does not establish Write confinement.
- The available integration template enumerates no additional concrete human-only items (`template/docs/INTEGRATION.md.jinja:80`). The C5 capability-probe smell-test found no eager-capability guard of the specified kind; the confirmed problem is inaccurate failure attribution, not a contested load-time workaround.

### Advisory — code-review

# Check advisory — code review (correctness + reuse/simplification)

- NEEDS-HUMAN [impl] — `test_sandbox_cannot_start_is_classified_infra_not_human`
  (`template/tests/test_plan_advisory.py:185`, target) fails its RED leg for the
  wrong reason. `gate-logs/C4-verify.log:48-54` shows the "production change
  reverted" run erroring with `AttributeError: module 'pdca_harness.assemble' has
  no attribute 'LEAF_STATUS_SANDBOX'` — the assertion never gets far enough to
  compare the placeholder's actual marker, because the test's own RHS
  (`assemble.LEAF_STATUS_SANDBOX`) is the symbol this patch adds. brief.md's
  Falsifiability section says exactly this shape "proves nothing" and must be
  avoided ("It must NOT fail only because it mocks or imports a symbol the fix
  adds; a red that comes from an AttributeError proves nothing... Do not patch a
  function the fix introduces"). The C4 gate still shows green-after/red-before
  mechanically, but the RED evidence for criterion (a) is not what the brief asked
  for — pre-fix, this scenario in fact misclassifies as `human-empty` (today's
  bug), and the test could show that with a literal string (`"sandbox-empty"`) or
  by asserting on the rendered marker text instead of the new constant, giving a
  real behavioral red instead of an AttributeError.

- `_plan_advisory_completed` (`template/src/pdca_harness/leaves.py:3270-3288`)
  re-implements the same glob → skip-decorrelation-note → read-text →
  `assemble.leaf_status` loop that `_plan_findings` (`leaves.py:3249-3267`) already
  has, rather than sharing one iterator/helper between them. Per bundle this is a
  third full pass over `plan-advisory-*.md` (`_plan_findings` itself is already
  called twice, at `leaves.py:3603` and `:3621`) and a second place that has to be
  kept in step if the exclusion rule (decorrelation note, placeholder detection)
  ever changes. Not a correctness bug — worth folding into one shared helper (e.g.
  a generator yielding each artifact's status) that both functions consume.

No other correctness bugs found in this diff: `_invoke`'s new `keep_final_text`/
`capture_into` params are additive and off by default (verified byte-identical
behavior for existing callers), `capture_into.append(output)` runs before the
`rc != 0` branch so a successful run's output is captured too, and it correctly
rides through `_invoke_leaf_resilient`'s `**kw` on every retry attempt.
`_final_assistant_text`/`final_text["text"]` in `progress.py` only overwrite on a
non-empty match, so a trailing tool-only `assistant` event can't clobber the real
last answer with `""`. The new `LEAF_STATUS_SANDBOX` / `_FAIL_SANDBOX` constants
are wired consistently everywhere the existing INFRA/STARTUP ones are (the
`_unavailable_classification` map, `assemble._LEAF_STATUS_LABEL`,
`assemble._items_from_artifact`'s forced-HUMAN routing for placeholders).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm merged and closed/rejected prior art for all six affected paths — the brief reports a narrower path search, and this disposable target has one synthetic commit and no remotes, so independent history adjudication is unavailable (`brief.md:103`; `template/src/pdca_harness/progress.py:48`).
- [ ] Validation — fitness-to-purpose — Decide whether authenticated live evidence establishes usable Write delivery and unchanged confinement — the required real vendor session was not exercised beyond authentication, so current delivery/boundary evidence rests on code inspection and offline fixtures (`brief.md:95`; `template/pdca.toml.jinja:752`; `review-tmp/tmp18010wkp/results/issue_LIVE/plan-advisory-live.error.log:3`).
- [ ] `test_sandbox_cannot_start_is_classified_infra_not_human`

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
- Iteration delta (if iterating): Put the "if Bash fails, use Write" condition into the prompt text itself — today it is a Python comment (leaves.py `_plan_advisory_prompt`), so the model never sees the condition and every run, healthy or not, is told to claim Bash was unavailable. Classify as sandbox-infra only on evidence the sandbox actually failed to start (tool-error text such as apply-seccomp / bwrap / uid_map / setgroups, or "sandbox ... could not start/initialize"), not the bare word "sandbox" — a healthy run saying "the sandbox is working normally" must stay classified as today (criterion e). Add a test for exactly that case. Make the red-before-fix test assert on the literal "sandbox-empty" / marker text and the benefit record, so pre-fix it fails a real assertion, not an AttributeError on the new LEAF_STATUS_SANDBOX constant (the brief's Falsifiability rule). Keep: the Write delivery route + agent frontmatter change, the `completed` benefit field, and the live-check evidence approach. Optional cleanup: share one artifact-status loop between `_plan_findings` and `_plan_advisory_completed`.
- By / date: Eduard Ralph / 2026-09-18

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
