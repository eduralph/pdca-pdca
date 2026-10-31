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

Review the fix for Git C-quoted paths being omitted from `waves.diff_files`, causing missed overlap warnings and understated patch file counts.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable decoding, mixed-rename, compatibility, overlap, and malformed-input outcomes; the shared callers establish the impact (`template/src/pdca_harness/flow.py:1592`, `template/src/pdca_harness/size_signal.py:406`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the patch produced seven assertion failures across ten executed tests, including real-Git quoted paths and the missing overlap warning (`review-evidence/red.log:1`, `template/tests/test_waves_quoted_paths.py:68`, `template/tests/test_waves_quoted_paths.py:137`). |
| C3 Change | PASS | The patch stays within the specified parser/docstring and regression-test scope; the public return contract and advisory consumer remain intact (`template/src/pdca_harness/waves.py:474`, `template/tests/test_waves_quoted_paths.py:22`). |
| C4 Verification (red→green) | PASS | After stash-pop restored the same patch, all ten regression tests passed independently; the frozen verifier likewise records ten green tests and seven pre-fix failures (`review-evidence/green.log:3`, `gate-logs/C4-verify.log:95`, `template/tests/test_waves_quoted_paths.py:73`). |
| C5 Causal adequacy | PASS | Real-Git inputs and the production overlap audit now meet the failing expectations; the parser resolves the header-format mismatch directly, with no capability probe or load-time symptom guard (`template/src/pdca_harness/waves.py:443`, `template/tests/test_waves_quoted_paths.py:148`). |
| T1 Structure | PASS | One shared path parser continues to serve overlap auditing and both size-count consumers, avoiding divergent definitions of touched files (`template/src/pdca_harness/waves.py:492`, `template/src/pdca_harness/size_signal.py:406`, `template/scripts/size-calibrate:344`). |
| T2 Shape | PASS | Independent docs lint, 22-page rendering/link audit, and git diff whitespace checks passed; frozen host-parity evidence supports the same docs checks (`gate-logs/T2-docs.log:15`, `gate-logs/host-ci-docs.log:13`). |
| T3 Runtime | PASS | Independently ran 147 existing waves/size tests successfully; the frozen full-suite log records 50 root tests and 2,657 driver tests passing, with two skips (`gate-logs/T3-suite.log:80`, `gate-logs/T3-suite.log:1902`, `template/tests/test_waves.py:243`). |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; the substantive contribution audit must rerun at publish, as the deferred gate explicitly states (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged-history and closed/rejected-work searches by both affected file paths — the local search exposes only a synthetic base commit and no remote, while the brief supplies provenance rather than those searches, leaving duplicate or previously rejected work unresolved (`review-evidence/prior-art.log:1`, `brief.md:63`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the restored overlap warnings and higher quoted-path file counts as fit for the workflow — automated parsing/audit evidence cannot decide whether these advisory signals meet maintainer needs (`template/src/pdca_harness/flow.py:1599`, `template/src/pdca_harness/size_signal.py:390`). |

The disposable target matched the supplied patch and was restored after the independent red→green run. Only the originally patched production file and new test remain changed there. All review scratch files were kept inside this review directory.

Independent regression command: `TMPDIR=/tmp/pdca-review-m82whij0/review-tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/pdca-review-m82whij0/target/template/src python3 review-evidence/test_waves_quoted_paths.py`, executed against the stashed base, then against the restored production source. The red leg executed ten tests and failed seven assertions; the green leg executed ten and passed. Captured output is in `review-evidence/red.log` and `review-evidence/green.log`.

Independent compatibility command, from `target/template`: `TMPDIR=/tmp/pdca-review-m82whij0/review-tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_waves tests.test_size_calibrate tests.test_size_signal` (147 tests, OK). From `target`, ran `python3 docs/publishing/tools/lint_docs.py`, `python3 docs/publishing/tools/render_site.py --check --out /tmp/pdca-review-m82whij0/review-evidence/site`, and `git diff --check`; all passed.

The instance-scoped gate wrappers were assessed from their frozen logs, not from the target's template skeletons. The full root/driver suites were not independently repeated; their recorded counts and outcomes are identified above. The production-path log reports the new test's production-package import, independently corroborated by running that test against the actual stashed/restored module. Real Git and Python were exercised; no external dependency workaround was needed. The supplied integration template lists project-specific human-only items as TODO, rather than enumerating additional applicable decisions (`template/docs/INTEGRATION.md.jinja:80`).

Prior-art investigation ran `git log --all --oneline -- template/src/pdca_harness/waves.py template/tests/test_waves_quoted_paths.py` and `git remote -v` in the supplied target. Results: one synthetic pre-fix base commit, no remote. No closed/rejected-work search evidence is supplied, so that confirmation remains a human decision, not a patch defect. No implementation defect or contested symptom-versus-root-cause concern was found.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue_781 (diff-files-git-quoted-paths)

Advisory only. Gates: C4 passes (red before the fix, green after); T3 suite passes.

## Correctness

I found no correctness bugs in the patch. I probed `_header_paths` by hand against the
patched `template/src/pdca_harness/waves.py:443-471`:

- Plain headers still go through the old regex and behave as before.
- Quoted sides, mixed renames in both orders, an unquoted old path with a space next to a
  quoted new path, and a trailing `\r` all decode correctly.
- Bad input returns `[]` and never raises. That covers a short octal, `\400`, an unknown
  escape, no closing quote, a lone `"`, a double space between sides, and a tab separator.
- The escape table at `waves.py:409` matches Git's `quote.c`.
- Octal bytes are collected into a `bytearray` and decoded as UTF-8 once at the closing
  quote. That is right for multi-byte names.

## Findings

- NEEDS-HUMAN [impl] — `template/tests/test_waves_quoted_paths.py:130`: leg (f) only checks
  `assertIsInstance(..., set)`. The docstring at `template/src/pdca_harness/waves.py:481-482`
  promises that a malformed quoted header is *skipped*, but the test never checks that.
  Each malformed line in the test resolves to `[]` today, so `assertEqual(waves.diff_files(p),
  set())` would pin the stated behaviour. Without it, a change that returns a half-decoded
  path, such as `"a/x\\q"`, would still pass.
- `template/src/pdca_harness/waves.py:450`: small cleanup. The unquoted branch adds
  `_DIFF_GIT_PREFIX` back onto `rest` just so `_DIFF_GIT_RE` can match it. A
  prefix-free regex (`r"a/(.+) b/(.+)$"`) would avoid building the string twice. Also, the
  unquoted old side in the mixed case (`waves.py:460`) is not `.strip()`ped, while the regex
  branch strips both sides. That is harmless today because Git never writes trailing
  whitespace before the separator. Not blocking.
- NEEDS-HUMAN [human] — Reuse and a follow-up scope question. Two other copies of the old
  plain regex keep the same quoted-path bug and do not use the new helper:
  - `template/src/pdca_harness/registry.py:23` (`touched_paths`). This feeds the
    `registry-check` *gate* (`registry.py:78`, `template/src/pdca_harness/cli.py:477`). A
    patch that edits `café.txt` gets no touched path for that file, so a registry line
    naming it could be flagged wrongly.
  - `template/scripts/checks/test_exercises_production.py:27`. This misses a new test file
    whose name Git quotes.

  The brief scopes the fix to `waves.py`, so this is not a defect in the patch. A human
  should decide whether to file a follow-up that has these callers share
  `waves._header_paths`, or a public version of it.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm merged-history and closed/rejected-work searches by both affected file paths — the local search exposes only a synthetic base commit and no remote, while the brief supplies provenance rather than those searches, leaving duplicate or previously rejected work unresolved (`review-evidence/prior-art.log:1`, `brief.md:63`).
- [ ] Validation — fitness-to-purpose — Accept the restored overlap warnings and higher quoted-path file counts as fit for the workflow — automated parsing/audit evidence cannot decide whether these advisory signals meet maintainer needs (`template/src/pdca_harness/flow.py:1599`, `template/src/pdca_harness/size_signal.py:390`).
- [ ] `template/tests/test_waves_quoted_paths.py:130`: leg (f) only checks `assertIsInstance(..., set)`. The docstring at `template/src/pdca_harness/waves.py:481-482` promises that a malformed quoted header is *skipped*, but the test never checks that. Each malformed line in the test resolves to `[]` today, so `assertEqual(waves.diff_files(p), set())` would pin the stated behaviour. Without it, a change that returns a half-decoded path, such as `"a/x\\q"`, would still pass.
- [ ] Reuse and a follow-up scope question. Two other copies of the old plain regex keep the same quoted-path bug and do not use the new helper:
- [ ] **The tracker record is missing.** The cwd has only `brief.md`; there is no `notes.json`, `sources/` or `dependency-state.json`. So I could not check the problem statement or the "Prior-art check" line (`results/issue_395/iteration-v9/brief.md:127`, a sign-off finding on #395 iteration 8) against any thread. The brief's origin and the claim "No earlier fix on `main`" are unverified. A human should confirm the #395 sign-off finding exists and says what the brief says it says.
- [ ] **"The only caller today is the advisory `_audit_wave_overlap`" is false.** `waves.diff_files` also feeds the size backstop: `template/src/pdca_harness/size_signal.py:406` (`patch_files = len(waves.diff_files(patch))`, with a docstring at :390-392 saying the backstop and the scheduler must agree on this count) and `template/scripts/size-calibrate:344` (`patch_files=len(waves.diff_files(patch))`). The fix will therefore also raise `patch_files` for any bundle that touches a quoted path, which changes a size signal and calibration rows. That is probably the right outcome, but it is a behaviour change the brief neither scopes nor tests. The brief should list these callers. Criterion (d) should also name `template/tests/test_size_calibrate.py` (e.g. `test_diff_files_are_counted`, :339-343) as a test that must stay green.
- [ ] **No criterion that the unquote helper never raises.** `size_signal.measure` wraps the call in `except (OSError, UnicodeDecodeError, ValueError)` (`size_signal.py:405-410`), but `_audit_wave_overlap` has no guard (`flow.py:1592`). If the new helper raises on a malformed or truncated escape, for example `bytes.decode` on a lone `\3` or an invalid UTF-8 octal sequence, the advisory audit turns into a crash in the flow. Today it only misses the path. Add a criterion: a malformed quoted header (bad escape, unterminated quote, octal bytes that are not valid UTF-8) does not raise, and is either skipped or decoded with replacement.
- [ ] **The mixed-header claim doesn't match the code.** The brief says (line 8) that "a mixed header (one side quoted) yields a path with a stray quote". For `diff --git a/plain.txt "b/café…"`, the regex requires a literal ` b/`, but the line has ` "b/`. For `diff --git "a/…" b/plain.txt`, the line has no `^diff --git a/` prefix. Both forms fail to match, so both paths are dropped; no stray-quote path comes out. Criterion (c) is still RED on `main` either way, so this only corrects the framing. But Do should not write a test asserting today's "stray quote" behaviour as the baseline.
- [ ] **The dependence on git config is unstated.** Criterion (a) relies on the default `core.quotePath=true` in the temp repo. A developer or CI machine with `core.quotePath=false` in global config would write `café.txt` unquoted, and (a) would pass on `main`, which breaks the "RED on `main`" claim. The test should pin the setting with `git -c core.quotePath=true diff`. If it does not, it should at least include a case that git always quotes (`"`, `\`, tab), which criterion (b) covers. Nothing in the target source sets `quotePath` (Grep found no matches), so harness-produced patches follow whatever the user's git config says.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — `template/tests/test_waves_quoted_paths.py:130`: leg (f) only checks `assertIsInstance(..., set)`. The docstring at `template/src/pdca_harness/waves.py:481-482` promises that a malformed quoted header is *skipped*, but the test never checks that. Each malformed line in the test resolves to `[]` today, so `assertEqual(waves.diff_files(p), set())` would pin the stated behaviour. Without it, a change that returns a half-decoded path, such as `"a/x\\q"`, would still pass.. Deferred, not addressed here: 7 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
