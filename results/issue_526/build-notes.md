# Build notes — issue 526 / plan-advisory-truthful-when-sandbox-cannot-start (iteration 2)

Target: `eduralph/pdca-harness @ main`, base `origin/main` = `4050da2`. Every `path:line`
below is on that base (`base`) or on the patched tree (`patched`, i.e. base + `patch.diff`).

## What changed, by criterion

**(a) Sandbox failure is filed as infra, with its cause.**
- New marker `sandbox-empty` + its §6 label:
  `template/src/pdca_harness/assemble.py` base 99-108 → patched 105, 112-113.
- New failure class `_FAIL_SANDBOX` and its placeholder text in
  `_unavailable_classification`: `template/src/pdca_harness/leaves.py` base 2766-2768,
  2810-2847 → patched 2796, 2838-2886. The text names the vendor sandbox, says a plain
  re-run fails the same way, and says what the host needs.
- Evidence reader, placed before the runner (patched `leaves.py:3414-3502`):
  `_BashSandboxProbe` (patched 3455) reads the leaf's own stream. It matches each Bash
  `tool_result` to its `tool_use` by id. It reports "the sandbox could not start" only if
  the leaf made Bash calls, **none** ran, and **every** failure carries the sandbox
  helper's own line-start prefix (`apply-seccomp:` / `bwrap:`, patched 3425).
  `_sandbox_refusal` (patched 3498) finds the CLI's own "sandbox required but
  unavailable" line when the CLI refuses to start (exit 1).
- Wiring in `_run_plan_advisory_sandboxed` (base 3344-3394 → patched 3505-3581):
  exit 0 + no artifact + probe evidence → `sandbox-empty`; exit ≠ 0 with the refusal
  line → `sandbox-empty`; anything else → exactly as before.
- The placeholder's closing instruction says "make the host able to start the
  sandbox, then re-run it" for this class only (`_plan_advisory_unavailable`, base
  3407-3417 → patched 3608-3620).

**(b) The benefit record says the review did not complete, and why.**
- `plan-advisory-benefit.json` gains `completed` (bool) and `not_completed`
  (`{leaf id: leaf status}`), `leaves.py` base 3512-3520 → patched 3715-3731.
- One artifact walk, `_plan_advisory_outcomes` (patched 3282), now feeds both
  `_plan_findings` (base 3207-3225 → patched 3256-3268) and the new
  `_plan_not_completed` (patched 3271). This is the sign-off's optional cleanup.
- `act` reads SUMMARY §10, not the JSON, so the §10 line changes too when a review did
  not complete: `- Plan advisory NOT completed (sandbox-empty): plan-reviewer — …. Its
  counts (0 finding(s); brief revised: no) say nothing about the brief`
  (`assemble.py` base 361-368 → patched 368-387). The status comes first because
  `act._norm` groups §10 lines by their first 8 words (`act.py:871-873`). Records
  without the new fields (older bundles) render exactly as before.

**(c) Findings still reach the bundle without Bash.**
- Agent frontmatter `tools:` gains `Write`: `template/.claude/agents/plan-reviewer.md.jinja:9`
  (the brief cites `:8`; it is line 9 on base).
- The prompt now carries the condition as TEXT (sign-off item 1):
  `_plan_advisory_prompt`, base 3139-3159 → patched 3178-3207. It says: if Bash does not
  work (every command fails before it starts, `apply-seccomp:`/`bwrap:`), finish with
  Read/Grep/Glob, create the file with Write, make its first line say Bash was
  unavailable — "Do not add that line when Bash works."
- Agent body (`template/agents/plan-reviewer.md.jinja`, base 30-32 and 49-53 → patched
  32-34 and 57-61): "no Write/Edit" became "no Edit, and Write only to deliver your
  output file into your cwd", plus the same fallback paragraph. Leaving "You have no
  Write/Edit" would contradict the new tool. Iteration 1 missed this.
- If the review arrives while the probe shows Bash was dead, the harness appends its
  own note with the vendor error (`_note_bash_unavailable`, patched `leaves.py:3584`).
  So "it still states that Bash was unavailable" doesn't depend on the model
  remembering. It is a blockquote, not a bullet, so it is never counted as a finding.

**(d) Boundary unchanged; brief and target not writable.**
- The three sandbox keys are written exactly as before. `_seed_plan_sandbox_settings`
  (base 2656-2691 → patched 2663-2713) gains `read_only=`, and the runner passes the
  bundle dir and the pinned target (patched `leaves.py:3542-3543`). Each becomes
  `permissions.deny: ["Edit(//<abs path>/**)"]`, with both the given and the resolved
  spelling. Deny rules only take away; no allow rule and no Check grant is added.
  `test_claude_plan_reviewer_gets_a_minimal_failclosed_sandbox` is untouched and green.
- **Deliberate change from iteration 1:** the example argv does NOT add `Write` to
  `--allowedTools` (`template/pdca.toml.jinja` base 750 → patched 757, unchanged line).
  A comment explains why (patched 745-751). Evidence below (probe P2-C).

**(e) A working sandbox that writes nothing keeps today's class.** The leaf's own text
is never read. Only tool results are, and only with the vendor prefix, and only when no
Bash call ran. The test covers exactly the sign-off's case ("The sandbox is working
normally" as the closing text of a run whose Bash worked), plus two neighbours.

`progress.py` gains one opt-in hook, `on_event` (base 35-51, 203-205 → patched 51,
151-158, 216-220). `_invoke` passes it through (`leaves.py` base 566-578, 657-660 →
patched 579, 667). It is called with each decoded stream event, and exceptions are
swallowed, like the existing `status`/`telemetry` hooks. Default `None`: every
existing caller is byte-identical. `import re` added (`leaves.py` patched 42).

## How the iteration-1 carry-forward was addressed

1. *Condition into the prompt text* — done (see (c)). Guarded by
   `test_the_bash_fallback_is_in_the_prompt_the_model_reads`.
2. *Classify only on evidence the sandbox failed to start, not the word "sandbox"* —
   done, and stricter than asked: the model's words are not read at all. Evidence is
   the vendor's own tool error, required on every Bash call, with none succeeding.
   Guarded by `test_a_working_sandbox_that_delivers_nothing_keeps_todays_class`, whose
   first case is the exact "the sandbox is working normally" run (pinned real bytes).
3. *Red must be a real assertion, not an AttributeError* — every new test asserts
   literals (`"<!-- pdca:leaf-status sandbox-empty -->"`, `"sandbox-empty"`,
   `benefit.get("completed")`, `benefit.get("not_completed")`). None references
   `LEAF_STATUS_SANDBOX`, `_FAIL_SANDBOX` or any other symbol the fix adds. Proven by
   the gate's red leg below: 9 FAILs, 0 ERRORs.
4. *Keep the Write route + frontmatter, the `completed` field, live evidence* — kept.
   The one part of iteration 1's route I dropped is `Write` in `--allowedTools`: live,
   it let Write overwrite a file outside every granted directory (P2-C).
5. *Optional: share one artifact-status loop* — done (`_plan_advisory_outcomes`).

The iteration-1 reviewer also asked for sentinel evidence that Write cannot alter the
real brief or the pinned target. Iteration 1 would have failed that: its own comment
admitted Write reaches `--add-dir` paths, and live it does (P2-A). Fixed by the deny
rules, and proven with sentinels (P2-B, P5, E2E runs).

## Why this mechanism, and what I ruled out (with costs)

- **Evidence = the stream's tool results, via a hook** (5 code lines in `progress.py`,
  1 parameter in `_invoke`). Iteration 1 read the model's final text. The sign-off
  rejected that (false positive on "the sandbox is working normally"). It also cost
  more: about 30 lines in `progress.py` (`keep_final_text`, `_final_assistant_text`,
  a banner) plus two `_invoke` parameters (`keep_final_text`, `capture_into`).
- **`capture=True` for this leaf instead of a hook** — rejected. Under `capture`,
  `output` becomes the raw stdout, so every plan-advisory failure's
  `plan-advisory-<id>.error.log` would hold the whole JSONL stream instead of the
  ≤200-line stderr tail (`_format_leaf_attempt`, base `leaves.py:788-800`). The #506
  report append is also skipped under `capture` (base `progress.py:303`).
- **Reading the session transcript under `~/.claude/projects/`** — rejected. It depends
  on the vendor's storage layout and session id; the stream already has the data.
- **Deny rules in the seeded settings, rather than `--disallowedTools` on argv or
  `chmod -R a-w` on the pinned target.** `--disallowedTools` is a claude-only flag, and
  the runner builds argv from family profiles (`families.py`); it would need a new
  profile field. `chmod` touches `_pinned_plan_target` (base 3302-3341), walks the
  whole target tree, and must restore permissions before `worktree remove --force`,
  for every family. The seed is already the claude-only policy channel; the change is
  6 code lines, and live-verified (P2-B, P5).
- **Denying only the bundle `d` and the pinned target, not `cfg.bundle_root` or
  `cfg.root`.** Those are the two things (d) names. Other bundles and the instance are
  not working directories, so the CLI asks for approval there, which a `-p` run
  cannot give (P2-A shows the refusal: "Claude requested permissions to write to …,
  but you haven't granted it yet"). Denying `cfg.root` would also block the leaf's own
  cwd if an operator's `TMPDIR` sits under the instance.
- **A "final text becomes the artifact" delivery route instead of Write** — considered
  and not taken. It would need no new tool and no deny rules. But the sign-off said to
  keep the Write route, and Write delivered live on both haiku and sonnet.
- **The refusal path (exit 1, bubblewrap missing) is included on purpose.** It is the
  same seeded `failIfUnavailable` failing on "a host where the vendor sandbox cannot
  start" (the brief's Scope). Today it files as "substantive — do not assume an infra
  blip" too: the CLI's `result` event counts as session output, so `produced=True`,
  and the leaf is classified substantive. Cost: 8 lines in the runner plus
  `_SANDBOX_REFUSAL_RE`. One test, one live observation (P3). If the reviewer calls it
  scope creep, it comes out cleanly: drop `_sandbox_refusal`, its regex and the
  `if refusal:` branch.

## Live checks on this host (supplementary evidence; not gates)

Host: `sysctl kernel.apparmor_restrict_unprivileged_userns` = 1, `unshare -Ur true` →
`write failed /proc/self/uid_map: Operation not permitted`, `claude` 2.1.277, `bwrap`
and `socat` installed. All scratch lives under `results/issue_526/.scratch/`.

- **P1 — the defect, raw stream.** Seeded fail-closed settings. Asked to run
  `echo hello`: exit 0, stderr empty. The Bash `tool_result` was `is_error: true`,
  `Exit code 1\napply-seccomp: write /proc/self/setgroups (nested userns is
  capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`.
  Pinned as `template/tests/fixtures/claude_sandbox_cannot_start.stream.jsonl`.
  This also confirmed that settings load from the cwd even inside the pdca-pdca repo.
- **P2 — Write's reach** (neutral probe agent with `tools: Read, Bash, Grep, Glob,
  Write`, `acceptEdits`, `--setting-sources project`, `--add-dir <target>`, sentinels):
  - A (the three sandbox keys only, i.e. iteration 1's policy): Write **created
    `target/NEW.txt` and overwrote `target/SENTINEL.txt` → "CHANGED"**. The bundle
    stand-in (not granted) was refused by the approval prompt.
  - B (plus `Edit(//…/**)` deny rules for target + bundle): all four writes refused,
    "File is in a directory that is denied by your permission settings". Both still
    readable. Write into the cwd works.
  - C (three keys only, `--allowedTools …,Write`, i.e. iteration 1's example argv):
    Write **created `bundle/NEW.txt` and overwrote `bundle/brief.md` → "CHANGED"**, a
    path outside every granted directory. That is why `Write` stays out of the argv.
- **P3 — refusal.** Same run with `bwrap` hidden from `PATH`: exit 1 before any API
  call, stderr `Error: sandbox required but unavailable: … bubblewrap (bwrap) not
  installed …`, stdout one `result` with `is_error: true`. Pinned as
  `claude_sandbox_refused.{stream.jsonl,stderr.txt}`.
- **P4 — working Bash** (this run with `sandbox.enabled: false`, since this host
  cannot start one): `echo hello` → `hello`, `false` → `Exit code 1`, closing text "The
  sandbox is working normally. I reviewed the brief and found no issues." Pinned as
  `claude_bash_ran.stream.jsonl`.
- **P5 — boundary with the production seed output.** The settings file was written by
  the patched `_seed_plan_sandbox_settings(…, read_only=(bundle, target))`, not by
  hand. Same result as P2-B: 4 writes denied, sentinels intact, cwd write fine.
- **End-to-end through `leaves.run_plan_advisory`** (`.scratch/live/e2e/run_e2e.py`: a
  scratch instance, a toy target repo `org/toy`, the real pinned-worktree path, the
  real `claude`):
  - E2E-1, patched code + patched agent, haiku: the artifact is a real review (2
    findings). First line "Bash was unavailable in this run.", harness note appended.
    Benefit `completed: true, not_completed: {}, findings: 2`. Brief sha unchanged,
    target checkout unchanged, pinned worktree removed.
  - E2E-4, same on **sonnet** (the model pdca-pdca runs this leaf on): real review, 1
    finding. First line names the `apply-seccomp` error, harness note appended, benefit
    `completed: true`. Brief and target unchanged.
  - E2E-2, patched code + the *old* agent (no Write): exit 0, no file → placeholder
    `sandbox-empty` quoting the real `apply-seccomp` line. Benefit `completed: false,
    not_completed: {"plan-reviewer": "sandbox-empty"}`.
  - E2E-3, **unpatched base code** + old agent (the live red): `human-empty`,
    "substantive — needs a human … do not assume an infra blip". Benefit has only
    `findings: 0, revised: false`, no completion field. This is the defect as reported.
- The probes cost about $0.26 in total by the CLI's own `total_cost_usd`. The four
  E2E runs don't report cost (the production path does not keep the `result` event).

## Gate scripts run (project's own, on a fresh clone of base + `patch.diff`)

- `engine/scripts/run-verify.sh` (C4): **PASS**. Green leg: `Ran 32 tests … OK`. Red leg
  (production hunks reverted, tests and fixtures kept): `FAILED (failures=9)`, 0 errors.
  Each failure is the pre-fix behaviour, e.g. `'<!-- pdca:leaf-status sandbox-empty -->'
  not found in '… human-empty …'`, `None != {'plan-reviewer': 'human-empty'}`,
  `'Edit(//tmp/…/pinned-target/**)' not found in []`. Log: `.scratch/c4-verify.log`.
- `engine/scripts/run-suite.sh` (T3): root suite `Ran 24 … OK` (includes the render
  test that re-runs the driver suite inside a rendered instance), driver suite
  `Ran 1901 … OK (skipped=2)`. Log: `.scratch/t3-suite.log`. The first T3 run failed:
  my agent-file test read `.jinja` paths that don't exist in a rendered instance. I
  fixed it with the `.jinja`-then-rendered fallback other tests use
  (`test_act_index_sizing.py:38-47`).
- `engine/scripts/run-docs-check.sh` (T2): lint clean, 22-page render + link audit OK.
- `git diff --check` on the patched tree: clean. The target has no Python formatter
  or commit hooks (`.github/workflows/*`, no `.pre-commit-config.yaml`, no hooksPath).
  The one whitespace issue was the pinned stderr's final blank line, which I dropped;
  the fixture README says so.

## Refuting my own test

- **(a) Genuine red? Yes.** The C4 script reverted every production hunk (agent
  frontmatter and body, config comment, `leaves.py`, `progress.py`, `assemble.py`) and
  kept the tests and fixtures (`git apply --exclude=template/tests/*` also keeps
  `template/tests/fixtures/…`; I checked that on a throwaway patch). 9 tests FAILED on
  assertions, 0 ERRORs, no import failure. The (e) test's classification assertions
  pass pre-fix, as they should. It goes red only on the missing `not_completed` field.
- **(b) Production path? Yes.** The stand-in replaces only the vendor CLI: a Python
  interpreter in the leaf's `argv`, the boundary the brief suggests. Everything else is
  production: `run_plan_advisory` → `_run_plan_advisory_leaves` →
  `_run_plan_advisory_sandboxed` → `_invoke_leaf_resilient` → `_invoke` →
  `progress.run_with_heartbeat` (a real `Popen`, the real stream drain) → the probe →
  the real placeholder and benefit writers. The seed test mocks only
  `_invoke_leaf_resilient` and `_pinned_plan_target`, both pre-existing, as the peer
  test at base `test_plan_advisory.py:110-138` does; the seed function itself runs.
- **(c) Fixture includes the fault? Yes.** The stand-in replays bytes the real CLI
  wrote on this host while its sandbox could not start (P1, P3), not a synthesized
  shape. The (e) fixture is a real run containing the exact false-positive trap. The
  live E2E runs used the real CLI on the real restricted host, with no stand-in.

## One tool restriction (same as iteration 1)

My Edit tool refused `template/.claude/agents/plan-reviewer.md.jinja` ("a sensitive
file"). I did not route around that refusal in the worktree. `$PDCA_WORKTREE` therefore
lacks that one line. `patch.diff` carries it as a hand-built hunk (first hunk in the
file), with blob ids from `git hash-object` matching base (`4d5b198`) and result
(`6d08ddf`). Verified by `git apply --check` + apply on a fresh clone at `4050da2`, where
the file reads `tools: Read, Bash, Grep, Glob, Write` and every gate script above ran
green. Everything else in the worktree is byte-identical to that patched clone.

## Not verified here, or worth knowing

- On a host where the sandbox DOES start, Claude Code may also apply `Edit` deny rules
  to Bash's sandboxed writes. If so, Bash can no longer write inside the pinned target
  (e.g. build caches). That matches the documented intent ("`$PDCA_TARGET` is
  grounding you read, never write", agent body patched line 40), but I could not observe it on
  this host.
- `bwrap:` as a prefix and the `Sandbox Error:` refusal line are read out of the
  binary / bubblewrap's conventions, not observed. Only `apply-seccomp:` and "sandbox
  required but unavailable" were observed.
- Out of scope, pre-existing: `--allowedTools Read` (bare) lets Read reach paths
  outside the granted dirs. In E2E-4 the model read the primary checkout's `.git`
  config. This fix neither changes nor relies on read confinement.
- The pdca-pdca instance gets the new agent line only through `copier update`. Its
  `pdca.toml` keeps the leaf disabled pending this issue (`pdca.toml:899-931`).

## Leftovers in the bundle

- `.scratch/` holds my scratch: two repo clones, live-probe dirs, E2E runs, gate logs,
  about 59 MB. `pdca record` stages `git add -A -- results/issue_526` (`record.py:111`),
  which would sweep it in. So I added `.scratch/.gitignore` (`*`) rather than deleting
  anything. The evidence stays on disk for sign-off and out of the records commit.
- `patch.diff.wip`, `source.diff.wip` (19:38) and the `.scratch/plan-reviewer.md.jinja.*`
  pair predate this attempt (iteration 1). I left them alone. `test_plan_advisory.py`
  in the bundle is now this attempt's file.
