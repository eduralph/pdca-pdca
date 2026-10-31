# Result — issue 781 / diff-files-git-quoted-paths

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: 
  - (a) A real-git patch (made with `git -c core.quotePath=true diff` in a temp repo —
    pinned, so a machine with `core.quotePath=false` in its global config cannot make
    this leg green on `main`) that edits `café.txt` → `diff_files` returns `{"café.txt"}`.
  - (b) Paths with a double quote, a backslash and a tab in the name each come back
    decoded.
  - (c) A rename between a quoted and an unquoted name returns both names.
  - (d) Unquoted headers, `/dev/null` sides and a missing file behave as today (existing
    `template/tests/test_waves.py` stays green, and so does
    `template/tests/test_size_calibrate.py`, e.g. `test_diff_files_are_counted` at
    :339-343).
  - (e) `_audit_wave_overlap` reports an overlap for two bundles whose patches both edit
    `café.txt` (drive it as the existing overlap-audit tests do). Red on `main`.
  - (f) A malformed quoted header never raises: a bad escape (e.g. a lone `\3`, `\q`),
    an unterminated quote, and octal bytes that are not valid UTF-8 each return without
    an exception (the path is skipped or decoded with replacement — Do's choice, stated in
    the docstring). `_audit_wave_overlap` has no guard, so a raise here would turn an
    advisory miss into a flow crash. Green on `main` (the regex just skips the line);
    guards against a careless helper.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

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

Fix `waves.diff_files` dropping Git C-quoted paths, which hides same-wave overlaps and undercounts changed files.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief specifies observable real-Git results, compatibility boundaries, and malformed-input behavior; these match the shared reader and its consumers (`template/src/pdca_harness/waves.py:476`, `template/src/pdca_harness/flow.py:1592`, `template/src/pdca_harness/size_signal.py:406`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production fix reproduced 9 failures among 13 tests, including the missing café.txt overlap warning (`template/tests/test_waves_quoted_paths.py:86`, `template/tests/test_waves_quoted_paths.py:172`; `review-red-green.log:6`). |
| C3 Change | PASS | The patch stays within the specified header parser, its documentation, and production-facing regression tests; restored target blob hashes match the diff (`template/src/pdca_harness/waves.py:413`, `template/tests/test_waves_quoted_paths.py:22`). |
| C4 Verification (red→green) | PASS | After stash pop, all 160 quoted-path, wave, size-calibration, and size-signal tests passed; independent results reproduce the frozen red→green evidence (`review-red-green.log:136`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | Real-Git assertions cover decoded identity, mixed renames, shared and distinct paths, and malformed-header isolation; the earlier weak assertion is now exact, and no capability-probe symptom guard was introduced (`template/tests/test_waves_quoted_paths.py:116`, `template/tests/test_waves_quoted_paths.py:167`, `template/tests/test_waves_quoted_paths.py:206`). |
| T1 Structure | PASS | Two private parsing helpers preserve the shared reader's public contract and avoid duplicating logic in its consumers (`template/src/pdca_harness/waves.py:413`, `template/src/pdca_harness/waves.py:442`, `template/src/pdca_harness/waves.py:495`). |
| T2 Shape | PASS | Independent whitespace, docs lint, 22-page render/link audit, six checker tests, relative-link scan, and ADR-index checks passed; frozen docs and host-parity logs also show clean runs (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The independent relevant suite passed 160 tests; frozen full-suite output records 50 root tests passing and 2660 driver tests passing with two skips (`review-red-green.log:145`, `gate-logs/T3-suite.log:80`, `gate-logs/T3-suite.log:1902`). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the recorded deferred gate requires the substantive contribution audit at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged history and closed/rejected work by both affected file paths before accepting this as new work — the local path-scoped history search yields only one synthetic base commit, with no remotes; the brief's provenance does not establish that wider check (`template/src/pdca_harness/waves.py:405`, `template/tests/test_waves_quoted_paths.py:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the corrected overlap coverage and higher file counts for the intended repository workflows, including the documented replacement decoding of non-UTF-8 names — threshold effects and acceptable path identity require maintainer judgment (`template/src/pdca_harness/flow.py:1597`, `template/src/pdca_harness/size_signal.py:406`, `template/src/pdca_harness/waves.py:483`). |

Source citations resolve under `$PDCA_TARGET` (`target/`). The target was readable, the patch was present, and both changed files matched their patch blob hashes after restoration. The stash was restored and no reviewer source edits remain.

Independent reproduction used `git stash push -- template/src/pdca_harness/waves.py`, then `PYTHONPATH=src python3 -m unittest tests.test_waves_quoted_paths` from `target/template`; after `git stash pop`, the same command included `tests.test_waves`, `tests.test_size_calibrate`, and `tests.test_size_signal`. Full captured output is in `review-red-green.log`. All 13 new tests ran without skips, using real Git; no external dependency remained unmet for these criteria.

The instance-scoped gate wrappers were not available in this target. Their frozen logs were read for C4, C5, T2, host CI parity, T3, and T4. The full root/driver suite was adjudicated from `gate-logs/T3-suite.log`, rather than claimed as independently rerun. The production-import check was independently confirmed from the test AST (`template/tests/test_waves_quoted_paths.py:22`). Independent docs checks reported 458 relative links across 67 Markdown files with zero broken links, and 12 ADRs with zero problems.

Prior-art investigation ran `git log --all -- template/src/pdca_harness/waves.py template/tests/test_waves_quoted_paths.py`, `git rev-list --all --count`, and `git remote -v`: one synthetic pre-fix commit, count 1, no remotes. Merged-history and closed/rejected-work coverage therefore remain unestablished. The available integration template enumerates no additional concrete human-only checks (`template/docs/INTEGRATION.md.jinja:80`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — diff-files-git-quoted-paths

No correctness bugs found, and no cleanup that needs a human. The notes below are minor and informational. None is tagged NEEDS-HUMAN.

**Correctness.** I traced `_unquote_c` (`template/src/pdca_harness/waves.py:413`) and `_header_paths` (`template/src/pdca_harness/waves.py:442`) against every malformed line in the new test and against real Git output. A backslash at the end of the string, a short octal escape, an octal value above 0o377, a missing closing quote, trailing text, a wrong `a/`/`b/` prefix and an empty path all return `None` or `[]`. None of them raises, so the unguarded caller `_audit_wave_overlap` (`template/src/pdca_harness/flow.py:1592`) cannot crash on patch content. Headers with no quote still go through the old regex unchanged (`waves.py:455-457`), so `test_waves.py` and `test_size_calibrate.py` behave as before. The mixed-header split at `waves.py:464` (`partition(' "')`) is safe because Git always quotes a plain name that contains `"`, so the first ` "` must be where the quoted side starts. The round-1 finding is fixed: leg (f) now asserts `set()` for each malformed header, and asserts that the next header still parses. Leg (c) and the space-in-name case are pinned with real `git` output. The gate log shows the non-UTF-8 test ran rather than skipped (`gate-logs/C4-verify.log:13-15`, `OK` with no skip count).

- `template/src/pdca_harness/waves.py:464` — In a mixed header, the plain side is not passed through `.strip()`, but the all-plain path is (`waves.py:457`). This only matters for a hand-made header with stray whitespace. Git never writes one, and `splitlines()` already removes `\r`. No action needed.
- `template/src/pdca_harness/waves.py:455-458` — Small simplification: `rest.startswith('"')` is checked twice, and `_DIFF_GIT_RE` repeats the `diff --git ` prefix that `_DIFF_GIT` (`waves.py:406`) now holds. The code is clear as it is, so this is optional.
- Reuse, out of scope for this patch: two other parsers still use the plain `^diff --git a/(.+) b/(.+)$` regex and will skip Git-quoted paths in the same way. They are `template/src/pdca_harness/registry.py:23` and `template/scripts/checks/test_exercises_production.py:27`. The brief limits the fix to `waves.py`, so this is not a defect in this diff. A later issue could have both call `waves._header_paths`, or a shared public helper.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged history and closed/rejected work by both affected file paths before accepting this as new work — the local path-scoped history search yields only one synthetic base commit, with no remotes; the brief's provenance does not establish that wider check (`template/src/pdca_harness/waves.py:405`, `template/tests/test_waves_quoted_paths.py:1`).
- [x] Validation — fitness-to-purpose — Accept the corrected overlap coverage and higher file counts for the intended repository workflows, including the documented replacement decoding of non-UTF-8 names — threshold effects and acceptable path identity require maintainer judgment (`template/src/pdca_harness/flow.py:1597`, `template/src/pdca_harness/size_signal.py:406`, `template/src/pdca_harness/waves.py:483`).
- [x] **The tracker record is missing.** The cwd has only `brief.md`; there is no `notes.json`, `sources/` or `dependency-state.json`. So I could not check the problem statement or the "Prior-art check" line (`results/issue_395/iteration-v9/brief.md:127`, a sign-off finding on #395 iteration 8) against any thread. The brief's origin and the claim "No earlier fix on `main`" are unverified. A human should confirm the #395 sign-off finding exists and says what the brief says it says.
- [x] **"The only caller today is the advisory `_audit_wave_overlap`" is false.** `waves.diff_files` also feeds the size backstop: `template/src/pdca_harness/size_signal.py:406` (`patch_files = len(waves.diff_files(patch))`, with a docstring at :390-392 saying the backstop and the scheduler must agree on this count) and `template/scripts/size-calibrate:344` (`patch_files=len(waves.diff_files(patch))`). The fix will therefore also raise `patch_files` for any bundle that touches a quoted path, which changes a size signal and calibration rows. That is probably the right outcome, but it is a behaviour change the brief neither scopes nor tests. The brief should list these callers. Criterion (d) should also name `template/tests/test_size_calibrate.py` (e.g. `test_diff_files_are_counted`, :339-343) as a test that must stay green.
- [x] **No criterion that the unquote helper never raises.** `size_signal.measure` wraps the call in `except (OSError, UnicodeDecodeError, ValueError)` (`size_signal.py:405-410`), but `_audit_wave_overlap` has no guard (`flow.py:1592`). If the new helper raises on a malformed or truncated escape, for example `bytes.decode` on a lone `\3` or an invalid UTF-8 octal sequence, the advisory audit turns into a crash in the flow. Today it only misses the path. Add a criterion: a malformed quoted header (bad escape, unterminated quote, octal bytes that are not valid UTF-8) does not raise, and is either skipped or decoded with replacement.
- [x] **The mixed-header claim doesn't match the code.** The brief says (line 8) that "a mixed header (one side quoted) yields a path with a stray quote". For `diff --git a/plain.txt "b/café…"`, the regex requires a literal ` b/`, but the line has ` "b/`. For `diff --git "a/…" b/plain.txt`, the line has no `^diff --git a/` prefix. Both forms fail to match, so both paths are dropped; no stray-quote path comes out. Criterion (c) is still RED on `main` either way, so this only corrects the framing. But Do should not write a test asserting today's "stray quote" behaviour as the baseline.
- [x] **The dependence on git config is unstated.** Criterion (a) relies on the default `core.quotePath=true` in the temp repo. A developer or CI machine with `core.quotePath=false` in global config would write `café.txt` unquoted, and (a) would pass on `main`, which breaks the "RED on `main`" claim. The test should pin the setting with `git -c core.quotePath=true diff`. If it does not, it should at least include a case that git always quotes (`"`, `\`, tab), which criterion (b) covers. Nothing in the target source sets `quotePath` (Grep found no matches), so harness-produced patches follow whatever the user's git config says.
- [x] T5 Judgment — Confirm merged-history and closed/rejected-work searches by both affected file paths — the local search exposes only a synthetic base commit and no remote, while the brief supplies provenance rather than those searches, leaving duplicate or previously rejected work unresolved (`review-evidence/prior-art.log:1`, `brief.md:63`).
- [x] Reuse and a follow-up scope question. Two other copies of the old plain regex keep the same quoted-path bug and do not use the new helper:

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
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Follow-up: the same Git-quoted-path bug remains in `template/src/pdca_harness/registry.py:23` and `template/scripts/checks/test_exercises_production.py:27` (old plain `diff --git a/(.+) b/(.+)` regex); file an issue to have them use `waves._header_paths` or a shared public helper.
