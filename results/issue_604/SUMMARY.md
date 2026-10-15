# Result — issue 604 / signoff-delta-cannot-forge-section6

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `pdca signoff <id> --iterate-do|--iterate-plan|… --delta "<text>"` writes `<text>` verbatim into §9's `- Iteration delta (if iterating):` field: `cli._signoff` passes `args.delta` straight through (`template/src/pdca_harness/cli.py:1473-1474`) and `signoff.record` writes it as given (`template/src/pdca_harness/signoff.py:247`, `:307-308`). Only the flow's sign-off path flattens the rationale to one line first (`template/src/pdca_harness/flow.py:182-186`). Every §6 reader takes the section under the LAST `## 6. NEEDS-HUMAN` heading (`signoff._needs_human_section`, `signoff.py:103-118`), and its docstring relies on §9 being single-line ("§9 holds only the sign-off record, whose iteration delta the flow flattens to one line"). A multi-line `--delta` holding a `## 6. NEEDS-HUMAN` line (e.g. a §6 block pasted from an older SUMMARY) therefore becomes the "real" §6. At the iterate transition `driver._retire_cleared_deferrals` (`template/src/pdca_harness/driver.py:135`, `:317-340`) calls `autoiterate.retire_cleared` (`template/src/pdca_harness/autoiterate.py:348`), which reads ticks from that forged block (`autoiterate.py:409-410`) and retires deferred-ledger entries the human never cleared. Reproduced by the issue_409 adversary review: ledger `[E1, E2]`, both open in the real §6, then `pdca signoff X --iterate-do --delta "$(printf 'notes\n## 6. NEEDS-HUMAN (from v1)\n- [x] E1\n- [x] E2')"` → both retired (`kept: []`). The suite cannot see it because its helper `_section6` (`template/tests/test_autoiterate.py:95-99`) uses the same last-heading rule.
- Success criterion: With the patch, through the CLI sign-off path (`cli._signoff` with `iterate_do=True` and `delta` set to `"notes\n## 6. NEEDS-HUMAN (from v1)\n- [x] E1\n- [x] E2"`), then `driver.advance` on that bundle: the deferred ledger (`autoiterate.deferred`) still holds both `E1` and `E2`, which were open `- [ ]` rows in the §6 `assemble` wrote. A second leg does the same with the forged block in `by` instead (`by="me\n## 6. NEEDS-HUMAN\n- [x] E1"`, plain `delta`): the ledger still holds `E1`. In both legs the SUMMARY.md written by the sign-off has exactly one line that starts with `## 6. NEEDS-HUMAN` (the one `assemble` wrote), and §9 holds the human's words on one line (`notes` and `E1` appear in the delta field, `me` in `By / date`). The forged heading text may survive as inline text inside that line; that is safe because headings only count at the start of a line (`signoff._section_span`, `signoff.py:359`, `line.startswith("## ")` over `text.splitlines()` at `:345`). Positive control, same fixture: a single-line delta plus a real `- [x]` on `E1` in assemble's §6 retires `E1` and keeps `E2`. This proves the retire step actually runs on this fixture, so the RED below is not a fixture failure. Pre-fix the forged legs retire the entries (the ledger is `[]` in the delta leg, `[E2]` in the `by` leg). That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make `signoff.record` unable to write a line break into §9, for both the `delta` and the `by` values, so every caller gets one rule: `cli._signoff` (`cli.py:1473-1474`), the flow (`flow.py:182-186`), and `cleanup` (`cleanup.py:154`). The fix lives in `signoff.record` (`signoff.py:247-310`), not at each call site. Rule: each line-boundary run is replaced by one space; a value with no line boundary is recorded byte-for-byte as today (so every existing #529 test still passes unchanged). Amend the #529 docstring in `set_field` (`signoff.py:277-278`, "every byte the human wrote is recorded literally") and the module docstring of `test_signoff_verbatim.py` to say: literal, except that line breaks become spaces. Known side effect, expected: before the fix, `signoff.iteration_delta` (`_DELTA_RE`, `signoff.py:33`, one line per match) already cut a multi-line delta to its first line, so the next brief's carry-forward (`driver.py:371`) saw only `notes`. After the fix it sees the whole flattened text. / out of scope: the markdown-state format redesign (#607); the flow's session carry-forward (`state.SESSION_CARRY`, which stores the full multi-line rationale outside SUMMARY.md and must keep doing so); changing `_needs_human_section`'s last-heading rule; the test helper `_section6` (it may stay as is); changing what `record` does with backslashes (#529).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review issue #604: prevent multiline sign-off delta or signer text from forging SUMMARY.md §6 and retiring deferred findings the human never cleared.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded contract protects §6 authority while preserving single-line text and existing backslash behavior; the criteria are executable, with the signer-payload clarification below (`brief.md:11`, `brief.md:18`; `template/tests/test_signoff_verbatim.py:258`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production change reproduced an empty ledger for the forged delta and `[E2]` for the trailing-newline signer; the real-tick control still passed (`review-red.log:64`, `review-red.log:86`; `template/tests/test_signoff_verbatim.py:268`). |
| C3 Change | PASS | The two-file patch stays within the specified writer boundary and preserves callers, section selection, and session carry-forward; restored target diff matches `patch.diff` byte-for-byte (`template/src/pdca_harness/signoff.py:296`, `template/src/pdca_harness/signoff.py:319`). |
| C4 Verification (red→green) | PASS | The same nine tests produced 15 failed assertions/subtests with production stashed, then all passed after restoration, independently confirming the frozen C4 evidence (`review-red.log:232`, `review-green.log:16`; `template/tests/test_signoff_verbatim.py:237`). |
| C5 Causal adequacy | PASS | Removing line boundaries at the shared writer prevents the forged heading itself; actual CLI/driver retirement fails before the fix, while legitimate retirement succeeds, so this is neither a capability guard nor a vacuous fixture (`template/src/pdca_harness/signoff.py:296`; `template/tests/test_signoff_verbatim.py:223`, `template/tests/test_signoff_verbatim.py:268`). |
| T1 Structure | PASS | One shared normalization rule covers every recorded field without a dependency or duplicated caller policy; the callable replacement retains literal backslash semantics (`template/src/pdca_harness/signoff.py:275`, `template/src/pdca_harness/signoff.py:298`). |
| T2 Shape | PASS | Independent whitespace checking, docs lint, and rendering of 22 pages with the internal-link audit passed; frozen docs and host-parity logs agree (`target/.github/workflows/docs-check.yml:33`; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`). |
| T3 Runtime | PASS | Independent driver suite: 2,374 tests, two skips, no failures; the frozen root-suite evidence shows 24 tests passing, including real render/update cases, which the local interpreter could not rerun because Copier is not importable (`review-suite.log:1797`; `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive PR-body/tracker audit is owed to the mandatory publish rerun, not to a human waiver (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for both changed paths, including `template/tests/test_signoff_verbatim.py` — the brief documents production-path history but omits that affected test path, and this one-commit target has no remote/history with which to settle overlap independently (`brief.md:23`; `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept newline-to-space recording and the resulting full flattened rationale in the next brief as the intended interim behavior pending the format redesign — automated evidence proves ledger protection, while suitability of the changed human record remains a sign-off decision (`brief.md:18`; `template/src/pdca_harness/driver.py:371`). |

Source paths beginning `template/` resolve under `$PDCA_TARGET`, the supplied disposable `target/` checkout. Bundle and reviewer-log paths resolve in this review directory. The target matches the brief's base `b5f5c29`; no stale-target caveat was needed.

Independent reproduction used `git stash push -- template/src/pdca_harness/signoff.py`, retained the patched tests, ran `PYTHONPATH=src python3 -m unittest -v tests.test_signoff_verbatim` from `target/template`, restored with `git stash pop`, and reran the same command. Both legs and the full suite used a temporary directory inside this review root. The restored diff is identical to the supplied patch.

The brief's signer example without a trailing newline does forge a second heading before the fix, but the appended date prevents its tick from matching E1 exactly. The patch tests that heading injection and adds a trailing-newline payload that actually retires E1. Both fail before the fix and pass afterward. The genuine §6 tick retires only E1 in both versions. Exhaustive enumeration of Unicode `str.splitlines` boundaries, combined boundary runs, ordinary whitespace, and the existing backslash cases pass after restoration.

The C5 wrapper's frozen output only says no new test file was added (`gate-logs/C5-prod-path.log:10`); it does not establish production coverage. I also ran the available reference scanner, but base C5 on the exercised CLI, assembled SUMMARY, archived transition, and real ledger assertions above. Stub leaves and the `true` gate do not conceal the forbidden failure: the red leg demonstrates it in that same fixture.

The root-suite rerun exited 77: 19 tests ran with three skips and no Copier-dependent case executed (`review-root-suite.log`). This is a local interpreter limitation, not a patch failure or a verified local root-suite pass. The frozen gate log explicitly shows both render cases and all five update-compatibility cases executing successfully. The brief's Python/git dependency for the defect reproduction was exercised directly; no shim substituted for it. The available `template/docs/INTEGRATION.md.jinja` §4 contains only a TODO for additional project-defined human-only items.

Prior-art inspection ran by both affected file paths. `git log --all` returns only the synthetic base commit, `git remote -v` is empty, and the entire available history contains one commit (`review-prior-art.log`). Thus the brief's named merged/closed PR history is documented input, not independently confirmed history; the T5 decision above preserves that distinction.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 604 (signoff-delta-cannot-forge-section6)

The patch is clean on both lenses. I found no correctness bugs and no NEEDS-HUMAN items. The notes below are minor and optional.

## Correctness

- `template/src/pdca_harness/signoff.py:296`: the fix is in the right place. `set_field` flattens `value` before the callable `repl` closes over it. So `Outcome`, `By / date` (`f"{by} / {date}"`) and `Iteration delta` all go through one rule, and the #529 callable-`repl` handling of backslashes is unchanged. A value with no line break is not touched.
- `template/src/pdca_harness/signoff.py:41`: the character class matches exactly the 10 characters `str.splitlines` splits on. I checked this by running the same enumeration the test uses, which returns 10. `\r\n` is a run, so it becomes one space. The `+` keeps runs together, and other whitespace (tabs, double spaces) is kept as-is, as the brief asks.
- The tests do exercise the fix. The CLI legs (`template/tests/test_signoff_verbatim.py:237`, `:258`, `:263`) go through `cli._signoff` on a bundle at `cfg.bundle(id)`. The positive control (`:268`) shows the retire step really runs on this fixture. `gate-logs/C4-verify.log` shows these tests fail without the fix and pass with it. The `:263` leg (a trailing break in `--by`) is a good extra case: without the fix it is the one that actually retires E1.

## Reuse / simplification / efficiency (optional, non-blocking)

- `template/tests/test_signoff_verbatim.py:280`: scanning all 0x110000 code points takes about 0.13 s per run. That's acceptable, and deriving the set from `splitlines` (rather than hard-coding it) keeps the test honest if Python's set ever changes. No change needed.
- `template/tests/test_signoff_verbatim.py:284`, `:294`: each subtest calls the existing `_bundle()` helper (`:63`). That helper makes a `tempfile.mkdtemp()` directory and never removes it, so this test leaves about 13 temp directories behind per run. Older tests in the file already use the same helper. An `addCleanup(shutil.rmtree, d, True)` would fix it if wanted. Cosmetic only.
- `template/tests/test_signoff_verbatim.py:211`: the method is named `_signoff_then_advance`, but it never calls `driver.advance`, because `cli._signoff` already drives the transition. The docstring explains this, so it isn't misleading, but a name like `_signoff_via_cli` would match what the method does.

No NEEDS-HUMAN findings.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for both changed paths, including `template/tests/test_signoff_verbatim.py` — the brief documents production-path history but omits that affected test path, and this one-commit target has no remote/history with which to settle overlap independently (`brief.md:23`; `review-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Accept newline-to-space recording and the resulting full flattened rationale in the next brief as the intended interim behavior pending the format redesign — automated evidence proves ledger protection, while suitability of the changed human record remains a sign-off decision (`brief.md:18`; `template/src/pdca_harness/driver.py:371`).
- [x] **The invariant covers more than the scope and criterion test (`--by` is the same hole).** The brief's Invariant says "Every §9 value is recorded as one line, whichever entry point writes it". But Scope covers only "`--delta` passed to `pdca signoff`", and the Success criterion tests only `delta`. `by` goes through the same `set_field` with no flattening: `f"{by} / {date}"` at `signoff.py:302`, fed from `cli.py:1473` (`args.by`, `--by` at `cli.py:383`), `flow.py:185` (`pdca flow --by`, `cli.py:177`) and `cleanup.py:154` (`--by`, `cli.py:361`). For example, `pdca signoff X --iterate-do --by "$(printf 'me\n## 6. NEEDS-HUMAN\n- [x] E1')"` forges §6 the same way the issue describes. The planner has to pick one: (a) make Scope include `by` and add a `--by` RED leg, or (b) narrow the Invariant to the delta field and leave `--by` as a known residual (or file it). As written, Do can either quietly widen the patch or ship a fix that its own Invariant line says is incomplete, and no gate would notice either way.
- [x] **"One rule for every caller of `signoff.record`" contradicts the #529 contract the brief says not to change.** Scope and Invariant point toward flattening inside `signoff.record` ("any later caller of `signoff.record`"). But `record`'s own docstring at `signoff.py:277-278` promises "every byte the human wrote is recorded literally, whatever it contains". The test module Do is told to append to is named for that promise: `test_signoff_verbatim.py`, docstring lines 1-2, "§9 records the human's sign-off text verbatim". The brief only rules out changing backslash handling (`signoff.py:262-276`). It does not say whether flattening whitespace in `record` is allowed to override "every byte… literally", or whether the fix must stay at the call sites (`cli._signoff`, matching `flow.py:183`). The issue allowed either ("Flatten `--delta` in `cli._signoff` or in `signoff.record` itself"). The brief should name the layer, and if it picks `record`, say which docstring and contract text gets amended. Otherwise this is design drift found at review time.
- [x] **The test fixture in the brief doesn't fit the call it prescribes.** "Test file" sends Do to the `_bundle` helper in `test_signoff_verbatim.py:51-54`. That helper builds a bare `tempfile.mkdtemp()` with a hand-written 4-line SUMMARY (`:40-48`). It is not an "assembled SUMMARY.md", and it is not at `cfg.bundle(issue_id)`. `cli._signoff` resolves the bundle with `cfg.bundle(args.issue_id)` (`cli.py:1448`) and returns 1 if no SUMMARY is there (`:1450-1452`). Also, `driver.advance` → `_retire_cleared_deferrals` calls `assemble.collect_needs_human(d, cfg)` (`driver.py:334`) inside a catch-all `except Exception` that only prints (`:338-340`). If the stub bundle makes that call raise, retire never runs, the ledger stays `[E1, E2]` before the fix as well, and the test is green on both sides. So the "RED" would be vacuous, and C4 would only catch it if the revert leg actually checks for failure. The brief should require the test to first assert the pre-fix outcome (ledger `[]`) on that exact fixture, or to call `autoiterate.retire_cleared` directly as well. It should also say the fixture needs a bundle dir resolvable through `cfg.bundle` (not `_bundle()`) plus whatever Check artifacts `collect_needs_human` needs.
- [x] **Part of the criterion doesn't line up with what flattening produces.** The criterion says §9's delta "still carries the human's words (`notes` and `E1` appear in it)". After flattening, the recorded line is `notes ## 6. NEEDS-HUMAN (from v1) - [x] E1 - [x] E2`: the forged heading text stays, as inline text, in §9 and in the carry-forward (`driver.py:371` → `iteration_delta`). That is safe for `_section` only if heading matching is anchored at line start. The brief asserts that ("exactly one `## 6. NEEDS-HUMAN` heading at the start of a line"), but it doesn't cite where `_section`/`_section_span` anchors. One `path:line` showing the anchoring would make that assertion checkable, not assumed. A related side effect worth recording: before the fix, `iteration_delta` (`signoff.py:33` regex, `.*?$` per line) already cut a multi-line delta down to its first line (`notes`). So the fix also changes what the next brief's carry-forward contains. That's expected, but the brief should state it rather than leave it as an unannounced behaviour change.

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
- By / date: Eduard Ralph / 2026-10-10

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 4 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
