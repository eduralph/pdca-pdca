# Result — issue 508 / handoff-command-runs-its-own-check

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The rendered `/handoff <id>` command never runs its check.
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
- Success criterion: In the template on `origin/main` after the fix: (a) no `!` pre-execution
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make `/handoff <id>` actually run `handoff_guard.py --check <id>` in a rendered
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

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- C5 added test exercises production, not a copy: unverifiable — test file(s) add no import of the production package 'pdca_harness' — may exercise a copy, not production: template/test

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

Review issue #508: restore `/handoff <id>` self-check execution without expansion-bearing pre-execution blocks, preserving the required-id and no-Stop-enforcement contracts.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable command, regression, and compatibility criteria and explicitly separates live confirmation from offline evidence (`brief.md:20`, `brief.md:81`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the command change makes the retained regression test fail on `$CLAUDE_PROJECT_DIR`; this reproduces the static defect, not the interactive permission error (`reviewer-rerun.log:6`, `target/template/tests/test_slash_commands.py:52`). |
| C3 Change | FAIL | The promised protection for future commands misses inline and indented expansion-bearing blocks: the whole-line matcher silently ignores them, and the actual test passes both probes (`target/template/tests/test_slash_commands.py:29`, `reviewer-scanner.log:16`, `reviewer-scanner.log:22`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the independently reproduced static red→green discharges the explicitly human-judged C4 exception — the frozen gate exits 77 and does not verify interactive execution (`brief.md:34`, `gate-logs/C4-verify.log:10`, `reviewer-rerun.log:25`, `reviewer-rerun.log:51`). |
| C5 Causal adequacy | PASS | Removing the rejected pre-execution route addresses the reported cause without a capability probe or symptom guard; the test reads the shipped command itself, explaining the import-scanner advisory (`target/template/.claude/commands/handoff.md.jinja:13`, `target/template/tests/test_slash_commands.py:42`, `gate-logs/C5-prod-path.log:10`). |
| T1 Structure | PASS | The two-file scope respects the parallel-work exclusions and keeps checking logic in the existing guard; no architecture or Plan re-entry decision arises (`target/template/.claude/commands/handoff.md.jinja:16`, `target/template/tests/test_slash_commands.py:1`, `brief.md:72`). |
| T2 Shape | PASS | Independently rerun docs lint and 22-page rendering/link audit pass; frozen docs and host-parity logs corroborate those results (`reviewer-docs.log:1`, `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | The independent offline run passes 1,895 tests with two skips, including 64 focused handoff tests; render/update coverage rests on the frozen 24-test pass because local Python lacks Copier (`reviewer-offline.log:1656`, `reviewer-rerun.log:56`, `gate-logs/T3-suite.log:54`, `reviewer-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred substantive audit must run at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by both affected paths — the brief records a command/hook search, but the new test path is absent from that evidence and this isolated target exposes only a synthetic base commit and no remote (`brief.md:94`, `reviewer-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm that a live interactive Claude Code leaf actually issues the Bash check and relays its verdict — that external session was not exercised, so static scans and Python tests cannot establish restored user behavior (`brief.md:81`, `target/template/.claude/commands/handoff.md.jinja:16`). |

Source citations prefixed `target/` refer to the supplied `$PDCA_TARGET`; other citations name review inputs or independent evidence in this sandbox. The target was readable, the patch was present, and the command change was restored after the red leg. No production or test edits were made.

**Advisory finding (P2): broaden the block scanner to enforce the stated invariant.** At `target/template/tests/test_slash_commands.py:29`, `^` and the end-of-line requirement constrain detection to an entire unindented line. I ran the actual new unittest against scratch command files: a standalone block containing `$HOME` failed as expected, but `Current value: !` followed by a backtick-quoted `echo $HOME`, and the same block indented two spaces, both passed with zero detected blocks (`reviewer-scanner.log:1`, `reviewer-scanner.log:16`, `reviewer-scanner.log:22`). Thus a future command can contain the prohibited syntax without this regression test examining it. Recognize blocks in their supported surrounding contexts and cover these cases. The current handoff text itself contains no executable pre-execution block.

**Evidence limits and human check.** The six supplied gate logs were available. The C4 wrapper's documentation classification and C5 scanner's production-import heuristic are not patch defects. Local render-suite execution reports missing importable Copier; the frozen log explicitly shows render and update tests executing successfully, so this is a local host caveat, not an unmet dependency in the original gate run. The available integration file is the unfilled template (`target/template/docs/INTEGRATION.md.jinja:80`); the instance-specific C4 human exception is stated in `brief.md:34`.

For live validation, use a rendered instance carrying this patch. From its project root, launch `env -u CLAUDE_PROJECT_DIR claude` and enter `/handoff issue_508` (substitute a real issue id). Observe a Bash tool call equivalent to `python3 .claude/hooks/handoff_guard.py --check issue_508`, guard output rather than `Contains simple_expansion`, and verbatim relay of the verdict. Then repeat `/handoff <id>` inside the driver's registered interactive leaf for that bundle to exercise its real contract: an unmet contract must report FAIL; after satisfying its named artifacts, the same check must report PASS. An unregistered standalone session can establish tool invocation but cannot establish the registered-leaf contract. The interactive session is the remaining external dependency; a headless run does not substitute for it (`brief.md:39`).

### Advisory — code-review

# Check — advisory code review (issue #508)

Second lens: bugs the patch introduces, plus reuse/simplification. Reviewed
`patch.diff` against the target tree; ran the new test both pre- and post-patch.

## Findings

Nothing that rises to a correctness bug or a missed-reuse opportunity. Specifics
that back that up:

- `template/.claude/commands/handoff.md.jinja:13-16` — the replacement line drops
  the `!` block and asks the model to run the command itself, mirroring the
  `--abandon` line already at `:26` (same shape: bare backtick span, no `!`, no
  quoting gymnastics). I ran the new test both ways to confirm the causal claim:
  on the pre-patch tree it fails with `$CLAUDE_PROJECT_DIR` flagged; on the
  patched tree it passes (`python3 -m unittest template.tests.test_slash_commands`
  — 1 test, OK both times, matching the file's own docstring claim of red→green).
- The relative path `python3 .claude/hooks/handoff_guard.py --check $1` (no
  `CLAUDE_PROJECT_DIR`) works with the guard's own fallback: `handoff_guard.py:38-39`
  resolves the instance root from `__file__` when the env var is unset, and
  interactive leaves are spawned with `cwd=cfg.root` per the brief's citations —
  so the relative call resolves correctly regardless of whether a session's Bash
  tool sees `CLAUDE_PROJECT_DIR`. No new dependency on that variable was introduced.
- `template/tests/test_slash_commands.py` — new file, doesn't duplicate any
  existing lint (checked: no prior `simple_expansion`/shell-expansion check
  anywhere else in the tree). It doesn't literally reuse `test_handoff.py`'s
  `_first` dual-home helper, but it doesn't need to: it enumerates every file
  under `.claude/commands/` by iterdir rather than hardcoding a `.jinja` vs
  rendered filename, so it already runs unchanged in both a template checkout
  and a rendered instance. That's a reasonable, arguably simpler substitute for
  copying `_first`, not a gap.
- Existing pins hold: `test_handoff.py:121-134` (`argument-hint`, "no scan mode",
  `$1`, `handoff_guard.py` named) all still match the new line 13-16 wording;
  `handoff_guard.py:9-10`'s `--check` description doesn't claim anything about a
  `!` block, so it correctly needed no edit, per the brief's own scope note.
- Minor, non-blocking observation: `BANG_BLOCK` in
  `template/tests/test_slash_commands.py:51` only matches a `!` block that is a
  single line ending in a backtick (`^!\`(.*)\`\s*$`). A hypothetical future `!`
  block with trailing text after the closing backtick, or a multi-line form,
  would silently not match and so not be checked. Today there's exactly one
  command file and its shape is what the regex expects, so this isn't a live bug
  — just a limit worth knowing if `/abandon` (#404) or later commands use a
  different `!` block shape.

No reuse/efficiency issue and no correctness bug introduced by this patch.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decide whether the independently reproduced static red→green discharges the explicitly human-judged C4 exception — the frozen gate exits 77 and does not verify interactive execution (`brief.md:34`, `gate-logs/C4-verify.log:10`, `reviewer-rerun.log:25`, `reviewer-rerun.log:51`).
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by both affected paths — the brief records a command/hook search, but the new test path is absent from that evidence and this isolated target exposes only a synthetic base commit and no remote (`brief.md:94`, `reviewer-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Confirm that a live interactive Claude Code leaf actually issues the Bash check and relays its verdict — that external session was not exercised, so static scans and Python tests cannot establish restored user behavior (`brief.md:81`, `target/template/.claude/commands/handoff.md.jinja:16`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- [x] C5 added test exercises production, not a copy unverifiable — test file(s) add no import of the production package 'pdca_harness' — may exercise a copy, not production: template/test

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
