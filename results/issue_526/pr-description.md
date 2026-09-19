## Summary
**User impact:** On a stock Ubuntu machine, the optional plan review never produces a
review. Worse, the harness then tells you the review "ran but gave no usable verdict —
do not assume an infra blip", so you go looking for a problem in your brief when the real
cause is the machine. The saved statistics record it as a review that ran and found
nothing, so over time the feature looks useless for a reason that has nothing to do with
it.

This PR lets the review still arrive on such a machine. When it can't, the harness says
plainly that the sandbox could not start on this host and what to fix. The statistics now
record "did not complete" instead of "found nothing".

Reported in [#526](https://github.com/eduralph/pdca-harness/issues/526).

## What to look at
The plan reviewer runs inside Claude Code's sandbox, set to refuse to run rather than run
unconfined. Ubuntu blocks what that sandbox needs by default
(`kernel.apparmor_restrict_unprivileged_userns = 1`), so every shell command the reviewer
tries fails, and the shell was its only way to save its review. The change has three
parts:

1. **Deliver anyway.** The reviewer may now save its file with the Write tool. When the
   shell is dead it is told to finish with Read/Grep/Glob and say so in the review. The
   harness adds its own note quoting the sandbox error, so this doesn't depend on the
   model remembering.
2. **Name the real cause.** If nothing arrives and the shell failed because the sandbox
   could not start, the result is filed as a host problem (`sandbox-empty`), not as
   "needs a human". The harness decides this from the sandbox's own error lines in the
   tool results, never from what the model says. A run whose shell worked and that wrote
   nothing is classified exactly as before.
3. **Honest statistics.** `plan-advisory-benefit.json` gains `completed` and
   `not_completed`. The SUMMARY Act-candidates line then reads "Plan advisory NOT
   completed (sandbox-empty): …".

The sandbox settings do not get weaker. Because the reviewer can now write files, the
seeded settings also block edits to the bundle and to the pinned target checkout.

**To try it** on an affected host (`unshare -Ur true` fails with
`write failed /proc/self/uid_map: Operation not permitted`): enable the commented
`[[leaves.plan_advisory]]` example in `pdca.toml` and plan a brief that matches its
`when`. Before this change you get a "needs a human" placeholder. After it you get a
real review whose first line says the shell was unavailable.

## Root cause
The plan-review leaf is the only leaf seeded with a fail-closed sandbox
(`template/src/pdca_harness/leaves.py:2656-2688` on `main`), and its only write path was
Bash, which that sandbox kills on a userns-restricted host. The leaf then exits 0 with no
file, and the runner files "produced no artifact" (`leaves.py:3394`) under the default
`_FAIL_SUBSTANTIVE` class (`leaves.py:2768`). The benefit record (`leaves.py:3514-3520`)
has no field that could tell "did not run" apart from "ran, found nothing".

## Fix
- **Delivery route:** `Write` added to the agent's `tools:`
  (`template/.claude/agents/plan-reviewer.md.jinja:9`). The fallback condition is written
  into the prompt text (`_plan_advisory_prompt`, `leaves.py:3178-3207`) and the agent
  body (`template/agents/plan-reviewer.md.jinja:32-34`, `:57-61`), and ends with "Do not
  add that line when Bash works", so healthy runs are unaffected.
- **Evidence:** `_BashSandboxProbe` (`leaves.py:3455`) watches the leaf's stream through
  a new opt-in `on_event` hook in `progress.run_with_heartbeat`
  (`template/src/pdca_harness/progress.py:51`, `:151-158`, `:216-220`; default `None`, so
  every existing caller is unchanged). It reports a sandbox failure only if the leaf made
  Bash calls, none ran, and every failure starts with `apply-seccomp:` or `bwrap:`.
  `_sandbox_refusal` (`leaves.py:3498`) covers the CLI refusing to start at all ("sandbox
  required but unavailable", exit 1).
- **Classification:** new `_FAIL_SANDBOX` → `LEAF_STATUS_SANDBOX = "sandbox-empty"`, an
  infra status with its own placeholder text (`leaves.py:2838-2886`) and label
  (`template/src/pdca_harness/assemble.py:105`, `:112-113`). The runner applies it
  (`leaves.py:3505-3581`); every other path is unchanged.
- **Record:** `completed` / `not_completed` in the benefit JSON (`leaves.py:3715-3731`).
  One artifact walk, `_plan_advisory_outcomes` (`leaves.py:3282`), feeds both the
  findings count and the new field. The Act-candidates line puts the status first, so
  `act` groups repeats of the same host fault together (`assemble.py:368-387`).
- **Boundary:** `_seed_plan_sandbox_settings` (`leaves.py:2663-2713`) still writes
  `enabled: true`, `allowUnsandboxedCommands: false`, `failIfUnavailable: true`, and now
  also `permissions.deny: ["Edit(//<abs>/**)"]` for the bundle and the pinned target
  (both the given and the resolved path). Deny rules only remove access; no grant is
  added. `Write` is deliberately left out of the example `--allowedTools`
  (`template/pdca.toml.jinja:745-757`, comment explains why).

Out of scope: a `doctor` preflight for "this host cannot start the sandbox" (#452), and
any loosening of the fail-closed settings.

## Verification
Line numbers below are on this PR's branch (`main` @ `4050da2` + this change) unless
marked `main`.

- **Claim:** a sandbox that cannot start is filed as infra and names the cause.
  **Checked:** `leaves.py:2838-2886`, `:3558-3581`.
  **Test:** `test_a_sandbox_that_cannot_start_is_filed_as_sandbox_infra`
  (`template/tests/test_plan_advisory.py:257`) and
  `test_a_cli_that_refuses_to_start_without_its_sandbox_is_sandbox_infra` (`:279`).
  Both replay real CLI output captured on an affected host
  (`template/tests/fixtures/claude_sandbox_cannot_start.stream.jsonl`,
  `claude_sandbox_refused.*`).
- **Claim:** the benefit record can tell "did not complete" apart from "found nothing".
  **Checked:** `leaves.py:3715-3731`, `assemble.py:368-387`.
  **Test:** the same two tests assert `completed: false` and
  `not_completed: {"plan-reviewer": "sandbox-empty"}`.
- **Claim:** a review delivered without the shell is kept and says the shell was
  unavailable. **Checked:** `leaves.py:3570-3574`, `:3584`.
  **Test:** `test_a_review_delivered_without_bash_is_kept_and_says_so` (`:291`),
  `test_the_bash_fallback_is_in_the_prompt_the_model_reads` (`:367`),
  `test_the_reviewer_agent_has_write_but_the_example_argv_does_not_preapprove_it`
  (`:376`).
- **Claim:** a run whose shell worked and that wrote nothing keeps today's class, even
  if the model mentions the sandbox. **Checked:** the probe reads tool results only
  (`leaves.py:3455-3496`). **Test:**
  `test_a_working_sandbox_that_delivers_nothing_keeps_todays_class` (`:309`), including a
  real run whose closing text is "The sandbox is working normally"
  (`fixtures/claude_bash_ran.stream.jsonl`).
- **Claim:** the sandbox policy is unchanged, and the bundle and target stay read-only.
  **Checked:** `leaves.py:2663-2713`.
  **Test:** `test_claude_plan_reviewer_gets_a_minimal_failclosed_sandbox` (`:140`,
  unchanged, green) and `test_the_seeded_policy_keeps_the_target_and_the_bundle_read_only`
  (`:331`). The test checks the JSON the harness writes. Whether the CLI honours the
  `Edit(//<abs>/**)` spelling was checked live: with the settings file written by the
  patched `_seed_plan_sandbox_settings`, all four write attempts on the bundle and target
  were refused ("denied by your permission settings"), test files there were left intact,
  and writing into the leaf's own directory still worked. Without the deny rules, Write
  did overwrite a file in the target, which is why they are needed.
- **Red → green:** with the production changes reverted and the tests and fixtures kept,
  9 of the new assertions fail (0 errors: none fail on a missing symbol). With the change,
  `test_plan_advisory.py` runs 32 tests OK, and the full driver suite runs 1901 OK
  (2 skipped).
- **Live, on an affected host** (Ubuntu, userns restricted, `claude` 2.1.277), through
  `leaves.run_plan_advisory` against a toy target: on haiku and on sonnet the reviewer
  delivered a real review (2 and 1 findings) via Write, first line naming the missing
  shell, benefit `completed: true`, brief and target unchanged. With the old agent
  (no Write) the result was `sandbox-empty` quoting the real `apply-seccomp` error. On
  unpatched `main` it was the misleading "needs a human" placeholder with
  `findings: 0, revised: false`, which is the bug as reported.

Fixes #526
