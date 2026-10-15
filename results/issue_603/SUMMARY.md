# Result — issue 603 / plan-advisory-tick-survives-iterate-do

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Plan-advisory findings are folded into SUMMARY §6 on every Check: `assemble.collect_needs_human` re-reads every `plan-advisory-*.md` in the bundle (`template/src/pdca_harness/assemble.py:446-448`) and renders each finding as an open `- [ ]` row. On iterate-do those files are NOT archived (`driver._archive_iteration` moves `plan-advisory-*` only when `include_brief` is true, i.e. on iterate-plan: `template/src/pdca_harness/driver.py:460-464`), so the next round reads the same files and every plan finding comes back unticked. The human's tick is never carried: `driver._retire_cleared_deferrals` (`driver.py:317-340`) only touches the #409 deferred-findings ledger and returns at once when that ledger is empty (`driver.py:332-333`), and even with a ledger a tick on a row that is one of this Check's own findings "retires nothing" (`autoiterate.retire_cleared`, `template/src/pdca_harness/autoiterate.py:366-370`). Effect, seen on issue_409 (5 plan findings re-cleared at each of 4 rounds) and issue_408 (6 findings across 3 rounds) of eduralph/pdca-pdca: the human clears the same plan findings again every round, even after a re-plan addressed them.
- Success criterion: With the patch, a plan-advisory finding the human ticked (`- [x]`) in §6 of round N's SUMMARY.md, followed by an iterate-do (`driver.advance` on a bundle whose §9 records `iterate-do`), does NOT appear as an open `- [ ]` row in §6 of round N+1's SUMMARY.md, and still does not after a SECOND iterate-do (round N+1 → N+2) with no new tick. The tick persists across rounds; it is not read once from round N's SUMMARY and then lost. The carried finding is either absent from §6 or shown outside §6's checkbox list; assembly never renders it as `- [x]` (see Scope). In the same test: (i) a plan-advisory finding the human did NOT tick at round N is still an open `- [ ]` row at round N+1 and N+2 and still blocks accept (`flow.accept_blockers` / `signoff.open_needs_human` returns it); (ii) after an iterate-plan, a re-plan whose plan advisory writes a `plan-advisory-*.md` raising the SAME text (byte-identical is allowed; the stub leaf does exactly that) shows it as an open row again. What resets the tick is the event, not the file content: the iterate-plan archive (`driver.py:460-464`) or a plan-advisory re-run (`leaves.py:4341-4342`). (iii) Ledger present: the same finding was also written to the #409 deferred-findings ledger by an earlier auto-iterate round (plan findings are HUMAN-kind, `assemble.py:442-445`, so `autoiterate.deferrable` keeps them, `autoiterate.py:318-325`). The human ticks it, iterate-do runs, and at round N+1 it is not an open row, neither as a fresh finding nor through `_deferred_needs_human` (`assemble.py:571-598`). Pre-fix the ticked row comes back open at round N+1. That is the RED.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a human's tick on a plan-advisory §6 row survive every iterate-do until the plan-advisory evidence is replaced, on both iterate entry points (`pdca signoff --iterate-do` then `pdca run`, and the flow's sign-off path), with or without a deferred-findings ledger present. Constraints on the fix: (a) Rendering: a carried finding is dropped from §6's checkbox list or shown as a read-only line that is not a checkbox. Assembly must never write `- [x]`: ticks are read positively from `- [x]` rows (`signoff.cleared_needs_human`, used by `autoiterate.retire_cleared`, `autoiterate.py:355-370`), so an assembly-written tick would count as a human one and could retire a ledger entry with no human action, against "It never clears a §6 box" (`autoiterate.py:46`). (b) Ledger: where the ticked finding is also a ledger entry, that entry must not bring it back as an open row. (c) Lifetime of whatever records the carried ticks: it must outlive iterate-do, and go away exactly when the plan-advisory artifacts do, i.e. when iterate-plan archives `plan-advisory-*` (`driver.py:460-464`) and when plan advisory re-runs and unlinks `plan-advisory-*` (`leaves.py:4341-4342`). So it must not be matched by `state.DOWNSTREAM_GLOBS` (archived on every iterate-do), and must not be matched by the `plan-advisory-*.md` globs that read findings (`assemble.py:447`, `leaves.py:3917`, `leaves.py:4272`). A non-`.md` file under the `plan-advisory-` prefix (e.g. `plan-advisory-cleared.json`) meets both. Do not use a `.memory.jsonl` suffix: `*.memory.jsonl` is in `state.DOWNSTREAM_GLOBS` (`state.py:155`) and is archived on every iterate. Do may choose another home that meets (c). / out of scope: changing what plan advisory raises or how it is run; folding plan findings into §6 only once (rejected: it would let an unticked finding stop blocking accept); the Check-side advisory and reviewer rows (their artifacts are re-generated every Check); the decorrelation note (#605); the §9 `--delta` parsing (#604).

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

Review issue #603: preserve human clearance of Plan-advisory findings across iterate-do rounds, while unticked findings remain blocking and replacement advisory evidence reopens findings.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | Persistence, unticked blockers, ledger duplicates, and event-driven reopening have falsifiable acceptance criteria; the existing contract requires findings to remain until human disposition (`brief.md:10`; `target/template/src/pdca_harness/assemble.py:438`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the two production files caused four of five new tests to fail because a cleared finding returned open; the quoted-tick safety case still passed (`review-red.log:19`; `review-red.log:67`; `target/template/tests/test_autoiterate.py:2370`). |
| C3 Change | PASS | The change stays within the authorized Plan-advisory lifetime and preserves the human-only origin of ticks; clearance is captured before archival and also excludes ledger duplicates (`target/template/src/pdca_harness/driver.py:136`; `target/template/src/pdca_harness/assemble.py:526`; `target/template/src/pdca_harness/assemble.py:676`). |
| C4 Verification (red→green) | PASS | After stash-pop, all 145 autoiterate tests passed, including all five new cases; the restored diff is byte-identical to the supplied patch (`review-green.log:298`; `target/template/tests/test_autoiterate.py:2361`). |
| C5 Causal adequacy | PASS | The observed cause is lost disposition state across retained evidence; actual driver/assembly tests cover two iterates, both reset events, ledger overlap, and quoted ticks, with no capability probe masking a load-time cause (`target/template/tests/test_autoiterate.py:2333`; `target/template/tests/test_autoiterate.py:2378`; `target/template/src/pdca_harness/assemble.py:510`). |
| T1 Structure | PASS | Both entry paths converge on the existing driver transition; clearance lifetime follows the same archive/rerun boundaries as its evidence, avoiding a competing lifecycle (`target/template/src/pdca_harness/flow.py:516`; `target/template/src/pdca_harness/cli.py:1483`; `target/template/src/pdca_harness/driver.py:482`; `target/template/src/pdca_harness/leaves.py:4341`). |
| T2 Shape | PASS | Independent docs lint and 22-page render/internal-link audit passed, as did diff whitespace checking; frozen host-parity evidence reports the same checks, not a remote CI run (`review-docs-lint.log:1`; `review-docs-render.log:2`; `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent offline suite passed 2,374 tests with two skips; the separate root render/update suite is supported by its frozen 24-test successful run, not an independent rerun (`review-suite.log:1810`; `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit is deferred to its mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art for every affected file, including `template/tests/test_autoiterate.py` — the brief records a production-path search, but this checkout has only one synthetic base commit and no remote, so completeness cannot be independently established (`brief.md:23`; `review-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether omitting previously cleared Plan-advisory rows until advisory replacement meets the intended sign-off workflow — tests establish persistence and blocker behavior, but acceptance of that disposition policy remains human judgment (`brief.md:18`; `target/template/tests/test_autoiterate.py:2361`). |

Evidence and limits:

- Source citations above were checked against the supplied disposable `$PDCA_TARGET` at `target/`. Its base identifies the brief's `b5f5c29` revision; no stale-target caveat was needed. No implementation files were edited. Only the production hunks were temporarily stashed for reproduction, keeping the new tests present, and the exact supplied patch was restored.
- Independent reproduction used `PYTHONPATH=src python3 -m unittest tests.test_autoiterate.PlanAdvisoryTickSurvivesIterateDo -v` from `target/template` with production changes stashed. Four failures explicitly reported a ticked finding returning open. After restoration, `PYTHONPATH=src python3 -m unittest tests.test_autoiterate -v` passed all 145 tests. Logs are `review-red.log` and `review-green.log`.
- Independent runtime validation used unittest discovery over `target/template/tests`, with `PYTHONPATH` pointing to its source. All temporary test artifacts were directed inside this review sandbox. Docs checks used the commands in `target/.github/workflows/docs-check.yml:33`, with render output and the Mermaid cache inside the sandbox.
- All six frozen gate logs were inspected. The C5 production-path scanner explicitly did no substantive checking because no new test file was added (`gate-logs/C5-prod-path.log:10`); the C5 verdict instead rests on source inspection and the independently executed production calls. Instance-scoped wrappers were not sought in unrelated checkouts.
- Copier is not importable in this review interpreter, and the disposable checkout has no release history. The root render/update suite therefore rests on frozen evidence: 24 tests passed, including render and update compatibility cases (`gate-logs/T3-suite.log:33`). This dependency was exercised by the original gate; it is not an unmet dependency of the Python/git bug reproduction. No tool aliases or substitute implementations were used for the independent red→green run.
- The prior-art investigation ran `git log` by all three affected paths, `git remote -v`, and `git show-ref`; the sole result was the synthetic base and local master (`review-prior-art.log:1`). The brief's history claim is recorded, not independently affirmed. The supplied integration template has no enumerated project-specific human-only items beyond its unfilled placeholder (`target/template/docs/INTEGRATION.md.jinja:80`).

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 603 (plan-advisory tick survives iterate-do)

Overall: the patch is correct for the cases in the brief. I found no bug that needs a rebuild. Ticks are read only from the real §6 (`signoff.cleared_needs_human`, the strict reader). Assembly never writes `- [x]`. The record file `plan-advisory-cleared.json` sits under the `plan-advisory-` prefix, so the iterate-plan archive (`template/src/pdca_harness/driver.py:482`) and the plan-advisory re-run unlink (`template/src/pdca_harness/leaves.py:4341`) both remove it. It is not `.md`, so the findings readers (`assemble.py:447` old / `_plan_advisory_items`, `leaves.py:3917`, `leaves.py:4272`) skip it. It is not in `state.DOWNSTREAM_GLOBS` (`state.py:155`), so an iterate-do keeps it. Both iterate entry points (CLI `pdca run` and the flow) go through `driver.advance`, so the one hook at `driver.py:136` covers both. The C4 log shows 4 of the 5 new tests red before the fix and all green after. The fifth is the §5-quote guard, which is expected to pass on both sides.

Minor notes. None of these blocks the patch, and none needs the human:

- `template/src/pdca_harness/assemble.py:676` — the ledger filter in `_deferred_needs_human` hides any ledger entry whose text matches a cleared plan finding, whatever leaf raised it. The ledger does not record where an entry came from. So if a Check-side advisory later raises the exact same text, gets deferred, and then stops raising it, its ledger copy is hidden too. This needs exact text equality with something the human already ticked, so the risk is small. The guard at `assemble.py:527` only covers the case where the other source is still open at tick time. To tighten it, apply the filter only when that text is still raised by a live `plan-advisory-*.md`, i.e. intersect with `_plan_advisory_items(d)`.
- `template/src/pdca_harness/assemble.py:539-542` — this re-implements the temp-file-plus-replace write that `autoiterate._write_ledger` already does (`template/src/pdca_harness/autoiterate.py:290-297`), but leaves out the PID in the temp name. Two writers on one bundle are unlikely, but the PID-suffixed form is the house pattern. A shared helper would remove the duplicate. The leftover `.plan-advisory-cleared.json.tmp` from a crash is dot-prefixed, so the `plan-advisory-*` archive and unlink globs never sweep it. That is harmless because the next write overwrites it.
- `template/src/pdca_harness/assemble.py:450` and `:676` — `plan_advisory_cleared(d)` reads and parses the JSON twice per assembly. It is a tiny file, so this is a nit only.
- `template/tests/test_autoiterate.py:2437` — `test_a_tick_quoted_into_section5_clears_no_plan_finding` passes before the fix as well, since no record exists to clear anything. It works as a regression guard for the strict-reader choice, not as part of the RED. That is fine, but the C4 red count (4 failures) depends on it staying that way.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art for every affected file, including `template/tests/test_autoiterate.py` — the brief records a production-path search, but this checkout has only one synthetic base commit and no remote, so completeness cannot be independently established (`brief.md:23`; `review-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether omitting previously cleared Plan-advisory rows until advisory replacement meets the intended sign-off workflow — tests establish persistence and blocker behavior, but acceptance of that disposition policy remains human judgment (`brief.md:18`; `target/template/tests/test_autoiterate.py:2361`).
- [x] **The success criterion only tests round N → N+1, but the reported defect spans 3–4 rounds.** The thread's evidence is "issue_409: 5 plan findings … re-entered §6 at every one of 4 rounds". The brief's criterion only checks that a tick at round N is not open at round N+1. Suppose a fix only reads round N's SUMMARY ticks at the next iterate and does not persist them. Or suppose it drops the row from §6 at N+1, so there is nothing to re-tick at the N+1 → N+2 iterate. Either fix passes the RED→GREEN test, and the row is back open at N+2. Add a second `iterate-do` (N+1 → N+2, with no new tick) to the criterion so that persistence across rounds is what gets tested.
- [x] **"File unchanged" in the criterion contradicts clause (ii) when a re-plan writes a byte-identical file.** The criterion and invariant tie the carried tick to "as long as the `plan-advisory-*.md` file that raised it is unchanged" / "the evidence that raised it is unchanged". Clause (ii) says a re-plan "raising the same text shows it as an open row again". A deterministic advisory gives exactly that case. The stub leaf always writes the same text (`leaves.py:4243-4248`), and that is the stub-config fixture the brief's own repro uses. A fix keyed on content hash or finding text would therefore carry the tick across iterate-plan and fail (ii), or meet (ii) only by accident. The brief should say that what resets the tick is an *event*: the iterate-plan archive (`driver.py:460-464`) and/or the plan-advisory re-run that unlinks stale artifacts (`leaves.py:4341-4342`). It should not be file identity. It should also say where the carried-tick record lives. A name matching `plan-advisory-*` is archived and unlinked at the right moments, but if it ends in `.md` it also lands in assemble's `plan-advisory-*.md` glob (`assemble.py:446-447`) and `_plan_advisory_outcomes` (`leaves.py:3917`). A name in `DOWNSTREAM_OF_BRIEF` would be archived on every iterate-do and defeat the fix.
- [x] **The brief doesn't say how a carried row is rendered, and one plausible choice silently retires deferred-ledger entries.** The criterion only says the row must not be an open `- [ ]`. That allows either dropping the row or having assembly pre-render it as `- [x]`. The second choice is unsafe:
- [x] **The scope covers runs with a deferred-findings ledger, but the test doesn't.** The Scope says "with or without a deferred-findings ledger present". The Repro and Falsifiability fixture has only a `plan-advisory-x.md` and no ledger. The case with a ledger is reachable: plan findings are HUMAN-kind (`assemble.py:442-445`), and `autoiterate.deferrable` excludes only IMPL and `no_verdict` items (`autoiterate.py:318-325`). So an auto-iterate round writes plan findings into the ledger. From then on, `_deferred_needs_human` (`assemble.py:571-598`) renders such a finding as an open row from the ledger whenever it is missing from this Check's fresh items. A fix that removes the ticked plan finding from `collect_needs_human` therefore brings it back through the ledger as an open `- [ ]` row unless the ledger entry is retired too. Add a ledger-present case to the criterion: the plan finding was deferred in an earlier auto round, the human ticks it, and it is not open after the next iterate-do.
- [x] **I could not check that issue 605 exists.** `Conflicts with: 605` is a conflict, not a `Depends on`, so it can't block the run. But there is no `dependency-state.json` and the thread never mentions 605, so the ordering note ("605 builds on it") is the planner's claim alone. Confirm 605 exists and touches `assemble.collect_needs_human` before relying on the wave order.

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
- Plan advisory: 5 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
