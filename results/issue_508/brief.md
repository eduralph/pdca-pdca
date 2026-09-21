# Brief — issue 508 / handoff-command-runs-its-own-check

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** handoff-command-runs-its-own-check
- **Defect:** The rendered `/handoff <id>` command never runs its check.
  `template/.claude/commands/handoff.md.jinja:13` runs the guard through a `!` pre-execution
  block that carries two shell expansions:
  `` !`python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/handoff_guard.py" --check "$1"` ``. Claude Code's
  shell-permission checker will not match any allow-rule against a command containing a simple
  expansion, so the block aborts before anything runs (`Error: Shell command permission check
  failed … Contains simple_expansion`, reported in the issue). `allowed-tools: Bash(python3:*)`
  (`:4`) and the instance's own allow rules cannot help: the checker refuses to match, it does not
  fail to find a match. Since #534 (e9e5982) this is worse than before: the Stop hook is retired,
  and the command body says so itself (`:17-18`: "This command is the session's self-check;
  nothing checks the contract when a turn ends"). So the only in-session check an interactive
  leaf has is the one that cannot run. The line was introduced in 900d638 (#331); e9e5982 reworded
  the body around it and left line 13 unchanged. Every render ships it (`handoff.md.jinja` is the
  only file under `template/.claude/commands/`).
- **Success criterion:** In the template on `origin/main` after the fix: (a) no `!` pre-execution
  block in any file under `template/.claude/commands/` contains a shell expansion (`$NAME`,
  `${…}`, `$1`/`$ARGUMENTS`, `$(…)`, or a nested backtick). A test enumerates the directory, so the
  rule also covers any command added later, such as the `/abandon` proposed in #404. (b) `/handoff`
  still verifies exactly ONE required id: the existing pins in
  `template/tests/test_handoff.py:121-132` (`argument-hint: <issue_id>`, "no scan mode", `$1`
  present, `handoff_guard.py` named) stay green unchanged. (c) The command body makes no claim
  that a hook enforces the contract: `ModelFacingTextPromisesNoEnforcement` in
  `template/tests/test_handoff_reap.py` stays green. (d) The command tells the session how to run
  the check in a form that works in a session's Bash tool. That tool does NOT receive
  `CLAUDE_PROJECT_DIR`: it is empty in this planner session's Bash tool, and 10-adapting.md:165
  only documents it for hook commands. So a model-made call must not depend on that variable.
- **Falsifiability:** RED for (a) on the offline driver suite: `handoff.md.jinja:13` on `origin/main`
  contains `$CLAUDE_PROJECT_DIR` and `$1` inside a `!` block, so the new test fails on the base.
  **Gate caveat (surfaced for the human):** this instance's C4 gate (`engine/scripts/run-verify.sh`)
  classifies `*.md.jinja` as non-behavioral. If the patch's only non-test change is
  `handoff.md.jinja`, C4 exits 77 `PDCA-UNVERIFIABLE` and the item lands in SUMMARY §6 (INTEGRATION
  §4 lists that as human-judged). If the patch also changes a `.py` production file, the red leg
  reverts the whole non-test diff, `.md.jinja` included, and C4 earns a real red. Do must NOT add
  a `.py` change just to earn the red. Whether the permission checker still refuses the old form
  can only be shown in a live interactive Claude Code session: `claude -p` does not show `!` block
  output at all (tried on 2.1.276 with a literal `` !`echo fixed-literal` `` block and got no
  output), so a headless run is not evidence either way. For the fixed form, the model-made-call
  shape is known to work on Claude Code 2.1.276: this instance ships it (pdca-pdca 8d5a7a2), and
  a headless `/handoff issue_481` run during this Plan session made the Bash call and got the
  guard's verdict back.
- **Invariant to restore:** A shipped slash command's pre-execution block is a command the
  permission checker can match: no shell expansion appears in any `!` block of any rendered
  command. Anything that varies per call (the id) reaches the guard by a route the checker
  accepts. Source: Claude Code's permission checker behaviour as observed and quoted in the issue
  ("Contains simple_expansion"), plus the contrast the issue draws: the same expansion is fine in
  a `hooks` entry (`template/.claude/settings.json`), which is executed directly and never checked.
  Tier B, observed vendor behaviour, not a documented rule, so treat it as corroborating. Self-test:
  a test that only looks at `handoff.md.jinja` would let a future `/abandon` ship broken, so the
  rule is stated over the whole commands directory.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:**
- **Conflicts with:**
- **Ordering note:** Run 4 of `plan-0.60-bug-order.md`, after #534 (merged, e9e5982). To stay in
  the same wave as #528, this bundle must NOT edit `template/src/pdca_harness/handoff.py` or
  `template/tests/test_handoff.py` (528 edits both); its test goes in a new file. Lands before
  #404 (0.61), which would otherwise copy the broken shape.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Make `/handoff <id>` actually run `handoff_guard.py --check <id>` in a rendered
  instance, and keep the one-required-id contract and the no-enforcement-claim wording. The route
  the id takes to the guard is Do's call. The issue lists the options: the command drops the `!`
  block and has the model make the Bash call itself (what this instance ships locally, 8d5a7a2,
  and what the `--abandon` line at `:22-23` already implies), or the guard resolves the id another
  way. The instance's local text is NOT a drop-in: its line 24 says "The Stop hook enforces this
  same contract", which #534 retired and `test_handoff_reap.py` forbids. Update the `--check`
  description in `template/.claude/hooks/handoff_guard.py:9-10` only if it becomes untrue. / out of
  scope: `template/src/pdca_harness/handoff.py` and `template/tests/test_handoff.py` (owned by #528
  this run); the `/abandon` command itself (#404); any change to how the driver judges the
  contract at reap (#534's design); `settings.json` hook registration.
- **Repro instruction:** In any rendered instance on the current template (e.g. this one before
  8d5a7a2, or a fresh render of `origin/main`), start an interactive leaf and type
  `/handoff <id>`. The expected failure is
  `Error: Shell command permission check failed for pattern "!`python3 "$CLAUDE_PROJECT_DIR/…" --check "$1"`": Contains simple_expansion`.
  Statically: `git -C ../pdca-harness show origin/main:template/.claude/commands/handoff.md.jinja | sed -n 13p`
  shows both expansions inside the `!` block.
- **External dependencies:** none for the gates (offline suite). The live confirmation needs an interactive Claude Code session in a rendered instance (a human-run check with no detect command).
- **Test file:** template/tests/test_slash_commands.py (NEW file, so it does not collide with
  #528's `test_handoff.py`). Enumerate `template/.claude/commands/*` (use the same
  `.jinja`-or-rendered dual-home lookup as `_first` in `test_handoff.py:49-54`, so the test also
  runs inside a rendered instance) and assert that no `!` block carries a shell expansion. Expect
  the C5 prod-path advisory to report this test as not importing `pdca_harness`: it checks a
  shipped file, which is correct for this defect.
- **Citations expected:** Do must cite path:line on `origin/main` for every change. Peer to
  mirror: the existing `--abandon` instruction at `handoff.md.jinja:22-23`, a model-run relative
  `python3 .claude/hooks/handoff_guard.py …` call from the project root. Interactive leaves are
  spawned with `cwd=cfg.root` (`template/src/pdca_harness/leaves.py:1001`, `:3539`, `:3688`,
  `:3758`), and the guard finds its own instance root from `__file__` when `CLAUDE_PROJECT_DIR` is
  unset (`handoff_guard.py:38-39`).
- **Prior-art check (triage cycles):** by path,
  `git -C ../pdca-harness log --oneline origin/main -- template/.claude/commands/handoff.md.jinja template/.claude/hooks/handoff_guard.py`:
  e9e5982 (#534, reworded the body and kept line 13), 900d638 (#331, introduced it). Closed-unmerged
  PRs touching these paths: none. Open PRs: none. Instance-side prior art: pdca-pdca 8d5a7a2
  replaced the block locally with a model-made call. It works, but its wording predates #534.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
