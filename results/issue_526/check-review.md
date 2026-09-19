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
