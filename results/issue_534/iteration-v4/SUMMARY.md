# Result — issue 534 / handoff-contract-checked-at-reap-not-turn-end

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `template/.claude/settings.json:60-71` registers `handoff_guard.py` as a Claude
  Code **Stop** hook. Stop fires every time the main agent finishes a turn, not when the
  session ends. `_stop_verdict()` (`template/.claude/hooks/handoff_guard.py:48-73`) exits 2
  while the leaf's contract is undischarged, and on exit 2 Claude Code sends the hook's stderr
  back to the model instead of handing the turn to the human (the hook's own docstring says
  so at `handoff_guard.py:14-15`). An interactive leaf that asks the human a question therefore
  never reaches the human. The model gets the guard's text, answers it, ends another turn, and
  is blocked again. Nothing bounds the repeat: the envelope is parsed and thrown away
  (`handoff_guard.py:53`). Observed: a sign-off session blocked twelve turns in a row. The
  pressure on the model is to write the artifact the guard demands, and for sign-off that
  artifact is `signoff-decision`, the human's own decision. The hook is live for every
  interactive leaf with a contract (planner, signoff, publisher, act: `handoff.py:70-78`).
- Success criterion: all of the following, shown by the named test at C4:
  (a) **No turn end is intercepted.** The rendered template registers no hook on the Stop
      event, and `handoff_guard.py` run the way the old registration ran it (no arguments, a
      Stop-event JSON envelope on stdin, `PDCA_HANDOFF_ROLE` and `PDCA_HANDOFF_STATE` set, and
      the registered bundle's contract **undischarged**) exits 0 and writes nothing to stderr.
      So an instance whose `settings.json` still carries the old registration (e.g. a
      `copier update` merge that kept it) cannot deadlock either.
  (b) **The contract is reported at reap.** When the `handoff.session(...)` context the driver
      wraps around an interactive leaf exits with the contract undischarged, the problems
      `stop_problems()` finds are printed to **stderr**, naming the role and each bundle
      (e.g. a sign-off bundle with no `signoff-decision`; a signoff `iterate-do` with no
      rationale; a planner brief with an empty Success criterion). A discharged contract
      prints nothing. A recorded `--abandon` reason is still reported as it is today
      (`handoff.py:307-310`), in place of the problem list.
  (c) **Report only.** The reap check writes nothing into any bundle, deletes or moves no
      artifact, raises nothing, and a failure inside the check (e.g. an unreadable config)
      degrades to a one-line stderr note, never an exception out of the context manager
      (the existing rule at `handoff.py:273`: the contract must never break the leaf it checks).
  (d) `/handoff <id>` (`handoff_guard.py --check`) and `--abandon` keep working unchanged as
      the model's self-check and the typed-abandon channel.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: remove turn-end enforcement of the interactive leaves' exit contract and move
  the check to the session boundary, as stated in the criterion. Files in reach:
  `template/.claude/settings.json` (the Stop registration),
  `template/.claude/hooks/handoff_guard.py` (Stop mode; docstring),
  `template/src/pdca_harness/handoff.py` (`session()` reap; module/function docstrings that
  describe a Stop hook), and the text that promises Stop-hook enforcement to the model or the
  operator: `leaves.py` prompt strings in `_plan_prompt` (`:1035`), `_plan_batch_prompt`
  (`:1293`, `:1310`) and `_signoff_prompt` (`:3438`), the comments in `run_signoff` (`:3414`)
  and `run_publish` (`:3628`), `template/.claude/commands/handoff.md.jinja:17-19`, and
  `docs/01-render-and-integrate.md:178-181`. Prompts should now say `/handoff` is the
  self-check and the driver reports an unmet contract when the session ends. Updating
  `template/tests/test_handoff.py` to match is **in scope and expected**:
  `test_stop_hook_ships_and_is_registered` (`:133-141`) asserts the registration this fix
  removes and must be inverted, and the module docstring's item (b) (`:10-11`) rewritten. The
  `StopVerdict` tests (`:331-362`) test `stop_problems()`, which stays, and must keep passing.
  / out of scope: `do_plan`, `do_plan_batch`, `run_plan_advisory_batch` in `leaves.py` (see
  Ordering note); reopening a session or changing any flow/state transition on an unmet
  contract; renaming `stop_problems`; the per-role contract checks themselves
  (`check_planner` / `check_signoff` / `check_publisher` / `check_act`); #508 (`/handoff`
  cannot run in a rendered instance) and #528 (Act vs `/handoff`); #492 `/interview`; this
  instance's own copy of the hook (it changes at the next `copier update`).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

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

Review issue #534: let interactive leaves hand each turn back to the human, then report unmet handoff contracts when the session ends, including after abandonment.

Source paths below are relative to `$PDCA_TARGET` (`/tmp/pdca-review-2xdfke1q/target`); evidence paths are relative to this review directory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The observable turn-end, reap-report, and report-only requirements are testable; Iteration 3 explicitly supersedes the original abandon-suppresses-problems requirement (`template/tests/test_handoff_reap.py:309`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the tracked fix produced 27 assertion failures across 22 tests, including a real hook process returning 2 for a live unmet contract (`template/tests/test_handoff_reap.py:209`; `review-red.log`). |
| C3 Change | PASS | Unmet artifacts remain visible after abandonment, and a broken bundle no longer hides its peers; the excluded planner functions remain unchanged (`template/src/pdca_harness/handoff.py:365`, `template/src/pdca_harness/handoff.py:470`). |
| C4 Verification (red→green) | PASS | Restoring the same fix made all 57 handoff tests pass, covering the subprocess protocol, malformed artifacts, abandon reporting, and unchanged bundle contents (`template/tests/test_handoff_reap.py:365`; `review-green.log:3`). |
| C5 Causal adequacy | PASS | Removing turn-end enforcement eliminates the feedback loop itself; no optional-capability probe masks a load-time cause, and tests exercise production checks (`template/.claude/hooks/handoff_guard.py:77`, `template/tests/test_handoff_reap.py:181`). |
| T1 Structure | PASS | The existing session boundary owns the report and reuses the existing contract dispatcher, with per-bundle error isolation and no new flow/state transition (`template/src/pdca_harness/handoff.py:342`, `template/src/pdca_harness/handoff.py:473`). |
| T2 Shape | PASS | Independent whitespace, docs-lint, and 22-page render/link checks passed; operator guidance now describes the report-only boundary (`docs/01-render-and-integrate.md:178`; `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver discovery completed 1,810 tests with two skips; frozen evidence records 24 passing root render/update tests, which this interpreter could not rerun because Copier is not importable (`review-suite.log:1109`; `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are deliberately not drafted yet; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Affected-path review of all 233 closed PRs found the original handoff implementation in merged PR #398 and no closed-unmerged overlap; the patch addresses that implementation within the agreed report-only scope (`template/src/pdca_harness/handoff.py:347`; `review-closed-prs.json`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether session-end terminal reports give operators sufficient visibility into malformed or unfinished work while preserving their control of each turn; automated protocol and artifact checks cannot settle that workflow judgment (`docs/01-render-and-integrate.md:178`). |

## Independent evidence and limits

- **Red→green:** used `git stash push` in the disposable target, retaining the new regression test, then ran `PYTHONPATH=target/template/src python3 -m unittest discover -s target/template/tests -p test_handoff_reap.py`. The old command returned 2 with the missing-decision message, rather than taking the unavailable-config escape. After `git stash pop`, discovery with `-p 'test_handoff*.py'` passed. Temporary test files were confined through `TMPDIR` inside this review directory. The supplied patch still passes `git apply --reverse --check`; no implementation edits were made.
- **Other reruns:** the full offline driver suite, `docs/publishing/tools/lint_docs.py`, `docs/publishing/tools/render_site.py --check`, and `template/scripts/checks/test_exercises_production.py` all passed. The scanner confirmed the added test imports `pdca_harness`.
- **Copier host caveat:** the local root-suite attempt truthfully reported `PDCA-UNVERIFIABLE` (`review-root-suite.log`). The frozen T3 log explicitly shows both render tests and all five update-compatibility tests executing successfully, followed by `Ran 24 tests` and `OK` (`gate-logs/T3-suite.log:38`). Thus this is a local rerun limitation, not an undischarged gate dependency or patch defect. The instance-scoped gate wrappers were adjudicated using their captured logs and available underlying commands.
- **Prior art:** GitHub's commits API for `template/.claude/hooks/handoff_guard.py` returned its introduction, `900d638` (`review-prior-art.log`). Enumerating all 233 closed PRs and intersecting their changed-file paths with every path in this patch found merged [PR #398](https://github.com/eduralph/pdca-harness/pull/398), no overlapping closed-unmerged PR, and no file-list truncation. The disposable target itself contains only its synthetic base commit, so local history alone would not establish this.
- **Scope and human-only items:** the three explicitly excluded planner functions have identical ASTs before and after the patch; their known stale comments remain excluded by the brief. The integration template's human-only list is still a placeholder (`template/docs/INTEGRATION.md.jinja:80`), supplying no additional enumerated decision. No new patch defect was found; fitness-to-purpose remains for sign-off.

### Advisory — adversary

# Adversarial review: issue 534, iteration 4

**Result: I could not refute the fix.** The red→green proof holds, the tests run the real
code, and I found no input that makes the reap block a turn, write to a bundle, or raise out
of `handoff.session`. Below are two gaps for a human to judge (both low impact), two
low-priority notes, and the attacks that failed.

## For a human to judge

- NEEDS-HUMAN — **The docs promise more than the reap checks on the CSV-batch planner path.**
  `docs/01-render-and-integrate.md:177-180` (new text in this diff) says the end-of-session
  check means "a session can't close silently with a bad artifact". On the CSV/default
  planner path the driver registers no bundles, so `stop_problems` returns `[]` as soon as
  any `/handoff` has passed (`template/src/pdca_harness/handoff.py:478-479`) and never
  re-checks the briefs. Concrete case, run against the patched tree: the session passes
  `/handoff issue_7`, then writes `issue_8/brief.md` with an empty Success criterion and
  never checks it. `check_planner(issue_8)` reports the empty field, but the reap prints
  **nothing**. An empty Success criterion is exactly the case the brief says nothing
  downstream catches. The gap predates this diff (the old Stop hook used the same
  `stop_problems`), so this is not a regression. But the diff restates the promise, and the
  `report_at_reap` docstring (`handoff.py:360-363`) makes the same claim. There are two ways
  to fix it: make the docs sentence say "every bundle the driver registered", or, as a
  follow-up, re-check the briefs the session added. The driver already works out that list
  in `_warn_unseeded_briefs`, but that code is in `do_plan_batch`, which is out of scope
  here (issue 480).
- NEEDS-HUMAN — **An abandon reason with a terminal escape code can hide the list that
  follows it.** `report_at_reap` prints the reason raw (`handoff.py:368-369`) and then the
  problem list. Concrete case, run against the patched tree:
  `record_abandon(state, "out of time\x1b[8m")` produces
  `'…deliberately abandoned — out of time\x1b[8m\nhandoff: the signoff session ended with…'`.
  `ESC[8m` is the "concealed text" mode, so on most terminals the problem list and any
  driver output after it print invisibly. That breaks the promise this diff adds, "an
  abandon never hides what is missing" (`docs/01-render-and-integrate.md:184-185`,
  `handoff.py:264-268`). The leaf can also write any `abandoned` value straight into its
  scratch file. The odds are low: it takes a leaf doing this on purpose, and the leaf never
  sees the reap output, so nothing pushes it to. Printing the reason raw predates this diff.
  What is new is that the list now comes after the reason. The fix is small: escape
  non-printable characters in the reason before printing it. The human's call is whether a
  leaf that hides the report on purpose is in scope.

## Low-priority notes (not refutations)

- Reading the doctor table early (`handoff.py:462-468`) turns a malformed
  `[[doctor.checks]]` table (for example `[doctor] checks = ["protoc"]`) into the one line
  "could not check the planner session's exit contract … — nothing reported". That happens
  even for an id-seeded batch where every issue was legitimately left UNPLANNED, where each
  bundle's own `check_planner` would pass (I ran this). It also hides "brief.md is missing"
  and "unfilled template copy" findings, but the driver catches both later (`flow.py`,
  `state` treats a placeholder brief as UNPLANNED). Nothing only the reap can catch is lost,
  and a broken table is worth reporting anyway. This matches the human's iteration-3 wish
  to keep config-wide failures to one line.
- Two more driver-suite tests print the reap report to the real stderr:
  `template/tests/test_state_resolved.py:191` and `:217` (visible in
  `gate-logs/T3-suite.log:1043-1050`). This is the same kind of noise as iteration 3's item
  2, which silenced `test_handoff.py` and `test_publish_slice.py`. Each needs one
  `redirect_stderr(io.StringIO())` wrapper. Worth folding in only if there is another
  iteration anyway.

## Attacks that did not land

- **Red→green evidence.** I re-ran both legs in a sandbox copy of `$PDCA_TARGET`. On the
  patched tree, 57/57 pass (`tests.test_handoff_reap`, `tests.test_handoff`). With
  `settings.json`, `handoff_guard.py`, `handoff.py` and `leaves.py` put back to HEAD, 29
  fail, the same 2 + 27 as `gate-logs/C4-verify.log:108-371`. The (a) red leg is not the
  false green the brief warned about: `template/tests/test_handoff_reap.py:189` first proves
  the contract check is live (`--check` → 1 in the same environment), and the pre-fix hook
  then returns 2 with "may not end yet" (`C4-verify.log:113-133`). The subprocess variant
  (`test_handoff_reap.py:210-236`) loads its own `pdca.toml` and does not rely on the
  `_bootstrap` patch.
- **Production path.** The tests load the real hook file from `template/.claude/hooks/` and
  the real `pdca_harness.handoff`. There is no mirror copy.
- **Making the reap raise.** `report_at_reap` catches `Exception` around both the reason
  print and `stop_problems` (`handoff.py:365-374`). Each bundle check is isolated
  (`:472-475`), and the leaf's own exception passes through unchanged (tested). The only
  ways out are `BaseException` (Ctrl-C during a slow detect command) or the final `print`
  failing on a closed stderr. Neither is realistic.
- **Making the reap write.** The sign-off, publisher and act checks are pure reads. Planner
  detect commands (`doctor.py:312`, no timeout) are the only side channel, and
  `plan_policy` already runs them after Plan (`driver.py:56`).
- **Other turn-end hooks.** Nothing is registered on Stop or SubagentStop in
  `settings.json`, and the agent frontmatter only registers PreToolUse (`builder_guard.py`)
  for builder and publisher.
- **The new "unknown mode → exit 2" branch** (`handoff_guard.py:73-76`) would only bring
  back a turn-end block for a Stop registration that passes an argument. The retired
  registration passed none, and no caller passes anything other than `--check` or
  `--abandon`.
- **Leftover promises of Stop-hook enforcement.** None remain in prompts, agent bodies,
  `/handoff`, or the docs, apart from the comments this bundle was told to leave alone
  (`leaves.py:916-917`, `:1106-1108`).
- **Blank abandon values, a non-UTF-8 decision file, a directory in a file's place, a leaf
  that rewrites its scratch file, an abandon plus a problem list:** all are covered by
  tests that go red before the fix.

### Advisory — code-review

# Advisory code review — issue #534

Second-lens read of the diff (introduced-bug and reuse/efficiency lens), grounded on
the target checkout. The main mechanism — drop the Stop registration, make the hook's
no-arg path inert, judge the contract at `handoff.session`'s reap via
`report_at_reap`/`stop_problems`, abandon reason printed before (not instead of) the
problem list, per-bundle error isolation — reads correctly and matches the three
carry-forward fixes from prior iterations (blank-abandon handling in
`_abandon_reason`, per-bundle `try/except` in the loop, abandon no longer suppressing
the list). One finding below is a real gap the patch introduces; the rest are minor.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/handoff.py:462-468` (target,
  `stop_problems`): for a planner session, the shared `_doctor.registered_ids(cfg)`
  pre-check runs unconditionally whenever `bundles` is non-empty, before the
  per-bundle loop — even when every bundle in the batch is legitimately unplanned
  (`allow_absent=True`, no `brief.md` written at all). In that case `check_planner`
  itself never touches the `doctor` module (it returns `[]` at the `if not bp.exists()`
  guard, `handoff.py:112-115`), so the shared pre-check is consulting an input none of
  the bundles actually need. If `pdca.toml`'s `[[doctor.checks]]` table happens to be
  malformed for a reason unrelated to this session, a batch-planner reap that would
  otherwise print nothing (every id correctly left unplanned) instead prints "could not
  check the planner session's exit contract (...) — nothing reported" — a false alarm
  at a report-only checkpoint, on the exact "leave it UNPLANNED" path the brief calls
  out as a legitimate outcome. This is new code (the pre-check didn't exist before this
  iteration's per-bundle-isolation fix); worth gating it behind "does any bundle in
  this batch actually have an authored `brief.md`" before spending the shared read, or
  moving it back inside the per-bundle `try` so an unrelated broken table only ever
  produces a per-bundle note. Not covered by any test in `test_handoff_reap.py` — the
  existing broken-config tests all use briefed bundles
  (`test_a_broken_config_is_one_line_for_the_whole_batch`).

- `template/src/pdca_harness/handoff.py:462-468` and `check_planner`
  (`handoff.py:99-129`): minor duplicate work, not a bug. The shared
  `_doctor.registered_ids(cfg)` call's result is discarded — it exists only to raise
  early — and every bundle in the loop still re-parses `pdca.toml` on its own via
  `check_planner` → `_doctor.unregistered_dependencies` (→ `registered_ids`) and
  `_doctor.failing_dependencies` (→ `current_doctor_checks`). So a planner reap over N
  bundles parses `pdca.toml` up to `1 + 2N` times instead of once. This only runs once
  per session's reap and the file is small, so it's not worth blocking on — flagging
  for awareness, not a fix demand.

No other correctness bugs found: the `session()` finally-block merge
(`{**_read_json(path), **registered}`, `handoff.py:342`) correctly re-asserts the
driver-registered `bundles`/`role`/`require_artifact`/`baseline` over whatever the leaf
wrote to its own scratch file while preserving `passed`/`abandoned`, matching the
"report the bundles the driver actually registered" test. `report_at_reap`'s own
`try/except` correctly prints an already-emitted abandon reason before the one-line
"could not check" note on a shared-check failure. The hook's no-argument path never
touches stdin and exits 0 unconditionally, satisfying the turn-end criterion regardless
of `PDCA_HANDOFF_ROLE`. The `test_publish_slice.py` edit that adds `redirect_stderr`
around `run_publish` is correctly scoped (that file already imports `io` and
`redirect_stderr`) and is the only pre-existing test call site this patch's new
reap-report chattiness required touching — the other `handoff.session`-driving test
file, `test_leaf_workspace_admission.py`, already wraps every leaf spawn in its own
`_quiet()` helper, so it needed no change.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether session-end terminal reports give operators sufficient visibility into malformed or unfinished work while preserving their control of each turn; automated protocol and artifact checks cannot settle that workflow judgment (`docs/01-render-and-integrate.md:178`).
- [ ] **The docs promise more than the reap checks on the CSV-batch planner path.**
- [ ] **An abandon reason with a terminal escape code can hide the list that
- [ ] `template/src/pdca_harness/handoff.py:462-468` (target,
- [ ] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): The size backstop tripped: three rounds already spent (threshold 3), so this goes back to Plan instead of another rebuild. Keep the approach as is: no Stop registration, the no-argument hook path inert, a report-only check at reap, one shared `_abandon_reason` test, per-bundle error isolation, and the abandon reason printed before (not instead of) the problem list. In the re-plan, decide for each remaining round-4 finding whether it becomes its own issue or a small fold-in to this slice: 1. `handoff.py:462-468`: the shared `[[doctor.checks]]` pre-read in `stop_problems` gives a "could not check" false alarm on a planner batch where every issue was correctly left UNPLANNED. Either read it only when some bundle has a `brief.md`, or move it inside the per-bundle `try`. Add a test. 2. `handoff.py:368-369`: escape non-printable characters in the abandon reason before printing it, so a terminal escape code cannot hide the problem list that follows. 3. `docs/01-render-and-integrate.md:177-180` and the `report_at_reap` docstring (`handoff.py:360-363`) promise more than the code does on the CSV-batch planner path: `stop_problems` returns [] once any `/handoff` has passed (`handoff.py:478-479`). Reword to "every bundle the driver registered". Re-checking the briefs the session added belongs in `do_plan_batch` (issue 480). 4. `test_state_resolved.py:191` and `:217` print the reap report to the real stderr. Wrap each in `redirect_stderr(io.StringIO())`.
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
