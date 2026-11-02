# Result — issue 842 / wave-mode-unknown-value-note

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: (a) `Config.load(root)` on a `pdca.toml` with `[driver] wave_mode = "bogus"` raises `ValueError`; the exception message names `wave_mode`, the bad value, and the allowed values `stack | merge`; nothing is written to stderr by `Config.load` itself (the CLI prints the message, see (c)). (b) `"Merge"`, `"merge "` (trailing space), `"none"`, and the non-string values `1`, `true`, the array `["merge"]` and the inline table `{ mode = "merge" }` are refused the same way: `ValueError`, message naming the value as given (`!r`, so `"merge "` shows its space and `["merge"]` shows its brackets). The check must raise `ValueError` and nothing else for ANY TOML value type: an array or table is unhashable, so a bare `value not in {"stack", "merge"}` set test raises `TypeError` instead, which `cli.py:452` does not catch and which is then a traceback — test the type first (`isinstance(value, str)`) and membership against a tuple. Matching stays exact on purpose — no `.lower()`, no `.strip()`: today neither `"Merge"` nor `"merge "` enables merge mode (the checks compare with `==`), and folding case or whitespace would start merging PRs for that instance. `"none"` is an unknown value in this bundle; the sibling 843 then adds it to the allowed set (that is what 843 depends on this bundle for). (c) Driving the real CLI, `cli.main(["status"])` with the working directory on such a root returns 2, stderr is exactly one line, that line contains `wave_mode`, the bad value and `stack | merge`, and contains no `Traceback`. This leg needs no CLI change: `cli.py:452-454` already catches `ValueError` from `Config.load` and prints `pdca: invalid pdca.toml — <message>`. (d) `"stack"`, `"merge"` and an absent key raise nothing, print nothing, and keep their value (`"stack"` for the absent key).
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

Review issue #842: reject unknown `[driver].wave_mode` values with a silent loader `ValueError`, surfaced by the CLI as one stderr line and exit 2, while preserving valid values and the default.

Source citations are relative to `$PDCA_TARGET` (`target/`); brief and evidence citations are relative to this review directory.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Exact matching, invalid TOML types, error ownership, and unchanged defaults have explicit, falsifiable outcomes; the brief expressly supersedes the rejected fallback policy (brief.md:10, brief.md:12; template/src/pdca_harness/cli.py:452). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix leaves nine assertion failures: eight invalid values are accepted and the CLI returns 0 instead of 2; valid/default cases already pass (review-red-green.log:4, review-red-green.log:101; template/tests/test_config_wave_mode.py:68, template/tests/test_config_wave_mode.py:88). |
| C3 Change | PASS | The patch stays within the authorized loader boundary and new regression file; the existing CLI error contract handles the failure without a second printing site (template/src/pdca_harness/config.py:738, template/src/pdca_harness/cli.py:452; review-context.log:9). |
| C4 Verification (red→green) | PASS | Restoring the same production change independently turns all three tests green after the nine pre-fix failures; this agrees with the frozen gate evidence (review-red-green.log:101, review-red-green.log:117; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | Rejecting invalid input before constructing the config prevents downstream mode misclassification; this is input validation, with no optional-capability probe or fallback hiding an eager cause; 19 invalid literals across every TOML type also passed real loader/CLI checks (template/src/pdca_harness/config.py:739, template/src/pdca_harness/config.py:875; review-types.log:21). |
| T1 Structure | PASS | Validation belongs at the single loading boundary, and tests import the production APIs rather than copying the decision logic or modifying callers (template/src/pdca_harness/config.py:739; template/tests/test_config_wave_mode.py:20, template/tests/test_config_wave_mode.py:40). |
| T2 Shape | PASS | Independent docs lint, 64-page site render/internal-link audit, and diff whitespace checks pass; frozen docs and host-parity logs report the same local checks, without establishing a remote CI run (review-scanners.log:1; gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | Independent driver-suite run reports 2,700 tests, OK with two skips; frozen evidence additionally shows 50 root tests passing, including real render/update cases; the local Copier limitation is documented below (review-driver-suite.log:1819; gate-logs/T3-suite.log:66, gate-logs/T3-suite.log:80). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate explicitly owes its substantive audit to publish, where it must re-run (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Decide whether the carried-forward prior-art conclusion adequately covers merged and closed/rejected work by affected file path — the brief records that search, but this target has only one synthetic commit and no remotes, so the historical conclusion cannot be independently settled here (brief.md:27, brief.md:33; review-context.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept strict rejection as fit for release and record the superseding ruling on #842 before publish — its stale issue body still promises fallback, while hook error handling and neighbouring fallback policies remain explicitly deferred human-owned follow-ups (brief.md:10, brief.md:19; template/src/pdca_harness/config.py:740). |

Independent execution used the disposable target in place: `git stash push -- template/src/pdca_harness/config.py`, run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_config_wave_mode.py -v` from `target/template`, then `git stash pop` and re-run. The new test remained present for both legs. The patch was restored and `git apply --reverse --check ../patch.diff` confirmed that the supplied patch matches the target (review-context.log:9). Full driver discovery and both docs tools were also run directly; temporary files and renderer output stayed inside the review directory.

The local root runner exited 77 because `/usr/bin/python3` cannot import Copier; its 45-test run with three skips is **not** evidence of render/update coverage (review-root-suite.log:3, review-root-suite.log:6). The frozen T3 log independently supplies that coverage: both render cases and five update-compatibility cases executed successfully, and the root run ended with 50 tests passing (gate-logs/T3-suite.log:38, gate-logs/T3-suite.log:66, gate-logs/T3-suite.log:80). This is a reviewer-host caveat, not a patch defect or an undischarged dependency of the fix. The brief declares no external dependencies (brief.md:20).

For the instance-scoped wrapper verdicts, their supplied logs were read; the production-import assertion is corroborated by the actual imports and execution, and the deferred T4 row remains N/A. The available integration file is the unrendered template with no additional enumerated human-only items (template/docs/INTEGRATION.md.jinja:80).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review: issue 842, wave_mode refusal

No correctness bugs found in the patch. There are no NEEDS-HUMAN items. The one finding below is an optional cleanup.

- Simplification (optional): `template/src/pdca_harness/config.py:739` — the `isinstance(wave_mode, str)` test changes nothing, because membership in a tuple compares with `==` and never hashes. I ran `['merge'] in ("stack", "merge")`, and the same check on a dict, an int, a bool and a date. All return `False` with no `TypeError`, so `if wave_mode not in ("stack", "merge"):` refuses the same values. The comment at `config.py:737` ("The type comes first so that every TOML value is refused the same way") implies the type test is needed. The `TypeError` risk only applies to a set, which the patch does not use. The brief asks for the type test explicitly, so keeping it conforms to the brief and does no harm. The type test would only matter if someone later changed the tuple to a set.

## What was checked and found clean

- Message stays on one line: `!r` escapes any newline in a TOML string, so `template/src/pdca_harness/cli.py:452-454` still prints a single line.
- Callers: `cli.py:448` and `template/scripts/size-calibrate:599-601` both catch `ValueError`. `template/.claude/hooks/handoff_guard.py:45` does not, and the brief rules it out of scope.
- Existing configs in the repo: every `wave_mode` line in a TOML template or test uses `stack` or `merge`. The other tests set the attribute directly on a `Config`, which skips the new check. The full driver suite passes (`gate-logs/T3-suite.log`: 2700 tests, OK, 2 skipped).
- Tests: `template/tests/test_config_wave_mode.py` goes through the real loader and the real CLI, and restores the working directory before the temp directory is removed. The C4 log shows the tests fail without the fix and pass with it. I re-ran the new test file on the target and all 3 tests passed.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Decide whether the carried-forward prior-art conclusion adequately covers merged and closed/rejected work by affected file path — the brief records that search, but this target has only one synthetic commit and no remotes, so the historical conclusion cannot be independently settled here (brief.md:27, brief.md:33; review-context.log:1).
- [x] Validation — fitness-to-purpose — Accept strict rejection as fit for release and record the superseding ruling on #842 before publish — its stale issue body still promises fallback, while hook error handling and neighbouring fallback policies remain explicitly deferred human-owned follow-ups (brief.md:10, brief.md:19; template/src/pdca_harness/config.py:740).
- [x] **Unhashable values can escape the handler, and the criterion would not catch it.** Brief (b) requires refusal of "a non-string value such as `1`", and (c) requires no `Traceback`. TOML also allows `wave_mode = ["merge"]` or an inline table. If Do writes the membership test against a set (`not in {"stack", "merge"}`), a list raises `TypeError: unhashable type`, which `cli.py:452` (`except ValueError`) does not catch, so it is a traceback. `1` is hashable, so every test the brief specifies would stay green on that patch. The brief does not pin the test's shape. Revise: add an array value to leg (b) and the unknown-values test, or require a tuple or an `isinstance` guard.
- [x] **"Do reads ONLY this file" conflicts with the test instructions.** Brief line 3 and `.claude/agents/builder.md:25` ("Read `brief.md` **only** — not prior cycles") bar Do from prior cycles. The builder's one exception covers a peer callsite named under `Citations expected` (`builder.md:29-31`). Yet `Test file` tells Do to "keep its loader helper and the known-values test as they are" from `iteration-v1/patch.diff`, which is a prior cycle and is not cited there. Do must either break its contract or reinvent the helper while told to keep it. The `test_flow_slice.py:636-652` shape is also cited only under `Test file`, not under `Citations expected`. Revise: inline the helper and test text in the brief, or state the helper's shape and move both references under `Citations expected`.
- [x] **The tracker still specifies the rejected policy, and the ruling appears nowhere in the thread.** `notes.json` has `"comments":[]`, and its body says "prints one stderr line ... and gives `cfg.wave_mode == \"stack\"`", "print the note, fall back to `\"stack\"`, and raise nothing", and "validate as `merge_requires` does ... (print a note, fall back)". It also lists `"none"` as out of scope without saying it is refused. The title and slug still say "note". The brief reverses all of this on the authority of a sign-off recorded only in the bundle, and the PR will carry `Refs #842`. A reviewer reading the linked issue sees a patch contradicting its criterion. Revise: have the brief require a #842 body update or comment recording the 2026-10-30 ruling before publish, or state explicitly that the tracker is left stale.
- [x] **"How the CLI surfaces it" leaves one caller of the raise unguarded.** The brief says "`Config.load` raises, and the CLI turns that into one stderr line". There are three non-test callers: `cli.py:448` and `scripts/size-calibrate:599-601` both catch `ValueError`, but `template/.claude/hooks/handoff_guard.py:45` does not. `_bootstrap()` runs on both `--check` and `--abandon` (`handoff_guard.py:55`, `:58`), so a bad `wave_mode` there gives a raw traceback, not one line. On `--check` the exit status also becomes 1, the same code the docstring gives a contract FAIL (`:10`). `--abandon` is the escape route the driver tells a leaf session to use (`handoff.py:621`, `leaves.py:4474`), and it could not record a reason. This gap already exists for malformed TOML, and it needs `pdca.toml` to go bad during a leaf session, because a bad file would already stop `pdca` before the leaf starts, so severity is modest. But the brief's out-of-scope list names only `cli.py`, so this stays undecided. Revise: state that the hook is knowingly left as is, and file it, or bring it in scope.
- [x] **The carved-out sibling keys have no destination.** Brief line 5 states the ruling generally ("a mis-configured `pdca.toml` must produce a message AND a failure"), but the scope leaves `merge_requires`, `merge_method` and `merge_wait_secs` "for its own issue", with no id. The list is also incomplete against that ruling. `config.py` keeps note-and-substitute behaviour at `sweep_worktrees` (`:768-772`), `[records] mode` (`:808-809`), `confirm_gating_fail` (`:599-602`), `network_access` (`:674-676`) and `dependency_halt` (`:796-798`). After this patch one key hard-fails while its neighbours fall back, and `config.py:735-737` still argues for falling back. Limiting this slice to one site is correct; the fault is that nothing tracks the rest except a pointer to round 1's SUMMARY §10, which is not in the inputs here. Revise: cite the follow-up issue id and list the full set of sites, or record that the human accepted the inconsistency.

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
- File: `template/.claude/hooks/handoff_guard.py:45` does not catch `ValueError` from `Config.load` — a bad `pdca.toml` during a leaf session gives a traceback on `--check` / `--abandon` (ruled out of scope here, brief.md:19).
- File: apply the 2026-10-30 fail-not-fallback ruling to the other note-and-substitute config keys (`confirm_gating_fail`, `network_access`, `merge_requires`, `merge_wait_secs`, `expected_checks`, `sweep_worktrees`, `dependency_halt`, `[records] mode`, `merge_method`) — after #842 one key hard-fails while its neighbours fall back (brief.md:19).
