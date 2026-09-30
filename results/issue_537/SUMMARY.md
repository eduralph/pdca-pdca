# Result — issue 537 / the-builder-retries-like-every-other-leaf

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch: (i) a **transient** builder death is retried,
  bounded, with backoff, under the same `_invoke_leaf_resilient` contract the other three
  leaves use, while a **substantive** builder failure is still not retried; either way the
  final failure is still captured to `build.error.log` and still re-raised, so
  `flow._isolate` drops just this bundle as today; (ii) a retried **builder** is told in its
  prompt that a previous attempt died mid-flight and that any `patch.diff` /
  `build-notes.md` / test file present is that attempt's incomplete residue to verify or
  replace — never evidence the work is done, and attempt 1's prompt is byte-identical to
  today's; (iii) **every** failed Do — transient or substantive — prints the residue actually
  on disk and the next action true for it, naming, when a `patch.diff` was left, that the
  bundle now reads BUILT and that a plain re-run runs Check on it; only the *"transient —
  absorbed after N attempts"* sentence is conditioned on the failure having been classified
  transient, and N is the attempts actually spent, not the budget. Nothing deletes the
  builder's artifacts to make that sentence true, and the state machine is **asked**
  (`state.state(d)`), never inferred from the residue's shape; (iv) the per-attempt records
  the wrapper flushed (child-1) survive — `do_build`'s outer capture must not overwrite the
  post-mortem the retries built; what is left for that capture is a Do that died *around* the
  leaf (`worktree.ensure`, the lane lock), which otherwise has nothing bundle-local at all;
  (v) nothing else changes: the shipped resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, and the `_memory_log_for` derivation — **derive
  it, do not pass `memory_log=`** where the other three call sites do not; the builder's
  current explicit `memory_log=d / BUILD_MEMORY_LOG` at `:1830` derives to the identical
  file), the #420 memory-telemetry post-mortem still rides `output` into the same log, a
  successful build is spawned and reported exactly as today, `_stub_build` (`:1889`) and
  `select_builder` (`:1634`) behave exactly as today, `do_build`'s stale-log clear
  (`:1747-1753`) and the archive rule pinned by `test_build_error_log.py:91-105` still hold,
  and both offline suites stay green **and fast** (see Falsifiability).
- Repo + branch target: eduralph/pdca-harness @ main (base `acb214a`; every `path:line`
  above was re-verified against it while this proposal was written)
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

Review the builder retry fix: absorb transient Do failures with bounded retries, preserve attempt records, and accurately explain unfinished artifacts and the next action.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded retry, unchanged substantive-failure behavior, residue warning, and preserved error-record requirements are falsifiable through the existing Do entry point; `target/template/tests/test_builder_retry.py:164`, `target/template/tests/test_builder_retry.py:223`. |
| C2 Reproduction (red pre-fix) | PASS | Stashing only production changes reproduced nine behavioral failures across 23 tests, including one invocation instead of three; tests imported successfully (`reviewer-red.log:138`; `target/template/tests/test_builder_retry.py:168`). |
| C3 Change | PASS | Failed attempts retain their records and propagate the final exception; successful invocation arguments and attempt-one prompt remain unchanged, preserving caller containment and telemetry (`target/template/src/pdca_harness/leaves.py:2042`, `target/template/src/pdca_harness/leaves.py:2168`; `target/template/tests/test_builder_retry.py:290`). |
| C4 Verification (red→green) | PASS | After stash restoration, all 28 changed-file and shared-resilience tests passed in 0.857s; the independently reproduced red→green agrees with the frozen gate (`reviewer-green.log:41`; `gate-logs/C4-verify.log:10`; `target/template/tests/test_builder_retry.py:164`). |
| C5 Causal adequacy | PASS | The missing builder retry path is corrected through the shared production wrapper; subprocess tests exercise that path and its real failure classification, rather than a copied implementation (`target/template/src/pdca_harness/leaves.py:2168`; `target/template/tests/test_builder_retry.py:135`; `gate-logs/C5-prod-path.log:10`). |
| T1 Structure | PASS | One production module and two test files cover the same recovery contract; state determination stays with the existing state machine and attempt recording stays with the shared wrapper (`target/template/src/pdca_harness/leaves.py:2082`, `target/template/src/pdca_harness/leaves.py:753`). |
| T2 Shape | PASS | Independent whitespace validation, docs lint, and the 22-page render/link audit passed; frozen host-CI parity evidence agrees (`reviewer-docs.log:1`; `gate-logs/host-ci-docs.log:10`; `target/.github/workflows/docs-check.yml:36`). |
| T3 Runtime | PASS | The independent driver suite passed 1,977 tests in 34.128s with two skips; the frozen root suite passed all 24 tests, including render/update cases; local root reproduction is limited by missing Copier in this interpreter (`reviewer-suite.log:1656`; `gate-logs/T3-suite.log:54`; `reviewer-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit is deferred to its mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-file prior art across merged history and closed/rejected work before accepting novelty and scope: the supplied target has one snapshot commit and no remote, while the brief supplies only a narrative of earlier attempts (`reviewer-prior-art.log:1`; `brief.md:185`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the existing transient classification and prompt-only recovery guidance are sufficient for real builder recovery: subprocess evidence proves retry mechanics and truthful reporting, but does not establish how a vendor model handles unfinished source edits (`target/template/src/pdca_harness/leaves.py:2187`, `target/template/src/pdca_harness/leaves.py:2274`). |

No grounded patch defects found. This review is advisory and does not gate acceptance.

Independent verification used the disposable `$PDCA_TARGET` under this review directory. I stashed only `template/src/pdca_harness/leaves.py`, retained the changed tests for the red leg, restored the stash, and ran the changed tests plus `tests.test_leaf_resilience`. The original three-file patch remains applied. The pre-fix snapshot contains the prerequisite per-attempt flush and settlement code; no stale-target caveat was needed.

The complete driver suite and docs checks were rerun with temporary files confined to this review directory. The root runner exited 77 because `/usr/bin/python3` cannot import Copier; this is a reviewer-host limitation, not a patch failure. The frozen T3 log explicitly shows successful Copier render/update cases (`gate-logs/T3-suite.log:35`) and the full root result (`gate-logs/T3-suite.log:54`). It therefore supplies the unavailable rerun evidence, rather than leaving the dependency undisclosed or unexercised. Instance-scoped gate wrappers were not available here; their captured logs were used alongside the direct checks. The C5 log confirms a production import, and the independently executed subprocess tests provide stronger behavioral evidence.

The C5 symptom-guard check found no eager/load-time capability workaround. Callable dispatch handles the declared string-or-callable prompt contract; artifact existence checks describe files that may legitimately be absent. Retry defaults, substantive failure classification, and sibling-owned harvest behavior remain unchanged.

Prior-art investigation ran by all three affected paths and returned only the synthetic base commit (`reviewer-prior-art.log:1`). No merged history, closed/rejected patch archive, or tracker metadata is available in the supplied artifacts. The brief names earlier rejected rounds, but that does not independently establish their path-level coverage. The target integration template's human-only list is an unfilled TODO (`target/template/docs/INTEGRATION.md.jinja:80`), so it adds no enumerated decisions beyond the two table rows above.

### Advisory — adversary

# Adversarial review — #537 (the builder retries like every other leaf)

I could not break the mechanism. The red→green proof holds and runs the real code path.
What sign-off has to weigh is what the fix does **not** cover.

## Findings

- NEEDS-HUMAN — **The incident behind this issue is still not retried.**
  `template/src/pdca_harness/progress.py:478` describes it: an escalated builder ran ~18
  minutes, then the API connection dropped mid-response and the CLI exited 1. Any
  `assistant`/`user`/`result` event sets `produced` (`progress.py:432`), so
  `LeafError.transient` is False (`leaves.py:106-109`) and the wrapper stops after attempt 1
  (`leaves.py:733` and the `break` below it). I ran that exact shape (an init event, a
  tool-use `assistant` event, an `is_api_error_message` event, exit 1) through the patched
  `leaves.do_build`: **1 invocation, no backoff, `LeafError transient=False`.** So the
  reported incident still costs a full cycle round. The brief scoped this out on purpose
  (#533/#510 own the classification), but the call-site comment at `leaves.py:2143-2144`
  ("no builder failure was ever retried — on the leaf where an attempt costs the most")
  reads as if the expensive case is now covered. It is not: only deaths **before the first
  work event** are absorbed, which are the cheap ones. The same cause makes criterion (ii)
  change nothing today. A retry only follows a death that did no tool work, so the retried
  builder sees exactly the bundle and worktree attempt 1 saw, plus `build.error.log`. The
  case the `_retry_notice` docstring gives as its reason (`leaves.py:2256-2258`: a retry
  reading "a partial patch.diff … as a finished build") can't happen under the current
  transient rule. Any build-notes.md or test file present at retry time was also there,
  unflagged, for attempt 1. The notice only starts to matter once #533/#510 widen what
  counts as transient. Sign-off should accept both points knowingly rather than read this
  patch as fixing the #506 incident.

- Test can't tell "attempts spent" from "the budget" (`template/tests/test_builder_retry.py:242`).
  I replaced `{spent}` with a literal `{3}` at `leaves.py:2191` and all 11 tests still
  pass. This isn't a defect: the wrapper only ends on a transient error when
  `attempt == attempts`, so the two numbers are always equal today. Criterion (iii)'s
  "N is the attempts actually spent" holds by construction, not because the test proves it.

- The retry prompt with a rubric configured is untested. `test_builder_retry.py:202` asserts
  `retry.startswith(first)`, which only holds with **no** rubric: with a rubric, `first` is
  task + rubric and the retry is task + notice + rubric. The production code is right
  (`leaves.py:2250` puts the notice before the rubric, and the rubric comes from the
  snapshot attempt 1 already wrote, so it's the same text). This is a coverage gap only.

- In-place mode leaves residue the report doesn't mention. `_do_residue` only lists bundle
  files (`leaves.py:2056-2061`). With `worktree = false`, or when `worktree.ensure` falls back
  to in-place, a substantive death that edited source leaves a dirty tree. The report still
  says "no patch.diff … was left in the bundle" and "a plain re-run starts Do again"
  (`leaves.py:2088-2092`), and the next builder builds on that tree without being told. With
  a real worktree this is fine, because the next Do resets it (`worktree.py:377-384`). Minor,
  but the retry notice already names in-place edits (`leaves.py:2269-2271`), so the report
  could name them too.

- The wrapper's retry progress line prints `workdir.name` (`leaves.py:755-757`). For the
  builder, that is the harness root or the lane worktree directory, not the bundle. In a
  run with several targets, the operator can't tell which Do is retrying. The brief says
  #533 owns the strings in that function, so this is not for this slice.

## Attempted and could not refute

- **Red→green.** I re-ran it in a sandbox copy. Red (production hunks of `leaves.py`
  reverted): 9 of the 11 new tests fail on assertions, none on imports. The 2 that pass are
  the no-regression guards (a substantive failure is not retried; a successful spawn keeps
  today's arguments). Green: 28 tests across `test_builder_retry`, `test_build_error_log` and
  `test_leaf_resilience` pass in 1.2 s. This matches `gate-logs/C4-verify.log`.
- **Production path, not a copy.** The tests drive the real `leaves.do_build` →
  `_invoke_leaf_resilient` → `_invoke` → a subprocess stub. Only pre-existing API is
  imported at module level.
- **(iv) overwrite guard** (`leaves.py:2042`). Without the retry-built log, the outer capture
  would write one record, and `test_both_attempts_are_still_in_the_log` checks for
  "first-death", so it would fail.
- **Unwritable settled record** (`leaves.py:766`, `2176-2183`). I changed `except OSError` to
  `except KeyError` and `test_build_error_log.py:163` errors, so the branch is covered (its
  `Path.write_text` mock reaches `_replace_record`'s temp-file write).
- **Attempt 1's prompt is byte-identical.** `leaves.py:2250` appends `""` when
  `dead_attempts == 0`, and `first` is built with the same `worktree_root=wt` as before.
- **#420 memory log.** `_memory_log_for` (`leaves.py:364-374`) derives `build.memory.jsonl`,
  the same file the old explicit argument named.
- **Wall-clock trap.** `test_build_error_log` runs in 0.23 s. No real backoff is slept, and
  the shipped defaults are untouched.
- **A stale log misread as this Do's record.** This can't happen. `do_build`'s unlink runs
  before the `try`, so a failing unlink raises before the new `error_log.exists()` guard.
- `_stub_build`, `select_builder` and the stale-log clear are untouched by the diff. T3 is
  green (`gate-logs/T3-suite.log`).

### Advisory — code-review

# Advisory code review — issue_537 (the builder retries like every other leaf)

I found no correctness bug that blocks this patch. The builder now goes through
`_invoke_leaf_resilient` with the shipped defaults. Attempt 1's prompt is built exactly as
before. The memory log is derived by the wrapper, not passed in. `do_build` still
re-raises, and its outer capture no longer overwrites the per-attempt record. Both new
test files drive the real `do_build` through a stub leaf. The findings below are minor.

- `template/src/pdca_harness/leaves.py:2042` — low, edge case. If the wrapper's
  mid-retry flush worked but the final settle write then failed (for example ENOSPC),
  `build.error.log` is left holding the UNFINISHED record. `do_build` sees that the file
  exists, skips its own write, and prints "the builder's per-attempt record is in
  build.error.log". The record is there, but readers treat it as if no log existed. Before
  this patch, the outer capture's raw `write_text` did not carry the settled marker
  either, so what a reader concludes does not change. The console line is only a little
  more confident than the disk supports. Not worth another round.
- `template/src/pdca_harness/leaves.py:766` / `:2180` — `raise exc from last` changes what
  the other three resilient call sites see when the settle write fails: the OSError now
  has `__cause__` set to the leaf's failure. They still get the same OSError type, so
  their behaviour does not change. Only `_do_build_command` reads `__cause__`, and it
  re-raises the original when the cause is `None` (for example an OSError from the
  opening `unlink`). The existing read-only test covers this path:
  `template/tests/test_build_error_log.py:165-170` patches `Path.write_text`, which
  `_replace_record` goes through.
- `template/src/pdca_harness/leaves.py:2160` — simplification, optional. The attempt count
  is tracked with a `nonlocal spent` side effect inside the prompt callback. It is correct:
  the callback runs right before each spawn, so `spent` is the number of attempts actually
  made. But the count comes from how prompts are generated, not from the wrapper. Having
  the wrapper expose the attempt count (or count the `----- attempt N` records) would
  avoid the hidden coupling. Leave it as is unless someone touches this again.
- `template/tests/test_build_error_log.py:36` vs `template/tests/test_builder_retry.py:99`
  — the two test modules each carry their own "time without sleep" shim
  (a `SimpleNamespace` copy vs a `__getattr__` proxy). The brief asks for copying over
  cross-module imports, so this is expected. Mentioned only in case a shared test helper
  is wanted later.
- `template/src/pdca_harness/leaves.py:2056` — checked, no issue. `_do_residue` resolves
  the brief's test file against the bundle. That matches `brief.test_files` ("relative to
  the bundle", `brief.py:181-186`) and the Do prompt, which tells the builder to put the
  test file in the bundle directory. The residue report and the retry notice are therefore
  talking about the same files.

No NEEDS-HUMAN items from this lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm affected-file prior art across merged history and closed/rejected work before accepting novelty and scope: the supplied target has one snapshot commit and no remote, while the brief supplies only a narrative of earlier attempts (`reviewer-prior-art.log:1`; `brief.md:185`).
- [x] Validation — fitness-to-purpose — Decide whether the existing transient classification and prompt-only recovery guidance are sufficient for real builder recovery: subprocess evidence proves retry mechanics and truthful reporting, but does not establish how a vendor model handles unfinished source edits (`target/template/src/pdca_harness/leaves.py:2187`, `target/template/src/pdca_harness/leaves.py:2274`).
- [x] **The incident behind this issue is still not retried.** `template/src/pdca_harness/progress.py:478` describes it: an escalated builder ran ~18 minutes, then the API connection dropped mid-response and the CLI exited 1. Any `assistant`/`user`/`result` event sets `produced` (`progress.py:432`), so `LeafError.transient` is False (`leaves.py:106-109`) and the wrapper stops after attempt 1 (`leaves.py:733` and the `break` below it). I ran that exact shape (an init event, a tool-use `assistant` event, an `is_api_error_message` event, exit 1) through the patched `leaves.do_build`: **1 invocation, no backoff, `LeafError transient=False`.** So the reported incident still costs a full cycle round. The brief scoped this out on purpose (#533/#510 own the classification), but the call-site comment at `leaves.py:2143-2144` ("no builder failure was ever retried — on the leaf where an attempt costs the most") reads as if the expensive case is now covered. It is not: only deaths **before the first work event** are absorbed, which are the cheap ones. The same cause makes criterion (ii) change nothing today. A retry only follows a death that did no tool work, so the retried builder sees exactly the bundle and worktree attempt 1 saw, plus `build.error.log`. The case the `_retry_notice` docstring gives as its reason (`leaves.py:2256-2258`: a retry reading "a partial patch.diff … as a finished build") can't happen under the current transient rule. Any build-notes.md or test file present at retry time was also there, unflagged, for attempt 1. The notice only starts to matter once #533/#510 widen what counts as transient. Sign-off should accept both points knowingly rather than read this patch as fixing the #506 incident.

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
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- #539 should correct the builder retry comment at `leaves.py:2143-2144` once the transient rule widens (it currently overstates what #537 alone covers).
