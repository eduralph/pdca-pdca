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

Review issue #526: preserve Plan advisory delivery and truthful completion reporting when the vendor sandbox cannot start, while retaining confinement.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The required outcomes distinguish unavailable review, delivered review, healthy empty output, and preserved confinement; each has an observable criterion (`brief.md:27`, `target/template/tests/test_plan_advisory.py:255`). |
| C2 Reproduction (red pre-fix) | PASS | Independent production-only stash reproduced nine assertion failures, including `human-empty` instead of `sandbox-empty` and missing completion metadata, without missing-symbol errors (`review-red.log:28`, `review-red.log:37`, `target/template/tests/test_plan_advisory.py:255`). |
| C3 Change | PASS | No confirmed patch defect found: ordinary command failures retain their classification, unavailable reviews remain distinct from zero findings, and the fallback instruction is conditional (`target/template/src/pdca_harness/leaves.py:3487`, `target/template/src/pdca_harness/leaves.py:3199`, `target/template/src/pdca_harness/assemble.py:377`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Confirm real Claude Write delivery and target/bundle denial on the restricted host — offline red→green passes, but authenticated Claude was not available to this reviewer, so those vendor behaviors still rest on a stand-in and policy inspection (`review-live.log:4`, `target/template/tests/test_plan_advisory.py:292`, `target/template/tests/test_plan_advisory.py:331`). |
| C5 Causal adequacy | PASS | The required Bash-independent delivery route addresses the lost-output cause; the event observer classifies actual failures and does not guard an eager/load-time capability side effect (`target/template/agents/plan-reviewer.md.jinja:57`, `target/template/src/pdca_harness/leaves.py:3455`). |
| T1 Structure | PASS | Stream observation stays generic, vendor interpretation stays in the leaf runner, and outcome interpretation is shared with Act reporting (`target/template/src/pdca_harness/progress.py:216`, `target/template/src/pdca_harness/leaves.py:3282`, `target/template/src/pdca_harness/assemble.py:368`). |
| T2 Shape | PASS | Independent docs lint and 22-page render/link audit passed, as did `git diff --check`; both frozen docs gates corroborate those results (`review-docs.log:1`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver suite passed 1,901 tests with two skips; frozen evidence also shows 24 root tests passing. Local root rerun lacked importable Copier, a host limitation rather than a patch failure (`gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1713`, `review-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the frozen gate explicitly defers its substantive audit to mandatory publish-time execution (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by every affected path — the brief records checks for core paths, but the disposable target has only one synthetic base commit and no remotes, so completeness, including `progress.py` and `assemble.py`, cannot be established here (`brief.md:103`, `review-prior-art.log:2`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether operators can use the host-failure guidance and distinguish incomplete reviews at Act, and accept the live delivery/confinement evidence before sign-off — offline behavior alone cannot establish that operational outcome (`target/template/src/pdca_harness/assemble.py:385`, `target/template/src/pdca_harness/leaves.py:2868`, `brief.md:95`). |

Independent evidence:

- Stashed only production/prompt changes, retaining the added tests and pinned fixtures; the focused suite ran 32 tests and failed nine assertions. Restored the stash and reran the same command: all 32 passed (`review-red.log`, `review-green.log`). The target patch was restored and remains uncommitted; no source fix was made.
- Command: `TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/target/template/src" python3 -m unittest discover -s target/template/tests -p test_plan_advisory.py`. Full driver rerun used the same environment without `-p`; its complete output is `review-suite.log`.
- The frozen C5 scanner says only “patch adds no new test file”; it does not establish production coverage. Source inspection and the subprocess-based focused rerun establish that the appended tests call `leaves.run_plan_advisory` (`target/template/tests/test_plan_advisory.py:249`).
- Docs lint/render were rerun directly from the target using its CI commands. The local root suite exited 77 because `/usr/bin/python3` cannot import Copier. The frozen T3 log supplies the successful root-suite evidence; this is not an undischarged gate-tool dependency.
- All six supplied gate logs were inspected. T4's deferred result is not an unavailable gate. The provided integration template enumerates no additional concrete human-only items (`target/template/docs/INTEGRATION.md.jinja:80`). Source citations above ground in the supplied patched target; no stale-target caveat was needed.

Live dependency and concrete follow-up:

`unshare -Ur true` failed with `write failed /proc/self/uid_map: Operation not permitted`; `bwrap` exists. A real Claude 2.1.277 run loaded the patched agent with Read/Bash/Grep/Glob/Write and the fail-closed policy, then exited 1 with `authentication_failed` before any tool call (`review-live.log:3`). No review was produced. The unchanged sentinels therefore prove nothing about permission enforcement. None of the frozen logs supplies a successful authenticated delivery-and-denial run.

The prepared fixture is `review-tmp/live/`: it contains the patched agent, seeded settings, and disposable target/bundle sentinels. To complete the check while this scratch bundle exists, authenticate Claude interactively using the fixture's isolated `CLAUDE_CONFIG_DIR`, then run:

```sh
cd /tmp/pdca-review-lpnuj68o/review-tmp/live
export CLAUDE_CONFIG_DIR="$PWD/cli-config"
export XDG_CACHE_HOME="$PWD/cache"
export TMPDIR=/tmp/pdca-review-lpnuj68o/review-tmp
claude -p --model haiku --agent plan-reviewer \
  --permission-mode acceptEdits --allowedTools Read,Bash,Grep,Glob \
  --setting-sources project --add-dir "$PWD/pinned" \
  --output-format stream-json --verbose \
  'Try Bash echo hello once. If it fails, use Write to create plan-advisory-plan-reviewer.md with a brief review disclosing that Bash was unavailable. Then attempt Write to pinned/sentinel.txt and bundle/brief.md with changed content; report whether both are denied. Modify no files outside this cwd.'
```

Require a recorded sandbox startup error, a delivered review, denied writes to both sentinels, and unchanged sentinel contents. Then exercise `leaves.run_plan_advisory` with the authenticated configured leaf on the restricted host and retain the resulting real review plus `plan-advisory-benefit.json`; check `completed: true` for delivery and `completed: false` with `sandbox-empty` when delivery fails. This discharges the real-vendor dependency behind criteria (c)/(d), which the Python stand-in cannot test.

### Advisory — code-review

# Check advisory — code review (issue #526)

Read the whole diff against target source, traced the new `_BashSandboxProbe` /
`_sandbox_refusal` / `_seed_plan_sandbox_settings` machinery through `progress.py`'s
existing #506 retention plumbing and the retry loop in `_invoke_leaf_resilient`, and
cross-checked the gate logs (C4 shows all 9 new tests failing on real assertions
pre-fix, passing post-fix; T3 is 1901/1901 green).

## Findings

- No correctness bug found in the new stream-watching path. One thing worth a human's
  eye rather than a rebuild: `_seed_plan_sandbox_settings`
  (`template/src/pdca_harness/leaves.py:2699-2701`) denies only `Edit(<path>/**)`, never
  `Write(<path>/**)`, to keep the target/bundle read-only while granting the leaf `Write`
  as its no-Bash delivery route. That's deliberate and matches this repo's own established
  fact (`template/tests/test_settings_permissions.py:13-16`: Claude Code's file-permission
  checker only ever consults `Edit(path)` rules, and an `Edit` deny is documented there to
  cover `Write` too) — not a gap, just flagging the dependency so a reviewer knows where the
  safety property actually lives.
  - NEEDS-HUMAN — The stronger version of the same point: the double-slash absolute-path
    spelling `Edit(/{path}/**)` (`template/src/pdca_harness/leaves.py:2699-2701`, asserted
    verbatim in `template/tests/test_plan_advisory.py:363`) is a claim about Claude Code's
    own path-rule syntax that no test in this diff exercises against the real vendor CLI —
    the only test that touches it (`test_the_seeded_policy_keeps_the_target_and_the_bundle_read_only`)
    mocks `_invoke_leaf_resilient` out entirely and just checks the JSON the harness writes,
    never that the vendor actually honors it. Criterion (d) rests on this rule actually
    blocking `Write`, and the docstring says it was "observed" live that *without* the rule
    Write escaped to the target — but there's no equivalent observed-live confirmation in
    the diff, brief, or gate evidence that the rule *with* the leading `//` actually stops
    it. If that live confirmation happened during the build and just isn't reflected here,
    this is a non-issue; if not, it's worth one live rerun before relying on it as the
    fail-closed boundary criterion (d) requires.

- Efficiency / reuse: `_sandbox_refusal` (`template/src/pdca_harness/leaves.py:3498-3502`)
  regexes `err.output` for the CLI's "sandbox required but unavailable" text. That text
  reaches `output` through the pre-existing #506 retention path in
  `template/src/pdca_harness/progress.py:316-325` (`_terminal_error` → `terminal["text"]`
  appended to `output`) plus the stderr tail capture — the patch correctly builds a
  classifier on top of that existing evidence-retention plumbing instead of adding a new
  parallel capture path. No duplication to flag here; noting it because it's easy to
  mistake for a second capture mechanism on a first read.

- Retry-loop interaction checked and clean: `_invoke_leaf_resilient` reuses the same
  `on_event=bash` probe instance across retry attempts, but the two failure shapes this
  patch adds either never raise (rc=0, cannot-start case: `_BashSandboxProbe` only sees one
  attempt) or aren't classified as transient (`result` event counts as "produced," so
  `exc.transient` is `False` and the refusal case doesn't retry either) — so the probe is
  never fed events from more than one attempt in practice. Confirmed by the gate log:
  32 tests in well under a second, no multi-second retry backoff observed.

If nothing else turns up on a live rerun of the read-only test, this patch is clean on
both lenses: no bugs introduced, and the one duplication risk I went looking for (a second
artifact-status walk, called out in the brief's carry-forward note) was actually
consolidated into the shared `_plan_advisory_outcomes` generator
(`template/src/pdca_harness/leaves.py:3282-3295`).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Confirm real Claude Write delivery and target/bundle denial on the restricted host — offline red→green passes, but authenticated Claude was not available to this reviewer, so those vendor behaviors still rest on a stand-in and policy inspection (`review-live.log:4`, `target/template/tests/test_plan_advisory.py:292`, `target/template/tests/test_plan_advisory.py:331`).
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by every affected path — the brief records checks for core paths, but the disposable target has only one synthetic base commit and no remotes, so completeness, including `progress.py` and `assemble.py`, cannot be established here (`brief.md:103`, `review-prior-art.log:2`).
- [x] Validation — fitness-to-purpose — Decide whether operators can use the host-failure guidance and distinguish incomplete reviews at Act, and accept the live delivery/confinement evidence before sign-off — offline behavior alone cannot establish that operational outcome (`target/template/src/pdca_harness/assemble.py:385`, `target/template/src/pdca_harness/leaves.py:2868`, `brief.md:95`).
- [x] The stronger version of the same point: the double-slash absolute-path

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
- By / date: Eduard Ralph / 2026-09-18

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
