# Result — issue 376 / install-path-symlink

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `make install` (i.e. `template/scripts/bootstrap-tools.sh`) exposes the
  installed console script on PATH: idempotently symlink `.venv/bin/<cli_name>` →
  `~/.local/bin/<cli_name>` when `~/.local/bin` exists and is on PATH, reported as one
  `OK|INSTALLED` row; a WARN naming the exact `ln -s` command when `~/.local/bin` is
  absent or off PATH (never guessing at shell profiles); `--check`
  (`make install-check`) reports the row without creating anything. Closes the gap
  where every instance operator invents the last hop themselves — and where the
  shipped T4 gate row (`{{ cli_name }} contribcheck`, `template/pdca.toml.jinja:850`)
  spawns the CLI by bare name via /bin/sh and fails command-not-found on a fresh
  render + `make install` (the pdca-pdca instance hit exactly this on its first
  offline cycle).
- Success criterion: tests appended to `template/tests/test_bootstrap.py` go
  red→green against the script alone (the existing `_run_check`-style sandbox — temp
  root, synthetic `pdca.toml`/`pyproject.toml`, faked `HOME` and `PATH` passed via the
  subprocess env): (a) an install-mode run with a pre-seeded fake `.venv/bin` (stub
  `pip` + a `<cli>` script file) and a faked `HOME` whose `.local/bin` exists and is
  on the injected PATH creates the symlink `~/.local/bin/<cli>` → `.venv/bin/<cli>`
  and prints its row; (b) `--check` in the same setup reports the row and creates no
  symlink; (c) `HOME` without `.local/bin` (or with it off PATH) → WARN containing the
  exact `ln -s` command and no symlink created; (d) a re-run with the symlink already
  in place reports OK and changes nothing (idempotent); (e) an existing
  `~/.local/bin/<cli>` pointing somewhere OTHER than this venv is left untouched and
  WARNed about, never clobbered. Assert on stdout rows and the filesystem, not on the
  script's exit code (a sandbox host may legitimately lack `gh`, which is an unrelated
  required-miss).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: one logical change to `template/scripts/bootstrap-tools.sh` (a PATH-link
  step in the console-script section) + the appended tests. / out of scope: editing
  `template/Makefile` (its closing message stays name-agnostic; the new row is the
  communication), shell-profile mutation of any kind (the WARN prints the command,
  per the issue), Windows (`scripts/install.ps1` — separate surface), the root-level
  render suites (the offline driver suite is the home for this test), and changing
  the T4 gate row itself (its bare-name spawn is by design once the script is on PATH).

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
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpdkbggklh/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #376: make the installed project console script discoverable on PATH through a safe, idempotent `~/.local/bin` symlink step.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The specified install, check-only, off-PATH, idempotency, and no-clobber outcomes are explicit and independently observable in the production branches and focused cases (`template/scripts/bootstrap-tools.sh:119`, `template/tests/test_bootstrap.py:160`). |
| C2 Reproduction (red pre-fix) | PASS | With the new tests retained and only the production hunk absent, the bootstrap module ran 13 tests with five failures and one error, so the missing PATH-link behavior is a genuine pre-fix red (`template/tests/test_bootstrap.py:160`). |
| C3 Change | PASS | The change stays within the briefed script and test surfaces, derives names from `[project.scripts]`, and confines mutation to an absent or same-venv link (`template/scripts/bootstrap-tools.sh:102`, `template/scripts/bootstrap-tools.sh:131`). |
| C4 Verification (red→green) | PASS | An isolated base-plus-test run was red, then the same 13-test command passed after applying the full patch; the green cases assert both output and filesystem state (`template/tests/test_bootstrap.py:155`, `template/tests/test_bootstrap.py:223`). |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether probing required-base Python and WARN-skipping the link is legitimate degraded-host handling or whether name parsing should be deferred until that dependency is established so the probe is unnecessary — it matters because this path can leave the motivating bare-name gate unresolved (`template/scripts/bootstrap-tools.sh:119`, `template/scripts/bootstrap-tools.sh:121`). |
| T1 Structure | PASS | The parser/link step is localized between console-script installation and tier-2 bootstrap, with its behavioral fixture isolated in one test class (`template/scripts/bootstrap-tools.sh:102`, `template/tests/test_bootstrap.py:104`). |
| T2 Shape | NEEDS-HUMAN | Decide whether to accept the recorded site-render pass or rerun with network/a local `MERMAID_JS` asset — lint and shell/Python syntax passed locally, but the renderer could not complete its Mermaid fetch, so its link audit was not independently reproduced (`docs/publishing/tools/render_site.py:403`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded `/tmp/.../issue_500/split-proposal.md` suite red is unrelated by rerunning with `copier` installed — all 1,314 template tests passed locally, but all six root render/update tests skipped on the explicit missing-`copier` guard (`tests/test_render_and_run.py:23`, `tests/test_render_and_run.py:31`). |
| T4 Contribution | NEEDS-HUMAN | Decide whether the eventual PR body and commit message satisfy user-impact and `#376` policy — those artifacts were not supplied, and the checker is intentionally default-open while the PR body is absent, so the recorded pass cannot be reconstructed (`template/src/pdca_harness/cli.py:1034`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether prior work makes this contribution duplicate or previously rejected — local history-by-both-affected-paths found merged #207 only, but invalid GitHub authentication prevented settling the closed/rejected corpus and the project routine remains TODO (`template/docs/INTEGRATION.md.jinja:83`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the synthetic HOME/PATH fixture represents a fresh rendered operator install — in such an instance, run `make install`, `/bin/sh -c '<cli> contribcheck'`, rerun install, then preseed a foreign `<cli>` and confirm bare-name execution, `OK`, and no clobber respectively (`template/tests/test_bootstrap.py:109`, `template/tests/test_bootstrap.py:198`). |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether probing required-base Python and WARN-skipping the link is legitimate degraded-host handling or whether name parsing should be deferred until that dependency is established so the probe is unnecessary — it matters because this path can leave the motivating bare-name gate unresolved (`template/scripts/bootstrap-tools.sh:119`, `template/scripts/bootstrap-tools.sh:121`).
- [x] T2 Shape — Decide whether to accept the recorded site-render pass or rerun with network/a local `MERMAID_JS` asset — lint and shell/Python syntax passed locally, but the renderer could not complete its Mermaid fetch, so its link audit was not independently reproduced (`docs/publishing/tools/render_site.py:403`).
- [x] T3 Runtime — Decide whether the recorded `/tmp/.../issue_500/split-proposal.md` suite red is unrelated by rerunning with `copier` installed — all 1,314 template tests passed locally, but all six root render/update tests skipped on the explicit missing-`copier` guard (`tests/test_render_and_run.py:23`, `tests/test_render_and_run.py:31`).
- [x] T4 Contribution — Decide whether the eventual PR body and commit message satisfy user-impact and `#376` policy — those artifacts were not supplied, and the checker is intentionally default-open while the PR body is absent, so the recorded pass cannot be reconstructed (`template/src/pdca_harness/cli.py:1034`).
- [x] T5 Judgment — Decide whether prior work makes this contribution duplicate or previously rejected — local history-by-both-affected-paths found merged #207 only, but invalid GitHub authentication prevented settling the closed/rejected corpus and the project routine remains TODO (`template/docs/INTEGRATION.md.jinja:83`).
- [x] Validation — fitness-to-purpose — Decide whether the synthetic HOME/PATH fixture represents a fresh rendered operator install — in such an instance, run `make install`, `/bin/sh -c '<cli> contribcheck'`, rerun install, then preseed a foreign `<cli>` and confirm bare-name execution, `OK`, and no clobber respectively (`template/tests/test_bootstrap.py:109`, `template/tests/test_bootstrap.py:198`).

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
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
